"""Fail-closed tests for Sprint 10.8.2.20 Qt baselines."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest
from tests.dataset.test_qt_model_input_adaptation import _split

import experimentation.qt_unimodal_baselines as boundary
from dataset.model_input import ModelPartitionInput, PreparedModelInput
from dataset.qt_model_input_adaptation import (
    QtModelInputAdaptationResult,
    adapt_qt_model_inputs,
)
from preprocessing.qt_model_ready_preparation import prepare_qt_model_ready_inputs

ROOT = Path(__file__).resolve().parents[2]


def _configuration():
    return json.loads(
        (ROOT / "configs/experiments/qt_unimodal_baselines_1.0.0.json").read_text()
    )


def _prepared():
    source = adapt_qt_model_inputs(_split())
    # The test fixture has only three TRAIN messages; allow all test tokens into
    # the frozen TRAIN-only policy by repeating a neutral token.
    text = source.text
    train = text.train
    messages = (("neutral alpha",), ("neutral beta",), ("neutral gamma",))
    changed = ModelPartitionInput(
        "train",
        train.identifiers,
        messages,
        train.y,
        train.feature_names,
        train.metadata,
    )
    text = PreparedModelInput(
        text.dataset_name,
        text.dataset_version,
        changed,
        text.validation,
        text.test,
        text.feature_names,
        text.target_name,
        text.metadata,
    )
    source = QtModelInputAdaptationResult(
        source.specification,
        source.policy,
        source.code,
        source.process,
        text,
        source.validation,
        source.source_split_identity_digest,
        QtModelInputAdaptationResult.calculate_identity(
            source.specification, source.policy, source.code, source.process, text
        ),
    )
    return prepare_qt_model_ready_inputs(source)


def test_real_artifact_preserves_frozen_model_ready_identity_and_dimensions():
    prepared = boundary.load_qt_model_ready(
        ROOT
        / "artifacts/qtbase/datasets"
        / "a1af25290bbd078628e362d4b704a047853d620c"
        / "qt-model-inputs.json"
    )
    assert dict(prepared.partition_counts) == {
        "train": 11718,
        "validation": 2511,
        "test": 2511,
    }
    assert (
        len(prepared.code_feature_names),
        len(prepared.process_feature_names),
        len(prepared.text_feature_names),
    ) == (13, 2, 3989)
    assert prepared.text_state.fit_partition == "train"


@pytest.mark.parametrize(
    "field,value",
    [
        ("fit_partition", "validation"),
        ("evaluation_partitions", ["train", "validation", "test"]),
        ("sealed_partition", "validation"),
    ],
)
def test_only_train_can_fit_validation_is_evaluation_only_and_test_is_sealed(
    field, value
):
    config = _configuration()
    config[field] = value
    with pytest.raises(boundary.QtBaselineBoundaryError):
        boundary.run_qt_baselines(_prepared(), config)


def test_six_runs_are_isolated_deterministic_and_have_no_forbidden_science():
    config = _configuration()
    config["models"]["RF"]["hyperparameters"]["n_estimators"] = 3
    first = boundary.run_qt_baselines(_prepared(), config)
    repeated = boundary.run_qt_baselines(_prepared(), config)
    assert first == repeated
    assert [(run["modality"], run["model"]) for run in first["runs"]] == [
        (modality, model) for modality in boundary.MODALITIES for model in ("LR", "RF")
    ]
    assert all(
        len(run["feature_names"])
        == {"CODE": 13, "PROCESS": 2, "TEXT": 1}[run["modality"]]
        for run in first["runs"]
    )
    assert first["test_sealing"] == {
        "structural_checks_only": True,
        "predict_called": False,
        "targets_used_for_metrics": False,
        "outcomes_persisted": False,
    }
    assert first["scientific_exclusions"] == {
        "fusion": False,
        "calibration": False,
        "xai": False,
        "human_18c_consumed": False,
        "test_predictive_evaluation": False,
    }
    assert all(
        set(run["probabilities"]) == {"train", "validation"} for run in first["runs"]
    )


def test_forbidden_predictor_fails_closed():
    prepared = _prepared()
    with pytest.raises(ValueError, match="schemas must remain frozen"):
        replace(
            prepared,
            code_feature_names=("bug_confidence",) + prepared.code_feature_names[1:],
        )


def test_configuration_prohibits_fusion_calibration_xai_and_refitting():
    prohibited = set(_configuration()["prohibited_operations"])
    assert {
        "multimodal-fusion",
        "calibration",
        "xai",
        "train-validation-refit",
        "test-predictive-evaluation",
    } <= prohibited
    assert (
        _configuration()["imbalance_policy"] == "no-resampling-and-no-class-weighting"
    )


def test_model_ready_text_state_cannot_be_changed_by_validation_or_test():
    prepared = _prepared()
    assert prepared.fit_audit["fit_partitions"] == ("train",)
    assert prepared.fit_audit["transform_only_partitions"] == ("validation", "test")
    assert (
        prepared.text_state.training_document_count == prepared.train.observation_count
    )


def test_human_18c_files_are_not_runtime_inputs():
    module_text = Path(boundary.__file__).read_text()
    assert "validation/18C" not in module_text
    assert "reviewer_A_form" not in module_text


def test_real_single_class_train_fails_before_any_classifier_fit(monkeypatch):
    prepared = boundary.load_qt_model_ready(
        ROOT
        / "artifacts/qtbase/datasets"
        / "a1af25290bbd078628e362d4b704a047853d620c"
        / "qt-model-inputs.json"
    )
    fit_called = False

    def forbidden_fit(*args, **kwargs):
        nonlocal fit_called
        fit_called = True

    monkeypatch.setattr(boundary.LogisticRegressionModel, "fit", forbidden_fit)
    with pytest.raises(
        boundary.QtBaselineBoundaryError, match="TRAIN must contain both"
    ):
        boundary.run_qt_baselines(prepared, _configuration())
    assert fit_called is False
