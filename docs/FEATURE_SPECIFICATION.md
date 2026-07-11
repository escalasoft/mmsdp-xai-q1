# MMSDP-XAI Feature Specification

Version: 1.0  
Status: Draft governance specification  
Primary source of truth: `docs/PROJECT_CONTEXT.md` Version 2.0

## 1. Purpose

This document defines the implementation-independent governance specification for features that may appear in the MMSDP-XAI project.

It specifies how features must be identified, categorized, validated, audited for leakage, traced to source artifacts, versioned, and approved before use in modeling or interpretation.

This document does not define final feature counts, feature values, repository statistics, embeddings, implemented transformations, or completed feature engineering. Unresolved items are marked as `Pending Decision`.

## 2. Scope

This specification applies to every candidate, approved, quarantined, deprecated, or forbidden variable associated with the MQtBase dataset and MMSDP-XAI experiments.

In scope:

- Commit-level code features.
- Commit-level process features.
- Commit-level text features.
- Metadata used for governance, reproducibility, and traceability.
- Traceability variables used to link records, outputs, and evidence.
- Target variables and label evidence.
- Forbidden variables and leakage-sensitive variables.
- Feature lineage, validation, versioning, and quality controls.

Out of scope:

- Machine learning model implementation.
- Final feature engineering algorithms.
- Final embedding models or embedding dimensions.
- Final dataset statistics or feature counts.
- Experimental results.
- Journal-specific manuscript formatting.

## 3. Source Authority

`docs/PROJECT_CONTEXT.md` Version 2.0 is the Single Source of Truth for this document.

The following documents are used only for consistency with existing governance:

| Document | Role in This Specification |
| --- | --- |
| `docs/SYSTEM_ARCHITECTURE.md` | Confirms system layers, repository paths, modalities, leakage prevention, and train-only preprocessing. |
| `docs/DATASET_SPECIFICATION.md` | Confirms dataset lifecycle, commit-level unit, schema governance, lineage, and dataset validation controls. |
| `docs/DESIGN_DECISIONS.md` | Provides decision IDs for feature governance and leakage controls. |
| `docs/QUALITY_REQUIREMENTS.md` | Provides measurable feature, leakage, preprocessing, and traceability requirements. |
| `docs/RISK_REGISTER.md` | Provides feature-related risks. |
| `docs/EXPERIMENT_QUALITY_GATES.md` | Provides quality gates that block or condition feature use. |

## 4. Feature Governance

All features must be governed before they are used as predictors.

| Governance Rule | Specification |
| --- | --- |
| Unit of analysis | Commit. |
| Core predictor modalities | Code, Process, and Text. |
| Metadata role | Governance, reproducibility, and traceability only. |
| Traceability variables | Not predictors. |
| Target variables | Never predictors. |
| Label-derived variables | Forbidden by default. |
| Proxy-target variables | Forbidden by default until explicitly cleared by governance. |
| Future-derived variables | Forbidden by default. |
| Identifier variables | Traceability-only by default. |
| Preprocessing fit scope | Any fitted transformation must be fitted only on training data. |
| Primary split policy | Strict chronological 70 / 15 / 15 validation. |
| Feature approval evidence | Feature registry, lineage, leakage classification, validation rule, and quality gate status. |

## 5. Feature Lifecycle

Each feature must move through a documented lifecycle.

| Stage | Name | Description | Required Evidence | Allowed Next States |
| --- | --- | --- | --- | --- |
| F0 | Proposal | A candidate feature is identified from an approved source artifact. | Feature registry draft. | Candidate, Forbidden |
| F1 | Source mapping | The feature is linked to a source artifact and commit-level derivation rule. | Lineage entry. | Candidate, Quarantined, Forbidden |
| F2 | Timing review | The feature is checked for availability at prediction time. | Temporal leakage review. | Candidate, Quarantined, Forbidden |
| F3 | Semantic leakage review | The feature is checked for label-derived, proxy-target, or issue-derived leakage. | Semantic leakage report. | Approved, Quarantined, Forbidden |
| F4 | Validation design | The feature receives type, missing-value, and value-domain validation rules. | Feature validation rule. | Candidate, Approved, Quarantined |
| F5 | Approval | The feature is approved for a specific dataset version and split protocol. | Feature registry approval. | Approved, Deprecated |
| F6 | Experiment use | The feature may be used only in eligible configurations and tracked in manifests. | Run manifest and training feature list. | Approved, Quarantined, Deprecated |
| F7 | Monitoring | Ablation, plausibility, and explanation checks may trigger review. | Ablation and plausibility reports. | Approved, Quarantined, Deprecated, Forbidden |
| F8 | Retirement | The feature is removed or superseded. | Deprecation record. | Deprecated, Forbidden |

