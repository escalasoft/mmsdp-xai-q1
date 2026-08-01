"""Reproducible training adapter for random-forest classification."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from numbers import Integral, Real
from types import MappingProxyType

from sklearn.ensemble import RandomForestClassifier

from dataset.model_input import PreparedModelInput

__all__ = [
    "RandomForestConfiguration",
    "PreparedRandomForestModel",
    "RandomForestAdapter",
]

_CRITERIA = frozenset({"gini", "entropy", "log_loss"})
_CLASS_WEIGHT_PRESETS = frozenset({"balanced", "balanced_subsample"})
_MAX_FEATURE_PRESETS = frozenset({"sqrt", "log2"})


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
    """Return a detached representation containing standard containers."""
    if isinstance(value, Mapping):
        return {deepcopy(key): _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    if isinstance(value, frozenset):
        return {_thaw(item) for item in value}
    return deepcopy(value)


def _positive_integer(name: str, value: object, minimum: int = 1) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise TypeError(f"{name} must be an integer and must not be bool")
    if value < minimum:
        raise ValueError(f"{name} must be at least {minimum}")
    return int(value)


def _sample_size(name: str, value: object, minimum: int) -> int | float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{name} must be numeric and must not be bool")
    if isinstance(value, Integral):
        return _positive_integer(name, value, minimum)
    normalized = float(value)
    if not math.isfinite(normalized) or not 0.0 < normalized <= 1.0:
        raise ValueError(f"{name} as a float must be finite and in (0, 1]")
    return normalized


def _has_duplicates(values: Sequence[object]) -> bool:
    return any(
        value == previous
        for index, value in enumerate(values)
        for previous in values[:index]
    )


@dataclass(frozen=True, slots=True, init=False)
class RandomForestConfiguration:
    """Validated, deterministic random-forest training settings."""

    n_estimators: int
    criterion: str
    max_depth: int | None
    min_samples_split: int | float
    min_samples_leaf: int | float
    max_features: str | int | float | None
    bootstrap: bool
    class_weight: Mapping[object, float] | str | None
    random_state: int

    def __init__(
        self,
        n_estimators: int = 100,
        criterion: str = "gini",
        max_depth: int | None = None,
        min_samples_split: int | float = 2,
        min_samples_leaf: int | float = 1,
        max_features: str | int | float | None = "sqrt",
        bootstrap: bool = True,
        class_weight: Mapping[object, float] | str | None = None,
        random_state: int = 0,
    ) -> None:
        normalized_estimators = _positive_integer("n_estimators", n_estimators)
        if not isinstance(criterion, str):
            raise TypeError("criterion must be a string")
        if criterion not in _CRITERIA:
            raise ValueError(f"criterion must be one of {sorted(_CRITERIA)}")
        normalized_depth = (
            None if max_depth is None else _positive_integer("max_depth", max_depth)
        )
        normalized_split = _sample_size("min_samples_split", min_samples_split, 2)
        normalized_leaf = _sample_size("min_samples_leaf", min_samples_leaf, 1)
        if max_features is None:
            normalized_features: str | int | float | None = None
        elif isinstance(max_features, str):
            if max_features not in _MAX_FEATURE_PRESETS:
                raise ValueError(
                    f"max_features must be one of {sorted(_MAX_FEATURE_PRESETS)}"
                )
            normalized_features = max_features
        elif isinstance(max_features, Integral) and not isinstance(max_features, bool):
            normalized_features = _positive_integer("max_features", max_features)
        elif isinstance(max_features, Real) and not isinstance(max_features, bool):
            normalized_features = float(max_features)
            if (
                not math.isfinite(normalized_features)
                or not 0.0 < normalized_features <= 1.0
            ):
                raise ValueError("max_features as a float must be finite and in (0, 1]")
        else:
            raise TypeError("max_features must be a string, integer, float, or None")
        if not isinstance(bootstrap, bool):
            raise TypeError("bootstrap must be bool")
        if isinstance(class_weight, str):
            if class_weight not in _CLASS_WEIGHT_PRESETS:
                raise ValueError(
                    f"class_weight must be one of {sorted(_CLASS_WEIGHT_PRESETS)}"
                )
            immutable_weights: Mapping[object, float] | str | None = class_weight
        elif class_weight is None:
            immutable_weights = None
        elif isinstance(class_weight, Mapping):
            normalized_weights: dict[object, float] = {}
            for label, weight in class_weight.items():
                if isinstance(weight, bool) or not isinstance(weight, Real):
                    raise TypeError("class_weight values must be numeric and not bool")
                normalized_weight = float(weight)
                if not math.isfinite(normalized_weight) or normalized_weight <= 0.0:
                    raise ValueError(
                        "class_weight values must be finite and greater than zero"
                    )
                normalized_weights[deepcopy(label)] = normalized_weight
            immutable_weights = MappingProxyType(normalized_weights)
        else:
            raise TypeError("class_weight must be a mapping, preset string, or None")
        if isinstance(random_state, bool) or not isinstance(random_state, Integral):
            raise TypeError("random_state must be an integer and must not be bool")
        normalized_seed = int(random_state)

        object.__setattr__(self, "n_estimators", normalized_estimators)
        object.__setattr__(self, "criterion", criterion)
        object.__setattr__(self, "max_depth", normalized_depth)
        object.__setattr__(self, "min_samples_split", normalized_split)
        object.__setattr__(self, "min_samples_leaf", normalized_leaf)
        object.__setattr__(self, "max_features", normalized_features)
        object.__setattr__(self, "bootstrap", bootstrap)
        object.__setattr__(self, "class_weight", immutable_weights)
        object.__setattr__(self, "random_state", normalized_seed)

    def to_dict(self) -> dict[str, object]:
        """Return a deterministic, detached standard-container representation."""
        return {
            "n_estimators": self.n_estimators,
            "criterion": self.criterion,
            "max_depth": self.max_depth,
            "min_samples_split": self.min_samples_split,
            "min_samples_leaf": self.min_samples_leaf,
            "max_features": self.max_features,
            "bootstrap": self.bootstrap,
            "class_weight": _thaw(self.class_weight),
            "random_state": self.random_state,
        }


@dataclass(frozen=True, slots=True, init=False)
class PreparedRandomForestModel:
    """Immutable, framework-neutral snapshot of learned forest parameters."""

    dataset_name: str
    dataset_version: str
    feature_names: tuple[str, ...]
    target_name: str
    class_labels: tuple[object, ...]
    feature_importances: tuple[float, ...]
    tree_node_counts: tuple[int, ...]
    tree_max_depths: tuple[int, ...]
    configuration: RandomForestConfiguration
    metadata: Mapping[str, object]

    def __init__(
        self,
        dataset_name: str,
        dataset_version: str,
        feature_names: Sequence[str],
        target_name: str,
        class_labels: Sequence[object],
        feature_importances: Sequence[float],
        tree_node_counts: Sequence[int],
        tree_max_depths: Sequence[int],
        configuration: RandomForestConfiguration,
        metadata: Mapping[str, object] = MappingProxyType({}),
    ) -> None:
        if not isinstance(configuration, RandomForestConfiguration):
            raise TypeError("configuration must be RandomForestConfiguration")
        if not isinstance(metadata, Mapping):
            raise TypeError("metadata must be a mapping")
        names = tuple(feature_names)
        labels = tuple(deepcopy(tuple(class_labels)))
        importances = tuple(float(value) for value in feature_importances)
        node_counts = tuple(int(value) for value in tree_node_counts)
        depths = tuple(int(value) for value in tree_max_depths)
        if not names or not labels or not importances:
            raise ValueError("features, classes, and importances must not be empty")
        if _has_duplicates(labels):
            raise ValueError("class_labels must not contain duplicates")
        if len(importances) != len(names):
            raise ValueError("feature_importances must match feature_names")
        if len(node_counts) != configuration.n_estimators:
            raise ValueError("tree_node_counts must match n_estimators")
        if len(depths) != len(node_counts):
            raise ValueError("tree summaries must align")
        if any(not math.isfinite(value) or value < 0.0 for value in importances):
            raise ValueError("feature_importances must be finite and non-negative")
        if any(value <= 0 for value in node_counts) or any(
            value < 0 for value in depths
        ):
            raise ValueError("tree summaries contain invalid values")

        object.__setattr__(self, "dataset_name", deepcopy(dataset_name))
        object.__setattr__(self, "dataset_version", deepcopy(dataset_version))
        object.__setattr__(self, "feature_names", tuple(deepcopy(names)))
        object.__setattr__(self, "target_name", deepcopy(target_name))
        object.__setattr__(self, "class_labels", labels)
        object.__setattr__(self, "feature_importances", importances)
        object.__setattr__(self, "tree_node_counts", node_counts)
        object.__setattr__(self, "tree_max_depths", depths)
        object.__setattr__(self, "configuration", configuration)
        object.__setattr__(self, "metadata", _freeze_mapping(metadata))

    def to_dict(self) -> dict[str, object]:
        """Return a deterministic, fully detached standard representation."""
        return {
            "dataset_name": deepcopy(self.dataset_name),
            "dataset_version": deepcopy(self.dataset_version),
            "feature_names": list(deepcopy(self.feature_names)),
            "target_name": deepcopy(self.target_name),
            "class_labels": _thaw(self.class_labels),
            "feature_importances": list(self.feature_importances),
            "tree_node_counts": list(self.tree_node_counts),
            "tree_max_depths": list(self.tree_max_depths),
            "configuration": self.configuration.to_dict(),
            "metadata": _thaw(self.metadata),
        }


class RandomForestAdapter:
    """Train a random forest without preprocessing or inference behavior."""

    adapter_name = "random-forest"

    def __init__(self, configuration: RandomForestConfiguration) -> None:
        if not isinstance(configuration, RandomForestConfiguration):
            raise TypeError("configuration must be RandomForestConfiguration")
        self._configuration = configuration

    @property
    def configuration(self) -> RandomForestConfiguration:
        """Return the immutable training configuration."""
        return self._configuration

    def train(self, prepared_input: PreparedModelInput, /) -> PreparedRandomForestModel:
        """Fit only the supplied training partition and snapshot learned values."""
        if not isinstance(prepared_input, PreparedModelInput):
            raise TypeError("prepared_input must be a PreparedModelInput")
        labels = prepared_input.train.y
        unique_labels: list[object] = []
        for label in labels:
            if not any(label == existing for existing in unique_labels):
                unique_labels.append(label)
        if len(unique_labels) < 2:
            raise ValueError("training targets must contain at least two classes")
        for row in prepared_input.train.X:
            for value in row:
                if isinstance(value, bool) or not isinstance(value, Real):
                    raise TypeError("training features must contain numeric values")
                if not math.isfinite(float(value)):
                    raise ValueError("training features must contain finite values")

        estimator = RandomForestClassifier(
            **self.configuration.to_dict(),
            n_jobs=1,
        )
        estimator.fit(prepared_input.train.X, labels)

        return PreparedRandomForestModel(
            dataset_name=prepared_input.dataset_name,
            dataset_version=prepared_input.dataset_version,
            feature_names=prepared_input.feature_names,
            target_name=prepared_input.target_name,
            class_labels=tuple(
                value.item() if hasattr(value, "item") else deepcopy(value)
                for value in estimator.classes_
            ),
            feature_importances=estimator.feature_importances_.tolist(),
            tree_node_counts=tuple(
                tree.tree_.node_count for tree in estimator.estimators_
            ),
            tree_max_depths=tuple(
                tree.tree_.max_depth for tree in estimator.estimators_
            ),
            configuration=self.configuration,
            metadata=prepared_input.metadata,
        )
