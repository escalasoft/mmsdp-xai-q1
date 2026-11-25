"""Prospective D-RF verifier: accepted T1 only; no fitting or mixed-source access."""
import datetime, decimal, fcntl, gzip, hashlib, importlib.metadata, io, json, os, platform, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
C = 'audits/q1-e1-code-permission-c/1.0.0/'
I = 'audits/q1-bounded-complementary-e1-xai/1.0.0/'
R = 'audits/q1-xai-reconstruction-execution/1.0.0/'
T = 'audits/q1-t1-confirmatory-execution/1.0.0/'
P = 'audits/q1-xai-reconstruction-equivalence-protocol/1.0.0/'
FEATURES = ['la','ld','nf','nd','ns','ent']
ALGS = ['Random Forest']
PINS = {
 C+'validated/code_t1.jsonl':'16a30607ce34bb11703b8810f026fbdf0fd39725e2ee9774c55e2c0e9211e91c',
 C+'validated/provenance.json':'9a8b826d6d72ebf6c3c54253a70d01d6690768062912a5981a0cc624867c2f84',
 C+'completion.json':'658506923f0e0fe739ac64270b5234fd051bfd3d9d155b07fc5a14e0bbf3f981',
 I+'e1_t1_global_foreground_population.jsonl':'e80eda789dedabbe3cb249aa15d3c3568cc19ebff2c4551ae7b2b7a293ff4b02',
 I+'e1_local_case_population.jsonl':'7dfb985d78b10bed896c003da2b1dd6fa36a682e5f74b3f1f2a2d2dcf8c333e5',
 I+'representations/t1_row_registry.jsonl':'8faa1cede722f2858ee4c546bea9257687c5cb31c978f05c646e3e6d854345e5',
 R+'repetitions/rep_01/component_journal.jsonl':'80d64276ddd1fd938b056dbd317e10713a2fd0bb50445826cfd23611d33bb1e5',
 P+'numerical_tolerance_policy.json':'62fd3780c94c6a69bfc036bdd4b567409ffc46c8c892a807b221f5d40d0eb336',
 T+'results/t1_prediction_evidence.jsonl.gz':'eb4b6956b185e63cd322d92b8cdf96f53fcb09ef83b6a16f2334d660c6f5adc8',
 T+'results/post_execution_integrity.json':'98144cf3a61063bcce1c833b4b90ae6b79fc8835dc7f63a2b5d0e392302cb6dc',
}
PINS.update({'audits/q1-t1-confirmatory-execution/1.0.0/results/MANIFEST.sha256': 'f396cfa0db8d01c8c1392fe7bb8affe8413638e3c0e20a3c113d7fe94a6d3a7e', 'audits/q1-xai-reconstruction-equivalence-protocol/1.0.0/deterministic_execution_contract.json': '2130f60bd3d3dd2e35f2409b5110ba015bdc118ff08c3018c733aa62cd78c0d7', 'audits/q1-xai-reconstruction-execution/1.0.0/runtime.json': 'fe00b9b6a7111545e627cafa917297fa2cc6e9588069e101adc69aef8af49cb2', 'src/evaluation/q1_t1_confirmatory_execution.py': '2232b338de5c7411fe0c1f04e1a71ecf5778b01b62c0da93382ff158de601c26', 'src/experimentation/q1_controlled_unimodal_modeling.py': 'b25e27eaf89d54d376aca95529e9765130700cc734fa7bf95b60e2abe66e5145'})
def sha(b): return hashlib.sha256(b).hexdigest()
def canonical(v): return (json.dumps(v,ensure_ascii=True,allow_nan=False,sort_keys=True,separators=(',',':'))+'\n').encode()
def require(ok, code):
    if not ok: raise RuntimeError(code)
def read(p): return (ROOT/p).read_bytes()
def lines(p): return [json.loads(l) for l in read(p).splitlines() if l.strip()]
def write(name,v):
    with (OUT/name).open('xb') as f: f.write(canonical(v))
