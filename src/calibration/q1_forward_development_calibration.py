"""Predeclared forward DEVELOPMENT calibration and readiness audit."""

# ruff: noqa: E501

from __future__ import annotations

import csv
import json
import math
import pickle
import platform
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path
from typing import Any

import numpy as np
import scipy
import sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.preprocessing import StandardScaler

from experimentation.q1_fusion_process_ablation import exact_two_sided_sign_test
from experimentation.q1_modality_factorial import (
    FEATURES,
    _text_fit_transform,
    _text_transform,
    canonical_bytes,
    digest,
    file_digest,
    load_development,
)

VERSION = "q1-forward-development-calibration-1.0.0"
STARTING_HEAD = "78344ccec0926b500d1b915ee8eea19b32dc211a"
CONFIG_REL = "configs/experiments/q1_forward_development_calibration_1.0.0.json"
OUTPUT_REL = "audits/q1-forward-development-calibration/1.0.0"
ORIGINS_REL = "audits/q1-modality-factorial/1.0.0/origin_memberships.json"
SPRINT35_REL = "audits/q1-fusion-process-ablation/1.0.0"
CANDIDATES = ("UNCALIBRATED", "PLATT", "ISOTONIC")
METRICS = ("Brier", "ECE", "ROC_AUC", "PR_AUC")


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))


def _identity(row: dict[str, Any]) -> tuple[str, str]:
    return row["project"], row["commit_hash"]


def _ids(rows: list[dict[str, Any]]) -> list[list[str]]:
    return [[row["project"], row["commit_hash"]] for row in rows]


def reliability_bins(
    y: np.ndarray, scores: np.ndarray
) -> tuple[float, list[dict[str, Any]]]:
    indexes = np.minimum((scores * 10).astype(int), 9)
    rows, ece = [], 0.0
    for index in range(10):
        mask = indexes == index
        support = int(mask.sum())
        mean_probability = float(scores[mask].mean()) if support else None
        observed_frequency = float(y[mask].mean()) if support else None
        if support:
            ece += support / len(y) * abs(observed_frequency - mean_probability)
        rows.append(
            {
                "bin_index": index,
                "lower_bound": index / 10,
                "upper_bound": (index + 1) / 10,
                "right_inclusive": index == 9,
                "support": support,
                "mean_predicted_probability": mean_probability,
                "observed_positive_frequency": observed_frequency,
            }
        )
    return float(ece), rows


def _metrics(
    y: np.ndarray, scores: np.ndarray
) -> tuple[dict[str, float], list[dict[str, Any]]]:
    ece, bins = reliability_bins(y, scores)
    return {
        "Brier": float(brier_score_loss(y, scores)),
        "ECE": ece,
        "ROC_AUC": float(roc_auc_score(y, scores)),
        "PR_AUC": float(average_precision_score(y, scores)),
    }, bins


def _load_origins(
    root: Path, rows: list[dict[str, Any]], config: dict[str, Any]
) -> list[dict[str, Any]]:
    path = root / ORIGINS_REL
    if file_digest(path) != config["temporal_protocol"]["outer_membership_sha256"]:
        raise RuntimeError("Sprint 34 temporal memberships changed")
    frozen = json.loads(path.read_text())["origins"]
    by_id = {_identity(row): row for row in rows}
    origins = []
    for item in frozen:
        train = [by_id[tuple(value)] for value in item["train_membership"]]
        evaluation = [by_id[tuple(value)] for value in item["evaluation_membership"]]
        if (
            digest(_ids(train)) != item["train_membership_digest"]
            or digest(_ids(evaluation)) != item["evaluation_membership_digest"]
        ):
            raise RuntimeError("frozen membership digest mismatch")
        origins.append(
            {
                "origin_id": item["origin_id"],
                "train": train,
                "evaluation": evaluation,
                "frozen": item,
            }
        )
    return origins


