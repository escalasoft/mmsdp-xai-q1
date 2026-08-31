"""Deterministic optional adapters for XGBoost and LightGBM.

Imports are intentionally lazy so repository audits and non-boosting workflows
remain executable when the optional native dependencies are unavailable.
"""

from __future__ import annotations

import importlib
import math
import pickle
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import asdict, dataclass
from numbers import Real
from types import MappingProxyType

from dataset.model_input import PreparedModelInput

__all__ = [
    "DependencyUnavailableError",
    "XGBoostConfiguration",
    "LightGBMConfiguration",
    "PreparedBoostingModel",
    "XGBoostAdapter",
    "LightGBMAdapter",
    "XGBOOST_SEARCH_SPACE",
    "LIGHTGBM_SEARCH_SPACE",
]


class DependencyUnavailableError(RuntimeError):
    """Raised when an explicitly declared optional model dependency is absent."""


XGBOOST_SEARCH_SPACE = MappingProxyType(
    {
        "n_estimators": (100, 300, 600),
        "max_depth": (3, 6, 9),
        "learning_rate": (0.01, 0.05, 0.1),
        "subsample": (0.7, 1.0),
        "colsample_bytree": (0.7, 1.0),
        "min_child_weight": (1.0, 5.0),
        "reg_lambda": (1.0, 5.0),
    }
)
LIGHTGBM_SEARCH_SPACE = MappingProxyType(
    {
        "n_estimators": (100, 300, 600),
        "num_leaves": (15, 31, 63),
        "max_depth": (-1, 6, 12),
        "learning_rate": (0.01, 0.05, 0.1),
        "subsample": (0.7, 1.0),
        "colsample_bytree": (0.7, 1.0),
        "reg_lambda": (1.0, 5.0),
    }
)


def _positive(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{name} must be numeric")
    normalized = float(value)
    if not math.isfinite(normalized) or normalized <= 0:
        raise ValueError(f"{name} must be finite and greater than zero")
    return normalized


def _unit_interval(name: str, value: object) -> float:
    normalized = _positive(name, value)
    if normalized > 1:
        raise ValueError(f"{name} must be at most one")
    return normalized


def _integer(name: str, value: object, *, minimum: int = 1) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value < minimum:
        raise ValueError(f"{name} must be at least {minimum}")
    return value


@dataclass(frozen=True, slots=True)
class XGBoostConfiguration:
    n_estimators: int = 300
    max_depth: int = 6
    learning_rate: float = 0.05
    subsample: float = 1.0
    colsample_bytree: float = 1.0
    min_child_weight: float = 1.0
    reg_lambda: float = 1.0
    random_state: int = 20260829

    def __post_init__(self) -> None:
        _integer("n_estimators", self.n_estimators)
        _integer("max_depth", self.max_depth)
        _positive("learning_rate", self.learning_rate)
        _unit_interval("subsample", self.subsample)
        _unit_interval("colsample_bytree", self.colsample_bytree)
        _positive("min_child_weight", self.min_child_weight)
        _positive("reg_lambda", self.reg_lambda)
        _integer("random_state", self.random_state, minimum=0)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class LightGBMConfiguration:
    n_estimators: int = 300
    num_leaves: int = 31
    max_depth: int = -1
    learning_rate: float = 0.05
    subsample: float = 1.0
    colsample_bytree: float = 1.0
    reg_lambda: float = 1.0
    random_state: int = 20260829

    def __post_init__(self) -> None:
        _integer("n_estimators", self.n_estimators)
        _integer("num_leaves", self.num_leaves, minimum=2)
        if self.max_depth != -1:
            _integer("max_depth", self.max_depth)
        _positive("learning_rate", self.learning_rate)
        _unit_interval("subsample", self.subsample)
        _unit_interval("colsample_bytree", self.colsample_bytree)
        _positive("reg_lambda", self.reg_lambda)
        _integer("random_state", self.random_state, minimum=0)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PreparedBoostingModel:
    family: str
    dataset_name: str
    dataset_version: str
    feature_names: tuple[str, ...]
    target_name: str
    class_labels: tuple[object, ...]
    feature_importances: tuple[float, ...]
    configuration: Mapping[str, object]
    metadata: Mapping[str, object]
    serialized_estimator: bytes

    def to_dict(self) -> dict[str, object]:
        return {
            "family": self.family,
            "dataset_name": self.dataset_name,
            "dataset_version": self.dataset_version,
            "feature_names": list(self.feature_names),
            "target_name": self.target_name,
            "class_labels": list(self.class_labels),
            "feature_importances": list(self.feature_importances),
            "configuration": dict(self.configuration),
            "metadata": dict(self.metadata),
            "serialized_estimator_sha256_recorded_elsewhere": True,
        }


class _BoostingAdapter:
    module_name = ""
    estimator_name = ""
    family = ""

    def __init__(self, configuration: object) -> None:
        self.configuration = configuration

    def _estimator(self):
        try:
            module = importlib.import_module(self.module_name)
        except Exception as error:
            raise DependencyUnavailableError(
                f"{self.module_name} is required for {self.family} training"
            ) from error
        return getattr(module, self.estimator_name)

    def train(self, prepared_input: PreparedModelInput, /) -> PreparedBoostingModel:
        if not isinstance(prepared_input, PreparedModelInput):
            raise TypeError("prepared_input must be a PreparedModelInput")
        if len(set(prepared_input.train.y)) < 2:
            raise ValueError("training targets must contain at least two classes")
        for row in prepared_input.train.X:
            for value in row:
                if isinstance(value, bool) or not isinstance(value, Real):
                    raise TypeError("training features must contain numeric values")
                if not math.isfinite(float(value)):
                    raise ValueError("training features must contain finite values")
        configuration = self.configuration.to_dict()
        estimator_type = self._estimator()
        estimator = estimator_type(
            **configuration,
            n_jobs=1,
            verbosity=0,
        )
        estimator.fit(prepared_input.train.X, prepared_input.train.y)
        labels = tuple(
            value.item() if hasattr(value, "item") else deepcopy(value)
            for value in estimator.classes_
        )
        return PreparedBoostingModel(
            family=self.family,
            dataset_name=prepared_input.dataset_name,
            dataset_version=prepared_input.dataset_version,
            feature_names=prepared_input.feature_names,
            target_name=prepared_input.target_name,
            class_labels=labels,
            feature_importances=tuple(
                float(value) for value in estimator.feature_importances_
            ),
            configuration=MappingProxyType(configuration),
            metadata=MappingProxyType(dict(prepared_input.metadata)),
            serialized_estimator=pickle.dumps(estimator, protocol=5),
        )


class XGBoostAdapter(_BoostingAdapter):
    module_name = "xgboost"
    estimator_name = "XGBClassifier"
    family = "xgboost"

    def __init__(self, configuration: XGBoostConfiguration) -> None:
        if not isinstance(configuration, XGBoostConfiguration):
            raise TypeError("configuration must be XGBoostConfiguration")
        super().__init__(configuration)


class LightGBMAdapter(_BoostingAdapter):
    module_name = "lightgbm"
    estimator_name = "LGBMClassifier"
    family = "lightgbm"

    def __init__(self, configuration: LightGBMConfiguration) -> None:
        if not isinstance(configuration, LightGBMConfiguration):
            raise TypeError("configuration must be LightGBMConfiguration")
        super().__init__(configuration)
