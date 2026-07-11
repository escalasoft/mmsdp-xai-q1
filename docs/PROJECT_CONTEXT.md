# MMSDP-XAI Project Context

Version: 2.0

This document consolidates only information stated in the authoritative documents under `reference/`.

Authoritative sources used:

- `reference/project_plan/Proyecto_de_Tesis.docx`
- `reference/thesis/Thesis_Draft.docx`
- `reference/paper/Paper_Draft.docx`

## 1. Research Motivation

Software defects remain a persistent and growing challenge because they affect product quality, operational reliability, security, maintenance effort, and economic performance. The project plan reports that poor software quality in the United States reached USD 2.41 trillion and accumulated technical debt reached USD 1.52 trillion, citing CISQ 2022. (Source: `reference/project_plan/Proyecto_de_Tesis.docx`, P8)

Software Defect Prediction (SDP) is motivated by the need to identify, before production failures occur, components, modules, or changes that are likely to contain defects, so that testing and validation resources can be prioritized. (Sources: `reference/project_plan/Proyecto_de_Tesis.docx`, P10; `reference/paper/Paper_Draft.docx`, P29)

The motivation for MMSDP-XAI is that traditional SDP approaches are predominantly unimodal, usually relying on static code metrics, while modern projects generate heterogeneous information from source code, change histories, collaborative repositories, commit messages, and issues. (Sources: `reference/project_plan/Proyecto_de_Tesis.docx`, P12; `reference/paper/Paper_Draft.docx`, P29)

The paper draft states that no existing framework explicitly combines multiple heterogeneous modalities for defect prediction while also providing modality-adapted explainability. It argues that defects arise from interactions among code complexity, development process dynamics, textual communication, and dependency structure. (Source: `reference/paper/Paper_Draft.docx`, P34)

## 2. Research Problem

The research problem is the lack of an integrative framework that explicitly combines heterogeneous modalities for software defect prediction while providing modality-adapted explainability and well-calibrated probabilities. This gap prevents development, QA, and management teams from anticipating and understanding defect causes through the interaction of multiple software development artifacts. (Source: `reference/project_plan/Proyecto_de_Tesis.docx`, P26)

The general research question is: how does integrating a multimodal and explainable framework that combines code, process, and text artifacts influence the precision, reliability, and interpretability of software defect prediction in modern development environments? (Source: `reference/project_plan/Proyecto_de_Tesis.docx`, P32)

Specific problem areas are architecture design, construction of a temporally valid commit-level multimodal dataset, performance improvement over unimodal and bimodal baselines, impact of post-hoc probabilistic calibration, and implementation of global, local, and counterfactual explainability. (Source: `reference/project_plan/Proyecto_de_Tesis.docx`, P36-P44)

## 3. General Objective

Propose and validate a multimodal and explainable framework, MMSDP-XAI, for software defect prediction that integrates heterogeneous code, process, and text artifacts and demonstrates improved predictive performance, probability reliability, and interpretability compared with unimodal approaches. (Source: `reference/project_plan/Proyecto_de_Tesis.docx`, P76)

## 4. Specific Objectives

1. Design and implement the modular MMSDP-XAI architecture, including multimodal data acquisition, modality-specific preprocessing, unimodal modeling, decision-level late fusion, post-hoc probabilistic calibration, and global, local, and counterfactual explainability layers. (Source: `reference/project_plan/Proyecto_de_Tesis.docx`, P82)
2. Build a commit-level multimodal dataset from the QtBase repository, integrating static and semantic code features, JIT process metrics, and commit-message text, using a strict 70/15/15 temporal split and leakage control. (Source: `reference/project_plan/Proyecto_de_Tesis.docx`, P84)
3. Empirically evaluate MMSDP-XAI against unimodal and bimodal baselines using discrimination metrics including AUC-ROC, AUC-PR, recall, precision, and F1 under class imbalance. (Source: `reference/project_plan/Proyecto_de_Tesis.docx`, P86)
4. Evaluate prediction reliability by applying post-fusion Platt calibration and measuring ECE and MCE, comparing calibrated and uncalibrated probabilities. (Source: `reference/project_plan/Proyecto_de_Tesis.docx`, P88)
5. Implement and demonstrate explainability at three levels: global SHAP importance, local SHAP force plots, and counterfactual changes that alter predictions, with relevance for developers, QA engineers, and project managers. (Source: `reference/project_plan/Proyecto_de_Tesis.docx`, P90)

