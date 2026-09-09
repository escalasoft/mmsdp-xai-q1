"""R4 gates and synthetic data tests; no benchmark payload or predictor loads."""

import ast
import copy
import gzip
import json
from pathlib import Path

import pytest
from src.evaluation import q1_e1_prospective_train_representation_reconstruction as r


@pytest.fixture(scope="module")
def parent():
    _, d, _ = r.metadata()
    return d


def test_branch():
    r.r3.branch_gate(r.r3.b.BRANCH)
    with pytest.raises(ValueError):
        r.r3.branch_gate("main")


@pytest.mark.parametrize("verdict", ["BLOCKED", "FAIL", "READY", None])
def test_parent_pass_required(parent, verdict):
    d = copy.deepcopy(parent)
    d["protocol_summary.json"]["verdict"] = verdict
    with pytest.raises(ValueError):
        r.verify_r3(d)


def proof():
    return dict(
        path=r.FREEZE + "/text_dataset.jsonl.gz",
        partition="TRAIN",
        project=r.PROJECT,
        source_class="AUTHORITATIVE_FROZEN_SOURCE_WITH_LIMITATION",
        membership_verified=True,
        producer_order_verified=True,
        boundary_verified=True,
        decompressed_lines_read=3675,
        compressed_bytes_read=706809,
        prefix_sha256="708d0909cc4d1cb665eab7bd91fcf17f2c3d5ca5ef5e32eb73e235c193b78ee5",
    )


@pytest.mark.parametrize(
    "key,value",
    [
        ("partition", "T1"),
        ("partition", "T2"),
        ("partition", None),
        ("project", "apache/camel"),
        ("source_class", "PARTIAL_DIAGNOSTIC_ONLY"),
        ("source_class", "UNKNOWN_SOURCE"),
        ("source_class", "UNVERIFIED_COPY"),
        ("source_class", "T1_SOURCE"),
        ("source_class", "T2_SOURCE"),
        ("source_class", "POST_OUTCOME_SOURCE"),
        ("path", "labels.json"),
        ("path", "T1.csv"),
        ("path", "T2.csv"),
        ("path", r.FREEZE + "/row_identity_provenance.jsonl.gz"),
        ("membership_verified", False),
        ("producer_order_verified", False),
        ("boundary_verified", False),
        ("boundary_verified", "true"),
        ("compressed_bytes_read", 706810),
        ("decompressed_lines_read", 3676),
        ("prefix_sha256", "0" * 64),
    ],
)
def test_admission_precedes_open(key, value, monkeypatch):
    p = proof()
    p[key] = value
    monkeypatch.setattr(
        Path, "open", lambda *a, **kw: pytest.fail("Must reject before IO")
    )
    with pytest.raises((ValueError, PermissionError)):
        r.read_source(p)


def test_exact_admission_contract():
    r.source_gate(proof())


def test_bounded_prefix_does_not_consume_tail(tmp_path):
    prefix = b'{"partition":"TRAIN"}\n'
    content = gzip.compress(prefix, mtime=0)
    p = tmp_path / "synthetic.gz"
    p.write_bytes(content + b"SEALED_T2_SENTINEL")
    actual, consumed = r.bounded_prefix(p, 1, len(content))
    assert actual == prefix and consumed <= len(content)
    with pytest.raises(ValueError):
        r.bounded_prefix(p, 2, len(content))


@pytest.mark.parametrize("n,cap", [(0, 1), (1, 0), (-1, 5), (1, -2), (1.0, 8)])
def test_bad_prefix_bounds(tmp_path, n, cap):
    with pytest.raises(ValueError):
        r.bounded_prefix(tmp_path / "does-not-exist", n, cap)


def identity_rows():
    return [
        dict(
            partition="TRAIN",
            project=r.PROJECT,
            row_identifier="a" * 64,
            order_key=["2000-01-01", "a" * 40],
        )
    ]


def identity_proof():
    return dict(ids=["a" * 64], prefix_sha256="b" * 64)


@pytest.mark.parametrize(
    "field,value",
    [
        ("partition", "T1"),
        ("partition", "T2"),
        ("partition", None),
        ("row_identifier", None),
        ("order_key", []),
        ("project", "unknown"),
    ],
)
def test_row_partition_identity_required(field, value):
    rows = identity_rows()
    rows[0][field] = value
    with pytest.raises(ValueError):
        r.identities(rows, identity_proof())


def test_duplicate_row_identity():
    with pytest.raises(ValueError):
        r.identities(identity_rows() * 2, identity_proof())


