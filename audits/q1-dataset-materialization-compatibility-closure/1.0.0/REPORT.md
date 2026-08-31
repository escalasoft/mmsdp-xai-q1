# Sprint 10.8.2.48B — Dataset Materialization & Compatibility Closure

## Scientific classification

`BLOCKED_MISSING_PROSPECTIVE_TEST`

All 21 local JIT-Defects4J upstream snapshots contain commits strictly after each
project's historically consumed boundary.  This sprint materializes
58,272 deterministic,
label-sealed commit identities with timestamps, provenance-ref hashes, and zero
overlap with the historical benchmark.  They are **candidates, not TEST**: no
audited prospective target labels, positive/negative counts, or prevalence are
available.  QtBase remains ineligible because its completed construction artifact
contains 16,740 nominal negatives and zero admissible positives.

The historical JIT aggregate is independently re-read from its immutable manifest:
27,319 observations, 2,332 positives, 24,987 nominal negatives, prevalence
8.536%.  Sprint 46A's `NO_VERIFIABLE_UNTOUCHED_FINAL_TEST` and Sprint 31 TEST
consumption remain unchanged.

## Readiness outcome

The strict SOURCE-only normalization, exact schema rejection, deterministic LOPO
membership, seven modality levels, 48A-scoped calibration, bounded XGBoost and
LightGBM adapters/search spaces, blocked campaign generator, and atomic one-use
authorization contract are implemented.  XGBoost/LightGBM runtime status is
recorded in `algorithm_readiness.json`.  Named SHAP/LIME/PDP/ICE/DiCE integration
remains a documented later blocker; no TARGET XAI was run.

The pre-execution campaign contains 720 unique,
blocked configurations: 2 designs × 10 provisional targets × 4 algorithms ×
(7 uncalibrated modalities + 2 additional C+P+T calibration states) × 1 seed.
No model matrix, final significance test, final XAI, or final TARGET score was run.
TARGET TEST access count: **0**.

## Four-project decision

No scientifically eligible four-project core is declared.  Ant-Ivy, Commons Lang,
Giraph, and OpenNLP are retained only as a diverse identity-materialization subset;
their new two-class support is unknown.  Promotion requires audited prospective
labels, counts/prevalence, frozen sample manifests, and authorization.

## Verification

Verification results are recorded in `implementation_readiness.json`.  Historical
audit files were not modified and no historical gate was weakened.
