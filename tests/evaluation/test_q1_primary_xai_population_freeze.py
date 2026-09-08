"""Sprint 56.2 readiness/contracts and honest fail-closed population status."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'audits/q1-primary-xai-population-freeze/1.0.0'
SPEC=importlib.util.spec_from_file_location('population_freeze',ROOT/'src/evaluation/q1_primary_xai_population_freeze.py')
m=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


def read(name):
    return m.read(OUT/name)


def rows(name):
    return m.rows(OUT/name)


def test_exact_389_scope_universe_and_three_exclusions():
    scopes=rows('primary_xai_scope_ledger.jsonl')
    assert len(scopes)==len({r['model_identity_sha256'] for r in scopes})==389
    assert len({(r['project'],r['algorithm'],r['configuration']) for r in scopes})==389
    assert {tuple(r) for r in read('scope_readiness_summary.json')['excluded_scopes']}==m.EXCLUDED
    assert not m.EXCLUDED & {(r['project'],r['algorithm'],r['configuration']) for r in scopes}
    prior={r['model_identity_sha256'] for r in m.rows(m.G5/'xai_readiness_ledger.jsonl')}
    assert prior=={r['model_identity_sha256'] for r in scopes}


def test_every_scope_has_exact_g1_g5_chain_and_required_objects():
    records=rows('model_state_readiness_ledger.jsonl')
    g3={r['model_identity_sha256']:r for r in m.rows(m.G3/'scope_g1_g3_eligibility.jsonl')}
    for r in records:
        assert r['state_readiness']=='READY_VERIFIED'
        assert r['G4']=='G4_PASS_ROW_LEVEL_RAW_EQUIVALENCE'
        assert r['G5']=='G5_PASS_FINAL_OUTPUT_EQUIVALENCE'
        assert r['G1_G3']==g3[r['model_identity_sha256']]['gate_results']
        expected=g3[r['model_identity_sha256']]['required_base_components'][:]
        if g3[r['model_identity_sha256']]['required_fusion_component']:
            expected.append(g3[r['model_identity_sha256']]['required_fusion_component'])
        assert r['required_logical_states']==expected
        for state in r['states']:
            assert state['status']=='READY_VERIFIED'
            for ref in state['objects'].values():
                assert m.sha(m.STORE/ref['path'])==ref['sha256']
                assert (m.STORE/ref['path']).stat().st_size==ref['bytes']


def test_runtime_and_predictive_environments_are_exactly_bound():
    r=read('xai_runtime_binding.json')
    assert r['runtime_hash']==m.sha(m.SMOKE/'isolated_runtime_lock.json')
    assert r['exact_inventory']==m.read(m.SMOKE/'isolated_runtime_lock.json')['inventory']
    assert m.inventory()==m.read(m.SMOKE/'predictive_inventory_before.json')
    assert r['environment']==str(ROOT/'.venv-xai-s56')
    assert all(value=='1' for value in r['required_threads'].values())
    assert r['runtime_changes_require']=='PROSPECTIVE_XAI_RUNTIME_AMENDMENT'


def test_methods_and_scales_are_deterministic_for_all_scopes():
    for s in rows('primary_xai_scope_ledger.jsonl'):
        if '+' in s['configuration']:
            assert s['role']=='E2' and s['method']=='ANALYTICAL_LR_FUSION_DECOMPOSITION'
            assert s['explanation_scale']=='META_LOGIT'
        else:
            assert s['role']=='E1' and s['method']==m.METHODS[s['algorithm']]
            assert s['explanation_scale']==m.SCALES[s['algorithm']]
    counts=read('scope_readiness_summary.json')
    assert counts['E1']==168 and counts['E2']==221
    tree=read('xai_output_scale_contract.json')['TreeSHAP']
    assert tree['approximate'] is False and tree['model_output']=='raw'


def candidates(partition='TRAIN',n=300):
    return [{'project':'synthetic_project','partition':partition,'row_identifier':f'row_{i:04d}',
             **({'class':i%2} if partition=='TRAIN' else {})} for i in range(n)]


def test_train_selection_class_quota_hash_order_and_insufficient_rows():
    data=candidates()
    selected=m.select_population(data,'synthetic_project','model','TRAIN_REFERENCE',256,True)
    assert len(selected)==256
    assert sum(r['class']==1 for r in selected)==128
    assert selected==m.select_population(list(reversed(data)),'synthetic_project','model','TRAIN_REFERENCE',256,True)
    assert [r['selection_key'] for r in selected]==sorted(r['selection_key'] for r in selected)
    assert len(m.select_population(data[:20],'synthetic_project','model','TRAIN_REFERENCE',256,True))==20
    skew=[{**r,'class':0} for r in data]
    skew[0]['class']=1
    assert len(m.select_population(skew,'synthetic_project','model','TRAIN_REFERENCE',256,True))==256
    expected=hashlib.sha256(m.canonical({'seed':20260901,'purpose':'TRAIN_REFERENCE','project':'synthetic_project',
        'model_identity_sha256':'model','row_identifier':'row_0000'})).hexdigest()
    assert m.stable_key('synthetic_project','model','row_0000','TRAIN_REFERENCE')==expected


def test_t1_identity_only_selection_and_local_subset():
    data=candidates('T1')
    fg=m.select_population(data,'synthetic_project',None,'T1_GLOBAL_FOREGROUND_SELECTION',256)
    assert len(fg)==256 and all(r['partition']=='T1' for r in fg)
    stripped=[{k:r[k] for k in ['project','partition','row_identifier']} for r in fg]
    local=m.select_population(stripped,'synthetic_project','model','T1_LOCAL_CASE_SELECTION',8)
    assert len(local)==8 and {r['row_identifier'] for r in local}<={r['row_identifier'] for r in fg}
    assert all('class' not in r for r in fg+local)
    with pytest.raises(m.FreezeError):
        m.select_population(data,'synthetic_project',None,'T1_GLOBAL_FOREGROUND_SELECTION',256,True)
    for extra in ['class','prediction','confidence','residual','SHAP','correctness']:
        with pytest.raises(m.FreezeError):
            m.select_population([{**data[0],extra:1}],'synthetic_project',None,'T1_GLOBAL_FOREGROUND_SELECTION',256)
    with pytest.raises(m.FreezeError):
        m.select_population(candidates('T2'),'synthetic_project',None,'T1_GLOBAL_FOREGROUND_SELECTION',256)
    with pytest.raises(m.FreezeError):
        m.select_population([data[0],data[0]],'synthetic_project',None,'T1_GLOBAL_FOREGROUND_SELECTION',256)


def test_feature_and_text_exactness_from_immutable_representations():
    import struct
    reg=read('feature_order_registry.json')
    assert reg['numeric_names']==m.FEATURES
    assert len(reg['base_predictors'])==168
    text=read('text_representation_registry.json')
    assert len(text['states'])==56
    for logical,state in text['states'].items():
        rep=m.read(m.STORE/state['representation_object']['path'])
        assert state['vocabulary_sha256']==m.digest(rep['vocabulary'])
        assert state['final_column_order']==rep['feature_order']
        assert state['feature_order_sha256']==m.digest(rep['feature_order'])
        assert state['tokenizer_rules']==rep['parameters']
        assert all(rep['vocabulary'][token]==i for i,token in enumerate(rep['feature_order']))
        assert hashlib.sha256(struct.pack('<'+'d'*len(rep['idf']),*rep['idf'])).hexdigest()==state['idf_sha256']
        assert reg['base_predictors'][logical]['order']==rep['feature_order']


def test_tolerances_budgets_stability_heterogeneity_and_e3():
    f=read('xai_fidelity_contract.json')
    assert f['LR_logit']['relative_bound']==f['fusion_meta_logit']['relative_bound']==1e-10
    assert f['LR_sigmoid_absolute']==f['fusion_sigmoid_absolute']==1e-10
    assert f['TreeSHAP']['relative_bound']==1e-6 and f['TreeSHAP']['approximate'] is False
    assert f['global_reconstruction_absolute_where_applicable']==1e-12
    b=read('xai_query_budget.json')['per_scope']
    assert b==m.read(m.S55/'query_budget_policy.json')['per_scope']
    assert b['TRAIN_background_unique_rows_max']==b['T1_global_foreground_unique_rows_max']==256
    assert b['T1_local_cases_max']==8 and b['primary_attribution_row_evaluations_max_including_stability']==5120
    st=read('xai_stability_contract.json')
    assert st['seeds']==list(range(20260901,20260921)) and st['top_k']==[3,10]
    assert st['deterministic_method_max_absolute_attribution_difference']==1e-12
    assert st['population_reselection_by_stability_seed'] is False
    h=read('xai_heterogeneity_contract.json')
    assert h['cross_family_thresholds']==st['thresholds']=={'Jaccard_min':0.6,'Spearman_min':0.7,'sign_agreement_min':0.8,'TV_max':0.25}
    assert h['cross_family_minimum']==3 and h['stable_minimum_PASS_projects']==11
    assert h['stable_maximum_material_reversal_projects']==1
    assert read('calibration_e3_contract.json')['distribution']=={'RAW':375,'ISOTONIC':14}
    assert read('correlation_group_contract.json')['absolute_threshold']==0.7


def test_result_schemas_complete_and_reject_wrong_scales_partitions():
    schema=read('xai_result_schema.json')
    assert schema['$schema']=='https://json-schema.org/draft/2020-12/schema'
    assert schema['oneOf']==[{'$ref':'#/$defs/E1'},{'$ref':'#/$defs/E2'}]
    for name,definition in schema['$defs'].items():
        required=set(definition['required'])
        common={'project','algorithm','configuration','row_identifier','partition','method','explanation_scale',
                'baseline','attribution_sum','model_output','reconstructed_output','residual','runtime_hash',
                'model_state_hash','population_selection_hash'}
        assert common<=required
        if name=='E1':
            assert {'modality','feature_identity','feature_value','attribution_value'}<=required
        else:
            assert {'modality_probability','beta','raw_contribution','reference_mean_probability',
                    'centered_contribution','meta_logit','fused_probability'}<=required
        sample={}
        for key in required:
            prop=definition['properties'][key]
            sample[key]=(prop['const'] if 'const' in prop else prop['enum'][0] if 'enum' in prop
                         else 1.0 if prop.get('type')=='number' else 'a'*64 if 'pattern' in prop else 'test')
        sample['algorithm']='Logistic Regression'
        sample['configuration']='C' if name=='E1' else 'C+P'
        assert m.validate_schema_record(sample,name)
        with pytest.raises(m.FreezeError):
            m.validate_schema_record({**sample,'partition':'T2'},name)
        with pytest.raises(m.FreezeError):
            m.validate_schema_record({**sample,'explanation_scale':'SILENTLY_CONVERTED'},name)
        with pytest.raises(m.FreezeError):
            m.validate_schema_record({**sample,'runtime_hash':'wrong'},name)
        with pytest.raises(m.FreezeError):
            m.validate_schema_record({**sample,'residual':float('nan')},name)


def test_guard_no_queries_attributions_metrics_or_immutable_writes():
    for path in [ROOT/'data/source.csv',m.DATA_FREEZE/'temporal_partition_manifest.jsonl.gz',
                 ROOT/'audits/q1-heldout-governance-calibration-freeze/1.0.0/t2_identity_integrity.json',
                 ROOT/'audits/q1-t1-confirmatory-execution/1.0.0/results/t1_prediction_evidence.jsonl.gz']:
        with pytest.raises(PermissionError):
            m.guard('open',(str(path),'rb',0))
    for path in [m.SMOKE/'MANIFEST.sha256',m.STORE/'objects/test',ROOT/'.venv/pyvenv.cfg',ROOT/'.venv-xai-s56/pyvenv.cfg']:
        with pytest.raises(PermissionError):
            m.guard('open',(str(path),'wb',0))
    source=ast.parse((ROOT/'src/evaluation/q1_primary_xai_population_freeze.py').read_text())
    forbidden={'fit','fit_transform','partial_fit','predict','predict_proba','decision_function','shap_values','TreeExplainer',
               'dump','save_model','average_precision_score','roc_auc_score','f1_score','matthews_corrcoef',
               'recall_score','precision_score','brier_score_loss','permutation_importance'}
    for n in ast.walk(source):
        if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute):
            assert n.func.attr not in forbidden
        if isinstance(n,(ast.Import,ast.ImportFrom)):
            names=[a.name for a in n.names] if isinstance(n,ast.Import) else [n.module or '']
            assert not any(x.split('.')[0] in ['shap','joblib','sklearn','xgboost','lightgbm','lime','dice_ml'] for x in names)


def test_missing_population_source_is_not_reported_as_success():
    status=read('population_selection_summary.json')
    assert status['status']=='NOT_FROZEN_SOURCE_ACCESS_CONTRACT_BLOCKED'
    assert status['outcome']=='PRIMARY_XAI_T1_SELECTION_CONTRACT_FAILURE'
    assert status['population_checks_passed'] is False
    for filename in ['train_reference_population.jsonl','t1_global_foreground_population.jsonl',
                     't1_local_case_population.jsonl','correlated_feature_groups.jsonl']:
        assert rows(filename)==[]
    counters=read('xai_governance_counters.json')
    assert counters['T1_XAI_POPULATION_FREEZE_ACCESS_COUNT']==1
    assert counters['T1_AGGREGATE_IDENTITY_REGISTRY_ACCESS_COUNT']==1
    assert counters['T1_IDENTITY_ROW_READ_COUNT']==0
    for key in ['T1_XAI_MODEL_QUERY_COUNT','T1_XAI_ATTRIBUTION_EXECUTION_COUNT','T2_ACCESS_COUNT',
                'predictive_metric_count','artifact_mutation_count','reconstruction_count','refit_count','recalibration_count']:
        assert counters[key]==0
    assert counters['T2_STATE']=='DENY_SEALED_REVIEWER_RESERVE'
    assert read('sprint56_3_execution_prerequisites.json')['Sprint56_3_authorized'] is False


def test_frozen_evidence_and_store_unchanged_after_governance():
    before=read('preexecution_integrity.json')
    after=read('postexecution_integrity.json')
    assert before['object_store']==after['object_store']
    assert before['predictive_inventory']==after['predictive_inventory']==m.inventory()
    assert before['protected']==after['protected']
    assert all(m.sha(ROOT/name)==sha for name,sha in before['protected'].items())


def test_manifest_exact_and_complete():
    entries={}
    for line in (OUT/'MANIFEST.sha256').read_text().splitlines():
        sha,name=line.split('  ',1)
        assert name not in entries
        entries[name]=sha
    assert set(entries)=={p.name for p in OUT.iterdir() if p.is_file() and p.name!='MANIFEST.sha256'}
    assert all(m.sha(OUT/name)==sha for name,sha in entries.items())
