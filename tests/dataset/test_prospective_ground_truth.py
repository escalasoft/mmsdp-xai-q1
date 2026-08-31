"""Focused tests for prospective ground-truth contracts."""

from __future__ import annotations

import pytest

from dataset.prospective_ground_truth import (
    AttributionEvidence,
    EvidenceState,
    GroundTruthContractError,
    VerificationMaturityRule,
    decide_ground_truth,
    validate_project_gates,
)


def _attribution(**changes: object) -> AttributionEvidence:
    values: dict[str, object] = {
        "defect_evidence_id": "ISSUE-1",
        "defect_evidence_location": "https://example.test/ISSUE-1",
        "fixing_sha": "f" * 40,
        "parent_sha": "p" * 40,
        "file_path": "src/Main.java",
        "repair_or_deleted_line": "return correct;",
        "line_history_evidence": "git blame --line-porcelain -M -w",
        "blamed_sha": "b" * 40,
        "filters_applied": ("exclude-whitespace", "exclude-tests"),
        "attribution_result": "ACCEPTED",
        "decision_reason": "validated repair line has one prior origin",
        "evidence_timestamp": "2026-01-01T00:00:00Z",
        "evidence_hash": "evidence-hash",
    }
    values.update(changes)
    return AttributionEvidence(**values)  # type: ignore[arg-type]


def _rule(**changes: object) -> VerificationMaturityRule:
    values: dict[str, object] = {
        "rule_id": "rule-1",
        "window_seconds": 100,
        "evidence_basis": "validated project rule",
        "evidence_location": "https://example.test/rule",
        "project_aware": True,
    }
    values.update(changes)
    return VerificationMaturityRule(**values)  # type: ignore[arg-type]


def _decision(**changes: object):
    values: dict[str, object] = {
        "commit_sha": "b" * 40,
        "commit_epoch": 200,
        "boundary_sha": "a" * 40,
        "boundary_epoch": 100,
        "identity_resolved": True,
        "provenance_resolved": True,
    }
    values.update(changes)
    return decide_ground_truth(**values)  # type: ignore[arg-type]


def test_temporal_enforcement() -> None:
    with pytest.raises(GroundTruthContractError, match="strictly post-boundary"):
        _decision(commit_epoch=100, commit_sha="a" * 40)


def test_provenance_completeness_fails_closed() -> None:
    decision = _decision(provenance_resolved=False, attributions=(_attribution(),))
    assert (decision.state, decision.label) == (
        EvidenceState.PROVENANCE_UNRESOLVED,
        None,
    )


def test_fixing_and_inducing_commits_are_separate() -> None:
    evidence = _attribution(blamed_sha="f" * 40)
    assert "fixing commit must not be treated as inducing commit" in evidence.validate()
    decision = _decision(commit_sha="f" * 40, attributions=(evidence,))
    assert (decision.state, decision.label) == (EvidenceState.AMBIGUOUS, None)


def test_complete_positive_construction() -> None:
    decision = _decision(attributions=(_attribution(),))
    assert (decision.state, decision.label) == (EvidenceState.SUPPORTED_POSITIVE, 1)
    assert decision.accepted_attribution_hashes == ("evidence-hash",)


def test_negative_requires_defensible_maturity() -> None:
    decision = _decision(
        negative_verification_complete=True, tracker_coverage_complete=True
    )
    assert (decision.state, decision.label) == (
        EvidenceState.PROVENANCE_UNRESOLVED,
        None,
    )


def test_mature_affirmative_negative() -> None:
    decision = _decision(
        negative_verification_complete=True,
        tracker_coverage_complete=True,
        maturity_rule=_rule(),
        evidence_cutoff_epoch=301,
    )
    assert (decision.state, decision.label) == (EvidenceState.SUPPORTED_NEGATIVE, 0)


def test_right_censoring_is_not_negative() -> None:
    decision = _decision(
        negative_verification_complete=True,
        tracker_coverage_complete=True,
        maturity_rule=_rule(),
        evidence_cutoff_epoch=250,
    )
    assert (decision.state, decision.label) == (EvidenceState.RIGHT_CENSORED, None)


def test_unresolved_without_affirmative_evidence() -> None:
    decision = _decision()
    assert (decision.state, decision.label) == (
        EvidenceState.PROVENANCE_UNRESOLVED,
        None,
    )


def test_ambiguous_attribution_has_no_label() -> None:
    decision = _decision(attributions=(_attribution(attribution_result="AMBIGUOUS"),))
    assert (decision.state, decision.label) == (EvidenceState.AMBIGUOUS, None)


def test_all_eligibility_gates_are_required() -> None:
    gates = {f"G{number}": True for number in range(1, 16)}
    assert validate_project_gates(gates) == (True, [])
    gates["G9"] = False
    assert validate_project_gates(gates) == (False, ["FAIL_G9"])
