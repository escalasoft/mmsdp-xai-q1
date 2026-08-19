"""Execute the frozen VALIDATION-only JIT-Defects4J calibration protocol."""

# ruff: noqa: E501

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.model_selection import StratifiedKFold

from calibration.jit_defects4j_calibration_protocol import (
    CalibrationProtocolError,
    expected_calibration_error,
    identity,
    load_and_validate,
    select_method,
)
from experimentation.jit_defects4j_controlled_baselines import (
    DevelopmentInputs,
    _matrix,
    load_development_inputs,
)
from experimentation.jit_defects4j_controlled_multimodal_fusion import (
    _fit_frozen_models,
    _frozen_baselines,
)


def _validate_execution(configuration: dict[str, Any]) -> None:
    expected = {
        "branch": "sprint-10/jit-defects4j-calibration-execution",
        "candidates": ["UNCALIBRATED", "PLATT", "ISOTONIC"],
        "test_access": False,
        "threshold_optimization": False,
        "final_refit_execution": False,
    }
    if any(configuration.get(key) != value for key, value in expected.items()):
        raise CalibrationProtocolError("calibration execution contract changed")
    if configuration.get("platt_implementation") != {
        "class": "sklearn.linear_model.LogisticRegression",
        "solver": "liblinear",
        "random_state": 0,
    }:
        raise CalibrationProtocolError("Platt implementation changed")
    if configuration.get("isotonic_implementation") != {
        "class": "sklearn.isotonic.IsotonicRegression",
        "out_of_bounds": "clip",
    }:
        raise CalibrationProtocolError("isotonic implementation changed")


def reliability_bins(y: np.ndarray, p: np.ndarray) -> list[dict[str, Any]]:
    assignments = np.minimum((p * 10).astype(int), 9)
    rows = []
    for index in range(10):
        selected = assignments == index
        if selected.any():
            rows.append(
                {
                    "bin_index": index,
                    "lower_bound": index / 10,
                    "upper_bound": (index + 1) / 10,
                    "upper_bound_inclusive": index == 9,
                    "observation_count": int(selected.sum()),
                    "mean_predicted_probability": float(p[selected].mean()),
                    "observed_positive_fraction": float(y[selected].mean()),
                }
            )
    return rows


def _calibrate_oof(
    y: np.ndarray, raw: np.ndarray, method: str, protocol: dict[str, Any]
) -> tuple[np.ndarray, list[dict[str, Any]]]:
    if method == "UNCALIBRATED":
        return raw.copy(), []
    cross = protocol["cross_fitting"]
    splitter = StratifiedKFold(
        n_splits=cross["folds"],
        shuffle=cross["shuffle"],
        random_state=cross["random_seed"],
    )
    oof = np.full(len(y), np.nan)
    coverage = np.zeros(len(y), dtype=int)
    folds = []
    for fold, (fit, held_out) in enumerate(splitter.split(raw, y)):
        fit_pos = int(y[fit].sum())
        fit_neg = int(len(fit) - fit_pos)
        eval_pos = int(y[held_out].sum())
        eval_neg = int(len(held_out) - eval_pos)
        if (
            fit_pos < cross["minimum_fit_positives"]
            or fit_neg < cross["minimum_fit_negatives"]
            or eval_pos < cross["minimum_evaluation_positives"]
            or eval_neg < cross["minimum_evaluation_negatives"]
        ):
            raise CalibrationProtocolError("pathological calibration fold")
        if method == "PLATT":
            estimator = LogisticRegression(random_state=0, solver="liblinear")
            estimator.fit(raw[fit].reshape(-1, 1), y[fit])
            values = estimator.predict_proba(raw[held_out].reshape(-1, 1))[:, 1]
        else:
            if np.unique(raw[fit]).size < 2:
                raise CalibrationProtocolError("ISOTONIC fit fold is infeasible")
            estimator = IsotonicRegression(out_of_bounds="clip")
            estimator.fit(raw[fit], y[fit])
            values = estimator.predict(raw[held_out])
        oof[held_out] = values
        coverage[held_out] += 1
        folds.append(
            {
                "fold": fold,
                "fit_count": len(fit),
                "fit_positive": fit_pos,
                "fit_nominal_negative": fit_neg,
                "held_out_count": len(held_out),
                "held_out_positive": eval_pos,
                "held_out_nominal_negative": eval_neg,
                "fit_held_out_overlap": int(np.intersect1d(fit, held_out).size),
            }
        )
    if not np.all(coverage == 1) or not np.isfinite(oof).all():
        raise CalibrationProtocolError("OOF coverage must be exactly once")
    if ((oof < 0) | (oof > 1)).any():
        raise CalibrationProtocolError("calibrated probability outside [0,1]")
    return oof, folds