## 6. Feature Categories

| Category | Modality | Predictor Eligibility | Purpose | Governing Controls |
| --- | --- | --- | --- | --- |
| Code | Code | Eligible only after approval | Represent source-code or code-change information at commit level. | DD-004, DD-005, QR-005, G3, G4 |
| Process | Process | Eligible only after approval | Represent development-process or change-process information at commit level. | DD-004, DD-005, QR-005, G3, G4, G5 |
| Text | Text | Eligible only after approval | Represent commit-message or approved text information available at prediction time. | DD-004, DD-005, QR-005, QR-006, G3, G4 |
| Metadata | None | Not eligible by default | Support governance, reproducibility, partitioning, and audit. | DD-006, QR-003, QR-009 |
| Traceability | None | Not eligible | Link commits, labels, predictions, metrics, and explanations to evidence. | DD-002, DD-006, QR-003 |
| Target | None | Never eligible | Define the supervised learning outcome. | DD-005, QR-004, G2 |
| Forbidden | None or Pending Decision | Never eligible unless governance reclassifies the variable | Quarantine leakage-sensitive, label-derived, proxy-target, or future-derived variables. | DD-005, QR-006, QR-007, QR-008, G4 |

## 7. Feature Registry

The final feature registry is `Pending Decision`.

Every feature definition must contain the following fields.

| Field | Requirement |
| --- | --- |
| Feature ID | Stable identifier for the feature. |
| Feature Name | Human-readable feature name. |
| Category | Code, Process, Text, Metadata, Traceability, Target, or Forbidden. |
| Modality | Code, Process, Text, None, or Pending Decision. |
| Description | Implementation-independent description. |
| Data Type | Final type or `Pending Decision`. |
| Source Artifact | Repository-relative source artifact or approved source type. |
| Derivation Rule | Non-code transformation description or `Pending Decision`. |
| Available at Prediction Time | Yes, No, or Pending Decision. |
| Leakage Level | Low, Medium, High, or Critical. |
| Predictor Eligibility | Eligible, Not Eligible, Forbidden, or Pending Decision. |
| Missing Value Policy | Approved policy or `Pending Decision`. |
| Validation Rule | Required validation check or `Pending Decision`. |
| Version Introduced | Dataset or feature-spec version. |
| Current Status | Candidate, Approved, Quarantined, Deprecated, or Forbidden. |
| Related Design Decision | Relevant DD ID. |
| Related Quality Requirement | Relevant QR ID. |
| Related Risk | Relevant RK ID. |
| Related Quality Gate | Relevant G ID. |

Feature registry artifacts should be stored under `outputs/reports/` unless a future governance decision specifies a different repository-relative path.

## 8. Code Feature Family

Code features are candidate predictors derived from source-code artifacts, code changes, or approved code representations at the commit level.

The source documents mention code modality and code-related representations, but the final code feature list, feature counts, data types, and transformations are `Pending Decision`.

| Feature ID | Feature Name | Category | Modality | Description | Data Type | Source Artifact | Derivation Rule | Available at Prediction Time | Leakage Level | Predictor Eligibility | Missing Value Policy | Validation Rule | Version Introduced | Current Status | Related Design Decision | Related Quality Requirement | Related Risk | Related Quality Gate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| FEAT-CODE-PD | Pending Decision | Code | Code | Candidate commit-level code feature derived from approved QtBase code artifacts. | Pending Decision | `data/raw/` or `data/interim/` | Pending Decision | Pending Decision | Medium | Pending Decision | Pending Decision | Must be commit-scoped and leakage-reviewed. | Pending Decision | Candidate | DD-004, DD-005 | QR-005, QR-007 | RK-002, RK-008 | G3, G4, G5 |

Code features must not use future source snapshots or post-commit information. Snapshot timing is part of leakage validation and remains `Pending Decision`.

## 9. Process Feature Family

Process features are candidate predictors derived from commit metadata, change history, or development-process artifacts available at prediction time.

The source documents identify process modality as part of the project scope, but the final process feature list, feature counts, and derivation rules are `Pending Decision`.