def worker():
    import numpy as np, joblib
    hashes = {p:sha(read(p)) for p in PINS}
    require(hashes==PINS,'INPUT_HASH_MISMATCH')
    baseline=json.loads((OUT/'prospective_record.json').read_text())['preserved_D_hashes']
    hashes.update(baseline)
    require(all(sha(read(p))==h for p,h in baseline.items()),'D_INVARIANCE')
    runtime={n:importlib.metadata.version(n) for n in ['numpy','scipy','scikit-learn','xgboost','lightgbm','joblib']}
    runtime['python']=platform.python_version()
    frozen=json.loads(read(P+'deterministic_execution_contract.json'))['frozen_runtime']
    require(all(runtime[k]==v for k,v in frozen.items()) and runtime['joblib']=='1.5.3','RUNTIME_MISMATCH')
    for p in [P+'deterministic_execution_contract.json',R+'runtime.json',T+'results/MANIFEST.sha256', 'src/evaluation/q1_xai_train_source_reconstruction.py','src/evaluation/q1_t1_confirmatory_execution.py','src/experimentation/q1_controlled_unimodal_modeling.py']:
        hashes[p]=sha(read(p))
    receipt=json.loads(read(C+'completion.json')); provenance=json.loads(read(C+'validated/provenance.json'))
    require(receipt['accepted'] and receipt['status']=='PASS' and receipt['output_sha256']==PINS[C+'validated/code_t1.jsonl'],'C_NOT_ACCEPTED')
    require(provenance['output_sha256']==receipt['output_sha256'] and provenance['rows']==245,'C_PROVENANCE_MISMATCH')
    registry=lines(I+'representations/t1_row_registry.jsonl')
    ids=[r['row_identifier'] for r in registry]
    require(len(ids)==len(set(ids))==245,'REGISTRY_COUNT')
    require([r['order_key'] for r in registry]==sorted(r['order_key'] for r in registry),'TEMPORAL_ORDER')
    for r in registry:
        require(r['partition']=='T1' and r['project']=='apache/activemq','IDENTITY_SCOPE')
        require(r['row_identifier']==sha(('apachejit-v2|apache/activemq|apache/activemq|'+r['commit_identity']).encode()),'COMMIT_BINDING')
    fg=lines(I+'e1_t1_global_foreground_population.jsonl'); local=lines(I+'e1_local_case_population.jsonl')
    require(len(fg)==245 and {r['row_identifier'] for r in fg}==set(ids),'FOREGROUND_SET')
    require(len(local)==8 and len({r['row_identifier'] for r in local})==8 and {r['row_identifier'] for r in local}<=set(ids),'LOCAL_SET')
    def unique(pairs):
        d={}
        for k,v in pairs:
            require(k not in d,'DUPLICATE_JSON_KEY');d[k]=v
        return d
    rows=[json.loads(l,parse_float=decimal.Decimal,object_pairs_hook=unique) for l in read(C+'validated/code_t1.jsonl').splitlines()]
    require([r['row_identifier'] for r in rows]==ids,'OUTPUT_IDENTITY_ORDER')
    for r in rows:
        require(set(r)==set(['row_identifier']+FEATURES),'OUTPUT_SCHEMA')
        require(re.fullmatch('[0-9a-f]{64}',r['row_identifier']) is not None,'ID_TYPE')
        for k in FEATURES:
            require(type(r[k]) in (int,decimal.Decimal) and decimal.Decimal(r[k]).is_finite(),'NUMERIC_TYPE')
    # Explicit historical representation: float64 in frozen CODE_FEATURES order.
    x=np.asarray([[float(r[k]) for k in FEATURES] for r in rows],dtype=np.float64)
    require(x.shape==(245,6) and np.isfinite(x).all(),'FLOAT64_INPUT')
    records={r['algorithm']:r for r in lines(R+'repetitions/rep_01/component_journal.jsonl') if r.get('logical_id') in ['apache/activemq|'+a+'|FINAL_BASE|C' for a in ALGS]}
    require(set(records)==set(ALGS),'PIPELINE_INVENTORY')
    # Only T1 evidence; filter scope before JSON decoding. No mixed source opened.
    refs={a:[] for a in ALGS}
    compressed=read(T+'results/t1_prediction_evidence.jsonl.gz')
    require(sha(compressed)==PINS[T+'results/t1_prediction_evidence.jsonl.gz'],'REFERENCE_CAPTURE_HASH')
    with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as f:
        for line in f:
            if b'"project":"apache/activemq"' not in line or b'"configuration":"C"' not in line: continue
            if not any(('"algorithm":"'+a+'"').encode() in line for a in ALGS): continue
            e=json.loads(line)
            if e['project']!='apache/activemq' or e['configuration']!='C' or e['algorithm'] not in ALGS: continue
            refs[e['algorithm']].append({k:e[k] for k in ['row_identifier','raw_predicted_probability','model_identity_sha256','model_provenance','modalities']})
    def desc(v):
        a=np.ascontiguousarray(np.asarray(v)); return {'dtype':a.dtype.str,'shape':list(a.shape),'sha256':sha(a.tobytes(order='C'))}
    result={}
    for alg in ALGS:
        record=records[alg]; old=record['canonical_state']; prov=old['provenance']; artifact=R+record['executable']['path']
        payload=read(artifact);hashes[artifact]=sha(payload)
        require(hashes[artifact]==record['executable']['sha256'] and len(payload)==record['executable']['bytes'],'PIPELINE_HASH')
        pipe=joblib.load(io.BytesIO(payload)); model=pipe.named_steps['model']; imp=pipe.named_steps['imputer']
        require(all(model.get_params()[k]==v for k,v in prov['selected_parameters'].items()),'MODEL_PARAMETERS')
        pre={'type':'NUMERIC','imputer_statistics':desc(imp.statistics_)}
        if 'scaler' in pipe.named_steps:
            sc=pipe.named_steps['scaler'];pre['scaler']={k:desc(getattr(sc,k+'_')) for k in ['mean','scale','var','n_samples_seen']}
        m={'algorithm':alg,'classes':model.classes_.tolist(),'n_features_in':int(model.n_features_in_)}
        require(m['classes']==[0,1] and m['n_features_in']==6,'FEATURE_CLASS_CONTRACT')
        tree_digests=[]
        for estimator in model.estimators_:
            tree=estimator.tree_
            td={'node_count':int(tree.node_count),'max_depth':int(tree.max_depth)}
            for key in ['children_left','children_right','feature','threshold','impurity','n_node_samples','weighted_n_node_samples','value']:
                td[key]=desc(getattr(tree,key))
            tree_digests.append(sha(canonical(td)))
        m.update(estimator_count=len(tree_digests),tree_digests=tree_digests)
        require(len(tree_digests)==300 and model.n_jobs==1,'RF_ESTIMATOR_CONTRACT')
        state={'logical_id':record['logical_id'],'provenance':prov,'preprocessing':pre,'model':m}
        require(state==old and sha(canonical(state))==record['canonical_state_sha256'],'LEARNED_STATE_MISMATCH_'+alg)
        rr=refs[alg]
        require([r['row_identifier'] for r in rr]==ids,'REFERENCE_ORDER_'+alg)
        mids={r['model_identity_sha256'] for r in rr}
        require(len(mids)==1 and mids<=set(prov['consuming_model_identity_sha256']),'REFERENCE_MODEL_IDENTITY')
        for r in rr:
            mp=r['model_provenance']
            require(r['modalities']==['C'] and mp['training_partition']=='TRAIN' and mp['train_identity_sha256']==prov['train_membership_sha256'],'REFERENCE_TRAIN_BINDING')
            require(mp['selected_candidate_ids'].get('C')==prov['selected_candidate_id'],'REFERENCE_CANDIDATE')
        ref=np.asarray([r['raw_predicted_probability'] for r in rr],dtype=np.float64)
        predicted=np.asarray(pipe.predict_proba(x)[:,1],dtype=np.float64)
        require(np.isfinite(predicted).all() and np.isfinite(ref).all(),'NONFINITE_PROBABILITY')
        delta=np.abs(predicted-ref);domain=np.abs(ref)>=1e-8;rel=delta[domain]/np.abs(ref[domain])
        valid=delta<=1e-12;valid[domain]&=rel<=1e-10
        mismatches=int(np.count_nonzero((predicted>=.5)!=(ref>=.5)))
        result[alg]={'status':'PASS' if valid.all() and not mismatches else 'FAIL','compared':245,'matches':int(valid.sum()),'exact_matches':int(np.count_nonzero(delta==0)),'max_absolute_error':float(delta.max()),'mean_absolute_error':float(delta.mean()),'max_relative_error':float(rel.max(initial=0)),'relative_domain_count':int(domain.sum()),'out_of_tolerance':int(np.count_nonzero(~valid)),'classification_discrepancies':mismatches,'nan_inf':False,'local_cases_compared':8,'pipeline_sha256':hashes[artifact],'canonical_state_sha256':record['canonical_state_sha256'],'model_identity_sha256':next(iter(mids)),'probabilities_float64_sha256':sha(predicted.tobytes()),'reference_float64_sha256':sha(ref.tobytes())}

    require(all(sha(read(p))==h for p,h in hashes.items()),'HISTORICAL_MUTATION')
    return {'status':'PASS' if all(v['status']=='PASS' for v in result.values()) else 'FAIL','results':result,'historical_hashes':hashes,'runtime':runtime,'platform':platform.platform(),'historical_invariance':True,'temporal_rows':245,'local_cases':8,'feature_order':FEATURES}

