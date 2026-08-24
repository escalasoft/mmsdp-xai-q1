import copy
import hashlib
import inspect
import json
from pathlib import Path

import pytest

from evaluation.q1_advancement_governance_protocol import CRITERIA, STATES
from evaluation.q1_controlled_criterion_state_evaluation import (
    PROHIBITED_COUNTERS,
    RULE_PATH,
    _observation,
    accepted_historical_hashes,
    build_evidence,
    build_integrity_evidence,
    canonical_bytes,
    current_historical_hashes,
    evaluate,
    execution_ledger,
    observed_integrity_evidence,
    record_quality_gate_evidence,
    validate_evaluation,
    verify_hashes,
)
from evaluation.q1_prospective_criterion_operationalization import (
    contract as sprint_41_contract,
)
from evaluation.q1_prospective_criterion_operationalization import (
    derive_integrity_state,
)

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def result():
    return evaluate(ROOT)


def test_exact_nine_criterion_completeness_and_order(result):
    assert [row["criterion"] for row in result["criteria"]] == list(CRITERIA)
    assert len(result["criteria"]) == 9


def test_state_vocabulary_is_frozen(result):
    assert result["canonical_state_vocabulary"] == list(STATES)
    assert {row["state"] for row in result["criteria"]} <= set(STATES)


def test_materialization_is_deterministic(result):
    assert canonical_bytes(result) == canonical_bytes(evaluate(ROOT))


def test_every_record_has_evidence_provenance(result):
    for row in result["criteria"]:
        assert row["evidence_references"]
        assert all(
            ref["path"] and len(ref["sha256"]) == 64 and ref["originating_sprint"]
            for ref in row["evidence_references"]
        )
        assert (
            row["evidence_provenance"]["eligibility"]
            == "ACCEPTED_PERSISTED_DEVELOPMENT_ONLY"
        )


def test_every_record_uses_sprint_41_rule_provenance(result):
    assert all(
        row["rule_reference"]["path"] == RULE_PATH
        and row["rule_reference"]["declared_in_sprint"] == "10.8.2.41"
        for row in result["criteria"]
    )


def test_temporal_prospective_semantics(result):
    assert result["evaluation_timing"] == "DERIVED_DURING_AUTHORIZED_SPRINT_10.8.2.42"
    assert result["prospectivity"] == {
        "sprint_41_role": "RULE_DEFINITION_NOT_PRIOR_STATE_DERIVATION",
        "retrospective_reinterpretation": False,
        "future_evidence_used": False,
    }


def test_complexity_policy_has_sprint_41_provenance(result):
    row = next(
        row for row in result["criteria"] if row["criterion"] == "complexity_parsimony"
    )
    assert (
        row["rule_reference"]["rule_type"] == "PARETO_COMPLEXITY_WITH_INCREMENTAL_VALUE"
    )
    assert row["rule_reference"]["declared_in_sprint"] == "10.8.2.41"


def test_stability_is_independent(result):
    stability = next(
        row
        for row in result["criteria"]
        if row["criterion"] == "stability_across_origins"
    )
    complexity = next(
        row for row in result["criteria"] if row["criterion"] == "complexity_parsimony"
    )
    assert stability["rule_reference"]["rule_type"] == "FIVE_ORIGIN_SIGN_CONSISTENCY"
    assert stability["rule_reference"] != complexity["rule_reference"]


@pytest.mark.parametrize("mutation", ["missing", "extra", "duplicate"])
def test_rejects_noncanonical_criteria(result, mutation):
    value = copy.deepcopy(result)
    if mutation == "missing":
        value["criteria"].pop()
    elif mutation == "extra":
        value["criteria"].append(
            copy.deepcopy(value["criteria"][-1]) | {"criterion": "extra"}
        )
    else:
        value["criteria"][-1] = copy.deepcopy(value["criteria"][0])
    with pytest.raises(ValueError):
        validate_evaluation(value)


@pytest.mark.parametrize(
    "field", ["advancement_outcome", "final_candidate", "governance_outcome"]
)
def test_rejects_unauthorized_advancement_fields(result, field):
    value = copy.deepcopy(result)
    value[field] = "GO"
    with pytest.raises(ValueError, match="unauthorized advancement"):
        validate_evaluation(value)


def test_test_remains_sealed(result):
    assert result["test_sealed"] is True
    assert result["advancement_outcome_derived"] is False


def test_all_prohibited_counters_are_zero():
    ledger = execution_ledger()
    assert all(ledger[name] == 0 for name in PROHIBITED_COUNTERS)


def test_historical_protected_files_unchanged():
    manifest = json.loads(
        (
            ROOT
            / "audits/q1-controlled-criterion-state-evaluation/1.0.0"
            / "historical_artifact_hashes.json"
        ).read_text()
    )
    result = verify_hashes(ROOT, manifest)
    assert result["protected_files_checked"] == len(manifest)
    assert result["missing_files"] == []
    assert result["extra_files"] == []
    assert result["hash_mismatches"] == []
    assert result["passed"] is True


