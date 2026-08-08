"""Focused scientific tests for Qt temporal dataset splitting."""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

import pytest

from dataset.qt_multimodal_dataset_assembly import (
    QtDatasetObservation,
    QtMultimodalDatasetAssemblyResult,
)
from dataset.qt_temporal_dataset_split import (
    QtTemporalSplitError,
    QtTemporalSplitPolicy,
    _adapt_observation,
    build_qt_temporal_split_specification,
    split_qt_temporal_dataset,
)
from feature_engineering.qt_feature_construction import QT_CODE_FEATURE_NAMES

_DIGEST = "a" * 64


def _observation(
    index: int,
    timestamp: str,
    *,
    target: int | None = None,
    churn: int | None = None,
) -> QtDatasetObservation:
    values = {
        "commit_identifier": f"{index:040x}",
        "committed_at": timestamp,
        "code_features": {
            name: (index if name == "total_churn" and churn is None else 0)
            for name in QT_CODE_FEATURE_NAMES
        },
        "process_features": {"is_merge_commit": 0, "parent_count": 1},
        "text_features": {"raw_commit_message": f"message {index}"},
        "target": index % 2 if target is None else target,
        "source_multimodal_record_digest": _DIGEST,
        "source_target_assignment_artifact_digest": "b" * 64,
    }
    if churn is not None:
        values["code_features"]["total_churn"] = churn
    return QtDatasetObservation(
        **values,
        observation_digest=QtDatasetObservation.calculate_digest(**values),
    )


def _dataset(
    observations: tuple[QtDatasetObservation, ...] | None = None,
    *,
    identity: str = "c" * 64,
) -> QtMultimodalDatasetAssemblyResult:
    if observations is None:
        observations = tuple(
            _observation(index, f"2024-01-{20 - index:02d}T00:00:00+00:00")
            for index in range(20)
        )
    result = object.__new__(QtMultimodalDatasetAssemblyResult)
    object.__setattr__(result, "observations", observations)
    object.__setattr__(result, "assembly_identity_digest", identity)
    object.__setattr__(
        result, "dataset_artifact", SimpleNamespace(content_digest="d" * 64)
    )
    object.__setattr__(
        result,
        "specification",
        SimpleNamespace(specification_digest="e" * 64),
    )
    return result


def _split(dataset=None):
    dataset = dataset or _dataset()
    policy = QtTemporalSplitPolicy.create()
    specification = build_qt_temporal_split_specification(dataset, policy)
    return split_qt_temporal_dataset(dataset, specification, policy)


def _members(result):
    return tuple(
        tuple(item.commit_identifier for item in partition)
        for partition in (result.train, result.validation, result.test)
    )


def test_uses_frozen_70_15_15_policy_and_exact_counts():
    result = _split()

    assert (len(result.train), len(result.validation), len(result.test)) == (14, 3, 3)
    assert result.policy.to_dict() == {
        **QtTemporalSplitPolicy.scientific_values(),
        "policy_digest": QtTemporalSplitPolicy.calculate_digest(),
    }


def test_is_deterministic_and_independent_of_input_iteration_order():
    source = _dataset()
    reversed_source = _dataset(tuple(reversed(source.observations)))

    first = _split(source)
    repeated = _split(source)
    reordered = _split(reversed_source)

    assert _members(first) == _members(repeated) == _members(reordered)
    assert first.split_identity_digest == repeated.split_identity_digest
    assert first.split_identity_digest == reordered.split_identity_digest


def test_partitions_are_chronological_contiguous_and_conserve_every_observation():
    source = _dataset()
    result = _split(source)
    combined = result.train + result.validation + result.test
    times = [item.committed_at for item in combined]

    assert times == sorted(times)
    assert result.train[-1].committed_at <= result.validation[0].committed_at
    assert result.validation[-1].committed_at <= result.test[0].committed_at
    assert len(combined) == len(source.observations)
    assert {item.commit_identifier for item in combined} == {
        item.commit_identifier for item in source.observations
    }


def test_equal_timestamps_use_commit_identifier_as_secondary_order():
    same = "2024-01-01T00:00:00+00:00"
    observations = tuple(_observation(index, same) for index in reversed(range(20)))

    result = _split(_dataset(observations))
    combined = result.train + result.validation + result.test

    assert [item.commit_identifier for item in combined] == sorted(
        item.commit_identifier for item in observations
    )
    assert result.train_end == result.validation_start == same
    assert result.validation_end == result.test_start == same


