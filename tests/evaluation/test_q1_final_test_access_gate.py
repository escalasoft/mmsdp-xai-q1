from copy import deepcopy
from pathlib import Path

import pytest

from evaluation.q1_final_test_access_gate import (
    canonical_bytes,
    collect_evidence,
    decide,
    digest,
    evaluate,
)

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def valid_evidence():
    return collect_evidence(ROOT)


def changed(evidence, path, value):
    result = deepcopy(evidence)
    target = result
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    return result


def assert_blocked(evidence, reason):
    result = decide(evidence)
    assert result["gate_decision"] == "BLOCKED"
    assert result["one_shot_test_access_authorized"] is False
    assert result["test_sealed"] is True
    assert result["test_access_count"] == 0
    assert any(reason in row for row in result["blocking_reasons"])


def test_valid_complete_authorization(valid_evidence):
    result = decide(valid_evidence)
    assert result["gate_decision"] == "AUTHORIZED_ONE_SHOT_TEST_ACCESS"
    assert result["one_shot_test_access_authorized"] is True
    assert result["test_access_count"] == 0


def test_missing_sprint45_artifact_blocks(valid_evidence):
    assert_blocked(
        changed(valid_evidence, ("sprint45", "missing"), ["authorization.json"]),
        "missing Sprint 45",
    )


def test_sprint45_hash_mismatch_blocks(valid_evidence):
    assert_blocked(
        changed(valid_evidence, ("sprint45", "authorization_hash_valid"), False),
        "hash mismatch",
    )


def test_candidate_identity_mismatch_blocks(valid_evidence):
    assert_blocked(
        changed(valid_evidence, ("candidate", "id"), "CT_equal"), "candidate identity"
    )


def test_candidate_fitted_state_hash_mismatch_blocks(valid_evidence):
    assert_blocked(
        changed(valid_evidence, ("reference_integrity", "passed"), False),
        "fitted-state",
    )


def test_missing_mandatory_comparator_blocks(valid_evidence):
    evidence = deepcopy(valid_evidence)
    evidence["comparators"]["items"].pop()
    assert_blocked(evidence, "mandatory comparator")


def test_comparator_hash_mismatch_blocks(valid_evidence):
    assert_blocked(
        changed(valid_evidence, ("reference_integrity", "passed"), False),
        "reference hash",
    )


def test_threshold_not_point_five_blocks(valid_evidence):
    assert_blocked(
        changed(valid_evidence, ("threshold", "value"), 0.51), "threshold differs"
    )


@pytest.mark.parametrize(
    "field,reason",
    [
        ("selection_on_test_authorized", "threshold selection"),
        ("optimization_on_test_authorized", "threshold optimization"),
    ],
)
def test_threshold_test_operations_block(valid_evidence, field, reason):
    assert_blocked(changed(valid_evidence, ("threshold", field), True), reason)


def test_missing_calibration_state_blocks(valid_evidence):
    assert_blocked(
        changed(valid_evidence, ("calibration", "ids"), ["UNCALIBRATED", "PLATT"]),
        "missing calibration",
    )


def test_calibrator_fit_or_refit_on_test_blocks(valid_evidence):
    assert_blocked(
        changed(
            valid_evidence, ("calibration", "fit_or_refit_on_test_authorized"), True
        ),
        "fit/refit",
    )


@pytest.mark.parametrize(
    "counter",
    [
        "test_label_access",
        "model_fit",
        "threshold_optimization",
        "XAI",
        "rescue_experiment",
    ],
)
def test_any_nonzero_prohibited_counter_blocks(valid_evidence, counter):
    assert_blocked(changed(valid_evidence, ("ledger", counter), 1), "counter nonzero")


def test_test_already_accessed_blocks(valid_evidence):
    assert_blocked(
        changed(valid_evidence, ("seal", "test_access_count"), 1), "already accessed"
    )


def test_test_not_sealed_blocks(valid_evidence):
    assert_blocked(
        changed(valid_evidence, ("seal", "test_sealed"), False), "not sealed"
    )


def test_xai_authorization_blocks(valid_evidence):
    assert_blocked(
        changed(valid_evidence, ("prohibitions", "xai_authorized"), True), "XAI"
    )


def test_test_adaptation_authorization_blocks(valid_evidence):
    assert_blocked(
        changed(
            valid_evidence, ("prohibitions", "test_based_adaptation_authorized"), True
        ),
        "adaptation",
    )


def test_deterministic_replay_is_byte_identical(valid_evidence):
    assert canonical_bytes(decide(valid_evidence)) == canonical_bytes(
        decide(valid_evidence)
    )


def test_historical_accepted_files_unchanged():
    manifest = (
        ROOT
        / "audits/q1-human-prospective-final-evaluation-authorization/1.0.0"
        / "MANIFEST.sha256"
    )
    for line in manifest.read_text().splitlines():
        expected, relative = line.split("  ", 1)
        assert digest(ROOT / relative) == expected


def test_authorization_true_only_when_every_gate_passes(valid_evidence):
    assert evaluate(ROOT, valid_evidence)["one_shot_test_access_authorized"] is True
    invalid = changed(valid_evidence, ("sprint45", "manifest_valid"), False)
    assert evaluate(ROOT, invalid)["one_shot_test_access_authorized"] is False
