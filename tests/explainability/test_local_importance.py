"""Tests for deterministic local feature-importance contracts."""

from dataclasses import FrozenInstanceError
from types import MappingProxyType

import pytest

import explainability.local_importance as module
from explainability.local_importance import (
    LocalFeatureAttribution,
    LocalFeatureImportanceExplainer,
    LocalFeatureImportanceResult,
)
from models.logistic_regression_adapter import (
    LogisticRegressionConfiguration,
    PreparedLogisticRegressionModel,
)
from models.random_forest_adapter import (
    PreparedRandomForestModel,
    RandomForestConfiguration,
)


def logistic_model(metadata: object = None) -> PreparedLogisticRegressionModel:
    return PreparedLogisticRegressionModel(
        "data",
        "v1",
        ("a", "b", "c"),
        "defect",
        (0, 1),
        ((2.0, -1.0, 0.5),),
        (0.0,),
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
        {"nested": [1, {"x": {2, 3}}]},
    )


def attribution(
    name: str, value: float, rank: int, raw: float, norm: float
) -> LocalFeatureAttribution:
    direction = "positive" if raw > 0 else "negative" if raw < 0 else "neutral"
    return LocalFeatureAttribution(name, value, rank, raw, abs(raw), norm, direction)


def result_values() -> dict[str, object]:
    return {
        "dataset_name": "data",
        "dataset_version": "v1",
        "model_name": "logistic-regression",
        "target_name": "defect",
        "class_labels": (0, 1),
        "observation_identifier": {"commit": ["abc"]},
        "feature_names": ("a", "b"),
        "attributions": (
            attribution("a", 1.0, 1, 2.0, 2 / 3),
            attribution("b", 1.0, 2, -1.0, 1 / 3),
        ),
        "attribution_method": "linear-logit-contribution",
        "normalization_method": "absolute-sum",
        "metadata": {"nested": [1, 2]},
    }


def test_logistic_attributions_are_local_signed_normalized_and_ranked() -> None:
    result = LocalFeatureImportanceExplainer().explain(
        logistic_model(), "abc", (1.0, 3.0, -2.0)
    )
    assert [item.feature_name for item in result.attributions] == ["b", "a", "c"]
    assert [item.raw_attribution for item in result.attributions] == [-3.0, 2.0, -1.0]
    assert [
        item.normalized_importance for item in result.attributions
    ] == pytest.approx([0.5, 1 / 3, 1 / 6])
    assert [item.direction for item in result.attributions] == [
        "negative",
        "positive",
        "negative",
    ]
    assert result.feature_count == 3
    assert result.attribution_method == "linear-logit-contribution"


def test_forest_is_rejected_when_snapshot_cannot_support_local_attribution() -> None:
    message = (
        "only global feature importances.*insufficient tree-path information.*"
        "TreeSHAP or equivalent model-aware adapter"
    )
    with pytest.raises(NotImplementedError, match=message):
        LocalFeatureImportanceExplainer().explain(forest_model(), 7, (-3.0, 1.0, 3.0))


def test_logistic_methodology_is_explicitly_scoped_to_the_linear_logit() -> None:
    documentation = LocalFeatureImportanceExplainer.__doc__ or ""
    assert "linear score (logit)" in documentation
    assert "not a direct\n    contribution to predicted probability" in documentation
    assert "causal effect" in documentation


def test_all_zero_values_preserve_model_feature_order() -> None:
    result = LocalFeatureImportanceExplainer().explain(logistic_model(), "x", (0, 0, 0))
    assert (
        tuple(item.feature_name for item in result.attributions) == result.feature_names
    )
    assert all(item.normalized_importance == 0 for item in result.attributions)
    assert all(item.direction == "neutral" for item in result.attributions)


def test_equal_nonzero_contributions_preserve_model_feature_order() -> None:
    result = LocalFeatureImportanceExplainer().explain(
        logistic_model(), "x", (1.0, -2.0, 4.0)
    )
    assert tuple(item.feature_name for item in result.attributions) == ("a", "b", "c")
    assert tuple(item.raw_attribution for item in result.attributions) == (
        2.0,
        2.0,
        2.0,
    )


