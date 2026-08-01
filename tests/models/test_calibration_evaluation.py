"""Tests for reproducible binary probability-calibration evaluation."""

from dataclasses import FrozenInstanceError, replace
from types import MappingProxyType

import pytest

import models.calibration_evaluation as module
from models.calibration import CalibratedPredictionResult
from models.calibration_evaluation import (
    CalibrationBinResult,
    ProbabilityCalibrationComparison,
    ProbabilityCalibrationEvaluation,
    ProbabilityCalibrationEvaluator,
)
from models.prediction import ModelPredictionResult


def prediction(
    *,
    labels: tuple[object, ...] = ("no", "yes"),
    probabilities: tuple[tuple[float, ...], ...] = (
        (1.0, 0.0),
        (0.8, 0.2),
        (0.4, 0.6),
        (0.0, 1.0),
    ),
    partition: str = "test",
    dataset_name: str = "dataset",
    model_name: str = "model",
) -> ModelPredictionResult:
    return ModelPredictionResult(
        dataset_name=dataset_name,
        dataset_version="1",
        partition_name=partition,
        model_name=model_name,
        identifiers=[f"id-{index}" for index in range(len(probabilities))],
        class_labels=labels,
        predictions=[
            labels[max(range(len(row)), key=row.__getitem__)] for row in probabilities
        ],
        probabilities=probabilities,
        observation_count=len(probabilities),
        metadata={"nested": {"values": [1]}, "tags": {"stable"}},
    )


def calibrated(
    *,
    probabilities: tuple[tuple[float, float], ...] = (
        (0.9, 0.1),
        (0.9, 0.1),
        (0.1, 0.9),
        (0.1, 0.9),
    ),
    method: str = "platt",
    partition: str = "test",
) -> CalibratedPredictionResult:
    labels = ("no", "yes")
    return CalibratedPredictionResult(
        dataset_name="dataset",
        dataset_version="1",
        partition_name=partition,
        model_name="model",
        identifiers=[f"id-{index}" for index in range(len(probabilities))],
        class_labels=labels,
        predictions=[
            labels[0] if row[0] >= row[1] else labels[1] for row in probabilities
        ],
        probabilities=probabilities,
        observation_count=len(probabilities),
        calibration_method=method,
        calibration_partition_name="validation",
        positive_label="yes",
        metadata={"nested": {"values": [1]}},
    )


def evaluations() -> tuple[
    ProbabilityCalibrationEvaluation, ProbabilityCalibrationEvaluation
]:
    evaluator = ProbabilityCalibrationEvaluator(positive_label="yes", bin_count=2)
    targets = ["no", "no", "yes", "yes"]
    return (
        evaluator.evaluate_uncalibrated(prediction(), targets),
        evaluator.evaluate_calibrated(calibrated(), targets),
    )


def test_public_api_is_exact() -> None:
    assert module.__all__ == [
        "CalibrationBinResult",
        "ProbabilityCalibrationEvaluation",
        "ProbabilityCalibrationComparison",
        "ProbabilityCalibrationEvaluator",
    ]


def test_known_example_has_exact_bins_brier_ece_and_mce() -> None:
    result = ProbabilityCalibrationEvaluator(
        positive_label="yes", bin_count=2
    ).evaluate_uncalibrated(prediction(), ["no", "no", "yes", "yes"])
    assert result.calibration_method == "uncalibrated"
    assert [item.observation_count for item in result.bins] == [2, 2]
    assert result.bins[0].mean_predicted_probability == pytest.approx(0.1)
    assert result.bins[0].observed_positive_rate == 0.0
    assert result.bins[1].mean_predicted_probability == pytest.approx(0.8)
    assert result.bins[1].observed_positive_rate == 1.0
    assert result.brier_score == pytest.approx(0.05)
    assert result.expected_calibration_error == pytest.approx(0.15)
    assert result.maximum_calibration_error == pytest.approx(0.2)


def test_reversed_class_order_selects_positive_label_column() -> None:
    source = prediction(
        labels=("yes", "no"),
        probabilities=((0.0, 1.0), (0.2, 0.8), (0.6, 0.4), (1.0, 0.0)),
    )
    result = ProbabilityCalibrationEvaluator(
        positive_label="yes", bin_count=2
    ).evaluate_uncalibrated(source, ["no", "no", "yes", "yes"])
    assert result.brier_score == pytest.approx(0.05)
    assert [item.observation_count for item in result.bins] == [2, 2]


