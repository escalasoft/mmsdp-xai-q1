"""Tests for deterministic model-explanation orchestration."""

from __future__ import annotations

from copy import deepcopy

import pytest

import explainability.explanation_runner as runner_module
from dataset.model_input import ModelPartitionInput, PreparedModelInput
from explainability.explanation_runner import (
    ModelExplanationResult,
    ModelExplanationRunner,
    ObservationExplanationRequest,
)
from models.logistic_regression_adapter import (
    LogisticRegressionConfiguration,
    PreparedLogisticRegressionModel,
)
from models.random_forest_adapter import (
    PreparedRandomForestModel,
    RandomForestConfiguration,
)


def _partition(name, identifiers, rows, targets=(0, 1)):
    return ModelPartitionInput(
        partition_name=name,
        identifiers=identifiers,
        X=rows,
        y=targets,
        feature_names=("age", "score"),
        metadata={"partition": name},
    )


def _prepared(metadata=None):
    return PreparedModelInput(
        dataset_name="changes",
        dataset_version="v1",
        train=_partition(
            "train",
            ({"commit": ["abc"], "project": "sample"}, "train-2"),
            ((1.0, 10.0), (2.0, 20.0)),
        ),
        validation=_partition(
            "validation", ("validation-1", "validation-2"), ((3.0, 30.0), (4.0, 40.0))
        ),
        test=_partition("test", ("test-1", "test-2"), ((5.0, 50.0), (6.0, 60.0))),
        feature_names=("age", "score"),
        target_name="defect",
        metadata={"source": {"versions": [1, 2]}} if metadata is None else metadata,
    )


def _logistic(**changes):
    values = {
        "dataset_name": "changes",
        "dataset_version": "v1",
        "feature_names": ("age", "score"),
        "target_name": "defect",
        "class_labels": (0, 1),
        "coefficients": ((0.5, -0.25),),
        "intercepts": (0.1,),
        "iteration_counts": (4,),
        "configuration": LogisticRegressionConfiguration(),
        "metadata": {"model": "snapshot"},
    }
    values.update(changes)
    return PreparedLogisticRegressionModel(**values)


def _forest(**changes):
    values = {
        "dataset_name": "changes",
        "dataset_version": "v1",
        "feature_names": ("age", "score"),
        "target_name": "defect",
        "class_labels": (0, 1),
        "feature_importances": (0.25, 0.75),
        "tree_node_counts": (3,),
        "tree_max_depths": (1,),
        "configuration": RandomForestConfiguration(n_estimators=1),
        "metadata": {"model": "snapshot"},
    }
    values.update(changes)
    return PreparedRandomForestModel(**values)


def _request(partition, identifier):
    return ObservationExplanationRequest(partition, identifier)


def test_logistic_run_without_requests_and_identity():
    result = ModelExplanationRunner().run(_logistic(), _prepared())

    assert result.model_name == "logistic-regression"
    assert result.dataset_name == "changes"
    assert result.dataset_version == "v1"
    assert result.target_name == "defect"
    assert result.class_labels == (0, 1)
    assert result.feature_names == ("age", "score")
    assert result.local_explanations == ()
    assert result.unsupported_local_requests == ()
    assert result.requested_observation_count == 0


def test_logistic_training_request_uses_complex_structural_identifier():
    identifier = {"project": "sample", "commit": ["abc"]}
    request = _request("train", identifier)
    result = ModelExplanationRunner().run(_logistic(), _prepared(), [request])

    assert result.requested_observations == (request,)
    assert result.local_explanations[0].observation_identifier == {
        "commit": ("abc",),
        "project": "sample",
    }
    values = {
        item.feature_name: item.feature_value
        for item in result.local_explanations[0].attributions
    }
    assert values == {"age": 1.0, "score": 10.0}


def test_validation_test_request_order_and_row_alignment():
    requests = (_request("test", "test-2"), _request("validation", "validation-1"))
    result = ModelExplanationRunner().run(_logistic(), _prepared(), requests)

    assert result.requested_observations == requests
    assert tuple(item.observation_identifier for item in result.local_explanations) == (
        "test-2",
        "validation-1",
    )
    assert tuple(
        next(a.feature_value for a in item.attributions if a.feature_name == "age")
        for item in result.local_explanations
    ) == (6.0, 3.0)