def main():
    if '--worker' in sys.argv:
        try: print(json.dumps(worker(),allow_nan=False))
        except Exception as e: print(json.dumps({'status':'INCONCLUSIVE','error_type':type(e).__name__,'reason':str(e) if isinstance(e,RuntimeError) else 'VERIFICATION_EXCEPTION_NO_DATA_DISCLOSED'}));sys.exit(1)
        return
    now=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat()
    write('authorization.json',{'stage':'D-RF','version':'1.0.0','created_utc':now(),'user_authorized':True,'scope':'245 ActiveMQ CODE T1; RF RAW predictive equivalence only','repetitions':3,'pins':PINS,'absolute_tolerance':1e-12,'relative_tolerance':1e-10,'relative_domain':1e-8,'threshold':0.5,'prohibited':['mixed CODE source','T2','fit','calibration','SHAP','E1 explanations'],'verifier_sha256':sha(Path(__file__).read_bytes())})
    lock=ROOT/C/'scientific.lock'
    with lock.open('rb') as f:
        st=os.fstat(f.fileno());require((st.st_dev,st.st_ino)==(16777225,131286779),'LOCK_IDENTITY')
        fcntl.flock(f,fcntl.LOCK_SH|fcntl.LOCK_NB)
        reps=[]
        for i in range(1,4):
            p=subprocess.run([sys.executable,'-B',str(Path(__file__).resolve()),'--worker'],capture_output=True,text=True,timeout=120)
            try:r=json.loads(p.stdout)
            except Exception:r={'status':'INCONCLUSIVE','reason':'WORKER_PROTOCOL'}
            r['stderr_present']=bool(p.stderr);r['stderr_sha256']=sha(p.stderr.encode());r['returncode']=p.returncode
            write(f'repetition_{i:02d}.json',r);reps.append(r)
            if r['status']!='PASS':break
        repeat=len(reps)==3 and all(r['results']==reps[0]['results'] for r in reps)
        write('result.json',{'stage':'D-RF','completed_utc':now(),'status':'FAIL' if any(r['status']=='FAIL' for r in reps) else ('PASS' if repeat else 'INCONCLUSIVE'),'repetitions_completed':len(reps),'exact_repeatability':repeat,'results':reps[-1].get('results',{}),'failure':reps[-1].get('reason'),'historical_invariance':all(r.get('historical_invariance',False) for r in reps),'lock_device':st.st_dev,'lock_inode':st.st_ino,'no_mixed_source_no_T2_no_SHAP':True})
    print((OUT/'result.json').read_text())
if __name__=='__main__':main()
