"""Only invented rows and temporary synthetic gzip files. No repository payloads."""
import base64
import contextlib
import dataclasses
import gzip
import hashlib
import io
import json
import os
import stat
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from src.governance import e1_code_synthetic_extractor as e


def row(i):
    return dict(row_identifier=f"synthetic-row-{i:04d}", la=i, ld=0,
                nf=1, nd=1, ns=1, ent=0.125)


def line(value):
    return json.dumps(value, separators=(",", ":"), allow_nan=True).encode() + b"\n"


class SyntheticExtractorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="e1-code-b-synthetic-",
                                              dir=str(Path(tempfile.gettempdir()).resolve()))
        self.path = Path(self.tmp.name) / "fixture.code.jsonl.gz"
        self.targets = [row(i) for i in (1, 2, 3)]
        self.prefix = b'{"discarded":"SYNTHETIC_PRE_T1"}\n'
        self.tail = b'{"secret":"SYNTHETIC_T2_SENTINEL"}\n'
        self.make()

    def tearDown(self):
        self.tmp.cleanup()

    def make(self, records=None, tail=None):
        records = self.targets if records is None else records
        self.raw = self.prefix + b"".join(v if isinstance(v, bytes) else line(v)
                                         for v in records) + (self.tail if tail is None else tail)
        self.payload = gzip.compress(self.raw, mtime=0)
        self.path.write_bytes(self.payload)
        self.c = e.Contract(hashlib.sha256(self.payload).hexdigest(),
                            tuple(r['row_identifier'] for r in self.targets),
                            (self.targets[0]['row_identifier'],), 1, 4, 100000)

    def reject(self, c=None):
        stdout, stderr = io.StringIO(), io.StringIO()
        delivered = []
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            with self.assertRaises(e.Rejected) as caught:
                delivered.append(e.extract_synthetic(self.path, c or self.c))
        self.assertEqual(str(caught.exception), 'EXTRACTION_REJECTED')
        self.assertEqual(delivered, [])
        self.assertEqual(stdout.getvalue() + stderr.getvalue(), '')

    def test_01_correct_segment_and_exact_types(self):
        result = e.extract_synthetic(self.path, self.c)
        self.assertEqual(result['rows'], self.targets)
        for actual, expected in zip(result['rows'], self.targets):
            self.assertEqual({k: type(v) for k, v in actual.items()},
                             {k: type(v) for k, v in expected.items()})

    def test_02_exact_stop_and_same_stream_T2_sentinel(self):
        result = e.extract_synthetic(self.path, self.c)
        end = self.prefix + b''.join(map(line, self.targets))
        self.assertEqual(result['transport']['decoded_bytes'], len(end))
        self.assertEqual(result['transport']['lines'], 4)
        self.assertNotIn('SYNTHETIC_T2_SENTINEL', json.dumps(result))
        self.assertLess(result['transport']['compressed_bytes_consumed'], len(self.payload))

    def test_03_truncated_expected_file(self):
        self.path.write_bytes(self.payload[:len(self.payload)//2])
        self.reject()

    def test_04_truncated_prefix_even_with_matching_hash(self):
        payload = gzip.compress(self.prefix + line(self.targets[0]), mtime=0)
        self.path.write_bytes(payload)
        self.reject(dataclasses.replace(self.c, expected_sha256=hashlib.sha256(payload).hexdigest()))

    def test_05_corruption_and_invalid_compression(self):
        for payload in [self.payload[:-1] + bytes([self.payload[-1] ^ 1]), b'not gzip']:
            self.path.write_bytes(payload)
            self.reject()
        self.reject(dataclasses.replace(self.c, expected_sha256=hashlib.sha256(b'not gzip').hexdigest()))

    def test_06_duplicate_missing_unexpected_identity(self):
        for records in [[row(1), row(1), row(3)], [row(1), row(2)],
                        [row(1), row(2), row(99)]]:
            with self.subTest(records=len(records)):
                self.make(records);self.reject()

    def test_07_changed_order(self):
        self.make([row(2), row(1), row(3)]);self.reject()

    def test_08_extra_fields_and_duplicate_keys(self):
        self.make([row(1), row(2), dict(row(3), forbidden='SYNTHETIC_T2_SENTINEL')])
        self.reject()
        duplicate = line(row(3)).replace(b'"la":3', b'"la":3,"la":3')
        self.make([row(1), row(2), duplicate]);self.reject()

    def test_09_incorrect_types_and_nonfinite(self):
        for field, value in [('la', True), ('la', '3'), ('la', 3.0), ('ent', 1),
                             ('ent', float('nan')), ('ent', float('inf')),
                             ('ent', None), ('ent', {})]:
            with self.subTest(field=field, kind=type(value).__name__):
                bad = dict(row(3));bad[field] = value
                self.make([row(1), row(2), bad]);self.reject()
        overflow = line(row(3)).replace(b'0.125', b'1e9999')
        self.make([row(1), row(2), overflow]);self.reject()

    def test_10_last_row_failure_worker_has_no_partial_output(self):
        self.make([row(1), row(2), b'{"secret":"SYNTHETIC_T2_SENTINEL"}\n'])
        request = json.dumps({'contract': dataclasses.asdict(self.c),
                              'payload': base64.b64encode(self.payload).decode()}).encode()
        run = subprocess.run([sys.executable, '-I', '-B', e.__file__, '--worker'],
                             input=request, capture_output=True, timeout=10)
        self.assertEqual(run.returncode, 2)
        self.assertEqual(run.stdout, b'{"error":"REJECTED"}')
        self.assertEqual(run.stderr, b'')
        self.reject()

    def test_11_no_auxiliary_writes(self):
        events, active = [], [True]
        def audit(event, args):
            if not active[0]:return
            if event == 'open':
                mode, flags = args[1], args[2]
                # The explicit IPC pipe is an authorized channel, not a disk artifact.
                if isinstance(args[0], int) and stat.S_ISFIFO(os.fstat(args[0]).st_mode):
                    return
                if (isinstance(mode, str) and any(c in mode for c in 'wax+')) or (
                    isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT)):
                    events.append(event)
            elif event in {'os.mkdir', 'os.remove', 'os.rename', 'os.rmdir'}:
                events.append(event)
        sys.addaudithook(audit)
        try:e.extract_synthetic(self.path, self.c)
        finally:active[0] = False
        self.assertEqual(events, [])
        self.assertEqual(list(self.path.parent.iterdir()), [self.path])

    def test_12_separate_consumer_cannot_open_source(self):
        rows = e.extract_synthetic(self.path, self.c)['rows']
        code = '''import sys,json
def deny(event,args):
 if event=='open':raise PermissionError('DENIED')
sys.addaudithook(deny)
rows=json.load(sys.stdin)
try:
 open(sys.argv[1],'rb')
except PermissionError:
 print(json.dumps({'rows':len(rows),'source_access':'DENIED'}))
else:sys.exit(2)
'''
        run = subprocess.run([sys.executable, '-I', '-B', '-c', code, str(self.path)],
                             input=json.dumps(rows).encode(), capture_output=True, timeout=10)
        self.assertEqual(run.returncode, 0)
        self.assertEqual(json.loads(run.stdout), {'rows': 3, 'source_access': 'DENIED'})
        self.assertEqual(run.stderr, b'')

    def test_13_source_replaced_during_read(self):
        original, changed = e.os.read, [False]
        def replace(fd, size):
            data = original(fd, size)
            if not changed[0]:
                changed[0] = True
                replacement = self.path.with_suffix('.replacement')
                replacement.write_bytes(self.payload)
                os.replace(replacement, self.path)
            return data
        with patch.object(e.os, 'read', side_effect=replace):self.reject()

    def test_14_source_modified_during_read(self):
        original, changed = e.os.read, [False]
        def modify(fd, size):
            data = original(fd, size)
            if not changed[0]:
                changed[0] = True
                self.path.write_bytes(self.payload + b'changed')
            return data
        with patch.object(e.os, 'read', side_effect=modify):self.reject()

    def test_15_tail_noninterference(self):
        results = []
        for tail in [b'T2_A\n', b'T2_B' * 1000 + b'\n', b'\xff\x00not-json\n']:
            self.make(tail=tail)
            results.append(e.extract_synthetic(self.path, self.c)['rows'])
        self.assertEqual(results, [self.targets] * 3)

    def test_16_immutable_verified_bytes_after_capture(self):
        original = e._run_worker
        def replace_after(payload, contract):
            self.path.write_bytes(b'changed after capture')
            return original(payload, contract)
        with patch.object(e, '_run_worker', side_effect=replace_after):
            self.assertEqual(e.extract_synthetic(self.path, self.c)['rows'], self.targets)

    def test_17_byte_memory_and_line_limits(self):
        for c in [dataclasses.replace(self.c, max_compressed=1),
                  dataclasses.replace(self.c, max_line=2),
                  dataclasses.replace(self.c, max_decoded=5)]:self.reject(c)

    def test_18_real_configuration_symlinks_and_bad_contract_denied(self):
        with self.assertRaises(e.Rejected):
            e.extract_synthetic('/forbidden/code_dataset.jsonl.gz', self.c)
        self.reject(dataclasses.replace(self.c, expected_ids=('real-sha',)*3))
        self.reject(dataclasses.replace(self.c, local_ids=('synthetic-row-9999',)))
        self.path.unlink();self.path.symlink_to(self.path.parent / 'nonexistent')
        self.reject()

    def test_19_full_future_cardinality_is_synthetic(self):
        self.targets = [row(i) for i in range(1, 246)]
        self.make()
        self.c = dataclasses.replace(self.c, stop=246,
                                     local_ids=tuple(r['row_identifier'] for r in self.targets[:8]))
        result = e.extract_synthetic(self.path, self.c)
        self.assertEqual(result['rows'], self.targets)
        self.assertEqual(len(self.c.local_ids), 8)


if __name__ == '__main__':
    unittest.main()
