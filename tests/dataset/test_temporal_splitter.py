"""Tests for deterministic temporal dataset splitting."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from dataset.contracts import AdaptedDataset, DatasetRecord
from dataset.temporal_splitter import (
    TemporalDatasetSplit,
    TemporalDatasetSplitter,
    TemporalSplitConfiguration,
)


def _record(identifier: object, timestamp: object) -> DatasetRecord:
    return DatasetRecord(
        identifier=identifier,
        features={"temperature": identifier},
        target="normal",
        timestamp=timestamp,
        metadata={"source": ["sensor"]},
    )


def _dataset(timestamps: tuple[object, ...] = (6, 1, 4, 2, 5, 3)) -> AdaptedDataset:
    return AdaptedDataset(
        dataset_name="machines",
        dataset_version="2026.1",
        records=tuple(
            _record(index, timestamp) for index, timestamp in enumerate(timestamps)
        ),
        feature_names=("temperature",),
        target_name="condition",
        metadata={"site": "plant-a", "labels": ["verified"]},
    )


@pytest.fixture
def configuration() -> TemporalSplitConfiguration:
    return TemporalSplitConfiguration(0.5, 0.25, 0.25)


def test_split_is_chronological_contiguous_and_has_exact_counts(configuration):
    result = TemporalDatasetSplitter(configuration).split(_dataset())

    assert [record.timestamp for record in result.train] == [1, 2, 3]
    assert [record.timestamp for record in result.validation] == [4]
    assert [record.timestamp for record in result.test] == [5, 6]
    assert result.training_observation_count == 3
    assert result.validation_observation_count == 1
    assert result.test_observation_count == 2
    assert result.total_observation_count == 6


def test_splitter_name_is_stable(configuration):
    assert TemporalDatasetSplitter(configuration).splitter_name == "temporal"


def test_dataset_fields_and_detached_metadata_are_preserved(configuration):
    source = _dataset()
    result = TemporalDatasetSplitter(configuration).split(source)

    assert result.dataset_name == source.dataset_name
    assert result.dataset_version == source.dataset_version
    assert result.feature_names == source.feature_names
    assert result.target_name == source.target_name
    assert result.metadata == source.metadata
    assert result.metadata is not source.metadata


def test_splitting_does_not_modify_source_dataset_or_records(configuration):
    source = _dataset()
    before = source.to_dict()
    records_before = source.records

    TemporalDatasetSplitter(configuration).split(source)

    assert source.to_dict() == before
    assert source.records == records_before


def test_configuration_is_immutable_and_to_dict_is_deterministic(configuration):
    with pytest.raises((FrozenInstanceError, AttributeError)):
        configuration.train_fraction = 0.4
    assert configuration.to_dict() == configuration.to_dict()
    output = configuration.to_dict()
    output["train_fraction"] = 0.1
    assert configuration.train_fraction == 0.5


def test_result_is_immutable(configuration):
    result = TemporalDatasetSplitter(configuration).split(_dataset())
    assert isinstance(result, TemporalDatasetSplit)
    assert isinstance(result.train, tuple)
    with pytest.raises((FrozenInstanceError, AttributeError)):
        result.train = ()
    with pytest.raises(TypeError):
        result.metadata["site"] = "changed"


def test_result_to_dict_is_deterministic_and_detached(configuration):
    result = TemporalDatasetSplitter(configuration).split(_dataset())
    first = result.to_dict()
    second = result.to_dict()

    assert first == second
    assert first is not second
    first["metadata"]["labels"].append("changed")
    first["train"][0]["features"]["temperature"] = "changed"
    assert result.to_dict() == second


def test_repeated_splitting_produces_equal_results(configuration):
    splitter = TemporalDatasetSplitter(configuration)
    source = _dataset()
    assert splitter.split(source) == splitter.split(source)


def test_equal_timestamps_preserve_source_order(configuration):
    source = _dataset((2, 1, 1, 3, 2, 4, 5, 6))
    result = TemporalDatasetSplitter(configuration).split(source)
    ordered_ids = [
        record.identifier for record in result.train + result.validation + result.test
    ]
    assert ordered_ids == [1, 2, 0, 4, 3, 5, 6, 7]


@pytest.mark.parametrize("timestamp", [None, "", "   "])
def test_missing_or_empty_timestamps_are_rejected(configuration, timestamp):
    source = _dataset((1, 2, timestamp, 4))
    with pytest.raises(ValueError, match="timestamp"):
        TemporalDatasetSplitter(configuration).split(source)


@pytest.mark.parametrize("value", [None, [], {}, "dataset", object()])
def test_non_adapted_dataset_inputs_are_rejected(configuration, value):
    with pytest.raises(TypeError, match="AdaptedDataset"):
        TemporalDatasetSplitter(configuration).split(value)


def test_empty_bypass_constructed_dataset_is_rejected(configuration):
    source = object.__new__(AdaptedDataset)
    object.__setattr__(source, "records", ())
    with pytest.raises(ValueError, match="empty"):
        TemporalDatasetSplitter(configuration).split(source)


@pytest.mark.parametrize("size", [1, 2, 3])
def test_insufficient_dataset_is_rejected(configuration, size):
    source = _dataset(tuple(range(size)))
    with pytest.raises(ValueError, match="empty partition"):
        TemporalDatasetSplitter(configuration).split(source)


@pytest.mark.parametrize("value", ["0.5", None, object(), [], 1 + 2j])
def test_invalid_fraction_types_are_rejected(value):
    with pytest.raises(TypeError, match="numeric"):
        TemporalSplitConfiguration(value, 0.25, 0.25)


@pytest.mark.parametrize("position", [0, 1, 2])
def test_bool_fractions_are_rejected(position):
    values = [0.5, 0.25, 0.25]
    values[position] = True
    with pytest.raises(TypeError, match="not bool"):
        TemporalSplitConfiguration(*values)


@pytest.mark.parametrize("value", [0, -0.1, 1, 1.1, float("inf"), float("nan")])
def test_out_of_range_fractions_are_rejected(value):
    with pytest.raises(ValueError, match="greater than zero"):
        TemporalSplitConfiguration(value, 0.5, 0.5)


def test_fractions_must_sum_to_one():
    with pytest.raises(ValueError, match="sum to one"):
        TemporalSplitConfiguration(0.4, 0.3, 0.2)
    with pytest.raises(ValueError, match="sum to one"):
        TemporalSplitConfiguration(0.5, 0.25, 0.25000000001)


def test_partitions_do_not_overlap_and_cover_every_identifier_once(configuration):
    source = _dataset()
    result = TemporalDatasetSplitter(configuration).split(source)
    partitions = [
        {record.identifier for record in result.train},
        {record.identifier for record in result.validation},
        {record.identifier for record in result.test},
    ]
    assert partitions[0].isdisjoint(partitions[1])
    assert partitions[0].isdisjoint(partitions[2])
    assert partitions[1].isdisjoint(partitions[2])
    identifiers = [
        record.identifier
        for partition in (result.train, result.validation, result.test)
        for record in partition
    ]
    assert sorted(identifiers) == sorted(record.identifier for record in source.records)
    assert len(identifiers) == len(set(identifiers))


def test_temporal_boundaries_are_respected(configuration):
    result = TemporalDatasetSplitter(configuration).split(_dataset())
    assert max(record.timestamp for record in result.train) <= min(
        record.timestamp for record in result.validation
    )
    assert max(record.timestamp for record in result.validation) <= min(
        record.timestamp for record in result.test
    )


@pytest.mark.parametrize("timestamps", [(1, "2", 3, 4), (1, float("nan"), 2, 3)])
def test_unorderable_or_inconsistent_timestamps_are_rejected(configuration, timestamps):
    with pytest.raises(ValueError, match="consistently comparable"):
        TemporalDatasetSplitter(configuration).split(_dataset(timestamps))


def test_direct_split_metadata_is_detached():
    metadata = {"nested": ["original"]}
    result = TemporalDatasetSplit(
        "name",
        "version",
        (_record(1, 1),),
        (_record(2, 2),),
        (_record(3, 3),),
        ("temperature",),
        "target",
        metadata,
    )
    metadata["nested"].append("caller change")
    assert result.to_dict()["metadata"] == {"nested": ["original"]}


def test_public_exports_are_narrow_and_explicit():
    from dataset import temporal_splitter

    assert temporal_splitter.__all__ == [
        "TemporalSplitConfiguration",
        "TemporalDatasetSplit",
        "TemporalDatasetSplitter",
    ]
