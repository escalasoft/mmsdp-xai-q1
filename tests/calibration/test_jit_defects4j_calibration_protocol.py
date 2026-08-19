"""Focused integrity tests for Sprint 10.8.2.28."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from calibration.jit_defects4j_calibration_protocol import (
    CalibrationProtocolError,
    expected_calibration_error,
    identity,
    load_and_validate,
    select_method,
    validate_architecture,
    validate_protocol,
)

ROOT = Path(__file__).resolve().parents[2]


def test_architecture_freeze_integrity_and_identities() -> None:
    architecture, _ = load_and_validate(ROOT)
    assert architecture["primary_modalities"] == ["CODE", "TEXT"]
    assert architecture["fusion"]["weights"] == {"CODE": 0.5, "TEXT": 0.5}
    assert architecture["process_status"]["in_primary_predictor"] is False
    assert architecture["process_status"]["retained"] is True
    assert architecture["probability_semantics"] == {
        "target": "P(y=defect-prone|commit)",
        "positive_label": 1,
        "class_order": [0, 1],
        "source_column": 1,
    }


def test_architecture_mutations_fail_closed() -> None:
    architecture, _ = load_and_validate(ROOT)
    architecture["fusion"]["weights"]["CODE"] = 0.6
    with pytest.raises(CalibrationProtocolError):
        validate_architecture(architecture)


def test_calibrator_crossfit_ece_threshold_and_test_contracts() -> None:
    _, protocol = load_and_validate(ROOT)
    assert protocol["candidate_methods"] == ["UNCALIBRATED", "PLATT", "ISOTONIC"]
    assert protocol["cross_fitting"]["folds"] == 5
    assert protocol["cross_fitting"]["partition"] == "VALIDATION"
    assert protocol["metrics"]["ece"]["empty_bins"] == "omitted (zero contribution)"
    assert (
        protocol["threshold_separation"]["calibrator_selection_uses_threshold_metrics"]
        is False
    )
    assert protocol["test_seal"]["TEST_SEALED"] is True
    assert len(protocol["leakage_safeguards"]["forbidden_predictors"]) == 5


def test_protocol_mutations_fail_closed() -> None:
    _, protocol = load_and_validate(ROOT)
    protocol["candidate_methods"].append("BETA")
    with pytest.raises(CalibrationProtocolError):
        validate_protocol(protocol)


def test_exact_ece_equal_width_definition() -> None:
    y = np.array([0, 1, 1, 0])
    p = np.array([0.05, 0.15, 0.95, 1.0])
    assert expected_calibration_error(y, p) == pytest.approx(0.4625)


def test_deterministic_tie_breaking() -> None:
    metrics = {
        "UNCALIBRATED": {"brier": 0.2, "ece": 0.1},
        "PLATT": {"brier": 0.2 - 5e-13, "ece": 0.1},
        "ISOTONIC": {"brier": 0.21, "ece": 0.01},
    }
    assert select_method(metrics) == "UNCALIBRATED"
    metrics["PLATT"]["ece"] = 0.09
    assert select_method(metrics) == "PLATT"


def test_protocol_identity_is_deterministic() -> None:
    architecture, protocol = load_and_validate(ROOT)
    assert identity(architecture) == identity(json.loads(json.dumps(architecture)))
    assert identity(protocol) == identity(json.loads(json.dumps(protocol)))
