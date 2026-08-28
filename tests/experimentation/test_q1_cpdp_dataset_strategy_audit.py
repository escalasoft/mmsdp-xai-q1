"""Fail-closed tests for the non-executing Sprint 10.8.2.48A audit."""

import json
from pathlib import Path

from experimentation.q1_cpdp_dataset_strategy_audit import generate, validate


def test_audit_is_deterministic_complete_and_sealed(tmp_path: Path) -> None:
    out = generate(tmp_path)
    first = {p.name: p.read_bytes() for p in out.iterdir()}
    assert validate(out) == []
    generate(tmp_path)
    assert first == {p.name: p.read_bytes() for p in out.iterdir()}
    blueprint = json.loads((out / "campaign_blueprint.json").read_text())
    evidence = json.loads((out / "evidence_inventory.json").read_text())
    assert blueprint["classification"] == "BLOCKED_MISSING_DATASET_EVIDENCE"
    assert blueprint["execution_authorized"] is False
    assert blueprint["target_test_access_count"] == 0
    assert evidence["prohibited_payloads_opened"] == []


def test_matrix_is_minimal_factorial_and_unique(tmp_path: Path) -> None:
    matrix = json.loads((generate(tmp_path) / "experimental_matrix.json").read_text())
    assert matrix["total"] == len(matrix["cells"]) == 720
    assert len({cell["id"] for cell in matrix["cells"]}) == 720
    assert {cell["design"] for cell in matrix["cells"]} == {"WPDP", "LOPO_CPDP"}
    assert all(cell["status"] == "BLOCKED" for cell in matrix["cells"])
    calibrated = [c for c in matrix["cells"] if c["calibration"] != "UNCALIBRATED"]
    assert len(calibrated) == 160
    assert {c["modality"] for c in calibrated} == {"C+P+T"}


def test_validator_detects_access_and_manifest_tampering(tmp_path: Path) -> None:
    out = generate(tmp_path)
    path = out / "campaign_blueprint.json"
    value = json.loads(path.read_text())
    value["target_test_access_count"] = 1
    path.write_text(json.dumps(value))
    errors = validate(out)
    assert "campaign must remain unauthorized with zero target accesses" in errors
    assert "manifest mismatch: campaign_blueprint.json" in errors