def test_same_identifier_across_partitions_is_rejected_with_traceability_message():
    requests = (
        _request("train", "shared"),
        _request("validation", "shared"),
    )

    with pytest.raises(ValueError, match="do not currently retain partition_name"):
        ModelExplanationRunner().run(_logistic(), _prepared(), requests)


def test_equivalent_nested_identifiers_across_partitions_are_rejected():
    requests = (
        _request("train", {"commit": ["abc"], "context": {"index": 1}}),
        _request("validation", {"context": {"index": 1}, "commit": ("abc",)}),
    )

    with pytest.raises(ValueError, match="globally unique"):
        ModelExplanationRunner().run(_forest(), _prepared(), requests)


def test_different_identifiers_across_partitions_remain_valid():
    requests = (
        _request("train", "train-2"),
        _request("validation", "validation-2"),
    )

    result = ModelExplanationRunner().run(_logistic(), _prepared(), requests)

    assert result.requested_observations == requests
    assert tuple(item.observation_identifier for item in result.local_explanations) == (
        "train-2",
        "validation-2",
    )


def test_explainer_invocation_counts_and_local_data_flow(monkeypatch):
    global_calls = []
    local_calls = []
    real_global = runner_module.GlobalFeatureImportanceExplainer
    real_local = runner_module.LocalFeatureImportanceExplainer

    class GlobalSpy:
        def explain(self, model):
            global_calls.append(model)
            return real_global().explain(model)

    class LocalSpy:
        def explain(self, model, identifier, feature_values):
            local_calls.append((model, identifier, feature_values))
            return real_local().explain(model, identifier, feature_values)

    monkeypatch.setattr(runner_module, "GlobalFeatureImportanceExplainer", GlobalSpy)
    monkeypatch.setattr(runner_module, "LocalFeatureImportanceExplainer", LocalSpy)
    prepared = _prepared()
    requests = (_request("train", "train-2"), _request("test", "test-1"))
    model = _logistic()
    ModelExplanationRunner().run(model, prepared, requests)

    assert global_calls == [model]
    assert local_calls == [
        (model, "train-2", (2.0, 20.0)),
        (model, "test-1", (5.0, 50.0)),
    ]
    assert all(prepared.train.y not in call for call in local_calls)


def test_random_forest_global_only_and_all_requests_unsupported(monkeypatch):
    class ForbiddenLocalExplainer:
        def __init__(self):
            raise AssertionError("local explainer must not be instantiated")

    monkeypatch.setattr(
        runner_module, "LocalFeatureImportanceExplainer", ForbiddenLocalExplainer
    )
    requests = (_request("train", "train-2"), _request("test", "test-1"))
    result = ModelExplanationRunner().run(_forest(), _prepared(), requests)

    assert result.model_name == "random-forest"
    assert result.global_explanation.model_name == "random-forest"
    assert result.local_explanations == ()
    assert result.unsupported_local_requests == requests
    assert result.unsupported_local_request_count == 2


def test_repeated_runs_and_independent_runners_are_equal():
    request = _request("validation", "validation-2")
    first = ModelExplanationRunner().run(_logistic(), _prepared(), (request,))
    second = ModelExplanationRunner().run(_logistic(), _prepared(), (request,))

    assert first == second
    assert first.to_dict() == second.to_dict()


def test_sources_and_nested_request_are_not_mutated():
    identifier = {"commit": ["abc"], "project": "sample"}
    identifier_before = deepcopy(identifier)
    request = _request("train", identifier)
    model = _logistic()
    prepared = _prepared()
    model_before = model.to_dict()
    prepared_before = prepared.to_dict()

    ModelExplanationRunner().run(model, prepared, [request])

    assert model.to_dict() == model_before
    assert prepared.to_dict() == prepared_before
    assert identifier == identifier_before


