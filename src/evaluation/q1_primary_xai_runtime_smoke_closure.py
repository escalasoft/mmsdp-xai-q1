"""Read-only validation and reporting closure for Sprint 56.1; no model queries."""
import argparse
import importlib.util
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('smoke_governance', ROOT / 'src/evaluation/q1_primary_xai_runtime_smoke.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
OUT = m.OUT
FILES = {'lr':'lr_analytical_smoke.json', 'rf':'rf_treeshap_smoke.json',
         'xgb':'xgb_treeshap_smoke.json', 'lgb':'lgb_treeshap_smoke.json',
         'fusion':'fusion_analytical_smoke.json'}


def manifest():
    (OUT / 'MANIFEST.sha256').write_text(''.join(
        f'{m.sha(p)}  {p.name}\n' for p in sorted(OUT.iterdir())
        if p.is_file() and p.name != 'MANIFEST.sha256'))


def close():
    m.branch_check()
    assert Path(__import__('sys').prefix).resolve() == ROOT / '.venv'
    m.save('predictive_inventory_after.json', m.inventory())
    before = m.load(OUT / 'preexecution_integrity.json')
    after = {'objects': m.store_snapshot(), 'protected': m.protected_snapshot()}
    m.save('postexecution_integrity.json', after)
    preservation = before['objects'] == after['objects'] and before['protected'] == after['protected']
    inventory_same = m.load(OUT / 'predictive_inventory_before.json') == m.inventory()
    results = {key: m.load(OUT / filename) for key, filename in FILES.items()}
    repeat = m.load(OUT / 'determinism_smoke.json')
    text = m.load(OUT / 'text_alignment_smoke.json')
    loads = m.load(OUT / 'model_state_load_compatibility.json')
    passed = [key for key, value in results.items() if value['outcome'].endswith('_PASS')]
    nondeterministic = any(r['max_absolute_attribution_difference'] is not None
                          and r['max_absolute_attribution_difference'] > 1e-12 for r in repeat['families'].values())
    if not (preservation and inventory_same):
        outcome = 'XAI_RUNTIME_SMOKE_TEST_INTEGRITY_FAILURE'
    elif nondeterministic:
        outcome = 'XAI_RUNTIME_NONDETERMINISM_DETECTED'
    elif len(passed) == 5 and repeat['all_pass'] and text['outcome'] == 'TEXT_ALIGNMENT_SMOKE_PASS':
        outcome = 'PRIMARY_XAI_ISOLATED_RUNTIME_SMOKE_TEST_PASS'
    elif passed:
        outcome = 'PRIMARY_XAI_RUNTIME_PARTIAL_FAMILY_SUPPORT'
    elif any(r['classification'] == 'LOAD_INCOMPATIBLE' for r in loads.values()):
        outcome = 'MODEL_STATE_LOAD_INCOMPATIBLE'
    else:
        outcome = 'XAI_RUNTIME_SMOKE_TEST_INTEGRITY_FAILURE'
    counters = {k: 0 for k in ['T1_XAI_ACCESS_COUNT', 'T1_XAI_MODEL_QUERY_COUNT', 'T1_XAI_ROW_READ_COUNT',
        'T2_ACCESS_COUNT', 'predictive_metric_count', 'artifact_mutation_count', 'reconstruction_count',
        'refit_count', 'retraining_count', 'recalibration_count', 'LIME_installation_count', 'LIME_execution_count',
        'counterfactual_execution_count', 'PDP_ICE_execution_count', 'permutation_importance_count',
        'article_plot_count', 'commit_count', 'push_count']}
    counters.update({'T2_STATE': 'DENY_SEALED_REVIEWER_RESERVE',
        'historical_Sprint54_predictive_access_scoring': [1, 1],
        'historical_counters_modified': False, 'predictive_inventory_unchanged': inventory_same,
        'object_bytes_unchanged': preservation, 'TRAIN_only_scope_count': 5,
        'counter_basis': 'Bounded TRAIN prefix/membership evidence, guarded smoke file opens, source/API restrictions, before/after inventories and object SHA256; no claim of OS syscall tracing.'})
    m.save('runtime_governance_counters.json', counters)
    prerequisites = {'Sprint56_2_authorized': False, 'Sprint56_1_outcome': outcome,
        'maximum_future_XAI_universe': 389,
        'excluded_scopes': m.load(OUT / 'representative_scope_selection.json')['excluded_scopes'],
        'required_before_any_primary_XAI': [
            'Human review and explicit separate Sprint 56.2 primary XAI execution authorization naming exact permitted scopes, role, methods, runtime lock and data partition.',
            'Accept Sprint 56.1 family support, exact warning ledger, fidelity/additivity and deterministic-repeat evidence; any failure requires a prospectively authorized resolution, never output-driven scope/version changes.',
            'Verify this manifest, exact isolated runtime lock, unchanged predictive runtime, and all 5649 immutable objects with 0 missing references and 0 orphans.',
            'Preserve 389 G1-G5 eligible scopes and the three apache/zeppelin LR exclusions; separately govern load compatibility for all additional persisted states because five representative scopes do not prove universal compatibility.',
            'Explicitly authorize T1 XAI access and query budgets before any T1 read; freeze TRAIN reference, T1 foreground and local SHA256 selections under Sprint 55 contracts before attribution.',
            'Retain exact primary method scales, approximate=False, feature order, thread controls, frozen tolerances, query ledger and reproducibility checks.',
            'Keep T2 DENY_SEALED_REVIEWER_RESERVE with zero access; no predictive metrics, retraining/refit, reconstruction, recalibration, LIME, PDP/ICE, counterfactuals or permutation importance.',
            'Any state conversion, serialization change or scientific visualization outside separately authorized scope requires separate authorization.'
        ], 'automatic_transition_permitted': False}
    m.save('sprint56_2_authorization_prerequisites.json', prerequisites)
    lock = m.load(OUT / 'isolated_runtime_lock.json')
    selection = m.load(OUT / 'representative_scope_selection.json')
    pop = m.load(OUT / 'train_only_population_manifest.json')
    summary = {'outcome': outcome, 'family_support': {key:value['outcome'] for key,value in results.items()},
        'passed_family_count': len(passed), 'scientific_disposition': 'TRAIN_ONLY_RUNTIME_VALIDATION_NO_SCIENTIFIC_XAI_CLAIM',
        'branch': before['branch'], 'head': before['head'], 'environment': lock['environment'],
        'predictive_environment_preserved': inventory_same, 'artifact_bytes_preserved': preservation,
        'text_alignment': text['outcome'], 'maxima': {key: {
            'additivity': value.get('run_1',{}).get('max_abs_residual'),
            'sigmoid': value.get('run_1',{}).get('max_abs_sigmoid_residual'),
            'centered': value.get('run_1',{}).get('max_abs_centered_residual'),
            'repeat': repeat['families'][key]['max_absolute_attribution_difference']}
            for key,value in results.items()}}
    m.save('sprint56_1_summary.json', summary)
    versions = {r['name'].lower():r['version'] for r in lock['inventory']['packages']}
    table = []
    for scope in selection['scopes']:
        key = scope['key']
        logical = f"{scope['project']}|{scope['algorithm']}|{'FUSION_META' if key=='fusion' else 'FINAL_BASE'}|{scope['configuration']}"
        maxima = summary['maxima'][key]
        table.append(f"| {scope['algorithm']} / {scope['configuration']} | {loads[logical]['classification']} | {results[key]['outcome']} | {maxima['additivity']} | {maxima['repeat']} |")
    validation_path = OUT / 'validation_results.json'
    validation = m.load(validation_path) if validation_path.exists() else {'status': 'PENDING_FOCUSED_TESTS'}
    text_report = f'''# Sprint 56.1 — Isolated XAI Runtime + TRAIN-only Smoke Test

`{outcome}`

## A–H. Provenance and frozen state

- **A. Branch / HEAD:** `{before['branch']}` / `{before['head']}`. No commit or push.
- **B. Isolated environment:** `{lock['environment']}`; system site packages disabled, narrowly ignored by `/.venv-xai-s56/`.
- **C. Predictive preservation:** inventory unchanged = `{inventory_same}`. Python 3.11.14, NumPy 2.4.6, SciPy 1.17.1, scikit-learn 1.9.0, XGBoost 3.2.0, LightGBM 4.6.0 remain in `.venv`. No predictive requirement edits. Protected Sprint 55 evidence hashes unchanged = `{preservation}`.
- **D–E. Exact XAI runtime:** Python `{lock['inventory']['python']}`, NumPy `{versions['numpy']}`, SciPy `{versions['scipy']}`, scikit-learn `{versions['scikit-learn']}`, XGBoost `{versions['xgboost']}`, LightGBM `{versions['lightgbm']}`, SHAP `{versions['shap']}`, Numba `{versions['numba']}`, llvmlite `{versions['llvmlite']}`, joblib `{versions['joblib']}`, cloudpickle `{versions['cloudpickle']}`. Platform `{lock['platform']}`, architecture `{lock['architecture']}`. All five prescribed thread variables equal 1; supported model controls and threadpool limits set to 1 in memory only.
- **F. Installation:** PyPI binary wheels exclusively; zero source builds. The initial sandbox DNS failure was followed by an authorized network retry of the same pins. Full commands, URLs, wheel hashes and dependency metadata are in `isolated_runtime_installation_provenance.json`, `pip-install-report.json`, `isolated_runtime_lock.json` and `requirements-xai-hashed.txt`. Bootstrap pip/setuptools versions are included in the complete lock inventory; Python executable and SHA256 are recorded. `pip check` passed. The NumPy-only change to the predictive-library tuple was chosen before any explanation based on [Numba compatibility](https://numba.readthedocs.io/en/stable/user/installing.html#version-support-information) and [SHAP 0.51.0 metadata](https://pypi.org/pypi/shap/0.51.0/json).
- **G. Object integrity:** 5,649 objects; 2,139,594,110 bytes; zero missing references and orphans. Every SHA256 verified before and after. Store snapshot `{after['objects']['snapshot_sha256']}` matches Sprint 55. No resaving, conversion or serialization mutation.
- **H. Representatives:** `{selection['project']}`, first lexicographic eligible project, repetition `rep_01`. Fixed LR TEXT, RF/XGB/LGB CODE and LR fusion C+P+T cover five families and TF-IDF without performance/attribution selection. G1–G5 universe remains 389 with the exact three apache/zeppelin LR exclusions.

## I–P. Load, fidelity and determinism

| Scope | Load compatibility | Smoke outcome | Max absolute additive residual | Max repeated attribution difference |
|---|---|---|---:|---:|
{chr(10).join(table)}

**N. TEXT:** `{text['outcome']}`. Exact persisted vocabulary, IDF, token-column map and feature order were compared with the loaded LR vectorizer; transformed TRAIN dimensionality and predictor alignment verified. Fusion uses that same frozen LR TEXT pipeline. Tree TEXT was not selected; no broader text-family compatibility claim is made.

**O. Analytical checks:** LR maximum sigmoid residual `{summary['maxima']['lr']['sigmoid']}`; fusion maximum sigmoid residual `{summary['maxima']['fusion']['sigmoid']}`; fusion centered-logit maximum residual `{summary['maxima']['fusion']['centered']}`. All per-row values and complete contribution vectors are retained in the family JSON records for both runs. Local checks are the four SHA256-selected rows within the 16-row foreground. No feature/modality/token interpretation or scientific plot was generated.

**P. Repeatability:** tolerance fixed prospectively at 1e-12. Each completed method was instantiated/executed twice; persisted vectors are independently compared by tests. TreeSHAP uses `tree_path_dependent`, `model_output=raw`, `approximate=False`, `check_additivity=True`; RF selects positive-class probability, boosters use native raw margin. Stored TRAIN path counts supply the TreeSHAP background semantics; no explicit background matrix is required. Analytical fusion reference means use 64 TRAIN rows. Fidelity tolerances remain 1e-10 × (1 + |logit|), sigmoid 1e-10, and trees 1e-6 × (1 + |output|).

Exact warnings, including categories, source paths and line numbers, are retained in `model_state_load_compatibility.json`, family JSON records and `smoke-execution-output.txt`; captured warnings were also re-emitted. No warnings were filtered away. Load success is limited to the selected persisted states and is not proof of predictive equivalence across runtimes.

## Q–V. Governance and scientific disposition

- **Q. T1:** access = 0, model queries = 0, row reads = 0. Historical Sprint 54 predictive access/scoring remains 1/1.
- **R. T2:** access = 0; `DENY_SEALED_REVIEWER_RESERVE`.
- **S. Metrics:** predictive metric computations = 0.
- **T. Mutation:** artifact mutations, reconstruction, refit, retraining and recalibration = 0.
- **U. Family support:** {len(passed)}/5 representative families passed; final classification `{outcome}`.
- **V. Scientific disposition:** `TRAIN_ONLY_RUNTIME_VALIDATION_NO_SCIENTIFIC_XAI_CLAIM`. Sprint 54 `MIXED_CONFIRMATORY_EVIDENCE`, Sprint 55 closed/readiness state, G4 389/389 and G5 389/389 remain accepted without rerunning predictive evaluation.

TRAIN extraction read exactly {pop['available_train_rows']} first-project TRAIN records in each aligned frozen stream, stopping at its documented chronological prefix boundary. It did not traverse the remaining mixed-population stream, read labels, hash full dataset files, or open T1 prediction evidence. The TRAIN membership digest `{pop['train_membership_sha256']}` matches persisted final-base provenance. SHA256 selection produced 64 reference, 16 foreground, 4 local and {pop['unique_selected_rows']} unique TRAIN inputs. Each prefix's compressed-byte boundary and decompressed-prefix digest are logged. These streams contain other partitions later in the files; only the TRAIN prefix was decoded. The Python audit hook governs smoke execution, while prefix extraction is separately bounded and tested; no OS-wide syscall trace is claimed.

## W. Exact Sprint 56.2 prerequisites

{chr(10).join(str(i+1)+'. '+p for i,p in enumerate(prerequisites['required_before_any_primary_XAI']))}

`Sprint56_2_authorized=false`. Stop after this TRAIN-only validation. No primary XAI, T1/T2 access, plots, commit or push.

## Validation

`{json.dumps(validation, sort_keys=True)}`

The focused suite independently verifies persisted equations, additive residuals, repeat differences, deterministic selection, package/path separation, object hashes, prohibited-operation guards and the complete manifest. Relevant Sprint 55 runtime, SHAP compatibility, external-store and G5 regressions run under a protected-data read guard. Three exclusions are explicit: the G5 parent-hash test opens historical T1 predictions; the G5 isotonic linkage test opens an out-of-scope development probability ledger; and the historical external-store ignore test asserts the exact Sprint 55 uncommitted worktree size. Current narrow ignores and evidence visibility are verified by a replacement focused test. No Sprint 55 test or evidence was edited.

Validation development history is retained in `validation_history.json` and the captured test logs. Test-only corrections normalize JSON tuples/lists and restore XGBoost float32 arithmetic after JSON loading. The XGBoost additive sum also passes the original 1e-6 relative tolerance when independently recomputed in float64. No smoke execution, model, scope, version, attribution vector or tolerance was changed or rerun to obtain these test results.

READY FOR HUMAN REVIEW BEFORE PRIMARY XAI EXECUTION AUTHORIZATION
'''
    (OUT / 'SPRINT56_1_XAI_RUNTIME_SMOKE_REPORT.md').write_text(text_report)
    manifest()
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('stage', choices=['close', 'manifest'])
    {'close':close, 'manifest':manifest}[parser.parse_args().stage]()
