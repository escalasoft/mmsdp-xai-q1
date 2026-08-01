"""Tests for deterministic binary probability calibration."""

from dataclasses import FrozenInstanceError
from types import MappingProxyType

import pytest

import models.calibration as calibration_module
from models.calibration import (
    CalibratedPredictionResult,
    ModelProbabilityCalibrator,
    PreparedProbabilityCalibrator,
    ProbabilityCalibrationConfiguration,
)
from models.prediction import ModelPredictionResult


def prediction(
    partition: str = "validation",
    *,
    labels: tuple[object, object] = ("no", "yes"),
    probabilities: tuple[tuple[float, float], ...] = (
        (0.9, 0.1),
        (0.7, 0.3),
        (0.4, 0.6),
        (0.1, 0.9),
    ),
    dataset_name: str = "dataset",
    dataset_version: str = "1",
    model_name: str = "model",
) -> ModelPredictionResult:
    return ModelPredictionResult(
        dataset_name=dataset_name,
        dataset_version=dataset_version,
        partition_name=partition,
        model_name=model_name,
        identifiers=[f"id-{index}" for index in range(len(probabilities))],
        class_labels=labels,
        predictions=[
            labels[0] if row[0] >= row[1] else labels[1] for row in probabilities
        ],
        probabilities=probabilities,
        observation_count=len(probabilities),
        metadata={"nested": {"values": [1, 2]}},
    )


def fitted(
    method: str = "platt",
) -> tuple[ModelProbabilityCalibrator, PreparedProbabilityCalibrator]:
    service = ModelProbabilityCalibrator(
        ProbabilityCalibrationConfiguration(method, "yes")
    )
    return service, service.fit(prediction(), ["no", "no", "yes", "yes"])


@pytest.mark.parametrize("method", ["platt", "isotonic"])
def test_valid_configuration_and_deterministic_to_dict(method: str) -> None:
    configuration = ProbabilityCalibrationConfiguration(method, ["positive"])
    first = configuration.to_dict()
    second = configuration.to_dict()
    assert first == second == {"method": method, "positive_label": ["positive"]}
    first["positive_label"].append("changed")
    assert configuration.to_dict()["positive_label"] == ["positive"]


@pytest.mark.parametrize("method", [None, 1, ""])
def test_invalid_method_type_or_empty_is_rejected(method: object) -> None:
    with pytest.raises(ValueError, match="non-empty string"):
        ProbabilityCalibrationConfiguration(method, "yes")  # type: ignore[arg-type]


def test_unsupported_method_is_rejected() -> None:
    with pytest.raises(ValueError, match="platt or isotonic"):
        ProbabilityCalibrationConfiguration("beta", "yes")


def test_configuration_is_immutable_and_positive_label_is_detached() -> None:
    label = ["yes"]
    configuration = ProbabilityCalibrationConfiguration("platt", label)
    label.append("mutated")
    assert configuration.positive_label == ("yes",)
    with pytest.raises(FrozenInstanceError):
        configuration.method = "isotonic"  # type: ignore[misc]


@pytest.mark.parametrize("method", ["platt", "isotonic"])
def test_fit_is_deterministic_and_framework_neutral(method: str) -> None:
    service = ModelProbabilityCalibrator(
        ProbabilityCalibrationConfiguration(method, "yes")
    )
    source = prediction()
    targets = ["no", "no", "yes", "yes"]
    assert (
        service.fit(source, targets).to_dict() == service.fit(source, targets).to_dict()
    )
    snapshot = service.fit(source, targets)
    assert not any(
        hasattr(snapshot, name) for name in ("fit", "train", "predict", "predict_proba")
    )
    expected_keys = (
        {"coefficient", "intercept"}
        if method == "platt"
        else {"x_thresholds", "y_thresholds"}
    )
    assert set(snapshot.parameters) == expected_keys