## 5. Research Hypothesis

The general hypothesis is that implementing MMSDP-XAI, integrating heterogeneous code, process, and text artifacts, significantly improves predictive performance measured by AUC-PR and recall, probability reliability measured by ECE, and interpretability evidenced through global, local, and counterfactual SHAP analysis, compared with traditional unimodal and limited bimodal approaches under temporal validation and class imbalance conditions. (Source: `reference/project_plan/Proyecto_de_Tesis.docx`, P276)

The specific hypotheses state that the architecture is feasible with open-source tools; the QtBase multimodal dataset with 22 features and 70/15/15 temporal split is adequate; multimodal models outperform unimodal and bimodal models in AUC-PR and recall; post-fusion Platt calibration reduces ECE and MCE; and SHAP values identify modality and feature contributions useful to different project roles. (Source: `reference/project_plan/Proyecto_de_Tesis.docx`, P284-P292)

## 6. Scope

The framework scope covers three modalities: code, process, and text. Code includes static metrics and semantic representations; process includes just-in-time change characteristics; text includes commit messages and issue descriptions or associated textual artifacts. (Sources: `reference/project_plan/Proyecto_de_Tesis.docx`, P82-P84; `reference/paper/Paper_Draft.docx`, P40)

The unit of analysis is the commit. Each commit includes metadata, change statistics, modality-specific features, and a binary label indicating whether the change is defect-prone or clean. (Sources: `reference/project_plan/Proyecto_de_Tesis.docx`, P391; `reference/thesis/Thesis_Draft.docx`, P642-P643)

The empirical dataset is based on QtBase commits from 2018 to 2023 and uses temporal validation to simulate prediction of future defects from past information. (Sources: `reference/project_plan/Proyecto_de_Tesis.docx`, P427-P429; `reference/paper/Paper_Draft.docx`, P125, P169)

The paper draft mentions that the system is modular and can incorporate additional modalities. (Source: `reference/paper/Paper_Draft.docx`, P40)

## 7. Scientific Contribution

The project contributes a unified architecture for SDP and XAI that integrates three complementary modalities and treats explainability as a central component rather than a post-hoc add-on. (Source: `reference/project_plan/Proyecto_de_Tesis.docx`, P54)

It contributes rigorous experimental protocols, including temporal validation and leakage control, and a multimodal public dataset intended to support future comparisons and replication. (Source: `reference/project_plan/Proyecto_de_Tesis.docx`, P56)

It contributes to understanding how code, process, and text characteristics interact in defect generation. (Source: `reference/project_plan/Proyecto_de_Tesis.docx`, P58)

The thesis draft identifies the convergence of multimodal integration, explainable AI, and probabilistic calibration in a unified architecture as the main conceptual contribution of MMSDP-XAI. (Source: `reference/thesis/Thesis_Draft.docx`, P556-P561)

## 8. Paper Contribution

The paper draft states four main contributions: a unified multimodal architecture, user-centered explainability, an empirical basis for rigorous comparison of unimodal and multimodal models, and quantitative and qualitative demonstration of the impact of multimodality on precision and explanation usability. (Source: `reference/paper/Paper_Draft.docx`, P42-P47)

The paper draft presents MMSDP-XAI as a framework combining unimodal learning, decision-level multimodal fusion, post-hoc probability calibration, and global/local explainability for reliable risk estimation and practical transparency. (Source: `reference/paper/Paper_Draft.docx`, P17)

## 9. Doctoral Thesis Contribution

The doctoral thesis contribution is the design, implementation, and validation of MMSDP-XAI as a multimodal, explainable, and probabilistically reliable framework for software defect prediction. (Sources: `reference/thesis/Thesis_Draft.docx`, P595-P596; `reference/project_plan/Proyecto_de_Tesis.docx`, P76)