def test_vector_is_evidence_derived(result):
    evidence = build_evidence(ROOT)
    assert set(evidence) == set(CRITERIA)
    assert [row["state"] for row in result["criteria"]] == [
        "MIXED",
        "PASS",
        "MIXED",
        "MIXED",
        "MIXED",
        "MIXED",
        "MIXED",
        "MIXED",
        "PASS",
    ]


def test_historical_scope_includes_sprint_41():
    paths = accepted_historical_hashes(ROOT)
    assert any(
        path.startswith("audits/q1-prospective-criterion-operationalization/")
        for path in paths
    )


def test_invariant_name_alone_cannot_pass():
    evidence = observed_integrity_evidence(["required invariant"], {})
    assert evidence["valid"] is False
    assert derive_integrity_state(evidence, ["required invariant"]) == "UNRESOLVED"


def test_missing_or_malformed_provenance_is_unresolved():
    evidence = observed_integrity_evidence(
        ["required invariant"],
        {
            "required invariant": {
                "valid": True,
                "supported": True,
                "path": "artifact.json",
                "field": "field",
                "artifact_sha256": "not-a-digest",
            }
        },
    )
    assert evidence["provenance_complete"] is False
    assert derive_integrity_state(evidence, ["required invariant"]) == "UNRESOLVED"


def test_observed_false_invariant_fails():
    evidence = observed_integrity_evidence(
        ["required invariant"],
        {
            "required invariant": {
                "valid": True,
                "artifact_exists": True,
                "field_present": True,
                "structurally_valid": True,
                "predicate_evaluable": True,
                "supported": False,
                "path": "artifact.json",
                "field": "field",
                "artifact_sha256": "0" * 64,
            }
        },
    )
    assert derive_integrity_state(evidence, ["required invariant"]) == "FAIL"


def test_existing_artifact_missing_field_is_unresolved(tmp_path):
    artifact = tmp_path / "artifact.json"
    artifact.write_text("{}", encoding="utf-8")
    observation = _observation(
        tmp_path,
        "artifact.json",
        "required",
        None,
        False,
        field_present=False,
        structurally_valid=False,
    )
    evidence = observed_integrity_evidence(["required"], {"required": observation})
    assert observation["artifact_exists"] is True
    assert observation["field_present"] is False
    assert derive_integrity_state(evidence, ["required"]) == "UNRESOLVED"


def test_existing_artifact_malformed_field_is_unresolved(tmp_path):
    artifact = tmp_path / "artifact.json"
    artifact.write_text('{"required":"not-a-list"}', encoding="utf-8")
    observation = _observation(
        tmp_path,
        "artifact.json",
        "required",
        "not-a-list",
        False,
        field_present=True,
        structurally_valid=False,
    )
    evidence = observed_integrity_evidence(["required"], {"required": observation})
    assert observation["predicate_evaluable"] is False
    assert derive_integrity_state(evidence, ["required"]) == "UNRESOLVED"


def test_existing_valid_contradictory_field_fails(tmp_path):
    artifact = tmp_path / "artifact.json"
    artifact.write_text('{"required":false}', encoding="utf-8")
    observation = _observation(
        tmp_path,
        "artifact.json",
        "required",
        False,
        False,
        field_present=True,
        structurally_valid=True,
    )
    evidence = observed_integrity_evidence(["required"], {"required": observation})
    assert observation["predicate_evaluable"] is True
    assert derive_integrity_state(evidence, ["required"]) == "FAIL"


def test_existing_valid_supporting_field_is_pass_or_mixed(tmp_path):
    artifact = tmp_path / "artifact.json"
    artifact.write_text('{"required":true}', encoding="utf-8")
    observation = _observation(
        tmp_path,
        "artifact.json",
        "required",
        True,
        True,
        field_present=True,
        structurally_valid=True,
    )
    passing = observed_integrity_evidence(["required"], {"required": observation})
    limited = observed_integrity_evidence(
        ["required"], {"required": observation}, [{"text": "accepted limitation"}]
    )
    assert derive_integrity_state(passing, ["required"]) == "PASS"
    assert derive_integrity_state(limited, ["required"]) == "MIXED"


def test_integrity_provenance_is_field_derived():
    evidence = build_integrity_evidence(ROOT)
    for criterion in evidence.values():
        assert criterion["provenance_complete"] is True
        assert criterion["invariant_observations"]
        assert all(
            row["path"] and row["field"]
            for row in criterion["invariant_observations"].values()
        )


