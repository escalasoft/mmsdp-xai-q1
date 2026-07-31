"""Tests for framework-neutral stacking experiment execution."""

from collections.abc import Sequence
from dataclasses import FrozenInstanceError

import pytest

from experimentation.runner import ExperimentRunner, ExperimentRunResult
from experimentation.specification import ExperimentSpecification
from fusion.contracts import PredictionOutput
from fusion.stacking_features import StackingFeatureBuilder

MODALITIES = ("code", "text")
LABELS = ("clean", "defective")


class RecordingBuilder(StackingFeatureBuilder):
    """Feature builder recording its public orchestration calls."""

    def __init__(self) -> None:
        super().__init__(MODALITIES, LABELS)
        self.calls: list[Sequence[PredictionOutput]] = []

    def build_features(
        self, predictions: Sequence[PredictionOutput], /
    ) -> tuple[tuple[object, ...], ...]:
        self.calls.append(predictions)
        return super().build_features(predictions)


class RecordingModel:
    """Deterministic structural stacking model."""

    def __init__(self) -> None:
        self.fit_calls: list[tuple[object, object]] = []
        self.predict_calls: list[object] = []
        self.proba_calls: list[object] = []
        self.predictions = ["clean", "defective"]
        self.probabilities = [[0.8, 0.2], [0.1, 0.9]]

    def fit(self, features: object, targets: object, /) -> "RecordingModel":
        self.fit_calls.append((features, targets))
        return self

    def predict(self, features: object, /) -> object:
        self.predict_calls.append(features)
        return self.predictions

    def predict_proba(self, features: object, /) -> object:
        self.proba_calls.append(features)
        return self.probabilities


@pytest.fixture
def specification() -> ExperimentSpecification:
    return ExperimentSpecification(
        experiment_id="stacking-8.5",
        dataset_name="fixture",
        dataset_version="1",
        random_seed=17,
        modalities=MODALITIES,
        algorithm="recording",
        fusion_strategy="stacking",
        class_labels=LABELS,
        classification_threshold=0.5,
        output_directory="unused",
        code_version="test",
    )


def outputs(observations: int = 2) -> tuple[PredictionOutput, ...]:
    return tuple(
        PredictionOutput(
            probabilities=(0.75, 0.25),
            class_labels=LABELS,
            modality=modality,
            metadata={},
        )
        for _ in range(observations)
        for modality in MODALITIES
    )


def test_run_orchestrates_pipeline_and_returns_detached_result(
    specification: ExperimentSpecification,
) -> None:
    builder = RecordingBuilder()
    model = RecordingModel()
    training = outputs(3)
    evaluation = outputs(2)
    targets = ("clean", "defective", "clean")
    runner = ExperimentRunner(specification, builder, model)

    result = runner.run(training, targets, evaluation)

    assert isinstance(result, ExperimentRunResult)
    assert result.experiment_id == "stacking-8.5"
    assert result.class_labels == LABELS
    assert result.predictions == ("clean", "defective")
    assert result.probabilities == ((0.8, 0.2), (0.1, 0.9))
    assert result.training_observation_count == 3
    assert result.evaluation_observation_count == 2
    assert builder.calls == [training, evaluation, evaluation]
    assert (
        len(model.fit_calls)
        == len(model.predict_calls)
        == len(model.proba_calls)
        == 1
    )
    assert model.fit_calls[0][1] is targets

    model.predictions[0] = "changed"
    model.probabilities[0][0] = 0.0
    assert result.predictions == ("clean", "defective")
    assert result.probabilities == ((0.8, 0.2), (0.1, 0.9))


@pytest.mark.parametrize("training,evaluation", [((), outputs()), (outputs(), ())])
def test_run_rejects_empty_inputs(
    specification: ExperimentSpecification,
    training: tuple[PredictionOutput, ...],
    evaluation: tuple[PredictionOutput, ...],
) -> None:
    runner = ExperimentRunner(specification, RecordingBuilder(), RecordingModel())
    with pytest.raises(ValueError, match="must not be empty"):
        runner.run(training, (), evaluation)


