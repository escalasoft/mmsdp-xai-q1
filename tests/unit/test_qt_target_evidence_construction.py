"""Unit contracts for deterministic Qt target-evidence construction."""

import dataclasses
import hashlib
import inspect
import json

import pytest

import dataset.qt_target_evidence_construction as module
import extraction.qt_commit_extraction as commit_module
import extraction.qt_commit_issue_linking as link_module
import extraction.qt_issue_extraction as issue_module
from dataset.qt_target_evidence_construction import (
    QtTargetEvidenceConstructionResult,
    QtTargetEvidenceConstructor,
    QtTargetEvidenceSpecification,
)
from dataset.scientific_builder_contracts import (
    ScientificArtifactReference,
    ScientificArtifactRole,
    ScientificTargetEvidenceRecord,
)
from extraction.qt_commit_extraction import (
    QtCommitExtractionResult,
    QtCommitExtractionSpecification,
    ScientificCommitRecord,
)
from extraction.qt_commit_issue_linking import (
    QtCommitIssueLink,
    QtCommitIssueLinkingResult,
    QtCommitIssueLinkSpecification,
)
from extraction.qt_issue_extraction import (
    QtIssueExtractionResult,
    QtIssueExtractionSpecification,
    QtIssueRecord,
)


def _issue(identifier="QTBUG-1", issue_type="Bug", created="2024-01-02T03:04:05+02:00"):
    values = {
        "issue_identifier": identifier,
        "project_identifier": "fixture-qtbase",
        "issue_type": issue_type,
        "status": "Closed",
        "resolution": "Done",
        "priority": "P2",
        "created_timestamp": issue_module._timestamp(created, "created_timestamp"),
        "updated_timestamp": issue_module._timestamp(created, "updated_timestamp"),
        "resolved_timestamp": issue_module._timestamp(created, "resolved_timestamp"),
        "summary": "Résumé unrestricted text that must not be copied",
        "description": "Sensitive full issue description that must not be copied",
        "reporter_identifier": "source-user",
        "assignee_identifier": None,
        "component": "Core",
        "version": None,
        "fix_versions": (),
    }
    return QtIssueRecord(
        **values,
        source_record_digest=issue_module._digest(issue_module._record_content(values)),
    )


def _bundle(issue_type="Bug", metadata=None):
    commit = ScientificCommitRecord(
        commit_id="a" * 40,
        parent_ids=(),
        author_name="Author",
        author_email="author@example.invalid",
        authored_at="2024-01-03T00:00:00+00:00",
        committer_name="Committer",
        committer_email="committer@example.invalid",
        committed_at="2024-01-03T00:00:00+00:00",
        message="Fixes: QTBUG-1\nfull commit message must not be copied",
    )
    commit_spec = QtCommitExtractionSpecification(
        "1.0.0",
        observation_window_start="2024-01-01T00:00:00+00:00",
        observation_window_end="2024-01-07T00:00:00+00:00",
    )
    history_digest = hashlib.sha256(
        commit_module._canonical_bytes({"reachable_commit_ids": (commit.commit_id,)})
    ).hexdigest()
    commit_payload = {
        "schema_version": "1.0.0",
        "artifact_role": "commit-artifact",
        "source_repository": "qtbase",
        "source_revision": "a" * 40,
        "source_snapshot_digest": "b" * 64,
        "object_hash_algorithm": "sha1",
        "ordering_policy": commit_spec.ordering_policy,
        "observation_window_start": commit_spec.observation_window_start,
        "observation_window_end": commit_spec.observation_window_end,
        "reachable_historical_commit_count": 1,
        "pre_window_historical_commit_count": 0,
        "reachable_history_digest": history_digest,
        "records": (commit,),
    }
    commit_artifact = ScientificArtifactReference(
        "qtbase-commits",
        ScientificArtifactRole.COMMIT_ARTIFACT,
        commit_spec.artifact_repository_relative_path,
        hashlib.sha256(commit_module._canonical_bytes(commit_payload)).hexdigest(),
        "1.0.0",
        1,
    )
    commits = QtCommitExtractionResult(
        commit_spec,
        "a" * 40,
        "b" * 64,
        "sha1",
        (commit,),
        commit_artifact,
        commit_spec.ordering_policy,
        ("git:cat-file:completed",),
        1,
        0,
        history_digest,
    )
    issue = _issue(issue_type=issue_type)
    issue_spec = QtIssueExtractionSpecification(
        "qtbase",
        "urn:fixture:qtbase-issues",
        "fixture-export-v1",
        "c" * 64,
        "fixture-qtbase",
        "1.0.0",
        "1.0.0",
    )
    issue_content = issue_module._artifact_content(issue_spec, (issue,))
    issue_artifact = ScientificArtifactReference(
        "qtbase-issues",
        ScientificArtifactRole.ISSUE_ARTIFACT,
        "artifacts/qtbase/issues/fixture-export-v1/qt-issues.jsonl",
        issue_module._digest(issue_content),
        "1.0.0",
        1,
    )
    issue_identity = issue_module._digest(
        {
            "artifact_content_digest": issue_artifact.content_digest,
            "canonical_issue_source": issue_spec.canonical_issue_source,
            "source_revision": issue_spec.source_revision,
            "source_artifact_digest": issue_spec.source_artifact_digest,
            "issue_schema_version": issue_spec.issue_schema_version,
            "extraction_policy_version": issue_spec.extraction_policy_version,
        }
    )
    issues = QtIssueExtractionResult(
        issue_spec,
        (issue,),
        issue_artifact,
        1,
        {issue_type: 1},
        {"Closed": 1},
        1,
        0,
        0,
        0,
        issue_identity,
        ("local-artifact:sha256-verified", "parser:json:completed"),
    )
    link_values = {
        "commit_revision": "a" * 40,
        "issue_identifier": "QTBUG-1",
        "reference_type": "fixes",
        "reference_location": "commit-message:line:1",
    }
    link = QtCommitIssueLink(
        **link_values, artifact_digest=link_module._digest(link_values)
    )
    link_spec = QtCommitIssueLinkSpecification(
        "1.0.0", commit_artifact.content_digest, issue_artifact.content_digest
    )
    links = QtCommitIssueLinkingResult(
        link_spec,
        (link,),
        link_module._digest(link_module._result_content(link_spec, (link,))),
    )
    specification = QtTargetEvidenceSpecification(
        "qtbase",
        commit_artifact.content_digest,
        issue_artifact.content_digest,
        links.artifact_digest,
        "1.0.0",
        metadata=metadata or {},
    )
    return specification, commits, issues, links


