# MMSDP-XAI Scientific Dataset Specification

Version: 2.0
Status: Contract defined; dataset reconstruction and empirical evidence pending
Machine-readable template: `configs/scientific_dataset.json`

## 1. Purpose and scope

This is the canonical, project-independent scientific dataset specification for MMSDP-XAI. It defines contracts that every dataset must satisfy before modeling. It does not reconstruct Qt, approve an actual feature inventory, report results, or establish causality. Qt is the intended first implementation, not part of the generic contract.

## 2. Relationship to MMSDP-XAI

The contract supplies a reproducible commit-level handoff to the existing preparation, modeling, calibration, explanation, counterfactual, and experiment layers. It preserves the architectural decisions that the unit is a commit, code/process/text are core modalities, ordering is chronological, learned preprocessing is train-only, and identifiers, timestamps, partitions, target evidence, and provenance do not enter model fitting.

## 3. Observation unit

One observation is one repository commit. Each row has one stable non-empty unique identifier, one authoritative non-missing commit timestamp, and one binary software-defect target. File-, issue-, method-, or release-level artifacts may contribute only through documented commit-level linkage or aggregation.

## 4. Dataset identity and versioning

Scientific identity comprises dataset, dataset version, schema version, builder version, source repository name and URL, immutable source revision, observation unit `commit`, and deterministic metadata. Required names and versions are non-empty. A release version changes whenever its source revision, schema, construction policy, feature contract, or other scientifically meaningful input changes.

Runtime creation timestamps, usernames, local paths, machine names, object or memory identifiers, and Python hash values are excluded. A deterministic version identifies scientific content; operational timestamps may appear only in a separate runtime log and never affect identity or digest.

## 5. Identifier contract

The generic identifier field is `commit_hash`. It has role `identifier`, is required, unique, stable, and non-empty, and is never a predictor. A project adapter may map an equivalent source key to this logical field without changing its role.

## 6. Timestamp contract

The generic authoritative field is `commit_timestamp`. Its timezone interpretation must be explicit; the template normalizes to UTC while retaining source-offset provenance. Observations are ordered chronologically ascending. Missing timestamps are forbidden. Equal timestamps are allowed only with deterministic secondary ordering by observation identifier. Exact timestamps are ordering metadata, not predictors.

## 7. Binary target contract

The generic field is `is_defect_prone`, with `1` meaning defect-prone commit and `0` meaning non-defect-prone commit. The concrete labeling protocol must document sources, linking rules, cutoff times, ambiguity and exclusion handling, and audit evidence. Defect-inducing and bug-fixing commits must not be conflated. Keyword presence does not define the target, issue linking is not itself defect causality, and no causal interpretation is claimed.

## 8. Target-construction independence

Target derivation is a separate stage from feature construction. Issue links, label confidence, heuristic keywords, or other evidence used to assign or audit a label remain target provenance and never automatically become predictors. Candidate historical issue features require an independent operational definition and strict prior-time cutoff; reuse is not justified merely because the same source system supplied labels.

## 9. Multimodal organization

Every specification requires `code`, `process`, and `text`. Required and optional modality sets are unique and disjoint. The validated vocabulary can evolve through contract versions without changing the experiment pipeline; documented examples are `ast`, `cfg`, `call-graph`, and `image`. Undocumented arbitrary strings are rejected rather than silently accepted.

## 10. Feature provenance

Every candidate predictor has one immutable record containing its unique name, modality, source artifact and ordered source fields, temporal scope and availability, derivation, target/issue/future/post-event/full-dataset usage flags, leakage risk, disposition, scenario flags, rationale, and deterministic metadata. Raw identifier, timestamp, target, partition, and provenance fields are represented by their own roles, not disguised as model features.

## 11. Temporal availability

The controlled scopes are `commit-current`, `history-before-commit`, `static-project-metadata`, `future-derived`, `post-event`, `label-derived`, and `unknown`. Commit-current data must exist when the commit is observed. Historical windows end strictly before the current commit. Future-derived, post-event, and label-derived candidates are prohibited. Unknown timing requires review and cannot be presumed safe.

## 12. Leakage policy

Each candidate receives `none`, `low`, `medium`, `high`, `prohibited`, or `review-required` risk and one disposition: `permitted`, `prohibited`, `review-required`, `metadata-only`, `identifier-only`, `target-only`, or `timestamp-only`.

Target use, future information, post-event information, and corresponding temporal scopes force prohibition. Full-dataset aggregates are prohibited for fitting; a metadata-only aggregate is acceptable only when never supplied to a model. Prohibited candidates are disabled in all scenarios. A leakage-controlled candidate must also be explicitly enabled in the complete scenario. Validation reports policy violations without repairing them.

Text features are assessed by source-text availability, preprocessing fit scope, intentionally engineered target-linking tokens, and whether vocabularies or embeddings used future/test observations. Embeddings are not automatically leakage-free.

## 13. Complete-feature scenario

