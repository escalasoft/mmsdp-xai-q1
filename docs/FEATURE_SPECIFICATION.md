# MMSDP-XAI Feature Specification

Version: 2.0
Status: Generic feature contract; concrete Qt inventory pending

## Purpose and scope

This document defines the mandatory dictionary and admissibility policy for every candidate model feature in any MMSDP-XAI dataset. It complements `docs/DATASET_SPECIFICATION.md`; it does not approve a Qt feature list, implement extraction, or report experiments.

## Mandatory feature dictionary

No column may reach model input without one provenance record. Each record must contain:

| Field | Required meaning |
| --- | --- |
| `name` | Unique stable feature name. |
| `modality` | Validated modality such as code, process, text, or a documented extension. |
| `mathematical/operational definition` | Reproducible formula, algorithm, units, and commit-level interpretation. |
| `source artifacts` | Versioned artifacts from which the value is derived. |
| `source fields` | Immutable ordered input-field sequence. |
| `temporal availability` | Commit-current, strictly before commit, static metadata, future, post-event, label-derived, or unknown, including cutoff. |
| `aggregation window` | Exact lower/upper bounds and tie policy, or not applicable. |
| `fit scope` | Not applicable or training observations only; never validation/test/full-dataset fitting. |
| `missing-value policy` | Detection, representation, and train-fitted handling. |
| `transformation policy` | Deterministic transformation and stored parameters/version. |
| `leakage risk` | None, low, medium, high, prohibited, or review-required. |
| `disposition` | Permitted, prohibited, review-required, metadata-only, identifier-only, target-only, or timestamp-only. |
| `complete-scenario inclusion` | Explicit Boolean. |
| `leakage-controlled inclusion` | Explicit Boolean. |
| `rationale` | Non-empty scientific and temporal justification. |

The executable record additionally exposes explicit Boolean flags for target, issue-link, future, post-event, and full-dataset use plus deterministic metadata. Provenance is attached to candidate features before scenario selection; exclusions remain documented rather than disappearing from the audit.

## Feature classes

### Admissible commit-current features

These use artifacts available when the commit is observed, such as current diff magnitude or commit-time source structure. “Current” must match the intended prediction moment. A commit message is available at commit time, but an engineered bug/fix linking indicator may still be target-derived and prohibited.

### Admissible history-before-commit features

These use a window ending strictly before the current commit. The dictionary states cutoff, tie handling, aggregation, and empty-history behavior. A historical process feature may be permitted or review-required when it is independent of the current target and future bug links. Issue-system origin alone neither validates nor invalidates it.

An enabled issue-derived historical feature must carry structured metadata with exactly these controls: `temporal_cutoff_policy="strictly-before-observation"`, `target_independence=true`, `current_target_excluded=true`, `future_links_excluded=true`, and a non-empty `linkage_policy_version`. It must also use `history-before-commit`, exclude target, future, and post-event information, and avoid full-dataset computation. A prose rationale remains mandatory documentation but is not admissibility evidence and is never parsed for scientific decisions.

### Target-linking evidence

Issue identifiers, SZZ/linking signals, keyword rules, confidence, and audit evidence used to construct the target are provenance, not predictors. Issue linking must not be interpreted automatically as defect causality, and bug-fixing commits must not be conflated with defect-inducing commits.

### Target-derived proxies

Direct target use, label confidence, target probability, or engineered variables reproducing the labeling rule are prohibited. This includes normalized variants of `bug_confidence`, `msg_has_bug_kw`, `has_bug_keyword`, keyword/link indicators, `is_bug`, and `is_buggy` when used as predictors.

### Future-derived features

Any value requiring observations after the current commit is prohibited, including future bug/fix counts and transformations whose fitted vocabulary, statistics, embedding, imputation, scaling, or selection used future/test observations.

### Post-event features

Outcomes observed after a release, defect report, inspection, or other prediction event are prohibited. Availability must be judged against the declared prediction time, not merely against when raw fields were eventually collected.

### Metadata-only fields

Identifiers, exact timestamps, target/linking provenance, partitions, dataset versions, checksums, source revisions, and audit fields remain available for ordering and traceability but are never model features. Metadata-only full-dataset summaries are acceptable only when never passed to fitting.

## Multimodal rules

Code, process, and text are required scientific modalities. Optional documented extensions include AST, CFG, call-graph, and image representations. Modality labels are controlled and versioned; arbitrary unknown strings are rejected. Required and optional sets are unique and disjoint.

Text embeddings are not assumed leakage-free. Review must establish source-text availability at commit time, training-only fit for vocabulary/representation transformations, absence or declared treatment of deliberately engineered target-linking tokens, and transform-only use on validation/test observations.

## Scenario policy

The complete scenario includes only candidates explicitly enabled for it; it is not a dump of all fields. It may include review-required candidates for declared sensitivity analysis, but never prohibited or non-feature roles. The leakage-controlled scenario is a subset containing explicitly enabled permitted candidates only. Review-required and prohibited candidates are excluded.

## Validation and evidence

Contract validation checks unique names, valid controlled values, complete rationale, scenario consistency, suspicious name patterns, temporal invariants, role-like predictors, minimum inventory size, and provenance warnings. It never repairs invalid records. Future builders must add extraction tests and manifests. Future experiments must separately show train-only transformations, chronological partitions, scenario comparisons, ablations, and evidence-bounded interpretations.

## Change control

Changing a definition, source, window, fit scope, missing/transformation policy, timing, risk, disposition, or scenario flag is scientifically meaningful. It requires a version update, a new scientific digest, revalidation, and reconsideration of dependent results. No concrete Qt feature inventory is approved in this sprint.
