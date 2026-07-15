"""Validation of caller-supplied commit-level dataset records and splits."""

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from .schema import DatasetContract, DatasetValidationError

Record = Mapping[str, str]


def validate_dataset(records: Sequence[Record], contract: DatasetContract) -> None:
    """Validate records against only the rules supplied by ``contract``."""
    _reject_empty_dataset(records)
    validate_required_columns(records, contract.required_columns)
    validate_missing_primary_keys(records, contract.primary_key)
    validate_duplicate_primary_keys(records, contract.primary_key)
    if contract.target_column is not None:
        validate_missing_targets(records, contract.target_column)
        validate_binary_target(records, contract.target_column)
    if contract.timestamp_column is not None:
        validate_timestamp_presence(records, contract.timestamp_column)


def validate_required_columns(
    records: Sequence[Record], required_columns: Sequence[str]
) -> None:
    """Require a non-empty dataset and every supplied column in every record."""
    _reject_empty_dataset(records)
    required = set(required_columns)
    for index, record in enumerate(records):
        missing = required.difference(record)
        if missing:
            names = ", ".join(sorted(missing))
            raise DatasetValidationError(
                f"Record {index} is missing required columns: {names}"
            )


def validate_duplicate_primary_keys(
    records: Sequence[Record], primary_key: str
) -> None:
    """Reject repeated non-empty primary-key values."""
    seen: set[str] = set()
    for record in records:
        value = record.get(primary_key, "")
        if value and value in seen:
            raise DatasetValidationError(
                f"Duplicate primary key in column {primary_key!r}: {value!r}"
            )
        if value:
            seen.add(value)


def validate_missing_primary_keys(records: Sequence[Record], primary_key: str) -> None:
    """Reject absent or empty primary-key values."""
    _validate_present_values(records, primary_key, "primary key")


def validate_missing_targets(records: Sequence[Record], target_column: str) -> None:
    """Reject absent or empty target values."""
    _validate_present_values(records, target_column, "target")


def validate_binary_target(records: Sequence[Record], target_column: str) -> None:
    """Require supplied target values to use the string domain ``0`` and ``1``."""
    validate_missing_targets(records, target_column)
    invalid = {
        record[target_column]
        for record in records
        if record[target_column] not in {"0", "1"}
    }
    if invalid:
        values = ", ".join(repr(value) for value in sorted(invalid))
        raise DatasetValidationError(
            f"Column {target_column!r} contains non-binary values: {values}"
        )


def validate_timestamp_presence(
    records: Sequence[Record], timestamp_column: str
) -> None:
    """Reject absent or empty timestamp values."""
    _validate_present_values(records, timestamp_column, "timestamp")


def validate_chronological_split_ordering(
    train_records: Sequence[Record],
    validation_records: Sequence[Record],
    test_records: Sequence[Record],
    timestamp_column: str,
    *,
    timestamp_key: Callable[[str], Any] | None = None,
) -> None:
    """Validate supplied train, validation, and test records are chronological.

    The function validates existing partitions only. By default it compares the
    supplied timestamp strings directly; callers may provide a parsing key when
    their approved timestamp representation requires one.
    """
    splits = (train_records, validation_records, test_records)
    for records in splits:
        _reject_empty_dataset(records)
        validate_timestamp_presence(records, timestamp_column)

    key = timestamp_key or _identity
    keyed_splits = [
        [key(record[timestamp_column]) for record in records] for records in splits
    ]
    for values in keyed_splits:
        if values != sorted(values):
            raise DatasetValidationError(
                "Records within each split must be in chronological order"
            )
    if max(keyed_splits[0]) > min(keyed_splits[1]) or max(keyed_splits[1]) > min(
        keyed_splits[2]
    ):
        raise DatasetValidationError(
            "Split timestamps must follow train, validation, then test order"
        )


def _reject_empty_dataset(records: Sequence[Record]) -> None:
    if not records:
        raise DatasetValidationError("Dataset must contain at least one record")


def _validate_present_values(
    records: Sequence[Record], column: str, value_kind: str
) -> None:
    _reject_empty_dataset(records)
    for index, record in enumerate(records):
        if column not in record or record[column] == "":
            raise DatasetValidationError(
                f"Record {index} has a missing {value_kind} in column {column!r}"
            )


def _identity(value: str) -> str:
    return value
