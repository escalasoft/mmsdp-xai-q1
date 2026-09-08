# Sprint 56.2 — Primary XAI Authorization and Population Freeze

`PRIMARY_XAI_T1_SELECTION_CONTRACT_FAILURE`

State/runtime governance is verified. **The population freeze is incomplete, not ready for scientific execution.** No scientific XAI or population selection was executed. Empty population/group JSONL files explicitly mean unavailable outputs.

## A–H. Inherited state, universe and readiness

- **A. Branch / HEAD:** `sprint-10/q1-primary-xai-execution` / `89fe7e1c2da425ea63427d1d699d6f8a531e8c6f`. No commit or push.
- **B. Inherited Sprint56.1:** `PRIMARY_XAI_ISOLATED_RUNTIME_SMOKE_TEST_PASS`; `TRAIN_ONLY_RUNTIME_VALIDATION_NO_SCIENTIFIC_XAI_CLAIM`. Sprint54 `MIXED_CONFIRMATORY_EVIDENCE` and Sprint55 closed/G1–G5 readiness remain preserved.
- **C. Authorized universe:** exactly 389 unique scopes, included for governance/population freeze; scientific execution is false for every row.
- **D. Exclusions:** exactly three: apache/zeppelin | Logistic Regression | C+T; P+T; C+P+T. No rescue or new exclusions.
- **E. Readiness:** 389/389 `READY_VERIFIED`; 0 `NOT_READY`. The 389 distinct required executable states include 168 final bases and 221 fusion meta-learners. Every reference resolves through canonical metadata, external registry SHA256 and G1–G5 PASS. No deserialization or model query occurred. Load compatibility for untested states is not inferred from representative smoke success.
- **F–G. Methods:** 168 unimodal E1 and 221 multimodal E2 scopes:

| Algorithm | Role | Method | Count |
|---|---|---|---:|
| LightGBM | E1 | EXACT_TREESHAP_NATIVE_RAW_MARGIN | 42 |
| LightGBM | E2 | ANALYTICAL_LR_FUSION_DECOMPOSITION | 56 |
| Logistic Regression | E1 | ANALYTICAL_LINEAR_LOGIT_DECOMPOSITION | 42 |
| Logistic Regression | E2 | ANALYTICAL_LR_FUSION_DECOMPOSITION | 53 |
| Random Forest | E1 | EXACT_TREESHAP_POSITIVE_CLASS_OUTPUT | 42 |
| Random Forest | E2 | ANALYTICAL_LR_FUSION_DECOMPOSITION | 56 |
| XGBoost | E1 | EXACT_TREESHAP_NATIVE_RAW_MARGIN | 42 |
| XGBoost | E2 | ANALYTICAL_LR_FUSION_DECOMPOSITION | 56 |

- **H. Runtime binding:** `.venv-xai-s56`; Sprint56.1 lock SHA256 `324707477b91d36ab382c0d367324aa1d11aea3fa06a6a6a081693e14731c9ee`. Python 3.11.14, NumPy 2.3.5, SciPy 1.17.1, scikit-learn 1.9.0, XGBoost 3.2.0, LightGBM 4.6.0, SHAP 0.51.0, Numba 0.62.1, llvmlite 0.45.1, joblib 1.5.3, cloudpickle 3.1.2. Exact installed package inventory matches; predictive inventory unchanged. Any runtime amendment must be prospective. All required execution thread controls remain 1.

The external store remains 5,649 objects / 2,139,594,110 bytes, zero missing references/orphans. Every object hash was checked before and after; snapshot `5e8ebc15b2377045683978763ecebdb621e5af24cbffddeb0b62d9cf1653dea9`. Sprint55 and Sprint56.1 manifests and artifact bytes are unchanged.

## I–M. Populations and representation

