"""Focused tests for immutable candidate scientific contracts."""

from __future__ import annotations

import dataclasses
import inspect
from dataclasses import FrozenInstanceError

import pytest

from dataset import scientific_candidate_contracts as module
from dataset.qt_candidate_construction_contracts import QtCandidateConstructionPolicy
from dataset.scientific_builder_contracts import ScientificArtifactReference
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

SHA = "a" * 64
SHA2 = "b" * 64
OID = "c" * 40
OID2 = "d" * 40

EXPECTED_API = [
    "ScientificCandidateAggregationLevel",
    "ScientificCandidateAttributionMethod",
    "ScientificCandidateDisposition",
    "ScientificCandidateExclusionReason",
    "ScientificCandidateFileDisposition",
    "ScientificCandidateBlameBoundaryPolicy",
    "ScientificCandidateDeduplicationPolicy",
    "ScientificCandidateOrderingPolicy",
    "ScientificCandidateConstructionSpecification",
    "ScientificCandidateConstructionPolicy",
    "ScientificCandidateAttributionRecord",
    "ScientificDefectInducingCandidateRecord",
    "ScientificCandidateExclusionRecord",
    "ScientificCandidateConstructionValidation",
    "ScientificCandidateArtifactBinding",
    "ScientificCandidateConstructionResult",
]


def _policy() -> ScientificCandidateConstructionPolicy:
    return QtCandidateConstructionPolicy.create().scientific_policy


def _specification(policy: ScientificCandidateConstructionPolicy):
    values = {
        "schema_version": "1.0.0",
        "specification_version": "candidate-specification-1.0.0",
        "repository_snapshot_digest": SHA,
        "commit_artifact_digest": SHA,
        "issue_artifact_digest": SHA,
        "commit_issue_link_artifact_digest": SHA,
        "target_evidence_artifact_digest": SHA,
        "diff_artifact_digest": SHA,
        "policy_digest": policy.policy_digest,
    }
    return ScientificCandidateConstructionSpecification(
        **values,
        specification_digest=(
            ScientificCandidateConstructionSpecification.calculate_digest(**values)
        ),
    )


def _attribution(**changes: object) -> ScientificCandidateAttributionRecord:
    policy = _policy()
    values = {
        "repository_snapshot_digest": SHA,
        "fixing_commit": OID2,
        "baseline_commit": OID,
        "issue_identifier": "QTBUG-1",
        "target_evidence_identifier": "evidence-1",
        "commit_issue_link_identifier": "link-1",
        "commit_issue_link_artifact_digest": SHA,
        "diff_artifact_digest": SHA,
        "hunk_identifier": "hunk-1",
        "old_path": "src/a.cpp",
        "old_blob_identifier": OID,
        "deleted_preimage_line_number": 7,
        "blamed_historical_commit": OID,
        "attribution_method": "line-provenance-blame",
        "policy_version": policy.policy_version,
        "policy_digest": policy.policy_digest,
    }
    values.update(changes)
    return ScientificCandidateAttributionRecord(
        **values,
        attribution_identifier=(
            ScientificCandidateAttributionRecord.calculate_identifier(**values)
        ),
    )


def _candidate(attribution_identifier: str):
    policy = _policy()
    values = {
        "blamed_historical_commit": OID,
        "aggregation_level": "commit",
        "attribution_identifiers": (attribution_identifier,),
        "fixing_commits": (OID2,),
        "issue_identifiers": ("QTBUG-1",),
        "target_evidence_identifiers": ("evidence-1",),
        "policy_version": policy.policy_version,
        "policy_digest": policy.policy_digest,
    }
    return ScientificDefectInducingCandidateRecord(
        **values,
        candidate_identifier=(
            ScientificDefectInducingCandidateRecord.calculate_identifier(**values)
        ),
    )


def _exclusion() -> ScientificCandidateExclusionRecord:
    policy = _policy()
    values = {
        "disposition": "unresolved",
        "reason": "unblamable-line",
        "fixing_commit": OID2,
        "baseline_commit": OID,
        "issue_identifier": "QTBUG-1",
        "target_evidence_identifier": "evidence-1",
        "hunk_identifier": "hunk-2",
        "old_path": "src/b.cpp",
        "old_blob_identifier": OID,
        "deleted_preimage_line_number": 8,
        "policy_version": policy.policy_version,
        "policy_digest": policy.policy_digest,
        "detail_code": "no-attribution-produced",
    }
    return ScientificCandidateExclusionRecord(
        **values,
        exclusion_identifier=(
            ScientificCandidateExclusionRecord.calculate_identifier(**values)
        ),
    )


def test_exact_public_api_and_frozen_slotted_contracts() -> None:
    assert module.__all__ == EXPECTED_API
    contract_types = [getattr(module, name) for name in EXPECTED_API[8:]]
    for contract_type in contract_types:
        assert dataclasses.is_dataclass(contract_type)
        assert contract_type.__dataclass_params__.frozen
        assert "__slots__" in vars(contract_type)
    with pytest.raises(FrozenInstanceError):
        _attribution().old_path = "other.cpp"