The thesis methodology integrates evidence-based software engineering, machine learning, multimodal learning, and explainable AI to develop a model that improves defect prediction through multiple modalities and generates interpretable and probabilistically reliable predictions. (Source: `reference/thesis/Thesis_Draft.docx`, P595)

## 10. Current Implementation Status

The source documents contain draft-stage and implementation-status inconsistencies.

The project plan describes implementation of MMSDP-XAI as a planned activity, with the software artifact expected in month 6. (Source: `reference/project_plan/Proyecto_de_Tesis.docx`, T14R5; T15R4)

The paper draft states that the dataset construction pipeline was built with scripts, that the dataset was released in a public repository under CC BY 4.0, and that the code is available in a complementary repository, but it also shows placeholder values such as `https://doi.org/10.5281/zenodo.xxxxxx`, `https://github.com/...`, and "DOI pendiente". (Source: `reference/paper/Paper_Draft.docx`, P150-P162)

The project plan states that annexes, formats, templates, and diagrams will be completed and validated during execution of the research. (Source: `reference/project_plan/Proyecto_de_Tesis.docx`, P952)

No source document specifies the current implementation status of this local workspace. Not specified in the source documents.

## 11. Planned System Architecture

MMSDP-XAI is planned as a modular architecture with six layers: data acquisition, modality-specific preprocessing, unimodal modeling, multimodal fusion, probabilistic calibration, and explanation generation. (Source: `reference/project_plan/Proyecto_de_Tesis.docx`, P243)

The planned architecture ingests code, process, and text modalities; preprocesses each modality; trains unimodal models; performs late fusion through a logistic-regression metamodel with 5-fold stacking; applies post-fusion Platt scaling; and generates SHAP-based global, local, and counterfactual explanations. (Source: `reference/project_plan/Proyecto_de_Tesis.docx`, P805-P856)

The paper draft specifies modality-specific model choices: XGBoost or LightGBM for code metrics and embeddings, LSTM for JIT process sequences, and fine-tuned CodeBERT for text. (Source: `reference/paper/Paper_Draft.docx`, P96-P100)

The paper draft states that late decision-level fusion uses the raw probabilities from code, process, and text models as inputs to a higher-level metamodel, with logistic regression with L2 regularization selected as the default metamodel. (Source: `reference/paper/Paper_Draft.docx`, P101-P105)

## 12. Datasets

The main dataset is based on the QtBase repository, selected for maturity, long development history, more than 50,000 commits in the analyzed period, and availability of defect-labeled issue data. (Sources: `reference/project_plan/Proyecto_de_Tesis.docx`, P427; `reference/paper/Paper_Draft.docx`, P121-P124)

The paper draft calls the dataset `MQtBase` and later `MQtDbase`. This naming inconsistency is present in the source documents. (Source: `reference/paper/Paper_Draft.docx`, P120-P152)

The dataset integrates three modalities at commit level: text from commit messages, process metrics from Git history, and code metrics from source snapshots and static/AST analysis. (Source: `reference/paper/Paper_Draft.docx`, P126-P130)

The paper draft states that commits from the main branch between January 1, 2018 and December 31, 2023 are included, excluding merge commits, commits without meaningful messages, and commits related only to documentation or CI configuration. (Source: `reference/paper/Paper_Draft.docx`, P125)

Dataset size is inconsistent across the source documents. The paper draft reports filtering 620,859 commits to 200,712 valid instances before integration, then reports a final set of 51,280 commits with 4,892 defect-labeled commits. (Source: `reference/paper/Paper_Draft.docx`, P125, P138) The project plan also reports 51,280 commits and 4,892 positives. (Source: `reference/project_plan/Proyecto_de_Tesis.docx`, P421) The thesis draft reports 15,424 valid commits and explicitly notes that the number should be replaced if the final dataset changes. (Source: `reference/thesis/Thesis_Draft.docx`, P709)

The final feature set reported by the paper draft contains 22 features: 5 text features, 9 process features, 6 code features, and 2 control variables retained for traceability and temporal partitioning but excluded from model training. (Source: `reference/paper/Paper_Draft.docx`, P145)

## 13. Experimental Methodology

