# E2 final scientific closure

**E2_FINAL_CLOSURE_PASS**

## A. Purpose and verified execution context

This package closes the previously prepared primary multimodal E2 explanatory layer.
It does not reopen predictive experimentation, calibration, statistical conclusions or
the frozen MIXED_CONFIRMATORY_EVIDENCE conclusion.

Repository: `/Users/alex/MMSDP-XAI-Q1`.
Branch: `sprint-10/q1-e2-final-closure`.
Starting HEAD: `77c1af5d59ee7af6257f67ce17d06968ef78a416`.
The original closure began with a clean working tree. This authorized resumption begins
with the earlier diagnostic, foreground-freeze package and its implementation/tests
untracked; the exact resumption state is preserved in `e2_execution_manifest.json`.
All historical evidence, including the failed 1.0.0 closure and the foreground freeze,
remains unchanged. No commit, push, merge, rebase or reset occurred.

## B. Frozen inputs and provenance

Authoritative sources are the 56.2E E2 readiness/OOF mean records, the primary scope ledger,
the frozen reconstruction component journal and LR meta-model objects, the isolated
Sprint54 T1 probability ledger, and the PASS foreground package at
`audits/q1-e2-t1-foreground-freeze/1.0.0/`.
All 302 critical input hashes are recorded in `e2_execution_manifest.json`
and rechecked at finalization. Each executable LR coefficient/intercept dtype, shape and
array hash agrees with its canonical state; model identity and actual modality order agree
with the scope contract. OOF objects are hash-verified; resolved means are looked up by
project/family/modality, checked against their hexadecimal value, scalar hash and historical
meta-training membership. No reference mean was recomputed or substituted.

The isolated T1 source has SHA-256
`eb4b6956b185e63cd322d92b8cdf96f53fcb09ef83b6a16f2334d660c6f5adc8`.
Its unchanged bytes and prior identity/probability reconciliation establish frozen-source
continuity. Only the frozen foreground RAW probabilities enter E2; labels, calibrated
outputs and thresholds are unused. Reading the T1 transport is not a new prediction run.

**Logit provenance:** the ledger stores RAW fusion probabilities, not a separate native
meta-logit column. The logit reference is the independently evaluated uncentered expression
`alpha + P @ beta` from the verified frozen state and inputs. The centered reconstruction
is compared to that reference and independently to the persisted RAW fusion probability.
No claim is made that a separately persisted logit was recovered. No estimator prediction
or fitting method was called.

## C. E2 population

All 221 eligible scopes executed: C+P 56; C+T 55; P+T 55; C+P+T 55, across 14 Apache
projects and four frozen base-model families. The three existing apache/zeppelin Logistic
Regression TEXT-containing multimodal exclusions remain unchanged.

The 2,450 frozen unique project/commit foreground cases yield **39,026 scope-row
explanations**. This is not 39,026 distinct commits: the same case can occur in multiple
models/configurations. The local table covers all **1,768 frozen local scope-rows** (8 per
scope). No population reselection, expansion or post-hoc substitution occurred.

## D. Reference regime

PRIMARY_REFERENCE_OOF is unchanged. Each mu is the resolved full historical temporal
meta-training OOF mean. The warmup exclusion belongs to that historical design.
These means describe the historical meta-training regime and are not claimed to represent
deployed-model full-TRAIN behavior. T1 is never used to construct the baseline.

## E. Mathematical decomposition

For the actual frozen modality order:

`phi_0 = beta_0 + sum(beta_m * mu_m)`

`phi_m = beta_m * (p_m - mu_m)`

`eta_E2 = phi_0 + sum(phi_m)`

`z_reference = beta_0 + sum(beta_m * p_m)`

`p_reconstructed = sigmoid(eta_E2)`

The calculation uses binary64 inputs and arithmetic. Signed phi indicates movement above
or below the modality's OOF-reference contribution to the fusion meta-logit. Absolute phi
describes score-contribution magnitude, not causal importance. No SHAP execution occurs.

## F. Fidelity

