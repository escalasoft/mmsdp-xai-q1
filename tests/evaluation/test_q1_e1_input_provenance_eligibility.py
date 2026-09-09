"""Read-only metadata/partial TRAIN audit and synthetic adversarial tests."""

import ast
import copy
from pathlib import Path

import pytest
from src.evaluation import q1_e1_input_provenance_eligibility as g


@pytest.fixture(scope="module")
def evidence():
    reader = g.Reader()
    return reader, reader.load()


@pytest.fixture(scope="module")
def result(evidence):
    reader, docs = evidence
    return g.compile_gate(docs, reader)


def test_branch_and_parent_gate():
    g.preflight(g.BRANCH, g.R2_PASS, True)
    for branch, parent, ancestry in [
        ("main", g.R2_PASS, True),
        (g.BRANCH, "FAIL", True),
        (g.BRANCH, g.R2_PASS, False),
    ]:
        with pytest.raises(ValueError):
            g.preflight(branch, parent, ancestry)


def test_parent_required(evidence):
    reader, docs = evidence
    changed = copy.deepcopy(docs)
    changed[f"{g.R2}/protocol_summary.json"]["resolution"] = "FAIL"
    with pytest.raises(ValueError):
        g.compile_gate(changed, reader)


@pytest.mark.parametrize(
    "mutation", ["missing", "duplicate", "pairwise", "full", "modality"]
)
def test_exact_unimodal_universe(evidence, mutation):
    rows = copy.deepcopy(evidence[1][f"{g.BASE}/e1_scope_universe.jsonl"])
    assert len(g.universe(rows)) == 168
    if mutation == "missing":
        rows.pop()
    elif mutation == "duplicate":
        rows[-1] = rows[0]
    elif mutation == "modality":
        rows[0]["modality"] = "PROCESS"
    else:
        rows[0]["historical_configuration"] = "CP" if mutation == "pairwise" else "CPT"
    with pytest.raises(ValueError):
        g.universe(rows)


@pytest.mark.parametrize(
    "path",
    [
        "data/T2.json",
        "data/T1.json",
        "data/external/apachejit-v2/extracted/apachejit/dataset/apachejit_total.csv",
        "objects/model.joblib",
        f"{g.MAT}/e1_row_identity_registry.jsonl",
        "/tmp/anything.json",
        "../outside",
        f"{g.BASE}/../../payload.json",
    ],
)
def test_read_boundary_before_open(path, monkeypatch):
    monkeypatch.setattr(Path, "read_bytes", lambda *a: pytest.fail("Payload opened"))
    with pytest.raises(PermissionError):
        g.Reader().read(path)


def test_symlink_denied(tmp_path):
    target = tmp_path / "target"
    target.write_text("payload")
    rel = f"{g.BASE}/e1_scope_universe.jsonl"
    path = tmp_path / rel
    path.parent.mkdir(parents=True)
    path.symlink_to(target)
    with pytest.raises(ValueError):
        g.Reader(tmp_path).read(rel)


@pytest.mark.parametrize(
    "field",
    [
        "row_identity",
        "feature_order",
        "preprocessing",
        "reconstructed",
        "g4",
        "g5",
        "semantics",
        "no_leakage",
        "partition",
        "population",
        "model_alignment",
        "finite",
        "t1_feature_authorized",
        "fidelity_ready",
        "stability_ready",
        "heterogeneity_ready",
        "local_global_ready",
        "manuscript_traceability",
        "scale",
        "limitations_bounded",
        "no_posthoc",
        "no_t2",
    ],
)
def test_missing_proof_never_passes(field):
    fields = [
        "row_identity",
        "feature_order",
        "preprocessing",
        "reconstructed",
        "g4",
        "g5",
        "semantics",
        "no_leakage",
        "partition",
        "population",
        "model_alignment",
        "finite",
        "t1_feature_authorized",
        "fidelity_ready",
        "stability_ready",
        "heterogeneity_ready",
        "local_global_ready",
        "manuscript_traceability",
        "scale",
        "limitations_bounded",
        "no_posthoc",
        "no_t2",
    ]
    proof = dict.fromkeys(fields, True)
    assert g.eligibility(proof, "CODE") == "Q1_E1_ELIGIBLE"
    del proof[field]
    assert g.eligibility(proof, "CODE") == "Q1_E1_BLOCKED"


def test_text_and_contamination_fail_closed():
    assert g.eligibility({}, "TEXT") == "Q1_E1_INELIGIBLE"
    assert (
        g.eligibility({"token_column_alignment": False}, "TEXT") == "Q1_E1_INELIGIBLE"
    )
    assert g.eligibility({"token_column_alignment": True}, "TEXT") == "Q1_E1_BLOCKED"
    assert g.eligibility({"contamination": True}, "CODE") == "Q1_E1_INELIGIBLE"
    with pytest.raises(ValueError):
        g.disjoint(["a"], ["a"])
    assert g.disjoint(["a"], ["b"])