def test_historical_integrity_detects_independent_baseline_mismatch(tmp_path):
    relative = "audits/q1-experimental-validity-contract/1.0.0/contract.json"
    target = tmp_path / relative
    target.parent.mkdir(parents=True)
    target.write_text("changed", encoding="utf-8")
    accepted = hashlib.sha256(b"accepted").hexdigest()
    result = verify_hashes(tmp_path, {relative: accepted})
    assert result["passed"] is False
    assert result["hash_mismatches"] == [relative]


def test_historical_baseline_is_not_current_filesystem():
    accepted = accepted_historical_hashes(ROOT)
    current = current_historical_hashes(ROOT)
    assert accepted == current
    source = inspect.getsource(accepted_historical_hashes)
    assert "git" in source and "git show" not in inspect.getsource(
        current_historical_hashes
    )


def test_quality_gate_pass_cannot_be_forged_by_literal():
    import evaluation.q1_controlled_criterion_state_evaluation as module

    assert not hasattr(module, "QUALITY_GATES")
    with pytest.raises(ValueError):
        record_quality_gate_evidence(
            ROOT,
            [
                {
                    "id": "focused_pytest",
                    "command": ["pytest"],
                    "exit_code": 1,
                    "observed_output": "19 passed",
                }
            ],
        )


def test_all_integrity_invariants_have_observed_fields():
    evidence = build_integrity_evidence(ROOT)
    assert all(
        set(item["invariants"]) == set(item["invariant_observations"])
        for item in evidence.values()
    )


def _temporal_state_with_protocol(protocol):
    path = (
        "audits/q1-development-practical-utility-execution/1.0.0/"
        "protocol_integrity.json"
    )
    evidence = build_integrity_evidence(ROOT, {path: protocol})["temporal_validity"]
    rule = next(
        row
        for row in sprint_41_contract()["criteria"]
        if row["id"] == "temporal_validity"
    )
    invariants = rule["required_evidence"]["mandatory_invariants"]
    return evidence, derive_integrity_state(evidence, invariants)


def _integrity_state_with_documents(criterion, documents):
    evidence = build_integrity_evidence(ROOT, documents)[criterion]
    rule = next(
        row for row in sprint_41_contract()["criteria"] if row["id"] == criterion
    )
    invariants = rule["required_evidence"]["mandatory_invariants"]
    return evidence, derive_integrity_state(evidence, invariants)


def test_build_integrity_missing_composite_constituent_is_unresolved():
    path = (
        ROOT / "audits/q1-development-practical-utility-execution/1.0.0/"
        "protocol_integrity.json"
    )
    protocol = json.loads(path.read_text())
    protocol.pop("cost_scenarios_unchanged")
    evidence, state = _temporal_state_with_protocol(protocol)
    observation = next(
        row
        for row in evidence["invariant_observations"].values()
        if row["field"] == "threshold_grid_unchanged/cost_scenarios_unchanged"
    )
    assert observation["field_present"] is False
    assert observation["predicate_evaluable"] is False
    assert state == "UNRESOLVED"


def test_build_integrity_malformed_composite_constituent_is_unresolved():
    path = (
        ROOT / "audits/q1-development-practical-utility-execution/1.0.0/"
        "protocol_integrity.json"
    )
    protocol = json.loads(path.read_text())
    protocol["cost_scenarios_unchanged"] = "true"
    evidence, state = _temporal_state_with_protocol(protocol)
    observation = next(
        row
        for row in evidence["invariant_observations"].values()
        if row["field"] == "threshold_grid_unchanged/cost_scenarios_unchanged"
    )
    assert observation["field_present"] is True
    assert observation["structurally_valid"] is False
    assert state == "UNRESOLVED"


def test_build_integrity_valid_composite_contradiction_fails():
    path = (
        ROOT / "audits/q1-development-practical-utility-execution/1.0.0/"
        "protocol_integrity.json"
    )
    protocol = json.loads(path.read_text())
    protocol["cost_scenarios_unchanged"] = False
    evidence, state = _temporal_state_with_protocol(protocol)
    observation = next(
        row
        for row in evidence["invariant_observations"].values()
        if row["field"] == "threshold_grid_unchanged/cost_scenarios_unchanged"
    )
    assert observation["structurally_valid"] is True
    assert observation["predicate_evaluable"] is True
    assert observation["supported"] is False
    assert state == "FAIL"


def test_malformed_origins_element_is_unresolved_without_exception():
    relative = (
        "audits/q1-development-practical-utility-execution/1.0.0/"
        "temporal_memberships.json"
    )
    document = json.loads((ROOT / relative).read_text())
    document["origins"][2] = "MALFORMED"
    evidence, state = _integrity_state_with_documents(
        "temporal_validity", {relative: document}
    )
    observation = next(
        row
        for row in evidence["invariant_observations"].values()
        if row["field"] == "origins[].origin_id"
    )
    malformed = next(
        row for row in observation["constituents"] if row["field"] == "origins[2]"
    )
    assert malformed["structurally_valid"] is False
    assert state == "UNRESOLVED"


