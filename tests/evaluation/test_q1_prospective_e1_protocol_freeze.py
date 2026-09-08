# ruff: noqa: E501
"""Metadata-only protocol checks; no historical scientific execution replay."""

import ast
import copy
from pathlib import Path

import pytest
from src.evaluation import q1_prospective_e1_protocol_freeze as s


@pytest.fixture(scope="module")
def evidence():
    return s.load_evidence()[0]


@pytest.fixture(scope="module")
def policy(evidence):
    return s.compile_protocol(evidence)


def test_branch_independent_deterministic_generation(evidence, monkeypatch):
    original = copy.deepcopy(evidence)
    first = s.serialize(s.compile_protocol(evidence))
    monkeypatch.setattr(s, "BRANCH", "unrelated-review-branch")
    monkeypatch.setattr(s, "git", lambda *a: pytest.fail("Pure compiler consulted git"))
    assert first == s.serialize(s.compile_protocol(copy.deepcopy(evidence)))
    assert evidence == original


@pytest.mark.parametrize(
    "path",
    [
        "data/T1.json",
        "data/T2.json",
        "data/raw/commits.csv",
        "audits/q1-t1-confirmatory-execution/1.0.0/results/t1_prediction_evidence.jsonl.gz",
        "audits/q1-primary-xai-e1-scientific-input-materialization/1.0.0/e1_row_identity_registry.jsonl",
        "audits/q1-primary-xai-runtime-smoke/1.0.0/selected_train_rows.json",
        "objects/model.pipeline.joblib",
        "../outside.json",
        "/tmp/T1.json",
        "audits/q1-xai-runtime-freeze/1.0.0/../../data/T1.json",
    ],
)
def test_no_scientific_payload_read(path, monkeypatch):
    monkeypatch.setattr(
        Path, "read_bytes", lambda *a: pytest.fail("Read occurred before deny")
    )
    with pytest.raises(PermissionError):
        s.MetadataReader(s.ROOT).read(path)


def test_allowlist_not_extended_by_manifest_or_file_suffix():
    assert len(s.allowed_paths()) == 31
    assert all("/objects/" not in p and ".matrix." not in p for p in s.allowed_paths())
    assert not any(
        "prediction_evidence" in p or "row_identity_registry" in p
        for p in s.allowed_paths()
    )


def test_missing_parent_fails_closed(tmp_path):
    with pytest.raises(s.ProtocolBlocked, match="Missing metadata"):
        s.load_evidence(tmp_path)
    assert not (tmp_path / "audits/q1-prospective-e1-protocol-freeze").exists()


def test_symlink_metadata_fails_closed(tmp_path):
    rel = s.source_path(s.RUNTIME, "MANIFEST.sha256")
    path = tmp_path / rel
    path.parent.mkdir(parents=True)
    target = tmp_path / "fake.txt"
    target.write_text("not read")
    path.symlink_to(target)
    with pytest.raises(s.ProtocolBlocked, match="symbolic-link"):
        s.MetadataReader(tmp_path).read(rel)


def test_tampered_parent_fails_before_compilation(tmp_path):
    for name in s.PACKAGES:
        rel = s.source_path(name, "MANIFEST.sha256")
        path = tmp_path / rel
        path.parent.mkdir(parents=True)
        path.write_bytes((s.ROOT / rel).read_bytes())
    for key, pair in s.SOURCES.items():
        rel = s.source_path(*pair)
        (tmp_path / rel).write_bytes((s.ROOT / rel).read_bytes())
    target = tmp_path / s.source_path(*s.SOURCES["fidelity"])
    target.write_bytes(target.read_bytes() + b" ")
    with pytest.raises(s.ProtocolBlocked, match="digest mismatch"):
        s.load_evidence(tmp_path)


