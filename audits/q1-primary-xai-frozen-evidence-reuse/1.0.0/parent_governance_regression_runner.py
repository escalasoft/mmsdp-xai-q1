import sys
import pytest
from src.evaluation import q1_primary_xai_frozen_evidence_reuse as s
s.prepare()
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
args.extend(['tests/evaluation/test_q1_primary_xai_t2_semantic_boundary.py::test_actual_decision_does_not_overclaim','tests/evaluation/test_q1_primary_xai_t2_semantic_boundary.py::test_canonical_recipe_complete_and_new_namespace','tests/evaluation/test_q1_primary_xai_t2_semantic_boundary.py::test_counters_and_stop','tests/evaluation/test_q1_primary_xai_t2_semantic_boundary.py::test_manifest'])
raise SystemExit(pytest.main(args))
