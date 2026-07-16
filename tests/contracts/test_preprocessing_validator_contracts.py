"""Public API contracts for preprocessing dataframe validation."""

from dataclasses import FrozenInstanceError

import pytest

import preprocessing
from preprocessing import PreprocessingValidationReport


def test_preprocessing_package_exports_validator_api() -> None:
    expected = {
        "DataFrameLike",
        "PreprocessingValidationError",
        "PreprocessingValidationReport",
        "validate_preprocessing_dataframe",
    }

    assert expected <= set(preprocessing.__all__)
    assert all(hasattr(preprocessing, name) for name in expected)


def test_validation_report_is_immutable() -> None:
    report = PreprocessingValidationReport(1, 1, {"feature": 0}, 0)

    with pytest.raises(FrozenInstanceError):
        report.row_count = 2  # type: ignore[misc]