def test_fit_uses_validation_only_and_rejects_test() -> None:
    service, _ = fitted()
    with pytest.raises(ValueError, match="validation"):
        service.fit(prediction("test"), ["no", "no", "yes", "yes"])


@pytest.mark.parametrize("targets", [None, [], ["no"], ["no"] * 5])
def test_target_presence_and_alignment_validation(targets: object) -> None:
    service, _ = fitted()
    with pytest.raises((TypeError, ValueError)):
        service.fit(prediction(), targets)  # type: ignore[arg-type]


def test_unknown_and_one_class_targets_are_rejected() -> None:
    service, _ = fitted()
    with pytest.raises(ValueError, match="belong"):
        service.fit(prediction(), ["no", "no", "yes", "unknown"])
    with pytest.raises(ValueError, match="both classes"):
        service.fit(prediction(), ["yes"] * 4)


def test_positive_label_lookup_respects_reversed_class_order() -> None:
    source = prediction(
        labels=("yes", "no"),
        probabilities=((0.1, 0.9), (0.3, 0.7), (0.6, 0.4), (0.9, 0.1)),
    )
    service = ModelProbabilityCalibrator(
        ProbabilityCalibrationConfiguration("isotonic", "yes")
    )
    snapshot = service.fit(source, ["no", "no", "yes", "yes"])
    result = service.calibrate(snapshot, source)
    assert result.class_labels == ("yes", "no")
    assert result.probabilities[0][0] == 0.0
    assert result.probabilities[-1][0] == 1.0


@pytest.mark.parametrize("partition", ["validation", "test"])
@pytest.mark.parametrize("method", ["platt", "isotonic"])
def test_calibrated_output_contract(partition: str, method: str) -> None:
    service, snapshot = fitted(method)
    source = prediction(partition)
    before = source.to_dict()
    result = service.calibrate(snapshot, source)
    assert result.partition_name == partition
    assert result.class_labels == source.class_labels
    assert result.identifiers == source.identifiers
    assert result.observation_count == source.observation_count
    assert all(0.0 <= value <= 1.0 for row in result.probabilities for value in row)
    assert all(
        sum(row) == pytest.approx(1.0, abs=1e-12) for row in result.probabilities
    )
    assert result.predictions == tuple(
        result.class_labels[0] if row[0] >= row[1] else result.class_labels[1]
        for row in result.probabilities
    )
    assert source.to_dict() == before


def test_ties_resolve_to_first_class() -> None:
    source = prediction(probabilities=((0.5, 0.5),))
    snapshot = PreparedProbabilityCalibrator(
        dataset_name="dataset",
        dataset_version="1",
        model_name="model",
        calibration_partition_name="validation",
        class_labels=("no", "yes"),
        positive_label="yes",
        method="platt",
        parameters={"coefficient": 0.0, "intercept": 0.0},
        calibration_observation_count=4,
    )
    service = ModelProbabilityCalibrator(
        ProbabilityCalibrationConfiguration("platt", "yes")
    )
    result = service.calibrate(snapshot, source)
    assert result.probabilities == ((0.5, 0.5),)
    assert result.predictions == ("no",)


def test_repeated_calibration_is_structurally_equal() -> None:
    service, snapshot = fitted("isotonic")
    assert (
        service.calibrate(snapshot, prediction("test")).to_dict()
        == service.calibrate(snapshot, prediction("test")).to_dict()
    )


def test_source_targets_are_not_mutated() -> None:
    targets = ["no", "no", "yes", "yes"]
    original = list(targets)
    service = ModelProbabilityCalibrator(
        ProbabilityCalibrationConfiguration("platt", "yes")
    )
    service.fit(prediction(), targets)
    assert targets == original


