"""Focused synthetic checks for identity-only E2 population materialization."""
import json
from pathlib import Path
import subprocess
import sys

import pytest

from src.evaluation import q1_e2_t1_foreground_freeze as m


def candidates(n=300):
    return [dict(project='fixture', partition='T1', row_identifier=f'{i:064x}') for i in range(n)]


def test_exact_parent_selection_and_permutation_invariance():
    data = candidates()
    first = m.select(data, 'fixture', None, 'T1_GLOBAL_FOREGROUND_SELECTION', 256)
    second = m.select(list(reversed(data)), 'fixture', None, 'T1_GLOBAL_FOREGROUND_SELECTION', 256)
    assert first == second
    assert len(first) == 256
    assert first == m.independent_selection(data, 'fixture', None, 'T1_GLOBAL_FOREGROUND_SELECTION', 256)


def test_local_scope_key_and_subset():
    fg = m.select(candidates(), 'fixture', None, 'T1_GLOBAL_FOREGROUND_SELECTION', 256)
    stripped = [{k: r[k] for k in ['project', 'partition', 'row_identifier']} for r in fg]
    local = m.select(stripped, 'fixture', 'model-A', 'T1_LOCAL_CASE_SELECTION', 8)
    assert len(local) == 8
    assert {r['row_identifier'] for r in local} <= {r['row_identifier'] for r in fg}
    other = m.select(stripped, 'fixture', 'model-B', 'T1_LOCAL_CASE_SELECTION', 8)
    assert local != other
    assert len(m.select(candidates(3), 'fixture', None, 'T1_GLOBAL_FOREGROUND_SELECTION', 256)) == 3


@pytest.mark.parametrize('field', ['class', 'label', 'confidence', 'correctness', 'prediction', 'SHAP'])
def test_selection_rejects_forbidden_fields(field):
    with pytest.raises(m.parent.FreezeError):
        m.select([{**candidates(1)[0], field: 1}], 'fixture', None, 'T1_GLOBAL_FOREGROUND_SELECTION', 256)


def test_t2_duplicates_and_project_mismatch_rejected():
    for rows in [[{**candidates(1)[0], 'partition': 'T2'}], candidates(1)*2,
                 [{**candidates(1)[0], 'project': 'other'}]]:
        with pytest.raises(m.parent.FreezeError):
            m.select(rows, 'fixture', None, 'T1_GLOBAL_FOREGROUND_SELECTION', 256)


def test_projection_is_invariant_to_outcomes():
    identity = dict(project='fixture', row_identifier='a'*64, algorithm='fixture',
                    configuration='C+P', model_identity_sha256='b'*64)
    for label, prob in [(0, 0.001), (1, 0.999)]:
        payload = {**identity, 'benchmark_defined_observed_label': label,
                   'raw_predicted_probability': prob, 'fixed_threshold_prediction': label,
                   'model_provenance': {'training_partition': 'TRAIN'}}
        assert json.loads(json.dumps(payload), object_pairs_hook=m.identity_projection) == identity


def test_provenance_hashes_and_local_scope_schema():
    data = candidates(5)
    selected = m.select(data, 'fixture', None, 'T1_GLOBAL_FOREGROUND_SELECTION', 256)
    annotated = m.annotate(selected, [r['row_identifier'] for r in data])
    assert [r['ordinal'] for r in annotated] == [1, 2, 3, 4, 5]
    assert all(r['count'] == 5 and 'class' not in r for r in annotated)
    assert annotated[0]['source_membership_digest'] == m.digest([r['row_identifier'] for r in data])
    assert annotated[0]['ordering_hash'] == m.digest([r['row_identifier'] for r in selected])


def test_unknown_source_is_rejected_before_open():
    with pytest.raises(m.FreezeError, match='before open'):
        m.load_candidates([], {'path': 'data/forbidden-T2.gz'})


def test_worker_guard_blocks_unapproved_scientific_reads(tmp_path):
    # Read-denial is checked before open even if the named file does not exist.
    script = """
from pathlib import Path
from src.evaluation import q1_e2_t1_foreground_freeze as m
m.install_guard(Path(%r))
try:
    (m.ROOT/'data/forbidden-T2.gz').read_bytes()
except m.FreezeError:
    print('DENIED_BEFORE_OPEN')
else:
    raise RuntimeError('guard failed')
""" % str(tmp_path/'result.json')
    proc = subprocess.run([sys.executable, '-B', '-c', script], cwd=m.ROOT,
                          text=True, capture_output=True)
    assert proc.returncode == 0, proc.stderr
    assert 'DENIED_BEFORE_OPEN' in proc.stdout
