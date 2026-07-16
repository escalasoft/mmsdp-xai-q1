"""Unit tests for structural preprocessing dataframe validation."""

from copy import deepcopy

import pytest

from preprocessing import (
    PreprocessingValidationError,
    validate_preprocessing_dataframe,
)


class _Counts(dict[str, int]):
    def sum(self) -> int:
        return sum(self.values())


class _MissingTable:
    def __init__(self, counts: dict[str, int]) -> None:
        self._counts = counts

    def sum(self) -> _Counts:
        return _Counts(self._counts)


class Frame:
    def __init__(self, columns: list[str], rows: list[list[object]]) -> None:
        self.columns = columns
        self.rows = rows
        self.index = list(range(len(rows)))

    def isna(self) -> _MissingTable:
        return _MissingTable(
            {
                column: sum(row[index] is None for row in self.rows)
                for index, column in enumerate(self.columns)
            }
        )

    def duplicated(self) -> _Counts:
        seen: list[list[object]] = []
        duplicated = 0
        for row in self.rows:
            if row in seen:
                duplicated += 1
            else:
                seen.append(row)
        return _Counts({"duplicated": duplicated})


def test_valid_dataframe_returns_structural_report_without_modification() -> None:
    frame = Frame(
        ["feature", "target"],
        [[1, 0], [None, 1], [1, 0]],
    )
    before = deepcopy(frame.__dict__)

    report = validate_preprocessing_dataframe(
        frame,
        required_columns=("feature", "target"),
        target_column="target",
        feature_columns=("feature",),
    )

    assert report.row_count == 3
    assert report.column_count == 2
    assert dict(report.missing_values) == {"feature": 1, "target": 0}
    assert report.duplicated_row_count == 1
    assert frame.__dict__ == before
    with pytest.raises(TypeError):
        report.missing_values["feature"] = 0  # type: ignore[index]


@pytest.mark.parametrize(
    ("frame", "message"),
    [
        (Frame(["feature"], []), "at least one row"),
        (Frame(["feature", "feature"], [[1, 1]]), "duplicated column"),
    ],
)
def test_invalid_dataframe_structure_is_rejected(frame: Frame, message: str) -> None:
    with pytest.raises(PreprocessingValidationError, match=message):
        validate_preprocessing_dataframe(frame)


def test_missing_required_column_is_rejected() -> None:
    with pytest.raises(PreprocessingValidationError, match="Required columns"):
        validate_preprocessing_dataframe(
            Frame(["feature"], [[1]]), required_columns=("missing",)
        )


@pytest.mark.parametrize("target", ["", "missing"])
def test_invalid_target_column_is_rejected(target: str) -> None:
    with pytest.raises(PreprocessingValidationError, match="target|Target"):
        validate_preprocessing_dataframe(
            Frame(["feature"], [[1]]), target_column=target
        )


def test_target_cannot_be_a_feature_column() -> None:
    with pytest.raises(PreprocessingValidationError, match="also be a feature"):
        validate_preprocessing_dataframe(
            Frame(["target"], [[1]]),
            target_column="target",
            feature_columns=("target",),
        )


@pytest.mark.parametrize("features", [("missing",), ("feature", "feature"), ("",)])
def test_invalid_feature_columns_are_rejected(features: tuple[str, ...]) -> None:
    with pytest.raises(PreprocessingValidationError, match="feature_columns|Feature"):
        validate_preprocessing_dataframe(
            Frame(["feature"], [[1]]), feature_columns=features
        )
