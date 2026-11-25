"""Descriptive synthesis of accepted persisted CODE results; no predictors/SHAP."""
import csv,json,hashlib,itertools,datetime,sys
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr,kendalltau
BASE=Path(__file__).resolve().parent; ROOT=BASE.parents[2]
SOURCE=ROOT/'audits/q1-e1-code-execution/1.0.0/scientific'
FEATURES=['la','ld','nf','nd','ns','ent']; MODELS=['LR','RF','XGB','LGB']
SCALES={'LR':'Logit (analytical decomposition)','RF':'Probability (exact TreeSHAP)','XGB':'Native margin (exact TreeSHAP)','LGB':'Native margin (exact TreeSHAP)'}
def sha(x):return hashlib.sha256(x).hexdigest()
def read(p):return json.loads(p.read_text())
def save(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x') as f:json.dump(v,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
def table(p,records):
    with p.open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
def sign(x):return np.where(x>1e-12,1,np.where(x< -1e-12,-1,0))
def finite(v):return float(v) if np.isfinite(v) else None
def load_source():
    manifest=read(SOURCE/'MANIFEST.json')
    for p,h in manifest.items():assert sha((SOURCE/p).read_bytes())==h,p
    assert all(v['status']=='PASS' for v in read(SOURCE/'status.json').values())
    index=[json.loads(l) for l in (SOURCE/'identities.jsonl').read_text().splitlines()]
    assert len(index)==245 and len({r['row_identifier'] for r in index})==245
    assert sum(r['local_index'] is not None for r in index)==8
    data={}; integrity={}
    for m in MODELS:
        with np.load(SOURCE/m/'explanations.npz',allow_pickle=False) as z:d={k:z[k] for k in z.files}
        assert d['features'].tolist()==FEATURES and d['phi'].shape==(20,245,6)
        assert d['row_identifier'].tolist()==[r['row_identifier'] for r in index]
        assert d['commit_identity'].tolist()==[r['commit_identity'] for r in index]
        assert np.isfinite(d['phi']).all()
        delta=float(np.max(np.abs(d['phi']-d['phi'][0])))
        assert delta==0
        reconstructed=d['base']+d['phi'].sum(2)
        assert np.array_equal(reconstructed,d['reconstructed']) and np.array_equal(reconstructed-d['model_output'],d['residual'])
        normalized=float(np.max(np.abs(d['residual'])/(1+np.abs(d['model_output']))))
        assert normalized <= (1e-10 if m=='LR' else 1e-6)
        g=read(SOURCE/m/'global.json');assert g['stability']=='STABLE' and len(g['stability_pairs'])==190
        assert np.array_equal(np.mean(np.abs(d['phi'][0]),axis=0),g['mean_absolute'][0])
        meta=read(SOURCE/m/'metadata.json')
        integrity[m]={'npz_sha256':sha((SOURCE/m/'explanations.npz').read_bytes()),'model_identity':str(d['model_identity']),'scale':meta['scale'],'max_residual':float(np.max(np.abs(d['residual']))),'max_normalized_residual':normalized,'max_repeat_difference':delta,'stability_pairs':190,'rows':245,'local_cases':8,'repetitions':20,'feature_values_persisted':False}
        data[m]=d
    return data,index,integrity,manifest
def analyze(dest):
    dest.mkdir(exist_ok=False)
    data,index,integrity,manifest=load_source();globalrows=[];long=[];commitrows=[];local=[];hetero=[];means={};pairrows=[];localpair=[]
    for m,d in data.items():
        phi=d['phi'][0];absolute=np.abs(phi);mean=absolute.mean(0);means[m]=mean
        rank=sorted(range(6),key=lambda j:(-mean[j],FEATURES[j]));amplitude=absolute.sum(1)
        share=np.divide(absolute,amplitude[:,None],out=np.zeros_like(absolute),where=amplitude[:,None]>0)
        dominant=[min(range(6),key=lambda j:(-absolute[i,j],FEATURES[j])) for i in range(245)]
        cancellation=np.divide(np.abs(phi.sum(1)),amplitude,out=np.ones(245),where=amplitude>0);cancellation=1-cancellation
        entropy=-np.sum(np.where(share>0,share*np.log(np.maximum(share,1e-300)),0),axis=1)/np.log(6)
        for j,f in enumerate(FEATURES):
            v=phi[:,j];av=absolute[:,j];q=np.percentile(v,[1,5,25,50,75,95,99]);aq=np.percentile(av,[25,50,75,95])
            rr={'model':m,'feature':f,'scale':SCALES[m],'n':245,'rank':rank.index(j)+1,'mean_absolute':float(mean[j]),'median_absolute':float(aq[1]),'mean_signed':float(v.mean()),'median_signed':float(q[3]),'std_signed_population':float(v.std(ddof=0)),'std_absolute_population':float(av.std(ddof=0)),'iqr_signed':float(q[4]-q[2]),'iqr_absolute':float(aq[2]-aq[0]),'minimum':float(v.min()),'maximum':float(v.max()),'positive_proportion_exact':float(np.mean(v>0)),'negative_proportion_exact':float(np.mean(v<0)),'zero_proportion_exact':float(np.mean(v==0)),'positive_proportion_1e12':float(np.mean(v>1e-12)),'negative_proportion_1e12':float(np.mean(v< -1e-12)),'null_proportion_1e12':float(np.mean(np.abs(v)<=1e-12)),'within_model_absolute_share':float(mean[j]/mean.sum()),'dominant_commit_count':dominant.count(j)}
            rr.update({f'p{p:02d}_signed':float(z) for p,z in zip([1,5,25,50,75,95,99],q)});rr['p95_absolute']=float(aq[3]);globalrows.append(rr)
            for i,r in enumerate(index):long.append({'model':m,'row_identifier':r['row_identifier'],'commit_identity':r['commit_identity'],'temporal_index':i,'feature':f,'attribution':float(v[i]),'scale':SCALES[m]})
        for i,r in enumerate(index):
            cr={'model':m,'row_identifier':r['row_identifier'],'commit_identity':r['commit_identity'],'temporal_index':i,'local_index':r['local_index'],'probability':float(d['probability'][0,i]),'decision_at_0_5':int(d['probability'][0,i]>=.5),'base':float(d['base'][0,i]),'output':float(d['model_output'][0,i]),'reconstructed':float(d['reconstructed'][0,i]),'residual':float(d['residual'][0,i]),'sum_absolute':float(amplitude[i]),'dominant_feature':FEATURES[dominant[i]],'dominant_share':float(share[i,dominant[i]]),'cancellation_index':float(cancellation[i]),'normalized_attribution_entropy':float(entropy[i])}
            commitrows.append(cr)
            if r['local_index'] is not None:
                pos=[j for j in range(6) if phi[i,j]>0];neg=[j for j in range(6) if phi[i,j]<0]
                pj=max(pos,key=lambda j:phi[i,j]) if pos else None;nj=min(neg,key=lambda j:phi[i,j]) if neg else None
                lr={**cr,'scale':SCALES[m],'model_identity':str(d['model_identity']),'phi':phi[i].tolist(),'feature_values':None,'feature_values_status':'NOT_PERSISTED_IN_AUTHORIZED_SOURCE','largest_positive_feature':FEATURES[pj] if pj is not None else None,'largest_positive_value':float(phi[i,pj]) if pj is not None else None,'largest_negative_feature':FEATURES[nj] if nj is not None else None,'largest_negative_value':float(phi[i,nj]) if nj is not None else None}
                lr['interpretation']=f"{m}: stored defect-class probability {cr['probability']:.6f} (threshold decision {cr['decision_at_0_5']}); base {cr['base']:.6f} plus six contributions reconstructs {cr['reconstructed']:.6f} on the {SCALES[m]} scale. Largest positive contribution: {lr['largest_positive_feature'] or 'none'}; largest negative contribution: {lr['largest_negative_feature'] or 'none'}. These describe model contributions, not high/low feature values or causal effects."
                local.append(lr)
        hetero.append({'model':m,'top_feature':FEATURES[rank[0]],'top_two_global_share':float(mean[rank[:2]].sum()/mean.sum()),'mean_cancellation_index':float(cancellation.mean()),'median_cancellation_index':float(np.median(cancellation)),'p90_cancellation_index':float(np.percentile(cancellation,90)),'median_normalized_entropy':float(np.median(entropy)),'median_dominant_share':float(np.median(share.max(1))),'dominant_feature_counts':{FEATURES[j]:dominant.count(j) for j in range(6)},'zero_total_attribution_rows':int(np.sum(amplitude==0)),'positive_threshold_decisions':int(np.sum(d['probability'][0]>=.5))})
    for a,b in itertools.combinations(MODELS,2):
        ma,mb=means[a],means[b];ta=set(np.argsort(-ma)[:3]);tb=set(np.argsort(-mb)[:3]);pa=data[a]['phi'][0];pb=data[b]['phi'][0];aa=np.abs(pa);ab=np.abs(pb)
        perrho=[finite(spearmanr(aa[i],ab[i]).statistic) for i in range(245)]
        good=[v for v in perrho if v is not None]
        tv=np.abs(aa/aa.sum(1)[:,None]-ab/ab.sum(1)[:,None]).sum(1)/2
        pairrows.append({'model_a':a,'model_b':b,'global_spearman':float(spearmanr(ma,mb).statistic),'global_kendall_tau':float(kendalltau(ma,mb).statistic),'top3_jaccard':len(ta&tb)/len(ta|tb),'per_commit_abs_rank_spearman_median':float(np.median(good)),'per_commit_rank_undefined':245-len(good),'median_normalized_absolute_profile_TV':float(np.median(tv)),'threshold_disagreement_count':int(np.sum((data[a]['probability'][0]>=.5)!=(data[b]['probability'][0]>=.5))),'interpretation':'Descriptive model agreement, not accuracy, causality or equal attribution magnitudes; six features only.'})
        for i,r in enumerate(index):localpair.append({'model_a':a,'model_b':b,'row_identifier':r['row_identifier'],'commit_identity':r['commit_identity'],'abs_rank_spearman':perrho[i],'normalized_absolute_profile_TV':float(tv[i])})
    for n,records in [('global_statistics',globalrows),('attributions_long',long),('commit_heterogeneity',commitrows),('rank_concordance',pairrows),('paired_commit_profiles',localpair)]:
        save(dest/(n+'.json'),records);table(dest/(n+'.csv'),records)
    local.sort(key=lambda r:(MODELS.index(r['model']),r['local_index']));save(dest/'local_cases.json',local)
    table(dest/'local_cases.csv',[{**{k:v for k,v in r.items() if k not in ['phi','feature_values']},**{f'phi_{f}':r['phi'][j] for j,f in enumerate(FEATURES)}} for r in local])
    save(dest/'heterogeneity_summary.json',hetero);save(dest/'integrity.json',{'models':integrity,'source_manifest_sha256':sha((SOURCE/'MANIFEST.json').read_bytes()),'all_source_hashes_verified':True,'source_manifest':manifest,'repetition_policy':'Use repetition 0 after verifying all 20 attribution arrays are exactly equal; n=245, never n=4900.','statistical_policy':'Population SD ddof=0; NumPy linear percentiles; exact zero and frozen +/-1e-12 zero band both reported; no p-values, bootstraps or generalization.'})
    fig=dest/'figure_data';fig.mkdir()
    save(fig/'global_importance.json',{'features':FEATURES,'models':{m:{'scale':SCALES[m],'values':means[m].tolist()} for m in MODELS}})
    save(fig/'attribution_distributions.json',{'features':FEATURES,'models':{m:{'scale':SCALES[m],'values':data[m]['phi'][0].tolist(),'row_identifiers':data[m]['row_identifier'].tolist()} for m in MODELS},'feature_values_available':False})
    save(fig/'rank_comparison.json',{'features':FEATURES,'models':{m:[int(sorted(range(6),key=lambda j:(-means[m][j],FEATURES[j])).index(j)+1) for j in range(6)] for m in MODELS}})
    for m in MODELS:save(fig/f'waterfalls_{m}.json',{'features':FEATURES,'model':m,'scale':SCALES[m],'cases':[r for r in local if r['model']==m]})
    return globalrows,local,hetero,pairrows,integrity
if __name__=='__main__':
    dest=Path(sys.argv[1]) if len(sys.argv)>1 else BASE/'tables'
    results=analyze(dest);print(json.dumps({'status':'PASS','global_rows':len(results[0]),'local_rows':len(results[1]),'rank_concordance':results[3],'heterogeneity':results[2]},indent=2))
