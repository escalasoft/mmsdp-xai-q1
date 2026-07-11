# MQtBase Dataset Specification

Version: 1.0  
Status: Draft governance specification  
Primary source of truth: `docs/PROJECT_CONTEXT.md` Version 2.0

## 1. Purpose

This document defines the implementation-independent lifecycle specification for the MQtBase dataset used by the clean MMSDP-XAI project.

The specification defines how dataset sources, versions, schemas, lineage, partitions, validation rules, leakage controls, traceability, governance, and output artifacts must be organized before dataset construction and experimentation.

This document does not define machine learning algorithms, final dataset statistics, final feature counts, repository date ranges, or experimental results. Any unresolved item is explicitly marked as `Pending Decision`.

## 2. Source Authority

`docs/PROJECT_CONTEXT.md` Version 2.0 is the primary Single Source of Truth for this specification.

The following documents are used only for consistency with approved project governance:

| Document | Use in This Specification |
| --- | --- |
| `docs/SYSTEM_ARCHITECTURE.md` | Architectural consistency, repository paths, lifecycle layers, reproducibility expectations. |
| `docs/DESIGN_DECISIONS.md` | Approved dataset and evaluation decisions. |
| `docs/QUALITY_REQUIREMENTS.md` | Dataset, leakage, traceability, reproducibility, and quality requirements. |
| `docs/RISK_REGISTER.md` | Dataset-related risks and controls. |
| `docs/EXPERIMENT_QUALITY_GATES.md` | Required quality gates before accepting experimental results. |

Reference documents under `reference/` remain authoritative only through the synthesis recorded in `docs/PROJECT_CONTEXT.md` Version 2.0.

## 3. Dataset Identity

| Item | Specification |
| --- | --- |
| Dataset name | MQtBase |
| Source repository | QtBase |
| Project framework | MMSDP-XAI |
| Unit of analysis | Commit |
| Core modalities | Code, Process, Text |
| Primary validation strategy | Strict chronological 70 / 15 / 15 partitioning |
| Dataset statistics | Pending Decision |
| Final repository snapshot | Pending Decision |
| Final repository date range | Pending Decision |
| Public release location | Pending Decision |

The source documents contain naming inconsistencies between `MQtBase` and `MQtDbase`. For the clean project, `MQtBase` is the canonical dataset name according to `docs/PROJECT_CONTEXT.md` Version 2.0.

## 4. Dataset Lifecycle Overview

The MQtBase lifecycle must preserve raw data immutability, commit-level traceability, leakage prevention, chronological validation, and reproducibility.

| Stage | Name | Purpose | Primary Paths | Status |
| --- | --- | --- | --- | --- |
| L0 | Governance specification | Define dataset rules before implementation. | `docs/` | This document |
| L1 | Source identification | Identify QtBase source repository, snapshot, and extraction boundaries. | `data/external/`, `outputs/reports/` | Pending Decision |
| L2 | Raw acquisition | Preserve immutable source artifacts and extraction manifests. | `data/raw/` | Pending Decision |
| L3 | Interim extraction | Convert source artifacts into commit-level, label, and modality-specific intermediate tables. | `data/interim/` | Pending Decision |
| L4 | Feature inventory | Document all candidate features by modality and leakage eligibility. | `outputs/reports/` | Pending Decision |
| L5 | Leakage audit | Remove or quarantine target-derived, proxy-target, and future-derived variables. | `outputs/reports/` | Pending Decision |
| L6 | Chronological partitioning | Assign commits to train, validation, and test partitions by time. | `data/processed/` | Pending Decision |
| L7 | Processed dataset release | Produce validated train, validation, test, metadata, and manifest artifacts. | `data/processed/`, `outputs/reports/` | Pending Decision |
| L8 | Experiment handoff | Provide only approved processed artifacts to modeling and evaluation components. | `data/processed/`, `configs/`, `outputs/` | Pending Decision |
| L9 | Dataset version governance | Freeze dataset versions and preserve lineage for reproducibility. | `docs/`, `outputs/reports/` | Pending Decision |