def test_no_scientific_execution_imports_or_calls():
    tree = ast.parse(Path(s.__file__).read_text())
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(a.name.split(".")[0] for a in node.names)
        if isinstance(node, ast.ImportFrom):
            imports.add(node.module.split(".")[0])
    assert imports <= {
        "__future__",
        "argparse",
        "collections",
        "hashlib",
        "json",
        "pathlib",
        "subprocess",
    }
    calls = {
        node.func.attr if isinstance(node.func, ast.Attribute) else node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, (ast.Attribute, ast.Name))
    }
    assert not calls & {
        "predict",
        "predict_proba",
        "decision_function",
        "fit",
        "fit_transform",
        "partial_fit",
        "transform",
        "TreeExplainer",
        "Explainer",
        "shap_values",
        "savefig",
        "read_csv",
        "roc_auc_score",
        "average_precision_score",
        "calibrate",
        "kmeans",
        "eval",
        "exec",
        "import_module",
        "__import__",
    }


def test_compile_performs_no_io(evidence, monkeypatch):
    monkeypatch.setattr(
        Path, "read_bytes", lambda *a: pytest.fail("Compiler read a file")
    )
    monkeypatch.setattr(
        Path, "write_bytes", lambda *a: pytest.fail("Compiler wrote a file")
    )
    monkeypatch.setattr(s, "git", lambda *a: pytest.fail("Compiler spawned a process"))
    assert len(s.compile_protocol(evidence)["e1_scope_universe.jsonl"]) == 168


@pytest.mark.parametrize("counter", s.ZERO)
def test_execution_counters_zero(counter, policy):
    assert policy["execution_counters.json"][counter] == 0


def test_historical_counters_and_conclusion(policy):
    c = policy["execution_counters.json"]
    assert (
        c["historical_T1_predictive_access_count"]
        == c["historical_T1_predictive_scoring_count"]
        == 1
    )
    assert (
        policy["scientific_state_preservation.json"]["predictive_conclusion"]
        == "MIXED_CONFIRMATORY_EVIDENCE"
    )
    assert (
        policy["scientific_state_preservation.json"]["historical_recovery"] == "CLOSED"
    )


def test_universe_unimodal_complete_and_no_false_eligibility(policy):
    rows = policy["e1_scope_universe.jsonl"]
    assert len(rows) == len({r["scope_id"] for r in rows}) == 168
    assert len({r["project"] for r in rows}) == 14
    assert {r["algorithm_family"] for r in rows} == set(s.FAMILIES)
    assert {r["modality"] for r in rows} == {"CODE", "PROCESS", "TEXT"}
    assert all("+" not in r["historical_configuration"] for r in rows)
    assert all(
        r["equivalence_eligible"] and not r["scientific_execution_eligible"]
        for r in rows
    )
    assert policy["protocol_summary.json"]["eligibility_counts"] == {
        "E1_PENDING_SCIENTIFIC_INPUT_PROVENANCE": 112,
        "TEXT_E1_INELIGIBLE": 56,
    }
    assert all(r["fidelity"] == "FIDELITY_NOT_TESTED" for r in rows)


def test_missing_duplicate_or_mismatched_scope_fails_closed(evidence):
    for mutation in ["missing", "duplicate", "identity"]:
        e = copy.deepcopy(evidence)
        if mutation == "missing":
            e["material"].pop(0)
        elif mutation == "duplicate":
            e["material"].append(e["material"][0])
        else:
            e["material"][0]["model_identity_sha256"] = "wrong"
        with pytest.raises(s.ProtocolBlocked):
            s.compile_protocol(e)


def test_failed_equivalence_cannot_be_promoted(evidence):
    e = copy.deepcopy(evidence)
    e["g5"][0]["G5_outcome"] = "FAILED"
    rows = s.scope_universe(e)
    row = next(
        r
        for r in rows
        if r["model_identity_sha256"] == e["g5"][0]["model_identity_sha256"]
    )
    assert row["eligibility"] == "E1_INELIGIBLE_EQUIVALENCE"
    assert not row["scientific_execution_eligible"]


