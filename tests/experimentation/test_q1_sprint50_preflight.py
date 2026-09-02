from __future__ import annotations

from pathlib import Path

from experimentation.q1_sprint50_preflight import (
    CLASSIFICATION,
    access_audit,
    inspect,
)

ROOT = Path(__file__).resolve().parents[2]


def test_preflight_preserves_exact_factorial_and_detects_temporal_blockers() -> None:
    result = inspect(ROOT)
    assert result["classification"] == CLASSIFICATION
    assert result["factorial"]["cv_values"] == list(range(2, 12))
    assert result["factorial"]["expected_conditions"] == 14 * 4 * 7 * 10
    assert result["factorial"]["completed_conditions"] == 0
    assert {item["id"] for item in result["blockers"]} == {
        "K2_STACKING_META_WARMUP_UNAVAILABLE",
        "K10_K11_TRAIN_PARTITION_CONFLICT",
    }


def test_k2_cannot_backfill_and_k10_k11_are_validation_blocks() -> None:
    blockers = {item["id"]: item for item in inspect(ROOT)["blockers"]}
    k2 = blockers["K2_STACKING_META_WARMUP_UNAVAILABLE"]["evidence"]
    assert k2["required_meta_training_blocks_for_cv2"] == []
    assert k2["frozen_backfill_warmup_rows"] is False
    later = blockers["K10_K11_TRAIN_PARTITION_CONFLICT"]["evidence"]
    assert later["train_forward_blocks"] == list(range(1, 10))
    assert later["validation_forward_blocks"] == [9, 10, 11]
    assert later["frozen_fold_builder_partition_requirement"] == "TRAIN_ONLY"


def test_all_t1_t2_execution_counters_are_zero() -> None:
    audit = access_audit()
    counters = {key: value for key, value in audit.items() if key.endswith("_count")}
    assert counters
    assert set(counters.values()) == {0}
    assert audit["predictive_execution_started"] is False
