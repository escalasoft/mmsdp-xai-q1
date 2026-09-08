# ruff: noqa: E501
"""Narrow byte/provenance checks. Never replay historical smoke or predictive data."""

import ast
import copy
import hashlib
from pathlib import Path

import pytest
from src.evaluation import q1_prospective_e1_parent_integrity_resolution as r


@pytest.fixture(scope="module")
def current():
    return r.Reader(r.ROOT).read(r.TARGET)


@pytest.fixture(scope="module")
def expected():
    return r.manifest_entry(
        r.Reader(r.ROOT).read(r.MANIFEST), "validation-initial-output.txt"
    )["expected_sha256"]


@pytest.fixture(scope="module")
def preflight():
    g = r.ReadOnlyGit(r.ROOT)
    return {"branch": r.BRANCH, "HEAD": g.run("rev-parse", "HEAD").decode().strip()}


@pytest.fixture(scope="module")
def findings(preflight):
    return r.investigate(r.ROOT, preflight)


def test_current_hash_exact(current):
    assert r.sha(current) == hashlib.sha256(current).hexdigest()
    assert len(current) == 4758 and current.count(b"\n") == 60
    assert r.blob_id(current) == "150a9905dcaca3b623c2ed41a0c31b7baa48fee2"


def test_exact_manifest_parser(expected):
    assert len(expected) == 64
    raw = r.Reader(r.ROOT).read(r.MANIFEST)
    record = r.manifest_entry(raw, "validation-initial-output.txt")
    assert record["exact_line"] == expected + "  validation-initial-output.txt"
    assert record["path_semantics"] == "PACKAGE_RELATIVE_BASENAME"
    with pytest.raises(r.AuditBlocked):
        r.manifest_entry(
            raw + record["exact_line"].encode() + b"\n", "validation-initial-output.txt"
        )
    with pytest.raises(r.AuditBlocked):
        r.manifest_entry(
            b"invalid  validation-initial-output.txt\n", "validation-initial-output.txt"
        )


def test_exact_sha256_candidate_independently_verified(current, expected):
    old, evidence = r.reconstruct_whitespace_candidate(current, expected)
    assert old is not None and old != current
    assert hashlib.sha256(old).hexdigest() == expected
    assert evidence["line_1_based"] == 8 and evidence["restored_ASCII_spaces"] == 9
    assert old.splitlines(keepends=True)[7] == b"E" + b" " * 9 + b"\n"
    assert current.splitlines(keepends=True)[7] == b"E\n"
    assert len(old) == 4767
    assert (
        evidence["source"]
        == "DETERMINISTIC_HASH_VERIFIED_RECONSTRUCTION_NOT_GIT_RECOVERY"
    )


def test_no_guessing_from_text_normalization(current):
    old, evidence = r.reconstruct_whitespace_candidate(current, "0" * 64)
    assert old is None and evidence["status"] == "NO_EXACT_SHA256_MATCH"
    assert r.difference_ledger(old, current)[0]["classification"] == [
        "UNKNOWN_DIFFERENCE"
    ]


def test_complete_whitespace_diff_not_semantic_claim_by_filename(current, expected):
    old, _ = r.reconstruct_whitespace_candidate(current, expected)
    ledger = r.difference_ledger(old, current)
    assert len(ledger) == 1
    assert (
        ledger[0]["old_line_range_1_based"]
        == ledger[0]["current_line_range_1_based"]
        == [8, 8]
    )
    assert ledger[0]["classification"] == ["WHITESPACE_ONLY", "FORMAT_ONLY"]
    assert ledger[0]["affects_smoke_conclusion"] is False
    assert ledger[0]["affects_56_3A_integrity_gate"] is True
    assert (
        b"3 failed, 48 passed, 2 deselected" in old
        and b"3 failed, 48 passed, 2 deselected" in current
    )
    assert old.split() == current.split()


def test_material_difference_not_whitelisted():
    ledger = r.difference_ledger(b"51 passed\n", b"51 failed\n")
    assert ledger[0]["classification"] == ["UNKNOWN_DIFFERENCE"]
    assert ledger[0]["affects_smoke_conclusion"] is None


@pytest.mark.parametrize(
    "path",
    [
        "data/T1.json",
        "data/T2.json",
        "objects/model.joblib",
        "/tmp/T1.json",
        "../outside.json",
        r.SMOKE + "/selected_train_rows.json",
        r.SMOKE + "/lr_analytical_smoke.json",
        "audits/q1-t1-confirmatory-execution/1.0.0/results/t1_prediction_evidence.jsonl.gz",
        "audits/q1-xai-reconstruction-execution/1.0.0/objects/model.json",
        "audits/q1-xai-reconstruction-execution/1.0.0/objects/MANIFEST.sha256",
    ],
)
def test_no_scientific_payload_read(path, monkeypatch):
    monkeypatch.setattr(Path, "read_bytes", lambda *a: pytest.fail("Read before deny"))
    with pytest.raises(PermissionError):
        r.Reader(r.ROOT).read(path)


