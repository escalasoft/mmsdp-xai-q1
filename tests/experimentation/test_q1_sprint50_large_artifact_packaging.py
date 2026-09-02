from __future__ import annotations

import gzip
import json
import subprocess
from pathlib import Path

import pytest

from experimentation.q1_sprint50_large_artifact_packaging import (
    CORRECTION_NAME,
    EQUALITY_NAME,
    EXPECTED_CONDITION_COUNT,
    EXPECTED_LEDGER_SHA256,
    EXPECTED_LEDGER_SIZE,
    EXPECTED_RECORD_COUNT,
    INVENTORY_NAME,
    LEDGER_FIELDS,
    LEDGER_NAME,
    OUTPUT_REL,
    LargeArtifactPackagingError,
    file_sha256,
    materialize,
    verify_materialized_artifact,
    verify_package,
)

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / OUTPUT_REL


@pytest.fixture(scope="module", autouse=True)
def packaging_artifacts() -> None:
    materialize(ROOT)


def test_large_ledger_is_narrowly_ignored_but_lightweight_evidence_is_not() -> None:
    ledger = str(OUTPUT_REL / LEDGER_NAME)
    ignored = subprocess.run(
        ("git", "check-ignore", "-v", ledger),
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert ledger in ignored
    for name in ("REPORT.md", "condition_results.csv", INVENTORY_NAME, CORRECTION_NAME):
        result = subprocess.run(
            ("git", "check-ignore", str(OUTPUT_REL / name)),
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1


def test_inventory_has_required_contract_and_exact_local_identity() -> None:
    inventory = json.loads((OUTPUT / INVENTORY_NAME).read_text())
    artifact = inventory["artifacts"][0]
    required = {
        "artifact_name",
        "relative_original_path",
        "artifact_role",
        "compressed_size_bytes",
        "sha256",
        "record_count",
        "schema",
        "generated_from",
        "generation_contract",
        "scientific_dependencies",
        "downstream_use",
        "git_tracking_policy",
        "external_storage_status",
        "materialization_required_for_calibration",
        "verification_command",
        "verification_process",
    }
    assert required <= set(artifact)
    assert artifact["artifact_name"] == LEDGER_NAME
    assert artifact["compressed_size_bytes"] == EXPECTED_LEDGER_SIZE
    assert artifact["sha256"] == EXPECTED_LEDGER_SHA256
    assert artifact["record_count"] == EXPECTED_RECORD_COUNT
    assert artifact["schema"]["fields"] == LEDGER_FIELDS
    assert artifact["generated_from"]["source_condition_count"] == 3920
    assert artifact["generated_from"]["source_probability_count"] == 1_928_304
    assert artifact["external_storage_status"] == "NOT_YET_MATERIALIZED"
    assert artifact["external_url"] is None
    ledger = OUTPUT / LEDGER_NAME
    assert ledger.stat().st_size == artifact["compressed_size_bytes"]
    assert file_sha256(ledger) == artifact["sha256"]


def test_git_manifest_excludes_only_declared_external_artifact() -> None:
    names = {
        line.split("  ", 1)[1]
        for line in (OUTPUT / "MANIFEST.sha256").read_text().splitlines()
    }
    expected = {
        path.name
        for path in OUTPUT.iterdir()
        if path.is_file() and path.name not in {"MANIFEST.sha256", LEDGER_NAME}
    }
    assert names == expected
    assert LEDGER_NAME not in names
    assert {
        "condition_results.json",
        "statistical_pairwise_results.csv",
        "FINAL_HUMAN_REVIEW_REPORT.md",
        INVENTORY_NAME,
        EQUALITY_NAME,
        CORRECTION_NAME,
    } <= names


def test_scientific_results_are_byte_identical_and_test_access_is_zero() -> None:
    equality = json.loads((OUTPUT / EQUALITY_NAME).read_text())
    assert equality["status"] == "PASS_BYTE_IDENTICAL"
    assert equality["condition_count"] == EXPECTED_CONDITION_COUNT
    assert equality["scientific_value_change_count"] == 0
    assert all(row["byte_identical"] for row in equality["protected_artifacts"])
    assert set(equality["T1_T2_access_counters"].values()) == {0}


def test_complete_package_and_local_ledger_verify() -> None:
    result = verify_package(ROOT)
    assert result["status"] == "PASS"
    assert result["inventory"]["artifacts"][0]["record_count"] == 1_928_304


def test_calibration_materialization_fails_closed_on_hash_mismatch(
    tmp_path: Path,
) -> None:
    path = tmp_path / LEDGER_NAME
    row = {
        "algorithm": "LR",
        "benchmark_defined_observed_label": 0,
        "configuration": "C",
        "cv_value": 2,
        "forward_block": 2,
        "frozen_partition_provenance": "TRAIN",
        "project": "apache/example",
        "raw_probability": 0.5,
        "row_identifier": "a" * 64,
    }
    with gzip.open(path, "wt", encoding="utf-8", newline="") as stream:
        stream.write(json.dumps(row, sort_keys=True) + "\n")
    artifact = {
        "compressed_size_bytes": path.stat().st_size,
        "sha256": "0" * 64,
        "record_count": 1,
        "schema": {"fields": LEDGER_FIELDS},
    }
    with pytest.raises(LargeArtifactPackagingError, match="SHA-256 mismatch"):
        verify_materialized_artifact(path, artifact)


def test_metadata_regeneration_is_deterministic() -> None:
    names = (INVENTORY_NAME, EQUALITY_NAME, CORRECTION_NAME, "MANIFEST.sha256")
    before = {name: file_sha256(OUTPUT / name) for name in names}
    materialize(ROOT)
    after = {name: file_sha256(OUTPUT / name) for name in names}
    assert after == before
