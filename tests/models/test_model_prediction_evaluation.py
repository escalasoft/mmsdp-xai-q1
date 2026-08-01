"""Tests for reproducible model-prediction evaluation."""

from dataclasses import FrozenInstanceError
from types import MappingProxyType

import pytest

from experimentation.evaluation import ExperimentEvaluationResult
from models.evaluation import ModelEvaluationResult, ModelPredictionEvaluator
from models.prediction import ModelPredictionResult


def make_prediction(
    *,
    labels: tuple[object, object] = ("negative", "positive"),
    predictions: tuple[object, ...] = (
        "negative",
        "positive",
        "positive",
        "negative",
    ),
    probabilities: tuple[tuple[float, float], ...] = (
        (0.9, 0.1),
        (0.2, 0.8),
        (0.4, 0.6),
        (0.7, 0.3),
    ),
    metadata: dict[str, object] | None = None,
) -> ModelPredictionResult:
    return ModelPredictionResult(
        dataset_name="dataset",
        dataset_version="1.0",
        partition_name="test",
        model_name="classifier",
        identifiers=tuple(range(len(predictions))),
        class_labels=labels,
        predictions=predictions,
        probabilities=probabilities,
        observation_count=len(predictions),
        metadata=metadata or {"source": {"tags": ["stable"]}},
    )


def evaluate() -> ModelEvaluationResult:
    return ModelPredictionEvaluator(positive_label="positive").evaluate(
        make_prediction(), ("negative", "positive", "negative", "positive")
    )


def test_known_binary_metrics_counts_and_context() -> None:
    result = evaluate()

    assert (result.true_negative, result.false_positive) == (1, 1)
    assert (result.false_negative, result.true_positive) == (1, 1)
    assert (result.observation_count, result.positive_count) == (4, 2)
    assert result.positive_rate == 0.5
    assert (result.accuracy, result.precision, result.recall, result.f1) == (
        0.5,
        0.5,
        0.5,
        0.5,
    )
    assert result.mcc == 0.0
    assert result.roc_auc == pytest.approx(0.75)
    assert result.pr_auc == pytest.approx(5 / 6)
    assert result.brier_score == pytest.approx(0.225)
    assert (
        result.dataset_name,
        result.dataset_version,
        result.partition_name,
        result.model_name,
    ) == ("dataset", "1.0", "test", "classifier")
    assert result.class_labels == ("negative", "positive")


@pytest.mark.parametrize(
    "labels,probabilities",
    [
        (("positive", "negative"), ((0.9, 0.1), (0.2, 0.8))),
        (("negative", "positive"), ((0.1, 0.9), (0.8, 0.2))),
    ],
)
def test_positive_probability_column_tracks_class_label_order(
    labels: tuple[str, str], probabilities: tuple[tuple[float, float], ...]
) -> None:
    prediction = make_prediction(
        labels=labels,
        predictions=("positive", "negative"),
        probabilities=probabilities,
    )
    result = ModelPredictionEvaluator(positive_label="positive").evaluate(
        prediction, ("positive", "negative")
    )
    assert result.class_labels == labels
    assert result.roc_auc == 1.0
    assert result.brier_score == pytest.approx(0.025)


def test_repeated_evaluation_is_structurally_equal_and_non_mutating() -> None:
    prediction = make_prediction()
    targets = ["negative", "positive", "negative", "positive"]
    prediction_before = prediction.to_dict()
    targets_before = list(targets)
    evaluator = ModelPredictionEvaluator(positive_label="positive")

    assert evaluator.evaluate(prediction, targets) == evaluator.evaluate(
        prediction, targets
    )
    assert prediction.to_dict() == prediction_before
    assert targets == targets_before


def test_result_and_nested_metadata_are_immutable_and_detached() -> None:
    metadata = {"source": {"tags": ["stable"], "groups": {"a", "b"}}}
    prediction = make_prediction(metadata=metadata)
    result = ModelPredictionEvaluator(positive_label="positive").evaluate(
        prediction, ("negative", "positive", "negative", "positive")
    )
    metadata["source"]["tags"].append("changed")  # type: ignore[index,union-attr]

    assert isinstance(result.metadata, MappingProxyType)
    assert result.metadata["source"]["tags"] == ("stable",)  # type: ignore[index]
    with pytest.raises(FrozenInstanceError):
        result.accuracy = 0.0  # type: ignore[misc]
    with pytest.raises(TypeError):
        result.metadata["new"] = "value"  # type: ignore[index]


def test_to_dict_is_deterministic_detached_and_mutable() -> None:
    result = evaluate()
    first = result.to_dict()
    second = result.to_dict()
    assert first == second
    assert first is not second
    first["class_labels"].append("changed")  # type: ignore[union-attr]
    first["metadata"]["source"]["tags"].append("changed")  # type: ignore[index]
    assert result.to_dict() == second


