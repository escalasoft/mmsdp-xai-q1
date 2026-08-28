"""Fail-closed tests for the Sprint 10.8.2.48 prospective CPDP contract."""

import json
from pathlib import Path

from experimentation.q1_cpdp_campaign_contract import (
    ALGORITHMS,
    CALIBRATIONS,
    MODALITIES,
    PROJECTS,
    generate,
    validate,
)


def test_generated_contract_is_complete_deterministic_and_sealed(
    tmp_path: Path,
) -> None:
    out = generate(tmp_path)
    first = {path.name: path.read_bytes() for path in out.iterdir()}
    assert validate(out) == []
    generate(tmp_path)
    assert first == {path.name: path.read_bytes() for path in out.iterdir()}

    contract = json.loads((out / "campaign_contract.json").read_text())
    policy = json.loads((out / "target_access_policy.json").read_text())
    assert contract["classification"] == "BLOCKED_MISSING_COMPATIBLE_DATASETS"
    assert contract["execution_authorized"] is False
    assert contract["target_accesses"] == policy["access_counter"] == 0
    assert contract["modalities"] == list(MODALITIES)


def test_matrix_is_complete_unique_and_never_executable(tmp_path: Path) -> None:
    matrix = json.loads((generate(tmp_path) / "experimental_matrix.json").read_text())
    expected = len(PROJECTS) * len(ALGORITHMS) * len(MODALITIES) * len(CALIBRATIONS)
    assert matrix["total_configurations"] == expected == 1764
    experiments = matrix["experiments"]
    assert len({item["experiment_id"] for item in experiments}) == expected
    assert all(
        item["execution_status"] == "BLOCKED_PENDING_TARGET_MATERIALIZATION"
        for item in experiments
    )
    assert all("test" not in item["dataset_source"].lower() for item in experiments)


def test_validator_rejects_target_access_or_authorization(tmp_path: Path) -> None:
    out = generate(tmp_path)
    contract_path = out / "campaign_contract.json"
    contract = json.loads(contract_path.read_text())
    contract["target_accesses"] = 1
    contract["execution_authorized"] = True
    contract_path.write_text(json.dumps(contract))
    errors = validate(out)
    assert "campaign must remain unauthorized with zero target accesses" in errors
    assert "manifest mismatch: campaign_contract.json" in errors
