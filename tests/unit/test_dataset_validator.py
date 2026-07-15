"""Unit tests for dataset-record validation."""

import pytest

from dataset import (
    DatasetContract,
    DatasetValidationError,
    validate_binary_target,
    validate_chronological_split_ordering,
    validate_dataset,
    validate_duplicate_primary_keys,
    validate_missing_primary_keys,
    validate_missing_targets,
    validate_required_columns,
    validate_timestamp_presence,
)


def test_empty_dataset_is_rejected() -> None:
    contract = DatasetContract(("key",), (), "key")

    with pytest.raises(DatasetValidationError, match="at least one"):
        validate_dataset([], contract)


def test_missing_required_column_is_rejected() -> None:
    with pytest.raises(DatasetValidationError, match="required columns"):
        validate_required_columns([{"key": "one"}], ("key", "value"))


def test_duplicate_primary_key_is_rejected() -> None:
    records = [{"key": "same"}, {"key": "same"}]

    with pytest.raises(DatasetValidationError, match="Duplicate"):
        validate_duplicate_primary_keys(records, "key")


def test_missing_primary_key_is_rejected() -> None:
    with pytest.raises(DatasetValidationError, match="missing primary key"):
        validate_missing_primary_keys([{"key": ""}], "key")


def test_missing_target_is_rejected() -> None:
    with pytest.raises(DatasetValidationError, match="missing target"):
        validate_missing_targets([{"outcome": ""}], "outcome")


def test_missing_timestamp_is_rejected() -> None:
    with pytest.raises(DatasetValidationError, match="missing timestamp"):
        validate_timestamp_presence([{}], "when")


def test_non_binary_target_is_rejected() -> None:
    with pytest.raises(DatasetValidationError, match="non-binary"):
        validate_binary_target([{"outcome": "2"}], "outcome")


def test_binary_target_is_valid() -> None:
    validate_binary_target([{"outcome": "0"}, {"outcome": "1"}], "outcome")


def test_chronological_splits_are_valid() -> None:
    validate_chronological_split_ordering(
        [{"when": "2026-01-01"}, {"when": "2026-01-02"}],
        [{"when": "2026-02-01"}],
        [{"when": "2026-03-01"}],
        "when",
    )


def test_invalid_chronological_split_ordering_is_rejected() -> None:
    with pytest.raises(DatasetValidationError, match="train, validation, then test"):
        validate_chronological_split_ordering(
            [{"when": "2026-02-01"}],
            [{"when": "2026-01-01"}],
            [{"when": "2026-03-01"}],
            "when",
        )