The pre-existing prospective tolerance was retained before attribution: logit residual
<= `1e-10*(1+abs(z_reference))`; RAW probability residual <= `1e-10`. These are strict
binary64 reconstruction bounds, allowing arithmetic reassociation and sigmoid rounding;
they were not changed after seeing outputs. The aggregate mean-logit bound is `1e-12`.

- Rows checked per execution: **39026**.
- Maximum / mean logit residual: **1.77635683940025e-15 / 1.705800453598173e-16**.
- Maximum / mean RAW probability residual: **4.440892098500626e-16 / 2.8058372118431e-17**.
- Rows outside tolerance: **0**; affected scopes: **none**.
- Aggregate mean-logit checks: **PASS for every scope**.

`e2_fidelity_summary.csv` reports each project/model/configuration, support, maxima, means
and failures. Calibration is outside the additive scale and is not compared to the logit.

## G. Deterministic reproducibility

Two independent Python processes reopened the same frozen inputs and recomputed E2.
The compressed attribution CSV, fidelity table, local table and provenance files are
byte-identical. Differing rows: **0**; maximum numeric difference: **0**.
`e2_reproducibility_report.json` records both hashes of every principal numeric artifact,
including the uncompressed CSV hash in the worker provenance. There were no random seeds,
retraining repetitions or stochastic-stability claims. This tests execution reproducibility.

## H. Global findings and heterogeneity

The table below pools descriptive scope-row observations within each configuration.
Its observations overlap across model families; it is not an independent-sample estimate,
a predictive comparison, a population-weighted project estimate or an inferential test.
The complete table also provides configuration/family and project/family/configuration
strata, medians, 10th/90th percentiles, and positive/negative/zero fractions.

| Configuration | Modality | Scope-rows | Mean signed phi | Mean absolute phi | Positive fraction |
|---|---|---:|---:|---:|---:|
| C+P | CODE | 9800 | 0.3873 | 0.8183 | 0.5695 |
| C+P | PROCESS | 9800 | 0.0422 | 0.1887 | 0.5251 |
| C+P+T | CODE | 9742 | 0.3504 | 0.7557 | 0.5681 |
| C+P+T | PROCESS | 9742 | 0.0142 | 0.1517 | 0.4769 |
| C+P+T | TEXT | 9742 | 0.1677 | 0.3667 | 0.6064 |
| C+T | CODE | 9742 | 0.3810 | 0.8186 | 0.5681 |
| C+T | TEXT | 9742 | 0.1884 | 0.3936 | 0.6064 |
| P+T | PROCESS | 9742 | 0.0626 | 0.3634 | 0.5231 |
| P+T | TEXT | 9742 | 0.2453 | 0.5093 | 0.6412 |


In this frozen foreground, pooled mean signed contributions are positive in all listed
configuration/modality summaries, although individual contributions have both signs.
In configurations containing CODE, its pooled mean absolute contribution exceeds the other
included modalities for this population. This descriptive observation is conditional on
the frozen model, reference and foreground; it establishes no intrinsic modality superiority.
PROCESS pooled magnitude differs markedly across configurations (about 0.152 in C+P+T
versus 0.363 in P+T), illustrating dependence on the fitted fusion context.

Project/model/configuration mean absolute contributions range from approximately
0.289–1.649 for CODE, 0.0079–1.213 for PROCESS, and 0.0057–2.082 for TEXT across applicable
scopes. Figure E2-1 retains each project as a point within each family/configuration and
shows the across-project median and interquartile range. Those ranges are descriptive
heterogeneity, not confidence intervals. No universal ranking is asserted.

## I. Local examples

The frozen contract is label-free and unstratified; TP/TN/FP/FN, confidence, correctness and
predicted-decision selection are prohibited. The complete local table preserves every
frozen local case, exact probabilities, coefficients, OOF means, phi_0, signed modality
terms, both logits, both RAW probabilities and residuals.

