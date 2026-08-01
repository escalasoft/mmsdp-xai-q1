"""Reproducible training adapter for logistic regression."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from numbers import Integral, Real
from types import MappingProxyType

from sklearn.linear_model import LogisticRegression

from dataset.model_input import PreparedModelInput

__all__ = [
    "LogisticRegressionConfiguration",
    "PreparedLogisticRegressionModel",
    "LogisticRegressionAdapter",
]

_SOLVERS = frozenset(
    {"lbfgs", "liblinear", "newton-cg", "newton-cholesky", "sag", "saga"}
)


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


def _positive_real(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{name} must be numeric and must not be bool")
    normalized = float(value)
    if not math.isfinite(normalized) or normalized <= 0.0:
        raise ValueError(f"{name} must be finite and greater than zero")
    return normalized


def _has_duplicates(values: Sequence[object]) -> bool:
    return any(
        value == previous
        for index, value in enumerate(values)
        for previous in values[:index]
    )


@dataclass(frozen=True, slots=True, init=False)
class LogisticRegressionConfiguration:
    """Validated, deterministic logistic-regression training settings."""

    C: float
    fit_intercept: bool
    class_weight: Mapping[object, float] | None
    random_state: int
    solver: str
    max_iter: int
    tol: float

    def __init__(
        self,
        C: float = 1.0,
        fit_intercept: bool = True,
        class_weight: Mapping[object, float] | None = None,
        random_state: int = 0,
        solver: str = "lbfgs",
        max_iter: int = 1000,
        tol: float = 1e-4,
    ) -> None:
        normalized_c = _positive_real("C", C)
        normalized_tol = _positive_real("tol", tol)
        if not isinstance(fit_intercept, bool):
            raise TypeError("fit_intercept must be bool")
        if class_weight is not None and not isinstance(class_weight, Mapping):
            raise TypeError("class_weight must be a mapping or None")
        if class_weight is not None:
            normalized_weights: dict[object, float] = {}
            for label, weight in class_weight.items():
                normalized_weights[deepcopy(label)] = _positive_real(
                    "class_weight values", weight
                )
            immutable_weights = MappingProxyType(normalized_weights)
        else:
            immutable_weights = None
        if isinstance(random_state, bool) or not isinstance(random_state, Integral):
            raise TypeError("random_state must be an integer and must not be bool")
        if not isinstance(solver, str):
            raise TypeError("solver must be a string")
        if solver not in _SOLVERS:
            raise ValueError(f"solver must be one of {sorted(_SOLVERS)}")
        if isinstance(max_iter, bool) or not isinstance(max_iter, Integral):
            raise TypeError("max_iter must be an integer and must not be bool")
        if max_iter <= 0:
            raise ValueError("max_iter must be greater than zero")

        object.__setattr__(self, "C", normalized_c)
        object.__setattr__(self, "fit_intercept", fit_intercept)
        object.__setattr__(self, "class_weight", immutable_weights)
        object.__setattr__(self, "random_state", int(random_state))
        object.__setattr__(self, "solver", solver)
        object.__setattr__(self, "max_iter", int(max_iter))
        object.__setattr__(self, "tol", normalized_tol)

    def to_dict(self) -> dict[str, object]:
        """Return a deterministic, detached standard-container representation."""
        return {
            "C": self.C,
            "fit_intercept": self.fit_intercept,
            "class_weight": _thaw(self.class_weight),
            "random_state": self.random_state,
            "solver": self.solver,
            "max_iter": self.max_iter,
            "tol": self.tol,
        }


@dataclass(frozen=True, slots=True, init=False)
class PreparedLogisticRegressionModel:
    """Immutable, framework-neutral snapshot of learned model parameters."""

    dataset_name: str
    dataset_version: str
    feature_names: tuple[str, ...]
    target_name: str
    class_labels: tuple[object, ...]
    coefficients: tuple[tuple[float, ...], ...]
    intercepts: tuple[float, ...]
    iteration_counts: tuple[int, ...]
    configuration: LogisticRegressionConfiguration
    metadata: Mapping[str, object]

    def __init__(
        self,
        dataset_name: str,
        dataset_version: str,
        feature_names: Sequence[str],
        target_name: str,
        class_labels: Sequence[object],
        coefficients: Sequence[Sequence[float]],
        intercepts: Sequence[float],
        iteration_counts: Sequence[int],
        configuration: LogisticRegressionConfiguration,
        metadata: Mapping[str, object] = MappingProxyType({}),
    ) -> None:
        if not isinstance(configuration, LogisticRegressionConfiguration):
            raise TypeError("configuration must be LogisticRegressionConfiguration")
        if not isinstance(metadata, Mapping):
            raise TypeError("metadata must be a mapping")
        names = tuple(feature_names)
        labels = tuple(deepcopy(tuple(class_labels)))
        coefficient_rows = tuple(
            tuple(float(value) for value in row) for row in coefficients
        )
        normalized_intercepts = tuple(float(value) for value in intercepts)
        normalized_iterations = tuple(int(value) for value in iteration_counts)
        if not names or not labels or not coefficient_rows:
            raise ValueError("features, classes, and coefficients must not be empty")
        if _has_duplicates(labels):
            raise ValueError("class_labels must not contain duplicates")
        if any(len(row) != len(names) for row in coefficient_rows):
            raise ValueError("every coefficient row must match feature_names")
        if len(coefficient_rows) != len(normalized_intercepts):
            raise ValueError("coefficients and intercepts must align")
        if not normalized_iterations:
            raise ValueError("iteration_counts must not be empty")
        numeric_values = (value for row in coefficient_rows for value in row)
        if any(not math.isfinite(value) for value in numeric_values) or any(
            not math.isfinite(value) for value in normalized_intercepts
        ):
            raise ValueError("learned parameters must be finite")

        object.__setattr__(self, "dataset_name", deepcopy(dataset_name))
        object.__setattr__(self, "dataset_version", deepcopy(dataset_version))
        object.__setattr__(self, "feature_names", tuple(deepcopy(names)))
        object.__setattr__(self, "target_name", deepcopy(target_name))
        object.__setattr__(self, "class_labels", labels)
        object.__setattr__(self, "coefficients", coefficient_rows)
        object.__setattr__(self, "intercepts", normalized_intercepts)
        object.__setattr__(self, "iteration_counts", normalized_iterations)
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
            "coefficients": _thaw(self.coefficients),
            "intercepts": list(self.intercepts),
            "iteration_counts": list(self.iteration_counts),
            "configuration": self.configuration.to_dict(),
            "metadata": _thaw(self.metadata),
        }


class LogisticRegressionAdapter:
    """Train logistic regression without preprocessing or inference behavior."""

    adapter_name = "logistic-regression"

    def __init__(self, configuration: LogisticRegressionConfiguration) -> None:
        if not isinstance(configuration, LogisticRegressionConfiguration):
            raise TypeError("configuration must be LogisticRegressionConfiguration")
        self._configuration = configuration

    @property
    def configuration(self) -> LogisticRegressionConfiguration:
        """Return the immutable training configuration."""
        return self._configuration

    def train(
        self, prepared_input: PreparedModelInput, /
    ) -> PreparedLogisticRegressionModel:
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

        estimator = LogisticRegression(
            C=self.configuration.C,
            fit_intercept=self.configuration.fit_intercept,
            class_weight=(
                None
                if self.configuration.class_weight is None
                else dict(self.configuration.class_weight)
            ),
            random_state=self.configuration.random_state,
            solver=self.configuration.solver,
            max_iter=self.configuration.max_iter,
            tol=self.configuration.tol,
        )
        estimator.fit(prepared_input.train.X, labels)

        return PreparedLogisticRegressionModel(
            dataset_name=prepared_input.dataset_name,
            dataset_version=prepared_input.dataset_version,
            feature_names=prepared_input.feature_names,
            target_name=prepared_input.target_name,
            class_labels=tuple(
                value.item() if hasattr(value, "item") else deepcopy(value)
                for value in estimator.classes_
            ),
            coefficients=estimator.coef_.tolist(),
            intercepts=estimator.intercept_.tolist(),
            iteration_counts=estimator.n_iter_.tolist(),
            configuration=self.configuration,
            metadata=prepared_input.metadata,
        )