## 5. Data Sources

| Source | Role | Required Documentation | Governance Status |
| --- | --- | --- | --- |
| QtBase repository | Primary software project source for commit-level data. | Repository URL, snapshot identifier, extraction date, date range, commit count, license status. | Pending Decision |
| Issue or bug tracking source | Candidate source for defect labels and commit-to-issue linkage. | Source system, linking rules, label definitions, timestamp fields, ambiguity handling. | Pending Decision |
| Commit metadata | Candidate source for process and text modalities. | Commit hash, author information policy, commit timestamp, message handling policy. | Pending Decision |
| Code changes | Candidate source for code modality and process attributes. | File-level extraction scope, language/file filters, generated-file policy, binary-file policy. | Pending Decision |
| External auxiliary data | Optional supporting source if required by the approved dataset pipeline. | Purpose, provenance, license, version, linkage rules. | Pending Decision |

No additional data source may be introduced without updating dataset lineage, provenance documentation, leakage analysis, and release governance.

## 6. Repository Snapshot

The dataset must be tied to a reproducible QtBase repository snapshot.

| Attribute | Required Value |
| --- | --- |
| Source repository name | QtBase |
| Source repository URL | Pending Decision |
| Snapshot identifier | Pending Decision |
| Snapshot type | Pending Decision |
| Extraction timestamp | Pending Decision |
| Commit date range | Pending Decision |
| Included branches | Pending Decision |
| Excluded branches | Pending Decision |
| Submodule handling | Pending Decision |
| License and redistribution status | Pending Decision |

The snapshot identifier must be recorded in all raw, interim, processed, and report-level metadata artifacts.

## 7. Unit of Analysis

The unit of analysis is a commit.

Each dataset row in the canonical processed dataset must represent exactly one commit. File-level, method-level, message-level, or issue-level artifacts may be used during extraction only when they are aggregated or linked back to the commit-level unit of analysis.

Identifiers such as commit hashes and issue identifiers are preserved for traceability and partitioning, but they are not predictors unless explicitly approved by leakage governance. The default status of identifiers as model predictors is prohibited.

## 8. Dataset Versions

Every dataset release must have a unique dataset version identifier.

| Version Element | Requirement |
| --- | --- |
| Dataset version format | Pending Decision |
| Version owner | Pending Decision |
| Version approval authority | Pending Decision |
| Immutable raw snapshot association | Required |
| Processed artifact checksum | Required |
| Configuration reference | Required |
| Quality gate status | Required |
| Release notes | Required |
| Compatibility notes | Required |

Dataset versions must distinguish raw source snapshots, interim extraction versions, and processed modeling-ready versions.

## 9. Folder Organization

The dataset lifecycle must use the existing repository structure.

| Path | Purpose | Mutability |
| --- | --- | --- |
| `data/raw/` | Immutable raw source artifacts and raw acquisition manifests. | Immutable after acquisition |
| `data/interim/` | Intermediate extracted tables, linked records, and audit inputs. | Regenerable |
| `data/processed/` | Validated train, validation, test, metadata, and modeling-ready artifacts. | Versioned and controlled |
| `data/external/` | External auxiliary sources if approved. | Versioned and controlled |
| `configs/` | Dataset, extraction, preprocessing, and experiment configuration files. | Versioned |
| `outputs/reports/` | Dataset reports, leakage audits, validation reports, and release notes. | Versioned |
| `outputs/metrics/` | Dataset quality metrics and quality gate outputs. | Versioned |
| `docs/` | Governance and specification documents. | Versioned |

No dataset artifact should be written outside these repository paths unless a future governance decision defines an external storage policy.

## 10. Dataset Lineage

Every processed dataset artifact must be traceable back to source artifacts and transformation decisions.

