"""Single-use Route B release. Production entry requires a future approval file.

No production approval is distributed with this module. Trusted local operation,
not a signature system or OS sandbox. Synthetic entry exercises the same engine.
"""
from __future__ import annotations
import base64
import dataclasses
from datetime import datetime, timezone
import errno
import json
import os
from pathlib import Path
import platform
import stat
import subprocess
import sys
import zlib
from . import e1_code_candidate as c
from . import e1_code_coordinator as k

AUDIT = k.REPO / 'audits/q1-e1-code-coordinator/1.1.0'
CODE = ('src/governance/e1_code_candidate.py','src/governance/e1_code_coordinator.py',
        'src/governance/e1_code_release.py','src/governance/e1_code_release_worker.py')


@dataclasses.dataclass(frozen=True)
class Outcome:
    status: str
    reason: str
    accepted: bool = False


class Stop(Exception):
    def __init__(self, status, reason):
        self.status, self.reason = status, reason


def reject(ok, reason):
    if not ok: raise Stop('FAIL', reason)


def classify(exc):
    if isinstance(exc, Stop): return Outcome(exc.status, exc.reason)
    if isinstance(exc, (KeyboardInterrupt, SystemExit, MemoryError, subprocess.TimeoutExpired)):
        return Outcome('INCONCLUSIVE', 'INTERRUPTION_OR_RESOURCE')
    if isinstance(exc, c.Rejected):
        changed = exc.args and exc.args[0] in {'SOURCE_CHANGED','SOURCE_CHANGED_AFTER_CAPTURE','LOCK_CHANGED'}
        return Outcome('INCONCLUSIVE' if changed else 'FAIL',
                       'CONCURRENT_CHANGE' if changed else 'VALIDATION_REJECTED')
    if isinstance(exc, (json.JSONDecodeError, ValueError, TypeError, KeyError)):
        return Outcome('FAIL', 'INVALID_STRUCTURE')
    if isinstance(exc, OSError):
        if exc.errno in {errno.ENOSPC, errno.ENOMEM, errno.EINTR, errno.EAGAIN}:
            return Outcome('INCONCLUSIVE','RESOURCE_OR_CONCURRENCY')
        return Outcome('INCONCLUSIVE','IO_UNCERTAIN')
    return Outcome('INCONCLUSIVE', 'UNEXPECTED_STATE')


def metadata(path, limit=1048576):
    s=path.lstat()
    reject(stat.S_ISREG(s.st_mode) and s.st_nlink==1 and s.st_size<=limit,'METADATA_TYPE')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    try:
        reject(c.stamp(os.fstat(fd))==c.stamp(s),'METADATA_CHANGED')
        raw=b''
        while len(raw)<=limit:
            block=os.read(fd,min(65536,limit+1-len(raw)))
            if not block:break
            raw+=block
        reject(len(raw)<=limit and c.stamp(os.fstat(fd))==c.stamp(path.lstat())==c.stamp(s),
               'METADATA_CHANGED')
        return raw
    finally:os.close(fd)


def release():
    raw=metadata(AUDIT/'release.json');manifest=c.parse(raw)
    reject(set(manifest['code_sha256'])==set(CODE),'CODE_INVENTORY')
    for name,expected in {**manifest['code_sha256'],**manifest['contract_sha256']}.items():
        reject(c.sha((k.REPO/name).read_bytes())==expected,'RELEASE_HASH')
    return manifest,c.sha(raw)


@dataclasses.dataclass(frozen=True)
class Context:
    root: Path
    source: Path
    expected: str
    contract_path: Path
    contract_sha: str
    scope: str
    ids: c.Identities | None


