"""R4A finite resolution gates: only metadata and synthetic inputs."""

import ast
import copy

import pytest
from src.evaluation import q1_e1_remaining_train_source_transformation_resolution as r


@pytest.fixture(scope="module")
def evidence():
    return r.load_parent()


@pytest.fixture(scope="module")
def result(evidence):
    inherited, r3, parent, _ = evidence
    transforms, _ = r.inspect_transforms(
        inherited[f"{r.r4.r3.b.OUT}/e1_scope_universe.json"],
        inherited[f"{r.r4.r3.R1}/text_token_column_alignment.jsonl"],
    )
    return r.build(inherited, r3, parent, transforms)


def test_branch():
    r.r4.r3.branch_gate(r.r4.r3.b.BRANCH)
    with pytest.raises(ValueError):
        r.r4.r3.branch_gate("main")


@pytest.mark.parametrize(
    "field,value",
    [
        ("verdict", "PASS"),
        ("projects", 13),
        ("expected_train_rows", 56820),
        ("persisted_representations", 2),
        ("persisted_unique_train_rows", 80),
        ("compatible_e1_scopes", 3),
    ],
)
def test_parent_material_difference(evidence, field, value):
    d = copy.deepcopy(evidence[2])
    d["protocol_summary.json"][field] = value
    with pytest.raises(ValueError):
        r.verify_parent(d)


@pytest.mark.parametrize("key", list(r.r4.r3.b.ZERO))
def test_parent_zero_counters_required(evidence, key):
    d = copy.deepcopy(evidence[2])
    d["governance_counters.json"][key] = 1
    with pytest.raises(ValueError):
        r.verify_parent(d)


def proof():
    return dict(
        partition="TRAIN",
        classification="AUTHORITATIVE",
        project_known=True,
        membership_known=True,
        identity_deterministic=True,
        semantics_known=True,
        modality_correct=True,
        safe_route=True,
        transform_defined=True,
    )


@pytest.mark.parametrize(
    "key",
    [
        "project_known",
        "membership_known",
        "identity_deterministic",
        "semantics_known",
        "modality_correct",
        "safe_route",
        "transform_defined",
    ],
)
@pytest.mark.parametrize("value", [False, None, "true", 1])
def test_required_source_evidence(key, value):
    p = proof()
    p[key] = value
    assert r.source_admission(p) == "SOURCE_REJECTED"


@pytest.mark.parametrize("partition", ["T1", "T2", "TRAIN,T1", None])
def test_partition_rejected(partition):
    p = proof()
    p["partition"] = partition
    assert r.source_admission(p) == "SOURCE_REJECTED"


@pytest.mark.parametrize(
    "classification",
    ["DIAGNOSTIC_ONLY", "UNVERIFIED", "INADMISSIBLE", "PARTIAL_DIAGNOSTIC_ONLY", None],
)
def test_source_classes(classification):
    p = proof()
    p["classification"] = classification
    assert r.source_admission(p) == "SOURCE_REJECTED"


@pytest.mark.parametrize(
    "key",
    [
        "T1_dependency",
        "T2_dependency",
        "target_dependency",
        "performance_selection",
        "new_fit",
    ],
)
def test_forbidden_dependencies(key):
    p = proof()
    p[key] = True
    assert r.source_admission(p) == "SOURCE_REJECTED"


def test_source_gate_does_not_grant_io():
    assert r.source_admission(proof()) == "SOURCE_ADMITTED"
    p = proof()
    p["classification"] = "AUTHORITATIVE_WITH_LIMITATION"
    assert r.source_admission(p) == "SOURCE_ADMITTED_WITH_LIMITATION"


@pytest.mark.parametrize(
    "change", ["target", "future", "timestamp", "missing", "nonfinite"]
)
def test_process_future_or_unproven_rejected(change):
    p = dict(ancestral_proof=True, value_timestamp=10, prediction_timestamp=20)
    if change == "target":
        p["target_dependency"] = True
    if change == "future":
        p["future_information"] = True
    if change == "timestamp":
        p["value_timestamp"] = 21
    if change == "missing":
        del p["ancestral_proof"]
    if change == "nonfinite":
        p["value_timestamp"] = float("nan")
    with pytest.raises(ValueError):
        r.validate_temporal(p)


