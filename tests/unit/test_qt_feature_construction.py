"""Focused Sprint 10.8.2.14 Qt feature-value construction tests."""

from dataclasses import replace

import pytest

import extraction.qt_commit_extraction as commit_module
import extraction.qt_diff_statistics_extraction as stats_module
from dataset.scientific_builder_contracts import (
    ScientificArtifactReference,
    ScientificArtifactRole,
)
from extraction.qt_commit_extraction import (
    QtCommitExtractionResult,
    QtCommitExtractionSpecification,
    ScientificCommitRecord,
)
from extraction.qt_diff_statistics_extraction import (
    QtDiffStatisticsExtractionResult,
    QtDiffStatisticsExtractor,
    QtDiffStatisticsSpecification,
)
from feature_engineering.qt_feature_construction import (
    QT_CODE_FEATURE_NAMES,
    QT_UNAVAILABLE_PROCESS_FEATURE_NAMES,
    construct_qt_code_features,
    construct_qt_multimodal_features,
)
from feature_engineering.qt_feature_inventory import build_qt_feature_inventory

REVISION = "f" * 40
COMMIT_A = "a" * 40
COMMIT_B = "b" * 40
SNAPSHOT_DIGEST = "1" * 64
SOURCE_DIFF_DIGEST = "2" * 64


def artifact(
    name: str,
    role: ScientificArtifactRole,
    digest: str,
    *,
    path: str | None = None,
    count: int = 2,
) -> ScientificArtifactReference:
    return ScientificArtifactReference(
        name,
        role,
        path or f"artifacts/{name}.jsonl",
        digest,
        "1.0.0",
        count,
    )


def statistics_result(*, changed: bool = False) -> QtDiffStatisticsExtractionResult:
    first = QtDiffStatisticsExtractor._statistics(COMMIT_A, ())
    second_values = {
        "commit_identifier": COMMIT_B,
        "file_statistics": (),
        "files_changed": 0,
        "files_added": 0,
        "files_modified": 0,
        "files_removed": 0,
        "files_renamed": 0,
        "files_copied": 0,
        "files_type_changed": 0,
        "text_files": 0,
        "binary_files": 0,
        "has_binary_files": False,
        "insertions": 0,
        "deletions": 0,
        "total_churn": 0,
    }
    if changed:
        # A scientifically valid relevant change without relying on file fixtures.
        second_values.update(
            files_changed=1,
            files_added=1,
            text_files=1,
            insertions=3,
            total_churn=3,
        )
        from extraction.qt_diff_statistics_extraction import QtFileDiffStatistics

        second_values["file_statistics"] = (
            QtFileDiffStatistics(
                COMMIT_B, "added", None, "new.txt", "new.txt", False, 3, 0, 3
            ),
        )
    second = stats_module.QtCommitDiffStatistics(
        **second_values,
        record_digest=stats_module._digest(second_values),
    )
    records = (first, second)
    specification = QtDiffStatisticsSpecification(
        "qtbase",
        "https://code.qt.io/qt/qtbase.git",
        REVISION,
        SOURCE_DIFF_DIGEST,
        "1.0.0",
    )
    source = artifact(
        "qtbase-diffs",
        ScientificArtifactRole.DIFF_ARTIFACT,
        SOURCE_DIFF_DIGEST,
    )
    content = {
        "repository_revision": REVISION,
        "source_diff_artifact_digest": SOURCE_DIFF_DIGEST,
        "extraction_policy_version": "1.0.0",
        "policies": {
            name: getattr(specification, name) for name in stats_module._POLICIES
        },
        "commit_statistics": records,
    }
    digest = stats_module._digest(content)
    output = artifact(
        "qtbase-diff-statistics",
        ScientificArtifactRole.DIFF_ARTIFACT,
        digest,
        path=f"artifacts/qtbase/diff-statistics/{REVISION}/qt-diff-statistics.jsonl",
        count=sum(item.files_changed for item in records),
    )
    identity = stats_module._digest(
        {
            "artifact_content_digest": digest,
            "source_diff_artifact_digest": SOURCE_DIFF_DIGEST,
            "repository_revision": REVISION,
            "extraction_policy_version": "1.0.0",
        }
    )
    return QtDiffStatisticsExtractionResult(
        specification,
        source,
        records,
        output,
        2,
        sum(item.files_changed for item in records),
        sum(item.insertions for item in records),
        sum(item.deletions for item in records),
        sum(item.total_churn for item in records),
        sum(item.binary_files for item in records),
        identity,
    )


