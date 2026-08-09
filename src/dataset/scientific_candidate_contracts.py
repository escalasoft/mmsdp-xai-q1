"""Immutable scientific contracts for defect-inducing candidate evidence."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, fields
from enum import Enum, StrEnum
from types import MappingProxyType

from dataset.scientific_builder_contracts import (
    ScientificArtifactReference,
    ScientificArtifactRole,
)

__all__ = [
    "ScientificCandidateAggregationLevel",
    "ScientificCandidateAttributionMethod",
    "ScientificCandidateDisposition",
    "ScientificCandidateExclusionReason",
    "ScientificCandidateFileDisposition",
    "ScientificCandidateBlameBoundaryPolicy",
    "ScientificCandidateDeduplicationPolicy",
    "ScientificCandidateOrderingPolicy",
    "ScientificCandidateConstructionSpecification",
    "ScientificCandidateConstructionPolicy",
    "ScientificCandidateAttributionRecord",
    "ScientificDefectInducingCandidateRecord",
    "ScientificCandidateExclusionRecord",
    "ScientificCandidateConstructionValidation",
    "ScientificCandidateArtifactBinding",
    "ScientificCandidateConstructionResult",
]


class ScientificCandidateAggregationLevel(StrEnum):
    LINE = "line"
    HUNK = "hunk"
    COMMIT = "commit"


class ScientificCandidateAttributionMethod(StrEnum):
    LINE_PROVENANCE_BLAME = "line-provenance-blame"


class ScientificCandidateDisposition(StrEnum):
    ADMISSIBLE = "admissible"
    EXCLUDED = "excluded"
    UNRESOLVED = "unresolved"


class ScientificCandidateExclusionReason(StrEnum):
    POLICY_REJECTION = "policy-rejection"
    INCOMPLETE_PROVENANCE = "incomplete-provenance"
    INELIGIBLE_ISSUE = "ineligible-issue"
    INELIGIBLE_FIXING_COMMIT = "ineligible-fixing-commit"
    INELIGIBLE_FILE = "ineligible-file"
    INELIGIBLE_CHANGE = "ineligible-change"
    BLANK_OR_COMMENT_LINE = "blank-or-comment-line"
    FORMATTING_ONLY_CHANGE = "formatting-only-change"
    ATTRIBUTION_FAILURE = "attribution-failure"
    UNBLAMABLE_LINE = "unblamable-line"
    BOUNDARY_COMMIT = "boundary-commit"
    IGNORED_REVISION = "ignored-revision"
    TEMPORAL_INCONSISTENCY = "temporal-inconsistency"
    OUTSIDE_OBSERVATION_WINDOW = "outside-observation-window"


class ScientificCandidateFileDisposition(StrEnum):
    INCLUDED = "included"
    EXCLUDED = "excluded"
    METADATA_ONLY = "metadata-only"


class ScientificCandidateBlameBoundaryPolicy(StrEnum):
    EXCLUDE = "exclude"
    RECORD_UNRESOLVED = "record-unresolved"


class ScientificCandidateDeduplicationPolicy(StrEnum):
    FULL_PROVENANCE = "full-provenance"


class ScientificCandidateOrderingPolicy(StrEnum):
    CANONICAL_PROVENANCE = "canonical-provenance"


_EMPTY: Mapping[str, object] = MappingProxyType({})
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_OBJECT_ID = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
_BANNED = {
    "bug_confidence",
    "confidence",
    "created_at",
    "duration",
    "environment",
    "execution_timestamp",
    "feature",
    "feature_name",
    "feature_value",
    "hostname",
    "label",
    "local_path",
    "machine_identifier",
    "machine_name",
    "memory_address",
    "prediction",
    "probability",
    "runtime_duration",
    "runtime_timestamp",
    "target",
    "target_label",
    "username",
}


def _key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _digest(value: object, name: str) -> str:
    value = _text(value, name)
    if not _SHA256.fullmatch(value):
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")
    return value


def _oid(value: object, name: str) -> str:
    value = _text(value, name)
    if not _OBJECT_ID.fullmatch(value):
        raise ValueError(f"{name} must be a lowercase Git object identifier")
    return value


def _enum(value: object, enum: type[Enum], name: str):
    try:
        return enum(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"invalid {name}: {value!r}") from error


def _ordered(
    values: Sequence[object], name: str, *, required: bool = False
) -> tuple[str, ...]:
    result = tuple(_text(item, name) for item in values)
    if required and not result:
        raise ValueError(f"{name} must not be empty")
    if result != tuple(sorted(set(result))):
        raise ValueError(f"{name} must be unique and deterministically ordered")
    return result


def _freeze(value: object, path: str = "metadata") -> object:
    if isinstance(value, Mapping):
        result: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(f"{path} keys must be strings")
            if _key(key) in _BANNED:
                raise ValueError(f"{path} must not contain forbidden field {key!r}")
            result[key] = _freeze(item, f"{path}.{key}")
        return MappingProxyType(result)
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item, path) for item in value)
    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{path} must contain finite values")
        return value
    if isinstance(value, str):
        if value.startswith("/") or re.search(r"\b0x[0-9a-fA-F]{6,}\b", value):
            raise ValueError(f"{path} must not contain machine-local identity")
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


def _canonical(value: Mapping[str, object]) -> str:
    payload = json.dumps(
        _thaw(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class ScientificCandidateConstructionSpecification:
    schema_version: str
    specification_version: str
    repository_snapshot_digest: str
    commit_artifact_digest: str
    issue_artifact_digest: str
    commit_issue_link_artifact_digest: str
    target_evidence_artifact_digest: str
    diff_artifact_digest: str
    policy_digest: str
    specification_digest: str
    metadata: Mapping[str, object] = field(default_factory=lambda: _EMPTY)

    def __post_init__(self) -> None:
        for name in ("schema_version", "specification_version"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        for name in (
            "repository_snapshot_digest",
            "commit_artifact_digest",
            "issue_artifact_digest",
            "commit_issue_link_artifact_digest",
            "target_evidence_artifact_digest",
            "diff_artifact_digest",
            "policy_digest",
        ):
            object.__setattr__(self, name, _digest(getattr(self, name), name))
        object.__setattr__(self, "metadata", _freeze(self.metadata))
        if self.specification_digest != self.calculate_digest(**self._content()):
            raise ValueError("specification_digest must derive from scientific content")

    def _content(self) -> dict[str, object]:
        return {
            item.name: getattr(self, item.name)
            for item in fields(self)
            if item.name not in {"specification_digest", "metadata"}
        }

    @classmethod
    def calculate_digest(cls, **content: object) -> str:
        content.pop("metadata", None)
        content.pop("specification_digest", None)
        return _canonical(content)

    def to_dict(self) -> dict[str, object]:
        return _dict(self)


@dataclass(frozen=True, slots=True)
class ScientificCandidateConstructionPolicy:
    policy_version: str
    admissible_issue_types: tuple[str, ...]
    admissible_issue_statuses: tuple[str, ...]
    admissible_issue_resolutions: tuple[str, ...]
    admissible_reference_types: tuple[str, ...]
    fixing_commit_policy: str
    temporal_consistency_policy: str
    eligible_change_types: tuple[str, ...]
    included_source_suffixes: tuple[str, ...]
    excluded_path_components: tuple[str, ...]
    generated_file_policy: ScientificCandidateFileDisposition
    vendored_file_policy: ScientificCandidateFileDisposition
    test_file_policy: ScientificCandidateFileDisposition
    binary_file_policy: ScientificCandidateFileDisposition
    renamed_file_policy: ScientificCandidateFileDisposition
    copied_file_policy: ScientificCandidateFileDisposition
    added_file_policy: ScientificCandidateFileDisposition
    deleted_file_policy: ScientificCandidateFileDisposition
    baseline_policy: str
    merge_fix_policy: str
    root_commit_policy: str
    attribution_method: ScientificCandidateAttributionMethod
    blame_options: tuple[str, ...]
    follow_renames: bool
    follow_copies: bool
    whitespace_policy: str
    ignored_revisions: tuple[str, ...]
    blank_line_policy: str
    comment_line_policy: str
    comment_classifier_version: str
    comment_classifier_digest: str
    formatting_only_policy: str
    formatting_classifier_version: str
    formatting_classifier_digest: str
    deletion_hunk_policy: str
    replacement_hunk_policy: str
    attribution_failure_policy: str
    unblamable_line_policy: str
    boundary_policy: ScientificCandidateBlameBoundaryPolicy
    deduplication_policy: ScientificCandidateDeduplicationPolicy
    ordering_policy: ScientificCandidateOrderingPolicy
    aggregation_levels: tuple[ScientificCandidateAggregationLevel, ...]
    policy_digest: str
    metadata: Mapping[str, object] = field(default_factory=lambda: _EMPTY)

    def __post_init__(self) -> None:
        scalar_names = (
            "policy_version",
            "fixing_commit_policy",
            "temporal_consistency_policy",
            "baseline_policy",
            "merge_fix_policy",
            "root_commit_policy",
            "whitespace_policy",
            "blank_line_policy",
            "comment_line_policy",
            "comment_classifier_version",
            "formatting_only_policy",
            "formatting_classifier_version",
            "deletion_hunk_policy",
            "replacement_hunk_policy",
            "attribution_failure_policy",
            "unblamable_line_policy",
        )
        for name in scalar_names:
            object.__setattr__(self, name, _text(getattr(self, name), name))
        for name in (
            "admissible_issue_types",
            "admissible_issue_statuses",
            "admissible_issue_resolutions",
            "admissible_reference_types",
            "eligible_change_types",
            "included_source_suffixes",
            "excluded_path_components",
            "blame_options",
            "ignored_revisions",
        ):
            object.__setattr__(
                self,
                name,
                _ordered(
                    getattr(self, name),
                    name,
                    required=name not in {"ignored_revisions"},
                ),
            )
        for name in (
            "comment_classifier_digest",
            "formatting_classifier_digest",
        ):
            object.__setattr__(self, name, _digest(getattr(self, name), name))
        for name in (
            "generated_file_policy",
            "vendored_file_policy",
            "test_file_policy",
            "binary_file_policy",
            "renamed_file_policy",
            "copied_file_policy",
            "added_file_policy",
            "deleted_file_policy",
        ):
            object.__setattr__(
                self,
                name,
                _enum(getattr(self, name), ScientificCandidateFileDisposition, name),
            )
        object.__setattr__(
            self,
            "attribution_method",
            _enum(
                self.attribution_method,
                ScientificCandidateAttributionMethod,
                "attribution_method",
            ),
        )
        object.__setattr__(
            self,
            "boundary_policy",
            _enum(
                self.boundary_policy,
                ScientificCandidateBlameBoundaryPolicy,
                "boundary_policy",
            ),
        )
        object.__setattr__(
            self,
            "deduplication_policy",
            _enum(
                self.deduplication_policy,
                ScientificCandidateDeduplicationPolicy,
                "deduplication_policy",
            ),
        )
        object.__setattr__(
            self,
            "ordering_policy",
            _enum(
                self.ordering_policy,
                ScientificCandidateOrderingPolicy,
                "ordering_policy",
            ),
        )
        levels = tuple(
            _enum(item, ScientificCandidateAggregationLevel, "aggregation_levels")
            for item in self.aggregation_levels
        )
        if levels != tuple(ScientificCandidateAggregationLevel):
            raise ValueError(
                "aggregation_levels must contain line, hunk, and commit order"
            )
        object.__setattr__(self, "aggregation_levels", levels)
        if (
            type(self.follow_renames) is not bool
            or type(self.follow_copies) is not bool
        ):
            raise TypeError("follow_renames and follow_copies must be bool")
        object.__setattr__(self, "metadata", _freeze(self.metadata))
        if self.policy_digest != self.calculate_digest(**self._content()):
            raise ValueError("policy_digest must derive from scientific content")

    def _content(self) -> dict[str, object]:
        return {
            item.name: getattr(self, item.name)
            for item in fields(self)
            if item.name not in {"policy_digest", "metadata"}
        }

    @classmethod
    def calculate_digest(cls, **content: object) -> str:
        content.pop("metadata", None)
        content.pop("policy_digest", None)
        return _canonical(content)

    def to_dict(self) -> dict[str, object]:
        return _dict(self)


@dataclass(frozen=True, slots=True)
class ScientificCandidateAttributionRecord:
    attribution_identifier: str
    repository_snapshot_digest: str
    fixing_commit: str
    baseline_commit: str
    issue_identifier: str
    target_evidence_identifier: str
    commit_issue_link_identifier: str
    commit_issue_link_artifact_digest: str
    diff_artifact_digest: str
    hunk_identifier: str
    old_path: str
    old_blob_identifier: str
    deleted_preimage_line_number: int
    blamed_historical_commit: str
    attribution_method: ScientificCandidateAttributionMethod
    policy_version: str
    policy_digest: str
    metadata: Mapping[str, object] = field(default_factory=lambda: _EMPTY)

    def __post_init__(self) -> None:
        for name in (
            "issue_identifier",
            "target_evidence_identifier",
            "commit_issue_link_identifier",
            "hunk_identifier",
            "old_path",
            "policy_version",
        ):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        for name in (
            "repository_snapshot_digest",
            "commit_issue_link_artifact_digest",
            "diff_artifact_digest",
            "policy_digest",
        ):
            object.__setattr__(self, name, _digest(getattr(self, name), name))
        for name in (
            "fixing_commit",
            "baseline_commit",
            "old_blob_identifier",
            "blamed_historical_commit",
        ):
            object.__setattr__(self, name, _oid(getattr(self, name), name))
        if (
            type(self.deleted_preimage_line_number) is not int
            or self.deleted_preimage_line_number < 1
        ):
            raise ValueError("deleted_preimage_line_number must be a positive integer")
        object.__setattr__(
            self,
            "attribution_method",
            _enum(
                self.attribution_method,
                ScientificCandidateAttributionMethod,
                "attribution_method",
            ),
        )
        object.__setattr__(self, "metadata", _freeze(self.metadata))
        if self.attribution_identifier != self.calculate_identifier(**self._content()):
            raise ValueError(
                "attribution_identifier must derive from scientific content"
            )

    def _content(self) -> dict[str, object]:
        return {
            item.name: getattr(self, item.name)
            for item in fields(self)
            if item.name not in {"attribution_identifier", "metadata"}
        }

    @classmethod
    def calculate_identifier(cls, **content: object) -> str:
        content.pop("metadata", None)
        content.pop("attribution_identifier", None)
        return _canonical(content)

    def to_dict(self) -> dict[str, object]:
        return _dict(self)


@dataclass(frozen=True, slots=True)
class ScientificDefectInducingCandidateRecord:
    candidate_identifier: str
    blamed_historical_commit: str
    aggregation_level: ScientificCandidateAggregationLevel
    attribution_identifiers: tuple[str, ...]
    fixing_commits: tuple[str, ...]
    issue_identifiers: tuple[str, ...]
    target_evidence_identifiers: tuple[str, ...]
    policy_version: str
    policy_digest: str
    metadata: Mapping[str, object] = field(default_factory=lambda: _EMPTY)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "blamed_historical_commit",
            _oid(self.blamed_historical_commit, "blamed_historical_commit"),
        )
        object.__setattr__(
            self,
            "aggregation_level",
            _enum(
                self.aggregation_level,
                ScientificCandidateAggregationLevel,
                "aggregation_level",
            ),
        )
        for name in (
            "attribution_identifiers",
            "fixing_commits",
            "issue_identifiers",
            "target_evidence_identifiers",
        ):
            object.__setattr__(
                self, name, _ordered(getattr(self, name), name, required=True)
            )
        object.__setattr__(
            self, "policy_version", _text(self.policy_version, "policy_version")
        )
        object.__setattr__(
            self, "policy_digest", _digest(self.policy_digest, "policy_digest")
        )
        object.__setattr__(self, "metadata", _freeze(self.metadata))
        if self.candidate_identifier != self.calculate_identifier(**self._content()):
            raise ValueError("candidate_identifier must derive from scientific content")

    def _content(self) -> dict[str, object]:
        return {
            item.name: getattr(self, item.name)
            for item in fields(self)
            if item.name not in {"candidate_identifier", "metadata"}
        }

    @classmethod
    def calculate_identifier(cls, **content: object) -> str:
        content.pop("metadata", None)
        content.pop("candidate_identifier", None)
        return _canonical(content)

    def to_dict(self) -> dict[str, object]:
        return _dict(self)


@dataclass(frozen=True, slots=True)
class ScientificCandidateExclusionRecord:
    exclusion_identifier: str
    disposition: ScientificCandidateDisposition
    reason: ScientificCandidateExclusionReason
    fixing_commit: str
    baseline_commit: str
    issue_identifier: str
    target_evidence_identifier: str
    hunk_identifier: str
    old_path: str
    old_blob_identifier: str
    deleted_preimage_line_number: int
    policy_version: str
    policy_digest: str
    detail_code: str
    blamed_historical_commit: str | None = None
    metadata: Mapping[str, object] = field(default_factory=lambda: _EMPTY)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "disposition",
            _enum(self.disposition, ScientificCandidateDisposition, "disposition"),
        )
        if self.disposition is ScientificCandidateDisposition.ADMISSIBLE:
            raise ValueError("exclusion disposition cannot be admissible")
        object.__setattr__(
            self,
            "reason",
            _enum(self.reason, ScientificCandidateExclusionReason, "reason"),
        )
        for name in ("fixing_commit", "baseline_commit", "old_blob_identifier"):
            object.__setattr__(self, name, _oid(getattr(self, name), name))
        if self.blamed_historical_commit is not None:
            object.__setattr__(
                self,
                "blamed_historical_commit",
                _oid(self.blamed_historical_commit, "blamed_historical_commit"),
            )
        if (
            self.reason is ScientificCandidateExclusionReason.OUTSIDE_OBSERVATION_WINDOW
        ) != (self.blamed_historical_commit is not None):
            raise ValueError(
                "outside-window exclusions must bind the blamed historical commit"
            )
        for name in (
            "issue_identifier",
            "target_evidence_identifier",
            "hunk_identifier",
            "old_path",
            "policy_version",
            "detail_code",
        ):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        if (
            type(self.deleted_preimage_line_number) is not int
            or self.deleted_preimage_line_number < 1
        ):
            raise ValueError("deleted_preimage_line_number must be a positive integer")
        object.__setattr__(
            self, "policy_digest", _digest(self.policy_digest, "policy_digest")
        )
        object.__setattr__(self, "metadata", _freeze(self.metadata))
        if self.exclusion_identifier != self.calculate_identifier(**self._content()):
            raise ValueError("exclusion_identifier must derive from scientific content")

    def _content(self) -> dict[str, object]:
        return {
            item.name: getattr(self, item.name)
            for item in fields(self)
            if item.name not in {"exclusion_identifier", "metadata"}
        }

    @classmethod
    def calculate_identifier(cls, **content: object) -> str:
        content.pop("metadata", None)
        content.pop("exclusion_identifier", None)
        content.setdefault("blamed_historical_commit", None)
        return _canonical(content)

    def to_dict(self) -> dict[str, object]:
        return _dict(self)


@dataclass(frozen=True, slots=True)
class ScientificCandidateConstructionValidation:
    is_valid: bool
    specification_digest: str
    policy_digest: str
    attribution_count: int
    candidate_count: int
    exclusion_count: int
    error_codes: tuple[str, ...]
    warning_codes: tuple[str, ...]
    outside_observation_window_attribution_count: int = 0
    outside_observation_window_identity_digest: str | None = None
    metadata: Mapping[str, object] = field(default_factory=lambda: _EMPTY)

    def __post_init__(self) -> None:
        if type(self.is_valid) is not bool:
            raise TypeError("is_valid must be bool")
        for name in ("specification_digest", "policy_digest"):
            object.__setattr__(self, name, _digest(getattr(self, name), name))
        for name in ("attribution_count", "candidate_count", "exclusion_count"):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        if (
            type(self.outside_observation_window_attribution_count) is not int
            or self.outside_observation_window_attribution_count < 0
        ):
            raise ValueError(
                "outside_observation_window_attribution_count must be non-negative"
            )
        if self.outside_observation_window_attribution_count:
            if not isinstance(
                self.outside_observation_window_identity_digest, str
            ) or not _SHA256.fullmatch(self.outside_observation_window_identity_digest):
                raise ValueError(
                    "outside-window provenance must have an identity digest"
                )
        elif self.outside_observation_window_identity_digest is not None:
            raise ValueError("empty outside-window provenance must not have a digest")
        for name in ("error_codes", "warning_codes"):
            object.__setattr__(self, name, _ordered(getattr(self, name), name))
        if self.is_valid == bool(self.error_codes):
            raise ValueError("is_valid must agree with error_codes")
        object.__setattr__(self, "metadata", _freeze(self.metadata))

    def to_dict(self) -> dict[str, object]:
        return _dict(self)


@dataclass(frozen=True, slots=True)
class ScientificCandidateArtifactBinding:
    artifact: ScientificArtifactReference
    specification_digest: str
    policy_digest: str
    repository_snapshot_digest: str
    upstream_artifact_digests: Mapping[str, str]
    ordered_candidate_identifiers: tuple[str, ...]
    ordered_exclusion_identifiers: tuple[str, ...]
    binding_digest: str
    metadata: Mapping[str, object] = field(default_factory=lambda: _EMPTY)

    def __post_init__(self) -> None:
        if (
            not isinstance(self.artifact, ScientificArtifactReference)
            or self.artifact.artifact_role
            is not ScientificArtifactRole.DEFECT_INDUCING_CANDIDATE
        ):
            raise ValueError("artifact must have defect-inducing-candidate role")
        for name in (
            "specification_digest",
            "policy_digest",
            "repository_snapshot_digest",
        ):
            object.__setattr__(self, name, _digest(getattr(self, name), name))
        upstream = dict(self.upstream_artifact_digests)
        if tuple(upstream) != tuple(sorted(upstream)):
            raise ValueError(
                "upstream_artifact_digests must be deterministically ordered"
            )
        for name, digest in upstream.items():
            _text(name, "upstream artifact name")
            _digest(digest, "upstream artifact digest")
        object.__setattr__(
            self, "upstream_artifact_digests", MappingProxyType(upstream)
        )
        for name in ("ordered_candidate_identifiers", "ordered_exclusion_identifiers"):
            object.__setattr__(self, name, _ordered(getattr(self, name), name))
        object.__setattr__(self, "metadata", _freeze(self.metadata))
        if self.binding_digest != self.calculate_digest(**self._content()):
            raise ValueError("binding_digest must derive from scientific content")

    def _content(self) -> dict[str, object]:
        return {
            item.name: getattr(self, item.name)
            for item in fields(self)
            if item.name not in {"binding_digest", "metadata"}
        }

    @classmethod
    def calculate_digest(cls, **content: object) -> str:
        content.pop("metadata", None)
        content.pop("binding_digest", None)
        return _canonical(content)

    def to_dict(self) -> dict[str, object]:
        return _dict(self)


@dataclass(frozen=True, slots=True)
class ScientificCandidateConstructionResult:
    specification: ScientificCandidateConstructionSpecification
    policy: ScientificCandidateConstructionPolicy
    attributions: tuple[ScientificCandidateAttributionRecord, ...]
    candidates: tuple[ScientificDefectInducingCandidateRecord, ...]
    exclusions: tuple[ScientificCandidateExclusionRecord, ...]
    validation: ScientificCandidateConstructionValidation
    artifact_binding: ScientificCandidateArtifactBinding
    metadata: Mapping[str, object] = field(default_factory=lambda: _EMPTY)

    def __post_init__(self) -> None:
        if not isinstance(
            self.specification, ScientificCandidateConstructionSpecification
        ) or not isinstance(self.policy, ScientificCandidateConstructionPolicy):
            raise TypeError("specification and policy must use candidate contracts")
        groups = (
            ("attributions", ScientificCandidateAttributionRecord),
            ("candidates", ScientificDefectInducingCandidateRecord),
            ("exclusions", ScientificCandidateExclusionRecord),
        )
        normalized: dict[str, tuple[object, ...]] = {}
        for name, kind in groups:
            values = tuple(getattr(self, name))
            if any(not isinstance(item, kind) for item in values):
                raise TypeError(f"{name} contains an invalid contract")
            identity_name = {
                "attributions": "attribution_identifier",
                "candidates": "candidate_identifier",
                "exclusions": "exclusion_identifier",
            }[name]
            identities = tuple(getattr(item, identity_name) for item in values)
            if identities != tuple(sorted(set(identities))):
                raise ValueError(f"{name} must be unique and deterministically ordered")
            normalized[name] = values
            object.__setattr__(self, name, values)
        if (
            not isinstance(self.validation, ScientificCandidateConstructionValidation)
            or not self.validation.is_valid
        ):
            raise ValueError("validation must be a valid candidate validation")
        if not isinstance(self.artifact_binding, ScientificCandidateArtifactBinding):
            raise TypeError(
                "artifact_binding must be ScientificCandidateArtifactBinding"
            )
        if self.specification.policy_digest != self.policy.policy_digest:
            raise ValueError("specification and policy digests disagree")
        counts = (len(self.attributions), len(self.candidates), len(self.exclusions))
        if counts != (
            self.validation.attribution_count,
            self.validation.candidate_count,
            self.validation.exclusion_count,
        ):
            raise ValueError("validation counts disagree with result")
        if (
            tuple(item.candidate_identifier for item in self.candidates)
            != self.artifact_binding.ordered_candidate_identifiers
            or tuple(item.exclusion_identifier for item in self.exclusions)
            != self.artifact_binding.ordered_exclusion_identifiers
        ):
            raise ValueError("artifact binding identifiers disagree with result")
        object.__setattr__(self, "metadata", _freeze(self.metadata))

    def to_dict(self) -> dict[str, object]:
        return _dict(self)
