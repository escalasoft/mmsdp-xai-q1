"""Focused tests for reproducible QtBase target assignment."""

from __future__ import annotations

import hashlib
from dataclasses import replace

import pytest

import extraction.qt_commit_extraction as commit_module
from dataset.qt_candidate_construction_contracts import QtCandidateConstructionPolicy
from dataset.qt_target_assignment import QtTargetAssigner, QtTargetAssignmentError
from dataset.qt_target_assignment_contracts import (
    QtTargetAssignmentPolicy,
    QtTargetAssignmentSpecification,
)
from dataset.scientific_builder_contracts import ScientificArtifactReference
from dataset.scientific_builder_pipeline import _detach
from dataset.scientific_candidate_contracts import (
    ScientificCandidateArtifactBinding,
    ScientificCandidateAttributionRecord,
    ScientificCandidateConstructionResult,
    ScientificCandidateConstructionSpecification,
    ScientificCandidateConstructionValidation,
    ScientificCandidateExclusionRecord,
    ScientificDefectInducingCandidateRecord,
)
from dataset.scientific_target_assignment_contracts import (
    ScientificTargetAssignmentSpecification,
)
from extraction.qt_commit_extraction import (
    QtCommitExtractionResult,
    QtCommitExtractionSpecification,
    ScientificCommitRecord,
)

SNAPSHOT = "a" * 64
HISTORICAL = "1" * 40
NEGATIVE = "2" * 40
FIXING = "3" * 40
OTHER = "4" * 40


def _commits() -> QtCommitExtractionResult:
    records = tuple(
        ScientificCommitRecord(
            identifier,
            (),
            "A",
            "a@example.invalid",
            timestamp,
            "C",
            "c@example.invalid",
            timestamp,
            message,
        )
        for identifier, timestamp, message in (
            (HISTORICAL, "2020-01-01T00:00:00+00:00", "ordinary change"),
            (NEGATIVE, "2020-01-02T00:00:00+00:00", "bug fix words irrelevant"),
            (FIXING, "2020-01-03T00:00:00+00:00", "neutral text"),
        )
    )
    spec = QtCommitExtractionSpecification("1.0.0")
    content = {
        "schema_version": spec.schema_version,
        "artifact_role": "commit-artifact",
        "source_repository": "qtbase",
        "source_revision": FIXING,
        "source_snapshot_digest": SNAPSHOT,
        "object_hash_algorithm": "sha1",
        "ordering_policy": spec.ordering_policy,
        "records": records,
    }
    artifact = ScientificArtifactReference(
        "qtbase-commits",
        "commit-artifact",
        spec.artifact_repository_relative_path,
        hashlib.sha256(commit_module._canonical_bytes(content)).hexdigest(),
        spec.schema_version,
        len(records),
    )
    return QtCommitExtractionResult(
        spec,
        FIXING,
        SNAPSHOT,
        "sha1",
        records,
        artifact,
        spec.ordering_policy,
        ("git:cat-file:completed",),
    )


def _attribution(commits, *, historical=HISTORICAL, line=7):
    policy = QtCandidateConstructionPolicy.create().scientific_policy
    values = dict(
        repository_snapshot_digest=SNAPSHOT,
        fixing_commit=FIXING,
        baseline_commit=NEGATIVE,
        issue_identifier="QTBUG-1",
        target_evidence_identifier="evidence-1",
        commit_issue_link_identifier="link-1",
        commit_issue_link_artifact_digest="b" * 64,
        diff_artifact_digest="c" * 64,
        hunk_identifier=f"hunk-{line}",
        old_path="src/a.cpp",
        old_blob_identifier="5" * 40,
        deleted_preimage_line_number=line,
        blamed_historical_commit=historical,
        attribution_method="line-provenance-blame",
        policy_version=policy.policy_version,
        policy_digest=policy.policy_digest,
    )
    return ScientificCandidateAttributionRecord(
        **values,
        attribution_identifier=ScientificCandidateAttributionRecord.calculate_identifier(
            **values
        ),
    )


