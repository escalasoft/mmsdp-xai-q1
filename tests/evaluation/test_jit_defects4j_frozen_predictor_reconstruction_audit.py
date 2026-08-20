from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from evaluation.jit_defects4j_frozen_predictor_reconstruction_audit import (
    ReconstructionAuditError,
    _audit_test_artifact,
    _validate,
    load_configuration,
)

ROOT = Path(__file__).resolve().parents[2]


def test_contract_rejects_test_scoring_or_process() -> None:
    configuration = load_configuration(ROOT)
    for key, value in (
        ("test_predictive_scoring", True),
        ("primary_modalities", ["CODE", "TEXT", "PROCESS"]),
        ("classification_threshold", 0.5),
        ("base_fit_population", "TRAIN+VALIDATION"),
    ):
        changed = deepcopy(configuration)
        changed[key] = value
        with pytest.raises(ReconstructionAuditError, match="unauthorized"):
            _validate(changed)


def test_sealed_test_artifact_is_audited_without_predictive_scoring() -> None:
    result = _audit_test_artifact(ROOT, load_configuration(ROOT))
    assert result["integrity_pass"] is True
    assert result["predictive_scoring_executed"] is False
    assert result["row_count"] == 4119
    assert result["canonical_order_and_targets_match"] is True
    assert result["raw_fusion_exact"] is True
    assert result["calibrated_probabilities_exact"] is True
    assert result["reported_metrics_match"] is True
