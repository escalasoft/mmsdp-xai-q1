import extraction


def test_package_public_exports_are_stable() -> None:
    assert set(extraction.__all__) == {
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
    }


def test_raw_contracts_exclude_downstream_scientific_fields() -> None:
    prohibited = {"label", "target", "feature", "split", "model", "issue"}
    for record_type in (extraction.CommitRecord, extraction.DiffStatRecord):
        names = set(record_type.__dataclass_fields__)
        assert not any(term in name for name in names for term in prohibited)
