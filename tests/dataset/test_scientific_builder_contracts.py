"""Tests for scientific dataset builder value and result contracts."""

from __future__ import annotations

import inspect
from dataclasses import FrozenInstanceError, replace
from decimal import Decimal
from fractions import Fraction

import pytest

from dataset import scientific_builder_contracts as contracts
from dataset.scientific_builder_contracts import (
    ScientificArtifactReference,
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
from dataset.scientific_dataset_contract import (
    ScientificFeatureProvenance,
    ScientificTargetContract,
)

SHA = "a" * 64
SHA2 = "b" * 64
EXPECTED_API = [
    "ScientificBuilderStage",
    "ScientificArtifactRole",
    "ScientificArtifactReference",
    "ScientificRepositorySnapshot",
    "ScientificTargetEvidenceRecord",
    "ScientificTargetAssignment",
    "ScientificFeatureValueRecord",
    "ScientificFeatureInventory",
    "ScientificDatasetAssemblyInput",
    "ScientificDatasetBuildManifest",
    "ScientificDatasetBuildValidation",
    "ScientificDatasetBuildResult",
]


def _artifact(
    name: str = "commits", role: str = "commit-artifact"
) -> ScientificArtifactReference:
    return ScientificArtifactReference(
        name, role, f"artifacts/{name}.json", SHA, "1.0", 1, {"nested": [1]}
    )


def _snapshot() -> ScientificRepositorySnapshot:
    return ScientificRepositorySnapshot(
        "sample", "https://example.invalid/sample", "c" * 40, "main", "1.0", SHA
    )


def _target_contract(
    negative_label: str | int = 0, positive_label: str | int = 1
) -> ScientificTargetContract:
    return ScientificTargetContract(
        "is_defect_prone",
        "binary",
        negative_label,
        positive_label,
        "defect-prone commit",
        "non-defect-prone commit",
        "Target construction is separate from feature construction.",
        ("provenance",),
        True,
    )


def _provenance(**changes: object) -> ScientificFeatureProvenance:
    values = {
        "feature_name": "lines_added",
        "modality": "code",
        "source_artifact": "commit-diff",
        "source_fields": ("added_lines",),
        "temporal_scope": "commit-current",
        "availability_time": "at commit",
        "derivation_summary": "Count current added lines.",
        "uses_target": False,
        "uses_issue_linking_evidence": False,
        "uses_future_information": False,
        "uses_post_event_information": False,
        "computed_using_full_dataset": False,
        "leakage_risk": "low",
        "disposition": "permitted",
        "rationale": "Available at observation time.",
        "allowed_in_complete_scenario": True,
        "allowed_in_leakage_controlled_scenario": True,
        "metadata": {},
    }
    values.update(changes)
    return ScientificFeatureProvenance(**values)


def _inventory(
    features: tuple[ScientificFeatureProvenance, ...] | None = None,
) -> ScientificFeatureInventory:
    provenance = features or (_provenance(),)
    complete = tuple(
        sorted(
            item.feature_name
            for item in provenance
            if item.allowed_in_complete_scenario
        )
    )
    controlled = tuple(
        sorted(
            item.feature_name
            for item in provenance
            if item.allowed_in_leakage_controlled_scenario
        )
    )
    prohibited = tuple(
        sorted(
            item.feature_name
            for item in provenance
            if item.disposition.value == "prohibited"
        )
    )
    review = tuple(
        sorted(
            item.feature_name
            for item in provenance
            if item.disposition.value == "review-required"
        )
    )
    digest = ScientificFeatureInventory.calculate_digest(
        specification_digest=SHA,
        feature_provenance=provenance,
        complete_scenario_feature_names=complete,
        leakage_controlled_feature_names=controlled,
        prohibited_feature_names=prohibited,
        review_required_feature_names=review,
    )
    return ScientificFeatureInventory(
        SHA, provenance, complete, controlled, prohibited, review, digest
    )


def _assignment(identifier: str = "c1", label: int = 1) -> ScientificTargetAssignment:
    return ScientificTargetAssignment(
        identifier,
        "is_defect_prone",
        label,
        "1.0",
        ("e1",) if label else (),
        "Deterministic evidence policy.",
    )


def _value(
    identifier: str = "c1", feature: str = "lines_added"
) -> ScientificFeatureValueRecord:
    return ScientificFeatureValueRecord(
        identifier, feature, "code", 2, SHA, "commit-current"
    )


def _assembly(**changes: object) -> ScientificDatasetAssemblyInput:
    values = {
        "repository_snapshot": _snapshot(),
        "source_artifacts": (_artifact(),),
        "observation_identifiers": ("c1",),
        "observation_timestamps": {"c1": "2020-01-01T00:00:00Z"},
        "target_contract": _target_contract(),
        "target_assignments": (_assignment(),),
        "feature_inventory": _inventory(),
        "feature_values": (_value(),),
        "scientific_dataset_specification_digest": SHA,
        "metadata": {},
    }
    values.update(changes)
    return ScientificDatasetAssemblyInput(**values)


def _manifest(**changes: object) -> ScientificDatasetBuildManifest:
    values = {
        "build_schema_version": "1.0",
        "dataset_name": "sample",
        "dataset_version": "1.0",
        "repository_snapshot_digest": SHA,
        "scientific_dataset_specification_digest": SHA,
        "feature_inventory_digest": _inventory().inventory_digest,
        "source_artifact_digests": {"commits": SHA},
        "stage_sequence": tuple(contracts.ScientificBuilderStage),
        "observation_count": 1,
        "feature_count": 1,
        "target_positive_count": 1,
        "target_negative_count": 0,
        "output_artifacts": (_artifact("dataset", "dataset"),),
        "metadata": {},
    }
    values.update(changes)
    values["scientific_digest"] = ScientificDatasetBuildManifest.calculate_digest(
        **values
    )
    return ScientificDatasetBuildManifest(**values)


def _validation() -> ScientificDatasetBuildValidation:
    return ScientificDatasetBuildValidation(
        True, (), (), 1, 1, 1, 1, SHA, _inventory().inventory_digest
    )


def test_exact_public_api_and_enum_values() -> None:
    assert contracts.__all__ == EXPECTED_API
    assert [item.value for item in contracts.ScientificBuilderStage] == [
        "repository-acquisition",
        "raw-artifact-extraction",
        "target-evidence-construction",
        "candidate-construction",
        "target-assignment",
        "feature-construction",
        "feature-provenance-audit",
        "leakage-validation",
        "dataset-assembly",
        "manifest-generation",
        "validation-reporting",
    ]


def test_contracts_are_immutable_and_metadata_is_detached() -> None:
    metadata = {"nested": [1]}
    artifact = ScientificArtifactReference(
        "a", "commit-artifact", "a.json", SHA, "1", 0, metadata
    )
    metadata["nested"].append(2)
    with pytest.raises(FrozenInstanceError):
        artifact.record_count = 2
    with pytest.raises(TypeError):
        artifact.metadata["new"] = True
    assert artifact.to_dict()["metadata"] == {"nested": [1]}
    first = artifact.to_dict()
    first["metadata"]["nested"].append(9)
    assert artifact.to_dict()["metadata"] == {"nested": [1]}


@pytest.mark.parametrize("path", ["/tmp/a", "../a", "a/../b", "a\\b", "a//b", "./a"])
def test_artifact_paths_reject_absolute_traversal_or_non_normalized(path: str) -> None:
    with pytest.raises(ValueError, match="relative and normalized"):
        ScientificArtifactReference("a", "commit-artifact", path, SHA, "1", 0)


@pytest.mark.parametrize("digest", ["A" * 64, "a" * 63, "g" * 64, "sha256:" + SHA])
def test_sha256_validation(digest: str) -> None:
    with pytest.raises(ValueError, match="SHA-256"):
        replace(_artifact(), content_digest=digest)


def test_repository_snapshot_validation_and_runtime_identity_exclusion() -> None:
    assert (
        replace(_snapshot(), repository_revision="d" * 40).repository_revision
        == "d" * 40
    )
    assert (
        replace(_snapshot(), repository_revision="e" * 64).repository_revision
        == "e" * 64
    )
    assert _snapshot() == _snapshot()
    assert _snapshot().to_dict() == _snapshot().to_dict()
    for revision in (
        "abc123",
        "A" * 40,
        "main",
        "master",
        "release-1.0",
        "HEAD",
        "latest",
        "tip",
    ):
        with pytest.raises(ValueError, match="complete lowercase"):
            replace(_snapshot(), repository_revision=revision)
    with pytest.raises(ValueError, match="non-empty"):
        replace(_snapshot(), repository_url=" ")
    with pytest.raises(ValueError, match="runtime identity"):
        replace(_snapshot(), metadata={"username": "alex"})


def test_target_evidence_is_audit_only_and_normalizes_timestamp() -> None:
    evidence = ScientificTargetEvidenceRecord(
        "c1",
        "e1",
        "issue-link",
        _artifact("issue", "issue-artifact"),
        "2020-01-01T01:00:00+01:00",
        "Linked evidence.",
        True,
        "reviewed",
    )
    assert evidence.evidence_timestamp == "2020-01-01T00:00:00Z"
    assert "confidence_category" in evidence.to_dict()
    with pytest.raises(ValueError, match="feature"):
        replace(evidence, metadata={"enabled_as_feature": True})


@pytest.mark.parametrize(
    "role",
    [
        "commit-artifact",
        "diff-artifact",
        "file-artifact",
        "issue-artifact",
        "target-evidence",
    ],
)
def test_target_evidence_accepts_raw_and_evidence_source_roles(role: str) -> None:
    ScientificTargetEvidenceRecord(
        "c1",
        "e1",
        "link",
        _artifact("source", role),
        "2020-01-01T00:00:00Z",
        "Evidence.",
        True,
        "reviewed",
    )


@pytest.mark.parametrize(
    "role",
    [
        "code-feature",
        "process-feature",
        "text-feature",
        "dataset",
        "manifest",
        "validation-report",
        "target-assignment",
        "leakage-audit",
    ],
)
def test_target_evidence_rejects_derived_source_roles(role: str) -> None:
    with pytest.raises(ValueError, match="role"):
        ScientificTargetEvidenceRecord(
            "c1",
            "e1",
            "link",
            _artifact("source", role),
            "2020-01-01T00:00:00Z",
            "Evidence.",
            True,
            "reviewed",
        )


def test_target_assignment_scalar_policy_and_separation() -> None:
    assignment = _assignment()
    assert set(assignment.to_dict()).isdisjoint(
        {"target_probability", "bug_confidence", "feature_values"}
    )
    assert replace(assignment, evidence_identifiers=()).evidence_identifiers == ()
    with pytest.raises(TypeError, match="target_label"):
        replace(assignment, target_label=True)
    source = inspect.getsource(ScientificTargetAssignment.__post_init__)
    assert all(
        vocabulary not in source
        for vocabulary in ('"positive"', '"bug"', '"defect"', '"defect-prone"')
    )


@pytest.mark.parametrize(
    "value",
    [
        True,
        False,
        float("nan"),
        float("inf"),
        -float("inf"),
        "1",
        1 + 2j,
        Decimal("1.2"),
    ],
)
def test_feature_values_require_finite_numeric_scalar(value: object) -> None:
    with pytest.raises((TypeError, ValueError), match="finite numeric"):
        replace(_value(), value=value)


def test_real_numeric_scalars_are_normalized_to_json_numbers() -> None:
    integral = replace(_value(), value=3)
    real = replace(_value(), value=Fraction(1, 2))
    assert type(integral.value) is int
    assert type(real.value) is float
    assert real.to_dict()["value"] == 0.5


@pytest.mark.parametrize(
    "key", ["target", "label_confidence", "bug-confidence", "issue_link", "prediction"]
)
def test_feature_metadata_rejects_target_linking_fields(key: str) -> None:
    with pytest.raises(ValueError, match="metadata"):
        replace(_value(), metadata={"nested": {key: 1}})


def test_inventory_digest_is_stable_and_sensitive() -> None:
    first = _inventory()
    assert first == _inventory()
    changed_feature = _provenance(rationale="A scientifically different rationale.")
    assert first.inventory_digest != _inventory((changed_feature,)).inventory_digest
    with pytest.raises(ValueError, match="canonical"):
        replace(first, inventory_digest=SHA2)


def test_inventory_metadata_is_descriptive_but_provenance_metadata_is_identity() -> (
    None
):
    first = _inventory()
    descriptive = replace(first, metadata={"note": "different description"})
    assert descriptive.inventory_digest == first.inventory_digest
    changed = _inventory((_provenance(metadata={"temporal_cutoff": "strict"}),))
    assert changed.inventory_digest != first.inventory_digest
    changed_membership = ScientificFeatureInventory.calculate_digest(
        specification_digest=SHA,
        feature_provenance=first.feature_provenance,
        complete_scenario_feature_names=(),
        leakage_controlled_feature_names=(),
        prohibited_feature_names=(),
        review_required_feature_names=(),
    )
    assert changed_membership != first.inventory_digest


def test_inventory_category_consistency_and_subset_invariants() -> None:
    inventory = _inventory()
    with pytest.raises(ValueError, match="subset"):
        replace(
            inventory,
            complete_scenario_feature_names=(),
            leakage_controlled_feature_names=("lines_added",),
            inventory_digest=SHA,
        )
    with pytest.raises(ValueError, match="flags"):
        replace(
            inventory,
            complete_scenario_feature_names=(),
            leakage_controlled_feature_names=(),
            inventory_digest=SHA,
        )
    prohibited = _provenance(
        feature_name="unsafe",
        temporal_scope="label-derived",
        uses_target=True,
        leakage_risk="prohibited",
        disposition="prohibited",
        allowed_in_complete_scenario=False,
        allowed_in_leakage_controlled_scenario=False,
    )
    bad_digest = ScientificFeatureInventory.calculate_digest(
        specification_digest=SHA,
        feature_provenance=(prohibited,),
        complete_scenario_feature_names=("unsafe",),
        leakage_controlled_feature_names=(),
        prohibited_feature_names=("unsafe",),
        review_required_feature_names=(),
    )
    with pytest.raises(ValueError, match="flags"):
        ScientificFeatureInventory(
            SHA, (prohibited,), ("unsafe",), (), ("unsafe",), (), bad_digest
        )


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"observation_identifiers": ("c1", "c1")}, "unique"),
        ({"observation_timestamps": {}}, "timestamps"),
        ({"target_assignments": ()}, "target assignment"),
        ({"feature_values": (_value("orphan"),)}, "orphan"),
        ({"feature_values": (_value(), _value())}, "duplicate"),
        ({"feature_values": (_value(feature="unknown"),)}, "unknown"),
    ],
)
def test_assembly_input_rejects_inconsistent_observations(
    changes: dict[str, object], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        _assembly(**changes)


def test_assembly_rejects_prohibited_feature_and_controls_target_evidence() -> None:
    prohibited = _provenance(
        feature_name="unsafe",
        temporal_scope="label-derived",
        uses_target=True,
        leakage_risk="prohibited",
        disposition="prohibited",
        allowed_in_complete_scenario=False,
        allowed_in_leakage_controlled_scenario=False,
    )
    with pytest.raises(ValueError, match="ineligible|prohibited"):
        _assembly(
            feature_inventory=_inventory((prohibited,)),
            feature_values=(
                ScientificFeatureValueRecord(
                    "c1", "unsafe", "code", 1, SHA, "label-derived"
                ),
            ),
        )
    evidence = replace(_artifact("evidence", "target-evidence"), content_digest=SHA2)
    assembly = _assembly(source_artifacts=(_artifact(), evidence))
    assert evidence in assembly.source_artifacts
    assert (
        assembly.to_dict()["source_artifacts"][1]["artifact_role"] == "target-evidence"
    )
    with pytest.raises(ValueError, match="digest"):
        _assembly(
            source_artifacts=(_artifact(), evidence),
            feature_values=(replace(_value(), provenance_digest=SHA2),),
        )
    bad_provenance = _provenance(source_artifact="evidence")
    with pytest.raises(ValueError, match="provenance sources"):
        _assembly(
            source_artifacts=(_artifact(), evidence),
            feature_inventory=_inventory((bad_provenance,)),
        )

    candidate = replace(
        _artifact("candidates", "defect-inducing-candidate"),
        content_digest=SHA2,
    )
    with pytest.raises(ValueError, match="candidate artifact"):
        _assembly(
            source_artifacts=(_artifact(), candidate),
            feature_values=(replace(_value(), provenance_digest=SHA2),),
        )
    with pytest.raises(ValueError, match="candidate artifacts"):
        _assembly(
            source_artifacts=(_artifact(), candidate),
            feature_inventory=(
                _inventory((_provenance(source_artifact="candidates"),))
            ),
        )


def test_target_assignments_are_bound_to_official_target_contract() -> None:
    with pytest.raises(ValueError, match="outside target contract"):
        _assembly(target_assignments=(_assignment(label=7),))
    with pytest.raises(ValueError, match="requires evidence"):
        _assembly(target_assignments=(replace(_assignment(), evidence_identifiers=()),))
    negative = _assembly(target_assignments=(_assignment(label=0),))
    assert negative.target_assignments[0].evidence_identifiers == ()
    with pytest.raises(ValueError, match="field"):
        _assembly(target_assignments=(replace(_assignment(), target_field="other"),))


def test_string_labels_are_valid_only_when_declared_by_target_contract() -> None:
    contract = _target_contract("clean", "risky")
    accepted = _assembly(
        target_contract=contract,
        target_assignments=(_assignment(label="risky"),),
    )
    assert accepted.target_assignments[0].target_label == "risky"
    with pytest.raises(ValueError, match="outside target contract"):
        _assembly(
            target_contract=contract,
            target_assignments=(_assignment(label="defect-prone"),),
        )


def test_nested_assembly_collections_are_immutable_and_to_dict_is_detached() -> None:
    assembly = _assembly()
    with pytest.raises(TypeError):
        assembly.observation_timestamps["c1"] = "changed"
    detached = assembly.to_dict()
    detached["observation_timestamps"]["c1"] = "changed"
    detached["target_assignments"][0]["evidence_identifiers"].append("e2")
    assert assembly.observation_timestamps["c1"] == "2020-01-01T00:00:00Z"
    assert assembly.target_assignments[0].evidence_identifiers == ("e1",)


def test_manifest_counts_order_and_digest_invariants() -> None:
    manifest = _manifest()
    assert manifest.scientific_digest == _manifest().scientific_digest
    with pytest.raises(ValueError, match="positive and negative"):
        _manifest(target_negative_count=1)
    with pytest.raises(ValueError, match="stage_sequence"):
        _manifest(stage_sequence=tuple(contracts.ScientificBuilderStage)[:-1])
    with pytest.raises(ValueError, match="canonical"):
        replace(manifest, scientific_digest=SHA2)


def test_manifest_accepts_distinct_candidate_artifact_digest() -> None:
    candidate = replace(
        _artifact("candidates", "defect-inducing-candidate"),
        content_digest=SHA2,
    )
    manifest = _manifest(source_artifact_digests={"candidates": SHA2, "commits": SHA})
    assert manifest.source_artifact_digests["candidates"] == candidate.content_digest
    assert (
        candidate.artifact_role
        is contracts.ScientificArtifactRole.DEFECT_INDUCING_CANDIDATE
    )


def test_validation_invariants_and_deterministic_messages() -> None:
    result = ScientificDatasetBuildValidation(
        False, ("z", "a"), ("w2", "w1"), 0, 0, 0, 0, SHA, SHA
    )
    assert result.errors == ("a", "z")
    assert result.to_dict()["warnings"] == ["w1", "w2"]
    with pytest.raises(ValueError, match="exactly"):
        replace(result, is_valid=True)
    with pytest.raises(ValueError, match="non-negative"):
        replace(result, checked_feature_count=-1)


def test_build_result_consistency_and_no_tabular_content() -> None:
    manifest = _manifest()
    result = ScientificDatasetBuildResult(
        manifest, _validation(), 1, 1, (_artifact(),), manifest.output_artifacts
    )
    assert "feature_values" not in result.to_dict()
    with pytest.raises(ValueError, match="counts"):
        replace(result, assembled_feature_count=2)
    with pytest.raises(ValueError, match="source artifacts"):
        replace(result, source_artifacts=(_artifact("other"),))
    invalid = replace(_validation(), is_valid=False, errors=("failure",))
    with pytest.raises(ValueError, match="validation must be valid"):
        replace(result, validation=invalid)
