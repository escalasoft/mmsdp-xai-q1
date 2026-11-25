"""Versioned Route B coordinator. Real execution is deliberately unavailable."""
from __future__ import annotations
import base64
from contextlib import contextmanager
import dataclasses
import fcntl
import json
import os
from pathlib import Path
import platform
import shutil
import stat
import subprocess
import tempfile
import zlib
from . import e1_code_candidate as c

REPO = Path(__file__).resolve().parents[2]
AUDIT = REPO / 'audits/q1-e1-code-coordinator/1.0.0'
LIMITS = dict(source_bytes=4985060, start=4900, stop=5145, rows=245,
              line_bytes=4096, prefix_bytes=4194304, request_bytes=12582912,
              response_bytes=2097152, timeout_seconds=10)
CODE_FILES = ('src/governance/e1_code_coordinator.py', 'src/governance/e1_code_candidate.py')


def canonical(obj):
    return (json.dumps(obj, sort_keys=True, separators=(',', ':')) + '\n').encode()


def release():
    """Local reviewed release manifest, not a hostile-user signature mechanism."""
    obj = c.parse((AUDIT / 'release.json').read_bytes())
    c.need(set(obj['code_sha256']) == set(CODE_FILES), 'CODE_INVENTORY')
    for name, expected in obj['code_sha256'].items():
        c.need(c.sha((REPO / name).read_bytes()) == expected, 'CODE_HASH')
    for name, expected in obj['contract_sha256'].items():
        c.need(c.sha((REPO / name).read_bytes()) == expected, 'CONTRACT_HASH')
    return obj


def production_specification():
    """Metadata only; never touches the real source or runs its identity adapter."""
    release()
    obj = c.parse((AUDIT / 'production_contract.json').read_bytes())
    c.need(obj['limits'] == LIMITS and obj['permission_C'] is False, 'PRODUCTION_CONTRACT')
    return obj


@dataclasses.dataclass(frozen=True)
class Plan:
    root: Path
    source: Path
    ids: c.Identities
    source_sha256: str
    scope: str
    contract_sha256: str
    contract_path: Path


def prepare_production_plan():
    """Identity/contract metadata only. No payload read and no execution authority."""
    obj = production_specification()
    ids = c.load_frozen_identities(REPO)
    destination = REPO / obj['destination']
    c.need(destination.name == 'validated'
           and REPO / obj['cooperative_lock'] == destination.parent / 'scientific.lock',
           'PRODUCTION_PATHS')
    return Plan(destination.parent, REPO / obj['source'], ids, obj['source_sha256'],
                'PRODUCTION_NOT_AUTHORIZED', c.sha((AUDIT / 'production_contract.json').read_bytes()),
                AUDIT / 'production_contract.json')


def run_production():
    # No option, env var, CLI switch or token can enable production in this release.
    raise c.Rejected('PERMISSION_C_NOT_AUTHORIZED')


def fixture_root(root):
    p = Path(root).absolute()
    c.need(p == p.resolve() and p.parent == Path(tempfile.gettempdir()).resolve()
           and p.name.startswith('e1-code-coordinator-synthetic-'), 'SYNTHETIC_ONLY')
    return p


def load_fixture(root, expected_contract_sha256):
    """Test-only adapter. It cannot provide arbitrary source/destination paths."""
    root = fixture_root(root)
    raw = (root / 'fixture_contract.json').read_bytes()
    c.need(c.sha(raw) == expected_contract_sha256, 'FIXTURE_CONTRACT_HASH')
    obj = c.parse(raw)
    c.need(set(obj) == {'version', 'scope', 'project', 'partition', 'source_sha256',
                       'limits', 'ids'}, 'FIXTURE_SCHEMA')
    c.need(obj['version'] == '1.0.0' and obj['scope'] == 'INVENTED_ONLY'
           and obj['project'] == 'apache/activemq' and obj['partition'] == 'T1'
           and obj['limits'] == LIMITS, 'FIXTURE_SCOPE')
    ids = c.Identities(**{k: tuple(v) for k, v in obj['ids'].items()})
    ids.validate()
    c.need(type(obj['source_sha256']) is str
           and c.re.fullmatch('[0-9a-f]{64}', obj['source_sha256']), 'SOURCE_HASH_FORMAT')
    return root, obj, ids