def test_ancestor_boundaries():
    assert r.validate_temporal(
        dict(ancestral_proof=True, value_timestamp=20, prediction_timestamp=20)
    )


@pytest.mark.parametrize(
    "key,value",
    [
        ("new_fit", True),
        ("project", "apache/camel"),
        ("vectorizer_scope", "CAMPAIGN_GLOBAL"),
        ("message_commit_link", False),
        ("state_verified", False),
        ("state_project", None),
    ],
)
def test_text_link_and_project_scope(key, value):
    p = dict(
        project=r.r4.PROJECT,
        state_project=r.r4.PROJECT,
        vectorizer_scope="PROJECT_SPECIFIC",
        message_commit_link=True,
        state_verified=True,
    )
    p[key] = value
    with pytest.raises((ValueError, PermissionError)):
        r.validate_text_binding(p)


@pytest.mark.parametrize("modality", ["CODE", "PROCESS"])
def test_modality_and_order_preserved(evidence, modality):
    contract = evidence[1]["code_process_semantic_contract.json"]
    names = contract["names"][modality]
    assert r.validate_feature_order(modality, names, contract)
    with pytest.raises(ValueError):
        r.validate_feature_order(modality, list(reversed(names)), contract)
    other = "PROCESS" if modality == "CODE" else "CODE"
    with pytest.raises(ValueError):
        r.validate_feature_order(modality, contract["names"][other], contract)


def complete_proof():
    p = proof()
    p["representation_state"] = "RECONSTRUCTED_REPRESENTATION"
    p.update(
        dict.fromkeys(
            [
                "row_registry",
                "column_registry",
                "transform_state",
                "source_digest",
                "matrix_digest",
                "schema_digest",
                "row_order_digest",
                "column_order_digest",
                "manifest_verified",
                "persistence_verified",
                "repeatability_verified",
                "numerical_integrity_verified",
                "partition_verified",
                "model_metadata_verified",
            ],
            True,
        )
    )
    return p


@pytest.mark.parametrize(
    "missing",
    [
        "row_registry",
        "column_registry",
        "transform_state",
        "source_digest",
        "matrix_digest",
        "schema_digest",
        "row_order_digest",
        "column_order_digest",
        "manifest_verified",
        "persistence_verified",
        "repeatability_verified",
        "numerical_integrity_verified",
        "partition_verified",
        "model_metadata_verified",
    ],
)
def test_no_eligibility_without_required_persistence(missing):
    p = complete_proof()
    del p[missing]
    with pytest.raises(ValueError):
        r.eligibility_gate(p)


@pytest.mark.parametrize("label", ["ORIGINAL", "ORIGINAL_REPRESENTATION", None])
def test_original_label_denied(label):
    p = complete_proof()
    p["representation_state"] = label
    with pytest.raises(ValueError):
        r.eligibility_gate(p)


def test_rejected_source_never_reconstructs():
    p = complete_proof()
    p["safe_route"] = False
    with pytest.raises(PermissionError):
        r.eligibility_gate(p)


def test_partial_reporting_all_42(result):
    rows = result["remaining_train_scope_matrix.jsonl"]
    assert len(rows) == 42 and len({(x["project"], x["modality"]) for x in rows}) == 42
    assert (
        sum(
            x["reconstruction_status"] == "PARENT_COMPLETE_WITH_LIMITATION"
            for x in rows
        )
        == 1
    )
    assert sum(x["q1_status"] == "Q1_E1_TRAIN_BLOCKED" for x in rows) == 41
    cov = result["combined_r4_r4a_train_coverage.json"]
    assert (
        cov["eligible_including_limited"] == 1
        and cov["projects_without_eligible_modality"] == 13
    )
    assert (
        cov["projects_with_1_modality"] == 1
        and cov["projects_with_2_modalities"] == cov["projects_with_3_modalities"] == 0
    )
    assert cov["new_rows"] == cov["new_R4A_representations"] == 0
    assert result["protocol_summary.json"]["verdict"] == r.VERDICT


