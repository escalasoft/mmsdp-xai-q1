import csv
import hashlib
import json
from pathlib import Path

import numpy as np

from evaluation.q1_development_practical_utility_execution import (
    ORIGINS,
    OUTPUT_REL,
    STATES,
    UNRESOLVED_DECISION,
    _confusion,
    advancement_evidence,
    calculate,
    evaluate_advancement,
    render_report_from_artifacts,
    validate_pre_execution,
)

ROOT = Path(__file__).resolve().parents[2]


def test_pre_execution_integrity_matches_frozen_sprint_37():
    audit = validate_pre_execution(ROOT)
    assert audit["thresholds"] == [index / 20 for index in range(1, 20)]
    assert audit["ratios"] == [1, 2, 5, 10, 20]
    assert tuple(row["origin_id"] for row in audit["temporal"]["origins"]) == ORIGINS
    assert tuple(audit["protocol"]["calibration_states"]) == STATES


def test_confusion_and_net_benefit_are_reconstructable():
    row = _confusion(np.asarray([1, 0, 1, 0]), np.asarray([0.9, 0.8, 0.4, 0.1]), 0.5)
    assert (row["TP"], row["FP"], row["TN"], row["FN"]) == (1, 1, 1, 1)
    assert row["net_benefit_model"] == 0.0
    assert row["net_benefit_treat_none"] == 0.0


def test_undefined_precision_is_explicit():
    row = _confusion(np.asarray([1, 0]), np.asarray([0.1, 0.2]), 0.9)
    assert row["precision"] is None
    assert row["precision_defined"] is False
    assert row["precision_undefined_reason"]


def test_cost_formula_and_baselines_use_frozen_normalization():
    recovered = {
        origin: {
            "y": np.asarray([1, 0]),
            "scores": {state: np.asarray([0.4, 0.6]) for state in STATES},
        }
        for origin in ORIGINS
    }
    curves, costs = calculate(recovered, [0.5], [2])
    assert len(curves) == 15 and len(costs) == 15
    row = costs[0]
    assert row["FP_cost"] == 1 and row["FN_cost"] == 2
    assert row["total_expected_cost"] == 3
    assert row["normalized_expected_cost"] == 1.5
    assert row["treat_none_cost"] == 2 and row["treat_all_cost"] == 1


def test_materialized_outputs_are_complete_and_sealed():
    output = ROOT / OUTPUT_REL
    required = {
        "experiment_manifest.json",
        "protocol_integrity.json",
        "temporal_memberships.json",
        "execution_ledger.json", "leakage_audit.json", "decision_curve_results.csv",
        "decision_curve_summary.json", "practical_utility_results.csv",
        "practical_utility_summary.json", "origin_stability.json",
        "calibration_state_comparison.json", "baseline_comparison.json",
        "advancement_evaluation.json", "scientific_decision.json",
        "reproducibility_manifest.json", "historical_artifact_hashes.json", "REPORT.md",
        "quality_gates.json",
    }
    assert required <= {path.name for path in output.iterdir()}
    ledger = json.loads((ROOT / OUTPUT_REL / "execution_ledger.json").read_text())
    assert ledger["decision_curve_cells"] == 285
    assert ledger["practical_utility_cells"] == 1425
    assert all(value == 0 for key, value in ledger.items() if key.startswith("TEST_"))
    with (output / "decision_curve_results.csv").open() as handle:
        assert sum(1 for _ in csv.DictReader(handle)) == 285
    with (output / "practical_utility_results.csv").open() as handle:
        assert sum(1 for _ in csv.DictReader(handle)) == 1425
    report = (output / "REPORT.md").read_text()
    assert "TEST REMAINED SEALED" in report
    assert "not measured monetary or industrial costs" in report


def test_reproducibility_rerun_equivalence_is_recorded():
    path = ROOT / OUTPUT_REL / "reproducibility_manifest.json"
    manifest = json.loads(path.read_text())
    assert manifest["deterministic_rerun_equivalence"] is True
    assert manifest["stochastic_operations"] == []


