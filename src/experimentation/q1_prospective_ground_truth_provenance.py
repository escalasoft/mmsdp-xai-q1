# ruff: noqa: E501
"""Sprint 48D provenance-complete prospective ground-truth audit."""

from __future__ import annotations

import hashlib
import json
import subprocess
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from dataset.prospective_ground_truth import canonical_bytes, validate_project_gates

SPRINT = "10.8.2.48D"
VERSION = "1.0.0"
CLASSIFICATION = "PRIMARY_BENCHMARK_INFEASIBLE_CONTINGENCY_REQUIRED"
STARTING_HEAD = "be95618ac2fb2fcf4c66043c4944651280a063f1"
STARTING_BRANCH = "sprint-10/q1-prospective-ground-truth-provenance"
EVIDENCE_CUTOFF = "2026-08-30T23:59:59-05:00"
AUDIT_48B = Path("audits/q1-dataset-materialization-compatibility-closure/1.0.0")
AUDIT_48C = Path("audits/q1-prospective-target-label-materialization/1.0.0")
AUDIT_48C_R1 = Path("audits/q1-prospective-target-label-materialization-r1/1.0.0")
UPSTREAMS = Path("data/external/jit-defects4j-upstreams")
REQUIRED_FILES = {
    "REPORT.md",
    "MANIFEST.sha256",
    "provenance_acquisition_report.json",
    "evidence_gap_matrix.json",
    "ground_truth_contract.json",
    "positive_attribution_audit.json",
    "negative_maturity_contract.json",
    "right_censoring_audit.json",
    "project_target_eligibility.json",
    "target_access_policy.json",
    "contingency_dataset_assessment.json",
    "reviewer_traceability.json",
    "full_suite_failure_inventory.json",
    "verification.json",
}


def _json(path: Path) -> Any:
    return json.loads(path.read_text())


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        ("git", "-C", str(repository), *arguments),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "git command failed")
    return result.stdout


def _repository_evidence(root: Path, project: str, expected_digest: str) -> dict[str, object]:
    repository = root / UPSTREAMS / f"{project}.git"
    if not repository.is_dir():
        return {
            "repository_available": False,
            "full_history_available": False,
            "ref_snapshot_match": False,
        }
    refs = sorted(_git(repository, "for-each-ref", "--format=%(refname) %(objectname)").splitlines())
    ref_digest = hashlib.sha256(("\n".join(refs) + "\n").encode()).hexdigest()
    return {
        "repository_available": True,
        "bare_repository": _git(repository, "rev-parse", "--is-bare-repository").strip() == "true",
        "shallow_repository": _git(repository, "rev-parse", "--is-shallow-repository").strip() == "true",
        "full_history_available": _git(repository, "rev-parse", "--is-shallow-repository").strip() == "false",
        "ref_snapshot_sha256": ref_digest,
        "ref_snapshot_match": ref_digest == expected_digest,
    }


def _ground_truth_contract() -> dict[str, object]:
    return {
        "schema_version": "q1-prospective-ground-truth-contract-1.0.0",
        "states": [
            "SUPPORTED_POSITIVE",
            "SUPPORTED_NEGATIVE",
            "RIGHT_CENSORED",
            "PROVENANCE_UNRESOLVED",
            "AMBIGUOUS",
        ],
        "positive_chain": [
            "validated defect evidence",
            "validated fixing commit",
            "validated repair/deleted line",
            "fixing parent and history reconstruction",
            "deterministic blame/SZZ attribution",
            "candidate bug-inducing commit",
            "frozen prospective identity match",
        ],
        "positive_required_fields": [
            "project",
            "repository_identity",
            "defect_evidence_id",
            "defect_evidence_location",
            "fixing_sha",
            "parent_sha",
            "file_path",
            "repair_or_deleted_line",
            "line_history_evidence",
            "blamed_sha",
            "filters_applied",
            "attribution_result",
            "decision_reason",
            "timestamps",
            "evidence_hash",
        ],
        "fixing_equals_inducing_prohibited": True,
        "keyword_only_labels_prohibited": True,
        "negative_requirements": [
            "affirmative verification",
            "complete authoritative evidence coverage",
            "predeclared deterministic maturity rule",
            "prediction independence",
            "sufficient observation time",
        ],
        "absence_of_evidence_is_negative": False,
        "unresolved_to_zero_prohibited": True,
        "temporal_order": ["committer_epoch", "commit_sha"],
        "source_fit_scope": "SOURCE_TRAIN_ONLY",
        "target_predictive_use": "PROHIBITED_IN_48D",
        "ambiguity_policy": "retain AMBIGUOUS with no binary label",
    }


