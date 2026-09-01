# Sprint 49 Development and Hyperparameter Governance

Every project/algorithm/modality search uses exactly two predeclared candidates and three expanding TRAIN-only folds (k=3, 6, 9). This early/middle/late setting was frozen before results to provide drift coverage at six fits per search. Infrastructure supports k=2 through 11, but the full robustness sweep is deferred.

Mean PR-AUC is the sole selection statistic. MCC, ROC-AUC, and Recall are diagnostics; accuracy is never computed or used. Ties follow predeclared candidate order. Search preserves natural prevalence, uses seed 20260901, and never consumes VALIDATION, T1, or T2.

The actual-data engineering smoke test completed 12 independent searches and 72 TRAIN-side fits without VALIDATION metrics. Its selections are engineering evidence only and did not alter grids. Campaign selections will be recorded independently per project, algorithm, and modality before each frozen VALIDATION evaluation.
