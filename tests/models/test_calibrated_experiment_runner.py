"""Tests for complete deterministic calibrated model experiments."""

from dataclasses import FrozenInstanceError, replace
from types import MappingProxyType

import pytest

import models.calibrated_experiment_runner as module
from dataset.model_input import ModelPartitionInput, PreparedModelInput
from models.calibrated_experiment_runner import (
    CalibratedModelExperimentResult,
    CalibratedModelExperimentRunner,
)
from models.calibration import (
    ModelProbabilityCalibrator,
    ProbabilityCalibrationConfiguration,
)
from models.logistic_regression_adapter import (
    LogisticRegressionAdapter,
    LogisticRegressionConfiguration,
)
from models.random_forest_adapter import RandomForestAdapter, RandomForestConfiguration


def _partition(name: str, start: int, X, y) -> ModelPartitionInput:
    return ModelPartitionInput(
        name,
        tuple(range(start, start + len(y))),
        X,
        y,
        ("first", "second"),
        {"nested": {"tags": [name]}},
    )


@pytest.fixture
def prepared_input() -> PreparedModelInput:
    return PreparedModelInput(
        "example",
        "1.0",
        _partition(
            "train",
            0,
            ((-3, 1), (-2, 1), (-1, 0), (1, 0), (2, -1), (3, -1)),
            ("negative", "negative", "negative", "positive", "positive", "positive"),
        ),
        _partition(
            "validation",
            10,
            ((2.5, -1), (-2.5, 1), (0.2, 0), (-0.3, 0)),
            ("positive", "negative", "positive", "negative"),
        ),
        _partition(
            "test",
            20,
            ((-0.2, 0), (1.5, -1), (-1.5, 1), (2.2, -1)),
            ("negative", "positive", "negative", "positive"),
        ),
        ("first", "second"),
        "label",
        {"source": {"tags": ["stable"], "groups": {"a", "b"}}},
    )


def _logistic() -> LogisticRegressionAdapter:
    return LogisticRegressionAdapter(LogisticRegressionConfiguration(random_state=17))


def _run(prepared_input, method="platt", adapter=None):
    return CalibratedModelExperimentRunner(
        model_adapter=adapter or _logistic(),
        calibration_configuration=ProbabilityCalibrationConfiguration(
            method, "positive"
        ),
        positive_label="positive",
        bin_count=3,
    ).run(prepared_input)


@pytest.mark.parametrize("method", ["platt", "isotonic"])
def test_logistic_end_to_end_is_complete(prepared_input, method) -> None:
    result = _run(prepared_input, method)
    assert result.calibration_method == method
    assert result.prepared_calibrator.method == method
    assert result.calibrated_validation_prediction.partition_name == "validation"
    assert result.calibrated_test_prediction.partition_name == "test"
    assert result.calibrated_validation_calibration.calibration_method == method
    assert result.calibrated_test_calibration.calibration_method == method
    assert (
        result.validation_calibration_comparison.before
        is result.uncalibrated_validation_calibration
    )
    assert (
        result.test_calibration_comparison.after is result.calibrated_test_calibration
    )


def test_random_forest_end_to_end(prepared_input) -> None:
    adapter = RandomForestAdapter(
        RandomForestConfiguration(n_estimators=9, random_state=17)
    )
    result = _run(prepared_input, adapter=adapter)
    assert result.model_name == "random-forest"
    assert result.uncalibrated_experiment.model_name == "random-forest"


def test_identity_order_labels_and_counts_are_preserved(prepared_input) -> None:
    result = _run(prepared_input)
    assert (result.dataset_name, result.dataset_version) == ("example", "1.0")
    for original, calibrated, evaluation in (
        (
            result.uncalibrated_experiment.validation_prediction,
            result.calibrated_validation_prediction,
            result.calibrated_validation_calibration,
        ),
        (
            result.uncalibrated_experiment.test_prediction,
            result.calibrated_test_prediction,
            result.calibrated_test_calibration,
        ),
    ):
        assert calibrated.identifiers == original.identifiers
        assert (
            calibrated.class_labels == original.class_labels == evaluation.class_labels
        )
        assert calibrated.observation_count == original.observation_count
        assert calibrated.model_name == original.model_name


def test_train_fit_and_calibration_data_flow(monkeypatch, prepared_input) -> None:
    train_calls = []
    fit_calls = []
    calibrate_calls = []
    original_train = LogisticRegressionAdapter.train
    original_fit = ModelProbabilityCalibrator.fit
    original_calibrate = ModelProbabilityCalibrator.calibrate

    def train_spy(self, value):
        train_calls.append(value)
        return original_train(self, value)

    def fit_spy(self, prediction, targets):
        fit_calls.append((prediction, tuple(targets)))
        return original_fit(self, prediction, targets)

    def calibrate_spy(self, calibrator, prediction):
        calibrate_calls.append((calibrator, prediction.partition_name))
        return original_calibrate(self, calibrator, prediction)

    monkeypatch.setattr(LogisticRegressionAdapter, "train", train_spy)
    monkeypatch.setattr(ModelProbabilityCalibrator, "fit", fit_spy)
    monkeypatch.setattr(ModelProbabilityCalibrator, "calibrate", calibrate_spy)
    result = _run(prepared_input)

    assert train_calls == [prepared_input]
    assert fit_calls == [
        (
            result.uncalibrated_experiment.validation_prediction,
            prepared_input.validation.y,
        )
    ]
    assert prepared_input.test.y != fit_calls[0][1]
    assert [partition for _, partition in calibrate_calls] == ["validation", "test"]
    assert calibrate_calls[0][0] is calibrate_calls[1][0] is result.prepared_calibrator