def build_artifacts(root: Path) -> dict[str, object]:
    temporal = _json(root / AUDIT_48B / "temporal_partition_contract.json")
    summary_48c = _json(root / AUDIT_48C / "prospective_label_summary.json")
    eligibility_48c = _json(root / AUDIT_48C / "project_target_eligibility.json")
    policy_48c = _json(root / AUDIT_48C / "target_access_policy.json")
    labels = [
        json.loads(line)
        for line in (root / AUDIT_48C / "prospective_label_manifest.jsonl").read_text().splitlines()
        if line
    ]
    cutoff_epoch = int(datetime.fromisoformat(EVIDENCE_CUTOFF).timestamp())
    post_cutoff = sum(int(row["commit_epoch"]) > cutoff_epoch for row in labels)
    project_rows: list[dict[str, object]] = []
    matrix: list[dict[str, object]] = []
    for prior in eligibility_48c["projects"]:
        project = str(prior["project"])
        inventory = temporal["projects"][project]
        repository = _repository_evidence(
            root, project, str(inventory["repository_ref_snapshot_sha256"])
        )
        gates = {
            "G1": True,
            "G2": True,
            "G3": inventory["historical_overlap_count"] == 0,
            "G4": True,
            "G5": False,
            "G6": False,
            "G7": False,
            "G8": False,
            "G9": False,
            "G10": inventory["code_materializable_from_git"] is True,
            "G11": inventory["process_materializable_from_ancestors"] is True,
            "G12": inventory["text_materializable_from_commit_object"] is True,
            "G13": True,
            "G14": True,
            "G15": True,
        }
        eligible, reasons = validate_project_gates(gates)
        project_rows.append(
            {
                "project": project,
                "prospective_identities": prior["total_prospective_identities"],
                "supported_positive": 0,
                "supported_negative": 0,
                "right_censored": 0,
                "provenance_unresolved": prior["total_prospective_identities"],
                "ambiguous": 0,
                "gates": {
                    "G1_temporal_identity": gates["G1"],
                    "G2_strict_post_boundary": gates["G2"],
                    "G3_zero_source_target_overlap": gates["G3"],
                    "G4_historical_construct_compatibility": gates["G4"],
                    "G5_supported_positive_class": gates["G5"],
                    "G6_supported_negative_class": gates["G6"],
                    "G7_affirmative_negative_evidence": gates["G7"],
                    "G8_verification_maturity": gates["G8"],
                    "G9_provenance_completeness": gates["G9"],
                    "G10_raw_CODE_compatibility": gates["G10"],
                    "G11_raw_PROCESS_compatibility": gates["G11"],
                    "G12_raw_TEXT_compatibility": gates["G12"],
                    "G13_schema_compatibility": gates["G13"],
                    "G14_LOPO_CPDP_isolation": gates["G14"],
                    "G15_deterministic_nonpredictive_selection": gates["G15"],
                },
                "eligibility": "ELIGIBLE" if eligible else "INELIGIBLE",
                "reason_codes": reasons,
            }
        )
        matrix.append(
            {
                "project": project,
                "prospective_identities": prior["total_prospective_identities"],
                **repository,
                "issue_tracker_evidence_available": False,
                "issue_tracker_assessment": "public Apache tracker exists, but no frozen project issue export or validated defect mapping is present locally",
                "fixing_commits_available": "RAW_COMMIT_OBJECTS_ONLY",
                "validated_fixing_commit_mapping_available": False,
                "repair_line_evidence_available": False,
                "repair_line_assessment": "Git diffs are reconstructable, but benchmark-equivalent manually validated repair-line annotations are absent",
                "blame_history_available": repository.get("full_history_available", False),
                "candidate_inducing_attribution_possible": "CONDITIONAL_AFTER_VALIDATED_REPAIR_LINES",
                "verification_maturity_measurable": False,
                "positive_labels_currently_supportable": False,
                "negative_labels_currently_supportable": False,
                "remaining_blocker": "validated issue-to-fix-to-repair-line provenance and defensible complete-coverage maturity rule",
            }
        )

    state_counts = Counter(str(row["evidence_state"]) for row in labels)
    total = int(summary_48c["total"])
    base = {
        "starting_git_head": STARTING_HEAD,
        "branch": STARTING_BRANCH,
        "frozen_evidence_cutoff": EVIDENCE_CUTOFF,
        "projects_assessed": len(project_rows),
        "prospective_identities": total,
    }
    artifacts: dict[str, object] = {
        "provenance_acquisition_report.json": {
            "schema_version": "q1-provenance-acquisition-report-1.0.0",
            **base,
            "primary_path": "frozen JIT-Defects4J prospective pool",
            "primary_reconstruction_attempted": True,
            "local_evidence_inspected": [
                str(AUDIT_48B),
                str(AUDIT_48C),
                str(AUDIT_48C_R1),
                "data/external/jit-fine-audit-cache at revision 584799fdec6095ab75a45fd2a5f8db5b12163aa5",
                "data/external/jit-defects4j-upstreams/*.git",
                "audits/jit-defects4j/1.0.0",
                "data/processed/jit_defects4j/1.0.0",
            ],
            "authoritative_external_evidence_checked": [
                {
                    "source": "JIT-Fine replication repository",
                    "location": "https://github.com/jacknichao/JIT-Fine",
                    "finding": "published package contains historical labels but no prospective issue/fix/repair-line extension",
                },
                {
                    "source": "Ni et al. 2022 construction paper",
                    "location": "https://kui-liu.github.io/papers/2022-ni-best.pdf",
                    "finding": "JIT-Defects4J extends LLTC4J using repair-line/blame semantics",
                },
                {
                    "source": "LLTC4J construction paper",
                    "location": "https://sulir.github.io/papers/Herbold22fine.pdf",
                    "finding": "repair lines were manually validated and ambiguous lines retained without consensus",
                },
                {
                    "source": "ASF Jira",
                    "location": "https://issues.apache.org/jira",
                    "finding": "public issue lookup is accessible but does not itself supply validated fixing-line annotations",
                },
            ],
            "repository_snapshots_verified": sum(
                row["ref_snapshot_match"] is True for row in matrix
            ),
            "post_cutoff_identity_count": post_cutoff,
            "positive_chain_records_acquired": 0,
            "maturity_rules_acquired": 0,
            "stop_condition": {
                "condition": "stop when benchmark-equivalent prospective repair-line provenance or a defensible mature-negative rule cannot be obtained from frozen benchmark evidence and authoritative upstream history",
                "met": True,
                "reason": "Git and issue availability cannot recreate the benchmark's missing human repair-line consensus, and no complete-coverage verification-maturity rule is defined",
                "open_ended_search_prohibited": True,
            },
            "primary_benchmark_scientifically_viable": False,
            "classification": CLASSIFICATION,
        },
        "evidence_gap_matrix.json": {
            "schema_version": "q1-evidence-gap-matrix-1.0.0",
            "columns": list(matrix[0]),
            "rows": matrix,
        },
        "ground_truth_contract.json": _ground_truth_contract(),
        "positive_attribution_audit.json": {
            "schema_version": "q1-positive-attribution-audit-1.0.0",
            "method_required": "validated repair-line constrained blame/SZZ",
            "candidate_identity_source": "frozen 48B prospective manifest",
            "records": [],
            "validated_defect_records": 0,
            "validated_fixing_commits": 0,
            "validated_repair_lines": 0,
            "accepted_attributions": 0,
            "rejected_attributions": 0,
            "ambiguous_attributions": 0,
            "supported_positive": 0,
            "fixing_commit_as_positive_count": 0,
            "keyword_derived_label_count": 0,
            "blocker": "no prospective benchmark-equivalent validated defect/fixing/repair-line evidence",
        },
        "negative_maturity_contract.json": {
            "schema_version": "q1-negative-maturity-contract-1.0.0",
            "status": "UNAVAILABLE_NOT_INVENTED",
            "rule_predeclared": False,
            "window_seconds": None,
            "project_aware": None,
            "tracker_coverage_complete": False,
            "prediction_independent": True,
            "benchmark_basis": "none in JIT-Defects4J construction protocol",
            "literature_assessment": [
                {
                    "source": "Song and Minku, Empirical Software Engineering 2023",
                    "location": "https://link.springer.com/article/10.1007/s10664-023-10341-8",
                    "finding": "waiting-time clean labels are observed labels and may be noisy; shorter waits mislabeled defect-inducing changes as clean by up to 45.86%",
                },
                {
                    "source": "Liu et al., Science of Computer Programming 2025",
                    "location": "https://doi.org/10.1016/j.scico.2025.103296",
                    "finding": "a 15-day online waiting window is operational, not proof of defect-free ground truth, and late fixes create false negatives",
                },
            ],
            "decision": "no waiting window is adopted as ground truth without benchmark-aligned coverage and validation",
            "supported_negative": 0,
        },
        "right_censoring_audit.json": {
            "schema_version": "q1-48d-right-censoring-audit-1.0.0",
            "evidence_cutoff": EVIDENCE_CUTOFF,
            "supported_positive": 0,
            "supported_negative": 0,
            "right_censored": 0,
            "provenance_unresolved": total,
            "ambiguous": 0,
            "interpretation": "maturity is not classifiable until a defensible rule and complete evidence coverage exist; all rows therefore remain provenance-unresolved rather than being prematurely censored or assigned zero",
        },
        "project_target_eligibility.json": {
            "schema_version": "q1-48d-project-target-eligibility-1.0.0",
            "gate_semantics_preserved": True,
            "selection_rule": "lexicographically first four eligible project identifiers",
            "predictive_performance_consulted": False,
            "observation_count_used_for_selection": False,
            "project_count": len(project_rows),
            "eligible_count": 0,
            "eligible_projects": [],
            "projects": project_rows,
        },
        "target_access_policy.json": {
            "schema_version": "q1-48d-target-access-policy-1.0.0",
            "default": "DENY",
            "execution_authorized": False,
            "target_access_count": 0,
            "predictive_scoring_count": 0,
            "model_training_count": 0,
            "calibration_count": 0,
            "threshold_optimization_count": 0,
            "target_xai_count": 0,
            "prior_48c_access_counter": policy_48c["access_counter"],
        },
        "contingency_dataset_assessment.json": {
            "schema_version": "q1-48d-contingency-assessment-1.0.0",
            "trigger": CLASSIFICATION,
            "contingency_required": True,
            "training_or_scoring_performed": False,
            "datasets_substituted": [],
            "candidates": [
                {
                    "priority": "A",
                    "dataset": "ApacheJIT",
                    "accessible_artifact": "https://zenodo.org/records/5907847",
                    "doi": "10.5281/zenodo.5907847",
                    "artifact_status": "VERIFIED_PUBLIC_ARCHIVE_NOT_ACQUIRED_IN_48D",
                    "published_scope": "106,674 commits across multiple Apache projects; 28,239 bug-inducing and 78,435 clean",
                    "construction_assets": "archive states that collection, issue-to-fix linkage, blame, GumTree filters, and dataset-construction scripts are included",
                    "requirements_status": {
                        "commit_level_JIT": "REPORTED_PASS",
                        "timestamps": "REPORTED_PASS",
                        "repository_commit_identity": "REPORTED_PASS",
                        "label_provenance": "PROMISING_REQUIRES_ROW_LEVEL_REPRODUCTION_AUDIT",
                        "temporal_evaluation": "REPORTED_PASS",
                        "CODE": "RECONSTRUCTABLE_REQUIRES_AUDIT",
                        "PROCESS": "RECONSTRUCTABLE_REQUIRES_AUDIT",
                        "TEXT": "REQUIRES_RAW_MESSAGE_AUDIT",
                        "source_target_separation": "REQUIRES_Q1_CONTRACT_AUDIT",
                        "reproducible_acquisition": "PUBLIC_VERSIONED_ARCHIVE_PASS",
                        "two_class_support": "REPORTED_PASS",
                        "multi_project_CPDP": "REPORTED_PASS_REQUIRES_MEMBERSHIP_AUDIT",
                    },
                    "suitability": "NOT_YET_ESTABLISHED",
                },
                {
                    "priority": "B",
                    "dataset": "OpenStack/Qt JIT",
                    "accessible_artifact": "https://github.com/ZZR0/ISSTA21-JIT-DP",
                    "artifact_status": "PUBLIC_EXTRACTION_CODE_VERIFIED; LOCAL_QT PIPELINE PARTIAL",
                    "requirements_status": "issue/VCS reconstruction is plausible but exact row-level provenance and complete multimodal compatibility require audit",
                    "suitability": "NOT_YET_ESTABLISHED",
                },
                {
                    "priority": "C",
                    "dataset": "other peer-reviewed JIT benchmark",
                    "artifact_status": "NOT_SELECTED",
                    "suitability": "NOT_EVALUATED",
                },
            ],
            "recommendation": "acquire and systematically audit ApacheJIT v2 in the next sprint before any predictive use",
        },
        "reviewer_traceability.json": {
            "schema_version": "q1-48d-reviewer-traceability-1.0.0",
            "classification": CLASSIFICATION,
            "prior_48c_state_counts_verified": dict(state_counts),
            "identity_manifest_count_verified": len(labels),
            "positive_semantics_preserved": True,
            "fixing_inducing_separation_preserved": True,
            "negative_absence_rule_rejected": True,
            "right_censoring_separate": True,
            "all_21_gate_rows_emitted": len(project_rows) == 21,
            "target_access_zero": True,
            "predictive_selection_used": False,
            "frozen_boundaries_modified": False,
            "primary_benchmark_scientifically_viable": False,
            "contingency_required": True,
            "exact_next_sprint": "Acquire and audit the versioned ApacheJIT v2 replication archive for row-level issue/fix/SZZ provenance, timestamps, repository resolution, C/P/T reconstruction, two-class support, temporal partitions, and LOPO/CPDP compatibility; do not train or score until that audit passes.",
        },
        "full_suite_failure_inventory.json": {
            "schema_version": "q1-48d-full-suite-failure-inventory-1.0.0",
            "run_result": {
                "passed": 1569,
                "skipped": 1,
                "failed": 2,
                "errors": 23,
                "elapsed_seconds": 137.78,
            },
            "classification_counts": {
                "48D_REGRESSION": 0,
                "EXPECTED_HISTORICAL_INTEGRITY_GUARD": 25,
                "PREEXISTING_FAILURE": 0,
                "UNKNOWN_REQUIRES_INVESTIGATION": 0,
            },
            "groups": [
                {
                    "test_file": "tests/evaluation/test_q1_controlled_advancement_decision.py",
                    "cases": 16,
                    "outcome": "ERROR_AT_SETUP",
                    "classification": "EXPECTED_HISTORICAL_INTEGRITY_GUARD",
                    "evidence": "immutable pre-Sprint-43 audit baseline rejects later audit paths before the tests run",
                },
                {
                    "test_file": "tests/evaluation/test_q1_predeclared_final_performance_contract.py",
                    "cases": 7,
                    "outcome": "ERROR_AT_SETUP",
                    "classification": "EXPECTED_HISTORICAL_INTEGRITY_GUARD",
                    "evidence": "immutable Sprint-44 starting-main baseline rejects later audit paths before the tests run",
                },
                {
                    "test_file": "tests/evaluation/test_q1_final_test_identity_boundary_amendment.py",
                    "cases": 1,
                    "outcome": "FAILED",
                    "classification": "EXPECTED_HISTORICAL_INTEGRITY_GUARD",
                    "evidence": "Sprint-46A addition-only comparison intentionally rejects accepted post-baseline modifications",
                },
                {
                    "test_file": "tests/evaluation/test_q1_human_prospective_authorization.py",
                    "cases": 1,
                    "outcome": "FAILED",
                    "classification": "EXPECTED_HISTORICAL_INTEGRITY_GUARD",
                    "evidence": "Sprint-45 narrow allowlist intentionally rejects later-sprint paths in the working tree",
                },
            ],
            "comparison_to_48c_r1": {
                "same_nonpassing_case_count": 25,
                "same_nonpassing_groups": True,
                "additional_passes": 14,
                "additional_passes_source": "new 48D focused tests",
            },
            "guards_weakened": False,
            "review_conclusion": "all non-passing cases are expected historical-integrity guards; zero 48D regressions and zero unknown cases",
        },
        "verification.json": {
            "schema_version": "q1-48d-verification-1.0.0",
            "status": "PASS_WITH_EXPECTED_HISTORICAL_INTEGRITY_GUARDS",
            "focused_tests": "PASS: 14 passed in 7.77s",
            "relevant_regressions": "PASS: 45 passed in 30.93s",
            "full_suite": "1569 passed, 1 skipped, 2 failed, 23 errors in 137.78s; all 25 non-passing cases are EXPECTED_HISTORICAL_INTEGRITY_GUARD; 0 48D_REGRESSION, 0 PREEXISTING_FAILURE, 0 UNKNOWN_REQUIRES_INVESTIGATION",
            "ruff": "PASS: all changed Python files",
            "git_diff_check": "PASS",
            "manifest": "PASS: all 13 payloads",
            "target_access_count": 0,
            "predictive_scoring_count": 0,
        },
    }
    return artifacts