def test_snapshot_is_immutable_detached_and_to_dict_is_detached() -> None:
    parameters = {"coefficient": 1.0, "intercept": 0.0}
    metadata = {"nested": {"values": [1]}}
    snapshot = PreparedProbabilityCalibrator(
        "dataset",
        "1",
        "model",
        "validation",
        ["no", "yes"],
        "yes",
        "platt",
        parameters,
        4,
        metadata,
    )
    parameters["coefficient"] = 9.0
    metadata["nested"]["values"].append(2)
    assert snapshot.parameters["coefficient"] == 1.0
    assert snapshot.metadata["nested"]["values"] == (1,)
    with pytest.raises(TypeError):
        snapshot.parameters["coefficient"] = 2.0  # type: ignore[index]
    exported = snapshot.to_dict()
    exported["parameters"]["coefficient"] = 3.0
    assert snapshot.to_dict()["parameters"]["coefficient"] == 1.0


def test_result_is_immutable_detached_and_to_dict_is_detached() -> None:
    service, snapshot = fitted()
    result = service.calibrate(snapshot, prediction())
    with pytest.raises(FrozenInstanceError):
        result.model_name = "changed"  # type: ignore[misc]
    with pytest.raises(TypeError):
        result.metadata["new"] = True  # type: ignore[index]
    exported = result.to_dict()
    exported["identifiers"].append("new")
    exported["metadata"]["nested"]["values"].append(3)
    assert len(result.identifiers) == 4
    assert result.metadata["nested"]["values"] == (1, 2)
    assert not any(
        hasattr(result, name) for name in ("fit", "train", "predict", "predict_proba")
    )


@pytest.mark.parametrize(
    ("field", "replacement", "message"),
    [
        ("dataset_name", "other", "dataset_name"),
        ("dataset_version", "2", "dataset_version"),
        ("model_name", "other", "model_name"),
    ],
)
def test_mismatched_identity_is_rejected(
    field: str, replacement: str, message: str
) -> None:
    service, snapshot = fitted()
    kwargs = {field: replacement}
    with pytest.raises(ValueError, match=message):
        service.calibrate(snapshot, prediction("test", **kwargs))


def test_mismatched_class_labels_are_rejected() -> None:
    service, snapshot = fitted()
    source = prediction(
        "test",
        labels=("yes", "no"),
        probabilities=((0.1, 0.9), (0.3, 0.7), (0.6, 0.4), (0.9, 0.1)),
    )
    with pytest.raises(ValueError, match="class_labels"):
        service.calibrate(snapshot, source)


def test_invalid_calibrator_and_prediction_types_are_rejected() -> None:
    service, snapshot = fitted()
    with pytest.raises(TypeError, match="calibrator"):
        service.calibrate(object(), prediction())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="prediction_result"):
        service.calibrate(snapshot, object())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="prediction_result"):
        service.fit(object(), ["no", "yes"])  # type: ignore[arg-type]


def test_malformed_probability_rows_rejected_by_existing_contract() -> None:
    with pytest.raises(ValueError, match="probability row"):
        ModelPredictionResult(
            "dataset",
            "1",
            "validation",
            "model",
            ["id"],
            ["no", "yes"],
            ["no"],
            [(1.0,)],
            1,
        )


def test_direct_result_contract_rejects_prediction_not_matching_argmax() -> None:
    with pytest.raises(ValueError, match="argmax"):
        CalibratedPredictionResult(
            "dataset",
            "1",
            "test",
            "model",
            ["id"],
            ["no", "yes"],
            ["yes"],
            [(0.8, 0.2)],
            1,
            "platt",
            "validation",
            "yes",
        )


def test_public_all_is_exact() -> None:
    assert calibration_module.__all__ == [
        "ProbabilityCalibrationConfiguration",
        "PreparedProbabilityCalibrator",
        "CalibratedPredictionResult",
        "ModelProbabilityCalibrator",
    ]


def test_default_metadata_is_immutable_mapping() -> None:
    snapshot = PreparedProbabilityCalibrator(
        "dataset",
        "1",
        "model",
        "validation",
        ("no", "yes"),
        "yes",
        "platt",
        {"coefficient": 1.0, "intercept": 0.0},
        2,
    )
    assert isinstance(snapshot.metadata, MappingProxyType)
