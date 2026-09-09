from pathlib import Path
import sys,subprocess,json
sys.path.insert(0,str(Path.cwd()))
from src.evaluation import q1_bounded_complementary_e1_xai as q
p=q.OUT
# Source and draft-generation persistence.
(p/'runtime').mkdir(exist_ok=True)
(p/'runtime/manuscript_generation.py').write_bytes(Path('/tmp/s56c_manuscript.py').read_bytes())
(p/'runtime/publication_table_generation_executed.py').write_bytes(Path('/tmp/s56c_publish_build.py').read_bytes())
(p/'runtime/finalize_generation.py').write_bytes(Path(__file__).read_bytes())
sources=[Path(q.__file__),q.ROOT/'src/evaluation/q1_bounded_complementary_e1_figures.py',q.ROOT/'src/evaluation/q1_bounded_complementary_e1_publication.py',q.ROOT/'tests/evaluation/test_q1_bounded_complementary_e1_xai.py']
q.save('implementation_provenance.json',dict(source_files={q.rel(x):q.sha(x) for x in sources},execution_environment='.venv-xai-s56',attribution_methods_unchanged_by_final_formatting=True,post_execution_changes=['Handle RF family-local exact explainer failure without abandoning other families','Prevent rerunning a closed execution','Format code and add focused tests'],manuscript_generator='runtime/manuscript_generation.py',table_generator_executed='runtime/publication_table_generation_executed.py'))
# Count exact nested model evaluations from the executed SHAP implementation.
c=q.read(p/'governance_counters.json')
c.update(EXPLICIT_PREDICTION_API_CALL_COUNT=5,SHAP_INTERNAL_MODEL_EVALUATION_COUNT=61,MODEL_QUERY_COUNT=66,T1_MODEL_QUERY_COUNT=66,FIGURE_GENERATION_COUNT=12,FIGURE_FILE_EXPORT_COUNT=24,UNIQUE_PUBLICATION_FIGURES=4)
c['counter_units']['MODEL_QUERY_COUNT']='5 explicit predictions + 1 RF internal prediction + 40 XGB native calls (contribution and raw margin) + 20 LGB native contribution calls'
c['counter_units']['T1_IDENTITY_ACCESS_COUNT']='751 primary-source/population row loads across materialization and two execution invocations; derived explanation/report identity reuse is separate'
c['counter_units']['T1_FEATURE_VALUE_ACCESS_COUNT']='245 raw T1 messages + two loads of the 245-row persisted T1 input matrix; rendering reads attribution results, not new inputs'
c['figure_generation_note']='Four initial figures, four title-layout repair renders, four final formatted-script renders; 12 figure calls and 24 SVG/PNG exports, four unique figures'
c['counter_scope']='Scientific source access and model/XAI operations; metadata/derived-artifact verification and rendering recorded separately'
q.save('governance_counters.json',c)
shap_source=q.ROOT/'.venv-xai-s56/lib/python3.11/site-packages/shap/explainers/_tree.py'
q.save('runtime/model_query_counter_reconciliation.json',dict(explicit_prediction_calls=5,RF_internal_prediction=1,XGB_pred_contrib_calls=20,XGB_internal_margin_calls=20,LGB_pred_contrib_calls=20,total=66,source=q.rel(shap_source),source_digest=q.sha(shap_source),source_lines=[599,607,613,711],model_loads=4,SHAP_attempts=41,SHAP_completed_valid=40,analytical_completed=20,valid_row_attributions=14700))
q.save('runtime/artifact_access_accounting.json',dict(primary_source_counters='governance_counters.json',derived_artifact_operations=['per-family all-repetition hash verification','global/local attribution aggregation','publication table generation','manuscript generation from saved results','figure rendering and visual QA','focused manifest/integrity tests'],opaque_hashing_is_not_new_feature_interpretation=True,pre_T1_transport_rows_per_source=4900,raw_sources_opened=['frozen partition identity stream prefix','frozen TEXT message stream prefix'],T2_decoded_bytes=0,T1_label_source_opened=False))
# Add RF-unavailable pair records explicitly without inventing statistics.
r=q.read(p/'e1_cross_model_consistency.json')
r['unavailable_comparisons']=[dict(family_a='RF',family_b=f,k=k,status='INSUFFICIENT_EVIDENCE',reason='RF exact additivity failure') for f in ['LR','XGB','LGB'] for k in [3,10]]
q.save('e1_cross_model_consistency.json',r)
# Separate the bounded top-10 commonality from a universal stable core claim.
h=q.read(p/'e1_explanation_heterogeneity.json');h['core_scope']='Intersection of top-10 sets in the three valid families only; RF excluded; ranking consistency thresholds do not pass';q.save('e1_explanation_heterogeneity.json',h)
# Artifact hashes precede final report use.
q.save('attributions/array_digest_registry.json',{str(x.relative_to(p)):q.sha(x) for x in sorted((p/'attributions').glob('*.npz'))})
q.save('runtime/governance_preservation_verification.json',dict(parent_before_after_equal=q.parent_snapshot()==q.read(p/'parent_integrity_before.json'),E2_unchanged=True,T2_untouched=True,T1_labels_untouched=True,retraining_refit_recalibration_tuning=False,predictive_metrics_recomputed=False,git_commit_push_PR=False,historical_T1='1/1'))
validation=dict(status='PASS_FOCUSED_WITH_INHERITED_REGRESSION_LIMITATIONS',focused=dict(passed=78,failed=0,command='PYTHONPATH=.:src .venv/bin/python -m pytest -q -p no:cacheprovider tests/evaluation/test_q1_bounded_complementary_e1_xai.py'),safe_regressions=dict(passed=383,failed=1,errors=51,deselected=1,coverage=['56.3B-R4B','56.3B-R4A','56.3B-R4','56.3B-R3','Sprint55 runtime/XAI governance','Sprint54 metadata integrity'],failure='Inherited terminal-LF serialization differences in R4; 22 mismatches all recover the expected digest by appending exactly one LF; parent unchanged',forbidden_payload_manifest_test_deselected='test_final_manifests_and_complete_chain_of_custody_verify'),initial_collection_error='Direct pytest executable omitted repository root from sys.path; corrected with PYTHONPATH=.:src and python -m pytest',ruff='PASS',git_diff_check='PASS',T2_payload_tests=False,T1_label_dependent_tests=False,visual_QA='PASS')
q.save('validation_results.json',validation)
(p/'validation_focused.log').write_bytes(Path('/tmp/s56c_focused.log').read_bytes())
(p/'reproduction_notes.md').write_text('''# Reproduction and closed execution boundary

This is a completed bounded execution. Do not rerun against the occupied namespace, start a recovery sprint, mutate parent artifacts, commit, push, or open a PR.

The preserved environment is `.venv-xai-s56` (Python 3.11.14, SHAP 0.51.0); package versions are in `e1_xai_runtime.json`. Attribution execution used one CPU thread and seeds 20260901–20260920. Figure generation uses a separate temporary Python environment whose versions are recorded in `figures/runtime.json`; it did not change the XAI environment.

In an independently authorized fresh reproduction workspace, the stages are `python -m src.evaluation.q1_bounded_complementary_e1_xai --prepare`; if and only if the documented terminal-LF gate fails, the one permitted `--prepare --bounded-repair` restores the exact expected hashes in child copies; then `--execute` executes the frozen families. The final runner records family-local exact TreeSHAP failure and proceeds with the remaining frozen families. The observed RF failure and first/remaining execution logs are retained. No model, vectorizer or tolerance change was used to repair RF.

`src/evaluation/q1_bounded_complementary_e1_publication.py` creates tables from saved valid results; `src/evaluation/q1_bounded_complementary_e1_figures.py` creates SVG and 300-dpi PNG files from those tables. Exact table and manuscript generation scripts used in this run are retained under `runtime/`. Final source hashes and the post-execution formatting/failure-handling changes are disclosed in `implementation_provenance.json`. These scripts are execution provenance, not instructions to launch new work.

Verification reads only this output package, metadata, and TRAIN parent artifacts. The root MANIFEST covers every persisted file other than itself, including the nested TRAIN-copy manifest. Parent checks are read-only. Legacy tests are not all green: the original R4 terminal-LF differences remain in place by design, and are reported rather than silently repaired in parent evidence.
''')
report='''# Sprint 56.3C — Bounded complementary E1 XAI

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
'''
(p/'SPRINT56_3C_BOUNDED_COMPLEMENTARY_E1_XAI_REPORT.md').write_text(report)
assert q.parent_snapshot()==q.read(p/'parent_integrity_before.json')
count=q.manifest();print('Manifest verified:',count,'files')
