# Sprint 10.8.2.32 — Q1 Experimental Evidence Gap Audit and Roadmap

## 1. Executive scientific assessment

MMSDP-XAI does **not yet possess the empirical body needed for the broad Q1 claim presently made in the thesis/article**. It does possess a defensible, leakage-controlled, temporally sealed result for one fixed **CODE+TEXT** predictor and strong evidence that isotonic calibration improved its probability reliability. The central three-modality claim, learned fusion claim, repeated temporal robustness, external validation, XAI validity, and practical prioritization remain unsupported or only partially supported.

The minimum defensible route is therefore not to revisit Sprint 31 TEST, but to create a new predeclared temporal protocol, evaluate the full modality factorial design, isolate fusion and ablation effects, compare calibration, establish repeated temporal uncertainty, validate externally where construct-compatible, and only then execute XAI and practical-utility studies. Neutral or negative results must be retained.

## 2. Evidence sources inspected

Documentary intent was inspected in:

- `reference/thesis/Thesis_Draft.docx`
- `reference/paper/Paper_Draft.docx`
- `reference/project_plan/Proyecto_de_Tesis.docx`
- `reference/reviewer_feedback/Respuesta a los revisores.docx`
- `docs/PROJECT_CONTEXT.md`, `DATASET_SPECIFICATION.md`, `FEATURE_SPECIFICATION.md`, `SYSTEM_ARCHITECTURE.md`, `REVIEWER_TRACEABILITY_MATRIX.md`, quality/risk/design documents

Executed evidence was inspected in the versioned JIT-Defects4J audits for canonical materialization, adapters, controlled baselines, fusion, robustness, calibration protocol/execution, final-refit governance, one-shot TEST, and Sprint 31A reconstruction; their configs and frozen output/state artifacts were also inspected. Qt artifacts and unimodal outputs were treated as repository evidence of a separate pipeline, not automatically as compatible external validation.

Documents were treated as commitments/plans, not proof of execution. Where they conflict, executed repository evidence controls implementation status.

## 3. Current frozen experimental state

The scientifically frozen predictor is CODE RF over six structural features plus TEXT liblinear LR over a TRAIN-fitted 5,000-dimensional unigram TF-IDF representation. It uses fixed, unlearned late fusion `p_raw = 0.5*p_CODE + 0.5*p_TEXT`; PROCESS is excluded. Isotonic calibration was selected on canonical VALIDATION and fitted there. Base models and representations used TRAIN only.

The sealed temporal TEST contains 4,119 observations, 160 positives, and prevalence 0.038844. Raw ROC-AUC/AP/Brier/ECE are 0.747128/0.121984/0.039909/0.058956. Isotonic values are 0.745211/0.112854/0.037023/0.023942. Thus reliability improved materially while discrimination decreased slightly. This observation cannot drive adaptation.

Sprint 31A found the provenance defensible and reproduced development/calibration states. The exact originally fitted RF/LR objects were not persisted, preventing byte-level identity comparison; this is a reproducibility limitation, not evidence of inconsistency.

## 4. Thesis/article/RQ alignment

The plan and thesis require a three-modality CODE+PROCESS+TEXT framework, unimodal and bimodal comparisons, late meta-fusion, calibration, and global/local/counterfactual explanation. The article additionally alternates between three and four modalities, mentions early and late fusion, specifies CodeBERT/AST semantics and Platt, and writes several empirical conclusions as already established.

Executed evidence instead supports a simpler CODE+TEXT fixed-fusion predictor with TF-IDF and isotonic calibration. The manuscript statements that multimodality improves consistently, all three modalities complement one another, and XAI outputs are useful exceed present evidence.

The proposed seven-RQ structure in `research_question_alignment.json` is coherent and should be adopted only through an explicit thesis/article scope decision. It must not silently replace PE/OE/HE commitments.

## 5. Reviewer concern traceability

