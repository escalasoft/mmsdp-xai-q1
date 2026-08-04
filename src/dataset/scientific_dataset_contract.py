"""Immutable, project-independent scientific dataset contracts."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum, StrEnum
from pathlib import Path
from types import MappingProxyType
from typing import Any

__all__ = [
    "ScientificDatasetRole",
    "ScientificFeatureModality",
    "ScientificFeatureTemporalScope",
    "ScientificLeakageRisk",
    "ScientificFeatureDisposition",
    "ScientificDatasetIdentity",
    "ScientificObservationContract",
    "ScientificTargetContract",
    "ScientificTimestampContract",
    "ScientificFeatureProvenance",
    "ScientificDatasetSpecification",
    "ScientificDatasetValidationResult",
    "ScientificDatasetContractValidator",
    "load_scientific_dataset_specification",
]


class ScientificDatasetRole(StrEnum):
    IDENTIFIER = "identifier"
    TIMESTAMP = "timestamp"
    TARGET = "target"
    FEATURE = "feature"
    METADATA = "metadata"
    PARTITION = "partition"
    PROVENANCE = "provenance"


class ScientificFeatureModality(StrEnum):
    CODE = "code"
    PROCESS = "process"
    TEXT = "text"
    AST = "ast"
    CFG = "cfg"
    CALL_GRAPH = "call-graph"
    IMAGE = "image"


class ScientificFeatureTemporalScope(StrEnum):
    COMMIT_CURRENT = "commit-current"
    HISTORY_BEFORE_COMMIT = "history-before-commit"
    STATIC_PROJECT_METADATA = "static-project-metadata"
    FUTURE_DERIVED = "future-derived"
    POST_EVENT = "post-event"
    LABEL_DERIVED = "label-derived"
    UNKNOWN = "unknown"


class ScientificLeakageRisk(StrEnum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    PROHIBITED = "prohibited"
    REVIEW_REQUIRED = "review-required"


class ScientificFeatureDisposition(StrEnum):
    PERMITTED = "permitted"
    PROHIBITED = "prohibited"
    REVIEW_REQUIRED = "review-required"
    METADATA_ONLY = "metadata-only"
    IDENTIFIER_ONLY = "identifier-only"
    TARGET_ONLY = "target-only"
    TIMESTAMP_ONLY = "timestamp-only"


_EMPTY_METADATA: Mapping[str, object] = MappingProxyType({})
_BANNED_IDENTITY_KEYS = {
    "created_at",
    "creation_timestamp",
    "hostname",
    "local_path",
    "machine_name",
    "memory_address",
    "object_id",
    "runtime_timestamp",
    "username",
}


def _name(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value


def _enum(value: object, enum_type: type[Enum], field_name: str) -> Any:
    try:
        return enum_type(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"invalid {field_name}: {value!r}") from error


def _freeze(value: object, *, path: str = "metadata") -> object:
    if isinstance(value, Mapping):
        result: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(f"{path} keys must be strings")
            result[key] = _freeze(item, path=f"{path}.{key}")
        return MappingProxyType(result)
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item, path=path) for item in value)
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{path} must contain only finite numbers")
        return value
    raise TypeError(f"{path} must contain only deterministic JSON-compatible values")


def _metadata(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TypeError("metadata must be a mapping")
    return _freeze(value)  # type: ignore[return-value]


def _thaw(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    if isinstance(value, Enum):
        return value.value
    return value


def _bool(value: object, field_name: str) -> bool:
    if type(value) is not bool:
        raise TypeError(f"{field_name} must be bool")
    return value


def _binary_label(value: object, field_name: str) -> str | int:
    if isinstance(value, str):
        if not value.strip():
            raise ValueError(f"{field_name} must be a non-empty string or integer")
        return value
    if type(value) is int:
        return value
    raise TypeError(
        f"{field_name} must be a non-empty string or integer excluding bool"
    )


@dataclass(frozen=True, slots=True)
class ScientificDatasetIdentity:
    dataset_name: str
    dataset_version: str
    schema_version: str
    builder_version: str
    source_repository_name: str
    source_repository_url: str
    source_repository_revision: str
    observation_unit: str
    metadata: Mapping[str, object] = field(default_factory=lambda: _EMPTY_METADATA)

    def __post_init__(self) -> None:
        for item in (
            "dataset_name",
            "dataset_version",
            "schema_version",
            "builder_version",
            "source_repository_name",
            "source_repository_url",
            "source_repository_revision",
            "observation_unit",
        ):
            object.__setattr__(self, item, _name(getattr(self, item), item))
        if self.observation_unit != "commit":
            raise ValueError("observation_unit must equal 'commit'")
        frozen = _metadata(self.metadata)
        for key in frozen:
            if key.lower() in _BANNED_IDENTITY_KEYS:
                raise ValueError(f"identity metadata must not contain {key!r}")
        object.__setattr__(self, "metadata", frozen)

    def to_dict(self) -> dict[str, object]:
        return {name: _thaw(getattr(self, name)) for name in self.__dataclass_fields__}


@dataclass(frozen=True, slots=True)
class ScientificObservationContract:
    identifier_field: str
    identifier_role: ScientificDatasetRole
    identifier_unique: bool
    identifier_non_empty: bool
    timestamp_field: str
    target_field: str
    metadata: Mapping[str, object] = field(default_factory=lambda: _EMPTY_METADATA)

    def __post_init__(self) -> None:
        for item in ("identifier_field", "timestamp_field", "target_field"):
            object.__setattr__(self, item, _name(getattr(self, item), item))
        object.__setattr__(
            self,
            "identifier_role",
            _enum(self.identifier_role, ScientificDatasetRole, "identifier_role"),
        )
        if self.identifier_role is not ScientificDatasetRole.IDENTIFIER:
            raise ValueError("identifier_role must be identifier")
        if not _bool(self.identifier_unique, "identifier_unique") or not _bool(
            self.identifier_non_empty, "identifier_non_empty"
        ):
            raise ValueError("identifier must be unique and non-empty")
        if len({self.identifier_field, self.timestamp_field, self.target_field}) != 3:
            raise ValueError(
                "identifier, timestamp, and target fields must be distinct"
            )
        object.__setattr__(self, "metadata", _metadata(self.metadata))

    def to_dict(self) -> dict[str, object]:
        return {name: _thaw(getattr(self, name)) for name in self.__dataclass_fields__}


@dataclass(frozen=True, slots=True)
class ScientificTargetContract:
    field_name: str
    target_type: str
    negative_label: object
    positive_label: object
    positive_semantics: str
    negative_semantics: str
    derivation_policy: str
    allowed_source_roles: tuple[ScientificDatasetRole, ...]
    prohibited_feature_reuse: bool
    metadata: Mapping[str, object] = field(default_factory=lambda: _EMPTY_METADATA)

    def __post_init__(self) -> None:
        object.__setattr__(self, "field_name", _name(self.field_name, "field_name"))
        if self.target_type != "binary":
            raise ValueError("target_type must be 'binary'")
        negative_label = _binary_label(self.negative_label, "negative_label")
        positive_label = _binary_label(self.positive_label, "positive_label")
        if negative_label == positive_label:
            raise ValueError("positive and negative labels must be distinct")
        object.__setattr__(self, "negative_label", negative_label)
        object.__setattr__(self, "positive_label", positive_label)
        positive = _name(self.positive_semantics, "positive_semantics")
        if "defect-prone commit" not in positive.lower():
            raise ValueError("positive_semantics must identify defect-prone commits")
        object.__setattr__(
            self,
            "negative_semantics",
            _name(self.negative_semantics, "negative_semantics"),
        )
        policy = _name(self.derivation_policy, "derivation_policy")
        if "separate" not in policy.lower() or "feature" not in policy.lower():
            raise ValueError(
                "derivation_policy must separate target and feature construction"
            )
        roles = tuple(
            _enum(value, ScientificDatasetRole, "allowed_source_roles")
            for value in self.allowed_source_roles
        )
        if not roles:
            raise ValueError("allowed_source_roles must not be empty")
        object.__setattr__(self, "allowed_source_roles", roles)
        if not _bool(self.prohibited_feature_reuse, "prohibited_feature_reuse"):
            raise ValueError("prohibited_feature_reuse must be true")
        object.__setattr__(self, "metadata", _metadata(self.metadata))

    def to_dict(self) -> dict[str, object]:
        return {name: _thaw(getattr(self, name)) for name in self.__dataclass_fields__}


@dataclass(frozen=True, slots=True)
class ScientificTimestampContract:
    field_name: str
    timezone_policy: str
    ordering_policy: str
    missing_allowed: bool
    duplicate_timestamp_policy: str
    metadata: Mapping[str, object] = field(default_factory=lambda: _EMPTY_METADATA)

    def __post_init__(self) -> None:
        object.__setattr__(self, "field_name", _name(self.field_name, "field_name"))
        object.__setattr__(
            self, "timezone_policy", _name(self.timezone_policy, "timezone_policy")
        )
        ordering = _name(self.ordering_policy, "ordering_policy")
        if (
            "chronological" not in ordering.lower()
            or "ascending" not in ordering.lower()
        ):
            raise ValueError(
                "ordering_policy must enforce chronological ascending order"
            )
        if _bool(self.missing_allowed, "missing_allowed"):
            raise ValueError("missing_allowed must be false")
        duplicate = _name(self.duplicate_timestamp_policy, "duplicate_timestamp_policy")
        if "allow" in duplicate.lower() and not all(
            word in duplicate.lower() for word in ("identifier", "secondary", "order")
        ):
            raise ValueError(
                "allowed duplicate timestamps require deterministic secondary "
                "ordering by observation identifier"
            )
        object.__setattr__(self, "metadata", _metadata(self.metadata))

    def to_dict(self) -> dict[str, object]:
        return {name: _thaw(getattr(self, name)) for name in self.__dataclass_fields__}


@dataclass(frozen=True, slots=True)
class ScientificFeatureProvenance:
    feature_name: str
    modality: ScientificFeatureModality
    source_artifact: str
    source_fields: tuple[str, ...]
    temporal_scope: ScientificFeatureTemporalScope
    availability_time: str
    derivation_summary: str
    uses_target: bool
    uses_issue_linking_evidence: bool
    uses_future_information: bool
    uses_post_event_information: bool
    computed_using_full_dataset: bool
    leakage_risk: ScientificLeakageRisk
    disposition: ScientificFeatureDisposition
    rationale: str
    allowed_in_complete_scenario: bool
    allowed_in_leakage_controlled_scenario: bool
    metadata: Mapping[str, object] = field(default_factory=lambda: _EMPTY_METADATA)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "feature_name", _name(self.feature_name, "feature_name")
        )
        object.__setattr__(
            self,
            "modality",
            _enum(self.modality, ScientificFeatureModality, "modality"),
        )
        object.__setattr__(
            self, "source_artifact", _name(self.source_artifact, "source_artifact")
        )
        fields = tuple(self.source_fields)
        if any(not isinstance(item, str) or not item.strip() for item in fields):
            raise ValueError("source_fields must contain non-empty strings")
        object.__setattr__(self, "source_fields", fields)
        object.__setattr__(
            self,
            "temporal_scope",
            _enum(
                self.temporal_scope, ScientificFeatureTemporalScope, "temporal_scope"
            ),
        )
        object.__setattr__(
            self,
            "availability_time",
            _name(self.availability_time, "availability_time"),
        )
        object.__setattr__(
            self,
            "derivation_summary",
            _name(self.derivation_summary, "derivation_summary"),
        )
        object.__setattr__(
            self,
            "leakage_risk",
            _enum(self.leakage_risk, ScientificLeakageRisk, "leakage_risk"),
        )
        object.__setattr__(
            self,
            "disposition",
            _enum(self.disposition, ScientificFeatureDisposition, "disposition"),
        )
        object.__setattr__(self, "rationale", _name(self.rationale, "rationale"))
        if (self.disposition is ScientificFeatureDisposition.PROHIBITED) != (
            self.leakage_risk is ScientificLeakageRisk.PROHIBITED
        ):
            raise ValueError(
                "prohibited disposition and prohibited leakage risk must coincide"
            )
        if (
            self.disposition is ScientificFeatureDisposition.REVIEW_REQUIRED
            and self.leakage_risk
            not in {
                ScientificLeakageRisk.MEDIUM,
                ScientificLeakageRisk.HIGH,
                ScientificLeakageRisk.REVIEW_REQUIRED,
            }
        ):
            raise ValueError(
                "review-required disposition requires medium, high, or "
                "review-required leakage risk"
            )
        if (
            self.leakage_risk is ScientificLeakageRisk.HIGH
            and self.disposition is ScientificFeatureDisposition.PERMITTED
        ):
            raise ValueError("high leakage risk cannot use permitted disposition")
        if (
            self.disposition is ScientificFeatureDisposition.PERMITTED
            and self.leakage_risk
            in {
                ScientificLeakageRisk.PROHIBITED,
                ScientificLeakageRisk.REVIEW_REQUIRED,
            }
        ):
            raise ValueError(
                "permitted disposition cannot use prohibited or review-required risk"
            )
        flags = (
            "uses_target",
            "uses_issue_linking_evidence",
            "uses_future_information",
            "uses_post_event_information",
            "computed_using_full_dataset",
            "allowed_in_complete_scenario",
            "allowed_in_leakage_controlled_scenario",
        )
        for item in flags:
            _bool(getattr(self, item), item)
        prohibited_scope = self.temporal_scope in {
            ScientificFeatureTemporalScope.FUTURE_DERIVED,
            ScientificFeatureTemporalScope.POST_EVENT,
            ScientificFeatureTemporalScope.LABEL_DERIVED,
        }
        if (
            self.uses_target
            or self.uses_future_information
            or self.uses_post_event_information
            or prohibited_scope
        ) and self.disposition is not ScientificFeatureDisposition.PROHIBITED:
            raise ValueError(
                "target-, future-, post-event-, and label-derived features "
                "must be prohibited"
            )
        if self.computed_using_full_dataset and self.disposition not in {
            ScientificFeatureDisposition.PROHIBITED,
            ScientificFeatureDisposition.METADATA_ONLY,
        }:
            raise ValueError(
                "full-dataset aggregates must be prohibited or metadata-only"
            )
        if self.disposition is ScientificFeatureDisposition.PROHIBITED and (
            self.allowed_in_complete_scenario
            or self.allowed_in_leakage_controlled_scenario
        ):
            raise ValueError("prohibited features cannot be enabled")
        if (
            self.allowed_in_leakage_controlled_scenario
            and not self.allowed_in_complete_scenario
        ):
            raise ValueError(
                "leakage-controlled inclusion implies complete-scenario inclusion"
            )
        if (
            self.disposition is ScientificFeatureDisposition.REVIEW_REQUIRED
            and self.allowed_in_leakage_controlled_scenario
        ):
            raise ValueError(
                "review-required features cannot be enabled in "
                "leakage-controlled scenario"
            )
        if self.disposition in {
            ScientificFeatureDisposition.METADATA_ONLY,
            ScientificFeatureDisposition.IDENTIFIER_ONLY,
            ScientificFeatureDisposition.TARGET_ONLY,
            ScientificFeatureDisposition.TIMESTAMP_ONLY,
        } and (
            self.allowed_in_complete_scenario
            or self.allowed_in_leakage_controlled_scenario
        ):
            raise ValueError("non-feature fields cannot be supplied to model fitting")
        object.__setattr__(self, "metadata", _metadata(self.metadata))

    def to_dict(self) -> dict[str, object]:
        return {name: _thaw(getattr(self, name)) for name in self.__dataclass_fields__}


@dataclass(frozen=True, slots=True)
class ScientificDatasetSpecification:
    identity: ScientificDatasetIdentity
    observation: ScientificObservationContract
    target: ScientificTargetContract
    timestamp: ScientificTimestampContract
    required_modalities: tuple[ScientificFeatureModality, ...]
    optional_modalities: tuple[ScientificFeatureModality, ...]
    features: tuple[ScientificFeatureProvenance, ...]
    prohibited_feature_name_patterns: tuple[str, ...]
    review_required_feature_name_patterns: tuple[str, ...]
    leakage_policy_version: str
    manifest_schema_version: str
    minimum_feature_count: int
    metadata: Mapping[str, object] = field(default_factory=lambda: _EMPTY_METADATA)

    def __post_init__(self) -> None:
        if (
            not isinstance(self.identity, ScientificDatasetIdentity)
            or not isinstance(self.observation, ScientificObservationContract)
            or not isinstance(self.target, ScientificTargetContract)
            or not isinstance(self.timestamp, ScientificTimestampContract)
        ):
            raise TypeError(
                "identity, observation, target, and timestamp must use "
                "scientific contracts"
            )
        required = tuple(
            _enum(value, ScientificFeatureModality, "required_modalities")
            for value in self.required_modalities
        )
        optional = tuple(
            _enum(value, ScientificFeatureModality, "optional_modalities")
            for value in self.optional_modalities
        )
        if len(required) != len(set(required)) or len(optional) != len(set(optional)):
            raise ValueError("modalities must not contain duplicates")
        if set(required) & set(optional):
            raise ValueError("required and optional modalities must not overlap")
        core = {
            ScientificFeatureModality.CODE,
            ScientificFeatureModality.PROCESS,
            ScientificFeatureModality.TEXT,
        }
        if not core.issubset(required):
            raise ValueError("required_modalities must contain code, process, and text")
        features = tuple(self.features)
        if not features or any(
            not isinstance(item, ScientificFeatureProvenance) for item in features
        ):
            raise ValueError("features must contain scientific feature provenance")
        names = [item.feature_name for item in features]
        if len(names) != len(set(names)):
            raise ValueError("feature names must be unique")
        prohibited = self._patterns(
            self.prohibited_feature_name_patterns, "prohibited_feature_name_patterns"
        )
        review = self._patterns(
            self.review_required_feature_name_patterns,
            "review_required_feature_name_patterns",
            empty_allowed=True,
        )
        if (
            type(self.minimum_feature_count) is not int
            or self.minimum_feature_count <= 0
        ):
            raise ValueError("minimum_feature_count must be a positive integer")
        object.__setattr__(self, "required_modalities", required)
        object.__setattr__(self, "optional_modalities", optional)
        object.__setattr__(self, "features", features)
        object.__setattr__(self, "prohibited_feature_name_patterns", prohibited)
        object.__setattr__(self, "review_required_feature_name_patterns", review)
        object.__setattr__(
            self,
            "leakage_policy_version",
            _name(self.leakage_policy_version, "leakage_policy_version"),
        )
        object.__setattr__(
            self,
            "manifest_schema_version",
            _name(self.manifest_schema_version, "manifest_schema_version"),
        )
        object.__setattr__(self, "metadata", _metadata(self.metadata))

    @staticmethod
    def _patterns(
        values: Sequence[str], name: str, *, empty_allowed: bool = False
    ) -> tuple[str, ...]:
        patterns = tuple(values)
        if not patterns and not empty_allowed:
            raise ValueError(f"{name} must not be empty")
        for pattern in patterns:
            if (
                not isinstance(pattern, str)
                or not pattern
                or pattern != pattern.lower()
            ):
                raise ValueError(f"{name} must contain lowercase non-empty patterns")
            try:
                re.compile(pattern)
            except re.error as error:
                raise ValueError(
                    f"invalid feature-name pattern: {pattern!r}"
                ) from error
        return patterns

    def to_dict(self) -> dict[str, object]:
        return {
            "identity": self.identity.to_dict(),
            "observation": self.observation.to_dict(),
            "target": self.target.to_dict(),
            "timestamp": self.timestamp.to_dict(),
            "required_modalities": _thaw(self.required_modalities),
            "optional_modalities": _thaw(self.optional_modalities),
            "features": [item.to_dict() for item in self.features],
            "prohibited_feature_name_patterns": list(
                self.prohibited_feature_name_patterns
            ),
            "review_required_feature_name_patterns": list(
                self.review_required_feature_name_patterns
            ),
            "leakage_policy_version": self.leakage_policy_version,
            "manifest_schema_version": self.manifest_schema_version,
            "minimum_feature_count": self.minimum_feature_count,
            "metadata": _thaw(self.metadata),
        }

    def permitted_features(self) -> tuple[ScientificFeatureProvenance, ...]:
        """Return complete-scenario-enabled candidate model features.

        This may include explicitly enabled review-required sensitivity
        candidates; it does not mean every result has disposition permitted.
        """

        return tuple(
            item for item in self.features if item.allowed_in_complete_scenario
        )

    def leakage_controlled_features(self) -> tuple[ScientificFeatureProvenance, ...]:
        """Return explicitly enabled leakage-controlled candidate features."""

        return tuple(
            item
            for item in self.features
            if item.allowed_in_leakage_controlled_scenario
        )

    def prohibited_features(self) -> tuple[ScientificFeatureProvenance, ...]:
        """Return candidates whose scientific disposition is prohibited."""

        return tuple(
            item
            for item in self.features
            if item.disposition is ScientificFeatureDisposition.PROHIBITED
        )

    def review_required_features(self) -> tuple[ScientificFeatureProvenance, ...]:
        """Return candidates requiring scientific review before general use."""

        return tuple(
            item
            for item in self.features
            if item.disposition is ScientificFeatureDisposition.REVIEW_REQUIRED
        )

    def feature_by_name(self, name: str) -> ScientificFeatureProvenance:
        for feature in self.features:
            if feature.feature_name == name:
                return feature
        raise KeyError(name)

    def canonical_json(self) -> str:
        return json.dumps(
            self.to_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )

    def scientific_digest(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class ScientificDatasetValidationResult:
    is_valid: bool
    error_count: int
    warning_count: int
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    checked_feature_count: int
    permitted_feature_count: int
    leakage_controlled_feature_count: int
    prohibited_feature_count: int
    review_required_feature_count: int
    specification_digest: str
    metadata: Mapping[str, object] = field(default_factory=lambda: _EMPTY_METADATA)

    def __post_init__(self) -> None:
        object.__setattr__(self, "errors", tuple(self.errors))
        object.__setattr__(self, "warnings", tuple(self.warnings))
        if self.error_count != len(self.errors) or self.warning_count != len(
            self.warnings
        ):
            raise ValueError("validation counts must align with errors and warnings")
        if self.is_valid != (not self.errors):
            raise ValueError("is_valid must be true exactly when errors is empty")
        for name in (
            "error_count",
            "warning_count",
            "checked_feature_count",
            "permitted_feature_count",
            "leakage_controlled_feature_count",
            "prohibited_feature_count",
            "review_required_feature_count",
        ):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        object.__setattr__(
            self,
            "specification_digest",
            _name(self.specification_digest, "specification_digest"),
        )
        object.__setattr__(self, "metadata", _metadata(self.metadata))

    def to_dict(self) -> dict[str, object]:
        return {name: _thaw(getattr(self, name)) for name in self.__dataclass_fields__}


class ScientificDatasetContractValidator:
    """Perform deterministic semantic validation without repairing input."""

    def validate(
        self, specification: ScientificDatasetSpecification
    ) -> ScientificDatasetValidationResult:
        if not isinstance(specification, ScientificDatasetSpecification):
            raise TypeError("specification must be ScientificDatasetSpecification")
        errors: list[str] = []
        warnings: list[str] = []
        features = specification.features
        if len(features) < specification.minimum_feature_count:
            errors.append("minimum feature count is not satisfied")
        if not specification.prohibited_feature_name_patterns:
            errors.append("prohibited feature-name pattern policy is empty")
        if not specification.manifest_schema_version.strip():
            errors.append("manifest schema version is missing")
        if (
            specification.observation.timestamp_field
            != specification.timestamp.field_name
            or specification.observation.target_field != specification.target.field_name
        ):
            errors.append(
                "observation, target, and timestamp contracts are not aligned"
            )
        for feature in features:
            lower_name = feature.feature_name.lower()
            enabled = (
                feature.allowed_in_complete_scenario
                or feature.allowed_in_leakage_controlled_scenario
            )
            if (
                feature.disposition is ScientificFeatureDisposition.PROHIBITED
                and enabled
            ):
                errors.append(f"{feature.feature_name}: prohibited feature is enabled")
            if (
                feature.disposition is ScientificFeatureDisposition.REVIEW_REQUIRED
                and feature.allowed_in_leakage_controlled_scenario
            ):
                errors.append(
                    f"{feature.feature_name}: review-required feature is enabled "
                    "in leakage-controlled scenario"
                )
            if feature.uses_target and enabled:
                errors.append(
                    f"{feature.feature_name}: target-derived feature is enabled"
                )
            if (
                feature.uses_future_information
                or feature.temporal_scope
                is ScientificFeatureTemporalScope.FUTURE_DERIVED
            ) and enabled:
                errors.append(
                    f"{feature.feature_name}: future-derived feature is enabled"
                )
            if (
                feature.uses_post_event_information
                or feature.temporal_scope is ScientificFeatureTemporalScope.POST_EVENT
            ) and enabled:
                errors.append(f"{feature.feature_name}: post-event feature is enabled")
            if feature.computed_using_full_dataset and enabled:
                errors.append(
                    f"{feature.feature_name}: full-dataset aggregate is enabled "
                    "for training"
                )
            if (
                feature.uses_issue_linking_evidence
                and enabled
                and not self._admissible_historical_issue_feature(feature)
            ):
                errors.append(
                    f"{feature.feature_name}: issue-linking evidence lacks "
                    "independent prior-time justification"
                )
            for kind, pattern in (
                ("identifier", r"(^|_)(commit_?hash|identifier|id)($|_)"),
                ("timestamp", r"(^|_)(timestamp|date|time)($|_)"),
                ("target", r"(^|_)(target|label|is_bug|is_buggy|is_defect_prone)($|_)"),
                ("partition", r"(^|_)(split|partition|fold)($|_)"),
            ):
                if enabled and re.search(pattern, lower_name):
                    errors.append(
                        f"{feature.feature_name}: {kind}-like field is enabled "
                        "as a predictor"
                    )
            if enabled and any(
                re.search(pattern, lower_name)
                for pattern in specification.prohibited_feature_name_patterns
            ):
                errors.append(
                    f"{feature.feature_name}: matches prohibited feature-name policy"
                )
            if feature.temporal_scope is ScientificFeatureTemporalScope.UNKNOWN:
                warnings.append(f"{feature.feature_name}: temporal scope is unknown")
            if feature.leakage_risk is ScientificLeakageRisk.MEDIUM:
                warnings.append(f"{feature.feature_name}: leakage risk is medium")
            if feature.disposition is ScientificFeatureDisposition.REVIEW_REQUIRED:
                warnings.append(f"{feature.feature_name}: feature requires review")
            if feature.source_artifact.lower() in {"unknown", "unclassified"}:
                warnings.append(
                    f"{feature.feature_name}: source artifact is unclassified"
                )
            if (
                not feature.source_fields
                or not feature.derivation_summary.strip()
                or not feature.availability_time.strip()
            ):
                warnings.append(
                    f"{feature.feature_name}: provenance detail is incomplete"
                )
        errors = sorted(set(errors))
        warnings = sorted(set(warnings))
        return ScientificDatasetValidationResult(
            is_valid=not errors,
            error_count=len(errors),
            warning_count=len(warnings),
            errors=tuple(errors),
            warnings=tuple(warnings),
            checked_feature_count=len(features),
            permitted_feature_count=len(specification.permitted_features()),
            leakage_controlled_feature_count=len(
                specification.leakage_controlled_features()
            ),
            prohibited_feature_count=len(specification.prohibited_features()),
            review_required_feature_count=len(specification.review_required_features()),
            specification_digest=specification.scientific_digest(),
            metadata={
                "validator": "scientific-dataset-contract",
                "validation_order": "lexicographic",
            },
        )

    @staticmethod
    def _admissible_historical_issue_feature(
        feature: ScientificFeatureProvenance,
    ) -> bool:
        required_controls = {
            "temporal_cutoff_policy",
            "target_independence",
            "current_target_excluded",
            "future_links_excluded",
            "linkage_policy_version",
        }
        metadata = feature.metadata
        return (
            feature.temporal_scope
            is ScientificFeatureTemporalScope.HISTORY_BEFORE_COMMIT
            and not feature.uses_target
            and not feature.uses_future_information
            and not feature.uses_post_event_information
            and not feature.computed_using_full_dataset
            and set(metadata) == required_controls
            and metadata.get("temporal_cutoff_policy") == "strictly-before-observation"
            and metadata.get("target_independence") is True
            and metadata.get("current_target_excluded") is True
            and metadata.get("future_links_excluded") is True
            and isinstance(metadata.get("linkage_policy_version"), str)
            and bool(str(metadata["linkage_policy_version"]).strip())
        )


_TOP_LEVEL_FIELDS = {
    "identity",
    "observation",
    "target",
    "timestamp",
    "required_modalities",
    "optional_modalities",
    "features",
    "prohibited_feature_name_patterns",
    "review_required_feature_name_patterns",
    "leakage_policy_version",
    "manifest_schema_version",
    "minimum_feature_count",
    "metadata",
}


def _strict_fields(
    data: Mapping[str, object], expected: set[str], context: str
) -> None:
    unknown = sorted(set(data) - expected)
    missing = sorted(expected - set(data))
    if unknown:
        raise ValueError(f"unknown {context} fields: {', '.join(unknown)}")
    if missing:
        raise ValueError(f"missing required {context} fields: {', '.join(missing)}")


def load_scientific_dataset_specification(
    path: str | Path,
) -> ScientificDatasetSpecification:
    """Load a strict UTF-8 JSON scientific dataset specification."""
    with Path(path).open(encoding="utf-8") as source:
        parsed = json.load(
            source,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"non-finite JSON value: {value}")
            ),
        )
    if not isinstance(parsed, Mapping):
        raise TypeError("scientific dataset specification must be a JSON object")
    _strict_fields(parsed, _TOP_LEVEL_FIELDS, "top-level")

    def mapping(name: str) -> dict[str, object]:
        value = parsed[name]
        if not isinstance(value, Mapping):
            raise TypeError(f"{name} must be an object")
        return dict(value)

    identity_data = mapping("identity")
    observation_data = mapping("observation")
    target_data = mapping("target")
    timestamp_data = mapping("timestamp")
    _strict_fields(
        identity_data, set(ScientificDatasetIdentity.__dataclass_fields__), "identity"
    )
    _strict_fields(
        observation_data,
        set(ScientificObservationContract.__dataclass_fields__),
        "observation",
    )
    _strict_fields(
        target_data, set(ScientificTargetContract.__dataclass_fields__), "target"
    )
    _strict_fields(
        timestamp_data,
        set(ScientificTimestampContract.__dataclass_fields__),
        "timestamp",
    )
    raw_features = parsed["features"]
    if not isinstance(raw_features, list):
        raise TypeError("features must be an array")
    features = []
    for index, raw in enumerate(raw_features):
        if not isinstance(raw, Mapping):
            raise TypeError(f"features[{index}] must be an object")
        data = dict(raw)
        _strict_fields(
            data,
            set(ScientificFeatureProvenance.__dataclass_fields__),
            f"features[{index}]",
        )
        features.append(ScientificFeatureProvenance(**data))
    return ScientificDatasetSpecification(
        identity=ScientificDatasetIdentity(**identity_data),
        observation=ScientificObservationContract(**observation_data),
        target=ScientificTargetContract(**target_data),
        timestamp=ScientificTimestampContract(**timestamp_data),
        required_modalities=tuple(parsed["required_modalities"]),
        optional_modalities=tuple(parsed["optional_modalities"]),
        features=tuple(features),
        prohibited_feature_name_patterns=tuple(
            parsed["prohibited_feature_name_patterns"]
        ),
        review_required_feature_name_patterns=tuple(
            parsed["review_required_feature_name_patterns"]
        ),
        leakage_policy_version=parsed["leakage_policy_version"],
        manifest_schema_version=parsed["manifest_schema_version"],
        minimum_feature_count=parsed["minimum_feature_count"],
        metadata=parsed["metadata"],
    )