- **I. TRAIN references actually frozen:** 0. Planned ceiling 256 per scope, label-stratified only on TRAIN; no fabricated selected identities or membership hashes.
- **J. T1 global foreground actually frozen:** 0. Planned ceiling 256 per project shared by its scopes. Historical G5 aggregate counts imply a prospective capacity of 2450 distinct identities, but this is not a selected population.
- **K. Local cases actually frozen:** 0. Planned ceiling 8 per scope, subset of its project foreground. No correctness, confidence or label strata: Sprint55 explicitly sets T1 label use to false. The identity-only unstratified fallback is documented before any output; a shared project foreground takes precedence over Sprint55's per-model selection-key scope under the explicit Sprint56.2 instruction.
- **L. Feature/TEXT registry:** 168 final-base feature orders and all 56 TEXT representations verified. Vocabulary, IDF float64 bytes, token-column map, tokenizer parameters, exact feature order and canonical predictor dimensions agree with immutable persisted metadata. CODE order: la, ld, nf, nd, ns, ent. PROCESS order: ndev, age, nuc, aexp, arexp, asexp. Fusion preserves applicable C/P/T order. This is metadata/state readiness, not newly executed model transformation validation.
- **M. Correlated groups actually derived:** not computed. The empty JSONL is not evidence of zero correlated groups. Frozen rule: same-project TRAIN only, absolute Spearman rho >=0.70, connected components, omit singletons, record signs/magnitudes; no causal or SHAP redefinition.

### Access blocker

The available original membership/identity/CODE/PROCESS files are single gzip streams combining TRAIN, VALIDATION, T1 and T2. The generator writes all project rows sequentially. Existing readers either deserialize all partition identities including T2 or scan mixed payload rows. The Sprint56.1 first-project TRAIN-prefix method cannot reach later projects without traversing earlier T2 sections. No relevant segregated source or independent access index was located during metadata-only discovery.

The user's section24 explicitly states: **“No T2 identity read. No T2 feature read. No T2 label read.”** No mixed stream was opened, filtered, fully hashed, indexed or traversed in this sprint. Discarding T2 after reading it would not satisfy that boundary. The source-path question was sent while state/contract work proceeded; no permission to relax the rule was inferred.

Completion requires verifiable, independently addressable TRAIN identities/classes/CODE/PROCESS values and T1 identity-only metadata for all 14 projects, matching the frozen per-project membership digests and original feature provenance. Creating such an export by accessing T2 is not authorized here. See `population_source_access_blocker.json` for the exact input contract.

## N–R. Frozen prospective contracts

- **N. Budgets:** TRAIN <=256; global T1 <=256 per project; local <=8 per scope within foreground; every explained row gets fidelity checks. Total primary-plus-stability row evaluations <=5,120 per scope, including all repeated evaluations. No post-output increases.
- **O. Fidelity:** LR/fusion absolute residual <=1e-10*(1+absolute logit); sigmoid <=1e-10; exact TreeSHAP <=1e-6*(1+absolute model output); applicable global reconstruction <=1e-12. Approximate SHAP false. RF positive-class probability; LR logit; XGB/LGB native raw margin; fusion meta-logit. No silent scale conversion.
- **P. Stability:** seeds 20260901–20260920, unchanged populations, top-k 3/10, repeat attribution difference <=1e-12; Jaccard >=0.60, Spearman >=0.70, sign agreement >=0.80, TV <=0.25. PASS/MIXED/FAIL/INSUFFICIENT_EVIDENCE definitions frozen; undefined diagnostics are not silently omitted.
- **Q. Heterogeneity:** >=3 comparable families; every eligible family pair retained. Stable project pattern requires >=11/14 PASS and <=1 material reversal, with explicit prospective reversal/alignment definitions. Project/model dependence and insufficient evidence take precedence over universal claims. TEXT cross-project pooling requires strict representation and semantic alignment.
- **R. Schemas:** E1/E2 JSON Schema definitions, exact required provenance fields, separate E3 mapping, deterministic global ranking and figure lineage are frozen. Future fused reference means are not computed now because they require prohibited model queries. E3 distribution remains 375 RAW /14 ISOTONIC. Figures are policy-only; no plots or attributions exist.