def test_exact_api_frozen_slots_and_canonical_record_reuse() -> None:
    assert module.__all__ == [
        "QtTargetEvidenceSpecification",
        "QtTargetEvidenceConstructionResult",
        "QtTargetEvidenceConstructor",
    ]
    for contract in (QtTargetEvidenceSpecification, QtTargetEvidenceConstructionResult):
        assert contract.__dataclass_params__.frozen
        assert "__slots__" in contract.__dict__
    assert "QtTargetEvidenceRecord" not in vars(module)
    result = QtTargetEvidenceConstructor().construct(*_bundle())
    assert all(
        isinstance(item, ScientificTargetEvidenceRecord)
        for item in result.evidence_records
    )
    assert {
        name for name in dir(QtTargetEvidenceConstructor) if not name.startswith("_")
    } == {
        "construct",
        "constructor_name",
    }


def test_detachment_deterministic_dict_and_metadata_independent_identity() -> None:
    source = {"audit": ["one", {"note": "two"}]}
    one = QtTargetEvidenceConstructor().construct(*_bundle(metadata=source))
    source["audit"].append("changed")
    two = QtTargetEvidenceConstructor().construct(
        *_bundle(metadata={"different": "description"})
    )
    assert one.specification.to_dict()["metadata"] == {
        "audit": ["one", {"note": "two"}]
    }
    assert one.evidence_identity_digest == two.evidence_identity_digest
    assert one.evidence_artifact.content_digest == two.evidence_artifact.content_digest
    assert one.to_dict() == one.to_dict()
    with pytest.raises(TypeError):
        one.metadata["new"] = True


@pytest.mark.parametrize(
    "metadata",
    [
        {"target_label": 1},
        {"nested": {"feature_enabled": True}},
        {"prediction": "x"},
        {"probability": 0.5},
        {"bug_confidence": "high"},
        {"local_path": "/tmp/private"},
        {"runtime_timestamp": "now"},
        {"duration": 1},
        {"username": "person"},
        {"hostname": "machine"},
        {"credentials": "secret"},
        {"note": "object at 0x12345678"},
    ],
)
def test_metadata_rejects_leakage_runtime_and_machine_local_fields(metadata) -> None:
    with pytest.raises(ValueError):
        _bundle(metadata=metadata)


def test_controlled_identity_placeholders_digests_and_policies() -> None:
    placeholders = QtTargetEvidenceSpecification(
        "qtbase", *module._PLACEHOLDERS.values(), "1.0.0"
    )
    _, commits, issues, links = _bundle()
    with pytest.raises(ValueError, match="placeholders"):
        QtTargetEvidenceConstructor().construct(placeholders, commits, issues, links)
    with pytest.raises(ValueError, match="project_name"):
        dataclasses.replace(_bundle()[0], project_name="Qt")
    with pytest.raises(ValueError, match="SHA-256"):
        dataclasses.replace(_bundle()[0], commit_artifact_digest="A" * 64)
    with pytest.raises(ValueError, match="ordering_policy"):
        dataclasses.replace(_bundle()[0], ordering_policy="input-order")


