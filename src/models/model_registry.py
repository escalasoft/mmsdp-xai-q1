"""Generic immutable trained-model contract and deterministic adapter registry."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from types import MappingProxyType
from typing import Protocol, runtime_checkable

from dataset.model_input import ModelPartitionInput, PreparedModelInput
from models.logistic_regression_adapter import (
    LogisticRegressionAdapter,
    LogisticRegressionConfiguration,
    PreparedLogisticRegressionModel,
)
from models.prediction import ModelPredictionResult, ModelPredictor
from models.random_forest_adapter import (
    PreparedRandomForestModel,
    RandomForestAdapter,
    RandomForestConfiguration,
)

__all__ = [
    "ModelCapabilities",
    "PreparedTrainedModel",
    "ModelAdapter",
    "ModelAdapterRegistry",
    "default_model_adapter_registry",
]


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
        return sorted((_thaw(item) for item in value), key=repr)
    return deepcopy(value)


def _digest(value: object) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class ModelCapabilities:
    prediction: bool = True
    probability_prediction: bool = True
    global_explanation: bool = True
    local_explanation: bool = False
    counterfactual_explanation: bool = False

    def to_dict(self) -> dict[str, bool]:
        return {
            "prediction": self.prediction,
            "probability_prediction": self.probability_prediction,
            "global_explanation": self.global_explanation,
            "local_explanation": self.local_explanation,
            "counterfactual_explanation": self.counterfactual_explanation,
        }


NativeModel = PreparedLogisticRegressionModel | PreparedRandomForestModel


@dataclass(frozen=True, slots=True, init=False)
class PreparedTrainedModel:
    """One immutable generic artifact produced by exactly one base-model fit."""

    model_name: str
    model_family: str
    dataset_name: str
    dataset_version: str
    feature_names: tuple[str, ...]
    target_name: str
    class_labels: tuple[object, ...]
    training_observation_count: int
    configuration: Mapping[str, object]
    learned_state: Mapping[str, object]
    capabilities: ModelCapabilities
    metadata: Mapping[str, object]
    model_fingerprint: str
    native_model: NativeModel
    predictions: Mapping[str, ModelPredictionResult]

    def __init__(
        self,
        *,
        model_name: str,
        model_family: str,
        training_observation_count: int,
        native_model: NativeModel,
        capabilities: ModelCapabilities,
        predictions: Mapping[str, ModelPredictionResult],
    ) -> None:
        if not isinstance(
            native_model, (PreparedLogisticRegressionModel, PreparedRandomForestModel)
        ):
            raise TypeError("native_model must be a supported immutable snapshot")
        if not isinstance(capabilities, ModelCapabilities):
            raise TypeError("capabilities must be ModelCapabilities")
        if set(predictions) != {"validation", "test"}:
            raise ValueError("predictions must contain validation and test")
        configuration = native_model.configuration.to_dict()
        learned_state = native_model.to_dict()
        learned_state.pop("metadata", None)
        fingerprint = _digest(
            {
                "model_name": model_name,
                "model_family": model_family,
                "dataset_name": native_model.dataset_name,
                "dataset_version": native_model.dataset_version,
                "feature_names": list(native_model.feature_names),
                "target_name": native_model.target_name,
                "class_labels": _thaw(native_model.class_labels),
                "training_observation_count": training_observation_count,
                "configuration": configuration,
                "learned_state": learned_state,
            }
        )
        traced_predictions = {
            name: ModelPredictionResult(
                dataset_name=result.dataset_name,
                dataset_version=result.dataset_version,
                partition_name=result.partition_name,
                model_name=result.model_name,
                identifiers=result.identifiers,
                class_labels=result.class_labels,
                predictions=result.predictions,
                probabilities=result.probabilities,
                observation_count=result.observation_count,
                metadata={
                    **_thaw(result.metadata),
                    "model_fingerprint": fingerprint,
                },
            )
            for name, result in predictions.items()
        }
        object.__setattr__(self, "model_name", model_name)
        object.__setattr__(self, "model_family", model_family)
        object.__setattr__(self, "dataset_name", native_model.dataset_name)
        object.__setattr__(self, "dataset_version", native_model.dataset_version)
        object.__setattr__(self, "feature_names", native_model.feature_names)
        object.__setattr__(self, "target_name", native_model.target_name)
        object.__setattr__(self, "class_labels", native_model.class_labels)
        object.__setattr__(
            self, "training_observation_count", training_observation_count
        )
        object.__setattr__(self, "configuration", _freeze(configuration))
        object.__setattr__(self, "learned_state", _freeze(learned_state))
        object.__setattr__(self, "capabilities", capabilities)
        object.__setattr__(self, "metadata", _freeze(native_model.metadata))
        object.__setattr__(self, "model_fingerprint", fingerprint)
        object.__setattr__(self, "native_model", native_model)
        object.__setattr__(self, "predictions", MappingProxyType(traced_predictions))

    def to_dict(self) -> dict[str, object]:
        return {
            "model_name": self.model_name,
            "model_family": self.model_family,
            "dataset_name": self.dataset_name,
            "dataset_version": self.dataset_version,
            "feature_names": list(self.feature_names),
            "target_name": self.target_name,
            "class_labels": _thaw(self.class_labels),
            "training_observation_count": self.training_observation_count,
            "configuration": _thaw(self.configuration),
            "learned_state": _thaw(self.learned_state),
            "capabilities": self.capabilities.to_dict(),
            "metadata": _thaw(self.metadata),
            "model_fingerprint": self.model_fingerprint,
        }


@runtime_checkable
class ModelAdapter(Protocol):
    def train(self, prepared_input: PreparedModelInput) -> PreparedTrainedModel: ...

    def predict(
        self, trained_model: PreparedTrainedModel, partition_input: ModelPartitionInput
    ) -> ModelPredictionResult: ...


class _RegisteredAdapter:
    def __init__(self, configuration: object) -> None:
        if isinstance(configuration, LogisticRegressionConfiguration):
            self._adapter = LogisticRegressionAdapter(configuration)
            self._name = self._family = "logistic-regression"
            self._capabilities = ModelCapabilities(True, True, True, True, True)
        elif isinstance(configuration, RandomForestConfiguration):
            self._adapter = RandomForestAdapter(configuration)
            self._name = self._family = "random-forest"
            self._capabilities = ModelCapabilities()
        else:
            raise TypeError("unsupported model configuration")

    def train(self, prepared_input: PreparedModelInput) -> PreparedTrainedModel:
        native = self._adapter.train(prepared_input)
        predictor = ModelPredictor()
        predictions = {
            name: predictor.predict(native, prepared_input, name)
            for name in ("validation", "test")
        }
        return PreparedTrainedModel(
            model_name=self._name,
            model_family=self._family,
            training_observation_count=prepared_input.train.observation_count,
            native_model=native,
            capabilities=self._capabilities,
            predictions=predictions,
        )

    def predict(
        self, trained_model: PreparedTrainedModel, partition_input: ModelPartitionInput
    ) -> ModelPredictionResult:
        if partition_input.partition_name not in trained_model.predictions:
            raise ValueError("partition prediction is unavailable")
        result = trained_model.predictions[partition_input.partition_name]
        if result.identifiers != partition_input.identifiers:
            raise ValueError("partition identifiers do not match trained artifact")
        return result


class ModelAdapterRegistry:
    """Deterministic configuration-type to adapter-factory registry."""

    def __init__(self) -> None:
        self._factories: dict[type[object], object] = {}

    def register(self, configuration_type: type[object], factory: object) -> None:
        if configuration_type in self._factories:
            raise ValueError("configuration type is already registered")
        if not isinstance(configuration_type, type) or not callable(factory):
            raise TypeError("registration requires a type and callable factory")
        self._factories[configuration_type] = factory

    def resolve(self, configuration: object) -> ModelAdapter:
        factory = self._factories.get(type(configuration))
        if factory is None:
            raise TypeError("unsupported model configuration")
        return factory(configuration)  # type: ignore[operator,no-any-return]


default_model_adapter_registry = ModelAdapterRegistry()
default_model_adapter_registry.register(
    LogisticRegressionConfiguration, _RegisteredAdapter
)
default_model_adapter_registry.register(RandomForestConfiguration, _RegisteredAdapter)
