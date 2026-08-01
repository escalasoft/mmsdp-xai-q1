"""Deterministic binary probability calibration."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from types import MappingProxyType

import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression

from models.prediction import ModelPredictionResult

__all__ = [
    "ProbabilityCalibrationConfiguration",
    "PreparedProbabilityCalibrator",
    "CalibratedPredictionResult",
    "ModelProbabilityCalibrator",
]

_METHODS = frozenset({"platt", "isotonic"})
_PARTITIONS = frozenset({"validation", "test"})
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


def _index(values: Sequence[object], candidate: object) -> int:
    for index, value in enumerate(values):
        if candidate == value:
            return index
    raise ValueError("positive_label must belong to class_labels")


def _has_duplicates(values: Sequence[object]) -> bool:
    return any(
        value == previous
        for index, value in enumerate(values)
        for previous in values[:index]
    )


def _validate_name(name: str, value: object) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


def _validate_method(method: object) -> None:
    if not isinstance(method, str) or not method.strip():
        raise ValueError("method must be a non-empty string")
    if method not in _METHODS:
        raise ValueError("method must be platt or isotonic")


def _normalized_binary_labels(class_labels: Sequence[object]) -> tuple[object, ...]:
    if isinstance(class_labels, (str, bytes)):
        raise TypeError("class_labels must be a sequence")
    try:
        labels = tuple(class_labels)
    except TypeError as error:
        raise TypeError("class_labels must be a sequence") from error
    if len(labels) != 2 or _has_duplicates(labels):
        raise ValueError("class_labels must contain exactly two distinct labels")
    return tuple(_freeze(labels))


def _finite_float(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float, np.number)):
        raise TypeError(f"{name} must be numeric")
    normalized = float(value)
    if not math.isfinite(normalized):
        raise ValueError(f"{name} must be finite")
    return normalized


def _normalize_parameters(
    method: str, parameters: Mapping[str, object]
) -> dict[str, object]:
    if not isinstance(parameters, Mapping):
        raise TypeError("parameters must be a mapping")
    if method == "platt":
        if set(parameters) != {"coefficient", "intercept"}:
            raise ValueError("platt parameters must contain coefficient and intercept")
        return {
            "coefficient": _finite_float("coefficient", parameters["coefficient"]),
            "intercept": _finite_float("intercept", parameters["intercept"]),
        }
    if set(parameters) != {"x_thresholds", "y_thresholds"}:
        raise ValueError(
            "isotonic parameters must contain x_thresholds and y_thresholds"
        )
    try:
        x_values = tuple(
            _finite_float("x_thresholds", value)
            for value in parameters["x_thresholds"]  # type: ignore[union-attr]
        )
        y_values = tuple(
            _finite_float("y_thresholds", value)
            for value in parameters["y_thresholds"]  # type: ignore[union-attr]
        )
    except TypeError as error:
        raise TypeError("isotonic thresholds must be sequences") from error
    if not x_values or len(x_values) != len(y_values):
        raise ValueError("isotonic thresholds must be non-empty and align")
    if any(right <= left for left, right in zip(x_values, x_values[1:], strict=False)):
        raise ValueError("x_thresholds must be strictly increasing")
    if any(not 0.0 <= value <= 1.0 for value in y_values):
        raise ValueError("y_thresholds must be in [0, 1]")
    return {"x_thresholds": x_values, "y_thresholds": y_values}


@dataclass(frozen=True, slots=True, init=False)
class ProbabilityCalibrationConfiguration:
    """Immutable probability-calibration configuration."""

    method: str
    positive_label: object

    def __init__(self, method: str, positive_label: object) -> None:
        _validate_method(method)
        object.__setattr__(self, "method", deepcopy(method))
        object.__setattr__(self, "positive_label", _freeze(positive_label))

    def to_dict(self) -> dict[str, object]:
        """Return a deterministic, detached standard-container representation."""
        return {"method": self.method, "positive_label": _thaw(self.positive_label)}


@dataclass(frozen=True, slots=True, init=False)
class PreparedProbabilityCalibrator:
    """Framework-neutral immutable snapshot of a fitted calibrator."""

    dataset_name: str
    dataset_version: str
    model_name: str
    calibration_partition_name: str
    class_labels: tuple[object, ...]
    positive_label: object
    method: str
    parameters: Mapping[str, object]
    calibration_observation_count: int
    metadata: Mapping[str, object]

    def __init__(
        self,
        dataset_name: str,
        dataset_version: str,
        model_name: str,
        calibration_partition_name: str,
        class_labels: Sequence[object],
        positive_label: object,
        method: str,
        parameters: Mapping[str, object],
        calibration_observation_count: int,
        metadata: Mapping[str, object] = MappingProxyType({}),
    ) -> None:
        for name, value in (
            ("dataset_name", dataset_name),
            ("dataset_version", dataset_version),
            ("model_name", model_name),
            ("calibration_partition_name", calibration_partition_name),
        ):
            _validate_name(name, value)
        if calibration_partition_name != "validation":
            raise ValueError("calibration_partition_name must be validation")
        labels = _normalized_binary_labels(class_labels)
        if not _contains(labels, positive_label):
            raise ValueError("positive_label must belong to class_labels")
        _validate_method(method)
        normalized_parameters = _normalize_parameters(method, parameters)
        if isinstance(calibration_observation_count, bool) or not isinstance(
            calibration_observation_count, int
        ):
            raise TypeError("calibration_observation_count must be an integer")
        if calibration_observation_count <= 0:
            raise ValueError("calibration_observation_count must be positive")
        if not isinstance(metadata, Mapping):
            raise TypeError("metadata must be a mapping")
        object.__setattr__(self, "dataset_name", deepcopy(dataset_name))
        object.__setattr__(self, "dataset_version", deepcopy(dataset_version))
        object.__setattr__(self, "model_name", deepcopy(model_name))
        object.__setattr__(self, "calibration_partition_name", "validation")
        object.__setattr__(self, "class_labels", labels)
        object.__setattr__(self, "positive_label", _freeze(positive_label))
        object.__setattr__(self, "method", method)
        object.__setattr__(self, "parameters", _freeze_mapping(normalized_parameters))
        object.__setattr__(
            self, "calibration_observation_count", calibration_observation_count
        )
        object.__setattr__(self, "metadata", _freeze_mapping(metadata))

    def to_dict(self) -> dict[str, object]:
        """Return a deterministic, detached standard-container representation."""
        return {
            "dataset_name": deepcopy(self.dataset_name),
            "dataset_version": deepcopy(self.dataset_version),
            "model_name": deepcopy(self.model_name),
            "calibration_partition_name": self.calibration_partition_name,
            "class_labels": _thaw(self.class_labels),
            "positive_label": _thaw(self.positive_label),
            "method": self.method,
            "parameters": _thaw(self.parameters),
            "calibration_observation_count": self.calibration_observation_count,
            "metadata": _thaw(self.metadata),
        }


@dataclass(frozen=True, slots=True, init=False)
class CalibratedPredictionResult:
    """Immutable calibrated predictions for one partition."""

    dataset_name: str
    dataset_version: str
    partition_name: str
    model_name: str
    identifiers: tuple[object, ...]
    class_labels: tuple[object, ...]
    predictions: tuple[object, ...]
    probabilities: tuple[tuple[float, ...], ...]
    observation_count: int
    calibration_method: str
    calibration_partition_name: str
    positive_label: object
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
        calibration_method: str,
        calibration_partition_name: str,
        positive_label: object,
        metadata: Mapping[str, object] = MappingProxyType({}),
    ) -> None:
        for name, value in (
            ("dataset_name", dataset_name),
            ("dataset_version", dataset_version),
            ("partition_name", partition_name),
            ("model_name", model_name),
            ("calibration_partition_name", calibration_partition_name),
        ):
            _validate_name(name, value)
        if partition_name not in _PARTITIONS:
            raise ValueError("partition_name must be validation or test")
        if calibration_partition_name != "validation":
            raise ValueError("calibration_partition_name must be validation")
        _validate_method(calibration_method)
        labels = _normalized_binary_labels(class_labels)
        if not _contains(labels, positive_label):
            raise ValueError("positive_label must belong to class_labels")
        if any(
            isinstance(value, (str, bytes))
            for value in (identifiers, predictions, probabilities)
        ):
            raise TypeError("prediction values must be sequences")
        try:
            normalized_identifiers = tuple(identifiers)
            normalized_predictions = tuple(predictions)
            normalized_probabilities = tuple(
                tuple(_finite_float("probability", value) for value in row)
                for row in probabilities
            )
        except TypeError as error:
            raise TypeError("prediction values must be sequences") from error
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
        if _has_duplicates(normalized_identifiers):
            raise ValueError("identifiers must be unique")
        if any(
            not _contains(labels, prediction) for prediction in normalized_predictions
        ):
            raise ValueError("predictions must belong to class_labels")
        for prediction, row in zip(
            normalized_predictions, normalized_probabilities, strict=True
        ):
            if len(row) != 2:
                raise ValueError("every probability row must contain two entries")
            if any(not 0.0 <= value <= 1.0 for value in row):
                raise ValueError("probabilities must be finite and in [0, 1]")
            if not math.isclose(
                math.fsum(row), 1.0, rel_tol=0.0, abs_tol=_PROBABILITY_TOLERANCE
            ):
                raise ValueError("each probability row must sum to one")
            expected = labels[0] if row[0] >= row[1] else labels[1]
            if prediction != expected:
                raise ValueError("predictions must correspond to calibrated argmax")
        if not isinstance(metadata, Mapping):
            raise TypeError("metadata must be a mapping")
        object.__setattr__(self, "dataset_name", deepcopy(dataset_name))
        object.__setattr__(self, "dataset_version", deepcopy(dataset_version))
        object.__setattr__(self, "partition_name", partition_name)
        object.__setattr__(self, "model_name", deepcopy(model_name))
        object.__setattr__(self, "identifiers", tuple(_freeze(normalized_identifiers)))
        object.__setattr__(self, "class_labels", labels)
        object.__setattr__(self, "predictions", tuple(_freeze(normalized_predictions)))
        object.__setattr__(self, "probabilities", normalized_probabilities)
        object.__setattr__(self, "observation_count", observation_count)
        object.__setattr__(self, "calibration_method", calibration_method)
        object.__setattr__(self, "calibration_partition_name", "validation")
        object.__setattr__(self, "positive_label", _freeze(positive_label))
        object.__setattr__(self, "metadata", _freeze_mapping(metadata))

    def to_dict(self) -> dict[str, object]:
        """Return a deterministic, detached standard-container representation."""
        return {
            "dataset_name": deepcopy(self.dataset_name),
            "dataset_version": deepcopy(self.dataset_version),
            "partition_name": self.partition_name,
            "model_name": deepcopy(self.model_name),
            "identifiers": _thaw(self.identifiers),
            "class_labels": _thaw(self.class_labels),
            "predictions": _thaw(self.predictions),
            "probabilities": _thaw(self.probabilities),
            "observation_count": self.observation_count,
            "calibration_method": self.calibration_method,
            "calibration_partition_name": self.calibration_partition_name,
            "positive_label": _thaw(self.positive_label),
            "metadata": _thaw(self.metadata),
        }


class ModelProbabilityCalibrator:
    """Fit and apply deterministic binary probability calibration."""

    calibrator_name = "model-probability-calibrator"

    def __init__(self, configuration: ProbabilityCalibrationConfiguration) -> None:
        if not isinstance(configuration, ProbabilityCalibrationConfiguration):
            raise TypeError(
                "configuration must be a ProbabilityCalibrationConfiguration"
            )
        self._configuration = configuration

    @property
    def configuration(self) -> ProbabilityCalibrationConfiguration:
        return self._configuration

    def fit(
        self,
        prediction_result: ModelPredictionResult,
        targets: Sequence[object],
    ) -> PreparedProbabilityCalibrator:
        """Fit exclusively on a validation prediction partition."""
        if not isinstance(prediction_result, ModelPredictionResult):
            raise TypeError("prediction_result must be a ModelPredictionResult")
        if prediction_result.partition_name != "validation":
            raise ValueError("calibration fitting requires the validation partition")
        labels = _normalized_binary_labels(prediction_result.class_labels)
        positive_index = _index(labels, self.configuration.positive_label)
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
        binary_targets = np.asarray(
            [
                int(target == self.configuration.positive_label)
                for target in normalized_targets
            ],
            dtype=int,
        )
        if np.unique(binary_targets).size != 2:
            raise ValueError("calibration targets must contain both classes")
        positive_probabilities = np.asarray(
            [row[positive_index] for row in prediction_result.probabilities],
            dtype=float,
        )
        if self.configuration.method == "platt":
            estimator = LogisticRegression(random_state=0, solver="liblinear")
            estimator.fit(positive_probabilities.reshape(-1, 1), binary_targets)
            parameters: Mapping[str, object] = {
                "coefficient": float(estimator.coef_[0, 0]),
                "intercept": float(estimator.intercept_[0]),
            }
        else:
            estimator = IsotonicRegression(out_of_bounds="clip")
            estimator.fit(positive_probabilities, binary_targets)
            parameters = {
                "x_thresholds": tuple(
                    float(value) for value in estimator.X_thresholds_
                ),
                "y_thresholds": tuple(
                    float(value) for value in estimator.y_thresholds_
                ),
            }
        return PreparedProbabilityCalibrator(
            dataset_name=prediction_result.dataset_name,
            dataset_version=prediction_result.dataset_version,
            model_name=prediction_result.model_name,
            calibration_partition_name="validation",
            class_labels=labels,
            positive_label=self.configuration.positive_label,
            method=self.configuration.method,
            parameters=parameters,
            calibration_observation_count=prediction_result.observation_count,
            metadata=prediction_result.metadata,
        )

    def calibrate(
        self,
        calibrator: PreparedProbabilityCalibrator,
        prediction_result: ModelPredictionResult,
    ) -> CalibratedPredictionResult:
        """Apply stored calibration parameters without refitting."""
        if not isinstance(calibrator, PreparedProbabilityCalibrator):
            raise TypeError("calibrator must be a PreparedProbabilityCalibrator")
        if not isinstance(prediction_result, ModelPredictionResult):
            raise TypeError("prediction_result must be a ModelPredictionResult")
        if prediction_result.partition_name not in _PARTITIONS:
            raise ValueError("prediction partition must be validation or test")
        for name in ("dataset_name", "dataset_version", "model_name"):
            if getattr(prediction_result, name) != getattr(calibrator, name):
                raise ValueError(f"{name} does not match the calibrator")
        if prediction_result.class_labels != calibrator.class_labels:
            raise ValueError("class_labels do not match the calibrator")
        positive_index = _index(calibrator.class_labels, calibrator.positive_label)
        source = np.asarray(
            [row[positive_index] for row in prediction_result.probabilities],
            dtype=float,
        )
        if calibrator.method == "platt":
            coefficient = float(calibrator.parameters["coefficient"])
            intercept = float(calibrator.parameters["intercept"])
            scores = coefficient * source + intercept
            positive = np.empty_like(scores)
            nonnegative = scores >= 0
            positive[nonnegative] = 1.0 / (1.0 + np.exp(-scores[nonnegative]))
            exponentials = np.exp(scores[~nonnegative])
            positive[~nonnegative] = exponentials / (1.0 + exponentials)
        else:
            positive = np.interp(
                source,
                np.asarray(calibrator.parameters["x_thresholds"], dtype=float),
                np.asarray(calibrator.parameters["y_thresholds"], dtype=float),
            )
        positive = np.clip(positive, 0.0, 1.0)
        rows: list[tuple[float, float]] = []
        predictions: list[object] = []
        for value in positive:
            positive_value = float(value)
            negative_value = 1.0 - positive_value
            row = (
                (positive_value, negative_value)
                if positive_index == 0
                else (negative_value, positive_value)
            )
            rows.append(row)
            predictions.append(
                calibrator.class_labels[0]
                if row[0] >= row[1]
                else calibrator.class_labels[1]
            )
        return CalibratedPredictionResult(
            dataset_name=prediction_result.dataset_name,
            dataset_version=prediction_result.dataset_version,
            partition_name=prediction_result.partition_name,
            model_name=prediction_result.model_name,
            identifiers=prediction_result.identifiers,
            class_labels=prediction_result.class_labels,
            predictions=predictions,
            probabilities=rows,
            observation_count=prediction_result.observation_count,
            calibration_method=calibrator.method,
            calibration_partition_name=calibrator.calibration_partition_name,
            positive_label=calibrator.positive_label,
            metadata=prediction_result.metadata,
        )
