# Canonical JIT-Defects4J Multimodal Dataset Audit

Decision: **GO**

## Inventory and frozen temporal split

- Observations: 27319 (2332 positive; 24987 nominal negative).
- TRAIN: 19114 (1912 positive; 17202 nominal negative; prevalence 0.10003139).
- VALIDATION: 4086 (260 positive; 3826 nominal negative; prevalence 0.06363191).
- TEST: 4119 (160 positive; 3959 nominal negative; prevalence 0.03884438).
- Projects: 21.
- Class-sparse project partitions: 4; see manifest for exact entries.
- Identity uniqueness: PASS; cross-partition overlap: 0.

## Predictor contracts

- CODE: exact Git parent/root raw tree changes: path, status, modes, old/new blob identities, and status counts.
- PROCESS: parent count, merge indicator, prior-history indicator, and exact count of commits in ancestors(C). Descendants and C itself are excluded.
- TEXT: canonical raw commit message; missing values use `<MISSING_COMMIT_MESSAGE>`.
- Leakage denylist: PASS. Targets, line labels, fix/SZZ/blame/future/post-observation metadata, label-derived fields, and supplied partitions are excluded.

## Reproducibility

- Source revision: `584799fdec6095ab75a45fd2a5f8db5b12163aa5`.
- Package SHA-256: `9e5ca1a393b70ee7e87c410b162005958775f3f3732f9f83da9dd24a7dfe2b47`.
- Scientific identity: `e509995da233c932cafce531c13ad2cd617a0d8abbe8d81ccaa373b8f29fa519`.
- Manifest SHA-256: `95b1a362f6756f641cc575cabf54a3a99e2846568d5ef110dac38a45f3d81ef1`.
- Every scientific artifact is canonically serialized and SHA-256 identified in `manifest.json`.

## Per-project counts and class sparsity

| Project | Split | N | Positive | Nominal negative | Prevalence | Sparse |
|---|---:|---:|---:|---:|---:|---:|
| ant-ivy | train | 1239 | 293 | 946 | 0.23648103 | no |
| ant-ivy | validation | 265 | 24 | 241 | 0.09056604 | no |
| ant-ivy | test | 267 | 15 | 252 | 0.05617978 | no |
| commons-bcel | train | 577 | 44 | 533 | 0.07625650 | no |
| commons-bcel | validation | 123 | 8 | 115 | 0.06504065 | no |
| commons-bcel | test | 125 | 8 | 117 | 0.06400000 | no |
| commons-beanutils | train | 427 | 36 | 391 | 0.08430913 | no |
| commons-beanutils | validation | 91 | 1 | 90 | 0.01098901 | no |
| commons-beanutils | test | 93 | 0 | 93 | 0.00000000 | yes |
| commons-codec | train | 532 | 29 | 503 | 0.05451128 | no |
| commons-codec | validation | 114 | 6 | 108 | 0.05263158 | no |
| commons-codec | test | 115 | 1 | 114 | 0.00869565 | no |
| commons-collections | train | 1276 | 32 | 1244 | 0.02507837 | no |
| commons-collections | validation | 273 | 7 | 266 | 0.02564103 | no |
| commons-collections | test | 274 | 11 | 263 | 0.04014599 | no |
| commons-compress | train | 1141 | 155 | 986 | 0.13584575 | no |
| commons-compress | validation | 244 | 19 | 225 | 0.07786885 | no |
| commons-compress | test | 245 | 4 | 241 | 0.01632653 | no |
| commons-configuration | train | 1286 | 143 | 1143 | 0.11119751 | no |
| commons-configuration | validation | 275 | 9 | 266 | 0.03272727 | no |
| commons-configuration | test | 277 | 3 | 274 | 0.01083032 | no |
| commons-dbcp | train | 725 | 56 | 669 | 0.07724138 | no |
| commons-dbcp | validation | 155 | 2 | 153 | 0.01290323 | no |
| commons-dbcp | test | 157 | 0 | 157 | 0.00000000 | yes |
| commons-digester | train | 755 | 7 | 748 | 0.00927152 | no |
| commons-digester | validation | 161 | 5 | 156 | 0.03105590 | no |
| commons-digester | test | 163 | 7 | 156 | 0.04294479 | no |
| commons-io | train | 799 | 69 | 730 | 0.08635795 | no |
| commons-io | validation | 171 | 3 | 168 | 0.01754386 | no |
| commons-io | test | 172 | 1 | 171 | 0.00581395 | no |
| commons-jcs | train | 581 | 64 | 517 | 0.11015491 | no |
| commons-jcs | validation | 124 | 12 | 112 | 0.09677419 | no |
| commons-jcs | test | 126 | 12 | 114 | 0.09523810 | no |
| commons-lang | train | 2078 | 109 | 1969 | 0.05245428 | no |
| commons-lang | validation | 445 | 29 | 416 | 0.06516854 | no |
| commons-lang | test | 446 | 8 | 438 | 0.01793722 | no |
| commons-math | train | 2818 | 252 | 2566 | 0.08942512 | no |
| commons-math | validation | 603 | 59 | 544 | 0.09784411 | no |
| commons-math | test | 605 | 24 | 581 | 0.03966942 | no |
| commons-net | train | 784 | 102 | 682 | 0.13010204 | no |
| commons-net | validation | 168 | 10 | 158 | 0.05952381 | no |
| commons-net | test | 169 | 5 | 164 | 0.02958580 | no |
| commons-scxml | train | 380 | 37 | 343 | 0.09736842 | no |
| commons-scxml | validation | 81 | 2 | 79 | 0.02469136 | no |
| commons-scxml | test | 83 | 8 | 75 | 0.09638554 | no |
| commons-validator | train | 418 | 26 | 392 | 0.06220096 | no |
| commons-validator | validation | 89 | 6 | 83 | 0.06741573 | no |
| commons-validator | test | 91 | 4 | 87 | 0.04395604 | no |
| commons-vfs | train | 777 | 105 | 672 | 0.13513514 | no |
| commons-vfs | validation | 166 | 6 | 160 | 0.03614458 | no |
| commons-vfs | test | 167 | 3 | 164 | 0.01796407 | no |
| giraph | train | 590 | 140 | 450 | 0.23728814 | no |
| giraph | validation | 126 | 12 | 114 | 0.09523810 | no |
| giraph | test | 128 | 11 | 117 | 0.08593750 | no |
| gora | train | 387 | 39 | 348 | 0.10077519 | no |
| gora | validation | 82 | 0 | 82 | 0.00000000 | yes |
| gora | test | 84 | 0 | 84 | 0.00000000 | yes |
| opennlp | train | 760 | 75 | 685 | 0.09868421 | no |
| opennlp | validation | 162 | 8 | 154 | 0.04938272 | no |
| opennlp | test | 164 | 8 | 156 | 0.04878049 | no |
| parquet-mr | train | 784 | 99 | 685 | 0.12627551 | no |
| parquet-mr | validation | 168 | 32 | 136 | 0.19047619 | no |
| parquet-mr | test | 168 | 27 | 141 | 0.16071429 | no |

## Limitations

Nominal negatives retain the benchmark's closed-world semantics. CODE is a deterministic tree-change representation, not raw patch text or a learned encoding; rename similarity is deliberately not inferred. PROCESS intentionally favors a small auditable ancestor-only schema. No model, vectorizer, embedding, calibration, fusion, or explanation was fit.
