# Sprint 10.8.2.48C-R1 — Validator Generalization and Full-Suite Failure Evidence Review

## Final classification

`PASS_48C_R1_READY_FOR_CLOSURE`

The accepted Sprint 48C scientific classification remains
`BLOCKED_PROSPECTIVE_LABEL_PROVENANCE`. This minor review changes validator
architecture and test evidence only. It does not create labels, change temporal
boundaries, authorize TARGET use, or execute any predictive or XAI operation.

## Starting state

- Branch: `sprint-10/q1-prospective-target-label-materialization`
- HEAD: `30a37f1fbf582b549ddc08e8b535ac30e10989bd`
- Review mode: no new branch, commit, push, PR, or merge

## Files inspected

- `src/experimentation/q1_prospective_target_label_materialization.py`
- `tests/experimentation/test_q1_prospective_target_label_materialization.py`
- `scripts/materialize_q1_prospective_target_labels.py`
- Frozen 48C package under `audits/q1-prospective-target-label-materialization/1.0.0/`
- `tests/evaluation/test_q1_controlled_advancement_decision.py`
- `src/evaluation/q1_controlled_advancement_decision.py`
- `tests/evaluation/test_q1_predeclared_final_performance_contract.py`
- `src/evaluation/q1_predeclared_final_performance_contract.py`
- `tests/evaluation/test_q1_final_test_identity_boundary_amendment.py`
- `src/evaluation/q1_final_test_identity_boundary_amendment.py`
- `tests/evaluation/test_q1_human_prospective_authorization.py`
- `src/evaluation/q1_human_prospective_authorization.py`
- `pyproject.toml`, `requirements/base.txt`, and Git status/diff evidence

## Files modified or created by R1

Modified:

- `src/experimentation/q1_prospective_target_label_materialization.py`
- `scripts/materialize_q1_prospective_target_labels.py`
- `tests/experimentation/test_q1_prospective_target_label_materialization.py`

Created:

- This versioned R1 audit directory and its five required artifacts.

The frozen 48C evidence artifacts were not modified.

## Validator separation

Before R1, `validate()` mixed general checks with literal assertions requiring
exactly 58,272 rows, zero assigned labels, 21 projects, and zero eligible projects.
Those valid frozen results would have rejected a future provenance-complete package
solely because it contained supported labels or eligible projects.

After R1, `validate()` checks reusable scientific invariants and artifact
consistency. `validate_frozen_48c_snapshot()` composes the general validator with
the exact frozen regression assertions. The materialization script invokes the
frozen validator when reproducing Sprint 48C.

Frozen snapshot assertions remain:

- total identities = 58,272;
- project count = 21;
- assigned label count = 0;
- eligible project count = 0.

Reusable invariants include:

- label-summary counts agree with the observation manifest;
- only declared evidence states are accepted;
- supported positives carry label 1 and require resolved provenance plus a
  complete positive chain;
- supported negatives carry label 0 and require resolved provenance,
  affirmative negative verification, and completed maturity support;
- unresolved, identity-unresolved, provenance-unresolved, and right-censored
  observations cannot receive binary labels;
- every prospective identity is strictly after its frozen temporal boundary;
- per-row evidence hashes remain valid;
- project eligibility counts and decisions are recomputed through the common
  scientific gate;
- predictive metrics cannot participate in TARGET selection;
- any four-project freeze follows the predeclared lexical, performance-independent
  rule;
- TARGET access, authorization, predictive scoring, and campaign execution remain
  blocked and zero;
- the SHA-256 manifest covers every generated artifact and every digest matches.

A hypothetical test-only package with one supported positive, one affirmatively
supported mature negative, two assigned labels, and one eligible project passes
general validation and fails only the frozen snapshot regression check. No actual
48C label or TARGET evidence is changed by that test.

## Full-suite evidence

The comparable closure run used `.venv/bin/pytest`. Result:

- 1,555 passed;
- 1 skipped;
- 2 failed;
- 23 errors;
- elapsed time: 127.17 seconds.

All 25 non-passing cases are individually recorded in
`full_suite_failure_inventory.json`. Every case is classified
`EXPECTED_HISTORICAL_INTEGRITY_GUARD`. There are zero `48C_REGRESSION` and zero
`UNKNOWN_REQUIRES_INVESTIGATION` cases.

The 16 Sprint-43 setup errors and seven Sprint-44 setup errors are raised by
immutable-baseline audit guards that already reject post-baseline audit paths. The
Sprint-46A assertion rejects tracked modifications relative to its accepted
baseline (`pyproject.toml` and `requirements/base.txt` are non-additions). The
Sprint-45 authorization assertion rejects working-tree paths outside its narrow
Sprint-45 allowlist; 48C paths trigger that expected legacy guard, but do not alter
historical evidence. Weakening any of these tests merely to make the suite green
would weaken their declared integrity scope.

## Verification

- Focused 48C/R1: `16 passed in 18.45s`.
- Relevant regressions (conservative expanded set): `33 passed in 11.57s`.
- Complete suite: `1555 passed, 1 skipped, 2 failed, 23 errors in 127.17s`.
- Ruff on changed Python files: PASS.
- `git diff --check`: PASS.
- Frozen 48C manifest: PASS, all 14 payloads verified.
- Frozen snapshot validator: PASS with no errors.
- TARGET access count: 0 in policy, provenance, and freeze artifacts.
- Predictive scoring count: 0.
- R1 audit manifest: PASS.

## Preserved scientific result

- 58,272 prospective identities;
- 21 projects evaluated;
- 0 supported positives and 0 supported negatives;
- 58,272 `PROVENANCE_UNRESOLVED`;
- 0 assigned labels and 0 eligible TARGET projects;
- no four-project TARGET set frozen;
- TARGET access count = 0;
- predictive scoring count = 0;
- 720 campaign configurations not executed.

## Final worktree status

```text
?? audits/q1-prospective-target-label-materialization-r1/
?? audits/q1-prospective-target-label-materialization/
?? scripts/materialize_q1_prospective_target_labels.py
?? src/experimentation/q1_prospective_target_label_materialization.py
?? tests/experimentation/test_q1_prospective_target_label_materialization.py
```

## Recommendation

48C-R1 is ready for closure and human review. After acceptance, the reviewed 48C
and R1 files may proceed through the normal human-authorized commit, push, PR, and
merge workflow. None of those operations was performed in this review. Do not
begin Sprint 48D until the human review and closure decision are complete.
