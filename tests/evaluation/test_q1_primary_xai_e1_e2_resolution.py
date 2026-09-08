import ast
import hashlib
import json
import subprocess
from pathlib import Path
import pytest
from src.evaluation import q1_primary_xai_e1_e2_resolution as s

def get(n):return s.read(s.OUT/n)
def records(n):return s.rows(s.OUT/n)
def test_branch():assert subprocess.check_output(['git','symbolic-ref','--short','HEAD'],text=True).strip()==s.BRANCH
def test_parent_bytes():assert s.snapshot()==get('parent_integrity_before.json')==get('parent_integrity_after.json')
def test_parent_outcomes():
 assert s.read(s.D/'final_xai_execution_readiness.json')['verdict']==s.VERDICT
 assert s.read(s.BASE/'recommended_next_action.json')['outcome']=='PARTIAL_FROZEN_EVIDENCE_REUSE_FEASIBLE'
 assert s.read(s.parent.Q1/'q1_manuscript_xai_readiness.json')['Q1_XAI_MANUSCRIPT_READINESS']=='Q1_XAI_INSUFFICIENT_FOR_PRIMARY_MANUSCRIPT_CLAIMS'
def test_scopes():
 d=get('q1_execution_readiness.json');assert d['scope_count']==389
 assert d['exclusions']==s.read(s.BASE/'scope_integrity.json')['excluded'] and len(d['exclusions'])==3
 assert len(records('e1_input_recovery_ledger.jsonl'))==168
 assert len(get('e2_primary_reference_decision.json')['scopes'])==221
@pytest.mark.parametrize('path',['data/mixed.csv','audits/q1-t1-confirmatory-execution/1.0.0/results/t1_prediction_evidence.jsonl.gz','data/T2.json'])
def test_payload_guard(path):
 with pytest.raises(PermissionError):s.guard('open',(str(s.ROOT/path),'r',0))
def test_parent_write_guard():
 with pytest.raises(PermissionError):s.guard('open',(str(s.D/'final_xai_execution_readiness.json'),'w',0))
def test_no_execution_calls():
 t=ast.parse(Path(s.__file__).read_text());forbidden={'predict','predict_proba','decision_function','fit','fit_transform','transform','TreeExplainer','Explainer','shap_values','savefig','roc_auc_score','average_precision_score','f1_score','matthews_corrcoef'}
 calls={n.func.attr if isinstance(n.func,ast.Attribute) else n.func.id for n in ast.walk(t) if isinstance(n,ast.Call) and isinstance(n.func,(ast.Name,ast.Attribute))}
 assert not calls&forbidden
 imports=[n for n in ast.walk(t) if isinstance(n,(ast.Import,ast.ImportFrom))]
 assert not any('shap' in ast.unparse(n) or 'sklearn' in ast.unparse(n) for n in imports)
def test_all_prohibited_counters_zero():assert all(get('governance_counters.json')[k]==0 for k in s.ZERO)
def test_identity_and_state_linkage():
 journal={r['logical_id']:r for r in s.rows(s.STORE/'repetitions/rep_01/component_journal.jsonl')}
 for r in records('e1_input_recovery_ledger.jsonl'):
  st=journal[f"{r['project']}|{r['algorithm']}|FINAL_BASE|{r['modality']}"]
  assert r['model_identity_sha256'] in st['canonical_state']['provenance']['consuming_model_identity_sha256']
  assert r['preprocessing_state']==st['canonical_state']['preprocessing'] and r['predictor_state']==st['executable']
def test_exact_schema():
 for r in records('e1_input_recovery_ledger.jsonl'):
  if r['modality']=='C':assert r['feature_names']==['la','ld','nf','nd','ns','ent']
  if r['modality']=='P':assert r['feature_names']==['ndev','age','nuc','aexp','arexp','asexp']
def test_text_not_promoted():
 d=get('e1_text_resolution.json');assert d['status']==s.NOT and d['no_fit_or_transform']
 assert set(['vocabulary','idf','token_pattern','lowercase','ngram_range','min_df','max_features','norm','sublinear_tf'])<=set(d['TEXT_required'])
 assert all(r['text_alignment_status']=='STATE_AVAILABLE_ROWS_INCOMPLETE' for r in d['scope_records'])
def test_coverage_counts():
 for p in ['train','t1']:
  d=get(f'e1_{p}_coverage.json');assert len(d['records'])==168
  assert sum(r['total_rows'] for r in d['records'])==d['total_expected']
  assert sum(r['recoverable_rows'] for r in d['records'])==d['total_recoverable']
  for r in d['records']:assert r['total_rows']==r['recoverable_rows']+r['unrecoverable_rows']
 assert get('e1_train_coverage.json')['unique_recoverable_source_rows']==80
 assert get('e1_t1_coverage.json')['total_recoverable']==0
