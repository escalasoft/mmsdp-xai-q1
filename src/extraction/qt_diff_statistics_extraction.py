"""Deterministic structural statistics from an immutable Qt diff artifact."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path, PurePosixPath
from types import MappingProxyType

from dataset.scientific_builder_contracts import (
    ScientificArtifactReference,
    ScientificArtifactRole,
)
from extraction.qt_diff_extraction import QtDiffExtractionResult, QtFileChangeRecord

__all__ = [
    "QtDiffStatisticsSpecification",
    "QtFileDiffStatistics",
    "QtCommitDiffStatistics",
    "QtDiffStatisticsExtractionResult",
    "QtDiffStatisticsExtractor",
]

_NAME = "qtbase"
_URL = "https://code.qt.io/qt/qtbase.git"
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_OBJECT_ID = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
_EMPTY: Mapping[str, object] = MappingProxyType({})
_POLICIES = {
    "ordering_policy": "diff-artifact-commit-and-file-order",
    "statistics_policy": "structural-counts-only",
    "binary_statistics_policy": "null-line-counts-and-explicit-indicator",
    "churn_policy": "text-insertions-plus-deletions",
}
_BANNED_KEYS = {
    "created_at",
    "duration",
    "environment",
    "hostname",
    "label",
    "local_path",
    "runtime_identifier",
    "runtime_timestamp",
    "target",
    "timestamp",
    "username",
}


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
            normalized = re.sub(r"[^a-z0-9]+", "_", key.lower()).strip("_")
            if normalized in _BANNED_KEYS:
                raise ValueError(f"{path} contains forbidden field {key!r}")
            result[key] = _freeze(item, f"{path}.{key}")
        return MappingProxyType(result)
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item, path) for item in value)
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{path} contains a non-finite number")
    if value is None or type(value) in {bool, int, float}:
        return value
    if isinstance(value, str):
        if Path(value).is_absolute():
            raise ValueError(f"{path} contains machine-local information")
        return value
    raise TypeError(f"{path} must contain JSON-compatible values")


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
    if isinstance(value, ScientificArtifactRole):
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


@dataclass(frozen=True, slots=True)
class QtDiffStatisticsSpecification:
    repository_name: str
    canonical_repository_url: str
    repository_revision: str
    diff_artifact_digest: str
    extraction_policy_version: str
    ordering_policy: str = _POLICIES["ordering_policy"]
    statistics_policy: str = _POLICIES["statistics_policy"]
    binary_statistics_policy: str = _POLICIES["binary_statistics_policy"]
    churn_policy: str = _POLICIES["churn_policy"]
    metadata: Mapping[str, object] = field(default_factory=lambda: _EMPTY)

    def __post_init__(self) -> None:
        if self.repository_name != _NAME:
            raise ValueError("repository_name must equal 'qtbase'")
        if self.canonical_repository_url != _URL:
            raise ValueError(f"canonical_repository_url must equal {_URL!r}")
        if not _OBJECT_ID.fullmatch(self.repository_revision):
            raise ValueError("repository_revision must be a complete Git identifier")
        if not _SHA256.fullmatch(self.diff_artifact_digest):
            raise ValueError("diff_artifact_digest must be a lowercase SHA-256 digest")
        for name, expected in _POLICIES.items():
            if getattr(self, name) != expected:
                raise ValueError(f"{name} must equal {expected!r}")
        object.__setattr__(
            self,
            "extraction_policy_version",
            _text(self.extraction_policy_version, "extraction_policy_version"),
        )
        object.__setattr__(self, "metadata", _freeze(self.metadata))

    def to_dict(self) -> dict[str, object]:
        return _thaw(self)  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class QtFileDiffStatistics:
    commit_identifier: str
    change_type: str
    old_path: str | None
    new_path: str | None
    path: str
    is_binary: bool
    insertions: int | None
    deletions: int | None
    total_churn: int | None

    def __post_init__(self) -> None:
        if not _OBJECT_ID.fullmatch(self.commit_identifier):
            raise ValueError("commit_identifier must be a complete Git identifier")
        for name in ("old_path", "new_path", "path"):
            value = getattr(self, name)
            if value is None and name != "path":
                continue
            if (
                not isinstance(value, str)
                or not value
                or PurePosixPath(value).is_absolute()
            ):
                raise ValueError(f"{name} must be repository-relative")
        if type(self.is_binary) is not bool:
            raise TypeError("is_binary must be bool")
        if self.is_binary:
            if any(
                value is not None
                for value in (self.insertions, self.deletions, self.total_churn)
            ):
                raise ValueError("binary files require null line statistics")
        else:
            insertions = _count(self.insertions, "insertions")
            deletions = _count(self.deletions, "deletions")
            if self.total_churn != insertions + deletions:
                raise ValueError("total_churn must equal insertions plus deletions")

    def to_dict(self) -> dict[str, object]:
        return _thaw(self)  # type: ignore[return-value]


_KINDS = ("added", "modified", "deleted", "renamed", "copied", "type-changed")


@dataclass(frozen=True, slots=True)
class QtCommitDiffStatistics:
    commit_identifier: str
    file_statistics: tuple[QtFileDiffStatistics, ...]
    files_changed: int
    files_added: int
    files_modified: int
    files_removed: int
    files_renamed: int
    files_copied: int
    files_type_changed: int
    text_files: int
    binary_files: int
    has_binary_files: bool
    insertions: int
    deletions: int
    total_churn: int
    record_digest: str

    def __post_init__(self) -> None:
        if not _OBJECT_ID.fullmatch(self.commit_identifier):
            raise ValueError("commit_identifier must be a complete Git identifier")
        records = tuple(self.file_statistics)
        if any(
            not isinstance(item, QtFileDiffStatistics)
            or item.commit_identifier != self.commit_identifier
            for item in records
        ):
            raise TypeError("file_statistics must contain matching immutable records")
        paths = [
            (item.path, item.change_type, item.old_path or "", item.new_path or "")
            for item in records
        ]
        if paths != sorted(paths):
            raise ValueError(
                "file_statistics must use canonical deterministic ordering"
            )
        counts = {
            kind: sum(item.change_type == kind for item in records) for kind in _KINDS
        }
        expected = (
            len(records),
            counts["added"],
            counts["modified"],
            counts["deleted"],
            counts["renamed"],
            counts["copied"],
            counts["type-changed"],
            sum(not item.is_binary for item in records),
            sum(item.is_binary for item in records),
        )
        actual = (
            self.files_changed,
            self.files_added,
            self.files_modified,
            self.files_removed,
            self.files_renamed,
            self.files_copied,
            self.files_type_changed,
            self.text_files,
            self.binary_files,
        )
        if actual != expected or any(type(item) is not int for item in actual):
            raise ValueError("structural file counts are inconsistent")
        insertions = sum(item.insertions or 0 for item in records)
        deletions = sum(item.deletions or 0 for item in records)
        if (self.insertions, self.deletions, self.total_churn) != (
            insertions,
            deletions,
            insertions + deletions,
        ):
            raise ValueError("patch line statistics are inconsistent")
        if self.has_binary_files is not bool(self.binary_files):
            raise ValueError("has_binary_files is inconsistent")
        content = {
            name: getattr(self, name)
            for name in (
                "commit_identifier",
                "file_statistics",
                "files_changed",
                "files_added",
                "files_modified",
                "files_removed",
                "files_renamed",
                "files_copied",
                "files_type_changed",
                "text_files",
                "binary_files",
                "has_binary_files",
                "insertions",
                "deletions",
                "total_churn",
            )
        }
        if self.record_digest != _digest(content):
            raise ValueError("record_digest must identify canonical statistics")
        object.__setattr__(self, "file_statistics", records)

    def to_dict(self) -> dict[str, object]:
        return _thaw(self)  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class QtDiffStatisticsExtractionResult:
    specification: QtDiffStatisticsSpecification
    source_diff_artifact: ScientificArtifactReference
    commit_statistics: tuple[QtCommitDiffStatistics, ...]
    extraction_artifact: ScientificArtifactReference
    commit_count: int
    files_changed: int
    insertions: int
    deletions: int
    total_churn: int
    binary_files: int
    statistics_identity_digest: str
    metadata: Mapping[str, object] = field(default_factory=lambda: _EMPTY)

    def __post_init__(self) -> None:
        if not isinstance(self.specification, QtDiffStatisticsSpecification):
            raise TypeError("specification must be QtDiffStatisticsSpecification")
        if (
            self.source_diff_artifact.artifact_role
            is not ScientificArtifactRole.DIFF_ARTIFACT
        ):
            raise ValueError("source_diff_artifact must have diff-artifact role")
        if (
            self.source_diff_artifact.content_digest
            != self.specification.diff_artifact_digest
        ):
            raise ValueError("source diff artifact identity is inconsistent")
        records = tuple(self.commit_statistics)
        totals = (
            len(records),
            sum(item.files_changed for item in records),
            sum(item.insertions for item in records),
            sum(item.deletions for item in records),
            sum(item.total_churn for item in records),
            sum(item.binary_files for item in records),
        )
        if totals != (
            self.commit_count,
            self.files_changed,
            self.insertions,
            self.deletions,
            self.total_churn,
            self.binary_files,
        ):
            raise ValueError("result aggregate statistics are inconsistent")
        content = {
            "repository_revision": self.specification.repository_revision,
            "source_diff_artifact_digest": self.source_diff_artifact.content_digest,
            "extraction_policy_version": self.specification.extraction_policy_version,
            "policies": {name: getattr(self.specification, name) for name in _POLICIES},
            "commit_statistics": records,
        }
        content_digest = _digest(content)
        expected_path = (
            f"artifacts/qtbase/diff-statistics/{self.specification.repository_revision}/"
            "qt-diff-statistics.jsonl"
        )
        if (
            self.extraction_artifact.artifact_role
            is not ScientificArtifactRole.DIFF_ARTIFACT
            or self.extraction_artifact.repository_relative_path != expected_path
            or self.extraction_artifact.record_count != totals[1]
            or self.extraction_artifact.content_digest != content_digest
        ):
            raise ValueError("statistics artifact identity is inconsistent")
        identity = _digest(
            {
                "artifact_content_digest": content_digest,
                "source_diff_artifact_digest": self.source_diff_artifact.content_digest,
                "repository_revision": self.specification.repository_revision,
                "extraction_policy_version": (
                    self.specification.extraction_policy_version
                ),
            }
        )
        if self.statistics_identity_digest != identity:
            raise ValueError("statistics_identity_digest is inconsistent")
        object.__setattr__(self, "commit_statistics", records)
        object.__setattr__(self, "metadata", _freeze(self.metadata))

    def to_dict(self) -> dict[str, object]:
        return _thaw(self)  # type: ignore[return-value]


class QtDiffStatisticsExtractor:
    """Collect structural counts only from a validated immutable diff artifact."""

    extractor_name = "qt-diff-statistics-extractor"

    def extract(
        self,
        specification: QtDiffStatisticsSpecification,
        diff_extraction_result: QtDiffExtractionResult,
    ) -> QtDiffStatisticsExtractionResult:
        if not isinstance(specification, QtDiffStatisticsSpecification):
            raise TypeError("specification must be QtDiffStatisticsSpecification")
        if not isinstance(diff_extraction_result, QtDiffExtractionResult):
            raise TypeError("diff_extraction_result must be QtDiffExtractionResult")
        snapshot = diff_extraction_result.repository_snapshot
        if (
            specification.repository_name,
            specification.canonical_repository_url,
            specification.repository_revision,
            specification.diff_artifact_digest,
        ) != (
            snapshot.repository_name,
            snapshot.repository_url,
            snapshot.repository_revision,
            diff_extraction_result.extraction_artifact.content_digest,
        ):
            raise ValueError("specification and immutable diff artifact do not agree")
        records = tuple(
            self._statistics(item.commit_identifier, item.file_changes)
            for item in diff_extraction_result.commit_diffs
        )
        content = {
            "repository_revision": specification.repository_revision,
            "source_diff_artifact_digest": specification.diff_artifact_digest,
            "extraction_policy_version": specification.extraction_policy_version,
            "policies": {name: getattr(specification, name) for name in _POLICIES},
            "commit_statistics": records,
        }
        content_digest = _digest(content)
        file_count = sum(item.files_changed for item in records)
        artifact = ScientificArtifactReference(
            artifact_name="qtbase-diff-statistics",
            artifact_role=ScientificArtifactRole.DIFF_ARTIFACT,
            repository_relative_path=(
                f"artifacts/qtbase/diff-statistics/{specification.repository_revision}/qt-diff-statistics.jsonl"
            ),
            content_digest=content_digest,
            schema_version=specification.extraction_policy_version,
            record_count=file_count,
            metadata={"record_count_policy": "file-statistic-records"},
        )
        identity = _digest(
            {
                "artifact_content_digest": content_digest,
                "source_diff_artifact_digest": specification.diff_artifact_digest,
                "repository_revision": specification.repository_revision,
                "extraction_policy_version": specification.extraction_policy_version,
            }
        )
        return QtDiffStatisticsExtractionResult(
            specification,
            diff_extraction_result.extraction_artifact,
            records,
            artifact,
            len(records),
            file_count,
            sum(item.insertions for item in records),
            sum(item.deletions for item in records),
            sum(item.total_churn for item in records),
            sum(item.binary_files for item in records),
            identity,
        )

    @staticmethod
    def _statistics(
        commit: str, changes: tuple[QtFileChangeRecord, ...]
    ) -> QtCommitDiffStatistics:
        files = tuple(
            QtFileDiffStatistics(
                item.commit_identifier,
                item.change_type,
                item.old_path,
                item.new_path,
                item.path,
                item.is_binary,
                item.additions,
                item.deletions,
                None
                if item.is_binary
                else (item.additions or 0) + (item.deletions or 0),
            )
            for item in changes
        )
        counts = {
            kind: sum(item.change_type == kind for item in files) for kind in _KINDS
        }
        insertions = sum(item.insertions or 0 for item in files)
        deletions = sum(item.deletions or 0 for item in files)
        values: dict[str, object] = {
            "commit_identifier": commit,
            "file_statistics": files,
            "files_changed": len(files),
            "files_added": counts["added"],
            "files_modified": counts["modified"],
            "files_removed": counts["deleted"],
            "files_renamed": counts["renamed"],
            "files_copied": counts["copied"],
            "files_type_changed": counts["type-changed"],
            "text_files": sum(not item.is_binary for item in files),
            "binary_files": sum(item.is_binary for item in files),
            "has_binary_files": any(item.is_binary for item in files),
            "insertions": insertions,
            "deletions": deletions,
            "total_churn": insertions + deletions,
        }
        return QtCommitDiffStatistics(**values, record_digest=_digest(values))  # type: ignore[arg-type]
