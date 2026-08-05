"""Contract tests for reproducible Qt diff extraction."""

from dataclasses import FrozenInstanceError

import pytest

import extraction.qt_diff_extraction as module
from extraction.qt_diff_extraction import (
    QtCommitDiffRecord,
    QtDiffExtractionSpecification,
    QtDiffExtractor,
    QtFileChangeRecord,
)

SHA1 = "1" * 40
EMPTY = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
DIGEST = "2" * 64
CANONICAL = "https://code.qt.io/qt/qtbase.git"


def specification(**changes):
    values = {
        "repository_name": "qtbase",
        "canonical_repository_url": CANONICAL,
        "repository_revision": SHA1,
        "commit_artifact_digest": DIGEST,
        "extraction_policy_version": "1.0.0",
    }
    values.update(changes)
    return QtDiffExtractionSpecification(**values)


def file_record(**changes):
    values = {
        "commit_identifier": SHA1,
        "change_type": "modified",
        "old_path": "src/a.cpp",
        "new_path": "src/a.cpp",
        "path": "src/a.cpp",
        "is_binary": False,
        "additions": 2,
        "deletions": 1,
        "old_blob_identifier": "3" * 40,
        "new_blob_identifier": "4" * 40,
        "old_file_mode": "100644",
        "new_file_mode": "100644",
        "similarity_percent": None,
    }
    values.update(changes)
    return QtFileChangeRecord(**values)


def commit_record(changes):
    ordered = tuple(sorted(changes, key=module._file_order))
    content = module._record_content(SHA1, EMPTY, (), True, False, ordered)
    return QtCommitDiffRecord(
        SHA1,
        EMPTY,
        (),
        True,
        False,
        ordered,
        len(ordered),
        sum(not item.is_binary for item in ordered),
        sum(item.is_binary for item in ordered),
        sum(item.additions or 0 for item in ordered if not item.is_binary),
        sum(item.deletions or 0 for item in ordered if not item.is_binary),
        module._digest(content),
    )


def test_exact_public_api_and_no_generic_git_api() -> None:
    assert module.__all__ == [
        "QtDiffExtractionSpecification",
        "QtFileChangeRecord",
        "QtCommitDiffRecord",
        "QtDiffExtractionResult",
        "QtDiffExtractor",
    ]
    assert not hasattr(QtDiffExtractor, "run")
    assert not any(
        word in module.__all__
        for word in ("Issue", "Target", "Feature", "Dataset", "Model", "Experiment")
    )


def test_specification_is_frozen_slotted_detached_and_deterministic() -> None:
    source = {"purpose": ["raw", {"stage": "diff"}]}
    one = specification(metadata=source)
    source["purpose"].append("changed")
    assert (
        one.to_dict()
        == specification(metadata={"purpose": ["raw", {"stage": "diff"}]}).to_dict()
    )
    assert not hasattr(one, "__dict__")
    with pytest.raises(FrozenInstanceError):
        one.repository_name = "other"  # type: ignore[misc]


@pytest.mark.parametrize(
    "field,value",
    [
        ("repository_name", "other"),
        ("canonical_repository_url", "https://example.invalid/x"),
        ("repository_revision", "abc"),
        ("commit_artifact_digest", "abc"),
        ("allowed_hash_algorithms", ("sha1",)),
    ],
)
def test_specification_rejects_invalid_identity(field, value) -> None:
    with pytest.raises(ValueError):
        specification(**{field: value})


@pytest.mark.parametrize("field", list(module._POLICIES))
def test_specification_rejects_uncontrolled_policies(field) -> None:
    with pytest.raises(ValueError):
        specification(**{field: "caller-choice"})


@pytest.mark.parametrize(
    "metadata",
    [
        {"local_path": "/tmp/x"},
        {"runtime_timestamp": "now"},
        {"label": 1},
        {"issue_link": "QT-1"},
        {"nested": {"username": "me"}},
    ],
)
def test_metadata_rejects_sensitive_or_semantic_fields(metadata) -> None:
    with pytest.raises(ValueError):
        specification(metadata=metadata)


@pytest.mark.parametrize("path", ["/tmp/a", "../a", "a/../b", r"a\\b", "", "."])
def test_paths_must_be_repository_relative_posix(path) -> None:
    with pytest.raises(ValueError):
        file_record(old_path=path, new_path=path, path=path)


def test_file_change_invariants_and_binary_null_policy() -> None:
    assert (
        file_record(change_type="added", old_path=None, new_path="a", path="a").path
        == "a"
    )
    assert (
        file_record(change_type="deleted", old_path="a", new_path=None, path="a").path
        == "a"
    )
    renamed = file_record(
        change_type="renamed",
        old_path="a",
        new_path="b",
        path="b",
        similarity_percent=80,
    )
    assert renamed.similarity_percent == 80
    copied = file_record(
        change_type="copied",
        old_path="a",
        new_path="b",
        path="b",
        similarity_percent=100,
    )
    assert copied.change_type == "copied"
    binary = file_record(is_binary=True, additions=None, deletions=None)
    assert binary.additions is None and binary.deletions is None
    with pytest.raises(ValueError):
        file_record(additions=True)
    with pytest.raises(ValueError):
        file_record(old_blob_identifier="abc")
    with pytest.raises(ValueError):
        file_record(old_file_mode="777")
    with pytest.raises(ValueError):
        file_record(
            change_type="renamed",
            old_path="a",
            new_path="b",
            path="b",
            similarity_percent=101,
        )


def test_commit_record_order_aggregates_duplicates_and_metadata_independence() -> None:
    a = file_record()
    b = file_record(
        change_type="added",
        old_path=None,
        new_path="a.txt",
        path="a.txt",
        additions=1,
        deletions=0,
    )
    record = commit_record((b, a))
    assert tuple(item.path for item in record.file_changes) == ("a.txt", "src/a.cpp")
    assert (
        record.changed_file_count,
        record.text_file_count,
        record.total_additions,
    ) == (2, 2, 3)
    with pytest.raises(ValueError, match="duplicate"):
        commit_record((a, a))
    changed_metadata = QtCommitDiffRecord(
        *[
            getattr(record, field.name)
            for field in module.fields(record)
            if field.name != "metadata"
        ],
        metadata={"note": "descriptive"},
    )
    assert changed_metadata.record_digest == record.record_digest


def test_constructor_with_placeholders_performs_no_subprocess(monkeypatch) -> None:
    spec = specification(
        repository_revision=module._PLACEHOLDER_REVISION,
        commit_artifact_digest=module._PLACEHOLDER_DIGEST,
    )
    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda *args, **kwargs: pytest.fail("subprocess executed"),
    )
    assert spec.repository_revision == module._PLACEHOLDER_REVISION
