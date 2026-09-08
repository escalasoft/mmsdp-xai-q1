"""Frozen-evidence and prospective-contract checks; no models or explainers."""
import ast,json,math
from pathlib import Path
import pytest
from src.evaluation import q1_primary_xai_missing_evidence_remediation as s

def read(n):return json.loads((s.OUT/n).read_text())
def rows(n):return [json.loads(x) for x in (s.OUT/n).read_text().splitlines() if x.strip()]

def test_branch_diff():
 assert s.git('symbolic-ref','--short','HEAD')==s.BRANCH
 assert s.git('diff','--check')==''

def test_parent_evidence_unchanged():
 assert read('parent_integrity_before.json')==read('parent_integrity_after.json')
 assert s.read(s.BASE/'recommended_next_action.json')['outcome']=='PARTIAL_FROZEN_EVIDENCE_REUSE_FEASIBLE'
 assert s.read(s.Q1/'q1_manuscript_xai_readiness.json')['Q1_XAI_MANUSCRIPT_READINESS']=='Q1_XAI_INSUFFICIENT_FOR_PRIMARY_MANUSCRIPT_CLAIMS'

def test_scopes_and_exclusions():
 r=read('final_xai_execution_readiness.json')
 assert r['eligible_scopes']==389
 assert {tuple(x) for x in r['excluded']}=={('apache/zeppelin','Logistic Regression',x) for x in ['C+T','P+T','C+P+T']}
 assert len(rows('e1_resolution_ledger.jsonl'))==168
 assert len(read('e2_reference_resolution.json')['scopes'])==221

def test_e1_e2_independent_not_ready():
 r=read('final_xai_execution_readiness.json')
 assert all(v['status']=='NOT_READY' for v in r['E1'].values())
 assert all(v['status']=='NOT_READY' for v in r['E2'].values())
 assert r['verdict']=='Q1_PRIMARY_XAI_EXECUTION_NOT_READY'
 assert len(read('fusion_reference_mean_resolution.json')['means'])==112

def test_mean_recipe_on_synthetic_values():
 assert s.mean([0.125,0.375])==0.25
 assert s.mean([0.0,1.0])==0.5
 with pytest.raises(ValueError):s.mean([math.nan])
 with pytest.raises(ValueError):s.mean([])

def test_mean_protocol_precedes_read_and_selection_not_adopted():
 p=read('reference_feasibility_calculation_protocol.json')
 assert p['frozen_before_probability_reads'] and p['no_favorable_reference_selection']
 assert not p['primary_population_selected']
 assert (s.OUT/'reference_feasibility_calculation_protocol.json').stat().st_mtime_ns <= (s.OUT/'fusion_reference_mean_resolution.json').stat().st_mtime_ns

def test_reference_regimes_and_exact_provenance():
 r=read('fusion_reference_mean_resolution.json')
 assert set(r['reference_classes'])=={'OOF_REFERENCE','FINAL_TRAIN_REFERENCE','SOURCE_ONLY_REFERENCE','INVALID_REFERENCE'}
 assert not r['primary_means_resolved'] and r['no_automatic_OOF_substitution']
 pairs={}
 for x in r['means']:
  assert x['source_only'] and x['rows']>0 and not x['primary_selected_reference_accepted']
  assert x['modality_order']==['C','P','T'] and len(x['membership_digest'])==64
  assert [x['mu'][k].hex() for k in ['C','P','T']]==x['mu_binary64_hex']
  assert all(len(p['sha256'])==64 for p in x['sources'])
  pairs.setdefault((x['project'],x['algorithm']),set()).add(x['reference_class'])
 assert len(pairs)==56 and all(v=={'OOF_REFERENCE','FINAL_TRAIN_REFERENCE'} for v in pairs.values())
 assert not s.reference_accepted('OOF_REFERENCE',True,True)
 assert not s.reference_accepted('FINAL_TRAIN_REFERENCE',True,False)

def test_referenced_probability_hashes_unchanged():
 r=read('TRAIN_object_integrity.json');assert r['before_sha256']==r['after_sha256']
 assert r['distinct_probability_artifacts']==224

def test_all_remediation_rows_have_provenance_and_no_unsafe_path():
 r=rows('missing_evidence_remediation_matrix.jsonl');assert len(r)==1223
 for x in r:
  assert x['status'] in s.STATUSES
  assert len(x['source_provenance']['base_manifest_sha256'])==64
  assert not any(x[k] for k in ['requires_T2_access','requires_model_query','requires_retraining','requires_T1_source_access'])
  assert 'no fuzzy mapping' in x['validation_method']
 assert sum(x['status']=='RESOLVABLE_FROM_FROZEN_EVIDENCE' for x in r)==221

def test_text_exact_mapping_contract():
 r=read('text_representation_resolution.json')
 assert r['frozen_final_TEXT_states']==56 and r['state_evidence_is_not_row_evidence']
 assert set(['vocabulary','IDF','token-column order','feature order','predictor alignment','exact row representation'])<=set(r['required'])
 assert not r['transform_or_fit_executed'] and r['current_rows']['T1']==0

