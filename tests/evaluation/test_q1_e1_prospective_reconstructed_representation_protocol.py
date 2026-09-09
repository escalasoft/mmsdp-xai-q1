"""Protocol-only validation using metadata and synthetic byte receipts."""

import ast
import copy
from pathlib import Path

import pytest
from src.evaluation import q1_e1_prospective_reconstructed_representation_protocol as r


@pytest.fixture(scope="module")
def evidence():
    return r.Reader().load()


@pytest.fixture(scope="module")
def protocol(evidence):
    return r.compile_protocol(evidence)


def test_branch():
    r.branch_gate(r.b.BRANCH)
    with pytest.raises(ValueError):
        r.branch_gate("main")


@pytest.mark.parametrize("package", list(r.PINS))
@pytest.mark.parametrize(
    "field,value", [("verdict", "PASS"), ("candidate_scopes", 167)]
)
def test_material_parent_changes_stop(evidence, package, field, value):
    d = copy.deepcopy(evidence)
    d[f"{package}/protocol_summary.json"][field] = value
    with pytest.raises(ValueError):
        r.verify_parents(d)


@pytest.mark.parametrize(
    "key",
    list(r.b.ZERO)
    + [
        "historical_T1_predictive_access_count",
        "historical_T1_predictive_scoring_count",
        "T2_STATE",
    ],
)
def test_parent_counter_changes_stop(evidence, key):
    d = copy.deepcopy(evidence)
    d[f"{r.R2}/governance_counters.json"][key] = 2
    with pytest.raises(ValueError):
        r.verify_parents(d)


@pytest.mark.parametrize(
    "path",
    ["data/train.csv", "T1.csv", "T2.csv", "model.pkl", "../source", "arbitrary.json"],
)
def test_read_boundary_precedes_io(path, monkeypatch):
    monkeypatch.setattr(Path, "read_bytes", lambda _: pytest.fail("Forbidden IO"))
    with pytest.raises(PermissionError):
        r.Reader().read(path)


@pytest.mark.parametrize(
    "file,key,value",
    [
        ("predictive_xai_evidence_boundary.json", "SPRINT54_PREDICTIVE_BLOCK", "OPEN"),
        (
            "historical_recovery_closure.json",
            "HISTORICAL_EXACT_E1_REPRESENTATION_RECOVERY",
            "OPEN",
        ),
        ("terminology_contract.json", "predictor_state", "ORIGINAL"),
        (
            "terminology_contract.json",
            "representation_state",
            "ORIGINAL_REPRESENTATION",
        ),
        ("future_execution_policy.json", "authorized", True),
        ("persistence_at_creation_contract.json", "failure", "CONTINUE"),
    ],
)
def test_policy_mutation_denied(protocol, file, key, value):
    f = copy.deepcopy(protocol)
    f[file][key] = value
    with pytest.raises(ValueError):
        r.validate_policy(f)


@pytest.mark.parametrize("artifact", r.ALL_ARTIFACTS)
def test_every_future_artifact_required(protocol, artifact):
    f = copy.deepcopy(protocol)
    f["future_ml_xai_artifact_persistence_contract.json"]["required"].remove(artifact)
    with pytest.raises(ValueError):
        r.validate_policy(f)


@pytest.mark.parametrize("artifact", r.REPRESENTATION + r.TEXT_EXTRA)
def test_missing_persisted_object_stops(artifact):
    objects = {k: b"synthetic receipt" for k in r.REPRESENTATION + r.TEXT_EXTRA}
    digests = {k: r.sha(v) for k, v in objects.items()}
    del objects[artifact]
    del digests[artifact]
    with pytest.raises(ValueError, match="STOP"):
        r.persistence_gate(objects, digests, "TEXT")


@pytest.mark.parametrize("modality", ["CODE", "PROCESS", "TEXT"])
def test_valid_receipts_never_authorize_xai(modality):
    keys = r.REPRESENTATION + (r.TEXT_EXTRA if modality == "TEXT" else [])
    objects = {k: b"synthetic receipt" for k in keys}
    digests = {k: r.sha(v) for k, v in objects.items()}
    assert (
        r.persistence_gate(objects, digests, modality)
        == "PERSISTENCE_VERIFIED_NOT_XAI_AUTHORIZATION"
    )
    objects["representation_matrix"] = b"corrupted synthetic receipt"
    with pytest.raises(ValueError, match="STOP"):
        r.persistence_gate(objects, digests, modality)


def request():
    return dict(
        partition="TRAIN",
        destination=r.NAMESPACE + "/1.0.0/project/TRAIN",
        **dict.fromkeys(
            [
                "source_digest_verified",
                "safe_identity_route",
                "partition_contract_verified",
                "semantics_verified",
                "frozen_transform_verified",
                "reconstructed_model_equivalence_verified",
            ],
            True,
        ),
    )


@pytest.mark.parametrize(
    "field",
    [
        "source_digest_verified",
        "safe_identity_route",
        "partition_contract_verified",
        "semantics_verified",
        "frozen_transform_verified",
        "reconstructed_model_equivalence_verified",
    ],
)
@pytest.mark.parametrize("value", [None, False, "true", 1])
def test_source_admission_requires_literal_proof(field, value):
    q = request()
    q[field] = value
    with pytest.raises(ValueError):
        r.validate_reconstruction_request(q)


