import os
import subprocess

import pytest

from extraction.git_client import (
    GitClient,
    GitCommandError,
    GitCommandTimeoutError,
    InvalidGitRepositoryError,
    RepositoryNotFoundError,
)


def test_missing_repository_path(tmp_path) -> None:
    with pytest.raises(RepositoryNotFoundError):
        GitClient(tmp_path / "missing")


def test_non_git_directory(tmp_path) -> None:
    with pytest.raises(InvalidGitRepositoryError):
        GitClient(tmp_path)


def test_valid_repository_and_head(tmp_path) -> None:
    subprocess.run(["git", "init", "-q", tmp_path], check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "commit", "--allow-empty", "-m", "first"],
        check=True,
        env={
            **os.environ,
            "GIT_AUTHOR_NAME": "Test",
            "GIT_AUTHOR_EMAIL": "test@example.test",
            "GIT_COMMITTER_NAME": "Test",
            "GIT_COMMITTER_EMAIL": "test@example.test",
        },
    )
    assert len(GitClient(tmp_path).repository_head()) == 40


def test_command_failure_is_explicit(tmp_path) -> None:
    subprocess.run(["git", "init", "-q", tmp_path], check=True)
    client = GitClient(tmp_path)
    with pytest.raises(GitCommandError):
        client.repository_head()


def test_command_timeout_with_controlled_double(tmp_path, monkeypatch) -> None:
    subprocess.run(["git", "init", "-q", tmp_path], check=True)
    client = GitClient(tmp_path)

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], kwargs["timeout"])

    monkeypatch.setattr(subprocess, "run", timeout)
    with pytest.raises(GitCommandTimeoutError):
        client.repository_head()


def test_adapter_rejects_mutating_command(tmp_path) -> None:
    subprocess.run(["git", "init", "-q", tmp_path], check=True)
    client = GitClient(tmp_path)
    with pytest.raises(GitCommandError):
        client._run(["checkout", "other"])
