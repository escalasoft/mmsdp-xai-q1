"""Deterministic orchestration for scientific dataset construction stages."""

from __future__ import annotations

import math
import re
from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from enum import Enum
from types import MappingProxyType

from dataset.scientific_builder_contracts import (
    ScientificArtifactReference,
    ScientificArtifactRole,
    ScientificBuilderStage,
    ScientificDatasetAssemblyInput,
    ScientificDatasetBuildManifest,
    ScientificDatasetBuildResult,
    ScientificDatasetBuildValidation,
    ScientificFeatureInventory,
    ScientificFeatureValueRecord,
    ScientificRepositorySnapshot,
    ScientificTargetAssignment,
    ScientificTargetEvidenceRecord,
)
from dataset.scientific_candidate_contracts import (
    ScientificCandidateArtifactBinding,
    ScientificCandidateAttributionRecord,
    ScientificCandidateConstructionPolicy,
    ScientificCandidateConstructionResult,
    ScientificCandidateConstructionSpecification,
    ScientificCandidateConstructionValidation,
    ScientificCandidateExclusionRecord,
    ScientificDefectInducingCandidateRecord,
)
from dataset.scientific_dataset_contract import (
    ScientificFeatureProvenance,
    ScientificTargetContract,
)
from dataset.scientific_target_assignment_contracts import (
    ScientificTargetAssignmentArtifactBinding,
    ScientificTargetAssignmentPolicy,
    ScientificTargetAssignmentResult,
    ScientificTargetAssignmentSpecification,
    ScientificTargetAssignmentValidation,
    ScientificTargetEvidenceTrace,
)

__all__ = [
    "ScientificDatasetBuildStageHandler",
    "ScientificDatasetBuilderPipeline",
]

_STAGES = tuple(ScientificBuilderStage)
_FINAL_KEYS = frozenset(
    {
        "repository_snapshot",
        "source_artifacts",
        "target_assignments",
        "feature_inventory",
        "assembly_input",
        "manifest",
        "validation",
        "build_result",
    }
)
_CONFIDENCE_KEYS = frozenset(
    {
        "bug_confidence",
        "label_confidence",
        "target_probability",
        "msg_has_bug_kw",
        "has_bug_keyword",
        "contains_bug_keyword",
        "contains_fix_keyword",
        "future_bug_count",
        "future_fix_count",
        "post_release_defect_count",
        "target_field",
        "target_label",
        "evidence_identifiers",
        "assignment_rationale",
    }
)
_RUNTIME_KEYS = frozenset(
    {"hostname", "machine_identifier", "machine_name", "memory_address", "username"}
)
_OBJECT_REPR = re.compile(r"<[^>]+(?:object at )?0x[0-9a-fA-F]+>")
_MEMORY_ADDRESS = re.compile(r"\b0x[0-9a-fA-F]{6,}\b")
_SCIENTIFIC_CONTRACT_TYPES = (
    ScientificArtifactReference,
    ScientificRepositorySnapshot,
    ScientificTargetEvidenceRecord,
    ScientificTargetAssignment,
    ScientificFeatureValueRecord,
    ScientificFeatureInventory,
    ScientificDatasetAssemblyInput,
    ScientificDatasetBuildManifest,
    ScientificDatasetBuildValidation,
    ScientificDatasetBuildResult,
    ScientificFeatureProvenance,
    ScientificTargetContract,
    ScientificCandidateConstructionSpecification,
    ScientificCandidateConstructionPolicy,
    ScientificCandidateAttributionRecord,
    ScientificDefectInducingCandidateRecord,
    ScientificCandidateExclusionRecord,
    ScientificCandidateConstructionValidation,
    ScientificCandidateArtifactBinding,
    ScientificCandidateConstructionResult,
    ScientificTargetAssignmentSpecification,
    ScientificTargetAssignmentPolicy,
    ScientificTargetEvidenceTrace,
    ScientificTargetAssignmentValidation,
    ScientificTargetAssignmentArtifactBinding,
    ScientificTargetAssignmentResult,
)

_CANDIDATE_TYPES = (
    ScientificCandidateConstructionSpecification,
    ScientificCandidateConstructionPolicy,
    ScientificCandidateAttributionRecord,
    ScientificDefectInducingCandidateRecord,
    ScientificCandidateExclusionRecord,
    ScientificCandidateConstructionValidation,
    ScientificCandidateArtifactBinding,
    ScientificCandidateConstructionResult,
)