| Feature ID | Feature Name | Category | Modality | Description | Data Type | Source Artifact | Derivation Rule | Available at Prediction Time | Leakage Level | Predictor Eligibility | Missing Value Policy | Validation Rule | Version Introduced | Current Status | Related Design Decision | Related Quality Requirement | Related Risk | Related Quality Gate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| FEAT-PROC-PD | Pending Decision | Process | Process | Candidate commit-level process feature derived from approved commit or change-process artifacts. | Pending Decision | `data/raw/` or `data/interim/` | Pending Decision | Pending Decision | Medium | Pending Decision | Pending Decision | Must be commit-scoped, time-available, and leakage-reviewed. | Pending Decision | Candidate | DD-004, DD-005, DD-007 | QR-005, QR-007, QR-011 | RK-002, RK-008 | G3, G4, G5 |

Process features must not use future commits, future issue outcomes, validation/test distribution information, or post-commit evidence.

## 10. Text Feature Family

Text features are candidate predictors derived from approved text artifacts available at commit prediction time.

The source documents identify text modality and commit-message information as part of the project scope. Final text features, vocabulary policy, embeddings, embedding dimensions, and text preprocessing rules are `Pending Decision`.

| Feature ID | Feature Name | Category | Modality | Description | Data Type | Source Artifact | Derivation Rule | Available at Prediction Time | Leakage Level | Predictor Eligibility | Missing Value Policy | Validation Rule | Version Introduced | Current Status | Related Design Decision | Related Quality Requirement | Related Risk | Related Quality Gate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| FEAT-TEXT-PD | Pending Decision | Text | Text | Candidate commit-level text feature derived from approved text artifacts. | Pending Decision | `data/raw/` or `data/interim/` | Pending Decision | Pending Decision | High | Pending Decision | Pending Decision | Must pass semantic leakage review and train-only preprocessing checks. | Pending Decision | Candidate | DD-004, DD-005, DD-018 | QR-005, QR-006, QR-010 | RK-001, RK-003, RK-008 | G3, G4, G6 |

Text features derived from label keywords, issue labels, future issue states, or post-hoc defect evidence are forbidden by default.

## 11. Metadata Feature Family

Metadata exists only for governance, reproducibility, partitioning, and traceability unless an explicit future governance decision changes a specific field.

| Feature ID | Feature Name | Category | Modality | Description | Data Type | Source Artifact | Derivation Rule | Available at Prediction Time | Leakage Level | Predictor Eligibility | Missing Value Policy | Validation Rule | Version Introduced | Current Status | Related Design Decision | Related Quality Requirement | Related Risk | Related Quality Gate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| FEAT-META-001 | `dataset_version` | Metadata | None | Dataset release identifier. | Pending Decision | `data/processed/` | Assigned by dataset governance. | Yes | Low | Not Eligible | Must be present. | Must match dataset manifest. | 1.0 | Approved | DD-001, DD-019 | QR-023, QR-025 | RK-018, RK-019 | G16, G18 |
| FEAT-META-002 | `split` | Metadata | None | Train, validation, or test partition marker. | Pending Decision | `data/processed/` | Assigned by chronological partitioning. | Yes | High | Not Eligible | Must be present. | Must contain only approved split labels and must not be used as a predictor. | 1.0 | Approved | DD-006, DD-007 | QR-009, QR-011 | RK-002, RK-003 | G5 |
| FEAT-META-003 | `source_snapshot_id` | Metadata | None | Identifier of the QtBase source snapshot. | Pending Decision | `data/raw/` | Recorded during raw acquisition. | Yes | Low | Not Eligible | Must be present for released datasets. | Must match repository snapshot report. | 1.0 | Approved | DD-003, DD-017 | QR-001, QR-002 | RK-005, RK-018 | G1 |

## 12. Traceability Feature Family

Traceability variables connect commits, labels, features, predictions, metrics, explanations, and reports. They are not predictors.

