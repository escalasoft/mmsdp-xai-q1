"""Deterministic Qt post-split adaptation into modality-specific model inputs."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, fields, is_dataclass
from enum import Enum

from dataset.contracts import AdaptedDataset, DatasetRecord
from dataset.experiment_dataset import (
    ExperimentDatasetPartition,
    ExperimentDatasetPreparer,
    PreparedExperimentDataset,
)
from dataset.model_input import ModelInputBuilder, PreparedModelInput
from dataset.qt_multimodal_dataset_assembly import QtDatasetObservation
from dataset.qt_temporal_dataset_split import QtTemporalDatasetSplit
from dataset.temporal_splitter import TemporalDatasetSplit
from feature_engineering.qt_feature_construction import QT_CODE_FEATURE_NAMES

__all__ = [
    "QT_PROCESS_FEATURE_NAMES",
    "QT_TEXT_FEATURE_NAMES",
    "QtModelInputAdaptationError",
    "QtModelInputAdaptationPolicy",
    "QtModelInputAdaptationSpecification",
    "QtModelInputAdaptationValidation",
    "QtModelInputAdaptationResult",
    "adapt_qt_model_inputs",
]

QT_PROCESS_FEATURE_NAMES = ("is_merge_commit", "parent_count")
QT_TEXT_FEATURE_NAMES = ("raw_commit_message",)
_MODALITY_SCHEMAS = {
    "code": QT_CODE_FEATURE_NAMES,
    "process": QT_PROCESS_FEATURE_NAMES,
    "text": QT_TEXT_FEATURE_NAMES,
}
_PARTITION_NAMES = ("train", "validation", "test")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


class QtModelInputAdaptationError(RuntimeError):
    """A violation of the frozen Qt model-input adaptation boundary."""


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


@dataclass(frozen=True, slots=True)
class QtModelInputAdaptationPolicy:
    """Frozen whitelist and no-preprocessing policy for the three modalities."""

    policy_version: str = "qt-model-input-adaptation-policy-1.0.0"
    modality_order: tuple[str, ...] = ("code", "process", "text")
    code_feature_names: tuple[str, ...] = QT_CODE_FEATURE_NAMES
    process_feature_names: tuple[str, ...] = QT_PROCESS_FEATURE_NAMES
    text_feature_names: tuple[str, ...] = QT_TEXT_FEATURE_NAMES
    membership_policy: str = "preserve-frozen-temporal-partitions-exactly"
    preprocessing_policy: str = "none"
    text_policy: str = "preserve-raw-python-string"
    policy_digest: str = ""

    def __post_init__(self) -> None:
        content = self.to_dict()
        content.pop("policy_digest")
        if content != self.scientific_values():
            raise ValueError("adaptation policy does not match the frozen policy")
        if self.policy_digest != self.calculate_digest():
            raise ValueError("policy_digest must derive from frozen scientific policy")

    @staticmethod
    def scientific_values() -> dict[str, object]:
        return {
            "policy_version": "qt-model-input-adaptation-policy-1.0.0",
            "modality_order": ["code", "process", "text"],
            "code_feature_names": list(QT_CODE_FEATURE_NAMES),
            "process_feature_names": list(QT_PROCESS_FEATURE_NAMES),
            "text_feature_names": list(QT_TEXT_FEATURE_NAMES),
            "membership_policy": "preserve-frozen-temporal-partitions-exactly",
            "preprocessing_policy": "none",
            "text_policy": "preserve-raw-python-string",
        }

    @classmethod
    def create(cls) -> QtModelInputAdaptationPolicy:
        return cls(policy_digest=cls.calculate_digest())

    @classmethod
    def calculate_digest(cls) -> str:
        return _digest(cls.scientific_values())

    def to_dict(self) -> dict[str, object]:
        return _thaw(self)  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class QtModelInputAdaptationSpecification:
    """Scientific binding between one frozen split and one adaptation policy."""

    specification_version: str
    source_split_identity_digest: str
    source_split_specification_digest: str
    source_dataset_artifact_digest: str
    source_dataset_identity_digest: str
    source_dataset_specification_digest: str
    adaptation_policy_digest: str
    specification_digest: str

    def __post_init__(self) -> None:
        if self.specification_version != "qt-model-input-adaptation-1.0.0":
            raise ValueError("unsupported adaptation specification version")
        for item in fields(self):
            if item.name.endswith("_digest") and item.name != "specification_digest":
                _require_digest(getattr(self, item.name), item.name)
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
class QtModelInputAdaptationValidation:
    """Auditable alignment checks performed at the adaptation boundary."""

    is_valid: bool
    train_count: int
    validation_count: int
    test_count: int
    modalities: tuple[str, ...]
    identifiers_aligned: bool
    targets_aligned: bool
    schemas_exact: bool
    error_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.is_valid is not True or self.error_codes:
            raise ValueError(
                "only successfully validated adaptations are representable"
            )
        if any(
            type(value) is not int or value <= 0
            for value in (self.train_count, self.validation_count, self.test_count)
        ):
            raise ValueError("partition counts must be positive integers")
        if self.modalities != ("code", "process", "text"):
            raise ValueError("validation must cover exactly the frozen modalities")
        if not all(
            (self.identifiers_aligned, self.targets_aligned, self.schemas_exact)
        ):
            raise ValueError("adapted modality validation must pass")

    def to_dict(self) -> dict[str, object]:
        return _thaw(self)  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class QtModelInputAdaptationResult:
    """Three aligned immutable modality inputs and their scientific identity."""

    specification: QtModelInputAdaptationSpecification
    policy: QtModelInputAdaptationPolicy
    code: PreparedModelInput
    process: PreparedModelInput
    text: PreparedModelInput
    validation: QtModelInputAdaptationValidation
    source_split_identity_digest: str
    adaptation_identity_digest: str

    def __post_init__(self) -> None:
        if self.specification.adaptation_policy_digest != self.policy.policy_digest:
            raise ValueError("specification and adaptation policy disagree")
        if self.source_split_identity_digest != (
            self.specification.source_split_identity_digest
        ):
            raise ValueError("source split identity binding is inconsistent")
        _validate_outputs(self.code, self.process, self.text)
        if (
            self.validation.train_count,
            self.validation.validation_count,
            self.validation.test_count,
        ) != tuple(
            getattr(self.code, name).observation_count for name in _PARTITION_NAMES
        ):
            raise ValueError("validation counts do not match adapted partitions")
        expected = self.calculate_identity(
            self.specification, self.policy, self.code, self.process, self.text
        )
        if self.adaptation_identity_digest != expected:
            raise ValueError("adaptation_identity_digest is inconsistent")

    @staticmethod
    def calculate_identity(
        specification: QtModelInputAdaptationSpecification,
        policy: QtModelInputAdaptationPolicy,
        code: PreparedModelInput,
        process: PreparedModelInput,
        text: PreparedModelInput,
    ) -> str:
        inputs = {"code": code, "process": process, "text": text}
        return _digest(
            {
                "source_split_identity_digest": (
                    specification.source_split_identity_digest
                ),
                "source_split_specification_digest": (
                    specification.source_split_specification_digest
                ),
                "source_dataset_artifact_digest": (
                    specification.source_dataset_artifact_digest
                ),
                "source_dataset_identity_digest": (
                    specification.source_dataset_identity_digest
                ),
                "source_dataset_specification_digest": (
                    specification.source_dataset_specification_digest
                ),
                "adaptation_specification_digest": specification.specification_digest,
                "adaptation_policy_digest": policy.policy_digest,
                "modalities": [
                    {"name": name, "feature_names": list(inputs[name].feature_names)}
                    for name in policy.modality_order
                ],
                "ordered_partitions": [
                    {
                        "partition": partition_name,
                        "ordered_observations": [
                            {
                                "commit_identifier": identifier,
                                "observation_digest": observation_digest,
                                "target": target,
                            }
                            for identifier, observation_digest, target in zip(
                                getattr(code, partition_name).identifiers,
                                getattr(code, partition_name).metadata[
                                    "ordered_observation_digests"
                                ],
                                getattr(code, partition_name).y,
                                strict=True,
                            )
                        ],
                    }
                    for partition_name in _PARTITION_NAMES
                ],
            }
        )

    def to_dict(self) -> dict[str, object]:
        return _thaw(self)  # type: ignore[return-value]


def _validate_source(split: QtTemporalDatasetSplit) -> None:
    if not isinstance(split, QtTemporalDatasetSplit):
        raise TypeError("split must be a QtTemporalDatasetSplit")
    spec = split.specification
    if spec.split_policy_digest != split.policy.policy_digest:
        raise QtModelInputAdaptationError("source split policy binding is invalid")
    if split.policy.policy_digest != split.policy.calculate_digest():
        raise QtModelInputAdaptationError("source split policy identity is invalid")
    if spec.specification_digest != spec.calculate_digest(**spec._content()):
        raise QtModelInputAdaptationError("source split specification is invalid")
    partitions = (split.train, split.validation, split.test)
    identifiers: set[str] = set()
    for partition in partitions:
        for observation in partition:
            if not isinstance(observation, QtDatasetObservation):
                raise QtModelInputAdaptationError(
                    "source partitions must contain QtDatasetObservation instances"
                )
            if observation.commit_identifier in identifiers:
                raise QtModelInputAdaptationError(
                    "duplicate or cross-partition commit identity"
                )
            identifiers.add(observation.commit_identifier)
            if tuple(observation.code_features) != QT_CODE_FEATURE_NAMES:
                raise QtModelInputAdaptationError("CODE predictor schema is not exact")
            if tuple(observation.process_features) != QT_PROCESS_FEATURE_NAMES:
                raise QtModelInputAdaptationError(
                    "PROCESS predictor schema is not exact"
                )
            if tuple(observation.text_features) != QT_TEXT_FEATURE_NAMES:
                raise QtModelInputAdaptationError("TEXT predictor schema is not exact")
            if any(
                type(value) is not int or value < 0
                for value in observation.code_features.values()
            ):
                raise QtModelInputAdaptationError("CODE values violate their domain")
            if (
                type(observation.process_features["is_merge_commit"]) is not int
                or observation.process_features["is_merge_commit"] not in (0, 1)
                or type(observation.process_features["parent_count"]) is not int
                or observation.process_features["parent_count"] < 0
            ):
                raise QtModelInputAdaptationError("PROCESS values violate their domain")
            if not isinstance(observation.text_features["raw_commit_message"], str):
                raise QtModelInputAdaptationError("raw TEXT must be a Python string")
            if observation.observation_digest != observation.calculate_digest(
                **observation._content()
            ):
                raise QtModelInputAdaptationError("observation identity is invalid")
    if split.split_identity_digest != split.calculate_identity(spec, partitions):
        raise QtModelInputAdaptationError("source split identity is invalid")
    boundaries = (
        partitions[0][-1].committed_at,
        partitions[1][0].committed_at,
        partitions[1][-1].committed_at,
        partitions[2][0].committed_at,
    )
    if boundaries != (
        split.train_end,
        split.validation_start,
        split.validation_end,
        split.test_start,
    ):
        raise QtModelInputAdaptationError("source split identity is invalid")
    try:
        QtTemporalDatasetSplit(
            split.specification,
            split.policy,
            split.train,
            split.validation,
            split.test,
            split.train_end,
            split.validation_start,
            split.validation_end,
            split.test_start,
            split.split_identity_digest,
        )
    except (TypeError, ValueError) as error:
        raise QtModelInputAdaptationError(
            "source split violates the frozen temporal contract"
        ) from error


def _build_input(
    split: QtTemporalDatasetSplit,
    modality: str,
    specification: QtModelInputAdaptationSpecification,
) -> PreparedModelInput:
    schema = _MODALITY_SCHEMAS[modality]
    source_partitions = (split.train, split.validation, split.test)
    records_by_partition: list[tuple[DatasetRecord, ...]] = []
    all_records: list[DatasetRecord] = []
    for partition in source_partitions:
        records = tuple(
            DatasetRecord(
                identifier=observation.commit_identifier,
                features=dict(getattr(observation, f"{modality}_features")),
                target=observation.target,
                metadata={"observation_digest": observation.observation_digest},
            )
            for observation in partition
        )
        records_by_partition.append(records)
        all_records.extend(records)
    metadata = {
        "modality": modality,
        "source_split_identity_digest": split.split_identity_digest,
        "source_split_specification_digest": split.specification.specification_digest,
        "adaptation_specification_digest": specification.specification_digest,
    }
    adapted = AdaptedDataset(
        dataset_name=f"qt-{modality}",
        dataset_version=specification.specification_version,
        records=all_records,
        feature_names=schema,
        target_name="target",
        metadata=metadata,
    )
    temporal = TemporalDatasetSplit(
        dataset_name=adapted.dataset_name,
        dataset_version=adapted.dataset_version,
        train=records_by_partition[0],
        validation=records_by_partition[1],
        test=records_by_partition[2],
        feature_names=adapted.feature_names,
        target_name=adapted.target_name,
        metadata=adapted.metadata,
    )
    prepared = ExperimentDatasetPreparer().prepare(temporal)
    replacements: list[ExperimentDatasetPartition] = []
    for name, source_partition in zip(_PARTITION_NAMES, source_partitions, strict=True):
        partition = getattr(prepared, name)
        replacements.append(
            ExperimentDatasetPartition(
                partition.partition_name,
                partition.identifiers,
                partition.features,
                partition.targets,
                partition.feature_names,
                {
                    **partition.metadata,
                    "ordered_observation_digests": tuple(
                        item.observation_digest for item in source_partition
                    ),
                },
            )
        )
    prepared_with_identities = PreparedExperimentDataset(
        prepared.dataset_name,
        prepared.dataset_version,
        replacements[0],
        replacements[1],
        replacements[2],
        prepared.feature_names,
        prepared.target_name,
        prepared.metadata,
    )
    return ModelInputBuilder().build(prepared_with_identities)


def _validate_outputs(
    code: PreparedModelInput,
    process: PreparedModelInput,
    text: PreparedModelInput,
) -> None:
    outputs = (code, process, text)
    if tuple(item.feature_names for item in outputs) != tuple(
        _MODALITY_SCHEMAS[name] for name in ("code", "process", "text")
    ):
        raise QtModelInputAdaptationError("modality predictor schemas are not exact")
    for partition_name in _PARTITION_NAMES:
        partitions = tuple(getattr(item, partition_name) for item in outputs)
        if any(item.identifiers != partitions[0].identifiers for item in partitions):
            raise QtModelInputAdaptationError("modality identifiers are not aligned")
        if any(item.y != partitions[0].y for item in partitions):
            raise QtModelInputAdaptationError("modality targets are not aligned")
        if any(
            item.metadata.get("ordered_observation_digests")
            != partitions[0].metadata.get("ordered_observation_digests")
            for item in partitions
        ):
            raise QtModelInputAdaptationError(
                "modality observation identities are not aligned"
            )
        if any(
            item.observation_count != partitions[0].observation_count
            for item in partitions
        ):
            raise QtModelInputAdaptationError(
                "modality partition counts are not aligned"
            )


def adapt_qt_model_inputs(
    split: QtTemporalDatasetSplit,
    policy: QtModelInputAdaptationPolicy | None = None,
) -> QtModelInputAdaptationResult:
    """Adapt one frozen split without re-splitting or learning representations."""
    _validate_source(split)
    policy = policy or QtModelInputAdaptationPolicy.create()
    if not isinstance(policy, QtModelInputAdaptationPolicy):
        raise TypeError("policy must be a QtModelInputAdaptationPolicy")
    source_specification = split.specification
    values = {
        "specification_version": "qt-model-input-adaptation-1.0.0",
        "source_split_identity_digest": split.split_identity_digest,
        "source_split_specification_digest": source_specification.specification_digest,
        "source_dataset_artifact_digest": (
            source_specification.source_dataset_artifact_digest
        ),
        "source_dataset_identity_digest": (
            source_specification.source_dataset_identity_digest
        ),
        "source_dataset_specification_digest": (
            source_specification.source_dataset_specification_digest
        ),
        "adaptation_policy_digest": policy.policy_digest,
    }
    specification = QtModelInputAdaptationSpecification(
        **values,
        specification_digest=QtModelInputAdaptationSpecification.calculate_digest(
            **values
        ),
    )
    code = _build_input(split, "code", specification)
    process = _build_input(split, "process", specification)
    text = _build_input(split, "text", specification)
    _validate_outputs(code, process, text)
    validation = QtModelInputAdaptationValidation(
        True,
        len(split.train),
        len(split.validation),
        len(split.test),
        ("code", "process", "text"),
        True,
        True,
        True,
    )
    identity = QtModelInputAdaptationResult.calculate_identity(
        specification, policy, code, process, text
    )
    return QtModelInputAdaptationResult(
        specification,
        policy,
        code,
        process,
        text,
        validation,
        split.split_identity_digest,
        identity,
    )