def matrix():
    return dict(
        partition="TRAIN",
        row_ids=["a", "b"],
        feature_names=["la", "ld"],
        feature_order=["la", "ld"],
        X=dict(
            shape=[2, 2], dtype="<f8", format="DENSE", values=[[1.0, 2.0], [3.0, 4.0]]
        ),
    )


@pytest.mark.parametrize(
    "failure",
    [
        "nan",
        "inf",
        "negative_inf",
        "dtype",
        "duplicate_row",
        "duplicate_column",
        "order",
        "shape",
        "missing",
        "t1",
        "t2",
    ],
)
def test_matrix_integrity(failure):
    m = matrix()
    assert g.matrix_integrity(m, ["la", "ld"])["status"] == "PASS_PARTIAL_TRAIN_ONLY"
    if failure in ["nan", "inf", "negative_inf"]:
        m["X"]["values"][0][0] = float(
            {"nan": "nan", "inf": "inf", "negative_inf": "-inf"}[failure]
        )
    elif failure == "dtype":
        m["X"]["dtype"] = "<i4"
    elif failure == "duplicate_row":
        m["row_ids"] = ["a", "a"]
    elif failure == "duplicate_column":
        m["feature_names"] = ["la", "la"]
    elif failure == "order":
        m["feature_order"].reverse()
    elif failure == "shape":
        m["X"]["shape"] = [3, 2]
    elif failure == "missing":
        m["X"]["values"][0].pop()
    else:
        m["partition"] = failure.upper()
        with pytest.raises(PermissionError):
            g.matrix_integrity(m, ["la", "ld"])
        return
    assert g.matrix_integrity(m, ["la", "ld"])["status"] == "FAIL"


@pytest.mark.parametrize(
    "indices,ptr",
    [([2], [0, 1, 1]), ([0], [0, 2, 1]), ([0, 0], [0, 2, 2]), ([-1], [0, 1, 1])],
)
def test_malformed_sparse(indices, ptr):
    m = matrix()
    m["X"] = dict(
        format="CSR",
        shape=[2, 2],
        dtype="<f8",
        data=[1.0] * len(indices),
        indices=indices,
        indptr=ptr,
    )
    assert g.matrix_integrity(m, ["la", "ld"])["status"] == "FAIL"


def test_sampling_caps_seed_label_independence():
    ids = [str(i) for i in range(500)]
    assert g.SEED == 20260901
    for purpose, partition in [("TRAIN_REFERENCE", "TRAIN"), ("T1_GLOBAL", "T1")]:
        first = g.select_identities(ids, "p", "r", purpose, partition)
        assert first == g.select_identities(ids[::-1], "p", "r", purpose, partition)
        assert len(first) == 256
        local = g.local_cases(first)
        assert len(local) == 8 and set(local) <= set(first)
        assert g.select_identities(["a"], "p", "r", purpose, partition) == ["a"]
    with pytest.raises(PermissionError):
        g.select_identities(ids, "p", "r", "TRAIN_REFERENCE", "T1")
    with pytest.raises(PermissionError):
        g.select_identities(ids, "p", "r", "T1_GLOBAL", "T2")
    with pytest.raises(ValueError):
        g.select_identities(["a", "a"], "p", "r", "T1_GLOBAL", "T1")
    with pytest.raises(TypeError):
        g.select_identities(ids, "p", "r", "T1_GLOBAL", "T1", labels=[])


def test_semantics_preserved(evidence):
    assert g.SEMANTICS["CODE"] == ["la", "ld", "nf", "nd", "ns", "ent"]
    assert g.SEMANTICS["PROCESS"] == ["ndev", "age", "nuc", "aexp", "arexp", "asexp"]
    reader, docs = evidence
    changed = copy.deepcopy(docs)
    changed[f"{g.MAT}/e1_feature_schema_registry.jsonl"][0]["feature_names"] = ["bug"]
    with pytest.raises(ValueError):
        g.compile_gate(changed, reader)


def test_model_identity_and_equivalence_enforced(evidence):
    reader, docs = evidence
    changed = copy.deepcopy(docs)
    row = changed[f"{g.POP}/model_state_readiness_ledger.jsonl"][0]
    row["model_identity_sha256"] = "wrong"
    with pytest.raises(ValueError):
        g.compile_gate(changed, reader)
    for field in ["G4", "G5"]:
        changed = copy.deepcopy(docs)
        row = next(
            r
            for r in changed[f"{g.POP}/model_state_readiness_ledger.jsonl"]
            if r["configuration"] == "C"
        )
        row[field] = "UNKNOWN"
        result = g.compile_gate(changed, reader)
        sid = "|".join(g.key(row))
        r = next(
            r
            for r in result["e1_scope_eligibility_ledger.jsonl"]
            if r["scope_id"] == sid
        )
        assert "RECONSTRUCTED_EQUIVALENCE_UNPROVEN" in r["limitation_codes"]


