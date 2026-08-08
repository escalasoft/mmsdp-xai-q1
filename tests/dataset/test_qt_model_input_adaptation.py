"""Focused tests for reproducible Qt model-input adaptation."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from types import MappingProxyType

import pytest

from dataset.model_input import ModelPartitionInput, PreparedModelInput
from dataset.qt_model_input_adaptation import (
    QT_PROCESS_FEATURE_NAMES,
    QT_TEXT_FEATURE_NAMES,
    QtModelInputAdaptationError,
    QtModelInputAdaptationResult,
    adapt_qt_model_inputs,
)
from dataset.qt_multimodal_dataset_assembly import QtDatasetObservation
from dataset.qt_temporal_dataset_split import (
    QtTemporalDatasetSplit,
    QtTemporalSplitPolicy,
    QtTemporalSplitSpecification,
)
from feature_engineering.qt_feature_construction import QT_CODE_FEATURE_NAMES


def _observation(index: int, *, message: str | None = None) -> QtDatasetObservation:
    code = {
        name: (index if name in {"deletions", "insertions", "total_churn"} else 0)
        for name in QT_CODE_FEATURE_NAMES
    }
    process = {"is_merge_commit": int(index % 3 == 0), "parent_count": 2}
    text = {
        "raw_commit_message": message if message is not None else f"raw\n{index} 🚀"
    }
    values = {
        "commit_identifier": f"{index:040x}",
        "committed_at": f"2024-01-{index + 1:02d}T00:00:00+00:00",
        "code_features": code,
        "process_features": process,
        "text_features": text,
        "target": index % 2,
        "source_multimodal_record_digest": "a" * 64,
        "source_target_assignment_artifact_digest": "b" * 64,
    }
    return QtDatasetObservation(
        **values,
        observation_digest=QtDatasetObservation.calculate_digest(**values),
    )


def _split(*, changed_target: bool = False) -> QtTemporalDatasetSplit:
    observations = tuple(_observation(index) for index in range(7))
    if changed_target:
        original = observations[0]
        values = original._content()
        values["target"] = 1 - original.target
        changed = QtDatasetObservation(
            **values,
            observation_digest=QtDatasetObservation.calculate_digest(**values),
        )
        observations = (changed, *observations[1:])
    policy = QtTemporalSplitPolicy.create()
    values = {
        "specification_version": "qt-temporal-dataset-split-1.0.0",
        "source_dataset_artifact_digest": "c" * 64,
        "source_dataset_identity_digest": "d" * 64,
        "source_dataset_specification_digest": "e" * 64,
        "split_policy_digest": policy.policy_digest,
    }
    specification = QtTemporalSplitSpecification(
        **values,
        specification_digest=QtTemporalSplitSpecification.calculate_digest(**values),
    )
    partitions = (observations[:3], observations[3:5], observations[5:])
    return QtTemporalDatasetSplit(
        specification,
        policy,
        *partitions,
        partitions[0][-1].committed_at,
        partitions[1][0].committed_at,
        partitions[1][-1].committed_at,
        partitions[2][0].committed_at,
        QtTemporalDatasetSplit.calculate_identity(specification, partitions),
    )


def _partitions(model_input: PreparedModelInput):
    return (model_input.train, model_input.validation, model_input.test)


def test_exact_three_outputs_schemas_alignment_counts_and_numeric_contracts():
    source = _split()
    result = adapt_qt_model_inputs(source)

    assert tuple(
        name
        for name in ("code", "process", "text")
        if isinstance(getattr(result, name), PreparedModelInput)
    ) == ("code", "process", "text")
    assert result.code.feature_names == QT_CODE_FEATURE_NAMES
    assert result.process.feature_names == QT_PROCESS_FEATURE_NAMES
    assert result.text.feature_names == QT_TEXT_FEATURE_NAMES
    assert result.validation.to_dict()["modalities"] == ["code", "process", "text"]
    for index, name in enumerate(("train", "validation", "test")):
        modal = tuple(getattr(result, item) for item in ("code", "process", "text"))
        partitions = tuple(getattr(item, name) for item in modal)
        expected = getattr(source, name)
        assert all(item.identifiers == partitions[0].identifiers for item in partitions)
        assert all(item.y == partitions[0].y for item in partitions)
        assert partitions[0].identifiers == tuple(x.commit_identifier for x in expected)
        assert partitions[0].y == tuple(x.target for x in expected)
        assert partitions[0].observation_count == (3, 2, 2)[index]
        assert all(type(value) is int for row in partitions[0].X for value in row)
        assert all(type(value) is int for row in partitions[1].X for value in row)


def test_predictor_whitelists_exclude_identity_target_time_and_provenance():
    result = adapt_qt_model_inputs(_split())
    schemas = set(
        result.code.feature_names
        + result.process.feature_names
        + result.text.feature_names
    )
    forbidden = {
        "committed_at",
        "commit_identifier",
        "target",
        "partition",
        "partition_name",
        "observation_digest",
        "source_split_identity_digest",
        "dataset_identity_digest",
        "feature_artifact_digest",
        "target_assignment",
        "candidate",
        "evidence",
        "issue_link",
        "bug_confidence",
        "fix_keyword_indicator",
        "runtime_path",
        "runtime_timestamp",
        "host",
        "user",
        "provenance",
    }
    assert schemas.isdisjoint(forbidden)
    assert (
        result.code.metadata["source_split_identity_digest"]
        == result.source_split_identity_digest
    )
    assert "ordered_observation_digests" in result.code.train.metadata
    assert result.code.train.X[0] == tuple(_split().train[0].code_features.values())


def test_raw_text_is_preserved_exactly_without_numeric_conversion():
    source = _split()
    result = adapt_qt_model_inputs(source)
    expected = tuple(
        (item.text_features["raw_commit_message"],) for item in source.train
    )
    assert result.text.train.X == expected
    assert isinstance(result.text.train.X[0][0], str)


def test_repeated_adaptation_is_deterministic_immutable_and_detached():
    source = _split()
    before = source.to_dict()
    first = adapt_qt_model_inputs(source)
    repeated = adapt_qt_model_inputs(source)

    assert first == repeated
    assert first.to_dict() == repeated.to_dict()
    assert source.to_dict() == before
    assert first.code.train.X is not source.train
    with pytest.raises(FrozenInstanceError):
        first.adaptation_identity_digest = "f" * 64
    with pytest.raises(TypeError):
        first.code.metadata["new"] = True
    detached = first.to_dict()
    detached["code"]["train"]["X"][0][0] = 999
    assert first.to_dict() == repeated.to_dict()


@pytest.mark.parametrize("field", ["split_identity_digest", "train_end"])
def test_invalid_source_binding_fails_closed(field):
    source = _split()
    object.__setattr__(source, field, "f" * 64)
    with pytest.raises(QtModelInputAdaptationError, match="source split identity"):
        adapt_qt_model_inputs(source)


@pytest.mark.parametrize("modality", ["code", "process", "text"])
def test_missing_extra_or_reordered_predictors_fail(modality):
    source = _split()
    observation = source.train[0]
    field = f"{modality}_features"
    malformed = dict(getattr(observation, field))
    if len(malformed) == 1:
        malformed["extra"] = "forbidden"
    else:
        first = next(iter(malformed))
        malformed = {
            **{key: value for key, value in malformed.items() if key != first},
            first: malformed[first],
        }
    object.__setattr__(observation, field, MappingProxyType(malformed))
    with pytest.raises(QtModelInputAdaptationError, match="schema"):
        adapt_qt_model_inputs(source)


def test_duplicate_cross_partition_commit_fails_even_with_rebound_split_identity():
    source = _split()
    partitions = (source.train, source.validation, (source.train[0], source.test[1]))
    object.__setattr__(source, "test", partitions[2])
    object.__setattr__(
        source,
        "split_identity_digest",
        source.calculate_identity(source.specification, partitions),
    )
    with pytest.raises(
        QtModelInputAdaptationError, match="duplicate or cross-partition"
    ):
        adapt_qt_model_inputs(source)


@pytest.mark.parametrize(
    ("field", "values", "message"),
    [
        (
            "code_features",
            {**{name: 0 for name in QT_CODE_FEATURE_NAMES}, "total_churn": -1},
            "CODE",
        ),
        ("process_features", {"is_merge_commit": 2, "parent_count": 1}, "PROCESS"),
    ],
)
def test_code_and_process_domain_violations_fail(field, values, message):
    source = _split()
    object.__setattr__(source.train[0], field, MappingProxyType(values))
    with pytest.raises(QtModelInputAdaptationError, match=message):
        adapt_qt_model_inputs(source)


def test_modality_identifier_and_target_mismatch_fails():
    result = adapt_qt_model_inputs(_split())
    changed_partition = ModelPartitionInput(
        "train",
        result.process.train.identifiers,
        result.process.train.X,
        (1 - result.process.train.y[0], *result.process.train.y[1:]),
        result.process.train.feature_names,
        result.process.train.metadata,
    )
    changed_process = PreparedModelInput(
        result.process.dataset_name,
        result.process.dataset_version,
        changed_partition,
        result.process.validation,
        result.process.test,
        result.process.feature_names,
        result.process.target_name,
        result.process.metadata,
    )
    with pytest.raises(QtModelInputAdaptationError, match="targets"):
        replace(result, process=changed_process)

    changed_partition = ModelPartitionInput(
        "train",
        ("f" * 40, *result.process.train.identifiers[1:]),
        result.process.train.X,
        result.process.train.y,
        result.process.train.feature_names,
        result.process.train.metadata,
    )
    changed_process = PreparedModelInput(
        result.process.dataset_name,
        result.process.dataset_version,
        changed_partition,
        result.process.validation,
        result.process.test,
        result.process.feature_names,
        result.process.target_name,
        result.process.metadata,
    )
    with pytest.raises(QtModelInputAdaptationError, match="identifiers"):
        replace(result, process=changed_process)


def test_scientific_changes_change_identity_but_runtime_metadata_does_not():
    baseline = adapt_qt_model_inputs(_split())
    changed = adapt_qt_model_inputs(_split(changed_target=True))
    assert baseline.adaptation_identity_digest != changed.adaptation_identity_digest

    metadata_only = PreparedModelInput(
        baseline.code.dataset_name,
        baseline.code.dataset_version,
        baseline.code.train,
        baseline.code.validation,
        baseline.code.test,
        baseline.code.feature_names,
        baseline.code.target_name,
        {**baseline.code.metadata, "runtime_note": "ignored"},
    )
    assert (
        QtModelInputAdaptationResult.calculate_identity(
            baseline.specification,
            baseline.policy,
            metadata_only,
            baseline.process,
            baseline.text,
        )
        == baseline.adaptation_identity_digest
    )
