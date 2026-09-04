#!/usr/bin/env python3
"""Freeze the reconstructed object store as an external artifact registry.

This module only hashes and inventories persisted files. It has no model,
dataset, fitting, reconstruction, explanation, T1, T2, deletion, move, or
object-write path.
"""

# ruff: noqa: E501

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

VERSION = "q1-xai-external-artifact-store-freeze-1.0.0"
BRANCH = "sprint-10/q1-xai-governance-protocol"
EXECUTION_REL = Path("audits/q1-xai-reconstruction-execution/1.0.0")
OBJECTS_REL = EXECUTION_REL / "objects"
OUTPUT_REL = EXECUTION_REL / "external_artifact_registry"
GITIGNORE_RULE = "/audits/q1-xai-reconstruction-execution/1.0.0/objects/"
ORIGINAL_RUNTIME_REL = Path("audits/q1-xai-runtime-freeze/1.0.0")
PINNED_EVIDENCE = {
    "runtime_freeze_manifest": (ORIGINAL_RUNTIME_REL / "MANIFEST.sha256", "27b12b1f9105c1c9fdbdf9cac9e7a9942ed20f6303586dd54ce84b29c11e5c29"),
    "runtime_contract": (ORIGINAL_RUNTIME_REL / "xai_runtime_contract.json", "876836ddef18d5400a870b21997ea68ecc1793dcc48466233cde015e7f03045d"),
    "shap_resolution_amendment_manifest": (ORIGINAL_RUNTIME_REL / "amendments/shap_compatibility_resolution/1.0.0/MANIFEST.sha256", "b4a8ff54e61313941de69f9f5d23d8e3d2f369685d36bb7c42863a80a749d21a"),
}
TYPE_MAP = {
    "pipeline.joblib": "RECONSTRUCTED_EXECUTABLE_PIPELINE",
    "meta.joblib": "RECONSTRUCTED_FUSION_META_LEARNER",
    "lgb.txt": "LIGHTGBM_NATIVE_MODEL_STATE",
    "xgb.json": "XGBOOST_NATIVE_MODEL_STATE",
    "tfidf.json": "TFIDF_REPRESENTATION_STATE",
    "oof.json": "OOF_PROBABILITY_STATE",
    "npy": "TRAIN_SOURCE_CHECK_OUTPUT_ARRAY",
}


