import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BLOCK7 = ROOT / "audits/q1-xai-reconstruction-execution/1.0.0"
PACKAGE = BLOCK7 / "forensics/g3_failure_root_cause/1.0.0"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json(name: str):
    return json.loads((PACKAGE / name).read_text())


def test_forensic_manifest_verifies_without_modifying_block7_manifest():
    entries = []
    for line in (PACKAGE / "MANIFEST.sha256").read_text().splitlines():
        sha256, name = line.split("  ", 1)
        entries.append(name)
        assert _sha256(PACKAGE / name) == sha256
    assert entries == [
        "G3_FAILURE_FORENSIC_REPORT.md",
        "g3_downstream_propagation.json",
        "g3_recovery_relationship.json",
        "g3_root_cause_analysis.json",
        "g3_three_way_state_diff.json",
    ]
    assert _sha256(BLOCK7 / "MANIFEST.sha256") == (
        "994a6f7aa8d1393904c605e0b5d65db6fcd39b9be55a1eb5219f899346b83d2e"
    )
    assert _sha256(BLOCK7 / "g1_g2_g3_results.json") == (
        "c07a0bd18d1c73e2cddae0ca829de3dd9e698b233d5d27f3f3f8928fb153f8a5"
    )


def test_root_classification_preserves_g3_and_counts_propagation_once():
    analysis = _json("g3_root_cause_analysis.json")
    assert analysis["block7_outcome_preserved"] == (
        "RECONSTRUCTION_NONDETERMINISTIC_STOP"
    )
    assert analysis["g3_counts_preserved"] == {
        "G3_PASS_DETERMINISTIC": 1732,
        "G3_FAIL_NONDETERMINISTIC": 4,
    }
    assert analysis["RAW_FAILED_LOGICAL_UNIT_COUNT"] == 4
    assert analysis["INDEPENDENT_ROOT_FAILURE_COUNT"] == 1
    assert analysis["DOWNSTREAM_PROPAGATED_FAILURE_COUNT"] == 3
    assert analysis["root_cause_classification"] == ("TRUE_FITTED_MODEL_NONDETERMINISM")
    assert analysis["first_semantic_difference"]["field"] == (
        "canonical_state.model.coef"
    )
    assert analysis["input_integrity_classification"] == "INPUT_IDENTICAL"

    frozen = json.loads((BLOCK7 / "g1_g2_g3_results.json").read_text())
    failures = {
        row["logical_id"]
        for row in frozen["g3_results"]
        if row["result"] == "G3_FAIL_NONDETERMINISTIC"
    }
    assert failures == {
        "apache/zeppelin|Logistic Regression|OOF|T|block=2",
        "apache/zeppelin|Logistic Regression|FUSION_META|C+T",
        "apache/zeppelin|Logistic Regression|FUSION_META|P+T",
        "apache/zeppelin|Logistic Regression|FUSION_META|C+P+T",
    }


def test_tfidf_is_exact_and_lr_semantic_state_is_first_difference():
    state = _json("g3_three_way_state_diff.json")
    common = state["identical_across_repetitions"]
    assert common["vocabulary_membership"] is True
    assert common["token_to_column_assignment"] is True
    assert common["feature_order"] is True
    assert common["idf_values"] is True
    assert common["feature_count"] == 90
    assert common["n_iter"] == [4]
    assert state["first_semantic_difference"] == "model.coef"
    diagnostics = state["rep_01_vs_rep_02_numeric_diagnostics"]
    assert diagnostics["coef"]["differing_elements"] == 78
    assert diagnostics["intercept"]["differing_elements"] == 1
    assert diagnostics["check_output"]["differing_elements"] == 47
    assert state["rep_01_vs_rep_03"] == ("EXACT_SEMANTIC_STATE_AND_CHECK_OUTPUT_MATCH")


def test_three_fusion_failures_are_root_propagation_with_exact_controls():
    propagation = _json("g3_downstream_propagation.json")
    matrix = propagation["oof_training_matrix"]["rep_01_vs_rep_02"]
    assert matrix["C"]["exact_equal"] is True
    assert matrix["P"]["exact_equal"] is True
    assert matrix["T"]["differing_elements"] == 47
    assert all(
        row["classification"] == "PROPAGATED_FROM_ROOT_TEXT_OOF"
        and row["independent_fusion_nondeterminism_evidence"] is False
        for row in propagation["downstream_units"].values()
    )
    assert propagation["negative_control"] == {
        "logical_id": "apache/zeppelin|Logistic Regression|FUSION_META|C+P",
        "contains_text_column": False,
        "canonical_state_exact_equal_across_repetitions": True,
        "check_output_exact_equal_across_repetitions": True,
        "g3_result": "G3_PASS_DETERMINISTIC",
    }


def test_recovery_is_not_boundary_associated_and_governance_is_unchanged():
    recovery = _json("g3_recovery_relationship.json")
    assert recovery["classification"] == "RECOVERY_UNRELATED_BY_EVIDENCE"
    assert recovery["root_reconstructed_after_recovery"] is True
    assert recovery["root_was_first_resumed_component"] is False
    assert recovery["completed_units_between_resume_point_and_root"] == 829

    governance = _json("g3_root_cause_analysis.json")["governance"]
    assert governance == {
        "t1_original_predictive_access_count": 1,
        "t1_original_predictive_scoring_count": 1,
        "t1_rerun": False,
        "block7_t1_new_model_queries": 0,
        "t2_access_count": 0,
        "t2_state": "DENY_SEALED_REVIEWER_RESERVE",
        "g4_execution_count": 0,
        "g5_execution_count": 0,
        "xai_execution_count": 0,
        "reconstruction_or_refit_during_forensics": 0,
    }
    assert _json("g3_root_cause_analysis.json")["prohibited_operations_executed"] == []