@pytest.mark.parametrize("mutation", ["drop", "duplicate", "modality", "parent"])
def test_no_scope_disappears(result, mutation):
    rows = copy.deepcopy(result["remaining_train_scope_matrix.jsonl"])
    if mutation == "drop":
        rows.pop()
    if mutation == "duplicate":
        rows[0] = copy.deepcopy(rows[1])
    if mutation == "modality":
        rows[0]["modality"] = "FUSION"
    if mutation == "parent":
        for row in rows:
            row["reconstruction_status"] = "BLOCKED"
    with pytest.raises(ValueError):
        r.coverage(rows)


def test_parent_reference_only(result):
    reuse = result["parent_activemq_text_reuse.json"]
    assert reuse["rows"] == 3675 and reuse["columns"] == 2557
    assert not any(reuse[k] for k in ["regenerated", "copied", "overwritten"])
    links = result["r4a_representation_to_model_dependency.jsonl"]
    assert (
        len(links) == 168
        and sum(x["representation_id"] is not None for x in links) == 4
    )
    assert (
        result["r4a_train_row_registry.jsonl"]
        == result["r4a_train_column_registry.jsonl"]
        == result["r4a_representation_digest_registry.jsonl"]
        == []
    )


def test_all_vectorizers_verified_without_reconstruction(result):
    rows = result["text_vectorizer_scope_audit.jsonl"]
    assert len(rows) == 14 and len({x["project"] for x in rows}) == 14
    assert all(
        x["scope_matches_predictors"] and len(x["model_dependencies"]) == 4
        for x in rows
    )
    assert all(
        x["new_vectorizer_fit"] == "DENY" and not x["used_for_new_representation"]
        for x in rows
    )


def test_weak_coverage_keeps_t1_blocked(result):
    assert (
        result["r4a_scientific_coverage.json"]["classification"]
        == "Q1_TRAIN_COVERAGE_WEAK"
    )
    policy = result["future_t1_policy.json"]
    assert policy["T1_FEATURE_RECONSTRUCTION_PHASE"] == "BLOCKED_COVERAGE_WEAK"
    assert not policy["authorized"] and not policy["R5_started"]


def test_actual_counters_zero(result):
    counters = result["governance_counters.json"]
    for key in (
        *r.r4.r3.b.ZERO,
        "TRAIN_SOURCE_VALUE_READ_COUNT",
        "TRAIN_REPRESENTATION_RECONSTRUCTION_COUNT",
        "TRAIN_REPRESENTATION_PERSIST_COUNT",
        "TRAIN_RECONSTRUCTION_REPLAY_COUNT",
    ):
        assert counters[key] == 0
    assert (
        counters["historical_T1_predictive_access_count"]
        == counters["historical_T1_predictive_scoring_count"]
        == 1
    )
    assert counters["T2_STATE"] == "DENY_SEALED_REVIEWER_RESERVE"


def test_no_executable_scientific_calls():
    tree = ast.parse((r.ROOT / r.SOURCE).read_text())
    prohibited = {
        "predict",
        "predict_proba",
        "fit",
        "fit_transform",
        "transform",
        "transform_text",
        "read_source",
        "bounded_prefix",
        "shap_values",
        "savefig",
        "train",
        "calibrate",
        "load_model",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            assert node.func.attr not in prohibited


def test_parent_byte_identities_unchanged(evidence):
    parent = evidence[2]
    for name, h in parent["parent_integrity_after.json"]["metadata_sha256"].items():
        assert r.sha((r.ROOT / name).read_bytes()) == h


def test_deterministic_jsonl_and_manifest(result):
    rows = result["remaining_train_scope_matrix.jsonl"]
    raw = r.jsonl(rows)
    assert len(raw.splitlines()) == 42 and r.lines(raw) == rows
    first = r.r4.r3.b.serialize(
        {k: v for k, v in result.items() if not k.endswith(".jsonl")}
    )
    assert first == r.r4.r3.b.serialize(
        {k: v for k, v in result.items() if not k.endswith(".jsonl")}
    )
    for line in first["MANIFEST.sha256"].decode().splitlines():
        h, name = line.split("  ", 1)
        assert r.sha(first[name]) == h
