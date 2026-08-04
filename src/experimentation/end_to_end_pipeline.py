"""Architecture-complete, single-training end-to-end experimentation."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from types import MappingProxyType

from dataset.contracts import AdaptedDataset
from dataset.experiment_dataset import (
    ExperimentDatasetPreparer,
    PreparedExperimentDataset,
)
from dataset.model_input import ModelInputBuilder, PreparedModelInput
from dataset.temporal_splitter import (
    TemporalDatasetSplit,
    TemporalDatasetSplitter,
    TemporalSplitConfiguration,
)
from explainability.counterfactual import CounterfactualExplanationResult
from explainability.explanation_runner import ObservationExplanationRequest
from explainability.global_importance import GlobalFeatureImportanceResult
from explainability.local_importance import LocalFeatureImportanceResult
from explainability.strategy_registry import (
    ExplanationOutcome,
    ExplanationStrategyRegistry,
    counterfactual_strategies,
    global_explanation_strategies,
    local_explanation_strategies,
)
from models.calibrated_experiment_runner import (
    CalibratedModelExperimentResult,
    CalibratedModelExperimentRunner,
)
from models.calibration import ProbabilityCalibrationConfiguration
from models.experiment_runner import ModelExperimentResult, ModelExperimentRunner
from models.model_registry import (
    ModelAdapterRegistry,
    PreparedTrainedModel,
    default_model_adapter_registry,
)

__all__ = [
    "EndToEndExperimentConfiguration",
    "EndToEndExperimentResult",
    "EndToEndExperimentPipeline",
]

_PARTITIONS = frozenset({"validation", "test"})


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


def _canonical(value: object) -> object:
    if isinstance(value, Mapping):
        return {
            str(key): _canonical(item)
            for key, item in sorted(value.items(), key=lambda pair: repr(pair[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_canonical(item) for item in value]
    if isinstance(value, (set, frozenset)):
        items = [_canonical(item) for item in value]
        return sorted(items, key=lambda item: json.dumps(item, sort_keys=True))
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    return {"type": type(value).__qualname__, "repr": repr(value)}


def _fingerprint(value: object) -> str:
    payload = json.dumps(
        _canonical(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _same(left: object, right: object) -> bool:
    return bool(left == right)


def _normalize_requests(
    name: str, value: object
) -> tuple[ObservationExplanationRequest, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise TypeError(f"{name} must be a sequence")
    requests = tuple(value)
    if any(not isinstance(item, ObservationExplanationRequest) for item in requests):
        raise TypeError(f"{name} must contain ObservationExplanationRequest values")
    if any(item.partition_name not in _PARTITIONS for item in requests):
        raise ValueError(f"{name} may identify only validation or test observations")
    if any(
        item.partition_name == previous.partition_name
        and _same(item.observation_identifier, previous.observation_identifier)
        for index, item in enumerate(requests)
        for previous in requests[:index]
    ):
        raise ValueError(f"{name} contains a duplicate structural request")
    return requests


@dataclass(frozen=True, slots=True, init=False)
class EndToEndExperimentConfiguration:
    temporal_split_configuration: TemporalSplitConfiguration
    model_configuration: object
    calibration_configuration: ProbabilityCalibrationConfiguration
    positive_label: object
    local_explanation_requests: tuple[ObservationExplanationRequest, ...]
    counterfactual_requests: tuple[ObservationExplanationRequest, ...]

    def __init__(
        self,
        temporal_split_configuration: TemporalSplitConfiguration,
        model_configuration: object,
        calibration_configuration: ProbabilityCalibrationConfiguration,
        positive_label: object,
        local_explanation_requests: Sequence[ObservationExplanationRequest] = (),
        counterfactual_requests: Sequence[ObservationExplanationRequest] = (),
    ) -> None:
        if not isinstance(temporal_split_configuration, TemporalSplitConfiguration):
            raise TypeError(
                "temporal_split_configuration must be a TemporalSplitConfiguration"
            )
        if not callable(getattr(model_configuration, "to_dict", None)):
            raise TypeError("model_configuration must provide deterministic to_dict()")
        if not isinstance(
            calibration_configuration, ProbabilityCalibrationConfiguration
        ):
            raise TypeError(
                "calibration_configuration must be a "
                "ProbabilityCalibrationConfiguration"
            )
        if not _same(positive_label, calibration_configuration.positive_label):
            raise ValueError("positive_label must match calibration configuration")
        object.__setattr__(
            self, "temporal_split_configuration", temporal_split_configuration
        )
        object.__setattr__(self, "model_configuration", model_configuration)
        object.__setattr__(self, "calibration_configuration", calibration_configuration)
        object.__setattr__(self, "positive_label", _freeze(positive_label))
        object.__setattr__(
            self,
            "local_explanation_requests",
            _normalize_requests(
                "local_explanation_requests", local_explanation_requests
            ),
        )
        object.__setattr__(
            self,
            "counterfactual_requests",
            _normalize_requests("counterfactual_requests", counterfactual_requests),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "temporal_split_configuration": self.temporal_split_configuration.to_dict(),
            "model_configuration": deepcopy(self.model_configuration.to_dict()),
            "calibration_configuration": self.calibration_configuration.to_dict(),
            "positive_label": _thaw(self.positive_label),
            "local_explanation_requests": [
                item.to_dict() for item in self.local_explanation_requests
            ],
            "counterfactual_requests": [
                item.to_dict() for item in self.counterfactual_requests
            ],
        }


@dataclass(frozen=True, slots=True, init=False)
class EndToEndExperimentResult:
    dataset_name: str
    dataset_version: str
    model_name: str
    temporal_split: TemporalDatasetSplit
    prepared_experiment_dataset: PreparedExperimentDataset
    prepared_model_input: PreparedModelInput
    trained_model: PreparedTrainedModel
    model_experiment_result: ModelExperimentResult
    calibrated_experiment_result: CalibratedModelExperimentResult
    global_explanation: GlobalFeatureImportanceResult
    local_explanation_requests: tuple[ObservationExplanationRequest, ...]
    counterfactual_requests: tuple[ObservationExplanationRequest, ...]
    local_explanation_outcomes: tuple[ExplanationOutcome, ...]
    counterfactual_outcomes: tuple[ExplanationOutcome, ...]
    local_explanations: tuple[LocalFeatureImportanceResult, ...]
    unsupported_local_requests: tuple[ObservationExplanationRequest, ...]
    counterfactual_explanations: tuple[CounterfactualExplanationResult, ...]
    unsupported_counterfactual_requests: tuple[ObservationExplanationRequest, ...]
    experiment_fingerprint: str
    metadata: Mapping[str, object]

    def __init__(
        self,
        *,
        temporal_split: TemporalDatasetSplit,
        prepared_experiment_dataset: PreparedExperimentDataset,
        prepared_model_input: PreparedModelInput,
        trained_model: PreparedTrainedModel,
        model_experiment_result: ModelExperimentResult,
        calibrated_experiment_result: CalibratedModelExperimentResult,
        global_explanation: GlobalFeatureImportanceResult,
        local_explanation_requests: Sequence[ObservationExplanationRequest],
        counterfactual_requests: Sequence[ObservationExplanationRequest],
        local_explanation_outcomes: Sequence[ExplanationOutcome],
        counterfactual_outcomes: Sequence[ExplanationOutcome],
        experiment_fingerprint: str,
        metadata: Mapping[str, object],
    ) -> None:
        dataset_name = trained_model.dataset_name
        dataset_version = trained_model.dataset_version
        model_name = trained_model.model_name
        identity = (
            temporal_split,
            prepared_experiment_dataset,
            prepared_model_input,
            model_experiment_result,
            calibrated_experiment_result,
            global_explanation,
        )
        if any(item.dataset_name != dataset_name for item in identity):
            raise ValueError("dataset identity must match across all stages")
        if any(item.dataset_version != dataset_version for item in identity):
            raise ValueError("dataset version must match across all stages")
        if any(
            item.feature_names != trained_model.feature_names
            for item in (
                temporal_split,
                prepared_experiment_dataset,
                prepared_model_input,
                global_explanation,
            )
        ):
            raise ValueError("feature schema must match across all stages")
        if any(
            item.target_name != trained_model.target_name
            for item in (
                temporal_split,
                prepared_experiment_dataset,
                prepared_model_input,
                global_explanation,
            )
        ):
            raise ValueError("target schema must match across all stages")
        if (
            calibrated_experiment_result.uncalibrated_experiment
            is not model_experiment_result
        ):
            raise ValueError(
                "calibration must reference the exact uncalibrated experiment"
            )
        for name, prediction, partition in (
            (
                "validation",
                model_experiment_result.validation_prediction,
                prepared_model_input.validation,
            ),
            (
                "test",
                model_experiment_result.test_prediction,
                prepared_model_input.test,
            ),
        ):
            if (
                prediction.partition_name != name
                or prediction.identifiers != partition.identifiers
            ):
                raise ValueError("prediction partition identifiers must align exactly")
            if prediction.observation_count != partition.observation_count:
                raise ValueError("prediction observation counts must align")
            if prediction.class_labels != trained_model.class_labels:
                raise ValueError("prediction class labels must match the trained model")
        if global_explanation.class_labels != trained_model.class_labels:
            raise ValueError("explanation class labels must match the trained model")
        local = tuple(local_explanation_outcomes)
        counterfactual = tuple(counterfactual_outcomes)
        local_requests = tuple(local_explanation_requests)
        counterfactual_requests_tuple = tuple(counterfactual_requests)
        for requests, outcomes in (
            (local_requests, local),
            (counterfactual_requests_tuple, counterfactual),
        ):
            if len(requests) != len(outcomes):
                raise ValueError(
                    "every explanation request requires exactly one outcome"
                )
            if tuple(item.request_position for item in outcomes) != tuple(
                range(len(outcomes))
            ):
                raise ValueError("explanation outcomes must be complete and ordered")
            if any(
                outcome.partition_name != request.partition_name
                or not _same(
                    outcome.observation_identifier,
                    request.observation_identifier,
                )
                for request, outcome in zip(requests, outcomes, strict=True)
            ):
                raise ValueError("explanation outcomes must align with requests")
            if any(
                outcome.model_fingerprint != trained_model.model_fingerprint
                for outcome in outcomes
            ):
                raise ValueError("explanation outcome model fingerprint must match")
        for capability, outcomes in (
            (trained_model.capabilities.local_explanation, local),
            (trained_model.capabilities.counterfactual_explanation, counterfactual),
        ):
            if not capability and any(item.status == "successful" for item in outcomes):
                raise ValueError("a disabled capability cannot produce explanations")
            if capability and any(
                item.reason_code == "model-method-incompatible" for item in outcomes
            ):
                raise ValueError("compatible methods cannot be marked incompatible")
        local_results = tuple(
            item.explanation for item in local if item.status == "successful"
        )
        counterfactual_results = tuple(
            item.explanation for item in counterfactual if item.status == "successful"
        )
        unsupported_local = tuple(
            ObservationExplanationRequest(
                item.partition_name, item.observation_identifier
            )
            for item in local
            if item.status == "unsupported"
        )
        unsupported_counterfactual = tuple(
            ObservationExplanationRequest(
                item.partition_name, item.observation_identifier
            )
            for item in counterfactual
            if item.status == "unsupported"
        )
        if metadata.get("model_training_execution_count") != 1:
            raise ValueError("model_training_execution_count must equal one")
        if metadata.get("shared_trained_model_instance") is not True:
            raise ValueError("shared_trained_model_instance must be true")
        object.__setattr__(self, "dataset_name", dataset_name)
        object.__setattr__(self, "dataset_version", dataset_version)
        object.__setattr__(self, "model_name", model_name)
        object.__setattr__(self, "temporal_split", temporal_split)
        object.__setattr__(
            self, "prepared_experiment_dataset", prepared_experiment_dataset
        )
        object.__setattr__(self, "prepared_model_input", prepared_model_input)
        object.__setattr__(self, "trained_model", trained_model)
        object.__setattr__(self, "model_experiment_result", model_experiment_result)
        object.__setattr__(
            self, "calibrated_experiment_result", calibrated_experiment_result
        )
        object.__setattr__(self, "global_explanation", global_explanation)
        object.__setattr__(self, "local_explanation_requests", local_requests)
        object.__setattr__(
            self, "counterfactual_requests", counterfactual_requests_tuple
        )
        object.__setattr__(self, "local_explanation_outcomes", local)
        object.__setattr__(self, "counterfactual_outcomes", counterfactual)
        object.__setattr__(self, "local_explanations", local_results)
        object.__setattr__(self, "unsupported_local_requests", unsupported_local)
        object.__setattr__(self, "counterfactual_explanations", counterfactual_results)
        object.__setattr__(
            self, "unsupported_counterfactual_requests", unsupported_counterfactual
        )
        object.__setattr__(self, "experiment_fingerprint", experiment_fingerprint)
        object.__setattr__(self, "metadata", _freeze(metadata))

    def to_dict(self) -> dict[str, object]:
        return {
            "dataset_name": self.dataset_name,
            "dataset_version": self.dataset_version,
            "model_name": self.model_name,
            "temporal_split": self.temporal_split.to_dict(),
            "prepared_experiment_dataset": self.prepared_experiment_dataset.to_dict(),
            "prepared_model_input": self.prepared_model_input.to_dict(),
            "trained_model": self.trained_model.to_dict(),
            "model_experiment_result": self.model_experiment_result.to_dict(),
            "calibrated_experiment_result": self.calibrated_experiment_result.to_dict(),
            "global_explanation": self.global_explanation.to_dict(),
            "local_explanation_requests": [
                item.to_dict() for item in self.local_explanation_requests
            ],
            "counterfactual_requests": [
                item.to_dict() for item in self.counterfactual_requests
            ],
            "local_explanation_outcomes": [
                item.to_dict() for item in self.local_explanation_outcomes
            ],
            "counterfactual_outcomes": [
                item.to_dict() for item in self.counterfactual_outcomes
            ],
            "local_explanations": [item.to_dict() for item in self.local_explanations],
            "unsupported_local_requests": [
                item.to_dict() for item in self.unsupported_local_requests
            ],
            "counterfactual_explanations": [
                item.to_dict() for item in self.counterfactual_explanations
            ],
            "unsupported_counterfactual_requests": [
                item.to_dict() for item in self.unsupported_counterfactual_requests
            ],
            "experiment_fingerprint": self.experiment_fingerprint,
            "metadata": _thaw(self.metadata),
        }


class EndToEndExperimentPipeline:
    pipeline_name = "end-to-end-experiment"

    @staticmethod
    def experiment_fingerprint(
        dataset: AdaptedDataset,
        configuration: EndToEndExperimentConfiguration,
    ) -> str:
        """Return the public deterministic fingerprint for scientific inputs."""
        if not isinstance(dataset, AdaptedDataset):
            raise TypeError("dataset must be an AdaptedDataset")
        if not isinstance(configuration, EndToEndExperimentConfiguration):
            raise TypeError("configuration must be an EndToEndExperimentConfiguration")
        return _fingerprint(
            {
                "dataset_name": dataset.dataset_name,
                "dataset_version": dataset.dataset_version,
                "feature_names": dataset.feature_names,
                "target_name": dataset.target_name,
                **configuration.to_dict(),
            }
        )

    def __init__(
        self,
        configuration: EndToEndExperimentConfiguration,
        *,
        model_registry: ModelAdapterRegistry = default_model_adapter_registry,
        global_registry: ExplanationStrategyRegistry = global_explanation_strategies,
        local_registry: ExplanationStrategyRegistry = local_explanation_strategies,
        counterfactual_registry: ExplanationStrategyRegistry = (
            counterfactual_strategies
        ),
    ) -> None:
        if not isinstance(configuration, EndToEndExperimentConfiguration):
            raise TypeError("configuration must be an EndToEndExperimentConfiguration")
        if not isinstance(model_registry, ModelAdapterRegistry):
            raise TypeError("model_registry must be a ModelAdapterRegistry")
        self._configuration = configuration
        self._model_registry = model_registry
        self._global_registry = global_registry
        self._local_registry = local_registry
        self._counterfactual_registry = counterfactual_registry

    @property
    def configuration(self) -> EndToEndExperimentConfiguration:
        return self._configuration

    def run(self, dataset: AdaptedDataset) -> EndToEndExperimentResult:
        if not isinstance(dataset, AdaptedDataset):
            raise TypeError("dataset must be an AdaptedDataset")
        split = TemporalDatasetSplitter(
            self.configuration.temporal_split_configuration
        ).split(dataset)
        prepared_dataset = ExperimentDatasetPreparer().prepare(split)
        prepared_input = ModelInputBuilder().build(prepared_dataset)
        adapter = self._model_registry.resolve(self.configuration.model_configuration)
        trained_model = adapter.train(prepared_input)
        experiment = ModelExperimentRunner(
            positive_label=self.configuration.positive_label
        ).run(trained_model, prepared_input)
        calibrated = CalibratedModelExperimentRunner(
            calibration_configuration=self.configuration.calibration_configuration,
            positive_label=self.configuration.positive_label,
        ).run(experiment, prepared_input)
        global_strategy = self._global_registry.resolve(trained_model.model_family)
        if not trained_model.capabilities.global_explanation or global_strategy is None:
            raise ValueError("a registered compatible global strategy is required")
        global_explanation = global_strategy(trained_model)  # type: ignore[operator]
        local_outcomes = self._outcomes(
            trained_model,
            prepared_input,
            self.configuration.local_explanation_requests,
            "local_explanation",
            self._local_registry,
            "linear-logit-contribution",
        )
        counterfactual_outcomes = self._outcomes(
            trained_model,
            prepared_input,
            self.configuration.counterfactual_requests,
            "counterfactual_explanation",
            self._counterfactual_registry,
            "minimal-single-feature-linear-boundary",
        )
        experiment_fingerprint = self.experiment_fingerprint(
            dataset, self.configuration
        )
        executed = ["global"]
        if any(item.status == "successful" for item in local_outcomes):
            executed.append("local")
        if any(item.status == "successful" for item in counterfactual_outcomes):
            executed.append("counterfactual")
        metadata = _thaw(dataset.metadata)
        metadata.update(
            {
                "model_capabilities": trained_model.capabilities.to_dict(),
                "strategies_executed": executed,
                "global_explanation_method": (
                    "model-native-feature-importance:absolute-sum"
                ),
                "calibration_method": (
                    self.configuration.calibration_configuration.method
                ),
                "split_configuration": (
                    self.configuration.temporal_split_configuration.to_dict()
                ),
                "model_configuration": deepcopy(
                    self.configuration.model_configuration.to_dict()
                ),
                "model_fingerprint": trained_model.model_fingerprint,
                "experiment_fingerprint": experiment_fingerprint,
                "model_training_execution_count": 1,
                "shared_trained_model_instance": True,
                "scientific_boundaries": {
                    "prediction_probability_calibration_are_distinct": True,
                    "local_attribution_is_not_probability_or_causality": True,
                    "counterfactual_is_model_boundary_not_actionability": True,
                },
            }
        )
        return EndToEndExperimentResult(
            temporal_split=split,
            prepared_experiment_dataset=prepared_dataset,
            prepared_model_input=prepared_input,
            trained_model=trained_model,
            model_experiment_result=experiment,
            calibrated_experiment_result=calibrated,
            global_explanation=global_explanation,
            local_explanation_requests=self.configuration.local_explanation_requests,
            counterfactual_requests=self.configuration.counterfactual_requests,
            local_explanation_outcomes=local_outcomes,
            counterfactual_outcomes=counterfactual_outcomes,
            experiment_fingerprint=experiment_fingerprint,
            metadata=metadata,
        )

    @staticmethod
    def _outcomes(
        model: PreparedTrainedModel,
        prepared_input: PreparedModelInput,
        requests: Sequence[ObservationExplanationRequest],
        capability_name: str,
        registry: ExplanationStrategyRegistry,
        method: str,
    ) -> tuple[ExplanationOutcome, ...]:
        capability = getattr(model.capabilities, capability_name)
        strategy = registry.resolve(model.model_family)
        outcomes = []
        for position, request in enumerate(requests):
            partition = getattr(prepared_input, request.partition_name)
            matches = [
                index
                for index, identifier in enumerate(partition.identifiers)
                if _same(identifier, request.observation_identifier)
            ]
            if len(matches) != 1:
                raise ValueError("each request must locate exactly one feature row")
            if not capability:
                outcomes.append(
                    ExplanationOutcome(
                        request,
                        position,
                        status="unsupported",
                        explanation_method=None,
                        explanation=None,
                        reason_code="model-method-incompatible",
                        model_fingerprint=model.model_fingerprint,
                    )
                )
            elif strategy is None:
                outcomes.append(
                    ExplanationOutcome(
                        request,
                        position,
                        status="unsupported",
                        explanation_method=None,
                        explanation=None,
                        reason_code="strategy-not-registered",
                        model_fingerprint=model.model_fingerprint,
                    )
                )
            else:
                explanation = strategy(  # type: ignore[operator]
                    model, request.observation_identifier, partition.X[matches[0]]
                )
                outcomes.append(
                    ExplanationOutcome(
                        request,
                        position,
                        status="successful",
                        explanation_method=method,
                        explanation=explanation,
                        reason_code=None,
                        model_fingerprint=model.model_fingerprint,
                    )
                )
        return tuple(outcomes)
