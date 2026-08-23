# Sprint 10.8.2.38 — Frozen DEVELOPMENT Practical-Utility Execution

## 1. Scientific objective

Evaluate the frozen MMSDP-XAI DEVELOPMENT predictor under the exact Sprint 37 decision thresholds and normalized defect-misclassification cost scenarios, without outcome-driven modification.

## 2. Starting repository state

Branch `sprint-10/q1-development-practical-utility-execution`, starting HEAD `488921fcfd2f8081748986930d77dce6a0d38ab2`, clean starting worktree. Changes remain uncommitted.

## 3. Frozen protocol provenance

Source: `audits/q1-development-practical-utility-protocol/1.0.0`. The 19 thresholds, five FN/FP ratios, three calibration states, formulas, baselines, memberships, inference policy, and advancement rule were read from committed machine-readable artifacts and were not modified.

## 4. Protocol-integrity verification

**PASS.** All Sprint 37 manifest hashes matched; threshold, cost, formula, and advancement declarations agreed with `protocol.json`. Protocol hash count: 13.

## 5. DEVELOPMENT temporal memberships

The five Sprint 37 membership digests match Sprint 36. No origin was dropped or pooled.

- O1: N=2018, prevalence=0.104063; DCA dominates both in 25/57 cells; cost wins/ties/losses=89/66/130 of 285.
- O2: N=2228, prevalence=0.093806; DCA dominates both in 33/57 cells; cost wins/ties/losses=104/66/115 of 285.
- O3: N=2319, prevalence=0.073307; DCA dominates both in 32/57 cells; cost wins/ties/losses=122/54/109 of 285.
- O4: N=2174, prevalence=0.068077; DCA dominates both in 38/57 cells; cost wins/ties/losses=143/47/95 of 285.
- O5: N=2191, prevalence=0.068005; DCA dominates both in 13/57 cells; cost wins/ties/losses=43/122/120 of 285.

## 6. Leakage audit

**PASS. TEST REMAINED SEALED.** TEST scoring, TEST label access, TEST probability loading, threshold optimization, hyperparameter search, model refit, calibration fit/selection, XAI, and external-data acquisition counters are all zero. DEVELOPMENT scoring reconstructed probabilities from frozen Sprint 36 persisted estimator/calibrator bundles.

## 7. Decision-curve results

All 285 origin × state × threshold cells were evaluated. `decision_curve_results.csv` retains confusion counts, explicit undefined precision/MCC states, model and baseline net benefit, differences, and dominance flags. Cell-count summaries are descriptive across the complete frozen grid and are not threshold selections.

- UNCALIBRATED: all five origins dominate both baselines at thresholds 0.05, 0.10, 0.15, 0.20, 0.25.
- PLATT: all five origins dominate both baselines at thresholds 0.10, 0.15, 0.20.
- ISOTONIC: all five origins dominate both baselines at thresholds 0.05, 0.10, 0.15.

## 8. Practical-utility / cost results

All 1,425 origin × state × threshold × ratio cells were evaluated. Costs follow `FP + r*FN`, normalized by N. Treat None and Treat All costs and absolute/relative differences are retained. Ratios are normalized sensitivity scenarios, not measured monetary or industrial costs.

- FN/FP=1: wins/ties/losses=59/113/113 of 285 frozen cells.
- FN/FP=2: wins/ties/losses=113/91/81 of 285 frozen cells.
- FN/FP=5: wins/ties/losses=156/93/36 of 285 frozen cells.
- FN/FP=10: wins/ties/losses=148/56/81 of 285 frozen cells.
- FN/FP=20: wins/ties/losses=25/2/258 of 285 frozen cells.

The ratio pattern is non-monotonic: improvement cells increase from ratios 1 to 5–10, but ratio 20 is predominantly unfavorable (258/285 losses). This contradiction is retained rather than used to select a threshold or cost scenario.

## 9. Origin-level behavior

