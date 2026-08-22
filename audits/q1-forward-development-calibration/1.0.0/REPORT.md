# Sprint 10.8.2.36 — Forward DEVELOPMENT Calibration and Decision-Curve Readiness Audit

## Scientific decision

`SPRINT_10.8.2.36_GO_WITH_LIMITATIONS`

Aggregate selection-rule winner: `ISOTONIC`. Adequacy-gate recommendation: `ISOTONIC`.

## Protocol actually executed

Frozen equal-weight C+T was fit on the earliest 5/6 of each project-local outer-training prefix. PLATT and ISOTONIC were fit on the later historical 1/6 and evaluated on the unchanged subsequent outer DEVELOPMENT block for evaluable projects. TEST remained sealed.

## Aggregate calibration

| Method | Brier mean | ECE mean | ROC-AUC mean | PR-AUC mean |
|---|---:|---:|---:|---:|
| UNCALIBRATED | 0.069598 | 0.032652 | 0.745698 | 0.243639 |
| PLATT | 0.069557 | 0.024131 | 0.745698 | 0.243639 |
| ISOTONIC | 0.069454 | 0.013826 | 0.739360 | 0.215410 |

## Origin-level calibration and temporal stability

| Origin | Method | N train/cal/eval | Prev. | Brier | ECE | ROC-AUC | PR-AUC |
|---|---|---:|---:|---:|---:|---:|---:|
| O1 | UNCALIBRATED | 8407/1690/2018 | 0.1041 | 0.084355 | 0.025595 | 0.767698 | 0.301329 |
| O1 | PLATT | 8407/1690/2018 | 0.1041 | 0.085543 | 0.031021 | 0.767698 | 0.301329 |
| O1 | ISOTONIC | 8407/1690/2018 | 0.1041 | 0.085055 | 0.020870 | 0.764837 | 0.271847 |
| O2 | UNCALIBRATED | 11128/2235/2228 | 0.0938 | 0.077693 | 0.026988 | 0.747327 | 0.292948 |
| O2 | PLATT | 11128/2235/2228 | 0.0938 | 0.077906 | 0.033300 | 0.747327 | 0.292948 |
| O2 | ISOTONIC | 11128/2235/2228 | 0.0938 | 0.077228 | 0.009808 | 0.745186 | 0.253904 |
| O3 | UNCALIBRATED | 13519/2713/2319 | 0.0733 | 0.064124 | 0.035931 | 0.742243 | 0.230110 |
| O3 | PLATT | 13519/2713/2319 | 0.0733 | 0.063564 | 0.024086 | 0.742243 | 0.230110 |
| O3 | ISOTONIC | 13519/2713/2319 | 0.0733 | 0.063901 | 0.017379 | 0.736237 | 0.211545 |
| O4 | UNCALIBRATED | 14489/2905/2174 | 0.0681 | 0.061305 | 0.036124 | 0.700000 | 0.196831 |
| O4 | PLATT | 14489/2905/2174 | 0.0681 | 0.060090 | 0.013519 | 0.700000 | 0.196831 |
| O4 | ISOTONIC | 14489/2905/2174 | 0.0681 | 0.061120 | 0.012144 | 0.695512 | 0.166346 |
| O5 | UNCALIBRATED | 16347/3277/2191 | 0.0680 | 0.060510 | 0.038620 | 0.771222 | 0.196978 |
| O5 | PLATT | 16347/3277/2191 | 0.0680 | 0.060684 | 0.018729 | 0.771222 | 0.196978 |
| O5 | ISOTONIC | 16347/3277/2191 | 0.0680 | 0.059967 | 0.008929 | 0.755027 | 0.173410 |

## Temporal memberships and exclusions

