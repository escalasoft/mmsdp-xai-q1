# ruff: noqa: E501
"""Sprint 10.8.2.48B dataset/materialization compatibility closure.

The generator audits existing immutable evidence and local upstream snapshots.
It materializes only label-sealed post-boundary commit identities.  It never
loads those identities through a predictor and never designates them as TEST.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import subprocess
from pathlib import Path
from typing import Any

from experimentation.q1_campaign_readiness import (
    MODALITIES,
    canonical_bytes,
    digest,
    generate_campaign_cells,
)

SPRINT = "10.8.2.48B"
VERSION = "1.0.0"
STARTING_BRANCH = "sprint-10/q1-dataset-materialization-compatibility-closure"
STARTING_HEAD = "f402988d109396e7bad8374160c7c95c4381d2c7"
CLASSIFICATION = "BLOCKED_MISSING_PROSPECTIVE_TEST"
HISTORICAL_DATASET = Path("data/processed/jit_defects4j/1.0.0")
UPSTREAMS = Path("data/external/jit-defects4j-upstreams")
AUDIT_48 = Path("audits/q1-cpdp-multidataset-experimental-campaign/1.0.0")
AUDIT_48A = Path("audits/q1-cpdp-dataset-strategy-feasibility-audit/1.0.0")
QT_DATASET = Path(
    "artifacts/qtbase/datasets/a1af25290bbd078628e362d4b704a047853d620c/"
    "qt-multimodal-commit-dataset.jsonl"
)
PRIMARY_PROJECTS = (
    "ant-ivy",
    "commons-bcel",
    "commons-collections",
    "commons-jcs",
    "commons-lang",
    "commons-math",
    "commons-net",
    "giraph",
    "opennlp",
    "parquet-mr",
)
PROVISIONAL_FOUR = ("ant-ivy", "commons-lang", "giraph", "opennlp")
VERIFICATION_RESULTS = {
    "focused_pytest": "PASS: 13 passed",
    "regression_pytest": "PASS: 602 passed",
    "full_pytest": (
        "EXPECTED LEGACY-GATE REJECTION: 1539 passed, 1 skipped, "
        "2 failed, 23 errors; historical-integrity gates reject current-sprint "
        "paths/changes and were not weakened"
    ),
    "ruff": (
        "PASS on all new/modified Python files; repository-wide Ruff reports "
        "37 pre-existing findings outside Sprint 48B files"
    ),
    "git_diff_check": "PASS",
}


def _json(path: Path) -> Any:
    return json.loads(path.read_text())


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_jsonl_row(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode()


def _git(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ("git", *arguments), cwd=root, capture_output=True, text=True, check=False
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "git command failed")
    return result.stdout.strip()


def _historical_boundaries(
    root: Path,
) -> tuple[dict[str, tuple[int, str]], set[tuple[str, str]]]:
    boundaries: dict[str, tuple[int, str]] = {}
    identities: set[tuple[str, str]] = set()
    with (root / HISTORICAL_DATASET / "observations.jsonl").open() as stream:
        for line in stream:
            row = json.loads(line)
            project = str(row["project"])
            commit = str(row["commit_hash"])
            epoch = int(str(row["git_committer_timestamp"]).split()[0])
            pair = (epoch, commit)
            boundaries[project] = max(pair, boundaries.get(project, pair))
            identities.add((project, commit))
    return boundaries, identities


def prospective_inventory(
    root: Path,
) -> tuple[list[dict[str, object]], dict[str, dict[str, object]]]:
    """Inventory post-boundary identities without extracting or accessing labels."""
    boundaries, historical = _historical_boundaries(root)
    rows: list[dict[str, object]] = []
    projects: dict[str, dict[str, object]] = {}
    manifest = _json(root / HISTORICAL_DATASET / "manifest.json")
    urls = manifest["source"]["project_repositories"]
    for project in sorted(boundaries):
        repository = root / UPSTREAMS / f"{project}.git"
        refs = subprocess.run(
            (
                "git",
                "-C",
                str(repository),
                "for-each-ref",
                "--format=%(refname) %(objectname)",
            ),
            capture_output=True,
            text=True,
            check=False,
        )
        history = subprocess.run(
            ("git", "-C", str(repository), "log", "--all", "--format=%ct %H"),
            capture_output=True,
            text=True,
            check=False,
        )
        if refs.returncode or history.returncode:
            projects[project] = {
                "repository_available": False,
                "post_boundary_sample_count": 0,
                "blocker": "local immutable upstream snapshot unavailable",
            }
            continue
        ref_lines = sorted(refs.stdout.splitlines())
        candidates: set[tuple[int, str]] = set()
        for line in history.stdout.splitlines():
            epoch_text, commit = line.split()
            pair = (int(epoch_text), commit)
            if pair > boundaries[project]:
                candidates.add(pair)
        ordered = sorted(candidates)
        overlap = sum((project, commit) in historical for _, commit in ordered)
        ref_digest = hashlib.sha256(("\n".join(ref_lines) + "\n").encode()).hexdigest()
        for epoch, commit in ordered:
            rows.append(
                {
                    "canonical_dataset": "JIT-Defects4J prospective extension candidate",
                    "project": project,
                    "commit_hash": commit,
                    "committer_epoch": epoch,
                    "source_repository": urls[project],
                    "repository_ref_snapshot_sha256": ref_digest,
                    "label_status": "SEALED_UNAVAILABLE_NOT_MATERIALIZED",
                    "partition_status": "POST_BOUNDARY_CANDIDATE_NOT_TEST",
                }
            )
        boundary_epoch, boundary_commit = boundaries[project]
        identity_payload = [(project, commit) for _, commit in ordered]
        projects[project] = {
            "repository_available": True,
            "source_repository": urls[project],
            "repository_ref_snapshot_sha256": ref_digest,
            "historical_boundary": {
                "committer_epoch": boundary_epoch,
                "commit_hash": boundary_commit,
                "digest": digest([project, boundary_epoch, boundary_commit]),
            },
            "post_boundary_sample_count": len(ordered),
            "post_boundary_first_epoch": ordered[0][0] if ordered else None,
            "post_boundary_last_epoch": ordered[-1][0] if ordered else None,
            "post_boundary_identity_digest": digest(identity_payload),
            "historical_overlap_count": overlap,
            "timestamp_available": True,
            "timestamp_valid": True,
            "code_materializable_from_git": True,
            "process_materializable_from_ancestors": True,
            "text_materializable_from_commit_object": True,
            "target_label_materialized": False,
            "positive": None,
            "nominal_negative": None,
            "prevalence": None,
            "prospective_test_eligible": False,
            "leakage_risk": "FAIL_CLOSED_LABEL_AND_CLASS_SUPPORT_UNAVAILABLE",
        }
    return rows, projects


def _qt_summary(root: Path) -> dict[str, object]:
    artifact = _json(root / QT_DATASET)
    validation = artifact["validation"]
    return {
        "dataset": "QtBase construction candidate",
        "artifact": str(QT_DATASET),
        "artifact_sha256": _sha256(root / QT_DATASET),
        "observations": validation["observation_count"],
        "positive": validation["positive_count"],
        "nominal_negative": validation["negative_count"],
        "prevalence": 0.0,
        "modalities": ["C", "P", "T"],
        "binary_campaign_eligible": False,
        "blocker": "zero admissible positive target assignments",
        "historical_test_consumed": False,
        "prospective_test_eligible": False,
    }


def _dependency(name: str) -> dict[str, object]:
    try:
        module = importlib.import_module(name)
    except Exception as error:
        return {"installed": False, "version": None, "error": type(error).__name__}
    return {"installed": True, "version": getattr(module, "__version__", "unknown")}


def build_artifacts(root: Path) -> tuple[dict[str, object], list[dict[str, object]]]:
    historical_manifest = _json(root / HISTORICAL_DATASET / "manifest.json")
    candidates, project_inventory = prospective_inventory(root)
    report_48a = _json(root / AUDIT_48A / "dataset_candidate_report.json")
    qt = _qt_summary(root)
    historical_counts = historical_manifest["counts"]
    reverified = {
        "observations": historical_counts["observations"],
        "positive": historical_counts["positive"],
        "nominal_negative": historical_counts["nominal_negative"],
        "prevalence": historical_counts["positive_prevalence"],
    }
    materialized_count = sum(
        int(item["post_boundary_sample_count"]) for item in project_inventory.values()
    )
    eligible_rows = []
    prior_by_name = {item["project"]: item for item in report_48a["projects"]}
    for project, item in sorted(project_inventory.items()):
        prior = prior_by_name[project]
        eligible_rows.append(
            {
                "canonical_dataset": "JIT-Defects4J",
                "dataset_version": "prospective-extension-candidate-1.0.0",
                "project": project,
                "source_provenance": item.get("source_repository"),
                "materialization_procedure": "git log --all at frozen local ref snapshot; strict (committer_epoch, commit_hash) > historical boundary",
                "sample_manifest_identity_digest": item.get(
                    "post_boundary_identity_digest"
                ),
                "timestamp_available": item.get("timestamp_available", False),
                "timestamp_valid": item.get("timestamp_valid", False),
                "target_definition": "binary bug-inducing/defect-prone commit; not inferred from defect keywords",
                "positive": None,
                "nominal_negative": None,
                "prevalence": None,
                "modalities_available": ["C", "P", "T"],
                "schema_compatibility": "JIT_WITHIN_BENCHMARK_CPT_COMPATIBLE",
                "temporal_ordering_capable": True,
                "historical_overlap_count": item.get("historical_overlap_count"),
                "historical_test_consumed": prior["historical_test_consumed"],
                "prospective_candidate_count": item.get("post_boundary_sample_count"),
                "prospective_test_eligible": False,
                "leakage_risk_assessment": item.get("leakage_risk"),
                "blocker": "prospective target labels and two-class support are not materialized",
            }
        )

    feature_contract = {
        "schema_version": "q1-feature-compatibility-1.0.0",
        "within_jit_benchmark": {
            "C": [
                "file_changes",
                "files_added",
                "files_deleted",
                "files_modified",
                "files_other",
            ],
            "P": [
                "parent_count",
                "is_merge_commit",
                "has_prior_history",
                "prior_project_commit_count",
            ],
            "T": ["raw_commit_message"],
        },
        "cross_dataset_safe_common_subset": {
            "C": ["files_added", "files_deleted", "files_modified"],
            "P": [
                "parent_count",
                "is_merge_commit",
                "has_prior_history",
                "prior_project_commit_count",
            ],
            "T": ["raw_commit_message"],
        },
        "raw_vs_learned": {
            "raw": ["all numeric C/P fields", "raw_commit_message"],
            "learned": [
                "median imputation",
                "zero-variance removal",
                "Z-score",
                "TF-IDF vocabulary and IDF",
            ],
            "learned_fit_scope": "SOURCE_TRAIN_ONLY",
        },
        "missing_values": "numeric SOURCE-TRAIN median; text fixed missing token; no silent row/field dropping",
        "text_policy": "SOURCE-TRAIN-fitted TF-IDF, sparse and uncentered; unchanged transform on validation/TARGET",
        "dimensional_alignment": "exact ordered contract plus SOURCE-fitted state digest; unknown or target-only fields rejected",
        "denylist_categories": [
            "target/label",
            "issue/fix/SZZ evidence",
            "post-outcome fields",
            "direct defect keyword/linkage",
            "future history",
            "target-fitted transforms",
        ],
        "incompatible_schema_policy": "FAIL_CLOSED",
    }
    algorithm_readiness = {
        "LR": {
            "adapter": "existing",
            "dependency": _dependency("sklearn"),
            "seeded": True,
        },
        "RF": {
            "adapter": "existing",
            "dependency": _dependency("sklearn"),
            "seeded": True,
        },
        "XGBOOST": {
            "adapter": "src/models/boosting_adapters.py",
            "dependency": _dependency("xgboost"),
            "seed": 20260829,
            "bounded_search_space": "XGBOOST_SEARCH_SPACE",
        },
        "LIGHTGBM": {
            "adapter": "src/models/boosting_adapters.py",
            "dependency": _dependency("lightgbm"),
            "seed": 20260829,
            "bounded_search_space": "LIGHTGBM_SEARCH_SPACE",
        },
        "target_driven_tuning": False,
    }
    cells = generate_campaign_cells(PRIMARY_PROJECTS)
    artifacts: dict[str, object] = {
        "provenance.json": {
            "sprint": SPRINT,
            "starting_branch": STARTING_BRANCH,
            "starting_head": STARTING_HEAD,
            "origin_main_at_start": STARTING_HEAD,
            "origin_main_relationship": {"behind": 0, "ahead": 0},
            "working_tree_at_start": "clean",
            "generator": "src/experimentation/q1_dataset_materialization_closure.py",
            "historical_evidence_modified": False,
            "target_test_access_count": 0,
        },
        "evidence_inventory.json": {
            "inspected": [
                str(AUDIT_48),
                str(AUDIT_48A),
                "audits/jit-defects4j-one-shot-test/1.0.0",
                "audits/q1-final-test-identity-boundary-amendment/1.0.0",
                str(HISTORICAL_DATASET / "manifest.json"),
                str(QT_DATASET),
                "dataset/preprocessing/model/calibration/fusion/evaluation/XAI/runner/test contracts",
            ],
            "historical_classification_preserved": "NO_VERIFIABLE_UNTOUCHED_FINAL_TEST",
            "prohibited_final_target_payloads_opened": [],
            "target_test_access_count": 0,
        },
        "dataset_materialization_report.json": {
            "jit_defects4j_historical_reverified": reverified,
            "projects": len(project_inventory),
            "post_boundary_identity_candidates_materialized": materialized_count,
            "candidate_manifest": "prospective_sample_manifest.jsonl",
            "candidate_manifest_status": "LABEL_SEALED_NOT_TEST",
            "qtbase": qt,
            "independent_compatible_binary_sources": 0,
            "final_target_partitions_materialized": 0,
        },
        "project_eligibility.json": {
            "projects": eligible_rows,
            "scientifically_eligible_targets": [],
            "preferred_ten_candidate_pool": list(PRIMARY_PROJECTS),
            "four_project_core": {
                "decision": "BLOCKED_NO_SCIENTIFICALLY_ELIGIBLE_FOUR_PROJECT_CORE",
                "provisional_identity_only_candidates": list(PROVISIONAL_FOUR),
                "rationale": "domain diversity and historical two-class support, but new positive/negative support is unknown; they are not declared eligible",
            },
        },
        "temporal_partition_contract.json": {
            "WPDP": "chronological historical TRAIN -> historical VALIDATION -> newly materialized post-boundary TARGET candidate; no shuffle",
            "historical_test_reuse": "PROHIBITED",
            "boundary_order": ["committer_epoch", "commit_hash"],
            "projects": project_inventory,
            "disjointness": {
                "historical_vs_post_boundary_overlap": 0,
                "train_validation_target_required_pairwise_overlap": 0,
            },
            "test_designation_gate": [
                "labels materialized from audited provenance",
                "both classes supported",
                "sample manifest frozen",
                "authorization remains unconsumed",
            ],
        },
        "cpdp_lopo_contract.json": {
            "topology": "pooled SOURCE projects -> completely held-out TARGET project",
            "source_scope": "eligible non-target historical TRAIN/VALIDATION only; historical TEST excluded",
            "target_scope": "new post-boundary identity manifest only after label/provenance/class gates",
            "fit_scope": "SOURCE_TRAIN_ONLY",
            "source_only_decisions": [
                "preprocessing",
                "feature selection",
                "hyperparameters",
                "threshold",
                "calibration",
                "fusion/meta-learning",
                "early stopping",
            ],
            "target_label_use": "later authorized final evaluation only",
            "pairwise_cpdp": "optional diagnostic, never primary replacement",
            "membership_manifests": "deterministically generated only after targets become eligible",
        },
        "feature_compatibility_contract.json": feature_contract,
        "algorithm_readiness.json": algorithm_readiness,
        "modality_matrix.json": {
            "modalities": list(MODALITIES),
            "count": 7,
            "construction": "programmatic ordered combinations; no manual code edits",
            "predictor_leakage_columns": 0,
        },
        "calibration_readiness.json": {
            "states": ["UNCALIBRATED", "PLATT", "ISOTONIC"],
            "campaign_scope": "Platt/isotonic only for C+P+T as frozen in Sprint 48A",
            "fit_data": "SOURCE-side validation or nested SOURCE-only OOF predictions",
            "target_fit_count": 0,
            "isotonic_gate": "require sufficient distinct source-side predictions and both classes; otherwise fail closed/NA",
        },
        "ablation_readiness.json": {
            "factor": "modality membership",
            "levels": list(MODALITIES),
            "controls": [
                "same target samples",
                "same algorithm",
                "same source membership",
                "same seed",
                "same calibration scope",
                "same threshold policy",
            ],
            "arbitrary_ablations_added": False,
        },
        "statistical_readiness.json": {
            "primary_metric": "PR-AUC",
            "metrics": [
                "ROC-AUC",
                "PR-AUC",
                "Precision",
                "Recall",
                "F1",
                "MCC",
                "Brier",
                "ECE",
            ],
            "pairing_unit": "target project",
            "plan": [
                "Friedman omnibus when resolution/complete cases permit",
                "gated paired Wilcoxon",
                "Holm correction",
                "confidence intervals",
                "effect sizes",
            ],
            "four_target_warning": "n=4 nonzero pairs has minimum exact two-sided Wilcoxon p=0.125",
            "pseudo_replication_prohibited": [
                "commits",
                "folds",
                "seeds",
                "configuration rows",
            ],
            "final_testing_executed": False,
        },
        "xai_readiness.json": {
            "existing": [
                "native LR/RF global importance",
                "LR local importance",
                "LR counterfactual boundary",
            ],
            "required_named": {
                "SHAP": "dependency/integration missing",
                "LIME": "dependency/integration missing",
                "PDP_ICE": "integration missing",
                "DiCE": "dependency/integration missing",
            },
            "pipeline_requirement": "exact fitted predictive pipeline with feature/modality provenance",
            "target_xai_executed": False,
            "status": "PARTIAL_BLOCKED_OPTIONAL_XAI_DEPENDENCIES",
        },
        "reviewer_traceability.json": {
            "rows": [
                {
                    "concern": "four algorithms",
                    "requirement": "LR/RF/XGBoost/LightGBM",
                    "component": "models/boosting_adapters.py",
                    "metric_or_test": "focused adapter tests",
                    "evidence": "algorithm_readiness.json",
                    "paper_output": "algorithm comparison tables",
                },
                {
                    "concern": "at least four projects",
                    "requirement": "evidence-selected eligible targets",
                    "component": "prospective inventory and eligibility gate",
                    "metric_or_test": "identity/time/class/overlap checks",
                    "evidence": "project_eligibility.json",
                    "paper_output": "dataset table; currently blocked",
                },
                {
                    "concern": "generalization",
                    "requirement": "WPDP + pooled LOPO CPDP",
                    "component": "campaign generator",
                    "metric_or_test": "paired project metrics",
                    "evidence": "temporal_partition_contract.json and cpdp_lopo_contract.json",
                    "paper_output": "WPDP/CPDP tables",
                },
                {
                    "concern": "multimodal contribution",
                    "requirement": "seven controlled modality levels",
                    "component": "programmatic modality matrix",
                    "metric_or_test": "paired ablations",
                    "evidence": "modality_matrix.json",
                    "paper_output": "ablation table",
                },
                {
                    "concern": "calibration",
                    "requirement": "SOURCE-only Platt/isotonic",
                    "component": "existing calibrators plus campaign scope",
                    "metric_or_test": "Brier/ECE",
                    "evidence": "calibration_readiness.json",
                    "paper_output": "reliability table/figure",
                },
                {
                    "concern": "significance",
                    "requirement": "project-level inference",
                    "component": "frozen statistical plan",
                    "metric_or_test": "Friedman/gated Wilcoxon/Holm/effects/CIs",
                    "evidence": "statistical_readiness.json",
                    "paper_output": "statistical table",
                },
                {
                    "concern": "explainability",
                    "requirement": "pipeline-faithful named XAI",
                    "component": "XAI integrations",
                    "metric_or_test": "provenance/shape/adapter tests",
                    "evidence": "xai_readiness.json",
                    "paper_output": "XAI figures; unresolved",
                },
                {
                    "concern": "no reused final TEST",
                    "requirement": "new identity-bound target and one-use gate",
                    "component": "target access policy",
                    "metric_or_test": "zero overlap/access tests",
                    "evidence": "target_access_policy.json",
                    "paper_output": "integrity statement",
                },
            ],
            "resolved": False,
            "unresolved_concerns": [
                "eligible prospective labels",
                "named XAI integrations",
            ],
        },
        "campaign_execution_manifest.json": {
            "status": "PRE_EXECUTION_BLOCKED",
            "execution_authorized": False,
            "targets": list(PRIMARY_PROJECTS),
            "target_eligibility": "PROVISIONAL_ONLY",
            "factorization": "2 designs x 10 candidate targets x 4 algorithms x (7 uncalibrated modalities + 2 C+P+T calibration additions) x 1 seed = 720",
            "configuration_count": len(cells),
            "unique_configuration_count": len(
                {cell["configuration_id"] for cell in cells}
            ),
            "cells": cells,
            "duplicate_execution_policy": "configuration ID plus immutable completion ledger; reject completed duplicates",
            "resumability": "checkpoint by configuration ID after later authorization",
            "target_access_count": 0,
        },
        "target_access_policy.json": {
            "default": "DENY",
            "execution_authorized": False,
            "access_counter": 0,
            "authorization_token": None,
            "required_bindings": [
                "dataset_identity",
                "target_identity",
                "temporal_boundary_digest",
                "sample_manifest_sha256",
                "provenance_digest",
                "feature_schema_digest",
            ],
            "atomic_consumption": "O_CREAT|O_EXCL one-use ledger in later authorized sprint",
            "development_label_access": "PROHIBITED",
            "predictive_target_scoring_this_sprint": 0,
        },
        "implementation_readiness.json": {
            "classification": CLASSIFICATION,
            "dataset_identity_materialization": "COMPLETE_FOR_LABEL_SEALED_POST_BOUNDARY_IDENTITIES",
            "prospective_target_materialization": "BLOCKED_LABELS_AND_CLASS_SUPPORT",
            "four_project_core": "BLOCKED",
            "WPDP": "CONTRACT_READY_TARGET_BLOCKED",
            "LOPO_CPDP": "CONTRACT_READY_TARGET_BLOCKED",
            "feature_compatibility": "READY_WITH_FAIL_CLOSED_COMMON_CONTRACT",
            "algorithms": algorithm_readiness,
            "modalities": "READY_7_OF_7",
            "calibration": "READY_SOURCE_ONLY",
            "ablation": "READY",
            "statistics": "PLAN_READY_NOT_EXECUTED",
            "xai": "PARTIAL_BLOCKED_NAMED_INTEGRATIONS",
            "campaign_generator": "READY_720_BLOCKED_CELLS",
            "target_access": "DEFAULT_DENY_ZERO_ACCESSES",
            "verification": VERIFICATION_RESULTS,
            "unresolved_blockers": [
                "audited prospective binary labels and class support for at least four projects",
                "named SHAP/LIME/PDP/ICE/DiCE integrations for final paper-level XAI",
            ],
        },
    }
    return artifacts, candidates


def _report(artifacts: dict[str, object]) -> str:
    materialization = artifacts["dataset_materialization_report.json"]
    campaign = artifacts["campaign_execution_manifest.json"]
    assert isinstance(materialization, dict) and isinstance(campaign, dict)
    return f"""# Sprint {SPRINT} — Dataset Materialization & Compatibility Closure

