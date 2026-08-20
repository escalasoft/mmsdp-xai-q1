# Sprint 10.8.2.30 — Final-refit/calibration compatibility audit

## 1. Sprint purpose

This independent audit determines whether a complete JIT-Defects4J CODE+TEXT fitting and calibration procedure can be frozen before one-shot temporal TEST evaluation. It is not a performance or model-selection sprint.

## 2. Repository/branch state

The audit began on `sprint-10/jit-defects4j-final-refit-audit`, at HEAD `7fb3aa9c9bc61b674df97b5f5d394a68bcbef8ef`, equal to `origin/main`. There were no tracked changes; only intentionally ignored generated/cache artifacts. No checkout, commit, push, merge, PR, or branch deletion occurred.

## 3. Frozen scientific ancestry

Repository artifacts, rather than remembered values, establish the following identities: dataset `e509995...fa519`; manifest `95b1a36...81ef1`; temporal boundary `d1b4448...078a7`; adapters `9c22de3...3d2c`; controlled baselines `535459c...6268b`; fusion `84d08da...e4cd`; robustness `384e640...1c618`; architecture `0f0547c...c47d`; calibration protocol `4523351...8f35895`; and calibration execution `578283a...2aa3`.

## 4. Central calibration-compatibility problem

Sprint 10.8.2.29 proposed fitting isotonic regression on probabilities from the TRAIN-fitted base system but applying it to probabilities from a newly TRAIN+VALIDATION-refitted system. Equal architecture and hyperparameters do not make separately fitted estimators the same score generator. The probability scale may change, so direct compatibility is not established.

## 5. Exact current architecture

CODE is `jit-10.8.2.25-code-rf-2`: six ordered structural features, TRAIN-fitted `StandardScaler`, and `RandomForestClassifier(n_estimators=100, criterion=gini, max_depth=12, min_samples_split=2, min_samples_leaf=5, max_features=sqrt, bootstrap=true, class_weight=null, random_state=0)`. Missingness is handled by the already materialized numeric contract. Class order is `[0,1]`; column 1 is positive probability.

TEXT is `jit-10.8.2.25-text-lr-2`: lowercase deterministic token regex `(?u)\b[^\W_]{2,}\b`, unigram TF-IDF, maximum 5,000 features, minimum TRAIN document frequency 2, vocabulary ordered by descending TRAIN document frequency then token, TRAIN-only vocabulary/DF/IDF, sublinear TF, smooth IDF and L2 normalization, no declared stop-word or `max_df` filtering, missing message token `<MISSING_COMMIT_MESSAGE>`, and liblinear LR (`C=1`, intercept, `tol=0.0001`, `max_iter=2000`, no class weight, random_state 0). PROCESS is excluded.

Fusion is exactly `p_raw = 0.5*p_CODE + 0.5*p_TEXT`; there is no learned weight, stacking, or meta-model.

## 6. Sprint 10.8.2.29 calibration provenance

The frozen TRAIN-fitted CODE+TEXT model generated raw probabilities for canonical VALIDATION. Five-fold stratified cross-fitting over those fixed probabilities selected ISOTONIC by the predeclared lowest-Brier rule. Verified OOF metrics were Brier `0.056083223875184815`, ECE `0.005046090270136952`, ROC-AUC `0.7338885761389682`, and AP `0.17204383535872067`. Discrimination was diagnostic, not selection evidence.

## 7. Candidate procedures considered

- **A — no base refit (selected):** retain the exact TRAIN-fitted preprocessing and base estimators; fit one isotonic mapping on all 4,086 canonical VALIDATION raw scores and labels.
- **B — development cross-fit plus final refit (rejected):** leakage-free OOF scores are feasible when all preprocessing is fold-local, but fold estimators remain different fitted score generators from the final full-development estimator. Compatibility is a methodological approximation, not verified equivalence, and it changes the prior declaration.
- **Existing 10.8.2.29 hybrid (rejected):** directly combines a TRAIN-score calibrator with TRAIN+VALIDATION final scores and therefore fails compatibility.

## 8. Leakage analysis

The selected procedure consumes frozen TRAIN adapters for base fitting and frozen VALIDATION adapters/labels only for calibration. Identity overlap is zero. Target, fixing/SZZ/blame, future metadata, issue linkage, split and project identifiers are absent from predictors. TEST vocabulary, IDF, scaling, features, labels, scores, prevalence, calibration, and diagnostics are not accessed. The development loader rejects `partition("test")`.

## 9. Calibration-score compatibility analysis

**Empirical evidence:** raw VALIDATION probabilities reproduce the frozen Sprint 10.8.2.27 seed-0 fusion metrics exactly within `1e-12`. The final full-VALIDATION isotonic mapping has 38 fitted breakpoints and state digest `7c5ca79...64dbc`.

