"""Sprint56.2F: partial frozen-input materialization, no model querying."""
from __future__ import annotations
import argparse,hashlib,json,os,subprocess,sys,warnings
from pathlib import Path
from src.evaluation import q1_primary_xai_e1_e2_resolution as previous
ROOT=previous.ROOT;E=previous.OUT;SMOKE=previous.parent.SMOKE;STORE=previous.STORE
OUT=ROOT/'audits/q1-primary-xai-e1-scientific-input-materialization/1.0.0'
BRANCH=previous.BRANCH;VERDICT=previous.VERDICT
ALLOWED=set();READS=set()
FEATURES={'C':['la','ld','nf','nd','ns','ent'],'P':['ndev','age','nuc','aexp','arexp','asexp']}
ZERO=['MODEL_QUERY_COUNT','PREDICT_PROBA_COUNT','DECISION_FUNCTION_COUNT','SHAP_EXECUTION_COUNT','ANALYTICAL_ATTRIBUTION_EXECUTION_COUNT','FIGURE_GENERATION_COUNT','PREDICTIVE_METRIC_COUNT','RETRAIN_COUNT','REFIT_COUNT','RECALIBRATION_COUNT','NEW_VECTORIZER_FIT_COUNT','NEW_SCALER_FIT_COUNT','FEATURE_SELECTION_COUNT','T2_ACCESS_COUNT','T2_ROW_READ_COUNT','T2_IDENTITY_READ_COUNT','T2_FEATURE_READ_COUNT','T2_LABEL_READ_COUNT','T2_MODEL_QUERY_COUNT','T2_XAI_COUNT','E2_REOPEN_COUNT','NEW_T1_SOURCE_ROW_READ_COUNT','HISTORICAL_T1_PAYLOAD_READ_COUNT','MODEL_RECONSTRUCTION_COUNT','EXPLANATION_SAMPLE_SELECTION_COUNT']
def enc(x):return previous.enc(x)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(x):return hashlib.sha256(enc(x)).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def rows(p):return [json.loads(l) for l in Path(p).read_text().splitlines() if l.strip()]
def rel(p):return Path(p).relative_to(ROOT).as_posix()
def save(n,x):(OUT/n).write_bytes(enc(x))
def ledger(n,x):(OUT/n).write_bytes(b''.join(enc(r) for r in x))
def prepare():
 previous.prepare();ALLOWED.update(previous.ALLOWED)
 ALLOWED.update(p.resolve() for p in E.iterdir() if p.is_file())
 # No mixed, T1 scientific, or OOF probability payload is admitted.
def guard(event,args):
 if event!='open' or not isinstance(args[0],(str,bytes,os.PathLike)):return
 p=Path(os.fsdecode(args[0])).resolve()
 if not p.is_relative_to(ROOT):return
 mode,flags=args[1] or '',args[2] or 0
 writing=any(c in mode for c in 'wax+') or bool(flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC))
 if writing and not p.is_relative_to(OUT):raise PermissionError('Protected write denied')
 code=any(p.is_relative_to(ROOT/k) for k in ['src','tests']) and p.suffix in ['.py','.pyc']
 runtime=any(p.is_relative_to(ROOT/k) for k in ['.venv','.venv-xai-s56'])
 if not (p.is_relative_to(OUT) or p in ALLOWED or code or runtime or p.name in ['pyproject.toml','.gitignore'] and p.parent==ROOT):raise PermissionError('Unapproved scientific payload denied')
 if not writing:READS.add(rel(p))
def snapshot():
 x=previous.snapshot();x.update({rel(p):sha(p) for p in E.iterdir() if p.is_file()});return x

