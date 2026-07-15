"""Implementation-independent contracts for immutable extraction records."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path


class ExtractionStage(Enum):
    """Raw extraction stage represented by an output artifact."""

    COMMITS = "commits"
    DIFF_STATS = "diff_stats"


@dataclass(frozen=True)
class CommitRecord:
    """Untransformed metadata for one Git commit."""

    commit_hash: str
    parent_hashes: tuple[str, ...]
    author_name: str
    author_email: str
    authored_at: datetime
    committer_name: str
    committer_email: str
    committed_at: datetime
    subject: str
    body: str


@dataclass(frozen=True)
class DiffStatRecord:
    """Raw Git line counts for one file changed by one commit."""

    commit_hash: str
    file_path: str
    added_lines: int
    deleted_lines: int


@dataclass(frozen=True)
class ExtractionManifest:
    """Provenance for one completed extraction artifact."""

    repository_path: Path
    repository_head: str
    extraction_stage: ExtractionStage
    extracted_at: datetime
    record_count: int
    output_path: Path
    checksum: str