Before attribution, the display rule was fixed in `pre_execution_policy.json`: for each
configuration, choose local ordinal 1 in the lexicographically first eligible project/model
scope. This yields four ActiveMQ/LightGBM illustrations; they are not representative
samples of all projects or families. They were not selected for their explanation values.
Their frozen RAW probabilities are approximately 0.3380 (C+P), 0.4431 (C+T), 0.1753 (P+T)
and 0.5909 (C+P+T). Exact rows are in `figure_data/E2_local_meta_logit_decomposition.csv`.
Figure E2-2 distinguishes positive and negative logit movement; numeric rounding is display-only.

## J. Limitations and manuscript boundaries

- E2 explains frozen model behavior, not causal influences on defects or individual features.
- OOF reference describes historical meta-training, not deployed-model full-TRAIN behavior.
- Patterns depend on project, family, configuration and the bounded selected T1 foreground.
- Global pooled observations overlap across scopes; no significance or superiority claim follows.
- The four local panels are deterministic illustrations from one project/family; broader local
  evidence is available in the complete table, without changing the selection contract.
- E1 remains bounded complementary evidence; its figures, exclusions and conclusions are unchanged.
- T2 remained sealed. No T2-based claim, validation or rescue analysis is supported.
- No human usefulness, organizational impact, user acceptance, developer behavior or predictive
  improvement was tested. Predictive metrics and MIXED_CONFIRMATORY_EVIDENCE remain frozen.

## K. Publication readiness and deliverables

The following are publication-ready for the bounded E2 claim:

- **Table E2-A:** `e2_global_summary.csv` (configuration, family and scope strata).
- **Table E2-B:** `e2_fidelity_summary.csv` (all 221 scopes).
- **Table E2-C:** `e2_local_cases.csv` (all 1,768 local scope-rows).
- **Figure E2-1:** `figures/E2_global_modality_contributions.png`, PDF and SVG.
- **Figure E2-2:** `figures/E2_local_meta_logit_decomposition.png`, PDF and SVG.

PNG exports use 300 dpi; PDFs/SVGs preserve vectors. `figure_data/` retains exact inputs and
the derived plotting summaries. An optional third figure is omitted because E2-1 already
shows the requested project/family/configuration heterogeneity. `e2_attributions.csv.gz`
contains all 39,026 scope-row decompositions, one row per scope/commit.

**E2 is scientifically ready to be cited in Section 5 and discussed in Section 6 within
these explicit limitations.** Use `e2_publication_claims.json` to constrain wording.

## L. Governance, checks and reproduction

T2 scientific accesses = **0**; E1 reruns = **0**; model retraining = **0**;
calibration refits = **0**; predictive recomputations = **0**.
There are two E2 arithmetic executions and zero estimator prediction calls.
Exact scientific-payload allowlists guard worker reads; writes are confined to temporary
worker output directories. Historical input hashes were rechecked after execution and at
finalization. Git reports no tracked or staged changes. All closure work remains untracked
for human inspection; the old diagnostic and foreground package retain their valid manifests.

Nine focused E2 tests passed (ordering, additive reconstruction, sigmoid, OOF lookup,
determinism, invalid probabilities, eligibility and T2 read denial). The final CSV invariants,
exact repeated hashes and both publication figures were checked. `validation_results.json`
records validation; `plot_runtime.json` records the isolated temporary plotting environment.
Installing plotting dependencies did not change either frozen Python environment.

Reproduction entry points, in order, are the dedicated module
`src.evaluation.q1_e2_final_closure`, `scripts/plot_q1_e2_final_closure.py`, and
`scripts/finalize_q1_e2_final_closure.py`. The scientific worker runs with `.venv-xai-s56/bin/python`
and all five documented thread variables set to 1. The module refuses to overwrite this
package; reproduction should use an isolated repository copy where this output version is
absent. No already-frozen package should be deleted or overwritten to rerun it.

The finalizer requires recorded test and visual QA results in `validation_results.json`;
reviewers must rerun tests and visually inspect regenerated figures before setting those
fields. All artifact hashes, including this report and the execution manifest, are in
`MANIFEST.sha256` (which excludes itself to avoid recursive hashing).

## M. Final status

**E2_FINAL_CLOSURE_PASS**
