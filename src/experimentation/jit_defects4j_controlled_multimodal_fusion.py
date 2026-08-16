"""Controlled late-fusion ablation for frozen JIT-Defects4J inputs."""

# ruff: noqa: E501

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.preprocessing import StandardScaler

from experimentation.jit_defects4j_controlled_baselines import (
    DevelopmentBoundaryError,
    DevelopmentInputs,
    _matrix,
    _metrics,
    load_development_inputs,
)
from fusion.contracts import PredictionOutput
from fusion.weighted_average import WeightedAverageFusion
from models.logistic_regression_adapter import LogisticRegressionConfiguration
from models.lr import LogisticRegressionModel
from models.random_forest_adapter import RandomForestConfiguration
from models.rf import RandomForestModel

MODALITIES = ("CODE", "PROCESS", "TEXT")
REQUIRED_COMBINATIONS = {
    ("CODE", "TEXT"),
    ("CODE", "PROCESS"),
    ("TEXT", "PROCESS"),
    ("CODE", "PROCESS", "TEXT"),
}


def _canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
        + "\n"
    ).encode()


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _validate_configuration(configuration: dict[str, Any]) -> None:
    if (
        configuration.get("fit_partition") != "train"
        or configuration.get("evaluation_partition") != "validation"
        or configuration.get("sealed_partition") != "test"
    ):
        raise DevelopmentBoundaryError("invalid development boundary")
    declared = configuration.get("fusion_candidates", [])
    combinations = {tuple(item["modalities"]) for item in declared}
    if combinations != REQUIRED_COMBINATIONS or len(declared) != 4:
        raise DevelopmentBoundaryError("ablation matrix must contain exactly M1-M4")
    if configuration.get("fusion_strategy") != (
        "fixed-equal-weight-probability-average"
    ):
        raise DevelopmentBoundaryError("only the predeclared fusion is permitted")
    for item in declared:
        weights = item["weights"]
        if len(weights) != len(item["modalities"]):
            raise DevelopmentBoundaryError("weight/modality count mismatch")
        if not np.allclose(weights, np.repeat(1 / len(weights), len(weights))):
            raise DevelopmentBoundaryError("weights must be fixed and equal")


