"""Deterministic orchestration of global and supported local explanations."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from types import MappingProxyType

from dataset.model_input import ModelPartitionInput, PreparedModelInput
from explainability.global_importance import (
    GlobalFeatureImportanceExplainer,
    GlobalFeatureImportanceResult,
)
from explainability.local_importance import (
    LocalFeatureImportanceExplainer,
    LocalFeatureImportanceResult,
)
from models.logistic_regression_adapter import PreparedLogisticRegressionModel
from models.random_forest_adapter import PreparedRandomForestModel

__all__ = [
    "ObservationExplanationRequest",
    "ModelExplanationResult",
    "ModelExplanationRunner",
]

_MODEL_NAMES = frozenset({"logistic-regression", "random-forest"})
_PARTITION_NAMES = frozenset({"train", "validation", "test"})


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
    """Return a detached representation containing ordinary containers."""
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


def _structurally_equal(left: object, right: object) -> bool:
    """Compare recursively frozen values without requiring hashability."""
    return bool(left == right)


def _has_duplicates(values: Sequence[object]) -> bool:
    return any(
        _structurally_equal(value, previous)
        for index, value in enumerate(values)
        for previous in values[:index]
    )


def _same_request(
    left: ObservationExplanationRequest, right: ObservationExplanationRequest
) -> bool:
    return left.partition_name == right.partition_name and _structurally_equal(
        left.observation_identifier, right.observation_identifier
    )


def _request_duplicates(requests: Sequence[ObservationExplanationRequest]) -> bool:
    return any(
        _same_request(request, previous)
        for index, request in enumerate(requests)
        for previous in requests[:index]
    )


def _has_ambiguous_identifiers(
    requests: Sequence[ObservationExplanationRequest],
) -> bool:
    """Enforce traceability until local results retain partition identity."""
    return _has_duplicates(
        tuple(request.observation_identifier for request in requests)
    )


def _validate_request_traceability(
    requests: Sequence[ObservationExplanationRequest],
) -> None:
    if _has_ambiguous_identifiers(requests):
        raise ValueError(
            "requested observation identifiers must be globally unique because "
            "local explanation results do not currently retain partition_name"
        )


@dataclass(frozen=True, slots=True, init=False)
class ObservationExplanationRequest:
    """Immutable identification of one prepared observation to explain."""

    partition_name: str
    observation_identifier: object

    def __init__(self, partition_name: str, observation_identifier: object) -> None:
        if partition_name not in _PARTITION_NAMES:
            raise ValueError(
                f"partition_name must be one of {sorted(_PARTITION_NAMES)}"
            )
        if observation_identifier is None:
            raise ValueError("observation_identifier must not be None")
        object.__setattr__(self, "partition_name", deepcopy(partition_name))
        object.__setattr__(
            self, "observation_identifier", _freeze(observation_identifier)
        )

    def to_dict(self) -> dict[str, object]:
        """Return a deterministic, detached standard-container representation."""
        return {
            "partition_name": self.partition_name,
            "observation_identifier": _thaw(self.observation_identifier),
        }


@dataclass(frozen=True, slots=True, init=False)
class ModelExplanationResult:
    """Immutable aggregate of one global and supported local explanations."""

    dataset_name: str
    dataset_version: str
    model_name: str
    target_name: str
    class_labels: tuple[object, ...]
    feature_names: tuple[str, ...]
    global_explanation: GlobalFeatureImportanceResult
    local_explanations: tuple[LocalFeatureImportanceResult, ...]
    requested_observations: tuple[ObservationExplanationRequest, ...]
    unsupported_local_requests: tuple[ObservationExplanationRequest, ...]
    metadata: Mapping[str, object]

    def __init__(
        self,
        dataset_name: str,
        dataset_version: str,
        model_name: str,
        target_name: str,
        class_labels: Sequence[object],
        feature_names: Sequence[str],
        global_explanation: GlobalFeatureImportanceResult,
        local_explanations: Sequence[LocalFeatureImportanceResult] = (),
        requested_observations: Sequence[ObservationExplanationRequest] = (),
        unsupported_local_requests: Sequence[ObservationExplanationRequest] = (),
        metadata: Mapping[str, object] = MappingProxyType({}),
    ) -> None:
        strings = {
            "dataset_name": _non_empty_string("dataset_name", dataset_name),
            "dataset_version": _non_empty_string("dataset_version", dataset_version),
            "model_name": _non_empty_string("model_name", model_name),
            "target_name": _non_empty_string("target_name", target_name),
        }
        if model_name not in _MODEL_NAMES:
            raise ValueError(f"model_name must be one of {sorted(_MODEL_NAMES)}")
        for name, values in (
            ("class_labels", class_labels),
            ("feature_names", feature_names),
            ("local_explanations", local_explanations),
            ("requested_observations", requested_observations),
            ("unsupported_local_requests", unsupported_local_requests),
        ):
            if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
                raise TypeError(f"{name} must be a sequence")

        labels = tuple(_freeze(tuple(class_labels)))
        features = tuple(feature_names)
        local = tuple(local_explanations)
        requested = tuple(requested_observations)
        unsupported = tuple(unsupported_local_requests)
        if len(labels) != 2 or _has_duplicates(labels):
            raise ValueError("class_labels must contain exactly two distinct labels")
        if not features:
            raise ValueError("feature_names must not be empty")
        if any(not isinstance(item, str) or not item.strip() for item in features):
            raise ValueError("feature_names must contain non-empty strings")
        if _has_duplicates(features):
            raise ValueError("feature_names must be unique")
        if not isinstance(global_explanation, GlobalFeatureImportanceResult):
            raise TypeError(
                "global_explanation must be a GlobalFeatureImportanceResult"
            )
        if any(not isinstance(item, LocalFeatureImportanceResult) for item in local):
            raise TypeError(
                "local_explanations must contain LocalFeatureImportanceResult values"
            )
        if any(
            not isinstance(item, ObservationExplanationRequest) for item in requested
        ):
            raise TypeError(
                "requested_observations must contain "
                "ObservationExplanationRequest values"
            )
        if any(
            not isinstance(item, ObservationExplanationRequest) for item in unsupported
        ):
            raise TypeError(
                "unsupported_local_requests must contain "
                "ObservationExplanationRequest values"
            )
        if _request_duplicates(requested):
            raise ValueError("requested observations must be structurally unique")
        _validate_request_traceability(requested)

        unsupported_positions: list[int] = []
        for item in unsupported:
            positions = [
                index
                for index, request in enumerate(requested)
                if _same_request(item, request)
            ]
            if len(positions) != 1:
                raise ValueError(
                    "unsupported local requests must be contained in "
                    "requested observations"
                )
            unsupported_positions.append(positions[0])
        if unsupported_positions != sorted(unsupported_positions) or len(
            unsupported_positions
        ) != len(set(unsupported_positions)):
            raise ValueError(
                "unsupported local requests must be an ordered subset of requests"
            )

        successful_positions: list[int] = []
        for explanation in local:
            positions = [
                index
                for index, request in enumerate(requested)
                if _structurally_equal(
                    explanation.observation_identifier,
                    request.observation_identifier,
                )
            ]
            if len(positions) != 1:
                raise ValueError(
                    "every local explanation must match exactly one "
                    "requested observation"
                )
            successful_positions.append(positions[0])
        if successful_positions != sorted(successful_positions) or len(
            successful_positions
        ) != len(set(successful_positions)):
            raise ValueError("local explanations must preserve requested order")
        if set(successful_positions) & set(unsupported_positions):
            raise ValueError(
                "a request cannot be both successfully and unsupported locally"
            )

        expected = (
            dataset_name,
            dataset_version,
            model_name,
            target_name,
            labels,
            features,
        )
        global_actual = (
            global_explanation.dataset_name,
            global_explanation.dataset_version,
            global_explanation.model_name,
            global_explanation.target_name,
            global_explanation.class_labels,
            global_explanation.feature_names,
        )
        if global_actual != expected:
            raise ValueError("global explanation does not match result identity")
        for explanation in local:
            actual = (
                explanation.dataset_name,
                explanation.dataset_version,
                explanation.model_name,
                explanation.target_name,
                explanation.class_labels,
                explanation.feature_names,
            )
            if actual != expected:
                raise ValueError("local explanation does not match result identity")

        all_positions = set(range(len(requested)))
        if model_name == "logistic-regression":
            if unsupported:
                raise ValueError(
                    "logistic-regression does not allow unsupported local requests"
                )
            if set(successful_positions) != all_positions:
                raise ValueError(
                    "every logistic-regression request requires a local explanation"
                )
        else:
            if local:
                raise ValueError("random-forest does not support local explanations")
            if set(unsupported_positions) != all_positions:
                raise ValueError(
                    "every random-forest request must be recorded as unsupported"
                )

        for name, value in strings.items():
            object.__setattr__(self, name, value)
        object.__setattr__(self, "class_labels", labels)
        object.__setattr__(self, "feature_names", tuple(deepcopy(features)))
        object.__setattr__(self, "global_explanation", global_explanation)
        object.__setattr__(self, "local_explanations", local)
        object.__setattr__(self, "requested_observations", requested)
        object.__setattr__(self, "unsupported_local_requests", unsupported)
        object.__setattr__(self, "metadata", _freeze_mapping(metadata))

    @property
    def requested_observation_count(self) -> int:
        return len(self.requested_observations)

    @property
    def local_explanation_count(self) -> int:
        return len(self.local_explanations)

    @property
    def unsupported_local_request_count(self) -> int:
        return len(self.unsupported_local_requests)

    def to_dict(self) -> dict[str, object]:
        """Return a deterministic, detached standard-container representation."""
        return {
            "dataset_name": deepcopy(self.dataset_name),
            "dataset_version": deepcopy(self.dataset_version),
            "model_name": self.model_name,
            "target_name": deepcopy(self.target_name),
            "class_labels": _thaw(self.class_labels),
            "feature_names": list(deepcopy(self.feature_names)),
            "global_explanation": self.global_explanation.to_dict(),
            "local_explanations": [item.to_dict() for item in self.local_explanations],
            "requested_observations": [
                item.to_dict() for item in self.requested_observations
            ],
            "unsupported_local_requests": [
                item.to_dict() for item in self.unsupported_local_requests
            ],
            "metadata": _thaw(self.metadata),
        }


class ModelExplanationRunner:
    """Combine model-native global and supported local explanations."""

    runner_name = "model-explanation-runner"

    def run(
        self,
        model: PreparedLogisticRegressionModel | PreparedRandomForestModel,
        prepared_input: PreparedModelInput,
        requests: Sequence[ObservationExplanationRequest] = (),
    ) -> ModelExplanationResult:
        """Run deterministic explanation orchestration without model inference."""
        if not isinstance(
            model, (PreparedLogisticRegressionModel, PreparedRandomForestModel)
        ):
            raise TypeError("model must be a supported prepared model snapshot")
        if not isinstance(prepared_input, PreparedModelInput):
            raise TypeError("prepared_input must be a PreparedModelInput")
        if isinstance(requests, (str, bytes)) or not isinstance(requests, Sequence):
            raise TypeError("requests must be a sequence")
        normalized_requests = tuple(requests)
        if any(
            not isinstance(item, ObservationExplanationRequest)
            for item in normalized_requests
        ):
            raise TypeError(
                "requests must contain ObservationExplanationRequest values"
            )
        if _request_duplicates(normalized_requests):
            raise ValueError("requests must be structurally unique")
        _validate_request_traceability(normalized_requests)

        for name in ("dataset_name", "dataset_version", "target_name", "feature_names"):
            if getattr(model, name) != getattr(prepared_input, name):
                raise ValueError(f"model and prepared_input {name} must match")
        if len(model.class_labels) != 2 or _has_duplicates(model.class_labels):
            raise ValueError("model class_labels must represent binary classification")

        aligned_rows: list[tuple[object, ...]] = []
        for request in normalized_requests:
            partition = getattr(prepared_input, request.partition_name)
            aligned_rows.append(self._resolve_row(partition, request))

        global_explanation = GlobalFeatureImportanceExplainer().explain(model)
        if isinstance(model, PreparedLogisticRegressionModel):
            local_explainer = LocalFeatureImportanceExplainer()
            local = tuple(
                local_explainer.explain(
                    model, request.observation_identifier, feature_values
                )
                for request, feature_values in zip(
                    normalized_requests, aligned_rows, strict=True
                )
            )
            unsupported: tuple[ObservationExplanationRequest, ...] = ()
            model_name = "logistic-regression"
        else:
            local = ()
            unsupported = normalized_requests
            model_name = "random-forest"

        runner_metadata = {
            "name": self.runner_name,
            "requested_observation_count": len(normalized_requests),
            "local_explanation_count": len(local),
            "unsupported_local_request_count": len(unsupported),
        }
        metadata = _thaw(prepared_input.metadata)
        metadata[self._metadata_key(metadata)] = runner_metadata
        return ModelExplanationResult(
            dataset_name=prepared_input.dataset_name,
            dataset_version=prepared_input.dataset_version,
            model_name=model_name,
            target_name=prepared_input.target_name,
            class_labels=model.class_labels,
            feature_names=prepared_input.feature_names,
            global_explanation=global_explanation,
            local_explanations=local,
            requested_observations=normalized_requests,
            unsupported_local_requests=unsupported,
            metadata=metadata,
        )

    @staticmethod
    def _resolve_row(
        partition: ModelPartitionInput, request: ObservationExplanationRequest
    ) -> tuple[object, ...]:
        positions = [
            index
            for index, identifier in enumerate(partition.identifiers)
            if _structurally_equal(identifier, request.observation_identifier)
        ]
        if len(positions) != 1:
            raise ValueError(
                "requested identifier must exist exactly once in its declared partition"
            )
        return partition.X[positions[0]]

    @staticmethod
    def _metadata_key(metadata: Mapping[str, object]) -> str:
        if "runner" not in metadata:
            return "runner"
        if "explanation_runner" not in metadata:
            return "explanation_runner"
        suffix = 2
        while f"explanation_runner_{suffix}" in metadata:
            suffix += 1
        return f"explanation_runner_{suffix}"
