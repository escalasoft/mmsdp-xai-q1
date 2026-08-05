# Reviewer Traceability Matrix

Version: 1.0

Primary source of truth: `docs/PROJECT_CONTEXT.md` Version 2.0.

## Sprint 10.8.1 scientific dataset contract traceability

The rows below refine only dataset-contract-related concerns. `addressed-by-specification` means a design control now exists; it does not mean that reconstruction or empirical validation is complete. Implementation and experimental evidence remain separate.

| Reviewer concern | Specification-level response | Implementation evidence required | Experimental evidence required | Responsible sprint | Current status |
| --- | --- | --- | --- | --- | --- |
| Target leakage and label-derived predictors | Target construction is separate; target/link evidence and proxies are prohibited as predictors. | Feature inventory, linkage audit, scenario validation, and model-input manifest. | Leakage-controlled comparison and suspicious-feature ablations. | 10.8.2.1b target-contract binding and label-blind feature context; project implementation pending | architecture-addressed; implementation-pending; experiment-pending |
| `bug_confidence` | Canonical prohibited-name policy and prohibited provenance example. | Demonstrate absence from every fitted matrix and retain it only as label provenance if needed. | Ablation/comparison if any prior result used it. | 10.8.2.1b structural removal of assignments, evidence, and confidence from Feature Construction; project implementation pending | architecture-addressed; implementation-pending; experiment-pending |
| Bug/fix keyword features (`msg_has_bug_kw`, `has_bug_keyword`, variants) | Engineered target-linking keyword indicators are prohibited; raw text is assessed separately. | Token/feature lineage audit and verified exclusion of engineered linking indicators. | Text scenario/ablation evidence under leakage control. | 10.8.2.1b recursive protected-context controls; project implementation pending | architecture-addressed; implementation-pending; experiment-pending |
| Temporal reconstruction prerequisites | One authoritative timestamp, chronological order, and no future/post-event features remain required; immutable Qt Base source acquisition now establishes only the repository revision prerequisite. | Commit extraction, dataset ordering report, and chronological split manifest remain required. | Temporally valid evaluation; no random split as replacement. | 10.8.2.2 repository acquisition implemented; commit and temporal extraction pending | architecture-addressed; acquisition-implemented; extraction-pending; experiment-pending |
| Train/test preprocessing separation | Learned preprocessing, vocabularies, embeddings, imputers, scalers, and selectors are training-fit only. | Stored fit-scope manifest and tests proving transform-only validation/test handling. | Runs generated exclusively from compliant artifacts. | 10.8.1 specification; preprocessing evidence sprint pending | addressed-by-specification; implementation-pending; experiment-pending |
| Reproducibility of dataset source | Deterministic acquisition identity, policy version, canonical JSON, immutable revision, and SHA-256 digests are required. | Qt Base acquisition specification, validated snapshot, artifact checksum, and offline Git integration tests; dataset reconstruction remains pending. | Independent reconstruction or reproducibility audit for reported experiments. | 10.8.2.2 Qt Base repository acquisition adapter | architecture-addressed; acquisition-implemented; extraction-pending; experiment-pending |
| Source revision traceability | Mutable branch and tag inputs must resolve to a full immutable commit object identifier before downstream extraction. | Snapshot revision, detected Git object format, resolved-reference evidence, and digest consistency tests. | Experiment manifests must later bind the approved snapshot digest. | 10.8.2.2 Qt Base repository acquisition adapter | architecture-addressed; acquisition-implemented; extraction-pending; experiment-pending |
| Repository provenance | Scientific identity retains the official Qt Base URL; transport identity is validated and machine-local paths and runtime timestamps are excluded. | Canonical URL enforcement, remote validation, sanitized command evidence, and stable repository identity digest. | Dataset and experiment manifests must later retain this provenance chain. | 10.8.2.2 Qt Base repository acquisition adapter | architecture-addressed; acquisition-implemented; extraction-pending; experiment-pending |
| External validity limitations | Qt Base remains the first single-project source; acquisition does not establish cross-project generalizability. | Explicit scope limitation in dataset documentation after extraction. | Conditional external validation or claims narrowed to Qt Base evidence. | 10.8.2.2 acquisition scope; external validation remains future work | architecture-addressed; acquisition-implemented; extraction-pending; experiment-pending |
| Feature provenance | Every candidate, including excluded fields, requires source, timing, derivation, fit scope, leakage and scenario disposition. | Completed project-specific feature dictionary and source-to-feature lineage. | Feature/modality ablations and explanation traceability for accepted models. | 10.8.2.1b digest-bearing provenance controls and descriptive inventory metadata policy; project implementation pending | architecture-addressed; implementation-pending; experiment-pending |
| Calibration isolation | Dataset contract excludes targets/proxies and test-fitted transformations; calibration remains a separate downstream stage. | Validation-only calibrator fit manifest and no test access during selection. | Pre/post Brier Score and ECE on held-out chronological test data. | 10.8.1 specification; calibration sprint evidence pending | addressed-by-specification; implementation-pending; experiment-pending |
| Experiment reproducibility | Dataset digest and manifest become immutable experiment inputs. | Experiment manifests linking configuration, code, environment, dataset digest, seeds, and artifacts. | Repeated execution with matching outputs within declared determinism/tolerance. | 10.8.1 specification; experiment evidence sprint pending | addressed-by-specification; implementation-pending; experiment-pending |