class StoreError(RuntimeError):
    """Fail-closed artifact-store integrity error."""


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def write_json(path: Path, value: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(canonical(value) + b"\n")
    os.replace(temporary, path)


def artifact_suffix(filename: str) -> str:
    return filename.split(".", 1)[1] if "." in filename else ""


def snapshot(root: Path) -> list[dict[str, Any]]:
    object_root = root / OBJECTS_REL
    paths = sorted(path for path in object_root.rglob("*") if path.is_file())

    def inspect(path: Path) -> dict[str, Any]:
        relative = path.relative_to(root / EXECUTION_REL).as_posix()
        stat = path.stat()
        digest = sha256(path)
        suffix = artifact_suffix(path.name)
        return {"relative_path": relative, "filename": path.name, "sha256": digest, "size_bytes": stat.st_size, "extension_type": suffix, "artifact_type": TYPE_MAP.get(suffix, "UNKNOWN_RECONSTRUCTED_ARTIFACT")}

    with ThreadPoolExecutor(max_workers=8) as pool:
        return list(pool.map(inspect, paths))


def snapshot_digest(rows: list[dict[str, Any]]) -> str:
    return hashlib.sha256(canonical(rows)).hexdigest()


def manifest_references(root: Path) -> dict[str, str]:
    result = {}
    for line in (root / EXECUTION_REL / "MANIFEST.sha256").read_text().splitlines():
        digest, relative = line.split("  ", 1)
        if relative.startswith("objects/"):
            if relative in result:
                raise StoreError(f"duplicate manifest object: {relative}")
            result[relative] = digest
    return result


def evidence_reference_counts(root: Path) -> Counter[str]:
    counts: Counter[str] = Counter()
    pattern = re.compile(r'"path"\s*:\s*"(objects/[^"\\]+)"')
    base = root / EXECUTION_REL
    excluded_roots = {base / "objects", base / "external_artifact_registry"}
    for path in sorted(base.rglob("*")):
        if not path.is_file() or any(parent == excluded for excluded in excluded_roots for parent in (path, *path.parents)):
            continue
        if path.suffix not in {".json", ".jsonl"}:
            continue
        text = path.read_text(errors="strict")
        counts.update(pattern.findall(text))
    return counts


def verify_pinned(root: Path) -> dict[str, Any]:
    result = {}
    original_inventory = json.loads((root / ORIGINAL_RUNTIME_REL / "dependency_inventory.json").read_text())
    for name, record in original_inventory["parents_after"].items():
        actual = sha256(root / record["path"])
        if actual != record["sha256"]:
            raise StoreError(f"protected Sprint 54-to-G5 evidence changed: {name}")
        result[name] = {"path": record["path"], "sha256": actual}
    for name, (relative, expected) in PINNED_EVIDENCE.items():
        actual = sha256(root / relative)
        if actual != expected:
            raise StoreError(f"protected runtime evidence changed: {name}")
        result[name] = {"path": str(relative), "sha256": actual}
    return result


def git_visible_worktree_bytes(root: Path) -> int:
    untracked = subprocess.check_output(["git", "ls-files", "--others", "--exclude-standard", "-z"], cwd=root).split(b"\0")
    modified = subprocess.check_output(["git", "diff", "--name-only", "-z"], cwd=root).split(b"\0")
    names = {item.decode() for item in (*untracked, *modified) if item}
    return sum((root / name).stat().st_size for name in names if (root / name).is_file())


def report(summary: dict[str, Any]) -> str:
    return f"""# External Reconstructed Artifact Store Freeze

## Classification

`EXTERNAL_RECONSTRUCTED_EXECUTABLE_ARTIFACT_STORE`

The object files are generated fitted-state artifacts required for future Sprint 56 XAI. They are not source code and are intentionally excluded from ordinary Git blob storage, but remain scientifically required, locally preserved, and provenance-bound by SHA-256. Git exclusion does not make them disposable.

## Verified disposition

- Object count: {summary['object_count']}
- Total bytes: {summary['total_size_bytes']}
- Largest object: `{summary['largest_object']['relative_path']}` ({summary['largest_object']['size_bytes']} bytes)
- Block 7 manifest-referenced objects: {summary['referenced_object_count']}
- Missing references: {summary['missing_reference_count']}
- Orphans: {summary['orphan_count']}
- Integrity: `{summary['integrity_status']}`
- Store snapshot SHA-256: `{summary['store_snapshot_sha256']}`
- Git policy: `{GITIGNORE_RULE}`
- Git-visible Sprint 55 working-tree evidence after object exclusion: {summary.get('git_visible_sprint55_size_bytes_after_object_exclusion', 'PENDING_FINALIZATION')} bytes

## Preservation and restoration

`LOCAL_ARTIFACT_PRESERVATION_REQUIRED_UNTIL_SPRINT56`

Do not delete, clean, relocate, compress, overwrite, or modify this store before the Sprint 56 runtime/environment strategy is finalized. Sprint 56 must fail closed if any required object is absent, has a size mismatch, or fails SHA-256 verification against `external_artifact_inventory.jsonl`.

A future separately authorized publication may deposit a versioned bundle in Zenodo or an equivalent scientific repository with this inventory, checksums, provenance, and DOI/content identifier. No bundle, upload, relocation, or publication occurred in this block.

T1 access, T2 access, model queries, XAI, fitting, reconstruction, and recalibration were all zero. Existing Block 7/7A/7B, G4, G5, and runtime-freeze evidence remained unchanged.
"""


def run(root: Path) -> Path:
    branch = subprocess.check_output(["git", "symbolic-ref", "--short", "HEAD"], cwd=root, text=True).strip()
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    if branch != BRANCH:
        raise StoreError(f"wrong branch: {branch}")
    if GITIGNORE_RULE not in (root / ".gitignore").read_text().splitlines():
        raise StoreError("narrow object-store Git ignore rule is absent")
    pinned_before = verify_pinned(root)
    before = snapshot(root)
    manifest = manifest_references(root)
    physical = {row["relative_path"]: row for row in before}
    evidence_counts = evidence_reference_counts(root)
    missing = sorted(set(manifest) - set(physical))
    orphans = sorted(set(physical) - set(manifest))
    digest_mismatches = sorted(path for path in set(manifest) & set(physical) if manifest[path] != physical[path]["sha256"])
    filename_digest_mismatches = sorted(row["relative_path"] for row in before if row["filename"].split(".", 1)[0] != row["sha256"])
    if missing or orphans or digest_mismatches or filename_digest_mismatches:
        raise StoreError("object store is not a complete content-addressed match to the Block 7 manifest")
    inventory = [{**row, "referenced_in_block7_manifest": True, "block7_evidence_reference_count": evidence_counts[row["relative_path"]]} for row in before]
    output = root / OUTPUT_REL
    output.mkdir(parents=True, exist_ok=True)
    inventory_path = output / "external_artifact_inventory.jsonl"
    temporary = inventory_path.with_suffix(".jsonl.tmp")
    with temporary.open("wb") as stream:
        for row in inventory:
            stream.write(canonical(row) + b"\n")
    os.replace(temporary, inventory_path)
    largest = max(before, key=lambda row: (row["size_bytes"], row["relative_path"]))
    by_type = Counter(row["artifact_type"] for row in before)
    timestamp = datetime.now(UTC).isoformat()
    summary = {"schema_version": VERSION, "classification": "EXTERNAL_RECONSTRUCTED_EXECUTABLE_ARTIFACT_STORE", "preservation_state": "LOCAL_ARTIFACT_PRESERVATION_REQUIRED_UNTIL_SPRINT56", "branch": branch, "git_HEAD": head, "timestamp_utc": timestamp, "object_count": len(before), "total_size_bytes": sum(row["size_bytes"] for row in before), "largest_object": largest, "referenced_object_count": len(set(manifest) & set(physical)), "manifest_reference_count": len(manifest), "objects_with_direct_evidence_path_reference": sum(evidence_counts[path] > 0 for path in physical), "direct_evidence_reference_occurrence_count": sum(evidence_counts.values()), "missing_reference_count": len(missing), "missing_references": missing, "orphan_count": len(orphans), "orphan_objects": orphans, "digest_mismatch_count": len(digest_mismatches), "filename_digest_mismatch_count": len(filename_digest_mismatches), "artifact_type_counts": dict(sorted(by_type.items())), "store_snapshot_sha256": snapshot_digest(before), "integrity_status": "PASS_EXACT_CONTENT_ADDRESSED_MANIFEST_EQUIVALENCE", "object_bytes_embedded": False, "governance": {"T1_access_count": 0, "T2_access_count": 0, "T2_state": "DENY_SEALED_REVIEWER_RESERVE", "XAI_execution_count": 0, "model_query_count": 0, "fit_count": 0, "reconstruction_count": 0, "recalibration_count": 0}}
    restoration = {"schema_version": VERSION, "state": "LOCAL_ARTIFACT_PRESERVATION_REQUIRED_UNTIL_SPRINT56", "disposable": False, "prohibited_before_runtime_strategy": ["DELETE", "GIT_CLEAN", "RELOCATE", "COMPRESS", "OVERWRITE", "BYTE_MODIFICATION"], "Sprint56_preflight": ["REQUIRE_ALL_INVENTORY_PATHS", "VERIFY_EXACT_SIZE", "VERIFY_SHA256", "FAIL_CLOSED_ON_ANY_MISSING_OR_MISMATCH"], "ordinary_git_blob_storage": "EXCLUDED", "external_publication_status": "DOCUMENTED_NOT_AUTHORIZED_NOT_EXECUTED", "future_repository_examples": ["ZENODO", "EQUIVALENT_SCIENTIFIC_ARTIFACT_REPOSITORY"], "future_bundle_requirements": ["OBJECT_BUNDLE", "EXACT_INVENTORY", "CHECKSUMS", "PROVENANCE", "VERSION", "DOI_OR_CONTENT_IDENTIFIER"], "restore_rule": "Restore every relative_path byte-for-byte beneath audits/q1-xai-reconstruction-execution/1.0.0 and verify the complete inventory before use."}
    write_json(output / "external_artifact_summary.json", summary)
    write_json(output / "external_artifact_restoration_policy.json", restoration)
    (output / "EXTERNAL_ARTIFACT_STORE_REPORT.md").write_text(report(summary))
    after = snapshot(root)
    pinned_after = verify_pinned(root)
    if before != after or pinned_before != pinned_after:
        raise StoreError("object bytes or protected evidence changed during registry creation")
    summary["post_write_object_count"] = len(after)
    summary["post_write_store_snapshot_sha256"] = snapshot_digest(after)
    summary["object_bytes_unchanged_before_after"] = True
    summary["protected_evidence_unchanged_before_after"] = True
    summary["gitignore_rule"] = GITIGNORE_RULE
    write_json(output / "external_artifact_summary.json", summary)
    (output / "EXTERNAL_ARTIFACT_STORE_REPORT.md").write_text(report(summary))
    names = sorted(path.name for path in output.iterdir() if path.is_file() and path.name != "MANIFEST.sha256" and not path.name.endswith(".tmp"))
    for _ in range(5):
        (output / "MANIFEST.sha256").write_text("".join(f"{sha256(output / name)}  {name}\n" for name in names))
        visible_bytes = git_visible_worktree_bytes(root)
        if summary.get("git_visible_sprint55_size_bytes_after_object_exclusion") == visible_bytes:
            break
        summary["git_visible_sprint55_size_bytes_after_object_exclusion"] = visible_bytes
        write_json(output / "external_artifact_summary.json", summary)
        (output / "EXTERNAL_ARTIFACT_STORE_REPORT.md").write_text(report(summary))
    else:
        raise StoreError("Git-visible size accounting did not stabilize")
    (output / "MANIFEST.sha256").write_text("".join(f"{sha256(output / name)}  {name}\n" for name in names))
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    print(run(args.root.resolve()))


if __name__ == "__main__":
    main()
