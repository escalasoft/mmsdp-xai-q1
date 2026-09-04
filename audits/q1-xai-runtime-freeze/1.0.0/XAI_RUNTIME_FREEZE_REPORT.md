# Sprint 55 XAI Runtime Freeze Report

## Disposition

`SHAP_RUNTIME_VERSION_UNRESOLVED`

The complete explainer, population, ordering, query-budget, fidelity, stability, interpretation, T1, and T2 contracts are frozen. No SHAP release can currently be selected without changing the frozen predictive runtime: SHAP 0.52.0 requires Python >=3.12, while SHAP 0.51.0 on Darwin x86_64 requires Numba <0.63 and Numba 0.62.1 requires NumPy <2.4, conflicting with frozen NumPy 2.4.6. Installation and execution therefore remain prohibited pending a separate prospective human decision.

## A–Z record

- **A — Branch and HEAD:** `sprint-10/q1-xai-governance-protocol` at `e13e9949a0bc0ea828882c4d22a5de310f909386`.
- **B — Starting G5 state:** `FULL_G5_FINAL_OUTPUT_EQUIVALENCE_XAI_READINESS_ESTABLISHED`.
- **C — XAI universe:** 389 unique G5-ready scopes, verified from the frozen ledger.
- **D — Exclusions:** Zeppelin Logistic Regression `C+T`, `P+T`, and `C+P+T` remain excluded.
- **E — Runtime:** Python 3.11.14; NumPy 2.4.6; SciPy 1.17.1; scikit-learn 1.9.0; XGBoost 3.2.0; LightGBM 4.6.0; Darwin x86_64.
- **F — SHAP:** no version selected; authoritative package metadata proves the current incompatibility chain. Status `SHAP_RUNTIME_VERSION_UNRESOLVED`.
- **G — Installation:** none; before/after package inventories are identical.
- **H — Explainers:** analytical LR logit decomposition; exact RF TreeSHAP positive-class output; exact XGBoost/LightGBM TreeSHAP native raw margin; analytical LR fusion decomposition.
- **I — Scales:** LOGIT, frozen RF positive-class model output, NATIVE_RAW_MARGIN, and META_LOGIT respectively.
- **J — TRAIN background:** same-project TRAIN only, maximum 256, deterministic stratification and SHA-256 ordering, seed 20260901.
- **K — T1 foreground:** T1 only, maximum 256, performance/explanation independent, no labels, deterministic frozen-decision strata and SHA-256 ordering.
- **L — Local cases:** foreground subset, maximum 8, frozen-decision 4/4 allocation with deterministic reallocation; never selected after attribution.
- **M — Budget:** maximum 256 TRAIN background and 256 unique T1 foreground rows per scope; local 8 are a subset; fidelity on every explained row; no T2.
- **N — LR fidelity:** decomposition residual <= `1e-10*(1+abs(eta))`; sigmoid residual <= `1e-10`.
- **O — TreeSHAP additivity:** residual <= `1e-6*(1+abs(model_output))`; approximate mode forbidden.
- **P — TEXT:** only G5-aligned frozen TF-IDF state; exact vocabulary/token-column/IDF/order/predictor linkage; no semantic-intent inference.
- **Q — Correlation:** TRAIN-only CODE/PROCESS Spearman groups at absolute rho >=0.70, connected-component grouping, individual and grouped summaries.
- **R — Stability:** seeds 20260901–20260920; deterministic maximum difference 1e-12; top-k 3/10 with Jaccard, Spearman, sign agreement, and total variation.
- **S — Cross-model:** at least three comparable eligible families; frozen 0.60/0.70/0.80/0.25 thresholds.
- **T — Projects:** fewer than three is insufficient; stability requires at least 11/14 projects and at most one material reversal.
- **U — E3:** RAW identity and frozen isotonic inspection remain separate from E1/E2; no feature attribution through calibration.
- **V — LIME:** excluded from primary XAI; exploratory use requires separate authorization.
- **W — Counterfactuals:** excluded from Sprint 56 primary XAI and require a separate protocol.
- **X — T1:** no T1 rows accessed in this freeze; future use is separately counted `TECHNICAL_EXPLANATION_ACCESS`; historical counters remain 1/1/false.
- **Y — T2:** access count 0; state `DENY_SEALED_REVIEWER_RESERVE`.
- **Z — Sprint 56 prerequisites:** resolve and prospectively amend the SHAP version/runtime conflict without silent predictive-stack mutation; freeze package provenance and hashes; obtain separate execution authorization; verify all parent hashes and thread controls; materialize populations before attribution; retain zero T2 access.

Timestamp: `2026-09-04T09:23:24.822413+00:00`. XAI, SHAP, LIME, analytical attribution, T1 explanation, T2 access, fitting, reconstruction, recalibration, and metric-recomputation counts are all zero.
