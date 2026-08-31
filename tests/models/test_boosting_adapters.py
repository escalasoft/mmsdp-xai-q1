"""Focused deterministic readiness tests for XGBoost and LightGBM adapters."""

from types import MappingProxyType

import pytest

from dataset.model_input import ModelPartitionInput, PreparedModelInput
from models.boosting_adapters import (
    LIGHTGBM_SEARCH_SPACE,
    XGBOOST_SEARCH_SPACE,
    LightGBMAdapter,
    LightGBMConfiguration,
    XGBoostAdapter,
    XGBoostConfiguration,
)


def _partition(name, offset, rows, labels):
    return ModelPartitionInput(
        name,
        tuple(range(offset, offset + len(rows))),
        rows,
        labels,
        ("first", "second"),
    )


@pytest.fixture
def prepared_input() -> PreparedModelInput:
    return PreparedModelInput(
        "example",
        "1.0",
        _partition(
            "train", 0, ((0.0, 0.0), (0.2, 0.1), (1.0, 1.0), (0.8, 0.9)), (0, 0, 1, 1)
        ),
        _partition("validation", 10, ((0.1, 0.1),), (0,)),
        _partition("test", 20, ((0.9, 0.9),), (1,)),
        ("first", "second"),
        "target",
        {"fit_scope": "SOURCE_TRAIN_ONLY"},
    )


def test_search_spaces_are_frozen_bounded_and_seeded() -> None:
    assert isinstance(XGBOOST_SEARCH_SPACE, MappingProxyType)
    assert isinstance(LIGHTGBM_SEARCH_SPACE, MappingProxyType)
    assert XGBoostConfiguration().random_state == 20260829
    assert LightGBMConfiguration().random_state == 20260829
    assert all(len(values) <= 3 for values in XGBOOST_SEARCH_SPACE.values())
    assert all(len(values) <= 3 for values in LIGHTGBM_SEARCH_SPACE.values())


@pytest.mark.parametrize(
    "adapter",
    [
        XGBoostAdapter(XGBoostConfiguration(n_estimators=4, max_depth=2)),
        LightGBMAdapter(LightGBMConfiguration(n_estimators=4, num_leaves=4)),
    ],
)
def test_adapter_fits_source_train_and_returns_auditable_snapshot(
    adapter, prepared_input
) -> None:
    result = adapter.train(prepared_input)
    assert result.dataset_name == "example"
    assert result.feature_names == ("first", "second")
    assert result.class_labels == (0, 1)
    assert len(result.feature_importances) == 2
    assert result.metadata["fit_scope"] == "SOURCE_TRAIN_ONLY"
    assert result.serialized_estimator


@pytest.mark.parametrize(
    ("configuration", "error"),
    [
        (lambda: XGBoostConfiguration(n_estimators=0), ValueError),
        (lambda: XGBoostConfiguration(subsample=1.1), ValueError),
        (lambda: LightGBMConfiguration(num_leaves=1), ValueError),
        (lambda: LightGBMConfiguration(random_state=True), TypeError),
    ],
)
def test_invalid_configurations_fail_closed(configuration, error) -> None:
    with pytest.raises(error):
        configuration()
