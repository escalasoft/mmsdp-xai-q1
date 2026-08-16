"""Canonical, fail-closed JIT-Defects4J multimodal materialization."""

from __future__ import annotations

import hashlib
import subprocess
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path

from migration.jit_defects4j import (
    DENYLIST,
    PACKAGE_SHA256,
    PACKAGE_SIZE,
    PROJECTS,
    SOURCE_REVISION,
    ContractError,
    ResolvedCommit,
    canonical_bytes,
    strict_temporal_membership,
)

DATASET_VERSION = "1.0.0"
SCHEMA_VERSION = "jit-defects4j-canonical-dataset-1.0.0"
MISSING_TEXT_SENTINEL = "<MISSING_COMMIT_MESSAGE>"
PARTITIONS = ("train", "validation", "test")
CODE_FIELDS = (
    "file_changes",
    "files_added",
    "files_deleted",
    "files_modified",
    "files_other",
)
PROCESS_FIELDS = (
    "parent_count",
    "is_merge_commit",
    "has_prior_history",
    "prior_project_commit_count",
)
TEXT_FIELDS = ("raw_commit_message",)


def canonical_jsonl(rows: Iterable[Mapping[str, object]]) -> bytes:
    """Serialize records with stable key ordering and one LF per record."""
    return b"".join(canonical_bytes(dict(row)) for row in rows)


