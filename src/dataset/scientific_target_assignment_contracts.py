"""Immutable contracts for reproducible commit-level target assignment."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, fields
from enum import Enum, StrEnum
from types import MappingProxyType

from dataset.scientific_builder_contracts import (
    ScientificArtifactReference,
    ScientificArtifactRole,
    ScientificTargetAssignment,
)

__all__ = [
    "ScientificTargetDisposition",
    "ScientificTargetAssignmentPolicy",
    "ScientificTargetAssignmentSpecification",
    "ScientificTargetEvidenceTrace",
    "ScientificTargetAssignmentValidation",
    "ScientificTargetAssignmentArtifactBinding",
    "ScientificTargetAssignmentResult",
]


class ScientificTargetDisposition(StrEnum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    EXCLUDED = "excluded"
    UNRESOLVED = "unresolved"


_EMPTY: Mapping[str, object] = MappingProxyType({})
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_OID = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
_BANNED = {
    "bug_confidence",
    "confidence",
    "feature",
    "feature_name",
    "feature_value",
    "prediction",
    "probability",
    "msg_has_bug_kw",
    "has_bug_keyword",
}


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _digest(value: object, name: str) -> str:
    value = _text(value, name)
    if not _SHA256.fullmatch(value):
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")
    return value


def _ordered(values: Sequence[object], name: str) -> tuple[str, ...]:
    result = tuple(_text(item, name) for item in values)
    if result != tuple(sorted(set(result))):
        raise ValueError(f"{name} must be unique and deterministically ordered")
    return result


def _enum(value: object, kind: type[Enum], name: str):
    try:
        return kind(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"invalid {name}: {value!r}") from error


def _freeze(value: object, path: str = "metadata") -> object:
    if isinstance(value, Mapping):
        result = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(f"{path} keys must be strings")
            normalized = re.sub(r"[^a-z0-9]+", "_", key.lower()).strip("_")
            if normalized in _BANNED:
                raise ValueError(f"{path} contains forbidden predictive field {key!r}")
            result[key] = _freeze(item, f"{path}.{key}")
        return MappingProxyType(result)
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item, path) for item in value)
    if value is None or type(value) in {str, bool, int, float}:
        if isinstance(value, str) and value.startswith("/"):
            raise ValueError(f"{path} must not contain absolute local paths")
        return value
    raise TypeError(f"{path} must contain deterministic JSON-compatible values")


def _thaw(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    if hasattr(value, "to_dict"):
        return value.to_dict()
    return value


def _dict(value: object) -> dict[str, object]:
    return {item.name: _thaw(getattr(value, item.name)) for item in fields(value)}


def _canonical(value: object) -> str:
    payload = json.dumps(
        _thaw(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class ScientificTargetAssignmentPolicy:
    policy_version: str
    unit_of_prediction: str
    target_field: str
    positive_label: int
    negative_label: int
    positive_policy: str
    negative_policy: str
    unresolved_policy: str
    excluded_policy: str
    aggregation_policy: str
    temporal_policy: str
    ordering_policy: str
    forbidden_feature_sources: tuple[str, ...]
    policy_digest: str
    metadata: Mapping[str, object] = field(default_factory=lambda: _EMPTY)

    def __post_init__(self) -> None:
        for name in (
            "policy_version",
            "unit_of_prediction",
            "target_field",
            "positive_policy",
            "negative_policy",
            "unresolved_policy",
            "excluded_policy",
            "aggregation_policy",
            "temporal_policy",
            "ordering_policy",
        ):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        if self.unit_of_prediction != "commit" or (
            self.positive_label,
            self.negative_label,
        ) != (1, 0):
            raise ValueError("target policy must define binary commit-level assignment")
        object.__setattr__(
            self,
            "forbidden_feature_sources",
            _ordered(self.forbidden_feature_sources, "forbidden_feature_sources"),
        )
        object.__setattr__(self, "metadata", _freeze(self.metadata))
        if self.policy_digest != self.calculate_digest(**self._content()):
            raise ValueError("policy_digest must derive from scientific content")

    def _content(self):
        return {
            x.name: getattr(self, x.name)
            for x in fields(self)
            if x.name not in {"policy_digest", "metadata"}
        }

    @classmethod
    def calculate_digest(cls, **content: object) -> str:
        content.pop("policy_digest", None)
        content.pop("metadata", None)
        return _canonical(content)

    def to_dict(self):
        return _dict(self)


@dataclass(frozen=True, slots=True)
class ScientificTargetAssignmentSpecification:
    schema_version: str
    specification_version: str
    repository_snapshot_digest: str
    commit_artifact_digest: str
    candidate_artifact_digest: str
    candidate_binding_digest: str
    candidate_specification_digest: str
    candidate_policy_digest: str
    policy_digest: str
    specification_digest: str
    metadata: Mapping[str, object] = field(default_factory=lambda: _EMPTY)

    def __post_init__(self) -> None:
        for name in ("schema_version", "specification_version"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        for name in (
            "repository_snapshot_digest",
            "commit_artifact_digest",
            "candidate_artifact_digest",
            "candidate_binding_digest",
            "candidate_specification_digest",
            "candidate_policy_digest",
            "policy_digest",
        ):
            object.__setattr__(self, name, _digest(getattr(self, name), name))
        object.__setattr__(self, "metadata", _freeze(self.metadata))
        if self.specification_digest != self.calculate_digest(**self._content()):
            raise ValueError("specification_digest must derive from scientific content")

    def _content(self):
        return {
            x.name: getattr(self, x.name)
            for x in fields(self)
            if x.name not in {"specification_digest", "metadata"}
        }

    @classmethod
    def calculate_digest(cls, **content: object) -> str:
        content.pop("specification_digest", None)
        content.pop("metadata", None)
        return _canonical(content)

    def to_dict(self):
        return _dict(self)


@dataclass(frozen=True, slots=True)
class ScientificTargetEvidenceTrace:
    trace_identifier: str
    disposition: ScientificTargetDisposition
    historical_commit: str | None
    candidate_identifiers: tuple[str, ...]
    attribution_identifiers: tuple[str, ...]
    fixing_commits: tuple[str, ...]
    issue_identifiers: tuple[str, ...]
    target_evidence_identifiers: tuple[str, ...]
    exclusion_identifiers: tuple[str, ...]
    rationale_code: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "disposition",
            _enum(self.disposition, ScientificTargetDisposition, "disposition"),
        )
        if self.historical_commit is not None and not _OID.fullmatch(
            self.historical_commit
        ):
            raise ValueError(
                "historical_commit must be a complete Git object identifier"
            )
        for name in (
            "candidate_identifiers",
            "attribution_identifiers",
            "fixing_commits",
            "issue_identifiers",
            "target_evidence_identifiers",
            "exclusion_identifiers",
        ):
            object.__setattr__(self, name, _ordered(getattr(self, name), name))
        object.__setattr__(
            self, "rationale_code", _text(self.rationale_code, "rationale_code")
        )
        if self.disposition is ScientificTargetDisposition.POSITIVE and (
            self.historical_commit is None or not self.candidate_identifiers
        ):
            raise ValueError(
                "positive trace requires a historical commit and candidates"
            )
        if (
            self.disposition
            in {
                ScientificTargetDisposition.EXCLUDED,
                ScientificTargetDisposition.UNRESOLVED,
            }
            and not self.exclusion_identifiers
        ):
            raise ValueError("excluded/unresolved trace requires exclusions")
        if self.trace_identifier != self.calculate_identifier(**self._content()):
            raise ValueError("trace_identifier must derive from scientific content")

    def _content(self):
        return {
            x.name: getattr(self, x.name)
            for x in fields(self)
            if x.name != "trace_identifier"
        }

    @classmethod
    def calculate_identifier(cls, **content: object) -> str:
        content.pop("trace_identifier", None)
        return _canonical(content)

    def to_dict(self):
        return _dict(self)


@dataclass(frozen=True, slots=True)
class ScientificTargetAssignmentValidation:
    is_valid: bool
    eligible_commit_count: int
    assignment_count: int
    positive_count: int
    negative_count: int
    excluded_trace_count: int
    unresolved_trace_count: int
    error_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if type(self.is_valid) is not bool:
            raise TypeError("is_valid must be bool")
        for name in (
            "eligible_commit_count",
            "assignment_count",
            "positive_count",
            "negative_count",
            "excluded_trace_count",
            "unresolved_trace_count",
        ):
            if type(getattr(self, name)) is not int or getattr(self, name) < 0:
                raise ValueError(f"{name} must be non-negative")
        object.__setattr__(
            self, "error_codes", _ordered(self.error_codes, "error_codes")
        )
        if self.is_valid == bool(self.error_codes):
            raise ValueError("is_valid must agree with error_codes")

    def to_dict(self):
        return _dict(self)


@dataclass(frozen=True, slots=True)
class ScientificTargetAssignmentArtifactBinding:
    artifact: ScientificArtifactReference
    specification_digest: str
    policy_digest: str
    candidate_artifact_digest: str
    ordered_observation_identifiers: tuple[str, ...]
    ordered_trace_identifiers: tuple[str, ...]
    binding_digest: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.artifact, ScientificArtifactReference)
            or self.artifact.artifact_role
            is not ScientificArtifactRole.TARGET_ASSIGNMENT
        ):
            raise ValueError("artifact must have target-assignment role")
        for name in (
            "specification_digest",
            "policy_digest",
            "candidate_artifact_digest",
        ):
            object.__setattr__(self, name, _digest(getattr(self, name), name))
        for name in ("ordered_observation_identifiers", "ordered_trace_identifiers"):
            object.__setattr__(self, name, _ordered(getattr(self, name), name))
        if self.binding_digest != self.calculate_digest(**self._content()):
            raise ValueError("binding_digest must derive from scientific content")

    def _content(self):
        return {
            x.name: getattr(self, x.name)
            for x in fields(self)
            if x.name != "binding_digest"
        }

    @classmethod
    def calculate_digest(cls, **content: object) -> str:
        content.pop("binding_digest", None)
        return _canonical(content)

    def to_dict(self):
        return _dict(self)


@dataclass(frozen=True, slots=True)
class ScientificTargetAssignmentResult:
    specification: ScientificTargetAssignmentSpecification
    policy: ScientificTargetAssignmentPolicy
    assignments: tuple[ScientificTargetAssignment, ...]
    evidence_traces: tuple[ScientificTargetEvidenceTrace, ...]
    validation: ScientificTargetAssignmentValidation
    artifact_binding: ScientificTargetAssignmentArtifactBinding

    def __post_init__(self) -> None:
        if not isinstance(
            self.specification, ScientificTargetAssignmentSpecification
        ) or not isinstance(self.policy, ScientificTargetAssignmentPolicy):
            raise TypeError("invalid target contracts")
        assignments = tuple(self.assignments)
        traces = tuple(self.evidence_traces)
        if any(
            not isinstance(x, ScientificTargetAssignment) for x in assignments
        ) or any(not isinstance(x, ScientificTargetEvidenceTrace) for x in traces):
            raise TypeError("invalid target result record")
        observations = tuple(x.observation_identifier for x in assignments)
        trace_ids = tuple(x.trace_identifier for x in traces)
        if observations != tuple(sorted(set(observations))):
            raise ValueError("assignments must be unique and deterministically ordered")
        if trace_ids != tuple(sorted(set(trace_ids))):
            raise ValueError("traces must be unique and deterministically ordered")
        if any(
            x.target_field != self.policy.target_field
            or x.assignment_policy_version != self.policy.policy_version
            for x in assignments
        ):
            raise ValueError("assignment policy identity mismatch")
        if (
            not self.validation.is_valid
            or self.validation.assignment_count != len(assignments)
            or self.validation.eligible_commit_count != len(assignments)
        ):
            raise ValueError("validation counts disagree with result")
        positives = sum(
            x.target_label == self.policy.positive_label for x in assignments
        )
        negatives = sum(
            x.target_label == self.policy.negative_label for x in assignments
        )
        if (
            positives != self.validation.positive_count
            or negatives != self.validation.negative_count
            or positives + negatives != len(assignments)
        ):
            raise ValueError("target counts disagree with result")
        if (
            observations != self.artifact_binding.ordered_observation_identifiers
            or trace_ids != self.artifact_binding.ordered_trace_identifiers
        ):
            raise ValueError("artifact binding identifiers disagree with result")
        object.__setattr__(self, "assignments", assignments)
        object.__setattr__(self, "evidence_traces", traces)

    def to_dict(self):
        return _dict(self)
