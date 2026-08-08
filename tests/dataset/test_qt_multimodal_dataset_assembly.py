"""Focused Sprint 10.8.2.15 Qt multimodal dataset assembly tests."""

from __future__ import annotations

import hashlib
import runpy
from dataclasses import replace
from pathlib import Path

import pytest

import extraction.qt_commit_extraction as commit_module
from dataset.qt_multimodal_dataset_assembly import (
    QtDatasetAssemblyError,
    QtDatasetAssemblyPolicy,
    QtDatasetObservation,
    assemble_qt_multimodal_dataset,
    build_qt_dataset_assembly_specification,
)
from dataset.qt_target_assignment_contracts import QtTargetAssignmentPolicy
from dataset.scientific_builder_contracts import (
    ScientificArtifactReference,
    ScientificTargetAssignment,
)
from dataset.scientific_target_assignment_contracts import (
    ScientificTargetAssignmentArtifactBinding,
    ScientificTargetAssignmentResult,
    ScientificTargetAssignmentSpecification,
    ScientificTargetAssignmentValidation,
)
from feature_engineering.qt_feature_construction import (
    QT_CODE_FEATURE_NAMES,
    QT_UNAVAILABLE_PROCESS_FEATURE_NAMES,
    construct_qt_multimodal_features,
)
from feature_engineering.qt_feature_inventory import build_qt_feature_inventory

_FEATURE_HELPERS = runpy.run_path(
    str(Path(__file__).parents[1] / "unit" / "test_qt_feature_construction.py")
)
COMMIT_A = _FEATURE_HELPERS["COMMIT_A"]
COMMIT_B = _FEATURE_HELPERS["COMMIT_B"]
construction = _FEATURE_HELPERS["construction"]


def _with_committed_at(committed_at: str):
    built = construction()
    commits, code = built[0], built[2]
    records = tuple(
        replace(item, committed_at=committed_at) if item.commit_id == COMMIT_B else item
        for item in commits.records
    )
    payload = {
        "schema_version": commits.specification.schema_version,
        "artifact_role": "commit-artifact",
        "source_repository": "qtbase",
        "source_revision": commits.source_revision,
        "source_snapshot_digest": commits.source_snapshot_digest,
        "object_hash_algorithm": commits.object_hash_algorithm,
        "ordering_policy": commits.ordering_policy,
        "records": records,
    }
    artifact = replace(
        commits.artifact,
        content_digest=hashlib.sha256(
            commit_module._canonical_bytes(payload)
        ).hexdigest(),
    )
    changed_commits = replace(commits, records=records, artifact=artifact)
    inventory = build_qt_feature_inventory(artifact, code.artifact)
    features = construct_qt_multimodal_features(changed_commits, code, inventory)
    return changed_commits, features


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _targets(features, labels=None) -> ScientificTargetAssignmentResult:
    labels = labels or {COMMIT_A: 0, COMMIT_B: 1}
    policy = QtTargetAssignmentPolicy.create().scientific_policy
    spec_values = {
        "schema_version": "1.0.0",
        "specification_version": "qt-target-specification-1.0.0",
        "repository_snapshot_digest": features.repository_snapshot_digest,
        "commit_artifact_digest": features.source_commit_artifact.content_digest,
        "candidate_artifact_digest": "3" * 64,
        "candidate_binding_digest": "4" * 64,
        "candidate_specification_digest": "5" * 64,
        "candidate_policy_digest": "6" * 64,
        "policy_digest": policy.policy_digest,
    }
    specification = ScientificTargetAssignmentSpecification(
        **spec_values,
        specification_digest=ScientificTargetAssignmentSpecification.calculate_digest(
            **spec_values
        ),
    )
    assignments = tuple(
        ScientificTargetAssignment(
            identifier,
            policy.target_field,
            labels[identifier],
            policy.policy_version,
            (f"candidate-{identifier}",) if labels[identifier] else (),
            "frozen assignment",
        )
        for identifier in sorted(labels)
    )
    artifact = ScientificArtifactReference(
        "qtbase-target-assignments",
        "target-assignment",
        "artifacts/derived/qtbase-target-assignments.json",
        _digest(
            repr(tuple((x.observation_identifier, x.target_label) for x in assignments))
        ),
        "1.0.0",
        len(assignments),
    )
    binding_values = {
        "artifact": artifact,
        "specification_digest": specification.specification_digest,
        "policy_digest": policy.policy_digest,
        "candidate_artifact_digest": specification.candidate_artifact_digest,
        "ordered_observation_identifiers": tuple(
            item.observation_identifier for item in assignments
        ),
        "ordered_trace_identifiers": (),
    }
    binding = ScientificTargetAssignmentArtifactBinding(
        **binding_values,
        binding_digest=ScientificTargetAssignmentArtifactBinding.calculate_digest(
            **binding_values
        ),
    )
    positives = sum(item.target_label == 1 for item in assignments)
    validation = ScientificTargetAssignmentValidation(
        True,
        len(assignments),
        len(assignments),
        positives,
        len(assignments) - positives,
        0,
        0,
    )
    return ScientificTargetAssignmentResult(
        specification, policy, assignments, (), validation, binding
    )


