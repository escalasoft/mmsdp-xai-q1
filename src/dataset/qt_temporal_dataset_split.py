"""Reproducible temporal splitting of the assembled Qt scientific dataset."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime
from enum import Enum

from dataset.contracts import AdaptedDataset, DatasetRecord
from dataset.qt_multimodal_dataset_assembly import (
    QtDatasetObservation,
    QtMultimodalDatasetAssemblyResult,
)
from dataset.temporal_splitter import (
    TemporalDatasetSplitter,
    TemporalSplitConfiguration,
)

__all__ = [
    "QtTemporalSplitError",
    "QtTemporalSplitPolicy",
    "QtTemporalSplitSpecification",
    "QtTemporalDatasetSplit",
    "build_qt_temporal_split_specification",
    "split_qt_temporal_dataset",
]

_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_OBJECT_ID = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
_FEATURE_NAMES = (
    "binary_files",
    "deletions",
    "files_added",
    "files_changed",
    "files_copied",
    "files_modified",
    "files_removed",
    "files_renamed",
    "files_type_changed",
    "has_binary_files",
    "insertions",
    "text_files",
    "total_churn",
    "is_merge_commit",
    "parent_count",
    "raw_commit_message",
)


class QtTemporalSplitError(RuntimeError):
    """A violation of the frozen Qt temporal-splitting contract."""


def _thaw(value: object) -> object:
    if is_dataclass(value) and not isinstance(value, type):
        return {item.name: _thaw(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    if isinstance(value, Enum):
        return value.value
    return value


def _digest(value: object) -> str:
    payload = json.dumps(
        _thaw(value),
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _require_digest(value: object, name: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")
    return value


def _timestamp(value: object) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("committed_at must be a non-empty ISO-8601 string")
    try:
        result = datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError("committed_at must be an ISO-8601 timestamp") from error
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("committed_at must include a UTC offset")
    return result


@dataclass(frozen=True, slots=True)
class QtTemporalSplitPolicy:
    """Frozen primary-evaluation split and ordering semantics."""

    policy_version: str = "qt-temporal-split-policy-1.0.0"
    timestamp_field: str = "committed_at"
    timestamp_source: str = "approved-git-committer-timestamp"
    ordering_policy: str = "chronological-ascending"
    equal_timestamp_policy: str = "commit-identifier-ascending-secondary-order"
    membership_policy: str = "contiguous-oldest-70-next-15-newest-15"
    train_fraction: float = 0.70
    validation_fraction: float = 0.15
    test_fraction: float = 0.15
    policy_digest: str = ""

    def __post_init__(self) -> None:
        content = self.to_dict()
        content.pop("policy_digest")
        if content != self.scientific_values():
            raise ValueError("temporal split policy does not match the frozen policy")
        if self.policy_digest != self.calculate_digest():
            raise ValueError("policy_digest must derive from frozen scientific policy")

    @staticmethod
    def scientific_values() -> dict[str, object]:
        return {
            "policy_version": "qt-temporal-split-policy-1.0.0",
            "timestamp_field": "committed_at",
            "timestamp_source": "approved-git-committer-timestamp",
            "ordering_policy": "chronological-ascending",
            "equal_timestamp_policy": "commit-identifier-ascending-secondary-order",
            "membership_policy": "contiguous-oldest-70-next-15-newest-15",
            "train_fraction": 0.70,
            "validation_fraction": 0.15,
            "test_fraction": 0.15,
        }

    @classmethod
    def create(cls) -> QtTemporalSplitPolicy:
        return cls(policy_digest=cls.calculate_digest())

    @classmethod
    def calculate_digest(cls) -> str:
        return _digest(cls.scientific_values())

    def to_dict(self) -> dict[str, object]:
        return _thaw(self)  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class QtTemporalSplitSpecification:
    """Identity binding between one assembled dataset and one split policy."""

    specification_version: str
    source_dataset_artifact_digest: str
    source_dataset_identity_digest: str
    source_dataset_specification_digest: str
    split_policy_digest: str
    specification_digest: str

    def __post_init__(self) -> None:
        if self.specification_version != "qt-temporal-dataset-split-1.0.0":
            raise ValueError("unsupported temporal split specification version")
        for name in (
            "source_dataset_artifact_digest",
            "source_dataset_identity_digest",
            "source_dataset_specification_digest",
            "split_policy_digest",
        ):
            _require_digest(getattr(self, name), name)
        if self.specification_digest != self.calculate_digest(**self._content()):
            raise ValueError("specification_digest must identify scientific content")

    def _content(self) -> dict[str, object]:
        return {
            item.name: getattr(self, item.name)
            for item in fields(self)
            if item.name != "specification_digest"
        }

    @classmethod
    def calculate_digest(cls, **content: object) -> str:
        content.pop("specification_digest", None)
        return _digest(content)

    def to_dict(self) -> dict[str, object]:
        return _thaw(self)  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class QtTemporalDatasetSplit:
    """Immutable chronological Qt partitions with reproducible identity."""

    specification: QtTemporalSplitSpecification
    policy: QtTemporalSplitPolicy
    train: tuple[QtDatasetObservation, ...]
    validation: tuple[QtDatasetObservation, ...]
    test: tuple[QtDatasetObservation, ...]
    train_end: str
    validation_start: str
    validation_end: str
    test_start: str
    split_identity_digest: str

    def __post_init__(self) -> None:
        if self.specification.split_policy_digest != self.policy.policy_digest:
            raise ValueError("specification and temporal split policy disagree")
        partitions = (tuple(self.train), tuple(self.validation), tuple(self.test))
        if any(not partition for partition in partitions):
            raise ValueError("train, validation, and test must be non-empty")
        observations = tuple(item for part in partitions for item in part)
        identifiers = tuple(item.commit_identifier for item in observations)
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("partition membership must be unique")
        ordered = tuple(
            sorted(
                observations,
                key=lambda item: (
                    _timestamp(item.committed_at),
                    item.commit_identifier,
                ),
            )
        )
        if observations != ordered:
            raise ValueError("partitions must follow canonical chronological order")
        boundaries = (
            partitions[0][-1].committed_at,
            partitions[1][0].committed_at,
            partitions[1][-1].committed_at,
            partitions[2][0].committed_at,
        )
        if boundaries != (
            self.train_end,
            self.validation_start,
            self.validation_end,
            self.test_start,
        ):
            raise ValueError("declared split boundaries do not match membership")
        if self.split_identity_digest != self.calculate_identity(
            self.specification, partitions
        ):
            raise ValueError("split_identity_digest is inconsistent")
        object.__setattr__(self, "train", partitions[0])
        object.__setattr__(self, "validation", partitions[1])
        object.__setattr__(self, "test", partitions[2])

    @staticmethod
    def calculate_identity(
        specification: QtTemporalSplitSpecification,
        partitions: Sequence[Sequence[QtDatasetObservation]],
    ) -> str:
        names = ("train", "validation", "test")
        return _digest(
            {
                "source_dataset_artifact_digest": (
                    specification.source_dataset_artifact_digest
                ),
                "source_dataset_identity_digest": (
                    specification.source_dataset_identity_digest
                ),
                "split_specification_digest": specification.specification_digest,
                "ordered_membership": [
                    {
                        "partition": name,
                        "commit_identifier": item.commit_identifier,
                        "observation_digest": item.observation_digest,
                    }
                    for name, partition in zip(names, partitions, strict=True)
                    for item in partition
                ],
                "partition_counts": {
                    name: len(partition)
                    for name, partition in zip(names, partitions, strict=True)
                },
                "boundaries": {
                    "train_end": partitions[0][-1].committed_at,
                    "validation_start": partitions[1][0].committed_at,
                    "validation_end": partitions[1][-1].committed_at,
                    "test_start": partitions[2][0].committed_at,
                },
            }
        )

    @property
    def total_observation_count(self) -> int:
        return len(self.train) + len(self.validation) + len(self.test)

    def to_dict(self) -> dict[str, object]:
        return _thaw(self)  # type: ignore[return-value]


def build_qt_temporal_split_specification(
    dataset: QtMultimodalDatasetAssemblyResult,
    policy: QtTemporalSplitPolicy | None = None,
) -> QtTemporalSplitSpecification:
    """Bind the frozen assembled-dataset identity to the split policy."""
    if not isinstance(dataset, QtMultimodalDatasetAssemblyResult):
        raise TypeError("dataset must be QtMultimodalDatasetAssemblyResult")
    policy = policy or QtTemporalSplitPolicy.create()
    values = {
        "specification_version": "qt-temporal-dataset-split-1.0.0",
        "source_dataset_artifact_digest": dataset.dataset_artifact.content_digest,
        "source_dataset_identity_digest": dataset.assembly_identity_digest,
        "source_dataset_specification_digest": (
            dataset.specification.specification_digest
        ),
        "split_policy_digest": policy.policy_digest,
    }
    return QtTemporalSplitSpecification(
        **values,
        specification_digest=QtTemporalSplitSpecification.calculate_digest(**values),
    )


def _adapt_observation(observation: QtDatasetObservation) -> DatasetRecord:
    features = {
        **observation.code_features,
        **observation.process_features,
        **observation.text_features,
    }
    if tuple(features) != _FEATURE_NAMES:
        raise QtTemporalSplitError("Qt observation predictor inventory is not frozen")
    return DatasetRecord(
        identifier=observation.commit_identifier,
        features=features,
        target=observation.target,
        timestamp=_timestamp(observation.committed_at),
        metadata={"observation_digest": observation.observation_digest},
    )


def split_qt_temporal_dataset(
    dataset: QtMultimodalDatasetAssemblyResult,
    specification: QtTemporalSplitSpecification,
    policy: QtTemporalSplitPolicy,
) -> QtTemporalDatasetSplit:
    """Split by authoritative commit time without consulting targets or features."""
    if not isinstance(dataset, QtMultimodalDatasetAssemblyResult):
        raise TypeError("dataset must be QtMultimodalDatasetAssemblyResult")
    expected = build_qt_temporal_split_specification(dataset, policy)
    if specification != expected:
        raise QtTemporalSplitError("split specification does not bind exact inputs")

    by_identifier: dict[str, QtDatasetObservation] = {}
    for observation in dataset.observations:
        identifier = observation.commit_identifier
        if not isinstance(identifier, str) or not _OBJECT_ID.fullmatch(identifier):
            raise QtTemporalSplitError(
                "observation has a missing or invalid commit identity"
            )
        if identifier in by_identifier:
            raise QtTemporalSplitError(f"duplicate commit identity: {identifier}")
        _timestamp(observation.committed_at)
        by_identifier[identifier] = observation
    ordered = tuple(
        sorted(
            by_identifier.values(),
            key=lambda item: (_timestamp(item.committed_at), item.commit_identifier),
        )
    )
    adapted = AdaptedDataset(
        dataset_name="qtbase-multimodal-commit-dataset",
        dataset_version=dataset.assembly_identity_digest,
        records=tuple(_adapt_observation(item) for item in ordered),
        feature_names=_FEATURE_NAMES,
        target_name="target",
        metadata={
            "source_dataset_artifact_digest": dataset.dataset_artifact.content_digest,
            "source_dataset_identity_digest": dataset.assembly_identity_digest,
            "split_specification_digest": specification.specification_digest,
        },
    )
    generic = TemporalDatasetSplitter(
        TemporalSplitConfiguration(
            policy.train_fraction,
            policy.validation_fraction,
            policy.test_fraction,
        )
    ).split(adapted)

    partitions = tuple(
        tuple(by_identifier[record.identifier] for record in partition)
        for partition in (generic.train, generic.validation, generic.test)
    )
    identity = QtTemporalDatasetSplit.calculate_identity(specification, partitions)
    return QtTemporalDatasetSplit(
        specification=specification,
        policy=policy,
        train=partitions[0],
        validation=partitions[1],
        test=partitions[2],
        train_end=partitions[0][-1].committed_at,
        validation_start=partitions[1][0].committed_at,
        validation_end=partitions[1][-1].committed_at,
        test_start=partitions[2][0].committed_at,
        split_identity_digest=identity,
    )
