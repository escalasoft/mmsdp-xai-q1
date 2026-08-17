# JIT-Defects4J Predeclared TRAIN/VALIDATION Robustness Audit

## 1. Scientific decision

**GO**. CODE+TEXT is assessed only as a development candidate under the tested TRAIN/VALIDATION conditions.

## 2. Branch verification

Verified exactly: `sprint-10/jit-defects4j-robustness-analysis`.

## 3. Frozen scientific identities

- dataset_identity: `e509995da233c932cafce531c13ad2cd617a0d8abbe8d81ccaa373b8f29fa519`
- canonical_manifest_sha256: `95b1a362f6756f641cc575cabf54a3a99e2846568d5ef110dac38a45f3d81ef1`
- frozen_boundary_identity: `d1b4448e22a1dba4292b9cf8969ba77db0cf9a10ef66dfddf98642cb5dc078a7`
- adapter_identity: `9c22de3d15d09132af1920eec0fd02e3ea9f879a70ecbd90bc5adc7913b63d2c`
- baseline_result_identity: `535459c72b0a91f9a82d19d1742d47feb5c7d8ab382d86756270336f7716268b`
- fusion_result_identity: `84d08dae0dca0158b786d70c90f05e597a3a22147c5aea82ae0500aca9efe4cd`
- configuration_digest: `76d26af733a191a0f9927b4a48db8f29b2c33ec422bab401de3a552b71be178d`
- results_identity_digest: `384e640924979d59882aa6b567b7d3216bdb7420948f66288a48d44f66e1c618`

## 4. Dataset/split verification

Canonical total: 27,319 (2,332 positive; 24,987 nominal negative; 21 projects). TRAIN: 19,114 (1,912 positive; 17,202 nominal negative). VALIDATION: 4,086 (260 positive; 3,826 nominal negative).

## 5. Explicit TEST seal verification

TEST metadata (4,119 / 160 / 3,959) is inherited provenance only. TEST predictors were not loaded; matrices were not transformed; probabilities and metrics were not generated; TEST was absent from bootstrap, project analysis, thresholding, and model selection.

## 6. Robustness protocol

Predeclared seeds 0, 7, 13, 21, 42, 73, 101, 202; fixed TRAIN-only fitting; untouched VALIDATION; equal-weight CODE RF + TEXT LR probability fusion; 1,000 paired VALIDATION bootstrap replicates at seed 108227; project subgroups; deterministic stratified 100%/90%/80% TRAIN sensitivity over the same seeds. No tuning occurred.

## 7. Seed robustness results

| Seed | CODE ROC | CODE AP | TEXT ROC | TEXT AP | Fusion ROC | Fusion AP | Δ ROC vs best | Δ AP vs best |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 0.691365 | 0.161135 | 0.697600 | 0.140258 | 0.746033 | 0.193084 | 0.048433 | 0.031949 |
| 7 | 0.693937 | 0.160817 | 0.697600 | 0.140258 | 0.747287 | 0.194077 | 0.049687 | 0.033261 |
| 13 | 0.690802 | 0.158955 | 0.697600 | 0.140258 | 0.745613 | 0.192235 | 0.048013 | 0.033281 |
| 21 | 0.692563 | 0.159046 | 0.697600 | 0.140258 | 0.746004 | 0.190023 | 0.048404 | 0.030978 |
| 42 | 0.691914 | 0.163159 | 0.697600 | 0.140258 | 0.745940 | 0.194312 | 0.048340 | 0.031153 |
| 73 | 0.692128 | 0.162028 | 0.697600 | 0.140258 | 0.746870 | 0.193384 | 0.049270 | 0.031356 |
| 101 | 0.693987 | 0.165062 | 0.697600 | 0.140258 | 0.746176 | 0.194767 | 0.048576 | 0.029705 |
| 202 | 0.692511 | 0.159624 | 0.697600 | 0.140258 | 0.746091 | 0.193013 | 0.048491 | 0.033389 |

## 8. Paired bootstrap results

Percentile intervals are VALIDATION development stability intervals, not final population confidence intervals.

