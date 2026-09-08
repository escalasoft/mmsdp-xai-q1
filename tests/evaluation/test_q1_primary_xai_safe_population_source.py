"""Safe-source governance; all row fixtures are invented, never campaign rows."""
import ast
import copy
import gzip
import hashlib
import json
from pathlib import Path
import pytest
from src.evaluation import q1_primary_xai_safe_population_source as s

@pytest.fixture
def fixture_bundle():
    projects=['synthetic/a','synthetic/b']
    bundle={p:{} for p in ['TRAIN','T1']}
    expected={'projects':projects,'TRAIN':{},'T1':{}}
    for partition in bundle:
        for project in projects:
            rows=[]
            for i in range(3):
                row={'project':project,'partition':partition,'row_identifier':hashlib.sha256(f'{partition}/{project}/{i}'.encode()).hexdigest(),
                     'order_key':[f'2000-01-0{i+1}T00:00:00Z',f'{i:040x}']}
                if partition=='TRAIN':
                    row.update({'class':i%2,**{k:i+0.25 for k in s.C+s.P}})
                rows.append(row)
            bundle[partition][project]=rows
            expected[partition][project]={'count':3,'membership_digest':s.digest([r['row_identifier'] for r in rows]),
                'canonical_rows_sha256':hashlib.sha256(b''.join(s.canonical(r) for r in rows)).hexdigest()}
    return bundle,expected

def accepted():
    return {'status':'PHASE_A_ACCEPTED','all_acceptance_criteria_verified':True,'source_provenance':'SYNTHETIC_ONLY_TEST_FIXTURE'}

def test_canonical_golden():
    assert s.canonical({'z':'é','a':[1,2]})==b'{"a":[1,2],"z":"\\u00e9"}\n'

def test_phase_b_denied_before_processing(tmp_path):
    with pytest.raises(s.SafeSourceError,match='Phase B denied'):
        s.materialize({},None,None,tmp_path/'absent')
    assert not (tmp_path/'absent').exists()

def test_serialization_repeatability_and_minimal_schema(fixture_bundle,tmp_path):
    bundle,expected=fixture_bundle
    registries=[s.materialize(accepted(),bundle,expected,tmp_path/name) for name in ['one','two']]
    assert registries[0]==registries[1]
    for item in registries[0]:
        data=(tmp_path/'one'/item['path']).read_bytes()
        assert data==(tmp_path/'two'/item['path']).read_bytes()
        rows=[json.loads(x) for x in (gzip.decompress(data) if item['partition']=='TRAIN' else data).splitlines()]
        assert all(set(r)==set(s.TRAIN_FIELDS if item['partition']=='TRAIN' else s.T1_FIELDS) for r in rows)

@pytest.mark.parametrize('kind',['duplicate','project','partition','order','class_bool','class_range','nan','missing_feature','extra_feature','bad_time','bad_sha','bad_id','membership','count','values','no_value_provenance'])
def test_invalid_train_rejected(kind,fixture_bundle):
    bundle,expected=fixture_bundle
    rows=bundle['TRAIN']['synthetic/a']; ref=expected['TRAIN']['synthetic/a']
    if kind=='duplicate': rows[1]['row_identifier']=rows[0]['row_identifier']
    elif kind=='project': rows[0]['project']='different'
    elif kind=='partition': rows[0]['partition']='T2'
    elif kind=='order': rows.reverse()
    elif kind=='class_bool': rows[0]['class']=True
    elif kind=='class_range': rows[0]['class']=2
    elif kind=='nan': rows[0]['la']=float('nan')
    elif kind=='missing_feature': del rows[0]['la']
    elif kind=='extra_feature': rows[0]['invented']=1
    elif kind=='bad_time': rows[0]['order_key'][0]='nonsenseZ'
    elif kind=='bad_sha': rows[0]['order_key'][1]='bad'
    elif kind=='bad_id': rows[0]['row_identifier']='bad'
    elif kind=='membership': ref['membership_digest']='0'*64
    elif kind=='count': ref['count']=4
    elif kind=='values': rows[0]['la']=100
    elif kind=='no_value_provenance': del ref['canonical_rows_sha256']
    with pytest.raises(s.SafeSourceError): s.validate_rows(rows,'synthetic/a','TRAIN',ref,{'CODE':s.C,'PROCESS':s.P})

@pytest.mark.parametrize('field',['class','label','la','ndev','probability','prediction','shap_values'])
def test_t1_forbidden_fields_rejected(field,fixture_bundle):
    bundle,expected=fixture_bundle
    rows=bundle['T1']['synthetic/a']; rows[0][field]=0
    with pytest.raises(s.SafeSourceError): s.validate_rows(rows,'synthetic/a','T1',expected['T1']['synthetic/a'],{'CODE':s.C,'PROCESS':s.P})

