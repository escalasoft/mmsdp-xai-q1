"""Parsing and orchestration for raw local Git extraction."""

from datetime import datetime

from .git_client import GitClient, MalformedGitOutputError
from .schema import CommitRecord, DiffStatRecord

_RECORD_SEPARATOR = "\x1e"
_FIELD_SEPARATOR = "\x1f"
_COMMIT_FIELD_COUNT = 10


def extract_commits(client: GitClient) -> tuple[CommitRecord, ...]:
    """Extract immutable commit metadata records from ``client``."""
    return parse_commit_log(client.commit_log())


def extract_diff_stats(
    client: GitClient, commit_hash: str
) -> tuple[DiffStatRecord, ...]:
    """Extract immutable per-file line counts for one commit."""
    return parse_diff_stats(client.diff_statistics(commit_hash), commit_hash)


def parse_commit_log(output: str) -> tuple[CommitRecord, ...]:
    """Parse delimiter-framed Git log output without interpreting message text."""
    if not output:
        return ()
    if not output.startswith(_RECORD_SEPARATOR):
        raise MalformedGitOutputError(
            "Commit log is missing its first record delimiter"
        )

    records = []
    for raw_record in output.split(_RECORD_SEPARATOR)[1:]:
        raw_record = raw_record.removesuffix("\n")
        fields = raw_record.split(_FIELD_SEPARATOR)
        if len(fields) != _COMMIT_FIELD_COUNT:
            raise MalformedGitOutputError(
                "Commit log record does not contain the required fields"
            )
        (
            commit_hash,
            parents,
            author_name,
            author_email,
            authored_text,
            committer_name,
            committer_email,
            committed_text,
            subject,
            body,
        ) = fields
        if not commit_hash:
            raise MalformedGitOutputError("Commit log record has an empty commit hash")
        records.append(
            CommitRecord(
                commit_hash=commit_hash,
                parent_hashes=tuple(parents.split()) if parents else (),
                author_name=author_name,
                author_email=author_email,
                authored_at=_parse_timestamp(authored_text),
                committer_name=committer_name,
                committer_email=committer_email,
                committed_at=_parse_timestamp(committed_text),
                subject=subject,
                body=body,
            )
        )
    return tuple(records)


def parse_diff_stats(output: str, commit_hash: str) -> tuple[DiffStatRecord, ...]:
    """Parse NUL-delimited ``git show --numstat`` output."""
    if not output:
        return ()
    if not output.endswith("\x00"):
        raise MalformedGitOutputError("Diff statistics are not NUL terminated")
    records = []
    for entry in output[:-1].split("\x00"):
        fields = entry.split("\t", 2)
        if len(fields) != 3 or not fields[2]:
            raise MalformedGitOutputError("Malformed per-file diff statistics")
        added, deleted, file_path = fields
        try:
            added_lines = int(added)
            deleted_lines = int(deleted)
        except ValueError as error:
            raise MalformedGitOutputError(
                "Diff statistics contain non-numeric line counts"
            ) from error
        if added_lines < 0 or deleted_lines < 0:
            raise MalformedGitOutputError("Diff line counts cannot be negative")
        records.append(
            DiffStatRecord(
                commit_hash=commit_hash,
                file_path=file_path,
                added_lines=added_lines,
                deleted_lines=deleted_lines,
            )
        )
    return tuple(records)


def _parse_timestamp(value: str) -> datetime:
    try:
        timestamp = datetime.fromisoformat(value)
    except ValueError as error:
        raise MalformedGitOutputError(f"Malformed Git timestamp: {value!r}") from error
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise MalformedGitOutputError("Git timestamp must include a UTC offset")
    return timestamp
