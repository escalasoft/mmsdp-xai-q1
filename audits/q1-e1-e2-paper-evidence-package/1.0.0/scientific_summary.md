# Verified feature and modality explanations for MMSDP XAI

## Scope and principal finding

The accepted evidence supports linked feature-level and modality-level explanations for 245 ActiveMQ commits in T1. CODE explanations are available for LR, RF, XGBoost and LightGBM; TEXT explanations are available for LR, XGBoost and LightGBM. Their explained unimodal outputs match the corresponding inputs to the frozen fusion instances exactly. The resulting hierarchy is traceable but not a single additive decomposition. Feature-level PROCESS explanations are unavailable because temporal provenance could not be independently established. This limitation does not demonstrate observed leakage or erase the historical predictive and E2 results.

This evidence package provides Figures A–C for bounded manuscript integration and Figure D as an explicitly partial supplementary extension. It does not revise predictive experiments or the manuscript.

## E1 CODE methods

E1 CODE explains six frozen attributes (`la`, `ld`, `nf`, `nd`, `ns`, `ent`) using previously audited reconstructed pipelines. LR uses the analytical decomposition of its logit around the frozen mean of transformed TRAIN reference data. The reference comprises 256 deterministically selected identities from an independent 3,675-row TRAIN snapshot. The imputer and LR scaler remain frozen. For RF, XGBoost and LightGBM, exact TreeSHAP uses `tree_path_dependent`, `data=None`, and `approximate=False`. RF explains the positive-class probability; XGBoost and LightGBM explain native margins. Tree baselines depend on the frozen tree path counts rather than on a new T1 background sample.

All 245 foreground commits and the eight preselected local cases were retained. Twenty deterministic repetitions were persisted for each family. The present package reads those results; it does not call predictors, explanation methods or calibrators.

## Cross-level alignment procedure

The audit joins project, T1 membership and row identifier, then links row identifiers to commit SHA values. It explicitly reconciles CODE temporal order, TEXT foreground order and E2 foreground order. TEXT NPZ arrays do not embed their identifiers; their binding relies on the frozen population ledger and documented producer indexing. Recorded pipeline digests and the component journal establish that the E1 predictor and relevant fusion instance consume the same reconstructed FINAL_BASE component.

The E2 attribution table stores the unimodal probabilities actually used in fusion. CODE probabilities are read directly from the persisted E1 arrays. For TEXT, a sigmoid is applied arithmetically to the saved native output, preserving its stored numerical type; this is neither predictor execution nor calibration. Twelve CODE links and nine TEXT links passed, each covering 245 identities. All 5,145 row/link comparisons were exact, with maximum absolute and relative discrepancy zero. These are repeated comparisons of 245 commits across configurations, not 5,145 independent commits. Three RF TEXT links have predictor identity evidence but no accepted E1 attribution.

E2 uses the historical OOF reference and explains the frozen meta-logit. Its modality contributions must not be summed with E1 contributions, which use different references and potentially different output scales. Even when both panels are expressed as logits, they concern different predictors and baselines. Arrows in Figures A and D indicate verified input correspondence only.

## Global CODE results

The global mean absolute attribution ranks differ across families. LR ranks `ent` first (0.490638 logit), followed by `nd` (0.186846) and `nf` (0.181620). RF ranks `la` first (0.088517 probability), followed by `ld` (0.033489) and `nf` (0.027080). XGBoost ranks `la` first (0.755547 native margin), followed by `ld` (0.146422) and `nd` (0.105408). LightGBM ranks `la` first (0.869414 native margin), followed by `ld` (0.199690) and `nf` (0.110202). These numbers describe within-model contribution magnitude; they do not establish relative explanatory strength across scales.

The persisted descriptive rank comparisons reinforce this model dependence. Global Spearman correlations are −0.543 for LR–RF, −0.486 for LR–XGBoost and −0.829 for LR–LightGBM. Among tree families they are 0.600 for RF–XGBoost, 0.829 for RF–LightGBM and 0.429 for XGBoost–LightGBM. These six-feature comparisons are descriptive and carry no significance or predictive superiority claim. RF and LightGBM share the same top-three feature set; the ordering and lower-ranked features are still model dependent.

Mean absolute importance does not describe the direction of every local contribution. For example, LR `ent` has mean absolute attribution 0.490638 but mean signed attribution only 0.000221, consistent with cancellation across commits. Global summaries therefore complement, rather than replace, local evidence. Table B preserves medians, population standard deviations, interquartile ranges, percentiles and sign proportions from the audited synthesis.

## Verified local hierarchy

Figure A uses LR/C+T and the first frozen E1 local identity, commit `e947927511796484e2ae0a066df7fa7b4800a578`. This display rule was fixed before reading the case values for the package. It was not chosen for correctness, confidence or visual contrast. The case belongs to the E2 foreground, although it is not a member of the historical eight-case LR/C+T E2 local selection.

