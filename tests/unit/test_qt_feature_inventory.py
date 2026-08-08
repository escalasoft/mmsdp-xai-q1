"""Focused Sprint 10.8.2.13 Qt feature-inventory tests."""

from dataclasses import replace

import pytest

from dataset.scientific_builder_contracts import (
    ScientificArtifactReference,
    ScientificArtifactRole,
)
from dataset.scientific_dataset_contract import ScientificFeatureModality
from feature_engineering.qt_feature_inventory import (
    QtFeatureAdmissibility,
    QtFeatureDataType,
    QtFeatureDefinition,
    QtFeatureInventory,
    QtFeatureLeakageClassification,
    QtFeatureMissingPolicy,
    build_qt_feature_inventory,
)

DIGEST_A = "a" * 64
DIGEST_B = "b" * 64


def artifact(
    name: str, role: ScientificArtifactRole, digest: str
) -> ScientificArtifactReference:
    return ScientificArtifactReference(
        artifact_name=name,
        artifact_role=role,
        repository_relative_path=f"artifacts/{name}.json",
        content_digest=digest,
        schema_version="1.0.0",
        record_count=2,
    )


def sources():
    return (
        artifact("qt-commits", ScientificArtifactRole.COMMIT_ARTIFACT, DIGEST_A),
        artifact("qt-diff-statistics", ScientificArtifactRole.CODE_FEATURE, DIGEST_B),
    )


def inventory():
    return build_qt_feature_inventory(*sources())


def test_generation_order_and_digest_are_deterministic() -> None:
    first = inventory()
    second = inventory()
    assert first == second
    assert first.inventory_digest == second.inventory_digest
    assert first.to_dict() == second.to_dict()
    keys = [(item.modality.value, item.feature_id) for item in first.features]
    modality_rank = {"code": 0, "process": 1, "text": 2}
    assert keys == sorted(keys, key=lambda item: (modality_rank[item[0]], item[1]))


def test_modality_views_are_separate_and_complete() -> None:
    value = inventory()
    views = value.by_modality()
    assert set(views) == {
        ScientificFeatureModality.CODE,
        ScientificFeatureModality.PROCESS,
        ScientificFeatureModality.TEXT,
    }
    assert all(
        item.modality is modality for modality, items in views.items() for item in items
    )
    assert sum(map(len, views.values())) == len(value.features)


def test_identity_is_bound_to_source_content_not_a_version_only() -> None:
    commits, stats = sources()
    changed = replace(stats, content_digest="c" * 64)
    assert (
        build_qt_feature_inventory(commits, stats).inventory_digest
        != build_qt_feature_inventory(commits, changed).inventory_digest
    )


@pytest.mark.parametrize(
    "role",
    [
        ScientificArtifactRole.TARGET_EVIDENCE,
        ScientificArtifactRole.DEFECT_INDUCING_CANDIDATE,
        ScientificArtifactRole.TARGET_ASSIGNMENT,
        ScientificArtifactRole.ISSUE_ARTIFACT,
        ScientificArtifactRole.DATASET,
    ],
)
def test_prohibited_source_roles_are_rejected(role) -> None:
    bad = artifact("forbidden", role, DIGEST_A)
    commits, stats = sources()
    with pytest.raises(ValueError, match="role|prohibited"):
        if role is ScientificArtifactRole.COMMIT_ARTIFACT:
            build_qt_feature_inventory(bad, stats)
        else:
            QtFeatureInventory(
                (bad,), (), QtFeatureInventory.calculate_digest((bad,), ())
            )


@pytest.mark.parametrize(
    "field",
    ["target", "label", "bug_confidence", "target_evidence", "candidate_record"],
)
def test_target_label_and_prohibited_metadata_are_rejected(field) -> None:
    with pytest.raises(ValueError, match="prohibited"):
        definition(feature_id="safe_name", source_fields=(field,))


@pytest.mark.parametrize(
    "name", ["msg_has_bug_kw", "contains_fix_keyword", "bug_keyword_indicator"]
)
def test_engineered_bug_fix_keyword_features_are_rejected(name) -> None:
    with pytest.raises(ValueError, match="prohibited"):
        definition(feature_id=name)


def test_raw_text_is_admissible_without_engineered_representation() -> None:
    raw = next(
        item for item in inventory().features if item.feature_id == "raw_commit_message"
    )
    assert raw.admissibility is QtFeatureAdmissibility.ADMISSIBLE
    assert raw.source_fields == ("message",)
    assert raw.data_type is QtFeatureDataType.UTF8_TEXT
    assert "without keyword indicators" in raw.construction_rule


def test_unavailable_process_features_have_no_value_construction() -> None:
    unavailable = [
        item
        for item in inventory().by_modality()[ScientificFeatureModality.PROCESS]
        if item.admissibility is QtFeatureAdmissibility.UNAVAILABLE
    ]
    assert {item.feature_id for item in unavailable} == {
        "developer_prior_experience",
        "prior_file_change_count",
        "time_since_previous_change",
    }
    assert all(
        item.missing_value_policy is QtFeatureMissingPolicy.UNAVAILABLE
        for item in unavailable
    )
    assert all(item.exclusion_reason for item in unavailable)


def test_prohibited_concepts_are_auditable_but_have_no_dependency() -> None:
    excluded = {
        item.feature_id: item
        for item in inventory().features
        if item.admissibility is QtFeatureAdmissibility.INADMISSIBLE
    }
    assert set(excluded) == {
        "bug_confidence",
        "commit_message_bug_fix_keyword_indicator",
        "future_defect_count",
        "target_label",
    }
    assert all(not item.source_fields for item in excluded.values())
    assert all(
        item.upstream_artifact == "prohibited:no-source-dependency"
        for item in excluded.values()
    )


def test_process_temporal_rule_requires_current_or_strictly_prior_cutoff() -> None:
    with pytest.raises(ValueError, match="cutoff"):
        definition(
            feature_id="developer_experience",
            modality=ScientificFeatureModality.PROCESS,
            temporal="Available from repository history.",
        )
    with pytest.raises(ValueError, match="future"):
        definition(
            feature_id="later_change_count",
            modality=ScientificFeatureModality.PROCESS,
            temporal="Available from future commits after candidate commit.",
        )


def test_inventory_is_independent_from_target_values() -> None:
    first = inventory()
    target_assignments_a = {"a": 0, "b": 1}
    target_assignments_b = {"a": 1, "b": 0}
    del target_assignments_a, target_assignments_b
    assert inventory().inventory_digest == first.inventory_digest
    assert all("target" not in item.upstream_artifact for item in first.features)


def definition(
    *,
    feature_id="safe_feature",
    source_fields=("safe_field",),
    modality=ScientificFeatureModality.CODE,
    temporal="Available at candidate commit from the current diff.",
):
    return QtFeatureDefinition(
        feature_id=feature_id,
        modality=modality,
        upstream_artifact="approved-source",
        source_fields=source_fields,
        temporal_availability_rule=temporal,
        construction_rule="Copy the named source field deterministically.",
        data_type=QtFeatureDataType.NON_NEGATIVE_INTEGER,
        missing_value_policy=QtFeatureMissingPolicy.NOT_MISSING,
        leakage_classification=QtFeatureLeakageClassification.ADMISSIBLE_COMMIT_CURRENT,
        admissibility=QtFeatureAdmissibility.ADMISSIBLE,
        exclusion_reason=None,
    )
