"""Tests for deterministic scientific dataset builder orchestration."""

from __future__ import annotations

import inspect
from collections.abc import Mapping
from types import MappingProxyType

import pytest

from dataset import scientific_builder_pipeline as pipeline_module
from dataset.scientific_builder_contracts import (
    ScientificArtifactReference,
    ScientificBuilderStage,
    ScientificTargetAssignment,
    ScientificTargetEvidenceRecord,
)
from dataset.scientific_builder_pipeline import (
    ScientificDatasetBuilderPipeline,
    ScientificDatasetBuildStageHandler,
)

EXPECTED_API = [
    "ScientificDatasetBuildStageHandler",
    "ScientificDatasetBuilderPipeline",
]
FINAL = {
    "repository_snapshot": "snapshot",
    "source_artifacts": (),
    "target_assignments": (),
    "feature_inventory": "inventory",
    "assembly_input": "assembly",
    "manifest": "manifest",
    "validation": "validation",
    "build_result": "result",
}
SHA = "a" * 64
SHA2 = "b" * 64


def _artifact(name: str, role: str, digest: str = SHA) -> ScientificArtifactReference:
    return ScientificArtifactReference(
        name, role, f"artifacts/{name}.json", digest, "1.0", 1
    )


def _assignment(identifier: str, label: int) -> ScientificTargetAssignment:
    return ScientificTargetAssignment(
        identifier,
        "is_defect_prone",
        label,
        "1.0",
        (f"e-{identifier}",) if label else (),
        "Policy-derived assignment.",
    )


class FakeHandler(ScientificDatasetBuildStageHandler):
    def __init__(
        self,
        stage: ScientificBuilderStage,
        calls: list[str],
        *,
        output: object = None,
        error: Exception | None = None,
    ) -> None:
        self._stage = stage
        self.calls = calls
        self.output = output
        self.error = error
        self.seen: Mapping[str, object] | None = None

    @property
    def stage(self) -> ScientificBuilderStage:
        return self._stage

    def execute(self, context: Mapping[str, object]) -> Mapping[str, object]:
        self.calls.append(self.stage.value)
        self.seen = context
        if self.error:
            raise self.error
        if self.output is not None:
            return self.output  # type: ignore[return-value]
        result = dict(context)
        result["last_stage"] = self.stage.value
        if self.stage is ScientificBuilderStage.VALIDATION_REPORTING:
            result.update(FINAL)
        return result


def _handlers(calls: list[str] | None = None) -> list[FakeHandler]:
    log = calls if calls is not None else []
    return [FakeHandler(stage, log) for stage in ScientificBuilderStage]


def test_exact_public_api_and_no_forbidden_behavior_api() -> None:
    assert pipeline_module.__all__ == EXPECTED_API
    assert (
        ScientificDatasetBuilderPipeline.pipeline_name == "scientific-dataset-builder"
    )
    forbidden = {
        "train",
        "fit",
        "predict",
        "evaluate",
        "calibrate",
        "explain",
        "plot",
        "save",
        "clone",
        "fetch",
        "download",
        "extract",
    }
    public = {
        name
        for name, _ in inspect.getmembers(ScientificDatasetBuilderPipeline)
        if not name.startswith("_")
    }
    public |= {
        name
        for name, _ in inspect.getmembers(ScientificDatasetBuildStageHandler)
        if not name.startswith("_")
    }
    assert public.isdisjoint(forbidden)


def test_base_handler_cannot_silently_execute() -> None:
    with pytest.raises(TypeError):
        ScientificDatasetBuildStageHandler()


def test_required_order_duplicate_missing_and_wrong_order() -> None:
    handlers = _handlers()
    pipeline = ScientificDatasetBuilderPipeline(handlers)
    assert pipeline.stages == tuple(ScientificBuilderStage)
    with pytest.raises(ValueError, match="duplicate"):
        ScientificDatasetBuilderPipeline(handlers[:-1] + [handlers[0], handlers[-1]])
    with pytest.raises(ValueError, match="missing"):
        ScientificDatasetBuilderPipeline(handlers[:-1])
    swapped = handlers.copy()
    swapped[0], swapped[1] = swapped[1], swapped[0]
    with pytest.raises(ValueError, match="wrong order"):
        ScientificDatasetBuilderPipeline(swapped)


