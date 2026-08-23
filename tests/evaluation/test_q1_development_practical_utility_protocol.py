# ruff: noqa: E501

import hashlib
import json
from pathlib import Path

import pytest

from evaluation.q1_development_practical_utility_protocol import (
    CONFIG_REL,
    OUTPUT_REL,
    load_protocol,
    materialize,
    validate_protocol,
)

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def protocol():
    materialize(ROOT)
    return load_protocol(ROOT)


def test_test_boundary_and_declaration_only_ledger(protocol):
    assert protocol["sealed_partition"] == "test"
    ledger = json.loads((ROOT / OUTPUT_REL / "execution_ledger.json").read_text())
    assert ledger["sprint_mode"] == "PROTOCOL_DECLARATION_ONLY"
    assert all(value == 0 for key, value in ledger.items() if key != "sprint_mode")


def test_threshold_grid_is_finite_ordered_unique_frozen(protocol):
    grid = protocol["threshold_policy"]["grid"]
    assert grid == [index / 20 for index in range(1, 20)]
    assert grid == sorted(set(grid))
    assert all(0 < value < 1 for value in grid)
    assert 0.50 in grid
    assert protocol["threshold_policy"]["optimization"] is False
    assert protocol["threshold_policy"]["outcome_dependent_threshold_selection"] is False


def test_normalized_cost_scenarios_are_frozen_and_non_monetary(protocol):
    costs = protocol["cost_model"]
    assert costs["FN_FP_ratios"] == [1, 2, 5, 10, 20]
    assert costs["C_FP"] == 1 and costs["C_TP"] == costs["C_TN"] == 0
    assert "not_monetary" in costs["type"]
    assert protocol["decision_context"]["industrial_deployment_cost_claim"] is False
    assert costs["outcome_dependent_cost_selection"] is False


def test_formulas_and_baselines_are_exact(protocol):
    assert (
        protocol["decision_curve"]["formula"]
        == "NB(t) = TP(t) / N - FP(t) / N * t / (1 - t)"
    )
    assert protocol["decision_curve"]["baselines"] == [
        "TREAT_NONE_FLAG_NONE",
        "TREAT_ALL_FLAG_ALL",
    ]
    assert protocol["utility"]["expected_cost_formula"] == (
        "ExpectedCost(t, r) = FP(t) * C_FP + FN(t) * C_FN(r)"
    )
    assert protocol["utility"]["normalized_cost_formula"] == (
        "NormalizedCost(t, r) = ExpectedCost(t, r) / N"
    )


def test_temporal_memberships_match_frozen_sprint_36(protocol):
    temporal = protocol["temporal_protocol"]
    source = ROOT / temporal["source"]
    assert hashlib.sha256(source.read_bytes()).hexdigest() == temporal["source_sha256"]
    persisted = json.loads((ROOT / OUTPUT_REL / "temporal_memberships.json").read_text())
    assert persisted["verdict"] == "MATCHES_FROZEN_SPRINT_36_DEVELOPMENT_MEMBERSHIPS"
    assert [item["origin_id"] for item in persisted["origins"]] == [
        "O1", "O2", "O3", "O4", "O5"
    ]
    assert all(item["prevalence"] > 0 for item in persisted["origins"])


def test_metric_dispersion_and_inference_policies(protocol):
    metrics = set(protocol["outputs"]["per_origin_calibration_threshold"])
    probability = set(protocol["outputs"]["probability_level"])
    assert {"MCC", "TP", "FP", "TN", "FN", "net_benefit"} <= metrics
    assert {"ROC_AUC", "PR_AUC", "Brier", "ECE"} <= probability
    assert protocol["outputs"]["accuracy_or_f1_as_sole_evidence"] is False
    assert {"median", "minimum", "maximum", "Q1", "Q3", "IQR"} <= set(
        protocol["aggregation"]["required"]
    )
    assert protocol["inference"]["multiple_comparison_correction"] == (
        "Benjamini-Hochberg FDR"
    )
    assert protocol["inference"]["unit"] == "temporal_origin"


def test_calibration_and_advancement_do_not_make_final_claims(protocol):
    assert protocol["calibration_states"] == ["UNCALIBRATED", "PLATT", "ISOTONIC"]
    rule = protocol["advancement"]
    assert rule["highest_single_metric_sufficient"] is False
    assert rule["simplest_defensible_candidate_may_advance"] is True
    assert rule["final_candidate_selected"] is False
    assert rule["holdout_access_authorized"] is False


def test_historical_sprint_artifacts_are_hash_persisted(protocol):
    hashes = json.loads((ROOT / OUTPUT_REL / "historical_artifact_hashes.json").read_text())
    sprint_36 = "audits/q1-forward-development-calibration/1.0.0/REPORT.md"
    assert hashes[sprint_36] == hashlib.sha256((ROOT / sprint_36).read_bytes()).hexdigest()
    assert any("q1-modality-factorial" in path for path in hashes)
    assert any("q1-fusion-process-ablation" in path for path in hashes)


def test_validator_rejects_outcome_dependent_threshold_selection(protocol):
    changed = json.loads(json.dumps(protocol))
    changed["threshold_policy"]["outcome_dependent_threshold_selection"] = True
    with pytest.raises(ValueError, match="declaration-only"):
        validate_protocol(ROOT, changed)


def test_all_required_machine_readable_artifacts_exist(protocol):
    required = {
        "REPORT.md", "protocol.json", "cost_scenarios.json", "threshold_grid.json",
        "decision_curve_definition.json", "utility_definition.json",
        "temporal_memberships.json", "metric_policy.json", "inference_policy.json",
        "advancement_rule.json", "methodological_alignment.json",
        "historical_artifact_hashes.json", "experiment_manifest.json",
        "execution_ledger.json", "scientific_decision.json",
    }
    assert required <= {path.name for path in (ROOT / OUTPUT_REL).iterdir()}
    assert (ROOT / CONFIG_REL).exists()
