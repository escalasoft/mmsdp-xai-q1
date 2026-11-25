"""C.1 candidate: real identity metadata allowed; real payload execution disabled."""
from __future__ import annotations

import base64
import ctypes
import dataclasses
from decimal import Decimal
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import resource
import shutil
import stat
import subprocess
import sys
import tempfile
import zlib

SOURCE_SIZE = 4_985_060
SOURCE_SHA = "42ec61d2adf3c708a4e55d856a7f3e95ee58464da022f84552c846379d796be3"
START, STOP, COUNT = 4900, 5145, 245
LINE_LIMIT, DECODED_LIMIT = 4096, 4 * 1024 * 1024
REQUEST_LIMIT, RESPONSE_LIMIT, TIMEOUT = 12 * 1024 * 1024, 2 * 1024 * 1024, 10
FIELDS = {"row_identifier", "la", "ld", "nf", "nd", "ns", "ent"}
HASHES = {
    "e1_t1_global_foreground_population.jsonl": "e80eda789dedabbe3cb249aa15d3c3568cc19ebff2c4551ae7b2b7a293ff4b02",
    "e1_local_case_population.jsonl": "7dfb985d78b10bed896c003da2b1dd6fa36a682e5f74b3f1f2a2d2dcf8c333e5",
    "representations/t1_row_registry.jsonl": "8faa1cede722f2858ee4c546bea9257687c5cb31c978f05c646e3e6d854345e5",
}
MEMBERSHIP_SHA = "aded97af168717cf2ae8716835a79d8830adff9131ad04edc0618873ab42c0c8"


class Rejected(Exception):
    pass


