# Sprint 10.8.2.44 — Predeclared Final Performance Evaluation Contract

## Scope and authority

This is a prospective contract only. Sprint 43 is consumed at SHA-256 `62371c0bbd7381eaa8694a52d1f10d7008b2e2b76d7aceb3677cf31b147c0bd7` with outcome `GO_WITH_LIMITATIONS` under `RULE_4`. That outcome does not authorize TEST. TEST remains sealed and candidate, threshold, calibrator, and XAI authorization remain false.

## Frozen evidence

Primary predictive-performance reporting is mandatory and non-reducible: ROC-AUC, PR-AUC, Precision, Recall, F1-score, MCC. Positive-class prevalence is not a predictive-performance metric; it is mandatory descriptive class-distribution context and must accompany performance reporting independently. Calibration requires Brier score, ECE. Decision-curve and normalized/cost evidence are required where applicable. Accuracy cannot be the sole or principal argument; unfavorable and origin-level results cannot be hidden.

## Prospective safeguards

The accepted feature space and CODE/PROCESS/TEXT representations are frozen. Post-outcome imbalance intervention, feature selection, representation redesign, TEST tuning, and rescue experiments are prohibited. Anomalously high performance requires a persisted diagnostic audit and is never automatically accepted. Moderate or limited performance is reported exactly, preserved, and may support only a narrower evidence-backed claim.

## Interpretation

Comparative contribution, absolute predictive quality, calibration, practical utility, and robustness/stability are distinct, scientifically material dimensions. Interpretation uses STRONG, MODERATE, LIMITED, or INCONCLUSIVE without fabricated numerical cutoffs.

## Integrity and execution

Historical integrity: **PASS** across `159` accepted audit files. Every prohibited-operation counter is zero. Later TEST access requires a separate, explicit, human-accepted authorization; this contract does not grant it.

## Quality gates

- `focused_pytest`: PASS — 7 passed in 20.23s
- `preceding_regressions`: PASS — covered by isolated complete legacy suite; accepted artifacts restored byte-for-byte afterward
- `legacy_full_pytest`: PASS — 1509 passed, 1 skipped in 96.44s
- `ruff`: PASS — All checks passed for changed Python files
- `python_compilation`: PASS — py_compile passed
- `ajv_schema`: PASS — draft-07 contract schema valid under AJV
- `deterministic_replay`: PASS — byte-identical materialization replay
- `artifact_manifest`: PASS — all declared artifact SHA-256 values matched
- `historical_integrity`: PASS — 159 protected files; zero missing, unexpected, mismatched, or modified
- `git_diff_check`: PASS — clean