def test_outputs_are_reproducible_and_inputs_are_not_mutated() -> None:
    metadata = {"nested": {"values": [1, 2]}}
    model = logistic_model(metadata)
    values = [1.0, 2.0, 3.0]
    before = model.to_dict()
    first = LocalFeatureImportanceExplainer().explain(model, {"commit": ["a"]}, values)
    values.append(4.0)
    metadata["nested"]["values"].append(3)
    assert model.to_dict() == before
    assert first == LocalFeatureImportanceExplainer().explain(
        model, {"commit": ["a"]}, (1, 2, 3)
    )


def test_contracts_and_recursive_metadata_are_immutable() -> None:
    result = LocalFeatureImportanceResult(**result_values())
    with pytest.raises(FrozenInstanceError):
        result.model_name = "changed"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        result.attributions[0].rank = 3  # type: ignore[misc]
    with pytest.raises(TypeError):
        result.metadata["x"] = 1  # type: ignore[index]
    assert isinstance(result.metadata, MappingProxyType)


def test_to_dict_is_detached_and_uses_mutable_standard_containers() -> None:
    result = LocalFeatureImportanceResult(**result_values())
    first = result.to_dict()
    expected = result.to_dict()
    first["feature_names"].append("changed")  # type: ignore[union-attr]
    first["metadata"]["nested"].append(3)  # type: ignore[index,union-attr]
    first["observation_identifier"]["commit"].append("changed")  # type: ignore[index,union-attr]
    assert result.to_dict() == expected


@pytest.mark.parametrize(
    "identifier,values",
    [
        (None, (1, 2, 3)),
        ("x", (1, 2)),
        ("x", (1, float("nan"), 3)),
        ("x", (1, True, 3)),
    ],
)
def test_invalid_explain_inputs_are_rejected(
    identifier: object, values: object
) -> None:
    with pytest.raises((TypeError, ValueError)):
        LocalFeatureImportanceExplainer().explain(logistic_model(), identifier, values)  # type: ignore[arg-type]


def test_unsupported_model_is_rejected() -> None:
    with pytest.raises(TypeError, match="PreparedLogisticRegressionModel"):
        LocalFeatureImportanceExplainer().explain(object(), "x", (1,))  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "changes",
    [
        {"rank": True},
        {"feature_value": float("inf")},
        {"raw_attribution": True},
        {"absolute_attribution": 2.0},
        {"normalized_importance": 2.0},
        {"direction": "neutral"},
        {"feature_name": ""},
    ],
)
def test_invalid_attribution_values_are_rejected(changes: dict[str, object]) -> None:
    values = {
        "feature_name": "a",
        "feature_value": 1.0,
        "rank": 1,
        "raw_attribution": 1.0,
        "absolute_attribution": 1.0,
        "normalized_importance": 1.0,
        "direction": "positive",
    }
    with pytest.raises((TypeError, ValueError)):
        LocalFeatureAttribution(**(values | changes))


@pytest.mark.parametrize(
    "changes",
    [
        {"model_name": "other"},
        {"observation_identifier": None},
        {"feature_names": ("a", "a")},
        {"normalization_method": "sum"},
        {"attribution_method": "unsupported-local-method"},
        {"attributions": ()},
        {"metadata": []},
    ],
)
def test_invalid_result_invariants_are_rejected(changes: dict[str, object]) -> None:
    with pytest.raises((TypeError, ValueError)):
        LocalFeatureImportanceResult(**(result_values() | changes))


def test_public_api_is_narrow_and_stable() -> None:
    assert module.__all__ == [
        "LocalFeatureAttribution",
        "LocalFeatureImportanceResult",
        "LocalFeatureImportanceExplainer",
    ]
    explainer = LocalFeatureImportanceExplainer()
    assert explainer.explainer_name == "local-feature-importance"
    forbidden = {"fit", "predict", "plot", "save", "write"}
    assert not any(hasattr(explainer, name) for name in forbidden)
    assert "importance-times-absolute-value" not in vars(module).values()
    assert "importance-times-absolute-value" not in result_values().values()
