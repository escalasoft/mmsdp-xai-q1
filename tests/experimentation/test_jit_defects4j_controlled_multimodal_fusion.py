"""Focused integrity tests for Sprint 10.8.2.26."""

# ruff: noqa: E501

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from scipy.sparse import issparse

import experimentation.jit_defects4j_controlled_multimodal_fusion as fusion
from experimentation.jit_defects4j_controlled_baselines import DevelopmentBoundaryError

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs/experiments/jit_defects4j_controlled_multimodal_fusion_1.0.0.json"


def _configuration() -> dict:
    return json.loads(CONFIG.read_text())


def test_configuration_is_complete_fixed_and_predeclared() -> None:
    configuration = _configuration()
    declared = {tuple(item["modalities"]) for item in configuration["fusion_candidates"]}
    assert declared == fusion.REQUIRED_COMBINATIONS
    assert len(configuration["fusion_candidates"]) == 4
    for item in configuration["fusion_candidates"]:
        assert np.allclose(item["weights"], 1 / len(item["modalities"]))
    fusion._validate_configuration(configuration)


def test_invalid_boundary_or_missing_ablation_fails_closed() -> None:
    configuration = _configuration()
    configuration["evaluation_partition"] = "test"
    with pytest.raises(DevelopmentBoundaryError):
        fusion._validate_configuration(configuration)
    configuration = _configuration()
    configuration["fusion_candidates"].pop()
    with pytest.raises(DevelopmentBoundaryError):
        fusion._validate_configuration(configuration)


def test_canonical_alignment_sparse_text_and_test_seal() -> None:
    inputs = fusion.load_development_inputs(ROOT)
    assert len(inputs.train["identities"]) == 19114
    assert sum(inputs.train["targets"]) == 1912
    assert len(inputs.validation["identities"]) == 4086
    assert sum(inputs.validation["targets"]) == 260
    assert not ({tuple(x) for x in inputs.train["identities"]} & {tuple(x) for x in inputs.validation["identities"]})
    text = fusion._matrix(inputs.train, "TEXT")
    assert text.shape == (19114, 5000) and issparse(text)
    with pytest.raises(DevelopmentBoundaryError, match="TEST is sealed"):
        inputs.partition("test")


def test_fusion_is_deterministic_and_does_not_densify_features() -> None:
    scores = {"CODE": np.array([0.2, 0.8]), "TEXT": np.array([0.4, 0.6])}
    first = fusion._fuse(scores, ("CODE", "TEXT"), [0.5, 0.5])
    second = fusion._fuse(scores, ("CODE", "TEXT"), [0.5, 0.5])
    assert np.array_equal(first, second)
    assert np.allclose(first, [0.3, 0.7])


def test_ranking_and_process_delta_are_deterministic() -> None:
    def run(candidate: str, roc: float, ap: float, modalities: list[str]) -> dict:
        return {"candidate_id": candidate, "modalities": modalities, "validation_metrics": {"roc_auc": roc, "average_precision": ap}}
    candidates = [run("b", 0.7, 0.2, ["CODE", "TEXT"]), run("a", 0.7, 0.2, ["CODE", "TEXT"]), run("c", 0.69, 0.3, ["CODE", "TEXT", "PROCESS"])]
    assert [item["candidate_id"] for item in fusion._rank(candidates)] == ["a", "b", "c"]
    assert fusion._delta(run("w", 0.71, 0.22, []), run("x", 0.70, 0.20, [])) == pytest.approx({"roc_auc": 0.01, "average_precision": 0.02})


def test_generated_audit_proves_reproducibility_and_no_test_prediction() -> None:
    audit = json.loads((ROOT / "audits/jit-defects4j-controlled-multimodal-fusion/1.0.0/audit.json").read_text())
    assert audit["test_sealed"] is True
    assert audit["test_metadata"] == {"observations": 4119, "positive": 160, "nominal_negative": 3959}
    assert audit["leakage_checks"]["test_predictor_access"] is False
    assert audit["reproducibility_checks"]["independent_complete_runs"] == 2
    assert len(audit["multimodal_validation_results"]) == 4
    assert set(audit["process_ablation_deltas"]) == {"CODE+PROCESS_minus_CODE", "TEXT+PROCESS_minus_TEXT", "CODE+PROCESS+TEXT_minus_CODE+TEXT"}
