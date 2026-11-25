# Editable tables

CSV files preserve full precision. The compact Markdown views below use display rounding only.

## Table A coverage

| modality | algorithm | accepted_E1 | method | fidelity | stability_repetitions | E1_status |
| --- | --- | --- | --- | --- | --- | --- |
| CODE | LR | 245 | ANALYTICAL_CENTERED_LOGIT | PASS | 20 | READY |
| TEXT | LR | 245 | ANALYTICAL_CENTERED_LOGIT | FIDELITY_PASS | 20 | READY |
| PROCESS | LR | 0 | NOT_EVALUATED | NOT_EVALUATED | 0 | NO-GO |
| CODE | RF | 245 | EXACT_TREESHAP | PASS | 20 | READY |
| TEXT | RF | 0 | EXACT_TREE_PATH_DEPENDENT | FIDELITY_FAIL | 0 | NO-GO |
| PROCESS | RF | 0 | NOT_EVALUATED | NOT_EVALUATED | 0 | NO-GO |
| CODE | XGB | 245 | EXACT_TREESHAP | PASS | 20 | READY |
| TEXT | XGB | 245 | EXACT_TREE_PATH_DEPENDENT | FIDELITY_PASS | 20 | READY |
| PROCESS | XGB | 0 | NOT_EVALUATED | NOT_EVALUATED | 0 | NO-GO |
| CODE | LGB | 245 | EXACT_TREESHAP | PASS | 20 | READY |
| TEXT | LGB | 245 | EXACT_TREE_PATH_DEPENDENT | FIDELITY_PASS | 20 | READY |
| PROCESS | LGB | 0 | NOT_EVALUATED | NOT_EVALUATED | 0 | NO-GO |

## Table B global CODE

| model | feature | rank | mean_absolute | median_absolute | scale |
| --- | --- | --- | --- | --- | --- |
| LR | la | 5 | 0.0755375 | 0.046916 | Logit (analytical decomposition) |
| LR | ld | 6 | 0.00340398 | 0.00267529 | Logit (analytical decomposition) |
| LR | nf | 3 | 0.18162 | 0.170278 | Logit (analytical decomposition) |
| LR | nd | 2 | 0.186846 | 0.146974 | Logit (analytical decomposition) |
| LR | ns | 4 | 0.0859694 | 0.0130096 | Logit (analytical decomposition) |
| LR | ent | 1 | 0.490638 | 0.511236 | Logit (analytical decomposition) |
| RF | la | 1 | 0.0885165 | 0.0897343 | Probability (exact TreeSHAP) |
| RF | ld | 2 | 0.0334887 | 0.0254491 | Probability (exact TreeSHAP) |
| RF | nf | 3 | 0.0270805 | 0.0245872 | Probability (exact TreeSHAP) |
| RF | nd | 5 | 0.0176519 | 0.0116794 | Probability (exact TreeSHAP) |
| RF | ns | 6 | 0.00722741 | 0.00121614 | Probability (exact TreeSHAP) |
| RF | ent | 4 | 0.0229326 | 0.0173204 | Probability (exact TreeSHAP) |
| XGB | la | 1 | 0.755547 | 0.74126 | Native margin (exact TreeSHAP) |
| XGB | ld | 2 | 0.146422 | 0.0835227 | Native margin (exact TreeSHAP) |
| XGB | nf | 6 | 0.043632 | 0.0191786 | Native margin (exact TreeSHAP) |
| XGB | nd | 3 | 0.105408 | 0.0602136 | Native margin (exact TreeSHAP) |
| XGB | ns | 5 | 0.0519053 | 0.0114366 | Native margin (exact TreeSHAP) |
| XGB | ent | 4 | 0.0785003 | 0.0520705 | Native margin (exact TreeSHAP) |
| LGB | la | 1 | 0.869414 | 0.685335 | Native margin (exact TreeSHAP) |
| LGB | ld | 2 | 0.19969 | 0.117288 | Native margin (exact TreeSHAP) |
| LGB | nf | 3 | 0.110202 | 0.0467118 | Native margin (exact TreeSHAP) |
| LGB | nd | 6 | 0.0958377 | 0.0408084 | Native margin (exact TreeSHAP) |
| LGB | ns | 4 | 0.0983919 | 0.0178289 | Native margin (exact TreeSHAP) |
| LGB | ent | 5 | 0.0972515 | 0.0313713 | Native margin (exact TreeSHAP) |

## Table C alignment

| configuration | algorithm | commits | verified_explanatory_links | max_error | status |
| --- | --- | --- | --- | --- | --- |
| C+P | LR | 245 | 1 | 0.0 | PARTIAL |
| C+T | LR | 245 | 2 | 0.0 | READY |
| P+T | LR | 245 | 1 | 0.0 | PARTIAL |
| C+P+T | LR | 245 | 2 | 0.0 | PARTIAL |
| C+P | RF | 245 | 1 | 0.0 | PARTIAL |
| C+T | RF | 245 | 1 | 0.0 | PARTIAL |
| P+T | RF | 245 | 0 |  | PARTIAL |
| C+P+T | RF | 245 | 1 | 0.0 | PARTIAL |
| C+P | XGB | 245 | 1 | 0.0 | PARTIAL |
| C+T | XGB | 245 | 2 | 0.0 | READY |
| P+T | XGB | 245 | 1 | 0.0 | PARTIAL |
| C+P+T | XGB | 245 | 2 | 0.0 | PARTIAL |
| C+P | LGB | 245 | 1 | 0.0 | PARTIAL |
| C+T | LGB | 245 | 2 | 0.0 | READY |
| P+T | LGB | 245 | 1 | 0.0 | PARTIAL |
| C+P+T | LGB | 245 | 2 | 0.0 | PARTIAL |

## Table D limitations

| topic | evidence | boundary |
| --- | --- | --- |
| Scope | ActiveMQ T1; 245 commits | No automatic generalization to 14 projects |
| PROCESS | Predictive and E2 modality; E1 not evaluated | Temporal provenance not independently established; no observed leakage demonstrated |
| RF TEXT | Predictor remains; no accepted E1 | Exact TreeSHAP additivity failed |
| Calibration | 16 aligned scopes have RAW state | No independently verified calibrated endpoint for these instances |
| Scales | E1 native scales; E2 meta-logit | No cross-level addition or magnitude equivalence |
| Stability | 20 deterministic repetitions | Not perturbation robustness or human usefulness |
| Provenance | Reconstructed predictors and representations | Not original executable recovery |
| Local cases | Eight frozen E1 cases available in E2 foreground | Not the same E2 historical local set; not a representative sample |