_TARGET_ASSIGNMENT_TYPES = (
    ScientificTargetAssignmentSpecification,
    ScientificTargetAssignmentPolicy,
    ScientificTargetEvidenceTrace,
    ScientificTargetAssignmentValidation,
    ScientificTargetAssignmentArtifactBinding,
    ScientificTargetAssignmentResult,
)


def _key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def _detach(value: object, *, feature_view: bool = False) -> object:
    if feature_view and isinstance(value, _CANDIDATE_TYPES):
        return None
    if feature_view and isinstance(value, _TARGET_ASSIGNMENT_TYPES):
        return None
    if feature_view and isinstance(value, ScientificTargetEvidenceRecord):
        return None
    if feature_view and isinstance(value, ScientificTargetAssignment):
        return None
    if feature_view and isinstance(
        value,
        (
            ScientificTargetContract,
            ScientificDatasetAssemblyInput,
            ScientificDatasetBuildManifest,
            ScientificDatasetBuildResult,
        ),
    ):
        return None
    if feature_view and isinstance(value, ScientificArtifactReference):
        if value.artifact_role in {
            ScientificArtifactRole.TARGET_EVIDENCE,
            ScientificArtifactRole.DEFECT_INDUCING_CANDIDATE,
            ScientificArtifactRole.TARGET_ASSIGNMENT,
        }:
            return None
    if isinstance(value, _SCIENTIFIC_CONTRACT_TYPES):
        _detach(value.to_dict())
        return value
    if isinstance(value, Mapping):
        detached: dict[str, object] = {}
        alignment_identifiers: tuple[str, ...] | None = None
        if feature_view:
            assignment_entries = tuple(
                item
                for key, item in value.items()
                if isinstance(key, str) and _key(key) == "target_assignments"
            )
            if len(assignment_entries) > 1:
                raise ValueError(
                    "multiple normalized target_assignments keys are ambiguous"
                )
            if assignment_entries:
                assignments = assignment_entries[0]
                if not isinstance(assignments, (list, tuple)) or any(
                    not isinstance(assignment, ScientificTargetAssignment)
                    for assignment in assignments
                ):
                    raise TypeError(
                        "feature alignment requires typed target assignments"
                    )
                alignment_identifiers = tuple(
                    assignment.observation_identifier for assignment in assignments
                )
                if any(
                    not isinstance(identifier, str) or not identifier.strip()
                    for identifier in alignment_identifiers
                ):
                    raise ValueError(
                        "feature alignment observation identifiers must be non-empty"
                    )
                if len(alignment_identifiers) != len(set(alignment_identifiers)):
                    raise ValueError(
                        "feature alignment observation identifiers must be unique"
                    )
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("context keys must be strings")
            normalized = _key(key)
            if normalized in _RUNTIME_KEYS:
                raise ValueError(
                    f"context contains forbidden runtime identity field {key!r}"
                )
            if feature_view and normalized in {
                "assembly_input",
                "build_result",
                "manifest",
                "target_assignment_observation_identifiers",
                "target_contract",
                "target_evidence",
                "target_evidence_records",
                "candidate_attributions",
                "candidate_records",
                "candidate_exclusions",
                "candidate_validation",
                "candidate_result",
                "candidate_artifact_binding",
                "target_assignment_result",
                "target_assignment_artifact_binding",
            }:
                continue
            if feature_view and normalized == "target_assignments":
                continue
            if feature_view and normalized in _CONFIDENCE_KEYS:
                continue
            if feature_view and normalized == "source_artifacts":
                if not isinstance(item, (list, tuple)):
                    raise TypeError("source_artifacts must be an ordered collection")
                detached[key] = tuple(
                    artifact
                    for artifact in (
                        _detach(value, feature_view=True) for value in item
                    )
                    if artifact is not None
                )
                continue
            child = _detach(item, feature_view=feature_view)
            if not (feature_view and child is None):
                detached[key] = child
        if alignment_identifiers is not None:
            detached["target_assignment_observation_identifiers"] = (
                alignment_identifiers
            )
        return MappingProxyType(detached)
    if isinstance(value, (list, tuple)):
        items = tuple(_detach(item, feature_view=feature_view) for item in value)
        return tuple(item for item in items if not (feature_view and item is None))
    if value is None or isinstance(value, (bool, int, Enum)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("context must contain finite numeric values")
        return value
    if isinstance(value, str):
        if value.startswith("/"):
            raise ValueError("context must not contain local absolute paths")
        if _OBJECT_REPR.search(value) or _MEMORY_ADDRESS.search(value):
            raise ValueError(
                "context must not contain object representations or memory addresses"
            )
        return value
    raise TypeError("context must contain deterministic values or scientific contracts")


class ScientificDatasetBuildStageHandler(ABC):
    """One explicit, project-independent scientific builder stage."""

    @property
    @abstractmethod
    def stage(self) -> ScientificBuilderStage:
        """Return the single stage implemented by this handler."""

    @abstractmethod
    def execute(self, context: Mapping[str, object]) -> Mapping[str, object]:
        """Execute explicitly; the base contract never silently runs."""


class ScientificDatasetBuilderPipeline:
    """Orchestrate handlers without acquisition, extraction, or dataset behavior."""

    pipeline_name = "scientific-dataset-builder"

    def __init__(self, handlers: Sequence[ScientificDatasetBuildStageHandler]) -> None:
        supplied = tuple(handlers)
        stages: list[ScientificBuilderStage] = []
        for handler in supplied:
            if not isinstance(handler, ScientificDatasetBuildStageHandler):
                raise TypeError(
                    "handlers must implement ScientificDatasetBuildStageHandler"
                )
            try:
                stages.append(ScientificBuilderStage(handler.stage))
            except (TypeError, ValueError) as error:
                raise ValueError(
                    f"unsupported scientific builder stage: {handler.stage!r}"
                ) from error
        if len(stages) != len(set(stages)):
            raise ValueError("duplicate scientific builder stage handler")
        missing = tuple(stage for stage in _STAGES if stage not in stages)
        if missing:
            raise ValueError(f"missing scientific builder stages: {missing!r}")
        if tuple(stages) != _STAGES:
            raise ValueError("scientific builder handlers are in the wrong order")
        self._stage_handlers = tuple(zip(stages, supplied, strict=True))
        self._stages = tuple(stages)

    @property
    def stages(self) -> tuple[ScientificBuilderStage, ...]:
        return self._stages

    def run(self, initial_context: Mapping[str, object]) -> Mapping[str, object]:
        context = self._validate_initial_context(initial_context)
        outcomes: list[Mapping[str, object]] = []
        for captured_stage, handler in self._stage_handlers:
            supplied = self._prepare_stage_context(captured_stage, handler, context)
            output = self._execute_stage(captured_stage, handler, supplied)
            context = self._validate_stage_output(captured_stage, output)
            outcomes.append(self._record_stage_outcome(captured_stage))
        return self._validate_final_context(context, outcomes)

    @staticmethod
    def _validate_initial_context(
        initial_context: Mapping[str, object],
    ) -> Mapping[str, object]:
        if not isinstance(initial_context, Mapping):
            raise TypeError("initial_context must be a Mapping")
        return _detach(initial_context)  # type: ignore[return-value]

    @staticmethod
    def _prepare_stage_context(
        captured_stage: ScientificBuilderStage,
        handler: ScientificDatasetBuildStageHandler,
        context: Mapping[str, object],
    ) -> Mapping[str, object]:
        try:
            current_stage = ScientificBuilderStage(handler.stage)
        except (TypeError, ValueError) as error:
            raise ValueError(
                "handler stage changed after pipeline construction"
            ) from error
        if current_stage is not captured_stage:
            raise ValueError(
                f"handler stage changed after pipeline construction: "
                f"expected {captured_stage.value!r}, got {current_stage.value!r}"
            )
        return _detach(
            context,
            feature_view=captured_stage is ScientificBuilderStage.FEATURE_CONSTRUCTION,
        )  # type: ignore[return-value]

    @staticmethod
    def _execute_stage(
        captured_stage: ScientificBuilderStage,
        handler: ScientificDatasetBuildStageHandler,
        context: Mapping[str, object],
    ) -> object:
        del captured_stage
        return handler.execute(context)

    @staticmethod
    def _validate_stage_output(
        captured_stage: ScientificBuilderStage, output: object
    ) -> Mapping[str, object]:
        if not isinstance(output, Mapping):
            raise TypeError(f"{captured_stage.value} stage output must be a Mapping")
        return _detach(output)  # type: ignore[return-value]

    @staticmethod
    def _record_stage_outcome(
        captured_stage: ScientificBuilderStage,
    ) -> Mapping[str, object]:
        return MappingProxyType({"stage": captured_stage.value, "completed": True})

    @staticmethod
    def _validate_final_context(
        context: Mapping[str, object], outcomes: list[Mapping[str, object]]
    ) -> Mapping[str, object]:
        missing = sorted(_FINAL_KEYS - set(context))  # type: ignore[arg-type]
        if missing:
            raise ValueError(f"final context is missing required items: {missing!r}")
        final = dict(context)
        final["stage_outcomes"] = tuple(outcomes)
        return MappingProxyType(final)
