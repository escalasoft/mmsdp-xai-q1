"""C.1 tests: invented hex identities, values and 4,985,060-byte gzip fixtures."""
import base64
import dataclasses
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from src.governance import e1_code_candidate as c


class CandidateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='e1-code-c1-synthetic-',
                                               dir=str(Path(tempfile.gettempdir()).resolve()))
        self.root = Path(self.temp.name)
        self.path = self.root / 'fixture.code.jsonl.gz'
        temporal = tuple(hashlib.sha256(f'invented-{i}'.encode()).hexdigest() for i in range(245))
        self.ids = c.Identities(temporal, temporal[::-1], temporal[:8])
        self.lines = [(' {"row_identifier":"' + v + '","la":123,"ld":-0,"nf":1.00,'
                       '"nd":2e+0,"ns":3E-0,"ent":0.123456789012345678901234567890} \n').encode()
                      for v in temporal]
        self.prefix = b'{}\n' * 4900
        self.tail = b'{"secret":"T2_SYNTHETIC_SENTINEL"}\n'
        self.make()

    def tearDown(self):
        self.temp.cleanup()

    def make(self, lines=None, tail=None, prefix=None):
        raw = (self.prefix if prefix is None else prefix) + b''.join(self.lines if lines is None else lines)
        raw += self.tail if tail is None else tail
        compressed = gzip.compress(raw, mtime=0)
        self.assertLess(len(compressed), c.SOURCE_SIZE)
        # Standard gzip zero padding; still one compressed member with T2 in it.
        self.payload = compressed + b'\0' * (c.SOURCE_SIZE - len(compressed))
        self.path.write_bytes(self.payload)
        self.expected = c.sha(self.payload)

    def reject(self):
        delivered = []
        with self.assertRaises(c.Rejected) as err:
            delivered.append(c.extract_synthetic(self.path, self.expected, self.ids))
        self.assertEqual(str(err.exception), 'EXTRACTION_REJECTED')
        self.assertEqual(delivered, [])

    def test_01_hex_identity_orders_and_lexical_preservation(self):
        raw, result = c.extract_synthetic(self.path, self.expected, self.ids)
        self.assertEqual(raw, b''.join(self.lines))
        self.assertEqual(result['transport']['lines'], 5145)
        self.assertEqual(result['transport']['decoded_bytes'], len(self.prefix) + len(raw))
        self.assertNotIn(b'T2_SYNTHETIC_SENTINEL', raw)
        self.assertNotEqual(self.ids.temporal, self.ids.foreground)

    def test_02_identity_missing_duplicate_order_and_unknown(self):
        for lines in [self.lines[:-1], [self.lines[0]] + self.lines[:-1], self.lines[::-1],
                      self.lines[:-1] + [self.lines[-1].replace(self.ids.temporal[-1].encode(), b'f'*64)]]:
            self.make(lines=lines);self.reject()

    def test_03_non_numbers_nonfinite_and_duplicate_keys(self):
        for value in [b'true', b'null', b'"1"', b'{}', b'[]', b'NaN', b'Infinity', b'-Infinity']:
            with self.subTest(value=value):
                bad = self.lines[-1].replace(b'"la":123', b'"la":' + value)
                with self.assertRaises(Exception): c.validate_line(bad, self.ids.temporal[-1])
        for bad in [self.lines[-1].replace(b'"la":123', b'"la":123,"la":123'),
                    self.lines[-1].replace(b'"la":123', b'"extra":0,"la":123')]:
            self.make(lines=self.lines[:-1]+[bad]);self.reject()

    def test_04_last_row_failure_no_data_in_worker_error(self):
        self.make(lines=self.lines[:-1]+[b'{"secret":"T2_SYNTHETIC_SENTINEL"}\n'])
        request = json.dumps({'payload':base64.b64encode(self.payload).decode(),
                              'expected':self.expected,'ids':dataclasses.asdict(self.ids)}).encode()
        run = subprocess.run([sys.executable,'-I','-B',c.__file__,'--worker'],input=request,
                             capture_output=True,timeout=10)
        self.assertEqual((run.returncode,run.stdout,run.stderr),(2,b'{"error":"REJECTED"}',b''))

    def test_05_truncation_corruption_and_capture_hash(self):
        self.path.write_bytes(self.payload[:-1]);self.reject()
        damaged = bytearray(self.payload);damaged[100] ^= 1
        self.path.write_bytes(damaged);self.reject()
        with self.assertRaises(c.Rejected):c.run_worker(bytes(damaged),self.expected,self.ids)
        self.make(lines=self.lines[:1],tail=b'');self.reject()

    def test_06_atomic_directory_publication_and_no_overwrite(self):
        raw=b''.join(self.lines);dest=self.root/'accepted'
        before=c.rename_exclusive
        def inspect(source,destination):
            self.assertFalse(destination.exists())
            self.assertEqual(stat.S_IMODE(source.stat().st_mode),0o700)
            self.assertEqual((source/'code_t1.jsonl').read_bytes(),raw)
            self.assertEqual(stat.S_IMODE((source/'code_t1.jsonl').stat().st_mode),0o600)
            self.assertTrue((source/'provenance.json').is_file())
            before(source,destination)
        with patch.object(c,'rename_exclusive',side_effect=inspect):
            c.publish_synthetic(raw,dest,self.ids,self.expected)
        self.assertEqual(set(p.name for p in dest.iterdir()),{'code_t1.jsonl','provenance.json'})
        self.assertEqual(json.loads((dest/'provenance.json').read_text())['output_sha256'],c.sha(raw))
        with self.assertRaises(c.Rejected):c.publish_synthetic(raw,dest,self.ids,self.expected)
        self.assertEqual((dest/'code_t1.jsonl').read_bytes(),raw)

    def test_07_fail_before_and_during_publication(self):
        dest=self.root/'accepted'
        with self.assertRaises(c.Rejected):c.publish_synthetic(b'invalid',dest,self.ids,self.expected)
        original=c.write_private
        def partial(path,payload):
            if path.name=='provenance.json':raise OSError('invented failure')
            original(path,payload)
        with patch.object(c,'write_private',side_effect=partial):
            with self.assertRaises(c.Rejected):c.publish_synthetic(b''.join(self.lines),dest,self.ids,self.expected)
        self.assertFalse(dest.exists());self.assertFalse(list(self.root.glob('.private-stage-*')))
        with patch.object(c,'rename_exclusive',side_effect=OSError('invented failure')):
            with self.assertRaises(c.Rejected):c.publish_synthetic(b''.join(self.lines),dest,self.ids,self.expected)
        self.assertFalse(dest.exists());self.assertFalse(list(self.root.glob('.private-stage-*')))

    def test_08_destination_race_does_not_overwrite(self):
        dest=self.root/'accepted';original=c.rename_exclusive
        def race(source,destination):
            destination.mkdir();(destination/'owner').write_text('other')
            original(source,destination)
        with patch.object(c,'rename_exclusive',side_effect=race):
            with self.assertRaises(c.Rejected):c.publish_synthetic(b''.join(self.lines),dest,self.ids,self.expected)
        self.assertEqual((dest/'owner').read_text(),'other')
        self.assertFalse((dest/'code_t1.jsonl').exists())

    def test_09_source_replacement_and_modification_during_capture(self):
        original=c.os.read
        for mode in ['replace','modify']:
            self.make();done=[False]
            def change(fd,size):
                block=original(fd,size)
                if not done[0]:
                    done[0]=True
                    if mode=='replace':
                        other=self.root/'replacement';other.write_bytes(self.payload);os.replace(other,self.path)
                    else:self.path.write_bytes(b'bad')
                return block
            with patch.object(c.os,'read',side_effect=change):self.reject()

    def test_10_change_after_verified_capture_cannot_change_result(self):
        original=c.run_worker
        def after(payload,expected,ids):
            self.path.write_bytes(b'changed');return original(payload,expected,ids)
        with patch.object(c,'run_worker',side_effect=after):
            raw,_=c.extract_synthetic(self.path,self.expected,self.ids)
        self.assertEqual(raw,b''.join(self.lines))

    def test_11_tail_noninterference_and_prefix_limits(self):
        for tail in [b'T2_A\n', b'not-json-T2_B'*500+b'\n']:
            self.make(tail=tail)
            raw,_=c.extract_synthetic(self.path,self.expected,self.ids)
            self.assertEqual(raw,b''.join(self.lines))
        self.make(prefix=(b'x'*4096+b'\n')+b'{}\n'*4899);self.reject()
        self.make(prefix=(b'x'*900+b'\n')*4900);self.reject()

    def test_12_consumer_file_access_denied_and_no_extractor_writes(self):
        events=[];active=[True]
        def audit(event,args):
            if not active[0]:return
            if event=='open':
                if isinstance(args[0],int) and stat.S_ISFIFO(os.fstat(args[0]).st_mode):return
                mode,flags=args[1],args[2]
                if (isinstance(mode,str) and any(x in mode for x in 'wax+')) or (
                    isinstance(flags,int) and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT)):events.append(event)
            elif event in {'os.mkdir','os.remove','os.rename'}:events.append(event)
        sys.addaudithook(audit)
        try:raw,_=c.extract_synthetic(self.path,self.expected,self.ids)
        finally:active[0]=False
        self.assertEqual(events,[])
        code="""import sys
def deny(event,args):
 if event=='open':raise PermissionError('DENIED')
sys.addaudithook(deny)
raw=sys.stdin.buffer.read()
try:open(sys.argv[1],'rb')
except PermissionError:print(len(raw.splitlines()))
else:sys.exit(2)
"""
        run=subprocess.run([sys.executable,'-I','-B','-c',code,str(self.path)],input=raw,capture_output=True)
        self.assertEqual((run.returncode,run.stdout,run.stderr),(0,b'245\n',b''))

    def test_13_actual_subprocess_timeout_enforced(self):
        original=subprocess.run;started=time.monotonic()
        def stalled(*args,**kwargs):
            self.assertEqual(kwargs['timeout'],10)
            return original([sys.executable,'-I','-B','-c','import time;time.sleep(30)'],
                            capture_output=True,timeout=kwargs['timeout'])
        with patch.object(c.subprocess,'run',side_effect=stalled):self.reject()
        self.assertLess(time.monotonic()-started,15)

    def test_14_memory_guarantee_explicitly_pending(self):
        status=c.memory_status()
        self.assertFalse(status['hard_total_memory_enforced'])
        self.assertEqual(status['status'],'PENDING')
        self.assertEqual((c.SOURCE_SIZE,c.LINE_LIMIT,c.DECODED_LIMIT,c.REQUEST_LIMIT,c.RESPONSE_LIMIT),
                         (4985060,4096,4194304,12582912,2097152))

    def test_15_real_entry_point_disabled_and_symlink_rejected(self):
        with self.assertRaises(c.Rejected):c.extract_real()
        self.path.unlink();self.path.symlink_to(self.root/'missing');self.reject()
        with self.assertRaises(c.Rejected):c.capture_synthetic('/forbidden/code_dataset.jsonl.gz',self.expected)

    def test_16_identity_adapter_synthetic_metadata_and_hash_failure(self):
        records=[]
        for i in range(245):
            commit=f'{i:040x}'
            records.append({'row_identifier':c.sha(('apachejit-v2|apache/activemq|apache/activemq|'+commit).encode()),
                            'commit_identity':commit,'project':'apache/activemq','partition':'T1',
                            'order_key':[f'2020-01-01T00:{i//60:02d}:{i%60:02d}Z',commit]})
        groups=[records[::-1],records[:8],records]
        base=self.root/'audits/q1-bounded-complementary-e1-xai/1.0.0';base.mkdir(parents=True)
        hashes={}
        for name,rows in zip(c.HASHES,groups):
            p=base/name;p.parent.mkdir(parents=True,exist_ok=True)
            data=b''.join((json.dumps(r)+'\n').encode() for r in rows);p.write_bytes(data);hashes[name]=c.sha(data)
        membership=c.sha((json.dumps([r['row_identifier'] for r in records],separators=(',',':'))+'\n').encode())
        with patch.object(c,'HASHES',hashes),patch.object(c,'MEMBERSHIP_SHA',membership):
            ids=c.load_frozen_identities(self.root)
            self.assertEqual(ids.temporal,ids.foreground[::-1])
            (base/next(iter(hashes))).write_bytes(b'changed')
            with self.assertRaises(c.Rejected):c.load_frozen_identities(self.root)

    def test_17_partial_disk_write_never_published(self):
        dest=self.root/'accepted'
        def partial(path,payload):
            path.write_bytes(payload[:10])
            raise OSError('synthetic disk failure')
        with patch.object(c,'write_private',side_effect=partial):
            with self.assertRaises(c.Rejected):c.publish_synthetic(b''.join(self.lines),dest,self.ids,self.expected)
        self.assertFalse(dest.exists())
        self.assertFalse(list(self.root.glob('.private-stage-*')))

    def test_18_ipc_response_tampering_rejected(self):
        raw=b''.join(self.lines)
        fake=json.dumps({'output':base64.b64encode(raw).decode(),
                         'output_sha256':'0'*64,'source_sha256':self.expected}).encode()
        with patch.object(c.subprocess,'run',return_value=subprocess.CompletedProcess([],0,fake,b'')):
            self.reject()

    def test_19_line_byte_limit_and_missing_LF(self):
        raw=self.lines[0]
        allowed=raw[:-1]+b' '*(c.LINE_LIMIT-len(raw))+b'\n'
        self.assertEqual(c.validate_line(allowed,self.ids.temporal[0]),allowed)
        for bad in [allowed[:-1]+b' \n',raw[:-1]]:
            with self.assertRaises(c.Rejected):c.validate_line(bad,self.ids.temporal[0])


if __name__=='__main__':unittest.main()
