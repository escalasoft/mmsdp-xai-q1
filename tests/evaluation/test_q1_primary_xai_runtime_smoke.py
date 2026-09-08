"""Sprint 56.1 focused governance and persisted numerical checks."""
import ast
import gzip
import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'audits/q1-primary-xai-runtime-smoke/1.0.0'
SOURCE = ROOT / 'src/evaluation/q1_primary_xai_runtime_smoke.py'
spec = importlib.util.spec_from_file_location('s56_smoke', SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def load(name):
    return json.loads((OUT / name).read_text())


def test_environment_separation_and_inventory_preservation():
    lock = load('isolated_runtime_lock.json')
    assert Path(lock['environment']).resolve() == ROOT / '.venv-xai-s56'
    assert Path(lock['environment']).resolve() != ROOT / '.venv'
    assert 'include-system-site-packages = false' in (ROOT / '.venv-xai-s56/pyvenv.cfg').read_text()
    assert load('predictive_inventory_before.json') == load('predictive_inventory_after.json')
    assert module.inventory() == load('predictive_inventory_before.json')
    assert '/.venv-xai-s56/' in (ROOT / '.gitignore').read_text().splitlines()
    assert all(v == '1' for v in lock['threads'].values())


def test_all_object_hashes_and_protected_evidence_unchanged():
    before = load('preexecution_integrity.json')
    after = load('postexecution_integrity.json')
    assert before['objects'] == after['objects'] == module.store_snapshot()
    assert before['protected'] == after['protected'] == module.protected_snapshot()


def test_selection_is_deterministic_performance_independent_and_eligible():
    assert json.loads(module.canonical(module.select_scopes())) == load('representative_scope_selection.json')
    selection = load('representative_scope_selection.json')
    assert len(selection['scopes']) == 5 and selection['universe'] == 389
    assert selection['project'] == 'apache/activemq'
    assert len(selection['excluded_scopes']) == 3
    pop = load('train_only_population_manifest.json')
    ids = pop['train_ids_chronological']
    for role, budget in [('background', 64), ('foreground', 16)]:
        ordered = sorted(ids, key=lambda rid:(hashlib.sha256(
            f'S56.1|{selection["project"]}|{role}|{rid}'.encode()).hexdigest(), rid))
        assert ordered[:budget] == pop[role]
    local = sorted(pop['foreground'], key=lambda rid:(hashlib.sha256(
        f'S56.1|local|{rid}'.encode()).hexdigest(), rid))[:4]
    assert local == pop['local']
    assert set(pop['local']) <= set(pop['foreground'])
    assert set(pop['background'] + pop['foreground']) <= set(ids)
    assert module.sha(OUT / 'selected_train_rows.json') == pop['rows_sha256']
    assert {r['partition'] for r in load('selected_train_rows.json')} == {'TRAIN'}
    assert pop['non_TRAIN_rows_read'] == pop['non_TRAIN_rows_decoded'] == 0


def test_prefix_reader_does_not_decode_or_scan_tail(tmp_path, monkeypatch):
    monkeypatch.setattr(module, 'ROOT', tmp_path)
    p = tmp_path / 'prefix.gz'
    prefix = b'{"partition":"TRAIN"}\n' * 80
    # A corrupt trailing member must remain unreachable; no full gzip traversal.
    p.write_bytes(gzip.compress(prefix + b'VALIDATION\n' * 1000) + b'INVALID_T1_T2_TAIL')
    rows, evidence = module.bounded_gzip_prefix(p, 80)
    assert b''.join(rows) == prefix
    assert evidence['compressed_bytes_read'] < p.stat().st_size
    assert evidence['decompressed_lines_read'] == 80
    assert evidence['decode_limit_bytes'] == evidence['read_unit_bytes'] == 1
    assert not evidence['full_file_hash_or_tail_scan']


def test_guard_denies_protected_reads_and_state_writes():
    for p in [ROOT / 'data/anything', module.FREEZE / 'text_dataset.jsonl.gz',
              ROOT / 'audits/q1-t1-confirmatory-execution/1.0.0/results/anything']:
        with pytest.raises(PermissionError):
            module.guard('open', (str(p), 'rb', 0))
    for p in [module.STORE / 'objects/model.joblib', ROOT / '.venv/pyvenv.cfg']:
        with pytest.raises(PermissionError):
            module.guard('open', (str(p), 'wb', 0))
    events = load('runtime_read_events.json')['paths']
    assert not any('q1-t1-' in p or 'q1-apachejit-final-dataset-freeze' in p or p.startswith('data/') for p in events)


def test_no_reconstruction_refit_metrics_or_unapproved_explainers():
    tree = ast.parse(SOURCE.read_text())
    forbidden = {'fit', 'fit_transform', 'partial_fit', 'train', 'dump', 'save_model',
                 'roc_auc_score', 'average_precision_score', 'f1_score', 'matthews_corrcoef',
                 'precision_score', 'recall_score', 'brier_score_loss', 'permutation_importance'}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            assert node.func.attr not in forbidden
        if isinstance(node, ast.ImportFrom):
            assert not any(s in (node.module or '') for s in ['reconstruction', 'sklearn.metrics', 'lime', 'dice'])
    counters = load('runtime_governance_counters.json')
    for k in ['T1_XAI_ACCESS_COUNT', 'T1_XAI_MODEL_QUERY_COUNT', 'T1_XAI_ROW_READ_COUNT',
              'T2_ACCESS_COUNT', 'predictive_metric_count', 'artifact_mutation_count',
              'reconstruction_count', 'refit_count', 'retraining_count', 'recalibration_count']:
        assert counters[k] == 0
    assert counters['T2_STATE'] == 'DENY_SEALED_REVIEWER_RESERVE'
    assert counters['historical_Sprint54_predictive_access_scoring'] == [1, 1]


def test_lock_is_frozen_before_scientific_execution_and_wheels_are_hashed():
    start = load('smoke_execution_started.json')
    lock = load('isolated_runtime_lock.json')
    assert start['lock_sha256'] == module.sha(OUT / 'isolated_runtime_lock.json')
    assert lock['timestamp_before_explainer_import'] < start['timestamp']
    assert module.TOLERANCES == load('isolated_runtime_spec.json')['tolerances']
    assert all(w['url'].endswith('.whl') and len(w['hashes']['sha256']) == 64 for w in lock['wheels'])
    assert load('isolated_runtime_installation_provenance.json')['source_build_count'] == 0


@pytest.mark.parametrize('name', ['lr_analytical_smoke.json', 'fusion_analytical_smoke.json'])
def test_analytical_formulas_independently_from_persisted_contributions(name):
    result = load(name)
    if 'run_1' not in result:
        assert result['outcome'].endswith('_FAIL') and result['error']
        return
    for run in [result['run_1'], result['run_2']]:
        c = np.asarray(run['contribution_vector'])
        eta = run['intercept'] + c.sum(axis=1)
        predicted = np.asarray(run['predictor_logit'])
        assert np.all(np.abs(eta - predicted) <= 1e-10 * (1 + np.abs(predicted)))
        assert np.all(np.abs(1/(1+np.exp(-eta)) - run['predictor_probability']) <= 1e-10)
        if 'centered_contributions' in run:
            probabilities = np.asarray(run['modality_probabilities'])
            coef = np.asarray(run['coefficient'])
            mu = np.asarray(run['reference_modality_probabilities']).mean(axis=0)
            assert np.array_equal(c, probabilities * coef)
            centered = (probabilities - mu) * coef
            assert np.array_equal(centered, run['centered_contributions'])
            baseline = run['intercept'] + np.sum(coef * mu)
            assert np.all(np.abs(baseline + centered.sum(axis=1) - predicted) <= 1e-10 * (1 + np.abs(predicted)))


@pytest.mark.parametrize('name', ['rf_treeshap_smoke.json', 'xgb_treeshap_smoke.json', 'lgb_treeshap_smoke.json'])
def test_exact_tree_contract_and_recorded_additivity(name):
    result = load(name)
    if 'run_1' not in result:
        assert result['outcome'].endswith('_FAIL') and result['error']
        return
    for run in [result['run_1'], result['run_2']]:
        assert run['explainer']['approximate'] is False
        assert run['explainer']['feature_perturbation'] == 'tree_path_dependent'
        assert run['explainer']['model_output'] == 'raw'
        # XGBoost's native TreeSHAP returns float32; JSON numbers do not retain
        # dtype. Restore native arithmetic, then additionally verify float64.
        dtype = np.float32 if name == 'xgb_treeshap_smoke.json' else np.float64
        output = np.asarray(run['model_output'], dtype=dtype)
        residual = run['base_value'] + np.asarray(run['contribution_vector'], dtype=dtype).sum(axis=1) - output
        assert np.array_equal(residual, run['residual'])
        assert run['pass'] == bool(np.all(np.abs(residual) <= 1e-6 * (1 + np.abs(output))))
        output64 = np.asarray(run['model_output'], dtype=np.float64)
        residual64 = run['base_value'] + np.asarray(run['contribution_vector'], dtype=np.float64).sum(axis=1) - output64
        assert np.all(np.abs(residual64) <= 1e-6 * (1 + np.abs(output64)))


def test_narrow_ignores_without_historical_worktree_size_assumption():
    for path, expected in [('.venv-xai-s56/pyvenv.cfg', 0),
        ('audits/q1-primary-xai-runtime-smoke/1.0.0/isolated_runtime_lock.json', 1),
        ('audits/q1-xai-reconstruction-execution/1.0.0/external_artifact_registry/external_artifact_summary.json', 1),
        ('audits/q1-xai-final-output-equivalence-g5/1.0.0/g5_summary.json', 1)]:
        assert subprocess.run(['git', 'check-ignore', '-q', path], cwd=ROOT).returncode == expected
    sample = next((module.STORE / 'objects').iterdir())
    assert subprocess.run(['git', 'check-ignore', '-q', str(sample.relative_to(ROOT))], cwd=ROOT).returncode == 0
    assert not set((ROOT / '.gitignore').read_text().splitlines()) & {'audits/', '/audits/', '*.joblib', '*.npy', '*.pkl'}


def test_repeat_differences_recomputed_without_tolerance_relaxation():
    records = load('determinism_smoke.json')
    assert records['tolerance'] == 1e-12
    for key, name in [('lr','lr_analytical'),('rf','rf_treeshap'),('xgb','xgb_treeshap'),
                      ('lgb','lgb_treeshap'),('fusion','fusion_analytical')]:
        result = load(name + '_smoke.json')
        r = records['families'][key]
        if 'run_1' not in result:
            assert not r['pass']
            continue
        diffs = [np.max(np.abs(np.asarray(result['run_1']['contribution_vector']) - result['run_2']['contribution_vector']))]
        if key == 'fusion':
            diffs.append(np.max(np.abs(np.asarray(result['run_1']['centered_contributions']) - result['run_2']['centered_contributions'])))
        assert max(diffs) == r['max_absolute_attribution_difference']
        assert r['pass'] == (max(diffs) <= 1e-12)


def test_manifest_exact_and_primary_execution_unauthorized():
    manifest = {}
    for line in (OUT / 'MANIFEST.sha256').read_text().splitlines():
        digest, name = line.split('  ', 1)
        assert name not in manifest
        manifest[name] = digest
    assert set(manifest) == {p.name for p in OUT.iterdir() if p.is_file() and p.name != 'MANIFEST.sha256'}
    assert all(module.sha(OUT / name) == digest for name, digest in manifest.items())
    assert load('sprint56_2_authorization_prerequisites.json')['Sprint56_2_authorized'] is False
