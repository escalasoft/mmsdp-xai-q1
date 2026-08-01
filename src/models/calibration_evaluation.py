"""Deterministic evaluation and comparison of binary probability calibration."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from numbers import Integral, Real
from types import MappingProxyType

from models.calibration import CalibratedPredictionResult
from models.prediction import ModelPredictionResult

__all__ = [
    "CalibrationBinResult",
    "ProbabilityCalibrationEvaluation",
    "ProbabilityCalibrationComparison",
    "ProbabilityCalibrationEvaluator",
]

_METHODS = frozenset({"uncalibrated", "platt", "isotonic"})
_PARTITIONS = frozenset({"validation", "test"})
_TOLERANCE = 1e-12


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
    if not isinstance(value, Mapping):
        raise TypeError("metadata must be a mapping")
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


def _number(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{name} must be numeric and must not be bool")
    normalized = float(value)
    if not math.isfinite(normalized):
        raise ValueError(f"{name} must be finite")
    return normalized


def _probability(name: str, value: object) -> float:
    normalized = _number(name, value)
    if not 0.0 <= normalized <= 1.0:
        raise ValueError(f"{name} must be in [0, 1]")
    return normalized


def _integer(name: str, value: object, *, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise TypeError(f"{name} must be an integer and must not be bool")
    normalized = int(value)
    if normalized < minimum:
        raise ValueError(f"{name} must be at least {minimum}")
    return normalized


def _close(left: float, right: float) -> bool:
    return math.isclose(left, right, rel_tol=0.0, abs_tol=_TOLERANCE)


@dataclass(frozen=True, slots=True, init=False)
class CalibrationBinResult:
    """Immutable statistics for one reliability-diagram bin."""

    lower_bound: float
    upper_bound: float
    observation_count: int
    mean_predicted_probability: float
    observed_positive_rate: float
    absolute_calibration_error: float

    def __init__(
        self,
        lower_bound: float,
        upper_bound: float,
        observation_count: int,
        mean_predicted_probability: float,
        observed_positive_rate: float,
        absolute_calibration_error: float,
    ) -> None:
        lower = _probability("lower_bound", lower_bound)
        upper = _probability("upper_bound", upper_bound)
        if lower >= upper:
            raise ValueError("lower_bound must be strictly smaller than upper_bound")
        count = _integer("observation_count", observation_count, minimum=0)
        mean = _probability("mean_predicted_probability", mean_predicted_probability)
        rate = _probability("observed_positive_rate", observed_positive_rate)
        error = _probability("absolute_calibration_error", absolute_calibration_error)
        if count == 0:
            if (mean, rate, error) != (0.0, 0.0, 0.0):
                raise ValueError("empty bins must use zero statistics")
        elif not _close(error, abs(mean - rate)):
            raise ValueError(
                "absolute_calibration_error must equal the absolute bin difference"
            )
        object.__setattr__(self, "lower_bound", lower)
        object.__setattr__(self, "upper_bound", upper)
        object.__setattr__(self, "observation_count", count)
        object.__setattr__(self, "mean_predicted_probability", mean)
        object.__setattr__(self, "observed_positive_rate", rate)
        object.__setattr__(self, "absolute_calibration_error", error)

    def to_dict(self) -> dict[str, object]:
        """Return a detached standard-container representation."""
        return {
            "lower_bound": self.lower_bound,
            "upper_bound": self.upper_bound,
            "observation_count": self.observation_count,
            "mean_predicted_probability": self.mean_predicted_probability,
            "observed_positive_rate": self.observed_positive_rate,
            "absolute_calibration_error": self.absolute_calibration_error,
        }


@dataclass(frozen=True, slots=True, init=False)
class ProbabilityCalibrationEvaluation:
    """Immutable calibration-quality snapshot for one prediction result."""

    dataset_name: str
    dataset_version: str
    partition_name: str
    model_name: str
    calibration_method: str
    positive_label: object
    class_labels: tuple[object, ...]
    observation_count: int
    positive_count: int
    positive_rate: float
    bin_count: int
    bins: tuple[CalibrationBinResult, ...]
    brier_score: float
    expected_calibration_error: float
    maximum_calibration_error: float
    metadata: Mapping[str, object]

    def __init__(
        self,
        dataset_name: str,
        dataset_version: str,
        partition_name: str,
        model_name: str,
        calibration_method: str,
        positive_label: object,
        class_labels: Sequence[object],
        observation_count: int,
        positive_count: int,
        positive_rate: float,
        bin_count: int,
        bins: Sequence[CalibrationBinResult],
        brier_score: float,
        expected_calibration_error: float,
        maximum_calibration_error: float,
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
        if partition_name not in _PARTITIONS:
            raise ValueError("partition_name must be validation or test")
        if calibration_method not in _METHODS:
            raise ValueError(
                "calibration_method must be uncalibrated, platt, or isotonic"
            )
        if isinstance(class_labels, (str, bytes)):
            raise TypeError("class_labels must be a sequence")
        try:
            labels = tuple(_freeze(tuple(class_labels)))
        except TypeError as error:
            raise TypeError("class_labels must be a sequence") from error
        if len(labels) != 2 or _has_duplicates(labels):
            raise ValueError("class_labels must contain exactly two distinct labels")
        detached_positive = _freeze(positive_label)
        if not _contains(labels, detached_positive):
            raise ValueError("positive_label must belong to class_labels")
        observations = _integer("observation_count", observation_count, minimum=1)
        positives = _integer("positive_count", positive_count, minimum=0)
        if positives > observations:
            raise ValueError("positive_count must not exceed observation_count")
        rate = _probability("positive_rate", positive_rate)
        if not _close(rate, positives / observations):
            raise ValueError(
                "positive_rate must equal positive_count / observation_count"
            )
        normalized_bin_count = _integer("bin_count", bin_count, minimum=2)
        if isinstance(bins, (str, bytes)):
            raise TypeError("bins must be a sequence")
        try:
            normalized_bins = tuple(bins)
        except TypeError as error:
            raise TypeError("bins must be a sequence") from error
        if len(normalized_bins) != normalized_bin_count:
            raise ValueError("len(bins) must equal bin_count")
        if any(not isinstance(item, CalibrationBinResult) for item in normalized_bins):
            raise TypeError("bins must contain CalibrationBinResult values")
        if (
            normalized_bins[0].lower_bound != 0.0
            or normalized_bins[-1].upper_bound != 1.0
        ):
            raise ValueError("bins must cover [0, 1]")
        if any(
            left.upper_bound != right.lower_bound
            for left, right in zip(normalized_bins, normalized_bins[1:], strict=False)
        ):
            raise ValueError("bins must be ordered, contiguous, and non-overlapping")
        if (
            math.fsum(item.observation_count for item in normalized_bins)
            != observations
        ):
            raise ValueError("bin observation counts must sum to observation_count")
        brier = _probability("brier_score", brier_score)
        ece = _probability("expected_calibration_error", expected_calibration_error)
        mce = _probability("maximum_calibration_error", maximum_calibration_error)
        expected_ece = (
            math.fsum(
                item.observation_count * item.absolute_calibration_error
                for item in normalized_bins
            )
            / observations
        )
        expected_mce = max(item.absolute_calibration_error for item in normalized_bins)
        if not _close(ece, expected_ece):
            raise ValueError("expected_calibration_error is inconsistent with bins")
        if not _close(mce, expected_mce):
            raise ValueError("maximum_calibration_error is inconsistent with bins")

        for name, value in (
            ("dataset_name", dataset_name),
            ("dataset_version", dataset_version),
            ("partition_name", partition_name),
            ("model_name", model_name),
            ("calibration_method", calibration_method),
        ):
            object.__setattr__(self, name, deepcopy(value))
        object.__setattr__(self, "positive_label", detached_positive)
        object.__setattr__(self, "class_labels", labels)
        object.__setattr__(self, "observation_count", observations)
        object.__setattr__(self, "positive_count", positives)
        object.__setattr__(self, "positive_rate", rate)
        object.__setattr__(self, "bin_count", normalized_bin_count)
        object.__setattr__(self, "bins", normalized_bins)
        object.__setattr__(self, "brier_score", brier)
        object.__setattr__(self, "expected_calibration_error", ece)
        object.__setattr__(self, "maximum_calibration_error", mce)
        object.__setattr__(self, "metadata", _freeze_mapping(metadata))

    def to_dict(self) -> dict[str, object]:
        """Return a detached representation using mutable standard containers."""
        return {
            "dataset_name": deepcopy(self.dataset_name),
            "dataset_version": deepcopy(self.dataset_version),
            "partition_name": deepcopy(self.partition_name),
            "model_name": deepcopy(self.model_name),
            "calibration_method": self.calibration_method,
            "positive_label": _thaw(self.positive_label),
            "class_labels": _thaw(self.class_labels),
            "observation_count": self.observation_count,
            "positive_count": self.positive_count,
            "positive_rate": self.positive_rate,
            "bin_count": self.bin_count,
            "bins": [item.to_dict() for item in self.bins],
            "brier_score": self.brier_score,
            "expected_calibration_error": self.expected_calibration_error,
            "maximum_calibration_error": self.maximum_calibration_error,
            "metadata": _thaw(self.metadata),
        }


@dataclass(frozen=True, slots=True, init=False)
class ProbabilityCalibrationComparison:
    """Immutable comparison of uncalibrated and calibrated evaluations."""

    before: ProbabilityCalibrationEvaluation
    after: ProbabilityCalibrationEvaluation
    brier_score_change: float
    expected_calibration_error_change: float
    maximum_calibration_error_change: float
    brier_score_improved: bool
    expected_calibration_error_improved: bool
    maximum_calibration_error_improved: bool
    metadata: Mapping[str, object]

    def __init__(
        self,
        before: ProbabilityCalibrationEvaluation,
        after: ProbabilityCalibrationEvaluation,
        brier_score_change: float,
        expected_calibration_error_change: float,
        maximum_calibration_error_change: float,
        brier_score_improved: bool,
        expected_calibration_error_improved: bool,
        maximum_calibration_error_improved: bool,
        metadata: Mapping[str, object] = MappingProxyType({}),
    ) -> None:
        if not isinstance(before, ProbabilityCalibrationEvaluation) or not isinstance(
            after, ProbabilityCalibrationEvaluation
        ):
            raise TypeError("before and after must be calibration evaluations")
        if before.calibration_method != "uncalibrated":
            raise ValueError("before must use uncalibrated calibration_method")
        if after.calibration_method not in {"platt", "isotonic"}:
            raise ValueError("after must use platt or isotonic calibration_method")
        for name in (
            "dataset_name",
            "dataset_version",
            "partition_name",
            "model_name",
            "positive_label",
            "class_labels",
            "observation_count",
            "positive_count",
            "positive_rate",
            "bin_count",
        ):
            if getattr(before, name) != getattr(after, name):
                raise ValueError(f"before and after {name} must match")
        supplied_changes = {
            "brier_score_change": brier_score_change,
            "expected_calibration_error_change": expected_calibration_error_change,
            "maximum_calibration_error_change": maximum_calibration_error_change,
        }
        expected_changes = {
            "brier_score_change": after.brier_score - before.brier_score,
            "expected_calibration_error_change": (
                after.expected_calibration_error - before.expected_calibration_error
            ),
            "maximum_calibration_error_change": (
                after.maximum_calibration_error - before.maximum_calibration_error
            ),
        }
        normalized_changes = {
            name: _number(name, value) for name, value in supplied_changes.items()
        }
        for name, expected in expected_changes.items():
            if not _close(normalized_changes[name], expected):
                raise ValueError(f"{name} is inconsistent with evaluations")
        supplied_flags = {
            "brier_score_improved": brier_score_improved,
            "expected_calibration_error_improved": (
                expected_calibration_error_improved
            ),
            "maximum_calibration_error_improved": maximum_calibration_error_improved,
        }
        for flag_name, flag in supplied_flags.items():
            if not isinstance(flag, bool):
                raise TypeError(f"{flag_name} must be bool")
            change_name = flag_name.removesuffix("_improved") + "_change"
            if flag is not (expected_changes[change_name] < 0.0):
                raise ValueError(f"{flag_name} is inconsistent with its change")
        object.__setattr__(self, "before", before)
        object.__setattr__(self, "after", after)
        for name, value in normalized_changes.items():
            object.__setattr__(self, name, value)
        for name, value in supplied_flags.items():
            object.__setattr__(self, name, value)
        object.__setattr__(self, "metadata", _freeze_mapping(metadata))

    def to_dict(self) -> dict[str, object]:
        """Return a deterministic, detached standard-container representation."""
        return {
            "before": self.before.to_dict(),
            "after": self.after.to_dict(),
            "brier_score_change": self.brier_score_change,
            "expected_calibration_error_change": (
                self.expected_calibration_error_change
            ),
            "maximum_calibration_error_change": self.maximum_calibration_error_change,
            "brier_score_improved": self.brier_score_improved,
            "expected_calibration_error_improved": (
                self.expected_calibration_error_improved
            ),
            "maximum_calibration_error_improved": (
                self.maximum_calibration_error_improved
            ),
            "metadata": _thaw(self.metadata),
        }


class ProbabilityCalibrationEvaluator:
    """Evaluate binary probabilities with explicit equal-width bins."""

    evaluator_name = "probability-calibration-evaluator"

    def __init__(self, *, positive_label: object, bin_count: int = 10) -> None:
        self._positive_label = _freeze(positive_label)
        self._bin_count = _integer("bin_count", bin_count, minimum=2)

    @property
    def positive_label(self) -> object:
        """Return a detached copy of the configured positive label."""
        return _thaw(self._positive_label)

    @property
    def bin_count(self) -> int:
        return self._bin_count

    def evaluate_uncalibrated(
        self,
        prediction_result: ModelPredictionResult,
        targets: Sequence[object],
    ) -> ProbabilityCalibrationEvaluation:
        """Evaluate original, uncalibrated probabilities."""
        if not isinstance(prediction_result, ModelPredictionResult):
            raise TypeError("prediction_result must be a ModelPredictionResult")
        return self._evaluate(prediction_result, targets, "uncalibrated")

    def evaluate_calibrated(
        self,
        prediction_result: CalibratedPredictionResult,
        targets: Sequence[object],
    ) -> ProbabilityCalibrationEvaluation:
        """Evaluate probabilities already produced by a fitted calibrator."""
        if not isinstance(prediction_result, CalibratedPredictionResult):
            raise TypeError("prediction_result must be a CalibratedPredictionResult")
        if prediction_result.positive_label != self._positive_label:
            raise ValueError(
                "positive_label does not match calibrated prediction result"
            )
        return self._evaluate(
            prediction_result, targets, prediction_result.calibration_method
        )

    def _evaluate(
        self,
        prediction_result: ModelPredictionResult | CalibratedPredictionResult,
        targets: Sequence[object],
        calibration_method: str,
    ) -> ProbabilityCalibrationEvaluation:
        labels = tuple(prediction_result.class_labels)
        if len(labels) != 2 or _has_duplicates(labels):
            raise ValueError("class_labels must contain exactly two distinct labels")
        if not _contains(labels, self._positive_label):
            raise ValueError("positive_label must belong to class_labels")
        if targets is None or isinstance(targets, (str, bytes)):
            raise TypeError("targets must be a non-empty sequence")
        try:
            normalized_targets = tuple(targets)
        except TypeError as error:
            raise TypeError("targets must be a non-empty sequence") from error
        if not normalized_targets:
            raise ValueError("targets must not be empty")
        if len(normalized_targets) != prediction_result.observation_count:
            raise ValueError("target count must equal observation_count")
        if any(not _contains(labels, target) for target in normalized_targets):
            raise ValueError("targets must belong to class_labels")
        positive_index = next(
            index for index, label in enumerate(labels) if label == self._positive_label
        )
        probabilities = tuple(
            _probability("positive probability", row[positive_index])
            for row in prediction_result.probabilities
        )
        binary_targets = tuple(
            int(target == self._positive_label) for target in normalized_targets
        )
        positive_count = sum(binary_targets)
        grouped_probabilities: list[list[float]] = [[] for _ in range(self.bin_count)]
        grouped_targets: list[list[int]] = [[] for _ in range(self.bin_count)]
        for probability, target in zip(probabilities, binary_targets, strict=True):
            index = min(int(probability * self.bin_count), self.bin_count - 1)
            grouped_probabilities[index].append(probability)
            grouped_targets[index].append(target)
        bins: list[CalibrationBinResult] = []
        for index, (values, outcomes) in enumerate(
            zip(grouped_probabilities, grouped_targets, strict=True)
        ):
            count = len(values)
            mean = math.fsum(values) / count if count else 0.0
            rate = math.fsum(outcomes) / count if count else 0.0
            error = abs(mean - rate) if count else 0.0
            bins.append(
                CalibrationBinResult(
                    index / self.bin_count,
                    (index + 1) / self.bin_count,
                    count,
                    mean,
                    rate,
                    error,
                )
            )
        observations = prediction_result.observation_count
        brier = (
            math.fsum(
                (probability - target) ** 2
                for probability, target in zip(
                    probabilities, binary_targets, strict=True
                )
            )
            / observations
        )
        ece = (
            math.fsum(
                item.observation_count * item.absolute_calibration_error
                for item in bins
            )
            / observations
        )
        mce = max(item.absolute_calibration_error for item in bins)
        return ProbabilityCalibrationEvaluation(
            dataset_name=prediction_result.dataset_name,
            dataset_version=prediction_result.dataset_version,
            partition_name=prediction_result.partition_name,
            model_name=prediction_result.model_name,
            calibration_method=calibration_method,
            positive_label=self._positive_label,
            class_labels=labels,
            observation_count=observations,
            positive_count=positive_count,
            positive_rate=positive_count / observations,
            bin_count=self.bin_count,
            bins=bins,
            brier_score=brier,
            expected_calibration_error=ece,
            maximum_calibration_error=mce,
            metadata=prediction_result.metadata,
        )

    def compare(
        self,
        before: ProbabilityCalibrationEvaluation,
        after: ProbabilityCalibrationEvaluation,
    ) -> ProbabilityCalibrationComparison:
        """Compare calibrated metrics against their uncalibrated baseline."""
        if not isinstance(before, ProbabilityCalibrationEvaluation) or not isinstance(
            after, ProbabilityCalibrationEvaluation
        ):
            raise TypeError("before and after must be calibration evaluations")
        changes = {
            "brier_score_change": after.brier_score - before.brier_score,
            "expected_calibration_error_change": (
                after.expected_calibration_error - before.expected_calibration_error
            ),
            "maximum_calibration_error_change": (
                after.maximum_calibration_error - before.maximum_calibration_error
            ),
        }
        return ProbabilityCalibrationComparison(
            before=before,
            after=after,
            **changes,
            brier_score_improved=changes["brier_score_change"] < 0.0,
            expected_calibration_error_improved=(
                changes["expected_calibration_error_change"] < 0.0
            ),
            maximum_calibration_error_improved=(
                changes["maximum_calibration_error_change"] < 0.0
            ),
        )
