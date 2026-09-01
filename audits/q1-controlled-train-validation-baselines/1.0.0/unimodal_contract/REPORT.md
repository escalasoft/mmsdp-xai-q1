# Sprint 49 Unimodal Modeling Contract

The exact four families are Logistic Regression, Random Forest, XGBoost, and LightGBM. CODE uses only la, ld, nf, nd, ns, and ent. PROCESS uses only ndev, age, nuc, aexp, arexp, and asexp. Numeric median imputation is TRAIN-fitted. Standardization is applied only to Logistic Regression; tree families are not scaled.

TEXT uses only the raw prediction-commit message and a TRAIN-fitted sparse word-unigram TF-IDF representation. Character n-grams, supervised vocabulary construction, dimensionality reduction, transformers/embeddings, and explicit bug/fix/issue indicators are not used. No earlier frozen contract requires a transformer.

Natural TRAIN prevalence is preserved. Class weighting, oversampling, and SMOTE are not used. Every fitted model exposes positive-class probabilities. All 12 algorithm/modality pipelines passed an actual-data engineering smoke test without metrics or selection. T1 and T2 predictive accesses remain zero.
