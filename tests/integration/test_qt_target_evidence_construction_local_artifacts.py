"""Offline integration tests for Qt target-evidence construction."""

import dataclasses
import hashlib

import extraction.qt_commit_extraction as commit_module
import extraction.qt_commit_issue_linking as link_module
from dataset.qt_target_evidence_construction import (
    QtTargetEvidenceConstructor,
    QtTargetEvidenceSpecification,
)
from dataset.scientific_builder_contracts import ScientificArtifactReference
from extraction.qt_commit_issue_linking import (
    QtCommitIssueLink,
    QtCommitIssueLinkingResult,
)
from tests.unit.test_qt_target_evidence_construction import _bundle


def _expanded_bundle():
    specification, commits, issues, links = _bundle()
    commit_type = type(commits.records[0])
    extra_commits = tuple(
        commit_type(
            character * 40,
            (),
            "Unicode Author",
            "author@example.invalid",
            f"2024-01-0{index}T00:00:00+00:00",
            "Committer",
            "committer@example.invalid",
            f"2024-01-0{index}T00:00:00+00:00",
            message,
        )
        for index, (character, message) in enumerate(
            (("b", "Task-number: QTBUG-2"), ("c", "QTBUG-3"), ("d", "no links")),
            start=4,
        )
    )
    records = commits.records + extra_commits
    reachable_history_digest = hashlib.sha256(
        commit_module._canonical_bytes(
            {"reachable_commit_ids": tuple(item.commit_id for item in records)}
        )
    ).hexdigest()
    commit_payload = {
        "schema_version": "1.0.0",
        "artifact_role": "commit-artifact",
        "source_repository": "qtbase",
        "source_revision": "a" * 40,
        "source_snapshot_digest": "b" * 64,
        "object_hash_algorithm": "sha1",
        "ordering_policy": commits.ordering_policy,
        "observation_window_start": commits.specification.observation_window_start,
        "observation_window_end": commits.specification.observation_window_end,
        "reachable_historical_commit_count": len(records),
        "pre_window_historical_commit_count": 0,
        "reachable_history_digest": reachable_history_digest,
        "records": records,
    }
    artifact = ScientificArtifactReference(
        commits.artifact.artifact_name,
        commits.artifact.artifact_role,
        commits.artifact.repository_relative_path,
        hashlib.sha256(commit_module._canonical_bytes(commit_payload)).hexdigest(),
        commits.artifact.schema_version,
        len(records),
    )
    commits = dataclasses.replace(
        commits,
        records=records,
        artifact=artifact,
        reachable_historical_commit_count=len(records),
        reachable_history_digest=reachable_history_digest,
    )
    issue_factory = __import__(
        "tests.unit.test_qt_target_evidence_construction", fromlist=["_issue"]
    )._issue
    new_issues = (
        issue_factory("QTBUG-2", "Task", "2024-01-02T04:00:00-03:00"),
        issue_factory("QTBUG-3", "Improvement", "2024-01-02T05:00:00Z"),
    )
    issue_records = tuple(
        sorted(issues.issues + new_issues, key=lambda item: item.issue_identifier)
    )
    import extraction.qt_issue_extraction as issue_module

    issue_artifact = dataclasses.replace(
        issues.extraction_artifact,
        content_digest=issue_module._digest(
            issue_module._artifact_content(issues.specification, issue_records)
        ),
        record_count=3,
    )
    identity = issue_module._digest(
        {
            "artifact_content_digest": issue_artifact.content_digest,
            "canonical_issue_source": issues.specification.canonical_issue_source,
            "source_revision": issues.specification.source_revision,
            "source_artifact_digest": issues.specification.source_artifact_digest,
            "issue_schema_version": issues.specification.issue_schema_version,
            "extraction_policy_version": issues.specification.extraction_policy_version,
        }
    )
    issues = dataclasses.replace(
        issues,
        issues=issue_records,
        extraction_artifact=issue_artifact,
        extracted_issue_count=3,
        issue_type_counts={"Bug": 1, "Improvement": 1, "Task": 1},
        status_counts={"Closed": 3},
        resolved_issue_count=3,
        unresolved_issue_count=0,
        missing_resolved_timestamp_count=0,
        issue_identity_digest=identity,
    )
    raw_links = [
        ("c" * 40, "QTBUG-3", "plain", "commit-message:line:1"),
        ("a" * 40, "QTBUG-1", "fixes", "commit-message:line:2"),
        ("a" * 40, "QTBUG-1", "fixes", "commit-message:line:1"),
        ("b" * 40, "QTBUG-2", "task-number", "commit-message:line:1"),
        ("a" * 40, "QTBUG-1", "plain", "commit-message:line:3"),
    ]
    link_records = []
    for commit_id, issue_id, reference_type, location in raw_links:
        values = {
            "commit_revision": commit_id,
            "issue_identifier": issue_id,
            "reference_type": reference_type,
            "reference_location": location,
        }
        link_records.append(
            QtCommitIssueLink(**values, artifact_digest=link_module._digest(values))
        )
    link_records = tuple(
        sorted(
            set(link_records),
            key=lambda item: (
                item.commit_revision,
                item.issue_identifier,
                item.reference_type,
                item.reference_location,
            ),
        )
    )
    link_spec = dataclasses.replace(
        links.specification,
        commit_artifact_digest=artifact.content_digest,
        issue_artifact_digest=issue_artifact.content_digest,
    )
    links = QtCommitIssueLinkingResult(
        link_spec,
        link_records,
        link_module._digest(link_module._result_content(link_spec, link_records)),
    )
    specification = QtTargetEvidenceSpecification(
        "qtbase",
        artifact.content_digest,
        issue_artifact.content_digest,
        links.artifact_digest,
        "1.0.0",
    )
    return specification, commits, issues, links