The thesis draft describes the research as quantitative, applied, and computational-experimental, using hypotheses, objective measurement of variables, predictive model construction, and statistical analysis over real software repositories. (Source: `reference/thesis/Thesis_Draft.docx`, P599-P607)

The project plan describes a quasi-experimental intra-subject design in which the same commit units are evaluated under different framework configurations: unimodal code, unimodal process, unimodal text, bimodal configurations, and full multimodal MMSDP-XAI. (Source: `reference/project_plan/Proyecto_de_Tesis.docx`, P353-P357; T1R2)

The experimental process includes construction of the multimodal dataset, training and validation of unimodal models, stacking and late-fusion metamodel training, Platt calibration on the validation set, metric calculation, SHAP explanation generation, counterfactual generation, Wilcoxon paired tests, bootstrap confidence intervals with 1,000 replicas, and hypothesis acceptance or rejection at alpha 0.05. (Source: `reference/project_plan/Proyecto_de_Tesis.docx`, P857-P893)

Preprocessing must fit transformations only on training data and apply them identically to validation and test sets to avoid contamination. Numeric features use median imputation, logarithmic or power transformation, robust scaling, and percentile truncation; embeddings are passed through without additional standardization. (Source: `reference/paper/Paper_Draft.docx`, P90-P94)

## 14. Evaluation Protocol

The evaluation protocol uses strict temporal validation: commits are ordered chronologically, the oldest 70% are used for training, the next 15% for validation, and the most recent 15% for testing. (Sources: `reference/project_plan/Proyecto_de_Tesis.docx`, P267, P899-P912; `reference/paper/Paper_Draft.docx`, P88, P169)

The test set is reserved exclusively for final evaluation. (Source: `reference/thesis/Thesis_Draft.docx`, P713-P717)

Discrimination metrics include AUC-ROC, AUC-PR, precision, recall, F1-score, and, in the thesis metrics table, MCC. (Sources: `reference/project_plan/Proyecto_de_Tesis.docx`, T2R2; `reference/thesis/Thesis_Draft.docx`, T4R2-T4R8)

Calibration metrics include ECE, MCE, Brier Score, and reliability diagrams, with the project plan emphasizing ECE and MCE for hypothesis testing. (Sources: `reference/project_plan/Proyecto_de_Tesis.docx`, P532; `reference/thesis/Thesis_Draft.docx`, T4R9-T4R11)

Interpretability evaluation uses SHAP global summaries, local force plots, and counterfactual examples for representative cases. (Sources: `reference/project_plan/Proyecto_de_Tesis.docx`, P538; `reference/paper/Paper_Draft.docx`, P113-P119)

## 15. Reproducibility Requirements

The project requires temporal validation and leakage control to avoid future information entering training data. (Sources: `reference/project_plan/Proyecto_de_Tesis.docx`, P267, P347; `reference/paper/Paper_Draft.docx`, P139-P143)

Extraction, transformation, and integration procedures should be automated so the dataset can be reconstructed using the same methodological protocol. (Source: `reference/thesis/Thesis_Draft.docx`, P790-P792)

Each commit must remain traceable by its hash, partition assignment must be recorded, and processed datasets must be stored as CSV files with metadata. (Source: `reference/project_plan/Proyecto_de_Tesis.docx`, T9R4)

The project plan states that extraction scripts are documented and available in a public repository, and gives execution instructions for environment setup and dataset construction. (Source: `reference/project_plan/Proyecto_de_Tesis.docx`, P482-P494)

The project plan states that data come from open-source repositories and must be used for academic purposes while respecting licenses. It also states that source repository information was not manipulated or altered and that automated scripts preserve source data integrity. (Source: `reference/project_plan/Proyecto_de_Tesis.docx`, P944-P946)

## 16. Coding Standards

Python 3.10+ is specified as the main programming language. (Source: `reference/project_plan/Proyecto_de_Tesis.docx`, T10R2)

Specified tools include scikit-learn 1.2+ for modeling, metrics, calibration, and preprocessing; XGBoost or LightGBM 1.7+ for code modality modeling; TensorFlow/Keras 2.12+ for LSTM and CodeBERT-related modeling; SHAP 0.41+ for explainability; pandas/NumPy 1.5+ for data manipulation; Matplotlib/Seaborn 3.7+ for visualization; and SciPy 1.10+ for Wilcoxon tests and bootstrap. (Source: `reference/project_plan/Proyecto_de_Tesis.docx`, T10R2-T10R9)

