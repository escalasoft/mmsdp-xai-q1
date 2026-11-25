from pathlib import Path
import json,csv,hashlib,math,subprocess,sys,os
import numpy as np
O=Path(__file__).resolve().parent;R=O.parents[2];h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=json.loads((O/'provenance.json').read_text())
for r in p['source_files']:
 assert h(R/r['path'])==r['sha256']
 if 'manifest' in r:assert h(R/r['manifest'])==r['manifest_sha256']
checks=[]
for n in ['A','D']:
 d=json.loads((O/f'data/figure_{n}.json').read_text());e=d['E2']
 for mod in ['CODE','TEXT']:
  v=d[mod];assert len(v['phi'])==(6 if mod=='CODE' else 2557)
  assert np.isfinite(v['phi']).all() and abs(v['base']+math.fsum(v['phi'])-v['output'])<=1e-10
  assert v['probability']==float(e[mod+'_probability'])
  assert abs(1/(1+math.exp(-v['output']))-v['probability'])<=1e-12
 mods=['CODE','TEXT'] if n=='A' else ['CODE','PROCESS','TEXT']
 assert abs(float(e['phi0'])+math.fsum(float(e[m+'_phi']) for m in mods)-float(e['frozen_state_meta_logit']))<=1e-10
 assert d['identity']['local_index']==0 and d['family']=='LR'
 checks.append({'figure':n,'local_identity':'PASS','E1_reconstruction':'PASS','E2_stored_reconstruction':'PASS','probability_input_link':'EXACT'})
with (O/'tables/table_B_global_CODE.csv').open() as f:stats=list(csv.DictReader(f))
assert len(stats)==24
for fam in ['LR','RF','XGB','LGB']:
 with np.load(R/f'audits/q1-e1-code-execution/1.0.0/scientific/{fam}/explanations.npz',allow_pickle=False) as z:
  for col,feat in enumerate(z['features']):
   r=next(r for r in stats if r['model']==fam and r['feature']==feat)
   computed=math.fsum(abs(float(x)) for x in z['phi'][0,:,col])/245
   assert abs(computed-float(r['mean_absolute']))<=1e-14
localrows=[json.loads(l) for l in (R/'audits/q1-bounded-complementary-e1-xai/1.0.0/e1_local_explanations.jsonl').read_text().splitlines()]
d=json.loads((O/'data/figure_A.json').read_text());t=next(r for r in localrows if r['family']=='LR' and r['row_identifier']==d['identity']['row_identifier'])
for term in t['top_positive_features']+t['top_negative_features']:
 assert d['TEXT']['features'][term['column']]==term['token']
 assert d['TEXT']['phi'][term['column']]==term['attribution']
# Independent renderer process reads persisted plotting data, no source predictors.
v=O/'verification';v.mkdir(exist_ok=True)
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
subprocess.run([sys.executable,'-B',str(O/'plot.py'),str(v)],check=True,env=env)
for n in ['A','C','D']:assert h(v/f'figure_{n}.svg')==h(O/f'figures/figure_{n}.svg')
for ext in ['svg','png']:assert h(O/f'figures/figure_B.{ext}')==h(R/f'audits/q1-e1-code-scientific-synthesis/1.0.0/figures/global_importance.{ext}')
for r in p['source_files']:assert h(R/r['path'])==r['sha256']
out={'status':'PASS','independent_process':True,'source_references_unchanged':len(p['source_files']),'checks':checks,'global_mean_absolute_checks':24,'SVG_regeneration':'A/C/D byte-identical','figure_B':'SVG and PNG byte-identical to accepted source','TEXT_token_column_binding':'PASS','model_calls':0,'SHAP_calls':0,'calibration_calls':0,'T2_access':0}
(O/'independent_verification.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
