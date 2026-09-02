# Sprint 50 temporal robustness CV=2..11

**Final classification:** `PASS_50_WITH_MIXED_MULTIMODAL_EVIDENCE`

All 3,920 authorized development conditions completed under expanding forward temporal validation. No T1/T2 access, XAI, tuning, threshold selection, feature reselection, or calibration fitting occurred.

## Execution

- Projects: 14; algorithms: 4; configurations: 7; CV origins: 10.
- Successful conditions: 3,920; failed/non-estimable conditions: 0.
- Internal model fits: 4,088; predictive scoring operations: 4,088.
- Raw development probabilities retained: 1,928,304.
- Ceiling diagnostic threshold: 0.99.
- Flagged condition-metric ceilings: 490.
- Inference uses 14 paired project units after averaging repeated CV origins.

## Aggregate PR-AUC and MCC

| Algorithm | Configuration | PR-AUC mean ± SD | MCC mean ± SD |
|---|---|---:|---:|
| Logistic Regression | C | 0.6788 ± 0.2127 | 0.2629 ± 0.1642 |
| Logistic Regression | P | 0.5521 ± 0.2418 | 0.1297 ± 0.1361 |
| Logistic Regression | T | 0.5654 ± 0.2410 | 0.1230 ± 0.1323 |
| Logistic Regression | C+P | 0.6624 ± 0.2269 | 0.2228 ± 0.1749 |
| Logistic Regression | C+T | 0.6778 ± 0.2205 | 0.2436 ± 0.1822 |
| Logistic Regression | P+T | 0.5815 ± 0.2411 | 0.1365 ± 0.1450 |
| Logistic Regression | C+P+T | 0.6723 ± 0.2236 | 0.2420 ± 0.1722 |
| Random Forest | C | 0.6964 ± 0.2157 | 0.3521 ± 0.1672 |
| Random Forest | P | 0.6047 ± 0.2403 | 0.1890 ± 0.1433 |
| Random Forest | T | 0.5555 ± 0.2429 | 0.1316 ± 0.1392 |
| Random Forest | C+P | 0.6978 ± 0.2172 | 0.3150 ± 0.1839 |
| Random Forest | C+T | 0.6987 ± 0.2200 | 0.3248 ± 0.1891 |
| Random Forest | P+T | 0.6188 ± 0.2417 | 0.1679 ± 0.1661 |
| Random Forest | C+P+T | 0.7011 ± 0.2185 | 0.3234 ± 0.1877 |
| XGBoost | C | 0.6909 ± 0.2189 | 0.3425 ± 0.1531 |
| XGBoost | P | 0.6092 ± 0.2356 | 0.2072 ± 0.1331 |
| XGBoost | T | 0.5563 ± 0.2422 | 0.1372 ± 0.1449 |
| XGBoost | C+P | 0.6950 ± 0.2199 | 0.3086 ± 0.1818 |
| XGBoost | C+T | 0.6965 ± 0.2201 | 0.3164 ± 0.1869 |
| XGBoost | P+T | 0.6261 ± 0.2349 | 0.1932 ± 0.1673 |
| XGBoost | C+P+T | 0.7010 ± 0.2183 | 0.3187 ± 0.1870 |
| LightGBM | C | 0.6780 ± 0.2245 | 0.3334 ± 0.1545 |
| LightGBM | P | 0.6003 ± 0.2376 | 0.2047 ± 0.1360 |
| LightGBM | T | 0.5503 ± 0.2427 | 0.1493 ± 0.1307 |
| LightGBM | C+P | 0.6781 ± 0.2283 | 0.2913 ± 0.1792 |
| LightGBM | C+T | 0.6784 ± 0.2315 | 0.2968 ± 0.1894 |
| LightGBM | P+T | 0.6088 ± 0.2432 | 0.1833 ± 0.1661 |
| LightGBM | C+P+T | 0.6822 ± 0.2289 | 0.3029 ± 0.1812 |

The SD values above describe all 140 project-origin observations per algorithm/configuration, and therefore reflect both cross-project and temporal variation. Project-specific ten-origin dispersion is in `cv_dispersion_summary.csv`.

## Best-family comparisons