Scripts are expected for extraction, dataset construction, training baselines, multimodal training, calibration, metric collection, SHAP plots, and counterfactual generation. (Sources: `reference/project_plan/Proyecto_de_Tesis.docx`, T8R5-T8R7; `reference/paper/Paper_Draft.docx`, P154-P162)

Detailed repository-level coding style, formatting rules, naming conventions, linting rules, type-checking requirements, and testing standards are not specified in the source documents.

## 17. Documentation Standards

The project plan states that APA 7th edition formatting is used for references, including author names, year, title, journal or book title, volume, issue, page range, DOI, or URL where available. (Source: `reference/project_plan/Proyecto_de_Tesis.docx`, P756)

The project plan states that references to conference proceedings follow APA format and that arXiv references include arXiv identifiers as DOI alternatives. (Source: `reference/project_plan/Proyecto_de_Tesis.docx`, P760-P762)

The project plan states that the architecture should be documented through component diagrams and that the pipeline execution should be verified. (Source: `reference/project_plan/Proyecto_de_Tesis.docx`, P514)

Detailed documentation rules for Markdown files, docstrings, API documentation, changelogs, experiment reports, or code comments are not specified in the source documents.

## 18. Files That Must Never Be Modified Automatically

Not specified in the source documents.

## 19. Development Roadmap

The project plan defines a 12-month roadmap:

1. Review the systematic literature and update the state of the art during months 1-3. (Source: `reference/project_plan/Proyecto_de_Tesis.docx`, T14R2)
2. Design the detailed MMSDP-XAI architecture during months 2-3. (Source: `reference/project_plan/Proyecto_de_Tesis.docx`, T14R3)
3. Construct the multimodal QtBase dataset during months 3-5. (Source: `reference/project_plan/Proyecto_de_Tesis.docx`, T14R4)
4. Implement MMSDP-XAI, including unimodal models, fusion, and calibration, during months 4-6. (Source: `reference/project_plan/Proyecto_de_Tesis.docx`, T14R5)
5. Execute experiments and empirical validation during months 6-7. (Source: `reference/project_plan/Proyecto_de_Tesis.docx`, T14R6)
6. Analyze results and test hypotheses during months 7-8.5. (Source: `reference/project_plan/Proyecto_de_Tesis.docx`, T14R7)
7. Draft the doctoral thesis during months 7-10. (Source: `reference/project_plan/Proyecto_de_Tesis.docx`, T14R8)
8. Draft the indexed journal article during months 9-10. (Source: `reference/project_plan/Proyecto_de_Tesis.docx`, T14R9)
9. Complete post-advisory revisions and prepare the defense during months 10-11. (Source: `reference/project_plan/Proyecto_de_Tesis.docx`, T14R10)
10. Defend the thesis and disseminate results in month 12. (Source: `reference/project_plan/Proyecto_de_Tesis.docx`, T14R11)

The project plan includes milestones for architecture approval, validated dataset, implemented software artifact, preliminary experimental results, complete thesis draft, journal submission, final advisor-approved thesis, and thesis defense approval. (Source: `reference/project_plan/Proyecto_de_Tesis.docx`, T15R2-T15R9)

The project plan states that the schedule is initial planning subject to adjustment and recommends quarterly review of actual progress against planned progress. (Source: `reference/project_plan/Proyecto_de_Tesis.docx`, P688)

## 20. Canonical Terminology

Official project title: "Un marco multimodal y explicable para la prediccion de defectos de software." (Sources: `reference/project_plan/Proyecto_de_Tesis.docx`, P1; `reference/paper/Paper_Draft.docx`, P1)

Official framework name: MMSDP-XAI, expanded as Multimodal Software Defect Prediction with Explainable Artificial Intelligence or Multimodal Software Defect Prediction with Explainable AI. (Sources: `reference/thesis/Thesis_Draft.docx`, P728; `reference/paper/Paper_Draft.docx`, P36)

