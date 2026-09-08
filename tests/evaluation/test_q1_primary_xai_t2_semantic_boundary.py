"""Metadata-only semantic review tests. No router or scientific row fixtures."""
import ast
import json
from pathlib import Path
import pytest
from src.evaluation import q1_primary_xai_t2_semantic_boundary as s

def read(name): return json.loads((s.OUT/name).read_text())
def ledger(): return [json.loads(x) for x in (s.OUT/'evidence_classification_ledger.jsonl').read_text().splitlines()]

def test_branch_head_and_diff():
    assert s.git('symbolic-ref','--short','HEAD')==s.BRANCH
    assert s.git('rev-parse','HEAD') in (s.OUT/'SPRINT56_2B_T2_SEMANTIC_BOUNDARY_REPORT.md').read_text()
    assert s.git('diff','--check')==''

@pytest.mark.parametrize('prefix',[s.S,s.P,s.Q])
def test_parent_unchanged(prefix):
    before=read('parent_integrity_before.json'); after=read('parent_integrity_after.json')
    assert before[prefix]==after[prefix]
    for name,record in after[prefix].items():
        if 'fresh_metadata_sha256' in record: assert s.sha(s.ROOT/prefix/name)==record['fresh_metadata_sha256']

def test_parent_outcomes():
    assert s.load(s.S+'sprint56_1_summary.json')['outcome']=='PRIMARY_XAI_ISOLATED_RUNTIME_SMOKE_TEST_PASS'
    assert s.load(s.P+'sprint56_2_summary.json')['outcome']=='PRIMARY_XAI_T1_SELECTION_CONTRACT_FAILURE'
    assert s.load(s.Q+'source_selection.json')['accepted_candidates']==[]

def test_universe_exclusions():
    state=read('scope_integrity.json')
    assert state['count']==389 and state['E1']==168 and state['E2']==221
    assert {tuple(x) for x in state['excluded']}=={('apache/zeppelin','Logistic Regression',c) for c in ['C+T','P+T','C+P+T']}

@pytest.mark.parametrize('path',[
 'data/external/apachejit-v2/extracted/apachejit/dataset/apachejit_total.csv',
 s.F+'temporal_partition_manifest.jsonl.gz',s.F+'row_identity_provenance.jsonl.gz',s.F+'code_dataset.jsonl.gz',
 'data/T2.jsonl','audits/fixture/t1_prediction_evidence.jsonl.gz',s.S+'selected_train_rows.json',
 'audits/q1-xai-reconstruction-execution/1.0.0/objects/model.joblib'])
def test_payload_read_guard(path):
    with pytest.raises(PermissionError): s.guard('open',(str(s.ROOT/path),'rb',0))

@pytest.mark.parametrize('path',[s.P+'sprint56_2_summary.json',s.Q+'source_selection.json','.gitignore','.venv/pyvenv.cfg'])
def test_parent_write_guard(path):
    with pytest.raises(PermissionError): s.guard('open',(str(s.ROOT/path),'w',0))

def test_no_execution_apis_or_scientific_imports():
    tree=ast.parse(Path(s.__file__).read_text())
    forbidden={'fit','refit','predict','predict_proba','decision_function','TreeExplainer','shap_values','read_csv',
     'read_parquet','roc_auc_score','average_precision_score','matthews_corrcoef','savefig','scatter','plot',
     'materialize','_partition_rows','reconstruct','calibrate'}
    calls={n.func.attr if isinstance(n.func,ast.Attribute) else n.func.id for n in ast.walk(tree)
           if isinstance(n,ast.Call) and isinstance(n.func,(ast.Name,ast.Attribute))}
    assert not calls & forbidden
    imports={n.module.split('.')[0] for n in ast.walk(tree) if isinstance(n,ast.ImportFrom) and n.module}
    imports|={a.name.split('.')[0] for n in ast.walk(tree) if isinstance(n,ast.Import) for a in n.names}
    assert not imports & {'shap','numpy','pandas','sklearn','xgboost','lightgbm','matplotlib','joblib','pickle'}

def test_evidence_categories_and_exact_excerpts():
    for item in ledger():
        assert item['category'] in s.CATEGORIES
        if item['category'].startswith('DIRECT_'):
            path=s.ROOT/item['path']
            assert s.sha(path)==item['file_sha256']
            assert '\n'.join(path.read_text().splitlines()[item['line_start']-1:item['line_end']])==item['excerpt']

def test_invalid_evidence_category_rejected():
    with pytest.raises(ValueError): s.decide({},[{'category':'OPTIMISTIC'}])

@pytest.mark.parametrize('category',['DERIVED_INFERENCE','UNKNOWN'])
def test_inference_cannot_pass(category):
    refs=[{'id':'a','category':category,'supports':True}]
    criteria={key:{'status':'DIRECTLY_SUPPORTED','evidence_ids':['a']} for key in 'ABCDE'}
    assert s.decide(criteria,refs)=='T2_SEMANTIC_BOUNDARY_EVIDENCE_INSUFFICIENT'

