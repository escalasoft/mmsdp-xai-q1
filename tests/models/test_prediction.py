"""Tests for deterministic prediction from immutable model snapshots."""

from dataclasses import FrozenInstanceError, replace
from types import MappingProxyType

import pytest

from dataset.model_input import ModelPartitionInput, PreparedModelInput
from models.logistic_regression_adapter import (
    LogisticRegressionAdapter,
    LogisticRegressionConfiguration,
)
from models.prediction import ModelPredictionResult, ModelPredictor
from models.random_forest_adapter import RandomForestAdapter, RandomForestConfiguration


def _partition(name, identifiers, X, y):
    return ModelPartitionInput(
        name, identifiers, X, y, ("first", "second"), {"partition": [name]}
    )


@pytest.fixture
def prepared_input():
    return PreparedModelInput(
        "example",
        "1.0",
        _partition(
            "train",
            (0, 1, 2, 3, 4, 5),
            ((-3, 1), (-2, 1), (-1, 0), (1, 0), (2, -1), (3, -1)),
            ("negative", "negative", "negative", "positive", "positive", "positive"),
        ),
        _partition(
            "validation",
            ("third", "first", "second"),
            ((2.5, -1), (-2.5, 1), (0.2, 0)),
            ("positive", "negative", "positive"),
        ),
        _partition("test", (20, 21), ((-0.2, 0), (1.5, -1)), ("negative", "positive")),
        ("first", "second"),
        "label",
        {"source": {"tags": ["stable"]}},
    )


@pytest.fixture
def logistic_model(prepared_input):
    return LogisticRegressionAdapter(
        LogisticRegressionConfiguration(random_state=17)
    ).train(prepared_input)


@pytest.fixture
def forest_model(prepared_input):
    return RandomForestAdapter(
        RandomForestConfiguration(n_estimators=9, random_state=17)
    ).train(prepared_input)


@pytest.mark.parametrize("model_fixture", ["logistic_model", "forest_model"])
def test_supported_models_predict_complete_probabilities(
    request, prepared_input, model_fixture
):
    model = request.getfixturevalue(model_fixture)
    result = ModelPredictor().predict(model, prepared_input, "validation")

    assert result.identifiers == ("third", "first", "second")
    assert result.observation_count == 3
    assert result.class_labels == ("negative", "positive")
    assert len(result.predictions) == len(result.probabilities) == 3
    assert all(len(row) == len(result.class_labels) for row in result.probabilities)
    assert all(0.0 <= value <= 1.0 for row in result.probabilities for value in row)
    assert all(
        sum(row) == pytest.approx(1.0, abs=1e-12) for row in result.probabilities
    )
    assert all(label in result.class_labels for label in result.predictions)


def test_repeated_prediction_is_deterministic(
    prepared_input, logistic_model, forest_model
):
    predictor = ModelPredictor()
    for model in (logistic_model, forest_model):
        first = predictor.predict(model, prepared_input, "test")
        assert first == predictor.predict(model, prepared_input, "test")


def test_result_is_immutable_detached_and_serializes_deterministically(
    prepared_input, logistic_model
):
    result = ModelPredictor().predict(logistic_model, prepared_input, "validation")

    assert isinstance(result.metadata, MappingProxyType)
    assert result.metadata is not logistic_model.metadata
    with pytest.raises(FrozenInstanceError):
        result.model_name = "changed"
    with pytest.raises(TypeError):
        result.metadata["source"]["tags"] += ("changed",)
    first = result.to_dict()
    second = result.to_dict()
    first["identifiers"].append("changed")
    first["probabilities"][0][0] = 0.0
    first["metadata"]["source"]["tags"].append("changed")
    assert result.to_dict() == second


@pytest.mark.parametrize(
    "field,value,error",
    [
        ("dataset_name", "other", ValueError),
        ("dataset_version", "2.0", ValueError),
        ("target_name", "other", ValueError),
        ("feature_names", ("second", "first"), ValueError),
    ],
)
def test_model_and_input_mismatches_are_rejected(
    prepared_input, logistic_model, field, value, error
):
    incompatible = replace(logistic_model, **{field: value})
    with pytest.raises(error):
        ModelPredictor().predict(incompatible, prepared_input, "validation")


@pytest.mark.parametrize("partition", ["unknown", "", "TRAIN"])
def test_invalid_partitions_are_rejected(prepared_input, logistic_model, partition):
    with pytest.raises(ValueError):
        ModelPredictor().predict(logistic_model, prepared_input, partition)


def test_training_partition_and_unsupported_models_are_rejected(
    prepared_input, logistic_model
):
    with pytest.raises(ValueError, match="training-partition"):
        ModelPredictor().predict(logistic_model, prepared_input, "train")
    with pytest.raises(TypeError, match="unsupported"):
        ModelPredictor().predict(object(), prepared_input, "test")


def test_prediction_does_not_mutate_model_or_input(prepared_input, forest_model):
    model_before = forest_model.to_dict()
    input_before = prepared_input.to_dict()

    ModelPredictor().predict(forest_model, prepared_input, "validation")

    assert forest_model.to_dict() == model_before
    assert prepared_input.to_dict() == input_before


def test_result_validates_probability_and_alignment_contracts():
    arguments = {
        "dataset_name": "example",
        "dataset_version": "1",
        "partition_name": "test",
        "model_name": "model",
        "identifiers": (1,),
        "class_labels": ("no", "yes"),
        "predictions": ("yes",),
        "probabilities": ((0.25, 0.75),),
        "observation_count": 1,
    }
    assert ModelPredictionResult(**arguments).observation_count == 1
    with pytest.raises(ValueError, match="unique"):
        ModelPredictionResult(
            **(arguments | {"identifiers": (1, 1), "observation_count": 2})
        )
    with pytest.raises(ValueError, match="align"):
        ModelPredictionResult(**(arguments | {"observation_count": 2}))
    with pytest.raises(ValueError, match="belong"):
        ModelPredictionResult(**(arguments | {"predictions": ("maybe",)}))
    with pytest.raises(ValueError, match="finite"):
        ModelPredictionResult(**(arguments | {"probabilities": ((float("nan"), 0.0),)}))
    with pytest.raises(ValueError, match="sum"):
        ModelPredictionResult(**(arguments | {"probabilities": ((0.2, 0.2),)}))


def test_predictor_name_and_public_exports_are_narrow_and_exact():
    from models import prediction

    assert ModelPredictor.predictor_name == "model-predictor"
    assert prediction.__all__ == ["ModelPredictionResult", "ModelPredictor"]
