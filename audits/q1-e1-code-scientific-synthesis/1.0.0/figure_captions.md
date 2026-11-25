# Figure captions and placement recommendations

## Recommended main figures

**Figure 1 — Global CODE attribution importance.** Mean absolute feature attribution across 245 ActiveMQ T1 commits, computed from the first of 20 identical repetitions. Panel axes are independent: LR is in logit units, RF in probability units, and XGB/LGB in native margins. Bars rank features within models; their lengths must not be compared across output scales. Source: figure_data/global_importance.json.

**Figure 2 — Within-model feature rankings.** Rank 1 denotes the largest mean absolute attribution. This rank-only comparison highlights model-dependent ordering without equating attribution magnitudes or claiming causal importance. Six features are compared; rank correlations are descriptive. Source: figure_data/rank_comparison.json.

## Recommended supplementary figures

**Figure S1 — CODE attribution distributions.** Each feature row displays all 245 signed contributions, with deterministic vertical jitter and a median marker. Orange/blue encode positive/negative attribution, not high/low feature values. No observations are trimmed. Original feature values are unavailable. Source: figure_data/attribution_distributions.json.

**Figures S2–S5 — Eight frozen local explanations for LR, RF, XGB and LGB.** Each panel starts at the persisted model-specific base and cumulatively adds the six signed feature contributions in descending absolute magnitude (feature-name tie-break), reaching the persisted reconstructed output. Orange denotes positive contributions and blue negative contributions. Stored defect-class probabilities are displayed separately from the native explanation scale. The cases were selected before this analysis; none was reselected for visual appeal. Sources: figure_data/waterfalls_<model>.json.

All seven figures are provided as SVG and 300-dpi PNG. The four local sheets contain 32 waterfall panels. No dependence plots are produced because original feature values are absent. Additional heterogeneity and concordance results are tabulated rather than multiplying figures with overlapping information. The main manuscript has not been edited.
