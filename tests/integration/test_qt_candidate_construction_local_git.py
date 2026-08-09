"""Offline end-to-end candidate construction against deterministic local Git."""

import os
import subprocess
from pathlib import Path

import extraction.qt_commit_issue_linking as link_module
import extraction.qt_issue_extraction as issue_module
from dataset.qt_candidate_construction import QtCandidateConstructor
from dataset.qt_candidate_construction_contracts import (
    QtCandidateConstructionPolicy,
    QtCandidateConstructionSpecification,
)
from dataset.qt_target_evidence_construction import (
    QtTargetEvidenceConstructor,
    QtTargetEvidenceSpecification,
)
from dataset.scientific_builder_contracts import (
    ScientificArtifactReference,
    ScientificArtifactRole,
)
from dataset.scientific_candidate_contracts import (
    ScientificCandidateConstructionSpecification,
)
from extraction.qt_commit_extraction import (
    QtCommitExtractionSpecification,
    QtCommitExtractor,
)
from extraction.qt_commit_issue_linking import (
    QtCommitIssueLink,
    QtCommitIssueLinkingResult,
    QtCommitIssueLinkSpecification,
)
from extraction.qt_diff_extraction import QtDiffExtractionSpecification, QtDiffExtractor
from extraction.qt_issue_extraction import (
    QtIssueExtractionResult,
    QtIssueExtractionSpecification,
    QtIssueRecord,
)
from extraction.qt_repository_acquisition import (
    QtRepositoryAcquirer,
    QtRepositoryAcquisitionSpecification,
)

CANONICAL = "https://code.qt.io/qt/qtbase.git"


def _git(repository: Path, *arguments: str, day: int = 1) -> str:
    environment = {
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_TERMINAL_PROMPT": "0",
        "HOME": os.devnull,
        "LANG": "C",
        "LC_ALL": "C",
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "GIT_AUTHOR_DATE": f"2002-01-{day:02d}T00:00:00+0000",
        "GIT_COMMITTER_DATE": f"2002-01-{day:02d}T00:00:00+0000",
    }
    result = subprocess.run(
        ["git", *arguments],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
        env=environment,
        shell=False,
    )
    return result.stdout.strip()


def _issues() -> QtIssueExtractionResult:
    values = {
        "issue_identifier": "QTBUG-1",
        "project_identifier": "fixture-qtbase",
        "issue_type": "Bug",
        "status": "Closed",
        "resolution": "Fixed",
        "priority": "P2",
        "created_timestamp": issue_module._timestamp(
            "2002-01-01T00:00:00+00:00", "created_timestamp"
        ),
        "updated_timestamp": issue_module._timestamp(
            "2002-01-03T00:00:00+00:00", "updated_timestamp"
        ),
        "resolved_timestamp": issue_module._timestamp(
            "2002-01-03T00:00:00+00:00", "resolved_timestamp"
        ),
        "summary": "fixture",
        "description": None,
        "reporter_identifier": None,
        "assignee_identifier": None,
        "component": "Core",
        "version": None,
        "fix_versions": (),
    }
    issue = QtIssueRecord(
        **values,
        source_record_digest=issue_module._digest(issue_module._record_content(values)),
    )
    specification = QtIssueExtractionSpecification(
        "qtbase",
        "urn:fixture:qtbase-issues",
        "fixture-v1",
        "a" * 64,
        "fixture-qtbase",
        "1.0.0",
        "1.0.0",
    )
    artifact = ScientificArtifactReference(
        "qtbase-issues",
        ScientificArtifactRole.ISSUE_ARTIFACT,
        "artifacts/qtbase/issues/fixture-v1/qt-issues.jsonl",
        issue_module._digest(issue_module._artifact_content(specification, (issue,))),
        "1.0.0",
        1,
    )
    identity = issue_module._digest(
        {
            "artifact_content_digest": artifact.content_digest,
            "canonical_issue_source": specification.canonical_issue_source,
            "source_revision": specification.source_revision,
            "source_artifact_digest": specification.source_artifact_digest,
            "issue_schema_version": specification.issue_schema_version,
            "extraction_policy_version": specification.extraction_policy_version,
        }
    )
    return QtIssueExtractionResult(
        specification,
        (issue,),
        artifact,
        1,
        {"Bug": 1},
        {"Closed": 1},
        1,
        0,
        0,
        0,
        identity,
        ("local-artifact:sha256-verified", "parser:json:completed"),
    )