def test_reader_rejects_symlink(tmp_path):
    target = tmp_path / r.TARGET
    target.parent.mkdir(parents=True)
    other = tmp_path / "unapproved.txt"
    other.write_text("not read")
    target.symlink_to(other)
    with pytest.raises(r.AuditBlocked):
        r.Reader(tmp_path).read(r.TARGET)


@pytest.mark.parametrize(
    "args",
    [
        ("add", "file"),
        ("commit", "-m", "x"),
        ("push",),
        ("checkout", "HEAD"),
        ("restore", "file"),
        ("hash-object", "-w", "file"),
        ("cat-file", "-p", "abc"),
        ("diff", "--textconv"),
        ("log", "--output=/tmp/mutation"),
        ("hash-object", "--", "data/T1.json"),
    ],
)
def test_git_inspection_is_read_only(args, monkeypatch):
    monkeypatch.setattr(
        r.subprocess, "run", lambda *a, **k: pytest.fail("Process before deny")
    )
    with pytest.raises(PermissionError):
        r.ReadOnlyGit(r.ROOT).run(*args)


def test_git_blob_reader_denies_model_or_T1_route(monkeypatch):
    monkeypatch.setattr(
        r.subprocess, "run", lambda *a, **k: pytest.fail("Process before deny")
    )
    with pytest.raises(PermissionError):
        r.ReadOnlyGit(r.ROOT).blobs([("a" * 40, "data/T1.json")])


def test_no_scientific_imports_calls_or_shell():
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
        "difflib",
        "hashlib",
        "json",
        "os",
        "pathlib",
        "re",
        "stat",
        "subprocess",
    }
    calls = {
        n.func.attr if isinstance(n.func, ast.Attribute) else n.func.id
        for n in ast.walk(tree)
        if isinstance(n, ast.Call) and isinstance(n.func, (ast.Name, ast.Attribute))
    }
    assert not calls & {
        "fit",
        "fit_transform",
        "partial_fit",
        "predict",
        "predict_proba",
        "decision_function",
        "TreeExplainer",
        "Explainer",
        "shap_values",
        "read_csv",
        "savefig",
        "train",
        "calibrate",
        "average_precision_score",
        "roc_auc_score",
        "f1_score",
        "matthews_corrcoef",
        "exec",
        "eval",
        "import_module",
        "__import__",
        "unlink",
        "rename",
        "replace",
        "touch",
        "utime",
    }
    assert all(
        not any(
            k.arg == "shell" and isinstance(k.value, ast.Constant) and k.value.value
            for k in n.keywords
        )
        for n in ast.walk(tree)
        if isinstance(n, ast.Call)
    )


@pytest.mark.parametrize(
    "name", ["validation-initial-output.txt", "MANIFEST.sha256", "new_replacement.json"]
)
def test_historical_namespace_write_denied(tmp_path, name):
    historical = tmp_path / r.SMOKE / name
    with pytest.raises(PermissionError):
        r.write_new_package(tmp_path, historical.parent, {})
    assert not historical.exists()


def test_new_package_only_no_overwrite_and_manifest(tmp_path):
    files = {"evidence.json": r.canonical({"diagnostic": True})}
    files["MANIFEST.sha256"] = r.make_manifest(files)
    output = tmp_path / r.PACKAGE
    r.write_new_package(tmp_path, output, files)
    before = {p.name: p.read_bytes() for p in output.iterdir()}
    assert r.verify_files(before)
    with pytest.raises(FileExistsError):
        r.write_new_package(tmp_path, output, files)
    assert before == {p.name: p.read_bytes() for p in output.iterdir()}
    corrupted = dict(files)
    corrupted["evidence.json"] += b" "
    assert not r.verify_files(corrupted)


def test_package_deterministic_generation(findings, preflight):
    a = r.encode_files(findings)
    b = r.encode_files(copy.deepcopy(findings))
    assert a == b and r.make_manifest(a) == r.make_manifest(b)
    assert r.report(findings) == r.report(copy.deepcopy(findings))
    assert r.investigate(r.ROOT, preflight) == findings


def test_investigation_preserves_historical_bytes(preflight, current, expected):
    manifest = r.Reader(r.ROOT).read(r.MANIFEST)
    r.investigate(r.ROOT, preflight)
    assert r.Reader(r.ROOT).read(r.TARGET) == current
    assert r.Reader(r.ROOT).read(r.MANIFEST) == manifest
    assert (
        r.manifest_entry(manifest, "validation-initial-output.txt")["expected_sha256"]
        == expected
    )
    assert not r.ReadOnlyGit(r.ROOT).run("diff", "HEAD", "--name-only", "--", "audits")


def test_git_history_and_initial_mismatch_proven(findings):
    t = findings["manifest_file_timeline.json"]
    assert (
        t["first_file_commit"]
        == t["first_manifest_commit"]
        == "4572ec9a6e231996df72f0aa3ec5e7bd9ffec14b"
    )
    assert t["mismatch_present_in_first_commit"] and t["introduced_together"]
    assert (
        t["initial_file_identical_to_current"]
        and t["initial_manifest_identical_to_current"]
    )
    assert t["initial_file_sha256"] != t["initial_manifest_expected_sha256"]
    assert t["target_change_commit_count"] == t["manifest_change_commit_count"] == 1


