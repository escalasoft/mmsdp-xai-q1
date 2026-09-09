**E1-F1** Mean absolute feature contributions over all 245 frozen ActiveMQ T1 rows. LR uses centered analytical logit decomposition; XGB and LGB use exact TreeSHAP on native raw margins. RF failed exact additivity and is excluded. Horizontal scales are independent.

**E1-F2** Pairwise Jaccard overlap of top-3 and top-10 feature sets. RF cells are unavailable. The frozen overlap threshold is 0.60; full consistency additionally requires rank correlation ≥0.70 and sign agreement ≥0.80.

**E1-F3** First identity-selected local case, shown with LR (fixed family order). Twelve largest absolute centered logit contributions and the signed sum of all remaining features are displayed. Positive and negative contributions increase and decrease the model logit relative to the TRAIN reference.

**E1-F4** Hierarchical explainability architecture. Bounded E1 provides within-modality evidence for ActiveMQ TEXT, while E2 explains between-modality late fusion. Arrows show architectural continuity, not an additive mapping of feature attributions into fusion attributions.
