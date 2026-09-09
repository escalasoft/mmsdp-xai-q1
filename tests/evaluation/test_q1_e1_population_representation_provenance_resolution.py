"""R1 metadata tests and synthetic no-I/O access-boundary tests."""

import ast
import copy
from pathlib import Path

import pytest
from src.evaluation import q1_e1_population_representation_provenance_resolution as r


@pytest.fixture(scope="module")
def evidence():
    reader = r.Reader()
    reader.load()
    return reader


@pytest.fixture(scope="module")
def result(evidence):
    return r.build(evidence, r.discover())


def test_branch_required():
    r.branch_gate(r.parent.BRANCH)
    with pytest.raises(ValueError):
        r.branch_gate("main")


@pytest.mark.parametrize(
    "change",
    ["verdict", "count", "eligibility", "model_origin", "execution", "population"],
)
def test_material_parent_difference_stops(evidence, change):
    d = copy.deepcopy(evidence.docs)
    if change == "verdict":
        d[f"{r.PARENT}/protocol_summary.json"]["verdict"] = "PASS"
    elif change == "count":
        d[f"{r.PARENT}/protocol_summary.json"]["candidate_scopes"] = 167
    elif change == "eligibility":
        d[f"{r.PARENT}/e1_scope_eligibility_ledger.jsonl"][0][
            "final_scope_eligibility"
        ] = "Q1_E1_ELIGIBLE"
    elif change == "model_origin":
        d[f"{r.PARENT}/e1_scope_eligibility_ledger.jsonl"][0][
            "reconstructed_state_status"
        ] = "ORIGINAL"
    elif change == "execution":
        d[f"{r.PARENT}/governance_counters.json"]["MODEL_QUERY_COUNT"] = 1
    else:
        d[f"{r.PARENT}/train_background_population_registry.jsonl"] = [{"row": "a"}]
    with pytest.raises(ValueError):
        r.verify_parent(d)


@pytest.mark.parametrize(
    "path",
    [
        "data/T2.json",
        "data/T1.json",
        "objects/model.joblib",
        f"{r.STORE}/objects/fake.tfidf.json",
        "../outside.json",
        "audits/q1-apachejit-final-dataset-freeze/1.0.0/row_identity_provenance.jsonl.gz",
    ],
)
def test_unapproved_paths_denied_before_open(path, monkeypatch):
    monkeypatch.setattr(Path, "read_bytes", lambda *a: pytest.fail("Payload opened"))
    with pytest.raises(PermissionError):
        r.Reader().exact_read(path)
    with pytest.raises(PermissionError):
        r.Reader().transform(path)


def bound_request():
    bound = dict(
        partition="T1",
        project="apache/activemq",
        modality="CODE",
        scope_id="scope",
        schema=r.parent.SEMANTICS["CODE"],
        source_digest="frozen",
        identities=["a"],
        identity_partition_proof=True,
        safe_byte_route=True,
    )
    request = {
        k: v
        for k, v in bound.items()
        if k not in ["identities", "identity_partition_proof", "safe_byte_route"]
    }
    request.update(identity="a", fields=["la", "ld"], operation="READ_FEATURES")
    return bound, request


@pytest.mark.parametrize(
    "field,value",
    [
        ("partition", "T2"),
        ("partition", "UNKNOWN"),
        ("partition", "TRAIN"),
        ("identity", "unknown"),
        ("project", "apache/camel"),
        ("modality", "PROCESS"),
        ("scope_id", "other"),
        ("schema", ["ld", "la"]),
        ("source_digest", "changed"),
        ("fields", ["label"]),
        ("fields", ["prediction"]),
        ("fields", ["probability"]),
        ("fields", ["class"]),
        ("operation", "MODEL_QUERY"),
    ],
)
def test_route_binding_failure(field, value):
    bound, request = bound_request()
    assert r.validate_route(request, bound) == "BINDING_VALID_NOT_AUTHORIZATION"
    request[field] = value
    with pytest.raises(PermissionError):
        r.validate_route(request, bound)


@pytest.mark.parametrize("partition", ["T1", "T2", "UNKNOWN"])
def test_train_route_cannot_include_other_partition(partition):
    bound, request = bound_request()
    bound["partition"] = "TRAIN"
    request["partition"] = partition
    with pytest.raises(PermissionError):
        r.validate_route(request, bound)


@pytest.mark.parametrize("field", ["identity_partition_proof", "safe_byte_route"])
def test_no_boolean_proof_no_route(field):
    bound, request = bound_request()
    bound[field] = False
    with pytest.raises(PermissionError):
        r.validate_route(request, bound)


def test_even_valid_binding_does_not_grant_t1_read():
    bound, request = bound_request()
    assert r.validate_route(request, bound) == "BINDING_VALID_NOT_AUTHORIZATION"
    with pytest.raises(PermissionError):
        r.t1_payload_read(request, bound)


def test_malicious_label_schema_denied():
    bound, request = bound_request()
    bound["schema"] = ["label"]
    request["schema"] = ["label"]
    request["fields"] = ["label"]
    with pytest.raises(PermissionError):
        r.validate_route(request, bound)


@pytest.mark.parametrize("modality", ["CODE", "PROCESS"])
def test_numeric_semantics_preserved(modality):
    bound, request = bound_request()
    bound["modality"] = request["modality"] = modality
    bound["schema"] = request["schema"] = r.parent.SEMANTICS[modality]
    request["fields"] = bound["schema"][:1]
    assert r.validate_route(request, bound) == "BINDING_VALID_NOT_AUTHORIZATION"
    bound["schema"] = request["schema"] = ["bug_proxy"]
    with pytest.raises(PermissionError):
        r.validate_route(request, bound)