| Comparison | Metric | Mean Δ | Median Δ | 2.5% | 97.5% | P(Δ>0) |
|---|---|---:|---:|---:|---:|---:|
| CODE+TEXT_minus_CODE | roc_auc | 0.054940 | 0.055115 | 0.033836 | 0.077573 | 1.000 |
| CODE+TEXT_minus_CODE | average_precision | 0.030513 | 0.030515 | 0.010010 | 0.052565 | 1.000 |
| CODE+TEXT_minus_TEXT | roc_auc | 0.048389 | 0.048504 | 0.023074 | 0.073394 | 0.999 |
| CODE+TEXT_minus_TEXT | average_precision | 0.051838 | 0.051806 | 0.025676 | 0.082049 | 1.000 |

## 9. Project-level results

Evaluable projects: 20; undefined one-class projects: 1. ROC counts: {'fusion_gt_code': 16, 'fusion_gt_text': 16, 'ties_vs_code': 0, 'ties_vs_text': 0, 'fusion_degrades_vs_code': 4, 'fusion_degrades_vs_text': 4}. AP counts: {'fusion_gt_code': 12, 'fusion_gt_text': 18, 'ties_vs_code': 0, 'ties_vs_text': 0, 'fusion_degrades_vs_code': 8, 'fusion_degrades_vs_text': 2}.

| Project | N | Pos | Neg | Prev | CODE ROC | CODE AP | TEXT ROC | TEXT AP | Fusion ROC | Fusion AP |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ant-ivy | 265 | 24 | 241 | 0.090566 | 0.674533 | 0.206789 | 0.755705 | 0.222511 | 0.782676 | 0.250799 |
| commons-bcel | 123 | 8 | 115 | 0.065041 | 0.657609 | 0.237402 | 0.619022 | 0.093560 | 0.675543 | 0.165923 |
| commons-beanutils | 91 | 1 | 90 | 0.010989 | 0.905556 | 0.083333 | 0.877778 | 0.083333 | 0.933333 | 0.142857 |
| commons-codec | 114 | 6 | 108 | 0.052632 | 0.784722 | 0.297275 | 0.655093 | 0.159648 | 0.796296 | 0.241722 |
| commons-collections | 273 | 7 | 266 | 0.025641 | 0.744629 | 0.062717 | 0.580021 | 0.042043 | 0.740602 | 0.071492 |
| commons-compress | 244 | 19 | 225 | 0.077869 | 0.576491 | 0.165492 | 0.698947 | 0.183138 | 0.662924 | 0.250854 |
| commons-configuration | 275 | 9 | 266 | 0.032727 | 0.625731 | 0.046073 | 0.637009 | 0.057473 | 0.677109 | 0.059048 |
| commons-dbcp | 155 | 2 | 153 | 0.012903 | 0.901961 | 0.120370 | 0.591503 | 0.022862 | 0.872549 | 0.075000 |
| commons-digester | 161 | 5 | 156 | 0.031056 | 0.521154 | 0.040229 | 0.800641 | 0.298141 | 0.755769 | 0.149053 |
| commons-io | 171 | 3 | 168 | 0.017544 | 0.426587 | 0.018640 | 0.716270 | 0.225411 | 0.607143 | 0.061055 |
| commons-jcs | 124 | 12 | 112 | 0.096774 | 0.771949 | 0.431204 | 0.717262 | 0.238313 | 0.799851 | 0.428177 |
| commons-lang | 445 | 29 | 416 | 0.065169 | 0.605645 | 0.127943 | 0.702462 | 0.161672 | 0.696452 | 0.175460 |
| commons-math | 603 | 59 | 544 | 0.097844 | 0.694728 | 0.200280 | 0.641451 | 0.170626 | 0.713048 | 0.206315 |
| commons-net | 168 | 10 | 158 | 0.059524 | 0.591772 | 0.104348 | 0.691772 | 0.103574 | 0.713291 | 0.105777 |
| commons-scxml | 81 | 2 | 79 | 0.024691 | 0.829114 | 0.534483 | 0.765823 | 0.152778 | 0.803797 | 0.530303 |
| commons-validator | 89 | 6 | 83 | 0.067416 | 0.744980 | 0.142637 | 0.718876 | 0.193463 | 0.811245 | 0.258929 |
| commons-vfs | 166 | 6 | 160 | 0.036145 | 0.583854 | 0.127607 | 0.514583 | 0.043994 | 0.558333 | 0.120683 |
| giraph | 126 | 12 | 114 | 0.095238 | 0.798246 | 0.274762 | 0.723684 | 0.261963 | 0.815058 | 0.429583 |
| gora | 82 | 0 | 82 | 0.000000 | NA | NA | NA | NA | NA | NA |
| opennlp | 162 | 8 | 154 | 0.049383 | 0.700081 | 0.461058 | 0.398539 | 0.056077 | 0.725649 | 0.320247 |
| parquet-mr | 168 | 32 | 136 | 0.190476 | 0.822036 | 0.564068 | 0.745404 | 0.375255 | 0.842831 | 0.543547 |

