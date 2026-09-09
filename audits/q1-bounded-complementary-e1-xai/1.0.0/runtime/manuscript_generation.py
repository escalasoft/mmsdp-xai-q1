from pathlib import Path
import sys
sys.path.insert(0,str(Path.cwd()))
from src.evaluation import q1_bounded_complementary_e1_xai as q
p=q.OUT
q.manifest();q.verify_manifest(p)
local=q.rows(p/'e1_local_explanations.jsonl')[0]
def md(name,text): (p/name).write_text(text.strip()+'\n')
md('manuscript_xai_positioning.md','''# Manuscript positioning

The predictive block remains primary; calibration provides primary supporting evidence. E2 is the primary explainability contribution because it addresses the multimodal late-fusion architecture. E1 supplies bounded complementary within-modality evidence for provenance-eligible ActiveMQ TEXT. Reconstructed predictors and representations retain that designation throughout.

Use E1 Tables 1–5 and Figures 1–4 as a bounded explanatory case study. Do not imply full CODE/PROCESS/TEXT feature coverage, cross-project representativeness, predictive validation by attribution, or algebraic decomposition of E2 by E1.
''')
md('manuscript_e1_results_draft.md',f'''# Bounded complementary feature-level explanation

## A. Bounded scope

E1 was restricted to apache/activemq × TEXT. The persisted reconstructed TRAIN representation contained 3,675 rows and 2,557 TF-IDF features. A frozen vectorizer transformed all 245 authorized T1 messages without fitting or changing vocabulary or IDF; one deterministic replay reproduced the CSR structure and values exactly. Background selection retained 256 TRAIN identities, the global foreground contained all 245 T1 identities, and eight shared local identities were selected before attribution generation. No T1 labels or T2 rows were accessed. Four reconstructed model families were attempted without performance-based selection. LR, XGBoost and LightGBM yielded admissible explanations; RF failed exact TreeSHAP additivity and was excluded under the frozen fidelity policy.

## B. Global feature explanation

The three leading features were `svn`, `issues`, and `amq` for LR (mean absolute centered logit contributions 0.1773, 0.1731, and 0.1685); `amq`, `issues`, and `browse` for XGBoost (0.2647, 0.1808, and 0.1642 on the native margin scale); and `id`, `amq`, and `browse` for LightGBM (0.5465, 0.3403, and 0.3333 on its native margin scale). These magnitudes describe each corresponding predictor and must not be pooled or interpreted as a shared effect scale. Full rankings include all 2,557 features for each reportable family, including features with zero foreground values. Table E1-2 and Figure E1-F1 report the top 20.

## C. Local explanation

Twenty-four local records cover the eight preselected identities and three reportable families. Each record preserves output, baseline, positive and negative feature contributions, a full-vector reference, feature values, and fidelity residual. Figure E1-F3 shows the first frozen local identity using LR: commit `{local['commit_identity']}`, baseline {local['base_value']:.6f}, and output logit {local['model_output']:.6f}. The displayed features include `issues`, `browse`, `amq`, and `jira`; their contribution is relative to the TRAIN reference and does not establish a causal mechanism. The display includes the net contribution of all omitted features. Absent tokens may receive nonzero centered contributions.

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
''')
md('manuscript_e1_discussion_draft.md','''# Discussion: bounded feature evidence within a multimodal framework

E2 remains primary because the framework's central explanatory question concerns how CODE, PROCESS and TEXT outputs enter multimodal late fusion. The bounded E1 study adds a different level of evidence: it identifies TF-IDF features associated with the outputs of the ActiveMQ TEXT predictors whose representation and transformation provenance could be verified. This supports hierarchical interpretation without asserting that feature attributions exactly compose into fusion attributions.

The valid LR, XGBoost and LightGBM explanations were faithful and numerically repeatable, yet their feature rankings were model-dependent. Their six-feature common top-10 core should therefore be discussed alongside their ordering differences and model-specific features. Fidelity to a predictor does not imply that different predictors must give the same explanation or that any predictor is accurate. No predictive metrics were recomputed to select these models or interpret attribution quality.

Several prominent literal tokens resemble issue-reference or repository-related message text (for example, `issues`, `browse`, `svn`, and `id`). That lexical observation is a cautious interpretation of the displayed tokens, not an inferred developer intention or a causal defect mechanism. The results may reflect message conventions and correlations learned from the training population. The study does not assign semantic categories, group correlated tokens, or claim that adding or removing a token would change actual defect occurrence. Present and absent TF-IDF features can both receive contributions under centered or path-dependent references.

Provenance-aware scope is necessary for defensible feature interpretation. CODE and PROCESS feature-level results were intentionally omitted because the completed provenance campaign did not establish the required representations and transformations for scientific E1 use. ActiveMQ TEXT was retained because its persisted CSR representation, exact row and token registries, vocabulary and IDF were traceable. Unsupported full-modality explanations would enlarge coverage without establishing what the explanation actually refers to.

RF adds a technical limitation: its frozen exact TreeSHAP execution failed additivity and was excluded, although model-representation alignment passed. No performance comparison motivated that exclusion. The already frozen fidelity gate prevented use of an invalid explanation; no approximate method, interventional substitution or tolerance relaxation was introduced. The available three-family evidence remains complementary and cannot stand in for a successful four-family campaign.

Threats to validity include the single-project and single-modality scope; reconstructed rather than original historical matrices and predictors; family-specific output scales and references; TF-IDF correlations and message conventions; numerical repeatability assessed at fixed populations only; and the absence of an independently verified empirical same-row E1-to-E2 probability bridge. Exact terminal-LF restoration in child representation copies recovered inherited expected hashes, but inherited R4 serialization discrepancies still cause legacy regression failures. These engineering limitations are disclosed separately from the valid attribution results. The next manuscript step is integration of existing E2 and bounded E1 evidence, not another source recovery campaign.
''')
md('reviewer_response_unimodal_xai_scope.md','''# Response to reviewer: feature-level XAI scope

**Question.** Why is feature-level XAI not reported for CODE, PROCESS, and TEXT across all projects?

Explainability in this framework is hierarchical. E2 is the primary multimodal explanation: it addresses contributions of unimodal outputs within the frozen late-fusion architecture. E1 is complementary and addresses features within a scientifically traceable unimodal predictor.

The completed provenance campaign could not demonstrate the full feature-level representation and transformation lineage required for all modalities and projects. We therefore intentionally did not generate unsupported feature attributions. ActiveMQ TEXT was retained because its TRAIN matrix, row/commit identities, token/column registry, vocabulary, IDF and transformation state could be verified and its authorized T1 representation reproduced exactly without refitting or label access.

All four frozen model families were attempted. LR, XGBoost and LightGBM produced faithful, repeatable explanations; RF was excluded after exact TreeSHAP additivity failed. The manuscript explicitly reports that failure, model-dependent rankings, reconstructed artifact status, and the single-project/single-modality boundary. E1 is neither presented as all-project coverage nor propagated algebraically into E2. The bounded feature-level evidence complements the primary multimodal explanation and does not establish causality or validate predictive accuracy.
''')
md('manuscript_e1_limitations_paragraph.md','''The complementary E1 study is restricted to ActiveMQ TEXT and does not cover CODE or PROCESS at feature level or generalize to other ApacheJIT projects. Both representations and predictors remain reconstructed. LR, XGBoost and LightGBM explanations passed fidelity and fixed-population repeatability checks; RF exact TreeSHAP failed additivity and was excluded. TF-IDF attributions are associational, family-specific ranks differ, and exact repetition does not establish sampling or reference robustness. E1/E2 continuity is architectural and does not imply algebraic propagation or a newly verified same-row probability bridge. Exact child-only terminal-newline restoration recovered the TRAIN representation hashes, while inherited R4 serialization discrepancies remain visible in legacy tests.''')
# Preservation is measured, not inferred from a clean git status.
after=q.parent_snapshot();before=q.read(p/'parent_integrity_before.json');assert before==after
q.save('parent_integrity_after.json',after)
state=q.read(p/'parent_scientific_state_verification.json');state['status']='PASS_WITH_INHERITED_SERIALIZATION_LIMITATION';state['serialization_diagnostics']='parent_serialization_diagnostics.json';state['exact_child_representation_verified']=True;q.save('parent_scientific_state_verification.json',state)
q.save('governance_counters.json',{**q.read(p/'governance_counters.json'),'FIGURE_GENERATION_COUNT':8,'UNIQUE_PUBLICATION_FIGURES':4,'FIGURE_FILE_EXPORT_COUNT':16,'figure_generation_note':'Four initial renders plus four layout-verification renders; two formats each'})
q.save('figure_visual_qa.json',dict(status='PASS_AFTER_LOCAL_TITLE_LAYOUT_FIX',figures=['E1-F1','E1-F2','E1-F3','E1-F4'],source_values_checked=True,formats=['SVG','PNG_300_DPI'],no_crop_or_overlap=True))
for source,dest in [('/tmp/s56c_safe_regressions.log','validation_initial_collection.log'),('/tmp/s56c_safe_regressions_corrected.log','validation_safe_regressions.log'),('/tmp/s56c_remaining_execution.log','execution_remaining.log')]: (p/dest).write_bytes(Path(source).read_bytes())
q.manifest()
