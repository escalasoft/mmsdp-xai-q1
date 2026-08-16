# Controlled JIT-Defects4J Multimodal Fusion and Ablation Audit

## 1. Sprint objective

Determine on frozen TRAIN/VALIDATION data whether CODE, PROCESS, and TEXT probability-level fusion improves defect discrimination, with explicit PROCESS ablation. This is not final evaluation.

## 2. Branch verification

Verified branch: `sprint-10/jit-defects4j-controlled-multimodal-fusion`.

## 3. Scientific identities and frozen artifacts

- Canonical dataset: `e509995da233c932cafce531c13ad2cd617a0d8abbe8d81ccaa373b8f29fa519`
- Frozen boundary: `d1b4448e22a1dba4292b9cf8969ba77db0cf9a10ef66dfddf98642cb5dc078a7`
- Adapter: `9c22de3d15d09132af1920eec0fd02e3ea9f879a70ecbd90bc5adc7913b63d2c`
- Experiment configuration: `850a2479c5ba4c9ccb7db0f40ade325022c2bbef9d24faaba60a0a57a3a60f58`
- Result: `84d08dae0dca0158b786d70c90f05e597a3a22147c5aea82ae0500aca9efe4cd`

## 4. Dataset/split verification

TRAIN: 19,114 (1,912 positive; prevalence 0.1000313906). VALIDATION: 4,086 (260 positive; prevalence 0.0636319139). Exact `(project, commit_hash)` alignment and zero TRAIN/VALIDATION overlap passed.

## 5. TEST seal verification

TEST remained sealed. Only frozen metadata counts (4,119 total; 160 positive; 3,959 nominal negative) were recorded. No TEST predictor matrix, prediction, metric, selection, calibration, thresholding, or explanation was requested.

## 6. Frozen unimodal baselines

The selected Sprint 10.8.2.25 candidates were reproduced exactly within 1e-12: CODE RF, PROCESS RF (weak standalone baseline), and TEXT LR.

## 7. Fusion methodology

A single predeclared deterministic late-fusion strategy computes the equal-weight arithmetic mean of positive-class probabilities. Each frozen base learner is fitted on TRAIN only and predicts VALIDATION. No weights or meta-model are learned, no calibration is performed, and VALIDATION does not enter fitting. This simple strategy reuses the repository `WeightedAverageFusion` contract, preserves modality boundaries, avoids TEXT densification, and isolates ablation effects without a stacking leakage surface.

## 8. Stacking and anti-leakage protocol

Stacking was not used. Consequently no meta-training features exist. The learned components are only the frozen base models fitted on TRAIN; fusion is a fixed deterministic formula.

## 9. Predeclared configurations and selection

Exactly four candidates were declared before execution: CODE+TEXT, CODE+PROCESS, TEXT+PROCESS, and CODE+PROCESS+TEXT, all equal-weight. Ranking is descending VALIDATION ROC-AUC, then AP, then fewer modalities, then stable ID. An absolute ROC-AUC tolerance of 0.005 describes near ties; it is not a significance test.

## 10. Results by configuration

| Configuration | Modalities | Fusion | ROC-AUC | PR-AUC/AP | Δ ROC-AUC | Δ PR-AUC | Status |
|---|---|---|---:|---:|---:|---:|---|
| CODE | CODE | none-frozen-unimodal | 0.691365 | 0.161135 | — | — | frozen-baseline-reproduced |
| PROCESS | PROCESS | none-frozen-unimodal | 0.479598 | 0.061482 | — | — | frozen-baseline-reproduced |
| TEXT | TEXT | none-frozen-unimodal | 0.697600 | 0.140258 | — | — | frozen-baseline-reproduced |
| CODE+TEXT | CODE, TEXT | fixed-equal-weight-probability-average | 0.746033 | 0.193084 | — | — | development-candidate |
| CODE+PROCESS | CODE, PROCESS | fixed-equal-weight-probability-average | 0.668044 | 0.156715 | -0.023321 | -0.004420 | development-candidate |
| TEXT+PROCESS | TEXT, PROCESS | fixed-equal-weight-probability-average | 0.674090 | 0.129186 | -0.023510 | -0.011071 | development-candidate |
| CODE+PROCESS+TEXT | CODE, PROCESS, TEXT | fixed-equal-weight-probability-average | 0.731094 | 0.185728 | -0.014939 | -0.007356 | development-candidate |

