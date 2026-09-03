"""Sprint 51 development-only calibration of frozen Sprint 50 probabilities."""

# ruff: noqa: E501

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import platform
import shutil
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import numpy as np
import scipy
import sklearn
from scipy.stats import rankdata, wilcoxon
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from threadpoolctl import threadpool_limits

VERSION = "q1-development-only-calibration-1.0.0"
CONFIG_REL = Path("configs/experiments/q1_development_only_calibration_1.0.0.json")
OUTPUT_REL = Path("audits/q1-development-only-calibration/1.0.0")
AMENDMENT_REL = Path("audits/q1-temporal-protocol-amendment/1.0.0")
METHODS = ("RAW", "PLATT", "ISOTONIC")
PRIMARY_METRICS = ("Brier", "ECE")
DIAGNOSTIC_METRICS = ("ROC_AUC", "PR_AUC")


class CalibrationCampaignError(RuntimeError):
    """Raised whenever Sprint 51 must fail closed."""


def canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def identity_digest(values: object) -> str:
    return hashlib.sha256(canonical_bytes(values)).hexdigest()


def _write_json(path: Path, value: object) -> None:
    path.write_bytes(canonical_bytes(value))


def _write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _ordered_fields(rows: list[dict[str, Any]]) -> list[str]:
    return list(dict.fromkeys(key for row in rows for key in row))


def _write_gzip_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
            for row in rows:
                zipped.write(canonical_bytes(row))


def load_contract(root: Path) -> dict[str, Any]:
    contract = json.loads((root / CONFIG_REL).read_text(encoding="utf-8"))
    required = {
        "schema_version": "q1-development-only-calibration-contract-1.0.0",
        "starting_head": "5f2e0ef7b77081db3e91a46fca85da03a831d3ce",
        "methods": list(METHODS),
        "prohibited_partitions": ["T1", "T2"],
        "threshold_optimization": False,
        "model_training": False,
        "hyperparameter_search": False,
        "xai": False,
    }
    for key, value in required.items():
        if contract.get(key) != value:
            raise CalibrationCampaignError(f"execution contract changed: {key}")
    if contract["temporal_protocol"]["common_comparison_origins"] != list(range(3, 12)):
        raise CalibrationCampaignError("comparison origins changed")
    if contract["metrics"]["ece_bin_edges"] != [i / 10 for i in range(11)]:
        raise CalibrationCampaignError("ECE binning changed")
    return contract


