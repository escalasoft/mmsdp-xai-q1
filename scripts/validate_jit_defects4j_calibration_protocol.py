"""Validate and deterministically audit the predeclared calibration protocol."""

from __future__ import annotations

import json
from pathlib import Path

from calibration.jit_defects4j_calibration_protocol import (
    canonical_bytes,
    identity,
    load_and_validate,
)

ROOT = Path(__file__).resolve().parents[1]


def build_audit() -> dict:
    architecture, protocol = load_and_validate(ROOT)
    return {
        "schema_version": "jit-defects4j-calibration-protocol-audit-1.0.0",
        "sprint": "10.8.2.28",
        "branch": "sprint-10/jit-defects4j-calibration-protocol",
        "scientific_decision": "GO",
        "frozen_architecture_identity": identity(architecture),
        "calibration_protocol_identity": identity(protocol),
        "dataset_identity": architecture["dataset"]["identity"],
        "manifest_identity": architecture["dataset"]["manifest_sha256"],
        "frozen_boundary_identity": architecture["dataset"]["frozen_boundary_identity"],
        "adapter_identity": architecture["dataset"]["adapter_identity"],
        "sprint_10_8_2_27_result_identity": architecture["prior_evidence"][
            "result_identity"
        ],
        "primary_predictor": "CODE+TEXT",
        "process_status": architecture["process_status"]["status"],
        "candidate_methods": protocol["candidate_methods"],
        "test_sealed": True,
        "calibration_executed": False,
        "threshold_selection_executed": False,
        "validation_result": "pass",
    }


def main() -> None:
    audit = build_audit()
    path = ROOT / "audits/jit-defects4j-calibration-protocol/1.0.0/audit.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(audit))
    print(json.dumps(audit, sort_keys=True))


if __name__ == "__main__":
    main()