Official research domain: Software Defect Prediction, abbreviated SDP. (Sources: `reference/project_plan/Proyecto_de_Tesis.docx`, P10; `reference/thesis/Thesis_Draft.docx`, P200)

Dataset name: the paper draft uses `MQtBase` and later `MQtDbase`; `MQtBase` is the dataset name used when introducing the dataset, while the naming inconsistency remains unresolved in the sources. (Source: `reference/paper/Paper_Draft.docx`, P120-P152)

Unit of analysis: commit. (Sources: `reference/project_plan/Proyecto_de_Tesis.docx`, P219, P391; `reference/thesis/Thesis_Draft.docx`, P642-P643)

Main project repository used for the dataset: QtBase, available at `https://github.com/qt/qtbase.git`. (Source: `reference/paper/Paper_Draft.docx`, P121)

Main programming language for implementation: Python 3.10+. (Source: `reference/project_plan/Proyecto_de_Tesis.docx`, T10R2)

Official modalities: code, process, and text. (Sources: `reference/project_plan/Proyecto_de_Tesis.docx`, P82-P84; `reference/paper/Paper_Draft.docx`, P40)

Official validation term: temporal validation, using past data for training, intermediate data for validation, and future data for testing. (Sources: `reference/project_plan/Proyecto_de_Tesis.docx`, P267; `reference/paper/Paper_Draft.docx`, P169)

Official explainability terminology: global explanations, local explanations, and counterfactual explanations based primarily on SHAP. (Sources: `reference/project_plan/Proyecto_de_Tesis.docx`, P90; `reference/paper/Paper_Draft.docx`, P113-P119)

Official calibration terminology: post-fusion Platt calibration, evaluated with ECE and MCE. (Sources: `reference/project_plan/Proyecto_de_Tesis.docx`, P88, P532; `reference/paper/Paper_Draft.docx`, P109-P112)

## 21. Frozen Research Decisions

The following decisions are treated as frozen because they are repeatedly specified in the source documents:

1. Unit of analysis: commit. (Sources: `reference/project_plan/Proyecto_de_Tesis.docx`, P219, P391; `reference/thesis/Thesis_Draft.docx`, P642-P643)
2. Main dataset: QtBase-based multimodal dataset introduced as `MQtBase`. (Sources: `reference/project_plan/Proyecto_de_Tesis.docx`, P427; `reference/paper/Paper_Draft.docx`, P120-P124)
3. Modalities: code, process, and text. (Sources: `reference/project_plan/Proyecto_de_Tesis.docx`, P82-P84; `reference/paper/Paper_Draft.docx`, P40)
4. Temporal validation split: 70% training, 15% validation, and 15% testing in chronological order. (Sources: `reference/project_plan/Proyecto_de_Tesis.docx`, P267, P899-P912; `reference/paper/Paper_Draft.docx`, P88, P169)
5. Main fusion strategy: late decision-level fusion using a metamodel over unimodal predictions. (Sources: `reference/project_plan/Proyecto_de_Tesis.docx`, P166, P243; `reference/paper/Paper_Draft.docx`, P101-P105)
6. Calibration strategy: post-fusion Platt calibration. (Sources: `reference/project_plan/Proyecto_de_Tesis.docx`, P88, P184; `reference/paper/Paper_Draft.docx`, P109-P112)
7. Explainability strategy: SHAP-based global and local explanations, with counterfactual explanation support. (Sources: `reference/project_plan/Proyecto_de_Tesis.docx`, P90, P292; `reference/paper/Paper_Draft.docx`, P113-P119)
8. Leakage control: mandatory filtering and verification to prevent heuristic and temporal leakage. (Sources: `reference/project_plan/Proyecto_de_Tesis.docx`, P267, P347; `reference/paper/Paper_Draft.docx`, P139-P143)

## 22. Known Inconsistencies

The paper draft introduces the dataset as `MQtBase` and later refers to `MQtDbase`. The authoritative dataset name is therefore inconsistent in the sources. (Source: `reference/paper/Paper_Draft.docx`, P120-P152)