def test_changed_parent_governance_blocked(evidence):
    for key, field, value in [
        ("architecture", "selected_alternative", "B"),
        ("counters", "T2_STATE", "OPEN"),
        ("counters", "MODEL_QUERY_COUNT", 1),
        ("t1", "historical_T1_predictive_access_count", 2),
    ]:
        e = copy.deepcopy(evidence)
        e[key][field] = value
        with pytest.raises(s.ProtocolBlocked):
            s.compile_protocol(e)


def test_methods_scales_and_exact_tree_semantics(policy, evidence):
    assert policy["e1_method_contract.json"]["inherited"] == evidence["methods"]
    assert policy["lr_analytical_contract.json"]["scale"] == "LOGIT"
    for prefix, scale in [
        ("rf", "POSITIVE_CLASS_PROBABILITY"),
        ("xgb", "NATIVE_RAW_MARGIN"),
        ("lgb", "NATIVE_RAW_MARGIN"),
    ]:
        tree = policy[prefix + "_treeshap_contract.json"]
        assert tree["approximate"] is False and tree["check_additivity"] is True
        assert tree["feature_perturbation"] == "tree_path_dependent"
        assert tree["scale"] == scale and tree["positive_class"] == 1
        assert tree["no_switch_to_interventional"] is True
    assert policy["e1_method_contract.json"]["LIME"] == "EXCLUDED_FROM_PRIMARY_XAI"
    assert (
        policy["e1_method_contract.json"]["counterfactuals"]
        == "EXCLUDED_FROM_PRIMARY_XAI"
    )


def test_caps_sampling_and_label_blind_policy(policy):
    for name in ["train_background_policy", "t1_global_foreground_policy"]:
        p = policy[name + ".json"]
        assert p["maximum_rows_per_scope"] <= 256 and p["seed"] == 20260901
        assert "SHA-256" in p["tie_break"] and "lexical" in p["tie_break"]
        assert "All" not in p["allocation"] or "256" in p["allocation"]
        assert not p["selection_executed"]
    assert (
        policy["t1_global_foreground_policy.json"]["mode"] == "T1_SELECTION_LABEL_BLIND"
    )
    local = policy["local_case_selection_policy.json"]
    assert local["maximum_rows_per_scope"] <= 8 and local["subset_of_global"]
    assert (
        local["mode"] == "T1_SELECTION_LABEL_BLIND"
        and local["freeze_before_attribution"]
    )
    assert len(local["ordered_roles_per_predicted_class"]) == 4


def test_feature_registry_and_text_no_invented_semantics(policy):
    registry = policy["code_process_feature_contract.json"]["registry"]
    assert [r["feature_name"] for r in registry if r["modality"] == "CODE"] == [
        "la",
        "ld",
        "nf",
        "nd",
        "ns",
        "ent",
    ]
    assert [r["feature_name"] for r in registry if r["modality"] == "PROCESS"] == [
        "ndev",
        "age",
        "nuc",
        "aexp",
        "arexp",
        "asexp",
    ]
    required = {
        "feature_name",
        "display_name",
        "modality",
        "definition",
        "unit",
        "transformation",
        "sign_interpretation_limits",
        "missing_value_policy",
        "source_provenance",
    }
    assert all(required <= r.keys() for r in registry)
    assert (
        next(r for r in registry if r["feature_name"] == "age")["unit"]
        == "SOURCE_UNIT_UNRESOLVED"
    )
    assert policy["text_e1_contract.json"]["any_unknown"] == "TEXT_E1_INELIGIBLE"


def test_correlation_and_group_aggregation(policy):
    c = policy["correlated_feature_policy.json"]
    assert c["absolute_threshold"] == 0.70 and c["evidence_source"] == "TRAIN_ONLY"
    assert c["modalities"] == ["CODE", "PROCESS"]
    assert c["group_importance"] == "mean_i(abs(sum_j_in_group(phi_ij)))"
    assert "CONNECTED_COMPONENTS" in c["group_construction"]


