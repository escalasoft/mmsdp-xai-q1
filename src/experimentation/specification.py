"""Immutable specification for one reproducible experiment execution."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from numbers import Real
from types import MappingProxyType

__all__ = ["ExperimentSpecification"]


@dataclass(frozen=True, slots=True, init=False)
class ExperimentSpecification:
    """Framework-neutral configuration identifying one experiment execution.

    All provenance-sensitive values are supplied explicitly by the caller. The
    specification does not generate identifiers, inspect source control, access
    datasets, execute models, or write experiment artifacts.

    Attributes:
        experiment_id: Caller-supplied identifier for the experiment execution.
        dataset_name: Stable human-readable dataset name.
        dataset_version: Caller-supplied dataset version identifier.
        random_seed: Integer seed governing reproducible stochastic operations.
        modalities: Modalities in their required processing order.
        algorithm: Framework-independent algorithm identifier.
        fusion_strategy: Framework-independent fusion strategy identifier.
        class_labels: Labels in the required prediction-output order.
        model_configuration: Read-only snapshot of model configuration values.
        split_configuration: Read-only snapshot of dataset split configuration.
        classification_threshold: Inclusive decision threshold from zero to one.
        output_directory: Caller-supplied destination for experiment outputs.
        code_version: Caller-supplied code version identifier.
        notes: Optional descriptive notes about the experiment execution.
    """

    experiment_id: str
    dataset_name: str
    dataset_version: str
    random_seed: int
    modalities: tuple[str, ...]
    algorithm: str
    fusion_strategy: str
    class_labels: tuple[object, ...]
    model_configuration: Mapping[str, object] = field(default_factory=dict)
    split_configuration: Mapping[str, object] = field(default_factory=dict)
    classification_threshold: float
    output_directory: str
    code_version: str
    notes: str | None

    def __init__(
        self,
        experiment_id: str,
        dataset_name: str,
        dataset_version: str,
        random_seed: int,
        modalities: Sequence[str],
        algorithm: str,
        fusion_strategy: str,
        class_labels: Sequence[object],
        classification_threshold: float,
        output_directory: str,
        code_version: str,
        notes: str | None = None,
        *,
        model_configuration: Mapping[str, object] | None = None,
        split_configuration: Mapping[str, object] | None = None,
    ) -> None:
        """Initialize and validate an immutable experiment specification.

        Args:
            experiment_id: Caller-supplied experiment execution identifier.
            dataset_name: Stable human-readable dataset name.
            dataset_version: Caller-supplied dataset version identifier.
            random_seed: Integer seed for reproducible stochastic operations.
            modalities: Ordered sequence of modality identifiers.
            algorithm: Framework-independent algorithm identifier.
            fusion_strategy: Framework-independent fusion strategy identifier.
            class_labels: Ordered sequence of prediction class labels.
            classification_threshold: Inclusive threshold from zero to one.
            output_directory: Caller-supplied experiment output destination.
            code_version: Caller-supplied code version identifier.
            notes: Optional descriptive experiment notes.
            model_configuration: Optional declarative model configuration.
            split_configuration: Optional declarative split configuration.

        Raises:
            TypeError: If the random seed or classification threshold has an
                invalid type.
            ValueError: If a required value is empty, an ordered sequence
                contains duplicates, or the threshold is outside its range.
        """
        normalized_modalities = tuple(modalities)
        normalized_labels = tuple(class_labels)

        if not experiment_id:
            raise ValueError("experiment_id must not be empty")
        if not dataset_name:
            raise ValueError("dataset_name must not be empty")
        if not dataset_version:
            raise ValueError("dataset_version must not be empty")
        if isinstance(random_seed, bool) or not isinstance(random_seed, int):
            raise TypeError("random_seed must be an integer and must not be bool")
        if not normalized_modalities:
            raise ValueError("modalities must not be empty")
        if len(set(normalized_modalities)) != len(normalized_modalities):
            raise ValueError("modalities must not contain duplicates")
        if not algorithm:
            raise ValueError("algorithm must not be empty")
        if not fusion_strategy:
            raise ValueError("fusion_strategy must not be empty")
        if not normalized_labels:
            raise ValueError("class_labels must not be empty")
        if any(
            label == previous
            for index, label in enumerate(normalized_labels)
            for previous in normalized_labels[:index]
        ):
            raise ValueError("class_labels must not contain duplicates")
        if isinstance(classification_threshold, bool) or not isinstance(
            classification_threshold, Real
        ):
            raise TypeError(
                "classification_threshold must be numeric and must not be bool"
            )
        if not 0.0 <= classification_threshold <= 1.0:
            raise ValueError("classification_threshold must be in the range [0.0, 1.0]")
        if not output_directory:
            raise ValueError("output_directory must not be empty")
        if not code_version:
            raise ValueError("code_version must not be empty")

        object.__setattr__(self, "experiment_id", experiment_id)
        object.__setattr__(self, "dataset_name", dataset_name)
        object.__setattr__(self, "dataset_version", dataset_version)
        object.__setattr__(self, "random_seed", random_seed)
        object.__setattr__(self, "modalities", normalized_modalities)
        object.__setattr__(self, "algorithm", algorithm)
        object.__setattr__(self, "fusion_strategy", fusion_strategy)
        object.__setattr__(self, "class_labels", normalized_labels)
        object.__setattr__(
            self,
            "model_configuration",
            MappingProxyType(
                dict({} if model_configuration is None else model_configuration)
            ),
        )
        object.__setattr__(
            self,
            "split_configuration",
            MappingProxyType(
                dict({} if split_configuration is None else split_configuration)
            ),
        )
        object.__setattr__(
            self, "classification_threshold", float(classification_threshold)
        )
        object.__setattr__(self, "output_directory", output_directory)
        object.__setattr__(self, "code_version", code_version)
        object.__setattr__(self, "notes", notes)

    def to_dict(self) -> dict[str, object]:
        """Return an independent standard-structure representation.

        Returns:
            A deterministic dictionary containing every specification field.
            Ordered sequences are represented as lists and read-only mapping
            snapshots are copied into normal dictionaries.
        """
        return {
            "experiment_id": self.experiment_id,
            "dataset_name": self.dataset_name,
            "dataset_version": self.dataset_version,
            "random_seed": self.random_seed,
            "modalities": list(self.modalities),
            "algorithm": self.algorithm,
            "fusion_strategy": self.fusion_strategy,
            "class_labels": list(self.class_labels),
            "model_configuration": dict(self.model_configuration),
            "split_configuration": dict(self.split_configuration),
            "classification_threshold": self.classification_threshold,
            "output_directory": self.output_directory,
            "code_version": self.code_version,
            "notes": self.notes,
        }