def _assembly(
    *, changed=False, message="Fix nothing; preserve raw text.\n", labels=None
):
    built = construction(changed=changed, message=message)
    commits, features = built[0], built[-1]
    targets = _targets(features, labels)
    policy = QtDatasetAssemblyPolicy.create()
    specification = build_qt_dataset_assembly_specification(
        commits, features, targets, policy
    )
    return (
        commits,
        features,
        targets,
        assemble_qt_multimodal_dataset(
            commits, features, targets, specification, policy
        ),
    )


def test_exact_observation_schema_and_feature_target_separation() -> None:
    commits, features, targets, result = _assembly()
    assert tuple(item.commit_identifier for item in result.observations) == (
        COMMIT_A,
        COMMIT_B,
    )
    assert (
        result.validation.observation_count
        == len(features.records)
        == len(targets.assignments)
    )
    row = result.observations[1]
    assert tuple(row.code_features) == QT_CODE_FEATURE_NAMES
    assert tuple(row.process_features) == ("is_merge_commit", "parent_count")
    assert tuple(row.text_features) == ("raw_commit_message",)
    assert row.text_features["raw_commit_message"] == (
        "Fix nothing; preserve raw text.\n"
    )
    assert set(row.predictive_features()) == {"code", "process", "text"}
    assert "target" not in row.predictive_features()
    assert "commit_identifier" not in row.predictive_features()
    assert "committed_at" not in row.predictive_features()
    assert row.committed_at == next(
        item.committed_at for item in commits.records if item.commit_id == COMMIT_B
    )
    assert row.target == next(
        item.target_label
        for item in targets.assignments
        if item.observation_identifier == COMMIT_B
    )
    assert features.records[1].unavailable_process_features == (
        QT_UNAVAILABLE_PROCESS_FEATURE_NAMES
    )


def test_join_is_commit_based_and_independent_of_input_iteration_order() -> None:
    commits, features, targets, expected = _assembly()
    object.__setattr__(commits, "records", tuple(reversed(commits.records)))
    object.__setattr__(features, "records", tuple(reversed(features.records)))
    object.__setattr__(targets, "assignments", tuple(reversed(targets.assignments)))
    actual = assemble_qt_multimodal_dataset(
        commits,
        features,
        targets,
        build_qt_dataset_assembly_specification(commits, features, targets),
        QtDatasetAssemblyPolicy.create(),
    )
    assert actual.observations == expected.observations
    assert actual.assembly_identity_digest == expected.assembly_identity_digest


