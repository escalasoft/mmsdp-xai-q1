from datetime import timedelta

import pytest

from extraction.commit_extractor import parse_commit_log, parse_diff_stats
from extraction.git_client import MalformedGitOutputError


def test_commit_metadata_parsing_preserves_parents_and_timezone() -> None:
    output = (
        "\x1eabc\x1fp1 p2\x1fA Name\x1fa@example.test\x1f"
        "2024-01-02T03:04:05+05:30\x1fC Name\x1fc@example.test\x1f"
        "2024-01-02T04:05:06-03:00\x1fSubject text\x1fBody text\n"
    )
    record = parse_commit_log(output)[0]
    assert record.parent_hashes == ("p1", "p2")
    assert record.author_name == "A Name"
    assert record.subject == "Subject text"
    assert record.body == "Body text"
    assert record.authored_at.utcoffset() == timedelta(hours=5, minutes=30)
    assert record.committed_at.tzinfo is not None


@pytest.mark.parametrize(
    "output",
    [
        "missing delimiter",
        "\x1etoo\x1ffew",
        (
            "\x1eabc\x1f\x1fA\x1fa\x1fbad\x1fC\x1fc\x1f"
            "2024-01-01T00:00:00+00:00\x1fs\x1fb"
        ),
    ],
)
def test_malformed_commit_output_is_rejected(output) -> None:
    with pytest.raises(MalformedGitOutputError):
        parse_commit_log(output)


def test_diff_statistics_parsing() -> None:
    records = parse_diff_stats("2\t1\tfile name.txt\x00", "abc")
    assert records[0].file_path == "file name.txt"
    assert records[0].added_lines == 2


def test_binary_diff_statistics_are_rejected() -> None:
    with pytest.raises(MalformedGitOutputError):
        parse_diff_stats("-\t-\timage.bin\x00", "abc")
