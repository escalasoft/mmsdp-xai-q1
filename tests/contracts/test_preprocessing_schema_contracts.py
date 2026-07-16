"""Public API contracts for the preprocessing schema package."""

from dataclasses import fields

import preprocessing
from preprocessing import (
    FeatureTable,
    MergedFeatureRecord,
    PreprocessingManifest,
    TemporalSplit,
)


def test_preprocessing_package_exports_only_stable_schema_api() -> None:
    expected = {
        "FeatureTable",
        "DataFrameLike",
        "InvalidFeatureTableError",
        "InvalidManifestError",
        "InvalidTemporalSplitError",
        "MergedFeatureRecord",
        "PreprocessingManifest",
        "PreprocessingSchemaError",
        "PreprocessingSplit",
        "TemporalSplit",
        "PreprocessingValidationError",
        "PreprocessingValidationReport",
        "validate_preprocessing_dataframe",
    }

    assert set(preprocessing.__all__) == expected
    assert all(getattr(preprocessing, name) is not None for name in expected)


def test_public_dataclasses_expose_only_requested_fields() -> None:
    assert [field.name for field in fields(FeatureTable)] == [
        "modality",
        "primary_key",
        "column_names",
        "records",
    ]
    assert [field.name for field in fields(MergedFeatureRecord)] == [
        "primary_key",
        "primary_key_value",
        "values",
        "source_modalities",
    ]
    assert [field.name for field in fields(TemporalSplit)] == [
        "train_records",
        "validation_records",
        "test_records",
        "timestamp_column",
        "train_end",
        "validation_end",
    ]
    assert [field.name for field in fields(PreprocessingManifest)] == [
        "created_at",
        "input_record_count",
        "output_record_count",
        "output_paths",
        "checksums",
        "configuration_summary",
    ]


def test_public_schema_has_no_out_of_scope_fields() -> None:
    prohibited_terms = {
        "label",
        "target",
        "prediction",
        "model",
        "scaler",
        "encoder",
        "sampler",
        "qtbase",
    }
    public_classes = (
        FeatureTable,
        MergedFeatureRecord,
        TemporalSplit,
        PreprocessingManifest,
    )

    for schema_class in public_classes:
        field_names = {field.name.lower() for field in fields(schema_class)}
        assert all(
            term not in field_name
            for field_name in field_names
            for term in prohibited_terms
        )
