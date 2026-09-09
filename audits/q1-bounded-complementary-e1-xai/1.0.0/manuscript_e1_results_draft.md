# Bounded complementary feature-level explanation

## A. Bounded scope

E1 was restricted to apache/activemq × TEXT. The persisted reconstructed TRAIN representation contained 3,675 rows and 2,557 TF-IDF features. A frozen vectorizer transformed all 245 authorized T1 messages without fitting or changing vocabulary or IDF; one deterministic replay reproduced the CSR structure and values exactly. Background selection retained 256 TRAIN identities, the global foreground contained all 245 T1 identities, and eight shared local identities were selected before attribution generation. No T1 labels or T2 rows were accessed. Four reconstructed model families were attempted without performance-based selection. LR, XGBoost and LightGBM yielded admissible explanations; RF failed exact TreeSHAP additivity and was excluded under the frozen fidelity policy.

## B. Global feature explanation

The three leading features were `svn`, `issues`, and `amq` for LR (mean absolute centered logit contributions 0.1773, 0.1731, and 0.1685); `amq`, `issues`, and `browse` for XGBoost (0.2647, 0.1808, and 0.1642 on the native margin scale); and `id`, `amq`, and `browse` for LightGBM (0.5465, 0.3403, and 0.3333 on its native margin scale). These magnitudes describe each corresponding predictor and must not be pooled or interpreted as a shared effect scale. Full rankings include all 2,557 features for each reportable family, including features with zero foreground values. Table E1-2 and Figure E1-F1 report the top 20.

## C. Local explanation

Twenty-four local records cover the eight preselected identities and three reportable families. Each record preserves output, baseline, positive and negative feature contributions, a full-vector reference, feature values, and fidelity residual. Figure E1-F3 shows the first frozen local identity using LR: commit `e947927511796484e2ae0a066df7fa7b4800a578`, baseline -1.559703, and output logit 0.866426. The displayed features include `issues`, `browse`, `amq`, and `jira`; their contribution is relative to the TRAIN reference and does not establish a causal mechanism. The display includes the net contribution of all omitted features. Absent tokens may receive nonzero centered contributions.

## D. Fidelity

All 245 foreground rows passed the frozen residual bound in each of 20 repetitions for each reportable family, giving 14,700 valid row-level attribution checks. Maximum absolute residuals were 1.3323×10⁻¹⁵ for LR, 1.6689×10⁻⁶ for XGBoost, and 1.0183×10⁻¹² for LightGBM. The tolerances were 10⁻¹⁰(1+|output|) for LR and 10⁻⁶(1+|output|) for TreeSHAP; XGBoost's maximum absolute residual passed its output-dependent bound. LR also passed the separately checked sigmoid-to-probability identity. RF's exact explainer raised an additivity error (reported sum 0.742972 versus output 0.544626); no RF feature attribution was admitted, and no tolerance or explainer regime was changed.

## E. Stability

Across the 20 frozen seeds, LR, XGBoost and LightGBM each reproduced identical attribution values (maximum absolute difference zero). All 190 unordered repetition pairs per family satisfied the fixed-population ranking and sign diagnostics at k=3 and k=10; normalized attribution total variation was zero. This establishes numerical and ranking repeatability for the frozen foreground/background, not robustness to alternative population samples or reference distributions. RF stability is unavailable.

## F. Cross-model consistency

Top-3 Jaccard overlaps were 0.500 (LR–XGBoost), 0.200 (LR–LightGBM), and 0.500 (XGBoost–LightGBM). Top-10 overlaps were 0.538, 0.667, and 0.429, respectively. Spearman correlations on the union of top-10 features were 0.500, 0.406, and 0.420; shared-feature signed-mean agreement was 0.857, 1.000, and 0.833. No pair met all predeclared thresholds (Jaccard ≥0.60, Spearman ≥0.70, sign agreement ≥0.80). The outcome is MODEL_DEPENDENT_EXPLANATIONS, with RF comparisons unavailable.

## G. Model heterogeneity

The three reportable families shared six top-10 features: `amq`, `browse`, `id`, `incubator`, `issues`, and `test`. Nevertheless, their ordering and remaining prominent features differed. Features unique to one family's top 10 were `jira` for LR, `messages`, `of`, and `on` for XGBoost, and `0310` and `activemq` for LightGBM. This is partial overlap, not a universal feature narrative.

## H. E1/E2 interpretive continuity

E2 quantifies modality contributions within the frozen late-fusion architecture, while E1 identifies within-modality signals driving the provenance-eligible ActiveMQ TEXT predictors. Frozen model identities, vectorizer provenance and E2 scope references support an architectural connection. This sprint did not remeasure exact historical E2 same-row probability linkage; it therefore makes no empirical compositional or shared-row waterfall claim. E2 evidence was neither recomputed nor modified.

## I. Limitations

This single-project, single-modality case study complements the primary multimodal E2 analysis. It provides no CODE/PROCESS feature attribution and supports no generalization to all ApacheJIT projects. Representations and predictors are reconstructed; TF-IDF contributions are associational. RF exact additivity failed, cross-model rank agreement was limited, and stability was evaluated only at fixed populations. Five child representation files required exact one-byte terminal-LF restoration to recover the inherited hashes; parent files were unchanged. The inherited R4 package contains related serialization discrepancies that continue to fail legacy integrity tests and are reported separately. E1 attributions are not algebraically propagated into E2.

Evidence: `tables/E1-1_scope.*`, `tables/E1-2_top20.*`, `tables/E1-3_fidelity_stability.*`, `tables/E1-4_consistency.*`, `tables/E1-5_hierarchy.*`, `e1_fidelity_results.json`, `e1_stability_results.json`, `e1_to_e2_traceability.jsonl`, and `e1_limitations.json`.
