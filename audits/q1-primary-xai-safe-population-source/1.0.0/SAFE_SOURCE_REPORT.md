# Sprint 56.2A — Safe TRAIN/T1 Source Audit

`NO_SAFE_TRAIN_T1_SOURCE_AVAILABLE_UNDER_FROZEN_T2_BOUNDARY`

Phase A completed without an acceptable source. Phase B was not started. No scientific source rows, selected XAI populations, models, attributions or figures were produced.

## A. Branch / HEAD
`sprint-10/q1-primary-xai-execution` / `89fe7e1c2da425ea63427d1d699d6f8a531e8c6f`. No branch switch, staging, .gitignore change, commit, push or PR.

## B. Parent outcomes
Sprint56.1 `PRIMARY_XAI_ISOLATED_RUNTIME_SMOKE_TEST_PASS`; Sprint56.2 `PRIMARY_XAI_T1_SELECTION_CONTRACT_FAILURE`. The historical blocker remains unchanged and is an access/provenance failure, not a predictive-model or XAI-method failure.

## C. Frozen universe
389/389 READY_VERIFIED; E1 168, E2 221. Exactly three apache/zeppelin LR exclusions: C+T, P+T, C+P+T. The 168 base feature definitions and 56 TEXT representation records remain protected; no scope reselection.

## D. Protected evidence
`parent_integrity_before.json` and `parent_integrity_after.json` match. Fresh SHA256 was computed for 6056 permitted files, including all 5,649 model-state objects (2,139,594,110 bytes), 0 missing references and 0 orphans. 2 prohibited payload files retain inherited manifest SHA256, Git blob ID where tracked and filesystem metadata instead of a fresh payload hash.

**Hashing boundary:** Sprint54 T1 prediction payloads contain labels/outputs. The current instruction forbids reading these bytes even to discard them, and T2 payload hashing is explicitly forbidden. Accordingly no prohibited payload was opened merely to satisfy a checksum step. Their recorded hashes and metadata remained unchanged, but fresh byte-equivalence is **not claimed** for unrehashable payloads. This limitation is explicit and cannot be treated as a successful materialization-integrity proof.

## E. Search paths
All eight requested roots were inventoried by paths/stat metadata: audits/, data/, artifacts/, outputs/, experiments/, configs/, src/, tests/. See `source_discovery.json` and `path_inventory.json`. Scientific payloads were not opened to search their content. Source producers, safe provenance/manifests and relevant Git history were inspected.

## F. Candidate inventory
113 candidate records retain path, type, tracking status, source provenance, partition/addressability, safety and field availability, order/coverage/reconciliation, size, declared source hash, verdict and exact reason. Missing hashes are null rather than invented; unsafe payload hashes are inherited, not recomputed.

## G. Classifications
| Verdict | Candidates |
|---|---:|
| INCOMPLETE_SOURCE | 29 |
| NOT_RELEVANT | 26 |
| PROVENANCE_INSUFFICIENT | 4 |
| SEMANTIC_MISMATCH | 47 |
| T2_TRAVERSAL_REQUIRED | 7 |

No candidate received a SAFE verdict.

## H. Segregated sources
The Sprint56.1 separate TRAIN file has only 80 preselected activemq smoke rows, lacks class labels and does not cover the other projects or T1. Its TRAIN membership metadata is also first-project only and has no full C/P/classes. Parent56.2 population files are intentionally empty. The aggregate T1 registry records a count/hash/path but supplies no identity rows. Qt/JIT-Defects4J exports have a different producer/dataset lineage and cannot replace ApacheJIT.

## I. Upstream ApacheJIT
Acquisition provenance identifies the original balanced train subset (44,834 rows, supplied synthetic years 2003–2016) and labelled/featured 2017–2019 test subsets. The frozen campaign explicitly rebuilds per-project chronological partitions from raw UTC timestamps and rejects supplied synthetic year as authoritative. Therefore `apachejit_train.csv` is not a verified full frozen TRAIN export. `apachejit_test_*.csv` cannot be consumed as identity-only T1 because label/feature bytes are inseparable without a proven direct-access map. `apachejit_total.csv` is the parent of all campaign partitions; scanning it or rebuilding a row index would expose T2. ZIP member access does not isolate final partitions. Year/issue/link/Kamei files do not establish the missing partition/location proof. Notebook outputs were not opened because embedded scientific rows cannot be ruled out.

## J. Pre-existing indexes and Git history
No relevant SQLite/Parquet/Arrow/Feather/BGZF-GZI/zran/byte index was found. Relevant acquisition and final-freeze commit trees and reachable path history preserve metadata and mixed streams, not an independently addressable complete safe export. Bare Git repositories support commit-SHA object lookup, but the complete frozen row-id-to-commit map is missing and exact benchmark class/Kamei values cannot be replaced with Git-derived approximations. No Git commit payload or mixed-data index was read/created to repair this gap.

## K. Selected source
None. `source_selection.json` records `NO_SAFE_SOURCE_FOUND` and denies Phase B.

## L. T2 isolation
No safe read path was proved. Mixed files, unknown upstream CSV/notebook payloads, known T2 data and labelled prediction ledgers are rejected by the guard. No decompression/filtering, new index, protected-row hashing, T2 completeness check or T2 count-based inference occurred.

## M. TRAIN semantics
The validator freezes exactly project, TRAIN partition, row_identifier, class, order_key, CODE la, ld, nf, nd, ns, ent, PROCESS ndev, age, nuc, aexp, arexp, asexp. Binary class, finite exact numeric values, no extra/proxy/outcome fields, exact feature order and full project membership/value provenance are required. No actual TRAIN source was acquired.

