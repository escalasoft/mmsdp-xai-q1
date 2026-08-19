# JIT-Defects4J Calibration Execution Audit

## 1. Sprint objective and decision

**SPRINT_10.8.2.29_GO**. The predeclared VALIDATION-only protocol selected exactly one calibration method. This is not final evaluation.

## 2. Frozen upstream evidence and identities

- frozen_architecture_identity: `0f0547ce58d19a7eee75a93bee6addbfe23251758c8c43fb29852f2009d0c47d`
- calibration_protocol_identity: `45233511ca629ea5f38e499029e0eb6dfcac7c160a52d030a31113ea36f35895`
- dataset_identity: `e509995da233c932cafce531c13ad2cd617a0d8abbe8d81ccaa373b8f29fa519`
- manifest_identity: `95b1a362f6756f641cc575cabf54a3a99e2846568d5ef110dac38a45f3d81ef1`
- temporal_boundary_identity: `d1b4448e22a1dba4292b9cf8969ba77db0cf9a10ef66dfddf98642cb5dc078a7`
- adapter_identity: `9c22de3d15d09132af1920eec0fd02e3ea9f879a70ecbd90bc5adc7913b63d2c`
- frozen_robustness_result_identity: `384e640924979d59882aa6b567b7d3216bdb7420948f66288a48d44f66e1c618`
- execution_configuration_identity: `b4e2d5acafa6561208cbca0fdebba0a16c66f3b3ef1a3938197434199318833a`
- result_digest: `578283a75ae39ba37627e1201b1221e32cc5779daf993d66fdd643e5a1772aa3`

The frozen architecture is CODE Random Forest plus TEXT liblinear Logistic Regression using TRAIN-fitted preprocessing and deterministic equal-weight late probability fusion. PROCESS is excluded from the primary predictor.

## 3. Dataset and VALIDATION boundary

VALIDATION contains 4086 canonical observations: 260 positive and 3826 nominal negative; prevalence is 0.06363191385217817. Canonical order and the frozen temporal boundary were preserved.

## 4. Frozen calibration protocol and execution

Candidates were exactly UNCALIBRATED, PLATT, and ISOTONIC. Five shuffled StratifiedKFold folds used seed 108228. Fitted mappings saw only four VALIDATION folds and predicted only the disjoint held-out fold. OOF coverage was exactly once in canonical order. No base model or preprocessing was refit inside calibration folds.

## 5. Calibration and discrimination results

Brier and ECE are calibration-selection metrics. ROC-AUC and Average Precision are discrimination diagnostics only and did not participate in selection.

| Candidate | Brier | ECE | ROC-AUC | PR-AUC/AP | Selected |
|---|---:|---:|---:|---:|---|
| UNCALIBRATED | 0.05700106264607801 | 0.03420507746497094 | 0.7460332140415779 | 0.19308415510473656 | NO |
| PLATT | 0.05678503489218549 | 0.013547136102584928 | 0.7453556636776708 | 0.1933888609850548 | NO |
| ISOTONIC | 0.056083223875184815 | 0.005046090270136952 | 0.7338885761389682 | 0.17204383535872067 | YES |

Selected **ISOTONIC** by the frozen rule: lowest OOF VALIDATION Brier; ECE only within absolute 1e-12 Brier tie; final order UNCALIBRATED, PLATT, ISOTONIC.

## 6. Reliability diagnostics

All candidates use identical fixed equal-width bins. The reference is the identity diagonal `y=x`; diagrams are diagnostic and cannot override selection.