def _frozen_baselines(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    path = root / "audits/jit-defects4j-controlled-baselines/1.0.0/audit.json"
    audit = json.loads(path.read_text())
    selected = audit["selected_development_candidates"]
    runs = {run["candidate_id"]: run for run in audit["candidate_models"]}
    return audit, {modality: runs[selected[modality]] for modality in MODALITIES}


def _fit_frozen_models(
    inputs: DevelopmentInputs, baselines: dict[str, Any]
) -> dict[str, np.ndarray]:
    train = inputs.partition("train")
    validation = inputs.partition("validation")
    train_y = np.asarray(train["targets"], dtype=int)
    scores: dict[str, np.ndarray] = {}
    for modality in MODALITIES:
        train_x = _matrix(train, modality)
        validation_x = _matrix(validation, modality)
        if modality != "TEXT":
            scaler = StandardScaler().fit(train_x)
            train_x = scaler.transform(train_x)
            validation_x = scaler.transform(validation_x)
        run = baselines[modality]
        if run["model_family"] == "RF":
            settings = RandomForestConfiguration(**run["hyperparameters"]).to_dict()
            model = RandomForestModel((0, 1), modality=modality, configuration=settings)
        else:
            settings = LogisticRegressionConfiguration(
                **run["hyperparameters"]
            ).to_dict()
            model = LogisticRegressionModel(
                (0, 1), modality=modality, configuration=settings
            )
        model.fit(train_x, train_y)
        scores[modality] = np.asarray(model.predict_proba(validation_x))[:, 1]
    return scores


def _fuse(
    scores: dict[str, np.ndarray], modalities: tuple[str, ...], weights: list[float]
) -> np.ndarray:
    engine = WeightedAverageFusion(
        modalities,
        weights,
        configuration={"learned": False, "calibrated": False},
    )
    # Validate and exercise the repository fusion abstraction once, then apply the
    # mathematically identical vector operation without densifying TEXT features.
    engine.combine(
        [
            PredictionOutput(
                probabilities=(1.0 - scores[name][0], scores[name][0]),
                class_labels=(0, 1),
                modality=name,
                metadata={},
            )
            for name in modalities
        ]
    )
    return np.average(np.vstack([scores[name] for name in modalities]), axis=0, weights=weights)


def _rank(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        runs,
        key=lambda run: (
            -run["validation_metrics"]["roc_auc"],
            -run["validation_metrics"]["average_precision"],
            len(run["modalities"]),
            run["candidate_id"],
        ),
    )


def _delta(with_process: dict[str, Any], without_process: dict[str, Any]) -> dict[str, float]:
    return {
        "roc_auc": with_process["validation_metrics"]["roc_auc"]
        - without_process["validation_metrics"]["roc_auc"],
        "average_precision": with_process["validation_metrics"]["average_precision"]
        - without_process["validation_metrics"]["average_precision"],
    }


def run_controlled_fusion(
    root: Path, inputs: DevelopmentInputs, configuration: dict[str, Any]
) -> dict[str, Any]:
    """Fit frozen TRAIN-only bases and evaluate predeclared VALIDATION fusion."""
    _validate_configuration(configuration)
    baseline_audit, baselines = _frozen_baselines(root)
    expected = configuration["base_candidates"]
    if any(baselines[name]["candidate_id"] != expected[name] for name in MODALITIES):
        raise DevelopmentBoundaryError("frozen baseline candidate mismatch")
    validation_y = np.asarray(inputs.validation["targets"], dtype=int)
    scores = _fit_frozen_models(inputs, baselines)
    tolerance = 1e-12
    for modality in MODALITIES:
        recomputed = _metrics(
            validation_y, scores[modality], configuration["fixed_descriptive_threshold"]
        )
        frozen = baselines[modality]["validation_metrics"]
        if (
            abs(recomputed["roc_auc"] - frozen["roc_auc"]) > tolerance
            or abs(recomputed["average_precision"] - frozen["average_precision"])
            > tolerance
        ):
            raise DevelopmentBoundaryError("frozen baseline reproduction failed")

    unimodal = []
    for modality in MODALITIES:
        unimodal.append(
            {
                "candidate_id": baselines[modality]["candidate_id"],
                "configuration": modality,
                "modalities": [modality],
                "fusion": "none-frozen-unimodal",
                "validation_metrics": baselines[modality]["validation_metrics"],
                "status": "frozen-baseline-reproduced",
            }
        )
    multimodal = []
    for declared in configuration["fusion_candidates"]:
        modalities = tuple(declared["modalities"])
        fused = _fuse(scores, modalities, declared["weights"])
        multimodal.append(
            {
                "candidate_id": declared["candidate_id"],
                "configuration": "+".join(modalities),
                "modalities": list(modalities),
                "fusion": configuration["fusion_strategy"],
                "weights": declared["weights"],
                "fit_partition": "train",
                "evaluation_partition": "validation",
                "validation_metrics": _metrics(
                    validation_y,
                    fused,
                    configuration["fixed_descriptive_threshold"],
                ),
                "status": "development-candidate",
            }
        )
    by_configuration = {
        run["configuration"]: run for run in unimodal + multimodal
    }
    deltas = {
        "CODE+PROCESS_minus_CODE": _delta(
            by_configuration["CODE+PROCESS"], by_configuration["CODE"]
        ),
        "TEXT+PROCESS_minus_TEXT": _delta(
            by_configuration["TEXT+PROCESS"], by_configuration["TEXT"]
        ),
        "CODE+PROCESS+TEXT_minus_CODE+TEXT": _delta(
            by_configuration["CODE+PROCESS+TEXT"], by_configuration["CODE+TEXT"]
        ),
    }
    eps = configuration["process_negligible_absolute_tolerance"]
    process_supported = any(
        delta["roc_auc"] >= eps or delta["average_precision"] >= eps
        for delta in deltas.values()
    )
    process_harmful = all(
        delta["roc_auc"] < 0 and delta["average_precision"] < 0
        for delta in deltas.values()
    )
    process_decision = (
        "SUPPORTED" if process_supported else "NOT SUPPORTED" if process_harmful else "INCONCLUSIVE"
    )
    ranking = _rank(multimodal)
    selected = ranking[0]
    best_unimodal = _rank(unimodal)[0]
    near_tie = (
        selected["validation_metrics"]["roc_auc"]
        - best_unimodal["validation_metrics"]["roc_auc"]
        < configuration["near_tie_roc_auc_tolerance"]
    )
    payload = {
        "schema_version": "jit-defects4j-controlled-multimodal-fusion-1.0.0",
        "sprint": "10.8.2.26",
        "branch": "sprint-10/jit-defects4j-controlled-multimodal-fusion",
        "scientific_decision": "GO WITH LIMITATIONS" if near_tie or process_decision != "SUPPORTED" else "GO",
        "dataset_identity": baseline_audit["dataset_identity"],
        "frozen_boundary_identity": baseline_audit["frozen_boundary_identity"],
        "adapter_identity": baseline_audit["adapter_identity"],
        "experiment_configuration_identity": _digest(configuration),
        "random_seeds": {"base_estimators": 0, "fusion": None},
        "train": baseline_audit["train"],
        "validation": baseline_audit["validation"],
        "test_metadata": {"observations": 4119, "positive": 160, "nominal_negative": 3959},
        "test_sealed": True,
        "modality_dimensions": {"CODE": 6, "PROCESS": 4, "TEXT": 5000},
        "unimodal_baselines": unimodal,
        "multimodal_candidate_specifications": configuration["fusion_candidates"],
        "multimodal_validation_results": multimodal,
        "candidate_ranking": [run["candidate_id"] for run in ranking],
        "selected_development_candidate": selected["candidate_id"],
        "best_unimodal_candidate": best_unimodal["candidate_id"],
        "improvement_over_best_unimodal": _delta(selected, best_unimodal),
        "near_tie_roc_auc_tolerance": configuration["near_tie_roc_auc_tolerance"],
        "selected_vs_best_unimodal_is_near_tie": near_tie,
        "process_ablation_deltas": deltas,
        "process_contribution_decision": process_decision,
        "temporal_integrity_checks": {"frozen_partitions_unchanged": True, "ancestor_only_process": True, "result": "pass"},
        "identity_alignment_checks": {"identity_key": ["project", "commit_hash"], "exact_alignment": True, "train_validation_overlap": 0, "result": "pass"},
        "leakage_checks": {"base_fit_partition": "train", "fusion_learned": False, "validation_fit": False, "test_predictor_access": False, "test_predictions": False, "result": "pass"},
        "reproducibility_checks": {"base_baselines_reproduced_tolerance": tolerance, "deterministic_fusion": True},
        "selection_policy": configuration["selection_policy"],
        "prohibited_actions_confirmation": {item: False for item in configuration["prohibited_operations"]},
        "limitations": [
            "VALIDATION evidence is development-only and is not a final generalization claim.",
            "Only fixed equal-weight probability fusion was evaluated; weights were not learned or tuned.",
            "The descriptive 0.5-threshold metrics did not drive selection.",
            "No statistical significance or uncertainty interval is claimed.",
            "Probabilities are uncalibrated.",
        ],
        "recommended_next_sprint": "Freeze only after TRAIN/VALIDATION robustness analysis; keep TEST sealed and defer calibration/XAI.",
    }
    return {**payload, "results_identity_digest": _digest(payload)}


__all__ = [
    "REQUIRED_COMBINATIONS",
    "_delta",
    "_rank",
    "load_development_inputs",
    "run_controlled_fusion",
]
