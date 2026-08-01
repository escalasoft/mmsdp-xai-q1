"""Tests for the reproducible logistic-regression training adapter."""

from dataclasses import FrozenInstanceError
from types import MappingProxyType

import pytest

from dataset.model_input import ModelPartitionInput, PreparedModelInput
from models.logistic_regression_adapter import (
    LogisticRegressionAdapter,
    LogisticRegressionConfiguration,
    PreparedLogisticRegressionModel,
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
    configuration = LogisticRegressionConfiguration(random_state=17)
    adapter = LogisticRegressionAdapter(configuration)

    first = adapter.train(prepared_input)
    second = adapter.train(prepared_input)
    independent = LogisticRegressionAdapter(configuration).train(prepared_input)

    assert first == second == independent
    assert first.coefficients == second.coefficients
    assert adapter.configuration is configuration
    assert adapter.adapter_name == "logistic-regression"


def test_result_contains_framework_neutral_training_snapshot(prepared_input):
    result = LogisticRegressionAdapter(LogisticRegressionConfiguration()).train(
        prepared_input
    )

    assert isinstance(result, PreparedLogisticRegressionModel)
    assert result.dataset_name == "example"
    assert result.feature_names == ("first", "second")
    assert result.target_name == "label"
    assert result.class_labels == ("negative", "positive")
    assert len(result.coefficients) == len(result.intercepts) == 1
    assert all(isinstance(value, float) for value in result.coefficients[0])
    assert not hasattr(result, "predict")
    assert not hasattr(result, "predict_proba")


@pytest.mark.parametrize(
    ("changes", "error"),
    [
        ({"C": 0}, ValueError),
        ({"C": True}, TypeError),
        ({"C": float("inf")}, ValueError),
        ({"fit_intercept": 1}, TypeError),
        ({"class_weight": []}, TypeError),
        ({"class_weight": {0: 0}}, ValueError),
        ({"random_state": None}, TypeError),
        ({"random_state": True}, TypeError),
        ({"random_state": 1.5}, TypeError),
        ({"solver": "unknown"}, ValueError),
        ({"max_iter": 0}, ValueError),
        ({"max_iter": 1.5}, TypeError),
        ({"tol": float("nan")}, ValueError),
    ],
)
def test_invalid_configurations_are_rejected(changes, error):
    with pytest.raises(error):
        LogisticRegressionConfiguration(**changes)


def test_configuration_is_immutable_detached_and_serializable():
    weights = {0: 1.0, 1: 2.0}
    configuration = LogisticRegressionConfiguration(class_weight=weights)
    weights[0] = 99.0

    assert isinstance(configuration.class_weight, MappingProxyType)
    assert configuration.class_weight[0] == 1.0
    with pytest.raises(FrozenInstanceError):
        configuration.C = 2.0
    with pytest.raises(TypeError):
        configuration.class_weight[0] = 3.0
    serialized = configuration.to_dict()
    serialized["class_weight"][0] = 4.0
    assert configuration.class_weight[0] == 1.0


def test_adapter_rejects_invalid_inputs(prepared_input):
    with pytest.raises(TypeError, match="configuration"):
        LogisticRegressionAdapter(object())
    adapter = LogisticRegressionAdapter(LogisticRegressionConfiguration())
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
        LogisticRegressionAdapter(LogisticRegressionConfiguration()).train(prepared)


def test_output_and_nested_metadata_are_immutable_and_detached(prepared_input):
    result = LogisticRegressionAdapter(LogisticRegressionConfiguration()).train(
        prepared_input
    )

    assert isinstance(result.metadata, MappingProxyType)
    assert result.metadata is not prepared_input.metadata
    assert result.metadata["source"] is not prepared_input.metadata["source"]
    with pytest.raises(FrozenInstanceError):
        result.dataset_name = "changed"
    with pytest.raises(TypeError):
        result.metadata["new"] = True
    with pytest.raises(TypeError):
        result.metadata["source"]["tags"] += ("changed",)


def test_to_dict_is_deterministic_mutable_and_detached(prepared_input):
    result = LogisticRegressionAdapter(LogisticRegressionConfiguration()).train(
        prepared_input
    )
    first = result.to_dict()
    second = result.to_dict()

    assert first == second
    first["metadata"]["source"]["tags"].append("changed")
    first["coefficients"][0][0] = 999.0
    first["configuration"]["C"] = 99.0
    assert result.to_dict() == second


def test_structural_equality_and_inequality(prepared_input):
    first = LogisticRegressionAdapter(LogisticRegressionConfiguration()).train(
        prepared_input
    )
    equal = LogisticRegressionAdapter(LogisticRegressionConfiguration()).train(
        prepared_input
    )
    different = LogisticRegressionAdapter(LogisticRegressionConfiguration(C=0.5)).train(
        prepared_input
    )

    assert first == equal
    assert first != different


def test_public_exports_are_narrow_and_exact():
    from models import logistic_regression_adapter

    assert logistic_regression_adapter.__all__ == [
        "LogisticRegressionConfiguration",
        "PreparedLogisticRegressionModel",
        "LogisticRegressionAdapter",
    ]
