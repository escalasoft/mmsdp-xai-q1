"""Deterministic, framework-neutral global feature importance."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from numbers import Integral, Real
from types import MappingProxyType

from models.logistic_regression_adapter import PreparedLogisticRegressionModel
from models.random_forest_adapter import PreparedRandomForestModel

__all__ = [
    "GlobalFeatureAttribution",
    "GlobalFeatureImportanceResult",
    "GlobalFeatureImportanceExplainer",
]

_DIRECTIONS = frozenset({"positive", "negative", "neutral", "unsigned"})
_MODEL_NAMES = frozenset({"logistic-regression", "random-forest"})
_TOLERANCE = 1e-12


def _freeze(value: object) -> object:
    """Return a detached, recursively immutable value."""
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
    """Return a detached representation containing standard containers."""
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


def _close(left: float, right: float) -> bool:
    return math.isclose(left, right, rel_tol=0.0, abs_tol=_TOLERANCE)


def _has_duplicates(values: Sequence[object]) -> bool:
    return any(
        value == previous
        for index, value in enumerate(values)
        for previous in values[:index]
    )


@dataclass(frozen=True, slots=True, init=False)
class GlobalFeatureAttribution:
    """Immutable global attribution for one model feature."""

    feature_name: str
    rank: int
    raw_importance: float
    absolute_importance: float
    normalized_importance: float
    direction: str

    def __init__(
        self,
        feature_name: str,
        rank: int,
        raw_importance: float,
        absolute_importance: float,
        normalized_importance: float,
        direction: str,
    ) -> None:
        name = _non_empty_string("feature_name", feature_name)
        if isinstance(rank, bool) or not isinstance(rank, Integral):
            raise TypeError("rank must be an integer and must not be bool")
        normalized_rank = int(rank)
        if normalized_rank < 1:
            raise ValueError("rank must be at least 1")
        raw = _number("raw_importance", raw_importance)
        absolute = _number("absolute_importance", absolute_importance)
        normalized = _number("normalized_importance", normalized_importance)
        if absolute < 0.0:
            raise ValueError("absolute_importance must be non-negative")
        if not 0.0 <= normalized <= 1.0:
            raise ValueError("normalized_importance must be in [0, 1]")
        if not _close(absolute, abs(raw)):
            raise ValueError("absolute_importance must equal abs(raw_importance)")
        if direction not in _DIRECTIONS:
            raise ValueError(f"direction must be one of {sorted(_DIRECTIONS)}")
        if direction == "unsigned":
            if raw < 0.0:
                raise ValueError("unsigned raw_importance must be non-negative")
        elif raw > 0.0 and direction != "positive":
            raise ValueError("positive raw_importance requires positive direction")
        elif raw < 0.0 and direction != "negative":
            raise ValueError("negative raw_importance requires negative direction")
        elif raw == 0.0 and direction != "neutral":
            raise ValueError("zero signed raw_importance requires neutral direction")

        object.__setattr__(self, "feature_name", name)
        object.__setattr__(self, "rank", normalized_rank)
        object.__setattr__(self, "raw_importance", raw)
        object.__setattr__(self, "absolute_importance", absolute)
        object.__setattr__(self, "normalized_importance", normalized)
        object.__setattr__(self, "direction", direction)

    def to_dict(self) -> dict[str, object]:
        """Return a deterministic, detached standard-container representation."""
        return {
            "feature_name": deepcopy(self.feature_name),
            "rank": self.rank,
            "raw_importance": self.raw_importance,
            "absolute_importance": self.absolute_importance,
            "normalized_importance": self.normalized_importance,
            "direction": self.direction,
        }


@dataclass(frozen=True, slots=True, init=False)
class GlobalFeatureImportanceResult:
    """Immutable, observation-independent global model explanation."""

    dataset_name: str
    dataset_version: str
    model_name: str
    target_name: str
    class_labels: tuple[object, ...]
    feature_names: tuple[str, ...]
    attributions: tuple[GlobalFeatureAttribution, ...]
    normalization_method: str
    metadata: Mapping[str, object]

    def __init__(
        self,
        dataset_name: str,
        dataset_version: str,
        model_name: str,
        target_name: str,
        class_labels: Sequence[object],
        feature_names: Sequence[str],
        attributions: Sequence[GlobalFeatureAttribution],
        normalization_method: str,
        metadata: Mapping[str, object] = MappingProxyType({}),
    ) -> None:
        names_to_set = {
            "dataset_name": _non_empty_string("dataset_name", dataset_name),
            "dataset_version": _non_empty_string("dataset_version", dataset_version),
            "model_name": _non_empty_string("model_name", model_name),
            "target_name": _non_empty_string("target_name", target_name),
            "normalization_method": _non_empty_string(
                "normalization_method", normalization_method
            ),
        }
        if model_name not in _MODEL_NAMES:
            raise ValueError(f"model_name must be one of {sorted(_MODEL_NAMES)}")
        if normalization_method != "absolute-sum":
            raise ValueError("normalization_method must be absolute-sum")
        if isinstance(class_labels, (str, bytes)):
            raise TypeError("class_labels must be a sequence")
        try:
            labels = tuple(_freeze(tuple(class_labels)))
        except TypeError as error:
            raise TypeError("class_labels must be a sequence") from error
        if len(labels) != 2 or _has_duplicates(labels):
            raise ValueError("class_labels must contain exactly two distinct labels")
        if isinstance(feature_names, (str, bytes)):
            raise TypeError("feature_names must be a sequence")
        try:
            features = tuple(feature_names)
        except TypeError as error:
            raise TypeError("feature_names must be a sequence") from error
        if not features:
            raise ValueError("feature_names must not be empty")
        if any(not isinstance(item, str) or not item.strip() for item in features):
            raise ValueError("feature_names must contain non-empty strings")
        if _has_duplicates(features):
            raise ValueError("feature_names must be unique")
        if isinstance(attributions, (str, bytes)):
            raise TypeError("attributions must be a sequence")
        try:
            items = tuple(attributions)
        except TypeError as error:
            raise TypeError("attributions must be a sequence") from error
        if not items:
            raise ValueError("attributions must not be empty")
        if any(not isinstance(item, GlobalFeatureAttribution) for item in items):
            raise TypeError("attributions must contain GlobalFeatureAttribution values")
        if len(items) != len(features):
            raise ValueError("attributions must match feature_names")
        attribution_names = tuple(item.feature_name for item in items)
        if _has_duplicates(attribution_names):
            raise ValueError("attribution feature names must be unique")
        if len(attribution_names) != len(features) or any(
            name not in features for name in attribution_names
        ):
            raise ValueError(
                "attribution feature names must correspond to feature_names"
            )
        if tuple(item.rank for item in items) != tuple(range(1, len(items) + 1)):
            raise ValueError("attribution ranks must be contiguous and ordered from 1")

        positions = {name: index for index, name in enumerate(features)}
        expected_order = tuple(
            sorted(
                items,
                key=lambda item: (
                    -item.normalized_importance,
                    -item.absolute_importance,
                    positions[item.feature_name],
                ),
            )
        )
        if items != expected_order:
            raise ValueError("attributions are not in deterministic importance order")
        total = math.fsum(item.absolute_importance for item in items)
        if total > 0.0:
            if not _close(math.fsum(item.normalized_importance for item in items), 1.0):
                raise ValueError("normalized_importance values must sum to 1")
            if any(
                not _close(item.normalized_importance, item.absolute_importance / total)
                for item in items
            ):
                raise ValueError(
                    "normalized_importance must use absolute-sum normalization"
                )
        elif any(item.normalized_importance != 0.0 for item in items):
            raise ValueError("zero importances require zero normalized_importance")
        elif attribution_names != features:
            raise ValueError("all-zero importances must preserve feature ordering")

        if model_name == "logistic-regression" and any(
            item.direction not in {"positive", "negative", "neutral"} for item in items
        ):
            raise ValueError("logistic-regression attributions must be signed")
        if model_name == "random-forest" and any(
            item.direction != "unsigned" for item in items
        ):
            raise ValueError("random-forest attributions must be unsigned")

        for name, value in names_to_set.items():
            object.__setattr__(self, name, value)
        object.__setattr__(self, "class_labels", labels)
        object.__setattr__(self, "feature_names", tuple(deepcopy(features)))
        object.__setattr__(self, "attributions", items)
        object.__setattr__(self, "metadata", _freeze_mapping(metadata))

    @property
    def feature_count(self) -> int:
        """Return the number of explained features."""
        return len(self.feature_names)

    def to_dict(self) -> dict[str, object]:
        """Return a deterministic, detached representation."""
        return {
            "dataset_name": deepcopy(self.dataset_name),
            "dataset_version": deepcopy(self.dataset_version),
            "model_name": deepcopy(self.model_name),
            "target_name": deepcopy(self.target_name),
            "class_labels": _thaw(self.class_labels),
            "feature_names": list(deepcopy(self.feature_names)),
            "attributions": [item.to_dict() for item in self.attributions],
            "normalization_method": self.normalization_method,
            "metadata": _thaw(self.metadata),
        }


class GlobalFeatureImportanceExplainer:
    """Explain supported trained snapshots using model-native global values."""

    explainer_name = "global-feature-importance"

    def explain(
        self,
        model: PreparedLogisticRegressionModel | PreparedRandomForestModel,
    ) -> GlobalFeatureImportanceResult:
        """Return an observation-independent global feature explanation."""
        if isinstance(model, PreparedLogisticRegressionModel):
            if len(model.class_labels) != 2:
                raise ValueError("logistic regression explanation requires two classes")
            if len(model.coefficients) != 1:
                raise ValueError("binary logistic coefficients must contain one row")
            raw_values = tuple(
                _number("coefficient", value) for value in model.coefficients[0]
            )
            model_name = "logistic-regression"
            unsigned = False
        elif isinstance(model, PreparedRandomForestModel):
            raw_values = tuple(
                _number("feature importance", value)
                for value in model.feature_importances
            )
            if any(value < 0.0 for value in raw_values):
                raise ValueError(
                    "random-forest feature importances must be non-negative"
                )
            model_name = "random-forest"
            unsigned = True
        else:
            raise TypeError(
                "model must be PreparedLogisticRegressionModel or "
                "PreparedRandomForestModel"
            )

        feature_names = tuple(model.feature_names)
        if len(raw_values) != len(feature_names):
            raise ValueError("model importance width must match feature_names")
        if not feature_names:
            raise ValueError("feature_names must not be empty")
        absolute_values = tuple(abs(value) for value in raw_values)
        total = math.fsum(absolute_values)
        normalized_values = (
            tuple(value / total for value in absolute_values)
            if total > 0.0
            else (0.0,) * len(absolute_values)
        )
        ranked = sorted(
            range(len(feature_names)),
            key=lambda index: (
                -normalized_values[index],
                -absolute_values[index],
                index,
            ),
        )
        attributions = tuple(
            GlobalFeatureAttribution(
                feature_name=feature_names[index],
                rank=rank,
                raw_importance=raw_values[index],
                absolute_importance=absolute_values[index],
                normalized_importance=normalized_values[index],
                direction=(
                    "unsigned"
                    if unsigned
                    else (
                        "positive"
                        if raw_values[index] > 0.0
                        else "negative"
                        if raw_values[index] < 0.0
                        else "neutral"
                    )
                ),
            )
            for rank, index in enumerate(ranked, start=1)
        )
        return GlobalFeatureImportanceResult(
            dataset_name=model.dataset_name,
            dataset_version=model.dataset_version,
            model_name=model_name,
            target_name=model.target_name,
            class_labels=model.class_labels,
            feature_names=feature_names,
            attributions=attributions,
            normalization_method="absolute-sum",
            metadata=model.metadata,
        )
