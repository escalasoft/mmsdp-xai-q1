from pathlib import Path
import json,hashlib,csv
P=Path(__file__).resolve().parent;R=P.parents[2]
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
refs=json.loads((P/'integrity.json').read_text())
for x in refs:
 assert h(R/x['path'])==x['sha256']
 if 'manifest' in x:assert h(R/x['manifest'])==x['manifest_sha256']
a=json.loads((P/'alignment_matrix.json').read_text())
r=[json.loads(l) for l in (P/'row_level_comparisons.jsonl').read_text().splitlines()]
assert len(a)==24 and len(r)==5145 and all(x['within_tolerance'] for x in r)
assert all(x['absolute_error']==x['relative_error']==0 for x in r)
for x in a:
 sub=[v for v in r if (v['family'],v['configuration'],v['modality'])==(x['family'],x['configuration'],x['modality'])]
 assert len(sub)==x['rows']
 if sub:assert len({v['row_identifier'] for v in sub})==245 and sum(v['E1_local'] for v in sub)==8
ids=json.loads((P/'identity_crosswalk.json').read_text());assert len(ids)==245 and sum(v['local_index'] is not None for v in ids)==8
with (P/'local_coverage.csv').open() as f:c=list(csv.DictReader(f))
assert len(c)==16 and all(int(x['E1_local_in_E2_global'])==8 for x in c)
result={'status':'PASS','source_references_unchanged':len(refs),'matrix_links':24,'matched_links':21,'row_comparisons':5145,'maximum_absolute_error':0,'local_cases':8,'scope':'Independent process re-read of audit outputs, count/identity checks and source/manifest hashes; no new models or attribution calculations'}
(P/'independent_verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
