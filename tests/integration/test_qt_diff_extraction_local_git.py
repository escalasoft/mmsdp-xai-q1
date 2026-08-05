"""Offline extraction of reproducible file-level diffs from local Git."""

import os
import subprocess
from pathlib import Path

import pytest

from extraction.qt_commit_extraction import (
    QtCommitExtractionSpecification,
    QtCommitExtractor,
)
from extraction.qt_diff_extraction import (
    QtDiffExtractionSpecification,
    QtDiffExtractor,
)
from extraction.qt_repository_acquisition import (
    QtRepositoryAcquirer,
    QtRepositoryAcquisitionSpecification,
)

CANONICAL = "https://code.qt.io/qt/qtbase.git"


def git(repository: Path, *arguments: str) -> str:
    environment = {
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_TERMINAL_PROMPT": "0",
        "HOME": os.devnull,
        "LANG": "C",
        "LC_ALL": "C",
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "GIT_AUTHOR_DATE": "2002-01-01T00:00:00+0000",
        "GIT_COMMITTER_DATE": "2002-01-01T00:00:00+0000",
    }
    result = subprocess.run(
        ["git", *arguments],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )
    return result.stdout.strip()


@pytest.fixture
def extracted_inputs(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    git(source, "init", "-q")
    git(source, "config", "user.name", "Local Fixture Author")
    git(source, "config", "user.email", "fixture@example.invalid")
    (source / "root.txt").write_text("one\ntwo\n", encoding="utf-8")
    (source / "delete.txt").write_text("delete\n", encoding="utf-8")
    git(source, "add", ".")
    git(source, "commit", "-q", "-m", "root")
    root = git(source, "rev-parse", "HEAD")
    (source / "root.txt").write_text("one\nchanged\nthree\n", encoding="utf-8")
    (source / "binary.bin").write_bytes(b"\x00\x01binary")
    git(source, "rm", "-q", "delete.txt")
    git(source, "add", ".")
    git(source, "commit", "-q", "-m", "modify delete binary")
    modified = git(source, "rev-parse", "HEAD")
    git(source, "mv", "root.txt", "renamed.txt")
    git(source, "commit", "-q", "-m", "rename")
    renamed = git(source, "rev-parse", "HEAD")
    git(source, "commit", "-q", "--allow-empty", "-m", "empty")
    empty = git(source, "rev-parse", "HEAD")
    git(source, "checkout", "-q", "-b", "side", modified)
    (source / "side.txt").write_text("side\n", encoding="utf-8")
    git(source, "add", "side.txt")
    git(source, "commit", "-q", "-m", "side")
    git(source, "checkout", "-q", "master")
    git(source, "merge", "-q", "--no-ff", "side", "-m", "merge")
    merge = git(source, "rev-parse", "HEAD")

    remote = tmp_path / "qtbase.git"
    git(tmp_path, "clone", "-q", "--bare", str(source), str(remote))
    acquisition_spec = QtRepositoryAcquisitionSpecification._for_local_test(
        repository_name="qtbase",
        canonical_repository_url=CANONICAL,
        transport_repository_url=str(remote),
        requested_reference=merge,
        default_branch="master",
        acquisition_policy_version="1.0.0",
    )
    repository = tmp_path / "acquired"
    acquisition = QtRepositoryAcquirer().acquire(acquisition_spec, repository)
    commits = QtCommitExtractor().extract(
        acquisition,
        repository,
        tmp_path / "commits.json",
        QtCommitExtractionSpecification("1.0.0"),
    )
    spec = QtDiffExtractionSpecification(
        repository_name="qtbase",
        canonical_repository_url=CANONICAL,
        repository_revision=merge,
        commit_artifact_digest=commits.artifact.content_digest,
        extraction_policy_version="1.0.0",
    )
    return (
        repository,
        acquisition.repository_snapshot,
        commits,
        spec,
        {
            "root": root,
            "modified": modified,
            "renamed": renamed,
            "empty": empty,
            "merge": merge,
        },
    )


def test_offline_topology_and_repeatability(extracted_inputs) -> None:
    repository, snapshot, commits, spec, ids = extracted_inputs
    one = QtDiffExtractor().extract(spec, repository, snapshot, commits)
    two = QtDiffExtractor().extract(spec, repository, snapshot, commits)

    assert one == two
    assert [item.commit_identifier for item in one.commit_diffs] == [
        item.commit_id for item in commits.records
    ]
    by_id = {item.commit_identifier: item for item in one.commit_diffs}
    assert by_id[ids["root"]].is_root_commit
    assert (
        by_id[ids["root"]].baseline_identifier
        == "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
    )
    assert by_id[ids["empty"]].changed_file_count == 0
    assert by_id[ids["merge"]].is_merge_commit
    assert (
        by_id[ids["merge"]].baseline_identifier
        == by_id[ids["merge"]].parent_identifiers[0]
    )
    modified = by_id[ids["modified"]]
    assert any(item.change_type == "deleted" for item in modified.file_changes)
    binary = next(item for item in modified.file_changes if item.path == "binary.bin")
    assert binary.is_binary and binary.additions is None and binary.deletions is None
    rename = next(
        item
        for item in by_id[ids["renamed"]].file_changes
        if item.change_type == "renamed"
    )
    assert (rename.old_path, rename.new_path, rename.similarity_percent) == (
        "root.txt",
        "renamed.txt",
        100,
    )
    rendered = repr(one) + str(one.to_dict())
    assert str(repository) not in rendered


def test_non_git_and_identity_mismatch_are_rejected(
    tmp_path: Path, extracted_inputs
) -> None:
    repository, snapshot, commits, spec, _ = extracted_inputs
    non_git = tmp_path / "not-git"
    non_git.mkdir()
    with pytest.raises(RuntimeError, match="Git rev-parse failed"):
        QtDiffExtractor().extract(spec, non_git, snapshot, commits)
    wrong = QtDiffExtractionSpecification(
        repository_name="qtbase",
        canonical_repository_url=CANONICAL,
        repository_revision=spec.repository_revision,
        commit_artifact_digest="f" * 64,
        extraction_policy_version="1.0.0",
    )
    with pytest.raises(ValueError, match="do not agree"):
        QtDiffExtractor().extract(wrong, repository, snapshot, commits)
