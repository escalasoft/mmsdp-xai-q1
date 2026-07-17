"""Deterministic, side-effect-free dataset partitioning."""

from __future__ import annotations

import math
from dataclasses import dataclass
from numbers import Real
from typing import Protocol, TypeVar

__all__ = [
    "DataFrameCompatible",
    "EmptyDatasetError",
    "InvalidSplitInputError",
    "InvalidSplitRatiosError",
    "PreprocessingPartitions",
    "PreprocessingSplitterError",
    "split_preprocessing_dataset",
]


class PreprocessingSplitterError(ValueError):
    """Base exception for preprocessing dataset splitting failures."""


class InvalidSplitRatiosError(PreprocessingSplitterError):
    """Raised when split ratios are invalid or do not sum to one."""


class EmptyDatasetError(PreprocessingSplitterError):
    """Raised when a dataset has no records to partition."""


class InvalidSplitInputError(PreprocessingSplitterError):
    """Raised when an input does not provide dataframe-compatible operations."""


class _RowIndexer(Protocol):
    def __getitem__(self, key: slice, /) -> object: ...


class DataFrameCompatible(Protocol):
    """Minimal dataframe operations required by the splitter."""

    @property
    def index(self) -> object: ...

    @property
    def iloc(self) -> _RowIndexer: ...

    def copy(self, *, deep: bool = True) -> object: ...


FrameT = TypeVar("FrameT", bound=DataFrameCompatible)


@dataclass(frozen=True)
class PreprocessingPartitions:
    """Immutable container for deterministic dataset partitions."""

    train_records: object
    validation_records: object
    test_records: object


def split_preprocessing_dataset(
    dataframe: FrameT,
    *,
    train_ratio: float = 0.7,
    validation_ratio: float = 0.15,
    test_ratio: float = 0.15,
) -> PreprocessingPartitions:
    """Partition a dataframe-compatible input in its existing row order."""

    _validate_ratios(train_ratio, validation_ratio, test_ratio)
    row_count = _row_count(dataframe)
    if row_count == 0:
        raise EmptyDatasetError("Dataset must contain at least one record")

    train_end = int(row_count * train_ratio)
    validation_end = train_end + int(row_count * validation_ratio)

    return PreprocessingPartitions(
        train_records=_copy_partition(dataframe, 0, train_end),
        validation_records=_copy_partition(dataframe, train_end, validation_end),
        test_records=_copy_partition(dataframe, validation_end, row_count),
    )


def _validate_ratios(
    train_ratio: object,
    validation_ratio: object,
    test_ratio: object,
) -> None:
    ratios = (train_ratio, validation_ratio, test_ratio)
    if any(
        isinstance(ratio, bool)
        or not isinstance(ratio, Real)
        or not math.isfinite(float(ratio))
        for ratio in ratios
    ):
        raise InvalidSplitRatiosError("Split ratios must be finite numbers")
    if any(float(ratio) <= 0 or float(ratio) >= 1 for ratio in ratios):
        raise InvalidSplitRatiosError("Each split ratio must be between zero and one")
    if not math.isclose(sum(float(ratio) for ratio in ratios), 1.0):
        raise InvalidSplitRatiosError("Split ratios must sum to one")


def _row_count(dataframe: object) -> int:
    try:
        index = dataframe.index  # type: ignore[attr-defined]
        row_count = len(index)  # type: ignore[arg-type]
        dataframe.iloc  # type: ignore[attr-defined]
        dataframe.copy  # type: ignore[attr-defined]
    except (AttributeError, TypeError) as error:
        raise InvalidSplitInputError(
            "Input must provide dataframe-compatible index, iloc, and copy operations"
        ) from error
    return row_count


def _copy_partition(dataframe: FrameT, start: int, stop: int) -> object:
    try:
        partition = dataframe.iloc[start:stop]
        return partition.copy(deep=True)  # type: ignore[attr-defined, no-any-return]
    except (AttributeError, TypeError, ValueError) as error:
        raise InvalidSplitInputError(
            "Input must support positional row slicing and copying"
        ) from error
