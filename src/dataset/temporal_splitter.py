"""Deterministic chronological splitting for adapted datasets."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from numbers import Real
from types import MappingProxyType

from dataset.contracts import AdaptedDataset, DatasetRecord

__all__ = [
    "TemporalSplitConfiguration",
    "TemporalDatasetSplit",
    "TemporalDatasetSplitter",
]

_FRACTION_TOLERANCE = 1e-12


def _freeze_value(value: object) -> object:
    """Return a detached, recursively immutable snapshot."""
    if isinstance(value, Mapping):
        return MappingProxyType(
            {deepcopy(key): _freeze_value(item) for key, item in value.items()}
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_value(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze_value(item) for item in value)
    return deepcopy(value)


def _freeze_mapping(value: Mapping[str, object]) -> Mapping[str, object]:
    """Return a detached, read-only mapping snapshot."""
    return MappingProxyType(
        {deepcopy(key): _freeze_value(item) for key, item in value.items()}
    )


def _thaw_value(value: object) -> object:
    """Return detached mutable standard containers for a frozen value."""
    if isinstance(value, Mapping):
        return {deepcopy(key): _thaw_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_value(item) for item in value]
    if isinstance(value, frozenset):
        return {_thaw_value(item) for item in value}
    return deepcopy(value)


def _validate_fraction(name: str, value: object) -> float:
    """Validate and detach one configured fraction."""
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{name} must be a numeric value and not bool")
    normalized = float(value)
    if not math.isfinite(normalized) or not 0.0 < normalized < 1.0:
        raise ValueError(f"{name} must be greater than zero and less than one")
    return normalized


@dataclass(frozen=True, slots=True, init=False)
class TemporalSplitConfiguration:
    """Immutable fractions used to create a temporal dataset split."""

    train_fraction: float
    validation_fraction: float
    test_fraction: float

    def __init__(
        self,
        train_fraction: float,
        validation_fraction: float,
        test_fraction: float,
    ) -> None:
        """Validate and store detached numeric fractions."""
        train = _validate_fraction("train_fraction", train_fraction)
        validation = _validate_fraction("validation_fraction", validation_fraction)
        test = _validate_fraction("test_fraction", test_fraction)
        if not math.isclose(
            math.fsum((train, validation, test)),
            1.0,
            rel_tol=0.0,
            abs_tol=_FRACTION_TOLERANCE,
        ):
            raise ValueError("train, validation, and test fractions must sum to one")
        object.__setattr__(self, "train_fraction", train)
        object.__setattr__(self, "validation_fraction", validation)
        object.__setattr__(self, "test_fraction", test)

    def to_dict(self) -> dict[str, float]:
        """Return a deterministic, detached representation."""
        return {
            "train_fraction": self.train_fraction,
            "validation_fraction": self.validation_fraction,
            "test_fraction": self.test_fraction,
        }


@dataclass(frozen=True, slots=True, init=False)
class TemporalDatasetSplit:
    """Immutable chronological train, validation, and test partitions."""

    dataset_name: str
    dataset_version: str
    train: tuple[DatasetRecord, ...]
    validation: tuple[DatasetRecord, ...]
    test: tuple[DatasetRecord, ...]
    feature_names: tuple[str, ...]
    target_name: str
    metadata: Mapping[str, object]

    def __init__(
        self,
        dataset_name: str,
        dataset_version: str,
        train: Sequence[DatasetRecord],
        validation: Sequence[DatasetRecord],
        test: Sequence[DatasetRecord],
        feature_names: Sequence[str],
        target_name: str,
        metadata: Mapping[str, object],
    ) -> None:
        """Store immutable, detached partition metadata and ordered records."""
        partitions = (tuple(train), tuple(validation), tuple(test))
        if any(not partition for partition in partitions):
            raise ValueError("train, validation, and test partitions must be non-empty")
        if any(
            not isinstance(record, DatasetRecord)
            for partition in partitions
            for record in partition
        ):
            raise TypeError("partitions must contain only DatasetRecord instances")
        if not isinstance(metadata, Mapping):
            raise TypeError("metadata must be a mapping")

        object.__setattr__(self, "dataset_name", deepcopy(dataset_name))
        object.__setattr__(self, "dataset_version", deepcopy(dataset_version))
        object.__setattr__(self, "train", partitions[0])
        object.__setattr__(self, "validation", partitions[1])
        object.__setattr__(self, "test", partitions[2])
        object.__setattr__(self, "feature_names", tuple(deepcopy(tuple(feature_names))))
        object.__setattr__(self, "target_name", deepcopy(target_name))
        object.__setattr__(self, "metadata", _freeze_mapping(metadata))

    @property
    def training_observation_count(self) -> int:
        """Return the training partition size."""
        return len(self.train)

    @property
    def validation_observation_count(self) -> int:
        """Return the validation partition size."""
        return len(self.validation)

    @property
    def test_observation_count(self) -> int:
        """Return the test partition size."""
        return len(self.test)

    @property
    def total_observation_count(self) -> int:
        """Return the total number of partitioned observations."""
        return sum(
            (
                self.training_observation_count,
                self.validation_observation_count,
                self.test_observation_count,
            )
        )

    def to_dict(self) -> dict[str, object]:
        """Return a deterministic, fully detached standard representation."""
        return {
            "dataset_name": deepcopy(self.dataset_name),
            "dataset_version": deepcopy(self.dataset_version),
            "train": [record.to_dict() for record in self.train],
            "validation": [record.to_dict() for record in self.validation],
            "test": [record.to_dict() for record in self.test],
            "feature_names": list(deepcopy(self.feature_names)),
            "target_name": deepcopy(self.target_name),
            "metadata": _thaw_value(self.metadata),
        }


class TemporalDatasetSplitter:
    """Create deterministic contiguous partitions ordered by timestamp."""

    splitter_name = "temporal"

    def __init__(self, configuration: TemporalSplitConfiguration) -> None:
        """Initialize the splitter with an immutable configuration."""
        if not isinstance(configuration, TemporalSplitConfiguration):
            raise TypeError("configuration must be a TemporalSplitConfiguration")
        self._configuration = configuration

    @property
    def configuration(self) -> TemporalSplitConfiguration:
        """Return the immutable split configuration."""
        return self._configuration

    def split(self, dataset: AdaptedDataset) -> TemporalDatasetSplit:
        """Sort an adapted dataset chronologically and partition it."""
        if not isinstance(dataset, AdaptedDataset):
            raise TypeError("dataset must be an AdaptedDataset")
        records = tuple(dataset.records)
        if not records:
            raise ValueError("dataset must not be empty")
        for record in records:
            if record.timestamp is None:
                raise ValueError("every record must contain a non-None timestamp")
            if isinstance(record.timestamp, str) and not record.timestamp.strip():
                raise ValueError("timestamps must not be empty strings")

        try:
            ordered = tuple(sorted(records, key=lambda record: record.timestamp))
            for earlier, later in zip(ordered, ordered[1:], strict=False):
                if not earlier.timestamp <= later.timestamp:
                    raise ValueError("timestamps do not define a consistent ordering")
        except Exception as error:
            raise ValueError("timestamps must be consistently comparable") from error

        total = len(ordered)
        train_count = math.floor(total * self.configuration.train_fraction)
        validation_count = math.floor(total * self.configuration.validation_fraction)
        test_count = total - train_count - validation_count
        if min(train_count, validation_count, test_count) <= 0:
            raise ValueError("configuration would produce an empty partition")

        validation_end = train_count + validation_count
        return TemporalDatasetSplit(
            dataset_name=dataset.dataset_name,
            dataset_version=dataset.dataset_version,
            train=ordered[:train_count],
            validation=ordered[train_count:validation_end],
            test=ordered[validation_end:],
            feature_names=dataset.feature_names,
            target_name=dataset.target_name,
            metadata=dataset.metadata,
        )