def test_nondict_fitted_state_is_unresolved_without_exception():
    relative = (
        "audits/q1-forward-development-calibration/1.0.0/"
        "calibration_reproducibility_manifest.json"
    )
    document = json.loads((ROOT / relative).read_text())
    document["fitted_states"][1] = "MALFORMED"
    evidence, state = _integrity_state_with_documents(
        "reproducibility", {relative: document}
    )
    assert evidence["valid"] is False
    assert state == "UNRESOLVED"


def test_fitted_state_missing_nested_field_is_unresolved():
    relative = (
        "audits/q1-forward-development-calibration/1.0.0/"
        "calibration_reproducibility_manifest.json"
    )
    document = json.loads((ROOT / relative).read_text())
    document["fitted_states"][0].pop("sha256")
    evidence, state = _integrity_state_with_documents(
        "reproducibility", {relative: document}
    )
    assert evidence["valid"] is False
    assert state == "UNRESOLVED"


@pytest.mark.parametrize("collection", ["criteria", "criterion_states"])
def test_malformed_governance_collection_row_is_unresolved(collection):
    relative = (
        "audits/q1-advancement-governance-outcome-mapping/1.0.0/"
        "governance_contract.json"
    )
    document = json.loads((ROOT / relative).read_text())
    document[collection][1] = "MALFORMED"
    evidence, state = _integrity_state_with_documents(
        "absence_of_outcome_driven_tuning", {relative: document}
    )
    assert evidence["valid"] is False
    assert state == "UNRESOLVED"


def test_origins_wrong_outer_type_is_unresolved_without_exception():
    relative = (
        "audits/q1-development-practical-utility-execution/1.0.0/"
        "temporal_memberships.json"
    )
    document = json.loads((ROOT / relative).read_text())
    document["origins"] = {}
    evidence, state = _integrity_state_with_documents(
        "temporal_validity", {relative: document}
    )
    observation = next(
        row
        for row in evidence["invariant_observations"].values()
        if row["field"] == "origins[].origin_id"
    )
    assert observation["structurally_valid"] is False
    assert observation["predicate_evaluable"] is False
    assert state == "UNRESOLVED"


def test_fitted_states_wrong_outer_type_is_unresolved_without_exception():
    relative = (
        "audits/q1-forward-development-calibration/1.0.0/"
        "calibration_reproducibility_manifest.json"
    )
    document = json.loads((ROOT / relative).read_text())
    document["fitted_states"] = {}
    evidence, state = _integrity_state_with_documents(
        "reproducibility", {relative: document}
    )
    observations = [
        row
        for row in evidence["invariant_observations"].values()
        if row["field"] == "fitted_states" or "fitted_states[]" in row["field"]
    ]
    assert observations
    assert all(row["structurally_valid"] is False for row in observations)
    assert all(row["predicate_evaluable"] is False for row in observations)
    assert state == "UNRESOLVED"


@pytest.mark.parametrize(
    "collection", ["criteria", "criterion_states", "precedence_rules"]
)
def test_governance_collection_wrong_outer_type_is_unresolved(collection):
    relative = (
        "audits/q1-advancement-governance-outcome-mapping/1.0.0/"
        "governance_contract.json"
    )
    document = json.loads((ROOT / relative).read_text())
    document[collection] = {}
    evidence, state = _integrity_state_with_documents(
        "absence_of_outcome_driven_tuning", {relative: document}
    )
    observation = next(
        row
        for row in evidence["invariant_observations"].values()
        if row["field"]
        == "criteria/criterion_states/precedence_rules/independent_authorizations"
    )
    constituent = next(
        row for row in observation["constituents"] if row["field"] == collection
    )
    assert constituent["structurally_valid"] is False
    assert observation["predicate_evaluable"] is False
    assert state == "UNRESOLVED"


def test_malformed_precedence_rule_is_retained_and_unresolved():
    relative = (
        "audits/q1-advancement-governance-outcome-mapping/1.0.0/"
        "governance_contract.json"
    )
    document = json.loads((ROOT / relative).read_text())
    document["precedence_rules"][2] = "MALFORMED"
    evidence, state = _integrity_state_with_documents(
        "absence_of_outcome_driven_tuning", {relative: document}
    )
    observation = next(
        row
        for row in evidence["invariant_observations"].values()
        if row["field"]
        == "criteria/criterion_states/precedence_rules/independent_authorizations"
    )
    malformed = next(
        row
        for row in observation["constituents"]
        if row["field"] == "precedence_rules[2]"
    )
    assert malformed["observed_value"] == "MALFORMED"
    assert malformed["structurally_valid"] is False
    assert observation["predicate_evaluable"] is False
    assert state == "UNRESOLVED"
