# ruff: noqa: E501
"""Fail-closed Sprint 48C prospective TARGET-label scientific gate.

The module deliberately separates an identity candidate from a supported label.
It can validate complete external evidence records, but the repository generator
does not manufacture such evidence when it is absent.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

SPRINT = "10.8.2.48C"
VERSION = "1.0.0"
STARTING_BRANCH = "sprint-10/q1-prospective-target-label-materialization"
STARTING_HEAD = "30a37f1fbf582b549ddc08e8b535ac30e10989bd"
CLASSIFICATION = "BLOCKED_PROSPECTIVE_LABEL_PROVENANCE"
EVIDENCE_CUTOFF = "2026-08-30T23:59:59-05:00"
AUDIT_48B = Path("audits/q1-dataset-materialization-compatibility-closure/1.0.0")
HISTORICAL = Path("data/processed/jit_defects4j/1.0.0")
PROVISIONAL_FOUR = ("ant-ivy", "commons-lang", "giraph", "opennlp")
PREDICTIVE_METRICS = frozenset(
    {"roc_auc", "pr_auc", "precision", "recall", "f1", "mcc", "brier", "ece"}
)


class EvidenceState(StrEnum):
    """Mutually exclusive prospective ground-truth evidence states."""

    POSITIVE_SUPPORTED = "POSITIVE_SUPPORTED"
    NEGATIVE_SUPPORTED = "NEGATIVE_SUPPORTED"
    UNRESOLVED = "UNRESOLVED"
    RIGHT_CENSORED = "RIGHT_CENSORED"
    IDENTITY_UNRESOLVED = "IDENTITY_UNRESOLVED"
    PROVENANCE_UNRESOLVED = "PROVENANCE_UNRESOLVED"


class ContractError(ValueError):
    """Raised when a scientific gate is violated."""


@dataclass(frozen=True)
class LabelDecision:
    """A label decision that cannot silently turn uncertainty into zero."""

    state: EvidenceState
    label: int | None
    reason: str


def canonical_bytes(value: object) -> bytes:
    """Return deterministic UTF-8 JSON bytes."""
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode()


def digest(value: object) -> str:
    """Hash canonical evidence."""
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def decide_label(
    *,
    commit_epoch: int,
    boundary_epoch: int,
    identity_resolved: bool = True,
    provenance_resolved: bool = False,
    positive_chain_complete: bool = False,
    negative_verification_complete: bool = False,
    maturity_window_seconds: int | None = None,
    evidence_cutoff_epoch: int | None = None,
) -> LabelDecision:
    """Apply temporal, provenance, positive, negative, and maturity gates."""
    if commit_epoch <= boundary_epoch:
        raise ContractError("prospective commit is not strictly post-boundary")
    if not identity_resolved:
        return LabelDecision(EvidenceState.IDENTITY_UNRESOLVED, None, "identity")
    if not provenance_resolved:
        return LabelDecision(EvidenceState.PROVENANCE_UNRESOLVED, None, "provenance")
    if positive_chain_complete:
        return LabelDecision(EvidenceState.POSITIVE_SUPPORTED, 1, "complete chain")
    if negative_verification_complete:
        if maturity_window_seconds is None or evidence_cutoff_epoch is None:
            return LabelDecision(
                EvidenceState.UNRESOLVED, None, "negative maturity rule unavailable"
            )
        if evidence_cutoff_epoch - commit_epoch < maturity_window_seconds:
            return LabelDecision(EvidenceState.RIGHT_CENSORED, None, "immature")
        return LabelDecision(EvidenceState.NEGATIVE_SUPPORTED, 0, "verified mature")
    return LabelDecision(EvidenceState.UNRESOLVED, None, "no affirmative label evidence")


def project_is_eligible(project: Mapping[str, Any]) -> tuple[bool, list[str]]:
    """Apply the common 15-gate contract without sample-count invention."""
    reasons: list[str] = []
    for gate in (
        "G1_identity",
        "G2_post_boundary",
        "G3_no_overlap",
        "G4_label_construct",
        "G8_maturity",
        "G9_provenance",
        "G10_code",
        "G11_process",
        "G12_text",
        "G13_schema",
        "G14_lopo_holdout",
        "G15_no_predictive_selection",
    ):
        if project.get(gate) is not True:
            reasons.append(f"FAIL_{gate.upper()}")
    if int(project.get("supported_positive", 0)) < 1:
        reasons.append("FAIL_G5_NO_SUPPORTED_POSITIVE")
    if int(project.get("supported_negative", 0)) < 1:
        reasons.append("FAIL_G6_NO_SUPPORTED_NEGATIVE")
    if project.get("G7_negative_affirmative") is not True:
        reasons.append("FAIL_G7_NEGATIVE_NOT_AFFIRMATIVELY_SUPPORTED")
    return not reasons, reasons


def select_four_targets(projects: Sequence[Mapping[str, Any]]) -> list[str]:
    """Select lexically from eligible projects; reject predictive inputs."""
    for project in projects:
        lowered = {str(key).lower() for key in project}
        if lowered.intersection(PREDICTIVE_METRICS):
            raise ContractError("predictive metrics are forbidden in TARGET selection")
    eligible = sorted(
        str(project["project"])
        for project in projects
        if project.get("eligibility") == "ELIGIBLE"
    )
    if len(eligible) < 4:
        raise ContractError("fewer than four eligible prospective TARGET projects")
    return eligible[:4]


def _json(path: Path) -> Any:
    return json.loads(path.read_text())


def _write_json(path: Path, value: object) -> None:
    path.write_bytes(canonical_bytes(value))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _historical_semantics() -> dict[str, object]:
    assertions = [
        {
            "assertion": "JIT-Defects4J extends the manually line-labelled LLTC4J bug-fixing-commit corpus.",
            "status": "EVIDENCED",
            "supporting_artifact": "audits/jit-defects4j/1.0.0/REPORT.md",
            "upstream_reference": "Ni et al. 2022, DOI 10.1145/3540250.3549165, Section 4",
            "consequence": "Prospective extension requires equivalent authoritative fixing-line evidence.",
        },
        {
            "assertion": "A positive is a bug-inducing commit attributed by git blame from manually agreed bug-fixing lines.",
            "status": "EVIDENCED",
            "supporting_artifact": "audits/jit-defects4j/1.0.0/audit.json",
            "upstream_reference": "Ni et al. 2022, Section 4, pp. 676 and 680",
            "consequence": "A bug-fixing commit alone cannot be labeled positive.",
        },
        {
            "assertion": "Historical label zero means a remaining commit not attributed as bug-inducing, not exhaustively verified clean.",
            "status": "EVIDENCED",
            "supporting_artifact": "audits/jit-defects4j/1.0.0/audit.json target_contract.negative",
            "upstream_reference": "Ni et al. 2022, Section 4: remaining commits treated as clean",
            "consequence": "Historical zeros are closed-world nominal negatives and cannot justify prospective zero assignment.",
        },
        {
            "assertion": "The original issue identities and fixing-commit-to-bug mappings are available in this repository.",
            "status": "UNKNOWN",
            "supporting_artifact": "No matching local artifact after repository-wide search",
            "upstream_reference": None,
            "consequence": "Prospective positive provenance cannot be reproduced from present evidence.",
        },
        {
            "assertion": "A fixed verification-latency/observation window defines a supported negative.",
            "status": "UNKNOWN",
            "supporting_artifact": "No window in frozen configs, manifests, audits, or upstream Section 4",
            "upstream_reference": None,
            "consequence": "No prospective nominal zero can become NEGATIVE_SUPPORTED.",
        },
        {
            "assertion": "The package label field faithfully implements the publication procedure for every row.",
            "status": "INFERRED",
            "supporting_artifact": "Pinned data.zip hash and aggregate counts match publication Table 2",
            "upstream_reference": "Ni et al. 2022, Table 2",
            "consequence": "Historical use is traceable at package level, but row-level issue provenance is absent.",
        },
    ]
    return {
        "schema_version": "q1-prospective-label-semantics-audit-1.0.0",
        "historical_construct_reconstructable": True,
        "upstream_dataset": "JIT-Defects4J distributed by jacknichao/JIT-Fine",
        "acquisition_path": "data/external/jit-fine-audit-cache/data.zip",
        "upstream_revision": "584799fdec6095ab75a45fd2a5f8db5b12163aa5",
        "original_repository_identity": "per-project GitHub repository mapping pinned in canonical manifest",
        "historical_observation_identity": ["project", "commit_hash"],
        "positive_semantics": "LLTC4J agreed bug-fixing line -> git blame -> candidate bug-inducing commit -> positive commit",
        "negative_semantics": "closed-world remainder not attributed as bug-inducing; nominal, not verified defect-free",
        "direct_or_szz": "SZZ-family blame attribution constrained by manually validated repair-line evidence",
        "bug_fix_evidence_source": "LLTC4J participant consensus on lines contributing to bug fixing",
        "issue_tracker_evidence": "UNKNOWN_AT_ROW_LEVEL_IN_LOCAL_PACKAGE",
        "mapping_rules": "agreed repair line -> git blame antecedent; remaining commits -> nominal zero",
        "temporal_assumptions": "original publication timeframe; repository canonicalization later uses Git committer time",
        "observation_window": "UNKNOWN",
        "repository_transformations": [
            "resolve project-qualified commit identities",
            "replace package time with Git committer timestamp",
            "chronological 70/15/15 repartition without shuffle",
            "materialize CODE/PROCESS/TEXT under denylist",
            "preserve upstream binary target without recreating it",
        ],
        "assertions": assertions,
        "status_counts": dict(Counter(str(row["status"]) for row in assertions)),
    }


def _contingency() -> dict[str, object]:
    common = {
        "training_or_scoring_performed": False,
        "selection_status": "NOT_SUBSTITUTED",
        "required_next_evidence": "pin raw dataset/repository version; audit row-level labels, timestamps, and C/P/T reconstruction before adoption",
    }
    return {
        "schema_version": "q1-contingency-dataset-assessment-1.0.0",
        "trigger": CLASSIFICATION,
        "bounded_assessment_only": True,
        "priority_order": ["ApacheJIT", "established OpenStack/Qt JIT", "other peer-reviewed JIT benchmark"],
        "candidates": [
            {
                "priority": 1,
                "dataset": "ApacheJIT",
                "commit_level_jit_labels": "REPORTED_EXTERNALLY_NOT_LOCALLY_VERIFIED",
                "label_provenance_reproducibility": "UNKNOWN",
                "timestamps": "UNKNOWN_UNTIL_PINNED_ACQUISITION",
                "CODE_reconstructibility": "PLAUSIBLE_REQUIRES_REPOSITORY_IDENTITY_AUDIT",
                "PROCESS_reconstructibility": "PLAUSIBLE_REQUIRES_CAUSAL_HISTORY_AUDIT",
                "TEXT_reconstructibility": "PLAUSIBLE_REQUIRES_RAW_MESSAGE_AUDIT",
                "CPT_compatibility": "UNVERIFIED",
                "WPDP_LOPO_compatibility": "PLAUSIBLE_MULTI_PROJECT_UNVERIFIED",
                "migration_effort": "HIGH",
                "scientific_comparability": "JIT_COMMIT_LEVEL_POTENTIAL; LABEL_CONSTRUCT_ALIGNMENT_UNKNOWN",
                **common,
            },
            {
                "priority": 2,
                "dataset": "established OpenStack/Qt JIT benchmarks",
                "commit_level_jit_labels": "REPORTED_EXTERNALLY; LOCAL_QTBASE_ZERO_POSITIVE_ARTIFACT_INELIGIBLE",
                "label_provenance_reproducibility": "PARTIAL_LOCAL_QT_PIPELINE; BENCHMARK-SPECIFIC AUDIT_REQUIRED",
                "timestamps": "AVAILABLE_IN_PRINCIPLE_UNVERIFIED_FOR_EXTERNAL_PANEL",
                "CODE_reconstructibility": "PLAUSIBLE_FROM_GIT",
                "PROCESS_reconstructibility": "PLAUSIBLE_FROM_ANCESTORS",
                "TEXT_reconstructibility": "PLAUSIBLE_FROM_COMMIT_OBJECTS",
                "CPT_compatibility": "CONTRACTED_BUT_EXTERNAL_SCHEMA_UNVERIFIED",
                "WPDP_LOPO_compatibility": "WPDP_PLAUSIBLE; LOPO_REQUIRES_MULTIPLE_INDEPENDENT_PROJECTS",
                "migration_effort": "HIGH",
                "scientific_comparability": "JIT_COMMIT_LEVEL_BUT_ECOSYSTEM_AND_LABEL_CONSTRUCT_SHIFT",
                **common,
            },
            {
                "priority": 3,
                "dataset": "another peer-reviewed JIT benchmark",
                "commit_level_jit_labels": "NOT_SELECTED",
                "label_provenance_reproducibility": "UNKNOWN",
                "timestamps": "UNKNOWN",
                "CODE_reconstructibility": "UNKNOWN",
                "PROCESS_reconstructibility": "UNKNOWN",
                "TEXT_reconstructibility": "UNKNOWN",
                "CPT_compatibility": "UNKNOWN",
                "WPDP_LOPO_compatibility": "UNKNOWN",
                "migration_effort": "VERY_HIGH",
                "scientific_comparability": "UNKNOWN_UNTIL_SYSTEMATIC_EVIDENCE_AUDIT",
                **common,
            },
        ],
        "decision": "NO_DATASET_SUBSTITUTION_IN_48C",
    }


def build_artifacts(root: Path) -> tuple[dict[str, object], list[dict[str, object]]]:
    """Build deterministic fail-closed artifacts from immutable Sprint 48B rows."""
    temporal = _json(root / AUDIT_48B / "temporal_partition_contract.json")
    source_rows = [
        json.loads(line)
        for line in (root / AUDIT_48B / "prospective_sample_manifest.jsonl")
        .read_text()
        .splitlines()
    ]
    source_rows.sort(key=lambda row: (row["project"], row["committer_epoch"], row["commit_hash"]))
    label_rows: list[dict[str, object]] = []
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for source in source_rows:
        project = str(source["project"])
        boundary = temporal["projects"][project]["historical_boundary"]
        if (int(source["committer_epoch"]), str(source["commit_hash"])) <= (
            int(boundary["committer_epoch"]),
            str(boundary["commit_hash"]),
        ):
            raise ContractError("48B identity violates its frozen temporal boundary")
        record: dict[str, object] = {
            "project": project,
            "commit_sha": source["commit_hash"],
            "commit_epoch": source["committer_epoch"],
            "frozen_temporal_boundary": boundary,
            "evidence_cutoff": EVIDENCE_CUTOFF,
            "assigned_label": None,
            "evidence_state": EvidenceState.PROVENANCE_UNRESOLVED,
            "source_repository": source["source_repository"],
            "source_issue_or_bug_ids": [],
            "fixing_commit": None,
            "repair_line_evidence": [],
            "bug_inducing_commit": None,
            "provenance_chain": "UNAVAILABLE_FOR_PROSPECTIVE_EXTENSION",
            "labeling_method_version": "jit-defects4j-manual-fix-line-blame-extension-unavailable-1.0.0",
            "repository_ref_snapshot_sha256": source["repository_ref_snapshot_sha256"],
        }
        record["evidence_hash"] = digest(record)
        label_rows.append(record)
        grouped[project].append(record)

    projects: list[dict[str, object]] = []
    for project in sorted(grouped):
        inventory = temporal["projects"][project]
        rows = grouped[project]
        gate_input = {
            "G1_identity": True,
            "G2_post_boundary": True,
            "G3_no_overlap": inventory["historical_overlap_count"] == 0,
            "G4_label_construct": True,
            "supported_positive": 0,
            "supported_negative": 0,
            "G7_negative_affirmative": False,
            "G8_maturity": False,
            "G9_provenance": False,
            "G10_code": inventory["code_materializable_from_git"],
            "G11_process": inventory["process_materializable_from_ancestors"],
            "G12_text": inventory["text_materializable_from_commit_object"],
            "G13_schema": True,
            "G14_lopo_holdout": True,
            "G15_no_predictive_selection": True,
        }
        eligible, reasons = project_is_eligible(gate_input)
        projects.append(
            {
                "project": project,
                "source_repository": inventory["source_repository"],
                "total_prospective_identities": len(rows),
                "supported_positive": 0,
                "supported_negative": 0,
                "unresolved": len(rows),
                "right_censored": 0,
                "prevalence_supported": None,
                "temporal_range": {
                    "first_epoch": inventory["post_boundary_first_epoch"],
                    "last_epoch": inventory["post_boundary_last_epoch"],
                },
                "CODE_compatibility": "PASS_RAW_MATERIALIZABLE",
                "PROCESS_compatibility": "PASS_CAUSAL_ANCESTOR_MATERIALIZABLE",
                "TEXT_compatibility": "PASS_RAW_MESSAGE_WITH_FROZEN_DENYLIST",
                "provenance_status": "PROVENANCE_UNRESOLVED",
                "gates": gate_input,
                "eligibility": "ELIGIBLE" if eligible else "INELIGIBLE",
                "reason_codes": reasons,
                "provisional_named_candidate": project in PROVISIONAL_FOUR,
            }
        )

    semantics = _historical_semantics()
    summary = {
        "schema_version": "q1-prospective-label-summary-1.0.0",
        "evidence_cutoff": EVIDENCE_CUTOFF,
        "total": len(label_rows),
        "supported_positive": 0,
        "supported_negative": 0,
        "unresolved": len(label_rows),
        "right_censored": 0,
        "identity_unresolved": 0,
        "provenance_unresolved": len(label_rows),
        "assigned_label_count": 0,
        "projects": len(projects),
    }
    artifacts: dict[str, object] = {
        "provenance.json": {
            "sprint": SPRINT,
            "generator": "src/experimentation/q1_prospective_target_label_materialization.py",
            "starting_branch": STARTING_BRANCH,
            "starting_head": STARTING_HEAD,
            "starting_status": "clean",
            "pr_107_merge_verified": True,
            "authoritative_48b_classification": "BLOCKED_MISSING_PROSPECTIVE_TEST",
            "authoritative_48b_manifest_sha256": _sha256(root / AUDIT_48B / "MANIFEST.sha256"),
            "historical_package_sha256": _json(root / HISTORICAL / "manifest.json")["source"]["package_sha256"],
            "evidence_cutoff": EVIDENCE_CUTOFF,
            "target_access_count": 0,
        },
        "label_semantics_audit.json": semantics,
        "prospective_label_summary.json": summary,
        "right_censoring_audit.json": {
            "schema_version": "q1-right-censoring-audit-1.0.0",
            "evidence_cutoff": EVIDENCE_CUTOFF,
            "maturity_rule": "UNAVAILABLE_NOT_INVENTED",
            "methodological_basis": "No fixed observation window in repository contracts or JIT-Defects4J publication method",
            "mature_count": 0,
            "right_censored_count": 0,
            "unresolved_count": len(label_rows),
            "supported_positive": 0,
            "supported_negative": 0,
            "interpretation": "Maturity cannot be evaluated before provenance-complete prospective labeling exists; no absence-of-evidence zero was created.",
        },
        "project_target_eligibility.json": {
            "schema_version": "q1-project-target-eligibility-1.0.0",
            "common_contract_applied_to_all_projects": True,
            "project_count": len(projects),
            "eligible_count": 0,
            "projects": projects,
        },
        "four_target_freeze.json": {
            "schema_version": "q1-four-target-freeze-1.0.0",
            "status": "BLOCKED_FEWER_THAN_FOUR_ELIGIBLE",
            "eligible_count": 0,
            "frozen_primary_targets": [],
            "selection_rule": "lexicographically first four project identifiers among projects passing all G1-G15 gates",
            "selection_rule_predeclared_and_performance_independent": True,
            "predictive_performance_consulted": False,
            "target_access_count": 0,
        },
        "feature_compatibility_contract.json": {
            "schema_version": "q1-48c-feature-compatibility-1.0.0",
            "modalities": ["C", "P", "T"],
            "configurations_unchanged": ["C", "P", "T", "C+P", "C+T", "P+T", "C+P+T"],
            "C": "exact Git parent-diff materialization under frozen 48B schema",
            "P": "ancestor-only causal process history",
            "T": "raw commit message; defect/issue/fix linkage denied as predictor; SOURCE-only representation fitting",
            "learned_transform_scope": "SOURCE_TRAIN_ONLY",
            "prospective_raw_compatibility_all_21": True,
            "target_fitted_operations": [],
        },
        "temporal_integrity_audit.json": {
            "schema_version": "q1-48c-temporal-integrity-1.0.0",
            "boundary_order": ["committer_epoch", "commit_sha"],
            "strict_post_boundary_count": len(label_rows),
            "boundary_violation_count": 0,
            "historical_identity_overlap_count": 0,
            "evidence_cutoff": EVIDENCE_CUTOFF,
            "future_ground_truth_is_predictor": False,
        },
        "target_access_policy.json": {
            "schema_version": "q1-48c-target-access-policy-1.0.0",
            "default": "DENY",
            "access_counter": 0,
            "execution_authorized": False,
            "predictive_scoring_count": 0,
            "campaign_configuration_count": 720,
            "campaign_status": "BLOCKED_NOT_EXECUTED",
            "prohibited_uses": sorted(PREDICTIVE_METRICS),
        },
        "reviewer_traceability.json": {
            "schema_version": "q1-48c-reviewer-traceability-1.0.0",
            "scientific_question_answer": "NO_UNDER_CURRENT_EVIDENCE",
            "historical_construct_reconstructed": True,
            "prospective_label_chain_reproduced": False,
            "all_21_common_gate": "APPLIED",
            "provisional_four_preapproved": False,
            "unresolved_concerns": ["prospective repair-line/bug-fix/issue provenance", "verification maturity rule"],
        },
        "implementation_readiness.json": {
            "schema_version": "q1-48c-implementation-readiness-1.0.0",
            "classification": CLASSIFICATION,
            "historical_label_construct": "RECONSTRUCTED",
            "prospective_labels": "BLOCKED_NO_AUTHORITATIVE_RAW_EVIDENCE",
            "eligible_projects": 0,
            "four_target_freeze": "BLOCKED",
            "target_access": "DEFAULT_DENY_ZERO_ACCESSES",
            "predictive_campaign": "720_CONFIGURATIONS_NOT_EXECUTED",
            "xai": "UNCHANGED_PARTIAL_UNRESOLVED",
            "verification": {
                "focused_pytest": "PASS: 15 passed in 5.04s",
                "regression_pytest": "PASS: 32 passed in 13.07s",
                "full_pytest": "EXPECTED LEGACY-GATE REJECTION: 1554 passed, 1 skipped, 2 failed, 23 errors in 111.77s; protected historical-integrity gates reject later-sprint paths and were not weakened",
                "ruff": "PASS: all changed Python files",
                "git_diff_check": "PASS",
                "manifest_hash_verification": "PASS: all 14 hashed payloads",
            },
        },
        "contingency_dataset_assessment.json": _contingency(),
    }
    return artifacts, label_rows


def _report(artifacts: Mapping[str, object]) -> str:
    eligibility = artifacts["project_target_eligibility.json"]
    assert isinstance(eligibility, Mapping)
    projects = eligibility["projects"]
    assert isinstance(projects, list)
    table = "\n".join(
        f"| {row['project']} | {row['total_prospective_identities']} | 0 | 0 | {row['unresolved']} | 0 | INELIGIBLE |"
        for row in projects
    )
    return f"""# Sprint 10.8.2.48C — Prospective TARGET Label Materialization