def test_repeated_runs_are_equal_and_input_is_unmodified(prepared_input) -> None:
    before = prepared_input.to_dict()
    first = _run(prepared_input)
    second = _run(prepared_input)
    assert first == second
    assert prepared_input.to_dict() == before


def test_result_metadata_and_to_dict_are_immutable_detached(prepared_input) -> None:
    result = _run(prepared_input)
    assert isinstance(result.metadata, MappingProxyType)
    with pytest.raises(FrozenInstanceError):
        result.model_name = "changed"  # type: ignore[misc]
    with pytest.raises(TypeError):
        result.metadata["source"]["tags"] += ("changed",)  # type: ignore[index,operator]
    first, second = result.to_dict(), result.to_dict()
    assert first == second and first is not second
    first["metadata"]["source"]["tags"].append("changed")
    first["calibrated_test_prediction"]["identifiers"].append("changed")
    assert result.to_dict() == second


@pytest.mark.parametrize("adapter", [None, object(), "logistic"])
def test_invalid_adapter_is_rejected(adapter) -> None:
    with pytest.raises(TypeError, match="unsupported model adapter"):
        CalibratedModelExperimentRunner(
            model_adapter=adapter,
            calibration_configuration=ProbabilityCalibrationConfiguration(
                "platt", "positive"
            ),
            positive_label="positive",
        )


def test_invalid_configuration_is_rejected() -> None:
    with pytest.raises(TypeError, match="calibration_configuration"):
        CalibratedModelExperimentRunner(
            model_adapter=_logistic(),
            calibration_configuration=object(),  # type: ignore[arg-type]
            positive_label="positive",
        )


@pytest.mark.parametrize("value", [True, False, None, 2.5, "2", 0, 1, -1])
def test_invalid_bin_count_is_rejected(value) -> None:
    with pytest.raises((TypeError, ValueError), match="bin_count"):
        CalibratedModelExperimentRunner(
            model_adapter=_logistic(),
            calibration_configuration=ProbabilityCalibrationConfiguration(
                "platt", "positive"
            ),
            positive_label="positive",
            bin_count=value,
        )


@pytest.mark.parametrize("value", [None, object(), "prepared"])
def test_invalid_prepared_input_is_rejected(value) -> None:
    runner = CalibratedModelExperimentRunner(
        model_adapter=_logistic(),
        calibration_configuration=ProbabilityCalibrationConfiguration(
            "platt", "positive"
        ),
        positive_label="positive",
    )
    with pytest.raises(TypeError, match="PreparedModelInput"):
        runner.run(value)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("dataset_name", "other", "dataset_name"),
        ("dataset_version", "other", "dataset_version"),
        ("model_name", "other", "model_name"),
        ("calibration_method", "isotonic", "calibration_method"),
    ],
)
def test_result_rejects_top_level_mismatches(
    prepared_input, field, value, message
) -> None:
    result = _run(prepared_input)
    values = {name: getattr(result, name) for name in result.__dataclass_fields__}
    values[field] = value
    with pytest.raises(ValueError, match=message):
        CalibratedModelExperimentResult(**values)


def test_result_rejects_partition_labels_counts_and_comparisons(prepared_input) -> None:
    result = _run(prepared_input)
    base = {name: getattr(result, name) for name in result.__dataclass_fields__}
    bad_partition = replace(
        result.calibrated_test_prediction, partition_name="validation"
    )
    with pytest.raises(ValueError, match="test partition"):
        CalibratedModelExperimentResult(
            **{**base, "calibrated_test_prediction": bad_partition}
        )
    bad_labels = replace(
        result.prepared_calibrator, class_labels=("positive", "negative")
    )
    with pytest.raises(ValueError, match="class_labels"):
        CalibratedModelExperimentResult(**{**base, "prepared_calibrator": bad_labels})
    bad_count = replace(
        result.calibrated_test_prediction,
        identifiers=result.calibrated_test_prediction.identifiers[:3],
        predictions=result.calibrated_test_prediction.predictions[:3],
        probabilities=result.calibrated_test_prediction.probabilities[:3],
        observation_count=3,
    )
    with pytest.raises(ValueError, match="observation counts"):
        CalibratedModelExperimentResult(
            **{**base, "calibrated_test_prediction": bad_count}
        )
    detached_before = replace(
        result.uncalibrated_test_calibration,
        metadata={"detached": True},
    )
    bad_comparison = replace(
        result.test_calibration_comparison,
        before=detached_before,
    )
    with pytest.raises(ValueError, match=r"comparison\.before"):
        CalibratedModelExperimentResult(
            **{
                **base,
                "test_calibration_comparison": bad_comparison,
            }
        )


def test_public_surface_is_exact_and_behavior_free(prepared_input) -> None:
    assert module.__all__ == [
        "CalibratedModelExperimentResult",
        "CalibratedModelExperimentRunner",
    ]
    runner = CalibratedModelExperimentRunner(
        model_adapter=_logistic(),
        calibration_configuration=ProbabilityCalibrationConfiguration(
            "platt", "positive"
        ),
        positive_label="positive",
    )
    assert runner.runner_name == "calibrated-model-experiment-runner"
    assert runner.bin_count == 10
    assert runner.model_adapter is not None
    assert runner.calibration_configuration.method == "platt"
    for name in ("save", "load", "persist", "plot"):
        assert not hasattr(runner, name)
    result = runner.run(prepared_input)
    for name in ("train", "fit", "predict", "calibrate", "evaluate", "plot", "save"):
        assert not hasattr(result, name)
