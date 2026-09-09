# Sprint 56.3C — Bounded complementary E1 XAI

**56_3C_PASS_BOUNDED_E1_XAI_WITH_PREDECLARED_LIMITATIONS**

Branch: `sprint-10/q1-bounded-complementary-e1-xai`
HEAD: `4220e31de426e3defe5392cf6f8ae40e9fb2b022` (PR #121; includes `a438dee`).

## Scientific result

The bounded ActiveMQ TEXT case study produced faithful feature-level explanations for LR, XGBoost and LightGBM. All four frozen families were attempted; RF exact TreeSHAP failed its internal additivity check and no RF attribution was published. The exclusion follows the predeclared fidelity policy, not predictive performance. E2 remains primary and unchanged. This is not full-modality or multi-project feature-level coverage.

TRAIN contains 3,675 rows × 2,557 features. Five inherited representation text files lacked one terminal LF. The single bounded repair appended that byte in child copies only and reproduced every expected representation hash exactly; the CSR matrix was never regenerated. The verified frozen vectorizer transformed the 245 authorized T1 messages without refitting. One replay reproduced dtype, CSR values/indices/indptr, row order, column order and digests exactly. The frozen populations contain 256 TRAIN background identities, all 245 T1 foreground identities and eight shared local cases.

| Family | Status | Leading three features | Maximum fidelity residual | Stability |
| --- | --- | --- | --- | --- |
| LR | Valid centered analytical logit decomposition | svn; issues; amq | 1.3323e-15 | Exact, 20 seeds |
| RF | Excluded: exact TreeSHAP additivity failure | Not available | Internal check failed | Not evaluated |
| XGB | Valid exact native-margin TreeSHAP | amq; issues; browse | 1.6689e-6 | Exact, 20 seeds |
| LGB | Valid exact native-margin TreeSHAP | id; amq; browse | 1.0183e-12 | Exact, 20 seeds |

All 14,700 valid row/repetition attribution checks passed their output-dependent frozen tolerances. XGB's residual is judged against 1e-6 × (1+|output|), not an absolute 1e-6 threshold. Each valid family has 190 pairwise repetition comparisons with zero maximum attribution difference and zero normalized total variation. Stability concerns fixed populations only.

Top-10 Jaccard is 0.538 for LR–XGB, 0.667 for LR–LGB and 0.429 for XGB–LGB. No pair meets all frozen overlap/rank/sign thresholds. The outcome is MODEL_DEPENDENT_EXPLANATIONS with partial top-10 overlap. Six literal tokens appear in all three valid top-10 sets: amq, browse, id, incubator, issues and test. This does not establish a universal shared ranking or a causal mechanism.

## Publication package

The package contains full rankings (7,671 family-feature records), top-10/top-20 tables, 24 local explanations, complete attribution arrays for all 60 valid family/repetition executions, baselines, fidelity and stability diagnostics, six valid cross-model comparisons plus explicit unavailable RF pairs, architectural E1/E2 traceability, four figures in SVG/PNG with hashed source tables, captions, five principal publication tables and supporting tables in CSV/JSON/Markdown, Results/Discussion/limitations drafts and a reviewer response.

E1/E2 continuity is architectural and traceable by frozen model/scope references. No exact historical same-row probability linkage was remeasured and no E1 attribution was algebraically propagated into E2. Both predictors and representations remain RECONSTRUCTED. The Q1 assessment is Q1_BOUNDED_E1_COMPLEMENTARY_EVIDENCE_VIABLE_WITH_LIMITATION.

## Governance and validation

T1 primary-source/population row-load counters: metadata 1; identity 751; feature-value 735; labels 0. Repeated persisted matrix loads are counted. There were four model loads, five explicit prediction calls, 61 nested SHAP model evaluations (66 total model-query calls), 41 SHAP attempts (40 valid, one failed RF attempt), 20 analytical executions and 14,700 valid row attribution vectors. Twelve rendering calls produced four unique figures and 24 format exports during visual QA. Derived-artifact reporting and opaque hash verification are distinguished from new scientific input access.

All T2 access/identity/feature/label/model-query counters remain zero. TRAIN/VALIDATION prefix traversal occurs only in the label-free ActiveMQ transport prefix, with byte-at-a-time, output-limited decompression stopping at the last T1 newline. No T2 decoded byte was requested. T1 labels were not read. Retraining, refit, recalibration, tuning, selection, predictive metric recomputation, E2 recomputation and E2 mutation remain zero. Historical Sprint54 T1 predictive execution remains 1/1.

The 78 focused tests pass; Ruff and git diff --check pass. Safe inherited regressions: 383 pass, one fails and 51 error from inherited R4 terminal-LF digest discrepancies. Twenty-two R4 parent-manifest mismatches were diagnosed read-only; each matches its expected hash with precisely one additional LF. The broader parent package was not repaired. The excluded Sprint54 full-chain payload-manifest test was not run. An initial test collection path error was corrected without changing scientific evidence. All selected parent files and E2 hashes are unchanged before/after.

## Final decision and next action

The results are reportable under the predeclared family-exclusion and bounded-scope policies, with explicit RF, serialization, scale, fixed-population stability and architectural-continuity limitations. The package is ready for human scientific review; it does not claim a clean legacy regression suite.

Next action: **MANUSCRIPT_XAI_INTEGRATION** — integrate frozen primary E2 results, bounded LR/XGB/LGB E1 tables/figures, final Results, Discussion and Threats to Validity, and consolidate the framework figure. No source recovery, R4C, additional 56.3C sprint, commit, push or PR was started.

READY FOR HUMAN REVIEW — BOUNDED COMPLEMENTARY E1 XAI IS REPORTABLE WITH PREDECLARED LIMITATIONS