def test_offline_multi_artifact_construction_is_repeatable_conservative_and_exact() -> (
    None
):
    bundle = _expanded_bundle()
    one = QtTargetEvidenceConstructor().construct(*bundle)
    two = QtTargetEvidenceConstructor().construct(*bundle)
    assert one == two
    assert one.evidence_record_count == 4
    assert one.observations_with_evidence_count == 3
    assert one.observations_without_evidence_count == 1
    assert one.supporting_evidence_count == 0
    assert one.non_supporting_evidence_count == 4
    assert one.unresolved_evidence_count == 0
    assert [record.observation_identifier for record in one.evidence_records] == sorted(
        record.observation_identifier for record in one.evidence_records
    )
    assert {
        record.metadata["source_native_issue_type"] for record in one.evidence_records
    } == {"Bug", "Task", "Improvement"}
    assert {
        record.metadata["link_reference_type"] for record in one.evidence_records
    } == {"fixes", "plain", "task-number"}
    fixes = next(
        record
        for record in one.evidence_records
        if record.metadata["link_reference_type"] == "fixes"
    )
    assert fixes.metadata["reference_locations"] == (
        "commit-message:line:1",
        "commit-message:line:2",
    )
    assert not any(record.supports_positive_label for record in one.evidence_records)
    assert not hasattr(one, "target_assignment")
    assert not hasattr(one, "feature_matrix")


def test_artifact_commit_issue_and_scientific_evidence_mismatches_are_rejected() -> (
    None
):
    specification, commits, issues, links = _expanded_bundle()
    constructor = QtTargetEvidenceConstructor()
    for replacement in (
        dataclasses.replace(specification, linking_artifact_digest="f" * 64),
        dataclasses.replace(specification, commit_artifact_digest="f" * 64),
        dataclasses.replace(specification, issue_artifact_digest="f" * 64),
    ):
        import pytest

        with pytest.raises(ValueError):
            constructor.construct(replacement, commits, issues, links)
    changed = QtTargetEvidenceConstructor().construct(*_bundle("Task"))
    original = QtTargetEvidenceConstructor().construct(*_bundle("Bug"))
    assert changed.evidence_identity_digest != original.evidence_identity_digest
