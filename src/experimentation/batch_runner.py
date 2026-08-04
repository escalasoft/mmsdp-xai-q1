"""Deterministic sequential execution of end-to-end experiment batches."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass, field, fields
from numbers import Integral, Real
from time import perf_counter
from types import MappingProxyType

from dataset.contracts import AdaptedDataset
from experimentation.end_to_end_pipeline import (
    EndToEndExperimentConfiguration,
    EndToEndExperimentPipeline,
    EndToEndExperimentResult,
)

__all__ = [
    "BatchExperimentSpecification",
    "BatchExperimentRecord",
    "BatchExperimentResult",
    "BatchExperimentRunner",
]


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


def _thaw(value: object) -> object:
    """Return a detached snapshot made from ordinary mutable containers."""
    if isinstance(value, Mapping):
        return {deepcopy(key): _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    if isinstance(value, frozenset):
        return sorted((_thaw(item) for item in value), key=repr)
    return deepcopy(value)


def _configuration_fingerprint(
    dataset: AdaptedDataset, configuration: EndToEndExperimentConfiguration
) -> str:
    """Produce the fingerprint defined by the end-to-end pipeline contract."""
    return EndToEndExperimentPipeline.experiment_fingerprint(dataset, configuration)


@dataclass(frozen=True, slots=True, init=False)
class BatchExperimentSpecification:
    """Immutable ordered specification for a reproducible experiment batch."""

    experiment_name: str
    dataset: AdaptedDataset
    configurations: tuple[EndToEndExperimentConfiguration, ...]
    metadata: Mapping[str, object]
    configuration_fingerprints: tuple[str, ...]

    def __init__(
        self,
        experiment_name: str,
        dataset: AdaptedDataset,
        configurations: Sequence[EndToEndExperimentConfiguration],
        metadata: Mapping[str, object] = MappingProxyType({}),
    ) -> None:
        if not isinstance(experiment_name, str) or not experiment_name.strip():
            raise ValueError("experiment_name must be a non-empty string")
        if not isinstance(dataset, AdaptedDataset):
            raise TypeError("dataset must be an AdaptedDataset")
        if isinstance(configurations, (str, bytes)) or not isinstance(
            configurations, Sequence
        ):
            raise TypeError("configurations must be an ordered sequence")
        normalized = tuple(configurations)
        if not normalized:
            raise ValueError("configurations must not be empty")
        if any(
            not isinstance(item, EndToEndExperimentConfiguration) for item in normalized
        ):
            raise TypeError(
                "configurations must contain EndToEndExperimentConfiguration values"
            )
        if not isinstance(metadata, Mapping):
            raise TypeError("metadata must be a mapping")
        fingerprints = tuple(
            _configuration_fingerprint(dataset, configuration)
            for configuration in normalized
        )
        if len(set(fingerprints)) != len(fingerprints):
            raise ValueError("configurations contain duplicate experiment fingerprints")

        object.__setattr__(self, "experiment_name", experiment_name)
        object.__setattr__(self, "dataset", dataset)
        object.__setattr__(self, "configurations", normalized)
        object.__setattr__(self, "metadata", _freeze(metadata))
        object.__setattr__(self, "configuration_fingerprints", fingerprints)

    def to_dict(self) -> dict[str, object]:
        """Return a deterministic detached representation."""
        return {
            "experiment_name": self.experiment_name,
            "dataset": self.dataset.to_dict(),
            "configurations": [item.to_dict() for item in self.configurations],
            "metadata": _thaw(self.metadata),
            "configuration_fingerprints": list(self.configuration_fingerprints),
        }


@dataclass(frozen=True, slots=True)
class BatchExperimentRecord:
    """One immutable flattened scientific record for an executed configuration."""

    experiment_name: str
    execution_index: int
    experiment_fingerprint: str
    dataset_name: str
    dataset_version: str
    model_name: str
    model_family: str
    calibration_method: str
    training_observation_count: int
    validation_observation_count: int
    test_observation_count: int
    validation_positive_count: int
    test_positive_count: int
    uncalibrated_validation_positive_rate: float
    uncalibrated_test_positive_rate: float
    uncalibrated_validation_accuracy: float
    uncalibrated_validation_precision: float
    uncalibrated_validation_recall: float
    uncalibrated_validation_f1: float
    uncalibrated_validation_mcc: float
    uncalibrated_validation_roc_auc: float
    uncalibrated_validation_pr_auc: float
    uncalibrated_validation_brier_score: float
    calibrated_validation_brier_score: float
    uncalibrated_test_accuracy: float
    uncalibrated_test_precision: float
    uncalibrated_test_recall: float
    uncalibrated_test_f1: float
    uncalibrated_test_mcc: float
    uncalibrated_test_roc_auc: float
    uncalibrated_test_pr_auc: float
    uncalibrated_test_brier_score: float
    calibrated_test_brier_score: float
    global_explanation_supported: bool
    requested_local_explanation_count: int
    successful_local_explanation_count: int
    unsupported_local_explanation_count: int
    requested_counterfactual_count: int
    successful_counterfactual_count: int
    unsupported_counterfactual_count: int
    model_training_execution_count: int
    shared_trained_model_instance: bool
    execution_duration_seconds: float = field(compare=False)
    metadata: Mapping[str, object]

    def __post_init__(self) -> None:
        for name in (
            "experiment_name",
            "experiment_fingerprint",
            "dataset_name",
            "dataset_version",
            "model_name",
            "model_family",
            "calibration_method",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")

        count_names = (
            "execution_index",
            "training_observation_count",
            "validation_observation_count",
            "test_observation_count",
            "validation_positive_count",
            "test_positive_count",
            "requested_local_explanation_count",
            "successful_local_explanation_count",
            "unsupported_local_explanation_count",
            "requested_counterfactual_count",
            "successful_counterfactual_count",
            "unsupported_counterfactual_count",
            "model_training_execution_count",
        )
        for name in count_names:
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, Integral):
                raise TypeError(f"{name} must be an integer and must not be bool")
            if value < 0:
                raise ValueError(f"{name} must be non-negative")
            object.__setattr__(self, name, int(value))

        for partition in ("validation", "test"):
            if getattr(self, f"{partition}_positive_count") > getattr(
                self, f"{partition}_observation_count"
            ):
                raise ValueError(
                    f"{partition}_positive_count must not exceed observation count"
                )
        for explanation in ("local_explanation", "counterfactual"):
            requested = getattr(self, f"requested_{explanation}_count")
            successful = getattr(self, f"successful_{explanation}_count")
            unsupported = getattr(self, f"unsupported_{explanation}_count")
            if requested != successful + unsupported:
                raise ValueError(
                    f"requested_{explanation}_count must equal successful + unsupported"
                )

        bounded_metrics = (
            "uncalibrated_validation_positive_rate",
            "uncalibrated_test_positive_rate",
            "uncalibrated_validation_accuracy",
            "uncalibrated_validation_precision",
            "uncalibrated_validation_recall",
            "uncalibrated_validation_f1",
            "uncalibrated_validation_roc_auc",
            "uncalibrated_validation_pr_auc",
            "uncalibrated_validation_brier_score",
            "calibrated_validation_brier_score",
            "uncalibrated_test_accuracy",
            "uncalibrated_test_precision",
            "uncalibrated_test_recall",
            "uncalibrated_test_f1",
            "uncalibrated_test_roc_auc",
            "uncalibrated_test_pr_auc",
            "uncalibrated_test_brier_score",
            "calibrated_test_brier_score",
        )
        for name in bounded_metrics:
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, Real):
                raise TypeError(f"{name} must be numeric and must not be bool")
            normalized = float(value)
            if not math.isfinite(normalized) or not 0.0 <= normalized <= 1.0:
                raise ValueError(f"{name} must be finite and in [0, 1]")
            object.__setattr__(self, name, normalized)
        for name in ("uncalibrated_validation_mcc", "uncalibrated_test_mcc"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, Real):
                raise TypeError(f"{name} must be numeric and must not be bool")
            normalized = float(value)
            if not math.isfinite(normalized) or not -1.0 <= normalized <= 1.0:
                raise ValueError(f"{name} must be finite and in [-1, 1]")
            object.__setattr__(self, name, normalized)

        duration = self.execution_duration_seconds
        if isinstance(duration, bool) or not isinstance(duration, Real):
            raise TypeError(
                "execution_duration_seconds must be numeric and must not be bool"
            )
        normalized_duration = float(duration)
        if not math.isfinite(normalized_duration) or normalized_duration < 0.0:
            raise ValueError(
                "execution_duration_seconds must be finite and non-negative"
            )
        object.__setattr__(self, "execution_duration_seconds", normalized_duration)
        if self.model_training_execution_count != 1:
            raise ValueError("model_training_execution_count must equal one")
        if self.shared_trained_model_instance is not True:
            raise ValueError("shared_trained_model_instance must be true")
        if not isinstance(self.global_explanation_supported, bool):
            raise TypeError("global_explanation_supported must be a boolean")
        if not isinstance(self.metadata, Mapping):
            raise TypeError("metadata must be a mapping")
        object.__setattr__(self, "metadata", _freeze(self.metadata))

    def to_dict(self, *, include_runtime: bool = False) -> dict[str, object]:
        """Return a detached row, excluding environment-dependent runtime by default."""
        if not isinstance(include_runtime, bool):
            raise TypeError("include_runtime must be a boolean")
        result = {
            item.name: getattr(self, item.name)
            for item in fields(self)
            if item.name != "metadata"
            and (include_runtime or item.name != "execution_duration_seconds")
        }
        result["metadata"] = _thaw(self.metadata)
        return result


@dataclass(frozen=True, slots=True, init=False)
class BatchExperimentResult:
    """Immutable aggregate returned after sequential batch execution."""

    experiment_name: str
    records: tuple[BatchExperimentRecord, ...]
    execution_count: int
    successful_execution_count: int
    failed_execution_count: int
    failures: tuple[object, ...]
    metadata: Mapping[str, object]

    def __init__(
        self,
        *,
        experiment_name: str,
        records: Sequence[BatchExperimentRecord],
        execution_count: int,
        metadata: Mapping[str, object],
        successful_execution_count: int | None = None,
        failed_execution_count: int = 0,
        failures: Sequence[object] = (),
    ) -> None:
        if not isinstance(experiment_name, str) or not experiment_name.strip():
            raise ValueError("experiment_name must be a non-empty string")
        if not isinstance(metadata, Mapping):
            raise TypeError("metadata must be a mapping")
        normalized = tuple(records)
        if any(not isinstance(item, BatchExperimentRecord) for item in normalized):
            raise TypeError("records must contain BatchExperimentRecord values")
        if isinstance(execution_count, bool) or not isinstance(
            execution_count, Integral
        ):
            raise TypeError("execution_count must be an integer and must not be bool")
        if execution_count != len(normalized):
            raise ValueError("execution_count must equal the record count")
        successful = (
            len(normalized)
            if successful_execution_count is None
            else successful_execution_count
        )
        for name, value in (
            ("successful_execution_count", successful),
            ("failed_execution_count", failed_execution_count),
        ):
            if isinstance(value, bool) or not isinstance(value, Integral):
                raise TypeError(f"{name} must be an integer and must not be bool")
            if value < 0:
                raise ValueError(f"{name} must be non-negative")
        if successful != len(normalized):
            raise ValueError("successful_execution_count must equal the record count")
        normalized_failures = tuple(failures)
        if failed_execution_count != 0 or normalized_failures:
            raise ValueError("fail-fast results must have zero failures")
        if any(item.experiment_name != experiment_name for item in normalized):
            raise ValueError("all records must belong to experiment_name")
        if tuple(item.execution_index for item in normalized) != tuple(
            range(len(normalized))
        ):
            raise ValueError("record execution indexes must be exactly 0..n-1 in order")
        fingerprints = tuple(item.experiment_fingerprint for item in normalized)
        if len(set(fingerprints)) != len(fingerprints):
            raise ValueError("record experiment fingerprints must be unique")
        object.__setattr__(self, "experiment_name", experiment_name)
        object.__setattr__(self, "records", normalized)
        object.__setattr__(self, "execution_count", execution_count)
        object.__setattr__(self, "successful_execution_count", int(successful))
        object.__setattr__(self, "failed_execution_count", int(failed_execution_count))
        object.__setattr__(self, "failures", normalized_failures)
        object.__setattr__(self, "metadata", _freeze(metadata))

    def to_dict(self, *, include_runtime: bool = False) -> dict[str, object]:
        """Return an aggregate excluding environment-dependent runtime by default."""
        if not isinstance(include_runtime, bool):
            raise TypeError("include_runtime must be a boolean")
        return {
            "experiment_name": self.experiment_name,
            "records": [
                record.to_dict(include_runtime=include_runtime)
                for record in self.records
            ],
            "execution_count": self.execution_count,
            "successful_execution_count": self.successful_execution_count,
            "failed_execution_count": self.failed_execution_count,
            "failures": [],
            "metadata": _thaw(self.metadata),
        }

    def to_rows(self, *, include_runtime: bool = False) -> list[dict[str, object]]:
        """Return detached ordinary dictionaries in execution order."""
        if not isinstance(include_runtime, bool):
            raise TypeError("include_runtime must be a boolean")
        return [
            record.to_dict(include_runtime=include_runtime) for record in self.records
        ]


class BatchExperimentRunner:
    """Run end-to-end experiment configurations once each and in order."""

    runner_name = "batch-experiment-runner"

    def run(self, specification: BatchExperimentSpecification) -> BatchExperimentResult:
        """Execute a validated specification sequentially with fail-fast behavior."""
        if not isinstance(specification, BatchExperimentSpecification):
            raise TypeError("specification must be a BatchExperimentSpecification")

        records = []
        for execution_index, (configuration, expected_fingerprint) in enumerate(
            zip(
                specification.configurations,
                specification.configuration_fingerprints,
                strict=True,
            )
        ):
            started = perf_counter()
            result = EndToEndExperimentPipeline(configuration).run(
                specification.dataset
            )
            duration = perf_counter() - started
            self._validate_result(result, expected_fingerprint)
            records.append(
                self._record(
                    specification.experiment_name,
                    execution_index,
                    result,
                    duration,
                )
            )

        return BatchExperimentResult(
            experiment_name=specification.experiment_name,
            records=records,
            execution_count=len(records),
            metadata=specification.metadata,
        )

    @staticmethod
    def _validate_result(
        result: EndToEndExperimentResult, expected_fingerprint: str
    ) -> None:
        if not isinstance(result, EndToEndExperimentResult):
            raise TypeError("pipeline must return an EndToEndExperimentResult")
        if result.experiment_fingerprint != expected_fingerprint:
            raise ValueError(
                "configuration fingerprint does not match pipeline result fingerprint"
            )
        if result.metadata.get("model_training_execution_count") != 1:
            raise ValueError("each experiment must execute model training exactly once")
        if result.metadata.get("shared_trained_model_instance") is not True:
            raise ValueError("each experiment must share its trained model instance")

    @staticmethod
    def _record(
        experiment_name: str,
        execution_index: int,
        result: EndToEndExperimentResult,
        duration: float,
    ) -> BatchExperimentRecord:
        uncalibrated = result.model_experiment_result
        calibrated = result.calibrated_experiment_result
        validation = uncalibrated.validation_evaluation
        test = uncalibrated.test_evaluation
        calibrated_validation = calibrated.calibrated_validation_calibration
        calibrated_test = calibrated.calibrated_test_calibration
        trained = result.trained_model

        return BatchExperimentRecord(
            experiment_name=experiment_name,
            execution_index=execution_index,
            experiment_fingerprint=result.experiment_fingerprint,
            dataset_name=result.dataset_name,
            dataset_version=result.dataset_version,
            model_name=result.model_name,
            model_family=trained.model_family,
            calibration_method=calibrated.calibration_method,
            training_observation_count=trained.training_observation_count,
            validation_observation_count=validation.observation_count,
            test_observation_count=test.observation_count,
            validation_positive_count=validation.positive_count,
            test_positive_count=test.positive_count,
            uncalibrated_validation_positive_rate=validation.positive_rate,
            uncalibrated_test_positive_rate=test.positive_rate,
            uncalibrated_validation_accuracy=validation.accuracy,
            uncalibrated_validation_precision=validation.precision,
            uncalibrated_validation_recall=validation.recall,
            uncalibrated_validation_f1=validation.f1,
            uncalibrated_validation_mcc=validation.mcc,
            uncalibrated_validation_roc_auc=validation.roc_auc,
            uncalibrated_validation_pr_auc=validation.pr_auc,
            uncalibrated_validation_brier_score=(
                calibrated.uncalibrated_validation_calibration.brier_score
            ),
            calibrated_validation_brier_score=calibrated_validation.brier_score,
            uncalibrated_test_accuracy=test.accuracy,
            uncalibrated_test_precision=test.precision,
            uncalibrated_test_recall=test.recall,
            uncalibrated_test_f1=test.f1,
            uncalibrated_test_mcc=test.mcc,
            uncalibrated_test_roc_auc=test.roc_auc,
            uncalibrated_test_pr_auc=test.pr_auc,
            uncalibrated_test_brier_score=(
                calibrated.uncalibrated_test_calibration.brier_score
            ),
            calibrated_test_brier_score=calibrated_test.brier_score,
            global_explanation_supported=trained.capabilities.global_explanation,
            requested_local_explanation_count=len(result.local_explanation_requests),
            successful_local_explanation_count=len(result.local_explanations),
            unsupported_local_explanation_count=len(result.unsupported_local_requests),
            requested_counterfactual_count=len(result.counterfactual_requests),
            successful_counterfactual_count=len(result.counterfactual_explanations),
            unsupported_counterfactual_count=len(
                result.unsupported_counterfactual_requests
            ),
            model_training_execution_count=int(
                result.metadata["model_training_execution_count"]
            ),
            shared_trained_model_instance=bool(
                result.metadata["shared_trained_model_instance"]
            ),
            execution_duration_seconds=duration,
            metadata=result.metadata,
        )
