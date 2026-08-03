"""Tests for the deterministic counterfactual explanation engine."""

from dataclasses import FrozenInstanceError
from types import MappingProxyType

import pytest

import explainability.counterfactual as module
from explainability.counterfactual import (
    CounterfactualChange,
    CounterfactualExplainer,
    CounterfactualExplanationResult,
)
from models.logistic_regression_adapter import (
    LogisticRegressionConfiguration,
    PreparedLogisticRegressionModel,
)
from models.random_forest_adapter import (
    PreparedRandomForestModel,
    RandomForestConfiguration,
)


def logistic_model(
    coefficients: object = ((2.0, -1.0, 0.5),),
    intercepts: object = (0.0,),
    metadata: object = None,
) -> PreparedLogisticRegressionModel:
    return PreparedLogisticRegressionModel(
        "data",
        "v1",
        ("a", "b", "c"),
        "defect",
        (0, 1),
        coefficients,  # type: ignore[arg-type]
        intercepts,  # type: ignore[arg-type]
        (3,),
        LogisticRegressionConfiguration(),
        {"nested": {"values": [1, 2]}} if metadata is None else metadata,
    )


def forest_model() -> PreparedRandomForestModel:
    return PreparedRandomForestModel(
        "data",
        "v1",
        ("a", "b", "c"),
        "defect",
        (0, 1),
        (0.2, 0.6, 0.2),
        (3, 5),
        (1, 2),
        RandomForestConfiguration(n_estimators=2),
    )


def result_values() -> dict[str, object]:
    return {
        "dataset_name": "data",
        "dataset_version": "v1",
        "model_name": "logistic-regression",
        "target_name": "defect",
        "class_labels": (0, 1),
        "observation_identifier": {"commit": ["abc"]},
        "feature_names": ("a", "b"),
        "original_feature_values": (1.0, 1.0),
        "counterfactual_feature_values": (-0.5, 1.0),
        "original_prediction": 1,
        "counterfactual_prediction": 0,
        "original_score": 2.0,
        "counterfactual_score": -1e-12,
        "changes": (CounterfactualChange("a", 1.0, -0.5, -1.5, 1.5),),
        "generation_method": "minimal-single-feature-linear-boundary",
        "metadata": {"nested": [1, 2]},
    }


def test_positive_prediction_is_flipped_with_smallest_feature_change() -> None:
    result = CounterfactualExplainer().explain(logistic_model(), "abc", (1.0, 0.0, 0.0))
    assert result.original_prediction == 1
    assert result.counterfactual_prediction == 0
    assert result.counterfactual_score < 0.0
    assert result.changes[0].feature_name == "a"
    assert result.changed_feature_count == 1
    assert result.counterfactual_feature_values[1:] == (0.0, 0.0)
    assert result.model_name == "logistic-regression"
    assert result.generation_method == "minimal-single-feature-linear-boundary"


def test_negative_prediction_is_flipped_to_positive_class() -> None:
    result = CounterfactualExplainer().explain(
        logistic_model(intercepts=(-3.0,)), "abc", (0.0, 0.0, 0.0)
    )
    assert (result.original_prediction, result.counterfactual_prediction) == (0, 1)
    assert result.counterfactual_score >= 0.0
    assert result.changes[0].feature_name == "a"


def test_equal_candidate_changes_use_model_feature_order() -> None:
    result = CounterfactualExplainer().explain(
        logistic_model(coefficients=((2.0, -2.0, 0.5),)),
        "abc",
        (1.0, 0.0, 0.0),
    )
    assert result.changes[0].feature_name == "a"


def test_results_are_reproducible_and_inputs_are_detached() -> None:
    metadata = {"nested": {"values": [1, 2]}}
    model = logistic_model(metadata=metadata)
    values = [1.0, 2.0, 3.0]
    first = CounterfactualExplainer().explain(model, {"id": [1]}, values)
    values.append(4.0)
    metadata["nested"]["values"].append(3)
    second = CounterfactualExplainer().explain(model, {"id": [1]}, (1, 2, 3))
    assert first == second


def test_contracts_and_nested_metadata_are_immutable() -> None:
    result = CounterfactualExplanationResult(**result_values())
    with pytest.raises(FrozenInstanceError):
        result.model_name = "changed"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        result.changes[0].delta = 0.0  # type: ignore[misc]
    with pytest.raises(TypeError):
        result.metadata["x"] = 1  # type: ignore[index]
    assert isinstance(result.metadata, MappingProxyType)


