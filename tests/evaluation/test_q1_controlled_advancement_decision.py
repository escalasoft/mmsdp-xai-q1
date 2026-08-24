# ruff: noqa: E501

import copy
import json
from pathlib import Path

import pytest

from evaluation.q1_advancement_governance_protocol import derive_outcome
from evaluation.q1_controlled_advancement_decision import (
    EVIDENCE_PATH,
    GOVERNANCE_PATH,
    OUTPUT_REL,
    PERFORMANCE_SAFEGUARD,
    PROHIBITED_COUNTERS,
    accepted_historical_hashes,
    derive,
    execution_ledger,
    materialize,
    verify_historical_integrity,
)

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module", autouse=True)
def artifacts():
    materialize(ROOT)


def evidence():
    return json.loads((ROOT / EVIDENCE_PATH).read_text())


def test_exact_sprint_42_states_are_preserved_and_derivation_is_deterministic():
    expected = [
        {"criterion": row["criterion"], "state": row["state"]}
        for row in evidence()["criteria"]
    ]
    first = derive(ROOT)
    second = derive(ROOT)
    assert first == second
    assert first["input_criterion_state_vector"] == expected
    assert first["authorized_outcome_count"] == 1


def test_frozen_mapper_and_precedence_are_used_without_outcome_hard_coding():
    value = derive(ROOT)
    states = {
        row["criterion"]: row["state"] for row in value["input_criterion_state_vector"]
    }
    expected = derive_outcome(states)
    assert (
        value["advancement_outcome"],
        value["matched_precedence_rule"],
        value["reason_code"],
    ) == expected
    all_pass = evidence()
    for row in all_pass["criteria"]:
        row["state"] = "PASS"
    assert derive(ROOT, all_pass)["advancement_outcome"] == "GO"
    assert derive(ROOT, all_pass)["advancement_outcome"] != value["advancement_outcome"]


@pytest.mark.parametrize(
    ("criterion", "state", "outcome", "rule"),
    [
        ("leakage_safety", "FAIL", "BLOCKED", "RULE_2"),
        ("discrimination", "FAIL", "NO_GO", "RULE_3"),
        ("calibration", "UNRESOLVED", "BLOCKED", "RULE_1"),
        ("practical_utility", "MIXED", "GO_WITH_LIMITATIONS", "RULE_4"),
    ],
)
def test_fail_unresolved_and_mixed_handling(criterion, state, outcome, rule):
    value = evidence()
    for row in value["criteria"]:
        row["state"] = "PASS"
        if row["criterion"] == criterion:
            row["state"] = state
    result = derive(ROOT, value)
    assert (result["advancement_outcome"], result["matched_precedence_rule"]) == (
        outcome,
        rule,
    )


def test_unresolved_precedes_integrity_and_scientific_fail():
    value = evidence()
    states = {
        "leakage_safety": "FAIL",
        "discrimination": "FAIL",
        "calibration": "UNRESOLVED",
    }
    for row in value["criteria"]:
        row["state"] = states.get(row["criterion"], "PASS")
    result = derive(ROOT, value)
    assert result["matched_precedence_rule"] == "RULE_1"
    assert [row["precedence"] for row in result["precedence_evaluation"]] == [
        1,
        2,
        3,
        4,
        5,
    ]


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value["criteria"].pop(),
        lambda value: value["criteria"].append(copy.deepcopy(value["criteria"][0])),
        lambda value: value["criteria"][0].__setitem__("state", "pass"),
        lambda value: value.__setitem__("test_sealed", False),
        lambda value: value["criteria"][0].__setitem__("evidence_references", []),
    ],
)
def test_malformed_or_non_evaluable_evidence_is_rejected(mutation):
    value = evidence()
    mutation(value)
    with pytest.raises(ValueError):
        derive(ROOT, value)


def test_no_test_fitting_tuning_or_xai_and_documentary_safeguard_only():
    ledger = execution_ledger()
    assert all(ledger[name] == 0 for name in PROHIBITED_COUNTERS)
    assert (
        ledger["TEST_label_accesses"]
        == ledger["model_fits"]
        == ledger["threshold_optimizations"]
        == 0
    )
    assert PERFORMANCE_SAFEGUARD["documentary_only"] is True
    assert PERFORMANCE_SAFEGUARD["modifies_frozen_decision_mapper"] is False
    assert PERFORMANCE_SAFEGUARD["introduces_sprint_43_advancement_criterion"] is False


def test_only_explicit_accepted_inputs_are_loaded_and_governance_is_frozen():
    source = (ROOT / "src/evaluation/q1_controlled_advancement_decision.py").read_text()
    assert "data/" not in source and "outputs/" not in source
    assert "fit(" not in source and "tune(" not in source
    assert (ROOT / GOVERNANCE_PATH).is_file()


def test_historical_artifacts_match_immutable_pre_sprint_43_head():
    result = verify_historical_integrity(ROOT, accepted_historical_hashes(ROOT))
    assert result["passed"] is True
    assert result["historical_modification_count"] == 0


def test_materialized_artifacts_reconstruct_decision():
    output = ROOT / OUTPUT_REL
    persisted = json.loads((output / "advancement_decision.json").read_text())
    assert persisted == derive(ROOT)
    assert (
        json.loads((output / "execution_ledger.json").read_text()) == execution_ledger()
    )