- O1: base/calibration/evaluation 8407/1690/2018; excluded project-windows: 4 (minimum calibration-fit class support not met: 4). Exact identities, reasons, and SHA-256 membership digests are in `calibration_memberships.json`.
- O2: base/calibration/evaluation 11128/2235/2228; excluded project-windows: 1 (minimum calibration-fit class support not met: 1). Exact identities, reasons, and SHA-256 membership digests are in `calibration_memberships.json`.
- O3: base/calibration/evaluation 13519/2713/2319; excluded project-windows: 0 (none). Exact identities, reasons, and SHA-256 membership digests are in `calibration_memberships.json`.
- O4: base/calibration/evaluation 14489/2905/2174; excluded project-windows: 0 (none). Exact identities, reasons, and SHA-256 membership digests are in `calibration_memberships.json`.
- O5: base/calibration/evaluation 16347/3277/2191; excluded project-windows: 0 (none). Exact identities, reasons, and SHA-256 membership digests are in `calibration_memberships.json`.

## Paired inference

All origin-level deltas are retained in `paired_calibration_effects.json`. The exact two-sided paired sign test is the sole family. With five nonzero pairs its minimum attainable p-value is 0.0625; non-significance is not equivalence.

## Reliability and discrimination

Ten fixed [0,1] bins, including explicit empty bins, are retained in `reliability_bins.json`. ROC-AUC and PR-AUC are diagnostics only; isotonic ties and any ranking changes remain visible.

## Decision-curve readiness

`DECISION_CURVE_PROTOCOL_NOT_READY`. No curve or threshold optimization was executed. practical JIT-SDP decision cost structure is not yet declared; threshold grid therefore remains undeclared; actual utility comparison is deferred.

## Leakage and reproducibility

Leakage audit: PASS. Identity filtering materialized only TRAIN+VALIDATION; base preprocessing/models used the earliest admissible past; calibrators used only the later historical block; evaluation was disjoint and forward; no prohibited predictor, TEST evidence, outcome-driven boundary, or threshold selection entered fitting.

Five origin bundles include scalers, CODE estimator, TEXT vocabulary/IDF and estimator, feature order, fusion, calibrators, seeds, memberships, runtime and hashes. Reload prediction equivalence: PASS. Cross-runtime pickle byte identity is not claimed.

## Execution ledger

- base_model_fits: **10**
- CODE_fits: **5**
- TEXT_fits: **5**
- calibration_fits: **10**
- prediction_operations: **35**
- DEVELOPMENT_scoring_operations: **15**
- TEST_scoring: **0**
- TEST_predictive_scoring: **0**
- TEST_probability_loading: **0**
- TEST_calibration_fits: **0**
- TEST_threshold_optimization: **0**
- TEST_model_selection: **0**
- hyperparameter_searches: **0**
- continuous_fusion_weight_optimizations: **0**
- threshold_optimizations: **0**
- XAI_executions: **0**
- XAI_on_TEST: **0**
- external_dataset_acquisitions: **0**
- temporal_origins: **5**
- failed_or_undefined_evaluations: **0**

## Quality gates

- Focused Sprint 36 protocol tests before execution: **6 passed, 0 failed, 0 skipped**.
- Relevant calibration/fusion/temporal/governance tests: **153 passed, 0 failed, 0 skipped**.
- Full repository pytest: **1,384 passed, 0 failed, 1 skipped**. The inherited Git SHA-256 repository-capability test was skipped and is not counted as passed.
- Ruff on Sprint 36 Python files: **PASS**.
- Full repository Ruff: **FAIL** due to 31 pre-existing E501 line-length findings in `scripts/validate_q1_experimental_validity_contract.py` and `validation/18C/sample_review_package.py`; no Sprint 36 finding remains.
- Python compilation over `src`, `scripts`, and `tests`: **PASS**.
- `git diff --check`: **PASS**.
- Fitted-state reload equivalence: **PASS** for 5/5 origins.
- Deterministic rerun: **PASS**, byte-identical Sprint 36 artifacts.
- Historical Sprint 32–35 hash verification: **PASS** for 46/46 files.
- TEST boundary verification: **PASS**; all prohibited TEST counters are zero.

## Limitations

Only five dependent origins constrain inference. Raw commit text retains the inherited semantic-proxy limitation. This is DEVELOPMENT-only internal evidence, not external validation, final-model status, or operational utility. PROCESS remains excluded and was not redesigned.

## Exact next sprint

Sprint 10.8.2.37 — formal DEVELOPMENT decision-curve/practical-utility protocol declaration
