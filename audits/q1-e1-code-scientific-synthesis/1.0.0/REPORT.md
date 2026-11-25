# Scientific synthesis — E1 CODE

Status: synthesis and independent reproducibility verification PASS. Seven figures regenerated with identical SVG bytes and PNG pixels; all source artifacts unchanged.

## Scope and evidence

Exclusive result source: audits/q1-e1-code-execution/1.0.0/scientific/. All source hashes, IDs, 245 temporal positions, six features, four models, eight locals and 20 repetitions were checked. No original feature values exist in the NPZ schema. All files are reread from disk.

## Statistical conventions

Use repetition 0 only after verifying identical attribution arrays across all 20 repetitions; n=245, not 4900. Population standard deviation (ddof=0), linearly interpolated percentiles (1,5,25,50,75,95,99), signed and absolute IQRs, exact sign fractions and +/-1e-12 zero-band fractions. No labels, predictive accuracy, inferred feature values, inferential p-values or confidence intervals. Local values remain native-scale.

## Full mean/median overview

| Model | Feature | Rank | Mean absolute | Median absolute | Mean signed | Median signed |
|---|---|---:|---:|---:|---:|---:|
| LR | la | 5 | 0.075537523 | 0.046916038 | 0.012269801 | -0.041764263 |
| LR | ld | 6 | 0.0034039829 | 0.0026752855 | 0.0007949024 | 0.0026014208 |
| LR | nf | 3 | 0.18162023 | 0.17027846 | 0.021716005 | 0.10879569 |
| LR | nd | 2 | 0.18684623 | 0.14697387 | -0.0039198509 | -0.14697387 |
| LR | ns | 4 | 0.08596944 | 0.013009582 | -0.06855253 | 0.013009582 |
| LR | ent | 1 | 0.49063802 | 0.51123599 | 0.00022149111 | -0.16606473 |
| RF | la | 1 | 0.088516529 | 0.089734337 | 0.00026705927 | -0.016543434 |
| RF | ld | 2 | 0.033488703 | 0.025449086 | -0.0014254624 | -9.0761405e-05 |
| RF | nf | 3 | 0.027080453 | 0.024587204 | -0.0020033356 | -0.017633399 |
| RF | nd | 5 | 0.017651879 | 0.011679422 | -0.0051628154 | -0.011147432 |
| RF | ns | 6 | 0.0072274069 | 0.0012161427 | 0.0047630134 | -0.00091124692 |
| RF | ent | 4 | 0.022932628 | 0.017320412 | 0.0064030054 | -0.0029910943 |
| XGB | la | 1 | 0.75554724 | 0.74125969 | -0.16676104 | -0.028354643 |
| XGB | ld | 2 | 0.14642192 | 0.083522685 | -0.06752234 | -0.0069471104 |
| XGB | nf | 6 | 0.043631999 | 0.019178554 | 0.0086952781 | -0.017333413 |
| XGB | nd | 3 | 0.10540804 | 0.060213625 | -0.019190065 | -0.058303129 |
| XGB | ns | 5 | 0.051905341 | 0.011436632 | 0.037262195 | -0.0040402962 |
| XGB | ent | 4 | 0.078500291 | 0.052070532 | 0.0044697184 | -0.02667846 |
| LGB | la | 1 | 0.86941363 | 0.68533544 | 0.20756592 | 0.32463579 |
| LGB | ld | 2 | 0.19969049 | 0.1172884 | -0.14737553 | -0.066013246 |
| LGB | nf | 3 | 0.11020177 | 0.046711795 | 0.03124191 | -0.03986138 |
| LGB | nd | 6 | 0.095837681 | 0.040808374 | 0.007503205 | -0.035068256 |
| LGB | ns | 4 | 0.098391853 | 0.017828863 | 0.073472761 | -0.0077081058 |
| LGB | ent | 5 | 0.097251479 | 0.031371276 | -0.0054559203 | -0.0012595527 |

Complete distributions, extrema, percentiles, SD/IQR and sign proportions are in global_statistics.csv/JSON; 5880 per-commit feature contributions are in attributions_long.csv/JSON. The original 20-repetition tensors remain in the immutable source.

## Additional, non-redundant analyses

- Six model pairs: global Spearman/Kendall and top-three Jaccard; no significance claims.
- 1470 paired commit profiles: per-commit absolute-feature rank correlation and total variation between within-row normalized absolute profiles. These are composition comparisons, not equal magnitudes or equal reference estimands.
- 980 model–commit summaries: dominant feature, magnitude share, normalized entropy, cancellation index, stored probability and threshold decision. A zero attribution total makes distributional interpretations undefined; none occurs in this dataset.
- Model-level concentration and dominant-feature counts: inspect global/local heterogeneity without feature-value dependence claims.
- Threshold disagreement derived from stored probabilities only; no inference and no performance assessment.

All 32 local interpretations are in local_case_interpretations.md and local_cases.csv/JSON. All raw feature-value fields are explicitly null/unavailable.

## Reproduction

Run analyze.py into a new output directory; plot_svg.py accepts that figure_data directory and a new figure directory; render_png.cjs renders those SVGs using the installed Sharp library. No model or SHAP imports occur. SVG geometry is generated explicitly because matplotlib is not installed; no dependency installation was performed. Figure data include the complete plotted observations. See provenance.json and reproduction_verification.json for versions and byte/pixel comparisons.

## Claims boundary

Observed: model-specific attribution distributions, rankings, decomposition fidelity and fixed-input numerical stability. Descriptive: cross-model rank/profile agreement and cancellation. Requires further validation: causal explanations, defect-detection accuracy, reviewer benefit, industrial utility, trust, perturbation robustness, and generalization to other projects. E1 CODE/TEXT are unimodal and cannot replace or be summed into E2 fusion contributions. PROCESS E1 remains excluded for unproven temporal provenance. No historical results or main manuscript were changed.