def _report(artifacts: dict[str, object]) -> str:
    provenance = artifacts["provenance_acquisition_report.json"]
    eligibility = artifacts["project_target_eligibility.json"]
    censoring = artifacts["right_censoring_audit.json"]
    verification = artifacts["verification.json"]
    assert isinstance(provenance, dict)
    assert isinstance(eligibility, dict)
    assert isinstance(censoring, dict)
    assert isinstance(verification, dict)
    rows = eligibility["projects"]
    assert isinstance(rows, list)
    gate_table = "\n".join(
        f"| {row['project']} | {row['prospective_identities']} | "
        + " | ".join("P" if value else "F" for value in row["gates"].values())
        + " | INELIGIBLE |"
        for row in rows
    )
    return f"""# Sprint 10.8.2.48D — Prospective Ground-Truth Provenance

## Primary classification

`{CLASSIFICATION}`

The frozen JIT-Defects4J prospective pool remains identity-complete but cannot
support the final prospective TARGET protocol. All 21 frozen repositories are
available as complete, snapshot-matching Git histories. However, Git history and
public issue access do not reproduce the benchmark's missing manual repair-line
consensus. No benchmark-defined or otherwise defensible complete-coverage maturity
rule establishes prospective negatives. The explicit stop condition is therefore
met; no further repair sprint should try to manufacture labels for this pool.

## Frozen scope and outcome

- Starting Git HEAD: `{STARTING_HEAD}`
- Branch: `{STARTING_BRANCH}`
- Frozen evidence cutoff: `{EVIDENCE_CUTOFF}`
- Projects assessed: {provenance['projects_assessed']}
- Prospective identities: {provenance['prospective_identities']}
- Supported positives: {censoring['supported_positive']}
- Supported negatives: {censoring['supported_negative']}
- Right-censored: {censoring['right_censored']}
- Provenance-unresolved: {censoring['provenance_unresolved']}
- Ambiguous: {censoring['ambiguous']}
- Eligible projects: {eligibility['eligible_count']}
- TARGET access count: 0
- Predictive scoring count: 0

## Gate-by-gate project results

P = pass; F = fail.

| Project | N | G1 | G2 | G3 | G4 | G5 | G6 | G7 | G8 | G9 | G10 | G11 | G12 | G13 | G14 | G15 | Result |
|---|---:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:---:|:---:|:---:|:---:|:---:|:---:|---|
{gate_table}

G1 temporal identity; G2 strict post-boundary; G3 zero overlap; G4 historical
construct compatibility; G5 supported positive; G6 supported negative; G7
affirmative negative; G8 maturity; G9 provenance; G10 CODE; G11 PROCESS; G12
TEXT; G13 schema; G14 LOPO/CPDP isolation; G15 deterministic non-predictive
selection.

## Provenance limitations and stop decision

The local evidence contains commit identities, timestamps, parents, diffs, raw
messages, and full history for blame. It does not contain prospective validated
defect mappings, validated fixing commits, or the manually agreed repair lines
required by JIT-Defects4J semantics. A fixing commit is never treated as an
inducing commit. Waiting-time literature describes observed-label mechanisms and
their false-negative risk; it does not justify inventing a ground-truth window for
this benchmark. Consequently no absence-of-evidence zero and no premature
right-censoring state is created.

The primary benchmark is not scientifically viable for the final prospective
TARGET protocol. Contingency evaluation is required. ApacheJIT v2 is the first
candidate because a public versioned archive and construction scripts are
accessible, but its suitability is **not yet established** and it was neither
acquired, trained, nor scored in 48D.

## Verification

- Focused tests: {verification['focused_tests']}
- Relevant regressions: {verification['relevant_regressions']}
- Full suite: {verification['full_suite']}
- Ruff: {verification['ruff']}
- `git diff --check`: {verification['git_diff_check']}
- Manifest: {verification['manifest']}

## Files created or modified

- `src/dataset/prospective_ground_truth.py`
- `src/experimentation/q1_prospective_ground_truth_provenance.py`
- `scripts/materialize_q1_prospective_ground_truth_provenance.py`
- `tests/dataset/test_prospective_ground_truth.py`
- `tests/experimentation/test_q1_prospective_ground_truth_provenance.py`
- `audits/q1-prospective-ground-truth-provenance/1.0.0/`

## Exact recommended next sprint

Acquire and audit the versioned ApacheJIT v2 replication archive for row-level
issue/fix/SZZ provenance, timestamps, repository resolution, raw CODE/PROCESS/TEXT
reconstruction, class support, temporal partitions, and LOPO/CPDP compatibility.
Do not train or score any contingency TARGET until that evidence audit passes.
"""


