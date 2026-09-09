"""Canonical linkage tests: synthetic negatives and admitted TRAIN-only evidence."""

import ast
import copy
from pathlib import Path

import pytest
from src.evaluation import q1_e1_canonical_identity_representation_linkage as r


@pytest.fixture(scope="module")
def evidence():
    return r.Evidence().load()


@pytest.fixture(scope="module")
def result(evidence):
    return r.build(evidence, [])


def test_branch_gate():
    r.r1.branch_gate(r.b.BRANCH)
    with pytest.raises(ValueError):
        r.r1.branch_gate("main")


@pytest.mark.parametrize(
    "change", ["verdict", "scope_count", "t1_authorized", "model_origin", "counter"]
)
def test_parent_required(evidence, change):
    d = copy.deepcopy(evidence.docs)
    if change == "verdict":
        d["protocol_summary.json"]["verdict"] = "PASS"
    elif change == "scope_count":
        d["protocol_summary.json"]["candidate_scopes"] = 167
    elif change == "t1_authorized":
        d["t1_feature_value_access_authorization_contract.json"]["authorized"] = True
    elif change == "model_origin":
        d["reconstructed_state_e1_dependency_ledger.jsonl"][0]["origin"] = "ORIGINAL"
    else:
        d["governance_counters.json"]["SHAP_EXECUTION_COUNT"] = 1
    with pytest.raises(ValueError):
        r.verify_parent(d)


@pytest.mark.parametrize(
    "kind,identity,status",
    [
        ("full_commit_sha", "a" * 40, "IDENTITY_CANONICAL_EXACT"),
        ("frozen_row_sha256", "a" * 64, "IDENTITY_CANONICAL_WITH_LIMITATION"),
        ("full_commit_sha", "a" * 7, "IDENTITY_AMBIGUOUS"),
        ("full_commit_sha", "A" * 40, "IDENTITY_AMBIGUOUS"),
        ("row_index", "42", "IDENTITY_AMBIGUOUS"),
        ("project_qualified_sha", "project/" + "a" * 40, "IDENTITY_AMBIGUOUS"),
        ("full_commit_sha", " " + "a" * 40, "IDENTITY_AMBIGUOUS"),
    ],
)
def test_identity_normalization(kind, identity, status):
    first = r.normalize_identity("p", identity, kind)
    assert first == r.normalize_identity("p", identity, kind)
    assert first["status"] == status


@pytest.mark.parametrize(
    "field,value",
    [
        ("partition", "T1"),
        ("partition", "T2"),
        ("partition", "UNKNOWN"),
        ("project", "q"),
        ("commit_identity", "b" * 40),
        ("commit_identity", None),
        ("scientific_identity", "other"),
    ],
)
def test_cross_links_fail(field, value):
    a = dict(
        partition="TRAIN",
        project="p",
        commit_identity="a" * 40,
        scientific_identity="r",
    )
    assert r.validate_identity_link(a, a)
    other = dict(a)
    other[field] = value
    with pytest.raises((ValueError, PermissionError)):
        r.validate_identity_link(a, other)


@pytest.mark.parametrize(
    "path",
    [
        "data/T1.json",
        "data/T2.json",
        "audits/q1-apachejit-final-dataset-freeze/1.0.0/row_identity_provenance.jsonl.gz",
        "objects/model.joblib",
        "../outside",
    ],
)
def test_payload_boundary(path, monkeypatch):
    monkeypatch.setattr(Path, "read_bytes", lambda *a: pytest.fail("Forbidden read"))
    with pytest.raises(PermissionError):
        r.b.Reader().read(path)
    with pytest.raises(PermissionError):
        r.r1.Reader().exact_read(path)


@pytest.mark.parametrize(
    "values,columns,indices",
    [
        ([float("nan")], 1, None),
        ([float("inf")], 1, None),
        ([float("-inf")], 1, None),
        ([1.0], 2, None),
        ([1.0, 2.0], 2, [0, 0]),
        ([1.0], 2, [-1]),
        ([1.0], 2, [2]),
        ([1.0], 2, [0.0]),
        ([True], 1, None),
    ],
)
def test_invalid_serialization_fails(values, columns, indices):
    with pytest.raises(ValueError):
        r.row_bytes(values, columns, indices)


def test_dense_serialization_known_bytes():
    assert (
        r.row_bytes([1.0], 1).hex()
        == "453152325f524f575f563100440100000000000000000000000000f03f"
    )
    assert r.sha(r.row_bytes([1.0, 2.0], 2)) == r.sha(r.row_bytes([1.0, 2.0], 2))
    assert r.row_bytes([0.0], 1) != r.row_bytes([-0.0], 1)
    assert r.row_bytes([1.0, 2.0], 2) != r.row_bytes([2.0, 1.0], 2)


def test_sparse_canonical_order_and_shape():
    assert r.row_bytes([2.0, 1.0], 4, [3, 0]) == r.row_bytes([1.0, 2.0], 4, [0, 3])
    assert r.row_bytes([1.0], 4, [0]) != r.row_bytes([1.0], 5, [0])
    assert r.row_bytes([], 4, []) == r.row_bytes([], 4, [])
    assert r.row_bytes([0.0], 4, [0]) != r.row_bytes([], 4, [])


