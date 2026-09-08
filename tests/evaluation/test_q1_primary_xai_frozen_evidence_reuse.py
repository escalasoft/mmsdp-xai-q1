"""Governance and exact stored-evidence linkage; no scientific arithmetic."""
import ast
import json
from pathlib import Path
import pytest
from src.evaluation import q1_primary_xai_frozen_evidence_reuse as s

def read(name):return json.loads((s.OUT/name).read_text())
def rows(name):return [json.loads(x) for x in (s.OUT/name).read_text().splitlines() if x.strip()]

def test_branch_head_diff():
 assert s.git('symbolic-ref','--short','HEAD')==s.BRANCH
 assert s.git('rev-parse','HEAD')==read('scope_integrity.json')['HEAD']
 assert s.git('diff','--check')==''

def test_parent_hashes_unchanged():
 assert read('parent_integrity_before.json')==read('parent_integrity_after.json')

def test_parent_outcomes():
 assert json.loads((s.SMOKE/'sprint56_1_summary.json').read_text())['outcome']=='PRIMARY_XAI_ISOLATED_RUNTIME_SMOKE_TEST_PASS'
 assert json.loads((s.PARENT/'sprint56_2_summary.json').read_text())['outcome']=='PRIMARY_XAI_T1_SELECTION_CONTRACT_FAILURE'
 a=s.ROOT/'audits/q1-primary-xai-safe-population-source/1.0.0/source_selection.json'
 assert json.loads(a.read_text())['accepted_candidates']==[]
 b=s.ROOT/'audits/q1-primary-xai-t2-semantic-boundary-amendment/1.0.0/historical_partition_semantics_audit.json'
 assert json.loads(b.read_text())['amendment']=='AMENDMENT_NOT_JUSTIFIED'

def test_scope_integrity_exclusions():
 r=read('scope_integrity.json'); assert r['count']==389
 assert {tuple(x) for x in r['excluded']}=={('apache/zeppelin','Logistic Regression',c) for c in ['C+T','P+T','C+P+T']}

@pytest.mark.parametrize('path',['audits/q1-apachejit-final-dataset-freeze/1.0.0/code_dataset.jsonl.gz',
 'audits/q1-apachejit-final-dataset-freeze/1.0.0/temporal_partition_manifest.jsonl.gz','data/t2.jsonl','data/raw/train.csv'])
def test_prohibited_payload_guard(path):
 s.prepare()
 with pytest.raises(PermissionError):s.guard('open',(str(s.ROOT/path),'rb',0))

@pytest.mark.parametrize('path',['.gitignore','audits/q1-xai-reconstruction-execution/1.0.0/objects/test.joblib',
 'audits/q1-primary-xai-population-freeze/1.0.0/sprint56_2_summary.json'])
def test_immutable_write_guard(path):
 with pytest.raises(PermissionError):s.guard('open',(str(s.ROOT/path),'wb',0))

def test_no_query_shap_metric_refit_transform_or_population_selection():
 tree=ast.parse(Path(s.__file__).read_text())
 forbidden={'fit','fit_transform','transform','predict','predict_proba','decision_function','TreeExplainer','shap_values','shap',
 'reconstruct','refit','recalibrate','savefig','plot','mean','average_precision_score','roc_auc_score','f1_score','matthews_corrcoef',
 'precision_score','recall_score','brier_score_loss','select_population'}
 calls={n.func.attr if isinstance(n.func,ast.Attribute) else n.func.id for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,(ast.Name,ast.Attribute))}
 assert not calls & forbidden
 imports={n.module or '' for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)}
 imports|={a.name for n in ast.walk(tree) if isinstance(n,ast.Import) for a in n.names}
 assert not any(x.startswith(('shap','sklearn.metrics','matplotlib')) for x in imports)

def test_exact_identity_matching_not_fuzzy():
 ids=['synthetic-a','synthetic-b']
 assert s.membership_check(ids,s.digest(ids),2)
 assert not s.membership_check(ids[::-1],s.digest(ids),2)
 assert not s.membership_check(['synthetic-a','synthetic-a'],s.digest(ids),2)
 assert not s.membership_check(['synthetic-A','synthetic-b'],s.digest(ids),2)

def test_e1_e2_independent():
 assert s.e2_decision(True,False,True)==s.PARTIAL
 assert s.e2_decision(True,True,True)=='FULL_FROZEN_EVIDENCE_REUSE_FEASIBLE'
 assert s.e2_decision(False,True,True)==s.NO
 assert all(x['complete_reusable_scopes']==0 for x in read('e1_family_feasibility.json')['families'])
 assert read('e2_multimodal_feasibility.json')['raw_uncentered_T1_input_ready_scopes']==221

def test_t1_exact_g4_reference_reconciliation():
 r=read('row_identity_reconciliation.json')
 assert len(r['T1'])==389 and r['T1_unique_rows']==3787
 assert sum(x['rows'] for x in r['T1'])==105862
 assert all(x['exact_G4_identity_order_and_reference_probability_digest'] for x in r['T1'])
 assert r['exact_matching_only'] and not r['fuzzy_matching'] and not r['feature_value_identity_inference']