| Lineage Level | Required Traceability |
| --- | --- |
| Source repository | QtBase repository identity and snapshot identifier. |
| Raw acquisition | Acquisition configuration, timestamp, operator or automation identity, and checksum policy. |
| Commit extraction | Commit hash, commit timestamp, parent relationship policy, and extraction version. |
| Label construction | Label source, label rule identifier, linked issue or evidence record, and ambiguity status. |
| Feature construction | Feature name, modality, source artifact, derivation rule, and leakage status. |
| Partitioning | Chronological ordering attribute, split assignment, and split policy version. |
| Validation | Quality gate evidence, validation report, and unresolved exception log. |
| Release | Dataset version, artifact checksums, manifest, and approval status. |

Lineage records are mandatory for reproducibility and for thesis-paper-code consistency.

## 11. Commit Schema

The final commit-level schema is `Pending Decision`. At minimum, the processed dataset must support the following logical fields or equivalent metadata.

| Field | Purpose | Predictor Eligibility | Status |
| --- | --- | --- | --- |
| `commit_id` | Stable internal commit-level row identifier. | Prohibited by default | Pending Decision |
| `commit_hash` | Traceability to QtBase source commit. | Prohibited | Required |
| `parent_commit_hashes` | Reconstruct commit history and temporal lineage. | Prohibited by default | Pending Decision |
| `commit_timestamp` | Chronological partitioning and temporal validation. | Prohibited unless explicitly justified | Required |
| `commit_timezone` | Interpret timestamp consistently. | Prohibited | Pending Decision |
| `author_identifier` | Process metadata or traceability, depending on approved policy. | Pending Decision | Pending Decision |
| `committer_identifier` | Process metadata or traceability, depending on approved policy. | Pending Decision | Pending Decision |
| `commit_message` | Source for text modality. | Allowed only through approved text features | Pending Decision |
| `changed_file_count` | Candidate process/code-change descriptor. | Pending leakage audit | Pending Decision |
| `lines_added` | Candidate process/code-change descriptor. | Pending leakage audit | Pending Decision |
| `lines_deleted` | Candidate process/code-change descriptor. | Pending leakage audit | Pending Decision |
| `files_changed` | Candidate source for code/process modalities. | Pending leakage audit | Pending Decision |
| `linked_issue_ids` | Labeling and traceability evidence. | Prohibited by default | Pending Decision |
| `dataset_version` | Dataset release traceability. | Prohibited | Required |
| `split` | Train, validation, or test assignment. | Prohibited | Required |

Fields used only for traceability, labeling, auditing, or partitioning must not be used as model predictors.

## 12. Label Schema

The label schema must define defect-prone versus clean commits at the commit level. The final labeling protocol is `Pending Decision`.

| Field | Purpose | Predictor Eligibility | Status |
| --- | --- | --- | --- |
| `target_label` | Binary defect-prone or clean label. | Target only | Required |
| `label_definition` | Human-readable definition of the label. | Prohibited | Pending Decision |
| `label_rule_id` | Identifier for the labeling rule applied. | Prohibited | Required |
| `label_source` | Source artifact or evidence used to assign the label. | Prohibited | Pending Decision |
| `linked_issue_id` | Issue or bug report associated with the commit, if applicable. | Prohibited by default | Pending Decision |
| `label_timestamp` | Time associated with the labeling evidence. | Prohibited | Pending Decision |
| `label_confidence` | Confidence or ambiguity status of the label, if used. | Prohibited by default | Pending Decision |
| `label_ambiguity_reason` | Explanation for uncertain or excluded labels. | Prohibited | Pending Decision |

Variables such as `bug_confidence`, `msg_has_bug_kw`, `has_bug_keyword`, and any other target-derived, proxy-target, or future-derived variables require explicit leakage review. Their default status is prohibited as predictors.

## 13. Feature Schema

The final feature inventory, feature names, feature counts, and exact transformations are `Pending Decision`.

Every candidate feature must be registered before modeling.

