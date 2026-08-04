"""Tests for deterministic framework-neutral model input building."""

from dataclasses import FrozenInstanceError

import pytest

from dataset.experiment_dataset import (
    ExperimentDatasetPartition,
    PreparedExperimentDataset,
)
from dataset.model_input import (
    ModelInputBuilder,
    ModelPartitionInput,
    PreparedModelInput,
)


def partition(name: str, identifiers: tuple[int, ...]) -> ExperimentDatasetPartition:
    rows = tuple(([identifier], f"value-{identifier}") for identifier in identifiers)
    targets = tuple(f"target-{identifier}" for identifier in identifiers)
    return ExperimentDatasetPartition(
        name,
        identifiers,
        rows,
        targets,
        ("second", "first"),
        {"partition": name, "nested": [len(identifiers)]},
    )


@pytest.fixture
def prepared() -> PreparedExperimentDataset:
    return PreparedExperimentDataset(
        "example",
        "1.0",
        partition("train", (2, 1)),
        partition("validation", (4, 3)),
        partition("test", (6, 5)),
        ("second", "first"),
        "outcome",
        {"source": {"tags": ["stable"]}},
    )


def model_partition(name: str, identifier: int) -> ModelPartitionInput:
    return ModelPartitionInput(
        name, (identifier,), ((identifier,),), (identifier,), ("value",)
    )


def test_build_preserves_all_ordering_values_and_counts(prepared):
    result = ModelInputBuilder().build(prepared)

    assert result.train.identifiers == (2, 1)
    assert result.train.X == (((2,), "value-2"), ((1,), "value-1"))
    assert result.train.y == ("target-2", "target-1")
    assert result.feature_names == result.train.feature_names == ("second", "first")
    assert result.training_observation_count == 2
    assert result.validation_observation_count == 2
    assert result.test_observation_count == 2
    assert result.total_observation_count == 6
    assert result.feature_count == result.train.feature_count == 2


def test_build_preserves_dataset_and_partition_metadata(prepared):
    result = ModelInputBuilder().build(prepared)

    assert (result.dataset_name, result.dataset_version, result.target_name) == (
        "example",
        "1.0",
        "outcome",
    )
    assert result.metadata == prepared.metadata
    assert result.train.metadata == prepared.train.metadata


def test_outputs_are_immutable_and_detached(prepared):
    result = ModelInputBuilder().build(prepared)

    with pytest.raises(FrozenInstanceError):
        result.dataset_name = "changed"
    with pytest.raises(TypeError):
        result.metadata["new"] = True
    with pytest.raises(TypeError):
        result.train.metadata["new"] = True
    assert result.train.X is not prepared.train.features
    assert result.train.X[0] is not prepared.train.features[0]
    assert result.metadata is not prepared.metadata
    assert result.train.metadata is not prepared.train.metadata


def test_to_dict_is_deterministic_mutable_and_detached(prepared):
    result = ModelInputBuilder().build(prepared)
    first = result.to_dict()
    second = result.to_dict()

    assert first == second
    first["metadata"]["source"]["tags"].append("changed")
    first["train"]["X"][0][0].append(99)
    assert result.to_dict() == second


def test_repeated_builds_are_equal(prepared):
    builder = ModelInputBuilder()
    assert builder.build(prepared) == builder.build(prepared)
    assert builder.builder_name == "model-input"


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
def test_partition_rejects_malformed_inputs(arguments, error):
    with pytest.raises(error):
        ModelPartitionInput(*arguments)


def test_partition_rejects_misalignment_duplicates_and_bad_widths():
    with pytest.raises(ValueError, match="align"):
        ModelPartitionInput("train", (1, 2), ((1,),), (1, 2), ("x",))
    with pytest.raises(ValueError, match="unique"):
        ModelPartitionInput("train", (1, 1), ((1,), (2,)), (1, 2), ("x",))
    with pytest.raises(ValueError, match="unique"):
        ModelPartitionInput("train", (1,), ((1, 2),), (1,), ("x", "x"))
    with pytest.raises(ValueError, match="match"):
        ModelPartitionInput("train", (1,), ((1, 2),), (1,), ("x",))


def test_prepared_input_rejects_wrong_partitions_and_schemas():
    train = model_partition("train", 1)
    validation = model_partition("validation", 2)
    test = model_partition("test", 3)
    with pytest.raises(TypeError, match="ModelPartitionInput"):
        PreparedModelInput("data", "1", object(), validation, test, ("value",), "y")
    with pytest.raises(ValueError, match="partition names"):
        PreparedModelInput("data", "1", validation, validation, test, ("value",), "y")
    incompatible = ModelPartitionInput("validation", (2,), ((2,),), (2,), ("other",))
    with pytest.raises(ValueError, match="same feature_names"):
        PreparedModelInput("data", "1", train, incompatible, test, ("value",), "y")
    scoped = PreparedModelInput(
        "data",
        "1",
        train,
        model_partition("validation", 1),
        test,
        ("value",),
        "y",
    )
    assert scoped.train.identifiers == scoped.validation.identifiers


def test_builder_rejects_non_prepared_dataset():
    with pytest.raises(TypeError, match="PreparedExperimentDataset"):
        ModelInputBuilder().build(object())


def test_public_exports_are_narrow_and_exact():
    from dataset import model_input

    assert model_input.__all__ == [
        "ModelPartitionInput",
        "PreparedModelInput",
        "ModelInputBuilder",
    ]
