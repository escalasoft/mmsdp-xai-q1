"""Predeclared TRAIN/VALIDATION robustness analysis for frozen CODE+TEXT."""

# ruff: noqa: E501

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from experimentation.jit_defects4j_controlled_baselines import (
    DevelopmentBoundaryError,
    DevelopmentInputs,
    _matrix,
    load_development_inputs,
)
from experimentation.jit_defects4j_controlled_multimodal_fusion import _fuse
from models.logistic_regression_adapter import LogisticRegressionConfiguration
from models.lr import LogisticRegressionModel
from models.random_forest_adapter import RandomForestConfiguration
from models.rf import RandomForestModel


def canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
    ).encode()


def digest(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def validate_configuration(configuration: dict[str, Any]) -> None:
    if (
        configuration.get("fit_partition"),
        configuration.get("evaluation_partition"),
        configuration.get("sealed_partition"),
    ) != ("train", "validation", "test"):
        raise DevelopmentBoundaryError("invalid TRAIN/VALIDATION/TEST boundary")
    if (
        configuration.get("primary_candidate") != "CODE+TEXT"
        or configuration.get("fusion_strategy")
        != "equal_weight_probability_late_fusion"
        or configuration.get("fusion_weights") != [0.5, 0.5]
    ):
        raise DevelopmentBoundaryError(
            "only frozen equal-weight CODE+TEXT is permitted"
        )
    if configuration.get("seed_set") != [0, 7, 13, 21, 42, 73, 101, 202]:
        raise DevelopmentBoundaryError("predeclared seed set mismatch")
    if configuration.get("bootstrap_replicates") != 1000 or configuration.get(
        "training_fractions"
    ) != [1.0, 0.9, 0.8]:
        raise DevelopmentBoundaryError("predeclared robustness protocol mismatch")


def verify_identities(root: Path, configuration: dict[str, Any]) -> dict[str, str]:
    canonical = json.loads(
        (root / "audits/jit-defects4j-canonical/1.0.0/audit.json").read_text()
    )
    adapter = json.loads(
        (root / "audits/jit-defects4j-adapters/1.0.0/audit.json").read_text()
    )
    baseline = json.loads(
        (
            root / "audits/jit-defects4j-controlled-baselines/1.0.0/audit.json"
        ).read_text()
    )
    fusion = json.loads(
        (
            root / "audits/jit-defects4j-controlled-multimodal-fusion/1.0.0/audit.json"
        ).read_text()
    )
    actual = {
        "dataset_identity": canonical["scientific_identity_digest"],
        "canonical_manifest_sha256": canonical["manifest_sha256"],
        "frozen_boundary_identity": adapter["source"]["input_identity"],
        "adapter_identity": adapter["configuration_sha256"],
        "baseline_result_identity": baseline["results_identity_digest"],
        "fusion_result_identity": fusion["results_identity_digest"],
    }
    if actual != configuration.get("expected_identities"):
        raise DevelopmentBoundaryError("frozen scientific identity mismatch")
    if (
        not baseline["test_sealed"]
        or not fusion["test_sealed"]
        or adapter["test_sealing"]["test_matrix_materialized"]
    ):
        raise DevelopmentBoundaryError("prior artifacts do not prove TEST sealing")
    return actual


def _selected_runs(root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    audit = json.loads(
        (
            root / "audits/jit-defects4j-controlled-baselines/1.0.0/audit.json"
        ).read_text()
    )
    runs = {run["candidate_id"]: run for run in audit["candidate_models"]}
    return (
        audit,
        runs[audit["selected_development_candidates"]["CODE"]],
        runs[audit["selected_development_candidates"]["TEXT"]],
    )


def _scores(
    inputs: DevelopmentInputs,
    code_run: dict[str, Any],
    text_run: dict[str, Any],
    seed: int,
    indices: np.ndarray | None = None,
) -> dict[str, np.ndarray]:
    train, validation = inputs.partition("train"), inputs.partition("validation")
    y = np.asarray(train["targets"], dtype=int)
    take = np.arange(len(y)) if indices is None else indices
    code_train, code_validation = (
        _matrix(train, "CODE")[take],
        _matrix(validation, "CODE"),
    )
    scaler = StandardScaler().fit(code_train)
    code_settings = {**code_run["hyperparameters"], "random_state": seed}
    code = RandomForestModel(
        (0, 1),
        modality="CODE",
        configuration=RandomForestConfiguration(**code_settings).to_dict(),
    )
    code.fit(scaler.transform(code_train), y[take])
    text_settings = {**text_run["hyperparameters"], "random_state": seed}
    text = LogisticRegressionModel(
        (0, 1),
        modality="TEXT",
        configuration=LogisticRegressionConfiguration(**text_settings).to_dict(),
    )
    text.fit(_matrix(train, "TEXT")[take], y[take])
    values = {
        "CODE": np.asarray(code.predict_proba(scaler.transform(code_validation)))[:, 1],
        "TEXT": np.asarray(text.predict_proba(_matrix(validation, "TEXT")))[:, 1],
    }
    values["CODE+TEXT"] = _fuse(values, ("CODE", "TEXT"), [0.5, 0.5])
    return values


def _two_metrics(y: np.ndarray, scores: np.ndarray) -> dict[str, float]:
    return {
        "roc_auc": float(roc_auc_score(y, scores)),
        "average_precision": float(average_precision_score(y, scores)),
    }


def _condition(
    y: np.ndarray, scores: dict[str, np.ndarray], **metadata: Any
) -> dict[str, Any]:
    metrics = {name: _two_metrics(y, value) for name, value in scores.items()}
    return {
        **metadata,
        "metrics": metrics,
        "delta_vs_best_unimodal": {
            metric: metrics["CODE+TEXT"][metric]
            - max(metrics["CODE"][metric], metrics["TEXT"][metric])
            for metric in ("roc_auc", "average_precision")
        },
    }


def paired_bootstrap(
    y: np.ndarray, scores: dict[str, np.ndarray], replicates: int, seed: int
) -> dict[str, Any]:
    rng = np.random.RandomState(seed)
    values = {
        comparison: {metric: [] for metric in ("roc_auc", "average_precision")}
        for comparison in ("CODE+TEXT_minus_CODE", "CODE+TEXT_minus_TEXT")
    }
    completed = 0
    while completed < replicates:
        idx = rng.randint(0, len(y), len(y))
        if np.unique(y[idx]).size != 2:
            continue
        for base in ("CODE", "TEXT"):
            values[f"CODE+TEXT_minus_{base}"]["roc_auc"].append(
                roc_auc_score(y[idx], scores["CODE+TEXT"][idx])
                - roc_auc_score(y[idx], scores[base][idx])
            )
            values[f"CODE+TEXT_minus_{base}"]["average_precision"].append(
                average_precision_score(y[idx], scores["CODE+TEXT"][idx])
                - average_precision_score(y[idx], scores[base][idx])
            )
        completed += 1
    result: dict[str, Any] = {}
    for comparison, metric_values in values.items():
        result[comparison] = {}
        for metric, raw in metric_values.items():
            a = np.asarray(raw)
            result[comparison][metric] = {
                "mean": float(a.mean()),
                "median": float(np.median(a)),
                "percentile_2_5": float(np.percentile(a, 2.5)),
                "percentile_97_5": float(np.percentile(a, 97.5)),
                "proportion_delta_gt_zero": float(np.mean(a > 0)),
            }
    return {
        "replicates": replicates,
        "seed": seed,
        "scope": "VALIDATION development evidence only",
        "comparisons": result,
    }


def project_analysis(
    inputs: DevelopmentInputs, scores: dict[str, np.ndarray]
) -> dict[str, Any]:
    y = np.asarray(inputs.validation["targets"], dtype=int)
    projects = np.asarray([identity[0] for identity in inputs.validation["identities"]])
    rows = []
    counts = {
        metric: {
            "fusion_gt_code": 0,
            "fusion_gt_text": 0,
            "ties_vs_code": 0,
            "ties_vs_text": 0,
            "fusion_degrades_vs_code": 0,
            "fusion_degrades_vs_text": 0,
        }
        for metric in ("roc_auc", "average_precision")
    }
    for project in sorted(set(projects)):
        idx = np.flatnonzero(projects == project)
        positives = int(y[idx].sum())
        negatives = int(len(idx) - positives)
        evaluable = positives > 0 and negatives > 0
        metrics = {
            name: (
                _two_metrics(y[idx], value[idx])
                if evaluable
                else {"roc_auc": None, "average_precision": None}
            )
            for name, value in scores.items()
        }
        rows.append(
            {
                "project": project,
                "observations": len(idx),
                "positive": positives,
                "nominal_negative": negatives,
                "prevalence": float(y[idx].mean()),
                "evaluable": evaluable,
                "metrics": metrics,
            }
        )
        if evaluable:
            for metric in counts:
                for base, suffix in (("CODE", "code"), ("TEXT", "text")):
                    delta = metrics["CODE+TEXT"][metric] - metrics[base][metric]
                    counts[metric][
                        (
                            "fusion_gt_"
                            if delta > 0
                            else "fusion_degrades_vs_"
                            if delta < 0
                            else "ties_vs_"
                        )
                        + suffix
                    ] += 1
    evaluable_rows = [row for row in rows if row["evaluable"]]
    aggregate_without_each = []
    for row in evaluable_rows:
        idx = np.flatnonzero(projects != row["project"])
        aggregate_without_each.append(
            {
                "excluded_project": row["project"],
                "delta_vs_best_unimodal": _condition(
                    y[idx], {name: value[idx] for name, value in scores.items()}
                )["delta_vs_best_unimodal"],
            }
        )
    return {
        "projects": rows,
        "evaluable_projects": len(evaluable_rows),
        "undefined_projects": len(rows) - len(evaluable_rows),
        "comparison_counts": counts,
        "leave_one_project_out_aggregate": aggregate_without_each,
    }


def _stratified_indices(y: np.ndarray, fraction: float, seed: int) -> np.ndarray:
    if fraction == 1.0:
        return np.arange(len(y))
    selected, _ = train_test_split(
        np.arange(len(y)),
        train_size=fraction,
        random_state=seed,
        shuffle=True,
        stratify=y,
    )
    return np.sort(selected)


def run_robustness(
    root: Path, inputs: DevelopmentInputs, configuration: dict[str, Any]
) -> dict[str, Any]:
    validate_configuration(configuration)
    identities = verify_identities(root, configuration)
    baseline, code_run, text_run = _selected_runs(root)
    y = np.asarray(inputs.validation["targets"], dtype=int)
    seed_rows = [
        _condition(y, _scores(inputs, code_run, text_run, seed), seed=seed)
        for seed in configuration["seed_set"]
    ]
    reference_scores = _scores(inputs, code_run, text_run, 0)
    fraction_rows = []
    train_y = np.asarray(inputs.train["targets"], dtype=int)
    for fraction in configuration["training_fractions"]:
        rows = []
        for seed in configuration["training_fraction_seeds"]:
            idx = _stratified_indices(train_y, fraction, seed)
            rows.append(
                _condition(
                    y,
                    _scores(inputs, code_run, text_run, seed, idx),
                    seed=seed,
                    train_observations=len(idx),
                    train_positive=int(train_y[idx].sum()),
                    train_nominal_negative=int((train_y[idx] == 0).sum()),
                )
            )
        fraction_rows.append(
            {
                "fraction": fraction,
                "runs": rows,
                "median_delta_vs_best_unimodal": {
                    metric: float(
                        np.median(
                            [row["delta_vs_best_unimodal"][metric] for row in rows]
                        )
                    )
                    for metric in ("roc_auc", "average_precision")
                },
            }
        )
    bootstrap = paired_bootstrap(
        y,
        reference_scores,
        configuration["bootstrap_replicates"],
        configuration["bootstrap_seed"],
    )
    projects = project_analysis(inputs, reference_scores)
    median_seed_delta = {
        metric: float(
            np.median([row["delta_vs_best_unimodal"][metric] for row in seed_rows])
        )
        for metric in ("roc_auc", "average_precision")
    }
    bootstrap_clear = all(
        bootstrap["comparisons"][comparison][metric]["proportion_delta_gt_zero"]
        >= configuration["bootstrap_positive_threshold"]
        for comparison in bootstrap["comparisons"]
        for metric in ("roc_auc", "average_precision")
    )
    no_single_project_drives = all(
        all(
            item["delta_vs_best_unimodal"][metric] > 0
            for item in projects["leave_one_project_out_aggregate"]
        )
        for metric in ("roc_auc", "average_precision")
    )
    reductions_positive = all(
        item["median_delta_vs_best_unimodal"][metric] > 0
        for item in fraction_rows[1:]
        for metric in ("roc_auc", "average_precision")
    )
    seed_positive = all(median_seed_delta[metric] > 0 for metric in median_seed_delta)
    decision = (
        "GO"
        if seed_positive
        and bootstrap_clear
        and no_single_project_drives
        and reductions_positive
        else "GO_WITH_LIMITATIONS"
        if seed_positive
        else "NO_GO"
    )
    limitations = [
        "All inference is restricted to frozen VALIDATION development evidence; TEST remains sealed.",
        "Bootstrap percentile intervals are development-set stability intervals, not final population confidence intervals.",
        "Project-level estimates are heterogeneous and some projects have few positives.",
        "Training reduction is a sensitivity analysis, not model selection.",
        "Probabilities remain uncalibrated.",
    ]
    payload = {
        "schema_version": "jit-defects4j-robustness-1.0.0",
        "sprint": "10.8.2.27",
        "branch": configuration["branch"],
        **identities,
        "configuration_digest": digest(configuration),
        "test_sealed": True,
        "primary_candidate": "CODE+TEXT",
        "fusion_strategy": "equal_weight_probability_late_fusion",
        "train": baseline["train"],
        "validation": baseline["validation"],
        "test_metadata_inherited_only": {
            "observations": 4119,
            "positive": 160,
            "nominal_negative": 3959,
        },
        "seed_analysis": {
            "seeds": configuration["seed_set"],
            "runs": seed_rows,
            "median_delta_vs_best_unimodal": median_seed_delta,
        },
        "bootstrap_analysis": bootstrap,
        "project_analysis": projects,
        "training_fraction_analysis": {"fractions": fraction_rows},
        "primary_deltas": {
            "reference_seed_0": _condition(y, reference_scores)[
                "delta_vs_best_unimodal"
            ],
            "median_seed": median_seed_delta,
        },
        "decision_criteria": {
            "median_both_positive": seed_positive,
            "seed_no_systematic_collapse": seed_positive,
            "bootstrap_clear_majority": bootstrap_clear,
            "not_driven_solely_by_one_project": no_single_project_drives,
            "moderate_reductions_preserve_advantage": reductions_positive,
        },
        "decision": decision,
        "limitations": limitations,
        "process_status": "OPTIONAL ABLATION / NOT SUPPORTED AS PRIMARY CONTRIBUTOR UNDER CURRENT REPRESENTATION",
        "test_seal_checks": {
            "predictors_loaded": False,
            "matrices_transformed": False,
            "probabilities_generated": False,
            "metrics_calculated": False,
            "used_in_bootstrap": False,
            "used_in_project_analysis": False,
            "used_in_thresholding": False,
            "used_in_model_selection": False,
        },
        "leakage_audit": {
            "target_derived_predictor": False,
            "fixing_status_predictor": False,
            "szz_output_predictor": False,
            "future_defect_information": False,
            "split_membership_predictor": False,
            "issue_linkage_field": False,
            "post_observation_label_information": False,
            "text_vocabulary_fit_partition": "train",
            "preprocessing_fit_partition": "train",
            "project_identifier_predictor": False,
            "result": "pass",
        },
        "prohibited_actions_confirmation": {
            item: False for item in configuration["prohibited_operations"]
        },
        "recommended_next_sprint": "Sprint 10.8.2.28 — Freeze Robust Multimodal Architecture and Predeclare Calibration Protocol"
        if decision == "GO"
        else "Freeze CODE+TEXT with explicit robustness caveats or perform one narrowly scoped robustness-resolution sprint."
        if decision == "GO_WITH_LIMITATIONS"
        else "Return to representation/fusion design without opening TEST.",
    }
    return {**payload, "results_identity_digest": digest(payload)}


__all__ = [
    "canonical_bytes",
    "digest",
    "load_development_inputs",
    "paired_bootstrap",
    "project_analysis",
    "run_robustness",
    "validate_configuration",
    "verify_identities",
]
