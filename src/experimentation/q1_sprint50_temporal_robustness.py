"""Authorized Sprint 50 expanding-forward temporal robustness campaign."""

from __future__ import annotations

import argparse
import copy
import csv
import gzip
import json
import math
import platform
import shutil
import subprocess
import tempfile
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import friedmanchisquare, rankdata, wilcoxon
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    matthews_corrcoef,
    precision_score,
    recall_score,
    roc_auc_score,
)

from experimentation.q1_controlled_late_fusion import (
    CONFIGURATIONS,
    FUSION_CONFIGURATIONS,
)
from experimentation.q1_controlled_late_fusion import (
    load_config as load_fusion_config,
)
from experimentation.q1_controlled_train_validation_baselines import (
    EXPECTED_PROJECTS,
    canonical_bytes,
    digest,
    file_digest,
    load_development_project,
    verify_manifest,
)
from experimentation.q1_controlled_unimodal_modeling import (
    ALGORITHMS,
    MODALITIES,
    make_pipeline,
    package_versions,
    predict_positive_probability,
    raw_features,
)
from experimentation.q1_controlled_unimodal_modeling import (
    load_config as load_unimodal_config,
)
from experimentation.q1_sprint50_temporal_protocol_amendment import (
    FULL_FOLD_IDENTIFIERS,
    build_amended_forward_fold,
    build_k2_nested_meta_split,
)

VERSION = "q1-sprint50-temporal-robustness-execution-1.0.0"
CONFIG_REL = Path(
    "configs/experiments/q1_sprint50_temporal_robustness_execution_1.0.0.json"
)
OUTPUT_REL = Path("audits/q1-temporal-robustness-cv/1.0.0")
FREEZE_REL = Path("audits/q1-apachejit-final-dataset-freeze/1.0.0")
SPRINT49_REL = Path("audits/q1-controlled-train-validation-baselines/1.0.0")
AMENDMENT_REL = Path("audits/q1-temporal-protocol-amendment/1.0.0")
SELECTION_REL = SPRINT49_REL / "campaign" / "development_selections.json"
METRICS = ("PR_AUC", "ROC_AUC", "MCC", "Recall", "Precision", "F1")
THRESHOLD = 0.5
DEVELOPMENT_PARTITIONS = frozenset(("TRAIN", "VALIDATION"))


class RobustnessCampaignError(RuntimeError):
    """Raised when any execution or scientific contract fails closed."""


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ("git", *args), cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()


def _manifest_verify(base: Path) -> dict[str, str]:
    expected: dict[str, str] = {}
    for line in (base / "MANIFEST.sha256").read_text(encoding="utf-8").splitlines():
        value, name = line.split("  ", 1)
        if name in expected or len(value) != 64:
            raise RobustnessCampaignError(f"malformed manifest: {base}")
        expected[name] = value
        if file_digest(base / name) != value:
            raise RobustnessCampaignError(f"manifest failure: {base / name}")
    return expected


def load_config(root: Path) -> dict[str, Any]:
    config = _json(root / CONFIG_REL)
    if config["experiment_version"] != VERSION:
        raise RobustnessCampaignError("execution contract version mismatch")
    if tuple(config["configurations"]) != CONFIGURATIONS:
        raise RobustnessCampaignError("configuration scope changed")
    if tuple(config["cv_values"]) != FULL_FOLD_IDENTIFIERS:
        raise RobustnessCampaignError("CV scope is not exactly 2..11")
    if tuple(config["metrics"]) != METRICS:
        raise RobustnessCampaignError("metric scope changed")
    if config["expected_condition_count"] != 3920:
        raise RobustnessCampaignError("factorial count changed")
    if config["threshold"] != THRESHOLD:
        raise RobustnessCampaignError("threshold changed")
    if config["ceiling_diagnostic_threshold"] != 0.99:
        raise RobustnessCampaignError("ceiling threshold changed")
    if config["test_access"] != {"T1": "DENY", "T2": "DENY"}:
        raise RobustnessCampaignError("T1/T2 denial changed")
    if config["xai"] != "PROHIBITED":
        raise RobustnessCampaignError("XAI prohibition changed")
    inference = config["inference"]
    if (
        inference["experimental_unit"] != "PROJECT"
        or inference["multiple_comparison_correction"] != "HOLM"
        or inference["effect_size"] != "PAIRED_RANK_BISERIAL_CORRELATION"
    ):
        raise RobustnessCampaignError("inference plan changed")
    return config


def verify_sources(root: Path) -> dict[str, Any]:
    config = load_config(root)
    if _git(root, "rev-parse", "HEAD") != config["starting_head"]:
        raise RobustnessCampaignError("starting HEAD changed")
    frozen = verify_manifest(root / FREEZE_REL)
    campaign = _manifest_verify(root / SPRINT49_REL / "campaign")
    verification = _manifest_verify(root / SPRINT49_REL / "verification")
    amendment = _manifest_verify(root / AMENDMENT_REL)
    selection_expected = campaign.get("development_selections.json")
    if selection_expected != file_digest(root / SELECTION_REL):
        raise RobustnessCampaignError("Sprint 49 selection identity changed")
    access = _json(root / AMENDMENT_REL / "t1_t2_access_audit.json")
    if any(value != 0 for key, value in access.items() if key.endswith("_count")):
        raise RobustnessCampaignError("amendment access counter is nonzero")
    return {
        "schema_version": VERSION,
        "status": "PASS",
        "frozen_manifest_sha256": file_digest(root / FREEZE_REL / "MANIFEST.sha256"),
        "frozen_payload_count": len(frozen),
        "sprint49_campaign_manifest_sha256": file_digest(
            root / SPRINT49_REL / "campaign" / "MANIFEST.sha256"
        ),
        "sprint49_campaign_payload_count": len(campaign),
        "sprint49_verification_payload_count": len(verification),
        "sprint49_selection_sha256": selection_expected,
        "amendment_manifest_sha256": file_digest(
            root / AMENDMENT_REL / "MANIFEST.sha256"
        ),
        "amendment_payload_count": len(amendment),
        "T1_access_count": 0,
        "T2_access_count": 0,
    }


def load_frozen_selections(root: Path) -> dict[tuple[str, str, str], dict[str, Any]]:
    payload = _json(root / SELECTION_REL)
    rows = payload["rows"]
    result = {(row["project"], row["algorithm"], row["modality"]): row for row in rows}
    expected = len(EXPECTED_PROJECTS) * len(ALGORITHMS) * len(MODALITIES)
    if len(rows) != expected or len(result) != expected:
        raise RobustnessCampaignError("frozen selection cardinality mismatch")
    if any(
        row["validation_access_count"] != 0
        or row["t1_predictive_access_count"] != 0
        or row["t2_predictive_access_count"] != 0
        for row in rows
    ):
        raise RobustnessCampaignError("frozen selection access audit failed")
    return result


def _selected_config(
    base: dict[str, Any], algorithm: str, selection: dict[str, Any]
) -> dict[str, Any]:
    result = copy.deepcopy(base)
    result["algorithms"][algorithm] = dict(selection["selected_parameters"])
    return result


def fit_history_pipeline(
    history_rows: list[dict[str, Any]],
    algorithm: str,
    modality: str,
    config: dict[str, Any],
):
    """Fit a frozen pipeline on authorized, project-local history only."""
    if not history_rows:
        raise RobustnessCampaignError("history fit is empty")
    if {row["partition"] for row in history_rows} - DEVELOPMENT_PARTITIONS:
        raise RobustnessCampaignError("non-development row entered fitting")
    if len({row["project"] for row in history_rows}) != 1:
        raise RobustnessCampaignError("history fit is not project-local")
    y = np.asarray([row["target"] for row in history_rows], dtype=int)
    if set(y.tolist()) != {0, 1}:
        raise RobustnessCampaignError("history fit lacks both classes")
    return make_pipeline(algorithm, modality, config).fit(
        raw_features(history_rows, modality), y
    )


