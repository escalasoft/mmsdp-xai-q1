import copy
import inspect
from pathlib import Path

import pytest

import evaluation.q1_t1_confirmatory_execution as execution
from evaluation.q1_t1_confirmatory_execution import (
    ALGORITHMS,
    CONFIGURATIONS,
    EVIDENCE_FIELDS,
    EXPECTED_AMENDMENT_SHA256,
    EXPECTED_AUTHORIZATION_SHA256,
    EXPECTED_EVIDENCE_ROWS,
    EXPECTED_SPRINT53_MANIFEST_SHA256,
    EXPECTED_T1_HASH,
    EXPECTED_T1_ROWS,
    EXPECTED_T2_HASH,
    EXPECTED_T2_ROWS,
    INTEGRITY_CHECKS,
    ConfirmatoryExecutionError,
    _manifest_entries,
    _predict_t1,
    _validate_amendment_payload,
    build_execution_plan,
    execute_one_shot,
    file_sha256,
    load_json,
    near_perfect_flags,
    prepare_engine,
    structural_memberships,
    verify_authorization,
    verify_contracts,
    verify_manifest,
)

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def engine_components():
    authorization = verify_authorization(ROOT)
    return {
        "authorization": authorization,
        "plan": build_execution_plan(ROOT, authorization),
        "memberships": structural_memberships(ROOT),
    }


def test_block2_authorization_is_intact_and_not_accessed():
    record = verify_authorization(ROOT)
    assert record["scientific_authorization"]["authorization_mode"] == (
        "ONE_SHOT_CONFIRMATORY_EVALUATION"
    )
    assert record["heldout_identity_contract"]["t1"]["access_state"] == (
        "AUTHORIZED_NOT_YET_ACCESSED"
    )
    assert record["heldout_identity_contract"]["t1"]["predictive_access_count"] == 0
    assert record["heldout_identity_contract"]["t2"]["access_state"] == "DENY"
    assert record["heldout_identity_contract"]["t2"]["predictive_access_count"] == 0
    assert record["discrepancies"] == []


def test_complete_28_scope_and_392_project_scope_plan(engine_components):
    plan = engine_components["plan"]
    assert len(plan) == 392
    assert {(row["algorithm"], row["configuration"]) for row in plan} == {
        (algorithm, configuration)
        for algorithm in ALGORITHMS
        for configuration in CONFIGURATIONS
    }
    assert EXPECTED_EVIDENCE_ROWS == EXPECTED_T1_ROWS * 28


def test_frozen_calibration_mapping(engine_components):
    plan = engine_components["plan"]
    counts = {
        state: sum(row["calibration"]["state"] == state for row in plan)
        for state in ("RAW", "ISOTONIC")
    }
    assert counts == {"RAW": 378, "ISOTONIC": 14}
    calibrated = [row for row in plan if row["calibration"]["state"] != "RAW"]
    assert len(calibrated) == 14
    assert all(
        row["algorithm"] == "LightGBM" and row["configuration"] == "P"
        for row in calibrated
    )
    assert all(row["calibration"]["fitting_during_t1"] is False for row in calibrated)
    assert all(row["calibration"]["selection_using_t1"] is False for row in calibrated)


def test_fixed_threshold_for_every_scope(engine_components):
    assert {row["threshold"] for row in engine_components["plan"]} == {0.5}


def test_t1_only_authorization_and_t2_denial(engine_components):
    memberships = engine_components["memberships"]
    assert memberships["counts"]["T1"] == EXPECTED_T1_ROWS
    assert memberships["counts"]["T2"] == EXPECTED_T2_ROWS
    assert memberships["identity_hashes"] == {
        "T1": EXPECTED_T1_HASH,
        "T2": EXPECTED_T2_HASH,
    }
    assert memberships["predictive_access"] == {"T1": "DENY", "T2": "DENY"}
    authorization = engine_components["authorization"]
    assert (
        authorization["heldout_identity_contract"]["t1"]["predictive_access_count"] == 0
    )
    assert (
        authorization["heldout_identity_contract"]["t2"]["predictive_access_count"] == 0
    )


