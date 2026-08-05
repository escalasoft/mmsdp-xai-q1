"""Deterministic file-level diff extraction from one immutable Qt snapshot."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path, PurePosixPath
from types import MappingProxyType

from dataset.scientific_builder_contracts import (
    ScientificArtifactReference,
    ScientificArtifactRole,
    ScientificRepositorySnapshot,
)
from extraction.qt_commit_extraction import QtCommitExtractionResult

__all__ = [
    "QtDiffExtractionSpecification",
    "QtFileChangeRecord",
    "QtCommitDiffRecord",
    "QtDiffExtractionResult",
    "QtDiffExtractor",
]

_NAME = "qtbase"
_URL = "https://code.qt.io/qt/qtbase.git"
_PLACEHOLDER_REVISION = "revision-required-before-execution"
_PLACEHOLDER_DIGEST = "commit-artifact-digest-required-before-execution"
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_OBJECT_ID = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
_MODES = {"000000", "040000", "100644", "100755", "120000", "160000"}
_CHANGE_TYPES = {"added", "modified", "deleted", "renamed", "copied", "type-changed"}
_STATUS = {
    "A": "added",
    "M": "modified",
    "D": "deleted",
    "R": "renamed",
    "C": "copied",
    "T": "type-changed",
}
_POLICIES = {
    "ordering_policy": "commit-artifact-order",
    "merge_commit_policy": "first-parent-baseline",
    "root_commit_policy": "empty-tree-baseline",
    "rename_detection_policy": "git-native-renames",
    "binary_file_policy": "metadata-only",
    "path_normalization_policy": "repository-relative-posix",
}
_BANNED_KEYS = {
    "bug_confidence",
    "clone_date",
    "created_at",
    "credentials",
    "duration",
    "environment",
    "hostname",
    "issue",
    "issue_link",
    "label",
    "local_path",
    "machine_name",
    "password",
    "runtime_timestamp",
    "target",
    "timestamp",
    "token",
    "username",
}
_OBJECT_REPR = re.compile(r"<[^>]*(?:object at )?0x[0-9a-fA-F]+>")
_EVIDENCE = re.compile(
    r"git:(?:cat-file|config|diff|hash-object|rev-parse):completed\Z"
)
_EMPTY: Mapping[str, object] = MappingProxyType({})
_RENAME_SIMILARITY = 50
_TIMEOUT_SECONDS = 120
_PROJECT_ROOT = Path(__file__).resolve().parents[2]


class _QtDiffExtractionError(RuntimeError):
    """Sanitized failure of diff extraction."""


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def _freeze(value: object, path: str = "metadata") -> object:
    if isinstance(value, Mapping):
        frozen: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(f"{path} keys must be strings")
            normalized = _key(key)
            if normalized in _BANNED_KEYS or any(
                word in normalized
                for word in (
                    "bug_confidence",
                    "credential",
                    "hostname",
                    "issue",
                    "label",
                    "password",
                    "target",
                    "username",
                )
            ):
                raise ValueError(f"{path} contains forbidden field {key!r}")
            frozen[key] = _freeze(item, f"{path}.{key}")
        return MappingProxyType(frozen)
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item, path) for item in value)
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{path} contains a non-finite number")
    if value is None or type(value) in {bool, int, float}:
        return value
    if isinstance(value, str):
        if Path(value).is_absolute() or _OBJECT_REPR.search(value):
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


def _identifier(value: object, name: str, length: int | None = None) -> str:
    text = _text(value, name)
    if not _OBJECT_ID.fullmatch(text) or (length is not None and len(text) != length):
        raise ValueError(f"{name} must be a complete lowercase Git object identifier")
    return text


def _path(value: object, name: str, *, optional: bool = False) -> str | None:
    if value is None and optional:
        return None
    text = _text(value, name)
    pure = PurePosixPath(text)
    if (
        pure.is_absolute()
        or "\\" in text
        or ".." in pure.parts
        or str(pure) != text
        or text == "."
    ):
        raise ValueError(f"{name} must be a normalized repository-relative POSIX path")
    return text


def _count(value: object, name: str, *, nullable: bool = False) -> int | None:
    if value is None and nullable:
        return None
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


@dataclass(frozen=True, slots=True)
class QtDiffExtractionSpecification:
    repository_name: str
    canonical_repository_url: str
    repository_revision: str
    commit_artifact_digest: str
    extraction_policy_version: str
    ordering_policy: str = _POLICIES["ordering_policy"]
    merge_commit_policy: str = _POLICIES["merge_commit_policy"]
    root_commit_policy: str = _POLICIES["root_commit_policy"]
    rename_detection_policy: str = _POLICIES["rename_detection_policy"]
    binary_file_policy: str = _POLICIES["binary_file_policy"]
    path_normalization_policy: str = _POLICIES["path_normalization_policy"]
    allowed_hash_algorithms: tuple[str, ...] = ("sha1", "sha256")
    metadata: Mapping[str, object] = field(default_factory=lambda: _EMPTY)

    def __post_init__(self) -> None:
        if self.repository_name != _NAME:
            raise ValueError("repository_name must equal 'qtbase'")
        if self.canonical_repository_url != _URL:
            raise ValueError(f"canonical_repository_url must equal {_URL!r}")
        revision = _text(self.repository_revision, "repository_revision")
        if revision != _PLACEHOLDER_REVISION:
            _identifier(revision, "repository_revision")
        artifact_digest = _text(self.commit_artifact_digest, "commit_artifact_digest")
        if artifact_digest != _PLACEHOLDER_DIGEST and not _SHA256.fullmatch(
            artifact_digest
        ):
            raise ValueError(
                "commit_artifact_digest must be a lowercase SHA-256 digest"
            )
        for name, expected in _POLICIES.items():
            if getattr(self, name) != expected:
                raise ValueError(f"{name} must equal {expected!r}")
        algorithms = tuple(sorted(self.allowed_hash_algorithms))
        if algorithms != ("sha1", "sha256"):
            raise ValueError(
                "allowed_hash_algorithms must contain exactly sha1 and sha256"
            )
        object.__setattr__(
            self,
            "extraction_policy_version",
            _text(self.extraction_policy_version, "extraction_policy_version"),
        )
        object.__setattr__(self, "allowed_hash_algorithms", algorithms)
        object.__setattr__(self, "metadata", _freeze(self.metadata))

    def to_dict(self) -> dict[str, object]:
        return _thaw(self)  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class QtFileChangeRecord:
    commit_identifier: str
    change_type: str
    old_path: str | None
    new_path: str | None
    path: str
    is_binary: bool
    additions: int | None
    deletions: int | None
    old_blob_identifier: str | None
    new_blob_identifier: str | None
    old_file_mode: str | None
    new_file_mode: str | None
    similarity_percent: int | None
    metadata: Mapping[str, object] = field(default_factory=lambda: _EMPTY)

    def __post_init__(self) -> None:
        commit = _identifier(self.commit_identifier, "commit_identifier")
        if self.change_type not in _CHANGE_TYPES:
            raise ValueError("change_type is not supported")
        old = _path(self.old_path, "old_path", optional=True)
        new = _path(self.new_path, "new_path", optional=True)
        canonical = _path(self.path, "path")
        if self.change_type == "added" and (old is not None or new is None):
            raise ValueError("added files require only new_path")
        if self.change_type == "deleted" and (old is None or new is not None):
            raise ValueError("deleted files require only old_path")
        if self.change_type in {"modified", "type-changed"} and (
            old is None or old != new
        ):
            raise ValueError(
                f"{self.change_type} files require equal old and new paths"
            )
        if self.change_type in {"renamed", "copied"} and (
            old is None or new is None or old == new
        ):
            raise ValueError(
                f"{self.change_type} files require distinct old and new paths"
            )
        expected_path = old if self.change_type == "deleted" else new
        if canonical != expected_path:
            raise ValueError("path must be the canonical current path")
        if type(self.is_binary) is not bool:
            raise TypeError("is_binary must be bool")
        additions = _count(self.additions, "additions", nullable=self.is_binary)
        deletions = _count(self.deletions, "deletions", nullable=self.is_binary)
        if not self.is_binary and (additions is None or deletions is None):
            raise ValueError("text files require line counts")
        length = len(commit)
        for name in ("old_blob_identifier", "new_blob_identifier"):
            value = getattr(self, name)
            if value is not None:
                _identifier(value, name, length)
        for name in ("old_file_mode", "new_file_mode"):
            value = getattr(self, name)
            if value is not None and value not in _MODES:
                raise ValueError(f"{name} has invalid Git mode syntax")
        similarity = self.similarity_percent
        if self.change_type in {"renamed", "copied"}:
            if type(similarity) is not int or not 0 <= similarity <= 100:
                raise ValueError(
                    "rename/copy similarity must be an integer from 0 to 100"
                )
        elif similarity is not None:
            raise ValueError("similarity_percent is only valid for rename/copy records")
        object.__setattr__(self, "metadata", _freeze(self.metadata))

    def to_dict(self) -> dict[str, object]:
        return _thaw(self)  # type: ignore[return-value]


def _file_order(record: QtFileChangeRecord) -> tuple[str, ...]:
    return (
        record.path,
        record.change_type,
        record.old_path or "",
        record.new_path or "",
        record.old_blob_identifier or "",
        record.new_blob_identifier or "",
    )


def _record_content(
    commit: str,
    baseline: str,
    parents: tuple[str, ...],
    root: bool,
    merge: bool,
    changes: tuple[QtFileChangeRecord, ...],
) -> dict[str, object]:
    return {
        "commit_identifier": commit,
        "baseline_identifier": baseline,
        "parent_identifiers": parents,
        "is_root_commit": root,
        "is_merge_commit": merge,
        "file_changes": changes,
    }


@dataclass(frozen=True, slots=True)
class QtCommitDiffRecord:
    commit_identifier: str
    baseline_identifier: str
    parent_identifiers: tuple[str, ...]
    is_root_commit: bool
    is_merge_commit: bool
    file_changes: tuple[QtFileChangeRecord, ...]
    changed_file_count: int
    text_file_count: int
    binary_file_count: int
    total_additions: int
    total_deletions: int
    record_digest: str
    metadata: Mapping[str, object] = field(default_factory=lambda: _EMPTY)

    def __post_init__(self) -> None:
        commit = _identifier(self.commit_identifier, "commit_identifier")
        parents = tuple(self.parent_identifiers)
        if any(
            not _OBJECT_ID.fullmatch(parent) or len(parent) != len(commit)
            for parent in parents
        ):
            raise ValueError(
                "parent_identifiers must be complete matching Git identifiers"
            )
        baseline = _identifier(
            self.baseline_identifier, "baseline_identifier", len(commit)
        )
        if type(self.is_root_commit) is not bool or self.is_root_commit != (
            not parents
        ):
            raise ValueError("is_root_commit must agree with parent_identifiers")
        if type(self.is_merge_commit) is not bool or self.is_merge_commit != (
            len(parents) > 1
        ):
            raise ValueError("is_merge_commit must agree with parent_identifiers")
        if parents and baseline != parents[0]:
            raise ValueError("baseline_identifier must equal the first parent")
        changes = tuple(self.file_changes)
        if any(
            not isinstance(change, QtFileChangeRecord)
            or change.commit_identifier != commit
            for change in changes
        ):
            raise TypeError(
                "file_changes must contain matching QtFileChangeRecord values"
            )
        if changes != tuple(sorted(changes, key=_file_order)):
            raise ValueError("file_changes must use canonical deterministic ordering")
        identities = [
            (change.change_type, change.old_path, change.new_path) for change in changes
        ]
        if len(identities) != len(set(identities)):
            raise ValueError("duplicate canonical file-change identity")
        text = sum(not change.is_binary for change in changes)
        binary = len(changes) - text
        expected = (
            len(changes),
            text,
            binary,
            sum(change.additions or 0 for change in changes if not change.is_binary),
            sum(change.deletions or 0 for change in changes if not change.is_binary),
        )
        actual = (
            self.changed_file_count,
            self.text_file_count,
            self.binary_file_count,
            self.total_additions,
            self.total_deletions,
        )
        if actual != expected or any(type(item) is not int for item in actual):
            raise ValueError("commit diff aggregate counts are inconsistent")
        content = _record_content(
            commit,
            baseline,
            parents,
            self.is_root_commit,
            self.is_merge_commit,
            changes,
        )
        if self.record_digest != _digest(content):
            raise ValueError("record_digest must identify canonical scientific content")
        object.__setattr__(self, "parent_identifiers", parents)
        object.__setattr__(self, "file_changes", changes)
        object.__setattr__(self, "metadata", _freeze(self.metadata))

    def to_dict(self) -> dict[str, object]:
        return _thaw(self)  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class QtDiffExtractionResult:
    specification: QtDiffExtractionSpecification
    repository_snapshot: ScientificRepositorySnapshot
    commit_extraction_result: QtCommitExtractionResult
    commit_diffs: tuple[QtCommitDiffRecord, ...]
    extraction_artifact: ScientificArtifactReference
    extracted_commit_count: int
    extracted_file_change_count: int
    empty_diff_commit_count: int
    root_commit_count: int
    merge_commit_count: int
    diff_identity_digest: str
    command_evidence: tuple[str, ...]
    metadata: Mapping[str, object] = field(default_factory=lambda: _EMPTY)

    def __post_init__(self) -> None:
        if not isinstance(self.specification, QtDiffExtractionSpecification):
            raise TypeError("specification must be QtDiffExtractionSpecification")
        if not isinstance(self.repository_snapshot, ScientificRepositorySnapshot):
            raise TypeError("repository_snapshot must be ScientificRepositorySnapshot")
        if not isinstance(self.commit_extraction_result, QtCommitExtractionResult):
            raise TypeError("commit_extraction_result must be QtCommitExtractionResult")
        spec, snapshot, commits = (
            self.specification,
            self.repository_snapshot,
            self.commit_extraction_result,
        )
        if (
            snapshot.repository_name,
            snapshot.repository_url,
            snapshot.repository_revision,
        ) != (
            spec.repository_name,
            spec.canonical_repository_url,
            spec.repository_revision,
        ):
            raise ValueError("repository scientific identities do not agree")
        if (
            commits.source_revision != snapshot.repository_revision
            or commits.source_snapshot_digest != snapshot.snapshot_digest
            or commits.artifact.content_digest != spec.commit_artifact_digest
        ):
            raise ValueError(
                "commit extraction identity does not agree with the snapshot"
            )
        diffs = tuple(self.commit_diffs)
        if tuple(item.commit_identifier for item in diffs) != tuple(
            item.commit_id for item in commits.records
        ):
            raise ValueError("commit_diffs must exactly preserve commit artifact order")
        counts = (
            len(diffs),
            sum(item.changed_file_count for item in diffs),
            sum(item.changed_file_count == 0 for item in diffs),
            sum(item.is_root_commit for item in diffs),
            sum(item.is_merge_commit for item in diffs),
        )
        if counts != (
            self.extracted_commit_count,
            self.extracted_file_change_count,
            self.empty_diff_commit_count,
            self.root_commit_count,
            self.merge_commit_count,
        ):
            raise ValueError("result aggregate counts are inconsistent")
        content = {
            "repository_revision": snapshot.repository_revision,
            "source_snapshot_digest": snapshot.snapshot_digest,
            "commit_artifact_digest": commits.artifact.content_digest,
            "extraction_policy_version": spec.extraction_policy_version,
            "policies": {name: getattr(spec, name) for name in _POLICIES},
            "commit_diffs": diffs,
        }
        content_digest = _digest(content)
        artifact = self.extraction_artifact
        expected_path = (
            f"artifacts/qtbase/diffs/{snapshot.repository_revision}/"
            "qt-commit-diffs.jsonl"
        )
        if (
            artifact.artifact_role is not ScientificArtifactRole.DIFF_ARTIFACT
            or artifact.repository_relative_path != expected_path
            or artifact.record_count != counts[1]
            or artifact.content_digest != content_digest
        ):
            raise ValueError(
                "diff artifact identity or file-change record count is inconsistent"
            )
        identity = _digest(
            {
                "artifact_content_digest": content_digest,
                "repository_revision": snapshot.repository_revision,
                "commit_artifact_digest": commits.artifact.content_digest,
                "extraction_policy_version": spec.extraction_policy_version,
            }
        )
        if self.diff_identity_digest != identity:
            raise ValueError("diff_identity_digest is inconsistent")
        evidence = tuple(self.command_evidence)
        if (
            not evidence
            or evidence != tuple(sorted(set(evidence)))
            or any(not _EVIDENCE.fullmatch(item) for item in evidence)
        ):
            raise ValueError("command_evidence must be controlled, unique, and sorted")
        object.__setattr__(self, "commit_diffs", diffs)
        object.__setattr__(self, "command_evidence", evidence)
        object.__setattr__(self, "metadata", _freeze(self.metadata))

    def to_dict(self) -> dict[str, object]:
        return _thaw(self)  # type: ignore[return-value]


class _GitReader:
    def __init__(self, repository: Path) -> None:
        self.repository = repository
        self.evidence: set[str] = set()

    def run(
        self, operation: str, arguments: Sequence[str], *, input_text: str | None = None
    ) -> str:
        if operation not in {"cat-file", "config", "diff", "hash-object", "rev-parse"}:
            raise _QtDiffExtractionError("Git operation is not permitted")
        environment = {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_PAGER": "cat",
            "GIT_EXTERNAL_DIFF": "",
            "GIT_DIFF_OPTS": "",
            "HOME": os.devnull,
            "LANG": "C",
            "LC_ALL": "C",
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        }
        try:
            result = subprocess.run(
                [
                    "git",
                    "-c",
                    "color.ui=false",
                    "-c",
                    "diff.external=",
                    operation,
                    *arguments,
                ],
                cwd=self.repository,
                check=False,
                capture_output=True,
                text=True,
                input=input_text,
                encoding="utf-8",
                errors="surrogateescape",
                timeout=_TIMEOUT_SECONDS,
                env=environment,
                shell=False,
            )
        except (OSError, subprocess.TimeoutExpired, UnicodeError) as error:
            raise _QtDiffExtractionError(
                f"Git {operation} could not be read"
            ) from error
        if result.returncode:
            raise _QtDiffExtractionError(f"Git {operation} failed")
        self.evidence.add(f"git:{operation}:completed")
        return result.stdout


class QtDiffExtractor:
    """Extract raw file changes without constructing model features."""

    extractor_name = "qt-diff-extractor"

    def extract(
        self,
        specification: QtDiffExtractionSpecification,
        repository_path: str | Path,
        repository_snapshot: ScientificRepositorySnapshot,
        commit_extraction_result: QtCommitExtractionResult,
    ) -> QtDiffExtractionResult:
        if not isinstance(specification, QtDiffExtractionSpecification):
            raise TypeError("specification must be QtDiffExtractionSpecification")
        if not isinstance(repository_snapshot, ScientificRepositorySnapshot):
            raise TypeError("repository_snapshot must be ScientificRepositorySnapshot")
        if not isinstance(commit_extraction_result, QtCommitExtractionResult):
            raise TypeError("commit_extraction_result must be QtCommitExtractionResult")
        if (
            specification.repository_revision == _PLACEHOLDER_REVISION
            or specification.commit_artifact_digest == _PLACEHOLDER_DIGEST
        ):
            raise ValueError(
                "diff extraction placeholders must be resolved before execution"
            )
        repository = Path(repository_path).resolve()
        if not repository.is_dir():
            raise ValueError("repository_path must be an acquired Git repository")
        if repository == _PROJECT_ROOT or _PROJECT_ROOT in repository.parents:
            raise ValueError(
                "repository_path must lie outside the MMSDP-XAI repository"
            )
        reader = _GitReader(repository)
        if reader.run("rev-parse", ["--is-inside-work-tree"]).strip() != "true":
            raise _QtDiffExtractionError("repository is not a Git work tree")
        # The validated upstream artifact carries the object format. Complete object
        # names then provide an independent length check on older Git versions.
        algorithm = commit_extraction_result.object_hash_algorithm
        if algorithm not in specification.allowed_hash_algorithms or len(
            repository_snapshot.repository_revision
        ) != (40 if algorithm == "sha1" else 64):
            raise _QtDiffExtractionError(
                "repository object format does not match snapshot"
            )
        revision = reader.run(
            "rev-parse",
            ["--verify", f"{repository_snapshot.repository_revision}^{{commit}}"],
        ).strip()
        if revision != repository_snapshot.repository_revision:
            raise _QtDiffExtractionError("repository revision does not match snapshot")
        if reader.run("cat-file", ["-t", revision]).strip() != "commit":
            raise _QtDiffExtractionError("repository revision is not a commit")
        # Validate all cross-stage identities before per-commit subprocess calls.
        if (
            (
                specification.repository_name,
                specification.canonical_repository_url,
                specification.repository_revision,
                specification.commit_artifact_digest,
            )
            != (
                repository_snapshot.repository_name,
                repository_snapshot.repository_url,
                repository_snapshot.repository_revision,
                commit_extraction_result.artifact.content_digest,
            )
            or commit_extraction_result.source_revision != revision
            or commit_extraction_result.source_snapshot_digest
            != repository_snapshot.snapshot_digest
            or commit_extraction_result.object_hash_algorithm != algorithm
        ):
            raise ValueError(
                "snapshot, specification, and commit artifact do not agree"
            )
        empty_tree = reader.run(
            "hash-object", ["-t", "tree", "--stdin"], input_text=""
        ).strip()
        diffs = tuple(
            self._extract_commit(
                reader, record.commit_id, record.parent_ids, empty_tree, algorithm
            )
            for record in commit_extraction_result.records
        )
        content = {
            "repository_revision": revision,
            "source_snapshot_digest": repository_snapshot.snapshot_digest,
            "commit_artifact_digest": commit_extraction_result.artifact.content_digest,
            "extraction_policy_version": specification.extraction_policy_version,
            "policies": {name: getattr(specification, name) for name in _POLICIES},
            "commit_diffs": diffs,
        }
        content_digest = _digest(content)
        file_count = sum(item.changed_file_count for item in diffs)
        artifact = ScientificArtifactReference(
            artifact_name="qtbase-commit-diffs",
            artifact_role=ScientificArtifactRole.DIFF_ARTIFACT,
            repository_relative_path=f"artifacts/qtbase/diffs/{revision}/qt-commit-diffs.jsonl",
            content_digest=content_digest,
            schema_version=specification.extraction_policy_version,
            record_count=file_count,
            metadata={
                "record_count_policy": "file-change-records",
                "rename_similarity_threshold_percent": _RENAME_SIMILARITY,
            },
        )
        identity = _digest(
            {
                "artifact_content_digest": content_digest,
                "repository_revision": revision,
                "commit_artifact_digest": (
                    commit_extraction_result.artifact.content_digest
                ),
                "extraction_policy_version": specification.extraction_policy_version,
            }
        )
        return QtDiffExtractionResult(
            specification,
            repository_snapshot,
            commit_extraction_result,
            diffs,
            artifact,
            len(diffs),
            file_count,
            sum(item.changed_file_count == 0 for item in diffs),
            sum(item.is_root_commit for item in diffs),
            sum(item.is_merge_commit for item in diffs),
            identity,
            tuple(sorted(reader.evidence)),
        )

    @staticmethod
    def _extract_commit(
        reader: _GitReader,
        commit: str,
        parents: tuple[str, ...],
        empty_tree: str,
        algorithm: str,
    ) -> QtCommitDiffRecord:
        if reader.run("cat-file", ["-t", commit]).strip() != "commit":
            raise _QtDiffExtractionError(
                "commit artifact references a non-commit object"
            )
        baseline = parents[0] if parents else empty_tree
        common = [
            "--no-ext-diff",
            "--no-textconv",
            f"--find-renames={_RENAME_SIMILARITY}%",
            f"--find-copies={_RENAME_SIMILARITY}%",
        ]
        raw = reader.run(
            "diff", [*common, "--raw", "-z", "--no-abbrev", baseline, commit, "--"]
        )
        numstat = reader.run(
            "diff", [*common, "--numstat", "-z", baseline, commit, "--"]
        )
        stats = QtDiffExtractor._parse_numstat(numstat)
        changes = QtDiffExtractor._parse_raw(raw, stats, commit, algorithm)
        changes = tuple(sorted(changes, key=_file_order))
        root, merge = not parents, len(parents) > 1
        digest = _digest(
            _record_content(commit, baseline, parents, root, merge, changes)
        )
        return QtCommitDiffRecord(
            commit,
            baseline,
            parents,
            root,
            merge,
            changes,
            len(changes),
            sum(not item.is_binary for item in changes),
            sum(item.is_binary for item in changes),
            sum(item.additions or 0 for item in changes if not item.is_binary),
            sum(item.deletions or 0 for item in changes if not item.is_binary),
            digest,
            {
                "baseline_policy": "empty-tree-baseline"
                if root
                else "first-parent-baseline"
            },
        )

    @staticmethod
    def _parse_numstat(
        value: str,
    ) -> dict[tuple[str | None, str | None], tuple[bool, int | None, int | None]]:
        parts = value.split("\0")
        result = {}
        index = 0
        while index < len(parts) and parts[index]:
            header = parts[index]
            index += 1
            added, deleted, path = header.split("\t", 2)
            if path:
                old, new = path, path
            else:
                old, new = parts[index], parts[index + 1]
                index += 2
            binary = added == "-" or deleted == "-"
            result[(old, new)] = (
                binary,
                None if binary else int(added),
                None if binary else int(deleted),
            )
        return result

    @staticmethod
    def _parse_raw(
        value: str,
        stats: Mapping[
            tuple[str | None, str | None], tuple[bool, int | None, int | None]
        ],
        commit: str,
        algorithm: str,
    ) -> tuple[QtFileChangeRecord, ...]:
        parts = value.split("\0")
        changes = []
        index = 0
        length = 40 if algorithm == "sha1" else 64
        zero = "0" * length
        while index < len(parts) and parts[index]:
            header = parts[index]
            index += 1
            fields_ = header.split()
            if len(fields_) != 5 or not fields_[0].startswith(":"):
                raise _QtDiffExtractionError("Git raw diff output is malformed")
            old_mode, new_mode, old_blob, new_blob, status = (
                fields_[0][1:],
                fields_[1],
                fields_[2],
                fields_[3],
                fields_[4],
            )
            code = status[0]
            if code not in _STATUS:
                raise _QtDiffExtractionError("Git emitted an unsupported change type")
            first_path = parts[index]
            index += 1
            if code in {"R", "C"}:
                old_path, new_path = first_path, parts[index]
                index += 1
                similarity = int(status[1:])
            elif code == "A":
                old_path, new_path, similarity = None, first_path, None
            elif code == "D":
                old_path, new_path, similarity = first_path, None, None
            else:
                old_path = new_path = first_path
                similarity = None
            key = (old_path or new_path, new_path or old_path)
            stat = stats.get(key)
            if stat is None:
                raise _QtDiffExtractionError("Git diff status and line counts disagree")
            changes.append(
                QtFileChangeRecord(
                    commit,
                    _STATUS[code],
                    old_path,
                    new_path,
                    new_path or old_path or "",
                    stat[0],
                    stat[1],
                    stat[2],
                    None if old_blob == zero else old_blob,
                    None if new_blob == zero else new_blob,
                    None if old_mode == "000000" else old_mode,
                    None if new_mode == "000000" else new_mode,
                    similarity,
                )
            )
        return tuple(changes)