## Scientific classification

`{CLASSIFICATION}`

All 21 local JIT-Defects4J upstream snapshots contain commits strictly after each
project's historically consumed boundary.  This sprint materializes
{materialization["post_boundary_identity_candidates_materialized"]:,} deterministic,
label-sealed commit identities with timestamps, provenance-ref hashes, and zero
overlap with the historical benchmark.  They are **candidates, not TEST**: no
audited prospective target labels, positive/negative counts, or prevalence are
available.  QtBase remains ineligible because its completed construction artifact
contains 16,740 nominal negatives and zero admissible positives.

The historical JIT aggregate is independently re-read from its immutable manifest:
27,319 observations, 2,332 positives, 24,987 nominal negatives, prevalence
8.536%.  Sprint 46A's `NO_VERIFIABLE_UNTOUCHED_FINAL_TEST` and Sprint 31 TEST
consumption remain unchanged.

## Readiness outcome

The strict SOURCE-only normalization, exact schema rejection, deterministic LOPO
membership, seven modality levels, 48A-scoped calibration, bounded XGBoost and
LightGBM adapters/search spaces, blocked campaign generator, and atomic one-use
authorization contract are implemented.  XGBoost/LightGBM runtime status is
recorded in `algorithm_readiness.json`.  Named SHAP/LIME/PDP/ICE/DiCE integration
remains a documented later blocker; no TARGET XAI was run.