@pytest.mark.parametrize(
    ("issue_type", "evidence_type", "supports", "confidence"),
    [
        (
            "Bug",
            "linked-source-native-defect-type",
            False,
            "insufficient-for-target-assignment",
        ),
        ("Task", "linked-non-defect-issue-type", False, "non-supporting"),
        ("Improvement", "linked-non-defect-issue-type", False, "non-supporting"),
        (
            "Epic",
            "unresolved-or-unsupported-link-evidence",
            False,
            "requires-target-policy-review",
        ),
    ],
)
def test_conservative_evidence_semantics(
    issue_type, evidence_type, supports, confidence
) -> None:
    record = (
        QtTargetEvidenceConstructor()
        .construct(*_bundle(issue_type))
        .evidence_records[0]
    )
    assert record.evidence_type == evidence_type
    assert record.supports_positive_label is supports
    assert record.confidence_category == confidence
    assert record.metadata["source_native_issue_type"] == issue_type
    assert not isinstance(record.confidence_category, (int, float))
    assert "defect-inducing" not in record.evidence_summary
    assert "full commit" not in record.evidence_summary
    assert "Sensitive full" not in record.evidence_summary
    assert record.evidence_timestamp == "2024-01-02T01:04:05Z"


def test_result_counts_artifact_identity_and_absent_downstream_outputs() -> None:
    result = QtTargetEvidenceConstructor().construct(*_bundle())
    assert result.evidence_record_count == 1
    assert result.observations_with_evidence_count == 1
    assert result.observations_without_evidence_count == 0
    assert result.supporting_evidence_count == 0
    assert result.non_supporting_evidence_count == 1
    assert result.unresolved_evidence_count == 0
    assert result.evidence_type_counts == {"linked-source-native-defect-type": 1}
    assert (
        result.evidence_artifact.artifact_role is ScientificArtifactRole.TARGET_EVIDENCE
    )
    assert result.evidence_artifact.record_count == 1
    forbidden = {
        "target_assignment",
        "target_label",
        "feature_matrix",
        "dataset",
        "model",
        "experiment",
    }
    assert forbidden.isdisjoint(result.__dataclass_fields__)
    assert all(
        token not in json.dumps(result.evidence_records[0].to_dict()).lower()
        for token in ("msg_has_bug_kw", "contains_fix_keyword", "allowed_as_feature")
    )


def test_bug_link_is_not_defect_induction_or_positive_support() -> None:
    result = QtTargetEvidenceConstructor().construct(*_bundle("Bug"))
    record = result.evidence_records[0]
    assert record.evidence_type == "linked-source-native-defect-type"
    assert record.supports_positive_label is False
    assert record.confidence_category == "insufficient-for-target-assignment"
    assert "defect-inducing" not in record.evidence_summary
    assert not any(item.supports_positive_label for item in result.evidence_records)


def test_input_types_digest_mismatches_and_constructor_no_io(monkeypatch) -> None:
    bundle = _bundle()
    with pytest.raises(TypeError):
        QtTargetEvidenceConstructor().construct(None, *bundle[1:])
    with pytest.raises(ValueError, match="digests"):
        QtTargetEvidenceConstructor().construct(
            dataclasses.replace(bundle[0], linking_artifact_digest="f" * 64),
            *bundle[1:],
        )
    for target in ("open", "read_text", "read_bytes", "write_text", "write_bytes"):
        monkeypatch.setattr(
            f"pathlib.Path.{target}", lambda *args, **kwargs: pytest.fail("I/O")
        )
    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: pytest.fail("Git"))
    assert QtTargetEvidenceConstructor().construct(*bundle).evidence_record_count == 1


def test_identifier_ignores_descriptive_metadata_but_scientific_type_changes_it() -> (
    None
):
    bug = QtTargetEvidenceConstructor().construct(*_bundle("Bug"))
    task = QtTargetEvidenceConstructor().construct(*_bundle("Task"))
    assert (
        bug.evidence_records[0].evidence_identifier
        != task.evidence_records[0].evidence_identifier
    )
    assert bug.evidence_identity_digest != task.evidence_identity_digest


def test_result_rejects_inconsistent_counts_duplicates_and_wrong_input_identity() -> (
    None
):
    result = QtTargetEvidenceConstructor().construct(*_bundle())
    with pytest.raises(ValueError, match="aggregate"):
        dataclasses.replace(result, evidence_record_count=2)
    with pytest.raises(ValueError, match="unique"):
        dataclasses.replace(
            result,
            evidence_records=result.evidence_records * 2,
            evidence_record_count=2,
        )
    wrong_link_spec = dataclasses.replace(
        result.commit_issue_linking_result.specification,
        commit_artifact_digest="f" * 64,
    )
    with pytest.raises(ValueError):
        dataclasses.replace(
            result.commit_issue_linking_result, specification=wrong_link_spec
        )


def test_no_model_or_experiment_methods_exist() -> None:
    public = {
        name
        for name, _ in inspect.getmembers(QtTargetEvidenceConstructor)
        if not name.startswith("_")
    }
    assert public.isdisjoint(
        {"fit", "predict", "transform", "train", "evaluate", "download", "save"}
    )
