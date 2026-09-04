import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BLOCK7 = ROOT / "audits/q1-xai-reconstruction-execution/1.0.0"
PACKAGE = BLOCK7 / "dispositions/block7b_partial_eligibility/1.0.0"
PLAN = ROOT / "audits/q1-t1-confirmatory-execution/1.0.0/engine/engine_readiness.json"
POLICY = ROOT / "audits/q1-xai-reconstruction-equivalence-protocol/1.0.0/failure_partial_eligibility_policy.json"
ROOT_FAILURE = "apache/zeppelin|Logistic Regression|OOF|T|block=2"
FUSION_FAILURES = {
    "apache/zeppelin|Logistic Regression|FUSION_META|C+T",
    "apache/zeppelin|Logistic Regression|FUSION_META|P+T",
    "apache/zeppelin|Logistic Regression|FUSION_META|C+P+T",
}
ELIGIBLE = "G1_G3_ELIGIBLE_FOR_FUTURE_G4_REVIEW"
INELIGIBLE = "G3_INELIGIBLE_PROPAGATED_DEPENDENCY"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json(name: str):
    return json.loads((PACKAGE / name).read_text())


def _records():
    return [json.loads(line) for line in (PACKAGE / "scope_g1_g3_eligibility.jsonl").read_text().splitlines()]


def _dependencies(scope):
    modalities = scope["configuration"].split("+")
    prefix = f"{scope['project']}|{scope['algorithm']}"
    base = [f"{prefix}|FINAL_BASE|{modality}" for modality in modalities]
    if len(modalities) == 1:
        return base, [], None
    oof = [f"{prefix}|OOF|{modality}|block={block}" for modality in modalities for block in range(2, 10)]
    return base, oof, f"{prefix}|FUSION_META|{scope['configuration']}"


def test_all_392_scopes_appear_once_with_unique_linked_model_identities():
    records = _records()
    plan = json.loads(PLAN.read_text())["plan"]
    assert len(records) == len(plan) == 392
    assert len({row["model_identity_sha256"] for row in records}) == 392
    assert {
        (row["project"], row["algorithm"], row["configuration"], row["model_identity_sha256"])
        for row in records
    } == {
        (row["project"], row["algorithm"], row["configuration"], row["model_identity_sha256"])
        for row in plan
    }


def test_eligibility_is_rederived_from_exact_component_dependencies():
    frozen = json.loads((BLOCK7 / "g1_g2_g3_results.json").read_text())
    state = {row["logical_id"]: row["result"] for row in frozen["g3_results"]}
    for record in _records():
        base, oof, fusion = _dependencies(record)
        assert record["required_base_components"] == base
        assert record["required_oof_components"] == oof
        assert record["required_fusion_component"] == fusion
        required = base + oof + ([fusion] if fusion else [])
        assert not [logical_id for logical_id in required if logical_id not in state]
        failed = [logical_id for logical_id in required if state[logical_id] != "G3_PASS_DETERMINISTIC"]
        assert record["failed_dependency_logical_ids"] == failed
        assert record["eligibility_outcome"] == (INELIGIBLE if failed else ELIGIBLE)


def test_frozen_failures_and_historical_outcome_are_not_changed_or_rescued():
    frozen = json.loads((BLOCK7 / "g1_g2_g3_results.json").read_text())
    failures = {
        row["logical_id"]
        for row in frozen["g3_results"]
        if row["result"] == "G3_FAIL_NONDETERMINISTIC"
    }
    assert failures == {ROOT_FAILURE, *FUSION_FAILURES}
    assert frozen["g3_counts"] == {
        "G3_PASS_DETERMINISTIC": 1732,
        "G3_FAIL_NONDETERMINISTIC": 4,
    }
    assert frozen["outcome"] == "RECONSTRUCTION_NONDETERMINISTIC_STOP"
    summary = _json("partial_eligibility_summary.json")
    assert summary["historical_execution_outcome"] == "RECONSTRUCTION_NONDETERMINISTIC_STOP"
    assert summary["post_forensic_scope_disposition"] == (
        "PARTIAL_G1_G3_RECONSTRUCTION_READY_FOR_G4_REVIEW"
    )
    assert summary["eligibility_counts"] == {
        "eligible": 389,
        "ineligible": 3,
        "unresolved": 0,
        "g3_ineligible_root_failure": 0,
        "g3_ineligible_propagated_dependency": 3,
        "g1_g2_ineligible": 0,
    }