| Feature ID | Feature Name | Category | Modality | Description | Data Type | Source Artifact | Derivation Rule | Available at Prediction Time | Leakage Level | Predictor Eligibility | Missing Value Policy | Validation Rule | Version Introduced | Current Status | Related Design Decision | Related Quality Requirement | Related Risk | Related Quality Gate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| FEAT-TRACE-001 | `commit_hash` | Traceability | None | Commit-level key linking each row to QtBase source evidence. | Pending Decision | `data/raw/` | Extracted from QtBase commit history. | Yes | High | Not Eligible | Must be present. | Must be unique within each processed dataset version and absent from predictor matrices. | 1.0 | Approved | DD-002, DD-006 | QR-003, QR-009 | RK-003, RK-006, RK-018 | G3, G4 |
| FEAT-TRACE-002 | `commit_timestamp` | Traceability | None | Timestamp used for chronological ordering and partitioning. | Pending Decision | `data/raw/` | Extracted from QtBase commit history. | Yes | High | Not Eligible by default | Must be present for partitioning. | Must support strict chronological split and must not be used as a predictor unless explicitly reclassified. | 1.0 | Approved | DD-006, DD-007 | QR-007, QR-009, QR-011 | RK-002, RK-003 | G5 |
| FEAT-TRACE-003 | `issue_identifier` | Traceability | None | Issue-level identifier used for label evidence or linkage audit when available. | Pending Decision | `data/interim/` | Pending Decision | Pending Decision | Critical | Forbidden | Pending Decision | Must remain outside predictor matrices unless explicitly reclassified by governance. | 1.0 | Forbidden | DD-005, DD-006 | QR-004, QR-006, QR-009 | RK-001, RK-003, RK-006 | G2, G4 |

## 13. Target Variables

Target variables define the supervised outcome and must never be predictors.

| Feature ID | Feature Name | Category | Modality | Description | Data Type | Source Artifact | Derivation Rule | Available at Prediction Time | Leakage Level | Predictor Eligibility | Missing Value Policy | Validation Rule | Version Introduced | Current Status | Related Design Decision | Related Quality Requirement | Related Risk | Related Quality Gate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| FEAT-TARGET-001 | `target_label` | Target | None | Binary defect-prone or clean commit label. | Pending Decision | `data/interim/` or `data/processed/` | Pending Decision | No | Critical | Forbidden | Commits without valid labels must not enter supervised modeling datasets unless approved by governance. | Must be separated from predictors and documented by label rule. | 1.0 | Approved as target | DD-005 | QR-004 | RK-001, RK-007 | G2, G4 |
| FEAT-TARGET-002 | `label_rule_id` | Target | None | Identifier of the rule used to assign the target label. | Pending Decision | `data/interim/` or `outputs/reports/` | Assigned by labeling protocol. | No | Critical | Forbidden | Must be present for labeled records. | Must be traceable to labeling documentation and excluded from predictors. | 1.0 | Approved as target metadata | DD-005 | QR-004 | RK-001, RK-007 | G2 |

## 14. Forbidden Variables

Forbidden variables are not predictors. They may be retained only for labeling, auditing, traceability, or governance when explicitly documented.

The following variables are classified as Forbidden until explicitly approved by governance.

| Feature ID | Feature Name | Category | Modality | Description | Data Type | Source Artifact | Derivation Rule | Available at Prediction Time | Leakage Level | Predictor Eligibility | Missing Value Policy | Validation Rule | Version Introduced | Current Status | Related Design Decision | Related Quality Requirement | Related Risk | Related Quality Gate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| FEAT-FORB-001 | `bug_confidence` | Forbidden | None | Leakage-sensitive variable identified in governance as requiring semantic leakage audit. | Pending Decision | Pending Decision | Pending Decision | Pending Decision | Critical | Forbidden | Pending Decision | Must be excluded from predictor matrices unless formally reclassified. | 1.0 | Forbidden | DD-005 | QR-006, QR-008 | RK-001, RK-003 | G4, G14 |
| FEAT-FORB-002 | `msg_has_bug_kw` | Forbidden | Text | Bug-keyword indicator identified in governance as likely label-derived or proxy-target. | Pending Decision | Pending Decision | Pending Decision | Pending Decision | Critical | Forbidden | Pending Decision | Must be excluded from predictor matrices unless formally reclassified. | 1.0 | Forbidden | DD-005 | QR-006, QR-008 | RK-001, RK-003 | G4, G14 |
| FEAT-FORB-003 | `has_bug_keyword` | Forbidden | Text | Bug-keyword indicator identified in governance as likely label-derived or proxy-target. | Pending Decision | Pending Decision | Pending Decision | Pending Decision | Critical | Forbidden | Pending Decision | Must be excluded from predictor matrices unless formally reclassified. | 1.0 | Forbidden | DD-005 | QR-006, QR-008 | RK-001, RK-003 | G4, G14 |
| FEAT-FORB-004 | `label_confidence` | Forbidden | None | Label-confidence or ambiguity signal associated with target construction. | Pending Decision | `data/interim/` | Pending Decision | No | Critical | Forbidden | Pending Decision | Must be retained only as label metadata or audit evidence. | 1.0 | Forbidden | DD-005 | QR-004, QR-006 | RK-001, RK-007 | G2, G4 |
| FEAT-FORB-005 | Future timestamps | Forbidden | None | Any timestamp or derived value that is unavailable at commit prediction time. | Pending Decision | Pending Decision | Pending Decision | No | Critical | Forbidden | Pending Decision | Must be excluded by temporal leakage audit. | 1.0 | Forbidden | DD-005, DD-007 | QR-007, QR-011 | RK-002 | G5 |
| FEAT-FORB-006 | Issue labels | Forbidden | None | Issue classification labels or post-hoc defect evidence used for target construction or audit. | Pending Decision | Pending Decision | Pending Decision | Pending Decision | Critical | Forbidden | Pending Decision | Must be excluded from predictor matrices unless formally reclassified. | 1.0 | Forbidden | DD-005 | QR-004, QR-006, QR-008 | RK-001, RK-003, RK-007 | G2, G4 |
| FEAT-FORB-007 | Issue identifiers | Forbidden | None | Issue IDs or external issue references that may encode label or temporal information. | Pending Decision | Pending Decision | Pending Decision | Pending Decision | Critical | Forbidden | Pending Decision | Must be retained only for traceability or label audit unless formally reclassified. | 1.0 | Forbidden | DD-005, DD-006 | QR-004, QR-009 | RK-003, RK-006 | G2, G4 |
| FEAT-FORB-008 | Future-derived information | Forbidden | Pending Decision | Any variable computed from information not available at prediction time. | Pending Decision | Pending Decision | Pending Decision | No | Critical | Forbidden | Pending Decision | Must be excluded by semantic and temporal leakage audits. | 1.0 | Forbidden | DD-005, DD-007, DD-018 | QR-007, QR-010, QR-011 | RK-002, RK-003 | G4, G5, G6 |

