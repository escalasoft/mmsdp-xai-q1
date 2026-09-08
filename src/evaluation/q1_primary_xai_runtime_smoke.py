"""Sprint 56.1 only: isolated runtime, persisted states, bounded TRAIN smoke.

No reconstruction modules are imported. Never reads full mixed-population gzip
files: prefix extraction stops at the known first-project TRAIN boundary using
one compressed byte per read and one decompressed byte per decoder call.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
import warnings
import zlib
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'audits/q1-primary-xai-runtime-smoke/1.0.0'
STORE = ROOT / 'audits/q1-xai-reconstruction-execution/1.0.0'
FREEZE = ROOT / 'audits/q1-apachejit-final-dataset-freeze/1.0.0'
G5 = ROOT / 'audits/q1-xai-final-output-equivalence-g5/1.0.0'
BRANCH = 'sprint-10/q1-primary-xai-execution'
THREADS = ['OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
           'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS']
FEATURES = {'C': ['la', 'ld', 'nf', 'nd', 'ns', 'ent'],
            'P': ['ndev', 'age', 'nuc', 'aexp', 'arexp', 'asexp']}
TOLERANCES = {'analytical_relative': 1e-10, 'sigmoid_absolute': 1e-10,
              'tree_relative': 1e-6, 'repeat_absolute': 1e-12}
READ_EVENTS = []


def canonical(x):
    return (json.dumps(x, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                       allow_nan=False) + '\n').encode()


def digest(x):
    return hashlib.sha256(canonical(x)).hexdigest()


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def load(path):
    return json.loads(Path(path).read_text())


def save(name, x):
    (OUT / name).write_bytes(canonical(x))


def jsonlines(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def inventory():
    return {'python': platform.python_version(), 'packages': sorted(
        [{'name': d.metadata['Name'], 'version': d.version}
         for d in importlib.metadata.distributions()], key=lambda r: r['name'].lower())}


def branch_check():
    assert subprocess.check_output(['git', 'symbolic-ref', '--short', 'HEAD'],
                                   cwd=ROOT, text=True).strip() == BRANCH


def store_snapshot():
    registry = jsonlines(STORE / 'external_artifact_registry/external_artifact_inventory.jsonl')
    expected = {r['relative_path']: r for r in registry}
    physical = {p.relative_to(STORE).as_posix() for p in (STORE / 'objects').rglob('*') if p.is_file()}
    assert physical == set(expected)
    manifest = {line.split('  ', 1)[1]: line.split('  ', 1)[0]
                for line in (STORE / 'MANIFEST.sha256').read_text().splitlines()
                if line.split('  ', 1)[1].startswith('objects/')}
    assert set(manifest) == physical
    rows = []
    for name in sorted(physical):
        r = expected[name]
        assert sha(STORE / name) == r['sha256'] == manifest[name]
        assert (STORE / name).stat().st_size == r['size_bytes']
        rows.append({k: r[k] for k in ['relative_path', 'filename', 'sha256', 'size_bytes',
                                     'extension_type', 'artifact_type']})
    snapshot_hash = hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(',', ':'),
                                               ensure_ascii=False).encode()).hexdigest()
    previous = load(STORE / 'external_artifact_registry/external_artifact_summary.json')
    assert snapshot_hash == previous['store_snapshot_sha256']
    assert len(rows) == 5649 and sum(r['size_bytes'] for r in rows) == 2139594110
    return {'object_count': len(rows), 'bytes': sum(r['size_bytes'] for r in rows),
            'snapshot_sha256': snapshot_hash, 'missing_references': 0, 'orphan_objects': 0,
            'all_individual_sha256_verified': True}


def protected_snapshot():
    paths = [ROOT / 'pyproject.toml', ROOT / '.venv/pyvenv.cfg']
    # Only metadata/evidence in Sprint 55 namespaces; no Sprint 54 T1 payload hashing.
    for namespace in ['q1-xai-runtime-freeze', 'q1-xai-final-output-equivalence-g5',
                      'q1-xai-reconstruction-equivalence-g4']:
        paths.extend(p for p in (ROOT / 'audits' / namespace).rglob('*') if p.is_file())
    return {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(paths)}


def select_scopes():
    ledger = jsonlines(G5 / 'xai_readiness_ledger.jsonl')
    assert len(ledger) == 389
    excluded = {('apache/zeppelin', 'Logistic Regression', c) for c in ['C+T', 'P+T', 'C+P+T']}
    assert not excluded & {(r['project'], r['algorithm'], r['configuration']) for r in ledger}
    requests = [('lr', 'Logistic Regression', 'T'), ('rf', 'Random Forest', 'C'),
                ('xgb', 'XGBoost', 'C'), ('lgb', 'LightGBM', 'C'),
                ('fusion', 'Logistic Regression', 'C+P+T')]
    projects = sorted({r['project'] for r in ledger})
    eligible = [p for p in projects if all(any(r['project'] == p and r['algorithm'] == a
                 and r['configuration'] == c and r['method_specific_state_available']
                 for r in ledger) for _, a, c in requests)]
    project = eligible[0]
    assert project == 'apache/activemq', 'No fallback project permitted for prefix policy'
    selected = []
    for key, a, c in requests:
        row = next(r for r in ledger if (r['project'], r['algorithm'], r['configuration']) == (project, a, c))
        assert row['G5_outcome'] == 'G5_PASS_FINAL_OUTPUT_EQUIVALENCE'
        selected.append({'key': key, **row})
    return {'project': project, 'repetition': 'rep_01', 'scopes': selected,
            'eligible_projects_lexicographic': eligible, 'universe': 389,
            'excluded_scopes': sorted(excluded),
            'rule': 'First lexicographic eligible project; fixed LR TEXT, trees CODE, fusion LR C+P+T. No performance or attribution data used.',
            'configuration_rationale': 'Five scopes cover all families plus TF-IDF and all fusion modalities.',
            'fallback_after_failure': False}


def prepare():
    branch_check()
    assert not (OUT / 'preexecution_integrity.json').exists()
    selection = select_scopes()
    save('representative_scope_selection.json', selection)
    journal = jsonlines(STORE / 'repetitions/rep_01/component_journal.jsonl')
    wanted = [f"{selection['project']}|{s['algorithm']}|{'FUSION_META' if s['key']=='fusion' else 'FINAL_BASE'}|{s['configuration']}"
              for s in selection['scopes']]
    wanted += [f"{selection['project']}|Logistic Regression|FINAL_BASE|{m}" for m in ['C', 'P']]
    components = {}
    for logical in wanted:
        matches = [r for r in journal if r.get('logical_id') == logical]
        assert len(matches) == 1
        r = matches[0]
        assert r['g1'] == 'G1_PASS' and r['g2'] == 'G2_PASS'
        components[logical] = r
    save('selected_component_records.json', components)
    save('preexecution_integrity.json', {'branch': BRANCH, 'head': subprocess.check_output(
        ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(), 'objects': store_snapshot(),
        'protected': protected_snapshot(), 'selection_sha256': sha(OUT / 'representative_scope_selection.json'),
        'spec_sha256': sha(OUT / 'isolated_runtime_spec.json'),
        'source_sha256': sha(Path(__file__)), 'timestamp': datetime.now(timezone.utc).isoformat()})


def freeze_runtime():
    branch_check()
    assert Path(sys.prefix).resolve() == (ROOT / '.venv-xai-s56').resolve()
    assert not (OUT / 'isolated_runtime_lock.json').exists()
    spec = load(OUT / 'isolated_runtime_spec.json')
    actual = inventory()
    assert actual['python'] == spec['python']
    for package, version in spec['packages'].items():
        assert importlib.metadata.version(package) == version
    assert all(os.environ.get(t) == '1' for t in THREADS)
    report = load(OUT / 'pip-install-report.json')
    wheels = []
    for item in report['install']:
        info = item['download_info']
        assert info['url'].split('#')[0].endswith('.whl')
        wheels.append({'name': item['metadata']['name'], 'version': item['metadata']['version'],
                       'url': info['url'], 'hashes': info['archive_info']['hashes'],
                       'requires_dist': item['metadata'].get('requires_dist', []),
                       'provenance': 'PYPI_BINARY_WHEEL_NO_SOURCE_BUILD'})
    save('isolated_runtime_installation_provenance.json', {
        'environment_creation_command': '/usr/local/opt/python@3.11/bin/python3.11 -m venv .venv-xai-s56',
        'base_python_executable': sys._base_executable, 'base_python_sha256': sha(sys._base_executable),
        'commands': [
            '.venv-xai-s56/bin/python -m pip install --only-binary=:all: --index-url https://pypi.org/simple --report audits/q1-primary-xai-runtime-smoke/1.0.0/pip-install-report.json -r audits/q1-primary-xai-runtime-smoke/1.0.0/requirements-xai.txt',
            '.venv-xai-s56/bin/python -m pip install --no-cache-dir --only-binary=:all: --index-url https://pypi.org/simple --report audits/q1-primary-xai-runtime-smoke/1.0.0/pip-install-report.json -r audits/q1-primary-xai-runtime-smoke/1.0.0/requirements-xai.txt'],
        'first_attempt': 'SANDBOX_DNS_FAILURE_NO_PACKAGES_INSTALLED',
        'second_attempt': 'AUTHORIZED_NETWORK_RETRY_SAME_VERSION_PINS', 'package_source': 'https://pypi.org/simple',
        'wheels': wheels, 'source_build_count': 0})
    lock = {'role': 'ISOLATED_XAI_RUNTIME', 'environment': str(Path(sys.prefix)),
            'inventory': actual, 'platform': platform.platform(), 'architecture': platform.machine(),
            'threads': {t: os.environ[t] for t in THREADS}, 'wheels': wheels,
            'pip_report_sha256': sha(OUT / 'pip-install-report.json'),
            'spec_sha256': sha(OUT / 'isolated_runtime_spec.json'),
            'timestamp_before_explainer_import': datetime.now(timezone.utc).isoformat()}
    save('isolated_runtime_lock.json', lock)
    (OUT / 'requirements-xai-hashed.txt').write_text(''.join(
        f"{w['name']}=={w['version']} --hash=sha256:{w['hashes']['sha256']}\n" for w in sorted(wheels, key=lambda w:w['name'].lower())))


def bounded_gzip_prefix(path, n):
    """Decode exactly n lines, without scanning, seeking or hashing the tail."""
    decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
    lines, line = [], bytearray()
    consumed = 0
    with path.open('rb', buffering=0) as f:
        while len(lines) < n:
            if decoder.unconsumed_tail:
                compressed = decoder.unconsumed_tail
            else:
                compressed = f.read(1)
                consumed += len(compressed)
                if not compressed:
                    raise ValueError('Premature EOF in TRAIN prefix')
            value = decoder.decompress(compressed, max_length=1)
            line.extend(value)
            if value == b'\n':
                lines.append(bytes(line))
                line.clear()
    return lines, {'path': path.relative_to(ROOT).as_posix(), 'compressed_bytes_read': consumed,
                   'decompressed_lines_read': len(lines), 'prefix_sha256': hashlib.sha256(b''.join(lines)).hexdigest(),
                   'full_file_hash_or_tail_scan': False, 'read_unit_bytes': 1, 'decode_limit_bytes': 1}


def population():
    assert (OUT / 'isolated_runtime_lock.json').exists()
    selection = load(OUT / 'representative_scope_selection.json')
    components = load(OUT / 'selected_component_records.json')
    summary = load(FREEZE / 'temporal_partition_summary.json')
    first = sorted(summary['projects'], key=lambda r:r['project'])[0]
    assert first['project'] == selection['project']
    n = first['phase_support']['TRAIN']['rows']
    lines, boundary = bounded_gzip_prefix(FREEZE / 'temporal_partition_manifest.jsonl.gz', n)
    membership = [json.loads(line) for line in lines]
    assert all(r['partition'] == 'TRAIN' and r['project'] == selection['project'] for r in membership)
    ids = [r['row_identifier'] for r in membership]
    assert len(ids) == len(set(ids)) == n
    for r in components.values():
        if r['unit_type'] == 'UNIMODAL_PIPELINE':
            assert digest(ids) == r['canonical_state']['provenance']['train_membership_sha256']
    ordered = lambda role: sorted(ids, key=lambda rid:(hashlib.sha256(f'S56.1|{selection["project"]}|{role}|{rid}'.encode()).hexdigest(), rid))
    background, foreground = ordered('background')[:64], ordered('foreground')[:16]
    local = sorted(foreground, key=lambda rid:(hashlib.sha256(f'S56.1|local|{rid}'.encode()).hexdigest(), rid))[:4]
    chosen = set(background + foreground)
    rows = {rid: {'row_identifier': rid, 'partition': 'TRAIN', 'project': selection['project']} for rid in chosen}
    reads = [boundary]
    for modality, filename in [('C', 'code_dataset.jsonl.gz'), ('P', 'process_dataset.jsonl.gz'), ('T', 'text_dataset.jsonl.gz')]:
        payload, record = bounded_gzip_prefix(FREEZE / filename, n)
        reads.append(record)
        for expected_id, line in zip(ids, payload, strict=True):
            r = json.loads(line)
            assert r['row_identifier'] == expected_id
            if expected_id in chosen:
                rows[expected_id][modality] = (r['raw_commit_message'] if modality == 'T'
                                               else [float(r[name]) for name in FEATURES[modality]])
    save('selected_train_rows.json', [rows[rid] for rid in sorted(rows)])
    manifest = {'project': selection['project'], 'partition': 'TRAIN', 'available_train_rows': n,
                'train_membership_sha256': digest(ids), 'train_ids_chronological': ids,
                'background': background, 'foreground': foreground, 'local': local,
                'selection_rule': 'SHA256 UTF-8 S56.1|project|role|row_id, ascending digest then row_id; local SHA256 S56.1|local|row_id within foreground',
                'label_selection_or_label_read': False, 'bounded_prefix_reads': reads,
                'data_order_evidence': 'apachejit_final_dataset_freeze._partition_rows sorts projects lexicographically and rows chronologically, TRAIN first; aligned outputs preserve this order.',
                'rows_sha256': sha(OUT / 'selected_train_rows.json'), 'unique_selected_rows': len(rows),
                'budgets_per_scope': {'background': 64, 'foreground': 16, 'local': 4},
                'non_TRAIN_rows_read': 0, 'non_TRAIN_rows_decoded': 0}
    save('train_only_population_manifest.json', manifest)


def guard(event, args):
    if event != 'open' or not isinstance(args[0], (str, bytes, os.PathLike)):
        return
    p = Path(os.fsdecode(args[0])).resolve()
    mode = args[1] or ''
    flags = args[2] or 0
    writing = any(c in mode for c in 'wax+') or bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC))
    if p.is_relative_to(ROOT):
        relative = p.relative_to(ROOT).as_posix()
        if p.is_relative_to(ROOT / 'data') or p.is_relative_to(FREEZE) or 'q1-t1-' in relative:
            raise PermissionError(f'S56.1 protected data access denied: {relative}')
        if writing and (p.is_relative_to(STORE) or p.is_relative_to(ROOT / '.venv')):
            raise PermissionError(f'S56.1 immutable path write denied: {relative}')
        if not writing and p.is_relative_to(ROOT / 'audits'):
            READ_EVENTS.append(relative)


def warning_record(w):
    return {'category': w.category.__name__, 'message': str(w.message),
            'filename': w.filename, 'lineno': w.lineno}


def execute():
    branch_check()
    assert Path(sys.prefix).resolve() == (ROOT / '.venv-xai-s56').resolve()
    assert all(os.environ.get(t) == '1' for t in THREADS)
    lock = load(OUT / 'isolated_runtime_lock.json')
    assert inventory() == lock['inventory']
    assert sha(OUT / 'isolated_runtime_spec.json') == lock['spec_sha256']
    assert load(OUT / 'isolated_runtime_spec.json')['tolerances'] == TOLERANCES
    assert not (OUT / 'smoke_execution_started.json').exists(), 'No ungoverned rerun allowed'
    save('smoke_execution_started.json', {'timestamp': datetime.now(timezone.utc).isoformat(),
        'lock_sha256': sha(OUT / 'isolated_runtime_lock.json'), 'source_sha256': sha(Path(__file__)),
        'population_sha256': sha(OUT / 'train_only_population_manifest.json')})
    sys.addaudithook(guard)
    import numpy as np
    import joblib
    from scipy.special import expit
    import shap
    import xgboost as xgb
    import lightgbm as lgb
    from threadpoolctl import threadpool_limits, threadpool_info

    def no_fit(*args, **kwargs):
        raise PermissionError('Sprint 56.1 fitting API denied')
    from sklearn.pipeline import Pipeline
    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import RandomForestClassifier
    for cls in [Pipeline, LogisticRegression, RandomForestClassifier, xgb.XGBClassifier, lgb.LGBMClassifier]:
        cls.fit = no_fit
    threadpool_limits(limits=1)
    selection = load(OUT / 'representative_scope_selection.json')
    components = load(OUT / 'selected_component_records.json')
    pop = load(OUT / 'train_only_population_manifest.json')
    assert sha(OUT / 'selected_train_rows.json') == pop['rows_sha256']
    data = {r['row_identifier']: r for r in load(OUT / 'selected_train_rows.json')}
    assert all(r['partition'] == 'TRAIN' for r in data.values())
    fg = [data[i] for i in pop['foreground']]
    bg = [data[i] for i in pop['background']]
    models, compatibility = {}, {}
    for logical, record in components.items():
        ref = record['executable']
        assert sha(STORE / ref['path']) == ref['sha256']
        captured = []
        try:
            with warnings.catch_warnings(record=True) as captured:
                warnings.simplefilter('always')
                models[logical] = joblib.load(STORE / ref['path'])
            status = 'LOAD_COMPATIBLE_WITH_WARNING' if captured else 'LOAD_COMPATIBLE'
            error = None
        except Exception as exc:
            status, error = 'LOAD_INCOMPATIBLE', f'{type(exc).__name__}: {exc}'
        compatibility[logical] = {'classification': status, 'error': error,
                                  'warnings': [warning_record(w) for w in captured], 'object': ref}
        for w in captured:
            warnings.showwarning(w.message, w.category, w.filename, w.lineno)
    save('model_state_load_compatibility.json', compatibility)
    # The only in-memory model controls changed are execution thread counts.
    for logical, model in models.items():
        estimator = model.named_steps['model'] if hasattr(model, 'named_steps') else model
        if hasattr(estimator, 'n_jobs'):
            estimator.n_jobs = 1
        if '|XGBoost|' in logical:
            estimator.get_booster().set_param({'nthread': 1})
    raw = lambda rows, m: [r['T'] for r in rows] if m == 'T' else np.asarray([r[m] for r in rows], dtype=float)
    results, repeats, text_checks = {}, {}, {}

    def finite_max(x):
        x = np.asarray(x)
        assert np.all(np.isfinite(x))
        return float(np.max(np.abs(x))) if x.size else 0.0

    def analytic(model, X, background=None):
        coef = model.coef_[0]
        alpha = float(model.intercept_[0])
        matrix = X.toarray() if hasattr(X, 'toarray') else np.asarray(X)
        contributions = matrix * coef
        eta = alpha + contributions.sum(axis=1)
        predicted = np.asarray(model.decision_function(X))
        probability = model.predict_proba(X)[:, int(np.flatnonzero(model.classes_ == 1)[0])]
        residual = eta - predicted
        probability_residual = expit(eta) - probability
        passed = bool(np.all(np.abs(residual) <= 1e-10 * (1 + np.abs(predicted)))
                      and np.all(np.abs(probability_residual) <= 1e-10))
        value = {'intercept': alpha, 'coefficient': coef.tolist(), 'contribution_vector': contributions.tolist(),
                 'reconstructed_logit': eta.tolist(), 'predictor_logit': predicted.tolist(),
                 'predictor_probability': probability.tolist(), 'residual': residual.tolist(),
                 'sigmoid_residual': probability_residual.tolist(), 'max_abs_residual': finite_max(residual),
                 'max_abs_sigmoid_residual': finite_max(probability_residual), 'pass': passed}
        if background is not None:
            mu = background.mean(axis=0)
            centered = (matrix - mu) * coef
            baseline = alpha + np.sum(coef * mu)
            centered_residual = baseline + centered.sum(axis=1) - predicted
            value.update({'mu': mu.tolist(), 'centered_contributions': centered.tolist(),
                          'centered_baseline': float(baseline), 'centered_residual': centered_residual.tolist(),
                          'max_abs_centered_residual': finite_max(centered_residual),
                          'modality_probabilities': matrix.tolist(), 'reference_modality_probabilities': background.tolist()})
            value['pass'] = passed and bool(np.all(np.abs(centered_residual) <= 1e-10 * (1 + np.abs(predicted))))
        return value

    for scope in selection['scopes']:
        key, algorithm, configuration = scope['key'], scope['algorithm'], scope['configuration']
        logical = f"{selection['project']}|{algorithm}|{'FUSION_META' if key=='fusion' else 'FINAL_BASE'}|{configuration}"
        captured = []
        try:
            if logical not in models:
                raise RuntimeError('MODEL_STATE_LOAD_INCOMPATIBLE')
            with warnings.catch_warnings(record=True) as captured:
                warnings.simplefilter('always')
                pipeline = models[logical]
                if key == 'fusion':
                    order = components[logical]['canonical_state']['provenance']['modality_order']
                    assert order == ['C', 'P', 'T']
                    def base_probs(rows):
                        columns = []
                        for m in order:
                            base = models[f"{selection['project']}|{algorithm}|FINAL_BASE|{m}"]
                            pos = int(np.flatnonzero(base.named_steps['model'].classes_ == 1)[0])
                            columns.append(base.predict_proba(raw(rows, m))[:, pos])
                        return np.column_stack(columns)
                    runs = [analytic(pipeline, base_probs(fg), base_probs(bg)) for _ in range(2)]
                    for r in runs:
                        r['feature_order'] = order
                else:
                    model = pipeline.named_steps['model']
                    X = pipeline[:-1].transform(raw(fg, configuration))
                    assert X.shape[0] == 16 and X.shape[1] == model.n_features_in_
                    if configuration == 'T':
                        vectorizer = pipeline.named_steps['tfidf']
                        ref = components[logical]['text_representation']
                        exact = load(STORE / ref['path'])
                        names = vectorizer.get_feature_names_out().tolist()
                        aligned = (vectorizer.vocabulary_ == exact['vocabulary'] and
                                   np.array_equal(vectorizer.idf_, np.asarray(exact['idf'])) and
                                   names == exact['feature_order'] and
                                   all(vectorizer.vocabulary_[name] == i for i, name in enumerate(names)) and
                                   len(names) == model.n_features_in_)
                        assert aligned, 'TEXT_ALIGNMENT_SMOKE_FAIL'
                        text_checks[logical] = {'status': 'TEXT_ALIGNMENT_SMOKE_PASS',
                            'vocabulary_exact': True, 'idf_exact': True, 'token_column_mapping_exact': True,
                            'feature_order_exact': True, 'predictor_alignment': True,
                            'feature_order_sha256': digest(names), 'representation_object': ref,
                            'transformed_train_shape': list(X.shape), 'semantic_interpretation': False}
                    else:
                        names = FEATURES[configuration]
                    if key == 'lr':
                        runs = [analytic(model, pipeline[:-1].transform(raw(fg, configuration))) for _ in range(2)]
                        for r in runs:
                            r['feature_order'] = names
                            probability = pipeline.predict_proba(raw(fg, configuration))[:, 1]
                            r['pipeline_probability_alignment'] = bool(np.array_equal(probability, r['predictor_probability']))
                            r['pass'] = r['pass'] and r['pipeline_probability_alignment']
                    else:
                        runs = []
                        for _ in range(2):
                            explainer = shap.TreeExplainer(model, data=None, model_output='raw',
                                                        feature_perturbation='tree_path_dependent')
                            values = explainer.shap_values(X, approximate=False, check_additivity=True)
                            base = np.asarray(explainer.expected_value)
                            if key == 'rf':
                                positive = int(np.flatnonzero(model.classes_ == 1)[0])
                                values = np.asarray(values)[:, :, positive]
                                base = float(base[positive])
                                output = model.predict_proba(X)[:, positive]
                                identity = {'positive_class': 1, 'positive_class_index': positive,
                                            'scale': 'POSITIVE_CLASS_PROBABILITY', 'trees': len(model.estimators_)}
                            elif key == 'xgb':
                                booster = model.get_booster()
                                native = components[logical]['family_native_model']
                                config = json.loads(booster.save_config())
                                output = model.predict(X, output_margin=True)
                                base = float(base.reshape(-1)[0])
                                identity = {'native_object': native, 'objective': config['learner']['objective']['name'],
                                    'booster_config': config, 'native_feature_names': booster.feature_names,
                                    'missing_value': 'NaN' if np.isnan(model.missing) else model.missing,
                                    'input_semantics': 'Frozen imputer transform; feature positions preserved', 'scale': 'NATIVE_RAW_MARGIN'}
                            else:
                                booster = model.booster_
                                output = booster.predict(X, raw_score=True, num_threads=1)
                                base = float(base.reshape(-1)[0])
                                identity = {'native_object': components[logical]['family_native_model'],
                                    'objective': booster.params.get('objective'), 'native_feature_names': booster.feature_name(),
                                    'categorical_metadata': booster.pandas_categorical, 'scale': 'NATIVE_RAW_MARGIN'}
                            values = np.asarray(values)
                            residual = base + values.sum(axis=1) - output
                            runs.append({'base_value': base, 'contribution_vector': values.tolist(),
                                'model_output': np.asarray(output).tolist(), 'residual': residual.tolist(),
                                'max_abs_residual': finite_max(residual), 'feature_order': names, 'booster_identity': identity,
                                'pass': bool(np.all(np.abs(residual) <= 1e-6 * (1 + np.abs(output)))),
                                'explainer': {'class': 'shap.TreeExplainer', 'feature_perturbation': 'tree_path_dependent',
                                    'model_output': 'raw', 'approximate': False, 'check_additivity': True,
                                    'background': 'Persisted TRAIN path counts; data=None', 'thread_count': 1}})
                first, second = runs
                differences = [finite_max(np.asarray(first['contribution_vector']) - np.asarray(second['contribution_vector']))]
                if key == 'fusion':
                    differences.append(finite_max(np.asarray(first['centered_contributions']) - np.asarray(second['centered_contributions'])))
                difference = max(differences)
                repeats[key] = {'runs': 2, 'max_absolute_attribution_difference': difference,
                                'tolerance': 1e-12, 'pass': difference <= 1e-12,
                                'run_1_sha256': digest(first), 'run_2_sha256': digest(second)}
                family_pass = first['pass'] and second['pass']
                tag = {'lr': 'LR_ANALYTICAL', 'rf': 'RF_TREESHAP', 'xgb': 'XGB_TREESHAP',
                       'lgb': 'LGB_TREESHAP', 'fusion': 'FUSION_ANALYTICAL'}[key]
                results[key] = {'outcome': tag + '_SMOKE_' + ('PASS' if family_pass else 'FAIL'),
                                'scope': scope, 'row_ids': pop['foreground'], 'local_row_ids': pop['local'],
                                'run_1': first, 'run_2': second, 'purpose': 'RUNTIME_SMOKE_VALIDATION_ONLY'}
        except Exception as exc:
            results[key] = {'outcome': {'lr':'LR_ANALYTICAL','rf':'RF_TREESHAP','xgb':'XGB_TREESHAP',
                'lgb':'LGB_TREESHAP','fusion':'FUSION_ANALYTICAL'}[key] + '_SMOKE_FAIL',
                'scope': scope, 'error': f'{type(exc).__name__}: {exc}', 'fallback_attempted': False}
            repeats[key] = {'runs': 0, 'pass': False, 'status': 'NOT_COMPLETED', 'max_absolute_attribution_difference': None}
        results[key]['warnings'] = [warning_record(w) for w in captured]
        for w in captured:
            warnings.showwarning(w.message, w.category, w.filename, w.lineno)
        save({'lr':'lr_analytical_smoke.json','rf':'rf_treeshap_smoke.json','xgb':'xgb_treeshap_smoke.json',
              'lgb':'lgb_treeshap_smoke.json','fusion':'fusion_analytical_smoke.json'}[key], results[key])
        print(key, results[key]['outcome'], flush=True)
    save('text_alignment_smoke.json', {'checks': text_checks, 'outcome': 'TEXT_ALIGNMENT_SMOKE_PASS'
         if text_checks else 'TEXT_ALIGNMENT_SMOKE_FAIL', 'fusion_TEXT_uses_same_verified_LR_pipeline': True})
    save('determinism_smoke.json', {'families': repeats, 'all_pass': all(r['pass'] for r in repeats.values()),
                                  'tolerance': 1e-12, 'threads': threadpool_info()})
    save('runtime_read_events.json', {'paths': sorted(set(READ_EVENTS)), 'audit_hook': 'Python open events; denies data, mixed population files, T1 evidence, immutable writes during smoke',
                                    'prefix_extraction_separately_logged': True})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('stage', choices=['prepare', 'freeze-runtime', 'population', 'execute'])
    stage = parser.parse_args().stage
    {'prepare': prepare, 'freeze-runtime': freeze_runtime, 'population': population, 'execute': execute}[stage]()