def _candidate(attributions, level="commit"):
    policy = QtCandidateConstructionPolicy.create().scientific_policy
    values = dict(
        blamed_historical_commit=attributions[0].blamed_historical_commit,
        aggregation_level=level,
        attribution_identifiers=tuple(
            sorted(x.attribution_identifier for x in attributions)
        ),
        fixing_commits=(FIXING,),
        issue_identifiers=("QTBUG-1",),
        target_evidence_identifiers=("evidence-1",),
        policy_version=policy.policy_version,
        policy_digest=policy.policy_digest,
    )
    return ScientificDefectInducingCandidateRecord(
        **values,
        candidate_identifier=ScientificDefectInducingCandidateRecord.calculate_identifier(
            **values
        ),
    )


def _exclusion(disposition="unresolved"):
    policy = QtCandidateConstructionPolicy.create().scientific_policy
    values = dict(
        disposition=disposition,
        reason="unblamable-line" if disposition == "unresolved" else "policy-rejection",
        fixing_commit=FIXING,
        baseline_commit=NEGATIVE,
        issue_identifier="QTBUG-2",
        target_evidence_identifier="evidence-2",
        hunk_identifier=f"hunk-{disposition}",
        old_path="src/b.cpp",
        old_blob_identifier="6" * 40,
        deleted_preimage_line_number=9,
        policy_version=policy.policy_version,
        policy_digest=policy.policy_digest,
        detail_code=f"{disposition}-case",
    )
    return ScientificCandidateExclusionRecord(
        **values,
        exclusion_identifier=ScientificCandidateExclusionRecord.calculate_identifier(
            **values
        ),
    )


def _candidate_result(commits, *, multiple=False, exclusions=(), historical=HISTORICAL):
    policy = QtCandidateConstructionPolicy.create().scientific_policy
    spec_values = dict(
        schema_version="1.0.0",
        specification_version="candidate-specification-1.0.0",
        repository_snapshot_digest=SNAPSHOT,
        commit_artifact_digest=commits.artifact.content_digest,
        issue_artifact_digest="7" * 64,
        commit_issue_link_artifact_digest="b" * 64,
        target_evidence_artifact_digest="8" * 64,
        diff_artifact_digest="c" * 64,
        policy_digest=policy.policy_digest,
    )
    spec = ScientificCandidateConstructionSpecification(
        **spec_values,
        specification_digest=ScientificCandidateConstructionSpecification.calculate_digest(
            **spec_values
        ),
    )
    attributions = (_attribution(commits, historical=historical),)
    records = [_candidate(attributions)]
    if multiple:
        records.append(_candidate(attributions, "line"))
    records = tuple(sorted(records, key=lambda x: x.candidate_identifier))
    exclusions = tuple(sorted(exclusions, key=lambda x: x.exclusion_identifier))
    artifact = ScientificArtifactReference(
        "qtbase-candidates",
        "defect-inducing-candidate",
        "artifacts/derived/qtbase-candidates.json",
        "d" * 64,
        "1.0.0",
        len(records),
    )
    binding_values = dict(
        artifact=artifact,
        specification_digest=spec.specification_digest,
        policy_digest=policy.policy_digest,
        repository_snapshot_digest=SNAPSHOT,
        upstream_artifact_digests={
            "commits": commits.artifact.content_digest,
            "diffs": "c" * 64,
            "issues": "7" * 64,
            "links": "b" * 64,
            "target-evidence": "8" * 64,
        },
        ordered_candidate_identifiers=tuple(x.candidate_identifier for x in records),
        ordered_exclusion_identifiers=tuple(x.exclusion_identifier for x in exclusions),
    )
    binding = ScientificCandidateArtifactBinding(
        **binding_values,
        binding_digest=ScientificCandidateArtifactBinding.calculate_digest(
            **binding_values
        ),
    )
    validation = ScientificCandidateConstructionValidation(
        True,
        spec.specification_digest,
        policy.policy_digest,
        len(attributions),
        len(records),
        len(exclusions),
        (),
        (),
    )
    return ScientificCandidateConstructionResult(
        spec, policy, attributions, records, exclusions, validation, binding
    )


