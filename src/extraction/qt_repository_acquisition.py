"""Deterministic acquisition of one immutable Qt Base repository snapshot."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, fields
from pathlib import Path
from types import MappingProxyType
from urllib.parse import urlsplit, urlunsplit

from dataset.scientific_builder_contracts import (
    ScientificArtifactReference,
    ScientificArtifactRole,
    ScientificRepositorySnapshot,
)

__all__ = [
    "QtRepositoryAcquisitionSpecification",
    "QtRepositoryAcquisitionResult",
    "QtRepositoryAcquirer",
]

_REPOSITORY_NAME = "qtbase"
_CANONICAL_URL = "https://code.qt.io/qt/qtbase.git"
_LOCAL_TEST_TRANSPORT = "local-test-transport"
_PLACEHOLDER_REFERENCE = "revision-required-before-execution"
_OBJECT_IDS = {
    "sha1": re.compile(r"[0-9a-f]{40}\Z"),
    "sha256": re.compile(r"[0-9a-f]{64}\Z"),
}
_EMPTY = MappingProxyType({})
_TIMEOUT_SECONDS = 120
_BANNED_KEYS = {
    "clone_date",
    "created_at",
    "duration",
    "environment",
    "hostname",
    "local_path",
    "machine_identifier",
    "machine_name",
    "runtime_timestamp",
    "timestamp",
    "token",
    "username",
}
_OBJECT_REPR = re.compile(r"<[^>]*(?:object at )?0x[0-9a-fA-F]+>")
_COMMAND_EVIDENCE = re.compile(
    r"git:(?:cat-file|clone|config|fetch|remote|rev-parse):completed\Z"
)


class _QtRepositoryAcquisitionError(RuntimeError):
    """Sanitized acquisition failure."""


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
            if _key(key) in _BANNED_KEYS:
                raise ValueError(f"{path} contains forbidden field {key!r}")
            frozen[key] = _freeze(item, f"{path}.{key}")
        return MappingProxyType(frozen)
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item, path) for item in value)
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{path} contains a non-finite number")
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        if Path(value).is_absolute() or _OBJECT_REPR.search(value):
            raise ValueError(f"{path} contains machine-local information")
        return value
    raise TypeError(f"{path} must contain JSON-compatible values")


def _thaw(value: object) -> object:
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    if isinstance(value, ScientificArtifactRole):
        return value.value
    return value


def _as_dict(instance: object) -> dict[str, object]:
    return {
        item.name: _thaw(getattr(instance, item.name))
        for item in fields(instance)
        if not item.name.startswith("_")
    }


def _digest(content: Mapping[str, object]) -> str:
    payload = json.dumps(
        content, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _https_url(value: object, name: str) -> str:
    url = _text(value, name)
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
    ):
        raise ValueError(f"{name} must be an HTTPS URL without embedded credentials")
    if parsed.query or parsed.fragment:
        raise ValueError(f"{name} must not contain a query or fragment")
    return url


def _normalized_remote(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme == "https":
        if parsed.username or parsed.password:
            raise ValueError("repository URL must not contain embedded credentials")
        path = parsed.path.rstrip("/")
        if path.endswith(".git"):
            path = path[:-4]
        return urlunsplit(("https", parsed.netloc.lower(), path, "", ""))
    return str(Path(value).resolve())


@dataclass(frozen=True, slots=True)
class QtRepositoryAcquisitionSpecification:
    repository_name: str
    canonical_repository_url: str
    transport_repository_url: str
    requested_reference: str
    default_branch: str
    acquisition_policy_version: str
    allowed_hash_algorithms: tuple[str, ...] = ("sha1", "sha256")
    metadata: Mapping[str, object] = field(default_factory=lambda: _EMPTY)
    _allow_local_transport_for_tests: bool = field(
        default=False, repr=False, compare=False
    )
    _local_transport_path: str | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if _text(self.repository_name, "repository_name") != _REPOSITORY_NAME:
            raise ValueError("repository_name must equal 'qtbase'")
        canonical = _https_url(
            self.canonical_repository_url, "canonical_repository_url"
        )
        if canonical != _CANONICAL_URL:
            raise ValueError(f"canonical_repository_url must equal {_CANONICAL_URL!r}")
        transport = _text(self.transport_repository_url, "transport_repository_url")
        if self._allow_local_transport_for_tests:
            if transport == _LOCAL_TEST_TRANSPORT:
                if self._local_transport_path is not None:
                    raise ValueError(
                        "sanitized local transport must not retain an operational path"
                    )
            elif Path(transport).is_absolute():
                object.__setattr__(self, "_local_transport_path", transport)
                transport = _LOCAL_TEST_TRANSPORT
            else:
                raise ValueError("local test transport must be an absolute path")
        else:
            if self._local_transport_path is not None:
                raise ValueError("local transport path requires the local test policy")
            _https_url(transport, "transport_repository_url")
            if transport != canonical:
                raise ValueError(
                    "the production transport must equal the canonical URL"
                )
        reference = _text(self.requested_reference, "requested_reference")
        if reference.startswith("-") or any(ord(char) < 32 for char in reference):
            raise ValueError("requested_reference is not a safe Git reference")
        algorithms = tuple(sorted(self.allowed_hash_algorithms))
        if algorithms != ("sha1", "sha256"):
            raise ValueError(
                "allowed_hash_algorithms must contain exactly sha1 and sha256"
            )
        object.__setattr__(self, "repository_name", _REPOSITORY_NAME)
        object.__setattr__(self, "canonical_repository_url", canonical)
        object.__setattr__(self, "transport_repository_url", transport)
        object.__setattr__(self, "requested_reference", reference)
        object.__setattr__(
            self, "default_branch", _text(self.default_branch, "default_branch")
        )
        object.__setattr__(
            self,
            "acquisition_policy_version",
            _text(self.acquisition_policy_version, "acquisition_policy_version"),
        )
        object.__setattr__(self, "allowed_hash_algorithms", algorithms)
        object.__setattr__(self, "metadata", _freeze(self.metadata))

    @classmethod
    def _for_local_test(cls, **values: object) -> QtRepositoryAcquisitionSpecification:
        values["_allow_local_transport_for_tests"] = True
        return cls(**values)  # type: ignore[arg-type]

    def to_dict(self) -> dict[str, object]:
        return _as_dict(self)

    def _detached_for_result(self) -> QtRepositoryAcquisitionSpecification:
        if not self._allow_local_transport_for_tests:
            return self
        return QtRepositoryAcquisitionSpecification(
            repository_name=self.repository_name,
            canonical_repository_url=self.canonical_repository_url,
            transport_repository_url=_LOCAL_TEST_TRANSPORT,
            requested_reference=self.requested_reference,
            default_branch=self.default_branch,
            acquisition_policy_version=self.acquisition_policy_version,
            allowed_hash_algorithms=self.allowed_hash_algorithms,
            metadata=self.metadata,
            _allow_local_transport_for_tests=True,
        )


@dataclass(frozen=True, slots=True)
class QtRepositoryAcquisitionResult:
    specification: QtRepositoryAcquisitionSpecification
    repository_snapshot: ScientificRepositorySnapshot
    resolved_reference: str
    resolved_revision: str
    object_hash_algorithm: str
    canonical_repository_url: str
    transport_repository_url: str
    repository_identity_digest: str
    acquisition_artifact: ScientificArtifactReference
    command_evidence: tuple[str, ...]
    metadata: Mapping[str, object] = field(default_factory=lambda: _EMPTY)

    def __post_init__(self) -> None:
        if not isinstance(self.specification, QtRepositoryAcquisitionSpecification):
            raise TypeError(
                "specification must be QtRepositoryAcquisitionSpecification"
            )
        if not isinstance(self.repository_snapshot, ScientificRepositorySnapshot):
            raise TypeError("repository_snapshot must be ScientificRepositorySnapshot")
        if not isinstance(self.acquisition_artifact, ScientificArtifactReference):
            raise TypeError("acquisition_artifact must be ScientificArtifactReference")
        resolved_reference = _text(self.resolved_reference, "resolved_reference")
        if resolved_reference != self.specification.requested_reference:
            raise ValueError("resolved_reference must equal the requested reference")
        snapshot = self.repository_snapshot
        if snapshot.repository_name != _REPOSITORY_NAME:
            raise ValueError("snapshot repository_name must equal 'qtbase'")
        if snapshot.repository_url != _CANONICAL_URL:
            raise ValueError("snapshot repository_url must equal the canonical Qt URL")
        if snapshot.default_branch != self.specification.default_branch:
            raise ValueError("snapshot default_branch must equal the specification")
        if (
            snapshot.acquisition_policy_version
            != self.specification.acquisition_policy_version
        ):
            raise ValueError(
                "snapshot acquisition_policy_version must equal the specification"
            )
        if self.canonical_repository_url != self.specification.canonical_repository_url:
            raise ValueError("canonical_repository_url must equal the specification")
        expected_transport = self.specification.transport_repository_url
        if self.specification._allow_local_transport_for_tests:
            if expected_transport != _LOCAL_TEST_TRANSPORT:
                raise ValueError("local specification transport identity is invalid")
            if self.specification._local_transport_path is not None:
                raise ValueError("result specification must not retain a local path")
            if self.transport_repository_url != _LOCAL_TEST_TRANSPORT:
                raise ValueError("local-test transport must equal local-test-transport")
        elif self.transport_repository_url != expected_transport:
            raise ValueError("production transport must equal the specification")
        algorithm = _text(self.object_hash_algorithm, "object_hash_algorithm")
        revision = _text(self.resolved_revision, "resolved_revision")
        if algorithm not in _OBJECT_IDS or not _OBJECT_IDS[algorithm].fullmatch(
            revision
        ):
            raise ValueError("resolved_revision does not match object_hash_algorithm")
        if revision != snapshot.repository_revision:
            raise ValueError("snapshot revision must equal resolved_revision")
        if (
            self.acquisition_artifact.artifact_role
            is not ScientificArtifactRole.REPOSITORY_SNAPSHOT
        ):
            raise ValueError("acquisition_artifact must have repository-snapshot role")
        if (
            self.acquisition_artifact.content_digest
            != self.repository_snapshot.snapshot_digest
        ):
            raise ValueError("artifact and snapshot digests must agree")
        evidence = tuple(self.command_evidence)
        if evidence != tuple(sorted(set(evidence))):
            raise ValueError(
                "command_evidence must be unique and deterministically ordered"
            )
        if any(
            not isinstance(entry, str) or not _COMMAND_EVIDENCE.fullmatch(entry)
            for entry in evidence
        ):
            raise ValueError("command_evidence contains an invalid entry")
        frozen_metadata = _freeze(self.metadata)
        expected_identity = _identity_digest(
            self.specification,
            self.repository_snapshot,
            revision,
            algorithm,
            self.acquisition_artifact,
        )
        if self.repository_identity_digest != expected_identity:
            raise ValueError("repository_identity_digest is inconsistent")
        object.__setattr__(
            self,
            "resolved_reference",
            resolved_reference,
        )
        object.__setattr__(self, "resolved_revision", revision)
        object.__setattr__(self, "object_hash_algorithm", algorithm)
        object.__setattr__(self, "command_evidence", evidence)
        object.__setattr__(self, "metadata", frozen_metadata)

    def to_dict(self) -> dict[str, object]:
        return _as_dict(self)


def _identity_digest(
    specification: QtRepositoryAcquisitionSpecification,
    snapshot: ScientificRepositorySnapshot,
    revision: str,
    algorithm: str,
    artifact: ScientificArtifactReference,
) -> str:
    return _digest(
        {
            "repository_name": _REPOSITORY_NAME,
            "canonical_repository_url": _CANONICAL_URL,
            "resolved_revision": revision,
            "object_hash_algorithm": algorithm,
            "acquisition_policy_version": specification.acquisition_policy_version,
            "snapshot_digest": snapshot.snapshot_digest,
            "acquisition_artifact_digest": artifact.content_digest,
        }
    )


class _GitExecutor:
    _ALLOWED = {"cat-file", "clone", "config", "fetch", "remote", "rev-parse"}

    def __init__(self) -> None:
        self.evidence: set[str] = set()

    def run(
        self, operation: str, arguments: Sequence[str], *, cwd: Path | None = None
    ) -> str:
        if operation not in self._ALLOWED or not arguments or arguments[0] != operation:
            raise _QtRepositoryAcquisitionError("Git operation is not permitted")
        environment = {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0",
            "HOME": os.devnull,
            "LANG": "C",
            "LC_ALL": "C",
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        }
        try:
            result = subprocess.run(
                ["git", *arguments],
                cwd=cwd,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="strict",
                timeout=_TIMEOUT_SECONDS,
                env=environment,
                shell=False,
            )
        except subprocess.TimeoutExpired as error:
            raise _QtRepositoryAcquisitionError(
                f"Git {operation} exceeded the acquisition timeout"
            ) from error
        except (OSError, UnicodeError) as error:
            raise _QtRepositoryAcquisitionError(
                f"Git {operation} could not be executed"
            ) from error
        if result.returncode != 0:
            raise _QtRepositoryAcquisitionError(f"Git {operation} failed")
        self.evidence.add(f"git:{operation}:completed")
        return result.stdout.strip()


class QtRepositoryAcquirer:
    """Project-specific adapter for repository-acquisition only."""

    acquirer_name = "qt-repository-acquirer"

    def __init__(
        self, *, _allow_repository_destination_for_tests: bool = False
    ) -> None:
        self._allow_repository_destination_for_tests = (
            _allow_repository_destination_for_tests
        )

    def acquire(
        self,
        specification: QtRepositoryAcquisitionSpecification,
        destination: str | Path,
    ) -> QtRepositoryAcquisitionResult:
        if not isinstance(specification, QtRepositoryAcquisitionSpecification):
            raise TypeError(
                "specification must be QtRepositoryAcquisitionSpecification"
            )
        if specification.requested_reference == _PLACEHOLDER_REFERENCE:
            raise ValueError(
                "requested_reference must be deliberately resolved before acquisition"
            )
        if not isinstance(destination, (str, Path)) or not str(destination).strip():
            raise ValueError(
                "destination must be an explicit caller-supplied directory"
            )
        target = Path(destination).expanduser().resolve()
        project_root = Path(__file__).resolve().parents[2]
        if not self._allow_repository_destination_for_tests and (
            target == project_root or project_root in target.parents
        ):
            raise ValueError("destination must be outside the MMSDP-XAI repository")
        executor = _GitExecutor()
        git_marker = target / ".git"
        if not git_marker.exists():
            if target.exists() and (not target.is_dir() or any(target.iterdir())):
                raise ValueError("non-Git destination must be absent or empty")
            target.parent.mkdir(parents=True, exist_ok=True)
            executor.run(
                "clone",
                [
                    "clone",
                    "--no-checkout",
                    "--no-tags",
                    "--single-branch",
                    "--origin",
                    "origin",
                    self._operational_transport(specification),
                    str(target),
                ],
            )
        remote = executor.run("remote", ["remote", "get-url", "origin"], cwd=target)
        expected_remote = self._operational_transport(specification)
        try:
            matches = _normalized_remote(remote) == _normalized_remote(expected_remote)
        except ValueError as error:
            raise _QtRepositoryAcquisitionError(
                "repository remote identity is invalid"
            ) from error
        if not matches:
            raise _QtRepositoryAcquisitionError(
                "repository does not correspond to Qt Base transport"
            )
        revision = self._resolve(executor, target, specification.requested_reference)
        object_type = executor.run("cat-file", ["cat-file", "-t", revision], cwd=target)
        if object_type != "commit":
            raise _QtRepositoryAcquisitionError("resolved Git object is not a commit")
        algorithm = self._object_format(executor, target, revision)
        if algorithm not in specification.allowed_hash_algorithms:
            raise _QtRepositoryAcquisitionError(
                "repository object hash algorithm is not allowed"
            )
        snapshot_content = {
            "repository_name": _REPOSITORY_NAME,
            "repository_url": _CANONICAL_URL,
            "repository_revision": revision,
            "default_branch": specification.default_branch,
            "acquisition_policy_version": specification.acquisition_policy_version,
        }
        snapshot_digest = _digest(snapshot_content)
        snapshot = ScientificRepositorySnapshot(
            **snapshot_content,
            snapshot_digest=snapshot_digest,
            metadata={},
        )
        artifact = ScientificArtifactReference(
            artifact_name="qtbase-repository-snapshot",
            artifact_role=ScientificArtifactRole.REPOSITORY_SNAPSHOT,
            repository_relative_path="artifacts/repository/qtbase-snapshot.json",
            content_digest=snapshot_digest,
            schema_version=specification.acquisition_policy_version,
            record_count=1,
            metadata={},
        )
        identity = _identity_digest(
            specification, snapshot, revision, algorithm, artifact
        )
        result_specification = specification._detached_for_result()
        return QtRepositoryAcquisitionResult(
            specification=result_specification,
            repository_snapshot=snapshot,
            resolved_reference=specification.requested_reference,
            resolved_revision=revision,
            object_hash_algorithm=algorithm,
            canonical_repository_url=_CANONICAL_URL,
            transport_repository_url=specification.transport_repository_url,
            repository_identity_digest=identity,
            acquisition_artifact=artifact,
            command_evidence=tuple(sorted(executor.evidence)),
            metadata={},
        )

    @staticmethod
    def _operational_transport(
        specification: QtRepositoryAcquisitionSpecification,
    ) -> str:
        if specification._allow_local_transport_for_tests:
            path = specification._local_transport_path
            if path is None:
                raise _QtRepositoryAcquisitionError(
                    "local test transport path is unavailable"
                )
            return path
        return specification.transport_repository_url

    @staticmethod
    def _resolve(executor: _GitExecutor, target: Path, reference: str) -> str:
        candidates = (
            f"{reference}^{{commit}}",
            f"refs/tags/{reference}^{{commit}}",
            f"refs/heads/{reference}^{{commit}}",
            f"refs/remotes/origin/{reference}^{{commit}}",
        )
        for candidate in candidates:
            try:
                revision = executor.run(
                    "rev-parse", ["rev-parse", "--verify", candidate], cwd=target
                )
            except _QtRepositoryAcquisitionError:
                continue
            if revision:
                return revision
        try:
            executor.run(
                "fetch",
                ["fetch", "--no-tags", "origin", reference],
                cwd=target,
            )
            return executor.run(
                "rev-parse",
                ["rev-parse", "--verify", "FETCH_HEAD^{commit}"],
                cwd=target,
            )
        except _QtRepositoryAcquisitionError as error:
            raise _QtRepositoryAcquisitionError(
                "requested reference could not be resolved to a commit"
            ) from error

    @staticmethod
    def _object_format(executor: _GitExecutor, target: Path, revision: str) -> str:
        try:
            configured = executor.run(
                "config", ["config", "--get", "extensions.objectFormat"], cwd=target
            )
        except _QtRepositoryAcquisitionError:
            configured = ""
        algorithm = configured or ("sha1" if len(revision) == 40 else "sha256")
        if algorithm not in _OBJECT_IDS or not _OBJECT_IDS[algorithm].fullmatch(
            revision
        ):
            raise _QtRepositoryAcquisitionError(
                "Git returned an invalid full object identifier"
            )
        return algorithm