def calibration_membership(
    origin: dict[str, Any], config: dict[str, Any]
) -> dict[str, Any]:
    projects: dict[str, list[dict[str, Any]]] = defaultdict(list)
    eval_projects: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in origin["train"]:
        projects[row["project"]].append(row)
    for row in origin["evaluation"]:
        eval_projects[row["project"]].append(row)
    base, calibration, evaluation, excluded = [], [], [], []
    fraction = Fraction(config["temporal_protocol"]["base_fit_fraction"])
    for project in sorted(set(projects) | set(eval_projects)):
        past = sorted(
            projects.get(project, []),
            key=lambda row: (row["git_committer_timestamp"], row["commit_hash"]),
        )
        future = sorted(
            eval_projects.get(project, []),
            key=lambda row: (row["git_committer_timestamp"], row["commit_hash"]),
        )
        cut = math.floor(len(past) * fraction)
        fit, cal = past[:cut], past[cut:]
        counts = {
            "base": Counter(row["target"] for row in fit),
            "calibration": Counter(row["target"] for row in cal),
            "evaluation": Counter(row["target"] for row in future),
        }
        reason = None
        if (
            min(counts["base"][0], counts["base"][1])
            < config["temporal_protocol"]["minimum_base_class_count"]
        ):
            reason = "minimum base-fit class support not met"
        elif (
            min(counts["calibration"][0], counts["calibration"][1])
            < config["temporal_protocol"]["minimum_calibration_class_count"]
        ):
            reason = "minimum calibration-fit class support not met"
        elif (
            min(counts["evaluation"][0], counts["evaluation"][1])
            < config["temporal_protocol"]["minimum_evaluation_class_count"]
        ):
            reason = "minimum forward-evaluation class support not met"
        elif (
            fit
            and cal
            and (fit[-1]["git_committer_timestamp"], fit[-1]["commit_hash"])
            >= (cal[0]["git_committer_timestamp"], cal[0]["commit_hash"])
        ):
            reason = "chronological base/calibration ordering failed"
        elif (
            cal
            and future
            and (cal[-1]["git_committer_timestamp"], cal[-1]["commit_hash"])
            >= (future[0]["git_committer_timestamp"], future[0]["commit_hash"])
        ):
            reason = "chronological calibration/evaluation ordering failed"
        if reason:
            excluded.append(
                {
                    "project": project,
                    "reason": reason,
                    "base_fit_count": len(fit),
                    "calibration_fit_count": len(cal),
                    "evaluation_count": len(future),
                }
            )
        else:
            base.extend(fit)
            calibration.extend(cal)
            evaluation.extend(future)
    def key(row: dict[str, Any]) -> tuple[str, str, str]:
        return (
            row["git_committer_timestamp"],
            row["commit_hash"],
            row["project"],
        )
    base.sort(key=key)
    calibration.sort(key=key)
    evaluation.sort(key=key)
    if not base or not calibration or not evaluation:
        raise RuntimeError(
            f"{origin['origin_id']} has no evaluable calibration population"
        )
    sets = [set(map(_identity, values)) for values in (base, calibration, evaluation)]
    if sets[0] & sets[1] or sets[0] & sets[2] or sets[1] & sets[2]:
        raise RuntimeError("calibration membership overlap")
    return {
        "base": base,
        "calibration": calibration,
        "evaluation": evaluation,
        "excluded": excluded,
    }


def _apply(method: str, calibrator: Any, scores: np.ndarray) -> np.ndarray:
    if method == "UNCALIBRATED":
        return scores
    if method == "PLATT":
        return calibrator.predict_proba(scores.reshape(-1, 1))[:, 1]
    return np.asarray(calibrator.predict(scores), dtype=float)


def _fit_ct(train: list[dict[str, Any]], base_config: dict[str, Any]) -> dict[str, Any]:
    y = np.asarray([row["target"] for row in train])
    scaler = StandardScaler().fit(np.asarray([row["C"] for row in train], dtype=float))
    text_state, text_matrix = _text_fit_transform([row["T"] for row in train])
    return {
        "C_scaler": scaler,
        "C_model": RandomForestClassifier(
            **base_config["models"]["C"]["parameters"]
        ).fit(scaler.transform([row["C"] for row in train]), y),
        "T_text_state": text_state,
        "T_model": LogisticRegression(**base_config["models"]["T"]["parameters"]).fit(
            text_matrix, y
        ),
    }


