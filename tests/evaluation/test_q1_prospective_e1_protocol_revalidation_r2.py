# ruff: noqa: E501
"""R2 metadata validation and negative authorization tests; no historical loader."""

import ast
import copy
from pathlib import Path

import pytest
from src.evaluation import q1_prospective_e1_protocol_revalidation_r2 as r


@pytest.fixture(scope="module")
def base():
    return r.read_package(r.ROOT, r.BASE)


@pytest.fixture(scope="module")
def amendment():
    return r.read_package(r.ROOT, r.R1)


@pytest.fixture(scope="module")
def chronology():
    return r.chronology_metadata()


@pytest.fixture(scope="module")
def preexisting():
    paths = [
        "src/evaluation/q1_prospective_e1_protocol_freeze.py",
        "tests/evaluation/test_q1_prospective_e1_protocol_freeze.py",
        "tests/evaluation/run_q1_prospective_e1_governance_regressions.py",
        "src/evaluation/q1_prospective_e1_parent_integrity_resolution.py",
        "tests/evaluation/test_q1_prospective_e1_parent_integrity_resolution.py",
    ]
    return {p: {"sha256": r.sha((r.ROOT / p).read_bytes())} for p in paths}


@pytest.fixture(scope="module")
def result(base, amendment, chronology, preexisting):
    return r.revalidate(base, amendment, chronology, True, preexisting)


def changed(package, name, change):
    docs = package.documents()
    change(docs[name])
    files = dict(package.files)
    files[name] = r.encode(docs[name])
    files["MANIFEST.sha256"] = r.manifest_bytes(
        {k: v for k, v in files.items() if k != "MANIFEST.sha256"}
    )
    return r.VerifiedPackage(package.namespace, files)


def test_R1_manifest_required(amendment):
    files = dict(amendment.files)
    del files["MANIFEST.sha256"]
    with pytest.raises(r.ValidationBlocked) as e:
        r.VerifiedPackage(r.R1, files)
    assert e.value.result == r.INVALID
    files = dict(amendment.files)
    files["protocol_summary.json"] += b" "
    with pytest.raises(r.ValidationBlocked) as e:
        r.VerifiedPackage(r.R1, files)
    assert e.value.result == r.INVALID


def test_manifest_duplicates_and_path_traversal_block(amendment):
    for extra in [
        amendment.files["MANIFEST.sha256"].splitlines()[0] + b"\n",
        b"0" * 64 + b"  ../other.json\n",
    ]:
        files = dict(amendment.files)
        files["MANIFEST.sha256"] += extra
        with pytest.raises(r.ValidationBlocked):
            r.VerifiedPackage(r.R1, files)


@pytest.mark.parametrize(
    "name,field,value",
    [
        ("protocol_summary.json", "resolution", "WRONG"),
        ("protocol_summary.json", "amendment_type", "MANIFEST_CORRECTION"),
        ("current_hash_analysis.json", "matches_manifest", True),
        ("current_hash_analysis.json", "path", "audits/other/log.txt"),
        ("current_hash_analysis.json", "SHA256", "0" * 64),
        ("difference_classification_summary.json", "classes", ["WHITESPACE_ONLY"]),
        (
            "difference_classification_summary.json",
            "PASS_FAIL_semantic_difference",
            True,
        ),
        ("difference_classification_summary.json", "test_count_difference", True),
        ("sprint56_1_semantic_reconciliation.json", "independent_support", False),
        ("governance_counters.json", "HISTORICAL_PACKAGE_MUTATION_COUNT", 1),
        ("governance_counters.json", "T1_E1_MODEL_QUERY_COUNT", 1),
        ("governance_counters.json", "SHAP_EXECUTION_COUNT", 1),
        ("governance_counters.json", "RETRAIN_COUNT", 1),
        ("governance_counters.json", "T2_ACCESS_COUNT", 1),
        ("downstream_56_3a_policy.json", "action", "AUTHORIZE_E1"),
        ("downstream_56_3a_policy.json", "E1_execution_authorized", True),
    ],
)
def test_invalid_amendment_never_accepted(base, amendment, name, field, value):
    bad = changed(amendment, name, lambda d: d.__setitem__(field, value))
    with pytest.raises(r.ValidationBlocked) as error:
        r.verify_r1(bad, base)
    assert error.value.result == r.INVALID


