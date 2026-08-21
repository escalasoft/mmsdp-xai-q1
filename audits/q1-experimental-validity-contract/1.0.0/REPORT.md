# Sprint 10.8.2.33 — Experimental Validity, Temporal Boundary, and Provenance Contract

## 1. Objective and scientific decision

This sprint predeclares the validity contract for the new Q1 experimental campaign. It is a governance audit, not a predictive experiment. The decision is:

`SPRINT_10.8.2.33_GO_WITH_LIMITATIONS`

The campaign is safe to begin development-only Sprint 10.8.2.34 under this contract. It is not authorized to open a final boundary. The limitations below must remain explicit.

## 2. Observed repository evidence

The pre-modification repository identity inspected was branch `sprint-10/q1-experimental-validity-contract` at HEAD `f48f33e069ab65a34ac44814bacd309b1adeae4c`.

Evidence inspected included:

- Sprint 10.8.2.32 report, evidence audit, roadmap, and TEST governance;
- canonical JIT-Defects4J materialization config, implementation, audit, and dataset report;
- migration source schema, binary-label validation, denylist, Git resolution, and temporal membership contract;
- canonical model-input adapter config and implementation, including CODE/PROCESS schemas, TRAIN-fitted TEXT state, and TEST seal;
- frozen architecture and calibration protocol contracts;
- Sprint 10.8.2.31 one-shot configuration and report;
- Sprint 10.8.2.31A frozen-predictor reconstruction report and audit;
- current dataset/feature specifications and target-separation design decisions.

Repository evidence establishes a pinned canonical dataset and source package, project-qualified commit identities, canonical committer-time ordering, an ancestor-only PROCESS representation, exact-tree-diff CODE lineage, raw-message TEXT lineage, and explicit predictor denylists. It also establishes that Sprint 31 is immutable and that exact original fitted RF/LR objects were not persisted.

## 3. Observed experimental-unit and target evidence

The experimental unit is one commit. Its canonical identifier is `(project, commit_hash)`. Temporal order is `(git_committer_timestamp, commit_hash)`, with the hash providing deterministic tie-breaking.

The canonical source field `is_buggy_commit` is validated as binary and preserved as `target`. A value of `1` means the source benchmark identifies the observation commit as bug-inducing/defect-prone. A value of `0` is a closed-world nominal negative, not proof of exhaustive defect-freedom. The probability meaning is `P(y=defect-prone | commit)`.

Issue, fixing-commit, and SZZ/attribution evidence are not interchangeable. An issue describes a reported bug; a fixing commit repairs it; attribution may identify an earlier bug-inducing commit; that attributed commit is the positive prediction unit. Fixing/SZZ/issue evidence is target provenance and is prohibited as predictor input.

The pinned chain is traceable from source package/revision and `is_buggy_commit`, through binary/identity validation, canonical `target`, and separated adapter targets. The repository does not independently reconstruct the upstream benchmark creator's per-positive issue/fixing/SZZ derivation. No missing semantics were invented.

## 4. Observed feature/modality lineage and leakage audit

The exact adapted inventory contains six CODE features, four PROCESS features, and one TEXT source representation. `feature_lineage.json` records source, extraction stage, observation-time availability, fitted-state requirement, permitted use, leakage status, and justification for each.

- CODE is exact observed Git tree-change structure: changed/add/delete/modify/other file counts and mode-change count.
- PROCESS is commit topology and ancestors-only prior project history, excluding the observation and all descendants.
- TEXT is the canonical raw commit message (or fixed missing sentinel), transformed only with training-window-fitted vocabulary and TF-IDF state.

Exact denylist overlap is **0**. No modality is ambiguous and none was silently reassigned. The semantic proxy audit flags that natural commit text may contain bug/fix language. The canonical design permits raw text but forbids explicit `has_bug_keyword`, `msg_has_bug_kw`, or equivalent engineered indicators, label-informed text selection/masking, and future text/state. This is a declared representation limitation, not an exact prohibited overlap.

## 5. Predeclared methodological rules: temporal validity

Primary evidence must use expanding-window rolling-origin blocked evaluation. Ordinary shuffled/random k-fold CV is prohibited as primary evidence.

The historical development pool is canonical TRAIN plus VALIDATION only. Sprint 31 TEST is excluded from every new-campaign feature, model, fusion, calibration, threshold, or architecture choice. Within each project, rows are sorted by `(git_committer_timestamp, commit_hash)`. Five expanding origins are mechanically formed at rank fractions `1/2`, `3/5`, `7/10`, `4/5`, and `9/10`, with the last evaluation block ending at `1`. Boundaries use floor ranks; labels never move boundaries. Training is a strict prefix and evaluation is the next contiguous block.

Each training window must contain at least two positives and two nominal negatives; each validation/evaluation window must contain at least one of each. An infeasible project-window is recorded as infeasible. Its boundary is not moved, and future rows are not pooled backward. Nested tuning, learned fusion, and calibration must use an earlier fit prefix and a later contiguous development block. No row may be predicted by a model or transformation fitted on that row.