def test_all_frozen_criteria_have_only_permitted_evidence_states():
    rule = json.loads(
        (
            ROOT
            / "audits/q1-development-practical-utility-protocol/1.0.0"
            / "advancement_rule.json"
        ).read_text()
    )
    evidence = advancement_evidence()
    assert set(evidence) == set(rule["joint_criteria"])
    assert len(evidence) == 9
    assert {item["state"] for item in evidence.values()} <= {
        "PASS",
        "MIXED",
        "UNRESOLVED",
    }
    assert all(item["evidence"] and item["provenance"] for item in evidence.values())


def test_incomplete_frozen_mapping_fails_closed_as_unresolved():
    rule = json.loads(
        (
            ROOT
            / "audits/q1-development-practical-utility-protocol/1.0.0"
            / "advancement_rule.json"
        ).read_text()
    )
    result = evaluate_advancement(rule, advancement_evidence())
    assert result["decision"] == UNRESOLVED_DECISION
    assert result["mapping_complete"] is False
    assert result["experiment_execution_status"] == "SUCCESS_VALID"


def test_no_unsupported_go_with_limitations_remains_in_sprint_38():
    source = (
        ROOT / "src/evaluation/q1_development_practical_utility_execution.py"
    ).read_text()
    advancement = json.loads(
        (ROOT / OUTPUT_REL / "advancement_evaluation.json").read_text()
    )
    unsupported = "10.8.2.38_" + "GO_WITH_LIMITATIONS"
    assert unsupported not in source
    assert advancement["decision"] == UNRESOLVED_DECISION
    report = render_report_from_artifacts(ROOT)
    assert report == (ROOT / OUTPUT_REL / "REPORT.md").read_text()
    assert "12 passed, 0 failed" in report
    assert "231 passed, 0 failed" in report
    assert "1,406 passed, 1 skipped, 0 failed" in report
    assert "ADVANCEMENT_UNRESOLVED" in report
    assert "Prospective advancement-governance outcome-mapping protocol" in report
    assert unsupported not in report
    obsolete = "DEVELOPMENT practical-utility evidence synthesis"
    assert obsolete not in report


def test_numerical_evidence_hashes_are_preserved():
    expected = {
        "decision_curve_results.csv": (
            "74dbe0c82288c842693ce10de76da3e5dce0e01dc0b1398861f3c6136b8e90a2"
        ),
        "practical_utility_results.csv": (
            "9e04368c97daf4bfbaab9c1581cae18a3174f22baaff5eacf9e49993540c662f"
        ),
        "decision_curve_summary.json": (
            "1efcc05ab94002cca9b0dd4723a8617939e464985f8a024493bfdbc3edc57f87"
        ),
        "practical_utility_summary.json": (
            "8148d5acf9b810aef2f1136aa9e2c279ff741ee8ce4c861d25c67331e5b84286"
        ),
    }
    for name, digest in expected.items():
        actual = hashlib.sha256((ROOT / OUTPUT_REL / name).read_bytes()).hexdigest()
        assert actual == digest


def test_selection_and_test_use_counters_remain_zero():
    ledger = json.loads((ROOT / OUTPUT_REL / "execution_ledger.json").read_text())
    prohibited = {
        key: value
        for key, value in ledger.items()
        if key.startswith("TEST_")
        or key
        in {
            "model_fits",
            "meta_learner_fits",
            "calibration_fits",
            "calibration_selection_based_on_sprint_38_outcomes",
            "threshold_optimizations",
            "hyperparameter_searches",
            "XAI_executions",
            "external_dataset_acquisitions",
        }
    }
    assert prohibited and all(value == 0 for value in prohibited.values())


def test_sprint_32_through_37_historical_hashes_remain_valid():
    historical = json.loads(
        (ROOT / OUTPUT_REL / "historical_artifact_hashes.json").read_text()
    )
    for relative, expected in historical.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected
    protocol_dir = ROOT / "audits/q1-development-practical-utility-protocol/1.0.0"
    manifest = json.loads((protocol_dir / "experiment_manifest.json").read_text())
    for name, expected in manifest["artifact_sha256"].items():
        actual = hashlib.sha256((protocol_dir / name).read_bytes()).hexdigest()
        assert actual == expected
