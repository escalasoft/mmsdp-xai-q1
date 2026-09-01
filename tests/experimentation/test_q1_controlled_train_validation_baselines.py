from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from experimentation.q1_controlled_train_validation_baselines import (
    EXPECTED_PROJECTS,
    execute_pilot,
    execute_pilot_once,
    load_development_project,
    metric_values,
    verify_frozen_inputs,
    verify_manifest,
)

ROOT = Path(__file__).resolve().parents[2]
FREEZE = ROOT / "audits/q1-apachejit-final-dataset-freeze/1.0.0"
CONFIG = ROOT / (
    "configs/experiments/q1_controlled_train_validation_baselines_1.0.0.json"
)


def test_frozen_manifest_and_inputs_pass() -> None:
    assert len(verify_manifest(FREEZE)) == 26
    result = verify_frozen_inputs(ROOT)
    assert result["status"] == "PASS"
    assert result["eligible_projects"] == list(EXPECTED_PROJECTS)
    assert result["row_count"] == 94710
    assert result["labels"]["positive"] == 28239
    assert result["labels"]["negative"] == 66471
    assert result["cross_payload_row_identity_and_order_match"] is True


def test_pilot_loader_materializes_development_only() -> None:
    rows = load_development_project(ROOT, min(EXPECTED_PROJECTS))
    assert len(rows) == 4900
    assert {row["partition"] for row in rows} == {"TRAIN", "VALIDATION"}
    assert all(row["project"] == "apache/activemq" for row in rows)


def test_metrics_are_finite_and_correct_for_perfect_scores() -> None:
    values = metric_values(np.asarray([0, 0, 1, 1]), np.asarray([0.1, 0.2, 0.8, 0.9]))
    assert values["ROC_AUC"] == 1.0
    assert values["PR_AUC"] == 1.0
    assert values["F1"] == 1.0
    assert values["MCC"] == 1.0


def test_controlled_pilot_is_reproducible_and_test_denied() -> None:
    result = execute_pilot(ROOT)
    assert result["status"] == "PASS"
    assert result["reproducibility"] is True
    assert len(set(result["repeat_run_scientific_sha256"])) == 1
    pilot = result["pilot"]
    assert pilot["pilot_project"] == "apache/activemq"
    assert pilot["predictive_partitions_materialized"] == ["TRAIN", "VALIDATION"]
    assert pilot["t1_predictive_access_count"] == 0
    assert pilot["t2_predictive_access_count"] == 0
    assert pilot["final_test_metric_count"] == 0
    assert (
        pilot["fusion_C+P+T"]["meta_training_source"]
        == "STRICT_FORWARD_OUT_OF_FOLD_TRAIN"
    )
    assert all(
        fold["fit_prediction_disjoint"] and fold["strict_forward_time"]
        for fold in pilot["fusion_C+P+T"]["folds"]
    )


def test_single_pilot_uses_frozen_lr_contract() -> None:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    result = execute_pilot_once(ROOT, "apache/activemq", config)
    assert result["algorithm"] == "Logistic Regression"
    assert set(result["base_results"]) == {"C", "P", "T"}
    assert result["fusion_C+P+T"]["strategy"] == "STACKING_LATE_FUSION"
