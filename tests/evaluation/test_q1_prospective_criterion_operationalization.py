# ruff: noqa: E501

import copy
import json
import subprocess
from pathlib import Path

import pytest

from evaluation.q1_advancement_governance_protocol import (
    CRITERIA,
    INTEGRITY,
    STATES,
)
from evaluation.q1_advancement_governance_protocol import (
    OUTPUT_REL as SPRINT39_OUTPUT,
)
from evaluation.q1_advancement_governance_protocol import (
    contract as sprint39_contract,
)
from evaluation.q1_prospective_criterion_operationalization import (
    EFFECTIVE_FROM_SPRINT,
    OUTPUT_REL,
    PROHIBITED_COUNTERS,
    assert_prospective_target,
    canonical_bytes,
    complexity_state,
    contract,
    derive_criterion_state,
    derive_integrity_state,
    historical_hashes,
    materialize,
    oriented_dominance_state,
    stability_state,
    validate_contract,
    verify_historical_hashes,
)

ROOT = Path(__file__).resolve().parents[2]


def assert_schema(schema, instance, valid=True):
    script = """
const Ajv = require('ajv');
const input = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const ajv = new Ajv({allErrors: true, schemaId: 'auto'});
const validate = ajv.compile(input.schema);
const valid = validate(input.instance);
process.stdout.write(JSON.stringify({valid, errors: validate.errors}));
"""
    completed = subprocess.run(
        ["node", "-e", script],
        input=json.dumps({"schema": schema, "instance": instance}),
        text=True,
        capture_output=True,
        check=True,
    )
    result = json.loads(completed.stdout)
    assert result["valid"] is valid, result["errors"]


@pytest.fixture(scope="module", autouse=True)
def artifacts():
    materialize(ROOT)


def test_all_sprint39_criteria_covered_once_with_exact_classes_and_states():
    value = contract()
    validate_contract(value)
    rows = value["criteria"]
    assert [row["id"] for row in rows] == list(CRITERIA)
    assert len({row["id"] for row in rows}) == len(CRITERIA)
    parent_classes = {row["id"]: row["class"] for row in sprint39_contract()["criteria"]}
    assert {row["id"]: row["class"] for row in rows} == parent_classes
    assert value["canonical_state_vocabulary"] == list(STATES)


def test_each_criterion_has_complete_deterministic_operationalization():
    for row in contract()["criteria"]:
        assert row["required_evidence"]
        assert row["provenance_requirements"]
        assert row["comparator_reference"]
        assert row["decision_condition"].keys() == set(STATES)
        assert row["missing_evidence_handling"] == "UNRESOLVED"
        assert row["invalid_evidence_handling"]
        assert row["rationale"]
        assert row["anti_retrospective_tuning"]


def test_every_performance_criterion_has_predeclared_reference():
    rows = {row["id"]: row for row in contract()["criteria"]}
    for criterion in set(CRITERIA) - set(INTEGRITY):
        reference = rows[criterion]["comparator_reference"]
        assert reference["type"]
        assert reference["definition"]
        assert "before" in reference["freeze_timing"]


def test_numerical_values_are_inherited_grids_not_fitted_cutoffs():
    value = contract()
    utility = next(row for row in value["criteria"] if row["id"] == "practical_utility")
    frozen = json.loads(
        (ROOT / "audits/q1-development-practical-utility-protocol/1.0.0/protocol.json").read_text()
    )
    assert utility["grid_requirements"]["thresholds"] == frozen["threshold_policy"]["grid"]
    assert utility["grid_requirements"]["FN_FP_ratios"] == frozen["cost_model"]["FN_FP_ratios"]
    assert "No threshold" in value["anti_retrospective_tuning_declaration"]


def test_integrity_rule_pass_mixed_fail_and_unresolved():
    row = contract()["criteria"][0]
    names = row["required_evidence"]["mandatory_invariants"]
    base = {"valid": True, "provenance_complete": True, "invariants": dict.fromkeys(names, True), "limitations": []}
    assert derive_integrity_state(base, names) == "PASS"
    mixed = copy.deepcopy(base)
    mixed["limitations"] = ["complete non-mandatory limitation"]
    assert derive_integrity_state(mixed, names) == "MIXED"
    failed = copy.deepcopy(base)
    failed["invariants"][names[0]] = False
    assert derive_integrity_state(failed, names) == "FAIL"
    missing = copy.deepcopy(base)
    missing["invariants"].pop(names[0])
    assert derive_integrity_state(missing, names) == "UNRESOLVED"
    assert derive_integrity_state({"valid": False}, names) == "UNRESOLVED"


