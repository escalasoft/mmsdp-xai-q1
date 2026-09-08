"""56.2D: prospective remediation and authorized frozen-TRAIN mean feasibility."""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib,json,math,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'audits/q1-primary-xai-missing-evidence-remediation/1.0.0'
BASE=ROOT/'audits/q1-primary-xai-frozen-evidence-reuse/1.0.0'
Q1=BASE/'amendments/q1_scientific_sufficiency/1.0.0'
STORE=ROOT/'audits/q1-xai-reconstruction-execution/1.0.0'
POLICY=ROOT/'audits/q1-xai-runtime-freeze/1.0.0'
POP=ROOT/'audits/q1-primary-xai-population-freeze/1.0.0'
SMOKE=ROOT/'audits/q1-primary-xai-runtime-smoke/1.0.0'
G5=ROOT/'audits/q1-xai-final-output-equivalence-g5/1.0.0'
BRANCH='sprint-10/q1-primary-xai-execution'; VERDICT='Q1_PRIMARY_XAI_EXECUTION_NOT_READY'
STATUSES=['RESOLVABLE_FROM_FROZEN_EVIDENCE','RESOLVABLE_WITH_SAFE_NON_T2_MATERIALIZATION','BLOCKED_BY_MISSING_PROVENANCE','BLOCKED_BY_T2_BOUNDARY','SCIENTIFICALLY_INSUFFICIENT']
ALLOWED=set(); READS=set()
ZERO=['NEW_T1_SOURCE_ROW_READ_COUNT','HISTORICAL_T1_FROZEN_ARTIFACT_READ_COUNT','T2_ACCESS_COUNT','T2_IDENTITY_READ_COUNT',
 'T2_LABEL_READ_COUNT','T2_FEATURE_READ_COUNT','T2_MODEL_QUERY_COUNT','T2_XAI_EXECUTION_COUNT','MODEL_QUERY_COUNT',
 'SHAP_EXECUTION_COUNT','ANALYTICAL_ATTRIBUTION_EXECUTION_COUNT','FIGURE_GENERATION_COUNT','PREDICTIVE_METRIC_COUNT',
 'RETRAIN_COUNT','REFIT_COUNT','RECONSTRUCTION_COUNT','RECALIBRATION_COUNT','POPULATION_SELECTION_COUNT','COMMIT_COUNT','PUSH_COUNT']