@pytest.mark.parametrize("argument", ["training", "evaluation"])
def test_run_rejects_incomplete_modality_bundles(
    specification: ExperimentSpecification, argument: str
) -> None:
    runner = ExperimentRunner(specification, RecordingBuilder(), RecordingModel())
    incomplete = outputs()[:-1]
    training = incomplete if argument == "training" else outputs()
    evaluation = incomplete if argument == "evaluation" else outputs()
    with pytest.raises(ValueError, match="incomplete modality bundle"):
        runner.run(training, (), evaluation)


def test_run_rejects_incompatible_label_order(
    specification: ExperimentSpecification,
) -> None:
    invalid = list(outputs())
    invalid[0] = PredictionOutput((0.2, 0.8), LABELS[::-1], "code", {})
    runner = ExperimentRunner(specification, RecordingBuilder(), RecordingModel())
    with pytest.raises(ValueError, match="class-label order"):
        runner.run(tuple(invalid), (), outputs())


def test_run_rejects_unknown_modalities(
    specification: ExperimentSpecification,
) -> None:
    invalid = list(outputs())
    invalid[0] = PredictionOutput((0.2, 0.8), LABELS, "unknown", {})
    runner = ExperimentRunner(specification, RecordingBuilder(), RecordingModel())
    with pytest.raises(ValueError, match="modality"):
        runner.run(tuple(invalid), (), outputs())


@pytest.mark.parametrize("dependency", ["specification", "builder", "model"])
def test_constructor_rejects_none_dependencies(
    specification: ExperimentSpecification, dependency: str
) -> None:
    arguments = [specification, RecordingBuilder(), RecordingModel()]
    arguments[{"specification": 0, "builder": 1, "model": 2}[dependency]] = None
    with pytest.raises(ValueError, match="must not be None"):
        ExperimentRunner(*arguments)  # type: ignore[arg-type]


def test_constructor_validates_builder_metadata(
    specification: ExperimentSpecification,
) -> None:
    with pytest.raises(ValueError, match="modalities"):
        ExperimentRunner(
            specification,
            StackingFeatureBuilder(("audio",), LABELS),
            RecordingModel(),
        )
    with pytest.raises(ValueError, match="class labels"):
        ExperimentRunner(
            specification,
            StackingFeatureBuilder(MODALITIES, LABELS[::-1]),
            RecordingModel(),
        )


def test_result_is_immutable_and_to_dict_is_detached_and_deterministic() -> None:
    predictions = ["clean"]
    probabilities = [[0.8, 0.2]]
    result = ExperimentRunResult("id", LABELS, predictions, probabilities, 2, 1)
    expected = {
        "experiment_id": "id",
        "class_labels": ["clean", "defective"],
        "predictions": ["clean"],
        "probabilities": [[0.8, 0.2]],
        "training_observation_count": 2,
        "evaluation_observation_count": 1,
    }

    predictions[0] = "defective"
    probabilities[0][0] = 0.0
    first = result.to_dict()
    first["class_labels"].append("other")  # type: ignore[union-attr]
    first["probabilities"][0][0] = 0.0  # type: ignore[index]

    assert result.to_dict() == expected
    with pytest.raises(FrozenInstanceError):
        result.experiment_id = "changed"  # type: ignore[misc]


def test_runner_does_not_modify_dependencies(
    specification: ExperimentSpecification,
) -> None:
    builder = RecordingBuilder()
    model = RecordingModel()
    runner = ExperimentRunner(specification, builder, model)

    assert runner.specification is specification
    assert builder.metadata.input_modalities == MODALITIES
    assert builder.metadata.feature_names == (
        "code__clean",
        "code__defective",
        "text__clean",
        "text__defective",
    )
    assert model.fit_calls == model.predict_calls == model.proba_calls == []