def _raw_probabilities(
    root: Path, inputs: DevelopmentInputs, architecture: dict[str, Any]
) -> np.ndarray:
    baseline_audit, baselines = _frozen_baselines(root)
    for modality in ("CODE", "TEXT"):
        frozen = architecture["base_predictors"][modality]
        run = baselines[modality]
        if (
            run["candidate_id"] != frozen["candidate_id"]
            or run["configuration_digest"] != frozen["configuration_digest"]
            or run["preprocessing_state_digest"]
            != frozen["preprocessing_state_digest"]
        ):
            raise CalibrationProtocolError(f"frozen {modality} identity mismatch")
    if not baseline_audit["test_sealed"]:
        raise CalibrationProtocolError("upstream TEST seal failed")
    scores = _fit_frozen_models(inputs, baselines)
    raw = 0.5 * scores["CODE"] + 0.5 * scores["TEXT"]
    if not np.isfinite(raw).all() or ((raw < 0) | (raw > 1)).any():
        raise CalibrationProtocolError("invalid frozen fusion probabilities")
    return raw


def run_calibration_execution(
    root: Path, inputs: DevelopmentInputs, configuration: dict[str, Any]
) -> dict[str, Any]:
    _validate_execution(configuration)
    architecture, protocol = load_and_validate(root)
    if identity(architecture) != configuration["architecture_identity"]:
        raise CalibrationProtocolError("architecture identity mismatch")
    if identity(protocol) != configuration["protocol_identity"]:
        raise CalibrationProtocolError("protocol identity mismatch")
    y = np.asarray(inputs.validation["targets"], dtype=int)
    if (len(y), int(y.sum())) != (4086, 260):
        raise CalibrationProtocolError("VALIDATION population changed")
    if _matrix(inputs.validation, "CODE").shape != (4086, 6):
        raise CalibrationProtocolError("CODE representation changed")
    raw = _raw_probabilities(root, inputs, architecture)
    robustness = json.loads(
        (root / "audits/jit-defects4j-robustness/1.0.0/audit.json").read_text()
    )
    reference = robustness["seed_analysis"]["runs"][0]
    if reference["seed"] != 0:
        raise CalibrationProtocolError("frozen raw-probability reference changed")
    reproduced_raw = {
        "roc_auc": float(roc_auc_score(y, raw)),
        "average_precision": float(average_precision_score(y, raw)),
    }
    if any(
        abs(reproduced_raw[metric] - reference["metrics"]["CODE+TEXT"][metric])
        > 1e-12
        for metric in reproduced_raw
    ):
        raise CalibrationProtocolError("frozen raw fusion reproduction failed")
    results = {}
    fold_evidence = {}
    for method in configuration["candidates"]:
        probabilities, folds = _calibrate_oof(y, raw, method, protocol)
        results[method] = {
            "brier": float(brier_score_loss(y, probabilities)),
            "ece": expected_calibration_error(y, probabilities),
            "roc_auc": float(roc_auc_score(y, probabilities)),
            "average_precision": float(average_precision_score(y, probabilities)),
            "reliability_bins": reliability_bins(y, probabilities),
            "probability_digest": identity(probabilities.tolist()),
        }
        fold_evidence[method] = folds
    selected = select_method(results)
    payload = {
        "schema_version": "jit-defects4j-calibration-execution-audit-1.0.0",
        "sprint": "10.8.2.29",
        "repository": "MMSDP-XAI-Q1",
        "branch": configuration["branch"],
        "frozen_architecture_identity": identity(architecture),
        "calibration_protocol_identity": identity(protocol),
        "dataset_identity": architecture["dataset"]["identity"],
        "manifest_identity": architecture["dataset"]["manifest_sha256"],
        "temporal_boundary_identity": architecture["dataset"]["frozen_boundary_identity"],
        "adapter_identity": architecture["dataset"]["adapter_identity"],
        "frozen_robustness_result_identity": architecture["prior_evidence"]["result_identity"],
        "execution_configuration_identity": identity(configuration),
        "architecture": "CODE RF + TEXT LR; fixed 0.5/0.5 late probability fusion",
        "raw_fusion_reproduction": {
            "reference": "Sprint 10.8.2.27 seed-0 CODE+TEXT",
            "absolute_tolerance": 1e-12,
            "metrics": reproduced_raw,
            "result": "pass",
        },
        "validation": {
            "observations": len(y),
            "positive": int(y.sum()),
            "nominal_negative": int((y == 0).sum()),
            "prevalence": float(y.mean()),
            "canonical_order_preserved": True,
        },
        "candidates": configuration["candidates"],
        "cross_fitting": {**protocol["cross_fitting"], "fold_evidence": fold_evidence},
        "metrics": results,
        "selected_calibrator": selected,
        "selection_rationale": "lowest OOF VALIDATION Brier; ECE only within absolute 1e-12 Brier tie; final order UNCALIBRATED, PLATT, ISOTONIC",
        "discrimination_selection_use": False,
        "reliability_reference": "identity diagonal y=x; diagnostic only",
        "leakage_audit": {
            "target_as_predictor": False,
            "fixing_or_szz_as_predictor": False,
            "future_information_as_predictor": False,
            "issue_linkage_as_predictor": False,
            "project_identifier_as_predictor": False,
            "split_identifier_as_predictor": False,
            "text_preprocessing_fit_partition": "TRAIN",
            "base_model_fit_partition": "TRAIN",
            "calibration_fit_partition": "VALIDATION OOF fit folds only",
            "each_validation_observation_calibrated_without_own_label": True,
            "train_validation_identity_overlap": 0,
            "test_information_used": False,
            "provenance_traceable": True,
            "result": "pass",
        },
        "test_sealed": True,
        "threshold_optimization_executed": False,
        "final_refit_executed": False,
        "limitations": [
            "Selection evidence is development-only VALIDATION evidence.",
            "OOF calibrated discrimination can change across fold-specific mappings; isotonic may also introduce ties.",
            "Final generalization is unknown because TEST remains sealed.",
        ],
        "next_step_declaration": {
            "sprint": "10.8.2.30",
            "execute_now": False,
            "procedure": [
                "Freeze this audit and selected calibrator identity before any TEST access.",
                "Use exactly the existing canonical TRAIN and VALIDATION observations, pooled only for final base-model refit.",
                "Refit CODE StandardScaler on TRAIN+VALIDATION six frozen CODE features and refit the frozen RF configuration.",
                "Refit the frozen 5,000-feature unigram TF-IDF vocabulary/state on TRAIN+VALIDATION text only and refit the frozen liblinear LR configuration.",
                "Generate raw probabilities by fixed p=0.5*p_CODE+0.5*p_TEXT.",
                "Fit the selected calibrator once on the original TRAIN-fitted model's full canonical VALIDATION raw probabilities and labels; if UNCALIBRATED, retain identity mapping.",
                "Open TEST only after all refitted model, representation, fusion, calibration, metric, and threshold contracts are frozen and independently validated.",
                "Evaluate TEST exactly once and report ROC-AUC, Average Precision, Brier Score, and fixed-bin ECE; any threshold metrics require a separately predeclared frozen threshold.",
                "Make no post-TEST model, calibrator, feature, fusion-weight, or threshold changes.",
            ],
        },
    }
    return {**payload, "result_digest": identity(payload)}


def load_inputs(root: Path) -> DevelopmentInputs:
    """Expose the sealed development loader for the sprint runner."""
    return load_development_inputs(root)


def load_configuration(root: Path) -> dict[str, Any]:
    return json.loads(
        (root / "configs/experiments/jit_defects4j_calibration_execution_1.0.0.json").read_text()
    )


__all__ = [
    "load_configuration",
    "load_inputs",
    "reliability_bins",
    "run_calibration_execution",
]