def test_all_counters(result):
    counters = result["governance_counters.json"]
    assert all(counters[k] == 0 for k in g.ZERO)
    assert counters["T2_STATE"] == "DENY_SEALED_REVIEWER_RESERVE"
    assert counters["historical_T1_predictive_access_count"] == 1
    assert counters["historical_T1_predictive_scoring_count"] == 1


def test_complete_ledgers_coverage_and_no_admission(result):
    rows = result["e1_scope_eligibility_ledger.jsonl"]
    assert len(rows) == len({r["scope_id"] for r in rows}) == 168
    assert len(result["q1_scientific_sufficiency_ledger.jsonl"]) == 168
    for groups in result["coverage_summary.json"].values():
        assert sum(sum(c.values()) for c in groups.values()) == 168
    assert [len(gp) for gp in result["coverage_summary.json"].values()] == [
        3,
        4,
        14,
        12,
        56,
    ]
    for m in ["code", "process", "text"]:
        assert len(result[m + "_provenance_ledger.jsonl"]) == 56
    for n, value in result.items():
        if "population_registry" in n or "candidate_registry" in n:
            assert value == []
    assert result["future_execution_policy.json"]["authorized"] is False
    assert not result["future_execution_policy.json"]["eligible_scope_ids"]


def test_e2_separate_and_claims(result):
    claims = result["claim_to_evidence_boundary.json"]
    assert "no automatic" in claims["continuity"]
    assert result["explanation_scale_registry.json"]["E2"] == "META_LOGIT"
    assert all(
        r["modality"] in g.MODALITIES.values()
        for r in result["e1_scope_eligibility_ledger.jsonl"]
    )


def test_manifest_deterministic_and_parent_unchanged(result, evidence):
    first = g.serialize(result)
    assert first == g.serialize(copy.deepcopy(result))
    for line in first["MANIFEST.sha256"].decode().splitlines():
        digest, name = line.split("  ", 1)
        assert g.sha(first[name]) == digest
    reader, _ = evidence
    assert all(g.sha((g.ROOT / p).read_bytes()) == h for p, h in reader.reads.items())


def test_no_execution_dependencies_or_calls():
    tree = ast.parse(Path(g.__file__).read_text())
    prohibited = {
        "predict",
        "predict_proba",
        "fit",
        "fit_transform",
        "transform",
        "shap_values",
        "TreeExplainer",
        "LinearExplainer",
        "savefig",
        "load_model",
        "train",
        "score",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert all(
                a.name.split(".")[0]
                in {"argparse", "hashlib", "itertools", "json", "math", "subprocess"}
                for a in node.names
            )
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            assert node.func.attr not in prohibited


def test_exact_partial_text_metadata(evidence):
    schema = next(
        r
        for r in evidence[1][f"{g.MAT}/e1_feature_schema_registry.jsonl"]
        if r.get("text")
    )
    assert g.text_alignment(schema) == "EXACT_PARTIAL_METADATA_ONLY"
    bad = copy.deepcopy(schema)
    bad["text"]["token_column_mapping"][bad["feature_names"][0]] = 100
    assert g.text_alignment(bad) == "UNPROVEN"
    bad = copy.deepcopy(schema)
    del bad["text"]["token_pattern"]
    assert g.text_alignment(bad) == "UNPROVEN"


def test_unverified_record_cannot_admit_matrix(evidence, monkeypatch):
    record = next(
        r
        for r in evidence[1][f"{g.MAT}/e1_materialization_ledger.jsonl"]
        if r["matrix"]
    )
    monkeypatch.setattr(Path, "read_bytes", lambda *a: pytest.fail("Unverified read"))
    with pytest.raises(PermissionError):
        g.Reader().train_matrix(record)


def test_changed_r2_contract_not_hidden_by_summary(evidence):
    reader, docs = evidence
    bad = copy.deepcopy(docs)
    checks = bad[f"{g.R2}/revalidated_56_3a_contract.json"]["contract_checks"]
    checks[next(iter(checks))]["status"] = "FAIL"
    with pytest.raises(ValueError):
        g.compile_gate(bad, reader)


def test_metadata_manifest_tamper_denied(evidence, tmp_path):
    reader, _ = evidence
    for rel in sorted(reader.allowed - reader.partial):
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((g.ROOT / rel).read_bytes())
    target = tmp_path / g.BASE / "e1_scope_universe.jsonl"
    target.write_bytes(target.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="digest mismatch"):
        g.Reader(tmp_path).load()