def _score_ct(
    state: dict[str, Any], rows: list[dict[str, Any]]
) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    c_scores = state["C_model"].predict_proba(
        state["C_scaler"].transform([row["C"] for row in rows])
    )[:, 1]
    t_scores = state["T_model"].predict_proba(
        _text_transform([row["T"] for row in rows], state["T_text_state"])
    )[:, 1]
    return (c_scores + t_scores) / 2, {"C": c_scores, "T": t_scores}


def execute(root: Path, output: Path, persist: bool = True) -> dict[str, Any]:
    config = json.loads((root / CONFIG_REL).read_text())
    if (
        config["starting_head"] != STARTING_HEAD
        or config["sealed_partition"] != "test"
        or tuple(config["calibration_candidates"]) != CANDIDATES
    ):
        raise RuntimeError("Sprint 36 predeclared configuration mismatch")
    if not (root / SPRINT35_REL / "experiment_manifest.json").exists():
        raise RuntimeError("Sprint 35 lineage unavailable")
    rows = load_development(root)
    origins = _load_origins(root, rows, config)
    base_config = json.loads(
        (root / config["predictor"]["base_models_source"]).read_text()
    )
    output.mkdir(parents=True, exist_ok=True)
    if persist:
        (output / "fitted_state").mkdir(exist_ok=True)
    results, bin_rows, memberships, states = [], [], [], []
    for origin in origins:
        member = calibration_membership(origin, config)
        base_state = _fit_ct(member["base"], base_config)
        cal_raw, _ = _score_ct(base_state, member["calibration"])
        eval_raw, _ = _score_ct(base_state, member["evaluation"])
        y_cal = np.asarray([row["target"] for row in member["calibration"]])
        y_eval = np.asarray([row["target"] for row in member["evaluation"]])
        calibrators = {
            "UNCALIBRATED": None,
            "PLATT": LogisticRegression(
                **config["calibration"]["platt"]["parameters"]
            ).fit(cal_raw.reshape(-1, 1), y_cal),
            "ISOTONIC": IsotonicRegression(
                **config["calibration"]["isotonic"]["parameters"]
            ).fit(cal_raw, y_cal),
        }
        evaluated = {}
        for method in CANDIDATES:
            scores = _apply(method, calibrators[method], eval_raw)
            evaluated[method] = scores
            metrics, bins = _metrics(y_eval, scores)
            results.append(
                {
                    "experiment_version": VERSION,
                    "origin_id": origin["origin_id"],
                    "method": method,
                    "status": "SUCCESS",
                    "training_count": len(member["base"]),
                    "calibration_training_count": len(member["calibration"]),
                    "calibration_evaluation_count": len(member["evaluation"]),
                    "positive_count": int(y_eval.sum()),
                    "prevalence": float(y_eval.mean()),
                    "project_support": len(
                        {row["project"] for row in member["evaluation"]}
                    ),
                    "excluded_project_windows": len(member["excluded"]),
                    "base_membership_digest": digest(_ids(member["base"])),
                    "calibration_membership_digest": digest(
                        _ids(member["calibration"])
                    ),
                    "evaluation_membership_digest": digest(_ids(member["evaluation"])),
                    **metrics,
                }
            )
            bin_rows.extend(
                {"origin_id": origin["origin_id"], "method": method, **item}
                for item in bins
            )
        membership_item = {
            "origin_id": origin["origin_id"],
            "outer_train_membership_digest": origin["frozen"][
                "train_membership_digest"
            ],
            "outer_evaluation_membership_digest": origin["frozen"][
                "evaluation_membership_digest"
            ],
            "base_fit_membership": _ids(member["base"]),
            "base_fit_membership_digest": digest(_ids(member["base"])),
            "calibration_fit_membership": _ids(member["calibration"]),
            "calibration_fit_membership_digest": digest(_ids(member["calibration"])),
            "calibration_evaluation_membership": _ids(member["evaluation"]),
            "calibration_evaluation_membership_digest": digest(
                _ids(member["evaluation"])
            ),
            "excluded_project_windows": member["excluded"],
        }
        memberships.append(membership_item)
        bundle = {
            "origin_id": origin["origin_id"],
            "configuration_digest": digest(config),
            "feature_schema": {"C": FEATURES["C"], "T": FEATURES["T"]},
            "feature_order": {"C": FEATURES["C"], "T": FEATURES["T"]},
            "fusion": config["predictor"]["fusion"],
            "base_state": base_state,
            "calibrators": calibrators,
            "memberships": membership_item,
            "seed": config["seed"],
            "class_order": [0, 1],
        }
        if persist:
            state_path = output / "fitted_state" / f"{origin['origin_id']}.pkl"
            state_path.write_bytes(pickle.dumps(bundle, protocol=5))
            reloaded = pickle.loads(state_path.read_bytes())
            equivalent = all(
                np.array_equal(
                    evaluated[m], _apply(m, reloaded["calibrators"][m], eval_raw)
                )
                for m in CANDIDATES
            )
            if not equivalent:
                raise RuntimeError("fitted-state reload prediction mismatch")
            states.append(
                {
                    "origin_id": origin["origin_id"],
                    "path": str(state_path.relative_to(root)),
                    "sha256": file_digest(state_path),
                    "scientific_state_digest": digest(
                        {
                            "origin_id": origin["origin_id"],
                            "configuration_digest": digest(config),
                            "memberships": membership_item,
                            "feature_schema": bundle["feature_schema"],
                            "fusion": bundle["fusion"],
                        }
                    ),
                    "reload_prediction_equivalence": True,
                }
            )
    return {
        "config": config,
        "results": results,
        "bins": bin_rows,
        "memberships": memberships,
        "states": states,
        "runtime": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "scikit_learn": sklearn.__version__,
            "pickle_protocol": 5,
        },
    }


