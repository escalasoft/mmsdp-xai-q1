"""Deterministic construction of conservative Qt target-evidence provenance."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path
from types import MappingProxyType

from dataset.scientific_builder_contracts import (
    ScientificArtifactReference,
    ScientificArtifactRole,
    ScientificTargetEvidenceRecord,
)
from extraction.qt_commit_extraction import QtCommitExtractionResult
from extraction.qt_commit_issue_linking import QtCommitIssueLinkingResult
from extraction.qt_issue_extraction import QtIssueExtractionResult, QtIssueRecord

__all__ = [
    "QtTargetEvidenceSpecification",
    "QtTargetEvidenceConstructionResult",
    "QtTargetEvidenceConstructor",
]

_PROJECT_NAME = "qtbase"
_POLICIES = {
    "ordering_policy": "observation-evidence-identifier",
    "issue_type_policy": "preserve-source-native-type",
    "link_reference_policy": "explicit-link-provenance-only",
    "temporal_policy": "source-timestamps-normalized-to-utc",
    "unsupported_evidence_policy": "retain-as-non-supporting-audit-evidence",
}
_PLACEHOLDERS = {
    "commit_artifact_digest": "commit-artifact-digest-required-before-execution",
    "issue_artifact_digest": "issue-artifact-digest-required-before-execution",
    "linking_artifact_digest": "linking-artifact-digest-required-before-execution",
}
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_MEMORY_ADDRESS = re.compile(r"(?:^|\s)0x[0-9a-fA-F]{6,}(?:\s|$)")
_EMPTY: Mapping[str, object] = MappingProxyType({})
_BANNED_KEYS = {
    "allowed_as_feature",
    "bug_confidence",
    "contains_fix_keyword",
    "credentials",
    "duration",
    "feature_enable",
    "feature_enabled",
    "has_bug_keyword",
    "hostname",
    "is_bug",
    "is_buggy",
    "issue_link_indicator",
    "label",
    "label_confidence",
    "local_path",
    "memory_address",
    "msg_has_bug_kw",
    "password",
    "prediction",
    "probability",
    "runtime_timestamp",
    "target",
    "target_label",
    "target_probability",
    "username",
}
_EVIDENCE_TYPES = {
    "explicit-commit-issue-link",
    "linked-source-native-defect-type",
    "linked-non-defect-issue-type",
    "unresolved-or-unsupported-link-evidence",
    "temporal-consistency-evidence",
}
_CONFIDENCE_CATEGORIES = {
    "direct-explicit-reference",
    "source-native-defect-type",
    "insufficient-for-target-assignment",
    "non-supporting",
    "requires-target-policy-review",
}
_NON_DEFECT_TYPES = {"task", "improvement"}
_DEFECT_TYPES = {"bug"}


def _key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def _banned_key(value: str) -> bool:
    normalized = _key(value)
    if normalized in _BANNED_KEYS:
        return True
    parts = set(normalized.split("_"))
    return bool(
        parts
        & {
            "credential",
            "credentials",
            "duration",
            "hostname",
            "password",
            "prediction",
            "probability",
            "target",
            "username",
        }
        or normalized.endswith("_local_path")
        or normalized.endswith("_runtime_timestamp")
    )


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _freeze(value: object, path: str = "metadata") -> object:
    if isinstance(value, Mapping):
        result: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(f"{path} keys must be strings")
            if _banned_key(key):
                raise ValueError(f"{path} must not contain {key!r}")
            result[key] = _freeze(item, f"{path}.{key}")
        return MappingProxyType(result)
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item, path) for item in value)
    if value is None or type(value) in {bool, int}:
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{path} must contain finite values")
        return value
    if isinstance(value, str):
        if Path(value).is_absolute():
            raise ValueError(f"{path} must not contain local absolute paths")
        if _MEMORY_ADDRESS.search(value):
            raise ValueError(f"{path} must not contain memory addresses")
        return value
    raise TypeError(f"{path} must contain deterministic JSON-compatible values")


def _thaw(value: object) -> object:
    if is_dataclass(value) and not isinstance(value, type):
        return {item.name: _thaw(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    if isinstance(value, ScientificArtifactRole):
        return value.value
    return value


def _canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(
            _thaw(value),
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _scientific_record_content(
    record: ScientificTargetEvidenceRecord,
) -> dict[str, object]:
    metadata = record.metadata
    return {
        "observation_identifier": record.observation_identifier,
        "evidence_identifier": record.evidence_identifier,
        "evidence_type": record.evidence_type,
        "source_artifact_digest": record.source_artifact.content_digest,
        "evidence_timestamp": record.evidence_timestamp,
        "evidence_summary": record.evidence_summary,
        "supports_positive_label": record.supports_positive_label,
        "confidence_category": record.confidence_category,
        "issue_identifier": metadata["issue_identifier"],
        "source_native_issue_type": metadata["source_native_issue_type"],
        "link_reference_type": metadata["link_reference_type"],
        "reference_locations": metadata["reference_locations"],
        "linking_artifact_digest": metadata["linking_artifact_digest"],
        "issue_source_record_digest": metadata["issue_source_record_digest"],
        "timestamp_source": metadata["timestamp_source"],
    }


def _record_identifier_content(
    observation_identifier: str,
    issue_identifier: object,
    reference_type: object,
    reference_locations: object,
    evidence_type: str,
    linking_artifact_digest: object,
) -> dict[str, object]:
    return {
        "observation_identifier": observation_identifier,
        "issue_identifier": issue_identifier,
        "link_reference_type": reference_type,
        "reference_locations": reference_locations,
        "evidence_type": evidence_type,
        "source_artifact_digest": linking_artifact_digest,
    }


@dataclass(frozen=True, slots=True)
class QtTargetEvidenceSpecification:
    """Immutable scientific identity and controlled target-evidence policy."""

    project_name: str
    commit_artifact_digest: str
    issue_artifact_digest: str
    linking_artifact_digest: str
    evidence_policy_version: str
    ordering_policy: str = _POLICIES["ordering_policy"]
    issue_type_policy: str = _POLICIES["issue_type_policy"]
    link_reference_policy: str = _POLICIES["link_reference_policy"]
    temporal_policy: str = _POLICIES["temporal_policy"]
    unsupported_evidence_policy: str = _POLICIES["unsupported_evidence_policy"]
    metadata: Mapping[str, object] = field(default_factory=lambda: _EMPTY)

    def __post_init__(self) -> None:
        if self.project_name != _PROJECT_NAME:
            raise ValueError("project_name must equal 'qtbase'")
        for name, placeholder in _PLACEHOLDERS.items():
            value = _text(getattr(self, name), name)
            if value != placeholder and not _SHA256.fullmatch(value):
                raise ValueError(f"{name} must be a lowercase SHA-256 digest")
            object.__setattr__(self, name, value)
        object.__setattr__(
            self,
            "evidence_policy_version",
            _text(self.evidence_policy_version, "evidence_policy_version"),
        )
        for name, expected in _POLICIES.items():
            if getattr(self, name) != expected:
                raise ValueError(f"{name} must equal {expected!r}")
        object.__setattr__(self, "metadata", _freeze(self.metadata))

    def to_dict(self) -> dict[str, object]:
        return _thaw(self)  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class QtTargetEvidenceConstructionResult:
    """Validated immutable output of target-evidence construction."""

    specification: QtTargetEvidenceSpecification
    commit_extraction_result: QtCommitExtractionResult
    issue_extraction_result: QtIssueExtractionResult
    commit_issue_linking_result: QtCommitIssueLinkingResult
    evidence_records: tuple[ScientificTargetEvidenceRecord, ...]
    evidence_artifact: ScientificArtifactReference
    evidence_record_count: int
    observations_with_evidence_count: int
    observations_without_evidence_count: int
    supporting_evidence_count: int
    non_supporting_evidence_count: int
    unresolved_evidence_count: int
    evidence_type_counts: Mapping[str, int]
    evidence_identity_digest: str
    stage_outcome: str
    metadata: Mapping[str, object] = field(default_factory=lambda: _EMPTY)

    def __post_init__(self) -> None:
        _validate_inputs(
            self.specification,
            self.commit_extraction_result,
            self.issue_extraction_result,
            self.commit_issue_linking_result,
            reject_placeholders=True,
        )
        records = tuple(self.evidence_records)
        if any(
            not isinstance(item, ScientificTargetEvidenceRecord) for item in records
        ):
            raise TypeError(
                "evidence_records must contain ScientificTargetEvidenceRecord"
            )
        key = lambda item: (item.observation_identifier, item.evidence_identifier)  # noqa: E731
        if records != tuple(sorted(records, key=key)):
            raise ValueError("evidence records must be deterministically ordered")
        identifiers = tuple(item.evidence_identifier for item in records)
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("evidence records must be unique")
        commit_ids = {item.commit_id for item in self.commit_extraction_result.records}
        if any(item.observation_identifier not in commit_ids for item in records):
            raise ValueError("evidence observation is absent from commit artifact")
        issue_ids = {
            item.issue_identifier for item in self.issue_extraction_result.issues
        }
        if any(item.metadata["issue_identifier"] not in issue_ids for item in records):
            raise ValueError("evidence issue is absent from issue artifact")
        linked_locations: dict[tuple[str, str, str], set[str]] = {}
        for link in self.commit_issue_linking_result.links:
            link_key = (
                link.commit_revision,
                link.issue_identifier,
                link.reference_type,
            )
            linked_locations.setdefault(link_key, set()).add(link.reference_location)
        for item in records:
            if item.source_artifact != self.issue_extraction_result.extraction_artifact:
                raise ValueError("evidence source artifact is inconsistent")
            locations = item.metadata["reference_locations"]
            if (
                not isinstance(locations, tuple)
                or not locations
                or locations != tuple(sorted(set(locations)))
            ):
                raise ValueError(
                    "reference_locations must be non-empty, unique, and sorted"
                )
            link_key = (
                item.observation_identifier,
                item.metadata["issue_identifier"],
                item.metadata["link_reference_type"],
            )
            if locations != tuple(sorted(linked_locations.get(link_key, set()))):
                raise ValueError("reference_locations do not match linking provenance")
            expected_identifier = _digest(
                _record_identifier_content(
                    item.observation_identifier,
                    item.metadata["issue_identifier"],
                    item.metadata["link_reference_type"],
                    locations,
                    item.evidence_type,
                    item.metadata["linking_artifact_digest"],
                )
            )
            if item.evidence_identifier != expected_identifier:
                raise ValueError("evidence identifier is inconsistent")
        type_counts = dict(
            sorted(Counter(item.evidence_type for item in records).items())
        )
        unresolved = sum(
            item.evidence_type == "unresolved-or-unsupported-link-evidence"
            for item in records
        )
        supporting = sum(item.supports_positive_label for item in records)
        if supporting:
            raise ValueError(
                "target evidence must not support a positive label before assignment"
            )
        if any(
            item.evidence_type == "unresolved-or-unsupported-link-evidence"
            and item.supports_positive_label
            for item in records
        ):
            raise ValueError("unresolved evidence must not be supporting")
        non_supporting = len(records) - supporting - unresolved
        with_evidence = len({item.observation_identifier for item in records})
        expected = (
            len(records),
            with_evidence,
            len(commit_ids) - with_evidence,
            supporting,
            non_supporting,
            unresolved,
        )
        actual = (
            self.evidence_record_count,
            self.observations_with_evidence_count,
            self.observations_without_evidence_count,
            self.supporting_evidence_count,
            self.non_supporting_evidence_count,
            self.unresolved_evidence_count,
        )
        if actual != expected or dict(self.evidence_type_counts) != type_counts:
            raise ValueError("target-evidence aggregate counts are inconsistent")
        if any(
            item.evidence_type not in _EVIDENCE_TYPES
            or item.confidence_category not in _CONFIDENCE_CATEGORIES
            for item in records
        ):
            raise ValueError("evidence type or confidence category is not controlled")
        content = _evidence_content(self.specification, records)
        if (
            self.evidence_artifact.artifact_role
            is not ScientificArtifactRole.TARGET_EVIDENCE
            or self.evidence_artifact.record_count != len(records)
            or self.evidence_artifact.content_digest != _digest(content)
        ):
            raise ValueError("target-evidence artifact is inconsistent")
        identity = _digest(
            {
                "scientific_evidence": [
                    _scientific_record_content(item) for item in records
                ]
            }
        )
        if self.evidence_identity_digest != identity:
            raise ValueError("evidence_identity_digest is inconsistent")
        if self.stage_outcome != "target-evidence-constructed":
            raise ValueError("stage_outcome is not controlled")
        object.__setattr__(self, "evidence_records", records)
        object.__setattr__(self, "evidence_type_counts", MappingProxyType(type_counts))
        object.__setattr__(self, "metadata", _freeze(self.metadata))

    def to_dict(self) -> dict[str, object]:
        return _thaw(self)  # type: ignore[return-value]


def _validate_inputs(
    specification: QtTargetEvidenceSpecification,
    commits: QtCommitExtractionResult,
    issues: QtIssueExtractionResult,
    links: QtCommitIssueLinkingResult,
    *,
    reject_placeholders: bool,
) -> None:
    if not isinstance(specification, QtTargetEvidenceSpecification):
        raise TypeError("specification must be QtTargetEvidenceSpecification")
    if not isinstance(commits, QtCommitExtractionResult):
        raise TypeError("commit_extraction_result must be QtCommitExtractionResult")
    if not isinstance(issues, QtIssueExtractionResult):
        raise TypeError("issue_extraction_result must be QtIssueExtractionResult")
    if not isinstance(links, QtCommitIssueLinkingResult):
        raise TypeError(
            "commit_issue_linking_result must be QtCommitIssueLinkingResult"
        )
    if reject_placeholders and any(
        getattr(specification, name) == placeholder
        for name, placeholder in _PLACEHOLDERS.items()
    ):
        raise ValueError(
            "artifact digest placeholders must be resolved before execution"
        )
    expected = (
        commits.artifact.content_digest,
        issues.extraction_artifact.content_digest,
        links.artifact_digest,
    )
    actual = (
        specification.commit_artifact_digest,
        specification.issue_artifact_digest,
        specification.linking_artifact_digest,
    )
    if actual != expected:
        raise ValueError("specification artifact digests do not match inputs")
    if (
        links.specification.commit_artifact_digest != commits.artifact.content_digest
        or links.specification.issue_artifact_digest
        != issues.extraction_artifact.content_digest
    ):
        raise ValueError("linking result belongs to different input artifacts")
    if issues.specification.project_name != specification.project_name:
        raise ValueError(
            "issue project identity does not match target-evidence project"
        )
    if commits.artifact.artifact_name != "qtbase-commits":
        raise ValueError("commit artifact does not use the controlled Qt Base identity")
    commit_ids = {item.commit_id for item in commits.records}
    issue_ids = {item.issue_identifier for item in issues.issues}
    if any(item.commit_revision not in commit_ids for item in links.links):
        raise ValueError("linked commit is absent from commit artifact")
    if any(item.issue_identifier not in issue_ids for item in links.links):
        raise ValueError("linked issue is absent from issue artifact")


def _evidence_content(
    specification: QtTargetEvidenceSpecification,
    records: tuple[ScientificTargetEvidenceRecord, ...],
) -> dict[str, object]:
    return {
        "artifact_role": ScientificArtifactRole.TARGET_EVIDENCE.value,
        "project_name": specification.project_name,
        "input_artifact_digests": {
            "commit": specification.commit_artifact_digest,
            "issue": specification.issue_artifact_digest,
            "linking": specification.linking_artifact_digest,
        },
        "evidence_policy_version": specification.evidence_policy_version,
        "policies": {name: getattr(specification, name) for name in _POLICIES},
        "records": [_scientific_record_content(item) for item in records],
    }


class QtTargetEvidenceConstructor:
    """Construct target provenance without assigning labels or producing features."""

    constructor_name = "qt-target-evidence-constructor"

    def construct(
        self,
        specification: QtTargetEvidenceSpecification,
        commit_extraction_result: QtCommitExtractionResult,
        issue_extraction_result: QtIssueExtractionResult,
        commit_issue_linking_result: QtCommitIssueLinkingResult,
    ) -> QtTargetEvidenceConstructionResult:
        _validate_inputs(
            specification,
            commit_extraction_result,
            issue_extraction_result,
            commit_issue_linking_result,
            reject_placeholders=True,
        )
        commits = {item.commit_id: item for item in commit_extraction_result.records}
        issues = {
            item.issue_identifier: item for item in issue_extraction_result.issues
        }
        grouped_links: dict[tuple[str, str, str], set[str]] = {}
        for item in commit_issue_linking_result.links:
            link_key = (
                item.commit_revision,
                item.issue_identifier,
                item.reference_type,
            )
            grouped_links.setdefault(link_key, set()).add(item.reference_location)
        records = tuple(
            sorted(
                (
                    self._record(
                        specification,
                        commits[commit_id].committed_at,
                        issues[issue_id],
                        issue_extraction_result.extraction_artifact,
                        commit_id,
                        issue_id,
                        reference_type,
                        tuple(sorted(reference_locations)),
                    )
                    for (
                        commit_id,
                        issue_id,
                        reference_type,
                    ), reference_locations in grouped_links.items()
                ),
                key=lambda item: (
                    item.observation_identifier,
                    item.evidence_identifier,
                ),
            )
        )
        content = _evidence_content(specification, records)
        artifact = ScientificArtifactReference(
            artifact_name="qtbase-target-evidence",
            artifact_role=ScientificArtifactRole.TARGET_EVIDENCE,
            repository_relative_path="artifacts/derived/qtbase-target-evidence.json",
            content_digest=_digest(content),
            schema_version=specification.evidence_policy_version,
            record_count=len(records),
            metadata={"content_policy": "canonical-scientific-evidence-only"},
        )
        type_counts = dict(
            sorted(Counter(item.evidence_type for item in records).items())
        )
        unresolved = sum(
            item.evidence_type == "unresolved-or-unsupported-link-evidence"
            for item in records
        )
        supporting = sum(item.supports_positive_label for item in records)
        with_evidence = len({item.observation_identifier for item in records})
        return QtTargetEvidenceConstructionResult(
            specification=specification,
            commit_extraction_result=commit_extraction_result,
            issue_extraction_result=issue_extraction_result,
            commit_issue_linking_result=commit_issue_linking_result,
            evidence_records=records,
            evidence_artifact=artifact,
            evidence_record_count=len(records),
            observations_with_evidence_count=with_evidence,
            observations_without_evidence_count=(
                len(commit_extraction_result.records) - with_evidence
            ),
            supporting_evidence_count=supporting,
            non_supporting_evidence_count=len(records) - supporting - unresolved,
            unresolved_evidence_count=unresolved,
            evidence_type_counts=type_counts,
            evidence_identity_digest=_digest(
                {
                    "scientific_evidence": [
                        _scientific_record_content(item) for item in records
                    ]
                }
            ),
            stage_outcome="target-evidence-constructed",
            metadata={"count_policy": "supporting-non-supporting-unresolved-exclusive"},
        )

    @staticmethod
    def _record(
        specification: QtTargetEvidenceSpecification,
        committed_at: str,
        issue: QtIssueRecord,
        issue_artifact: ScientificArtifactReference,
        commit_id: str,
        issue_id: str,
        reference_type: str,
        reference_locations: tuple[str, ...],
    ) -> ScientificTargetEvidenceRecord:
        native_type = issue.issue_type
        normalized_type = native_type.casefold() if native_type else None
        if normalized_type in _DEFECT_TYPES:
            evidence_type = "linked-source-native-defect-type"
            supports = False
            confidence = "insufficient-for-target-assignment"
        elif normalized_type in _NON_DEFECT_TYPES:
            evidence_type = "linked-non-defect-issue-type"
            supports = False
            confidence = "non-supporting"
        else:
            evidence_type = "unresolved-or-unsupported-link-evidence"
            supports = False
            confidence = "requires-target-policy-review"
        identity = _record_identifier_content(
            commit_id,
            issue_id,
            reference_type,
            reference_locations,
            evidence_type,
            specification.linking_artifact_digest,
        )
        timestamp = issue.created_timestamp or committed_at
        timestamp_source = (
            "issue-created-timestamp"
            if issue.created_timestamp is not None
            else "commit-committed-timestamp"
        )
        shown_type = (
            native_type
            if normalized_type in _DEFECT_TYPES | _NON_DEFECT_TYPES
            else "<other-or-missing>"
        )
        summary = (
            f"Explicit {reference_type} reference to {issue_id}; "
            f"source-native issue type: {shown_type}."
        )
        return ScientificTargetEvidenceRecord(
            observation_identifier=commit_id,
            evidence_identifier=_digest(identity),
            evidence_type=evidence_type,
            source_artifact=issue_artifact,
            evidence_timestamp=timestamp,
            evidence_summary=summary,
            supports_positive_label=supports,
            confidence_category=confidence,
            metadata={
                "issue_identifier": issue_id,
                "source_native_issue_type": native_type,
                "link_reference_type": reference_type,
                "reference_locations": reference_locations,
                "linking_artifact_digest": specification.linking_artifact_digest,
                "issue_source_record_digest": issue.source_record_digest,
                "timestamp_source": timestamp_source,
                "semantic_limit": "evidence-not-target-assignment",
            },
        )
