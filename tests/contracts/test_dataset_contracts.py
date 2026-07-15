"""Contract tests for the stable dataset package API."""

import dataset

EXPECTED_EXPORTS = {
    "DatasetArtifact",
    "DatasetContract",
    "DatasetError",
    "DatasetNotFoundError",
    "DatasetSplit",
    "DatasetStage",
    "DatasetValidationError",
    "MalformedDatasetError",
    "UnsupportedDatasetFormatError",
    "load_csv",
    "validate_binary_target",
    "validate_chronological_split_ordering",
    "validate_dataset",
    "validate_duplicate_primary_keys",
    "validate_missing_primary_keys",
    "validate_missing_targets",
    "validate_required_columns",
    "validate_timestamp_presence",
}


def test_dataset_package_has_stable_explicit_exports() -> None:
    assert set(dataset.__all__) == EXPECTED_EXPORTS
    assert all(hasattr(dataset, name) for name in EXPECTED_EXPORTS)
