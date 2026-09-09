"""Packaging only. Standard-library parsing/hashing; no scientific execution."""
from pathlib import Path
import ast,csv,hashlib,io,json,re,subprocess,xml.etree.ElementTree as ET
ROOT=Path.cwd();P=ROOT/'audits/q1-bounded-complementary-e1-xai/1.0.0'
sha=lambda b:hashlib.sha256(b).hexdigest()
def dump(v):return (json.dumps(v,indent=2,sort_keys=True,ensure_ascii=True,allow_nan=False)+'\n').encode()
def load(p):return json.loads(p.read_text())
def snapshot():return {str(f.relative_to(P)):sha(f.read_bytes()) for f in sorted(P.rglob('*')) if f.is_file()}
def normalize(b):return b'\n'.join(line.rstrip(b' \t\r') for line in b.replace(b'\r\n',b'\n').split(b'\n')).rstrip(b'\n')+b'\n'
def manifests(base):
 entries={}
 for line in (base/'MANIFEST.sha256').read_text().splitlines():
  h,n=line.split('  ',1);assert '..' not in Path(n).parts and not Path(n).is_absolute() and n not in entries
  entries[n]=h
 return entries
before=snapshot();old_manifest=(P/'MANIFEST.sha256').read_bytes();expected=manifests(P)
mm=load(Path('/tmp/s56c_reconcile_analysis.json'));assert len(mm)==23
assert {r['path'] for r in mm}=={n for n,h in expected.items() if before[n]!=h}
for r in mm:
 n=r['path'];old=(Path('/tmp/s56c_packaging_preimages')/n).read_bytes();current=(P/n).read_bytes()
 assert sha(old)==r['expected'] and sha(current)==r['current']
 assert normalize(old)==normalize(current), n
 if n.endswith('.csv'):
  parse=lambda b:list(csv.reader(io.StringIO(b.decode(),newline='')))
  left,right=parse(old),parse(current);assert left==right
  r['semantic_verification']=dict(status='EXACT_PARSED_CELLS_ROWS_COLUMNS_ORDER',data_rows=len(right)-1,columns=len(right[0]),parsed_content_digest=sha(dump(right)))
 elif n.endswith('.jsonl'):
  parse=lambda b:[json.loads(line) for line in b.splitlines() if line.strip()]
  left,right=parse(old),parse(current);assert left==right
  r['semantic_verification']=dict(status='EXACT_PARSED_RECORDS_VALUES_IDENTITIES_ORDER',rows=len(right),parsed_content_digest=sha(dump(right)))
 elif n.endswith('.json'):
  left,right=json.loads(old),json.loads(current);assert left==right
  r['semantic_verification']=dict(status='EXACT_PARSED_TRANSFORM_VOCABULARY_IDF_FEATURE_ORDER',parsed_content_digest=sha(dump(right)))
 elif n.endswith('.svg'):
  a,b=ET.fromstring(old),ET.fromstring(current)
  def tree(e):
   attrs={k:(' '.join(v.split()) if k=='d' else v) for k,v in e.attrib.items()}
   return [e.tag,attrs,e.text if e.text and e.text.strip() else None,[tree(c) for c in e],e.tail if e.tail and e.tail.strip() else None]
  assert tree(a)==tree(b)
  r['semantic_verification']=dict(status='EXACT_XML_TREE_PATH_TOKENS_COORDINATES_TEXT_IDS_STYLES_AND_REFERENCES',elements=len(list(b.iter())),canonical_tree_digest=sha(dump(tree(b))),scientific_values_unchanged=True)
 elif n.endswith('.md'):
  r['semantic_verification']=dict(status='IDENTICAL_WORDS_NUMBERS_ORDER_AND_CLAIMS',difference='Two Markdown hard-break trailing-space markers removed; scientific text unchanged')
 else:
  a,b=ast.parse(old),ast.parse(current)
  # Only whitespace within the report literal differs; compare normalized string
  # constants and all remaining AST nodes, without executing any generation code.
  for t in [a,b]:
   for node in ast.walk(t):
    if isinstance(node,ast.Constant) and isinstance(node.value,str):node.value=normalize(node.value.encode()).decode()
  assert ast.dump(a)==ast.dump(b)
  r['semantic_verification']=dict(status='AST_EQUIVALENT_EXCEPT_REPORT_LITERAL_WHITESPACE',script_executed=False)
 assert r['classification']=='WHITESPACE_SERIALIZATION_ONLY'
