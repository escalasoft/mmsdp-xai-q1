import ast,subprocess
from pathlib import Path
import pytest
from src.evaluation import q1_primary_xai_canonical_rematerialization_feasibility as s

def get(n):return s.read(s.OUT/n)
def rows(n):return s.rows(s.OUT/n)
def test_branch_head():
 assert subprocess.check_output(['git','symbolic-ref','--short','HEAD'],text=True).strip()==s.parent.BRANCH
 assert get('q1_primary_xai_execution_readiness.json')['HEAD']==s.read(s.E/'q1_execution_readiness.json')['HEAD']
def test_parent_preservation():assert s.snapshot()==get('parent_integrity_before.json')==get('parent_integrity_after.json')
def test_scope_integrity():
 d=get('q1_primary_xai_execution_readiness.json');assert d['scope_count']==389 and len(d['exclusions'])==3
 assert d['exclusions']==s.read(s.E/'q1_execution_readiness.json')['exclusions']
 assert not d['Sprint56_3_authorized'] and d['not_a_SHAP_runtime_failure']
def test_E2_preserved():
 d=get('e2_integrity_preservation.json');assert d['status']=='PASS_PRESERVED' and d['E2_REOPEN_COUNT']==0
 for n,h in d['files_sha256'].items():assert s.sha(s.E/n)==h
@pytest.mark.parametrize('counter',s.ZERO)
def test_zero_counters(counter):assert get('governance_counters.json')[counter]==0
@pytest.mark.parametrize('path',['data/external/apachejit-v2/extracted/apachejit/dataset/apachejit_total.csv','audits/q1-apachejit-final-dataset-freeze/1.0.0/row_identity_provenance.jsonl.gz','audits/q1-apachejit-final-dataset-freeze/1.0.0/text_dataset.jsonl.gz','data/T2.json'])
def test_payload_denied(path):
 with pytest.raises(PermissionError):s.guard('open',(str(s.ROOT/path),'r',0))
def test_parent_write_denied():
 with pytest.raises(PermissionError):s.guard('open',(str(s.E/'q1_execution_readiness.json'),'w',0))
def test_no_execution():
 t=ast.parse(Path(s.__file__).read_text());calls={n.func.attr if isinstance(n.func,ast.Attribute) else n.func.id for n in ast.walk(t) if isinstance(n,ast.Call) and isinstance(n.func,(ast.Name,ast.Attribute))}
 assert not calls&{'predict','predict_proba','decision_function','fit','partial_fit','fit_transform','transform','TreeExplainer','Explainer','shap_values','kmeans','fillna','dropna','savefig','read_csv','roc_auc_score','average_precision_score'}
def test_canonical_classification():
 a=rows('canonical_source_registry.jsonl');assert len(a)==9
 assert sum(r['canonical_classification']=='T2_BOUNDARY_UNSAFE' for r in a)==7
 assert sum(r['canonical_classification']=='CANONICAL_WITH_LIMITATION' for r in a)==1
 assert not any(r['canonical_classification']=='CANONICAL_ACCEPTED' or r['payload_opened'] for r in a)
 for r in a:assert all(k in r for k in ['source_name','source_path','source_type','provenance_origin','creation_stage','project_coverage','temporal_coverage','row_identity_semantics','modality_coverage','scientific_schema','source_sha256','parent_artifact_linkage','predates_T1_evaluation','contains_T2','T2_physically_avoidable'])
 derivative=next(r for r in a if r['canonical_classification']=='NONCANONICAL');assert derivative['project_coverage']==['apache/activemq'] and not derivative['predates_T1_evaluation']
def test_hash_provenance():
 for r in rows('canonical_source_provenance.jsonl'):assert s.sha(s.ROOT/r['parent_artifact'])==r['parent_hash']
def test_identity_routing_gate():
 assert s.routing_admitted(True,True,True)
 for a in [(False,True,True),(True,False,True),(True,True,False)]:assert not s.routing_admitted(*a)
 assert not any(r['admitted_full_replay'] for r in rows('canonical_source_routing_safety.jsonl'))
def test_one_way_identity_not_inverted():
 a=rows('frozen_identity_source_linkage.jsonl');assert len(a)==14
 assert all(r['canonical_commit_bridge_status']=='UNRESOLVED' and not r['outcome_based_lookup'] for r in a)
