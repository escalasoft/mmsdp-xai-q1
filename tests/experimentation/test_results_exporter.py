"""Tests for deterministic, framework-neutral scientific results export."""

from __future__ import annotations

import csv
import json
from dataclasses import FrozenInstanceError, fields, replace
from pathlib import Path

import pytest

import experimentation.results_exporter as exporter_module
from experimentation.batch_runner import BatchExperimentRecord, BatchExperimentResult
from experimentation.results_exporter import (
    ScientificResultsArtifact,
    ScientificResultsExportConfiguration,
    ScientificResultsExporter,
)


def _record(index: int, *, runtime: float = 1.0) -> BatchExperimentRecord:
    offset = index / 10
    return BatchExperimentRecord(
        experiment_name="comparación-científica",
        execution_index=index,
        experiment_fingerprint=f"fingerprint-{index}",
        dataset_name="datos-ñ",
        dataset_version="v1",
        model_name=("árbol|modelo" if index == 0 else "linear_model"),
        model_family="tree" if index == 0 else "linear",
        calibration_method="platt&scale" if index == 0 else "isotonic",
        training_observation_count=60,
        validation_observation_count=20,
        test_observation_count=20,
        validation_positive_count=8,
        test_positive_count=9,
        uncalibrated_validation_positive_rate=0.4,
        uncalibrated_test_positive_rate=0.45,
        uncalibrated_validation_accuracy=0.70 + offset,
        uncalibrated_validation_precision=0.71 + offset,
        uncalibrated_validation_recall=0.72 + offset,
        uncalibrated_validation_f1=0.73 + offset,
        uncalibrated_validation_mcc=0.44 + offset,
        uncalibrated_validation_roc_auc=0.81 + offset,
        uncalibrated_validation_pr_auc=0.76 + offset,
        uncalibrated_validation_brier_score=0.19 - offset,
        calibrated_validation_brier_score=0.17 - offset,
        uncalibrated_test_accuracy=0.69 + offset,
        uncalibrated_test_precision=0.68 + offset,
        uncalibrated_test_recall=0.67 + offset,
        uncalibrated_test_f1=0.66 + offset,
        uncalibrated_test_mcc=0.42 + offset,
        uncalibrated_test_roc_auc=0.80 + offset,
        uncalibrated_test_pr_auc=0.75 + offset,
        uncalibrated_test_brier_score=0.20 - offset,
        calibrated_test_brier_score=0.18 - offset,
        global_explanation_supported=True,
        requested_local_explanation_count=2,
        successful_local_explanation_count=1,
        unsupported_local_explanation_count=1,
        requested_counterfactual_count=2,
        successful_counterfactual_count=1,
        unsupported_counterfactual_count=1,
        model_training_execution_count=1,
        shared_trained_model_instance=True,
        execution_duration_seconds=runtime,
        metadata={"nota": ["análisis", index]},
    )


def _result(*, runtime_delta: float = 0.0) -> BatchExperimentResult:
    return BatchExperimentResult(
        experiment_name="comparación-científica",
        records=(
            _record(0, runtime=1.25 + runtime_delta),
            _record(1, runtime=2.50 + runtime_delta),
        ),
        execution_count=2,
        metadata={"estudio": {"idioma": "español"}},
    )


def _configuration(tmp_path: Path, **changes) -> ScientificResultsExportConfiguration:
    values = {
        "output_directory": tmp_path / "results",
        "artifact_prefix": "thesis",
        "metadata": {"sprint": ["10.7"]},
    }
    values.update(changes)
    return ScientificResultsExportConfiguration(**values)


def _read_csv(path: str) -> list[dict[str, str]]:
    with Path(path).open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def _artifact_values(**changes):
    values = {
        "experiment_name": "experiment",
        "execution_count": 1,
        "complete_csv_path": "complete.csv",
        "summary_csv_path": "summary.csv",
        "markdown_table_path": "comparison.md",
        "latex_table_path": "comparison.tex",
        "manifest_json_path": "manifest.json",
        "complete_row_count": 1,
        "summary_row_count": 1,
        "exported_columns": ("model_name",),
        "scientific_digest": "0" * 64,
        "metadata": {},
    }
    values.update(changes)
    return values


