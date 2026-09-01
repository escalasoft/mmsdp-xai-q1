# ApacheJIT 48F-R1 Final Dataset Freeze Scientific Closure

## Decision

**PASS_48F_R1_FINAL_DATASET_FREEZE_READY_FOR_COMMIT**

The frozen input population contains 14 performance-independent 48E-R1
candidates. Evidence-driven E1-E15 outcomes yield 14 ELIGIBLE,
0 INELIGIBLE, and 0 UNRESOLVED
candidates; no final count is required. Apache Hadoop remains a pre-candidate exclusion
because it has zero positive observed labels. The eligible substrate contains
94,710 immutable row identities. No predictive performance was inspected.

## Scientific boundary

ApacheJIT labels are **BENCHMARK_DEFINED_OBSERVED_LABEL** values. They are reproducible benchmark-defined
observations and are not asserted to be verified ground truth. Negative labels are not
verified-clean commits. Fixing commits and bug-inducing commits remain distinct.

CODE (`la`, `ld`, `nf`, `nd`, `ns`, `ent`) and PROCESS (`ndev`, `age`, `nuc`,
`aexp`, `arexp`, `asexp`) numeric values are **APACHEJIT_V2_FROZEN_BENCHMARK_FEATURE**
values, not claimed as full primary-Git reconstructions. CODE has current-commit/direct-parent
semantics; a deterministic 14-row spot-check exactly reproduced `la`, `ld`, and `nf`.
PROCESS uses the published historical definitions and was
**NOT_INDEPENDENTLY_REPRODUCED_IN_48F_R1**; any future replay must be strict ancestor-only.
TEXT is independently reconstructed from the prediction Git commit object. Global
representation fitting and engineered bug/fix/issue/SZZ indicators are prohibited.

## Temporal and cross-project freeze

Rows use normalized raw Git author time plus SHA tie-break. The original thesis plan was
70/15/15. Before predictive experimentation, 48F amended this to 60% TRAIN, 20%
VALIDATION, and 20% TEST: T1 is the chronologically first 4 total percentage points
(20% of TEST), while T2 preserves the final 16 points (80% of TEST). The larger
VALIDATION reserve supports controlled selection without TEST; the larger future reserve
and limited T1 strengthen progressive final-evidence protection. Eleven development blocks
define future expanding folds 2-11. CPDP/LOPO is strict source-only; Hadoop-family
identities cannot cross a source-target boundary.

## TEST governance

Current predictive TEST access is **DENY**. T0 structural verification is allowed. T1
and T2 memberships are frozen but neither was executed. Future access is sequential:
T0, human review, T1, human review, T2.

## Execution ledger

`model_training_count = 0`, `predictive_scoring_count = 0`,
`calibration_fit_count = 0`, `test_predictive_access_count = 0`, and
`xai_execution_count = 0`.

## Verification

Focused tests: {'passed': 10, 'failed': 0}. Relevant regressions:
{'passed': 411, 'failed': 0}. Full suite:
{'passed': 1584, 'skipped': 1, 'failed': 2, 'errors': 23, 'expected_historical_guard_nonpassing': 25}. New unexplained regressions:
0. Ruff:
PASS. Git diff check:
PASS. Deterministic regeneration:
PASS_IDENTICAL_MANIFEST_AND_PAYLOAD_HASHES.

## Authorization boundary

TRAIN/VALIDATION experimentation: **YES**. T0 structural TEST verification: **YES**.
T1 predictive TEST: **NO**. T2 final predictive TEST: **NO**.
