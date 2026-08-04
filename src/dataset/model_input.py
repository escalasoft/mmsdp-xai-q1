"""Immutable, framework-neutral model inputs for prepared datasets."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from types import MappingProxyType

from dataset.experiment_dataset import (
    ExperimentDatasetPartition,
    PreparedExperimentDataset,
)

__all__ = ["ModelPartitionInput", "PreparedModelInput", "ModelInputBuilder"]


def _invalid_name(value: object) -> bool:
    return not isinstance(value, str) or not value.strip()


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


def _freeze_mapping(value: Mapping[str, object]) -> Mapping[str, object]:
    return MappingProxyType(
        {deepcopy(key): _freeze(item) for key, item in value.items()}
    )


def _thaw(value: object) -> object:
    if isinstance(value, Mapping):
        return {deepcopy(key): _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    if isinstance(value, frozenset):
        return {_thaw(item) for item in value}
    return deepcopy(value)


def _has_duplicates(values: Sequence[object]) -> bool:
    return any(
        value == previous
        for index, value in enumerate(values)
        for previous in values[:index]
    )


@dataclass(frozen=True, slots=True, init=False)
class ModelPartitionInput:
    """One immutable partition in algorithm-neutral ``X``/``y`` form."""

    partition_name: str
    identifiers: tuple[object, ...]
    X: tuple[tuple[object, ...], ...]
    y: tuple[object, ...]
    feature_names: tuple[str, ...]
    metadata: Mapping[str, object]

    def __init__(
        self,
        partition_name: str,
        identifiers: Sequence[object],
        X: Sequence[Sequence[object]],
        y: Sequence[object],
        feature_names: Sequence[str],
        metadata: Mapping[str, object] = MappingProxyType({}),
    ) -> None:
        if _invalid_name(partition_name):
            raise ValueError("partition_name must be a non-empty string")
        if isinstance(identifiers, (str, bytes)):
            raise TypeError("partition values must be sequences")
        if isinstance(X, (str, bytes)) or isinstance(y, (str, bytes)):
            raise TypeError("partition values must be sequences")
        if isinstance(feature_names, (str, bytes)):
            raise TypeError("partition values must be sequences")
        try:
            normalized_identifiers = tuple(identifiers)
            normalized_X = tuple(tuple(row) for row in X)
            normalized_y = tuple(y)
            normalized_names = tuple(feature_names)
        except TypeError as error:
            raise TypeError("partition values must be sequences") from error
        if not normalized_identifiers:
            raise ValueError("identifiers must not be empty")
        if not normalized_X:
            raise ValueError("X must not be empty")
        if not normalized_y:
            raise ValueError("y must not be empty")
        if not normalized_names:
            raise ValueError("feature_names must not be empty")
        if _has_duplicates(normalized_identifiers):
            raise ValueError("identifiers must be unique")
        if not (len(normalized_identifiers) == len(normalized_X) == len(normalized_y)):
            raise ValueError("identifiers, X, and y must align")
        if any(len(row) != len(normalized_names) for row in normalized_X):
            raise ValueError("every X row must match feature_names")
        if any(_invalid_name(name) for name in normalized_names):
            raise ValueError("feature_names must contain non-empty strings")
        if _has_duplicates(normalized_names):
            raise ValueError("feature_names must be unique")
        if not isinstance(metadata, Mapping):
            raise TypeError("metadata must be a mapping")

        object.__setattr__(self, "partition_name", partition_name)
        object.__setattr__(self, "identifiers", tuple(_freeze(normalized_identifiers)))
        object.__setattr__(self, "X", tuple(_freeze(normalized_X)))
        object.__setattr__(self, "y", tuple(_freeze(normalized_y)))
        object.__setattr__(self, "feature_names", normalized_names)
        object.__setattr__(self, "metadata", _freeze_mapping(metadata))

    @property
    def observation_count(self) -> int:
        return len(self.identifiers)

    @property
    def feature_count(self) -> int:
        return len(self.feature_names)

    def to_dict(self) -> dict[str, object]:
        """Return a deterministic, detached standard-container representation."""
        return {
            "partition_name": self.partition_name,
            "identifiers": _thaw(self.identifiers),
            "X": _thaw(self.X),
            "y": _thaw(self.y),
            "feature_names": list(self.feature_names),
            "metadata": _thaw(self.metadata),
        }


@dataclass(frozen=True, slots=True, init=False)
class PreparedModelInput:
    """Immutable model inputs and their dataset-level descriptive metadata."""

    dataset_name: str
    dataset_version: str
    train: ModelPartitionInput
    validation: ModelPartitionInput
    test: ModelPartitionInput
    feature_names: tuple[str, ...]
    target_name: str
    metadata: Mapping[str, object]

    def __init__(
        self,
        dataset_name: str,
        dataset_version: str,
        train: ModelPartitionInput,
        validation: ModelPartitionInput,
        test: ModelPartitionInput,
        feature_names: Sequence[str],
        target_name: str,
        metadata: Mapping[str, object] = MappingProxyType({}),
    ) -> None:
        if _invalid_name(dataset_name):
            raise ValueError("dataset_name must be a non-empty string")
        if _invalid_name(dataset_version):
            raise ValueError("dataset_version must be a non-empty string")
        if _invalid_name(target_name):
            raise ValueError("target_name must be a non-empty string")
        partitions = (train, validation, test)
        if any(not isinstance(item, ModelPartitionInput) for item in partitions):
            raise TypeError("partitions must be ModelPartitionInput instances")
        if tuple(item.partition_name for item in partitions) != (
            "train",
            "validation",
            "test",
        ):
            raise ValueError("partition names must be train, validation, and test")
        if isinstance(feature_names, (str, bytes)):
            raise TypeError("feature_names must be a sequence")
        try:
            normalized_names = tuple(feature_names)
        except TypeError as error:
            raise TypeError("feature_names must be a sequence") from error
        if any(item.feature_names != train.feature_names for item in partitions):
            raise ValueError("all partitions must expose the same feature_names")
        if normalized_names != train.feature_names:
            raise ValueError("top-level feature_names must match partition schemas")
        if not isinstance(metadata, Mapping):
            raise TypeError("metadata must be a mapping")

        object.__setattr__(self, "dataset_name", dataset_name)
        object.__setattr__(self, "dataset_version", dataset_version)
        object.__setattr__(self, "train", train)
        object.__setattr__(self, "validation", validation)
        object.__setattr__(self, "test", test)
        object.__setattr__(self, "feature_names", normalized_names)
        object.__setattr__(self, "target_name", target_name)
        object.__setattr__(self, "metadata", _freeze_mapping(metadata))

    @property
    def training_observation_count(self) -> int:
        return self.train.observation_count

    @property
    def validation_observation_count(self) -> int:
        return self.validation.observation_count

    @property
    def test_observation_count(self) -> int:
        return self.test.observation_count

    @property
    def total_observation_count(self) -> int:
        return sum(
            (
                self.training_observation_count,
                self.validation_observation_count,
                self.test_observation_count,
            )
        )

    @property
    def feature_count(self) -> int:
        return len(self.feature_names)

    def to_dict(self) -> dict[str, object]:
        """Return a deterministic, detached standard-container representation."""
        return {
            "dataset_name": self.dataset_name,
            "dataset_version": self.dataset_version,
            "train": self.train.to_dict(),
            "validation": self.validation.to_dict(),
            "test": self.test.to_dict(),
            "feature_names": list(self.feature_names),
            "target_name": self.target_name,
            "metadata": _thaw(self.metadata),
        }


class ModelInputBuilder:
    """Build immutable model inputs without transforming prepared values."""

    builder_name = "model-input"

    def build(self, dataset: PreparedExperimentDataset) -> PreparedModelInput:
        """Snapshot a valid prepared dataset while preserving every ordering."""
        if not isinstance(dataset, PreparedExperimentDataset):
            raise TypeError("dataset must be a PreparedExperimentDataset")

        def build_partition(
            expected_name: str, partition: ExperimentDatasetPartition
        ) -> ModelPartitionInput:
            if not isinstance(partition, ExperimentDatasetPartition):
                raise TypeError(
                    "prepared partitions must be ExperimentDatasetPartition instances"
                )
            if partition.partition_name != expected_name:
                raise ValueError(f"expected {expected_name} partition")
            if partition.feature_names != dataset.feature_names:
                raise ValueError(
                    "partition feature_names must match the dataset schema"
                )
            return ModelPartitionInput(
                partition_name=partition.partition_name,
                identifiers=partition.identifiers,
                X=partition.features,
                y=partition.targets,
                feature_names=partition.feature_names,
                metadata=partition.metadata,
            )

        return PreparedModelInput(
            dataset_name=dataset.dataset_name,
            dataset_version=dataset.dataset_version,
            train=build_partition("train", dataset.train),
            validation=build_partition("validation", dataset.validation),
            test=build_partition("test", dataset.test),
            feature_names=dataset.feature_names,
            target_name=dataset.target_name,
            metadata=dataset.metadata,
        )
