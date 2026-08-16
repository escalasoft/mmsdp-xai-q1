"""Fail-closed tests for the JIT-Defects4J migration preparation contract."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

import migration.jit_defects4j as contract
from migration.jit_defects4j import (
    FEATURE_COLUMNS,
    PACKAGE_SHA256,
    PROJECTS,
    SOURCE_REVISION,
    ContractError,
    canonical_bytes,
    digest,
    enforce_predictors,
    resolve_project,
    strict_temporal_membership,
    validate_parent,
    validate_rows,
    validate_source,
)


def row(
    project: str = "ant-ivy", commit: str = "a" * 40, label: int = 0
) -> dict[str, object]:
    values = {name: "1" for name in FEATURE_COLUMNS}
    values.update(
        {
            "project": project,
            "commit_hash": commit,
            "parent_hashes": "b" * 40,
            "author_date": "Thu Jun 16 18:36:46 2005 +0000",
            "author_date_unix_timestamp": "1118947006",
            "commit_message": "message",
            "is_buggy_commit": float(label),
        }
    )
    return values


def test_immutable_source_constants_are_exact() -> None:
    assert SOURCE_REVISION == "584799fdec6095ab75a45fd2a5f8db5b12163aa5"
    assert (
        PACKAGE_SHA256
        == "9e5ca1a393b70ee7e87c410b162005958775f3f3732f9f83da9dd24a7dfe2b47"
    )
    assert len(PROJECTS) == 21


def test_source_revision_and_package_digest_are_enforced(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "source"
    subprocess.run(["git", "init", str(repository)], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(repository), "config", "user.name", "Audit"], check=True
    )
    subprocess.run(
        ["git", "-C", str(repository), "config", "user.email", "audit@example.test"],
        check=True,
    )
    package = repository / "data.zip"
    package.write_bytes(b"pinned-package")
    subprocess.run(["git", "-C", str(repository), "add", "data.zip"], check=True)
    subprocess.run(
        ["git", "-C", str(repository), "commit", "-m", "source"],
        check=True,
        capture_output=True,
    )
    revision = subprocess.check_output(
        ["git", "-C", str(repository), "rev-parse", "HEAD"], text=True
    ).strip()
    monkeypatch.setattr(contract, "PACKAGE_SIZE", package.stat().st_size)
    monkeypatch.setattr(
        contract, "PACKAGE_SHA256", hashlib.sha256(package.read_bytes()).hexdigest()
    )
    monkeypatch.setattr(contract, "SOURCE_REVISION", revision)
    validate_source(package, repository)
    package.write_bytes(b"tampered-packg")
    with pytest.raises(ContractError, match="SHA-256"):
        validate_source(package, repository)


def test_schema_identity_uniqueness_and_target() -> None:
    result = validate_rows([row(label=1), row(commit="c" * 40)])
    assert result["positive"] == 1
    assert result["nominal_negative"] == 1
    with pytest.raises(ContractError, match="duplicate"):
        validate_rows([row(), row()])
    with pytest.raises(ContractError, match="binary"):
        validate_rows([row(label=3)])


@pytest.mark.parametrize("mutation", ["schema", "project", "commit", "timestamp"])
def test_malformed_source_is_rejected(mutation: str) -> None:
    value = row()
    if mutation == "schema":
        value.pop("fix")
    elif mutation == "project":
        value["project"] = "unknown"
    elif mutation == "commit":
        value["commit_hash"] = "not-a-sha"
    else:
        value["author_date"] = "tomorrow"
    with pytest.raises(ContractError):
        validate_rows([value])


def test_leakage_denylist_and_target_exclusion() -> None:
    assert enforce_predictors("text", ["masked_commit_message"]) == (
        "masked_commit_message",
    )
    with pytest.raises(ContractError, match="prohibited"):
        enforce_predictors("process", ["is_buggy_commit"])
    with pytest.raises(ContractError, match="allowlisted"):
        enforce_predictors("code", ["commit_message"])


def test_canonical_serialization_and_repeated_digest_are_identical() -> None:
    one = {"z": [2, 1], "a": "á"}
    two = {"a": "á", "z": [2, 1]}
    assert canonical_bytes(one) == canonical_bytes(two)
    assert (
        digest(one) == digest(two) == hashlib.sha256(canonical_bytes(one)).hexdigest()
    )
    assert json.loads(canonical_bytes(one)) == one


def test_project_aware_temporal_order_and_sha_tie_break() -> None:
    rows = [row(commit="c" * 40), row(commit="a" * 40, label=1), row(commit="b" * 40)]
    timestamps = {
        ("ant-ivy", item["commit_hash"]): "2000-01-01T00:00:00+00:00" for item in rows
    }
    split = strict_temporal_membership(rows, timestamps, (1 / 3, 1 / 3, 1 / 3))
    assert split["train"] == (("ant-ivy", "a" * 40),)
    assert split["validation"] == (("ant-ivy", "b" * 40),)
    assert split["test"] == (("ant-ivy", "c" * 40),)


def test_repository_and_parent_resolution(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    subprocess.run(["git", "init", str(repo)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Audit"], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "audit@example.test"],
        check=True,
    )
    file = repo / "x.txt"
    file.write_text("one\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "x.txt"], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-m", "one"], check=True, capture_output=True
    )
    parent = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
    ).strip()
    file.write_text("two\n", encoding="utf-8")
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-am", "two"],
        check=True,
        capture_output=True,
    )
    commit = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
    ).strip()
    resolved, missing = resolve_project("ant-ivy", [commit, "f" * 40], repo)
    assert missing == ("f" * 40,)
    assert validate_parent({"parent_hashes": parent}, resolved[commit])
    assert not validate_parent({"parent_hashes": ""}, resolved[commit])
