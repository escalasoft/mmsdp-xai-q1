"""Tests for deterministic experiment dataset preparation."""

from dataclasses import FrozenInstanceError

import pytest

from dataset.contracts import DatasetRecord
from dataset.experiment_dataset import (
    ExperimentDatasetPartition,
    ExperimentDatasetPreparer,
    PreparedExperimentDataset,
)
from dataset.temporal_splitter import TemporalDatasetSplit


def record(identifier: int, first: object, second: object) -> DatasetRecord:
    """Build a record whose mapping order differs from the declared schema."""
    return DatasetRecord(
        identifier,
        {"second": second, "first": first},
        f"target-{identifier}",
        timestamp=identifier,
        metadata={"nested": [identifier]},
    )


@pytest.fixture
def split() -> TemporalDatasetSplit:
    """Return a valid ordered temporal split."""
    return TemporalDatasetSplit(
        "example",
        "1.0",
        (record(1, [10], 11), record(2, [20], 21)),
        (record(3, [30], 31),),
        (record(4, [40], 41),),
        ("first", "second"),
        "outcome",
        {"source": {"tags": ["stable"]}},
    )


def partition(name: str, identifier: int = 1) -> ExperimentDatasetPartition:
    """Return a minimal valid partition."""
    return ExperimentDatasetPartition(
        name, (identifier,), ((identifier,),), (identifier,), ("value",), {"x": 1}
    )


def test_prepare_preserves_order_schema_alignment_and_counts(split):
    prepared = ExperimentDatasetPreparer().prepare(split)

    assert prepared.train.identifiers == (1, 2)
    assert prepared.train.features == (((10,), 11), ((20,), 21))
    assert prepared.train.targets == ("target-1", "target-2")
    assert prepared.feature_names == ("first", "second")
    assert prepared.training_observation_count == 2
    assert prepared.validation_observation_count == 1
    assert prepared.test_observation_count == 1
    assert prepared.total_observation_count == 4
    assert prepared.feature_count == prepared.train.feature_count == 2
    assert prepared.train.metadata == {
        "partition_name": "train",
        "observation_count": 2,
        "feature_count": 2,
    }


def test_prepare_preserves_identity_and_metadata(split):
    prepared = ExperimentDatasetPreparer().prepare(split)

    assert (prepared.dataset_name, prepared.dataset_version, prepared.target_name) == (
        "example",
        "1.0",
        "outcome",
    )
    assert prepared.metadata == split.metadata


def test_prepare_does_not_modify_split_or_records(split):
    split_before = split.to_dict()
    records_before = [item.to_dict() for item in split.train]

    ExperimentDatasetPreparer().prepare(split)

    assert split.to_dict() == split_before
    assert [item.to_dict() for item in split.train] == records_before


def test_results_and_nested_values_are_immutable_and_detached(split):
    prepared = ExperimentDatasetPreparer().prepare(split)
    source_feature = [10]
    direct = ExperimentDatasetPartition(
        "train", (1,), ((source_feature,),), (1,), ("value",), {"nested": [1]}
    )

    with pytest.raises(FrozenInstanceError):
        prepared.dataset_name = "changed"
    with pytest.raises(TypeError):
        prepared.metadata["new"] = True
    with pytest.raises(TypeError):
        prepared.train.metadata["new"] = True
    source_feature.append(99)
    assert direct.features[0][0] == (10,)


def test_to_dict_is_deterministic_mutable_and_detached(split):
    prepared = ExperimentDatasetPreparer().prepare(split)
    first = prepared.to_dict()
    second = prepared.to_dict()

    assert first == second
    first["metadata"]["source"]["tags"].append("changed")
    first["train"]["features"][0][0].append(99)
    assert prepared.to_dict() == second


def test_repeated_preparation_is_equal(split):
    preparer = ExperimentDatasetPreparer()
    assert preparer.prepare(split) == preparer.prepare(split)


