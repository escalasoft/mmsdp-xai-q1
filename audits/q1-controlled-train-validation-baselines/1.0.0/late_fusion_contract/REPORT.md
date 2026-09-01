# Sprint 49 Controlled Late-Fusion Contract

For each base family A, C_A, P_A, and T_A are independently fitted modality models. C+P, C+T, P+T, and C+P+T consume only their positive-class probabilities as meta-features. Raw feature concatenation is neither primary nor executed.

Each fixed L2 Logistic Regression meta-learner is trained only from strict-forward out-of-fold TRAIN probabilities. The earliest TRAIN block is retained as warm-up and never backfilled. Base learners are then refitted on full project TRAIN and score identical VALIDATION identities. VALIDATION labels do not fit a base learner or meta-learner.

The meta-learner is not a fifth family; comparisons refer to the four base families. The engineering smoke test executed all 28 conditions for the deterministic pilot project without metrics or performance selection. T1/T2 predictive access remains zero.