def test_R1_verified_and_narrow(base, amendment, result):
    v = r.verify_r1(amendment, base)
    assert v["manifest"]["status"] == "PASS" and all(v["conditions"].values())
    assert v["scope"]["only_artifact"] == r.TARGET
    assert "mtime/order" in v["excluded_from_amendment"]
    retained = result["historical_mismatch_retention.json"]
    assert retained["HISTORICAL_BYTE_INTEGRITY"] == "KNOWN_MISMATCH_RETAINED"
    assert (
        not retained["historical_manifest_match"]
        and not retained["historical_manifest_modified"]
    )
    assert retained["current_sha256"] != retained["manifest_expected_sha256"]
    assert (
        result["scientific_semantic_integrity.json"]["status"]
        == "PASS_WITH_PROVENANCE_AMENDMENT"
    )


def test_package_files_unchanged_after_validation(
    base, amendment, chronology, preexisting
):
    before = (copy.deepcopy(base.files), copy.deepcopy(amendment.files))
    r.revalidate(base, amendment, chronology, True, preexisting)
    assert before == (base.files, amendment.files)
    assert r.read_package(r.ROOT, r.BASE).files == base.files
    assert r.read_package(r.ROOT, r.R1).files == amendment.files


def test_unknown_failure_not_waived(base, amendment, chronology, preexisting):
    bad = changed(
        base,
        "validation_results.json",
        lambda d: d["failures"].append(
            {"test": "another_manifest_mismatch", "finding": "other file"}
        ),
    )
    out = r.revalidate(bad, amendment, chronology, True, preexisting)
    assert out["protocol_summary.json"]["resolution"] == r.BLOCKED
    assert out["downstream_56_3b_policy.json"]["SPRINT56_3B_ELIGIBILITY"] == "NOT_READY"


def test_source_provenance_not_waived(base, amendment, chronology, preexisting):
    bad = copy.deepcopy(preexisting)
    bad["src/evaluation/q1_prospective_e1_protocol_freeze.py"]["sha256"] = "0" * 64
    out = r.revalidate(base, amendment, chronology, True, bad)
    assert out["protocol_summary.json"]["resolution"] == r.BLOCKED


def test_original_failure_inventory_cannot_be_erased(
    base, amendment, chronology, preexisting
):
    bad = changed(
        base, "validation_results.json", lambda d: d.__setitem__("failures", [])
    )
    assert (
        r.revalidate(bad, amendment, chronology, True, preexisting)[
            "protocol_summary.json"
        ]["resolution"]
        == r.BLOCKED
    )


def test_mtime_alone_never_proves_chronology(base):
    only_mtime = {
        "filesystem_mtime_proves_generation_order": False,
        "records": [],
        "mtime_policy": 1,
        "mtime_means": 2,
    }
    out = r.review_mtime(base.documents(), only_mtime, True)
    assert out["disposition"] == "BLOCKED_UNRESOLVED"
    assert out["original_assertion_redefined_as_PASS"] is False


def test_same_commit_is_bounded_limitation_not_historical_order_proof(result):
    m = result["mtime_order_resolution.json"]
    assert m["disposition"] == "PASS_WITH_NONSCIENTIFIC_LIMITATION"
    assert "NOT_PROVEN" in m["historical_generation_order"]
    assert not m["original_assertion_redefined_as_PASS"]
    assert not m["R1_amendment_used_for_this_review"]
    assert m["original_failure_preserved"][0]["test"] == r.ORDER_TEST


def test_order_unrelated_paths_or_changed_history_blocks(
    base, amendment, chronology, preexisting
):
    for mode in ["path", "commit", "unchanged"]:
        bad = copy.deepcopy(chronology)
        unchanged = True
        if mode == "path":
            bad["records"][0]["path"] = "unrelated"
        elif mode == "commit":
            bad["records"][0]["change_commits"].append("0" * 40)
        else:
            unchanged = False
        out = r.revalidate(base, amendment, bad, unchanged, preexisting)
        assert out["protocol_summary.json"]["resolution"] == r.BLOCKED


