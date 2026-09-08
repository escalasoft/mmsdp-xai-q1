"""S56.2B inspection and protocol only. No router or row serializer exists here."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'audits/q1-primary-xai-t2-semantic-boundary-amendment/1.0.0'
BRANCH='sprint-10/q1-primary-xai-execution'
F='audits/q1-apachejit-final-dataset-freeze/1.0.0/'
A='audits/q1-apachejit-v2-scientific-suitability/1.0.0/'
S='audits/q1-primary-xai-runtime-smoke/1.0.0/'
P='audits/q1-primary-xai-population-freeze/1.0.0/'
Q='audits/q1-primary-xai-safe-population-source/1.0.0/'
CODE='src/dataset/apachejit_final_dataset_freeze.py'
SER='src/experimentation/q1_controlled_train_validation_baselines.py'
C=['la','ld','nf','nd','ns','ent']; PROCESS=['ndev','age','nuc','aexp','arexp','asexp']
CATEGORIES={'DIRECT_CODE_EVIDENCE','DIRECT_MANIFEST_EVIDENCE','DIRECT_PROVENANCE_EVIDENCE','DERIVED_INFERENCE','UNKNOWN'}
ALLOW={CODE,SER,A+'apachejit_archive_provenance.json',A+'apachejit_original_contract.json',
 A+'apachejit_temporal_partition_contract.json',F+'temporal_ordering_contract.json',F+'test_access_contract.json',
 S+'sprint56_1_summary.json',S+'isolated_runtime_lock.json',P+'sprint56_2_summary.json',P+'scope_readiness_summary.json',
 P+'primary_xai_scope_ledger.jsonl',P+'population_source_access_blocker.json',Q+'source_selection.json',
 Q+'reconciliation_spec.json',Q+'governance_counters.json',Q+'source_discovery.json',Q+'parent_integrity_after.json'}
COUNTERS=['TRAIN_SCIENTIFIC_ROW_READ_COUNT','T1_SCIENTIFIC_ROW_READ_COUNT','T2_SCIENTIFIC_ACCESS_COUNT',
 'T2_IDENTITY_READ_COUNT','T2_LABEL_READ_COUNT','T2_FEATURE_READ_COUNT','T2_MODEL_QUERY_COUNT','T2_XAI_EXECUTION_COUNT',
 'T2_PREDICTIVE_EVALUATION_COUNT','T2_LEVEL2_SCIENTIFIC_ACCESS_COUNT','T2_ACCESS_COUNT','mixed_payload_open_count',
 'source_container_access_count','partition_routing_execution_count','rematerialization_execution_count',
 'model_query_count','scientific_SHAP_execution_count','scientific_analytical_attribution_execution_count',
 'predictive_metric_count','retraining_count','refit_count','reconstruction_count','recalibration_count',
 'figure_generation_count','commit_count','push_count']
READS=set()

def canonical(value):
    return (json.dumps(value,sort_keys=True,ensure_ascii=True,allow_nan=False,separators=(',',':'))+'\n').encode('utf-8')

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(name): return json.loads((ROOT/name).read_text())
def save(name,value): (OUT/name).write_bytes(canonical(value))
def git(*args): return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()

def guard(event,args):
    if event!='open' or not isinstance(args[0],(str,bytes,os.PathLike)): return
    p=Path(os.fsdecode(args[0])).resolve()
    if not p.is_relative_to(ROOT): return
    name=p.relative_to(ROOT).as_posix()
    mode,flags=args[1] or '',args[2] or 0
    writing=any(c in mode for c in 'wax+') or bool(flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC))
    if writing and not p.is_relative_to(OUT):
        raise PermissionError('S56.2B inspection-only protected write denied: '+name)
    allowed=(p.is_relative_to(OUT) or name in ALLOW or
             name.startswith(('src/','tests/')) and p.suffix in ['.py','.pyc'] or
             name.startswith(('.venv/','.venv-xai-s56/')) or
             name.startswith('audits/') and p.name=='MANIFEST.sha256' or name=='.gitignore')
    if not allowed:
        raise PermissionError('S56.2B unapproved payload read denied: '+name)
    if not writing and not p.is_relative_to(OUT): READS.add(name)

def decide(criteria,ledger,already_bound=False,conflict=False):
    if any(r['category'] not in CATEGORIES for r in ledger): raise ValueError('Unknown evidence category')
    by_id={r['id']:r for r in ledger}
    if conflict: return 'T2_SEMANTIC_BOUNDARY_PROVENANCE_CONFLICT'
    if already_bound: return 'T2_ALREADY_SEMANTICALLY_BOUND_AT_SOURCE'
    for key in 'ABCDE':
        item=criteria.get(key,{})
        refs=item.get('evidence_ids',[])
        if item.get('status')!='DIRECTLY_SUPPORTED' or not refs:
            return 'T2_SEMANTIC_BOUNDARY_EVIDENCE_INSUFFICIENT'
        if any(r not in by_id or not by_id[r]['category'].startswith('DIRECT_') or by_id[r].get('supports')!=True for r in refs):
            return 'T2_SEMANTIC_BOUNDARY_EVIDENCE_INSUFFICIENT'
    return 'T2_SEMANTIC_BOUNDARY_AMENDMENT_JUSTIFIED'

def snapshot():
    # No scientific payload or model bytes are opened. Stat and inherited hashes
    # are deliberately distinguished from fresh metadata SHA256 observations.
    result={}
    for prefix in [S,P,Q]:
        parent=ROOT/prefix
        declared={name:h for h,name in (x.split('  ',1) for x in (parent/'MANIFEST.sha256').read_text().splitlines())}
        rows={}
        for p in sorted(parent.rglob('*')):
            if not p.is_file(): continue
            name=p.relative_to(parent).as_posix(); st=p.stat()
            record={'bytes':st.st_size,'mtime_ns':st.st_mtime_ns,'inode':st.st_ino,'inherited_manifest_sha256':declared.get(name)}
            if prefix+name in ALLOW or name=='MANIFEST.sha256':
                record['fresh_metadata_sha256']=sha(p)
                if name in declared and record['fresh_metadata_sha256']!=declared[name]: raise ValueError('Parent metadata mismatch')
            rows[name]=record
        result[prefix]=rows
    for name in [CODE,SER,'.gitignore','src/evaluation/q1_primary_xai_population_freeze.py','src/evaluation/q1_primary_xai_safe_population_source.py']:
        result[name]={'sha256':sha(ROOT/name)}
    store=ROOT/'audits/q1-xai-reconstruction-execution/1.0.0/objects'
    result['object_store_stat_only']={p.name:{'bytes':p.stat().st_size,'mtime_ns':p.stat().st_mtime_ns,'inode':p.stat().st_ino} for p in sorted(store.iterdir()) if p.is_file()}
    result['object_store_integrity_basis']='Inherited Sprint56.2A fresh integrity evidence; no model object payload opened in 56.2B.'
    result['limitation']='Whole-parent fresh byte equivalence is not claimed for scientific payloads: inherited manifest hashes plus unchanged filesystem metadata; fresh checks restricted to allowed metadata/source.'
    return result

def evidence(eid,category,path,start,end,claim,supports=True):
    text=(ROOT/path).read_text().splitlines()
    return {'id':eid,'category':category,'path':path,'line_start':start,'line_end':end,'file_sha256':sha(ROOT/path),
            'excerpt':'\n'.join(text[start-1:end]),'claim':claim,'supports':supports}

def manifest():
    (OUT/'MANIFEST.sha256').write_text(''.join(f'{sha(p)}  {p.name}\n' for p in sorted(OUT.iterdir()) if p.is_file() and p.name!='MANIFEST.sha256'))

def build():
    if git('symbolic-ref','--short','HEAD')!=BRANCH: raise ValueError('Wrong branch; no switch allowed')
    OUT.mkdir(parents=True,exist_ok=False)
    sys.addaudithook(guard)
    save('parent_integrity_before.json',snapshot())
    rows=[json.loads(x) for x in (ROOT/P/'primary_xai_scope_ledger.jsonl').read_text().splitlines()]
    scopes=load(P+'scope_readiness_summary.json')
    assert len(rows)==389 and len({r['project'] for r in rows})==14
    assert load(S+'sprint56_1_summary.json')['outcome']=='PRIMARY_XAI_ISOLATED_RUNTIME_SMOKE_TEST_PASS'
    assert load(P+'sprint56_2_summary.json')['outcome']=='PRIMARY_XAI_T1_SELECTION_CONTRACT_FAILURE'
    parent=load(Q+'source_selection.json')
    assert sum(parent['candidate_verdict_counts'].values())==113 and parent['accepted_candidates']==[]
    ledger=[
      evidence('E01','DIRECT_CODE_EVIDENCE',CODE,723,745,'Existing upstream total.csv is read and identified before partition assignment.'),
      evidence('E02','DIRECT_CODE_EVIDENCE',CODE,311,342,'Partition assignment uses project-local stable UTC/SHA sort and floor integer ordinal boundaries, without label or model inputs.'),
      evidence('E03','DIRECT_CODE_EVIDENCE',CODE,765,801,'Partition assignment precedes derived row hash construction; hash identity components were already available.'),
      evidence('E04','DIRECT_CODE_EVIDENCE',CODE,343,371,'The historical function ALSO aggregates every partition label/class support. Reusing it violates the proposed blind-router contract.',False),
      evidence('E05','DIRECT_CODE_EVIDENCE',CODE,850,867,'Historical project eligibility includes structural all-partition class support, including reserve; cannot claim historically wholly outcome-unobserved.',False),
      evidence('E06','DIRECT_CODE_EVIDENCE',CODE,218,243,'Canonical repository identity is deterministically resolved from commit existence and priority, not solely from project name.'),
      evidence('E07','DIRECT_CODE_EVIDENCE',SER,101,115,'Historical membership digest serializes ordered identity list as compact sorted-key ASCII-escaped JSON, UTF8 and terminal LF.'),
      evidence('E08','DIRECT_CODE_EVIDENCE',CODE,76,87,'Historical dataset JSONL serializer exists, but does not establish a digest of the new minimal safe-source schema.'),
      evidence('E09','DIRECT_MANIFEST_EVIDENCE',F+'temporal_ordering_contract.json',1,len((ROOT/F/'temporal_ordering_contract.json').read_text().splitlines()),'Frozen raw UTC/SHA chronology; synthetic year is nonauthoritative.'),
      evidence('E10','DIRECT_PROVENANCE_EVIDENCE',A+'apachejit_temporal_partition_contract.json',1,len((ROOT/A/'apachejit_temporal_partition_contract.json').read_text().splitlines()),'Acquisition contract explicitly says campaign partition not yet materialized; supplied upstream split is reference only.'),
      evidence('E11','DIRECT_PROVENANCE_EVIDENCE',F+'test_access_contract.json',1,len((ROOT/F/'test_access_contract.json').read_text().splitlines()),'Historical T0 allowed structural class-support checks; no predictive quantity influenced split; amendments cannot silently claim untouched holdout.'),
    ]
    ledger += [{'id':'U01','category':'UNKNOWN','supports':False,'claim':'No historical independently isolated blind router or direct field-access proof for upstream CSV was located; current code uses full pd.read_csv.'},
               {'id':'I01','category':'DERIVED_INFERENCE','supports':False,'claim':'A new isolated scanner might route from upstream metadata with exact cutpoints. This possibility does not prove T2 nonexposure and is not sufficient to approve C/D.'}]
    (OUT/'evidence_classification_ledger.jsonl').write_bytes(b''.join(canonical(r) for r in ledger))
    # Verify historical code directly without executing/importing it.
    revision=git('log','-1','--format=%H','--',CODE)
    historical=git('show',revision+':'+CODE)
    save('historical_code_provenance.json',{'commit':revision,'git_blob':git('rev-parse',revision+':'+CODE),
       'working_source_sha256':sha(ROOT/CODE),'historical_source_matches_working_tree':historical==(ROOT/CODE).read_text().strip(),
       'source_imported_or_executed':False})
    arc=load(A+'apachejit_archive_provenance.json')
    entry=next(r for r in arc['extracted_file_inventory'] if r['path']=='dataset/apachejit_total.csv')
    criteria={'A':{'status':'DIRECTLY_SUPPORTED','evidence_ids':['E01','E03','E10']},
      'B':{'status':'DIRECTLY_SUPPORTED','evidence_ids':['E02','E09','E11']},
      'C':{'status':'UNKNOWN','evidence_ids':['U01'],'reason':'Historical loader retains all columns and helper computes T2 class-support; no direct isolated routing proof.'},
      'D':{'status':'UNKNOWN','evidence_ids':['I01'],'reason':'No proof of content-independent error/stopping behavior, no-retention parser, ordering workspace and minimum-field acquisition under the no-label rule.'},
      'E':{'status':'DIRECTLY_SUPPORTED','evidence_ids':['E07','E08'],'scope':'Historical membership recipe known; new output digest defined prospectively, not an old full-row equivalence claim.'}}
    decision=decide(criteria,ledger)
    save('historical_partition_semantics_audit.json',{'criteria':criteria,'classification':decision,'amendment':'AMENDMENT_NOT_JUSTIFIED',
      'source_before_assignment':'YES_DIRECTLY_SUPPORTED','source_already_bound_before_creation':False,
      'canonical_mixed_exports_already_bound':True,'source_identity':{'path':'data/external/apachejit-v2/extracted/apachejit/dataset/apachejit_total.csv',
      'declared_sha256':entry['sha256'],'declared_bytes':entry['bytes'],'hash_basis':'INHERITED_ACQUISITION_PROVENANCE_NO_SOURCE_PAYLOAD_OPEN'},
      'critical_distinction':'Upstream predates original assignment, but membership is fixed now. Reopening upstream does not erase semantic membership or automatically relax current access policy.',
      'historical_T0_caveat':'Pre-predictive structural label checks are documented. This stage neither repeats them nor rewrites historical accounting.',
      'parent56_2A_outcome':'SAFE_TRAIN_T1_SOURCE_NOT_AVAILABLE_UNDER_CURRENT_T2_BOUNDARY'})
    save('partition_assignment_timeline.json',{'events':[
      {'sequence':1,'event':'External upstream source exists; original split differs from campaign split','evidence':['E01','E10']},
      {'sequence':2,'event':'Frozen candidate project set, UTC timestamps, repository/commit mapping available','evidence':['E01','E06']},
      {'sequence':3,'event':'Campaign TRAIN/VALIDATION/T1/T2 semantic labels assigned by ordinal function','evidence':['E02']},
      {'sequence':4,'event':'Structural support computed; derived identity digest generated; canonical partition records emitted','evidence':['E03','E04','E05']},
      {'sequence':5,'event':'Later confirmatory T1 completed, models frozen, reserve sealed; source audit failed','evidence_basis':'immutable parent outcome manifests'}],
      'row_identity_before_split':'project+commit identity exists; canonical repository resolution precedes split; final row_identifier SHA256 is computed after split, from partition-independent components.'})
    upstream_projects={r['project']:r['rows'] for r in load(A+'apachejit_original_contract.json')['projects']}
    membership=load(Q+'reconciliation_spec.json'); projects=[]
    for project in sorted({r['project'] for r in rows}):
        n=upstream_projects[project]
        cuts=[n*60//100,n*80//100,n*84//100]
        assert cuts[0]==membership['TRAIN'][project]['count']
        assert cuts[2]-cuts[1]==membership['T1'][project]['count']
        projects.append({'project':project,'upstream_project_count_metadata':n,'TRAIN_end_exclusive':cuts[0],
          'VALIDATION_end_exclusive':cuts[1],'T1_end_exclusive':cuts[2],
          'historical_TRAIN_membership_digest':membership['TRAIN'][project]['membership_digest'],
          'historical_T1_membership_digest':membership['T1'][project]['membership_digest'],
          'verification':'Ordinal counts match historical TRAIN/T1 metadata only; row identities/order not reread.'})
    save('frozen_partition_function_spec.json',{'status':'FROZEN_SPEC_ONLY_NOT_EXECUTABLE_ROUTER','source_sha256':sha(ROOT/CODE),
      'historical_commit':revision,'function':'_partition_rows assignment portion only, lines 311–342',
      'projects':projects,'project_set_fixed':True,'eligibility_reevaluation':'FORBIDDEN',
      'order':['raw author_date Unix seconds normalized UTC','commit_id lowercase full SHA ascending'],
      'sort':'project ASC, stable mergesort(timestamp_utc, commit_id)','duplicate_project_commit':'REJECT; historical source checked uniqueness before split',
      'boundaries':'zero-based i: i<floor(0.60*N) TRAIN; else i<floor(0.80*N) VALIDATION; else i<floor(0.84*N) T1; else T2',
      'boundary_dates':'NOT_INFERRED_OR_READ; ordinal boundaries are authoritative',
      'minimum_routing_fields':['project','author_date','commit_id'],
      'trusted_metadata_needed':['immutable upstream identity','frozen project whitelist and ordinal cutpoints','proof of source order or approved transient metadata sorting design'],
      'source_ordinal':'Original CSV index+2 is a source pointer, not chronological rank or byte offset.',
      'labels_needed_for_assignment':False,'physical_label_bytes_in_csv':'UNAVOIDABLE_WITH_HISTORICAL_FULL_ROW_LOADER; alternative field-reading proof UNKNOWN; NO AUTOMATIC APPROVAL',
      'model_predictions_probabilities_XAI_performance_dependencies':False,
      'historical_nonassignment_side_effects':['all-partition class-support aggregation','project eligibility checks'],
      'reuse_entire_historical_function':'PROHIBITED'})
    prohibited=['training','refitting','hyperparameter tuning','feature selection','algorithm selection','fusion selection','threshold selection',
      'calibration fitting','performance evaluation','statistical comparison','model ranking','SHAP','analytical attribution','interpretation',
      'local-case selection','global explanation','figure generation','methodological adaptation','stopping decisions','claim selection']
    save('t2_scientific_access_definition.json',{'status':'PROSPECTIVE_DEFINITION_NO_ACCESS_PERMISSION','uses':prohibited,
      'rule':'Any downstream T2 payload or T2-derived information used for these purposes increments T2_SCIENTIFIC_ACCESS_COUNT and is prohibited.',
      'existing_stricter_policy_still_effective':True,'payload_ever_untouched_claim':False})
    save('mechanical_routing_definition.json',{'status':'CONDITIONAL_PROPOSAL_NOT_ADOPTED','authorized':False,
      'definition':'Access immutable pre-partition source, assign frozen partition, retain only authorized TRAIN/T1, discard T2 before scientific code.',
      'requirements':['no retained T2 label/feature','no per-row T2 hash','no T2 identifiers/timestamps/logs','no T2 statistics/counts exported',
        'no downstream T2 scientific exposure','no T2 content-dependent scientific decision','no new partition/eligibility tuning'],
      'physical_bytes_vs_scientific_use':'Different concepts; historical source precedence supports discussion, not permission. Current physical-read prohibition remains.',
      'unavoidable_label_read_classification':'MECHANICAL_LABEL_BYTE_EXPOSURE_UNRESOLVED_REQUIRES_EXPLICIT_FUTURE_APPROVAL'})
    save('three_level_access_model.json',{'status':'CONDITIONAL_PROPOSAL_NOT_ADOPTED','levels':[
      {'level':0,'meaning':'Immutable pre-partition source container access','currently_authorized':False},
      {'level':1,'meaning':'Frozen deterministic partition routing','currently_authorized':False},
      {'level':2,'meaning':'Routed payload reaches scientific computation','T2':'DENIED'}],
      'no_retroactive_counter_reclassification':True})
    router_requirements=['approved upstream source only','minimum routing fields only','deterministic frozen assignment',
      'write authorized TRAIN only','write identity-only T1 only','DROP T2 immediately before downstream scientific boundary',
      'never expose T2 rows downstream','never serialize T2','never hash T2 rows','never compute T2 statistics',
      'never log T2 identity','never retain T2 labels/features','never invoke models','never invoke SHAP','never invoke metrics',
      'drop VALIDATION without scientific use','no eligibility recalculation','no content-derived errors or telemetry exposing reserve',
      'no T2-dependent methodological stopping or adaptation','no partial output promotion on failure']
    save('future_blind_router_contract.json',{'status':'PROPOSED_CONTRACT_ONLY','implementation_authorized':False,'execution_authorized':False,
      'requirements':router_requirements,'open_questions':['CSV field-byte isolation and quoted-record buffering',
        'Source order unproved; global/project ranking needs approved transient identity/order workspace or trusted exact cutpoint source',
        'No persistent T2 sorting spill, exception payload, tracing or per-row hash; prove erasure and scientific-code isolation',
        'Canonical repository mapping must match frozen identity without persisting reserve identities',
        'TRAIN feature/class decoding exactness and original numeric lexical provenance'],
      'historical_loader_approved':False,'proof_strategy_future_only':['static information-flow audit','synthetic canary fields and forbidden sinks',
        'crash/exception/log/spill inspection with invented rows','human review before any real container access'],
      'holdout_rationale':'No future T2 payload/statistic/outcome may affect scientific computation or choices; deterministic frozen assignment is necessary but not sufficient.',
      'historical_caveat':'Structural T0 class-support already occurred; do not claim reserve has never been structurally observed.'})
    for partition,fields in [('TRAIN',['project','partition','row_identifier','order_key','class',*C,*PROCESS]),('T1',['project','partition','row_identifier','order_key'])]:
        save('future_'+partition.lower()+'_output_contract.json',{'status':'PROSPECTIVE_ONLY','authorized':False,'partition':partition,
          'required_fields':fields,'additional_fields':False,'optional_fields':[],
          'identity':'SHA256 UTF8 apachejit-v2|project|canonical_repository|commit_sha',
          'order_key':['UTC ISO8601 seconds YYYY-MM-DDTHH:MM:SSZ','commit SHA'],
          'CODE':C if partition=='TRAIN' else [],'PROCESS':PROCESS if partition=='TRAIN' else [],
          'TEXT_linkage':'Separate authorized provenance must match frozen vocabulary/IDF/token order; no refitting or text source retrieval here.',
          'no_model_outputs_or_XAI':True,'T1_feature_resolution':'Only later separately governed XAI stage; forbidden in this output',
          'source_pointer':'If needed, separately governed sidecar before execution; no optional unreviewed fields admitted into canonical schema.'})
    save('t2_logging_prohibition.json',{'forbidden':['T2 row count','T2 class count','T2 prevalence','T2 timestamps','T2 identities',
      'T2 feature statistics','T2 hash ledger','T2 prediction values','T2 calibration values','T2 explanation values'],
      'allowed_governance_statement':'T2_LEVEL2_SCIENTIFIC_ACCESS_COUNT = 0','transient_discard_counter':'NO APPROVAL; explicit future human decision required'})
    save('partial_t2_consumption_policy.json',{'PARTIAL_T2_CONSUMPTION_POLICY':'REJECTED_WHILE_UPSTREAM_SOLUTION_REMAINS_POSSIBLE',
      'fraction_reclassified':0,'T2_STATE':'DENY_SEALED_REVIEWER_RESERVE',
      'reason':'Whole reserve already sealed; no post-T1 split into T2_XAI plus reserve.'})
    save('canonical_serialization_freeze.json',{'status':'PROSPECTIVELY_FROZEN_NO_SCIENTIFIC_ROW_HASHES_GENERATED',
      'encoding':'UTF-8 without BOM','key_order':'lexicographic Unicode key order via sort_keys=true; allowed keys fixed in output contracts',
      'string_encoding':'JSON ensure_ascii=true; no Unicode normalization; control characters JSON-escaped',
      'null':'JSON null reserved encoding; all required fields non-null, null input fails before output',
      'integers':'base-10 JSON number, no leading plus or zero padding; class integer 0 or 1, not bool',
      'floats':'CPython 3.11.14 json encoder shortest round-trip binary64 representation; preserve -0.0; allow_nan=false; no rounding, no tolerance matching',
      'numeric_type':'Preserve verified frozen per-column scalar type int vs binary64 float; do not coerce int to float. If type provenance absent, fail before materialization.',
      'whitespace':'separators comma and colon only; no spaces','newline':'one LF per canonical row including final row; empty population zero bytes',
      'row_order':'project-local chronological UTC Unix seconds then full commit SHA ASC; duplicate identities rejected',
      'hash':'SHA-256 of uncompressed concatenated canonical row bytes per project and partition',
      'compression':'If authorized gzip used, mtime=0, empty filename; logical SHA independent of container; exact runtime/compressor pinned before use',
      'historical_membership':'Preserve historical compact JSON ordered row-id LIST + terminal LF digest. Never replace with row-stream digest.',
      'schema_change_policy':'New version and human review before data; no recipe tuning to observed digest',
      'scope':'Recipe fully specified; exact per-column historical scalar type/source-value reconciliation remains a separate prerequisite.'})
    save('prospective_digest_policy.json',{'HISTORICAL_MEMBERSHIP_DIGEST':'existing frozen per-project ordered identity list digest, preserved unchanged',
      'S56_SAFE_SOURCE_CANONICAL_SHA256':'new future per-project partition minimal-row stream digest',
      'historical_row_digest_status':'HISTORICAL_ROW_DIGEST_RECIPE_UNAVAILABLE',
      'clarification':'Historical JSONL serialization is known. No historical digest of THIS minimal safe-source schema/value typing has been established. Do not equate container, membership, model state and new row hashes.',
      'digest_generated_this_stage':False,'recipe_chosen_without_future_row_output':True,'no_retrospective_hash_tuning':True,
      'historical_expected_full_row_hash_required':'Not invented; new digest records future reproducibility only. Historical feature equivalence requires independent source/schema/value provenance.'})
    save('future_safe_rematerialization_prerequisites.json',{'authorized':False,'resume_Sprint56_2':False,'Sprint56_3_authorized':False,
      'requirements':['Human review of insufficient C/D evidence and historical T0 caveat',
        'Direct independently auditable minimum-field routing/retention/isolation design, without using real T2 to prove it',
        'Explicit decision on unavoidable physical label/feature byte exposure; no implied approval',
        'Freeze exact parser/runtime, trusted order/cutpoint provenance, repository identity mapping and no-spill controls',
        'Independent TRAIN scalar type/value provenance and exact historical TRAIN/T1 membership reconciliation plan',
        'Pass synthetic isolation and noninterference tests before separate implementation/execution authorization',
        'Separate authorization for actual rematerialization; then human review before resumed56.2; separately authorize56.3'],
      'future_T1_explanation_rationale':'Completed historical T1 evaluation and frozen models allow consideration of post-hoc interpretation only: no refit, new metric, model selection or change to confirmatory claims. No T1 XAI authorized here.'})
    save('governance_counters.json',{**{k:0 for k in COUNTERS},'T2_STATE':'DENY_SEALED_REVIEWER_RESERVE',
      'future_rematerialization_authorized':False,'Sprint56_3_authorized':False,'counter_scope':'SPRINT56_2B_ONLY; historical counters unchanged'})
    save('scope_integrity.json',{'count':389,'E1':168,'E2':221,'excluded':scopes['excluded_scopes'],
      'scope_ledger_sha256':sha(ROOT/P/'primary_xai_scope_ledger.jsonl'),'selection_changed':False})
    finalize()

def finalize():
    sys.addaudithook(guard)
    before=json.loads((OUT/'parent_integrity_before.json').read_text()); after=snapshot()
    if before!=after: raise ValueError('Parent integrity changed')
    save('parent_integrity_after.json',after)
    save('implementation_provenance.json',{'source_sha256':sha(Path(__file__)),
      'test_sha256':sha(ROOT/'tests/evaluation/test_q1_primary_xai_t2_semantic_boundary.py') if (ROOT/'tests/evaluation/test_q1_primary_xai_t2_semantic_boundary.py').exists() else None,
      'router_implemented':False,'metadata_only':True})
    previous=json.loads((OUT/'read_access_log.json').read_text())['paths'] if (OUT/'read_access_log.json').exists() else []
    save('read_access_log.json',{'paths':sorted(READS|set(previous)),'scientific_payload_opens':0,'guard':'Allowlisted metadata/code only; model objects denied'})
    decision=json.loads((OUT/'historical_partition_semantics_audit.json').read_text())
    validations=json.loads((OUT/'validation_results.json').read_text()) if (OUT/'validation_results.json').exists() else {'status':'PENDING'}
    sections=[('A. Branch',BRANCH),('B. HEAD',git('rev-parse','HEAD')),
      ('C. Sprint56.1','PRIMARY_XAI_ISOLATED_RUNTIME_SMOKE_TEST_PASS'),('D. Sprint56.2','PRIMARY_XAI_T1_SELECTION_CONTRACT_FAILURE'),
      ('E. Sprint56.2A','SAFE_TRAIN_T1_SOURCE_NOT_AVAILABLE_UNDER_CURRENT_T2_BOUNDARY; 113 candidates, zero accepted.'),
      ('F. Universe','389 eligible scopes, E1=168/E2=221; exactly zeppelin LR C+T, P+T, C+P+T excluded. scope_integrity.json binds parent hash.'),
      ('G. Parent hashes','Before/after snapshots agree. Fresh SHA256 covers allowed parent metadata and source; scientific payload digests are inherited with unchanged stat records, not represented as fresh byte verification. All 5,649 objects preserved by stat comparison and inherited56.2A integrity; no model bytes opened.'),
      ('H. Upstream identity','Immutable acquisition-provenance total.csv predates campaign partition assignment. Canonical mixed gzip exports are downstream, already partition-bound, and cannot be reinterpreted as pre-partition sources.'),
      ('I. Source-before-partition','YES: E01/E03/E10 directly establish read of upstream, pending partition contract, then assignment. Source age does not reset membership already frozen today.'),
      ('J. Code/provenance','Exact excerpts and hashes in evidence_classification_ledger.jsonl. Historical Git code equality recorded. E02 isolates assignment; E04/E05 show prohibited aggregation/eligibility side effects.'),
      ('K. Timing','Existing project/commit and repository resolution precede split; final row_identifier hash is constructed AFTER split from partition-independent components. Do not claim the stored hash itself was already materialized earlier.'),
      ('L. Frozen function','Project-local stable UTC/SHA chronology; floor(60*N/100), floor(80*N/100), floor(84*N/100). All 14 project ordinal boundaries reconciled with existing TRAIN/T1 count metadata, without partition rows or T2 counts.'),
      ('M. Determinism','Assignment has no prediction/probability/XAI/performance input. Source project+SHA uniqueness and stable ties are explicit. Historical eligibility does use structural label support; future rerouting must NEVER rerun it.'),
      ('N. Scientific access','Any downstream reserve information used in training, selection, evaluation, interpretation, methodological/stopping/claim decisions remains prohibited. Existing stricter physical-access boundary remains effective.'),
      ('O. Mechanical routing','Conditional proposal only, not adopted. Immutable-source routing must discard T2 without downstream exposure. Unavoidable label bytes are unresolved, not automatically exempted.'),
      ('P. Three levels','L0 container, L1 deterministic routing, L2 scientific exposure. L0/L1 currently unauthorized; T2 L2 DENIED. No historical counter reclassification.'),
      ('Q. Feasibility','NOT DEMONSTRATED by direct evidence. Historical pd.read_csv loads full rows; _partition_rows also computes T2 class support. Minimum-field parser, transient ordering workspace, exact repository identity, no-spill/no-logging and content-independent failure handling remain unproved. A hypothetical new router is DERIVED_INFERENCE, not approval evidence.'),
      ('R. Logging','No T2 count, class, prevalence, timestamp, identity, feature statistic, row hash or output ledger. Only zero scientific-access governance assertions. Even transient operational counters need separate approval.'),
      ('S. TRAIN output','Proposed minimal identity/order/class and 6 CODE+6 PROCESS fields; exact original scalar/value provenance required; no model or XAI output. TEXT linkage must preserve frozen representation, not rebuild it.'),
      ('T. T1 output','Proposed project/partition/row_identifier/order_key only. No labels, features or predictions. Post-hoc explanation rationale requires frozen models, no metrics/selection/refit and separate authorization.'),
      ('U. Partial reserve','REJECTED_WHILE_UPSTREAM_SOLUTION_REMAINS_POSSIBLE. Whole T2 stays DENY_SEALED_REVIEWER_RESERVE; no fraction consumed.'),
      ('V. Serialization','Prospective UTF8, fixed allowed schema, lexicographic keys, JSON exact scalar policies, UTC/SHA row order, LF, no NaN/null required values, SHA256 over uncompressed canonical content. No scientific row hashes generated.'),
      ('W. Digests','HISTORICAL_MEMBERSHIP_DIGEST remains the ordered-list digest. S56_SAFE_SOURCE_CANONICAL_SHA256 is a distinct future row-stream digest. Historical minimal-row digest unavailable; no invented expected hash and no retrospective tuning.'),
      ('X. Counters/tests','All current scientific read/inference/XAI/metric/refit/reconstruction/recalibration/figure and routing/rematerialization counters are zero. '+json.dumps(validations,sort_keys=True)),
      ('Y. Decision',decision['classification']+' / AMENDMENT_NOT_JUSTIFIED. A/B/E supported; C/D remain UNKNOWN. This is insufficient evidence, not a finding that the upstream source was created after campaign T2 assignment. Historical T0 structural support prevents a claim of never-observed labels.'),
      ('Z. Human decision','Review the unmet isolation/noninterference requirements and historical T0 caveat. A separate prospective review may establish direct design evidence and explicitly decide unavoidable byte exposure. No automatic boundary amendment, router implementation, rematerialization, resumed56.2 or56.3 is authorized.')]
    report='# Sprint 56.2B — Prospective T2 semantic boundary review\n\nT2_SEMANTIC_BOUNDARY_EVIDENCE_INSUFFICIENT\n\nAMENDMENT_NOT_JUSTIFIED\n\n'
    report+='\n\n'.join('## '+title+'\n\n'+body for title,body in sections)
    report+='\n\nT2_SEMANTIC_BOUNDARY_AMENDMENT_NOT_JUSTIFIED\n\nREADY FOR HUMAN REVIEW — DO NOT REMATERIALIZE OR START SPRINT 56.3\n'
    (OUT/'SPRINT56_2B_T2_SEMANTIC_BOUNDARY_REPORT.md').write_text(report)
    manifest()
    print(decision['classification'])

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('stage',choices=['build','finalize','manifest'])
    {'build':build,'finalize':finalize,'manifest':manifest}[p.parse_args().stage]()
