"""Sprint 48D audit-package tests."""

from __future__ import annotations

import json
from pathlib import Path

from experimentation.q1_prospective_ground_truth_provenance import generate, validate


def test_generation_is_deterministic_and_valid(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    first = generate(root, tmp_path / "first")
    second = generate(root, tmp_path / "second")
    assert validate(first) == []
    assert validate(second) == []
    first_files = {path.name: path.read_bytes() for path in first.iterdir()}
    second_files = {path.name: path.read_bytes() for path in second.iterdir()}
    assert first_files == second_files


def test_primary_stop_condition_and_contingency(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    output = generate(root, tmp_path)
    provenance = json.loads((output / "provenance_acquisition_report.json").read_text())
    contingency = json.loads(
        (output / "contingency_dataset_assessment.json").read_text()
    )
    failures = json.loads((output / "full_suite_failure_inventory.json").read_text())
    assert (
        provenance["classification"]
        == "PRIMARY_BENCHMARK_INFEASIBLE_CONTINGENCY_REQUIRED"
    )
    assert provenance["stop_condition"]["met"] is True
    assert provenance["primary_benchmark_scientifically_viable"] is False
    assert contingency["contingency_required"] is True
    assert contingency["training_or_scoring_performed"] is False
    assert contingency["datasets_substituted"] == []
    assert failures["classification_counts"] == {
        "48D_REGRESSION": 0,
        "EXPECTED_HISTORICAL_INTEGRITY_GUARD": 25,
        "PREEXISTING_FAILURE": 0,
        "UNKNOWN_REQUIRES_INVESTIGATION": 0,
    }


def test_matrix_and_gate_results_cover_all_projects(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    output = generate(root, tmp_path)
    matrix = json.loads((output / "evidence_gap_matrix.json").read_text())
    eligibility = json.loads((output / "project_target_eligibility.json").read_text())
    assert len(matrix["rows"]) == 21
    assert sum(row["prospective_identities"] for row in matrix["rows"]) == 58_272
    assert all(row["repository_available"] for row in matrix["rows"])
    assert all(row["ref_snapshot_match"] for row in matrix["rows"])
    assert eligibility["eligible_count"] == 0
    assert all(row["eligibility"] == "INELIGIBLE" for row in eligibility["projects"])
    assert all(len(row["gates"]) == 15 for row in eligibility["projects"])


def test_states_and_target_access_fail_closed(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    output = generate(root, tmp_path)
    censoring = json.loads((output / "right_censoring_audit.json").read_text())
    policy = json.loads((output / "target_access_policy.json").read_text())
    expected_interpretation = (
        "maturity is not classifiable until a defensible rule and complete evidence "
        "coverage exist; all rows therefore remain provenance-unresolved rather than "
        "being prematurely censored or assigned zero"
    )
    assert censoring == {
        "ambiguous": 0,
        "evidence_cutoff": "2026-08-30T23:59:59-05:00",
        "interpretation": expected_interpretation,
        "provenance_unresolved": 58_272,
        "right_censored": 0,
        "schema_version": "q1-48d-right-censoring-audit-1.0.0",
        "supported_negative": 0,
        "supported_positive": 0,
    }
    assert policy["target_access_count"] == 0
    assert policy["predictive_scoring_count"] == 0
    assert policy["model_training_count"] == 0
    assert policy["target_xai_count"] == 0
