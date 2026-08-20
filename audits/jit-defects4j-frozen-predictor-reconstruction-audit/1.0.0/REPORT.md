# Sprint 10.8.2.31A — Frozen predictor reconstruction audit

## Scientific decision

`SPRINT_10.8.2.31A_GO_WITH_LIMITATIONS`

The frozen predictor provenance is scientifically consistent. A deterministic
TRAIN/VALIDATION-only reconstruction reproduced the frozen CODE preprocessing
state, frozen VALIDATION fusion metrics, and the final isotonic calibration
state. The sealed TEST artifact passed every integrity check and no second TEST
predictive scoring or post-TEST adaptation occurred. The limitation is that the
original fitted RF and LR estimator objects were not persisted before TEST, so
their byte-level identity cannot be directly compared with reconstructed fitted
objects.

## Objective and boundary

This was a post-TEST provenance and reconstruction audit, not a predictive
experiment. Reconstruction consumed only the persisted canonical TRAIN and
VALIDATION adapters. The audit never loaded or transformed TEST predictor
features and never invoked a predictor on TEST. It read the immutable Sprint 31
prediction artifact for integrity and metric recomputation, and read only the
canonical TEST identifier/target ledger to verify row membership and order.

No feature, representation, preprocessing step, estimator configuration,
fusion weight, calibrator, or threshold was changed. PROCESS remained excluded
and the classification threshold remained undefined.

## Starting state and ancestry

- Required audit branch already existed and was checked out before changes:
  `sprint-10/jit-defects4j-frozen-predictor-reconstruction-audit`.
- Initial worktree: clean.
- Starting HEAD: `c2e55b1e890b4dccb3d88d613d930045f57f75ef`.
- Local `main`: `c2e55b1e890b4dccb3d88d613d930045f57f75ef`.
- `origin/main`: `c2e55b1e890b4dccb3d88d613d930045f57f75ef`.
- Sprint 31 is in ancestry through commit
  `be9b27e54ceb23e327bb22a001f6b39291029339`.
- Sprint 28: `188718c02dcdf6f8fbef6d9f69da894f0084315e`.
- Sprint 29: `c8f6c9b3ef1ebe544ee40e575a41c5e2ba319932`.
- Sprint 30: `f93a439dc2ce38d7d5917d2583197b696823bf04`.
- Sprint 31: `be9b27e54ceb23e327bb22a001f6b39291029339`.

## Immutable contracts and evidence

| Sprint | Artifact | File SHA-256 / scientific identity |
|---|---|---|
| 28 | calibration protocol config | `c0f7e71058d5c17b90c0021e4908c8d072bf2807fe3657efcc63957b1bf5224d` |
| 28 | calibration protocol audit | `231135d990ba9002e5b7b6c8c2c96b00816752ce7d39a08ad36762bd5e5be494` |
| 28 | architecture identity | `0f0547ce58d19a7eee75a93bee6addbfe23251758c8c43fb29852f2009d0c47d` |
| 29 | calibration execution config | `8979711a83ecc8a943f714030419620bac3a86c1426a2e9c7c7ee78687e63a36` |
| 29 | calibration execution audit | `38eadcb864290d47ff1dcc089dcd01fdc18eae986fcfa9dcf9f7f58aedba8bea` |
| 29 | calibration execution identity | `578283a75ae39ba37627e1201b1221e32cc5779daf993d66fdd643e5a1772aa3` |
| 30 | final-refit config | `d7f26a3010163c98ceeb7c5e408f1df66eb288de3ffbc037d5696ab1ef40e67e` |
| 30 | final-refit audit | `5d459e1332fda4311112dcb105c1ac749db6670b6484afe1368a1217362f4da6` |
| 30 | final contract identity | `f146346caf4537ee7038e3df24065104c9dee81da6f0c8cdc0ab205701767381` |
| 31 | one-shot config | `cf37d0d372e6e2177fac8db656c58915a74027206c4d98c579d8d6d449a72fc7` |
| 31 | one-shot audit | `723e48b81c42230a710c51718470d93db9e6e6ecf035eb06bd5d503552ef0143` |
| 31 | sealed predictions | `98b218880a73b1fdee04a3a63449099627eb542f67c4db91df9254d7db39649f` |
| 31 | one-shot state | `f292e33e9fe4667f1811b3937c4a30f7442e4caa7665eb6b48b11bcf3607d1e5` |

## Frozen predictor identity and reconstruction

### CODE

The exact ordered schema was verified as `changed_file_count`, `files_added`,
`files_deleted`, `files_modified`, `files_other`, `mode_change_count`.
The population was canonical TRAIN (19,114 observations; 1,912 positive).
The TRAIN-fitted `StandardScaler` numeric state reproduced the pre-TEST frozen
digest exactly:
`28c09e8e32fab4cbc51ba939b32e4d6b82fa394e5441df71724cfeca361b9bb3`.

Candidate `jit-10.8.2.25-code-rf-2` reconstructed as the repository RF adapter
over `sklearn.ensemble.RandomForestClassifier`, with 100 estimators, Gini,
bootstrap, `max_depth=12`, `max_features=sqrt`, `min_samples_leaf=5`, no class
weight, and `random_state=0`. The reconstructed fitted-state digest is
`d38f55790fafd446877a8f256dac551e656896cceaee7e2a286c65f4b9266d77`.