@pytest.mark.parametrize("side", ["commit", "feature", "target"])
def test_duplicate_commit_identity_fails_explicitly(side) -> None:
    commits, features, targets, _ = _assembly()
    if side == "commit":
        object.__setattr__(commits, "records", commits.records + (commits.records[0],))
    elif side == "feature":
        object.__setattr__(
            features, "records", features.records + (features.records[0],)
        )
    else:
        object.__setattr__(
            targets, "assignments", targets.assignments + (targets.assignments[0],)
        )
    specification = build_qt_dataset_assembly_specification(commits, features, targets)
    with pytest.raises(QtDatasetAssemblyError, match=f"duplicate {side}"):
        assemble_qt_multimodal_dataset(
            commits, features, targets, specification, QtDatasetAssemblyPolicy.create()
        )


@pytest.mark.parametrize("side", ["commit", "feature", "target"])
def test_missing_join_identity_fails_without_silent_exclusion(side) -> None:
    commits, features, targets, _ = _assembly()
    if side == "commit":
        object.__setattr__(commits, "records", commits.records[:-1])
    elif side == "feature":
        object.__setattr__(features, "records", features.records[:-1])
    else:
        object.__setattr__(targets, "assignments", targets.assignments[:-1])
    specification = build_qt_dataset_assembly_specification(commits, features, targets)
    with pytest.raises(QtDatasetAssemblyError, match="eligible universes differ"):
        assemble_qt_multimodal_dataset(
            commits, features, targets, specification, QtDatasetAssemblyPolicy.create()
        )


@pytest.mark.parametrize(
    "mapping_name,bad_mapping",
    [
        ("code_features", {**dict.fromkeys(QT_CODE_FEATURE_NAMES, 0), "target": 1}),
        ("process_features", {"is_merge_commit": 0, "parent_count": 0, "label": 0}),
        ("text_features", {"raw_commit_message": "x", "issue_content": "secret"}),
    ],
)
def test_predictor_schema_rejects_leakage_and_provenance_keys(
    mapping_name, bad_mapping
) -> None:
    _, _, _, result = _assembly()
    values = result.observations[0].to_dict()
    values.pop("observation_digest")
    values[mapping_name] = bad_mapping
    with pytest.raises(ValueError):
        QtDatasetObservation(
            **values,
            observation_digest=QtDatasetObservation.calculate_digest(**values),
        )


def test_provenance_binds_approved_artifacts_and_rejects_other_specifications() -> None:
    commits, features, targets, result = _assembly()
    spec = result.specification
    assert spec.repository_snapshot_digest == features.repository_snapshot_digest
    assert spec.commit_artifact_digest == features.source_commit_artifact.content_digest
    assert spec.feature_inventory_digest == features.feature_inventory_digest
    assert spec.multimodal_construction_identity_digest == (
        features.construction_identity_digest
    )
    assert spec.target_assignment_artifact_digest == (
        targets.artifact_binding.artifact.content_digest
    )
    assert spec.target_assignment_specification_digest == (
        targets.specification.specification_digest
    )
    altered_values = spec.to_dict()
    altered_values.pop("specification_digest")
    altered_values["feature_inventory_digest"] = "9" * 64
    altered = type(spec)(
        **altered_values,
        specification_digest=spec.calculate_digest(**altered_values),
    )
    with pytest.raises(QtDatasetAssemblyError, match="does not bind exact inputs"):
        assemble_qt_multimodal_dataset(
            commits, features, targets, altered, QtDatasetAssemblyPolicy.create()
        )


def test_feature_and_target_upstream_identities_must_agree() -> None:
    commits, features, targets, _ = _assembly()
    object.__setattr__(targets.specification, "commit_artifact_digest", "8" * 64)
    with pytest.raises(QtDatasetAssemblyError, match="same snapshot and commits"):
        build_qt_dataset_assembly_specification(commits, features, targets)


