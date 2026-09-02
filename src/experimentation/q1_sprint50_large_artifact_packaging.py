"""Sprint 50-R2 packaging contract for the external raw-probability ledger."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from experimentation.q1_controlled_train_validation_baselines import canonical_bytes

VERSION = "q1-sprint50-r2-large-artifact-packaging-1.0.0"
OUTPUT_REL = Path("audits/q1-temporal-robustness-cv/1.0.0")
LEDGER_NAME = "raw_probability_provenance.jsonl.gz"
INVENTORY_NAME = "external_artifact_inventory.json"
EQUALITY_NAME = "scientific_equality_verification.json"
CORRECTION_NAME = "LARGE_ARTIFACT_PACKAGING_CORRECTION.md"
EXPECTED_LEDGER_SIZE = 96_315_731
EXPECTED_LEDGER_SHA256 = (
    "94be037a1ed99e71b11bc1ae9733c1cffeef7ad5b881a5e48039fbd2b8145203"
)
EXPECTED_RECORD_COUNT = 1_928_304
EXPECTED_CONDITION_COUNT = 3_920
PRE_CORRECTION_MANIFEST_SHA256 = (
    "e9c09ca84a9f5c82a4860b605ec484d20efeb588c047a11a38e8c7462ef7d44a"
)
LEDGER_FIELDS = {
    "algorithm": "string",
    "benchmark_defined_observed_label": "integer_0_or_1",
    "configuration": "string",
    "cv_value": "integer_2_through_11",
    "forward_block": "integer_2_through_11",
    "frozen_partition_provenance": "TRAIN_or_VALIDATION",
    "project": "string",
    "raw_probability": "number_0_through_1",
    "row_identifier": "sha256_string",
}
PROTECTED_SCIENTIFIC_HASHES = {
    "FINAL_HUMAN_REVIEW_REPORT.md": (
        "1119e5a895b36db028223068e5aad330c20cb1353de52d844ddcbab1edf87194"
    ),
    "condition_results.csv": (
        "f9336469a8c3215363457ef0b91e34a3ec32e4a1e74125713d5938b0bd8ab60e"
    ),
    "condition_results.json": (
        "234dcc5ed74ad7562ca3597c5bf218cab9f0baaa0597a906b3c772922ecea909"
    ),
    "cv_dispersion_summary.csv": (
        "6c4606d9c83e57d60782e2192d99b88aad41a09e811ca1cc08f43be364f08fb2"
    ),
    "cv_trajectory_data.csv": (
        "123e5b1a45539c5908eefd8afe23e48feef9ba2622aae9c224b796309e9c86bf"
    ),
    "effect_size_results.csv": (
        "37ae7b53d12a6f99bb1235d0cc3b98a1a6a54f251a6f4108db01c903fff6364f"
    ),
    "hyperparameter_provenance.csv": (
        "e73a343b6ce2b656e37d50f4a4913a5b3eb3e8341f3346e9c8b20d57cf236c67"
    ),
    "metric_results_long.csv": (
        "123e5b1a45539c5908eefd8afe23e48feef9ba2622aae9c224b796309e9c86bf"
    ),
    "perfect_near_perfect_diagnostic.csv": (
        "8597ba288de04213cf879d46b55d5be9e4ee264c672072175c9d28b9868a8134"
    ),
    "project_level_stability_summary.csv": (
        "24d744b2c1bcf8615d8350ad27b2825d4fb3df03a57eb196905417ceacbc18a5"
    ),
    "raw_probability_quality_summary.csv": (
        "470898f301157e5886c1906113d1579c6538a3ac11b2af9390b37ddeb67f2180"
    ),
    "statistical_omnibus_results.csv": (
        "1aed50e2e04bd8b89df55f3ace763f8ac12d248d4198df07f033c65701535cc4"
    ),
    "statistical_pairwise_results.csv": (
        "37ae7b53d12a6f99bb1235d0cc3b98a1a6a54f251a6f4108db01c903fff6364f"
    ),
    "t1_t2_access_audit.json": (
        "6adcd352a05ee7dae2f2b4185274c3c54d8c26e0a7947fd502dac419bf94f790"
    ),
    "temporal_membership_provenance.json": (
        "f8d56fd08d72efabc91404aef89417d4268e1edcbeb8ae9e515b3f1574c7a1e7"
    ),
}


class LargeArtifactPackagingError(RuntimeError):
    """Raised when packaging or downstream materialization must fail closed."""


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ("git", *args),
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _validate_row(row: dict[str, Any]) -> None:
    if set(row) != set(LEDGER_FIELDS):
        raise LargeArtifactPackagingError("raw ledger schema mismatch")
    if row["benchmark_defined_observed_label"] not in (0, 1):
        raise LargeArtifactPackagingError("raw ledger label schema mismatch")
    if row["cv_value"] not in range(2, 12) or row["forward_block"] not in range(2, 12):
        raise LargeArtifactPackagingError("raw ledger temporal schema mismatch")
    if row["frozen_partition_provenance"] not in {"TRAIN", "VALIDATION"}:
        raise LargeArtifactPackagingError("raw ledger provenance schema mismatch")
    probability = row["raw_probability"]
    if not isinstance(probability, (int, float)) or not 0 <= probability <= 1:
        raise LargeArtifactPackagingError("raw ledger probability schema mismatch")
    identifier = row["row_identifier"]
    if not isinstance(identifier, str) or len(identifier) != 64:
        raise LargeArtifactPackagingError("raw ledger identity schema mismatch")


def count_and_validate_records(path: Path) -> int:
    count = 0
    try:
        with gzip.open(path, "rt", encoding="utf-8", newline="") as stream:
            for line in stream:
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as error:
                    raise LargeArtifactPackagingError(
                        "raw ledger JSONL decoding failed"
                    ) from error
                _validate_row(row)
                count += 1
    except (gzip.BadGzipFile, EOFError) as error:
        raise LargeArtifactPackagingError("raw ledger gzip integrity failed") from error
    return count


def inventory_payload(root: Path) -> dict[str, Any]:
    ledger = root / OUTPUT_REL / LEDGER_NAME
    if not ledger.is_file():
        raise LargeArtifactPackagingError("external raw ledger is missing")
    size = ledger.stat().st_size
    sha256 = file_sha256(ledger)
    count = count_and_validate_records(ledger)
    if size != EXPECTED_LEDGER_SIZE:
        raise LargeArtifactPackagingError("external raw ledger size mismatch")
    if sha256 != EXPECTED_LEDGER_SHA256:
        raise LargeArtifactPackagingError("external raw ledger SHA-256 mismatch")
    if count != EXPECTED_RECORD_COUNT:
        raise LargeArtifactPackagingError("external raw ledger record count mismatch")
    return {
        "schema_version": VERSION,
        "external_storage_status": "NOT_YET_MATERIALIZED",
        "artifacts": [
            {
                "artifact_name": LEDGER_NAME,
                "relative_original_path": str(OUTPUT_REL / LEDGER_NAME),
                "artifact_role": (
                    "Development-only row-level raw probability and immutable "
                    "provenance "
                    "ledger for reproducibility and later calibration."
                ),
                "compressed_size_bytes": size,
                "sha256": sha256,
                "record_count": count,
                "schema": {
                    "name": "q1_sprint50_raw_probability_provenance_jsonl",
                    "version": "1.0.0",
                    "serialization": "deterministic gzip JSON Lines; gzip mtime=0",
                    "fields": LEDGER_FIELDS,
                },
                "generated_from": {
                    "sprint": "10.8.2.50",
                    "git_head": "2a140be481d29949d2fe0fd74dc5c99aeeecd143",
                    "source_condition_count": EXPECTED_CONDITION_COUNT,
                    "source_probability_count": EXPECTED_RECORD_COUNT,
                    "projects": 14,
                    "algorithms": 4,
                    "configurations": 7,
                    "temporal_cv_origins": list(range(2, 12)),
                },
                "generation_contract": {
                    "module": "experimentation.q1_sprint50_temporal_robustness",
                    "process": (
                        "Execute the frozen Sprint 49 selections under the accepted "
                        "Sprint 50-R1 expanding-forward protocol, serialize project "
                        "fragments in frozen project order, and gzip with mtime=0."
                    ),
                    "full_regeneration_command": (
                        "PYTHONPATH=src .venv/bin/python -m "
                        "experimentation.q1_sprint50_temporal_robustness --root . "
                        "--workers 3"
                    ),
                    "regeneration_policy": (
                        "Do not regenerate for packaging or calibration when the "
                        "verified ledger is available; full regeneration requires "
                        "separate authority."
                    ),
                },
                "scientific_dependencies": [
                    "Sprint 48F-R1 frozen ApacheJIT dataset",
                    "Sprint 49 frozen selections and hyperparameters",
                    "Sprint 50-R1 prospective temporal protocol amendment",
                    "Sprint 50 condition and temporal membership identities",
                ],
                "provenance_description": (
                    "Each record binds project, algorithm, configuration, temporal CV "
                    "origin, row identity, original TRAIN/VALIDATION provenance, "
                    "observed "
                    "development label, and raw positive-class probability."
                ),
                "downstream_use": [
                    "development-only calibration fitting/evaluation with causal "
                    "separation",
                    "Brier score and ECE verification",
                    "reliability-diagram materialization",
                    "row-level prediction reproducibility audit",
                ],
                "git_tracking_policy": "EXCLUDED_FROM_ORDINARY_GIT_TRACKING",
                "external_storage_status": "NOT_YET_MATERIALIZED",
                "expected_storage_location": (
                    "Current verified local path above; future durable external URI "
                    "must be "
                    "recorded prospectively without replacing this identity contract."
                ),
                "external_url": None,
                "materialization_required_for_calibration": True,
                "verification_command": (
                    "PYTHONPATH=src .venv/bin/python -m "
                    "experimentation.q1_sprint50_large_artifact_packaging --root . "
                    "--verify"
                ),
                "verification_process": [
                    "Require the declared local materialization path to exist.",
                    "Verify compressed byte size and SHA-256.",
                    "Stream and validate every gzip JSONL record against the frozen "
                    "schema.",
                    "Verify the exact record count.",
                    "Fail closed before calibration on any mismatch.",
                ],
            }
        ],
        "pre_correction_combined_manifest_sha256": PRE_CORRECTION_MANIFEST_SHA256,
    }


def write_external_inventory(root: Path) -> Path:
    output = root / OUTPUT_REL
    payload = inventory_payload(root)
    path = output / INVENTORY_NAME
    path.write_bytes(canonical_bytes(payload))
    return path


def verify_materialized_artifact(path: Path, artifact: dict[str, Any]) -> int:
    if not path.is_file():
        raise LargeArtifactPackagingError("external raw ledger is missing")
    if path.stat().st_size != artifact["compressed_size_bytes"]:
        raise LargeArtifactPackagingError("external raw ledger size mismatch")
    if file_sha256(path) != artifact["sha256"]:
        raise LargeArtifactPackagingError("external raw ledger SHA-256 mismatch")
    count = count_and_validate_records(path)
    if count != artifact["record_count"]:
        raise LargeArtifactPackagingError("external raw ledger record count mismatch")
    if artifact["schema"]["fields"] != LEDGER_FIELDS:
        raise LargeArtifactPackagingError(
            "external raw ledger declared schema mismatch"
        )
    return count


def verify_external_artifact(root: Path) -> dict[str, Any]:
    inventory_path = root / OUTPUT_REL / INVENTORY_NAME
    if not inventory_path.is_file():
        raise LargeArtifactPackagingError("external artifact inventory is missing")
    recorded = json.loads(inventory_path.read_text(encoding="utf-8"))
    artifact = recorded["artifacts"][0]
    verify_materialized_artifact(root / artifact["relative_original_path"], artifact)
    current = inventory_payload(root)
    if recorded != current:
        raise LargeArtifactPackagingError("external artifact inventory mismatch")
    return current


def scientific_equality(root: Path) -> dict[str, Any]:
    output = root / OUTPUT_REL
    rows = []
    for name, expected in sorted(PROTECTED_SCIENTIFIC_HASHES.items()):
        actual = file_sha256(output / name)
        rows.append(
            {
                "artifact": name,
                "expected_sha256": expected,
                "actual_sha256": actual,
                "byte_identical": actual == expected,
            }
        )
    if not all(row["byte_identical"] for row in rows):
        raise LargeArtifactPackagingError("protected scientific artifact changed")
    conditions = json.loads((output / "condition_results.json").read_text())["rows"]
    if len(conditions) != EXPECTED_CONDITION_COUNT:
        raise LargeArtifactPackagingError("condition count changed")
    access = json.loads((output / "t1_t2_access_audit.json").read_text())
    counters = {key: value for key, value in access.items() if key.endswith("_count")}
    if not counters or any(counters.values()):
        raise LargeArtifactPackagingError("T1/T2 counter changed")
    return {
        "schema_version": VERSION,
        "status": "PASS_BYTE_IDENTICAL",
        "condition_count": len(conditions),
        "protected_artifacts": rows,
        "T1_T2_access_counters": counters,
        "scientific_value_change_count": 0,
    }


def _write_git_manifest(output: Path) -> None:
    entries = [
        f"{file_sha256(path)}  {path.name}"
        for path in sorted(output.iterdir())
        if path.is_file() and path.name not in {"MANIFEST.sha256", LEDGER_NAME}
    ]
    (output / "MANIFEST.sha256").write_text("\n".join(entries) + "\n", encoding="utf-8")


def _correction_markdown(root: Path, inventory: dict[str, Any]) -> str:
    artifact = inventory["artifacts"][0]
    return "\n".join(
        [
            "# Sprint 50-R2 large-artifact packaging correction",
            "",
            "**Classification:** `PASS_50_R2_LARGE_ARTIFACT_PACKAGING_CORRECTION`",
            "",
            "This packaging-only correction excludes the large raw-probability ledger "
            "from ordinary Git tracking while leaving it at its original local path. "
            "No model, prediction, metric, statistical result, threshold, calibration "
            "state, temporal fold, label, feature, T1/T2 evidence, or XAI state "
            "changed.",
            "",
            "## External artifact identity",
            "",
            f"- Original path: `{artifact['relative_original_path']}`",
            f"- Compressed size: {artifact['compressed_size_bytes']} bytes",
            f"- SHA-256: `{artifact['sha256']}`",
            f"- Records: {artifact['record_count']}",
            "- External storage status: `NOT_YET_MATERIALIZED`",
            "- External URL: none assigned.",
            "",
            "## Packaging and manifest policy",
            "",
            "`.gitignore` contains one exact repository-relative rule for this ledger. "
            "`MANIFEST.sha256` is now the Git-tracked lightweight-package manifest and "
            "excludes only the declared ledger. `external_artifact_inventory.json` "
            "separately freezes its size, hash, record count, schema, provenance, "
            "generation contract, expected materialization path, and verification "
            "rule.",
            "",
            "## Scientific equality and calibration dependency",
            "",
            "`scientific_equality_verification.json` proves the protected Sprint 50 "
            "results remain byte-identical. Future calibration must first materialize "
            "the ledger at the declared path (or an explicitly resolved durable copy) "
            "and run the inventory verifier. Missing data, hash/size/count drift, gzip "
            "damage, or schema drift fails closed before calibration.",
            "",
            "## Reproduction",
            "",
            f"Verification command: `{artifact['verification_command']}`",
            "",
            f"Recorded branch: `{_git(root, 'symbolic-ref', '--short', 'HEAD')}`; "
            f"HEAD: `{_git(root, 'rev-parse', 'HEAD')}`.",
            "",
        ]
    )


def materialize(root: Path) -> Path:
    output = root / OUTPUT_REL
    inventory_path = write_external_inventory(root)
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    equality = scientific_equality(root)
    (output / EQUALITY_NAME).write_bytes(canonical_bytes(equality))
    (output / CORRECTION_NAME).write_text(
        _correction_markdown(root, inventory), encoding="utf-8"
    )
    _write_git_manifest(output)
    return output


def verify_package(root: Path) -> dict[str, Any]:
    inventory = verify_external_artifact(root)
    equality = scientific_equality(root)
    output = root / OUTPUT_REL
    manifest_names = []
    for line in (output / "MANIFEST.sha256").read_text().splitlines():
        expected, name = line.split("  ", 1)
        if name == LEDGER_NAME or file_sha256(output / name) != expected:
            raise LargeArtifactPackagingError("Git package manifest mismatch")
        manifest_names.append(name)
    expected_names = sorted(
        path.name
        for path in output.iterdir()
        if path.is_file() and path.name not in {"MANIFEST.sha256", LEDGER_NAME}
    )
    if sorted(manifest_names) != expected_names:
        raise LargeArtifactPackagingError("Git package manifest coverage mismatch")
    return {
        "status": "PASS",
        "inventory": inventory,
        "scientific_equality": equality,
        "git_manifest_entry_count": len(manifest_names),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    result = verify_package(root) if args.verify else materialize(root)
    if isinstance(result, Path):
        print(result)
    else:
        print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
