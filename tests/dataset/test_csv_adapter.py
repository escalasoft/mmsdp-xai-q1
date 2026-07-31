"""Tests for deterministic framework-neutral CSV adaptation."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path
from types import MappingProxyType

import pytest

from dataset.contracts import DatasetAdapter
from dataset.csv_adapter import CsvDatasetAdapter, CsvDatasetAdapterConfiguration


def _configuration(**changes: object) -> CsvDatasetAdapterConfiguration:
    """Return a small valid configuration, optionally with replacements."""

    values: dict[str, object] = {
        "dataset_name": "quality",
        "dataset_version": "1.0",
        "feature_names": ("size", "complexity"),
        "target_name": "defective",
    }
    values.update(changes)
    return CsvDatasetAdapterConfiguration(**values)  # type: ignore[arg-type]


def _write(tmp_path: Path, content: str, name: str = "data.csv") -> Path:
    """Write one test fixture and return its path."""

    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


def test_valid_adaptation_preserves_feature_and_source_row_order(
    tmp_path: Path,
) -> None:
    path = _write(tmp_path, "complexity,defective,size\n2,no,10\n4,yes,20\n")

    dataset = CsvDatasetAdapter(_configuration()).adapt(path)

    assert dataset.feature_names == ("size", "complexity")
    assert [record.identifier for record in dataset.records] == ["1", "2"]
    assert [record.features for record in dataset.records] == [
        {"size": "10", "complexity": "2"},
        {"size": "20", "complexity": "4"},
    ]
    assert [record.target for record in dataset.records] == ["no", "yes"]
    assert dataset.metadata["adapter"]["name"] == "csv"
    assert dataset.metadata["source"]["path"] == str(path)
    assert dataset.records[0].metadata["source"]["row_number"] == 1


def test_adapter_satisfies_protocol_and_has_stable_name() -> None:
    adapter = CsvDatasetAdapter(_configuration())

    assert isinstance(adapter, DatasetAdapter)
    assert adapter.adapter_name == "csv"


def test_explicit_identifiers_and_optional_timestamps(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "id,size,complexity,defective,when\na,10,2,no,2026-01-01\n",
    )
    adapter = CsvDatasetAdapter(
        _configuration(identifier_name="id", timestamp_name="when")
    )

    record = adapter.adapt(path).records[0]

    assert record.identifier == "a"
    assert record.timestamp == "2026-01-01"


def test_without_timestamp_uses_none(tmp_path: Path) -> None:
    record = (
        CsvDatasetAdapter(_configuration())
        .adapt(_write(tmp_path, "size,complexity,defective\n1,2,no\n"))
        .records[0]
    )

    assert record.timestamp is None


def test_configuration_metadata_is_detached_immutable_and_deterministic() -> None:
    caller_metadata = {"nested": {"labels": ["a"]}}
    configuration = _configuration(metadata=caller_metadata)
    caller_metadata["nested"]["labels"].append("changed")

    assert isinstance(configuration.metadata, MappingProxyType)
    assert configuration.to_dict()["metadata"] == {"nested": {"labels": ["a"]}}
    with pytest.raises(TypeError):
        configuration.metadata["new"] = True
    with pytest.raises(FrozenInstanceError):
        configuration.dataset_name = "changed"
    first = configuration.to_dict()
    assert first == configuration.to_dict()
    first["metadata"]["nested"]["labels"].append("detached")
    assert configuration.to_dict()["metadata"] == {"nested": {"labels": ["a"]}}


def test_repeated_adaptation_is_equal_and_does_not_change_inputs(
    tmp_path: Path,
) -> None:
    path = _write(tmp_path, "size,complexity,defective\n1,2,no\n")
    original_bytes = path.read_bytes()
    features = ["size", "complexity"]
    configuration = _configuration(feature_names=features)
    original_configuration = configuration.to_dict()
    adapter = CsvDatasetAdapter(configuration)

    first = adapter.adapt(path).to_dict()
    second = adapter.adapt(path).to_dict()

    assert first == second
    assert path.read_bytes() == original_bytes
    assert configuration.to_dict() == original_configuration
    assert features == ["size", "complexity"]


@pytest.mark.parametrize(
    ("delimiter", "content"),
    [
        (",", "size,complexity,defective\n1,2,no\n"),
        (";", "size;complexity;defective\n1;2;no\n"),
    ],
)
def test_comma_and_custom_delimiters(
    tmp_path: Path, delimiter: str, content: str
) -> None:
    dataset = CsvDatasetAdapter(_configuration(delimiter=delimiter)).adapt(
        _write(tmp_path, content)
    )

    assert dataset.records[0].features["size"] == "1"


def test_utf8_source_values_are_preserved(tmp_path: Path) -> None:
    path = _write(tmp_path, "size,complexity,defective\npequeño,ámbito,sí\n")

    record = CsvDatasetAdapter(_configuration()).adapt(path).records[0]

    assert record.features["size"] == "pequeño"
    assert record.target == "sí"


def test_missing_directory_and_unsupported_sources(tmp_path: Path) -> None:
    adapter = CsvDatasetAdapter(_configuration())

    with pytest.raises(FileNotFoundError):
        adapter.adapt(tmp_path / "missing.csv")
    with pytest.raises(IsADirectoryError):
        adapter.adapt(tmp_path)
    with pytest.raises(TypeError):
        adapter.adapt(42)


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("", "empty"),
        ("size,complexity,defective\n", "observation"),
        ("size,size,complexity,defective\n1,1,2,no\n", "duplicate"),
        ("size,defective\n1,no\n", "missing configured"),
        ("size,complexity,defective\n1,2,no,extra\n", "columns"),
        ("size,complexity,defective\n1,2\n", "columns"),
        ("size,complexity,defective\n,2,no\n", "empty configured features"),
        ("size,complexity,defective\n1,2,\n", "empty target"),
    ],
)
def test_invalid_csv_structure_or_required_values(
    tmp_path: Path, content: str, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        CsvDatasetAdapter(_configuration()).adapt(_write(tmp_path, content))


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("id,size,complexity,defective\n,1,2,no\n", "empty identifier"),
        ("id,size,complexity,defective\na,1,2,no\na,3,4,yes\n", "duplicate identifier"),
    ],
)
def test_invalid_explicit_identifiers(
    tmp_path: Path, content: str, message: str
) -> None:
    adapter = CsvDatasetAdapter(_configuration(identifier_name="id"))

    with pytest.raises(ValueError, match=message):
        adapter.adapt(_write(tmp_path, content))


def test_empty_timestamp_is_rejected(tmp_path: Path) -> None:
    adapter = CsvDatasetAdapter(_configuration(timestamp_name="when"))
    path = _write(tmp_path, "size,complexity,defective,when\n1,2,no,\n")

    with pytest.raises(ValueError, match="empty timestamp"):
        adapter.adapt(path)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"dataset_name": ""}, "dataset_name"),
        ({"dataset_version": "  "}, "dataset_version"),
        ({"target_name": ""}, "target_name"),
        ({"identifier_name": " "}, "identifier_name"),
        ({"timestamp_name": ""}, "timestamp_name"),
        ({"feature_names": ()}, "feature_names"),
        ({"feature_names": ("size", "")}, "feature_names"),
        ({"feature_names": ("size", "size")}, "duplicates"),
        ({"target_name": "size"}, "overlap"),
        ({"identifier_name": "size"}, "overlap"),
        ({"timestamp_name": "size"}, "overlap"),
        ({"identifier_name": "defective"}, "overlap"),
        ({"timestamp_name": "defective"}, "overlap"),
        ({"identifier_name": "same", "timestamp_name": "same"}, "overlap"),
    ],
)
def test_invalid_configuration_names_duplicates_and_role_overlaps(
    changes: dict[str, object], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        _configuration(**changes)