## 15. Leakage Classification

All features must receive a leakage level before modeling.

| Leakage Level | Definition | Default Predictor Policy | Examples or Notes |
| --- | --- | --- | --- |
| Low | Feature is available at prediction time, commit-scoped, not label-derived, and not an identifier. | Eligible after validation. | Final examples are `Pending Decision`. |
| Medium | Feature appears valid but depends on temporal aggregation, fitted preprocessing, or source timing that must be checked. | Candidate until validation passes. | Many code/process/text candidates begin here. |
| High | Feature may encode identity, timing, issue linkage, or strong proxy behavior. | Not eligible until explicitly cleared. | Commit timestamps and traceability identifiers are high risk by default. |
| Critical | Feature is target-derived, proxy-target, future-derived, or part of label construction. | Forbidden by default. | `bug_confidence`, `msg_has_bug_kw`, `has_bug_keyword`, `label_confidence`, future timestamps, issue labels, issue identifiers, future-derived information. |

## 16. Feature Validation Rules

Feature validation is mandatory before a feature can be approved.

| Validation Area | Rule | Related Controls |
| --- | --- | --- |
| Commit scope | Each feature value must map to exactly one commit-level unit of analysis. | DD-002, QR-003, G3 |
| Modality assignment | Predictor candidates must be assigned to Code, Process, or Text. | DD-004, QR-005, G3 |
| Source artifact | Each feature must identify an approved source artifact or source type. | QR-001, QR-002, G1 |
| Timing availability | Each feature must be available at commit prediction time. | DD-005, QR-007, G5 |
| Predictor eligibility | Each feature must be approved, not eligible, or forbidden before modeling. | DD-005, DD-006, QR-009, G4 |
| Missing values | Each feature must have a missing-value policy before training. | QR-005, G3 |
| Train-only fitting | Any vocabulary, scaler, imputer, encoder, threshold, or learned transformation must be fitted only on training data. | DD-018, QR-010, G6 |
| Leakage audit | Label-derived, proxy-target, identifier-derived, and future-derived features must be detected and controlled. | QR-006, QR-007, QR-008, G4, G5 |
| Feature manifest | Approved features must appear in the feature inventory and training feature list. | QR-005, QR-023, G3, G16 |
| Ablation readiness | Critical, suspicious, and top-ranked features must be ablation-ready. | DD-011, QR-016, G10 |

## 17. Feature Quality Controls

