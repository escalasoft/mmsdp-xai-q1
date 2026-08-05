"""Offline commit extraction from a deterministic acquired Git snapshot."""

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest

from extraction.qt_commit_extraction import (
    QtCommitExtractionError,
    QtCommitExtractionSpecification,
    QtCommitExtractor,
)
from extraction.qt_repository_acquisition import (
    QtRepositoryAcquirer,
    QtRepositoryAcquisitionSpecification,
)

CANONICAL = "https://code.qt.io/qt/qtbase.git"


def git(repository: Path, *arguments: str, env: dict[str, str] | None = None) -> str:
    environment = {
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_TERMINAL_PROMPT": "0",
        "HOME": os.devnull,
        "LANG": "C",
        "LC_ALL": "C",
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
    }
    if env:
        environment.update(env)
    result = subprocess.run(
        ["git", *arguments],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )
    return result.stdout.strip()


@pytest.fixture
def acquired_repository(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    git(source, "init", "-q")
    git(source, "symbolic-ref", "HEAD", "refs/heads/dev")
    git(source, "config", "user.name", "Scientific Author")
    git(source, "config", "user.email", "author@example.invalid")
    dates = {
        "GIT_AUTHOR_DATE": "2001-01-01T00:00:00+0530",
        "GIT_COMMITTER_DATE": "2001-01-01T01:00:00+0530",
    }
    (source / "one.txt").write_text("one\n", encoding="utf-8")
    git(source, "add", "one.txt")
    git(source, "commit", "-q", "-m", "first", env=dates)
    first = git(source, "rev-parse", "HEAD")
    dates = {
        "GIT_AUTHOR_DATE": "2001-01-02T00:00:00-0300",
        "GIT_COMMITTER_DATE": "2001-01-02T01:00:00-0300",
    }
    (source / "two.txt").write_text("two\n", encoding="utf-8")
    git(source, "add", "two.txt")
    git(source, "commit", "-q", "-m", "second", "-m", "body", env=dates)
    second = git(source, "rev-parse", "HEAD")
    remote = tmp_path / "qtbase.git"
    git(tmp_path, "clone", "-q", "--bare", str(source), str(remote))
    specification = QtRepositoryAcquisitionSpecification._for_local_test(
        repository_name="qtbase",
        canonical_repository_url=CANONICAL,
        transport_repository_url=str(remote),
        requested_reference=second,
        default_branch="dev",
        acquisition_policy_version="1.0.0",
        allowed_hash_algorithms=("sha1", "sha256"),
        metadata={},
    )
    clone = tmp_path / "acquired"
    acquisition = QtRepositoryAcquirer().acquire(specification, clone)
    return clone, acquisition, first, second


def test_artifact_is_deterministic_complete_and_oldest_first(
    tmp_path: Path, acquired_repository
) -> None:
    repository, acquisition, first, second = acquired_repository
    policy = QtCommitExtractionSpecification("1.0.0")
    first_output = tmp_path / "commits-one.json"
    second_output = tmp_path / "commits-two.json"
    one = QtCommitExtractor().extract(acquisition, repository, first_output, policy)
    two = QtCommitExtractor().extract(acquisition, repository, second_output, policy)

    assert [record.commit_id for record in one.records] == [first, second]
    assert one.records[1].parent_ids == (first,)
    assert one.records[0].authored_at.endswith("+05:30")
    assert one.records[1].message == "second\n\nbody\n"
    assert len(one.records[0].commit_id) == 40
    assert first_output.read_bytes() == second_output.read_bytes()
    assert one.artifact.content_digest == two.artifact.content_digest
    assert (
        one.artifact.content_digest
        == hashlib.sha256(first_output.read_bytes()).hexdigest()
    )
    payload = json.loads(first_output.read_text(encoding="utf-8"))
    assert payload["ordering_policy"] == "topological-oldest-first-v1"
    assert "issue" not in payload and "diff" not in payload


def test_exact_acquired_revision_is_used_even_when_head_moves(
    tmp_path: Path, acquired_repository
) -> None:
    repository, acquisition, _, second = acquired_repository
    git(repository, "config", "user.name", "Later Author")
    git(repository, "config", "user.email", "later@example.invalid")
    git(repository, "checkout", "-q", "-b", "later", second)
    (repository / "later.txt").write_text("later\n", encoding="utf-8")
    git(repository, "add", "later.txt")
    git(
        repository,
        "commit",
        "-q",
        "-m",
        "must not be extracted",
        env={
            "GIT_AUTHOR_DATE": "2001-01-03T00:00:00+0000",
            "GIT_COMMITTER_DATE": "2001-01-03T00:00:00+0000",
        },
    )
    result = QtCommitExtractor().extract(
        acquisition,
        repository,
        tmp_path / "anchored.json",
        QtCommitExtractionSpecification("1.0.0"),
    )
    assert len(result.records) == 2
    assert result.records[-1].commit_id == second


def test_existing_artifact_is_never_overwritten(
    tmp_path: Path, acquired_repository
) -> None:
    repository, acquisition, _, _ = acquired_repository
    output = tmp_path / "commits.json"
    output.write_text("keep", encoding="utf-8")
    with pytest.raises(QtCommitExtractionError, match="already exists"):
        QtCommitExtractor().extract(
            acquisition,
            repository,
            output,
            QtCommitExtractionSpecification("1.0.0"),
        )
    assert output.read_text(encoding="utf-8") == "keep"
