from pathlib import Path

from evaluation.q1_t1_confirmatory_execution import (
    AMENDMENT_REL,
    AUTH_REL,
    EXPECTED_AMENDMENT_MANIFEST_SHA256,
    EXPECTED_SPRINT53_MANIFEST_SHA256,
    SPRINT53_REL,
    load_json,
    verify_manifest,
)
from evaluation.q1_t1_reporting_traceability_freeze import (
    BLOCK6_CLASSIFICATION,
    BLOCK6_REL,
    BLOCK7_REL,
    EXPECTED_BLOCK6_MANIFEST_SHA256,
    EXPECTED_RESULTS_MANIFEST_SHA256,
    MIXED,
    RESULTS_REL,
)
from evaluation.q1_t1_sprint54_final_closure import (
    BLOCK7_CLASSIFICATION,
    BLOCK8_REL,
    EXPECTED_AUTH_MANIFEST_SHA256,
    EXPECTED_BLOCK7_MANIFEST_SHA256,
    FINAL_CLASSIFICATION,
)

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / BLOCK8_REL


def _read(name: str):
    return load_json(PACKAGE / name)


def test_final_manifests_and_complete_chain_of_custody_verify():
    assert verify_manifest(PACKAGE)["entry_count"] == 10
    assert verify_manifest(ROOT / SPRINT53_REL)["manifest_sha256"] == (
        EXPECTED_SPRINT53_MANIFEST_SHA256
    )
    assert verify_manifest(ROOT / AUTH_REL)["manifest_sha256"] == (
        EXPECTED_AUTH_MANIFEST_SHA256
    )
    assert verify_manifest(ROOT / AMENDMENT_REL)["manifest_sha256"] == (
        EXPECTED_AMENDMENT_MANIFEST_SHA256
    )
    assert verify_manifest(ROOT / RESULTS_REL)["manifest_sha256"] == (
        EXPECTED_RESULTS_MANIFEST_SHA256
    )
    assert verify_manifest(ROOT / BLOCK6_REL)["manifest_sha256"] == (
        EXPECTED_BLOCK6_MANIFEST_SHA256
    )
    assert verify_manifest(ROOT / BLOCK7_REL)["manifest_sha256"] == (
        EXPECTED_BLOCK7_MANIFEST_SHA256
    )
    chain = _read("sprint54_chain_of_custody.json")
    assert chain["status"] == "PASS_COMPLETE_CHAIN_OF_CUSTODY"
    assert chain["stage_count"] == 10
    assert chain["all_links_present"] is True
    assert chain["all_hashes_verified"] is True
    assert all(stage["artifact_exists"] for stage in chain["stages"])
    assert all(not stage["changed_predictive_evidence"] for stage in chain["stages"])
    assert (
        sum(stage["predictive_access_occurred_at_stage"] for stage in chain["stages"])
        == 1
    )


def test_final_classifications_and_access_state_remain_frozen():
    state = _read("sprint54_final_scientific_state.json")
    assert state["closure_classification"] == FINAL_CLASSIFICATION
    assert state["scientific_classification"] == MIXED
    assert state["block6_classification"] == BLOCK6_CLASSIFICATION
    assert state["block7_classification"] == BLOCK7_CLASSIFICATION
    integrity = _read("sprint54_integrity_closure.json")
    assert integrity["t1_predictive_access_count"] == 1
    assert integrity["predictive_scoring_count"] == 1
    assert integrity["t1_rerun_permitted"] is False
    assert integrity["t2_predictive_access_count"] == 0
    assert integrity["t2_state"] == "DENY_SEALED_REVIEWER_RESERVE"
    assert integrity["xai_execution_count"] == 0
    assert integrity["sealed_predictive_or_scientific_artifact_changed"] is False


def test_final_execution_snapshot_and_descriptive_values_are_exact():
    snapshot = _read("sprint54_final_result_snapshot.json")
    execution = snapshot["execution"]
    assert execution == {
        "execution_identifier": (
            "9fb5e4f7b43c7f5be7092632c4d471594aa28eeefa22cac4aa4a7e15355d7260"
        ),
        "t1_identities": 3787,
        "positive": 1046,
        "negative": 2741,
        "prevalence": 0.276208,
        "evidence_rows": 106036,
        "scopes": 28,
        "project_scopes": 392,
        "duplicate_rows": 0,
        "missing_predictions": 0,
        "missing_probabilities": 0,
        "out_of_range_probabilities": 0,
        "t2_contamination": 0,
        "train_validation_overlap": 0,
        "leakage_contract_violations": 0,
    }
    assert [
        row["value"] for row in snapshot["descriptive_pr_auc_no_post_t1_selection"]
    ] == [0.6584414158428827, 0.6785419992551178, 0.6888303122451366]


