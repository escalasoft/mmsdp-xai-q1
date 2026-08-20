"""Fail-closed final-refit compatibility audit; TEST predictive data is unreachable."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.isotonic import IsotonicRegression

from calibration.jit_defects4j_calibration_execution import _raw_probabilities
from calibration.jit_defects4j_calibration_protocol import identity, load_and_validate
from experimentation.jit_defects4j_controlled_baselines import (
    DevelopmentBoundaryError,
    DevelopmentInputs,
    load_development_inputs,
)


class FinalRefitAuditError(RuntimeError):
    """A frozen-contract, compatibility, leakage, or TEST-seal violation."""


def _read(root: Path, relative: str) -> dict[str, Any]:
    return json.loads((root / relative).read_text(encoding="utf-8"))


def _validate(configuration: dict[str, Any]) -> None:
    required = {
        "branch": "sprint-10/jit-defects4j-final-refit-audit",
        "selected_procedure": "A_NO_BASE_REFIT",
        "selected_calibration_method": "ISOTONIC",
        "base_fit_population": "TRAIN",
        "calibration_fit_population": "full canonical VALIDATION",
        "text_fit_population": "TRAIN",
        "fusion_weights": {"CODE": 0.5, "TEXT": 0.5},
        "positive_label": 1,
        "probability_column": 1,
        "test_access": False,
        "classification_threshold": None,
    }
    if any(configuration.get(key) != value for key, value in required.items()):
        raise FinalRefitAuditError("unauthorized final-refit configuration")


def deterministic_development_folds(
    y: np.ndarray, folds: int = 5, seed: int = 108230
) -> np.ndarray:
    """Return deterministic stratified membership for procedural validation."""
    from sklearn.model_selection import StratifiedKFold

    membership = np.full(len(y), -1, dtype=int)
    splitter = StratifiedKFold(n_splits=folds, shuffle=True, random_state=seed)
    for fold, (fit, held_out) in enumerate(splitter.split(np.zeros(len(y)), y)):
        if np.intersect1d(fit, held_out).size:
            raise FinalRefitAuditError("an observation would train its own OOF scorer")
        membership[held_out] = fold
    if (membership < 0).any():
        raise FinalRefitAuditError("incomplete deterministic fold coverage")
    return membership


def run_audit(
    root: Path, inputs: DevelopmentInputs, configuration: dict[str, Any]
) -> dict[str, Any]:
    _validate(configuration)
    architecture, protocol = load_and_validate(root)
    calibration = _read(
        root, "audits/jit-defects4j-calibration-execution/1.0.0/audit.json"
    )
    baselines = _read(
        root, "audits/jit-defects4j-controlled-baselines/1.0.0/audit.json"
    )
    fusion = _read(
        root, "audits/jit-defects4j-controlled-multimodal-fusion/1.0.0/audit.json"
    )
    robustness = _read(root, "audits/jit-defects4j-robustness/1.0.0/audit.json")
    observed = {
        "dataset": architecture["dataset"]["identity"],
        "manifest": architecture["dataset"]["manifest_sha256"],
        "temporal_boundary": architecture["dataset"]["frozen_boundary_identity"],
        "adapter": architecture["dataset"]["adapter_identity"],
        "baselines": baselines["results_identity_digest"],
        "fusion": fusion["results_identity_digest"],
        "robustness": robustness["results_identity_digest"],
        "architecture": identity(architecture),
        "calibration_protocol": identity(protocol),
        "calibration_execution": calibration["result_digest"],
    }
    if observed != configuration["expected_identities"]:
        raise FinalRefitAuditError("frozen ancestry identity mismatch")
    if (
        calibration["selected_calibrator"] != "ISOTONIC"
        or not calibration["test_sealed"]
    ):
        raise FinalRefitAuditError("calibration selection or TEST seal mismatch")
    train_ids = {tuple(value) for value in inputs.train["identities"]}
    validation_ids = {tuple(value) for value in inputs.validation["identities"]}
    if train_ids & validation_ids:
        raise FinalRefitAuditError("TRAIN/VALIDATION contamination")
    raw = _raw_probabilities(root, inputs, architecture)
    y = np.asarray(inputs.validation["targets"], dtype=int)
    if len(raw) != 4086 or int(y.sum()) != 260:
        raise FinalRefitAuditError("calibration population mismatch")
    calibrator = IsotonicRegression(out_of_bounds="clip").fit(raw, y)
    calibration_state = {
        "implementation": "sklearn.isotonic.IsotonicRegression",
        "out_of_bounds": "clip",
        "fit_population": "full canonical VALIDATION (4086; 260 positive)",
        "score_generator": "unchanged frozen TRAIN-fitted CODE+TEXT base system",
        "x_thresholds": calibrator.X_thresholds_.tolist(),
        "y_thresholds": calibrator.y_thresholds_.tolist(),
    }
    final_contract = {
        "procedure": "A_NO_BASE_REFIT",
        "identities": observed,
        "base_training": "TRAIN only (19114)",
        "code": architecture["base_predictors"]["CODE"],
        "text": architecture["base_predictors"]["TEXT"],
        "fusion": architecture["fusion"],
        "calibration": calibration_state,
        "deterministic_observation_order": "canonical VALIDATION adapter order",
        "class_order": [0, 1],
        "positive_probability_column": 1,
        "application_order": [
            "CODE probability",
            "TEXT probability",
            "equal-weight fusion",
            "ISOTONIC",
        ],
        "future_test_metrics": configuration["future_test_metrics"],
        "test_opening_preconditions": [
            "this contract merged unchanged",
            "separate explicit one-shot TEST sprint",
            "identity and seal gates pass",
        ],
        "post_test_immutability": (
            "no model, representation, fusion, calibrator, metric, "
            "or threshold changes"
        ),
        "classification_threshold": "UNDEFINED",
    }
    payload = {
        "schema_version": configuration["schema_version"],
        "sprint": "10.8.2.30",
        "decision": "SPRINT_10.8.2.30_GO",
        "selected_procedure": "A_NO_BASE_REFIT",
        "test_sealed": True,
        "leakage_audit": "PASS",
        "calibrator_score_compatibility": (
            "PASS: calibration and future scores use the identical fitted base "
            "score generator"
        ),
        "rejected_procedures": {
            "B_DEVELOPMENT_CROSS_FIT_FINAL_REFIT": (
                "OOF fold models and the final full-development model are not the "
                "same fitted score generator; compatibility remains an unverified "
                "inference and the procedure changes the prior declaration"
            ),
            "SPRINT_10.8.2.29_DECLARED_HYBRID": (
                "calibrator scores come from TRAIN-fitted models but final scores "
                "would come from TRAIN+VALIDATION-refitted models"
            ),
        },
        "final_contract": final_contract,
        "final_contract_digest": identity(final_contract),
        "calibration_state_digest": identity(calibration_state),
        "threshold_policy": "FINAL_CLASSIFICATION_THRESHOLD = UNDEFINED",
        "next_sprint": "10.8.2.31 probability-only one-shot temporal TEST evaluation",
    }
    return {**payload, "result_digest": identity(payload)}


def load_inputs(root: Path) -> DevelopmentInputs:
    try:
        return load_development_inputs(root)
    except DevelopmentBoundaryError as error:
        raise FinalRefitAuditError(str(error)) from error
