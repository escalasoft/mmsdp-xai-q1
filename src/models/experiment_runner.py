"""Deterministic orchestration of supported model experiments."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from types import MappingProxyType

from dataset.model_input import PreparedModelInput
from models.evaluation import ModelEvaluationResult, ModelPredictionEvaluator
from models.logistic_regression_adapter import (
    LogisticRegressionAdapter,
    PreparedLogisticRegressionModel,
)
from models.prediction import ModelPredictionResult, ModelPredictor
from models.random_forest_adapter import (
    PreparedRandomForestModel,
    RandomForestAdapter,
)

__all__ = [
    "ModelExperimentResult",
    "ModelExperimentRunner",
]


def _freeze(value: object) -> object:
    """Return a detached, recursively immutable snapshot."""
    if isinstance(value, Mapping):
        return MappingProxyType(
            {deepcopy(key): _freeze(item) for key, item in value.items()}
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze(item) for item in value)
    return deepcopy(value)


def _freeze_mapping(value: Mapping[str, object]) -> Mapping[str, object]:
    return MappingProxyType(
        {deepcopy(key): _freeze(item) for key, item in value.items()}
    )


def _thaw(value: object) -> object:
    """Return a detached snapshot containing ordinary mutable containers."""
    if isinstance(value, Mapping):
        return {deepcopy(key): _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    if isinstance(value, frozenset):
        return {_thaw(item) for item in value}
    return deepcopy(value)


def _validate_name(name: str, value: object) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


@dataclass(frozen=True, slots=True, init=False)
class ModelExperimentResult:
    """Immutable, framework-neutral result of one complete model experiment."""

    dataset_name: str
    dataset_version: str
    model_name: str
    validation_prediction: ModelPredictionResult
    validation_evaluation: ModelEvaluationResult
    test_prediction: ModelPredictionResult
    test_evaluation: ModelEvaluationResult
    metadata: Mapping[str, object]

    def __init__(
        self,
        dataset_name: str,
        dataset_version: str,
        model_name: str,
        validation_prediction: ModelPredictionResult,
        validation_evaluation: ModelEvaluationResult,
        test_prediction: ModelPredictionResult,
        test_evaluation: ModelEvaluationResult,
        metadata: Mapping[str, object] = MappingProxyType({}),
    ) -> None:
        for name, value in (
            ("dataset_name", dataset_name),
            ("dataset_version", dataset_version),
            ("model_name", model_name),
        ):
            _validate_name(name, value)

        expected_types = (
            ("validation_prediction", validation_prediction, ModelPredictionResult),
            ("validation_evaluation", validation_evaluation, ModelEvaluationResult),
            ("test_prediction", test_prediction, ModelPredictionResult),
            ("test_evaluation", test_evaluation, ModelEvaluationResult),
        )
        for name, value, expected_type in expected_types:
            if not isinstance(value, expected_type):
                raise TypeError(f"{name} must be a {expected_type.__name__}")
        if not isinstance(metadata, Mapping):
            raise TypeError("metadata must be a mapping")

        nested_results = (
            validation_prediction,
            validation_evaluation,
            test_prediction,
            test_evaluation,
        )
        if any(item.dataset_name != dataset_name for item in nested_results):
            raise ValueError("dataset_name must match all nested results")
        if any(item.dataset_version != dataset_version for item in nested_results):
            raise ValueError("dataset_version must match all nested results")
        if (
            validation_prediction.partition_name != "validation"
            or validation_evaluation.partition_name != "validation"
        ):
            raise ValueError("validation results must use the validation partition")
        if (
            test_prediction.partition_name != "test"
            or test_evaluation.partition_name != "test"
        ):
            raise ValueError("test results must use the test partition")
        if any(item.model_name != model_name for item in nested_results):
            raise ValueError("model_name must match all nested results")

        for partition_name, prediction, evaluation in (
            ("validation", validation_prediction, validation_evaluation),
            ("test", test_prediction, test_evaluation),
        ):
            if prediction.observation_count != evaluation.observation_count:
                raise ValueError(
                    f"{partition_name} prediction and evaluation observation counts "
                    "must match"
                )
            if prediction.class_labels != evaluation.class_labels:
                raise ValueError(
                    f"{partition_name} prediction and evaluation class_labels must "
                    "match"
                )

        object.__setattr__(self, "dataset_name", deepcopy(dataset_name))
        object.__setattr__(self, "dataset_version", deepcopy(dataset_version))
        object.__setattr__(self, "model_name", deepcopy(model_name))
        object.__setattr__(self, "validation_prediction", validation_prediction)
        object.__setattr__(self, "validation_evaluation", validation_evaluation)
        object.__setattr__(self, "test_prediction", test_prediction)
        object.__setattr__(self, "test_evaluation", test_evaluation)
        object.__setattr__(self, "metadata", _freeze_mapping(metadata))

    def to_dict(self) -> dict[str, object]:
        """Return a deterministic, detached representation using mutable containers."""
        return {
            "dataset_name": deepcopy(self.dataset_name),
            "dataset_version": deepcopy(self.dataset_version),
            "model_name": deepcopy(self.model_name),
            "validation_prediction": self.validation_prediction.to_dict(),
            "validation_evaluation": self.validation_evaluation.to_dict(),
            "test_prediction": self.test_prediction.to_dict(),
            "test_evaluation": self.test_evaluation.to_dict(),
            "metadata": _thaw(self.metadata),
        }


class ModelExperimentRunner:
    """Train, predict, and evaluate one supported deterministic model."""

    runner_name = "model-experiment-runner"

    def __init__(
        self,
        *,
        model_adapter: object,
        positive_label: object,
    ) -> None:
        if not isinstance(
            model_adapter, (LogisticRegressionAdapter, RandomForestAdapter)
        ):
            raise TypeError("unsupported model adapter")
        self._model_adapter = model_adapter
        self._positive_label = _freeze(positive_label)

    @property
    def model_adapter(self) -> LogisticRegressionAdapter | RandomForestAdapter:
        """Return the configured supported model adapter."""
        return self._model_adapter

    @property
    def positive_label(self) -> object:
        """Return a detached copy of the configured positive label."""
        return _thaw(self._positive_label)

    def run(self, prepared_input: PreparedModelInput) -> ModelExperimentResult:
        """Run one model experiment without transforming or mutating its input."""
        if not isinstance(prepared_input, PreparedModelInput):
            raise TypeError("prepared_input must be a PreparedModelInput")

        model = self._model_adapter.train(prepared_input)
        if isinstance(model, PreparedLogisticRegressionModel):
            model_name = "logistic-regression"
        elif isinstance(model, PreparedRandomForestModel):
            model_name = "random-forest"
        else:
            raise TypeError("model adapter returned an unsupported model type")

        predictor = ModelPredictor()
        evaluator = ModelPredictionEvaluator(positive_label=self._positive_label)
        validation_prediction = predictor.predict(model, prepared_input, "validation")
        validation_evaluation = evaluator.evaluate(
            validation_prediction, prepared_input.validation.y
        )
        test_prediction = predictor.predict(model, prepared_input, "test")
        test_evaluation = evaluator.evaluate(test_prediction, prepared_input.test.y)

        return ModelExperimentResult(
            dataset_name=prepared_input.dataset_name,
            dataset_version=prepared_input.dataset_version,
            model_name=model_name,
            validation_prediction=validation_prediction,
            validation_evaluation=validation_evaluation,
            test_prediction=test_prediction,
            test_evaluation=test_evaluation,
            metadata=prepared_input.metadata,
        )
