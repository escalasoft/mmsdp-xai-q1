"""Unit tests for immutable preprocessing schema contracts."""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from pathlib import Path

import pytest

from preprocessing.schema import (
    FeatureTable,
    InvalidFeatureTableError,
    InvalidManifestError,
    InvalidTemporalSplitError,
    MergedFeatureRecord,
    PreprocessingManifest,
    PreprocessingSchemaError,
    PreprocessingSplit,
    TemporalSplit,
)


def test_preprocessing_split_values() -> None:
    assert [split.value for split in PreprocessingSplit] == [
        "train",
        "validation",
        "test",
    ]


def test_feature_table_is_immutable_and_defensive() -> None:
    columns = ["commit_key", "caller_feature"]
    record = {"commit_key": "abc", "caller_feature": [1, 2]}
    table = FeatureTable("caller_modality", "commit_key", columns, [record])

    columns.append("later")
    record["commit_key"] = "changed"
    record["caller_feature"].append(3)

    assert table.column_names == ("commit_key", "caller_feature")
    assert table.records[0]["commit_key"] == "abc"
    assert table.records[0]["caller_feature"] == (1, 2)
    with pytest.raises(TypeError):
        table.records[0]["commit_key"] = "blocked"  # type: ignore[index]
    with pytest.raises(FrozenInstanceError):
        table.modality = "blocked"  # type: ignore[misc]


@pytest.mark.parametrize("modality", ["", "   "])
def test_feature_table_rejects_empty_modality(modality: str) -> None:
    with pytest.raises(InvalidFeatureTableError):
        FeatureTable(modality, "key", ("key",), ())


def test_feature_table_rejects_empty_primary_key_and_invalid_columns() -> None:
    with pytest.raises(InvalidFeatureTableError):
        FeatureTable("custom", "", ("key",), ())
    with pytest.raises(InvalidFeatureTableError):
        FeatureTable("custom", "key", (), ())
    with pytest.raises(InvalidFeatureTableError):
        FeatureTable("custom", "key", ("key", "key"), ())
    with pytest.raises(InvalidFeatureTableError):
        FeatureTable("custom", "key", ("key",), (object(),))  # type: ignore[arg-type]


def test_merged_feature_record_preserves_values_defensively() -> None:
    key_value = ["caller", "key"]
    values = {"custom": {"nested": [1]}}
    modalities = ["custom_one", "custom_two"]
    record = MergedFeatureRecord("commit_key", key_value, values, modalities)

    key_value.append("changed")
    values["custom"]["nested"].append(2)  # type: ignore[index, union-attr]
    modalities.append("changed")

    assert record.primary_key_value == ("caller", "key")
    assert record.values["custom"]["nested"] == (1,)  # type: ignore[index]
    assert record.source_modalities == ("custom_one", "custom_two")
    with pytest.raises(TypeError):
        record.values["custom"] = "blocked"  # type: ignore[index]
    with pytest.raises(FrozenInstanceError):
        record.primary_key = "blocked"  # type: ignore[misc]


def test_merged_feature_record_rejects_structural_errors() -> None:
    with pytest.raises(PreprocessingSchemaError):
        MergedFeatureRecord("", "value", {}, ())
    with pytest.raises(PreprocessingSchemaError):
        MergedFeatureRecord("key", "value", {}, ("same", "same"))


def test_temporal_split_constructs_empty_collections_and_freezes_records() -> None:
    train_record = {"when": datetime(2026, 1, 1, tzinfo=UTC), "items": [1]}
    split = TemporalSplit(
        [train_record],
        [],
        [],
        "caller_timestamp",
        datetime(2026, 1, 31, tzinfo=UTC),
        datetime(2026, 2, 28, tzinfo=UTC),
    )
    train_record["items"].append(2)

    assert split.train_records[0]["items"] == (1,)
    assert split.validation_records == ()
    assert split.test_records == ()
    with pytest.raises(FrozenInstanceError):
        split.timestamp_column = "blocked"  # type: ignore[misc]


def test_temporal_split_rejects_naive_and_reversed_boundaries() -> None:
    aware = datetime(2026, 2, 1, tzinfo=UTC)
    with pytest.raises(InvalidTemporalSplitError):
        TemporalSplit((), (), (), "timestamp", datetime(2026, 1, 1), aware)
    with pytest.raises(InvalidTemporalSplitError):
        TemporalSplit((), (), (), "timestamp", aware, datetime(2026, 3, 1))
    with pytest.raises(InvalidTemporalSplitError):
        TemporalSplit(
            (),
            (),
            (),
            "timestamp",
            datetime(2026, 3, 1, tzinfo=UTC),
            aware,
        )
    with pytest.raises(InvalidTemporalSplitError):
        TemporalSplit((), (), (), "", aware, aware)


def test_manifest_constructs_and_freezes_supplied_containers() -> None:
    paths = [Path("caller-output.csv")]
    checksums = {"caller-output.csv": "a" * 64}
    configuration = {"caller_key": {"options": [1, 2]}}
    manifest = PreprocessingManifest(
        datetime(2026, 1, 1, tzinfo=UTC),
        2,
        1,
        paths,
        checksums,
        configuration,
    )

    paths.append(Path("later.csv"))
    checksums["caller-output.csv"] = "b" * 64
    configuration["caller_key"]["options"].append(3)  # type: ignore[index, union-attr]

    assert manifest.output_paths == (Path("caller-output.csv"),)
    assert manifest.checksums["caller-output.csv"] == "a" * 64
    assert manifest.configuration_summary["caller_key"]["options"] == (1, 2)  # type: ignore[index]
    with pytest.raises(TypeError):
        manifest.checksums["new"] = "c" * 64  # type: ignore[index]
    with pytest.raises(FrozenInstanceError):
        manifest.input_record_count = 3  # type: ignore[misc]


@pytest.mark.parametrize("input_count, output_count", [(-1, 0), (0, -1)])
def test_manifest_rejects_negative_counts(input_count: int, output_count: int) -> None:
    with pytest.raises(InvalidManifestError):
        PreprocessingManifest(datetime.now(UTC), input_count, output_count, (), {}, {})


def test_manifest_rejects_output_count_greater_than_input_count() -> None:
    with pytest.raises(InvalidManifestError):
        PreprocessingManifest(datetime.now(UTC), 1, 2, (), {}, {})


@pytest.mark.parametrize(
    "checksums",
    [
        {"": "a" * 64},
        {"artifact": "a" * 63},
        {"artifact": "A" * 64},
        {"artifact": "g" * 64},
    ],
)
def test_manifest_rejects_empty_keys_and_malformed_checksums(
    checksums: dict[str, str],
) -> None:
    with pytest.raises(InvalidManifestError):
        PreprocessingManifest(datetime.now(UTC), 0, 0, (), checksums, {})