Secondary quality-improvement source: `reference/reviewer_feedback/Respuesta a los revisores.docx`.

Supporting architecture source: `docs/SYSTEM_ARCHITECTURE.md`.

This matrix transforms peer-review observations from a previous manuscript review into controlled quality-improvement decisions for the clean MMSDP-XAI project. The rejected or reviewed manuscript is not treated as the current project specification. Reviewer suggestions are evaluated against the current doctoral research scope, the clean project architecture, and the frozen decisions in `PROJECT_CONTEXT.md`.

Decision vocabulary:

- `Adopt`: incorporate as a project quality requirement.
- `Adapt`: incorporate only after reformulation to preserve strict temporal validation, clean-project scope, or the SSOT.
- `Defer`: postpone until scientifically justified or until future publication planning.
- `Reject`: do not incorporate because it conflicts with project constraints or lacks sufficient justification.
- `Journal-dependent`: keep as an editorial control for a target journal rather than as a scientific or software architecture requirement.

## Governing Interpretation Rules

1. `docs/PROJECT_CONTEXT.md` remains the primary Single Source of Truth.
2. Reviewer feedback is secondary and is used only to improve quality controls.
3. IEEE Access formatting instructions are journal-dependent unless they express a journal-independent quality concern.
4. Suggestions that conflict with chronological validation, the defined scientific scope, or the clean-project design are reformulated or rejected.
5. Random cross-validation is not adopted because the project requires chronological temporal validation.
6. Claims about completed experiments, final results, or final dataset statistics must not be introduced from the reviewer feedback.

## Proposed Control IDs

### Design Decisions

| ID | Decision |
|---|---|
| DD-001 | Preserve `PROJECT_CONTEXT.md` as primary SSOT. |
| DD-002 | Preserve commit as unit of analysis. |
| DD-003 | Preserve QtBase-based `MQtBase` as the primary dataset, subject to source-name inconsistency resolution. |
| DD-004 | Preserve Code + Process + Text modalities. |
| DD-005 | Preserve strict chronological 70 / 15 / 15 validation. |
| DD-006 | Use decision-level late fusion based on out-of-fold unimodal probabilities. |
| DD-007 | Use post-fusion Platt Scaling as the approved calibration approach. |
| DD-008 | Use SHAP-based global/local explanations plus counterfactual explanations. |
| DD-009 | Treat raw data as immutable and preprocessing as train-fitted only. |
| DD-010 | Keep notebooks exploratory and Python modules as production code. |
| DD-011 | Treat journal formatting as submission-target dependent. |
| DD-012 | Require baseline selection to be justified scientifically, not by a fixed reviewer-requested count. |
| DD-013 | Treat external validation as conditional robustness work, not a mandatory replacement for the primary QtBase study. |

### Quality Requirements

| ID | Requirement |
|---|---|
| QR-001 | Document complete dataset provenance, repository snapshot, date range, filtering rules, modality inventory, and labeling procedure. |
| QR-002 | Document and test leakage controls for `bug_confidence`, `msg_has_bug_kw`, `has_bug_keyword`, and all target-derived or future-derived variables. |
| QR-003 | Compare unimodal, bimodal, and full multimodal configurations. |
| QR-004 | Implement a real decision-level late-fusion experiment using out-of-fold unimodal probabilities. |
| QR-005 | Run mandatory ablation studies for critical features and modalities. |
| QR-006 | Report calibration before and after calibration, including Brier Score and ECE. |
| QR-007 | Gate perfect or near-perfect performance through plausibility checks before any scientific claim. |
| QR-008 | Preserve reproducibility manifests, including configuration, seed, environment, data manifest, logs, metrics, and artifacts. |
| QR-009 | Separate journal-independent writing quality from target-journal formatting controls. |
| QR-010 | Maintain traceability from commit hash to labels, features, splits, predictions, explanations, and metrics. |
| QR-011 | Justify baselines and algorithms according to research questions and literature relevance. |
| QR-012 | Preserve strict chronological validation; do not replace it with random cross-validation. |
| QR-013 | Document practical implications only after results are valid and leakage checks pass. |
| QR-014 | Document architecture-layer rationale and figure descriptions for publication clarity. |

