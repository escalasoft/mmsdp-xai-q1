"""Side-effect-free structural validation for preprocessing dataframes."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Protocol


class PreprocessingValidationError(ValueError):
    """Raised when a preprocessing dataframe is structurally invalid."""


class _CountableValues(Protocol):
    def sum(self) -> object: ...


class _MissingValueTable(Protocol):
    def sum(self) -> object: ...


class DataFrameLike(Protocol):
    """Read-only dataframe operations required by the validator."""

    @property
    def columns(self) -> Iterable[object]: ...

    @property
    def index(self) -> Sequence[object]: ...

    def isna(self) -> _MissingValueTable: ...

    def duplicated(self) -> _CountableValues: ...


@dataclass(frozen=True)
class PreprocessingValidationReport:
    """Immutable observations produced by structural dataframe validation."""

    row_count: int
    column_count: int
    missing_values: Mapping[str, int]
    duplicated_row_count: int

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "missing_values", MappingProxyType(dict(self.missing_values))
        )


def validate_preprocessing_dataframe(
    dataframe: DataFrameLike,
    *,
    required_columns: Sequence[str] = (),
    target_column: str | None = None,
    feature_columns: Sequence[str] = (),
) -> PreprocessingValidationReport:
    """Validate dataframe structure without changing the supplied dataframe.

    Duplicate rows and missing values are observations in the returned report,
    not validation failures. No value transformation or scientific validation is
    performed.
    """
    columns = tuple(dataframe.columns)
    _validate_column_names(columns)
    _validate_non_empty(dataframe)

    required = _validate_requested_columns(required_columns, "required_columns")
    features = _validate_requested_columns(feature_columns, "feature_columns")
    _validate_columns_exist(columns, required, "Required")
    _validate_columns_exist(columns, features, "Feature")
    _validate_target_column(columns, target_column, features)

    return PreprocessingValidationReport(
        row_count=len(dataframe.index),
        column_count=len(columns),
        missing_values=_missing_value_counts(dataframe, columns),
        duplicated_row_count=int(dataframe.duplicated().sum()),
    )


def _validate_column_names(columns: tuple[object, ...]) -> None:
    duplicates = sorted(
        (str(name) for name, count in Counter(columns).items() if count > 1)
    )
    if duplicates:
        raise PreprocessingValidationError(
            f"Dataframe contains duplicated column names: {', '.join(duplicates)}"
        )
    invalid = [
        name for name in columns if not isinstance(name, str) or not name.strip()
    ]
    if invalid:
        raise PreprocessingValidationError(
            "Dataframe column names must be non-empty strings"
        )


def _validate_non_empty(dataframe: DataFrameLike) -> None:
    if len(dataframe.index) == 0:
        raise PreprocessingValidationError("Dataframe must contain at least one row")


def _validate_requested_columns(
    names: Sequence[str], parameter_name: str
) -> tuple[str, ...]:
    values = tuple(names)
    if any(not isinstance(name, str) or not name.strip() for name in values):
        raise PreprocessingValidationError(
            f"{parameter_name} must contain non-empty strings"
        )
    if len(values) != len(set(values)):
        raise PreprocessingValidationError(
            f"{parameter_name} must not contain duplicates"
        )
    return values


def _validate_columns_exist(
    columns: tuple[object, ...], requested: tuple[str, ...], label: str
) -> None:
    missing = sorted(set(requested).difference(columns))
    if missing:
        raise PreprocessingValidationError(
            f"{label} columns do not exist: {', '.join(missing)}"
        )


def _validate_target_column(
    columns: tuple[object, ...],
    target_column: str | None,
    feature_columns: tuple[str, ...],
) -> None:
    if target_column is None:
        return
    if not isinstance(target_column, str) or not target_column.strip():
        raise PreprocessingValidationError(
            "target_column must be a non-empty string or None"
        )
    if target_column not in columns:
        raise PreprocessingValidationError(
            f"Target column does not exist: {target_column}"
        )
    if target_column in feature_columns:
        raise PreprocessingValidationError(
            "Target column must not also be a feature column"
        )


def _missing_value_counts(
    dataframe: DataFrameLike, columns: tuple[object, ...]
) -> Mapping[str, int]:
    counts = dataframe.isna().sum()
    return {str(column): int(counts[column]) for column in columns}  # type: ignore[index]