def test_identity_registry_full_commit_and_membership():
    rows = r.identities(identity_rows(), identity_proof())
    assert rows[0]["canonical_identity_key"] == [r.PROJECT, "a" * 40]
    assert rows[0]["source_digest"] == "b" * 64
    p = identity_proof()
    p["ids"] = ["b" * 64]
    with pytest.raises(ValueError):
        r.identities(identity_rows(), p)


def text_state():
    return dict(
        parameters=dict(
            lowercase=True,
            max_features=2,
            min_df=1,
            ngram_range=[1, 1],
            norm="l2",
            sublinear_tf=True,
            token_pattern=r"(?u)\b\w\w+\b",
        ),
        vocabulary={"alpha": 0, "beta": 1},
        idf=[1.0, 1.0],
        feature_order=["alpha", "beta"],
    )


@pytest.mark.parametrize("key", ["parameters", "vocabulary", "idf", "feature_order"])
def test_missing_text_state(key):
    d = text_state()
    del d[key]
    with pytest.raises(ValueError):
        r.validate_text(d)


@pytest.mark.parametrize("mutation", ["order", "idf", "nan", "duplicate", "tokenizer"])
def test_exact_state_required(mutation):
    d = text_state()
    if mutation == "order":
        d["feature_order"].reverse()
    if mutation == "idf":
        d["idf"].pop()
    if mutation == "nan":
        d["idf"][0] = float("nan")
    if mutation == "duplicate":
        d["feature_order"][1] = "alpha"
    if mutation == "tokenizer":
        del d["parameters"]["token_pattern"]
    with pytest.raises(ValueError):
        r.validate_text(d)


def test_transform_repeatability_without_fit(monkeypatch):
    from sklearn.feature_extraction.text import TfidfVectorizer

    monkeypatch.setattr(
        TfidfVectorizer, "fit", lambda *a, **kw: pytest.fail("fit forbidden")
    )
    monkeypatch.setattr(
        TfidfVectorizer,
        "fit_transform",
        lambda *a, **kw: pytest.fail("fit_transform forbidden"),
    )
    a = r.transform_text(["alpha", "beta"], text_state())
    b = r.transform_text(["alpha", "beta"], text_state())
    assert r.matrix_objects(a) == r.matrix_objects(b)
    assert r.integrity(a, ["row1", "row2"], ["alpha", "beta"])["status"] == "PASS"


@pytest.mark.parametrize(
    "mutation",
    [
        "nan",
        "inf",
        "negative_inf",
        "duplicate_ids",
        "duplicate_columns",
        "schema",
        "zero_column",
    ],
)
def test_integrity_rejects_invalid(mutation):
    from scipy.sparse import csr_matrix

    a = csr_matrix([[1.0, 0.0], [0.0, 1.0]])
    ids = ["row1", "row2"]
    names = ["alpha", "beta"]
    if mutation in ["nan", "inf", "negative_inf"]:
        a.data[0] = {
            "nan": float("nan"),
            "inf": float("inf"),
            "negative_inf": -float("inf"),
        }[mutation]
    if mutation == "duplicate_ids":
        ids[1] = ids[0]
    if mutation == "duplicate_columns":
        names[1] = names[0]
    if mutation == "schema":
        names.append("extra")
    if mutation == "zero_column":
        a = csr_matrix([[1.0, 0.0], [1.0, 0.0]])
    with pytest.raises(ValueError):
        r.integrity(a, ids, names)


@pytest.mark.parametrize(
    "name", ["../historical.json", "/tmp/historical.json", "a/../historical.json"]
)
def test_namespace_no_escape(tmp_path, name):
    with pytest.raises(PermissionError):
        r.atomic_file(tmp_path, name, b"x")


def test_atomic_no_overwrite_and_failure(tmp_path, monkeypatch):
    r.atomic_file(tmp_path, "receipt", b"original")
    with pytest.raises(FileExistsError):
        r.atomic_file(tmp_path, "receipt", b"new")
    assert (tmp_path / "receipt").read_bytes() == b"original"
    monkeypatch.setattr(
        r.os, "link", lambda *a: (_ for _ in ()).throw(OSError("disk failure"))
    )
    with pytest.raises(OSError):
        r.atomic_file(tmp_path, "failed", b"new")
    assert not (tmp_path / "failed").exists()
    with pytest.raises(ValueError):
        r.verify_persistence(tmp_path)