def test_only_exact_consuming_scopes_are_excluded():
    records = _records()
    affected = [row for row in records if row["eligibility_outcome"] != ELIGIBLE]
    assert {
        (row["project"], row["algorithm"], row["configuration"])
        for row in affected
    } == {
        ("apache/zeppelin", "Logistic Regression", "C+T"),
        ("apache/zeppelin", "Logistic Regression", "P+T"),
        ("apache/zeppelin", "Logistic Regression", "C+P+T"),
    }
    assert all(row["eligibility_outcome"] == INELIGIBLE for row in affected)
    assert all(ROOT_FAILURE in row["failed_dependency_logical_ids"] for row in affected)
    zeppelin_lr = {
        row["configuration"]: row
        for row in records
        if row["project"] == "apache/zeppelin" and row["algorithm"] == "Logistic Regression"
    }
    for configuration in ("C", "P", "T", "C+P"):
        assert zeppelin_lr[configuration]["eligibility_outcome"] == ELIGIBLE
    assert zeppelin_lr["T"]["required_oof_components"] == []
    assert zeppelin_lr["T"]["required_base_components"] == [
        "apache/zeppelin|Logistic Regression|FINAL_BASE|T"
    ]


def test_distributions_have_no_family_or_project_collateral_exclusion():
    records = _records()
    by_algorithm = Counter((row["algorithm"], row["eligibility_outcome"]) for row in records)
    assert by_algorithm[("Logistic Regression", ELIGIBLE)] == 95
    assert by_algorithm[("Logistic Regression", INELIGIBLE)] == 3
    for algorithm in ("Random Forest", "XGBoost", "LightGBM"):
        assert by_algorithm[(algorithm, ELIGIBLE)] == 98
        assert by_algorithm[(algorithm, INELIGIBLE)] == 0
    by_project = Counter((row["project"], row["eligibility_outcome"]) for row in records)
    assert by_project[("apache/zeppelin", ELIGIBLE)] == 25
    assert by_project[("apache/zeppelin", INELIGIBLE)] == 3
    assert all(
        by_project[(project, ELIGIBLE)] == 28
        for project in {row["project"] for row in records} - {"apache/zeppelin"}
    )


def test_governance_counts_and_original_manifests_remain_frozen():
    governance = json.loads((BLOCK7 / "governance_ledger.json").read_text())
    assert governance["original_t1_predictive_access_count"] == 1
    assert governance["original_t1_predictive_scoring_count"] == 1
    assert governance["t1_rerun_permitted"] is False
    assert governance["t1_model_query_count_block7"] == 0
    assert governance["t2_access_count_block7"] == 0
    assert governance["t2_state"] == "DENY_SEALED_REVIEWER_RESERVE"
    assert governance["g4_execution_count"] == 0
    assert governance["g5_execution_count"] == 0
    assert governance["xai_execution_count"] == 0
    assert _sha256(
        ROOT / "audits/q1-t1-confirmatory-execution/1.0.0/results/t1_prediction_evidence.jsonl.gz"
    ) == "eb4b6956b185e63cd322d92b8cdf96f53fcb09ef83b6a16f2334d660c6f5adc8"
    assert _sha256(ROOT / "audits/q1-t1-confirmatory-execution/1.0.0/MANIFEST.sha256") == (
        "f4f910a5144241b53f7f741ab2e49a5cb541abd8cff88f72c7a05ee30ecaeedf"
    )
    assert _sha256(BLOCK7 / "MANIFEST.sha256") == (
        "994a6f7aa8d1393904c605e0b5d65db6fcd39b9be55a1eb5219f899346b83d2e"
    )
    assert _sha256(BLOCK7 / "g1_g2_g3_results.json") == (
        "c07a0bd18d1c73e2cddae0ca829de3dd9e698b233d5d27f3f3f8928fb153f8a5"
    )
    assert _sha256(ROOT / "audits/q1-xai-reconstruction-equivalence-protocol/1.0.0/MANIFEST.sha256") == (
        "17341b4a585baab73118f21cc1056914326b61cba6751b16ff91bdf4b3dfc386"
    )
    assert _sha256(
        ROOT / "audits/q1-xai-reconstruction-equivalence-protocol/1.0.0/amendments/historical_design_rationale/1.0.0/MANIFEST.sha256"
    ) == "c9502cb1ec85d3053b8a972d61657038e66d04fb5e619b0fe08ed94d581c91bb"
    assert _sha256(BLOCK7 / "forensics/g3_failure_root_cause/1.0.0/MANIFEST.sha256") == (
        "a6f4bd5e5ec43f844860283aef6b3f21933728a5d0817773e7cb1fb742b866e7"
    )


def test_new_manifest_covers_only_new_disposition_artifacts():
    entries = []
    for line in (PACKAGE / "MANIFEST.sha256").read_text().splitlines():
        digest, name = line.split("  ", 1)
        entries.append(name)
        assert _sha256(PACKAGE / name) == digest
    assert entries == [
        "BLOCK7B_PARTIAL_ELIGIBILITY_REPORT.md",
        "affected_dependency_graph.json",
        "partial_eligibility_summary.json",
        "scope_g1_g3_eligibility.jsonl",
    ]
    assert json.loads(POLICY.read_text())["fail_closed_rules"]
