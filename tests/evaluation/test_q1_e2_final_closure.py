"""E2-only synthetic algebra, governance and failure-policy tests."""
import hashlib
import struct

import numpy as np
import pytest
from scipy.special import expit

from src.evaluation import q1_e2_final_closure as m


def test_centered_logit_and_probability_reconstruct_with_signed_terms():
    p=np.array([[.1,.9],[.8,.2]])
    beta=np.array([2.,-3.]);mu=np.array([.4,.5]);alpha=.25
    base,phi,eta,z,prob=m.decompose(p,beta,alpha,mu)
    np.testing.assert_allclose(eta,alpha+p@beta,rtol=0,atol=1e-14)
    np.testing.assert_allclose(base+phi.sum(1),z,rtol=0,atol=1e-14)
    np.testing.assert_allclose(prob,expit(z),rtol=0,atol=1e-14)
    assert phi[0,0]<0 and phi[1,1]>0


def test_order_is_not_alphabetically_replaced():
    p=np.array([[.8,.1,.6]]);beta=np.array([-4.,3.,2.]);mu=np.array([.2,.5,.4])
    a=m.decompose(p,beta,.2,mu)
    order=[2,0,1]
    b=m.decompose(p[:,order],beta[order],.2,mu[order])
    np.testing.assert_allclose(a[2],b[2],atol=1e-14)
    assert not np.allclose(a[2],m.decompose(p,beta[order],.2,mu)[2])


def test_repetitions_exact_and_boundary_probabilities_finite():
    args=(np.array([[0.,1.],[1.,0.]]),np.array([100.,-100.]),.1,np.array([.5,.5]))
    first=m.decompose(*args);second=m.decompose(*args)
    for a,b in zip(first,second):
        assert np.asarray(a).tobytes()==np.asarray(b).tobytes()
    assert np.isfinite(first[-1]).all()


@pytest.mark.parametrize('bad', [np.array([[np.nan,.1]]),np.array([[1.01,.1]]),np.array([[.1]])])
def test_invalid_inputs_fail_closed(bad):
    with pytest.raises(m.ClosureError):
        m.decompose(bad,np.array([1.,2.]),0.,np.array([.1,.2]))


def test_reference_lookup_uses_explicit_modality_order_and_rejects_t1():
    records=[]
    for mod,mu in [('C',.2),('P',.8)]:
        records.append(dict(project='p',algorithm='a',modality=mod,mu=mu,mu_hex=mu.hex(),
            mean_sha256=hashlib.sha256(struct.pack('<d',mu)).hexdigest(),source_partition='TRAIN_META_OOF',
            primary_reference='PRIMARY_REFERENCE_OOF',ordered_identity_digest='frozen'))
    means={(r['project'],r['algorithm'],r['modality']):r for r in records}
    scope=dict(project='p',algorithm='a',modality_order=['P','C'],primary_reference_status='PRIMARY_REFERENCE_OOF',
               meta_training_membership_sha256='frozen',primary_mean_records=records)
    np.testing.assert_array_equal(m.ordered_means(scope,means),[.8,.2])
    records[0]['source_partition']='T1'
    with pytest.raises(m.ClosureError):m.ordered_means(scope,means)


def test_eligibility_does_not_accept_empty_or_unimodal_replacement():
    with pytest.raises(m.ClosureError):m.eligible([],[])
    scopes=[dict(project=str(i),algorithm='a',configuration='C',model_identity_sha256=str(i)) for i in range(221)]
    with pytest.raises(m.ClosureError):m.eligible(scopes,[])


def test_worker_t2_read_guard_denies_before_open(tmp_path):
    import subprocess,sys
    code=f'''from pathlib import Path
from src.evaluation import q1_e2_final_closure as m
m.guard_worker(Path({str(tmp_path)!r}), [])
try:
 (m.ROOT/'data/T2-forbidden.gz').read_bytes()
except m.ClosureError:
 print('DENIED')
else:
 raise RuntimeError('guard failed')
'''
    result=subprocess.run([sys.executable,'-B','-c',code],cwd=m.ROOT,text=True,capture_output=True)
    assert result.returncode==0,result.stderr
    assert result.stdout.strip()=='DENIED'
