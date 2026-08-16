"""Focused fail-closed tests for Sprint 10.8.2.25."""

# ruff: noqa: E501

from __future__ import annotations

import json
from pathlib import Path

import pytest
from scipy.sparse import issparse

import experimentation.jit_defects4j_controlled_baselines as baseline

ROOT = Path(__file__).resolve().parents[2]


def _configuration() -> dict:
    return json.loads(
        (
            ROOT / "configs/experiments/jit_defects4j_controlled_baselines_1.0.0.json"
        ).read_text()
    )


def test_real_frozen_inputs_preserve_identity_dimensions_and_sparse_text() -> None:
    inputs = baseline.load_development_inputs(ROOT)
    assert len(inputs.train["identities"]) == 19114
    assert len(inputs.validation["identities"]) == 4086
    assert not (
        {tuple(x) for x in inputs.train["identities"]}
        & {tuple(x) for x in inputs.validation["identities"]}
    )
    assert baseline._matrix(inputs.train, "CODE").shape == (19114, 6)
    assert baseline._matrix(inputs.train, "PROCESS").shape == (19114, 4)
    text = baseline._matrix(inputs.train, "TEXT")
    assert text.shape == (19114, 5000)
    assert issparse(text)


def test_test_access_is_rejected() -> None:
    inputs = baseline.load_development_inputs(ROOT)
    with pytest.raises(baseline.DevelopmentBoundaryError, match="TEST is sealed"):
        inputs.partition("test")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("fit_partition", "validation"),
        ("evaluation_partition", "test"),
        ("sealed_partition", "validation"),
    ],
)
def test_boundary_configuration_fails_closed(field: str, value: object) -> None:
    configuration = _configuration()
    configuration[field] = value
    with pytest.raises(baseline.DevelopmentBoundaryError):
        baseline.run_development_baselines(
            baseline.load_development_inputs(ROOT), configuration
        )


def test_candidate_specification_is_small_deterministic_and_unweighted() -> None:
    configuration = _configuration()
    assert [item["C"] for item in configuration["models"]["LR"]] == [0.1, 1.0]
    assert len(configuration["models"]["RF"]) == 2
    assert all(
        item["random_state"] == 0 and item["class_weight"] is None
        for family in configuration["models"].values()
        for item in family
    )
    assert "test-access" in configuration["prohibited_operations"]


def test_audit_schema_and_repeated_run_identity() -> None:
    path = ROOT / "audits/jit-defects4j-controlled-baselines/1.0.0/audit.json"
    audit = json.loads(path.read_text())
    required = {
        "sprint",
        "decision",
        "dataset_identity",
        "frozen_boundary_identity",
        "adapter_identity",
        "test_sealed",
        "train",
        "validation",
        "modalities",
        "candidate_models",
        "selected_development_candidates",
        "reproducibility",
        "limitations",
    }
    assert required <= set(audit)
    assert audit["test_sealed"] is True
    assert audit["reproducibility"]["machine_readable_results_identical"] is True
    assert len(audit["candidate_models"]) == 12
    assert all(
        "validation_metrics" in run and "test" not in run
        for run in audit["candidate_models"]
    )
