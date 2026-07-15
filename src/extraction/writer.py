"""Deterministic, atomic CSV writers for raw extraction records."""

import csv
import hashlib
import os
import tempfile
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

from .git_client import ExtractionError, ExtractionOutputExistsError
from .schema import (
    CommitRecord,
    DiffStatRecord,
    ExtractionManifest,
    ExtractionStage,
)

COMMIT_COLUMNS = (
    "commit_hash",
    "parent_hashes",
    "author_name",
    "author_email",
    "authored_at",
    "committer_name",
    "committer_email",
    "committed_at",
    "subject",
    "body",
)
DIFF_STAT_COLUMNS = (
    "commit_hash",
    "file_path",
    "added_lines",
    "deleted_lines",
)
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_PROTECTED_OUTPUT_DIRECTORIES = (
    _PROJECT_ROOT / "docs",
    _PROJECT_ROOT / "reference",
)


def write_commit_records(
    records: Iterable[CommitRecord],
    output_path: str | Path,
    *,
    repository_path: str | Path,
    repository_head: str,
    overwrite: bool = False,
    create_parents: bool = False,
    extracted_at: datetime | None = None,
) -> ExtractionManifest:
    """Atomically write raw commit records in the stable contract order."""
    rows = (
        (
            record.commit_hash,
            " ".join(record.parent_hashes),
            record.author_name,
            record.author_email,
            record.authored_at.isoformat(),
            record.committer_name,
            record.committer_email,
            record.committed_at.isoformat(),
            record.subject,
            record.body,
        )
        for record in records
    )
    return _write_csv(
        rows,
        COMMIT_COLUMNS,
        output_path,
        repository_path=repository_path,
        repository_head=repository_head,
        stage=ExtractionStage.COMMITS,
        overwrite=overwrite,
        create_parents=create_parents,
        extracted_at=extracted_at,
    )


def write_diff_stat_records(
    records: Iterable[DiffStatRecord],
    output_path: str | Path,
    *,
    repository_path: str | Path,
    repository_head: str,
    overwrite: bool = False,
    create_parents: bool = False,
    extracted_at: datetime | None = None,
) -> ExtractionManifest:
    """Atomically write raw per-file diff statistics."""
    rows = (
        (record.commit_hash, record.file_path, record.added_lines, record.deleted_lines)
        for record in records
    )
    return _write_csv(
        rows,
        DIFF_STAT_COLUMNS,
        output_path,
        repository_path=repository_path,
        repository_head=repository_head,
        stage=ExtractionStage.DIFF_STATS,
        overwrite=overwrite,
        create_parents=create_parents,
        extracted_at=extracted_at,
    )


def _write_csv(
    rows: Iterable[tuple[object, ...]],
    columns: tuple[str, ...],
    output_path: str | Path,
    *,
    repository_path: str | Path,
    repository_head: str,
    stage: ExtractionStage,
    overwrite: bool,
    create_parents: bool,
    extracted_at: datetime | None,
) -> ExtractionManifest:
    destination = Path(output_path).resolve()
    if any(
        destination.is_relative_to(protected)
        for protected in _PROTECTED_OUTPUT_DIRECTORIES
    ):
        raise ExtractionError(
            f"Extraction output is prohibited in governance paths: {destination}"
        )
    if destination.exists() and not overwrite:
        raise ExtractionOutputExistsError(f"Extraction output exists: {destination}")
    if not destination.parent.exists():
        if not create_parents:
            raise ExtractionError(
                f"Output parent directory does not exist: {destination.parent}"
            )
        destination.parent.mkdir(parents=True)

    row_count = 0
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_name = temporary.name
            writer = csv.writer(temporary, lineterminator="\n")
            writer.writerow(columns)
            for row in rows:
                writer.writerow(row)
                row_count += 1
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_name, destination)
        temporary_name = None
    except (OSError, csv.Error) as error:
        raise ExtractionError(
            f"Unable to write extraction output: {destination}"
        ) from error
    finally:
        if temporary_name is not None:
            Path(temporary_name).unlink(missing_ok=True)

    checksum = hashlib.sha256(destination.read_bytes()).hexdigest()
    timestamp = extracted_at or datetime.now(UTC)
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ExtractionError("Manifest extraction timestamp must be timezone-aware")
    return ExtractionManifest(
        repository_path=Path(repository_path).resolve(),
        repository_head=repository_head,
        extraction_stage=stage,
        extracted_at=timestamp,
        record_count=row_count,
        output_path=destination,
        checksum=checksum,
    )