def commit_result(
    *, message: str = "Fix nothing; preserve raw text.\n"
) -> QtCommitExtractionResult:
    specification = QtCommitExtractionSpecification("1.0.0")
    records = (
        ScientificCommitRecord(
            COMMIT_B,
            ("c" * 40, "d" * 40),
            "B",
            "b@example.invalid",
            "2001-01-02T00:00:00+00:00",
            "B",
            "b@example.invalid",
            "2001-01-02T00:00:00+00:00",
            message,
        ),
        ScientificCommitRecord(
            COMMIT_A,
            (),
            "A",
            "a@example.invalid",
            "2001-01-01T00:00:00+00:00",
            "A",
            "a@example.invalid",
            "2001-01-01T00:00:00+00:00",
            "root\n",
        ),
    )
    payload = {
        "schema_version": "1.0.0",
        "artifact_role": ScientificArtifactRole.COMMIT_ARTIFACT.value,
        "source_repository": "qtbase",
        "source_revision": REVISION,
        "source_snapshot_digest": SNAPSHOT_DIGEST,
        "object_hash_algorithm": "sha1",
        "ordering_policy": specification.ordering_policy,
        "records": records,
    }
    digest = commit_module.hashlib.sha256(
        commit_module._canonical_bytes(payload)
    ).hexdigest()
    return QtCommitExtractionResult(
        specification,
        REVISION,
        SNAPSHOT_DIGEST,
        "sha1",
        records,
        artifact(
            "qtbase-commits",
            ScientificArtifactRole.COMMIT_ARTIFACT,
            digest,
            path="artifacts/raw/qtbase-commits.json",
        ),
        specification.ordering_policy,
        ("git:cat-file:completed",),
    )


def construction(*, message: str = "Fix nothing; preserve raw text.\n", changed=False):
    commits = commit_result(message=message)
    stats = statistics_result(changed=changed)
    code = construct_qt_code_features(stats)
    inventory = build_qt_feature_inventory(commits.artifact, code.artifact)
    return (
        commits,
        stats,
        code,
        inventory,
        construct_qt_multimodal_features(commits, code, inventory),
    )


def test_diff_artifact_is_unchanged_and_code_boundary_has_exact_mapping() -> None:
    source = statistics_result(changed=True)
    before = source.to_dict()
    result = construct_qt_code_features(source)
    assert source.to_dict() == before
    assert (
        source.extraction_artifact.artifact_role is ScientificArtifactRole.DIFF_ARTIFACT
    )
    assert result.artifact.artifact_role is ScientificArtifactRole.CODE_FEATURE
    assert tuple(result.records[1].feature_values()) == QT_CODE_FEATURE_NAMES
    assert result.records[1].feature_values() == {
        "binary_files": 0,
        "deletions": 0,
        "files_added": 1,
        "files_changed": 1,
        "files_copied": 0,
        "files_modified": 0,
        "files_removed": 0,
        "files_renamed": 0,
        "files_type_changed": 0,
        "has_binary_files": 0,
        "insertions": 3,
        "text_files": 1,
        "total_churn": 3,
    }


def test_code_derivation_and_identity_are_deterministic_and_content_bound() -> None:
    one = construct_qt_code_features(statistics_result())
    two = construct_qt_code_features(statistics_result())
    changed = construct_qt_code_features(statistics_result(changed=True))
    assert one == two
    assert one.to_dict() == two.to_dict()
    assert one.artifact.content_digest == two.artifact.content_digest
    assert one.code_feature_identity_digest == two.code_feature_identity_digest
    assert changed.artifact.content_digest != one.artifact.content_digest
    assert changed.code_feature_identity_digest != one.code_feature_identity_digest
    assert one.source_diff_statistics_artifact.content_digest == (
        statistics_result().extraction_artifact.content_digest
    )


def test_one_canonical_modality_separated_record_per_eligible_commit() -> None:
    _, _, _, _, result = construction()
    assert tuple(item.commit_identifier for item in result.records) == (
        COMMIT_A,
        COMMIT_B,
    )
    assert len(result.records) == 2
    assert tuple(item.artifact_role for item in result.modality_artifacts) == (
        ScientificArtifactRole.CODE_FEATURE,
        ScientificArtifactRole.PROCESS_FEATURE,
        ScientificArtifactRole.TEXT_FEATURE,
    )