Sprint 31 reported a scaler wrapper digest that differs because it serialized
the fit-partition label as `TRAIN` instead of the earlier contract's `train`.
The numeric mean and scale are the same, and reconstruction reproduced the
authoritative pre-TEST preprocessing digest.

### TEXT

The TF-IDF state is explicitly persisted and records TRAIN-only fitting over
19,114 documents, lowercase unigram tokenization, minimum document frequency
2, maximum 5,000 features, descending TRAIN document-frequency/token ordering,
sublinear TF, smoothed IDF, and L2 normalization.

- Vocabulary dimension: 5,000.
- Vocabulary/order digest:
  `ed9ce9bb9914e106990e6d2b12acf2f5110f4ce41b7b742b91a7aa1281c38b94`.
- IDF digest:
  `2f90a6a7bebbe0fd84ed1dc199abac000a356daf8a4a7b02c1d150ad904b9607`.
- Complete text-state digest:
  `fa99100fc470530d3445f08f0a855aeb42ec02ed038d434e5ed000b662fa8f35`.

Candidate `jit-10.8.2.25-text-lr-2` reconstructed as the repository LR adapter
over `sklearn.linear_model.LogisticRegression`, with `C=1.0`, liblinear,
intercept enabled, no class weight, tolerance 0.0001, maximum 2,000 iterations,
and `random_state=0`. Its reconstructed fitted-state digest is
`1800158649a5d2908cdd2def06a35e6a397b4ab44d8ddc69ecf0a6ecff7389aa`.

### Fusion

The exact frozen equation is:

`p_raw_fusion = 0.5 * p_CODE + 0.5 * p_TEXT`

Weights are fixed and unlearned. PROCESS is excluded. The reconstructed
VALIDATION raw-probability digest is
`71d5c82ab0038b85bbb7f697b9ae1beb979bf3d0b27647cad2df4388d16fbfc3`,
and its ROC-AUC and Average Precision match the frozen seed-0 robustness
reference within the pre-existing absolute tolerance of `1e-12`.

### Calibration

The selected method remains ISOTONIC with `out_of_bounds=clip`. Refitting the
audit calibrator only on the canonical VALIDATION raw scores and labels produced
an exact array match for all frozen X and Y thresholds. The calibration-state
digest is
`7c5ca79f929514e3db71ce75f37dd82806075b9fe193780387dc4d8401764dbc`.
The base score generator is the same reconstructed TRAIN-only CODE+TEXT system;
no TEST information entered calibration.

## Sealed TEST artifact integrity

- Prediction rows: 4,119; positives: 160; nominal negatives: 3,959.
- Row indices: exact contiguous order 0–4,118.
- Project-qualified identifiers: unique and in exact canonical TEST order.
- Stored targets: exact canonical target-ledger match.
- Raw probabilities: exact row-wise 0.5/0.5 fusion equality.
- Calibrated probabilities: exact equality to the frozen isotonic mapping.
- Prediction SHA-256: exact match to config, Sprint 31 audit, and one-shot state.
- One-shot state: `SCORED_EXACTLY_ONCE`, attempt 1.
- Metric recomputation: exact match to the Sprint 31 report.

| Output | ROC-AUC | Average Precision | Brier | ECE-10 |
|---|---:|---:|---:|---:|
| Raw | 0.7471275890376357 | 0.1219835857951105 | 0.0399093066790040 | 0.0589563531663344 |
| Isotonic | 0.7452110697145744 | 0.1128535195057349 | 0.0370225269288130 | 0.0239421727544636 |

## Leakage audit

**PASS.** TEST features were not loaded, transformed, or scored. TEST labels
were not used for fitting, reconstruction, selection, tuning, or the scientific
decision. The canonical identifier/target ledger and persisted prediction rows
were used only for artifact integrity, and persisted probabilities/targets were
used only for metric recomputation. Base estimators and CODE scaling used TRAIN
only; isotonic reconstruction used canonical VALIDATION only. No threshold was
defined and no post-TEST adaptation occurred.

## Reproducibility findings and limitations

Scientific provenance is defensible: immutable pre-TEST contracts identify the
schema, representations, populations, configurations, random states, fusion,
and calibrator; persisted TF-IDF and calibration states match; deterministic
development reconstruction reproduces the frozen validation evidence; and the
sealed TEST artifact is internally and externally consistent.

Exact fitted-object comparison is unavailable because neither the original
fitted RF nor LR estimator was serialized before TEST. Their reconstructed
states now have stable audit digests, but those digests have no pre-TEST fitted
object digest to compare against. This is a persisted-artifact reproducibility
gap, not evidence of leakage or material predictor inconsistency. It prevents an
unqualified GO and yields `GO_WITH_LIMITATIONS`.

## Exact final decision and next action

`SPRINT_10.8.2.31A_GO_WITH_LIMITATIONS`

Freeze and preserve this audit. Do not rerun TEST scoring and do not use TEST
results to modify the frozen predictor. If a later governance sprint addresses
reproducibility infrastructure, it may require persisting fitted-estimator state
before any future sealed evaluation, but it must not retrofit or replace the
already sealed Sprint 31 evidence.

## Quality gates

- Focused Sprint 31A tests: PASS (2 passed).
- Relevant calibration/fusion/evaluation tests: PASS (125 passed).
- Full repository suite: PASS (1,362 passed, 1 skipped).
- Ruff on modified Python files: PASS.
- Python compilation checks: PASS.
- `git diff --check`: PASS.