def test_fidelity_tolerances_exact_and_strict_failure(policy, evidence):
    f = policy["fidelity_contract.json"]
    assert f["inherited_exact"] == evidence["fidelity"]
    assert f["unexplained_fraction_threshold"] == 0.0
    assert s.fidelity_status(0, 0, 3) == "FIDELITY_NOT_TESTED"
    assert s.fidelity_status(3, 3, 3) == "FIDELITY_PASS"
    assert s.fidelity_status(2, 3, 3) == "FIDELITY_FAIL"
    assert s.fidelity_status(2, 2, 3) == "FIDELITY_MIXED"
    with pytest.raises(ValueError):
        s.fidelity_status(4, 3, 3)


def test_stability_and_heterogeneity_thresholds_inherited(policy, evidence):
    f = policy["stability_contract.json"]
    assert f["inherited_exact"] == evidence["stability"]
    assert f["inherited_exact"]["seeds"] == list(range(20260901, 20260921))
    assert f["inherited_exact"]["top_k"] == [3, 10]
    assert (
        f["inherited_exact"]["deterministic_method_max_absolute_attribution_difference"]
        == 1e-12
    )
    assert f["comparison_thresholds"] == {
        "Jaccard": 0.6,
        "Spearman": 0.7,
        "sign_agreement": 0.8,
        "total_variation_max": 0.25,
    }
    assert "no population reselection" in f["populations"]
    assert (
        policy["heterogeneity_contract.json"]["inherited_exact"]
        == evidence["heterogeneity"]
    )


def test_continuity_is_architectural_no_unvalidated_composition(policy, evidence):
    c = policy["e1_e2_continuity_contract.json"]
    assert c["E2_role"] == "PRIMARY_EXPLANATORY_CORE"
    assert c["E1_role"] == "COMPLEMENTARY_FEATURE_LAYER"
    assert c["parent_exact_link_contract"] == evidence["continuity"]
    assert set(c["labels"]) == {
        "CONTINUITY_ARCHITECTURAL",
        "CONTINUITY_DIRECTIONAL",
        "CONTINUITY_PROJECT_SPECIFIC",
        "CONTINUITY_MODEL_DEPENDENT",
        "CONTINUITY_NOT_ESTABLISHED",
    }
    assert "propagate E1 SHAP through E2" in c["prohibited"]
    assert policy["e1_e2_bridge_policy.json"]["no_mathematical_composition"]
    assert len(policy["e1_e2_bridge_policy.json"]["statuses"]) == 5


def test_figures_only_design_and_sufficiency_not_results(policy):
    figures = policy["figure_contract.json"]
    assert figures["generated_count"] == 0 and len(figures["families"]) == 8
    assert all(
        r["status"] == "FROZEN_DESIGN_NOT_EMPIRICAL_RESULT" for r in figures["families"]
    )
    gate = policy["q1_scientific_sufficiency_gate.json"]
    assert len(gate["criteria"]) == 18 and len(gate["aggregation"]) == 4
    assert policy["protocol_summary.json"]["disposition"] == s.BLOCKED
    assert policy["protocol_summary.json"]["scientific_execution_eligible_count"] == 0


def test_authorization_budget_and_t2(policy, evidence):
    a = policy["execution_authorization_gate.json"]
    assert not a["scientific_execution_authorized"]
    assert set(a["requirements"]) == {f"AUTH-E1-{i}" for i in range(1, 13)}
    q = policy["query_budget.json"]
    assert q["inherited_exact"] == evidence["budget"]
    assert (
        q["future_per_scope"][
            "primary_attribution_row_evaluations_max_including_stability"
        ]
        == 5120
    )
    t2 = policy["t2_sealed_reserve_policy.json"]
    assert t2["status"] == "DENY_SEALED_REVIEWER_RESERVE"
    assert t2["current_access_count"] == t2["future_budget"] == 0
    assert not policy["recommended_next_action.json"]["start_authorized"]