- **Perfect RF/MM-RF ≈1.0:** resolved only for the current leakage-safe path. Current scores are plausible and leakage audits pass. Historical perfect results are **superseded** and must never be cited as valid evidence.
- **Target proxies:** `bug_confidence`, `msg_has_bug_kw`, and `has_bug_keyword` are absent from the current frozen predictor schema; target/fix/SZZ/issue/future fields are denied. Semantic-equivalent screening remains a P0 gate.
- **Unimodal/bimodal/full models:** development comparisons exist, but only CODE+TEXT advanced to sealed evaluation. Full C+P+T contribution is not supported.
- **Fusion:** fixed probability averaging has evidence; learned late fusion/stacking has implementation infrastructure but no current scientific experiment. They are not equivalent.
- **CV=2…11:** rejected when interpreted as ordinary shuffled/random folds. Fold-count enumeration cannot compensate for invalid chronology.

Full mappings are in `reviewer_traceability.json` and the evidence matrix.

## 6. Existing evidence

Existing evidence supports canonical temporal identities, label/feature lineage, TRAIN-only fitting, a clean predictive denylist, explicit semantic separation of commit/target/fixing and inducing evidence, C/P/T development baselines, all fixed equal-weight modality combinations on VALIDATION, CODE+TEXT development stability, a predeclared calibration comparison, one immutable temporal TEST result, and a post-TEST reconstruction/integrity audit.

This is meaningful evidence for a constrained paper about a leakage-controlled calibrated CODE+TEXT JIT predictor. It is insufficient for the current full MMSDP-XAI contribution.

## 7. Missing evidence

P1 gaps are: repeated temporally valid C/P/T unimodal, all bimodal, and C+P+T comparisons; full modality ablation; fixed versus learned fusion if stacking remains claimed; calibration comparison on accepted future models; multi-origin robustness; paired uncertainty/effect magnitude; and statistically valid claim testing. P2 gaps are compact model-family sensitivity, independent compatible validation, XAI stability/fidelity, and operational prioritization.

## 8. Leakage/validity status

Current frozen-path leakage status is **PASS**. This does not validate historical perfect-score experiments or every feature implementation in the repository. Future features must be observation-time available, constructed within each training origin, and screened both by name and semantics. Correlation filtering alone is not a sufficient leakage defense and must not replace provenance analysis.

Semantic separation must remain explicit: a bug issue is not a fixing commit; a fixing commit is not a bug-inducing commit; a bug-inducing commit is the label evidence for a defect-prone prediction target, not a permissible predictor feature.

## 9. Unimodal evidence status

**PARTIALLY SUPPORTED.** Sprint 25 gives leakage-safe TRAIN→VALIDATION results for CODE, PROCESS, and TEXT. It shows PROCESS is weak under the minimal ancestor-only representation. It does not establish repeated temporal or external baseline performance.

## 10. Bimodal evidence status

**PARTIALLY SUPPORTED.** Sprint 26 evaluated C+P, C+T, and P+T with fixed equal weights on VALIDATION. C+T was strongest. These are development results, not final comparative generalization evidence.

## 11. Full multimodal evidence status

**NOT SUPPORTED.** C+P+T was evaluated as an equal-weight development candidate and underperformed C+T in both ROC-AUC and AP. It was not the sealed predictor. A true three-modality contribution may ultimately be rejected; that outcome would be scientifically valid and would require narrowing the claimed framework.

## 12. Fusion evidence status

Fixed equal-weight probability late fusion is **partially supported**. Learned weights, stacking/meta-learning, and early fusion are **not supported by executed current-dataset evidence**. Repository stacking modules/tests demonstrate software capability, not empirical benefit. If stacking remains central, its meta-features must be generated out-of-time using nested rolling/blocked folds; no base learner may predict a row it was trained on.

## 13. Calibration evidence status

Calibration is the strongest supported contribution. UNCALIBRATED, PLATT, and ISOTONIC were predeclared and compared out-of-fold on VALIDATION; isotonic was selected by Brier and subsequently improved sealed TEST Brier and ECE. Reliability bins and discrimination trade-offs are reported. The evidence is scoped to one predictor and period. Future accepted models require the same three-way comparison with reliability diagrams, binning-sensitivity disclosure, and paired uncertainty. The manuscript's Platt-specific claim conflicts with executed isotonic evidence.

