"""56.3C: negative gates, synthetic numerical tests and persisted evidence QA.

No T1 labels, T2 payloads, model loads or prediction recomputation.
"""

import ast
import gzip
import hashlib
from pathlib import Path

import numpy as np
import pytest
from src.evaluation import q1_bounded_complementary_e1_xai as q
from src.evaluation import q1_e1_prospective_train_representation_reconstruction as r4


def doc(name):
    return q.read(q.OUT / name)


def test_current_branch_and_merge():
    r = doc("preflight.json")
    q.branch_gate(r["branch"], r["head"])
    assert r["parent_merge"] == "PR #121"
    assert "a438dee" in r["log"]


@pytest.mark.parametrize(
    "branch,head", [("main", q.HEAD), (q.BRANCH, "0" * 40), ("", q.HEAD)]
)
def test_branch_rejects_wrong_base(branch, head):
    with pytest.raises(ValueError):
        q.branch_gate(branch, head)


@pytest.mark.parametrize(
    "change",
    [
        dict(project="apache/camel"),
        dict(modality="CODE"),
        dict(modality="PROCESS"),
        dict(family="SVM"),
        dict(partition="T2"),
        dict(labels=True),
        dict(partition="VALIDATION"),
    ],
)
def test_scope_denied_before_io(change, monkeypatch):
    kwargs = dict(
        project=q.PROJECT, modality="TEXT", family="LR", partition="T1", labels=False
    )
    kwargs.update(change)
    monkeypatch.setattr(
        Path, "open", lambda *a, **kw: pytest.fail("Must deny before IO")
    )
    with pytest.raises(PermissionError):
        q.authorize(**kwargs)


@pytest.mark.parametrize("family", list(q.FAMILIES))
def test_all_four_families_authorized(family):
    q.authorize(q.PROJECT, "TEXT", family)


@pytest.mark.parametrize("key", q.DENIED)
def test_prohibited_operations_frozen(key):
    assert doc("non_iteration_contract.json")[key] == "DENY"


@pytest.mark.parametrize("key", q.ZERO)
def test_actual_forbidden_counters_zero(key):
    assert doc("governance_counters.json")[key] == 0


def test_parent_route_and_predictive_closure():
    p = doc("parent_scientific_state_verification.json")
    assert p["r4b"]["source_recovery_closed"]
    assert (
        p["r4b"]["article_route"]
        == "ARTICLE_ROUTE_C_E2_PRIMARY_PLUS_BOUNDED_COMPLEMENTARY_E1"
    )
    assert p["sprint54"]["status"] == "PASS_SPRINT54_INTEGRITY_CLOSED"
    assert p["sprint54"]["predictive_scoring_count"] == 1
    assert p["sprint54"]["t2_state"] == "DENY_SEALED_REVIEWER_RESERVE"


def test_exact_serialization_repair_preserves_parent():
    r = doc("bounded_repair_attempt.json")
    assert (
        r["attempt"] == 1
        and not r["parent_modified"]
        and not r["scientific_content_changed"]
    )
    assert len(r["changes"]) == 5
    for x in r["changes"]:
        original = (
            q.R4 / "representations/apache_activemq/TEXT" / x["file"]
        ).read_bytes()
        child = (q.OUT / "representations/train_verified_copy" / x["file"]).read_bytes()
        assert original + b"\n" == child
        assert hashlib.sha256(child).hexdigest() == x["after"]
    r4.verify_persistence(q.OUT / "representations/train_verified_copy")


def test_integrity_and_repeatability_required():
    r = doc("text_train_representation_integrity.json")
    assert r["status"] == "PASS" and r["shape"] == [3675, 2557]
    r = doc("t1_text_representation_repeatability.json")
    assert r["status"] == "EXACT_REPEATABILITY" and r["shape"] == [245, 2557]
    assert all(
        r[k]
        for k in [
            "CSR_indices",
            "CSR_indptr",
            "values",
            "row_order",
            "column_order",
            "vocabulary_unchanged",
            "idf_unchanged",
        ]
    )
    assert r["refit"] is False


