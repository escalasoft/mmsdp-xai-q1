from pathlib import Path

from evaluation.q1_t1_confirmatory_execution import load_json, verify_manifest
from evaluation.q1_t1_reporting_traceability_freeze import (
    BLOCK6_CLASSIFICATION,
    BLOCK7_REL,
    EXPECTED_BLOCK6_MANIFEST_SHA256,
    EXPECTED_EVIDENCE_SHA256,
    EXPECTED_RESULTS_MANIFEST_SHA256,
    MIXED,
)

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / BLOCK7_REL


def _read(name: str):
    return load_json(PACKAGE / name)


def test_block7_manifest_and_sealed_reference_registry_are_exact():
    manifest = verify_manifest(PACKAGE)
    assert manifest["entry_count"] == 7
    registry = _read("sealed_reference_registry.json")
    assert registry["results_manifest_sha256"] == EXPECTED_RESULTS_MANIFEST_SHA256
    assert registry["block6_manifest_sha256"] == EXPECTED_BLOCK6_MANIFEST_SHA256
    assert registry["t1_evidence_sha256"] == EXPECTED_EVIDENCE_SHA256
    assert registry["scientific_classification"] == MIXED
    assert registry["block6_classification"] == BLOCK6_CLASSIFICATION
    assert registry["sealed_inputs_modified"] is False


def test_access_state_and_classifications_remain_frozen():
    registry = _read("sealed_reference_registry.json")
    assert registry["t1_predictive_access_count"] == 1
    assert registry["predictive_scoring_count"] == 1
    assert registry["t2_predictive_access_count"] == 0
    assert registry["xai_execution_count"] == 0
    assert registry["t1_rerun_permitted"] is False
    contract = _read("scientific_reporting_contract.json")
    assert contract["classification"] == MIXED
    assert contract["block6_classification"] == BLOCK6_CLASSIFICATION


def test_reporting_contract_preserves_frozen_results_and_audits():
    contract = _read("scientific_reporting_contract.json")
    assert [
        row["value"]
        for row in contract["descriptive_results_only_no_post_t1_selection"]
    ] == [
        0.6584414158428827,
        0.6785419992551178,
        0.6888303122451366,
    ]
    statistical = contract["statistical_reporting"]
    assert statistical["friedman_omnibus_rows"] == 32
    assert statistical["paired_two_sided_wilcoxon_rows"] == 384
    assert statistical["holm_families"] == 64
    assert statistical["alpha"] == 0.05
    assert statistical["result_state_counts"] == {
        "SIGNIFICANT_FAVORS_PROPOSAL": 137,
        "NON_SIGNIFICANT": 246,
        "SIGNIFICANT_FAVORS_COMPARATOR": 1,
        "INSUFFICIENT_SUPPORT": 0,
    }
    calibration = contract["calibration_reporting"]
    assert calibration["RAW_project_scopes"] == 378
    assert calibration["ISOTONIC_project_scopes"] == 14
    assert calibration["ISOTONIC_scope"] == "LightGBM + PROCESS"
    assert calibration["t1_calibration_fit_or_selection"] is False


def test_near_perfect_and_adverse_random_forest_evidence_remain_visible():
    contract = _read("scientific_reporting_contract.json")
    near = contract["near_perfect_reporting"]
    assert near["trigger_count"] == 62
    assert near["taxonomy_counts"] == {
        "EXPLAINABLE_BY_CLASS_SUPPORT_OR_THRESHOLD_BEHAVIOR": 32,
        "EXTREME_BUT_INTEGRITY_SUPPORTED": 30,
        "INSUFFICIENT_SUPPORT_FOR_INTERPRETATION": 0,
        "INTEGRITY_CONCERN_REQUIRES_ESCALATION": 0,
    }
    assert near["values_changed"] is False
    assert near["taxonomy_semantics"] == (
        "INTEGRITY_AUDIT_CATEGORIES_NOT_CAUSAL_EXPLANATIONS_OF_EXTREMENESS"
    )
    assert set(contract["adverse_random_forest_primary_directions"]) == {
        "BEST_PAIRWISE::Random Forest::MCC",
        "BEST_PAIRWISE::Random Forest::PR_AUC",
        "BEST_UNIMODAL::Random Forest::MCC",
    }


def test_reviewer_traceability_covers_every_required_concern():
    matrix = _read("reviewer_traceability_matrix.json")
    assert matrix["concern_count"] == 14
    required_fields = {
        "reviewer_concern",
        "governing_contract_or_artifact",
        "evidence_status",
        "scientific_interpretation",
        "remaining_limitation",
        "manuscript_safe_claim",
        "prohibited_overclaim",
    }
    assert all(required_fields <= row.keys() for row in matrix["concerns"])
    assert all("RESOLVED" not in row["evidence_status"] for row in matrix["concerns"])
    assert {row["reviewer_concern"] for row in matrix["concerns"]} == {
        "leakage / target proxy risk",
        "implausibly high or perfect metrics",
        "temporal evaluation",
        "unimodal baselines",
        "pairwise modality combinations",
        "full multimodal fusion",
        "fusion architecture",
        "calibration",
        "statistical comparison",
        "reproducibility / provenance",
        "benchmark label semantics",
        "external generalization",
        "T2 reserve",
        "XAI status",
    }


def test_claim_ledger_and_limitations_are_complete_and_bounded():
    ledger = _read("manuscript_claim_ledger.json")
    assert ledger["status_counts"] == {
        "SUPPORTED": 2,
        "SUPPORTED_WITH_LIMITATION": 2,
        "MIXED": 1,
        "NOT_SUPPORTED": 5,
        "DEFERRED": 2,
    }
    assert all(
        row["evidence_status"] in ledger["allowed_statuses"] for row in ledger["claims"]
    )
    assert all(row["evidence_references"] for row in ledger["claims"])
    prohibited = " ".join(ledger["prohibited_overclaims"])
    for fragment in (
        "universally outperforms unimodal models",
        "superior for all algorithms",
        "near-perfect results prove exceptional",
        "verified-clean ground truth",
        "generalize to all software projects",
        "T2 confirms",
        "XAI explains",
    ):
        assert fragment in prohibited

    limitations = _read("limitations_ledger.json")
    assert limitations["limitation_count"] == 9
    text = " ".join(row["limitation"] for row in limitations["limitations"])
    for fragment in (
        "Benchmark-defined",
        "Apache benchmark family",
        "limited power",
        "PR-AUC-selected comparators",
        "ECE",
        "not causal",
        "T2 has not been accessed",
        "XAI has not been executed",
        "not a causal explanation",
    ):
        assert fragment in text


def test_reviewer_summary_separates_result_interpretation_and_limitation():
    summary = _read("reviewer_facing_summary.json")
    assert summary["classification"] == MIXED
    assert summary["adverse_random_forest_hidden"] is False
    assert summary["non_significance_interpreted_as_equivalence"] is False
    assert summary["statistical_significance_interpreted_as_practical"] is False
    assert summary["promotional_language"] is False
    assert all(
        {"RESULT", "INTERPRETATION", "LIMITATION"} <= entry.keys()
        for entry in summary["entries"]
    )