| Quality Control | Required Evidence | Blocking Status |
| --- | --- | --- |
| Feature inventory | Feature registry with modality, source, derivation, timing, and predictor eligibility. | Blocking before modeling |
| Semantic leakage audit | Report covering target-derived and proxy-target variables. | Blocking before modeling |
| Temporal leakage audit | Report proving prediction-time availability and chronological integrity. | Blocking before evaluation |
| Train-only preprocessing manifest | Evidence that fitted transformations use training data only. | Blocking before experiments |
| Identifier exclusion check | Training feature list excluding traceability-only variables. | Blocking before modeling |
| Suspicious feature ablation | Ablation report for critical or suspicious features. | Blocking before final claims |
| Modality ablation | Ablation report for Code, Process, and Text modalities. | Blocking before multimodal claims |
| Result plausibility review | Review triggered by perfect or near-perfect performance. | Blocking when triggered |
| Explainability validity review | Evidence that explanations are not explaining leakage. | Blocking before scientific explanation claims |

## 18. Feature Lineage

Each feature must be traceable from source artifact to experiment use.

| Lineage Element | Required Link |
| --- | --- |
| Feature ID | Stable registry identifier. |
| Source artifact | `data/raw/`, `data/interim/`, `data/processed/`, or approved source type. |
| Dataset version | MQtBase dataset version where the feature appears. |
| Commit key | Commit-level traceability key. |
| Derivation rule | Implementation-independent rule or `Pending Decision`. |
| Leakage classification | Low, Medium, High, or Critical. |
| Predictor eligibility | Eligible, Not Eligible, Forbidden, or Pending Decision. |
| Validation evidence | Feature validation report and relevant quality gate outcomes. |
| Experiment use | Training feature list, run manifest, and ablation status when applicable. |

## 19. Feature Versioning

Feature versioning must preserve reproducibility across dataset and experiment versions.

| Versioning Rule | Specification |
| --- | --- |
| Feature registry version | Required for every approved feature inventory. |
| Dataset version linkage | Each feature must identify the dataset version where it is introduced. |
| Derivation rule changes | Any change to source, timing, derivation, or leakage status requires a new feature registry version. |
| Deprecation | Deprecated features remain documented for reproducibility. |
| Reclassification | Any change from Forbidden or Quarantined to Approved requires governance evidence and quality gate review. |
| Experiment traceability | Run manifests must reference the exact feature registry version used. |

The final feature version naming convention is `Pending Decision`.

## 20. Feature States

| State | Definition | Predictor Use |
| --- | --- | --- |
| Candidate | Proposed feature awaiting complete lineage, leakage classification, validation, or approval. | Not allowed in final modeling claims. |
| Approved | Feature has passed required governance, validation, leakage, and preprocessing controls for a specific dataset version. | Allowed according to its approved scope. |
| Quarantined | Feature has unresolved leakage, timing, missingness, or validation concerns. | Not allowed. |
| Deprecated | Feature was previously tracked but is retired or superseded. | Not allowed in new experiments unless explicitly justified for reproducibility. |
| Forbidden | Feature is target-derived, proxy-target, future-derived, or otherwise prohibited. | Never allowed unless formally reclassified by governance. |

## 21. Feature Registry Template

The following template must be used for future feature registry entries.

| Feature ID | Feature Name | Category | Modality | Description | Data Type | Source Artifact | Derivation Rule | Available at Prediction Time | Leakage Level | Predictor Eligibility | Missing Value Policy | Validation Rule | Version Introduced | Current Status | Related Design Decision | Related Quality Requirement | Related Risk | Related Quality Gate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Pending Decision | Pending Decision | Pending Decision | Pending Decision | Pending Decision | Pending Decision | Pending Decision | Pending Decision | Pending Decision | Pending Decision | Pending Decision | Pending Decision | Pending Decision | Pending Decision | Candidate | Pending Decision | Pending Decision | Pending Decision | Pending Decision |

## 22. Pending Decisions

The following feature-governance items remain unresolved.

| Item | Status |
| --- | --- |
| Final code feature list | Pending Decision |
| Final process feature list | Pending Decision |
| Final text feature list | Pending Decision |
| Final feature counts | Pending Decision |
| Final feature data types | Pending Decision |
| Final derivation rules | Pending Decision |
| Final text preprocessing policy | Pending Decision |
| Final embedding use, model, and dimensionality | Pending Decision |
| Final missing-value policy per feature | Pending Decision |
| Final modality missingness policy | Pending Decision |
| Final feature registry file format | Pending Decision |
| Final feature version naming convention | Pending Decision |
| Final leakage thresholds for proxy-target detection | Pending Decision |
| Final criteria for reclassifying forbidden variables | Pending Decision |
| Final source artifact paths for generated feature inventories | Pending Decision |
| Final approval authority for feature governance | Pending Decision |