def test_equal_width_boundaries_endpoints_and_empty_bins() -> None:
    result = ProbabilityCalibrationEvaluator(
        positive_label="yes", bin_count=4
    ).evaluate_uncalibrated(
        prediction(probabilities=((1.0, 0.0), (0.0, 1.0))), ["no", "yes"]
    )
    assert [(item.lower_bound, item.upper_bound) for item in result.bins] == [
        (0.0, 0.25),
        (0.25, 0.5),
        (0.5, 0.75),
        (0.75, 1.0),
    ]
    assert [item.observation_count for item in result.bins] == [1, 0, 0, 1]
    for item in result.bins[1:3]:
        assert (
            item.mean_predicted_probability,
            item.observed_positive_rate,
            item.absolute_calibration_error,
        ) == (0.0, 0.0, 0.0)


def test_internal_boundary_belongs_to_upper_bin() -> None:
    result = ProbabilityCalibrationEvaluator(
        positive_label="yes", bin_count=2
    ).evaluate_uncalibrated(prediction(probabilities=((0.5, 0.5),)), ["yes"])
    assert [item.observation_count for item in result.bins] == [0, 1]


def test_repeated_evaluation_is_structurally_equal_and_does_not_mutate_inputs() -> None:
    source = prediction()
    targets = ["no", "no", "yes", "yes"]
    source_before = source.to_dict()
    targets_before = list(targets)
    evaluator = ProbabilityCalibrationEvaluator(positive_label="yes", bin_count=3)
    first = evaluator.evaluate_uncalibrated(source, targets)
    second = evaluator.evaluate_uncalibrated(source, targets)
    assert first == second
    assert first.to_dict() == second.to_dict()
    assert source.to_dict() == source_before
    assert targets == targets_before


def test_positive_label_property_is_detached() -> None:
    label = ["yes"]
    evaluator = ProbabilityCalibrationEvaluator(positive_label=label, bin_count=2)
    label.append("changed")
    returned = evaluator.positive_label
    returned.append("changed again")
    assert evaluator.positive_label == ["yes"]


def test_results_nested_metadata_and_to_dict_are_immutable_and_detached() -> None:
    before, after = evaluations()
    comparison = ProbabilityCalibrationEvaluator(
        positive_label="yes", bin_count=2
    ).compare(before, after)
    with pytest.raises(FrozenInstanceError):
        before.brier_score = 0.0  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        before.bins[0].observation_count = 99  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        comparison.brier_score_change = 0.0  # type: ignore[misc]
    with pytest.raises(TypeError):
        before.metadata["new"] = 1  # type: ignore[index]
    with pytest.raises(TypeError):
        before.metadata["nested"]["new"] = 1  # type: ignore[index]
    first = comparison.to_dict()
    second = comparison.to_dict()
    assert first == second
    first["before"]["metadata"]["nested"]["values"].append(9)  # type: ignore[index,union-attr]
    assert comparison.to_dict() == second


@pytest.mark.parametrize("method", ["platt", "isotonic"])
def test_calibrated_evaluation_preserves_method(method: str) -> None:
    result = ProbabilityCalibrationEvaluator(
        positive_label="yes", bin_count=2
    ).evaluate_calibrated(calibrated(method=method), ["no", "no", "yes", "yes"])
    assert result.calibration_method == method


def test_comparison_uses_after_minus_before_and_negative_means_improved() -> None:
    before, after = evaluations()
    result = ProbabilityCalibrationEvaluator(positive_label="yes", bin_count=2).compare(
        before, after
    )
    assert result.brier_score_change == pytest.approx(
        after.brier_score - before.brier_score
    )
    assert result.expected_calibration_error_change == pytest.approx(
        after.expected_calibration_error - before.expected_calibration_error
    )
    assert result.maximum_calibration_error_change == pytest.approx(
        after.maximum_calibration_error - before.maximum_calibration_error
    )
    assert result.brier_score_improved
    assert result.expected_calibration_error_improved
    assert result.maximum_calibration_error_improved


def test_equal_metric_is_not_improvement_and_positive_change_is_not_improvement() -> (
    None
):
    evaluator = ProbabilityCalibrationEvaluator(positive_label="yes", bin_count=2)
    before = evaluator.evaluate_uncalibrated(
        prediction(probabilities=((0.8, 0.2), (0.2, 0.8))), ["no", "yes"]
    )
    equal_after = evaluator.evaluate_calibrated(
        calibrated(probabilities=((0.8, 0.2), (0.2, 0.8))), ["no", "yes"]
    )
    equal = evaluator.compare(before, equal_after)
    assert not any(
        (
            equal.brier_score_improved,
            equal.expected_calibration_error_improved,
            equal.maximum_calibration_error_improved,
        )
    )
    worse_after = evaluator.evaluate_calibrated(
        calibrated(probabilities=((0.1, 0.9), (0.9, 0.1))), ["no", "yes"]
    )
    worse = evaluator.compare(before, worse_after)
    assert worse.brier_score_change > 0.0
    assert not worse.brier_score_improved