@pytest.mark.parametrize(
    ("differences", "state"),
    [([0.0, 0.1], "PASS"), ([0.0, -0.1], "FAIL"), ([0.1, -0.1], "MIXED"), ([0.0, 0.0], "MIXED")],
)
def test_relational_dominance_is_deterministic(differences, state):
    evidence = {"valid": True, "complete": True, "provenance_complete": True, "oriented_differences": differences}
    assert oriented_dominance_state(evidence) == state
    assert oriented_dominance_state(evidence) == state


def test_relational_rule_rejects_missing_invalid_and_nonfinite_evidence():
    assert oriented_dominance_state({}) == "UNRESOLVED"
    base = {"valid": True, "complete": True, "provenance_complete": True, "oriented_differences": [0.1]}
    for value in (float("nan"), float("inf"), "0.1", True):
        malformed = copy.deepcopy(base)
        malformed["oriented_differences"] = [value]
        assert oriented_dominance_state(malformed) == "UNRESOLVED"


def complexity_evidence(candidate, reference, states=None):
    return {
        "valid": True,
        "provenance_complete": True,
        "candidate": candidate,
        "references": [reference],
        "incremental_value_states": states or {"discrimination": "PASS", "calibration": "PASS", "practical_utility": "PASS"},
    }


def test_complexity_parsimony_uses_pareto_order_and_incremental_value():
    simple = {"modality_count": 1, "fitted_component_count": 1, "learned_fusion_component_count": 0, "calibration_component_count": 0}
    complex_ = {"modality_count": 3, "fitted_component_count": 4, "learned_fusion_component_count": 1, "calibration_component_count": 1}
    assert complexity_state(complexity_evidence(simple, complex_)) == "PASS"
    assert complexity_state(complexity_evidence(complex_, simple)) == "PASS"
    assert complexity_state(complexity_evidence(complex_, simple, {"discrimination": "MIXED", "calibration": "PASS", "practical_utility": "PASS"})) == "MIXED"
    assert complexity_state(complexity_evidence(complex_, simple, {"discrimination": "FAIL", "calibration": "PASS", "practical_utility": "PASS"})) == "FAIL"
    assert complexity_state(complexity_evidence(complex_, simple, {"discrimination": "UNRESOLVED", "calibration": "PASS", "practical_utility": "PASS"})) == "UNRESOLVED"


def test_complexity_policy_is_prospective_new_and_keeps_stability_independent():
    row = next(
        item for item in contract()["criteria"] if item["id"] == "complexity_parsimony"
    )
    evidence = row["required_evidence"]
    assert "later explicitly authorized evaluation" in evidence["future_state_timing"]
    assert "new prospective" in evidence["prospective_policy_status"]
    assert "not an exact rule historically frozen by Sprint 37" in evidence["prospective_policy_status"]
    assert "stability_across_origins remains an independent required" in evidence["stability_separation"]
    assert "does not make stability optional" in evidence["stability_separation"]
    assert "already-derived Sprint 41" not in json.dumps(contract())


def test_stability_requires_exact_five_origin_coverage():
    def cell(values):
        return {"valid": True, "complete": True, "provenance_complete": True, "oriented_differences": values}

    favorable = {f"O{i}": cell([0.1, 0.0]) for i in range(1, 6)}
    evidence = {"valid": True, "provenance_complete": True, "origins": favorable}
    assert stability_state(evidence) == "PASS"
    evidence["origins"]["O5"] = cell([-0.1])
    assert stability_state(evidence) == "MIXED"
    evidence["origins"] = {f"O{i}": cell([-0.1]) for i in range(1, 6)}
    assert stability_state(evidence) == "FAIL"
    evidence["origins"].pop("O5")
    assert stability_state(evidence) == "UNRESOLVED"


def test_derivation_rejects_unknown_criterion_and_retrospective_targets():
    with pytest.raises(ValueError, match="retrospective"):
        assert_prospective_target("10.8.2.41")
    with pytest.raises(ValueError, match="unknown criterion"):
        derive_criterion_state(EFFECTIVE_FROM_SPRINT, "unknown", {})
    record = derive_criterion_state(EFFECTIVE_FROM_SPRINT, "discrimination", {})
    assert record["state"] == "UNRESOLVED"
    assert record["state"] in STATES


