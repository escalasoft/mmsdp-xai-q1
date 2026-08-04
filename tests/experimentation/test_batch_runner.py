"""Tests for deterministic sequential batch experiment execution."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, replace
from types import MappingProxyType

import pytest

import experimentation.batch_runner as batch_module
from dataset.contracts import AdaptedDataset, DatasetRecord
from dataset.temporal_splitter import TemporalSplitConfiguration
from experimentation.batch_runner import (
    BatchExperimentRecord,
    BatchExperimentResult,
    BatchExperimentRunner,
    BatchExperimentSpecification,
)
from experimentation.end_to_end_pipeline import (
    EndToEndExperimentConfiguration,
    EndToEndExperimentPipeline,
)
from explainability.explanation_runner import ObservationExplanationRequest
from models.calibration import ProbabilityCalibrationConfiguration
from models.logistic_regression_adapter import LogisticRegressionConfiguration
from models.random_forest_adapter import RandomForestConfiguration


def _dataset() -> AdaptedDataset:
    records = tuple(
        DatasetRecord(
            identifier={"commit": [f"c{index:02d}"]},
            features={
                "age": float(index - 20),
                "churn": float((index % 7) - 3),
            },
            target="defect" if index % 2 else "clean",
            timestamp=40 - index,
            metadata={"source_order": index},
        )
        for index in range(40)
    )
    return AdaptedDataset(
        "commits",
        "v10.6",
        records,
        ("age", "churn"),
        "defect_status",
        {"source": {"tags": ["synthetic", "temporal"]}},
    )


def _request(partition: str, chronological_index: int):
    source_index = 39 - chronological_index
    return ObservationExplanationRequest(
        partition, {"commit": [f"c{source_index:02d}"]}
    )


def _configurations() -> tuple[EndToEndExperimentConfiguration, ...]:
    requests = (_request("validation", 25), _request("test", 33))
    split = TemporalSplitConfiguration(0.6, 0.2, 0.2)
    model_configurations = (
        LogisticRegressionConfiguration(random_state=17, max_iter=300),
        RandomForestConfiguration(n_estimators=13, random_state=17),
    )
    return tuple(
        EndToEndExperimentConfiguration(
            split,
            model_configuration,
            ProbabilityCalibrationConfiguration(method, "defect"),
            "defect",
            requests,
            requests,
        )
        for model_configuration in model_configurations
        for method in ("platt", "isotonic")
    )


@pytest.fixture(scope="module")
def batch_execution():
    dataset = _dataset()
    configurations = _configurations()
    specification = BatchExperimentSpecification(
        "calibration-matrix",
        dataset,
        configurations,
        {"study": {"sprints": ["10.6"]}},
    )
    captured_pipeline_results = []
    pipeline_type = batch_module.EndToEndExperimentPipeline

    class CapturingPipeline:
        def __init__(self, configuration):
            self._pipeline = pipeline_type(configuration)

        def run(self, source_dataset):
            pipeline_result = self._pipeline.run(source_dataset)
            captured_pipeline_results.append(pipeline_result)
            return pipeline_result

    batch_module.EndToEndExperimentPipeline = CapturingPipeline
    try:
        result = BatchExperimentRunner().run(specification)
    finally:
        batch_module.EndToEndExperimentPipeline = pipeline_type
    return (
        dataset,
        configurations,
        specification,
        result,
        tuple(captured_pipeline_results),
    )


def test_four_configuration_execution_order_and_record_count(batch_execution):
    _, configurations, specification, result, captured = batch_execution
    assert isinstance(result, BatchExperimentResult)
    assert result.execution_count == result.successful_execution_count == 4
    assert result.failed_execution_count == 0
    assert result.failures == ()
    assert len(result.records) == len(configurations) == 4
    assert len(captured) == 4
    assert all(isinstance(record, BatchExperimentRecord) for record in result.records)
    assert tuple(record.execution_index for record in result.records) == (0, 1, 2, 3)
    assert tuple(record.experiment_fingerprint for record in result.records) == (
        specification.configuration_fingerprints
    )


def test_model_and_calibration_identification_is_exact(batch_execution):
    _, _, _, result, _ = batch_execution
    assert tuple(
        (record.model_name, record.model_family, record.calibration_method)
        for record in result.records
    ) == (
        ("logistic-regression", "logistic-regression", "platt"),
        ("logistic-regression", "logistic-regression", "isotonic"),
        ("random-forest", "random-forest", "platt"),
        ("random-forest", "random-forest", "isotonic"),
    )


def test_counts_training_and_shared_snapshot_invariants(batch_execution):
    _, _, _, result, _ = batch_execution
    for record in result.records:
        assert (
            record.training_observation_count,
            record.validation_observation_count,
            record.test_observation_count,
        ) == (24, 8, 8)
        assert (record.validation_positive_count, record.test_positive_count) == (4, 4)
        assert record.model_training_execution_count == 1
        assert record.shared_trained_model_instance is True


def test_metrics_and_brier_scores_are_copied_from_pipeline_results(batch_execution):
    _, configurations, _, result, pipeline_results = batch_execution
    metric_names = ("accuracy", "precision", "recall", "f1", "mcc", "roc_auc", "pr_auc")
    for configuration, record, pipeline_result in zip(
        configurations, result.records, pipeline_results, strict=True
    ):
        assert pipeline_result.experiment_fingerprint == (
            EndToEndExperimentPipeline.experiment_fingerprint(
                batch_execution[0], configuration
            )
        )
        experiment = pipeline_result.model_experiment_result
        calibrated = pipeline_result.calibrated_experiment_result
        for partition in ("validation", "test"):
            evaluation = getattr(experiment, f"{partition}_evaluation")
            for metric in metric_names:
                assert getattr(record, f"uncalibrated_{partition}_{metric}") == getattr(
                    evaluation, metric
                )
        assert record.calibrated_validation_brier_score == (
            calibrated.calibrated_validation_calibration.brier_score
        )
        assert record.calibrated_test_brier_score == (
            calibrated.calibrated_test_calibration.brier_score
        )
        assert record.uncalibrated_validation_brier_score == (
            calibrated.uncalibrated_validation_calibration.brier_score
        )
        assert record.uncalibrated_test_brier_score == (
            calibrated.uncalibrated_test_calibration.brier_score
        )


def test_explanation_counts_distinguish_supported_and_unsupported(batch_execution):
    _, _, _, result, _ = batch_execution
    for record in result.records[:2]:
        assert record.global_explanation_supported is True
        assert (
            record.requested_local_explanation_count,
            record.successful_local_explanation_count,
            record.unsupported_local_explanation_count,
        ) == (2, 2, 0)
        assert (
            record.requested_counterfactual_count,
            record.successful_counterfactual_count,
            record.unsupported_counterfactual_count,
        ) == (2, 2, 0)
    for record in result.records[2:]:
        assert (
            record.requested_local_explanation_count,
            record.successful_local_explanation_count,
            record.unsupported_local_explanation_count,
        ) == (2, 0, 2)
        assert (
            record.requested_counterfactual_count,
            record.successful_counterfactual_count,
            record.unsupported_counterfactual_count,
        ) == (2, 0, 2)


def test_source_dataset_and_configuration_sequence_are_not_mutated():
    dataset = _dataset()
    configurations = list(_configurations())
    dataset_before = dataset.to_dict()
    configurations_before = [item.to_dict() for item in configurations]
    specification = BatchExperimentSpecification("matrix", dataset, configurations)
    BatchExperimentRunner().run(specification)
    assert dataset.to_dict() == dataset_before
    assert [item.to_dict() for item in configurations] == configurations_before


def test_specification_records_and_result_metadata_are_immutable(batch_execution):
    _, _, specification, result, _ = batch_execution
    with pytest.raises(FrozenInstanceError):
        specification.experiment_name = "changed"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        result.records[0].model_name = "changed"  # type: ignore[misc]
    assert isinstance(specification.metadata, MappingProxyType)
    assert isinstance(result.metadata, MappingProxyType)
    with pytest.raises(TypeError):
        result.metadata["study"]["sprints"] += ("changed",)  # type: ignore[index,operator]
    with pytest.raises(TypeError):
        result.records[0].metadata["source"]["tags"] += ("changed",)  # type: ignore[index,operator]


def test_to_dict_and_to_rows_are_deterministic_detached_and_ordered(batch_execution):
    _, _, _, result, _ = batch_execution
    first = result.to_dict()
    second = result.to_dict()
    rows = result.to_rows()
    assert first == second and first is not second
    assert rows == first["records"]
    assert [row["execution_index"] for row in rows] == [0, 1, 2, 3]
    rows[0]["metadata"]["source"]["tags"].append("changed")
    first["metadata"]["study"]["sprints"].append("changed")
    assert result.to_dict() == second


def test_runtime_is_excluded_from_record_structural_equality(batch_execution):
    _, _, _, result, _ = batch_execution
    record = result.records[0]
    assert record == replace(
        record, execution_duration_seconds=record.execution_duration_seconds + 1.0
    )


def test_empty_invalid_and_duplicate_specifications_are_rejected():
    dataset = _dataset()
    configuration = _configurations()[0]
    with pytest.raises(ValueError, match="must not be empty"):
        BatchExperimentSpecification("batch", dataset, ())
    with pytest.raises(TypeError, match="AdaptedDataset"):
        BatchExperimentSpecification("batch", object(), (configuration,))
    with pytest.raises(ValueError, match="duplicate experiment fingerprints"):
        BatchExperimentSpecification("batch", dataset, (configuration, configuration))


def test_public_fingerprint_api_is_shared_and_private_helper_is_not_imported(
    batch_execution,
):
    dataset, configurations, specification, _, pipeline_results = batch_execution
    expected = tuple(
        EndToEndExperimentPipeline.experiment_fingerprint(dataset, configuration)
        for configuration in configurations
    )
    assert specification.configuration_fingerprints == expected
    assert tuple(item.experiment_fingerprint for item in pipeline_results) == expected
    assert "_fingerprint" not in vars(batch_module)


def test_metric_names_are_explicit_about_calibration_state(batch_execution):
    _, _, _, result, _ = batch_execution
    names = {item.name for item in fields(BatchExperimentRecord)}
    assert {
        "uncalibrated_validation_accuracy",
        "uncalibrated_test_pr_auc",
        "uncalibrated_validation_brier_score",
        "uncalibrated_test_brier_score",
        "calibrated_validation_brier_score",
        "calibrated_test_brier_score",
    } <= names
    assert "validation_brier_score" not in names
    assert "test_brier_score" not in names
    assert "calibrated_validation_accuracy" not in names
    assert "calibrated_test_accuracy" not in names
    assert set(result.to_rows()[0]) == names - {"execution_duration_seconds"}


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"execution_index": -1}, "execution_index"),
        ({"validation_observation_count": -1}, "validation_observation_count"),
        ({"uncalibrated_validation_accuracy": -0.1}, "accuracy"),
        ({"uncalibrated_test_roc_auc": float("inf")}, "roc_auc"),
        ({"uncalibrated_validation_mcc": float("nan")}, "mcc"),
        ({"execution_duration_seconds": float("nan")}, "duration"),
        ({"requested_local_explanation_count": 3}, "requested_local"),
        ({"model_training_execution_count": 0}, "training_execution"),
        ({"shared_trained_model_instance": False}, "shared_trained"),
    ],
)
def test_record_rejects_invalid_counts_metrics_and_invariants(
    batch_execution, changes, message
):
    _, _, _, result, _ = batch_execution
    with pytest.raises((TypeError, ValueError), match=message):
        replace(result.records[0], **changes)


def test_result_rejects_unordered_indexes_and_duplicate_fingerprints(batch_execution):
    _, _, _, result, _ = batch_execution
    first, second = result.records[:2]
    with pytest.raises(ValueError, match="indexes"):
        BatchExperimentResult(
            experiment_name=result.experiment_name,
            records=(
                replace(first, execution_index=1),
                replace(second, execution_index=0),
            ),
            execution_count=2,
            metadata=result.metadata,
        )
    with pytest.raises(ValueError, match="fingerprints"):
        BatchExperimentResult(
            experiment_name=result.experiment_name,
            records=(
                first,
                replace(
                    second,
                    execution_index=1,
                    experiment_fingerprint=first.experiment_fingerprint,
                ),
            ),
            execution_count=2,
            metadata=result.metadata,
        )


def test_result_rejects_cross_experiment_records_and_failures(batch_execution):
    _, _, _, result, _ = batch_execution
    record = result.records[0]
    with pytest.raises(ValueError, match="experiment_name"):
        BatchExperimentResult(
            experiment_name="another-experiment",
            records=(record,),
            execution_count=1,
            metadata={},
        )
    with pytest.raises(ValueError, match="zero failures"):
        BatchExperimentResult(
            experiment_name=result.experiment_name,
            records=(record,),
            execution_count=1,
            metadata={},
            failed_execution_count=1,
            failures=("failure",),
        )


def test_scientific_serialization_is_repeatable_and_runtime_is_optional(
    batch_execution,
):
    dataset, configurations, _, original, _ = batch_execution
    specification = BatchExperimentSpecification(
        "calibration-matrix",
        dataset,
        configurations[:1],
        {"study": {"sprints": ["10.6"]}},
    )
    repeated = BatchExperimentRunner().run(specification)
    original_single = BatchExperimentResult(
        experiment_name=original.experiment_name,
        records=original.records[:1],
        execution_count=1,
        metadata=original.metadata,
    )
    assert original_single.to_dict() == repeated.to_dict()
    assert original_single.to_rows() == repeated.to_rows()
    assert "execution_duration_seconds" not in repeated.to_rows()[0]
    runtime_rows = repeated.to_rows(include_runtime=True)
    runtime_dictionary = repeated.to_dict(include_runtime=True)
    assert runtime_rows[0]["execution_duration_seconds"] >= 0.0
    assert runtime_dictionary["records"] == runtime_rows


def test_stable_fingerprints_and_scientific_record_equality():
    first_specification = BatchExperimentSpecification(
        "matrix", _dataset(), _configurations()[:1]
    )
    second_specification = BatchExperimentSpecification(
        "matrix", _dataset(), _configurations()[:1]
    )
    assert first_specification.configuration_fingerprints == (
        second_specification.configuration_fingerprints
    )
    first = BatchExperimentRunner().run(first_specification)
    second = BatchExperimentRunner().run(second_specification)
    assert first.records == second.records
    assert first.to_dict() == second.to_dict()


def test_pipeline_fingerprint_mismatch_is_rejected(monkeypatch):
    specification = BatchExperimentSpecification(
        "matrix", _dataset(), _configurations()
    )
    actual_pipeline = EndToEndExperimentPipeline

    class MismatchingPipeline:
        def __init__(self, configuration):
            self._pipeline = actual_pipeline(configuration)

        def run(self, dataset):
            result = self._pipeline.run(dataset)
            object.__setattr__(result, "experiment_fingerprint", "0" * 64)
            return result

    monkeypatch.setattr(batch_module, "EndToEndExperimentPipeline", MismatchingPipeline)
    with pytest.raises(ValueError, match="fingerprint"):
        BatchExperimentRunner().run(specification)


def test_fail_fast_is_deterministic_and_does_not_execute_later_configurations(
    monkeypatch,
):
    specification = BatchExperimentSpecification(
        "matrix", _dataset(), _configurations()
    )
    calls = []

    class FailingPipeline:
        def __init__(self, configuration):
            calls.append(configuration)

        def run(self, dataset):
            raise RuntimeError("deterministic failure")

    monkeypatch.setattr(batch_module, "EndToEndExperimentPipeline", FailingPipeline)
    with pytest.raises(RuntimeError, match="deterministic failure"):
        BatchExperimentRunner().run(specification)
    assert calls == [specification.configurations[0]]


def test_public_api_is_narrow_and_runner_surface_is_batch_only():
    assert batch_module.__all__ == [
        "BatchExperimentSpecification",
        "BatchExperimentRecord",
        "BatchExperimentResult",
        "BatchExperimentRunner",
    ]
    forbidden = {"train", "predict", "fit", "save", "write", "plot"}
    assert forbidden.isdisjoint(dir(BatchExperimentRunner))


def test_runner_rejects_invalid_specification():
    with pytest.raises(TypeError, match="BatchExperimentSpecification"):
        BatchExperimentRunner().run(object())