def test_no_t1_fitting_or_selection_path(engine_components):
    plan = engine_components["plan"]
    assert all(row["training_partition"] == "TRAIN" for row in plan)
    assert all(row["t1_used_for_fit_or_selection"] is False for row in plan)
    assert all(
        row["development_validation_used_for_model_selection"] is False for row in plan
    )
    with pytest.raises(ConfirmatoryExecutionError, match="accepts T1 only"):
        _predict_t1(object(), [{"partition": "T2"}], "C")


def test_evidence_schema_is_complete_and_xai_remains_disabled(engine_components):
    assert {
        "row_identifier",
        "project",
        "benchmark_defined_observed_label",
        "raw_predicted_probability",
        "final_frozen_probability",
        "fixed_threshold_prediction",
        "model_identity_sha256",
        "model_provenance",
        "calibration_provenance",
        "execution_identifier",
    } <= set(EVIDENCE_FIELDS)
    authorization = engine_components["authorization"]
    assert authorization["xai_contract"]["access_state"] == "DENY"
    assert authorization["xai_contract"]["execution_count"] == 0
    assert (
        authorization["scientific_authorization"]["t1_predictive_execution_started"]
        is False
    )


def test_deterministic_execution_identity_and_plan(engine_components):
    authorization = verify_authorization(ROOT)
    second = build_execution_plan(ROOT, authorization)
    assert (
        authorization["execution_identifier"]
        == (engine_components["authorization"]["execution_identifier"])
    )
    assert second == engine_components["plan"]


def test_late_fusion_contract_is_preserved(engine_components):
    multimodal = [
        row for row in engine_components["plan"] if "+" in row["configuration"]
    ]
    assert len(multimodal) == 224
    assert all(
        row["late_fusion"]["architecture"] == "DECISION_LEVEL_STACKING_LATE_FUSION"
        for row in multimodal
    )
    assert all(
        row["late_fusion"]["independently_learned_base_modalities"] is True
        for row in multimodal
    )
    assert all(
        row["late_fusion"]["raw_feature_concatenation"] is False for row in multimodal
    )
    assert all(
        row["late_fusion"]["averaging"] is False
        and row["late_fusion"]["voting"] is False
        for row in multimodal
    )


def test_near_perfect_results_are_preserved_and_flagged():
    rows = [
        {"metric": "PR_AUC", "metric_value": 0.99},
        {"metric": "MCC", "metric_value": 0.25},
        {"metric": "Brier", "metric_value": 1.0},
    ]
    flagged = near_perfect_flags(rows)
    assert flagged == [
        {**rows[0], "integrity_audit_required": True},
        {**rows[2], "integrity_audit_required": True},
    ]
    assert rows[0]["metric_value"] == 0.99


def test_pre_and_post_execution_integrity_check_inventory():
    assert set(INTEGRITY_CHECKS) == {
        "exact T1 membership",
        "duplicate identities",
        "missing predictions",
        "missing probabilities",
        "probability range",
        "class prevalence",
        "configuration completeness",
        "execution-scope completeness",
        "T1/T2 contamination",
        "TRAIN/VALIDATION/T1 identity overlap",
        "leakage-contract violations",
        "model/configuration provenance",
        "calibration provenance",
    }


def _amendment_inputs():
    authorization = verify_authorization(ROOT)
    sprint53 = verify_manifest(ROOT / execution.SPRINT53_REL)
    entries = _manifest_entries(ROOT / execution.SPRINT53_REL / "MANIFEST.sha256")
    amendment = load_json(
        ROOT / execution.AMENDMENT_REL / execution.AMENDMENT_FILE
    )
    return authorization, sprint53, entries, amendment