@pytest.mark.parametrize(
    ("arguments", "error"),
    [
        (("", (1,), ((1,),), (1,), ("x",), {}), ValueError),
        (("train", (), ((1,),), (1,), ("x",), {}), ValueError),
        (("train", (1,), (), (1,), ("x",), {}), ValueError),
        (("train", (1,), ((1,),), (), ("x",), {}), ValueError),
        (("train", (1,), ((1,),), (1,), (), {}), ValueError),
        (("train", (1,), ((1,),), (1,), ("x",), []), TypeError),
        (("train", True, ((1,),), (1,), ("x",), {}), TypeError),
    ],
)
def test_partition_rejects_empty_or_invalid_inputs(arguments, error):
    with pytest.raises(error):
        ExperimentDatasetPartition(*arguments)


def test_partition_rejects_duplicate_names_identifiers_and_bad_widths():
    with pytest.raises(ValueError, match="unique"):
        ExperimentDatasetPartition("train", (1,), ((1, 2),), (1,), ("x", "x"))
    with pytest.raises(ValueError, match="unique"):
        ExperimentDatasetPartition("train", (1, 1), ((1,), (2,)), (1, 2), ("x",))
    with pytest.raises(ValueError, match="match"):
        ExperimentDatasetPartition("train", (1,), ((1, 2),), (1,), ("x",))


def test_dataset_rejects_invalid_names_partition_names_and_schemas():
    train = partition("train", 1)
    validation = partition("validation", 2)
    test = partition("test", 3)
    with pytest.raises(ValueError, match="dataset_name"):
        PreparedExperimentDataset("", "1", train, validation, test, ("value",), "y")
    with pytest.raises(ValueError, match="partition names"):
        PreparedExperimentDataset(
            "data", "1", validation, validation, test, ("value",), "y"
        )
    incompatible = ExperimentDatasetPartition(
        "validation", (2,), ((2,),), (2,), ("other",)
    )
    with pytest.raises(ValueError, match="same feature_names"):
        PreparedExperimentDataset(
            "data", "1", train, incompatible, test, ("value",), "y"
        )
    with pytest.raises(ValueError, match="top-level"):
        PreparedExperimentDataset("data", "1", train, validation, test, ("x",), "y")


def test_dataset_rejects_overlapping_partition_identifiers():
    with pytest.raises(ValueError, match="overlap"):
        PreparedExperimentDataset(
            "data",
            "1",
            partition("train", 1),
            partition("validation", 1),
            partition("test", 3),
            ("value",),
            "y",
        )


def test_prepare_rejects_missing_and_undeclared_features(split):
    missing = DatasetRecord(1, {"first": 1}, 1)
    extra = DatasetRecord(1, {"first": 1, "second": 2, "third": 3}, 1)
    for invalid_record in (missing, extra):
        invalid_split = TemporalDatasetSplit(
            "data",
            "1",
            (invalid_record,),
            split.validation,
            split.test,
            ("first", "second"),
            "y",
            {},
        )
        with pytest.raises(ValueError, match="exactly"):
            ExperimentDatasetPreparer().prepare(invalid_split)


def test_prepare_rejects_duplicate_or_overlapping_identifiers(split):
    duplicate = TemporalDatasetSplit(
        "data",
        "1",
        (record(1, 1, 2), record(1, 3, 4)),
        split.validation,
        split.test,
        ("first", "second"),
        "y",
        {},
    )
    overlap = TemporalDatasetSplit(
        "data",
        "1",
        (record(3, 1, 2),),
        split.validation,
        split.test,
        ("first", "second"),
        "y",
        {},
    )
    with pytest.raises(ValueError, match="unique"):
        ExperimentDatasetPreparer().prepare(duplicate)
    with pytest.raises(ValueError, match="overlap"):
        ExperimentDatasetPreparer().prepare(overlap)


def test_prepare_rejects_non_split_values():
    with pytest.raises(TypeError, match="TemporalDatasetSplit"):
        ExperimentDatasetPreparer().prepare(object())


def test_public_exports_are_narrow_and_exact():
    from dataset import experiment_dataset

    assert experiment_dataset.__all__ == [
        "ExperimentDatasetPartition",
        "PreparedExperimentDataset",
        "ExperimentDatasetPreparer",
    ]
