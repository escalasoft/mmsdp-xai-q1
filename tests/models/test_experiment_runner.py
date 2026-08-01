"""Tests for the reproducible model experiment runner."""

from dataclasses import FrozenInstanceError, replace
from types import MappingProxyType

import pytest

from dataset.model_input import ModelPartitionInput, PreparedModelInput
from models.evaluation import ModelPredictionEvaluator
from models.experiment_runner import ModelExperimentResult, ModelExperimentRunner
from models.logistic_regression_adapter import (
    LogisticRegressionAdapter,
    LogisticRegressionConfiguration,
)
from models.random_forest_adapter import RandomForestAdapter, RandomForestConfiguration


def _partition(
    name: str,
    identifiers: tuple[object, ...],
    X: tuple[tuple[float, float], ...],
    y: tuple[str, ...],
) -> ModelPartitionInput:
    return ModelPartitionInput(
        name,
        identifiers,
        X,
        y,
        ("first", "second"),
        {"partition": {"tags": [name]}},
    )


@pytest.fixture
def prepared_input() -> PreparedModelInput:
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
            (10, 11, 12),
            ((2.5, -1), (-2.5, 1), (0.2, 0)),
            ("positive", "negative", "positive"),
        ),
        _partition(
            "test",
            (20, 21, 22),
            ((-0.2, 0), (1.5, -1), (-1.5, 1)),
            ("negative", "positive", "negative"),
        ),
        ("first", "second"),
        "label",
        {"source": {"tags": ["stable"], "groups": {"a", "b"}}},
    )


@pytest.fixture
def logistic_adapter() -> LogisticRegressionAdapter:
    return LogisticRegressionAdapter(LogisticRegressionConfiguration(random_state=17))


@pytest.fixture
def forest_adapter() -> RandomForestAdapter:
    return RandomForestAdapter(
        RandomForestConfiguration(n_estimators=9, random_state=17)
    )


@pytest.mark.parametrize(
    ("adapter_fixture", "model_name"),
    [
        ("logistic_adapter", "logistic-regression"),
        ("forest_adapter", "random-forest"),
    ],
)
def test_end_to_end_supported_models_are_complete_and_deterministic(
    request: pytest.FixtureRequest,
    prepared_input: PreparedModelInput,
    adapter_fixture: str,
    model_name: str,
) -> None:
    runner = ModelExperimentRunner(
        model_adapter=request.getfixturevalue(adapter_fixture),
        positive_label="positive",
    )

    first = runner.run(prepared_input)
    second = runner.run(prepared_input)

    assert first == second
    assert (first.dataset_name, first.dataset_version, first.model_name) == (
        "example",
        "1.0",
        model_name,
    )
    assert first.validation_prediction.partition_name == "validation"
    assert first.validation_evaluation.partition_name == "validation"
    assert first.test_prediction.partition_name == "test"
    assert first.test_evaluation.partition_name == "test"
    assert first.validation_prediction.observation_count == 3
    assert first.validation_evaluation.observation_count == 3
    assert first.test_prediction.observation_count == 3
    assert first.test_evaluation.observation_count == 3


def test_training_and_evaluation_use_the_correct_partitions(
    monkeypatch: pytest.MonkeyPatch,
    prepared_input: PreparedModelInput,
    logistic_adapter: LogisticRegressionAdapter,
) -> None:
    train_calls: list[PreparedModelInput] = []
    evaluation_calls: list[tuple[str, tuple[object, ...]]] = []
    original_train = LogisticRegressionAdapter.train
    original_evaluate = ModelPredictionEvaluator.evaluate

    def train_spy(self: LogisticRegressionAdapter, value: PreparedModelInput):
        train_calls.append(value)
        return original_train(self, value)

    def evaluate_spy(self: ModelPredictionEvaluator, prediction_result, targets):
        evaluation_calls.append((prediction_result.partition_name, tuple(targets)))
        return original_evaluate(self, prediction_result, targets)

    monkeypatch.setattr(LogisticRegressionAdapter, "train", train_spy)
    monkeypatch.setattr(ModelPredictionEvaluator, "evaluate", evaluate_spy)

    ModelExperimentRunner(
        model_adapter=logistic_adapter, positive_label="positive"
    ).run(prepared_input)

    assert train_calls == [prepared_input]
    assert evaluation_calls == [
        ("validation", prepared_input.validation.y),
        ("test", prepared_input.test.y),
    ]