def test_scope_universe_unchanged_and_label_refinement_only(base, result):
    old = base.documents()["e1_scope_universe.jsonl"]
    new = result["e1_scope_status_after_r2.jsonl"]
    assert len(old) == len(new) == 168
    assert {r["scope_id"] for r in old} == {r["scope_id"] for r in new}
    assert (
        sum(
            x["status_after_R2"] == "E1_PENDING_SCIENTIFIC_INPUT_PROVENANCE"
            for x in new
        )
        == 112
    )
    assert (
        sum(
            x["status_after_R2"] == "TEXT_E1_INELIGIBLE_PENDING_ALIGNMENT_PROOF"
            for x in new
        )
        == 56
    )
    assert all(not x["scientific_execution_eligible"] for x in new)
    assert all(
        x["original_56_3A_status"] == "TEXT_E1_INELIGIBLE"
        for x in new
        if x["modality"] == "TEXT"
    )


@pytest.mark.parametrize(
    "name,field,value",
    [
        ("execution_counters.json", "MODEL_QUERY_COUNT", 1),
        ("execution_counters.json", "historical_T1_predictive_access_count", 2),
        ("scientific_state_preservation.json", "predictive_conclusion", "CHANGED"),
        ("t2_sealed_reserve_policy.json", "future_budget", 1),
        ("execution_authorization_gate.json", "scientific_execution_authorized", True),
    ],
)
def test_scientific_integrity_changes_fail(
    base, amendment, chronology, preexisting, name, field, value
):
    bad = changed(base, name, lambda d: d.__setitem__(field, value))
    out = r.revalidate(bad, amendment, chronology, True, preexisting)
    assert out["protocol_summary.json"]["resolution"] == r.FAIL
    assert not out["downstream_56_3b_policy.json"]["authorized"]


def test_missing_policy_definition_blocks(base, amendment, chronology, preexisting):
    bad = changed(base, "stability_contract.json", lambda d: d.pop("inherited_exact"))
    out = r.revalidate(bad, amendment, chronology, True, preexisting)
    assert out["protocol_summary.json"]["resolution"] == r.BLOCKED
    assert "BLOCKED" in out["q1_protocol_sufficiency_matrix.json"]["status_counts"]


def test_approximate_or_relaxed_policy_never_waived(
    base, amendment, chronology, preexisting
):
    bad = changed(
        base, "rf_treeshap_contract.json", lambda d: d.__setitem__("approximate", True)
    )
    assert (
        r.revalidate(bad, amendment, chronology, True, preexisting)[
            "protocol_summary.json"
        ]["resolution"]
        == r.BLOCKED
    )


@pytest.mark.parametrize("counter", r.ZERO)
def test_zero_scientific_counters(result, counter):
    assert result["governance_counters.json"][counter] == 0


def test_no_model_loads_or_scientific_calls():
    tree = ast.parse(Path(r.__file__).read_text())
    imports = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            imports.update(a.name.split(".")[0] for a in n.names)
        elif isinstance(n, ast.ImportFrom):
            imports.add(n.module.split(".")[0])
    assert imports <= {
        "__future__",
        "argparse",
        "collections",
        "hashlib",
        "json",
        "pathlib",
        "re",
        "subprocess",
    }
    calls = {
        n.func.attr if isinstance(n.func, ast.Attribute) else n.func.id
        for n in ast.walk(tree)
        if isinstance(n, ast.Call) and isinstance(n.func, (ast.Name, ast.Attribute))
    }
    assert not calls & {
        "load_evidence",
        "compile_protocol",
        "fit",
        "fit_transform",
        "partial_fit",
        "predict",
        "predict_proba",
        "TreeExplainer",
        "Explainer",
        "shap_values",
        "read_csv",
        "savefig",
        "average_precision_score",
        "roc_auc_score",
        "exec",
        "eval",
        "import_module",
        "__import__",
        "touch",
        "utime",
        "unlink",
        "rename",
    }


@pytest.mark.parametrize(
    "namespace",
    [
        r.TARGET,
        "data/T1.json",
        "data/T2.json",
        "objects/model.joblib",
        "audits/q1-xai-runtime-freeze/1.0.0",
        "../outside",
    ],
)
def test_no_historical_or_scientific_payload_read(namespace, monkeypatch):
    monkeypatch.setattr(
        Path, "read_bytes", lambda *a: pytest.fail("Read before denial")
    )
    with pytest.raises(PermissionError):
        r.read_package(r.ROOT, namespace)