@pytest.mark.parametrize("bad_input", [None, object(), "prediction"])
def test_non_prediction_result_is_rejected(bad_input: object) -> None:
    with pytest.raises(TypeError, match="ModelPredictionResult"):
        ModelPredictionEvaluator(positive_label="positive").evaluate(
            bad_input,
            ("negative", "positive"),  # type: ignore[arg-type]
        )


@pytest.mark.parametrize("targets", [None, ()])
def test_none_and_empty_targets_are_rejected(targets: object) -> None:
    with pytest.raises(ValueError, match="targets"):
        ModelPredictionEvaluator(positive_label="positive").evaluate(
            make_prediction(),
            targets,  # type: ignore[arg-type]
        )


def test_target_count_and_unknown_labels_are_rejected() -> None:
    evaluator = ModelPredictionEvaluator(positive_label="positive")
    with pytest.raises(ValueError, match="target count"):
        evaluator.evaluate(make_prediction(), ("negative", "positive"))
    with pytest.raises(ValueError, match="every target"):
        evaluator.evaluate(
            make_prediction(), ("negative", "positive", "unknown", "positive")
        )


def test_invalid_positive_label_is_rejected_and_property_is_detached() -> None:
    label = ["positive"]
    evaluator = ModelPredictionEvaluator(positive_label=label)
    label.append("changed")
    assert evaluator.positive_label == ["positive"]
    detached = evaluator.positive_label
    detached.append("again")  # type: ignore[union-attr]
    assert evaluator.positive_label == ["positive"]
    with pytest.raises(ValueError, match="positive_label"):
        evaluator.evaluate(make_prediction(), ("negative",) * 4)


@pytest.mark.parametrize("labels", [("negative",), ("negative", "negative")])
def test_malformed_non_binary_or_duplicate_labels_are_rejected(
    labels: tuple[str, ...],
) -> None:
    prediction = make_prediction()
    object.__setattr__(prediction, "class_labels", labels)
    with pytest.raises(ValueError, match="exactly two distinct"):
        ModelPredictionEvaluator(positive_label="positive").evaluate(
            prediction, ("negative", "positive", "negative", "positive")
        )


def test_malformed_prediction_alignment_is_rejected_by_bridge() -> None:
    prediction = make_prediction()
    object.__setattr__(prediction, "predictions", ("negative",))
    with pytest.raises(ValueError, match="predictions count"):
        ModelPredictionEvaluator(positive_label="positive").evaluate(
            prediction, ("negative", "positive", "negative", "positive")
        )


def test_result_constructor_validates_names_counts_rates_and_metadata() -> None:
    values = evaluate().to_dict()
    with pytest.raises(ValueError, match="dataset_name"):
        ModelEvaluationResult(**(values | {"dataset_name": ""}))
    with pytest.raises(ValueError, match="sum of confusion-matrix"):
        ModelEvaluationResult(**(values | {"observation_count": 5}))
    with pytest.raises(ValueError, match="positive_count"):
        ModelEvaluationResult(**(values | {"positive_count": 3}))
    with pytest.raises(ValueError, match="positive_rate"):
        ModelEvaluationResult(**(values | {"positive_rate": 2.0}))
    with pytest.raises(ValueError, match="accuracy"):
        ModelEvaluationResult(**(values | {"accuracy": float("nan")}))
    with pytest.raises(TypeError, match="metadata"):
        ModelEvaluationResult(**(values | {"metadata": []}))


def test_metrics_are_delegated_to_experiment_evaluator(monkeypatch) -> None:
    import models.evaluation as module

    expected = ExperimentEvaluationResult(
        "delegated",
        "positive",
        ("negative", "positive"),
        4,
        2,
        0.5,
        2,
        0,
        0,
        2,
        0.91,
        0.92,
        0.93,
        0.94,
        0.95,
        0.96,
        0.97,
        0.08,
    )

    class SpyEvaluator:
        called = False

        def __init__(self, *, positive_label: object) -> None:
            assert positive_label == "positive"

        def evaluate(self, result, targets):
            SpyEvaluator.called = True
            assert result.class_labels == ("negative", "positive")
            assert tuple(targets) == ("negative", "positive", "negative", "positive")
            return expected

    monkeypatch.setattr(module, "ExperimentEvaluator", SpyEvaluator)
    result = module.ModelPredictionEvaluator(positive_label="positive").evaluate(
        make_prediction(), ("negative", "positive", "negative", "positive")
    )
    assert SpyEvaluator.called
    assert result.accuracy == 0.91
    assert result.brier_score == 0.08


def test_public_api_and_evaluator_surface_are_narrow() -> None:
    from models import evaluation as module

    assert module.__all__ == ["ModelEvaluationResult", "ModelPredictionEvaluator"]
    assert ModelPredictionEvaluator.evaluator_name == "model-prediction-evaluator"
    evaluator = ModelPredictionEvaluator(positive_label="positive")
    for name in ("train", "fit", "predict", "predict_proba"):
        assert not hasattr(evaluator, name)
