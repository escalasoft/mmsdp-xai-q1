"""Checks manuscript classification against the frozen audit, not source data."""
import ast
import json
from pathlib import Path
import pytest
from src.evaluation import q1_primary_xai_q1_scientific_sufficiency as s

def read(name):return json.loads((s.OUT/name).read_text())
def ledger():return [json.loads(x) for x in (s.OUT/'q1_scientific_sufficiency_ledger.jsonl').read_text().splitlines()]

def test_branch_and_diff():
 assert s.git('symbolic-ref','--short','HEAD')==s.BRANCH
 assert s.git('diff','--check')==''

def test_base_manifest_and_all_files_unchanged():
 assert read('base_integrity_before.json')==read('base_integrity_after.json')==s.verify_base()
 assert read('base_integrity_before.json')['technical_verdict']==s.TECH

def test_scientific_verdict_separate_and_defensible():
 r=read('q1_manuscript_xai_readiness.json')
 assert r['BASE_TECHNICAL_VERDICT']==s.TECH
 assert r['Q1_XAI_MANUSCRIPT_READINESS']=='Q1_XAI_INSUFFICIENT_FOR_PRIMARY_MANUSCRIPT_CLAIMS'
 assert r['primary_Q1_sufficient_E1_scopes']==r['primary_Q1_sufficient_E2_scopes']==0

def test_twenty_gate_conditions_cannot_pass_partially():
 assert len(s.CRITERIA)==20
 assert s.classify_gate(['SUPPORTED']*20)=='Q1_SCIENTIFICALLY_SUFFICIENT'
 assert s.classify_gate(['SUPPORTED']*19)==s.INCOMPLETE
 assert s.classify_gate(['SUPPORTED']*19+['UNKNOWN'])==s.INCOMPLETE
 assert s.classify_gate(['SUPPORTED']*20,False)==s.NOT_DEFENSIBLE

def test_all_units_assessed_with_hash_bound_profiles():
 units=ledger(); profiles=read('q1_gate_criteria_and_profiles.json')['profiles']
 counts=read('q1_scientific_sufficiency_ledger_summary.json')['unit_counts']
 assert counts['E1_SCOPE']==168 and counts['E2_SCOPE']==221
 assert counts['PROJECT']==14 and counts['ALGORITHM_FAMILY']==4
 assert counts['GRAPH']==8 and counts['E1_MODALITY']==3 and counts['E2_CONFIGURATION']==4
 assert counts['ARTIFACT']==len(s.rows('frozen_artifact_candidate_inventory.jsonl'))
 for r in units:
  assert r['gate_profile'] in profiles and len(profiles[r['gate_profile']]['criteria'])==20
  assert r['scientific_sufficiency'] in s.CLASSES
  assert len(r['base_evidence_sha256'])==64 and not r['claim_supported']

def test_scopes_exclusions_unchanged():
 r=read('q1_manuscript_xai_readiness.json')
 assert r['eligible_scopes']==389
 assert {tuple(x) for x in r['excluded_scopes']}=={('apache/zeppelin','Logistic Regression',x) for x in ['C+T','P+T','C+P+T']}
 assert len({x['unit_id'] for x in ledger() if x['unit_type'] in ['E1_SCOPE','E2_SCOPE']})==389

def test_claim_traceability_fields_and_no_supported_partial_claim():
 claims=read('q1_claim_to_evidence_matrix.json')['claim_families']
 assert {x['claim_id'] for x in claims}==set('ABCDEFGHIJK')
 for x in claims:
  assert {'required_evidence','available_evidence','missing_evidence','project_coverage','algorithm_coverage','modality_coverage','scientific_sufficiency_classification','allowable_wording','prohibited_wording'}<=set(x)
  assert not x['claim_supported'] and x['missing_evidence']

def test_graphs_not_publication_ready():
 graphs=read('q1_graph_readiness_matrix.json')['graphs'];assert len(graphs)==8
 for r in graphs:
  assert {'required_evidence','evidence_completeness','sample_coverage','project_coverage','family_coverage','modality_coverage','baseline_definition','output_scale','reproducibility_status','fidelity_additivity_verification_availability','interpretation_limits','Q1_sufficiency_classification','allowable_manuscript_use'}<=set(r)
  assert not r['publication_ready'] and r['allowable_manuscript_use']=='NONE_AS_PRIMARY_EVIDENCE'
 assert any(r['future_exploratory_designation']=='EXPLORATORY_ONLY' for r in graphs)
 assert not read('q1_graph_readiness_matrix.json')['exploratory_plots_count_as_primary']