def preflight():
 assert subprocess.check_output(['git','symbolic-ref','--short','HEAD'],text=True).strip()==BRANCH
 OUT.mkdir(parents=True,exist_ok=False);prepare();sys.addaudithook(guard)
 save('parent_integrity_before.json',snapshot())
 status=read(E/'q1_execution_readiness.json');assert status['overall']==VERDICT and status['scope_count']==389
 pop=read(SMOKE/'train_only_population_manifest.json')
 assert pop['project']=='apache/activemq' and pop['partition']=='TRAIN' and pop['unique_selected_rows']==80 and pop['non_TRAIN_rows_read']==0
 source=SMOKE/'selected_train_rows.json'
 # Source bytes are not opened until the admission proof has been persisted.
 proof={'source_identity':rel(source),'expected_sha256':pop['rows_sha256'],'source_partition_scope':'TRAIN_ONLY','project_scope':['apache/activemq'],'temporal_scope':'Subset of exact frozen chronological TRAIN registry (3675 rows)',
  'row_identity_semantics':'Exact frozen row_identifier, source commit linkage inherited from frozen membership; no fuzzy matching','modality_semantics':{'C':FEATURES['C'],'P':FEATURES['P'],'T':'raw_commit_message only'},
  'provenance_chain':['Frozen dataset row identities and feature schema','Sprint56.1 guarded TRAIN-only prefix extraction','80 row immutable selected_train_rows.json','56.2C exact membership audit','56.2E partial recoverable source'],
  'T2_exclusion_proof':{'manifest':rel(SMOKE/'train_only_population_manifest.json'),'manifest_sha256':sha(SMOKE/'train_only_population_manifest.json'),'producer':'src/evaluation/q1_primary_xai_runtime_smoke.py:225-267','independent_partition_check':'Prior manifest records TRAIN-only reads and exact identity sequence; current payload must hash-match that frozen record'},
  'admission':'ACCEPTED_PARTIAL_FROZEN_SOURCE_ONLY','full_universe':False,'scientific_limit':'Not a representative full TRAIN universe. PROCESS per-row event cutoffs and aggregation provenance are inherited rather than independently rederived; any insufficient historical detail blocks Q1 promotion.'}
 save('source_admission_before_payload.json',proof)
 journal={r['logical_id']:r for r in rows(STORE/'repetitions/rep_01/component_journal.jsonl')}
 components=[r for k,r in sorted(journal.items()) if k.startswith('apache/activemq|') and '|FINAL_BASE|' in k];assert len(components)==12
 save('approved_component_records.json',components)
 candidates=[{'path':rel(source),'status':'ACCEPTED_PARTIAL','reason':proof,'priority':'C then D'},
 {'path':rel(previous.BASE/'g4_t1_input_reuse_audit.json'),'status':'REJECTED_AS_INPUT_SOURCE','priority':'A','reason':'No persisted G4 X; identity/probability digests do not reconstruct feature values'},
 {'path':rel(previous.BASE/'reconstruction_train_input_reuse_audit.json'),'status':'REJECTED_AS_INPUT_SOURCE','priority':'B','reason':'States, vectorizers and check-output probabilities do not embed full input matrices'},
 {'path':rel(E/'e1_input_recovery_ledger.jsonl'),'status':'REJECTED_AS_FULL_SOURCE','priority':'C/D','reason':'Full TRAIN/raw T1 feature-generation inputs absent; only80 prior TRAIN rows'},
 {'path':None,'status':'REJECTED_BEFORE_PAYLOAD','priority':'E','reason':'No independently proven authorized T1-only source; mixed source blocked by unchanged56.2B boundary'}]
 ledger('e1_materialization_source_registry.jsonl',candidates)
 contract={'full_universe_intent':True,'no_new_sampling':True,'scope_selection':'All eligible scopes audited; only the one already proven source is materialized, no outcome-based fallback',
 'matrix_recipe':'Apply pipeline[:-1].transform to existing frozen raw rows twice. Do not call full pipeline.transform or any predictor. Preserve output dtype, CSR representation for sparse output, exact order and values.',
 'row_order':'Existing source row order, no reselection','numerical_equivalence':'Exact repeated array/CSR equality only, no tolerance fallback. No historical transformed-X reference exists; repeat equality is not historical equality.',
 'storage':'Content-addressed canonical JSON arrays, including CSR data/indices/indptr; shared only when full matrix identity agrees. No model bytes copied. 80*2557*8*4 upper-bound dense TEXT ~6.6MB binary; JSON estimate below25MB per matrix. Hard25MB per output guard.',
 'output_unit':'PARTIAL_MATERIALIZED_UNIVERSE, never FULL_MATERIALIZED_UNIVERSE or FUTURE_EXPLANATION_SAMPLE',
 'runtime':{'path':'.venv-xai-s56','frozen_lock_sha256':sha(SMOKE/'isolated_runtime_lock.json')},
 'PROCESS_semantics':{'event_cutoff':'Historical source commit event; no new cutoff computed','ancestor_scope':'Inherited frozen source history; not reconstructed','aggregation_semantics':'Inherited ApacheJIT numeric aggregates; no future/target data added','proof_limit':'Exact historical aggregation details not independently recreated in this stage; unresolved details remain Q1 limitations, not invented proof'},
 'CODE_semantics':'Exact frozen la,ld,nf,nd,ns,ent values; no labels/proxies injected; no new feature derivation',
 'TEXT_semantics':'Frozen raw message and exact fitted vectorizer; no issue metadata or target-based filtering; exact vocabulary/IDF/order/parameters required'}
 save('transformation_contract.json',contract)
 save('preflight_access_log.json',{'paths':sorted(READS)})
 print('PREFLIGHT_COMPLETE_PARTIAL_TRAIN_ONLY')

