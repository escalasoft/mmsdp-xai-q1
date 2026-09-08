# Sprint 10.8.2.56.3A — Prospective Complementary E1 Protocol Freeze

Disposition: **PROSPECTIVE_E1_PROTOCOL_FREEZE_BLOCKED**. The immutable package records the proposed contracts and audit outcome. A BLOCKED disposition means protocol acceptance has not passed; references below to frozen designs do not authorize their execution. Parent evidence remains untouched.

## A. Branch and parent

Branch `sprint-10/q1-prospective-e1-protocol-freeze`; HEAD `b3ecfa2b45ea6b83159508e0581c475237bc8c56`. Clean preflight; merge parents ['89fe7e1c2da425ea63427d1d699d6f8a531e8c6f', '4572ec9a6e231996df72f0aa3ec5e7bd9ffec14b']. Eleven packages present; metadata hashes verified. Scientific payload files were not opened to hash them.

## B. Scientific state preserved

Sprint54 predictive evidence closed; MIXED_CONFIRMATORY_EVIDENCE; historical T1 access/scoring 1/1. G5 equivalence is reconstructed-state evidence, never original Sprint54 serialization. E2 remains primary; E3 separate; historical E1 illustrative and recovery closed.

## C. E1 unit of analysis

Project × algorithm family × unimodal modality. Performance-independent scope-complete eligible universe.

## D. Eligible algorithm families

Logistic Regression, Random Forest, XGBoost, LightGBM

## E. Eligible modalities

CODE, PROCESS, TEXT; no pairwise/full multimodal feature attribution.

## F. Candidate scope universe

168 candidates across 14 projects. Classification: {'E1_PENDING_SCIENTIFIC_INPUT_PROVENANCE': 112, 'TEXT_E1_INELIGIBLE': 56}. 168 have parent reconstructed-state equivalence; zero are scientifically execution-eligible now. TEXT requires complete representation/alignment proof, not just an available vectorizer.

## G. E1 method mapping

LR analytical logit decomposition; RF exact positive-class probability TreeSHAP; XGBoost/LightGBM exact native raw-margin TreeSHAP. LIME/counterfactuals excluded. Runtime is the existing isolated Sprint56.1 lock.

## H. LR analytical contract

phi_j=beta_j*(x_j-mu_j); phi_0=intercept+sum(beta_j*mu_j). mu is the selected transformed TRAIN reference mean. Global importance mean|phi|; raw coefficient magnitude diagnostic only.

## I. TreeSHAP contract

Inherit tree_path_dependent, model_output=raw, data=None, approximate=False. Persisted TRAIN path counts define tree references; capped explicit TRAIN rows do not silently change the TreeSHAP estimand. RF class 1 probability; boosters raw margin. Every explained row checked.

## J. TRAIN background policy

At most 256 observed rows per project/modality, shared across families where representations permit. All if small, otherwise equal round-robin binary TRAIN-label strata if authorized; identity-only fallback. Seed 20260901, SHA-256 lexical ordering; no kmeans. Class balancing defines the reference estimand, not full-TRAIN prevalence.

## K. T1 global foreground policy

At most 256. T1_SELECTION_LABEL_BLIND; frozen predicted-decision strata if complete, otherwise identity-only. No labels, errors, metrics or attribution selection. Only exact authorized T1 representations; new populations cannot silently replace historical T1.

## L. Local case policy

At most eight, subset of global: four per available predicted class, high confidence, near threshold, median confidence, remaining integrity-supported extreme; deterministic ties and quota fallback. Correct/error annotation deferred to separate label permission after selection.

## M. TEXT contract

Exact vocabulary, IDF, tokenizer settings, column order, predictor alignment and row representations required. Missing proof means TEXT_E1_INELIGIBLE. Keep absent-token contributions where method produces them. No token-rank pooling or intent claims.

## N. CODE/PROCESS feature contract

Twelve authoritative features frozen with definitions, units/unknown units, transforms, sign limits, missing policies and provenance. Parent PROCESS replay semantics and age/entropy/recency unit details remain explicitly unresolved; no silent reclassification or invented Git proxy.

## O. Correlated-feature policy

TRAIN-only absolute Spearman rho>=0.70 connected components; no TEXT grouping. Sum member contributions per row before mean absolute group aggregation, plus within-group shares and cancellation diagnostics. Do not overinterpret small correlated rank swaps.

## P. Fidelity

Inherited LR residual <=1e-10*(1+|eta|), sigmoid bound 1e-10; trees <=1e-6*(1+|output|); global reconstruction 1e-12. Zero unexplained fraction permitted. PASS/MIXED/FAIL/NOT_TESTED exact rules; only complete PASS admitted.