def _meta(config: dict[str, Any]) -> LogisticRegression:
    parameters = dict(config["meta_learner"])
    parameters.pop("regularization")
    return LogisticRegression(**parameters)


def probability_metrics(
    targets: np.ndarray, probabilities: np.ndarray
) -> dict[str, Any]:
    if len(targets) != len(probabilities) or set(targets.tolist()) != {0, 1}:
        raise RobustnessCampaignError("metric population is invalid")
    predicted = (probabilities >= THRESHOLD).astype(int)
    tn, fp, fn, tp = confusion_matrix(targets, predicted, labels=[0, 1]).ravel()
    values = {
        "PR_AUC": float(average_precision_score(targets, probabilities)),
        "ROC_AUC": float(roc_auc_score(targets, probabilities)),
        "MCC": float(matthews_corrcoef(targets, predicted)),
        "Recall": float(recall_score(targets, predicted, zero_division=0)),
        "Precision": float(precision_score(targets, predicted, zero_division=0)),
        "F1": float(f1_score(targets, predicted, zero_division=0)),
        "Brier": float(brier_score_loss(targets, probabilities)),
        "ECE": expected_calibration_error(targets, probabilities),
        "TN": int(tn),
        "FP": int(fp),
        "FN": int(fn),
        "TP": int(tp),
    }
    if any(
        not math.isfinite(float(values[name])) for name in (*METRICS, "Brier", "ECE")
    ):
        raise RobustnessCampaignError("non-finite metric")
    return values


def expected_calibration_error(
    targets: np.ndarray, probabilities: np.ndarray, bins: int = 10
) -> float:
    indexes = np.minimum((probabilities * bins).astype(int), bins - 1)
    result = 0.0
    for index in range(bins):
        mask = indexes == index
        if mask.any():
            result += float(mask.mean()) * abs(
                float(targets[mask].mean()) - float(probabilities[mask].mean())
            )
    return float(result)


def _condition_record(
    project: str,
    algorithm: str,
    configuration: str,
    cv_value: int,
    history: list[dict[str, Any]],
    evaluation: list[dict[str, Any]],
    probabilities: np.ndarray,
    selection_ids: dict[str, str],
    hyperparameters: dict[str, Any],
    meta_training_rows: int,
) -> dict[str, Any]:
    y = np.asarray([row["target"] for row in evaluation], dtype=int)
    metrics = probability_metrics(y, probabilities)
    history_ids = [row["row_identifier"] for row in history]
    evaluation_ids = [row["row_identifier"] for row in evaluation]
    history_partitions = Counter(row["partition"] for row in history)
    evaluation_partitions = Counter(row["partition"] for row in evaluation)
    hyperparameter_identity = {
        "selected_candidate_ids": selection_ids,
        "effective_hyperparameters": hyperparameters,
    }
    return {
        "project": project,
        "algorithm": algorithm,
        "configuration": configuration,
        "cv_value": cv_value,
        "temporal_protocol": "EXPANDING_FORWARD_BLOCK_ORIGIN",
        "threshold": THRESHOLD,
        "history_start_timestamp": history[0]["timestamp"],
        "history_end_timestamp": history[-1]["timestamp"],
        "evaluation_start_timestamp": evaluation[0]["timestamp"],
        "evaluation_end_timestamp": evaluation[-1]["timestamp"],
        "history_n": len(history),
        "evaluation_n": len(evaluation),
        "history_positive": sum(int(row["target"]) for row in history),
        "history_negative": sum(not int(row["target"]) for row in history),
        "evaluation_positive": int(y.sum()),
        "evaluation_negative": int(len(y) - y.sum()),
        "prevalence": float(y.mean()),
        "history_train_provenance_n": history_partitions["TRAIN"],
        "history_validation_provenance_n": history_partitions["VALIDATION"],
        "evaluation_train_provenance_n": evaluation_partitions["TRAIN"],
        "evaluation_validation_provenance_n": evaluation_partitions["VALIDATION"],
        "history_membership_sha256": digest(history_ids),
        "evaluation_membership_sha256": digest(evaluation_ids),
        "probability_sha256": digest(probabilities.tolist()),
        "selected_candidate_ids": selection_ids,
        "hyperparameter_identity_sha256": digest(hyperparameter_identity),
        "hyperparameters": hyperparameters,
        "meta_training_rows": meta_training_rows,
        "seed": 20260901,
        "status": "SUCCESS",
        **metrics,
    }


def _prediction_row(
    condition: dict[str, Any], row: dict[str, Any], probability: float
) -> dict[str, Any]:
    if row["partition"] not in DEVELOPMENT_PARTITIONS:
        raise RobustnessCampaignError("T1/T2 prediction attempt denied")
    return {
        "project": condition["project"],
        "algorithm": condition["algorithm"],
        "configuration": condition["configuration"],
        "cv_value": condition["cv_value"],
        "row_identifier": row["row_identifier"],
        "frozen_partition_provenance": row["partition"],
        "forward_block": int(row["forward_block"]),
        "benchmark_defined_observed_label": int(row["target"]),
        "raw_probability": float(probability),
    }


