# Sprint 51 development-only probability calibration

**Final scientific classification:** `PASS_51_ALGORITHM_SPECIFIC_CALIBRATION_SELECTED`

## Protocol

For each project, algorithm, configuration, and evaluation origin K=3..11, Platt and isotonic mappings were fitted only on frozen raw probabilities and labels from origins 2..K-1. Origin K was then evaluated once. CV=2 remained RAW-only because no earlier out-of-time probability block exists. Strict causality follows the frozen Sprint 50-R1 `(timestamp, commit_sha)` order; fit and evaluation identities are disjoint.

## Overall common-domain calibration

| State | Brier mean ± SD | ECE mean ± SD |
|---|---:|---:|
| RAW | 0.180784 ± 0.063113 | 0.118163 ± 0.081606 |
| PLATT | 0.189092 ± 0.084039 | 0.125134 ± 0.108795 |
| ISOTONIC | 0.189472 ± 0.084798 | 0.123840 ± 0.105710 |

SD is empirical dispersion across 3,527 valid project-origin-configuration-algorithm units per state, not a standard error or confidence interval.

## Selection

RAW/Platt/isotonic selections across 28 algorithm/configuration scopes: 27/0/1.
Exact joint magnitude, stability, Holm-adjusted Wilcoxon, rank-biserial, support, and instability gates are in `calibration_selection_decisions.csv`.

## Integrity

All 7054 calibrator fits were earlier-block-only. 1 unit was excluded for all three comparison states by the predeclared support rule and remains preserved in the all-origin RAW baseline. T1/T2 training, calibration fitting, scoring, threshold selection, and XAI counters are zero. No model retraining, hyperparameter search, threshold optimization, or XAI occurred.

## Near-perfect diagnostic

Flagged method-unit results: 61. A near-zero value alone was not classified as leakage; exact classifications for all valid units are retained in `near_perfect_diagnostics.csv`.

## Statistical comparison

Two-sided paired Wilcoxon signed-rank tests use 14 project means after averaging CV=3..11 within project. Holm correction covers six method-pair × primary-metric tests within each algorithm/configuration. Effect size is paired rank-biserial correlation. P-values alone do not determine selection.

## Recommendation

Sprint 52 should consume only the selected per-scope calibration state frozen here, retain RAW where calibration did not clear every gate, and continue to prohibit T1/T2 and XAI unless separately prospectively authorized.

## Final human review

- Branch: `sprint-10/q1-development-only-calibration`.
- Starting HEAD: `5f2e0ef7b77081db3e91a46fca85da03a831d3ce` (merged Sprint 50 baseline).
- Existing files modified: none. New implementation/configuration/test files and the versioned `audits/q1-development-only-calibration/1.0.0/` package were created.
- Exact protocol: for each project, algorithm, configuration, and K=3..11, fit each calibrator on raw probabilities and labels from K=2..K-1 and score K only. CV=2 is RAW-only. Fit/evaluation identities are disjoint and strict frozen `(timestamp, commit_sha)` ordering is enforced.
- Valid common comparison units: 3,527/3,528. The excluded unit is `apache/zeppelin × LightGBM × T × CV=3`: 105 fit rows and both classes, but one unique fit probability. It was excluded symmetrically from all three comparison states and preserved in the complete RAW baseline.
- Overall Brier mean ± sample SD: RAW `0.180784 ± 0.063113`; Platt `0.189092 ± 0.084039`; isotonic `0.189472 ± 0.084798`.
- Overall ECE mean ± sample SD: RAW `0.118163 ± 0.081606`; Platt `0.125134 ± 0.108795`; isotonic `0.123840 ± 0.105710`.
- Dispersion is empirical project-origin dispersion, not a standard error or confidence interval.
- Selection: RAW for 27/28 algorithm/configuration scopes; isotonic only for `LightGBM × P`; Platt for 0/28.
- Selected-scope paired evidence (`LightGBM × P`, isotonic minus RAW): Brier mean difference `-0.009813`, 11/14 project wins, Wilcoxon statistic `10`, raw p `0.005249`, Holm p `0.031494`, rank-biserial `0.809524`; ECE mean difference `-0.030529`, 11/14 wins, statistic `11`, raw p `0.006714`, Holm p `0.033569`, rank-biserial `0.790476`.
- All 168 paired comparisons, including Platt versus RAW, isotonic versus RAW, and Platt versus isotonic, are retained in `paired_statistical_comparisons.csv`. P-values were not used alone.
- Near-perfect audit: zero Brier≈0 and zero ECE≈0 units; 61 extreme-concentration flags—50 repeated/structural, 7 class-imbalance-sensitive, and 4 suspicious/provenance-review-required. The four suspicious cases are unfavorable degenerate calibration outputs outside the selected scope; none is treated as leakage from value alone.
- T1 counters—training 0, calibration fitting 0, scoring 0, threshold selection 0, XAI 0. T2 counters are identical zeros.
- Focused Sprint 51 tests: 17 passed, 0 failed, 0 skipped.
- Relevant Sprint 50/50-R1 regressions: 53 passed and 3 expected frozen starting-HEAD guard failures; unknown failures 0.
- Full suite: 1,695 passed, 1 skipped, 5 failed, 23 errors, 3 known LightGBM warnings. Historical expected guards: 23 errors + 2 failures from the Sprint 43 integrity/boundary family, plus 3 Sprint 50 starting-HEAD failures. New regressions 0; unknown failures 0.
- Ruff on changed Python files: PASS. `git diff --check`: PASS.
- Core manifest verification: PASS. Two consecutive isolated regenerations: PASS byte-identical with core manifest SHA-256 `6190cc714574578c07c14186778f23d1dba5247f2b55c9f2776bf63a25715d35`.
- Final scientific classification: `PASS_51_ALGORITHM_SPECIFIC_CALIBRATION_SELECTED`.
- Exact Sprint 52 recommendation: freeze isotonic only for `LightGBM × P`, freeze RAW for every other scope, carry forward the single support exclusion and four provenance-review flags as explicit limitations, and do not authorize T1, T2, threshold optimization, model reselection, retraining, or XAI without a separate prospective sprint.
