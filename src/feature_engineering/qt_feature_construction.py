"""Reproducible, leakage-safe construction of approved Qt feature values."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, fields, is_dataclass
from enum import Enum
from types import MappingProxyType

from dataset.scientific_builder_contracts import (
    ScientificArtifactReference,
    ScientificArtifactRole,
)
from dataset.scientific_dataset_contract import ScientificFeatureModality
from extraction.qt_commit_extraction import QtCommitExtractionResult
from extraction.qt_diff_statistics_extraction import (
    QtCommitDiffStatistics,
    QtDiffStatisticsExtractionResult,
)

from .qt_feature_inventory import QtFeatureAdmissibility, QtFeatureInventory

__all__ = [
    "QT_CODE_FEATURE_NAMES",
    "QT_UNAVAILABLE_PROCESS_FEATURE_NAMES",
    "QtCodeFeatureRecord",
    "QtCodeFeatureConstructionResult",
    "QtMultimodalFeatureRecord",
    "QtMultimodalFeatureConstructionResult",
    "construct_qt_code_features",
    "construct_qt_multimodal_features",
]

QT_CODE_FEATURE_NAMES = (
    "binary_files",
    "deletions",
    "files_added",
    "files_changed",
    "files_copied",
    "files_modified",
    "files_removed",
    "files_renamed",
    "files_type_changed",
    "has_binary_files",
    "insertions",
    "text_files",
    "total_churn",
)
QT_UNAVAILABLE_PROCESS_FEATURE_NAMES = (
    "developer_prior_experience",
    "prior_file_change_count",
    "time_since_previous_change",
)

_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_OBJECT_ID = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
_PROHIBITED_KEYS = frozenset(
    {
        "bug_confidence",
        "candidate",
        "candidate_artifact",
        "candidate_metadata",
        "defect_inducing_candidate",
        "future_defect_count",
        "future_information",
        "issue",
        "issue_artifact",
        "issue_link",
        "label",
        "labels",
        "target",
        "target_assignment",
        "target_evidence",
        "target_label",
    }
)
_KEYWORD_FEATURE = re.compile(
    r"(^|_)(bug|defect|fix|issue).*(keyword|indicator|flag)($|_)"
    r"|(^|_)(has|contains)_(bug|defect|fix|issue)($|_)"
)
_EMPTY: Mapping[str, object] = MappingProxyType({})


def _thaw(value: object) -> object:
    if is_dataclass(value) and not isinstance(value, type):
        return {
            item.name: _thaw(getattr(value, item.name))
            for item in fields(value)
            if not item.name.startswith("_")
        }
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
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _count(value: object, name: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


def _binary(value: object, name: str) -> int:
    if type(value) is not int or value not in (0, 1):
        raise ValueError(f"{name} must be the canonical integer 0 or 1")
    return value


def _validate_digest(value: str, name: str) -> None:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")


def _validate_metadata(value: Mapping[str, object]) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TypeError("metadata must be a mapping")

    def freeze(item: object, path: str) -> object:
        if isinstance(item, Mapping):
            result: dict[str, object] = {}
            for key, nested in item.items():
                if not isinstance(key, str):
                    raise TypeError(f"{path} keys must be strings")
                normalized = re.sub(r"[^a-z0-9]+", "_", key.lower()).strip("_")
                if normalized in _PROHIBITED_KEYS or _KEYWORD_FEATURE.search(
                    normalized
                ):
                    raise ValueError(f"{path} contains prohibited field {key!r}")
                result[key] = freeze(nested, f"{path}.{key}")
            return MappingProxyType(result)
        if isinstance(item, (list, tuple)):
            return tuple(freeze(nested, path) for nested in item)
        if isinstance(item, float) and not math.isfinite(item):
            raise ValueError(f"{path} must contain finite numbers")
        if item is None or type(item) in {bool, int, float}:
            return item
        if isinstance(item, str):
            if item.startswith("/"):
                raise ValueError(f"{path} must not contain machine-local paths")
            return item
        raise TypeError(f"{path} must contain deterministic JSON-compatible values")

    return freeze(value, "metadata")  # type: ignore[return-value]


def _modality_content(
    base: Mapping[str, object],
    records: Sequence[QtMultimodalFeatureRecord],
    modality: str,
) -> dict[str, object]:
    values: list[dict[str, object]] = []
    for record in records:
        if modality == "code":
            feature_values: object = dict(record.code.feature_values())
        elif modality == "process":
            feature_values = dict(record.process)
        else:
            feature_values = dict(record.text)
        values.append(
            {
                "commit_identifier": record.commit_identifier,
                "feature_values": feature_values,
                "record_digest": record.record_digest,
            }
        )
    return {**base, "modality": modality, "records": values}


@dataclass(frozen=True, slots=True)
class QtCodeFeatureRecord:
    """The exact 13 approved structural predictors for one historical commit."""

    commit_identifier: str
    binary_files: int
    deletions: int
    files_added: int
    files_changed: int
    files_copied: int
    files_modified: int
    files_removed: int
    files_renamed: int
    files_type_changed: int
    has_binary_files: int
    insertions: int
    text_files: int
    total_churn: int
    record_digest: str

    def __post_init__(self) -> None:
        if not _OBJECT_ID.fullmatch(self.commit_identifier):
            raise ValueError("commit_identifier must be a complete Git identifier")
        for name in QT_CODE_FEATURE_NAMES:
            if name == "has_binary_files":
                _binary(getattr(self, name), name)
            else:
                _count(getattr(self, name), name)
        if self.total_churn != self.insertions + self.deletions:
            raise ValueError("total_churn must equal insertions plus deletions")
        if self.has_binary_files != int(self.binary_files > 0):
            raise ValueError("has_binary_files must agree with binary_files")
        content = {
            "commit_identifier": self.commit_identifier,
            "features": {name: getattr(self, name) for name in QT_CODE_FEATURE_NAMES},
        }
        if self.record_digest != _digest(content):
            raise ValueError("record_digest must identify canonical CODE content")

    def feature_values(self) -> Mapping[str, int]:
        return MappingProxyType(
            {name: getattr(self, name) for name in QT_CODE_FEATURE_NAMES}
        )

    def to_dict(self) -> dict[str, object]:
        return _thaw(self)  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class QtCodeFeatureConstructionResult:
    repository_revision: str
    source_diff_statistics_artifact: ScientificArtifactReference
    feature_specification_digest: str
    records: tuple[QtCodeFeatureRecord, ...]
    artifact: ScientificArtifactReference
    code_feature_identity_digest: str
    metadata: Mapping[str, object] = field(default_factory=lambda: _EMPTY)

    def __post_init__(self) -> None:
        if not _OBJECT_ID.fullmatch(self.repository_revision):
            raise ValueError("repository_revision must be a complete Git identifier")
        if (
            self.source_diff_statistics_artifact.artifact_role
            is not ScientificArtifactRole.DIFF_ARTIFACT
        ):
            raise ValueError("CODE features require the approved diff-artifact")
        _validate_metadata(self.source_diff_statistics_artifact.metadata)
        records = tuple(self.records)
        if any(not isinstance(item, QtCodeFeatureRecord) for item in records):
            raise TypeError("records must contain QtCodeFeatureRecord values")
        identifiers = tuple(item.commit_identifier for item in records)
        if identifiers != tuple(sorted(identifiers)) or len(identifiers) != len(
            set(identifiers)
        ):
            raise ValueError("CODE records must be unique and canonically ordered")
        _validate_digest(
            self.feature_specification_digest, "feature_specification_digest"
        )
        scientific_content = {
            "repository_name": "qtbase",
            "repository_revision": self.repository_revision,
            "source_diff_statistics_artifact": (
                self.source_diff_statistics_artifact.to_dict()
            ),
            "feature_specification_digest": self.feature_specification_digest,
            "feature_names": list(QT_CODE_FEATURE_NAMES),
            "records": records,
        }
        content_digest = _digest(scientific_content)
        expected_path = (
            f"artifacts/qtbase/code-features/{self.repository_revision}/"
            "qt-code-features.jsonl"
        )
        if (
            self.artifact.artifact_role is not ScientificArtifactRole.CODE_FEATURE
            or self.artifact.artifact_name != "qtbase-code-features"
            or self.artifact.repository_relative_path != expected_path
            or self.artifact.content_digest != content_digest
            or self.artifact.record_count != len(records)
        ):
            raise ValueError("CODE feature artifact identity is inconsistent")
        identity = _digest(
            {
                "artifact_content_digest": content_digest,
                "source_diff_statistics_digest": (
                    self.source_diff_statistics_artifact.content_digest
                ),
                "repository_revision": self.repository_revision,
                "feature_specification_digest": self.feature_specification_digest,
            }
        )
        if self.code_feature_identity_digest != identity:
            raise ValueError("code_feature_identity_digest is inconsistent")
        object.__setattr__(self, "records", records)
        object.__setattr__(self, "metadata", _validate_metadata(self.metadata))

    def to_dict(self) -> dict[str, object]:
        return _thaw(self)  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class QtMultimodalFeatureRecord:
    """One modality-separated predictor record for an eligible Qt commit."""

    commit_identifier: str
    code: QtCodeFeatureRecord
    process: Mapping[str, int]
    text: Mapping[str, str]
    unavailable_process_features: tuple[str, ...]
    source_commit_artifact_digest: str
    source_code_feature_artifact_digest: str
    feature_inventory_digest: str
    record_digest: str

    def __post_init__(self) -> None:
        if self.code.commit_identifier != self.commit_identifier:
            raise ValueError("CODE and multimodal commit identifiers must agree")
        process = dict(self.process)
        if tuple(process) != ("is_merge_commit", "parent_count"):
            raise ValueError(
                "PROCESS values must contain only approved canonical fields"
            )
        _binary(process["is_merge_commit"], "is_merge_commit")
        _count(process["parent_count"], "parent_count")
        if process["is_merge_commit"] != int(process["parent_count"] > 1):
            raise ValueError("is_merge_commit must agree with parent_count")
        text = dict(self.text)
        if tuple(text) != ("raw_commit_message",) or not isinstance(
            text["raw_commit_message"], str
        ):
            raise ValueError("TEXT must contain only the exact raw_commit_message")
        if self.unavailable_process_features != QT_UNAVAILABLE_PROCESS_FEATURE_NAMES:
            raise ValueError("unavailable PROCESS features must remain explicit")
        for name in (
            "source_commit_artifact_digest",
            "source_code_feature_artifact_digest",
            "feature_inventory_digest",
        ):
            _validate_digest(getattr(self, name), name)
        object.__setattr__(self, "process", MappingProxyType(process))
        object.__setattr__(self, "text", MappingProxyType(text))
        content = {
            "commit_identifier": self.commit_identifier,
            "code": self.code,
            "process": process,
            "text": text,
            "unavailable_process_features": self.unavailable_process_features,
            "source_commit_artifact_digest": self.source_commit_artifact_digest,
            "source_code_feature_artifact_digest": (
                self.source_code_feature_artifact_digest
            ),
            "feature_inventory_digest": self.feature_inventory_digest,
        }
        if self.record_digest != _digest(content):
            raise ValueError("record_digest must identify canonical multimodal content")

    def to_dict(self) -> dict[str, object]:
        return _thaw(self)  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class QtMultimodalFeatureConstructionResult:
    repository_revision: str
    repository_snapshot_digest: str
    source_commit_artifact: ScientificArtifactReference
    source_code_feature_artifact: ScientificArtifactReference
    feature_inventory_digest: str
    records: tuple[QtMultimodalFeatureRecord, ...]
    modality_artifacts: tuple[ScientificArtifactReference, ...]
    construction_identity_digest: str
    metadata: Mapping[str, object] = field(default_factory=lambda: _EMPTY)

    def __post_init__(self) -> None:
        if (
            self.source_commit_artifact.artifact_role
            is not ScientificArtifactRole.COMMIT_ARTIFACT
        ):
            raise ValueError("source_commit_artifact must have commit-artifact role")
        if (
            self.source_code_feature_artifact.artifact_role
            is not ScientificArtifactRole.CODE_FEATURE
        ):
            raise ValueError("source_code_feature_artifact must have code-feature role")
        for name in ("repository_snapshot_digest", "feature_inventory_digest"):
            _validate_digest(getattr(self, name), name)
        records = tuple(self.records)
        identifiers = tuple(item.commit_identifier for item in records)
        if identifiers != tuple(sorted(identifiers)) or len(identifiers) != len(
            set(identifiers)
        ):
            raise ValueError(
                "multimodal records must be unique and canonically ordered"
            )
        artifacts = tuple(self.modality_artifacts)
        expected_roles = (
            ScientificArtifactRole.CODE_FEATURE,
            ScientificArtifactRole.PROCESS_FEATURE,
            ScientificArtifactRole.TEXT_FEATURE,
        )
        if tuple(item.artifact_role for item in artifacts) != expected_roles:
            raise ValueError(
                "modality artifacts must use canonical CODE, PROCESS, TEXT order"
            )
        base = {
            "repository_revision": self.repository_revision,
            "repository_snapshot_digest": self.repository_snapshot_digest,
            "source_commit_artifact": self.source_commit_artifact.to_dict(),
            "source_code_feature_artifact": self.source_code_feature_artifact.to_dict(),
            "feature_inventory_digest": self.feature_inventory_digest,
        }
        for artifact, role in zip(artifacts, expected_roles, strict=True):
            modality = role.value.removesuffix("-feature")
            expected_digest = _digest(_modality_content(base, records, modality))
            expected_path = (
                f"artifacts/qtbase/features/{self.repository_revision}/"
                f"qt-{modality}-features.jsonl"
            )
            if (
                artifact.content_digest != expected_digest
                or artifact.repository_relative_path != expected_path
                or artifact.record_count != len(records)
            ):
                raise ValueError(f"{modality} artifact identity is inconsistent")
        identity = _digest(
            {
                **base,
                "modality_artifacts": [item.to_dict() for item in artifacts],
            }
        )
        if self.construction_identity_digest != identity:
            raise ValueError("construction_identity_digest is inconsistent")
        object.__setattr__(self, "records", records)
        object.__setattr__(self, "modality_artifacts", artifacts)
        object.__setattr__(self, "metadata", _validate_metadata(self.metadata))

    def to_dict(self) -> dict[str, object]:
        return _thaw(self)  # type: ignore[return-value]


def _code_record(statistics: QtCommitDiffStatistics) -> QtCodeFeatureRecord:
    values = {name: int(getattr(statistics, name)) for name in QT_CODE_FEATURE_NAMES}
    content = {"commit_identifier": statistics.commit_identifier, "features": values}
    return QtCodeFeatureRecord(
        statistics.commit_identifier, **values, record_digest=_digest(content)
    )


def construct_qt_code_features(
    source: QtDiffStatisticsExtractionResult,
) -> QtCodeFeatureConstructionResult:
    """Derive exactly the frozen 13 CODE predictors from diff statistics."""
    if not isinstance(source, QtDiffStatisticsExtractionResult):
        raise TypeError("source must be QtDiffStatisticsExtractionResult")
    records = tuple(
        sorted(
            map(_code_record, source.commit_statistics),
            key=lambda item: item.commit_identifier,
        )
    )
    specification_digest = _digest(
        {
            "feature_names": list(QT_CODE_FEATURE_NAMES),
            "source_fields": list(QT_CODE_FEATURE_NAMES),
            "construction": "identity mapping from validated QtCommitDiffStatistics",
            "schema_version": "1.0.0",
        }
    )
    content = {
        "repository_name": "qtbase",
        "repository_revision": source.specification.repository_revision,
        "source_diff_statistics_artifact": source.extraction_artifact.to_dict(),
        "feature_specification_digest": specification_digest,
        "feature_names": list(QT_CODE_FEATURE_NAMES),
        "records": records,
    }
    digest = _digest(content)
    artifact = ScientificArtifactReference(
        "qtbase-code-features",
        ScientificArtifactRole.CODE_FEATURE,
        f"artifacts/qtbase/code-features/{source.specification.repository_revision}/qt-code-features.jsonl",
        digest,
        "1.0.0",
        len(records),
        metadata={"source_role": ScientificArtifactRole.DIFF_ARTIFACT.value},
    )
    identity = _digest(
        {
            "artifact_content_digest": digest,
            "source_diff_statistics_digest": source.extraction_artifact.content_digest,
            "repository_revision": source.specification.repository_revision,
            "feature_specification_digest": specification_digest,
        }
    )
    return QtCodeFeatureConstructionResult(
        source.specification.repository_revision,
        source.extraction_artifact,
        specification_digest,
        records,
        artifact,
        identity,
    )


def construct_qt_multimodal_features(
    commits: QtCommitExtractionResult,
    code_features: QtCodeFeatureConstructionResult,
    inventory: QtFeatureInventory,
) -> QtMultimodalFeatureConstructionResult:
    """Construct one canonical CODE/PROCESS/TEXT record per eligible commit."""
    if not isinstance(commits, QtCommitExtractionResult):
        raise TypeError("commits must be QtCommitExtractionResult")
    if not isinstance(code_features, QtCodeFeatureConstructionResult):
        raise TypeError("code_features must be QtCodeFeatureConstructionResult")
    if not isinstance(inventory, QtFeatureInventory):
        raise TypeError("inventory must be QtFeatureInventory")
    if commits.source_revision != code_features.repository_revision:
        raise ValueError(
            "commit and CODE artifacts must bind the same repository revision"
        )
    sources = {item.artifact_name: item for item in inventory.source_artifacts}
    if (
        sources.get(commits.artifact.artifact_name) != commits.artifact
        or sources.get(code_features.artifact.artifact_name) != code_features.artifact
    ):
        raise ValueError("inventory must bind the exact commit and CODE artifacts")
    admissible = {
        modality: tuple(
            item.feature_id
            for item in inventory.features
            if item.modality is modality
            and item.admissibility is QtFeatureAdmissibility.ADMISSIBLE
        )
        for modality in ScientificFeatureModality
        if modality
        in {
            ScientificFeatureModality.CODE,
            ScientificFeatureModality.PROCESS,
            ScientificFeatureModality.TEXT,
        }
    }
    if admissible != {
        ScientificFeatureModality.CODE: QT_CODE_FEATURE_NAMES,
        ScientificFeatureModality.PROCESS: ("is_merge_commit", "parent_count"),
        ScientificFeatureModality.TEXT: ("raw_commit_message",),
    }:
        raise ValueError("inventory admissible features do not match the frozen set")
    commit_by_id = {item.commit_id: item for item in commits.records}
    code_by_id = {item.commit_identifier: item for item in code_features.records}
    if set(commit_by_id) != set(code_by_id):
        raise ValueError(
            "eligible commits must match exactly across approved artifacts"
        )
    records = []
    for identifier in sorted(commit_by_id):
        commit = commit_by_id[identifier]
        code = code_by_id[identifier]
        process = {
            "is_merge_commit": int(len(commit.parent_ids) > 1),
            "parent_count": len(commit.parent_ids),
        }
        text = {"raw_commit_message": commit.message}
        content = {
            "commit_identifier": identifier,
            "code": code,
            "process": process,
            "text": text,
            "unavailable_process_features": QT_UNAVAILABLE_PROCESS_FEATURE_NAMES,
            "source_commit_artifact_digest": commits.artifact.content_digest,
            "source_code_feature_artifact_digest": (
                code_features.artifact.content_digest
            ),
            "feature_inventory_digest": inventory.inventory_digest,
        }
        records.append(
            QtMultimodalFeatureRecord(
                identifier,
                code,
                process,
                text,
                QT_UNAVAILABLE_PROCESS_FEATURE_NAMES,
                commits.artifact.content_digest,
                code_features.artifact.content_digest,
                inventory.inventory_digest,
                _digest(content),
            )
        )
    ordered_records = tuple(records)
    base = {
        "repository_revision": commits.source_revision,
        "repository_snapshot_digest": commits.source_snapshot_digest,
        "source_commit_artifact": commits.artifact.to_dict(),
        "source_code_feature_artifact": code_features.artifact.to_dict(),
        "feature_inventory_digest": inventory.inventory_digest,
    }
    artifacts = []
    for role in (
        ScientificArtifactRole.CODE_FEATURE,
        ScientificArtifactRole.PROCESS_FEATURE,
        ScientificArtifactRole.TEXT_FEATURE,
    ):
        modality = role.value.removesuffix("-feature")
        artifacts.append(
            ScientificArtifactReference(
                f"qtbase-{modality}-feature-values",
                role,
                f"artifacts/qtbase/features/{commits.source_revision}/qt-{modality}-features.jsonl",
                _digest(_modality_content(base, ordered_records, modality)),
                "1.0.0",
                len(ordered_records),
            )
        )
    modality_artifacts = tuple(artifacts)
    identity = _digest(
        {**base, "modality_artifacts": [item.to_dict() for item in modality_artifacts]}
    )
    return QtMultimodalFeatureConstructionResult(
        commits.source_revision,
        commits.source_snapshot_digest,
        commits.artifact,
        code_features.artifact,
        inventory.inventory_digest,
        ordered_records,
        modality_artifacts,
        identity,
    )