def test_no_false_git_recovery(findings):
    recovery = findings["historical_byte_recovery.json"]
    assert not recovery["exact_bytes_found_in_reachable_Git"]
    assert not recovery["forensic_copy_persisted"]
    assert (
        recovery["hash_verified_candidate"]["status"] == "EXACT_MANIFEST_SHA256_MATCH"
    )
    search = findings["expected_digest_search.json"]
    assert search["searched_safe_blob_count"] > 500
    assert search["git_digest_reference_hits"]
    assert not search["exact_expected_content_blobs"]
    assert not search["explicit_target_name_in_reachable_source"]
    assert all(r.safe_path(x["path"]) for x in search["searched_blob_inventory"])


def test_independent_support_is_manifest_and_git_anchored(findings):
    evidence = findings["sprint56_1_semantic_reconciliation.json"]
    assert evidence["independent_support"] and all(evidence["invariants"].values())
    assert len(evidence["evidence"]) == 12
    assert all(
        x["manifest_match"] and x["HEAD_match"] for x in evidence["evidence"].values()
    )
    assert evidence["parent_outcome"] == "PRIMARY_XAI_ISOLATED_RUNTIME_SMOKE_TEST_PASS"


def resolution_args():
    return dict(
        exact_git_recovery=False,
        exact_hash_candidate=True,
        whitespace_only=True,
        initial_packaging_mismatch=True,
        independent_support=True,
    )


def test_resolution_is_fail_closed_and_finite():
    args = resolution_args()
    assert r.choose_resolution(**args) == r.PACKAGING
    assert r.choose_resolution(**{**args, "independent_support": False}) == r.BLOCKED
    assert r.choose_resolution(**{**args, "exact_hash_candidate": False}) == r.BLOCKED
    assert r.choose_resolution(**{**args, "whitespace_only": False}) == r.BLOCKED
    assert (
        r.choose_resolution(**{**args, "initial_packaging_mismatch": False})
        == r.BLOCKED
    )
    assert r.choose_resolution(**args, material_change_unreconciled=True) == r.FAIL
    assert r.choose_resolution(**{**args, "exact_git_recovery": True}) == r.RECOVERED
    assert (
        r.choose_resolution(
            **{**args, "exact_hash_candidate": False},
            strong_conclusion_equivalence=True,
        )
        == r.LIMITED
    )
    assert len(r.RESOLUTIONS) == 5


def test_unresolved_cannot_pass_from_log_label_alone():
    args = {k: False for k in resolution_args()}
    assert r.choose_resolution(**args) == r.BLOCKED
    assert r.choose_resolution(**{**args, "whitespace_only": True}) == r.BLOCKED
    assert r.choose_resolution(**{**args, "independent_support": True}) == r.BLOCKED


def test_impact_matrix_complete_and_scoped(findings):
    rows = findings["scientific_impact_matrix.json"]["dimensions"]
    assert [x["id"] for x in rows] == list("ABCDEFGHI")
    assert set(x["status"] for x in rows) <= {
        "PASS_NO_IMPACT",
        "PASS_WITH_PROVENANCE_LIMITATION",
        "POTENTIAL_IMPACT",
        "FAIL_IMPACT",
    }
    assert all(x["status"] == "POTENTIAL_IMPACT" for x in r.impact_matrix(r.BLOCKED))


@pytest.mark.parametrize("counter", r.ZERO)
def test_scientific_counters_zero(findings, counter):
    assert findings["governance_counters.json"][counter] == 0


def test_historical_governance_and_downstream_still_closed(findings):
    c = findings["governance_counters.json"]
    assert (
        c["historical_T1_predictive_access_count"]
        == c["historical_T1_predictive_scoring_count"]
        == 1
    )
    assert c["T2_STATE"] == "DENY_SEALED_REVIEWER_RESERVE"
    p = findings["downstream_56_3a_policy.json"]
    assert (
        p["action"] == "REVALIDATE_SPRINT_56_3A_USING_EXPLICIT_R1_PROVENANCE_AMENDMENT"
    )
    assert p["original_56_3A_disposition"] == "PROSPECTIVE_E1_PROTOCOL_FREEZE_BLOCKED"
    assert (
        not p["56_3A_revalidated_in_R1"]
        and not p["56_3B_authorized"]
        and not p["E1_execution_authorized"]
    )
    assert (
        p["original_mismatch_must_remain_visible"] and p["no_retroactive_byte_identity"]
    )


def test_A_to_Z_report(findings):
    text = r.report(findings).decode()
    assert [line[3] for line in text.splitlines() if line.startswith("## ")] == list(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    )
    assert text.rstrip().endswith(
        "READY FOR HUMAN REVIEW — REVALIDATE SPRINT 56.3A WITH R1 PROVENANCE AMENDMENT"
    )
    assert r.PACKAGING in text
