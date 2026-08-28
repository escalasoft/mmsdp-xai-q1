# Sprint 10.8.2.48A — CPDP Dataset-Strategy Feasibility Audit

## Scientific classification

`BLOCKED_MISSING_DATASET_EVIDENCE`

The repository cannot yet support a complete final Q1 campaign. It verifies one 21-project benchmark with commit identity, chronology, binary labels, and common C/P/T features, but its canonical TEST was consumed in Sprint 31. It verifies no untouched target materialization and no four independent compatible dataset sources. This audit accessed no new TARGET TEST label, prediction, probability, score, or outcome; access count remains **0**.

## Dataset-strategy decision

Strategy C (hybrid) is preferred if Phase 1 establishes at least one genuinely independent compatible source. Strategy A plus D is the executable fallback: temporal WPDP and pooled-source leave-one-project-out CPDP across distinct JIT-Defects4J project domains, described honestly as within-benchmark evidence. Strategy B is blocked. Pooled training is valid only with the complete target excluded and is not presumed superior.

The provisional 10-project panel is: ant-ivy, commons-bcel, commons-collections, commons-jcs, commons-lang, commons-math, commons-net, giraph, opennlp, parquet-mr. It was chosen without performance results: each project has historical aggregate evidence of at least five positives in every chronological partition. These historical counts do **not** make the consumed TEST reusable and do not establish future target eligibility. Every project must pass new post-boundary class-support, temporal-range, identity, missingness, schema, provenance and overlap gates.

## Minimum sufficient campaign

The prospective minimum is **720 cells**: WPDP and pooled LOPO CPDP over 10 eligible targets; four named algorithms; all seven modalities uncalibrated; and Platt/isotonic additions for C+P+T. This directly tests modality contribution while focusing calibration analysis on the complete proposal. It is more defensible than four targets (whose two-sided exact Wilcoxon minimum p-value is 0.125) and avoids Sprint 48's unjustified calibration multiplier over every ablation. PR-AUC is primary and MCC receives emphasis; ROC-AUC, precision, recall, F1, Brier and ECE remain mandatory.

## Leakage and governance

All learned preprocessing is SOURCE-TRAIN-only. Independent TARGET Z-scoring is transductive adaptation and prohibited in strict inductive CPDP. Calibration and thresholds use source validation/nested source-only predictions. A separately declared label-free transductive sensitivity variant is permissible only as secondary evidence. Historical TEST is excluded from SOURCE and TARGET.

## Readiness

LR/RF, temporal split and core C/P/T/calibration/metric primitives exist. XGBoost, LightGBM, generic CPDP/schema alignment, campaign statistics, named SHAP/LIME/PDP/ICE/DiCE adapters, reproducible declared dependencies, and atomic target authorization remain incomplete. Existing XAI support is partial and must be applied only to prospectively frozen models.

## Execution roadmap

Phase 1 closes dataset/materialization, compatibility, algorithm, dependency and governance blockers. Phase 2 executes the frozen full matrix once. Phase 3 performs the predeclared statistics, calibration analysis, XAI and paper assembly. Paper table and figure schemas are frozen in `paper_output_schemas.json`; reviewer mapping is complete in `reviewer_traceability.json`.

No final experiment or significance test was run and no performance or superiority claim is made.
