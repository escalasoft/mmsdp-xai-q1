# Sprint 10.8.2.34 — Q1 Modality Factorial

## A. Scientific question

What independent, pairwise, and incremental predictive contribution do CODE, PROCESS, and TEXT provide under identical development-only temporal origins?

## B. Experimental contract inherited from Sprint 33

The exact seven treatments, five rank-fraction origins, support rules, frozen estimators, equal-weight fusion, seed, leakage denylist, and TEST prohibition are inherited unchanged.

## C. Dataset and development boundary

JIT-Defects4J 1.0.0 canonical TRAIN+VALIDATION only (23,200 eligible rows before per-origin support exclusions). Sealed TEST identities are not eligible and their JSON payloads are not deserialized.

## D. Temporal rolling-origin design

Within each project, order is `(git_committer_timestamp, commit_hash)`. Five expanding prefixes at 1/2, 3/5, 7/10, 4/5, and 9/10 predict the next blocked interval. Infeasible project-windows are recorded and excluded without boundary movement.

## E. Seven modality treatments

`C`, `P`, `T`, `C+P`, `C+T`, `P+T`, and `C+P+T` use identical origin memberships.

## F. Exact features per modality

CODE: changed-file, add, delete, modify, other-status, and mode-change counts. PROCESS: parent count, merge flag, prior-history flag, and ancestor-only prior project commit count. TEXT: canonical raw commit message transformed by origin-training-only unigram TF-IDF (min DF 2, maximum 5,000).

## G. Exact model and fusion implementation

Frozen RF candidate `code-rf-2` for C, RF candidate `process-rf-2` for P, and LR candidate `text-lr-2` for T. Multimodal scores are the fixed equal-weight arithmetic mean of constituent positive-class probabilities.

## H. Leakage controls

Development identities are obtained from frozen adapters; canonical rows are identity-filtered before deserialization. Scaling, vocabulary, DF/IDF, and estimators fit only the current origin prefix. Project, commit hash, timestamp, split, target, fixing/SZZ fields, and engineered defect-keyword indicators are not predictors.

## I. Reproducibility controls

Every origin bundle is written before evaluation transformation/scoring and contains scalers, ordered TEXT state, three estimators, schemas, membership/configuration digests, class order, seed-derived parameters, fixed threshold, and explicit null calibrator. SHA-256 and exact same-runtime reload fixture-prediction equality are recorded. Cross-runtime byte identity is not claimed.

## J. Origin-level results

Complete rows are in `factorial_results.csv` and `factorial_results.json`. ROC-AUC / PR-AUC by origin:

| Origin | Treatment | ROC-AUC | PR-AUC |
|---|---|---:|---:|
| O1 | C | 0.7177 | 0.2634 |
| O1 | P | 0.4787 | 0.0923 |
| O1 | T | 0.7309 | 0.2179 |
| O1 | C+P | 0.6904 | 0.2485 |
| O1 | C+T | 0.7661 | 0.3019 |
| O1 | P+T | 0.6912 | 0.1951 |
| O1 | C+P+T | 0.7532 | 0.2918 |
| O2 | C | 0.7056 | 0.2363 |
| O2 | P | 0.4676 | 0.0801 |
| O2 | T | 0.7087 | 0.2038 |
| O2 | C+P | 0.6648 | 0.2098 |
| O2 | C+T | 0.7539 | 0.2842 |
| O2 | P+T | 0.6810 | 0.1741 |
| O2 | C+P+T | 0.7382 | 0.2557 |
| O3 | C | 0.7212 | 0.2327 |
| O3 | P | 0.5274 | 0.0752 |
| O3 | T | 0.6971 | 0.1421 |
| O3 | C+P | 0.6970 | 0.2189 |
| O3 | C+T | 0.7530 | 0.2323 |
| O3 | P+T | 0.6757 | 0.1335 |
| O3 | C+P+T | 0.7387 | 0.2235 |
| O4 | C | 0.6467 | 0.1819 |
| O4 | P | 0.4789 | 0.0644 |
| O4 | T | 0.6800 | 0.1520 |
| O4 | C+P | 0.6303 | 0.1789 |
| O4 | C+T | 0.7049 | 0.2037 |
| O4 | P+T | 0.6636 | 0.1308 |
| O4 | C+P+T | 0.6966 | 0.1966 |
| O5 | C | 0.7270 | 0.1855 |
| O5 | P | 0.4656 | 0.0634 |
| O5 | T | 0.6999 | 0.1479 |
| O5 | C+P | 0.7080 | 0.1757 |
| O5 | C+T | 0.7699 | 0.2012 |
| O5 | P+T | 0.6740 | 0.1403 |
| O5 | C+P+T | 0.7572 | 0.1949 |

