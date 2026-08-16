# Controlled JIT-Defects4J TRAIN/VALIDATION Baseline Audit

## 1. Scientific decision

**GO.** The frozen identities and temporal partitions were preserved; all development decisions use TRAIN/VALIDATION only. These are development results, not final generalization claims.

## 2. Branch and repository state

Executed on `sprint-10/jit-defects4j-controlled-baselines`. No commit, push, merge, or PR was performed.

## 3. Scientific identities

- Canonical dataset: `e509995da233c932cafce531c13ad2cd617a0d8abbe8d81ccaa373b8f29fa519`
- Frozen boundary: `d1b4448e22a1dba4292b9cf8969ba77db0cf9a10ef66dfddf98642cb5dc078a7`
- Adapter configuration: `9c22de3d15d09132af1920eec0fd02e3ea9f879a70ecbd90bc5adc7913b63d2c`
- Results identity: `535459c72b0a91f9a82d19d1742d47feb5c7d8ab382d86756270336f7716268b`

## 4. Partitions and TEST seal

TRAIN: 19,114 observations, 1,912 positive, 17,202 nominal negative, prevalence 0.1000313906.
VALIDATION: 4,086 observations, 260 positive, 3,826 nominal negative, prevalence 0.0636319139.
TEST remained sealed. Only previously frozen metadata counts were verified; no TEST matrix, predictor, score, prediction, or predictive metric was requested.

## 5. Frozen modalities and candidate policy

CODE-STRUCTURAL has six exact Git raw-tree change-count features. PROCESS has four ancestor-only fields. TEXT is the frozen 5,000-dimensional TRAIN-fitted unigram TF-IDF CSR representation. Dense numeric scaling was fitted on TRAIN and applied transform-only to VALIDATION; TEXT remained sparse.

Two deterministic LR configurations (C=0.1, 1.0) and two deterministic RF configurations (unbounded depth/leaf=1; depth=12/leaf=5), all seed 0 and without class weighting, were compared. Selection sorts VALIDATION ROC-AUC, then VALIDATION average precision, then stable candidate ID. Fixed-threshold 0.5 diagnostics are descriptive only and never drive selection.

## 6. VALIDATION results and development ranking

| Modality | Model | Candidate | VALIDATION ROC-AUC | VALIDATION PR-AUC/AP | Status |
|---|---|---|---:|---:|---|
| CODE | LR | jit-10.8.2.25-code-lr-1 | 0.687016 | 0.155656 | candidate |
| CODE | LR | jit-10.8.2.25-code-lr-2 | 0.687018 | 0.155633 | candidate |
| CODE | RF | jit-10.8.2.25-code-rf-1 | 0.670244 | 0.155866 | candidate |
| CODE | RF | jit-10.8.2.25-code-rf-2 | 0.691365 | 0.161135 | selected |
| PROCESS | LR | jit-10.8.2.25-process-lr-1 | 0.450026 | 0.057104 | candidate |
| PROCESS | LR | jit-10.8.2.25-process-lr-2 | 0.450026 | 0.057104 | candidate |
| PROCESS | RF | jit-10.8.2.25-process-rf-1 | 0.476417 | 0.062622 | candidate |
| PROCESS | RF | jit-10.8.2.25-process-rf-2 | 0.479598 | 0.061482 | selected |
| TEXT | LR | jit-10.8.2.25-text-lr-1 | 0.692275 | 0.127026 | candidate |
| TEXT | LR | jit-10.8.2.25-text-lr-2 | 0.697600 | 0.140258 | selected |
| TEXT | RF | jit-10.8.2.25-text-rf-1 | 0.654051 | 0.117703 | candidate |
| TEXT | RF | jit-10.8.2.25-text-rf-2 | 0.691656 | 0.128072 | candidate |

- CODE: jit-10.8.2.25-code-rf-2 > jit-10.8.2.25-code-lr-2 > jit-10.8.2.25-code-lr-1 > jit-10.8.2.25-code-rf-1
- PROCESS: jit-10.8.2.25-process-rf-2 > jit-10.8.2.25-process-rf-1 > jit-10.8.2.25-process-lr-1 > jit-10.8.2.25-process-lr-2
- TEXT: jit-10.8.2.25-text-lr-2 > jit-10.8.2.25-text-lr-1 > jit-10.8.2.25-text-rf-2 > jit-10.8.2.25-text-rf-1

Selected for later controlled comparison: CODE=jit-10.8.2.25-code-rf-2; PROCESS=jit-10.8.2.25-process-rf-2; TEXT=jit-10.8.2.25-text-lr-2.

## 7. Leakage, temporal integrity, and reproducibility

Exact `(project, commit_hash)` alignment, zero TRAIN/VALIDATION overlap, preserved targets, ancestor-only PROCESS provenance, TRAIN-only TEXT fitting, and TRAIN-only preprocessing were verified. The development loader exposes only TRAIN and VALIDATION and rejects TEST fail-closed.

The complete workflow was run twice independently and the machine-readable result objects were identical. This establishes scientific/report reproducibility for the recorded runtime; byte-identical estimator serialization is not claimed because models are not persisted.

## 8. Actions not performed

No TEST predictive evaluation/selection/thresholding, TRAIN+VALIDATION refit, resampling, SMOTE, relabeling, membership change, calibration, fusion, stacking, XAI, SHAP, LIME, DiCE, pretrained download, semantic-code feature fabrication, commit, push, or PR creation was performed.

## 9. Limitations and recommendation

- VALIDATION evidence is not final generalization evidence.
- CODE-STRUCTURAL is not a semantic code representation.
- PROCESS is a small ancestor-only baseline.
- PROCESS did not show non-trivial VALIDATION discrimination; its selected label identifies only the highest-ranked attempted PROCESS candidate.
- TF-IDF is a lexical baseline, not the final MMSDP-XAI TEXT representation.
- Probabilities are uncalibrated.

Sprint 10.8.2.26 should run a controlled CODE+TEXT TRAIN/VALIDATION comparison using only the selected frozen candidates. PROCESS should appear only as a prespecified weak-baseline ablation, not as an assumed contributor. Preserve identities and natural prevalence, predeclare fusion candidates, and keep TEST sealed. Calibration and XAI should remain outside that comparison unless separately frozen.
