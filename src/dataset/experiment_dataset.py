"""Deterministic, immutable model-ready experiment dataset contracts.

This module converts chronological dataset splits into framework-neutral rows.
It performs no preprocessing, persistence, randomization, or model training.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from types import MappingProxyType

from dataset.contracts import DatasetRecord
from dataset.temporal_splitter import TemporalDatasetSplit

__all__ = [
    "ExperimentDatasetPartition",
    "PreparedExperimentDataset",
    "ExperimentDatasetPreparer",
]


def _invalid_name(value: object) -> bool:
    """Return whether *value* is not a non-empty string."""
    return not isinstance(value, str) or not value.strip()


def _freeze(value: object) -> object:
    """Return a detached snapshot whose standard containers are immutable."""
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
    """Return a detached read-only mapping snapshot."""
    return MappingProxyType(
        {deepcopy(key): _freeze(item) for key, item in value.items()}
    )


def _thaw(value: object) -> object:
    """Return a detached representation using standard mutable containers."""
    if isinstance(value, Mapping):
        return {deepcopy(key): _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    if isinstance(value, frozenset):
        return {_thaw(item) for item in value}
    return deepcopy(value)


def _has_duplicates(values: Sequence[object]) -> bool:
    """Return whether an ordered sequence contains equal values."""
    return any(
        value == previous
        for index, value in enumerate(values)
        for previous in values[:index]
    )


@dataclass(frozen=True, slots=True, init=False)
class ExperimentDatasetPartition:
    """One immutable, ordered, model-ready dataset partition."""

    partition_name: str
    identifiers: tuple[object, ...]
    features: tuple[tuple[object, ...], ...]
    targets: tuple[object, ...]
    feature_names: tuple[str, ...]
    metadata: Mapping[str, object]

    def __init__(
        self,
        partition_name: str,
        identifiers: Sequence[object],
        features: Sequence[Sequence[object]],
        targets: Sequence[object],
        feature_names: Sequence[str],
        metadata: Mapping[str, object] = MappingProxyType({}),
    ) -> None:
        """Validate inputs and store detached, recursively immutable values."""
        if _invalid_name(partition_name):
            raise ValueError("partition_name must be a non-empty string")
        try:
            normalized_identifiers = tuple(identifiers)
            normalized_features = tuple(tuple(row) for row in features)
            normalized_targets = tuple(targets)
            normalized_names = tuple(feature_names)
        except TypeError as error:
            raise TypeError("partition values must be sequences") from error
        if not normalized_identifiers:
            raise ValueError("identifiers must not be empty")
        if not normalized_features:
            raise ValueError("features must not be empty")
        if not normalized_targets:
            raise ValueError("targets must not be empty")
        if not normalized_names:
            raise ValueError("feature_names must not be empty")
        if _has_duplicates(normalized_identifiers):
            raise ValueError("identifiers must be unique")
        if not (
            len(normalized_identifiers)
            == len(normalized_features)
            == len(normalized_targets)
        ):
            raise ValueError("identifiers, features, and targets must align")
        if any(len(row) != len(normalized_names) for row in normalized_features):
            raise ValueError("every feature row must match feature_names")
        if any(_invalid_name(name) for name in normalized_names):
            raise ValueError("feature_names must contain non-empty strings")
        if _has_duplicates(normalized_names):
            raise ValueError("feature_names must be unique")
        if not isinstance(metadata, Mapping):
            raise TypeError("metadata must be a mapping")

        object.__setattr__(self, "partition_name", partition_name)
        object.__setattr__(self, "identifiers", tuple(_freeze(normalized_identifiers)))
        object.__setattr__(self, "features", tuple(_freeze(normalized_features)))
        object.__setattr__(self, "targets", tuple(_freeze(normalized_targets)))
        object.__setattr__(self, "feature_names", normalized_names)
        object.__setattr__(self, "metadata", _freeze_mapping(metadata))

    @property
    def observation_count(self) -> int:
        """Return the number of aligned observations."""
        return len(self.identifiers)

    @property
    def feature_count(self) -> int:
        """Return the number of values in each feature row."""
        return len(self.feature_names)

    def to_dict(self) -> dict[str, object]:
        """Return a deterministic, fully detached mutable representation."""
        return {
            "partition_name": self.partition_name,
            "identifiers": _thaw(self.identifiers),
            "features": _thaw(self.features),
            "targets": _thaw(self.targets),
            "feature_names": list(self.feature_names),
            "metadata": _thaw(self.metadata),
        }


@dataclass(frozen=True, slots=True, init=False)
class PreparedExperimentDataset:
    """Immutable train, validation, and test data ready for model consumers."""

    dataset_name: str
    dataset_version: str
    train: ExperimentDatasetPartition
    validation: ExperimentDatasetPartition
    test: ExperimentDatasetPartition
    feature_names: tuple[str, ...]
    target_name: str
    metadata: Mapping[str, object]

    def __init__(
        self,
        dataset_name: str,
        dataset_version: str,
        train: ExperimentDatasetPartition,
        validation: ExperimentDatasetPartition,
        test: ExperimentDatasetPartition,
        feature_names: Sequence[str],
        target_name: str,
        metadata: Mapping[str, object] = MappingProxyType({}),
    ) -> None:
        """Validate partition compatibility and store detached metadata."""
        if _invalid_name(dataset_name):
            raise ValueError("dataset_name must be a non-empty string")
        if _invalid_name(dataset_version):
            raise ValueError("dataset_version must be a non-empty string")
        if _invalid_name(target_name):
            raise ValueError("target_name must be a non-empty string")
        partitions = (train, validation, test)
        if any(
            not isinstance(partition, ExperimentDatasetPartition)
            for partition in partitions
        ):
            raise TypeError("partitions must be ExperimentDatasetPartition instances")
        if tuple(partition.partition_name for partition in partitions) != (
            "train",
            "validation",
            "test",
        ):
            raise ValueError("partition names must be train, validation, and test")
        normalized_names = tuple(feature_names)
        if any(
            partition.feature_names != train.feature_names for partition in partitions
        ):
            raise ValueError("all partitions must expose the same feature_names")
        if normalized_names != train.feature_names:
            raise ValueError("top-level feature_names must match partition schemas")
        all_identifiers = train.identifiers + validation.identifiers + test.identifiers
        if _has_duplicates(all_identifiers):
            raise ValueError("identifiers must not overlap across partitions")
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
        """Return the training observation count."""
        return self.train.observation_count

    @property
    def validation_observation_count(self) -> int:
        """Return the validation observation count."""
        return self.validation.observation_count

    @property
    def test_observation_count(self) -> int:
        """Return the test observation count."""
        return self.test.observation_count

    @property
    def total_observation_count(self) -> int:
        """Return the observation count across all partitions."""
        return sum(
            (
                self.training_observation_count,
                self.validation_observation_count,
                self.test_observation_count,
            )
        )

    @property
    def feature_count(self) -> int:
        """Return the shared feature count."""
        return len(self.feature_names)

    def to_dict(self) -> dict[str, object]:
        """Return a deterministic, fully detached mutable representation."""
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


class ExperimentDatasetPreparer:
    """Stateless converter from temporal splits to model-ready partitions."""

    preparer_name = "experiment-dataset"

    def prepare(self, split: TemporalDatasetSplit) -> PreparedExperimentDataset:
        """Return an immutable model-ready snapshot of ``split``.

        Raises:
            TypeError: If ``split`` is not a :class:`TemporalDatasetSplit`.
            ValueError: If a record's feature schema is not exactly declared.
        """
        if not isinstance(split, TemporalDatasetSplit):
            raise TypeError("split must be a TemporalDatasetSplit")
        feature_names = tuple(split.feature_names)
        if not feature_names or any(_invalid_name(name) for name in feature_names):
            raise ValueError("feature_names must contain non-empty strings")
        if _has_duplicates(feature_names):
            raise ValueError("feature_names must be unique")

        def prepare_partition(
            partition_name: str, records: Sequence[DatasetRecord]
        ) -> ExperimentDatasetPartition:
            rows: list[tuple[object, ...]] = []
            identifiers: list[object] = []
            targets: list[object] = []
            for record in records:
                record_names = tuple(record.features)
                if len(record_names) != len(feature_names) or any(
                    name not in record.features for name in feature_names
                ):
                    raise ValueError(
                        "every record must expose exactly the declared feature names"
                    )
                identifiers.append(record.identifier)
                rows.append(tuple(record.features[name] for name in feature_names))
                targets.append(record.target)
            return ExperimentDatasetPartition(
                partition_name=partition_name,
                identifiers=identifiers,
                features=rows,
                targets=targets,
                feature_names=feature_names,
                metadata={
                    "partition_name": partition_name,
                    "observation_count": len(identifiers),
                    "feature_count": len(feature_names),
                },
            )

        return PreparedExperimentDataset(
            dataset_name=split.dataset_name,
            dataset_version=split.dataset_version,
            train=prepare_partition("train", split.train),
            validation=prepare_partition("validation", split.validation),
            test=prepare_partition("test", split.test),
            feature_names=feature_names,
            target_name=split.target_name,
            metadata=split.metadata,
        )
