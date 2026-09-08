"""Sprint 56.2A: metadata source audit before conditional safe materialization.

The current audit has no accepted source. Unknown safety fails closed. Neither
mixed-data indexing nor read-and-drop is implemented. Earlier evidence/code is
never changed. Fixture materialization validates exact schema/identity/value
provenance and requires a completed Phase-A acceptance record.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.metadata
import json
import math
import os
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'audits/q1-primary-xai-safe-population-source/1.0.0'
PARENT=ROOT/'audits/q1-primary-xai-population-freeze/1.0.0'
SMOKE=ROOT/'audits/q1-primary-xai-runtime-smoke/1.0.0'
STORE=ROOT/'audits/q1-xai-reconstruction-execution/1.0.0'
FREEZE=ROOT/'audits/q1-apachejit-final-dataset-freeze/1.0.0'
ACQ=ROOT/'audits/q1-apachejit-v2-scientific-suitability/1.0.0'
BRANCH='sprint-10/q1-primary-xai-execution'
SEARCH_ROOTS=['audits','data','artifacts','outputs','experiments','configs','src','tests']
C=['la','ld','nf','nd','ns','ent']
P=['ndev','age','nuc','aexp','arexp','asexp']
TRAIN_FIELDS=['project','partition','row_identifier','class','order_key',*C,*P]
T1_FIELDS=['project','partition','row_identifier','order_key']
FAILURES=['SAFE_SOURCE_FOUND_AND_MATERIALIZED','SAFE_SOURCE_FOUND_MATERIALIZATION_FAILED','NO_SAFE_SOURCE_FOUND',
    'T2_TRAVERSAL_REQUIRED','TRAIN_PROVENANCE_MISMATCH','T1_IDENTITY_PROVENANCE_MISMATCH','TRAIN_FEATURE_SCHEMA_MISMATCH',
    'TRAIN_MEMBERSHIP_DIGEST_MISMATCH','T1_MEMBERSHIP_DIGEST_MISMATCH','DIGEST_RECONCILIATION_SPECIFICATION_INCOMPLETE',
    'SOURCE_SEMANTICS_INSUFFICIENT','MATERIALIZATION_NONDETERMINISTIC','PARENT_ARTIFACT_INTEGRITY_FAILURE']
COUNTER_NAMES=[f'{p}_{name}' for p in ['TRAIN','T1'] for name in ['SAFE_SOURCE_ACCESS_COUNT','IDENTITY_ROW_READ_COUNT',
    'MODEL_QUERY_COUNT','XAI_ATTRIBUTION_EXECUTION_COUNT']]+['TRAIN_LABEL_ROW_READ_COUNT','TRAIN_FEATURE_ROW_READ_COUNT',
    'T1_LABEL_READ_COUNT','T1_FEATURE_READ_COUNT']+[f'T2_{x}_COUNT' for x in ['ACCESS','IDENTITY_READ','FEATURE_READ','LABEL_READ','MODEL_QUERY','XAI_EXECUTION']]+[
    'scientific_SHAP_execution_count','scientific_analytical_attribution_execution_count','predictive_metric_count',
    'retraining_count','refit_count','reconstruction_count','recalibration_count','figure_generation_count','commit_count','push_count']
READ_EVENTS=set()


class SafeSourceError(RuntimeError):
    pass


def canonical(value):
    return (json.dumps(value,sort_keys=True,ensure_ascii=True,separators=(',', ':'),allow_nan=False)+'\n').encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def lines(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def save(name,value):
    (OUT/name).write_bytes(canonical(value))


def save_lines(name,records):
    (OUT/name).write_bytes(b''.join(canonical(r) for r in records))


def git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()


def forbidden_payload(path):
    p=Path(path).resolve()
    if p.is_relative_to(STORE/'objects'):
        return False  # Explicit read-only object integrity hashing is permitted.
    rel=p.relative_to(ROOT).as_posix() if p.is_relative_to(ROOT) else p.name
    lower=rel.lower()
    if p.is_relative_to(FREEZE) and p.suffix=='.gz':
        return True
    # No unknown physical source is considered safe based on its filename.
    if p.is_relative_to(ROOT/'data') or p.is_relative_to(ROOT/'artifacts'):
        return p.suffix not in ['.py','.md']
    if p.is_relative_to(ROOT/'outputs') and p.suffix in ['.json','.jsonl','.gz','.csv']:
        return True
    if re.search(r'(^|[/_.-])t2([/_.-]|$)',lower):
        return p.name!='t2_reviewer_reserve_policy.json'  # Known zero-counter policy, not T2 data.
    if 'prediction' in p.name.lower() and p.suffix in ['.gz','.csv','.jsonl']:
        return True
    if p.suffix=='.gz' and not p.is_relative_to(OUT):
        return True
    return False


def guard(event,args):
    if event!='open' or not isinstance(args[0],(str,bytes,os.PathLike)):
        return
    p=Path(os.fsdecode(args[0])).resolve()
    mode,flags=args[1] or '',args[2] or 0
    writing=any(c in mode for c in 'wax+') or bool(flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC))
    if forbidden_payload(p):
        raise PermissionError('S56.2A prohibited or unproved-safe scientific payload: '+str(p))
    if p.is_relative_to(ROOT):
        if writing and (p.is_relative_to(ROOT/'audits') and not p.is_relative_to(OUT)
                        or p.is_relative_to(ROOT/'data') or p.is_relative_to(ROOT/'artifacts')
                        or p.is_relative_to(ROOT/'.venv') or p.is_relative_to(ROOT/'.venv-xai-s56')
                        or p==ROOT/'.gitignore'):
            raise PermissionError('S56.2A protected write denied: '+str(p))
        if not writing and not p.is_relative_to(OUT):
            READ_EVENTS.add(p.relative_to(ROOT).as_posix())


def stat_record(path):
    st=path.stat()
    return {'size_bytes':st.st_size,'mtime_ns':st.st_mtime_ns,'inode':st.st_ino}


def inventory():
    return {'python':sys.version.split()[0],'packages':sorted(
        [{'name':d.metadata['Name'],'version':d.version} for d in importlib.metadata.distributions()],
        key=lambda r:r['name'].lower())}


def declared_hashes():
    result={}
    # Manifests are metadata. Never resolve their payload entries here.
    for p in (ROOT/'audits').rglob('MANIFEST.sha256'):
        if p.is_relative_to(OUT):
            continue
        for line in p.read_text().splitlines():
            if '  ' not in line:
                continue
            h,name=line.split('  ',1)
            if re.fullmatch('[0-9a-f]{64}',h):
                target=(p.parent/name).resolve()
                if target.is_relative_to(ROOT):
                    result[target.relative_to(ROOT).as_posix()]={'sha256':h,'manifest':p.relative_to(ROOT).as_posix()}
    arc=read(ACQ/'apachejit_archive_provenance.json')
    for item in arc['extracted_file_inventory']:
        name='data/external/apachejit-v2/extracted/apachejit/'+item['path']
        result[name]={'sha256':item['sha256'],'manifest':str((ACQ/'apachejit_archive_provenance.json').relative_to(ROOT))}
    result['data/external/apachejit-v2/apachejit_dataset_replication.zip']={
        'sha256':arc['sha256'],'manifest':str((ACQ/'apachejit_archive_provenance.json').relative_to(ROOT))}
    return result


def protected_snapshot(declared):
    namespaces=['q1-t1-confirmatory-execution','q1-xai-reconstruction-equivalence-protocol',
        'q1-xai-reconstruction-execution','q1-xai-reconstruction-equivalence-g4',
        'q1-xai-final-output-equivalence-g5','q1-xai-runtime-freeze',
        'q1-primary-xai-runtime-smoke','q1-primary-xai-population-freeze']
    records={}
    for namespace in namespaces:
        for p in sorted((ROOT/'audits'/namespace).rglob('*')):
            if not p.is_file():
                continue
            name=p.relative_to(ROOT).as_posix()
            st=stat_record(p)
            if forbidden_payload(p):
                records[name]={**st,'declared_sha256':declared.get(name,{}).get('sha256'),
                    'sha256_observation':'INHERITED_NOT_REHASHED_PAYLOAD_ACCESS_FORBIDDEN',
                    'git_blob_id':git('ls-files','-s','--',name).split()[1] if git('ls-files','--',name) else None}
            else:
                actual=sha(p)
                if name in declared and actual!=declared[name]['sha256']:
                    raise SafeSourceError('PARENT_ARTIFACT_INTEGRITY_FAILURE: '+name)
                records[name]={**st,'sha256':actual,'sha256_observation':'FRESH_READ_ONLY_SHA256'}
    for name in ['.gitignore','pyproject.toml','.venv/pyvenv.cfg','.venv-xai-s56/pyvenv.cfg']:
        p=ROOT/name
        records[name]={**stat_record(p),'sha256':sha(p),'sha256_observation':'FRESH_READ_ONLY_SHA256'}
    objects=[r for name,r in records.items() if name.startswith(str((STORE/'objects').relative_to(ROOT))+'/')]
    if len(objects)!=5649 or sum(r['size_bytes'] for r in objects)!=2139594110:
        raise SafeSourceError('PARENT_ARTIFACT_INTEGRITY_FAILURE: object count/size')
    registry=lines(STORE/'external_artifact_registry/external_artifact_inventory.jsonl')
    if {r['relative_path'] for r in registry}!={p.relative_to(STORE).as_posix() for p in (STORE/'objects').rglob('*') if p.is_file()}:
        raise SafeSourceError('PARENT_ARTIFACT_INTEGRITY_FAILURE: missing/orphan objects')
    return {'files':records,'records_sha256':digest(records),'object_count':5649,'object_bytes':2139594110,
        'missing_references':0,'orphan_objects':0,'predictive_inventory':inventory(),
        'fresh_sha256_count':sum('sha256' in r for r in records.values()),
        'payload_not_rehashed_count':sum('sha256' not in r for r in records.values()),
        'limitation':'Forbidden T1 labelled/prediction payloads and T2-bearing files are not opened even for hashing. Their inherited manifest SHA256, git blob and filesystem metadata are preserved separately, not represented as fresh byte verification.'}


def discover():
    command=['rg','--files','--hidden','--no-ignore',*SEARCH_ROOTS,'-g','!**/.git/**','-g','!**/__pycache__/**','-g','!**/objects/**']
    result=subprocess.run(command,cwd=ROOT,text=True,capture_output=True)
    if result.returncode not in [0,1,2]:
        raise SafeSourceError('Source inventory failed')
    paths=sorted(p for p in result.stdout.splitlines() if not p.startswith(str(OUT.relative_to(ROOT))+'/'))
    roots=[{'path':name,'exists':(ROOT/name).exists(),'listed_files':sum(p.startswith(name+'/') for p in paths)} for name in SEARCH_ROOTS]
    indices=[p for p in paths if Path(p).suffix.lower() in ['.gzi','.zran','.idx','.sqlite','.sqlite3','.db','.parquet','.arrow','.feather']
             and '.git/' not in p]
    history=git('log','--all','--format=COMMIT %H %s','--name-only','--','audits','data','artifacts','outputs','experiments')
    names=sorted({p for p in history.splitlines() if p and not p.startswith('COMMIT ')})
    history_candidates=[p for p in names if re.search(r'train\.json|t1.*identit|row_identity|offset|row.index|\.gzi$|\.parquet$|\.sqlite$',p,re.I)]
    trees={commit:git('ls-tree','-r','--long',commit,'--',prefix,'data','outputs') for commit,prefix in [
        ('c01ccaaf0594ab2131bd1820361517be2740e4f9','audits/q1-apachejit-final-dataset-freeze'),
        ('355d6ca44a8b5ae7861f923bbda46d54a131b1f8','audits/q1-apachejit-v2-scientific-suitability')]}
    return paths,{'roots':roots,'command':command,'stderr':result.stderr,'inventory_sha256':digest(paths),
        'existing_random_access_candidates':indices,'git_history_metadata_sha256':hashlib.sha256(history.encode()).hexdigest(),
        'historical_candidate_paths':history_candidates,'historical_trees':trees,
        'historical_payloads_opened':False,'Git_internal_objects_excluded':'pack indexes address repository object IDs, not the frozen scientific population rows; no frozen row-id map identified'}


def candidate_paths(paths,search):
    selected=set()
    for p in paths:
        if p.startswith('data/external/apachejit-v2/extracted/apachejit/') and Path(p).suffix in ['.csv','.ipynb']:
            selected.add(p)
        if p=='data/external/apachejit-v2/apachejit_dataset_replication.zip':
            selected.add(p)
        if p.startswith('artifacts/') and Path(p).suffix in ['.json','.jsonl']:
            selected.add(p)
        if p.startswith('outputs/adapters/') or p.startswith('data/processed/jit_defects4j/'):
            selected.add(p)
        if p.startswith('audits/') and (p.endswith('temporal_partition_manifest.jsonl.gz') or
            p.endswith('row_identity_provenance.jsonl.gz') or p.endswith(('_dataset.jsonl.gz','t1_identity_integrity.json')) or
            p.endswith('selected_train_rows.json') or p.endswith('train_only_population_manifest.json') or
            'membership' in Path(p).name or p.endswith(('train_reference_population.jsonl','t1_global_foreground_population.jsonl','t1_local_case_population.jsonl')) or
            p.endswith('t1_prediction_evidence.jsonl.gz')):
            selected.add(p)
    selected.update(search['existing_random_access_candidates'])
    selected.update(p for p in search['historical_candidate_paths'] if (ROOT/p).is_file())
    # Directory-level content-addressed alternatives, evaluated without reading commits.
    repo=ROOT/'data/external/apachejit-v2/repositories'
    selected.update(p.relative_to(ROOT).as_posix() for p in repo.iterdir() if p.is_dir() and p.name.endswith('.git'))
    return sorted(selected)


def classify_candidate(name,declared,tracked,ignored):
    p=ROOT/name
    isdir=p.is_dir()
    h=declared.get(name,{})
    r={'candidate_id':hashlib.sha256(name.encode()).hexdigest(),'path':name,
       'file_type':'GIT_OBJECT_DATABASE_DIRECTORY' if isdir else ''.join(p.suffixes) or 'FILE',
       'git_tracking_status':'TRACKED' if name in tracked else 'IGNORED' if name in ignored else 'UNTRACKED',
       'source_provenance':h.get('manifest','STATIC_PRODUCER_OR_PARENT_METADATA_REFERENCES'),
       'partition_semantics':'UNPROVEN_FOR_FROZEN_CAMPAIGN','row_level_addressability':'NOT_VERIFIED',
       'opening_necessarily_exposes_T2':'UNKNOWN_FAIL_CLOSED','TRAIN_without_T2_access':False,
       'T1_identity_without_T2_access':False,'TRAIN_class_available':'UNKNOWN',
       'CODE_values_available':'UNKNOWN','PROCESS_values_available':'UNKNOWN','T1_labels_avoidable_at_read_time':False,
       'row_order_semantics':'NOT_RECONCILED','project_coverage':'NOT_VERIFIED_FOR_ALL_14',
       'membership_reconciliation_capability':'NO_COMPLETE_SAFE_CAMPAIGN_ROWS',
       'source_hash':h.get('sha256'),'source_hash_basis':'INHERITED_FROZEN_MANIFEST_NOT_PAYLOAD_REHASHED' if h else 'UNAVAILABLE_NOT_INVENTED',
       'source_size_metadata':stat_record(p),'payload_opened_for_source_inspection':False,
       'verdict':'PROVENANCE_INSUFFICIENT','reason':'No provenance proving complete T2-free direct access; no row payload inspected.'}
    if isdir:
        r.update(verdict='INCOMPLETE_SOURCE',source_provenance='Frozen repository acquisition/assignment producer in apachejit_final_dataset_freeze.py',
            row_level_addressability='DIRECT_GIT_COMMIT_BY_KNOWN_SHA_ONLY_NOT_FROZEN_ROW_ID',
            reason='Git objects are addressable by commit SHA, but complete TRAIN/T1 row-id-to-SHA membership map is not available without mixed-stream access. Git does not provide benchmark SZZ classes or exact frozen Kamei PROCESS values; replacements are not authorized.')
    elif name.startswith(str(FREEZE.relative_to(ROOT))+'/') and p.suffix=='.gz':
        r.update(verdict='T2_TRAVERSAL_REQUIRED',partition_semantics='FROZEN_TRAIN_VALIDATION_T1_T2_PER_PROJECT',
            opening_necessarily_exposes_T2='COMPLETE_14_PROJECT_ACCESS_REQUIRES_T2_TRAVERSAL',
            row_level_addressability='SINGLE_GZIP_STREAM_NO_PREEXISTING_INDEX',
            row_order_semantics='project ASC then raw UTC timestamp and commit SHA; partitions sequential',
            project_coverage='14_PROJECTS_IN_MIXED_CONTAINER',
            reason='Producer writes one gzip stream; reaching later projects traverses earlier T2 rows. Cannot open/decompress/index/hash payload now.',
            source_provenance='src/dataset/apachejit_final_dataset_freeze.py:_write_jsonl_gz,_partition_rows')
        r['TRAIN_class_available']=p.name=='row_identity_provenance.jsonl.gz'
        r['CODE_values_available']=p.name=='code_dataset.jsonl.gz'
        r['PROCESS_values_available']=p.name=='process_dataset.jsonl.gz'
        r['T1_labels_avoidable_at_read_time']=p.name!='row_identity_provenance.jsonl.gz'
    elif name.endswith('apachejit_train.csv'):
        r.update(verdict='SEMANTIC_MISMATCH',partition_semantics='UPSTREAM_BALANCED_SYNTHETIC_YEAR_2003_2016_SUBSET_NOT_FROZEN_TRAIN',
            row_level_addressability='SEQUENTIAL_CSV_NO_ROW_ID_INDEX',TRAIN_class_available=True,CODE_values_available=True,PROCESS_values_available=True,
            row_order_semantics='UPSTREAM_SAMPLING_ORDER_NOT_FROZEN_PROJECT_CHRONOLOGICAL_ORDER',
            reason='Frozen acquisition metadata reports balanced upstream subset (44834 rows). Campaign explicitly rebuilds per-project raw-timestamp partitions from total.csv and rejects the supplied synthetic-year partition as authoritative. T2 exclusion and exact complete TRAIN correspondence are not proved; no read.',
            source_provenance='apachejit_original_contract.json; apachejit_temporal_integrity.json; apachejit_temporal_partition_contract.json')
    elif name.endswith(('apachejit_test_large.csv','apachejit_test_small.csv')):
        r.update(verdict='SEMANTIC_MISMATCH',partition_semantics='UPSTREAM_SYNTHETIC_YEAR_2017_2019_LABELLED_FEATURE_ROWS_NOT_T1_IDENTITY_EXPORT',
            row_level_addressability='SEQUENTIAL_CSV_NO_COLUMN_OR_ROW_ACCESS_INDEX',
            reason='Original test subsets use a different partition rule and physically include buggy label/CODE/PROCESS columns. Cannot read-and-drop T1 labels/features; final T2 membership not independently separable.',
            source_provenance='apachejit_original_contract.json; apachejit_temporal_integrity.json; suitability producer read_csv calls')
    elif name.endswith(('apachejit_total.csv','apachejit_dataset_replication.zip')):
        r.update(verdict='T2_TRAVERSAL_REQUIRED',partition_semantics='ALL_UPSTREAM_ROWS_SUPERSET_OF_FROZEN_PARTITIONS',
            opening_necessarily_exposes_T2='SCIENTIFIC_ROW_SCAN_WOULD_EXPOSE_T2',
            row_level_addressability='CSV_OR_ZIP_MEMBER_ACCESS_NOT_ROW_PARTITION_ADDRESSABILITY',
            TRAIN_class_available=True,CODE_values_available=True,PROCESS_values_available=True,
            reason='Total CSV is the parent of every frozen campaign partition. ZIP member boundaries do not segregate final TRAIN/T1 from T2. No accepted index or whitelist-to-byte mapping exists; payload and full-file hashing forbidden.')
    elif '/apachejit/data/' in name:
        r.update(verdict='SEMANTIC_MISMATCH',partition_semantics='UPSTREAM_ISSUES_LINKS_OR_BENCHMARK_METRICS_WITHOUT_FROZEN_PARTITION_MAP',
            row_level_addressability='SEQUENTIAL_CSV_NO_FROZEN_ROW_ID_ADDRESS_MAP',
            reason='Issue-year/project link tables or unpartitioned Kamei/AST inputs do not supply a complete independently addressable frozen TRAIN/T1 source. No campaign partition isolation proof; constructing one would require an unapproved source scan.',
            source_provenance='Frozen ApacheJIT archive member inventory; upstream collector.py; campaign feature-schema producer')
    elif p.suffix=='.ipynb':
        r.update(verdict='PROVENANCE_INSUFFICIENT',reason='Notebook can embed executed row outputs; not opened. Producer code/provenance cannot itself supply complete safe row inputs or a partition index.')
    elif '/qtbase' in name or '/jit_defects4j/' in name:
        r.update(verdict='NOT_RELEVANT',partition_semantics='DIFFERENT_DATASET_LINEAGE',
            project_coverage='QT_OR_JIT_DEFECTS4J_NOT_APACHEJIT_14_PROJECT_CAMPAIGN',
            source_provenance='src/dataset/qt_materialization.py or src/dataset/jit_defects4j_materialization.py; dataset-specific artifact namespace',
            reason='Distinct producer/schema/dataset lineage. A TRAIN filename in another dataset cannot be substituted for frozen ApacheJIT membership; no payload read.')
    elif name.endswith('selected_train_rows.json'):
        r.update(verdict='INCOMPLETE_SOURCE',partition_semantics='SPRINT56_1_TRAIN_ONLY_SMOKE_SUBSET',
            row_level_addressability='SAFE_SEPARATE_TRAIN_FILE_BUT_INCOMPLETE',opening_necessarily_exposes_T2=False,
            TRAIN_without_T2_access=True,TRAIN_class_available=False,CODE_values_available=True,PROCESS_values_available=True,
            project_coverage='apache/activemq ONLY; 80 preselected smoke rows',
            reason='Producer omits labels and retains only 80 smoke rows from one project. Not all TRAIN rows, no remaining project coverage and no T1 identities. Protected only, not decoded as a source.')
    elif name.endswith('train_only_population_manifest.json'):
        r.update(verdict='INCOMPLETE_SOURCE',partition_semantics='FIRST_PROJECT_TRAIN_IDENTITY_MEMBERSHIP_ONLY',
            opening_necessarily_exposes_T2=False,TRAIN_without_T2_access=True,TRAIN_class_available=False,
            CODE_values_available=False,PROCESS_values_available=False,project_coverage='apache/activemq ONLY',
            reason='Contains first-project TRAIN membership/selection provenance, but no class/CODE/PROCESS rows or complete T1/all-project source.')
    elif name.endswith('t1_identity_integrity.json'):
        r.update(verdict='INCOMPLETE_SOURCE',partition_semantics='T1_AGGREGATE_IDENTITY_REGISTRY_NO_ROW_IDENTITIES',
            opening_necessarily_exposes_T2=False,T1_labels_avoidable_at_read_time=True,
            row_level_addressability='COUNT_DIGEST_AND_MIXED_MANIFEST_PATH_ONLY',
            reason='Parent 56.2 already establishes that this registry contains aggregate identity count/digest and a mixed-stream path, not T1 identity rows. No fresh registry-row read required.')
    elif name.endswith('t1_prediction_evidence.jsonl.gz'):
        r.update(verdict='SEMANTIC_MISMATCH',partition_semantics='T1_PREDICTION_EVIDENCE_LABELS_FEATURE_DERIVED_OUTPUTS',
            opening_necessarily_exposes_T2=False,row_level_addressability='SEQUENTIAL_LABELLED_PREDICTION_RECORDS',
            reason='Physically contains T1 labels/probabilities/outputs; identity-only reading cannot avoid those bytes. Read-and-drop and payload hashing are not authorized.')
    elif name.startswith(str(PARENT.relative_to(ROOT))+'/') and p.stat().st_size==0:
        r.update(verdict='INCOMPLETE_SOURCE',partition_semantics='EXPLICITLY_UNFROZEN_EMPTY_OUTPUT',opening_necessarily_exposes_T2=False,
            reason='Parent failure artifacts are intentionally empty. They cannot establish nonempty complete population coverage.')
    elif 'membership' in p.name:
        r.update(verdict='INCOMPLETE_SOURCE',partition_semantics='HISTORICAL_DEVELOPMENT_OR_OOF_MEMBERSHIP_METADATA',
            reason='Development/fold membership provenance supplies no proven complete C/P/classes plus identity-only T1 source. Different older dataset namespaces are not substituted; no row payload inspection.')
    return r


def reconciliation_spec():
    scope_rows=lines(PARENT/'primary_xai_scope_ledger.jsonl')
    projects=sorted({r['project'] for r in scope_rows})
    t1={p:{'count':next(r['historical_T1_row_count'] for r in scope_rows if r['project']==p),
           'membership_digest':next(r['G4_G5_T1_membership_digest'] for r in scope_rows if r['project']==p)} for p in projects}
    train={}
    for r in lines(STORE/'repetitions/rep_01/component_journal.jsonl'):
        if '|FINAL_BASE|' not in r.get('logical_id',''):
            continue
        p=r['canonical_state']['provenance']['project']
        value={'count':r['check_row_count'],'membership_digest':r['canonical_state']['provenance']['train_membership_sha256']}
        if p in train and train[p]!=value:
            raise SafeSourceError('TRAIN_PROVENANCE_MISMATCH: inconsistent frozen membership')
        train[p]=value
    if set(train)!=set(projects):
        raise SafeSourceError('TRAIN_PROVENANCE_MISMATCH: coverage')
    return {'status':'MEMBERSHIP_DIGEST_RECIPE_SPECIFIED_SOURCE_ROWS_UNAVAILABLE','projects':projects,
        'TRAIN':train,'T1':t1,'membership_recipe':'SHA256(JSON ordered row_identifier list; ensure_ascii=true, sort_keys=true, separators=(comma,colon), allow_nan=false; UTF8; exactly one terminal LF)',
        'original_order':'timestamp UTC ascending then commit SHA ascending within project; no SHA-selection ordering substituted',
        'recipe_sources':['src/experimentation/q1_controlled_train_validation_baselines.py:canonical_bytes,digest',
            'src/evaluation/q1_xai_g4_row_equivalence.py:T1_row_identity_digest=digest(reference_ids)',
            'src/evaluation/q1_xai_train_source_reconstruction.py:train_membership_sha256'],
        'feature_reference':'Frozen CODE/PROCESS column contract and original per-row numeric provenance required; no complete safe per-project numeric reference supplied',
        'row_identity_recipe':'SHA256 UTF8 apachejit-v2|project|canonical_repository|commit_sha',
        'reconciliation_executed':False,'T2_counts_or_memberships_used':False}


def validate_rows(records,project,partition,expected,feature_schema):
    if partition not in ['TRAIN','T1']:
        raise SafeSourceError('SOURCE_SEMANTICS_INSUFFICIENT: prohibited partition')
    if feature_schema.get('CODE')!=C or feature_schema.get('PROCESS')!=P:
        raise SafeSourceError('TRAIN_FEATURE_SCHEMA_MISMATCH: column order')
    required=TRAIN_FIELDS if partition=='TRAIN' else T1_FIELDS
    seen=set()
    for row in records:
        if set(row)!=set(required):
            raise SafeSourceError('TRAIN_FEATURE_SCHEMA_MISMATCH' if partition=='TRAIN' else 'T1_IDENTITY_PROVENANCE_MISMATCH: forbidden/missing fields')
        if row['partition']!=partition or row['project']!=project:
            raise SafeSourceError('SOURCE_SEMANTICS_INSUFFICIENT: project/partition')
        rid=row['row_identifier']
        if not isinstance(rid,str) or not re.fullmatch('[0-9a-f]{64}',rid) or rid in seen:
            raise SafeSourceError('SOURCE_SEMANTICS_INSUFFICIENT: duplicate/invalid identity')
        seen.add(rid)
        order=row['order_key']
        if not isinstance(order,list) or len(order)!=2 or not all(isinstance(x,str) for x in order):
            raise SafeSourceError('SOURCE_SEMANTICS_INSUFFICIENT: order key')
        if not order[0].endswith('Z') or not re.fullmatch('[0-9a-f]{40}',order[1]):
            raise SafeSourceError('SOURCE_SEMANTICS_INSUFFICIENT: original timestamp/SHA order key')
        try:
            datetime.fromisoformat(order[0].replace('Z','+00:00'))
        except ValueError as exc:
            raise SafeSourceError('SOURCE_SEMANTICS_INSUFFICIENT: invalid timestamp') from exc
        if partition=='TRAIN':
            if type(row['class']) is not int or row['class'] not in [0,1]:
                raise SafeSourceError('TRAIN_FEATURE_SCHEMA_MISMATCH: class domain')
            if any(type(row[k]) not in [int,float] or not math.isfinite(row[k]) for k in C+P):
                raise SafeSourceError('TRAIN_FEATURE_SCHEMA_MISMATCH: numeric value')
    if records!=sorted(records,key=lambda r:r['order_key']):
        raise SafeSourceError('SOURCE_SEMANTICS_INSUFFICIENT: original order changed')
    if len(records)!=expected['count'] or digest([r['row_identifier'] for r in records])!=expected['membership_digest']:
        raise SafeSourceError(partition+'_MEMBERSHIP_DIGEST_MISMATCH')
    # Never invent a full-row reconciliation hash from membership-only evidence.
    if not expected.get('canonical_rows_sha256'):
        raise SafeSourceError('DIGEST_RECONCILIATION_SPECIFICATION_INCOMPLETE: exact row/value provenance absent')
    payload=b''.join(canonical(r) for r in records)
    if hashlib.sha256(payload).hexdigest()!=expected['canonical_rows_sha256']:
        raise SafeSourceError('TRAIN_PROVENANCE_MISMATCH: exact values' if partition=='TRAIN' else 'T1_IDENTITY_PROVENANCE_MISMATCH')
    return payload


def materialize(phase_a,bundle,expected,destination):
    """Conditional writer for already safely acquired and independently verified rows."""
    if phase_a.get('status')!='PHASE_A_ACCEPTED' or not phase_a.get('all_acceptance_criteria_verified'):
        raise SafeSourceError('NO_SAFE_SOURCE_FOUND: Phase B denied before data processing')
    projects=expected['projects']
    if set(bundle)!= {'TRAIN','T1'} or any(set(bundle[p])!=set(projects) for p in ['TRAIN','T1']):
        raise SafeSourceError('SOURCE_SEMANTICS_INSUFFICIENT: partial project coverage')
    payloads={}
    all_ids=set()
    for partition in ['TRAIN','T1']:
        for project in projects:
            payloads[partition,project]=validate_rows(bundle[partition][project],project,partition,
                expected[partition][project],{'CODE':C,'PROCESS':P})
            ids={r['row_identifier'] for r in bundle[partition][project]}
            if all_ids & ids:
                raise SafeSourceError('SOURCE_SEMANTICS_INSUFFICIENT: overlapping identities')
            all_ids.update(ids)
    # No writes occur until the entire bundle passes exact validation.
    destination=Path(destination)
    if destination.resolve().is_relative_to(ROOT) and not destination.resolve().is_relative_to(OUT):
        raise SafeSourceError('Materialization outside dedicated namespace denied')
    if destination.exists():
        raise SafeSourceError('Refuse to overwrite existing materialization')
    destination.mkdir(parents=True)
    artifacts=[]
    for (partition,project),payload in sorted(payloads.items()):
        folder=destination/partition.lower()
        folder.mkdir(exist_ok=True)
        basename=project.replace('/','__')
        filename=basename+'.jsonl.gz' if partition=='TRAIN' else basename+'_identities.jsonl'
        path=folder/filename
        encoded=gzip.compress(payload,mtime=0) if partition=='TRAIN' else payload
        path.write_bytes(encoded)
        artifacts.append({'path':path.relative_to(destination).as_posix(),'sha256':sha(path),'bytes':len(encoded),
            'logical_content_sha256':hashlib.sha256(payload).hexdigest(),'rows':expected[partition][project]['count'],
            'project':project,'partition':partition,'schema_digest':digest(TRAIN_FIELDS if partition=='TRAIN' else T1_FIELDS),
            'ordering_digest':digest([r['order_key'] for r in bundle[partition][project]]),
            'source_provenance':phase_a['source_provenance'],'origin':'DERIVED_SAFE_POPULATION_SOURCE'})
    return artifacts


def write_manifest():
    (OUT/'MANIFEST.sha256').write_text(''.join(f'{sha(p)}  {p.relative_to(OUT).as_posix()}\n'
        for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='MANIFEST.sha256'))


def audit():
    if git('symbolic-ref','--short','HEAD')!=BRANCH:
        raise SafeSourceError('Branch mismatch; no switching permitted')
    OUT.mkdir(parents=True,exist_ok=False)
    sys.addaudithook(guard)
    parent=read(PARENT/'sprint56_2_summary.json')
    assert parent['outcome']=='PRIMARY_XAI_T1_SELECTION_CONTRACT_FAILURE'
    scopes=lines(PARENT/'primary_xai_scope_ledger.jsonl')
    assert len(scopes)==len({r['model_identity_sha256'] for r in scopes})==389
    declared=declared_hashes()
    save('parent_integrity_before.json',protected_snapshot(declared))
    paths,search=discover()
    save('source_discovery.json',search)
    save('path_inventory.json',{'paths':paths,'payload_content_inspected':False})
    selected_paths=candidate_paths(paths,search)
    tracked=set(git('ls-files').splitlines())
    ignored_process=subprocess.run(['git','check-ignore','--stdin'],input='\n'.join(selected_paths)+'\n',cwd=ROOT,text=True,capture_output=True)
    if ignored_process.returncode not in [0,1]:
        raise SafeSourceError('Git tracking audit failed')
    ignored=set(ignored_process.stdout.splitlines())
    candidates=[classify_candidate(p,declared,tracked,ignored) for p in selected_paths]
    save_lines('source_candidate_ledger.jsonl',candidates)
    save('reconciliation_spec.json',reconciliation_spec())
    accepted=[r for r in candidates if r['verdict'] in ['SAFE_DIRECT_SOURCE','SAFE_UPSTREAM_RECONSTRUCTION_SOURCE','SAFE_PREEXISTING_RANDOM_ACCESS_INDEX']]
    # No source is promoted by extension, filename or guessed partition semantics.
    if accepted:
        raise SafeSourceError('Accepted candidate requires explicit full provenance/read-path implementation before Phase B')
    save('source_selection.json',{'phase':'PHASE_A_COMPLETE','status':'NO_SAFE_SOURCE_FOUND','selected_source':None,
        'accepted_candidates':[],'phase_B_authorized_by_audit':False,'materialization_executed':False,
        'outcome':'NO_SAFE_TRAIN_T1_SOURCE_AVAILABLE_UNDER_FROZEN_T2_BOUNDARY',
        'candidate_verdict_counts':dict(sorted(Counter(r['verdict'] for r in candidates).items())),
        'source_selection_criteria':['PROVENANCE','ACCESSIBILITY','PARTITION_SEMANTICS','IDENTITY_INTEGRITY','FEATURE_INTEGRITY','REPRODUCIBILITY','T2_ISOLATION'],
        'performance_or_XAI_outputs_used':False})
    save('feature_schema.json',{'TRAIN_fields':TRAIN_FIELDS,'T1_fields':T1_FIELDS,'CODE':C,'PROCESS':P,
        'class_domain':[0,1],'numeric_policy':'EXACT_FINITE_SOURCE_VALUES_NO_COERCION_OR_TOLERANCE_MATCHING',
        'additional_fields':False,'schema_sha256':digest({'TRAIN':TRAIN_FIELDS,'T1':T1_FIELDS,'C':C,'P':P})})
    for partition in ['train','t1']:
        save(partition+'_membership_registry.json',{'status':'NOT_MATERIALIZED','projects':{},'row_count':0,
            'reason':'NO_ACCEPTED_SAFE_SOURCE','frozen_expected_membership_reference':'reconciliation_spec.json'})
    save('materialization_integrity.json',{'phase_A':'COMPLETE_NO_SAFE_SOURCE','phase_B':'NOT_STARTED',
        'materialized_files':[],'materialized_rows':0,'materialized_bytes':0,
        'real_membership_reconciliation':'NOT_EXECUTED','real_feature_reconciliation':'NOT_EXECUTED',
        'real_repeatability':'NOT_EXECUTED','synthetic_fixture_tests_are_not_scientific_materialization':True})
    counters={name:0 for name in COUNTER_NAMES}
    counters.update({'T2_STATE':'DENY_SEALED_REVIEWER_RESERVE','Sprint56_3_authorized':False,'resume_Sprint56_2_authorized_by_this_run':False,
        'historical_Sprint54_predictive_access_scoring':[1,1],
        'counter_scope':'SPRINT56_2A_ONLY; source row accesses count row acquisition/decoding, not explicitly authorized integrity-only hashing of prior TRAIN/smoke artifact bytes',
        'prior_Sprint56_2_aggregate_T1_registry_access':1,'T1_aggregate_registry_fresh_source_read_this_stage':0})
    save('governance_counters.json',counters)
    save('provenance_chain.json',{'branch':BRANCH,'head':git('rev-parse','HEAD'),
        'parent_outcomes':{'Sprint56_1':'PRIMARY_XAI_ISOLATED_RUNTIME_SMOKE_TEST_PASS','Sprint56_2':parent['outcome']},
        'scope_ledger_sha256':sha(PARENT/'primary_xai_scope_ledger.jsonl'),
        'parent_blocker_sha256':sha(PARENT/'population_source_access_blocker.json'),
        'parent_MANIFEST_sha256':sha(PARENT/'MANIFEST.sha256'),'runtime_lock_sha256':sha(SMOKE/'isolated_runtime_lock.json'),
        'chain':['FROZEN_ACQUISITION_METADATA','CANONICAL_FREEZE_PRODUCER','G1_G5_MEMBERSHIP_PROVENANCE','SPRINT56_1','SPRINT56_2_BLOCKER','SPRINT56_2A_SOURCE_AUDIT'],
        'timestamp':datetime.now(timezone.utc).isoformat(),'failure_classes':FAILURES})
    finish()


def finish():
    sys.addaudithook(guard)
    before=read(OUT/'parent_integrity_before.json')
    after=protected_snapshot(declared_hashes())
    if before!=after:
        save('parent_integrity_after.json',after)
        raise SafeSourceError('PARENT_ARTIFACT_INTEGRITY_FAILURE')
    save('parent_integrity_after.json',after)
    source=read(OUT/'source_selection.json')
    search=read(OUT/'source_discovery.json')
    provenance=read(OUT/'provenance_chain.json')
    validation=read(OUT/'validation_results.json') if (OUT/'validation_results.json').exists() else {'status':'PENDING'}
    save('next_action.json',{'human_review_required':True,'resume_56_2':False,'Sprint56_3_authorized':False,
        'required_information':['Complete pre-existing independently addressable TRAIN source for 14 projects, including exact classes/CODE/PROCESS/original ordering and frozen provenance.',
            'Complete independently addressable T1 identity-only source with original ordering and no physically unavoidable labels/features.',
            'Frozen identity-to-source-location proof or pre-existing trusted random-access index; not an index created by scanning T2 now.'],
        'human_decision':'Provide a verifiable existing source/index or decide on a separate prospective scientific protocol for upstream rematerialization. Any operation requiring T2 traversal or unavoidable T1 label/feature reads is outside current authorization; no boundary change is assumed.',
        'no_best_effort_export':True,'no_direct_restart_of_56_3':True})
    counts='\n'.join(f'| {key} | {value} |' for key,value in source['candidate_verdict_counts'].items())
    report=f'''# Sprint 56.2A — Safe TRAIN/T1 Source Audit
+
+`NO_SAFE_TRAIN_T1_SOURCE_AVAILABLE_UNDER_FROZEN_T2_BOUNDARY`
+
+Phase A completed without an acceptable source. Phase B was not started. No scientific source rows, selected XAI populations, models, attributions or figures were produced.
+
+## A. Branch / HEAD
+`{BRANCH}` / `{provenance['head']}`. No branch switch, staging, .gitignore change, commit, push or PR.
+
+## B. Parent outcomes
+Sprint56.1 `PRIMARY_XAI_ISOLATED_RUNTIME_SMOKE_TEST_PASS`; Sprint56.2 `PRIMARY_XAI_T1_SELECTION_CONTRACT_FAILURE`. The historical blocker remains unchanged and is an access/provenance failure, not a predictive-model or XAI-method failure.
+
+## C. Frozen universe
+389/389 READY_VERIFIED; E1 168, E2 221. Exactly three apache/zeppelin LR exclusions: C+T, P+T, C+P+T. The 168 base feature definitions and 56 TEXT representation records remain protected; no scope reselection.
+
+## D. Protected evidence
+`parent_integrity_before.json` and `parent_integrity_after.json` match. Fresh SHA256 was computed for {after['fresh_sha256_count']} permitted files, including all 5,649 model-state objects (2,139,594,110 bytes), 0 missing references and 0 orphans. {after['payload_not_rehashed_count']} prohibited payload files retain inherited manifest SHA256, Git blob ID where tracked and filesystem metadata instead of a fresh payload hash.
+
+**Hashing boundary:** Sprint54 T1 prediction payloads contain labels/outputs. The current instruction forbids reading these bytes even to discard them, and T2 payload hashing is explicitly forbidden. Accordingly no prohibited payload was opened merely to satisfy a checksum step. Their recorded hashes and metadata remained unchanged, but fresh byte-equivalence is **not claimed** for unrehashable payloads. This limitation is explicit and cannot be treated as a successful materialization-integrity proof.
+
+## E. Search paths
+All eight requested roots were inventoried by paths/stat metadata: audits/, data/, artifacts/, outputs/, experiments/, configs/, src/, tests/. See `source_discovery.json` and `path_inventory.json`. Scientific payloads were not opened to search their content. Source producers, safe provenance/manifests and relevant Git history were inspected.
+
+## F. Candidate inventory
+{sum(source['candidate_verdict_counts'].values())} candidate records retain path, type, tracking status, source provenance, partition/addressability, safety and field availability, order/coverage/reconciliation, size, declared source hash, verdict and exact reason. Missing hashes are null rather than invented; unsafe payload hashes are inherited, not recomputed.
+
+## G. Classifications
+| Verdict | Candidates |
+|---|---:|
+{counts}
+
+No candidate received a SAFE verdict.
+
+## H. Segregated sources
+The Sprint56.1 separate TRAIN file has only 80 preselected activemq smoke rows, lacks class labels and does not cover the other projects or T1. Its TRAIN membership metadata is also first-project only and has no full C/P/classes. Parent56.2 population files are intentionally empty. The aggregate T1 registry records a count/hash/path but supplies no identity rows. Qt/JIT-Defects4J exports have a different producer/dataset lineage and cannot replace ApacheJIT.
+
+## I. Upstream ApacheJIT
+Acquisition provenance identifies the original balanced train subset (44,834 rows, supplied synthetic years 2003–2016) and labelled/featured 2017–2019 test subsets. The frozen campaign explicitly rebuilds per-project chronological partitions from raw UTC timestamps and rejects supplied synthetic year as authoritative. Therefore `apachejit_train.csv` is not a verified full frozen TRAIN export. `apachejit_test_*.csv` cannot be consumed as identity-only T1 because label/feature bytes are inseparable without a proven direct-access map. `apachejit_total.csv` is the parent of all campaign partitions; scanning it or rebuilding a row index would expose T2. ZIP member access does not isolate final partitions. Year/issue/link/Kamei files do not establish the missing partition/location proof. Notebook outputs were not opened because embedded scientific rows cannot be ruled out.
+
+## J. Pre-existing indexes and Git history
+No relevant SQLite/Parquet/Arrow/Feather/BGZF-GZI/zran/byte index was found. Relevant acquisition and final-freeze commit trees and reachable path history preserve metadata and mixed streams, not an independently addressable complete safe export. Bare Git repositories support commit-SHA object lookup, but the complete frozen row-id-to-commit map is missing and exact benchmark class/Kamei values cannot be replaced with Git-derived approximations. No Git commit payload or mixed-data index was read/created to repair this gap.
+
+## K. Selected source
+None. `source_selection.json` records `NO_SAFE_SOURCE_FOUND` and denies Phase B.
+
+## L. T2 isolation
+No safe read path was proved. Mixed files, unknown upstream CSV/notebook payloads, known T2 data and labelled prediction ledgers are rejected by the guard. No decompression/filtering, new index, protected-row hashing, T2 completeness check or T2 count-based inference occurred.
+
+## M. TRAIN semantics
+The validator freezes exactly project, TRAIN partition, row_identifier, class, order_key, CODE {', '.join(C)}, PROCESS {', '.join(P)}. Binary class, finite exact numeric values, no extra/proxy/outcome fields, exact feature order and full project membership/value provenance are required. No actual TRAIN source was acquired.
+
+## N. T1 identity-only semantics
+Exactly project, T1 partition, row_identifier, order_key. No label/class, probability, prediction, confidence, correctness, residual, feature value or output. Labelled/featured T1 rows cannot be read-and-dropped. No actual T1 identity source was acquired.
+
+## O. Project coverage
+Required: all 14 frozen projects. Accepted source coverage: 0 complete projects. Partial sources are not promoted or combined optimistically. No T2 counts were used to infer completeness.
+
+## P. Membership reconciliation
+The historical membership digest recipe is specified: SHA256 of the canonical original-order row-identity list with compact sorted-key ASCII-safe JSON, UTF8 and one final LF. G4 producer and base provenance provide the exact per-project counts/digests, persisted in `reconciliation_spec.json`. Actual reconciliation is not executed because source rows are unavailable. A membership-only hash cannot substitute for exact numerical/class provenance; the validator fails if a required row/value reference is absent.
+
+## Q. Feature reconciliation
+CODE/PROCESS schema and ordering match the frozen definitions. No alternative computation, tolerance matching, proxy field or numerical coercion is used. Real value reconciliation: NOT EXECUTED.
+
+## R. Determinism
+Conditional serialization uses canonical JSON and gzip mtime=0 after full validation. Focused tests exercise exact two-directory reproduction on explicitly synthetic fixtures only. Real materialization/repeatability: NOT EXECUTED; fixture success is not a scientific source PASS.
+
+## S. Materialized inventory
+0 files, 0 rows, 0 scientific source bytes. No train/ or t1/ export directory was created. Membership registries explicitly say NOT_MATERIALIZED. No final XAI population files were created in this namespace. Generated content consists only of audit/provenance/report/test evidence; no large scientific row dump or model binary is added to Git.
+
+## T. T1 counters
+T1_SAFE_SOURCE_ACCESS_COUNT=0; T1_IDENTITY_ROW_READ_COUNT=0; T1_LABEL_READ_COUNT=0; T1_FEATURE_READ_COUNT=0; T1_MODEL_QUERY_COUNT=0; T1_XAI_ATTRIBUTION_EXECUTION_COUNT=0. The prior Sprint56.2 aggregate-registry access of 1 is historical, not reset or repeated as a source read here.
+
+## U. T2 counters
+T2_ACCESS_COUNT=0; T2_IDENTITY_READ_COUNT=0; T2_FEATURE_READ_COUNT=0; T2_LABEL_READ_COUNT=0; T2_MODEL_QUERY_COUNT=0; T2_XAI_EXECUTION_COUNT=0. State DENY_SEALED_REVIEWER_RESERVE.
+
+## V. Other counters
+TRAIN_SAFE_SOURCE_ACCESS_COUNT=0; TRAIN_IDENTITY_ROW_READ_COUNT=0; TRAIN_LABEL_ROW_READ_COUNT=0; TRAIN_FEATURE_ROW_READ_COUNT=0; TRAIN_MODEL_QUERY_COUNT=0; TRAIN_XAI_ATTRIBUTION_EXECUTION_COUNT=0. Scientific SHAP/analytical, predictive metrics, retraining, refit, reconstruction, recalibration, figures, commit and push: all 0. Integrity-only hashing of authorized prior TRAIN/smoke bytes is distinguished from acquiring/decoding source rows. Historical Sprint54 predictive access/scoring remains 1/1.
+
+## W. Parent post-integrity
+All freshly hashable protected records and object bytes match; prohibited unrehashable payloads retain the same recorded hash/Git/blob/filesystem evidence with the limitation in D. Neither parent56.2 source/guard nor earlier tests/evidence were edited. Both runtime environments and .gitignore are unchanged.
+
+## X. Tests
+`{json.dumps(validation,sort_keys=True)}`
+Tests cover guards, exact schemas, prohibited fields, class/value/order integrity, duplicate/wrong-partition/wrong-project/partial-coverage failures, membership/value mismatches, conditional Phase-B refusal, deterministic synthetic serialization, parent preservation, prohibited APIs and manifest integrity. Only permissible governance regressions are run; earlier population-reading, fitting, scientific-output arithmetic and historical diff-size tests are not silently executed or edited.
+
+## Y. Disposition
+`NO_SAFE_TRAIN_T1_SOURCE_AVAILABLE_UNDER_FROZEN_T2_BOUNDARY`. This is an evidence-backed source-access failure, not an XAI-method or predictor failure. No best-effort source exists. Sprint56.2 remains historically incomplete; Sprint56.3 is not authorized.
+
+## Z. Exact next action
+Human review must provide an independently verifiable pre-existing T2-free source/index, or decide on a separate prospective scientific protocol for upstream rematerialization. The missing information is complete frozen TRAIN identities/classes/C/P/order/provenance and complete T1 identity-only order/provenance plus safe physical locations. Any new extraction needing T2 traversal or unavoidable T1 labels/features exceeds this authorization. No protocol amendment is assumed, no boundary is weakened, and no automatic resumption is permitted.
+
+SAFE_TRAIN_T1_SOURCE_NOT_AVAILABLE_UNDER_CURRENT_T2_BOUNDARY
+
+READY FOR HUMAN REVIEW — DO NOT START SPRINT 56.3
+'''
    (OUT/'SAFE_SOURCE_REPORT.md').write_text(report.replace('\n+','\n'))
    save('implementation_provenance.json',{'source_sha256':sha(Path(__file__)),
        'tests_sha256':sha(ROOT/'tests/evaluation/test_q1_primary_xai_safe_population_source.py') if (ROOT/'tests/evaluation/test_q1_primary_xai_safe_population_source.py').exists() else None,
        'forbidden_source_payload_opens':0,'scientific_source_materialization':False})
    save('read_only_access_log.json',{'paths':sorted(READ_EVENTS),'interpretation':'Allowed audit/metadata/integrity reads; not row-source traversal; denied requests fail before OS open'})
    write_manifest()
    print('NO_SAFE_TRAIN_T1_SOURCE_AVAILABLE_UNDER_FROZEN_T2_BOUNDARY')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('stage',choices=['audit','finish','manifest'])
    {'audit':audit,'finish':finish,'manifest':write_manifest}[parser.parse_args().stage]()