def authorization(ctx, release_sha, inventory_sha):
    path=ctx.root/'permission_C.json'
    if not os.path.lexists(path):raise Stop('FAIL','AUTHORIZATION_ABSENT')
    raw=metadata(path);a=c.parse(raw)
    reject(set(a)=={'version','decision','scope','approval_id','release_sha256','contract_sha256',
                   'inventory_sha256','approved_at','expires_at','lock_device','lock_inode',
                   'all_consumers_stopped','no_other_scientific_processes','source_writer_stopped',
                   'staging_reviewed','human_reviewer'},'AUTHORIZATION_SCHEMA')
    reject(a['version']=='1.0.0' and a['decision']=='APPROVE_ONCE' and a['scope']==ctx.scope,
           'AUTHORIZATION_SCOPE')
    reject(a['release_sha256']==release_sha and a['contract_sha256']==ctx.contract_sha
           and a['inventory_sha256']==inventory_sha,'AUTHORIZATION_BINDING')
    reject(type(a['approval_id']) is str and c.re.fullmatch('[0-9a-f]{64}',a['approval_id'])
           and type(a['human_reviewer']) is str and 0<len(a['human_reviewer'])<=128,'AUTHORIZATION_ID')
    for key in ['all_consumers_stopped','no_other_scientific_processes','source_writer_stopped','staging_reviewed']:
        reject(a[key] is True,'HUMAN_PREFLIGHT_REQUIRED')
    now=datetime.now(timezone.utc)
    start=datetime.fromisoformat(a['approved_at']);end=datetime.fromisoformat(a['expires_at'])
    reject(start.tzinfo is not None and end.tzinfo is not None,'AUTHORIZATION_TIME')
    reject(start<=now<end and (now-start).total_seconds()<=300
           and 0<(end-start).total_seconds()<=300,'AUTHORIZATION_EXPIRED')
    lock=ctx.root/'scientific.lock';s=lock.lstat()
    reject(type(a['lock_device']) is int and type(a['lock_inode']) is int
           and (s.st_dev,s.st_ino)==(a['lock_device'],a['lock_inode']),'LOCK_BINDING')
    return a,c.sha(raw)


def run_worker(payload,expected,ids):
    request=json.dumps({'payload':base64.b64encode(payload).decode(),'expected':expected,
                        'ids':dataclasses.asdict(ids)},separators=(',',':')).encode()
    reject(len(request)<=c.REQUEST_LIMIT,'IPC_REQUEST_LIMIT')
    run=subprocess.run([sys.executable,'-I','-B',str(Path(__file__).with_name('e1_code_release_worker.py'))],
                       input=request,capture_output=True,close_fds=True,timeout=c.TIMEOUT,
                       env={'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1'})
    if run.returncode<0:raise Stop('INCONCLUSIVE','WORKER_INTERRUPTED')
    reject(not run.stderr and len(run.stdout)<=c.RESPONSE_LIMIT,'IPC_RESPONSE_LIMIT')
    obj=c.parse(run.stdout)
    if run.returncode:
        reject(set(obj)=={'status','reason'} and obj['status'] in {'FAIL','INCONCLUSIVE'}
               and obj['reason'] in {'VALIDATION_REJECTED','INTERRUPTION_OR_RESOURCE','UNEXPECTED_STATE'},
               'IPC_ERROR_SCHEMA')
        raise Stop(obj['status'],obj['reason'])
    return base64.b64decode(obj['output'],validate=True),obj


def claim(ctx, auth_sha):
    path=ctx.root/'attempt.json'
    try:c.write_private(path,k.canonical({'authorization_sha256':auth_sha,'state':'CONSUMED_NO_RETRY'}))
    except FileExistsError:raise Stop('FAIL','AUTHORIZATION_REUSED') from None
    fd=os.open(ctx.root,os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)