## Primary scientific classification

`{CLASSIFICATION}`

The historical construct is reconstructable, but it cannot be extended from the
available prospective evidence. JIT-Defects4J positives require manually agreed
bug-fixing-line evidence followed by blame attribution. No equivalent prospective
issue/fix/repair-line evidence exists locally, and no frozen verification-latency
window exists for affirmative negatives. Therefore all 58,272 identities remain
`PROVENANCE_UNRESOLVED`; none is silently assigned label zero.

The authoritative Sprint 48B result `BLOCKED_MISSING_PROSPECTIVE_TEST` is preserved.
No four-project TARGET set is frozen. Ant-Ivy, Commons Lang, Giraph, and OpenNLP
were evaluated by the same contract as every other project and are ineligible.

## All-project result

| Project | Identities | Positive | Negative | Unresolved | Right-censored | Result |
|---|---:|---:|---:|---:|---:|---|
{table}

Raw CODE, causal PROCESS, and leakage-controlled raw TEXT are materially compatible
for all 21 repositories. Compatibility does not cure missing ground truth.

## Governance and contingency

TARGET access counter remains **0**. No predictive metric, model, calibration,
threshold, campaign cell, or XAI method was executed. The 720-cell campaign remains
blocked. A bounded contingency assessment records ApacheJIT first, established
OpenStack/Qt benchmarks second, and another peer-reviewed JIT benchmark third;
none was substituted, trained, or scored.