Dataset size differs across documents. The paper draft reports an initial filter from 620,859 commits to 200,712 valid instances and then a final set of 51,280 commits with 4,892 defect-labeled commits. The project plan also reports 51,280 commits and 4,892 positives. The thesis draft reports 15,424 valid commits and explicitly notes that this number must be replaced if the final dataset changes. (Sources: `reference/paper/Paper_Draft.docx`, P125, P138; `reference/project_plan/Proyecto_de_Tesis.docx`, P421; `reference/thesis/Thesis_Draft.docx`, P709)

The paper draft includes unresolved publication and repository placeholders, including `https://doi.org/10.5281/zenodo.xxxxxx`, `https://github.com/...`, and "DOI pendiente". (Source: `reference/paper/Paper_Draft.docx`, P150-P162)

The paper draft states in one contribution that the framework captures four modalities, while other core sections define three modalities: code, process, and text. (Sources: `reference/paper/Paper_Draft.docx`, P40, P44)

The paper draft describes both early and late fusion in one proposal paragraph, while later architecture and methodology sections specify late decision-level fusion as the adopted strategy. (Sources: `reference/paper/Paper_Draft.docx`, P40, P101-P105)

## 23. Research Risks

Data leakage is a methodological risk because features may encode the target label or future information. The source documents require leakage filtering, temporal validation, and exclusion of variables that encode future information or labeling heuristics. (Sources: `reference/paper/Paper_Draft.docx`, P139-P143; `reference/project_plan/Proyecto_de_Tesis.docx`, P267)

Dataset inconsistency is a risk because the source documents report different dataset names and sizes. (Sources: `reference/paper/Paper_Draft.docx`, P120-P152; `reference/project_plan/Proyecto_de_Tesis.docx`, P421; `reference/thesis/Thesis_Draft.docx`, P709)

Overfitting is a risk in the metamodel and model training process; the paper draft addresses this through 5-fold stacking for out-of-fold predictions, limited tree depth, early stopping, and a validation set. (Source: `reference/paper/Paper_Draft.docx`, P97-P105)

Class imbalance is a risk because the project plan and paper draft report approximately 9.54% positives. The research objectives and hypotheses emphasize AUC-PR and recall under class imbalance. (Sources: `reference/project_plan/Proyecto_de_Tesis.docx`, P286-P288; `reference/paper/Paper_Draft.docx`, P138)

Over-complexity of LSTM and CodeBERT in the first implementation is a risk because the planned architecture specifies LSTM for process and fine-tuned CodeBERT for text, while the paper draft also notes a lighter embedding-based alternative when GPU is unavailable. (Sources: `reference/paper/Paper_Draft.docx`, P98-P100; `reference/project_plan/Proyecto_de_Tesis.docx`, T10R5)

Misalignment between thesis, paper, and code is a risk because the source documents already contain inconsistencies in dataset naming, dataset size, and unresolved repository/DOI placeholders. (Sources: `reference/paper/Paper_Draft.docx`, P120-P162; `reference/thesis/Thesis_Draft.docx`, P709)

## 24. Decision History

### 2026-07-01

- Project repository initialized. (Source: current repository state)
- Reference documents added under `reference/`: project plan, thesis draft, and paper draft. (Source: current repository state)
- `docs/PROJECT_CONTEXT.md` created as the first Single Source of Truth document. (Source: current repository state)

## 25. Current Development Status

Repository scaffold created. The current repository contains placeholder-backed directories for `configs`, `data`, `docs`, `notebooks`, `src`, `tests`, `scripts`, `experiments`, `outputs`, and `paper`. (Source: current repository state)

Reference documents added. The current repository contains `reference/project_plan/Proyecto_de_Tesis.docx`, `reference/thesis/Thesis_Draft.docx`, and `reference/paper/Paper_Draft.docx`. (Source: current repository state)

`docs/PROJECT_CONTEXT.md` created and updated to version 2.0. (Source: current repository state)

Architecture document pending. No separate architecture document exists in the current repository state.

Dataset pipeline pending. No dataset pipeline implementation exists in the current repository state.

Model implementation pending. No model implementation exists in the current repository state.

Experiments pending. No experiment implementation or experiment result files exist in the current repository state.
