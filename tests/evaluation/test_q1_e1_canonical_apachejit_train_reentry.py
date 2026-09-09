"""Finite re-entry tests using metadata and synthetic source rows only."""

import ast
import copy
import json

import pytest
from src.evaluation import q1_e1_canonical_apachejit_train_reentry as r


@pytest.fixture(scope="module")
def parents():
    return r.load_parent()


def official():
    return dict(
        doi=r.DOI,
        version="v2",
        archive_sha256_from_frozen_lineage=r.ARCHIVE,
        published_balanced_train_replaces_campaign=False,
        official_record="https://zenodo.org/records/5907847",
    )


def test_branch():
    r.r4.r3.branch_gate(r.r4.r3.b.BRANCH)
    with pytest.raises(ValueError):
        r.r4.r3.branch_gate("main")


@pytest.mark.parametrize(
    "field,value",
    [
        ("verdict", "PASS"),
        ("project_modalities", 41),
        ("projects", 13),
        ("combined_eligible_with_limitation", 2),
        ("new_representations", 1),
    ],
)
def test_parent_required(parents, field, value):
    d = copy.deepcopy(parents[3])
    d["protocol_summary.json"][field] = value
    with pytest.raises(ValueError):
        r.validate_parent(d)


@pytest.mark.parametrize(
    "phase,tier",
    [
        ("web_search", 1),
        ("primary_inventory", 5),
        ("targeted_fallback_reconciliation", 0),
    ],
)
def test_no_lower_tiers_or_broad_rounds(phase, tier):
    with pytest.raises(PermissionError):
        r.SearchBudget().enter(phase, tier)


def test_exact_round_budget_and_termination():
    b = r.SearchBudget()
    with pytest.raises(PermissionError):
        b.enter("targeted_fallback_reconciliation", 3)
    b.enter("primary_inventory", 1)
    with pytest.raises(PermissionError):
        b.enter("primary_inventory", 2)
    with pytest.raises(ValueError):
        b.close()
    b.enter("targeted_fallback_reconciliation", 3)
    assert b.close() == "CANONICAL_SOURCE_RECOVERY_SEARCH_TERMINATES_AT_R4B"
    with pytest.raises(PermissionError):
        b.enter("targeted_fallback_reconciliation", 4)


@pytest.mark.parametrize(
    "field,value",
    [
        ("doi", "wrong"),
        ("version", "v1"),
        ("archive_sha256_from_frozen_lineage", "0" * 64),
        ("published_balanced_train_replaces_campaign", True),
        ("official_record", "https://unverified.example"),
    ],
)
def test_official_identity_and_campaign_membership(field, value):
    p = official()
    p[field] = value
    with pytest.raises(ValueError):
        r.validate_official(p)


@pytest.mark.parametrize("field", ["buggy", "fix", "label", "target"])
def test_labels_excluded(field):
    row = {"la": 1, field: True}
    with pytest.raises(ValueError):
        r.guard_fields(row, ["la"])


def test_project_qualified_commit_matching():
    candidates = [("a", "1234567" + "a" * 33), ("b", "1234567" + "b" * 33)]
    assert r.resolve_commit("a", "1234567", candidates) == candidates[0][1]
    with pytest.raises(ValueError):
        r.resolve_commit("a", "1234567", candidates + [("a", "1234567" + "c" * 33)])
    with pytest.raises(ValueError):
        r.resolve_commit("c", "1234567", candidates)
    with pytest.raises(ValueError):
        r.resolve_commit("", candidates[0][1], candidates)


@pytest.mark.parametrize("partition", ["T1", "T2", None, "TRAIN,T1"])
def test_no_prohibited_partition(partition):
    with pytest.raises(PermissionError):
        r.source_gate(r.r4.PROJECT, partition, "CODE_CANONICAL_PREFIX")


@pytest.mark.parametrize(
    "kind", ["labels", "T1_FEATURES", "T2", "predictor", "SHAP", "PROCESS_UNPROVEN"]
)
def test_no_other_payload_route(kind):
    with pytest.raises(PermissionError):
        r.source_gate(r.r4.PROJECT, "TRAIN", kind)


def test_only_admitted_project():
    with pytest.raises(PermissionError):
        r.source_gate("apache/camel", "TRAIN", "CODE_CANONICAL_PREFIX")


def direct():
    return dict.fromkeys(
        [
            "canonical_identity_exact",
            "source_snapshot_admitted",
            "frozen_transform_executable",
            "fitting_authorized_or_not_required",
            "persistence_verified",
        ],
        True,
    )


@pytest.mark.parametrize(
    "key",
    [
        "canonical_identity_exact",
        "source_snapshot_admitted",
        "frozen_transform_executable",
        "fitting_authorized_or_not_required",
        "persistence_verified",
    ],
)
@pytest.mark.parametrize("value", [False, None, "true"])
def test_optional_reconstruction_all_guards(key, value):
    p = direct()
    p[key] = value
    with pytest.raises(PermissionError):
        r.direct_reconstruction_gate(p)


@pytest.mark.parametrize("key", ["T1", "T2", "model_query", "new_vectorizer_fit"])
def test_direct_path_no_prohibited_action(key):
    p = direct()
    p[key] = True
    with pytest.raises(PermissionError):
        r.direct_reconstruction_gate(p)


def row():
    return dict(
        project=r.r4.PROJECT,
        partition="TRAIN",
        commit_identity="a" * 40,
        row_identifier="b" * 64,
        scientific_fields={x: 1 for x in r.r4.r3.b.SEMANTICS["CODE"]},
    )


