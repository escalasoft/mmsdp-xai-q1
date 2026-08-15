# Sprint 10.8.2.18C.4 corrective closure report

## Repository state

- Branch: `sprint-10/reproducible-qt-fixing-commit-semantics-audit` (unchanged).
- Source HEAD: `3388cd919ab72af3ab1ed78af11edc8637fddc62`.
- Initial status: clean (`## sprint-10/reproducible-qt-fixing-commit-semantics-audit`).
- Initial working tree: clean.

## Recovery

Inspected tracked files and every reachable commit/branch; path/content history; reflogs; unreachable Git objects; tags and notes; repository documentation and DOCX XML; reports; structured relationship, commit, issue, target-evidence, target-assignment, diff, and diff-statistics artifacts; and ignored repository-local provenance.

- 18C.1 exact 18-case exclusion list: **NOT_RECOVERABLE**. No exact identities, list, or membership marker exists in the inspected evidence. The 3,791-link artifact cannot identify which 18 were used. No list was inferred.
- 18C.2 exact Alternative-B matrix: **NOT_RECOVERABLE**. No exact historical matrix/version exists in the inspected evidence. The 18C.3 contextual dimensions were not promoted to historical fact.
- Git provenance: reachable HEAD/history contains no 18C.1/18C.2 commit; the only unreachable commit (`f6bd12e2bf686cb611add701881a76d5db708ecf`) concerns Sprint 10.3 explanation-runner code; unreachable blobs contained no relevant protocol evidence; there were no relevant tags or notes.

## New frozen protocol

`PROSPECTIVE_ALTERNATIVE_B_V1` was required and frozen at `2026-08-14T11:53:38-05:00` before prospective semantic adjudication. It is explicitly new, non-production, and not a reconstruction of 18C.2.

The deterministic matrix requires temporal admissibility for a fixing decision; C1 needs an explicit present corrective claim plus non-contradictory corroboration from I or D; C2 requires affirmative, mutually consistent I and D; C3 is non-fixing; mitigation/suppression-only, provenance-only, housekeeping, diagnostic, test-only-without-product-correction, and future-fix-only relationships are non-fixing; C4, missing critical evidence, temporal inadmissibility/unknown, or material contradiction are unresolved. Z/SZZ never affects fixing adjudication.

## Eligibility, exclusion, and sampling

Eligibility requires a unique exact link with commit and issue metadata. Diff, description, and resolution availability are not eligibility requirements. Production targets, model features/outcomes, and Z/SZZ are forbidden inputs.

The exact historical exclusion list is empty only because recovery failed—not because the historical cases are known absent. A hash split cannot prove independence from 18 unknown cases in the same frozen corpus. Therefore the 48 records are a **candidate review sample**, not valid independent validation evidence. Review may begin only after exact exclusion or case-level non-reuse certification.

- Eligible relationships: 3,791.
- Fixed seed: `SPRINT-10.8.2.18C.4-PROSPECTIVE-2026-08-14`.
- Procedure: deterministic greedy coverage of pre-adjudication strata, with ties ordered by SHA-256 of `seed|relationship_identifier`.
- Sample size: 48, chosen to cover all observable low-frequency conditions while remaining a modest validation exercise.
- Strata: reference type (`fixes` 1, `plain` 5, `task-number` 42); temporal relation (47 admissible, 1 inadmissible); diff availability (48 available); deletion band (3 deletion-only, 10 deletion-dominant, 27 mixed, 8 none); change family (8 test-only, 2 documentation-only, 38 source/mixed); issue description (47 present, 1 absent/weak).

## Blinded review package and stress coverage

The JSONL evidence package contains stable review/relationship identifiers, revisions/issues, source and record digests, reference location/type, commit and issue text/metadata/timestamps, temporal relation, diff availability/summary/excerpt, insertions/deletions/files changed, and observable change families. Two identical blank reviewer forms collect P/S/C/I/D/M/T, decision, unresolved reason, reviewer, and round. Z/SZZ, production targets, model outcomes, and other-reviewer judgments are absent.

Observable candidate flags represent: assertive non-corrective wording; mitigation; suppression; reversal of suppression; test-only; housekeeping/provenance; future-fix claims; temporal anomaly; weak/absent descriptions; deletion-only; and deletion-dominant changes. C1-vs-assertive, C2-vs-C3, mitigation/suppression presented as correction, and issue/diff contradiction are semantic conditions whose **actual** representation must be confirmed by human review; the keyword flags do not establish them.

## Leakage and construct audit

- Future model outcomes used: no.
- Z/SZZ used or exposed: no.
- Model features used to define target: no.
- Target-derived keywords/features introduced: no; sampling keyword flags are review-coverage metadata only and are not target/model features.
- Temporal information use: admissibility and pre-adjudication stratification only.
- Known reuse of protocol-design cases: none knowingly reused, but non-reuse is **not demonstrable** because identities are unavailable; blocker remains.
- Production labels/datasets/splits/features changed: no.

No genuine human judgments exist. Consequently no raw agreement, kappa, contingency table, disagreement count, adjudication rate, or unresolved rate is reported.

## Decision and remaining action

The rule remains scientifically plausible, explicit, frozen, provenance-preserving, and leakage-protected, but required implementation evidence is unavailable because independence is not established and dual-human review has not occurred.

**FINAL DECISION: REVISE B**

Production implementation is **not authorized**. Production labels, dataset identities, temporal splits, model-ready datasets, and feature constructors remain untouched.

Minimal necessary gate: an authorized provenance holder must either supply the exact 18C.1 relationship list or certify candidate-by-candidate non-reuse from independently preserved records. After that clearance, two genuine blinded reviewers must independently complete and lock the supplied forms; only then may the specified agreement/contingency metrics and adjudication be computed.

**18C NOT CLOSED — the single minimal scientific blocker is demonstrable independence from the unrecovered 18 design cases; dual-human validation cannot validly begin until it is cleared.**

## Versioned artifacts and SHA-256

Canonical artifact digests are recorded in `manifest.json`. Principal files:

- `protocol.json`: `70468398c946f95aaf2b3c051917c7e30a2d73e4608ce37a90c17a1e609d3b6c`
- `decision_matrix.csv`: `4af7c4110fcabf7d8494aac352f7d3f78a360d24d8d4f8eac16a318a6b7ca06c`
- `field_definitions.md`: `56630d04069702410f52a4cd7da0ea24da00ac9778640903f4bce191601f334e`
- `recovery_and_gate.md`: `1dd76c1d27a6908439ed3abc9b47d3163b6284acffa976051ed98c34774d6144`
- `sample_review_package.py`: `2a0864d838fbe48b410af178cfdbf5f6bf46172931a422179b312a5fc249b6fc`
- `blinded_review_package.jsonl`: `f579085edc1ebcd4ee96e61bcf381783c8fa93e7abfa79d4bcb7ba2a82413d6d`
- `reviewer_A_form.csv` and `reviewer_B_form.csv`: `ddffa314ce01b0f9795377a72e45a52013b5ac689d681bcd0b68039fc6f23771`
- `reviewer_instructions.md`: `2b0c3b2d6a0e199a670b55ccd52e52fb93ff45da42e468bdf298238cf316b6ed`
- `manifest.json`: see final repository verification (its digest is intentionally outside its own content).

Repository files changed are confined to `validation/18C/`. Final diff/status are recorded in the sprint handoff after verification.
