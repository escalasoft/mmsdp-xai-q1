from __future__ import annotations

from pathlib import Path

from experimentation.q1_controlled_scope_verification import (
    REQUIRED_REPRODUCIBILITY_FIELDS,
    verify_campaign,
    verify_raw_prediction_ledger,
)

ROOT = Path(__file__).resolve().parents[2]


def test_campaign_scope_and_reproducibility_pass() -> None:
    result = verify_campaign(ROOT)
    assert result["status"] == "PASS"
    assert result["primary_validation_condition_count"] == 392
    assert result["train_development_condition_fold_count"] == 1176
    assert result["reproducibility_record_count"] == 392
    assert result["execution_counters"]["model_training_count"] > 0
    assert result["execution_counters"]["predictive_scoring_count"] > 0
    assert result["execution_counters"]["t1_predictive_access_count"] == 0
    assert result["execution_counters"]["t2_predictive_access_count"] == 0
    assert result["execution_counters"]["xai_execution_count"] == 0


def test_raw_prediction_ledger_matches_every_condition_hash() -> None:
    result = verify_raw_prediction_ledger(ROOT)
    assert result["status"] == "PASS"
    assert result["condition_group_count"] == 1568
    assert result["validation_row_count"] == 530348
    assert result["train_development_row_count"] == 433860
    assert result["partitions"] == ["TRAIN", "VALIDATION"]
    assert result["t1_row_count"] == 0
    assert result["t2_row_count"] == 0


def test_reproducibility_field_contract_is_complete() -> None:
    assert REQUIRED_REPRODUCIBILITY_FIELDS == {
        "project",
        "algorithm_family",
        "configuration",
        "seed",
        "package_versions",
        "feature_schema_sha256",
        "train_identity_sha256",
        "validation_identity_sha256",
        "hyperparameters",
        "representation_parameters",
        "threshold_policy",
        "runtime",
        "metrics",
        "status",
        "probability_sha256",
    }