- O1: N=2018, prevalence=0.104063; DCA dominates both in 25/57 cells; cost wins/ties/losses=89/66/130 of 285.
- O2: N=2228, prevalence=0.093806; DCA dominates both in 33/57 cells; cost wins/ties/losses=104/66/115 of 285.
- O3: N=2319, prevalence=0.073307; DCA dominates both in 32/57 cells; cost wins/ties/losses=122/54/109 of 285.
- O4: N=2174, prevalence=0.068077; DCA dominates both in 38/57 cells; cost wins/ties/losses=143/47/95 of 285.
- O5: N=2191, prevalence=0.068005; DCA dominates both in 13/57 cells; cost wins/ties/losses=43/122/120 of 285.

## 10. Cross-origin stability

The full origin-level rows are retained in `origin_stability.json`; aggregate means are not treated as robustness when origins disagree.

## 11. Calibration-state comparison

- UNCALIBRATED: DCA dominates both in 46/95 cells; cost wins/ties/losses=132/151/192.
- PLATT: DCA dominates both in 48/95 cells; cost wins/ties/losses=152/139/184.
- ISOTONIC: DCA dominates both in 47/95 cells; cost wins/ties/losses=217/65/193.

These practical-utility results do not rewrite Sprint 36 calibration/discrimination evidence. Better calibration does not imply better utility, and any utility gain does not erase discrimination degradation.

## 12. Baseline comparison

Both Treat None / Flag None and Treat All / Flag All are present for every DCA and cost cell. Strict improvement, exact ties, and degradation are separately counted.

## 13. Advancement-rule evaluation

Experiment execution status: **SUCCESS / VALID**.

Advancement decision: **SPRINT_10.8.2.38_ADVANCEMENT_UNRESOLVED**. The frozen rule is qualitative and joint but contains no complete criterion-state to outcome mapping. The fail-closed evaluator therefore cannot derive an advancement outcome. `ADVANCEMENT_UNRESOLVED` does not mean experimental failure; it means the frozen governance declaration is insufficient to derive an advancement decision mechanically. No final candidate was selected and TEST opening remains unauthorized.

## 14. Reproducibility evidence

Deterministic rerun equivalence: **PASS** for the calculation artifacts. Runtime, inputs, hashes, memberships, states, seed, formulas, and output hashes are in `reproducibility_manifest.json`.

## 15. Quality gates

Focused Sprint 38 tests: **12 passed, 0 failed**. Relevant temporal/calibration/evaluation/governance/reproducibility/leakage tests: **231 passed, 0 failed**. Full pytest: **1,406 passed, 1 skipped, 0 failed**. Sprint 38 Ruff: **PASS, 0 findings**. Full-repository Ruff diagnostic: **FAIL, 31 pre-existing E501 findings in 2 unrelated files** (`scripts/validate_q1_experimental_validity_contract.py` and `validation/18C/sample_review_package.py`); neither file was modified. Python compilation: **PASS, 2 files**. `git diff --check`: **PASS, 0 errors**.

## 16. Limitations

Only five DEVELOPMENT origins are available. Cost ratios are normalized scenarios rather than observed industrial costs. Utility is conditional on the frozen model and these DEVELOPMENT data. Calibration and discrimination remain distinct. Cross-origin heterogeneity limits generalization claims. No external dataset or XAI evidence was generated. TEST is unopened. The Sprint 37 inference policy names BH-FDR but does not predeclare a statistic or concrete comparison family, so no post-hoc inferential test was invented; analysis is descriptive with full magnitude and dispersion.

## 17. Scientific decision

Experiment execution status: **SUCCESS / VALID**.

Advancement decision: **SPRINT_10.8.2.38_ADVANCEMENT_UNRESOLVED**. Within the frozen DEVELOPMENT origins, evidence is mixed/heterogeneous across thresholds, ratios, origins, and probability states. The unresolved advancement decision reflects the missing frozen outcome-mapping function, not experimental failure. This is not evidence of external validity, production readiness, or industrial cost savings. TEST REMAINED SEALED.

## 18. Exact recommended next sprint

**Sprint 10.8.2.39 — Prospective advancement-governance outcome-mapping protocol.** Prospectively predeclare criterion-state semantics and a complete deterministic mapping to advancement outcomes for future governance evaluations. Sprint 39 does not change or reinterpret Sprint 38 evidence, fit models, optimize thresholds, access TEST, or perform XAI.
