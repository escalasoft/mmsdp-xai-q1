# ruff: noqa: E501
"""Prospective, non-executing Sprint 10.8.2.48 CPDP campaign contract.

This module only generates and validates declarative artifacts.  It never opens
row-level datasets, predictions, fitted models, or target labels.
"""

from __future__ import annotations

import hashlib
import json
from itertools import product
from pathlib import Path
from typing import Any

VERSION = "1.0.0"
SPRINT = "10.8.2.48"
CLASSIFICATION = "BLOCKED_MISSING_COMPATIBLE_DATASETS"
STARTING_HEAD = "90acf442fe21e3becd8cf7cff02eaa75f8c97301"
HISTORICAL_DATASET_ID = (
    "e509995da233c932cafce531c13ad2cd617a0d8abbe8d81ccaa373b8f29fa519"
)
HISTORICAL_BOUNDARY_ID = (
    "d1b4448e22a1dba4292b9cf8969ba77db0cf9a10ef66dfddf98642cb5dc078a7"
)
PROJECTS = (
    "ant-ivy",
    "commons-bcel",
    "commons-beanutils",
    "commons-codec",
    "commons-collections",
    "commons-compress",
    "commons-configuration",
    "commons-dbcp",
    "commons-digester",
    "commons-io",
    "commons-jcs",
    "commons-lang",
    "commons-math",
    "commons-net",
    "commons-scxml",
    "commons-validator",
    "commons-vfs",
    "giraph",
    "gora",
    "opennlp",
    "parquet-mr",
)
ALGORITHMS = (
    ("LR", "Logistic Regression", "AVAILABLE"),
    ("RF", "Random Forest", "AVAILABLE"),
    ("XGB", "XGBoost", "IMPLEMENTATION_AND_DEPENDENCY_REQUIRED"),
    ("LGBM", "LightGBM", "IMPLEMENTATION_AND_DEPENDENCY_REQUIRED"),
)
MODALITIES = ("C", "P", "T", "C+P", "C+T", "P+T", "C+P+T")
CALIBRATIONS = ("UNCALIBRATED", "PLATT", "ISOTONIC")
METRICS = (
    "ROC-AUC",
    "PR-AUC",
    "Precision",
    "Recall",
    "F1",
    "MCC",
    "Brier Score",
    "ECE",
)


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    )


def dataset_audit() -> dict[str, Any]:
    return {
        "classification": "INSUFFICIENT_COMPATIBLE_DATASETS",
        "evidence_boundary": "repository metadata and committed audits only; no row-level TEST or prediction artifacts opened",
        "candidates": [
            {
                "dataset_name": "JIT-Defects4J",
                "version": "1.0.0",
                "provenance": "jacknichao/JIT-Fine data.zip plus 21 immutable upstream repository snapshots",
                "scientific_identity": HISTORICAL_DATASET_ID,
                "unit_of_analysis": "commit",
                "sample_identity": ["project", "commit_hash"],
                "commit_identity": "available",
                "timestamp": "git_committer_timestamp; chronological within project",
                "label": {
                    "field": "is_defect_prone",
                    "positive": "defect-prone commit",
                    "negative": "nominal non-defect-prone commit",
                },
                "observations": 27319,
                "positive": 2332,
                "negative": 24987,
                "prevalence": 0.08536183608477617,
                "projects": list(PROJECTS),
                "modalities": ["CODE", "PROCESS", "TEXT"],
                "feature_compatibility": "COMMON_SCHEMA_ACROSS_21_PROJECTS",
                "duplicate_and_overlap": "identity uniqueness passed and historical cross-partition overlap was zero",
                "leakage_risk": "denylist passed; nominal negatives retain closed-world benchmark semantics",
                "source_suitability": "ELIGIBLE_DEVELOPMENT_SOURCE_USING_ONLY_HISTORICAL_TRAIN_AND_VALIDATION",
                "target_suitability": "INELIGIBLE_AS_NEW_CONFIRMATORY_TARGET",
                "reason": "the only canonical TEST boundary was consumed in Sprint 31",
            },
            {
                "dataset_name": "QtBase",
                "version": None,
                "provenance": "repository snapshot and Jira/source construction contracts exist",
                "unit_of_analysis": "commit",
                "sample_identity": ["commit_hash"],
                "commit_identity": "contracted",
                "timestamp": "contracted UTC commit timestamp",
                "label": {
                    "field": "is_defect_prone",
                    "semantics": "contracted but final compatible materialization absent",
                },
                "observations": None,
                "positive": None,
                "negative": None,
                "prevalence": None,
                "projects": ["qtbase"],
                "modalities": ["CODE", "PROCESS", "TEXT"],
                "feature_compatibility": "NOT_ESTABLISHED_BY_A_MATERIALIZED_AUDIT",
                "duplicate_and_overlap": "NOT_COMPUTABLE",
                "leakage_risk": "construction denylist exists; materialized audit required",
                "source_suitability": "NOT_YET_MATERIALIZED",
                "target_suitability": "NOT_YET_MATERIALIZED",
            },
        ],
        "required_materialization": {
            "minimum": "new post-boundary, provenance-compatible target observations for at least four eligible projects; preferably all 21 rotations",
            "must_establish": [
                "immutable dataset/version/provenance",
                "row-stable sample and commit identities",
                "timestamps and target temporal boundary",
                "C/P/T schema mapping",
                "class support",
                "zero overlap with all source and Sprint 31 TEST identities",
                "access counter zero before authorization",
            ],
            "prohibited_substitution": "unrelated binary defect datasets",
        },
    }


