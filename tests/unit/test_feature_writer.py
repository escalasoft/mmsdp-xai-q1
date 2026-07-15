import csv
import hashlib

import pytest

from feature_engineering import (
    CodeFeatureRecord,
    FeatureEngineeringError,
    FeatureModality,
    write_code_features,
)
from feature_engineering.writer import CODE_COLUMNS


def test_writer_has_stable_columns_bytes_and_manifest(tmp_path) -> None:
    record = CodeFeatureRecord("abc", 2, 1, 3, 1)
    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"
    artifact = write_code_features([record], first)
    write_code_features([record], second)
    assert first.read_bytes() == second.read_bytes()
    with first.open(encoding="utf-8", newline="") as source:
        rows = list(csv.reader(source))
    assert tuple(rows[0]) == CODE_COLUMNS
    assert artifact.modality is FeatureModality.CODE
    assert artifact.row_count == 1
    assert artifact.checksum == hashlib.sha256(first.read_bytes()).hexdigest()


def test_writer_protects_existing_outputs_and_non_csv_paths(tmp_path) -> None:
    record = CodeFeatureRecord("abc", 2, 1, 3, 1)
    output = tmp_path / "features.csv"
    write_code_features([record], output)
    with pytest.raises(FeatureEngineeringError):
        write_code_features([record], output)
    with pytest.raises(FeatureEngineeringError):
        write_code_features([record], tmp_path / "features.json")


def test_writer_creates_parents_only_when_requested(tmp_path) -> None:
    record = CodeFeatureRecord("abc", 2, 1, 3, 1)
    output = tmp_path / "nested" / "features.csv"
    with pytest.raises(FeatureEngineeringError):
        write_code_features([record], output)
    artifact = write_code_features([record], output, create_parents=True)
    assert artifact.path.is_file()