@pytest.mark.parametrize(
    "change", ["order", "vocabulary", "idf", "config", "dimension"]
)
def test_text_exact_metadata_required(evidence, change):
    rec = next(
        iter(
            evidence.docs[f"{r.parent.POP}/text_representation_registry.json"][
                "states"
            ].values()
        )
    )
    transform = evidence.transform(f"{r.STORE}/{rec['representation_object']['path']}")
    assert all(r.verify_text(rec, transform).values())
    if change == "order":
        transform["feature_order"].reverse()
    elif change == "vocabulary":
        transform["vocabulary"][transform["feature_order"][0]] = 2
    elif change == "idf":
        transform["idf"][0] += 1
    elif change == "config":
        transform["parameters"]["lowercase"] = False
    else:
        rec = copy.deepcopy(rec)
        rec["feature_count"] += 1
    with pytest.raises(ValueError):
        r.verify_text(rec, transform)


def test_reconstructed_and_no_promotion(result):
    deps = result["reconstructed_state_e1_dependency_ledger.jsonl"]
    assert len(deps) == 168 and {d["origin"] for d in deps} == {"RECONSTRUCTED"}
    assert all(
        not d["equivalence_rerun"] and not d["current_execution_authorized"]
        for d in deps
    )
    token = result["text_token_column_alignment.jsonl"]
    assert len(token) == 56
    assert all(d["e1_eligibility"] == "TEXT_E1_INELIGIBLE" for d in token)
    assert (
        result["scientific_representation_rematerialization_policy.json"]["label"]
        == "RECONSTRUCTED_REPRESENTATION"
    )


def test_complete_resolution_and_strength(result):
    for modality in ["code", "process", "text"]:
        assert len(result[modality + "_representation_resolution.jsonl"]) == 14
    for name in [
        "model_alignment_metadata_resolution",
        "provenance_strength_ledger",
        "reconstructed_state_e1_dependency_ledger",
        "representation_integrity_readiness",
    ]:
        rows = result[name + ".jsonl"]
        assert len(rows) == len({x["scope_id"] for x in rows}) == 168
    assert not any(row["advance"] for row in result["provenance_strength_ledger.jsonl"])
    proof = {k: "P4" for k in result["provenance_strength_ledger.jsonl"][0]["elements"]}
    assert r.strength_ready(proof)
    for key in proof:
        failed = dict(proof)
        failed[key] = "P2"
        assert not r.strength_ready(failed)
    assert not r.strength_ready({})


def test_partial_identities_not_background(result):
    ids = result["train_identity_registry.jsonl"]
    assert len(ids) == 80 and {d["partition"] for d in ids} == {"TRAIN"}
    assert all(not d["complete_identity_route"] for d in ids)
    assert result["train_identity_access_path.json"]["complete_route"] is False
    assert (
        result["scientific_representation_rematerialization_policy.json"][
            "background_sampling_executed"
        ]
        is False
    )


def test_all_scientific_counters_zero(result):
    c = result["governance_counters.json"]
    assert all(c[k] == 0 for k in r.parent.ZERO)
    assert c["T1_PREDICTION_ACCESS_COUNT"] == 0
    assert c["T2_STATE"] == "DENY_SEALED_REVIEWER_RESERVE"
    assert (
        c["historical_T1_predictive_access_count"]
        == c["historical_T1_predictive_scoring_count"]
        == 1
    )


def test_no_access_or_revalidation_authorized(result):
    c = result["t1_feature_value_access_authorization_contract.json"]
    assert not c["authorized"] and c["allowed_identity_set"] == []
    assert c["current"]["T1_FEATURE_VALUES"] == "DENY_IN_R1"
    assert (
        result["future_revalidation_policy.json"][
            "SPRINT56_3B_REVALIDATION_ELIGIBILITY"
        ]
        == "BLOCKED"
    )
    assert not result["future_revalidation_policy.json"]["started"]
    assert (
        result["scientific_representation_rematerialization_policy.json"][
            "background_summary_policy_change"
        ]
        == "NOT_AUTHORIZED"
    )


def test_manifest_deterministic_and_parent_immutable(evidence, result):
    first = r.parent.serialize(result)
    second = r.parent.serialize(copy.deepcopy(result))
    assert first == second
    for line in first["MANIFEST.sha256"].decode().splitlines():
        digest, name = line.split("  ", 1)
        assert r.sha(first[name]) == digest
    assert all(r.sha((r.ROOT / p).read_bytes()) == h for p, h in evidence.reads.items())


def test_no_scientific_libraries_or_methods():
    tree = ast.parse(Path(r.__file__).read_text())
    forbidden = {
        "predict",
        "predict_proba",
        "fit",
        "fit_transform",
        "transform",
        "train",
        "shap_values",
        "TreeExplainer",
        "load_model",
        "savefig",
        "score",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert all(
                a.name.split(".")[0]
                in {"argparse", "json", "math", "struct", "subprocess"}
                for a in node.names
            )
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            # Reader.transform parses a whitelisted JSON; never calls an estimator.
            if node.func.attr == "transform":
                assert (
                    isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "reader"
                )
            else:
                assert node.func.attr not in forbidden
