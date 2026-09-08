"""S56.2C: inspect existing artifacts, never invoke their predictors or transforms."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import warnings

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'audits/q1-primary-xai-frozen-evidence-reuse/1.0.0'
BRANCH='sprint-10/q1-primary-xai-execution'
STORE=ROOT/'audits/q1-xai-reconstruction-execution/1.0.0'
G4=ROOT/'audits/q1-xai-reconstruction-equivalence-g4/1.0.0'
G5=ROOT/'audits/q1-xai-final-output-equivalence-g5/1.0.0'
SMOKE=ROOT/'audits/q1-primary-xai-runtime-smoke/1.0.0'
PARENT=ROOT/'audits/q1-primary-xai-population-freeze/1.0.0'
T1=ROOT/'audits/q1-t1-confirmatory-execution/1.0.0/results/t1_prediction_evidence.jsonl.gz'
DEV=ROOT/'audits/q1-controlled-train-validation-baselines/1.0.0/campaign'
PREFIXES=['q1-xai-reconstruction-execution','q1-xai-reconstruction-equivalence-g4','q1-xai-final-output-equivalence-g5',
 'q1-xai-runtime-freeze','q1-primary-xai-runtime-smoke','q1-t1-confirmatory-execution','q1-controlled-train-validation-baselines',
 'q1-robustness-cv-statistics-calibration','q1-temporal-robustness-cv','q1-fusion-process-ablation','q1-modality-factorial']
SEARCH=[f'audits/{x}' for x in PREFIXES]+['data','artifacts','outputs','experiments']
PARTIAL='PARTIAL_FROZEN_EVIDENCE_REUSE_FEASIBLE'; NO='FROZEN_EVIDENCE_REUSE_NOT_FEASIBLE'
ALLOWED=set(); READS=set(); INSPECTED={}; CANDIDATES=[]
ZERO=['NEW_T1_SOURCE_ROW_READ_COUNT','T2_ACCESS_COUNT','T2_IDENTITY_READ_COUNT','T2_FEATURE_READ_COUNT','T2_LABEL_READ_COUNT',
 'T2_MODEL_QUERY_COUNT','T2_XAI_EXECUTION_COUNT','MODEL_QUERY_COUNT','SHAP_EXECUTION_COUNT',
 'ANALYTICAL_ATTRIBUTION_EXECUTION_COUNT','PREDICTIVE_METRIC_COUNT','RETRAIN_COUNT','REFIT_COUNT','RECONSTRUCTION_COUNT',
 'RECALIBRATION_COUNT','FIGURE_GENERATION_COUNT','POPULATION_SELECTION_COUNT','COMMIT_COUNT','PUSH_COUNT']

def canonical(x): return (json.dumps(x,ensure_ascii=True,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def digest(x): return hashlib.sha256(canonical(x)).hexdigest()
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for chunk in iter(lambda:f.read(1048576),b''): h.update(chunk)
    return h.hexdigest()
def rel(p): return Path(p).relative_to(ROOT).as_posix()
def load(p):
    INSPECTED[rel(p)]='JSON_STRUCTURE_AND_PROVENANCE'
    return json.loads(Path(p).read_text())
def lines(p):
    INSPECTED[rel(p)]='JSONL_STRUCTURE_AND_PROVENANCE'
    return [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()]
def save(name,x): (OUT/name).write_bytes(canonical(x))
def save_lines(name,rows): (OUT/name).write_bytes(b''.join(canonical(x) for x in rows))
def git(*args): return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()

def guard(event,args):
    if event!='open' or not isinstance(args[0],(str,bytes,os.PathLike)): return
    p=Path(os.fsdecode(args[0])).resolve()
    if not p.is_relative_to(ROOT): return
    name=rel(p); mode=args[1] or ''; flags=args[2] or 0
    writing=any(k in mode for k in 'wax+') or bool(flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC))
    if writing and not p.is_relative_to(OUT): raise PermissionError('S56.2C immutable write denied: '+name)
    if p.is_relative_to(ROOT/'audits/q1-apachejit-final-dataset-freeze') and p.suffix=='.gz':
        raise PermissionError('S56.2C mixed T2 source denied')
    allowed=(p.is_relative_to(OUT) or p in ALLOWED or name.startswith(('.venv/','.venv-xai-s56/')) or
      name.startswith(('src/','tests/')) and p.suffix in ['.py','.pyc'] or name in ['.gitignore','pyproject.toml'])
    if not allowed: raise PermissionError('S56.2C unapproved source/payload denied: '+name)
    if not writing and not p.is_relative_to(OUT): READS.add(name)

def membership_check(ids,expected,count):
    return len(ids)==count and len(set(ids))==count and digest(ids)==expected

def e2_decision(t1_complete,reference_complete,model_linkage):
    if t1_complete and reference_complete and model_linkage: return 'FULL_FROZEN_EVIDENCE_REUSE_FEASIBLE'
    if t1_complete and model_linkage: return PARTIAL
    return NO

def prepare():
    # Approval is specific to previously frozen TRAIN/development artifacts and
    # the isolated Sprint54 T1 ledger. No prefix permission for upstream datasets.
    for folder in [STORE,G4,G5,SMOKE,PARENT,DEV]:
        ALLOWED.update(p.resolve() for p in folder.rglob('*') if p.is_file())
    for name in ['q1-primary-xai-safe-population-source','q1-primary-xai-t2-semantic-boundary-amendment','q1-xai-runtime-freeze']:
        ALLOWED.update(p.resolve() for p in (ROOT/'audits'/name).rglob('*') if p.is_file())
    ALLOWED.add(T1.resolve()); ALLOWED.add((T1.parent/'MANIFEST.sha256').resolve())
    for name in ['audits/q1-temporal-robustness-cv/1.0.0/temporal_membership_provenance.json',
      'audits/q1-robustness-cv-statistics-calibration/1.0.0/raw_probability_provenance.json']:
        ALLOWED.add((ROOT/name).resolve())


def snapshot():
    result={}
    parents=[SMOKE,PARENT,ROOT/'audits/q1-primary-xai-safe-population-source/1.0.0',
      ROOT/'audits/q1-primary-xai-t2-semantic-boundary-amendment/1.0.0']
    for folder in parents:
        result[rel(folder)]={rel(p):{'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(folder.rglob('*')) if p.is_file()}
    # TRAIN-only content-addressed objects were authorized for this forensic read.
    result['objects']={p.name:{'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted((STORE/'objects').iterdir()) if p.is_file()}
    result['source_and_ignore']={n:sha(ROOT/n) for n in ['.gitignore','src/evaluation/q1_primary_xai_population_freeze.py',
      'src/evaluation/q1_primary_xai_safe_population_source.py','src/evaluation/q1_primary_xai_t2_semantic_boundary.py']}
    return result


def add_candidate(p,kind,projects,partition,usable,reason,coverage=None):
    row={'candidate_id':digest(rel(p)),'path':rel(p),'bytes':p.stat().st_size,'sha256':sha(p),
      'type':kind,'projects':sorted(projects),'partition_provenance':partition,'sufficiency':usable,
      'reason':reason,'identity_coverage':coverage,'payload_structurally_inspected':rel(p) in INSPECTED,
      'future_execution_authorized':False}
    CANDIDATES.append(row); return row


def audit():
    if git('symbolic-ref','--short','HEAD')!=BRANCH: raise ValueError('Wrong branch')
    OUT.mkdir(parents=True,exist_ok=False); prepare(); sys.addaudithook(guard)
    save('parent_integrity_before.json',snapshot())
    import numpy as np
    import joblib
    paths=subprocess.check_output(['rg','--files','--hidden','--no-ignore',*SEARCH,'-g','!**/.git/**','-g','!**/__pycache__/**'],cwd=ROOT,text=True).splitlines()
    save('search_inventory.json',{'roots':[{'path':x,'exists':(ROOT/x).exists(),'files':sum(p.startswith(x+'/') for p in paths)} for x in SEARCH],
      'paths':sorted(paths),'search':'Frozen representations, matrices, state and probability evidence; no upstream discovery or extraction.',
      'scientific_payload_search':'No content search of unknown data files; only approved artifacts inspected.'})
    scopes=lines(PARENT/'primary_xai_scope_ledger.jsonl'); projects=sorted({r['project'] for r in scopes})
    assert len(scopes)==389 and len(projects)==14
    excluded=load(PARENT/'scope_readiness_summary.json')['excluded_scopes']
    before=load(OUT/'parent_integrity_before.json')
    assert len(before['objects'])==5649 and sum(x['bytes'] for x in before['objects'].values())==2139594110
    registry=lines(STORE/'external_artifact_registry/external_artifact_inventory.jsonl')
    for r in registry:
        assert before['objects'][r['filename']]=={'sha256':r['sha256'],'bytes':r['size_bytes']}
    journal=lines(STORE/'repetitions/rep_01/component_journal.jsonl')
    final={r['logical_id']:r for r in journal if '|FINAL_BASE|' in r['logical_id'] or '|FUSION_META|' in r['logical_id']}
    g4=lines(G4/'g4_scope_results.jsonl'); g4index={(r['project'],r['algorithm'],r['configuration']):r for r in g4}
    provenance=load(DEV/'execution_provenance.json')['rows']; prov={(r['project'],r['algorithm_family']):r for r in provenance}
    train_registry=load(ROOT/'audits/q1-primary-xai-safe-population-source/1.0.0/reconciliation_spec.json')['TRAIN']
    # G4 producer writes digests and comparison summaries, never batch features.
    g4files=[rel(p) for p in G4.rglob('*') if p.is_file()]
    save('g4_t1_input_reuse_audit.json',{'historical_unique_T1_rows':3787,'historical_queries':389,'historical_comparisons':105862,
      'persisted_feature_matrices_found':0,'files':sorted(g4files),'result_schema':sorted(g4[0]),
      'producer':'src/evaluation/q1_xai_g4_row_equivalence.py:545–604 loads in-memory project rows/base probabilities;629 writes result summaries;719 manifest',
      'finding':'Exact row/probability digests survive; input rows and base_probabilities are local variables, no promoted cache or object reference in G4 outputs.',
      'status':NO,'T1_probability_alternative':rel(T1)})
    # Only the historically isolated T1 prediction evidence is opened. Its producer
    # explicitly serializes t1_rows; no source stream or T2-containing evidence.
    groups=defaultdict(list); labels={}; keys=set(); total=0; fields=set()
    with gzip.open(T1,'rt',encoding='utf-8') as stream:
        for line in stream:
            r=json.loads(line); total+=1; fields.update(r)
            key=(r['project'],r['algorithm'],r['configuration'])
            identity=(key,r['row_identifier'])
            if identity in keys: raise ValueError('Duplicate T1 scope/row')
            keys.add(identity)
            groups[key].append((r['row_identifier'],r['raw_predicted_probability'],r['model_identity_sha256']))
            ik=(r['project'],r['row_identifier']); label=r['benchmark_defined_observed_label']
            if ik in labels and labels[ik]!=label: raise ValueError('T1 label conflict')
            labels[ik]=label
    INSPECTED[rel(T1)]='HISTORICAL_T1_ROW_IDENTITIES_PROBABILITIES_MODEL_LINKAGE_FIELDS_ONLY_NO_METRICS'
    t1checks=[]
    for scope in scopes:
        key=(scope['project'],scope['algorithm'],scope['configuration']); values=groups[key]; ref=g4index[key]
        ids=[x[0] for x in values]
        assert membership_check(ids,ref['T1_row_identity_digest'],ref['T1_row_count'])
        assert {x[2] for x in values}=={scope['model_identity_sha256']}
        raw=np.asarray([x[1] for x in values],dtype='<f8')
        assert hashlib.sha256(raw.tobytes()).hexdigest()==ref['frozen_reference_probability_digest']
        t1checks.append({'project':key[0],'algorithm':key[1],'configuration':key[2],'rows':len(ids),
          'model_identity_sha256':scope['model_identity_sha256'],'identity_digest':digest(ids),'exact_G4_identity_order_and_reference_probability_digest':True})
    assert len(labels)==3787
    add_candidate(T1,'T1_IDENTITY_LABEL_BASE_AND_FUSION_OUTPUT_LEDGER',projects,'T1_ONLY_FROZEN_SPRINT54',PARTIAL,
      'All eligible T1 identities and unimodal probabilities available; no C/P/T input features. T1 labels exist and need not gate global input feasibility.',
      {'unique_T1_rows':len(labels),'physical_scope_rows':total,'eligible_scope_rows':sum(x['rows'] for x in t1checks),'eligible_scopes':389})
    # Inspect every final serialized pipeline/meta state structurally, without
    # executing estimators, transformations, reconstruction or attribution.
    state_summaries=[]; check_arrays={}; aligned_train=[]; textstates=[]
    for logical,r in sorted(final.items()):
        p=STORE/r['executable']['path']
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always'); obj=joblib.load(p)
        INSPECTED[rel(p)]='DESERIALIZED_ATTRIBUTE_NAMES_AND_SHAPES_ONLY'
        steps=dict(obj.steps) if hasattr(obj,'steps') else {'meta':obj}
        structure={name:{'class':type(step).__module__+'.'+type(step).__name__,
             'attributes':sorted(vars(step))} for name,step in steps.items()}
        forbidden_inputs={'X_fit_','_fit_X','X_train_','training_data','train_data','training_inputs','row_identifiers'}
        embedded=[name for name,step in steps.items() if set(vars(step)) & forbidden_inputs]
        assert not embedded
        project=logical.split('|')[0]
        state_summaries.append({'logical_id':logical,'path':rel(p),'sha256':sha(p),'structure':structure,
          'embedded_training_rows_found':False,'warnings':[{'category':type(w.message).__name__,'message':str(w.message)} for w in caught]})
        add_candidate(p,'FINAL_FROZEN_MODEL_STATE',[project],'TRAIN_FITTED_STATE_NOT_TRAIN_ROWS',PARTIAL,
          'Exact state/preprocessing only. Structural attributes contain no persisted row-level input matrix.')
        if '|FINAL_BASE|' in logical:
            cp=STORE/r['check_output']['path']; arr=np.load(cp,allow_pickle=False)
            INSPECTED[rel(cp)]='NPY_SHAPE_DTYPE_AND_DIGEST'
            assert arr.shape==(r['check_row_count'],) and arr.dtype==np.dtype('<f8')
            assert hashlib.sha256(arr.tobytes()).hexdigest()==r['train_source_check_output_sha256']
            assert r['check_row_identity_sha256']==train_registry[project]['membership_digest']
            assert len(arr)==train_registry[project]['count']
            check_arrays[logical]=arr
            aligned_train.append({'logical_id':logical,'rows':len(arr),'historical_TRAIN_membership_digest':r['check_row_identity_sha256'],
              'membership_list_available':project=='apache/activemq','frozen_final_model_output':True})
            add_candidate(cp,'FINAL_BASE_TRAIN_PROBABILITY_VECTOR',[project],'COMPLETE_ORDERED_TRAIN_OUTPUTS',PARTIAL,
              'One scalar final-base probability per TRAIN row, not feature inputs. Full ordered identity list separately located only for activemq.',{'shape':list(arr.shape),'identity_digest':r['check_row_identity_sha256']})
            if r['text_representation']:
                tp=STORE/r['text_representation']['path']; t=load(tp)
                textstates.append({'logical_id':logical,'path':rel(tp),'fields':sorted(t),'rows_embedded':False})
                add_candidate(tp,'TFIDF_FITTED_REPRESENTATION',[project],'TRAIN_FITTED_VOCABULARY_IDF_NOT_INPUT_ROWS',PARTIAL,
                  'Frozen vocabulary/IDF/column map survives; it does not contain a TRAIN/T1 transformed matrix or raw messages.')
        del obj
    save('reconstruction_train_input_reuse_audit.json',{'object_type_counts':dict(Counter(r['artifact_type'] for r in registry)),
      'all_5649_registry_hashes_verified':True,'final_states_structurally_deserialized':len(state_summaries),
      'final_base_probability_vectors':len(aligned_train),'exact_feature_training_matrices_found':0,
      'final_states':state_summaries,'train_output_alignment':aligned_train,'TEXT_state':textstates,
      'producer':'src/evaluation/q1_xai_train_source_reconstruction.py:410–472 persists pipeline, native state, tfidf state, and check OUTPUT probabilities;1356–1405 persists OOF probabilities.',
      'no_model_contains_training_rows_assumed':False,'scope_of_embedding_inspection':'All representative repetition01 final base/meta objects; OOF types classified from registry and exact persistence source, not inferred to embed matrices.'})
    # OOF rows are source-only TRAIN, excluding warmup. Validate identity digest
    # and lineage; do not substitute cross-fitted probabilities for final models.
    oof=[]
    for descriptor in sorted((STORE/'repetitions/rep_01').glob('oof_*.json')):
        d=load(descriptor); p=STORE/d['object']['path']; x=load(p); pr=prov[d['project'],d['algorithm']]
        ids=x['row_identifiers']; values=x['probabilities']; targets=x['targets']
        assert len(ids)==len(values)==len(targets)==pr['meta_training_row_count']
        assert digest(ids)==d['meta_training_membership_sha256']==pr['meta_training_membership_sha256']
        assert len(set(ids))==len(ids) and all(len(v)==3 for v in values)
        assert all(type(y) is int and y in [0,1] for y in targets)
        assert d['lineage']==pr['oof_lineage']
        assert len(ids)+pr['warmup_row_count']==train_registry[d['project']]['count']
        oof.append({'project':d['project'],'algorithm':d['algorithm'],'path':rel(p),'rows':len(ids),
          'warmup_rows_absent':pr['warmup_row_count'],'membership_digest':digest(ids),'exact_historical_meta_TRAIN_membership':True,
          'modalities':['C','P','T'],'OOF_predictors_differ_from_final_base':True,'E1_background':False,
          'E2_possible_reference':'Source-only OOF reference can support a different prospective baseline; not silently interchangeable with frozen final-base TRAIN reference.'})
        add_candidate(p,'OOF_TRAIN_IDENTITIES_LABELS_MODALITY_PROBABILITIES',[d['project']],'TRAIN_MINUS_WARMUP',PARTIAL,
          'Exact meta-training row identities/classes and OOF probabilities, no original feature vectors; cross-fitted model provenance differs from final bases.',{'rows':len(ids),'membership_digest':digest(ids)})
    save('oof_evidence_reuse_audit.json',{'candidates':oof,'all_14_projects':True,'algorithm_project_pairs':len(oof),
      'means_computed':False,'OOF_to_final_prediction_substitution':'FORBIDDEN_WITHOUT_EXPLICIT_PROSPECTIVE_REFERENCE_DECISION',
      'exact_missing':'Warmup identities/classes for complete primary TRAIN selection in13projects; no E1 feature matrix in OOF payloads.'})
    # Existing smoke representations and a complete one-project identity registry.
    pop=load(SMOKE/'train_only_population_manifest.json'); smoke=load(SMOKE/'selected_train_rows.json')
    assert membership_check(pop['train_ids_chronological'],train_registry['apache/activemq']['membership_digest'],train_registry['apache/activemq']['count'])
    assert len(smoke)==80 and all(r['partition']=='TRAIN' for r in smoke)
    smoke_ids={r['row_identifier'] for r in smoke}; assert smoke_ids<=set(pop['train_ids_chronological'])
    add_candidate(SMOKE/'selected_train_rows.json','SMOKE_TRAIN_C_P_RAW_TEXT_ROWS',['apache/activemq'],'TRAIN_ONLY',PARTIAL,
      '80 exact prior smoke rows, not full TRAIN and no class field; raw TEXT plus frozen vectorizer is valid representation, no transformation executed.',{'rows':80,'full_TRAIN_rows':len(pop['train_ids_chronological'])})
    add_candidate(SMOKE/'train_only_population_manifest.json','COMPLETE_ONE_PROJECT_TRAIN_IDENTITY_ORDER',['apache/activemq'],'TRAIN_ONLY',PARTIAL,
      'Full chronological TRAIN identities bind all12 final-base probability vectors; labels/features incomplete.',{'rows':len(pop['train_ids_chronological'])})
    fusion=load(SMOKE/'fusion_analytical_smoke.json')
    assert len(fusion['run_1']['reference_modality_probabilities'])==len(pop['background'])==64
    add_candidate(SMOKE/'fusion_analytical_smoke.json','LR_SMOKE_REFERENCE_PROBABILITIES_AND_MEANS',['apache/activemq'],'TRAIN_ONLY_SMOKE_SELECTION',PARTIAL,
      'Stored 64-row reference probabilities/means and16-row foreground inputs; smoke hash-selection differs from frozen primary selection. No mean or contribution recalculated.',{'reference_rows':64,'foreground_rows':16})
    # Non-campaign prior artifacts: evidence lineage, not a substitute dataset.
    # Read source/provenance field schemas, not aggregate result/metric tables.
    for name in ['audits/q1-temporal-robustness-cv/1.0.0/temporal_membership_provenance.json',
      'audits/q1-robustness-cv-statistics-calibration/1.0.0/raw_probability_provenance.json']:
        p=ROOT/name; x=load(p)
        add_candidate(p,'HISTORICAL_DEVELOPMENT_PROVENANCE',projects,'DEVELOPMENT_METADATA',NO,
          'Provenance/digest linkage, not a persisted raw feature matrix.',{'root_fields':sorted(x)})
    # Complete physical object inventory, including repeated/OOF objects that were
    # classified by exact serialization code rather than needlessly deserialized.
    present={r['path'] for r in CANDIDATES}
    for r in registry:
        p=STORE/r['relative_path']
        if rel(p) not in present:
            CANDIDATES.append({'candidate_id':digest(rel(p)),'path':rel(p),'bytes':r['size_bytes'],'sha256':r['sha256'],
              'type':r['artifact_type'],'projects':[],'partition_provenance':'TRAIN_ONLY_RECONSTRUCTION; PROJECT_LINKAGE_IN_JOURNALS',
              'sufficiency':PARTIAL,'reason':'Additional/repeated state or output object. No additional E1 matrix object type exists; representative final/OOF inputs separately inspected.',
              'payload_structurally_inspected':False,'hash_verified':True,'future_execution_authorized':False})
    # Existence/format-only findings for other locations; never decode unknown or mixed data.
    external=[]
    for name in paths:
        p=ROOT/name
        if name.startswith(('data/','artifacts/','outputs/','experiments/')) and p.suffix in ['.npy','.npz','.pkl','.joblib','.jsonl','.csv','.gz']:
            external.append({'path':name,'bytes':p.stat().st_size,'payload_inspected':False,
             'status':'PROVENANCE_INSUFFICIENT','reason':'No frozen389-scope ApacheJIT execution reference to this external/older-dataset artifact; no source recovery attempted.'})
    for p in sorted((ROOT/'audits/q1-apachejit-final-dataset-freeze/1.0.0').glob('*.gz')):
        external.append({'path':rel(p),'bytes':p.stat().st_size,'payload_inspected':False,'status':'T2_CONTAMINATED_ARTIFACT',
          'reason':'Known mixed canonical partition container; forbidden and unopened.'})
    save('other_location_findings.json',{'artifacts':external,'upstream_not_reopened':True,
      'older_fusion_factorial_state':'O1–O5 fitted_state artifacts belong to earlier origin-based dataset lineage, not frozen14-project final states; no extrapolation to current scopes.',
      'searches_include_existing_arrays_and_caches':True})
    e2=[]; project_matrix=[]
    for scope in scopes:
        if scope['role']!='E2': continue
        key=(scope['project'],scope['algorithm'],scope['configuration']); mods=scope['configuration'].split('+')
        base=[groups[scope['project'],scope['algorithm'],m] for m in mods]
        assert all([x[0] for x in b]==[x[0] for x in groups[key]] for b in base)
        meta=final[f'{scope["project"]}|{scope["algorithm"]}|FUSION_META|{scope["configuration"]}']
        assert meta['canonical_state']['provenance']['modality_order']==mods
        assert meta['canonical_state']['provenance']['model_identity_sha256']==scope['model_identity_sha256']
        e2.append({'project':scope['project'],'algorithm':scope['algorithm'],'configuration':scope['configuration'],
          'model_identity_sha256':scope['model_identity_sha256'],'T1_raw_modality_input_complete':True,'exact_modality_order':mods,
          'T1_rows':len(groups[key]),'TRAIN_final_base_outputs_present':True,'TRAIN_full_identity_order_present':scope['project']=='apache/activemq',
          'OOF_source_only_reference_rows_present':True,'primary_TRAIN_reference_contract_complete':False,
          'uncentered_local_algebra_input_ready':True,'centered_primary_global_input_ready':False,
          'sufficiency':e2_decision(True,False,True),
          'missing':'Complete primary TRAIN reference selection provenance/classes/identities; OOF or smoke subset cannot silently replace the frozen primary population.'})
    families=sorted({r['algorithm'] for r in scopes})
    save('e1_family_feasibility.json',{'families':[{'algorithm':a,'classification':'E1_REUSE_NOT_FEASIBLE',
      'eligible_scopes':sum(r['role']=='E1' and r['algorithm']==a for r in scopes),'complete_reusable_scopes':0,
      'state_ready':True,'T1_feature_rows_available':0,'partial_TRAIN_project':'apache/activemq','partial_TRAIN_rows':80,
      'reason':'All exact final model states available; no persisted G4 C/P/T input rows located.'} for a in families]})
    save('e1_modality_feasibility.json',{'modalities':[{'modality':m,'classification':NO,'eligible_scopes':56,'complete_reusable_scopes':0,
      'T1_feature_rows':0,'TRAIN_rows_available':80,'TRAIN_projects':['apache/activemq'],
      'representation':'Raw C/P or raw TEXT plus exact frozen vectorizer; no raw-text requirement if a transformed matrix existed.'} for m in ['CODE','PROCESS','TEXT']]})
    save('e2_multimodal_feasibility.json',{'classification':PARTIAL,'scopes':e2,'complete_primary_reusable_scopes':0,
      'raw_uncentered_T1_input_ready_scopes':len(e2),'centered_reference_needs_human_decision':True,
      'configuration_counts':dict(Counter(r['configuration'] for r in e2)),
      'important':'OOF scientific representation is reusable as OOF, but it is not the same prediction function or population as final-base TRAIN-reference evidence.'})
    for project in projects:
        project_matrix.append({'project':project,'eligible_scopes':sum(r['project']==project for r in scopes),
          'E1_eligible':12,'E1_complete_reusable':0,'E2_eligible':sum(r['project']==project for r in e2),
          'E2_raw_T1_input_ready':sum(r['project']==project for r in e2),'E2_complete_primary_reusable':0,
          'T1_identity_probability_coverage':'FULL','T1_feature_coverage':'ZERO',
          'TRAIN_feature_coverage':'PARTIAL_80_ROWS' if project=='apache/activemq' else 'ZERO',
          'TRAIN_ordered_identity_coverage':'FULL' if project=='apache/activemq' else 'PARTIAL_OOF_EXCLUDES_WARMUP',
          'TRAIN_final_probability_vector_coverage':'FULL','TRAIN_OOF_label_probability_coverage':'PARTIAL_EXCLUDES_WARMUP'})
    save('project_coverage_matrix.json',{'projects':project_matrix,'no_implicit_extrapolation':True})
    save('row_identity_reconciliation.json',{'T1':t1checks,'T1_unique_rows':len(labels),'T1_label_consistency_checked':True,
      'TRAIN_final_outputs':aligned_train,'OOF':oof,'complete_TRAIN_identity_registry_projects':['apache/activemq'],
      'exact_matching_only':True,'fuzzy_matching':False,'feature_value_identity_inference':False,
      'tail_alignment_not_materialized':'Producer orders OOF rows by forward blocks after warmup; possible future final-output tail linkage needs explicit population review, no population selected here.'})
    save('xai_graphics_feasibility.json',{'plots':[
      {'family':name,'classification':status,'reason':reason} for name,status,reason in [
      ('global mean(|SHAP|) bar plots','NOT_READY','E1 T1 input features absent'),('beeswarm plots','NOT_READY','E1 T1 features absent'),
      ('local waterfall plots','PARTIALLY_READY','Raw E2 modality inputs available; E1 and centered primary reference incomplete'),
      ('TEXT token-attribution plots','NOT_READY','T1 TFIDF/raw text rows absent despite exact vectorizers'),
      ('multimodal modality-contribution plots','PARTIALLY_READY','221 raw E2 input sets complete; centered reference unresolved'),
      ('project heterogeneity heatmaps','PARTIALLY_READY','E2 raw inputs across14projects; primary centered comparability not ready'),
      ('model-family comparison summaries','PARTIALLY_READY','Four-family E2 raw input coverage; no E1/centered global attribution evidence generated')]],
      'graphics_generated':False,'readiness_does_not_authorize_plotting':True})
    save('exact_missing_evidence.json',{'E1':'Exact T1 C/P values or transformed inputs and T1 rawTEXT or exact TFIDF rows for3787identities. TRAIN complete C/P/T representation beyond80activemqrows.',
      'E2':'Complete primary reference population linkage: full TRAIN identity/class lists and exact final-base probabilities aligned to that selection. Complete probability arrays exist; all-project complete identity/class registries not found.',
      'OOF':'OOF matrices retain exact identities/labels/CPT probabilities for source-only non-warmup rows in all56algorithm-project pairs. Using this population or these predictors as primary baseline requires explicit contract decision.',
      'T1_labels':'Already persisted for all3787T1rows; absence of labels is not an E1 blocker. Later local-case stratification requires separate selection authorization.',
      'no_feature_reconstruction_from_predictions':True})
    save('recommended_next_action.json',{'outcome':PARTIAL,'human_review_required':True,
      'recommendation':'Review separate E2 route using stored T1 base probabilities and existing TRAIN output arrays/OOF identity evidence. Explicitly decide reference-population/predictor semantics before any population freeze. Do not silently substitute OOF/smoke reference. E1 still needs frozen input representations.',
      'resume_Sprint56_2':False,'Sprint56_3_authorized':False,'queries_authorized':False,'plots_authorized':False})
    save_lines('frozen_artifact_candidate_inventory.jsonl',CANDIDATES)
    save_lines('train_evidence_inventory.jsonl',[r for r in CANDIDATES if r['type'] in ['FINAL_BASE_TRAIN_PROBABILITY_VECTOR','OOF_TRAIN_IDENTITIES_LABELS_MODALITY_PROBABILITIES','SMOKE_TRAIN_C_P_RAW_TEXT_ROWS','COMPLETE_ONE_PROJECT_TRAIN_IDENTITY_ORDER','LR_SMOKE_REFERENCE_PROBABILITIES_AND_MEANS','TFIDF_FITTED_REPRESENTATION']])
    save_lines('t1_evidence_inventory.jsonl',[r for r in CANDIDATES if r['path']==rel(T1)])
    provenance_rows=[]
    for r in CANDIDATES:
        if r.get('payload_structurally_inspected'):
            provenance_rows.append({'path':r['path'],'sha256':r['sha256'],'project_coverage':r['projects'],
              'chain':['FROZEN_APACHEJIT_SOURCE_NO_REOPEN','HISTORICAL_TRAIN_OR_T1_PARTITION','SPRINT54_OR55_EXECUTION','FROZEN_MANIFEST_AND_OBJECT_HASH',r['type'],'ROW_ID_OR_ORDER_DIGEST','REP01_FINAL_MODEL_LINKAGE','FUTURE_E1_OR_E2_COMPONENT'],
              'component_provenance':'EXACT_HISTORICAL_COMPONENT','primary_population_provenance':'INCOMPLETE_WHERE_STATED_IN_SCOPE_DISPOSITION',
              'reuse_limit':r['reason']})
    save_lines('provenance_reuse_ledger.jsonl',provenance_rows)
    train_candidates=[r for r in CANDIDATES if r['type'] in ['FINAL_BASE_TRAIN_PROBABILITY_VECTOR','OOF_TRAIN_IDENTITIES_LABELS_MODALITY_PROBABILITIES','SMOKE_TRAIN_C_P_RAW_TEXT_ROWS','COMPLETE_ONE_PROJECT_TRAIN_IDENTITY_ORDER','LR_SMOKE_REFERENCE_PROBABILITIES_AND_MEANS']]
    save('governance_counters.json',{**{k:0 for k in ZERO},'FROZEN_ARTIFACT_FILES_INSPECTED':len(INSPECTED),
      'FROZEN_TRAIN_ARTIFACTS_FOUND':len(train_candidates),'FROZEN_T1_ARTIFACTS_FOUND':1,
      'REUSABLE_TRAIN_ARTIFACTS':len(train_candidates),'REUSABLE_T1_ARTIFACTS':1,
      'REUSABLE_E1_SCOPES':0,'REUSABLE_E2_SCOPES':0,'PARTIALLY_REUSABLE_E2_SCOPES':len(e2),
      'HISTORICAL_T1_ARTIFACT_READ_COUNT':1,'HISTORICAL_T1_ARTIFACT_ROW_RECORDS_INSPECTED':total,
      'T2_STATE':'DENY_SEALED_REVIEWER_RESERVE','historical_Sprint54_predictive_access_scoring':[1,1],
      'definitions':'Artifact counts are distinct structurally inspected files; reusable artifacts count exact components, not complete primary scopes. Reusable scope counters require complete frozen primary reference+foreground contract. T1 read count is distinct historical row artifact files.',
      'hash_only_objects_verified':5649})
    save('scope_integrity.json',{'count':389,'excluded':excluded,'parent_scope_sha256':sha(PARENT/'primary_xai_scope_ledger.jsonl'),
      'branch':BRANCH,'HEAD':git('rev-parse','HEAD')})
    save('inspection_log.json',{'files':INSPECTED,'read_paths':sorted(READS),'no_model_methods_called':True})
    complete_forensics()


def complete_forensics():
    import sys
    s=sys.modules[__name__]
    from collections import defaultdict,Counter
    import json,gzip,sys
    s.prepare(); sys.addaudithook(s.guard)
    log=json.loads((s.OUT/'inspection_log.json').read_text())
    log['files']={k:v for k,v in log['files'].items() if not k.startswith(s.rel(s.OUT)+'/')}
    links=defaultdict(set)
    for jp in sorted((s.STORE/'repetitions').glob('rep_*/component_journal.jsonl')):
     for r in s.lines(jp):
      for key in ['executable','check_output','family_native_model','text_representation']:
       if r.get(key): links[s.rel(s.STORE/r[key]['path'])].add(r['logical_id'])
    for dp in sorted((s.STORE/'repetitions').glob('rep_*/oof_*.json')):
     d=s.load(dp); links[s.rel(s.STORE/d['object']['path'])].add(d['project']+'|'+d['algorithm']+'|OOF_MATRIX|C+P+T')
    rows=s.lines(s.OUT/'frozen_artifact_candidate_inventory.jsonl'); merged={}
    for r in rows:
     p=r['path']; r['logical_state_references']=sorted(links[p]); r['projects']=sorted(set(r['projects'])|{x.split('|')[0] for x in links[p]})
     if not r['projects']:
      r['project_coverage_status']='UNKNOWN_NOT_EXTRAPOLATED'
      r['sufficiency']='PROVENANCE_INSUFFICIENT'
     else: r['project_coverage_status']='EXPLICIT_REFERENCES'
     if p in merged:
      old=merged[p]; old['projects']=sorted(set(old['projects'])|set(r['projects'])); old['payload_structurally_inspected']|=r['payload_structurally_inspected']
     else: merged[p]=r
    # Development probability ledger is provably T1/T2-free by its producer's prewrite guard.
    p=s.DEV/'raw_prediction_ledger.jsonl.gz'; partition_counts=Counter(); fields=set(); identities=defaultdict(set)
    with gzip.open(p,'rt',encoding='utf-8') as stream:
     for line in stream:
      r=json.loads(line)
      assert r['partition'] not in ['T1','T2']
      partition_counts[r['partition']]+=1; fields.update(r)
      identities[r['project'],r['partition']].add(r['row_identifier'])
    s.INSPECTED[s.rel(p)]='FULL_FROZEN_DEVELOPMENT_LEDGER_SCHEMA_PARTITION_IDENTITY_INSPECTION_NO_METRICS'
    s.add_candidate(p,'DEVELOPMENT_PROBABILITY_LEDGER',sorted({k[0] for k in identities}),'TRAIN_VALIDATION_DEVELOPMENT_ONLY',s.PARTIAL,
     'Stored development probabilities/labels/identities, not feature inputs or final-base full-TRAIN predictions. Source producer refuses T1/T2 before writing.',
     {'schema':sorted(fields),'partition_record_counts':dict(partition_counts),'project_partition_unique_ids':[{ 'project':k[0],'partition':k[1],'rows':len(v)} for k,v in sorted(identities.items())]})
    merged[s.rel(p)]=s.CANDIDATES[-1]
    s.save('development_ledger_reuse_audit.json',{'path':s.rel(p),'sha256':s.sha(p),'schema':sorted(fields),
     'partition_record_counts':dict(partition_counts),'new_predictions_or_metrics':False,
     'producer':'src/experimentation/q1_controlled_result_campaign.py:322–353 row schema;897 rejects T1/T2;908 writes ledger',
     'TRAIN_reference_limit':'Forward score blocks and validation, not a complete class/identity registry including warmup. No feature vectors.',
     'scope_linkage':'Historical fold and selected candidate provenance; not silently relabelled as final-base TRAIN outputs.'})
    # Classify historical origin-based serialized candidates explicitly by source lineage.
    for prefix in ['q1-fusion-process-ablation','q1-modality-factorial']:
     for p in sorted((s.ROOT/'audits'/prefix/'1.0.0/fitted_state').glob('*.pkl')):
      merged[s.rel(p)]={'candidate_id':s.digest(s.rel(p)),'path':s.rel(p),'bytes':p.stat().st_size,
       'sha256':None,'hash_basis':'Not freshly read; different dataset lineage established from producer',
       'type':'OLDER_ORIGIN_MODEL_STATE','projects':[],'project_coverage_status':'ZERO_CURRENT_APACHEJIT_COVERAGE',
       'partition_provenance':'JIT_DEFECTS4J_DEVELOPMENT_ORIGINS_O1_O5','sufficiency':s.NO,
       'reason':'src/experimentation/q1_modality_factorial.py:102–118 loads jit_defects4j; not current ApacheJIT models/rows.',
       'payload_structurally_inspected':False,'future_execution_authorized':False}
    # Known mixed candidates remain excluded without hashing.
    other=json.loads((s.OUT/'other_location_findings.json').read_text())
    for r in other['artifacts']:
     if r['status']=='T2_CONTAMINATED_ARTIFACT':
      merged[r['path']]={'candidate_id':s.digest(r['path']),'path':r['path'],'bytes':r['bytes'],'sha256':None,
       'type':'MIXED_CANONICAL_SOURCE','projects':[],'project_coverage_status':'NOT_INSPECTED_T2_DENIED',
       'partition_provenance':'TRAIN_VALIDATION_T1_T2_MIXED','sufficiency':r['status'],'reason':r['reason'],
       'payload_structurally_inspected':False,'future_execution_authorized':False}
    s.save_lines('frozen_artifact_candidate_inventory.jsonl',[merged[k] for k in sorted(merged)])
    # Keep per-use logical mappings in the main physical inventory; count files only once.
    types={'FINAL_BASE_TRAIN_PROBABILITY_VECTOR','OOF_TRAIN_IDENTITIES_LABELS_MODALITY_PROBABILITIES','SMOKE_TRAIN_C_P_RAW_TEXT_ROWS','COMPLETE_ONE_PROJECT_TRAIN_IDENTITY_ORDER','LR_SMOKE_REFERENCE_PROBABILITIES_AND_MEANS','TFIDF_FITTED_REPRESENTATION','DEVELOPMENT_PROBABILITY_LEDGER'}
    train=[r for r in merged.values() if r['type'] in types]
    s.save_lines('train_evidence_inventory.jsonl',sorted(train,key=lambda r:r['path']))
    log['files'].update({k:v for k,v in s.INSPECTED.items() if not k.startswith(s.rel(s.OUT)+'/')})
    log['read_paths']=sorted(set(log['read_paths'])|s.READS)
    s.save('inspection_log.json',log)
    c=json.loads((s.OUT/'governance_counters.json').read_text())
    c['FROZEN_ARTIFACT_FILES_INSPECTED']=len(log['files'])
    c['FROZEN_TRAIN_ARTIFACTS_FOUND']=len(train); c['REUSABLE_TRAIN_ARTIFACTS']=len(train)
    c['definitions']+=' TRAIN artifact count includes unique fitted TFIDF representation and development probability files; logical uses are distinct from physical files.'
    s.save('governance_counters.json',c)
    s.save('object_project_reference_audit.json',{'objects':sum('/objects/' in key for key in links),'unmapped_inventory_objects':[r['path'] for r in merged.values() if '/objects/' in r['path'] and not r['projects']],
     'mapping_basis':'All repetition journals and OOF descriptors; exact logical IDs, no feature-value inference.'})
    s.enrich_provenance()
    s.finalize()

def enrich_provenance():
    candidates=[json.loads(x) for x in (OUT/'frozen_artifact_candidate_inventory.jsonl').read_text().splitlines()]
    records=[]
    for r in candidates:
        if not r.get('payload_structurally_inspected'):
            continue
        p=ROOT/r['path']
        if p.is_relative_to(STORE):
            parent_manifest=STORE/'MANIFEST.sha256'
            source=ROOT/'src/evaluation/q1_xai_train_source_reconstruction.py'
            identity='Exact journal check_row_identity_sha256 or OOF descriptor membership digest; actual row IDs in OOF payload when present.'
        elif p==T1:
            parent_manifest=T1.parent/'MANIFEST.sha256'
            source=ROOT/'src/evaluation/q1_t1_confirmatory_execution.py'
            identity='Direct row_identifier/model_identity fields; all389 eligible ordered identity/raw-probability digests validated against G4.'
        elif p.is_relative_to(SMOKE):
            parent_manifest=SMOKE/'MANIFEST.sha256'
            source=ROOT/'src/evaluation/q1_primary_xai_runtime_smoke.py'
            identity='Explicit smoke row IDs/reference population and complete activemq TRAIN membership digest; not primary population.'
        elif p.is_relative_to(DEV):
            parent_manifest=DEV/'MANIFEST.sha256'
            source=ROOT/'src/experimentation/q1_controlled_result_campaign.py'
            identity='Explicit project/fold/partition/row_identifier; development outputs, not final-base full-TRAIN reference.'
        else:
            continue  # Metadata-only findings are not promoted as reusable row/state components.
        records.append({'path':r['path'],'sha256':r['sha256'],'project_coverage':r['projects'],
          'chain':['FROZEN_APACHEJIT_SOURCE_NO_REOPEN','HISTORICAL_TRAIN_OR_T1_PARTITION','HISTORICAL_PROCESSING',
           'FROZEN_MANIFEST_AND_OBJECT_HASH',r['type'],'ROW_ID_OR_ORDER_DIGEST','EXACT_LOGICAL_STATE_LINKAGE','FUTURE_E1_OR_E2_COMPONENT'],
          'original_source_provenance_reference':'audits/q1-xai-reconstruction-execution/1.0.0/frozen_input_verification.json',
          'source_provenance_sha256':sha(STORE/'frozen_input_verification.json'),
          'artifact_manifest':rel(parent_manifest),'artifact_manifest_sha256':sha(parent_manifest),
          'historical_processing_source':rel(source),'historical_processing_source_sha256':sha(source),
          'logical_states':r.get('logical_state_references',[]),'identity_alignment':identity,
          'reconciliation_artifact':'row_identity_reconciliation.json',
          'component_provenance':'EXACT_HISTORICAL_COMPONENT',
          'primary_population_provenance':'INCOMPLETE_WHERE_STATED_IN_SCOPE_DISPOSITION','reuse_limit':r['reason']})
    save_lines('provenance_reuse_ledger.jsonl',records)

def manifest():
    (OUT/'MANIFEST.sha256').write_text(''.join(f'{sha(p)}  {p.name}\n' for p in sorted(OUT.iterdir()) if p.is_file() and p.name!='MANIFEST.sha256'))

def finalize():
    prepare(); sys.addaudithook(guard)
    before=json.loads((OUT/'parent_integrity_before.json').read_text()); after=snapshot()
    assert before==after
    save('parent_integrity_after.json',after)
    counters=json.loads((OUT/'governance_counters.json').read_text())
    validation=json.loads((OUT/'validation_results.json').read_text()) if (OUT/'validation_results.json').exists() else {'status':'PENDING'}
    texts=[('A. Branch',BRANCH),('B. HEAD',git('rev-parse','HEAD')),
      ('C. Sprint56.1','PRIMARY_XAI_ISOLATED_RUNTIME_SMOKE_TEST_PASS'),('D. Sprint56.2','PRIMARY_XAI_T1_SELECTION_CONTRACT_FAILURE'),
      ('E. Sprint56.2A','SAFE_TRAIN_T1_SOURCE_NOT_AVAILABLE_UNDER_CURRENT_T2_BOUNDARY'),
      ('F. Sprint56.2B','T2_SEMANTIC_BOUNDARY_EVIDENCE_INSUFFICIENT / T2_SEMANTIC_BOUNDARY_AMENDMENT_NOT_JUSTIFIED'),
      ('G. Universe','389 scopes and exactly zeppelin LR C+T, P+T, C+P+T exclusions preserved. Fresh before/after parent/artifact hashes agree;5,649objects intact.'),
      ('H. Inspection',f"{counters['FROZEN_ARTIFACT_FILES_INSPECTED']} distinct artifacts structurally inspected; all5,649objecthashes verified separately. Exact paths and coverage in inventories; all15requestedroots searched."),
      ('I. TRAIN','168 complete final-base TRAIN probability vectors,56representative OOF identity/label/probability matrices,80activemq C/P/rawTEXTrows, complete activemq TRAIN identity order and prior64-row LR smoke reference evidence. These are different scientific representations; probability vectors are not feature matrices.'),
      ('J. T1','Isolated Sprint54 ledger retains3787unique identities,labels and probabilities for every eligible model scope. Identity/order and raw-probability hashes reconcile against all389G4references. No CODE/PROCESS/TEXT input vectors in that ledger. Labels are available; they are not the global XAI blocker.'),
      ('K. G4','G4 used3787feature rows and389queries/105862comparisons, but persisted result digests and summaries, not input matrices. Project rows and base probability buffers were local in-memory values. No frozen batch cache or G4 input object located.'),
      ('L. Reconstruction','All representative final base/meta objects inspected structurally. Pipelines persist fitted state; check_output NPY objects contain predictions, not X. TFIDF vocabulary/IDF persists but transformed TRAIN/T1 matrices do not. No reconstruction, model query or transform executed.'),
      ('M. OOF','Exact source-only TRAIN rows excluding warmup, with targets and C/P/T probabilities, exist for56algorithm/projectpairs. Membership hashes and lineage reconcile with frozen campaign provenance. OOF probabilities use fold predictors, not final bases: no silent substitution into primary reference means.'),
      ('N. Logistic Regression','E1_REUSE_NOT_FEASIBLE for complete primary scopes: exact states available, T1 input vectors missing.80activemq TRAINrows provide partial representation evidence.'),
      ('O. Random Forest','E1_REUSE_NOT_FEASIBLE; states available, T1 feature rows and complete TRAIN feature reference absent.'),
      ('P. XGBoost','E1_REUSE_NOT_FEASIBLE; booster/order state survives, required feature row representations absent.'),
      ('Q. LightGBM','E1_REUSE_NOT_FEASIBLE; exact state is distinct from missing input rows.'),
      ('R. CODE','80activemq TRAINrows available; other13projects TRAINfeatures absent; T1feature rows absent for14projects.'),
      ('S. PROCESS','Same explicit coverage as CODE; not hidden by missing TEXT.'),
      ('T. TEXT','Raw smoke TRAINmessages plus exact frozen vectorizers are acceptable partial representation.56final TEXTstates survive; no frozen T1rawmessages or exact transformed matrix found.'),
      ('U. E2',f"{counters['PARTIALLY_REUSABLE_E2_SCOPES']} scopes have exact T1 unimodal probabilities,meta-state and modality order sufficient for future RAW uncentered local algebra. C+P=56; C+T=55; P+T=55; C+P+T=55. Centered primary reference remains unresolved; complete primary reusable scope counter=0. No means/contributions calculated."),
      ('V. Projects','All14projects retain T1probability evidence and TRAINfinal probability arrays. Full TRAINidentity list located for activemq only; all14have partial OOF identities/labels excludingwarmup. Coverage is explicit perproject; no extrapolation.'),
      ('W. Graphics','E1bars/beeswarm/TEXTplots NOT_READY. E2modality contributions,raw local waterfalls and crossproject/family input comparisons PARTIALLY_READY. No graphics or interpretations produced.'),
      ('X. Missing evidence','E1needs exact frozen T1features and complete TRAINfeature inputs. E2needs a defensible primary TRAINreference population linkage. OOF and smoke references are real evidence, but changing population/predictor semantics requires explicit prospective review. No final populations selected.'),
      ('Y. Disposition',PARTIAL+' — exact reusable E2 components across14projects/4families exist; this does not certify the full centered primary XAI protocol. '+json.dumps(validation,sort_keys=True)),
      ('Z. Next step','Human review should decide a separate E2 reference-evidence path using the persisted arrays/OOF identities, with exact selection and predictor semantics. Preserve E1missing-input finding. Do not reopen sources, query models, resume56.2 or start56.3 automatically.')]
    report='# Sprint56.2C — Frozen evidence reuse feasibility\n\n'+PARTIAL+'\n\n'
    report+='\n\n'.join('## '+a+'\n\n'+b for a,b in texts)
    report=report.replace('all5,649objecthashes','all 5,649 object hashes').replace('all15requestedroots','all 15 requested roots').replace('3787unique','3,787 unique').replace('all389G4references','all 389 G4 references').replace('80activemq','80 activemq ').replace('56algorithm/projectpairs','56 algorithm/project pairs').replace('all14','all 14 ').replace('14projects','14 projects').replace('other13projects','other 13 projects').replace('56final TEXTstates','56 final TEXT states').replace('64-row','64-row').replace('excludingwarmup','excluding warmup').replace('T1feature','T1 feature').replace('TRAINfeatures','TRAIN features').replace('T1rawmessages','T1 raw messages').replace('T1probability','T1 probability').replace('TRAINfinal','TRAIN final').replace('TRAINidentity','TRAIN identity').replace('source-only','source-only')
    report+='\n\nAll current prohibited access/inference/XAI/metric/refit/reconstruction/recalibration/figure/selection counters are0. Historical T1 artifact read count=1 distinct file, not new source access. Historical predictive accounting remains1/1. No commit/push.\n\n'+PARTIAL+'\n\nREADY FOR HUMAN REVIEW BEFORE NEXT XAI ACTION\n'
    (OUT/'SPRINT56_2C_FROZEN_EVIDENCE_REUSE_REPORT.md').write_text(report)
    save('implementation_provenance.json',{'source_sha256':sha(Path(__file__)),'tests_sha256':sha(ROOT/'tests/evaluation/test_q1_primary_xai_frozen_evidence_reuse.py') if (ROOT/'tests/evaluation/test_q1_primary_xai_frozen_evidence_reuse.py').exists() else None})
    manifest(); print(PARTIAL)

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('stage',choices=['audit','complete','finalize','manifest'])
    {'audit':audit,'complete':complete_forensics,'finalize':finalize,'manifest':manifest}[p.parse_args().stage]()
