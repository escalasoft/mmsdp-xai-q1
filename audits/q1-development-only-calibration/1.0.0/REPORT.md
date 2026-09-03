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
