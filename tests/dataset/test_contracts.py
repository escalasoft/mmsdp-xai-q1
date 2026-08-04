"""Tests for framework-neutral dataset adapter contracts."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from types import MappingProxyType

import pytest

from dataset.contracts import AdaptedDataset, DatasetAdapter, DatasetRecord


def _record(identifier: object = "r1") -> DatasetRecord:
    return DatasetRecord(
        identifier,
        {"code": [1, 2], "process": 3},
        1,
        "2025-01-01",
        {"origin": {"project": "sample"}},
    )


def _dataset(*records: DatasetRecord) -> AdaptedDataset:
    return AdaptedDataset(
        "sample",
        "1.0",
        records or (_record(),),
        ("code", "process"),
        "defective",
        {"license": "research"},
    )


def test_valid_dataset_record_construction() -> None:
    record = _record()

    assert record.identifier == "r1"
    assert tuple(record.features) == ("code", "process")
    assert record.target == 1
    assert record.timestamp == "2025-01-01"
    assert record.metadata["origin"]["project"] == "sample"


def test_dataset_record_fields_and_mappings_are_immutable() -> None:
    record = _record()

    with pytest.raises(FrozenInstanceError):
        record.target = 0
    with pytest.raises(TypeError):
        record.features["code"] = 4
    with pytest.raises(TypeError):
        record.metadata["new"] = True
    assert isinstance(record.features, MappingProxyType)
    assert isinstance(record.metadata, MappingProxyType)


def test_dataset_record_to_dict_is_deterministic_and_detached() -> None:
    record = _record()
    first = record.to_dict()
    second = record.to_dict()

    assert first == second
    assert list(first) == [
        "identifier",
        "features",
        "target",
        "timestamp",
        "metadata",
    ]
    first["features"]["code"].append(9)
    first["metadata"]["origin"]["project"] = "changed"
    assert record.to_dict() == second


def test_dataset_record_rejects_none_identifier() -> None:
    with pytest.raises(ValueError, match="identifier"):
        DatasetRecord(None, {"feature": 1}, 0)


def test_dataset_record_rejects_empty_features() -> None:
    with pytest.raises(ValueError, match="features"):
        DatasetRecord("r1", {}, 0)


@pytest.mark.parametrize("name", ["", "  ", 1, None])
def test_dataset_record_rejects_invalid_feature_names(name: object) -> None:
    with pytest.raises(ValueError, match="feature names"):
        DatasetRecord("r1", {name: 1}, 0)


def test_dataset_record_rejects_none_target() -> None:
    with pytest.raises(ValueError, match="target"):
        DatasetRecord("r1", {"feature": 1}, None)


def test_valid_adapted_dataset_preserves_order_and_reports_count() -> None:
    first = _record("r1")
    second = _record("r2")
    dataset = _dataset(first, second)

    assert dataset.records == (first, second)
    assert dataset.observation_count == 2
    assert dataset.dataset_name == "sample"


def test_adapted_dataset_fields_and_metadata_are_immutable() -> None:
    dataset = _dataset()

    with pytest.raises(FrozenInstanceError):
        dataset.target_name = "changed"
    with pytest.raises(TypeError):
        dataset.metadata["new"] = True
    assert isinstance(dataset.metadata, MappingProxyType)


def test_adapted_dataset_to_dict_is_deterministic_and_detached() -> None:
    dataset = _dataset()
    first = dataset.to_dict()
    second = dataset.to_dict()

    assert first == second
    assert list(first) == [
        "dataset_name",
        "dataset_version",
        "records",
        "feature_names",
        "target_name",
        "metadata",
    ]
    first["records"][0]["features"]["code"].append(9)
    first["feature_names"].append("new")
    first["metadata"]["license"] = "changed"
    assert dataset.to_dict() == second


def test_adapted_dataset_rejects_empty_records() -> None:
    with pytest.raises(ValueError, match="records"):
        AdaptedDataset("sample", "1", (), ("feature",), "target")


def test_adapted_dataset_allows_identifiers_reused_across_future_partitions() -> None:
    assert _dataset(_record("same"), _record("same")).observation_count == 2


@pytest.mark.parametrize(
    "feature_names",
    [(), ("code", ""), ("code", 1), ("code", "code")],
)
def test_adapted_dataset_rejects_invalid_or_duplicate_feature_names(
    feature_names: tuple[object, ...],
) -> None:
    with pytest.raises(ValueError, match="feature_names"):
        AdaptedDataset("sample", "1", (_record(),), feature_names, "target")


def test_adapted_dataset_rejects_different_record_features() -> None:
    record = DatasetRecord("r1", {"code": 1, "different": 2}, 0)
    with pytest.raises(ValueError, match="exactly feature_names"):
        _dataset(record)


def test_adapted_dataset_rejects_different_feature_order() -> None:
    record = DatasetRecord("r1", {"process": 1, "code": 2}, 0)
    with pytest.raises(ValueError, match="same order"):
        _dataset(record)


def test_runtime_protocol_accepts_structurally_valid_adapter() -> None:
    class ValidAdapter:
        @property
        def adapter_name(self) -> str:
            return "valid"

        def adapt(self, source: object, /) -> AdaptedDataset:
            return _dataset()

    assert isinstance(ValidAdapter(), DatasetAdapter)


def test_runtime_protocol_rejects_incompatible_object() -> None:
    class IncompatibleAdapter:
        adapter_name = "incompatible"

    assert not isinstance(IncompatibleAdapter(), DatasetAdapter)


def test_contracts_do_not_mutate_source_mappings_or_records() -> None:
    features = {"code": [1, 2], "process": 3}
    metadata = {"nested": {"value": 4}}
    expected_features = {"code": [1, 2], "process": 3}
    expected_metadata = {"nested": {"value": 4}}
    record = DatasetRecord("r1", features, 0, metadata=metadata)
    before_record = record.to_dict()

    dataset = AdaptedDataset(
        "sample", "1", [record], ["code", "process"], "target", metadata
    )

    assert features == expected_features
    assert metadata == expected_metadata
    assert record.to_dict() == before_record
    features["code"].append(9)
    metadata["nested"]["value"] = 10
    assert record.features["code"] == (1, 2)
    assert dataset.metadata["nested"]["value"] == 4


def test_public_exports_are_narrow() -> None:
    from dataset import contracts

    assert contracts.__all__ == ["DatasetRecord", "AdaptedDataset", "DatasetAdapter"]
