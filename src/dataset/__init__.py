"""Stable public API for commit-level dataset contracts and validation."""

from .loader import load_csv
from .schema import (
    DatasetArtifact,
    DatasetContract,
    DatasetError,
    DatasetNotFoundError,
    DatasetSplit,
    DatasetStage,
    DatasetValidationError,
    MalformedDatasetError,
    UnsupportedDatasetFormatError,
)
from .validator import (
    validate_binary_target,
    validate_chronological_split_ordering,
    validate_dataset,
    validate_duplicate_primary_keys,
    validate_missing_primary_keys,
    validate_missing_targets,
    validate_required_columns,
    validate_timestamp_presence,
)

__all__ = [
    "DatasetArtifact",
    "DatasetContract",
    "DatasetError",
    "DatasetNotFoundError",
    "DatasetSplit",
    "DatasetStage",
    "DatasetValidationError",
    "MalformedDatasetError",
    "UnsupportedDatasetFormatError",
    "load_csv",
    "validate_binary_target",
    "validate_chronological_split_ordering",
    "validate_dataset",
    "validate_duplicate_primary_keys",
    "validate_missing_primary_keys",
    "validate_missing_targets",
    "validate_required_columns",
    "validate_timestamp_presence",
]