@pytest.mark.parametrize("missing", r.CRITICAL)
def test_complete_needs_every_critical_link(missing):
    proof = dict.fromkeys(r.CRITICAL, "P4")
    assert r.scope_status(proof, True, 80) == "CANONICAL_LINKAGE_COMPLETE"
    proof[missing] = "P2"
    assert r.scope_status(proof, True, 80) == "CANONICAL_LINKAGE_PARTIAL"
    del proof[missing]
    assert r.scope_status(proof, True, 0) == "CANONICAL_LINKAGE_UNRESOLVED"


def test_partial_population_never_complete():
    proof = dict.fromkeys(r.CRITICAL, "P4")
    assert r.scope_status(proof, False, 80) == "CANONICAL_LINKAGE_PARTIAL"
    assert r.scope_status(proof, False, 0) == "CANONICAL_LINKAGE_UNRESOLVED"
    with pytest.raises(ValueError):
        r.scope_status({"commit": "P5"}, True, 80)


def test_text_metadata_alone_insufficient(result):
    rows = result["text_canonical_linkage.jsonl"]
    assert len(rows) == 56
    assert all(x["linkage_status"] != "CANONICAL_LINKAGE_COMPLETE" for x in rows)
    assert all(x["provenance_strength"]["commit"] == "P0" for x in rows)
    assert len(result["text_commit_message_linkage.jsonl"]) == 80
    assert all(
        not x["canonical_message_commit_linkage"]
        for x in result["text_commit_message_linkage.jsonl"]
    )
    assert len(result["text_message_to_vector_linkage.jsonl"]) == 320


def test_row_and_column_identity_and_digests(result):
    rows = result["representation_row_identity_registry.jsonl"]
    values = result["representation_value_digest_registry.jsonl"]
    columns = result["representation_column_identity_registry.jsonl"]
    assert len(rows) == len(values) == 960
    assert len(columns) == 168
    assert len({(r["scope_id"], r["matrix_row_index"]) for r in rows}) == 960
    assert len({(r["scope_id"], r["identity"]) for r in values}) == 960
    for c in columns:
        assert len(set(c["feature_names"])) == c["n_columns"]
        assert r.sha(r.canonical(c["feature_names"])) == c["column_order_digest"]
        if c["modality"] in r.b.SEMANTICS:
            assert c["feature_names"] == r.b.SEMANTICS[c["modality"]]
    assert all(len(v["representation_digest"]) == 64 for v in values)


def test_reconstructed_distinction(result):
    assert {
        x["representation_origin"]
        for x in result["representation_value_digest_registry.jsonl"]
    } == {"RECONSTRUCTED_REPRESENTATION"}
    assert {
        x["model_origin"]
        for x in result["representation_to_model_identity_linkage.jsonl"]
    } == {"RECONSTRUCTED"}
    assert all(
        not x["original_matrix_claim"]
        for x in result["representation_value_digest_registry.jsonl"]
    )


def test_coverage_exact_universe(result):
    rows = result["canonical_linkage_scope_ledger.jsonl"]
    assert len(rows) == len({r["scope_id"] for r in rows}) == 168
    assert sum(x["linkage_status"] == "CANONICAL_LINKAGE_PARTIAL" for x in rows) == 12
    assert (
        sum(x["linkage_status"] == "CANONICAL_LINKAGE_UNRESOLVED" for x in rows) == 156
    )
    assert [len(x) for x in result["coverage_summary.json"].values()] == [
        14,
        3,
        4,
        42,
        12,
        168,
    ]
    assert all(
        sum(sum(c.values()) for c in groups.values()) == 168
        for groups in result["coverage_summary.json"].values()
    )
    assert (
        result["train_linkage_coverage_summary.json"]["total_expected_train"] == 56821
    )
    assert all(
        x["coverage"] == 0 for x in result["train_representation_completeness.json"]
    )


def test_counters_and_authorization(result):
    counters = result["governance_counters.json"]
    assert all(counters[k] == 0 for k in r.b.ZERO)
    assert counters["T2_STATE"] == "DENY_SEALED_REVIEWER_RESERVE"
    assert (
        counters["historical_T1_predictive_access_count"]
        == counters["historical_T1_predictive_scoring_count"]
        == 1
    )
    assert result["t1_canonical_identity_linkage.jsonl"] == []
    assert not result["t1_feature_access_linkage_readiness.json"][
        "feature_access_authorized"
    ]
    assert not result["future_revalidation_policy.json"]["started"]


def test_output_manifest_deterministic_and_parent_immutable(evidence, result):
    first = r.b.serialize(result)
    assert first == r.b.serialize(copy.deepcopy(result))
    for line in first["MANIFEST.sha256"].decode().splitlines():
        digest, name = line.split("  ", 1)
        assert r.sha(first[name]) == digest
    assert all(r.sha((r.ROOT / p).read_bytes()) == h for p, h in evidence.reads.items())


def test_no_model_or_attribution_execution():
    tree = ast.parse(Path(r.__file__).read_text())
    prohibited = {
        "fit",
        "fit_transform",
        "transform",
        "predict",
        "predict_proba",
        "train",
        "TreeExplainer",
        "LinearExplainer",
        "shap_values",
        "load_model",
        "savefig",
        "score",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert all(
                a.name in {"argparse", "json", "math", "re", "struct"}
                for a in node.names
            )
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            assert node.func.attr not in prohibited
