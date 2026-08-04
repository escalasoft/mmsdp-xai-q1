"""Tests for the deterministic end-to-end experiment pipeline."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from types import MappingProxyType

import pytest

import experimentation.end_to_end_pipeline as pipeline_module
from dataset.contracts import AdaptedDataset, DatasetRecord
from dataset.temporal_splitter import TemporalSplitConfiguration
from experimentation.end_to_end_pipeline import (
    EndToEndExperimentConfiguration,
    EndToEndExperimentPipeline,
    EndToEndExperimentResult,
)
from explainability.explanation_runner import ObservationExplanationRequest
from explainability.strategy_registry import ExplanationOutcome
from models.calibration import ProbabilityCalibrationConfiguration
from models.logistic_regression_adapter import (
    LogisticRegressionAdapter,
    LogisticRegressionConfiguration,
)
from models.model_registry import ModelAdapterRegistry, default_model_adapter_registry
from models.random_forest_adapter import RandomForestAdapter, RandomForestConfiguration


def _dataset() -> AdaptedDataset:
    records = tuple(
        DatasetRecord(
            identifier={"commit": [f"c{index:02d}"]},
            features={"age": float(index - 15), "churn": float((index % 5) - 2)},
            target="defect" if index % 2 else "clean",
            timestamp=30 - index,
            metadata={"source_order": index},
        )
        for index in range(30)
    )
    return AdaptedDataset(
        "commits",
        "v10.5",
        records,
        ("age", "churn"),
        "defect_status",
        {"source": {"tags": ["stable"]}},
    )


def _request(partition: str, chronological_index: int):
    source_index = 29 - chronological_index
    return ObservationExplanationRequest(
        partition, {"commit": [f"c{source_index:02d}"]}
    )


def _configuration(model="logistic", local=(), counterfactual=()):
    model_configuration = (
        LogisticRegressionConfiguration(random_state=23, max_iter=300)
        if model == "logistic"
        else RandomForestConfiguration(n_estimators=11, random_state=23)
    )
    return EndToEndExperimentConfiguration(
        TemporalSplitConfiguration(0.6, 0.2, 0.2),
        model_configuration,
        ProbabilityCalibrationConfiguration("platt", "defect"),
        "defect",
        local,
        counterfactual,
    )


def _run(model="logistic", local=(), counterfactual=()):
    return EndToEndExperimentPipeline(_configuration(model, local, counterfactual)).run(
        _dataset()
    )


@pytest.fixture
def requests():
    return (
        _request("test", 25),
        _request("validation", 19),
    )


def test_complete_logistic_pipeline_and_cross_component_consistency(requests):
    result = _run("logistic", requests, requests)
    assert isinstance(result, EndToEndExperimentResult)
    assert (result.dataset_name, result.dataset_version) == ("commits", "v10.5")
    assert result.model_name == "logistic-regression"
    assert result.temporal_split.feature_names == ("age", "churn")
    assert result.prepared_model_input.target_name == "defect_status"
    assert result.model_experiment_result == (
        result.calibrated_experiment_result.uncalibrated_experiment
    )
    assert result.global_explanation.model_name == result.model_name
    assert len(result.local_explanations) == len(requests)
    assert len(result.counterfactual_explanations) == len(requests)
    assert result.unsupported_local_requests == ()
    assert result.unsupported_counterfactual_requests == ()


def test_complete_random_forest_and_unsupported_requests_are_ordered(requests):
    result = _run("forest", requests, requests)
    assert result.model_name == "random-forest"
    assert result.global_explanation.model_name == "random-forest"
    assert result.local_explanations == ()
    assert result.counterfactual_explanations == ()
    assert result.unsupported_local_requests == requests
    assert result.unsupported_counterfactual_requests == requests


def test_exact_chronological_partition_and_model_input_preservation():
    result = _run()
    expected = tuple({"commit": [f"c{index:02d}"]} for index in range(29, -1, -1))
    split = result.temporal_split
    assert tuple(item.identifier for item in split.train) == expected[:18]
    assert tuple(item.identifier for item in split.validation) == expected[18:24]
    assert tuple(item.identifier for item in split.test) == expected[24:]
    assert (len(split.train), len(split.validation), len(split.test)) == (18, 6, 6)
    prepared = result.prepared_experiment_dataset
    model_input = result.prepared_model_input
    for name in ("train", "validation", "test"):
        prepared_partition = getattr(prepared, name)
        input_partition = getattr(model_input, name)
        assert input_partition.partition_name == name
        assert input_partition.identifiers == prepared_partition.identifiers
        assert input_partition.X == prepared_partition.features
        assert input_partition.y == prepared_partition.targets
        assert input_partition.feature_names == ("age", "churn")


def test_prediction_calibration_labels_identifiers_and_counts_align():
    result = _run()
    experiment = result.model_experiment_result
    calibrated = result.calibrated_experiment_result
    for name in ("validation", "test"):
        prediction = getattr(experiment, f"{name}_prediction")
        calibrated_prediction = getattr(calibrated, f"calibrated_{name}_prediction")
        source = getattr(result.prepared_model_input, name)
        assert prediction.partition_name == calibrated_prediction.partition_name == name
        assert (
            prediction.identifiers
            == calibrated_prediction.identifiers
            == source.identifiers
        )
        assert prediction.class_labels == calibrated_prediction.class_labels
        assert prediction.observation_count == source.observation_count
        assert calibrated_prediction.calibration_method == "platt"
        assert prediction.probabilities != ()


def test_logistic_explanations_preserve_request_alignment_and_semantics(requests):
    result = _run("logistic", requests, requests)
    assert tuple(
        item.observation_identifier for item in result.local_explanations
    ) == tuple(request.observation_identifier for request in requests)
    assert tuple(
        item.observation_identifier for item in result.counterfactual_explanations
    ) == tuple(request.observation_identifier for request in requests)
    assert all(
        item.attribution_method == "linear-logit-contribution"
        for item in result.local_explanations
    )
    assert all(
        item.generation_method == "minimal-single-feature-linear-boundary"
        for item in result.counterfactual_explanations
    )
    assert (
        result.metadata["scientific_boundaries"][
            "counterfactual_is_model_boundary_not_actionability"
        ]
        is True
    )


@pytest.mark.parametrize("model", ["logistic", "forest"])
def test_repeated_runs_are_structurally_equal(model, requests):
    configuration = _configuration(model, requests, requests)
    pipeline = EndToEndExperimentPipeline(configuration)
    assert pipeline.run(_dataset()) == pipeline.run(_dataset())
    assert pipeline.run(_dataset()).to_dict() == pipeline.run(_dataset()).to_dict()


def test_source_dataset_configuration_and_request_sequences_are_not_mutated(requests):
    dataset = _dataset()
    dataset_before = dataset.to_dict()
    request_list = list(requests)
    request_before = [item.to_dict() for item in request_list]
    configuration = _configuration("logistic", request_list, request_list)
    configuration_before = configuration.to_dict()
    EndToEndExperimentPipeline(configuration).run(dataset)
    assert dataset.to_dict() == dataset_before
    assert [item.to_dict() for item in request_list] == request_before
    assert configuration.to_dict() == configuration_before


def test_configuration_and_result_nested_metadata_are_immutable():
    configuration = _configuration()
    with pytest.raises(FrozenInstanceError):
        configuration.positive_label = "clean"  # type: ignore[misc]
    result = EndToEndExperimentPipeline(configuration).run(_dataset())
    with pytest.raises(FrozenInstanceError):
        result.model_name = "changed"  # type: ignore[misc]
    assert isinstance(result.metadata, MappingProxyType)
    with pytest.raises(TypeError):
        result.metadata["source"]["tags"] += ("changed",)  # type: ignore[index,operator]
    with pytest.raises(TypeError):
        result.prepared_model_input.metadata["source"]["new"] = True  # type: ignore[index]


def test_to_dict_is_deterministic_detached_and_mutable(requests):
    result = _run("logistic", requests, requests)
    first = result.to_dict()
    second = result.to_dict()
    assert first == second and first is not second
    first["metadata"]["source"]["tags"].append("changed")
    first["prepared_model_input"]["test"]["identifiers"].append("changed")
    assert result.to_dict() == second


@pytest.mark.parametrize("dataset", [None, object(), "dataset", {}])
def test_invalid_dataset_type_is_rejected(dataset):
    with pytest.raises(TypeError, match="AdaptedDataset"):
        EndToEndExperimentPipeline(_configuration()).run(dataset)


@pytest.mark.parametrize(
    ("position", "value", "message"),
    [
        (0, object(), "temporal_split_configuration"),
        (1, object(), "model_configuration"),
        (2, object(), "calibration_configuration"),
    ],
)
def test_invalid_configuration_component_types_are_rejected(position, value, message):
    values = [
        TemporalSplitConfiguration(0.6, 0.2, 0.2),
        LogisticRegressionConfiguration(),
        ProbabilityCalibrationConfiguration("platt", "defect"),
        "defect",
    ]
    values[position] = value
    with pytest.raises(TypeError, match=message):
        EndToEndExperimentConfiguration(*values)


def test_invalid_pipeline_configuration_and_positive_label_mismatch_are_rejected():
    with pytest.raises(TypeError, match="EndToEndExperimentConfiguration"):
        EndToEndExperimentPipeline(object())
    with pytest.raises(ValueError, match="positive_label"):
        EndToEndExperimentConfiguration(
            TemporalSplitConfiguration(0.6, 0.2, 0.2),
            LogisticRegressionConfiguration(),
            ProbabilityCalibrationConfiguration("platt", "defect"),
            "clean",
        )


def test_train_unknown_partition_and_missing_identifier_requests_are_rejected():
    with pytest.raises(ValueError, match="validation or test"):
        _configuration(local=(ObservationExplanationRequest("train", "id"),))
    with pytest.raises(ValueError, match="partition_name"):
        ObservationExplanationRequest("unknown", "id")
    with pytest.raises(ValueError, match="observation_identifier"):
        ObservationExplanationRequest("test", None)


@pytest.mark.parametrize("kind", ["local", "counterfactual"])
def test_duplicate_structural_requests_are_rejected(kind):
    requests = (
        ObservationExplanationRequest("test", {"id": [1]}),
        ObservationExplanationRequest("test", {"id": (1,)}),
    )
    kwargs = {"local": requests} if kind == "local" else {"counterfactual": requests}
    with pytest.raises(ValueError, match="duplicate structural"):
        _configuration(**kwargs)


def test_same_identifier_across_partitions_is_allowed_by_configuration():
    requests = (
        ObservationExplanationRequest("validation", {"id": [1]}),
        ObservationExplanationRequest("test", {"id": (1,)}),
    )
    assert _configuration(local=requests).local_explanation_requests == requests


@pytest.mark.parametrize("kind", ["local", "counterfactual"])
def test_unknown_identifier_and_wrong_partition_are_rejected(kind):
    requests = (ObservationExplanationRequest("test", {"commit": ["missing"]}),)
    kwargs = {"local": requests} if kind == "local" else {"counterfactual": requests}
    with pytest.raises(ValueError, match="exactly one feature row"):
        _run(**kwargs)


def test_public_api_is_narrow_and_behavioral_surface_is_orchestration_only():
    assert pipeline_module.__all__ == [
        "EndToEndExperimentConfiguration",
        "EndToEndExperimentResult",
        "EndToEndExperimentPipeline",
    ]
    assert EndToEndExperimentPipeline.pipeline_name == "end-to-end-experiment"
    forbidden = {"fit", "predict", "save", "write", "plot"}
    assert forbidden.isdisjoint(dir(EndToEndExperimentPipeline))


def test_metadata_collision_is_preserved():
    dataset = _dataset()
    colliding = AdaptedDataset(
        dataset.dataset_name,
        dataset.dataset_version,
        dataset.records,
        dataset.feature_names,
        dataset.target_name,
        {"end_to_end_pipeline": {"caller": True}},
    )
    result = EndToEndExperimentPipeline(_configuration()).run(colliding)
    assert result.metadata["end_to_end_pipeline"] == {"caller": True}
    assert result.metadata["model_training_execution_count"] == 1


def test_input_schema_traceability_across_all_results():
    result = _run()
    assert (
        result.global_explanation.feature_names
        == result.prepared_model_input.feature_names
    )
    assert (
        result.global_explanation.target_name == result.prepared_model_input.target_name
    )
    assert result.global_explanation.class_labels == (
        result.model_experiment_result.validation_prediction.class_labels
    )
    assert result.temporal_split.total_observation_count == 30
    assert result.prepared_experiment_dataset.total_observation_count == 30
    assert result.prepared_model_input.total_observation_count == 30


@pytest.mark.parametrize(
    ("model", "adapter_type"),
    [("logistic", LogisticRegressionAdapter), ("forest", RandomForestAdapter)],
)
def test_pipeline_trains_base_model_exactly_once(monkeypatch, model, adapter_type):
    calls = []
    original = adapter_type.train

    def spy(self, prepared_input):
        calls.append(prepared_input)
        return original(self, prepared_input)

    monkeypatch.setattr(adapter_type, "train", spy)
    result = _run(model)
    assert calls == [result.prepared_model_input]
    assert result.metadata["model_training_execution_count"] == 1
    assert result.metadata["shared_trained_model_instance"] is True


def test_registry_resolution_duplicate_and_unsupported_configuration():
    assert (
        default_model_adapter_registry.resolve(
            LogisticRegressionConfiguration()
        ).__class__.__name__
        == "_RegisteredAdapter"
    )
    registry = ModelAdapterRegistry()
    registry.register(LogisticRegressionConfiguration, lambda value: value)
    with pytest.raises(ValueError, match="already registered"):
        registry.register(LogisticRegressionConfiguration, lambda value: value)

    class UnknownConfiguration:
        def to_dict(self):
            return {"seed": 1}

    configuration = EndToEndExperimentConfiguration(
        TemporalSplitConfiguration(0.6, 0.2, 0.2),
        UnknownConfiguration(),
        ProbabilityCalibrationConfiguration("platt", "defect"),
        "defect",
    )
    with pytest.raises(TypeError, match="unsupported model configuration"):
        EndToEndExperimentPipeline(configuration).run(_dataset())


def test_model_fingerprint_is_shared_by_predictions_and_outcomes(requests):
    result = _run("logistic", requests, requests)
    fingerprint = result.trained_model.model_fingerprint
    assert (
        result.model_experiment_result.validation_prediction.metadata[
            "model_fingerprint"
        ]
        == fingerprint
    )
    assert (
        result.model_experiment_result.test_prediction.metadata["model_fingerprint"]
        == fingerprint
    )
    assert all(
        item.model_fingerprint == fingerprint
        for item in result.local_explanation_outcomes + result.counterfactual_outcomes
    )


def test_same_identifier_across_validation_and_test_remains_traceable():
    dataset = _dataset()
    records = list(dataset.records)
    records[4] = DatasetRecord(
        "shared", records[4].features, records[4].target, records[4].timestamp
    )
    records[10] = DatasetRecord(
        "shared", records[10].features, records[10].target, records[10].timestamp
    )
    duplicate_dataset = AdaptedDataset(
        dataset.dataset_name,
        dataset.dataset_version,
        records,
        dataset.feature_names,
        dataset.target_name,
    )
    requests = (
        ObservationExplanationRequest("test", "shared"),
        ObservationExplanationRequest("validation", "shared"),
    )
    result = EndToEndExperimentPipeline(
        _configuration("logistic", requests, requests)
    ).run(duplicate_dataset)
    assert tuple(
        (item.partition_name, item.observation_identifier, item.request_position)
        for item in result.local_explanation_outcomes
    ) == (("test", "shared", 0), ("validation", "shared", 1))


def test_experiment_fingerprint_is_stable_and_scientifically_sensitive(requests):
    baseline = _run("logistic", requests, requests).experiment_fingerprint
    assert baseline == _run("logistic", requests, requests).experiment_fingerprint
    assert baseline != _run("forest", requests, requests).experiment_fingerprint
    changed_seed = EndToEndExperimentConfiguration(
        TemporalSplitConfiguration(0.6, 0.2, 0.2),
        LogisticRegressionConfiguration(random_state=24),
        ProbabilityCalibrationConfiguration("platt", "defect"),
        "defect",
        requests,
        requests,
    )
    assert (
        baseline
        != EndToEndExperimentPipeline(changed_seed)
        .run(_dataset())
        .experiment_fingerprint
    )
    changed_calibration = EndToEndExperimentConfiguration(
        TemporalSplitConfiguration(0.6, 0.2, 0.2),
        LogisticRegressionConfiguration(random_state=23, max_iter=300),
        ProbabilityCalibrationConfiguration("isotonic", "defect"),
        "defect",
        requests,
        requests,
    )
    assert (
        baseline
        != EndToEndExperimentPipeline(changed_calibration)
        .run(_dataset())
        .experiment_fingerprint
    )
    assert baseline != _run("logistic", requests[:1], requests).experiment_fingerprint


def _aggregate_arguments(result):
    return {
        "temporal_split": result.temporal_split,
        "prepared_experiment_dataset": result.prepared_experiment_dataset,
        "prepared_model_input": result.prepared_model_input,
        "trained_model": result.trained_model,
        "model_experiment_result": result.model_experiment_result,
        "calibrated_experiment_result": result.calibrated_experiment_result,
        "global_explanation": result.global_explanation,
        "local_explanation_requests": result.local_explanation_requests,
        "counterfactual_requests": result.counterfactual_requests,
        "local_explanation_outcomes": result.local_explanation_outcomes,
        "counterfactual_outcomes": result.counterfactual_outcomes,
        "experiment_fingerprint": result.experiment_fingerprint,
        "metadata": result.metadata,
    }


def test_result_constructor_rejects_missing_extra_and_wrong_fingerprint_outcomes(
    requests,
):
    result = _run("logistic", requests, requests)
    arguments = _aggregate_arguments(result)
    with pytest.raises(ValueError, match="exactly one outcome"):
        EndToEndExperimentResult(
            **(
                arguments
                | {"local_explanation_outcomes": result.local_explanation_outcomes[:1]}
            )
        )
    with pytest.raises(ValueError, match="exactly one outcome"):
        EndToEndExperimentResult(
            **(
                arguments
                | {
                    "local_explanation_outcomes": (
                        *result.local_explanation_outcomes,
                        result.local_explanation_outcomes[-1],
                    )
                }
            )
        )
    original = result.local_explanation_outcomes[0]
    wrong = ExplanationOutcome(
        requests[0],
        0,
        status="successful",
        explanation_method=original.explanation_method,
        explanation=original.explanation,
        reason_code=None,
        model_fingerprint="0" * 64,
    )
    with pytest.raises(ValueError, match="fingerprint"):
        EndToEndExperimentResult(
            **(
                arguments
                | {
                    "local_explanation_outcomes": (
                        wrong,
                        *result.local_explanation_outcomes[1:],
                    )
                }
            )
        )
