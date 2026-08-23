# ruff: noqa: E501

import copy
import json
import subprocess
from pathlib import Path

import pytest

from evaluation.q1_advancement_governance_protocol import (
    AUTHORIZATIONS,
    CRITERIA,
    EFFECTIVE_FROM_SPRINT,
    INTEGRITY,
    OUTCOMES,
    OUTPUT_REL,
    SCIENTIFIC,
    STATES,
    canonical_bytes,
    contract,
    criterion_class,
    derive_outcome,
    evaluate,
    exhaustive_verification,
    historical_hashes,
    materialize,
    validate_contract,
    validate_records,
    verify_historical_hashes,
)

ROOT = Path(__file__).resolve().parents[2]


def records(states=None):
    states = states or dict.fromkeys(CRITERIA, "PASS")
    return [
        {
            "criterion": criterion,
            "criterion_class": criterion_class(criterion),
            "state": states[criterion],
            "evidence_reference": f"future/{criterion}/evidence.json",
            "provenance_reference": f"future/{criterion}/provenance.json",
            "relevant_hashes": {"evidence_sha256": "a" * 64},
        }
        for criterion in CRITERIA
    ]


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


def test_contract_exact_criteria_classes_states_outcomes_and_rules():
    governance = contract()
    validate_contract(governance)
    assert [row["id"] for row in governance["criteria"]] == list(CRITERIA)
    assert [row["id"] for row in governance["criterion_states"]] == list(STATES)
    assert [row["id"] for row in governance["advancement_outcomes"]] == list(OUTCOMES)
    assert {row["id"] for row in governance["criteria"] if row["class"] == "INTEGRITY_BLOCKING"} == set(INTEGRITY)
    assert {row["id"] for row in governance["criteria"] if row["class"] == "SCIENTIFIC_PERFORMANCE"} == set(SCIENTIFIC)
    assert governance["precedence_rules"][3] == {
        "id": "RULE_4",
        "condition": "ANY_MIXED",
        "outcome": "GO_WITH_LIMITATIONS",
    }


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda rows: rows.pop(), "malformed state vector"),
        (lambda rows: rows.append({**rows[-1], "criterion": "extra"}), "malformed state vector"),
        (lambda rows: rows.__setitem__(1, copy.deepcopy(rows[0])), "duplicate criterion"),
        (lambda rows: rows[0].__setitem__("criterion", "Leakage_Safety"), "missing, extra, or unknown criterion"),
        (lambda rows: rows[0].__setitem__("state", "pass"), "unknown state"),
    ],
)
def test_invalid_state_vectors_fail_closed(mutation, message):
    candidate = records()
    mutation(candidate)
    with pytest.raises(ValueError, match=message):
        validate_records(candidate)


def test_invalid_class_references_hashes_and_version_fail_closed():
    candidate = records()
    candidate[0]["criterion_class"] = "SCIENTIFIC_PERFORMANCE"
    with pytest.raises(ValueError, match="criterion class"):
        validate_records(candidate)
    candidate = records()
    candidate[0]["evidence_reference"] = ""
    with pytest.raises(ValueError, match="evidence reference"):
        validate_records(candidate)
    candidate = records()
    candidate[0]["relevant_hashes"] = {}
    with pytest.raises(ValueError, match="relevant hashes"):
        validate_records(candidate)
    governance = contract()
    governance["protocol_version"] = "0.0.0"
    with pytest.raises(ValueError, match="protocol version"):
        validate_contract(governance)


def test_duplicate_extra_and_invalid_contract_criteria_fail_closed():
    governance = contract()
    governance["criteria"].append(copy.deepcopy(governance["criteria"][0]))
    with pytest.raises(ValueError, match="duplicate criterion"):
        validate_contract(governance)
    governance = contract()
    governance["criteria"][0]["class"] = "SCIENTIFIC_PERFORMANCE"
    with pytest.raises(ValueError, match="criterion class"):
        validate_contract(governance)


def test_primary_mapping_and_integrity_mixed_amendment():
    base = dict.fromkeys(CRITERIA, "PASS")
    assert derive_outcome(base) == ("GO", "RULE_5", "ALL_PASS")
    for criterion in INTEGRITY:
        states = dict(base)
        states[criterion] = "MIXED"
        assert derive_outcome(states) == (
            "GO_WITH_LIMITATIONS",
            "RULE_4",
            "ANY_MIXED",
        )
    states = dict(base)
    states["calibration"] = "MIXED"
    assert derive_outcome(states)[0] == "GO_WITH_LIMITATIONS"
    states = dict(base)
    states["discrimination"] = "FAIL"
    assert derive_outcome(states)[0] == "NO_GO"
    states = dict(base)
    states["leakage_safety"] = "FAIL"
    assert derive_outcome(states)[0] == "BLOCKED"


def test_precedence_is_exact():
    base = dict.fromkeys(CRITERIA, "PASS")
    states = dict(base)
    states["reproducibility"] = "UNRESOLVED"
    states["calibration"] = "FAIL"
    assert derive_outcome(states)[1] == "RULE_1"
    states = dict(base)
    states["leakage_safety"] = "FAIL"
    states["calibration"] = "FAIL"
    assert derive_outcome(states)[1] == "RULE_2"
    states = dict(base)
    states["calibration"] = "FAIL"
    states["practical_utility"] = "MIXED"
    assert derive_outcome(states)[1] == "RULE_3"