| Candidate | Bin | N | Mean probability | Positive fraction |
|---|---|---:|---:|---:|
| UNCALIBRATED | [0.0, 0.1) | 2587 | 0.06181313378835564 | 0.028991109393119444 |
| UNCALIBRATED | [0.1, 0.2) | 1234 | 0.13497832979954405 | 0.09481361426256078 |
| UNCALIBRATED | [0.2, 0.3) | 200 | 0.23808339957603472 | 0.23 |
| UNCALIBRATED | [0.3, 0.4) | 42 | 0.3416044655705612 | 0.3333333333333333 |
| UNCALIBRATED | [0.4, 0.5) | 18 | 0.43607963465567456 | 0.2777777777777778 |
| UNCALIBRATED | [0.5, 0.6) | 4 | 0.531251197301684 | 0.5 |
| UNCALIBRATED | [0.6, 0.7) | 1 | 0.6503952434215448 | 1.0 |
| PLATT | [0.0, 0.1) | 3784 | 0.05758466079905408 | 0.04994714587737843 |
| PLATT | [0.1, 0.2) | 255 | 0.12821043407406982 | 0.21568627450980393 |
| PLATT | [0.2, 0.3) | 32 | 0.24064919361729298 | 0.3125 |
| PLATT | [0.3, 0.4) | 11 | 0.3466360149465705 | 0.2727272727272727 |
| PLATT | [0.4, 0.5) | 3 | 0.4495992656694301 | 0.6666666666666666 |
| PLATT | [0.6, 0.7) | 1 | 0.6165218312214598 | 1.0 |
| ISOTONIC | [0.0, 0.1) | 3409 | 0.041730465930004075 | 0.043121149897330596 |
| ISOTONIC | [0.1, 0.2) | 463 | 0.12224414048291216 | 0.12311015118790497 |
| ISOTONIC | [0.2, 0.3) | 110 | 0.2403030696791017 | 0.2818181818181818 |
| ISOTONIC | [0.3, 0.4) | 97 | 0.31711059990098484 | 0.2268041237113402 |
| ISOTONIC | [0.4, 0.5) | 2 | 0.42857142857142855 | 0.0 |
| ISOTONIC | [0.5, 0.6) | 1 | 0.5303770255944852 | 0.0 |
| ISOTONIC | [0.6, 0.7) | 1 | 0.6577889176134677 | 0.0 |
| ISOTONIC | [0.8, 0.9) | 1 | 0.8951790832933509 | 1.0 |
| ISOTONIC | [0.9, 1.0] | 2 | 1.0 | 1.0 |

## 7. Discrimination invariance

Fold-specific cross-fitted mappings need not be globally rank invariant because different fitted maps apply to different held-out folds. Platt is monotone within each fold. Isotonic is monotone within each fold and may introduce ties. Any observed ROC-AUC/AP changes are reported above, not suppressed, and were not used for selection.

## 8. Leakage audit

**PASS.** No target, fixing/SZZ, future, issue-linkage, project, or split identity entered predictors. TEXT remained TRAIN-fitted; base models fit TRAIN only; calibration fitting used VALIDATION OOF fit folds only; each held-out observation was excluded from its calibrator's labels; TRAIN/VALIDATION identities did not overlap; provenance remained traceable.

## 9. TEST seal

`TEST_SEALED = TRUE`. The development loader reads only frozen TRAIN and VALIDATION adapter artifacts and actively rejects TEST partition access. No TEST matrix, row-level label, prediction, probability, residual, metric, plot, threshold, fit, or selection operation occurred.

## 10. Reproducibility

Two independent complete executions were exactly identical for candidate metrics, selected method, reliability summaries, frozen identities, leakage outcome, and pre-annotation result digest.

## 11. Limitations

- Selection evidence is development-only VALIDATION evidence.
- OOF calibrated discrimination can change across fold-specific mappings; isotonic may also introduce ties.
- Final generalization is unknown because TEST remains sealed.

## 12. Predeclared final refit and one-shot TEST procedure (not executed)

1. Freeze this audit and selected calibrator identity before any TEST access.
2. Use exactly the existing canonical TRAIN and VALIDATION observations, pooled only for final base-model refit.
3. Refit CODE StandardScaler on TRAIN+VALIDATION six frozen CODE features and refit the frozen RF configuration.
4. Refit the frozen 5,000-feature unigram TF-IDF vocabulary/state on TRAIN+VALIDATION text only and refit the frozen liblinear LR configuration.
5. Generate raw probabilities by fixed p=0.5*p_CODE+0.5*p_TEXT.
6. Fit the selected calibrator once on the original TRAIN-fitted model's full canonical VALIDATION raw probabilities and labels; if UNCALIBRATED, retain identity mapping.
7. Open TEST only after all refitted model, representation, fusion, calibration, metric, and threshold contracts are frozen and independently validated.
8. Evaluate TEST exactly once and report ROC-AUC, Average Precision, Brier Score, and fixed-bin ECE; any threshold metrics require a separately predeclared frozen threshold.
9. Make no post-TEST model, calibrator, feature, fusion-weight, or threshold changes.

## 13. Recommended next sprint

Sprint 10.8.2.30 should independently validate and then execute only the frozen final-refit and one-shot TEST-opening procedure above, with no post-TEST changes. If a threshold metric is required, its threshold must first be frozen without TEST evidence.
