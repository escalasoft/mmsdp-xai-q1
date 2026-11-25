"""Read-only source audit: no model imports, inference, calibration or explanation execution."""
from pathlib import Path
import json, csv, gzip, hashlib, io, sys
import numpy as np
from scipy.special import expit
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
C=ROOT/'audits/q1-e1-code-execution/1.0.0/scientific'
T=ROOT/'audits/q1-bounded-complementary-e1-xai/1.0.0'
E=ROOT/'audits/q1-e2-final-closure/1.1.0'
J=ROOT/'audits/q1-xai-reconstruction-execution/1.0.0'
integrity=[]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def checked(base,name):
 m=base/('MANIFEST.json' if base==C else 'MANIFEST.sha256')
 if m.suffix=='.json': manifest=json.loads(m.read_text())
 else: manifest={line.split(maxsplit=1)[1].lstrip('*'):line.split()[0] for line in m.read_text().splitlines() if line.strip()}
 p=base/name; h=sha(p)
 assert h==manifest[name], str(p)+' hash mismatch'
 integrity.append({'path':str(p.relative_to(ROOT)),'sha256':h,'manifest':str(m.relative_to(ROOT)),'manifest_sha256':sha(m),'status':'PASS'})
 return p
def js(base,name): return json.loads(checked(base,name).read_text())
def jl(base,name): return [json.loads(x) for x in checked(base,name).read_text().splitlines() if x.strip()]
def write(name,obj): (OUT/name).write_text(json.dumps(obj,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
def table(name,rows):
 with (OUT/name).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
ids=jl(C,'identities.jsonl'); fg=jl(T,'e1_t1_global_foreground_population.jsonl'); local=jl(T,'e1_local_case_population.jsonl')
ci={r['row_identifier']:r for r in ids}; ti={r['row_identifier']:r for r in fg}; locals_={r['row_identifier'] for r in local}
assert len(ci)==len(ti)==245 and ci.keys()==ti.keys() and len(locals_)==8
assert locals_=={r['row_identifier'] for r in ids if r['local_index'] is not None}
for rid in ci:
 assert ci[rid]['commit_identity']==ti[rid]['commit_identity'] and ci[rid]['partition']==ti[rid]['partition']=='T1'
 assert ci[rid]['project']==ti[rid]['project']=='apache/activemq'
 assert fg[ci[rid]['foreground_index']]['row_identifier']==rid
assert [r['order_key'] for r in ids]==sorted(r['order_key'] for r in ids)
alignment={r['family']:r for r in jl(T,'e1_model_representation_alignment.jsonl')}
fail=js(T,'family_execution_failures.json'); continuity=js(T,'e1_e2_continuity_contract.json')
js(C,'status.json'); js(E,'e2_t2_non_access_report.json')
provenance=js(E,'scope_input_provenance.json')
journal=jl(J,'repetitions/rep_01/component_journal.jsonl')
journal={r['logical_id']:r for r in journal if 'logical_id' in r}
with gzip.open(checked(E,'e2_attributions.csv.gz'),'rt') as f: erows=list(csv.DictReader(f))
assert all(r['partition']=='T1' for r in erows)
erows=[r for r in erows if r['project']=='apache/activemq']
with checked(E,'e2_local_cases.csv').open() as f: elocal=[r for r in csv.DictReader(f) if r['project']=='apache/activemq']
families={'LR':'Logistic Regression','RF':'Random Forest','XGB':'XGBoost','LGB':'LightGBM'}
code={};text={};meta={}
for fam in families:
 meta[fam]=js(C,f'{fam}/metadata.json')
 with np.load(checked(C,f'{fam}/explanations.npz'),allow_pickle=False) as z:
  assert z['phi'].shape==(20,245,6) and list(z['features'])==['la','ld','nf','nd','ns','ent']
  assert list(z['row_identifier'])==[r['row_identifier'] for r in ids]
  assert list(z['commit_identity'])==[r['commit_identity'] for r in ids]
  assert str(z['model_identity'])==meta[fam]['model_identity']
  code[fam]=dict(zip(z['row_identifier'],z['probability'][0].tolist()))
 if fam!='RF':
  filename='lr_e1_attributions.npz' if fam=='LR' else f'{fam.lower()}_e1_shap_values.npz'
  with np.load(checked(T,filename),allow_pickle=False) as z:
   assert z['values'].shape==(245,2557) and np.isfinite(z['values']).all()
   # Arithmetic conversion of saved native outputs, preserving stored dtype; no predictor/calibrator.
   text[fam]=dict(zip([r['row_identifier'] for r in fg],expit(z['output']).astype(np.float64).tolist()))
policy_path=ROOT/'audits/q1-xai-reconstruction-equivalence-protocol/1.0.0/numerical_tolerance_policy.json'
policy=json.loads(policy_path.read_text());tol=policy['row_level_probability_equivalence']
integrity.append({'path':str(policy_path.relative_to(ROOT)),'sha256':sha(policy_path),'status':'RECORDED_CURRENT_DOCUMENT'})
rows=[]; details=[]; coverage=[]
for scope in provenance:
 if scope['project']!='apache/activemq':continue
 fam=next(k for k,v in families.items() if v==scope['model_family']); cfg=scope['configuration']; mid=scope['model_identity_sha256']
 subset=[r for r in erows if r['model_identity_sha256']==mid]
 assert len(subset)==245 and {r['row_identifier'] for r in subset}==ci.keys()
 assert all(r['configuration']==cfg and r['model_family']==families[fam] for r in subset)
 localset={r['row_identifier'] for r in elocal if r['model_identity_sha256']==mid}
 assert len(localset)==8 and localset<=ci.keys()
 coverage.append({'family':fam,'configuration':cfg,'fusion_identity':mid,'foreground':245,'E1_local_in_E2_global':len(locals_ & ci.keys()),'E2_frozen_local':8,'local_local_intersection':len(localset & locals_),'shared_local_ids':';'.join(sorted(localset & locals_))})
 for mod,letter in [('CODE','C'),('TEXT','T')]:
  if letter not in scope['modality_order']:continue
  rec=journal[f'apache/activemq|{families[fam]}|FINAL_BASE|{letter}']
  digest=meta[fam]['pipeline_sha256'] if mod=='CODE' else alignment[fam]['model_digest']
  standalone=meta[fam]['model_identity'] if mod=='CODE' else alignment[fam]['model_identity']
  consumers=rec['canonical_state']['provenance']['consuming_model_identity_sha256']
  assert digest==rec['executable']['sha256'] and mid in consumers and standalone in consumers
  values=code[fam] if mod=='CODE' else text.get(fam)
  diffs=[]; rels=[]; bad=0; exact=0; decisions=0
  if values is not None:
   for r in subset:
    rid=r['row_identifier'];p=values[rid];q=float(r[mod+'_probability']); d=abs(p-q);rel=d/abs(q) if abs(q)>=1e-8 else None
    ok=np.isfinite(p) and d<=tol['maximum_absolute_error'] and (rel is None or rel<=tol['maximum_relative_error'])
    bad+=not ok;exact+=p==q;decisions+=((p>=.5)!=(q>=.5));diffs.append(d)
    if rel is not None:rels.append(rel)
    details.append({'family':fam,'configuration':cfg,'modality':mod,'fusion_identity':mid,'row_identifier':rid,'commit_identity':ci[rid]['commit_identity'],'absolute_error':d,'relative_error':rel,'within_tolerance':bool(ok),'E1_local':rid in locals_})
  rows.append({'family':fam,'configuration':cfg,'modality':mod,'fusion_identity':mid,'unimodal_identity':standalone,'pipeline_sha256':digest,'identity_chain':'PASS','rows':245 if values else 0,'exact':exact,'maximum_absolute_error':max(diffs) if diffs else None,'maximum_relative_error':max(rels) if rels else None,'outside_tolerance':bad if values else None,'decision_disagreements':decisions if values else None,'probability_link':'PASS' if values and not bad else ('FAIL_PERSISTED_OUTPUT_CONVERSION' if values else 'UNAVAILABLE_RF_TEXT_ATTRIBUTIONS'),'conversion':'NONE_PERSISTED_PROBABILITY' if mod=='CODE' else 'SIGMOID_PERSISTED_NATIVE_OUTPUT_NATIVE_DTYPE'})
assert len(coverage)==16 and len(rows)==24

F=ROOT/'audits/q1-e2-t1-foreground-freeze/1.0.0'
ef=[r for r in jl(F,'t1_global_foreground_population.jsonl') if r['project']=='apache/activemq']
el=jl(F,'t1_local_case_population.jsonl')
assert len(ef)==245 and {r['row_identifier'] for r in ef}==ci.keys()
for scope in coverage:
 sub=[r for r in erows if r['model_identity_sha256']==scope['fusion_identity']]
 assert [r['row_identifier'] for r in sorted(sub,key=lambda r:int(r['foreground_ordinal']))]==[r['row_identifier'] for r in sorted(ef,key=lambda r:r['ordinal'])]
 frozen={r['row_identifier'] for r in el if r['model_identity_sha256']==scope['fusion_identity']}
 actual={r['row_identifier'] for r in elocal if r['model_identity_sha256']==scope['fusion_identity']}
 assert frozen==actual
G=ROOT/'audits/q1-xai-reconstruction-equivalence-g4/1.0.0'
g4=jl(G,'g4_scope_results.jsonl')
cal=[]
for scope in coverage:
 r=next(r for r in g4 if r['model_identity_sha256']==scope['fusion_identity'])
 cal.append({'family':scope['family'],'configuration':scope['configuration'],'fusion_identity':scope['fusion_identity'],'historical_calibration_state':r['calibration_state_recorded_for_future_G5_mapping'],'G4_status':r['G4_outcome'],'E2_explained_endpoint':'PRE_CALIBRATION_META_LOGIT','E2_probability':'RAW_SIGMOID_META_LOGIT','calibrated_values_verified_here':False})
table('calibration_boundary.csv',cal)
implementation=js(T,'implementation_provenance.json')
write('text_order_binding.json',{'producer_provenance':implementation,'binding':'Static producer lines 911-918: fg ledger -> row_index into T1 representation -> ordered output; NPZ has no embedded IDs. CODE foreground_index independently matches this ledger. No representation loaded.'})
report=ROOT/'audits/q1-e1-process-temporal-recoverability/2026-10-12/REPORT.md'
integrity.append({'path':str(report.relative_to(ROOT)),'sha256':sha(report),'status':'RECORDED_CURRENT_DOCUMENT'})

write('integrity.json',integrity);table('alignment_matrix.csv',rows);write('alignment_matrix.json',rows);table('local_coverage.csv',coverage)
with (OUT/'row_level_comparisons.jsonl').open('w') as f:
 for row in details:f.write(json.dumps(row,allow_nan=False)+'\n')
write('identity_crosswalk.json',ids)
write('summary.json',{'schema':'e1-e2-alignment-1.0.0','scope':'apache/activemq T1','population':245,'local_cases':8,'scopes':16,'modality_scope_links':24,'CODE_links':12,'TEXT_links':12,'TEXT_RF':fail,'source_manifests_full_walk':False,'integrity_scope':'Only allowlisted consumed artifacts; no mixed sources or model payloads opened','local_intersections':coverage,'probability_comparisons':rows,'numpy':np.__version__,'python':sys.version,'non_execution':'No model, SHAP, calibration, extraction or integrated figure execution'})
for r in integrity: assert sha(ROOT/r['path'])==r['sha256']
print(json.dumps({'verified_files':len(integrity),'links':len(rows),'probability_PASS':sum(r['probability_link']=='PASS' for r in rows),'calibration_states':cal},indent=2))
