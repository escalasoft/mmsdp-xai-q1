"""Reproducible evaluation of deterministic model predictions."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from math import isfinite
from numbers import Real
from types import MappingProxyType

from experimentation.evaluation import ExperimentEvaluationResult, ExperimentEvaluator
from experimentation.runner import ExperimentRunResult
from models.prediction import ModelPredictionResult

__all__ = ["ModelEvaluationResult", "ModelPredictionEvaluator"]


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


def _validate_count(value: object, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer and must not be bool")
    if value < 0:
        raise ValueError(f"{name} must be non-negative")


def _validate_metric(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{name} must be numeric and must not be bool")
    if not isfinite(value):
        raise ValueError(f"{name} must be finite")
    return float(value)


@dataclass(frozen=True, slots=True, init=False)
class ModelEvaluationResult:
    """Immutable framework-neutral evaluation of one prediction result."""

    dataset_name: str
    dataset_version: str
    partition_name: str
    model_name: str
    positive_label: object
    class_labels: tuple[object, ...]
    observation_count: int
    positive_count: int
    positive_rate: float
    true_negative: int
    false_positive: int
    false_negative: int
    true_positive: int
    accuracy: float
    precision: float
    recall: float
    f1: float
    mcc: float
    roc_auc: float
    pr_auc: float
    brier_score: float
    metadata: Mapping[str, object]

    def __init__(
        self,
        dataset_name: str,
        dataset_version: str,
        partition_name: str,
        model_name: str,
        positive_label: object,
        class_labels: Sequence[object],
        observation_count: int,
        positive_count: int,
        positive_rate: float,
        true_negative: int,
        false_positive: int,
        false_negative: int,
        true_positive: int,
        accuracy: float,
        precision: float,
        recall: float,
        f1: float,
        mcc: float,
        roc_auc: float,
        pr_auc: float,
        brier_score: float,
        metadata: Mapping[str, object] = MappingProxyType({}),
    ) -> None:
        names = {
            "dataset_name": dataset_name,
            "dataset_version": dataset_version,
            "partition_name": partition_name,
            "model_name": model_name,
        }
        for name, value in names.items():
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")
        if isinstance(class_labels, (str, bytes)):
            raise TypeError("class_labels must be a sequence")
        labels = tuple(_freeze(tuple(class_labels)))
        detached_positive_label = _freeze(positive_label)
        if len(labels) != 2 or labels[0] == labels[1]:
            raise ValueError("class_labels must contain exactly two distinct labels")
        if not _contains(labels, detached_positive_label):
            raise ValueError("positive_label must belong to class_labels")

        counts = {
            "observation_count": observation_count,
            "positive_count": positive_count,
            "true_negative": true_negative,
            "false_positive": false_positive,
            "false_negative": false_negative,
            "true_positive": true_positive,
        }
        for name, value in counts.items():
            _validate_count(value, name)
        if observation_count != sum(
            (true_negative, false_positive, false_negative, true_positive)
        ):
            raise ValueError(
                "observation_count must equal the sum of confusion-matrix counts"
            )
        if positive_count != true_positive + false_negative:
            raise ValueError("positive_count must equal true_positive + false_negative")

        normalized_metrics = {
            name: _validate_metric(value, name)
            for name, value in {
                "positive_rate": positive_rate,
                "accuracy": accuracy,
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "mcc": mcc,
                "roc_auc": roc_auc,
                "pr_auc": pr_auc,
                "brier_score": brier_score,
            }.items()
        }
        for name in (
            "positive_rate",
            "accuracy",
            "precision",
            "recall",
            "f1",
            "roc_auc",
            "pr_auc",
            "brier_score",
        ):
            if not 0.0 <= normalized_metrics[name] <= 1.0:
                raise ValueError(f"{name} must be in the range [0.0, 1.0]")
        if not -1.0 <= normalized_metrics["mcc"] <= 1.0:
            raise ValueError("mcc must be in the range [-1.0, 1.0]")
        if not isinstance(metadata, Mapping):
            raise TypeError("metadata must be a mapping")

        for name, value in names.items():
            object.__setattr__(self, name, deepcopy(value))
        object.__setattr__(self, "positive_label", detached_positive_label)
        object.__setattr__(self, "class_labels", labels)
        for name, value in counts.items():
            object.__setattr__(self, name, value)
        for name, value in normalized_metrics.items():
            object.__setattr__(self, name, value)
        object.__setattr__(self, "metadata", _freeze(metadata))

    def to_dict(self) -> dict[str, object]:
        """Return a detached representation using mutable standard containers."""
        return {
            "dataset_name": deepcopy(self.dataset_name),
            "dataset_version": deepcopy(self.dataset_version),
            "partition_name": deepcopy(self.partition_name),
            "model_name": deepcopy(self.model_name),
            "positive_label": _thaw(self.positive_label),
            "class_labels": _thaw(self.class_labels),
            "observation_count": self.observation_count,
            "positive_count": self.positive_count,
            "positive_rate": self.positive_rate,
            "true_negative": self.true_negative,
            "false_positive": self.false_positive,
            "false_negative": self.false_negative,
            "true_positive": self.true_positive,
            "accuracy": self.accuracy,
            "precision": self.precision,
            "recall": self.recall,
            "f1": self.f1,
            "mcc": self.mcc,
            "roc_auc": self.roc_auc,
            "pr_auc": self.pr_auc,
            "brier_score": self.brier_score,
            "metadata": _thaw(self.metadata),
        }


class ModelPredictionEvaluator:
    """Evaluate one deterministic model-prediction result."""

    evaluator_name = "model-prediction-evaluator"

    def __init__(self, *, positive_label: object) -> None:
        self._positive_label = _freeze(positive_label)

    @property
    def positive_label(self) -> object:
        """Return a detached copy of the configured positive label."""
        return _thaw(self._positive_label)

    def evaluate(
        self,
        prediction_result: ModelPredictionResult,
        targets: Sequence[object],
    ) -> ModelEvaluationResult:
        """Delegate metric calculation to :class:`ExperimentEvaluator`."""
        if not isinstance(prediction_result, ModelPredictionResult):
            raise TypeError("prediction_result must be a ModelPredictionResult")
        if targets is None:
            raise ValueError("targets must not be None")
        target_values = tuple(targets)
        if not target_values:
            raise ValueError("targets must not be empty")
        if len(target_values) != prediction_result.observation_count:
            raise ValueError(
                "target count must equal prediction_result.observation_count"
            )

        labels = tuple(prediction_result.class_labels)
        if len(labels) != 2 or labels[0] == labels[1]:
            raise ValueError("class_labels must contain exactly two distinct labels")
        if not _contains(labels, self._positive_label):
            raise ValueError(
                "positive_label must belong to prediction_result.class_labels"
            )
        if any(not _contains(labels, target) for target in target_values):
            raise ValueError(
                "every target must belong to prediction_result.class_labels"
            )

        bridge = ExperimentRunResult(
            experiment_id="model-prediction-evaluation",
            class_labels=labels,
            predictions=prediction_result.predictions,
            probabilities=prediction_result.probabilities,
            training_observation_count=0,
            evaluation_observation_count=prediction_result.observation_count,
        )
        metrics: ExperimentEvaluationResult = ExperimentEvaluator(
            positive_label=self._positive_label
        ).evaluate(bridge, target_values)
        return ModelEvaluationResult(
            dataset_name=prediction_result.dataset_name,
            dataset_version=prediction_result.dataset_version,
            partition_name=prediction_result.partition_name,
            model_name=prediction_result.model_name,
            positive_label=metrics.positive_label,
            class_labels=metrics.class_labels,
            observation_count=metrics.observation_count,
            positive_count=metrics.positive_count,
            positive_rate=metrics.positive_rate,
            true_negative=metrics.true_negative,
            false_positive=metrics.false_positive,
            false_negative=metrics.false_negative,
            true_positive=metrics.true_positive,
            accuracy=metrics.accuracy,
            precision=metrics.precision,
            recall=metrics.recall,
            f1=metrics.f1,
            mcc=metrics.mcc,
            roc_auc=metrics.roc_auc,
            pr_auc=metrics.pr_auc,
            brier_score=metrics.brier_score,
            metadata=prediction_result.metadata,
        )