def test_direct_evidence_gate_and_hierarchy():
    refs=[{'id':'a','category':'DIRECT_CODE_EVIDENCE','supports':True}]
    criteria={key:{'status':'DIRECTLY_SUPPORTED','evidence_ids':['a']} for key in 'ABCDE'}
    assert s.decide(criteria,refs)=='T2_SEMANTIC_BOUNDARY_AMENDMENT_JUSTIFIED'
    assert s.decide(criteria,refs,already_bound=True)=='T2_ALREADY_SEMANTICALLY_BOUND_AT_SOURCE'
    assert s.decide(criteria,refs,conflict=True)=='T2_SEMANTIC_BOUNDARY_PROVENANCE_CONFLICT'
    refs[0]['supports']=False
    assert s.decide(criteria,refs)=='T2_SEMANTIC_BOUNDARY_EVIDENCE_INSUFFICIENT'

def test_actual_decision_does_not_overclaim():
    a=read('historical_partition_semantics_audit.json')
    assert a['source_before_assignment']=='YES_DIRECTLY_SUPPORTED'
    assert a['criteria']['C']['status']==a['criteria']['D']['status']=='UNKNOWN'
    assert s.decide(a['criteria'],ledger())==a['classification']=='T2_SEMANTIC_BOUNDARY_EVIDENCE_INSUFFICIENT'
    assert a['amendment']=='AMENDMENT_NOT_JUSTIFIED'

def test_historical_code_and_ordinal_contract():
    assert read('historical_code_provenance.json')['historical_source_matches_working_tree']
    spec=read('frozen_partition_function_spec.json')
    assert len(spec['projects'])==14
    for p in spec['projects']:
        n=p['upstream_project_count_metadata']
        assert [p['TRAIN_end_exclusive'],p['VALIDATION_end_exclusive'],p['T1_end_exclusive']]==[n*60//100,n*80//100,n*84//100]
    assert spec['labels_needed_for_assignment'] is False
    assert spec['reuse_entire_historical_function']=='PROHIBITED'

def test_blind_router_contract_only_and_drop():
    r=read('future_blind_router_contract.json')
    assert not r['implementation_authorized'] and not r['execution_authorized']
    assert 'DROP T2 immediately before downstream scientific boundary' in r['requirements']
    assert {'never serialize T2','never hash T2 rows','never log T2 identity','never retain T2 labels/features'}<=set(r['requirements'])

def test_three_levels_not_adopted():
    r=read('three_level_access_model.json')
    assert r['status']=='CONDITIONAL_PROPOSAL_NOT_ADOPTED'
    assert all(not x['currently_authorized'] for x in r['levels'][:2])
    assert r['levels'][2]['T2']=='DENIED'

def test_partial_consumption_rejected():
    p=read('partial_t2_consumption_policy.json')
    assert p['PARTIAL_T2_CONSUMPTION_POLICY']=='REJECTED_WHILE_UPSTREAM_SOLUTION_REMAINS_POSSIBLE'
    assert p['fraction_reclassified']==0

def test_canonical_recipe_complete_and_new_namespace():
    c=read('canonical_serialization_freeze.json')
    assert {'encoding','key_order','string_encoding','null','integers','floats','numeric_type','whitespace','newline','row_order','hash','compression'}<=set(c)
    assert '3.11.14' in c['floats'] and 'allow_nan=false' in c['floats']
    p=read('prospective_digest_policy.json')
    assert p['HISTORICAL_MEMBERSHIP_DIGEST']!=p['S56_SAFE_SOURCE_CANONICAL_SHA256']
    assert p['historical_row_digest_status']=='HISTORICAL_ROW_DIGEST_RECIPE_UNAVAILABLE'
    assert not p['digest_generated_this_stage'] and p['no_retrospective_hash_tuning']

def test_output_contracts():
    assert read('future_t1_output_contract.json')['required_fields']==['project','partition','row_identifier','order_key']
    train=read('future_train_output_contract.json')
    assert train['CODE']==s.C and train['PROCESS']==s.PROCESS
    assert not train['authorized'] and not train['additional_fields']

def test_counters_and_stop():
    c=read('governance_counters.json')
    assert all(c[k]==0 for k in s.COUNTERS)
    assert c['T2_STATE']=='DENY_SEALED_REVIEWER_RESERVE'
    r=read('future_safe_rematerialization_prerequisites.json')
    assert not r['authorized'] and not r['resume_Sprint56_2'] and not r['Sprint56_3_authorized']

def test_object_preservation_without_payload_open():
    a=read('parent_integrity_after.json')['object_store_stat_only']
    assert len(a)==5649 and sum(x['bytes'] for x in a.values())==2139594110
    assert a==read('parent_integrity_before.json')['object_store_stat_only']
    assert not any('/objects/' in x for x in read('read_access_log.json')['paths'])

def test_manifest():
    entries={name:h for h,name in (x.split('  ',1) for x in (s.OUT/'MANIFEST.sha256').read_text().splitlines())}
    assert set(entries)=={p.name for p in s.OUT.iterdir() if p.is_file() and p.name!='MANIFEST.sha256'}
    assert all(s.sha(s.OUT/name)==h for name,h in entries.items())
