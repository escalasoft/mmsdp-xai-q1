# Block 7B Partial G1-G3 Eligibility Disposition

## A. 392-scope universe verified

The frozen confirmatory plan contains exactly **392** project/algorithm/configuration scopes and **392** unique `model_identity_sha256` values. Every scope appears exactly once in `scope_g1_g3_eligibility.jsonl`; every required dependency resolves to the frozen 1,736-unit G3 universe.

## B-D. Counts

- Eligible for possible future G4 review: **389**
- Ineligible: **3**
- Unresolved: **0**
- G1/G2 ineligible: **0**

The frozen component result remains 1,732 exact G3 passes and four G3 failures: one independent root plus three propagated failures. This disposition does not alter those results.

## E-F. Affected scopes and dependency paths

Only the following scopes are ineligible:

1. `apache/zeppelin | Logistic Regression | C+T` (`0147ca63a4a2489b26c36de8f710f55cbf2c260d0c2b17465ef3955085c611c9`)
2. `apache/zeppelin | Logistic Regression | P+T` (`dc23ba88042d5f02f5713e0e667f67d7b4fcb1e5031aafe01249bf4238557333`)
3. `apache/zeppelin | Logistic Regression | C+P+T` (`76c18e414f03fb10ea26dbb9b021b843a337cf69ec28f9e51f03e0d6cdc50837`)

For each, the dependency path is the failed root `apache/zeppelin|Logistic Regression|OOF|T|block=2` -> the configuration-specific failed `FUSION_META` component -> the final project scope. Each is classified `G3_INELIGIBLE_PROPAGATED_DEPENDENCY`. No final scope is classified as a direct root failure because the failed component is an OOF fold state used only by fusion training.

## G. Unaffected Zeppelin Logistic Regression scopes

`C`, `P`, `T`, and `C+P` remain eligible. In particular, unimodal `T` requires the independently G3-passing `FINAL_BASE|T` state and does not consume any OOF state. It is therefore not excluded by the failed TEXT OOF fold.

## H-J. Eligibility distributions

- Algorithm: Logistic Regression 95 eligible / 3 ineligible; Random Forest, XGBoost, and LightGBM each 98 eligible / 0 ineligible.
- Configuration: `C`, `P`, `T`, and `C+P` each 56 eligible; `C+T`, `P+T`, and `C+P+T` each 55 eligible / 1 ineligible.
- Project: `apache/zeppelin` 25 eligible / 3 ineligible; each of the other 13 projects 28 eligible / 0 ineligible.

Full enumerations by algorithm, configuration, and project are in `partial_eligibility_summary.json`.

## K-L. Outcomes preserved

- `historical_execution_outcome = RECONSTRUCTION_NONDETERMINISTIC_STOP`
- `post_forensic_scope_disposition = PARTIAL_G1_G3_RECONSTRUCTION_READY_FOR_G4_REVIEW`

The latter is a provenance-separated disposition layer and does not replace the historical Block 7 result.

## M-O. Governance

T1 original predictive access remains 1, original predictive scoring remains 1, and T1 rerun remains false. Block 7/7A/7B reconstructed-model T1 queries remain 0. T2 access remains 0 and its state remains `DENY_SEALED_REVIEWER_RESERVE`. G4, G5, and XAI execution counts remain 0.

G1-G3 eligibility establishes only that a reconstructed candidate may be considered by a separately authorized future G4 review. It does not establish original-state identity, T1 equivalence, SHAP or LIME eligibility, explanatory validity, or scientific superiority. The three G3-ineligible scopes remain prohibited from model-specific XAI based on reconstructed state.

## P. Validation

The focused Block 7B tests verify the 392-scope bijection, unique model-identity linkage, exact dependency derivation, unchanged four-unit G3 failure set and counts, lack of rescue or collateral exclusion, zero protected executions, and unchanged source manifests/hashes. `MANIFEST.sha256` covers the four new disposition artifacts without modifying prior manifests.

## Q. Exact recommended Block 8 authorization scope

No Block 8 action is authorized by this package. If a later human decision authorizes Block 8, the recommended maximum scope is G4 row-level equivalence review for exactly the **389** records classified `G1_G3_ELIGIBLE_FOR_FUTURE_G4_REVIEW` in `scope_g1_g3_eligibility.jsonl`. It must exclude the three enumerated Zeppelin Logistic Regression fusion scopes. Such authorization would not include G5, XAI, T2 access, remediation, refitting, or replacement of any repetition.
