# Sprint 55 Block 7A — G3 Failure Forensic Report

## Controlling result

Block 7 remains `RECONSTRUCTION_NONDETERMINISTIC_STOP` with 1,732 exact G3 passes and four G3 failures. This diagnosis did not reconstruct, refit, score a model, create a repetition, alter a tolerance, or execute G4, G5, T1/T2 access, SHAP, LIME, or other XAI.

## Root-cause classification

The root unit is classified `TRUE_FITTED_MODEL_NONDETERMINISM`:

`apache/zeppelin|Logistic Regression|OOF|T|block=2`

The first semantic difference is the fitted LR `coef_` array. Rep_01 and rep_03 match exactly; rep_02 differs in 78 of 90 coefficients. Its intercept also differs. Class order, `n_iter_=[4]`, and `n_features_in_=90` are identical.

The differences are at floating-point scale:

- coefficient maximum absolute difference: `3.3306690738754696e-16`;
- coefficient maximum relative difference, using nonzero rep_01 values as denominator: `6.67708419572521e-15`;
- intercept absolute difference: `2.220446049250313e-16`;
- 47 of 105 persisted block-2 check probabilities differ, with maximum absolute difference `1.1102230246251565e-16`.

These values are diagnostic measurements, not equivalence tolerances. Exact G3 equality remains controlling. The fitted-state difference is directly evidenced; a more specific solver-internal or numeric-runtime mechanism is not persisted, so this report does not relabel the cause `NUMERIC_RUNTIME_NONDETERMINISM`.

## TF-IDF forensics

TF-IDF is exactly identical across all repetitions:

- vocabulary membership and token-to-column assignments: identical, zero differences;
- vocabulary cardinality: 90;
- vocabulary digest: `be8cb98302b3060b997991e4a936f1777a28658632dca4ae1da2d6677d1f2f5e`;
- IDF digest and values: identical, zero differing elements;
- feature order and digest: identical;
- tokenizer/vectorizer parameters: identical;
- representation-object digest: identical.

Accordingly, the evidence does not support differing input rows, row order, vocabulary tie resolution, or text-representation nondeterminism.

## Input and execution-control integrity

Classification: `INPUT_IDENTICAL`.

All three records contain the same fit membership digest (`c9adb39f…ff2a2`), prediction membership digest (`da8bcc20…32c1`), candidate `LR_C_1_0`, liblinear hyperparameters, and seed `20260901`.

The authorized TRAIN/source loader independently confirms:

- Zeppelin TRAIN: 870 ordered rows;
- block-2 fit set: 106 ordered rows;
- block-2 prediction set: 105 ordered rows;
- ordered identities, labels, and raw UTF-8 commit-message sequences have fixed matching digests recorded in `g3_three_way_state_diff.json`.

All repetitions are governed by Python 3.11.14, NumPy 2.4.6, SciPy 1.17.1, scikit-learn 1.9.0, XGBoost 3.2.0, LightGBM 4.6.0, `PYTHONHASHSEED=20260901`, and one-thread controls. No input or order inconsistency was found.

## Persistence and serialization

Executable joblib object digests differ even between rep_01 and rep_03, whose semantic fitted states and check outputs are exact matches. Therefore executable-byte identity is not used as semantic G3 identity.

For rep_02, the deserialized fitted coefficients/intercept agree with the persisted canonical-state descriptors, and its persisted check-output array differs accordingly. This rules out a hash-only, journal-only, or serialization-only artifact as the root cause.

## Recovery relationship

Classification: `RECOVERY_UNRELATED_BY_EVIDENCE`.

The root was reconstructed after recovery, but it was not the first or a near-boundary component. It is ordinal 1,491; recovery resumed at ordinal 662, leaving 829 completed units between the boundary and root. Those intervening units pass G3. Rep_03 was later reconstructed in the same recovered process and its root state matches rep_01 exactly.

The root object was persisted at approximately `2026-09-04T07:14:45Z`, within the documented rep_02 continuation interval. Component journals lack per-record timestamps, so timing alone is not treated as causal.

## Downstream causal chain

The full Zeppelin LR OOF matrix has 764 rows with identical identities, order, targets, C probabilities, and P probabilities. Only the T column differs: precisely the same 47 block-2 probabilities from the root unit.

This difference fully explains the three downstream failures:

- `C+T`: `PROPAGATED_FROM_ROOT_TEXT_OOF`. Its meta coefficients/intercept differ after receiving the changed T column.
- `P+T`: `PROPAGATED_FROM_ROOT_TEXT_OOF`. Its fitted meta-state remains exact, but its persisted check output differs when evaluated on the changed T input column.
- `C+P+T`: `PROPAGATED_FROM_ROOT_TEXT_OOF`. Its fitted meta-state remains exact, but its persisted check output differs on the changed T input column.

The `C+P` fusion negative control contains no T column and matches exactly across all repetitions. No independent fusion nondeterminism is evidenced.

Thus:

- `RAW_FAILED_LOGICAL_UNIT_COUNT = 4`
- `INDEPENDENT_ROOT_FAILURE_COUNT = 1`
- `DOWNSTREAM_PROPAGATED_FAILURE_COUNT = 3`

## Unaffected controls and scope

All selected controls pass exact G3:

- Zeppelin LR OOF C and P at block 2;
- Zeppelin LR TEXT at blocks 3–9;
- Zeppelin Random Forest, XGBoost, and LightGBM TEXT at block 2;
- all 13 other projects' LR TEXT block-2 units;
- Zeppelin LR final TEXT base predictor;
- Zeppelin LR `C+P` fusion.

The phenomenon is localized to Zeppelin, Logistic Regression, TEXT, OOF block 2, plus three T-consuming downstream fusion checks. The final base predictor is unaffected. All other 1,732 logical units remain deterministic.

The four failed units are not G3-eligible for potential XAI use. Because Block 7 remains stopped and Block 8/XAI are not authorized, this report does not decide partial-scope eligibility or remediation.

## Governance confirmation

- Original T1 predictive access/scoring: `1/1`; T1 rerun: false.
- Block 7 new T1 model queries: 0.
- T2 access: 0; state: `DENY_SEALED_REVIEWER_RESERVE`.
- G4: 0; G5: 0; XAI: 0.
- Sprint 54 evidence, Block 6, Block 6A, original Block 7 manifest, and original G1/G2/G3 result hashes remain unchanged.

No remediation is performed or recommended as authorized work in Block 7A. Any remediation requires a separate prospective human decision and protocol amendment.
