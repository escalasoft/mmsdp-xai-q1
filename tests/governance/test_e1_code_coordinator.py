"""Invented fixtures only. No actual CODE payload is opened by these tests."""
import base64
import dataclasses
import gzip
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
from src.governance import e1_code_coordinator as k
from src.governance import e1_code_candidate as c


class CoordinatorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='e1-code-coordinator-synthetic-',
                    dir=str(Path(tempfile.gettempdir()).resolve()))
        self.root = Path(self.tmp.name)
        (self.root / 'scientific.lock').touch(mode=0o600)
        seq = tuple(c.sha(f'coordinator-invented-{i}'.encode()) for i in range(245))
        self.ids = c.Identities(seq, seq[::-1], seq[:8])
        self.lines = [(' {"row_identifier":"'+s+'","la":1,"ld":-0,"nf":1.00,'
                       '"nd":2e0,"ns":3E-0,"ent":0.1234567890123456789} \n').encode() for s in seq]
        self.make()

    def tearDown(self): self.tmp.cleanup()

    def make(self, lines=None, tail=b'T2_SECRET_SENTINEL\n'):
        self.prefix = b'NOT_JSON_TRAIN_VALIDATION\n'*4900
        compressed = gzip.compress(self.prefix+b''.join(self.lines if lines is None else lines)+tail,mtime=0)
        self.payload = compressed + b'\0'*(c.SOURCE_SIZE-len(compressed))
        self.source = self.root/'fixture.code.jsonl.gz'
        self.source.write_bytes(self.payload)
        self.contract = dict(version='1.0.0', scope='INVENTED_ONLY', project='apache/activemq',partition='T1',
             source_sha256=c.sha(self.payload), limits=k.LIMITS, ids=dataclasses.asdict(self.ids))
        self.seal()

    def seal(self):
        raw=k.canonical(self.contract)
        (self.root/'fixture_contract.json').write_bytes(raw)
        self.contract_sha=c.sha(raw)

    def run_it(self):return k.run_synthetic(self.root,self.contract_sha)

    def rejected(self):
        with self.assertRaises(c.Rejected) as e:self.run_it()
        self.assertEqual(str(e.exception),'COORDINATOR_REJECTED')
        self.assertFalse((self.root/'validated').exists())

    def test_01_end_to_end_linkage_and_no_T2(self):
        original=k.capture; captured=[]
        def spy(*args):
            result=original(*args);captured.append(result[0]);return result
        worker=c.run_worker
        def consume(payload,*args):
            self.assertIs(payload,captured[0]);return worker(payload,*args)
        with patch.object(k,'capture',side_effect=spy),patch.object(c,'run_worker',side_effect=consume):
            out=self.run_it()
        raw=(out/'code_t1.jsonl').read_bytes();meta=json.loads((out/'provenance.json').read_text())
        self.assertEqual(raw,b''.join(self.lines))
        self.assertEqual(meta['source_sha256'],c.sha(self.payload))
        self.assertEqual((meta['output_sha256'],meta['output_bytes']),(c.sha(raw),len(raw)))
        self.assertEqual(meta['transport']['lines'],5145)
        self.assertEqual(meta['transport']['decoded_bytes'],len(self.prefix)+len(raw))
        self.assertIn('compressed_bytes_supplied',meta['transport'])
        self.assertEqual(set(p.name for p in out.iterdir()),{'code_t1.jsonl','provenance.json'})
        for p in out.iterdir():
            self.assertNotIn(b'T2_SECRET_SENTINEL',p.read_bytes())
            self.assertNotIn(b'NOT_JSON_TRAIN_VALIDATION',p.read_bytes())
        self.assertNotIn('0.1234567890123456789',(out/'provenance.json').read_text())
        self.assertEqual(len(captured),1)

    def test_02_preflight_contract_tamper(self):
        (self.root/'fixture_contract.json').write_bytes(b'{}');self.rejected()

    def test_03_release_code_hash_rejected_before_capture(self):
        original=c.sha
        def altered(raw):
            return '0'*64 if raw==Path(k.__file__).read_bytes() else original(raw)
        with patch.object(c,'sha',side_effect=altered),patch.object(k,'capture') as capture:
            self.rejected();capture.assert_not_called()

    def test_04_preflight_destination_and_residue(self):
        for name in ['validated','.private-stage-old']:
            p=self.root/name;p.mkdir()
            with patch.object(k,'capture') as capture:
                with self.assertRaises(c.Rejected):self.run_it()
                capture.assert_not_called()
            self.assertTrue(p.exists());p.rmdir()

    def test_05_consumer_and_coordinator_exclusion(self):
        for consumer in [True,False]:
            with k.cooperative_lease(self.root,consumer=consumer):
                with patch.object(k,'capture') as capture:self.rejected();capture.assert_not_called()

    def test_06_capture_hash_and_size_failures(self):
        for bad in [self.payload[:-1],b'x'+self.payload[1:]]:
            self.source.write_bytes(bad);self.rejected()

    def test_07_capture_race(self):
        original=os.read;changed=[False]
        def race(fd,n):
            block=original(fd,n)
            if not changed[0]:
                changed[0]=True
                other=self.root/'replacement';other.write_bytes(self.payload);os.replace(other,self.source)
            return block
        with patch.object(k.os,'read',side_effect=race):self.rejected()

    def test_08_source_changed_after_capture(self):
        original=c.run_worker
        def change(*args):
            out=original(*args);self.source.write_bytes(b'changed');return out
        with patch.object(c,'run_worker',side_effect=change):self.rejected()
        self.assertFalse(list(self.root.glob('.private-stage-*')))

    def test_09_identity_and_schema_failures(self):
        for bad in [self.lines[::-1],self.lines[:-1]+[self.lines[0]],
                    self.lines[:-1]+[b'{"secret":"T2_SECRET_SENTINEL"}\n']]:
            self.make(lines=bad);self.rejected()

    def test_10_independent_response_counters_and_hashes(self):
        raw=b''.join(self.lines)
        good={'output':base64.b64encode(raw).decode(),'output_sha256':c.sha(raw),
              'source_sha256':c.sha(self.payload),'transport':{'lines':5145,
              'decoded_bytes':len(self.prefix)+len(raw),'compressed_bytes_consumed':100}}
        mutations=[('lines',5146),('lines',True),('decoded_bytes',4194305),
                   ('decoded_bytes',len(raw)),('compressed_bytes_consumed',0)]
        for key,value in mutations:
            response=json.loads(json.dumps(good));response['transport'][key]=value
            with patch.object(c,'run_worker',return_value=(raw,response)):self.rejected()
        for key in ['source_sha256','output_sha256']:
            response=dict(good);response[key]='0'*64
            with patch.object(c,'run_worker',return_value=(raw,response)):self.rejected()

    def test_11_ipc_errors_sanitized(self):
        with patch.object(c,'run_worker',side_effect=ValueError('T2_SECRET_SENTINEL')):
            self.rejected()

    def test_12_disk_corruption_never_published(self):
        original=c.write_private
        def corrupt(path,raw):original(path,raw+b'x' if path.name=='code_t1.jsonl' else raw)
        with patch.object(c,'write_private',side_effect=corrupt):self.rejected()
        self.assertFalse(list(self.root.glob('.private-stage-*')))

    def test_13_publication_failure_and_no_overwrite(self):
        with patch.object(c,'rename_exclusive',side_effect=OSError('T2_SECRET_SENTINEL')):self.rejected()
        self.assertFalse(list(self.root.glob('.private-stage-*')))
        out=self.run_it();raw=(out/'code_t1.jsonl').read_bytes()
        with self.assertRaises(c.Rejected):self.run_it()
        self.assertEqual((out/'code_t1.jsonl').read_bytes(),raw)

    def test_14_atomic_visibility_permissions(self):
        original=c.rename_exclusive
        def inspect(stage,dest):
            self.assertFalse(dest.exists())
            self.assertEqual(stat.S_IMODE(stage.stat().st_mode),0o700)
            for p in stage.iterdir():self.assertEqual(stat.S_IMODE(p.stat().st_mode),0o600)
            self.assertEqual((stage/'code_t1.jsonl').read_bytes(),b''.join(self.lines))
            original(stage,dest)
        with patch.object(c,'rename_exclusive',side_effect=inspect):self.run_it()

    def test_15_timeout_no_publication_no_retry(self):
        original=subprocess.run;started=time.monotonic();calls=[]
        def stall(*args,**kwargs):
            calls.append(1);self.assertEqual(kwargs['timeout'],10)
            return original([sys.executable,'-I','-B','-c','import time;time.sleep(30)'],
                            capture_output=True,timeout=kwargs['timeout'])
        with patch.object(c.subprocess,'run',side_effect=stall):self.rejected()
        self.assertEqual(len(calls),1);self.assertLess(time.monotonic()-started,15)

    def test_16_tail_independence(self):
        outputs=[]
        for tail in [b'T2_A\n',b'T2_B_INVALID_JSON'*1000]:
            self.make(tail=tail);out=self.run_it();outputs.append((out/'code_t1.jsonl').read_bytes())
            import shutil
            shutil.rmtree(out)
        self.assertEqual(outputs[0],outputs[1])

    def test_17_no_auxiliary_payload_writes(self):
        before=set(p.name for p in self.root.iterdir())
        self.run_it()
        self.assertEqual(set(p.name for p in self.root.iterdir()),before|{'validated'})

    def test_18_fixed_paths_limits_and_production_gate(self):
        spec=k.production_specification()
        self.assertFalse(spec['permission_C']);self.assertEqual(spec['limits'],k.LIMITS)
        # This new guard is not extract_real; no source access is possible.
        with patch.object(k,'capture') as capture:
            with self.assertRaises(c.Rejected):k.run_production()
            capture.assert_not_called()
        self.contract['limits']=dict(k.LIMITS,line_bytes=4097);self.seal();self.rejected()

    def test_19_symlink_and_hardlink_source_denied(self):
        other=self.root/'other';self.source.rename(other);self.source.symlink_to(other);self.rejected()
        self.source.unlink();os.link(other,self.source);self.rejected()

    def test_20_capture_not_reopened_for_extraction(self):
        original=os.open;opens=[]
        def track(path,*args,**kwargs):
            if Path(path)==self.source:opens.append(1)
            return original(path,*args,**kwargs)
        with patch.object(k.os,'open',side_effect=track):self.run_it()
        self.assertEqual(opens,[1])

    def test_21_contract_modified_during_worker(self):
        original=c.run_worker
        def changed(*args):
            out=original(*args);(self.root/'fixture_contract.json').write_bytes(b'{}');return out
        with patch.object(c,'run_worker',side_effect=changed):self.rejected()

    def test_22_partial_write_and_racing_destination(self):
        def partial(path,data):path.write_bytes(data[:12]);raise OSError('failure')
        with patch.object(c,'write_private',side_effect=partial):self.rejected()
        original=c.rename_exclusive
        def race(stage,dest):dest.mkdir();original(stage,dest)
        with patch.object(c,'rename_exclusive',side_effect=race):
            with self.assertRaises(c.Rejected):self.run_it()
        self.assertEqual(list((self.root/'validated').iterdir()),[])


    def test_23_forged_valid_hash_wrong_identity_and_numeric_type(self):
        for raw in [b''.join(self.lines[::-1]),
                    b''.join(self.lines).replace(b'"la":1',b'"la":true',1)]:
            response={'output':base64.b64encode(raw).decode(),'output_sha256':c.sha(raw),
                      'source_sha256':c.sha(self.payload),'transport':{'lines':5145,
                      'decoded_bytes':len(self.prefix)+len(raw),'compressed_bytes_consumed':100}}
            with patch.object(c,'run_worker',return_value=(raw,response)):self.rejected()

    def test_24_separate_process_cooperative_consumer_blocks(self):
        code = "import fcntl,sys; f=open(sys.argv[1],'rb'); fcntl.flock(f,fcntl.LOCK_SH); print('READY',flush=True); sys.stdin.read()"
        proc=subprocess.Popen([sys.executable,'-I','-B','-c',code,str(self.root/'scientific.lock')],
                              stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        try:
            self.assertEqual(proc.stdout.readline(),b'READY\n')
            with patch.object(k,'capture') as capture:self.rejected();capture.assert_not_called()
        finally:
            proc.communicate(timeout=5)
        self.assertEqual(proc.returncode,0)

    def test_25_outer_logs_and_errors_do_not_expose_payloads(self):
        from contextlib import redirect_stdout,redirect_stderr
        out,err=io.StringIO(),io.StringIO()
        with redirect_stdout(out),redirect_stderr(err):
            with patch.object(c,'run_worker',side_effect=ValueError('T2_SECRET_SENTINEL')):self.rejected()
        self.assertEqual((out.getvalue(),err.getvalue()),('',''))

    def test_26_production_plan_denied_by_shared_engine(self):
        plan=k.Plan(self.root,self.source,self.ids,c.sha(self.payload),
                    'PRODUCTION_NOT_AUTHORIZED',self.contract_sha,self.root/'fixture_contract.json')
        with patch.object(k,'capture') as capture:
            with self.assertRaises(c.Rejected):k._orchestrate(plan)
            capture.assert_not_called()

    def test_27_truncated_stream_even_with_matching_capture_hash(self):
        self.make(lines=self.lines[:1],tail=b'');self.rejected()

if __name__=='__main__':unittest.main()

