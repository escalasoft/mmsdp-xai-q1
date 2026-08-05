"""Contract tests for reproducible Qt issue extraction."""

import dataclasses
from dataclasses import FrozenInstanceError

import pytest

import extraction.qt_issue_extraction as module
from dataset.scientific_builder_contracts import (
    ScientificArtifactReference,
    ScientificArtifactRole,
)
from extraction.qt_issue_extraction import (
    QtIssueExtractionResult,
    QtIssueExtractionSpecification,
    QtIssueExtractor,
    QtIssueRecord,
)

DIGEST = "a" * 64


def specification(**changes):
    values = {
        "project_name": "qtbase",
        "canonical_issue_source": "urn:fixture:qtbase-issues",
        "source_revision": "fixture-export-v1",
        "source_artifact_digest": DIGEST,
        "project_identifier": "fixture-qtbase",
        "issue_schema_version": "fixture-schema-v1",
        "extraction_policy_version": "1.0.0",
    }
    values.update(changes)
    return QtIssueExtractionSpecification(**values)


def record(**changes):
    values = {
        "issue_identifier": "QT-FIXTURE-1",
        "project_identifier": "fixture-qtbase",
        "issue_type": "Task",
        "status": "Open",
        "resolution": None,
        "priority": None,
        "created_timestamp": "2024-01-01T00:00:00Z",
        "updated_timestamp": "2024-01-01T01:00:00Z",
        "resolved_timestamp": None,
        "summary": "Résumé Unicode",
        "description": None,
        "reporter_identifier": "source-user-1",
        "assignee_identifier": None,
        "component": None,
        "version": None,
        "fix_versions": (),
    }
    values.update(changes)
    for name in ("created_timestamp", "updated_timestamp", "resolved_timestamp"):
        values[name] = module._timestamp(values[name], name)
    values["fix_versions"] = tuple(sorted(values["fix_versions"]))
    digest = module._digest(module._record_content(values))
    return QtIssueRecord(**values, source_record_digest=digest)


def result(issue=None, **changes):
    spec = specification()
    issues = (issue or record(),)
    content = module._artifact_content(spec, issues)
    artifact = ScientificArtifactReference(
        "qtbase-issues",
        ScientificArtifactRole.ISSUE_ARTIFACT,
        "artifacts/qtbase/issues/fixture-export-v1/qt-issues.jsonl",
        module._digest(content),
        "fixture-schema-v1",
        len(issues),
    )
    identity = module._digest(
        {
            "artifact_content_digest": artifact.content_digest,
            "canonical_issue_source": spec.canonical_issue_source,
            "source_revision": spec.source_revision,
            "source_artifact_digest": spec.source_artifact_digest,
            "issue_schema_version": spec.issue_schema_version,
            "extraction_policy_version": spec.extraction_policy_version,
        }
    )
    values = {
        "specification": spec,
        "issues": issues,
        "extraction_artifact": artifact,
        "extracted_issue_count": len(issues),
        "issue_type_counts": {issues[0].issue_type: 1},
        "status_counts": {issues[0].status: 1},
        "resolved_issue_count": 0,
        "unresolved_issue_count": 1,
        "missing_created_timestamp_count": 0,
        "missing_resolved_timestamp_count": 1,
        "issue_identity_digest": identity,
        "command_evidence": (
            "local-artifact:sha256-verified",
            "parser:json:completed",
        ),
    }
    values.update(changes)
    return QtIssueExtractionResult(**values)


def test_exact_public_api_and_narrow_extractor_api() -> None:
    assert module.__all__ == [
        "QtIssueExtractionSpecification",
        "QtIssueRecord",
        "QtIssueExtractionResult",
        "QtIssueExtractor",
    ]
    public = {name for name in dir(QtIssueExtractor) if not name.startswith("_")}
    assert public == {"extract", "extractor_name"}
    assert not any(
        word in " ".join(module.__all__).lower()
        for word in ("link", "target", "feature", "dataset", "model", "experiment")
    )


@pytest.mark.parametrize(
    "contract", [QtIssueExtractionSpecification, QtIssueRecord, QtIssueExtractionResult]
)
def test_contracts_are_frozen_and_slotted(contract) -> None:
    assert contract.__dataclass_params__.frozen
    assert "__slots__" in contract.__dict__


def test_recursive_detachment_deterministic_serialization_and_freezing() -> None:
    source = {"notes": ["raw", {"kind": "provenance"}]}
    spec = specification(metadata=source)
    source["notes"].append("changed")
    assert (
        spec.to_dict()
        == specification(metadata={"notes": ["raw", {"kind": "provenance"}]}).to_dict()
    )
    detached = spec.to_dict()
    detached["metadata"]["notes"].append("detached")
    assert detached != spec.to_dict()
    with pytest.raises(FrozenInstanceError):
        spec.project_name = "other"  # type: ignore[misc]


