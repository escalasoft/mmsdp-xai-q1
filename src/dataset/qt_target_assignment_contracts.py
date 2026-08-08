"""Frozen QtBase target-assignment policy contracts."""

from __future__ import annotations

from dataclasses import dataclass

from dataset.scientific_target_assignment_contracts import (
    ScientificTargetAssignmentPolicy,
    ScientificTargetAssignmentSpecification,
)

__all__ = ["QtTargetAssignmentPolicy", "QtTargetAssignmentSpecification"]


@dataclass(frozen=True, slots=True)
class QtTargetAssignmentPolicy:
    scientific_policy: ScientificTargetAssignmentPolicy

    def __post_init__(self) -> None:
        if not isinstance(self.scientific_policy, ScientificTargetAssignmentPolicy):
            raise TypeError("scientific_policy must use the target-assignment contract")
        actual = self.scientific_policy.to_dict()
        actual.pop("policy_digest")
        actual.pop("metadata")
        if actual != self.scientific_values():
            raise ValueError("scientific_policy does not match the frozen Qt policy")

    @staticmethod
    def scientific_values() -> dict[str, object]:
        return {
            "policy_version": "qt-target-assignment-policy-1.0.0",
            "unit_of_prediction": "commit",
            "target_field": "is_defect_inducing",
            "positive_label": 1,
            "negative_label": 0,
            "positive_policy": "admissible-candidate-evidence-required",
            "negative_policy": "eligible-commit-without-admissible-candidate-evidence",
            "unresolved_policy": (
                "trace-separately-never-assign-from-unresolved-evidence"
            ),
            "excluded_policy": "trace-separately-never-assign-from-excluded-evidence",
            "aggregation_policy": (
                "one-assignment-per-historical-commit-union-provenance"
            ),
            "temporal_policy": (
                "historical-commit-strictly-precedes-every-fixing-commit"
            ),
            "ordering_policy": "commit-object-identifier-ascending",
            "forbidden_feature_sources": [
                "defect-inducing-candidate",
                "target-assignment",
                "target-evidence",
            ],
        }

    @classmethod
    def create(cls) -> QtTargetAssignmentPolicy:
        values = cls.scientific_values()
        digest = ScientificTargetAssignmentPolicy.calculate_digest(**values)
        return cls(ScientificTargetAssignmentPolicy(**values, policy_digest=digest))


@dataclass(frozen=True, slots=True)
class QtTargetAssignmentSpecification:
    scientific_specification: ScientificTargetAssignmentSpecification
    policy: QtTargetAssignmentPolicy
    project_name: str = "qtbase"

    def __post_init__(self) -> None:
        if not isinstance(
            self.scientific_specification, ScientificTargetAssignmentSpecification
        ):
            raise TypeError("scientific_specification must use the target contract")
        if not isinstance(self.policy, QtTargetAssignmentPolicy):
            raise TypeError("policy must be QtTargetAssignmentPolicy")
        if self.project_name != "qtbase":
            raise ValueError("project_name must be the controlled Qt Base identity")
        if (
            self.scientific_specification.policy_digest
            != self.policy.scientific_policy.policy_digest
        ):
            raise ValueError("specification and Qt policy digests disagree")
