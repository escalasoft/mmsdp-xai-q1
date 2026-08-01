"""Deterministic prediction from framework-neutral trained model snapshots."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from types import MappingProxyType

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression

from dataset.model_input import PreparedModelInput
from models.logistic_regression_adapter import PreparedLogisticRegressionModel
from models.random_forest_adapter import PreparedRandomForestModel

__all__ = ["ModelPredictionResult", "ModelPredictor"]

_ALLOWED_PARTITIONS = frozenset({"validation", "test"})
_PROBABILITY_TOLERANCE = 1e-12


def _freeze(value: object) -> object:
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
    if isinstance(value, Mapping):
        return {deepcopy(key): _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    if isinstance(value, frozenset):
        return {_thaw(item) for item in value}
    return deepcopy(value)


def _contains(values: Sequence[object], candidate: object) -> bool:
    return any(candidate == value for value in values)


def _has_duplicates(values: Sequence[object]) -> bool:
    return any(
        value == previous
        for index, value in enumerate(values)
        for previous in values[:index]
    )


@dataclass(frozen=True, slots=True, init=False)
class ModelPredictionResult:
    """Immutable predictions and class probabilities for one partition."""

    dataset_name: str
    dataset_version: str
    partition_name: str
    model_name: str
    identifiers: tuple[object, ...]
    class_labels: tuple[object, ...]
    predictions: tuple[object, ...]
    probabilities: tuple[tuple[float, ...], ...]
    observation_count: int
    metadata: Mapping[str, object]

    def __init__(
        self,
        dataset_name: str,
        dataset_version: str,
        partition_name: str,
        model_name: str,
        identifiers: Sequence[object],
        class_labels: Sequence[object],
        predictions: Sequence[object],
        probabilities: Sequence[Sequence[float]],
        observation_count: int,
        metadata: Mapping[str, object] = MappingProxyType({}),
    ) -> None:
        for name, value in (
            ("dataset_name", dataset_name),
            ("dataset_version", dataset_version),
            ("partition_name", partition_name),
            ("model_name", model_name),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")
        if isinstance(identifiers, (str, bytes)) or isinstance(
            class_labels, (str, bytes)
        ):
            raise TypeError("identifiers and class_labels must be sequences")
        if isinstance(predictions, (str, bytes)) or isinstance(
            probabilities, (str, bytes)
        ):
            raise TypeError("predictions and probabilities must be sequences")
        try:
            normalized_identifiers = tuple(identifiers)
            normalized_labels = tuple(class_labels)
            normalized_predictions = tuple(predictions)
            normalized_probabilities = tuple(
                tuple(float(value) for value in row) for row in probabilities
            )
        except TypeError as error:
            raise TypeError("prediction values must be sequences") from error
        if not normalized_labels:
            raise ValueError("class_labels must not be empty")
        if _has_duplicates(normalized_identifiers):
            raise ValueError("identifiers must be unique")
        if _has_duplicates(normalized_labels):
            raise ValueError("class_labels must be unique")
        if isinstance(observation_count, bool) or not isinstance(
            observation_count, int
        ):
            raise TypeError("observation_count must be an integer")
        if observation_count < 0:
            raise ValueError("observation_count must be non-negative")
        if not (
            len(normalized_identifiers)
            == len(normalized_predictions)
            == len(normalized_probabilities)
            == observation_count
        ):
            raise ValueError("prediction observations must align")
        if any(len(row) != len(normalized_labels) for row in normalized_probabilities):
            raise ValueError("every probability row must match class_labels")
        if any(
            not _contains(normalized_labels, prediction)
            for prediction in normalized_predictions
        ):
            raise ValueError("predictions must belong to class_labels")
        for row in normalized_probabilities:
            if any(
                not math.isfinite(value) or not 0.0 <= value <= 1.0 for value in row
            ):
                raise ValueError("probabilities must be finite and in [0, 1]")
            if not math.isclose(
                math.fsum(row), 1.0, rel_tol=0.0, abs_tol=_PROBABILITY_TOLERANCE
            ):
                raise ValueError("each probability row must sum to one")
        if not isinstance(metadata, Mapping):
            raise TypeError("metadata must be a mapping")

        object.__setattr__(self, "dataset_name", deepcopy(dataset_name))
        object.__setattr__(self, "dataset_version", deepcopy(dataset_version))
        object.__setattr__(self, "partition_name", partition_name)
        object.__setattr__(self, "model_name", model_name)
        object.__setattr__(self, "identifiers", tuple(_freeze(normalized_identifiers)))
        object.__setattr__(self, "class_labels", tuple(_freeze(normalized_labels)))
        object.__setattr__(self, "predictions", tuple(_freeze(normalized_predictions)))
        object.__setattr__(self, "probabilities", normalized_probabilities)
        object.__setattr__(self, "observation_count", observation_count)
        object.__setattr__(self, "metadata", _freeze_mapping(metadata))

    def to_dict(self) -> dict[str, object]:
        """Return a deterministic, detached standard-container representation."""
        return {
            "dataset_name": deepcopy(self.dataset_name),
            "dataset_version": deepcopy(self.dataset_version),
            "partition_name": self.partition_name,
            "model_name": self.model_name,
            "identifiers": _thaw(self.identifiers),
            "class_labels": _thaw(self.class_labels),
            "predictions": _thaw(self.predictions),
            "probabilities": _thaw(self.probabilities),
            "observation_count": self.observation_count,
            "metadata": _thaw(self.metadata),
        }


class ModelPredictor:
    """Predict from supported immutable model snapshots without exposing sklearn."""

    predictor_name = "model-predictor"

    def predict(
        self,
        model: PreparedLogisticRegressionModel | PreparedRandomForestModel,
        prepared_input: PreparedModelInput,
        partition_name: str,
        /,
    ) -> ModelPredictionResult:
        """Predict one validation or test partition in its original order."""
        if not isinstance(
            model, (PreparedLogisticRegressionModel, PreparedRandomForestModel)
        ):
            raise TypeError("unsupported model type")
        if not isinstance(prepared_input, PreparedModelInput):
            raise TypeError("prepared_input must be a PreparedModelInput")
        if not isinstance(partition_name, str):
            raise TypeError("partition_name must be a string")
        if partition_name == "train":
            raise ValueError("training-partition prediction is not permitted")
        if partition_name not in _ALLOWED_PARTITIONS:
            raise ValueError("partition_name must be validation or test")
        self._validate_compatibility(model, prepared_input)

        partition = getattr(prepared_input, partition_name)
        if isinstance(model, PreparedLogisticRegressionModel):
            estimator = self._logistic_estimator(model)
            model_name = "logistic-regression"
        else:
            estimator = self._random_forest_estimator(model, prepared_input)
            model_name = "random-forest"
        raw_predictions = estimator.predict(partition.X)
        raw_probabilities = estimator.predict_proba(partition.X)
        predictions = tuple(self._python_value(value) for value in raw_predictions)
        probabilities = tuple(
            tuple(float(value) for value in row) for row in raw_probabilities
        )

        return ModelPredictionResult(
            dataset_name=prepared_input.dataset_name,
            dataset_version=prepared_input.dataset_version,
            partition_name=partition_name,
            model_name=model_name,
            identifiers=partition.identifiers,
            class_labels=model.class_labels,
            predictions=predictions,
            probabilities=probabilities,
            observation_count=partition.observation_count,
            metadata=model.metadata,
        )

    @staticmethod
    def _validate_compatibility(
        model: PreparedLogisticRegressionModel | PreparedRandomForestModel,
        prepared_input: PreparedModelInput,
    ) -> None:
        if model.dataset_name != prepared_input.dataset_name:
            raise ValueError("dataset_name does not match the trained model")
        if model.dataset_version != prepared_input.dataset_version:
            raise ValueError("dataset_version does not match the trained model")
        if model.target_name != prepared_input.target_name:
            raise ValueError("target_name does not match the trained model")
        if model.feature_names != prepared_input.feature_names:
            raise ValueError("feature schema does not match the trained model")

    @staticmethod
    def _logistic_estimator(
        model: PreparedLogisticRegressionModel,
    ) -> LogisticRegression:
        estimator = LogisticRegression(**model.configuration.to_dict())
        estimator.classes_ = np.asarray(model.class_labels)
        estimator.coef_ = np.asarray(model.coefficients, dtype=float)
        estimator.intercept_ = np.asarray(model.intercepts, dtype=float)
        estimator.n_iter_ = np.asarray(model.iteration_counts, dtype=np.int32)
        estimator.n_features_in_ = len(model.feature_names)
        return estimator

    @staticmethod
    def _random_forest_estimator(
        model: PreparedRandomForestModel, prepared_input: PreparedModelInput
    ) -> RandomForestClassifier:
        estimator = RandomForestClassifier(
            **model.configuration.to_dict(),
            n_jobs=1,
        )
        estimator.fit(prepared_input.train.X, prepared_input.train.y)
        if tuple(
            ModelPredictor._python_value(value) for value in estimator.classes_
        ) != (model.class_labels):
            raise ValueError("reconstructed class_labels do not match the model")
        if tuple(tree.tree_.node_count for tree in estimator.estimators_) != (
            model.tree_node_counts
        ) or tuple(tree.tree_.max_depth for tree in estimator.estimators_) != (
            model.tree_max_depths
        ):
            raise ValueError("random-forest snapshot could not be reconstructed")
        return estimator

    @staticmethod
    def _python_value(value: object) -> object:
        return value.item() if hasattr(value, "item") else deepcopy(value)
