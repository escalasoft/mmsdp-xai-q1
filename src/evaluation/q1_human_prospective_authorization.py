"""Validate Sprint 45 prospective human authorization without accessing TEST."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

OUTPUT_REL = "audits/q1-human-prospective-final-evaluation-authorization/1.0.0"
SPRINT44_COMMIT = "f1c6aa385da81a5f46a70db7ad428f500e4db2e6"
PRE_MATERIALIZATION_HEAD = "f0791c22e6d90b4055ecffab956bb072ed6e7650"
CONTRACT_PATH = "audits/q1-predeclared-final-performance-contract/1.0.0/final_performance_contract.json"
CONTRACT_SHA256 = "15c02b6e46b9a45b5848a5713259a5dbd8c45038da41708fa08a163a51b761f9"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(root: Path) -> dict[str, Any]:
    return json.loads((root / OUTPUT_REL / "authorization.json").read_text())


def historical_modifications(root: Path) -> list[str]:
    rows = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    allowed = (OUTPUT_REL + "/", "src/evaluation/q1_human_prospective_authorization.py", "tests/evaluation/test_q1_human_prospective_authorization.py")
    return sorted(row[3:] for row in rows if not row[3:].startswith(allowed))


def validate(root: Path) -> dict[str, Any]:
    value = load(root)
    assert digest(root / CONTRACT_PATH) == CONTRACT_SHA256
    assert value["human_acceptance"] is True
    assert value["human_acceptance_scope"] == "PROSPECTIVE_PRE_TEST_FINAL_EVALUATION_GOVERNANCE"
    assert value["principal_candidate"] == "FROZEN_CT_EQUAL"
    assert value["frozen_candidate_use_authorized"] is True
    assert value["candidate_selection_on_test_authorized"] is False
    assert value["fixed_operational_threshold"] == 0.5
    assert value["frozen_threshold_use_authorized"] is True
    assert value["threshold_selection_on_test_authorized"] is False
    assert value["threshold_optimization_on_test_authorized"] is False
    assert [row["id"] for row in value["calibration_states"]] == ["UNCALIBRATED", "PLATT", "ISOTONIC"]
    assert value["calibration_selection_on_test_authorized"] is False
    assert value["calibrator_fit_or_refit_on_test_authorized"] is False
    assert [row["id"] for row in value["comparators"]] == ["C", "P", "T"]
    assert value["one_shot_test_access_authorized"] is False
    assert value["test_based_adaptation_authorized"] is False
    assert value["xai_authorized"] is False
    assert value["test_sealed"] is True
    assert value["test_access_count"] == 0
    for state in value["candidate_state_family"]["states"]:
        assert digest(root / state["path"]) == state["sha256"]
    calibration_manifest = json.loads(
        (root / value["calibration_state_provenance"]["manifest_path"]).read_text()
    )
    assert [row["sha256"] for row in calibration_manifest["fitted_states"]] == value[
        "calibration_state_provenance"
    ]["fitted_state_sha256"]
    comparator_config = json.loads(
        (root / value["comparator_provenance"]["configuration_path"]).read_text()
    )
    assert [comparator_config["models"][row["id"]]["candidate"] for row in value["comparators"]] == [
        row["model_candidate"] for row in value["comparators"]
    ]
    comparator_manifest = json.loads(
        (root / value["comparator_provenance"]["manifest_path"]).read_text()
    )
    assert [row["sha256"] for row in comparator_manifest["fitted_states"]] == value[
        "comparator_provenance"
    ]["fitted_state_sha256"]
    for reference in value["hashed_references"]:
        assert digest(root / reference["path"]) == reference["sha256"]
    manifest = root / OUTPUT_REL / "MANIFEST.sha256"
    for line in manifest.read_text().splitlines():
        expected, relative = line.split("  ", 1)
        assert digest(root / relative) == expected
    assert not historical_modifications(root)
    return {"status": "PASS", "test_sealed": True, "test_access_count": 0}


if __name__ == "__main__":
    print(json.dumps(validate(Path(__file__).resolve().parents[2]), sort_keys=True))
