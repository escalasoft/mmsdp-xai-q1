"""Sprint 56.2 metadata governance and fail-closed population preflight.

Only named governance records and immutable model-object hashes are read.
No model deserialization, prediction, attribution or mixed dataset stream opens.
Population materialization requires a separately addressable TRAIN/T1 source;
opaque traversal of T2 is not treated as zero access.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import struct
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'audits/q1-primary-xai-population-freeze/1.0.0'
SMOKE = ROOT / 'audits/q1-primary-xai-runtime-smoke/1.0.0'
S55 = ROOT / 'audits/q1-xai-runtime-freeze/1.0.0'
STORE = ROOT / 'audits/q1-xai-reconstruction-execution/1.0.0'
G4 = ROOT / 'audits/q1-xai-reconstruction-equivalence-g4/1.0.0'
G5 = ROOT / 'audits/q1-xai-final-output-equivalence-g5/1.0.0'
G3 = STORE / 'dispositions/block7b_partial_eligibility/1.0.0'
DATA_FREEZE = ROOT / 'audits/q1-apachejit-final-dataset-freeze/1.0.0'
BRANCH = 'sprint-10/q1-primary-xai-execution'
SEED = 20260901
EXCLUDED = {('apache/zeppelin', 'Logistic Regression', c) for c in ['C+T', 'P+T', 'C+P+T']}
FEATURES = {'C': ['la','ld','nf','nd','ns','ent'], 'P': ['ndev','age','nuc','aexp','arexp','asexp']}
METHODS = {'Logistic Regression': 'ANALYTICAL_LINEAR_LOGIT_DECOMPOSITION',
           'Random Forest': 'EXACT_TREESHAP_POSITIVE_CLASS_OUTPUT',
           'XGBoost': 'EXACT_TREESHAP_NATIVE_RAW_MARGIN', 'LightGBM': 'EXACT_TREESHAP_NATIVE_RAW_MARGIN'}
SCALES = {'Logistic Regression':'LOGIT','Random Forest':'POSITIVE_CLASS_PROBABILITY',
          'XGBoost':'NATIVE_RAW_MARGIN','LightGBM':'NATIVE_RAW_MARGIN'}
THREADS = ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','VECLIB_MAXIMUM_THREADS']
READS = set()


class FreezeError(RuntimeError):
    pass


def canonical(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(',', ':'), allow_nan=False)+'\n').encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def rows(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def save(name, value):
    (OUT / name).write_bytes(canonical(value))


def save_rows(name, values):
    with (OUT / name).open('wb') as f:
        for v in values:
            f.write(canonical(v))


def inventory():
    return {'python':platform.python_version(), 'packages':sorted(
        [{'name':d.metadata['Name'],'version':d.version} for d in importlib.metadata.distributions()],
        key=lambda r:r['name'].lower())}


def guard(event, args):
    if event != 'open' or not isinstance(args[0], (str,bytes,os.PathLike)):
        return
    p = Path(os.fsdecode(args[0])).resolve()
    mode, flags = args[1] or '', args[2] or 0
    writing = any(c in mode for c in 'wax+') or bool(flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC))
    if not p.is_relative_to(ROOT):
        return
    name = p.relative_to(ROOT).as_posix()
    if p.is_relative_to(ROOT/'data') or (p.is_relative_to(DATA_FREEZE) and p.suffix == '.gz'):
        raise PermissionError('S56.2 denies mixed TRAIN/T1/T2 data streams: '+name)
    if 'prediction' in p.name.lower() or 't2_identity' in p.name.lower():
        raise PermissionError('S56.2 denies prediction payloads and T2 identities: '+name)
    if writing and (p.is_relative_to(ROOT/'audits') and not p.is_relative_to(OUT)
                    or p.is_relative_to(ROOT/'.venv') or p.is_relative_to(ROOT/'.venv-xai-s56')):
        raise PermissionError('S56.2 immutable write denied: '+name)
    if not writing and p.is_relative_to(ROOT/'audits'):
        READS.add(name)


def verify_manifest(base):
    verified = {}
    for line in (base/'MANIFEST.sha256').read_text().splitlines():
        expected, name = line.split('  ',1)
        path = base/name
        assert path.resolve().is_relative_to(base.resolve())
        if sha(path) != expected:
            raise FreezeError('PRIMARY_XAI_PROVENANCE_FAILURE: '+str(path))
        verified[path.relative_to(ROOT).as_posix()] = expected
    verified[(base/'MANIFEST.sha256').relative_to(ROOT).as_posix()] = sha(base/'MANIFEST.sha256')
    return verified


def object_integrity():
    registry = rows(STORE/'external_artifact_registry/external_artifact_inventory.jsonl')
    indexed = {r['relative_path']:r for r in registry}
    files = {p.relative_to(STORE).as_posix() for p in (STORE/'objects').rglob('*') if p.is_file()}
    expected = {line.split('  ',1)[1]:line.split('  ',1)[0] for line in (STORE/'MANIFEST.sha256').read_text().splitlines()
                if line.split('  ',1)[1].startswith('objects/')}
    if files != set(indexed) or files != set(expected):
        raise FreezeError('PRIMARY_XAI_STATE_READINESS_INCOMPLETE: object paths differ')
    snapshot = []
    for name in sorted(files):
        r = indexed[name]
        if sha(STORE/name) != expected[name] or expected[name] != r['sha256'] or (STORE/name).stat().st_size != r['size_bytes']:
            raise FreezeError('PRIMARY_XAI_STATE_READINESS_INCOMPLETE: '+name)
        snapshot.append({k:r[k] for k in ['relative_path','filename','sha256','size_bytes','extension_type','artifact_type']})
    snapshot_hash = hashlib.sha256(json.dumps(snapshot,sort_keys=True,separators=(',', ':'),ensure_ascii=False).encode()).hexdigest()
    prior = read(STORE/'external_artifact_registry/external_artifact_summary.json')
    assert len(files) == 5649 and sum(r['size_bytes'] for r in registry) == 2139594110
    assert snapshot_hash == prior['store_snapshot_sha256']
    return indexed, {'count':len(files),'bytes':sum(r['size_bytes'] for r in registry),
        'snapshot_sha256':snapshot_hash,'missing':0,'orphans':0,'all_sha256_verified':True}


def runtime_binding():
    prior = read(SMOKE/'isolated_runtime_lock.json')
    code = ('import importlib.metadata as m,json,platform;'
            'print(json.dumps({"python":platform.python_version(),"packages":sorted('
            '[{"name":d.metadata["Name"],"version":d.version} for d in m.distributions()],key=lambda r:r["name"].lower())}))')
    observed = json.loads(subprocess.check_output([str(ROOT/'.venv-xai-s56/bin/python'),'-c',code],text=True,
        env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'}))
    if prior['inventory'] != observed:
        raise FreezeError('PRIMARY_XAI_RUNTIME_BINDING_FAILURE')
    if inventory() != read(SMOKE/'predictive_inventory_before.json'):
        raise FreezeError('PRIMARY_XAI_RUNTIME_BINDING_FAILURE: predictive runtime changed')
    return {'status':'VERIFIED_EXACT_SPRINT56_1_LOCK','environment':str(ROOT/'.venv-xai-s56'),
        'runtime_hash':sha(SMOKE/'isolated_runtime_lock.json'),
        'source_lock_path':str((SMOKE/'isolated_runtime_lock.json').relative_to(ROOT)),
        'exact_inventory':observed,'platform':prior['platform'],'architecture':prior['architecture'],
        'required_threads':{k:'1' for k in THREADS},'metadata_only_no_scientific_imports':True,
        'runtime_changes_require':'PROSPECTIVE_XAI_RUNTIME_AMENDMENT', 'predictive_inventory_unchanged':True,
        'primary_execution_authorized_now':False}


def state_readiness(indexed, runtime):
    ledger = rows(G5/'xai_readiness_ledger.jsonl')
    g4 = {r['model_identity_sha256']:r for r in rows(G4/'g4_scope_results.jsonl')}
    g5 = {r['model_identity_sha256']:r for r in rows(G5/'g5_scope_results.jsonl')}
    g3 = {r['model_identity_sha256']:r for r in rows(G3/'scope_g1_g3_eligibility.jsonl')}
    journal = rows(STORE/'repetitions/rep_01/component_journal.jsonl')
    components = {}
    for r in journal:
        if '|FINAL_BASE|' in r.get('logical_id','') or '|FUSION_META|' in r.get('logical_id',''):
            assert r['logical_id'] not in components
            components[r['logical_id']] = r
    identities = [r['model_identity_sha256'] for r in ledger]
    assert len(identities) == len(set(identities)) == 389
    assert not EXCLUDED & {(r['project'],r['algorithm'],r['configuration']) for r in ledger}
    assert set(g3)-set(identities) == {key for key,r in g3.items() if (r['project'],r['algorithm'],r['configuration']) in EXCLUDED}
    scope_ledger, ready, feature_registry, text_registry = [], [], {}, {}
    smoke_loads = read(SMOKE/'model_state_load_compatibility.json')
    for s in sorted(ledger,key=lambda r:(r['project'],r['algorithm'],r['configuration'])):
        mid = s['model_identity_sha256']
        assert g3[mid]['eligibility_outcome'] == 'G1_G3_ELIGIBLE_FOR_FUTURE_G4_REVIEW'
        assert g4[mid]['G4_outcome'] == 'G4_PASS_ROW_LEVEL_RAW_EQUIVALENCE'
        assert g5[mid]['G5_outcome'] == 'G5_PASS_FINAL_OUTPUT_EQUIVALENCE'
        logicals = g3[mid]['required_base_components'][:]
        if g3[mid]['required_fusion_component']:
            logicals.append(g3[mid]['required_fusion_component'])
        state_records = []
        for logical in logicals:
            if logical not in components:
                raise FreezeError('PRIMARY_XAI_STATE_READINESS_INCOMPLETE: '+logical)
            r = components[logical]
            assert digest(r['canonical_state']) == r['canonical_state_sha256']
            assert r['g1'] == 'G1_PASS' and r['g2'] == 'G2_PASS'
            refs = {key:r[key] for key in ['executable','family_native_model','text_representation'] if r.get(key)}
            for ref in refs.values():
                assert ref['path'] in indexed and indexed[ref['path']]['sha256'] == ref['sha256']
                assert indexed[ref['path']]['size_bytes'] == ref['bytes']
            state = r['canonical_state']
            provenance = state['provenance']
            assert provenance['project'] == s['project']
            if r['unit_type'] == 'UNIMODAL_PIPELINE':
                assert mid in provenance['consuming_model_identity_sha256']
                modality = r['modality']
                model = state['model']
                assert model['classes'] == [0,1]
                if modality == 'T':
                    representation = read(STORE/r['text_representation']['path'])
                    names = representation['feature_order']
                    vocab = representation['vocabulary']
                    idf = representation['idf']
                    prep = state['preprocessing']
                    assert len(names) == len(set(names)) == len(vocab) == len(idf) == model['n_features_in']
                    assert all(vocab[t] == i for i,t in enumerate(names))
                    assert digest(vocab) == prep['vocabulary_sha256']
                    assert digest(names) == prep['feature_order_sha256']
                    assert prep['idf']['dtype'] == '<f8'
                    assert hashlib.sha256(struct.pack('<'+'d'*len(idf),*idf)).hexdigest() == prep['idf']['sha256']
                    assert representation['parameters'] == prep['parameters']
                    text_registry[logical] = {'status':'READY_VERIFIED', 'project':s['project'],'algorithm':s['algorithm'],
                        'representation_object':refs['text_representation'],'pipeline_object':refs['executable'],
                        'feature_count':len(names),'vocabulary_sha256':digest(vocab),
                        'idf_sha256':prep['idf']['sha256'],'idf_dtype':'<f8','feature_order_sha256':digest(names),
                        'tokenizer_rules':representation['parameters'],'token_column_map':'EXACT vocabulary IN IMMUTABLE REPRESENTATION OBJECT',
                        'final_column_order':names,'predictor_alignment':'EXACT_CANONICAL_MODEL_DIMENSION_AND_G5_STATE_EVIDENCE',
                        'loaded_state_alignment_in_this_sprint':False,
                        'semantics':'TOKEN_ASSOCIATION_ONLY_NO_INTENT_CAUSAL_OR_SEMANTIC_TRUTH_INFERENCE'}
                else:
                    names = FEATURES[modality]
                    assert len(names) == model['n_features_in']
                feature_registry[logical] = {'project':s['project'],'algorithm':s['algorithm'],'modality':modality,
                    'order':names,'order_sha256':digest(names),'preprocessing_state':state['preprocessing'],
                    'executable':refs['executable'],'status':'READY_VERIFIED','feature_reordering':'FORBIDDEN'}
            else:
                assert provenance['model_identity_sha256'] == mid
                order = s['configuration'].split('+')
                assert provenance['modality_order'] == order and state['n_features_in'] == len(order)
                assert state['classes'] == [0,1] and state['coef']['shape'] == [1,len(order)]
            state_records.append({'logical_id':logical,'status':'READY_VERIFIED','objects':refs,
                'canonical_state_sha256':r['canonical_state_sha256'],
                'Sprint56_1_load_status':smoke_loads.get(logical,{}).get('classification','NOT_DESERIALIZED_IN_REPRESENTATIVE_SMOKE'),
                'availability_is_not_universal_runtime_load_proof':True})
        role = 'E2' if '+' in s['configuration'] else 'E1'
        method = 'ANALYTICAL_LR_FUSION_DECOMPOSITION' if role == 'E2' else METHODS[s['algorithm']]
        scale = 'META_LOGIT' if role == 'E2' else SCALES[s['algorithm']]
        assert s['future_primary_method'] == method
        entry = {key:s[key] for key in ['project','algorithm','configuration','model_identity_sha256']}
        entry.update({'role':role,'method':method,'explanation_scale':scale,'G1_G3':g3[mid]['gate_results'],
            'G4':g4[mid]['G4_outcome'],'G5':g5[mid]['G5_outcome'],'repetition':'rep_01',
            'primary_scope_inclusion':'AUTHORIZED_FOR_POPULATION_FREEZE_ONLY','scientific_execution_authorized':False,
            'required_logical_states':logicals,'runtime_hash':runtime['runtime_hash'],
            'calibration':g5[mid]['frozen_calibration_state'],'population_status':'NOT_FROZEN',
            'G4_G5_T1_membership_digest':g5[mid]['T1_row_identity_digest'],
            'historical_T1_row_count':g5[mid]['T1_row_count']})
        scope_ledger.append(entry)
        ready.append({**entry,'state_readiness':'READY_VERIFIED','states':state_records,
                      'verification_basis':'G1-G5_CHAIN_PLUS_CANONICAL_METADATA_AND_EXTERNAL_OBJECT_SHA256; NO DESERIALIZATION_OR_QUERY'})
    assert len(ready) == 389 and len(feature_registry) == 168 and len(text_registry) == 56
    return scope_ledger, ready, feature_registry, text_registry


def stable_key(project, identity, row_identifier, purpose):
    return digest({'seed':SEED,'purpose':purpose,'project':project,
                   'model_identity_sha256':identity,'row_identifier':row_identifier})


def select_population(candidates, project, identity, purpose, limit, stratified=False):
    """Pure metadata selection; no file access. All candidates must be prevalidated."""
    partition = 'TRAIN' if purpose == 'TRAIN_REFERENCE' else 'T1'
    if any(r['partition'] != partition or r['project'] != project for r in candidates):
        raise FreezeError('PRIMARY_XAI_T1_SELECTION_CONTRACT_FAILURE: partition/project mismatch')
    if len({r['row_identifier'] for r in candidates}) != len(candidates):
        raise FreezeError('PRIMARY_XAI_T1_SELECTION_CONTRACT_FAILURE: duplicates')
    if stratified and partition != 'TRAIN':
        raise FreezeError('T1 label stratification forbidden by Sprint55')
    allowed_fields = {'project','partition','row_identifier','order_key'}
    if partition == 'TRAIN':
        allowed_fields.add('class')
    if any(set(r)-allowed_fields for r in candidates):
        raise FreezeError('Population candidate contains unauthorized labels/predictions/selection signals')
    annotated = [{**r,'selection_key':stable_key(project,identity,r['row_identifier'],purpose)} for r in candidates]
    ordering = lambda r:(r['selection_key'],r['row_identifier'])
    if stratified:
        groups = {k:sorted([r for r in annotated if r['class'] == k],key=ordering) for k in [0,1]}
        if any(r['class'] not in [0,1] for r in annotated):
            raise FreezeError('TRAIN class invalid')
        n = min(limit,len(annotated))
        quota = {0:n//2+n%2,1:n//2}
        selected = groups[0][:quota[0]]+groups[1][:quota[1]]
        used = {r['row_identifier'] for r in selected}
        selected += sorted([r for r in annotated if r['row_identifier'] not in used],key=ordering)[:n-len(selected)]
    else:
        selected = sorted(annotated,key=ordering)[:limit]
    return sorted(selected,key=ordering)


def contracts(scopes, runtime, features, texts):
    counts = Counter((r['algorithm'],r['role'],r['method']) for r in scopes)
    save('primary_xai_method_assignment.json',{'E1':METHODS,'E2':'ANALYTICAL_LR_FUSION_DECOMPOSITION',
        'counts':[{'algorithm':a,'role':r,'method':m,'count':n} for (a,r,m),n in sorted(counts.items())],
        'naive_fused_original_feature_SHAP':'FORBIDDEN','performance_based_scope_reduction':'FORBIDDEN'})
    save('xai_output_scale_contract.json',{'E1':SCALES,'E2':'META_LOGIT','RF_positive_class':1,
        'RF_semantics':'POSITIVE_CLASS_PROBABILITY_CONFIRMED_BY_SPRINT56_1',
        'TreeSHAP':{'approximate':False,'model_output':'raw','feature_perturbation':'tree_path_dependent',
                   'background':'PERSISTED_TRAIN_PATH_COUNTS; EXPLICIT_BACKGROUND_NOT_REQUIRED'},
        'calibrated_probability':'SEPARATE_OPTIONAL_E3_FIELD_NOT_AN_ADDITIVE_SCALE',
        'silent_scale_conversion':False,'required_record_fields':['explanation_scale','baseline','attribution_sum',
            'model_output','reconstructed_output','residual','final_probability_if_separately_available']})
    save('xai_runtime_binding.json',runtime)
    save('feature_order_registry.json',{'numeric_names':FEATURES,'base_predictors':features,
        'fusion_order':{'C+P':['C','P'],'C+T':['C','T'],'P+T':['P','T'],'C+P+T':['C','P','T']},
        'pipeline_transform_required':'EXACT_FROZEN_TRANSFORM_NO_REFIT','feature_reordering':'FORBIDDEN'})
    save('text_representation_registry.json',{'base_predictor_count':len(texts),'states':texts,
        'immutable_objects_define_exact_vocabulary_and_idf':True,'cross_project_literal_rank_averaging':
        'FORBIDDEN_UNLESS_VOCABULARY_TOKENIZER_COLUMN_SEMANTICS_AND_FEATURE_MEANING_STRICTLY_ALIGN',
        'permitted':['WITHIN_PROJECT_MODEL_TOKEN_RANK','SIGNED_MODEL_ASSOCIATION','MEAN_ABSOLUTE_ATTRIBUTION','LOCAL_TOKEN_CONTRIBUTION'],
        'prohibited':['DEVELOPER_INTENTION','CAUSAL_DEFECT_MECHANISM','SEMANTIC_TRUTH','PSYCHOLOGICAL_MEANING']})
    save('population_selection_contract.json',{'seed':SEED,'canonical_json':
        'UTF8 ensure_ascii=true sort_keys=true separators=comma:colon allow_nan=false; one terminal LF',
        'key_fields':['seed','purpose','project','model_identity_sha256','row_identifier'],
        'hash':'SHA256','selection_order':'selection_key ASC, row_identifier ASC',
        'TRAIN':{'unit':'PROJECT_SCOPE','maximum':256,'purpose':'TRAIN_REFERENCE','class_use':True,
            'allocation':'equal binary quota; odd remainder to class0; shortage reassigned by stable_key',
            'source':'SAME_PROJECT_TRAIN_ONLY','count_if_fewer_than_budget':'ALL_AVAILABLE',
            'class_policy_source':str((S55/'explanation_population_policy.json').relative_to(ROOT))},
        'T1_global':{'unit':'PROJECT_SHARED_BY_ALL_ELIGIBLE_SCOPES','maximum':256,
            'purpose':'T1_GLOBAL_FOREGROUND_SELECTION','model_identity_sha256_in_key':None,
            'strata':'UNSTRATIFIED','label_use':False,'prediction_read':False,
            'reason':'Sprint56.2 per-project foreground overrides Sprint55 per-model identity key. No single project-wide frozen model decision is designated; identity-only unstratified fallback preserves no model/performance selection.',
            'scientific_queries':0},
        'T1_local':{'unit':'PROJECT_SCOPE','maximum':8,'purpose':'T1_LOCAL_CASE_SELECTION',
            'source':'FROZEN_T1_GLOBAL_FOREGROUND_SUBSET','strata':'UNSTRATIFIED','label_use':False,
            'rationale':'Sprint55 permits unstratified fallback. No labels, correctness or confidence strata are authorized/used.',
            'unavailable_strata':['TP_TN_FP_FN_NOT_ALLOWED_BY_SPRINT55_LABEL_POLICY','CONFIDENCE_NOT_ALLOWED',
                                  'PREDICTED_BINARY_STRATA_NOT_AVAILABLE_IN_IDENTITY_ONLY_SOURCE'],
            'posthoc_substitution':False},
        'required_population_provenance':['row_identifier','partition','project','class_TRAIN_only','selection_key',
            'ordinal','selection_hash','ordering_hash','count','source_membership_digest'],
        'T2_access':False})
    save('correlation_group_contract.json',{**read(S55/'correlated_feature_policy.json'),
        'population':'ALL_VERIFIED_SAME_PROJECT_TRAIN_ROWS','feature_orders':FEATURES,
        'missing_policy':'FAIL_CLOSED_NO_IMPUTATION_FOR_DESCRIPTIVE_CORRELATION',
        'ties':'AVERAGE_RANK','constant_column':'UNDEFINED_NO_EDGE_RECORD_REASON',
        'edges':'abs(Spearman rho)>=0.70','edge_fields':['project','modality','feature_a','feature_b','rho','sign','abs_rho','n'],
        'group_order':'lexicographic sorted feature identities; singleton groups omitted'})
    save('e1_global_summary_contract.json',{'per_row':['attribution_vector','baseline','model_output','residual'],
        'global':['mean_absolute_attribution','signed_mean_attribution','rank','support_count'],
        'importance':'mean(abs(phi_j))','ties':'EXACT_FEATURE_IDENTITY_ASC',
        'LR_local_raw':'c_j=beta_j*x_j; eta=intercept+sum(c_j)',
        'LR_primary_global_centered':'phi_j=beta_j*(x_j-mu_j); phi0=intercept+sum(beta_j*mu_j)',
        'mu_j':'MEAN_FROZEN_TRANSFORMED_TRAIN_REFERENCE; COMPUTE_ONLY_AFTER_SPRINT56_3_AUTHORIZATION',
        'group_summary':'SUM_ATTRIBUTIONS_WITHIN_FROZEN_TRAIN_CORRELATED_GROUPS_THEN_AGGREGATE',
        'raw_cross_family_magnitude_normalization_or_pooling':False})
    save('fusion_explanation_contract.json',{'method':'ANALYTICAL_LR_FUSION_DECOMPOSITION','scale':'META_LOGIT',
        'eta':'alpha+sum(beta_m*p_m)','raw':'c_m=beta_m*p_m','centered':'phi_m=beta_m*(p_m-mu_m)',
        'baseline':'phi0=alpha+sum(beta_m*mu_m)','mu_source':'SAME_SCOPE_FROZEN_TRAIN_REFERENCE_MEAN_BASE_PROBABILITY',
        'mu_status':'NOT_COMPUTED_NO_MODEL_QUERIES_AUTHORIZED','modality_order':['C','P','T'],
        'apply_only_configured_modalities':True,'persist':['RAW_MODALITY_CONTRIBUTION','CENTERED_MODALITY_CONTRIBUTION'],
        'primary_global_cross_case_comparison':'CENTERED_MODALITY_CONTRIBUTION','causality':False,
        'naive_original_feature_fused_SHAP':False,'coefficients':'LEARNED_FUSION_BEHAVIOR_ONLY'})
    registry = read(G5/'calibration_state_registry.json')
    assert registry['authorized_distribution'] == {'RAW':375,'ISOTONIC':14}
    save('calibration_e3_contract.json',{'distribution':registry['authorized_distribution'],
        'registry_path':str((G5/'calibration_state_registry.json').relative_to(ROOT)),
        'registry_sha256':sha(G5/'calibration_state_registry.json'),'scope_mappings':[
            {k:s[k] for k in ['model_identity_sha256','project','algorithm','configuration','calibration']} for s in scopes],
        'future_flow':'raw_probability -> frozen_isotonic_mapping -> calibrated_probability',
        'feature_assignment_through_calibration':'FORBIDDEN','new_fitting':False,'layer':'E3_SEPARATE_FROM_E1_E2'})
    save('xai_fidelity_contract.json',{'LR_logit':{'relative_bound':1e-10,'formula':'abs(residual)<=1e-10*(1+abs(logit))'},
        'LR_sigmoid_absolute':1e-10,'fusion_meta_logit':{'relative_bound':1e-10,'formula':'abs(residual)<=1e-10*(1+abs(meta_logit))'},
        'fusion_sigmoid_absolute':1e-10,'TreeSHAP':{'relative_bound':1e-6,'formula':'abs(residual)<=1e-6*(1+abs(model_output))',
        'approximate':False},'global_reconstruction_absolute_where_applicable':1e-12,'check_rows':'EVERY_EXPLAINED_ROW',
        'nonfinite_values':'FAIL','post_output_tolerance_change':False})
    thresholds = {'Jaccard_min':0.60,'Spearman_min':0.70,'sign_agreement_min':0.80,'TV_max':0.25}
    save('xai_stability_contract.json',{**read(S55/'xai_stability_contract.json'),
        'status_categories':['PASS','MIXED','FAIL','INSUFFICIENT_EVIDENCE'], 'thresholds':thresholds,
        'diagnostic_definitions':{'Jaccard':'intersection(top_k_sets)/union(top_k_sets); k=min(k,n_features)',
            'Spearman':'rank correlation of mean-absolute attribution vectors over identical feature identities; average ranks for tied values; constants undefined',
            'sign_agreement':'fraction of equal signs of signed mean attribution among identities with either value nonzero; empty denominator undefined',
            'TV':'0.5*sum(abs(p-q)); p,q=mean-absolute vectors divided by their own positive totals; zero total undefined'},
        'normalization_boundary':'Within-vector normalization only for the explicitly defined TV diagnostic; never pool raw family scales.',
        'classification':{'INSUFFICIENT_EVIDENCE':'Any required diagnostic undefined or no repeated evidence',
            'PASS':'All four frozen diagnostic thresholds satisfied for every applicable top-k and repeat comparison',
            'FAIL':'No defined diagnostic meets its threshold, or attribution repeat diff>1e-12',
            'MIXED':'Remaining defined cases; never omit failed diagnostics'},
        'reference_run_seed':SEED,'seed_behavior':'Same frozen populations/order/runtime across seeds; no reselection; seed affects only supported RNG controls',
        'repeat_nondeterminism_is_execution_failure':True})
    save('xai_heterogeneity_contract.json',{'cross_family_minimum':3,'cross_family_thresholds':thresholds,
        'context':'same project, modality/configuration, aligned feature identities and matched result definitions; no raw-scale magnitude pooling',
        'comparison':'All eligible family pairs; no best-agreement model selection',
        'cross_family_failure':'MODEL_DEPENDENT_EXPLANATION_PATTERN','project_universe':14,
        'stable_minimum_PASS_projects':11,'stable_maximum_material_reversal_projects':1,
        'statuses':['INSUFFICIENT_EVIDENCE','STABLE_EXPLANATORY_PATTERN','PROJECT_SPECIFIC_PATTERN','HETEROGENEOUS_MODEL_DEPENDENT_PATTERN'],
        'precedence':['INSUFFICIENT_EVIDENCE if <3 comparable families or <3 evaluable projects or required diagnostic undefined',
            'HETEROGENEOUS_MODEL_DEPENDENT_PATTERN if any defined required cross-family agreement fails',
            'STABLE_EXPLANATORY_PATTERN if >=11/14 PASS projects and <=1 material reversal',
            'PROJECT_SPECIFIC_PATTERN otherwise'],
        'material_reversal_definition':'For each aligned family/context separately, opposite nonzero signed-mean direction to the across-project median direction on any feature in the deterministic top3 by median within-project normalized mean-absolute attribution; undefined alignment is insufficient evidence.',
        'text_alignment_required':'STRICT_VOCABULARY_TOKENIZER_COLUMN_SEMANTICS_AND_FEATURE_MEANING_ALIGNMENT',
        'normalization_only_for':'TV_AND_PROSPECTIVELY_DEFINED_REVERSAL_REFERENCE; NEVER_UNQUALIFIED_IMPORTANCE_POOLING',
        'universal_claims':'ALL_PROJECTS_AND_APPLICABLE_FAMILIES_ONLY','post_result_policy_changes':False})
    save('xai_query_budget.json',{'per_scope':read(S55/'query_budget_policy.json')['per_scope'],
        'current_stage_model_queries':0,'current_stage_attributions':0,'all_scope_maximum_primary_attribution_row_evaluations':389*5120,
        'background_semantics':'Tree path dependent counts need no explicit data; analytical references <=256 rows',
        'local_subset_not_extra_rows':True,'5120_includes_primary_and_stability':True,
        'count_every_repeated_row_evaluation':True,'T2':0,'increase_requires':'PROSPECTIVE_AMENDMENT_BEFORE_RESULTS'})
    fields1 = ['project','algorithm','configuration','modality','row_identifier','partition','method','explanation_scale',
        'feature_identity','feature_value','attribution_value','baseline','attribution_sum','model_output',
        'reconstructed_output','residual','runtime_hash','model_state_hash','population_selection_hash','contribution_form']
    fields2 = ['project','algorithm','configuration','row_identifier','partition','method','explanation_scale','modality',
        'modality_probability','beta','raw_contribution','reference_mean_probability','centered_contribution','baseline',
        'alpha','meta_logit','fused_probability','attribution_sum','model_output','reconstructed_output','residual',
        'runtime_hash','model_state_hash','population_selection_hash']
    numeric = {'feature_value','attribution_value','baseline','attribution_sum','model_output','reconstructed_output','residual',
        'modality_probability','beta','raw_contribution','reference_mean_probability','centered_contribution','alpha','meta_logit','fused_probability'}
    def schema(required):
        props = {f:({'type':'number'} if f in numeric else {'type':'string'}) for f in required}
        for f in ['runtime_hash','model_state_hash','population_selection_hash']:
            props[f] = {'type':'string','pattern':'^[0-9a-f]{64}$'}
        props['partition'] = {'const':'T1'}
        props['modality'] = {'enum':['C','P','T']}
        props['final_probability'] = {'type':['number','null']}
        props['feature_column_index'] = {'type':'integer','minimum':0}
        props['run_seed'] = {'type':'integer','minimum':20260901,'maximum':20260920}
        return {'type':'object','required':required,'properties':props,'additionalProperties':False}
    e1,e2 = schema(fields1),schema(fields2)
    e1['properties']['method'] = {'enum':sorted(set(METHODS.values()))}
    e1['properties']['explanation_scale'] = {'enum':sorted(set(SCALES.values()))}
    e1['properties']['contribution_form'] = {'enum':['RAW_LINEAR','CENTERED_LINEAR','TREESHAP']}
    e2['properties']['method'] = {'const':'ANALYTICAL_LR_FUSION_DECOMPOSITION'}
    e2['properties']['explanation_scale'] = {'const':'META_LOGIT'}
    save('xai_result_schema.json',{'$schema':'https://json-schema.org/draft/2020-12/schema',
        '$defs':{'E1':e1,'E2':e2},'oneOf':[{'$ref':'#/$defs/E1'},{'$ref':'#/$defs/E2'}],
        'provenance_requirements':'Match scope/method/scale/state/runtime/population ledgers; finite numbers only; E1/E2 per-row baseline and outputs must agree across features/modalities'})
    failures = ['XAI_STATE_NOT_READY','XAI_T1_POPULATION_NOT_READY','XAI_FEATURE_ALIGNMENT_FAIL','XAI_EXPLAINER_EXECUTION_FAIL',
        'XAI_FIDELITY_FAIL','XAI_DETERMINISM_FAIL','XAI_QUERY_BUDGET_VIOLATION','XAI_PROVENANCE_FAIL','XAI_RUNTIME_INTEGRITY_FAIL']
    save('xai_failure_policy.json',{'classifications':failures,'failed_scope_remains_failed':True,
        'rescue_by_changing':['PROJECT_FORBIDDEN','FAMILY_FORBIDDEN','VERSION_FORBIDDEN','BACKGROUND_FORBIDDEN',
            'FOREGROUND_FORBIDDEN','TOLERANCE_FORBIDDEN','ROW_REDUCTION_FORBIDDEN','T2_FORBIDDEN'],
        'coverage_counts_required':['eligible','executed','passed','failed','excluded','unresolved'],
        'denominator':389,'excluded':3,'failed_scopes_in_denominator':True,
        'post_hoc_best_observed_model_analysis':'ONLY_AFTER_PRIMARY_COMPLETION_SEPARATE_LABEL',
        'primary_substitutes':['NO_GAIN','NO_IMPURITY','NO_SPLIT_COUNT','NO_PERMUTATION','NO_APPROXIMATE_SHAP']})
    save('figure_and_provenance_contract.json',{'figure_execution_in_sprint56_2':False,
        'future_allowed':['MEAN_ABSOLUTE_ATTRIBUTION_BAR','BEESWARM','FROZEN_LOCAL_WATERFALL',
            'PROSPECTIVELY_SELECTED_DEPENDENCE','CENTERED_MODALITY_CONTRIBUTION','HETEROGENEITY_HEATMAP_RANK_SUMMARY','E3_CALIBRATION_MAPPING'],
        'dependence_feature_selection':'No high-priority feature is selected in this freeze; freeze exact identities in a separate prospective pre-output amendment before producing dependence plots.',
        'chain':['SPRINT54_MODEL_IDENTITY','RECONSTRUCTED_STATE_HASH','G4','G5','SPRINT56_1_RUNTIME_AND_REPRESENTATIVE_LOAD_READINESS',
            'SPRINT56_2_SCOPE','POPULATION_SELECTION_HASH','FUTURE_EXECUTION_ID','EXACT_RESULT_RECORD_IDS_AND_HASHES','FIGURE'],
        'figure_required_provenance':['result_record_ids','result_file_sha256','runtime_hash','state_hashes','population_hashes','rendering_code_sha256'],
        'plot_driven_reselection':False,'scientific_results_exist':False})


def validate_schema_record(value, layer):
    """Validate the exact scalar schema subset frozen here without dependencies."""
    schema=read(OUT/'xai_result_schema.json')['$defs'][layer]
    if not set(schema['required'])<=set(value) or set(value)-set(schema['properties']):
        raise FreezeError('Result schema required/unknown fields')
    for key,item in value.items():
        prop=schema['properties'][key]
        if 'const' in prop and item!=prop['const']:
            raise FreezeError('Result schema const: '+key)
        if 'enum' in prop and item not in prop['enum']:
            raise FreezeError('Result schema enum: '+key)
        types=prop.get('type',[])
        types=[types] if isinstance(types,str) else types
        if types:
            matches=(item is None and 'null' in types or isinstance(item,str) and 'string' in types
                or type(item) is int and 'integer' in types
                or type(item) in [int,float] and 'number' in types and math.isfinite(item))
            if not matches:
                raise FreezeError('Result schema type: '+key)
        if 'pattern' in prop and not (isinstance(item,str) and len(item)==64 and all(c in '0123456789abcdef' for c in item)):
            raise FreezeError('Result schema hash: '+key)
        if 'minimum' in prop and item<prop['minimum'] or 'maximum' in prop and item>prop['maximum']:
            raise FreezeError('Result schema bound: '+key)
    expected_method='ANALYTICAL_LR_FUSION_DECOMPOSITION' if layer=='E2' else METHODS.get(value['algorithm'])
    expected_scale='META_LOGIT' if layer=='E2' else SCALES.get(value['algorithm'])
    if value['method']!=expected_method or value['explanation_scale']!=expected_scale:
        raise FreezeError('Result schema algorithm/method/scale mismatch')
    return True


def prepare():
    assert subprocess.check_output(['git','symbolic-ref','--short','HEAD'],cwd=ROOT,text=True).strip() == BRANCH
    OUT.mkdir(parents=True,exist_ok=False)
    sys.addaudithook(guard)
    inherited = read(SMOKE/'sprint56_1_summary.json')
    assert inherited['outcome'] == 'PRIMARY_XAI_ISOLATED_RUNTIME_SMOKE_TEST_PASS'
    protected = {}
    for base in [SMOKE,S55,S55/'amendments/shap_compatibility_resolution/1.0.0',G4,G5]:
        protected.update(verify_manifest(base))
    indexed, objects = object_integrity()
    runtime = runtime_binding()
    scopes, ready, features, texts = state_readiness(indexed,runtime)
    save_rows('primary_xai_scope_ledger.jsonl',scopes)
    save_rows('model_state_readiness_ledger.jsonl',ready)
    contracts(scopes,runtime,features,texts)
    save('preexecution_integrity.json',{'branch':BRANCH,'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'protected':protected,'object_store':objects,'predictive_inventory':inventory(),
        'timestamp':datetime.now(timezone.utc).isoformat(),'source_sha256':sha(Path(__file__))})
    save('scope_readiness_summary.json',{'authorized_scopes':len(scopes),'excluded_scopes':sorted(EXCLUDED),
        'READY_VERIFIED':len(ready),'NOT_READY':0,'base_predictors':len(features),'TEXT_representations':len(texts),
        'required_unique_executable_states':len({state['logical_id'] for r in ready for state in r['states']}),
        'E1':sum(s['role']=='E1' for s in scopes),'E2':sum(s['role']=='E2' for s in scopes),
        'runtime_hash':runtime['runtime_hash'],'scientific_execution_authorized':False})
    save('metadata_access_log.json',{'paths':sorted(READS),'data_streams_opened':0,'T1_identity_rows_read':0,'T2_identity_rows_read':0})
    print(json.dumps(read(OUT/'scope_readiness_summary.json'),indent=2))


def write_manifest():
    (OUT/'MANIFEST.sha256').write_text(''.join(
        f'{sha(p)}  {p.name}\n' for p in sorted(OUT.iterdir()) if p.is_file() and p.name!='MANIFEST.sha256'))


def close_unavailable():
    """Persist the actual blocked state; never manufacture population rows."""
    sys.addaudithook(guard)
    scopes=rows(OUT/'primary_xai_scope_ledger.jsonl')
    before=read(OUT/'preexecution_integrity.json')
    outcome='PRIMARY_XAI_T1_SELECTION_CONTRACT_FAILURE'
    for filename in ['train_reference_population.jsonl','t1_global_foreground_population.jsonl',
                     't1_local_case_population.jsonl','correlated_feature_groups.jsonl']:
        if (OUT/filename).exists() and (OUT/filename).stat().st_size:
            raise FreezeError('Refuse to overwrite an existing population')
        save_rows(filename,[])
    prospective={r['project']:r['historical_T1_row_count'] for r in scopes}
    save('population_source_access_blocker.json',{
        'status':'NO_VERIFIED_INDEPENDENTLY_ADDRESSABLE_TRAIN_T1_SOURCE_LOCATED',
        'user_rule_source':'Sprint56.2 sections 23-24: minimum T1 identity metadata only; no T2 identity/feature/label read',
        'user_rule_quote':'No T2 identity read. No T2 feature read. No T2 label read.',
        'mixed_streams_not_opened':[
            str((DATA_FREEZE/name).relative_to(ROOT)) for name in ['temporal_partition_manifest.jsonl.gz',
                'row_identity_provenance.jsonl.gz','code_dataset.jsonl.gz','process_dataset.jsonl.gz']],
        'storage_evidence':'apachejit_final_dataset_freeze._write_jsonl_gz writes all rows to one GzipFile; _partition_rows sorts project and time, so later projects follow earlier-project T2 sections.',
        'Sprint56_1_prefix_not_generalizable':'Only first-project TRAIN prefix is accessible before heldout partitions; cannot reach all 14 projects with that method without traversing T2.',
        'readers_not_reused':['q1_xai_train_source_reconstruction._load_train_project scans mixed streams',
            'q1_t1_confirmatory_execution.structural_memberships explicitly loads T2 identities'],
        'alternative_prediction_payload_not_used':'Contains labels/probabilities outside minimum identity-only access; also cannot supply full TRAIN numeric correlation inputs.',
        'directory_metadata_search':'No relevant .gzi/.idx/.zran/.sqlite/.parquet/.arrow/.feather index or separated scientific population file located under audits/data/outputs; Git pack indexes are unrelated.',
        'required_input':{'TRAIN':'All same-project TRAIN identities with class and frozen CODE/PROCESS columns, original order and verifiable membership/feature provenance for all 14 projects',
            'T1':'Identity/project/partition/order only for all 14 projects; no labels, probabilities, confidence or correctness',
            'proof':'Must match the per-project frozen TRAIN membership digests and G4/G5 T1 identity digests; preserve upstream frozen feature provenance',
            'access':'Physically segregated files or a pre-existing independent random-access index that does not require processing T2'},
        'source_path_question_sent':True,'permission_to_relax_T2_rule_assumed':False,
        'source_preparation_reading_T2_authorized':False})
    save('population_selection_summary.json',{'status':'NOT_FROZEN_SOURCE_ACCESS_CONTRACT_BLOCKED',
        'outcome':outcome,'population_checks_passed':False,'scope_count':389,
        'TRAIN_reference_rows_frozen':0,'T1_global_rows_frozen':0,'T1_local_scope_rows_frozen':0,
        'correlated_groups_derived':0,'correlated_group_result':'NOT_COMPUTED_NOT_ZERO_CORRELATION',
        'counts_per_project':[{'project':p,'TRAIN_selected':0,'T1_global_selected':0,'T1_local_selected':0,
            'historical_T1_count_from_G5_metadata':n,'prospective_global_count_if_verified':min(n,256)}
            for p,n in sorted(prospective.items())],
        'prospective_global_capacity_only':sum(min(n,256) for n in prospective.values()),
        'prospective_TRAIN_scope_capacity_only':389*256,'prospective_local_scope_capacity_only':389*8,
        'empty_jsonl_meaning':'No population/group rows exist; not a successful empty selection',
        'schema_and_selector_synthetic_tests_are_not_real_population_validation':True})
    counters={name:0 for name in ['T1_XAI_POPULATION_FREEZE_ACCESS_COUNT','T1_IDENTITY_ROW_READ_COUNT',
        'T1_LABEL_READ_COUNT','T1_XAI_MODEL_QUERY_COUNT','T1_XAI_ATTRIBUTION_EXECUTION_COUNT',
        'primary_XAI_execution_count','scientific_SHAP_execution_count','scientific_analytical_attribution_execution_count',
        'TRAIN_model_query_count','TRAIN_attribution_execution_count','T2_ACCESS_COUNT','T2_IDENTITY_READ_COUNT',
        'T2_FEATURE_READ_COUNT','T2_LABEL_READ_COUNT','predictive_metric_count','artifact_mutation_count',
        'reconstruction_count','refit_count','retraining_count','recalibration_count','LIME_execution_count',
        'PDP_ICE_execution_count','counterfactual_execution_count','permutation_importance_execution_count',
        'package_installation_count','figure_generation_count','commit_count','push_count']}
    counters.update({'T2_STATE':'DENY_SEALED_REVIEWER_RESERVE','historical_Sprint54_predictive_access_scoring':[1,1],
        'T1_XAI_POPULATION_FREEZE_ACCESS_COUNT':1,
        'T1_AGGREGATE_IDENTITY_REGISTRY_ACCESS_COUNT':1,
        'T1_metadata_access_detail':'One read-only discovery access to q1-heldout-governance-calibration-freeze/1.0.0/t1_identity_integrity.json: aggregate count/digest/source path only, no row identities or labels.',
        'T1_rerun':False,'counter_basis':'Includes the read-only shell discovery of the aggregate T1 identity registry plus guarded metadata governance; no actual population stream opened; object/protected evidence hashes before/after',
        'Sprint56_1_smoke_counts_are_historical_not_scientific_and_unchanged':True})
    save('xai_governance_counters.json',counters)
    save('sprint56_3_execution_prerequisites.json',{'Sprint56_3_authorized':False,
        'Sprint56_2_complete':False,'Sprint56_2_outcome':outcome,
        'required':['Provide a verifiable segregated TRAIN/T1 source or existing independent index under the current no-T2-access rule.',
            'Resume Sprint56.2 to freeze all actual TRAIN/T1/local identities and derive CODE/PROCESS TRAIN Spearman groups; match membership digests and validate every selected row.',
            'Close Sprint56.2 with all readiness, runtime, populations, ordering, schemas and governance tests passing; no vacuous population PASS.',
            'Human review must explicitly grant Sprint56.3 scientific execution with exact scope, population, runtime and state hashes.',
            'Keep all 389 scopes, three exclusions, 375 RAW/14 ISOTONIC, frozen scales/tolerances/budgets and T2 seal.',
            'Require per-state runtime load and feature alignment checks before future attribution; representative Sprint56.1 load success is not universal load proof.',
            'No state repair, refit, reconstruction, calibration fitting, runtime/scope/population/tolerance changes or failure rescue without separate prospective authorization.'],
        'automatic_transition':False})
    indexed,objects=object_integrity()
    del indexed
    protected={name:sha(ROOT/name) for name in before['protected']}
    assert protected==before['protected'] and objects==before['object_store']
    assert inventory()==before['predictive_inventory']
    assert subprocess.check_output(['git','symbolic-ref','--short','HEAD'],cwd=ROOT,text=True).strip()==BRANCH
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==before['head']
    save('postexecution_integrity.json',{'protected':protected,'object_store':objects,'predictive_inventory':inventory()})
    readiness=read(OUT/'scope_readiness_summary.json')
    counts=read(OUT/'primary_xai_method_assignment.json')['counts']
    table='\n'.join(f"| {r['algorithm']} | {r['role']} | {r['method']} | {r['count']} |" for r in counts)
    validations=read(OUT/'validation_results.json') if (OUT/'validation_results.json').exists() else {'status':'PENDING'}
    report=f'''# Sprint 56.2 — Primary XAI Authorization and Population Freeze

`{outcome}`

State/runtime governance is verified. **The population freeze is incomplete, not ready for scientific execution.** No scientific XAI or population selection was executed. Empty population/group JSONL files explicitly mean unavailable outputs.

## A–H. Inherited state, universe and readiness

- **A. Branch / HEAD:** `{BRANCH}` / `{before['head']}`. No commit or push.
- **B. Inherited Sprint56.1:** `PRIMARY_XAI_ISOLATED_RUNTIME_SMOKE_TEST_PASS`; `TRAIN_ONLY_RUNTIME_VALIDATION_NO_SCIENTIFIC_XAI_CLAIM`. Sprint54 `MIXED_CONFIRMATORY_EVIDENCE` and Sprint55 closed/G1–G5 readiness remain preserved.
- **C. Authorized universe:** exactly 389 unique scopes, included for governance/population freeze; scientific execution is false for every row.
- **D. Exclusions:** exactly three: apache/zeppelin | Logistic Regression | C+T; P+T; C+P+T. No rescue or new exclusions.
- **E. Readiness:** 389/389 `READY_VERIFIED`; 0 `NOT_READY`. The 389 distinct required executable states include 168 final bases and 221 fusion meta-learners. Every reference resolves through canonical metadata, external registry SHA256 and G1–G5 PASS. No deserialization or model query occurred. Load compatibility for untested states is not inferred from representative smoke success.
- **F–G. Methods:** 168 unimodal E1 and 221 multimodal E2 scopes:

| Algorithm | Role | Method | Count |
|---|---|---|---:|
{table}

- **H. Runtime binding:** `.venv-xai-s56`; Sprint56.1 lock SHA256 `{readiness['runtime_hash']}`. Python 3.11.14, NumPy 2.3.5, SciPy 1.17.1, scikit-learn 1.9.0, XGBoost 3.2.0, LightGBM 4.6.0, SHAP 0.51.0, Numba 0.62.1, llvmlite 0.45.1, joblib 1.5.3, cloudpickle 3.1.2. Exact installed package inventory matches; predictive inventory unchanged. Any runtime amendment must be prospective. All required execution thread controls remain 1.

The external store remains 5,649 objects / 2,139,594,110 bytes, zero missing references/orphans. Every object hash was checked before and after; snapshot `{objects['snapshot_sha256']}`. Sprint55 and Sprint56.1 manifests and artifact bytes are unchanged.

## I–M. Populations and representation

- **I. TRAIN references actually frozen:** 0. Planned ceiling 256 per scope, label-stratified only on TRAIN; no fabricated selected identities or membership hashes.
- **J. T1 global foreground actually frozen:** 0. Planned ceiling 256 per project shared by its scopes. Historical G5 aggregate counts imply a prospective capacity of {sum(min(n,256) for n in prospective.values())} distinct identities, but this is not a selected population.
- **K. Local cases actually frozen:** 0. Planned ceiling 8 per scope, subset of its project foreground. No correctness, confidence or label strata: Sprint55 explicitly sets T1 label use to false. The identity-only unstratified fallback is documented before any output; a shared project foreground takes precedence over Sprint55's per-model selection-key scope under the explicit Sprint56.2 instruction.
- **L. Feature/TEXT registry:** 168 final-base feature orders and all 56 TEXT representations verified. Vocabulary, IDF float64 bytes, token-column map, tokenizer parameters, exact feature order and canonical predictor dimensions agree with immutable persisted metadata. CODE order: la, ld, nf, nd, ns, ent. PROCESS order: ndev, age, nuc, aexp, arexp, asexp. Fusion preserves applicable C/P/T order. This is metadata/state readiness, not newly executed model transformation validation.
- **M. Correlated groups actually derived:** not computed. The empty JSONL is not evidence of zero correlated groups. Frozen rule: same-project TRAIN only, absolute Spearman rho >=0.70, connected components, omit singletons, record signs/magnitudes; no causal or SHAP redefinition.

### Access blocker

The available original membership/identity/CODE/PROCESS files are single gzip streams combining TRAIN, VALIDATION, T1 and T2. The generator writes all project rows sequentially. Existing readers either deserialize all partition identities including T2 or scan mixed payload rows. The Sprint56.1 first-project TRAIN-prefix method cannot reach later projects without traversing earlier T2 sections. No relevant segregated source or independent access index was located during metadata-only discovery.

The user's section24 explicitly states: **“No T2 identity read. No T2 feature read. No T2 label read.”** No mixed stream was opened, filtered, fully hashed, indexed or traversed in this sprint. Discarding T2 after reading it would not satisfy that boundary. The source-path question was sent while state/contract work proceeded; no permission to relax the rule was inferred.

Completion requires verifiable, independently addressable TRAIN identities/classes/CODE/PROCESS values and T1 identity-only metadata for all 14 projects, matching the frozen per-project membership digests and original feature provenance. Creating such an export by accessing T2 is not authorized here. See `population_source_access_blocker.json` for the exact input contract.

## N–R. Frozen prospective contracts

- **N. Budgets:** TRAIN <=256; global T1 <=256 per project; local <=8 per scope within foreground; every explained row gets fidelity checks. Total primary-plus-stability row evaluations <=5,120 per scope, including all repeated evaluations. No post-output increases.
- **O. Fidelity:** LR/fusion absolute residual <=1e-10*(1+absolute logit); sigmoid <=1e-10; exact TreeSHAP <=1e-6*(1+absolute model output); applicable global reconstruction <=1e-12. Approximate SHAP false. RF positive-class probability; LR logit; XGB/LGB native raw margin; fusion meta-logit. No silent scale conversion.
- **P. Stability:** seeds 20260901–20260920, unchanged populations, top-k 3/10, repeat attribution difference <=1e-12; Jaccard >=0.60, Spearman >=0.70, sign agreement >=0.80, TV <=0.25. PASS/MIXED/FAIL/INSUFFICIENT_EVIDENCE definitions frozen; undefined diagnostics are not silently omitted.
- **Q. Heterogeneity:** >=3 comparable families; every eligible family pair retained. Stable project pattern requires >=11/14 PASS and <=1 material reversal, with explicit prospective reversal/alignment definitions. Project/model dependence and insufficient evidence take precedence over universal claims. TEXT cross-project pooling requires strict representation and semantic alignment.
- **R. Schemas:** E1/E2 JSON Schema definitions, exact required provenance fields, separate E3 mapping, deterministic global ranking and figure lineage are frozen. Future fused reference means are not computed now because they require prohibited model queries. E3 distribution remains 375 RAW /14 ISOTONIC. Figures are policy-only; no plots or attributions exist.

## S–Z. Counters and disposition

- **S. T1 population-freeze metadata access:** 1, the aggregate `t1_identity_integrity.json` registry read during source discovery (count/digest/source path only). Actual T1 identity and label rows read: 0; no T1 population stream opened.
- **T. T1 model queries:** 0.
- **U. Scientific SHAP, analytical attribution and primary XAI executions:** 0. TRAIN model/attribution executions in Sprint56.2 also 0.
- **V. T2:** all access/identity/feature/label counters 0; `DENY_SEALED_REVIEWER_RESERVE`.
- **W. Predictive metric recomputation:** 0.
- **X. Artifact mutations, reconstruction, refit, retraining, recalibration and installations:** 0. Historical Sprint54 access/scoring remains 1/1 and T1 rerun false.
- **Y. Sprint56.3:** not authorized. First resolve source access and finish/validate Sprint56.2, then obtain separate human scientific-execution authorization.
- **Z. Scientific disposition:** governance/state readiness completed; population freeze blocked/incomplete; no scientific XAI result or readiness-for-execution claim.

## Validation

`{json.dumps(validations,sort_keys=True)}`

Tests distinguish verified governance/synthetic-selector behavior from unavailable real populations. Actual TRAIN/T1 membership selection, local subset and correlated-group data validation are **NOT EXECUTED**, never vacuously PASS. Relevant Sprint55/Sprint56.1 regressions use only permitted evidence; exclusions are recorded explicitly. No earlier evidence or tests were edited.

READY FOR HUMAN REVIEW BEFORE PRIMARY XAI SCIENTIFIC EXECUTION
'''
    (OUT/'SPRINT56_2_PRIMARY_XAI_AUTHORIZATION_REPORT.md').write_text(report)
    save('sprint56_2_summary.json',{'outcome':outcome,'state_readiness_count':389,'E1':168,'E2':221,
        'population_freeze_complete':False,'scientific_disposition':'GOVERNANCE_READY_POPULATION_SOURCE_BLOCKED_NO_SCIENTIFIC_XAI',
        'Sprint56_3_authorized':False,'branch':BRANCH,'head':before['head']})
    save('closure_metadata_access_log.json',{'paths':sorted(READS),'population_streams_opened':0})
    write_manifest()
    print(outcome)


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('stage',choices=['prepare','close-unavailable','manifest'])
    {'prepare':prepare,'close-unavailable':close_unavailable,'manifest':write_manifest}[parser.parse_args().stage]()