def test_to_dict_is_fully_detached() -> None:
    result = CounterfactualExplanationResult(**result_values())
    detached = result.to_dict()
    expected = result.to_dict()
    detached["feature_names"].append("changed")  # type: ignore[union-attr]
    detached["metadata"]["nested"].append(3)  # type: ignore[index,union-attr]
    detached["observation_identifier"]["commit"].append("x")  # type: ignore[index,union-attr]
    assert result.to_dict() == expected


def test_generic_result_accepts_other_model_and_generation_method() -> None:
    result = CounterfactualExplanationResult(
        **(
            result_values()
            | {
                "model_name": "future-model",
                "generation_method": "model-aware-search",
                "original_score": 0.8,
                "counterfactual_score": 0.2,
            }
        )
    )
    assert result.model_name == "future-model"
    assert result.generation_method == "model-aware-search"


def test_forest_failure_explains_model_specific_requirement() -> None:
    message = (
        "generic counterfactual result contract supports future model families.*"
        "no faithful PreparedRandomForestModel counterfactual generator.*"
        "model-aware tree information or an appropriate tree counterfactual method"
    )
    with pytest.raises(NotImplementedError, match=message):
        CounterfactualExplainer().explain(forest_model(), "abc", (1, 2, 3))


@pytest.mark.parametrize(
    "identifier,values",
    [
        (None, (1, 2, 3)),
        ("x", (1, 2)),
        ("x", (1, float("nan"), 3)),
        ("x", (1, float("inf"), 3)),
        ("x", (1, True, 3)),
        ("x", "123"),
    ],
)
def test_invalid_explain_inputs_are_rejected(
    identifier: object, values: object
) -> None:
    with pytest.raises((TypeError, ValueError)):
        CounterfactualExplainer().explain(logistic_model(), identifier, values)  # type: ignore[arg-type]


def test_zero_coefficient_model_cannot_produce_a_counterfactual() -> None:
    with pytest.raises(ValueError, match="non-zero coefficient"):
        CounterfactualExplainer().explain(
            logistic_model(coefficients=((0.0, 0.0, 0.0),)), "x", (1, 2, 3)
        )


def test_unsupported_model_is_rejected() -> None:
    """A generic result contract does not imply a generic executable strategy."""
    with pytest.raises(TypeError, match="PreparedLogisticRegressionModel"):
        CounterfactualExplainer().explain(object(), "x", (1,))  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "changes",
    [
        {"feature_name": ""},
        {"original_value": float("nan")},
        {"counterfactual_value": float("inf")},
        {"delta": 0.0},
        {"delta": 2.0},
        {"absolute_delta": -1.0},
        {"absolute_delta": 2.0},
    ],
)
def test_invalid_change_values_are_rejected(changes: dict[str, object]) -> None:
    values = {
        "feature_name": "a",
        "original_value": 1.0,
        "counterfactual_value": 2.0,
        "delta": 1.0,
        "absolute_delta": 1.0,
    }
    with pytest.raises((TypeError, ValueError)):
        CounterfactualChange(**(values | changes))  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "changes",
    [
        {"model_name": ""},
        {"generation_method": ""},
        {"observation_identifier": None},
        {"feature_names": ("a", "a")},
        {"original_feature_values": (1.0,)},
        {"counterfactual_feature_values": (1.0, 1.0)},
        {"counterfactual_prediction": 1},
        {"original_score": float("nan")},
        {"changes": ()},
        {"metadata": []},
    ],
)
def test_invalid_result_invariants_are_rejected(changes: dict[str, object]) -> None:
    with pytest.raises((TypeError, ValueError)):
        CounterfactualExplanationResult(**(result_values() | changes))


def test_public_api_is_narrow_and_stable() -> None:
    assert module.__all__ == [
        "CounterfactualChange",
        "CounterfactualExplanationResult",
        "CounterfactualExplainer",
    ]
    explainer = CounterfactualExplainer()
    assert explainer.explainer_name == "counterfactual"
    assert not any(hasattr(explainer, name) for name in {"fit", "predict", "plot"})
