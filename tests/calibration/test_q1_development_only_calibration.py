# ruff: noqa: E501

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from calibration.q1_development_only_calibration import (
    CalibrationCampaignError,
    apply_calibrator,
    canonical_bytes,
    final_classification,
    fit_calibrator,
    holm_adjust,
    load_contract,
    metric_values,
    paired_rank_biserial_left_better,
    reliability_bins,
    validate_membership_causality,
    verify_ledger_identity,
)

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = load_contract(ROOT)


def test_contract_freezes_methods_scope_and_t1_t2_prohibition():
    assert CONTRACT["methods"] == ["RAW", "PLATT", "ISOTONIC"]
    assert CONTRACT["prohibited_partitions"] == ["T1", "T2"]
    assert CONTRACT["model_training"] is False
    assert CONTRACT["threshold_optimization"] is False
    assert CONTRACT["xai"] is False
    assert CONTRACT["temporal_protocol"]["common_comparison_origins"] == list(
        range(3, 12)
    )


def test_temporal_calibration_causality_accepts_strict_prior_order():
    validate_membership_causality(
        ["fit-a", "fit-b"], ["eval"], ("2020", "b"), ("2020", "c")
    )


def test_no_evaluation_block_self_fitting():
    with pytest.raises(CalibrationCampaignError, match="self-fitting"):
        validate_membership_causality(["same"], ["same"], ("2019", "a"), ("2020", "a"))


def test_no_future_fitting():
    with pytest.raises(CalibrationCampaignError, match="future"):
        validate_membership_causality(["fit"], ["eval"], ("2021", "a"), ("2020", "a"))


def test_raw_baseline_is_exact_copy():
    raw = np.asarray([0.1, 0.4, 0.8])
    observed = apply_calibrator("RAW", None, raw)
    assert np.array_equal(observed, raw)
    assert observed is not raw


def test_platt_behavior_is_bounded_and_monotonic():
    raw = np.linspace(0.01, 0.99, 100)
    y = (raw > 0.6).astype(int)
    model = fit_calibrator("PLATT", raw, y, CONTRACT)
    calibrated = apply_calibrator("PLATT", model, raw)
    assert np.all((calibrated >= 0) & (calibrated <= 1))
    assert np.all(np.diff(calibrated) >= 0)


def test_isotonic_behavior_is_bounded_and_monotonic():
    raw = np.linspace(0.01, 0.99, 100)
    y = np.asarray(([0, 1] * 50), dtype=int)
    model = fit_calibrator("ISOTONIC", raw, y, CONTRACT)
    calibrated = apply_calibrator("ISOTONIC", model, raw)
    assert np.all((calibrated >= 0) & (calibrated <= 1))
    assert np.all(np.diff(calibrated) >= 0)


def test_brier_and_ece_computation():
    y = np.asarray([0, 1])
    p = np.asarray([0.25, 0.75])
    metrics, _ = metric_values(y, p)
    assert metrics["Brier"] == pytest.approx(0.0625)
    assert metrics["ECE"] == pytest.approx(0.25)


def test_deterministic_binning_retains_empty_and_right_edge():
    y = np.asarray([0, 1, 1])
    p = np.asarray([0.0, 0.1, 1.0])
    first = reliability_bins(y, p)
    second = reliability_bins(y, p)
    assert first == second
    _, bins = first
    assert len(bins) == 10
    assert bins[0]["observation_count"] == 1
    assert bins[1]["observation_count"] == 1
    assert bins[9]["observation_count"] == 1
    assert bins[9]["upper_inclusive"] is True
    assert bins[2]["observation_count"] == 0


def test_calibration_fit_support_fails_closed():
    raw = np.linspace(0, 1, 20)
    y = np.asarray([0, 1] * 10)
    with pytest.raises(CalibrationCampaignError, match="support"):
        fit_calibrator("PLATT", raw, y, CONTRACT)


def test_holm_is_deterministic_and_monotonic_in_sorted_order():
    adjusted = holm_adjust([0.01, 0.04, 0.03])
    assert adjusted == pytest.approx([0.03, 0.06, 0.06])


def test_selection_classification_preserves_raw_and_allows_scope_specific_choice():
    assert (
        final_classification([{"selected_calibration_state": "RAW"}])
        == "PASS_51_RAW_CALIBRATION_RETAINED"
    )
    assert (
        final_classification(
            [
                {"selected_calibration_state": "RAW"},
                {"selected_calibration_state": "ISOTONIC"},
            ]
        )
        == "PASS_51_ALGORITHM_SPECIFIC_CALIBRATION_SELECTED"
    )


def test_rank_biserial_direction_is_left_better_positive():
    left = np.asarray([1.0, 1.0, 1.0])
    right = np.asarray([2.0, 2.0, 2.0])
    assert paired_rank_biserial_left_better(left, right) == 1.0


def test_deterministic_serialization():
    first = canonical_bytes({"b": 2, "a": 1})
    second = canonical_bytes({"a": 1, "b": 2})
    assert first == second


def test_fail_closed_missing_provenance(tmp_path):
    with pytest.raises(CalibrationCampaignError, match="missing"):
        verify_ledger_identity(tmp_path / "missing.gz", 1, "0" * 64)


def test_fail_closed_corrupted_large_artifact(tmp_path):
    artifact = tmp_path / "ledger.gz"
    artifact.write_bytes(b"corrupt")
    expected = hashlib.sha256(b"different").hexdigest()
    with pytest.raises(CalibrationCampaignError, match="hash"):
        verify_ledger_identity(artifact, len(b"corrupt"), expected)


def test_generated_access_audit_and_manifest_if_present():
    output = ROOT / "audits/q1-development-only-calibration/1.0.0"
    if not (output / "t1_t2_access_audit.json").exists():
        return
    access = json.loads((output / "t1_t2_access_audit.json").read_text())
    assert access and all(value == 0 for value in access.values())
    manifest = (output / "MANIFEST.sha256").read_bytes()
    assert canonical_bytes(
        json.loads((output / "verification_report.json").read_text())
    )
    assert len(manifest) > 0
