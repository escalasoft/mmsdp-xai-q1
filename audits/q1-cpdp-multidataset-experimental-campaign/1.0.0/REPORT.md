# Sprint 10.8.2.48 — CPDP Multi-Dataset Experimental Campaign Contract

## Final scientific classification

`BLOCKED_MISSING_COMPATIBLE_DATASETS`

The repository supports a common C/P/T schema across 21 projects in one historical JIT-Defects4J 1.0.0 materialization, but its only canonical TEST boundary was consumed in Sprint 31. QtBase has construction contracts but no compatible audited materialization. Thus four untouched compatible target datasets/projects cannot currently be established. No final experiment was run, no historical TEST prediction/outcome artifact was opened, and target access remained zero.

## Starting state and preserved evidence

- Branch: `sprint-10/q1-cpdp-multidataset-experimental-campaign`
- HEAD: `90acf442fe21e3becd8cf7cff02eaa75f8c97301`
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

The canonical JIT-Defects4J TEST identified by temporal boundary `d1b4448e22a1dba4292b9cf8969ba77db0cf9a10ef66dfddf98642cb5dc078a7` and every associated Sprint 31 prediction/outcome artifact.

## Dataset and compatibility conclusion

JIT-Defects4J has 27,319 commit observations (2,332 positive; 24,987 nominal negative; prevalence 0.08536) across 21 named projects, with chronological timestamps and C/P/T predictors. These aggregate and project-level facts come from the committed canonical audit, not reopened TEST payloads. QtBase has a pinned repository snapshot and construction policies, but observations, class distribution, final label evidence, and compatible materialized schema are unavailable. The correct repository-evidence classification is `INSUFFICIENT_COMPATIBLE_DATASETS`.

The reusable common schema is six CODE change-count features, four ancestor-only PROCESS features, and source-train-fitted TF-IDF over raw commit messages. Names alone do not establish compatibility; prediction-time availability, units, aggregation, label semantics and provenance must pass. Label-derived, future, post-event, bug-keyword/linkage, and full-dataset-fitted predictors are prohibited.

## Frozen campaign design

The primary topology is multi-source-to-single-target leave-one-project-out: historical TRAIN/VALIDATION from 20 non-target projects develop the model, while a newly materialized post-boundary extension of the held-out project is FINAL TARGET TEST. Historical TEST rows are excluded everywhere. Single-source CPDP and leave-one-dataset-out are conditional secondary analyses only if materialization makes them feasible.

The full ablation matrix is C, P, T, C+P, C+T, P+T and C+P+T for LR, RF, XGBoost and LightGBM, each under UNCALIBRATED, PLATT and ISOTONIC states. Multimodal campaign cells use source-trained feature concatenation; historical CT_equal remains a historical candidate, not a selected new winner. The prospective matrix contains **1764** immutable, blocked configurations (21 × 4 × 7 × 3 × 1 seed).

All learned preprocessing is fit on SOURCE TRAIN. Numeric values use source-train median imputation, zero-variance removal and Z-score parameters; sparse text uses source-train TF-IDF without centering. Validation and target are never resampled. Baseline imbalance handling preserves natural prevalence. Threshold 0.5 is frozen without TARGET optimization. Calibrators are selected by SOURCE VALIDATION out-of-fold evidence and never by TARGET labels.

Metrics are ROC-AUC, PR-AUC, precision, recall, F1, MCC, Brier Score and ECE; accuracy is not primary. Discrimination, threshold-dependent performance and calibration are reported separately. Statistical pairing is by target project. The predeclared hierarchy uses paired bootstrap uncertainty, Friedman omnibus tests when sufficiently many complete target projects exist, conditional paired Wilcoxon post-hoc tests, Holm correction, and effect sizes. Seeds, folds and pooled commits are not treated as independent project replicates.

XAI is strictly post-evaluation: global, local, modality-level and feature-level explanations address complementary information but never select or tune against TARGET. Existing native LR/RF importance and LR counterfactual support are reusable; named SHAP/LIME/PDP/ICE/DiCE support is missing.

## Governance and execution decision

Every target must bind dataset/version/provenance, sample hash, feature-schema hash, project, temporal boundary, manifest, zero-overlap evidence, access counter zero and exact human authorization. Any missing or changed field fails closed. Development code must not expose labels; the future evaluator must atomically consume a one-use authorization. Current access counter: **0**. Current execution authorization: **false**.

No performance, generalization, error-reduction, modality-benefit, significance or superiority claim is made. Execution may begin only in a later authorized sprint after target materialization, XGB/LGBM and CPDP infrastructure, schema/overlap gates, and the access mechanism pass validation.

## Completion record

1. Starting branch: `sprint-10/q1-cpdp-multidataset-experimental-campaign`.
2. Starting HEAD: `90acf442fe21e3becd8cf7cff02eaa75f8c97301`.
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
19. Planned configurations: 1764.
20. Target governance: default deny, identity-bound, overlap-checked, atomic one-use access.
21. Files created: the eleven files in this versioned audit directory, plus one generator/validator module and one test module.
22. Files modified: none; all sprint changes are additive.
23. Tests executed: focused contract pytest, Ruff, and full pytest suite.
24. Results: focused 3 passed; Ruff passed; full suite 1,524 passed, 1 skipped, 1 failed and 23 errors because legacy historical-integrity tests reject any new audit/untracked sprint path. No legacy gate was weakened.
25. Historical files modified: NONE (confirmed by empty tracked Git diff).
26. TARGET TEST accesses: ZERO.
27. Final scientific classification: `BLOCKED_MISSING_COMPATIBLE_DATASETS`.