def _manifest_entries(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        digest, name = line.split("  ", 1)
        if len(digest) != 64 or name in entries:
            raise CalibrationCampaignError(f"malformed manifest: {path}")
        entries[name] = digest
    return entries


def verify_ledger_identity(
    path: Path, expected_size: int, expected_sha256: str
) -> dict[str, Any]:
    if not path.is_file():
        raise CalibrationCampaignError("Sprint 50 raw probability ledger missing")
    if path.stat().st_size != expected_size:
        raise CalibrationCampaignError("Sprint 50 raw probability ledger size changed")
    actual = file_sha256(path)
    if actual != expected_sha256:
        raise CalibrationCampaignError("Sprint 50 raw probability ledger hash changed")
    return {"size_bytes": expected_size, "sha256": actual}


def verify_preflight(root: Path, contract: dict[str, Any]) -> dict[str, Any]:
    source = root / contract["source_audit"]
    ledger = root / contract["source_ledger"]
    manifest = source / "MANIFEST.sha256"
    entries = _manifest_entries(manifest)
    for name, expected in entries.items():
        path = source / name
        if not path.is_file() or file_sha256(path) != expected:
            raise CalibrationCampaignError(f"Sprint 50 manifest failure: {name}")
    verify_ledger_identity(
        ledger,
        contract["source_ledger_size_bytes"],
        contract["source_ledger_sha256"],
    )
    inventory = json.loads(
        (source / "external_artifact_inventory.json").read_text(encoding="utf-8")
    )["artifacts"][0]
    if (
        inventory["record_count"] != contract["source_ledger_rows"]
        or inventory["sha256"] != contract["source_ledger_sha256"]
        or inventory["compressed_size_bytes"] != contract["source_ledger_size_bytes"]
    ):
        raise CalibrationCampaignError("Sprint 50 packaging metadata changed")
    amendment = root / AMENDMENT_REL
    amendment_entries = _manifest_entries(amendment / "MANIFEST.sha256")
    for name, expected in amendment_entries.items():
        if file_sha256(amendment / name) != expected:
            raise CalibrationCampaignError(f"Sprint 50-R1 manifest failure: {name}")
    source_access = json.loads(
        (source / "t1_t2_access_audit.json").read_text(encoding="utf-8")
    )
    amendment_access = json.loads(
        (amendment / "t1_t2_access_audit.json").read_text(encoding="utf-8")
    )
    if any(
        value != 0
        for audit in (source_access, amendment_access)
        for key, value in audit.items()
        if key.endswith("_count")
    ):
        raise CalibrationCampaignError("upstream T1/T2 access counter nonzero")
    return {
        "status": "PASS",
        "sprint50_manifest_sha256": file_sha256(manifest),
        "sprint50_manifest_entries": len(entries),
        "sprint50_r1_manifest_sha256": file_sha256(amendment / "MANIFEST.sha256"),
        "source_ledger_sha256": file_sha256(ledger),
        "source_ledger_size_bytes": ledger.stat().st_size,
        "source_ledger_rows_declared": contract["source_ledger_rows"],
    }


def reliability_bins(
    y: np.ndarray, p: np.ndarray
) -> tuple[float, list[dict[str, Any]]]:
    if len(y) == 0 or len(y) != len(p) or not np.isfinite(p).all():
        raise CalibrationCampaignError("invalid reliability input")
    if ((p < 0) | (p > 1)).any():
        raise CalibrationCampaignError("probability outside [0,1]")
    assignments = np.minimum((p * 10).astype(int), 9)
    bins: list[dict[str, Any]] = []
    ece = 0.0
    for index in range(10):
        selected = assignments == index
        count = int(selected.sum())
        mean_probability = float(p[selected].mean()) if count else None
        positive_frequency = float(y[selected].mean()) if count else None
        if count:
            ece += count / len(y) * abs(positive_frequency - mean_probability)
        bins.append(
            {
                "bin_index": index,
                "probability_interval_lower": index / 10,
                "probability_interval_upper": (index + 1) / 10,
                "upper_inclusive": index == 9,
                "observation_count": count,
                "mean_predicted_probability": mean_probability,
                "empirical_positive_frequency": positive_frequency,
            }
        )
    return float(ece), bins


def metric_values(
    y: np.ndarray, p: np.ndarray
) -> tuple[dict[str, float], list[dict[str, Any]]]:
    if set(np.unique(y)) != {0, 1}:
        raise CalibrationCampaignError("evaluation unit lacks both classes")
    ece, bins = reliability_bins(y, p)
    return (
        {
            "Brier": float(brier_score_loss(y, p)),
            "ECE": ece,
            "ROC_AUC": float(roc_auc_score(y, p)),
            "PR_AUC": float(average_precision_score(y, p)),
        },
        bins,
    )


def fit_calibrator(
    method: str, p: np.ndarray, y: np.ndarray, contract: dict[str, Any]
) -> Any:
    support = calibration_support(p, y, contract)
    if not support["eligible"]:
        raise CalibrationCampaignError("insufficient calibration-fit support")
    if method == "PLATT":
        parameters = contract["calibrators"][method]
        return LogisticRegression(
            solver=parameters["solver"],
            C=parameters["C"],
            max_iter=parameters["max_iter"],
            random_state=parameters["random_state"],
        ).fit(p.reshape(-1, 1), y)
    if method == "ISOTONIC":
        parameters = contract["calibrators"][method]
        return IsotonicRegression(
            out_of_bounds=parameters["out_of_bounds"],
            y_min=parameters["y_min"],
            y_max=parameters["y_max"],
        ).fit(p, y)
    raise CalibrationCampaignError(f"unknown calibrator: {method}")


def calibration_support(
    p: np.ndarray, y: np.ndarray, contract: dict[str, Any]
) -> dict[str, Any]:
    temporal = contract["temporal_protocol"]
    positive = int(y.sum())
    negative = int(len(y) - positive)
    eligible = not (
        len(y) < temporal["minimum_fit_rows"]
        or positive < temporal["minimum_fit_positives"]
        or negative < temporal["minimum_fit_negatives"]
        or np.unique(p).size < temporal["minimum_unique_probabilities"]
    )
    return {
        "eligible": eligible,
        "fit_rows": len(y),
        "fit_positive": positive,
        "fit_negative": negative,
        "fit_unique_probabilities": int(np.unique(p).size),
        "reason": "ELIGIBLE" if eligible else "INSUFFICIENT_CALIBRATION_FIT_SUPPORT",
    }


def apply_calibrator(
    method: str, calibrator: Any, p: np.ndarray, decimal_precision: int = 12
) -> np.ndarray:
    if method == "RAW":
        return p.copy()
    if method == "PLATT":
        result = calibrator.predict_proba(p.reshape(-1, 1))[:, 1]
    elif method == "ISOTONIC":
        result = calibrator.predict(p)
    else:
        raise CalibrationCampaignError(f"unknown calibration method: {method}")
    result = np.asarray(result, dtype=float)
    if not np.isfinite(result).all() or ((result < 0) | (result > 1)).any():
        raise CalibrationCampaignError("invalid calibrated probability")
    return np.round(result, decimals=decimal_precision)


def _calibrator_state(
    method: str, calibrator: Any, decimal_precision: int
) -> dict[str, Any]:
    if method == "PLATT":
        return {
            "coefficient": round(float(calibrator.coef_[0, 0]), decimal_precision),
            "intercept": round(float(calibrator.intercept_[0]), decimal_precision),
            "classes": [int(value) for value in calibrator.classes_],
        }
    return {
        "x_thresholds": [float(value) for value in calibrator.X_thresholds_],
        "y_thresholds": [float(value) for value in calibrator.y_thresholds_],
        "increasing": bool(calibrator.increasing_),
    }


def _load_temporal_evidence(root: Path) -> dict[tuple[str, int], dict[str, str]]:
    path = root / AMENDMENT_REL / "temporal_block_reconstruction.csv"
    evidence: dict[tuple[str, int], dict[str, str]] = {}
    with path.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            evidence[(row["project"], int(row["block_identifier"]))] = row
    return evidence


def validate_membership_causality(
    fit_identifiers: list[str],
    evaluation_identifiers: list[str],
    maximum_fit_order_key: tuple[str, str],
    minimum_evaluation_order_key: tuple[str, str],
) -> None:
    if not fit_identifiers:
        raise CalibrationCampaignError("calibration-fit membership is empty")
    if set(fit_identifiers) & set(evaluation_identifiers):
        raise CalibrationCampaignError("evaluation-block self-fitting detected")
    if maximum_fit_order_key >= minimum_evaluation_order_key:
        raise CalibrationCampaignError("future calibration fitting detected")


def _condition_reference(root: Path) -> dict[tuple[str, str, str, int], dict[str, str]]:
    path = root / "audits/q1-temporal-robustness-cv/1.0.0/condition_results.csv"
    result: dict[tuple[str, str, str, int], dict[str, str]] = {}
    with path.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            key = (
                row["project"],
                row["algorithm"],
                row["configuration"],
                int(row["cv_value"]),
            )
            result[key] = row
    return result


def _ledger_groups(
    path: Path,
) -> Iterable[tuple[tuple[str, str, str, int], list[dict[str, Any]]]]:
    current_key: tuple[str, str, str, int] | None = None
    rows: list[dict[str, Any]] = []
    record_count = 0
    with gzip.open(path, "rt", encoding="utf-8", newline="") as stream:
        for line in stream:
            row = json.loads(line)
            expected_fields = {
                "algorithm",
                "benchmark_defined_observed_label",
                "configuration",
                "cv_value",
                "forward_block",
                "frozen_partition_provenance",
                "project",
                "raw_probability",
                "row_identifier",
            }
            if set(row) != expected_fields:
                raise CalibrationCampaignError("raw ledger schema mismatch")
            if row["frozen_partition_provenance"] not in {"TRAIN", "VALIDATION"}:
                raise CalibrationCampaignError("non-development row in raw ledger")
            if row["cv_value"] != row["forward_block"]:
                raise CalibrationCampaignError("CV and forward block mismatch")
            key = (
                row["project"],
                row["algorithm"],
                row["configuration"],
                int(row["cv_value"]),
            )
            if current_key is not None and key != current_key:
                yield current_key, rows
                rows = []
            current_key = key
            rows.append(row)
            record_count += 1
    if current_key is not None:
        yield current_key, rows
    if record_count == 0:
        raise CalibrationCampaignError("raw ledger empty")


def execute(root: Path, contract: dict[str, Any]) -> dict[str, Any]:
    preflight = verify_preflight(root, contract)
    ledger = root / contract["source_ledger"]
    conditions = _condition_reference(root)
    temporal = _load_temporal_evidence(root)
    algorithms = contract["algorithms"]
    configurations = contract["configurations"]
    expected_group_order = [
        (project, algorithm, configuration, cv_value)
        for project in sorted({key[0] for key in conditions})
        for algorithm in algorithms
        for cv_value in range(2, 12)
        for configuration in configurations
    ]
    metrics: list[dict[str, Any]] = []
    raw_all_origins: list[dict[str, Any]] = []
    reliability: list[dict[str, Any]] = []
    states: list[dict[str, Any]] = []
    ineligible: list[dict[str, Any]] = []
    memberships: dict[tuple[str, int], dict[str, Any]] = {}
    seen_groups: list[tuple[str, str, str, int]] = []
    current_project: str | None = None
    histories: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    total_records = 0
    fit_count = 0
    for key, rows in _ledger_groups(ledger):
        seen_groups.append(key)
        total_records += len(rows)
        project, algorithm, configuration, cv_value = key
        series = key[:3]
        if project != current_project:
            current_project = project
            histories = defaultdict(list)
        fit_rows = histories[series]
        reference = conditions.get(key)
        if reference is None or len(rows) != int(reference["evaluation_n"]):
            raise CalibrationCampaignError("ledger/condition reconciliation failed")
        identifiers = [row["row_identifier"] for row in rows]
        labels = np.asarray(
            [row["benchmark_defined_observed_label"] for row in rows], dtype=int
        )
        probabilities = np.asarray([row["raw_probability"] for row in rows])
        membership_key = (project, cv_value)
        membership_digest = identity_digest(identifiers)
        existing = memberships.get(membership_key)
        if (
            existing is not None
            and existing["evaluation_membership_digest"] != membership_digest
        ):
            raise CalibrationCampaignError(
                "membership differs by algorithm/configuration"
            )
        if existing is None:
            block = temporal[membership_key]
            memberships[membership_key] = {
                "project": project,
                "evaluation_origin": cv_value,
                "calibration_fit_origins": "+".join(str(v) for v in range(2, cv_value)),
                "calibration_fit_origin_count": max(0, cv_value - 2),
                "evaluation_rows": len(rows),
                "evaluation_positive": int(labels.sum()),
                "evaluation_negative": int(len(labels) - labels.sum()),
                "evaluation_membership_digest": membership_digest,
                "evaluation_minimum_order_key": f"{block['minimum_timestamp']}|{block['minimum_commit_sha']}",
                "evaluation_maximum_order_key": f"{block['maximum_timestamp']}|{block['maximum_commit_sha']}",
                "strictly_causal": cv_value == 2,
                "cv2_calibrator_status": (
                    "INELIGIBLE_NO_EARLIER_RAW_PROBABILITY_BLOCK"
                    if cv_value == 2
                    else "NOT_APPLICABLE"
                ),
            }
        raw_metric, _ = metric_values(labels, probabilities)
        raw_all_origins.append(
            {
                "project": project,
                "algorithm": algorithm,
                "configuration": configuration,
                "evaluation_origin": cv_value,
                "evaluation_rows": len(rows),
                "evaluation_positive": int(labels.sum()),
                "evaluation_membership_digest": membership_digest,
                **raw_metric,
            }
        )
        for metric in ("Brier", "ECE", "ROC_AUC", "PR_AUC"):
            source_name = metric
            if abs(raw_metric[metric] - float(reference[source_name])) > 1e-12:
                raise CalibrationCampaignError(
                    f"Sprint 50 RAW {metric} baseline reproduction failed"
                )
        if cv_value >= 3:
            fit_identifiers = [row["row_identifier"] for row in fit_rows]
            fit_labels = np.asarray(
                [row["benchmark_defined_observed_label"] for row in fit_rows], dtype=int
            )
            fit_probabilities = np.asarray(
                [row["raw_probability"] for row in fit_rows], dtype=float
            )
            latest_fit = temporal[(project, cv_value - 1)]
            evaluation = temporal[(project, cv_value)]
            max_fit_key = (
                latest_fit["maximum_timestamp"],
                latest_fit["maximum_commit_sha"],
            )
            min_eval_key = (
                evaluation["minimum_timestamp"],
                evaluation["minimum_commit_sha"],
            )
            validate_membership_causality(
                fit_identifiers, identifiers, max_fit_key, min_eval_key
            )
            member = memberships[membership_key]
            support = calibration_support(fit_probabilities, fit_labels, contract)
            member.update(
                {
                    "calibration_fit_rows": len(fit_rows),
                    "calibration_fit_positive": int(fit_labels.sum()),
                    "calibration_fit_negative": int(len(fit_labels) - fit_labels.sum()),
                    "calibration_fit_membership_digest": identity_digest(
                        fit_identifiers
                    ),
                    "calibration_fit_maximum_order_key": "|".join(max_fit_key),
                    "fit_evaluation_identity_overlap": 0,
                    "strictly_causal": True,
                }
            )
            if not support["eligible"]:
                ineligible.append(
                    {
                        "project": project,
                        "algorithm": algorithm,
                        "configuration": configuration,
                        "evaluation_origin": cv_value,
                        **support,
                        "action": "EXCLUDE_UNIT_FOR_ALL_THREE_STATES_AND_RETAIN_RAW_IN_ALL_ORIGIN_BASELINE",
                    }
                )
                histories[series].extend(rows)
                continue
            calibrated = {"RAW": probabilities}
            calibrators: dict[str, Any] = {}
            for method in ("PLATT", "ISOTONIC"):
                calibrator = fit_calibrator(
                    method, fit_probabilities, fit_labels, contract
                )
                fit_count += 1
                calibrators[method] = calibrator
                calibrated[method] = apply_calibrator(
                    method,
                    calibrator,
                    probabilities,
                    contract["calibrated_probability_decimal_precision"],
                )
                states.append(
                    {
                        "project": project,
                        "algorithm": algorithm,
                        "configuration": configuration,
                        "evaluation_origin": cv_value,
                        "method": method,
                        "fit_rows": len(fit_rows),
                        "fit_positive": int(fit_labels.sum()),
                        "fit_negative": int(len(fit_labels) - fit_labels.sum()),
                        "fit_membership_digest": identity_digest(fit_identifiers),
                        **_calibrator_state(
                            method,
                            calibrator,
                            contract["calibrator_state_decimal_precision"],
                        ),
                    }
                )
            for method in METHODS:
                values, bins = metric_values(labels, calibrated[method])
                metric_row = {
                    "project": project,
                    "algorithm": algorithm,
                    "configuration": configuration,
                    "evaluation_origin": cv_value,
                    "calibration_method": method,
                    "fit_rows": 0 if method == "RAW" else len(fit_rows),
                    "evaluation_rows": len(rows),
                    "evaluation_positive": int(labels.sum()),
                    "prevalence": float(labels.mean()),
                    "fit_membership_digest": (
                        "NOT_APPLICABLE_RAW"
                        if method == "RAW"
                        else identity_digest(fit_identifiers)
                    ),
                    "evaluation_membership_digest": membership_digest,
                    "extreme_low_probability_count": int(
                        (
                            calibrated[method]
                            <= contract["near_perfect_diagnostic"][
                                "extreme_probability_threshold"
                            ]
                        ).sum()
                    ),
                    "extreme_high_probability_count": int(
                        (
                            calibrated[method]
                            >= 1
                            - contract["near_perfect_diagnostic"][
                                "extreme_probability_threshold"
                            ]
                        ).sum()
                    ),
                    **values,
                }
                metrics.append(metric_row)
                for bin_row in bins:
                    reliability.append(
                        {
                            **{
                                k: metric_row[k]
                                for k in (
                                    "project",
                                    "algorithm",
                                    "configuration",
                                    "evaluation_origin",
                                    "calibration_method",
                                    "evaluation_rows",
                                )
                            },
                            **bin_row,
                        }
                    )
            if any(
                abs(
                    raw_metric[name]
                    - next(
                        row[name]
                        for row in metrics[-3:]
                        if row["calibration_method"] == "RAW"
                    )
                )
                > 1e-15
                for name in (*PRIMARY_METRICS, *DIAGNOSTIC_METRICS)
            ):
                raise CalibrationCampaignError("RAW baseline changed")
        histories[series].extend(rows)
    if seen_groups != expected_group_order:
        raise CalibrationCampaignError("ledger order or factorial scope changed")
    if total_records != contract["source_ledger_rows"]:
        raise CalibrationCampaignError("ledger record count changed")
    return {
        "preflight": preflight,
        "metrics": metrics,
        "raw_all_origins": raw_all_origins,
        "reliability": reliability,
        "states": states,
        "ineligible": ineligible,
        "memberships": [memberships[key] for key in sorted(memberships)],
        "execution": {
            "source_probability_rows_loaded": total_records,
            "common_evaluation_units": len(metrics) // 3,
            "metric_rows": len(metrics),
            "calibrator_fits": fit_count,
            "reliability_rows": len(reliability),
        },
    }


def dispersion_rows(metrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in metrics:
        grouped[
            (row["algorithm"], row["configuration"], row["calibration_method"])
        ].append(row)
    result = []
    for key in sorted(grouped):
        rows = grouped[key]
        origins_by_project = [
            sum(row["project"] == project for row in rows)
            for project in sorted({row["project"] for row in rows})
        ]
        item: dict[str, Any] = {
            "algorithm": key[0],
            "configuration": key[1],
            "calibration_method": key[2],
            "valid_project_origin_units": len(rows),
            "projects": len({row["project"] for row in rows}),
            "origins_per_project_min": min(origins_by_project),
            "origins_per_project_max": max(origins_by_project),
        }
        for metric in (*PRIMARY_METRICS, *DIAGNOSTIC_METRICS):
            values = np.asarray([row[metric] for row in rows])
            item[f"{metric}_mean"] = float(values.mean())
            item[f"{metric}_sample_sd"] = float(values.std(ddof=1))
        result.append(item)
    return result


def holm_adjust(p_values: list[float]) -> list[float]:
    order = sorted(range(len(p_values)), key=lambda index: (p_values[index], index))
    adjusted = [0.0] * len(p_values)
    running = 0.0
    count = len(p_values)
    for rank, index in enumerate(order):
        running = max(running, min(1.0, (count - rank) * p_values[index]))
        adjusted[index] = running
    return adjusted


def paired_rank_biserial_left_better(left: np.ndarray, right: np.ndarray) -> float:
    improvement = right - left
    nonzero = improvement != 0
    if not nonzero.any():
        return 0.0
    values = improvement[nonzero]
    ranks = rankdata(np.abs(values), method="average")
    return float((ranks[values > 0].sum() - ranks[values < 0].sum()) / ranks.sum())


def paired_comparisons(metrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    project_values: dict[tuple[str, str, str, str], dict[str, float]] = defaultdict(
        dict
    )
    grouped: dict[tuple[str, str, str, str], list[float]] = defaultdict(list)
    for row in metrics:
        for metric in PRIMARY_METRICS:
            grouped[
                (
                    row["algorithm"],
                    row["configuration"],
                    row["calibration_method"],
                    row["project"],
                    metric,
                )
            ].append(row[metric])
    for (algorithm, configuration, method, project, metric), values in grouped.items():
        project_values[(algorithm, configuration, method, metric)][project] = float(
            np.mean(values)
        )
    result: list[dict[str, Any]] = []
    pairs = (("PLATT", "RAW"), ("ISOTONIC", "RAW"), ("PLATT", "ISOTONIC"))
    scopes = sorted({(row["algorithm"], row["configuration"]) for row in metrics})
    for algorithm, configuration in scopes:
        family: list[dict[str, Any]] = []
        for left_method, right_method in pairs:
            for metric in PRIMARY_METRICS:
                left_map = project_values[
                    (algorithm, configuration, left_method, metric)
                ]
                right_map = project_values[
                    (algorithm, configuration, right_method, metric)
                ]
                projects = sorted(set(left_map) & set(right_map))
                origin_counts = [
                    len(
                        grouped[
                            (
                                algorithm,
                                configuration,
                                left_method,
                                project,
                                metric,
                            )
                        ]
                    )
                    for project in projects
                ]
                left = np.asarray([left_map[project] for project in projects])
                right = np.asarray([right_map[project] for project in projects])
                difference = left - right
                if np.all(difference == 0):
                    statistic, p_value = 0.0, 1.0
                else:
                    test = wilcoxon(
                        left, right, alternative="two-sided", zero_method="wilcox"
                    )
                    statistic, p_value = float(test.statistic), float(test.pvalue)
                family.append(
                    {
                        "algorithm": algorithm,
                        "configuration": configuration,
                        "comparison": f"{left_method}_VS_{right_method}",
                        "left_method": left_method,
                        "right_method": right_method,
                        "metric": metric,
                        "paired_project_n": len(projects),
                        "origins_averaged_per_project_min": min(origin_counts),
                        "origins_averaged_per_project_max": max(origin_counts),
                        "statistic": statistic,
                        "raw_p_value": p_value,
                        "mean_left_minus_right": float(difference.mean()),
                        "median_left_minus_right": float(np.median(difference)),
                        "effect_rank_biserial_left_better": paired_rank_biserial_left_better(
                            left, right
                        ),
                        "left_wins": int((left < right).sum()),
                        "ties": int((left == right).sum()),
                        "left_losses": int((left > right).sum()),
                        "direction": (
                            "LEFT_BETTER"
                            if difference.mean() < 0
                            else "TIE"
                            if difference.mean() == 0
                            else "RIGHT_BETTER"
                        ),
                    }
                )
        adjusted = holm_adjust([row["raw_p_value"] for row in family])
        for row, value in zip(family, adjusted, strict=True):
            row["holm_adjusted_p_value"] = value
        result.extend(family)
    return result


def selection_rows(
    metrics: list[dict[str, Any]],
    dispersion: list[dict[str, Any]],
    comparisons: list[dict[str, Any]],
    contract: dict[str, Any],
) -> list[dict[str, Any]]:
    summary = {
        (r["algorithm"], r["configuration"], r["calibration_method"]): r
        for r in dispersion
    }
    tests = {
        (r["algorithm"], r["configuration"], r["comparison"], r["metric"]): r
        for r in comparisons
    }
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in metrics:
        grouped[
            (row["algorithm"], row["configuration"], row["calibration_method"])
        ].append(row)
    rule = contract["selection_rule"]
    result = []
    for algorithm in contract["algorithms"]:
        for configuration in contract["configurations"]:
            raw = summary[(algorithm, configuration, "RAW")]
            gates: dict[str, dict[str, Any]] = {}
            for method in ("PLATT", "ISOTONIC"):
                candidate = summary[(algorithm, configuration, method)]
                method_gates: dict[str, Any] = {
                    "support": len(grouped[(algorithm, configuration, method)]) == 126
                }
                for metric, threshold in (
                    ("Brier", rule["minimum_relative_brier_improvement"]),
                    ("ECE", rule["minimum_relative_ece_improvement"]),
                ):
                    relative = (
                        raw[f"{metric}_mean"] - candidate[f"{metric}_mean"]
                    ) / raw[f"{metric}_mean"]
                    test = tests[(algorithm, configuration, f"{method}_VS_RAW", metric)]
                    unit_candidate = grouped[(algorithm, configuration, method)]
                    unit_raw = {
                        (r["project"], r["evaluation_origin"]): r
                        for r in grouped[(algorithm, configuration, "RAW")]
                    }
                    large_degradations = sum(
                        row[metric]
                        > unit_raw[(row["project"], row["evaluation_origin"])][metric]
                        * (1 + rule["large_degradation_relative_threshold"])
                        for row in unit_candidate
                    ) / len(unit_candidate)
                    method_gates[f"{metric}_relative_improvement"] = relative
                    method_gates[f"{metric}_magnitude"] = relative >= threshold
                    method_gates[f"{metric}_stability"] = (
                        test["left_wins"] / test["paired_project_n"]
                        >= rule["minimum_project_win_fraction_each_primary_metric"]
                    )
                    method_gates[f"{metric}_adjusted_significance"] = (
                        test["holm_adjusted_p_value"] <= contract["inference"]["alpha"]
                    )
                    method_gates[f"{metric}_effect"] = (
                        test["effect_rank_biserial_left_better"]
                        >= rule["minimum_improvement_rank_biserial_each_primary_metric"]
                    )
                    method_gates[f"{metric}_large_degradation_fraction"] = (
                        large_degradations
                    )
                    method_gates[f"{metric}_instability"] = (
                        large_degradations
                        <= rule[
                            "maximum_fraction_large_degradations_each_primary_metric"
                        ]
                    )
                method_gates["passed"] = all(
                    value
                    for key, value in method_gates.items()
                    if key == "support"
                    or key.endswith(
                        (
                            "_magnitude",
                            "_stability",
                            "_adjusted_significance",
                            "_effect",
                            "_instability",
                        )
                    )
                )
                gates[method] = method_gates
            passing = [
                method for method in ("PLATT", "ISOTONIC") if gates[method]["passed"]
            ]
            rationale = "No calibrated method cleared every predeclared gate."
            selected = "RAW"
            if len(passing) == 1:
                selected = passing[0]
                rationale = f"{selected} alone cleared every predeclared gate."
            elif len(passing) == 2:
                iso_better = all(
                    tests[(algorithm, configuration, "PLATT_VS_ISOTONIC", metric)][
                        "holm_adjusted_p_value"
                    ]
                    <= contract["inference"]["alpha"]
                    and tests[(algorithm, configuration, "PLATT_VS_ISOTONIC", metric)][
                        "effect_rank_biserial_left_better"
                    ]
                    <= -rule["minimum_improvement_rank_biserial_each_primary_metric"]
                    for metric in PRIMARY_METRICS
                )
                platt_better = all(
                    tests[(algorithm, configuration, "PLATT_VS_ISOTONIC", metric)][
                        "holm_adjusted_p_value"
                    ]
                    <= contract["inference"]["alpha"]
                    and tests[(algorithm, configuration, "PLATT_VS_ISOTONIC", metric)][
                        "effect_rank_biserial_left_better"
                    ]
                    >= rule["minimum_improvement_rank_biserial_each_primary_metric"]
                    for metric in PRIMARY_METRICS
                )
                if iso_better:
                    selected, rationale = (
                        "ISOTONIC",
                        "Both passed; isotonic was coherently superior on both primary metrics.",
                    )
                else:
                    selected = "PLATT"
                    rationale = (
                        "Both passed; Platt was coherently superior on both primary metrics."
                        if platt_better
                        else "Both passed without coherent two-metric separation; the predeclared lower-variance Platt tie rule applied."
                    )
            result.append(
                {
                    "algorithm": algorithm,
                    "configuration": configuration,
                    "selected_calibration_state": selected,
                    "platt_passed_all_gates": gates["PLATT"]["passed"],
                    "isotonic_passed_all_gates": gates["ISOTONIC"]["passed"],
                    "platt_gate_details": json.dumps(
                        gates["PLATT"], sort_keys=True, separators=(",", ":")
                    ),
                    "isotonic_gate_details": json.dumps(
                        gates["ISOTONIC"], sort_keys=True, separators=(",", ":")
                    ),
                    "rationale": rationale,
                }
            )
    return result


def near_perfect_rows(
    metrics: list[dict[str, Any]],
    reliability: list[dict[str, Any]],
    contract: dict[str, Any],
) -> list[dict[str, Any]]:
    rule = contract["near_perfect_diagnostic"]
    bin_index: dict[tuple[str, str, str, int, str], list[dict[str, Any]]] = defaultdict(
        list
    )
    for row in reliability:
        key = (
            row["project"],
            row["algorithm"],
            row["configuration"],
            row["evaluation_origin"],
            row["calibration_method"],
        )
        bin_index[key].append(row)
    result = []
    preliminary = []
    for row in metrics:
        key = (
            row["project"],
            row["algorithm"],
            row["configuration"],
            row["evaluation_origin"],
            row["calibration_method"],
        )
        bins = bin_index[key]
        occupied = [item for item in bins if item["observation_count"]]
        near_zero_brier = row["Brier"] <= rule["approximately_zero_threshold"]
        near_zero_ece = row["ECE"] <= rule["approximately_zero_threshold"]
        extreme_fraction = (
            row["extreme_low_probability_count"] + row["extreme_high_probability_count"]
        ) / row["evaluation_rows"]
        flagged = (
            near_zero_brier
            or near_zero_ece
            or extreme_fraction
            >= rule["extreme_probability_concentration_fraction_threshold"]
        )
        prevalence_sensitive = (
            min(row["prevalence"], 1 - row["prevalence"])
            <= rule["class_imbalance_prevalence_threshold"]
        )
        sparse = any(
            item["observation_count"] <= rule["sparse_bin_count_threshold"]
            for item in occupied
        )
        preliminary.append(
            {
                "row": row,
                "near_zero_brier": near_zero_brier,
                "near_zero_ece": near_zero_ece,
                "extreme_fraction": extreme_fraction,
                "prevalence_sensitive": prevalence_sensitive,
                "sparse": sparse,
                "flagged": flagged,
            }
        )
    flagged_counts: dict[tuple[str, str, str], int] = defaultdict(int)
    for item in preliminary:
        if item["flagged"]:
            row = item["row"]
            flagged_counts[
                row["algorithm"], row["configuration"], row["calibration_method"]
            ] += 1
    repeated_keys = {key for key, count in flagged_counts.items() if count >= 2}
    for item in preliminary:
        row = item["row"]
        repeated = (
            row["algorithm"],
            row["configuration"],
            row["calibration_method"],
        ) in repeated_keys
        if item["flagged"]:
            classification = (
                "class-imbalance-sensitive"
                if item["prevalence_sensitive"]
                else "repeated/structural"
                if repeated
                else "sparse-bin-sensitive"
                if item["sparse"]
                else "suspicious/provenance-review-required"
            )
        else:
            classification = "plausible"
        result.append(
            {
                **{
                    name: row[name]
                    for name in (
                        "project",
                        "algorithm",
                        "configuration",
                        "evaluation_origin",
                        "calibration_method",
                    )
                },
                "Brier": row["Brier"],
                "ECE": row["ECE"],
                "near_zero_brier": item["near_zero_brier"],
                "near_zero_ece": item["near_zero_ece"],
                "extreme_low_probability_count": row["extreme_low_probability_count"],
                "extreme_high_probability_count": row["extreme_high_probability_count"],
                "extreme_probability_concentration": item["extreme_fraction"],
                "flagged": item["flagged"],
                "diagnostic_classification": classification,
                "leakage_conclusion": "NO_LEAKAGE_EVIDENCE_FROM_VALUE_ALONE",
            }
        )
    return result


def final_classification(selections: list[dict[str, Any]]) -> str:
    chosen = {row["selected_calibration_state"] for row in selections}
    if chosen == {"RAW"}:
        return "PASS_51_RAW_CALIBRATION_RETAINED"
    if chosen == {"PLATT"}:
        return "PASS_51_PLATT_SELECTED"
    if chosen == {"ISOTONIC"}:
        return "PASS_51_ISOTONIC_SELECTED"
    return "PASS_51_ALGORITHM_SPECIFIC_CALIBRATION_SELECTED"


def _manifest(output: Path) -> str:
    lines = []
    for path in sorted(
        p for p in output.iterdir() if p.is_file() and p.name != "MANIFEST.sha256"
    ):
        lines.append(f"{file_sha256(path)}  {path.name}")
    text = "\n".join(lines) + "\n"
    (output / "MANIFEST.sha256").write_text(text, encoding="utf-8")
    return hashlib.sha256(text.encode()).hexdigest()


def write_artifacts(
    root: Path, output: Path, contract: dict[str, Any], payload: dict[str, Any]
) -> dict[str, Any]:
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    metrics = payload["metrics"]
    dispersion = dispersion_rows(metrics)
    comparisons = paired_comparisons(metrics)
    selections = selection_rows(metrics, dispersion, comparisons, contract)
    diagnostics = near_perfect_rows(metrics, payload["reliability"], contract)
    diagnostic_flag_count = sum(row["flagged"] for row in diagnostics)
    classification = final_classification(selections)
    metric_fields = list(metrics[0])
    _write_json(output / "calibration_execution_contract.json", contract)
    _write_json(
        output / "input_probability_provenance.json",
        {
            **payload["preflight"],
            "source_path": contract["source_ledger"],
            "scientific_identity": "Sprint 50 frozen development-only raw positive-class probabilities",
            "fields": json.loads(
                (
                    root / contract["source_audit"] / "external_artifact_inventory.json"
                ).read_text()
            )["artifacts"][0]["schema"]["fields"],
            "condition_reconciliation": "3920_OF_3920",
            "calibration_fit_evaluation_distinction": "fit origins 2..K-1 versus evaluation origin K",
        },
    )
    _write_csv(
        output / "temporal_calibration_membership.csv",
        payload["memberships"],
        _ordered_fields(payload["memberships"]),
    )
    _write_csv(output / "calibration_metrics.csv", metrics, metric_fields)
    _write_csv(
        output / "raw_baseline_all_origins.csv",
        payload["raw_all_origins"],
        list(payload["raw_all_origins"][0]),
    )
    for method, name in (
        ("RAW", "raw_calibration_metrics.csv"),
        ("PLATT", "platt_calibration_metrics.csv"),
        ("ISOTONIC", "isotonic_calibration_metrics.csv"),
    ):
        subset = [row for row in metrics if row["calibration_method"] == method]
        _write_csv(output / name, subset, metric_fields)
    _write_csv(
        output / "brier_results.csv",
        [
            {k: v for k, v in row.items() if k not in {"ECE", "ROC_AUC", "PR_AUC"}}
            for row in metrics
        ],
        [name for name in metric_fields if name not in {"ECE", "ROC_AUC", "PR_AUC"}],
    )
    _write_csv(
        output / "ece_results.csv",
        [
            {k: v for k, v in row.items() if k not in {"Brier", "ROC_AUC", "PR_AUC"}}
            for row in metrics
        ],
        [name for name in metric_fields if name not in {"Brier", "ROC_AUC", "PR_AUC"}],
    )
    _write_csv(output / "dispersion_results.csv", dispersion, list(dispersion[0]))
    _write_csv(
        output / "paired_statistical_comparisons.csv", comparisons, list(comparisons[0])
    )
    _write_gzip_jsonl(
        output / "reliability_diagram_data.jsonl.gz", payload["reliability"]
    )
    _write_gzip_jsonl(output / "calibrator_states.jsonl.gz", payload["states"])
    _write_csv(
        output / "calibration_selection_decisions.csv", selections, list(selections[0])
    )
    diagnostic_fields = (
        list(diagnostics[0])
        if diagnostics
        else [
            "project",
            "algorithm",
            "configuration",
            "evaluation_origin",
            "calibration_method",
            "Brier",
            "ECE",
            "near_zero_brier",
            "near_zero_ece",
            "extreme_probability_concentration",
            "diagnostic_classification",
            "leakage_conclusion",
        ]
    )
    _write_csv(output / "near_perfect_diagnostics.csv", diagnostics, diagnostic_fields)
    _write_csv(
        output / "ineligible_calibration_units.csv",
        payload["ineligible"],
        list(payload["ineligible"][0]),
    )
    access = {
        f"{partition}_{operation}": 0
        for partition in ("T1", "T2")
        for operation in (
            "training",
            "calibration_fitting",
            "scoring",
            "threshold_selection",
            "XAI",
        )
    }
    _write_json(output / "t1_t2_access_audit.json", access)
    ledger = {
        **payload["execution"],
        "model_fits": 0,
        "model_retrains": 0,
        "hyperparameter_searches": 0,
        "threshold_optimizations": 0,
        "XAI_executions": 0,
        "T1_predictive_accesses": 0,
        "T2_predictive_accesses": 0,
        "raw_baseline_preserved": True,
    }
    _write_json(output / "execution_ledger.json", ledger)
    selection_counts = {
        method: sum(row["selected_calibration_state"] == method for row in selections)
        for method in METHODS
    }
    overall = {}
    for method in METHODS:
        rows = [row for row in metrics if row["calibration_method"] == method]
        overall[method] = {
            metric: {
                "mean": float(np.mean([row[metric] for row in rows])),
                "sample_sd": float(np.std([row[metric] for row in rows], ddof=1)),
            }
            for metric in PRIMARY_METRICS
        }
    verification = {
        "status": "PASS",
        "final_scientific_classification": classification,
        "raw_baseline_preservation": "PASS",
        "temporal_causality": (
            f"PASS_{payload['execution']['common_evaluation_units']}_OF_3528_"
            "UNITS; REMAINDER_PREDECLARED_SUPPORT_INELIGIBLE"
        ),
        "evaluation_block_self_fitting": 0,
        "future_block_fitting": 0,
        "common_evaluation_units": payload["execution"]["common_evaluation_units"],
        "paired_project_n": 14,
        "selection_counts": selection_counts,
        "near_perfect_flags": diagnostic_flag_count,
        "support_ineligible_units": len(payload["ineligible"]),
        "leakage_detected": False,
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "scikit_learn": sklearn.__version__,
        },
    }
    _write_json(output / "verification_report.json", verification)
    _write_json(
        output / "generated_artifact_inventory.json",
        {
            "large_external_artifact_created": False,
            "source_large_artifact_reused_without_modification": True,
            "source_large_artifact": contract["source_ledger"],
            "source_sha256": contract["source_ledger_sha256"],
            "compressed_machine_readable_outputs": [
                "reliability_diagram_data.jsonl.gz",
                "calibrator_states.jsonl.gz",
            ],
            "reconstruction": "Run the Sprint 51 module after verifying the frozen Sprint 50 ledger.",
        },
    )
    report_lines = [
        "# Sprint 51 development-only probability calibration",
        "",
        f"**Final scientific classification:** `{classification}`",
        "",
        "## Protocol",
        "",
        "For each project, algorithm, configuration, and evaluation origin K=3..11, Platt and isotonic mappings were fitted only on frozen raw probabilities and labels from origins 2..K-1. Origin K was then evaluated once. CV=2 remained RAW-only because no earlier out-of-time probability block exists. Strict causality follows the frozen Sprint 50-R1 `(timestamp, commit_sha)` order; fit and evaluation identities are disjoint.",
        "",
        "## Overall common-domain calibration",
        "",
        "| State | Brier mean ± SD | ECE mean ± SD |",
        "|---|---:|---:|",
    ]
    for method in METHODS:
        report_lines.append(
            f"| {method} | {overall[method]['Brier']['mean']:.6f} ± {overall[method]['Brier']['sample_sd']:.6f} | {overall[method]['ECE']['mean']:.6f} ± {overall[method]['ECE']['sample_sd']:.6f} |"
        )
    report_lines += [
        "",
        f"SD is empirical dispersion across {payload['execution']['common_evaluation_units']:,} valid project-origin-configuration-algorithm units per state, not a standard error or confidence interval.",
        "",
        "## Selection",
        "",
        f"RAW/Platt/isotonic selections across 28 algorithm/configuration scopes: {selection_counts['RAW']}/{selection_counts['PLATT']}/{selection_counts['ISOTONIC']}.",
        "Exact joint magnitude, stability, Holm-adjusted Wilcoxon, rank-biserial, support, and instability gates are in `calibration_selection_decisions.csv`.",
        "",
        "## Integrity",
        "",
        f"All {payload['execution']['calibrator_fits']} calibrator fits were earlier-block-only. {len(payload['ineligible'])} unit was excluded for all three comparison states by the predeclared support rule and remains preserved in the all-origin RAW baseline. T1/T2 training, calibration fitting, scoring, threshold selection, and XAI counters are zero. No model retraining, hyperparameter search, threshold optimization, or XAI occurred.",
        "",
        "## Near-perfect diagnostic",
        "",
        f"Flagged method-unit results: {diagnostic_flag_count}. A near-zero value alone was not classified as leakage; exact classifications for all valid units are retained in `near_perfect_diagnostics.csv`.",
        "",
        "## Statistical comparison",
        "",
        "Two-sided paired Wilcoxon signed-rank tests use 14 project means after averaging CV=3..11 within project. Holm correction covers six method-pair × primary-metric tests within each algorithm/configuration. Effect size is paired rank-biserial correlation. P-values alone do not determine selection.",
        "",
        "## Recommendation",
        "",
        "Sprint 52 should consume only the selected per-scope calibration state frozen here, retain RAW where calibration did not clear every gate, and continue to prohibit T1/T2 and XAI unless separately prospectively authorized.",
        "",
    ]
    text = "\n".join(report_lines)
    (output / "REPORT.md").write_text(text, encoding="utf-8")
    (output / "FINAL_HUMAN_REVIEW_REPORT.md").write_text(text, encoding="utf-8")
    manifest_sha = _manifest(output)
    return {**verification, "manifest_sha256": manifest_sha, "overall": overall}


def verify_manifest(output: Path) -> dict[str, Any]:
    entries = _manifest_entries(output / "MANIFEST.sha256")
    failures = [
        name
        for name, expected in entries.items()
        if not (output / name).is_file() or file_sha256(output / name) != expected
    ]
    if failures:
        raise CalibrationCampaignError(f"Sprint 51 manifest failure: {failures}")
    return {
        "status": "PASS",
        "entries": len(entries),
        "manifest_sha256": file_sha256(output / "MANIFEST.sha256"),
    }


def run(root: Path, output: Path) -> dict[str, Any]:
    contract = load_contract(root)
    with threadpool_limits(limits=contract["numeric_thread_limit"]):
        payload = execute(root, contract)
    result = write_artifacts(root, output, contract, payload)
    result["manifest_verification"] = verify_manifest(output)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output.resolve() if args.output else root / OUTPUT_REL
    result = verify_manifest(output) if args.verify else run(root, output)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