def test_each_stage_executes_once_and_initial_context_is_not_mutated() -> None:
    calls: list[str] = []
    initial = {"seed": {"values": [1]}}
    result = ScientificDatasetBuilderPipeline(_handlers(calls)).run(initial)
    assert calls == [stage.value for stage in ScientificBuilderStage]
    assert len(result["stage_outcomes"]) == len(ScientificBuilderStage)
    assert initial == {"seed": {"values": [1]}}
    with pytest.raises(TypeError):
        result["new"] = True


def test_stage_output_must_be_mapping() -> None:
    handlers = _handlers()
    handlers[0].output = []
    with pytest.raises(TypeError, match="must be a Mapping"):
        ScientificDatasetBuilderPipeline(handlers).run({})


def test_exception_propagates_without_retry() -> None:
    calls: list[str] = []
    handlers = _handlers(calls)
    handlers[2].error = RuntimeError("stage failed")
    with pytest.raises(RuntimeError, match="stage failed"):
        ScientificDatasetBuilderPipeline(handlers).run({})
    assert calls.count(ScientificBuilderStage.TARGET_EVIDENCE_CONSTRUCTION.value) == 1
    assert len(calls) == 3


def test_feature_context_excludes_target_evidence_and_confidence_fields() -> None:
    handlers = _handlers()
    evidence_handler = handlers[2]
    evidence_artifact = _artifact("evidence", "target-evidence", SHA2)
    evidence_record = ScientificTargetEvidenceRecord(
        "c1",
        "e-c1",
        "issue-link",
        evidence_artifact,
        "2020-01-01T00:00:00Z",
        "Audit evidence.",
        True,
        "reviewed",
    )
    evidence_handler.output = {
        "target_evidence": (evidence_record,),
        "nested": {
            "bug-confidence": 0.9,
            "target_label": 1,
            "assignment-rationale": "secret",
            "evidence_identifiers": ["e-c1"],
            "safe": 1,
        },
        "source_artifacts": (
            _artifact("commits", "commit-artifact"),
            evidence_artifact,
        ),
        "target_assignments": (_assignment("c1", 1), _assignment("c2", 0)),
        "target_contract": "must be removed structurally",
    }
    pipeline = ScientificDatasetBuilderPipeline(handlers)
    pipeline.run({})
    seen = handlers[5].seen
    assert seen is not None
    assert "target_evidence" not in seen
    assert seen["nested"] == {"safe": 1}
    assert "target_assignments" not in seen
    assert seen["target_assignment_observation_identifiers"] == ("c1", "c2")
    assert seen["source_artifacts"] == (_artifact("commits", "commit-artifact"),)
    serialized = repr(seen)
    for secret in (
        "is_defect_prone",
        "Policy-derived assignment.",
        "e-c1",
        "target-evidence",
        "bug-confidence",
    ):
        assert secret not in serialized


def test_feature_context_excludes_candidate_artifacts_and_records() -> None:
    handlers = _handlers()
    candidate_artifact = _artifact("candidates", "defect-inducing-candidate", SHA2)
    handlers[3].output = {
        "candidate_records": ({"candidate_identifier": "must-not-pass"},),
        "candidate_exclusions": ({"reason": "must-not-pass"},),
        "source_artifacts": (
            _artifact("commits", "commit-artifact"),
            candidate_artifact,
        ),
        "safe_candidate_stage_note": "contract-only",
    }
    ScientificDatasetBuilderPipeline(handlers).run({})
    seen = handlers[5].seen
    assert seen is not None
    assert "candidate_records" not in seen
    assert "candidate_exclusions" not in seen
    assert seen["source_artifacts"] == (_artifact("commits", "commit-artifact"),)
    assert "must-not-pass" not in repr(seen)


def test_feature_alignment_and_stage_outputs_are_recursively_immutable() -> None:
    handlers = _handlers()
    handlers[4].output = {
        "target_assignments": (_assignment("c1", 1),),
        "nested": {"values": [1]},
    }
    result = ScientificDatasetBuilderPipeline(handlers).run({})
    seen = handlers[5].seen
    assert seen is not None
    with pytest.raises(TypeError):
        seen["nested"]["new"] = True
    with pytest.raises(TypeError):
        result["stage_outcomes"][0]["completed"] = False
    assert isinstance(seen["target_assignment_observation_identifiers"], tuple)