## 10. Training-fraction sensitivity results

| Fraction | Seed | Train N | Train Pos | CODE ROC | CODE AP | TEXT ROC | TEXT AP | Fusion ROC | Fusion AP | Δ ROC vs best | Δ AP vs best |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 100% | 0 | 19114 | 1912 | 0.691365 | 0.161135 | 0.697600 | 0.140258 | 0.746033 | 0.193084 | 0.048433 | 0.031949 |
| 100% | 7 | 19114 | 1912 | 0.693937 | 0.160817 | 0.697600 | 0.140258 | 0.747287 | 0.194077 | 0.049687 | 0.033261 |
| 100% | 13 | 19114 | 1912 | 0.690802 | 0.158955 | 0.697600 | 0.140258 | 0.745613 | 0.192235 | 0.048013 | 0.033281 |
| 100% | 21 | 19114 | 1912 | 0.692563 | 0.159046 | 0.697600 | 0.140258 | 0.746004 | 0.190023 | 0.048404 | 0.030978 |
| 100% | 42 | 19114 | 1912 | 0.691914 | 0.163159 | 0.697600 | 0.140258 | 0.745940 | 0.194312 | 0.048340 | 0.031153 |
| 100% | 73 | 19114 | 1912 | 0.692128 | 0.162028 | 0.697600 | 0.140258 | 0.746870 | 0.193384 | 0.049270 | 0.031356 |
| 100% | 101 | 19114 | 1912 | 0.693987 | 0.165062 | 0.697600 | 0.140258 | 0.746176 | 0.194767 | 0.048576 | 0.029705 |
| 100% | 202 | 19114 | 1912 | 0.692511 | 0.159624 | 0.697600 | 0.140258 | 0.746091 | 0.193013 | 0.048491 | 0.033389 |
| 90% | 0 | 17202 | 1721 | 0.694888 | 0.168634 | 0.691282 | 0.129284 | 0.744565 | 0.187044 | 0.049677 | 0.018410 |
| 90% | 7 | 17202 | 1721 | 0.693252 | 0.164323 | 0.695790 | 0.138480 | 0.744758 | 0.195239 | 0.048967 | 0.030916 |
| 90% | 13 | 17202 | 1721 | 0.692602 | 0.162780 | 0.698620 | 0.141747 | 0.747610 | 0.196344 | 0.048990 | 0.033565 |
| 90% | 21 | 17202 | 1721 | 0.693953 | 0.159477 | 0.694242 | 0.137743 | 0.744254 | 0.189915 | 0.050012 | 0.030438 |
| 90% | 42 | 17202 | 1721 | 0.697194 | 0.162704 | 0.697161 | 0.143113 | 0.750526 | 0.197276 | 0.053332 | 0.034571 |
| 90% | 73 | 17202 | 1721 | 0.691037 | 0.154985 | 0.691564 | 0.138525 | 0.739557 | 0.187792 | 0.047993 | 0.032806 |
| 90% | 101 | 17202 | 1721 | 0.694292 | 0.163112 | 0.691700 | 0.133930 | 0.744529 | 0.186789 | 0.050237 | 0.023677 |
| 90% | 202 | 17202 | 1721 | 0.697441 | 0.161310 | 0.703659 | 0.146571 | 0.749763 | 0.198238 | 0.046104 | 0.036928 |
| 80% | 0 | 15291 | 1530 | 0.697186 | 0.172591 | 0.688886 | 0.127028 | 0.743776 | 0.189896 | 0.046591 | 0.017305 |
| 80% | 7 | 15291 | 1530 | 0.691419 | 0.156181 | 0.692856 | 0.136387 | 0.743438 | 0.186945 | 0.050582 | 0.030764 |
| 80% | 13 | 15291 | 1530 | 0.688544 | 0.153469 | 0.694113 | 0.141421 | 0.743232 | 0.192674 | 0.049119 | 0.039205 |
| 80% | 21 | 15291 | 1530 | 0.693458 | 0.159195 | 0.690954 | 0.137401 | 0.743615 | 0.184988 | 0.050156 | 0.025793 |
| 80% | 42 | 15291 | 1530 | 0.695733 | 0.164376 | 0.691372 | 0.139285 | 0.746974 | 0.196122 | 0.051242 | 0.031746 |
| 80% | 73 | 15291 | 1530 | 0.694918 | 0.164851 | 0.695339 | 0.146748 | 0.746257 | 0.194798 | 0.050918 | 0.029947 |
| 80% | 101 | 15291 | 1530 | 0.696478 | 0.164633 | 0.689513 | 0.130085 | 0.744848 | 0.188276 | 0.048370 | 0.023643 |
| 80% | 202 | 15291 | 1530 | 0.684454 | 0.154068 | 0.701356 | 0.144444 | 0.741586 | 0.191781 | 0.040230 | 0.037712 |

