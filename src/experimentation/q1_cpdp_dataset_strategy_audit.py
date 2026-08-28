# ruff: noqa: E501
"""Deterministic, non-executing Sprint 10.8.2.48A feasibility audit.

The generator consumes no datasets, labels, predictions, probabilities, scores, or
model artifacts.  Its inputs are frozen repository-level metadata transcribed from
the canonical audits identified in ``evidence_sources()``.
"""

from __future__ import annotations

import hashlib
import json
from itertools import product
from pathlib import Path
from typing import Any

VERSION = "1.0.0"
SPRINT = "10.8.2.48A"
CLASSIFICATION = "BLOCKED_MISSING_DATASET_EVIDENCE"
STARTING_HEAD = "5420b425ab225b35c3e109503e4f1bca065118d4"
AUDIT_ID = "q1-cpdp-dataset-strategy-feasibility-audit"
ALGORITHMS = ("LR", "RF", "XGBOOST", "LIGHTGBM")
MODALITIES = ("C", "P", "T", "C+P", "C+T", "P+T", "C+P+T")
CALIBRATIONS = ("UNCALIBRATED", "PLATT", "ISOTONIC")
PRIMARY_PROJECTS = (
    "ant-ivy", "commons-bcel", "commons-collections", "commons-jcs",
    "commons-lang", "commons-math", "commons-net", "giraph", "opennlp",
    "parquet-mr",
)
PROJECT_COUNTS = {
    "ant-ivy": (1771, 332), "commons-bcel": (825, 60),
    "commons-beanutils": (611, 37), "commons-codec": (761, 36),
    "commons-collections": (1823, 50), "commons-compress": (1630, 178),
    "commons-configuration": (1838, 155), "commons-dbcp": (1037, 58),
    "commons-digester": (1079, 19), "commons-io": (1142, 73),
    "commons-jcs": (831, 88), "commons-lang": (2969, 146),
    "commons-math": (4026, 335), "commons-net": (1121, 117),
    "commons-scxml": (544, 47), "commons-validator": (598, 36),
    "commons-vfs": (1110, 114), "giraph": (844, 163),
    "gora": (553, 39), "opennlp": (1086, 91), "parquet-mr": (1120, 158),
}
SPLIT_POSITIVES = {
    "ant-ivy": (293, 24, 15), "commons-bcel": (44, 8, 8),
    "commons-beanutils": (36, 1, 0), "commons-codec": (29, 6, 1),
    "commons-collections": (32, 7, 11), "commons-compress": (155, 19, 4),
    "commons-configuration": (143, 9, 3), "commons-dbcp": (56, 2, 0),
    "commons-digester": (7, 5, 7), "commons-io": (69, 3, 1),
    "commons-jcs": (64, 12, 12), "commons-lang": (109, 29, 8),
    "commons-math": (252, 59, 24), "commons-net": (102, 10, 5),
    "commons-scxml": (37, 2, 8), "commons-validator": (26, 6, 4),
    "commons-vfs": (105, 6, 3), "giraph": (140, 12, 11),
    "gora": (39, 0, 0), "opennlp": (75, 8, 8),
    "parquet-mr": (99, 32, 27),
}


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _write(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def evidence_sources() -> dict[str, Any]:
    return {
        "scope": "committed aggregate metadata and source/contracts only",
        "prohibited_payloads_opened": [],
        "target_test_access_count": 0,
        "sources": [
            {"path": "audits/jit-defects4j/1.0.0/audit.json", "use": "provenance, aggregate project inventory and label semantics"},
            {"path": "audits/jit-defects4j-canonical/1.0.0/audit.json", "use": "aggregate counts, missingness, schemas and temporal policy"},
            {"path": "audits/jit-defects4j-one-shot-test/1.0.0/REPORT.md", "use": "historical Sprint 31 TEST-consumption fact only"},
            {"path": "audits/q1-final-test-identity-boundary-amendment/1.0.0/identity_boundary_amendment.json", "use": "NO_VERIFIABLE_UNTOUCHED_FINAL_TEST governance conclusion"},
            {"path": "audits/q1-cpdp-multidataset-experimental-campaign/1.0.0", "use": "Sprint 48 contract and declared gaps"},
            {"path": "configs/qt_*.json and src/{extraction,dataset}/qt_*.py", "use": "Qt construction contracts; no materialized observations"},
            {"path": "src/{preprocessing,models,calibration,experimentation,explainability}", "use": "implementation readiness"},
            {"path": "pyproject.toml", "use": "declared dependency readiness"},
        ],
        "historical_integrity": "historical artifacts are read-only and remain authoritative",
    }


def candidate_report() -> dict[str, Any]:
    projects = []
    for name, (observations, positives) in PROJECT_COUNTS.items():
        projects.append({
            "dataset": "JIT-Defects4J", "dataset_version": "1.0.0",
            "project": name, "observations": observations, "positive": positives,
            "nominal_negative": observations - positives,
            "prevalence": positives / observations,
            "historical_train_validation_test_positive": list(SPLIT_POSITIVES[name]),
            "identity": ["project", "commit_hash"],
            "temporal_field": "git_committer_timestamp",
            "temporal_range": None,
            "modalities": ["C", "P", "T"],
            "missingness": "aggregate audit reports 16 missing commit messages benchmark-wide; per-project missingness unavailable",
            "duplicate_status": "benchmark-wide identity uniqueness passed",
            "schema_compatibility": "common within JIT-Defects4J; external compatibility unverified",
            "historical_test_consumed": True,
            "future_source": "historical TRAIN/VALIDATION only; exclude historical TEST",
            "future_untouched_target": "not currently available; requires new post-boundary materialization",
            "primary_panel_candidate": name in PRIMARY_PROJECTS,
            "selection_basis": "historical class support in every chronological partition (>=5 positives)" if name in PRIMARY_PROJECTS else "not in minimum panel because one historical partition has <5 positives",
        })
    return {
        "dataset_sources_verified": 1,
        "independent_external_sources_verified": 0,
        "benchmark_projects_verified": len(projects),
        "benchmark_total": {"observations": 27319, "positive": 2332, "nominal_negative": 24987, "prevalence": 2332 / 27319},
        "label": "commit-level binary is_defect_prone; negatives are closed-world nominal negatives",
        "provenance": "jacknichao/JIT-Fine data.zip plus immutable upstream repository snapshots",
        "feature_contract": {"C": ["file_changes", "files_added", "files_deleted", "files_modified", "files_other"], "P": ["parent_count", "is_merge_commit", "has_prior_history", "prior_project_commit_count"], "T": ["raw_commit_message -> SOURCE-TRAIN-fitted TF-IDF"]},
        "projects": projects,
        "other_candidate": {"dataset": "QtBase", "project": "qtbase", "version": None, "observations": None, "positive": None, "nominal_negative": None, "prevalence": None, "temporal_range": None, "modalities": "contracted C/P/T but not materially verified", "status": "NOT_MATERIALIZED", "source_or_target_eligibility": "UNVERIFIED"},
        "preferred_panel": list(PRIMARY_PROJECTS),
        "panel_is_final": False,
        "requalification": "Every project needs new post-boundary counts, class support, temporal range, hashes, missingness and zero-overlap proof before freezing; substitute by the same criteria, never performance.",
        "scientific_limitation": "Projects are distinct domains inside one benchmark, not four independent dataset sources.",
    }


def strategy_assessment() -> dict[str, Any]:
    return {"recommended": "C_HYBRID_CONDITIONAL_ON_EXTERNAL_COMPATIBILITY; A_PLUS_D_AS_EXECUTABLE_FALLBACK",
        "strategies": [
            {"id": "A", "name": "multi-project JIT-Defects4J", "WPDP": "feasible only after new post-boundary targets", "CPDP": "feasible as cross-project within-benchmark generalization", "strength": "controlled common provenance/schema", "limitation": "not independent-dataset external validity; consumed historical TEST", "status": "CONDITIONALLY_FEASIBLE"},
            {"id": "B", "name": "four independent sources", "strength": "strongest source-level external validity", "limitation": "repository verifies no four commit-level binary C/P/T sources; QtBase is unmaterialized", "status": "BLOCKED_MISSING_EVIDENCE"},
            {"id": "C", "name": "hybrid", "strength": "combines controlled within-benchmark replication with external validity", "limitation": "external compatible target absent", "status": "PREFERRED_IF_PHASE_1_CLOSES_EXTERNAL_DATA"},
            {"id": "D", "name": "pooled source training", "strength": "valid LOPO CPDP when target is strictly excluded", "limitation": "pooling is a hypothesis and may mask project heterogeneity", "status": "CONDITIONALLY_FEASIBLE"},
        ],
        "decision_rule": "Use hybrid if at least one independent C/P/T source passes the same immutable contract; otherwise report Strategy A+D honestly as within-benchmark multi-project evidence, without claiming independent-dataset external validity.",
    }


def preprocessing_policy() -> dict[str, Any]:
    return {"primary_protocol": "STRICT_INDUCTIVE_CPDP", "fit_scope": "SOURCE_TRAIN_ONLY",
        "steps": {
            "imputation": "source-train median for numeric; source-train explicit missing/unknown token for text/categorical",
            "normalization": "source-train mean/std, applied unchanged; zero variance removed from source train",
            "target_zscore": "PROHIBITED in primary protocol: TARGET mean/std is transductive covariate adaptation even without labels",
            "categorical_encoding": "source-train fitted with frozen unknown category",
            "feature_selection": "source-train/validation only; freeze before target access",
            "dimensionality_reduction": "source-train fitted only",
            "text": "source-train vocabulary and IDF; sparse and uncentered",
            "resampling": "source train only; never validation or target",
            "class_weighting": "derive from source train only",
            "calibration": "fit using source validation or nested source-only out-of-fold predictions",
            "threshold": "predeclare 0.5 and any operational threshold from source validation only",
        },
        "transductive_secondary": "A separately labelled, preregistered sensitivity analysis may fit unsupervised target covariate normalization; it must never use target labels or be conflated with strict inductive CPDP."}


def readiness() -> dict[str, Any]:
    return {"datasets": "BLOCKED: untouched compatible target materializations absent",
        "algorithms": {"LR": "AVAILABLE", "RF": "AVAILABLE", "XGBOOST": "MISSING dependency, adapter and frozen search space", "LIGHTGBM": "MISSING dependency, adapter and frozen search space"},
        "modalities": "C/P/T and all seven combinations are contract-ready for JIT-Defects4J; cross-source semantics unverified",
        "calibration": "Platt/isotonic and Brier/ECE primitives exist; source-only campaign orchestration and minimum-support gates required",
        "statistics": "plan is ready; campaign-wide executor absent",
        "xai": "native LR/RF global importance, LR local/counterfactual boundaries exist; SHAP/LIME/PDP/ICE/DiCE and XGB/LGBM adapters are absent",
        "cpdp": "generic pooled-source/held-out-target orchestrator and schema mapper absent",
        "governance": "atomic identity-bound one-use target authorization/access ledger absent",
        "dependencies": "pyproject declares no runtime dependencies; reproducible lock/declarations for sklearn/numpy/scipy/XGBoost/LightGBM/XAI stack are required"}


def matrix() -> dict[str, Any]:
    cells = []
    for design, target, algorithm, modality in product(("WPDP", "LOPO_CPDP"), PRIMARY_PROJECTS, ALGORITHMS, MODALITIES):
        core = {"design": design, "target": target, "algorithm": algorithm, "modality": modality, "calibration": "UNCALIBRATED"}
        cells.append({**core, "id": _digest(core)[:20], "status": "BLOCKED"})
    for design, target, algorithm, calibration in product(("WPDP", "LOPO_CPDP"), PRIMARY_PROJECTS, ALGORITHMS, ("PLATT", "ISOTONIC")):
        core = {"design": design, "target": target, "algorithm": algorithm, "modality": "C+P+T", "calibration": calibration}
        cells.append({**core, "id": _digest(core)[:20], "status": "BLOCKED"})
    return {"total": len(cells), "derivation": "2 designs x 10 targets x [4 algorithms x (7 uncalibrated modalities + 2 additional C+P+T calibrations)] = 720",
        "why_sufficient": "All algorithm/modality contrasts are paired uncalibrated; calibration is tested on the proposed complete multimodal model where probability quality is substantively claimed. Ten project units support project-level paired inference better than the reviewer-minimum four and avoid pseudo-replication.",
        "why_not_1764": "Calibration cannot change ranking metrics for monotone Platt/isotonic mappings and need not multiply every ablation; the 21-target topology is unavailable and was declarative, not a necessity argument.",
        "conditional_expansion": "Use every Phase-1-eligible target and independently compatible external source; matrix size becomes 72 x eligible targets (36 WPDP + 36 LOPO). Pairwise CPDP is diagnostic only, not mandatory.", "cells": cells}


def statistical_plan() -> dict[str, Any]:
    return {"primary_metric": "PR-AUC / Average Precision", "key_secondary": "MCC", "other_metrics": ["ROC-AUC", "Precision", "Recall", "F1", "Brier Score", "ECE"],
        "pairing_unit": "same target project, same frozen target samples, same design; one prespecified aggregate score per method and target",
        "not_replicates": ["commits", "folds", "seeds", "calibration states", "configuration rows"],
        "uncertainty": "project-stratified paired bootstrap confidence intervals for median/mean paired differences; per-project bootstrap is descriptive only",
        "omnibus": "Friedman across >=10 complete non-degenerate target projects for prespecified multi-method families",
        "post_hoc": "after omnibus rejection, paired two-sided Wilcoxon signed-rank with Pratt zero handling",
        "multiplicity": "Holm correction within each predeclared RQ x design x metric family",
        "effects": ["paired median difference", "Hodges-Lehmann shift", "rank-biserial correlation", "absolute Brier/ECE difference"],
        "four_project_warning": "With n=4 nonzero pairs, the minimum two-sided exact Wilcoxon p-value is 0.125; four projects alone cannot deliver conventional 0.05 Wilcoxon significance.",
        "degeneracy": "Undefined metrics remain NA; never impute. Report complete-case target counts per contrast.",
        "claims": "Statistical, practical, discrimination and calibration conclusions remain separate."}


def reviewer_traceability() -> dict[str, Any]:
    rows = [
        ("A", "statistical significance", "paired target-project scores", "Table 6", "Friedman; gated Wilcoxon; Holm; CIs/effects"),
        ("B/C", "add and compare four named algorithms", "LR/RF/XGBoost/LightGBM frozen implementations", "Tables 2-5", "paired algorithm contrasts"),
        ("D", "explain every dataset individually", "identity/provenance/count/prevalence/time/label/CPT/missingness", "Table 1", "descriptive audit"),
        ("E", "evaluate four projects individually", ">=10 preferred targets, never fewer than four eligible", "Tables 2-3", "per-project rows"),
        ("F", "generalization and stability", "temporal WPDP plus held-out-project LOPO CPDP", "Tables 2-3; Figures 2-3", "project-level distributions/CIs"),
        ("G", "audit pooled integration", "pooled non-target SOURCE vs individual-source diagnostic", "Table 3", "paired target contrasts; no assumed superiority"),
        ("H1", "does multimodality reduce errors", "fixed source-selected threshold confusion deltas", "Table 4", "paired FN/FP, recall/precision/MCC"),
        ("H2", "does it improve generalization", "C+P+T vs C/P/T and bimodal LOPO", "Tables 3-4", "PR-AUC/MCC paired effects"),
        ("H3", "complementary information", "seven-level ablation plus frozen-model XAI", "Table 4; Figures 5-6", "incremental effects and explanation concordance"),
        ("H4/I", "practical implication separate from performance", "recall at comparable precision, FNR, ranking/inspection effort, calibration risk tiers", "dedicated practical-utility columns/text", "no cost claim absent cost model"),
        ("Calibration", "effect and probability reliability", "C+P+T uncalibrated/Platt/isotonic", "Table 5; Figure 4", "Brier/ECE/reliability curves; source-only fit"),
        ("XAI", "interpret contribution", "post-evaluation frozen models only", "Figures 5-6", "SHAP global/local, LIME local, appropriate PDP/ICE, feasible DiCE"),
        ("Integrity", "no reused TEST as untouched", "identity-bound new post-boundary targets", "manifest and Table 1", "zero overlap and atomic access ledger"),
    ]
    return {"complete": True, "rows": [{"requirement": a, "question": b, "future_experiment": c, "paper_artifact": d, "analysis": e} for a,b,c,d,e in rows]}


def paper_schemas() -> dict[str, Any]:
    return {"tables": {
        "TABLE_1": ["dataset", "project", "version", "source", "provenance_hash", "time_start", "time_end", "n", "positive", "negative", "prevalence", "label_definition", "C_features", "P_features", "T_representation", "missingness", "duplicates", "prior_test_status"],
        "TABLE_2": ["project", "split_boundaries", "algorithm", "modality", "calibration", "metrics", "CI"],
        "TABLE_3": ["source_projects", "target_project", "topology", "algorithm", "modality", "calibration", "metrics", "CI"],
        "TABLE_4": ["design", "target", "algorithm", "contrast", "metric_delta", "CI", "effect_size"],
        "TABLE_5": ["design", "target", "algorithm", "calibration", "Brier", "ECE", "bin_counts", "calibration_slope", "calibration_intercept"],
        "TABLE_6": ["RQ", "design", "metric", "methods", "n_projects", "test", "statistic", "raw_p", "Holm_p", "effect", "CI"],
        "TABLE_7": ["reviewer_requirement", "experiment", "metric_or_analysis", "artifact", "answer_status"]},
        "figures": {"FIGURE_1": "leakage-safe WPDP/LOPO protocol", "FIGURE_2": "paired performance distributions", "FIGURE_3": "target-wise CPDP generalization", "FIGURE_4": "reliability diagrams with counts", "FIGURE_5": "global SHAP/modality contributions for frozen models", "FIGURE_6": "preselected representative local SHAP/LIME explanation"},
        "population_policy": "Schemas only; Phase 2/3 populate results. No prospective result field contains a value."}


def roadmap() -> dict[str, Any]:
    return {"phases": [
        {"phase": 1, "name": "dataset materialization and compatibility closure", "outputs": ["frozen dataset/project list", "source/target identities", "temporal boundaries", "sample/label/feature hashes", "counts/missingness/overlap", "XGB/LGBM adapters and lock", "CPDP/schema/governance gates"], "exit": "at least 10 eligible post-boundary target projects and preferably >=1 independent source; all four algorithms and access gates pass; otherwise reclassify scope before labels are exposed"},
        {"phase": 2, "name": "frozen full experimental execution", "outputs": ["720-cell minimum matrix or deterministic eligible-target expansion", "Tables 2-5 raw schemas", "Figures 2-4 inputs", "immutable execution ledger"], "exit": "one authorized run with no target-driven changes"},
        {"phase": 3, "name": "statistics, calibration, XAI and paper evidence", "outputs": ["Table 6 tests/effects/CIs", "Table 7 reviewer answers", "Figures 1-6", "practical-utility interpretation", "paper-ready evidence package"], "exit": "all claims trace to frozen evidence and limitations"}],
        "pre_execution_freeze": ["datasets/projects", "source/target identities", "temporal/sample boundaries", "label/feature contracts", "algorithms/hyperparameter spaces", "modalities", "calibration/thresholds", "metrics/tests", "target-access and XAI policies", "table/figure schemas"]}


def campaign_blueprint() -> dict[str, Any]:
    return {"classification": CLASSIFICATION, "execution_authorized": False, "target_test_access_count": 0,
        "starting_state": {"branch": "sprint-10/q1-cpdp-dataset-strategy-feasibility-audit", "head": STARTING_HEAD, "origin_main": STARTING_HEAD, "clean": True},
        "recommended_strategy": strategy_assessment()["recommended"], "minimum_projects": 10, "reviewer_floor": 4,
        "WPDP": "For each eligible project, chronological TRAIN -> VALIDATION -> new post-boundary TEST; tune/fit/calibrate on TRAIN/VALIDATION only; no shuffle.",
        "CPDP": "Primary pooled leave-one-project-out: all non-target projects are SOURCE, held-out project is unseen TARGET; target observations never enter training, fitting, calibration or threshold selection. Pairwise CPDP is optional diagnostic.",
        "pooled_policy": "Pooled SOURCE training is valid in addition to WPDP and optional individual-source CPDP, but superiority is an empirical result.",
        "algorithms": list(ALGORITHMS), "modalities": list(MODALITIES), "calibrations": list(CALIBRATIONS),
        "xai_policy": "Run only after models/configurations are frozen independently of target outcomes. Use SHAP global/local, LIME local, PDP/ICE only for interpretable low-dimensional features with dependence caveats, and DiCE only where feature actionability/constraints are defensible.",
        "practical_utility": "Translate effects to recall at comparable precision, false-negative rate, inspection/ranking effort, and calibrated prioritization; make no causal/economic claim without a cost model.",
        "test_policy": "Historical Sprint 31 TEST remains historical only. New targets require exact identity, zero overlap, label-sealed development, human authorization and an atomic one-use ledger.",
        "blockers": ["new post-boundary target materializations and temporal ranges/class support", "four independent C/P/T sources (for Strategy B; only one benchmark is verified)", "QtBase compatible materialization", "XGBoost/LightGBM dependencies/adapters/search spaces", "generic CPDP orchestrator/schema mapper", "campaign statistics and named XAI integrations", "atomic target access enforcement and reproducible dependency lock"]}


def _report() -> str:
    return f"""# Sprint {SPRINT} — CPDP Dataset-Strategy Feasibility Audit

## Scientific classification

`{CLASSIFICATION}`

The repository cannot yet support a complete final Q1 campaign. It verifies one 21-project benchmark with commit identity, chronology, binary labels, and common C/P/T features, but its canonical TEST was consumed in Sprint 31. It verifies no untouched target materialization and no four independent compatible dataset sources. This audit accessed no new TARGET TEST label, prediction, probability, score, or outcome; access count remains **0**.

## Dataset-strategy decision

Strategy C (hybrid) is preferred if Phase 1 establishes at least one genuinely independent compatible source. Strategy A plus D is the executable fallback: temporal WPDP and pooled-source leave-one-project-out CPDP across distinct JIT-Defects4J project domains, described honestly as within-benchmark evidence. Strategy B is blocked. Pooled training is valid only with the complete target excluded and is not presumed superior.

The provisional 10-project panel is: {', '.join(PRIMARY_PROJECTS)}. It was chosen without performance results: each project has historical aggregate evidence of at least five positives in every chronological partition. These historical counts do **not** make the consumed TEST reusable and do not establish future target eligibility. Every project must pass new post-boundary class-support, temporal-range, identity, missingness, schema, provenance and overlap gates.

## Minimum sufficient campaign

The prospective minimum is **720 cells**: WPDP and pooled LOPO CPDP over 10 eligible targets; four named algorithms; all seven modalities uncalibrated; and Platt/isotonic additions for C+P+T. This directly tests modality contribution while focusing calibration analysis on the complete proposal. It is more defensible than four targets (whose two-sided exact Wilcoxon minimum p-value is 0.125) and avoids Sprint 48's unjustified calibration multiplier over every ablation. PR-AUC is primary and MCC receives emphasis; ROC-AUC, precision, recall, F1, Brier and ECE remain mandatory.

## Leakage and governance

All learned preprocessing is SOURCE-TRAIN-only. Independent TARGET Z-scoring is transductive adaptation and prohibited in strict inductive CPDP. Calibration and thresholds use source validation/nested source-only predictions. A separately declared label-free transductive sensitivity variant is permissible only as secondary evidence. Historical TEST is excluded from SOURCE and TARGET.

## Readiness

LR/RF, temporal split and core C/P/T/calibration/metric primitives exist. XGBoost, LightGBM, generic CPDP/schema alignment, campaign statistics, named SHAP/LIME/PDP/ICE/DiCE adapters, reproducible declared dependencies, and atomic target authorization remain incomplete. Existing XAI support is partial and must be applied only to prospectively frozen models.

## Execution roadmap

Phase 1 closes dataset/materialization, compatibility, algorithm, dependency and governance blockers. Phase 2 executes the frozen full matrix once. Phase 3 performs the predeclared statistics, calibration analysis, XAI and paper assembly. Paper table and figure schemas are frozen in `paper_output_schemas.json`; reviewer mapping is complete in `reviewer_traceability.json`.

No final experiment or significance test was run and no performance or superiority claim is made.
"""


def generate(output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts = {"campaign_blueprint.json": campaign_blueprint(), "dataset_candidate_report.json": candidate_report(), "strategy_assessment.json": strategy_assessment(), "preprocessing_policy.json": preprocessing_policy(), "implementation_readiness.json": readiness(), "experimental_matrix.json": matrix(), "statistical_analysis_plan.json": statistical_plan(), "reviewer_traceability.json": reviewer_traceability(), "paper_output_schemas.json": paper_schemas(), "execution_roadmap.json": roadmap(), "evidence_inventory.json": evidence_sources()}
    for name, value in artifacts.items():
        _write(output_dir / name, value)
    (output_dir / "REPORT.md").write_text(_report())
    manifest_files = sorted([*artifacts, "REPORT.md"])
    lines = [f"{hashlib.sha256((output_dir / name).read_bytes()).hexdigest()}  {name}" for name in manifest_files]
    (output_dir / "MANIFEST.sha256").write_text("\n".join(lines) + "\n")
    return output_dir


def validate(output_dir: Path) -> list[str]:
    errors = []
    blueprint = json.loads((output_dir / "campaign_blueprint.json").read_text())
    planned = json.loads((output_dir / "experimental_matrix.json").read_text())
    evidence = json.loads((output_dir / "evidence_inventory.json").read_text())
    if blueprint["execution_authorized"] or blueprint["target_test_access_count"] != 0:
        errors.append("campaign must remain unauthorized with zero target accesses")
    if planned["total"] != 720 or len(planned["cells"]) != 720:
        errors.append("minimum matrix must contain exactly 720 unique planned cells")
    if len({cell["id"] for cell in planned["cells"]}) != 720 or any(cell["status"] != "BLOCKED" for cell in planned["cells"]):
        errors.append("matrix cells must be unique and blocked")
    if evidence["prohibited_payloads_opened"] or evidence["target_test_access_count"] != 0:
        errors.append("prohibited target evidence access recorded")
    for line in (output_dir / "MANIFEST.sha256").read_text().splitlines():
        expected, name = line.split("  ", 1)
        if hashlib.sha256((output_dir / name).read_bytes()).hexdigest() != expected:
            errors.append(f"manifest mismatch: {name}")
    return errors
