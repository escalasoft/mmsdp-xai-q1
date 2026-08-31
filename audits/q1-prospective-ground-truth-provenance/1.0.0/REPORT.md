# Sprint 10.8.2.48D — Prospective Ground-Truth Provenance

## Primary classification

`PRIMARY_BENCHMARK_INFEASIBLE_CONTINGENCY_REQUIRED`

The frozen JIT-Defects4J prospective pool remains identity-complete but cannot
support the final prospective TARGET protocol. All 21 frozen repositories are
available as complete, snapshot-matching Git histories. However, Git history and
public issue access do not reproduce the benchmark's missing manual repair-line
consensus. No benchmark-defined or otherwise defensible complete-coverage maturity
rule establishes prospective negatives. The explicit stop condition is therefore
met; no further repair sprint should try to manufacture labels for this pool.

## Frozen scope and outcome

- Starting Git HEAD: `be95618ac2fb2fcf4c66043c4944651280a063f1`
- Branch: `sprint-10/q1-prospective-ground-truth-provenance`
- Frozen evidence cutoff: `2026-08-30T23:59:59-05:00`
- Projects assessed: 21
- Prospective identities: 58272
- Supported positives: 0
- Supported negatives: 0
- Right-censored: 0
- Provenance-unresolved: 58272
- Ambiguous: 0
- Eligible projects: 0
- TARGET access count: 0
- Predictive scoring count: 0

## Gate-by-gate project results

P = pass; F = fail.

| Project | N | G1 | G2 | G3 | G4 | G5 | G6 | G7 | G8 | G9 | G10 | G11 | G12 | G13 | G14 | G15 | Result |
|---|---:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:---:|:---:|:---:|:---:|:---:|:---:|---|
| ant-ivy | 420 | P | P | P | P | F | F | F | F | F | P | P | P | P | P | P | INELIGIBLE |
| commons-bcel | 3148 | P | P | P | P | F | F | F | F | F | P | P | P | P | P | P | INELIGIBLE |
| commons-beanutils | 2522 | P | P | P | P | F | F | F | F | F | P | P | P | P | P | P | INELIGIBLE |
| commons-codec | 2489 | P | P | P | P | F | F | F | F | F | P | P | P | P | P | P | INELIGIBLE |
| commons-collections | 4339 | P | P | P | P | F | F | F | F | F | P | P | P | P | P | P | INELIGIBLE |
| commons-compress | 5546 | P | P | P | P | F | F | F | F | F | P | P | P | P | P | P | INELIGIBLE |
| commons-configuration | 2573 | P | P | P | P | F | F | F | F | F | P | P | P | P | P | P | INELIGIBLE |
| commons-dbcp | 2314 | P | P | P | P | F | F | F | F | F | P | P | P | P | P | P | INELIGIBLE |
| commons-digester | 1038 | P | P | P | P | F | F | F | F | F | P | P | P | P | P | P | INELIGIBLE |
| commons-io | 5631 | P | P | P | P | F | F | F | F | F | P | P | P | P | P | P | INELIGIBLE |
| commons-jcs | 1762 | P | P | P | P | F | F | F | F | F | P | P | P | P | P | P | INELIGIBLE |
| commons-lang | 7133 | P | P | P | P | F | F | F | F | F | P | P | P | P | P | P | INELIGIBLE |
| commons-math | 1571 | P | P | P | P | F | F | F | F | F | P | P | P | P | P | P | INELIGIBLE |
| commons-net | 2366 | P | P | P | P | F | F | F | F | F | P | P | P | P | P | P | INELIGIBLE |
| commons-scxml | 1206 | P | P | P | P | F | F | F | F | F | P | P | P | P | P | P | INELIGIBLE |
| commons-validator | 2098 | P | P | P | P | F | F | F | F | F | P | P | P | P | P | P | INELIGIBLE |
| commons-vfs | 3885 | P | P | P | P | F | F | F | F | F | P | P | P | P | P | P | INELIGIBLE |
| giraph | 169 | P | P | P | P | F | F | F | F | F | P | P | P | P | P | P | INELIGIBLE |
| gora | 623 | P | P | P | P | F | F | F | F | F | P | P | P | P | P | P | INELIGIBLE |
| opennlp | 2601 | P | P | P | P | F | F | F | F | F | P | P | P | P | P | P | INELIGIBLE |
| parquet-mr | 4838 | P | P | P | P | F | F | F | F | F | P | P | P | P | P | P | INELIGIBLE |

G1 temporal identity; G2 strict post-boundary; G3 zero overlap; G4 historical
construct compatibility; G5 supported positive; G6 supported negative; G7
affirmative negative; G8 maturity; G9 provenance; G10 CODE; G11 PROCESS; G12
TEXT; G13 schema; G14 LOPO/CPDP isolation; G15 deterministic non-predictive
selection.

## Provenance limitations and stop decision

The local evidence contains commit identities, timestamps, parents, diffs, raw
messages, and full history for blame. It does not contain prospective validated
defect mappings, validated fixing commits, or the manually agreed repair lines
required by JIT-Defects4J semantics. A fixing commit is never treated as an
inducing commit. Waiting-time literature describes observed-label mechanisms and
their false-negative risk; it does not justify inventing a ground-truth window for
this benchmark. Consequently no absence-of-evidence zero and no premature
right-censoring state is created.

The primary benchmark is not scientifically viable for the final prospective
TARGET protocol. Contingency evaluation is required. ApacheJIT v2 is the first
candidate because a public versioned archive and construction scripts are
accessible, but its suitability is **not yet established** and it was neither
acquired, trained, nor scored in 48D.

## Verification

- Focused tests: PASS: 14 passed in 7.77s
- Relevant regressions: PASS: 45 passed in 30.93s
- Full suite: 1569 passed, 1 skipped, 2 failed, 23 errors in 137.78s; all 25 non-passing cases are EXPECTED_HISTORICAL_INTEGRITY_GUARD; 0 48D_REGRESSION, 0 PREEXISTING_FAILURE, 0 UNKNOWN_REQUIRES_INVESTIGATION
- Ruff: PASS: all changed Python files
- `git diff --check`: PASS
- Manifest: PASS: all 13 payloads

## Files created or modified

- `src/dataset/prospective_ground_truth.py`
- `src/experimentation/q1_prospective_ground_truth_provenance.py`
- `scripts/materialize_q1_prospective_ground_truth_provenance.py`
- `tests/dataset/test_prospective_ground_truth.py`
- `tests/experimentation/test_q1_prospective_ground_truth_provenance.py`
- `audits/q1-prospective-ground-truth-provenance/1.0.0/`

## Exact recommended next sprint

Acquire and audit the versioned ApacheJIT v2 replication archive for row-level
issue/fix/SZZ provenance, timestamps, repository resolution, raw CODE/PROCESS/TEXT
reconstruction, class support, temporal partitions, and LOPO/CPDP compatibility.
Do not train or score any contingency TARGET until that evidence audit passes.