@pytest.mark.parametrize("partition", ["T1", "T2", "TRAIN,T1", None])
def test_train_cannot_expand_partition(partition):
    q = request()
    q["partition"] = partition
    with pytest.raises(PermissionError):
        r.validate_reconstruction_request(q)


@pytest.mark.parametrize(
    "key", ["labels", "t2", "performance_selection", "new_fit", "new_vectorizer"]
)
def test_forbidden_source_dependencies(key):
    q = request()
    q[key] = True
    with pytest.raises(PermissionError):
        r.validate_reconstruction_request(q)


@pytest.mark.parametrize(
    "destination",
    [
        "audits/sprint54/1.0.0/x",
        r.NAMESPACE,
        r.NAMESPACE + "/x/y",
        r.NAMESPACE + "/1.0.0/../old",
        "/" + r.NAMESPACE + "/1.0.0/x",
        r.NAMESPACE + "//1.0.0/x",
    ],
)
def test_immutable_namespace(destination):
    with pytest.raises(PermissionError):
        r.validate_destination(destination)


def test_preflight_does_not_authorize():
    assert (
        r.validate_reconstruction_request(request())
        == "PREFLIGHT_VALID_NOT_EXECUTION_AUTHORIZATION"
    )


def test_complete_protocol_and_unchanged_parents(protocol, evidence):
    reader = r.Reader()
    reader.load()
    before = reader.reads.copy()
    assert r.validate_policy(protocol)
    assert protocol["protocol_summary.json"]["scope_count"] == 168
    assert (
        protocol["protocol_summary.json"]["currently_admitted_execution_scopes"] == []
    )
    serialized = r.b.serialize(protocol)
    assert serialized == r.b.serialize(r.compile_protocol(evidence))
    for line in serialized["MANIFEST.sha256"].decode().splitlines():
        digest, name = line.split("  ", 1)
        assert r.sha(serialized[name]) == digest
    for p, h in before.items():
        assert r.sha((r.ROOT / p).read_bytes()) == h


def test_disclosures_and_conditional_claims(protocol):
    reviewer = protocol["reviewer_artifact_persistence_response.json"]
    assert reviewer["exact_historical_human_reason"] == "UNKNOWN_NOT_DOCUMENTED"
    assert (
        "No representations have been reconstructed under R3"
        in reviewer["current_response"]
    )
    assert "intentionally" not in reviewer["current_response"]
    assert protocol["manuscript_transparency_contract.json"]["final_wording"] is False
    assert (
        protocol["future_claims.json"]["status"] == "CONDITIONAL_NOT_CURRENT_FINDINGS"
    )
    assert len(protocol["prohibited_claims.json"]["claims"]) == 7
    assert "SHAP proves causality" in protocol["prohibited_claims.json"]["claims"]
    assert protocol["threats_to_validity.json"]["future_mitigations_executed"] is False


def test_future_contract_completeness(protocol):
    assert len(protocol["q1_defensibility_assessment.json"]["dimensions"]) == 15
    assert len(protocol["replication_package_contract.json"]["required"]) == 12
    assert len(protocol["runtime_persistence_contract.json"]["required"]) == 16
    assert (
        protocol["future_model_persistence_contract.json"][
            "predictions_only_completion"
        ]
        is False
    )
    assert (
        protocol["future_xai_persistence_contract.json"]["figure_without_source_tables"]
        == "DENY"
    )
    assert (
        protocol["persistence_at_creation_contract.json"][
            "downstream_XAI_before_verification"
        ]
        is False
    )
    assert (
        protocol["atomic_write_immutability_contract.json"]["replace_existing"] is False
    )
    assert protocol["t1_reconstruction_policy.json"]["authorized"] is False
    assert (
        protocol["t1_reconstruction_policy.json"]["T1_LABELS_FOR_E1_SELECTION"]
        == "DENY"
    )
    assert (
        protocol["text_reconstruction_policy.json"]["new_vectorizer_fit_authorized"]
        is False
    )
    assert (
        protocol["code_process_semantic_contract.json"]["feature_migration"] == "DENY"
    )
    assert (
        protocol["prospective_e1_design.json"]["performance_based_reselection"] is False
    )
    assert protocol["future_execution_policy.json"]["started"] is False


def test_literature_is_bounded(protocol):
    sources = protocol["literature_evidence_registry.json"]["sources"]
    assert len(sources) == 4
    assert all(s["url"].startswith("https://") for s in sources)
    assert "Our methodological inference is conditional" in r.literature_markdown()


def test_all_scientific_counters_zero(protocol):
    counters = protocol["governance_counters.json"]
    for key in (*r.b.ZERO, "REPRESENTATION_RECONSTRUCTION_COUNT"):
        assert counters[key] == 0
    assert (
        counters["historical_T1_predictive_access_count"]
        == counters["historical_T1_predictive_scoring_count"]
        == 1
    )
    assert counters["T2_STATE"] == "DENY_SEALED_REVIEWER_RESERVE"


def test_no_scientific_execution_dependencies():
    tree = ast.parse((r.ROOT / r.SOURCE).read_text())
    banned = {
        "numpy",
        "scipy",
        "sklearn",
        "shap",
        "pickle",
        "joblib",
        "xgboost",
        "lightgbm",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert not any(a.name.split(".")[0] in banned for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert (node.module or "").split(".")[0] not in banned
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            assert node.func.attr not in {
                "predict",
                "predict_proba",
                "fit",
                "fit_transform",
                "shap_values",
                "train",
                "calibrate",
                "savefig",
                "train_matrix",
            }
