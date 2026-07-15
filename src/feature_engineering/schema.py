"""Immutable contracts for deterministic commit-level feature tables."""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class FeatureModality(Enum):
    """Supported feature-table modalities."""

    CODE = "code"
    PROCESS = "process"
    TEXT = "text"


@dataclass(frozen=True)
class CodeFeatureRecord:
    """Deterministic line-change features for one commit."""

    commit_hash: str
    lines_added: int
    lines_deleted: int
    lines_changed: int
    changed_file_count: int


@dataclass(frozen=True)
class ProcessFeatureRecord:
    """Deterministic commit-process descriptors for one commit."""

    commit_hash: str
    parent_count: int
    is_merge_commit: int
    author_is_committer: int


@dataclass(frozen=True)
class TextFeatureRecord:
    """Rule-based structural features from one commit message."""

    commit_hash: str
    character_count: int
    word_count: int
    line_count: int
    non_whitespace_character_count: int


@dataclass(frozen=True)
class FeatureArtifact:
    """Deterministic provenance for a written feature table."""

    path: Path
    modality: FeatureModality
    row_count: int
    column_names: tuple[str, ...]
    checksum: str


class FeatureEngineeringError(Exception):
    """Raised when feature input or output violates the layer contract."""