def test_process_values_raw_text_and_unavailable_features_are_exact() -> None:
    raw = "Fix BUG-7?\nDo not transform café.\n"
    _, _, _, _, result = construction(message=raw)
    by_id = {item.commit_identifier: item for item in result.records}
    assert by_id[COMMIT_A].process == {"is_merge_commit": 0, "parent_count": 0}
    assert by_id[COMMIT_B].process == {"is_merge_commit": 1, "parent_count": 2}
    assert by_id[COMMIT_B].text == {"raw_commit_message": raw}
    assert by_id[COMMIT_B].unavailable_process_features == (
        QT_UNAVAILABLE_PROCESS_FEATURE_NAMES
    )


def test_multimodal_provenance_and_identity_bind_all_scientific_inputs() -> None:
    commits, _, code, inventory, result = construction()
    assert result.repository_snapshot_digest == commits.source_snapshot_digest
    assert result.source_commit_artifact == commits.artifact
    assert result.source_code_feature_artifact == code.artifact
    assert result.feature_inventory_digest == inventory.inventory_digest
    assert result == construction()[-1]
    assert construction(message="changed\n")[-1].construction_identity_digest != (
        result.construction_identity_digest
    )
    assert construction(changed=True)[-1].construction_identity_digest != (
        result.construction_identity_digest
    )


@pytest.mark.parametrize(
    "role",
    [
        ScientificArtifactRole.TARGET_EVIDENCE,
        ScientificArtifactRole.DEFECT_INDUCING_CANDIDATE,
        ScientificArtifactRole.TARGET_ASSIGNMENT,
        ScientificArtifactRole.ISSUE_ARTIFACT,
    ],
)
def test_target_candidate_and_issue_artifacts_cannot_enter_code_boundary(role) -> None:
    valid = construct_qt_code_features(statistics_result())
    forbidden = artifact("forbidden", role, "9" * 64)
    with pytest.raises(ValueError, match="diff-artifact"):
        replace(valid, source_diff_statistics_artifact=forbidden)


@pytest.mark.parametrize(
    "metadata",
    [
        {"target": 1},
        {"label": 0},
        {"bug_confidence": 0.9},
        {"candidate_artifact": "x"},
        {"contains_fix_keyword": True},
        {"future_information": 3},
    ],
)
def test_leakage_prone_metadata_is_rejected(metadata) -> None:
    valid = construct_qt_code_features(statistics_result())
    with pytest.raises(ValueError, match="prohibited"):
        replace(valid, metadata=metadata)


def test_leakage_prone_upstream_artifact_metadata_cannot_cross_boundary() -> None:
    source = statistics_result()
    tainted_artifact = replace(
        source.extraction_artifact, metadata={"bug_confidence": 0.9}
    )
    tainted_source = replace(source, extraction_artifact=tainted_artifact)
    with pytest.raises(ValueError, match="prohibited"):
        construct_qt_code_features(tainted_source)


def test_inventory_must_bind_exact_approved_sources_and_commit_sets() -> None:
    commits, _, code, inventory, _ = construction()
    wrong_inventory = build_qt_feature_inventory(
        commits.artifact,
        replace(code.artifact, content_digest="8" * 64),
    )
    with pytest.raises(ValueError, match="exact commit and CODE"):
        construct_qt_multimodal_features(commits, code, wrong_inventory)
    with pytest.raises(ValueError, match="artifact identity"):
        replace(code, records=code.records[:1])


def test_domains_and_canonical_record_identity_are_enforced() -> None:
    valid = construct_qt_code_features(statistics_result())
    with pytest.raises(ValueError, match="canonical integer"):
        replace(valid.records[0], has_binary_files=2)
    with pytest.raises(ValueError, match="canonical CODE content"):
        replace(valid.records[0], binary_files=1, has_binary_files=1)


def test_no_prohibited_dependency_vocabulary_exists_in_scientific_content() -> None:
    _, _, code, _, result = construction()
    scientific = {"code": code.to_dict(), "multimodal": result.to_dict()}
    serialized = stats_module.json.dumps(scientific, sort_keys=True)
    for prohibited in (
        '"target"',
        '"label"',
        '"bug_confidence"',
        '"candidate_artifact"',
        '"target_assignment"',
        '"target_evidence"',
    ):
        assert prohibited not in serialized
