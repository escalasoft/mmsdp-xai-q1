# Sprint 49 Controlled TRAIN/VALIDATION Campaign Results

The campaign produced 392 primary VALIDATION conditions and 1176 TRAIN-development condition-fold results. Every result reports PR-AUC, ROC-AUC, MCC, Recall, Precision, F1, confusion counts, prevalence, observation count, threshold, and membership/probability hashes.

Threshold 0.5 was predeclared and never selected on VALIDATION. All hyperparameter choices were frozen by TRAIN-side PR-AUC before VALIDATION scoring. Accuracy is not a primary result. T1 and T2 were not predictively accessed.

Tables A–F and explicit full-versus-pairwise ablation comparisons are provided. Differences are descriptive; no statistical-significance claim is made. Feature-level SHAP ablation was not executed.

The automatic ceiling-performance guard produced 4 diagnostic flag(s). Every flag is retained for audit without changing the dataset or accessing T1/T2.
