"""Unit tests for deterministic preprocessing dataset splitting."""

from copy import deepcopy
from dataclasses import FrozenInstanceError

import pytest

from preprocessing.splitter import (
    EmptyDatasetError,
    InvalidSplitInputError,
    InvalidSplitRatiosError,
    split_preprocessing_dataset,
)


class _Indexer:
    def __init__(self, frame: "Frame") -> None:
        self.frame = frame

    def __getitem__(self, key: slice) -> "Frame":
        return Frame(self.frame.rows[key])


class Frame:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows = deepcopy(rows)
        self.index = list(range(len(rows)))
        self.iloc = _Indexer(self)

    def copy(self, *, deep: bool = True) -> "Frame":
        return Frame(deepcopy(self.rows) if deep else self.rows)


def test_normal_split_preserves_order_and_configured_ratios() -> None:
    frame = Frame([{"id": number} for number in range(10)])

    result = split_preprocessing_dataset(
        frame, train_ratio=0.6, validation_ratio=0.2, test_ratio=0.2
    )

    assert [row["id"] for row in result.train_records.rows] == list(range(6))
    assert [row["id"] for row in result.validation_records.rows] == [6, 7]
    assert [row["id"] for row in result.test_records.rows] == [8, 9]


def test_split_is_deterministic() -> None:
    frame = Frame([{"id": number} for number in range(20)])

    first = split_preprocessing_dataset(frame)
    second = split_preprocessing_dataset(frame)

    assert first.train_records.rows == second.train_records.rows
    assert first.validation_records.rows == second.validation_records.rows
    assert first.test_records.rows == second.test_records.rows


@pytest.mark.parametrize(
    "ratios",
    [
        (0.6, 0.2, 0.1),
        (0.0, 0.5, 0.5),
        (-0.1, 0.5, 0.6),
        (1.0, 0.0, 0.0),
        (float("nan"), 0.5, 0.5),
        (True, 0.5, 0.5),
        ("0.6", 0.2, 0.2),
    ],
)
def test_invalid_ratios_are_rejected(ratios: tuple[object, object, object]) -> None:
    with pytest.raises(InvalidSplitRatiosError):
        split_preprocessing_dataset(
            Frame([{"id": 1}]),
            train_ratio=ratios[0],  # type: ignore[arg-type]
            validation_ratio=ratios[1],  # type: ignore[arg-type]
            test_ratio=ratios[2],  # type: ignore[arg-type]
        )


def test_empty_dataframe_is_rejected() -> None:
    with pytest.raises(EmptyDatasetError, match="at least one record"):
        split_preprocessing_dataset(Frame([]))


def test_invalid_input_is_rejected() -> None:
    with pytest.raises(InvalidSplitInputError, match="dataframe-compatible"):
        split_preprocessing_dataset(object())  # type: ignore[arg-type]


def test_output_is_immutable() -> None:
    result = split_preprocessing_dataset(Frame([{"id": number} for number in range(4)]))

    with pytest.raises(FrozenInstanceError):
        result.train_records = Frame([])  # type: ignore[misc]


def test_original_dataframe_is_unchanged_and_partitions_are_independent() -> None:
    frame = Frame([{"id": number, "values": [number]} for number in range(10)])
    before = deepcopy(frame.rows)

    result = split_preprocessing_dataset(frame)
    result.train_records.rows[0]["values"].append("changed")

    assert frame.rows == before