def test_bounded_decoder_never_emits_tail(tmp_path):
    first = b'{"identity":"allowed"}\n'
    path = tmp_path / "synthetic.gz"
    path.write_bytes(gzip.compress(first + b"FORBIDDEN_RESERVE_SENTINEL\n"))
    raw, n = r4.bounded_prefix(path, 1, path.stat().st_size)
    assert raw == first and b"FORBIDDEN" not in raw
    assert n <= path.stat().st_size


@pytest.mark.parametrize(
    "purpose,cap", [("background", 256), ("foreground", 256), ("local", 8)]
)
def test_selection_deterministic_and_capped(purpose, cap):
    rr = [dict(row_identifier=str(i)) for i in range(300)]
    a = q.sample(rr, purpose, cap, "frozen")
    assert a == q.sample(rr[::-1], purpose, cap, "frozen")
    assert len(a) == cap
    with pytest.raises(ValueError):
        q.sample(rr, purpose, cap + 1, "frozen")
    with pytest.raises(ValueError):
        q.sample(rr + [rr[0]], purpose, cap, "frozen")


def test_populations_frozen_before_xai():
    r = doc("populations/freeze.json")
    assert r["before_attribution"] and not r["labels_used"]
    assert (r["background"], r["foreground"], r["local"]) == (256, 245, 8)
    assert r["seed"] == 20260901


def test_alignment_mandatory_and_four_families_accounted():
    r = q.rows(q.OUT / "e1_model_representation_alignment.jsonl")
    assert {x["family"] for x in r} == set(q.FAMILIES)
    assert all(
        x["status"] == "ALIGNMENT_PASS_WITH_PREDECLARED_LIMITATION"
        and x["feature_count"] == 2557
        and x["classes"] == [0, 1]
        for x in r
    )
    assert all(
        x["model_state"] == "RECONSTRUCTED"
        and x["prior_equivalence"] == "G4_PASS_ROW_LEVEL_RAW_EQUIVALENCE"
        for x in r
    )


@pytest.mark.parametrize(
    "family,method",
    [
        ("LR", "EXACT_CENTERED_ANALYTICAL_LOGIT_DECOMPOSITION"),
        ("RF", "EXACT_TREESHAP_POSITIVE_CLASS"),
        ("XGB", "EXACT_TREESHAP_RAW_MARGIN"),
        ("LGB", "EXACT_TREESHAP_RAW_MARGIN"),
    ],
)
def test_frozen_method_and_scale(family, method):
    assert doc("e1_method_registry.json")[family] == method
    assert doc("e1_output_scale_registry.json")["scales"][family] == q.SCALES[family]
    assert not doc("e1_method_registry.json")["approximate"]


def test_fidelity_rejects_real_error_without_relaxation():
    phi = np.array([[0.2, -0.1], [0.5, -0.3]])
    f, _ = q.fidelity(phi, 0.4, np.array([0.5, 0.6]), 1e-10)
    assert f["status"] == "FIDELITY_PASS"
    f, _ = q.fidelity(phi, 0.4, np.array([0.5, 0.9]), 1e-10)
    assert f["status"] == "FIDELITY_FAIL" and f["failures"] == 1
    with pytest.raises(ValueError):
        q.fidelity(np.array([[np.nan]]), 0, np.array([0]), 1e-10)


def test_rf_invalid_values_never_published():
    assert doc("rf_e1_fidelity.json")["status"] == "FIDELITY_FAIL"
    assert doc("rf_e1_shap_values_status.json")["array"] is None
    assert not (q.OUT / "rf_e1_shap_values.npz").exists()
    assert doc("e1_stability_results.json")["RF"]["status"] == "INSUFFICIENT_EVIDENCE"


@pytest.mark.parametrize("family", ["LR", "XGB", "LGB"])
def test_valid_fidelity_stability_complete(family):
    f = doc("e1_fidelity_results.json")[family]
    s = doc("e1_stability_results.json")[family]
    assert (
        f["status"] == "FIDELITY_PASS"
        and f["failures"] == 0
        and f["total_evaluated"] == 4900
    )
    assert len(f["repetition_fidelity"]) == 20
    assert (
        s["status"] == "STABILITY_PASS"
        and s["max_absolute_difference"] == 0
        and len(s["pairs"]) == 190
    )
    assert all(r["total_variation"] == 0 for r in s["pairs"])
    assert len(list((q.OUT / "attributions").glob(f"{family.lower()}_rep_*.npz"))) == 20


