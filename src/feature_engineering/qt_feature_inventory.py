"""Deterministic, leakage-safe inventory of candidate Qt predictive features."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType

from dataset.scientific_builder_contracts import (
    ScientificArtifactReference,
    ScientificArtifactRole,
)
from dataset.scientific_dataset_contract import ScientificFeatureModality

__all__ = [
    "QtFeatureDataType",
    "QtFeatureMissingPolicy",
    "QtFeatureLeakageClassification",
    "QtFeatureAdmissibility",
    "QtFeatureDefinition",
    "QtFeatureInventory",
    "build_qt_feature_inventory",
]


class QtFeatureDataType(StrEnum):
    NON_NEGATIVE_INTEGER = "non-negative-integer"
    BOOLEAN = "boolean"
    UTF8_TEXT = "utf-8-text"


class QtFeatureMissingPolicy(StrEnum):
    NOT_MISSING = "not-missing"
    UNAVAILABLE = "unavailable-no-value-construction"


class QtFeatureLeakageClassification(StrEnum):
    ADMISSIBLE_COMMIT_CURRENT = "admissible-commit-current"
    ADMISSIBLE_STRICTLY_PRIOR = "admissible-strictly-prior"
    PROHIBITED_TARGET_DERIVED = "prohibited-target-derived"
    PROHIBITED_KEYWORD_PROXY = "prohibited-keyword-proxy"
    PROHIBITED_FUTURE_DERIVED = "prohibited-future-derived"
    UNAVAILABLE_UPSTREAM = "unavailable-upstream"


class QtFeatureAdmissibility(StrEnum):
    ADMISSIBLE = "admissible"
    INADMISSIBLE = "inadmissible"
    UNAVAILABLE = "unavailable"


_MODALITY_ORDER = {
    ScientificFeatureModality.CODE: 0,
    ScientificFeatureModality.PROCESS: 1,
    ScientificFeatureModality.TEXT: 2,
}
_ALLOWED_SOURCE_ROLES = frozenset(
    {ScientificArtifactRole.COMMIT_ARTIFACT, ScientificArtifactRole.CODE_FEATURE}
)
_PROHIBITED_SOURCE_ROLES = frozenset(
    {
        ScientificArtifactRole.ISSUE_ARTIFACT,
        ScientificArtifactRole.TARGET_EVIDENCE,
        ScientificArtifactRole.DEFECT_INDUCING_CANDIDATE,
        ScientificArtifactRole.TARGET_ASSIGNMENT,
        ScientificArtifactRole.DATASET,
    }
)
_PROHIBITED_KEYS = frozenset(
    {
        "bug_confidence",
        "candidate_attribution",
        "candidate_record",
        "defect_inducing_candidate",
        "future_bug_count",
        "future_fix_count",
        "issue_link",
        "issue_linking",
        "label",
        "label_confidence",
        "post_release_defect_count",
        "target",
        "target_assignment",
        "target_evidence",
        "target_probability",
    }
)
_KEYWORD_FEATURE = re.compile(
    r"(^|_)(bug|buggy|defect|fix|fixed|fixing|issue)_?(keyword|kw|indicator|flag)($|_)"
    r"|(^|_)(has|contains)_?(bug|defect|fix|issue)($|_)"
)


def _key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _canonical_digest(value: object) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class QtFeatureDefinition:
    feature_id: str
    modality: ScientificFeatureModality
    upstream_artifact: str
    source_fields: tuple[str, ...]
    temporal_availability_rule: str
    construction_rule: str
    data_type: QtFeatureDataType
    missing_value_policy: QtFeatureMissingPolicy
    leakage_classification: QtFeatureLeakageClassification
    admissibility: QtFeatureAdmissibility
    exclusion_reason: str | None

    def __post_init__(self) -> None:
        identifier = _key(_text(self.feature_id, "feature_id"))
        if identifier != self.feature_id:
            raise ValueError("feature_id must use canonical snake_case")
        object.__setattr__(self, "modality", ScientificFeatureModality(self.modality))
        if self.modality not in _MODALITY_ORDER:
            raise ValueError("Qt inventory modality must be code, process, or text")
        object.__setattr__(
            self,
            "upstream_artifact",
            _text(self.upstream_artifact, "upstream_artifact"),
        )
        fields = tuple(_text(item, "source_fields") for item in self.source_fields)
        object.__setattr__(self, "source_fields", fields)
        for name in ("temporal_availability_rule", "construction_rule"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        object.__setattr__(self, "data_type", QtFeatureDataType(self.data_type))
        object.__setattr__(
            self,
            "missing_value_policy",
            QtFeatureMissingPolicy(self.missing_value_policy),
        )
        object.__setattr__(
            self,
            "leakage_classification",
            QtFeatureLeakageClassification(self.leakage_classification),
        )
        object.__setattr__(
            self, "admissibility", QtFeatureAdmissibility(self.admissibility)
        )
        if self.admissibility is QtFeatureAdmissibility.ADMISSIBLE:
            if self.exclusion_reason is not None:
                raise ValueError("admissible features cannot have an exclusion reason")
            if not fields:
                raise ValueError("admissible features require source fields")
        elif (
            not isinstance(self.exclusion_reason, str)
            or not self.exclusion_reason.strip()
        ):
            raise ValueError("non-admissible features require an exclusion reason")
        if self.admissibility is QtFeatureAdmissibility.UNAVAILABLE and (
            self.missing_value_policy is not QtFeatureMissingPolicy.UNAVAILABLE
            or self.leakage_classification
            is not QtFeatureLeakageClassification.UNAVAILABLE_UPSTREAM
        ):
            raise ValueError("unavailable features require unavailable policies")
        _validate_definition_firewall(self)

    def to_dict(self) -> dict[str, object]:
        return {
            "feature_id": self.feature_id,
            "modality": self.modality.value,
            "upstream_artifact": self.upstream_artifact,
            "source_fields": list(self.source_fields),
            "temporal_availability_rule": self.temporal_availability_rule,
            "construction_rule": self.construction_rule,
            "data_type": self.data_type.value,
            "missing_value_policy": self.missing_value_policy.value,
            "leakage_classification": self.leakage_classification.value,
            "admissibility": self.admissibility.value,
            "exclusion_reason": self.exclusion_reason,
        }


def _validate_definition_firewall(feature: QtFeatureDefinition) -> None:
    keys = {_key(feature.feature_id), _key(feature.upstream_artifact)}
    keys.update(_key(field) for field in feature.source_fields)
    prohibited_concept = bool(keys & _PROHIBITED_KEYS) or bool(
        _KEYWORD_FEATURE.search(feature.feature_id)
    )
    if prohibited_concept and not (
        feature.admissibility is QtFeatureAdmissibility.INADMISSIBLE
        and not feature.source_fields
        and feature.upstream_artifact.startswith("prohibited:")
    ):
        raise ValueError("feature definition consumes a prohibited predictive source")
    temporal = feature.temporal_availability_rule.lower()
    if feature.modality is ScientificFeatureModality.PROCESS:
        if "future" in temporal or "after candidate" in temporal:
            raise ValueError("process features cannot use future information")
        if feature.admissibility is QtFeatureAdmissibility.ADMISSIBLE and not (
            "strictly before" in temporal or "at candidate commit" in temporal
        ):
            raise ValueError("admissible process features require an explicit cutoff")


@dataclass(frozen=True, slots=True)
class QtFeatureInventory:
    source_artifacts: tuple[ScientificArtifactReference, ...]
    features: tuple[QtFeatureDefinition, ...]
    inventory_digest: str

    def __post_init__(self) -> None:
        artifacts = tuple(self.source_artifacts)
        if not artifacts:
            raise ValueError("source_artifacts must not be empty")
        if any(not isinstance(item, ScientificArtifactReference) for item in artifacts):
            raise TypeError("source_artifacts must contain artifact references")
        if any(item.artifact_role in _PROHIBITED_SOURCE_ROLES for item in artifacts):
            raise ValueError(
                "target, candidate, issue, and dataset artifacts are prohibited"
            )
        if any(item.artifact_role not in _ALLOWED_SOURCE_ROLES for item in artifacts):
            raise ValueError("source artifact role is not approved for Qt features")
        artifact_names = tuple(item.artifact_name for item in artifacts)
        if artifact_names != tuple(sorted(artifact_names)) or len(
            artifact_names
        ) != len(set(artifact_names)):
            raise ValueError(
                "source_artifacts must be uniquely and canonically ordered"
            )
        features = tuple(self.features)
        expected = tuple(
            sorted(
                features,
                key=lambda item: (_MODALITY_ORDER[item.modality], item.feature_id),
            )
        )
        if features != expected:
            raise ValueError(
                "features must use canonical modality and identifier ordering"
            )
        names = tuple(item.feature_id for item in features)
        if len(names) != len(set(names)):
            raise ValueError("feature identifiers must be unique")
        bound = set(artifact_names)
        if any(
            item.admissibility is QtFeatureAdmissibility.ADMISSIBLE
            and item.upstream_artifact not in bound
            for item in features
        ):
            raise ValueError(
                "admissible features must bind to an approved source artifact"
            )
        object.__setattr__(self, "source_artifacts", artifacts)
        object.__setattr__(self, "features", features)
        if self.inventory_digest != self.calculate_digest(artifacts, features):
            raise ValueError(
                "inventory_digest must identify canonical scientific content"
            )

    @staticmethod
    def calculate_digest(
        source_artifacts: Sequence[ScientificArtifactReference],
        features: Sequence[QtFeatureDefinition],
    ) -> str:
        return _canonical_digest(
            {
                "source_artifacts": [item.to_dict() for item in source_artifacts],
                "features": [item.to_dict() for item in features],
            }
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "source_artifacts": [item.to_dict() for item in self.source_artifacts],
            "features": [item.to_dict() for item in self.features],
            "inventory_digest": self.inventory_digest,
        }

    def by_modality(
        self,
    ) -> Mapping[ScientificFeatureModality, tuple[QtFeatureDefinition, ...]]:
        return MappingProxyType(
            {
                modality: tuple(
                    item for item in self.features if item.modality is modality
                )
                for modality in _MODALITY_ORDER
            }
        )


def _feature(
    feature_id: str,
    modality: ScientificFeatureModality,
    artifact: str,
    fields: tuple[str, ...],
    rule: str,
    construction: str,
    data_type: QtFeatureDataType,
) -> QtFeatureDefinition:
    return QtFeatureDefinition(
        feature_id,
        modality,
        artifact,
        fields,
        rule,
        construction,
        data_type,
        QtFeatureMissingPolicy.NOT_MISSING,
        QtFeatureLeakageClassification.ADMISSIBLE_COMMIT_CURRENT,
        QtFeatureAdmissibility.ADMISSIBLE,
        None,
    )


def build_qt_feature_inventory(
    commit_artifact: ScientificArtifactReference,
    diff_statistics_artifact: ScientificArtifactReference,
) -> QtFeatureInventory:
    """Build the fixed Sprint inventory from two approved, content-bound artifacts."""
    if commit_artifact.artifact_role is not ScientificArtifactRole.COMMIT_ARTIFACT:
        raise ValueError("commit_artifact must have commit-artifact role")
    if (
        diff_statistics_artifact.artifact_role
        is not ScientificArtifactRole.CODE_FEATURE
    ):
        raise ValueError("diff_statistics_artifact must have code-feature role")
    commit = commit_artifact.artifact_name
    stats = diff_statistics_artifact.artifact_name
    at_commit = "Available at candidate commit creation from its immutable Git object."
    from_diff = (
        "Available at candidate commit from its reproducible parent-relative diff."
    )
    features = [
        _feature(
            "binary_files",
            ScientificFeatureModality.CODE,
            stats,
            ("binary_files",),
            from_diff,
            "Use the per-commit binary_files structural count.",
            QtFeatureDataType.NON_NEGATIVE_INTEGER,
        ),
        _feature(
            "deletions",
            ScientificFeatureModality.CODE,
            stats,
            ("deletions",),
            from_diff,
            "Use the per-commit text-line deletion count; binary line counts "
            "remain excluded.",
            QtFeatureDataType.NON_NEGATIVE_INTEGER,
        ),
        _feature(
            "files_added",
            ScientificFeatureModality.CODE,
            stats,
            ("files_added",),
            from_diff,
            "Use the per-commit added-file count.",
            QtFeatureDataType.NON_NEGATIVE_INTEGER,
        ),
        _feature(
            "files_changed",
            ScientificFeatureModality.CODE,
            stats,
            ("files_changed",),
            from_diff,
            "Use the per-commit changed-file count.",
            QtFeatureDataType.NON_NEGATIVE_INTEGER,
        ),
        _feature(
            "files_copied",
            ScientificFeatureModality.CODE,
            stats,
            ("files_copied",),
            from_diff,
            "Use the per-commit copied-file count.",
            QtFeatureDataType.NON_NEGATIVE_INTEGER,
        ),
        _feature(
            "files_modified",
            ScientificFeatureModality.CODE,
            stats,
            ("files_modified",),
            from_diff,
            "Use the per-commit modified-file count.",
            QtFeatureDataType.NON_NEGATIVE_INTEGER,
        ),
        _feature(
            "files_removed",
            ScientificFeatureModality.CODE,
            stats,
            ("files_removed",),
            from_diff,
            "Use the per-commit removed-file count.",
            QtFeatureDataType.NON_NEGATIVE_INTEGER,
        ),
        _feature(
            "files_renamed",
            ScientificFeatureModality.CODE,
            stats,
            ("files_renamed",),
            from_diff,
            "Use the per-commit renamed-file count.",
            QtFeatureDataType.NON_NEGATIVE_INTEGER,
        ),
        _feature(
            "files_type_changed",
            ScientificFeatureModality.CODE,
            stats,
            ("files_type_changed",),
            from_diff,
            "Use the per-commit type-changed-file count.",
            QtFeatureDataType.NON_NEGATIVE_INTEGER,
        ),
        _feature(
            "has_binary_files",
            ScientificFeatureModality.CODE,
            stats,
            ("has_binary_files",),
            from_diff,
            "Use the deterministic binary-file presence marker.",
            QtFeatureDataType.BOOLEAN,
        ),
        _feature(
            "insertions",
            ScientificFeatureModality.CODE,
            stats,
            ("insertions",),
            from_diff,
            "Use the per-commit text-line insertion count; binary line counts "
            "remain excluded.",
            QtFeatureDataType.NON_NEGATIVE_INTEGER,
        ),
        _feature(
            "text_files",
            ScientificFeatureModality.CODE,
            stats,
            ("text_files",),
            from_diff,
            "Use the per-commit text-file count.",
            QtFeatureDataType.NON_NEGATIVE_INTEGER,
        ),
        _feature(
            "total_churn",
            ScientificFeatureModality.CODE,
            stats,
            ("total_churn",),
            from_diff,
            "Use insertions plus deletions from the same commit diff.",
            QtFeatureDataType.NON_NEGATIVE_INTEGER,
        ),
        _feature(
            "is_merge_commit",
            ScientificFeatureModality.PROCESS,
            commit,
            ("parent_ids",),
            "Available at candidate commit; no later repository state is consulted.",
            "Return true exactly when parent_ids contains more than one identifier.",
            QtFeatureDataType.BOOLEAN,
        ),
        _feature(
            "parent_count",
            ScientificFeatureModality.PROCESS,
            commit,
            ("parent_ids",),
            "Available at candidate commit; no later repository state is consulted.",
            "Count parent_ids in the immutable candidate commit object.",
            QtFeatureDataType.NON_NEGATIVE_INTEGER,
        ),
        _feature(
            "raw_commit_message",
            ScientificFeatureModality.TEXT,
            commit,
            ("message",),
            at_commit,
            "Register the exact raw UTF-8 commit message without keyword "
            "indicators, embeddings, vocabulary fitting, or semantic transformation.",
            QtFeatureDataType.UTF8_TEXT,
        ),
    ]
    unavailable = (
        (
            "developer_prior_experience",
            ("author_identity", "prior_commits"),
            "Count commits by the author strictly before the candidate commit.",
        ),
        (
            "prior_file_change_count",
            ("changed_paths", "prior_commits"),
            "Count earlier changes to current paths strictly before the candidate "
            "commit.",
        ),
        (
            "time_since_previous_change",
            ("committed_at", "changed_paths", "prior_commits"),
            "Measure elapsed time from the latest earlier change to current paths.",
        ),
    )
    for identifier, fields, construction in unavailable:
        features.append(
            QtFeatureDefinition(
                identifier,
                ScientificFeatureModality.PROCESS,
                "unavailable:qt-prior-history-feature-artifact",
                fields,
                "Would require history strictly before the candidate commit; "
                "equal-time ties must be ordered by complete commit identifier.",
                construction,
                QtFeatureDataType.NON_NEGATIVE_INTEGER,
                QtFeatureMissingPolicy.UNAVAILABLE,
                QtFeatureLeakageClassification.UNAVAILABLE_UPSTREAM,
                QtFeatureAdmissibility.UNAVAILABLE,
                "No approved Qt upstream artifact currently specifies and binds "
                "the required prior-history aggregation.",
            )
        )
    excluded = (
        (
            "bug_confidence",
            ScientificFeatureModality.PROCESS,
            QtFeatureLeakageClassification.PROHIBITED_TARGET_DERIVED,
            "Confidence belongs to target attribution and can never be predictive.",
        ),
        (
            "commit_message_bug_fix_keyword_indicator",
            ScientificFeatureModality.TEXT,
            QtFeatureLeakageClassification.PROHIBITED_KEYWORD_PROXY,
            "Engineered bug/fix keyword indicators overlap labeling semantics.",
        ),
        (
            "future_defect_count",
            ScientificFeatureModality.PROCESS,
            QtFeatureLeakageClassification.PROHIBITED_FUTURE_DERIVED,
            "Subsequent defect knowledge is unavailable at prediction time.",
        ),
        (
            "target_label",
            ScientificFeatureModality.PROCESS,
            QtFeatureLeakageClassification.PROHIBITED_TARGET_DERIVED,
            "The prediction target cannot be reused as a feature.",
        ),
    )
    for identifier, modality, classification, reason in excluded:
        features.append(
            QtFeatureDefinition(
                identifier,
                modality,
                "prohibited:no-source-dependency",
                (),
                "Never available to a predictive feature view.",
                "No value construction is permitted.",
                QtFeatureDataType.NON_NEGATIVE_INTEGER,
                QtFeatureMissingPolicy.UNAVAILABLE,
                classification,
                QtFeatureAdmissibility.INADMISSIBLE,
                reason,
            )
        )
    artifacts = tuple(
        sorted(
            (commit_artifact, diff_statistics_artifact),
            key=lambda item: item.artifact_name,
        )
    )
    ordered = tuple(
        sorted(
            features, key=lambda item: (_MODALITY_ORDER[item.modality], item.feature_id)
        )
    )
    return QtFeatureInventory(
        artifacts, ordered, QtFeatureInventory.calculate_digest(artifacts, ordered)
    )