### Risks

| ID | Risk |
|---|---|
| RK-001 | Data leakage through target-derived or future-derived features. |
| RK-002 | Implausible perfect or near-perfect performance. |
| RK-003 | Architecture-experiment mismatch. |
| RK-004 | Insufficient dataset and labeling documentation. |
| RK-005 | Calibration claims unsupported by quantitative metrics. |
| RK-006 | Explanations reflect leakage rather than defect risk. |
| RK-007 | Reproducibility gaps. |
| RK-008 | Journal-specific formatting mixed into scientific requirements. |
| RK-009 | Baseline selection driven by arbitrary reviewer counts instead of scientific rationale. |
| RK-010 | External validity limitations if only one dataset is evaluated. |
| RK-011 | Misalignment between thesis, paper, and code. |
| RK-012 | Random validation undermines chronological deployment realism. |

### Quality Gates

| ID | Gate |
|---|---|
| QG-001 | Leakage audit gate. |
| QG-002 | Dataset documentation gate. |
| QG-003 | Temporal split gate. |
| QG-004 | Baseline and ablation gate. |
| QG-005 | Late-fusion implementation gate. |
| QG-006 | Calibration evidence gate. |
| QG-007 | Explainability validity gate. |
| QG-008 | Result plausibility gate. |
| QG-009 | Reproducibility manifest gate. |
| QG-010 | Editorial quality gate. |
| QG-011 | External validation decision gate. |
| QG-012 | Thesis-paper-code alignment gate. |

## Traceability Matrix

