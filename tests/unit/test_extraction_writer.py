import csv
import hashlib
from datetime import datetime, timezone

import pytest

from extraction import (
    CommitRecord,
    ExtractionError,
    ExtractionOutputExistsError,
    ExtractionStage,
    write_commit_records,
)
from extraction.writer import COMMIT_COLUMNS


def _record(subject="subject") -> CommitRecord:
    timestamp = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return CommitRecord(
        "a" * 40,
        ("b" * 40,),
        "Author",
        "author@example.test",
        timestamp,
        "Committer",
        "committer@example.test",
        timestamp,
        subject,
        "body, preserved\nwith newline",
    )


def test_deterministic_columns_manifest_count_and_checksum(tmp_path) -> None:
    output = tmp_path / "commits.csv"
    manifest = write_commit_records(
        [_record()],
        output,
        repository_path=tmp_path,
        repository_head="a" * 40,
        extracted_at=datetime(2024, 1, 2, tzinfo=timezone.utc),
    )
    with output.open(encoding="utf-8", newline="") as source:
        rows = list(csv.reader(source))
    assert tuple(rows[0]) == COMMIT_COLUMNS
    assert rows[1][-1] == "body, preserved\nwith newline"
    assert manifest.record_count == 1
    assert manifest.extraction_stage is ExtractionStage.COMMITS
    assert manifest.checksum == hashlib.sha256(output.read_bytes()).hexdigest()


def test_overwrite_protection_and_optional_overwrite(tmp_path) -> None:
    output = tmp_path / "commits.csv"
    kwargs = {"repository_path": tmp_path, "repository_head": "a" * 40}
    write_commit_records([_record()], output, **kwargs)
    with pytest.raises(ExtractionOutputExistsError):
        write_commit_records([_record("second")], output, **kwargs)
    write_commit_records([_record("second")], output, overwrite=True, **kwargs)
    assert "second" in output.read_text(encoding="utf-8")


def test_parent_directories_are_created_only_when_requested(tmp_path) -> None:
    output = tmp_path / "nested" / "commits.csv"
    kwargs = {"repository_path": tmp_path, "repository_head": "a" * 40}
    with pytest.raises(Exception):
        write_commit_records([_record()], output, **kwargs)
    write_commit_records([_record()], output, create_parents=True, **kwargs)
    assert output.is_file()


def test_governance_output_paths_are_protected() -> None:
    project_root = __import__("pathlib").Path(__file__).resolve().parents[2]
    with pytest.raises(ExtractionError):
        write_commit_records(
            [_record()],
            project_root / "docs" / "commits.csv",
            repository_path=project_root,
            repository_head="a" * 40,
        )
