# ruff: noqa: E501

import json
from pathlib import Path

import pytest

from governance.q1_t1_confirmatory_protocol import (
    ALGORITHMS,
    CONFIGURATIONS,
    ConfirmatoryProtocolError,
    build,
    execution_ledger,
    verify_output,
    write_package,
)

ROOT = Path(__file__).resolve().parents[2]


def test_build_freezes_scientific_universe_and_questions():
    artifacts = build(ROOT)
    assert len(ALGORITHMS) == 4
    assert len(CONFIGURATIONS) == 7
    questions = artifacts["confirmatory_research_questions.json"]
    assert [row["id"] for row in questions["questions"]] == [
        f"RQ-T1-{number}" for number in range(1, 7)
    ]
    assert questions["full_multimodality_required_to_win_everywhere"] is False


def test_comparators_are_development_selected_and_complete():
    contract = build(ROOT)["frozen_comparator_contract.json"]
    assert contract["identity_count"] == 112
    assert len(contract["comparator_identities"]) == 112
    assert all(not row["t1_selection_permitted"] for row in contract["comparator_identities"])
    assert {row["family"] for row in contract["comparator_identities"]} == {
        "BEST_UNIMODAL",
        "BEST_PAIRWISE",
    }


def test_metrics_statistics_and_ablation_are_complete():
    artifacts = build(ROOT)
    metrics = artifacts["frozen_metric_contract.json"]
    assert [row["metric"] for row in metrics["metrics"] if row["role"] == "PRIMARY"] == ["PR_AUC", "MCC"]
    assert metrics["accuracy_role"] == "NOT_PRIMARY_NOT_REQUIRED_CONFIRMATORY_METRIC"
    stats = artifacts["statistical_analysis_contract.json"]
    assert stats["omnibus"]["test"] == "FRIEDMAN"
    assert stats["post_hoc"]["test"] == "WILCOXON_SIGNED_RANK_TWO_SIDED"
    assert stats["significance_alpha"] == 0.05
    assert len(artifacts["ablation_contract.json"]["required_full_incremental_contrasts"]) == 6


def test_access_gates_are_ready_but_do_not_authorize_execution():
    artifacts = build(ROOT)
    gate = artifacts["t1_execution_authorization_gate.json"]
    assert len(gate["gates"]) == 20
    assert all(row["status"] == "PASS" for row in gate["gates"])
    assert gate["human_authorization_granted"] is False
    assert gate["t1_execution_authorized"] is False
    assert artifacts["t2_sealed_reserve_verification.json"]["role"] == "SEALED_REVIEWER_RESERVE"


def test_all_execution_counters_are_zero_and_xai_is_deferred():
    ledger = execution_ledger()
    assert ledger["all_required_counters_zero"] is True
    assert all(value == 0 for key, value in ledger.items() if key.endswith("_count"))
    xai = build(ROOT)["future_xai_multirole_protocol.json"]
    assert xai["xai_execution_count"] == 0
    assert len(xai["qa_role_interpretation_map"]) == 5


def test_reporting_and_near_perfect_audit_are_predeclared():
    artifacts = build(ROOT)
    tables = artifacts["t1_reporting_tables_contract.json"]
    assert [row["id"] for row in tables["tables"]] == [f"T1-{letter}" for letter in "ABCDEFGH"]
    assert len(artifacts["t1_reporting_figures_contract.json"]["figures"]) == 6
    audit = artifacts["near_perfect_result_audit_contract.json"]
    assert audit["trigger"] == "ANY_T1_METRIC_GREATER_THAN_OR_EQUAL_TO_0.99"
    assert audit["automatic_leakage_classification"] is False


def test_deterministic_regeneration_manifest_and_machine_readability(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    assert write_package(ROOT, first) == write_package(ROOT, second)
    assert {path.name: path.read_bytes() for path in first.iterdir()} == {
        path.name: path.read_bytes() for path in second.iterdir()
    }
    assert verify_output(first)["status"] == "PASS"
    for path in first.glob("*.json"):
        json.loads(path.read_text(encoding="utf-8"))


def test_manifest_tampering_fails_closed(tmp_path):
    output = tmp_path / "output"
    write_package(ROOT, output)
    (output / "execution_ledger.json").write_text("{}\n", encoding="utf-8")
    with pytest.raises(ConfirmatoryProtocolError, match="manifest mismatch"):
        verify_output(output)