def materialize():
 prepare();sys.addaudithook(guard)
 assert snapshot()==read(OUT/'parent_integrity_before.json')
 proof=read(OUT/'source_admission_before_payload.json');source=ROOT/proof['source_identity'];assert sha(source)==proof['expected_sha256']
 data=read(source);pop=read(SMOKE/'train_only_population_manifest.json');ids=[r['row_identifier'] for r in data]
 assert len(ids)==len(set(ids))==80 and set(ids)<=set(pop['train_ids_chronological'])
 assert all(r['partition']=='TRAIN' and r['project']=='apache/activemq' and set(r)=={'row_identifier','partition','project','C','P','T'} for r in data)
 import numpy as np
 import scipy.sparse as sp
 import joblib
 import platform
 save('materialization_runtime.json',{'python':platform.python_version(),'numpy':np.__version__,'executable':sys.executable,'threads':{k:os.environ.get(k) for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','VECLIB_MAXIMUM_THREADS']}})
 def array(a):
  a=np.ascontiguousarray(np.asarray(a));return {'dtype':a.dtype.str,'shape':list(a.shape),'sha256':hashlib.sha256(a.tobytes()).hexdigest()}
 def payload(a,names):
  if sp.issparse(a):
   a=a.tocsr();matrix={'format':'CSR','shape':list(a.shape),'dtype':a.dtype.str,'data':a.data.tolist(),'indices':a.indices.tolist(),'indptr':a.indptr.tolist(),'index_dtype':a.indices.dtype.str,'indptr_dtype':a.indptr.dtype.str}
  else:matrix={'format':'DENSE','shape':list(a.shape),'dtype':a.dtype.str,'values':np.asarray(a).tolist()}
  return {'row_ids':ids,'partition':'TRAIN','project':'apache/activemq','feature_names':names,'feature_order':names,'X':matrix}
 records=[];hashes={};warnings_log=[]
 for st in read(OUT/'approved_component_records.json'):
  logical=st['logical_id'];project,alg,role,mod=logical.split('|');path=STORE/st['executable']['path'];ALLOWED.add(path.resolve());assert sha(path)==st['executable']['sha256'];hashes[rel(path)]=sha(path)
  try:
   with warnings.catch_warnings(record=True) as captured:
    warnings.simplefilter('always');pipeline=joblib.load(path)
    model=pipeline.named_steps['model'];pre=st['canonical_state']['preprocessing'];text_details=None
    if mod=='T':
     ref=STORE/st['text_representation']['path'];ALLOWED.add(ref.resolve());assert sha(ref)==st['text_representation']['sha256'];hashes[rel(ref)]=sha(ref);tr=read(ref)
     vec=pipeline.named_steps['tfidf'];names=vec.get_feature_names_out().tolist()
     assert vec.vocabulary_==tr['vocabulary'] and np.array_equal(vec.idf_,np.asarray(tr['idf'])) and names==tr['feature_order']
     assert all(vec.vocabulary_[name]==i for i,name in enumerate(names))
     for k,v in tr['parameters'].items():assert (list(getattr(vec,k)) if k=='ngram_range' else getattr(vec,k))==v
     assert array(vec.idf_)==pre['idf'] and digest(names)==pre['feature_order_sha256'] and digest(tr['vocabulary'])==pre['vocabulary_sha256']
     text_details={'vocabulary':tr['vocabulary'],'vocabulary_hash':digest(tr['vocabulary']),'idf':tr['idf'],'idf_hash':array(vec.idf_)['sha256'],**tr['parameters'],'token_column_mapping':tr['vocabulary'],'token_column_hash':digest(tr['vocabulary']),'representation_source':st['text_representation']}
    else:
     names=FEATURES[mod];assert array(pipeline.named_steps['imputer'].statistics_)==pre['imputer_statistics']
     if 'scaler' in pipeline.named_steps:
      scaler=pipeline.named_steps['scaler']
      for key,attr in [('mean','mean_'),('scale','scale_'),('var','var_'),('n_samples_seen','n_samples_seen_')]:assert array(getattr(scaler,attr))==pre['scaler'][key]
    raw=[r[mod] for r in data];a=pipeline[:-1].transform(raw);b=pipeline[:-1].transform(raw)
    pa=payload(a,names);pb=payload(b,names);assert enc(pa)==enc(pb),'REPRESENTATION_EQUIVALENCE_FAIL'
    assert a.shape==(80,len(names)) and model.n_features_in_==len(names) and np.asarray(model.classes_).tolist()==[0,1]
    details={'n_features_in':int(model.n_features_in_),'class_order':[0,1],'preprocessing_hash_verified':True,'model_query':False}
    if alg=='Logistic Regression':assert model.coef_.shape==(1,len(names));details['coefficient_shape']=list(model.coef_.shape)
    if alg=='XGBoost':
     booster=model.get_booster();assert booster.num_features()==len(names);details.update({'feature_names':booster.feature_names,'feature_types':booster.feature_types,'missing':str(model.missing),'objective':model.objective,'output_scale':'NATIVE_RAW_MARGIN'})
    if alg=='LightGBM':
     booster=model.booster_;assert booster.num_feature()==len(names);details.update({'feature_names':booster.feature_name(),'categorical_metadata':booster.pandas_categorical,'objective':str(model.objective),'output_scale':'NATIVE_RAW_MARGIN','missing_semantics':'Frozen booster defaults; no replacement of missing sentinels'})
    scientific_id=digest({'source_hash':proof['expected_sha256'],'modality':mod,'row_ids':ids,'raw':raw})
    matrix_bytes=enc(pa);assert len(matrix_bytes)<25_000_000;h=hashlib.sha256(matrix_bytes).hexdigest();outpath=OUT/f'{h}.matrix.json'
    if not outpath.exists():outpath.write_bytes(matrix_bytes)
    record={'logical_id':logical,'project':project,'algorithm':alg,'modality':mod,'partition':'TRAIN','row_ids':ids,'row_identity_sha256':digest(ids),'rows':80,'feature_names':names,'feature_order':names,'column_identity_sha256':digest(names),'dtype':pa['X']['dtype'],'format':pa['X']['format'],'shape':pa['X']['shape'],'nnz':int(a.nnz) if sp.issparse(a) else int(np.count_nonzero(a)),
     'missing_value_semantics':'Exact frozen preprocessing output; stored imputer statistics or TFIDF normalization, no refit','preprocessing_identity':pre,'preprocessing_hash':digest(pre),'predictor_identity':st['canonical_state']['provenance']['consuming_model_identity_sha256'],'predictor_hash':st['executable']['sha256'],'predictor_artifact':st['executable'],
     'source_artifact':rel(source),'source_hash':proof['expected_sha256'],'materialization_method':'Frozen preprocessing transform of all80 previously persisted raw rows','scientific_input_identity':scientific_id,'model_input_representation_identity':h,'output_artifact':rel(outpath),'output_hash':h,'values_hash':digest(pa['X']),'transformation_contract_hash':sha(OUT/'transformation_contract.json'),
     'equivalence_status':'EXACT_REPEAT_PASS_HISTORICAL_X_REFERENCE_UNAVAILABLE','historical_equivalence_claim':False,'provenance_status':'EXACT_PARTIAL_SOURCE_STATE_CHAIN','model_alignment':details,'text':text_details,'full_universe':False,'q1_ready':False,'status':'PARTIAL_TRAIN_MATERIALIZED'}
    records.append(record)
   warnings_log.extend({'logical_id':logical,'category':type(w.message).__name__,'message':str(w.message)} for w in captured)
  except Exception as error:
   records.append({'logical_id':logical,'project':project,'algorithm':alg,'modality':mod,'rows':0,'status':'MATERIALIZATION_FAILED','error':f'{type(error).__name__}: {error}','q1_ready':False})
   warnings_log.extend({'logical_id':logical,'category':type(w.message).__name__,'message':str(w.message)} for w in captured)
 ledger('partial_matrix_records.jsonl',records);save('exact_load_warnings.json',warnings_log)
 save('read_object_integrity.json',{'before':hashes,'after':{p:sha(ROOT/p) for p in hashes}})
 save('materialization_access_log.json',{'paths':sorted(READS)})
 print('PARTIAL_MATRICES',sum(r['status']=='PARTIAL_TRAIN_MATERIALIZED' for r in records),'FAILURES',sum(r['status']=='MATERIALIZATION_FAILED' for r in records))

def report():
 prepare();sys.addaudithook(guard);assert snapshot()==read(OUT/'parent_integrity_before.json')
 prior=rows(E/'e1_input_recovery_ledger.jsonl');partial=rows(OUT/'partial_matrix_records.jsonl');lookup={(r['project'],r['algorithm'],r['modality']):r for r in partial if r['status']=='PARTIAL_TRAIN_MATERIALIZED'}
 full=[];identity=[];schema=[];alignment=[];equivalence=[];chain=[]
 for r in prior:
  key=(r['project'],r['algorithm'],r['modality']);m=lookup.get(key)
  full.append({**{k:r[k] for k in ['project','algorithm','modality','model_identity_sha256','expected_train_rows','expected_t1_rows']},'materialized_train_rows':m['rows'] if m else 0,'materialized_t1_rows':0,'full_scope_materialized':False,'status':'PARTIAL_TRAIN_ONLY' if m else 'UNRESOLVED','path':'C/D' if m else 'F','matrix':{'path':m['output_artifact'],'hash':m['output_hash']} if m else None,'exact_blocker':'No authorized T1 input source; full TRAIN rows absent','q1_status':'E1_'+{'C':'CODE','P':'PROCESS','T':'TEXT'}[r['modality']]+'_Q1_NOT_READY'})
  identity.append({'project':key[0],'algorithm':key[1],'modality':key[2],'partition':'TRAIN','row_ids':m['row_ids'] if m else [],'row_identity_hash':m['row_identity_sha256'] if m else None,'no_T1_rows':True,'identity_method':'Exact prior TRAIN membership, frozen row identifiers'})
  schema.append({'project':key[0],'algorithm':key[1],'modality':key[2],'feature_names':m['feature_names'] if m else r['feature_names'],'order_status':'EXACT_FOR_PARTIAL_MATRIX' if m else 'FROZEN_STATE_ONLY_NO_MATRIX','columns_hash':m['column_identity_sha256'] if m else None,'text':m['text'] if m else None})
  alignment.append({'project':key[0],'algorithm':key[1],'modality':key[2],'status':'STRUCTURAL_PASS_PARTIAL' if m else 'NOT_EXECUTED_NO_MATRIX','details':m['model_alignment'] if m else None,'preprocessing':m['preprocessing_identity'] if m else r['preprocessing_state'],'predictor':r['predictor_state']})
  equivalence.append({'project':key[0],'algorithm':key[1],'modality':key[2],'status':m['equivalence_status'] if m else 'NOT_EXECUTED_NO_MATRIX','exact_repeat':bool(m),'historical_X_equality':None,'historical_reference':'No persisted transformed matrix available; repeatability is not independent historical equivalence'})
  chain.append({'project':key[0],'algorithm':key[1],'modality':key[2],'source_hash':m['source_hash'] if m else None,'transformation_contract_hash':sha(OUT/'transformation_contract.json'),'preprocessing_hash':m['preprocessing_hash'] if m else digest(r['preprocessing_state']),'matrix_hash':m['output_hash'] if m else None,'predictor_identity_hash':r['model_identity_sha256'],'predictor_object_hash':r['predictor_state']['sha256'],'chain_complete_for_full_universe':False,'chain_complete_for_partial_matrix':bool(m)})
 for n,x in [('e1_materialization_ledger.jsonl',full),('e1_row_identity_registry.jsonl',identity),('e1_feature_schema_registry.jsonl',schema),('e1_model_alignment_registry.jsonl',alignment),('e1_representation_equivalence.jsonl',equivalence),('e1_chain_of_custody.jsonl',chain)]:ledger(n,x)
 for part in ['train','t1']:
  rec=[]
  for r in full:
   n,k=r[f'expected_{part}_rows'],r[f'materialized_{part}_rows'];rec.append({'project':r['project'],'algorithm':r['algorithm'],'modality':r['modality'],'expected_rows':n,'materialized_rows':k,'missing_rows':n-k,'coverage_fraction':k/n})
  save(f'e1_{part}_materialization_coverage.json',{'scope_records':rec,'row_count_unit':'scope-row; repeated across families/modalities','expected_rows':sum(r['expected_rows'] for r in rec),'materialized_rows':sum(r['materialized_rows'] for r in rec),'unique_materialized_rows':80 if part=='train' and lookup else 0})
 for name,mod in [('CODE','C'),('PROCESS','P'),('TEXT','T')]:
  rs=[r for r in full if r['modality']==mod];pr=[r for r in partial if r['modality']==mod]
  save(f'e1_{name.lower()}_materialization.json',{'status':f'E1_{name}_Q1_NOT_READY','expected_projects':14,'recovered_projects_partial':len({r['project'] for r in pr if r['status']=='PARTIAL_TRAIN_MATERIALIZED'}),'expected_algorithms':4,'recovered_algorithms_partial':len({r['algorithm'] for r in pr if r['status']=='PARTIAL_TRAIN_MATERIALIZED'}),'expected_project_algorithm_scopes':56,'fully_recovered_scopes':0,'partially_materialized_scopes':sum(r['status']=='PARTIAL_TRAIN_MATERIALIZED' for r in pr),'expected_train_rows':sum(r['expected_train_rows'] for r in rs),'recovered_train_rows':sum(r['materialized_train_rows'] for r in rs),'expected_t1_rows':sum(r['expected_t1_rows'] for r in rs),'recovered_t1_rows':0,'full_coverage_fraction':0,'partial_matrices':pr})
 save('e1_missingness_analysis.json',{'pattern':'SYSTEMATIC_MISSINGNESS','affected_projects':14,'missing_T1_all':True,'TRAIN_partial_only':'80 activemq source rows, historical smoke selection;13 projects have no input rows','bias':'Project and historical smoke-subset selection cannot represent full TRAIN or T1 population. No performance/attribution filtering performed; bias-free campaign claim unsupported.','additional_PROCESS_limit':read(OUT/'transformation_contract.json')['PROCESS_semantics'],'no_convenience_subset_promotion':True})
 save('e1_q1_scientific_sufficiency.json',{'CODE':'E1_CODE_Q1_NOT_READY','PROCESS':'E1_PROCESS_Q1_NOT_READY','TEXT':'E1_TEXT_Q1_NOT_READY','systematic_missingness_blocks':True,'runability_does_not_imply_readiness':True})
 for name,limit in [('shap_background',256),('t1_foreground',256),('local_case',8)]:save(f'future_{name}_readiness.json',{'status':'NOT_READY','max_rows':limit,'seed':20260901,'project_specific':True,'source':'Full eligible materialized universe required; partial historical80 rows not approved replacement','selection_performed':False,'correlation_threshold_abs_Spearman':0.70 if name=='shap_background' else None})
 e2files={p.name:sha(p) for p in E.iterdir() if p.is_file() and p.name.startswith('e2_')}
 save('e2_integrity_preservation.json',{'status':'PASS_PRESERVED','files_sha256':e2files,'parent_snapshot_verifies_each':True,'E2_REOPEN_COUNT':0,'reference_regime':'56.2E PRIMARY_REFERENCE_OOF, FINAL_TRAIN secondary only','outcomes':{c:'Q1_READY_WITH_PREDECLARED_LIMITATION' for c in ['C+P','C+T','P+T','C+P+T']}})
 figs=read(E/'publication_graph_input_readiness.json')['figures']
 for f in figs:f['status']='INPUT_READY_WITH_PREDECLARED_LIMITATION' if f['status']=='INPUTS_READY_WITH_LIMITATION' else 'INPUT_NOT_READY'
 save('publication_graph_input_readiness.json',{'figures':figs,'E1_global_local_ready':False,'E2_only_prior_limitations_preserved':True,'no_figures_generated':True})
 save('q1_primary_xai_execution_readiness.json',{'branch':BRANCH,'HEAD':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'eligible_scopes':389,'exclusions':read(E/'q1_execution_readiness.json')['exclusions'],'E1':read(OUT/'e1_q1_scientific_sufficiency.json'),'E2_INTEGRITY':'PASS_PRESERVED','overall':VERDICT,'Sprint56_3_authorized':False})
 counters={k:0 for k in ZERO};counters.update({'E1_SOURCE_CANDIDATES_AUDITED':5,'E1_SOURCES_ACCEPTED':1,'E1_SOURCES_REJECTED':4,'REPRESENTATION_MATERIALIZATION_COUNT':len(lookup),'REPRESENTATION_EQUIVALENCE_CHECK_COUNT':len(lookup),'TEXT_FROZEN_VECTORIZER_APPLICATION_COUNT':2*sum(k[2]=='T' for k in lookup),'NUMERIC_FROZEN_PREPROCESSOR_APPLICATION_COUNT':2*sum(k[2]!='T' for k in lookup),'TRAIN_ROWS_EXPECTED':sum(r['expected_train_rows'] for r in full),'TRAIN_ROWS_MATERIALIZED':sum(r['materialized_train_rows'] for r in full),'T1_ROWS_EXPECTED':sum(r['expected_t1_rows'] for r in full),'T1_ROWS_MATERIALIZED':0,'UNIQUE_TRAIN_ROWS_MATERIALIZED':80 if lookup else 0,'row_count_unit':'scope-row; not unique source rows','T2_STATE':'DENY_SEALED_REVIEWER_RESERVE'})
 for n,m in [('CODE','C'),('PROCESS','P'),('TEXT','T')]:counters.update({f'E1_{n}_SCOPES_EXPECTED':56,f'E1_{n}_SCOPES_MATERIALIZED':0,f'E1_{n}_SCOPES_PARTIALLY_MATERIALIZED':sum(k[2]==m for k in lookup)})
 save('governance_counters.json',counters)
 save('exact_remaining_blockers.json',{'unresolved_scopes':[{'project':r['project'],'algorithm':r['algorithm'],'modality':r['modality'],'TRAIN_missing':r['expected_train_rows']-r['materialized_train_rows'],'T1_missing':r['expected_t1_rows']} for r in full],'blockers':['No proven segregated exact T1 source for any scope','Full TRAIN representation absent','Independent historical transformed-X comparison unavailable','PROCESS detailed historical event/aggregation evidence not independently rederived; do not invent it'],'materialization_failures':[r for r in partial if r['status']=='MATERIALIZATION_FAILED']})
 save('recommended_next_action.json',{'action':'Human review must identify and independently establish a provenance-complete segregated TRAIN/T1 input source before any further payload access, or separately reconsider manuscript scope. Repeating authorization without new admissible evidence cannot recover absent rows. Preserve E2 and T2 boundary.','primary_XAI_authorized':False})
 finalize()

def manifest():
 (OUT/'MANIFEST.sha256').write_text(''.join(f'{sha(p)}  {p.name}\n' for p in sorted(OUT.iterdir()) if p.is_file() and p.name!='MANIFEST.sha256'))
def finalize():
 prepare();sys.addaudithook(guard);after=snapshot();assert after==read(OUT/'parent_integrity_before.json');save('parent_integrity_after.json',after)
 files=[p for p in OUT.iterdir() if p.is_file()];save('output_size_audit.json',{'per_file_bytes':{p.name:p.stat().st_size for p in files if p.name not in ['MANIFEST.sha256','output_size_audit.json']},'greater_than_25MB':[p.name for p in files if p.stat().st_size>25_000_000],'greater_than_50MB':[p.name for p in files if p.stat().st_size>50_000_000],'no_models_copied':True,'storage_policy':'Canonical content-addressed JSON; identical model inputs deduplicated, shared source identity separate from model-specific representation'})
 c=read(OUT/'governance_counters.json');r=read(OUT/'q1_primary_xai_execution_readiness.json')
 sections=[('A. Branch',BRANCH),('B. HEAD',r['HEAD']),('C. Parents','All56.1–56.2E evidence unchanged by hash snapshots. Historical Sprint54 predictive payload not opened.'),('D. E2','PASS_PRESERVED; no reference reselection, mean recomputation or reopening.'),('E. Universe','389 scopes and three frozen zeppelin LR fusion exclusions preserved.'),('F. T2','DENY_SEALED_REVIEWER_RESERVE; all access counters zero.'),('G. Sources','Five targeted source-path candidates audited.'),('H. Admission','Only the immutable80-row activemq TRAIN source accepted, partial only. Other paths lack matrices or independently proven T1 isolation; no mixed source opened.'),('I. CODE','Partial frozen-preprocessor matrices only; E1_CODE_Q1_NOT_READY.'),('J. PROCESS','Partial frozen-preprocessor matrices only; E1_PROCESS_Q1_NOT_READY. Historical semantics inherited, not independently reconstructed or claimed proven beyond prior evidence.'),('K. TEXT','Frozen vectorizer applied, exact vocabulary/IDF/parameters/order checked; E1_TEXT_Q1_NOT_READY.'),('L. TRAIN',f"{c['TRAIN_ROWS_MATERIALIZED']}/{c['TRAIN_ROWS_EXPECTED']} scope-rows materialized;80 unique source rows. No new selection."),('M. T1',f"0/{c['T1_ROWS_EXPECTED']} scope-rows. All expected T1 inputs missing."),('N. Identity','Exact source SHA256 and membership subset checks; original row order retained.'),('O. Schema','Frozen C/P names retained; TEXT token-column map explicit; no anonymous scientific columns.'),('P. Preprocessing','Frozen imputer/scaler or vectorizer descriptors verified; no fit or normalization change.'),('Q. Alignment','Feature dimension/classes and family-specific structure checked without prediction.'),('R. Vectorizer','Exact frozen vocabulary, IDF, token parameters and order retained.'),('S. Equivalence','Two identical transforms checked exactly. Historical transformed-X reference unavailable: repeatability is not independent historical equivalence.'),('T. Missingness','Systematic across14 projects; partial activemq TRAIN subset cannot support general feature-level conclusions.'),('U. Background','Not ready; full TRAIN universe required before <=256 sampling, seed20260901.'),('V. Foreground','Not ready; T1 universe absent, <=256/project future limit unchanged.'),('W. Local cases','Not ready for E1; no cases selected; future8/scope limit preserved.'),('X. Figures','E1 inputs not ready. Prior E2-only limited input readiness retained; none publication-ready, none generated.'),('Y. Verdict',VERDICT),('Z. Next action',read(OUT/'recommended_next_action.json')['action'])]
 text='# Sprint56.2F E1 scientific input materialization\n\n'+'\n\n'.join('## '+a+'\n\n'+b for a,b in sections)
 v=read(OUT/'validation_results.json') if (OUT/'validation_results.json').exists() else {'status':'PENDING'}
 text+='\n\nValidation: '+json.dumps(v)+'\n\nModel queries, XAI, metrics, refits, T2 access and E2 reopening remain zero. No commit, push or staging. Partial materialization is not full-universe or Q1 acceptance. All unresolved scopes are enumerated in exact_remaining_blockers.json.\n'
 (OUT/'SPRINT56_2F_E1_SCIENTIFIC_INPUT_MATERIALIZATION_REPORT.md').write_text(text)
 save('implementation_provenance.json',{'source_sha256':sha(Path(__file__)),'test_sha256':sha(ROOT/'tests/evaluation/test_q1_primary_xai_e1_scientific_input_materialization.py')});manifest();print(VERDICT)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('stage',choices=['preflight','materialize','report','finalize','manifest']);{'preflight':preflight,'materialize':materialize,'report':report,'finalize':finalize,'manifest':manifest}[p.parse_args().stage]()