## 11. Primary CODE+TEXT versus unimodal comparison

Reference seed-0 Δ versus the metric-wise best unimodal: ROC-AUC +0.048433; AP +0.031949. Median across seeds: ROC-AUC +0.048462; AP +0.031653.

## 12. Decision-rule application

- median_both_positive: **PASS**
- seed_no_systematic_collapse: **PASS**
- bootstrap_clear_majority: **PASS**
- not_driven_solely_by_one_project: **PASS**
- moderate_reductions_preserve_advantage: **PASS**

## 13. Threats to validity

- All inference is restricted to frozen VALIDATION development evidence; TEST remains sealed.
- Bootstrap percentile intervals are development-set stability intervals, not final population confidence intervals.
- Project-level estimates are heterogeneous and some projects have few positives.
- Training reduction is a sensitivity analysis, not model selection.
- Probabilities remain uncalibrated.

## 14. Scientific interpretation

The result supports only the most robust development candidate among the frozen alternatives. It does not prove final generalization, production superiority, statistical universality, causal complementarity, or a final benchmark result. AP receives particular weight because positives are sparse; ROC-AUC and AP are retained separately.

## 15. Explicit prohibited-actions confirmation

No TEST predictive access, TRAIN+VALIDATION refit, calibration, XAI, learned/optimized fusion, hyperparameter search, semantic model download, relabeling, split change, SMOTE, commit, push, PR, merge, or branch deletion occurred.

## 16. PROCESS status

**OPTIONAL ABLATION / NOT SUPPORTED AS PRIMARY CONTRIBUTOR UNDER CURRENT REPRESENTATION**. The current ancestor-only representation under the evaluated fusion design lacked positive incremental development evidence; this is not a claim that process information is intrinsically useless.

## 17. Reproducibility and quality

Two complete independent runs were exactly equal before artifact annotation, including configuration, seed set, metrics, bootstrap, projects, fractions, decision, and identity. Focused/full pytest, Ruff, compilation, and git diff checks are recorded in the machine-readable audit.

## 18. Recommended next sprint

Sprint 10.8.2.28 — Freeze Robust Multimodal Architecture and Predeclare Calibration Protocol
