"""Offline integration tests against deterministic local Git repositories."""

import json
import os
import re
import subprocess
from pathlib import Path

import pytest

from extraction.qt_repository_acquisition import (
    QtRepositoryAcquirer,
    QtRepositoryAcquisitionSpecification,
)

CANONICAL = "https://code.qt.io/qt/qtbase.git"


def git(
    repository: Path, *arguments: str, environment: dict[str, str] | None = None
) -> str:
    env = {
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_TERMINAL_PROMPT": "0",
        "HOME": os.devnull,
        "LANG": "C",
        "LC_ALL": "C",
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
    }
    if environment:
        env.update(environment)
    result = subprocess.run(
        ["git", *arguments],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
        env=env,
        shell=False,
    )
    return result.stdout.strip()


@pytest.fixture
def local_remote(tmp_path: Path) -> tuple[Path, str, str]:
    source = tmp_path / "source"
    source.mkdir()
    git(source, "init")
    git(source, "symbolic-ref", "HEAD", "refs/heads/dev")
    git(source, "config", "user.name", "Deterministic Test Author")
    git(source, "config", "user.email", "test-author@example.invalid")
    dates = {
        "GIT_AUTHOR_DATE": "2001-01-01T00:00:00+0000",
        "GIT_COMMITTER_DATE": "2001-01-01T00:00:00+0000",
    }
    (source / "first.txt").write_text("first\n", encoding="utf-8")
    git(source, "add", "first.txt")
    git(source, "commit", "-m", "first", environment=dates)
    first = git(source, "rev-parse", "HEAD")
    git(source, "tag", "v1-test", first)
    (source / "second.txt").write_text("second\n", encoding="utf-8")
    git(source, "add", "second.txt")
    dates = {
        "GIT_AUTHOR_DATE": "2001-01-02T00:00:00+0000",
        "GIT_COMMITTER_DATE": "2001-01-02T00:00:00+0000",
    }
    git(source, "commit", "-m", "second", environment=dates)
    second = git(source, "rev-parse", "HEAD")
    remote = tmp_path / "qtbase-local.git"
    git(tmp_path, "clone", "--bare", str(source), str(remote))
    return remote, first, second


def local_spec(
    remote: Path, reference: str, **changes: object
) -> QtRepositoryAcquisitionSpecification:
    values: dict[str, object] = {
        "repository_name": "qtbase",
        "canonical_repository_url": CANONICAL,
        "transport_repository_url": str(remote),
        "requested_reference": reference,
        "default_branch": "dev",
        "acquisition_policy_version": "1.0.0",
        "allowed_hash_algorithms": ("sha1", "sha256"),
        "metadata": {},
    }
    values.update(changes)
    return QtRepositoryAcquisitionSpecification._for_local_test(**values)


@pytest.mark.parametrize("reference_selector", ["dev", "v1-test", "commit"])
def test_branch_tag_and_commit_resolve_to_full_immutable_revision(
    tmp_path: Path,
    local_remote: tuple[Path, str, str],
    reference_selector: str,
) -> None:
    remote, first, second = local_remote
    reference = first if reference_selector == "commit" else reference_selector
    expected = first if reference_selector in {"v1-test", "commit"} else second
    result = QtRepositoryAcquirer().acquire(
        local_spec(remote, reference), tmp_path / f"clone-{reference_selector}"
    )
    assert result.resolved_revision == expected
    assert re.fullmatch(r"[0-9a-f]{40}", result.resolved_revision)
    assert result.object_hash_algorithm == "sha1"
    assert result.repository_snapshot.repository_revision == result.resolved_revision
    assert (
        result.acquisition_artifact.content_digest
        == result.repository_snapshot.snapshot_digest
    )
    serialized = json.dumps(result.to_dict(), sort_keys=True)
    assert str(tmp_path) not in serialized
    assert result.transport_repository_url == "local-test-transport"
    assert result.specification.transport_repository_url == "local-test-transport"
    assert result.specification._local_transport_path is None
    assert str(tmp_path) not in repr(result)
    assert "runtime_timestamp" not in serialized
    assert "test-author" not in serialized
    assert result.command_evidence == tuple(sorted(set(result.command_evidence)))


