# Sprint 50-R1 prospective temporal-protocol amendment

**Classification:** `PASS_50_R1_TEMPORAL_PROTOCOL_AMENDMENT_READY_FOR_HUMAN_AUTHORIZATION`

THIS AMENDMENT WAS DEFINED BEFORE OBSERVING ANY SPRINT 50 CV=2..11 PREDICTIVE RESULTS.

The amendment resolves both known blockers at the protocol and membership-construction level. It does not authorize or execute the predictive campaign; human authorization remains mandatory.

## 1. Baseline and frozen identity

- Branch: `sprint-10/q1-robustness-cv-statistics-calibration`
- Starting HEAD: `2a140be481d29949d2fe0fd74dc5c99aeeecd143`
- Frozen 48F-R1 payloads verified: 26
- Sprint 49 campaign payloads verified: 22
- Frozen rows, labels, features, and partition values were not changed.

## 2. Sprint 50 blockers reproduced

- K2_STACKING_META_WARMUP_UNAVAILABLE affected 224 nominal conditions.
- K10_K11_TRAIN_PARTITION_CONFLICT affected 784 nominal conditions.
- The original Sprint 50 stop was scientifically correct.

## 3. Temporal block reconstruction

| Blocks | Frozen provenance | Evaluation role | Later history role |
|---|---|---|---|
| 1 | TRAIN | none; K2 inner history | K2 through K11 |
| 2–8 | TRAIN | CV=block | subsequent CV origins |
| 9 | TRAIN+VALIDATION | CV=9 | CV=10 and CV=11 |
| 10 | VALIDATION | CV=10 | CV=11 |
| 11 | VALIDATION | CV=11 | none |

Exact project/block timestamps, SHAs, support, provenance counts, and eligible predecessors are in temporal_block_reconstruction.csv (154 rows).

## 4. Exact CV semantics

For project p and K in {2,...,11}: H(p,K) is every authorized development row in blocks b<K; E(p,K) is every authorized development row in block K. The required inequality is max(time(H)) < min(time(E)). This is temporally ordered expanding forward validation, never shuffled K-fold CV. Frozen partition is provenance/access metadata; temporal role is history or evaluation relative to K.

## 5. K2 scientific analysis and decision

Synthetic/future backfill is rejected. No earlier outer block exists. The accepted prospective construction orders block 1 and splits at floor(N/2): the first half fits base pipelines and transformations; those pipelines predict the second half; second-half OOF probabilities and labels fit the meta-model; final base pipelines fit all block 1; evaluation is block 2. Thus max(inner-fit) < min(meta-prediction) and max(meta-prediction) < min(block-2 evaluation). The boundary is fixed, symmetric, and not chosen from predictive metrics. Class support was used only as an estimability gate. Every project has both classes on both inner sides.

K2 final decision: K2_LATE_FUSION_CAUSALLY_ESTIMABLE_BY_NESTED_TEMPORAL_SPLIT.

## 6. K10/K11 scientific analysis and decision

48F defines fold history as blocks <K and authorizes development use of TRAIN/VALIDATION while denying T1/T2. Therefore an earlier VALIDATION-provenance row may serve as later fold history if its immutable partition value is retained, it strictly predates evaluation, frozen Sprint 49 hyperparameters are used, and all fitting remains history-only. The new builder retains each row's original partition; it does not relabel.

K10/K11 final decision: K10_K11_CAUSAL_ROLE_AMENDMENT_JUSTIFIED.

## 7. Prospective amendment, leakage audit, and gates

The smallest change is a Sprint-50-specific fold builder plus the K2 inner membership builder and fit-scope guard. Historical builders and contracts remain unchanged. Every history/evaluation pair is disjoint and strictly ordered; no evaluated or future row may fit a transformer, base model, or meta-model; no synthetic OOF backfill is permitted. All gates G1–G15 pass, but automation does not authorize campaign execution.

## 8. Factorial, counters, and limitations

The nominal 14 × 4 × 7 × 10 = 3,920 domain is preserved. The amendment affects 224 K2 late-fusion conditions and 784 K10/K11 conditions. T1/T2 training, scoring, calibration, and XAI counters are all zero. Model fits, predictive scores, calibration fits, XAI runs, and Sprint 50 conditions are all zero.

The K2 meta window for Zeppelin contains only 4 positives, so its K2 late-fusion estimate may have high variance. This is retained and reported, not optimized away. CV=9 now follows the frozen whole-block definition and therefore includes both TRAIN- and VALIDATION-provenance rows in block 9; it is not silently equated with Sprint 49's TRAIN-only K9 diagnostic.

## 9. Implementation and verification

Added one prospective config, one Sprint-50-specific membership module, 34 focused tests, and a versioned evidence package. Focused tests: 34 passed. Relevant regressions: 36 passed. Full suite: 1,662 passed, 1 skipped, 2 failed, 23 errors. All 25 nonpassing cases are expected historical integrity guards; new regressions and unknown failures are zero. Changed Python files pass Ruff; git diff check passes; two deterministic regenerations and all amendment/frozen manifests pass.

No predictive CV result was generated, inspected, or used to define this amendment. No performance improvement or superiority is claimed.