def test_complete_export_names_columns_content_and_manifest(tmp_path):
    result = _result()
    artifact = ScientificResultsExporter().export(result, _configuration(tmp_path))
    assert {
        Path(path).name
        for path in (
            artifact.complete_csv_path,
            artifact.summary_csv_path,
            artifact.markdown_table_path,
            artifact.latex_table_path,
            artifact.manifest_json_path,
        )
    } == {
        "thesis_complete.csv",
        "thesis_summary.csv",
        "thesis_comparison.md",
        "thesis_comparison.tex",
        "thesis_manifest.json",
    }
    complete = _read_csv(artifact.complete_csv_path)
    expected = [
        item.name
        for item in fields(BatchExperimentRecord)
        if item.name != "execution_duration_seconds"
    ]
    assert list(complete[0]) == expected
    assert artifact.complete_row_count == artifact.summary_row_count == 2
    assert complete[0]["model_name"] == "árbol|modelo"
    summary = _read_csv(artifact.summary_csv_path)
    assert {
        "execution_index",
        "uncalibrated_validation_roc_auc",
        "calibrated_validation_brier_score",
        "uncalibrated_test_brier_score",
        "calibrated_test_brier_score",
        "unsupported_counterfactual_count",
    } <= set(summary[0])
    markdown = Path(artifact.markdown_table_path).read_text(encoding="utf-8")
    assert "| Model | Calibration | ROC-AUC | PR-AUC" in markdown
    assert "árbol\\|modelo" in markdown
    assert "0.8000" in markdown
    latex = Path(artifact.latex_table_path).read_text(encoding="utf-8")
    assert "\\begin{tabular}{llrrrrrrrr}" in latex
    assert "\\end{tabular}" in latex
    assert "linear\\_model" in latex
    assert "platt\\&scale" in latex
    assert "\\label{tab:thesis}" in latex
    manifest = json.loads(Path(artifact.manifest_json_path).read_text(encoding="utf-8"))
    assert manifest["export_schema_version"] == "1.0"
    assert manifest["experiment_name"] == result.experiment_name
    assert manifest["experiment_fingerprints"] == [
        "fingerprint-0",
        "fingerprint-1",
    ]
    assert manifest["source_batch_metadata"]["estudio"]["idioma"] == "español"
    assert manifest["scientific_digest"] == artifact.scientific_digest
    assert manifest["scientific_content"] == {
        "export_schema_version": "1.0",
        "experiment_name": result.experiment_name,
        "execution_count": 2,
        "experiment_fingerprints": ["fingerprint-0", "fingerprint-1"],
        "decimal_places": 4,
        "include_runtime": False,
        "exported_columns": list(artifact.exported_columns),
        "sort_columns": [],
        "rows": result.to_rows(),
    }


def test_digest_is_deterministic_and_sensitive_to_metric_and_precision(tmp_path):
    exporter = ScientificResultsExporter()
    first = exporter.export(_result(), _configuration(tmp_path, artifact_prefix="a"))
    second = exporter.export(_result(), _configuration(tmp_path, artifact_prefix="b"))
    changed_record = replace(_record(0), uncalibrated_test_roc_auc=0.79)
    changed = BatchExperimentResult(
        experiment_name="comparación-científica",
        records=(changed_record, _record(1)),
        execution_count=2,
        metadata=_result().metadata,
    )
    metric = exporter.export(changed, _configuration(tmp_path, artifact_prefix="c"))
    precision = exporter.export(
        _result(), _configuration(tmp_path, artifact_prefix="d", decimal_places=3)
    )
    assert first.scientific_digest == second.scientific_digest
    assert metric.scientific_digest != first.scientific_digest
    assert precision.scientific_digest != first.scientific_digest


def test_digest_covers_experiment_schema_and_fingerprint_identity(
    tmp_path, monkeypatch
):
    exporter = ScientificResultsExporter()
    baseline = exporter.export(
        _result(), _configuration(tmp_path, artifact_prefix="baseline")
    )
    renamed_records = tuple(
        replace(record, experiment_name="renamed-experiment")
        for record in _result().records
    )
    renamed = BatchExperimentResult(
        experiment_name="renamed-experiment",
        records=renamed_records,
        execution_count=2,
        metadata={},
    )
    renamed_artifact = exporter.export(
        renamed, _configuration(tmp_path, artifact_prefix="renamed")
    )
    changed_fingerprint = BatchExperimentResult(
        experiment_name=_result().experiment_name,
        records=(
            replace(_record(0), experiment_fingerprint="changed-fingerprint"),
            _record(1),
        ),
        execution_count=2,
        metadata={},
    )
    fingerprint_artifact = exporter.export(
        changed_fingerprint,
        _configuration(tmp_path, artifact_prefix="fingerprint"),
    )
    shorter = BatchExperimentResult(
        experiment_name=_result().experiment_name,
        records=(_record(0),),
        execution_count=1,
        metadata={},
    )
    execution_artifact = exporter.export(
        shorter, _configuration(tmp_path, artifact_prefix="execution")
    )
    monkeypatch.setattr(exporter_module, "_SCHEMA_VERSION", "2.0")
    schema_artifact = exporter.export(
        _result(), _configuration(tmp_path, artifact_prefix="schema")
    )
    assert renamed_artifact.scientific_digest != baseline.scientific_digest
    assert fingerprint_artifact.scientific_digest != baseline.scientific_digest
    assert execution_artifact.scientific_digest != baseline.scientific_digest
    assert schema_artifact.scientific_digest != baseline.scientific_digest


