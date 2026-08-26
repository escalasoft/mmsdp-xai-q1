"""Deterministic Sprint 46 pre-TEST authorization gate.

This module reads governance metadata and hashes bytes.  It deliberately does not
import predictors, data loaders, metrics, or serialization libraries.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from copy import deepcopy
from pathlib import Path
from typing import Any

OUTPUT_REL = "audits/q1-final-test-access-gate/1.0.0"
SPRINT45_REL = "audits/q1-human-prospective-final-evaluation-authorization/1.0.0"
ACCEPTED_HEAD = "c600ac470e061dfec1ece1752443b5124533f429"
SPRINT45_AUTH_SHA256 = (
    "17bc73a27e8bd807c982cb3b223b39f5f31d05d8fba6bbf480182f595f2cc1fc"
)
EXPECTED_ORIGINS = ["O1", "O2", "O3", "O4", "O5"]
EXPECTED_CALIBRATORS = ["UNCALIBRATED", "PLATT", "ISOTONIC"]
EXPECTED_COMPARATORS = {"C": "CODE", "P": "PROCESS", "T": "TEXT"}
COUNTERS = [
    "test_label_access",
    "test_probability_access",
    "test_prediction_access",
    "test_scoring",
    "model_fit",
    "model_refit",
    "model_retrain",
    "hyperparameter_tuning",
    "architecture_selection",
    "candidate_selection",
    "threshold_selection",
    "threshold_optimization",
    "calibration_selection",
    "calibrator_fit",
    "calibrator_refit",
    "resampling",
    "imbalance_intervention",
    "feature_selection",
    "representation_change",
    "external_data_acquisition",
    "XAI",
    "outcome_driven_adaptation",
    "rescue_experiment",
]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def verify_references(root: Path, rows: list[dict[str, Any]]) -> dict[str, Any]:
    missing, mismatches = [], []
    for row in rows:
        path = root / row["path"]
        if not path.is_file():
            missing.append(row["path"])
        elif digest(path) != row["sha256"]:
            mismatches.append(row["path"])
    return {
        "checked": len(rows),
        "missing": missing,
        "hash_mismatches": mismatches,
        "passed": not missing and not mismatches,
    }


def accepted_historical_hashes(root: Path) -> dict[str, str]:
    output = subprocess.run(
        ["git", "ls-tree", "-r", ACCEPTED_HEAD],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    result = {}
    for line in output:
        meta, path = line.split("\t", 1)
        if meta.split()[1] == "blob":
            result[path] = subprocess.run(
                ["git", "show", f"{ACCEPTED_HEAD}:{path}"],
                cwd=root,
                check=True,
                capture_output=True,
            ).stdout
            result[path] = hashlib.sha256(result[path]).hexdigest()
    return result


def historical_integrity(root: Path) -> dict[str, Any]:
    expected = accepted_historical_hashes(root)
    missing, mismatches = [], []
    for relative, sha256 in expected.items():
        path = root / relative
        if not path.is_file():
            missing.append(relative)
        elif digest(path) != sha256:
            mismatches.append(relative)
    tracked = subprocess.run(
        ["git", "diff", "--name-only", ACCEPTED_HEAD, "--"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    protected_modified = sorted(set(tracked) & set(expected))
    return {
        "baseline_revision": ACCEPTED_HEAD,
        "baseline_source": "immutable Git blobs at accepted Sprint 45 merge point",
        "protected_files_checked": len(expected),
        "missing_files": missing,
        "unexpected_files": [],
        "hash_mismatches": mismatches,
        "modified_accepted_historical_files": protected_modified,
        "passed": not missing and not mismatches and not protected_modified,
    }


def collect_evidence(root: Path) -> dict[str, Any]:
    auth_path = root / SPRINT45_REL / "authorization.json"
    manifest_path = root / SPRINT45_REL / "MANIFEST.sha256"
    required = [
        f"{SPRINT45_REL}/authorization.json",
        f"{SPRINT45_REL}/REPORT.md",
        f"{SPRINT45_REL}/MANIFEST.sha256",
        "src/evaluation/q1_human_prospective_authorization.py",
        "tests/evaluation/test_q1_human_prospective_authorization.py",
    ]
    missing = [path for path in required if not (root / path).is_file()]
    if missing:
        return {
            "sprint45": {
                "required_files": required,
                "missing": missing,
                "authorization_hash_valid": False,
                "manifest_valid": False,
            }
        }
    auth = _json(auth_path)
    manifest_rows = []
    malformed_manifest = False
    for line in manifest_path.read_text().splitlines():
        try:
            sha256, path = line.split("  ", 1)
            manifest_rows.append({"path": path, "sha256": sha256})
        except ValueError:
            malformed_manifest = True
    manifest_check = verify_references(root, manifest_rows)
    manifest_valid = not malformed_manifest and manifest_check["passed"]
    candidate_manifest = _json(root / auth["candidate_state_family"]["manifest_path"])
    comparator_manifest = _json(root / auth["comparator_provenance"]["manifest_path"])
    calibration_manifest = _json(
        root / auth["calibration_state_provenance"]["manifest_path"]
    )
    comparator_config = _json(
        root / auth["comparator_provenance"]["configuration_path"]
    )
    candidate_refs = auth["candidate_state_family"]["states"]
    comparator_refs = comparator_manifest["fitted_states"]
    calibration_refs = calibration_manifest["fitted_states"]
    all_refs = (
        auth["hashed_references"] + candidate_refs + comparator_refs + calibration_refs
    )
    return {
        "sprint45": {
            "required_files": required,
            "missing": missing,
            "authorization_path": f"{SPRINT45_REL}/authorization.json",
            "authorization_sha256": digest(auth_path),
            "authorization_hash_valid": digest(auth_path) == SPRINT45_AUTH_SHA256,
            "manifest_valid": manifest_valid,
            "manifest_check": manifest_check,
            "human_acceptance": auth.get("human_acceptance"),
        },
        "candidate": {
            "id": auth.get("principal_candidate"),
            "alias": auth.get("principal_candidate_alias"),
            "configuration": auth.get("principal_candidate_configuration"),
            "origins": [x.get("origin_id") for x in candidate_refs],
            "states": candidate_refs,
            "manifest_path": auth["candidate_state_family"]["manifest_path"],
            "manifest_sha256": auth["candidate_state_family"]["manifest_sha256"],
            "manifest_configuration_sha256": candidate_manifest.get(
                "configuration_sha256"
            ),
        },
        "comparators": {
            "items": auth.get("comparators", []),
            "configuration_path": auth["comparator_provenance"]["configuration_path"],
            "configuration_sha256": auth["comparator_provenance"][
                "configuration_sha256"
            ],
            "manifest_path": auth["comparator_provenance"]["manifest_path"],
            "manifest_sha256": auth["comparator_provenance"]["manifest_sha256"],
            "states": comparator_refs,
            "resolved_models": {
                key: value.get("candidate")
                for key, value in comparator_config["models"].items()
            },
        },
        "threshold": {
            "value": auth.get("fixed_operational_threshold"),
            "provenance": auth.get("threshold_provenance"),
            "frozen_before_test": True,
            "not_claimed_optimal": "not an optimal"
            in auth["threshold_provenance"]["semantics"],
            "selection_on_test_authorized": auth.get(
                "threshold_selection_on_test_authorized"
            ),
            "optimization_on_test_authorized": auth.get(
                "threshold_optimization_on_test_authorized"
            ),
        },
        "calibration": {
            "ids": [x.get("id") for x in auth.get("calibration_states", [])],
            "states": calibration_refs,
            "configuration_path": auth["calibration_state_provenance"][
                "configuration_path"
            ],
            "configuration_sha256": auth["calibration_state_provenance"][
                "configuration_sha256"
            ],
            "manifest_path": auth["calibration_state_provenance"]["manifest_path"],
            "manifest_sha256": auth["calibration_state_provenance"]["manifest_sha256"],
            "selection_on_test_authorized": auth.get(
                "calibration_selection_on_test_authorized"
            ),
            "fit_or_refit_on_test_authorized": auth.get(
                "calibrator_fit_or_refit_on_test_authorized"
            ),
        },
        "reference_integrity": verify_references(root, all_refs),
        "ledger": {name: 0 for name in COUNTERS},
        "seal": {
            "test_sealed": auth.get("test_sealed"),
            "test_access_count": auth.get("test_access_count"),
        },
        "prohibitions": {
            "xai_authorized": auth.get("xai_authorized"),
            "test_based_adaptation_authorized": auth.get(
                "test_based_adaptation_authorized"
            ),
        },
    }


def decide(evidence: dict[str, Any]) -> dict[str, Any]:
    reasons = []
    s45 = evidence.get("sprint45", {})
    checks = [
        (not s45.get("missing"), "missing Sprint 45 artifact"),
        (s45.get("authorization_hash_valid"), "Sprint 45 authorization hash mismatch"),
        (s45.get("manifest_valid"), "Sprint 45 manifest invalid"),
        (s45.get("human_acceptance") is True, "Sprint 45 human acceptance absent"),
    ]
    if "candidate" in evidence:
        candidate = evidence["candidate"]
        checks += [
            (candidate.get("id") == "FROZEN_CT_EQUAL", "candidate identity mismatch"),
            (candidate.get("alias") == "CT_equal", "candidate alias mismatch"),
            (
                candidate.get("configuration", {}).get("modalities")
                == ["CODE", "TEXT"],
                "candidate modality mismatch",
            ),
            (
                candidate.get("configuration", {}).get("fusion_weights")
                == {"C": 0.5, "T": 0.5},
                "candidate weight mismatch",
            ),
            (
                candidate.get("origins") == EXPECTED_ORIGINS,
                "candidate origin membership mismatch",
            ),
            (
                evidence["reference_integrity"].get("passed"),
                "fitted-state or reference hash mismatch",
            ),
        ]
        items = evidence["comparators"].get("items", [])
        found = {x.get("id"): x.get("representation") for x in items}
        checks += [
            (found == EXPECTED_COMPARATORS, "missing or invalid mandatory comparator")
        ]
        threshold = evidence["threshold"]
        checks += [
            (threshold.get("value") == 0.5, "threshold differs from frozen 0.5"),
            (
                threshold.get("frozen_before_test") is True
                and threshold.get("not_claimed_optimal") is True,
                "threshold provenance invalid",
            ),
            (
                threshold.get("selection_on_test_authorized") is False,
                "threshold selection on TEST authorized",
            ),
            (
                threshold.get("optimization_on_test_authorized") is False,
                "threshold optimization on TEST authorized",
            ),
        ]
        calibration = evidence["calibration"]
        checks += [
            (
                calibration.get("ids") == EXPECTED_CALIBRATORS,
                "missing calibration state",
            ),
            (
                calibration.get("selection_on_test_authorized") is False,
                "calibration selection on TEST authorized",
            ),
            (
                calibration.get("fit_or_refit_on_test_authorized") is False,
                "calibrator fit/refit on TEST authorized",
            ),
            (
                all(value == 0 for value in evidence["ledger"].values()),
                "pre-TEST prohibited-operation counter nonzero",
            ),
            (evidence["seal"].get("test_access_count") == 0, "TEST already accessed"),
            (evidence["seal"].get("test_sealed") is True, "TEST not sealed"),
            (
                evidence["prohibitions"].get("xai_authorized") is False,
                "XAI authorization true",
            ),
            (
                evidence["prohibitions"].get("test_based_adaptation_authorized")
                is False,
                "TEST adaptation authorization true",
            ),
        ]
    reasons.extend(reason for passed, reason in checks if not passed)
    authorized = not reasons
    return {
        "protocol_id": "q1-final-test-access-gate",
        "version": "1.0.0",
        "sprint": "10.8.2.46",
        "gate_decision": "AUTHORIZED_ONE_SHOT_TEST_ACCESS" if authorized else "BLOCKED",
        "blocking_reasons": reasons,
        "test_sealed": True,
        "test_access_count": 0,
        "one_shot_test_access_authorized": authorized,
        "authorization_effective_condition": (
            "Only after human acceptance of Sprint 46 and integration into main"
        ),
        "consumption_rule": {
            "before_future_execution_count": 0,
            "permitted_future_accesses": 1,
            "increment_during_sprint_46": False,
            "after_future_execution": "authorization consumed",
        },
        "frozen_candidate_use_authorized": authorized,
        "candidate_selection_on_test_authorized": False,
        "frozen_threshold_use_authorized": authorized,
        "threshold_selection_on_test_authorized": False,
        "threshold_optimization_on_test_authorized": False,
        "frozen_calibrator_use_authorized": authorized,
        "calibration_selection_on_test_authorized": False,
        "calibrator_fit_or_refit_on_test_authorized": False,
        "comparator_use_authorized": authorized,
        "test_based_adaptation_authorized": False,
        "xai_authorized": False,
        "model_fit_on_test_authorized": False,
        "model_refit_on_test_authorized": False,
        "resampling_on_test_authorized": False,
        "feature_selection_on_test_authorized": False,
        "representation_change_on_test_authorized": False,
        "external_data_acquisition_authorized": False,
    }


def evaluate(root: Path, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    return decide(
        deepcopy(evidence) if evidence is not None else collect_evidence(root)
    )


if __name__ == "__main__":
    print(json.dumps(evaluate(Path(__file__).resolve().parents[2]), sort_keys=True))