def test_claims_missing_values_and_persistence(policy):
    assert len(policy["prohibited_claims.json"]["prohibited"]) >= 9
    assert policy["missing_value_policy.json"]["new_imputer_fit"] == "FORBIDDEN"
    assert (
        policy["missing_value_policy.json"]["SHAP_specific_imputation"] == "FORBIDDEN"
    )
    assert policy["reproducibility_persistence_contract.json"]["no_overwrite"]
    assert (
        policy["primary_secondary_analysis_policy.json"]["secondary_label"]
        == "POST_HOC_BEST_OBSERVED_MODEL_ANALYSIS"
    )


def test_manifest_roundtrip_detects_any_change(policy):
    files = s.serialize(policy)
    manifest = s.manifest_bytes(files)
    entries = dict(line.split("  ", 1)[::-1] for line in manifest.decode().splitlines())
    assert set(entries) == set(files)
    assert all(s.digest(files[name]) == h for name, h in entries.items())
    name = "fidelity_contract.json"
    assert s.digest(files[name] + b" ") != entries[name]


def test_required_artifacts_and_A_to_Z_report(policy):
    required = "protocol_summary scientific_state_preservation e1_unit_of_analysis e1_method_contract lr_analytical_contract rf_treeshap_contract xgb_treeshap_contract lgb_treeshap_contract train_background_policy t1_global_foreground_policy local_case_selection_policy text_e1_contract code_process_feature_contract correlated_feature_policy fidelity_contract stability_contract heterogeneity_contract e1_e2_continuity_contract e1_e2_bridge_policy figure_contract q1_scientific_sufficiency_gate execution_authorization_gate t1_xai_access_policy t2_sealed_reserve_policy query_budget missing_value_policy reproducibility_persistence_contract primary_secondary_analysis_policy manuscript_integration_contract threats_to_validity prohibited_claims execution_counters recommended_next_action".split()
    assert {name + ".json" for name in required} <= policy.keys()
    report = s.report(
        policy, {"branch": "test", "HEAD": "test", "merge_parents": ["a", "b"]}
    ).decode()
    assert [line[3] for line in report.splitlines() if line.startswith("## ")] == list(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    )


def test_typed_output_schemas(policy):
    schemas = policy["output_schemas.json"]["schemas"]
    assert set(schemas) == {
        "population",
        "attribution",
        "global_feature",
        "sufficiency",
        "stability",
        "bridge",
    }
    for schema in schemas.values():
        assert schema["additionalProperties"] is False
        assert set(schema["required"]) == set(schema["properties"])
    assert schemas["population"]["properties"]["partition"]["enum"] == ["TRAIN", "T1"]


def test_bad_preflight_cannot_publish(tmp_path):
    with pytest.raises(s.ProtocolBlocked, match="preflight"):
        s.publish({"branch": "wrong", "initial_status": ""}, {}, tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_parent_manifest_discrepancy_blocks_freeze(policy, evidence):
    finding = evidence["parent_log_audit"]
    assert finding["status"] == "FAIL_MANIFEST_MISMATCH"
    assert finding["manifest_sha256"] != finding["actual_sha256"]
    assert policy["protocol_summary.json"]["disposition"] == s.BLOCKED
    assert (
        "do not start56.3B"
        in policy["recommended_next_action.json"]["immediate_action"]
    )
    report = s.report(
        policy, {"branch": "test", "HEAD": "test", "merge_parents": []}
    ).decode()
    assert report.rstrip().endswith("BLOCKED — DO NOT START PROSPECTIVE E1 EXECUTION")


def test_disposition_is_derived_not_forced(evidence):
    hypothetical = copy.deepcopy(evidence)
    hypothetical["parent_log_audit"]["status"] = "PASS"
    hypothetical["parent_log_audit"]["manifest_sha256"] = hypothetical[
        "parent_log_audit"
    ]["actual_sha256"]
    p = s.compile_protocol(hypothetical)
    assert p["protocol_summary.json"]["disposition"] == s.PASS_LIMITED
    assert not p["protocol_summary.json"]["execution_authorized"]
