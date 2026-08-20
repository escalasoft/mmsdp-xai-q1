# Sprint 10.8.2.31 — Probability-only one-shot temporal TEST evaluation

> **THIS IS FINAL ONE-SHOT TEMPORAL TEST EVIDENCE FOR THE FROZEN CONFIGURATION.**

## Scientific decision

`SPRINT_10.8.2.31_GO`

The sole authorized predictive access to the canonical temporal TEST partition
completed under the unchanged Sprint 10.8.2.30 final contract. The result is
preserved as evidence and did not trigger any modeling change.

## Pre-flight and TEST opening

- Branch: `sprint-10/jit-defects4j-one-shot-test-evaluation`
- HEAD at clean initial pre-flight: `0f7f2fe3b25d8a29b21074b9b311c1cb28c10ec8`
- Sprint 10.8.2.30 merged ancestor: `f93a439`
- Initial worktree: clean
- Prior TEST state: `TEST_SEALED = TRUE`
- Prior final-configuration TEST predictions/metrics: none found
- Opening authorization: all frozen identity, ancestry, seal, population,
  architecture, calibration, leakage, and one-shot gates passed
- Predictive TEST scoring count: exactly **1**

Sprint implementation files were necessarily uncommitted after the clean initial
gate because the sprint explicitly prohibits commits. The runner allowed only
Sprint 31 paths to differ and continued to enforce all frozen upstream paths.

## Frozen identities

| Identity | SHA-256 / digest |
|---|---|
| Canonical dataset | `e509995da233c932cafce531c13ad2cd617a0d8abbe8d81ccaa373b8f29fa519` |
| Manifest | `95b1a362f6756f641cc575cabf54a3a99e2846568d5ef110dac38a45f3d81ef1` |
| Temporal boundary | `d1b4448e22a1dba4292b9cf8969ba77db0cf9a10ef66dfddf98642cb5dc078a7` |
| Adapter | `9c22de3d15d09132af1920eec0fd02e3ea9f879a70ecbd90bc5adc7913b63d2c` |
| Baselines | `535459c72b0a91f9a82d19d1742d47feb5c7d8ab382d86756270336f7716268b` |
| Fusion | `84d08dae0dca0158b786d70c90f05e597a3a22147c5aea82ae0500aca9efe4cd` |
| Architecture | `0f0547ce58d19a7eee75a93bee6addbfe23251758c8c43fb29852f2009d0c47d` |
| Robustness result | `384e640924979d59882aa6b567b7d3216bdb7420948f66288a48d44f66e1c618` |
| Calibration protocol | `45233511ca629ea5f38e499029e0eb6dfcac7c160a52d030a31113ea36f35895` |
| Calibration execution | `578283a75ae39ba37627e1201b1221e32cc5779daf993d66fdd643e5a1772aa3` |
| Final-refit contract | `f146346caf4537ee7038e3df24065104c9dee81da6f0c8cdc0ab205701767381` |
| Final-refit audit | `9fbffbf7d4ee54911399a52ba904af1e308613fb218e7d3eb884e53c1191e09c` |

## Frozen predictor

- CODE: the six frozen structural features, the exact TRAIN-fitted
  `StandardScaler` state, and frozen candidate `jit-10.8.2.25-code-rf-2`
  (`RandomForestClassifier`, random state 0). Scaler-state digest:
  `f965086202e60c3766b7cb58e869a8bd0730efb3d0bc3f5debf95481a15b29a9`.
- TEXT: the exact TRAIN-fitted 5,000-dimensional unigram TF-IDF vocabulary,
  document frequencies, IDF, and L2 normalization state, followed by frozen
  candidate `jit-10.8.2.25-text-lr-2` (liblinear logistic regression, random
  state 0). Text-state digest:
  `fa99100fc470530d3445f08f0a855aeb42ec02ed038d434e5ed000b662fa8f35`.
- PROCESS: **EXCLUDED FROM PRIMARY PREDICTOR**; retained only as prior ablation
  evidence.
- Fusion: `p_raw_fusion = 0.5 * p_CODE + 0.5 * p_TEXT`; fixed and unlearned.
- Calibration: **ISOTONIC**, using the exact frozen Sprint 10.8.2.30 mapping.
- Classification threshold: **UNDEFINED**. No binary predictions or
  threshold-dependent metrics were generated.