def test_g4_digests_are_not_features():
 r=read('g4_t1_input_reuse_audit.json')
 assert r['persisted_feature_matrices_found']==0
 assert 'frozen_reference_probability_digest' in r['result_schema']
 assert not any('input_matrix' in x for x in r['result_schema'])

def test_final_outputs_not_training_input_matrices():
 r=read('reconstruction_train_input_reuse_audit.json')
 assert r['final_base_probability_vectors']==168 and r['exact_feature_training_matrices_found']==0
 assert r['final_states_structurally_deserialized']==392
 assert all(not x['embedded_training_rows_found'] for x in r['final_states'])
 assert len(r['TEXT_state'])==56

def test_oof_membership_provenance_and_reference_limit():
 r=read('oof_evidence_reuse_audit.json')
 assert len(r['candidates'])==56 and len({x['project'] for x in r['candidates']})==14
 assert all(x['exact_historical_meta_TRAIN_membership'] and x['warmup_rows_absent']>0 for x in r['candidates'])
 assert all(x['OOF_predictors_differ_from_final_base'] and not x['E1_background'] for x in r['candidates'])
 assert not r['means_computed']

def test_e2_coverage_order_and_no_overclaim():
 r=read('e2_multimodal_feasibility.json')
 assert r['configuration_counts']=={'C+P':56,'C+T':55,'P+T':55,'C+P+T':55}
 assert r['complete_primary_reusable_scopes']==0
 for x in r['scopes']:
  assert x['exact_modality_order']==x['configuration'].split('+')
  assert x['T1_raw_modality_input_complete'] and x['uncentered_local_algebra_input_ready']
  assert not x['centered_primary_global_input_ready']

def test_project_and_modality_coverage_reconcile():
 p=read('project_coverage_matrix.json')['projects']; assert len(p)==14
 assert sum(x['eligible_scopes'] for x in p)==389
 assert sum(x['E1_eligible'] for x in p)==168 and sum(x['E2_raw_T1_input_ready'] for x in p)==221
 assert sum(x['TRAIN_feature_coverage']=='PARTIAL_80_ROWS' for x in p)==1
 assert all(x['T1_feature_coverage']=='ZERO' for x in p)
 assert {x['modality'] for x in read('e1_modality_feasibility.json')['modalities']}=={'CODE','PROCESS','TEXT'}

def test_graphics_map_matches_inputs():
 plots=read('xai_graphics_feasibility.json')['plots']
 assert len(plots)==7 and not any(x['classification']=='READY_FROM_FROZEN_EVIDENCE' for x in plots)
 assert next(x for x in plots if x['family']=='beeswarm plots')['classification']=='NOT_READY'
 assert next(x for x in plots if x['family']=='multimodal modality-contribution plots')['classification']=='PARTIALLY_READY'

def test_counters_and_unique_file_inventory():
 r=read('governance_counters.json'); assert all(r[k]==0 for k in s.ZERO)
 assert r['HISTORICAL_T1_ARTIFACT_READ_COUNT']==1 and r['HISTORICAL_T1_ARTIFACT_ROW_RECORDS_INSPECTED']==106036
 assert r['REUSABLE_E1_SCOPES']==r['REUSABLE_E2_SCOPES']==0 and r['PARTIALLY_REUSABLE_E2_SCOPES']==221
 candidates=rows('frozen_artifact_candidate_inventory.jsonl')
 assert len(candidates)==len({x['path'] for x in candidates})
 assert r['FROZEN_ARTIFACT_FILES_INSPECTED']==len(read('inspection_log.json')['files'])
 assert r['FROZEN_TRAIN_ARTIFACTS_FOUND']==r['REUSABLE_TRAIN_ARTIFACTS']==len(rows('train_evidence_inventory.jsonl'))

def test_reusable_component_provenance_and_no_scope_promotion():
 for r in rows('provenance_reuse_ledger.jsonl'):
  assert len(r['sha256'])==64 and 'FROZEN_MANIFEST_AND_OBJECT_HASH' in r['chain']
  assert r['artifact_manifest_sha256'] and r['historical_processing_source_sha256']
  assert r['component_provenance']=='EXACT_HISTORICAL_COMPONENT'
  assert r['primary_population_provenance']=='INCOMPLETE_WHERE_STATED_IN_SCOPE_DISPOSITION'
 assert not read('recommended_next_action.json')['Sprint56_3_authorized']

def test_manifest():
 records={name:h for h,name in (x.split('  ',1) for x in (s.OUT/'MANIFEST.sha256').read_text().splitlines())}
 assert set(records)=={p.name for p in s.OUT.iterdir() if p.is_file() and p.name!='MANIFEST.sha256'}
 assert all(s.sha(s.OUT/name)==h for name,h in records.items())
