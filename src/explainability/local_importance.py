"""Deterministic, framework-neutral local feature importance."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from functools import cmp_to_key
from numbers import Integral, Real
from types import MappingProxyType

from models.logistic_regression_adapter import PreparedLogisticRegressionModel
from models.random_forest_adapter import PreparedRandomForestModel

__all__ = [
    "LocalFeatureAttribution",
    "LocalFeatureImportanceResult",
    "LocalFeatureImportanceExplainer",
]

_DIRECTIONS = frozenset({"positive", "negative", "neutral"})
_ATTRIBUTION_METHOD = "linear-logit-contribution"
_MODEL_NAME = "logistic-regression"
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
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _close(left: float, right: float) -> bool:
    return math.isclose(left, right, rel_tol=0.0, abs_tol=_TOLERANCE)


def _has_duplicates(values: Sequence[object]) -> bool:
    return any(
        value == previous
        for index, value in enumerate(values)
        for previous in values[:index]
    )


def _compare_importance(
    left_value: float, left_position: int, right_value: float, right_position: int
) -> int:
    if _close(left_value, right_value):
        return left_position - right_position
    return -1 if left_value > right_value else 1


@dataclass(frozen=True, slots=True, init=False)
class LocalFeatureAttribution:
    """Immutable, model-agnostic attribution for one observation feature."""

    feature_name: str
    feature_value: float
    rank: int
    raw_attribution: float
    absolute_attribution: float
    normalized_importance: float
    direction: str

    def __init__(
        self,
        feature_name: str,
        feature_value: float,
        rank: int,
        raw_attribution: float,
        absolute_attribution: float,
        normalized_importance: float,
        direction: str,
    ) -> None:
        name = _non_empty_string("feature_name", feature_name)
        value = _number("feature_value", feature_value)
        if isinstance(rank, bool) or not isinstance(rank, Integral):
            raise TypeError("rank must be an integer and must not be bool")
        normalized_rank = int(rank)
        if normalized_rank < 1:
            raise ValueError("rank must be at least 1")
        raw = _number("raw_attribution", raw_attribution)
        absolute = _number("absolute_attribution", absolute_attribution)
        normalized = _number("normalized_importance", normalized_importance)
        if absolute < 0.0 or not _close(absolute, abs(raw)):
            raise ValueError("absolute_attribution must equal abs(raw_attribution)")
        if not 0.0 <= normalized <= 1.0:
            raise ValueError("normalized_importance must be in [0, 1]")
        if direction not in _DIRECTIONS:
            raise ValueError(f"direction must be one of {sorted(_DIRECTIONS)}")
        expected_direction = (
            "positive" if raw > 0.0 else "negative" if raw < 0.0 else "neutral"
        )
        if direction != expected_direction:
            raise ValueError("direction must match raw_attribution")

        object.__setattr__(self, "feature_name", name)
        object.__setattr__(self, "feature_value", value)
        object.__setattr__(self, "rank", normalized_rank)
        object.__setattr__(self, "raw_attribution", raw)
        object.__setattr__(self, "absolute_attribution", absolute)
        object.__setattr__(self, "normalized_importance", normalized)
        object.__setattr__(self, "direction", direction)

    def to_dict(self) -> dict[str, object]:
        """Return a detached standard-container representation."""
        return {
            "feature_name": deepcopy(self.feature_name),
            "feature_value": self.feature_value,
            "rank": self.rank,
            "raw_attribution": self.raw_attribution,
            "absolute_attribution": self.absolute_attribution,
            "normalized_importance": self.normalized_importance,
            "direction": self.direction,
        }


@dataclass(frozen=True, slots=True, init=False)
class LocalFeatureImportanceResult:
    """Immutable local explanation compatible with future model-aware adapters."""

    dataset_name: str
    dataset_version: str
    model_name: str
    target_name: str
    class_labels: tuple[object, ...]
    observation_identifier: object
    feature_names: tuple[str, ...]
    attributions: tuple[LocalFeatureAttribution, ...]
    attribution_method: str
    normalization_method: str
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
        attributions: Sequence[LocalFeatureAttribution],
        attribution_method: str,
        normalization_method: str,
        metadata: Mapping[str, object] = MappingProxyType({}),
    ) -> None:
        for name, value in (
            ("dataset_name", dataset_name),
            ("dataset_version", dataset_version),
            ("model_name", model_name),
            ("target_name", target_name),
            ("attribution_method", attribution_method),
            ("normalization_method", normalization_method),
        ):
            _non_empty_string(name, value)
        if model_name != _MODEL_NAME:
            raise ValueError("model_name must be logistic-regression")
        if attribution_method != _ATTRIBUTION_METHOD:
            raise ValueError("attribution_method must be linear-logit-contribution")
        if normalization_method != "absolute-sum":
            raise ValueError("normalization_method must be absolute-sum")
        if observation_identifier is None:
            raise ValueError("observation_identifier must not be None")
        if isinstance(class_labels, (str, bytes)):
            raise TypeError("class_labels must be a sequence")
        if isinstance(feature_names, (str, bytes)):
            raise TypeError("feature_names must be a sequence")
        if isinstance(attributions, (str, bytes)):
            raise TypeError("attributions must be a sequence")
        try:
            labels = tuple(_freeze(tuple(class_labels)))
            features = tuple(feature_names)
            items = tuple(attributions)
        except TypeError as error:
            raise TypeError("contract collections must be sequences") from error
        if len(labels) != 2 or _has_duplicates(labels):
            raise ValueError("class_labels must contain exactly two distinct labels")
        if not features:
            raise ValueError("feature_names must not be empty")
        if any(not isinstance(item, str) or not item.strip() for item in features):
            raise ValueError("feature_names must contain non-empty strings")
        if _has_duplicates(features):
            raise ValueError("feature_names must be unique")
        if len(items) != len(features):
            raise ValueError("attributions must match feature_names")
        if any(not isinstance(item, LocalFeatureAttribution) for item in items):
            raise TypeError("attributions must contain LocalFeatureAttribution values")
        names = tuple(item.feature_name for item in items)
        if _has_duplicates(names) or any(name not in features for name in names):
            raise ValueError(
                "attribution feature names must correspond to feature_names"
            )
        if tuple(item.rank for item in items) != tuple(range(1, len(items) + 1)):
            raise ValueError("attribution ranks must be contiguous and ordered from 1")
        positions = {name: index for index, name in enumerate(features)}
        expected_order = tuple(
            sorted(
                items,
                key=cmp_to_key(
                    lambda left, right: _compare_importance(
                        left.absolute_attribution,
                        positions[left.feature_name],
                        right.absolute_attribution,
                        positions[right.feature_name],
                    )
                ),
            )
        )
        if items != expected_order:
            raise ValueError("attributions are not in deterministic importance order")
        total = math.fsum(item.absolute_attribution for item in items)
        if total > 0.0:
            if any(
                not _close(
                    item.normalized_importance, item.absolute_attribution / total
                )
                for item in items
            ):
                raise ValueError(
                    "normalized_importance must use absolute-sum normalization"
                )
        elif any(item.normalized_importance != 0.0 for item in items):
            raise ValueError("zero attributions require zero normalized_importance")
        elif names != features:
            raise ValueError("all-zero attributions must preserve feature ordering")

        object.__setattr__(self, "dataset_name", deepcopy(dataset_name))
        object.__setattr__(self, "dataset_version", deepcopy(dataset_version))
        object.__setattr__(self, "model_name", model_name)
        object.__setattr__(self, "target_name", deepcopy(target_name))
        object.__setattr__(self, "class_labels", labels)
        object.__setattr__(
            self, "observation_identifier", _freeze(observation_identifier)
        )
        object.__setattr__(self, "feature_names", tuple(deepcopy(features)))
        object.__setattr__(self, "attributions", items)
        object.__setattr__(self, "attribution_method", attribution_method)
        object.__setattr__(self, "normalization_method", normalization_method)
        object.__setattr__(self, "metadata", _freeze_mapping(metadata))

    @property
    def feature_count(self) -> int:
        return len(self.feature_names)

    def to_dict(self) -> dict[str, object]:
        """Return a deterministic, detached standard-container representation."""
        return {
            "dataset_name": deepcopy(self.dataset_name),
            "dataset_version": deepcopy(self.dataset_version),
            "model_name": self.model_name,
            "target_name": deepcopy(self.target_name),
            "class_labels": _thaw(self.class_labels),
            "observation_identifier": _thaw(self.observation_identifier),
            "feature_names": list(deepcopy(self.feature_names)),
            "attributions": [item.to_dict() for item in self.attributions],
            "attribution_method": self.attribution_method,
            "normalization_method": self.normalization_method,
            "metadata": _thaw(self.metadata),
        }


class LocalFeatureImportanceExplainer:
    """Compute reproducible logistic-regression linear-score contributions.

    Each raw attribution is ``coefficient * feature_value`` and is an additive
    contribution to the binary model's linear score (logit). It is not a direct
    contribution to predicted probability and must not be interpreted as a
    causal effect.
    """

    explainer_name = "local-feature-importance"

    def explain(
        self,
        model: PreparedLogisticRegressionModel | PreparedRandomForestModel,
        observation_identifier: object,
        feature_values: Sequence[float],
        /,
    ) -> LocalFeatureImportanceResult:
        """Explain one vector as additive linear-logit feature contributions."""
        if isinstance(model, PreparedRandomForestModel):
            raise NotImplementedError(
                "PreparedRandomForestModel local attribution is not implemented: "
                "the stored snapshot contains only global feature importances and "
                "insufficient tree-path information for faithful local "
                "attributions. Random Forest local explanations require a future "
                "TreeSHAP or equivalent model-aware adapter."
            )
        if not isinstance(model, PreparedLogisticRegressionModel):
            raise TypeError(
                "model must be PreparedLogisticRegressionModel or "
                "PreparedRandomForestModel"
            )
        if observation_identifier is None:
            raise ValueError("observation_identifier must not be None")
        if isinstance(feature_values, (str, bytes)):
            raise TypeError("feature_values must be a sequence")
        try:
            values = tuple(_number("feature value", value) for value in feature_values)
        except TypeError as error:
            raise TypeError("feature_values must be a numeric sequence") from error
        feature_names = tuple(model.feature_names)
        if not feature_names or len(values) != len(feature_names):
            raise ValueError("feature_values must match model feature_names")

        if len(model.class_labels) != 2 or len(model.coefficients) != 1:
            raise ValueError("local logistic explanation requires a binary model")
        coefficients = tuple(
            _number("coefficient", value) for value in model.coefficients[0]
        )
        if len(coefficients) != len(feature_names):
            raise ValueError("model coefficient width must match feature_names")
        raw_values = tuple(
            coefficient * value
            for coefficient, value in zip(coefficients, values, strict=True)
        )

        absolute_values = tuple(abs(value) for value in raw_values)
        total = math.fsum(absolute_values)
        normalized = (
            tuple(value / total for value in absolute_values)
            if total > 0.0
            else (0.0,) * len(values)
        )
        ranked = sorted(
            range(len(values)),
            key=cmp_to_key(
                lambda left, right: _compare_importance(
                    absolute_values[left], left, absolute_values[right], right
                )
            ),
        )
        attributions = tuple(
            LocalFeatureAttribution(
                feature_names[index],
                values[index],
                rank,
                raw_values[index],
                absolute_values[index],
                normalized[index],
                "positive"
                if raw_values[index] > 0.0
                else "negative"
                if raw_values[index] < 0.0
                else "neutral",
            )
            for rank, index in enumerate(ranked, start=1)
        )
        return LocalFeatureImportanceResult(
            dataset_name=model.dataset_name,
            dataset_version=model.dataset_version,
            model_name=_MODEL_NAME,
            target_name=model.target_name,
            class_labels=model.class_labels,
            observation_identifier=observation_identifier,
            feature_names=feature_names,
            attributions=attributions,
            attribution_method=_ATTRIBUTION_METHOD,
            normalization_method="absolute-sum",
            metadata=model.metadata,
        )