def test_canonical_identifiers_are_deterministic_and_metadata_independent() -> None:
    first = _attribution(metadata={"scientific_note": ["stable"]})
    second = _attribution(metadata={"scientific_note": ["different"]})
    assert first.attribution_identifier == second.attribution_identifier
    assert len(first.attribution_identifier) == 64
    changed = _attribution(deleted_preimage_line_number=8)
    assert changed.attribution_identifier != first.attribution_identifier


def test_classifier_versions_and_digests_are_policy_identity_bearing() -> None:
    policy = _policy()
    values = policy.to_dict()
    values.pop("policy_digest")
    values.pop("metadata")
    changed = dict(values)
    changed["comment_classifier_version"] = "different-classifier-1.0.0"
    assert ScientificCandidateConstructionPolicy.calculate_digest(**changed) != (
        policy.policy_digest
    )
    changed = dict(values)
    changed["formatting_classifier_digest"] = SHA2
    assert ScientificCandidateConstructionPolicy.calculate_digest(**changed) != (
        policy.policy_digest
    )
    with pytest.raises(ValueError, match="SHA-256"):
        ScientificCandidateConstructionPolicy(
            **(values | {"comment_classifier_digest": "unversioned"}),
            policy_digest=SHA,
        )


def test_recursive_immutability_and_forbidden_semantics() -> None:
    source = {"nested": ["value"]}
    record = _attribution(metadata=source)
    source["nested"].append("mutated")
    assert record.to_dict()["metadata"] == {"nested": ["value"]}
    with pytest.raises(TypeError):
        record.metadata["other"] = 1
    for key in (
        "label",
        "target",
        "prediction",
        "probability",
        "confidence",
        "feature_value",
        "runtime_timestamp",
        "hostname",
        "local_path",
    ):
        with pytest.raises(ValueError, match="forbidden|machine-local"):
            _attribution(metadata={"nested": {key: 1}})


def test_ordering_and_uniqueness_are_enforced() -> None:
    attribution = _attribution()
    with pytest.raises(ValueError, match="unique and deterministically ordered"):
        _candidate(attribution.attribution_identifier).__class__(
            candidate_identifier=SHA,
            blamed_historical_commit=OID,
            aggregation_level="commit",
            attribution_identifiers=(
                attribution.attribution_identifier,
                attribution.attribution_identifier,
            ),
            fixing_commits=(OID2,),
            issue_identifiers=("QTBUG-1",),
            target_evidence_identifiers=("evidence-1",),
            policy_version=_policy().policy_version,
            policy_digest=_policy().policy_digest,
        )


def test_provenance_is_complete_and_assignment_fields_are_absent() -> None:
    names = {
        item.name for item in dataclasses.fields(ScientificCandidateAttributionRecord)
    }
    assert {
        "repository_snapshot_digest",
        "fixing_commit",
        "baseline_commit",
        "issue_identifier",
        "target_evidence_identifier",
        "commit_issue_link_identifier",
        "commit_issue_link_artifact_digest",
        "diff_artifact_digest",
        "hunk_identifier",
        "old_path",
        "old_blob_identifier",
        "deleted_preimage_line_number",
        "blamed_historical_commit",
        "attribution_method",
        "policy_version",
        "policy_digest",
    }.issubset(names)
    candidate_names = {
        item.name
        for item in dataclasses.fields(ScientificDefectInducingCandidateRecord)
    }
    assert candidate_names.isdisjoint(
        {"label", "target", "prediction", "probability", "confidence", "feature_value"}
    )


def test_result_and_manifest_binding_are_consistent() -> None:
    policy = _policy()
    specification = _specification(policy)
    attribution = _attribution()
    candidate = _candidate(attribution.attribution_identifier)
    exclusion = _exclusion()
    artifact = ScientificArtifactReference(
        "qtbase-candidates",
        "defect-inducing-candidate",
        "artifacts/derived/qtbase-candidates.json",
        SHA2,
        "1.0.0",
        1,
    )
    binding_values = {
        "artifact": artifact,
        "specification_digest": specification.specification_digest,
        "policy_digest": policy.policy_digest,
        "repository_snapshot_digest": SHA,
        "upstream_artifact_digests": {
            "commits": SHA,
            "diffs": SHA,
            "issues": SHA,
            "links": SHA,
            "target-evidence": SHA,
        },
        "ordered_candidate_identifiers": (candidate.candidate_identifier,),
        "ordered_exclusion_identifiers": (exclusion.exclusion_identifier,),
    }
    binding = ScientificCandidateArtifactBinding(
        **binding_values,
        binding_digest=ScientificCandidateArtifactBinding.calculate_digest(
            **binding_values
        ),
    )
    validation = ScientificCandidateConstructionValidation(
        True,
        specification.specification_digest,
        policy.policy_digest,
        1,
        1,
        1,
        (),
        (),
    )
    result = ScientificCandidateConstructionResult(
        specification,
        policy,
        (attribution,),
        (candidate,),
        (exclusion,),
        validation,
        binding,
    )
    assert result.artifact_binding.artifact.artifact_role.value == (
        "defect-inducing-candidate"
    )
    assert not hasattr(result, "target_assignments")


def test_contract_module_contains_no_execution_surface() -> None:
    source = inspect.getsource(module)
    for forbidden in ("subprocess", "GitClient", "git blame", "requests", "httpx"):
        assert forbidden not in source