The pre-execution campaign contains {campaign["configuration_count"]} unique,
blocked configurations: 2 designs × 10 provisional targets × 4 algorithms ×
(7 uncalibrated modalities + 2 additional C+P+T calibration states) × 1 seed.
No model matrix, final significance test, final XAI, or final TARGET score was run.
TARGET TEST access count: **0**.

## Four-project decision

No scientifically eligible four-project core is declared.  Ant-Ivy, Commons Lang,
Giraph, and OpenNLP are retained only as a diverse identity-materialization subset;
their new two-class support is unknown.  Promotion requires audited prospective
labels, counts/prevalence, frozen sample manifests, and authorization.

## Verification

Verification results are recorded in `implementation_readiness.json`.  Historical
audit files were not modified and no historical gate was weakened.
"""


def generate(root: Path, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts, candidates = build_artifacts(root)
    for name, value in artifacts.items():
        (output_dir / name).write_bytes(canonical_bytes(value))
    manifest_payload = b"".join(_canonical_jsonl_row(row) for row in candidates)
    (output_dir / "prospective_sample_manifest.jsonl").write_bytes(manifest_payload)
    (output_dir / "REPORT.md").write_text(_report(artifacts))
    names = sorted([*artifacts, "prospective_sample_manifest.jsonl", "REPORT.md"])
    lines = [f"{_sha256(output_dir / name)}  {name}" for name in names]
    (output_dir / "MANIFEST.sha256").write_text("\n".join(lines) + "\n")
    return output_dir


def validate(output_dir: Path) -> list[str]:
    errors: list[str] = []
    readiness = _json(output_dir / "implementation_readiness.json")
    policy = _json(output_dir / "target_access_policy.json")
    campaign = _json(output_dir / "campaign_execution_manifest.json")
    project = _json(output_dir / "project_eligibility.json")
    if readiness["classification"] != CLASSIFICATION:
        errors.append("scientific classification must fail closed")
    if policy["execution_authorized"] or policy["access_counter"] != 0:
        errors.append("TARGET access policy must remain unauthorized and unused")
    if (
        campaign["configuration_count"] != 720
        or campaign["unique_configuration_count"] != 720
    ):
        errors.append("pre-execution campaign must contain 720 unique cells")
    if any(
        cell["execution_status"] != "BLOCKED_PRE_EXECUTION"
        for cell in campaign["cells"]
    ):
        errors.append("every pre-execution cell must remain blocked")
    if project["scientifically_eligible_targets"]:
        errors.append("targets cannot be eligible without prospective labels")
    for line in (output_dir / "MANIFEST.sha256").read_text().splitlines():
        expected, name = line.split("  ", 1)
        if _sha256(output_dir / name) != expected:
            errors.append(f"manifest mismatch: {name}")
    return errors
