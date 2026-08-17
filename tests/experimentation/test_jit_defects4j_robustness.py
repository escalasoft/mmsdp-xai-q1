"""Focused integrity tests for Sprint 10.8.2.27."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from experimentation.jit_defects4j_controlled_baselines import DevelopmentBoundaryError
from experimentation.jit_defects4j_robustness import (
    load_development_inputs,
    paired_bootstrap,
    validate_configuration,
    verify_identities,
)

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs/experiments/jit_defects4j_robustness_1.0.0.json"


def configuration() -> dict:
    return json.loads(CONFIG.read_text())


def test_protocol_and_frozen_identities_are_exact() -> None:
    value = configuration()
    validate_configuration(value)
    assert verify_identities(ROOT, value) == value["expected_identities"]


def test_protocol_mutation_fails_closed() -> None:
    value = configuration()
    value["evaluation_partition"] = "test"
    with pytest.raises(DevelopmentBoundaryError):
        validate_configuration(value)
    value = configuration()
    value["seed_set"].append(999)
    with pytest.raises(DevelopmentBoundaryError):
        validate_configuration(value)


def test_test_partition_is_inaccessible() -> None:
    inputs = load_development_inputs(ROOT)
    with pytest.raises(DevelopmentBoundaryError, match="TEST is sealed"):
        inputs.partition("test")


def test_paired_bootstrap_is_deterministic() -> None:
    y = np.array([0, 0, 1, 1, 0, 1])
    scores = {
        "CODE": np.array([0.1, 0.4, 0.6, 0.8, 0.2, 0.7]),
        "TEXT": np.array([0.2, 0.3, 0.7, 0.6, 0.1, 0.9]),
        "CODE+TEXT": np.array([0.15, 0.35, 0.65, 0.7, 0.15, 0.8]),
    }
    assert paired_bootstrap(y, scores, 20, 42) == paired_bootstrap(y, scores, 20, 42)


def test_generated_audit_contract_when_present() -> None:
    path = ROOT / "audits/jit-defects4j-robustness/1.0.0/audit.json"
    if not path.exists():
        pytest.skip("audit not generated yet")
    audit = json.loads(path.read_text())
    assert audit["test_sealed"] is True
    assert all(value is False for value in audit["test_seal_checks"].values())
    assert audit["reproducibility"]["result"] == "pass"
    assert audit["primary_candidate"] == "CODE+TEXT"