| Observation ID | Source | Original concern, accurately paraphrased | Category | Scientific or technical risk | Relevance to the clean project | Decision | Rationale | Proposed design decision ID | Proposed quality requirement ID | Proposed risk ID | Proposed quality gate ID | Files or modules affected | Impact on thesis | Impact on paper | Verification evidence | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| OBS-001 | Editor | The manuscript must strictly follow the IEEE Access template. | Editorial or journal-specific | Journal formatting noncompliance at submission. | Low for clean project architecture; relevant only when submitting to IEEE Access. | Journal-dependent | Template compliance depends on the target journal and must not shape the scientific architecture. | DD-011 | QR-009 | RK-008 | QG-010 | `paper/` | No thesis architecture impact. | Apply only for IEEE Access submission. | Target-journal checklist before submission. | Open |
| OBS-002 | Editor | Abbreviations should be removed from title, abstract, and index terms and defined later. | Editorial or journal-specific | Premature abbreviation use may violate journal style. | Low for code and architecture; relevant to manuscript preparation. | Journal-dependent | Abbreviation placement is journal style, not a project requirement. | DD-011 | QR-009 | RK-008 | QG-010 | `paper/` | No thesis architecture impact unless required by thesis style. | Apply according to target journal. | Editorial checklist. | Open |
| OBS-003 | Editor | At least 10 IEEE taxonomy index terms are required. | Editorial or journal-specific | Submission formatting issue. | Low; target-journal dependent. | Journal-dependent | IEEE taxonomy terms are specific to IEEE Access or IEEE-family publication. | DD-011 | QR-009 | RK-008 | QG-010 | `paper/` | No thesis impact. | Apply only for IEEE-style submission. | Journal instructions review. | Open |
| OBS-004 | Editor | Abstract should be limited to 150 words and focus on originality. | Editorial or journal-specific | Abstract may fail journal requirements or obscure contribution. | Mixed: word count is journal-dependent; clarity of originality is journal-independent. | Adapt | Preserve contribution clarity as a quality control; treat 150-word limit as journal-dependent. | DD-011 | QR-009, QR-014 | RK-008 | QG-010 | `paper/` | Strengthen thesis abstract/contribution wording without fixed IEEE word count. | Apply word count only if target journal requires it. | Abstract review checklist. | Open |
| OBS-005 | Editor | Introduction does not sufficiently analyze specific prior work or clearly state originality. | Scientific contribution | Contribution may appear unsupported. | High; aligns with SSOT motivation and contribution sections. | Adopt | The clean project must preserve a clear literature gap and contribution narrative. | DD-001 | QR-014 | RK-011 | QG-012 | `docs/PROJECT_CONTEXT.md`, `paper/`, `docs/` | Thesis should clearly separate problem, gap, contribution. | Paper introduction must state novelty against closest work. | Literature-gap checklist. | Open |
| OBS-006 | Editor | References should be improved with recent IEEE journal and conference work. | Documentation | Literature coverage may be perceived as insufficient. | Medium; must be handled without citation padding. | Adapt | Add or remove references only when scientifically relevant; do not privilege IEEE solely unless target journal requires it. | DD-011 | QR-009, QR-014 | RK-008 | QG-010 | `paper/`, thesis references | Thesis literature review may need updates. | Paper references should be relevant, current, and deduplicated. | Reference audit. | Open |
| OBS-007 | Editor | Table captions are too brief and insufficiently explicit. | Documentation | Tables may be hard to interpret. | Medium for manuscripts, low for architecture. | Adopt | Clear captions are journal-independent quality controls. | DD-011 | QR-009 | RK-008 | QG-010 | `paper/`, `outputs/reports` | Improve table self-containment in thesis. | Improve table captions in paper. | Caption checklist. | Open |
| OBS-008 | Editor | English grammar and spelling are not acceptable; professional language review suggested. | Editorial or journal-specific | Presentation quality may block publication. | Medium for manuscripts; not a software architecture constraint. | Adapt | Professional language quality is journal-independent; Paperpal certificate is IEEE Access-dependent. | DD-011 | QR-009 | RK-008 | QG-010 | `paper/`, thesis manuscript | Thesis language review recommended. | Journal-specific certificate only if required. | Editorial review record. | Open |
| OBS-009 | Reviewer 1 | The topic is promising, but methodology and presentation require major revision. | Scientific contribution | Work may be unevaluable without transparent methods. | High; supports stronger clean-project quality gates. | Adopt | The clean project must explicitly gate methodology, reproducibility, and presentation. | DD-001 | QR-001, QR-008, QR-014 | RK-004, RK-007 | QG-002, QG-009, QG-010 | `docs/`, `src/`, `experiments/`, `outputs/` | Thesis methods chapter must be complete. | Paper methods and presentation must be complete. | Quality gate checklist. | Open |
| OBS-010 | Reviewer 1 | Perfect RF and MM-RF scores are not credible without rigorous leakage analysis, especially for `bug_confidence`, `msg_has_bug_kw`, and `has_bug_keyword`. | Data leakage | Target-derived proxies may make the task trivial. | Critical; directly aligns with mandatory treatment rule 1. | Adopt | The clean project must test these and any target-derived or future-derived variables before modeling claims. | DD-005, DD-009 | QR-002, QR-007 | RK-001, RK-002 | QG-001, QG-008 | `src/preprocessing`, `src/feature_engineering`, `src/evaluation`, `outputs/metrics` | Thesis must document leakage audit and feature exclusion rationale. | Paper must report leakage controls and plausibility gate. | Leakage report showing variable definitions, removals, and tests. | Open |
| OBS-011 | Reviewer 1 | Claimed architecture does not match experiments; missing unimodal baselines, pairwise modalities, real late fusion, and ablations. | Experimental design | Architecture-experiment mismatch undermines contribution. | Critical; aligns with mandatory treatment rules 2-4. | Adopt | The clean project must evaluate unimodal, bimodal, and full multimodal configurations with true late fusion and ablations. | DD-004, DD-006 | QR-003, QR-004, QR-005 | RK-003 | QG-004, QG-005 | `src/models`, `src/multimodal`, `experiments`, `outputs/metrics` | Thesis must align hypotheses with actual experiments. | Paper must only claim what experiments implement. | Experiment manifest and comparison tables. | Open |
| OBS-012 | Reviewer 1 | Dataset and labeling procedure require complete documentation: Qt snapshot, time range, filtering, defect links, text features, and feature inventory. | Dataset construction | Study cannot be reproduced. | Critical; aligns with mandatory treatment rule 7. | Adopt | The clean project requires dataset provenance, labeling rules, modality inventory, and traceability. | DD-002, DD-003 | QR-001, QR-010 | RK-004, RK-007 | QG-002, QG-009 | `data/`, `src/extraction`, `src/preprocessing`, `docs/`, `outputs/reports` | Thesis dataset construction section must be complete. | Paper dataset section must be complete and concise. | Dataset manifest and data dictionary. | Open |
| OBS-013 | Reviewer 1 | Calibration section is incomplete; method, selection, application scope, Brier Score, and ECE should be reported before and after calibration. | Calibration | Calibration claims may be unsupported. | Critical; aligns with mandatory treatment rule 5. | Adopt | SSOT already approves Platt Scaling; evidence must include before/after Brier Score and ECE. | DD-007 | QR-006 | RK-005 | QG-006 | `src/calibration`, `src/evaluation`, `outputs/metrics`, `outputs/figures` | Thesis must report calibration methodology and metrics. | Paper must include quantitative calibration evidence. | Calibration report with pre/post metrics. | Open |
| OBS-014 | Reviewer 1 | SHAP and feature-importance explanations are meaningless if the model learns leakage proxies. | Explainability | XAI may explain leakage rather than defect risk. | Critical; direct dependency on leakage gate. | Adopt | Explainability outputs must be generated and interpreted only after leakage and plausibility gates pass. | DD-008, DD-009 | QR-002, QR-005 | RK-006 | QG-001, QG-007, QG-008 | `src/explainability`, `src/evaluation`, `outputs/figures`, `outputs/reports` | Thesis explanation claims must be conditional on leakage validity. | Paper XAI section must avoid causal overclaiming. | Explanation validity checklist and leakage audit. | Open |
| OBS-015 | Reviewer 1 | Manuscript still contains template placeholders, placeholder DOI, corresponding-author placeholder text, funding footnote text, language errors, and typos. | Editorial or journal-specific | Manuscript may appear unfinished. | Low for clean architecture; relevant for future paper. | Journal-dependent | Placeholder removal is a manuscript submission control. | DD-011 | QR-009 | RK-008 | QG-010 | `paper/` | No thesis architecture impact. | Remove before submission. | Final manuscript editorial audit. | Open |
| OBS-016 | Reviewer 1 | References include duplicates and inconsistent entries. | Documentation | Citation list may be unreliable. | Medium for thesis and paper. | Adopt | Deduplication is journal-independent documentation quality. | DD-011 | QR-009 | RK-008 | QG-010 | `paper/`, thesis references | Thesis reference list should be deduplicated. | Paper reference list should be deduplicated. | Reference audit report. | Open |
| OBS-017 | Reviewer 2 | Reviewer states the work is good, technically sound, authentic, and within scope. | Scientific contribution | Positive feedback may mask unresolved issues from other reviewers. | Low as a requirement; useful as context only. | Defer | Positive endorsement does not create a design requirement. | DD-001 | QR-014 | RK-011 | QG-012 | `docs/`, `paper/` | Can support contribution confidence after evidence exists. | Can inform response narrative after issues are fixed. | No gate required beyond existing evidence. | Recorded |
| OBS-018 | Reviewer 3 | Abstract does not clearly state MMSDP-XAI novelty or explicit research gap. | Scientific contribution | Contribution may be unclear. | High for future paper and thesis summary. | Adopt | Gap and novelty are core to SSOT and must be explicit. | DD-001 | QR-014 | RK-011 | QG-010, QG-012 | `paper/`, thesis front matter | Thesis abstract/introduction must state gap and novelty. | Paper abstract must state gap and novelty. | Abstract novelty checklist. | Open |
| OBS-019 | Reviewer 3 | Design rationale should explain separation between learning, fusion, calibration, and interpretation. | Documentation | Architecture may appear arbitrary. | High; already reflected in system architecture. | Adopt | Component separation is central to MMSDP-XAI and should be justified. | DD-006, DD-007, DD-008 | QR-014 | RK-003 | QG-012 | `docs/SYSTEM_ARCHITECTURE.md`, `paper/` | Thesis architecture chapter should justify layers. | Paper architecture section should justify design. | Architecture rationale section. | Open |
| OBS-020 | Reviewer 3 | Six-layer architecture requires justification. | Documentation | Layering may look decorative rather than methodological. | Medium; current architecture uses layered decomposition. | Adapt | Explain the modular layers as research pipeline responsibilities; do not force exactly six layers if clean architecture needs more detailed repository layers. | DD-001 | QR-014 | RK-003 | QG-012 | `docs/SYSTEM_ARCHITECTURE.md`, `paper/` | Thesis can explain conceptual six-layer framework and implementation layers separately. | Paper can present simplified layer diagram. | Architecture-layer mapping table. | Open |
| OBS-021 | Reviewer 3 | Figures, especially architecture figure, need brief descriptions throughout the article. | Documentation | Readers may not understand diagrams. | Medium. | Adopt | Figure descriptions are journal-independent manuscript quality controls. | DD-011 | QR-009, QR-014 | RK-008 | QG-010 | `paper/`, `outputs/figures`, `outputs/reports` | Thesis figures need explanatory captions. | Paper figures need explanatory captions. | Figure-caption review. | Open |
| OBS-022 | Reviewer 3 | Late fusion is not sufficiently justified against alternative fusion strategies. | Late fusion | Fusion choice may appear unsupported. | High; late fusion is frozen in SSOT. | Adopt | Preserve late fusion but document rationale and compare or discuss alternatives without changing temporal validation. | DD-006 | QR-004, QR-014 | RK-003 | QG-005, QG-012 | `src/multimodal`, `docs/`, `paper/` | Thesis must justify late fusion. | Paper must justify late fusion. | Late-fusion rationale and implementation evidence. | Open |
| OBS-023 | Reviewer 3 | Robustness claims are not empirically supported. | Result plausibility | Unsupported claims may overstate contribution. | Critical for future results reporting. | Adopt | Claims of robustness require ablations, repeated temporal evaluation, or external validation evidence. | DD-005, DD-013 | QR-005, QR-007 | RK-002, RK-010 | QG-004, QG-008, QG-011 | `experiments`, `outputs/metrics`, `paper/` | Thesis claims must match evidence. | Paper must avoid robustness claims without evidence. | Robustness evidence table or claim removal. | Open |
| OBS-024 | Reviewer 3 | Experimental justification is missing, including ablation and comparison. | Ablation | Contribution may not be isolated. | Critical; aligns with mandatory treatment rule 2. | Adopt | Ablation is mandatory for critical features and modalities. | DD-004 | QR-005 | RK-003 | QG-004 | `experiments`, `src/evaluation`, `outputs/metrics` | Thesis must show contribution of features/modalities. | Paper must include ablation results. | Ablation report. | Open |
| OBS-025 | Reviewer 4 | MMSDP-XAI integration of multimodality, calibration, and XAI is innovative and addresses a real need. | Scientific contribution | Positive feedback does not validate implementation. | Medium as contribution framing. | Adopt | Keep the contribution framing, but only support it with valid experiments. | DD-001 | QR-014 | RK-011 | QG-012 | `docs/PROJECT_CONTEXT.md`, `paper/` | Supports thesis contribution narrative. | Supports paper positioning. | Contribution traceability to valid evidence. | Open |
| OBS-026 | Reviewer 4 | Perfect RF results suggest leakage; define `bug_confidence`, ablate it or top SHAP features, and compare multimodal versus unimodal again. | Data leakage | Leakage and ceiling effects compromise fusion/calibration claims. | Critical; overlaps Reviewer 1 and mandatory rules 1, 2, 3, 6. | Adopt | Leakage analysis, ablation, unimodal/multimodal comparison, and plausibility gate are mandatory. | DD-004, DD-005, DD-009 | QR-002, QR-003, QR-005, QR-007 | RK-001, RK-002, RK-006 | QG-001, QG-004, QG-008 | `src/preprocessing`, `src/evaluation`, `experiments`, `outputs/metrics` | Thesis must include leakage and ablation evidence. | Paper must not report perfect results without plausibility evidence. | Leakage audit, ablation tables, plausibility report. | Open |
| OBS-027 | Reviewer 4 | If perfect performance persists, add a second public dataset such as PROMISE or another Qt version. | External validation | Single-dataset evidence may limit generalizability. | Medium; must not override primary QtBase scope. | Adapt | Convert into conditional external validation or later robustness study; do not make second dataset mandatory unless scientifically justified. | DD-013 | QR-007 | RK-010 | QG-011 | `data/external`, `experiments`, `outputs/metrics` | Thesis may include future/optional robustness study. | Paper may include external validation if feasible and justified. | External validation decision record. | Deferred |
| OBS-028 | Reviewer 4 | Remove duplicated introduction paragraphs and improve language. | Editorial or journal-specific | Manuscript quality issue. | Low for architecture; relevant to future manuscript. | Adopt | Duplicate removal and language clarity are journal-independent editorial controls. | DD-011 | QR-009 | RK-008 | QG-010 | `paper/` | Thesis language consistency. | Paper editorial quality. | Editorial audit. | Open |
| OBS-029 | Reviewer 4 | State that preprocessing, training, and feature-extraction scripts will be published in GitHub/Zenodo after acceptance. | Reproducibility | Reproducibility claims may be weak. | High, but release timing needs project control. | Adapt | Adopt repository publication controls and reproducibility manifests; publication timing is journal/project dependent. | DD-001 | QR-008 | RK-007 | QG-009 | `scripts`, `src/`, `experiments`, `outputs/`, repository release docs | Thesis should document reproducible artifacts. | Paper should state availability accurately when ready. | Repository release checklist and manifest. | Open |
| OBS-030 | Reviewer 4 | References are mostly relevant and recent; no inappropriate references identified. | Documentation | Positive evidence but not a control by itself. | Low. | Defer | Positive reference assessment does not remove need for deduplication and relevance audit. | DD-011 | QR-009 | RK-008 | QG-010 | `paper/`, thesis references | No direct thesis change. | Maintain reference quality. | Reference audit. | Recorded |
| OBS-031 | Reviewer 5 | Justify perfect scores by reporting variability such as standard deviation. | Statistical validation | Perfect results may hide instability or leakage. | High, but variability alone is insufficient. | Adapt | Require result-plausibility gate with temporal repeated evaluation or bootstrap intervals; variability cannot replace leakage analysis. | DD-005 | QR-007 | RK-002 | QG-008 | `src/evaluation`, `outputs/metrics` | Thesis must explain plausibility checks. | Paper must report uncertainty when valid. | Plausibility and uncertainty report. | Open |
| OBS-032 | Reviewer 5 | Run metrics with random CV from 2 to 11 folds. | Experimental design | Random CV conflicts with chronological validation. | High as conflict. | Adapt | Reformulate into temporally valid repeated evaluation or rolling/blocked temporal analysis; do not recommend random cross-validation. | DD-005 | QR-012 | RK-012 | QG-003 | `src/evaluation`, `experiments` | Thesis must preserve deployment-realistic validation. | Paper must avoid random CV as replacement for temporal validation. | Temporal validation protocol. | Open |
| OBS-033 | Reviewer 5 | Add significance testing and two more algorithms to show superiority and stability. | Statistical validation | Weak statistical support or arbitrary algorithm choice. | Medium. | Adapt | Adopt statistical validation; reject arbitrary fixed algorithm count unless baselines are justified. | DD-012 | QR-011 | RK-009 | QG-004 | `src/evaluation`, `experiments`, `outputs/metrics` | Thesis should justify statistical tests and baselines. | Paper should report justified comparisons. | Baseline rationale and statistical test report. | Open |
| OBS-034 | Reviewer 5 | Strengthen introduction contribution and highlights by explaining how the contribution was achieved. | Scientific contribution | Contribution may remain descriptive rather than demonstrable. | High for thesis/paper writing. | Adopt | Contribution statements should link architecture, data, validation, calibration, and XAI to evidence. | DD-001 | QR-014 | RK-011 | QG-012 | `paper/`, thesis introduction | Thesis contribution section strengthened. | Paper highlights strengthened. | Contribution-to-evidence table. | Open |
| OBS-035 | Reviewer 5 | Verify whether the difference between unimodal and multimodal results is shown. | Baselines | Multimodal benefit may be unsubstantiated. | Critical; aligns with mandatory treatment rule 3. | Adopt | Unimodal, bimodal, and full multimodal comparisons are mandatory. | DD-004, DD-006 | QR-003 | RK-003 | QG-004 | `src/models`, `src/multimodal`, `experiments`, `outputs/metrics` | Thesis must compare configurations. | Paper must show configuration comparisons. | Comparison tables. | Open |
| OBS-036 | Reviewer 5 | Provide links and descriptions for source datasets used by reference articles. | Dataset construction | Dataset context may be unclear. | Medium. | Adapt | Document datasets used in this study completely; describe external/reference datasets when they are used for baselines or external validation. | DD-003, DD-013 | QR-001 | RK-004, RK-010 | QG-002, QG-011 | `docs/`, `data/external`, `paper/` | Thesis dataset context improved. | Paper dataset section improved if external datasets are used. | Dataset documentation appendix. | Open |
| OBS-037 | Reviewer 5 | Specify algorithms in the model diagram and consider algorithms from cited works. | Documentation | Architecture diagram may be too abstract. | Medium. | Adapt | Diagrams should name planned algorithms when frozen; do not adopt algorithms solely from reviewer examples. | DD-012 | QR-011, QR-014 | RK-009 | QG-004, QG-010 | `docs/SYSTEM_ARCHITECTURE.md`, `paper/`, `outputs/figures` | Thesis architecture diagram clearer. | Paper figure clearer. | Diagram review and baseline rationale. | Open |
| OBS-038 | Reviewer 5 | Compare experiments with four algorithms. | Baselines | Arbitrary algorithm count may distort design. | Medium. | Adapt | Require justified baselines; do not adopt a fixed number solely because requested. | DD-012 | QR-011 | RK-009 | QG-004 | `src/models`, `experiments` | Thesis baselines must be justified. | Paper baselines must be justified. | Baseline selection memo. | Open |
| OBS-039 | Reviewer 5 | Demonstrate improvement, or if equal, demonstrate greater stability and generalizability. | Result plausibility | Claims may overstate performance. | High. | Adopt | Improvement, stability, or generalizability claims require evidence; otherwise claims must be narrowed. | DD-005, DD-013 | QR-007 | RK-002, RK-010 | QG-008, QG-011 | `src/evaluation`, `experiments`, `outputs/metrics`, `paper/` | Thesis conclusions must match evidence. | Paper claims must be evidence-bounded. | Result-claim traceability table. | Open |
| OBS-040 | Reviewer 5 | Use four datasets individually and then integrate them, or explain each dataset in data collection. | External validation | Scope expansion may dilute clean project and conflict with primary QtBase design. | Medium. | Defer | Mandatory four-dataset evaluation is not adopted unless scientifically justified; external validation remains conditional. | DD-003, DD-013 | QR-001 | RK-010 | QG-011 | `data/external`, `experiments`, `paper/` | Thesis may discuss as future or robustness work. | Paper may defer unless journal/research question requires it. | External validation decision record. | Deferred |
| OBS-041 | Reviewer 5 | Explain why the multimodal combination matters and add practical implications. | Scientific contribution | Practical value may be unclear. | Medium, but depends on valid results. | Adapt | Practical implications must be written after leakage, ablation, and evaluation gates pass. | DD-001 | QR-013, QR-014 | RK-011 | QG-012 | `paper/`, thesis discussion | Thesis discussion should connect evidence to practice. | Paper discussion should avoid unsupported deployment claims. | Evidence-backed implications section. | Open |