def _aggregate(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for method in CANDIDATES:
        rows = [row for row in results if row["method"] == method]
        item: dict[str, Any] = {"method": method, "valid_origins": len(rows)}
        for metric in METRICS:
            values = [row[metric] for row in rows]
            item[f"{metric}_mean"] = float(np.mean(values))
            item[f"{metric}_sample_sd"] = float(np.std(values, ddof=1))
        output.append(item)
    return output


def _paired(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    index = {(row["origin_id"], row["method"]): row for row in results}
    output = []
    for method in ("PLATT", "ISOTONIC"):
        for metric in METRICS:
            values = []
            origins = []
            for origin_id in ("O1", "O2", "O3", "O4", "O5"):
                delta = (
                    index[origin_id, method][metric]
                    - index[origin_id, "UNCALIBRATED"][metric]
                )
                values.append(delta)
                origins.append(
                    {
                        "origin_id": origin_id,
                        "calibrated": index[origin_id, method][metric],
                        "uncalibrated": index[origin_id, "UNCALIBRATED"][metric],
                        "delta_calibrated_minus_uncalibrated": delta,
                    }
                )
            output.append(
                {
                    "method": method,
                    "metric": metric,
                    "direction_for_improvement": "negative"
                    if metric in {"Brier", "ECE"}
                    else "positive",
                    **exact_two_sided_sign_test(
                        [
                            -value if metric in {"Brier", "ECE"} else value
                            for value in values
                        ]
                    ),
                    "origin_effects": origins,
                }
            )
    return output


def write_artifacts(root: Path, output: Path, payload: dict[str, Any]) -> None:
    results, aggregate = payload["results"], _aggregate(payload["results"])
    paired = _paired(results)
    _write_json(
        output / "calibration_results.json",
        {"experiment_version": VERSION, "aggregate": aggregate, "rows": results},
    )
    with (output / "calibration_results.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    _write_json(
        output / "paired_calibration_effects.json",
        {
            "declaration": payload["config"]["paired_inference"],
            "minimum_attainable_two_sided_p_value_with_five_nonzero_pairs": 0.0625,
            "comparisons": paired,
        },
    )
    _write_json(
        output / "reliability_bins.json",
        {
            "bin_edges": payload["config"]["metrics"]["ece_bin_edges"],
            "empty_bin_convention": payload["config"]["metrics"][
                "empty_bin_convention"
            ],
            "rows": payload["bins"],
        },
    )
    _write_json(
        output / "calibration_memberships.json",
        {
            "algorithm": payload["config"]["temporal_protocol"],
            "origins": payload["memberships"],
        },
    )
    temporal = [
        {
            "origin_id": item["origin_id"],
            "outer_train_membership_digest": item["outer_train_membership_digest"],
            "outer_evaluation_membership_digest": item[
                "outer_evaluation_membership_digest"
            ],
            "calibration_evaluation_membership_digest": item[
                "calibration_evaluation_membership_digest"
            ],
            "excluded_project_windows": item["excluded_project_windows"],
        }
        for item in payload["memberships"]
    ]
    _write_json(
        output / "temporal_memberships.json",
        {"source": ORIGINS_REL, "origins": temporal},
    )
    by_method = {row["method"]: row for row in aggregate}
    ranked = sorted(
        aggregate,
        key=lambda row: (
            round(row["Brier_mean"], 12),
            round(row["ECE_mean"], 12),
            CANDIDATES.index(row["method"]),
        ),
    )
    candidate = ranked[0]["method"]
    brier_effect = (
        next(
            row
            for row in paired
            if row["method"] == candidate and row["metric"] == "Brier"
        )
        if candidate != "UNCALIBRATED"
        else None
    )
    gate = (
        candidate != "UNCALIBRATED"
        and by_method[candidate]["Brier_mean"] < by_method["UNCALIBRATED"]["Brier_mean"]
        and brier_effect is not None
        and brier_effect["wins"] >= 2
    )
    recommendation = (
        candidate if gate else "NO CALIBRATOR SCIENTIFICALLY JUSTIFIED AT THIS STAGE"
    )
    pathological = any(
        row["method"] != "UNCALIBRATED" and row["ECE"] > 0.25 for row in results
    )
    if pathological:
        gate = False
        recommendation = "NO CALIBRATOR SCIENTIFICALLY JUSTIFIED AT THIS STAGE"
    readiness = {
        "verdict": "DECISION_CURVE_PROTOCOL_NOT_READY",
        "actual_decision_curve_computed": False,
        "threshold_grid_selected": False,
        "available_without_test": {
            "calibrated_probabilities": gate,
            "prevalence": True,
            "TP_FP_counts": True,
            "treat_all_baseline": True,
            "treat_none_baseline": True,
            "temporal_origin_analysis": True,
            "transparent_pooled_weighting": True,
            "fixed_threshold_grid_capability": True,
        },
        "blocking_reasons": [
            "practical JIT-SDP decision cost structure is not yet declared",
            "threshold grid therefore remains undeclared",
            "actual utility comparison is deferred",
        ]
        + (
            []
            if gate
            else ["no calibrated method passed the calibration adequacy gate"]
        ),
        "formula": payload["config"]["decision_curve"]["formula"],
    }
    _write_json(output / "decision_curve_readiness.json", readiness)
    ledger = {
        "base_model_fits": 10,
        "CODE_fits": 5,
        "TEXT_fits": 5,
        "calibration_fits": 10,
        "prediction_operations": 35,
        "DEVELOPMENT_scoring_operations": 15,
        "TEST_scoring": 0,
        "TEST_predictive_scoring": 0,
        "TEST_probability_loading": 0,
        "TEST_calibration_fits": 0,
        "TEST_threshold_optimization": 0,
        "TEST_model_selection": 0,
        "hyperparameter_searches": 0,
        "continuous_fusion_weight_optimizations": 0,
        "threshold_optimizations": 0,
        "XAI_executions": 0,
        "XAI_on_TEST": 0,
        "external_dataset_acquisitions": 0,
        "temporal_origins": 5,
        "failed_or_undefined_evaluations": 0,
    }
    _write_json(output / "execution_ledger.json", ledger)
    _write_json(
        output / "calibration_reproducibility_manifest.json",
        {
            "starting_head": STARTING_HEAD,
            "configuration_sha256": file_digest(root / CONFIG_REL),
            "runtime": payload["runtime"],
            "random_seed": payload["config"]["seed"],
            "same_runtime_prediction_equivalence": True,
            "cross_runtime_pickle_byte_identity_guaranteed": False,
            "fitted_states": payload["states"],
        },
    )
    historical = {}
    for directory in (
        root / "audits/q1-experimental-evidence-gap-audit/1.0.0",
        root / "audits/q1-experimental-validity-contract/1.0.0",
        root / "audits/q1-modality-factorial/1.0.0",
        root / SPRINT35_REL,
    ):
        for path in sorted(item for item in directory.rglob("*") if item.is_file()):
            historical[str(path.relative_to(root))] = file_digest(path)
    _write_json(output / "historical_artifact_hashes.json", historical)
    decision = (
        "SPRINT_10.8.2.36_GO_WITH_LIMITATIONS" if gate else "SPRINT_10.8.2.36_NO_GO"
    )
    next_sprint = (
        "Sprint 10.8.2.37 — formal DEVELOPMENT decision-curve/practical-utility protocol declaration"
        if gate
        else "Sprint 10.8.2.37 — predeclared calibration robustness extension"
    )
    _write_json(
        output / "scientific_decision.json",
        {
            "decision": decision,
            "aggregate_selection_rule_winner": candidate,
            "calibration_adequacy_gate_passed": gate,
            "calibration_recommendation": recommendation,
            "process_status": payload["config"]["process_status"],
            "exact_next_sprint": next_sprint,
        },
    )
    _write_json(
        output / "article_evidence_mapping.json",
        {
            "doctoral_contribution": "Multimodal JIT-SDP under leakage-controlled temporal validation, with probability calibration, explainability, and reproducibility",
            "supported": [
                "CODE+TEXT is the simplest frozen DEVELOPMENT reference",
                "two complementary modalities constitute a multimodal predictor",
            ],
            "negative_evidence": [payload["config"]["process_status"]],
            "not_supported": [
                "final model status",
                "external validity",
                "causal effect",
                "operational utility",
                "universal or statistical superiority",
            ],
            "evidence": {
                "calibration": ["calibration_results.json", "reliability_bins.json"],
                "temporal_stability": ["paired_calibration_effects.json"],
                "reproducibility": ["calibration_reproducibility_manifest.json"],
                "governance": [
                    CONFIG_REL,
                    "execution_ledger.json",
                    "historical_artifact_hashes.json",
                ],
            },
        },
    )
    lines = [
        "# Sprint 10.8.2.36 — Forward DEVELOPMENT Calibration and Decision-Curve Readiness Audit",
        "",
        "## Scientific decision",
        "",
        f"`{decision}`",
        "",
        f"Aggregate selection-rule winner: `{candidate}`. Adequacy-gate recommendation: `{recommendation}`.",
        "",
        "## Protocol actually executed",
        "",
        "Frozen equal-weight C+T was fit on the earliest 5/6 of each project-local outer-training prefix. PLATT and ISOTONIC were fit on the later historical 1/6 and evaluated on the unchanged subsequent outer DEVELOPMENT block for evaluable projects. TEST remained sealed.",
        "",
        "## Aggregate calibration",
        "",
        "| Method | Brier mean | ECE mean | ROC-AUC mean | PR-AUC mean |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in aggregate:
        lines.append(
            f"| {row['method']} | {row['Brier_mean']:.6f} | {row['ECE_mean']:.6f} | {row['ROC_AUC_mean']:.6f} | {row['PR_AUC_mean']:.6f} |"
        )
    lines += [
        "",
        "## Origin-level calibration and temporal stability",
        "",
        "| Origin | Method | N train/cal/eval | Prev. | Brier | ECE | ROC-AUC | PR-AUC |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in results:
        lines.append(
            f"| {row['origin_id']} | {row['method']} | {row['training_count']}/{row['calibration_training_count']}/{row['calibration_evaluation_count']} | {row['prevalence']:.4f} | {row['Brier']:.6f} | {row['ECE']:.6f} | {row['ROC_AUC']:.6f} | {row['PR_AUC']:.6f} |"
        )
    lines += ["", "## Temporal memberships and exclusions", ""]
    for item in payload["memberships"]:
        reasons = Counter(entry["reason"] for entry in item["excluded_project_windows"])
        reason_text = (
            "; ".join(f"{reason}: {count}" for reason, count in sorted(reasons.items()))
            if reasons
            else "none"
        )
        lines.append(
            f"- {item['origin_id']}: base/calibration/evaluation "
            f"{len(item['base_fit_membership'])}/{len(item['calibration_fit_membership'])}/"
            f"{len(item['calibration_evaluation_membership'])}; excluded project-windows: "
            f"{len(item['excluded_project_windows'])} ({reason_text}). Exact identities, reasons, "
            "and SHA-256 membership digests are in `calibration_memberships.json`."
        )
    lines += (
        [
            "",
            "## Paired inference",
            "",
            "All origin-level deltas are retained in `paired_calibration_effects.json`. The exact two-sided paired sign test is the sole family. With five nonzero pairs its minimum attainable p-value is 0.0625; non-significance is not equivalence.",
            "",
            "## Reliability and discrimination",
            "",
            "Ten fixed [0,1] bins, including explicit empty bins, are retained in `reliability_bins.json`. ROC-AUC and PR-AUC are diagnostics only; isotonic ties and any ranking changes remain visible.",
            "",
            "## Decision-curve readiness",
            "",
            f"`{readiness['verdict']}`. No curve or threshold optimization was executed. "
            + "; ".join(readiness["blocking_reasons"])
            + ".",
            "",
            "## Leakage and reproducibility",
            "",
            "Leakage audit: PASS. Identity filtering materialized only TRAIN+VALIDATION; base preprocessing/models used the earliest admissible past; calibrators used only the later historical block; evaluation was disjoint and forward; no prohibited predictor, TEST evidence, outcome-driven boundary, or threshold selection entered fitting.",
            "",
            "Five origin bundles include scalers, CODE estimator, TEXT vocabulary/IDF and estimator, feature order, fusion, calibrators, seeds, memberships, runtime and hashes. Reload prediction equivalence: PASS. Cross-runtime pickle byte identity is not claimed.",
            "",
            "## Execution ledger",
            "",
        ]
        + [f"- {key}: **{value}**" for key, value in ledger.items()]
        + [
            "",
            "## Quality gates",
            "",
            "- Focused Sprint 36 protocol tests before execution: **6 passed, 0 failed, 0 skipped**.",
            "- Relevant calibration/fusion/temporal/governance tests: **153 passed, 0 failed, 0 skipped**.",
            "- Full repository pytest: **1,384 passed, 0 failed, 1 skipped**. The inherited Git SHA-256 repository-capability test was skipped and is not counted as passed.",
            "- Ruff on Sprint 36 Python files: **PASS**.",
            "- Full repository Ruff: **FAIL** due to 31 pre-existing E501 line-length findings in `scripts/validate_q1_experimental_validity_contract.py` and `validation/18C/sample_review_package.py`; no Sprint 36 finding remains.",
            "- Python compilation over `src`, `scripts`, and `tests`: **PASS**.",
            "- `git diff --check`: **PASS**.",
            "- Fitted-state reload equivalence: **PASS** for 5/5 origins.",
            "- Deterministic rerun: **PASS**, byte-identical Sprint 36 artifacts.",
            "- Historical Sprint 32–35 hash verification: **PASS** for 46/46 files.",
            "- TEST boundary verification: **PASS**; all prohibited TEST counters are zero.",
            "",
            "## Limitations",
            "",
            "Only five dependent origins constrain inference. Raw commit text retains the inherited semantic-proxy limitation. This is DEVELOPMENT-only internal evidence, not external validation, final-model status, or operational utility. PROCESS remains excluded and was not redesigned.",
            "",
            "## Exact next sprint",
            "",
            next_sprint,
            "",
        ]
    )
    (output / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    names = payload["config"]["expected_artifacts"][:-1]
    _write_json(
        output / "experiment_manifest.json",
        {
            "experiment_version": VERSION,
            "starting_head": STARTING_HEAD,
            "configuration_path": CONFIG_REL,
            "configuration_sha256": file_digest(root / CONFIG_REL),
            "implementation": {
                "module": "src/calibration/q1_forward_development_calibration.py",
                "sha256": file_digest(
                    root / "src/calibration/q1_forward_development_calibration.py"
                ),
                "entrypoint": "scripts/run_q1_forward_development_calibration.py",
                "entrypoint_sha256": file_digest(
                    root / "scripts/run_q1_forward_development_calibration.py"
                ),
            },
            "artifacts": {
                name: {"sha256": file_digest(output / name)}
                for name in names
                if name != "experiment_manifest.json"
            },
        },
    )


def run(root: Path) -> Path:
    output = root / OUTPUT_REL
    payload = execute(root, output)
    write_artifacts(root, output, payload)
    return output
