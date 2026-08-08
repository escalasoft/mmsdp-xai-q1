"""Deterministic assembly of the canonical Qt commit-level scientific dataset."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, fields, is_dataclass
from datetime import datetime
from enum import Enum
from types import MappingProxyType

from dataset.scientific_builder_contracts import (
    ScientificArtifactReference,
    ScientificArtifactRole,
    ScientificTargetAssignment,
)
from dataset.scientific_target_assignment_contracts import (
    ScientificTargetAssignmentResult,
)
from extraction.qt_commit_extraction import QtCommitExtractionResult
from feature_engineering.qt_feature_construction import (
    QT_CODE_FEATURE_NAMES,
    QtMultimodalFeatureConstructionResult,
)

__all__ = [
    "QtDatasetAssemblyError",
    "QtDatasetAssemblyPolicy",
    "QtDatasetAssemblySpecification",
    "QtDatasetObservation",
    "QtDatasetAssemblyValidation",
    "QtMultimodalDatasetAssemblyResult",
    "build_qt_dataset_assembly_specification",
    "assemble_qt_multimodal_dataset",
]


_EMPTY: Mapping[str, object] = MappingProxyType({})
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_OBJECT_ID = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
_PROCESS_NAMES = ("is_merge_commit", "parent_count")
_TEXT_NAMES = ("raw_commit_message",)
_FORBIDDEN_PREDICTOR_KEYS = frozenset(
    {
        "bug_confidence",
        "candidate_identifier",
        "candidate_identifiers",
        "defect_inducing_candidate",
        "future_defect_count",
        "future_information",
        "has_bug_keyword",
        "has_fix_keyword",
        "issue_content",
        "issue_identifier",
        "issue_identifiers",
        "label",
        "target",
        "target_assignment",
        "target_evidence",
        "target_label",
    }
)
_BANNED_METADATA_KEYS = frozenset(
    {
        "created_at",
        "duration",
        "hostname",
        "local_path",
        "memory_address",
        "random_uuid",
        "runtime_timestamp",
        "username",
    }
)


class QtDatasetAssemblyError(RuntimeError):
    """A deterministic scientific inconsistency at the Qt dataset join boundary."""


def _key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


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


def _digest(value: object) -> str:
    payload = json.dumps(
        _thaw(value),
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _require_digest(value: object, name: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")
    return value


def _require_text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _freeze_metadata(value: Mapping[str, object]) -> Mapping[str, object]:
    result: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise TypeError("metadata keys must be strings")
        if _key(key) in _BANNED_METADATA_KEYS:
            raise ValueError(f"metadata must not contain runtime field {key!r}")
        if isinstance(item, Mapping):
            result[key] = _freeze_metadata(item)
        elif isinstance(item, (list, tuple)):
            result[key] = tuple(
                _freeze_metadata(entry) if isinstance(entry, Mapping) else entry
                for entry in item
            )
        elif item is None or type(item) in {str, bool, int, float}:
            if isinstance(item, str) and item.startswith("/"):
                raise ValueError("metadata must not contain absolute local paths")
            result[key] = item
        else:
            raise TypeError("metadata must contain deterministic JSON values")
    return MappingProxyType(result)


def _ordered_artifact_digests(
    artifacts: Sequence[ScientificArtifactReference],
) -> Mapping[str, str]:
    pairs = sorted(
        (item.artifact_role.value, item.content_digest) for item in artifacts
    )
    if len(pairs) != len({role for role, _ in pairs}):
        raise ValueError("modality artifact roles must be unique")
    return MappingProxyType(dict(pairs))


@dataclass(frozen=True, slots=True)
class QtDatasetAssemblyPolicy:
    policy_version: str = "qt-multimodal-dataset-assembly-policy-1.0.0"
    unit_of_analysis: str = "commit"
    join_key: str = "immutable-complete-git-object-identifier"
    join_cardinality: str = "one-to-one-exact-eligible-universe"
    ordering_policy: str = "commit-object-identifier-ascending"
    predictor_modalities: tuple[str, ...] = ("code", "process", "text")
    target_source: str = "frozen-target-assignment-artifact-only"
    policy_digest: str = ""

    def __post_init__(self) -> None:
        actual = self.to_dict()
        actual.pop("policy_digest")
        if actual != self.scientific_values():
            raise ValueError("assembly policy does not match the frozen Qt policy")
        expected = self.calculate_digest()
        if self.policy_digest != expected:
            raise ValueError("policy_digest must derive from frozen scientific policy")

    @classmethod
    def create(cls) -> QtDatasetAssemblyPolicy:
        return cls(policy_digest=cls.calculate_digest())

    @staticmethod
    def scientific_values() -> dict[str, object]:
        return {
            "policy_version": "qt-multimodal-dataset-assembly-policy-1.0.0",
            "unit_of_analysis": "commit",
            "join_key": "immutable-complete-git-object-identifier",
            "join_cardinality": "one-to-one-exact-eligible-universe",
            "ordering_policy": "commit-object-identifier-ascending",
            "predictor_modalities": ["code", "process", "text"],
            "target_source": "frozen-target-assignment-artifact-only",
        }

    @classmethod
    def calculate_digest(cls) -> str:
        return _digest(cls.scientific_values())

    def to_dict(self) -> dict[str, object]:
        return _thaw(self)  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class QtDatasetAssemblySpecification:
    schema_version: str
    specification_version: str
    repository_revision: str
    repository_snapshot_digest: str
    commit_artifact_digest: str
    multimodal_construction_identity_digest: str
    modality_artifact_digests: Mapping[str, str]
    feature_inventory_digest: str
    target_assignment_artifact_digest: str
    target_assignment_binding_digest: str
    target_assignment_specification_digest: str
    target_assignment_policy_digest: str
    assembly_policy_digest: str
    specification_digest: str

    def __post_init__(self) -> None:
        _require_text(self.schema_version, "schema_version")
        _require_text(self.specification_version, "specification_version")
        if not _OBJECT_ID.fullmatch(self.repository_revision):
            raise ValueError("repository_revision must be a complete Git identifier")
        for name in (
            "repository_snapshot_digest",
            "commit_artifact_digest",
            "multimodal_construction_identity_digest",
            "feature_inventory_digest",
            "target_assignment_artifact_digest",
            "target_assignment_binding_digest",
            "target_assignment_specification_digest",
            "target_assignment_policy_digest",
            "assembly_policy_digest",
        ):
            _require_digest(getattr(self, name), name)
        modality = dict(self.modality_artifact_digests)
        if tuple(modality) != ("code-feature", "process-feature", "text-feature"):
            raise ValueError("modality artifacts must use canonical modality roles")
        for role, digest in modality.items():
            _require_text(role, "modality artifact role")
            _require_digest(digest, f"{role} digest")
        object.__setattr__(
            self, "modality_artifact_digests", MappingProxyType(modality)
        )
        if self.specification_digest != self.calculate_digest(**self._content()):
            raise ValueError("specification_digest must identify scientific content")

    def _content(self) -> dict[str, object]:
        return {
            item.name: getattr(self, item.name)
            for item in fields(self)
            if item.name != "specification_digest"
        }

    @classmethod
    def calculate_digest(cls, **content: object) -> str:
        content.pop("specification_digest", None)
        return _digest(content)

    def to_dict(self) -> dict[str, object]:
        return _thaw(self)  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class QtDatasetObservation:
    commit_identifier: str
    committed_at: str
    code_features: Mapping[str, int]
    process_features: Mapping[str, int]
    text_features: Mapping[str, str]
    target: int
    source_multimodal_record_digest: str
    source_target_assignment_artifact_digest: str
    observation_digest: str

    def __post_init__(self) -> None:
        if not _OBJECT_ID.fullmatch(self.commit_identifier):
            raise ValueError("commit_identifier must be a complete Git identifier")
        if not isinstance(self.committed_at, str):
            raise TypeError("committed_at must be a string")
        try:
            timestamp = datetime.fromisoformat(self.committed_at)
        except ValueError as error:
            raise ValueError("committed_at must be an ISO-8601 timestamp") from error
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError("committed_at must include a UTC offset")
        code = dict(self.code_features)
        process = dict(self.process_features)
        text = dict(self.text_features)
        if tuple(code) != QT_CODE_FEATURE_NAMES:
            raise ValueError("CODE must contain exactly the frozen 13 features")
        if tuple(process) != _PROCESS_NAMES:
            raise ValueError("PROCESS must contain exactly the two approved features")
        if tuple(text) != _TEXT_NAMES or not isinstance(
            text["raw_commit_message"], str
        ):
            raise ValueError("TEXT must preserve only raw_commit_message")
        keys = {_key(item) for item in (*code, *process, *text)}
        if keys & _FORBIDDEN_PREDICTOR_KEYS:
            raise ValueError("predictor mappings contain a prohibited leakage field")
        if any(type(value) is not int or value < 0 for value in code.values()):
            raise ValueError("CODE values must be non-negative integers")
        if (
            type(process["parent_count"]) is not int
            or process["parent_count"] < 0
            or type(process["is_merge_commit"]) is not int
            or process["is_merge_commit"] not in {0, 1}
        ):
            raise ValueError("PROCESS values are outside their approved domains")
        if type(self.target) is not int or self.target not in {0, 1}:
            raise ValueError("target must be the frozen binary integer assignment")
        for name in (
            "source_multimodal_record_digest",
            "source_target_assignment_artifact_digest",
        ):
            _require_digest(getattr(self, name), name)
        object.__setattr__(self, "code_features", MappingProxyType(code))
        object.__setattr__(self, "process_features", MappingProxyType(process))
        object.__setattr__(self, "text_features", MappingProxyType(text))
        if self.observation_digest != self.calculate_digest(**self._content()):
            raise ValueError("observation_digest must identify canonical content")

    def _content(self) -> dict[str, object]:
        return {
            item.name: getattr(self, item.name)
            for item in fields(self)
            if item.name != "observation_digest"
        }

    @classmethod
    def calculate_digest(cls, **content: object) -> str:
        content.pop("observation_digest", None)
        return _digest(content)

    def predictive_features(self) -> Mapping[str, Mapping[str, object]]:
        return MappingProxyType(
            {
                "code": self.code_features,
                "process": self.process_features,
                "text": self.text_features,
            }
        )

    def to_dict(self) -> dict[str, object]:
        return _thaw(self)  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class QtDatasetAssemblyValidation:
    is_valid: bool
    feature_record_count: int
    target_assignment_count: int
    observation_count: int
    positive_count: int
    negative_count: int
    exclusion_count: int
    error_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if type(self.is_valid) is not bool:
            raise TypeError("is_valid must be bool")
        for name in (
            "feature_record_count",
            "target_assignment_count",
            "observation_count",
            "positive_count",
            "negative_count",
            "exclusion_count",
        ):
            if type(getattr(self, name)) is not int or getattr(self, name) < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        if self.is_valid != (not self.error_codes):
            raise ValueError("validation status must agree with error_codes")
        if self.positive_count + self.negative_count != self.observation_count:
            raise ValueError("target counts must equal observation count")
        if self.exclusion_count != 0:
            raise ValueError("exact eligible-universe assembly has no exclusions")

    def to_dict(self) -> dict[str, object]:
        return _thaw(self)  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class QtMultimodalDatasetAssemblyResult:
    specification: QtDatasetAssemblySpecification
    policy: QtDatasetAssemblyPolicy
    observations: tuple[QtDatasetObservation, ...]
    validation: QtDatasetAssemblyValidation
    dataset_artifact: ScientificArtifactReference
    assembly_identity_digest: str
    metadata: Mapping[str, object] = field(default_factory=lambda: _EMPTY)

    def __post_init__(self) -> None:
        if not isinstance(
            self.specification, QtDatasetAssemblySpecification
        ) or not isinstance(self.policy, QtDatasetAssemblyPolicy):
            raise TypeError("result requires Qt dataset specification and policy")
        if self.specification.assembly_policy_digest != self.policy.policy_digest:
            raise ValueError("specification and assembly policy disagree")
        observations = tuple(self.observations)
        identifiers = tuple(item.commit_identifier for item in observations)
        if identifiers != tuple(sorted(set(identifiers))):
            raise ValueError("observations must be unique and canonically ordered")
        if not self.validation.is_valid or self.validation.observation_count != len(
            observations
        ):
            raise ValueError("validation and observations disagree")
        scientific_content = {
            "specification": self.specification,
            "policy": self.policy,
            "observations": observations,
            "validation": self.validation,
        }
        content_digest = _digest(scientific_content)
        expected_path = (
            f"artifacts/qtbase/datasets/{self.specification.repository_revision}/"
            "qt-multimodal-commit-dataset.jsonl"
        )
        if (
            self.dataset_artifact.artifact_role is not ScientificArtifactRole.DATASET
            or self.dataset_artifact.artifact_name != "qtbase-multimodal-commit-dataset"
            or self.dataset_artifact.repository_relative_path != expected_path
            or self.dataset_artifact.content_digest != content_digest
            or self.dataset_artifact.record_count != len(observations)
        ):
            raise ValueError("dataset artifact identity is inconsistent")
        expected_identity = _digest(
            {
                "dataset_artifact_digest": content_digest,
                "dataset_specification_digest": self.specification.specification_digest,
                "ordered_observation_digests": [
                    item.observation_digest for item in observations
                ],
            }
        )
        if self.assembly_identity_digest != expected_identity:
            raise ValueError("assembly_identity_digest is inconsistent")
        object.__setattr__(self, "observations", observations)
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))

    def to_dict(self) -> dict[str, object]:
        return _thaw(self)  # type: ignore[return-value]


def build_qt_dataset_assembly_specification(
    commits: QtCommitExtractionResult,
    features: QtMultimodalFeatureConstructionResult,
    targets: ScientificTargetAssignmentResult,
    policy: QtDatasetAssemblyPolicy | None = None,
) -> QtDatasetAssemblySpecification:
    """Bind every approved upstream scientific identity used by assembly."""
    if not isinstance(commits, QtCommitExtractionResult):
        raise TypeError("commits must be QtCommitExtractionResult")
    if not isinstance(features, QtMultimodalFeatureConstructionResult):
        raise TypeError("features must be QtMultimodalFeatureConstructionResult")
    if not isinstance(targets, ScientificTargetAssignmentResult):
        raise TypeError("targets must be ScientificTargetAssignmentResult")
    policy = policy or QtDatasetAssemblyPolicy.create()
    if (
        commits.artifact != features.source_commit_artifact
        or commits.source_revision != features.repository_revision
        or commits.source_snapshot_digest != features.repository_snapshot_digest
    ):
        raise QtDatasetAssemblyError(
            "commit extraction and features do not bind the same scientific source"
        )
    if (
        targets.specification.repository_snapshot_digest
        != features.repository_snapshot_digest
        or targets.specification.commit_artifact_digest
        != features.source_commit_artifact.content_digest
    ):
        raise QtDatasetAssemblyError(
            "feature and target artifacts do not bind the same snapshot and commits"
        )
    values = {
        "schema_version": "1.0.0",
        "specification_version": "qt-multimodal-dataset-assembly-1.0.0",
        "repository_revision": features.repository_revision,
        "repository_snapshot_digest": features.repository_snapshot_digest,
        "commit_artifact_digest": features.source_commit_artifact.content_digest,
        "multimodal_construction_identity_digest": (
            features.construction_identity_digest
        ),
        "modality_artifact_digests": _ordered_artifact_digests(
            features.modality_artifacts
        ),
        "feature_inventory_digest": features.feature_inventory_digest,
        "target_assignment_artifact_digest": (
            targets.artifact_binding.artifact.content_digest
        ),
        "target_assignment_binding_digest": targets.artifact_binding.binding_digest,
        "target_assignment_specification_digest": (
            targets.specification.specification_digest
        ),
        "target_assignment_policy_digest": targets.policy.policy_digest,
        "assembly_policy_digest": policy.policy_digest,
    }
    return QtDatasetAssemblySpecification(
        **values,
        specification_digest=QtDatasetAssemblySpecification.calculate_digest(**values),
    )


def _unique_by_commit(records: Sequence[object], side: str) -> dict[str, object]:
    result: dict[str, object] = {}
    for record in records:
        identifier = getattr(record, "commit_identifier", None)
        if side == "commit":
            identifier = getattr(record, "commit_id", None)
        if side == "target":
            identifier = getattr(record, "observation_identifier", None)
        if not isinstance(identifier, str) or not _OBJECT_ID.fullmatch(identifier):
            raise QtDatasetAssemblyError(f"{side} record has an ambiguous identity")
        if identifier in result:
            raise QtDatasetAssemblyError(
                f"duplicate {side} commit identity: {identifier}"
            )
        result[identifier] = record
    return result


def assemble_qt_multimodal_dataset(
    commits: QtCommitExtractionResult,
    features: QtMultimodalFeatureConstructionResult,
    targets: ScientificTargetAssignmentResult,
    specification: QtDatasetAssemblySpecification,
    policy: QtDatasetAssemblyPolicy,
    *,
    metadata: Mapping[str, object] = _EMPTY,
) -> QtMultimodalDatasetAssemblyResult:
    """Join frozen feature and target artifacts by immutable commit identity only."""
    expected = build_qt_dataset_assembly_specification(
        commits, features, targets, policy
    )
    if specification != expected:
        raise QtDatasetAssemblyError(
            "assembly specification does not bind exact inputs"
        )
    commit_by_id = _unique_by_commit(commits.records, "commit")
    feature_by_id = _unique_by_commit(features.records, "feature")
    target_by_id = _unique_by_commit(targets.assignments, "target")
    if not (set(commit_by_id) == set(feature_by_id) == set(target_by_id)):
        all_identifiers = set(commit_by_id) | set(feature_by_id) | set(target_by_id)
        missing_commits = sorted(all_identifiers - set(commit_by_id))
        missing_targets = sorted(all_identifiers - set(target_by_id))
        missing_features = sorted(all_identifiers - set(feature_by_id))
        raise QtDatasetAssemblyError(
            "commit, feature, and target eligible universes differ: "
            f"missing_commits={missing_commits}, missing_targets={missing_targets}, "
            f"missing_features={missing_features}"
        )
    observations = []
    for identifier in sorted(feature_by_id):
        feature = feature_by_id[identifier]
        assignment = target_by_id[identifier]
        commit = commit_by_id[identifier]
        if not isinstance(assignment, ScientificTargetAssignment):
            raise TypeError("target records must be ScientificTargetAssignment")
        if (
            assignment.target_field != targets.policy.target_field
            or type(assignment.target_label) is not int
            or assignment.target_label
            not in {targets.policy.negative_label, targets.policy.positive_label}
        ):
            raise QtDatasetAssemblyError("target assignment violates frozen policy")
        values = {
            "commit_identifier": identifier,
            "committed_at": commit.committed_at,
            "code_features": feature.code.feature_values(),
            "process_features": feature.process,
            "text_features": feature.text,
            "target": assignment.target_label,
            "source_multimodal_record_digest": feature.record_digest,
            "source_target_assignment_artifact_digest": (
                targets.artifact_binding.artifact.content_digest
            ),
        }
        observations.append(
            QtDatasetObservation(
                **values,
                observation_digest=QtDatasetObservation.calculate_digest(**values),
            )
        )
    ordered = tuple(observations)
    positives = sum(item.target == targets.policy.positive_label for item in ordered)
    validation = QtDatasetAssemblyValidation(
        True,
        len(feature_by_id),
        len(target_by_id),
        len(ordered),
        positives,
        len(ordered) - positives,
        0,
    )
    content = {
        "specification": specification,
        "policy": policy,
        "observations": ordered,
        "validation": validation,
    }
    artifact = ScientificArtifactReference(
        "qtbase-multimodal-commit-dataset",
        ScientificArtifactRole.DATASET,
        f"artifacts/qtbase/datasets/{specification.repository_revision}/"
        "qt-multimodal-commit-dataset.jsonl",
        _digest(content),
        specification.schema_version,
        len(ordered),
    )
    identity = _digest(
        {
            "dataset_artifact_digest": artifact.content_digest,
            "dataset_specification_digest": specification.specification_digest,
            "ordered_observation_digests": [
                item.observation_digest for item in ordered
            ],
        }
    )
    return QtMultimodalDatasetAssemblyResult(
        specification,
        policy,
        ordered,
        validation,
        artifact,
        identity,
        metadata,
    )