def test_result_metadata_is_immutable_and_to_dict_is_detached():
    result = ModelExplanationRunner().run(_logistic(), _prepared())
    with pytest.raises(TypeError):
        result.metadata["new"] = "value"
    with pytest.raises(TypeError):
        result.metadata["source"]["new"] = "value"

    first = result.to_dict()
    first["metadata"]["source"]["versions"].append(3)
    assert result.to_dict()["metadata"]["source"]["versions"] == [1, 2]
    assert result.to_dict() == result.to_dict()


@pytest.mark.parametrize("bad_model", [object(), None, "model"])
def test_invalid_model_is_rejected(bad_model):
    with pytest.raises(TypeError):
        ModelExplanationRunner().run(bad_model, _prepared())


def test_invalid_prepared_input_is_rejected():
    with pytest.raises(TypeError):
        ModelExplanationRunner().run(_logistic(), object())


@pytest.mark.parametrize("requests", ["request", b"request", {"request"}, 1])
def test_invalid_requests_container_is_rejected(requests):
    with pytest.raises(TypeError):
        ModelExplanationRunner().run(_logistic(), _prepared(), requests)


def test_non_request_and_duplicate_requests_are_rejected():
    runner = ModelExplanationRunner()
    with pytest.raises(TypeError):
        runner.run(_logistic(), _prepared(), [object()])
    request = _request("test", {"id": [1]})
    equivalent = _request("test", {"id": (1,)})
    with pytest.raises(ValueError):
        runner.run(_logistic(), _prepared(), [request, equivalent])


@pytest.mark.parametrize(
    ("partition", "identifier"),
    [("train", "missing"), ("validation", "test-1"), ("test", "train-2")],
)
def test_missing_or_wrong_partition_identifier_is_rejected(partition, identifier):
    with pytest.raises(ValueError):
        ModelExplanationRunner().run(
            _logistic(), _prepared(), [_request(partition, identifier)]
        )


@pytest.mark.parametrize(
    "model",
    [
        _logistic(dataset_name="other"),
        _logistic(dataset_version="v2"),
        _logistic(target_name="other"),
        _logistic(feature_names=("score", "age")),
    ],
)
def test_model_and_input_identity_mismatches_are_rejected(model):
    with pytest.raises(ValueError):
        ModelExplanationRunner().run(model, _prepared())


def test_result_constructor_rejects_mismatched_global_explanation():
    valid = ModelExplanationRunner().run(_logistic(), _prepared())
    with pytest.raises(ValueError):
        ModelExplanationResult(
            dataset_name="other",
            dataset_version=valid.dataset_version,
            model_name=valid.model_name,
            target_name=valid.target_name,
            class_labels=valid.class_labels,
            feature_names=valid.feature_names,
            global_explanation=valid.global_explanation,
        )


def test_result_constructor_rejects_cross_partition_identifier_ambiguity():
    valid = ModelExplanationRunner().run(_logistic(), _prepared())
    requests = (
        _request("train", {"id": [1]}),
        _request("validation", {"id": (1,)}),
    )

    with pytest.raises(ValueError, match="do not currently retain partition_name"):
        ModelExplanationResult(
            dataset_name=valid.dataset_name,
            dataset_version=valid.dataset_version,
            model_name=valid.model_name,
            target_name=valid.target_name,
            class_labels=valid.class_labels,
            feature_names=valid.feature_names,
            global_explanation=valid.global_explanation,
            requested_observations=requests,
        )


def test_result_constructor_rejects_mismatched_local_explanation():
    local_result = ModelExplanationRunner().run(
        _logistic(), _prepared(), [_request("test", "test-1")]
    )
    global_result = ModelExplanationRunner().run(_logistic(), _prepared())
    with pytest.raises(ValueError):
        ModelExplanationResult(
            dataset_name="changes",
            dataset_version="v1",
            model_name="logistic-regression",
            target_name="defect",
            class_labels=("no", "yes"),
            feature_names=("age", "score"),
            global_explanation=global_result.global_explanation,
            local_explanations=local_result.local_explanations,
            requested_observations=local_result.requested_observations,
        )


