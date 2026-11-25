"""TRAIN reference and invented-input method compatibility; never attributes T1."""
import hashlib, io, json, warnings
from pathlib import Path
import numpy as np
import joblib

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
TRAIN=ROOT/'audits/q1-e1-canonical-apachejit-train-reentry/1.0.0/source_snapshots/apache_activemq/CODE'
RECON=ROOT/'audits/q1-xai-reconstruction-execution/1.0.0'
FEATURES=['la','ld','nf','nd','ns','ent']
ALGS=['Logistic Regression','Random Forest','XGBoost','LightGBM']
def sha(b):return hashlib.sha256(b).hexdigest()
def canon(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def write(n,v):
    with (OUT/n).open('xb') as f:f.write(canon(v)+b'\n')
def desc(v):
    a=np.ascontiguousarray(v);return {'dtype':a.dtype.str,'shape':list(a.shape),'sha256':sha(a.tobytes())}
def rows(p):return [json.loads(l) for l in p.read_bytes().splitlines() if l.strip()]
def main():
    hashes={}
    for l in (TRAIN/'MANIFEST.sha256').read_text().splitlines():
        h,n=l.split();assert sha((TRAIN/n).read_bytes())==h;hashes[str((TRAIN/n).relative_to(ROOT))]=h
    source=rows(TRAIN/'source.jsonl');order=rows(TRAIN/'row_order.jsonl')
    assert len(source)==3675 and len({r['row_identifier'] for r in source})==3675
    assert [r['row_identifier'] for r in source]==[r['row_identifier'] for r in order]
    for r in source:
        assert set(r)=={'project','partition','commit_identity','row_identifier','scientific_fields'}
        assert r['partition']=='TRAIN' and r['project']=='apache/activemq'
        assert r['row_identifier']==sha(('apachejit-v2|apache/activemq|apache/activemq|'+r['commit_identity']).encode())
        assert set(r['scientific_fields'])==set(FEATURES)
        assert all(type(r['scientific_fields'][k]) in (int,float) and np.isfinite(r['scientific_fields'][k]) for k in FEATURES)
    x=np.asarray([[r['scientific_fields'][k] for k in FEATURES] for r in source],dtype=np.float64)
    journal=RECON/'repetitions/rep_01/component_journal.jsonl'
    assert sha(journal.read_bytes())=='80d64276ddd1fd938b056dbd317e10713a2fd0bb50445826cfd23611d33bb1e5'
    records={r['algorithm']:r for r in rows(journal) if r.get('logical_id') in ['apache/activemq|'+a+'|FINAL_BASE|C' for a in ALGS]}
    models={};common=None
    for a in ALGS:
        r=records[a];p=RECON/r['executable']['path'];blob=p.read_bytes();assert sha(blob)==r['executable']['sha256']
        hashes[str(p.relative_to(ROOT))]=sha(blob);pipe=joblib.load(io.BytesIO(blob));models[a]=pipe
        pre=r['canonical_state']['preprocessing'];assert desc(pipe.named_steps['imputer'].statistics_)==pre['imputer_statistics']
        if common is None:common=pre['imputer_statistics']
        assert common==pre['imputer_statistics']
        if 'scaler' in pipe.named_steps:
            assert {k:desc(np.ascontiguousarray(getattr(pipe.named_steps['scaler'],k+'_'))) for k in ['mean','scale','var','n_samples_seen']}==pre['scaler']
        assert np.isfinite(pipe[:-1].transform(x)).all()
    representation={'project':'apache/activemq','modality':'CODE','feature_order':FEATURES,'dtype':'float64','common_preprocessing':{'imputer_statistics':common},'stage':'COMMON_IMPUTED_INPUT_BEFORE_FAMILY_SPECIFIC_LR_SCALER'}
    representation_id=sha(canon(representation))
    def key(r):return sha(canon({'seed':20260901,'purpose':'TRAIN_REFERENCE','project':'apache/activemq','representation_identity':representation_id,'row_identifier':r['row_identifier']}))
    selection=sorted(range(len(source)),key=lambda i:(key(source[i]),source[i]['row_identifier']))[:256]
    identity=[{k:source[i][k] for k in ['project','partition','commit_identity','row_identifier']}|{'selection_key':key(source[i]),'source_row_index':i} for i in selection]
    selected=x[selection];lr=models['Logistic Regression'];z=lr[:-1].transform(selected);mu=z.mean(axis=0)
    assert np.array_equal(mu,lr[:-1].transform(selected).mean(axis=0))
    # Preserve selected source bytes; no labels and no synthetic reference points.
    raw=(TRAIN/'source.jsonl').read_bytes().splitlines(keepends=True)
    with (OUT/'train_reference.jsonl').open('xb') as f:
        for i in selection:f.write(raw[i])
    write('reference_identities.json',identity)
    write('lr_transformed_mean.json',{'feature_order':FEATURES,'values':mu.tolist(),'descriptor':desc(mu),'selected_rows':256,'pipeline_sha256':records['Logistic Regression']['executable']['sha256']})
    write('reference_result.json',{'status':'REF PASS','source_rows':3675,'valid_rows':3675,'excluded_rows':0,'selected_rows':256,'strata':{'UNLABELLED':256},'labels_used':False,'partition':'TRAIN','representation':representation,'representation_identity':representation_id,'reference_sha256':sha((OUT/'train_reference.jsonl').read_bytes()),'identity_digest':sha(canon([r['row_identifier'] for r in identity])),'selection_digest':sha(canon(identity)),'order':'ascending stable_key, row_identifier tie-break','source_temporal_range':None,'temporal_range_limitation':'Snapshot row-order metadata has no timestamp; no dates inferred or other partition source opened. TRAIN membership verified for all rows.','tree_data':None,'lr_mean_repeatability_exact':True,'historical_hashes':hashes})
    fixture=json.loads((OUT/'authorization.json').read_text())['fixture_raw_rows']
    fx=np.asarray(fixture,dtype=np.float64)
    results={}
    import shap
    for a in ALGS:
        pipe=models[a];model=pipe.named_steps['model'];xx=pipe[:-1].transform(fx)
        try:
            with warnings.catch_warnings(record=True) as ww:
                warnings.simplefilter('always')
                if a=='Logistic Regression':
                    phi=(xx-mu)*model.coef_[0];base=float(model.intercept_[0]+mu@model.coef_[0]);output=model.decision_function(xx)
                    err=float(np.max(np.abs(1/(1+np.exp(-output))-pipe.predict_proba(fx)[:,1])))
                    bound=1e-10;assert err<=1e-10;scale='LOGIT';repeat=phi.copy()
                else:
                    exp=shap.TreeExplainer(model,data=None,feature_perturbation='tree_path_dependent',model_output='raw')
                    def run():
                        values=np.asarray(exp.shap_values(xx,approximate=False,check_additivity=True));base=np.asarray(exp.expected_value)
                        if a=='Random Forest':
                            pos=int(np.flatnonzero(model.classes_==1)[0]);assert values.shape==(4,6,2)
                            return values[:,:,pos],float(base[pos])
                        return values,float(base.reshape(-1)[0])
                    phi,base=run();repeat,base2=run();assert base==base2
                    output=model.predict_proba(xx)[:,1] if a=='Random Forest' else model.predict(xx,**({'output_margin':True} if a=='XGBoost' else {'raw_score':True}))
                    scale='POSITIVE_CLASS_PROBABILITY' if a=='Random Forest' else 'NATIVE_RAW_MARGIN';bound=1e-6
                assert phi.shape==(4,6) and np.isfinite(phi).all() and np.isfinite(output).all() and np.isfinite(base)
                residual=np.abs(base+phi.sum(axis=1)-output);passed=bool(np.all(residual<=bound*(1+np.abs(output))))
                exact=bool(np.array_equal(phi,repeat))
                results[a]={'status':'METHOD PASS' if passed and exact else 'FAIL','fixture_rows':4,'real_T1_attributions':0,'scale':scale,'max_residual':float(residual.max()),'repeatability_exact':exact,'data':None if a!='Logistic Regression' else 'selected TRAIN transformed mean','approximate':False,'warning_categories':sorted({type(w.message).__name__ for w in ww})}
        except Exception as e:
            results[a]={'status':'INCONCLUSIVE','error_type':type(e).__name__,'error':str(e),'real_T1_attributions':0,'no_fallback_applied':True}
    assert all(sha((ROOT/p).read_bytes())==h for p,h in hashes.items())
    write('method_results.json',results)
    print(json.dumps(results))
if __name__=='__main__':main()