def test_original_authorization_and_sprint53_manifest_remain_unchanged():
    authorization_path = ROOT / execution.AUTH_REL / execution.AUTHORIZATION_FILE
    sprint53_manifest = ROOT / execution.SPRINT53_REL / "MANIFEST.sha256"
    before = (file_sha256(authorization_path), file_sha256(sprint53_manifest))
    verify_contracts(ROOT, verify_authorization(ROOT))
    after = (file_sha256(authorization_path), file_sha256(sprint53_manifest))
    assert before == after == (
        EXPECTED_AUTHORIZATION_SHA256,
        EXPECTED_SPRINT53_MANIFEST_SHA256,
    )


def test_exact_21_to_22_amendment_is_accepted_and_readiness_passes():
    readiness = prepare_engine(ROOT)
    amendment = readiness["contract_verification"]["prospective_amendment"]
    assert readiness["status"] == "PASS_READY_T1_NOT_ACCESSED"
    assert amendment == {
        "status": "PASS_EXACT_PROSPECTIVE_METADATA_CORRECTION",
        "amendment_sha256": EXPECTED_AMENDMENT_SHA256,
        "original_declared_entry_count": 21,
        "effective_entry_count": 22,
        "verified_entry_count": 22,
    }


def test_any_different_amendment_count_fails_closed():
    authorization, sprint53, entries, amendment = _amendment_inputs()
    amendment = copy.deepcopy(amendment)
    amendment["metadata_correction"]["effective_entry_count"] = 23
    with pytest.raises(ConfirmatoryExecutionError, match="amendment changed"):
        _validate_amendment_payload(amendment, authorization, sprint53, entries)


def test_any_manifest_hash_change_fails_closed():
    authorization, sprint53, entries, amendment = _amendment_inputs()
    sprint53 = dict(sprint53)
    sprint53["manifest_sha256"] = "0" * 64
    with pytest.raises(ConfirmatoryExecutionError, match="amendment changed"):
        _validate_amendment_payload(amendment, authorization, sprint53, entries)


def test_any_entry_hash_change_fails_closed():
    authorization, sprint53, entries, amendment = _amendment_inputs()
    entries = dict(entries)
    first = next(iter(entries))
    entries[first] = "0" * 64
    with pytest.raises(ConfirmatoryExecutionError, match="amendment changed"):
        _validate_amendment_payload(amendment, authorization, sprint53, entries)


def test_missing_amendment_fails_closed(monkeypatch):
    monkeypatch.setattr(execution, "AMENDMENT_REL", Path("missing-amendment"))
    with pytest.raises(ConfirmatoryExecutionError, match="missing manifest"):
        verify_contracts(ROOT, verify_authorization(ROOT))


def test_amendment_counters_remain_zero():
    _, _, _, amendment = _amendment_inputs()
    assert amendment["counters_at_amendment"] == {
        "t1_predictive_access_count": 0,
        "t2_predictive_access_count": 0,
        "predictive_scoring_count": 0,
        "xai_execution_count": 0,
    }


def test_completed_one_shot_evidence_is_sealed_and_counters_are_exact():
    results = ROOT / execution.AUTH_REL / "results"
    verify_manifest(results)
    started = load_json(results / "execution_started.json")
    completed = load_json(results / "execution_completed.json")
    integrity = load_json(results / "post_execution_integrity.json")
    assert started["state"] == "T1_EXECUTION_STARTED_IRREVERSIBLE"
    assert completed["state"] == "T1_CONFIRMATORY_EXECUTION_COMPLETE_DO_NOT_RERUN"
    assert completed["t1_predictive_access_count"] == 1
    assert completed["predictive_scoring_count"] == 1
    assert completed["t2_predictive_access_count"] == 0
    assert completed["xai_execution_count"] == 0
    assert completed["t1_rerun_permitted"] is False
    assert integrity["status"] == "PASS_COMPLETE_EVIDENCE"
    assert integrity["evidence_rows"] == EXPECTED_EVIDENCE_ROWS
    assert integrity["unique_t1_identities"] == EXPECTED_T1_ROWS


def test_second_t1_access_is_blocked_before_payload_materialization():
    source = inspect.getsource(execute_one_shot)
    assert source.index("if output.exists() or start.exists()") < source.index(
        "_load_authorized_t1"
    )
    assert (ROOT / execution.AUTH_REL / "results").is_dir()