def test_path_priority():
 for r in records('e1_input_recovery_ledger.jsonl'):
  assert list(r['path_evaluation'])==list('ABCDEF') and r['recovery_path']=='F' and r['q1_scientific_status']=='Q1_NOT_READY'
def test_no_fuzzy_mapping():
 assert 'fuzzy' not in {n.func.attr for n in ast.walk(ast.parse(Path(s.__file__).read_text())) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)}
 assert all('Exact historical' in r['row_identity_method'] for r in records('e1_input_recovery_ledger.jsonl'))
def test_reference_rule_fail_closed():
 assert s.primary_reference('TEMPORAL_OOF',True,True)=='PRIMARY_REFERENCE_OOF'
 for a in [('FINAL_TRAIN',True,True),('TEMPORAL_OOF',False,True),('TEMPORAL_OOF',True,False)]:assert s.primary_reference(*a)=='REFERENCE_UNRESOLVED'
def test_decision_frozen_before_mean():
 assert (s.OUT/'prospective_resolution_policy.json').stat().st_mtime_ns<(s.OUT/'e2_reference_means.jsonl').stat().st_mtime_ns
 d=get('prospective_resolution_policy.json');assert d['pre_XAI_prospective_decision'] and d['full_OOF_reference_not_E1_background']
def test_oof_forward_membership():
 a=get('e2_oof_reference_audit.json');assert len(a['pairs'])==56
 assert len({x['project'] for x in a['pairs']})==14
 for x in a['pairs']:
  assert sum(f['prediction_count'] for f in x['fold_lineage'])==x['rows']
  assert all(f['strict_forward_and_disjoint'] and max(f['fit_blocks'])<f['prediction_block'] for f in x['fold_lineage'])
  assert x['warmup_classification']=='EXPECTED_BY_DESIGN_NOT_META_TRAINING_MEMBER'
def test_mean_recipe():
 assert s.mean([.125,.375])==.25
 for v in [[],[float('nan')],[-.1],[1.1]]:
  with pytest.raises(ValueError):s.mean(v)
def test_means_match_parent_and_digests():
 a=records('e2_reference_means.jsonl');assert len(a)==168
 for r in a:
  assert r['mu'].hex()==r['mu_hex'] and 0<=r['mu']<=1 and r['repeat_exact'] and r['parent56_2D_exact_match']
  assert all(len(r[k])==64 for k in ['sorted_identity_digest','ordered_identity_digest','probability_vector_sha256','mean_sha256'])
  assert r['source_partition']=='TRAIN_META_OOF'
def test_oof_objects_unchanged():
 d=get('read_objects_integrity.json');assert d['before']==d['after'] and len(d['before'])==56
 for p,h in d['before'].items():assert s.sha(s.ROOT/p)==h
def test_e2_scope_order_and_membership():
 d=get('e2_primary_reference_decision.json');assert d['resolved']==221 and d['unresolved']==0
 for r in d['scopes']:
  assert r['modality_order']==r['configuration'].split('+')
  assert [m['modality'] for m in r['primary_mean_records']]==r['modality_order']
  assert all(m['ordered_identity_digest']==r['meta_training_membership_sha256'] for m in r['primary_mean_records'])
  assert r['future_symbolic_decomposition_ready'] and r['q1_status']==s.LIMITED
  assert r['alpha_available']['shape']==[1] and r['beta_available']['shape']==[1,len(r['modality_order'])]
def test_final_train_secondary():
 d=get('e2_final_train_reference_audit.json');assert d['status']=='SECONDARY_REFERENCE_ONLY' and d['in_sample'] and not d['used_as_meta_fit_input']
def test_source_only_distinctness():assert get('e2_source_only_reference_audit.json')['classification']=='NO_DISTINCT_BETTER_REFERENCE_ESTABLISHED'
def test_e1_e2_independent():
 d=get('q1_execution_readiness.json');assert set(d['E1'].values())=={s.NOT} and set(d['E2'].values())=={s.LIMITED} and d['overall']==s.VERDICT
 assert not d['Sprint56_3_authorized'] and not d['primary_execution_authorized']
def test_graphs_honest():
 for f in get('publication_graph_input_readiness.json')['figures']:
  assert not f['publication_ready'] and f['population_not_selected']
  if f['status']=='INPUTS_READY_WITH_LIMITATION':assert 'E2 only' in f['scope']
def test_no_false_equivalence_pass():
 assert all(r['passed'] is None for r in records('representation_equivalence_ledger.jsonl'))
def test_manifest():
 for line in (s.OUT/'MANIFEST.sha256').read_text().splitlines():
  h,p=line.split('  ',1);assert s.sha(s.OUT/p)==h
def test_diff():assert subprocess.run(['git','diff','--check'],capture_output=True).returncode==0
