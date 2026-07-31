"""Tests for reproducible binary experiment evaluation."""

from dataclasses import FrozenInstanceError

import pytest

from experimentation.evaluation import ExperimentEvaluationResult, ExperimentEvaluator
from experimentation.runner import ExperimentRunResult


def make_result(
    *,
    labels: tuple[object, object] = ("negative", "positive"),
    predictions: tuple[object, ...] = ("negative", "positive", "positive", "negative"),
    probabilities: tuple[tuple[float, float], ...] = (
        (0.9, 0.1),
        (0.2, 0.8),
        (0.4, 0.6),
        (0.7, 0.3),
    ),
) -> ExperimentRunResult:
    return ExperimentRunResult(
        "experiment-8.6", labels, predictions, probabilities, 8, len(predictions)
    )


def test_known_binary_metrics_and_counts() -> None:
    evaluation = ExperimentEvaluator(positive_label="positive").evaluate(
        make_result(), ("negative", "positive", "negative", "positive")
    )

    assert (evaluation.true_negative, evaluation.false_positive) == (1, 1)
    assert (evaluation.false_negative, evaluation.true_positive) == (1, 1)
    assert evaluation.observation_count == 4
    assert evaluation.positive_count == 2
    assert evaluation.positive_rate == 0.5
    assert evaluation.accuracy == 0.5
    assert evaluation.precision == 0.5
    assert evaluation.recall == 0.5
    assert evaluation.f1 == 0.5
    assert evaluation.mcc == 0.0
    assert evaluation.roc_auc == pytest.approx(0.75)
    assert evaluation.pr_auc == pytest.approx(5 / 6)
    assert evaluation.brier_score == pytest.approx(0.225)


@pytest.mark.parametrize(
    "labels,positive,probabilities",
    [
        (("positive", "negative"), "positive", ((0.9, 0.1), (0.2, 0.8))),
        (("negative", "positive"), "positive", ((0.1, 0.9), (0.8, 0.2))),
    ],
)
def test_positive_probability_column_and_label_order_are_preserved(
    labels: tuple[str, str],
    positive: str,
    probabilities: tuple[tuple[float, float], ...],
) -> None:
    result = make_result(
        labels=labels,
        predictions=(positive, labels[1] if labels[0] == positive else labels[0]),
        probabilities=probabilities,
    )
    evaluation = ExperimentEvaluator(positive_label=positive).evaluate(
        result, (positive, labels[1] if labels[0] == positive else labels[0])
    )
    assert evaluation.class_labels == labels
    assert evaluation.roc_auc == 1.0


def test_delegated_prediction_order_is_used_without_probability_thresholding() -> None:
    result = make_result(
        predictions=("positive", "negative"),
        probabilities=((0.99, 0.01), (0.01, 0.99)),
    )
    evaluation = ExperimentEvaluator(positive_label="positive").evaluate(
        result, ("positive", "negative")
    )
    assert evaluation.true_positive == 1
    assert evaluation.true_negative == 1


def test_mismatched_target_count_is_rejected() -> None:
    with pytest.raises(ValueError, match="target count"):
        ExperimentEvaluator(positive_label="positive").evaluate(
            make_result(), ("negative", "positive")
        )


def test_unknown_target_and_prediction_labels_are_rejected() -> None:
    evaluator = ExperimentEvaluator(positive_label="positive")
    with pytest.raises(ValueError, match="target"):
        evaluator.evaluate(
            make_result(), ("unknown", "positive", "negative", "positive")
        )
    with pytest.raises(ValueError, match="prediction"):
        evaluator.evaluate(
            make_result(predictions=("unknown", "positive", "negative", "positive")),
            ("negative", "positive", "negative", "positive"),
        )


@pytest.mark.parametrize(
    "probabilities,message",
    [
        (((1.0,), (0.2, 0.8)), "one value per class label"),
        (((-0.1, 1.1), (0.2, 0.8)), "range"),
        (((0.7, 0.4), (0.2, 0.8)), "sum to one"),
    ],
)
def test_invalid_probabilities_are_rejected(
    probabilities: tuple[tuple[float, ...], ...], message: str
) -> None:
    result = make_result(
        predictions=("negative", "positive"),
        probabilities=((0.8, 0.2), (0.2, 0.8)),
    )
    object.__setattr__(result, "probabilities", probabilities)
    with pytest.raises(ValueError, match=message):
        ExperimentEvaluator(positive_label="positive").evaluate(
            result, ("negative", "positive")
        )


def test_one_class_targets_are_rejected() -> None:
    with pytest.raises(ValueError, match="both target classes"):
        ExperimentEvaluator(positive_label="positive").evaluate(
            make_result(), ("positive",) * 4
        )


def test_none_result_is_rejected() -> None:
    with pytest.raises(ValueError, match="result must not be None"):
        ExperimentEvaluator(positive_label="positive").evaluate(
            None,
            ("positive",),  # type: ignore[arg-type]
        )


def test_result_is_immutable_and_to_dict_is_detached_and_deterministic() -> None:
    evaluation = ExperimentEvaluator(positive_label="positive").evaluate(
        make_result(), ("negative", "positive", "negative", "positive")
    )
    first = evaluation.to_dict()
    first["class_labels"].append("changed")  # type: ignore[union-attr]
    assert evaluation.to_dict() == evaluation.to_dict()
    assert evaluation.to_dict()["class_labels"] == ["negative", "positive"]
    with pytest.raises(FrozenInstanceError):
        evaluation.accuracy = 0.0  # type: ignore[misc]


def test_evaluation_does_not_modify_result_or_targets() -> None:
    result = make_result()
    targets = ["negative", "positive", "negative", "positive"]
    before_result = result.to_dict()
    before_targets = list(targets)
    ExperimentEvaluator(positive_label="positive").evaluate(result, targets)
    assert result.to_dict() == before_result
    assert targets == before_targets


def test_result_constructor_validation() -> None:
    with pytest.raises(ValueError, match="exactly two distinct"):
        ExperimentEvaluationResult(
            "id",
            "yes",
            ("yes", "yes"),
            0,
            0,
            0.0,
            0,
            0,
            0,
            0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
        )