@pytest.mark.parametrize(
    "missing",
    [
        "matrix.bin",
        "row_registry.jsonl",
        "column_registry.jsonl",
        "transform_state.json",
        "schema.json",
        "digests.json",
        "provenance.json",
        "raw_message_registry.jsonl",
        "vocabulary.json",
        "idf.json",
        "token_column_registry.jsonl",
        "creation_runtime.json",
        "csr_data.f64",
        "csr_indices.u64",
        "csr_indptr.u64",
        "csr_shape.json",
    ],
)
def test_every_persistence_object_required(tmp_path, missing):
    required = {
        "matrix.bin",
        "row_registry.jsonl",
        "column_registry.jsonl",
        "transform_state.json",
        "schema.json",
        "digests.json",
        "provenance.json",
        "raw_message_registry.jsonl",
        "vocabulary.json",
        "idf.json",
        "token_column_registry.jsonl",
        "creation_runtime.json",
        "csr_data.f64",
        "csr_indices.u64",
        "csr_indptr.u64",
        "csr_shape.json",
    }
    for name in required - {missing}:
        r.atomic_file(tmp_path, name, b"synthetic")
    manifest = "".join(
        f"{r.sha(p.read_bytes())}  {p.name}\n" for p in sorted(tmp_path.iterdir())
    )
    r.atomic_file(tmp_path, "MANIFEST.sha256", manifest.encode())
    with pytest.raises(ValueError):
        r.verify_persistence(tmp_path)


def test_frozen_semantics_and_future_authorization(parent):
    assert parent["code_process_semantic_contract.json"]["feature_migration"] == "DENY"
    assert (
        parent["text_reconstruction_policy.json"]["new_vectorizer_fit_authorized"]
        is False
    )
    assert parent["t1_reconstruction_policy.json"]["authorized"] is False
    assert (
        parent["terminology_contract.json"]["representation_state"]
        == "RECONSTRUCTED_REPRESENTATION"
    )


def test_no_predictive_execution():
    tree = ast.parse((r.ROOT / r.SOURCE).read_text())
    forbidden = {
        "predict",
        "predict_proba",
        "fit",
        "fit_transform",
        "shap_values",
        "savefig",
        "train",
        "calibrate",
        "load_model",
        "dump",
        "load",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if (
                node.func.attr == "load"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "reader"
            ):
                continue
            assert node.func.attr not in forbidden


def test_parent_hashes_unchanged(parent):
    assert parent["parent_r2_verification.json"]["verified"]
    for name, h in parent["historical_immutability_verification.json"][
        "parent_hashes"
    ].items():
        assert r.sha((r.ROOT / name).read_bytes()) == h


def test_persisted_representation_cross_artifact_integrity():
    base = r.ROOT / r.OUT / "representations/apache_activemq/TEXT"
    if not base.exists():
        pytest.skip("Execution artifact not generated yet")
    assert (
        r.verify_persistence(base)
        == "ELIGIBLE_FOR_DOWNSTREAM_REVIEW_NOT_XAI_AUTHORIZATION"
    )
    for path in base.iterdir():
        assert not path.stat().st_mode & 0o222


def test_actual_coverage_counter_and_safety_evidence():
    out = r.ROOT / r.OUT
    if not (out / "protocol_summary.json").exists():
        pytest.skip("Execution artifact not generated yet")

    def read(name):
        return json.loads((out / name).read_text())

    summary = read("protocol_summary.json")
    assert (
        summary["persisted_representations"] == 1
        and summary["persisted_unique_train_rows"] == 3675
    )
    coverage = read("coverage_summary.json")
    assert coverage["blocked"] == 41 and coverage["compatible_e1_dependencies"] == 4
    counters = read("governance_counters.json")
    for key in r.r3.b.ZERO:
        assert counters[key] == 0
    assert counters["TRAIN_SOURCE_VALUE_READ_COUNT"] == 7350
    assert counters["TRAIN_REPRESENTATION_RECONSTRUCTION_COUNT"] == 2
    assert counters["TRAIN_REPRESENTATION_PERSIST_COUNT"] == 1
    assert (
        counters["historical_T1_predictive_access_count"]
        == counters["historical_T1_predictive_scoring_count"]
        == 1
    )
    assert read("parent_integrity_diff.json")["before_equals_after"]
    assert read("future_t1_policy.json")["authorized"] is False
    assert read("train_partition_safety_audit.json")["TRAIN_ONLY"] == "PASS"
    links = [
        json.loads(x)
        for x in (out / "train_representation_to_e1_scope_linkage.jsonl")
        .read_text()
        .splitlines()
        if x.strip()
    ]
    matched = [x for x in links if x["representation_id"]]
    assert len(matched) == 4 and len({x["representation_id"] for x in matched}) == 1