def test_original_feature_definitions():
 a=rows('code_feature_definition_registry.jsonl');b=rows('process_feature_definition_registry.jsonl')
 assert [r['feature_name'] for r in a]==['la','ld','nf','nd','ns','ent']
 assert [r['feature_name'] for r in b]==['ndev','age','nuc','aexp','arexp','asexp']
 for r in a:assert 'Copy' in r['computation_formula/rule'] and r['reproducibility_status'].startswith('NOT_REMATERIALIZABLE')
 for r in b:assert r['classification']=='SEMANTICS_UNRESOLVED' and r['cutoff_rule']=='Strict ancestors, current commit excluded'
def test_process_no_substitute():
 a=rows('implementation_traceability.jsonl');assert any(r.get('function')=='generate_process_features' and 'NOT the six' in r['configuration'] for r in a)
 assert all(r['numeric_value_source']=='APACHEJIT_V2_FROZEN_BENCHMARK_FEATURE' for r in rows('process_feature_definition_registry.jsonl'))
def test_text_contract():
 d=get('text_representation_contract.json');assert d['raw_text_vs_vectorizer_distinct'] and not d['new_text_read']
 assert all(k in d['vectorizer'] for k in ['vocabulary','IDF','token_pattern','lowercase','ngram_range','norm','min_df','max_features','sublinear_tf','token-column'])
def test_coverage_honest():
 for p in ['train','t1']:
  d=get(f'{p}_canonical_coverage.json');assert len(d['records'])==42
  assert sum(r['expected_rows'] for r in d['records'])==3*d['expected_unique_partition_rows']
  assert all(r['unresolved_rows']==r['expected_rows'] and r['source_resolvable_rows']==0 for r in d['records'])
  for r in d['records']:
   if r['modality']=='TEXT':assert r['exact_message_matches'] is None and r['missing_messages'] is None and r['ambiguous_messages'] is None
 assert get('train_canonical_coverage.json')['prior80_derivative_preserved_separately']
def test_nan_inf_unknown():
 a=rows('missing_value_semantics.jsonl');assert len(a)==364
 for r in a:
  assert r['NaN'] is None and r['positive_inf'] is None and r['negative_inf'] is None
  assert r['classification']=='MISSING_SEMANTICS_UNRESOLVED'
 assert get('governance_counters.json')['MISSING_VALUE_CASE_COUNT'] is None
 assert get('governance_counters.json')['MISSING_SEMANTICS_CONTRADICTION_COUNT']==0
def test_deterministic_conditional_contract():
 d=get('canonical_replay_contract.json');assert d['status']=='BLOCKED_NO_EXECUTABLE_SAFE_FULL_ROUTE' and d['no_model_query'] and d['no_replay_authorized']
 assert len(get('canonical_replay_order.json')['order'])==6
def test_equivalence_terminology():
 d=get('rematerialization_equivalence_hierarchy.json');assert list(d['levels'])==[f'R{i}' for i in range(1,8)]
 assert 'SEMANTIC_AND_PROCEDURAL_REPRODUCTION' in d['without_historical_X']
 assert 'historical byte' in d['forbidden_claim']
def test_manuscript_boundary():
 t=(s.OUT/'manuscript_rematerialization_rationale.md').read_text();assert all(k in t for k in ['A:','B:','C:','NOT currently true','not recovery'])
def test_kmeans_and_sampling_deferred():
 d=get('future_background_reduction_policy.json');assert d['KMEANS_BACKGROUND_STATUS']=='DEFERRED_UNTIL_FULL_BACKGROUND_UNIVERSE_IS_ESTABLISHED'
 assert not d['kmeans_executed'] and not d['KernelSHAP_substitution']
 for n in ['shap_background','t1_foreground']:assert not get(f'future_{n}_readiness.json')['selection_executed']
def test_path_gate_and_next_action():
 d=get('q1_e1_rematerialization_feasibility.json');assert d['scientific_path']==s.PATH_VERDICT
 assert all(v.endswith('NOT_FEASIBLE') for v in d['modalities'].values())
 n=get('recommended_next_action.json');assert n['decision']=='STOP_REPEATED_ARTIFACT_RECOVERY_ATTEMPTS' and not n['Sprint56_2H_full_rematerialization_recommended'] and not n['T2_relaxation_recommended']
def test_manifest():
 for l in (s.OUT/'MANIFEST.sha256').read_text().splitlines():
  h,n=l.split('  ',1);assert s.sha(s.OUT/n)==h

def test_diff():assert subprocess.run(['git','diff','--check'],capture_output=True).returncode==0