@pytest.mark.parametrize(
    ("field", "changed"),
    [
        ("dataset_name", "other"),
        ("model_name", "other"),
        ("partition_name", "validation"),
        ("positive_label", "no"),
        ("class_labels", ("yes", "no")),
        ("observation_count", 5),
    ],
)
def test_comparison_rejects_mismatched_identity(field: str, changed: object) -> None:
    before, after = evaluations()
    object.__setattr__(after, field, changed)
    with pytest.raises(ValueError, match=field):
        ProbabilityCalibrationEvaluator(positive_label="yes", bin_count=2).compare(
            before, after
        )


@pytest.mark.parametrize("value", [True, False, 1, 1.5, "2", None])
def test_invalid_constructor_bin_count_is_rejected(value: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        ProbabilityCalibrationEvaluator(
            positive_label="yes",
            bin_count=value,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    "targets", [None, [], "yes", b"yes", ["yes"], ["no"] * 5, ["no"] * 3 + ["?"]]
)
def test_empty_misaligned_string_and_unknown_targets_are_rejected(
    targets: object,
) -> None:
    with pytest.raises((TypeError, ValueError)):
        ProbabilityCalibrationEvaluator(
            positive_label="yes", bin_count=2
        ).evaluate_uncalibrated(prediction(), targets)  # type: ignore[arg-type]


def test_malformed_binary_labels_and_unknown_positive_label_are_rejected() -> None:
    evaluator = ProbabilityCalibrationEvaluator(positive_label="yes", bin_count=2)
    malformed = prediction(
        labels=("no", "maybe", "yes"),
        probabilities=((0.2, 0.3, 0.5),),
    )
    with pytest.raises(ValueError, match="exactly two"):
        evaluator.evaluate_uncalibrated(malformed, ["yes"])
    with pytest.raises(ValueError, match="positive_label"):
        ProbabilityCalibrationEvaluator(
            positive_label="other", bin_count=2
        ).evaluate_uncalibrated(prediction(), ["no", "no", "yes", "yes"])


@pytest.mark.parametrize(
    "kwargs",
    [
        {"observation_count": True},
        {"lower_bound": False},
        {"lower_bound": 0.5, "upper_bound": 0.5},
        {"mean_predicted_probability": float("nan")},
        {"absolute_calibration_error": 0.3},
    ],
)
def test_invalid_bin_values_are_rejected(kwargs: dict[str, object]) -> None:
    values: dict[str, object] = {
        "lower_bound": 0.0,
        "upper_bound": 0.5,
        "observation_count": 1,
        "mean_predicted_probability": 0.2,
        "observed_positive_rate": 0.0,
        "absolute_calibration_error": 0.2,
    }
    values.update(kwargs)
    with pytest.raises((TypeError, ValueError)):
        CalibrationBinResult(**values)  # type: ignore[arg-type]


def test_empty_bin_requires_zero_statistics() -> None:
    with pytest.raises(ValueError, match="zero"):
        CalibrationBinResult(0.0, 0.5, 0, 0.1, 0.0, 0.1)


def test_comparison_constructor_rejects_inconsistent_changes_and_flags() -> None:
    before, after = evaluations()
    valid = ProbabilityCalibrationEvaluator(positive_label="yes", bin_count=2).compare(
        before, after
    )
    values = valid.to_dict()
    with pytest.raises(ValueError, match="brier_score_change"):
        ProbabilityCalibrationComparison(
            before,
            after,
            0.0,
            valid.expected_calibration_error_change,
            valid.maximum_calibration_error_change,
            valid.brier_score_improved,
            valid.expected_calibration_error_improved,
            valid.maximum_calibration_error_improved,
        )
    assert values["metadata"] == {}


def test_evaluator_exposes_no_training_prediction_calibration_or_plotting() -> None:
    evaluator = ProbabilityCalibrationEvaluator(positive_label="yes")
    assert not any(
        hasattr(evaluator, name)
        for name in ("fit", "train", "predict", "calibrate", "plot", "plotting")
    )


def test_evaluation_rejects_inconsistent_derived_values() -> None:
    before, _ = evaluations()
    with pytest.raises(ValueError, match="positive_rate"):
        replace(before, positive_rate=0.9)
    with pytest.raises(ValueError, match="expected_calibration_error"):
        replace(before, expected_calibration_error=0.9)


def test_default_metadata_is_immutable() -> None:
    item = CalibrationBinResult(0.0, 0.5, 1, 0.0, 0.0, 0.0)
    other = CalibrationBinResult(0.5, 1.0, 0, 0.0, 0.0, 0.0)
    result = ProbabilityCalibrationEvaluation(
        "d",
        "v",
        "test",
        "m",
        "uncalibrated",
        "yes",
        ("no", "yes"),
        1,
        0,
        0.0,
        2,
        (item, other),
        0.0,
        0.0,
        0.0,
    )
    assert isinstance(result.metadata, MappingProxyType)
