"""Materialize only the predeclared E2 T1 foreground; never execute models/XAI.

The historical Sprint56.2 selector is imported unchanged. Sprint56.2C identifies
the isolated T1 evidence; this task authorizes identity extraction and freezing.
No mixed scientific source, model object, label or probability is selected.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile

from src.evaluation import q1_primary_xai_population_freeze as parent

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'audits/q1-e2-t1-foreground-freeze/1.0.0'
POP = 'audits/q1-primary-xai-population-freeze/1.0.0/'
REUSE = 'audits/q1-primary-xai-frozen-evidence-reuse/1.0.0/'
RESOLVE = 'audits/q1-primary-xai-e1-input-e2-reference-resolution/1.0.0/'
DESIGN = 'audits/q1-primary-xai-alternative-design/1.0.0/'
SOURCE = 'audits/q1-t1-confirmatory-execution/1.0.0/results/t1_prediction_evidence.jsonl.gz'
BRANCH = 'sprint-10/q1-e2-final-closure'
COUNTS = {'C+P': 56, 'C+T': 55, 'P+T': 55, 'C+P+T': 55}
INPUTS = [
    POP + 'population_selection_contract.json',
    POP + 'population_selection_summary.json',
    POP + 'primary_xai_scope_ledger.jsonl',
    POP + 'scope_readiness_summary.json',
    POP + 't1_global_foreground_population.jsonl',
    POP + 't1_local_case_population.jsonl',
    REUSE + 't1_evidence_inventory.jsonl',
    REUSE + 'execution_provenance.json',
    REUSE + 'row_identity_reconciliation.json',
    RESOLVE + 'e2_fusion_decomposition_readiness.json',
    RESOLVE + 'exact_remaining_blockers.json',
    DESIGN + 'e2_primary_scientific_scope.json',
    DESIGN + 'exact_next_execution_path.json',
    'audits/q1-xai-runtime-freeze/1.0.0/explanation_population_policy.json',
]
CODE = [
    'src/evaluation/q1_primary_xai_population_freeze.py',
    'tests/evaluation/test_q1_primary_xai_population_freeze.py',
    'src/evaluation/q1_primary_xai_frozen_evidence_reuse.py',
    'src/evaluation/q1_t1_confirmatory_execution.py',
]
ZERO = dict.fromkeys(['T2_scientific_accesses', 'model_retraining', 'calibration_refits',
                     'predictive_recomputations', 'E1_reruns', 'E2_attributions',
                     'selection_label_uses', 'selection_probability_uses',
                     'selection_correctness_uses'], 0)


class FreezeError(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise FreezeError(message)


def enc(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=True,
                       separators=(',', ':'), allow_nan=False) + '\n').encode()


def digest(value):
    return hashlib.sha256(enc(value)).hexdigest()


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def rows(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line]


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def check_inputs():
    """Check named governance files against their existing manifests only."""
    records = []
    for name in INPUTS:
        path = ROOT / name
        entries = dict(line.split('  ', 1)[::-1]
                       for line in (path.parent / 'MANIFEST.sha256').read_text().splitlines())
        actual = sha(path)
        require(entries.get(path.name) == actual, 'Input manifest mismatch: ' + name)
        records.append(dict(path=name, sha256=actual))
    for name in CODE:
        records.append(dict(path=name, sha256=sha(ROOT / name)))
    return records


def recover():
    contract = read(ROOT / POP / 'population_selection_contract.json')
    require(contract['seed'] == parent.SEED == 20260901, 'Seed conflict')
    require(contract['selection_order'] == 'selection_key ASC, row_identifier ASC', 'Order conflict')
    g, local = contract['T1_global'], contract['T1_local']
    require(g['maximum'] == 256 and g['model_identity_sha256_in_key'] is None
            and g['purpose'] == 'T1_GLOBAL_FOREGROUND_SELECTION'
            and g['strata'] == 'UNSTRATIFIED' and not g['label_use'], 'Global rule conflict')
    require(local['maximum'] == 8 and local['purpose'] == 'T1_LOCAL_CASE_SELECTION'
            and local['source'] == 'FROZEN_T1_GLOBAL_FOREGROUND_SUBSET'
            and local['strata'] == 'UNSTRATIFIED' and not local['label_use']
            and not local['posthoc_substitution'], 'Local rule conflict')
    scopes = [r for r in rows(ROOT / POP / 'primary_xai_scope_ledger.jsonl') if r['role'] == 'E2']
    ready = read(ROOT / RESOLVE / 'e2_fusion_decomposition_readiness.json')['scopes']
    key = lambda r: (r['project'], r['algorithm'], r['configuration'], r['model_identity_sha256'])
    require(len(scopes) == len(set(map(key, scopes))) == 221, 'Duplicate/missing eligible scope')
    require(set(map(key, scopes)) == set(map(key, ready)), 'Eligibility identity conflict')
    require(dict(Counter(r['configuration'] for r in scopes)) == COUNTS, 'Eligibility count conflict')
    design = read(ROOT / DESIGN / 'e2_primary_scientific_scope.json')
    require(design['configurations'] == COUNTS and design['eligible_multimodal_scopes'] == 221,
            'Later E2 scope conflict')
    inventory = rows(ROOT / REUSE / 't1_evidence_inventory.jsonl')
    require(len(inventory) == 1 and inventory[0]['path'] == SOURCE
            and inventory[0]['partition_provenance'] == 'T1_ONLY_FROZEN_SPRINT54',
            'No authoritative isolated T1 source')
    return contract, sorted(scopes, key=key), inventory[0]


IDENTITY_FIELDS = frozenset(['project', 'row_identifier', 'algorithm', 'configuration', 'model_identity_sha256'])


def identity_projection(pairs):
    """Drop nonidentity fields at JSON decoding; never retrieve their values.

    The physical T1 transport contains labels/predictions. This is not a claim
    that those bytes were never decompressed; none enter selection or outputs.
    """
    result = {}
    for key, value in pairs:
        if key in IDENTITY_FIELDS:
            require(key not in result, 'Duplicate identity field')
            result[key] = value
    return result


def load_candidates(scopes, source):
    require(source['path'] == SOURCE, 'Unknown source refused before open')
    require(sha(ROOT / SOURCE) == source['sha256'], 'Frozen T1 source hash conflict')
    expected = {(r['project'], r['algorithm'], r['configuration']): r for r in scopes}
    grouped = defaultdict(list)
    physical_count = 0
    with gzip.open(ROOT / SOURCE, 'rt', encoding='utf-8') as stream:
        for line in stream:
            record = json.loads(line, object_pairs_hook=identity_projection)
            physical_count += 1
            require(set(record) == IDENTITY_FIELDS, 'Missing T1 identity field')
            key = (record['project'], record['algorithm'], record['configuration'])
            if key not in expected:
                continue  # Fixed E2 eligibility, never selected using any outcome.
            require(record['model_identity_sha256'] == expected[key]['model_identity_sha256'],
                    'Frozen model identity conflict')
            rid = record['row_identifier']
            require(isinstance(rid, str) and len(rid) == 64
                    and all(c in '0123456789abcdef' for c in rid), 'Invalid row identity')
            grouped[key].append(rid)
    require(physical_count == source['identity_coverage']['physical_scope_rows'], 'T1 physical count conflict')
    require(set(grouped) == set(expected), 'Missing eligible source scope')
    projects = {}
    for key, ids in grouped.items():
        scope = expected[key]
        require(len(ids) == len(set(ids)) == scope['historical_T1_row_count'], 'T1 membership count conflict')
        require(digest(ids) == scope['G4_G5_T1_membership_digest'], 'T1 ordered membership conflict')
        if key[0] in projects:
            require(projects[key[0]] == ids, 'Scopes disagree on project membership/order')
        projects[key[0]] = ids
    require(len(projects) == 14, 'Project coverage conflict')
    require(sha(ROOT / SOURCE) == source['sha256'], 'Source changed during read')
    return projects, physical_count


def independent_selection(candidates, project, identity, purpose, limit):
    """Independent expression of the already-frozen key and sorting recipe."""
    def key(row):
        payload = dict(seed=20260901, purpose=purpose, project=project,
                       model_identity_sha256=identity, row_identifier=row['row_identifier'])
        encoded = (json.dumps(payload, ensure_ascii=True, sort_keys=True,
                              separators=(',', ':'), allow_nan=False) + '\n').encode('utf-8')
        return hashlib.sha256(encoded).hexdigest(), row['row_identifier']
    return [{**r, 'selection_key': key(r)[0]} for r in sorted(candidates, key=key)[:limit]]


def select(candidates, project, identity, purpose, limit):
    selected = parent.select_population(candidates, project, identity, purpose, limit)
    require(selected == independent_selection(candidates, project, identity, purpose, limit),
            'Independent selector mismatch')
    return selected


def annotate(selected, source_ids, identity=None, scope=None):
    # Reporting/hash conventions only; no new scientific selection decision.
    ids = [r['row_identifier'] for r in selected]
    common = dict(count=len(ids), selection_hash=digest(sorted(ids)), ordering_hash=digest(ids),
                  source_membership_digest=digest(source_ids), model_identity_sha256=identity)
    if scope:
        common.update(algorithm=scope['algorithm'], configuration=scope['configuration'])
    return [{**r, **common, 'ordinal': i} for i, r in enumerate(selected, 1)]


def compute():
    inputs = check_inputs()
    contract, scopes, source = recover()
    projects, physical = load_candidates(scopes, source)
    global_rows, local_rows, summaries = [], [], []
    for project, source_ids in sorted(projects.items()):
        candidates = [dict(project=project, partition='T1', row_identifier=rid) for rid in source_ids]
        global_rule = contract['T1_global']
        fg = select(candidates, project, None, global_rule['purpose'], global_rule['maximum'])
        global_rows.extend(annotate(fg, source_ids))
        stripped = [{k: r[k] for k in ['project', 'partition', 'row_identifier']} for r in fg]
        project_scopes = [r for r in scopes if r['project'] == project]
        for scope in project_scopes:
            local_rule = contract['T1_local']
            local = select(stripped, project, scope['model_identity_sha256'],
                           local_rule['purpose'], local_rule['maximum'])
            local_rows.extend(annotate(local, source_ids, scope['model_identity_sha256'], scope))
        summaries.append(dict(project=project, source_rows=len(source_ids), global_rows=len(fg),
                              local_scope_rows=len(project_scopes)*min(local_rule['maximum'], len(fg)),
                              eligible_scopes=len(project_scopes), source_membership_digest=digest(source_ids)))
    return dict(global_rows=global_rows, local_rows=local_rows, project_summary=summaries,
                inputs=inputs, source=source, physical_T1_transport_rows=physical,
                eligible_scopes=scopes, recovered_contract=contract)


def install_guard(destination):
    allowed = { (ROOT / p).resolve() for p in INPUTS + CODE + [SOURCE] }
    allowed.update((ROOT / p).parent / 'MANIFEST.sha256' for p in INPUTS)
    opened = set()
    def guard(event, args):
        if event != 'open' or not isinstance(args[0], (str, bytes, os.PathLike)):
            return
        path = Path(os.fsdecode(args[0])).resolve()
        mode, flags = args[1] or '', args[2] or 0
        writing = any(c in mode for c in 'wax+') or bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC))
        if writing:
            require(path == destination.resolve(), 'Worker write outside its result file')
        elif path.is_relative_to(ROOT / 'audits') or path.is_relative_to(ROOT / 'data') or path.is_relative_to(ROOT / 'artifacts'):
            require(path in allowed, 'Unapproved scientific read: ' + str(path))
            opened.add(str(path.relative_to(ROOT)))
    sys.addaudithook(guard)
    return opened


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--worker', type=Path)
    args = parser.parse_args()
    if args.worker:
        accesses = install_guard(args.worker)
        result = compute()
        result['read_access_log'] = sorted(accesses)
        args.worker.write_bytes(enc(result))
        return
    require(git('symbolic-ref', '--short', 'HEAD') == BRANCH, 'Wrong branch')
    require(Path(git('rev-parse', '--show-toplevel')) == ROOT, 'Wrong repository')
    require(not OUT.exists(), 'Never overwrite prior population evidence')
    baseline = git('status', '--porcelain=v1')
    head = git('rev-parse', 'HEAD')
    with tempfile.TemporaryDirectory(prefix='e2-foreground-') as tmp:
        repetitions = []
        for i in [1, 2]:
            dest = Path(tmp) / f'repetition_{i}.json'
            subprocess.run([sys.executable, '-m', 'src.evaluation.q1_e2_t1_foreground_freeze',
                            '--worker', str(dest)], cwd=ROOT, check=True,
                           env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
            repetitions.append(dest.read_bytes())
        require(repetitions[0] == repetitions[1], 'Independent-process reproduction mismatch')
        result = json.loads(repetitions[0])
    OUT.mkdir(parents=True)
    save = lambda name, obj: (OUT / name).write_bytes(enc(obj))
    output_hashes = {}
    for field, filename in [('global_rows', 't1_global_foreground_population.jsonl'),
                            ('local_rows', 't1_local_case_population.jsonl')]:
        payload = b''.join(enc(row) for row in result[field])
        (OUT / filename).write_bytes(payload)
        output_hashes[filename] = hashlib.sha256(payload).hexdigest()
    save('recovered_selection_contract.json', dict(
        prospective_contract=result['recovered_contract'],
        authority_paths=INPUTS + CODE,
        source_authority='Sprint56.2C isolated frozen T1 inventory and producer; Sprint56.2H historical E2 track; current task authorizes identity-only population materialization.',
        selector='Unchanged src.evaluation.q1_primary_xai_population_freeze.select_population',
        global_key_identity=None, local_key_identity='Existing E2 scope model_identity_sha256 (parent selector test)',
        selection_fields=['seed', 'purpose', 'project', 'model_identity_sha256', 'row_identifier'],
        validation_fields=['partition', 'algorithm', 'configuration'],
        excluded_fields=['labels', 'probabilities', 'confidence', 'correctness', 'predicted_decision', 'E2 contributions'],
        transport_boundary='Known T1-only gzip is decoded; JSON projection drops nonidentity fields. Label/prediction bytes exist in transport; values are not retrieved, selected, logged or persisted. No scientific probability query is executed.',
        output_schema=dict(global_fields=sorted(result['global_rows'][0]), local_fields=sorted(result['local_rows'][0])),
        serialization_conventions=dict(ordinal='1-based within project/global or scope/local',
            selection_hash='SHA256 canonical JSON sorted selected row identifier list',
            ordering_hash='SHA256 canonical JSON selected row identifier list in emitted order',
            source_membership_digest='SHA256 original ordered T1 row identifier list; exactly reconciled to frozen G4/G5 scope ledger',
            outer_order='project ASC; local algorithm ASC then configuration ASC; within population frozen key order',
            note='Packaging conventions implement required provenance fields; they do not change the predeclared selector. No TRAIN class field in T1 outputs.')))
    save('deterministic_reproduction.json', dict(status='PASS', independent_processes=2,
        independent_selector_check='PASS in both processes', exact_binary_equal=True,
        differing_rows=0, repetition_payload_sha256=[hashlib.sha256(b).hexdigest() for b in repetitions],
        output_hashes=output_hashes, each_process_reopens_frozen_source=True))
    save('source_access_and_governance.json', dict(counters=ZERO, read_access_log_per_process=result['read_access_log'],
        T2_scientific_access_log=[], source_transport_passes=2,
        source_T1_transport_rows_per_pass=result['physical_T1_transport_rows'],
        labels_used=False, confidence_or_correctness_used=False, transport_boundary='See recovered_selection_contract.json'))
    save('population_manifest.json', dict(status='E2_T1_FOREGROUND_FREEZE_PASS',
        timestamp_UTC=datetime.now(timezone.utc).isoformat(), starting_HEAD=head, branch=BRANCH,
        starting_working_tree=baseline, runtime=dict(python=platform.python_version(), packages='standard library only'),
        parent_blocked_package=POP, parent_closure_diagnostic='audits/q1-e2-final-closure/1.0.0/',
        prior_blocked_evidence_preserved=True, critical_inputs=result['inputs'],
        source_T1_artifact=dict(path=SOURCE, sha256=result['source']['sha256']),
        eligible_scopes=221, eligible_configuration_counts=COUNTS,
        eligible_scope_identities=[{k:r[k] for k in ['project','algorithm','configuration','model_identity_sha256']} for r in result['eligible_scopes']],
        unique_T1_source_rows=sum(p['source_rows'] for p in result['project_summary']),
        global_rows=len(result['global_rows']), local_scope_rows=len(result['local_rows']),
        global_scope_rows=sum(p['global_rows']*p['eligible_scopes'] for p in result['project_summary']),
        per_project=result['project_summary'], output_hashes=output_hashes,
        recovered_contract_sha256=sha(OUT/'recovered_selection_contract.json'),
        implementation_sha256=sha(Path(__file__)), counters=ZERO,
        attribution_executed=False, E2_final_closure_status='NOT_CLOSED_BY_THIS_TASK',
        remaining_foreground_blockers=[], next_stage='READY_TO_RESUME_EXISTING_E2_FINAL_CLOSURE_PROMPT'))
    require(check_inputs() == result['inputs'], 'Parent evidence changed')
    report = f'''# E2 T1 foreground freeze

**E2_T1_FOREGROUND_FREEZE_PASS**

Branch: {BRANCH}. Starting HEAD: {head}. Prior diagnostic package preserved.

The unchanged Sprint56.2 selector and its prospective contract define seed 20260901,
SHA-256 of canonical JSON (seed, purpose, project, model_identity_sha256, row_identifier),
then selection_key ascending and row_identifier ascending. Global selection is unstratified,
at most 256/project with null model identity; local selection is at most 8/eligible scope,
from that project's global subset with the frozen scope model identity and the distinct
T1_LOCAL_CASE_SELECTION purpose. All available cases are retained when below the limit.
No labels, predicted decisions, confidence, correctness or explanation values select cases.
The later per-project unstratified rule supersedes Sprint55's conditional predicted strata.

Authoritative source: `{SOURCE}`.
SHA-256: `{result['source']['sha256']}`.
The Sprint56.2C source inventory establishes physically isolated T1 evidence; its producer
and existing ordered G4/G5 membership digests establish identity provenance. The current
task authorizes materialization from this frozen source; no mixed dataset was accessed.
The T1 gzip contains label/prediction bytes; they are decoded as transport but dropped by
the identity projection and never used, inspected for selection, logged or persisted.
This does not claim zero physical decoding of T1 label/prediction bytes.

Eligible E2 scopes: 221 (C+P 56, C+T 55, P+T 55, C+P+T 55), unchanged.
Global project-row records: {len(result['global_rows'])}.
Local scope-row records: {len(result['local_rows'])} (8 per eligible scope).
Scope-weighted global rows: {sum(p['global_rows']*p['eligible_scopes'] for p in result['project_summary'])}.
Source unique T1 rows: {sum(p['source_rows'] for p in result['project_summary'])}.
Local counts repeat a commit across scopes; they are not counts of unique commits.

Provenance/selection use only identity fields, scope identity and fixed seed/purpose;
partition is T1 by the verified isolated-source provenance. Every eligible scope's
ordered source identity list matched its pre-existing G4/G5 digest and count, and
all scopes of each project had exactly the same ordered membership.

Two fresh Python processes independently reopened the source and repeated the complete
validation and selection. Both also checked results against an independent implementation
of the frozen hash recipe. Complete result payloads were byte-identical, with zero differing
rows. Per-output hashes are in `deterministic_reproduction.json` and `population_manifest.json`.
Contract hash: `{sha(OUT/'recovered_selection_contract.json')}`.
Population manifest hash: `{sha(OUT/'population_manifest.json')}`.

Global output SHA-256: `{output_hashes['t1_global_foreground_population.jsonl']}`.
Local output SHA-256: `{output_hashes['t1_local_case_population.jsonl']}`.

T2 scientific accesses = 0; model retraining = 0; calibration refits = 0;
predictive recomputations = 0; E1 reruns = 0; E2 attribution executions = 0.
No historical population, predictive artifact, E1 result or earlier diagnostic was overwritten.
No commit, push, merge, rebase or reset was performed.

No foreground-freeze blocker remains. E2 itself is not closed: attribution, numerical
fidelity, deterministic attribution reproduction and publication tables/figures remain
for the separately authorized final-closure task. This PASS covers the T1 foreground only.

READY_TO_RESUME_EXISTING_E2_FINAL_CLOSURE_PROMPT
'''
    (OUT/'E2_T1_FOREGROUND_FREEZE_REPORT.md').write_text(report)
    (OUT/'MANIFEST.sha256').write_text(''.join(f'{sha(p)}  {p.name}\n' for p in sorted(OUT.iterdir()) if p.is_file()))
    print('E2_T1_FOREGROUND_FREEZE_PASS', len(result['global_rows']), len(result['local_rows']))


if __name__ == '__main__':
    main()
