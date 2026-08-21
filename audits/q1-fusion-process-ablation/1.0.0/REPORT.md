# Sprint 10.8.2.35 — Predeclared Fusion Sensitivity, PROCESS Ablation, and Paired Inference Audit

## 1. Scientific decision

`SPRINT_10.8.2.35_GO_WITH_LIMITATIONS`

Development-only execution is methodologically admissible and reproducible. The decision remains limited because five origins cannot yield a two-sided exact sign-test p-value below 0.05, no calibration was fitted, and no final TEST boundary was opened.

## 2. Starting branch and HEAD

Started from clean, synchronized local `main` at `b85cbb318eb8157bc30459859142ee29db681cca`; work executed on `sprint-10/q1-fusion-process-ablation`.

## 3. Scientific questions

The audit asks whether PROCESS degradation is attributable to its frozen representation, fixed equal-weight fusion, absent complementarity, or a combination; secondarily, whether strictly nested out-of-time learned stacking improves on fixed fusion.

## 4. Frozen governance

Only canonical TRAIN+VALIDATION development identities were eligible. Sprint 34 memberships, labels, boundaries, seed, base estimators, preprocessing locality, 0.5 threshold, and uncalibrated status were frozen. Candidate ablations, weights, stacking blocks, and inference family were configuration-declared before this execution.

## 5. PROCESS feature lineage

`parent_count` describes commit topology; `is_merge_commit` is the derived multi-parent topology flag; `has_prior_history` indicates at least one parent; `prior_project_commit_count` is the exact ancestors-only history count. All are observation-time available and exclude descendants.

## 6. PROCESS ablation declaration and results

The frozen family contains the full representation, four individual leave-one-feature-out variants, topology-only, and history-only. Each uses origin-training-only scaling and the frozen PROCESS RF. Results retain every sign. Mean ROC-AUC / PR-AUC:

| Candidate | P alone | C+P+T with ablated P |
|---|---:|---:|
| P_full | 0.4836 / 0.0751 | 0.7368 / 0.2325 |
| P_without_parent_count | 0.4863 / 0.0753 | 0.7388 / 0.2341 |
| P_without_is_merge_commit | 0.4844 / 0.0753 | 0.7404 / 0.2349 |
| P_without_has_prior_history | 0.4839 / 0.0753 | 0.7377 / 0.2333 |
| P_without_prior_project_commit_count | 0.5000 / 0.0803 | 0.7496 / 0.2447 |
| P_topology_only | 0.5000 / 0.0803 | 0.7496 / 0.2447 |
| P_history_only | 0.4872 / 0.0755 | 0.7379 / 0.2332 |

Ablations diagnose sensitivity of the current representation; they do not authorize outcome-driven feature removal or PROCESS redesign.

The degradation is concentrated in `prior_project_commit_count` under the frozen PROCESS RF: removing it (or retaining topology alone) makes PROCESS exactly non-discriminating by ROC-AUC (0.5000) and makes the C+P+T ranking identical to C+T. The other individual removals recover only part of the loss. This supports a representation-specific problem, while the absence of improvement beyond C+T provides no evidence of useful incremental PROCESS signal.

## 7. Fixed-fusion sensitivity declaration

C+T candidates were equal 50/50, CODE-heavy 60/40, and TEXT-heavy 40/60. C+P+T candidates were equal thirds, PROCESS-low 40/20/40, and PROCESS-minimal 47.5/5/47.5. No continuous or expanded search was performed.

## 8. Fixed-fusion results

Mean ROC-AUC / PR-AUC:

| Candidate | Result |
|---|---:|
| CT_equal | 0.7496 / 0.2447 |
| CT_code_60 | 0.7481 / 0.2493 |
| CT_text_60 | 0.7484 / 0.2346 |
| CPT_equal | 0.7368 / 0.2325 |
| CPT_process_20 | 0.7455 / 0.2405 |
| CPT_process_05 | 0.7494 / 0.2443 |

