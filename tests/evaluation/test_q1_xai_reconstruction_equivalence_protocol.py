import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "audits/q1-xai-reconstruction-equivalence-protocol/1.0.0"


def _read(name: str):
    return json.loads((PACKAGE / name).read_text())


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_package_manifest_and_sealed_sprint54_references_verify():
    entries = []
    for line in (PACKAGE / "MANIFEST.sha256").read_text().splitlines():
        digest, name = line.split("  ", 1)
        entries.append(name)
        assert _sha256(PACKAGE / name) == digest
    assert len(entries) == 12

    registry = _read("sealed_reference_registry.json")
    assert registry["sealed_inputs_modified"] is False
    for reference in registry["references"]:
        assert _sha256(ROOT / reference["path"]) == reference["sha256"]


def test_block6_is_contract_only_and_performs_no_prohibited_operation():
    protocol = _read("reconstruction_authorization_protocol.json")
    assert protocol["block6_authorizes_execution"] is False
    assert protocol["stop_condition"] == (
        "PROTOCOL_FROZEN_NO_RECONSTRUCTION_NO_G4_NO_G5_NO_XAI_NO_T2"
    )
    assert protocol["current_authorization"] == {
        "train_source_only_reconstruction": (
            "DENY_PENDING_SEPARATE_HUMAN_G5_AUTHORIZATION"
        ),
        "t1_feature_access_or_model_query": (
            "DENY_PENDING_SEPARATE_HUMAN_G4_AUTHORIZATION"
        ),
        "fusion_calibration_final_output_verification": (
            "DENY_PENDING_G4_G5_GATE_AUTHORIZATION"
        ),
        "t2_access": "DENY_SEALED_REVIEWER_RESERVE",
        "xai_execution": "DENY_PENDING_EQUIVALENCE_AND_XAI_AUTHORIZATION",
    }
    assert {path.suffix for path in PACKAGE.iterdir() if path.is_file()} <= {
        ".json",
        ".md",
        ".sha256",
    }


def test_governance_counters_and_scientific_classifications_remain_frozen():
    state = _read("reconstruction_authorization_protocol.json")[
        "immutable_scientific_state"
    ]
    assert state == {
        "sprint54_classification": "MIXED_CONFIRMATORY_EVIDENCE",
        "evidence_audit_classification": (
            "PASS_CONFIRMATORY_EVIDENCE_INTERNALLY_CONSISTENT_REPORTABLE_MIXED"
        ),
        "t1_predictive_access_count": 1,
        "t1_predictive_scoring_count": 1,
        "t1_rerun_permitted": False,
        "t2_predictive_access_count": 0,
        "t2_state": "DENY_SEALED_REVIEWER_RESERVE",
        "xai_execution_count": 0,
    }


def test_reconstruction_inputs_are_train_source_only_and_fail_closed():
    inputs = _read("frozen_input_provenance_contract.json")
    assert inputs["allowed_fit_partition"] == "TRAIN_SOURCE_ONLY"
    prohibited = " ".join(inputs["prohibited_inputs"])
    for required in ("T1 labels", "T1 metrics", "T1 explanation", "T2"):
        assert required in prohibited
    assert inputs["input_validation_outcome_on_any_mismatch"] == (
        "RECONSTRUCTION_PREREQUISITES_INCOMPLETE"
    )
    components = _read("reconstruction_component_inventory.json")
    assert components["minimum_final_state_units"] == {
        "unimodal_base_predictors": 168,
        "numeric_fitted_preprocessing_chains": 112,
        "text_fitted_tfidf_vectorizers": 56,
        "fusion_logistic_regression_meta_learners": 224,
        "persisted_isotonic_mappings_reused_not_refitted": 14,
        "raw_identity_calibration_mappings": 378,
    }


def test_determinism_and_tolerances_are_prospectively_frozen():
    deterministic = _read("deterministic_execution_contract.json")
    assert deterministic["independent_reconstruction_repetitions"] == 3
    assert deterministic["execution_controls"]["cpu_threads"] == 1
    assert deterministic["execution_controls"]["algorithm_n_jobs"] == 1
    tolerance = _read("numerical_tolerance_policy.json")
    assert tolerance["frozen_before_reconstruction"] is True
    assert tolerance["policy_mutability"] == (
        "IMMUTABLE_AFTER_ANY_RECONSTRUCTED_STATE_OR_OUTPUT_IS_OBSERVED"
    )
    assert tolerance["deterministic_repeatability"]["tolerance"] == 0.0
    probability = tolerance["row_level_probability_equivalence"]
    assert probability["maximum_absolute_error"] == 1e-12
    assert probability["maximum_relative_error"] == 1e-10
    assert tolerance["decision_equivalence"]["threshold"] == 0.5
    assert tolerance["decision_equivalence"]["mismatch_budget"] == 0


def test_gate_order_requires_row_level_not_metric_equivalence():
    gates = _read("equivalence_gate_hierarchy.json")
    assert [gate["gate"] for gate in gates["ordered_fail_closed_gates"]] == [
        "G1_RECONSTRUCTION_PROVENANCE_EQUIVALENCE",
        "G2_FITTED_STATE_STRUCTURAL_VALIDITY",
        "G3_DETERMINISTIC_RECONSTRUCTION_REPEATABILITY",
        "G4_RAW_PREDICTIVE_OUTPUT_EQUIVALENCE",
        "G5_FUSION_CALIBRATION_FINAL_OUTPUT_EQUIVALENCE",
    ]
    assert all(
        gate["block6_execution"] == "DENY"
        for gate in gates["ordered_fail_closed_gates"][1:]
    )
    assert "aggregate or project-level metric similarity" in gates[
        "metric_non_equivalence"
    ]


def test_failure_partial_eligibility_and_xai_policy_are_fail_closed():
    failure = _read("failure_partial_eligibility_policy.json")
    assert failure["current_outcome"] == "RECONSTRUCTION_AUTHORIZED_NOT_EXECUTED"
    assert "PARTIAL_XAI_ELIGIBILITY" in failure["allowed_outcomes"]
    assert failure["no_fallback"] == (
        "XAI_INELIGIBLE_RECONSTRUCTION_NOT_EQUIVALENT"
    )
    xai = _read("xai_eligibility_policy.json")
    assert xai["stored_predictions_alone_sufficient"] is False
    assert "NOT_AUTHORIZED_NOT_EXECUTED" in xai["shap_status"]
    assert "NOT_AUTHORIZED_NOT_EXECUTED" in xai["lime_status"]
    assert xai["block6_xai_execution_count"] == 0


def test_t1_technical_verification_is_separate_and_t2_remains_sealed():
    separation = _read("t1_t2_verification_separation_policy.json")
    original = separation["sprint54_confirmatory_evaluation"]
    assert original["access_count"] == 1
    assert original["predictive_scoring_count"] == 1
    assert original["rerun_permitted"] is False
    future = separation["future_reconstruction_equivalence_verification"]
    assert future["state"] == "NOT_AUTHORIZED_NOT_EXECUTED"
    assert separation["separate_ledger_required"][
        "does_not_increment_original_t1_predictive_access_count"
    ] is True
    assert separation["t2"] == {
        "state": "DENY_SEALED_REVIEWER_RESERVE",
        "access_count": 0,
        "prohibited": [
            "identities",
            "features",
            "labels",
            "predictions",
            "model queries",
            "equivalence checks",
            "SHAP",
            "LIME",
            "calibration",
            "thresholding",
            "statistics",
        ],
    }