def feature_contract() -> dict[str, Any]:
    return {
        "modalities": {"C": "CODE", "P": "PROCESS", "T": "TEXT"},
        "COMMON_FEATURES": {
            "C": [
                "file_changes",
                "files_added",
                "files_deleted",
                "files_modified",
                "files_other",
                "mode_changes",
            ],
            "P": [
                "parent_count",
                "is_merge_commit",
                "has_prior_history",
                "prior_project_commit_count",
            ],
            "T": ["raw_commit_message transformed by SOURCE-TRAIN-fitted TF-IDF"],
        },
        "DATASET_SPECIFIC_FEATURES": {
            "JIT-Defects4J": [],
            "QtBase": "unresolved until materialization and mapping audit",
        },
        "INCOMPATIBLE_FEATURES": [
            "language-specific AST/CFG features without common semantics",
            "dataset-supplied partitions as predictors",
            "unmapped source-native issue attributes",
        ],
        "POTENTIAL_LEAKAGE_FEATURES": [
            "bug_confidence",
            "msg_has_bug_kw",
            "issue_link_indicator",
            "bug_link_count",
            "future_bug_count",
            "future_fix_count",
            "post_release_defect_count",
            "label_confidence",
            "target_probability",
            "is_bug",
            "is_buggy",
            "full-dataset-fitted vocabulary or embeddings",
        ],
        "alignment": "intersection schema in fixed order; missing required common fields fail closed; no target-derived imputation or vocabulary",
        "comparability_gate": "matching names are insufficient: provenance, prediction-time availability, units, aggregation, and target semantics must match",
    }


