"""Reproducible evaluation of binary experiment-run outputs."""

from __future__ import annotations

from collections.abc import Sequence
from copy import deepcopy
from dataclasses import dataclass, fields
from math import isclose, isfinite, sqrt
from numbers import Real

from experimentation.runner import ExperimentRunResult

__all__ = ["ExperimentEvaluationResult", "ExperimentEvaluator"]


@dataclass(frozen=True, slots=True, init=False)
class ExperimentEvaluationResult:
    """Immutable snapshot of binary prediction and probability metrics."""

    experiment_id: str
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

    def __init__(
        self,
        experiment_id: str,
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
    ) -> None:
        if not experiment_id:
            raise ValueError("experiment_id must not be empty")

        labels = tuple(deepcopy(tuple(class_labels)))
        detached_positive_label = deepcopy(positive_label)
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

        _validate_rate(positive_rate, "positive_rate")
        metric_values = {
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "mcc": mcc,
            "roc_auc": roc_auc,
            "pr_auc": pr_auc,
            "brier_score": brier_score,
        }
        for name, value in metric_values.items():
            _validate_finite_number(value, name)

        values: dict[str, object] = {
            "experiment_id": deepcopy(experiment_id),
            "positive_label": detached_positive_label,
            "class_labels": labels,
            **counts,
            "positive_rate": float(positive_rate),
            **{name: float(value) for name, value in metric_values.items()},
        }
        for name, value in values.items():
            object.__setattr__(self, name, value)

    def to_dict(self) -> dict[str, object]:
        """Return a detached dictionary made from standard Python structures."""
        result = {
            field.name: deepcopy(getattr(self, field.name)) for field in fields(self)
        }
        result["class_labels"] = list(result["class_labels"])
        return result


class ExperimentEvaluator:
    """Evaluate one binary :class:`ExperimentRunResult` deterministically."""

    def __init__(self, *, positive_label: object) -> None:
        self._positive_label = deepcopy(positive_label)

    @property
    def positive_label(self) -> object:
        """Return a detached copy of the explicitly configured positive label."""
        return deepcopy(self._positive_label)

    def evaluate(
        self,
        result: ExperimentRunResult,
        targets: Sequence[object],
    ) -> ExperimentEvaluationResult:
        """Calculate binary metrics without modifying run outputs or targets."""
        if result is None:
            raise ValueError("result must not be None")
        if not targets:
            raise ValueError("targets must not be empty")

        labels = tuple(result.class_labels)
        if len(labels) != 2 or labels[0] == labels[1]:
            raise ValueError(
                "result.class_labels must contain exactly two distinct labels"
            )
        if not _contains(labels, self._positive_label):
            raise ValueError("positive_label must belong to result.class_labels")

        target_values = tuple(targets)
        predictions = tuple(result.predictions)
        probabilities = tuple(tuple(row) for row in result.probabilities)
        count = len(target_values)
        if count != result.evaluation_observation_count:
            raise ValueError(
                "target count must equal result.evaluation_observation_count"
            )
        if count != len(predictions):
            raise ValueError("target count must equal prediction count")
        if count != len(probabilities):
            raise ValueError("target count must equal probability-row count")

        for target in target_values:
            if not _contains(labels, target):
                raise ValueError("every target must belong to result.class_labels")
        for prediction in predictions:
            if not _contains(labels, prediction):
                raise ValueError("every prediction must belong to result.class_labels")
        for row in probabilities:
            if len(row) != len(labels):
                raise ValueError(
                    "each probability row must have one value per class label"
                )
            for value in row:
                _validate_rate(value, "probability value")
            if not isclose(sum(row), 1.0, rel_tol=1e-9, abs_tol=1e-9):
                raise ValueError("each probability row must sum to one")

        positive_index = _index(labels, self._positive_label)
        target_positive = tuple(
            int(target == self._positive_label) for target in target_values
        )
        prediction_positive = tuple(
            prediction == self._positive_label for prediction in predictions
        )
        positive_probabilities = tuple(
            float(row[positive_index]) for row in probabilities
        )

        positive_count = sum(target_positive)
        if positive_count in (0, count):
            raise ValueError(
                "ROC-AUC and PR-AUC require both target classes to be represented"
            )

        true_positive = sum(
            actual and predicted
            for actual, predicted in zip(
                target_positive, prediction_positive, strict=True
            )
        )
        false_negative = sum(
            actual and not predicted
            for actual, predicted in zip(
                target_positive, prediction_positive, strict=True
            )
        )
        false_positive = sum(
            not actual and predicted
            for actual, predicted in zip(
                target_positive, prediction_positive, strict=True
            )
        )
        true_negative = count - true_positive - false_negative - false_positive

        accuracy = (true_positive + true_negative) / count
        precision = _safe_ratio(true_positive, true_positive + false_positive)
        recall = _safe_ratio(true_positive, true_positive + false_negative)
        f1 = _safe_ratio(2 * precision * recall, precision + recall)
        mcc_numerator = true_positive * true_negative - false_positive * false_negative
        mcc_denominator = sqrt(
            (true_positive + false_positive)
            * (true_positive + false_negative)
            * (true_negative + false_positive)
            * (true_negative + false_negative)
        )
        mcc = _safe_ratio(mcc_numerator, mcc_denominator)
        brier_score = (
            sum(
                (probability - actual) ** 2
                for probability, actual in zip(
                    positive_probabilities, target_positive, strict=True
                )
            )
            / count
        )

        return ExperimentEvaluationResult(
            experiment_id=result.experiment_id,
            positive_label=self._positive_label,
            class_labels=labels,
            observation_count=count,
            positive_count=positive_count,
            positive_rate=positive_count / count,
            true_negative=true_negative,
            false_positive=false_positive,
            false_negative=false_negative,
            true_positive=true_positive,
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1=f1,
            mcc=mcc,
            roc_auc=_roc_auc(target_positive, positive_probabilities),
            pr_auc=_average_precision(target_positive, positive_probabilities),
            brier_score=brier_score,
        )


