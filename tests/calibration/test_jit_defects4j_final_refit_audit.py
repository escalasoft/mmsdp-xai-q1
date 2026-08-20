import json
from pathlib import Path

import numpy as np
import pytest

from calibration.jit_defects4j_final_refit_audit import (
    FinalRefitAuditError,
    deterministic_development_folds,
    load_inputs,
    run_audit,
)
from experimentation.jit_defects4j_controlled_baselines import DevelopmentBoundaryError

ROOT = Path(__file__).resolve().parents[2]


def config():
    return json.loads(
        (
            ROOT / "configs/experiments/jit_defects4j_final_refit_audit_1.0.0.json"
        ).read_text()
    )


def test_test_access_fails_closed():
    with pytest.raises(DevelopmentBoundaryError, match="TEST is sealed"):
        load_inputs(ROOT).partition("test")


def test_unauthorized_refit_is_rejected():
    changed = config()
    changed["base_fit_population"] = "TRAIN+VALIDATION"
    with pytest.raises(FinalRefitAuditError, match="unauthorized"):
        run_audit(ROOT, load_inputs(ROOT), changed)


def test_equal_weight_and_full_validation_isotonic_contract_is_deterministic():
    first = run_audit(ROOT, load_inputs(ROOT), config())
    second = run_audit(ROOT, load_inputs(ROOT), config())
    assert first == second
    assert first["decision"] == "SPRINT_10.8.2.30_GO"
    assert first["final_contract"]["fusion"]["weights"] == {"CODE": 0.5, "TEXT": 0.5}
    assert first["final_contract"]["calibration"]["fit_population"].startswith(
        "full canonical VALIDATION"
    )
    assert first["final_contract"]["text"]["preprocessing"].startswith(
        "TRAIN-fitted TF-IDF"
    )


def test_deterministic_folds_cover_once_without_self_training():
    y = np.array([0] * 100 + [1] * 20)
    first = deterministic_development_folds(y)
    assert np.array_equal(first, deterministic_development_folds(y))
    assert set(first) == set(range(5))