# Check every persisted scientific binary against the original manifest; no decode.
binaries={n:h for n,h in expected.items() if Path(n).suffix in ['.npz','.bin','.f64','.u64','.png']}
assert all(before[n]==h for n,h in binaries.items())
# Explicit inherited protected-file maps: hash approved TRAIN/protocol/E2 files only.
parent=load(P/'parent_integrity_before.json');assert parent==load(P/'parent_integrity_after.json')
e2=load(P/'e2_parent_integrity_before.json');assert e2==load(P/'e2_parent_integrity_after.json')
for n,h in parent.items():
 assert n.startswith('audits/') and 'row_identity_provenance.jsonl.gz' not in n
 assert sha((ROOT/n).read_bytes())==h,n
assert all(sha((ROOT/n).read_bytes())==h for n,h in e2.items())
counters=load(P/'governance_counters.json')
assert counters['T1_LABEL_ACCESS_COUNT']==0 and all(v==0 for k,v in counters.items() if k.startswith('T2_'))
# Verify figure scientific identity and caption/source linkage before metadata edit.
fig_old=[json.loads(l) for l in (P/'e1_figure_registry.jsonl').read_text().splitlines() if l.strip()]
fig_new=json.loads(json.dumps(fig_old))
for r in fig_new:
 source=r['source_data_path'];assert expected[source]==r['source_data_digest']
 r['source_data_digest']=sha((P/source).read_bytes())
 for o in r['outputs']:
  assert expected[o['path']]==o['sha256'];o['sha256']=sha((P/o['path']).read_bytes())
 assert sha((ROOT/r['generation_script']).read_bytes())==r['generation_script_digest']
for a,b in zip(fig_old,fig_new):
 stripped=lambda r:{k:v for k,v in r.items() if k not in ['source_data_digest','outputs']}
 assert stripped(a)==stripped(b)
 assert [o['path'] for o in a['outputs']]==[o['path'] for o in b['outputs']]