| Field | Purpose | Required |
| --- | --- | --- |
| `feature_name` | Stable feature identifier. | Yes |
| `modality` | One of Code, Process, or Text. | Yes |
| `description` | Human-readable feature description. | Yes |
| `source_artifact` | Commit, code change, metadata, message, or approved source. | Yes |
| `derivation_rule` | Implementation-independent transformation description. | Yes |
| `available_at_commit_time` | Whether the value is available at prediction time. | Yes |
| `leakage_status` | Approved, rejected, quarantined, or pending review. | Yes |
| `predictor_eligibility` | Whether the feature may be used in model training. | Yes |
| `missing_value_policy` | Feature-specific missing-value handling rule. | Yes |
| `fit_scope` | Whether fitting is train-only, not applicable, or Pending Decision. | Yes |
| `version_introduced` | Dataset version where the feature first appears. | Yes |

Feature engineering must preserve the approved modalities: code, process, and text.

## 14. Metadata Schema

Each dataset release must include machine-readable and human-readable metadata. The exact file format is `Pending Decision`.

| Metadata Field | Purpose | Status |
| --- | --- | --- |
| `dataset_name` | Identifies the dataset as MQtBase. | Required |
| `dataset_version` | Identifies the dataset release. | Required |
| `source_repository` | Identifies QtBase as the source repository. | Required |
| `source_snapshot_id` | Links to the repository snapshot. | Required |
| `extraction_config_id` | Links to extraction configuration. | Required |
| `preprocessing_config_id` | Links to preprocessing configuration. | Required |
| `split_policy_id` | Links to chronological split policy. | Required |
| `quality_gate_status` | Records pass, fail, or exception status for required gates. | Required |
| `random_seed` | Records seed when any stochastic process is approved. | Required when applicable |
| `environment_reference` | Links to reproducibility environment capture. | Required |
| `artifact_checksums` | Records checksums for released artifacts. | Required |
| `known_limitations` | Lists limitations and unresolved issues. | Required |

## 15. Temporal Attributes

Temporal integrity is mandatory because validation must be chronological.

| Attribute | Requirement |
| --- | --- |
| Primary ordering timestamp | Pending Decision |
| Timestamp timezone policy | Pending Decision |
| Commit timestamp source | Pending Decision |
| Issue timestamp handling | Pending Decision |
| Future-derived data exclusion | Required |
| Split ordering | Ascending chronological order |
| Partition proportions | 70 / 15 / 15 |
| Tie handling | Pending Decision |

No feature may use information that would not have been available at the prediction time of the commit.

## 16. Chronological Partitioning

The processed dataset must be partitioned into training, validation, and test sets using strict chronological order.

| Partition | Proportion | Purpose |
| --- | --- | --- |
| Training | 70% | Fit preprocessing, feature transformations, unimodal models, fusion models, and calibration inputs as permitted by the experiment design. |
| Validation | 15% | Model selection, calibration protocol support, and quality checks as approved by the experimental design. |
| Test | 15% | Final held-out evaluation only. |

Random cross-validation must not replace chronological validation. Any repeated evaluation strategy must preserve temporal validity.

The exact partition boundary timestamps and tie-breaking policy are `Pending Decision`.

## 17. Missing-Value Policy

The missing-value policy must be defined before model training.

| Dataset Layer | Policy |
| --- | --- |
| Raw | Preserve original missingness and source-level absence without imputation. |
| Interim | Represent missingness explicitly and retain reason codes where available. |
| Processed | Apply only approved missing-value handling rules. Any fitted imputation must be fitted only on training data. |
| Modality-level missingness | Pending Decision |
| Label missingness | Commits without valid labels must not enter supervised modeling datasets unless an approved rule allows it. |
| Metadata missingness | Missing required metadata blocks dataset release. |

Missing values must not be filled using validation or test distribution information.

## 18. Duplicate Policy

Duplicate handling must preserve commit-level identity and traceability.

| Duplicate Type | Policy |
| --- | --- |
| Duplicate `commit_hash` in a dataset split | Not allowed. |
| Same `commit_hash` across multiple splits | Not allowed. |
| Duplicate rows with identical commit identity | Not allowed. |
| Duplicate commit messages | Not sufficient by itself to define a duplicate. |
| Duplicate code changes | Pending Decision |
| Cherry-picks or equivalent commits | Pending Decision |
| Merge commits | Pending Decision |