## 14. Ablation evidence status

PROCESS addition/removal and modality combinations have development ablation evidence, with no positive PROCESS contribution under the frozen representation. Required future ablations are leave-one-modality-out and constituent-versus-combination comparisons across temporal origins. Feature-group ablation is warranted only for predeclared semantically coherent groups. A special target-proxy ablation is unnecessary for the clean path because proxies are forbidden, not optional predictors; historical results should instead be invalidated/superseded.

## 15. Robustness evidence status

**PARTIALLY SUPPORTED.** Seed variation, training-fraction sensitivity, project subgroups, and paired VALIDATION bootstrap support development stability of C+T. They do not replace repeated temporal evaluation. One sealed temporal TEST is evidence of one future period, not temporal robustness in general.

The required alternative is expanding-window rolling-origin or blocked temporal evaluation with several chronological holdouts, reported with prevalence/drift and adequate positive support. Random k-fold CV=2…11 is scientifically inappropriate for primary JIT evaluation because most folds train on observations later than their held-out rows, producing future-to-past learning and optimistic estimates. A range of invalid K values does not create robustness.

## 16. Statistical inference gap

Future comparisons should use paired bootstrap of metric differences within each untouched evaluation block. Across a sufficient number of independent temporal periods or projects, Wilcoxon signed-rank can summarize paired block-level effects, accompanied by an effect size such as Cliff's delta (or an explicitly paired alternative) and confidence intervals. Holm correction should cover the predeclared family of modality/fusion comparisons. DeLong is reasonable only as a secondary paired ROC-AUC analysis; it does not address AP, calibration, temporal heterogeneity, or multiplicity. Applying Wilcoxon to thousands of individual prediction rows would be pseudoreplication and is rejected.

## 17. External validation gap

**REQUIRES EXTERNAL VALIDATION** for strong transportability claims. JIT-Defects4J spans projects but shares one benchmark construction. A compatible external dataset must be commit-level, chronologically ordered, have observation-time CODE/PROCESS/TEXT inputs, and use construct-equivalent defect-inducing labels. PROMISE's common module/release-level datasets are not automatically compatible with JIT multimodal commit prediction. Qt can qualify only after label, coverage, modality, and temporal-boundary compatibility gates; its current artifacts do not yet constitute accepted external predictive evidence.

## 18. XAI readiness

**NOT READY FOR EMPIRICAL CLAIMS.** XAI modules and unit tests are infrastructure only. SHAP/global/local analysis should run only for models accepted after predictive, temporal, and preferably external validation. Required evidence includes model-method compatibility, fidelity, bootstrap/period stability, representative local cases, and constraint validity for counterfactuals. LIME may be a sensitivity comparator; PDP/ICE require careful handling of correlated features. All outputs describe predictive associations or model behavior—not causes of defects.

## 19. Practical relevance gap

**NOT SUPPORTED.** Sprint 31 intentionally has no threshold. The future article should report Recall@K and Precision@K under predeclared inspection budgets. AUCEC/Popt are appropriate only when changed lines/files or another measure is validated as inspection effort and the ranking unit matches commit-level operations. Budget curves are preferable to a cherry-picked threshold.

## 20. Q1 contribution audit

| Contribution | Status now | Evidence boundary |
|---|---|---|
| C1 Leakage-controlled multimodal JIT prediction | PARTIALLY SUPPORTED | Leakage controlled; predictor is C+T, not full C+P+T |
| C2 C/P/T complementarity | NOT YET SUPPORTED | PROCESS contribution currently negative |
| C3 Fusion benefit | PARTIALLY SUPPORTED | Fixed C+T development evidence only for comparison |
| C4 Probability calibration | SUPPORTED NOW | One frozen predictor/period; Brier and ECE improve |
| C5 Multimodal XAI | NOT YET SUPPORTED | No accepted empirical XAI study |
| C6 Temporal robustness | PARTIALLY SUPPORTED | One TEST period plus development sensitivity |
| C7 External generalization | NOT YET SUPPORTED | No independent compatible validation |
| C8 Operational relevance | NOT YET SUPPORTED | No effort/budget-aware accepted evaluation |

