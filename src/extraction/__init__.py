"""Stable public API for raw local Git extraction."""

from .commit_extractor import extract_commits, extract_diff_stats
from .git_client import (
    ExtractionError,
    ExtractionOutputExistsError,
    GitClient,
    GitCommandError,
    GitCommandTimeoutError,
    InvalidGitRepositoryError,
    MalformedGitOutputError,
    RepositoryNotFoundError,
)
from .schema import CommitRecord, DiffStatRecord, ExtractionManifest, ExtractionStage
from .writer import write_commit_records, write_diff_stat_records

__all__ = [
    "CommitRecord",
    "DiffStatRecord",
    "ExtractionError",
    "ExtractionManifest",
    "ExtractionOutputExistsError",
    "ExtractionStage",
    "GitClient",
    "GitCommandError",
    "GitCommandTimeoutError",
    "InvalidGitRepositoryError",
    "MalformedGitOutputError",
    "RepositoryNotFoundError",
    "extract_commits",
    "extract_diff_stats",
    "write_commit_records",
    "write_diff_stat_records",
]
