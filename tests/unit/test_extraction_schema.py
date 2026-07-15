from dataclasses import FrozenInstanceError
from datetime import datetime, timezone

import pytest

from extraction.schema import CommitRecord, ExtractionStage


def test_extraction_stages_are_raw_only() -> None:
    assert {stage.value for stage in ExtractionStage} == {"commits", "diff_stats"}


def test_commit_record_is_immutable() -> None:
    record = CommitRecord(
        "a" * 40,
        (),
        "Author",
        "author@example.test",
        datetime.now(timezone.utc),
        "Committer",
        "committer@example.test",
        datetime.now(timezone.utc),
        "subject",
        "body",
    )
    with pytest.raises(FrozenInstanceError):
        record.subject = "changed"  # type: ignore[misc]
