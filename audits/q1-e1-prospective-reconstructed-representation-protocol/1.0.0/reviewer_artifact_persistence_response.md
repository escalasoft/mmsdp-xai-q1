# Reviewer response: artifact persistence

The confirmatory predictive experiment was completed and frozen before the feature-level explainability campaign. Predictive outputs and experimental metadata were retained, but complete fitted/transformed feature matrices were not persisted as standalone scientific artifacts in the inspected workflow. The exact historical human reason is not documented. The implementation focused on predictive outputs and experimental evidence; the representation persistence limitation was identified during later XAI audits. We have now frozen a prospective deterministic reconstruction protocol. No representations have been reconstructed under R3. Future representations must use admitted frozen inputs and transformations, retain explicit reconstructed labels, and be versioned, hashed and persisted separately. This amendment changes the provenance protocol for post-hoc explanation inputs; it does not recompute or replace the frozen predictive results.

- **preserved_outputs:** [Sprint54 manifest and row-prediction evidence reference; do not reopen payload here]
- **implementation:** src/evaluation/q1_t1_confirmatory_execution.py:1578
- **historical_gaps:** audits/q1-e1-canonical-identity-representation-linkage/1.0.0/remaining_blockers.json
- **predictor_equivalence:** [Per-scope G4/G5 ledger and state digest]
- **future_reconstruction:** [Future accepted representation manifest]
- **future_validation:** [Future contract-validation results]
- **future_persistence:** [Future atomic publication receipts and verified manifests]

The completed reconstruction wording is not currently authorized by the evidence.