@pytest.mark.parametrize(
    "field,value",
    [
        ("artifact", None),
        ("source_snapshot_digest", "7" * 64),
        ("source_revision", "7" * 40),
    ],
)
def test_commit_extraction_must_bind_the_exact_feature_source(field, value) -> None:
    commits, features, targets, _ = _assembly()
    if field == "artifact":
        value = replace(commits.artifact, content_digest="7" * 64)
    object.__setattr__(commits, field, value)
    with pytest.raises(QtDatasetAssemblyError, match="same scientific source"):
        build_qt_dataset_assembly_specification(commits, features, targets)


def test_assembly_policy_is_frozen() -> None:
    with pytest.raises(ValueError, match="frozen Qt policy"):
        QtDatasetAssemblyPolicy(
            unit_of_analysis="file",
            policy_digest=QtDatasetAssemblyPolicy.calculate_digest(),
        )


def test_identity_is_repeatable_and_changes_with_features_or_target() -> None:
    first = _assembly()[3]
    repeated = _assembly()[3]
    changed_feature = _assembly(changed=True)[3]
    changed_target = _assembly(labels={COMMIT_A: 1, COMMIT_B: 0})[3]
    assert first.to_dict() == repeated.to_dict()
    assert first.assembly_identity_digest == repeated.assembly_identity_digest
    assert changed_feature.assembly_identity_digest != first.assembly_identity_digest
    assert changed_target.assembly_identity_digest != first.assembly_identity_digest


def test_authoritative_committed_at_changes_observation_and_dataset_identity() -> None:
    original = _assembly()[3]
    commits, features = _with_committed_at("2002-02-03T04:05:06+00:00")
    targets = _targets(features)
    policy = QtDatasetAssemblyPolicy.create()
    specification = build_qt_dataset_assembly_specification(
        commits, features, targets, policy
    )
    changed = assemble_qt_multimodal_dataset(
        commits, features, targets, specification, policy
    )
    original_row = next(
        item for item in original.observations if item.commit_identifier == COMMIT_B
    )
    changed_row = next(
        item for item in changed.observations if item.commit_identifier == COMMIT_B
    )
    assert changed_row.committed_at == "2002-02-03T04:05:06+00:00"
    assert changed_row.observation_digest != original_row.observation_digest
    assert changed.assembly_identity_digest != original.assembly_identity_digest


def test_raw_text_keywords_are_not_used_to_validate_or_alter_target() -> None:
    ordinary = _assembly(message="ordinary text\n")[3]
    keywords = _assembly(message="BUG FIX target label candidate issue\n")[3]
    assert [item.target for item in ordinary.observations] == [
        item.target for item in keywords.observations
    ]
    assert keywords.observations[1].text_features["raw_commit_message"] == (
        "BUG FIX target label candidate issue\n"
    )


def test_runtime_metadata_is_excluded_from_identity_and_forbidden_when_sensitive() -> (
    None
):
    commits, features, targets, result = _assembly()
    specification = build_qt_dataset_assembly_specification(commits, features, targets)
    with_metadata = assemble_qt_multimodal_dataset(
        commits,
        features,
        targets,
        specification,
        QtDatasetAssemblyPolicy.create(),
        metadata={"note": "non-scientific annotation"},
    )
    assert with_metadata.assembly_identity_digest == result.assembly_identity_digest
    assert [item.committed_at for item in with_metadata.observations] == [
        item.committed_at for item in result.observations
    ]
    with pytest.raises(ValueError, match="runtime field"):
        assemble_qt_multimodal_dataset(
            commits,
            features,
            targets,
            specification,
            QtDatasetAssemblyPolicy.create(),
            metadata={"hostname": "worker"},
        )


def test_no_model_or_experiment_execution_dependency_is_introduced() -> None:
    import dataset.qt_multimodal_dataset_assembly as module

    source_names = set(module.__dict__)
    assert not source_names & {
        "train_test_split",
        "TemporalSplitter",
        "calibrate",
        "ExplanationRunner",
        "ExperimentRunner",
    }