The family is a specification-sensitivity analysis, not an optimized weight search. The highest mean within a declared family is reported descriptively only.

C+T is robust within the narrow declared family: neither 60/40 variant jointly improves ROC-AUC and PR-AUC. In contrast, progressively downweighting PROCESS recovers the C+P+T deficit monotonically on both primary means; 5% PROCESS reaches 0.7494/0.2443, essentially the 0.7496/0.2447 C+T reference. Thus equal-weight fusion amplifies the weak PROCESS representation, but changing fixed weights does not reveal complementary PROCESS value.

## 9. Learned-stacking protocol

For every outer frozen origin, each project-specific outer training prefix was divided into three forward nested blocks (1/2→2/3, 2/3→5/6, 5/6→1). Each base model and all preprocessing were refit on the earlier prefix and predicted only the later block. Pooled OOT probabilities trained fixed logistic meta-learners for C+T and C+P+T. Base models were then fit on the complete admissible outer past and the meta-learner scored the unchanged outer evaluation block.

## 10. Learned-stacking results

STACK_CT: 0.7495 / 0.2422; STACK_CPT: 0.7490 / 0.2415. These are uncalibrated development results at the frozen threshold.

STACK_CT does not improve the fixed C+T reference and adds complexity. STACK_CPT reproducibly recovers most of the equal-weight C+P+T deficit (five of five origins for both primary metrics), but does not exceed fixed C+T on the mean primary metrics. Learned fusion therefore mitigates dilution; it does not establish useful complementary PROCESS signal or justify a more complex architecture.

## 11. Paired-inference declaration

The sole family is the exact two-sided paired sign test, with exact zero differences excluded from the binomial count. Mean and median signed effects preserve magnitude descriptively; the test itself uses direction. With five pairs, the minimum attainable two-sided p-value is 0.0625.

## 12. Paired comparisons

All primary and predeclared ablation contrasts are in `paired_inference.json`. Key discrimination contrasts:

| Contrast | Metric | Mean difference | W/T/L | Exact p |
|---|---|---:|---:|---:|
| CT_equal_vs_C | ROC_AUC | +0.0459 | 5/0/0 | 0.0625 |
| CT_equal_vs_C | PR_AUC | +0.0247 | 4/0/1 | 0.3750 |
| CT_equal_vs_T | ROC_AUC | +0.0462 | 5/0/0 | 0.0625 |
| CT_equal_vs_T | PR_AUC | +0.0719 | 5/0/0 | 0.0625 |
| CPT_equal_vs_CT_equal | ROC_AUC | -0.0128 | 0/0/5 | 0.0625 |
| CPT_equal_vs_CT_equal | PR_AUC | -0.0122 | 0/0/5 | 0.0625 |
| CT_code_60_vs_CT_equal | ROC_AUC | -0.0015 | 3/0/2 | 1.0000 |
| CT_code_60_vs_CT_equal | PR_AUC | +0.0046 | 4/0/1 | 0.3750 |
| CT_text_60_vs_CT_equal | ROC_AUC | -0.0012 | 2/0/3 | 1.0000 |
| CT_text_60_vs_CT_equal | PR_AUC | -0.0100 | 0/0/5 | 0.0625 |
| CPT_process_20_vs_CPT_equal | ROC_AUC | +0.0087 | 5/0/0 | 0.0625 |
| CPT_process_20_vs_CPT_equal | PR_AUC | +0.0080 | 5/0/0 | 0.0625 |
| CPT_process_05_vs_CPT_equal | ROC_AUC | +0.0126 | 5/0/0 | 0.0625 |
| CPT_process_05_vs_CPT_equal | PR_AUC | +0.0118 | 5/0/0 | 0.0625 |
| STACK_CT_vs_CT_equal | ROC_AUC | -0.0001 | 2/0/3 | 1.0000 |
| STACK_CT_vs_CT_equal | PR_AUC | -0.0025 | 2/0/3 | 1.0000 |
| STACK_CPT_vs_CPT_equal | ROC_AUC | +0.0122 | 5/0/0 | 0.0625 |
| STACK_CPT_vs_CPT_equal | PR_AUC | +0.0090 | 5/0/0 | 0.0625 |

