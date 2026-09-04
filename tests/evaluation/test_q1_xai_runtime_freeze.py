# ruff: noqa: E501

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "audits/q1-xai-runtime-freeze/1.0.0"
G5 = ROOT / "audits/q1-xai-final-output-equivalence-g5/1.0.0"
EXCLUDED = {
    ("apache/zeppelin", "Logistic Regression", "C+T"),
    ("apache/zeppelin", "Logistic Regression", "P+T"),
    ("apache/zeppelin", "Logistic Regression", "C+P+T"),
}


def load(name):
    return json.loads((PACKAGE / name).read_text())


def test_exact_ready_universe_and_exclusions_are_preserved():
    rows = [json.loads(line) for line in (G5 / "xai_readiness_ledger.jsonl").read_text().splitlines()]
    assert len(rows) == len({row["model_identity_sha256"] for row in rows}) == 389
    assert all(row["future_xai_readiness"] == "FUTURE_PRIMARY_XAI_STATE_READY_PENDING_SEPARATE_RUNTIME_AND_EXECUTION_AUTHORIZATION" for row in rows)
    assert not {(row["project"], row["algorithm"], row["configuration"]) for row in rows} & EXCLUDED
    runtime = load("xai_runtime_contract.json")
    assert runtime["g5_ready_scope_count"] == 389
    assert runtime["excluded_scope_count"] == 3


def test_shap_version_fails_closed_and_environment_is_unchanged():
    freeze = load("shap_version_freeze.json")
    assert freeze["status"] == "SHAP_RUNTIME_VERSION_UNRESOLVED"
    assert freeze["selected_version"] is None
    assert freeze["installation_performed"] is False
    assert freeze["package_trials"] == freeze["explainer_imports"] == freeze["explainer_executions"] == 0
    inventory = load("dependency_inventory.json")
    assert inventory["inventories_identical"] is True
    assert inventory["before"] == inventory["after"]
    assert not {row["name"].lower() for row in inventory["after"]["packages"]} & {"shap", "lime"}


def test_explainer_scales_and_approximation_contract_are_exact():
    policy = load("explainer_contract.json")
    e1 = policy["E1_unimodal"]
    assert e1["Logistic Regression"]["scale"] == "LOGIT"
    assert e1["Random Forest"]["primary_method"] == "EXACT_TREESHAP_POSITIVE_CLASS_OUTPUT"
    assert e1["Random Forest"]["approximate"] is False
    assert e1["XGBoost"]["scale"] == e1["LightGBM"]["scale"] == "NATIVE_RAW_MARGIN"
    assert policy["E2_multimodal"]["scale"] == "META_LOGIT"
    assert policy["E3_calibration"]["separate_from_E1_E2"] is True
    assert policy["LIME_PRIMARY_STATUS"] == "EXCLUDED_FROM_PRIMARY_XAI"


def test_population_local_and_query_budget_are_frozen_without_access():
    populations = load("explanation_population_policy.json")
    assert populations["TRAIN_background"]["maximum_rows_per_scope"] == 256
    assert populations["T1_global_foreground"]["maximum_rows_per_scope"] == 256
    assert populations["T1_global_foreground"]["label_use"] is False
    assert populations["selection_execution_in_freeze"] is False
    local = load("local_case_selection_policy.json")
    assert local["maximum_rows_per_scope"] == 8
    assert local["source"] == "SUBSET_OF_FROZEN_T1_GLOBAL_FOREGROUND"
    assert local["post_attribution_selection"] == "FORBIDDEN"
    budget = load("query_budget_policy.json")
    assert budget["per_scope"]["unique_model_input_rows_max"] == 512
    assert budget["per_scope"]["primary_attribution_row_evaluations_max_including_stability"] == 5120
    assert budget["T2_queries"] == 0


def test_fidelity_stability_text_correlation_and_interpretation_are_frozen():
    fidelity = load("xai_fidelity_contract.json")
    assert fidelity["analytical_LR"]["failure"] == "XAI_FAIL_FIDELITY"
    assert fidelity["TreeSHAP"]["failure"] == "XAI_FAIL_ADDITIVITY"
    assert fidelity["TreeSHAP"]["approximate"] == "FORBIDDEN"
    assert fidelity["global"]["reconstruction_tolerance"] == 1e-12
    stability = load("xai_stability_contract.json")
    assert stability["seeds"] == list(range(20260901, 20260921))
    assert stability["top_k"] == [3, 10]
    assert stability["deterministic_method_max_absolute_attribution_difference"] == 1e-12
    assert len(load("text_attribution_contract.json")["required_evidence"]) == 6
    assert load("correlated_feature_policy.json")["absolute_threshold"] == 0.70
    heterogeneity = load("heterogeneity_interpretation_policy.json")
    assert heterogeneity["cross_model"]["minimum_eligible_comparable_algorithm_families"] == 3
    assert heterogeneity["cross_project"]["stable_minimum_pass_projects"] == 11


def test_all_execution_and_protected_access_counters_are_zero():
    counters = load("xai_runtime_contract.json")["execution_counters"]
    assert all(value == 0 for value in counters.values())
    t1 = load("t1_xai_access_policy.json")
    assert t1["freeze_access_count"] == 0
    assert (t1["historical_T1_predictive_access_count"], t1["historical_T1_predictive_scoring_count"], t1["historical_T1_rerun"]) == (1, 1, False)
    t2 = load("t2_reviewer_reserve_policy.json")
    assert t2["T2_ACCESS_COUNT"] == 0
    assert t2["T2_STATE"] == "DENY_SEALED_REVIEWER_RESERVE"


def test_source_has_no_forbidden_execution_or_data_path():
    source = (ROOT / "src/evaluation/q1_xai_runtime_freeze.py").read_text().lower()
    assert "import " + "shap" not in source
    assert "import " + "lime" not in source
    assert ".fit(" not in source
    assert "predict_proba(" not in source
    assert "decision_function(" not in source
    assert "sklearn.metrics" not in source
    assert "t2_rel" not in source


def test_parent_hashes_and_manifest_are_exact():
    inventory = load("dependency_inventory.json")
    assert inventory["parents_after"] == load("xai_runtime_contract.json")["parents_before"]
    entries = {}
    for line in (PACKAGE / "MANIFEST.sha256").read_text().splitlines():
        digest, name = line.split("  ", 1)
        entries[name] = digest
    required = {
        "XAI_RUNTIME_FREEZE_REPORT.md", "xai_runtime_contract.json", "shap_version_freeze.json",
        "explainer_contract.json", "explanation_population_policy.json", "local_case_selection_policy.json",
        "query_budget_policy.json", "xai_fidelity_contract.json", "xai_stability_contract.json",
        "text_attribution_contract.json", "correlated_feature_policy.json", "heterogeneity_interpretation_policy.json",
        "t1_xai_access_policy.json", "t2_reviewer_reserve_policy.json",
        "sprint56_primary_xai_authorization_prerequisites.json", "dependency_inventory.json",
    }
    assert set(entries) == required
    assert all(hashlib.sha256((PACKAGE / name).read_bytes()).hexdigest() == digest for name, digest in entries.items())


def test_sprint56_remains_unauthorized_and_blocked():
    prereq = load("sprint56_primary_xai_authorization_prerequisites.json")
    assert prereq["Sprint56_authorized"] is False
    assert prereq["runtime_freeze_outcome"] == "SHAP_RUNTIME_VERSION_UNRESOLVED"
    assert prereq["execution_forbidden_until_all_satisfied"] is True
