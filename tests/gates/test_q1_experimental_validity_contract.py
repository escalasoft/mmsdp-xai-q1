import ast
import json
from pathlib import Path

from scripts.validate_q1_experimental_validity_contract import contract_digest, validate

ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "audits/q1-experimental-validity-contract/1.0.0"


def _artifacts():
    return (
        json.loads((AUDIT / "contract.json").read_text()),
        json.loads((AUDIT / "feature_lineage.json").read_text()),
    )


def test_contract_parses_has_required_governance_and_digest():
    contract, lineage = _artifacts()
    validate(contract, lineage)
    assert contract["contract_digest"] == contract_digest(contract)


def test_modalities_leakage_temporal_factorial_and_persistence_gates():
    contract, lineage = _artifacts()
    assert {row["modality"] for row in lineage["features"]} == {"CODE", "PROCESS", "TEXT"}
    assert lineage["exact_prohibited_overlaps"] == []
    assert contract["temporal_protocol"]["ordinary_shuffled_or_random_kfold_primary_cv"] == "PROHIBITED"
    assert contract["factorial_modality_space"] == ["C", "P", "T", "C+P", "C+T", "P+T", "C+P+T"]
    assert "immutable historical evidence" in contract["inherited_sprint_31_31a_restrictions"]["sprint_31_test"]
    persistence = contract["fitted_state_persistence"]
    assert "configuration_reproducibility" in persistence
    assert "fitted_object_reproducibility" in persistence


def test_validator_is_structural_and_execution_ledger_is_zero():
    contract, _ = _artifacts()
    source_path = ROOT / "scripts/validate_q1_experimental_validity_contract.py"
    tree = ast.parse(source_path.read_text())
    imports = {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    imports |= {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    assert not any(name.startswith(("src.models", "src.evaluation", "src.calibration", "src.explainability")) for name in imports)
    assert contract["execution_ledger"]["model_training"] == 0
    assert contract["execution_ledger"]["predictive_test_or_final_scoring"] == 0
    assert contract["execution_ledger"]["calibration_fitting"] == 0
    assert contract["execution_ledger"]["xai_execution"] == 0
