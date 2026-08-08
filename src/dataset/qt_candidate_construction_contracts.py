"""Qt-specific policy contracts for future candidate construction.

This module deliberately exposes no constructor and performs no Git operations.
"""

from __future__ import annotations

from dataclasses import dataclass

from dataset.scientific_candidate_contracts import (
    ScientificCandidateConstructionPolicy,
    ScientificCandidateConstructionSpecification,
)

__all__ = [
    "QtCandidateConstructionPolicy",
    "QtCandidateConstructionSpecification",
]

_SOURCE_SUFFIXES = (
    ".c",
    ".cc",
    ".cpp",
    ".cxx",
    ".h",
    ".hh",
    ".hpp",
    ".hxx",
    ".inl",
    ".mm",
    ".qml",
)
_EXCLUDED_PATHS = (
    "3rdparty",
    "dist",
    "examples",
    "generated",
    "mkspecs",
    "tests",
    "vendor",
)


@dataclass(frozen=True, slots=True)
class QtCandidateConstructionPolicy:
    scientific_policy: ScientificCandidateConstructionPolicy

    def __post_init__(self) -> None:
        if not isinstance(
            self.scientific_policy, ScientificCandidateConstructionPolicy
        ):
            raise TypeError(
                "scientific_policy must be ScientificCandidateConstructionPolicy"
            )
        expected = self.scientific_values()
        actual = self.scientific_policy.to_dict()
        actual.pop("policy_digest")
        actual.pop("metadata")
        if actual != expected:
            raise ValueError("scientific_policy does not match the frozen Qt policy")

    @staticmethod
    def scientific_values() -> dict[str, object]:
        return {
            "policy_version": "qt-candidate-policy-1.0.0",
            "admissible_issue_types": ["Bug"],
            "admissible_issue_statuses": ["Closed", "Resolved"],
            "admissible_issue_resolutions": ["Fixed"],
            "admissible_reference_types": ["commit-message-exact-qtbug-reference"],
            "fixing_commit_policy": "matching-link-and-target-evidence-required",
            "temporal_consistency_policy": "historical-commit-strictly-precedes-fix",
            "eligible_change_types": ["deleted", "modified", "renamed"],
            "included_source_suffixes": list(_SOURCE_SUFFIXES),
            "excluded_path_components": list(_EXCLUDED_PATHS),
            "generated_file_policy": "excluded",
            "vendored_file_policy": "excluded",
            "test_file_policy": "excluded",
            "binary_file_policy": "metadata-only",
            "renamed_file_policy": "included",
            "copied_file_policy": "excluded",
            "added_file_policy": "excluded",
            "deleted_file_policy": "included",
            "baseline_policy": "recorded-first-parent",
            "merge_fix_policy": "recorded-first-parent-baseline",
            "root_commit_policy": "excluded-no-parent-baseline",
            "attribution_method": "line-provenance-blame",
            "blame_options": ["--line-porcelain", "-M", "-w"],
            "follow_renames": True,
            "follow_copies": False,
            "whitespace_policy": "ignore-all-whitespace",
            "ignored_revisions": [],
            "blank_line_policy": "exclude",
            "comment_line_policy": "exclude-language-aware",
            "comment_classifier_version": (
                "qt-comment-line-classification-contract-1.0.0"
            ),
            "comment_classifier_digest": (
                "0aac48e6867d7fd5022028a9570a007ae87cfeef45f6a2aad957c2d6e83ca483"
            ),
            "formatting_only_policy": "exclude-or-unresolved",
            "formatting_classifier_version": (
                "qt-formatting-only-classification-contract-1.0.0"
            ),
            "formatting_classifier_digest": (
                "9bd515bae7626e39e86874f0f6359f36bd8358a8948f747db63f6b90ec1deda2"
            ),
            "deletion_hunk_policy": "attribute-deleted-preimage-lines",
            "replacement_hunk_policy": "attribute-deleted-preimage-lines-only",
            "attribution_failure_policy": "record-unresolved-no-guess",
            "unblamable_line_policy": "record-unresolved-no-guess",
            "boundary_policy": "record-unresolved",
            "deduplication_policy": "full-provenance",
            "ordering_policy": "canonical-provenance",
            "aggregation_levels": ["line", "hunk", "commit"],
        }

    @classmethod
    def create(cls) -> QtCandidateConstructionPolicy:
        values = cls.scientific_values()
        digest = ScientificCandidateConstructionPolicy.calculate_digest(**values)
        policy = ScientificCandidateConstructionPolicy(
            **values,
            policy_digest=digest,
        )
        return cls(policy)

    def to_dict(self) -> dict[str, object]:
        return {"scientific_policy": self.scientific_policy.to_dict()}


@dataclass(frozen=True, slots=True)
class QtCandidateConstructionSpecification:
    scientific_specification: ScientificCandidateConstructionSpecification
    policy: QtCandidateConstructionPolicy
    project_name: str = "qtbase"

    def __post_init__(self) -> None:
        if not isinstance(
            self.scientific_specification,
            ScientificCandidateConstructionSpecification,
        ):
            raise TypeError(
                "scientific_specification must use the scientific candidate contract"
            )
        if not isinstance(self.policy, QtCandidateConstructionPolicy):
            raise TypeError("policy must be QtCandidateConstructionPolicy")
        if self.project_name != "qtbase":
            raise ValueError("project_name must be the controlled Qt Base identity")
        if (
            self.scientific_specification.policy_digest
            != self.policy.scientific_policy.policy_digest
        ):
            raise ValueError("specification and Qt policy digests disagree")

    def to_dict(self) -> dict[str, object]:
        return {
            "scientific_specification": self.scientific_specification.to_dict(),
            "policy": self.policy.to_dict(),
            "project_name": self.project_name,
        }