For CODE, the base logit is −1.353054 and the explained logit is −1.308170, corresponding to RAW probability 0.212793. `ent` contributes +0.261165, whereas `ns` contributes −0.153513 and `nf` contributes −0.075653. For TEXT, the base logit is −1.559703 and the explained logit is 0.866426, corresponding to RAW probability 0.704001. Displayed positive terms include `issues`, `browse`, `amq`, `jira` and `deadlock`. Negative terms include `and` and `on`; their interpretation is relative to the reference, not evidence that those tokens must be present in the message. The other 2,550 feature contributions are summed within TEXT only, preserving its complete decomposition. Full token-indexed contributions remain in the figure data.

The C+T E2 baseline is −1.326734 meta-logit. CODE and TEXT contributions are +0.297632 and +2.435149, respectively, yielding meta-logit 1.406048 and RAW probability 0.803142. CODE contributes positively relative to its OOF reference even though its unimodal probability is below 0.5; a reference-relative E2 sign is not a unimodal classification. No observed defect label or correctness claim is attached to this example.

Figure D uses the same case and family in the distinct C+P+T fusion instance. Its PROCESS term is shown only at E2. Differences between Figures A and D reflect different frozen fusion models, not a causal ablation or an isolated intervention on PROCESS. The extension remains PARTIAL.

## Fidelity and deterministic stability

All CODE families passed their frozen fidelity criteria. Maximum absolute residuals are 4.4408920985e−16 for LR, 1.7541523789e−14 for RF, 3.2233074307e−6 for XGBoost and 1.0658141036e−14 for LightGBM. The corresponding maximum normalized residuals are approximately 4.2132e−16, 9.3517e−15, 8.2302e−7 and 8.3997e−15. LR uses the bound 1e−10 × (1 + |logit|), alongside its probability reconstruction check; trees use 1e−6 × (1 + |output|). XGBoost's absolute residual above 1e−6 therefore does not violate its output-dependent bound.

The maximum attribution difference across the 20 CODE repetitions is zero for each model. Historical rank, sign, top-three and total-variation diagnostics also passed. This establishes fixed-input numerical reproducibility, not robustness to perturbations, a different background, different populations or alternative models. Historical TEXT fidelity and stability are retained for the three accepted families. RF TEXT remains excluded after its exact TreeSHAP additivity failure.

## Coverage and validity boundaries

The aligned subset contains 16 model/configuration instances, each with 245 commits. All eight E1 local cases are present in the E2 foreground of each instance. However, strict overlap with E2's historical local sets is one for LR/C+P, one for LightGBM/C+P, two for RF/P+T and zero elsewhere. The RF/P+T identity overlaps do not supply accepted RF TEXT feature explanations. Local evidence should be described as preselected E1 cases linked to persisted E2 foreground explanations, not as identical historical local samples.

PROCESS remains a predictive input and an E2 component. Its missing E1 branch is labelled “E1 PROCESS not evaluated: temporal provenance not independently established.” The article must not interpret this as zero importance, technical impossibility or observed leakage. It must also avoid asserting independently established temporal provenance for all PROCESS inputs. The existing G4 predictive equivalence does not establish feature ancestry.

The 16 aligned instances record RAW calibration state. This package explains pre-calibration meta-logits and reports their persisted RAW probabilities. It neither demonstrates a separately calibrated endpoint for those instances nor supports an additive explanation of a post-calibration probability. Any broader calibration finding in the framework requires its own independent evidence.

Other boundaries include reconstructed rather than original executables, different explanatory reference regimes, bounded ActiveMQ/T1 coverage, and unavailable original CODE feature values in the E1 NPZ schema. Token contributions and CODE attributions describe model behavior rather than causal effects on defects. Numerical fidelity is not evidence of improved defect detection, developer trust or industrial utility. No generalization to all 14 projects is claimed.

## Interpretation and implications for audit

Empirically, the package establishes persistent, identity-linked explanations and exact correspondence between accepted E1 outputs and E2 inputs. As a reasoned interpretation, the separate panels make it possible to inspect how a modality-level fusion contribution relates to the behavior of the unimodal predictor that supplied its probability. This supports technical traceability of the recorded computation without claiming a single feature-to-fusion attribution calculus.

Potential improvements in QA triage, developer understanding or review efficiency remain hypotheses. They would require user studies or task-based evaluations. Causal interpretation, perturbation robustness and cross-project explanation stability also require additional validation. None is inferred from the present fixed-input audit.

## Recommended manuscript placement

Place Figure A with the explanation results to demonstrate the verified cross-level connection. Place Figure B alongside the global CODE results, retaining independent axes and explicit units. Figure C and a compact Table A should establish coverage and exclusions near the explanation methods or results. Use a reduced Table B in the main article and retain the full editable statistics as supplementary material. Table C provides the audit trail; its full 16-instance form can be supplementary. Table D should guide the threats-to-validity text. Figure D is optional supplementary material and must retain its PARTIAL label.

This recommendation does not depend on the current Word section numbering and does not modify the manuscript. It supplies evidence and draft prose for a later, separately controlled editorial update.
