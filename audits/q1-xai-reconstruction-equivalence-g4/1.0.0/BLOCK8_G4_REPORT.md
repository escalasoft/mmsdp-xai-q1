# Block 8 G4 Row-Level Raw T1 Equivalence Report

## A-E. Authorization, frozen scope, representative state, reference, and accounting

Human G4-only authorization was applied to exactly 389 Block 7B-eligible model identities. The three frozen Zeppelin Logistic Regression fusion exclusions were not queried. `rep_01` was frozen before any T1 feature access as the sole representative for scopes whose complete dependency closure passed exact G3. Sprint 54 evidence and every parent manifest/hash were verified before and after execution.

The separate technical ledger records 3787 unique T1 feature rows, two feature-access events (one fail-closed before querying and one successful execution), one authorized identity-schema diagnostic access, and 4032 feature-row access operations across those attempts. The successful execution used 14 project batches, 389 persisted reconstructed-component queries, and 105862 row-probability comparisons.

## F-H. Execution distributions

Exact results by algorithm, configuration, and project are persisted in `g4_summary.json`. Every one of the 389 authorized scopes is represented exactly once in `g4_scope_results.jsonl`.

## I-J. Unimodal and multimodal raw equivalence

Unimodal: 168 pass, 0 fail, 168 total. Multimodal: 221 pass, 0 direct fail, 0 upstream-ineligible, 221 total. Fusion inputs used the frozen modality order and only base probabilities whose own raw G4 state passed.

## K-N. Exact outcomes, errors, and dependency propagation

- Pass: 389
- Fail: 0
- Ineligible upstream: 0
- Unresolved: 0
- Maximum observed absolute error: `0.0`
- Maximum observed relative error where defined: `0.0`

Failed or propagated scopes:

None.

## O-S. Exclusions and governance

The excluded Zeppelin Logistic Regression `C+T`, `P+T`, and `C+P+T` scopes received zero T1 model queries. Historical Sprint 54 predictive access/scoring remain 1/1 and rerun remains false. `T2_ACCESS_COUNT = 0`; `T2_STATE = DENY_SEALED_REVIEWER_RESERVE`. T2 remains untouched and reserved for future reviewer-facing validation under a separately frozen protocol. G5 execution is 0 and XAI execution is 0.

## T. Validation

Focused tests verify the 392/389/3 universe, pre-query representative policy, exclusion enforcement, absence of fitting/reconstruction and aggregate metrics, exact row/model alignment, immutable tolerances/hashes, technical counters, T2/G5/XAI zeros, and artifact manifest integrity. Relevant Sprint 54 through Block 7B governance regressions are reported separately in the completion handoff.

## U-V. Scientific outcome and next action

`block8_outcome = FULL_G4_RAW_EQUIVALENCE_READY_FOR_G5_REVIEW`

This outcome establishes only raw row-level T1 predictive equivalence for passing reconstructed scopes. It does not make reconstructed state original, validate explanations, authorize G5/XAI, establish multimodal superiority, or support causal interpretation. The next action is human review of this G4 package. Any G5 or method-specific XAI work requires a separate prospective authorization and must be limited to scopes allowed by this result.