def canonical(x):return (json.dumps(x,sort_keys=True,ensure_ascii=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(x):return hashlib.sha256(canonical(x)).hexdigest()
def rel(p):return Path(p).relative_to(ROOT).as_posix()
def read(p):return json.loads(Path(p).read_text())
def rows(p):return [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()]
def save(n,x):(OUT/n).write_bytes(canonical(x))
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()
def prepare():
 for folder in [BASE,Q1,POLICY,POP,SMOKE,G5]:
  ALLOWED.update(p.resolve() for p in folder.iterdir() if p.is_file())
 for name in ['q1-primary-xai-safe-population-source','q1-primary-xai-t2-semantic-boundary-amendment']:
  ALLOWED.update(p.resolve() for p in (ROOT/'audits'/name/'1.0.0').iterdir() if p.is_file())
 ALLOWED.add((STORE/'repetitions/rep_01/component_journal.jsonl').resolve())
 ALLOWED.update(p.resolve() for p in (STORE/'repetitions/rep_01').glob('oof_*.json'))
 ALLOWED.add((STORE/'external_artifact_registry/external_artifact_inventory.jsonl').resolve())
def guard(event,args):
 if event!='open' or not isinstance(args[0],(str,bytes,os.PathLike)):return
 p=Path(os.fsdecode(args[0])).resolve()
 if not p.is_relative_to(ROOT):return
 mode,flags=args[1] or '',args[2] or 0;writing=any(c in mode for c in 'wax+') or bool(flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC))
 if writing and not p.is_relative_to(OUT):raise PermissionError('56.2D protected write denied')
 allowed=p.is_relative_to(OUT) or p in ALLOWED or p.is_relative_to(ROOT/'.venv') or p.is_relative_to(ROOT/'src') and p.suffix in ['.py','.pyc'] or p.is_relative_to(ROOT/'tests') and p.suffix in ['.py','.pyc'] or p.name in ['pyproject.toml','.gitignore'] and p.parent==ROOT
 if not allowed:raise PermissionError('56.2D unapproved source/T1/T2/model payload denied')
 if not writing and not p.is_relative_to(OUT):READS.add(rel(p))
def snapshot():
 result={}
 for folder in [BASE,Q1,POP,SMOKE,ROOT/'audits/q1-primary-xai-safe-population-source/1.0.0',ROOT/'audits/q1-primary-xai-t2-semantic-boundary-amendment/1.0.0']:
  for p in folder.iterdir():
   if p.is_file():result[rel(p)]=sha(p)
 result['.gitignore']=sha(ROOT/'.gitignore')
 result['store_stat_only']={p.name:[p.stat().st_size,p.stat().st_mtime_ns] for p in (STORE/'objects').iterdir() if p.is_file()}
 return result

def mean(values):
 if not values or any(not math.isfinite(float(v)) or not 0<=float(v)<=1 for v in values):raise ValueError('Invalid frozen probabilities')
 return math.fsum(float(v) for v in values)/len(values)
def reference_accepted(kind,membership,primary_population):
 return kind=='FINAL_TRAIN_REFERENCE' and membership and primary_population

def build():
 assert git('symbolic-ref','--short','HEAD')==BRANCH
 OUT.mkdir(parents=True,exist_ok=False);prepare();sys.addaudithook(guard)
 save('parent_integrity_before.json',snapshot())
 scope=read(BASE/'scope_integrity.json');assert scope['count']==389
 assert read(BASE/'recommended_next_action.json')['outcome']=='PARTIAL_FROZEN_EVIDENCE_REUSE_FEASIBLE'
 assert read(Q1/'q1_manuscript_xai_readiness.json')['Q1_XAI_MANUSCRIPT_READINESS']=='Q1_XAI_INSUFFICIENT_FOR_PRIMARY_MANUSCRIPT_CLAIMS'
 all_scopes=read(BASE/'row_identity_reconciliation.json')['T1']
 e2=read(BASE/'e2_multimodal_feasibility.json')['scopes']
 journal={r['logical_id']:r for r in rows(STORE/'repetitions/rep_01/component_journal.jsonl')}
 inv={r['relative_path']:r for r in rows(STORE/'external_artifact_registry/external_artifact_inventory.jsonl')}
 # This contract is persisted BEFORE any probability object is opened.
 save('reference_feasibility_calculation_protocol.json',{'frozen_before_probability_reads':True,
  'selection':'All56 project/algorithm pairs, deterministic lexical order; both reference regimes examined; no value-based choice',
  'allowed_statistics':'Only per-modality full-population probability means; no contributions, phi0, correlations, metrics or predictions',
  'recipe':'CPython3.11.14 math.fsum(binary64 stored probabilities)/N; retain float.hex; deterministic binary64 aggregate, not rational arithmetic claim',
  'primary_population_selected':False,'OOF_reference':'Full historical source-only meta-training population, excludes warmup; fold predictors',
  'final_reference':'All historical final-base TRAIN check outputs, final predictors; not selected<=256 background',
  'primary_reference_status':'Neither full-population diagnostic automatically replaces frozen selected primary reference',
  'prospective_preference':'OOF_REFERENCE for describing meta-training information regime; FINAL_TRAIN_REFERENCE for frozen deployed-model TRAIN-background estimand. They answer different questions.',
  'no_favorable_reference_selection':True})
 import numpy as np
 means=[]; hashes={}
 old={ (r['project'],r['algorithm']):r for r in read(BASE/'oof_evidence_reuse_audit.json')['candidates']}
 for dp in sorted((STORE/'repetitions/rep_01').glob('oof_*.json')):
  d=read(dp);p=STORE/d['object']['path'];ALLOWED.add(p.resolve())
  assert sha(p)==d['object']['sha256']==inv[d['object']['path']]['sha256'];hashes[rel(p)]=sha(p)
  payload=read(p);ids=payload['row_identifiers'];values=payload['probabilities']
  assert len(ids)==len(set(ids))==len(values)==old[d['project'],d['algorithm']]['rows']
  assert digest(ids)==d['meta_training_membership_sha256']==old[d['project'],d['algorithm']]['membership_digest']
  assert all(len(x)==3 for x in values)
  mu=[mean([x[i] for x in values]) for i in range(3)]
  final_mu=[];final_sources=[];final_count=None;final_identity=None
  for modality in ['C','P','T']:
   r=journal[f'{d["project"]}|{d["algorithm"]}|FINAL_BASE|{modality}'];ref=r['check_output'];ap=STORE/ref['path'];ALLOWED.add(ap.resolve())
   assert sha(ap)==ref['sha256']==inv[ref['path']]['sha256'];hashes[rel(ap)]=sha(ap)
   a=np.load(ap,allow_pickle=False)
   assert a.shape==(r['check_row_count'],) and a.dtype==np.dtype('<f8')
   assert hashlib.sha256(a.tobytes()).hexdigest()==r['train_source_check_output_sha256']
   assert r['check_row_identity_sha256']==r['canonical_state']['provenance']['train_membership_sha256']
   if final_count is not None:assert final_count==len(a) and final_identity==r['check_row_identity_sha256']
   final_count=len(a);final_identity=r['check_row_identity_sha256'];final_mu.append(mean(a.tolist()))
   final_sources.append({'modality':modality,'path':rel(ap),'sha256':ref['sha256'],'logical_id':r['logical_id']})
  assert final_count==len(ids)+old[d['project'],d['algorithm']]['warmup_rows_absent']
  for kind,vector,n,identity,sources in [('OOF_REFERENCE',mu,len(ids),digest(ids),[{'path':rel(p),'sha256':d['object']['sha256']}]),('FINAL_TRAIN_REFERENCE',final_mu,final_count,final_identity,final_sources)]:
   means.append({'project':d['project'],'algorithm':d['algorithm'],'reference_class':kind,'source_only':True,'rows':n,
    'modality_order':['C','P','T'],'mu':dict(zip(['C','P','T'],vector)),'mu_binary64_hex':[x.hex() for x in vector],
    'membership_digest':identity,'sources':sources,'calculation_status':'DETERMINISTIC_MEAN_RESOLVED_FOR_THIS_FULL_HISTORICAL_POPULATION',
    'primary_selected_reference_accepted':False,'scope':'TRAIN_REFERENCE_FEASIBILITY_ONLY_NOT_XAI_RESULT',
    'identity_limit':'Explicit ordered IDs in OOF object' if kind=='OOF_REFERENCE' else 'Ordered output digest certified by journal; complete explicit TRAIN identity list located only for activemq'})
 save('fusion_reference_mean_resolution.json',{'means':means,'reference_classes':['OOF_REFERENCE','FINAL_TRAIN_REFERENCE','SOURCE_ONLY_REFERENCE','INVALID_REFERENCE'],
  'SOURCE_ONLY_REFERENCE':'Umbrella property, not a replacement for predictor-regime labeling',
  'INVALID_REFERENCE':['T1/T2/validation as background','OOF relabelled as final-model probability','unmapped rows','favorable-output reference choice'],
  'primary_means_resolved':False,'scientific_resolution':'Full OOF means match meta-training information regime; full final-TRAIN means describe deployed base-model TRAIN behavior. Both are reproducible candidates. Neither is the existing selected<=256 primary baseline.',
  'preserve_existing_primary_contract':True,'no_automatic_OOF_substitution':True})
 save('TRAIN_object_integrity.json',{'before_sha256':hashes,'after_sha256':{p:sha(ROOT/p) for p in hashes},'distinct_probability_artifacts':len(hashes)})
 resolution=[]
 for r in e2:
  key=f'{r["project"]}|{r["algorithm"]}|FUSION_META|{r["configuration"]}';state=journal[key]['canonical_state'];pr=state['provenance']
  assert pr['modality_order']==r['configuration'].split('+') and pr['model_identity_sha256']==r['model_identity_sha256']
  assert state['n_features_in']==len(pr['modality_order'])
  resolution.append({'project':r['project'],'algorithm':r['algorithm'],'configuration':r['configuration'],'model_identity_sha256':r['model_identity_sha256'],
   'alpha_beta_evidence':{'journal':rel(STORE/'repetitions/rep_01/component_journal.jsonl'),'logical_id':key,'canonical_state_sha256':journal[key]['canonical_state_sha256']},
   'modality_order':pr['modality_order'],'T1_p_source':'Frozen56.2C exact G4/Sprint54 probability reconciliation; no T1 payload reread',
   'OOF_mean_population_digest':pr['meta_training_membership_sha256'],'candidate_mean_evidence':'fusion_reference_mean_resolution.json',
   'primary_selected_mu_status':'BLOCKED_BY_MISSING_PROVENANCE','readiness':'NOT_READY',
   'why':'Numerical full-population means resolved, but selecting/validating an exact primary population and estimand is unresolved; no replacement of frozen contract.'})
 save('e2_reference_resolution.json',{'scopes':resolution,'overall':'NOT_READY','configurations':{c:{'eligible':sum(r['configuration']==c for r in resolution),'ready':0,'status':'NOT_READY'} for c in ['C+P','C+T','P+T','C+P+T']},
  'equations':{'eta':'alpha + sum(beta_m*p_m)','phi_m':'beta_m*(p_m-mu_m)','phi0':'alpha+sum(beta_m*mu_m)','p_fusion':'sigmoid(eta)'},
  'OOF_required_for':'Meta-training features must remain out-of-fold; never refit the meta learner on in-sample probabilities.',
  'final_TRAIN_allowed_for':'Explanatory background of the fixed deployed predictor is not meta-training; it does not refit or estimate predictive performance.',
  'no_inference_or_contributions':True})
 matrix=[];e1ledger=[]
 def item(r,missing,status,source,resolution_text,layer):
  matrix.append({'evidence_id':digest([r['model_identity_sha256'],missing]),'E1_or_E2':layer,'project':r['project'],'algorithm':r['algorithm'],
   'modality/configuration':r['configuration'],'missing_item':missing,'candidate_frozen_source':source,
   'source_provenance':{'base_manifest_sha256':sha(BASE/'MANIFEST.sha256'),'scope_model_identity_sha256':r['model_identity_sha256'],'prior_q1_manifest_sha256':sha(Q1/'MANIFEST.sha256')},
   'proposed_resolution':resolution_text,'requires_new_data_access':False,'requires_T1_source_access':False,'requires_T2_access':False,
   'requires_model_query':False,'requires_retraining':False,'validation_method':'Exact identity/order/membership, representation and state hash reconciliation; no fuzzy mapping',
   'equivalence_test':'Exact feature/input bytes or stored probability/identity digests; future explanation fidelity is separate',
   'Q1_acceptance_criterion':'Complete specified primary population, exact model/preprocessing alignment, fidelity/stability and adequate coverage',
   'status':status,'access_flag_scope':'Proposed permitted action only; blocked alternatives are not authorized by these false flags.'})
 for r in all_scopes:
  if '+' not in r['configuration']:
   item(r,'T1 exact model input representation','BLOCKED_BY_MISSING_PROVENANCE','g4_t1_input_reuse_audit.json in frozen56.2C',
    'A persisted inputs absent; B content-addressed store has states/outputs, not X; C G4 has digests, not X; D no proven complete non-T2 representation; E unresolved. No canonical source read.','E1')
   item(r,'TRAIN reference input and deterministic population chain','SCIENTIFICALLY_INSUFFICIENT','56.2C TRAIN evidence inventory',
    'A complete X absent; B complete fold feature matrices absent; C OOF probability matrices do not replace E1 features; D only80activemq smoke rows; E unresolved.','E1')
   item(r,'TRAIN correlated-feature grouping evidence','SCIENTIFICALLY_INSUFFICIENT','56.2C e1_modality_feasibility.json',
    'Recover complete legitimate TRAIN feature representation before Spearman grouping; no correlation computed here.','E1')
   if r['configuration']=='T':item(r,'TEXT raw/transformed row mapping','BLOCKED_BY_MISSING_PROVENANCE','56.2C reconstruction_train_input_reuse_audit.json',
    'Preserve exact vocabulary/IDF/token-column/feature order; raw frozen text OR exact TFIDF rows accepted; vectorizer alone is insufficient.','E1')
   e1ledger.append({**{k:r[k] for k in ['project','algorithm','configuration','model_identity_sha256','rows']},'readiness':'NOT_READY','T1_feature_rows':0,
    'model_state':'FROZEN_AVAILABLE','TRAIN_feature_rows_available':80 if r['project']=='apache/activemq' else 0})
  else:
   item(r,'Full source-only reference mean feasibility','RESOLVABLE_FROM_FROZEN_EVIDENCE','fusion_reference_mean_resolution.json',
    'OOF and final-TRAIN complete-population means resolved independently; retain both regimes and hashes. No primary baseline adoption.','E2')
   item(r,'Selected primary TRAIN-centered reference population','BLOCKED_BY_MISSING_PROVENANCE','fusion_reference_mean_resolution.json;56.2C OOF and identity inventories',
    'Explicitly resolve final-model reference identity/class linkage or prospectively review a different OOF population/estimand; do not substitute automatically.','E2')
   item(r,'Primary centered fidelity/stability/publication evidence','SCIENTIFICALLY_INSUFFICIENT','56.2C Q1 amendment',
    'Prepare contracts now; execute only after inputs/populations are complete and separate primary authorization.','E2')
 (OUT/'missing_evidence_remediation_matrix.jsonl').write_bytes(b''.join(canonical(x) for x in matrix))
 (OUT/'e1_resolution_ledger.jsonl').write_bytes(b''.join(canonical(x) for x in e1ledger))
 save('train_background_resolution.json',{'status':'NOT_READY','options':['A frozen full X absent','B complete fold X absent','C OOF probabilities useful only for E2','D reconstructed state not training X;80activemq TRAIN rows partial','E unresolved'],
  'future_policy':{'partition':'TRAIN_ONLY','max_rows_per_scope':256,'seed':20260901,'project_specific':True,'stratification':'Only frozen legitimate class labels; no silent change of prior primary stratification rule',
  'ordering':'SHA256 deterministic predeclared identity ordering; full eligible candidate membership required','no_T1_outcome_selection':True},
  'population_selected':False,'forbidden_fallbacks':['VALIDATION','T1','T2','fabricated/imputed population from model statistics']})
 save('t1_foreground_resolution.json',{'status':'NOT_READY_FOR_E1','identity_probability_coverage':{'projects':14,'rows':3787,'scopes':389},
  'frozen_feature_rows_available':0,'options':'A/B/C/D unavailable under existing provenance, E unresolved; mixed upstream is not an option',
  'future_global':{'max_rows_per_project':256,'project_shared_across_families':True,'seed':20260901,
  'proposed_order':'SHA256 canonical JSON(seed,purpose=T1_GLOBAL,project,row_identifier), tie row_identifier; choose prefix up to256',
  'prior_scope_specific_selection_reconciliation':'Prospective project-shared contract only; confirm compatibility with56.2 scope-specific identity-key rule before execution; do not overwrite parent rule',
  'excluded_selection_inputs':['probability','label','correctness','attribution','visual quality']},
  'future_local':{'max_cases_per_scope':8,'subset_of_global':True,'default':'Predeclared SHA256 order over global IDs and scope identity; no post-attribution changes',
   'optional_strata':['prediction-only risk strata','TP/FP/FN/TN only with legitimate frozen labels and separate predeclaration'],
   'strata_selected_here':False},'no_new_T1_reads':True})
 save('text_representation_resolution.json',{'status':'NOT_READY','frozen_final_TEXT_states':56,'state_mapping_verified_by':'56.2C reconstruction_train_input_reuse_audit.json and exact state objects',
  'required':['vocabulary','IDF','tokenizer/lowercase policy','n-gram policy','token-column order','feature order','predictor alignment','exact row representation'],
  'state_evidence_is_not_row_evidence':True,'accepted_rows':['raw frozen text+exact frozen vectorizer','exact frozen TFIDF matrix+token-column mapping'],
  'current_rows':{'TRAIN':80,'TRAIN_project':'apache/activemq','T1':0},
  'cross_project':'No literal token-rank averaging without demonstrated comparability; project-specific features or predeclared reproducible categories only.',
  'semantic_intent_or_causality':'FORBIDDEN','transform_or_fit_executed':False})
 save('family_input_contract.json',{'Logistic Regression':['coef_','intercept_','classes_ order','exact x','baseline/reference','feature order','LOGIT'],
  'Random Forest':['exact forest','class order','exact matrix','TRAIN background','positive-class output','exact TreeSHAP'],
  'XGBoost':['exact booster','objective','feature order/types','missing semantics','NATIVE_RAW_MARGIN','exact TreeSHAP'],
  'LightGBM':['exact booster','objective','feature order','missing semantics','NATIVE_RAW_MARGIN','exact TreeSHAP'],
  'families_readiness':{a:'NOT_READY' for a in ['Logistic Regression','Random Forest','XGBoost','LightGBM']}})
 save('fidelity_execution_contract.json',{'status':'FROZEN_FUTURE_TEST_CONTRACT_NOT_EXECUTED','LR_fusion':{'identity':'eta=intercept+sum(contributions)','absolute_residual_bound':'1e-10*(1+abs(eta))','sigmoid_absolute_bound':1e-10},
  'TreeSHAP':{'identity':'base+sum(phi)=f(x) on frozen scale','absolute_residual_bound':'1e-6*(1+abs(f(x)))','approximate':False},
  'global_reconstruction_tolerance':1e-12,'global_definition':'Mean absolute/signed attribution and aggregate reconstruction over frozen foreground, store support and rank',
  'fused_probability_reference':'Frozen RAW fused probability; any calibration transformation separate, never compare native logit to calibrated probability',
  'on_failure':'Block manuscript admission; preserve failure; no tolerance changes, model changes or scope cherry-picking',
  'runtime_lock':{'path':rel(SMOKE/'isolated_runtime_lock.json'),'sha256':sha(SMOKE/'isolated_runtime_lock.json')},
  'thread_controls':{k:'1' for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','VECLIB_MAXIMUM_THREADS']}})
 save('stability_execution_contract.json',{'status':'PREPARED_NOT_EXECUTED','seeds':list(range(20260901,20260921)),
  'deterministic_max_absolute_difference':1e-12,'metrics':['top-3 Jaccard','top-10 Jaccard','Spearman rank correlation','sign agreement','total variation distance'],
  'population_reselection_by_seed':False,'rank_policy':'Fixed feature identity alignment, deterministic lexical tie-breaking; k=min(k,feature_count)',
  'TV_policy':'Only comparable normalized nonnegative attribution magnitude distributions over identical feature support; all-zero distribution reported degenerate, not silently passing',
  'stochasticity':'Only documented governed sources; deterministic methods repeated, do not invent random perturbations',
  'report_failures_and_instability':True})
 hetero=read(POLICY/'heterogeneity_interpretation_policy.json')
 save('heterogeneity_execution_contract.json',{'status':'PREPARED_NOT_EXECUTED','cross_family_minimum':3,
  'cross_family_diagnostics':{'top_k_Jaccard_min':0.60,'Spearman_min':0.70,'sign_agreement_min':0.80,'TV_max':0.25},
  'categories':['STABLE_CROSS_PROJECT_PATTERN','PROJECT_SPECIFIC_PATTERN','MODEL_DEPENDENT_PATTERN','HETEROGENEOUS_PATTERN','INSUFFICIENT_EVIDENCE'],
  'frozen_parent_policy':hetero,'universal':'All eligible projects and relevant families, no material reversal; otherwise narrow claim',
  'no_family_or_scope_discard_from_diagnostics':True,'scale_policy':'Ranks/normalized distributions only when comparable; do not average raw logit and probability attribution magnitudes across families',
  'correlation':{'source':'TRAIN only','method':'Spearman','absolute_threshold':0.70,'reports':['individual attribution','group sensitivity'],
   'grouping':'Predeclare exact group construction and hash membership before attribution; do not infer unique causality from redistribution'},
  'complementarity':'Descriptive non-zero heterogeneous predictive contributions only after validation; magnitude alone proves neither superiority nor causal complementarity.'})
 finish_contracts()

def finish_contracts():
 prepare();sys.addaudithook(guard)
 scope=read(BASE/'scope_integrity.json');e2=read(BASE/'e2_multimodal_feasibility.json')['scopes']
 hashes=read(OUT/'TRAIN_object_integrity.json')['before_sha256']
 states=rows(G5/'xai_readiness_ledger.jsonl')
 iso=[r for r in states if r['calibration_explanation_readiness']=='E3_FROZEN_MAPPING_INSPECTION_READY'];assert len(iso)==14
 assert all(r['algorithm']=='LightGBM' and r['configuration']=='P' for r in iso)
 save('calibration_xai_separation_contract.json',{'RAW':375,'ISOTONIC':14,'isotonic_scopes':[{k:r[k] for k in ['project','algorithm','configuration','model_identity_sha256']} for r in iso],
  'E1':'Frozen predictor quantity only','E3':'Frozen isotonic mapping separately; no feature allocation through calibration; no refit',
  'LIME_PRIMARY_STATUS':'EXCLUDED_FROM_PRIMARY_XAI','LIME_future':'EXPLORATORY_NON_CONFIRMATORY only after separate authorization',
  'counterfactuals':'EXCLUDED; nonactionable history, invalid correlated/text combinations, modality dependencies, noninvertible calibration and new query requirements'})
 claim_names=['CODE feature patterns','PROCESS feature patterns','TEXT attribution patterns','family explanatory differences','cross-project stability','local examples','pairwise modality contributions','full C+P+T contributions','project heterogeneity','explanation reliability','calibration/XAI separation']
 claims=[]
 for i,title in enumerate(claim_names,1):
  claims.append({'claim_id':f'C{i}','claim':title,'required_evidence':['exact governed populations/state/representation','fidelity','stability','explicit coverage and heterogeneity'],
   'minimum_project_coverage':'All eligible projects for general/universal claims; narrower substantial coverage must be explicitly reviewed, not inferred from one project',
   'minimum_family_coverage':'All four where applicable; at least3 for comparable cross-family agreement diagnostics',
   'modality_coverage':'C/P/T and relevant pairwise/full fusion; C+P+T required endpoint','permitted_wording':'Descriptive frozen-model predictive contributions only if validated; presently input/protocol limitations only',
   'prohibited_wording':['causal mechanisms','semantic intent','attribution magnitude proves superiority','one project/family represents campaign'],
   'required_figure_table':f'FIG-XAI-{min(i,8)} plus exact coverage/fidelity table','readiness':'NOT_READY'})
 claim_figures={1:[1,2],2:[1,2],3:[4],4:[7],5:[6,8],6:[3],7:[5],8:[5],9:[6],10:[8],11:[9]}
 for i,c in enumerate(claims,1):
  c['required_figure_table']=[f'FIG-XAI-{v}' for v in claim_figures[i]]+['Exact population/coverage/fidelity/stability table']
  c['modality_coverage']=({1:'C',2:'P',3:'T',7:'C+P/C+T/P+T',8:'C+P+T',11:'LightGBM P isotonic E3 and RAW identity mappings'}.get(i,'All relevant E1 modalities and E2 configurations'))
 save('claim_to_evidence_contract.json',{'claims':claims,'E1_and_E2_complementary_not_substitutes':True})
 fig_names=['Global mean absolute feature attribution','Beeswarm','Local waterfall','TEXT attribution','Multimodal decomposition','Project heterogeneity','Cross-model agreement','Stability diagnostics','E3 calibration transformation']
 figures=[]
 for i,title in enumerate(fig_names,1):
  figures.append({'figure_id':f'FIG-XAI-{i}','title':title,'optional':i==9,
   'source_artifact_path':f'FUTURE_AUTHORIZED_RESULT_NAMESPACE/FIG-XAI-{i}_input.jsonl','source_exists':False,
   'source_record_schema':['scope_id','project','algorithm','configuration','population_manifest_sha256','model_sha256','runtime_lock_sha256','scale','fidelity_status','stability_status','values','support_count','provenance'],
   'population_definition':'Frozen TRAIN reference and T1 global/local subset; E3 frozen mapping only',
   'sample_size':{'actual':None,'TRAIN_max_per_scope':256,'T1_max_per_project':256,'local_max_per_scope':8},
   'algorithm_scope':'All eligible families; E3 LightGBM P only','modality_scope':'Relevant C/P/T and pairwise/full fusion; exact identity alignment',
   'project_coverage':'All14 eligible for campaign claims; explicit exclusions','output_scale':'Family-specific predictor scale; E2 meta-logit; E3 mapping axes explicitly labelled',
   'fidelity_status':'NOT_EXECUTED','stability_status':'NOT_EXECUTED','limitations':['Input gaps unresolved','No primary figure admission before valid provenance/fidelity','No causal or literal cross-project token interpretation'],
   'publication_ready':False,'placeholder_not_existing_artifact':True})
 figure_columns={
  1:['feature_id','mean_absolute_attribution','signed_mean_attribution','rank','n_foreground'],
  2:['row_identifier','feature_id','model_input_value','attribution','baseline','model_output'],
  3:['row_identifier','local_case_policy_digest','feature_or_modality_id','contribution','baseline','reconstructed_quantity','frozen_model_quantity','residual'],
  4:['row_identifier','token_column','token','TFIDF_value','attribution','vocabulary_sha256','IDF_sha256'],
  5:['row_identifier','modality','p_m','beta_m','mu_m','raw_contribution','centered_contribution','phi0','eta_fusion','sigmoid_probability','frozen_raw_fusion_probability','residual'],
  6:['project','algorithm','feature_or_modality_id','comparable_aggregate','support_count','pattern_category','material_reversal_flag'],
  7:['project','modality','family_a','family_b','feature_alignment_digest','top3_Jaccard','top10_Jaccard','Spearman','sign_agreement','TV','diagnostic_status'],
  8:['scope_id','seed','repeat_id','population_digest','maximum_repeat_difference','top3_Jaccard','top10_Jaccard','Spearman','sign_agreement','TV','fidelity_status','stability_status'],
  9:['scope_id','isotonic_mapping_digest','raw_probability_axis','calibrated_probability_axis','frozen_mapping_knots']}
 for i,f in enumerate(figures,1):f['required_figure_specific_columns']=figure_columns[i]
 save('publication_figure_data_contract.json',{'figures':figures,'figures_generated':0,
  'schema_policy':'Additional fields require provenance and review; every row must satisfy shared linkage fields and its figure-specific schema. Raw magnitude scales cannot be pooled across incompatible families.'})
 save('q1_completeness_gate.json',{'mandatory_E1':['CODE','PROCESS','TEXT'],'mandatory_E2':['C+P','C+T','P+T','C+P+T'],
  'quality':['complete population/provenance','adequate project/family coverage','global and local','fidelity pass','stability assessed','heterogeneity reported','no T2 or cherry-picking'],
  'systematic_gaps_not_isolated_exclusions':True,'current_gate_pass':False})
 save('final_xai_execution_readiness.json',{'verdict':VERDICT,'branch':BRANCH,'HEAD':git('rev-parse','HEAD'),'eligible_scopes':389,'excluded':scope['excluded'],
  'E1':{m:{'status':'NOT_READY','eligible_projects':14,'eligible_families':4,'eligible_scopes':56,'ready_scopes':0,'T1_feature_rows':0,'TRAIN_feature_rows':80,'TRAIN_feature_projects':1} for m in ['CODE','PROCESS','TEXT']},
  'E2':{c:{'status':'NOT_READY','eligible_scopes':sum(r['configuration']==c for r in e2),'ready_scopes':0} for c in ['C+P','C+T','P+T','C+P+T']},
  'resolved_this_stage':'112 full-source reference mean triplets (56 OOF +56 final TRAIN), identity/hash linked; not adopted primary reference',
  'remaining_blockers':['E1 input representations','primary<=256 TRAIN reference population provenance/estimand','foreground population-rule reconciliation','future fidelity/stability results'],
  'next_action':'Human review must resolve a provenance-complete non-T2 E1 input path and explicitly decide the E2 primary reference population/estimand. No source route is proved by a protocol alone.',
  'Sprint56_3_authorized':False,'resume56_2_authorized':False})
 save('governance_counters.json',{**{k:0 for k in ZERO},'T2_STATE':'DENY_SEALED_REVIEWER_RESERVE',
  'TRAIN_REFERENCE_MEAN_TRIPLETS_COMPUTED':112,'TRAIN_REFERENCE_MODALITY_MEANS_COMPUTED':336,
  'FROZEN_TRAIN_PROBABILITY_ARTIFACTS_READ':len(hashes),'counter_scope':'56.2D only; prior counters unchanged',
  'scientific_access_note':'Only explicitly authorized frozen TRAIN/source-only mean feasibility; no coefficients multiplied by inputs, no phi0 or attribution computed.'})
 finalize()

def manifest():
 (OUT/'MANIFEST.sha256').write_text(''.join(f'{sha(p)}  {p.name}\n' for p in sorted(OUT.iterdir()) if p.is_file() and p.name!='MANIFEST.sha256'))
def finalize():
 prepare();sys.addaudithook(guard)
 before=read(OUT/'parent_integrity_before.json');after=snapshot();assert before==after
 save('parent_integrity_after.json',after)
 r=read(OUT/'final_xai_execution_readiness.json');v=read(OUT/'validation_results.json') if (OUT/'validation_results.json').exists() else {'status':'PENDING'}
 sections=[('A. Branch',BRANCH),('B. HEAD',r['HEAD']),('C. Parent state','56.1 PASS;56.2 selection failure;56.2A no safe source;56.2B amendment unjustified;56.2C technical partial and Q1 insufficient. All unchanged.'),
 ('D. Scope integrity','389 eligible scopes preserved.'),('E. Exclusions','zeppelin LR C+T, P+T, C+P+T unchanged.'),
 *[(f'{letter}. E1 {modality}', 'NOT_READY. No exact T1 feature rows located; complete TRAIN input chain missing. No model/source recovery executed.') for letter,modality in [('F','CODE'),('G','PROCESS'),('H','TEXT')]],
 *[(f'{letter}. {family}', 'Frozen state preserved; E1 NOT_READY due to input evidence, not method replacement.') for letter,family in [('I','LR'),('J','RF'),('K','XGBoost'),('L','LightGBM')]],
 ('M. TRAIN background','Full source-only probability means now resolved for112 population/regime pairs. No selected<=256 background frozen; E1 X cannot be replaced by probabilities.'),
 ('N. T1 foreground','Prior3787 identity/probability rows and221 E2 raw input sets retained by reference; no historical or source T1 rows reread. Exact E1 representations remain absent.'),
 ('O. TEXT','56 final state representations retained; vocabulary/IDF alone are not row inputs. Raw text+vectorizer OR exact TFIDF rows acceptable. No transformation performed.'),
 *[(f'{letter}. E2 {config}', 'NOT_READY. OOF and final-TRAIN mean triplets reproducible from frozen evidence, but neither full population automatically satisfies the selected primary baseline.') for letter,config in [('P','C+P'),('Q','C+T'),('R','P+T'),('S','C+P+T')]],
 ('T. Fidelity','Future residual/sigmoid/additivity contracts frozen; no fidelity execution or tolerance change. Numerical additivity is not a formal correctness or causal guarantee.'),
 ('U. Stability','Seeds20260901–20260920, deterministic1e-12 repeat bound and required rank/sign/TV diagnostics retained. No instability suppression.'),
 ('V. Heterogeneity','Frozen thresholds and all-project universal-claim rule retained; no family removal. Correlated-feature grouping requires missing TRAIN features.'),
 ('W. Figures','Eight mandatory and optional E3 figure contracts prepared; none generated or publication-ready. E3 preserves375 RAW/14 isotonic LightGBM P mappings.'),
 ('X. Remaining blockers','Systematic E1 X gaps and primary-reference population linkage remain. OOF matches meta-training information regime; final-TRAIN reference describes the deployed predictor. No meta refitting or silent baseline substitution.'),
 ('Y. Verdict',VERDICT+'; prepared contracts are not resolved scientific inputs. '+json.dumps(v,sort_keys=True)),
 ('Z. Next action',r['next_action']+' Separate authorization remains required before populations, primary XAI and figures.')]
 text='# Sprint56.2D — Q1 missing-evidence remediation\n\n'+'\n\n'.join('## '+a+'\n\n'+b for a,b in sections)
 text+='\n\n## Methodological basis\n\nEvaluateXAI reports reliability/consistency issues for rule-based explainers in software analytics including JIT-SDP ([Awal and Roy](https://arxiv.org/abs/2407.13902)). FoX studies formal correctness and robustness against model-agnostic alternatives ([A Formal Explainer](https://doi.org/10.1145/3664809)). These motivate auditable fidelity/stability controls, not a claim that TreeSHAP inherits formal-explanation guarantees. LIME remains excluded; no substitute explainer installed.\n\nAll prohibited current counters remain0;336 TRAIN-only mean components were computed solely for authorized reference feasibility. Parent byte snapshots agree; only referenced probability object hashes were rechecked, other store objects monitored by unchanged filesystem metadata. No model query, T1/T2 read, plot, refit or attribution.\n\nSPRINT56_2D_Q1_XAI_EXECUTION_READINESS =\n'+VERDICT+'\n\nREADY FOR HUMAN REVIEW BEFORE PRIMARY XAI EXECUTION\n'
 (OUT/'SPRINT56_2D_Q1_XAI_REMEDIATION_REPORT.md').write_text(text)
 save('implementation_provenance.json',{'source_sha256':sha(Path(__file__)),'test_sha256':sha(ROOT/'tests/evaluation/test_q1_primary_xai_missing_evidence_remediation.py') if (ROOT/'tests/evaluation/test_q1_primary_xai_missing_evidence_remediation.py').exists() else None})
 prior=read(OUT/'metadata_access_log.json')['paths'] if (OUT/'metadata_access_log.json').exists() else []
 save('metadata_access_log.json',{'paths':sorted(READS|set(prior)),'no_T1_T2_scientific_payload_reads':True})
 manifest();print(VERDICT)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('stage',choices=['build','resume-contracts','finalize','manifest']);{'build':build,'resume-contracts':finish_contracts,'finalize':finalize,'manifest':manifest}[p.parse_args().stage]()