| Algorithm | Metric | Against | Mean delta ± SD | Project W/T/L | CV W/T/L |
|---|---|---|---:|---:|---:|
| Logistic Regression | PR_AUC | BEST_UNIMODAL | -0.0113 ± 0.0635 | 6/0/8 | 4/0/6 |
| Logistic Regression | PR_AUC | BEST_PAIRWISE | -0.0094 ± 0.0181 | 1/0/13 | 0/0/10 |
| Logistic Regression | MCC | BEST_UNIMODAL | -0.0504 ± 0.1330 | 5/0/9 | 2/0/8 |
| Logistic Regression | MCC | BEST_PAIRWISE | -0.0176 ± 0.0534 | 3/0/11 | 1/0/9 |
| Random Forest | PR_AUC | BEST_UNIMODAL | 0.0026 ± 0.0332 | 10/0/4 | 7/0/3 |
| Random Forest | PR_AUC | BEST_PAIRWISE | -0.0055 ± 0.0182 | 4/0/10 | 0/0/10 |
| Random Forest | MCC | BEST_UNIMODAL | -0.0410 ± 0.1462 | 6/0/8 | 3/0/7 |
| Random Forest | MCC | BEST_PAIRWISE | -0.0168 ± 0.0459 | 0/0/14 | 0/0/10 |
| XGBoost | PR_AUC | BEST_UNIMODAL | 0.0049 ± 0.0239 | 11/0/3 | 7/0/3 |
| XGBoost | PR_AUC | BEST_PAIRWISE | -0.0055 ± 0.0142 | 4/0/10 | 1/0/9 |
| XGBoost | MCC | BEST_UNIMODAL | -0.0346 ± 0.1451 | 7/0/7 | 3/0/7 |
| XGBoost | MCC | BEST_PAIRWISE | -0.0174 ± 0.0628 | 3/0/11 | 1/0/9 |
| LightGBM | PR_AUC | BEST_UNIMODAL | 0.0004 ± 0.0458 | 9/0/5 | 6/0/4 |
| LightGBM | PR_AUC | BEST_PAIRWISE | -0.0061 ± 0.0155 | 2/0/12 | 2/0/8 |
| LightGBM | MCC | BEST_UNIMODAL | -0.0458 ± 0.1419 | 6/0/8 | 0/0/10 |
| LightGBM | MCC | BEST_PAIRWISE | -0.0192 ± 0.0652 | 5/0/9 | 1/0/9 |

These are descriptive comparisons against the observed best member of each family at the same project/CV origin. Formal inference remains on the six predeclared exact comparators to avoid treating a post-observation maximum as an ordinary fixed comparator.

## Statistical and multimodal interpretation

Robust favorable primary comparisons meeting adjusted significance, positive 95% CI, and rank-biserial ≥0.3: 31/48. Significant negative comparisons: 1/48. Statistical significance is not interpreted as practical superiority by itself.
The sole adjusted-significant negative primary result is Logistic Regression PR-AUC for C+P+T versus C+T (mean project difference -0.0055, Holm-adjusted p=0.0105, rank-biserial -0.810). Thus full multimodality is not uniformly better than pairwise fusion.

The complete exact-comparator trajectories, project win/tie/loss evidence, Holm-adjusted tests, bootstrap intervals, and effect sizes are retained in the machine-readable artifacts. The final classification follows the prospectively declared rule; no narrative or model was optimized after results.

## Temporal dispersion and ceiling audit

Mean trajectory range across project/algorithm/configuration groups is 0.4075 for PR-AUC and 0.3590 for MCC. Most trajectories are non-monotonic; the exact trajectory evidence is retained without outlier removal.
The predeclared >=0.99 audit flagged 490 condition-metrics, including 337 exact 1.0 values: PR-AUC=110, Recall=255, and Precision=125. No ROC-AUC, MCC, or F1 value crossed the threshold.
Diagnostic classes were repeated-adjacent=296, isolated=129, and class-imbalance-sensitive=65. These flags are not classified as leakage without evidence.

## Calibration and integrity

No calibrator was fitted. RAW Brier score and ECE are retained at condition level, raw probabilities are preserved for the dedicated calibration stage, and RAW/Platt/Isotonic selection is deferred. T1/T2 training, scoring, calibration, and XAI counters are all zero.

## Limitations

Temporal origins within a project are dependent and are used descriptively; inference collapses them to a project-level mean. K2 Zeppelin late-fusion meta-training has only four positives. ApacheJIT labels remain benchmark-defined observations rather than verified ground truth. CV=9 uses the accepted full mixed-provenance block and is not identical to Sprint 49's TRAIN-only K9 diagnostic. Calibration fitting and XAI remain deferred.