def test_digest_tracks_actual_sorted_order_and_preserves_raw_metrics(tmp_path):
    exporter = ScientificResultsExporter()
    result = BatchExperimentResult(
        experiment_name=_result().experiment_name,
        records=(
            _record(0),
            replace(_record(1), uncalibrated_test_roc_auc=0.87654321),
        ),
        execution_count=2,
        metadata={},
    )
    unsorted = exporter.export(
        result,
        _configuration(tmp_path, artifact_prefix="unsorted", decimal_places=2),
    )
    sorted_artifact = exporter.export(
        result,
        _configuration(
            tmp_path,
            artifact_prefix="sorted-digest",
            sort_columns=("model_name",),
            decimal_places=2,
        ),
    )
    manifest = json.loads(
        Path(sorted_artifact.manifest_json_path).read_text(encoding="utf-8")
    )
    assert sorted_artifact.scientific_digest != unsorted.scientific_digest
    assert manifest["scientific_content"]["experiment_fingerprints"] == [
        "fingerprint-1",
        "fingerprint-0",
    ]
    assert (
        manifest["scientific_content"]["rows"][0]["uncalibrated_test_roc_auc"]
        == 0.87654321
    )
    assert "0.88" in Path(sorted_artifact.markdown_table_path).read_text(
        encoding="utf-8"
    )


def test_runtime_policy_controls_columns_and_digest(tmp_path):
    exporter = ScientificResultsExporter()
    excluded_a = exporter.export(
        _result(), _configuration(tmp_path, artifact_prefix="ea")
    )
    excluded_b = exporter.export(
        _result(runtime_delta=7), _configuration(tmp_path, artifact_prefix="eb")
    )
    included_a = exporter.export(
        _result(), _configuration(tmp_path, artifact_prefix="ia", include_runtime=True)
    )
    included_b = exporter.export(
        _result(runtime_delta=7),
        _configuration(tmp_path, artifact_prefix="ib", include_runtime=True),
    )
    assert "execution_duration_seconds" not in excluded_a.exported_columns
    assert "execution_duration_seconds" in included_a.exported_columns
    assert excluded_a.scientific_digest == excluded_b.scientific_digest
    assert included_a.scientific_digest != included_b.scientific_digest


def test_default_order_and_explicit_sorting_do_not_mutate_result(tmp_path):
    result = _result()
    before = result.to_dict(include_runtime=True)
    default = ScientificResultsExporter().export(
        result, _configuration(tmp_path, artifact_prefix="default")
    )
    ordered = ScientificResultsExporter().export(
        result,
        _configuration(
            tmp_path,
            artifact_prefix="sorted",
            sort_columns=("model_name",),
        ),
    )
    assert [row["execution_index"] for row in _read_csv(default.complete_csv_path)] == [
        "0",
        "1",
    ]
    assert [row["execution_index"] for row in _read_csv(ordered.complete_csv_path)] == [
        "1",
        "0",
    ]
    assert result.to_dict(include_runtime=True) == before


def test_configuration_and_artifact_are_deeply_immutable_and_detached(tmp_path):
    source = {"nested": ["value"]}
    configuration = _configuration(tmp_path, metadata=source)
    source["nested"].append("later")
    with pytest.raises(FrozenInstanceError):
        configuration.decimal_places = 2
    with pytest.raises(TypeError):
        configuration.metadata["new"] = "value"
    assert configuration.metadata["nested"] == ("value",)
    first = configuration.to_dict()
    first["metadata"]["nested"].append("detached")
    assert configuration.to_dict() == configuration.to_dict()
    artifact = ScientificResultsExporter().export(_result(), configuration)
    with pytest.raises(FrozenInstanceError):
        artifact.execution_count = 3
    with pytest.raises(TypeError):
        artifact.metadata["new"] = "value"
    detached = artifact.to_dict()
    detached["metadata"]["nested"].append("detached")
    assert artifact.metadata["nested"] == ("value",)
    assert isinstance(artifact, ScientificResultsArtifact)


@pytest.mark.parametrize("metadata", [[], "metadata", 1, None])
def test_configuration_rejects_non_mapping_metadata(tmp_path, metadata):
    with pytest.raises(TypeError, match="metadata must be a mapping"):
        _configuration(tmp_path, metadata=metadata)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_configuration_rejects_nested_non_finite_metadata(tmp_path, value):
    with pytest.raises(ValueError, match="NaN or infinity"):
        _configuration(tmp_path, metadata={"nested": {"value": value}})