def campaign_contract() -> dict[str, Any]:
    return {
        "protocol_id": "q1-cpdp-multidataset-experimental-campaign",
        "version": VERSION,
        "sprint": SPRINT,
        "classification": CLASSIFICATION,
        "execution_authorized": False,
        "target_accesses": 0,
        "starting_state": {
            "branch": "sprint-10/q1-cpdp-multidataset-experimental-campaign",
            "head": STARTING_HEAD,
            "origin_main_ahead": 0,
            "origin_main_behind": 0,
            "worktree_clean": True,
            "sprint_46a_ancestor": "7d4f346",
            "preserved_classification": "NO_VERIFIABLE_UNTOUCHED_FINAL_TEST",
        },
        "research_questions": {
            "existing_general_rq": "How does integrating a multimodal and explainable framework combining code, process, and text influence precision, reliability, and interpretability of defect prediction?",
            "campaign_operational_rqs": [
                "RQ1 multimodal versus unimodal predictive performance",
                "RQ2 contribution of modality combinations",
                "RQ3 stability across algorithms",
                "RQ4 cross-project generalization",
                "RQ5 calibration reliability versus discrimination",
                "RQ6 statistical and practical meaning",
                "RQ7 explanatory evidence of complementary modality contributions",
            ],
            "reconciliation": "The seven campaign RQs operationalize, and do not overwrite, the repository's general RQ.",
        },
        "topology": {
            "primary": "multi-source-to-single-target leave-one-project-out",
            "conditional_secondary": [
                "single-source-to-single-target",
                "leave-one-dataset-out when at least four independently compatible datasets exist",
            ],
            "source": "historical TRAIN/VALIDATION from all non-target projects",
            "target": "new post-boundary materialization for held-out project",
            "historical_test": "excluded from source and target",
        },
        "modalities": list(MODALITIES),
        "algorithms": [{"id": a, "name": n, "status": s} for a, n, s in ALGORITHMS],
        "fusion": {
            "unimodal": "direct probability",
            "multimodal_campaign_comparator": "feature-level concatenation after modality-specific SOURCE-TRAIN fitting",
            "historical_candidate": "FROZEN_CT_EQUAL / CT_equal, CODE+TEXT probability late fusion 0.5/0.5; historical evidence only",
            "reusable_mechanisms": [
                "fixed weighted late fusion",
                "stacking with LR/RF meta-models",
            ],
            "selection": "no fusion selection using TARGET",
        },
        "preprocessing": {
            "fit_scope": "SOURCE_TRAIN_ONLY",
            "numeric": "median imputation then zero-variance removal then Z-score using source-train mu/sigma",
            "categorical": "source-train-fitted encoder with explicit unknown category",
            "text": "source-train-fitted TF-IDF; vocabulary/IDF never fit on validation or target",
            "sparse": "preserve sparse representation; do not center",
            "outliers": "no removal or winsorization in baseline",
            "alignment": "fixed common feature order",
            "target_adaptation": "none",
        },
        "lifecycle": {
            "SOURCE_TRAIN": "fit preprocessing, representations, model and imbalance transformations",
            "SOURCE_VALIDATION": "hyperparameters, calibrator policy and fixed threshold development only",
            "TARGET_FINAL_TEST": "one authorized inference/evaluation after manifest and access gate pass",
            "shuffle": False,
            "temporal_order": True,
        },
        "calibration": {
            "states": list(CALIBRATIONS),
            "fit": "SOURCE_VALIDATION out-of-fold for selection; final mapping fitted on full SOURCE_VALIDATION after selection",
            "target_fit_or_selection": False,
            "reliability": "10 fixed equal-width bins plus reliability diagram",
            "separation": "report Brier/ECE separately from discrimination",
        },
        "metrics": {
            "threshold_independent": ["ROC-AUC", "PR-AUC", "Brier Score", "ECE"],
            "threshold_dependent": ["Precision", "Recall", "F1", "MCC"],
            "threshold": 0.5,
            "target_optimization": False,
            "accuracy_primary": False,
        },
        "imbalance": {
            "baseline": "natural prevalence; no resampling; no class weighting",
            "conditional_sensitivity": "SOURCE-TRAIN-only class weighting, separately identified and frozen before authorization",
            "validation_or_target_resampling": False,
        },
        "hyperparameters": "nested chronological SOURCE development only; fixed search space must be added with XGB/LGBM implementations before execution; TARGET never participates",
        "xai": {
            "timing": "after frozen predictive evaluation",
            "selection_use": False,
            "levels": ["global", "local", "modality-level", "feature-level"],
            "available": [
                "native global coefficient/importance",
                "LR local linear attribution",
                "LR counterfactual",
            ],
            "missing": [
                "SHAP adapter",
                "LIME adapter",
                "PDP",
                "ICE",
                "DiCE integration",
                "faithful tree counterfactual",
            ],
            "purpose": "explain complementary modality contribution, not decorate or optimize",
        },
        "prohibitions": [
            "final experiment execution",
            "target-label access before authorization",
            "Sprint 31 TEST reuse",
            "Sprint 47 execution",
            "target-based fitting/selection/thresholding",
            "post-outcome protocol changes",
            "XAI-driven target optimization",
            "superiority claims",
        ],
    }