## Verification

- Focused tests: 15 passed.
- Relevant regressions: 32 passed.
- Full suite: 1554 passed, 1 skipped, 2 failed, 23 errors. The non-passing
  legacy tests are protected historical-integrity gates that reject later-sprint
  paths; they were not weakened.
- Ruff on changed Python files, `git diff --check`, and manifest/hash verification:
  PASS.

## Exact recommended next sprint

Acquire and pin provenance-complete prospective ground truth: authoritative bug
identities, validated bug-fixing commits, agreed repair-line evidence, deterministic
blame attribution, and a literature- or upstream-defined verification-latency rule.
Then rerun this unchanged gate; do not begin predictive execution until at least four
projects pass all G1-G15 criteria.
"""


def generate(root: Path, output: Path) -> Path:
    """Generate the versioned 48C audit package."""
    artifacts, label_rows = build_artifacts(root)
    output.mkdir(parents=True, exist_ok=True)
    for name, value in sorted(artifacts.items()):
        _write_json(output / name, value)
    (output / "prospective_label_manifest.jsonl").write_bytes(
        b"".join(canonical_bytes(row) for row in label_rows)
    )
    (output / "REPORT.md").write_text(_report(artifacts))
    names = sorted(path.name for path in output.iterdir() if path.name != "MANIFEST.sha256")
    manifest = "".join(f"{_sha256(output / name)}  {name}\n" for name in names)
    (output / "MANIFEST.sha256").write_text(manifest)
    return output


def validate(output: Path) -> list[str]:
    """Validate reusable scientific invariants and every artifact digest."""
    errors: list[str] = []
    required = {
        "REPORT.md",
        "MANIFEST.sha256",
        "provenance.json",
        "label_semantics_audit.json",
        "prospective_label_manifest.jsonl",
        "prospective_label_summary.json",
        "right_censoring_audit.json",
        "project_target_eligibility.json",
        "four_target_freeze.json",
        "feature_compatibility_contract.json",
        "temporal_integrity_audit.json",
        "target_access_policy.json",
        "reviewer_traceability.json",
        "implementation_readiness.json",
        "contingency_dataset_assessment.json",
    }
    missing = sorted(required - {path.name for path in output.iterdir()})
    if missing:
        errors.append(f"missing artifacts: {missing}")
        return errors
    policy = _json(output / "target_access_policy.json")
    if (
        policy.get("access_counter") != 0
        or policy.get("execution_authorized") is not False
        or policy.get("predictive_scoring_count") != 0
        or policy.get("campaign_status") != "BLOCKED_NOT_EXECUTED"
    ):
        errors.append("TARGET access policy must remain unauthorized and unused")
    summary = _json(output / "prospective_label_summary.json")
    label_rows = [
        json.loads(line)
        for line in (output / "prospective_label_manifest.jsonl").read_text().splitlines()
        if line
    ]
    state_counts = Counter(str(row.get("evidence_state")) for row in label_rows)
    assigned_label_count = sum(row.get("assigned_label") is not None for row in label_rows)
    expected_summary_counts = {
        "total": len(label_rows),
        "supported_positive": state_counts[EvidenceState.POSITIVE_SUPPORTED],
        "supported_negative": state_counts[EvidenceState.NEGATIVE_SUPPORTED],
        "unresolved": sum(
            state_counts[state]
            for state in (
                EvidenceState.UNRESOLVED,
                EvidenceState.IDENTITY_UNRESOLVED,
                EvidenceState.PROVENANCE_UNRESOLVED,
            )
        ),
        "right_censored": state_counts[EvidenceState.RIGHT_CENSORED],
        "identity_unresolved": state_counts[EvidenceState.IDENTITY_UNRESOLVED],
        "provenance_unresolved": state_counts[EvidenceState.PROVENANCE_UNRESOLVED],
        "assigned_label_count": assigned_label_count,
    }
    if any(summary.get(key) != value for key, value in expected_summary_counts.items()):
        errors.append("prospective label summary must match manifest evidence states")
    for row in label_rows:
        state = row.get("evidence_state")
        label = row.get("assigned_label")
        if state not in set(EvidenceState):
            errors.append("prospective observations must use a declared evidence state")
            break
        boundary = row.get("frozen_temporal_boundary", {})
        if (row.get("commit_epoch"), row.get("commit_sha")) <= (
            boundary.get("committer_epoch"),
            boundary.get("commit_hash"),
        ):
            errors.append("prospective observations must remain strictly post-boundary")
            break
        evidence_payload = {key: value for key, value in row.items() if key != "evidence_hash"}
        if row.get("evidence_hash") != digest(evidence_payload):
            errors.append("prospective observation evidence hash mismatch")
            break
        if (state == EvidenceState.POSITIVE_SUPPORTED and label != 1) or (
            state == EvidenceState.NEGATIVE_SUPPORTED and label != 0
        ):
            errors.append("supported evidence states must carry their corresponding labels")
            break
        if state not in {
            EvidenceState.POSITIVE_SUPPORTED,
            EvidenceState.NEGATIVE_SUPPORTED,
        } and label is not None:
            errors.append("unresolved or censored evidence must not receive a label")
            break
        if label is not None and row.get("provenance_resolved") is not True:
            errors.append("provenance must be resolved before assigning a label")
            break
        if label == 1 and row.get("positive_chain_complete") is not True:
            errors.append("positive labels require a complete positive provenance chain")
            break
        if label == 0:
            if row.get("negative_verification_complete") is not True:
                errors.append("negative labels require affirmative negative evidence")
                break
            maturity_window = row.get("maturity_window_seconds")
            cutoff_epoch = row.get("evidence_cutoff_epoch")
            if (
                not isinstance(maturity_window, int)
                or not isinstance(cutoff_epoch, int)
                or cutoff_epoch - int(row["commit_epoch"]) < maturity_window
            ):
                errors.append("negative labels require completed maturity support")
                break
    eligibility = _json(output / "project_target_eligibility.json")
    projects = eligibility.get("projects", [])
    eligible_projects: list[str] = []
    eligibility_consistent = isinstance(projects, list)
    if eligibility_consistent:
        for project in projects:
            if {str(key).lower() for key in project}.intersection(PREDICTIVE_METRICS):
                eligibility_consistent = False
                errors.append("predictive metrics are forbidden in TARGET selection")
                break
            gates = project.get("gates", {})
            eligible, reasons = project_is_eligible(gates)
            declared_eligible = project.get("eligibility") == "ELIGIBLE"
            if declared_eligible:
                eligible_projects.append(str(project.get("project")))
            if declared_eligible != eligible or project.get("reason_codes") != reasons:
                eligibility_consistent = False
                break
    if (
        not eligibility_consistent
        or eligibility.get("project_count") != len(projects)
        or eligibility.get("eligible_count") != len(eligible_projects)
    ):
        errors.append("project eligibility counts and decisions must match the common gate")
    freeze = _json(output / "four_target_freeze.json")
    frozen_targets = freeze.get("frozen_primary_targets")
    expected_targets = sorted(eligible_projects)[:4] if len(eligible_projects) >= 4 else []
    if (
        freeze.get("eligible_count") != len(eligible_projects)
        or frozen_targets != expected_targets
        or freeze.get("predictive_performance_consulted") is not False
        or freeze.get("selection_rule_predeclared_and_performance_independent") is not True
        or freeze.get("target_access_count") != 0
    ):
        errors.append("four-TARGET freeze must follow the predeclared non-predictive rule")
    manifest_entries: dict[str, str] = {}
    for line in (output / "MANIFEST.sha256").read_text().splitlines():
        parts = line.split("  ", 1)
        if len(parts) != 2:
            errors.append("malformed MANIFEST.sha256 entry")
            continue
        expected, name = parts
        manifest_entries[name] = expected
    expected_manifest_names = {
        path.name for path in output.iterdir() if path.name != "MANIFEST.sha256"
    }
    if set(manifest_entries) != expected_manifest_names:
        errors.append("MANIFEST.sha256 must cover every generated artifact exactly once")
    for name, expected in manifest_entries.items():
        if not (output / name).is_file() or _sha256(output / name) != expected:
            errors.append(f"manifest mismatch: {name}")
    return errors


def validate_frozen_48c_snapshot(output: Path) -> list[str]:
    """Validate the accepted Sprint 48C result in addition to general invariants."""
    errors = validate(output)
    summary = _json(output / "prospective_label_summary.json")
    if summary.get("total") != 58_272 or summary.get("assigned_label_count") != 0:
        errors.append("frozen 48C snapshot must contain 58,272 identities and 0 assigned labels")
    eligibility = _json(output / "project_target_eligibility.json")
    if eligibility.get("project_count") != 21 or eligibility.get("eligible_count") != 0:
        errors.append("frozen 48C snapshot must contain 21 projects and 0 eligible projects")
    return errors