def test_run_does_not_modify_input_or_nested_metadata(
    prepared_input: PreparedModelInput,
    forest_adapter: RandomForestAdapter,
) -> None:
    before = prepared_input.to_dict()
    result = ModelExperimentRunner(
        model_adapter=forest_adapter, positive_label="positive"
    ).run(prepared_input)

    assert prepared_input.to_dict() == before
    assert result.metadata is not prepared_input.metadata
    assert result.metadata == prepared_input.metadata


def test_result_is_immutable_and_metadata_is_detached(
    prepared_input: PreparedModelInput,
    logistic_adapter: LogisticRegressionAdapter,
) -> None:
    result = ModelExperimentRunner(
        model_adapter=logistic_adapter, positive_label="positive"
    ).run(prepared_input)

    assert isinstance(result.metadata, MappingProxyType)
    with pytest.raises(FrozenInstanceError):
        result.model_name = "changed"  # type: ignore[misc]
    with pytest.raises(TypeError):
        result.metadata["source"]["tags"] += ("changed",)  # type: ignore[index,operator]


def test_to_dict_is_deterministic_mutable_and_detached(
    prepared_input: PreparedModelInput,
    logistic_adapter: LogisticRegressionAdapter,
) -> None:
    result = ModelExperimentRunner(
        model_adapter=logistic_adapter, positive_label="positive"
    ).run(prepared_input)
    first = result.to_dict()
    second = result.to_dict()

    assert first == second
    assert first is not second
    first["metadata"]["source"]["tags"].append("changed")  # type: ignore[index,union-attr]
    first["validation_prediction"]["predictions"].append("changed")  # type: ignore[index,union-attr]
    assert result.to_dict() == second


@pytest.mark.parametrize("adapter", [None, object(), "logistic-regression"])
def test_unsupported_adapters_are_rejected(adapter: object) -> None:
    with pytest.raises(TypeError, match="unsupported model adapter"):
        ModelExperimentRunner(model_adapter=adapter, positive_label="positive")


@pytest.mark.parametrize("bad_input", [None, object(), "prepared"])
def test_non_prepared_inputs_are_rejected(
    bad_input: object, logistic_adapter: LogisticRegressionAdapter
) -> None:
    runner = ModelExperimentRunner(
        model_adapter=logistic_adapter, positive_label="positive"
    )
    with pytest.raises(TypeError, match="PreparedModelInput"):
        runner.run(bad_input)  # type: ignore[arg-type]


def test_invalid_positive_label_is_rejected_by_evaluator_contract(
    prepared_input: PreparedModelInput,
    logistic_adapter: LogisticRegressionAdapter,
) -> None:
    runner = ModelExperimentRunner(
        model_adapter=logistic_adapter, positive_label="unknown"
    )
    with pytest.raises(ValueError, match="positive_label"):
        runner.run(prepared_input)


def test_positive_label_is_detached(
    logistic_adapter: LogisticRegressionAdapter,
) -> None:
    label = ["positive"]
    runner = ModelExperimentRunner(model_adapter=logistic_adapter, positive_label=label)
    label.append("changed")
    assert runner.positive_label == ["positive"]
    detached = runner.positive_label
    detached.append("again")  # type: ignore[union-attr]
    assert runner.positive_label == ["positive"]
    assert runner.model_adapter is logistic_adapter


