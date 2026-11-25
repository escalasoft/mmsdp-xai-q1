"""E1 CODE generation and independent disk-only verification. No fitting."""
import os,sys,json,hashlib,datetime,ctypes,fcntl,io,warnings,itertools
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr
ROOT=Path(__file__).resolve().parents[3]; AUDIT=Path(__file__).resolve().parent
ENV=ROOT/'audits/q1-e1-code-environment-reference/1.0.0'
I=ROOT/'audits/q1-bounded-complementary-e1-xai/1.0.0'
C=ROOT/'audits/q1-e1-code-permission-c/1.0.0'
R=ROOT/'audits/q1-xai-reconstruction-execution/1.0.0'
FEATURES=['la','ld','nf','nd','ns','ent']
ALGS={'LR':'Logistic Regression','RF':'Random Forest','XGB':'XGBoost','LGB':'LightGBM'}
def sha(x):return hashlib.sha256(x).hexdigest()
def read(p):return json.loads(p.read_text())
def rows(p):return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
def write(p,v):
    with p.open('x') as f:json.dump(v,f,sort_keys=True,allow_nan=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
def check(ok,reason):
    if not ok:raise RuntimeError(reason)
def signs(a):return np.where(a>1e-12,1,np.where(a< -1e-12,-1,0))
def summary(phi):
    absolute=np.mean(np.abs(phi),axis=1);signed=np.mean(phi,axis=1)
    ranks=[sorted(range(6),key=lambda j:(-v[j],FEATURES[j])) for v in absolute]
    pairs=[]
    for i,j in itertools.combinations(range(20),2):
        spearman=float(spearmanr(absolute[i],absolute[j]).statistic)
        tv=float(.5*np.sum(np.abs(absolute[i]/absolute[i].sum()-absolute[j]/absolute[j].sum()))) if absolute[i].sum()>0 and absolute[j].sum()>0 else None
        topi=set(ranks[i][:3]);topj=set(ranks[j][:3])
        pairs.append({'i':i,'j':j,'maximum_attribution_difference':float(np.max(np.abs(phi[i]-phi[j]))),'jaccard_top3':len(topi&topj)/len(topi|topj),'jaccard_top6':1.,'top6_informative':False,'spearman':spearman if np.isfinite(spearman) else None,'sign_agreement':float(np.mean(signs(phi[i])==signs(phi[j]))),'global_sign_agreement':float(np.mean(signs(signed[i])==signs(signed[j]))),'total_variation':tv})
    finite=all(p['spearman'] is not None and p['total_variation'] is not None for p in pairs)
    stable=finite and all(p['maximum_attribution_difference']<=1e-12 and p['jaccard_top3']>=.6 and p['spearman']>=.7 and p['sign_agreement']>=.8 and p['total_variation']<=.25 for p in pairs)
    return {'features':FEATURES,'mean_absolute':absolute.tolist(),'signed_mean':signed.tolist(),'feature_ranks':[[FEATURES[j] for j in rr] for rr in ranks],'support_count':245,'stability_pairs':pairs,'stability':'STABLE' if stable else ('INSUFFICIENT_EVIDENCE' if not finite else 'UNSTABLE'),'primary_repetition':0}
def identities():
    registry=rows(I/'representations/t1_row_registry.jsonl');fg=rows(I/'e1_t1_global_foreground_population.jsonl');loc=rows(I/'e1_local_case_population.jsonl')
    ids=[r['row_identifier'] for r in registry]; check(len(ids)==len(set(ids))==245,'IDENTITY_COUNT')
    check(set(ids)=={r['row_identifier'] for r in fg} and len(loc)==8,'POPULATION')
    check([r['order_key'] for r in registry]==sorted(r['order_key'] for r in registry),'TEMPORAL_ORDER')
    for r in registry:
        check(r['project']=='apache/activemq' and r['partition']=='T1','SCOPE')
        check(sha(('apachejit-v2|apache/activemq|apache/activemq|'+r['commit_identity']).encode())==r['row_identifier'],'COMMIT_IDENTITY')
    lp={r['row_identifier']:i for i,r in enumerate(loc)};fp={r['row_identifier']:i for i,r in enumerate(fg)}
    check(len(lp)==8 and set(lp)<=set(ids),'LOCAL_MEMBERSHIP')
    return [dict(r,temporal_index=i,foreground_index=fp[r['row_identifier']],local_index=lp.get(r['row_identifier'])) for i,r in enumerate(registry)]
def local_records(arr,index):
    for t in range(20):
        for r in sorted((r for r in index if r['local_index'] is not None),key=lambda r:r['local_index']):
            i=r['temporal_index'];yield {'schema':'e1-code-local-1.0.0','repetition':t,'seed':20260901+t,'row_identifier':r['row_identifier'],'commit_identity':r['commit_identity'],'local_index':r['local_index'],'phi':arr['phi'][t,i].tolist(),'base':float(arr['base'][t,i]),'model_output':float(arr['model_output'][t,i]),'reconstructed':float(arr['reconstructed'][t,i]),'residual':float(arr['residual'][t,i])}
def validate_model(directory,index,code):
    with np.load(directory/'explanations.npz',allow_pickle=False) as z:arr={k:z[k] for k in z.files}
    meta=read(directory/'metadata.json')
    check(arr['row_identifier'].tolist()==[r['row_identifier'] for r in index],'DISK_IDENTITIES')
    check(arr['commit_identity'].tolist()==[r['commit_identity'] for r in index] and arr['features'].tolist()==FEATURES,'DISK_FEATURES')
    check(str(arr['model_identity'])==meta['model_identity'] and arr['seeds'].tolist()==list(range(20260901,20260921)),'DISK_MODEL_SEEDS')
    check(arr['phi'].shape==(20,245,6),'DISK_DIMENSIONS')
    for k in ['base','model_output','reconstructed','residual','probability']:
        check(arr[k].shape==(20,245) and np.isfinite(arr[k]).all(),'DISK_DIMENSIONS_FINITE')
    check(np.isfinite(arr['phi']).all(),'ATTRIBUTION_FINITE')
    reconstructed=arr['base']+arr['phi'].sum(axis=2);residual=reconstructed-arr['model_output'];tol=1e-10 if code=='LR' else 1e-6
    check(np.array_equal(reconstructed,arr['reconstructed']) and np.array_equal(residual,arr['residual']),'DISK_RESIDUAL')
    check(np.all(np.abs(residual)<=tol*(1+np.abs(arr['model_output']))),'FIDELITY')
    if code=='LR':check(np.max(np.abs(1/(1+np.exp(-reconstructed))-arr['probability']))<=1e-10,'LR_PROBABILITY_RECONSTRUCTION')
    if code=='RF':check(np.array_equal(arr['model_output'],arr['probability']),'RF_SCALE')
    global_data=summary(arr['phi']);check(global_data==read(directory/'global.json'),'GLOBAL_RECONSTRUCTION')
    check(global_data['stability']=='STABLE','STABILITY')
    check(list(local_records(arr,index))==rows(directory/'local.jsonl'),'LOCAL_RECONSTRUCTION')
    # Independent reduction path for the primary aggregate, no SHAP/model calls.
    import math
    alternate=[math.fsum(abs(float(v)) for v in arr['phi'][0,:,j])/245 for j in range(6)]
    check(np.max(np.abs(np.asarray(alternate)-np.asarray(global_data['mean_absolute'][0])))<=1e-12,'INDEPENDENT_GLOBAL_REDUCTION')
    return {'status':'PASS','rows':245,'local_rows':8,'repetitions':20,'max_abs_residual':float(np.max(np.abs(residual))),'maximum_attribution_repeat_difference':max(p['maximum_attribution_difference'] for p in global_data['stability_pairs']),'stability':'STABLE','pairs_checked':190,'arrays_reconstructed':True,'global_and_local_reconstructed':True}
def manifest(directory):
    hashes={str(p.relative_to(directory)):sha(p.read_bytes()) for p in sorted(directory.rglob('*')) if p.is_file() and p.name!='MANIFEST.json'}
    write(directory/'MANIFEST.json',hashes)
def verify(directory):
    for p,h in read(directory/'MANIFEST.json').items():check(sha((directory/p).read_bytes())==h,'PUBLISHED_HASH')
    index=rows(directory/'identities.jsonl');check(index==identities(),'PUBLISHED_INDEX')
    status=read(directory/'status.json');verified={}
    for code in ALGS:
        if status[code]['status']=='PASS':verified[code]=validate_model(directory/code,index,code)
        else:verified[code]={'status':status[code]['status'],'diagnostics_only':True}
    return verified
def execute():
    import joblib,shap,importlib.metadata,platform
    auth=read(AUDIT/'authorization.json')
    for p,h in auth['input_hashes'].items():check(sha((ROOT/p).read_bytes())==h,'INPUT_HASH')
    check(read(C/'completion.json')['status']=='PASS' and read(ENV/'result.json')['global']=='READY','ADMISSION')
    expected=read(ENV/'environment_inventory.json')['.venv-xai-s56']
    runtime={n:importlib.metadata.version(n) for n in ['numpy','scipy','scikit-learn','shap','numba','llvmlite','xgboost','lightgbm','joblib']}
    check(all(runtime[n]==expected[n] for n in runtime) and platform.python_version()==expected['python'],'RUNTIME')
    stage=AUDIT/'.staging';stage.mkdir(mode=0o700);index=identities()
    with (stage/'identities.jsonl').open('x') as f:
        for r in index:f.write(json.dumps(r,sort_keys=True)+'\n')
    entries=rows(C/'validated/code_t1.jsonl');check([r['row_identifier'] for r in entries]==[r['row_identifier'] for r in index],'SOURCE_ORDER')
    check(all(set(r)==set(['row_identifier']+FEATURES) for r in entries),'SOURCE_SCHEMA')
    x=np.asarray([[r[k] for k in FEATURES] for r in entries],dtype=np.float64);check(np.isfinite(x).all(),'SOURCE_FINITE')
    mu=np.asarray(read(ENV/'lr_transformed_mean.json')['values'],dtype=np.float64)
    journal=R/'repetitions/rep_01/component_journal.jsonl';check(sha(journal.read_bytes())=='80d64276ddd1fd938b056dbd317e10713a2fd0bb50445826cfd23611d33bb1e5','JOURNAL')
    rec={r['algorithm']:r for r in rows(journal) if r.get('logical_id') in ['apache/activemq|'+a+'|FINAL_BASE|C' for a in ALGS.values()]}
    control=read(ENV/'environment_repetition_1.json')['results'];statuses={};model_hashes={}
    for code,algorithm in ALGS.items():
        dest=stage/code;dest.mkdir();saved=[];counter={'explainer_calls':0,'attribution_rows':0,'direct_prediction_calls':0,'direct_prediction_rows':0,'internal_tree_operations':None,'local_extra_calls':0}
        try:
            r=rec[algorithm];blob=(R/r['executable']['path']).read_bytes();check(sha(blob)==r['executable']['sha256']==control[algorithm]['pipeline_sha256'],'MODEL_HASH');model_hashes[str((R/r['executable']['path']).relative_to(ROOT))]=sha(blob)
            pipe=joblib.load(io.BytesIO(blob));model=pipe.named_steps['model'];check(model.classes_.tolist()==[0,1],'CLASSES');xx=pipe[:-1].transform(x)
            check(xx.shape==(245,6) and np.isfinite(xx).all(),'TRANSFORM')
            probability=np.asarray(model.predict_proba(xx)[:,1],dtype=np.float64);counter['direct_prediction_calls']+=1;counter['direct_prediction_rows']+=245
            check(sha(probability.tobytes())==control[algorithm]['probabilities_float64_sha256'],'PREDICTION_INVARIANCE')
            if code=='RF':output=probability;scale='POSITIVE_CLASS_PROBABILITY'
            elif code=='LR':output=model.decision_function(xx);scale='LOGIT'
            else:output=model.predict(xx,**({'output_margin':True} if code=='XGB' else {'raw_score':True}));scale='NATIVE_RAW_MARGIN'
            if code!='RF':counter['direct_prediction_calls']+=1;counter['direct_prediction_rows']+=245
            output=np.asarray(output,dtype=np.float64);all_phi=[];all_base=[];warning_log=[]
            for t in range(20):
                np.random.seed(20260901+t)
                with warnings.catch_warnings(record=True) as ww:
                    warnings.simplefilter('always')
                    if code=='LR':phi=(xx-mu)*model.coef_[0];base=float(model.intercept_[0]+mu@model.coef_[0])
                    else:
                        exp=shap.TreeExplainer(model,data=None,feature_perturbation='tree_path_dependent',model_output='raw')
                        counter['explainer_calls']+=1
                        values=np.asarray(exp.shap_values(xx,approximate=False,check_additivity=True));base_array=np.asarray(exp.expected_value)
                        if code=='RF':check(values.shape==(245,6,2),'RF_SHAPE');phi=values[:,:,1];base=float(base_array[1])
                        else:phi=values;base=float(base_array.reshape(-1)[0])
                    warning_log.extend({'repetition':t,'category':type(w.message).__name__,'message':str(w.message)} for w in ww)
                counter['attribution_rows']+=245;phi=np.asarray(phi,dtype=np.float64)
                check(phi.shape==(245,6) and np.isfinite(phi).all() and np.isfinite(base),'ATTRIBUTION_INVALID')
                reconstruction=base+phi.sum(axis=1);residual=reconstruction-output
                all_phi.append(phi);all_base.append(np.full(245,base));saved=all_phi
                check(np.all(np.abs(residual)<=(1e-10 if code=='LR' else 1e-6)*(1+np.abs(output))),'FIDELITY')
                if code=='LR':check(np.max(np.abs(1/(1+np.exp(-reconstruction))-probability))<=1e-10,'LR_PROBABILITY')
            phis=np.stack(all_phi);bases=np.stack(all_base);outputs=np.tile(output,(20,1));reconstruction=bases+phis.sum(axis=2)
            arr={'phi':phis,'base':bases,'model_output':outputs,'reconstructed':reconstruction,'residual':reconstruction-outputs,'probability':np.tile(probability,(20,1)),'row_identifier':np.asarray([r['row_identifier'] for r in index]),'commit_identity':np.asarray([r['commit_identity'] for r in index]),'features':np.asarray(FEATURES),'model_identity':np.asarray(control[algorithm]['model_identity_sha256']),'seeds':np.arange(20260901,20260921)}
            np.savez_compressed(dest/'explanations.npz',**arr)
            write(dest/'metadata.json',{'schema':'e1-code-scientific-1.0.0','model':algorithm,'model_identity':control[algorithm]['model_identity_sha256'],'pipeline_sha256':sha(blob),'features':FEATURES,'scale':scale,'positive_class':1,'method':'ANALYTICAL_CENTERED_LOGIT' if code=='LR' else 'EXACT_TREESHAP','feature_perturbation':None if code=='LR' else 'tree_path_dependent','data':None,'approximate':False,'counters':counter,'warnings':warning_log})
            write(dest/'global.json',summary(phis))
            with (dest/'local.jsonl').open('x') as f:
                for rr in local_records(arr,index):f.write(json.dumps(rr,allow_nan=False,sort_keys=True)+'\n')
            statuses[code]=validate_model(dest,index,code)
            print(code+' generation and staging validation PASS',flush=True)
        except Exception as e:
            diag=stage/'diagnostics';diag.mkdir(exist_ok=True);os.rename(dest,diag/code)
            if saved:np.savez_compressed(diag/code/'partial_attributions.npz',phi=np.stack(saved))
            statuses[code]={'status':'FAIL' if isinstance(e,RuntimeError) else 'INCONCLUSIVE','error_type':type(e).__name__,'reason':str(e),'accepted':False,'completed_repetitions':len(saved),'counters':counter}
            write(diag/code/'failure.json',statuses[code]);print(code+' '+statuses[code]['status'],flush=True)
    for p,h in {**auth['input_hashes'],**model_hashes}.items():check(sha((ROOT/p).read_bytes())==h,'HISTORICAL_MUTATION')
    write(stage/'status.json',statuses);write(stage/'provenance.json',{'runtime':runtime,'python':platform.python_version(),'platform':platform.platform(),'inputs':auth['input_hashes'],'pipelines':model_hashes,'code_sha256':sha(Path(__file__).read_bytes()),'output_contract_sha256':sha((AUDIT/'output_contract.json').read_bytes()),'historical_invariance':True,'no_T2':True,'no_PROCESS':True,'no_refit':True})
    manifest(stage);verify(stage)
    for p in stage.rglob('*'):
        if p.is_file():
            with p.open('rb') as f:os.fsync(f.fileno())
    libc=ctypes.CDLL(None,use_errno=True);fn=libc.renamex_np;fn.argtypes=[ctypes.c_char_p,ctypes.c_char_p,ctypes.c_uint];fn.restype=ctypes.c_int
    check(fn(os.fsencode(stage),os.fsencode(AUDIT/'scientific'),4)==0,'ATOMIC_PUBLICATION_FAILED')
    print('Scientific bundle published; independent verification still required.',flush=True)
if __name__=='__main__':
    if '--verify' in sys.argv:
        result=verify(AUDIT/'scientific');write(AUDIT/'independent_readback.json',{'models':result,'status':'PASS' if all(v['status']=='PASS' for v in result.values()) else 'NOT_ALL_PASS','models_or_SHAP_loaded':False,'scientific_manifest_sha256':sha((AUDIT/'scientific/MANIFEST.json').read_bytes())});print(json.dumps(result))
    else:
        with (C/'scientific.lock').open('rb') as lock:
            st=os.fstat(lock.fileno());check((st.st_dev,st.st_ino)==(16777225,131286779),'LOCK_IDENTITY');fcntl.flock(lock,fcntl.LOCK_SH|fcntl.LOCK_NB);execute()
