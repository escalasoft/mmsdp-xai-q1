"""Tests for deterministic global feature-importance contracts."""

from dataclasses import FrozenInstanceError
from types import MappingProxyType

import pytest

import explainability.global_importance as module
from explainability.global_importance import (
    GlobalFeatureAttribution,
    GlobalFeatureImportanceExplainer,
    GlobalFeatureImportanceResult,
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
    coefficients: tuple[tuple[float, ...], ...] = ((2.0, -1.0, 0.0),),
    feature_names: tuple[str, ...] = ("complexity", "churn", "age"),
    metadata: object = None,
) -> PreparedLogisticRegressionModel:
    return PreparedLogisticRegressionModel(
        dataset_name="project-metrics",
        dataset_version="v1",
        feature_names=feature_names,
        target_name="defect",
        class_labels=(0, 1),
        coefficients=coefficients,
        intercepts=(0.25,) * len(coefficients),
        iteration_counts=(4,),
        configuration=LogisticRegressionConfiguration(),
        metadata={"nested": {"values": [1, 2]}} if metadata is None else metadata,
    )


def forest_model(
    importances: tuple[float, ...] = (0.2, 0.6, 0.2),
    feature_names: tuple[str, ...] = ("complexity", "churn", "age"),
    metadata: object = None,
) -> PreparedRandomForestModel:
    configuration = RandomForestConfiguration(n_estimators=2)
    return PreparedRandomForestModel(
        dataset_name="project-metrics",
        dataset_version="v1",
        feature_names=feature_names,
        target_name="defect",
        class_labels=(0, 1),
        feature_importances=importances,
        tree_node_counts=(3, 5),
        tree_max_depths=(1, 2),
        configuration=configuration,
        metadata={"nested": {"values": [1, 2]}} if metadata is None else metadata,
    )


def attribution(
    name: str,
    rank: int,
    raw: float,
    normalized: float,
    direction: str,
) -> GlobalFeatureAttribution:
    return GlobalFeatureAttribution(name, rank, raw, abs(raw), normalized, direction)


def result_values() -> dict[str, object]:
    return {
        "dataset_name": "data",
        "dataset_version": "v1",
        "model_name": "logistic-regression",
        "target_name": "target",
        "class_labels": (0, 1),
        "feature_names": ("a", "b"),
        "attributions": (
            attribution("a", 1, 2.0, 2 / 3, "positive"),
            attribution("b", 2, -1.0, 1 / 3, "negative"),
        ),
        "normalization_method": "absolute-sum",
        "metadata": {"nested": [1, {"x": {2, 3}}]},
    }


def test_known_logistic_coefficients_have_signed_normalized_attributions() -> None:
    explained = GlobalFeatureImportanceExplainer().explain(logistic_model())

    assert [item.feature_name for item in explained.attributions] == [
        "complexity",
        "churn",
        "age",
    ]
    assert [item.raw_importance for item in explained.attributions] == [2.0, -1.0, 0.0]
    assert [item.absolute_importance for item in explained.attributions] == [
        2.0,
        1.0,
        0.0,
    ]
    assert [
        item.normalized_importance for item in explained.attributions
    ] == pytest.approx([2 / 3, 1 / 3, 0.0])
    assert [item.direction for item in explained.attributions] == [
        "positive",
        "negative",
        "neutral",
    ]
    assert explained.model_name == "logistic-regression"
    assert explained.feature_count == 3


def test_known_forest_importances_are_renormalized_unsigned_and_ranked() -> None:
    explained = GlobalFeatureImportanceExplainer().explain(
        forest_model((2.0, 6.0, 2.0))
    )

    assert [item.feature_name for item in explained.attributions] == [
        "churn",
        "complexity",
        "age",
    ]
    assert [item.raw_importance for item in explained.attributions] == [6.0, 2.0, 2.0]
    assert [
        item.normalized_importance for item in explained.attributions
    ] == pytest.approx([0.6, 0.2, 0.2])
    assert all(item.direction == "unsigned" for item in explained.attributions)
    assert sum(
        item.normalized_importance for item in explained.attributions
    ) == pytest.approx(1.0)


@pytest.mark.parametrize(
    "model", [logistic_model(((0.0, 0.0, 0.0),)), forest_model((0.0, 0.0, 0.0))]
)
def test_all_zero_models_preserve_source_order(model: object) -> None:
    explained = GlobalFeatureImportanceExplainer().explain(model)  # type: ignore[arg-type]
    assert (
        tuple(item.feature_name for item in explained.attributions)
        == model.feature_names
    )  # type: ignore[attr-defined]
    assert [item.rank for item in explained.attributions] == [1, 2, 3]
    assert all(item.normalized_importance == 0.0 for item in explained.attributions)


def test_repeated_and_independent_explainers_are_structurally_equal() -> None:
    model = logistic_model()
    first = GlobalFeatureImportanceExplainer().explain(model)
    assert first == GlobalFeatureImportanceExplainer().explain(model)
    assert first == GlobalFeatureImportanceExplainer().explain(logistic_model())


def test_explanation_does_not_mutate_model_or_nested_metadata() -> None:
    source = {"nested": {"values": [1, 2]}}
    model = logistic_model(metadata=source)
    before = model.to_dict()

    explained = GlobalFeatureImportanceExplainer().explain(model)
    source["nested"]["values"].append(3)  # type: ignore[index,union-attr]

    assert model.to_dict() == before
    assert explained.metadata["nested"]["values"] == (1, 2)  # type: ignore[index]