def test_result_rejects_unsupported_not_requested_and_overlap():
    valid = ModelExplanationRunner().run(
        _logistic(), _prepared(), [_request("test", "test-1")]
    )
    missing = _request("test", "test-2")
    with pytest.raises(ValueError):
        ModelExplanationResult(
            dataset_name=valid.dataset_name,
            dataset_version=valid.dataset_version,
            model_name=valid.model_name,
            target_name=valid.target_name,
            class_labels=valid.class_labels,
            feature_names=valid.feature_names,
            global_explanation=valid.global_explanation,
            local_explanations=valid.local_explanations,
            requested_observations=valid.requested_observations,
            unsupported_local_requests=(missing,),
        )
    with pytest.raises(ValueError):
        ModelExplanationResult(
            dataset_name=valid.dataset_name,
            dataset_version=valid.dataset_version,
            model_name=valid.model_name,
            target_name=valid.target_name,
            class_labels=valid.class_labels,
            feature_names=valid.feature_names,
            global_explanation=valid.global_explanation,
            local_explanations=valid.local_explanations,
            requested_observations=valid.requested_observations,
            unsupported_local_requests=valid.requested_observations,
        )


def test_model_specific_result_capability_rules():
    logistic = ModelExplanationRunner().run(
        _logistic(), _prepared(), [_request("test", "test-1")]
    )
    forest = ModelExplanationRunner().run(
        _forest(), _prepared(), [_request("test", "test-1")]
    )
    with pytest.raises(ValueError):
        ModelExplanationResult(
            dataset_name=logistic.dataset_name,
            dataset_version=logistic.dataset_version,
            model_name=logistic.model_name,
            target_name=logistic.target_name,
            class_labels=logistic.class_labels,
            feature_names=logistic.feature_names,
            global_explanation=logistic.global_explanation,
            requested_observations=logistic.requested_observations,
            unsupported_local_requests=logistic.requested_observations,
        )
    with pytest.raises(ValueError):
        ModelExplanationResult(
            dataset_name=forest.dataset_name,
            dataset_version=forest.dataset_version,
            model_name=forest.model_name,
            target_name=forest.target_name,
            class_labels=forest.class_labels,
            feature_names=forest.feature_names,
            global_explanation=forest.global_explanation,
            local_explanations=logistic.local_explanations,
            requested_observations=forest.requested_observations,
        )


def test_counts_and_runner_metadata_are_correct():
    result = ModelExplanationRunner().run(
        _logistic(),
        _prepared(),
        [_request("validation", "validation-1"), _request("test", "test-1")],
    )
    assert result.requested_observation_count == 2
    assert result.local_explanation_count == 2
    assert result.unsupported_local_request_count == 0
    assert result.metadata["runner"] == {
        "name": "model-explanation-runner",
        "requested_observation_count": 2,
        "local_explanation_count": 2,
        "unsupported_local_request_count": 0,
    }


def test_caller_metadata_and_collisions_are_preserved():
    caller = {
        "runner": {"caller": True},
        "explanation_runner": {"caller": "also"},
        "nested": [1, 2],
    }
    result = ModelExplanationRunner().run(_logistic(), _prepared(caller))
    assert result.metadata["runner"] == {"caller": True}
    assert result.metadata["explanation_runner"] == {"caller": "also"}
    assert result.metadata["explanation_runner_2"]["name"] == (
        "model-explanation-runner"
    )
    assert caller == {
        "runner": {"caller": True},
        "explanation_runner": {"caller": "also"},
        "nested": [1, 2],
    }


def test_public_api_runner_name_and_absent_behavioral_methods():
    assert runner_module.__all__ == [
        "ObservationExplanationRequest",
        "ModelExplanationResult",
        "ModelExplanationRunner",
    ]
    assert ModelExplanationRunner.runner_name == "model-explanation-runner"
    forbidden = {
        "train",
        "fit",
        "predict",
        "calibrate",
        "evaluate",
        "plot",
        "save",
        "write",
        "persistence",
        "explain",
    }
    assert forbidden.isdisjoint(dir(ModelExplanationRunner))
    assert forbidden.isdisjoint(dir(ModelExplanationResult))
