import ast,json,subprocess
from pathlib import Path
import pytest
from src.evaluation import q1_primary_xai_alternative_design as s

def get(n):return s.read(s.OUT/n)
def test_branch_head():
 assert subprocess.check_output(['git','symbolic-ref','--short','HEAD'],text=True).strip()==s.BRANCH
 assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==s.read(s.E/'q1_execution_readiness.json')['HEAD']
def test_parent_preservation():assert s.snapshot()==get('parent_integrity_before.json')==get('parent_integrity_after.json')
def test_previous_blocker_not_rewritten():
 assert s.read(s.G/'q1_e1_rematerialization_feasibility.json')['scientific_path']=='CANONICAL_E1_REMATERIALIZATION_PATH_NOT_ESTABLISHED'
 assert s.read(s.E/'q1_execution_readiness.json')['overall']=='Q1_PRIMARY_XAI_EXECUTION_NOT_READY'
 assert get('q1_scientific_defensibility.json')['parent_readiness_not_overwritten']
def test_scope_integrity():
 d=get('e2_primary_scientific_scope.json');assert d['historical_universe']==389 and d['eligible_multimodal_scopes']==221
 assert d['configurations']=={'C+P':56,'C+T':55,'P+T':55,'C+P+T':55}
 assert d['exclusions']==s.read(s.E/'q1_execution_readiness.json')['exclusions'] and len(d['exclusions'])==3
def test_e2_unchanged():
 d=get('e2_integrity_preservation.json');assert d['status']=='PASS_PRESERVED' and d['E2_REOPEN_COUNT']==0
 for p,h in d['hashes'].items():assert s.sha(s.E/p)==h
@pytest.mark.parametrize('key',s.ZERO)
def test_zero_counters(key):assert get('governance_counters.json')[key]==0
@pytest.mark.parametrize('path',['data/T2.json','data/external/apachejit-v2/extracted/apachejit/dataset/apachejit_total.csv','audits/q1-t1-confirmatory-execution/1.0.0/results/t1_prediction_evidence.jsonl.gz'])
def test_no_payload_access(path):
 with pytest.raises(PermissionError):s.guard('open',(str(s.ROOT/path),'r',0))
def test_no_parent_write():
 with pytest.raises(PermissionError):s.guard('open',(str(s.G/'q1_primary_xai_execution_readiness.json'),'w',0))
def test_no_scientific_calls():
 t=ast.parse(Path(s.__file__).read_text());calls={n.func.attr if isinstance(n.func,ast.Attribute) else n.func.id for n in ast.walk(t) if isinstance(n,ast.Call) and isinstance(n.func,(ast.Name,ast.Attribute))}
 assert not calls&{'predict','predict_proba','decision_function','fit','partial_fit','fit_transform','transform','TreeExplainer','Explainer','shap_values','kmeans','savefig','read_csv','roc_auc_score','average_precision_score'}
def test_local_continuity_all_exact():
 good={k:True for k in s.EXACT};assert s.continuity(good)=='DIRECT'
 for k in s.EXACT:
  d={**good,k:False};assert s.continuity(d)!='DIRECT'
  d={**good,k:None};assert s.continuity(d)!='DIRECT'
 assert s.continuity({})=='NONE'
 assert s.continuity(good,'global')!='DIRECT'
def test_architecture_not_direct():
 d={'same_architecture':True,'same_modality_definitions':True};assert s.continuity(d)=='ARCHITECTURAL'
 assert s.continuity({'same_algorithm':True,'same_modality':True})=='CONCEPTUAL_ONLY'
def test_nested_only_global_with_coverage():
 d={k:True for k in ['proven_nested_population','adequate_projects','adequate_families','no_subset_bias','direction_stability_verified','same_project','same_partition','same_algorithm','same_modality','same_preprocessing','same_base_predictor','same_probability_input','same_fusion','calibration_link_exact']}
 assert s.continuity(d,'global')=='NESTED' and s.continuity(d,'local')!='NESTED'
 for k in d:assert s.continuity({**d,k:False},'global')!='NESTED'
def test_record_schema_and_identity_consistency():
 schema=get('explanation_continuity_contract.json')['candidate_record_schema'];assert len(schema['required'])==13
 record={k:'same' for k in schema['required']};record['continuity_classification']='DIRECT';e={k:True for k in s.EXACT}
 assert s.direct_record_valid(record,e)
 assert not s.direct_record_valid({**record,'row_identity':None},e)
 assert not s.direct_record_valid({**record,'e2_base_predictor_identity':'different'},e)
 assert schema['allOf'][0]['then']['properties']['row_identity']['minLength']==1
def test_candidate_records_no_false_direct():
 d=get('limited_e1_continuity.json');assert len(d['candidates'])==12
 required=set(get('explanation_continuity_contract.json')['candidate_record_schema']['required'])
 for c in d['candidates']:
  assert set(c['candidate_record'])==required
  assert c['candidate_record']['continuity_classification']=='CONCEPTUAL_ONLY'
  assert c['partition']=='TRAIN' and c['e2_primary_partition']=='T1' and not c['same_primary_local_row']
  assert not s.direct_record_valid(c['candidate_record'],{k:True for k in s.EXACT})