**Methodological inference:** calibration transfer is strongest when the mapping and future scores share the identical fitted base score generator. Procedure A guarantees that identity. Procedure B does not guarantee identical score distributions between OOF fold models and a full-data refit.

**Frozen decision:** do not refit the base models.

## 10. Representation refit analysis

No representation is refitted. CODE scaler population remains TRAIN. TEXT vocabulary, document frequencies, IDF, and normalization state remain TRAIN-fitted. Consequently representation semantics and the calibrator input scale remain those selected in prior sprints. The proposed TRAIN+VALIDATION TF-IDF refit would be leakage-free with respect to TEST, but it would produce a new fitted representation and score generator and is not selected.

## 11. Development-only diagnostics

Only TRAIN and VALIDATION were used. Diagnostics were limited to frozen-score reproduction, population/identity checks, isotonic feasibility/state, and deterministic procedural fold checks. No candidate search occurred.

## 12. Selected final-refit procedure

Despite the historical name “final refit,” the frozen procedure is **A_NO_BASE_REFIT**: preserve both TRAIN-fitted predictors and their preprocessing; generate `0.5/0.5` raw fusion probabilities; apply the isotonic regression fitted once on the complete canonical VALIDATION raw probabilities and labels. Base fitting population is TRAIN (19,114); calibration fitting population is VALIDATION (4,086; 260 positive).

## 13. Rejected procedures and reasons

The declared Sprint 10.8.2.29 hybrid is scientifically incompatible because the calibration and application score generators differ. Development cross-fit/final-refit is not leaky if implemented correctly, but is rejected because its OOF-to-full estimator transfer risk remains and Procedure A offers exact fitted-generator compatibility without altering frozen choices.

## 14. Threshold-policy status

`FINAL_CLASSIFICATION_THRESHOLD = UNDEFINED`. This does not block ROC-AUC, AP, Brier, or frozen 10-bin ECE. Precision, recall, F1, MCC, specificity, balanced accuracy, and confusion matrices are forbidden in the one-shot TEST sprint without a separately frozen TEST-independent threshold. Recommendation: use option B—probability-only one-shot TEST in Sprint 10.8.2.31 and reserve threshold classification for a separately predeclared study. This avoids delaying the primary probability study and prevents retroactive threshold selection.

## 15. TEST-seal verification

Only inherited aggregate identity/count/schema metadata was read. No TEST row-level predictor, label, transformation, feature matrix, probability, prediction, metric, plot, subgroup, threshold, or XAI path executed. `TEST_SEALED = TRUE`.

## 16. Reproducibility evidence

Two complete independent executions produced the same decision, procedure, ancestry, isotonic breakpoints, calibration state digest, final contract digest, and result digest. Seeds remain RF/LR `0`; the procedural-only deterministic stratified-fold validator uses `108230`. Estimator serialization byte identity is not claimed.

## 17. Quality checks

Focused pytest passed (`4 passed`); relevant calibration/fusion/robustness pytest passed (`27 passed`); the complete suite passed (`1349 passed, 1 skipped`). Ruff on modified Python files, Python compilation, and `git diff --check` passed. Historical unrelated Qt lint artifacts are unchanged.

## 18. Threats to validity

Procedure A forgoes using VALIDATION to improve base-estimator fitting and may underuse development data. Isotonic is fitted on only 260 positives and can create ties. Exact compatibility does not imply temporal generalization or calibration stability on TEST. Library/platform differences may affect estimator recreation, so the frozen implementation environment and identities remain important.

## 19. Exact frozen machine-readable identities

Final contract digest: `f146346caf4537ee7038e3df24065104c9dee81da6f0c8cdc0ab205701767381`. Calibration state digest: `7c5ca79f929514e3db71ce75f37dd82806075b9fe193780387dc4d8401764dbc`. Audit result digest: `9fbffbf7d4ee54911399a52ba904af1e308613fb218e7d3eb884e53c1191e09c`. Full identities and isotonic breakpoints are in `audit.json`.

## 20. Scientific decision

**SPRINT_10.8.2.30_GO.** This means only that the complete procedure is frozen and may be subjected to one-shot temporal TEST evaluation. It is not generalization evidence.

## 21. Exact next sprint recommendation

Sprint 10.8.2.31 should execute a probability-only, one-shot temporal TEST evaluation under the frozen contract, reporting prevalence, ROC-AUC, Average Precision, Brier Score, fixed 10-bin ECE, reliability diagram, and bin support. It must make no further development decision and must not report threshold-dependent metrics.
