"""Deterministic, side-effect-free merging of validated modality tables."""

from __future__ import annotations

from collections.abc import Hashable, Iterable, Sequence
from dataclasses import dataclass

from preprocessing.schema import FeatureTable, MergedFeatureRecord

__all__ = [
    "ConflictingSharedMetadataError",
    "DuplicateModalityError",
    "DuplicatePrimaryKeyError",
    "IncompatiblePrimaryKeyError",
    "InvalidMergeInputError",
    "MissingRequiredModalityError",
    "PreprocessingMergeError",
    "MergedFeatureTable",
    "merge_preprocessing_tables",
]


class PreprocessingMergeError(ValueError):
    """Base exception for preprocessing merge-rule violations."""


class DuplicatePrimaryKeyError(PreprocessingMergeError):
    """Raised when one modality contains the same primary key more than once."""


class MissingRequiredModalityError(PreprocessingMergeError):
    """Raised when a required modality table was not supplied."""


class ConflictingSharedMetadataError(PreprocessingMergeError):
    """Raised when modalities disagree on shared metadata for one record."""


class IncompatiblePrimaryKeyError(PreprocessingMergeError):
    """Raised when modality tables do not use one common primary-key column."""


class DuplicateModalityError(PreprocessingMergeError):
    """Raised when more than one table is supplied for the same modality."""


class InvalidMergeInputError(PreprocessingMergeError):
    """Raised when table records or merge configuration are malformed."""


@dataclass(frozen=True)
class MergedFeatureTable:
    """Immutable collection of deterministically ordered merged records."""

    primary_key: str
    modalities: tuple[str, ...]
    records: tuple[MergedFeatureRecord, ...]


def merge_preprocessing_tables(
    tables: Iterable[FeatureTable],
    *,
    required_modalities: Sequence[str],
    shared_metadata: Sequence[str] = (),
) -> MergedFeatureTable:
    """Outer-merge validated modality tables without mutating their records.

    Modality-specific columns are namespaced as ``modality.column``. Columns
    named in ``shared_metadata`` remain unprefixed and must have equal values
    whenever multiple modalities provide them for the same primary key.
    """

    table_values = tuple(tables)
    required = _unique_names(required_modalities, "required_modalities")
    shared = _unique_names(shared_metadata, "shared_metadata")
    if not table_values:
        raise MissingRequiredModalityError("No modality tables were supplied")
    if any(not isinstance(table, FeatureTable) for table in table_values):
        raise InvalidMergeInputError("tables must contain only FeatureTable values")

    modalities = tuple(sorted(table.modality for table in table_values))
    if len(modalities) != len(set(modalities)):
        raise DuplicateModalityError("Each modality may be supplied only once")
    missing = sorted(set(required).difference(modalities))
    if missing:
        raise MissingRequiredModalityError(
            f"Missing required modalities: {', '.join(missing)}"
        )

    primary_keys = {table.primary_key for table in table_values}
    if len(primary_keys) != 1:
        raise IncompatiblePrimaryKeyError(
            "All modality tables must use the same primary key"
        )
    primary_key = next(iter(primary_keys))
    if primary_key in shared:
        raise InvalidMergeInputError("shared_metadata must not include the primary key")

    by_key: dict[Hashable, dict[str, object]] = {}
    sources: dict[Hashable, set[str]] = {}
    raw_keys: dict[Hashable, object] = {}
    for table in sorted(table_values, key=lambda item: item.modality):
        _merge_table(table, shared, by_key, sources, raw_keys)

    ordered_keys = sorted(by_key, key=_deterministic_key)
    records = tuple(
        MergedFeatureRecord(
            primary_key=primary_key,
            primary_key_value=raw_keys[key],
            values=by_key[key],
            source_modalities=tuple(sorted(sources[key])),
        )
        for key in ordered_keys
    )
    return MergedFeatureTable(primary_key, modalities, records)


def _merge_table(
    table: FeatureTable,
    shared: tuple[str, ...],
    by_key: dict[Hashable, dict[str, object]],
    sources: dict[Hashable, set[str]],
    raw_keys: dict[Hashable, object],
) -> None:
    declared = set(table.column_names)
    if table.primary_key not in declared:
        raise InvalidMergeInputError(
            f"Primary key {table.primary_key!r} is not declared by {table.modality!r}"
        )
    undeclared_shared = sorted(set(shared).difference(declared))
    if undeclared_shared:
        raise InvalidMergeInputError(
            f"Shared metadata missing from {table.modality!r}: "
            f"{', '.join(undeclared_shared)}"
        )

    seen: set[Hashable] = set()
    for record in table.records:
        missing_columns = sorted(declared.difference(record))
        if missing_columns:
            raise InvalidMergeInputError(
                f"Record in {table.modality!r} is missing columns: "
                f"{', '.join(missing_columns)}"
            )
        key_value = record[table.primary_key]
        key = _hashable_key(key_value, table.modality)
        if key in seen:
            raise DuplicatePrimaryKeyError(
                f"Duplicate primary key in modality {table.modality!r}: {key_value!r}"
            )
        seen.add(key)
        raw_keys.setdefault(key, key_value)
        values = by_key.setdefault(key, {})
        sources.setdefault(key, set()).add(table.modality)
        for column in table.column_names:
            if column == table.primary_key:
                continue
            value = record[column]
            output_column = column if column in shared else f"{table.modality}.{column}"
            if output_column in values and values[output_column] != value:
                raise ConflictingSharedMetadataError(
                    f"Conflicting shared metadata {column!r} for primary key "
                    f"{key_value!r}"
                )
            values[output_column] = value


def _unique_names(names: Sequence[str], parameter: str) -> tuple[str, ...]:
    values = tuple(names)
    if any(not isinstance(name, str) or not name.strip() for name in values):
        raise InvalidMergeInputError(f"{parameter} must contain non-empty strings")
    if len(values) != len(set(values)):
        raise InvalidMergeInputError(f"{parameter} must not contain duplicates")
    return values


def _hashable_key(value: object, modality: str) -> Hashable:
    if not isinstance(value, Hashable):
        raise InvalidMergeInputError(
            f"Primary keys in modality {modality!r} must be hashable"
        )
    return value


def _deterministic_key(value: Hashable) -> tuple[str, str, str]:
    value_type = type(value)
    return (value_type.__module__, value_type.__qualname__, repr(value))