Any duplicate-removal rule must be documented in lineage and validation reports.

## 19. Leakage-Prevention Rules

Leakage prevention is mandatory and blocking before final experimental results are accepted.

| Rule ID | Rule |
| --- | --- |
| LP-001 | Target labels must never appear as predictors. |
| LP-002 | Label-derived variables must not be used as predictors. |
| LP-003 | Proxy-target variables must be detected, documented, and excluded unless explicitly approved after audit. |
| LP-004 | Future-derived variables must be prohibited. |
| LP-005 | Identifiers are preserved only for traceability, linkage, auditing, and partitioning by default. |
| LP-006 | All preprocessing that learns parameters must be fitted only on the training partition. |
| LP-007 | Validation and test partitions must not influence feature selection, scaling, imputation, text vocabulary construction, calibration fitting, or model selection unless an approved protocol explicitly permits their role. |
| LP-008 | `bug_confidence`, `msg_has_bug_kw`, `has_bug_keyword`, and similar variables require explicit semantic leakage review. |
| LP-009 | Explainability outputs cannot be accepted until leakage and result-plausibility gates pass. |
| LP-010 | Perfect or near-perfect performance must reopen leakage, ablation, and plausibility gates. |

## 20. Dataset Validation Rules

Dataset validation must occur before artifacts are released to experiments.

| Validation Area | Mandatory Checks |
| --- | --- |
| Provenance | Source repository, snapshot, extraction configuration, and artifact checksums are recorded. |
| Schema | Required fields exist, types are valid, and controlled vocabularies are respected. |
| Unit of analysis | Each processed row represents exactly one commit. |
| Label integrity | Label rule, source, and ambiguity status are documented. |
| Temporal integrity | Partitioning follows chronological order and prohibits future-derived predictors. |
| Split integrity | No commit appears in more than one partition. |
| Feature inventory | Every candidate predictor has modality, source, derivation, leakage status, and eligibility. |
| Leakage audit | Semantic, temporal, and proxy-target leakage checks are complete. |
| Missing values | Required fields are complete and approved missing-value policies are applied. |
| Duplicates | Duplicate commit identities and split collisions are absent. |
| Reproducibility | Dataset manifest, configuration references, environment references, and checksums are present. |

## 21. Quality Controls

The dataset specification aligns with the following quality gates.

| Gate | Dataset Control |
| --- | --- |
| G1 Dataset provenance | Blocks release until source, snapshot, and lineage evidence exist. |
| G2 Label integrity | Blocks release until labeling rules and ambiguity handling are documented. |
| G3 Feature inventory | Blocks modeling until all candidate features are registered and classified. |
| G4 Semantic leakage audit | Blocks modeling until leakage-sensitive variables are reviewed. |
| G5 Temporal integrity | Blocks evaluation until chronological split integrity is verified. |
| G6 Train-only preprocessing | Blocks experiments until fit scope is documented and controlled. |
| G14 Result plausibility | Reopens leakage review for perfect or near-perfect metrics. |
| G16 Reproducibility | Blocks final acceptance until manifests and environment records exist. |
| G18 Thesis-paper-code consistency | Blocks final reporting when dataset claims diverge across artifacts. |
| G19 Release and confidentiality | Blocks public release until confidential and source-document exposure risks are reviewed. |

## 22. Traceability

Traceability must connect each dataset row, feature, label, partition assignment, validation result, and experiment input to documented evidence.

| Traceability Target | Required Link |
| --- | --- |
| Commit row | QtBase commit hash and dataset version. |
| Label | Label rule, source evidence, and ambiguity status. |
| Feature | Feature inventory entry, modality, source artifact, derivation rule, and leakage status. |
| Partition | Split policy, chronological ordering attribute, and split assignment. |
| Dataset artifact | Dataset version, configuration, checksums, and quality gate status. |
| Experiment input | Processed dataset version, split files, feature inventory, and leakage report. |
| Publication claim | Dataset version, validation evidence, and consistency with project governance documents. |

