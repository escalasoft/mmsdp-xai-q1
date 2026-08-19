# JIT-Defects4J Frozen Architecture and Calibration Predeclaration Audit

## Scientific decision

**GO.** This is a control/freeze decision, not TEST generalization evidence. No
calibration candidate was fitted or selected and no TEST predictive information was
accessed.

## Inherited evidence and architecture freeze

Sprint 10.8.2.27 result identity
`384e640924979d59882aa6b567b7d3216bdb7420948f66288a48d44f66e1c618`
reported a GO on TRAIN/VALIDATION robustness: CODE+TEXT beat the metric-wise best
unimodal candidate for every declared seed, with median deltas of approximately
+0.048462 ROC-AUC and +0.031653 AP. Its paired-bootstrap intervals were above zero,
and leave-one-project-out and TRAIN-fraction sensitivity aggregates retained positive
advantages. Project heterogeneity remains a limitation.

The frozen primary predictor is the selected CODE random forest
`jit-10.8.2.25-code-rf-2` and selected TEXT logistic regression
`jit-10.8.2.25-text-lr-2`. Both use random state 0. CODE consumes six structural
features after TRAIN-fitted standardization. TEXT consumes the frozen 5,000-column
TRAIN-fitted unigram TF-IDF CSR representation. Both emit column 1 under class order
`[0, 1]`, meaning `P(y=defect-prone | commit)`. Their outputs are combined by fixed,
unlearned probability-level late fusion:

`p_fusion = 0.5 * p_CODE + 0.5 * p_TEXT`

The calibration target is this raw post-fusion probability. Calibration cannot alter
features, preprocessing, base models, or fusion weights.

PROCESS remains available for ablation and future representation research, but is not
in the frozen primary predictor. Its status is **OPTIONAL ABLATION MODALITY / NOT
SUPPORTED AS PRIMARY CONTRIBUTOR UNDER CURRENT REPRESENTATION**. This conclusion is
representation- and experiment-specific.

## Frozen identities

- Dataset: `e509995da233c932cafce531c13ad2cd617a0d8abbe8d81ccaa373b8f29fa519`
- Manifest: `95b1a362f6756f641cc575cabf54a3a99e2846568d5ef110dac38a45f3d81ef1`
- Temporal boundary: `d1b4448e22a1dba4292b9cf8969ba77db0cf9a10ef66dfddf98642cb5dc078a7`
- Adapter: `9c22de3d15d09132af1920eec0fd02e3ea9f879a70ecbd90bc5adc7913b63d2c`
- Frozen architecture: `0f0547ce58d19a7eee75a93bee6addbfe23251758c8c43fb29852f2009d0c47d`
- Calibration protocol: `45233511ca629ea5f38e499029e0eb6dfcac7c160a52d030a31113ea36f35895`

## Predeclared calibration protocol

Candidates are exactly UNCALIBRATED (identity reference), PLATT (monotonic logistic
sigmoid), and ISOTONIC (monotonic non-parametric mapping). Selection uses deterministic
five-fold `StratifiedKFold` within VALIDATION, shuffled with seed 108228. The frozen
VALIDATION support (260 positives, 3,826 nominal negatives) supports this choice.
Each fitted calibrator uses four folds and predicts the disjoint held-out fold. OOF
probabilities are restored to original VALIDATION order and scored once across all
observations. Base models and preprocessing are never refitted within these folds.

Every fit fold must contain at least two positives and two negatives; every evaluation
fold at least one of each. Isotonic additionally requires two distinct fit-fold raw
probabilities. Any pathological fold fails the protocol without changing K, seed, or
folds. Infeasible isotonic is recorded as ineligible without a fallback mapping.

Primary selection minimizes OOF VALIDATION Brier Score,
`N^-1 sum_i (p_i-y_i)^2`. Values within absolute `1e-12` are tied. Among that tie set,
selection minimizes ECE, again with absolute `1e-12`. Remaining ties prefer
UNCALIBRATED, then PLATT, then ISOTONIC.

ECE uses ten fixed equal-width bins on `[0,1]`: `[0,.1)`, ..., `[.8,.9)`, and
`[.9,1]`. Empty bins are omitted. It is
`sum_{b:n_b>0} (n_b/N) * |mean_b(y)-mean_b(p)|`.

Reliability diagrams use the same fixed bin edges for all methods; each non-empty bin
shows mean predicted probability, observed positive fraction, and support, plus the
identity line. Diagrams are diagnostic and cannot select the calibrator. ROC-AUC and
Average Precision are secondary ranking-invariance checks only; ranking changes must
be reported.

## Leakage and TEST seal

The protocol rejects target-derived, fixing/SZZ, future, split-identifier, and
issue-linkage predictors. TEXT state remains TRAIN-fitted. Calibrators consume only
frozen probabilities. Project is metadata only. TEST-derived transformations,
calibrator fitting, method selection, and threshold selection are forbidden.

`TEST_SEALED = TRUE`. No TEST predictions, probabilities, labels for predictive
evaluation, calibration/discrimination metrics, reliability diagrams, or threshold
analyses were accessed. Calibration is strictly separate from thresholding; F1,
precision, recall, MCC, accuracy, and cost/business thresholds cannot influence this
stage.

## Reproducibility, limitations, and next step

Two independent validations produced identical architecture identity, protocol
identity, machine-readable audit, and GO decision. The protocol freezes method
selection but deliberately does not define or execute the later final calibrator refit.
The evidence remains development-only; class imbalance and project heterogeneity
remain explicit limitations.

Sprint 10.8.2.29 should execute only this frozen VALIDATION cross-fitting protocol,
select exactly one candidate by the declared rule, report OOF calibration and
invariance diagnostics, keep TEST sealed, and predeclare the later final-refit and
one-shot TEST-opening procedure before any TEST access.
