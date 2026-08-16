"""Fail-closed tests for canonical JIT-Defects4J materialization."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from dataset.jit_defects4j_materialization import (
    CODE_FIELDS,
    MISSING_TEXT_SENTINEL,
    PROCESS_FIELDS,
    TEXT_FIELDS,
    ancestor_process_features,
    assign_split,
    canonical_jsonl,
    git_raw_diff,
    normalize_text,
    validate_predictor_schema,
    write_immutable,
)
from migration.jit_defects4j import ContractError, ResolvedCommit


def _resolved(project: str, commit: str, timestamp: str) -> ResolvedCommit:
    return ResolvedCommit(project, commit, (), timestamp, timestamp)


def _repo(path: Path) -> tuple[Path, str, str]:
    subprocess.run(("git", "init", str(path)), check=True, capture_output=True)
    subprocess.run(("git", "-C", str(path), "config", "user.name", "Test"), check=True)
    subprocess.run(
        ("git", "-C", str(path), "config", "user.email", "test@example.test"),
        check=True,
    )
    file = path / "x.txt"
    file.write_text("one\n", encoding="utf-8")
    subprocess.run(("git", "-C", str(path), "add", "x.txt"), check=True)
    subprocess.run(
        ("git", "-C", str(path), "commit", "-m", "one"), check=True, capture_output=True
    )
    parent = subprocess.check_output(
        ("git", "-C", str(path), "rev-parse", "HEAD"), text=True
    ).strip()
    file.write_text("one\ntwo\n", encoding="utf-8")
    subprocess.run(
        ("git", "-C", str(path), "commit", "-am", "two"),
        check=True,
        capture_output=True,
    )
    child = subprocess.check_output(
        ("git", "-C", str(path), "rev-parse", "HEAD"), text=True
    ).strip()
    return path, parent, child


def test_project_aware_temporal_split_is_deterministic_and_exact() -> None:
    rows = []
    resolved = {}
    for project in ("ant-ivy", "commons-bcel"):
        for index, letter in enumerate("jihgfedcba"):
            commit = letter * 40
            rows.append({"project": project, "commit_hash": commit})
            resolved[(project, commit)] = _resolved(
                project, commit, f"{index:020d} +0000"
            )
    one = assign_split(rows, resolved)
    two = assign_split(list(reversed(rows)), resolved)
    assert one == two
    for project in ("ant-ivy", "commons-bcel"):
        assert (
            sum(split == "train" for (p, _), split in one.items() if p == project) == 7
        )
        assert (
            sum(split == "validation" for (p, _), split in one.items() if p == project)
            == 1
        )
        assert (
            sum(split == "test" for (p, _), split in one.items() if p == project) == 2
        )
    assert len(one) == len(set(one)) == 20


def test_target_is_not_part_of_split_assignment() -> None:
    rows = [
        {"project": "ant-ivy", "commit_hash": chr(97 + i) * 40, "target": i % 2}
        for i in range(10)
    ]
    resolved = {
        (row["project"], row["commit_hash"]): _resolved(
            row["project"], row["commit_hash"], f"{i:020d} +0000"
        )
        for i, row in enumerate(rows)
    }
    before = assign_split(rows, resolved)
    for row in rows:
        row["target"] = 1 - row["target"]
    assert assign_split(rows, resolved) == before


def test_predictor_denylist_fails_closed() -> None:
    validate_predictor_schema(
        {"code": CODE_FIELDS, "process": PROCESS_FIELDS, "text": TEXT_FIELDS}
    )
    with pytest.raises(ContractError):
        validate_predictor_schema(
            {
                "code": (*CODE_FIELDS, "target"),
                "process": PROCESS_FIELDS,
                "text": TEXT_FIELDS,
            }
        )
    with pytest.raises(ContractError):
        validate_predictor_schema(
            {
                "code": CODE_FIELDS,
                "process": PROCESS_FIELDS,
                "text": ("classification",),
            }
        )


def test_process_history_is_strictly_ancestor_only(tmp_path: Path) -> None:
    repository, parent, child = _repo(tmp_path / "repo")
    features = ancestor_process_features("ant-ivy", [parent, child], repository)
    assert features[parent]["prior_project_commit_count"] == 0
    assert features[child]["prior_project_commit_count"] == 1
    assert (
        features[parent]["prior_project_commit_count"]
        < features[child]["prior_project_commit_count"]
    )


def test_git_code_representation_uses_exact_diff(tmp_path: Path) -> None:
    repository, _, child = _repo(tmp_path / "repo")
    result = git_raw_diff(child, repository)
    assert result["files_added"] == 0
    assert result["files_deleted"] == 0
    assert result["files_modified"] == 1
    assert result["files_other"] == 0
    assert result["file_changes"][0]["path"] == "x.txt"
    assert result["file_changes"][0]["status"] == "M"


def test_missing_text_representation_is_deterministic() -> None:
    assert normalize_text(None) == (MISSING_TEXT_SENTINEL, True)
    assert normalize_text(" \n") == (MISSING_TEXT_SENTINEL, True)
    assert normalize_text(" message \n") == (" message \n", False)


def test_canonical_materialization_and_digest_are_reproducible(tmp_path: Path) -> None:
    one = canonical_jsonl([{"z": 1, "a": "á"}, {"b": [2, 1]}])
    two = canonical_jsonl([{"a": "á", "z": 1}, {"b": [2, 1]}])
    assert one == two
    path = tmp_path / "artifact.jsonl"
    digest = write_immutable(path, one)
    assert digest == hashlib.sha256(one).hexdigest()
    assert write_immutable(path, two) == digest
    with pytest.raises(ContractError, match="immutable"):
        write_immutable(path, b"changed\n")


def test_manifest_style_artifact_digest_integrity(tmp_path: Path) -> None:
    payload = canonical_jsonl([{"project": "ant-ivy", "commit_hash": "a" * 40}])
    artifact = tmp_path / "observations.jsonl"
    value = write_immutable(artifact, payload)
    manifest = {"artifacts": {artifact.name: {"sha256": value}}}
    assert (
        json.loads(json.dumps(manifest))["artifacts"][artifact.name]["sha256"]
        == hashlib.sha256(artifact.read_bytes()).hexdigest()
    )
