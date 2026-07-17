"""Public API contracts for preprocessing dataset splitting."""

import inspect
from dataclasses import FrozenInstanceError, fields, is_dataclass

import pytest

import preprocessing.splitter as splitter
from preprocessing.splitter import PreprocessingPartitions, split_preprocessing_dataset


def test_splitter_module_exports_public_api() -> None:
    expected = {
        "DataFrameCompatible",
        "EmptyDatasetError",
        "InvalidSplitInputError",
        "InvalidSplitRatiosError",
        "PreprocessingPartitions",
        "PreprocessingSplitterError",
        "split_preprocessing_dataset",
    }

    assert set(splitter.__all__) == expected
    assert all(getattr(splitter, name) is not None for name in expected)


def test_preprocessing_partitions_is_an_immutable_exact_contract() -> None:
    assert is_dataclass(PreprocessingPartitions)
    assert [field.name for field in fields(PreprocessingPartitions)] == [
        "train_records",
        "validation_records",
        "test_records",
    ]

    result = PreprocessingPartitions((), (), ())
    with pytest.raises(FrozenInstanceError):
        result.test_records = ("changed",)  # type: ignore[misc]


def test_splitter_public_signature_exposes_only_partition_configuration() -> None:
    parameters = inspect.signature(split_preprocessing_dataset).parameters

    assert list(parameters) == [
        "dataframe",
        "train_ratio",
        "validation_ratio",
        "test_ratio",
    ]
    assert parameters["train_ratio"].default == 0.7
    assert parameters["validation_ratio"].default == 0.15
    assert parameters["test_ratio"].default == 0.15


def test_splitter_module_exports_the_package_contract() -> None:
    from preprocessing.splitter import PreprocessingPartitions as ModulePartitions

    assert ModulePartitions is PreprocessingPartitions
