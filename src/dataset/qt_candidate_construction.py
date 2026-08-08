"""Deterministic construction of Qt defect-inducing candidate evidence."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, fields, is_dataclass
from pathlib import Path

from dataset.qt_candidate_classifiers import (
    QtCommentLineClassifier,
    QtFormattingOnlyClassifier,
)
from dataset.qt_candidate_construction_contracts import (
    QtCandidateConstructionSpecification,
)
from dataset.qt_target_evidence_construction import QtTargetEvidenceConstructionResult
from dataset.scientific_builder_contracts import (
    ScientificArtifactReference,
    ScientificArtifactRole,
)
from dataset.scientific_candidate_contracts import (
    ScientificCandidateArtifactBinding,
    ScientificCandidateAttributionRecord,
    ScientificCandidateConstructionResult,
    ScientificCandidateConstructionValidation,
    ScientificCandidateExclusionRecord,
    ScientificDefectInducingCandidateRecord,
)
from extraction.qt_commit_extraction import QtCommitExtractionResult
from extraction.qt_commit_issue_linking import QtCommitIssueLinkingResult
from extraction.qt_diff_extraction import QtDiffExtractionResult, QtDiffHunkRecord
from extraction.qt_issue_extraction import QtIssueExtractionResult
from extraction.qt_repository_acquisition import QtRepositoryAcquisitionResult

__all__ = ["QtCandidateConstructionError", "QtCandidateConstructor"]

_OID = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
_HEADER = re.compile(
    r"^(\^?)([0-9a-f]{40}|[0-9a-f]{64}) ([1-9][0-9]*) "
    r"([1-9][0-9]*) ([1-9][0-9]*)$"
)
_PROJECT_ROOT = Path(__file__).resolve().parents[2]


class QtCandidateConstructionError(RuntimeError):
    """Sanitized deterministic candidate-construction failure."""


def _thaw(value: object) -> object:
    if is_dataclass(value) and not isinstance(value, type):
        return {item.name: _thaw(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    if hasattr(value, "value"):
        return value.value
    return value


def _canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(
            _thaw(value),
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


class _GitReader:
    def __init__(self, repository: Path) -> None:
        self.repository = repository

    def run(
        self,
        operation: str,
        arguments: Sequence[str],
        *,
        accepted_codes: tuple[int, ...] = (0,),
    ) -> tuple[int, str]:
        if operation not in {"blame", "cat-file", "merge-base", "rev-parse"}:
            raise QtCandidateConstructionError("Git operation is not permitted")
        environment = {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_PAGER": "cat",
            "HOME": os.devnull,
            "LANG": "C",
            "LC_ALL": "C",
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        }
        try:
            completed = subprocess.run(
                [
                    "git",
                    "-c",
                    "color.ui=false",
                    "-c",
                    "core.quotePath=false",
                    operation,
                    *arguments,
                ],
                cwd=self.repository,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="surrogateescape",
                timeout=120,
                env=environment,
                shell=False,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise QtCandidateConstructionError(
                f"Git {operation} could not be read"
            ) from error
        if completed.returncode not in accepted_codes:
            raise QtCandidateConstructionError(f"Git {operation} failed")
        return completed.returncode, completed.stdout


@dataclass(frozen=True, slots=True)
class _BlameAttribution:
    commit: str
    original_line: int
    filename: str
    content: str
    boundary: bool


def _parse_blame(output: str, requested_line: int) -> _BlameAttribution:
    lines = output.splitlines()
    if not lines:
        raise QtCandidateConstructionError("Git blame produced no attribution")
    match = _HEADER.fullmatch(lines[0])
    if match is None or int(match[3]) != requested_line or int(match[5]) != 1:
        raise QtCandidateConstructionError("Git blame header is inconsistent")
    filename: str | None = None
    content: str | None = None
    boundary = bool(match[1])
    for line in lines[1:]:
        if line == "boundary":
            boundary = True
        elif line.startswith("filename "):
            if filename is not None:
                raise QtCandidateConstructionError("Git blame filename is ambiguous")
            filename = line[9:]
        elif line.startswith("\t"):
            if content is not None:
                raise QtCandidateConstructionError("Git blame content is ambiguous")
            content = line[1:]
    commit = match[2]
    if filename is None or content is None or not _OID.fullmatch(commit):
        raise QtCandidateConstructionError("Git blame attribution is incomplete")
    return _BlameAttribution(commit, int(match[3]), filename, content, boundary)


class QtCandidateConstructor:
    """Construct candidate evidence without assigning targets or labels."""

    constructor_name = "qt-candidate-constructor"

    def construct(
        self,
        specification: QtCandidateConstructionSpecification,
        repository_path: str | Path,
        acquisition_result: QtRepositoryAcquisitionResult,
        commit_extraction_result: QtCommitExtractionResult,
        diff_extraction_result: QtDiffExtractionResult,
        issue_extraction_result: QtIssueExtractionResult,
        commit_issue_linking_result: QtCommitIssueLinkingResult,
        target_evidence_result: QtTargetEvidenceConstructionResult,
    ) -> ScientificCandidateConstructionResult:
        self._validate_inputs(
            specification,
            acquisition_result,
            commit_extraction_result,
            diff_extraction_result,
            issue_extraction_result,
            commit_issue_linking_result,
            target_evidence_result,
        )
        policy = specification.policy.scientific_policy
        QtCommentLineClassifier.verify_identity(
            policy.comment_classifier_version, policy.comment_classifier_digest
        )
        QtFormattingOnlyClassifier.verify_identity(
            policy.formatting_classifier_version,
            policy.formatting_classifier_digest,
        )
        repository = Path(repository_path).resolve()
        if (
            not repository.is_dir()
            or repository == _PROJECT_ROOT
            or _PROJECT_ROOT in repository.parents
        ):
            raise ValueError(
                "repository_path must be an acquired Git repository outside the project"
            )
        reader = _GitReader(repository)
        _, resolved = reader.run(
            "rev-parse",
            ["--verify", f"{acquisition_result.resolved_revision}^{{commit}}"],
        )
        if resolved.strip() != acquisition_result.resolved_revision:
            raise QtCandidateConstructionError("repository snapshot does not match")

        issues = {
            item.issue_identifier: item for item in issue_extraction_result.issues
        }
        evidence = {
            (
                item.observation_identifier,
                item.metadata["issue_identifier"],
                item.metadata["link_reference_type"],
            ): item
            for item in target_evidence_result.evidence_records
        }
        admissible_links = tuple(
            item
            for item in commit_issue_linking_result.links
            if item.reference_type == "fixes"
            and (item.commit_revision, item.issue_identifier, item.reference_type)
            in evidence
            and issues[item.issue_identifier].issue_type
            in policy.admissible_issue_types
            and issues[item.issue_identifier].status in policy.admissible_issue_statuses
            and issues[item.issue_identifier].resolution
            in policy.admissible_issue_resolutions
        )
        diffs = {
            item.commit_identifier: item for item in diff_extraction_result.commit_diffs
        }
        attributions: dict[str, ScientificCandidateAttributionRecord] = {}
        exclusions: dict[str, ScientificCandidateExclusionRecord] = {}
        for link in admissible_links:
            diff = diffs[link.commit_revision]
            if diff.is_root_commit:
                continue
            target = evidence[
                (link.commit_revision, link.issue_identifier, link.reference_type)
            ]
            for change in diff.file_changes:
                if not self._eligible_change(change, policy):
                    continue
                assert change.old_path is not None
                assert change.old_blob_identifier is not None
                blob_lines = self._blob_lines(
                    reader,
                    diff.baseline_identifier,
                    change.old_path,
                    change.old_blob_identifier,
                )
                comments = QtCommentLineClassifier.comment_only_line_numbers(blob_lines)
                for hunk in change.hunks:
                    added_lines = self._added_lines(reader, hunk)
                    for line_number in hunk.deleted_preimage_line_numbers:
                        line = blob_lines[line_number - 1]
                        common = dict(
                            fixing_commit=link.commit_revision,
                            baseline_commit=diff.baseline_identifier,
                            issue_identifier=link.issue_identifier,
                            target_evidence_identifier=target.evidence_identifier,
                            hunk_identifier=hunk.hunk_identifier,
                            old_path=change.old_path,
                            old_blob_identifier=change.old_blob_identifier,
                            deleted_preimage_line_number=line_number,
                            policy_version=policy.policy_version,
                            policy_digest=policy.policy_digest,
                        )
                        reason: str | None = None
                        disposition = "excluded"
                        detail = ""
                        if not line.strip() or line_number in comments:
                            reason, detail = (
                                "blank-or-comment-line",
                                "blank-or-language-aware-comment-line",
                            )
                        elif QtFormattingOnlyClassifier.is_formatting_only(
                            line, added_lines
                        ):
                            reason, detail = (
                                "formatting-only-change",
                                "unicode-whitespace-normalization-equivalent",
                            )
                        if reason is not None:
                            exclusion = self._exclusion(
                                disposition, reason, detail, common
                            )
                            exclusions[exclusion.exclusion_identifier] = exclusion
                            continue
                        try:
                            _, output = reader.run(
                                "blame",
                                [
                                    "--line-porcelain",
                                    "-M",
                                    "-w",
                                    "-L",
                                    f"{line_number},{line_number}",
                                    diff.baseline_identifier,
                                    "--",
                                    change.old_path,
                                ],
                            )
                            blamed = _parse_blame(output, line_number)
                            if blamed.content != line:
                                raise QtCandidateConstructionError(
                                    "Git blame content disagrees with baseline blob"
                                )
                            if blamed.boundary:
                                exclusion = self._exclusion(
                                    "unresolved",
                                    "boundary-commit",
                                    "line-porcelain-boundary",
                                    common,
                                )
                                exclusions[exclusion.exclusion_identifier] = exclusion
                                continue
                            code, _ = reader.run(
                                "merge-base",
                                [
                                    "--is-ancestor",
                                    blamed.commit,
                                    diff.baseline_identifier,
                                ],
                                accepted_codes=(0, 1),
                            )
                            if code != 0:
                                exclusion = self._exclusion(
                                    "unresolved",
                                    "temporal-inconsistency",
                                    "historical-commit-not-reachable-from-baseline",
                                    common,
                                )
                                exclusions[exclusion.exclusion_identifier] = exclusion
                                continue
                            values = dict(
                                repository_snapshot_digest=(
                                    acquisition_result.repository_snapshot.snapshot_digest
                                ),
                                commit_issue_link_identifier=link.artifact_digest,
                                commit_issue_link_artifact_digest=(
                                    commit_issue_linking_result.artifact_digest
                                ),
                                diff_artifact_digest=(
                                    diff_extraction_result.extraction_artifact.content_digest
                                ),
                                blamed_historical_commit=blamed.commit,
                                attribution_method=policy.attribution_method,
                                **common,
                            )
                            attribution = ScientificCandidateAttributionRecord(
                                **values,
                                attribution_identifier=(
                                    ScientificCandidateAttributionRecord.calculate_identifier(
                                        **values
                                    )
                                ),
                            )
                            attributions[attribution.attribution_identifier] = (
                                attribution
                            )
                        except QtCandidateConstructionError:
                            exclusion = self._exclusion(
                                "unresolved",
                                "attribution-failure",
                                "git-blame-unresolved",
                                common,
                            )
                            exclusions[exclusion.exclusion_identifier] = exclusion

        ordered_attributions = tuple(attributions[key] for key in sorted(attributions))
        ordered_exclusions = tuple(exclusions[key] for key in sorted(exclusions))
        candidates = self._candidates(ordered_attributions, policy)
        scientific_spec = specification.scientific_specification
        validation = ScientificCandidateConstructionValidation(
            True,
            scientific_spec.specification_digest,
            policy.policy_digest,
            len(ordered_attributions),
            len(candidates),
            len(ordered_exclusions),
            (),
            (),
        )
        upstream = dict(
            sorted(
                {
                    "commits": commit_extraction_result.artifact.content_digest,
                    "diffs": diff_extraction_result.extraction_artifact.content_digest,
                    "issues": (
                        issue_extraction_result.extraction_artifact.content_digest
                    ),
                    "links": commit_issue_linking_result.artifact_digest,
                    "target-evidence": (
                        target_evidence_result.evidence_artifact.content_digest
                    ),
                }.items()
            )
        )
        payload = {
            "specification_digest": scientific_spec.specification_digest,
            "policy_digest": policy.policy_digest,
            "repository_snapshot_digest": scientific_spec.repository_snapshot_digest,
            "upstream_artifact_digests": upstream,
            "attributions": ordered_attributions,
            "candidates": candidates,
            "exclusions": ordered_exclusions,
            "validation": validation,
        }
        artifact = ScientificArtifactReference(
            "qtbase-defect-inducing-candidates",
            ScientificArtifactRole.DEFECT_INDUCING_CANDIDATE,
            "artifacts/derived/qtbase-defect-inducing-candidates.json",
            _digest(payload),
            scientific_spec.schema_version,
            len(candidates),
            metadata={"content_policy": "canonical-scientific-content-only"},
        )
        binding_values = dict(
            artifact=artifact,
            specification_digest=scientific_spec.specification_digest,
            policy_digest=policy.policy_digest,
            repository_snapshot_digest=scientific_spec.repository_snapshot_digest,
            upstream_artifact_digests=upstream,
            ordered_candidate_identifiers=tuple(
                item.candidate_identifier for item in candidates
            ),
            ordered_exclusion_identifiers=tuple(
                item.exclusion_identifier for item in ordered_exclusions
            ),
        )
        binding = ScientificCandidateArtifactBinding(
            **binding_values,
            binding_digest=ScientificCandidateArtifactBinding.calculate_digest(
                **binding_values
            ),
        )
        return ScientificCandidateConstructionResult(
            scientific_spec,
            policy,
            ordered_attributions,
            candidates,
            ordered_exclusions,
            validation,
            binding,
        )

    @staticmethod
    def _validate_inputs(
        specification, acquisition, commits, diffs, issues, links, evidence
    ) -> None:
        expected_types = (
            (specification, QtCandidateConstructionSpecification),
            (acquisition, QtRepositoryAcquisitionResult),
            (commits, QtCommitExtractionResult),
            (diffs, QtDiffExtractionResult),
            (issues, QtIssueExtractionResult),
            (links, QtCommitIssueLinkingResult),
            (evidence, QtTargetEvidenceConstructionResult),
        )
        if any(not isinstance(value, kind) for value, kind in expected_types):
            raise TypeError("candidate construction input uses an invalid contract")
        spec = specification.scientific_specification
        actual = (
            acquisition.repository_snapshot.snapshot_digest,
            commits.artifact.content_digest,
            issues.extraction_artifact.content_digest,
            links.artifact_digest,
            evidence.evidence_artifact.content_digest,
            diffs.extraction_artifact.content_digest,
        )
        expected = (
            spec.repository_snapshot_digest,
            spec.commit_artifact_digest,
            spec.issue_artifact_digest,
            spec.commit_issue_link_artifact_digest,
            spec.target_evidence_artifact_digest,
            spec.diff_artifact_digest,
        )
        if actual != expected:
            raise ValueError(
                "candidate specification does not match upstream artifacts"
            )
        if (
            diffs.commit_extraction_result != commits
            or evidence.commit_extraction_result != commits
            or evidence.issue_extraction_result != issues
            or evidence.commit_issue_linking_result != links
        ):
            raise ValueError("candidate upstream result chain is inconsistent")

    @staticmethod
    def _eligible_change(change, policy) -> bool:
        if (
            change.change_type not in policy.eligible_change_types
            or change.is_binary
            or change.old_path is None
            or change.old_blob_identifier is None
        ):
            return False
        path = Path(change.old_path)
        return path.suffix.casefold() in policy.included_source_suffixes and not set(
            part.casefold() for part in path.parts
        ) & set(policy.excluded_path_components)

    @staticmethod
    def _blob_lines(
        reader, baseline: str, path: str, expected_blob: str
    ) -> tuple[str, ...]:
        _, blob = reader.run("rev-parse", [f"{baseline}:{path}"])
        if blob.strip() != expected_blob:
            raise QtCandidateConstructionError(
                "recorded old blob does not match baseline"
            )
        _, content = reader.run("cat-file", ["blob", expected_blob])
        return tuple(content.splitlines())

    @staticmethod
    def _added_lines(reader, hunk: QtDiffHunkRecord) -> tuple[str, ...]:
        if not hunk.added_line_numbers or hunk.new_path is None:
            return ()
        _, content = reader.run("cat-file", ["blob", hunk.new_blob_identifier])
        lines = tuple(content.splitlines())
        return tuple(lines[number - 1] for number in hunk.added_line_numbers)

    @staticmethod
    def _exclusion(
        disposition: str, reason: str, detail: str, common: dict[str, object]
    ):
        values = dict(
            disposition=disposition, reason=reason, detail_code=detail, **common
        )
        return ScientificCandidateExclusionRecord(
            **values,
            exclusion_identifier=ScientificCandidateExclusionRecord.calculate_identifier(
                **values
            ),
        )

    @staticmethod
    def _candidates(attributions, policy):
        groups: dict[
            tuple[str, str, str], list[ScientificCandidateAttributionRecord]
        ] = {}
        for item in attributions:
            keys = (
                ("line", item.attribution_identifier),
                ("hunk", item.hunk_identifier),
                ("commit", item.blamed_historical_commit),
            )
            for level, key in keys:
                groups.setdefault(
                    (level, item.blamed_historical_commit, key), []
                ).append(item)
        result = []
        for (level, blamed, _), records in sorted(groups.items()):
            values = dict(
                blamed_historical_commit=blamed,
                aggregation_level=level,
                attribution_identifiers=tuple(
                    sorted({x.attribution_identifier for x in records})
                ),
                fixing_commits=tuple(sorted({x.fixing_commit for x in records})),
                issue_identifiers=tuple(sorted({x.issue_identifier for x in records})),
                target_evidence_identifiers=tuple(
                    sorted({x.target_evidence_identifier for x in records})
                ),
                policy_version=policy.policy_version,
                policy_digest=policy.policy_digest,
            )
            result.append(
                ScientificDefectInducingCandidateRecord(
                    **values,
                    candidate_identifier=ScientificDefectInducingCandidateRecord.calculate_identifier(
                        **values
                    ),
                )
            )
        return tuple(sorted(result, key=lambda item: item.candidate_identifier))
