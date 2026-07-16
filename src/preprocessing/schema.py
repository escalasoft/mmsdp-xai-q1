"""Immutable, implementation-independent preprocessing schema contracts."""

from __future__ import annotations

import re
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from types import MappingProxyType

_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}\Z")


class PreprocessingSchemaError(Exception):
    """Base exception for invalid preprocessing schema values."""


class InvalidFeatureTableError(PreprocessingSchemaError):
    """Raised when a feature table violates a structural invariant."""


class InvalidTemporalSplitError(PreprocessingSchemaError):
    """Raised when temporal split metadata is structurally invalid."""


class InvalidManifestError(PreprocessingSchemaError):
    """Raised when preprocessing manifest metadata is invalid."""


class PreprocessingSplit(Enum):
    """Names of the chronological preprocessing partitions."""

    TRAIN = "train"
    VALIDATION = "validation"
    TEST = "test"


def _freeze_value(value: object) -> object:
    """Return a defensive, recursively read-only representation of a value."""

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
    return MappingProxyType(
        {deepcopy(key): _freeze_value(item) for key, item in value.items()}
    )


def _freeze_records(
    records: tuple[Mapping[str, object], ...],
    error_type: type[PreprocessingSchemaError],
) -> tuple[Mapping[str, object], ...]:
    frozen_records: list[Mapping[str, object]] = []
    for record in records:
        if not isinstance(record, Mapping):
            raise error_type("records must contain only mappings")
        frozen_records.append(_freeze_mapping(record))
    return tuple(frozen_records)


def _is_empty_string(value: object) -> bool:
    return not isinstance(value, str) or not value.strip()


@dataclass(frozen=True)
class FeatureTable:
    """A caller-defined modality feature table without scientific assumptions."""

    modality: str
    primary_key: str
    column_names: tuple[str, ...]
    records: tuple[Mapping[str, object], ...]

    def __post_init__(self) -> None:
        if _is_empty_string(self.modality):
            raise InvalidFeatureTableError("modality must be a non-empty string")
        if _is_empty_string(self.primary_key):
            raise InvalidFeatureTableError("primary_key must be a non-empty string")

        column_names = tuple(self.column_names)
        if not column_names or any(_is_empty_string(name) for name in column_names):
            raise InvalidFeatureTableError(
                "column_names must contain non-empty strings"
            )
        if len(column_names) != len(set(column_names)):
            raise InvalidFeatureTableError("column_names must not contain duplicates")

        object.__setattr__(self, "column_names", column_names)
        object.__setattr__(
            self,
            "records",
            _freeze_records(self.records, InvalidFeatureTableError),
        )


@dataclass(frozen=True)
class MergedFeatureRecord:
    """A read-only record shaped by caller-supplied feature values."""

    primary_key: str
    primary_key_value: object
    values: Mapping[str, object]
    source_modalities: tuple[str, ...]

    def __post_init__(self) -> None:
        if _is_empty_string(self.primary_key):
            raise PreprocessingSchemaError("primary_key must be a non-empty string")
        if not isinstance(self.values, Mapping):
            raise PreprocessingSchemaError("values must be a mapping")

        source_modalities = tuple(self.source_modalities)
        if len(source_modalities) != len(set(source_modalities)):
            raise PreprocessingSchemaError(
                "source_modalities must not contain duplicates"
            )

        object.__setattr__(
            self, "primary_key_value", _freeze_value(self.primary_key_value)
        )
        object.__setattr__(self, "values", _freeze_mapping(self.values))
        object.__setattr__(self, "source_modalities", source_modalities)


@dataclass(frozen=True)
class TemporalSplit:
    """Read-only records and timezone-aware chronological boundaries."""

    train_records: tuple[Mapping[str, object], ...]
    validation_records: tuple[Mapping[str, object], ...]
    test_records: tuple[Mapping[str, object], ...]
    timestamp_column: str
    train_end: datetime
    validation_end: datetime

    def __post_init__(self) -> None:
        if _is_empty_string(self.timestamp_column):
            raise InvalidTemporalSplitError(
                "timestamp_column must be a non-empty string"
            )
        if self.train_end.tzinfo is None or self.train_end.utcoffset() is None:
            raise InvalidTemporalSplitError("train_end must be timezone-aware")
        if (
            self.validation_end.tzinfo is None
            or self.validation_end.utcoffset() is None
        ):
            raise InvalidTemporalSplitError("validation_end must be timezone-aware")
        if self.train_end > self.validation_end:
            raise InvalidTemporalSplitError(
                "train_end must not be later than validation_end"
            )

        object.__setattr__(
            self,
            "train_records",
            _freeze_records(self.train_records, InvalidTemporalSplitError),
        )
        object.__setattr__(
            self,
            "validation_records",
            _freeze_records(self.validation_records, InvalidTemporalSplitError),
        )
        object.__setattr__(
            self,
            "test_records",
            _freeze_records(self.test_records, InvalidTemporalSplitError),
        )


@dataclass(frozen=True)
class PreprocessingManifest:
    """Read-only provenance metadata for preprocessing artifacts."""

    created_at: datetime
    input_record_count: int
    output_record_count: int
    output_paths: tuple[Path, ...]
    checksums: Mapping[str, str]
    configuration_summary: Mapping[str, object]

    def __post_init__(self) -> None:
        if self.input_record_count < 0 or self.output_record_count < 0:
            raise InvalidManifestError("record counts must not be negative")
        if self.output_record_count > self.input_record_count:
            raise InvalidManifestError(
                "output_record_count must not exceed input_record_count"
            )
        if not isinstance(self.checksums, Mapping):
            raise InvalidManifestError("checksums must be a mapping")
        if not isinstance(self.configuration_summary, Mapping):
            raise InvalidManifestError("configuration_summary must be a mapping")

        for key, checksum in self.checksums.items():
            if _is_empty_string(key):
                raise InvalidManifestError("checksum keys must be non-empty strings")
            if not isinstance(checksum, str) or not _SHA256_PATTERN.fullmatch(checksum):
                raise InvalidManifestError(
                    "checksum values must be lowercase SHA-256 hexadecimal strings"
                )

        object.__setattr__(self, "output_paths", tuple(self.output_paths))
        object.__setattr__(
            self,
            "checksums",
            MappingProxyType(dict(self.checksums)),
        )
        object.__setattr__(
            self,
            "configuration_summary",
            _freeze_mapping(self.configuration_summary),
        )