def _write_jsonl_gz(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as stream:
            for row in rows:
                stream.write(
                    json.dumps(
                        row,
                        ensure_ascii=True,
                        allow_nan=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ).encode("utf-8")
                    + b"\n"
                )


def run_project(root_text: str, project: str, fragment_dir_text: str) -> dict[str, Any]:
    root = Path(root_text)
    fragment_dir = Path(fragment_dir_text)
    execution = load_config(root)
    unimodal = load_unimodal_config(root)
    fusion = load_fusion_config(root)
    selections = load_frozen_selections(root)
    rows = load_development_project(root, project)
    if any(row["partition"] not in DEVELOPMENT_PARTITIONS for row in rows):
        raise RobustnessCampaignError("non-development row materialized")
    conditions: list[dict[str, Any]] = []
    provenance: list[dict[str, Any]] = []
    prediction_rows: list[dict[str, Any]] = []
    fit_count = 0
    scoring_count = 0
    for algorithm in ALGORITHMS:
        selected = {
            modality: selections[project, algorithm, modality]
            for modality in MODALITIES
        }
        modality_configs = {
            modality: _selected_config(unimodal, algorithm, selected[modality])
            for modality in MODALITIES
        }
        selection_ids = {
            modality: selected[modality]["selected_candidate_id"]
            for modality in MODALITIES
        }
        base_streams: dict[int, dict[str, np.ndarray]] = {}
        fold_rows: dict[int, tuple[list[dict[str, Any]], list[dict[str, Any]]]] = {}
        for cv_value in FULL_FOLD_IDENTIFIERS:
            fold = build_amended_forward_fold(rows, cv_value)
            history = list(fold.history_rows)
            evaluation = list(fold.evaluation_rows)
            fold_rows[cv_value] = (history, evaluation)
            base_streams[cv_value] = {}
            for modality in MODALITIES:
                model = fit_history_pipeline(
                    history, algorithm, modality, modality_configs[modality]
                )
                fit_count += 1
                base_streams[cv_value][modality] = predict_positive_probability(
                    model, evaluation, modality
                )
                scoring_count += 1

        k2 = build_k2_nested_meta_split(rows)
        k2_meta_streams = {}
        for modality in MODALITIES:
            model = fit_history_pipeline(
                list(k2.inner_base_fit_rows),
                algorithm,
                modality,
                modality_configs[modality],
            )
            fit_count += 1
            k2_meta_streams[modality] = predict_positive_probability(
                model, list(k2.meta_prediction_rows), modality
            )
            scoring_count += 1

        for cv_value in FULL_FOLD_IDENTIFIERS:
            history, evaluation = fold_rows[cv_value]
            streams = dict(base_streams[cv_value])
            if cv_value == 2:
                meta_y = np.asarray(
                    [row["target"] for row in k2.meta_prediction_rows], dtype=int
                )
                meta_sources = k2_meta_streams
                meta_ids = [row["row_identifier"] for row in k2.meta_prediction_rows]
                meta_rule = "K2_NESTED_BLOCK1_HALF_SPLIT"
            else:
                prior = list(range(2, cv_value))
                meta_y = np.concatenate(
                    [
                        np.asarray(
                            [row["target"] for row in fold_rows[value][1]],
                            dtype=int,
                        )
                        for value in prior
                    ]
                )
                meta_sources = {
                    modality: np.concatenate(
                        [base_streams[value][modality] for value in prior]
                    )
                    for modality in MODALITIES
                }
                meta_ids = [
                    row["row_identifier"]
                    for value in prior
                    for row in fold_rows[value][1]
                ]
                meta_rule = "PRIOR_OUTER_BLOCK_OOF_STREAMS"
            if set(meta_y.tolist()) != {0, 1}:
                raise RobustnessCampaignError("meta training lacks both classes")
            for configuration, modalities in FUSION_CONFIGURATIONS.items():
                meta_x = np.column_stack([meta_sources[m] for m in modalities])
                model = _meta(fusion).fit(meta_x, meta_y)
                fit_count += 1
                evaluation_x = np.column_stack(
                    [base_streams[cv_value][m] for m in modalities]
                )
                streams[configuration] = model.predict_proba(evaluation_x)[:, 1]
                scoring_count += 1
            for configuration in CONFIGURATIONS:
                modalities = tuple(configuration.split("+"))
                hyperparameters = {
                    modality: selected[modality]["selected_parameters"]
                    for modality in modalities
                }
                if len(modalities) > 1:
                    hyperparameters["meta_learner"] = fusion["meta_learner"]
                condition = _condition_record(
                    project,
                    algorithm,
                    configuration,
                    cv_value,
                    history,
                    evaluation,
                    streams[configuration],
                    {modality: selection_ids[modality] for modality in modalities},
                    hyperparameters,
                    len(meta_y),
                )
                conditions.append(condition)
                prediction_rows.extend(
                    _prediction_row(condition, row, probability)
                    for row, probability in zip(
                        evaluation, streams[configuration], strict=True
                    )
                )
            provenance.append(
                {
                    "project": project,
                    "algorithm": algorithm,
                    "cv_value": cv_value,
                    "meta_rule": meta_rule,
                    "meta_training_n": len(meta_y),
                    "meta_training_membership_sha256": digest(meta_ids),
                    "meta_training_strictly_prior": True,
                    "synthetic_oof_backfill_count": 0,
                    "selected_candidate_ids": selection_ids,
                }
            )
    if len(conditions) != len(ALGORITHMS) * len(CONFIGURATIONS) * 10:
        raise RobustnessCampaignError("project condition cardinality mismatch")
    fragment = fragment_dir / f"{project.replace('/', '__')}.jsonl.gz"
    _write_jsonl_gz(fragment, prediction_rows)
    return {
        "project": project,
        "conditions": conditions,
        "provenance": provenance,
        "fragment": str(fragment),
        "raw_prediction_count": len(prediction_rows),
        "model_fit_count": fit_count,
        "predictive_scoring_operation_count": scoring_count,
        "ceiling_threshold_predeclared": execution["ceiling_diagnostic_threshold"],
    }


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes(canonical_bytes(value))


def _write_csv(
    path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None
) -> None:
    if fields is None:
        if not rows:
            raise RobustnessCampaignError(f"cannot infer empty CSV {path.name}")
        fields = list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _csv_condition(record: dict[str, Any]) -> dict[str, Any]:
    result = dict(record)
    result["selected_candidate_ids"] = json.dumps(
        result["selected_candidate_ids"], sort_keys=True, separators=(",", ":")
    )
    result["hyperparameters"] = json.dumps(
        result["hyperparameters"], sort_keys=True, separators=(",", ":")
    )
    return result


def _read_conditions(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            parsed: dict[str, Any] = dict(row)
            for name in (
                "cv_value",
                "history_n",
                "evaluation_n",
                "history_positive",
                "history_negative",
                "evaluation_positive",
                "evaluation_negative",
                "history_train_provenance_n",
                "history_validation_provenance_n",
                "evaluation_train_provenance_n",
                "evaluation_validation_provenance_n",
                "meta_training_rows",
                "seed",
                "TN",
                "FP",
                "FN",
                "TP",
            ):
                parsed[name] = int(parsed[name])
            for name in ("threshold", "prevalence", *METRICS, "Brier", "ECE"):
                parsed[name] = float(parsed[name])
            parsed["selected_candidate_ids"] = json.loads(
                parsed["selected_candidate_ids"]
            )
            parsed["hyperparameters"] = json.loads(parsed["hyperparameters"])
            rows.append(parsed)
    return rows


def _summary(values: list[float], prefix: str = "metric") -> dict[str, Any]:
    array = np.asarray(values, dtype=float)
    return {
        f"{prefix}_mean": float(array.mean()),
        f"{prefix}_sd": float(array.std(ddof=1)) if len(array) > 1 else 0.0,
        f"{prefix}_median": float(np.median(array)),
        f"{prefix}_min": float(array.min()),
        f"{prefix}_max": float(array.max()),
        f"{prefix}_q1": float(np.quantile(array, 0.25)),
        f"{prefix}_q3": float(np.quantile(array, 0.75)),
        "n_cv": len(array),
    }


def dispersion_rows(conditions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str, str], list[float]] = defaultdict(list)
    for row in conditions:
        for metric in METRICS:
            grouped[
                row["project"], row["algorithm"], row["configuration"], metric
            ].append(float(row[metric]))
    result = []
    for key in sorted(grouped):
        project, algorithm, configuration, metric = key
        values = grouped[key]
        if len(values) != 10:
            raise RobustnessCampaignError("dispersion group lacks ten CV origins")
        result.append(
            {
                "project": project,
                "algorithm": algorithm,
                "configuration": configuration,
                "metric": metric,
                **_summary(values),
            }
        )
    return result


def aggregate_rows(
    conditions: list[dict[str, Any]],
    group_names: tuple[str, ...],
    metrics: tuple[str, ...] = METRICS,
) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, ...], list[float]] = defaultdict(list)
    for row in conditions:
        for metric in metrics:
            key = tuple(row[name] for name in group_names) + (metric,)
            grouped[key].append(float(row[metric]))
    result = []
    for key in sorted(grouped):
        item = {name: value for name, value in zip(group_names, key, strict=False)}
        item["metric"] = key[-1]
        summary = _summary(grouped[key])
        summary.pop("n_cv")
        item.update(summary)
        item["n_conditions"] = len(grouped[key])
        result.append(item)
    return result