def test_different_offsets_are_ordered_by_instant_with_identifier_ties():
    timestamps = {
        10: "2024-01-01T00:30:00+02:00",  # 2023-12-31 22:30 UTC
        11: "2023-12-31T23:00:00+00:00",
        2: "2024-01-02T10:00:00+00:00",
        17: "2024-01-02T05:00:00-05:00",  # Same instant as commit 2.
    }
    observations = tuple(
        _observation(
            index,
            timestamps.get(index, f"2024-02-{index + 1:02d}T00:00:00+00:00"),
        )
        for index in reversed(range(20))
    )

    result = _split(_dataset(observations))
    combined = result.train + result.validation + result.test
    instants = [datetime.fromisoformat(item.committed_at) for item in combined]
    identifiers = [item.commit_identifier for item in combined]

    assert instants == sorted(instants)
    assert [item.committed_at for item in combined] != sorted(
        item.committed_at for item in combined
    )
    assert identifiers.index(f"{2:040x}") < identifiers.index(f"{17:040x}")


def test_membership_is_target_and_feature_independent():
    timestamps = tuple(f"2024-01-{index + 1:02d}T00:00:00+00:00" for index in range(20))
    baseline = tuple(
        _observation(index, value) for index, value in enumerate(timestamps)
    )
    changed = tuple(
        _observation(index, value, target=1 - index % 2, churn=999 - index)
        for index, value in enumerate(timestamps)
    )

    assert _members(_split(_dataset(baseline))) == _members(_split(_dataset(changed)))


def test_adapter_exposes_only_frozen_predictors():
    observation = _observation(1, "2024-01-01T00:00:00+00:00")
    record = _adapt_observation(observation)

    assert set(record.features) == {
        *QT_CODE_FEATURE_NAMES,
        "is_merge_commit",
        "parent_count",
        "raw_commit_message",
    }
    assert not set(record.features) & {
        "committed_at",
        "commit_identifier",
        "target",
        "partition",
        "observation_digest",
        "assembly_identity_digest",
    }
    assert record.timestamp.isoformat() == observation.committed_at


@pytest.mark.parametrize(
    ("timestamp", "message"),
    [
        (None, "non-empty"),
        ("", "non-empty"),
        ("not-a-time", "ISO-8601"),
        ("2024-01-01T00:00:00", "UTC offset"),
    ],
)
def test_missing_invalid_or_naive_authoritative_timestamps_are_rejected(
    timestamp, message
):
    observation = _observation(0, "2024-01-01T00:00:00+00:00")
    object.__setattr__(observation, "committed_at", timestamp)
    with pytest.raises(ValueError, match=message):
        _split(_dataset((observation,) * 20))


def test_duplicate_commit_identity_is_rejected():
    observations = list(_dataset().observations)
    observations[-1] = observations[0]
    with pytest.raises(QtTemporalSplitError, match="duplicate commit identity"):
        _split(_dataset(tuple(observations)))


@pytest.mark.parametrize("identifier", [None, "", "short"])
def test_missing_or_invalid_commit_identity_is_rejected(identifier):
    observations = list(_dataset().observations)
    object.__setattr__(observations[0], "commit_identifier", identifier)
    with pytest.raises(QtTemporalSplitError, match="commit identity"):
        _split(_dataset(tuple(observations)))


def test_source_dataset_and_policy_are_bound_into_identity():
    source = _dataset()
    first = _split(source)
    changed_source = _split(_dataset(source.observations, identity="f" * 64))

    assert first.specification.source_dataset_identity_digest == "c" * 64
    assert first.specification.split_policy_digest == first.policy.policy_digest
    assert first.split_identity_digest != changed_source.split_identity_digest


def test_mismatched_specification_is_rejected():
    source = _dataset()
    policy = QtTemporalSplitPolicy.create()
    specification = build_qt_temporal_split_specification(source, policy)
    other = _dataset(source.observations, identity="f" * 64)

    with pytest.raises(QtTemporalSplitError, match="exact inputs"):
        split_qt_temporal_dataset(other, specification, policy)


def test_too_few_observations_cannot_create_empty_partitions():
    observations = tuple(
        _observation(index, f"2024-01-0{index + 1}T00:00:00+00:00")
        for index in range(3)
    )
    with pytest.raises(ValueError, match="empty partition"):
        _split(_dataset(observations))