def write_immutable(path: Path, payload: bytes) -> str:
    """Write once, or verify an existing versioned artifact byte for byte."""
    if path.exists() and path.read_bytes() != payload:
        raise ContractError(f"immutable artifact disagrees with rerun: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()


def normalize_text(value: object) -> tuple[str, bool]:
    """Preserve raw text, replacing absent/blank values with a fixed sentinel."""
    if value is None or not str(value).strip():
        return MISSING_TEXT_SENTINEL, True
    return str(value), False


def validate_predictor_schema(
    schemas: Mapping[str, Sequence[str]], denylist: Iterable[str] = DENYLIST
) -> None:
    """Reject prohibited, unknown, duplicate, or cross-modality predictors."""
    expected = {"code": CODE_FIELDS, "process": PROCESS_FIELDS, "text": TEXT_FIELDS}
    seen: set[str] = set()
    prohibited_names = set(denylist)
    for modality, required in expected.items():
        actual = tuple(schemas.get(modality, ()))
        if actual != required or len(actual) != len(set(actual)):
            raise ContractError(f"{modality} predictor schema is not canonical")
        prohibited = prohibited_names.intersection(actual)
        if prohibited:
            raise ContractError(f"prohibited predictors: {sorted(prohibited)}")
        overlap = seen.intersection(actual)
        if overlap:
            raise ContractError(
                f"predictors cross modality boundaries: {sorted(overlap)}"
            )
        seen.update(actual)


def assign_split(
    rows: Sequence[Mapping[str, object]],
    resolved: Mapping[tuple[str, str], ResolvedCommit],
) -> dict[tuple[str, str], str]:
    timestamps = {
        identity: item.committer_timestamp for identity, item in resolved.items()
    }
    membership = strict_temporal_membership(rows, timestamps)
    assigned: dict[tuple[str, str], str] = {}
    for partition, identities in membership.items():
        for identity in identities:
            if identity in assigned:
                raise ContractError("project-qualified identity crossed partitions")
            assigned[identity] = partition
    expected = {(str(row["project"]), str(row["commit_hash"])) for row in rows}
    if set(assigned) != expected:
        raise ContractError("split membership is not total and exact")
    return assigned


def ancestor_process_features(
    project: str,
    observations: Sequence[str],
    repository: Path,
) -> dict[str, dict[str, int]]:
    """Compute history counts from ancestors(C), excluding C itself."""
    process = subprocess.run(
        (
            "git",
            "-C",
            str(repository),
            "rev-list",
            "--topo-order",
            "--reverse",
            "--parents",
            "--stdin",
        ),
        input="".join(f"{commit}\n" for commit in observations),
        text=True,
        capture_output=True,
        check=False,
    )
    if process.returncode:
        raise ContractError(process.stderr.strip() or "ancestor traversal failed")
    masks: dict[str, int] = {}
    indexes: dict[str, int] = {}
    result: dict[str, dict[str, int]] = {}
    observation_set = set(observations)
    for index, line in enumerate(process.stdout.splitlines()):
        values = line.split()
        commit, parents = values[0], values[1:]
        ancestor_mask = 0
        for parent in parents:
            if parent not in masks:
                raise ContractError("ancestor traversal was not parent-before-child")
            ancestor_mask |= masks[parent] | (1 << indexes[parent])
        masks[commit] = ancestor_mask
        indexes[commit] = index
        if commit in observation_set:
            result[commit] = {
                "parent_count": len(parents),
                "is_merge_commit": int(len(parents) > 1),
                "has_prior_history": int(bool(parents)),
                "prior_project_commit_count": ancestor_mask.bit_count(),
            }
    missing = observation_set.difference(result)
    if missing:
        raise ContractError(f"PROCESS history omitted observations: {len(missing)}")
    return result


def git_raw_diff(commit: str, repository: Path) -> dict[str, object]:
    """Extract exact current-vs-parent Git tree changes without blob hydration."""
    result = subprocess.run(
        (
            "git",
            "-C",
            str(repository),
            "diff-tree",
            "--root",
            "--raw",
            "--no-commit-id",
            "-r",
            "--no-renames",
            commit,
        ),
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        detail = result.stderr.strip() or "Git raw diff extraction failed"
        raise ContractError(f"Git raw diff failed for {commit}: {detail}")
    changes: list[dict[str, str]] = []
    statuses = Counter()
    for line in result.stdout.splitlines():
        metadata, separator, path = line.partition("\t")
        parts = metadata.removeprefix(":").split()
        if not separator or len(parts) != 5:
            raise ContractError("malformed Git raw diff output")
        old_mode, new_mode, old_blob, new_blob, status = parts
        statuses[status] += 1
        changes.append(
            {
                "path": path,
                "status": status,
                "old_mode": old_mode,
                "new_mode": new_mode,
                "old_blob": old_blob,
                "new_blob": new_blob,
            }
        )
    return {
        "file_changes": sorted(
            changes, key=lambda item: (item["path"], item["status"])
        ),
        "files_added": statuses["A"],
        "files_deleted": statuses["D"],
        "files_modified": statuses["M"],
        "files_other": sum(
            value for key, value in statuses.items() if key not in "ADM"
        ),
    }


def summarize(
    observations: Sequence[Mapping[str, object]],
) -> tuple[dict[str, object], list[dict[str, object]]]:
    global_counts: dict[str, object] = {}
    sparse: list[dict[str, object]] = []
    for scope, selected in [("global", observations)]:
        labels = Counter(int(row["target"]) for row in selected)
        global_counts = {
            "observations": len(selected),
            "positive": labels[1],
            "nominal_negative": labels[0],
            "positive_prevalence": labels[1] / len(selected),
        }
    per_project: dict[str, object] = {}
    for project in PROJECTS:
        per_project[project] = {}
        for partition in PARTITIONS:
            selected = [
                row
                for row in observations
                if row["project"] == project and row["split"] == partition
            ]
            labels = Counter(int(row["target"]) for row in selected)
            entry = {
                "observations": len(selected),
                "positive": labels[1],
                "nominal_negative": labels[0],
                "positive_prevalence": labels[1] / len(selected),
            }
            per_project[project][partition] = entry
            if labels[0] == 0 or labels[1] == 0:
                sparse.append({"project": project, "split": partition, **entry})
    split_counts = {}
    for partition in PARTITIONS:
        selected = [row for row in observations if row["split"] == partition]
        labels = Counter(int(row["target"]) for row in selected)
        split_counts[partition] = {
            "observations": len(selected),
            "positive": labels[1],
            "nominal_negative": labels[0],
            "positive_prevalence": labels[1] / len(selected),
        }
    global_counts["splits"] = split_counts
    global_counts["per_project"] = per_project
    return global_counts, sparse


def source_contract() -> dict[str, object]:
    return {
        "repository_revision": SOURCE_REVISION,
        "package_bytes": PACKAGE_SIZE,
        "package_sha256": PACKAGE_SHA256,
    }