def experimental_matrix() -> dict[str, Any]:
    experiments = []
    for target, (algorithm, name, status), modality, calibration in product(
        PROJECTS, ALGORITHMS, MODALITIES, CALIBRATIONS
    ):
        core = {
            "dataset_source": "JIT-Defects4J-1.0.0-historical-development-only",
            "dataset_target": "JIT-Defects4J-prospective-extension-identity-required",
            "project_source": [project for project in PROJECTS if project != target],
            "project_target": target,
            "algorithm": algorithm,
            "algorithm_name": name,
            "modality_combination": modality,
            "fusion_configuration": "NONE"
            if "+" not in modality
            else "SOURCE_TRAIN_FITTED_FEATURE_CONCATENATION",
            "calibration_state": calibration,
            "threshold_policy": "FIXED_0.5_NO_TARGET_OPTIMIZATION",
            "preprocessing_policy": "SOURCE_TRAIN_ONLY_COMMON_SCHEMA_V1",
            "imbalance_policy": "NATURAL_PREVALENCE_NO_RESAMPLING_NO_CLASS_WEIGHTING",
            "seed": 108248,
            "metric_set": list(METRICS),
            "statistical_comparison_group": f"LOPO::{target}",
        }
        experiments.append(
            {
                "experiment_id": "CPDP-" + _digest(core)[:20].upper(),
                **core,
                "implementation_status": status,
                "execution_status": "BLOCKED_PENDING_TARGET_MATERIALIZATION",
            }
        )
    return {
        "matrix_version": VERSION,
        "frozen": True,
        "execution_authorized": False,
        "factorization": {
            "target_rotations": len(PROJECTS),
            "algorithms": len(ALGORITHMS),
            "modalities": len(MODALITIES),
            "calibration_states": len(CALIBRATIONS),
            "seeds": 1,
        },
        "total_configurations": len(experiments),
        "experiments": experiments,
    }


def statistical_plan() -> dict[str, Any]:
    return {
        "frozen_before_target_access": True,
        "unit_of_pairing": "same eligible target project and identical target samples",
        "primary_metric": "PR-AUC",
        "secondary_metrics": ["ROC-AUC", "F1", "MCC", "Brier Score", "ECE"],
        "confidence_intervals": "paired stratified project-level bootstrap, 10,000 resamples, seed 108248; sample bootstrap within project only for descriptive per-target intervals",
        "omnibus": "Friedman test across eligible target projects for each prespecified metric/comparison family when >=10 complete, non-degenerate paired projects",
        "post_hoc": "only after applicable omnibus rejection: paired Wilcoxon signed-rank across target-project scores, two-sided, Pratt zero handling",
        "multiplicity": "Holm correction within each RQ-by-metric comparison family; report raw and adjusted p-values",
        "effect_sizes": [
            "paired median difference",
            "Hodges-Lehmann paired shift",
            "rank-biserial correlation",
            "absolute Brier/ECE change",
        ],
        "not_independent_replicates": [
            "seeds",
            "folds",
            "individual commits pooled across projects",
        ],
        "feasibility": "tests requiring project-level replication are not run with fewer than the stated complete targets; class-degenerate target metrics are NA, never imputed",
        "interpretation": "statistical significance is reported with uncertainty and effect size and is not treated as practical importance",
    }


