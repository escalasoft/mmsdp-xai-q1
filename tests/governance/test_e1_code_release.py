"""Final release tests: invented fixtures; never call production_entry/extract_real."""
import ast
from datetime import datetime,timezone,timedelta
import dataclasses
import errno
import json
import os
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch
import test_e1_code_coordinator as previous
from src.governance import e1_code_release as r
from src.governance import e1_code_candidate as c
from src.governance import e1_code_coordinator as k


class ReleaseTests(unittest.TestCase):
    make=previous.CoordinatorTests.make
    seal=previous.CoordinatorTests.seal
    tearDown=previous.CoordinatorTests.tearDown
    def setUp(self):previous.CoordinatorTests.setUp(self)
    def approve(self,**changes):
        now=datetime.now(timezone.utc);s=(self.root/'scientific.lock').stat()
        self.auth=dict(version='1.0.0',decision='APPROVE_ONCE',scope='INVENTED_ONLY',
          approval_id='a'*64,release_sha256=r.release()[1],contract_sha256=self.contract_sha,
          inventory_sha256=c.sha((r.AUDIT/'consumers.json').read_bytes()),
          approved_at=now.isoformat(),expires_at=(now+timedelta(seconds=240)).isoformat(),
          lock_device=s.st_dev,lock_inode=s.st_ino,all_consumers_stopped=True,
          no_other_scientific_processes=True,source_writer_stopped=True,staging_reviewed=True,
          human_reviewer='SYNTHETIC_TEST_ONLY')
        self.auth.update(changes)
        (self.root/'permission_C.json').write_bytes(k.canonical(self.auth))
    def run_it(self):return r.synthetic_entry(self.root,self.contract_sha)
    def check(self,status):
        result=self.run_it();self.assertEqual(result.status,status)
        self.assertFalse(result.accepted);self.assertFalse((self.root/'validated').exists())
        self.assertNotIn('T2_SECRET',str(result));return result
    def test_01_absent_approval_never_captures(self):
        with patch.object(k,'capture') as cap:
            self.assertEqual(self.check('FAIL').reason,'AUTHORIZATION_ABSENT');cap.assert_not_called()
        self.assertFalse((self.root/'attempt.json').exists())
    def test_02_invalid_and_incompatible_authorizations(self):
        for changes in [dict(decision='NO'),dict(scope='CODE_ACTIVEMQ_T1'),dict(release_sha256='0'*64),
                        dict(contract_sha256='0'*64),dict(inventory_sha256='0'*64),
                        dict(all_consumers_stopped=False),dict(approval_id='bad'),dict(extra='bad')]:
            self.approve(**changes)
            with patch.object(k,'capture') as cap:self.check('FAIL');cap.assert_not_called()
    def test_03_expiry_and_lock_substitution(self):
        self.approve(approved_at=(datetime.now(timezone.utc)-timedelta(hours=1)).isoformat());self.check('FAIL')
        self.approve();old=self.root/'scientific.lock';old.rename(self.root/'old.lock');old.touch();self.check('FAIL')
    def test_04_success_exact_bytes_receipt_and_reuse(self):
        self.approve();result=self.run_it();self.assertEqual(result,r.Outcome('PASS','COMPLETE',True))
        out=self.root/'validated';self.assertEqual((out/'code_t1.jsonl').read_bytes(),b''.join(self.lines))
        prov=json.loads((out/'provenance.json').read_text());self.assertEqual(prov['source_sha256'],c.sha(self.payload))
        self.assertEqual(prov['authorization_sha256'],c.sha((self.root/'permission_C.json').read_bytes()))
        for p in out.iterdir():self.assertNotIn(b'T2_SECRET_SENTINEL',p.read_bytes())
        self.assertTrue(json.loads((self.root/'completion.json').read_text())['accepted'])
        with patch.object(k,'capture') as cap:
            again=self.run_it();self.assertEqual(again.status,'FAIL');self.assertFalse(again.accepted);cap.assert_not_called()
    def test_05_failed_attempt_cannot_be_reused(self):
        self.approve();self.source.write_bytes(b'x'+self.payload[1:]);self.check('FAIL')
        self.assertTrue((self.root/'attempt.json').exists());self.source.write_bytes(self.payload)
        with patch.object(k,'capture') as cap:self.check('FAIL');cap.assert_not_called()
    def test_06_worker_identity_failure_is_FAIL(self):
        self.make(lines=self.lines[::-1]);self.approve();self.check('FAIL')
        self.assertFalse(json.loads((self.root/'completion.json').read_text())['accepted'])
    def test_07_timeout_inconclusive_no_retry(self):
        self.approve()
        with patch.object(r,'run_worker',side_effect=subprocess.TimeoutExpired('synthetic',10)) as worker:
            self.check('INCONCLUSIVE');self.assertEqual(worker.call_count,1)
    def test_08_interruption_and_resource_classification(self):
        for exc in [KeyboardInterrupt('T2_SECRET'),MemoryError('T2_SECRET'),OSError(errno.ENOSPC,'T2_SECRET')]:
            self.assertEqual(r.classify(exc).status,'INCONCLUSIVE');self.assertNotIn('T2_SECRET',str(r.classify(exc)))
        self.approve()
        with patch.object(r,'run_worker',side_effect=KeyboardInterrupt('T2_SECRET')):self.check('INCONCLUSIVE')
    def test_09_concurrent_source_change(self):
        self.approve();original=r.run_worker
        def race(*args):
            output=original(*args);self.source.write_bytes(b'changed');return output
        with patch.object(r,'run_worker',side_effect=race):self.check('INCONCLUSIVE')
    def test_10_lease_conflict_and_no_claim(self):
        self.approve()
        with k.cooperative_lease(self.root,consumer=True):self.check('INCONCLUSIVE')
        self.assertFalse((self.root/'attempt.json').exists())
    def test_11_partial_publication_rejected(self):
        self.approve()
        with patch.object(c,'rename_exclusive',side_effect=c.Rejected('PUBLICATION_REJECTED')):self.check('FAIL')
        self.assertFalse(list(self.root.glob('.private-stage-*')))
    def test_12_uncertain_after_rename_not_accepted(self):
        self.approve();original=c.rename_exclusive
        def crash(*args):original(*args);raise KeyboardInterrupt('T2_SECRET')
        with patch.object(c,'rename_exclusive',side_effect=crash):
            result=self.run_it();self.assertEqual(result.status,'INCONCLUSIVE');self.assertFalse(result.accepted)
        self.assertFalse(json.loads((self.root/'completion.json').read_text())['accepted'])
    def test_13_receipt_failure_never_PASS(self):
        self.approve();original=c.write_private
        def fail(path,payload):
            if path.name=='completion.json':raise OSError(errno.ENOSPC,'T2_SECRET')
            original(path,payload)
        with patch.object(c,'write_private',side_effect=fail):
            result=self.run_it();self.assertEqual(result.status,'INCONCLUSIVE');self.assertFalse(result.accepted)
        self.assertFalse((self.root/'completion.json').exists())
    def test_14_no_real_entry_called_static_fixed_contract(self):
        node=next(n for n in ast.parse(Path(r.__file__).read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='production_entry')
        self.assertFalse(node.args.args);self.assertIn('production_contract.json',ast.unparse(node))
        self.assertFalse((k.REPO/'audits/q1-e1-code-permission-c/1.0.0/permission_C.json').exists())
        # Same gate, production scope, invented paths; no call to production_entry.
        ctx=r.Context(self.root,self.source,c.sha(self.payload),self.root/'fixture_contract.json',
                      self.contract_sha,'CODE_ACTIVEMQ_T1',None)
        with patch.object(k,'capture') as cap:
            self.assertEqual(r._execute(ctx).reason,'AUTHORIZATION_ABSENT');cap.assert_not_called()
    def test_15_approval_modified_before_commit(self):
        self.approve();original=r.run_worker
        def change(*args):
            result=original(*args);self.approve(approval_id='b'*64);return result
        with patch.object(r,'run_worker',side_effect=change):self.check('FAIL')
    def test_16_no_auxiliary_payload_copies(self):
        self.approve();before=set(self.root.iterdir());self.assertTrue(self.run_it().accepted)
        self.assertEqual({p.name for p in set(self.root.iterdir())-before},{'attempt.json','completion.json','validated'})
    def test_17_claim_exclusive(self):
        self.approve();ctx=r.Context(self.root,self.source,c.sha(self.payload),self.root/'fixture_contract.json',self.contract_sha,'INVENTED_ONLY',self.ids)
        r.claim(ctx,'a'*64)
        with self.assertRaises(r.Stop) as e:r.claim(ctx,'b'*64)
        self.assertEqual(e.exception.reason,'AUTHORIZATION_REUSED')
    def test_18_staging_residue_rejects_before_claim(self):
        self.approve();(self.root/'.private-stage-residue').mkdir();self.check('FAIL')
        self.assertFalse((self.root/'attempt.json').exists())

if __name__=='__main__':unittest.main()
