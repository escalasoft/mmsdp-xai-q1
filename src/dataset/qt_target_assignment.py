"""Deterministic QtBase commit-level target assignment."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from datetime import datetime
from enum import Enum

from dataset.qt_target_assignment_contracts import QtTargetAssignmentSpecification
from dataset.scientific_builder_contracts import (
    ScientificArtifactReference,
    ScientificArtifactRole,
    ScientificTargetAssignment,
)
from dataset.scientific_candidate_contracts import (
    ScientificCandidateAggregationLevel,
    ScientificCandidateConstructionResult,
    ScientificCandidateDisposition,
)
from dataset.scientific_target_assignment_contracts import (
    ScientificTargetAssignmentArtifactBinding,
    ScientificTargetAssignmentResult,
    ScientificTargetAssignmentValidation,
    ScientificTargetDisposition,
    ScientificTargetEvidenceTrace,
)
from extraction.qt_commit_extraction import QtCommitExtractionResult

__all__ = ["QtTargetAssignmentError", "QtTargetAssigner"]


class QtTargetAssignmentError(RuntimeError):
    """A deterministic scientific inconsistency in target assignment."""


def _thaw(value: object) -> object:
    if is_dataclass(value) and not isinstance(value, type):
        return {item.name: _thaw(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    if isinstance(value, Enum):
        return value.value
    return value


def _artifact_digest(value: object) -> str:
    payload = (
        json.dumps(
            _thaw(value),
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )
    return hashlib.sha256(payload).hexdigest()


class QtTargetAssigner:
    """Assign exactly one binary target per eligible commit."""

    def construct(
        self,
        specification: QtTargetAssignmentSpecification,
        commits: QtCommitExtractionResult,
        candidates: ScientificCandidateConstructionResult,
    ) -> ScientificTargetAssignmentResult:
        self._validate_inputs(specification, commits, candidates)
        spec = specification.scientific_specification
        policy = specification.policy.scientific_policy
        commit_by_id = {item.commit_id: item for item in commits.records}
        attribution_by_id = {
            item.attribution_identifier: item for item in candidates.attributions
        }

        grouped: dict[str, list[object]] = {}
        for candidate in candidates.candidates:
            if candidate.blamed_historical_commit not in commit_by_id:
                raise QtTargetAssignmentError(
                    "candidate historical commit is outside the eligible universe"
                )
            grouped.setdefault(candidate.blamed_historical_commit, []).append(candidate)

        assignments = []
        traces = []
        for commit_id in sorted(commit_by_id):
            records = grouped.get(commit_id, [])
            if records:
                candidate_ids = tuple(sorted(x.candidate_identifier for x in records))
                attribution_ids = tuple(
                    sorted(
                        {value for x in records for value in x.attribution_identifiers}
                    )
                )
                attributions = []
                for identifier in attribution_ids:
                    try:
                        attribution = attribution_by_id[identifier]
                    except KeyError as error:
                        raise QtTargetAssignmentError(
                            "candidate references a missing attribution"
                        ) from error
                    if attribution.blamed_historical_commit != commit_id:
                        raise QtTargetAssignmentError(
                            "candidate attribution historical identity mismatch"
                        )
                    attributions.append(attribution)
                fixing = tuple(sorted({x.fixing_commit for x in attributions}))
                issues = tuple(sorted({x.issue_identifier for x in attributions}))
                evidence = tuple(
                    sorted({x.target_evidence_identifier for x in attributions})
                )
                historical_time = datetime.fromisoformat(
                    commit_by_id[commit_id].committed_at
                )
                if any(
                    fix not in commit_by_id
                    or historical_time
                    >= datetime.fromisoformat(commit_by_id[fix].committed_at)
                    for fix in fixing
                ):
                    raise QtTargetAssignmentError(
                        "candidate temporal/provenance inconsistency"
                    )
                trace_values = dict(
                    disposition=ScientificTargetDisposition.POSITIVE,
                    historical_commit=commit_id,
                    candidate_identifiers=candidate_ids,
                    attribution_identifiers=attribution_ids,
                    fixing_commits=fixing,
                    issue_identifiers=issues,
                    target_evidence_identifiers=evidence,
                    exclusion_identifiers=(),
                    rationale_code="admissible-candidate-aggregate",
                )
                trace = ScientificTargetEvidenceTrace(
                    **trace_values,
                    trace_identifier=ScientificTargetEvidenceTrace.calculate_identifier(
                        **trace_values
                    ),
                )
                traces.append(trace)
                assignments.append(
                    ScientificTargetAssignment(
                        commit_id,
                        policy.target_field,
                        policy.positive_label,
                        policy.policy_version,
                        candidate_ids,
                        "admissible reproducible candidate evidence",
                    )
                )
            else:
                assignments.append(
                    ScientificTargetAssignment(
                        commit_id,
                        policy.target_field,
                        policy.negative_label,
                        policy.policy_version,
                        (),
                        "eligible commit without admissible candidate evidence",
                    )
                )

        for exclusion in candidates.exclusions:
            disposition = ScientificTargetDisposition(exclusion.disposition.value)
            trace_values = dict(
                disposition=disposition,
                historical_commit=None,
                candidate_identifiers=(),
                attribution_identifiers=(),
                fixing_commits=(exclusion.fixing_commit,),
                issue_identifiers=(exclusion.issue_identifier,),
                target_evidence_identifiers=(exclusion.target_evidence_identifier,),
                exclusion_identifiers=(exclusion.exclusion_identifier,),
                rationale_code=f"candidate-{exclusion.reason.value}",
            )
            traces.append(
                ScientificTargetEvidenceTrace(
                    **trace_values,
                    trace_identifier=ScientificTargetEvidenceTrace.calculate_identifier(
                        **trace_values
                    ),
                )
            )

        assignments = tuple(sorted(assignments, key=lambda x: x.observation_identifier))
        traces = tuple(sorted(traces, key=lambda x: x.trace_identifier))
        positives = sum(x.target_label == policy.positive_label for x in assignments)
        validation = ScientificTargetAssignmentValidation(
            True,
            len(commits.records),
            len(assignments),
            positives,
            len(assignments) - positives,
            sum(x.disposition is ScientificTargetDisposition.EXCLUDED for x in traces),
            sum(
                x.disposition is ScientificTargetDisposition.UNRESOLVED for x in traces
            ),
        )
        payload = {
            "specification_digest": spec.specification_digest,
            "policy_digest": policy.policy_digest,
            "repository_snapshot_digest": spec.repository_snapshot_digest,
            "commit_artifact_digest": spec.commit_artifact_digest,
            "candidate_artifact_digest": spec.candidate_artifact_digest,
            "candidate_binding_digest": spec.candidate_binding_digest,
            "assignments": assignments,
            "evidence_traces": traces,
            "validation": validation,
        }
        artifact = ScientificArtifactReference(
            "qtbase-target-assignments",
            ScientificArtifactRole.TARGET_ASSIGNMENT,
            "artifacts/derived/qtbase-target-assignments.json",
            _artifact_digest(payload),
            spec.schema_version,
            len(assignments),
            metadata={
                "feature_input": False,
                "content_policy": "canonical-scientific-content-only",
            },
        )
        binding_values = dict(
            artifact=artifact,
            specification_digest=spec.specification_digest,
            policy_digest=policy.policy_digest,
            candidate_artifact_digest=spec.candidate_artifact_digest,
            ordered_observation_identifiers=tuple(
                x.observation_identifier for x in assignments
            ),
            ordered_trace_identifiers=tuple(x.trace_identifier for x in traces),
        )
        binding = ScientificTargetAssignmentArtifactBinding(
            **binding_values,
            binding_digest=ScientificTargetAssignmentArtifactBinding.calculate_digest(
                **binding_values
            ),
        )
        return ScientificTargetAssignmentResult(
            spec, policy, assignments, traces, validation, binding
        )

    @staticmethod
    def _validate_inputs(specification, commits, candidates) -> None:
        if (
            not isinstance(specification, QtTargetAssignmentSpecification)
            or not isinstance(commits, QtCommitExtractionResult)
            or not isinstance(candidates, ScientificCandidateConstructionResult)
        ):
            raise TypeError("target assignment input uses an invalid contract")
        spec = specification.scientific_specification
        binding = candidates.artifact_binding
        actual = (
            commits.source_snapshot_digest,
            commits.artifact.content_digest,
            binding.artifact.content_digest,
            binding.binding_digest,
            candidates.specification.specification_digest,
            candidates.policy.policy_digest,
        )
        expected = (
            spec.repository_snapshot_digest,
            spec.commit_artifact_digest,
            spec.candidate_artifact_digest,
            spec.candidate_binding_digest,
            spec.candidate_specification_digest,
            spec.candidate_policy_digest,
        )
        if actual != expected:
            raise ValueError(
                "target specification does not match upstream artifact identity"
            )
        if (
            binding.repository_snapshot_digest != commits.source_snapshot_digest
            or binding.upstream_artifact_digests.get("commits")
            != commits.artifact.content_digest
        ):
            raise ValueError(
                "candidate artifact provenance does not match commit artifact"
            )
        if (
            tuple(x.candidate_identifier for x in candidates.candidates)
            != binding.ordered_candidate_identifiers
        ):
            raise ValueError("candidate artifact binding mismatch")
        commit_level = {
            x.blamed_historical_commit
            for x in candidates.candidates
            if x.aggregation_level is ScientificCandidateAggregationLevel.COMMIT
        }
        all_levels = {x.blamed_historical_commit for x in candidates.candidates}
        if commit_level != all_levels:
            raise QtTargetAssignmentError(
                "candidate aggregation levels are inconsistent"
            )
        if any(
            x.disposition is ScientificCandidateDisposition.ADMISSIBLE
            for x in candidates.exclusions
        ):
            raise QtTargetAssignmentError(
                "candidate exclusion has conflicting disposition"
            )