## 23. Output Artifacts

The following artifacts are required unless a future governance decision replaces them.

| Artifact | Purpose | Suggested Location | Status |
| --- | --- | --- | --- |
| Raw acquisition manifest | Records source snapshot, acquisition settings, and checksums. | `data/raw/` or `outputs/reports/` | Pending Decision |
| Source snapshot report | Documents QtBase snapshot and extraction boundaries. | `outputs/reports/` | Pending Decision |
| Commit table | Commit-level canonical records. | `data/interim/` and `data/processed/` | Pending Decision |
| Label documentation | Defines labeling rules, sources, ambiguity handling, and exclusions. | `outputs/reports/` | Pending Decision |
| Feature inventory | Lists candidate features by modality and leakage eligibility. | `outputs/reports/` | Pending Decision |
| Leakage audit report | Records semantic, temporal, and proxy-target leakage checks. | `outputs/reports/` | Pending Decision |
| Split manifest | Records train, validation, and test assignments. | `data/processed/` or `outputs/reports/` | Pending Decision |
| Dataset metadata file | Records dataset version, source, configuration, checksums, and quality status. | `data/processed/` | Pending Decision |
| Dataset validation report | Records validation checks and gate outcomes. | `outputs/reports/` | Pending Decision |
| Release notes | Documents dataset version changes and limitations. | `outputs/reports/` | Pending Decision |

Final artifact file formats are `Pending Decision`.

## 24. Governance

Dataset governance must preserve the approved clean-project scope.

| Governance Topic | Rule |
| --- | --- |
| Primary authority | `docs/PROJECT_CONTEXT.md` Version 2.0 governs scientific scope and frozen decisions. |
| Dataset name | Use MQtBase as the canonical dataset name. |
| Source project | Use QtBase as the primary source repository. |
| Scope control | Do not add datasets, modalities, labels, or validation protocols without documented decision updates. |
| Raw data | Raw data are immutable after acquisition. |
| Preprocessing | Fitted preprocessing must be fitted only on training data. |
| Release control | Public release must pass confidentiality and reproducibility checks. |
| Documentation | Dataset claims must be evidence-bounded and traceable. |
| Journal controls | Journal-specific formatting rules must not redefine dataset science. |

## 25. Versioning

Dataset versioning must distinguish source snapshots, transformations, and processed releases.

| Versioned Object | Requirement |
| --- | --- |
| Source snapshot | Must have a stable snapshot identifier. |
| Raw dataset | Must reference the source snapshot and acquisition manifest. |
| Interim dataset | Must reference raw dataset version and extraction configuration. |
| Processed dataset | Must reference interim dataset version, feature inventory, leakage report, split manifest, and validation report. |
| Dataset documentation | Must reference the dataset version it describes. |
| Experiment configuration | Must reference the processed dataset version used. |

The final version naming convention is `Pending Decision`.

## 26. Pending Decisions

The following items are not finalized in the project governance documents and must remain unresolved until formally decided.

| Item | Status |
| --- | --- |
| QtBase repository URL | Pending Decision |
| Source snapshot identifier | Pending Decision |
| Repository extraction date | Pending Decision |
| Repository date range | Pending Decision |
| Final dataset statistics | Pending Decision |
| Final feature inventory and feature counts | Pending Decision |
| Final label construction protocol | Pending Decision |
| Commit-to-issue linking algorithm | Pending Decision |
| Merge commit handling | Pending Decision |
| Cherry-pick handling | Pending Decision |
| Timestamp timezone policy | Pending Decision |
| Chronological split boundary timestamps | Pending Decision |
| Missing-value handling by feature | Pending Decision |
| Modality-level missingness policy | Pending Decision |
| Dataset artifact file formats | Pending Decision |
| Dataset version naming convention | Pending Decision |
| Dataset public release location | Pending Decision |
| License and redistribution policy | Pending Decision |

