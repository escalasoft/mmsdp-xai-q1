"""Offline integration tests for explicit Qt commit--issue provenance."""

import hashlib
import json

import pytest

from extraction.qt_commit_issue_linking import (
    QtCommitIssueLinker,
    QtCommitIssueLinkSpecification,
)


def artifact(path, records):
    raw = json.dumps(
        records, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def test_local_artifacts_link_only_existing_explicit_identifiers(tmp_path) -> None:
    commits = tmp_path / "commits.json"
    issues = tmp_path / "issues.json"
    commit_digest = artifact(
        commits,
        {
            "records": [
                {"commit_id": "c" * 40, "message": "Fixes: QTBUG-100"},
                {
                    "commit_id": "b" * 40,
                    "message": (
                        "QTBUG-300 and QTBUG-100\n"
                        "Pick-to: QTBUG-200 QTBUG-200\n"
                        "Task-number: QTBUG-999"
                    ),
                },
                {"commit_id": "a" * 40, "message": "No issue reference"},
            ]
        },
    )
    issue_digest = artifact(
        issues,
        {
            "issues": [
                {"issue_identifier": "QTBUG-200"},
                {"issue_identifier": "QTBUG-100"},
                {"issue_identifier": "QTBUG-300"},
            ]
        },
    )
    spec = QtCommitIssueLinkSpecification("1.0.0", commit_digest, issue_digest)
    one = QtCommitIssueLinker().link(spec, commits, issues)
    two = QtCommitIssueLinker().link(spec, commits, issues)
    assert one == two
    assert [
        (item.commit_revision, item.issue_identifier, item.reference_type)
        for item in one.links
    ] == [
        ("b" * 40, "QTBUG-100", "plain"),
        ("b" * 40, "QTBUG-200", "pick-to"),
        ("b" * 40, "QTBUG-300", "plain"),
        ("c" * 40, "QTBUG-100", "fixes"),
    ]
    assert len({item.artifact_digest for item in one.links}) == 4
    assert one.artifact_digest == two.artifact_digest
    assert "QTBUG-999" not in str(one.to_dict())
    assert not hasattr(one.links[0], "is_bug")
    assert not hasattr(one.links[0], "label")


def test_missing_commit_or_issue_artifact_and_digest_are_rejected(tmp_path) -> None:
    commits = tmp_path / "commits.json"
    issues = tmp_path / "issues.json"
    commit_digest = artifact(commits, [])
    issue_digest = artifact(issues, [])
    spec = QtCommitIssueLinkSpecification("1.0.0", commit_digest, issue_digest)
    assert QtCommitIssueLinker().link(spec, commits, issues).links == ()
    with pytest.raises(ValueError, match="commit_artifact_path"):
        QtCommitIssueLinker().link(spec, tmp_path / "missing.json", issues)
    with pytest.raises(ValueError, match="issue_artifact_path"):
        QtCommitIssueLinker().link(spec, commits, tmp_path / "missing.json")
    wrong = QtCommitIssueLinkSpecification("1.0.0", "f" * 64, issue_digest)
    with pytest.raises(RuntimeError, match="digest"):
        QtCommitIssueLinker().link(wrong, commits, issues)
