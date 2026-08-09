"""Deterministic commit-only extraction from an acquired Qt snapshot."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, fields, is_dataclass
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from types import MappingProxyType

from dataset.scientific_builder_contracts import (
    ScientificArtifactReference,
    ScientificArtifactRole,
)
from extraction.qt_repository_acquisition import QtRepositoryAcquisitionResult

__all__ = [
    "QtCommitExtractionSpecification",
    "ScientificCommitRecord",
    "QtCommitExtractionResult",
    "QtCommitExtractor",
]

_ORDERING_POLICY = "topological-oldest-first-v1"
_EMPTY: Mapping[str, object] = MappingProxyType({})
_OBJECT_IDS = {
    "sha1": re.compile(r"[0-9a-f]{40}\Z"),
    "sha256": re.compile(r"[0-9a-f]{64}\Z"),
}
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_IDENTITY = re.compile(r"^(.*) <([^<>]*)> (-?\d+) ([+-])(\d{2})(\d{2})$")
_EVIDENCE = re.compile(r"git:(?:cat-file|rev-list|rev-parse):completed\Z")


class QtCommitExtractionError(RuntimeError):
    """A sanitized failure of the scientific commit-extraction stage."""


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
            result[key] = _freeze(item, f"{path}.{key}")
        return MappingProxyType(result)
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item, path) for item in value)
    if value is None or type(value) in {bool, int, float}:
        return value
    if isinstance(value, str):
        if Path(value).is_absolute():
            raise ValueError(f"{path} must not contain absolute local paths")
        return value
    raise TypeError(f"{path} must contain JSON-compatible values")


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


@dataclass(frozen=True, slots=True)
class QtCommitExtractionSpecification:
    """Immutable scientific policy for the commit-only artifact."""

    schema_version: str
    artifact_repository_relative_path: str = "artifacts/raw/qtbase-commits.json"
    ordering_policy: str = _ORDERING_POLICY
    observation_window_start: str = "2011-06-18T00:00:00+00:00"
    observation_window_end: str = "2014-03-18T23:59:59+00:00"
    metadata: Mapping[str, object] = field(default_factory=lambda: _EMPTY)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )
        path = _text(
            self.artifact_repository_relative_path,
            "artifact_repository_relative_path",
        )
        pure = PurePosixPath(path)
        if (
            pure.is_absolute()
            or ".." in pure.parts
            or str(pure) != path
            or "\\" in path
        ):
            raise ValueError("artifact path must be normalized and repository-relative")
        if self.ordering_policy != _ORDERING_POLICY:
            raise ValueError(f"ordering_policy must equal {_ORDERING_POLICY!r}")
        boundaries = []
        for name in ("observation_window_start", "observation_window_end"):
            value = _text(getattr(self, name), name)
            try:
                timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError as error:
                raise ValueError(f"{name} must be an ISO-8601 timestamp") from error
            if timestamp.tzinfo is None or timestamp.utcoffset() is None:
                raise ValueError(f"{name} must include a UTC offset")
            normalized = timestamp.astimezone(UTC).isoformat()
            object.__setattr__(self, name, normalized)
            boundaries.append(timestamp.astimezone(UTC))
        if boundaries[0] > boundaries[1]:
            raise ValueError("observation window start must not follow end")
        object.__setattr__(self, "artifact_repository_relative_path", path)
        object.__setattr__(self, "metadata", _freeze(self.metadata))

    def to_dict(self) -> dict[str, object]:
        return _thaw(self)  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class ScientificCommitRecord:
    """One untransformed Git commit, identified by its complete object name."""

    commit_id: str
    parent_ids: tuple[str, ...]
    author_name: str
    author_email: str
    authored_at: str
    committer_name: str
    committer_email: str
    committed_at: str
    message: str

    def __post_init__(self) -> None:
        identifier = _text(self.commit_id, "commit_id")
        identifier_pattern = (
            _OBJECT_IDS["sha1"] if len(identifier) == 40 else _OBJECT_IDS["sha256"]
        )
        if not identifier_pattern.fullmatch(identifier):
            raise ValueError("commit_id must be a complete Git object identifier")
        parents = tuple(self.parent_ids)
        if any(
            not isinstance(parent, str) or not identifier_pattern.fullmatch(parent)
            for parent in parents
        ):
            raise ValueError("parent_ids must be complete matching Git identifiers")
        for name in (
            "author_name",
            "author_email",
            "authored_at",
            "committer_name",
            "committer_email",
            "committed_at",
            "message",
        ):
            if not isinstance(getattr(self, name), str):
                raise TypeError(f"{name} must be a string")
        for name in ("authored_at", "committed_at"):
            try:
                timestamp = datetime.fromisoformat(getattr(self, name))
            except ValueError as error:
                raise ValueError(f"{name} must be an ISO-8601 timestamp") from error
            if timestamp.tzinfo is None or timestamp.utcoffset() is None:
                raise ValueError(f"{name} must include a UTC offset")
        object.__setattr__(self, "commit_id", identifier)
        object.__setattr__(self, "parent_ids", parents)

    def to_dict(self) -> dict[str, object]:
        return _thaw(self)  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class QtCommitExtractionResult:
    """Immutable scientific contract for one completed commit artifact."""

    specification: QtCommitExtractionSpecification
    source_revision: str
    source_snapshot_digest: str
    object_hash_algorithm: str
    records: tuple[ScientificCommitRecord, ...]
    artifact: ScientificArtifactReference
    ordering_policy: str
    command_evidence: tuple[str, ...]
    reachable_historical_commit_count: int
    pre_window_historical_commit_count: int
    reachable_history_digest: str

    def __post_init__(self) -> None:
        if not isinstance(self.specification, QtCommitExtractionSpecification):
            raise TypeError("specification must be QtCommitExtractionSpecification")
        pattern = _OBJECT_IDS.get(self.object_hash_algorithm)
        if pattern is None or not pattern.fullmatch(self.source_revision):
            raise ValueError("source_revision must be a complete Git object identifier")
        records = tuple(self.records)
        if any(not isinstance(record, ScientificCommitRecord) for record in records):
            raise TypeError("records must contain ScientificCommitRecord values")
        seen: set[str] = set()
        window_start = datetime.fromisoformat(
            self.specification.observation_window_start
        )
        window_end = datetime.fromisoformat(self.specification.observation_window_end)
        for record in records:
            if not pattern.fullmatch(record.commit_id):
                raise ValueError(
                    "commit_id must preserve the complete object identifier"
                )
            if record.commit_id in seen:
                raise ValueError("commit identifiers must be unique")
            if any(not pattern.fullmatch(parent) for parent in record.parent_ids):
                raise ValueError("parent_ids must preserve complete object identifiers")
            committed = datetime.fromisoformat(record.committed_at).astimezone(UTC)
            if not window_start <= committed <= window_end:
                raise ValueError("commit record lies outside the observation window")
            seen.add(record.commit_id)
        if self.ordering_policy != self.specification.ordering_policy:
            raise ValueError("result ordering policy must equal its specification")
        if self.artifact.artifact_role is not ScientificArtifactRole.COMMIT_ARTIFACT:
            raise ValueError("artifact must have commit-artifact role")
        if not _SHA256.fullmatch(self.source_snapshot_digest):
            raise ValueError("source_snapshot_digest must be a SHA-256 digest")
        if (
            self.artifact.repository_relative_path
            != self.specification.artifact_repository_relative_path
            or self.artifact.schema_version != self.specification.schema_version
        ):
            raise ValueError(
                "artifact identity must equal the extraction specification"
            )
        if self.artifact.record_count != len(records):
            raise ValueError("artifact record count must equal extracted records")
        if (
            type(self.reachable_historical_commit_count) is not int
            or type(self.pre_window_historical_commit_count) is not int
            or self.reachable_historical_commit_count < len(records)
            or self.pre_window_historical_commit_count < 0
            or self.pre_window_historical_commit_count
            != self.reachable_historical_commit_count - len(records)
        ):
            raise ValueError("historical and observation-window counts disagree")
        if not _SHA256.fullmatch(self.reachable_history_digest):
            raise ValueError("reachable_history_digest must be a SHA-256 digest")
        expected_content = _canonical_bytes(
            {
                "schema_version": self.specification.schema_version,
                "artifact_role": ScientificArtifactRole.COMMIT_ARTIFACT.value,
                "source_repository": "qtbase",
                "source_revision": self.source_revision,
                "source_snapshot_digest": self.source_snapshot_digest,
                "object_hash_algorithm": self.object_hash_algorithm,
                "ordering_policy": self.ordering_policy,
                "observation_window_start": self.specification.observation_window_start,
                "observation_window_end": self.specification.observation_window_end,
                "reachable_historical_commit_count": (
                    self.reachable_historical_commit_count
                ),
                "pre_window_historical_commit_count": (
                    self.pre_window_historical_commit_count
                ),
                "reachable_history_digest": self.reachable_history_digest,
                "records": records,
            }
        )
        if self.artifact.content_digest != hashlib.sha256(expected_content).hexdigest():
            raise ValueError(
                "artifact digest must identify the canonical commit payload"
            )
        evidence = tuple(self.command_evidence)
        if evidence != tuple(sorted(set(evidence))) or any(
            not _EVIDENCE.fullmatch(item) for item in evidence
        ):
            raise ValueError("command_evidence must be valid, unique, and sorted")
        object.__setattr__(self, "records", records)
        object.__setattr__(self, "command_evidence", evidence)

    def to_dict(self) -> dict[str, object]:
        return _thaw(self)  # type: ignore[return-value]


class _GitReader:
    def __init__(self, repository: Path) -> None:
        self.repository = repository
        self.evidence: set[str] = set()

    def run(self, operation: str, arguments: Sequence[str]) -> str:
        if operation not in {"cat-file", "rev-list", "rev-parse"}:
            raise QtCommitExtractionError("Git operation is not permitted")
        environment = {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_TERMINAL_PROMPT": "0",
            "HOME": os.devnull,
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        }
        try:
            result = subprocess.run(
                ["git", operation, *arguments],
                cwd=self.repository,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="strict",
                timeout=120,
                env=environment,
                shell=False,
            )
        except (OSError, subprocess.TimeoutExpired, UnicodeError) as error:
            raise QtCommitExtractionError(
                f"Git {operation} could not be read"
            ) from error
        if result.returncode:
            raise QtCommitExtractionError(f"Git {operation} failed")
        self.evidence.add(f"git:{operation}:completed")
        return result.stdout


class QtCommitExtractor:
    """Extract commits reachable from one exact acquired Qt revision."""

    extractor_name = "qt-commit-extractor"

    def extract(
        self,
        acquisition: QtRepositoryAcquisitionResult,
        repository_path: str | Path,
        output_path: str | Path,
        specification: QtCommitExtractionSpecification,
    ) -> QtCommitExtractionResult:
        if not isinstance(acquisition, QtRepositoryAcquisitionResult):
            raise TypeError("acquisition must be QtRepositoryAcquisitionResult")
        if not isinstance(specification, QtCommitExtractionSpecification):
            raise TypeError("specification must be QtCommitExtractionSpecification")
        repository = Path(repository_path).resolve()
        if not repository.is_dir():
            raise ValueError("repository_path must be an acquired repository directory")
        reader = _GitReader(repository)
        revision = acquisition.resolved_revision
        resolved = reader.run(
            "rev-parse", ["--verify", f"{revision}^{{commit}}"]
        ).strip()
        if resolved != revision:
            raise QtCommitExtractionError("acquired revision identity does not match")
        object_type = reader.run("cat-file", ["-t", revision]).strip()
        if object_type != "commit":
            raise QtCommitExtractionError("acquired revision is not a commit")
        reachable_ids = tuple(
            item
            for item in reader.run(
                "rev-list", ["--topo-order", "--reverse", revision]
            ).splitlines()
            if item
        )
        reachable_records = tuple(
            self._read_record(reader, commit_id, acquisition.object_hash_algorithm)
            for commit_id in reachable_ids
        )
        window_start = datetime.fromisoformat(specification.observation_window_start)
        window_end = datetime.fromisoformat(specification.observation_window_end)
        records = tuple(
            record
            for record in reachable_records
            if window_start
            <= datetime.fromisoformat(record.committed_at).astimezone(UTC)
            <= window_end
        )
        if not records:
            raise QtCommitExtractionError("observation window contains no commits")
        later = tuple(
            record.commit_id
            for record in reachable_records
            if datetime.fromisoformat(record.committed_at).astimezone(UTC) > window_end
        )
        if later:
            raise QtCommitExtractionError(
                "snapshot contains commits after the approved observation window"
            )
        history_digest = hashlib.sha256(
            _canonical_bytes({"reachable_commit_ids": reachable_ids})
        ).hexdigest()
        payload = {
            "schema_version": specification.schema_version,
            "artifact_role": ScientificArtifactRole.COMMIT_ARTIFACT.value,
            "source_repository": acquisition.repository_snapshot.repository_name,
            "source_revision": revision,
            "source_snapshot_digest": acquisition.repository_snapshot.snapshot_digest,
            "object_hash_algorithm": acquisition.object_hash_algorithm,
            "ordering_policy": specification.ordering_policy,
            "observation_window_start": specification.observation_window_start,
            "observation_window_end": specification.observation_window_end,
            "reachable_historical_commit_count": len(reachable_records),
            "pre_window_historical_commit_count": len(reachable_records) - len(records),
            "reachable_history_digest": history_digest,
            "records": records,
        }
        content = _canonical_bytes(payload)
        digest = hashlib.sha256(content).hexdigest()
        artifact = ScientificArtifactReference(
            artifact_name="qtbase-commits",
            artifact_role=ScientificArtifactRole.COMMIT_ARTIFACT,
            repository_relative_path=specification.artifact_repository_relative_path,
            content_digest=digest,
            schema_version=specification.schema_version,
            record_count=len(records),
            metadata={
                "ordering_policy": specification.ordering_policy,
                "source_snapshot_digest": (
                    acquisition.repository_snapshot.snapshot_digest
                ),
            },
        )
        result = QtCommitExtractionResult(
            specification=specification,
            source_revision=revision,
            source_snapshot_digest=acquisition.repository_snapshot.snapshot_digest,
            object_hash_algorithm=acquisition.object_hash_algorithm,
            records=records,
            artifact=artifact,
            ordering_policy=specification.ordering_policy,
            command_evidence=tuple(sorted(reader.evidence)),
            reachable_historical_commit_count=len(reachable_records),
            pre_window_historical_commit_count=len(reachable_records) - len(records),
            reachable_history_digest=history_digest,
        )
        self._write_once(Path(output_path).resolve(), content)
        return result

    @staticmethod
    def _read_record(
        reader: _GitReader, commit_id: str, algorithm: str
    ) -> ScientificCommitRecord:
        pattern = _OBJECT_IDS[algorithm]
        if not pattern.fullmatch(commit_id):
            raise QtCommitExtractionError("Git emitted an incomplete commit identifier")
        raw = reader.run("cat-file", ["commit", commit_id])
        header, separator, message = raw.partition("\n\n")
        if not separator:
            raise QtCommitExtractionError("Git commit object is malformed")
        parents: list[str] = []
        author = committer = None
        for line in header.splitlines():
            if line.startswith("parent "):
                parents.append(line[7:])
            elif line.startswith("author "):
                author = QtCommitExtractor._identity(line[7:])
            elif line.startswith("committer "):
                committer = QtCommitExtractor._identity(line[10:])
        if author is None or committer is None:
            raise QtCommitExtractionError(
                "Git commit lacks author or committer identity"
            )
        if any(not pattern.fullmatch(parent) for parent in parents):
            raise QtCommitExtractionError("Git emitted an incomplete parent identifier")
        return ScientificCommitRecord(
            commit_id=commit_id,
            parent_ids=tuple(parents),
            author_name=author[0],
            author_email=author[1],
            authored_at=author[2],
            committer_name=committer[0],
            committer_email=committer[1],
            committed_at=committer[2],
            message=message,
        )

    @staticmethod
    def _identity(value: str) -> tuple[str, str, str]:
        match = _IDENTITY.fullmatch(value)
        if match is None:
            raise QtCommitExtractionError("Git commit identity is malformed")
        name, email, seconds, sign, hours, minutes = match.groups()
        offset = timedelta(hours=int(hours), minutes=int(minutes))
        if sign == "-":
            offset = -offset
        try:
            instant = datetime.fromtimestamp(int(seconds), timezone(offset))
        except (OverflowError, OSError, ValueError) as error:
            raise QtCommitExtractionError("Git commit timestamp is invalid") from error
        return name, email, instant.isoformat()

    @staticmethod
    def _write_once(destination: Path, content: bytes) -> None:
        if not destination.parent.is_dir():
            raise ValueError("output parent directory must already exist")
        temporary_name: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=destination.parent,
                prefix=f".{destination.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                temporary_name = temporary.name
                temporary.write(content)
                temporary.flush()
                os.fsync(temporary.fileno())
            os.link(temporary_name, destination)
        except FileExistsError as error:
            try:
                if destination.read_bytes() == content:
                    return
            except OSError:
                pass
            raise QtCommitExtractionError("commit artifact already exists") from error
        except OSError as error:
            raise QtCommitExtractionError(
                "commit artifact could not be written"
            ) from error
        finally:
            if temporary_name is not None:
                Path(temporary_name).unlink(missing_ok=True)