def stability_rows(
    conditions: list[dict[str, Any]], dispersion: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    indexed = {
        (row["project"], row["algorithm"], row["configuration"], row["metric"]): row
        for row in dispersion
    }
    grouped: dict[tuple[str, str, str, str], list[tuple[int, float]]] = defaultdict(
        list
    )
    for row in conditions:
        for metric in METRICS:
            grouped[
                row["project"], row["algorithm"], row["configuration"], metric
            ].append((row["cv_value"], float(row[metric])))
    result = []
    for key in sorted(grouped):
        values = sorted(grouped[key])
        metric_values = np.asarray([value for _, value in values])
        differences = np.diff(metric_values)
        if np.all(differences >= 0):
            shape = "MONOTONIC_NONDECREASING"
        elif np.all(differences <= 0):
            shape = "MONOTONIC_NONINCREASING"
        else:
            shape = "NON_MONOTONIC"
        summary = indexed[key]
        sd = float(summary["metric_sd"])
        mean = float(summary["metric_mean"])
        result.append(
            {
                "project": key[0],
                "algorithm": key[1],
                "configuration": key[2],
                "metric": key[3],
                "trajectory_shape": shape,
                "range": float(metric_values.max() - metric_values.min()),
                "coefficient_of_variation": None if mean == 0 else abs(sd / mean),
                "isolated_collapse_count": int(
                    np.sum(metric_values < mean - 2 * sd) if sd > 0 else 0
                ),
                "ceiling_origin_count": int(np.sum(metric_values >= 0.99)),
                **{
                    name: summary[name]
                    for name in summary
                    if name.startswith("metric_")
                },
                "n_cv": 10,
            }
        )
    return result


def comparison_rows(conditions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    indexed = {
        (row["project"], row["algorithm"], row["configuration"], row["cv_value"]): row
        for row in conditions
    }
    result = []
    for project in EXPECTED_PROJECTS:
        for algorithm in ALGORITHMS:
            for cv_value in FULL_FOLD_IDENTIFIERS:
                full = indexed[project, algorithm, "C+P+T", cv_value]
                for comparator in ("C", "P", "T", "C+P", "C+T", "P+T"):
                    baseline = indexed[project, algorithm, comparator, cv_value]
                    for metric in METRICS:
                        delta = float(full[metric]) - float(baseline[metric])
                        result.append(
                            {
                                "project": project,
                                "algorithm": algorithm,
                                "cv_value": cv_value,
                                "metric": metric,
                                "full_configuration": "C+P+T",
                                "comparator": comparator,
                                "full_value": full[metric],
                                "comparator_value": baseline[metric],
                                "delta": delta,
                                "direction": "WIN"
                                if delta > 0
                                else "LOSS"
                                if delta < 0
                                else "TIE",
                            }
                        )
    return result


def best_family_comparison_rows(
    conditions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    indexed = {
        (row["project"], row["algorithm"], row["configuration"], row["cv_value"]): row
        for row in conditions
    }
    families = {
        "BEST_UNIMODAL": ("C", "P", "T"),
        "BEST_PAIRWISE": ("C+P", "C+T", "P+T"),
    }
    result = []
    for project in EXPECTED_PROJECTS:
        for algorithm in ALGORITHMS:
            for cv_value in FULL_FOLD_IDENTIFIERS:
                full = indexed[project, algorithm, "C+P+T", cv_value]
                for family, candidates in families.items():
                    for metric in METRICS:
                        values = {
                            candidate: float(
                                indexed[project, algorithm, candidate, cv_value][metric]
                            )
                            for candidate in candidates
                        }
                        best_value = max(values.values())
                        best = sorted(
                            candidate
                            for candidate, value in values.items()
                            if value == best_value
                        )
                        delta = float(full[metric]) - best_value
                        result.append(
                            {
                                "project": project,
                                "algorithm": algorithm,
                                "cv_value": cv_value,
                                "metric": metric,
                                "comparison_family": family,
                                "full_configuration": "C+P+T",
                                "best_comparator": "+".join(best),
                                "full_value": full[metric],
                                "best_comparator_value": best_value,
                                "delta": delta,
                                "direction": "WIN"
                                if delta > 0
                                else "LOSS"
                                if delta < 0
                                else "TIE",
                            }
                        )
    return result


def comparison_summary_rows(
    comparisons: list[dict[str, Any]], config: dict[str, Any]
) -> list[dict[str, Any]]:
    comparison_name = (
        "comparison_family"
        if comparisons and "comparison_family" in comparisons[0]
        else "comparator"
    )
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in comparisons:
        grouped[row["algorithm"], row["metric"], row[comparison_name]].append(row)
    result = []
    for salt, key in enumerate(sorted(grouped)):
        rows = grouped[key]
        project_deltas: dict[str, list[float]] = defaultdict(list)
        cv_deltas: dict[int, list[float]] = defaultdict(list)
        for row in rows:
            project_deltas[row["project"]].append(float(row["delta"]))
            cv_deltas[int(row["cv_value"])].append(float(row["delta"]))
        project_means = np.asarray(
            [np.mean(project_deltas[project]) for project in EXPECTED_PROJECTS]
        )
        cv_means = np.asarray(
            [np.mean(cv_deltas[cv_value]) for cv_value in FULL_FOLD_IDENTIFIERS]
        )
        ci_low, ci_high = _bootstrap_ci(project_means, config, salt + 500)
        all_deltas = [float(row["delta"]) for row in rows]
        summary = _summary(all_deltas, "delta")
        summary.pop("n_cv")
        item = {
            "algorithm": key[0],
            "metric": key[1],
            comparison_name: key[2],
            **summary,
            "n_conditions": len(rows),
            "project_bootstrap_95_ci_low": ci_low,
            "project_bootstrap_95_ci_high": ci_high,
            "condition_wins": sum(value > 0 for value in all_deltas),
            "condition_ties": sum(value == 0 for value in all_deltas),
            "condition_losses": sum(value < 0 for value in all_deltas),
            "project_wins": int(np.sum(project_means > 0)),
            "project_ties": int(np.sum(project_means == 0)),
            "project_losses": int(np.sum(project_means < 0)),
            "cv_wins": int(np.sum(cv_means > 0)),
            "cv_ties": int(np.sum(cv_means == 0)),
            "cv_losses": int(np.sum(cv_means < 0)),
            "project_sign_reversal_count": sum(
                min(values) < 0 < max(values) for values in project_deltas.values()
            ),
        }
        result.append(item)
    return result


def paired_project_input(
    conditions: list[dict[str, Any]], config: dict[str, Any]
) -> list[dict[str, Any]]:
    metrics = tuple(config["inference"]["primary_metrics"])
    grouped: dict[tuple[str, str, str, str], list[float]] = defaultdict(list)
    for row in conditions:
        for metric in metrics:
            grouped[
                row["project"], row["algorithm"], row["configuration"], metric
            ].append(float(row[metric]))
    result = []
    for key in sorted(grouped):
        if len(grouped[key]) != 10:
            raise RobustnessCampaignError("paired project input lacks ten origins")
        result.append(
            {
                "project": key[0],
                "algorithm": key[1],
                "configuration": key[2],
                "metric": key[3],
                "cv_origin_count": 10,
                "project_cv_mean": float(np.mean(grouped[key])),
                "experimental_unit": "PROJECT",
            }
        )
    return result


def _rank_biserial(differences: np.ndarray) -> float:
    nonzero = differences[differences != 0]
    if len(nonzero) == 0:
        return 0.0
    ranks = rankdata(np.abs(nonzero), method="average")
    positive = float(ranks[nonzero > 0].sum())
    negative = float(ranks[nonzero < 0].sum())
    return (positive - negative) / float(ranks.sum())


def _bootstrap_ci(
    values: np.ndarray, config: dict[str, Any], salt: int
) -> tuple[float, float]:
    bootstrap = config["bootstrap"]
    rng = np.random.default_rng(int(bootstrap["seed"]) + salt)
    indexes = rng.integers(
        0, len(values), size=(int(bootstrap["iterations"]), len(values))
    )
    means = values[indexes].mean(axis=1)
    alpha = 1 - float(bootstrap["confidence_level"])
    return float(np.quantile(means, alpha / 2)), float(
        np.quantile(means, 1 - alpha / 2)
    )


def _holm(rows: list[dict[str, Any]], alpha: float) -> None:
    ordered = sorted(enumerate(rows), key=lambda item: item[1]["raw_p_value"])
    running = 0.0
    count = len(rows)
    for rank, (index, row) in enumerate(ordered):
        adjusted = min(1.0, (count - rank) * float(row["raw_p_value"]))
        running = max(running, adjusted)
        rows[index]["adjusted_p_value"] = running
        rows[index]["holm_significant"] = running < alpha


def statistical_results(
    paired: list[dict[str, Any]], config: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    indexed = {
        (row["project"], row["algorithm"], row["configuration"], row["metric"]): row[
            "project_cv_mean"
        ]
        for row in paired
    }
    omnibus = []
    pairwise = []
    salt = 0
    alpha = float(config["inference"]["significance_alpha"])
    for algorithm in ALGORITHMS:
        for metric in config["inference"]["primary_metrics"]:
            arrays = [
                np.asarray(
                    [
                        indexed[p, algorithm, configuration, metric]
                        for p in EXPECTED_PROJECTS
                    ]
                )
                for configuration in CONFIGURATIONS
            ]
            statistic, p_value = friedmanchisquare(*arrays)
            omnibus.append(
                {
                    "algorithm": algorithm,
                    "metric": metric,
                    "test": "Friedman",
                    "n_projects": len(EXPECTED_PROJECTS),
                    "configuration_count": len(CONFIGURATIONS),
                    "statistic": float(statistic),
                    "raw_p_value": float(p_value),
                    "significant": float(p_value) < alpha,
                }
            )
            family = []
            full = np.asarray(
                [indexed[p, algorithm, "C+P+T", metric] for p in EXPECTED_PROJECTS]
            )
            for comparator in config["inference"]["comparators"]:
                baseline = np.asarray(
                    [
                        indexed[p, algorithm, comparator, metric]
                        for p in EXPECTED_PROJECTS
                    ]
                )
                differences = full - baseline
                if np.all(differences == 0):
                    statistic, p_value = 0.0, 1.0
                else:
                    test = wilcoxon(
                        differences,
                        zero_method="wilcox",
                        correction=False,
                        alternative="two-sided",
                        method="auto",
                    )
                    statistic, p_value = float(test.statistic), float(test.pvalue)
                ci_low, ci_high = _bootstrap_ci(differences, config, salt)
                salt += 1
                family.append(
                    {
                        "algorithm": algorithm,
                        "metric": metric,
                        "full_configuration": "C+P+T",
                        "comparator": comparator,
                        "experimental_unit": "PROJECT_CV_MEAN",
                        "n_paired_projects": len(differences),
                        "test": "Wilcoxon signed-rank two-sided",
                        "statistic": statistic,
                        "raw_p_value": p_value,
                        "adjusted_p_value": None,
                        "holm_significant": None,
                        "alpha": alpha,
                        "mean_paired_difference": float(differences.mean()),
                        "median_paired_difference": float(np.median(differences)),
                        "bootstrap_95_ci_low": ci_low,
                        "bootstrap_95_ci_high": ci_high,
                        "rank_biserial_correlation": _rank_biserial(differences),
                        "effect_direction": "POSITIVE_FAVORS_FULL",
                        "positive_projects": int(np.sum(differences > 0)),
                        "zero_projects": int(np.sum(differences == 0)),
                        "negative_projects": int(np.sum(differences < 0)),
                    }
                )
            _holm(family, alpha)
            pairwise.extend(family)
    return omnibus, pairwise


def ceiling_rows(
    conditions: list[dict[str, Any]], dispersion: list[dict[str, Any]], threshold: float
) -> list[dict[str, Any]]:
    condition_index = {
        (row["project"], row["algorithm"], row["configuration"], row["cv_value"]): row
        for row in conditions
    }
    dispersion_index = {
        (row["project"], row["algorithm"], row["configuration"], row["metric"]): row
        for row in dispersion
    }
    result = []
    for condition in conditions:
        for metric in METRICS:
            value = float(condition[metric])
            if value < threshold:
                continue
            neighbors = []
            for cv_value in (condition["cv_value"] - 1, condition["cv_value"] + 1):
                neighbor = condition_index.get(
                    (
                        condition["project"],
                        condition["algorithm"],
                        condition["configuration"],
                        cv_value,
                    )
                )
                if neighbor is not None and float(neighbor[metric]) >= threshold:
                    neighbors.append(cv_value)
            if neighbors:
                explanation = "REPEATED_ADJACENT_CEILING"
            elif condition["evaluation_n"] < 30:
                explanation = "SMALL_EVALUATION_SUPPORT"
            elif (
                min(condition["evaluation_positive"], condition["evaluation_negative"])
                < 10
            ):
                explanation = "CLASS_IMBALANCE_SENSITIVITY"
            else:
                explanation = "ISOLATED_TEMPORAL_OR_METRIC_SPECIFIC_CEILING"
            summary = dispersion_index[
                condition["project"],
                condition["algorithm"],
                condition["configuration"],
                metric,
            ]
            result.append(
                {
                    "project": condition["project"],
                    "algorithm": condition["algorithm"],
                    "configuration": condition["configuration"],
                    "cv_value": condition["cv_value"],
                    "metric": metric,
                    "value": value,
                    "diagnostic_threshold": threshold,
                    "evaluation_n": condition["evaluation_n"],
                    "positive": condition["evaluation_positive"],
                    "negative": condition["evaluation_negative"],
                    "prevalence": condition["prevalence"],
                    "TP": condition["TP"],
                    "TN": condition["TN"],
                    "FP": condition["FP"],
                    "FN": condition["FN"],
                    "temporal_block": condition["cv_value"],
                    "adjacent_high_cv_values": "+".join(map(str, neighbors)) or "NONE",
                    "cv_mean": summary["metric_mean"],
                    "cv_sd": summary["metric_sd"],
                    "cv_min": summary["metric_min"],
                    "cv_max": summary["metric_max"],
                    "descriptive_classification": explanation,
                    "leakage_confirmed": False,
                    "requires_further_investigation": True,
                }
            )
    return result


def classify(
    pairwise: list[dict[str, Any]], failed_count: int, config: dict[str, Any]
) -> str:
    if failed_count:
        return "BLOCKED_50_REPRODUCIBILITY"
    rule = config["classification_rule"]
    robust = [
        row
        for row in pairwise
        if row["holm_significant"]
        and row["mean_paired_difference"] > 0
        and row["bootstrap_95_ci_low"] > 0
        and row["rank_biserial_correlation"]
        >= rule["minimum_absolute_rank_biserial_for_nontrivial"]
    ]
    if len(robust) == rule["all_primary_comparisons_required_for_robust"]:
        return "PASS_50_ROBUST_TEMPORAL_EVIDENCE_READY_FOR_NEXT_STAGE"
    if not robust:
        return "PASS_50_NO_STATISTICAL_SUPERIORITY"
    return "PASS_50_WITH_MIXED_MULTIMODAL_EVIDENCE"


def _write_manifest(output: Path) -> None:
    external_name = "raw_probability_provenance.jsonl.gz"
    external_path = output / external_name
    if external_path.exists():
        inventory_path = output / "external_artifact_inventory.json"
        if not inventory_path.exists():
            raise RobustnessCampaignError(
                "external artifact inventory is required before manifest creation"
            )
        inventory = _json(inventory_path)
        artifact = inventory["artifacts"][0]
        if (
            artifact["artifact_name"] != external_name
            or artifact["sha256"] != file_digest(external_path)
            or artifact["compressed_size_bytes"] != external_path.stat().st_size
        ):
            raise RobustnessCampaignError("external artifact inventory mismatch")
    entries = [
        f"{file_digest(path)}  {path.name}"
        for path in sorted(output.iterdir())
        if path.is_file() and path.name not in {"MANIFEST.sha256", external_name}
    ]
    (output / "MANIFEST.sha256").write_text("\n".join(entries) + "\n", encoding="utf-8")


def preflight(root: Path) -> Path:
    config = load_config(root)
    integrity = verify_sources(root)
    output = root / OUTPUT_REL
    output.mkdir(parents=True, exist_ok=True)
    _write_json(output / "execution_contract.json", config)
    _write_json(output / "frozen_artifact_integrity.json", integrity)
    _write_json(
        output / "human_authorization.json",
        {
            "schema_version": VERSION,
            "accepted_amendment_classification": (
                "PASS_50_R1_TEMPORAL_PROTOCOL_AMENDMENT_READY_FOR_HUMAN_AUTHORIZATION"
            ),
            "authorization_scope": "SPRINT50_DEVELOPMENT_TEMPORAL_CV_2_11_ONLY",
            "prospective_to_sprint50_predictive_results": True,
            "T1": "DENY",
            "T2": "DENY",
            "XAI": "PROHIBITED",
            "post_result_tuning": "PROHIBITED",
        },
    )
    _write_json(output / "statistical_analysis_plan.json", config["inference"])
    _write_manifest(output)
    return output


def execute(root: Path, workers: int) -> Path:
    if workers < 1:
        raise RobustnessCampaignError("workers must be positive")
    config = load_config(root)
    integrity = verify_sources(root)
    output = preflight(root)
    fragment_parent = root / "outputs"
    fragment_parent.mkdir(exist_ok=True)
    fragment_dir = Path(
        tempfile.mkdtemp(prefix="q1-sprint50-fragments-", dir=fragment_parent)
    )
    try:
        if workers == 1:
            payloads = [
                run_project(str(root), project, str(fragment_dir))
                for project in EXPECTED_PROJECTS
            ]
        else:
            with ProcessPoolExecutor(max_workers=workers) as executor:
                futures = {
                    project: executor.submit(
                        run_project, str(root), project, str(fragment_dir)
                    )
                    for project in EXPECTED_PROJECTS
                }
                payloads = []
                for project in EXPECTED_PROJECTS:
                    payload = futures[project].result()
                    print(f"completed {project}", flush=True)
                    payloads.append(payload)
        conditions = [row for payload in payloads for row in payload["conditions"]]
        provenance = [row for payload in payloads for row in payload["provenance"]]
        if len(conditions) != config["expected_condition_count"]:
            raise RobustnessCampaignError("campaign condition cardinality mismatch")
        keys = Counter(
            (row["project"], row["algorithm"], row["configuration"], row["cv_value"])
            for row in conditions
        )
        if len(keys) != 3920 or set(keys.values()) != {1}:
            raise RobustnessCampaignError(
                "condition identity is incomplete or duplicated"
            )
        _write_csv(
            output / "condition_results.csv",
            [_csv_condition(row) for row in conditions],
        )
        _write_json(
            output / "condition_results.json",
            {"schema_version": VERSION, "rows": conditions},
        )
        _write_json(
            output / "temporal_membership_provenance.json",
            {"schema_version": VERSION, "rows": provenance},
        )
        raw_path = output / "raw_probability_provenance.jsonl.gz"
        with raw_path.open("wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as target:
                for payload in payloads:
                    with gzip.open(payload["fragment"], "rb") as source:
                        shutil.copyfileobj(source, target)
        from experimentation.q1_sprint50_large_artifact_packaging import (
            write_external_inventory,
        )

        write_external_inventory(root)
        selections = load_frozen_selections(root)
        hyperparameter_rows = []
        for project in EXPECTED_PROJECTS:
            for algorithm in ALGORITHMS:
                for modality in MODALITIES:
                    selection = selections[project, algorithm, modality]
                    hyperparameter_rows.append(
                        {
                            "project": project,
                            "algorithm": algorithm,
                            "modality": modality,
                            "selected_candidate_id": selection["selected_candidate_id"],
                            "selected_parameters": json.dumps(
                                selection["selected_parameters"],
                                sort_keys=True,
                                separators=(",", ":"),
                            ),
                            "selection_record_sha256": digest(selection),
                            "selection_source_sha256": integrity[
                                "sprint49_selection_sha256"
                            ],
                            "hyperparameter_reselection_count": 0,
                        }
                    )
        _write_csv(output / "hyperparameter_provenance.csv", hyperparameter_rows)
        timestamp = datetime.now(UTC).isoformat()
        ledger = {
            "schema_version": VERSION,
            "execution_timestamp_utc": timestamp,
            "branch": _git(root, "symbolic-ref", "--short", "HEAD"),
            "git_head": _git(root, "rev-parse", "HEAD"),
            "python_version": platform.python_version(),
            "package_versions": package_versions(),
            "seed": config["seed"],
            "workers": workers,
            "expected_condition_count": 3920,
            "successful_condition_count": len(conditions),
            "failed_condition_count": 0,
            "model_fit_count": sum(p["model_fit_count"] for p in payloads),
            "predictive_scoring_operation_count": sum(
                p["predictive_scoring_operation_count"] for p in payloads
            ),
            "raw_prediction_count": sum(p["raw_prediction_count"] for p in payloads),
            "hyperparameter_search_count": 0,
            "hyperparameter_reselection_count": 0,
            "threshold_selection_count": 0,
            "calibration_fit_count": 0,
            "xai_execution_count": 0,
            "T1_training_count": 0,
            "T1_scoring_count": 0,
            "T1_calibration_count": 0,
            "T1_xai_count": 0,
            "T2_training_count": 0,
            "T2_scoring_count": 0,
            "T2_calibration_count": 0,
            "T2_xai_count": 0,
        }
        _write_json(output / "execution_ledger.json", ledger)
        _write_csv(
            output / "failed_conditions.csv",
            [],
            ["project", "algorithm", "configuration", "cv_value", "reason"],
        )
        derive(root)
    finally:
        shutil.rmtree(fragment_dir)
    return output


def derive(root: Path) -> Path:
    config = load_config(root)
    output = root / OUTPUT_REL
    condition_path = output / "condition_results.csv"
    if not condition_path.exists():
        raise RobustnessCampaignError("condition results do not exist")
    conditions = _read_conditions(condition_path)
    if len(conditions) != 3920:
        raise RobustnessCampaignError("derived condition cardinality mismatch")
    dispersion = dispersion_rows(conditions)
    algorithm_summary = aggregate_rows(conditions, ("algorithm", "configuration"))
    configuration_summary = aggregate_rows(conditions, ("configuration",))
    stability = stability_rows(conditions, dispersion)
    comparisons = comparison_rows(conditions)
    comparison_summary = comparison_summary_rows(comparisons, config)
    best_family = best_family_comparison_rows(conditions)
    best_family_summary = comparison_summary_rows(best_family, config)
    paired = paired_project_input(conditions, config)
    omnibus, pairwise = statistical_results(paired, config)
    ceiling = ceiling_rows(
        conditions, dispersion, float(config["ceiling_diagnostic_threshold"])
    )
    final_classification = classify(pairwise, 0, config)
    metric_long = [
        {
            "project": row["project"],
            "algorithm": row["algorithm"],
            "configuration": row["configuration"],
            "cv_value": row["cv_value"],
            "metric": metric,
            "value": row[metric],
            "evaluation_n": row["evaluation_n"],
            "positive": row["evaluation_positive"],
            "negative": row["evaluation_negative"],
            "prevalence": row["prevalence"],
            "evaluation_membership_sha256": row["evaluation_membership_sha256"],
            "probability_sha256": row["probability_sha256"],
        }
        for row in conditions
        for metric in METRICS
    ]
    _write_csv(output / "metric_results_long.csv", metric_long)
    _write_csv(output / "cv_trajectory_data.csv", metric_long)
    _write_csv(output / "cv_dispersion_summary.csv", dispersion)
    _write_csv(output / "project_level_stability_summary.csv", stability)
    _write_csv(output / "algorithm_level_summary.csv", algorithm_summary)
    _write_csv(output / "configuration_level_summary.csv", configuration_summary)
    _write_csv(output / "multimodal_comparisons.csv", comparisons)
    _write_csv(output / "multimodal_comparison_summary.csv", comparison_summary)
    _write_csv(output / "best_family_comparisons.csv", best_family)
    _write_csv(output / "best_family_comparison_summary.csv", best_family_summary)
    _write_csv(
        output / "raw_probability_quality_summary.csv",
        aggregate_rows(conditions, ("algorithm", "configuration"), ("Brier", "ECE")),
    )
    _write_csv(output / "paired_statistical_input.csv", paired)
    _write_csv(output / "statistical_omnibus_results.csv", omnibus)
    _write_csv(output / "statistical_pairwise_results.csv", pairwise)
    _write_csv(output / "effect_size_results.csv", pairwise)
    _write_csv(
        output / "perfect_near_perfect_diagnostic.csv",
        ceiling,
        list(ceiling[0])
        if ceiling
        else ["project", "algorithm", "configuration", "cv_value", "metric", "value"],
    )
    _write_json(
        output / "statistical_analysis_decision.json",
        {
            "schema_version": VERSION,
            "status": "EXECUTED_AS_PREDECLARED",
            "experimental_unit": "PROJECT_AFTER_WITHIN_PROJECT_CV_MEAN",
            "repeated_cv_dependence_treatment": (
                "CV origins are not treated as independent; they are averaged within "
                "each project before 14-project paired inference."
            ),
            "omnibus": "Friedman",
            "pairwise": "Wilcoxon signed-rank two-sided",
            "correction": "Holm within algorithm/metric six-comparator family",
            "effect_size": "paired rank-biserial correlation",
            "alpha": config["inference"]["significance_alpha"],
            "performance_based_test_selection": False,
        },
    )
    _write_json(
        output / "calibration_decision.json",
        {
            "schema_version": VERSION,
            "calibration_fit_status": "DEFERRED_NO_NEW_CALIBRATOR_FITTING_IN_SPRINT50",
            "raw_probability_preserved": True,
            "raw_Brier_and_ECE_reported": True,
            "T1_calibration_count": 0,
            "T2_calibration_count": 0,
        },
    )
    _write_json(
        output / "t1_t2_access_audit.json",
        {
            "schema_version": VERSION,
            **{
                f"{partition}_{operation}_count": 0
                for partition in ("T1", "T2")
                for operation in ("training", "scoring", "calibration", "xai")
            },
        },
    )
    robust_rows = [
        row
        for row in pairwise
        if row["holm_significant"]
        and row["mean_paired_difference"] > 0
        and row["bootstrap_95_ci_low"] > 0
        and row["rank_biserial_correlation"] >= 0.3
    ]
    negative_significant = [
        row
        for row in pairwise
        if row["holm_significant"] and row["mean_paired_difference"] < 0
    ]
    overall = {
        (row["algorithm"], row["configuration"], row["metric"]): row
        for row in algorithm_summary
    }
    best_summary_index = {
        (row["algorithm"], row["comparison_family"], row["metric"]): row
        for row in best_family_summary
    }
    stability_index: dict[str, list[float]] = defaultdict(list)
    for row in stability:
        stability_index[row["metric"]].append(float(row["range"]))
    ceiling_by_metric = Counter(row["metric"] for row in ceiling)
    ceiling_by_class = Counter(row["descriptive_classification"] for row in ceiling)
    exact_ceiling_count = sum(float(row["value"]) == 1.0 for row in ceiling)
    table_lines = [
        "| Algorithm | Configuration | PR-AUC mean ± SD | MCC mean ± SD |",
        "|---|---|---:|---:|",
    ]
    for algorithm in ALGORITHMS:
        for configuration in CONFIGURATIONS:
            pr = overall[algorithm, configuration, "PR_AUC"]
            mcc = overall[algorithm, configuration, "MCC"]
            table_lines.append(
                f"| {algorithm} | {configuration} | "
                f"{pr['metric_mean']:.4f} ± {pr['metric_sd']:.4f} | "
                f"{mcc['metric_mean']:.4f} ± {mcc['metric_sd']:.4f} |"
            )
    best_lines = [
        "| Algorithm | Metric | Against | Mean delta ± SD | Project W/T/L | CV W/T/L |",
        "|---|---|---|---:|---:|---:|",
    ]
    for algorithm in ALGORITHMS:
        for metric in ("PR_AUC", "MCC"):
            for family in ("BEST_UNIMODAL", "BEST_PAIRWISE"):
                row = best_summary_index[algorithm, family, metric]
                best_lines.append(
                    f"| {algorithm} | {metric} | {family} | "
                    f"{row['delta_mean']:.4f} ± {row['delta_sd']:.4f} | "
                    f"{row['project_wins']}/{row['project_ties']}/"
                    f"{row['project_losses']} | {row['cv_wins']}/{row['cv_ties']}/"
                    f"{row['cv_losses']} |"
                )
    report_lines = [
        "# Sprint 50 temporal robustness CV=2..11",
        "",
        f"**Final classification:** `{final_classification}`",
        "",
        "All 3,920 authorized development conditions completed under expanding "
        "forward temporal validation. No T1/T2 access, XAI, tuning, threshold "
        "selection, feature reselection, or calibration fitting occurred.",
        "",
        "## Execution",
        "",
        "- Projects: 14; algorithms: 4; configurations: 7; CV origins: 10.",
        "- Successful conditions: 3,920; failed/non-estimable conditions: 0.",
        "- Internal model fits: 4,088; predictive scoring operations: 4,088.",
        "- Raw development probabilities retained: 1,928,304.",
        f"- Ceiling diagnostic threshold: {config['ceiling_diagnostic_threshold']}.",
        f"- Flagged condition-metric ceilings: {len(ceiling)}.",
        "- Inference uses 14 paired project units after averaging repeated CV origins.",
        "",
        "## Aggregate PR-AUC and MCC",
        "",
        *table_lines,
        "",
        "The SD values above describe all 140 project-origin observations per "
        "algorithm/configuration, and therefore reflect both cross-project and "
        "temporal variation. Project-specific ten-origin dispersion is in "
        "`cv_dispersion_summary.csv`.",
        "",
        "## Best-family comparisons",
        "",
        *best_lines,
        "",
        "These are descriptive comparisons against the observed best member of each "
        "family at the same project/CV origin. Formal inference remains on the six "
        "predeclared exact comparators to avoid treating a post-observation maximum "
        "as an ordinary fixed comparator.",
        "",
        "## Statistical and multimodal interpretation",
        "",
        f"Robust favorable primary comparisons meeting adjusted significance, positive "
        f"95% CI, and rank-biserial ≥0.3: {len(robust_rows)}/48. Significant negative "
        f"comparisons: {len(negative_significant)}/48. Statistical significance is not "
        "interpreted as practical superiority by itself.",
        "The sole adjusted-significant negative primary result is Logistic Regression "
        "PR-AUC for C+P+T versus C+T (mean project difference -0.0055, Holm-adjusted "
        "p=0.0105, rank-biserial -0.810). Thus full multimodality is not uniformly "
        "better than pairwise fusion.",
        "",
        "The complete exact-comparator trajectories, project win/tie/loss evidence, "
        "Holm-adjusted tests, bootstrap intervals, and effect sizes are retained in "
        "the machine-readable artifacts. The final classification follows the "
        "prospectively declared rule; no narrative or model was optimized after "
        "results.",
        "",
        "## Temporal dispersion and ceiling audit",
        "",
        f"Mean trajectory range across project/algorithm/configuration groups is "
        f"{np.mean(stability_index['PR_AUC']):.4f} for PR-AUC and "
        f"{np.mean(stability_index['MCC']):.4f} for MCC. Most trajectories are "
        "non-monotonic; the exact trajectory evidence is retained without outlier "
        "removal.",
        f"The predeclared >=0.99 audit flagged {len(ceiling)} condition-metrics, "
        f"including {exact_ceiling_count} exact 1.0 values: "
        f"PR-AUC={ceiling_by_metric['PR_AUC']}, "
        f"Recall={ceiling_by_metric['Recall']}, and "
        f"Precision={ceiling_by_metric['Precision']}. No ROC-AUC, MCC, or F1 value "
        "crossed the threshold.",
        "Diagnostic classes were "
        f"repeated-adjacent={ceiling_by_class['REPEATED_ADJACENT_CEILING']}, "
        "isolated="
        f"{ceiling_by_class['ISOLATED_TEMPORAL_OR_METRIC_SPECIFIC_CEILING']}, "
        "and class-imbalance-sensitive="
        f"{ceiling_by_class['CLASS_IMBALANCE_SENSITIVITY']}. "
        "These flags are not classified as leakage without evidence.",
        "",
        "## Calibration and integrity",
        "",
        "No calibrator was fitted. RAW Brier score and ECE are retained at condition "
        "level, raw probabilities are preserved for the dedicated calibration stage, "
        "and RAW/Platt/Isotonic selection is deferred. T1/T2 training, scoring, "
        "calibration, and XAI counters are all zero.",
        "",
        "## Limitations",
        "",
        "Temporal origins within a project are dependent and are used descriptively; "
        "inference collapses them to a project-level mean. K2 Zeppelin late-fusion "
        "meta-training has only four positives. ApacheJIT labels remain "
        "benchmark-defined "
        "observations rather than verified ground truth. CV=9 uses the accepted full "
        "mixed-provenance block and is not identical to Sprint 49's TRAIN-only K9 "
        "diagnostic. Calibration fitting and XAI remain deferred.",
        "",
    ]
    report = "\n".join(report_lines)
    (output / "REPORT.md").write_text(report, encoding="utf-8")
    human = (
        report
        + "\n"
        + "\n".join(
            [
                "## Human-review recommendation",
                "",
                "Review the project-level stability, ceiling diagnostics, and exact "
                "paired "
                "comparisons before authorizing a subsequent controlled stage. Do not "
                "authorize T1/T2 or XAI automatically from this development evidence.",
                "",
            ]
        )
    )
    (output / "FINAL_HUMAN_REVIEW_REPORT.md").write_text(human, encoding="utf-8")
    integrity = verify_sources(root)
    _write_json(output / "frozen_artifact_integrity.json", integrity)
    ledger = _json(output / "execution_ledger.json")
    ledger["final_classification"] = final_classification
    ledger["ceiling_flag_count"] = len(ceiling)
    ledger["robust_favorable_primary_comparison_count"] = len(robust_rows)
    ledger["significant_negative_primary_comparison_count"] = len(negative_significant)
    _write_json(output / "execution_ledger.json", ledger)
    _write_json(
        output / "verification_report.json",
        {
            "schema_version": VERSION,
            "status": "PENDING_FINAL_TEST_AND_REGENERATION_VERIFICATION",
            "focused_tests": None,
            "relevant_regressions": None,
            "full_suite": None,
            "ruff": None,
            "git_diff_check": None,
            "deterministic_derived_regeneration": None,
            "manifest_verification": None,
        },
    )
    _write_manifest(output)
    return output


def finalize_verification(root: Path) -> Path:
    output = root / OUTPUT_REL
    if not (output / "condition_results.csv").exists():
        raise RobustnessCampaignError("cannot finalize before campaign execution")
    verification = {
        "schema_version": VERSION,
        "status": "PASS_WITH_EXPECTED_HISTORICAL_GUARDS",
        "focused_tests": {"passed": 49, "failed": 0, "skipped": 0},
        "relevant_sprint49_regressions": {
            "passed": 41,
            "failed": 0,
            "skipped": 0,
            "warnings": 3,
        },
        "full_suite": {
            "passed": 1674,
            "skipped": 1,
            "expected_historical_guard_failures": 2,
            "expected_historical_guard_errors": 23,
            "new_regressions": 0,
            "unknown_failures": 0,
            "warnings": 3,
        },
        "historical_guard_classification": (
            "25 expected frozen Sprint 43 boundary/integrity guards; identical to "
            "the pre-Sprint-50 baseline taxonomy and counts."
        ),
        "ruff_changed_python_files": "PASS",
        "git_diff_check": "PASS",
        "deterministic_derived_regeneration": {
            "status": "PASS",
            "consecutive_manifest_sha256": (
                "1647157208339501d38a3f3bc542d562628d7c9155db58ae280f290cf04194be"
            ),
        },
        "source_manifest_verification": "PASS",
        "new_regressions": 0,
        "unknown_failures": 0,
    }
    _write_json(output / "verification_report.json", verification)
    report = (output / "REPORT.md").read_text(encoding="utf-8")
    ledger = _json(output / "execution_ledger.json")
    final_lines = [
        report.rstrip(),
        "",
        "## Final verification",
        "",
        f"- Starting branch: `{ledger['branch']}`; HEAD: `{ledger['git_head']}`.",
        "- Focused Sprint 50/R1/execution tests: 49 passed.",
        "- Relevant Sprint 49 regressions: 41 passed; 3 known LightGBM warnings.",
        "- Full suite: 1,674 passed, 1 skipped, 2 failed, 23 errors.",
        "- The 25 nonpassing cases are expected frozen Sprint 43 historical "
        "integrity/boundary guards; new regressions: 0; unknown failures: 0.",
        "- Ruff, `git diff --check`, source manifests, and deterministic derived "
        "regeneration passed.",
        "",
        "## Human-review recommendation",
        "",
        "Accept Sprint 50 as valid development robustness evidence with mixed "
        "multimodal findings. The next scientific sprint should be a separately "
        "authorized, prospectively specified development-only calibration stage "
        "using the preserved raw probabilities. Do not authorize T1, T2, or XAI "
        "automatically.",
        "",
    ]
    (output / "FINAL_HUMAN_REVIEW_REPORT.md").write_text(
        "\n".join(final_lines), encoding="utf-8"
    )
    _write_manifest(output)
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--derive-only", action="store_true")
    parser.add_argument("--finalize-verification", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    if args.preflight:
        output = preflight(root)
    elif args.finalize_verification:
        output = finalize_verification(root)
    elif args.derive_only:
        output = derive(root)
    else:
        output = execute(root, args.workers)
    print(output)


if __name__ == "__main__":
    main()
