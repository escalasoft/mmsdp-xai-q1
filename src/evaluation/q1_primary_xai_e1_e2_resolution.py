"""Sprint 56.2E: bounded frozen-evidence resolution, no model execution."""
from __future__ import annotations
import argparse, hashlib, json, math, os, struct, subprocess, sys
from pathlib import Path
from src.evaluation import q1_primary_xai_missing_evidence_remediation as parent
ROOT=parent.ROOT
OUT=ROOT/'audits/q1-primary-xai-e1-input-e2-reference-resolution/1.0.0'
BASE=parent.BASE; D=parent.OUT; STORE=parent.STORE
BRANCH=parent.BRANCH
NOT='Q1_NOT_READY'; LIMITED='Q1_READY_WITH_PREDECLARED_LIMITATION'
VERDICT='Q1_PRIMARY_XAI_EXECUTION_NOT_READY'
ALLOWED=set();READS=set()
ZERO=['REPRESENTATION_RECONSTRUCTION_COUNT','REPRESENTATION_EQUIVALENCE_CHECK_COUNT','HISTORICAL_T1_FROZEN_ARTIFACT_READ_COUNT','NEW_T1_SOURCE_ROW_READ_COUNT','T2_ACCESS_COUNT','T2_ROW_READ_COUNT','T2_IDENTITY_READ_COUNT','T2_LABEL_READ_COUNT','T2_FEATURE_READ_COUNT','T2_MODEL_QUERY_COUNT','T2_XAI_COUNT','MODEL_QUERY_COUNT','SHAP_EXECUTION_COUNT','ANALYTICAL_ATTRIBUTION_EXECUTION_COUNT','FIGURE_GENERATION_COUNT','PREDICTIVE_METRIC_COUNT','MODEL_RECONSTRUCTION_COUNT','RETRAIN_COUNT','REFIT_COUNT','RECALIBRATION_COUNT']
def enc(x):return (json.dumps(x,sort_keys=True,ensure_ascii=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(x):return hashlib.sha256(enc(x)).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def rows(p):return [json.loads(l) for l in Path(p).read_text().splitlines() if l.strip()]
def save(n,x):(OUT/n).write_bytes(enc(x))
def ledger(n,x):(OUT/n).write_bytes(b''.join(enc(r) for r in x))
def rel(p):return Path(p).relative_to(ROOT).as_posix()
def prepare():
 parent.prepare();ALLOWED.update(parent.ALLOWED)
 ALLOWED.update(p.resolve() for p in D.iterdir() if p.is_file())
 # No T1 scientific artifact is permitted, including the historically isolated gzip.
def guard(event,args):
 if event!='open' or not isinstance(args[0],(str,bytes,os.PathLike)):return
 p=Path(os.fsdecode(args[0])).resolve()
 if not p.is_relative_to(ROOT):return
 mode,flags=args[1] or '',args[2] or 0
 writing=any(c in mode for c in 'wax+') or bool(flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC))
 if writing and not p.is_relative_to(OUT):raise PermissionError('Protected evidence write')
 code=any(p.is_relative_to(ROOT/k) for k in ['src','tests']) and p.suffix in ['.py','.pyc']
 if not (p.is_relative_to(OUT) or p in ALLOWED or code or p.is_relative_to(ROOT/'.venv') or p.name in ['.gitignore','pyproject.toml'] and p.parent==ROOT):raise PermissionError('Unapproved scientific payload')
 if not writing:READS.add(rel(p))
def snapshot():
 x=parent.snapshot()
 x.update({rel(p):sha(p) for p in D.iterdir() if p.is_file()})
 return x

def primary_reference(meta_regime,exact_membership,forward):
 return 'PRIMARY_REFERENCE_OOF' if meta_regime=='TEMPORAL_OOF' and exact_membership and forward else 'REFERENCE_UNRESOLVED'
def mean(v):
 if not v or any(not math.isfinite(x) or x<0 or x>1 for x in v):raise ValueError('Invalid probability population')
 return math.fsum(v)/len(v)
def coverage(n,k):return {'total_rows':n,'recoverable_rows':k,'unrecoverable_rows':n-k,'coverage_fraction':k/n,'classification':'COMPLETE' if k==n else 'PARTIAL' if k else 'INSUFFICIENT'}

def build():
 assert subprocess.check_output(['git','symbolic-ref','--short','HEAD'],text=True).strip()==BRANCH
 OUT.mkdir(parents=True,exist_ok=False);prepare();sys.addaudithook(guard)
 save('parent_integrity_before.json',snapshot())
 scope=read(BASE/'scope_integrity.json');assert scope['count']==389
 allscopes=read(BASE/'row_identity_reconciliation.json')['T1']; e2=read(BASE/'e2_multimodal_feasibility.json')['scopes']
 old=read(BASE/'oof_evidence_reuse_audit.json')['candidates'];oldmap={(r['project'],r['algorithm']):r for r in old}
 journal={r['logical_id']:r for r in rows(STORE/'repetitions/rep_01/component_journal.jsonl')}
 descriptors=[read(p) for p in sorted((STORE/'repetitions/rep_01').glob('oof_*.json'))];assert len(descriptors)==56
 # Decision depends on historical regime, not probabilities, means, metrics or explanation output.
 policy={'primary':'PRIMARY_REFERENCE_OOF','population':'Full exact historical meta-training membership, temporal OOF blocks after initial warmup; no final row subset selected',
  'estimand':'Centered predictive modality contribution relative to historical source-side meta-training probability population',
  'pre_XAI_prospective_decision':True,'user_authority':'Sprint56.2E sections15-22 explicitly request scientifically aligned primary reference selection',
  'parent_contract_transition':'Child prospective E2 reference decision replaces the previously unresolved selected-final-TRAIN baseline for this estimand. Parent56.2D findings remain unchanged. E1 <=256 TRAIN background rule remains unchanged. No general claim that every valid explanation must use OOF.',
  'full_OOF_reference_not_E1_background':True,'final_TRAIN':'SECONDARY_REFERENCE_ONLY, deployed in-sample predictor background; different population and model regime',
  'missing_warmup':'Expected by forward meta-training design; no missing member of the actual meta-training population',
  'readiness_limitation':'OOF-centered explanations describe the historical meta-training reference; they are not centered on deployed-model full TRAIN probabilities. Final T1/local populations and execution still require later authorization.',
  'mean_recipe':'math.fsum(binary64 probabilities)/N; compute twice; exact binary64 equality; no tolerance relaxation',
  'digest_recipe':{'identity':'SHA256 UTF8 canonical JSON sorted identity list, sort_keys, ASCII, compact separators, final LF', 'probability':'SHA256 concatenated little-endian IEEE754 binary64 vector in frozen OOF row order','mean':'SHA256 one little-endian IEEE754 binary64 scalar'},
  'representation_equivalence':'Prefer byte equality, then exact arrays with equal shape/dtype/sparsity/order/missingness. No numerical tolerance fallback authorized here; failures block.'}
 save('prospective_resolution_policy.json',policy)
 evidence=[]
 for path,start,end,claim in [('src/evaluation/q1_xai_train_source_reconstruction.py',1244,1291,'OOF membership and forward lineage checked against frozen provenance'),('src/evaluation/q1_xai_train_source_reconstruction.py',1356,1455,'Persisted OOF matrix supplies meta.fit columns; no final-TRAIN vector used'),('src/experimentation/q1_controlled_train_validation_baselines.py',41,42,'Actual CODE and PROCESS schema'),('src/evaluation/q1_xai_g4_row_equivalence.py',545,629,'Inputs local to G4 execution; persisted output summaries do not retain X')]:
  p=ROOT/path;content=p.read_text().splitlines();evidence.append({'path':path,'sha256':sha(p),'start':start,'end':end,'claim':claim,'category':'DIRECT_CODE_EVIDENCE','excerpt':'\n'.join(content[start-1:end])})
 save('direct_code_evidence.json',evidence)
 recovered=[];eq=[]
 for r in allscopes:
  if '+' in r['configuration']:continue
  project,alg,mod=r['project'],r['algorithm'],r['configuration'];st=journal[f'{project}|{alg}|FINAL_BASE|{mod}'];train=st['check_row_count'];k=80 if project=='apache/activemq' else 0
  assert r['model_identity_sha256'] in st['canonical_state']['provenance']['consuming_model_identity_sha256']
  recovered.append({'project':project,'algorithm':alg,'modality':mod,'model_identity_sha256':r['model_identity_sha256'],
   'expected_train_rows':train,'recoverable_train_rows':k,'expected_t1_rows':r['rows'],'recoverable_t1_rows':0,
   'recovery_path':'F','path_evaluation':{'A':'No persisted G4 X','B':'No G4/G5 content-addressed X reference','C':'No frozen T1 raw or transformed X found','D':'Only80 activemq TRAIN source rows plus frozen preprocessing; no T1 source representation','E':'No proven independently authorized T1-only source; blocked before access','F':'Full E1 input chain unresolved'},
   'source_artifact':rel(BASE/'g4_t1_input_reuse_audit.json'),'source_hash':sha(BASE/'g4_t1_input_reuse_audit.json'),
   'partial_TRAIN_source':{'path':rel(parent.SMOKE/'selected_train_rows.json'),'sha256':sha(parent.SMOKE/'selected_train_rows.json'),'status':'Exact frozen raw rows, representation recoverable using frozen preprocessing; not transformed or selected here'} if k else None,
   'row_identity_method':'Exact historical identity/order digests; never infer identity from feature values',
   'preprocessing_state':st['canonical_state']['preprocessing'],'predictor_state':st['executable'],
   'feature_names': ['la','ld','nf','nd','ns','ent'] if mod=='C' else ['ndev','age','nuc','aexp','arexp','asexp'] if mod=='P' else st['text_representation'],
   'feature_order_status':'FROZEN_STATE_AVAILABLE_INPUT_ROWS_INCOMPLETE','model_state_status':'FROZEN_HASH_LINKED_PRIOR_G4_PASS',
   'text_alignment_status':'STATE_AVAILABLE_ROWS_INCOMPLETE' if mod=='T' else 'NOT_APPLICABLE',
   'equivalence_status':'NOT_EXECUTED_NO_RECONSTRUCTION','provenance_status':'MODEL_STATE_EXACT_FULL_INPUT_CHAIN_INCOMPLETE','q1_scientific_status':'Q1_NOT_READY'})
  eq.append({'project':project,'algorithm':alg,'modality':mod,'status':'NOT_APPLICABLE_NO_RECONSTRUCTION','passed':None,'reason':'No new matrix generated; partial raw rows remain prior evidence, not a new equivalent full matrix'})
 ledger('e1_input_recovery_ledger.jsonl',recovered);ledger('representation_equivalence_ledger.jsonl',eq)
 for partition in ['train','t1']:
  records=[{'project':r['project'],'algorithm':r['algorithm'],'modality':r['modality'],**coverage(r[f'expected_{partition}_rows'],r[f'recoverable_{partition}_rows'])} for r in recovered]
  save(f'e1_{partition}_coverage.json',{'records':records,'count_unit':'scope-row; repeated across models/modalities, not unique source rows','total_expected':sum(x['total_rows'] for x in records),'total_recoverable':sum(x['recoverable_rows'] for x in records),'unique_recoverable_source_rows':80 if partition=='train' else 0,'missingness':'Systematic absence of persisted inputs; activemq smoke selection is not representative of all projects. No global claim from convenience subset.'})
 for name,mod in [('code','C'),('process','P'),('text','T')]:
  save(f'e1_{name}_resolution.json',{'status':NOT,'scopes':56,'projects':14,'families':4,'ready_scopes':0,'partial_TRAIN_project':'apache/activemq','partial_TRAIN_rows':80,'T1_recoverable_rows':0,'scope_records':[r for r in recovered if r['modality']==mod],
  'semantic_policy':'Actual frozen schema only; PROCESS ancestor-only provenance must remain unchanged; no recomputation of history or features.',
  'TEXT_required':['vocabulary','idf','token_pattern','lowercase','ngram_range','min_df','max_features','norm','sublinear_tf','token-column mapping','feature order','sparse/dense layout','exact predictor alignment'] if mod=='T' else [],'no_fit_or_transform':True})
 save('g4_input_recovery_analysis.json',{'prior_analysis':read(BASE/'g4_t1_input_reuse_audit.json'),'paths_A_through_F_assessed':True,'no_new_source_discovery':'Targeted existing artifact lineage only','T1_payload_opened':False})
 computed=[];audits=[];hashes={}
 previous={(r['project'],r['algorithm']):r for r in read(D/'fusion_reference_mean_resolution.json')['means'] if r['reference_class']=='OOF_REFERENCE'}
 for d in descriptors:
  key=d['project'],d['algorithm'];pr=oldmap[key];p=STORE/d['object']['path'];ALLOWED.add(p.resolve());h=sha(p);assert h==d['object']['sha256'];hashes[rel(p)]=h
  x=read(p);ids=x['row_identifiers'];v=x['probabilities'];assert len(ids)==len(set(ids))==len(v)==pr['rows']
  assert digest(ids)==d['meta_training_membership_sha256']==pr['membership_digest']
  offset=0
  for f in d['lineage']:
   assert f['strict_forward_and_disjoint'] and all(k<f['prediction_block'] for k in f['fit_blocks'])
   assert digest(ids[offset:offset+f['prediction_count']])==f['prediction_membership_sha256'];offset+=f['prediction_count']
  assert offset==len(ids) and all(len(row)==3 for row in v)
  for i,m in enumerate(['C','P','T']):
   vector=[float(row[i]) for row in v];a=mean(vector);b=mean(vector)
   assert a.hex()==b.hex()==previous[key]['mu'][m].hex()
   computed.append({'project':key[0],'algorithm':key[1],'modality':m,'primary_reference':'PRIMARY_REFERENCE_OOF','rows':len(ids),'mu':a,'mu_hex':a.hex(),
    'ordered_identity_digest':digest(ids),'sorted_identity_digest':digest(sorted(ids)),'probability_vector_sha256':hashlib.sha256(b''.join(struct.pack('<d',q) for q in vector)).hexdigest(),'mean_sha256':hashlib.sha256(struct.pack('<d',a)).hexdigest(),
    'source_path':rel(p),'source_sha256':h,'source_partition':'TRAIN_META_OOF','probability_scale':'Positive-class probability [0,1]','repeat_exact':True,'parent56_2D_exact_match':True})
  audits.append({'project':key[0],'algorithm':key[1],'rows':len(ids),'warmup_rows':pr['warmup_rows_absent'],'warmup_classification':'EXPECTED_BY_DESIGN_NOT_META_TRAINING_MEMBER','membership_digest':digest(ids),'source_path':rel(p),'source_sha256':h,'fold_lineage':d['lineage'],'source_only_provenance':'Exact frozen prior meta-TRAIN membership and forward lineage; no T1/T2 identity list opened for set comparison','classification':primary_reference('TEMPORAL_OOF',True,True)})
 ledger('e2_reference_means.jsonl',computed)
 save('e2_oof_reference_audit.json',{'pairs':audits,'projects':14,'algorithms':4,'modalities':['C','P','T'],'primary_reference_population':'Full meta-training population; warmup exclusion expected, not convenience sampling'})
 candidates=[];decisions=[]
 for r in e2:
  key=(r['project'],r['algorithm']);a=next(x for x in audits if (x['project'],x['algorithm'])==key);st=journal[f'{key[0]}|{key[1]}|FUSION_META|{r["configuration"]}'];pr=st['canonical_state']['provenance']
  assert pr['meta_training_membership_sha256']==a['membership_digest'] and pr['modality_order']==r['exact_modality_order'] and pr['model_identity_sha256']==r['model_identity_sha256']
  assert st['canonical_state']['classes']==[0,1] and st['canonical_state']['n_features_in']==len(pr['modality_order'])
  assert r['T1_raw_modality_input_complete']
  base={k:r[k] for k in ['project','algorithm','configuration','model_identity_sha256']}
  for ref,status in [('OOF_REFERENCE','PRIMARY_REFERENCE_OOF'),('FINAL_TRAIN_REFERENCE','SECONDARY_REFERENCE_ONLY'),('SOURCE_ONLY_REFERENCE','NO_DISTINCT_BETTER_REFERENCE_ESTABLISHED')]:candidates.append({**base,'reference':ref,'classification':status,'evidence':'Exact temporal OOF meta-training lineage; final-TRAIN means retained from56.2D; source-only stacked matrix is the same OOF object, not independent third data'})
  decisions.append({**base,'primary_reference_status':'PRIMARY_REFERENCE_OOF','primary_mean_records':[x for x in computed if (x['project'],x['algorithm'])==key and x['modality'] in pr['modality_order']],
   'meta_state':st['executable'],'meta_canonical_state_sha256':st['canonical_state_sha256'],'alpha_available':st['canonical_state']['intercept'],'beta_available':st['canonical_state']['coef'],
   'modality_order':pr['modality_order'],'meta_training_membership_sha256':a['membership_digest'],
   'T1_probabilities':'Prior56.2C exact identity/order/probability reconciliation against G4; frozen raw base probabilities, not calibrated outputs','T1_evidence_sha256':sha(BASE/'row_identity_reconciliation.json'),
   'future_symbolic_decomposition_ready':True,'q1_status':LIMITED,'limitations':[policy['readiness_limitation'],'E2 is not E1; source-regime contrast must be labelled explicitly; fidelity/stability not executed']})
 ledger('e2_reference_candidate_ledger.jsonl',candidates)
 save('e2_primary_reference_decision.json',{'decision':policy,'scopes':decisions,'resolved':221,'unresolved':0})
 save('e2_final_train_reference_audit.json',{'status':'SECONDARY_REFERENCE_ONLY','pairs':56,'source':'Frozen56.2D final-TRAIN means and original check-output provenance','parent_sha256':sha(D/'fusion_reference_mean_resolution.json'),'in_sample':True,'used_as_meta_fit_input':False,'scientific_use':'Secondary deployed-model descriptive reference only; not erased or deemed mathematically invalid','recomputed':False})
 save('e2_source_only_reference_audit.json',{'classification':'NO_DISTINCT_BETTER_REFERENCE_ESTABLISHED','source_only_is_property_not_unique_regime':True,'stacked_meta_training_matrix':'Identical to persisted OOF columns by direct producer code','temporal_validation':'No independent provenance-complete alternative matching the actual meta-training membership established; no source exploration or values used to choose'})
 gates={c:{'eligible_scopes':sum(r['configuration']==c for r in decisions),'resolved_primary_references':sum(r['configuration']==c for r in decisions),'unresolved_references':0,'exact_mu_available':True,'modality_order_verified':True,'meta_state_verified':'Prior structural audit plus current canonical provenance/shape linkage','T1_probabilities_frozen':True,'future_decomposition_readiness':LIMITED} for c in ['C+P','C+T','P+T','C+P+T']}
 save('e2_fusion_decomposition_readiness.json',{'configurations':gates,'equations':['phi0=alpha+sum(beta_m*mu_m)','phi_m=beta_m*(p_m-mu_m)','eta=phi0+sum(phi_m)','sigmoid(eta) links to frozen RAW fusion probability'], 'no_attribution_executed':True,'stability_and_fidelity_contract':{'path':rel(D/'fidelity_execution_contract.json'),'sha256':sha(D/'fidelity_execution_contract.json')},'scopes':decisions})
 figures=[]
 for i,n in enumerate(['global mean absolute attribution','beeswarm','local waterfall','TEXT attribution','multimodal contribution','project heterogeneity','cross-model agreement','stability diagnostics'],1):
  figures.append({'figure':i,'name':n,'status':'INPUTS_READY_WITH_LIMITATION' if i in [3,5,6,7,8] else 'INPUTS_NOT_READY','scope':'E2 only; E1 inputs missing' if i in [3,5,6,7,8] else 'E1 input gap','population_not_selected':True,'publication_ready':False,'limitation':'OOF reference source resolved; future deterministic populations and fidelity/stability execution still pending. No full combined E1/E2 figure readiness.'})
 save('publication_graph_input_readiness.json',{'figures':figures,'parent_matrix_sha256':sha(D/'publication_figure_data_contract.json'),'parent_not_overwritten':True})
 counters={k:0 for k in ZERO};counters.update({'E1_SCOPES_AUDITED':168,'E1_SCOPES_Q1_READY':0,'E1_SCOPES_Q1_READY_WITH_LIMITATION':0,'E1_SCOPES_NOT_READY':168,'TRAIN_ROWS_EXPECTED':sum(r['expected_train_rows'] for r in recovered),'TRAIN_ROWS_RECOVERABLE':sum(r['recoverable_train_rows'] for r in recovered),'T1_ROWS_EXPECTED':sum(r['expected_t1_rows'] for r in recovered),'T1_ROWS_RECOVERABLE':0,'row_counter_unit':'scope-row, not unique source row','E2_REFERENCE_CANDIDATES_AUDITED':len(candidates),'E2_PRIMARY_REFERENCES_RESOLVED':221,'E2_REFERENCES_UNRESOLVED':0,'E2_REFERENCE_MEAN_COMPUTATION_COUNT':336,'E2_UNIQUE_MODALITY_MEANS':168,'mean_count_definition':'168 unique means, each computed twice; reused across221 scopes','FROZEN_TRAIN_OOF_FILES_READ':56,'T2_STATE':'DENY_SEALED_REVIEWER_RESERVE'})
 save('governance_counters.json',counters)
 save('q1_execution_readiness.json',{'branch':BRANCH,'HEAD':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'scope_count':389,'exclusions':scope['excluded'],'E1':{m:NOT for m in ['CODE','PROCESS','TEXT']},'E2':{c:LIMITED for c in gates},'overall':VERDICT,'reason':'Core E1 unresolved systematically, despite E2 reference resolution. Section38 fail-closed rule takes precedence over interpreting E2 progress as full-campaign readiness.','primary_execution_authorized':False,'Sprint56_3_authorized':False})
 save('exact_remaining_blockers.json',{'E1':'Exact full TRAIN and all T1 feature representations missing; no proven non-T2 T1 source. 80 frozen activemq TRAIN raw rows are partial only.','E2_remaining':'Reference regime and means resolved. Govern future foreground/local selection and explicit OOF baseline labelling; execute fidelity/stability only after separate authorization.','no_T2_rescue':True})
 save('recommended_next_action.json',{'action':'Human review of the OOF-centered E2 reference and its explicit limitations. E1 requires a provenance-complete segregated TRAIN/T1 representation source or a separately reviewed change of manuscript scope. No such source is asserted to exist.','do_not':'No primary XAI, no Sprint56.3, no mixed-source rematerialization, no T2 access.'})
 save('read_objects_integrity.json',{'before':hashes,'after':{p:sha(ROOT/p) for p in hashes}})
 finalize()

def manifest():
 (OUT/'MANIFEST.sha256').write_text(''.join(f'{sha(p)}  {p.name}\n' for p in sorted(OUT.iterdir()) if p.is_file() and p.name!='MANIFEST.sha256'))
def finalize():
 prepare();sys.addaudithook(guard);after=snapshot();assert after==read(OUT/'parent_integrity_before.json');save('parent_integrity_after.json',after)
 r=read(OUT/'q1_execution_readiness.json');c=read(OUT/'governance_counters.json')
 sections=[('A. Branch',BRANCH),('B. HEAD',r['HEAD']),('C. Parents','56.1 PASS;56.2 blocker;56.2A no safe source;56.2B unjustified;56.2C technical partial/Q1 insufficient;56.2D not ready. Byte hashes unchanged.'),('D. Universe','389 eligible scopes'),('E. Exclusions',json.dumps(r['exclusions'])),('F. CODE',NOT),('G. PROCESS',NOT),('H. TEXT',NOT),('I. TRAIN coverage',f"{c['TRAIN_ROWS_RECOVERABLE']}/{c['TRAIN_ROWS_EXPECTED']} scope-rows recoverable from prior raw evidence; 80 unique activemq rows, no transformation executed."),('J. T1 coverage',f"0/{c['T1_ROWS_EXPECTED']} E1 scope-rows; all14 projects affected."),('K. Representation reconstruction','None performed. A-D lack complete input chain; E lacks proven segregated authorized source; F unresolved.'),('L. Equivalence','No new representation; no comparison falsely marked PASS. Exact equivalence contract prospectively frozen.'),('M. LR',NOT),('N. RF',NOT),('O. XGBoost',NOT),('P. LightGBM',NOT),('Q. OOF','56 exact temporal OOF matrices; warmup exclusion matches actual meta-training by design. Row-order, fold membership and hashes verified.'),('R. Final TRAIN','SECONDARY_REFERENCE_ONLY. Final-model in-sample probabilities were not meta-training inputs. Preserved, not recomputed.'),('S. Source-only','The stacked meta-training matrix is the OOF artifact; no distinct better third regime established.'),('T. Selected regime','PRIMARY_REFERENCE_OOF for221 eligible scopes. Explicit child prospective E2 baseline decision; parent evidence unchanged. Full meta-training reference, not E1 selected background.'),('U. Means','168 unique modality means recomputed twice, exact binary64 agreement with each other and56.2D; membership/vector/mean digests persisted.'),('V. C+P',LIMITED+';56 scopes'),('W. C+T',LIMITED+';55 scopes'),('X. P+T',LIMITED+';55 scopes'),('Y. C+P+T',LIMITED+';55 scopes'),('Z. Overall',VERDICT)]
 text='# Sprint56.2E E1/E2 resolution\n\n'+'\n\n'.join('## '+a+'\n\n'+b for a,b in sections)
 text+='\n\n## Remaining limits and next action\n\nE1 input gaps are systematic. Review a provenance-complete segregated source or a separately governed narrowing of manuscript scope; this audit does not establish such a source. E2 has source inputs ready with explicit OOF-reference limitations for multimodal contributions and E2-only local/heterogeneity/agreement/stability figures. No figure is publication-ready: final foreground/local populations and fidelity/stability execution remain pending. E2 does not explain modality internals, imply causal importance, or replace E1. OOF baselines describe the historical meta-training regime, not deployed-model full TRAIN behavior.\n\nAll prohibited access/query/XAI/metric/model-mutation counters are zero. Only authorized frozen TRAIN reference statistics were computed. No T1 payload reread. Object hashes rechecked for56 OOF artifacts; other object-store integrity monitored by unchanged count/size/mtime, not claimed rehashed in full. No commit/push/stage.\n'
 v=read(OUT/'validation_results.json') if (OUT/'validation_results.json').exists() else {'status':'PENDING'}
 text+='\nValidation: '+json.dumps(v)+'\n'
 (OUT/'SPRINT56_2E_E1_E2_RESOLUTION_REPORT.md').write_text(text)
 save('implementation_provenance.json',{'source_sha256':sha(Path(__file__))})
 prior=read(OUT/'access_log.json')['paths'] if (OUT/'access_log.json').exists() else []
 save('access_log.json',{'paths':sorted(READS|set(prior)),'scope':'Python audit hook guarded build/finalization reads; initial code/metadata inspection separately identified in direct_code_evidence.json'})
 manifest();print(VERDICT)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('stage',choices=['build','finalize','manifest']);{'build':build,'finalize':finalize,'manifest':manifest}[p.parse_args().stage]()