## N. T1 identity-only semantics
Exactly project, T1 partition, row_identifier, order_key. No label/class, probability, prediction, confidence, correctness, residual, feature value or output. Labelled/featured T1 rows cannot be read-and-dropped. No actual T1 identity source was acquired.

## O. Project coverage
Required: all 14 frozen projects. Accepted source coverage: 0 complete projects. Partial sources are not promoted or combined optimistically. No T2 counts were used to infer completeness.

## P. Membership reconciliation
The historical membership digest recipe is specified: SHA256 of the canonical original-order row-identity list with compact sorted-key ASCII-safe JSON, UTF8 and one final LF. G4 producer and base provenance provide the exact per-project counts/digests, persisted in `reconciliation_spec.json`. Actual reconciliation is not executed because source rows are unavailable. A membership-only hash cannot substitute for exact numerical/class provenance; the validator fails if a required row/value reference is absent.

## Q. Feature reconciliation
CODE/PROCESS schema and ordering match the frozen definitions. No alternative computation, tolerance matching, proxy field or numerical coercion is used. Real value reconciliation: NOT EXECUTED.

## R. Determinism
Conditional serialization uses canonical JSON and gzip mtime=0 after full validation. Focused tests exercise exact two-directory reproduction on explicitly synthetic fixtures only. Real materialization/repeatability: NOT EXECUTED; fixture success is not a scientific source PASS.

## S. Materialized inventory
0 files, 0 rows, 0 scientific source bytes. No train/ or t1/ export directory was created. Membership registries explicitly say NOT_MATERIALIZED. No final XAI population files were created in this namespace. Generated content consists only of audit/provenance/report/test evidence; no large scientific row dump or model binary is added to Git.

## T. T1 counters
T1_SAFE_SOURCE_ACCESS_COUNT=0; T1_IDENTITY_ROW_READ_COUNT=0; T1_LABEL_READ_COUNT=0; T1_FEATURE_READ_COUNT=0; T1_MODEL_QUERY_COUNT=0; T1_XAI_ATTRIBUTION_EXECUTION_COUNT=0. The prior Sprint56.2 aggregate-registry access of 1 is historical, not reset or repeated as a source read here.

## U. T2 counters
T2_ACCESS_COUNT=0; T2_IDENTITY_READ_COUNT=0; T2_FEATURE_READ_COUNT=0; T2_LABEL_READ_COUNT=0; T2_MODEL_QUERY_COUNT=0; T2_XAI_EXECUTION_COUNT=0. State DENY_SEALED_REVIEWER_RESERVE.

## V. Other counters
TRAIN_SAFE_SOURCE_ACCESS_COUNT=0; TRAIN_IDENTITY_ROW_READ_COUNT=0; TRAIN_LABEL_ROW_READ_COUNT=0; TRAIN_FEATURE_ROW_READ_COUNT=0; TRAIN_MODEL_QUERY_COUNT=0; TRAIN_XAI_ATTRIBUTION_EXECUTION_COUNT=0. Scientific SHAP/analytical, predictive metrics, retraining, refit, reconstruction, recalibration, figures, commit and push: all 0. Integrity-only hashing of authorized prior TRAIN/smoke bytes is distinguished from acquiring/decoding source rows. Historical Sprint54 predictive access/scoring remains 1/1.

## W. Parent post-integrity
All freshly hashable protected records and object bytes match; prohibited unrehashable payloads retain the same recorded hash/Git/blob/filesystem evidence with the limitation in D. Neither parent56.2 source/guard nor earlier tests/evidence were edited. Both runtime environments and .gitignore are unchanged.

## X. Tests
`{"deselection_reason": "Historical Sprint55 Git-visible worktree byte-total assertion belongs to its historical working tree; current narrow-ignore preservation tested separately.", "focused": {"passed": 46}, "git_diff_check_returncode": 0, "regressions": {"deselected": 1, "passed": 48}, "scientific_materialization": "NOT_EXECUTED_NO_SAFE_SOURCE", "selection_boundary": "Only safe governance tests selected; no earlier mixed-stream/real-row acquisition, analytical or SHAP calculations, model inference, or metric tests executed. Regression process installs current read guard before pytest.", "status": "PASS_GOVERNANCE_AND_SYNTHETIC_FIXTURES_ONLY"}`
Tests cover guards, exact schemas, prohibited fields, class/value/order integrity, duplicate/wrong-partition/wrong-project/partial-coverage failures, membership/value mismatches, conditional Phase-B refusal, deterministic synthetic serialization, parent preservation, prohibited APIs and manifest integrity. Only permissible governance regressions are run; earlier population-reading, fitting, scientific-output arithmetic and historical diff-size tests are not silently executed or edited.

## Y. Disposition
`NO_SAFE_TRAIN_T1_SOURCE_AVAILABLE_UNDER_FROZEN_T2_BOUNDARY`. This is an evidence-backed source-access failure, not an XAI-method or predictor failure. No best-effort source exists. Sprint56.2 remains historically incomplete; Sprint56.3 is not authorized.

## Z. Exact next action
Human review must provide an independently verifiable pre-existing T2-free source/index, or decide on a separate prospective scientific protocol for upstream rematerialization. The missing information is complete frozen TRAIN identities/classes/C/P/order/provenance and complete T1 identity-only order/provenance plus safe physical locations. Any new extraction needing T2 traversal or unavoidable T1 labels/features exceeds this authorization. No protocol amendment is assumed, no boundary is weakened, and no automatic resumption is permitted.

SAFE_TRAIN_T1_SOURCE_NOT_AVAILABLE_UNDER_CURRENT_T2_BOUNDARY

READY FOR HUMAN REVIEW — DO NOT START SPRINT 56.3
