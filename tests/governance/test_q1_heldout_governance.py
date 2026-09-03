# ruff: noqa: E501

import json
from pathlib import Path

import pytest

from governance.q1_heldout_governance import (
    ALGORITHMS,
    CONFIGURATIONS,
    GovernanceFreezeError,
    build,
    canonical_bytes,
    execution_ledger,
    manifest_entries,
    verify_output,
    write_package,
)

ROOT = Path(__file__).resolve().parents[2]


def test_build_freezes_complete_universe_and_policies():
    artifacts = build(ROOT)
    assert artifacts["frozen_model_universe.json"]["algorithms"] == list(ALGORITHMS)
    assert len(CONFIGURATIONS) == 7
    calibration = artifacts["frozen_calibration_policy.json"]
    assert calibration["selection_counts"] == {"RAW": 27, "PLATT": 0, "ISOTONIC": 1}
    selected = [row for row in calibration["mapping"] if row["calibration_state"] != "RAW"]
    assert [(row["algorithm"], row["configuration"]) for row in selected] == [("LightGBM", "PROCESS")]
    assert artifacts["frozen_threshold_policy.json"]["threshold"] == 0.5


def test_feature_contract_is_exact_and_denylist_is_explicit():
    feature = build(ROOT)["frozen_feature_contract.json"]
    assert feature["allowed_feature_schema"]["CODE"] == ["la", "ld", "nf", "nd", "ns", "ent"]
    assert feature["allowed_feature_schema"]["PROCESS"] == ["ndev", "age", "nuc", "aexp", "arexp", "asexp"]
    assert feature["allowed_feature_schema"]["TEXT"] == ["raw_commit_message"]
    assert "SZZ metadata or outputs" in feature["prohibited_feature_classes"]
    assert "engineered bug/fix/issue keyword indicators" in feature["prohibited_feature_classes"]


def test_t1_t2_roles_gates_and_all_counters_are_fail_closed():
    artifacts = build(ROOT)
    assert artifacts["t1_access_contract.json"]["T1_ROLE"] == "CONFIRMATORY_HELD_OUT_TEST"
    reserve = artifacts["t2_reviewer_reserve_contract.json"]
    assert reserve["T2_ROLE"] == "SEALED_REVIEWER_RESERVE"
    assert reserve["automatic_access_after_t1"] is False
    assert len(artifacts["heldout_access_gate.json"]["gate_rows"]) == 18
    assert artifacts["heldout_access_gate.json"]["t1_predictive_execution_authorized"] is False
    ledger = execution_ledger()
    assert ledger["all_required_counters_zero"] is True
    assert all(value == 0 for key, value in ledger.items() if key.endswith("_count"))


def test_identity_audit_is_structural_and_label_free():
    artifacts = build(ROOT)
    for partition in ("t1", "t2"):
        item = artifacts[f"{partition}_identity_integrity.json"]
        assert item["manifest_contains_labels_or_predictions"] is False
        assert item["verification_scope"] == "STRUCTURAL_NON_PREDICTIVE_ONLY"
        assert item["predictive_access_count"] == 0
        assert len(item["identity_sha256"]) == 64


def test_deterministic_regeneration_and_manifest(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    first_digest = write_package(ROOT, first)
    second_digest = write_package(ROOT, second)
    assert first_digest == second_digest
    assert {p.name: p.read_bytes() for p in first.iterdir()} == {
        p.name: p.read_bytes() for p in second.iterdir()
    }
    assert verify_output(first)["status"] == "PASS"


def test_manifest_verification_fails_closed_on_tampering(tmp_path):
    output = tmp_path / "output"
    write_package(ROOT, output)
    (output / "execution_ledger.json").write_text("{}\n", encoding="utf-8")
    with pytest.raises(GovernanceFreezeError, match="manifest mismatch"):
        verify_output(output)


def test_canonical_serialization_and_machine_readability(tmp_path):
    assert canonical_bytes({"b": 2, "a": 1}) == b'{"a":1,"b":2}\n'
    output = tmp_path / "output"
    write_package(ROOT, output)
    for name in manifest_entries(output / "MANIFEST.sha256"):
        if name.endswith(".json"):
            json.loads((output / name).read_text(encoding="utf-8"))
