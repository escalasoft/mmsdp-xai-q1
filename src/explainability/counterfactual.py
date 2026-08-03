"""Framework-neutral counterfactual contracts and model-specific generation.

The result contract can represent counterfactuals from different frameworks.
The included explainer implements only the deterministic linear-boundary method
for binary logistic regression; new model families require model-specific
counterfactual adapters or strategies.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from numbers import Real
from types import MappingProxyType

from models.logistic_regression_adapter import PreparedLogisticRegressionModel
from models.random_forest_adapter import PreparedRandomForestModel

__all__ = [
    "CounterfactualChange",
    "CounterfactualExplanationResult",
    "CounterfactualExplainer",
]

_MODEL_NAME = "logistic-regression"
_GENERATION_METHOD = "minimal-single-feature-linear-boundary"
_NEGATIVE_MARGIN = -1e-12
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


def _non_empty_string(name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return deepcopy(value)


def _number(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{name} must be numeric and must not be bool")
    normalized = float(value)
    if not math.isfinite(normalized):
        raise ValueError(f"{name} must be finite")
    return normalized


def _sequence(name: str, value: object) -> tuple[object, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise TypeError(f"{name} must be a sequence")
    return tuple(value)


def _has_duplicates(values: Sequence[object]) -> bool:
    return any(
        value == previous
        for index, value in enumerate(values)
        for previous in values[:index]
    )


def _close(left: float, right: float) -> bool:
    return math.isclose(left, right, rel_tol=0.0, abs_tol=_TOLERANCE)


@dataclass(frozen=True, slots=True, init=False)
class CounterfactualChange:
    """Immutable change to one feature in a counterfactual observation."""

    feature_name: str
    original_value: float
    counterfactual_value: float
    delta: float
    absolute_delta: float

    def __init__(
        self,
        feature_name: str,
        original_value: float,
        counterfactual_value: float,
        delta: float,
        absolute_delta: float,
    ) -> None:
        name = _non_empty_string("feature_name", feature_name)
        original = _number("original_value", original_value)
        counterfactual = _number("counterfactual_value", counterfactual_value)
        normalized_delta = _number("delta", delta)
        absolute = _number("absolute_delta", absolute_delta)
        if normalized_delta == 0.0:
            raise ValueError("delta must not be zero")
        if not _close(counterfactual - original, normalized_delta):
            raise ValueError("delta must equal counterfactual_value - original_value")
        if absolute <= 0.0 or not _close(absolute, abs(normalized_delta)):
            raise ValueError("absolute_delta must equal abs(delta) and be positive")

        object.__setattr__(self, "feature_name", name)
        object.__setattr__(self, "original_value", original)
        object.__setattr__(self, "counterfactual_value", counterfactual)
        object.__setattr__(self, "delta", normalized_delta)
        object.__setattr__(self, "absolute_delta", absolute)

    def to_dict(self) -> dict[str, object]:
        return {
            "feature_name": deepcopy(self.feature_name),
            "original_value": self.original_value,
            "counterfactual_value": self.counterfactual_value,
            "delta": self.delta,
            "absolute_delta": self.absolute_delta,
        }


@dataclass(frozen=True, slots=True, init=False)
class CounterfactualExplanationResult:
    """Immutable, framework-neutral binary counterfactual explanation."""

    dataset_name: str
    dataset_version: str
    model_name: str
    target_name: str
    class_labels: tuple[object, ...]
    observation_identifier: object
    feature_names: tuple[str, ...]
    original_feature_values: tuple[float, ...]
    counterfactual_feature_values: tuple[float, ...]
    original_prediction: object
    counterfactual_prediction: object
    original_score: float
    counterfactual_score: float
    changes: tuple[CounterfactualChange, ...]
    generation_method: str
    metadata: Mapping[str, object]

    def __init__(
        self,
        dataset_name: str,
        dataset_version: str,
        model_name: str,
        target_name: str,
        class_labels: Sequence[object],
        observation_identifier: object,
        feature_names: Sequence[str],
        original_feature_values: Sequence[float],
        counterfactual_feature_values: Sequence[float],
        original_prediction: object,
        counterfactual_prediction: object,
        original_score: float,
        counterfactual_score: float,
        changes: Sequence[CounterfactualChange],
        generation_method: str,
        metadata: Mapping[str, object] = MappingProxyType({}),
    ) -> None:
        strings = {
            "dataset_name": _non_empty_string("dataset_name", dataset_name),
            "dataset_version": _non_empty_string("dataset_version", dataset_version),
            "model_name": _non_empty_string("model_name", model_name),
            "target_name": _non_empty_string("target_name", target_name),
            "generation_method": _non_empty_string(
                "generation_method", generation_method
            ),
        }
        if observation_identifier is None:
            raise ValueError("observation_identifier must not be None")
        labels = tuple(_freeze(_sequence("class_labels", class_labels)))
        features = _sequence("feature_names", feature_names)
        originals = tuple(
            _number("original feature value", item)
            for item in _sequence("original_feature_values", original_feature_values)
        )
        counterfactuals = tuple(
            _number("counterfactual feature value", item)
            for item in _sequence(
                "counterfactual_feature_values", counterfactual_feature_values
            )
        )
        items = _sequence("changes", changes)
        if len(labels) != 2 or _has_duplicates(labels):
            raise ValueError("class_labels must contain exactly two distinct labels")
        if not features:
            raise ValueError("feature_names must not be empty")
        if any(not isinstance(item, str) or not item.strip() for item in features):
            raise ValueError("feature_names must contain non-empty strings")
        if _has_duplicates(features):
            raise ValueError("feature_names must be unique")
        if len(originals) != len(features) or len(counterfactuals) != len(features):
            raise ValueError("feature vectors must match feature_names")
        if original_prediction not in labels or counterfactual_prediction not in labels:
            raise ValueError("predictions must be members of class_labels")
        if original_prediction == counterfactual_prediction:
            raise ValueError(
                "counterfactual_prediction must differ from original_prediction"
            )
        original_linear_score = _number("original_score", original_score)
        counterfactual_linear_score = _number(
            "counterfactual_score", counterfactual_score
        )
        if len(items) != 1 or not isinstance(items[0], CounterfactualChange):
            raise ValueError("changes must contain exactly one CounterfactualChange")
        change = items[0]
        if change.feature_name not in features:
            raise ValueError("change feature_name must occur in feature_names")
        position = features.index(change.feature_name)
        differing = tuple(
            index
            for index, (left, right) in enumerate(
                zip(originals, counterfactuals, strict=True)
            )
            if left != right
        )
        if differing != (position,):
            raise ValueError("feature vectors must differ only at the changed feature")
        if not _close(change.original_value, originals[position]) or not _close(
            change.counterfactual_value, counterfactuals[position]
        ):
            raise ValueError("change values must match the feature vectors")

        for name, value in strings.items():
            object.__setattr__(self, name, value)
        object.__setattr__(self, "class_labels", labels)
        object.__setattr__(
            self, "observation_identifier", _freeze(observation_identifier)
        )
        object.__setattr__(self, "feature_names", tuple(deepcopy(features)))
        object.__setattr__(self, "original_feature_values", originals)
        object.__setattr__(self, "counterfactual_feature_values", counterfactuals)
        object.__setattr__(self, "original_prediction", _freeze(original_prediction))
        object.__setattr__(
            self, "counterfactual_prediction", _freeze(counterfactual_prediction)
        )
        object.__setattr__(self, "original_score", original_linear_score)
        object.__setattr__(self, "counterfactual_score", counterfactual_linear_score)
        object.__setattr__(self, "changes", tuple(items))
        object.__setattr__(self, "metadata", _freeze_mapping(metadata))

    @property
    def changed_feature_count(self) -> int:
        return len(self.changes)

    def to_dict(self) -> dict[str, object]:
        return {
            "dataset_name": deepcopy(self.dataset_name),
            "dataset_version": deepcopy(self.dataset_version),
            "model_name": self.model_name,
            "target_name": deepcopy(self.target_name),
            "class_labels": _thaw(self.class_labels),
            "observation_identifier": _thaw(self.observation_identifier),
            "feature_names": list(deepcopy(self.feature_names)),
            "original_feature_values": list(self.original_feature_values),
            "counterfactual_feature_values": list(self.counterfactual_feature_values),
            "original_prediction": _thaw(self.original_prediction),
            "counterfactual_prediction": _thaw(self.counterfactual_prediction),
            "original_score": self.original_score,
            "counterfactual_score": self.counterfactual_score,
            "changes": [item.to_dict() for item in self.changes],
            "generation_method": self.generation_method,
            "metadata": _thaw(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class CounterfactualExplainer:
    """Generate binary logistic-regression linear-boundary counterfactuals.

    The search is exhaustive over all non-zero coefficients. Candidates are
    ordered by absolute feature change, with model feature order as the stable
    tie-breaker. Other model families require their own model-aware adapter or
    strategy. No actionability or causal claim is implied.
    """

    explainer_name: str = "counterfactual"

    def explain(
        self,
        model: PreparedLogisticRegressionModel | PreparedRandomForestModel,
        observation_identifier: object,
        feature_values: Sequence[float],
        /,
    ) -> CounterfactualExplanationResult:
        if isinstance(model, PreparedRandomForestModel):
            raise NotImplementedError(
                "The generic counterfactual result contract supports future model "
                "families, but no faithful PreparedRandomForestModel counterfactual "
                "generator is implemented. Random Forest generation requires "
                "additional model-aware tree information or an appropriate tree "
                "counterfactual method; that information is intentionally unavailable "
                "in the current reproducible snapshot."
            )
        if isinstance(model, PreparedLogisticRegressionModel):
            return self._explain_logistic_regression(
                model, observation_identifier, feature_values
            )
        raise TypeError(
            "model must be PreparedLogisticRegressionModel or PreparedRandomForestModel"
        )

    def _explain_logistic_regression(
        self,
        model: PreparedLogisticRegressionModel,
        observation_identifier: object,
        feature_values: Sequence[float],
    ) -> CounterfactualExplanationResult:
        """Apply the deterministic binary linear-boundary strategy."""
        if observation_identifier is None:
            raise ValueError("observation_identifier must not be None")
        raw_values = _sequence("feature_values", feature_values)
        values = tuple(_number("feature value", item) for item in raw_values)
        feature_names = tuple(model.feature_names)
        if not feature_names or len(values) != len(feature_names):
            raise ValueError("feature_values must match model feature_names")
        if _has_duplicates(feature_names) or any(
            not isinstance(item, str) or not item.strip() for item in feature_names
        ):
            raise ValueError("model feature_names must be non-empty and unique")
        if len(model.class_labels) != 2 or len(model.coefficients) != 1:
            raise ValueError("counterfactual generation requires a binary model")
        coefficients = tuple(
            _number("coefficient", item) for item in model.coefficients[0]
        )
        if len(coefficients) != len(feature_names):
            raise ValueError("model coefficient width must match feature_names")
        if len(model.intercepts) != 1:
            raise ValueError("binary model must contain exactly one intercept")
        intercept = _number("intercept", model.intercepts[0])
        score = intercept + math.fsum(
            coefficient * value
            for coefficient, value in zip(coefficients, values, strict=True)
        )
        if not math.isfinite(score):
            raise ValueError("linear score must be finite")
        target_score = _NEGATIVE_MARGIN if score >= 0.0 else 0.0
        candidates = tuple(
            (
                abs((target_score - score) / coefficient),
                index,
                (target_score - score) / coefficient,
            )
            for index, coefficient in enumerate(coefficients)
            if coefficient != 0.0
        )
        if not candidates:
            raise ValueError(
                "counterfactual generation requires at least one non-zero coefficient"
            )
        _, position, delta = min(candidates, key=lambda item: (item[0], item[1]))
        counterfactual_values = list(values)
        counterfactual_values[position] += delta
        counterfactual_score = intercept + math.fsum(
            coefficient * value
            for coefficient, value in zip(
                coefficients, counterfactual_values, strict=True
            )
        )
        # Floating-point cancellation can land on the wrong side of the boundary.
        direction = (
            -math.inf if (score >= 0.0) == (coefficients[position] > 0.0) else math.inf
        )
        while (counterfactual_score >= 0.0) == (score >= 0.0):
            counterfactual_values[position] = math.nextafter(
                counterfactual_values[position], direction
            )
            counterfactual_score = intercept + math.fsum(
                coefficient * value
                for coefficient, value in zip(
                    coefficients, counterfactual_values, strict=True
                )
            )
        final_delta = counterfactual_values[position] - values[position]
        labels = tuple(model.class_labels)
        original_prediction = labels[1] if score >= 0.0 else labels[0]
        counterfactual_prediction = (
            labels[1] if counterfactual_score >= 0.0 else labels[0]
        )
        change = CounterfactualChange(
            feature_names[position],
            values[position],
            counterfactual_values[position],
            final_delta,
            abs(final_delta),
        )
        return CounterfactualExplanationResult(
            model.dataset_name,
            model.dataset_version,
            _MODEL_NAME,
            model.target_name,
            labels,
            observation_identifier,
            feature_names,
            values,
            counterfactual_values,
            original_prediction,
            counterfactual_prediction,
            score,
            counterfactual_score,
            (change,),
            _GENERATION_METHOD,
            model.metadata,
        )