def test_multimodal_all_configs_and_quantities():
 r=read('q1_multimodal_explanation_readiness.json')
 assert r['configuration_counts']=={'C+P':56,'C+T':55,'P+T':55,'C+P+T':55}
 assert len(r['scopes'])==221 and r['C_P_T_full_configuration_priority']
 for x in r['scopes']:
  assert x['modality_order']==x['configuration'].split('+')
  assert x['raw_algebra_technical_readiness_preserved']
  assert x['quantities']['centered_baseline_phi0']=='BLOCKED_BY_PRIMARY_MU_REFERENCE'
  assert not x['empirical_claim_supported']
 assert not r['TRAIN_mean_assessment']['complete_primary_reference_mean_available_or_defensibly_derivable_now']
 assert r['TRAIN_mean_assessment']['no_mean_computed']

def test_risk_controls_and_blocking_gate():
 r=read('q1_risk_control_matrix.json')
 assert len(r['risks'])==17 and r['blocking_risk_count']==5
 assert all(x['status'] in ['ABSENT','CONTROLLED','PRESENT_WITH_LIMITATION','PRESENT_BLOCKING'] for x in r['risks'])
 assert r['blocking_risk_prevents_full_defensibility']
 assert not any(x['published_violation_observed'] for x in r['risks'])

def test_no_single_project_family_or_raw_component_promotion():
 r=read('q1_manuscript_xai_readiness.json')
 assert r['evidence_components_project_coverage']==14 and len(r['evidence_components_algorithm_families'])==4
 assert r['primary_supported_claim_families']==r['publication_ready_graph_families']==0
 assert all(x['project_coverage']['primary_validated']==0 for x in read('q1_claim_to_evidence_matrix.json')['claim_families'])

def test_all_eighteen_answers_present():
 a=read('q1_manuscript_xai_readiness.json')['explicit_answers']
 assert [r['question_number'] for r in a]==list(range(1,19))
 assert all(r['answer'] for r in a)

def test_scientific_counters_unchanged_and_zero_for_amendment():
 c=read('governance_counters.json')
 assert all(v==0 for v in c['amendment_counters'].values())
 assert c['base_counter_snapshot']==s.read('governance_counters.json')
 assert c['base_historical_T1_read_count_preserved']==1
 assert not c['Sprint56_3_authorized']

def test_next_action_requires_both_endpoints():
 n=read('q1_next_action.json')
 assert 'BOTH E1' in n['minimum_next_action']
 assert not any(n[k] for k in ['resume_population_freeze_authorized','Sprint56_3_authorized','model_query_authorized','scientific_payload_read_authorized','plots_authorized'])
 assert {x['requirement_id'] for x in read('q1_exact_remaining_requirements.json')['requirements']}=={'REQ_E1','REQ_E2','REQ_SELECTION','REQ_VALIDATION','REQ_REPORTING'}

@pytest.mark.parametrize('path',['audits/q1-t1-confirmatory-execution/1.0.0/results/t1_prediction_evidence.jsonl.gz',
 'audits/q1-xai-reconstruction-execution/1.0.0/objects/model.joblib','data/T2.csv',
 'audits/q1-apachejit-final-dataset-freeze/1.0.0/code_dataset.jsonl.gz'])
def test_no_underlying_artifact_read(path):
 with pytest.raises(PermissionError):s.guard('open',(str(s.ROOT/path),'rb',0))

@pytest.mark.parametrize('path',['MANIFEST.sha256','recommended_next_action.json','governance_counters.json'])
def test_parent_write_denied(path):
 with pytest.raises(PermissionError):s.guard('open',(str(s.BASE/path),'wb',0))

def test_no_scientific_or_discovery_code():
 tree=ast.parse(Path(s.__file__).read_text())
 forbidden={'fit','predict','predict_proba','decision_function','TreeExplainer','shap_values','transform','mean','load_model','materialize','rglob','walk','read_csv','read_parquet','savefig','plot','roc_auc_score','matthews_corrcoef'}
 calls={n.func.attr if isinstance(n.func,ast.Attribute) else n.func.id for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,(ast.Name,ast.Attribute))}
 assert not calls & forbidden
 imports={a.name for n in ast.walk(tree) if isinstance(n,ast.Import) for a in n.names}
 assert not imports & {'numpy','pandas','shap','joblib','pickle','matplotlib'}

def test_amendment_manifest():
 expected={name:h for h,name in (x.split('  ',1) for x in (s.OUT/'MANIFEST.sha256').read_text().splitlines())}
 assert set(expected)=={p.name for p in s.OUT.iterdir() if p.is_file() and p.name!='MANIFEST.sha256'}
 assert all(s.sha(s.OUT/n)==h for n,h in expected.items())