def test_cross_model_comparison_and_heterogeneity():
    r = doc("e1_cross_model_consistency.json")
    assert r["status"] == "MODEL_DEPENDENT_EXPLANATIONS"
    assert len(r["comparisons"]) == 6 and {x["k"] for x in r["comparisons"]} == {3, 10}
    assert r["thresholds"] == dict(jaccard=0.6, spearman=0.7, sign=0.8)
    assert not any(x["thresholds_pass"] for x in r["comparisons"])
    assert not doc("e1_explanation_heterogeneity.json")["universal_narrative"]


def test_architectural_traceability_no_propagation():
    r = q.rows(q.OUT / "e1_to_e2_traceability.jsonl")
    assert len(r) == 4 and all(
        x["continuity"] == "ARCHITECTURAL" and not x["algebraic_propagation"] for x in r
    )
    assert all(x["matching_frozen_scope_records"] > 0 for x in r)
    assert doc("xai_claim_hierarchy.json")["E2_ROLE"] == "PRIMARY_MULTIMODAL_XAI"
    assert doc("e1_e2_continuity_contract.json")["algebraic_propagation"] == "DENY"


def test_parent_and_e2_bytes_unchanged():
    assert (
        doc("parent_integrity_before.json")
        == doc("parent_integrity_after.json")
        == q.parent_snapshot()
    )
    assert doc("e2_parent_integrity_before.json") == doc(
        "e2_parent_integrity_after.json"
    )
    assert doc("e2_parent_integrity_diff.json")["status"] == "UNCHANGED"


def test_every_figure_has_hashed_source_table():
    r = q.rows(q.OUT / "e1_figure_registry.jsonl")
    assert len(r) == 4
    for x in r:
        assert q.sha(q.OUT / x["source_data_path"]) == x["source_data_digest"]
        assert x["caption"] and x["runtime"] and x["population"] and x["scale"]
        assert q.sha(q.ROOT / x["generation_script"]) == x["generation_script_digest"]
        for output in x["outputs"]:
            assert q.sha(q.OUT / output["path"]) == output["sha256"]


@pytest.mark.parametrize(
    "name",
    [
        "E1-1_scope",
        "E1-2_top20",
        "E1-3_fidelity_stability",
        "E1-4_consistency",
        "E1-5_hierarchy",
    ],
)
def test_publication_tables_three_formats(name):
    assert all(
        (q.OUT / "tables" / f"{name}.{ext}").is_file() for ext in ["csv", "json", "md"]
    )


def test_claim_ledger_limitations_and_manuscript():
    claims = q.rows(q.OUT / "e1_claim_ledger.jsonl")
    assert claims and all(
        r["status"]
        in [
            "SUPPORTED",
            "SUPPORTED_WITH_LIMITATION",
            "MIXED",
            "NOT_SUPPORTED",
            "DEFERRED",
        ]
        for r in claims
    )
    assert all((q.OUT / p).is_file() for r in claims for p in r["evidence"])
    assert len(doc("e1_limitations.json")) >= 10
    for n in [
        "manuscript_xai_positioning.md",
        "manuscript_e1_results_draft.md",
        "manuscript_e1_discussion_draft.md",
        "reviewer_response_unimodal_xai_scope.md",
    ]:
        assert (q.OUT / n).stat().st_size > 100


def test_manifest_verifies_and_tamper_rejected(tmp_path):
    assert len(q.verify_manifest(q.OUT)) > 100
    (tmp_path / "x").write_bytes(b"changed")
    (tmp_path / "MANIFEST.sha256").write_text("0" * 64 + "  x\n")
    with pytest.raises(ValueError):
        q.verify_manifest(tmp_path)


def test_no_fit_or_predictive_metrics_in_implementation():
    tree = ast.parse(Path(q.__file__).read_text())
    calls = {
        n.func.attr
        for n in ast.walk(tree)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
    }
    assert not calls & {
        "fit",
        "fit_transform",
        "partial_fit",
        "roc_auc_score",
        "f1_score",
        "accuracy_score",
    }
    text = Path(q.__file__).read_text()
    assert "['git', 'commit'" not in text and "['git', 'push'" not in text
    assert doc("recommended_next_action.json")["action"] == "MANUSCRIPT_XAI_INTEGRATION"
