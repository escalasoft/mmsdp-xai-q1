# Sprint 10.8.2.43 — Controlled Prospective Advancement Decision

## Evidence-derived decision

**GO_WITH_LIMITATIONS**, mechanically selected by `RULE_4` (`ANY_MIXED`) from the accepted Sprint 42 vector under the frozen Sprint 39 mapper. This is not a desired-outcome selection.

| Criterion | Accepted state |
|---|---|
| `leakage_safety` | **MIXED** |
| `temporal_validity` | **PASS** |
| `reproducibility` | **MIXED** |
| `discrimination` | **MIXED** |
| `calibration` | **MIXED** |
| `practical_utility` | **MIXED** |
| `complexity_parsimony` | **MIXED** |
| `stability_across_origins` | **MIXED** |
| `absence_of_outcome_driven_tuning` | **PASS** |

The full evidence paths, SHA-256 identities, per-criterion provenance, rule traversal, precedence, and resulting outcome are in `advancement_decision.json`.

## Experimental validity versus performance sufficiency

Experimental/governance validity and predictive/scientific performance sufficiency are distinct. Discrimination, calibration, practical utility, temporal and cross-origin stability, comparative unimodal/bimodal/multimodal performance, uncertainty, and later statistical evaluation remain scientifically material.

Advancement-governance validity does not by itself establish predictive superiority or publication-level performance sufficiency.

## Documentary publication-performance safeguard

This safeguard is documentary only. It neither modifies the frozen mapper nor introduces a Sprint 43 advancement criterion. Later work must evaluate, where applicable: ROC-AUC, PR-AUC, Precision, Recall, F1, MCC, Brier Score, ECE / reliability, unimodal baselines, bimodal combinations, full multimodal model, ablation evidence, temporal robustness, cross-origin stability where available, uncertainty/statistical comparison.

1. Multimodality does not excuse poor predictive performance.
2. Explainability does not excuse poor predictive performance.
3. Calibration does not replace discrimination.
4. High discrimination does not excuse leakage or invalid evaluation.
5. A multimodal model must be compared against strong simpler baselines.
6. A scientifically valid experiment may still provide insufficient evidence for a publication claim.
7. No publication claim may exceed the empirical evidence.

## TEST and prohibited operations

TEST remained sealed. No fitting/refitting, calibration fitting/refitting, tuning, feature/modality/candidate selection, architecture modification, external acquisition, XAI, SHAP, LIME, counterfactual generation, or new experimental evaluation occurred. All counters in `execution_ledger.json` are zero.

## Historical integrity

`149` pre-Sprint-43 audit artifacts checked; missing `0`; unexpected `0`; hash mismatches `0`; historical tracked modifications `0`. Verdict: **PASS**.

## Quality gates

Status: `COMPLETED_WITH_REPOSITORY_FORMAT_FINDINGS`.

- `focused_pytest`: exit `0`; `16 passed in 9.40s`
- `sprint_39_42_regression`: exit `0`; `87 passed in 26.51s`
- `full_pytest`: exit `0`; `1509 passed, 1 skipped in 91.42s (0:01:31)`
- `ruff`: exit `0`; `All checks passed!`
- `python_compilation`: exit `0`; `command completed with exit code 0`
- `json_schema`: exit `0`; `valid`
- `determinism`: exit `0`; `deterministic`
- `historical_integrity`: exit `0`; `{'baseline_revision': '4fc4f888fa90ae9b3576640605a9c1081aec05fd', 'baseline_source': 'immutable Git blobs at accepted pre-Sprint-43 HEAD', 'protected_files_checked': 149, 'missing_files': [], 'unexpected_files': [], 'hash_mismatches': [], 'historical_tracked_modifications': [], 'historical_modification_count': 0, 'passed': True}`
- `artifact_manifest`: exit `0`; `8`
- `project_quality_gates`: exit `0`; `All checks passed!`
- `repository_format_diagnostic`: exit `2`; `make: *** [format-check] Error 1`
- `git_diff_check`: exit `0`; `command completed with exit code 0`