## Mandatory Quality Requirements Derived from Reviewer Feedback

The following controls are adopted or adapted as project-level quality requirements:

1. Rigorous leakage analysis must cover `bug_confidence`, `msg_has_bug_kw`, `has_bug_keyword`, and any target-derived or future-derived variable.
2. Ablation studies are mandatory for critical features and modalities.
3. Unimodal, bimodal, and full multimodal comparisons are mandatory.
4. Decision-level late fusion must be implemented as a real experiment using out-of-fold unimodal probabilities.
5. Calibration must be evaluated quantitatively before and after calibration, including Brier Score and ECE.
6. Perfect or near-perfect performance must trigger a result-plausibility gate.
7. Dataset construction and labeling documentation must be complete.
8. Reproducibility manifests and repository-publication controls are mandatory.
9. Random CV=2 to CV=11 is reformulated as temporally valid repeated evaluation; random cross-validation is not recommended as a replacement for chronological validation.
10. Four-dataset evaluation is deferred unless scientifically justified.
11. A second dataset request is adapted into conditional external validation or later robustness study.
12. IEEE Access formatting, 150-word abstract, index-term taxonomy, and template instructions are journal-dependent.
13. Algorithms are not adopted solely because a reviewer suggested a fixed number; baselines must be justified.
14. Strict chronological validation is preserved.
15. The clean-project scope and `PROJECT_CONTEXT.md` remain authoritative.

