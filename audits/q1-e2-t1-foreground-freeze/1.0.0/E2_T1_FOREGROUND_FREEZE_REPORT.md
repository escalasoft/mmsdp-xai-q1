# E2 T1 foreground freeze

**E2_T1_FOREGROUND_FREEZE_PASS**

Branch: sprint-10/q1-e2-final-closure. Starting HEAD: 77c1af5d59ee7af6257f67ce17d06968ef78a416. Prior diagnostic package preserved.

The unchanged Sprint56.2 selector and its prospective contract define seed 20260901,
SHA-256 of canonical JSON (seed, purpose, project, model_identity_sha256, row_identifier),
then selection_key ascending and row_identifier ascending. Global selection is unstratified,
at most 256/project with null model identity; local selection is at most 8/eligible scope,
from that project's global subset with the frozen scope model identity and the distinct
T1_LOCAL_CASE_SELECTION purpose. All available cases are retained when below the limit.
No labels, predicted decisions, confidence, correctness or explanation values select cases.
The later per-project unstratified rule supersedes Sprint55's conditional predicted strata.

Authoritative source: `audits/q1-t1-confirmatory-execution/1.0.0/results/t1_prediction_evidence.jsonl.gz`.
SHA-256: `eb4b6956b185e63cd322d92b8cdf96f53fcb09ef83b6a16f2334d660c6f5adc8`.
The Sprint56.2C source inventory establishes physically isolated T1 evidence; its producer
and existing ordered G4/G5 membership digests establish identity provenance. The current
task authorizes materialization from this frozen source; no mixed dataset was accessed.
The T1 gzip contains label/prediction bytes; they are decoded as transport but dropped by
the identity projection and never used, inspected for selection, logged or persisted.
This does not claim zero physical decoding of T1 label/prediction bytes.

Eligible E2 scopes: 221 (C+P 56, C+T 55, P+T 55, C+P+T 55), unchanged.
Global project-row records: 2450.
Local scope-row records: 1768 (8 per eligible scope).
Scope-weighted global rows: 39026.
Source unique T1 rows: 3787.
Local counts repeat a commit across scopes; they are not counts of unique commits.

Provenance/selection use only identity fields, scope identity and fixed seed/purpose;
partition is T1 by the verified isolated-source provenance. Every eligible scope's
ordered source identity list matched its pre-existing G4/G5 digest and count, and
all scopes of each project had exactly the same ordered membership.

Two fresh Python processes independently reopened the source and repeated the complete
validation and selection. Both also checked results against an independent implementation
of the frozen hash recipe. Complete result payloads were byte-identical, with zero differing
rows. Per-output hashes are in `deterministic_reproduction.json` and `population_manifest.json`.
Contract hash: `74a1b3a3b7a0e93dff08de5365712922dfd6efb2ebe2d1a4d363cfe0c5481871`.
Population manifest hash: `a3dcfbc5647f32d473c131ceb1708579f7d8831e910b47832ed954d4b70463a9`.

Global output SHA-256: `9a5f42f673c24a36960bb4f11bc9c0eeda22ec39dc46605531feef0ed63d764a`.
Local output SHA-256: `df3d76ae2c3a193b75b0c13afade42e42ddf191940808d472e9ef6c33ee5e261`.

T2 scientific accesses = 0; model retraining = 0; calibration refits = 0;
predictive recomputations = 0; E1 reruns = 0; E2 attribution executions = 0.
No historical population, predictive artifact, E1 result or earlier diagnostic was overwritten.
No commit, push, merge, rebase or reset was performed.

No foreground-freeze blocker remains. E2 itself is not closed: attribution, numerical
fidelity, deterministic attribution reproduction and publication tables/figures remain
for the separately authorized final-closure task. This PASS covers the T1 foreground only.

Validation: 13 focused tests passed; all persisted local memberships and critical input hashes verified. Prior diagnostic manifest remains valid; tracked and staged Git diffs remain empty. See `validation_results.json`.

READY_TO_RESUME_EXISTING_E2_FINAL_CLOSURE_PROMPT
