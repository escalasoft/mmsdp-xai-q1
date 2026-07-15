"""Safe, read-only adapter for a local Git work tree."""

import subprocess
from collections.abc import Sequence
from pathlib import Path


class ExtractionError(Exception):
    """Base exception for extraction-layer failures."""


class RepositoryNotFoundError(ExtractionError):
    """Raised when a repository path is not an existing directory."""


class InvalidGitRepositoryError(ExtractionError):
    """Raised when a directory is not a Git work tree."""


class GitCommandError(ExtractionError):
    """Raised when an allowed Git command fails."""


class GitCommandTimeoutError(ExtractionError):
    """Raised when an allowed Git command exceeds its timeout."""


class MalformedGitOutputError(ExtractionError):
    """Raised when Git emits output that violates an extraction contract."""


class ExtractionOutputExistsError(ExtractionError):
    """Raised when an extraction output would be overwritten."""


class GitClient:
    """Execute only the Git reads required by the extraction layer."""

    _ALLOWED_COMMANDS = {"rev-parse", "log", "show"}

    def __init__(self, repository_path: str | Path, *, timeout: float = 30.0):
        self.repository_path = Path(repository_path).resolve()
        self.timeout = timeout
        if not self.repository_path.is_dir():
            raise RepositoryNotFoundError(
                f"Repository directory not found: {self.repository_path}"
            )
        try:
            result = self._run_process(["rev-parse", "--is-inside-work-tree"])
        except GitCommandError as error:
            raise InvalidGitRepositoryError(
                f"Not a Git work tree: {self.repository_path}"
            ) from error
        if result.strip() != "true":
            raise InvalidGitRepositoryError(
                f"Not a Git work tree: {self.repository_path}"
            )

    def repository_head(self) -> str:
        """Return the full object name at repository HEAD."""
        head = self._run(["rev-parse", "--verify", "HEAD"]).strip()
        if not head:
            raise MalformedGitOutputError("Git returned an empty repository HEAD")
        return head

    def commit_log(self) -> str:
        """Return all commit metadata in deterministic Git history order."""
        format_spec = (
            "%x1e%H%x1f%P%x1f%an%x1f%ae%x1f%aI%x1f%cn%x1f%ce%x1f%cI%x1f%s%x1f%b"
        )
        return self._run(["log", "--topo-order", f"--format={format_spec}"])

    def diff_statistics(self, commit_hash: str) -> str:
        """Return NUL-delimited per-file numstat output for one commit."""
        if not commit_hash or commit_hash.startswith("-"):
            raise GitCommandError(
                "A commit object name must be non-empty and positional"
            )
        return self._run(
            [
                "show",
                "--format=",
                "--numstat",
                "--no-renames",
                "-z",
                commit_hash,
                "--",
            ]
        )

    def _run(self, arguments: Sequence[str]) -> str:
        if not arguments or arguments[0] not in self._ALLOWED_COMMANDS:
            raise GitCommandError(
                "Git command is not permitted by the read-only adapter"
            )
        return self._run_process(arguments)

    def _run_process(self, arguments: Sequence[str]) -> str:
        try:
            result = subprocess.run(
                ["git", *arguments],
                cwd=self.repository_path,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="strict",
                timeout=self.timeout,
            )
        except subprocess.TimeoutExpired as error:
            raise GitCommandTimeoutError(
                f"Git command timed out after {self.timeout} seconds: {arguments[0]}"
            ) from error
        except (OSError, UnicodeError) as error:
            raise GitCommandError(
                f"Unable to execute Git command: {arguments[0]}"
            ) from error
        if result.returncode != 0:
            detail = result.stderr.strip() or "no error output"
            raise GitCommandError(f"Git command failed ({arguments[0]}): {detail}")
        return result.stdout
