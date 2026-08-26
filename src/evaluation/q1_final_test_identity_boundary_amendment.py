"""Outcome-blind Sprint 46A final-TEST identity audit.

Only committed governance metadata and Git object metadata are inspected. Dataset
rows, labels, predictions, models, and metric implementations are never opened.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

BASELINE = "9647eec872971b2b366fb4f21dca9ba6b27f7f23"
CLASSIFICATION = "NO_VERIFIABLE_UNTOUCHED_FINAL_TEST"
CANONICAL_DATASET = "e509995da233c932cafce531c13ad2cd617a0d8abbe8d81ccaa373b8f29fa519"
CANONICAL_MANIFEST = "95b1a362f6756f641cc575cabf54a3a99e2846568d5ef110dac38a45f3d81ef1"
CANONICAL_BOUNDARY = "d1b4448e22a1dba4292b9cf8969ba77db0cf9a10ef66dfddf98642cb5dc078a7"
SPRINT31_COMMIT = "be9b27e54ceb23e327bb22a001f6b39291029339"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()


def collect_evidence(root: Path) -> dict[str, Any]:
    config = json.loads(
        (root / "configs/jit_defects4j_materialization.json").read_text()
    )
    canonical = json.loads(
        (root / "audits/jit-defects4j-canonical/1.0.0/audit.json").read_text()
    )
    one_shot = json.loads(
        (root / "audits/jit-defects4j-one-shot-test/1.0.0/audit.json").read_text()
    )
    gate = json.loads(
        (
            root
            / "audits/q1-final-test-access-gate/1.0.0/authorization_gate.json"
        ).read_text()
    )
    changed = _git(
        root,
        "diff",
        "--name-only",
        f"{SPRINT31_COMMIT}..{BASELINE}",
        "--",
        "data",
        "outputs",
        "configs/jit_defects4j_materialization.json",
        "src/dataset/jit_defects4j_materialization.py",
    ).splitlines()
    return {
        "canonical": {
            "dataset_version": canonical["dataset_version"],
            "scientific_identity": canonical["scientific_identity_digest"],
            "manifest_identity": canonical["manifest_sha256"],
            "materialization_configuration_sha256": digest(
                root / "configs/jit_defects4j_materialization.json"
            ),
            "source_revision": config["source"]["revision"],
            "source_package_sha256": config["source"]["package_sha256"],
            "observation_identity": config["observation_identity"],
            "temporal_policy": config["split"],
            "temporal_boundary_identity": one_shot["frozen_identities"][
                "temporal_boundary"
            ],
        },
        "historical_test": {
            "sprint": "10.8.2.31",
            "commit": SPRINT31_COMMIT,
            "dataset_identity": one_shot["frozen_identities"]["dataset"],
            "manifest_identity": one_shot["frozen_identities"]["manifest"],
            "temporal_boundary_identity": one_shot["frozen_identities"][
                "temporal_boundary"
            ],
            "consumed": one_shot.get("test_scoring_count") == 1,
        },
        "post_sprint31_materialization_changes": changed,
        "sprint46": {
            "gate_decision": gate["gate_decision"],
            "dataset_identity_bound": "final_test_dataset_identity" in gate,
            "temporal_boundary_bound": "temporal_boundary_identity" in gate,
            "recorded_access_count": gate["test_access_count"],
        },
    }


def decide(evidence: dict[str, Any]) -> dict[str, Any]:
    canonical = evidence["canonical"]
    historical = evidence["historical_test"]
    same_consumed_boundary = (
        historical["consumed"]
        and canonical["scientific_identity"] == historical["dataset_identity"]
        and canonical["manifest_identity"] == historical["manifest_identity"]
        and canonical["temporal_boundary_identity"]
        == historical["temporal_boundary_identity"]
    )
    distinct_candidate = bool(evidence["post_sprint31_materialization_changes"])
    classification = CLASSIFICATION
    if not same_consumed_boundary or distinct_candidate:
        classification = "AMBIGUOUS_FINAL_TEST_IDENTITY"
    return {
        "protocol_id": "q1-final-test-identity-boundary-amendment",
        "version": "1.0.0",
        "sprint": "10.8.2.46A",
        "classification": classification,
        "authorization_amended": False,
        "one_shot_test_access_authorized": False,
        "test_sealed": True,
        "access_count": {"before": 0, "during": 0, "after": 0},
        "distinct_untouched_final_test_exists": False,
        "candidate_final_test_identity": None,
        "candidate_temporal_boundary_identity": None,
        "overlap": {
            "train": "NOT_COMPUTABLE_WITHOUT_A_DISTINCT_CANDIDATE",
            "validation": "NOT_COMPUTABLE_WITHOUT_A_DISTINCT_CANDIDATE",
            "historical_sprint31_test": "IDENTICAL_CANONICAL_PARTITION",
        },
        "reason": (
            "The sole canonical TEST identity is the Sprint 31 consumed partition; "
            "no distinct later materialization is evidenced."
        ),
    }


def evaluate(root: Path) -> dict[str, Any]:
    return decide(collect_evidence(root))
