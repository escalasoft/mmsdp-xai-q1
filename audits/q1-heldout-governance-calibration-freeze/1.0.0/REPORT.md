# Sprint 52 prospective calibration freeze and held-out governance

**Final classification:** `PASS_52_HELDOUT_GOVERNANCE_FROZEN_READY_FOR_T1_AUTHORIZATION_REVIEW`

This is a governance/freeze result only. It does not authorize T1 predictive execution.

- Starting branch: `sprint-10/q1-heldout-governance-calibration-freeze`.
- Starting HEAD: `92216e0` (`92216e0d8f5ad4a39efa6977322c837c0306c092`).

## Frozen contract

- Algorithms: Logistic Regression, Random Forest, XGBoost, LightGBM.
- Configurations: CODE, PROCESS, TEXT, CODE + PROCESS, CODE + TEXT, PROCESS + TEXT, CODE + PROCESS + TEXT.
- Calibration: RAW 27/28; PLATT 0/28; ISOTONIC 1/28 (`LightGBM × PROCESS` only).
- Threshold: fixed 0.5 for all 28 scopes, inherited from Sprint 49; no optimization.
- T1 role: `CONFIRMATORY_HELD_OUT_TEST`; current access DENY.
- T2 role: `SEALED_REVIEWER_RESERVE`; remains sealed after T1 and is not automatically opened.

## Integrity

- All Sprint 48F-R1, 49, 50, 50-R1, and 51 manifest packages verified.
- T1 structural identities: 3787; SHA-256 `50186112bc3860c7c97d00233b389386a84acf0505d4f05bdb2075128b350f93`.
- T2 structural identities: 15161; SHA-256 `e6ba492aae300a61aefad01d1697bef3e10303bffc924ba437bd8437f6dbb4f7`.
- All Sprint 52 execution counters are zero.
- G1–G18: PASS for future human authorization review; T1 execution remains unauthorized.

## Governance consequence

The primary article design is DEVELOPMENT → separately authorized T1 confirmatory evaluation. T2 remains sealed. Opening T2 is a separate scientific event requiring its own human authorization and immutable protocol. There is no requirement to consume all held-out data.

## Verification scope

Only immutable evidence hashes and structural, label-free membership records were read. No model training, predictive scoring, calibration fitting, threshold or feature selection, hyperparameter search, held-out predictive access, metrics, or XAI occurred.

## Verification results

- Focused Sprint 52 tests: 7 passed, 0 failed.
- Relevant Sprint 48F-R1/49/50/50-R1/51 regressions: 118 passed; 3 expected Sprint 50 starting-HEAD guards failed; 0 new or unknown failures.
- Full suite: 1,702 passed, 1 skipped, 5 failed, 23 errors, 3 warnings.
- Expected historical guards: 23 Sprint 43 integrity errors, 2 historical-boundary failures, and 3 Sprint 50 starting-HEAD failures.
- New regressions: 0. Unknown failures: 0.
- Ruff, git diff check, output manifest verification, and two-run byte-identical deterministic regeneration: PASS.
