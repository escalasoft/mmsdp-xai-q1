from pathlib import Path
import hashlib,json,csv,gzip,shutil,sys
import numpy as np
R=Path(__file__).resolve().parents[3];O=Path(__file__).resolve().parent
C=R/'audits/q1-e1-code-execution/1.0.0/scientific';S=R/'audits/q1-e1-code-scientific-synthesis/1.0.0';T=R/'audits/q1-bounded-complementary-e1-xai/1.0.0';E=R/'audits/q1-e2-final-closure/1.1.0';A=R/'audits/q1-e1-e2-hierarchical-alignment/1.0.0'
for d in ['figures','tables','data']: (O/d).mkdir(exist_ok=True)
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();sources=[]
def get(b,n):
 m=b/('MANIFEST.json' if b==C else 'MANIFEST.sha256')
 hashes=json.loads(m.read_text()) if b==C else {x.split(maxsplit=1)[1].lstrip('*'):x.split()[0] for x in m.read_text().splitlines() if x.strip()}
 p=b/n;assert h(p)==hashes[n],str(p)
 sources.append({'path':str(p.relative_to(R)),'sha256':h(p),'manifest':str(m.relative_to(R)),'manifest_sha256':h(m)})
 return p
def js(b,n):return json.loads(get(b,n).read_text())
def jl(b,n):return [json.loads(x) for x in get(b,n).read_text().splitlines() if x.strip()]
def save(n,v):(O/n).write_text(json.dumps(v,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
def table(n,v):
 with (O/n).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(v[0]));w.writeheader();w.writerows(v)
# Verify the complete accepted alignment package and its referenced scientific inputs.
for l in (A/'MANIFEST.sha256').read_text().splitlines():
 digest,n=l.split(maxsplit=1);assert h(A/n)==digest
for r in js(A,'integrity.json'):
 assert h(R/r['path'])==r['sha256']
 if 'manifest' in r: assert h(R/r['manifest'])==r['manifest_sha256']
 sources.append(r)
ids=jl(C,'identities.jsonl');local=min((r for r in ids if r['local_index'] is not None),key=lambda r:r['local_index']);rid=local['row_identifier'];i=local['temporal_index']
fg=jl(T,'e1_t1_global_foreground_population.jsonl');j=next(i for i,r in enumerate(fg) if r['row_identifier']==rid)
localtext=next(r for r in jl(T,'e1_local_explanations.jsonl') if r['family']=='LR' and r['row_identifier']==rid)
vocab=js(T,'representations/train_verified_copy/vocabulary.json');names={v:k for k,v in vocab.items()}
with np.load(get(T,'lr_e1_attributions.npz'),allow_pickle=False) as z:
 t={'phi':z['values'][j].tolist(),'base':float(z['base']),'output':float(z['output'][j]),'residual':float(z['residual'][j]),'features':[names[k] for k in range(2557)]}
assert t['output']==localtext['model_output']
with np.load(get(C,'LR/explanations.npz'),allow_pickle=False) as z:
 c={'phi':z['phi'][0,i].tolist(),'base':float(z['base'][0,i]),'output':float(z['model_output'][0,i]),'residual':float(z['residual'][0,i]),'probability':float(z['probability'][0,i]),'features':z['features'].tolist()}
with gzip.open(get(E,'e2_attributions.csv.gz'),'rt') as f:
 fusion=[r for r in csv.DictReader(f) if r['project']=='apache/activemq' and r['model_family']=='Logistic Regression' and r['row_identifier']==rid and r['configuration'] in ['C+T','C+P+T']]
assert len(fusion)==2
matrix=js(A,'alignment_matrix.json')
for row in fusion:
 assert all(next(r for r in matrix if r['family']=='LR' and r['configuration']==row['configuration'] and r['modality']==mod)['probability_link']=='PASS' for mod in ['CODE','TEXT'])
 assert float(row['CODE_probability'])==c['probability']
 t['probability']=float(row['TEXT_probability'])
 data={'schema':'hierarchical-figure-data-1.0.0','identity':local,'family':'LR','configuration':row['configuration'],'CODE':c,'TEXT':t,'E2':row,'scope_status':'READY' if row['configuration']=='C+T' else 'PARTIAL','selection_policy':'selection_policy.json'}
 save('data/'+('figure_A' if row['configuration']=='C+T' else 'figure_D')+'.json',data)
# Copy existing global figure and its data byte-for-byte.
for ext in ['svg','png']:shutil.copyfile(get(S,'figures/global_importance.'+ext),O/'figures'/('figure_B.'+ext))
shutil.copyfile(get(S,'tables/figure_data/global_importance.json'),O/'data/figure_B.json')
shutil.copyfile(get(S,'tables/global_statistics.csv'),O/'tables/table_B_global_CODE.csv')
shutil.copyfile(get(S,'tables/rank_concordance.csv'),O/'tables/supplement_rank_concordance.csv')
shutil.copyfile(get(A,'local_coverage.csv'),O/'tables/supplement_local_overlap.csv')
# Manifest-check all CODE scientific payloads without model execution; summarize persisted diagnostics.
coverage=[]
tf=js(T,'e1_fidelity_results.json');ts=js(T,'e1_stability_results.json')
for fam in ['LR','RF','XGB','LGB']:
 meta=js(C,f'{fam}/metadata.json');g=js(C,f'{fam}/global.json')
 with np.load(get(C,f'{fam}/explanations.npz'),allow_pickle=False) as z:
  assert z['phi'].shape==(20,245,6) and np.isfinite(z['phi']).all()
  repeat=float(np.max(np.abs(z['phi']-z['phi'][0])));res=float(np.max(np.abs(z['residual'])))
  normalized=float(np.max(np.abs(z['residual'])/(1+np.abs(z['model_output']))))
 coverage.append(dict(modality='CODE',algorithm=fam,project='apache/activemq',partition='T1',commits=245,accepted_E1=245,method=meta['method'],scale=meta['scale'],fidelity='PASS',max_residual=res,normalized_residual=normalized,stability_repetitions=20,max_attribution_difference=repeat,E1_status='READY',E2='AVAILABLE in 3 configurations',cross_level='EXACT',limitation='Reconstructed pipeline; fixed population stability'))
 valid=fam!='RF'
 coverage.append(dict(modality='TEXT',algorithm=fam,project='apache/activemq',partition='T1',commits=245,accepted_E1=245 if valid else 0,method='ANALYTICAL_CENTERED_LOGIT' if fam=='LR' else 'EXACT_TREE_PATH_DEPENDENT',scale='LOGIT' if fam=='LR' else ('RAW_MARGIN' if valid else 'UNAVAILABLE'),fidelity=tf[fam]['status'],max_residual=tf[fam].get('max_residual'),normalized_residual=None,stability_repetitions=20 if valid else 0,max_attribution_difference=0 if valid else None,E1_status='READY' if valid else 'NO-GO',E2='AVAILABLE in 3 configurations',cross_level='EXACT' if valid else 'PREDICTOR_IDENTITY_ONLY',limitation='Reconstructed representation' if valid else 'Exact TreeSHAP additivity failed; no accepted attributions'))
 coverage.append(dict(modality='PROCESS',algorithm=fam,project='apache/activemq',partition='T1',commits=245,accepted_E1=0,method='NOT_EVALUATED',scale='NOT_APPLICABLE',fidelity='NOT_EVALUATED',max_residual=None,normalized_residual=None,stability_repetitions=0,max_attribution_difference=None,E1_status='NO-GO',E2='AVAILABLE in 3 configurations',cross_level='E2_ONLY',limitation='PROCESS_ANCESTRAL_UNPROVEN; not evidence of observed leakage'))
table('tables/table_A_coverage.csv',coverage);save('data/figure_C.json',coverage)
scopes=[]
for fam in ['LR','RF','XGB','LGB']:
 for config in ['C+P','C+T','P+T','C+P+T']:
  links=[r for r in matrix if r['family']==fam and r['configuration']==config];ok=[r for r in links if r['probability_link']=='PASS']
  scopes.append(dict(configuration=config,algorithm=fam,commits=245,verified_explanatory_links=len(ok),comparisons=245*len(ok),max_error=max([r['maximum_absolute_error'] for r in ok],default=None),status='READY' if config=='C+T' and fam!='RF' else 'PARTIAL',verification='SHA256 + row identity + shared FINAL_BASE + stored probability equality',limitation='; '.join((['PROCESS E1 unavailable'] if 'P' in config else [])+(['RF TEXT E1 unavailable'] if fam=='RF' and 'T' in config else []))))
table('tables/table_C_alignment.csv',scopes)
limits=[('Scope','ActiveMQ T1; 245 commits','No automatic generalization to 14 projects'),('PROCESS','Predictive and E2 modality; E1 not evaluated','Temporal provenance not independently established; no observed leakage demonstrated'),('RF TEXT','Predictor remains; no accepted E1','Exact TreeSHAP additivity failed'),('Calibration','16 aligned scopes have RAW state','No independently verified calibrated endpoint for these instances'),('Scales','E1 native scales; E2 meta-logit','No cross-level addition or magnitude equivalence'),('Stability','20 deterministic repetitions','Not perturbation robustness or human usefulness'),('Provenance','Reconstructed predictors and representations','Not original executable recovery'),('Local cases','Eight frozen E1 cases available in E2 foreground','Not the same E2 historical local set; not a representative sample')]
table('tables/table_D_limitations.csv',[dict(topic=a,evidence=b,boundary=c) for a,b,c in limits])
# Hash reports consumed as narrative sources.
for b,n in [(S,'REPORT.md'),(C.parent,'REPORT.md'),(T,'SPRINT56_3C_BOUNDED_COMPLEMENTARY_E1_XAI_REPORT.md'),(E,'E2_FINAL_CLOSURE_REPORT.md'),(A,'REPORT.md')]:get(b,n)
for r in sources:assert h(R/r['path'])==r['sha256']
save('provenance.json',{'source_files':sources,'python':sys.version,'numpy':np.__version__,'selection':local,'read_only_scientific_sources':True,'word_access':'Not opened or modified; package only','scope':'Persisted explanations only; no models, SHAP, calibration, extraction or T2'})
print(json.dumps({'selected_commit':local['commit_identity'],'row_identifier':rid,'local_index':local['local_index'],'tables':4,'sources':len(sources),'CODE':c,'TEXT_output':t['output'],'TEXT_base':t['base']}))