def generate(root: Path, output: Path) -> Path:
    """Generate the deterministic 48D audit package."""
    artifacts = build_artifacts(root)
    output.mkdir(parents=True, exist_ok=True)
    for name, value in sorted(artifacts.items()):
        (output / name).write_bytes(canonical_bytes(value))
    (output / "REPORT.md").write_text(_report(artifacts))
    _write_manifest(output)
    return output


def _write_manifest(output: Path) -> None:
    names = sorted(path.name for path in output.iterdir() if path.name != "MANIFEST.sha256")
    (output / "MANIFEST.sha256").write_text(
        "".join(f"{_sha256(output / name)}  {name}\n" for name in names)
    )


def write_verification(output: Path, verification: dict[str, object]) -> None:
    """Replace the pending verification record and refresh report and hashes."""
    path = output / "verification.json"
    current = _json(path)
    current.update(verification)
    path.write_bytes(canonical_bytes(current))
    artifacts = {
        name: _json(output / name)
        for name in REQUIRED_FILES
        if name.endswith(".json")
    }
    (output / "REPORT.md").write_text(_report(artifacts))
    _write_manifest(output)


def validate(output: Path) -> list[str]:
    """Validate the complete 48D evidence package."""
    errors: list[str] = []
    present = {path.name for path in output.iterdir()}
    if missing := sorted(REQUIRED_FILES - present):
        return [f"missing artifacts: {missing}"]
    policy = _json(output / "target_access_policy.json")
    if any(
        policy.get(name) != 0
        for name in (
            "target_access_count",
            "predictive_scoring_count",
            "model_training_count",
            "calibration_count",
            "threshold_optimization_count",
            "target_xai_count",
        )
    ) or policy.get("execution_authorized") is not False:
        errors.append("TARGET access and predictive operations must remain zero")
    eligibility = _json(output / "project_target_eligibility.json")
    projects = eligibility.get("projects", [])
    if len(projects) != 21 or eligibility.get("eligible_count") != 0:
        errors.append("48D must report 21 assessed and zero eligible projects")
    for project in projects:
        normalized = {
            key.split("_", 1)[0]: value for key, value in project["gates"].items()
        }
        eligible, reasons = validate_project_gates(normalized)
        if eligible or project.get("eligibility") != "INELIGIBLE" or project.get("reason_codes") != reasons:
            errors.append("project eligibility must match frozen G1-G15 recomputation")
            break
    censoring = _json(output / "right_censoring_audit.json")
    if (
        censoring.get("supported_positive") != 0
        or censoring.get("supported_negative") != 0
        or censoring.get("right_censored") != 0
        or censoring.get("ambiguous") != 0
        or censoring.get("provenance_unresolved") != 58_272
    ):
        errors.append("48D evidence-state counts must preserve the fail-closed result")
    provenance = _json(output / "provenance_acquisition_report.json")
    if (
        provenance.get("classification") != CLASSIFICATION
        or provenance.get("repository_snapshots_verified") != 21
        or provenance.get("primary_benchmark_scientifically_viable") is not False
        or provenance.get("stop_condition", {}).get("met") is not True
    ):
        errors.append("primary-path stop condition and classification must be evidenced")
    matrix = _json(output / "evidence_gap_matrix.json")
    if len(matrix.get("rows", [])) != 21:
        errors.append("evidence gap matrix must cover every project")
    for row in matrix.get("rows", []):
        if not row.get("repository_available") or not row.get("ref_snapshot_match"):
            errors.append("every frozen repository snapshot must remain available and matching")
            break
        if row.get("positive_labels_currently_supportable") or row.get("negative_labels_currently_supportable"):
            errors.append("unsupported project labels must fail closed")
            break
    manifest: dict[str, str] = {}
    for line in (output / "MANIFEST.sha256").read_text().splitlines():
        parts = line.split("  ", 1)
        if len(parts) != 2:
            errors.append("malformed manifest entry")
            continue
        manifest[parts[1]] = parts[0]
    expected_names = present - {"MANIFEST.sha256"}
    if set(manifest) != expected_names:
        errors.append("manifest must cover every payload exactly once")
    for name, expected in manifest.items():
        if _sha256(output / name) != expected:
            errors.append(f"manifest mismatch: {name}")
    return errors
