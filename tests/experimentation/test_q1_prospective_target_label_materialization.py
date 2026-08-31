# ruff: noqa: E501
"""Scientific contract tests for Sprint 48C."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from experimentation.q1_prospective_target_label_materialization import (
    ContractError,
    EvidenceState,
    canonical_bytes,
    decide_label,
    digest,
    generate,
    project_is_eligible,
    select_four_targets,
    validate,
    validate_frozen_48c_snapshot,
)

# GENERAL CONTRACT TESTS


def _eligible(name: str) -> dict[str, object]:
    return {"project": name, "eligibility": "ELIGIBLE"}


def _gate(**changes: object) -> dict[str, object]:
    value: dict[str, object] = {
        "G1_identity": True,
        "G2_post_boundary": True,
        "G3_no_overlap": True,
        "G4_label_construct": True,
        "supported_positive": 1,
        "supported_negative": 1,
        "G7_negative_affirmative": True,
        "G8_maturity": True,
        "G9_provenance": True,
        "G10_code": True,
        "G11_process": True,
        "G12_text": True,
        "G13_schema": True,
        "G14_lopo_holdout": True,
        "G15_no_predictive_selection": True,
    }
    value.update(changes)
    return value


def test_supported_positive_label() -> None:
    result = decide_label(commit_epoch=11, boundary_epoch=10, provenance_resolved=True, positive_chain_complete=True)
    assert (result.state, result.label) == (EvidenceState.POSITIVE_SUPPORTED, 1)


def test_supported_negative_label() -> None:
    result = decide_label(commit_epoch=11, boundary_epoch=10, provenance_resolved=True, negative_verification_complete=True, maturity_window_seconds=5, evidence_cutoff_epoch=20)
    assert (result.state, result.label) == (EvidenceState.NEGATIVE_SUPPORTED, 0)


def test_unresolved_fails_closed() -> None:
    result = decide_label(commit_epoch=11, boundary_epoch=10, provenance_resolved=True)
    assert (result.state, result.label) == (EvidenceState.UNRESOLVED, None)


def test_right_censored_cannot_become_negative() -> None:
    result = decide_label(commit_epoch=18, boundary_epoch=10, provenance_resolved=True, negative_verification_complete=True, maturity_window_seconds=5, evidence_cutoff_epoch=20)
    assert (result.state, result.label) == (EvidenceState.RIGHT_CENSORED, None)


def test_temporal_boundary_enforced() -> None:
    with pytest.raises(ContractError, match="strictly post-boundary"):
        decide_label(commit_epoch=10, boundary_epoch=10)


def test_provenance_required() -> None:
    result = decide_label(commit_epoch=11, boundary_epoch=10, positive_chain_complete=True)
    assert (result.state, result.label) == (EvidenceState.PROVENANCE_UNRESOLVED, None)


def test_overlap_rejected() -> None:
    eligible, reasons = project_is_eligible(_gate(G3_no_overlap=False))
    assert eligible is False
    assert "FAIL_G3_NO_OVERLAP" in reasons


def test_two_class_project_eligible() -> None:
    assert project_is_eligible(_gate()) == (True, [])


def test_single_class_project_rejected() -> None:
    eligible, reasons = project_is_eligible(_gate(supported_positive=0))
    assert eligible is False
    assert "FAIL_G5_NO_SUPPORTED_POSITIVE" in reasons


def test_modality_incompatibility_rejected() -> None:
    eligible, reasons = project_is_eligible(_gate(G12_text=False))
    assert eligible is False
    assert "FAIL_G12_TEXT" in reasons


def test_four_target_selection_is_deterministic() -> None:
    projects = [_eligible(name) for name in ("z", "c", "a", "b", "d")]
    assert select_four_targets(projects) == ["a", "b", "c", "d"]
    assert select_four_targets(list(reversed(projects))) == ["a", "b", "c", "d"]


def test_predictive_metrics_cannot_influence_selection() -> None:
    projects = [_eligible(name) for name in ("a", "b", "c", "d")]
    projects[0]["roc_auc"] = 0.9
    with pytest.raises(ContractError, match="predictive metrics"):
        select_four_targets(projects)


def test_fewer_than_four_blocks() -> None:
    with pytest.raises(ContractError, match="fewer than four"):
        select_four_targets([_eligible("a"), _eligible("b"), _eligible("c")])


def _refresh_manifest(output: Path) -> None:
    names = sorted(path.name for path in output.iterdir() if path.name != "MANIFEST.sha256")
    manifest = "".join(
        f"{hashlib.sha256((output / name).read_bytes()).hexdigest()}  {name}\n"
        for name in names
    )
    (output / "MANIFEST.sha256").write_text(manifest)


def test_general_validation_accepts_supported_labels_and_an_eligible_project(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    output = generate(root, tmp_path)
    manifest_path = output / "prospective_label_manifest.jsonl"
    rows = [json.loads(line) for line in manifest_path.read_text().splitlines()]
    project_name = rows[0]["project"]
    project_rows = [row for row in rows if row["project"] == project_name]
    positive, negative = project_rows[:2]

    positive.update(
        {
            "assigned_label": 1,
            "evidence_state": EvidenceState.POSITIVE_SUPPORTED,
            "provenance_resolved": True,
            "positive_chain_complete": True,
            "source_issue_or_bug_ids": ["HYPOTHETICAL-POSITIVE"],
            "fixing_commit": "hypothetical-fixing-commit",
            "repair_line_evidence": ["hypothetical-reviewed-repair-line"],
            "bug_inducing_commit": positive["commit_sha"],
            "provenance_chain": "COMPLETE_HYPOTHETICAL_TEST_FIXTURE",
        }
    )
    negative.update(
        {
            "assigned_label": 0,
            "evidence_state": EvidenceState.NEGATIVE_SUPPORTED,
            "provenance_resolved": True,
            "negative_verification_complete": True,
            "maturity_window_seconds": 1,
            "evidence_cutoff_epoch": int(negative["commit_epoch"]) + 1,
            "provenance_chain": "AFFIRMATIVE_NEGATIVE_HYPOTHETICAL_TEST_FIXTURE",
        }
    )
    for row in (positive, negative):
        row["evidence_hash"] = digest(
            {key: value for key, value in row.items() if key != "evidence_hash"}
        )
    manifest_path.write_bytes(b"".join(canonical_bytes(row) for row in rows))

    summary_path = output / "prospective_label_summary.json"
    summary = json.loads(summary_path.read_text())
    summary.update(
        {
            "supported_positive": 1,
            "supported_negative": 1,
            "unresolved": summary["unresolved"] - 2,
            "provenance_unresolved": summary["provenance_unresolved"] - 2,
            "assigned_label_count": 2,
        }
    )
    summary_path.write_bytes(canonical_bytes(summary))

    eligibility_path = output / "project_target_eligibility.json"
    eligibility = json.loads(eligibility_path.read_text())
    project = next(row for row in eligibility["projects"] if row["project"] == project_name)
    project["gates"].update(
        {
            "supported_positive": 1,
            "supported_negative": 1,
            "G7_negative_affirmative": True,
            "G8_maturity": True,
            "G9_provenance": True,
        }
    )
    project.update(
        {
            "supported_positive": 1,
            "supported_negative": 1,
            "unresolved": project["unresolved"] - 2,
            "eligibility": "ELIGIBLE",
            "reason_codes": [],
            "provenance_status": "RESOLVED_HYPOTHETICAL_TEST_FIXTURE",
        }
    )
    eligibility["eligible_count"] = 1
    eligibility_path.write_bytes(canonical_bytes(eligibility))

    freeze_path = output / "four_target_freeze.json"
    freeze = json.loads(freeze_path.read_text())
    freeze["eligible_count"] = 1
    freeze_path.write_bytes(canonical_bytes(freeze))
    _refresh_manifest(output)

    assert validate(output) == []
    snapshot_errors = validate_frozen_48c_snapshot(output)
    assert "frozen 48C snapshot must contain 58,272 identities and 0 assigned labels" in snapshot_errors
    assert "frozen 48C snapshot must contain 21 projects and 0 eligible projects" in snapshot_errors


def test_manifest_tampering_is_detected(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    output = generate(root, tmp_path)
    path = output / "target_access_policy.json"
    policy = json.loads(path.read_text())
    policy["access_counter"] = 1
    path.write_text(json.dumps(policy))
    errors = validate(output)
    assert "TARGET access policy must remain unauthorized and unused" in errors
    assert "manifest mismatch: target_access_policy.json" in errors


# FROZEN 48C SNAPSHOT REGRESSION TESTS


def test_generated_snapshot_preserves_zero_access_and_hashes(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    output = generate(root, tmp_path)
    assert validate(output) == []
    assert validate_frozen_48c_snapshot(output) == []
    policy = json.loads((output / "target_access_policy.json").read_text())
    summary = json.loads((output / "prospective_label_summary.json").read_text())
    eligibility = json.loads((output / "project_target_eligibility.json").read_text())
    assert policy["access_counter"] == 0
    assert policy["predictive_scoring_count"] == 0
    assert summary["total"] == 58_272
    assert summary["assigned_label_count"] == 0
    assert eligibility["project_count"] == 21
    assert eligibility["eligible_count"] == 0
