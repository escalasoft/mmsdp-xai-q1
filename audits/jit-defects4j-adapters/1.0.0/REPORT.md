# Frozen JIT-Defects4J Input and Modality Adapter Audit

Decision: **GO**

## Frozen input

- Canonical scientific identity: `e509995da233c932cafce531c13ad2cd617a0d8abbe8d81ccaa373b8f29fa519`.
- Canonical manifest SHA-256: `95b1a362f6756f641cc575cabf54a3a99e2846568d5ef110dac38a45f3d81ef1`.
- Observations: 27,319; TRAIN 19,114; VALIDATION 4,086; TEST 4,119.
- TRAIN: 1,912 positive and 17,202 closed-world nominal negative.
- VALIDATION: 260 positive and 3,826 closed-world nominal negative.
- TEST: 160 positive and 3,959 closed-world nominal negative. These labels were only mechanically validated against the frozen contract; no predictive evaluation used them.

All canonical artifacts are SHA-256 verified before parsing. Every join uses the
project-qualified `(project, commit_hash)` identity. Duplicate, missing,
cross-split, or cross-modal identities fail closed.

## Adapter contracts

- **CODE-STRUCTURAL** has six deterministic dimensions: changed file count,
  added/deleted/modified/other counts, and mode-change count. It uses only the
  exact canonical raw tree-change artifact. It has no fitted state and makes no
  claim of source-code semantics.
- **PROCESS** has four deterministic dimensions: parent count, merge indicator,
  prior-history indicator, and exact prior ancestor count. Values are unscaled,
  so there is no fitted state. The canonical ancestor-only provenance contract
  is retained.
- **TEXT** is a deterministic 5,000-dimensional unigram TF-IDF baseline. Its
  vocabulary, document frequencies, and smooth IDF are fitted from TRAIN only.
  VALIDATION is transform-only. `<MISSING_COMMIT_MESSAGE>` yields an explicit
  deterministic zero lexical row under the frozen tokenizer.

Targets, project identifiers, split identifiers, target-generation metadata,
and denylisted fields are metadata, never predictors. No target-derived keyword
features are constructed.

## TEST sealing and extension point

The ordinary adapter API transforms only TRAIN and VALIDATION and rejects TEST.
Mechanical TEST transformation exists behind an explicit final-evaluation seal
for a later sprint after every development decision is frozen. This sprint did
not invoke it and did not materialize a TEST matrix.

Future CODE-SEMANTIC or learned TEXT backends can be introduced behind the same
identity, split, fit/transform, and audit boundary without changing the frozen
target or membership. No pretrained model was downloaded or used here.

Machine-readable hashes, fitted-state identity, matrix scientific digests,
software provenance, and sealing assertions are in `audit.json`.