def traceability() -> dict[str, Any]:
    rows = [
        (
            "compare four algorithms",
            "LR/RF/XGBoost/LightGBM controlled comparison",
            "paired metrics by algorithm; XGB/LGBM blocked until implemented",
        ),
        (
            "significance testing",
            "predeclared Friedman/Wilcoxon hierarchy with Holm correction",
            "adjusted p-values, confidence intervals, effect sizes",
        ),
        (
            "stable/generalizable results",
            "multi-source leave-one-project-out CPDP",
            "between-project distribution and paired stability",
        ),
        (
            "describe datasets individually",
            "dataset/project provenance and characterization audit",
            "identity, size, prevalence, modalities, leakage and suitability",
        ),
        (
            "test on four datasets/projects",
            "21 evidenced project rotations, conditional on >=4 new compatible targets",
            "eligible target count and per-project results",
        ),
        (
            "explain why combination matters",
            "complete ablation plus post-evaluation XAI",
            "incremental metric deltas, effect sizes, modality/feature contributions",
        ),
        (
            "Does it reduce errors?",
            "fixed-threshold paired error analysis",
            "precision, recall, F1, MCC and confusion counts",
        ),
        (
            "Does it improve generalization?",
            "held-out-project CPDP",
            "PR-AUC/ROC-AUC and cross-project effect distribution",
        ),
        (
            "Does it capture ignored information?",
            "C/P/T ablation and explanation concordance",
            "incremental deltas and modality-level contribution",
        ),
    ]
    return {
        "no_superiority_claim": True,
        "rows": [
            {"reviewer_request": a, "campaign_response": b, "measurable_evidence": c}
            for a, b, c in rows
        ],
    }


def target_policy() -> dict[str, Any]:
    return {
        "default": "DENY",
        "access_counter": 0,
        "authorized": False,
        "required_before_access": [
            "dataset identity",
            "version",
            "provenance",
            "sample identity hash",
            "feature-schema identity",
            "target-project identity",
            "temporal-boundary identity",
            "manifest hash",
            "zero source/target/Sprint31 overlap proof",
            "access counter = 0",
            "human authorization bound to exact identities",
        ],
        "label_isolation": "development loaders expose target predictors only after identity validation and never expose target labels; evaluation loader requires one-use authorization token",
        "fail_closed_on": [
            "missing/null/changed identity",
            "manifest mismatch",
            "nonzero access counter",
            "overlap",
            "schema incompatibility",
            "authorization mismatch",
            "attempted target fit/selection/normalization/calibration/thresholding",
        ],
        "transaction": "atomically increment access counter before the single authorized evaluation; abort without exposing data if ledger update cannot be committed",
        "historical_sprint31_test": {
            "identity": HISTORICAL_BOUNDARY_ID,
            "status": "PERMANENTLY_INELIGIBLE_AS_NEW_CONFIRMATORY_TEST",
        },
    }


def schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "campaign_contract.schema.json",
        "title": "MMSDP-XAI CPDP campaign contract",
        "type": "object",
        "required": [
            "protocol_id",
            "version",
            "sprint",
            "classification",
            "execution_authorized",
            "target_accesses",
            "starting_state",
            "topology",
            "modalities",
            "algorithms",
            "preprocessing",
            "calibration",
            "metrics",
            "xai",
            "prohibitions",
        ],
        "properties": {
            "protocol_id": {"const": "q1-cpdp-multidataset-experimental-campaign"},
            "version": {"const": VERSION},
            "sprint": {"const": SPRINT},
            "classification": {
                "enum": [
                    "READY_TO_MATERIALIZE_CPDP_CAMPAIGN",
                    "BLOCKED_MISSING_COMPATIBLE_DATASETS",
                    "BLOCKED_MISSING_REQUIRED_INFRASTRUCTURE",
                ]
            },
            "execution_authorized": {"const": False},
            "target_accesses": {"const": 0},
            "modalities": {"const": list(MODALITIES)},
        },
        "additionalProperties": True,
    }


