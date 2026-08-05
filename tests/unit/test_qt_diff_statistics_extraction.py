"""Contract tests for deterministic Qt structural diff statistics."""

from dataclasses import FrozenInstanceError

import pytest

import extraction.qt_diff_statistics_extraction as module
from extraction.qt_diff_extraction import QtFileChangeRecord
from extraction.qt_diff_statistics_extraction import (
    QtDiffStatisticsExtractor,
    QtDiffStatisticsSpecification,
)

SHA1 = "1" * 40
DIGEST = "2" * 64
CANONICAL = "https://code.qt.io/qt/qtbase.git"


def specification(**changes):
    values = {
        "repository_name": "qtbase",
        "canonical_repository_url": CANONICAL,
        "repository_revision": SHA1,
        "diff_artifact_digest": DIGEST,
        "extraction_policy_version": "1.0.0",
    }
    values.update(changes)
    return QtDiffStatisticsSpecification(**values)


def change(kind="modified", path="b.txt", **changes):
    old = None if kind == "added" else path
    new = None if kind == "deleted" else path
    values = {
        "commit_identifier": SHA1,
        "change_type": kind,
        "old_path": old,
        "new_path": new,
        "path": path,
        "is_binary": False,
        "additions": 2,
        "deletions": 1,
        "old_blob_identifier": None if kind == "added" else "3" * 40,
        "new_blob_identifier": None if kind == "deleted" else "4" * 40,
        "old_file_mode": None if kind == "added" else "100644",
        "new_file_mode": None if kind == "deleted" else "100644",
        "similarity_percent": None,
    }
    values.update(changes)
    return QtFileChangeRecord(**values)


def test_exact_public_api_and_acquisition_only_language() -> None:
    assert module.__all__ == [
        "QtDiffStatisticsSpecification",
        "QtFileDiffStatistics",
        "QtCommitDiffStatistics",
        "QtDiffStatisticsExtractionResult",
        "QtDiffStatisticsExtractor",
    ]
    assert not hasattr(QtDiffStatisticsExtractor, "run")
    assert not any(
        word in module.__all__ for word in ("Feature", "Dataset", "Model", "Label")
    )


def test_specification_is_immutable_detached_and_policy_controlled() -> None:
    source = {"purpose": ["structural"]}
    value = specification(metadata=source)
    source["purpose"].append("changed")
    assert value.to_dict()["metadata"] == {"purpose": ["structural"]}
    assert not hasattr(value, "__dict__")
    with pytest.raises(FrozenInstanceError):
        value.repository_name = "other"  # type: ignore[misc]
    for name in module._POLICIES:
        with pytest.raises(ValueError):
            specification(**{name: "caller-choice"})


@pytest.mark.parametrize(
    "metadata", [{"timestamp": "now"}, {"local_path": "/tmp/x"}, {"label": 1}]
)
def test_metadata_excludes_nondeterministic_and_downstream_fields(metadata) -> None:
    with pytest.raises(ValueError):
        specification(metadata=metadata)


def test_empty_diff_statistics() -> None:
    record = QtDiffStatisticsExtractor._statistics(SHA1, ())
    assert (
        record.files_changed
        == record.insertions
        == record.deletions
        == record.total_churn
        == 0
    )
    assert record.file_statistics == ()
    assert not record.has_binary_files


def test_all_structural_change_kinds_and_patch_statistics() -> None:
    records = (
        change("added", "a.txt", additions=4, deletions=0),
        change("copied", "c.txt", old_path="source.txt", similarity_percent=90),
        change("deleted", "d.txt", additions=0, deletions=3),
        change("modified", "m.txt"),
        change("renamed", "r-new.txt", old_path="r-old.txt", similarity_percent=100),
        change("type-changed", "t.txt"),
    )
    result = QtDiffStatisticsExtractor._statistics(SHA1, records)
    assert (
        result.files_added,
        result.files_removed,
        result.files_renamed,
        result.files_copied,
    ) == (1, 1, 1, 1)
    assert (result.files_modified, result.files_type_changed, result.files_changed) == (
        1,
        1,
        6,
    )
    assert (result.insertions, result.deletions, result.total_churn) == (12, 7, 19)


def test_binary_marker_preserves_null_counts() -> None:
    binary = change(
        "added",
        "asset.bin",
        is_binary=True,
        additions=None,
        deletions=None,
    )
    result = QtDiffStatisticsExtractor._statistics(SHA1, (binary,))
    assert result.binary_files == 1 and result.has_binary_files
    assert result.insertions == result.deletions == result.total_churn == 0
    assert result.file_statistics[0].total_churn is None


def test_multiple_files_preserve_canonical_order_and_repeatability() -> None:
    changes = (change("added", "a.txt"), change("modified", "z.txt"))
    one = QtDiffStatisticsExtractor._statistics(SHA1, changes)
    two = QtDiffStatisticsExtractor._statistics(SHA1, changes)
    assert one == two
    assert tuple(item.path for item in one.file_statistics) == ("a.txt", "z.txt")
    with pytest.raises(FrozenInstanceError):
        one.files_changed = 3  # type: ignore[misc]
    with pytest.raises(ValueError, match="ordering"):
        QtDiffStatisticsExtractor._statistics(SHA1, tuple(reversed(changes)))
