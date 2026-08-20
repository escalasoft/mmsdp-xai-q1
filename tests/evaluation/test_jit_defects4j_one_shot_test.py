from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from evaluation.jit_defects4j_one_shot_test import (
    OneShotTestError,
    _claim_once,
    _validate_configuration,
    metrics_from_prediction_rows,
    probability_metrics,
    reliability_bins,
)


def configuration() -> dict[str, object]:
    return {
        "branch": "sprint-10/jit-defects4j-one-shot-test-evaluation",
        "selected_calibrator": "ISOTONIC",
        "primary_modalities": ["CODE", "TEXT"],
        "excluded_modalities": ["PROCESS"],
        "fusion_weights": {"CODE": 0.5, "TEXT": 0.5},
        "classification_threshold": None,
        "ece_edges": [i / 10 for i in range(11)],
        "test": {"observations": 4119, "positive": 160, "nominal_negative": 3959},
    }


@pytest.mark.parametrize(
    ("key", "bad"),
    [
        ("branch", "wrong"),
        ("selected_calibrator", "PLATT"),
        ("primary_modalities", ["CODE", "PROCESS", "TEXT"]),
        ("excluded_modalities", []),
        ("fusion_weights", {"CODE": 0.4, "TEXT": 0.6}),
        ("classification_threshold", 0.5),
    ],
)
def test_immutable_contract_rejects_changes(key: str, bad: object) -> None:
    value = configuration()
    value[key] = bad
    with pytest.raises(OneShotTestError):
        _validate_configuration(value)


def test_probability_outputs_and_frozen_reliability_bins() -> None:
    y = np.array([0, 0, 1, 1])
    p = np.array([0.0, 0.15, 0.8, 1.0])
    metrics = probability_metrics(y, p)
    assert set(metrics) == {"roc_auc", "average_precision", "brier", "ece"}
    bins = reliability_bins(y, p)
    assert [row["bin_index"] for row in bins] == [0, 1, 8, 9]
    assert sum(row["support"] for row in bins) == 4


def test_probability_shape_and_range_fail_closed() -> None:
    with pytest.raises(OneShotTestError):
        probability_metrics(np.array([0, 1]), np.array([0.2]))
    with pytest.raises(OneShotTestError):
        probability_metrics(np.array([0, 1]), np.array([0.2, 1.1]))


def test_metrics_reproducible_from_persisted_schema() -> None:
    rows = [
        {"target": 0, "p_raw_fusion": 0.1, "p_calibrated": 0.05},
        {"target": 1, "p_raw_fusion": 0.9, "p_calibrated": 0.8},
    ]
    assert metrics_from_prediction_rows(rows) == metrics_from_prediction_rows(
        json.loads(json.dumps(rows))
    )


def test_one_shot_claim_denies_second_scoring(tmp_path: Path) -> None:
    from evaluation.jit_defects4j_one_shot_test import PreflightAuthorization

    authorization = PreflightAuthorization("a" * 40, {}, {}, True)
    path = tmp_path / "state.json"
    _claim_once(path, authorization)
    with pytest.raises(OneShotTestError, match="second predictive"):
        _claim_once(path, authorization)


def test_repository_contract_has_no_threshold_or_process() -> None:
    root = Path(__file__).resolve().parents[2]
    value = json.loads(
        (
            root / "configs/experiments/jit_defects4j_one_shot_test_1.0.0.json"
        ).read_text()
    )
    _validate_configuration(value)
    assert value["classification_threshold"] is None
    assert value["primary_modalities"] == ["CODE", "TEXT"]
    assert value["excluded_modalities"] == ["PROCESS"]
