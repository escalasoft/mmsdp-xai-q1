"""Tests for deterministic experiment artifact persistence."""

from __future__ import annotations

import hashlib
import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from experimentation.artifacts import (
    ExperimentArtifactManifest,
    ExperimentArtifactWriter,
)
from experimentation.evaluation import ExperimentEvaluationResult
from experimentation.runner import ExperimentRunResult
from experimentation.specification import ExperimentSpecification


@pytest.fixture
def experiment_objects():
    specification = ExperimentSpecification(
        experiment_id="exp-ñ",
        dataset_name="dataset",
        dataset_version="1",
        random_seed=7,
        modalities=("text",),
        algorithm="stacking",
        fusion_strategy="late",
        class_labels=("negative", "positive"),
        classification_threshold=0.5,
        output_directory="metadata-only",
        code_version="abc123",
        model_configuration={"depth": 2},
    )
    run_result = ExperimentRunResult(
        experiment_id="exp-ñ",
        class_labels=("negative", "positive"),
        predictions=("negative", "positive"),
        probabilities=((0.8, 0.2), (0.1, 0.9)),
        training_observation_count=4,
        evaluation_observation_count=2,
    )
    evaluation = _evaluation()
    return specification, run_result, evaluation


def _evaluation(
    *, experiment_id="exp-ñ", class_labels=("negative", "positive"), count=2
):
    return ExperimentEvaluationResult(
        experiment_id=experiment_id,
        positive_label="positive",
        class_labels=class_labels,
        observation_count=count,
        positive_count=1,
        positive_rate=0.5,
        true_negative=1 if count == 2 else 2,
        false_positive=0,
        false_negative=0,
        true_positive=1,
        accuracy=1.0,
        precision=1.0,
        recall=1.0,
        f1=1.0,
        mcc=1.0,
        roc_auc=1.0,
        pr_auc=1.0,
        brier_score=0.025,
    )


def test_writes_deterministic_content_and_hashes(tmp_path, experiment_objects):
    specification, run_result, evaluation = experiment_objects
    output = tmp_path / "nested" / "artifacts"

    manifest = ExperimentArtifactWriter().write(
        specification, run_result, evaluation, output
    )

    assert {path.name for path in output.iterdir()} == {
        "specification.json",
        "run_result.json",
        "evaluation.json",
        "manifest.json",
    }
    sources = {
        "specification.json": specification.to_dict(),
        "run_result.json": run_result.to_dict(),
        "evaluation.json": evaluation.to_dict(),
    }
    hashes = {}
    for filename, expected in sources.items():
        payload = (output / filename).read_bytes()
        assert payload.endswith(b"\n") and not payload.endswith(b"\n\n")
        assert json.loads(payload.decode("utf-8")) == expected
        hashes[filename] = hashlib.sha256(payload).hexdigest()
    assert manifest.specification_sha256 == hashes["specification.json"]
    assert manifest.run_result_sha256 == hashes["run_result.json"]
    assert manifest.evaluation_sha256 == hashes["evaluation.json"]
    assert json.loads((output / "manifest.json").read_text()) == manifest.to_dict()
    assert manifest.specification_file == "specification.json"
    assert manifest.run_result_file == "run_result.json"
    assert manifest.evaluation_file == "evaluation.json"
    assert manifest.manifest_file == "manifest.json"
    assert not list(output.glob("*.tmp"))
    assert not list(output.glob(".*.tmp"))


def test_repeated_writes_are_byte_identical(tmp_path, experiment_objects):
    first = tmp_path / "first"
    second = tmp_path / "second"
    writer = ExperimentArtifactWriter()
    writer.write(*experiment_objects, first)
    writer.write(*experiment_objects, second)

    for filename in ("specification.json", "run_result.json", "evaluation.json"):
        assert (first / filename).read_bytes() == (second / filename).read_bytes()


def test_manifest_is_immutable_deterministic_and_detached():
    digest = "a" * 64
    manifest = ExperimentArtifactManifest(
        "id", "out", "s", "r", "e", "m", digest, digest, digest
    )
    first = manifest.to_dict()
    first["experiment_id"] = "changed"
    assert manifest.to_dict() == manifest.to_dict()
    assert manifest.experiment_id == "id"
    with pytest.raises(FrozenInstanceError):
        manifest.experiment_id = "changed"


@pytest.mark.parametrize("dependency_index", range(3))
def test_rejects_none_dependencies(tmp_path, experiment_objects, dependency_index):
    arguments = [*experiment_objects, tmp_path]
    arguments[dependency_index] = None
    with pytest.raises(ValueError, match="must not be None"):
        ExperimentArtifactWriter().write(*arguments)


def test_rejects_empty_output_directory(experiment_objects):
    with pytest.raises(ValueError, match="output_directory"):
        ExperimentArtifactWriter().write(*experiment_objects, "")


def test_rejects_mismatched_experiment_ids(tmp_path, experiment_objects):
    specification, run_result, _ = experiment_objects
    with pytest.raises(ValueError, match="experiment IDs"):
        ExperimentArtifactWriter().write(
            specification, run_result, _evaluation(experiment_id="other"), tmp_path
        )


def test_rejects_mismatched_class_label_order(tmp_path, experiment_objects):
    specification, run_result, _ = experiment_objects
    evaluation = _evaluation(class_labels=("positive", "negative"))
    with pytest.raises(ValueError, match="class labels"):
        ExperimentArtifactWriter().write(
            specification, run_result, evaluation, tmp_path
        )


def test_rejects_mismatched_observation_count(tmp_path, experiment_objects):
    specification, run_result, _ = experiment_objects
    with pytest.raises(ValueError, match="observation counts"):
        ExperimentArtifactWriter().write(
            specification, run_result, _evaluation(count=3), tmp_path
        )


def test_existing_artifact_is_rejected_without_changes(tmp_path, experiment_objects):
    existing = tmp_path / "evaluation.json"
    existing.write_bytes(b"original")
    with pytest.raises(FileExistsError):
        ExperimentArtifactWriter().write(*experiment_objects, tmp_path)
    assert existing.read_bytes() == b"original"
    assert {path.name for path in tmp_path.iterdir()} == {"evaluation.json"}


def test_overwrite_replaces_artifacts_and_preserves_unrelated_file(
    tmp_path, experiment_objects
):
    unrelated = tmp_path / "notes.txt"
    unrelated.write_text("keep me")
    for filename in (
        "specification.json",
        "run_result.json",
        "evaluation.json",
        "manifest.json",
    ):
        (tmp_path / filename).write_text("stale")

    writer = ExperimentArtifactWriter(overwrite=True)
    writer.write(*experiment_objects, tmp_path)
    first = {
        path.name: path.read_bytes()
        for path in tmp_path.iterdir()
        if path.suffix == ".json"
    }
    writer.write(*experiment_objects, Path(tmp_path))

    assert first == {
        path.name: path.read_bytes()
        for path in tmp_path.iterdir()
        if path.suffix == ".json"
    }
    assert unrelated.read_text() == "keep me"


def test_source_objects_are_not_modified(tmp_path, experiment_objects):
    before = tuple(item.to_dict() for item in experiment_objects)
    ExperimentArtifactWriter().write(*experiment_objects, tmp_path)
    assert tuple(item.to_dict() for item in experiment_objects) == before


@pytest.mark.parametrize("value", [0, 1, None, "false"])
def test_overwrite_must_be_boolean(value):
    with pytest.raises(TypeError, match="overwrite"):
        ExperimentArtifactWriter(overwrite=value)
