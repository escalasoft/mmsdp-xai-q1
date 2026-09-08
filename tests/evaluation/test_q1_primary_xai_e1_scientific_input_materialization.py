import ast,json,subprocess
from pathlib import Path
import pytest
from src.evaluation import q1_primary_xai_e1_scientific_input_materialization as s

def get(n):return s.read(s.OUT/n)
def rows(n):return s.rows(s.OUT/n)
def test_branch_and_head():
 assert subprocess.check_output(['git','symbolic-ref','--short','HEAD'],text=True).strip()==s.BRANCH
 assert get('q1_primary_xai_execution_readiness.json')['HEAD']==s.read(s.E/'q1_execution_readiness.json')['HEAD']
def test_parent_bytes():assert s.snapshot()==get('parent_integrity_before.json')==get('parent_integrity_after.json')
def test_scope_and_exclusions():
 d=get('q1_primary_xai_execution_readiness.json');assert d['eligible_scopes']==389
 assert d['exclusions']==s.read(s.E/'q1_execution_readiness.json')['exclusions'] and len(d['exclusions'])==3
 assert len(rows('e1_materialization_ledger.jsonl'))==168
def test_e2_bytes_and_no_reopen():
 d=get('e2_integrity_preservation.json');assert d['status']=='PASS_PRESERVED' and d['E2_REOPEN_COUNT']==0
 assert set(d['files_sha256'])=={'e2_final_train_reference_audit.json','e2_fusion_decomposition_readiness.json','e2_oof_reference_audit.json','e2_primary_reference_decision.json','e2_reference_candidate_ledger.jsonl','e2_reference_means.jsonl','e2_source_only_reference_audit.json'}
 for n,h in d['files_sha256'].items():assert s.sha(s.E/n)==h
@pytest.mark.parametrize('key',s.ZERO)
def test_prohibited_counters_zero(key):assert get('governance_counters.json')[key]==0
@pytest.mark.parametrize('p',['data/mixed.csv','data/T2.json','audits/q1-t1-confirmatory-execution/1.0.0/results/t1_prediction_evidence.jsonl.gz'])
def test_source_guard(p):
 with pytest.raises(PermissionError):s.guard('open',(str(s.ROOT/p),'r',0))
def test_parent_write_guard():
 with pytest.raises(PermissionError):s.guard('open',(str(s.E/'q1_execution_readiness.json'),'w',0))
def test_no_inference_or_fit_code():
 t=ast.parse(Path(s.__file__).read_text());calls={n.func.attr if isinstance(n.func,ast.Attribute) else n.func.id for n in ast.walk(t) if isinstance(n,ast.Call) and isinstance(n.func,(ast.Name,ast.Attribute))}
 assert not calls&{'predict','predict_proba','decision_function','fit','fit_transform','TreeExplainer','Explainer','shap_values','savefig','roc_auc_score','average_precision_score','matthews_corrcoef'}
 transforms=[n for n in ast.walk(t) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='transform']
 assert len(transforms)==2 and all(ast.unparse(n.func.value)=='pipeline[:-1]' for n in transforms)
def test_preflight_before_outputs():
 p=s.OUT/'source_admission_before_payload.json'
 assert all(p.stat().st_mtime_ns<x.stat().st_mtime_ns for x in s.OUT.glob('*.matrix.json'))
 assert get('source_admission_before_payload.json')['source_partition_scope']=='TRAIN_ONLY'
def test_source_hash_and_membership_proof():
 proof=get('source_admission_before_payload.json');pop=s.read(s.SMOKE/'train_only_population_manifest.json')
 assert proof['expected_sha256']==pop['rows_sha256']==s.sha(s.ROOT/proof['source_identity'])
 assert pop['non_TRAIN_rows_read']==0
 for r in rows('partial_matrix_records.jsonl'):
  assert len(r['row_ids'])==len(set(r['row_ids']))==80
  assert set(r['row_ids'])<=set(pop['train_ids_chronological'])
  assert r['row_identity_sha256']==s.digest(r['row_ids']) and r['project']=='apache/activemq' and r['partition']=='TRAIN'
def test_matrix_metadata_and_custody():
 for r in rows('partial_matrix_records.jsonl'):
  p=s.ROOT/r['output_artifact'];m=s.read(p);assert s.sha(p)==r['output_hash']==r['model_input_representation_identity']
  assert m['row_ids']==r['row_ids'] and m['feature_names']==r['feature_order'] and m['partition']=='TRAIN'
  assert s.digest(m['X'])==r['values_hash'] and m['X']['shape']==r['shape'] and m['X']['dtype']==r['dtype']
  assert r['preprocessing_hash']==s.digest(r['preprocessing_identity'])
  assert r['column_identity_sha256']==s.digest(r['feature_order'])
  assert r['transformation_contract_hash']==s.sha(s.OUT/'transformation_contract.json')
def test_schema_and_modalities():
 for r in rows('partial_matrix_records.jsonl'):
  if r['modality'] in ['C','P']:assert r['feature_order']==s.FEATURES[r['modality']] and r['shape']==[80,6]
  else:assert r['shape']==[80,2557] and r['format']=='CSR'