## Q. Stability

Seeds 20260901–20260920; identical populations, all 190 repeat pairs, deterministic difference<=1e-12. Top3/top10; Jaccard>=.60, Spearman>=.70, sign>=.80, TV<=.25 on comparable support. Degenerate metrics are insufficient, not passes. No claim of sampling robustness from identical reruns.

## R. Heterogeneity

Within-project cross-model, within-model cross-project, modality synthesis. >=3 comparable families; inherited cross-project >=11 passing projects and <=1 material reversal. Raw cross-scale pooling forbidden; universal claim requires all14/all4 with no reversal. Descriptive primary analysis.

## S. E1–E2 continuity

Features -> representation -> base model -> probability -> fusion -> multimodal prediction. Architectural continuity is design-level; directional/project/model labels require exact linked future evidence. Never propagate/add E1 SHAP values through E2 or equate feature importance with modality contribution.

## T. E1–E2 bridge

Compare stable E1 patterns and strongest E2 modality descriptively, only with exact common chain. Five bridge statuses distinguish consistency, partial consistency, divergence, insufficient E1 and insufficient E2. Historical/prospective panels cannot imply a shared row without proof.

## U. Figures

Eight frozen families: E1-G1,G2,G3,L1,L2,C1,T1,E2. Every panel requires counts, family, modality, scale, normalization, omissions and descriptive label. No figures generated; correct/error L2 conditional on separate label authorization.

## V. Q1 sufficiency gate

Eighteen criteria, hard provenance/fidelity/repeatability/completeness/traceability gates, explicit small-sample and multi-project/family coverage rules. Four future E1_Q1 dispositions defined but none assigned now. Successful SHAP execution alone never suffices.

## W. Governance and counters

All current scientific execution/access/mutation counters zero; historical predictive counters 1/1. T2 DENY_SEALED_REVIEWER_RESERVE, future budget0. AUTH-E1-1 through12 plus source proof and explicit human approval required. Future budgets:256 TRAIN,256 unique T1,8 local subset,20 repeats,5120 attribution row evaluations and at most5120 direct model row evaluations.

## X. Threats to validity

- Reconstructed predictors are not original Sprint54 serialized states
- Model explanation is not a causal software-engineering mechanism
- Correlated features redistribute attribution
- TEXT association does not establish semantic developer intent
- Cross-project vocabularies and token semantics differ
- Eligibility failures reduce project/modality coverage
- RF probability and LR/boosted logit-margin scales differ
- Attribution magnitudes require justified normalization before cross-model comparison
- Local explanations are case-specific
- E2 modality contribution is not E1 feature importance
- ApacheJIT benchmark-defined observed labels are not independently verified-clean ground truth
- One benchmark family limits external generalization
- Balanced capped reference/foreground defines a sample-specific estimand
- Identical deterministic repetitions do not establish sampling or background robustness
- Historical input provenance remains unresolved and cannot be repaired by policy wording

## Y. Prohibited claims

- causal defect causes
- causal developer behavior
- semantic intent from TEXT
- universal software-defect mechanisms
- universal feature superiority
- universal multimodal superiority
- reconstructed states are original Sprint54 models
- unvalidated end-to-end E1 decomposition of E2
- SHAP proves performance improvement
- largest E1 feature caused largest E2 modality contribution

## Z. Final disposition / next action

PROSPECTIVE_E1_PROTOCOL_FREEZE_BLOCKED. Contracts are prepared and persisted for review, with zero currently executable scopes. Parent integrity finding: {"actual_sha256": "b9d17eb93ab80e96d9eae4d0d924511ed9aa23e5ce53c569274913ceb7100ab6", "manifest_sha256": "8c4e2582fc9bc11d2d417f8e785089eebe44c6390d13343e9200b1f639eda4de", "path": "audits/q1-primary-xai-runtime-smoke/1.0.0/validation-initial-output.txt", "scope": "Historical validation log; original bytes not recoverable from current manifest alone", "status": "FAIL_MANIFEST_MISMATCH"}. Resolve the inherited manifest discrepancy through a separately reviewed provenance amendment; do not rewrite parent artifacts. Then re-review 56.3A before any next sprint. Planned next sprint: Sprint 10.8.2.56.3B — Prospective E1 Scientific Input Provenance and Population Eligibility Gate. Human review, legitimate source proof, representation/identity alignment and separate population-access authorization are prerequisites. If no legitimate source is available, stop for design review; do not reopen historical recovery, train, refit, recalibrate or start attribution. See validation_results.json for the sealed validation record.

BLOCKED — DO NOT START PROSPECTIVE E1 EXECUTION
