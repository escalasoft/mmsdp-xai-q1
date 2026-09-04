# ruff: noqa: E501

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXECUTION = ROOT / "audits/q1-xai-reconstruction-execution/1.0.0"
OBJECTS = EXECUTION / "objects"
REGISTRY = EXECUTION / "external_artifact_registry"
RULE = "/audits/q1-xai-reconstruction-execution/1.0.0/objects/"


def load(name):
    return json.loads((REGISTRY / name).read_text())


def inventory():
    return [json.loads(line) for line in (REGISTRY / "external_artifact_inventory.jsonl").read_text().splitlines()]


def sha256(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def test_exact_inventory_count_size_types_and_unique_paths():
    rows = inventory()
    summary = load("external_artifact_summary.json")
    assert len(rows) == summary["object_count"] == summary["post_write_object_count"] == 5649
    assert len({row["relative_path"] for row in rows}) == len({row["sha256"] for row in rows}) == 5649
    assert sum(row["size_bytes"] for row in rows) == summary["total_size_bytes"]
    assert sum(summary["artifact_type_counts"].values()) == 5649
    assert summary["largest_object"]["size_bytes"] == max(row["size_bytes"] for row in rows)


def test_every_inventory_hash_size_and_content_address_matches_physical_bytes():
    for row in inventory():
        path = EXECUTION / row["relative_path"]
        assert path.is_file()
        assert path.stat().st_size == row["size_bytes"]
        assert sha256(path) == row["sha256"]
        assert row["filename"].split(".", 1)[0] == row["sha256"]


def test_block7_manifest_references_every_object_without_missing_or_orphans():
    summary = load("external_artifact_summary.json")
    assert summary["referenced_object_count"] == summary["manifest_reference_count"] == 5649
    assert summary["missing_reference_count"] == summary["orphan_count"] == 0
    assert summary["digest_mismatch_count"] == summary["filename_digest_mismatch_count"] == 0
    assert summary["integrity_status"] == "PASS_EXACT_CONTENT_ADDRESSED_MANIFEST_EQUIVALENCE"
    assert summary["object_bytes_unchanged_before_after"] is True


def test_gitignore_is_exact_narrow_and_registry_remains_visible():
    lines = (ROOT / ".gitignore").read_text().splitlines()
    assert lines.count(RULE) == 1
    assert not any(line in {"audits/", "/audits/", "*.joblib", "*.npy", "*.pkl"} for line in lines)
    sample = next(OBJECTS.iterdir())
    assert subprocess.run(["git", "check-ignore", "-q", str(sample.relative_to(ROOT))], cwd=ROOT).returncode == 0
    assert subprocess.run(["git", "check-ignore", "-q", str((REGISTRY / "external_artifact_summary.json").relative_to(ROOT))], cwd=ROOT).returncode == 1
    assert subprocess.run(["git", "check-ignore", "-q", "audits/q1-xai-final-output-equivalence-g5/1.0.0/g5_summary.json"], cwd=ROOT).returncode == 1
    summary = load("external_artifact_summary.json")
    untracked = subprocess.check_output(["git", "ls-files", "--others", "--exclude-standard", "-z"], cwd=ROOT).split(b"\0")
    modified = subprocess.check_output(["git", "diff", "--name-only", "-z"], cwd=ROOT).split(b"\0")
    names = {item.decode() for item in (*untracked, *modified) if item}
    assert summary["git_visible_sprint55_size_bytes_after_object_exclusion"] == sum((ROOT / name).stat().st_size for name in names if (ROOT / name).is_file())


def test_restoration_and_future_publication_fail_closed_policy():
    policy = load("external_artifact_restoration_policy.json")
    assert policy["state"] == "LOCAL_ARTIFACT_PRESERVATION_REQUIRED_UNTIL_SPRINT56"
    assert policy["disposable"] is False
    assert policy["ordinary_git_blob_storage"] == "EXCLUDED"
    assert policy["external_publication_status"] == "DOCUMENTED_NOT_AUTHORIZED_NOT_EXECUTED"
    assert policy["Sprint56_preflight"] == ["REQUIRE_ALL_INVENTORY_PATHS", "VERIFY_EXACT_SIZE", "VERIFY_SHA256", "FAIL_CLOSED_ON_ANY_MISSING_OR_MISMATCH"]


def test_t1_t2_xai_and_mutation_counters_remain_zero():
    governance = load("external_artifact_summary.json")["governance"]
    assert governance["T1_access_count"] == 0
    assert governance["T2_access_count"] == 0
    assert governance["T2_state"] == "DENY_SEALED_REVIEWER_RESERVE"
    assert governance["XAI_execution_count"] == governance["model_query_count"] == governance["fit_count"] == governance["reconstruction_count"] == governance["recalibration_count"] == 0


def test_prior_manifests_and_runtime_evidence_are_unchanged():
    expected = {
        EXECUTION / "MANIFEST.sha256": "994a6f7aa8d1393904c605e0b5d65db6fcd39b9be55a1eb5219f899346b83d2e",
        EXECUTION / "forensics/g3_failure_root_cause/1.0.0/MANIFEST.sha256": "a6f4bd5e5ec43f844860283aef6b3f21933728a5d0817773e7cb1fb742b866e7",
        EXECUTION / "dispositions/block7b_partial_eligibility/1.0.0/MANIFEST.sha256": "6e74700b5deeafb4e70d4e46a07a920df37372aa1f52fd1d17b26d3a7a2fdbeb",
        ROOT / "audits/q1-xai-reconstruction-equivalence-g4/1.0.0/MANIFEST.sha256": "158f52c8cd16e633d11202a86dff467d33838e84617aeaf64d94c361a66f3074",
        ROOT / "audits/q1-xai-final-output-equivalence-g5/1.0.0/MANIFEST.sha256": "a0eaa7d0e0e6e3a119160bab2709f5f16319f6429fdd5cc16e72db311f851f10",
        ROOT / "audits/q1-xai-runtime-freeze/1.0.0/MANIFEST.sha256": "27b12b1f9105c1c9fdbdf9cac9e7a9942ed20f6303586dd54ce84b29c11e5c29",
    }
    assert all(sha256(path) == digest for path, digest in expected.items())


def test_registry_manifest_verifies_and_contains_only_compact_evidence():
    entries = {}
    for line in (REGISTRY / "MANIFEST.sha256").read_text().splitlines():
        digest, name = line.split("  ", 1)
        entries[name] = digest
    assert set(entries) == {"EXTERNAL_ARTIFACT_STORE_REPORT.md", "external_artifact_inventory.jsonl", "external_artifact_restoration_policy.json", "external_artifact_summary.json"}
    assert all(sha256(REGISTRY / name) == digest for name, digest in entries.items())
    assert load("external_artifact_summary.json")["object_bytes_embedded"] is False


def test_source_has_no_object_mutation_model_or_protected_data_path():
    source = (ROOT / "src/evaluation/q1_xai_external_artifact_store_freeze.py").read_text().lower()
    assert "unlink(" not in source
    assert "rmtree" not in source
    assert "rename(" not in source
    assert "open(\"wb\")" not in source[source.index("def snapshot("):source.index("def snapshot_digest(")]
    assert ".fit(" not in source
    assert "predict_proba(" not in source
    assert "t1_rel" not in source
    assert "t2_rel" not in source
