"""Unit tests for safe CSV loading."""

from pathlib import Path

import pytest

from dataset import (
    DatasetNotFoundError,
    MalformedDatasetError,
    UnsupportedDatasetFormatError,
    load_csv,
)


def test_load_csv_returns_unmodified_string_records(tmp_path: Path) -> None:
    source = tmp_path / "records.csv"
    source.write_text('key,message\nabc,"value, preserved"\n', encoding="utf-8")

    assert load_csv(source) == [{"key": "abc", "message": "value, preserved"}]


def test_load_csv_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(DatasetNotFoundError):
        load_csv(tmp_path / "missing.csv")


def test_load_csv_rejects_unsupported_extension(tmp_path: Path) -> None:
    source = tmp_path / "records.json"
    source.write_text("{}", encoding="utf-8")

    with pytest.raises(UnsupportedDatasetFormatError):
        load_csv(source)


@pytest.mark.parametrize(
    "content",
    [
        'key,message\nabc,"unterminated\n',
        "key,message\nabc\n",
        "key,key\nabc,def\n",
    ],
)
def test_load_csv_rejects_malformed_csv(tmp_path: Path, content: str) -> None:
    source = tmp_path / "records.csv"
    source.write_text(content, encoding="utf-8")

    with pytest.raises(MalformedDatasetError):
        load_csv(source)