def test_malformed_contracts_rejected_semantically():
    for mutation in (
        lambda value: value["criteria"].pop(),
        lambda value: value["criteria"].append(copy.deepcopy(value["criteria"][0])),
        lambda value: value["criteria"][0].__setitem__("id", "unknown"),
        lambda value: value.__setitem__("effective_sprint", "10.8.2.40"),
        lambda value: value.__setitem__("prospective_only", False),
        lambda value: value.__setitem__("canonical_state_vocabulary", ["PASS"]),
    ):
        malformed = copy.deepcopy(contract())
        mutation(malformed)
        with pytest.raises(ValueError):
            validate_contract(malformed)


def test_real_json_schema_accepts_contract_and_rejects_malformed_instances():
    output = ROOT / OUTPUT_REL
    schema = json.loads((output / "criterion_operationalization.schema.json").read_text())
    value = json.loads((output / "criterion_operationalization.json").read_text())
    assert_schema(schema, value)
    malformed = copy.deepcopy(value)
    malformed["criteria"][0].pop("required_evidence")
    assert_schema(schema, malformed, valid=False)
    malformed = copy.deepcopy(value)
    malformed["test_access_prohibited"] = False
    assert_schema(schema, malformed, valid=False)


def test_real_evidence_schema_rejects_unknown_criterion_and_bad_hash():
    schema = json.loads((ROOT / OUTPUT_REL / "evidence_contract.schema.json").read_text())
    value = {"protocol_id": "q1-prospective-criterion-operationalization", "protocol_version": "1.0.0", "target_sprint": "10.8.2.42", "criterion": "discrimination", "evidence": {}, "artifact_sha256": "a" * 64}
    assert_schema(schema, value)
    malformed = copy.deepcopy(value)
    malformed["criterion"] = "unknown"
    assert_schema(schema, malformed, valid=False)
    malformed = copy.deepcopy(value)
    malformed["artifact_sha256"] = "bad"
    assert_schema(schema, malformed, valid=False)


def test_sprint39_contract_mapping_and_artifacts_remain_unchanged():
    persisted = json.loads((ROOT / SPRINT39_OUTPUT / "governance_contract.json").read_text())
    assert persisted == sprint39_contract()
    assert persisted["criterion_states"] == sprint39_contract()["criterion_states"]
    assert persisted["precedence_rules"] == sprint39_contract()["precedence_rules"]


def test_historical_artifacts_unchanged_and_manifest_is_exact():
    expected = json.loads((ROOT / OUTPUT_REL / "historical_artifact_hashes.json").read_text())
    verify_historical_hashes(ROOT, expected)
    assert expected == historical_hashes(ROOT)
    assert any(path.startswith("audits/q1-advancement-governance-outcome-mapping") for path in expected)


def test_test_and_prohibited_operation_counters_are_zero():
    ledger = json.loads((ROOT / OUTPUT_REL / "execution_ledger.json").read_text())
    assert set(PROHIBITED_COUNTERS) <= set(ledger)
    assert all(ledger[key] == 0 for key in PROHIBITED_COUNTERS)


def test_repeated_materialization_is_byte_deterministic():
    output = materialize(ROOT)
    first = {path.name: path.read_bytes() for path in output.iterdir() if path.is_file() and path.name != "REPORT.md"}
    output = materialize(ROOT)
    second = {path.name: path.read_bytes() for path in output.iterdir() if path.is_file() and path.name != "REPORT.md"}
    assert first == second
    assert canonical_bytes(contract()) == canonical_bytes(contract())


def test_required_artifacts_exist_and_no_advancement_outcome_is_derived():
    output = ROOT / OUTPUT_REL
    required = {"REPORT.md", "criterion_operationalization.json", "criterion_operationalization.schema.json", "evidence_contract.schema.json", "execution_ledger.json", "historical_artifact_hashes.json", "experiment_manifest.json", "quality_gates.json", "scientific_decision.json"}
    assert required <= {path.name for path in output.iterdir()}
    decision = json.loads((output / "scientific_decision.json").read_text())
    assert decision["advancement_outcome_derived"] is False
    assert decision["test_access_authorized"] is False