No contrast supports statistical superiority at alpha 0.05; descriptive direction and inferential evidence are intentionally separated.

## 13. Temporal stability

Every comparison pairs identical O1–O5 evaluation memberships. Direction counts and full origin effects are retained in the paired artifact; five origins limit resolution and transport claims.

## 14. Leakage audit

No outcome moved a boundary or changed the declared family. Nested prediction memberships are disjoint from their fit memberships, preserve project-local forward order, and are fully persisted. Vocabulary, scaling, base estimation, and meta-learning remain local to admissible past data. No target proxy or bug/fix keyword feature was added.

## 15. Reproducibility/fitted-state evidence

Five bundles persist outer base estimators/preprocessors, all ablation estimators/scalers, nested base fitted states, meta-learners, schemas, class order, null calibrator, threshold, memberships, seeds, runtime, SHA-256 values, scientific-state digests, and reload prediction equivalence.

## 16. TEST governance

TEST predictive scoring, selection, threshold optimization, calibration fitting, and XAI were all zero. Canonical rows were identity-filtered against TRAIN+VALIDATION before JSON deserialization, using the inherited Sprint 34 development loader.

## 17. Execution ledger

- model_fits: **100**
- base_model_fits: **90**
- meta_learner_fits: **10**
- base_prediction_operations: **90**
- development_configuration_origin_evaluations: **110**
- development_origin_scoring: **110**
- TEST_scoring: **0**
- TEST_predictive_scoring: **0**
- TEST_based_model_selection: **0**
- TEST_based_threshold_optimization: **0**
- TEST_calibration_fitting: **0**
- calibration_fits: **0**
- XAI_executions: **0**
- XAI_on_TEST: **0**
- external_dataset_acquisitions: **0**
- hyperparameter_searches: **0**
- continuous_weight_optimizations: **0**
- threshold_optimizations: **0**
- temporal_origins: **5**
- nested_temporal_blocks_per_origin: **3**
- failed_or_undefined_evaluations: **0**

## 18. Quality gates

- Pre-execution focused Sprint 35 protocol tests: **7 passed, 0 failed, 0 skipped**.
- Focused Sprint 35 plus relevant temporal/data/modality/fusion/calibration governance tests: **55 passed, 0 failed, 0 skipped**.
- Full repository pytest: **1,378 passed, 0 failed, 1 skipped**. The skip is `test_sha256_repository_acquisition_if_supported`, because the installed Git lacks SHA-256 repository support; it is not classified as passed.
- Python `compileall` over `src`, `scripts`, and `tests`: **PASS**.
- Ruff on all Sprint 35 Python files: **PASS**.
- Full repository Ruff: **PASS** after mechanical import/format corrections to three baseline files; the corrections do not alter scientific behavior or historical artifacts.
- `git diff --check`: **PASS**.

## 19. Limitations

Only five dependent temporal origins are available; exact sign inference has low power and cannot establish superiority at alpha 0.05. Development evidence is not final or externally validated. Raw commit text retains its inherited semantic-proxy limitation. PROCESS ablations diagnose the frozen four-feature representation but do not explore redesigned features. Scores are uncalibrated and threshold-dependent metrics remain tied to 0.5.

## 20. Article-evidence mapping

Machine-readable mapping is in `article_evidence_mapping.json`. Claims must be framed as development-only sensitivity, temporal direction, and reproducibility evidence—not final superiority.

## 21. Exact recommended next sprint

Sprint 10.8.2.36 — Predeclared forward DEVELOPMENT calibration and decision-curve readiness audit for the simplest leakage-safe C+T reference justified jointly by Sprint 35 robustness, paired direction, reproducibility, and complexity; keep TEST sealed, fit no final calibrator, and do not select an architecture from mean AUC alone.