def test_statistics_calibration_and_near_perfect_snapshot_are_exact():
    snapshot = _read("sprint54_final_result_snapshot.json")
    statistics = snapshot["statistics"]
    assert statistics["friedman_omnibus_rows"] == 32
    assert statistics["paired_two_sided_wilcoxon_rows"] == 384
    assert statistics["holm_families"] == 64
    assert statistics["alpha"] == 0.05
    assert statistics["result_state_counts"] == {
        "SIGNIFICANT_FAVORS_PROPOSAL": 137,
        "NON_SIGNIFICANT": 246,
        "SIGNIFICANT_FAVORS_COMPARATOR": 1,
        "INSUFFICIENT_SUPPORT": 0,
    }
    calibration = snapshot["calibration"]
    assert calibration["RAW_project_scopes"] == 378
    assert calibration["ISOTONIC_project_scopes"] == 14
    assert calibration["ISOTONIC_scope"] == "LightGBM + PROCESS"
    assert calibration["t1_calibration_fit_or_selection"] is False
    near = snapshot["near_perfect_audit"]
    assert near["trigger_count"] == 62
    assert near["taxonomy_counts"] == {
        "EXPLAINABLE_BY_CLASS_SUPPORT_OR_THRESHOLD_BEHAVIOR": 32,
        "EXTREME_BUT_INTEGRITY_SUPPORTED": 30,
        "INSUFFICIENT_SUPPORT_FOR_INTERPRETATION": 0,
        "INTEGRITY_CONCERN_REQUIRES_ESCALATION": 0,
    }
    assert near["values_changed"] is False


def test_framework_consistency_keeps_xai_and_qa_downstream():
    framework = _read("sprint54_framework_consistency.json")
    assert framework["status"] == ("PASS_CONSISTENT_WITH_FROZEN_MMSDP_XAI_PIPELINE")
    assert framework["distinct_modalities"] == ["CODE", "PROCESS", "TEXT"]
    assert framework["independently_learned_base_modalities"] is True
    assert framework["fusion_architecture"] == ("DECISION_LEVEL_STACKING_LATE_FUSION")
    assert framework["raw_feature_concatenation"] is False
    assert framework["simple_probability_averaging"] is False
    assert framework["voting"] is False
    assert framework["post_t1_meta_learner_fitting"] is False
    assert framework["xai_state"] == "DEFERRED_NOT_EXECUTED"
    assert framework["qa_role_explanation_claimed"] is False


def test_reviewer_traceability_retains_adverse_and_bounded_interpretation():
    reviewer = _read("sprint54_reviewer_traceability_final_check.json")
    assert reviewer["status"] == "PASS_14_OF_14_CONCERNS_TRACEABLE"
    assert reviewer["concern_count"] == 14
    assert reviewer["partially_addressed_labeled_fully_resolved"] is False
    assert reviewer["limitations_hidden"] is False
    assert reviewer["adverse_random_forest_visible"] is True
    assert set(reviewer["adverse_random_forest_directions"]) == {
        "BEST_PAIRWISE::Random Forest::MCC",
        "BEST_PAIRWISE::Random Forest::PR_AUC",
        "BEST_UNIMODAL::Random Forest::MCC",
    }
    assert reviewer["near_perfect_categories_presented_as_causal"] is False
    assert reviewer["significance_equated_with_practical_significance"] is False
    assert reviewer["non_significance_interpreted_as_equivalence"] is False


def test_claim_and_limitation_freeze_is_exact():
    frozen = _read("sprint54_claim_and_limitation_freeze.json")
    assert frozen["claim_status_counts"] == {
        "SUPPORTED": 2,
        "SUPPORTED_WITH_LIMITATION": 2,
        "MIXED": 1,
        "NOT_SUPPORTED": 5,
        "DEFERRED": 2,
    }
    assert frozen["limitation_count"] == 9
    assert len(frozen["limitations"]) == 9
    assert len(frozen["prohibited_overclaims"]) == 7
    assert frozen["stronger_claims_added_in_block8"] is False


def test_future_boundary_and_human_report_are_complete():
    boundary = _read("sprint54_future_action_boundary.json")
    prohibited = " ".join(boundary["not_permitted_without_new_prospective_sprint"])
    for term in ("T1 rerun", "threshold", "calibration", "T2 access", "XAI"):
        assert term in prohibited
    report = (PACKAGE / "FINAL_SPRINT54_HUMAN_REVIEW_REPORT.md").read_text()
    required_sections = [
        "Scope",
        "Prospective protocol",
        "One-shot T1 execution",
        "Execution integrity",
        "Predictive findings",
        "Multimodal findings",
        "Statistical evidence",
        "Calibration evidence",
        "Near-perfect-result audit",
        "Scientific classification",
        "Reviewer traceability",
        "Limitations",
        "T2 reserve state",
        "XAI state",
        "Permitted future work",
        "Prohibited post-T1 actions",
        "Human acceptance checklist",
    ]
    assert all(
        f"## {index}. {title}" in report
        for index, title in enumerate(required_sections, 1)
    )