def test_feature_order_rejected(fixture_bundle):
    bundle,expected=fixture_bundle
    with pytest.raises(s.SafeSourceError,match='column order'):
        s.validate_rows(bundle['TRAIN']['synthetic/a'],'synthetic/a','TRAIN',expected['TRAIN']['synthetic/a'],{'CODE':s.C[::-1],'PROCESS':s.P})

def test_partial_coverage_no_writes(fixture_bundle,tmp_path):
    bundle,expected=fixture_bundle; del bundle['T1']['synthetic/b']
    with pytest.raises(s.SafeSourceError,match='coverage'): s.materialize(accepted(),bundle,expected,tmp_path/'out')
    assert not (tmp_path/'out').exists()

def test_late_failure_no_partial_materialization(fixture_bundle,tmp_path):
    bundle,expected=fixture_bundle; bundle['T1']['synthetic/b'][2]['class']=1
    with pytest.raises(s.SafeSourceError): s.materialize(accepted(),bundle,expected,tmp_path/'out')
    assert not (tmp_path/'out').exists()

@pytest.mark.parametrize('path',['data/external/apachejit-v2/extracted/apachejit/data/apachejit_train.csv',
    'audits/q1-apachejit-final-dataset-freeze/1.0.0/code_dataset.jsonl.gz','data/t2.csv',
    'audits/fixture/t1_prediction_evidence.jsonl.gz'])
def test_payload_guard_denies_before_open(path):
    with pytest.raises(PermissionError): s.guard('open',(str(s.ROOT/path),'r',0))

@pytest.mark.parametrize('path',['.gitignore','.venv/pyvenv.cfg','.venv-xai-s56/pyvenv.cfg',
    'audits/q1-primary-xai-population-freeze/1.0.0/source.json','audits/q1-xai-reconstruction-execution/1.0.0/objects/test'])
def test_protected_write_denied(path):
    with pytest.raises(PermissionError): s.guard('open',(str(s.ROOT/path),'w',0))

def test_branch_and_head():
    assert s.git('symbolic-ref','--short','HEAD')==s.BRANCH
    assert s.git('rev-parse','HEAD')==s.read(s.OUT/'provenance_chain.json')['head']

def test_parent_snapshot_matches():
    assert s.read(s.OUT/'parent_integrity_before.json')==s.read(s.OUT/'parent_integrity_after.json')

def test_universe_and_exclusions():
    rows=s.lines(s.PARENT/'primary_xai_scope_ledger.jsonl')
    assert len(rows)==389
    assert len({r['project'] for r in rows})==14
    excluded={('apache/zeppelin','Logistic Regression',c) for c in ['C+T','P+T','C+P+T']}
    assert not {(r['project'],r['algorithm'],r['configuration']) for r in rows} & excluded
    assert s.read(s.PARENT/'sprint56_2_summary.json')['outcome']=='PRIMARY_XAI_T1_SELECTION_CONTRACT_FAILURE'

def test_all_current_counters_zero():
    counters=s.read(s.OUT/'governance_counters.json')
    assert all(counters[k]==0 for k in s.COUNTER_NAMES)
    assert counters['T2_STATE']=='DENY_SEALED_REVIEWER_RESERVE'
    assert counters['historical_Sprint54_predictive_access_scoring']==[1,1]

def test_no_safe_candidate_or_real_materialization():
    rows=s.lines(s.OUT/'source_candidate_ledger.jsonl')
    assert len(rows)==113
    assert all(not r['verdict'].startswith('SAFE_') for r in rows)
    assert next(r for r in rows if r['path'].endswith('apachejit_train.csv'))['verdict']=='SEMANTIC_MISMATCH'
    assert s.read(s.OUT/'materialization_integrity.json')['materialized_rows']==0
    assert not (s.OUT/'train').exists() and not (s.OUT/'t1').exists()

def test_no_scientific_api_calls():
    tree=ast.parse(Path(s.__file__).read_text())
    forbidden={'fit','fit_transform','predict','predict_proba','decision_function','shap_values','TreeExplainer','read_csv','read_parquet',
        'roc_auc_score','average_precision_score','f1_score','matthews_corrcoef','partial_fit'}
    calls={n.func.attr if isinstance(n.func,ast.Attribute) else n.func.id for n in ast.walk(tree)
           if isinstance(n,ast.Call) and isinstance(n.func,(ast.Name,ast.Attribute))}
    assert not calls & forbidden

def test_next_stage_denied():
    next_action=s.read(s.OUT/'next_action.json')
    assert next_action['human_review_required'] and not next_action['resume_56_2'] and not next_action['Sprint56_3_authorized']

def test_manifest():
    entries={name:h for h,name in (line.split('  ',1) for line in (s.OUT/'MANIFEST.sha256').read_text().splitlines())}
    assert set(entries)=={p.relative_to(s.OUT).as_posix() for p in s.OUT.rglob('*') if p.is_file() and p.name!='MANIFEST.sha256'}
    assert all(s.sha(s.OUT/name)==h for name,h in entries.items())