@contextmanager
def cooperative_lease(root, consumer=False):
    """All cooperative consumers MUST hold SH throughout use; coordinator holds EX.

    The persistent inode is provisioned beforehand, never unlinked/replaced here.
    This does not enumerate or exclude non-cooperating same-UID processes.
    """
    path = root / 'scientific.lock'
    s = path.lstat()
    c.need(stat.S_ISREG(s.st_mode) and s.st_nlink == 1, 'LOCK_TYPE')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        c.need(c.stamp(os.fstat(fd)) == c.stamp(s), 'LOCK_CHANGED')
        fcntl.flock(fd, (fcntl.LOCK_SH if consumer else fcntl.LOCK_EX) | fcntl.LOCK_NB)
        yield
    finally:
        os.close(fd)


def empty_destination(root):
    c.need(not os.path.lexists(root / 'validated'), 'DESTINATION_EXISTS')
    c.need(not any(root.glob('.private-stage-*')), 'STAGING_RESIDUAL')


def capture(path, expected):
    """One read-only descriptor; returns immutable bytes and stable source stamp."""
    s = path.lstat()
    c.need(stat.S_ISREG(s.st_mode) and s.st_nlink == 1 and s.st_size == c.SOURCE_SIZE,
           'SOURCE_TYPE_SIZE')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
        stamp = c.stamp(s)
        c.need(c.stamp(os.fstat(fd)) == stamp == c.stamp(path.lstat()), 'SOURCE_CHANGED')
        blocks, remaining = [], c.SOURCE_SIZE
        while remaining:
            block = os.read(fd, min(65536, remaining))
            c.need(bool(block), 'TRUNCATED')
            blocks.append(block)
            remaining -= len(block)
        c.need(c.stamp(os.fstat(fd)) == stamp == c.stamp(path.lstat()), 'SOURCE_CHANGED')
        payload = b''.join(blocks)
        c.need(c.sha(payload) == expected, 'CAPTURE_HASH')
        return payload, stamp
    finally:
        os.close(fd)


def verify_response(payload, response, raw, ids, expected):
    """Independent coordinator checks; transport counts are range checked, not replayed."""
    c.need(type(payload) is bytes and len(payload) == c.SOURCE_SIZE
           and c.sha(payload) == expected, 'CAPTURE_LINK')
    c.need(set(response) == {'output', 'output_sha256', 'source_sha256', 'transport'}, 'IPC_SCHEMA')
    c.need(base64.b64decode(response['output'], validate=True) == raw, 'IPC_OUTPUT')
    c.validate_output(raw, ids)
    c.need(response['source_sha256'] == expected
           and response['output_sha256'] == c.sha(raw), 'IPC_HASH')
    counts = response['transport']
    c.need(set(counts) == {'lines', 'decoded_bytes', 'compressed_bytes_consumed'}
           and all(type(x) is int for x in counts.values()), 'COUNTER_TYPES')
    c.need(counts['lines'] == c.STOP, 'COUNTER_LINES')
    c.need(c.START + len(raw) <= counts['decoded_bytes'] <= min(
        c.DECODED_LIMIT, c.START * c.LINE_LIMIT + len(raw)), 'COUNTER_PREFIX')
    c.need(0 < counts['compressed_bytes_consumed'] <= len(payload), 'COUNTER_COMPRESSED')
    return {'lines': counts['lines'], 'decoded_bytes': counts['decoded_bytes'],
            'compressed_bytes_supplied': counts['compressed_bytes_consumed']}