## 21. Proposed future experimental roadmap

The dependency-ordered minimum is:

1. **10.8.2.33 — Validity/new-boundary contract:** freeze provenance, semantic schemas, future rolling origins, untouched final boundary, and pre-evaluation estimator persistence.
2. **10.8.2.34 — Modality factorial:** C, P, T, C+P, C+T, P+T, C+P+T on development temporal origins.
3. **10.8.2.35 — Fusion and ablation:** fixed fusion; nested temporal stacking only if the claim is retained; leave-one-modality-out.
4. **10.8.2.36 — Calibration:** raw versus Platt versus isotonic for accepted candidates.
5. **10.8.2.37 — Temporal robustness:** expanding-window/rolling-origin evaluation.
6. **10.8.2.38 — Inference/model sensitivity:** paired uncertainty, effect sizes, multiplicity control; LR, RF, and at most one justified boosted-tree family.
7. **10.8.2.39 — External validation:** independent construct-compatible JIT data.
8. **10.8.2.40 — XAI:** fidelity and stability for accepted predictors only.
9. **10.8.2.41 — Practical utility and synthesis:** budget-aware evaluation and claim/evidence ledger.

For every sprint, `experimental_roadmap.json` records the objective, hypothesis, inputs, frozen elements, allowed/forbidden changes, experiment, metrics, statistical analysis, acceptance criteria, artifact, dependency, and enabled claim.

## 22. TEST governance

Sprint 31 TEST remains immutable historical evidence for exactly the frozen C+T 0.5/0.5 isotonic configuration. It may be cited and its preserved integrity audited, but it may not be rerun, rescored, tuned upon, or used to choose features, representations, model families, fusion, calibration, thresholds, or explanations.

Future work must use TRAIN/VALIDATION-derived rolling development folds and then an untouched **new** later period or independent compatible dataset as the new final boundary. All decisions and fitted-state digests must be frozen before opening that boundary once. Sprint 31 outcomes cannot be an acceptance criterion for candidate design.

## 23. Threats and limitations

This audit is documentary and repository-bounded; it does not independently reproduce raw-data acquisition or verify claims against external literature. Documents contain internal inconsistencies and unfinished placeholders. Existing results use a low-prevalence benchmark with heterogeneous project support. PROCESS is intentionally minimal, so its negative result cannot be generalized to all process representations. The audit cannot restore pre-TEST fitted RF/LR objects. The future sprint identifiers are proposals, not authorization to execute experiments.

## 24. Scientific decision

The audit maps the available documentary commitments, executed evidence, reviewer concerns, gaps, dependencies, random-CV ruling, and sealed-TEST governance. It executed no experiment and made no post-TEST adaptation. The limitation is substantive: the present evidence supports only a constrained C+T calibrated predictor, not the broad three-modality/XAI/generalization claim.

## 25. Exact next sprint recommendation

**Sprint 10.8.2.33 — New Experimental Validity, Temporal Boundary, and Provenance Predeclaration.** It must be audit/protocol only: freeze construct-compatible modalities and labels, ban semantic target proxies, specify rolling-origin development partitions and a new untouched final boundary, define estimator-state persistence, predeclare candidate/metric/comparison families, and certify that Sprint 31 evidence was not used for adaptation. No model should be trained until this gate passes.

## Quality-gate and prohibited-execution ledger

Sprint 32 is an audit generator only. Its focused tests validate schema/status/priority/risk domains, completeness, random-CV rejection, roadmap fields, sealed-TEST language, and zero-execution counters. The explicit execution ledger is:

- TEST predictive scoring executions during Sprint 32 = **0**
- model training executions during Sprint 32 = **0**
- calibration fitting executions during Sprint 32 = **0**
- XAI model explanation executions during Sprint 32 = **0**

Final repository-wide quality-gate results are recorded in the completion handoff after execution.

SPRINT_10.8.2.32_GO_WITH_LIMITATIONS