Rules frozen now are ordering, development eligibility, origin fractions, expanding/blocked structure, support checks, selection restrictions, and the final-boundary eligibility rule. Exact row memberships and support feasibility are mechanically derivable later. The new final boundary itself is not yet materialized: it must be a provenance-compatible period strictly later per project than campaign development, or an independently eligible external holdout. Sprint 31 TEST cannot substitute for it.

## 6. Predeclared methodological rules: evaluation and persistence

Training uses only the current chronological prefix. Validation/model selection uses only later development blocks. Calibration uses a reserved forward block and base predictions from a predictor that did not train on those rows. Any future threshold is selected on predeclared development validation data and persisted before final evaluation. Repeated temporal evaluation precedes a single final opening. No adaptation is allowed after final outcomes are observed.

Configuration reproducibility and fitted-object reproducibility are distinct. Configuration identity records code, schemas, hyperparameters, seeds, and procedures. It does not identify learned parameters. Before any final evaluation, every applicable preprocessor, estimator, vocabulary/order/DF/IDF state, fusion state, calibrator, threshold or explicit null, schema, dataset/split membership, seed, runtime, class order, and serialization version must be persisted. A manifest must bind component SHA-256 values and the complete predictor graph. Reload and non-final fixture prediction-equivalence checks are mandatory. This closes the future-facing Sprint 31A gap without retroactively reconstructing Sprint 31.

## 7. Predeclared factorial, fusion, and calibration governance

The exact modality factorial is:

`C`, `P`, `T`, `C+P`, `C+T`, `P+T`, `C+P+T`.

All seven use identical temporal origins. Neutral and negative contributions are retained; `C+P+T` is not presumed superior.

Fixed fusion rules/weights must be declared before evaluation. Learned fusion may use only nested out-of-time development predictions; no base learner may generate its own in-sample meta-feature. Final outcomes cannot choose fusion. Calibration candidates are UNCALIBRATED, PLATT, and ISOTONIC; fitting/comparison occurs only under a later forward/nested development protocol. Final labels cannot fit or select calibration.

## 8. Predeclared external-validation and XAI governance

External datasets must be chosen before performance access using commit-level JIT unit, construct-equivalent bug-inducing target, timestamp semantics, modality compatibility, provenance, leakage controls, and chronology. Partial compatibility must limit the external claim explicitly.

XAI is deferred until a scientifically accepted fitted predictor is frozen. It must explain that persisted predictor using permitted data, separate global/local explanation, preserve modality attribution where meaningful, make no causal claim, and never post-hoc modify the evaluated predictor.

## 9. Inherited Sprint 31/31A restrictions

Sprint 31 TEST remains immutable historical evidence. It was not rerun, rescored, refitted, reconstructed as original, or used for any decision in this contract. Sprint 31A's reconstructed objects remain audit reconstructions; they are not the missing original RF/LR objects. Historical outcomes are not optimization information for this campaign.

## 10. Limitations and unresolved items

Three limitations remain, none of which makes development-only Sprint 34 unsafe:

1. Upstream per-positive issue/fix/SZZ construction is pinned and inherited but not independently reconstructed in this repository.
2. The new final period cannot be identified until a later compatible snapshot exists; its eligibility and freeze procedure are fixed, and final evaluation remains unauthorized meanwhile.
3. Raw commit messages can naturally contain defect/fix language; engineered keyword proxies and label-informed processing are forbidden, and this limitation must be reported.

There is no unresolved ambiguity permitting target polarity changes, prohibited feature inclusion, temporal boundary adjustment based on outcomes, or evaluation with unpersisted fitted state.

## 11. Acceptance gates

The machine-readable artifact parses; required sections exist; modalities are recognized; prohibited predictor overlap is zero; temporal ordering and random-CV prohibition are explicit; the factorial is exact; Sprint 31 immutability exists; persistence components exist; configuration and fitted-state identities are distinguished; and the structural execution ledger is zero. Focused and repository quality-gate results are reported in the final human handoff.

## 12. Scientific identity and next sprint

The feature-lineage artifact SHA-256 is `6d9f112fe34567610c6df1ec861f6d58068b92ac4c9419d68677f0591197c613`. The canonical contract digest is `f36980a32278cf6a677f3a637ea0a4e30900c5bcd14a97f866f4a043aaf09119`, computed as SHA-256 over canonical JSON with `contract_digest` removed.

Exact recommendation: **Sprint 10.8.2.34 — Modality Factorial under the frozen development-only rolling-origin protocol.** It may derive memberships and evaluate all seven combinations on development origins only. It may not open any final boundary.

## 13. Execution ledger

- model training = **0**
- predictive TEST/final scoring = **0**
- calibration fitting = **0**
- XAI execution = **0**
- external dataset acquisition = **0**
