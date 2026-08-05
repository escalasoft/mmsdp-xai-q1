"""Contracts for deterministic Qt commit--issue linking."""

import dataclasses
import hashlib
import json
from dataclasses import FrozenInstanceError

import pytest

import extraction.qt_commit_issue_linking as module
from extraction.qt_commit_issue_linking import (
    QtCommitIssueLink,
    QtCommitIssueLinker,
    QtCommitIssueLinkingResult,
    QtCommitIssueLinkSpecification,
)


def write_json(path, value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def specification(commit_digest="a" * 64, issue_digest="b" * 64, **changes):
    values = {
        "schema_version": "1.0.0",
        "commit_artifact_digest": commit_digest,
        "issue_artifact_digest": issue_digest,
    }
    values.update(changes)
    return QtCommitIssueLinkSpecification(**values)


def link(**changes):
    values = {
        "commit_revision": "a" * 40,
        "issue_identifier": "QTBUG-100",
        "reference_type": "fixes",
        "reference_location": "commit-message:line:2",
    }
    values.update(changes)
    return QtCommitIssueLink(**values, artifact_digest=module._digest(values))


def result(links=None):
    spec = specification()
    values = tuple(links or (link(),))
    return QtCommitIssueLinkingResult(
        spec, values, module._digest(module._result_content(spec, values))
    )


def test_exact_api_surface_and_no_downstream_scientific_api() -> None:
    assert module.__all__ == [
        "QtCommitIssueLinkSpecification",
        "QtCommitIssueLink",
        "QtCommitIssueLinkingResult",
        "QtCommitIssueLinker",
    ]
    assert {
        name for name in dir(QtCommitIssueLinker) if not name.startswith("_")
    } == {"link", "linker_name"}
    forbidden = ("label", "bug", "target", "feature", "model", "train", "metric")
    assert not any(word in " ".join(module.__all__).lower() for word in forbidden)
    assert set(item.name for item in dataclasses.fields(QtCommitIssueLink)) == {
        "commit_revision",
        "issue_identifier",
        "reference_type",
        "reference_location",
        "artifact_digest",
    }


@pytest.mark.parametrize(
    "contract",
    [QtCommitIssueLinkSpecification, QtCommitIssueLink, QtCommitIssueLinkingResult],
)
def test_contracts_are_frozen_and_slotted(contract) -> None:
    assert contract.__dataclass_params__.frozen
    assert "__slots__" in contract.__dict__
    instance = specification() if contract is QtCommitIssueLinkSpecification else (
        link() if contract is QtCommitIssueLink else result()
    )
    field_name = dataclasses.fields(instance)[0].name
    with pytest.raises(FrozenInstanceError):
        setattr(instance, field_name, "changed")


def test_serialization_is_detached_canonical_and_stable() -> None:
    one = result()
    assert one.to_dict() == result().to_dict()
    detached = one.to_dict()
    detached["links"].append({"scientific": "interpretation"})
    assert detached != one.to_dict()
    assert one.artifact_digest == result().artifact_digest


def test_result_rejects_noncanonical_order_and_duplicates() -> None:
    first = link(issue_identifier="QTBUG-100")
    second = link(issue_identifier="QTBUG-200")
    with pytest.raises(ValueError, match="ordered"):
        result((second, first))
    with pytest.raises(ValueError, match="unique"):
        result((first, first))


def test_constructor_has_no_io(monkeypatch) -> None:
    monkeypatch.setattr(module.Path, "read_bytes", lambda self: pytest.fail("I/O"))
    assert QtCommitIssueLinker().linker_name == "qt-commit-issue-linker"
    assert specification().schema_version == "1.0.0"


def test_duplicate_and_repeated_references_are_deterministic(tmp_path) -> None:
    commits = tmp_path / "commits.json"
    issues = tmp_path / "issues.json"
    commit_digest = write_json(
        commits,
        [
            {
                "commit_id": "b" * 40,
                "message": "Fixes: QTBUG-200 QTBUG-200\nQTBUG-100\nQTBUG-100",
            },
            {"commit_id": "a" * 40, "message": "Task-number: QTBUG-200"},
        ],
    )
    issue_digest = write_json(
        issues,
        [{"issue_identifier": "QTBUG-200"}, {"issue_identifier": "QTBUG-100"}],
    )
    output = QtCommitIssueLinker().link(
        specification(commit_digest, issue_digest), commits, issues
    )
    assert [(item.commit_revision, item.issue_identifier) for item in output.links] == [
        ("a" * 40, "QTBUG-200"),
        ("b" * 40, "QTBUG-100"),
        ("b" * 40, "QTBUG-100"),
        ("b" * 40, "QTBUG-200"),
    ]
    assert [item.reference_location for item in output.links[1:3]] == [
        "commit-message:line:2",
        "commit-message:line:3",
    ]
    assert output.links[-1].reference_type == "fixes"


@pytest.mark.parametrize(
    "message",
    [
        "Fixes: QTCREATORBUG-100",
        "Fixes: QTBUG #100",
        "Fixes: qtbug-100",
        "Related-to: ISSUE-100",
        "QTBUG-100extra",
    ],
)
def test_unsupported_reference_patterns_do_not_link(tmp_path, message) -> None:
    commits = tmp_path / "commits.json"
    issues = tmp_path / "issues.json"
    commit_digest = write_json(
        commits, [{"commit_id": "a" * 40, "message": message}]
    )
    issue_digest = write_json(issues, [{"issue_identifier": "QTBUG-100"}])
    output = QtCommitIssueLinker().link(
        specification(commit_digest, issue_digest), commits, issues
    )
    assert output.links == ()


def test_digest_tampering_and_invalid_policies_are_rejected() -> None:
    with pytest.raises(ValueError, match="canonical link"):
        QtCommitIssueLink(
            "a" * 40,
            "QTBUG-100",
            "plain",
            "commit-message:line:1",
            "f" * 64,
        )
    with pytest.raises(ValueError):
        specification(ordering_policy="filesystem-order")
    with pytest.raises(ValueError):
        specification(matching_policy="semantic-similarity")