def test_exhaustive_state_space_is_total_repeatable_and_order_invariant():
    result = exhaustive_verification()
    assert result["vectors_verified"] == 262_144
    assert sum(result["outcome_counts"].values()) == 262_144
    assert set(result["outcome_counts"]) == set(OUTCOMES)
    assert result["deterministic_repeatability"] is True
    assert result["input_order_invariance"] is True
    assert result["exactly_one_outcome_per_vector"] is True


def test_trace_order_invariance_byte_repeatability_and_authorizations():
    forward = records()
    reverse = list(reversed(copy.deepcopy(forward)))
    first = evaluate(contract(), EFFECTIVE_FROM_SPRINT, forward)
    second = evaluate(contract(), EFFECTIVE_FROM_SPRINT, reverse)
    assert canonical_bytes(first) == canonical_bytes(second)
    assert first["canonical_criterion_order"] == list(CRITERIA)
    assert first["advancement_outcome"] == "GO"
    assert all(first[key] is False for key in AUTHORIZATIONS)


def test_retrospective_application_fails_closed():
    with pytest.raises(ValueError, match="retrospective"):
        evaluate(contract(), "10.8.2.38", records())


def test_historical_hashes_and_sprint_38_status_are_unchanged():
    expected = json.loads(
        (ROOT / OUTPUT_REL / "historical_artifact_hashes.json").read_text()
    )
    verify_historical_hashes(ROOT, expected)
    assert expected == historical_hashes(ROOT)
    decision = json.loads(
        (
            ROOT
            / "audits/q1-development-practical-utility-execution/1.0.0"
            / "scientific_decision.json"
        ).read_text()
    )
    assert decision["experiment_execution_status"] == "SUCCESS_VALID"
    assert (
        decision["advancement_decision"]
        == "SPRINT_10.8.2.38_ADVANCEMENT_UNRESOLVED"
    )


def test_test_and_prohibited_operation_counters_are_zero():
    ledger = json.loads((ROOT / OUTPUT_REL / "execution_ledger.json").read_text())
    assert ledger["sprint_mode"] == "PROSPECTIVE_GOVERNANCE_PROTOCOL_ONLY"
    assert all(value == 0 for key, value in ledger.items() if key != "sprint_mode")


def test_required_artifacts_exist():
    required = {
        "governance_contract.json",
        "governance_contract.schema.json",
        "derivation_trace.schema.json",
        "historical_artifact_hashes.json",
        "experiment_manifest.json",
        "execution_ledger.json",
        "exhaustive_verification.json",
        "quality_gates.json",
        "scientific_decision.json",
        "REPORT.md",
    }
    assert required <= {path.name for path in (ROOT / OUTPUT_REL).iterdir()}


def test_materialized_contract_validates_against_real_json_schema():
    output = ROOT / OUTPUT_REL
    schema = json.loads((output / "governance_contract.schema.json").read_text())
    instance = json.loads((output / "governance_contract.json").read_text())
    assert_schema(schema, instance)


def test_representative_traces_for_all_outcomes_validate_against_schema():
    schema = json.loads(
        (ROOT / OUTPUT_REL / "derivation_trace.schema.json").read_text()
    )
    vectors = []
    for criterion, state in (
        ("reproducibility", "UNRESOLVED"),
        ("discrimination", "FAIL"),
        ("leakage_safety", "MIXED"),
    ):
        values = dict.fromkeys(CRITERIA, "PASS")
        values[criterion] = state
        vectors.append(values)
    vectors.append(dict.fromkeys(CRITERIA, "PASS"))
    traces = [evaluate(contract(), EFFECTIVE_FROM_SPRINT, records(item)) for item in vectors]
    assert {item["advancement_outcome"] for item in traces} == set(OUTCOMES)
    for trace in traces:
        assert_schema(schema, trace)


def test_malformed_contract_instances_are_rejected_by_schema():
    output = ROOT / OUTPUT_REL
    schema = json.loads((output / "governance_contract.schema.json").read_text())
    instance = json.loads((output / "governance_contract.json").read_text())
    malformed = copy.deepcopy(instance)
    malformed["criteria"][0]["class"] = "SCIENTIFIC_PERFORMANCE"
    assert_schema(schema, malformed, valid=False)
    malformed = copy.deepcopy(instance)
    malformed["precedence_rules"][3]["condition"] = "ANY_SCIENTIFIC_MIXED"
    assert_schema(schema, malformed, valid=False)
    malformed = copy.deepcopy(instance)
    malformed["independent_authorizations"]["test_access_authorized"] = True
    assert_schema(schema, malformed, valid=False)


def test_malformed_derivation_traces_are_rejected_by_schema():
    schema = json.loads(
        (ROOT / OUTPUT_REL / "derivation_trace.schema.json").read_text()
    )
    trace = evaluate(contract(), EFFECTIVE_FROM_SPRINT, records())
    malformed = copy.deepcopy(trace)
    malformed["criteria"][0]["state"] = "UNKNOWN"
    assert_schema(schema, malformed, valid=False)
    malformed = copy.deepcopy(trace)
    malformed["test_access_authorized"] = True
    assert_schema(schema, malformed, valid=False)
    malformed = copy.deepcopy(trace)
    malformed["matched_precedence_rule"] = "RULE_4"
    assert_schema(schema, malformed, valid=False)
    malformed = copy.deepcopy(trace)
    malformed["criteria"][0]["state"] = "MIXED"
    assert_schema(schema, malformed, valid=False)
