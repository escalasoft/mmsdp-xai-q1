"""Fail-closed scientific contracts for the JIT-Defects4J migration gate."""

from __future__ import annotations

import hashlib
import io
import json
import re
import subprocess
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

SCHEMA_VERSION = "jit-defects4j-migration-audit-1.0.0"
SOURCE_REVISION = "584799fdec6095ab75a45fd2a5f8db5b12163aa5"
PACKAGE_SHA256 = "9e5ca1a393b70ee7e87c410b162005958775f3f3732f9f83da9dd24a7dfe2b47"
PACKAGE_SIZE = 75_326_372

PROJECTS = (
    "ant-ivy",
    "commons-bcel",
    "commons-beanutils",
    "commons-codec",
    "commons-collections",
    "commons-compress",
    "commons-configuration",
    "commons-dbcp",
    "commons-digester",
    "commons-io",
    "commons-jcs",
    "commons-lang",
    "commons-math",
    "commons-net",
    "commons-scxml",
    "commons-validator",
    "commons-vfs",
    "giraph",
    "gora",
    "opennlp",
    "parquet-mr",
)
REPOSITORIES = {name: f"https://github.com/apache/{name}.git" for name in PROJECTS}
FEATURE_COLUMNS = (
    "project",
    "parent_hashes",
    "commit_hash",
    "author_name",
    "author_email",
    "author_date",
    "author_date_unix_timestamp",
    "commit_message",
    "la",
    "ld",
    "fileschanged",
    "nf",
    "ns",
    "nd",
    "entropy",
    "ndev",
    "lt",
    "nuc",
    "age",
    "exp",
    "rexp",
    "sexp",
    "classification",
    "fix",
    "is_buggy_commit",
)
DENYLIST = frozenset(
    {
        "is_buggy_commit",
        "label",
        "target",
        "classification",
        "fix",
        "fixing_status",
        "buggy_line",
        "line_label",
        "szz",
        "blame_output",
        "future_bug_fix",
        "future_issue_metadata",
        "post_observation_defect",
        "manual_defect_indicator",
        "packaged_split",
    }
)
ALLOWLIST = {
    "code": ("git_parent_diff_added_lines", "git_parent_diff_deleted_lines"),
    "process": (
        "files_changed",
        "added_loc",
        "deleted_loc",
        "churn",
        "developer_experience_before_commit",
        "prior_changes",
        "prior_developer_activity",
        "prior_project_activity",
        "time_since_previous_change",
        "prior_file_history",
    ),
    "text": ("masked_commit_message",),
}
_SHA1 = re.compile(r"[0-9a-f]{40}\Z")


class ContractError(ValueError):
    """A source or scientific-contract violation."""


