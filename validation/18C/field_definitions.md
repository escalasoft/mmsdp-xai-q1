# PROSPECTIVE_ALTERNATIVE_B_V1 field definitions

This is a frozen, non-production protocol. It is a new prospective protocol, not a reconstruction of the historical 18C.2 matrix.

- `P` — provenance: whether the relationship and evidence sources are traceable to frozen artifacts.
- `S` — syntax: the observable issue-reference form and location; syntax alone never establishes fixing.
- `C` — corrective semantic category (`C1`–`C4`) defined in `decision_matrix.csv`.
- `I` — independent issue evidence: `AFFIRMATIVE`, `CONTRADICTORY`, `INSUFFICIENT`, or `MISSING` based on issue text/metadata available no later than adjudication.
- `D` — diff corroboration: `AFFIRMATIVE`, `CONTRADICTORY`, `INSUFFICIENT`, or `MISSING` based on the actual commit diff.
- `M` — mitigation/suppression state: `NONE`, `MITIGATION_ONLY`, `SUPPRESSION_ONLY`, `REVERSAL_OF_SUPPRESSION`, or `MIXED`. Mitigation/suppression alone is non-fixing; reversal is judged from its present corrective effect and does not automatically imply fixing.
- `T` — temporal admissibility: `ADMISSIBLE`, `INADMISSIBLE`, or `UNKNOWN`. Admissible means the commit is not earlier than issue creation. Missing/unparseable creation or commit time is `UNKNOWN`. `T` is used only as an admissibility guard, never as affirmative fixing evidence.
- `Z` — downstream SZZ opportunity. It is excluded from reviewer packages and can never change `C` or the fixing decision.
- `fixing_decision` — `FIXING`, `NON_FIXING`, or `UNRESOLVED`.
- `unresolved_reason` — mandatory for `UNRESOLVED`; one or more of `TEMPORAL_INADMISSIBLE`, `TEMPORAL_UNKNOWN`, `MISSING_CRITICAL_EVIDENCE`, `MATERIAL_CONTRADICTION`, `AMBIGUOUS_SEMANTICS`.

Reviewers first record P/S/C/I/D/M/T and the fixing decision independently. Reviewer identities use pseudonymous stable codes. Comparison, agreement computation, adjudication, and any release of Z occur only after both round-1 forms are locked.
