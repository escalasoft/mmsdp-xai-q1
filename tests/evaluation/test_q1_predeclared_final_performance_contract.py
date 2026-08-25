# ruff: noqa: E501
import copy
import json
import subprocess
from pathlib import Path

import pytest

from evaluation.q1_predeclared_final_performance_contract import (
    CALIBRATION_METRICS,
    OUTPUT_REL,
    PRIMARY_METRICS,
    PROHIBITED_COUNTERS,
    accepted_historical_hashes,
    contract,
    execution_ledger,
    materialize,
    validate_contract,
    verify_historical_integrity,
)

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module", autouse=True)
def artifacts():
    materialize(ROOT)


def test_sprint43_authority_is_exact_and_test_remains_sealed():
    value = contract(ROOT)
    source = value["authoritative_sprint43_input"]
    assert (source["advancement_outcome"], source["matched_precedence_rule"]) == ("GO_WITH_LIMITATIONS", "RULE_4")
    assert source["test_sealed"] is True
    assert all(source[key] is False for key in ("test_access_authorized", "final_candidate_authorized", "threshold_selection_authorized", "calibration_selection_authorized", "xai_authorized"))
    assert all(value["sprint44_authorizations"][key] is False for key in value["sprint44_authorizations"])


def test_metric_set_is_non_reducible_and_prevalence_mandatory():
    value = contract(ROOT)
    assert value["reporting"]["primary_metrics_required_exactly"] == list(PRIMARY_METRICS)
    assert "positive-class prevalence" not in PRIMARY_METRICS
    assert value["reporting"]["mandatory_descriptive_context"] == [
        "positive-class prevalence"
    ]
    assert value["reporting"]["calibration_metrics_required_exactly"] == list(CALIBRATION_METRICS)
    assert value["imbalance_governance"]["positive_class_prevalence_mandatory"] is True
    reduced = copy.deepcopy(value)
    reduced["reporting"]["primary_metrics_required_exactly"].pop()
    with pytest.raises(ValueError):
        validate_contract(reduced)


def test_post_hoc_imbalance_feature_and_representation_changes_are_prohibited():
    value = contract(ROOT)
    assert {"SMOTE", "SMOTE-Tomek", "ADASYN"} <= set(value["imbalance_governance"]["primary_experiment_post_outcome_prohibited"])
    assert {"Boruta", "genetic-algorithm feature selection", "recursive selection"} <= set(value["feature_selection_governance"]["post_hoc_prohibited"])
    assert value["representation_scope"]["primary_representations"] == ["CODE", "PROCESS", "TEXT"]
    assert value["representation_scope"]["post_hoc_rescue_prohibited"] is True


def test_high_performance_requires_audit_and_limited_performance_cannot_rescue_tune():
    value = contract(ROOT)
    high = value["anomalously_high_performance"]
    limited = value["limited_performance"]
    assert high["diagnostic_audit_required"] and high["audit_result_must_be_persisted"] and high["automatic_acceptance_prohibited"]
    assert {"leakage", "temporal contamination", "train/evaluation overlap"} <= set(high["checks"])
    assert limited["test_tuning_prohibited"] and limited["rescue_models_features_resampling_prohibited"]
    assert limited["report_exactly_and_preserve_as_evidence"]


def test_no_candidate_threshold_calibrator_test_or_other_prohibited_operation():
    ledger = execution_ledger()
    assert all(ledger[name] == 0 for name in PROHIBITED_COUNTERS)
    persisted = json.loads((ROOT / OUTPUT_REL / "scientific_decision.json").read_text())
    assert persisted["final_candidate_authorized"] is False
    assert persisted["threshold_selection_authorized"] is False
    assert persisted["calibration_selection_authorized"] is False


def test_historical_evidence_unchanged_against_accepted_git_objects():
    result = verify_historical_integrity(ROOT, accepted_historical_hashes(ROOT))
    assert result["passed"] and not result["historical_tracked_modifications"]


def test_contract_is_deterministic_schema_valid_and_manifest_matches():
    assert contract(ROOT) == contract(ROOT)
    validate_contract(contract(ROOT))
    output = materialize(ROOT)
    first = {p.name: p.read_bytes() for p in output.iterdir()}
    materialize(ROOT)
    assert first == {p.name: p.read_bytes() for p in output.iterdir()}
    manifest = json.loads((output / "experiment_manifest.json").read_text())
    assert manifest["starting_main"] == "1cd7b980c36a212f24d9cc239de2fcdb8473b821"
    payload = json.dumps(
        {
            "schema": json.loads(
                (output / "final_performance_contract.schema.json").read_text()
            ),
            "data": json.loads(
                (output / "final_performance_contract.json").read_text()
            ),
        }
    )
    script = """
const Ajv = require('ajv');
const input = JSON.parse(process.argv[1]);
const valid = new Ajv({allErrors: true, schemaId: 'auto'}).validate(input.schema, input.data);
if (!valid) process.exit(1);
"""
    subprocess.run(["node", "-e", script, payload], cwd=ROOT, check=True)
