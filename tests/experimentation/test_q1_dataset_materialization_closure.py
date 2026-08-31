"""Evidence-first tests for the Sprint 48B audit generator."""

import json
from pathlib import Path

from experimentation.q1_dataset_materialization_closure import generate, validate


def test_materialization_audit_is_complete_blocked_and_sealed(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    output = generate(root, tmp_path)
    assert validate(output) == []

    report = json.loads((output / "dataset_materialization_report.json").read_text())
    eligibility = json.loads((output / "project_eligibility.json").read_text())
    policy = json.loads((output / "target_access_policy.json").read_text())
    campaign = json.loads((output / "campaign_execution_manifest.json").read_text())

    assert report["projects"] == 21
    assert report["post_boundary_identity_candidates_materialized"] > 0
    assert report["final_target_partitions_materialized"] == 0
    assert report["qtbase"]["positive"] == 0
    assert eligibility["scientifically_eligible_targets"] == []
    assert policy["execution_authorized"] is False
    assert policy["access_counter"] == 0
    assert campaign["configuration_count"] == 720


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
