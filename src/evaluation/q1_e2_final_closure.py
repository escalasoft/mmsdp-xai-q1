"""Frozen-state, OOF-centered E2 only. No estimator prediction/fit is called."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import gzip
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import platform
import struct
import subprocess
import sys
import tempfile

import joblib
import numpy as np
import pandas as pd
from scipy.special import expit

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'audits/q1-e2-final-closure/1.1.0'
FG = ROOT/'audits/q1-e2-t1-foreground-freeze/1.0.0'
OLD = ROOT/'audits/q1-e2-final-closure/1.0.0'
READY = ROOT/'audits/q1-primary-xai-e1-input-e2-reference-resolution/1.0.0'
POP = ROOT/'audits/q1-primary-xai-population-freeze/1.0.0'
STORE = ROOT/'audits/q1-xai-reconstruction-execution/1.0.0'
REUSE = ROOT/'audits/q1-primary-xai-frozen-evidence-reuse/1.0.0'
SOURCE = ROOT/'audits/q1-t1-confirmatory-execution/1.0.0/results/t1_prediction_evidence.jsonl.gz'
FIDELITY = ROOT/'audits/q1-primary-xai-missing-evidence-remediation/1.0.0/fidelity_execution_contract.json'
BRANCH = 'sprint-10/q1-e2-final-closure'
CONFIGS = ['C+P','C+T','P+T','C+P+T']
COUNTS = {'C+P':56,'C+T':55,'P+T':55,'C+P+T':55}
NAMES = {'C':'CODE','P':'PROCESS','T':'TEXT'}
LOGIT_TOL = 1e-10
PROB_TOL = 1e-10
GLOBAL_TOL = 1e-12
COUNTERS = dict.fromkeys(['T2_scientific_access_count','E1_reexecution_count',
    'model_retraining_count','calibration_refit_count','predictive_recomputation_count'],0)
INPUT_HASHES = {}
READ_LOG = set()


class ClosureError(RuntimeError):
    pass


def require(ok, message):
    if not ok:
        raise ClosureError(message)


def canonical(value):
    return (json.dumps(value,sort_keys=True,ensure_ascii=True,separators=(',',':'),allow_nan=False)+'\n').encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for b in iter(lambda:stream.read(1048576),b''):
            h.update(b)
    return h.hexdigest()


def rel(path):
    return str(Path(path).relative_to(ROOT))


def checked(path, expected=None):
    path=Path(path)
    actual=sha(path)
    if expected is not None:
        require(actual==expected,'Frozen hash mismatch: '+rel(path))
    INPUT_HASHES[rel(path)]=actual
    return path


def read(path):
    return json.loads(checked(path).read_text())


def rows(path):
    return [json.loads(l) for l in checked(path).read_text().splitlines() if l.strip()]


def save(path,value):
    Path(path).write_bytes(canonical(value))


def verify_package(base):
    for line in checked(base/'MANIFEST.sha256').read_text().splitlines():
        expected,name=line.split('  ',1)
        p=(base/name).resolve()
        require(p.is_relative_to(base.resolve()),'Manifest path escape')
        checked(p,expected)


def check_named(path, base=None):
    base=base or path.parent
    entries={n:h for h,n in (l.split('  ',1) for l in (base/'MANIFEST.sha256').read_text().splitlines())}
    checked(path,entries[str(path.relative_to(base))])


def key(r):
    return r['project'],r['algorithm'],r['configuration']


def eligible(scopes,ledger):
    require(len(scopes)==221 and len({key(r) for r in scopes})==221,'E2 scope count/duplicates')
    require(dict(Counter(r['configuration'] for r in scopes))==COUNTS,'E2 eligibility counts changed')
    old={key(r):r['model_identity_sha256'] for r in ledger if r['role']=='E2'}
    require(old=={key(r):r['model_identity_sha256'] for r in scopes},'E2 scope identity conflict')


def ordered_means(scope, means):
    result=[]
    require(scope['primary_reference_status']=='PRIMARY_REFERENCE_OOF','Wrong reference regime')
    for mod in scope['modality_order']:
        k=(scope['project'],scope['algorithm'],mod)
        require(k in means,'Missing OOF mean')
        r=means[k]
        require(r['source_partition']=='TRAIN_META_OOF' and r['primary_reference']=='PRIMARY_REFERENCE_OOF','Invalid OOF regime')
        require(r['ordered_identity_digest']==scope['meta_training_membership_sha256'],'OOF membership mismatch')
        require(float(r['mu']).hex()==r['mu_hex'],'OOF mean representation mismatch')
        require(hashlib.sha256(struct.pack('<d',r['mu'])).hexdigest()==r['mean_sha256'],'OOF scalar hash mismatch')
        require(r in scope['primary_mean_records'],'Readiness mean differs from resolved mean ledger')
        result.append(r['mu'])
    return np.asarray(result,dtype='<f8')


def decompose(probabilities,beta,alpha,mu):
    p=np.asarray(probabilities,dtype='<f8')
    require(p.ndim==2 and p.shape[1]==len(beta)==len(mu),'Modality dimension/order mismatch')
    require(np.isfinite(p).all() and ((p>=0)&(p<=1)).all(),'Invalid frozen probability')
    phi0=float(alpha+np.dot(beta,mu))
    phi=(p-mu)*beta
    eta=phi0+phi.sum(axis=1)
    # Direct, uncentered frozen-state algebra is the independent logit reference.
    # Source ledger persists RAW probabilities, not a separate meta-logit column.
    z=alpha+p@beta
    probability=expit(eta)
    require(np.isfinite(phi).all() and np.isfinite(eta).all(),'Nonfinite E2 output')
    return phi0,phi,eta,z,probability


def guard_worker(destination, scientific_paths):
    allowed={Path(p).resolve() for p in scientific_paths}
    def guard(event,args):
        if event!='open' or not isinstance(args[0],(str,bytes,os.PathLike)):
            return
        p=Path(os.fsdecode(args[0])).resolve()
        mode,flags=args[1] or '',args[2] or 0
        writing=any(c in mode for c in 'wax+') or bool(flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC))
        if writing:
            require(p.is_relative_to(destination.resolve()),'Scientific worker write outside its isolated output')
        elif any(p.is_relative_to(ROOT/x) for x in ['audits','data','artifacts','outputs']):
            require(p in allowed,'Unapproved scientific payload: '+str(p))
            READ_LOG.add(rel(p))
    sys.addaudithook(guard)


def load_context():
    # Only known governance before installing exact-payload allowlist.
    verify_package(FG)
    verify_package(OLD)
    needed=[READY/'e2_fusion_decomposition_readiness.json',READY/'e2_reference_means.jsonl',
        POP/'primary_xai_scope_ledger.jsonl',FIDELITY,REUSE/'t1_evidence_inventory.jsonl',
        REUSE/'row_identity_reconciliation.json']
    for p in needed:
        check_named(p)
    journal_path=STORE/'repetitions/rep_01/component_journal.jsonl'
    check_named(journal_path,STORE)
    scopes=read(READY/'e2_fusion_decomposition_readiness.json')['scopes']
    ledger=rows(POP/'primary_xai_scope_ledger.jsonl')
    eligible(scopes,ledger)
    manifest=read(FG/'population_manifest.json')
    require(manifest['status']=='E2_T1_FOREGROUND_FREEZE_PASS','Foreground not frozen')
    require(manifest['eligible_scopes']==221 and manifest['eligible_configuration_counts']==COUNTS,'Foreground eligibility conflict')
    require({(r['project'],r['algorithm'],r['configuration'],r['model_identity_sha256']) for r in manifest['eligible_scope_identities']}==
            {(*key(r),r['model_identity_sha256']) for r in scopes},'Frozen foreground model identity conflict')
    source=rows(REUSE/'t1_evidence_inventory.jsonl')[0]
    require(source['path']==rel(SOURCE) and source['partition_provenance']=='T1_ONLY_FROZEN_SPRINT54','Unproved T1 source')
    require(manifest['source_T1_artifact']['sha256']==source['sha256'],'Foreground/source linkage mismatch')
    contract=read(FIDELITY)['LR_fusion']
    require(contract=={'absolute_residual_bound':'1e-10*(1+abs(eta))','identity':'eta=intercept+sum(contributions)','sigmoid_absolute_bound':1e-10},'Fidelity contract changed')
    means_list=rows(READY/'e2_reference_means.jsonl')
    means={(r['project'],r['algorithm'],r['modality']):r for r in means_list}
    require(len(means)==len(means_list)==168,'Duplicate/missing reference means')
    journal={r['logical_id']:r for r in rows(journal_path)}
    return scopes,ledger,manifest,source,means,journal


def compute(destination):
    scopes,ledger,manifest,source,means,journal=load_context()
    models=[STORE/s['meta_state']['path'] for s in scopes]
    oof=[ROOT/r['source_path'] for r in means.values()]
    guard_worker(destination,[ROOT/p for p in INPUT_HASHES]+[SOURCE]+models+oof)
    for r in means.values():
        path=ROOT/r['source_path']
        if rel(path) not in INPUT_HASHES:
            checked(path,r['source_sha256'])  # Hash only; resolved means are never recomputed.
    fg=rows(FG/'t1_global_foreground_population.jsonl')
    local=rows(FG/'t1_local_case_population.jsonl')
    require(all(r['partition']=='T1' for r in fg+local),'T2/non-T1 foreground rejected')
    foreground=defaultdict(list)
    for r in fg:
        foreground[r['project']].append(r['row_identifier'])
    require(len(fg)==manifest['global_rows'] and len(local)==manifest['local_scope_rows'],'Frozen foreground count mismatch')
    scope_map={key(r):r for r in ledger}
    wanted={p:set(ids) for p,ids in foreground.items()}
    # Obtain only foreground probabilities; no other T1 row is used for E2.
    predictions={}
    checked(SOURCE,source['sha256'])
    with gzip.open(SOURCE,'rt',encoding='utf-8') as stream:
        for line in stream:
            r=json.loads(line)
            if r['row_identifier'] not in wanted.get(r['project'],set()):
                continue
            k=key(r)
            if k not in scope_map:
                continue
            require(r['model_identity_sha256']==scope_map[k]['model_identity_sha256'],'Frozen probability identity mismatch')
            rk=(*k,r['row_identifier'])
            require(rk not in predictions,'Duplicate frozen probability row')
            predictions[rk]=float(r['raw_predicted_probability'])
            # No label, calibrated probability, threshold, confidence or correctness field accessed.
    records=[]
    fidelity=[]
    scope_inputs=[]
    for scope in sorted(scopes,key=key):
        project,algorithm,configuration=key(scope)
        order=scope['modality_order']
        j=journal[f'{project}|{algorithm}|FUSION_META|{configuration}']
        state=j['canonical_state']
        require(digest(state)==j['canonical_state_sha256']==scope['meta_canonical_state_sha256'],'Canonical state mismatch')
        require(state['provenance']['modality_order']==order and order==configuration.split('+'),'Modality order conflict')
        require(state['provenance']['model_identity_sha256']==scope['model_identity_sha256'],'Meta-model identity mismatch')
        require(j['executable']==scope['meta_state'],'Frozen executable reference mismatch')
        model=joblib.load(checked(STORE/scope['meta_state']['path'],scope['meta_state']['sha256']))
        require(type(model).__name__=='LogisticRegression' and model.classes_.tolist()==[0,1],'Wrong frozen fusion model')
        for attr,name in [('coef_','coef'),('intercept_','intercept')]:
            a=np.asarray(getattr(model,attr))
            require(list(a.shape)==state[name]['shape'] and a.dtype.str==state[name]['dtype']
                    and hashlib.sha256(a.tobytes()).hexdigest()==state[name]['sha256'],'Frozen coefficient mismatch')
        beta=np.asarray(model.coef_[0],dtype='<f8')
        alpha=float(model.intercept_[0])
        mu=ordered_means(scope,means)
        ids=foreground[project]
        try:
            p=np.array([[predictions[(project,algorithm,m,rid)] for m in order] for rid in ids],dtype='<f8')
            frozen=np.array([predictions[(project,algorithm,configuration,rid)] for rid in ids],dtype='<f8')
        except KeyError as e:
            raise ClosureError('Missing frozen foreground probability') from e
        phi0,phi,eta,z,prob=decompose(p,beta,alpha,mu)
        lr=np.abs(eta-z)
        pr=np.abs(prob-frozen)
        fails=(lr>LOGIT_TOL*(1+np.abs(z)))|(pr>PROB_TOL)
        global_res=float(abs(np.mean(eta)-np.mean(z)))
        f=dict(project=project,model_family=algorithm,configuration=configuration,rows_checked=len(ids),
               max_logit_residual=float(lr.max()),mean_logit_residual=float(lr.mean()),
               max_probability_residual=float(pr.max()),mean_probability_residual=float(pr.mean()),
               failures=int(fails.sum()),global_mean_logit_residual=global_res,
               global_reconstruction_pass=global_res<=GLOBAL_TOL)
        fidelity.append(f)
        if fails.any() or global_res>GLOBAL_TOL:
            save(destination/'fidelity_failure.json',f)
            raise ClosureError('Unexplained fidelity failure; tolerances unchanged: '+str(key(scope)))
        scope_inputs.append(dict(project=project,model_family=algorithm,configuration=configuration,
            model_identity_sha256=scope['model_identity_sha256'],modality_order=order,
            model_path=rel(STORE/scope['meta_state']['path']),model_sha256=scope['meta_state']['sha256'],
            alpha=alpha,beta=beta.tolist(),mu=mu.tolist(),phi0=phi0,
            foreground_ordering_hash=digest(ids),reference='PRIMARY_REFERENCE_OOF'))
        for i,rid in enumerate(ids):
            rec=dict(project=project,model_family=algorithm,configuration=configuration,row_identifier=rid,
                     partition='T1',model_identity_sha256=scope['model_identity_sha256'],foreground_ordinal=i+1,
                     alpha=alpha,phi0=phi0,reconstructed_meta_logit=float(eta[i]),frozen_state_meta_logit=float(z[i]),
                     reconstructed_RAW_probability=float(prob[i]),frozen_RAW_probability=float(frozen[i]),
                     logit_residual=float(lr[i]),probability_residual=float(pr[i]))
            for ix,mod in enumerate(order):
                for name,val in [('probability',p[i,ix]),('beta',beta[ix]),('OOF_mu',mu[ix]),('phi',phi[i,ix])]:
                    rec[f'{NAMES[mod]}_{name}']=float(val)
            records.append(rec)
    df=pd.DataFrame(records)
    require(len(df)==manifest['global_scope_rows'],'E2 output population count mismatch')
    payload=df.to_csv(index=False,float_format='%.17g').encode()
    with (destination/'e2_attributions.csv.gz').open('wb') as raw:
        with gzip.GzipFile(filename='',fileobj=raw,mode='wb',mtime=0) as compressed:
            compressed.write(payload)
    pd.DataFrame(fidelity).to_csv(destination/'e2_fidelity_summary.csv',index=False,float_format='%.17g')
    local_index={(r['project'],r['algorithm'],r['configuration'],r['row_identifier']):r for r in local}
    local_records=[]
    for r in records:
        k=(r['project'],r['model_family'],r['configuration'],r['row_identifier'])
        if k in local_index:
            local_records.append({**r,'local_ordinal':local_index[k]['ordinal'],
                                  'local_selection_key':local_index[k]['selection_key']})
    require(len(local_records)==len(local_index)==len(local),'Local frozen population mismatch')
    pd.DataFrame(local_records).to_csv(destination/'e2_local_cases.csv',index=False,float_format='%.17g')
    save(destination/'scope_input_provenance.json',scope_inputs)
    checked(SOURCE,source['sha256'])
    for path,expected in list(INPUT_HASHES.items()):
        require(sha(ROOT/path)==expected,'Input changed during E2: '+path)
    save(destination/'worker_provenance.json',dict(input_hashes=INPUT_HASHES,read_access_log=sorted(READ_LOG),
        rows=len(df),scopes=len(scopes),local_rows=len(local_records),
        attribution_uncompressed_sha256=hashlib.sha256(payload).hexdigest(),
        logit_reference='Direct alpha + P @ beta using frozen LR coefficients and frozen RAW base probabilities; no separately persisted logit field is claimed.',
        model_prediction_calls=0,model_fit_calls=0,counters=COUNTERS))


def aggregate(out):
    df=pd.read_csv(out/'e2_attributions.csv.gz',float_precision='round_trip')
    long=[]
    for mod in NAMES.values():
        s=df[['project','model_family','configuration',f'{mod}_phi']].dropna().rename(columns={f'{mod}_phi':'phi'})
        s['modality']=mod
        long.append(s)
    long=pd.concat(long,ignore_index=True)
    summaries=[]
    for level,groups in [('configuration',['configuration','modality']),
                         ('configuration_model',['configuration','model_family','modality']),
                         ('scope',['project','configuration','model_family','modality'])]:
        for keys,g in long.groupby(groups,sort=True):
            v=g.phi.to_numpy();a=np.abs(v)
            summaries.append(dict(grouping=level,**dict(zip(groups,keys)),n=len(v),
                mean_phi=float(v.mean()),median_phi=float(np.median(v)),mean_abs_phi=float(a.mean()),
                median_abs_phi=float(np.median(a)),q10_phi=float(np.quantile(v,.1)),q90_phi=float(np.quantile(v,.9)),
                q10_abs_phi=float(np.quantile(a,.1)),q90_abs_phi=float(np.quantile(a,.9)),
                positive_proportion=float(np.mean(v>0)),negative_proportion=float(np.mean(v<0)),zero_proportion=float(np.mean(v==0))))
    summary=pd.DataFrame(summaries)
    summary.to_csv(out/'e2_global_summary.csv',index=False,float_format='%.17g')
    fd=out/'figure_data';fd.mkdir()
    summary[summary.grouping=='scope'].to_csv(fd/'E2_global_modality_contributions.csv',index=False,float_format='%.17g')
    local=pd.read_csv(out/'e2_local_cases.csv',float_precision='round_trip')
    # Declared before computation: one frozen ordinal-1 case per configuration,
    # using lexicographically first eligible project/model scope. No magnitude use.
    selected=local[local.local_ordinal==1].sort_values(['configuration','project','model_family']).groupby('configuration',sort=True).head(1)
    require(len(selected)==4,'Publication local panel missing configuration')
    selected.to_csv(fd/'E2_local_meta_logit_decomposition.csv',index=False,float_format='%.17g')
    return df,summary


def finalize(out,baseline,discovery,repeats):
    df,summary=aggregate(out)
    f=pd.read_csv(out/'e2_fidelity_summary.csv',float_precision='round_trip')
    worker=read(out/'worker_provenance.json')
    save(out/'e2_discovery_inventory.json',discovery)
    save(out/'e2_eligibility_summary.json',dict(eligible_scopes=221,configuration_counts=COUNTS,
        global_unique_project_rows=2450,scope_rows_explained=len(df),local_scope_rows=1768,
        exclusions=[['apache/zeppelin','Logistic Regression',c] for c in ['C+T','P+T','C+P+T']],
        foreground_package=rel(FG),no_population_reselection=True))
    save(out/'e2_reproducibility_report.json',dict(status='PASS',independent_executions=2,
        binary_identical=True,differing_rows=0,maximum_numeric_difference=0,outputs=repeats,
        comparison='Exact bytes of deterministic gzip CSV, fidelity CSV, local CSV, input provenance and worker provenance; both workers reload inputs in fresh processes.',
        numerical_environment=runtime(),no_seeds_or_retraining=True))
    save(out/'e2_t2_non_access_report.json',dict(scientific_T2_access_count=0,scientific_T2_access_log=[],
        counters=COUNTERS,worker_read_allowlist_enforced=True,read_access_log=worker['read_access_log'],
        T1_transport='Only the hash-verified T1-only ledger; only frozen foreground RAW probabilities enter computation. Labels and calibration outputs are unused.',
        discovery_boundary='Filename search and selected governance/code only; no mixed or T2 scientific payload opened.'))
    save(out/'e2_publication_claims.json',dict(
        SUPPORTED_CLAIMS=[f'E2 explains {len(df)} frozen T1 scope-row observations over 221 multimodal scopes.',
            'Centered modality terms reconstruct the frozen-state LR fusion logit and its frozen RAW probability within predeclared bounds.',
            'Two independent executions produce byte-identical E2 numeric artifacts.'],
        BOUNDED_CLAIMS=['Signed terms indicate movement relative to historical OOF contributions; absolute terms quantify model-score magnitude, not causal importance.',
            'Reference means describe historical meta-training, not deployed-model full-TRAIN behavior.',
            'Patterns and comparisons are conditional on project, model family, configuration and the bounded T1 foreground.',
            'Local panels are deterministic illustrations from the frozen local population; they are not error-stratified or claims of statistical representativeness.',
            'E1 remains bounded complementary evidence with unchanged inclusion/exclusion decisions.'],
        PROHIBITED_CLAIMS=['Causal modality or feature claims','Universal modality superiority','E2 improves predictive performance',
            'E2 validates human usefulness, developer behavior, organizational impact or user acceptance',
            'E1 generalizes beyond its frozen scope','Claims based on T2','Changes to MIXED_CONFIRMATORY_EVIDENCE',
            'Local examples selected as TP/TN/FP/FN','A separately persisted meta-logit column existed in the T1 source']))
    save(out/'e2_execution_manifest.json',dict(status='E2_FINAL_CLOSURE_PASS',starting_context=baseline,
        timestamp_UTC=datetime.now(timezone.utc).isoformat(),runtime=runtime(),input_hashes=worker['input_hashes'],
        output_hash_convention='MANIFEST.sha256 records every output except itself; execution manifest does not recursively hash itself.',
        eligible_scope_counts=COUNTS,T1_scope_rows=len(df),T1_unique_project_rows=2450,
        counters=COUNTERS,model_predict_calls=0,attribution_executions=2,
        logit_reference=worker['logit_reference'],reference='PRIMARY_REFERENCE_OOF',
        numerical_tolerances=dict(logit='1e-10*(1+abs(frozen_state_meta_logit))',probability=PROB_TOL,global_mean_logit=GLOBAL_TOL),
        fidelity=dict(rows_checked=len(df),maximum_logit_residual=float(df.logit_residual.max()),
            mean_logit_residual=float(df.logit_residual.mean()),maximum_probability_residual=float(df.probability_residual.max()),
            mean_probability_residual=float(df.probability_residual.mean()),rows_outside_tolerance=int(f.failures.sum()),scopes_affected=[]),
        implementation_sha256=sha(Path(__file__)),frozen_artifacts_changed=False,
        prior_diagnostic_preserved=rel(OLD),population_freeze_preserved=rel(FG)))
    # Figures and final narrative are completed only after successful numerical closure.
    print('NUMERIC_E2_PASS',len(df),float(df.probability_residual.max()))


def runtime():
    return dict(python=platform.python_version(),platform=platform.platform(),
        packages={p:importlib.metadata.version(p) for p in ['numpy','scipy','pandas','joblib','scikit-learn']},
        thread_controls={p:os.environ.get(p) for p in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','VECLIB_MAXIMUM_THREADS']})


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--worker',type=Path);args=parser.parse_args()
    if args.worker:
        compute(args.worker);return
    git=lambda *args:subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()
    require(git('symbolic-ref','--short','HEAD')==BRANCH,'Wrong branch')
    require(Path(git('rev-parse','--show-toplevel'))==ROOT,'Wrong repository')
    require(not OUT.exists(),'Prior closure package must never be overwritten')
    baseline=dict(repository=str(ROOT),branch=BRANCH,HEAD=git('rev-parse','HEAD'),working_tree=git('status','--porcelain=v1'),
        resumed_authorized_work=True,original_task_start_HEAD='77c1af5d59ee7af6257f67ce17d06968ef78a416',original_task_start_working_tree='clean')
    names=subprocess.check_output(['rg','--files','--hidden','--no-ignore','-g','!.git/**','-g','!.venv/**','-g','!.venv-xai-s56/**','-g','!**/__pycache__/**'],cwd=ROOT,text=True).splitlines()
    discovery=dict(prior_diagnostic=rel(OLD),resolved_prerequisite=rel(FG),
        search='Complete repository filename inventory excluding Git internals, environments and bytecode; prior forensic evidence reused.',
        candidate_paths=[n for n in names if any(w in Path(n).name.lower() for w in ['e2','foreground','fusion','oof','meta','fidelity','attribution','closure'])],
        later_valid_final_E2_execution_found=False,prior_fail_closed_preserved=True)
    OUT.mkdir(parents=True)
    save(OUT/'pre_execution_policy.json',dict(status='FROZEN_BEFORE_ATTRIBUTION',reference='PRIMARY_REFERENCE_OOF',
        foreground=rel(FG),logit_tolerance='1e-10*(1+abs(frozen_state_meta_logit))',probability_tolerance=PROB_TOL,
        global_mean_logit_tolerance=GLOBAL_TOL,repetitions=2,
        local_table='All 1768 frozen local scope-rows, no selection change',
        local_figure='For each configuration use frozen local ordinal 1 in the lexicographically first eligible (project, algorithm) scope.',
        no_labels_or_confidence=True,logit_reference='Independent uncentered frozen-state algebra, not an invented persisted source field'))
    try:
        with tempfile.TemporaryDirectory(prefix='e2-attribution-') as tmp:
            repdirs=[]
            for i in [1,2]:
                dest=Path(tmp)/str(i);dest.mkdir();repdirs.append(dest)
                subprocess.run([sys.executable,'-m','src.evaluation.q1_e2_final_closure','--worker',str(dest)],cwd=ROOT,check=True,
                    env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
            require({p.name for p in repdirs[0].iterdir()}=={p.name for p in repdirs[1].iterdir()},'Repeat file mismatch')
            repeats={}
            for p in sorted(repdirs[0].iterdir()):
                h=sha(p);other=sha(repdirs[1]/p.name)
                require(h==other,'Attribution reproducibility failed: '+p.name)
                repeats[p.name]=[h,other]
                (OUT/p.name).write_bytes(p.read_bytes())
        finalize(OUT,baseline,discovery,repeats)
    except Exception as exc:
        save(OUT/'fail_closed.json',dict(status='E2_FINAL_CLOSURE_FAIL_CLOSED',reason=str(exc),counters=COUNTERS))
        raise


if __name__=='__main__':
    main()