def need(ok, code):
    if not ok:
        raise Rejected(code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def pairs(items):
    out = {}
    for key, value in items:
        need(key not in out, "DUPLICATE_KEY")
        out[key] = value
    return out


def constant(_):
    raise Rejected("NONFINITE")


def parse(raw):
    return json.loads(raw, object_pairs_hook=pairs, parse_float=Decimal,
                      parse_int=int, parse_constant=constant)


@dataclasses.dataclass(frozen=True)
class Identities:
    temporal: tuple[str, ...]
    foreground: tuple[str, ...]
    local: tuple[str, ...]

    def validate(self):
        need(len(self.temporal) == len(self.foreground) == COUNT and len(self.local) == 8,
             "IDENTITY_COUNT")
        for sequence in (self.temporal, self.foreground, self.local):
            need(type(sequence) is tuple, 'IDENTITY_IMMUTABILITY')
            need(len(set(sequence)) == len(sequence), "IDENTITY_DUPLICATE")
            need(all(type(v) is str and re.fullmatch('[0-9a-f]{64}', v) for v in sequence),
                 "IDENTITY_FORMAT")
        need(set(self.temporal) == set(self.foreground) and set(self.local) <= set(self.temporal),
             "IDENTITY_MEMBERSHIP")


def load_frozen_identities(root):
    """Read ONLY the three pinned identity metadata files, never CODE values."""
    try:
        base = Path(root) / 'audits/q1-bounded-complementary-e1-xai/1.0.0'
        groups = {}
        for name, expected in HASHES.items():
            raw = (base / name).read_bytes()
            need(sha(raw) == expected, "IDENTITY_FILE_HASH")
            records = [parse(line) for line in raw.splitlines() if line.strip()]
            for r in records:
                need(r['project'] == 'apache/activemq' and r['partition'] == 'T1', 'IDENTITY_SCOPE')
                commit = r['commit_identity']
                need(re.fullmatch('[0-9a-f]{40}', commit) is not None, 'COMMIT_FORMAT')
                need(sha(('apachejit-v2|apache/activemq|apache/activemq|' + commit).encode())
                     == r['row_identifier'], 'IDENTITY_FORMULA')
                need(r['order_key'][1] == commit, 'ORDER_KEY')
            groups[name] = records
        fg, local, temporal = (groups[name] for name in HASHES)
        bundle = Identities(tuple(r['row_identifier'] for r in temporal),
                            tuple(r['row_identifier'] for r in fg),
                            tuple(r['row_identifier'] for r in local))
        bundle.validate()
        lookup = {r['row_identifier']: (r['commit_identity'], r['order_key']) for r in temporal}
        need(all(lookup[r['row_identifier']] == (r['commit_identity'], r['order_key'])
                 for r in fg + local), 'IDENTITY_JOIN')
        need([r['order_key'] for r in temporal] == sorted(r['order_key'] for r in temporal),
             'TEMPORAL_ORDER')
        raw = (json.dumps(list(bundle.temporal), sort_keys=True, separators=(',', ':')) + '\n').encode()
        need(sha(raw) == MEMBERSHIP_SHA, 'MEMBERSHIP_HASH')
        return bundle
    except Exception:
        raise Rejected('IDENTITY_METADATA_REJECTED') from None


def stamp(s):
    return s.st_dev, s.st_ino, s.st_mode, s.st_size, s.st_mtime_ns, s.st_ctime_ns


def capture_synthetic(path, expected):
    path = Path(path).absolute()
    need(path.name == 'fixture.code.jsonl.gz' and path.parent.name.startswith('e1-code-c1-synthetic-')
         and path.parent.resolve() == path.parent, 'SYNTHETIC_ONLY')
    s = path.lstat()
    need(stat.S_ISREG(s.st_mode) and not stat.S_ISLNK(s.st_mode), 'SOURCE_TYPE')
    need(s.st_size == SOURCE_SIZE, 'SOURCE_SIZE')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
        before = stamp(s)
        need(stamp(os.fstat(fd)) == before == stamp(path.lstat()), 'SOURCE_CHANGED')
        chunks, remaining = [], SOURCE_SIZE
        while remaining:
            block = os.read(fd, min(65536, remaining))
            need(bool(block), 'SOURCE_TRUNCATED')
            chunks.append(block)
            remaining -= len(block)
        need(stamp(os.fstat(fd)) == before == stamp(path.lstat()), 'SOURCE_CHANGED')
        payload = b''.join(chunks)
        need(sha(payload) == expected, 'SOURCE_HASH')
        return payload
    finally:
        os.close(fd)


def validate_line(raw, expected_id):
    need(raw.endswith(b'\n') and len(raw) <= LINE_LIMIT and raw.count(b'\n') == 1,
         'LINE_LIMIT')
    row = parse(raw)
    need(type(row) is dict and set(row) == FIELDS, 'SCHEMA')
    need(row['row_identifier'] == expected_id, 'IDENTITY_ORDER')
    for key in FIELDS - {'row_identifier'}:
        value = row[key]
        need(type(value) is int or type(value) is Decimal, 'NUMBER_TYPE')
        need(type(value) is int or value.is_finite(), 'NONFINITE')
    return raw  # Original spelling, whitespace, key order and LF are retained.


def validate_output(raw, ids):
    ids.validate()
    need(len(raw) <= COUNT * LINE_LIMIT, 'OUTPUT_LIMIT')
    lines = raw.splitlines(keepends=True)
    need(len(lines) == COUNT, 'OUTPUT_COUNT')
    for line, expected_id in zip(lines, ids.temporal):
        validate_line(line, expected_id)


def decode(payload, expected, ids):
    ids.validate()
    need(len(payload) == SOURCE_SIZE and sha(payload) == expected, 'CAPTURE_HASH')
    decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
    consumed = total = count = 0
    line, staged = bytearray(), []
    while count < STOP:
        if decoder.unconsumed_tail:
            block = decoder.unconsumed_tail
        else:
            need(consumed < SOURCE_SIZE, 'TRUNCATED')
            block = payload[consumed:consumed + 1]
            consumed += 1
        byte = decoder.decompress(block, max_length=1)
        need(not decoder.eof or byte, 'TRUNCATED')
        total += len(byte)
        need(total <= DECODED_LIMIT, 'DECODED_LIMIT')
        line.extend(byte)
        need(len(line) <= LINE_LIMIT, 'LINE_LIMIT')
        if byte == b'\n':
            if count >= START:
                staged.append(validate_line(bytes(line), ids.temporal[count - START]))
            line.clear()
            count += 1
    raw = b''.join(staged)
    validate_output(raw, ids)
    return raw, {'lines': count, 'decoded_bytes': total, 'compressed_bytes_consumed': consumed}


def deny_io(event, args):
    if event == 'open' or event.startswith(('socket.', 'subprocess.')) or event in {
        'os.mkdir', 'os.remove', 'os.rename', 'os.rmdir', 'os.link', 'os.symlink',
        'os.chmod', 'os.truncate', 'os.utime', 'os.system', 'os.listdir', 'os.scandir'
    }:
        raise Rejected('IO_DENIED')


def memory_status():
    return {'platform': platform.system(), 'hard_total_memory_enforced': False,
            'status': 'PENDING', 'reason': 'No reliable hard total-RSS enforcement validated on this macOS host',
            'rlimit_as_available': hasattr(resource, 'RLIMIT_AS'),
            'rlimit_rss_available': hasattr(resource, 'RLIMIT_RSS'),
            'logical_limits_enforced': True}


def worker():
    sys.addaudithook(deny_io)
    try:
        request = sys.stdin.buffer.read(REQUEST_LIMIT + 1)
        need(len(request) <= REQUEST_LIMIT, 'REQUEST_LIMIT')
        obj = json.loads(request)
        ids = Identities(**{k: tuple(v) for k, v in obj['ids'].items()})
        payload = base64.b64decode(obj['payload'], validate=True)
        raw, counts = decode(payload, obj['expected'], ids)
        response = json.dumps({'output': base64.b64encode(raw).decode(),
                               'output_sha256': sha(raw), 'source_sha256': sha(payload),
                               'transport': counts}, separators=(',', ':')).encode()
        need(len(response) <= RESPONSE_LIMIT, 'RESPONSE_LIMIT')
    except BaseException:
        sys.stdout.write('{"error":"REJECTED"}')
        return 2
    sys.stdout.buffer.write(response)
    return 0


def run_worker(payload, expected, ids):
    ids.validate()
    request = json.dumps({'payload': base64.b64encode(payload).decode(), 'expected': expected,
                          'ids': dataclasses.asdict(ids)}, separators=(',', ':')).encode()
    need(len(request) <= REQUEST_LIMIT, 'REQUEST_LIMIT')
    run = subprocess.run([sys.executable, '-I', '-B', str(Path(__file__).resolve()), '--worker'],
                         input=request, capture_output=True, close_fds=True, timeout=TIMEOUT,
                         env={'PATH': '/usr/bin:/bin', 'PYTHONDONTWRITEBYTECODE': '1'})
    need(run.returncode == 0 and not run.stderr and len(run.stdout) <= RESPONSE_LIMIT, 'WORKER')
    result = json.loads(run.stdout)
    raw = base64.b64decode(result['output'], validate=True)
    validate_output(raw, ids)
    need(sha(raw) == result['output_sha256'] and result['source_sha256'] == expected, 'IPC_HASH')
    return raw, result


def extract_synthetic(path, expected, ids):
    try:
        return run_worker(capture_synthetic(path, expected), expected, ids)
    except BaseException:
        raise Rejected('EXTRACTION_REJECTED') from None


def extract_real(*args, **kwargs):
    raise Rejected('PERMISSION_C_NOT_AUTHORIZED')


def rename_exclusive(source, destination):
    # Darwin SDK sys/stdio.h: RENAME_EXCL = 0x00000004.
    need(sys.platform == 'darwin', 'ATOMIC_BACKEND_UNAVAILABLE')
    libc = ctypes.CDLL(None, use_errno=True)
    rename = libc.renamex_np
    rename.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
    rename.restype = ctypes.c_int
    if rename(os.fsencode(source), os.fsencode(destination), 0x4) != 0:
        raise Rejected('PUBLICATION_REJECTED')


def write_private(path, payload):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, 'wb', closefd=False) as f:
            f.write(payload)
            f.flush()
            os.fsync(fd)
    finally:
        os.close(fd)