def _target_spec(commits, candidates, **changes):
    policy = QtTargetAssignmentPolicy.create()
    values = dict(
        schema_version="1.0.0",
        specification_version="qt-target-specification-1.0.0",
        repository_snapshot_digest=SNAPSHOT,
        commit_artifact_digest=commits.artifact.content_digest,
        candidate_artifact_digest=candidates.artifact_binding.artifact.content_digest,
        candidate_binding_digest=candidates.artifact_binding.binding_digest,
        candidate_specification_digest=candidates.specification.specification_digest,
        candidate_policy_digest=candidates.policy.policy_digest,
        policy_digest=policy.scientific_policy.policy_digest,
    )
    values.update(changes)
    scientific = ScientificTargetAssignmentSpecification(
        **values,
        specification_digest=ScientificTargetAssignmentSpecification.calculate_digest(
            **values
        ),
    )
    return QtTargetAssignmentSpecification(scientific, policy)


def test_positive_negative_and_multiple_candidates_aggregate_once():
    commits = _commits()
    candidates = _candidate_result(commits, multiple=True)
    result = QtTargetAssigner().construct(
        _target_spec(commits, candidates), commits, candidates
    )
    by_id = {x.observation_identifier: x for x in result.assignments}
    assert by_id[HISTORICAL].target_label == 1
    assert len(by_id[HISTORICAL].evidence_identifiers) == 2
    assert by_id[NEGATIVE].target_label == 0
    assert len(result.assignments) == len(set(by_id)) == 3


def test_repeated_construction_order_and_digest_are_stable():
    commits = _commits()
    candidates = _candidate_result(commits, multiple=True)
    spec = _target_spec(commits, candidates)
    first = QtTargetAssigner().construct(spec, commits, candidates)
    second = QtTargetAssigner().construct(spec, commits, candidates)
    assert first == second
    assert (
        first.artifact_binding.artifact.content_digest
        == second.artifact_binding.artifact.content_digest
    )
    assert tuple(x.observation_identifier for x in first.assignments) == tuple(
        sorted((HISTORICAL, NEGATIVE, FIXING))
    )


def test_unresolved_and_excluded_evidence_are_traced_not_assigned():
    commits = _commits()
    candidates = _candidate_result(
        commits, exclusions=(_exclusion(), _exclusion("excluded"))
    )
    result = QtTargetAssigner().construct(
        _target_spec(commits, candidates), commits, candidates
    )
    assert result.validation.unresolved_trace_count == 1
    assert result.validation.excluded_trace_count == 1
    assert all(
        trace.historical_commit is None
        for trace in result.evidence_traces
        if trace.disposition.value in {"excluded", "unresolved"}
    )


@pytest.mark.parametrize(
    "field",
    [
        "repository_snapshot_digest",
        "commit_artifact_digest",
        "candidate_artifact_digest",
        "candidate_binding_digest",
    ],
)
def test_mismatched_upstream_identity_fails(field):
    commits = _commits()
    candidates = _candidate_result(commits)
    spec = _target_spec(commits, candidates, **{field: "f" * 64})
    with pytest.raises(ValueError, match="upstream artifact identity"):
        QtTargetAssigner().construct(spec, commits, candidates)


def test_temporal_or_unknown_historical_candidate_fails():
    commits = _commits()
    unknown = _candidate_result(commits, historical=OTHER)
    with pytest.raises(QtTargetAssignmentError, match="outside the eligible universe"):
        QtTargetAssigner().construct(_target_spec(commits, unknown), commits, unknown)
    late = _candidate_result(commits, historical=FIXING)
    with pytest.raises(QtTargetAssignmentError, match="temporal/provenance"):
        QtTargetAssigner().construct(_target_spec(commits, late), commits, late)


def test_target_artifact_is_forbidden_from_feature_view_and_keywords_irrelevant():
    commits = _commits()
    candidates = _candidate_result(commits)
    result = QtTargetAssigner().construct(
        _target_spec(commits, candidates), commits, candidates
    )
    assert _detach(result, feature_view=True) is None
    assert _detach(result.artifact_binding.artifact, feature_view=True) is None
    assert (
        next(
            x for x in result.assignments if x.observation_identifier == NEGATIVE
        ).target_label
        == 0
    )
    source = QtTargetAssignmentPolicy.create().scientific_policy.to_dict()
    assert "bug_confidence" not in str(source)
    with pytest.raises(ValueError, match="forbidden predictive field"):
        replace(result.policy, metadata={"bug_confidence": 1})
