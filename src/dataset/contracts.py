"""Framework-neutral contracts for normalized dataset observations.

Dataset adapters isolate external source representations from the rest of the
architecture by normalizing them into the immutable internal representation
defined by this module.  The contracts perform no loading, parsing,
preprocessing, persistence, or framework-specific work.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from types import MappingProxyType
from typing import Protocol, runtime_checkable

__all__ = ["DatasetRecord", "AdaptedDataset", "DatasetAdapter"]


def _is_invalid_name(value: object) -> bool:
    """Return whether a value is not a non-empty string."""

    return not isinstance(value, str) or not value.strip()


def _freeze_value(value: object) -> object:
    """Create a detached, recursively read-only snapshot of a value."""

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
    """Create a detached mapping-proxy snapshot."""

    return MappingProxyType(
        {deepcopy(key): _freeze_value(item) for key, item in value.items()}
    )


def _thaw_value(value: object) -> object:
    """Convert a frozen value into detached standard mutable structures."""

    if isinstance(value, Mapping):
        return {deepcopy(key): _thaw_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_value(item) for item in value]
    if isinstance(value, frozenset):
        return {_thaw_value(item) for item in value}
    return deepcopy(value)


def _contains_duplicate(values: Sequence[object]) -> bool:
    """Return whether an ordered sequence contains equal values."""

    return any(
        value == previous
        for index, value in enumerate(values)
        for previous in values[:index]
    )


@dataclass(frozen=True, slots=True, init=False)
class DatasetRecord:
    """One immutable observation in the framework-neutral representation.

    Attributes:
        identifier: Caller-supplied observation identifier.
        features: Ordered, read-only snapshot of named feature values.
        target: Caller-supplied prediction target.
        timestamp: Optional caller-supplied temporal ordering value.
        metadata: Read-only snapshot of descriptive observation metadata.
    """

    identifier: object
    features: Mapping[str, object]
    target: object
    timestamp: object | None
    metadata: Mapping[str, object]

    def __init__(
        self,
        identifier: object,
        features: Mapping[str, object],
        target: object,
        timestamp: object | None = None,
        metadata: Mapping[str, object] = MappingProxyType({}),
    ) -> None:
        """Initialize and validate a normalized dataset observation.

        Args:
            identifier: Non-null observation identifier.
            features: Non-empty ordered mapping of named feature values.
            target: Non-null prediction target.
            timestamp: Optional temporal ordering value.
            metadata: Descriptive metadata for the observation.

        Raises:
            TypeError: If features or metadata is not a mapping.
            ValueError: If a required value is null or a feature name is
                empty, invalid, or duplicated.
        """
        if identifier is None:
            raise ValueError("identifier must not be None")
        if features is None:
            raise ValueError("features must not be None")
        if not isinstance(features, Mapping):
            raise TypeError("features must be a mapping")
        feature_items = tuple(features.items())
        if not feature_items:
            raise ValueError("features must not be empty")
        feature_names = tuple(name for name, _ in feature_items)
        if any(_is_invalid_name(name) for name in feature_names):
            raise ValueError("feature names must be non-empty strings")
        if _contains_duplicate(feature_names):
            raise ValueError("feature names must be unique")
        if target is None:
            raise ValueError("target must not be None")
        if metadata is None:
            raise ValueError("metadata must not be None")
        if not isinstance(metadata, Mapping):
            raise TypeError("metadata must be a mapping")

        object.__setattr__(self, "identifier", deepcopy(identifier))
        object.__setattr__(self, "features", _freeze_mapping(dict(feature_items)))
        object.__setattr__(self, "target", deepcopy(target))
        object.__setattr__(self, "timestamp", deepcopy(timestamp))
        object.__setattr__(self, "metadata", _freeze_mapping(metadata))

    def to_dict(self) -> dict[str, object]:
        """Return a deterministic, detached standard-structure representation.

        Returns:
            A new dictionary whose nested contract containers are ordinary
            mutable Python dictionaries, lists, and sets.
        """
        return {
            "identifier": deepcopy(self.identifier),
            "features": _thaw_value(self.features),
            "target": deepcopy(self.target),
            "timestamp": deepcopy(self.timestamp),
            "metadata": _thaw_value(self.metadata),
        }


@dataclass(frozen=True, slots=True, init=False)
class AdaptedDataset:
    """Immutable dataset normalized by an external-source adapter.

    Attributes:
        dataset_name: Stable human-readable dataset name.
        dataset_version: Caller-supplied dataset version identifier.
        records: Observations in their source-defined deterministic order.
        feature_names: Feature names in the required observation order.
        target_name: Stable human-readable prediction-target name.
        metadata: Read-only snapshot of descriptive dataset metadata.
    """

    dataset_name: str
    dataset_version: str
    records: tuple[DatasetRecord, ...]
    feature_names: tuple[str, ...]
    target_name: str
    metadata: Mapping[str, object]

    def __init__(
        self,
        dataset_name: str,
        dataset_version: str,
        records: Sequence[DatasetRecord],
        feature_names: Sequence[str],
        target_name: str,
        metadata: Mapping[str, object] = MappingProxyType({}),
    ) -> None:
        """Initialize and validate a normalized framework-neutral dataset.

        Args:
            dataset_name: Stable non-empty dataset name.
            dataset_version: Non-empty dataset version identifier.
            records: Ordered normalized observations.
            feature_names: Declared feature names in required order.
            target_name: Stable non-empty target name.
            metadata: Descriptive metadata for the dataset.

        Raises:
            TypeError: If records contain another type or metadata is not a
                mapping.
            ValueError: If a required value is empty, identifiers or feature
                names are duplicated, or a record violates the feature schema.
        """
        if _is_invalid_name(dataset_name):
            raise ValueError("dataset_name must be a non-empty string")
        if _is_invalid_name(dataset_version):
            raise ValueError("dataset_version must be a non-empty string")

        normalized_records = tuple(records)
        if not normalized_records:
            raise ValueError("records must not be empty")
        if any(not isinstance(record, DatasetRecord) for record in normalized_records):
            raise TypeError("records must contain only DatasetRecord instances")

        normalized_feature_names = tuple(feature_names)
        if not normalized_feature_names:
            raise ValueError("feature_names must not be empty")
        if any(_is_invalid_name(name) for name in normalized_feature_names):
            raise ValueError("feature_names must contain non-empty strings")
        if _contains_duplicate(normalized_feature_names):
            raise ValueError("feature_names must not contain duplicates")
        if _is_invalid_name(target_name):
            raise ValueError("target_name must be a non-empty string")

        for record in normalized_records:
            if tuple(record.features) != normalized_feature_names:
                raise ValueError(
                    "every record must expose exactly feature_names in the same order"
                )
        if metadata is None:
            raise ValueError("metadata must not be None")
        if not isinstance(metadata, Mapping):
            raise TypeError("metadata must be a mapping")

        object.__setattr__(self, "dataset_name", dataset_name)
        object.__setattr__(self, "dataset_version", dataset_version)
        object.__setattr__(self, "records", normalized_records)
        object.__setattr__(self, "feature_names", normalized_feature_names)
        object.__setattr__(self, "target_name", target_name)
        object.__setattr__(self, "metadata", _freeze_mapping(metadata))

    @property
    def observation_count(self) -> int:
        """Return the number of normalized observations in the dataset."""

        return len(self.records)

    def to_dict(self) -> dict[str, object]:
        """Return a deterministic, detached standard-structure representation.

        Returns:
            A new dictionary containing records and feature names as lists and
            metadata as an ordinary mutable dictionary.
        """
        return {
            "dataset_name": self.dataset_name,
            "dataset_version": self.dataset_version,
            "records": [record.to_dict() for record in self.records],
            "feature_names": list(self.feature_names),
            "target_name": self.target_name,
            "metadata": _thaw_value(self.metadata),
        }


@runtime_checkable
class DatasetAdapter(Protocol):
    """Structural contract for normalizing an external dataset source.

    Implementations may consume any external representation, but must return
    the framework-neutral immutable representation defined by this module.
    """

    @property
    def adapter_name(self) -> str:
        """Return the stable, human-readable adapter name."""
        ...

    def adapt(self, source: object, /) -> AdaptedDataset:
        """Normalize an external source into an adapted dataset."""
        ...