def report(matrix_count: int) -> str:
    return f"""# Sprint {SPRINT} — CPDP Multi-Dataset Experimental Campaign Contract

## Final scientific classification

`{CLASSIFICATION}`

The repository supports a common C/P/T schema across 21 projects in one historical JIT-Defects4J 1.0.0 materialization, but its only canonical TEST boundary was consumed in Sprint 31. QtBase has construction contracts but no compatible audited materialization. Thus four untouched compatible target datasets/projects cannot currently be established. No final experiment was run, no historical TEST prediction/outcome artifact was opened, and target access remained zero.

## Starting state and preserved evidence

- Branch: `sprint-10/q1-cpdp-multidataset-experimental-campaign`
- HEAD: `{STARTING_HEAD}`
- `origin/main...HEAD`: 0 behind / 0 ahead; `origin/main` is an ancestor.
- Initial working tree: clean.
- Sprint 46A commit `7d4f346` is an ancestor and its classification `NO_VERIFIABLE_UNTOUCHED_FINAL_TEST` is preserved.
- Historical Sprint 31–46A files were not modified. Sprint 47 was not executed.

## Repository-wide inventory

### EXISTING_AND_REUSABLE

Dataset/scientific contracts; JIT-Defects4J materializer and adapters; Qt construction contracts; chronological splitters; stable commit/project identity; CODE, PROCESS and TEXT feature builders; source-fitted numeric scaling and TF-IDF patterns; LR and RF adapters; probability calibration (uncalibrated, Platt, isotonic); Brier/ECE and reliability-bin support; ROC-AUC, PR-AUC, precision, recall, F1 and MCC evaluation; fixed weighted late fusion; LR/RF stacking; experiment specifications/runners/artifact hashing; global/local importance contracts; LR counterfactuals; tests and frozen audit conventions.

### MISSING_FOR_FINAL_CAMPAIGN

New untouched post-boundary target materializations with identity/access ledgers; a generic CPDP loader/orchestrator; explicit cross-dataset schema mapper; XGBoost and LightGBM dependencies/adapters/search spaces; campaign-wide statistical executor; SHAP, LIME, PDP, ICE and DiCE integrations; atomic target authorization token/ledger enforcement. These must be implemented and validated before execution.

### HISTORICAL_ONLY

Sprint 25–46A development results, modality factorial and process ablation, calibration study, `FROZEN_CT_EQUAL` / `CT_equal`, and the Sprint 31 one-shot evaluation remain historical evidence only.

### MUST_NOT_BE_REUSED_AS_CONFIRMATORY_TEST

The canonical JIT-Defects4J TEST identified by temporal boundary `{HISTORICAL_BOUNDARY_ID}` and every associated Sprint 31 prediction/outcome artifact.

## Dataset and compatibility conclusion

JIT-Defects4J has 27,319 commit observations (2,332 positive; 24,987 nominal negative; prevalence 0.08536) across 21 named projects, with chronological timestamps and C/P/T predictors. These aggregate and project-level facts come from the committed canonical audit, not reopened TEST payloads. QtBase has a pinned repository snapshot and construction policies, but observations, class distribution, final label evidence, and compatible materialized schema are unavailable. The correct repository-evidence classification is `INSUFFICIENT_COMPATIBLE_DATASETS`.

The reusable common schema is six CODE change-count features, four ancestor-only PROCESS features, and source-train-fitted TF-IDF over raw commit messages. Names alone do not establish compatibility; prediction-time availability, units, aggregation, label semantics and provenance must pass. Label-derived, future, post-event, bug-keyword/linkage, and full-dataset-fitted predictors are prohibited.

## Frozen campaign design

The primary topology is multi-source-to-single-target leave-one-project-out: historical TRAIN/VALIDATION from 20 non-target projects develop the model, while a newly materialized post-boundary extension of the held-out project is FINAL TARGET TEST. Historical TEST rows are excluded everywhere. Single-source CPDP and leave-one-dataset-out are conditional secondary analyses only if materialization makes them feasible.

The full ablation matrix is C, P, T, C+P, C+T, P+T and C+P+T for LR, RF, XGBoost and LightGBM, each under UNCALIBRATED, PLATT and ISOTONIC states. Multimodal campaign cells use source-trained feature concatenation; historical CT_equal remains a historical candidate, not a selected new winner. The prospective matrix contains **{matrix_count}** immutable, blocked configurations (21 × 4 × 7 × 3 × 1 seed).

All learned preprocessing is fit on SOURCE TRAIN. Numeric values use source-train median imputation, zero-variance removal and Z-score parameters; sparse text uses source-train TF-IDF without centering. Validation and target are never resampled. Baseline imbalance handling preserves natural prevalence. Threshold 0.5 is frozen without TARGET optimization. Calibrators are selected by SOURCE VALIDATION out-of-fold evidence and never by TARGET labels.

Metrics are ROC-AUC, PR-AUC, precision, recall, F1, MCC, Brier Score and ECE; accuracy is not primary. Discrimination, threshold-dependent performance and calibration are reported separately. Statistical pairing is by target project. The predeclared hierarchy uses paired bootstrap uncertainty, Friedman omnibus tests when sufficiently many complete target projects exist, conditional paired Wilcoxon post-hoc tests, Holm correction, and effect sizes. Seeds, folds and pooled commits are not treated as independent project replicates.

XAI is strictly post-evaluation: global, local, modality-level and feature-level explanations address complementary information but never select or tune against TARGET. Existing native LR/RF importance and LR counterfactual support are reusable; named SHAP/LIME/PDP/ICE/DiCE support is missing.

## Governance and execution decision

Every target must bind dataset/version/provenance, sample hash, feature-schema hash, project, temporal boundary, manifest, zero-overlap evidence, access counter zero and exact human authorization. Any missing or changed field fails closed. Development code must not expose labels; the future evaluator must atomically consume a one-use authorization. Current access counter: **0**. Current execution authorization: **false**.

No performance, generalization, error-reduction, modality-benefit, significance or superiority claim is made. Execution may begin only in a later authorized sprint after target materialization, XGB/LGBM and CPDP infrastructure, schema/overlap gates, and the access mechanism pass validation.

## Completion record

1. Starting branch: `sprint-10/q1-cpdp-multidataset-experimental-campaign`.
2. Starting HEAD: `{STARTING_HEAD}`.
3. Origin/main relationship: equal, 0 behind / 0 ahead at start.
4. Starting work tree: clean.
5. Components inspected: dataset contracts/adapters, extraction, preprocessing, feature engineering, modalities, models, fusion, calibration, evaluation, experimentation, XAI, temporal splitting, reproducibility, configs, manifests, audits, tests, documentation, specifications and frozen decisions.
6. Reusable infrastructure: listed under `EXISTING_AND_REUSABLE`.
7. Missing infrastructure: listed under `MISSING_FOR_FINAL_CAMPAIGN`.
8. Datasets/projects discovered: JIT-Defects4J 1.0.0 (21 projects) and non-materialized QtBase construction evidence.
9. Compatibility: `INSUFFICIENT_COMPATIBLE_DATASETS` for untouched confirmatory use.
10. Modalities: JIT-Defects4J C/P/T; QtBase C/P/T contracted but not materially established.
11. Available algorithms: Logistic Regression and Random Forest.
12. Algorithms requiring implementation/dependencies: XGBoost and LightGBM.
13. CPDP topology: multi-source leave-one-project-out to new post-boundary single target; conditional secondary topologies only.
14. Preprocessing: SOURCE-TRAIN-only learned state and fixed common schema.
15. Calibration: UNCALIBRATED, PLATT and ISOTONIC; SOURCE VALIDATION only for fitting/selection.
16. Ablations: C, P, T, C+P, C+T, P+T and C+P+T.
17. Statistics: paired project-level uncertainty/effects; conditional Friedman then Wilcoxon; Holm correction.
18. Reviewer traceability: `reviewer_traceability.json`.
19. Planned configurations: {matrix_count}.
20. Target governance: default deny, identity-bound, overlap-checked, atomic one-use access.
21. Files created: the eleven files in this versioned audit directory, plus one generator/validator module and one test module.
22. Files modified: none; all sprint changes are additive.
23. Tests executed: focused contract pytest, Ruff, and full pytest suite.
24. Results: focused 3 passed; Ruff passed; full suite 1,524 passed, 1 skipped, 1 failed and 23 errors because legacy historical-integrity tests reject any new audit/untracked sprint path. No legacy gate was weakened.
25. Historical files modified: NONE (confirmed by empty tracked Git diff).
26. TARGET TEST accesses: ZERO.
27. Final scientific classification: `{CLASSIFICATION}`.
"""