def test_existing_valid_repository_is_accepted(
    local_remote: tuple[Path, str, str], tmp_path: Path
) -> None:
    remote, _, second = local_remote
    destination = tmp_path / "existing"
    git(tmp_path, "clone", str(remote), str(destination))
    result = QtRepositoryAcquirer().acquire(local_spec(remote, "dev"), destination)
    assert result.resolved_revision == second


def test_wrong_existing_repository_identity_is_rejected(
    local_remote: tuple[Path, str, str], tmp_path: Path
) -> None:
    remote, _, _ = local_remote
    other = tmp_path / "other.git"
    git(tmp_path, "clone", "--bare", str(remote), str(other))
    destination = tmp_path / "wrong"
    git(tmp_path, "clone", str(other), str(destination))
    with pytest.raises(RuntimeError, match="does not correspond"):
        QtRepositoryAcquirer().acquire(local_spec(remote, "dev"), destination)


def test_non_git_nonempty_destination_is_rejected(
    local_remote: tuple[Path, str, str], tmp_path: Path
) -> None:
    remote, _, _ = local_remote
    destination = tmp_path / "occupied"
    destination.mkdir()
    (destination / "keep.txt").write_text("keep", encoding="utf-8")
    with pytest.raises(ValueError, match="absent or empty"):
        QtRepositoryAcquirer().acquire(local_spec(remote, "dev"), destination)


def test_non_commit_object_and_unresolved_reference_are_rejected(
    local_remote: tuple[Path, str, str], tmp_path: Path
) -> None:
    remote, _, _ = local_remote
    with pytest.raises(RuntimeError, match="could not be resolved"):
        QtRepositoryAcquirer().acquire(
            local_spec(remote, "missing"), tmp_path / "missing"
        )

    destination = tmp_path / "blob-destination"
    git(tmp_path, "clone", str(remote), str(destination))
    blob = git(destination, "hash-object", "first.txt")
    with pytest.raises(RuntimeError, match="could not be resolved"):
        QtRepositoryAcquirer().acquire(local_spec(remote, blob), destination)


def test_identity_digest_is_deterministic_and_metadata_independent(
    local_remote: tuple[Path, str, str], tmp_path: Path
) -> None:
    remote, first, second = local_remote
    one = QtRepositoryAcquirer().acquire(local_spec(remote, first), tmp_path / "one")
    two = QtRepositoryAcquirer().acquire(
        local_spec(remote, first, metadata={"description": "changed"}), tmp_path / "two"
    )
    three = QtRepositoryAcquirer().acquire(
        local_spec(remote, second), tmp_path / "three"
    )
    assert one.repository_identity_digest == two.repository_identity_digest
    assert one.repository_identity_digest != three.repository_identity_digest


def test_sha256_repository_when_supported(tmp_path: Path) -> None:
    probe = subprocess.run(
        ["git", "init", "--object-format=sha256", str(tmp_path / "sha256-source")],
        check=False,
        capture_output=True,
        text=True,
    )
    if probe.returncode:
        pytest.skip("installed Git does not support SHA-256 repositories")
    source = tmp_path / "sha256-source"
    git(source, "config", "user.name", "Test Author")
    git(source, "config", "user.email", "test@example.invalid")
    (source / "content.txt").write_text("content\n", encoding="utf-8")
    git(source, "add", "content.txt")
    git(
        source,
        "commit",
        "-m",
        "sha256",
        environment={
            "GIT_AUTHOR_DATE": "2001-01-01T00:00:00+0000",
            "GIT_COMMITTER_DATE": "2001-01-01T00:00:00+0000",
        },
    )
    revision = git(source, "rev-parse", "HEAD")
    result = QtRepositoryAcquirer().acquire(
        local_spec(source, revision), tmp_path / "sha256-clone"
    )
    assert result.object_hash_algorithm == "sha256"
    assert result.resolved_revision == revision