@pytest.mark.parametrize("metadata", [[], "metadata", 1, None])
def test_artifact_rejects_non_mapping_metadata(metadata):
    with pytest.raises(TypeError, match="metadata must be a mapping"):
        ScientificResultsArtifact(**_artifact_values(metadata=metadata))


@pytest.mark.parametrize(
    ("columns", "message"),
    [
        ((), "must not be empty"),
        (("model_name", "model_name"), "duplicates"),
    ],
)
def test_artifact_rejects_empty_and_duplicate_exported_columns(columns, message):
    with pytest.raises(ValueError, match=message):
        ScientificResultsArtifact(**_artifact_values(exported_columns=columns))


@pytest.mark.parametrize(
    "changes",
    [
        {"execution_count": 2},
        {"complete_row_count": 0},
        {"summary_row_count": 0},
    ],
)
def test_artifact_rejects_mismatched_execution_and_row_counts(changes):
    with pytest.raises(ValueError, match="row_count must equal execution_count"):
        ScientificResultsArtifact(**_artifact_values(**changes))


@pytest.mark.parametrize("output", ["", "   ", 42, None])
def test_invalid_output_directory_is_rejected(output):
    with pytest.raises((TypeError, ValueError)):
        ScientificResultsExportConfiguration(output_directory=output)


@pytest.mark.parametrize(
    "prefix", ["", "../escape", "path/name", "path\\name", "/absolute", ".", "a b"]
)
def test_invalid_prefix_is_rejected(tmp_path, prefix):
    with pytest.raises(ValueError):
        _configuration(tmp_path, artifact_prefix=prefix)


@pytest.mark.parametrize("places", [-1, True, 1.5, "2"])
def test_invalid_decimal_precision_is_rejected(tmp_path, places):
    with pytest.raises((TypeError, ValueError)):
        _configuration(tmp_path, decimal_places=places)


@pytest.mark.parametrize(
    "columns", ["model_name", ("unknown",), ("model_name", "model_name"), (1,)]
)
def test_invalid_sort_columns_are_rejected(tmp_path, columns):
    with pytest.raises((TypeError, ValueError)):
        _configuration(tmp_path, sort_columns=columns)


def test_runtime_sort_requires_runtime_inclusion(tmp_path):
    with pytest.raises(ValueError, match="runtime is included"):
        _configuration(tmp_path, sort_columns=("execution_duration_seconds",))


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_scientific_content_is_rejected(tmp_path, value):
    result = _result()
    object.__setattr__(result.records[0], "uncalibrated_test_roc_auc", value)
    with pytest.raises(ValueError, match="NaN|infinity|finite"):
        ScientificResultsExporter().export(result, _configuration(tmp_path))


def test_existing_files_are_replaced_atomically(tmp_path):
    configuration = _configuration(tmp_path)
    destination = Path(configuration.output_directory)
    destination.mkdir(parents=True)
    existing = destination / "thesis_complete.csv"
    existing.write_text("old", encoding="utf-8")
    artifact = ScientificResultsExporter().export(_result(), configuration)
    assert Path(artifact.complete_csv_path).read_text(encoding="utf-8") != "old"
    assert not list(destination.glob(".*.tmp"))
    assert not list(destination.glob(".*.backup"))


def test_failure_restores_existing_files_and_cleans_temporary_files(
    tmp_path, monkeypatch
):
    configuration = _configuration(tmp_path)
    destination = Path(configuration.output_directory)
    destination.mkdir(parents=True)
    expected = {}
    for suffix in (
        "complete.csv",
        "summary.csv",
        "comparison.md",
        "comparison.tex",
        "manifest.json",
    ):
        path = destination / f"thesis_{suffix}"
        path.write_text(f"old-{suffix}", encoding="utf-8")
        expected[path] = f"old-{suffix}"
    actual_replace = exporter_module.os.replace
    calls = 0

    def fail_once(source, target):
        nonlocal calls
        calls += 1
        if calls == 7:
            raise OSError("simulated replacement failure")
        actual_replace(source, target)

    monkeypatch.setattr(exporter_module.os, "replace", fail_once)
    with pytest.raises(OSError, match="simulated"):
        ScientificResultsExporter().export(_result(), configuration)
    assert {path: path.read_text(encoding="utf-8") for path in expected} == expected
    assert not list(destination.glob(".*.tmp"))
    assert not list(destination.glob(".*.backup"))


def test_public_api_and_exporter_surface_are_narrow():
    assert exporter_module.__all__ == [
        "ScientificResultsExportConfiguration",
        "ScientificResultsArtifact",
        "ScientificResultsExporter",
    ]
    forbidden = {"train", "fit", "predict", "plot", "calibrate", "explain"}
    assert forbidden.isdisjoint(dir(ScientificResultsExporter))