## Editorial Controls for Future Journal Submission

### Journal-Independent Manuscript Quality Controls

- State the research gap and MMSDP-XAI novelty explicitly.
- Align claims with implemented experiments and verified evidence.
- Document dataset construction, labeling, features, temporal split, leakage controls, calibration, and reproducibility.
- Remove duplicate paragraphs and duplicated references.
- Use clear figure descriptions, table captions, and contribution-to-evidence mapping.
- Improve language quality before submission.
- Avoid robustness, superiority, or practical-impact claims unless supported by valid experiments.
- Ensure calibration, explainability, and fusion claims are supported by quantitative or traceable evidence.

### IEEE Access-Specific or Journal-Dependent Controls

- Apply the IEEE Access template only if IEEE Access is the selected target journal.
- Enforce the 150-word abstract limit only if required by the selected journal.
- Select IEEE taxonomy index terms only for IEEE-family submissions that require them.
- Follow IEEE-specific abbreviation placement rules only when submitting to IEEE Access or a journal with equivalent instructions.
- Use Paperpal Preflight or equivalent certificate only if required or beneficial for the target submission.
- Remove IEEE template placeholder text, placeholder DOI, corresponding-author placeholder text, and funding footnote placeholders before IEEE Access submission.

## Qt source reconstruction status

| Concern | Implementation status | Reviewer-visible boundary |
|---|---|---|
| Dataset source reconstruction | acquisition-implemented; commit-extraction-implemented; diff-extraction-implemented | Contracts reconstruct immutable repository, commit, and file-change identities; no claim is made that the real Qt dataset or diffs have been acquired. |
| File-change provenance | diff-extraction-implemented | Each raw file change retains commit, path, status, blob, mode, binary, line-count, and rename provenance with a canonical digest. |
| Merge/root reproducibility | diff-extraction-implemented | Root commits use the empty tree; merge commits use the first parent; commit and parent order come from the validated commit artifact. |
| Leakage prevention | issue-extraction-pending; target-construction-pending; feature-construction-pending | Raw diff extraction exposes no approved predictor or target construction API; empirical leakage validation remains pending. |
| Temporal reconstruction prerequisites | acquisition-implemented; commit-extraction-implemented; diff-extraction-implemented | Stable source identities and ordered raw diffs are prerequisites only; temporal splitting remains experiment-pending. |
| External validity | experiment-pending | No empirical result or generalization claim is made. |