def publish_synthetic(raw, destination, ids, source_sha):
    """Atomic directory publication: one output plus provenance, never overwrite."""
    stage = None
    try:
        validate_output(raw, ids)
        need(re.fullmatch('[0-9a-f]{64}', source_sha) is not None, 'SOURCE_HASH')
        destination = Path(destination).absolute()
        parent = destination.parent
        need(parent.name.startswith('e1-code-c1-synthetic-') and parent.resolve() == parent,
             'SYNTHETIC_ONLY')
        need(not destination.exists() and not destination.is_symlink(), 'DESTINATION_EXISTS')
        stage = Path(tempfile.mkdtemp(prefix='.private-stage-', dir=parent))
        os.chmod(stage, 0o700)
        write_private(stage / 'code_t1.jsonl', raw)
        provenance = {'version': 'C.1-candidate-1.0.0', 'source_sha256': source_sha,
                      'execution_scope': 'SYNTHETIC_ONLY',
                      'implementation_sha256': sha(Path(__file__).read_bytes()),
                      'output_sha256': sha(raw), 'rows': COUNT, 'fields': sorted(FIELDS),
                      'order': 'temporal', 'serialization': 'original validated JSONL bytes including LF',
                      'memory': memory_status(), 'python': platform.python_version(),
                      'zlib': zlib.ZLIB_RUNTIME_VERSION,
                      'limits': {'source': SOURCE_SIZE, 'start': START, 'stop': STOP,
                                 'line': LINE_LIMIT, 'decoded': DECODED_LIMIT,
                                 'request': REQUEST_LIMIT, 'response': RESPONSE_LIMIT, 'timeout': TIMEOUT},
                      'identity_hashes': {k: sha(json.dumps(v, separators=(',', ':')).encode())
                                          for k, v in dataclasses.asdict(ids).items()}}
        write_private(stage / 'provenance.json', (json.dumps(provenance, sort_keys=True) + '\n').encode())
        fd = os.open(stage, os.O_RDONLY)
        try: os.fsync(fd)
        finally: os.close(fd)
        rename_exclusive(stage, destination)
        stage = None  # Visibility commit point; no subsequent fallible publication work.
        return destination
    except BaseException:
        raise Rejected('PUBLICATION_REJECTED') from None
    finally:
        if stage is not None:
            shutil.rmtree(stage, ignore_errors=True)


if __name__ == '__main__':
    if sys.argv[1:] == ['--worker']:
        raise SystemExit(worker())
    raise SystemExit('PERMISSION_C_NOT_AUTHORIZED')
