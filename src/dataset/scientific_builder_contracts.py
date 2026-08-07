"""Immutable contracts for project-independent scientific dataset construction."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum, StrEnum
from numbers import Integral, Real
from pathlib import PurePosixPath
from types import MappingProxyType
from typing import Any

from dataset.scientific_dataset_contract import (
    ScientificFeatureDisposition,
    ScientificFeatureModality,
    ScientificFeatureProvenance,
    ScientificFeatureTemporalScope,
    ScientificTargetContract,
)

__all__ = [
    "ScientificBuilderStage",
    "ScientificArtifactRole",
    "ScientificArtifactReference",
    "ScientificRepositorySnapshot",
    "ScientificTargetEvidenceRecord",
    "ScientificTargetAssignment",
    "ScientificFeatureValueRecord",
    "ScientificFeatureInventory",
    "ScientificDatasetAssemblyInput",
    "ScientificDatasetBuildManifest",
    "ScientificDatasetBuildValidation",
    "ScientificDatasetBuildResult",
]


class ScientificBuilderStage(StrEnum):
    REPOSITORY_ACQUISITION = "repository-acquisition"
    RAW_ARTIFACT_EXTRACTION = "raw-artifact-extraction"
    TARGET_EVIDENCE_CONSTRUCTION = "target-evidence-construction"
    CANDIDATE_CONSTRUCTION = "candidate-construction"
    TARGET_ASSIGNMENT = "target-assignment"
    FEATURE_CONSTRUCTION = "feature-construction"
    FEATURE_PROVENANCE_AUDIT = "feature-provenance-audit"
    LEAKAGE_VALIDATION = "leakage-validation"
    DATASET_ASSEMBLY = "dataset-assembly"
    MANIFEST_GENERATION = "manifest-generation"
    VALIDATION_REPORTING = "validation-reporting"


class ScientificArtifactRole(StrEnum):
    REPOSITORY_SNAPSHOT = "repository-snapshot"
    COMMIT_ARTIFACT = "commit-artifact"
    DIFF_ARTIFACT = "diff-artifact"
    FILE_ARTIFACT = "file-artifact"
    ISSUE_ARTIFACT = "issue-artifact"
    TARGET_EVIDENCE = "target-evidence"
    DEFECT_INDUCING_CANDIDATE = "defect-inducing-candidate"
    TARGET_ASSIGNMENT = "target-assignment"
    CODE_FEATURE = "code-feature"
    PROCESS_FEATURE = "process-feature"
    TEXT_FEATURE = "text-feature"
    FEATURE_PROVENANCE = "feature-provenance"
    LEAKAGE_AUDIT = "leakage-audit"
    DATASET = "dataset"
    MANIFEST = "manifest"
    VALIDATION_REPORT = "validation-report"


_EMPTY: Mapping[str, object] = MappingProxyType({})
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_GIT_OBJECT_ID = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
_BANNED_RUNTIME_KEYS = {
    "clone_date",
    "created_at",
    "environment",
    "execution_timestamp",
    "hostname",
    "local_clone_path",
    "local_path",
    "machine_identifier",
    "machine_name",
    "runtime_duration",
    "runtime_timestamp",
    "username",
}
_BANNED_FEATURE_KEYS = {
    "bug_confidence",
    "contains_bug_keyword",
    "contains_fix_keyword",
    "future_bug_count",
    "future_fix_count",
    "has_bug_keyword",
    "issue_link",
    "issue_linking",
    "label",
    "label_confidence",
    "msg_has_bug_kw",
    "post_release_defect_count",
    "prediction",
    "target",
    "target_probability",
}


def _normalized_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def _name(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


def _sha256(value: object, field_name: str) -> str:
    text = _name(value, field_name)
    if not _SHA256.fullmatch(text):
        raise ValueError(f"{field_name} must be a lowercase SHA-256 digest")
    return text


def _count(value: object, field_name: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer")
    return value


def _freeze(value: object, *, path: str = "metadata") -> object:
    if isinstance(value, Mapping):
        frozen: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(f"{path} keys must be strings")
            normalized = _normalized_key(key)
            if normalized in _BANNED_RUNTIME_KEYS:
                raise ValueError(
                    f"{path} must not contain runtime identity field {key!r}"
                )
            frozen[key] = _freeze(item, path=f"{path}.{key}")
        return MappingProxyType(frozen)
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item, path=path) for item in value)
    if value is None or isinstance(value, (str, bool, int)):
        if isinstance(value, str) and value.startswith("/"):
            raise ValueError(f"{path} must not contain local absolute paths")
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{path} must contain finite values")
        return value
    raise TypeError(f"{path} must contain deterministic JSON-compatible values")


def _metadata(value: object, *, banned: set[str] | None = None) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TypeError("metadata must be a mapping")
    if banned:
        for key in _walk_keys(value):
            if _normalized_key(key) in banned:
                raise ValueError(f"metadata must not contain {key!r}")
    return _freeze(value)  # type: ignore[return-value]


def _walk_keys(value: object):
    if isinstance(value, Mapping):
        for key, item in value.items():
            if isinstance(key, str):
                yield key
            yield from _walk_keys(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _walk_keys(item)


def _thaw(value: object) -> object:
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    if isinstance(value, Enum):
        return value.value
    return value


def _to_dict(instance: object) -> dict[str, object]:
    return {
        name: _thaw(getattr(instance, name))
        for name in instance.__dataclass_fields__  # type: ignore[attr-defined]
    }


def _canonical_digest(content: Mapping[str, object]) -> str:
    payload = json.dumps(
        content,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def _enum(value: object, enum_type: type[Enum], field_name: str) -> Any:
    try:
        return enum_type(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"invalid {field_name}: {value!r}") from error


def _unique_names(
    values: Sequence[object], field_name: str, *, non_empty: bool = False
) -> tuple[str, ...]:
    result = tuple(_name(value, field_name) for value in values)
    if non_empty and not result:
        raise ValueError(f"{field_name} must not be empty")
    if len(result) != len(set(result)):
        raise ValueError(f"{field_name} must contain unique values")
    return result


@dataclass(frozen=True, slots=True)
class ScientificArtifactReference:
    artifact_name: str
    artifact_role: ScientificArtifactRole
    repository_relative_path: str
    content_digest: str
    schema_version: str
    record_count: int
    metadata: Mapping[str, object] = field(default_factory=lambda: _EMPTY)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "artifact_name", _name(self.artifact_name, "artifact_name")
        )
        object.__setattr__(
            self,
            "artifact_role",
            _enum(self.artifact_role, ScientificArtifactRole, "artifact_role"),
        )
        path = _name(self.repository_relative_path, "repository_relative_path")
        pure = PurePosixPath(path)
        if (
            pure.is_absolute()
            or "\\" in path
            or ".." in pure.parts
            or str(pure) != path
            or path in {".", ""}
        ):
            raise ValueError(
                "repository_relative_path must be relative and normalized "
                "without traversal"
            )
        object.__setattr__(
            self, "content_digest", _sha256(self.content_digest, "content_digest")
        )
        object.__setattr__(
            self, "schema_version", _name(self.schema_version, "schema_version")
        )
        object.__setattr__(
            self, "record_count", _count(self.record_count, "record_count")
        )
        object.__setattr__(self, "metadata", _metadata(self.metadata))

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class ScientificRepositorySnapshot:
    repository_name: str
    repository_url: str
    repository_revision: str
    default_branch: str
    acquisition_policy_version: str
    snapshot_digest: str
    metadata: Mapping[str, object] = field(default_factory=lambda: _EMPTY)

    def __post_init__(self) -> None:
        for name in (
            "repository_name",
            "repository_url",
            "repository_revision",
            "default_branch",
            "acquisition_policy_version",
        ):
            object.__setattr__(self, name, _name(getattr(self, name), name))
        if not _GIT_OBJECT_ID.fullmatch(self.repository_revision):
            raise ValueError(
                "repository_revision must be a complete lowercase 40- or "
                "64-character Git object identifier"
            )
        object.__setattr__(
            self, "snapshot_digest", _sha256(self.snapshot_digest, "snapshot_digest")
        )
        object.__setattr__(self, "metadata", _metadata(self.metadata))

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class ScientificTargetEvidenceRecord:
    observation_identifier: str
    evidence_identifier: str
    evidence_type: str
    source_artifact: ScientificArtifactReference
    evidence_timestamp: str
    evidence_summary: str
    supports_positive_label: bool
    confidence_category: str
    metadata: Mapping[str, object] = field(default_factory=lambda: _EMPTY)

    def __post_init__(self) -> None:
        for name in (
            "observation_identifier",
            "evidence_identifier",
            "evidence_type",
            "evidence_summary",
            "confidence_category",
        ):
            object.__setattr__(self, name, _name(getattr(self, name), name))
        if not isinstance(self.source_artifact, ScientificArtifactReference):
            raise TypeError("source_artifact must be ScientificArtifactReference")
        admissible_roles = {
            ScientificArtifactRole.COMMIT_ARTIFACT,
            ScientificArtifactRole.DIFF_ARTIFACT,
            ScientificArtifactRole.FILE_ARTIFACT,
            ScientificArtifactRole.ISSUE_ARTIFACT,
            ScientificArtifactRole.TARGET_EVIDENCE,
        }
        if self.source_artifact.artifact_role not in admissible_roles:
            raise ValueError(
                "source_artifact role is not admissible target-evidence provenance"
            )
        if type(self.supports_positive_label) is not bool:
            raise TypeError("supports_positive_label must be bool")
        try:
            parsed = datetime.fromisoformat(
                _name(self.evidence_timestamp, "evidence_timestamp").replace(
                    "Z", "+00:00"
                )
            )
        except ValueError as error:
            raise ValueError(
                "evidence_timestamp must be an ISO-8601 timestamp"
            ) from error
        if parsed.tzinfo is None:
            raise ValueError("evidence_timestamp must include an explicit timezone")
        normalized = parsed.astimezone(UTC).isoformat().replace("+00:00", "Z")
        object.__setattr__(self, "evidence_timestamp", normalized)
        object.__setattr__(
            self,
            "metadata",
            _metadata(
                self.metadata,
                banned={
                    "feature_enabled",
                    "feature_enable",
                    "enabled_as_feature",
                    "use_as_feature",
                },
            ),
        )

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class ScientificTargetAssignment:
    observation_identifier: str
    target_field: str
    target_label: str | int
    assignment_policy_version: str
    evidence_identifiers: tuple[str, ...]
    assignment_rationale: str
    metadata: Mapping[str, object] = field(default_factory=lambda: _EMPTY)

    def __post_init__(self) -> None:
        for name in (
            "observation_identifier",
            "target_field",
            "assignment_policy_version",
            "assignment_rationale",
        ):
            object.__setattr__(self, name, _name(getattr(self, name), name))
        if not (
            (type(self.target_label) is int)
            or (isinstance(self.target_label, str) and self.target_label.strip())
        ):
            raise TypeError(
                "target_label must be a non-empty string or integer excluding bool"
            )
        evidence = _unique_names(self.evidence_identifiers, "evidence_identifiers")
        object.__setattr__(self, "evidence_identifiers", evidence)
        object.__setattr__(
            self, "metadata", _metadata(self.metadata, banned=_BANNED_FEATURE_KEYS)
        )

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class ScientificFeatureValueRecord:
    observation_identifier: str
    feature_name: str
    modality: ScientificFeatureModality
    value: float | int
    provenance_digest: str
    temporal_scope: ScientificFeatureTemporalScope
    metadata: Mapping[str, object] = field(default_factory=lambda: _EMPTY)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "observation_identifier",
            _name(self.observation_identifier, "observation_identifier"),
        )
        object.__setattr__(
            self, "feature_name", _name(self.feature_name, "feature_name")
        )
        object.__setattr__(
            self,
            "modality",
            _enum(self.modality, ScientificFeatureModality, "modality"),
        )
        if isinstance(self.value, bool):
            raise ValueError("value must be a finite numeric scalar excluding bool")
        if isinstance(self.value, Integral):
            normalized_value: int | float = int(self.value)
        elif isinstance(self.value, Real):
            normalized_value = float(self.value)
            if not math.isfinite(normalized_value):
                raise ValueError("value must be a finite numeric scalar excluding bool")
        else:
            raise ValueError("value must be a finite numeric scalar excluding bool")
        object.__setattr__(self, "value", normalized_value)
        object.__setattr__(
            self,
            "provenance_digest",
            _sha256(self.provenance_digest, "provenance_digest"),
        )
        object.__setattr__(
            self,
            "temporal_scope",
            _enum(
                self.temporal_scope, ScientificFeatureTemporalScope, "temporal_scope"
            ),
        )
        object.__setattr__(
            self, "metadata", _metadata(self.metadata, banned=_BANNED_FEATURE_KEYS)
        )

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class ScientificFeatureInventory:
    specification_digest: str
    feature_provenance: tuple[ScientificFeatureProvenance, ...]
    complete_scenario_feature_names: tuple[str, ...]
    leakage_controlled_feature_names: tuple[str, ...]
    prohibited_feature_names: tuple[str, ...]
    review_required_feature_names: tuple[str, ...]
    inventory_digest: str
    metadata: Mapping[str, object] = field(default_factory=lambda: _EMPTY)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "specification_digest",
            _sha256(self.specification_digest, "specification_digest"),
        )
        provenance = tuple(self.feature_provenance)
        if any(
            not isinstance(item, ScientificFeatureProvenance) for item in provenance
        ):
            raise TypeError(
                "feature_provenance must contain ScientificFeatureProvenance"
            )
        names = tuple(item.feature_name for item in provenance)
        if len(names) != len(set(names)):
            raise ValueError("feature_provenance names must be unique")
        categories = {}
        for field_name in (
            "complete_scenario_feature_names",
            "leakage_controlled_feature_names",
            "prohibited_feature_names",
            "review_required_feature_names",
        ):
            supplied = tuple(getattr(self, field_name))
            ordered = tuple(sorted(_unique_names(supplied, field_name)))
            if supplied != ordered:
                raise ValueError(f"{field_name} must be deterministically ordered")
            if not set(ordered).issubset(names):
                raise ValueError(f"{field_name} contains an unknown feature")
            categories[field_name] = ordered
            object.__setattr__(self, field_name, ordered)
        complete = set(categories["complete_scenario_feature_names"])
        controlled = set(categories["leakage_controlled_feature_names"])
        prohibited = set(categories["prohibited_feature_names"])
        review = set(categories["review_required_feature_names"])
        if not controlled.issubset(complete):
            raise ValueError(
                "leakage-controlled features must be a subset of complete features"
            )
        if controlled & review:
            raise ValueError("review-required features cannot be leakage-controlled")
        by_name = {item.feature_name: item for item in provenance}
        for name, feature in by_name.items():
            if (name in complete) != feature.allowed_in_complete_scenario or (
                name in controlled
            ) != feature.allowed_in_leakage_controlled_scenario:
                raise ValueError(
                    "scenario categories must match feature provenance flags"
                )
            if (name in prohibited) != (
                feature.disposition is ScientificFeatureDisposition.PROHIBITED
            ):
                raise ValueError("prohibited category must match feature disposition")
            if (name in review) != (
                feature.disposition is ScientificFeatureDisposition.REVIEW_REQUIRED
            ):
                raise ValueError(
                    "review-required category must match feature disposition"
                )
        object.__setattr__(self, "feature_provenance", provenance)
        object.__setattr__(self, "metadata", _metadata(self.metadata))
        expected = _canonical_digest(self._scientific_content())
        if self.inventory_digest != expected:
            raise ValueError(
                "inventory_digest must derive from canonical scientific content"
            )

    def _scientific_content(self) -> dict[str, object]:
        return {
            "specification_digest": self.specification_digest,
            "feature_provenance": [item.to_dict() for item in self.feature_provenance],
            "complete_scenario_feature_names": list(
                self.complete_scenario_feature_names
            ),
            "leakage_controlled_feature_names": list(
                self.leakage_controlled_feature_names
            ),
            "prohibited_feature_names": list(self.prohibited_feature_names),
            "review_required_feature_names": list(self.review_required_feature_names),
        }

    @classmethod
    def calculate_digest(
        cls,
        *,
        specification_digest: str,
        feature_provenance: Sequence[ScientificFeatureProvenance],
        complete_scenario_feature_names: Sequence[str],
        leakage_controlled_feature_names: Sequence[str],
        prohibited_feature_names: Sequence[str],
        review_required_feature_names: Sequence[str],
        metadata: Mapping[str, object] = _EMPTY,
    ) -> str:
        return _canonical_digest(
            {
                "specification_digest": specification_digest,
                "feature_provenance": [item.to_dict() for item in feature_provenance],
                "complete_scenario_feature_names": list(
                    complete_scenario_feature_names
                ),
                "leakage_controlled_feature_names": list(
                    leakage_controlled_feature_names
                ),
                "prohibited_feature_names": list(prohibited_feature_names),
                "review_required_feature_names": list(review_required_feature_names),
            }
        )

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class ScientificDatasetAssemblyInput:
    repository_snapshot: ScientificRepositorySnapshot
    source_artifacts: tuple[ScientificArtifactReference, ...]
    observation_identifiers: tuple[str, ...]
    observation_timestamps: Mapping[str, str]
    target_contract: ScientificTargetContract
    target_assignments: tuple[ScientificTargetAssignment, ...]
    feature_inventory: ScientificFeatureInventory
    feature_values: tuple[ScientificFeatureValueRecord, ...]
    scientific_dataset_specification_digest: str
    metadata: Mapping[str, object] = field(default_factory=lambda: _EMPTY)

    def __post_init__(self) -> None:
        if not isinstance(
            self.repository_snapshot, ScientificRepositorySnapshot
        ) or not isinstance(self.feature_inventory, ScientificFeatureInventory):
            raise TypeError(
                "repository_snapshot and feature_inventory must use "
                "scientific contracts"
            )
        if not isinstance(self.target_contract, ScientificTargetContract):
            raise TypeError("target_contract must be ScientificTargetContract")
        artifacts = tuple(self.source_artifacts)
        if any(not isinstance(item, ScientificArtifactReference) for item in artifacts):
            raise TypeError("source_artifacts must contain artifact references")
        target_evidence_artifacts = tuple(
            item
            for item in artifacts
            if item.artifact_role is ScientificArtifactRole.TARGET_EVIDENCE
        )
        candidate_artifacts = tuple(
            item
            for item in artifacts
            if item.artifact_role is ScientificArtifactRole.DEFECT_INDUCING_CANDIDATE
        )
        observations = _unique_names(
            self.observation_identifiers, "observation_identifiers", non_empty=True
        )
        timestamps = dict(self.observation_timestamps)
        if set(timestamps) != set(observations) or any(
            not isinstance(value, str) or not value.strip()
            for value in timestamps.values()
        ):
            raise ValueError(
                "timestamps must exist for every and only known observation"
            )
        assignments = tuple(self.target_assignments)
        assignment_ids = [
            item.observation_identifier
            for item in assignments
            if isinstance(item, ScientificTargetAssignment)
        ]
        if (
            len(assignment_ids) != len(assignments)
            or set(assignment_ids) != set(observations)
            or len(assignment_ids) != len(set(assignment_ids))
        ):
            raise ValueError(
                "one target assignment must exist for every and only known observation"
            )
        for assignment in assignments:
            if assignment.target_field != self.target_contract.field_name:
                raise ValueError("target assignment field must match target contract")
            if assignment.target_label not in {
                self.target_contract.negative_label,
                self.target_contract.positive_label,
            }:
                raise ValueError("target assignment label is outside target contract")
            if (
                assignment.target_label == self.target_contract.positive_label
                and not assignment.evidence_identifiers
            ):
                raise ValueError(
                    "positive target assignment requires evidence identifiers"
                )
        values = tuple(self.feature_values)
        if any(not isinstance(item, ScientificFeatureValueRecord) for item in values):
            raise TypeError("feature_values must contain scientific feature values")
        known_features = set(self.feature_inventory.complete_scenario_feature_names)
        prohibited = set(self.feature_inventory.prohibited_feature_names)
        pairs: set[tuple[str, str]] = set()
        by_name = {
            item.feature_name: item
            for item in self.feature_inventory.feature_provenance
        }
        target_evidence_digests = {
            item.content_digest for item in target_evidence_artifacts
        }
        candidate_digests = {item.content_digest for item in candidate_artifacts}
        target_evidence_sources = {
            identity
            for item in target_evidence_artifacts
            for identity in (item.artifact_name, item.repository_relative_path)
        }
        candidate_sources = {
            identity
            for item in candidate_artifacts
            for identity in (item.artifact_name, item.repository_relative_path)
        }
        for provenance in self.feature_inventory.feature_provenance:
            if (
                provenance.source_artifact
                in target_evidence_sources | candidate_sources
            ):
                raise ValueError(
                    "target-evidence and candidate artifacts cannot be feature "
                    "provenance sources"
                )
        for value in values:
            if value.observation_identifier not in observations:
                raise ValueError("orphan feature value")
            if (
                value.feature_name not in known_features
                or value.feature_name in prohibited
            ):
                raise ValueError(
                    "feature value uses unknown, ineligible, or prohibited feature"
                )
            if value.feature_name in {"target", "timestamp"}:
                raise ValueError("target or timestamp cannot be reused as a feature")
            if value.provenance_digest in target_evidence_digests | candidate_digests:
                raise ValueError(
                    "target-evidence or candidate artifact digest cannot back a "
                    "feature value"
                )
            provenance = by_name[value.feature_name]
            if (
                value.modality is not provenance.modality
                or value.temporal_scope is not provenance.temporal_scope
            ):
                raise ValueError("feature value does not match registered provenance")
            pair = (value.observation_identifier, value.feature_name)
            if pair in pairs:
                raise ValueError("duplicate observation-feature pair")
            pairs.add(pair)
        object.__setattr__(self, "source_artifacts", artifacts)
        object.__setattr__(self, "observation_identifiers", observations)
        object.__setattr__(
            self,
            "observation_timestamps",
            _freeze(timestamps, path="observation_timestamps"),
        )
        object.__setattr__(self, "target_assignments", assignments)
        object.__setattr__(self, "feature_values", values)
        object.__setattr__(
            self,
            "scientific_dataset_specification_digest",
            _sha256(
                self.scientific_dataset_specification_digest,
                "scientific_dataset_specification_digest",
            ),
        )
        if (
            self.scientific_dataset_specification_digest
            != self.feature_inventory.specification_digest
        ):
            raise ValueError("specification digest must agree with feature inventory")
        object.__setattr__(self, "metadata", _metadata(self.metadata))

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


_APPROVED_STAGES = tuple(ScientificBuilderStage)


@dataclass(frozen=True, slots=True)
class ScientificDatasetBuildManifest:
    build_schema_version: str
    dataset_name: str
    dataset_version: str
    repository_snapshot_digest: str
    scientific_dataset_specification_digest: str
    feature_inventory_digest: str
    source_artifact_digests: Mapping[str, str]
    stage_sequence: tuple[ScientificBuilderStage, ...]
    observation_count: int
    feature_count: int
    target_positive_count: int
    target_negative_count: int
    output_artifacts: tuple[ScientificArtifactReference, ...]
    scientific_digest: str
    metadata: Mapping[str, object] = field(default_factory=lambda: _EMPTY)

    def __post_init__(self) -> None:
        for name in ("build_schema_version", "dataset_name", "dataset_version"):
            object.__setattr__(self, name, _name(getattr(self, name), name))
        for name in (
            "repository_snapshot_digest",
            "scientific_dataset_specification_digest",
            "feature_inventory_digest",
        ):
            object.__setattr__(self, name, _sha256(getattr(self, name), name))
        digests = dict(self.source_artifact_digests)
        if len(digests) != len(set(digests)):
            raise ValueError("source artifact names must be unique")
        for name, digest in digests.items():
            _name(name, "source artifact name")
            _sha256(digest, "source artifact digest")
        stages = tuple(
            _enum(item, ScientificBuilderStage, "stage_sequence")
            for item in self.stage_sequence
        )
        if stages != _APPROVED_STAGES:
            raise ValueError("stage_sequence must exactly match the approved pipeline")
        for name in (
            "observation_count",
            "feature_count",
            "target_positive_count",
            "target_negative_count",
        ):
            object.__setattr__(self, name, _count(getattr(self, name), name))
        if (
            self.target_positive_count + self.target_negative_count
            != self.observation_count
        ):
            raise ValueError(
                "positive and negative counts must equal observation count"
            )
        outputs = tuple(self.output_artifacts)
        output_names = [
            item.artifact_name
            for item in outputs
            if isinstance(item, ScientificArtifactReference)
        ]
        if len(output_names) != len(outputs) or len(output_names) != len(
            set(output_names)
        ):
            raise ValueError("output artifact names must be unique")
        object.__setattr__(
            self,
            "source_artifact_digests",
            _freeze(digests, path="source_artifact_digests"),
        )
        object.__setattr__(self, "stage_sequence", stages)
        object.__setattr__(self, "output_artifacts", outputs)
        object.__setattr__(self, "metadata", _metadata(self.metadata))
        if self.scientific_digest != _canonical_digest(self._scientific_content()):
            raise ValueError(
                "scientific_digest must derive from canonical scientific content"
            )

    def _scientific_content(self) -> dict[str, object]:
        content = _to_dict(self)
        content.pop("scientific_digest")
        return content

    @classmethod
    def calculate_digest(cls, **values: object) -> str:
        content = dict(values)
        content.pop("scientific_digest", None)
        return _canonical_digest(_thaw(content))  # type: ignore[arg-type]

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class ScientificDatasetBuildValidation:
    is_valid: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    checked_observation_count: int
    checked_feature_count: int
    checked_feature_value_count: int
    checked_target_assignment_count: int
    specification_digest: str
    feature_inventory_digest: str
    metadata: Mapping[str, object] = field(default_factory=lambda: _EMPTY)

    def __post_init__(self) -> None:
        errors = tuple(sorted(_unique_names(self.errors, "errors")))
        warnings = tuple(sorted(_unique_names(self.warnings, "warnings")))
        if self.is_valid != (not errors):
            raise ValueError("is_valid must be true exactly when errors is empty")
        if type(self.is_valid) is not bool:
            raise TypeError("is_valid must be bool")
        object.__setattr__(self, "errors", errors)
        object.__setattr__(self, "warnings", warnings)
        for name in (
            "checked_observation_count",
            "checked_feature_count",
            "checked_feature_value_count",
            "checked_target_assignment_count",
        ):
            object.__setattr__(self, name, _count(getattr(self, name), name))
        object.__setattr__(
            self,
            "specification_digest",
            _sha256(self.specification_digest, "specification_digest"),
        )
        object.__setattr__(
            self,
            "feature_inventory_digest",
            _sha256(self.feature_inventory_digest, "feature_inventory_digest"),
        )
        object.__setattr__(self, "metadata", _metadata(self.metadata))

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class ScientificDatasetBuildResult:
    manifest: ScientificDatasetBuildManifest
    validation: ScientificDatasetBuildValidation
    assembled_observation_count: int
    assembled_feature_count: int
    source_artifacts: tuple[ScientificArtifactReference, ...]
    output_artifacts: tuple[ScientificArtifactReference, ...]
    metadata: Mapping[str, object] = field(default_factory=lambda: _EMPTY)

    def __post_init__(self) -> None:
        if not isinstance(
            self.manifest, ScientificDatasetBuildManifest
        ) or not isinstance(self.validation, ScientificDatasetBuildValidation):
            raise TypeError("manifest and validation must use scientific contracts")
        if not self.validation.is_valid:
            raise ValueError("validation must be valid")
        for name in ("assembled_observation_count", "assembled_feature_count"):
            object.__setattr__(self, name, _count(getattr(self, name), name))
        if (
            self.assembled_observation_count != self.manifest.observation_count
            or self.assembled_feature_count != self.manifest.feature_count
        ):
            raise ValueError("assembled counts must agree with manifest")
        sources = tuple(self.source_artifacts)
        outputs = tuple(self.output_artifacts)
        if {item.artifact_name: item.content_digest for item in sources} != dict(
            self.manifest.source_artifact_digests
        ):
            raise ValueError("source artifacts must agree with manifest")
        if outputs != self.manifest.output_artifacts:
            raise ValueError("output artifacts must agree with manifest")
        object.__setattr__(self, "source_artifacts", sources)
        object.__setattr__(self, "output_artifacts", outputs)
        object.__setattr__(self, "metadata", _metadata(self.metadata))

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)