def canonical_bytes(value: object) -> bytes:
    """Serialize scientific JSON identically across repeated runs."""
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def digest(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def validate_source(package: Path, repository: Path) -> None:
    if not package.is_file() or package.stat().st_size != PACKAGE_SIZE:
        raise ContractError("official package is absent or has the wrong byte size")
    if file_sha256(package) != PACKAGE_SHA256:
        raise ContractError("official package SHA-256 mismatch")
    actual = _git(repository, "rev-parse", "HEAD").strip()
    if actual != SOURCE_REVISION:
        raise ContractError("JIT-Fine repository revision mismatch")


def validate_rows(rows: Sequence[Mapping[str, object]]) -> dict[str, object]:
    if not rows:
        raise ContractError("dataset must not be empty")
    if tuple(rows[0]) != FEATURE_COLUMNS:
        raise ContractError("feature schema does not match the pinned schema")
    identities: set[tuple[str, str]] = set()
    missing = Counter()
    labels = Counter()
    for row in rows:
        if tuple(row) != FEATURE_COLUMNS:
            raise ContractError("all observations must have the exact schema")
        project, commit = row["project"], row["commit_hash"]
        if (
            project not in PROJECTS
            or not isinstance(commit, str)
            or not _SHA1.fullmatch(commit)
        ):
            raise ContractError("malformed project-qualified commit identity")
        identity = (project, commit)
        if identity in identities:
            raise ContractError("duplicate project-qualified commit identity")
        identities.add(identity)
        label = row["is_buggy_commit"]
        if label not in (0, 0.0, 1, 1.0):
            raise ContractError("target must be binary")
        labels[int(label)] += 1
        for field in (
            "parent_hashes",
            "author_date",
            "author_date_unix_timestamp",
            "commit_message",
        ):
            if row[field] is None or str(row[field]).strip() == "":
                missing[field] += 1
        try:
            int(str(row["author_date_unix_timestamp"]))
            datetime.strptime(str(row["author_date"]), "%a %b %d %H:%M:%S %Y %z")
        except (TypeError, ValueError) as error:
            raise ContractError("malformed author timestamp") from error
    return {
        "observations": len(rows),
        "positive": labels[1],
        "nominal_negative": labels[0],
        "missing": dict(sorted(missing.items())),
        "duplicate_identities": 0,
    }


def enforce_predictors(modality: str, fields: Iterable[str]) -> tuple[str, ...]:
    if modality not in ALLOWLIST:
        raise ContractError("unknown modality")
    normalized = tuple(fields)
    prohibited = DENYLIST.intersection(normalized)
    if prohibited:
        raise ContractError(f"prohibited predictors: {sorted(prohibited)}")
    unknown = set(normalized).difference(ALLOWLIST[modality])
    if unknown:
        raise ContractError(f"predictors are not allowlisted: {sorted(unknown)}")
    return normalized


@dataclass(frozen=True, slots=True)
class ResolvedCommit:
    project: str
    commit_hash: str
    parents: tuple[str, ...]
    author_timestamp: str
    committer_timestamp: str

    @property
    def identity(self) -> tuple[str, str]:
        return self.project, self.commit_hash


def _git(repository: Path, *arguments: str, input_text: str | None = None) -> str:
    result = subprocess.run(
        ("git", "-C", str(repository), *arguments),
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise ContractError(result.stderr.strip() or "Git command failed")
    return result.stdout


def resolve_project(
    project: str, commits: Sequence[str], repository: Path
) -> tuple[dict[str, ResolvedCommit], tuple[str, ...]]:
    """Resolve commit metadata without checking out or modifying the repository."""
    if project not in PROJECTS:
        raise ContractError("unknown project")
    query = "".join(f"{item}\n" for item in commits)
    checked = _git(
        repository, "cat-file", "--batch-check", input_text=query
    ).splitlines()
    available = [line.split()[0] for line in checked if not line.endswith(" missing")]
    unresolved = tuple(sorted(set(commits).difference(available)))
    resolved: dict[str, ResolvedCommit] = {}
    if available:
        process = subprocess.run(
            ("git", "-C", str(repository), "cat-file", "--batch"),
            input="".join(f"{item}\n" for item in available).encode(),
            capture_output=True,
            check=False,
        )
        if process.returncode:
            raise ContractError(process.stderr.decode(errors="replace"))
        output = io.BytesIO(process.stdout)
        for _ in available:
            header = output.readline().decode().strip().split()
            if len(header) != 3 or header[1] != "commit":
                raise ContractError("Git object is not a commit")
            commit, size = header[0], int(header[2])
            payload = output.read(size).decode("utf-8", errors="replace")
            output.read(1)
            commit_headers = payload.split("\n\n", 1)[0].splitlines()
            parents = tuple(
                line.removeprefix("parent ")
                for line in commit_headers
                if line.startswith("parent ")
            )
            author_line = next(
                line for line in commit_headers if line.startswith("author ")
            )
            committer_line = next(
                line for line in commit_headers if line.startswith("committer ")
            )
            author_parts = author_line.rsplit(" ", 2)
            committer_parts = committer_line.rsplit(" ", 2)
            resolved[commit] = ResolvedCommit(
                project,
                commit,
                parents,
                f"{int(author_parts[-2]):020d} {author_parts[-1]}",
                f"{int(committer_parts[-2]):020d} {committer_parts[-1]}",
            )
    return resolved, unresolved


def validate_parent(record: Mapping[str, object], resolved: ResolvedCommit) -> bool:
    supplied = tuple(str(record["parent_hashes"]).split())
    return supplied == resolved.parents


def write_canonical(path: Path, value: Mapping[str, object]) -> str:
    payload = canonical_bytes(value)
    path.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()


def strict_temporal_membership(
    rows: Sequence[Mapping[str, object]],
    timestamps: Mapping[tuple[str, str], str],
    fractions: tuple[float, float, float] = (0.70, 0.15, 0.15),
) -> dict[str, tuple[tuple[str, str], ...]]:
    """Design-only project-aware contiguous split with SHA tie breaking."""
    if abs(sum(fractions) - 1.0) > 1e-12 or any(value <= 0 for value in fractions):
        raise ContractError("invalid temporal fractions")
    result = {"train": [], "validation": [], "test": []}
    for project in PROJECTS:
        identities = [
            (project, str(row["commit_hash"]))
            for row in rows
            if row["project"] == project
        ]
        ordered = sorted(identities, key=lambda item: (timestamps[item], item[1]))
        train_end = int(len(ordered) * fractions[0])
        validation_end = train_end + int(len(ordered) * fractions[1])
        result["train"].extend(ordered[:train_end])
        result["validation"].extend(ordered[train_end:validation_end])
        result["test"].extend(ordered[validation_end:])
    return {key: tuple(value) for key, value in result.items()}