The complete scenario contains only candidate model features whose provenance explicitly sets complete-scenario inclusion. It is not “all columns” and never includes prohibited, metadata-only, identifier-only, target-only, or timestamp-only fields. Review-required features may appear only as declared sensitivity candidates and remain subject to implementation evidence.

## 14. Leakage-controlled scenario

The leakage-controlled scenario is the conservative primary scientific input: only explicitly enabled permitted features. It excludes prohibited and review-required candidates, identifiers, timestamps, targets, partitions, raw provenance, future/test-fitted transformations, and target-linking evidence.

## 15. Prohibited information

Prohibited information includes label-derived and proxy-target variables; engineered bug/fix keyword or issue-link indicators used in labeling; future bug/fix links; post-release defect outcomes; target probabilities or confidence; exact identifiers, timestamps and partitions as predictors; and transformations fitted over the full dataset. The canonical pattern policy covers normalized variants including `bug_confidence`, `msg_has_bug_kw`, `has_bug_keyword`, `contains_bug_keyword`, `contains_fix_keyword`, `issue_link_indicator`, `bug_link_count`, `future_bug_count`, `future_fix_count`, `post_release_defect_count`, `label_confidence`, `target_probability`, `is_bug`, and `is_buggy`.

## 16. Review-required information

Unknown timing, medium/high ambiguity, issue-related histories, and text transformations with unresolved fit scope require review. An issue-related historical process feature can be permitted or review-required when it uses only information strictly before the commit, does not use the current target or future bug links, and has an independent justification in the feature dictionary. Issue-related does not mean automatically invalid.

## 17. Dataset manifest

Each realized release must contain a deterministic manifest with scientific identity and digest; immutable source revision; builder/config/schema/policy versions; observation, target, timestamp, modality and feature dictionaries; source checksums; deterministic row ordering and counts; label and linkage policy identifiers; exclusion rules; split policy; train-only preprocessing declarations; artifact names, sizes and SHA-256 checksums; validation results; and known limitations. Keys and collections have deterministic order. Runtime logs are separate.

## 18. Dataset validation gates

Before experimental use, evidence must show: aligned identifier/timestamp/target fields; code/process/text presence; unique modalities and feature names; sufficient feature inventory; complete rationales and provenance; valid temporal availability; no enabled prohibited or role-like fields; review-required exclusion from leakage control; target-construction independence; no future/test preprocessing fit; chronological ordering with deterministic ties; and a complete manifest version. Warnings identify unknown timing, medium risk, review-required status, unclassified artifacts, or incomplete provenance. Gates do not silently repair input.

## 19. Scientific digest

Canonical JSON uses UTF-8, sorted keys, separators `,` and `:`, Unicode preservation, and rejection of NaN/infinity. SHA-256 of those bytes is the scientific digest. Runtime timestamps, local paths, users, machines, memory addresses, and language hash values are excluded. Identical contracts yield identical digests; a scientifically meaningful contract change changes it.

## 20. Extensibility to future repositories

Repository-specific builders instantiate this contract with a source identity, immutable revision, labeling protocol, and provenance-complete features. New modalities require a documented vocabulary/version change but no experiment-pipeline redesign. No Qt name, path, metric, feature list, or result is embedded in the generic contract.

## 21. Relationship to the article and thesis methodology

The thesis and revised article may cite this document as the pre-extraction method contract for observation identity, timing, target separation, multimodal provenance, scenarios, leakage gates, manifests, and versioning. They must separately report the realized dataset, implementation audit, and experiments. A stated rule is not evidence that a builder obeyed it or that a result is valid.

## 22. Relationship to former IEEE Access reviewer observations

The specification responds at the design level to concerns about suspicious variables such as `bug_confidence`, bug/fix keyword proxies, temporal validation, train/test preprocessing separation, feature traceability, calibration isolation, and reproducibility. The response has three evidence levels:

1. **Specification-level control:** contracts and blocking rules defined here.
2. **Future implementation evidence:** manifests, source/link audits, fitted-transform records, and executable validation from a reconstructed dataset.
3. **Future experimental evidence:** leakage-controlled comparisons, ablations, calibration evidence, uncertainty, and plausibility checks.

Only the first level is delivered by this sprint. Reviewer concerns are not fully resolved until their required implementation and experimental evidence exists.

## 23. Limitations

The contract cannot prove source correctness, label validity, issue-link quality, semantic absence of proxy leakage, repository representativeness, external validity, or causal relationships. Name patterns are screening controls, not substitutes for review. Determinism does not imply scientific validity. Concrete thresholds, sources, filters, label rules, features, and outcomes remain future implementation decisions.

## 24. Change-control policy

Changes use semantic versions and a documented rationale. Any change to observation, identity, target meaning, timestamp policy, modality vocabulary, feature provenance, leakage/scenario policy, manifest schema, or canonicalization is scientifically meaningful: update the contract/configuration, regenerate the digest, revalidate realized datasets, and invalidate dependent evidence where necessary. Editorial wording with no semantic effect may change a documentation revision without changing a frozen dataset digest.