def publish(root, raw, provenance, ids, before_commit):
    """Private implementation: caller has already validated capture and IPC linkage."""
    c.validate_output(raw, ids)
    c.need(provenance['output_sha256'] == c.sha(raw)
           and provenance['output_bytes'] == len(raw), 'PUBLICATION_LINK')
    empty_destination(root)
    stage = Path(tempfile.mkdtemp(prefix='.private-stage-', dir=root))
    try:
        os.chmod(stage, 0o700)
        c.write_private(stage / 'code_t1.jsonl', raw)
        meta = canonical(provenance)
        c.write_private(stage / 'provenance.json', meta)
        written = (stage / 'code_t1.jsonl').read_bytes()
        c.need(written == raw and c.sha(written) == provenance['output_sha256'], 'DISK_HASH')
        c.validate_output(written, ids)
        c.need((stage / 'provenance.json').read_bytes() == meta, 'DISK_PROVENANCE')
        c.need(set(p.name for p in stage.iterdir()) == {'code_t1.jsonl', 'provenance.json'}, 'DISK_FILES')
        fd = os.open(stage, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
        before_commit()
        c.rename_exclusive(stage, root / 'validated')
        stage = None  # Atomic visibility commit; no fallible file operations afterwards.
        return root / 'validated'
    finally:
        if stage is not None:
            shutil.rmtree(stage, ignore_errors=True)  # Any leftover blocks next preflight.


def _orchestrate(plan):
    # Release gate also protects the shared engine, not just its public wrapper.
    c.need(plan.scope == 'INVENTED_ONLY', 'PERMISSION_C_NOT_AUTHORIZED')
    root = fixture_root(plan.root)
    source, ids = plan.source, plan.ids
    c.need(source == root / 'fixture.code.jsonl.gz', 'FIXED_SOURCE')
    approved = release()
    with cooperative_lease(root):
        empty_destination(root)
        payload, stamp = capture(source, plan.source_sha256)
        raw, response = c.run_worker(payload, plan.source_sha256, ids)
        counts = verify_response(payload, response, raw, ids, plan.source_sha256)
        provenance = {
            'version': 'coordinator-1.0.0', 'scope': plan.scope, 'permission_C': False,
            'project': 'apache/activemq', 'partition': 'T1',
            'source_sha256': c.sha(payload), 'source_bytes': len(payload), 'source_stamp': stamp,
            'output_sha256': c.sha(raw), 'output_bytes': len(raw), 'rows': 245,
            'fields': ['row_identifier', 'la', 'ld', 'nf', 'nd', 'ns', 'ent'],
            'order': 'temporal', 'serialization': 'original JSONL bytes including LF',
            'identity_order_sha256': {k: c.sha(canonical(v)) for k,v in dataclasses.asdict(ids).items()},
            'input_contract_sha256': plan.contract_sha256,
            'release_manifest_sha256': c.sha((AUDIT / 'release.json').read_bytes()),
            'code_sha256': approved['code_sha256'], 'contract_sha256': approved['contract_sha256'],
            'limits': LIMITS, 'transport': counts,
            'python': platform.python_version(), 'zlib': zlib.ZLIB_RUNTIME_VERSION,
            'cooperative_exclusion': True, 'OS_sandbox': False, 'hard_RSS_limit': False,
            'no_internal_zlib_anticipation_certified': False}
        def before_commit():
            c.need(c.stamp(source.lstat()) == stamp, 'SOURCE_CHANGED_AFTER_CAPTURE')
            c.need(c.sha(plan.contract_path.read_bytes()) == plan.contract_sha256,
                   'CONTRACT_CHANGED')
            c.need(release() == approved, 'RELEASE_CHANGED')
        return publish(root, raw, provenance, ids, before_commit)


def run_synthetic(root, expected_contract_sha256):
    """Only executable coordinator entry point in this release; invented fixtures."""
    try:
        release()
        root, contract, ids = load_fixture(root, expected_contract_sha256)
        plan = Plan(root, root / 'fixture.code.jsonl.gz', ids, contract['source_sha256'],
                    'INVENTED_ONLY', expected_contract_sha256, root / 'fixture_contract.json')
        return _orchestrate(plan)
    except BaseException:
        raise c.Rejected('COORDINATOR_REJECTED') from None