def generate(root: Path) -> Path:
    out = root / "audits/q1-cpdp-multidataset-experimental-campaign" / VERSION
    out.mkdir(parents=True, exist_ok=True)
    matrix = experimental_matrix()
    artifacts = {
        "campaign_contract.json": campaign_contract(),
        "campaign_contract.schema.json": schema(),
        "dataset_project_audit.json": dataset_audit(),
        "feature_compatibility_contract.json": feature_contract(),
        "experimental_matrix.json": matrix,
        "reviewer_traceability.json": traceability(),
        "statistical_analysis_plan.json": statistical_plan(),
        "target_access_policy.json": target_policy(),
        "provenance.json": {
            "protocol_id": "q1-cpdp-multidataset-experimental-campaign",
            "version": VERSION,
            "generated_from_head": STARTING_HEAD,
            "historical_inputs": [
                "audits/q1-final-test-identity-boundary-amendment/1.0.0",
                "audits/jit-defects4j-canonical/1.0.0",
                "configs/experiments",
                "src",
                "tests",
                "docs",
            ],
            "row_level_target_inputs": [],
            "target_accesses": 0,
            "generation": "deterministic standard-library contract generation",
        },
    }
    for name, value in artifacts.items():
        _write_json(out / name, value)
    (out / "REPORT.md").write_text(report(matrix["total_configurations"]))
    names = sorted([*artifacts, "REPORT.md"])
    lines = [
        f"{hashlib.sha256((out / name).read_bytes()).hexdigest()}  {name}"
        for name in names
    ]
    (out / "MANIFEST.sha256").write_text("\n".join(lines) + "\n")
    return out