def _contains(values: Sequence[object], candidate: object) -> bool:
    return any(candidate == value for value in values)


def _index(values: Sequence[object], candidate: object) -> int:
    return next(index for index, value in enumerate(values) if candidate == value)


def _validate_count(value: object, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer and must not be bool")
    if value < 0:
        raise ValueError(f"{name} must be non-negative")


def _validate_finite_number(value: object, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{name} must be numeric and must not be bool")
    if not isfinite(value):
        raise ValueError(f"{name} must be finite")


def _validate_rate(value: object, name: str) -> None:
    _validate_finite_number(value, name)
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be in the range [0.0, 1.0]")


def _safe_ratio(numerator: Real, denominator: Real) -> float:
    return float(numerator / denominator) if denominator else 0.0


def _roc_auc(targets: Sequence[int], probabilities: Sequence[float]) -> float:
    positive_scores = [
        score for target, score in zip(targets, probabilities, strict=True) if target
    ]
    negative_scores = [
        score
        for target, score in zip(targets, probabilities, strict=True)
        if not target
    ]
    concordance = sum(
        1.0 if positive > negative else 0.5 if positive == negative else 0.0
        for positive in positive_scores
        for negative in negative_scores
    )
    return concordance / (len(positive_scores) * len(negative_scores))


def _average_precision(targets: Sequence[int], probabilities: Sequence[float]) -> float:
    ranked = sorted(
        zip(probabilities, targets, strict=True), key=lambda item: item[0], reverse=True
    )
    total_positive = sum(targets)
    seen = 0
    true_positive = 0
    weighted_precision = 0.0
    index = 0
    while index < len(ranked):
        score = ranked[index][0]
        group_positive = 0
        group_size = 0
        while index < len(ranked) and ranked[index][0] == score:
            group_positive += ranked[index][1]
            group_size += 1
            index += 1
        seen += group_size
        true_positive += group_positive
        weighted_precision += group_positive * true_positive / seen
    return weighted_precision / total_positive