def test_repeated_local_construction_is_identical_and_preserves_exclusions(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    _git(source, "init", "-q")
    _git(source, "config", "user.name", "Fixture")
    _git(source, "config", "user.email", "fixture@example.invalid")
    (source / "seed.txt").write_text("seed\n", encoding="utf-8")
    _git(source, "add", ".")
    _git(source, "commit", "-q", "-m", "root", day=1)
    (source / "src").mkdir()
    (source / "src/a.cpp").write_text(
        "int historical = 1;\n// remove comment\nif (ready) {\n}\n",
        encoding="utf-8",
    )
    _git(source, "add", ".")
    _git(source, "commit", "-q", "-m", "introduce source", day=2)
    historical = _git(source, "rev-parse", "HEAD")
    (source / "src/a.cpp").write_text(
        "int fixed = 2;\nif(ready){\n}\n", encoding="utf-8"
    )
    _git(source, "add", ".")
    _git(source, "commit", "-q", "-m", "Fixes: QTBUG-1", day=3)
    fixing = _git(source, "rev-parse", "HEAD")
    remote = tmp_path / "qtbase.git"
    _git(tmp_path, "clone", "-q", "--bare", str(source), str(remote))
    acquisition = QtRepositoryAcquirer().acquire(
        QtRepositoryAcquisitionSpecification._for_local_test(
            repository_name="qtbase",
            canonical_repository_url=CANONICAL,
            transport_repository_url=str(remote),
            requested_reference=fixing,
            default_branch="master",
            acquisition_policy_version="1.0.0",
        ),
        tmp_path / "acquired",
    )
    repository = tmp_path / "acquired"
    commits = QtCommitExtractor().extract(
        acquisition,
        repository,
        tmp_path / "commits.json",
        QtCommitExtractionSpecification(
            "1.0.0",
            observation_window_start="2002-01-01T00:00:00+00:00",
            observation_window_end="2002-01-03T23:59:59+00:00",
        ),
    )
    diffs = QtDiffExtractor().extract(
        QtDiffExtractionSpecification(
            "qtbase", CANONICAL, fixing, commits.artifact.content_digest, "1.0.0"
        ),
        repository,
        acquisition.repository_snapshot,
        commits,
    )
    issues = _issues()
    link_values = {
        "commit_revision": fixing,
        "issue_identifier": "QTBUG-1",
        "reference_type": "fixes",
        "reference_location": "commit-message:line:1",
    }
    link = QtCommitIssueLink(
        **link_values, artifact_digest=link_module._digest(link_values)
    )
    link_spec = QtCommitIssueLinkSpecification(
        "1.0.0",
        commits.artifact.content_digest,
        issues.extraction_artifact.content_digest,
    )
    links = QtCommitIssueLinkingResult(
        link_spec,
        (link,),
        link_module._digest(link_module._result_content(link_spec, (link,))),
    )
    evidence = QtTargetEvidenceConstructor().construct(
        QtTargetEvidenceSpecification(
            "qtbase",
            commits.artifact.content_digest,
            issues.extraction_artifact.content_digest,
            links.artifact_digest,
            "1.0.0",
        ),
        commits,
        issues,
        links,
    )
    policy = QtCandidateConstructionPolicy.create()
    spec_values = {
        "schema_version": "1.0.0",
        "specification_version": "qt-candidate-specification-1.0.0",
        "repository_snapshot_digest": acquisition.repository_snapshot.snapshot_digest,
        "commit_artifact_digest": commits.artifact.content_digest,
        "issue_artifact_digest": issues.extraction_artifact.content_digest,
        "commit_issue_link_artifact_digest": links.artifact_digest,
        "target_evidence_artifact_digest": evidence.evidence_artifact.content_digest,
        "diff_artifact_digest": diffs.extraction_artifact.content_digest,
        "policy_digest": policy.scientific_policy.policy_digest,
    }
    scientific = ScientificCandidateConstructionSpecification(
        **spec_values,
        specification_digest=(
            ScientificCandidateConstructionSpecification.calculate_digest(**spec_values)
        ),
    )
    specification = QtCandidateConstructionSpecification(scientific, policy)
    arguments = (
        specification,
        repository,
        acquisition,
        commits,
        diffs,
        issues,
        links,
        evidence,
    )
    first = QtCandidateConstructor().construct(*arguments)
    second = QtCandidateConstructor().construct(*arguments)
    assert first == second
    assert first.artifact_binding.artifact.content_digest == (
        second.artifact_binding.artifact.content_digest
    )
    assert {item.blamed_historical_commit for item in first.attributions} == {
        historical
    }
    assert len(first.attributions) == 1
    assert {item.reason.value for item in first.exclusions} == {
        "blank-or-comment-line",
        "formatting-only-change",
    }
    assert len(first.candidates) == 3
    assert not hasattr(first, "target_assignments")
