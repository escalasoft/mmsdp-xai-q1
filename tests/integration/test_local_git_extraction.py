import shutil
import subprocess

import pytest

from extraction import GitClient, extract_commits


@pytest.mark.skipif(shutil.which("git") is None, reason="Git executable is unavailable")
def test_extracts_two_commits_from_temporary_local_repository(tmp_path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    subprocess.run(["git", "init", "-q", repository], check=True)
    subprocess.run(
        ["git", "-C", str(repository), "config", "user.name", "Integration Test"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(repository), "config", "user.email", "test@example.test"],
        check=True,
    )
    tracked = repository / "sample.txt"
    tracked.write_text("first\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repository), "add", "sample.txt"], check=True)
    subprocess.run(
        ["git", "-C", str(repository), "commit", "-q", "-m", "First subject"],
        check=True,
    )
    tracked.write_text("first\nsecond\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repository), "add", "sample.txt"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(repository),
            "commit",
            "-q",
            "-m",
            "Second subject",
            "-m",
            "Second body",
        ],
        check=True,
    )

    records = extract_commits(GitClient(repository))

    assert [record.subject for record in records] == ["Second subject", "First subject"]
    assert records[0].body == "Second body\n"
    assert records[0].parent_hashes == (records[1].commit_hash,)
    assert records[1].parent_hashes == ()
    assert all(record.authored_at.tzinfo is not None for record in records)
