"""Unit tests for deterministic preprocessing modality merging."""

from dataclasses import FrozenInstanceError

import pytest

from preprocessing.merger import (
    ConflictingSharedMetadataError,
    DuplicateModalityError,
    DuplicatePrimaryKeyError,
    IncompatiblePrimaryKeyError,
    MissingRequiredModalityError,
    merge_preprocessing_tables,
)
from preprocessing.schema import FeatureTable


def _table(
    modality: str,
    records: list[dict[str, object]],
    columns: tuple[str, ...] = ("id", "project", "value"),
) -> FeatureTable:
    return FeatureTable(modality, "id", columns, tuple(records))


def test_merge_is_deterministic_and_preserves_outer_join_records() -> None:
    text = _table(
        "text",
        [
            {"id": "b", "project": "p", "value": 20},
            {"id": "a", "project": "p", "value": 10},
        ],
    )
    code = _table(
        "code",
        [
            {"id": "c", "project": "p", "value": 3},
            {"id": "a", "project": "p", "value": 1},
        ],
    )

    merged = merge_preprocessing_tables(
        [text, code],
        required_modalities=("text", "code"),
        shared_metadata=("project",),
    )

    assert merged.primary_key == "id"
    assert merged.modalities == ("code", "text")
    assert [record.primary_key_value for record in merged.records] == ["a", "b", "c"]
    assert dict(merged.records[0].values) == {
        "code.value": 1,
        "project": "p",
        "text.value": 10,
    }
    assert merged.records[1].source_modalities == ("text",)
    assert merged.records[2].source_modalities == ("code",)


def test_merge_does_not_modify_inputs_and_returns_deeply_immutable_values() -> None:
    source = {"id": "a", "project": "p", "value": [1]}
    table = _table("code", [source])

    merged = merge_preprocessing_tables([table], required_modalities=("code",))
    source["value"].append(2)  # type: ignore[union-attr]

    assert merged.records[0].values["code.value"] == (1,)
    with pytest.raises(TypeError):
        merged.records[0].values["new"] = 1  # type: ignore[index]
    with pytest.raises(FrozenInstanceError):
        merged.records = ()  # type: ignore[misc]


def test_duplicate_primary_key_inside_modality_is_rejected() -> None:
    table = _table(
        "code",
        [
            {"id": "a", "project": "p", "value": 1},
            {"id": "a", "project": "p", "value": 2},
        ],
    )

    with pytest.raises(DuplicatePrimaryKeyError):
        merge_preprocessing_tables([table], required_modalities=("code",))


def test_missing_required_modality_is_rejected() -> None:
    table = _table("code", [{"id": "a", "project": "p", "value": 1}])

    with pytest.raises(MissingRequiredModalityError, match="text"):
        merge_preprocessing_tables([table], required_modalities=("code", "text"))


def test_conflicting_shared_metadata_is_rejected() -> None:
    code = _table("code", [{"id": "a", "project": "one", "value": 1}])
    text = _table("text", [{"id": "a", "project": "two", "value": 2}])

    with pytest.raises(ConflictingSharedMetadataError, match="project"):
        merge_preprocessing_tables(
            [code, text],
            required_modalities=("code", "text"),
            shared_metadata=("project",),
        )


def test_incompatible_primary_keys_are_rejected() -> None:
    code = _table("code", [{"id": "a", "project": "p", "value": 1}])
    text = FeatureTable(
        "text", "key", ("key", "project"), ({"key": "a", "project": "p"},)
    )

    with pytest.raises(IncompatiblePrimaryKeyError):
        merge_preprocessing_tables([code, text], required_modalities=("code", "text"))


def test_duplicate_modality_tables_are_rejected() -> None:
    first = _table("code", [{"id": "a", "project": "p", "value": 1}])
    second = _table("code", [{"id": "b", "project": "p", "value": 2}])

    with pytest.raises(DuplicateModalityError):
        merge_preprocessing_tables([first, second], required_modalities=("code",))
