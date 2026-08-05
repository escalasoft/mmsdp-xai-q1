"""Deterministic explicit linking of extracted Qt commits and issues."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, fields, is_dataclass
from pathlib import Path, PurePosixPath

__all__ = [
    "QtCommitIssueLinkSpecification",
    "QtCommitIssueLink",
    "QtCommitIssueLinkingResult",
    "QtCommitIssueLinker",
]

_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_ISSUE = re.compile(r"(?<![A-Za-z0-9-])QTBUG-[0-9]+(?![A-Za-z0-9-])")
_LABELED = re.compile(
    r"^[ \t]*(Fixes|Task-number|Pick-to)[ \t]*:[ \t]*(.*)$",
    re.IGNORECASE,
)
_REFERENCE_TYPES = {
    "fixes": "fixes",
    "task-number": "task-number",
    "pick-to": "pick-to",
}
_ORDERING_POLICY = "commit-revision-issue-identifier-reference-type-location"
_DUPLICATE_POLICY = "remove-identical-explicit-references"
_MATCHING_POLICY = "explicit-qtbug-identifiers-only"
_MISSING_ISSUE_POLICY = "omit-unresolved-explicit-references"
_DIGEST_PLACEHOLDERS = {
    "commit_artifact_digest": "commit-artifact-sha256-required-before-execution",
    "issue_artifact_digest": "issue-artifact-sha256-required-before-execution",
}
_COMMIT_FIELDS = frozenset({"commit_id", "message"})
_ISSUE_FIELDS = frozenset({"issue_identifier"})


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _thaw(value: object) -> object:
    if is_dataclass(value) and not isinstance(value, type):
        return {item.name: _thaw(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
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


def _artifact_records(raw: bytes, name: str) -> Sequence[object]:
    try:
        value = json.loads(raw.decode("utf-8", errors="strict"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise RuntimeError(f"{name} artifact is malformed") from error
    if isinstance(value, list):
        return value
    if isinstance(value, Mapping):
        for key in ("records", "issues", "commits"):
            records = value.get(key)
            if isinstance(records, list):
                return records
    raise RuntimeError(f"{name} artifact does not contain a record array")


@dataclass(frozen=True, slots=True)
class QtCommitIssueLinkSpecification:
    """Immutable identity and policy for one linking operation."""

    schema_version: str
    commit_artifact_digest: str
    issue_artifact_digest: str
    artifact_repository_relative_path: str = (
        "artifacts/derived/qtbase-commit-issue-links.json"
    )
    ordering_policy: str = _ORDERING_POLICY
    duplicate_policy: str = _DUPLICATE_POLICY
    matching_policy: str = _MATCHING_POLICY
    missing_issue_policy: str = _MISSING_ISSUE_POLICY

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )
        for name in ("commit_artifact_digest", "issue_artifact_digest"):
            value = _text(getattr(self, name), name)
            if value != _DIGEST_PLACEHOLDERS[name] and not _SHA256.fullmatch(value):
                raise ValueError(f"{name} must be a lowercase SHA-256 digest")
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
        policies = {
            "ordering_policy": _ORDERING_POLICY,
            "duplicate_policy": _DUPLICATE_POLICY,
            "matching_policy": _MATCHING_POLICY,
            "missing_issue_policy": _MISSING_ISSUE_POLICY,
        }
        for name, expected in policies.items():
            if getattr(self, name) != expected:
                raise ValueError(f"{name} must equal {expected!r}")
        object.__setattr__(self, "artifact_repository_relative_path", path)

    def to_dict(self) -> dict[str, object]:
        return _thaw(self)  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class QtCommitIssueLink:
    """One explicit, source-located commit-to-issue provenance statement."""

    commit_revision: str
    issue_identifier: str
    reference_type: str
    reference_location: str
    artifact_digest: str

    def __post_init__(self) -> None:
        for name in (
            "commit_revision",
            "issue_identifier",
            "reference_type",
            "reference_location",
        ):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        if not _ISSUE.fullmatch(self.issue_identifier):
            raise ValueError("issue_identifier must be an explicit QTBUG identifier")
        if self.reference_type not in {"plain", *_REFERENCE_TYPES.values()}:
            raise ValueError("reference_type is not controlled")
        if not re.fullmatch(
            r"commit-message:line:[1-9][0-9]*", self.reference_location
        ):
            raise ValueError("reference_location must identify a commit-message line")
        if not _SHA256.fullmatch(self.artifact_digest):
            raise ValueError("artifact_digest must be a lowercase SHA-256 digest")
        if self.artifact_digest != _digest(_link_content(self)):
            raise ValueError("artifact_digest must identify canonical link provenance")

    def to_dict(self) -> dict[str, object]:
        return _thaw(self)  # type: ignore[return-value]


def _link_content(link: QtCommitIssueLink | Mapping[str, object]) -> dict[str, object]:
    names = (
        "commit_revision",
        "issue_identifier",
        "reference_type",
        "reference_location",
    )
    if isinstance(link, Mapping):
        return {name: link[name] for name in names}
    return {name: getattr(link, name) for name in names}


@dataclass(frozen=True, slots=True)
class QtCommitIssueLinkingResult:
    """Immutable canonical output of explicit commit--issue linking."""

    specification: QtCommitIssueLinkSpecification
    links: tuple[QtCommitIssueLink, ...]
    artifact_digest: str

    def __post_init__(self) -> None:
        if not isinstance(self.specification, QtCommitIssueLinkSpecification):
            raise TypeError("specification must be QtCommitIssueLinkSpecification")
        links = tuple(self.links)
        if any(not isinstance(item, QtCommitIssueLink) for item in links):
            raise TypeError("links must contain QtCommitIssueLink values")
        key = lambda item: (  # noqa: E731
            item.commit_revision,
            item.issue_identifier,
            item.reference_type,
            item.reference_location,
        )
        if links != tuple(sorted(set(links), key=key)):
            raise ValueError("links must be unique and canonically ordered")
        if not _SHA256.fullmatch(self.artifact_digest):
            raise ValueError("artifact_digest must be a lowercase SHA-256 digest")
        if self.artifact_digest != _digest(_result_content(self.specification, links)):
            raise ValueError(
                "artifact_digest must identify the canonical link artifact"
            )
        object.__setattr__(self, "links", links)

    def to_dict(self) -> dict[str, object]:
        return _thaw(self)  # type: ignore[return-value]


def _result_content(
    specification: QtCommitIssueLinkSpecification,
    links: tuple[QtCommitIssueLink, ...],
) -> dict[str, object]:
    return {"specification": specification, "links": links}


class QtCommitIssueLinker:
    """Recover explicit QTBUG references without semantic interpretation."""

    linker_name = "qt-commit-issue-linker"

    def link(
        self,
        specification: QtCommitIssueLinkSpecification,
        commit_artifact_path: str | Path,
        issue_artifact_path: str | Path,
    ) -> QtCommitIssueLinkingResult:
        if not isinstance(specification, QtCommitIssueLinkSpecification):
            raise TypeError("specification must be QtCommitIssueLinkSpecification")
        if any(
            getattr(specification, name) == placeholder
            for name, placeholder in _DIGEST_PLACEHOLDERS.items()
        ):
            raise ValueError(
                "artifact digest placeholders must be resolved before linking"
            )
        commit_raw = self._read(commit_artifact_path, "commit")
        issue_raw = self._read(issue_artifact_path, "issue")
        if (
            hashlib.sha256(commit_raw).hexdigest()
            != specification.commit_artifact_digest
        ):
            raise RuntimeError("commit artifact digest does not match specification")
        if hashlib.sha256(issue_raw).hexdigest() != specification.issue_artifact_digest:
            raise RuntimeError("issue artifact digest does not match specification")
        commits = self._commits(_artifact_records(commit_raw, "commit"))
        issues = self._issues(_artifact_records(issue_raw, "issue"))
        values: set[QtCommitIssueLink] = set()
        for revision, message in commits:
            for line_number, line in enumerate(message.splitlines(), start=1):
                labeled = _LABELED.match(line)
                reference_type = (
                    _REFERENCE_TYPES[labeled.group(1).lower()] if labeled else "plain"
                )
                searchable = labeled.group(2) if labeled else line
                for match in _ISSUE.finditer(searchable):
                    identifier = match.group(0)
                    if identifier not in issues:
                        continue
                    content = {
                        "commit_revision": revision,
                        "issue_identifier": identifier,
                        "reference_type": reference_type,
                        "reference_location": f"commit-message:line:{line_number}",
                    }
                    values.add(
                        QtCommitIssueLink(
                            **content, artifact_digest=_digest(content)
                        )
                    )
        key = lambda item: (  # noqa: E731
            item.commit_revision,
            item.issue_identifier,
            item.reference_type,
            item.reference_location,
        )
        links = tuple(sorted(values, key=key))
        return QtCommitIssueLinkingResult(
            specification=specification,
            links=links,
            artifact_digest=_digest(_result_content(specification, links)),
        )

    @staticmethod
    def _read(path_value: str | Path, name: str) -> bytes:
        path = Path(path_value)
        if not path.is_file():
            raise ValueError(f"{name}_artifact_path must be an existing regular file")
        try:
            return path.read_bytes()
        except OSError as error:
            raise RuntimeError(f"{name} artifact could not be read") from error

    @staticmethod
    def _commits(records: Sequence[object]) -> tuple[tuple[str, str], ...]:
        result: dict[str, str] = {}
        for value in records:
            if not isinstance(value, Mapping) or not _COMMIT_FIELDS <= value.keys():
                raise RuntimeError("commit artifact contains malformed records")
            revision = _text(value["commit_id"], "commit_id")
            message = value["message"]
            if not isinstance(message, str) or revision in result:
                raise RuntimeError("commit artifact contains malformed records")
            result[revision] = message
        return tuple(sorted(result.items()))

    @staticmethod
    def _issues(records: Sequence[object]) -> frozenset[str]:
        result: set[str] = set()
        for value in records:
            if not isinstance(value, Mapping) or not _ISSUE_FIELDS <= value.keys():
                raise RuntimeError("issue artifact contains malformed records")
            identifier = _text(value["issue_identifier"], "issue_identifier")
            if not _ISSUE.fullmatch(identifier) or identifier in result:
                raise RuntimeError("issue artifact contains malformed records")
            result.add(identifier)
        return frozenset(result)
