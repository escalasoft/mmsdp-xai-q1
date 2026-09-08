import sys
from src.evaluation import q1_primary_xai_t2_semantic_boundary as s
import pytest
# These parent namespaces contain governance metadata, not scientific row payloads.
for prefix in ['audits/q1-xai-runtime-freeze/1.0.0/',s.Q]:
    s.ALLOW.update(p.relative_to(s.ROOT).as_posix() for p in (s.ROOT/prefix).iterdir() if p.is_file())
s.ALLOW.update(p.relative_to(s.ROOT).as_posix() for p in (s.ROOT/s.P).glob('*.json'))
s.ALLOW.add('audits/q1-xai-final-output-equivalence-g5/1.0.0/xai_readiness_ledger.jsonl')
s.ALLOW.update(s.S+x for x in ['predictive_inventory_before.json','predictive_inventory_after.json','isolated_runtime_installation_provenance.json'])
s.ALLOW.add('pyproject.toml')
s.ALLOW.update(s.S+x for x in ['runtime_read_events.json','runtime_governance_counters.json'])
for name in ['train_reference_population.jsonl','t1_global_foreground_population.jsonl','t1_local_case_population.jsonl','correlated_feature_groups.jsonl']:
    assert (s.ROOT/s.P/name).stat().st_size==0
    s.ALLOW.add(s.P+name)
sys.addaudithook(s.guard)
args=['-q','-p','no:cacheprovider','tests/evaluation/test_q1_xai_runtime_freeze.py',
 'tests/evaluation/test_q1_primary_xai_runtime_smoke.py::test_environment_separation_and_inventory_preservation',
 'tests/evaluation/test_q1_primary_xai_runtime_smoke.py::test_guard_denies_protected_reads_and_state_writes',
 'tests/evaluation/test_q1_primary_xai_runtime_smoke.py::test_no_reconstruction_refit_metrics_or_unapproved_explainers',
 'tests/evaluation/test_q1_primary_xai_runtime_smoke.py::test_narrow_ignores_without_historical_worktree_size_assumption',
 'tests/evaluation/test_q1_primary_xai_population_freeze.py::test_exact_389_scope_universe_and_three_exclusions',
 'tests/evaluation/test_q1_primary_xai_population_freeze.py::test_guard_no_queries_attributions_metrics_or_immutable_writes',
 'tests/evaluation/test_q1_primary_xai_population_freeze.py::test_missing_population_source_is_not_reported_as_success',
 'tests/evaluation/test_q1_primary_xai_safe_population_source.py::test_branch_and_head',
 'tests/evaluation/test_q1_primary_xai_safe_population_source.py::test_parent_snapshot_matches',
 'tests/evaluation/test_q1_primary_xai_safe_population_source.py::test_all_current_counters_zero',
 'tests/evaluation/test_q1_primary_xai_safe_population_source.py::test_no_safe_candidate_or_real_materialization',
 'tests/evaluation/test_q1_primary_xai_safe_population_source.py::test_no_scientific_api_calls',
 'tests/evaluation/test_q1_primary_xai_safe_population_source.py::test_next_stage_denied',
 'tests/evaluation/test_q1_primary_xai_safe_population_source.py::test_manifest']
code=pytest.main(args)
print('REGRESSION_SCIENTIFIC_PAYLOAD_OPENS=0; current inspection guard active')
raise SystemExit(code)
