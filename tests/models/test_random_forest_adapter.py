"""Tests for the reproducible random-forest training adapter."""

from dataclasses import FrozenInstanceError
from types import MappingProxyType

import pytest

from dataset.model_input import ModelPartitionInput, PreparedModelInput
from models.random_forest_adapter import (
    PreparedRandomForestModel,
    RandomForestAdapter,
    RandomForestConfiguration,
)


def _partition(name: str, offset: int, X, y) -> ModelPartitionInput:
    return ModelPartitionInput(
        name,
        tuple(range(offset, offset + len(X))),
        X,
        y,
        ("first", "second"),
        {"partition": {"name": name}},
    )


@pytest.fixture
def prepared_input() -> PreparedModelInput:
    return PreparedModelInput(
        "example",
        "1.0",
        _partition(
            "train",
            0,
            ((-2.0, 1.0), (-1.0, 0.5), (1.0, -0.5), (2.0, -1.0)),
            ("negative", "negative", "positive", "positive"),
        ),
        _partition("validation", 10, ((-0.5, 0.25),), ("negative",)),
        _partition("test", 20, ((0.5, -0.25),), ("positive",)),
        ("first", "second"),
        "label",
        {"source": {"tags": ["stable"]}},
    )


def test_training_is_deterministic_and_reproducible(prepared_input):
    configuration = RandomForestConfiguration(n_estimators=8, random_state=17)
    adapter = RandomForestAdapter(configuration)

    first = adapter.train(prepared_input)
    second = adapter.train(prepared_input)
    independent = RandomForestAdapter(configuration).train(prepared_input)

    assert first == second == independent
    assert adapter.configuration is configuration
    assert adapter.adapter_name == "random-forest"


def test_result_contains_framework_neutral_training_snapshot(prepared_input):
    result = RandomForestAdapter(RandomForestConfiguration(n_estimators=7)).train(
        prepared_input
    )

    assert isinstance(result, PreparedRandomForestModel)
    assert result.feature_names == ("first", "second")
    assert result.class_labels == ("negative", "positive")
    assert len(result.feature_importances) == 2
    assert len(result.tree_node_counts) == len(result.tree_max_depths) == 7
    assert not hasattr(result, "predict")
    assert not hasattr(result, "predict_proba")


@pytest.mark.parametrize(
    ("changes", "error"),
    [
        ({"n_estimators": 0}, ValueError),
        ({"n_estimators": True}, TypeError),
        ({"criterion": "unknown"}, ValueError),
        ({"max_depth": 0}, ValueError),
        ({"min_samples_split": 1}, ValueError),
        ({"min_samples_split": 1.1}, ValueError),
        ({"min_samples_leaf": 0}, ValueError),
        ({"max_features": True}, TypeError),
        ({"max_features": float("nan")}, ValueError),
        ({"bootstrap": 1}, TypeError),
        ({"class_weight": []}, TypeError),
        ({"class_weight": {0: 0}}, ValueError),
        ({"random_state": None}, TypeError),
        ({"random_state": True}, TypeError),
    ],
)
def test_invalid_configurations_are_rejected(changes, error):
    with pytest.raises(error):
        RandomForestConfiguration(**changes)


def test_configuration_is_immutable_detached_and_serializable():
    weights = {0: 1.0, 1: 2.0}
    configuration = RandomForestConfiguration(class_weight=weights)
    weights[0] = 99.0

    assert isinstance(configuration.class_weight, MappingProxyType)
    assert configuration.class_weight[0] == 1.0
    with pytest.raises(FrozenInstanceError):
        configuration.n_estimators = 2
    serialized = configuration.to_dict()
    serialized["class_weight"][0] = 4.0
    assert configuration.class_weight[0] == 1.0


def test_adapter_rejects_invalid_inputs(prepared_input):
    with pytest.raises(TypeError, match="configuration"):
        RandomForestAdapter(object())
    adapter = RandomForestAdapter(RandomForestConfiguration(n_estimators=3))
    with pytest.raises(TypeError, match="PreparedModelInput"):
        adapter.train(object())

    one_class = PreparedModelInput(
        "one",
        "1",
        _partition("train", 0, ((1.0, 2.0),), (0,)),
        _partition("validation", 2, ((1.0, 2.0),), (0,)),
        _partition("test", 3, ((1.0, 2.0),), (0,)),
        ("first", "second"),
        "label",
    )
    with pytest.raises(ValueError, match="two classes"):
        adapter.train(one_class)


@pytest.mark.parametrize("bad_value", ["text", True, float("nan"), float("inf")])
def test_training_rejects_non_numeric_or_non_finite_features(bad_value):
    prepared = PreparedModelInput(
        "bad",
        "1",
        _partition("train", 0, ((bad_value, 0.0), (1.0, 1.0)), (0, 1)),
        _partition("validation", 2, ((0.0, 0.0),), (0,)),
        _partition("test", 3, ((1.0, 1.0),), (1,)),
        ("first", "second"),
        "label",
    )
    with pytest.raises((TypeError, ValueError)):
        RandomForestAdapter(RandomForestConfiguration(n_estimators=3)).train(prepared)


def test_output_and_serialization_are_immutable_and_detached(prepared_input):
    result = RandomForestAdapter(RandomForestConfiguration(n_estimators=3)).train(
        prepared_input
    )

    assert isinstance(result.metadata, MappingProxyType)
    with pytest.raises(FrozenInstanceError):
        result.dataset_name = "changed"
    with pytest.raises(TypeError):
        result.metadata["source"]["tags"] += ("changed",)
    first = result.to_dict()
    second = result.to_dict()
    first["metadata"]["source"]["tags"].append("changed")
    first["feature_importances"][0] = 999.0
    assert result.to_dict() == second


def test_structural_equality_and_inequality(prepared_input):
    configuration = RandomForestConfiguration(n_estimators=4)
    first = RandomForestAdapter(configuration).train(prepared_input)
    equal = RandomForestAdapter(configuration).train(prepared_input)
    different = RandomForestAdapter(
        RandomForestConfiguration(n_estimators=4, max_depth=1)
    ).train(prepared_input)

    assert first == equal
    assert first != different


def test_public_exports_are_narrow_and_exact():
    from models import random_forest_adapter

    assert random_forest_adapter.__all__ == [
        "RandomForestConfiguration",
        "PreparedRandomForestModel",
        "RandomForestAdapter",
    ]
