# Blinded independent review instructions

Use only the assigned reviewer package, `field_definitions.md`, and `decision_matrix.csv`. Do not consult production labels, model inputs/outcomes, SZZ results/opportunity, another reviewer, or prior 18C judgments. Confirm before starting that the coordinator has cleared the independence gate in `recovery_and_gate.md`.

For every record, independently enter `P`, `S`, `C`, `I`, `D`, `M`, `T`, `fixing_decision`, and (when unresolved) `unresolved_reason`; add a brief evidence rationale. Sign the completed file with reviewer ID, round, UTC completion time, and SHA-256 digest. Do not change package evidence fields. Round 1 must be locked before reviewers see one another's judgments. A third human adjudicator resolves disagreements only after round-1 locking.

The coordinator may compute raw agreement, nominal Cohen's kappa (with `UNRESOLVED` distinct), disagreement counts, C1/C2 and C2/C3 disagreements, adjudication rate, unresolved rate, and contingency tables only from two genuine locked reviews.
