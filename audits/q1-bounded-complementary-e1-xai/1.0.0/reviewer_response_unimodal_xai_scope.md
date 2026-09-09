# Response to reviewer: feature-level XAI scope

**Question.** Why is feature-level XAI not reported for CODE, PROCESS, and TEXT across all projects?

Explainability in this framework is hierarchical. E2 is the primary multimodal explanation: it addresses contributions of unimodal outputs within the frozen late-fusion architecture. E1 is complementary and addresses features within a scientifically traceable unimodal predictor.

The completed provenance campaign could not demonstrate the full feature-level representation and transformation lineage required for all modalities and projects. We therefore intentionally did not generate unsupported feature attributions. ActiveMQ TEXT was retained because its TRAIN matrix, row/commit identities, token/column registry, vocabulary, IDF and transformation state could be verified and its authorized T1 representation reproduced exactly without refitting or label access.

All four frozen model families were attempted. LR, XGBoost and LightGBM produced faithful, repeatable explanations; RF was excluded after exact TreeSHAP additivity failed. The manuscript explicitly reports that failure, model-dependent rankings, reconstructed artifact status, and the single-project/single-modality boundary. E1 is neither presented as all-project coverage nor propagated algebraically into E2. The bounded feature-level evidence complements the primary multimodal explanation and does not establish causality or validate predictive accuracy.