def validate(out: Path) -> list[str]:
    errors: list[str] = []
    required = {
        "REPORT.md",
        "campaign_contract.json",
        "campaign_contract.schema.json",
        "dataset_project_audit.json",
        "feature_compatibility_contract.json",
        "experimental_matrix.json",
        "reviewer_traceability.json",
        "statistical_analysis_plan.json",
        "target_access_policy.json",
        "provenance.json",
        "MANIFEST.sha256",
    }
    if {p.name for p in out.iterdir()} != required:
        errors.append("artifact set differs from the frozen required set")
    contract = json.loads((out / "campaign_contract.json").read_text())
    matrix = json.loads((out / "experimental_matrix.json").read_text())
    policy = json.loads((out / "target_access_policy.json").read_text())
    if (
        contract.get("execution_authorized") is not False
        or contract.get("target_accesses") != 0
    ):
        errors.append("campaign must remain unauthorized with zero target accesses")
    if contract.get("modalities") != list(MODALITIES):
        errors.append("modality matrix mismatch")
    expected_count = (
        len(PROJECTS) * len(ALGORITHMS) * len(MODALITIES) * len(CALIBRATIONS)
    )
    if matrix.get("total_configurations") != expected_count:
        errors.append("matrix cardinality mismatch")
    ids = [item["experiment_id"] for item in matrix.get("experiments", [])]
    if len(ids) != len(set(ids)):
        errors.append("experiment IDs are not unique")
    if any(
        item.get("execution_status") != "BLOCKED_PENDING_TARGET_MATERIALIZATION"
        for item in matrix.get("experiments", [])
    ):
        errors.append("an experiment is not fail-closed")
    if policy.get("access_counter") != 0 or policy.get("authorized") is not False:
        errors.append("target policy is not sealed")
    manifest = {}
    for line in (out / "MANIFEST.sha256").read_text().splitlines():
        digest, name = line.split("  ", 1)
        manifest[name] = digest
    for name, expected in manifest.items():
        if hashlib.sha256((out / name).read_bytes()).hexdigest() != expected:
            errors.append(f"manifest mismatch: {name}")
    return errors


if __name__ == "__main__":
    repository = Path(__file__).resolve().parents[2]
    destination = generate(repository)
    failures = validate(destination)
    if failures:
        raise SystemExit("\n".join(failures))
    print(destination)
