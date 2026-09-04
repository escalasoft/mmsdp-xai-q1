import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PARENT = ROOT / "audits/q1-xai-reconstruction-equivalence-protocol/1.0.0"
AMENDMENT = PARENT / "amendments/historical_design_rationale/1.0.0"
PARENT_MANIFEST_SHA256 = (
    "17341b4a585baab73118f21cc1056914326b61cba6751b16ff91bdf4b3dfc386"
)


def _read(name: str):
    return json.loads((AMENDMENT / name).read_text())


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_amendment_manifest_verifies_and_parent_manifest_is_unchanged():
    entries = []
    for line in (AMENDMENT / "MANIFEST.sha256").read_text().splitlines():
        digest, name = line.split("  ", 1)
        entries.append(name)
        assert _sha256(AMENDMENT / name) == digest
    assert len(entries) == 5
    assert _sha256(PARENT / "MANIFEST.sha256") == PARENT_MANIFEST_SHA256
    linkage = _read("parent_linkage_and_governance.json")
    assert linkage["parent"]["manifest_modified"] is False
    assert linkage["parent"]["manifest_entry_count"] == 12


def test_frozen_tolerances_gates_inputs_and_failure_rules_remain_unchanged():
    expected = {
        "numerical_tolerance_policy.json": (
            "62fd3780c94c6a69bfc036bdd4b567409ffc46c8c892a807b221f5d40d0eb336"
        ),
        "equivalence_gate_hierarchy.json": (
            "e451edc38b5f2a91f4b00d475ca902a2ae13f319933519b177f607cdd54b3545"
        ),
        "frozen_input_provenance_contract.json": (
            "6410ff45413b0121ff1d73d665388b8ea40fe897ac3e23aad135a4a4fe1d2f9e"
        ),
        "deterministic_execution_contract.json": (
            "2130f60bd3d3dd2e35f2409b5110ba015bdc118ff08c3018c733aa62cd78c0d7"
        ),
        "failure_partial_eligibility_policy.json": (
            "cfa869239109d9ca12195ef62c99d454a8ae2083f40c55c82510c8cf8b084bf8"
        ),
    }
    assert all(_sha256(PARENT / name) == digest for name, digest in expected.items())
    tolerance = json.loads((PARENT / "numerical_tolerance_policy.json").read_text())
    assert tolerance["row_level_probability_equivalence"][
        "maximum_absolute_error"
    ] == 1e-12
    assert tolerance["row_level_probability_equivalence"][
        "maximum_relative_error"
    ] == 1e-10


def test_historical_claims_are_typed_and_unsupported_intent_is_disclaimed():
    rationale = _read("historical_design_rationale.json")
    assert set(rationale["claim_classes"]) == {
        "HISTORICALLY_EVIDENCED",
        "PROTOCOL_INTERPRETATION",
        "CURRENT_LIMITATION_CLASSIFICATION",
        "PROSPECTIVE_REMEDIATION",
    }
    assert rationale["historical_intent_not_proven"] == [
        "Non-persistence was an intentional omission.",
        "Non-persistence was a methodological advantage.",
        "Non-persistence improved predictive performance.",
        "Persistence was considered unnecessary or undesirable.",
    ]
    assert rationale["block6_reopened_or_reinterpreted"] is False


def test_limitation_and_reconstructed_state_isolation_are_fail_closed():
    limitation = _read("limitation_classification.json")
    assert limitation["classification"] == (
        "POST_CONFIRMATORY_EXECUTABLE_STATE_PERSISTENCE_LIMITATION"
    )
    assert limitation["limitation_resolved"] is False
    assert limitation["aggregate_metric_similarity_sufficient"] is False
    isolation = limitation["reconstructed_state_isolation"]
    assert isolation["successful_label"] == "RECONSTRUCTED_EQUIVALENCE_VERIFIED"
    assert isolation["prohibited_label"] == "ORIGINAL_SPRINT54_FITTED_STATE"
    assert isolation["required_namespace"] == (
        "NEW_PROVENANCE_SEPARATED_RECONSTRUCTION_NAMESPACE"
    )


def test_sprint54_evidence_governance_and_zero_execution_remain_exact():
    linkage = _read("parent_linkage_and_governance.json")
    evidence = linkage["sprint54_evidence"]
    assert _sha256(
        ROOT
        / "audits/q1-t1-confirmatory-execution/1.0.0/results/t1_prediction_evidence.jsonl.gz"
    ) == evidence["t1_prediction_evidence_sha256"]
    assert _sha256(
        ROOT / "audits/q1-t1-confirmatory-execution/1.0.0/results/MANIFEST.sha256"
    ) == evidence["results_manifest_sha256"]
    assert evidence["modified"] is False
    assert linkage["governance"] == {
        "t1_predictive_access_count": 1,
        "t1_predictive_scoring_count": 1,
        "t1_rerun_permitted": False,
        "t2_predictive_access_count": 0,
        "t2_state": "DENY_SEALED_REVIEWER_RESERVE",
        "xai_execution_count": 0,
        "reconstructed_model_count": 0,
        "trained_or_refitted_model_count": 0,
        "g4_execution_count": 0,
        "g5_execution_count": 0,
    }
    assert linkage["amendment_authorizes_execution"] is False
    assert linkage["stop_state"] == "DOCUMENTATION_VALIDATED_STOP_BEFORE_BLOCK7"


def test_manuscript_statement_preserves_four_reproducibility_layers():
    statement = (AMENDMENT / "manuscript_traceability_statement.md").read_text()
    normalized = statement.lower()
    for heading in (
        "confirmatory evidence reproducibility",
        "executable fitted-state reproducibility",
        "reconstruction-equivalence verification",
        "explanation/XAI reproducibility",
    ):
        assert heading.lower() in normalized
    assert "No reconstruction or equivalence verification has yet occurred" in statement
    assert "intentional methodological choice or best practice" in statement