## S–Z. Counters and disposition

- **S. T1 population-freeze metadata access:** 1, the aggregate `t1_identity_integrity.json` registry read during source discovery (count/digest/source path only). Actual T1 identity and label rows read: 0; no T1 population stream opened.
- **T. T1 model queries:** 0.
- **U. Scientific SHAP, analytical attribution and primary XAI executions:** 0. TRAIN model/attribution executions in Sprint56.2 also 0.
- **V. T2:** all access/identity/feature/label counters 0; `DENY_SEALED_REVIEWER_RESERVE`.
- **W. Predictive metric recomputation:** 0.
- **X. Artifact mutations, reconstruction, refit, retraining, recalibration and installations:** 0. Historical Sprint54 access/scoring remains 1/1 and T1 rerun false.
- **Y. Sprint56.3:** not authorized. First resolve source access and finish/validate Sprint56.2, then obtain separate human scientific-execution authorization.
- **Z. Scientific disposition:** governance/state readiness completed; population freeze blocked/incomplete; no scientific XAI result or readiness-for-execution claim.

## Validation

`{"counter_audit_note": "Aggregate T1 identity-registry discovery access is counted conservatively as 1 metadata access; actual T1 identity/label rows remain zero. Counter test updated to distinguish metadata registry access from actual population reads.", "deselected": 3, "excluded_tests": {"test_gitignore_is_exact_narrow_and_registry_remains_visible": "Historical Sprint55 uncommitted-size assertion; current narrow-ignore test from Sprint56.1 passes", "test_isotonic_state_digests_match_persisted_source_and_block7_linkage": "Out-of-scope development probability ledger", "test_parent_hashes_tolerances_and_calibrators_remain_unchanged": "Historical T1 prediction payload outside identity-only authorization"}, "failed": 0, "full_JSON_Schema_engine_installed_or_used": false, "git_diff_check": "PASS", "guard_enabled": true, "passed": 64, "real_population_checks": {"T1_only_membership": "NOT_EXECUTED_SOURCE_UNAVAILABLE", "TRAIN_correlated_groups": "NOT_EXECUTED_SOURCE_UNAVAILABLE", "TRAIN_only_membership": "NOT_EXECUTED_SOURCE_UNAVAILABLE", "local_subset": "NOT_EXECUTED_SOURCE_UNAVAILABLE"}, "schema_validation": "Focused validator for the exact frozen scalar schema subset, including algorithm/method/scale bindings; no package installation", "status": "GOVERNANCE_AND_CONTRACT_TESTS_PASS_REAL_POPULATIONS_NOT_FROZEN", "verified": ["389 unique scopes and 3 exclusions", "G1-G5 links and required immutable object hashes", "runtime lock binding and unchanged predictive inventory", "method/scale assignments", "168 feature orders and 56 exact TFIDF representations", "synthetic TRAIN balanced selection, SHA256 ordering, T1 identity-only selection and local subset", "reject forbidden partitions, labels, prediction signals and immutable writes", "fidelity, budgets, stability, heterogeneity and E3 distribution", "complete E1/E2 schema with scalar/provenance validation", "fail-closed unavailable population status", "Sprint55/Sprint56.1 evidence preserved", "exact manifest"]}`

Tests distinguish verified governance/synthetic-selector behavior from unavailable real populations. Actual TRAIN/T1 membership selection, local subset and correlated-group data validation are **NOT EXECUTED**, never vacuously PASS. Relevant Sprint55/Sprint56.1 regressions use only permitted evidence; exclusions are recorded explicitly. No earlier evidence or tests were edited.

READY FOR HUMAN REVIEW BEFORE PRIMARY XAI SCIENTIFIC EXECUTION
