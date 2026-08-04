"""Deterministic model-family explanation strategy registries and outcomes."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from types import MappingProxyType

from explainability.counterfactual import (
    CounterfactualExplainer,
    CounterfactualExplanationResult,
)
from explainability.explanation_runner import ObservationExplanationRequest
from explainability.global_importance import (
    GlobalFeatureImportanceExplainer,
    GlobalFeatureImportanceResult,
)
from explainability.local_importance import (
    LocalFeatureImportanceExplainer,
    LocalFeatureImportanceResult,
)

__all__ = [
    "ExplanationOutcome",
    "ExplanationStrategyRegistry",
    "global_explanation_strategies",
    "local_explanation_strategies",
    "counterfactual_strategies",
]

ExplanationResult = (
    GlobalFeatureImportanceResult
    | LocalFeatureImportanceResult
    | CounterfactualExplanationResult
)


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


@dataclass(frozen=True, slots=True, init=False)
class ExplanationOutcome:
    partition_name: str
    observation_identifier: object
    request_position: int
    status: str
    explanation_method: str | None
    explanation: ExplanationResult | None
    reason_code: str | None
    model_fingerprint: str

    def __init__(
        self,
        request: ObservationExplanationRequest,
        request_position: int,
        *,
        status: str,
        explanation_method: str | None,
        explanation: ExplanationResult | None,
        reason_code: str | None,
        model_fingerprint: str,
    ) -> None:
        if status not in {"successful", "unsupported"}:
            raise ValueError("status must be successful or unsupported")
        if isinstance(request_position, bool) or request_position < 0:
            raise ValueError("request_position must be a non-negative integer")
        if status == "successful":
            if (
                explanation is None
                or explanation_method is None
                or reason_code is not None
            ):
                raise ValueError("successful outcomes require a method and explanation")
        elif (
            explanation is not None
            or explanation_method is not None
            or reason_code
            not in {
                "model-method-incompatible",
                "strategy-not-registered",
            }
        ):
            raise ValueError("unsupported outcomes require an explicit reason code")
        object.__setattr__(self, "partition_name", request.partition_name)
        object.__setattr__(
            self, "observation_identifier", _freeze(request.observation_identifier)
        )
        object.__setattr__(self, "request_position", request_position)
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "explanation_method", explanation_method)
        object.__setattr__(self, "explanation", explanation)
        object.__setattr__(self, "reason_code", reason_code)
        object.__setattr__(self, "model_fingerprint", model_fingerprint)

    def to_dict(self) -> dict[str, object]:
        return {
            "partition_name": self.partition_name,
            "observation_identifier": _thaw(self.observation_identifier),
            "request_position": self.request_position,
            "status": self.status,
            "explanation_method": self.explanation_method,
            "explanation": (
                None if self.explanation is None else self.explanation.to_dict()
            ),
            "reason_code": self.reason_code,
            "model_fingerprint": self.model_fingerprint,
        }


class ExplanationStrategyRegistry:
    def __init__(self) -> None:
        self._strategies: dict[str, object] = {}

    def register(self, model_family: str, strategy: object) -> None:
        if model_family in self._strategies:
            raise ValueError("model family is already registered")
        if not isinstance(model_family, str) or not model_family.strip():
            raise ValueError("model_family must be a non-empty string")
        if not callable(strategy):
            raise TypeError("strategy must be callable")
        self._strategies[model_family] = strategy

    def resolve(self, model_family: str) -> object | None:
        return self._strategies.get(model_family)

    @property
    def strategies(self) -> Mapping[str, object]:
        return MappingProxyType(dict(self._strategies))


global_explanation_strategies = ExplanationStrategyRegistry()
local_explanation_strategies = ExplanationStrategyRegistry()
counterfactual_strategies = ExplanationStrategyRegistry()


def _global(model, _identifier=None, _values=None):
    return GlobalFeatureImportanceExplainer().explain(model.native_model)


def _local(model, identifier, values):
    return LocalFeatureImportanceExplainer().explain(
        model.native_model, identifier, values
    )


def _counterfactual(model, identifier, values):
    return CounterfactualExplainer().explain(model.native_model, identifier, values)


global_explanation_strategies.register("logistic-regression", _global)
global_explanation_strategies.register("random-forest", _global)
local_explanation_strategies.register("logistic-regression", _local)
counterfactual_strategies.register("logistic-regression", _counterfactual)
