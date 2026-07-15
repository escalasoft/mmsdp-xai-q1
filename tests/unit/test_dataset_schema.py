"""Unit tests for implementation-independent dataset contracts."""

from datetime import UTC, datetime
from pathlib import Path

from dataset import (
    DatasetArtifact,
    DatasetContract,
    DatasetSplit,
    DatasetStage,
)


def test_dataset_enums_define_approved_lifecycle_values() -> None:
    assert [stage.value for stage in DatasetStage] == ["raw", "interim", "processed"]
    assert [split.value for split in DatasetSplit] == [
        "train",
        "validation",
        "test",
    ]


def test_dataset_artifact_preserves_supplied_metadata() -> None:
    created_at = datetime(2026, 1, 1, tzinfo=UTC)
    artifact = DatasetArtifact(
        path=Path("data/processed/example.csv"),
        stage=DatasetStage.PROCESSED,
        dataset_version="caller-supplied",
        source_snapshot="caller-supplied",
        checksum="caller-supplied",
        created_at=created_at,
        row_count=2,
        column_names=("record_key", "outcome"),
    )

    assert artifact.created_at is created_at
    assert artifact.column_names == ("record_key", "outcome")


def test_dataset_contract_does_not_freeze_column_names() -> None:
    contract = DatasetContract(
        required_columns=("arbitrary_key",),
        optional_columns=("arbitrary_metadata",),
        primary_key="arbitrary_key",
    )

    assert contract.target_column is None
    assert contract.timestamp_column is None
