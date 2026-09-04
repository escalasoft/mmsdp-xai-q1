# Sprint 55 Block 6 — Reconstruction-Equivalence Authorization Protocol

## Status

`RECONSTRUCTION_AUTHORIZED_NOT_EXECUTED` means the prospective protocol is scientifically specified; it does not grant operational G5 or G4 authorization. Original executable Sprint 54 state remains unavailable, so E1/E2 execution remains blocked.

## Scope and immutable evidence

This package freezes how TRAIN/source-only reconstruction could later be attempted and how row-level equivalence could subsequently be verified. Sprint 54 predictions, labels, metrics, statistics, calibration evidence, identities, classification, and reporting remain immutable. The scientific classifications remain `MIXED_CONFIRMATORY_EVIDENCE` and `PASS_CONFIRMATORY_EVIDENCE_INTERNALLY_CONSISTENT_REPORTABLE_MIXED`.

## Reconstruction units

The minimum final-state universe comprises 168 fitted unimodal predictors, 112 numeric preprocessing chains, 56 fitted TF-IDF vectorizers, and 224 fitted fusion LR meta-learners. Every fold-specific state used to regenerate strict-forward OOF meta-features must also be persisted. The 14 provenance-verified isotonic mappings are reused unchanged; they are never refitted.

## Inputs and determinism

Only exact frozen TRAIN/source data, identities, schemas, candidates, hyperparameters, seed 20260901, modality order, OOF lineage, calibration state, model identity, and the frozen Python 3.11.14 dependency environment may be used. Three independent, single-thread repetitions are required. Canonical state and TRAIN/source check-output digests must match exactly.

## Equivalence gates

G1 validates reconstruction provenance. G2 validates fitted-state structure. G3 requires deterministic repeatability. Only a separate later authorization may perform G4 row-level T1 raw-output comparison. Multimodal G5 then checks base outputs, ordered LR fusion, calibration, final probabilities, and decisions. Aggregate metric similarity never establishes equivalence.

## Frozen tolerances

Repeated reconstruction has zero tolerance: canonical state and canonical float64 check-output digests must be identical across all three repetitions. A future authorized comparison with frozen probabilities requires every row to have maximum absolute error at most `1e-12` and, where the reference magnitude is at least `1e-8`, maximum relative error at most `1e-10`. Calibration identities, arrays, feature/class/modality order, and threshold decisions must match exactly; decision mismatch budget is zero. These tolerances cannot be weakened after any reconstruction result is observed.

## Scientific separation

Future equivalence verification is technical and non-confirmatory. It cannot alter Sprint 54 evidence, select or tune models, change thresholds/calibration, or update scientific conclusions. It must use a separate technical ledger and leave the original T1 access/scoring ledger unchanged.

## XAI and T2

SHAP and LIME remain non-executed candidate complementary methods. Stored predictions alone are insufficient. No XAI target is selected. T2 remains `DENY_SEALED_REVIEWER_RESERVE` with zero access.

## Block 6 stop

No model was loaded for inference, trained, reconstructed, refitted, scored, or explained. No G4/G5 verification occurred. The next action is human review of this prospective protocol and, only if separately authorized, a TRAIN/source-only reconstruction phase that stops before T1 verification.
