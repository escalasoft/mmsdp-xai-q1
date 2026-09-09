# Literature-supported methodological rationale

These sources support general principles; none validates this repository's reconstructed matrices or grants journal acceptance.

ML pipelines transform raw data into features and generate intermediate artifacts. Ormenisan et al. describe capturing processing/artifact provenance and using versioned data for reproducibility and debugging. This motivates retaining source, transformation and representation lineage. [Ormenisan et al., OpML 2020](https://www.usenix.org/conference/opml20/presentation/ormenisan).

Pineau et al. identify reliable reporting and reproducibility as methodological requirements and discuss code submission, reproducibility challenges and checklists. This supports documenting code, data and experimental choices; it does not establish that a missing historical state can be recovered. [Pineau et al., JMLR 2021](https://jmlr.org/papers/v22/20-303.html).

ML Metadata explicitly models artifacts and executions and supports tracing how artifacts were produced. It illustrates why preprocessing, data lineage and environment metadata must accompany model/output artifacts. This is primary engineering documentation, not peer-reviewed evidence for the particular amendment. [TensorFlow ML Metadata](https://www.tensorflow.org/tfx/guide/mlmd).

SHAP assigns feature importance to particular model predictions. Its additive explanation formulation supports post-hoc analysis of documented model inputs, not causal claims or provenance inference. It cannot establish that a reconstructed input equals an unavailable historical matrix. [Lundberg and Lee, NeurIPS 2017](https://proceedings.neurips.cc/paper/2017/hash/8a20a8621978632d76c43dfd28b67767-Abstract.html).

Our methodological inference is conditional: explicit source/transform lineage, deterministic reconstruction, previously supported predictor equivalence and complete persistence can define a transparent new explanatory experiment. Historical preprocessing capture gaps remain limitations. Exact safe input routing and scientific semantics must still pass independent checks. The literature does not demonstrate those checks for MMSDP-XAI, does not declare this exact workflow standard, and does not say that Q1 journals explicitly allow reconstructed feature matrices.

The mandatory A–Z persistence policy is a prospective project decision informed by these principles, not a quotation or universal rule attributed to any single source.