## TEST integrity and population

- Observations: **4,119**
- Positives: **160**
- Nominal negatives: **3,959**
- Prevalence: **0.038844379703811605** (3.8844%)
- Duplicate project-qualified identities: **0**
- TRAIN/VALIDATION/TEST overlap: **0**
- CODE/TEXT identity alignment: exact
- Canonical identity order and target membership: preserved

## Probability-only TEST metrics

| Probability output | ROC-AUC | Average Precision | Brier Score | ECE (10 fixed equal-width bins) |
|---|---:|---:|---:|---:|
| Raw 0.5/0.5 fusion | 0.7471275890376357 | 0.1219835857951105 | 0.0399093066790040 | 0.0589563531663344 |
| Frozen isotonic calibrated | 0.7452110697145744 | 0.1128535195057349 | 0.0370225269288130 | 0.0239421727544636 |

Isotonic calibration descriptively reduced Brier Score and ECE while ROC-AUC and
AP were lower than for the raw fused scores. This observation did not alter the
frozen calibrator or any other component.

## Calibrated reliability bins

The exact frozen intervals are `[left,right)`, except `[0.9,1.0]` for the final
bin; empty bins are omitted.

| Lower | Upper | Support | Mean probability | Positive fraction |
|---:|---:|---:|---:|---:|
| 0.0 | 0.1 | 3,407 | 0.0417184252871758 | 0.0272967420017611 |
| 0.1 | 0.2 | 505 | 0.1189812085553146 | 0.0693069306930693 |
| 0.2 | 0.3 | 97 | 0.2309214889574598 | 0.0824742268041237 |
| 0.3 | 0.4 | 109 | 0.3070095862745794 | 0.2201834862385321 |
| 0.5 | 0.6 | 1 | 0.5341949689907828 | 0.0000000000000000 |

## Leakage audit

**PASS.** Predictor-schema denylist overlap was empty. Neither target, future
information, fixing/SZZ evidence, issue linkage, split membership, nor project
identifier entered the predictor. TEST labels and TEST statistics were not used
during transformation or fitting. TEST did not fit vocabulary, scaling,
models, fusion weights, or calibration. PROCESS was not scored as an input.

## Immutable artifacts and reproducibility

- Predictions (ignored generated output):
  `outputs/metrics/jit-defects4j-one-shot-test/1.0.0/predictions.jsonl`
  - SHA-256: `98b218880a73b1fdee04a3a63449099627eb542f67c4db91df9254d7db39649f`
  - Rows: 4,119
  - Scientific identity: `f7d05ef2a3dc3fb5a3eb9b20dc43f3f7ebf02f3d534ef8a29a777158936fdd99`
  - Schema: `row_index`, `project`, `commit_hash`, `target`, `p_code`,
    `p_text`, `p_raw_fusion`, `p_calibrated`
- One-shot state SHA-256:
  `f292e33e9fe4667f1811b3937c4a30f7442e4caa7665eb6b48b11bcf3607d1e5`
- Result identity:
  `ec3eaf099c1cc4eec7d24cf4d7b844a90b82a9d4ca3c1dc381e7febcd49eb34d`

Reproducibility is limited to deterministic parsing, serialization, hashing,
and metric recomputation from the immutable prediction artifact. The predictive
models will not be run against TEST again.

## Quality checks

- Focused Sprint 31 tests: PASS (11 passed)
- Relevant evaluation/calibration/fusion/robustness tests: PASS (38 passed)
- Full pytest suite: PASS (1,360 passed, 1 skipped)
- Ruff on Sprint 31 Python files: PASS
- Python compilation: PASS
- `git diff --check`: PASS

## Limitations

This is evidence from one temporal TEST partition within JIT-Defects4J. It is not
external validation across independent datasets, does not establish universal
generalization or causality, and does not support a statistical-superiority
claim. The frozen TF-IDF and structural CODE representations also limit the
scope of inference. The one-observation 0.5–0.6 reliability bin is descriptive
and should not be overinterpreted.

## Exact next recommendation

Freeze and preserve this result without any post-TEST adaptation. Proceed only
to the separately governed next scientific phase; do not use these TEST results
to change representations, features, preprocessing, models, fusion,
calibration, or thresholds.