def test_text_exact_state():
 for r in rows('partial_matrix_records.jsonl'):
  if r['modality']!='T':continue
  t=r['text'];assert len(t['vocabulary'])==len(t['idf'])==2557
  assert t['vocabulary_hash']==s.digest(t['vocabulary']) and t['token_column_mapping']==t['vocabulary']
  assert all(t['token_column_mapping'][n]==i for i,n in enumerate(r['feature_names']))
  assert {'token_pattern','lowercase','ngram_range','min_df','max_features','norm','sublinear_tf'}<=set(t)
  assert t['idf_hash']==r['preprocessing_identity']['idf']['sha256']
def test_model_alignment():
 for r in rows('partial_matrix_records.jsonl'):
  d=r['model_alignment'];assert d['n_features_in']==r['shape'][1] and d['class_order']==[0,1] and not d['model_query']
  if r['algorithm']=='Logistic Regression':assert d['coefficient_shape']==[1,r['shape'][1]]
  if r['algorithm'] in ['XGBoost','LightGBM']:assert d['output_scale']=='NATIVE_RAW_MARGIN'
def test_process_temporal_limits_honest():
 d=get('transformation_contract.json')['PROCESS_semantics'];assert set(d)=={'event_cutoff','ancestor_scope','aggregation_semantics','proof_limit'}
 assert 'not reconstructed' in d['ancestor_scope'] and 'not independently' in d['proof_limit']
 assert get('e1_process_materialization.json')['status']=='E1_PROCESS_Q1_NOT_READY'
def test_repeat_not_historical_equivalence():
 eq=rows('e1_representation_equivalence.jsonl');assert sum(r['exact_repeat'] for r in eq)==12
 assert all(r['historical_X_equality'] is None for r in eq)
 assert all(r['equivalence_status']=='EXACT_REPEAT_PASS_HISTORICAL_X_REFERENCE_UNAVAILABLE' and not r['historical_equivalence_claim'] for r in rows('partial_matrix_records.jsonl'))
def test_object_bytes_unchanged():
 d=get('read_object_integrity.json');assert d['before']==d['after']
 for p,h in d['before'].items():assert s.sha(s.ROOT/p)==h
def test_scientific_vs_model_input_identity():
 a=rows('partial_matrix_records.jsonl');assert len({r['scientific_input_identity'] for r in a})==3
 assert len({r['model_input_representation_identity'] for r in a})>3
 assert not any(r['full_universe'] or r['q1_ready'] for r in a)
def test_coverage_no_hidden_rows():
 for name in ['train','t1']:
  d=get(f'e1_{name}_materialization_coverage.json');assert len(d['scope_records'])==168
  assert sum(r['expected_rows'] for r in d['scope_records'])==d['expected_rows']
  assert sum(r['materialized_rows'] for r in d['scope_records'])==d['materialized_rows']
  for r in d['scope_records']:assert r['expected_rows']==r['materialized_rows']+r['missing_rows']
 assert get('e1_train_materialization_coverage.json')['materialized_rows']==960
 assert get('e1_t1_materialization_coverage.json')['materialized_rows']==0
 for m in ['code','process','text']:
  d=get(f'e1_{m}_materialization.json');assert d['expected_projects']==14 and d['expected_algorithms']==4 and d['expected_project_algorithm_scopes']==56
  assert d['fully_recovered_scopes']==0 and d['partially_materialized_scopes']==4
def test_counter_units():
 d=get('governance_counters.json');assert d['REPRESENTATION_MATERIALIZATION_COUNT']==12 and d['REPRESENTATION_EQUIVALENCE_CHECK_COUNT']==12
 assert d['TEXT_FROZEN_VECTORIZER_APPLICATION_COUNT']==8 and d['NUMERIC_FROZEN_PREPROCESSOR_APPLICATION_COUNT']==16
 assert d['UNIQUE_TRAIN_ROWS_MATERIALIZED']==80
 assert d['E1_SOURCE_CANDIDATES_AUDITED']==d['E1_SOURCES_ACCEPTED']+d['E1_SOURCES_REJECTED']==5
def test_missingness_gate():
 assert get('e1_missingness_analysis.json')['pattern']=='SYSTEMATIC_MISSINGNESS'
 assert get('q1_primary_xai_execution_readiness.json')['overall']==s.VERDICT
 assert not get('q1_primary_xai_execution_readiness.json')['Sprint56_3_authorized']
def test_future_sampling_not_done():
 for n,mx in [('shap_background',256),('t1_foreground',256),('local_case',8)]:
  d=get(f'future_{n}_readiness.json');assert d['status']=='NOT_READY' and d['max_rows']==mx and not d['selection_performed']
def test_graphs_not_promoted():
 for f in get('publication_graph_input_readiness.json')['figures']:
  assert not f['publication_ready']
  if f['status']=='INPUT_READY_WITH_PREDECLARED_LIMITATION':assert 'E2 only' in f['scope']
def test_storage_policy():
 assert not get('output_size_audit.json')['greater_than_25MB'] and not get('output_size_audit.json')['greater_than_50MB']
 assert all(p.stat().st_size<25_000_000 for p in s.OUT.iterdir() if p.is_file())
 assert len(list(s.OUT.glob('*.matrix.json')))<12
 assert not list(s.OUT.glob('*.joblib'))
def test_warnings_recorded():assert get('exact_load_warnings.json')==[]
def test_manifest():
 for l in (s.OUT/'MANIFEST.sha256').read_text().splitlines():
  h,n=l.split('  ',1);assert s.sha(s.OUT/n)==h

def test_diff():assert subprocess.run(['git','diff','--check'],capture_output=True).returncode==0
