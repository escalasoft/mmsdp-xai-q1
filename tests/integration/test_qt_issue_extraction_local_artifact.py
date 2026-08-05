"""Offline integration tests for the versioned local issue artifact adapter."""

import hashlib
import json
import socket
from pathlib import Path

import pytest

from extraction.qt_issue_extraction import (
    QtIssueExtractionSpecification,
    QtIssueExtractor,
)

FIXTURE_JSON_SHA256 = "2cca9b139bd789d663314486a97d7d9499b03516033d95f7d20ddb332cc25ea6"


def source_records():
    common = {
        "project_identifier": "fixture-qtbase",
        "resolution": None,
        "priority": None,
        "description": None,
        "reporter_identifier": None,
        "assignee_identifier": None,
        "component": None,
        "version": None,
        "fix_versions": [],
        "metadata": {"source_scope": "offline-fixture"},
    }
    return [
        {
            **common,
            "issue_identifier": "QT-FIXTURE-30",
            "issue_type": "Improvement",
            "status": "Open",
            "created_timestamp": None,
            "updated_timestamp": None,
            "resolved_timestamp": None,
            "summary": "Mejora con Unicode: café λ",
        },
        {
            **common,
            "issue_identifier": "QT-FIXTURE-10",
            "issue_type": "Bug",
            "status": "Closed",
            "resolution": "Fixed",
            "created_timestamp": "2024-01-01T02:00:00+02:00",
            "updated_timestamp": "2024-01-02T03:00:00+02:00",
            "resolved_timestamp": "2024-01-02T00:00:00Z",
            "summary": "Render failure — résumé",
            "description": "Raw defect-like source text",
            "fix_versions": ["6.7", "6.8"],
        },
        {
            **common,
            "issue_identifier": "QT-FIXTURE-20",
            "issue_type": "Task",
            "status": "In Progress",
            "created_timestamp": "2023-12-31T19:00:00-05:00",
            "updated_timestamp": "2024-01-01T20:00:00-05:00",
            "resolved_timestamp": None,
            "summary": "Documentation task",
        },
    ]


def write_artifact(tmp_path: Path, records=None, extension="json"):
    records = source_records() if records is None else records
    if extension == "json":
        data = json.dumps(
            records, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
    else:
        data = (
            "\n".join(
                json.dumps(
                    item, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                )
                for item in records
            )
        ).encode()
    path = tmp_path / f"issues.{extension}"
    path.write_bytes(data)
    return path, hashlib.sha256(data).hexdigest()


def specification(digest, **changes):
    values = {
        "project_name": "qtbase",
        "canonical_issue_source": "urn:fixture:qtbase-issues",
        "source_revision": "fixture-export-v1",
        "source_artifact_digest": digest,
        "project_identifier": "fixture-qtbase",
        "issue_schema_version": "fixture-schema-v1",
        "extraction_policy_version": "1.0.0",
    }
    values.update(changes)
    return QtIssueExtractionSpecification(**values)


def test_repeated_offline_extraction_is_canonical_and_semantic(tmp_path, monkeypatch):
    path, digest = write_artifact(tmp_path)
    assert digest == FIXTURE_JSON_SHA256
    monkeypatch.setattr(
        socket, "create_connection", lambda *a, **k: pytest.fail("network")
    )
    one = QtIssueExtractor().extract(specification(digest), path)
    two = QtIssueExtractor().extract(specification(digest), path)
    assert one == two
    assert [item.issue_identifier for item in one.issues] == [
        "QT-FIXTURE-10",
        "QT-FIXTURE-20",
        "QT-FIXTURE-30",
    ]
    assert [item.issue_type for item in one.issues] == ["Bug", "Task", "Improvement"]
    assert one.issues[0].created_timestamp == "2024-01-01T00:00:00Z"
    assert one.issues[1].created_timestamp == "2024-01-01T00:00:00Z"
    assert one.issues[2].created_timestamp is None
    assert "café λ" in one.issues[2].summary
    assert one.issue_type_counts == {"Bug": 1, "Improvement": 1, "Task": 1}
    assert one.status_counts == {"Closed": 1, "In Progress": 1, "Open": 1}
    assert (one.resolved_issue_count, one.unresolved_issue_count) == (1, 2)
    assert (
        one.missing_created_timestamp_count,
        one.missing_resolved_timestamp_count,
    ) == (1, 2)
    public = str(one.to_dict()) + repr(one)
    assert str(tmp_path) not in public
    assert "runtime_timestamp" not in public
    assert "commit_link" not in public and "target_label" not in public


def test_jsonl_is_supported_and_content_change_changes_identity(tmp_path):
    path, digest = write_artifact(tmp_path, extension="jsonl")
    one = QtIssueExtractor().extract(specification(digest), path)
    changed = source_records()
    changed[0] = {**changed[0], "summary": "Scientifically changed"}
    other_path = tmp_path / "changed.jsonl"
    data = (
        "\n".join(
            json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            for item in changed
        )
    ).encode()
    other_path.write_bytes(data)
    two = QtIssueExtractor().extract(
        specification(hashlib.sha256(data).hexdigest()), other_path
    )
    assert (
        one.extraction_artifact.content_digest != two.extraction_artifact.content_digest
    )
    assert one.issue_identity_digest != two.issue_identity_digest


def test_digest_mismatch_malformed_duplicate_and_paths_are_rejected(tmp_path):
    path, digest = write_artifact(tmp_path)
    with pytest.raises(RuntimeError, match="digest"):
        QtIssueExtractor().extract(specification("f" * 64), path)
    malformed = tmp_path / "malformed.json"
    malformed.write_text('[{"issue_identifier":', encoding="utf-8")
    with pytest.raises(RuntimeError, match="malformed"):
        QtIssueExtractor().extract(
            specification(hashlib.sha256(malformed.read_bytes()).hexdigest()), malformed
        )
    duplicates = source_records() + [{**source_records()[0], "summary": "conflict"}]
    duplicate_path, duplicate_digest = write_artifact(tmp_path, duplicates)
    with pytest.raises(RuntimeError, match="conflicting duplicate"):
        QtIssueExtractor().extract(specification(duplicate_digest), duplicate_path)
    with pytest.raises(ValueError, match="regular file"):
        QtIssueExtractor().extract(specification(digest), tmp_path)
    unsupported = tmp_path / "issues.txt"
    unsupported.write_bytes(path.read_bytes())
    with pytest.raises(ValueError, match="extension"):
        QtIssueExtractor().extract(specification(digest), unsupported)


def test_unknown_fields_and_wrong_project_are_not_silently_repaired(tmp_path):
    values = source_records()
    values[0] = {**values[0], "derived_bug_label": True}
    path, digest = write_artifact(tmp_path, values)
    with pytest.raises(RuntimeError, match="malformed"):
        QtIssueExtractor().extract(specification(digest), path)
    values = source_records()
    values[0] = {**values[0], "project_identifier": "another-project"}
    path, digest = write_artifact(tmp_path, values)
    with pytest.raises(RuntimeError, match="malformed"):
        QtIssueExtractor().extract(specification(digest), path)