# Resolve leaves -> nested manifest -> parent-referencing integrity metadata -> root.
(P/'packaging').mkdir(exist_ok=True)
(P/'packaging/pre_normalization_manifest.sha256.txt').write_bytes(old_manifest)
(P/'packaging/reconcile_packaging.py').write_bytes(Path(__file__).read_bytes())
(P/'e1_figure_registry.jsonl').write_bytes(b''.join((json.dumps(r,sort_keys=True)+'\n').encode() for r in fig_new))
child=P/'representations/train_verified_copy';child_old=sha((child/'MANIFEST.sha256').read_bytes());child_entries=manifests(child)
(child/'MANIFEST.sha256').write_text(''.join(f'{sha((child/n).read_bytes())}  {n}\n' for n in sorted(child_entries)))
child_new=sha((child/'MANIFEST.sha256').read_bytes())
# Preserve canonical scientific digests and representation identity. Their bytes
# describe the executed representation, not a new fitted or reconstructed state.
integrity=load(P/'text_train_representation_integrity.json')
assert integrity['manifest']==child_old
integrity['execution_manifest_sha256']=child_old
integrity['manifest']=child_new
integrity['packaging_serialization_note']='Scientific digests retain execution identity; current serialized-file hashes are in packaging/serialization_digest_registry.json. No scientific reconstruction.'
(P/'text_train_representation_integrity.json').write_bytes(dump(integrity))
registry=dict(schema='56.3C_PACKAGING_SERIALIZATION_DIGEST_MAP',scientific_identity_policy='Retain all original representation/model/vectorizer/feature-order digests as execution identities; resolve current file bytes using this packaging map.',files=[dict(path=r['path'],execution_sha256=r['expected'],packaged_sha256=r['current'],classification=r['classification']) for r in mm],scientific_identity_reference_files_preserved=['representations/train_verified_copy/digests.json','t1_text_representation_registry.json','t1_text_representation_repeatability.json','e1_model_representation_alignment.jsonl','e1_to_e2_traceability.jsonl','bounded_repair_attempt.json'])
(P/'packaging/serialization_digest_registry.json').write_bytes(dump(registry))
refreshed=['e1_figure_registry.jsonl','representations/train_verified_copy/MANIFEST.sha256','text_train_representation_integrity.json','manifest_verification.json','MANIFEST.sha256']
record=dict(verdict='PACKAGING_MANIFEST_RECONCILIATION_PASS',scope='Closed Sprint 56.3C packaging only',original_mismatch_count=23,original_mismatches=mm,files_normalized=[r['path'] for r in mm],classification_counts=dict(WHITESPACE_SERIALIZATION_ONLY=23,SCIENTIFIC_CONTENT_CHANGED=0,OTHER_PACKAGING_CHANGE=0),metadata_files_refreshed=refreshed,before_manifest_sha256=sha(old_manifest),before_actual_package_file_map_sha256=sha(dump(before)),scientific_equivalence='PASS_ALL_23_ORIGINAL_HASH_PREIMAGES_AND_PARSED_CONTENT_EQUIVALENT',unchanged_scientific_binary_count=len(binaries),unchanged_scientific_binaries=binaries,parent_files_verified=len(parent),E2_files_verified=len(e2),parent_unchanged=True,E2_unchanged=True,scientific_counters_unchanged=True,new_operations=dict(model_loads=0,model_queries=0,SHAP=0,analytical_attributions=0,representation_reconstruction=0,T1_labels=0,T2_access=0,retraining=0,refit=0,recalibration=0,tuning=0,E2_recomputation=0,E2_mutation=0,population_reselection=0,figure_regeneration=0,table_recomputation=0,source_recovery=0),dependency_order=['figure serialized-file references','nested TRAIN copy manifest','integrity record linking nested manifest','packaging records','root MANIFEST.sha256','detached final verification receipt'],final_receipt='../packaging_closure_receipt.json',receipt_explanation='Detached receipt hashes the final manifest without creating a self-referential digest cycle.')
(P/'packaging/reconciliation.json').write_bytes(dump(record))
(P/'manifest_verification.json').write_bytes(dump(dict(status='PASS',algorithm='SHA256',scope='Every file in 1.0.0 except root MANIFEST.sha256; nested manifest included',packaging_reconciliation='packaging/reconciliation.json',scientific_equivalence='PASS',original_mismatches=23,final_mismatches=0,parent_E2_unchanged=True,final_command='shasum -a 256 -c MANIFEST.sha256',detached_final_receipt='../packaging_closure_receipt.json')))
actual=snapshot();actual.pop('MANIFEST.sha256')
(P/'MANIFEST.sha256').write_text(''.join(f'{h}  {n}\n' for n,h in sorted(actual.items())))
# From-scratch verification after all covered metadata is finalized.
results={}
for name,cmd,cwd in [('root_manifest',['shasum','-a','256','-c','MANIFEST.sha256'],P),('nested_manifest',['shasum','-a','256','-c','MANIFEST.sha256'],child),('git_diff_check',['git','diff','--check'],ROOT),('git_cached_diff_check',['git','diff','--cached','--check'],ROOT)]:
 r=subprocess.run(cmd,cwd=cwd,capture_output=True,text=True);assert r.returncode==0,(name,r.stdout,r.stderr)
 results[name]=dict(command=' '.join(cmd),exit_code=r.returncode,OK_lines=sum(l.endswith(': OK') for l in r.stdout.splitlines()),stdout_sha256=sha(r.stdout.encode()),stderr=r.stderr)
assert all(sha((ROOT/n).read_bytes())==h for n,h in parent.items())
assert sha((P/'governance_counters.json').read_bytes())==before['governance_counters.json']
after=snapshot();changes={n:dict(before=before.get(n),after=h) for n,h in after.items() if before.get(n)!=h}
assert all(n in refreshed or n.startswith('packaging/') for n in changes)
receipt=dict(verdict='PACKAGING_MANIFEST_RECONCILIATION_PASS',package='1.0.0',before_manifest_sha256=sha(old_manifest),after_manifest_sha256=after['MANIFEST.sha256'],after_package_file_map_sha256=sha(dump(after)),final_manifest_entry_count=len(actual),original_mismatches=23,final_mismatches=0,checks=results,files_written=changes,scientific_content_unchanged=True,parents_unchanged=True,E2_unchanged=True,T1_labels=0,T2_all_counters=0,scientific_recomputation=0,git_commit_push_PR=False)
(P.parent/'packaging_closure_receipt.json').write_bytes(dump(receipt))
print(json.dumps({k:receipt[k] for k in ['verdict','before_manifest_sha256','after_manifest_sha256','final_manifest_entry_count','original_mismatches','final_mismatches']},indent=2))
