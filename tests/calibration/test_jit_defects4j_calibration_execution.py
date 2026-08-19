"""Focused tests for Sprint 10.8.2.29 calibration execution."""

# ruff: noqa: E501

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from calibration.jit_defects4j_calibration_execution import (
    _calibrate_oof,
    _validate_execution,
    load_configuration,
    reliability_bins,
)
from calibration.jit_defects4j_calibration_protocol import (
    CalibrationProtocolError,
    load_and_validate,
)

ROOT = Path(__file__).resolve().parents[2]


def test_execution_configuration_is_frozen_and_test_sealed() -> None:
    configuration = load_configuration(ROOT)
    _validate_execution(configuration)
    assert configuration["test_access"] is False
    assert configuration["threshold_optimization"] is False
    assert configuration["final_refit_execution"] is False


def test_execution_configuration_mutation_fails_closed() -> None:
    configuration = load_configuration(ROOT)
    configuration["candidates"].append("BETA")
    with pytest.raises(CalibrationProtocolError):
        _validate_execution(configuration)


def test_fixed_reliability_bins_include_one_in_final_bin() -> None:
    rows = reliability_bins(np.array([0, 1, 1]), np.array([0.0, 0.1, 1.0]))
    assert [row["bin_index"] for row in rows] == [0, 1, 9]
    assert rows[-1]["upper_bound_inclusive"] is True


def test_oof_protocol_is_deterministic_and_complete() -> None:
    _, protocol = load_and_validate(ROOT)
    y = np.tile(np.array([0, 0, 0, 1]), 20)
    raw = np.linspace(0.01, 0.99, len(y))
    for method in ("PLATT", "ISOTONIC"):
        first, folds = _calibrate_oof(y, raw, method, protocol)
        second, _ = _calibrate_oof(y, raw, method, protocol)
        assert np.array_equal(first, second)
        assert np.isfinite(first).all()
        assert len(folds) == 5
        assert all(row["fit_held_out_overlap"] == 0 for row in folds)


def test_authoritative_upstream_identity_values() -> None:
    configuration = load_configuration(ROOT)
    audit = json.loads(
        (ROOT / "audits/jit-defects4j-calibration-protocol/1.0.0/audit.json").read_text()
    )
    assert configuration["architecture_identity"] == audit["frozen_architecture_identity"]
    assert configuration["protocol_identity"] == audit["calibration_protocol_identity"]
