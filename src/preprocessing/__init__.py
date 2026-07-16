"""Stable preprocessing schema contracts."""

from preprocessing.merger import (
    ConflictingSharedMetadataError,
    DuplicateModalityError,
    DuplicatePrimaryKeyError,
    IncompatiblePrimaryKeyError,
    InvalidMergeInputError,
    MergedFeatureTable,
    MissingRequiredModalityError,
    PreprocessingMergeError,
    merge_preprocessing_tables,
)
from preprocessing.schema import (
    FeatureTable,
    InvalidFeatureTableError,
    InvalidManifestError,
    InvalidTemporalSplitError,
    MergedFeatureRecord,
    PreprocessingManifest,
    PreprocessingSchemaError,
    PreprocessingSplit,
    TemporalSplit,
)
from preprocessing.validator import (
    DataFrameLike,
    PreprocessingValidationError,
    PreprocessingValidationReport,
    validate_preprocessing_dataframe,
)

__all__ = [
    "ConflictingSharedMetadataError",
    "DuplicateModalityError",
    "DuplicatePrimaryKeyError",
    "FeatureTable",
    "IncompatiblePrimaryKeyError",
    "InvalidFeatureTableError",
    "InvalidMergeInputError",
    "InvalidManifestError",
    "InvalidTemporalSplitError",
    "MergedFeatureRecord",
    "MergedFeatureTable",
    "MissingRequiredModalityError",
    "PreprocessingMergeError",
    "PreprocessingManifest",
    "PreprocessingSchemaError",
    "PreprocessingSplit",
    "TemporalSplit",
    "DataFrameLike",
    "PreprocessingValidationError",
    "PreprocessingValidationReport",
    "validate_preprocessing_dataframe",
    "merge_preprocessing_tables",
]