def test_fusion_model_and_modality_order():
 r=read('e2_reference_resolution.json')
 for x in r['scopes']:
  assert x['modality_order']==x['configuration'].split('+')
  assert x['alpha_beta_evidence']['canonical_state_sha256']
  assert x['readiness']=='NOT_READY'
 assert r['no_inference_or_contributions']

def test_population_policies_not_executed():
 t=read('train_background_resolution.json');f=read('t1_foreground_resolution.json')
 assert t['future_policy']['max_rows_per_scope']==256 and t['future_policy']['seed']==20260901
 assert not t['population_selected']
 assert f['future_global']['max_rows_per_project']==256 and f['future_local']['max_cases_per_scope']==8
 assert not f['future_local']['strata_selected_here']

def test_fidelity_complete():
 r=read('fidelity_execution_contract.json')
 assert r['LR_fusion']['absolute_residual_bound']=='1e-10*(1+abs(eta))'
 assert r['LR_fusion']['sigmoid_absolute_bound']==1e-10
 assert r['TreeSHAP']['absolute_residual_bound']=='1e-6*(1+abs(f(x)))' and not r['TreeSHAP']['approximate']
 assert r['global_reconstruction_tolerance']==1e-12
 assert all(x=='1' for x in r['thread_controls'].values())

def test_stability_and_heterogeneity_complete():
 r=read('stability_execution_contract.json');h=read('heterogeneity_execution_contract.json')
 assert r['seeds']==list(range(20260901,20260921)) and r['deterministic_max_absolute_difference']==1e-12
 assert len(r['metrics'])==5 and not r['population_reselection_by_seed']
 assert h['cross_family_minimum']==3 and h['correlation']['absolute_threshold']==0.70
 assert h['cross_family_diagnostics']=={'top_k_Jaccard_min':0.6,'Spearman_min':0.7,'sign_agreement_min':0.8,'TV_max':0.25}
 assert len(h['categories'])==5 and h['no_family_or_scope_discard_from_diagnostics']

def test_claim_contracts_and_specific_figures():
 r=read('claim_to_evidence_contract.json')['claims']
 assert [x['claim_id'] for x in r]==[f'C{i}' for i in range(1,12)]
 assert 'FIG-XAI-9' in r[10]['required_figure_table']
 assert all(x['readiness']=='NOT_READY' and x['required_evidence'] for x in r)

def test_figure_contract_complete():
 r=read('publication_figure_data_contract.json');assert len(r['figures'])==9 and r['figures_generated']==0
 for x in r['figures']:
  assert {'source_artifact_path','population_definition','sample_size','algorithm_scope','modality_scope','project_coverage','output_scale','fidelity_status','stability_status','limitations','required_figure_specific_columns'}<=set(x)
  assert x['required_figure_specific_columns'] and not x['source_exists'] and not x['publication_ready']

def test_calibration_lime_counterfactual():
 r=read('calibration_xai_separation_contract.json')
 assert r['RAW']==375 and r['ISOTONIC']==14 and len(r['isotonic_scopes'])==14
 assert all(x['algorithm']=='LightGBM' and x['configuration']=='P' for x in r['isotonic_scopes'])
 assert r['LIME_PRIMARY_STATUS']=='EXCLUDED_FROM_PRIMARY_XAI'
 assert r['counterfactuals'].startswith('EXCLUDED')

def test_counters_and_no_execution():
 r=read('governance_counters.json');assert all(r[k]==0 for k in s.ZERO)
 assert r['TRAIN_REFERENCE_MEAN_TRIPLETS_COMPUTED']==112
 assert r['TRAIN_REFERENCE_MODALITY_MEANS_COMPUTED']==336
 assert not read('final_xai_execution_readiness.json')['Sprint56_3_authorized']

@pytest.mark.parametrize('path',['data/t2.csv','audits/q1-apachejit-final-dataset-freeze/1.0.0/code_dataset.jsonl.gz',
 'audits/q1-t1-confirmatory-execution/1.0.0/results/t1_prediction_evidence.jsonl.gz'])
def test_read_guard(path):
 with pytest.raises(PermissionError):s.guard('open',(str(s.ROOT/path),'r',0))

def test_no_forbidden_calls():
 t=ast.parse(Path(s.__file__).read_text())
 calls={n.func.attr if isinstance(n.func,ast.Attribute) else n.func.id for n in ast.walk(t) if isinstance(n,ast.Call) and isinstance(n.func,(ast.Name,ast.Attribute))}
 assert not calls & {'predict','predict_proba','decision_function','fit','fit_transform','TreeExplainer','shap_values','savefig','plot','roc_auc_score','matthews_corrcoef','reconstruct','refit','recalibrate'}

def test_manifest():
 expected={n:h for h,n in (x.split('  ',1) for x in (s.OUT/'MANIFEST.sha256').read_text().splitlines())}
 assert set(expected)=={p.name for p in s.OUT.iterdir() if p.is_file() and p.name!='MANIFEST.sha256'}
 assert all(s.sha(s.OUT/n)==h for n,h in expected.items())
