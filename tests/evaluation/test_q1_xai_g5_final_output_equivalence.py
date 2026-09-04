import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path

from experimentation.q1_controlled_train_validation_baselines import digest


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "audits/q1-xai-final-output-equivalence-g5/1.0.0"
G4 = ROOT / "audits/q1-xai-reconstruction-equivalence-g4/1.0.0"
BLOCK7 = ROOT / "audits/q1-xai-reconstruction-execution/1.0.0"
BLOCK7B = BLOCK7 / "dispositions/block7b_partial_eligibility/1.0.0"
G4_PASS = "G4_PASS_ROW_LEVEL_RAW_EQUIVALENCE"
G5_PASS = "G5_PASS_FINAL_OUTPUT_EQUIVALENCE"
EXCLUDED = {
    ("apache/zeppelin", "Logistic Regression", "C+T"),
    ("apache/zeppelin", "Logistic Regression", "P+T"),
    ("apache/zeppelin", "Logistic Regression", "C+P+T"),
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json(name: str):
    return json.loads((PACKAGE / name).read_text())


def _jsonl(name: str):
    return [json.loads(line) for line in (PACKAGE / name).read_text().splitlines()]


def test_exact_g4_pass_universe_is_the_only_g5_universe():
    g4 = _jsonl_from(G4 / "g4_scope_results.jsonl")
    g5 = _jsonl("g5_scope_results.jsonl")
    assert len(g4) == len(g5) == 389
    assert all(row["G4_outcome"] == G4_PASS for row in g4)
    assert {row["model_identity_sha256"] for row in g4} == {
        row["model_identity_sha256"] for row in g5
    }
    assert all(row["G4_outcome"] == G4_PASS for row in g5)
    assert not {(row["project"], row["algorithm"], row["configuration"]) for row in g5} & EXCLUDED


def _jsonl_from(path: Path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_all_final_outputs_and_decisions_pass_exact_row_level_equivalence():
    rows = _jsonl("g5_scope_results.jsonl")
    assert all(row["G5_outcome"] == G5_PASS for row in rows)
    assert all(row["row_alignment_status"] == "EXACT_IDENTITY_AND_ORDER" for row in rows)
    assert all(row["max_absolute_error"] == 0.0 for row in rows)
    assert all(row["max_relative_error_where_defined"] == 0.0 for row in rows)
    assert all(row["rows_with_absolute_bound_violation"] == 0 for row in rows)
    assert all(row["rows_with_relative_bound_violation"] == 0 for row in rows)
    assert all(row["nan_or_infinite_count"] == 0 for row in rows)
    assert all(row["decision_mismatch_count"] == 0 for row in rows)
    assert all(row["frozen_threshold"] == 0.5 for row in rows)
    assert all(row["reconstructed_final_probability_digest"] == row["frozen_final_probability_digest"] for row in rows)
    assert sum(row["row_final_probability_comparison_count"] for row in rows) == 105862


def test_raw_and_isotonic_mappings_are_exactly_the_frozen_distribution():
    rows = _jsonl("g5_scope_results.jsonl")
    assert Counter(row["frozen_calibration_state"] for row in rows) == Counter({"RAW": 375, "ISOTONIC": 14})
    assert all(
        row["calibration_mapping_status"] == "RAW_IDENTITY_MAPPING_EXACT"
        and row["raw_probability_digest"] == row["reconstructed_final_probability_digest"]
        for row in rows if row["frozen_calibration_state"] == "RAW"
    )
    isotonic = [row for row in rows if row["frozen_calibration_state"] == "ISOTONIC"]
    assert len(isotonic) == 14
    assert all(
        row["algorithm"] == "LightGBM" and row["configuration"] == "P"
        and row["calibration_mapping_status"] == "PERSISTED_ISOTONIC_MAPPING_APPLIED_NO_REFIT"
        for row in isotonic
    )


def test_isotonic_state_digests_match_persisted_source_and_block7_linkage():
    states = {}
    path = ROOT / "audits/q1-development-only-calibration/1.0.0/calibrator_states.jsonl.gz"
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            if row["algorithm"] == "LightGBM" and row["configuration"] == "P" and row["method"] == "ISOTONIC" and row["evaluation_origin"] == 11:
                states[row["project"]] = row
    linkage = json.loads((BLOCK7 / "calibration_linkage.json").read_text())
    linked = {row["project"]: row for row in linkage["states"]}
    registry = _json("calibration_state_registry.json")["isotonic"]["states"]
    assert len(states) == len(registry) == 14
    for record in registry:
        state = states[record["project"]]
        assert record["calibration_state_digest"] == digest(state)
        assert record["calibration_state_digest"] == linked[record["project"]]["state_sha256"]
        assert record["fit_membership_digest"] == linked[record["project"]]["fit_membership_digest"]


def test_future_xai_readiness_is_strictly_g1_through_g5_and_state_derived():
    readiness = _jsonl("xai_readiness_ledger.jsonl")
    g5 = {row["model_identity_sha256"]: row for row in _jsonl("g5_scope_results.jsonl")}
    block7b = {
        row["model_identity_sha256"]: row
        for row in _jsonl_from(BLOCK7B / "scope_g1_g3_eligibility.jsonl")
    }
    assert len(readiness) == 389
    assert all(row["G5_outcome"] == G5_PASS for row in readiness)
    assert all(row["method_specific_state_available"] is True for row in readiness)
    assert all(row["future_xai_readiness"] == "FUTURE_PRIMARY_XAI_STATE_READY_PENDING_SEPARATE_RUNTIME_AND_EXECUTION_AUTHORIZATION" for row in readiness)
    assert all(row["xai_executed"] is False for row in readiness)
    for row in readiness:
        identity = row["model_identity_sha256"]
        assert g5[identity]["G5_outcome"] == G5_PASS
        assert block7b[identity]["eligibility_outcome"] == "G1_G3_ELIGIBLE_FOR_FUTURE_G4_REVIEW"


def test_method_mapping_and_text_alignment_are_complete():
    readiness = _jsonl("xai_readiness_ledger.jsonl")
    methods = Counter(row["future_primary_method"] for row in readiness)
    assert methods == Counter({
        "ANALYTICAL_LR_FUSION_DECOMPOSITION": 221,
        "EXACT_TREESHAP_NATIVE_RAW_MARGIN": 84,
        "ANALYTICAL_LINEAR_LOGIT_DECOMPOSITION": 42,
        "EXACT_TREESHAP_POSITIVE_CLASS_OUTPUT": 42,
    })
    text = [row for row in readiness if "T" in row["configuration"].split("+")]
    assert len(text) == 221
    assert all(row["text_feature_attribution_state"] == "TEXT_FEATURE_ATTRIBUTION_STATE_READY" for row in text)
    assert all(row["text_state_evidence"]["predictor_alignment"] is True for row in text)
    assert all(row["text_state_evidence"]["representation_object_bytes_verified"] is True for row in text)
    assert all(row["text_state_evidence"]["vocabulary_idf_token_column_feature_order_verified"] is True for row in text)
    assert all(row["text_state_evidence"][key] for row in text for key in (
        "text_representation_sha256", "vocabulary_sha256", "idf_sha256", "feature_order_sha256"
    ))


def test_xai_method_policy_freezes_e1_e2_e3_and_lime_exclusion_without_execution():
    policy = _json("xai_method_policy_freeze.json")
    assert policy["execution_in_g5"] is False
    assert policy["E1_unimodal"] == {
        "Logistic Regression": "ANALYTICAL_LINEAR_LOGIT_DECOMPOSITION",
        "Random Forest": "EXACT_TREESHAP_POSITIVE_CLASS_OUTPUT",
        "XGBoost": "EXACT_TREESHAP_NATIVE_RAW_MARGIN",
        "LightGBM": "EXACT_TREESHAP_NATIVE_RAW_MARGIN",
    }
    assert policy["E2_multimodal"]["values_calculated_in_g5"] is False
    assert policy["E3_calibration"]["RAW"] == "E3_IDENTITY_MAPPING_READY"
    assert policy["E3_calibration"]["ISOTONIC"] == "E3_FROZEN_MAPPING_INSPECTION_READY"
    assert policy["LIME_PRIMARY_STATUS"] == "EXCLUDED_FROM_PRIMARY_XAI"


def test_shap_runtime_is_metadata_only_and_requires_future_freeze():
    runtime = _json("shap_runtime_readiness.json")
    assert runtime["inspection_method"] == "IMPORTLIB_METADATA_ONLY_NO_SHAP_IMPORT"
    assert runtime["shap"] == {"installed": False, "observed_version_without_import": None}
    assert runtime["lime"] == {"installed": False, "observed_version_without_import": None}
    assert runtime["shap_execution_count"] == 0
    assert runtime["explainer_import_count"] == 0
    assert runtime["status"] == "RUNTIME_FREEZE_REQUIRED_BEFORE_PRIMARY_XAI"


def test_no_fit_metric_threshold_t2_or_xai_execution_path_exists():
    source = (ROOT / "src/evaluation/q1_xai_g5_final_output_equivalence.py").read_text()
    assert ".fit(" not in source
    assert "fit_unimodal" not in source
    assert "sklearn.metrics" not in source
    assert "roc_auc" not in source.lower()
    assert "average_precision" not in source.lower()
    assert "confusion_matrix" not in source
    assert "import shap" not in source.lower()
    assert "import lime" not in source.lower()
    assert "T2_REL" not in source
    ledger = _json("g5_governance_ledger.json")
    assert ledger["G5_T1_feature_access_count"] == 0
    assert ledger["G5_reconstructed_model_query_count"] == 0
    assert ledger["T2_access_count"] == 0
    assert ledger["XAI_execution_count"] == 0
    assert ledger["SHAP_execution_count"] == 0
    assert ledger["LIME_execution_count"] == 0
    assert ledger["analytical_attribution_execution_count"] == 0
    assert ledger["refit_count"] == ledger["reconstruction_count"] == ledger["recalibration_count"] == 0
    assert ledger["metric_recomputation_count"] == ledger["threshold_optimization_count"] == 0


def test_parent_hashes_tolerances_and_calibrators_remain_unchanged():
    expected = {
        ROOT / "audits/q1-t1-confirmatory-execution/1.0.0/results/t1_prediction_evidence.jsonl.gz": "eb4b6956b185e63cd322d92b8cdf96f53fcb09ef83b6a16f2334d660c6f5adc8",
        ROOT / "audits/q1-t1-confirmatory-execution/1.0.0/MANIFEST.sha256": "f4f910a5144241b53f7f741ab2e49a5cb541abd8cff88f72c7a05ee30ecaeedf",
        ROOT / "audits/q1-xai-reconstruction-equivalence-protocol/1.0.0/MANIFEST.sha256": "17341b4a585baab73118f21cc1056914326b61cba6751b16ff91bdf4b3dfc386",
        ROOT / "audits/q1-xai-reconstruction-equivalence-protocol/1.0.0/amendments/historical_design_rationale/1.0.0/MANIFEST.sha256": "c9502cb1ec85d3053b8a972d61657038e66d04fb5e619b0fe08ed94d581c91bb",
        BLOCK7 / "MANIFEST.sha256": "994a6f7aa8d1393904c605e0b5d65db6fcd39b9be55a1eb5219f899346b83d2e",
        BLOCK7 / "g1_g2_g3_results.json": "c07a0bd18d1c73e2cddae0ca829de3dd9e698b233d5d27f3f3f8928fb153f8a5",
        BLOCK7 / "forensics/g3_failure_root_cause/1.0.0/MANIFEST.sha256": "a6f4bd5e5ec43f844860283aef6b3f21933728a5d0817773e7cb1fb742b866e7",
        BLOCK7B / "MANIFEST.sha256": "6e74700b5deeafb4e70d4e46a07a920df37372aa1f52fd1d17b26d3a7a2fdbeb",
        G4 / "MANIFEST.sha256": "158f52c8cd16e633d11202a86dff467d33838e84617aeaf64d94c361a66f3074",
        G4 / "g4_scope_results.jsonl": "0320dcdf3eb73b5b242a4223292c9708074e6e24f33f4757a9ebe582a9e9d5c1",
        ROOT / "audits/q1-xai-reconstruction-equivalence-protocol/1.0.0/numerical_tolerance_policy.json": "62fd3780c94c6a69bfc036bdd4b567409ffc46c8c892a807b221f5d40d0eb336",
        ROOT / "audits/q1-heldout-governance-calibration-freeze/1.0.0/frozen_calibration_policy.json": "b1fcce1e0dc5178ecf0606ddba3263add308db0da959c58a5addc136ebcefc25",
        ROOT / "audits/q1-development-only-calibration/1.0.0/calibrator_states.jsonl.gz": "5708a6e2ca35d54e8fdc6cf0bbd23bc5e72be66d22400be97de152ee183dcbe3",
    }
    assert all(_sha256(path) == value for path, value in expected.items())


def test_summary_claim_boundaries_and_manifest_are_complete():
    summary = _json("g5_summary.json")
    assert summary["g5_outcome"] == "FULL_G5_FINAL_OUTPUT_EQUIVALENCE_XAI_READINESS_ESTABLISHED"
    assert summary["counts"] == {
        "authorized": 389, "pass": 389, "fail_calibration": 0,
        "fail_final_output": 0, "ineligible_upstream": 0, "unresolved": 0,
    }
    claims = _json("xai_claim_boundaries.json")
    assert "causal effects" in claims["prohibited_claims"]
    entries = []
    for line in (PACKAGE / "MANIFEST.sha256").read_text().splitlines():
        value, name = line.split("  ", 1)
        entries.append(name)
        assert _sha256(PACKAGE / name) == value
    assert entries == sorted(entries)
    assert set(entries) == {
        "G5_FINAL_OUTPUT_EQUIVALENCE_REPORT.md", "calibration_state_registry.json",
        "final_output_alignment.json", "g5_governance_ledger.json",
        "g5_scope_results.jsonl", "g5_summary.json", "shap_runtime_readiness.json",
        "xai_claim_boundaries.json", "xai_method_policy_freeze.json",
        "xai_readiness_ledger.jsonl",
    }