@pytest.mark.parametrize(
    "reserved_key",
    [
        "target_assignment_observation_identifiers",
        "Target Assignment Observation Identifiers",
        "target-assignment-observation-identifiers",
    ],
)
@pytest.mark.parametrize("reserved_first", [True, False])
def test_upstream_alignment_key_cannot_override_canonical_identifiers(
    reserved_key: str, reserved_first: bool
) -> None:
    handlers = _handlers()
    assignments = (_assignment("c2", 0), _assignment("c1", 1))
    items = [
        (reserved_key, ("forged",)),
        ("target_assignments", assignments),
    ]
    if not reserved_first:
        items.reverse()
    handlers[4].output = dict(items)
    ScientificDatasetBuilderPipeline(handlers).run({})
    seen = handlers[5].seen
    assert seen is not None
    assert seen["target_assignment_observation_identifiers"] == ("c2", "c1")


def test_alignment_key_is_absent_without_target_assignments() -> None:
    handlers = _handlers()
    handlers[4].output = {
        "target_assignment_observation_identifiers": ("forged",),
        "safe": True,
    }
    ScientificDatasetBuilderPipeline(handlers).run({})
    seen = handlers[5].seen
    assert seen is not None
    assert "target_assignment_observation_identifiers" not in seen


def test_normalized_target_assignment_variants_are_ambiguous() -> None:
    handlers = _handlers()
    handlers[4].output = {
        "target_assignments": (_assignment("c1", 1),),
        "Target-Assignments": (_assignment("c2", 0),),
    }
    with pytest.raises(ValueError, match="ambiguous"):
        ScientificDatasetBuilderPipeline(handlers).run({})


def test_duplicate_alignment_identifiers_are_rejected() -> None:
    handlers = _handlers()
    handlers[4].output = {
        "target_assignments": (_assignment("c1", 1), _assignment("c1", 0))
    }
    with pytest.raises(ValueError, match="unique"):
        ScientificDatasetBuilderPipeline(handlers).run({})


def test_empty_alignment_identifier_is_rejected_even_for_tampered_contract() -> None:
    handlers = _handlers()
    assignment = _assignment("c1", 1)
    object.__setattr__(assignment, "observation_identifier", "")
    handlers[4].output = {"target_assignments": (assignment,)}
    with pytest.raises(ValueError, match="non-empty"):
        ScientificDatasetBuilderPipeline(handlers).run({})


def test_handler_stage_mutation_is_detected_before_execution() -> None:
    calls: list[str] = []
    handlers = _handlers(calls)
    pipeline = ScientificDatasetBuilderPipeline(handlers)
    handlers[0]._stage = ScientificBuilderStage.RAW_ARTIFACT_EXTRACTION
    with pytest.raises(ValueError, match="stage changed"):
        pipeline.run({})
    assert calls == []
    assert pipeline.stages == tuple(ScientificBuilderStage)


def test_scientific_contract_representation_is_recursively_validated() -> None:
    artifact = _artifact("commits", "commit-artifact")
    object.__setattr__(
        artifact, "metadata", MappingProxyType({"nested": {"path": "/tmp/local"}})
    )
    with pytest.raises(ValueError, match="absolute paths"):
        ScientificDatasetBuilderPipeline(_handlers()).run({"artifact": artifact})


def test_fake_dataset_module_object_cannot_bypass_context_validation() -> None:
    class FakeContract:
        def to_dict(self) -> dict[str, object]:
            return {"path": "/tmp/local"}

    FakeContract.__module__ = "dataset.fake"
    with pytest.raises(TypeError, match="deterministic values"):
        ScientificDatasetBuilderPipeline(_handlers()).run({"fake": FakeContract()})


@pytest.mark.parametrize(
    "bad",
    [
        {"value": float("nan")},
        {"value": float("inf")},
        {"path": "/tmp/local"},
        {"username": "person"},
        {"value": "<Thing object at 0x123abc>"},
        {"value": object()},
    ],
)
def test_context_rejects_nondeterministic_or_machine_local_values(
    bad: dict[str, object],
) -> None:
    with pytest.raises((TypeError, ValueError)):
        ScientificDatasetBuilderPipeline(_handlers()).run(bad)


def test_final_required_context_keys_are_enforced() -> None:
    handlers = _handlers()
    handlers[-1].output = {"repository_snapshot": "only-one"}
    with pytest.raises(ValueError, match="missing required"):
        ScientificDatasetBuilderPipeline(handlers).run({})
