"""Public API contracts for preprocessing modality merging."""

import inspect
from dataclasses import FrozenInstanceError, fields, is_dataclass

import pytest

import preprocessing
import preprocessing.merger as merger
from preprocessing.merger import MergedFeatureTable, merge_preprocessing_tables


def test_merger_module_exports_exact_public_api() -> None:
    expected = {
        "ConflictingSharedMetadataError",
        "DuplicateModalityError",
        "DuplicatePrimaryKeyError",
        "IncompatiblePrimaryKeyError",
        "InvalidMergeInputError",
        "MergedFeatureTable",
        "MissingRequiredModalityError",
        "PreprocessingMergeError",
        "merge_preprocessing_tables",
    }

    assert set(merger.__all__) == expected
    assert all(
        getattr(preprocessing, name) is getattr(merger, name) for name in expected
    )


def test_merged_feature_table_is_an_immutable_exact_contract() -> None:
    assert is_dataclass(MergedFeatureTable)
    assert [field.name for field in fields(MergedFeatureTable)] == [
        "primary_key",
        "modalities",
        "records",
    ]

    result = MergedFeatureTable("id", ("code",), ())
    with pytest.raises(FrozenInstanceError):
        result.records = ()  # type: ignore[misc]


def test_merger_signature_exposes_only_merge_configuration() -> None:
    parameters = inspect.signature(merge_preprocessing_tables).parameters

    assert list(parameters) == [
        "tables",
        "required_modalities",
        "shared_metadata",
    ]
    assert parameters["required_modalities"].kind is inspect.Parameter.KEYWORD_ONLY
    assert parameters["shared_metadata"].default == ()


def test_all_merger_failures_have_one_dedicated_base_exception() -> None:
    exception_names = [
        "ConflictingSharedMetadataError",
        "DuplicateModalityError",
        "DuplicatePrimaryKeyError",
        "IncompatiblePrimaryKeyError",
        "InvalidMergeInputError",
        "MissingRequiredModalityError",
    ]

    assert all(
        issubclass(getattr(merger, name), merger.PreprocessingMergeError)
        for name in exception_names
    )