def test_snapshot_persistence_and_no_original_claim(tmp_path):
    item = r.snapshot_payload(
        r.r4.PROJECT, "CODE", [row()], "c" * 64, {"synthetic": True}, tmp_path
    )
    base = tmp_path / item["path"]
    assert r.verify_snapshot(base)
    assert item["state"] == "PROSPECTIVE_CANONICAL_SOURCE_SNAPSHOT"
    assert (
        json.loads((base / "creation_contract.json").read_text())[
            "original_Sprint54_claim"
        ]
        is False
    )
    with pytest.raises(FileExistsError):
        r.snapshot_payload(r.r4.PROJECT, "CODE", [row()], "c" * 64, {}, tmp_path)


@pytest.mark.parametrize(
    "missing",
    [
        "source.jsonl",
        "schema.json",
        "row_order.jsonl",
        "creation_contract.json",
        "runtime.json",
        "snapshot_identity.json",
        "MANIFEST.sha256",
    ],
)
def test_missing_snapshot_components_fail(tmp_path, missing):
    item = r.snapshot_payload(r.r4.PROJECT, "CODE", [row()], "c" * 64, {}, tmp_path)
    base = tmp_path / item["path"]
    (base / missing).unlink()
    with pytest.raises((ValueError, FileNotFoundError)):
        r.verify_snapshot(base)


@pytest.mark.parametrize("digest", ["", None, "wrong", "0" * 63])
def test_source_digest_mandatory(tmp_path, digest):
    with pytest.raises((ValueError, TypeError)):
        r.snapshot_payload(r.r4.PROJECT, "CODE", [row()], digest, {}, tmp_path)


@pytest.mark.parametrize("change", ["label", "modality", "partition", "duplicate"])
def test_bad_scientific_rows_rejected(tmp_path, change):
    rows = [row()]
    if change == "label":
        rows[0]["scientific_fields"]["buggy"] = True
    if change == "modality":
        rows[0]["scientific_fields"]["aexp"] = 3
    if change == "partition":
        rows[0]["partition"] = "T2"
    if change == "duplicate":
        rows = rows * 2
    with pytest.raises(ValueError):
        r.snapshot_payload(r.r4.PROJECT, "CODE", rows, "c" * 64, {}, tmp_path)


def matrix():
    return [
        dict(
            project=f"p{i}",
            modality=m,
            representation_ready=i == 0 and m == "TEXT",
            closure=r.CLOSED,
        )
        for i in range(14)
        for m in ["CODE", "PROCESS", "TEXT"]
    ]


@pytest.mark.parametrize("change", ["drop", "duplicate", "not_closed", "performance"])
def test_every_scope_closed_and_no_performance_selection(change):
    rows = matrix()
    if change == "drop":
        rows.pop()
    if change == "duplicate":
        rows[0] = rows[1].copy()
    if change == "not_closed":
        rows[0]["closure"] = "KEEP_SEARCHING"
    if change == "performance":
        rows[0]["performance_selection"] = True
    with pytest.raises(ValueError):
        r.freeze_decision(rows)


def test_article_route_and_search_closure():
    d = r.freeze_decision(matrix())
    assert d["article_route"] == r.ARTICLE
    assert (
        d["fallback"] == "E1_ILLUSTRATIVE_ONLY_NOT_PRIMARY" and d["search_terminated"]
    )


def test_process_temporal_proof_still_required():
    with pytest.raises(ValueError):
        r.r4a.validate_temporal(
            dict(ancestral_proof=False, value_timestamp=1, prediction_timestamp=2)
        )
    with pytest.raises(ValueError):
        r.r4a.validate_temporal(
            dict(ancestral_proof=True, value_timestamp=3, prediction_timestamp=2)
        )


def test_no_model_or_xai_execution():
    tree = ast.parse((r.ROOT / r.SOURCE).read_text())
    forbidden = {
        "predict",
        "predict_proba",
        "fit",
        "fit_transform",
        "transform_text",
        "shap_values",
        "savefig",
        "train",
        "calibrate",
        "load_model",
        "new_vectorizer",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            assert node.func.attr not in forbidden


def test_parent_r4a_unchanged(parents):
    before = parents[3]["preflight.json"]["parent_hashes"]
    for name, h in before.items():
        assert r.sha((r.ROOT / name).read_bytes()) == h


def test_execution_artifacts_if_present():
    out = r.ROOT / r.OUT
    if not (out / "protocol_summary.json").exists():
        pytest.skip("Execution not performed yet")
    s = json.loads((out / "protocol_summary.json").read_text())
    assert s["verdict"] == r.VERDICT and s["new_representations"] == 0
    entries = r.r4a.lines(
        (out / "canonical_source_snapshot_registry.jsonl").read_bytes()
    )
    assert len(entries) == 2 and all(x["row_count"] == 3675 for x in entries)
    for x in entries:
        r.verify_snapshot(out / x["path"])
    rows = r.r4a.lines((out / "r4b_final_scientific_reentry_matrix.jsonl").read_bytes())
    assert len(rows) == 42 and sum(x["representation_ready"] for x in rows) == 1
    c = json.loads((out / "governance_counters.json").read_text())
    for k in r.r4.r3.b.ZERO:
        assert c[k] == 0
    assert (
        c["TRAIN_CANONICAL_SOURCE_READ_COUNT"] == 7350
        and c["TRAIN_SOURCE_SNAPSHOT_PERSIST_COUNT"] == 2
    )
    assert (
        json.loads((out / "article_timeline_route_decision.json").read_text())[
            "R4C_recommended"
        ]
        is False
    )