def _execute(ctx):
    claimed=False;published=False
    try:
        manifest,release_sha=release()
        reject(ctx.root==ctx.root.resolve() and ctx.source.parent==ctx.source.parent.resolve(), 'PATH_CANONICAL')
        reject(c.sha(metadata(ctx.contract_path))==ctx.contract_sha,'CONTRACT_HASH')
        invraw=metadata(AUDIT/'consumers.json');inv=c.parse(invraw)
        reject(inv['during_C']=='ALL_DISABLED' and all(x['enabled_during_C'] is False for x in inv['participants']),
               'CONSUMER_INVENTORY')
        # Missing approval is rejected before opening even the lock or real identity files.
        a,auth_sha=authorization(ctx,release_sha,c.sha(invraw))
        with k.cooperative_lease(ctx.root):
            # Recheck after lease acquisition; lock inode must remain bound to approval.
            reject(authorization(ctx,release_sha,c.sha(invraw))[1]==auth_sha,'AUTHORIZATION_CHANGED')
            reject(not os.path.lexists(ctx.root/'attempt.json') and not os.path.lexists(ctx.root/'completion.json'),
                   'AUTHORIZATION_REUSED')
            k.empty_destination(ctx.root)
            claim(ctx,auth_sha);claimed=True
            ids=ctx.ids if ctx.ids is not None else c.load_frozen_identities(k.REPO)
            ids.validate()
            payload,stamp=k.capture(ctx.source,ctx.expected)
            raw,response=run_worker(payload,ctx.expected,ids)
            counts=k.verify_response(payload,response,raw,ids,ctx.expected)
            prov={'version':'1.1.0','scope':ctx.scope,'permission_C':ctx.scope=='CODE_ACTIVEMQ_T1',
                  'authorization_sha256':auth_sha,'release_sha256':release_sha,
                  'contract_sha256':ctx.contract_sha,'code_sha256':manifest['code_sha256'],
                  'source_sha256':c.sha(payload),'source_bytes':len(payload),'source_stamp':stamp,
                  'output_sha256':c.sha(raw),'output_bytes':len(raw),'rows':245,'order':'temporal',
                  'fields':['row_identifier','la','ld','nf','nd','ns','ent'],'limits':k.LIMITS,
                  'identity_order_sha256':{n:c.sha(k.canonical(v)) for n,v in dataclasses.asdict(ids).items()},
                  'transport':counts,'python':platform.python_version(),'zlib':zlib.ZLIB_RUNTIME_VERSION,
                  'OS_sandbox':False,'hard_RSS_limit':False,'zlib_internal_boundary_certified':False,
                  'consumer_inactivity':'cooperative lease plus fresh human attestation'}
            def before_commit():
                if c.stamp(ctx.source.lstat())!=stamp:raise Stop('INCONCLUSIVE','CONCURRENT_CHANGE')
                reject(release()[1]==release_sha,'RELEASE_CHANGED')
                reject(c.sha(metadata(ctx.contract_path))==ctx.contract_sha,'CONTRACT_CHANGED')
                reject(authorization(ctx,release_sha,c.sha(invraw))[1]==auth_sha,'AUTHORIZATION_CHANGED')
            k.publish(ctx.root,raw,prov,ids,before_commit);published=True
            result=Outcome('PASS','COMPLETE',True)
            c.write_private(ctx.root/'completion.json',k.canonical({**dataclasses.asdict(result),
                            'authorization_sha256':auth_sha,'output_sha256':c.sha(raw)}))
            return result
    except BaseException as exc:
        result=Outcome('INCONCLUSIVE','PUBLICATION_STATE_UNCERTAIN') if (published or (claimed and os.path.lexists(ctx.root/'validated'))) else classify(exc)
        # No PASS receipt => no output may be consumed, even if a crash followed rename.
        if claimed:
            try:c.write_private(ctx.root/'completion.json',k.canonical(dataclasses.asdict(result)))
            except BaseException:result=Outcome('INCONCLUSIVE','RESULT_RECORD_UNCERTAIN')
        return result


def production_entry():
    """No arguments. DO NOT call without separate explicit human Permission C."""
    try:
        release()
        path=AUDIT/'production_contract.json';raw=metadata(path);obj=c.parse(raw)
        reject(obj['authorization_required'] is True and obj['limits']==k.LIMITS,'PRODUCTION_CONTRACT')
        # All paths/identities originate in the hashed contract; no caller overrides.
        ctx=Context((k.REPO/obj['destination']).parent,k.REPO/obj['source'],obj['source_sha256'],
                    path,c.sha(raw),'CODE_ACTIVEMQ_T1',None)
        return _execute(ctx)
    except BaseException as exc:return classify(exc)


def synthetic_entry(root,contract_sha):
    """Only test fixture injection; production_entry is never called by tests."""
    try:
        root,obj,ids=k.load_fixture(root,contract_sha)
        return _execute(Context(root,root/'fixture.code.jsonl.gz',obj['source_sha256'],
                                root/'fixture_contract.json',contract_sha,'INVENTED_ONLY',ids))
    except BaseException as exc:return classify(exc)
