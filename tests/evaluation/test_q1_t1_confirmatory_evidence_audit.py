from pathlib import Path

from evaluation.q1_t1_confirmatory_evidence_audit import AUDIT_REL
from evaluation.q1_t1_confirmatory_execution import load_json, verify_manifest

ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / AUDIT_REL


def test_block6_manifest_and_overall_audit_are_complete():
    assert verify_manifest(AUDIT)["entry_count"] == 7
    result = load_json(AUDIT / "confirmatory_evidence_audit.json")
    assert result["audit_classification"] == (
        "PASS_CONFIRMATORY_EVIDENCE_INTERNALLY_CONSISTENT_REPORTABLE_MIXED"
    )
    assert result["execution_integrity_status"] == "PASS"
    assert result["result_reconciliation_status"] == "PASS_EXACT_RECONCILIATION"
    assert result["scientific_classification"] == "MIXED_CONFIRMATORY_EVIDENCE"
    assert result["new_integrity_concerns"] == []
    assert result["evidence_or_metrics_changed"] is False


def test_access_counters_remain_post_execution_exact():
    result = load_json(AUDIT / "confirmatory_evidence_audit.json")
    assert result["t1_predictive_access_count"] == 1
    assert result["predictive_scoring_count"] == 1
    assert result["t2_predictive_access_count"] == 0
    assert result["xai_execution_count"] == 0
    assert result["t1_rerun_permitted"] is False
    assert result["t2_access_state"] == "DENY_SEALED_REVIEWER_RESERVE"


def test_all_near_perfect_triggers_are_audited_without_escalation():
    result = load_json(AUDIT / "near_perfect_result_audit.json")
    assert result["status"] == "PASS_ALL_TRIGGERS_AUDITED_VALUES_UNCHANGED"
    assert result["trigger_count"] == 62
    assert result["taxonomy_counts"] == {
        "EXPLAINABLE_BY_CLASS_SUPPORT_OR_THRESHOLD_BEHAVIOR": 32,
        "EXTREME_BUT_INTEGRITY_SUPPORTED": 30,
    }
    assert result["integrity_concern_count"] == 0
    assert all(row["value_preserved_unchanged"] for row in result["records"])


def test_statistical_and_calibration_audits_match_frozen_counts():
    statistical = load_json(AUDIT / "statistical_evidence_audit.json")
    assert statistical["status"] == "PASS"
    assert statistical["friedman_omnibus_rows"] == 32
    assert statistical["paired_two_sided_wilcoxon_rows"] == 384
    assert statistical["holm_families"] == 64
    assert statistical["alpha"] == 0.05
    assert statistical["result_state_counts"] == {
        "NON_SIGNIFICANT": 246,
        "SIGNIFICANT_FAVORS_COMPARATOR": 1,
        "SIGNIFICANT_FAVORS_PROPOSAL": 137,
    }
    calibration = load_json(AUDIT / "calibration_evidence_audit.json")
    assert calibration["status"] == "PASS"
    assert calibration["project_scope_counts"] == {"RAW": 378, "ISOTONIC": 14}
    assert calibration["isotonic_scope"] == "LightGBM + PROCESS"
    assert calibration["t1_calibration_fit_or_selection"] is False


def test_multimodal_contract_remains_frozen_after_t1():
    result = load_json(AUDIT / "multimodal_fusion_audit.json")
    assert result["status"] == "PASS"
    assert result["architecture"] == "DECISION_LEVEL_STACKING_LATE_FUSION"
    assert result["independently_learned_base_modalities"] is True
    assert result["raw_feature_concatenation"] is False
    assert result["simple_averaging"] is False
    assert result["voting"] is False
    assert result["post_t1_meta_learner_fitting"] is False
    assert result["semantically_distinct_modalities"] == ["CODE", "PROCESS", "TEXT"]
