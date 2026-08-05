"""Deterministic extraction of raw Qt issues from a versioned local artifact."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, fields, is_dataclass
from datetime import UTC, datetime
from pathlib import Path
from types import MappingProxyType

from dataset.scientific_builder_contracts import (
    ScientificArtifactReference,
    ScientificArtifactRole,
)

__all__ = [
    "QtIssueExtractionSpecification",
    "QtIssueRecord",
    "QtIssueExtractionResult",
    "QtIssueExtractor",
]

_PROJECT_NAME = "qtbase"
_PLACEHOLDERS = {
    "canonical_issue_source": "issue-source-required-before-execution",
    "source_revision": "immutable-issue-source-revision-required-before-execution",
    "source_artifact_digest": "issue-source-sha256-required-before-execution",
    "project_identifier": "qtbase-project-identifier-required-before-execution",
    "issue_schema_version": "issue-schema-version-required-before-execution",
}
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_OBJECT_REPR = re.compile(r"<[^>]*(?:object at )?0x[0-9a-fA-F]+>")
_CREDENTIAL_URI = re.compile(r"^[a-z][a-z0-9+.-]*://[^/@\s]+@", re.IGNORECASE)
_MEMORY_ADDRESS = re.compile(r"\b0x[0-9a-fA-F]{6,}\b")
_POLICIES = {
    "ordering_policy": "canonical-issue-identifier",
    "timestamp_policy": "normalize-authoritative-timestamps-to-utc",
    "identity_policy": "source-native-stable-identifier",
    "duplicate_policy": "reject-conflicting-duplicates",
    "unresolved_record_policy": "retain-with-explicit-missing-fields",
}
_ALLOWED_FORMATS = ("json", "jsonl")
_EMPTY: Mapping[str, object] = MappingProxyType({})
_MAX_ARTIFACT_BYTES = 16 * 1024 * 1024
_BANNED_KEY_PARTS = {
    "bug_confidence",
    "created_at",
    "credential",
    "duration",
    "environment",
    "feature_enable",
    "hostname",
    "issue_link",
    "label",
    "local_path",
    "machine",
    "password",
    "prediction",
    "runtime_timestamp",
    "target",
    "timestamp",
    "token",
    "username",
}
_RECORD_FIELDS = {
    "issue_identifier",
    "project_identifier",
    "issue_type",
    "status",
    "resolution",
    "priority",
    "created_timestamp",
    "updated_timestamp",
    "resolved_timestamp",
    "summary",
    "description",
    "reporter_identifier",
    "assignee_identifier",
    "component",
    "version",
    "fix_versions",
    "metadata",
}
_OPTIONAL_TEXT_FIELDS = tuple(
    sorted(
        _RECORD_FIELDS
        - {"issue_identifier", "project_identifier", "fix_versions", "metadata"}
    )
)
_EVIDENCE = {
    "local-artifact:sha256-verified",
    "parser:json:completed",
    "parser:jsonl:completed",
}


class _QtIssueExtractionError(RuntimeError):
    """Sanitized issue-artifact validation or parsing failure."""


def _key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _safe_string(value: str, path: str) -> str:
    if (
        Path(value).is_absolute()
        or _OBJECT_REPR.search(value)
        or _MEMORY_ADDRESS.search(value)
    ):
        raise ValueError(f"{path} contains machine-local information")
    if _CREDENTIAL_URI.search(value):
        raise ValueError(f"{path} contains credentials")
    return value


def _freeze(value: object, path: str = "metadata") -> object:
    if isinstance(value, Mapping):
        frozen: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(f"{path} keys must be strings")
            normalized = _key(key)
            if any(part in normalized for part in _BANNED_KEY_PARTS):
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
        return _safe_string(value, path)
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


def _digest(value: object) -> str:
    payload = json.dumps(
        _thaw(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _timestamp(value: object, name: str) -> str | None:
    if value is None:
        return None
    text = _text(value, name)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"{name} must be a valid ISO-8601 timestamp") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{name} must include an explicit timezone")
    return parsed.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _record_content(record: QtIssueRecord | Mapping[str, object]) -> dict[str, object]:
    names = tuple(sorted(_RECORD_FIELDS - {"metadata"}))
    if isinstance(record, Mapping):
        return {name: record[name] for name in names}
    return {name: getattr(record, name) for name in names}


@dataclass(frozen=True, slots=True)
class QtIssueExtractionSpecification:
    project_name: str
    canonical_issue_source: str
    source_revision: str
    source_artifact_digest: str
    project_identifier: str
    issue_schema_version: str
    extraction_policy_version: str
    ordering_policy: str = _POLICIES["ordering_policy"]
    timestamp_policy: str = _POLICIES["timestamp_policy"]
    identity_policy: str = _POLICIES["identity_policy"]
    duplicate_policy: str = _POLICIES["duplicate_policy"]
    unresolved_record_policy: str = _POLICIES["unresolved_record_policy"]
    allowed_input_formats: tuple[str, ...] = _ALLOWED_FORMATS
    metadata: Mapping[str, object] = field(default_factory=lambda: _EMPTY)

    def __post_init__(self) -> None:
        if self.project_name != _PROJECT_NAME:
            raise ValueError("project_name must equal 'qtbase'")
        source = _text(self.canonical_issue_source, "canonical_issue_source")
        _safe_string(source, "canonical_issue_source")
        revision = _text(self.source_revision, "source_revision")
        digest = _text(self.source_artifact_digest, "source_artifact_digest")
        if digest != _PLACEHOLDERS["source_artifact_digest"] and not _SHA256.fullmatch(
            digest
        ):
            raise ValueError(
                "source_artifact_digest must be a lowercase SHA-256 digest"
            )
        for name in (
            "project_identifier",
            "issue_schema_version",
            "extraction_policy_version",
        ):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        for name, expected in _POLICIES.items():
            if getattr(self, name) != expected:
                raise ValueError(f"{name} must equal {expected!r}")
        if tuple(self.allowed_input_formats) != _ALLOWED_FORMATS:
            raise ValueError(f"allowed_input_formats must equal {_ALLOWED_FORMATS!r}")
        object.__setattr__(self, "canonical_issue_source", source)
        object.__setattr__(self, "source_revision", revision)
        object.__setattr__(self, "source_artifact_digest", digest)
        object.__setattr__(self, "allowed_input_formats", _ALLOWED_FORMATS)
        object.__setattr__(self, "metadata", _freeze(self.metadata))

    def to_dict(self) -> dict[str, object]:
        return _thaw(self)  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class QtIssueRecord:
    issue_identifier: str
    project_identifier: str
    issue_type: str | None
    status: str | None
    resolution: str | None
    priority: str | None
    created_timestamp: str | None
    updated_timestamp: str | None
    resolved_timestamp: str | None
    summary: str | None
    description: str | None
    reporter_identifier: str | None
    assignee_identifier: str | None
    component: str | None
    version: str | None
    fix_versions: tuple[str, ...]
    source_record_digest: str
    metadata: Mapping[str, object] = field(default_factory=lambda: _EMPTY)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "issue_identifier", _text(self.issue_identifier, "issue_identifier")
        )
        object.__setattr__(
            self,
            "project_identifier",
            _text(self.project_identifier, "project_identifier"),
        )
        for name in _OPTIONAL_TEXT_FIELDS:
            value = getattr(self, name)
            if value is not None and not isinstance(value, str):
                raise TypeError(f"{name} must be a string or None")
        for name in ("reporter_identifier", "assignee_identifier"):
            value = getattr(self, name)
            if value is not None:
                _safe_string(value, name)
        for name in ("created_timestamp", "updated_timestamp", "resolved_timestamp"):
            object.__setattr__(self, name, _timestamp(getattr(self, name), name))
        created, updated, resolved = (
            getattr(self, name)
            for name in ("created_timestamp", "updated_timestamp", "resolved_timestamp")
        )
        if updated is not None and created is None:
            raise ValueError("updated_timestamp requires created_timestamp")
        if resolved is not None and created is None:
            raise ValueError("resolved_timestamp requires created_timestamp")
        if updated is not None and updated < created:
            raise ValueError("updated_timestamp must not precede created_timestamp")
        if resolved is not None and resolved < created:
            raise ValueError("resolved_timestamp must not precede created_timestamp")
        versions = tuple(self.fix_versions)
        if any(not isinstance(item, str) or not item.strip() for item in versions):
            raise ValueError("fix_versions must contain non-empty strings")
        versions = tuple(sorted(item.strip() for item in versions))
        if len(versions) != len(set(versions)):
            raise ValueError("fix_versions must contain unique values")
        object.__setattr__(self, "fix_versions", versions)
        if not _SHA256.fullmatch(self.source_record_digest):
            raise ValueError("source_record_digest must be a lowercase SHA-256 digest")
        if self.source_record_digest != _digest(_record_content(self)):
            raise ValueError(
                "source_record_digest must identify canonical source content"
            )
        object.__setattr__(self, "metadata", _freeze(self.metadata))

    def to_dict(self) -> dict[str, object]:
        return _thaw(self)  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class QtIssueExtractionResult:
    specification: QtIssueExtractionSpecification
    issues: tuple[QtIssueRecord, ...]
    extraction_artifact: ScientificArtifactReference
    extracted_issue_count: int
    issue_type_counts: Mapping[str, int]
    status_counts: Mapping[str, int]
    resolved_issue_count: int
    unresolved_issue_count: int
    missing_created_timestamp_count: int
    missing_resolved_timestamp_count: int
    issue_identity_digest: str
    command_evidence: tuple[str, ...]
    metadata: Mapping[str, object] = field(default_factory=lambda: _EMPTY)

    def __post_init__(self) -> None:
        if not isinstance(self.specification, QtIssueExtractionSpecification):
            raise TypeError("specification must be QtIssueExtractionSpecification")
        issues = tuple(self.issues)
        if any(not isinstance(item, QtIssueRecord) for item in issues):
            raise TypeError("issues must contain QtIssueRecord values")
        identifiers = tuple(item.issue_identifier for item in issues)
        if identifiers != tuple(sorted(identifiers)) or len(identifiers) != len(
            set(identifiers)
        ):
            raise ValueError("issues must have unique identifiers in canonical order")
        if any(
            item.project_identifier != self.specification.project_identifier
            for item in issues
        ):
            raise ValueError("issue project identifiers must match the specification")
        type_counts = dict(
            sorted(Counter(item.issue_type or "<missing>" for item in issues).items())
        )
        status_counts = dict(
            sorted(Counter(item.status or "<missing>" for item in issues).items())
        )
        expected = (
            len(issues),
            sum(item.resolved_timestamp is not None for item in issues),
            sum(item.resolved_timestamp is None for item in issues),
            sum(item.created_timestamp is None for item in issues),
            sum(item.resolved_timestamp is None for item in issues),
        )
        actual = (
            self.extracted_issue_count,
            self.resolved_issue_count,
            self.unresolved_issue_count,
            self.missing_created_timestamp_count,
            self.missing_resolved_timestamp_count,
        )
        if (
            actual != expected
            or dict(self.issue_type_counts) != type_counts
            or dict(self.status_counts) != status_counts
        ):
            raise ValueError("result aggregate counts are inconsistent")
        content = _artifact_content(self.specification, issues)
        artifact = self.extraction_artifact
        expected_path = (
            f"artifacts/qtbase/issues/{self.specification.source_revision}/"
            "qt-issues.jsonl"
        )
        if (
            artifact.artifact_role is not ScientificArtifactRole.ISSUE_ARTIFACT
            or artifact.repository_relative_path != expected_path
            or artifact.record_count != len(issues)
            or artifact.content_digest != _digest(content)
        ):
            raise ValueError("issue artifact identity or record count is inconsistent")
        identity = _digest(
            {
                "artifact_content_digest": artifact.content_digest,
                "canonical_issue_source": self.specification.canonical_issue_source,
                "source_revision": self.specification.source_revision,
                "source_artifact_digest": self.specification.source_artifact_digest,
                "issue_schema_version": self.specification.issue_schema_version,
                "extraction_policy_version": (
                    self.specification.extraction_policy_version
                ),
            }
        )
        if self.issue_identity_digest != identity:
            raise ValueError("issue_identity_digest is inconsistent")
        evidence = tuple(self.command_evidence)
        if (
            not evidence
            or evidence != tuple(sorted(set(evidence)))
            or any(item not in _EVIDENCE for item in evidence)
        ):
            raise ValueError("command_evidence must be controlled, unique, and sorted")
        object.__setattr__(self, "issues", issues)
        object.__setattr__(self, "issue_type_counts", MappingProxyType(type_counts))
        object.__setattr__(self, "status_counts", MappingProxyType(status_counts))
        object.__setattr__(self, "command_evidence", evidence)
        object.__setattr__(self, "metadata", _freeze(self.metadata))

    def to_dict(self) -> dict[str, object]:
        return _thaw(self)  # type: ignore[return-value]


def _artifact_content(
    specification: QtIssueExtractionSpecification, issues: tuple[QtIssueRecord, ...]
) -> dict[str, object]:
    return {
        "canonical_issue_source": specification.canonical_issue_source,
        "source_revision": specification.source_revision,
        "source_artifact_digest": specification.source_artifact_digest,
        "project_identifier": specification.project_identifier,
        "issue_schema_version": specification.issue_schema_version,
        "extraction_policy_version": specification.extraction_policy_version,
        "policies": {name: getattr(specification, name) for name in _POLICIES},
        "issues": issues,
    }


class QtIssueExtractor:
    """Extract raw issue provenance without linking, labeling, or features."""

    extractor_name = "qt-issue-extractor"

    def extract(
        self,
        specification: QtIssueExtractionSpecification,
        source_artifact_path: str | Path,
    ) -> QtIssueExtractionResult:
        if not isinstance(specification, QtIssueExtractionSpecification):
            raise TypeError("specification must be QtIssueExtractionSpecification")
        unresolved = [
            name
            for name, placeholder in _PLACEHOLDERS.items()
            if getattr(specification, name) == placeholder
        ]
        if unresolved:
            raise ValueError(
                "issue extraction placeholders must be resolved before execution"
            )
        path = Path(source_artifact_path)
        if not path.is_file():
            raise ValueError("source_artifact_path must be an existing regular file")
        extension = path.suffix.lower().removeprefix(".")
        if extension not in specification.allowed_input_formats:
            raise ValueError("source artifact extension is not approved")
        try:
            size = path.stat().st_size
            if size > _MAX_ARTIFACT_BYTES:
                raise _QtIssueExtractionError(
                    "source artifact exceeds the safe size limit"
                )
            raw = path.read_bytes()
        except OSError as error:
            raise _QtIssueExtractionError(
                "source artifact could not be read"
            ) from error
        if hashlib.sha256(raw).hexdigest() != specification.source_artifact_digest:
            raise _QtIssueExtractionError(
                "source artifact digest does not match specification"
            )
        try:
            text = raw.decode("utf-8", errors="strict")
            values = self._parse(text, extension)
            records = tuple(
                self._record(value, specification.project_identifier)
                for value in values
            )
        except (UnicodeError, json.JSONDecodeError, TypeError, ValueError) as error:
            raise _QtIssueExtractionError(
                "source artifact contains malformed issue records"
            ) from error
        by_identifier: dict[str, QtIssueRecord] = {}
        for record in records:
            previous = by_identifier.get(record.issue_identifier)
            if previous is not None:
                if previous.source_record_digest != record.source_record_digest:
                    raise _QtIssueExtractionError(
                        "source artifact contains conflicting duplicate "
                        "issue identifiers"
                    )
                raise _QtIssueExtractionError(
                    "source artifact contains duplicate issue identifiers"
                )
            by_identifier[record.issue_identifier] = record
        issues = tuple(
            sorted(by_identifier.values(), key=lambda item: item.issue_identifier)
        )
        content_digest = _digest(_artifact_content(specification, issues))
        artifact = ScientificArtifactReference(
            artifact_name="qtbase-issues",
            artifact_role=ScientificArtifactRole.ISSUE_ARTIFACT,
            repository_relative_path=f"artifacts/qtbase/issues/{specification.source_revision}/qt-issues.jsonl",
            content_digest=content_digest,
            schema_version=specification.issue_schema_version,
            record_count=len(issues),
            metadata={"record_count_policy": "stable-issue-identifiers"},
        )
        identity = _digest(
            {
                "artifact_content_digest": content_digest,
                "canonical_issue_source": specification.canonical_issue_source,
                "source_revision": specification.source_revision,
                "source_artifact_digest": specification.source_artifact_digest,
                "issue_schema_version": specification.issue_schema_version,
                "extraction_policy_version": specification.extraction_policy_version,
            }
        )
        return QtIssueExtractionResult(
            specification=specification,
            issues=issues,
            extraction_artifact=artifact,
            extracted_issue_count=len(issues),
            issue_type_counts=dict(
                Counter(item.issue_type or "<missing>" for item in issues)
            ),
            status_counts=dict(Counter(item.status or "<missing>" for item in issues)),
            resolved_issue_count=sum(
                item.resolved_timestamp is not None for item in issues
            ),
            unresolved_issue_count=sum(
                item.resolved_timestamp is None for item in issues
            ),
            missing_created_timestamp_count=sum(
                item.created_timestamp is None for item in issues
            ),
            missing_resolved_timestamp_count=sum(
                item.resolved_timestamp is None for item in issues
            ),
            issue_identity_digest=identity,
            command_evidence=tuple(
                sorted(
                    {"local-artifact:sha256-verified", f"parser:{extension}:completed"}
                )
            ),
        )

    @staticmethod
    def _parse(text: str, extension: str) -> Sequence[object]:
        if extension == "json":
            value = json.loads(text)
            if not isinstance(value, list):
                raise ValueError("JSON issue artifact must contain one array")
            return value
        lines = text.splitlines()
        if any(not line.strip() for line in lines):
            raise ValueError("JSONL issue artifact must not contain blank records")
        return tuple(json.loads(line) for line in lines)

    @staticmethod
    def _record(value: object, project_identifier: str) -> QtIssueRecord:
        if not isinstance(value, Mapping) or any(
            not isinstance(key, str) for key in value
        ):
            raise TypeError("each issue record must be an object")
        unknown = set(value) - _RECORD_FIELDS
        if (
            unknown
            or "issue_identifier" not in value
            or "project_identifier" not in value
        ):
            raise ValueError("issue record fields do not match the controlled schema")
        if value["project_identifier"] != project_identifier:
            raise ValueError("issue project identifier does not match specification")
        metadata = value.get("metadata", {})
        if not isinstance(metadata, Mapping):
            raise TypeError("metadata must be a mapping")
        fix_versions = value.get("fix_versions", ())
        if isinstance(fix_versions, (str, bytes)) or not isinstance(
            fix_versions, Sequence
        ):
            raise TypeError("fix_versions must be an array")
        normalized: dict[str, object] = {
            "issue_identifier": value["issue_identifier"],
            "project_identifier": value["project_identifier"],
            "fix_versions": tuple(fix_versions),
        }
        normalized.update({name: value.get(name) for name in _OPTIONAL_TEXT_FIELDS})
        for name in ("created_timestamp", "updated_timestamp", "resolved_timestamp"):
            normalized[name] = _timestamp(normalized[name], name)
        if any(not isinstance(item, str) for item in normalized["fix_versions"]):
            raise TypeError("fix_versions must contain strings")
        normalized["fix_versions"] = tuple(
            sorted(item.strip() for item in normalized["fix_versions"])
        )
        digest = _digest(_record_content(normalized))
        return QtIssueRecord(
            **normalized, source_record_digest=digest, metadata=metadata
        )  # type: ignore[arg-type]