def test_limited_eligibility():
 d=get('historical_e1_eligibility.json');assert d['verdict']=='HISTORICAL_LIMITED_E1_ILLUSTRATIVE_ONLY'
 assert not d['primary_eligible'] and not d['secondary_inferential_eligible'] and d['rows']==80 and d['projects']==1
 assert not d['inclusion_in_preferred_primary_design']
def test_continuity_matrix():
 d=get('e1_e2_continuity_matrix.json');assert len(d['cells'])==12
 allowed={'DIRECT_CONTINUITY','NESTED_CONTINUITY','ARCHITECTURAL_CONTINUITY','CONCEPTUAL_ONLY','NOT_SUPPORTED'}
 for c in d['cells']:
  assert all(c[k] in allowed for k in ['historical_class','prospective_to_primary_historical_class','within_prospective_paired_chain'])
  assert c['within_prospective_status']=='CONDITIONAL_NOT_ESTABLISHED'
  if c['E1'] not in c['E2'].split('+'):assert c['historical_class']=='NOT_SUPPORTED'
  else:assert c['historical_class']=='CONCEPTUAL_ONLY'
def test_scale_and_interaction_boundaries():
 d=get('explanation_continuity_contract.json');assert 'cannot be multiplied by beta' in d['cross_level_scale_bridge']['warning']
 assert 'not equality' in d['composite_figure']
 assert 'no explicit pairwise' in get('e2_primary_scientific_scope.json')['interaction_policy']
def test_prospective_not_historical():
 d=get('prospective_e1_design.json');assert d['classification']=='PROSPECTIVE_COMPLEMENTARY_XAI_VALIDATION'
 assert not d['execution_authorized'] and not d['population_selected'] and d['no_historical_recovery_sprint']
 assert len(d['families'])==4
 a=get('prospective_e1_architectural_continuity.json');assert a['verdict']=='ARCHITECTURAL' and 'not empirical' in a['evidence_level']
def test_persistence_complete():
 d=get('prospective_e1_persistence_contract.json');assert d['persist_from_original_execution'] and d['not_Sprint54_recovery']
 text=' '.join(d['required_artifacts']);assert all(x in text for x in ['row identities','raw CODE/PROCESS/TEXT','transformed','preprocessors','vectorizers','predictor states','OOF','fusion','calibration','runtime','seeds','hashes','continuity'])
def test_population_options_unselected():
 d=get('prospective_population_options.json');assert len(d['options'])==4 and d['no_speed_based_choice']
 for r in d['options']:assert not r['selected'] and not r['payload_accessed'] and r['sample_size'] is None and r['viability']=='CONDITIONAL_NOT_APPROVED'
def test_stability_heterogeneity_preserved():
 d=get('xai_stability_requirements.json');assert d['seeds']==list(range(20260901,20260921)) and d['deterministic_max_absolute_difference']==1e-12
 assert 'non-discriminating' in d['E2_small_support_caveat'] and not d['results_exist']
 h=get('xai_heterogeneity_requirements.json');assert h['correlation']['absolute_threshold']==.70 and not h['results_exist']
 assert h['cross_family_diagnostics']=={'top_k_Jaccard_min':.60,'Spearman_min':.70,'sign_agreement_min':.80,'TV_max':.25}
def test_figure_design_not_results():
 a=get('xai_figure_design_registry.json');assert len(a['figures'])==11 and a['design_ready_is_not_result_ready']
 assert all(not f['publication_result_ready'] for f in a['figures'])
 f=next(f for f in a['figures'] if f['id']=='FIG-XAI-10');assert f['classification']=='PROSPECTIVE_VALIDATION_REQUIRED' and 'never splice' in f['continuity_limit']
def test_claim_boundaries():
 d=get('scientific_claim_ledger.json');assert len(d['claims'])>=10 and d['SUPPORTED_NOW_empirical_claims']==0
 for c in d['claims']:
  if c['claim_id'] in ['C3','C5','C9','C10','C11']:assert c['classification']=='NOT_SUPPORTED'
def test_alternatives_and_selection():
 d=get('alternative_design_matrix.json');assert len(d['alternatives'])==6
 assert [r['alternative'] for r in d['alternatives'] if r['selected']]==['C']
 for r in d['alternatives']:
  assert len(r['ordinal_assessment'])==9
  if r['alternative'] in ['E','F']:assert r['hard_gate']=='REJECT'
 assert d['no_total_score_or_speed_optimization']
def test_thesis_and_manuscript():
 assert get('xai_manuscript_section_readiness.json')['no_empirical_XAI_results_yet']
 t=get('xai_thesis_framework_continuity.json');assert t['coherent_design'] and not t['empirically_complete']
def test_next_action_not_execution():
 d=get('exact_next_execution_path.json');assert d['recommendation']=='Sprint56.3A — Prospective Complementary E1 Protocol Freeze'
 assert not d['start_authorized'] and d['no_historical_recovery_sprint'] and d['no_T2_use']
 assert get('recommended_xai_architecture.json')['verdicts']==s.VERDICTS
 assert get('q1_scientific_defensibility.json')['verdict']=='ALT_XAI_DESIGN_Q1_VIABLE_WITH_PREDECLARED_LIMITATIONS'
def test_manifest():
 for l in (s.OUT/'MANIFEST.sha256').read_text().splitlines():
  h,n=l.split('  ',1);assert s.sha(s.OUT/n)==h

def test_diff():assert subprocess.run(['git','diff','--check'],capture_output=True).returncode==0