def test_constructor_performs_no_io(monkeypatch) -> None:
    monkeypatch.setattr(module.Path, "read_bytes", lambda self: pytest.fail("I/O"))
    assert specification().project_name == "qtbase"


@pytest.mark.parametrize(
    "changes",
    [
        {"project_name": "Qt"},
        {"canonical_issue_source": "https://user:secret@example.test/export"},
        {"canonical_issue_source": "/Users/local/issues.json"},
        {"source_artifact_digest": "ABC"},
        {"allowed_input_formats": ("json",)},
        {"ordering_policy": "source-order"},
        {"timestamp_policy": "local-time"},
        {"identity_policy": "summary"},
        {"duplicate_policy": "last-wins"},
        {"unresolved_record_policy": "discard"},
    ],
)
def test_specification_rejects_uncontrolled_identity_or_policy(changes) -> None:
    with pytest.raises(ValueError):
        specification(**changes)


@pytest.mark.parametrize(
    "metadata",
    [
        {"local_path": "/tmp/issues"},
        {"runtime_timestamp": "now"},
        {"created_at": "2024-01-01T00:00:00Z"},
        {"duration_ms": 2},
        {"hostname": "host"},
        {"username": "person"},
        {"credentials": "secret"},
        {"environment": {}},
        {"feature_enabled": True},
        {"target_label": 1},
        {"prediction": 0.5},
        {"bug_confidence": 0.9},
        {"nested": {"value": "<X object at 0x12345678>"}},
    ],
)
def test_metadata_rejects_runtime_machine_and_target_fields(metadata) -> None:
    with pytest.raises(ValueError):
        specification(metadata=metadata)


def test_record_normalizes_timestamps_and_retains_missing_raw_semantics() -> None:
    item = record(
        issue_type="Improvement",
        created_timestamp="2024-01-01T02:00:00+02:00",
        updated_timestamp="2023-12-31T19:30:00-05:00",
        fix_versions=("6.7", "6.6"),
    )
    assert item.created_timestamp == "2024-01-01T00:00:00Z"
    assert item.updated_timestamp == "2024-01-01T00:30:00Z"
    assert item.fix_versions == ("6.6", "6.7")
    assert item.issue_type == "Improvement"
    assert item.resolution is item.description is item.assignee_identifier is None
    assert not hasattr(item, "is_bug")
    assert not hasattr(item, "contains_bug_keyword")
    assert not hasattr(item, "commit_identifier")


@pytest.mark.parametrize(
    "changes",
    [
        {"issue_identifier": ""},
        {"created_timestamp": "2024-01-01"},
        {"created_timestamp": "invalid"},
        {"updated_timestamp": "2023-12-31T23:59:00Z"},
        {"resolved_timestamp": "2023-12-31T23:59:00Z"},
        {"fix_versions": ("6.6", "6.6")},
        {"reporter_identifier": "/Users/local/person"},
    ],
)
def test_record_rejects_invalid_identity_time_sequence_or_machine_data(changes) -> None:
    with pytest.raises((TypeError, ValueError)):
        record(**changes)


def test_record_digest_is_deterministic_and_metadata_independent() -> None:
    one = record()
    values = {
        field.name: getattr(one, field.name)
        for field in dataclasses.fields(one)
        if field.name != "metadata"
    }
    two = QtIssueRecord(**values, metadata={"note": "descriptive"})
    assert one.source_record_digest == two.source_record_digest
    assert one.to_dict() == record().to_dict()


def test_result_counts_artifact_identity_and_metadata_invariants() -> None:
    one = result()
    assert one.extracted_issue_count == 1
    assert one.issue_type_counts == {"Task": 1}
    assert one.status_counts == {"Open": 1}
    assert (
        one.extraction_artifact.artifact_role is ScientificArtifactRole.ISSUE_ARTIFACT
    )
    assert one.extraction_artifact.record_count == 1
    assert one == result()
    changed_metadata = result(metadata={"note": "descriptive"})
    assert changed_metadata.issue_identity_digest == one.issue_identity_digest
    assert "/tmp" not in repr(one) and "/tmp" not in str(one.to_dict())


@pytest.mark.parametrize(
    "changes",
    [
        {"extracted_issue_count": 2},
        {"issue_type_counts": {"Bug": 1}},
        {"resolved_issue_count": 1},
        {"issues": (record(), record())},
        {"command_evidence": ("reader:/tmp/file",)},
    ],
)
def test_result_rejects_inconsistent_counts_duplicates_and_evidence(changes) -> None:
    with pytest.raises(ValueError):
        result(**changes)


def test_placeholder_execution_is_blocked_before_io(monkeypatch) -> None:
    values = specification().to_dict()
    for field, placeholder in module._PLACEHOLDERS.items():
        values[field] = placeholder
    spec = QtIssueExtractionSpecification(**values)
    monkeypatch.setattr(module.Path, "is_file", lambda self: pytest.fail("I/O"))
    with pytest.raises(ValueError, match="placeholders"):
        QtIssueExtractor().extract(spec, "/not/read")
