"""Validate and canonically identify the Sprint 10.8.2.33 contract.

This script performs structural governance checks only. It imports no modeling,
calibration, evaluation, or explainability module and reads no predictive data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "audits/q1-experimental-validity-contract/1.0.0"


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def contract_digest(contract: dict[str, object]) -> str:
    content = dict(contract)
    content.pop("contract_digest", None)
    return hashlib.sha256(canonical_bytes(content)).hexdigest()


def validate(contract: dict[str, object], lineage: dict[str, object]) -> None:
    required = {
        "schema_version", "sprint_identity", "repository", "dataset",
        "experimental_unit_and_target", "feature_lineage", "leakage_denylist",
        "temporal_protocol", "new_campaign_test_governance",
        "fitted_state_persistence", "factorial_modality_space",
        "fusion_governance", "calibration_governance",
        "external_validation_eligibility", "xai_governance",
        "inherited_sprint_31_31a_restrictions", "execution_ledger",
        "contract_digest",
    }
    assert required <= contract.keys()
    assert {item["modality"] for item in lineage["features"]} == {"CODE", "PROCESS", "TEXT"}
    assert len(lineage["features"]) == 11
    assert lineage["exact_prohibited_overlaps"] == []
    assert contract["leakage_denylist"]["exact_predictor_overlaps"] == []
    temporal = contract["temporal_protocol"]
    assert temporal["ordinary_shuffled_or_random_kfold_primary_cv"] == "PROHIBITED"
    assert temporal["canonical_order"] == ["git_committer_timestamp", "commit_hash"]
    assert contract["factorial_modality_space"] == ["C", "P", "T", "C+P", "C+T", "P+T", "C+P+T"]
    inherited = contract["inherited_sprint_31_31a_restrictions"]
    assert "immutable" in inherited["sprint_31_test"]
    persistence = contract["fitted_state_persistence"]
    assert persistence["configuration_reproducibility"] != persistence["fitted_object_reproducibility"]
    assert len(persistence["required_components"]) >= 16
    assert contract["execution_ledger"] == {
        "model_training": 0,
        "predictive_test_or_final_scoring": 0,
        "calibration_fitting": 0,
        "xai_execution": 0,
        "external_dataset_acquisition": 0,
    }
    assert contract["contract_digest"] == contract_digest(contract)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-digest", action="store_true")
    args = parser.parse_args()
    contract_path = AUDIT / "contract.json"
    lineage_path = AUDIT / "feature_lineage.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    lineage = json.loads(lineage_path.read_text(encoding="utf-8"))
    if args.write_digest:
        contract["feature_lineage"]["artifact_sha256"] = hashlib.sha256(
            lineage_path.read_bytes()
        ).hexdigest()
        contract["contract_digest"] = contract_digest(contract)
        contract_path.write_bytes(canonical_bytes(contract))
    validate(contract, lineage)
    print(f"PASS contract_digest={contract['contract_digest']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
