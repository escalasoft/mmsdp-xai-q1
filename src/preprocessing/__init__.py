"""Stable preprocessing schema contracts."""

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
    "FeatureTable",
    "InvalidFeatureTableError",
    "InvalidManifestError",
    "InvalidTemporalSplitError",
    "MergedFeatureRecord",
    "PreprocessingManifest",
    "PreprocessingSchemaError",
    "PreprocessingSplit",
    "TemporalSplit",
    "DataFrameLike",
    "PreprocessingValidationError",
    "PreprocessingValidationReport",
    "validate_preprocessing_dataframe",
]
