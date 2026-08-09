"""Minimal reproducible end-to-end materialization of the approved Qt dataset."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from dataclasses import fields, is_dataclass
from enum import Enum
from pathlib import Path
from types import MappingProxyType

import extraction.qt_commit_issue_linking as link_module
import extraction.qt_issue_extraction as issue_module
from dataset.qt_candidate_construction import QtCandidateConstructor
from dataset.qt_candidate_construction_contracts import (
    QtCandidateConstructionPolicy,
    QtCandidateConstructionSpecification,
)
from dataset.qt_model_input_adaptation import adapt_qt_model_inputs
from dataset.qt_multimodal_dataset_assembly import (
    QtDatasetAssemblyPolicy,
    assemble_qt_multimodal_dataset,
    build_qt_dataset_assembly_specification,
)
from dataset.qt_target_assignment import QtTargetAssigner
from dataset.qt_target_assignment_contracts import (
    QtTargetAssignmentPolicy,
    QtTargetAssignmentSpecification,
)
from dataset.qt_target_evidence_construction import (
    QtTargetEvidenceConstructor,
    QtTargetEvidenceSpecification,
)
from dataset.qt_temporal_dataset_split import (
    QtTemporalSplitPolicy,
    build_qt_temporal_split_specification,
    split_qt_temporal_dataset,
)
from dataset.scientific_candidate_contracts import (
    ScientificCandidateConstructionSpecification,
)
from dataset.scientific_target_assignment_contracts import (
    ScientificTargetAssignmentSpecification,
)
from extraction.qt_commit_extraction import (
    QtCommitExtractionSpecification,
    QtCommitExtractor,
)
from extraction.qt_commit_issue_linking import (
    QtCommitIssueLinker,
    QtCommitIssueLinkSpecification,
)
from extraction.qt_diff_extraction import QtDiffExtractionSpecification, QtDiffExtractor
from extraction.qt_diff_statistics_extraction import (
    QtDiffStatisticsExtractor,
    QtDiffStatisticsSpecification,
)
from extraction.qt_issue_extraction import (
    QtIssueExtractionSpecification,
    QtIssueExtractor,
)
from extraction.qt_jira_cloud_acquisition import (
    CANONICAL_SOURCE as JIRA_SOURCE,
)
from extraction.qt_jira_cloud_acquisition import (
    PROJECT_IDENTIFIER,
    acquire_qtbug_issues,
)
from extraction.qt_jira_cloud_acquisition import (
    SCHEMA_VERSION as JIRA_SCHEMA_VERSION,
)
from extraction.qt_repository_acquisition import (
    QtRepositoryAcquirer,
    QtRepositoryAcquisitionSpecification,
)
from feature_engineering.qt_feature_construction import (
    construct_qt_code_features,
    construct_qt_multimodal_features,
)
from feature_engineering.qt_feature_inventory import build_qt_feature_inventory

_QTBUG = re.compile(r"(?<![A-Za-z0-9-])QTBUG-[0-9]+(?![A-Za-z0-9-])")
_ROOT = Path(__file__).resolve().parents[2]


def _load(name: str) -> dict[str, object]:
    value = json.loads((_ROOT / "configs" / name).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{name} must contain one JSON object")
    return value


def _thaw(value: object) -> object:
    if is_dataclass(value) and not isinstance(value, type):
        return {item.name: _thaw(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, MappingProxyType):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, dict):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    if isinstance(value, list):
        return [_thaw(item) for item in value]
    if isinstance(value, Enum):
        return value.value
    return value


def _bytes(value: object, *, newline: bool = True) -> bytes:
    result = json.dumps(
        _thaw(value),
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return result + (b"\n" if newline else b"")


def _write(path: Path, value: object, *, newline: bool = True) -> str:
    content = _bytes(value, newline=newline)
    if path.exists():
        if path.read_bytes() != content:
            raise FileExistsError(
                f"immutable materialization artifact disagrees with rerun: {path}"
            )
        return hashlib.sha256(content).hexdigest()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return hashlib.sha256(content).hexdigest()


def _artifact_path(root: Path, repository_relative_path: str) -> Path:
    return root / repository_relative_path


def materialize(repository_path: Path, output_root: Path) -> dict[str, object]:
    repository_config = _load("qt_repository_acquisition.json")
    acquisition_spec = QtRepositoryAcquisitionSpecification(
        repository_name=repository_config["repository_name"],
        canonical_repository_url=repository_config["canonical_repository_url"],
        transport_repository_url=repository_config["transport_repository_url"],
        requested_reference=repository_config["requested_reference"],
        default_branch=repository_config["default_branch"],
        acquisition_policy_version=repository_config["acquisition_policy_version"],
        allowed_hash_algorithms=tuple(repository_config["allowed_hash_algorithms"]),
        metadata=repository_config["metadata"],
    )
    acquisition = QtRepositoryAcquirer().acquire(acquisition_spec, repository_path)
    acquisition_path = _artifact_path(
        output_root, acquisition.acquisition_artifact.repository_relative_path
    )
    _write(acquisition_path, acquisition.to_dict())

    commit_config = _load("qt_commit_extraction.json")
    commit_spec = QtCommitExtractionSpecification(
        schema_version=commit_config["schema_version"],
        artifact_repository_relative_path=commit_config[
            "artifact_repository_relative_path"
        ],
        ordering_policy=commit_config["ordering_policy"],
        observation_window_start=commit_config["observation_window_start"],
        observation_window_end=commit_config["observation_window_end"],
        metadata=commit_config["metadata"],
    )
    commit_path = _artifact_path(
        output_root, commit_spec.artifact_repository_relative_path
    )
    commit_path.parent.mkdir(parents=True, exist_ok=True)
    commits = QtCommitExtractor().extract(
        acquisition, repository_path, commit_path, commit_spec
    )
    referenced_identifiers = tuple(
        sorted(
            {
                match.group(0)
                for record in commits.records
                for match in _QTBUG.finditer(record.message)
            }
        )
    )
    if not referenced_identifiers:
        raise RuntimeError(
            "approved commit universe contains no exact QTBUG references"
        )

    jira_root = (
        output_root / "data" / "external" / "qtbug" / acquisition.resolved_revision
    )
    jira_manifest = acquire_qtbug_issues(referenced_identifiers, jira_root)
    normalized_issue_path = Path(jira_manifest["paths"]["normalized"])
    issue_source_digest = jira_manifest["normalized_source_sha256"]
    issue_source_revision = f"qtbug-cloud-{issue_source_digest[:16]}"
    issue_spec = QtIssueExtractionSpecification(
        project_name="qtbase",
        canonical_issue_source=JIRA_SOURCE,
        source_revision=issue_source_revision,
        source_artifact_digest=issue_source_digest,
        project_identifier=PROJECT_IDENTIFIER,
        issue_schema_version=JIRA_SCHEMA_VERSION,
        extraction_policy_version="1.0.0",
    )
    issues = QtIssueExtractor().extract(issue_spec, normalized_issue_path)
    issue_artifact_path = _artifact_path(
        output_root, issues.extraction_artifact.repository_relative_path
    )
    issue_artifact_content = issue_module._artifact_content(issue_spec, issues.issues)
    issue_file_digest = _write(
        issue_artifact_path, issue_artifact_content, newline=False
    )
    if issue_file_digest != issues.extraction_artifact.content_digest:
        raise RuntimeError("persisted issue artifact identity disagrees with contract")

    link_spec = QtCommitIssueLinkSpecification(
        schema_version="1.0.0",
        commit_artifact_digest=commits.artifact.content_digest,
        issue_artifact_digest=issues.extraction_artifact.content_digest,
    )
    links = QtCommitIssueLinker().link(link_spec, commit_path, issue_artifact_path)
    link_path = _artifact_path(output_root, link_spec.artifact_repository_relative_path)
    link_file_digest = _write(
        link_path, link_module._result_content(link_spec, links.links)
    )
    if link_file_digest != links.artifact_digest:
        raise RuntimeError(
            "persisted linking artifact identity disagrees with contract"
        )

    diff_spec = QtDiffExtractionSpecification(
        repository_name="qtbase",
        canonical_repository_url=acquisition.canonical_repository_url,
        repository_revision=acquisition.resolved_revision,
        commit_artifact_digest=commits.artifact.content_digest,
        extraction_policy_version="2.0.0",
    )
    diffs = QtDiffExtractor().extract(
        diff_spec, repository_path, acquisition.repository_snapshot, commits
    )
    diff_path = _artifact_path(
        output_root, diffs.extraction_artifact.repository_relative_path
    )
    _write(diff_path, diffs.to_dict())

    statistics_spec = QtDiffStatisticsSpecification(
        repository_name="qtbase",
        canonical_repository_url=acquisition.canonical_repository_url,
        repository_revision=acquisition.resolved_revision,
        diff_artifact_digest=diffs.extraction_artifact.content_digest,
        extraction_policy_version="1.0.0",
    )
    statistics = QtDiffStatisticsExtractor().extract(statistics_spec, diffs)
    statistics_path = _artifact_path(
        output_root, statistics.extraction_artifact.repository_relative_path
    )
    _write(statistics_path, statistics.to_dict())

    evidence_spec = QtTargetEvidenceSpecification(
        "qtbase",
        commits.artifact.content_digest,
        issues.extraction_artifact.content_digest,
        links.artifact_digest,
        "qt-target-evidence-policy-1.0.0",
    )
    evidence = QtTargetEvidenceConstructor().construct(
        evidence_spec, commits, issues, links
    )
    evidence_path = _artifact_path(
        output_root, evidence.evidence_artifact.repository_relative_path
    )
    _write(evidence_path, evidence.to_dict())

    candidate_policy = QtCandidateConstructionPolicy.create()
    candidate_values = {
        "schema_version": "1.0.0",
        "specification_version": "qt-candidate-specification-1.0.0",
        "repository_snapshot_digest": acquisition.repository_snapshot.snapshot_digest,
        "commit_artifact_digest": commits.artifact.content_digest,
        "issue_artifact_digest": issues.extraction_artifact.content_digest,
        "commit_issue_link_artifact_digest": links.artifact_digest,
        "target_evidence_artifact_digest": evidence.evidence_artifact.content_digest,
        "diff_artifact_digest": diffs.extraction_artifact.content_digest,
        "policy_digest": candidate_policy.scientific_policy.policy_digest,
    }
    candidate_scientific_spec = ScientificCandidateConstructionSpecification(
        **candidate_values,
        specification_digest=(
            ScientificCandidateConstructionSpecification.calculate_digest(
                **candidate_values
            )
        ),
    )
    candidate_spec = QtCandidateConstructionSpecification(
        candidate_scientific_spec, candidate_policy
    )
    candidates = QtCandidateConstructor().construct(
        candidate_spec,
        repository_path,
        acquisition,
        commits,
        diffs,
        issues,
        links,
        evidence,
    )
    candidate_path = _artifact_path(
        output_root, candidates.artifact_binding.artifact.repository_relative_path
    )
    _write(candidate_path, candidates.to_dict())

    target_policy = QtTargetAssignmentPolicy.create()
    target_values = {
        "schema_version": "1.0.0",
        "specification_version": "qt-target-specification-1.0.0",
        "repository_snapshot_digest": acquisition.repository_snapshot.snapshot_digest,
        "commit_artifact_digest": commits.artifact.content_digest,
        "candidate_artifact_digest": (
            candidates.artifact_binding.artifact.content_digest
        ),
        "candidate_binding_digest": candidates.artifact_binding.binding_digest,
        "candidate_specification_digest": candidates.specification.specification_digest,
        "candidate_policy_digest": candidates.policy.policy_digest,
        "policy_digest": target_policy.scientific_policy.policy_digest,
    }
    target_scientific_spec = ScientificTargetAssignmentSpecification(
        **target_values,
        specification_digest=ScientificTargetAssignmentSpecification.calculate_digest(
            **target_values
        ),
    )
    target_spec = QtTargetAssignmentSpecification(target_scientific_spec, target_policy)
    targets = QtTargetAssigner().construct(target_spec, commits, candidates)
    target_path = _artifact_path(
        output_root, targets.artifact_binding.artifact.repository_relative_path
    )
    _write(target_path, targets.to_dict())

    code = construct_qt_code_features(statistics)
    inventory = build_qt_feature_inventory(commits.artifact, code.artifact)
    features = construct_qt_multimodal_features(commits, code, inventory)
    feature_paths = []
    for artifact in (code.artifact, *features.modality_artifacts):
        path = _artifact_path(output_root, artifact.repository_relative_path)
        feature_paths.append(str(path))
    _write(
        _artifact_path(output_root, code.artifact.repository_relative_path),
        code.to_dict(),
    )
    for artifact, modality in zip(
        features.modality_artifacts, ("code", "process", "text"), strict=True
    ):
        records = [
            {
                "commit_identifier": record.commit_identifier,
                "values": _thaw(getattr(record, modality)),
                "record_digest": record.record_digest,
            }
            for record in features.records
        ]
        _write(_artifact_path(output_root, artifact.repository_relative_path), records)

    assembly_policy = QtDatasetAssemblyPolicy.create()
    assembly_spec = build_qt_dataset_assembly_specification(
        commits, features, targets, assembly_policy
    )
    dataset = assemble_qt_multimodal_dataset(
        commits, features, targets, assembly_spec, assembly_policy
    )
    dataset_path = _artifact_path(
        output_root, dataset.dataset_artifact.repository_relative_path
    )
    _write(dataset_path, dataset.to_dict())

    split_policy = QtTemporalSplitPolicy.create()
    split_spec = build_qt_temporal_split_specification(dataset, split_policy)
    split = split_qt_temporal_dataset(dataset, split_spec, split_policy)
    split_path = (
        output_root
        / "artifacts"
        / "qtbase"
        / "datasets"
        / acquisition.resolved_revision
        / "qt-temporal-split.json"
    )
    _write(split_path, split.to_dict())
    model_inputs = adapt_qt_model_inputs(split)
    model_input_path = split_path.with_name("qt-model-inputs.json")
    _write(model_input_path, model_inputs.to_dict())

    assignments = tuple(targets.assignments)
    positives = sum(item.target_label == 1 for item in assignments)
    ordered = sorted(
        commits.records, key=lambda item: (item.committed_at, item.commit_id)
    )
    partitions = {
        "train": split.train,
        "validation": split.validation,
        "test": split.test,
    }
    partition_stats = {
        name: {
            "count": len(values),
            "positive_count": sum(item.target == 1 for item in values),
            "positive_prevalence": (
                sum(item.target == 1 for item in values) / len(values)
            ),
        }
        for name, values in partitions.items()
    }
    exclusion_counts = Counter(item.reason.value for item in candidates.exclusions)
    report = {
        "canonical_repository_url": acquisition.canonical_repository_url,
        "repository_revision": acquisition.resolved_revision,
        "repository_snapshot_digest": acquisition.repository_snapshot.snapshot_digest,
        "reachable_historical_commit_count": commits.reachable_historical_commit_count,
        "eligible_commit_count": len(commits.records),
        "pre_window_historical_commit_count": (
            commits.pre_window_historical_commit_count
        ),
        "reachable_history_digest": commits.reachable_history_digest,
        "first_eligible_committed_at": ordered[0].committed_at,
        "last_eligible_committed_at": ordered[-1].committed_at,
        "jira": jira_manifest,
        "issue_artifact_digest": issues.extraction_artifact.content_digest,
        "issue_count": len(issues.issues),
        "link_count": len(links.links),
        "fixing_commit_count": len(
            {
                item.commit_revision
                for item in links.links
                if item.reference_type == "fixes"
            }
        ),
        "attribution_count": len(candidates.attributions),
        "candidate_count": len(candidates.candidates),
        "pre_window_candidate_exclusion_count": (
            candidates.validation.outside_observation_window_attribution_count
        ),
        "candidate_exclusion_counts": dict(sorted(exclusion_counts.items())),
        "observation_count": len(assignments),
        "positive_count": positives,
        "negative_count": len(assignments) - positives,
        "positive_prevalence": positives / len(assignments),
        "partition_statistics": partition_stats,
        "train_end": split.train_end,
        "validation_start": split.validation_start,
        "validation_end": split.validation_end,
        "test_start": split.test_start,
        "dataset_artifact_digest": dataset.dataset_artifact.content_digest,
        "dataset_identity_digest": dataset.assembly_identity_digest,
        "split_identity_digest": split.split_identity_digest,
        "model_input_identity_digest": model_inputs.adaptation_identity_digest,
        "artifact_paths": {
            "repository": str(acquisition_path),
            "commits": str(commit_path),
            "issues": str(issue_artifact_path),
            "links": str(link_path),
            "diffs": str(diff_path),
            "diff_statistics": str(statistics_path),
            "target_evidence": str(evidence_path),
            "candidates": str(candidate_path),
            "targets": str(target_path),
            "features": feature_paths,
            "dataset": str(dataset_path),
            "split": str(split_path),
            "model_inputs": str(model_input_path),
        },
    }
    report_path = (
        output_root
        / "outputs"
        / "reports"
        / f"qt-materialization-{acquisition.resolved_revision}.json"
    )
    _write(report_path, report)
    report["materialization_report_path"] = str(report_path)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-path", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, default=_ROOT)
    arguments = parser.parse_args()
    report = materialize(
        arguments.repository_path.resolve(), arguments.output_root.resolve()
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