## K. Aggregated descriptive results

Mean (sample SD) across five origins:

| Treatment | ROC-AUC | PR-AUC | Brier | ECE |
|---|---:|---:|---:|---:|
| C | 0.7036 (0.0328) | 0.2199 (0.0352) | 0.0696 (0.0103) | 0.0203 (0.0092) |
| P | 0.4836 (0.0252) | 0.0751 (0.0120) | 0.0763 (0.0133) | 0.0315 (0.0080) |
| T | 0.7033 (0.0186) | 0.1727 (0.0353) | 0.0722 (0.0099) | 0.0287 (0.0087) |
| C+P | 0.6781 (0.0311) | 0.2063 (0.0302) | 0.0705 (0.0112) | 0.0230 (0.0096) |
| C+T | 0.7496 (0.0260) | 0.2447 (0.0463) | 0.0683 (0.0099) | 0.0287 (0.0054) |
| P+T | 0.6771 (0.0101) | 0.1548 (0.0284) | 0.0720 (0.0112) | 0.0242 (0.0091) |
| C+P+T | 0.7368 (0.0241) | 0.2325 (0.0413) | 0.0695 (0.0106) | 0.0299 (0.0065) |

## L. Pairwise modality contrasts

Signed mean differences and origin win/tie/loss counts (left minus right):

| Contrast | ROC-AUC mean (W/T/L) | PR-AUC mean (W/T/L) |
|---|---:|---:|
| C+P - C | -0.0255 (0/0/5) | -0.0136 (0/0/5) |
| C+P - P | +0.1945 (5/0/0) | +0.1313 (5/0/0) |
| C+T - C | +0.0459 (5/0/0) | +0.0247 (4/0/1) |
| C+T - T | +0.0462 (5/0/0) | +0.0719 (5/0/0) |
| P+T - P | +0.1935 (5/0/0) | +0.0797 (5/0/0) |
| P+T - T | -0.0262 (0/0/5) | -0.0180 (0/0/5) |
| C+P+T - C+P | +0.0587 (5/0/0) | +0.0262 (5/0/0) |
| C+P+T - C+T | -0.0128 (0/0/5) | -0.0122 (0/0/5) |
| C+P+T - P+T | +0.0597 (5/0/0) | +0.0777 (5/0/0) |
| C+P+T - C | +0.0332 (5/0/0) | +0.0126 (4/0/1) |
| C+P+T - P | +0.2532 (5/0/0) | +0.1574 (5/0/0) |
| C+P+T - T | +0.0335 (5/0/0) | +0.0598 (5/0/0) |

## M. Calibration findings

No calibrator was fitted because Sprint 33 defers calibration comparison to a later forward/nested protocol. Brier and 10-bin ECE are explicitly uncalibrated descriptive evidence.

## N. Negative and neutral results

PROCESS is near random alone and often reduces discrimination when added. C+P+T does not exceed C+T at any origin on ROC-AUC or PR-AUC. These outcomes are retained without treatment changes.

## O. Limitations

Raw commit text may naturally contain defect/fix words; upstream positive-label derivation is inherited rather than independently reconstructed; several project-origin windows fail frozen support and are excluded as declared; probabilities are uncalibrated; five origins are too few for strong inferential claims.

## P. Threats to validity

Fixed averaging can attenuate a useful modality and does not test learned complementarity. Historical development data may not transport to a later snapshot. A fixed 0.5 threshold yields sparse positive classifications under imbalance and is descriptive, not an optimized operational rule.

## Q. Implications for MMSDP-XAI

Under this frozen representation, CODE+TEXT is the most defensible descriptive treatment; the broad claim that all three modalities complement one another is not supported.

## R. What the experiment DOES support

Paired descriptive claims about the seven frozen treatments across these five historical development origins, including direction, magnitude, temporal variability, and uncalibrated probability quality.

## S. What the experiment DOES NOT support

Statistical superiority, causal modality effects, external transportability, final TEST performance, optimal fusion, calibrated deployment probabilities, or XAI validity.

## T. Recommended next sprint

Sprint 10.8.2.35 — Fusion and ablation audit: carry C+T as the descriptive reference, test fixed fusion sensitivity and learned stacking only through nested out-of-time development predictions, and apply the single predeclared paired-inference family to this frozen matrix. Do not advance C+P+T by default and do not open TEST.

## Scientific decision

`SPRINT_10.8.2.34_GO_WITH_LIMITATIONS`
