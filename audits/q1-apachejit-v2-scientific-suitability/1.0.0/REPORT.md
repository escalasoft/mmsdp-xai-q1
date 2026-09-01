# ApacheJIT v2 Scientific Suitability Audit

## Decision

**PASS_48E_R1_READY_FOR_FREEZE** closes the three pre-freeze contract findings. The underlying
ApacheJIT suitability remains **PASS_WITH_LABEL_CONSTRUCT_LIMITATION**: acceptable for
continuation only as a peer-reviewed, benchmark-defined observed-label construct, not
verified ground truth. This classification does not authorize predictive TEST access.

## Frozen evidence

- Starting HEAD: `13b63f3c1b825fca529ca2cb1ce96df80cccef0b`
- Branch: `sprint-10/q1-apachejit-v2-scientific-suitability-audit`
- Archive: Zenodo record 5907847, version v2, DOI `10.5281/zenodo.5907847`
- Archive SHA-256: `533e7c6fc4f7cb6f34b35539a972d00baa63a125e88ddb5743283dd277edcd5c`
- Rows: 106,674; positive: 28,239; negative: 78,435
- Project identities: 15 CSV identities representing 14 paper project families
- Candidate-eligible project identities: 14 (performance-independent preconstruction screen)
- Final-eligible projects: 0 declared; final eligibility is unresolved and belongs to 48F

## Construct and provenance

Positive rows are filtered SZZ-attributed bug-inducing commits. Bug-fixing and
bug-inducing commits are explicitly distinct. Negative rows mean not identified as
bug-inducing by the benchmark procedure; they are not affirmatively verified clean.
The archive provides construction notebooks, issue/fix/SZZ intermediate files, full
SHAs, repository identities, timestamps, Kamei metrics, and GumTree tooling. The final
surviving issue-to-fix-to-inducing edge must be replayed, and the archive states no
license; both limitations remain recorded.

## Compatibility and governance

CODE contains current-change information: `la`, `ld`, `nf`, `nd`, `ns`, and `ent`
(`entropy`), plus any later-frozen commit-parent content/structural representations. PROCESS contains
only ancestor-history metrics: `ndev`, `age`, `nuc`, `aexp`, `arexp`, and `asexp`, under
an ancestor-only replay contract. No metric is duplicated across modalities. TEXT messages
are not distributed in the CSV but are reconstructable from resolved SHAs; engineered
bug/fix/issue keyword proxies are prohibited. Raw UTC timestamps support temporal
validation, while the supplied synthetic `year` field has 1,314
calendar-year mismatches and must not define the final partition. Strict source-fit
LOPO/CPDP is feasible. Predictive TEST access remains denied.

## Eligibility closure

The former `rows >= 800`, `positive >= 300`, and `negative >= 400` screen is inactive and
classified as a provisional engineering screen without frozen scientific justification.
R1 candidate eligibility instead requires mapped identity, complete well-formed SHAs and
timestamps, both observed classes in aggregate, at least three raw-UTC calendar years, and
identity-level C/P/T feasibility. These criteria yield 14 candidates and use no
predictive result. No project is final eligible until 48F completes SHA/parent materialization,
row-level C/P/T reconstruction, and chronological partition/class-support verification.

## Precedent and novelty scope

The targeted audit verified later peer-reviewed ApacheJIT use in ASE 2024, Empirical
Software Engineering (2024), and Neural Computing and Applications (2024). The two
Empirical Software Engineering records are Q1-verified for the 2024 SCImago Software
category; Neural Computing and Applications is Q1-verified from independent 2024 Scopus/SJR
metrics for Software and Artificial Intelligence. ASE/NeuroJIT remains Q1-unverified because
no independent 2024 quartile/category evidence was frozen. No precedent was found within
the audited scope for the complete conjunction of C+P+T, controlled fusion,
calibration, temporal validation, cross-project evaluation, and XAI; this is not a
universal novelty claim.

## Gate summary

All G1-G24 states and evidence are in `apachejit_scientific_gates.json`. Limitations
are retained on G3, G5-G15, and G17; no UNRESOLVED state was promoted to PASS.

## Zero-execution assertion

`model_training_count = 0`, `predictive_scoring_count = 0`,
`calibration_fit_count = 0`, `test_predictive_access_count = 0`, and
`xai_execution_count = 0`.

## Exact next sprint

Sprint 10.8.2.48F - ApacheJIT Final Dataset Construction and Freeze. Materialize every
candidate-eligible repository SHA and parent; freeze distinct CODE, PROCESS, and TEXT representations;
rebuild UTC temporal and source-target partitions; prepare TRAIN/VALIDATION; keep
predictive TEST closed. Determine final dataset eligibility only after row-level reconstruction
and partition verification. Do not train in 48F dataset construction/freeze.