def _valid_result(
    prepared_input: PreparedModelInput,
    logistic_adapter: LogisticRegressionAdapter,
) -> ModelExperimentResult:
    return ModelExperimentRunner(
        model_adapter=logistic_adapter, positive_label="positive"
    ).run(prepared_input)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ({"dataset_name": "different"}, "dataset_name"),
        ({"model_name": "different"}, "model_name"),
    ],
)
def test_result_rejects_inconsistent_top_level_identity(
    prepared_input: PreparedModelInput,
    logistic_adapter: LogisticRegressionAdapter,
    mutation: dict[str, object],
    message: str,
) -> None:
    result = _valid_result(prepared_input, logistic_adapter)
    values = {
        "dataset_name": result.dataset_name,
        "dataset_version": result.dataset_version,
        "model_name": result.model_name,
        "validation_prediction": result.validation_prediction,
        "validation_evaluation": result.validation_evaluation,
        "test_prediction": result.test_prediction,
        "test_evaluation": result.test_evaluation,
        "metadata": result.metadata,
    } | mutation
    with pytest.raises(ValueError, match=message):
        ModelExperimentResult(**values)  # type: ignore[arg-type]


def test_result_rejects_partition_model_count_and_class_mismatches(
    prepared_input: PreparedModelInput,
    logistic_adapter: LogisticRegressionAdapter,
) -> None:
    result = _valid_result(prepared_input, logistic_adapter)

    with pytest.raises(ValueError, match="validation partition"):
        ModelExperimentResult(
            result.dataset_name,
            result.dataset_version,
            result.model_name,
            replace(result.validation_prediction, partition_name="test"),
            result.validation_evaluation,
            result.test_prediction,
            result.test_evaluation,
        )
    with pytest.raises(ValueError, match="model_name"):
        ModelExperimentResult(
            result.dataset_name,
            result.dataset_version,
            result.model_name,
            replace(result.validation_prediction, model_name="different"),
            result.validation_evaluation,
            result.test_prediction,
            result.test_evaluation,
        )
    malformed_count = replace(
        result.validation_evaluation,
        observation_count=result.validation_evaluation.observation_count + 1,
        true_negative=result.validation_evaluation.true_negative + 1,
    )
    with pytest.raises(ValueError, match="observation counts"):
        ModelExperimentResult(
            result.dataset_name,
            result.dataset_version,
            result.model_name,
            result.validation_prediction,
            malformed_count,
            result.test_prediction,
            result.test_evaluation,
        )
    object.__setattr__(result.validation_evaluation, "class_labels", ("no", "yes"))
    with pytest.raises(ValueError, match="class_labels"):
        ModelExperimentResult(
            result.dataset_name,
            result.dataset_version,
            result.model_name,
            result.validation_prediction,
            result.validation_evaluation,
            result.test_prediction,
            result.test_evaluation,
        )


def test_result_rejects_wrong_nested_types_and_metadata(
    prepared_input: PreparedModelInput,
    logistic_adapter: LogisticRegressionAdapter,
) -> None:
    result = _valid_result(prepared_input, logistic_adapter)
    with pytest.raises(TypeError, match="validation_prediction"):
        ModelExperimentResult(
            result.dataset_name,
            result.dataset_version,
            result.model_name,
            object(),  # type: ignore[arg-type]
            result.validation_evaluation,
            result.test_prediction,
            result.test_evaluation,
        )
    with pytest.raises(TypeError, match="metadata"):
        ModelExperimentResult(
            result.dataset_name,
            result.dataset_version,
            result.model_name,
            result.validation_prediction,
            result.validation_evaluation,
            result.test_prediction,
            result.test_evaluation,
            metadata=[],  # type: ignore[arg-type]
        )


def test_public_surface_is_narrow_and_exact() -> None:
    from models import experiment_runner

    assert experiment_runner.__all__ == [
        "ModelExperimentResult",
        "ModelExperimentRunner",
    ]
    assert ModelExperimentRunner.runner_name == "model-experiment-runner"
    forbidden = (
        "save",
        "persist",
        "plot",
        "calibrate",
        "preprocess",
        "explain",
    )
    assert all(not hasattr(ModelExperimentRunner, name) for name in forbidden)