Threshold-dependent precision, recall, F1, MCC, and confusion matrices are retained in `audit.json` at the fixed 0.5 threshold and are descriptive only.

## 11. Ablation and PROCESS contribution

- CODE+PROCESS_minus_CODE: Δ ROC-AUC -0.023321; Δ AP -0.004420.
- TEXT+PROCESS_minus_TEXT: Δ ROC-AUC -0.023510; Δ AP -0.011071.
- CODE+PROCESS+TEXT_minus_CODE+TEXT: Δ ROC-AUC -0.014939; Δ AP -0.007356.

**PROCESS CONTRIBUTION: NOT SUPPORTED.** This decision is restricted to this dataset, frozen ancestor-only representation, temporal split, and equal-weight late-fusion candidate set. PROCESS is neither silently removed nor declared intrinsically useless.

## 12. Best development candidate and unimodal comparison

Selected multimodal candidate: `code-text-equal`. Relative to `jit-10.8.2.25-text-lr-2`, Δ ROC-AUC is +0.048433 and Δ AP is +0.052826. ROC-AUC and AP are both reported because class imbalance makes AP a major criterion; any disagreement is treated as a trade-off rather than hidden.

## 13. Reproducibility verification

Two independent complete executions produced identical candidate specifications, metrics, ranking, selected candidate, PROCESS decision, and scientific payload. Estimator serialization was not performed, so byte-identical model files are not claimed.

## 14. Temporal integrity and leakage audit

Frozen temporal membership, targets, ancestor-only PROCESS provenance, TRAIN-fitted TEXT state, TRAIN-only dense scaling, identity alignment, and the fail-closed TEST boundary passed. Natural prevalence was preserved.

## 15. Files created/modified

- `configs/experiments/jit_defects4j_controlled_multimodal_fusion_1.0.0.json`
- `src/experimentation/jit_defects4j_controlled_multimodal_fusion.py`
- `scripts/run_jit_defects4j_controlled_multimodal_fusion.py`
- `tests/experimentation/test_jit_defects4j_controlled_multimodal_fusion.py`
- `audits/jit-defects4j-controlled-multimodal-fusion/1.0.0/audit.json`
- `audits/jit-defects4j-controlled-multimodal-fusion/1.0.0/REPORT.md`

## 16. Tests and quality checks

- python_compilation: pass
- focused_pytest: pass (6 passed)
- complete_pytest: pass (1328 passed, 1 skipped)
- ruff_modified_files: pass
- git_diff_check: pass

## 17. Prohibited actions

No TEST predictor access/prediction/metric/selection, TRAIN+VALIDATION refit, threshold optimization, resampling, relabeling, membership or split modification, calibration, XAI, broad tuning, commit, push, merge, branch deletion, or PR creation occurred.

## 18. Limitations

- VALIDATION evidence is development-only and is not a final generalization claim.
- Only fixed equal-weight probability fusion was evaluated; weights were not learned or tuned.
- The descriptive 0.5-threshold metrics did not drive selection.
- No statistical significance or uncertainty interval is claimed.
- Probabilities are uncalibrated.

## 19. Scientific interpretation

Scientific decision: **GO WITH LIMITATIONS**. Performance alone does not establish validity; the decision also reflects seal, alignment, leakage, and reproducibility checks. PROCESS should proceed according to its explicit ablation result, not its weak standalone score.

## 20. Sprint 10.8.2.27 recommendation

Keep TEST sealed. Carry the selected candidate plus any ROC/AP near-tied simpler candidate into a predeclared TRAIN/VALIDATION robustness analysis. Retain PROCESS only if its ablation effect is practically supported; otherwise keep it as a weak/optional ablation modality. Resolve robustness uncertainty before freezing architecture or beginning a separately controlled calibration/XAI sprint.