def test_result_attribution_and_nested_metadata_are_immutable() -> None:
    explained = GlobalFeatureImportanceExplainer().explain(logistic_model())
    with pytest.raises(FrozenInstanceError):
        explained.model_name = "changed"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        explained.attributions[0].rank = 99  # type: ignore[misc]
    with pytest.raises(TypeError):
        explained.metadata["new"] = 1  # type: ignore[index]
    assert isinstance(explained.metadata, MappingProxyType)
    assert isinstance(explained.metadata["nested"], MappingProxyType)


def test_to_dict_is_deterministic_detached_and_uses_mutable_containers() -> None:
    explained = GlobalFeatureImportanceResult(**result_values())
    first = explained.to_dict()
    second = explained.to_dict()
    assert first == second
    assert isinstance(first["class_labels"], list)
    assert isinstance(first["feature_names"], list)
    assert isinstance(first["attributions"], list)
    assert isinstance(first["metadata"], dict)
    first["feature_names"].append("changed")  # type: ignore[union-attr]
    first["metadata"]["nested"].append("changed")  # type: ignore[index,union-attr]
    assert explained.feature_names == ("a", "b")
    assert explained.to_dict() == second


def test_unsupported_model_is_rejected() -> None:
    with pytest.raises(TypeError, match="PreparedLogisticRegressionModel"):
        GlobalFeatureImportanceExplainer().explain(object())  # type: ignore[arg-type]


def malformed_logistic(**changes: object) -> PreparedLogisticRegressionModel:
    model = logistic_model()
    for name, value in changes.items():
        object.__setattr__(model, name, value)
    return model


def malformed_forest(**changes: object) -> PreparedRandomForestModel:
    model = forest_model()
    for name, value in changes.items():
        object.__setattr__(model, name, value)
    return model


@pytest.mark.parametrize(
    "model",
    [
        malformed_logistic(coefficients=((1.0,), (2.0,))),
        malformed_logistic(coefficients=((1.0, 2.0),)),
        malformed_logistic(coefficients=((1.0, float("nan"), 2.0),)),
        malformed_forest(feature_importances=(0.5, 0.5)),
        malformed_forest(feature_importances=(0.5, -0.1, 0.6)),
        malformed_forest(feature_importances=(0.5, float("inf"), 0.5)),
    ],
)
def test_malformed_model_values_are_rejected(model: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        GlobalFeatureImportanceExplainer().explain(model)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "changes",
    [
        {"feature_names": ("a", "a")},
        {
            "attributions": (
                attribution("a", 1, 2.0, 2 / 3, "positive"),
                attribution("a", 2, 1.0, 1 / 3, "positive"),
            )
        },
        {
            "attributions": (
                attribution("a", 1, 2.0, 2 / 3, "positive"),
                attribution("b", 3, -1.0, 1 / 3, "negative"),
            )
        },
        {
            "attributions": (
                attribution("a", 1, 2.0, 0.5, "positive"),
                attribution("b", 2, -1.0, 0.5, "negative"),
            )
        },
        {
            "attributions": (
                attribution("b", 1, -1.0, 1 / 3, "negative"),
                attribution("a", 2, 2.0, 2 / 3, "positive"),
            )
        },
        {"model_name": "random-forest"},
    ],
)
def test_invalid_result_invariants_are_rejected(changes: dict[str, object]) -> None:
    with pytest.raises((TypeError, ValueError)):
        GlobalFeatureImportanceResult(**(result_values() | changes))


@pytest.mark.parametrize(
    "changes",
    [
        {"rank": True},
        {"raw_importance": True},
        {"absolute_importance": False},
        {"normalized_importance": True},
        {"absolute_importance": 2.0},
        {"normalized_importance": 2.0},
        {"direction": "neutral"},
        {"feature_name": ""},
    ],
)
def test_invalid_attribution_values_are_rejected(changes: dict[str, object]) -> None:
    values = {
        "feature_name": "a",
        "rank": 1,
        "raw_importance": 1.0,
        "absolute_importance": 1.0,
        "normalized_importance": 1.0,
        "direction": "positive",
    }
    with pytest.raises((TypeError, ValueError)):
        GlobalFeatureAttribution(**(values | changes))


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("dataset_name", ""),
        ("dataset_version", " "),
        ("model_name", "other"),
        ("target_name", 1),
        ("normalization_method", "sum"),
    ],
)
def test_invalid_result_names_are_rejected(name: str, value: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        GlobalFeatureImportanceResult(**(result_values() | {name: value}))


def test_public_api_and_explainer_surface_are_stable() -> None:
    assert module.__all__ == [
        "GlobalFeatureAttribution",
        "GlobalFeatureImportanceResult",
        "GlobalFeatureImportanceExplainer",
    ]
    explainer = GlobalFeatureImportanceExplainer()
    assert explainer.explainer_name == "global-feature-importance"
    forbidden = {
        "train",
        "fit",
        "predict",
        "predict_proba",
        "calibrate",
        "evaluate",
        "plot",
        "save",
        "write",
    }
    assert not any(hasattr(explainer, name) for name in forbidden)


def test_result_has_only_contract_behavior() -> None:
    public_callables = {
        name
        for name in dir(GlobalFeatureImportanceResult(**result_values()))
        if not name.startswith("_")
        and callable(getattr(GlobalFeatureImportanceResult(**result_values()), name))
    }
    assert public_callables == {"to_dict"}