@pytest.mark.parametrize(
    "args",
    [
        ("show", "HEAD:data/T1.json"),
        ("cat-file", "-p", "abc"),
        ("commit", "-m", "x"),
        ("push",),
        ("diff", "--patch"),
        ("log", "--output=/tmp/x"),
    ],
)
def test_git_metadata_only(args, monkeypatch):
    monkeypatch.setattr(
        r.subprocess,
        "check_output",
        lambda *a, **k: pytest.fail("Command before denial"),
    )
    with pytest.raises(PermissionError):
        r.git(*args)


@pytest.mark.parametrize(
    "namespace", [r.BASE, r.R1, "audits/q1-primary-xai-runtime-smoke/1.0.0"]
)
def test_historical_writes_denied(namespace, tmp_path):
    with pytest.raises(PermissionError):
        r.write_package(tmp_path, tmp_path / namespace, {})
    assert not (tmp_path / namespace).exists()


def test_Q1_matrix_complete(result):
    q = result["q1_protocol_sufficiency_matrix.json"]
    assert [x["id"] for x in q["items"]] == list("ABCDEFGHIJKLMNOPQR")
    assert q["status_counts"] == {"FROZEN_PASS": 15, "FROZEN_WITH_LIMITATION": 3}
    assert q["no_definition_blocker"] and not q["empirical_E1_Q1_readiness_claimed"]
    assert all(all(x["source_files"].values()) for x in q["items"])


def test_downstream_only_ready_on_PASS(result):
    assert result["protocol_summary.json"]["resolution"] == r.PASS
    downstream = result["downstream_56_3b_policy.json"]
    assert downstream["SPRINT56_3B_ELIGIBILITY"] == r.READY
    assert (
        downstream["authorized"] is False
        and downstream["automatically_started"] is False
    )
    assert (
        not downstream["E1_execution_authorized"]
        and not downstream["T1_scientific_row_access_authorized"]
        and not downstream["SHAP_authorized"]
    )
    assert r.select_result(False, {}, [], []) == r.INVALID
    assert r.select_result(True, {"x": {"status": "BLOCKED"}}, [], []) == r.BLOCKED
    assert r.select_result(True, {"x": {"status": "FAIL_SCIENTIFIC"}}, [], []) == r.FAIL


def test_revalidation_deterministic(base, amendment, chronology, preexisting, result):
    again = r.revalidate(base, amendment, copy.deepcopy(chronology), True, preexisting)
    assert result == again and r.serialize(result) == r.serialize(again)


def test_new_manifest_and_no_overwrite(tmp_path, result):
    files = r.serialize(result)
    files["MANIFEST.sha256"] = r.manifest_bytes(files)
    r.write_package(tmp_path, tmp_path / r.OUT, files)
    package = r.VerifiedPackage(
        r.OUT, {p.name: p.read_bytes() for p in (tmp_path / r.OUT).iterdir()}
    )
    assert package.verify()["status"] == "PASS"
    with pytest.raises(FileExistsError):
        r.write_package(tmp_path, tmp_path / r.OUT, files)
    package.files["protocol_summary.json"] += b" "
    with pytest.raises(r.ValidationBlocked):
        package.verify()


def test_report_A_to_Z(result):
    f = copy.deepcopy(result)
    f["preflight.json"] = {"branch": r.BRANCH, "HEAD": "test"}
    text = r.report(f).decode()
    assert [line[3] for line in text.splitlines() if line.startswith("## ")] == list(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    )
    assert text.rstrip().endswith(
        "READY FOR HUMAN REVIEW — SPRINT 56.3B MAY BE SEPARATELY AUTHORIZED"
    )


def test_missing_independent_proof_cannot_vacuously_pass(base, amendment):
    bad = changed(
        amendment,
        "sprint56_1_semantic_reconciliation.json",
        lambda d: d.__setitem__("invariants", {}),
    )
    with pytest.raises(r.ValidationBlocked) as error:
        r.verify_r1(bad, base)
    assert error.value.result == r.INVALID


def test_incomplete_decision_matrix_cannot_pass():
    assert r.select_result(True, {}, [], []) == r.BLOCKED
    assert r.select_result(True, {"check": {"status": "PASS"}}, [], []) == r.BLOCKED


def test_all_tracked_historical_audit_identities_unchanged(amendment):
    historical_tree = amendment.documents()["preflight.json"][
        "historical_audit_tree_snapshot"
    ]
    assert r.git("ls-tree", "-r", "HEAD", "--", "audits") == historical_tree
    assert r.git("diff", "HEAD", "--name-only", "--", "audits") == ""
    assert "/MANIFEST.sha256" in historical_tree
