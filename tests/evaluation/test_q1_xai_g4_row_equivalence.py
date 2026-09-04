import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "audits/q1-xai-reconstruction-equivalence-g4/1.0.0"
BLOCK7 = ROOT / "audits/q1-xai-reconstruction-execution/1.0.0"
BLOCK7B = BLOCK7 / "dispositions/block7b_partial_eligibility/1.0.0"
ELIGIBLE = "G1_G3_ELIGIBLE_FOR_FUTURE_G4_REVIEW"
PASS = "G4_PASS_ROW_LEVEL_RAW_EQUIVALENCE"
EXCLUDED = {
    ("apache/zeppelin", "Logistic Regression", "C+T"),
    ("apache/zeppelin", "Logistic Regression", "P+T"),
    ("apache/zeppelin", "Logistic Regression", "C+P+T"),
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json(name: str):
    return json.loads((PACKAGE / name).read_text())


def _results():
    return [json.loads(line) for line in (PACKAGE / "g4_scope_results.jsonl").read_text().splitlines()]


def test_frozen_universe_authorizes_exactly_389_and_excludes_exactly_three():
    ledger = [json.loads(line) for line in (BLOCK7B / "scope_g1_g3_eligibility.jsonl").read_text().splitlines()]
    authorized = [row for row in ledger if row["eligibility_outcome"] == ELIGIBLE]
    excluded = [row for row in ledger if row["eligibility_outcome"] != ELIGIBLE]
    assert len(ledger) == 392
    assert len({row["model_identity_sha256"] for row in ledger}) == 392
    assert len(authorized) == 389
    assert len(excluded) == 3
    assert {(row["project"], row["algorithm"], row["configuration"]) for row in excluded} == EXCLUDED


def test_representative_policy_was_frozen_before_query_and_is_non_performance_based():
    policy = _json("representative_reconstruction_policy.json")
    authorization = _json("g4_authorization_and_preflight.json")
    assert policy["status"] == "FROZEN_BEFORE_ANY_T1_FEATURE_ACCESS_OR_MODEL_QUERY"
    assert policy["representative_reconstruction"] == "rep_01"
    assert policy["selection_rule"] == (
        "ALWAYS_REP_01_IF_AND_ONLY_IF_ALL_SCOPE_G3_DEPENDENCIES_PASSED_EXACT_G3"
    )
    assert policy["refit_or_reconstruction"] is False
    assert authorization["representative_policy_sha256"] == _sha256(
        PACKAGE / "representative_reconstruction_policy.json"
    )
    assert authorization["status"] == "PRE_QUERY_AUTHORIZATION_FROZEN"
    assert authorization["tolerance"] == {
        "maximum_absolute_error": 1e-12,
        "maximum_relative_error": 1e-10,
        "relative_error_reference_minimum_absolute_value": 1e-8,
        "every_row_required": True,
        "nan_or_infinite": "FAIL",
        "row_identity_or_order_mismatch": "FAIL",
    }


def test_every_authorized_identity_has_one_row_level_result_and_exclusions_were_not_queried():
    results = _results()
    authorization = _json("g4_authorization_and_preflight.json")
    assert len(results) == 389
    assert len({row["model_identity_sha256"] for row in results}) == 389
    assert {row["model_identity_sha256"] for row in results} == set(
        authorization["authorized_model_identity_sha256"]
    )
    assert not {
        (row["project"], row["algorithm"], row["configuration"]) for row in results
    } & EXCLUDED
    graph = _json("g4_failure_dependency_graph.json")
    assert graph["excluded_scope_model_query_count"] == 0
    assert {
        (row["project"], row["algorithm"], row["configuration"])
        for row in graph["G3_excluded_scopes_not_queried"]
    } == EXCLUDED


def test_all_389_scopes_pass_exact_row_and_probability_alignment():
    results = _results()
    assert all(row["G4_outcome"] == PASS for row in results)
    assert all(row["representative_repetition"] == "rep_01" for row in results)
    assert all(row["row_alignment_status"] == "EXACT_IDENTITY_AND_ORDER" for row in results)
    assert all(row["frozen_reference_probability_digest"] == row["reconstructed_probability_digest"] for row in results)
    assert all(row["max_absolute_error"] == 0.0 for row in results)
    assert all(row["max_relative_error_where_defined"] == 0.0 for row in results)
    assert all(row["rows_with_absolute_bound_violation"] == 0 for row in results)
    assert all(row["rows_with_relative_bound_violation"] == 0 for row in results)
    assert all(row["nan_or_infinite_count"] == 0 for row in results)
    assert all(row["row_probability_comparison_count"] == row["T1_row_count"] for row in results)
    assert sum(row["row_probability_comparison_count"] for row in results) == 105862


def test_multimodal_results_require_passing_base_states_in_frozen_order():
    results = _results()
    expected_order = {
        "C+P": ["C", "P"],
        "C+T": ["C", "T"],
        "P+T": ["P", "T"],
        "C+P+T": ["C", "P", "T"],
    }
    for row in results:
        if "+" not in row["configuration"]:
            assert row["required_base_G4_states"] is None
            continue
        assert list(row["required_base_G4_states"]) == expected_order[row["configuration"]]
        assert set(row["required_base_G4_states"].values()) == {PASS}


def test_governance_uses_separate_technical_counters_and_preserves_prohibitions():
    ledger = _json("g4_governance_ledger.json")
    assert ledger["ledger_name"] == "RECONSTRUCTION_EQUIVALENCE_TECHNICAL_VERIFICATION_LEDGER"
    assert ledger["authorized_scope_count"] == 389
    assert ledger["excluded_scope_count"] == 3
    assert ledger["technical_t1_access_event_count"] == 3
    assert ledger["technical_t1_feature_access_event_count"] == 2
    assert ledger["technical_t1_identity_schema_diagnostic_access_count"] == 1
    assert ledger["technical_t1_feature_access_count"] == 3787
    assert ledger["technical_t1_feature_row_access_operation_count"] == 4032
    assert ledger["technical_reconstructed_model_query_count"] == 389
    assert ledger["row_probability_comparison_count"] == 105862
    assert ledger["historical_t1_predictive_access_count"] == 1
    assert ledger["historical_t1_predictive_scoring_count"] == 1
    assert ledger["historical_t1_rerun"] is False
    assert ledger["T2_access_count"] == 0
    assert ledger["T2_state"] == "DENY_SEALED_REVIEWER_RESERVE"
    assert ledger["G5_execution_count"] == 0
    assert ledger["XAI_execution_count"] == 0
    assert ledger["refit_count"] == 0
    assert ledger["reconstruction_count"] == 0
    assert ledger["metric_recomputation_count"] == 0
    assert ledger["excluded_scope_model_query_count"] == 0
    assert ledger["markers"] == ["NOT_CONFIRMATORY", "NO_MODEL_SELECTION", "NO_SCIENTIFIC_UPDATE"]


def test_operational_retry_is_disclosed_and_preceded_all_model_queries():
    recovery = _json("g4_operational_recovery.json")
    assert recovery["classification"] == "FAIL_CLOSED_PRE_QUERY_SCHEMA_DECLARATION_MISMATCH"
    assert recovery["scientific_failure"] is False
    assert recovery["representative_policy_changed"] is False
    assert recovery["tolerance_changed"] is False
    assert recovery["failed_attempt"]["authorized_t1_feature_rows_accessed"] == 245
    assert recovery["failed_attempt"]["reconstructed_model_query_count"] == 0
    assert recovery["failed_attempt"]["row_probability_comparison_count"] == 0
    assert recovery["correction"]["label_value_used_for_computation"] is False
    assert recovery["authorized_diagnostic"]["T1_identity_schema_access_count"] == 1
    assert recovery["authorized_diagnostic"]["content_retained"] == "FIELD_NAMES_ONLY"


def test_no_fit_reconstruction_metric_calibration_t2_or_xai_execution_path_exists():
    source = (ROOT / "src/evaluation/q1_xai_g4_row_equivalence.py").read_text()
    assert ".fit(" not in source
    assert "fit_unimodal" not in source
    assert "reconstruct_project_models" not in source
    assert "sklearn.metrics" not in source
    assert "roc_auc" not in source.lower()
    assert "average_precision" not in source.lower()
    assert "shap." not in source.lower()
    assert "lime." not in source.lower()
    assert "T2_REL" not in source
    assert "structural_memberships" not in source
    alignment = _json("g4_reference_alignment.json")
    assert alignment["aggregate_metric_substitution"] is False
    assert alignment["labels_used_for_computation"] is False


def test_all_parent_hashes_and_tolerance_remain_unchanged():
    expected = {
        ROOT / "audits/q1-t1-confirmatory-execution/1.0.0/results/t1_prediction_evidence.jsonl.gz": "eb4b6956b185e63cd322d92b8cdf96f53fcb09ef83b6a16f2334d660c6f5adc8",
        ROOT / "audits/q1-t1-confirmatory-execution/1.0.0/MANIFEST.sha256": "f4f910a5144241b53f7f741ab2e49a5cb541abd8cff88f72c7a05ee30ecaeedf",
        ROOT / "audits/q1-xai-reconstruction-equivalence-protocol/1.0.0/MANIFEST.sha256": "17341b4a585baab73118f21cc1056914326b61cba6751b16ff91bdf4b3dfc386",
        ROOT / "audits/q1-xai-reconstruction-equivalence-protocol/1.0.0/amendments/historical_design_rationale/1.0.0/MANIFEST.sha256": "c9502cb1ec85d3053b8a972d61657038e66d04fb5e619b0fe08ed94d581c91bb",
        BLOCK7 / "MANIFEST.sha256": "994a6f7aa8d1393904c605e0b5d65db6fcd39b9be55a1eb5219f899346b83d2e",
        BLOCK7 / "g1_g2_g3_results.json": "c07a0bd18d1c73e2cddae0ca829de3dd9e698b233d5d27f3f3f8928fb153f8a5",
        BLOCK7 / "forensics/g3_failure_root_cause/1.0.0/MANIFEST.sha256": "a6f4bd5e5ec43f844860283aef6b3f21933728a5d0817773e7cb1fb742b866e7",
        BLOCK7B / "MANIFEST.sha256": "6e74700b5deeafb4e70d4e46a07a920df37372aa1f52fd1d17b26d3a7a2fdbeb",
        BLOCK7B / "scope_g1_g3_eligibility.jsonl": "2a64d2496c5114c50264f1fbb26d611d7655d91802568c359532e0809fdf043b",
        ROOT / "audits/q1-xai-reconstruction-equivalence-protocol/1.0.0/numerical_tolerance_policy.json": "62fd3780c94c6a69bfc036bdd4b567409ffc46c8c892a807b221f5d40d0eb336",
    }
    assert all(_sha256(path) == digest for path, digest in expected.items())


def test_summary_and_manifest_are_complete_and_self_consistent():
    summary = _json("g4_summary.json")
    assert summary["block8_outcome"] == "FULL_G4_RAW_EQUIVALENCE_READY_FOR_G5_REVIEW"
    assert summary["scope_counts"] == {
        "authorized": 389, "excluded_g3": 3, "pass": 389,
        "fail": 0, "ineligible_upstream": 0, "unresolved": 0,
    }
    assert summary["unimodal"] == {"total": 168, "pass": 168, "fail": 0}
    assert summary["multimodal"] == {
        "total": 221, "pass": 221, "fail": 0, "ineligible_upstream": 0,
    }
    entries = []
    for line in (PACKAGE / "MANIFEST.sha256").read_text().splitlines():
        digest_value, name = line.split("  ", 1)
        entries.append(name)
        assert _sha256(PACKAGE / name) == digest_value
    assert entries == sorted(entries)
    assert set(entries) == {
        "BLOCK8_G4_REPORT.md", "g4_authorization_and_preflight.json",
        "g4_failure_dependency_graph.json", "g4_governance_ledger.json",
        "g4_operational_recovery.json", "g4_reference_alignment.json",
        "g4_scope_results.jsonl", "g4_summary.json",
        "representative_reconstruction_policy.json", "sealed_reference_registry.json",
    }
