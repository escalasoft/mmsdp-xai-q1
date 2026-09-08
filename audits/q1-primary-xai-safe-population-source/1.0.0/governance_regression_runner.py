import sys
from src.evaluation import q1_primary_xai_safe_population_source as s
import pytest
sys.addaudithook(s.guard)
args=['-q','-p','no:cacheprovider',
 'tests/evaluation/test_q1_t1_confirmatory_execution.py::test_second_t1_access_is_blocked_before_payload_materialization',
 'tests/evaluation/test_q1_t1_confirmatory_execution.py::test_block2_authorization_is_intact_and_not_accessed',
 'tests/evaluation/test_q1_xai_runtime_freeze.py',
 'tests/evaluation/test_q1_xai_shap_compatibility_resolution.py',
 'tests/evaluation/test_q1_xai_external_artifact_store_freeze.py',
 'tests/evaluation/test_q1_primary_xai_runtime_smoke.py::test_environment_separation_and_inventory_preservation',
 'tests/evaluation/test_q1_primary_xai_runtime_smoke.py::test_guard_denies_protected_reads_and_state_writes',
 'tests/evaluation/test_q1_primary_xai_runtime_smoke.py::test_no_reconstruction_refit_metrics_or_unapproved_explainers',
 'tests/evaluation/test_q1_primary_xai_runtime_smoke.py::test_lock_is_frozen_before_scientific_execution_and_wheels_are_hashed',
 'tests/evaluation/test_q1_primary_xai_runtime_smoke.py::test_narrow_ignores_without_historical_worktree_size_assumption',
 'tests/evaluation/test_q1_primary_xai_runtime_smoke.py::test_manifest_exact_and_primary_execution_unauthorized',
 'tests/evaluation/test_q1_primary_xai_population_freeze.py',
 '-k','not test_gitignore_is_exact_narrow_and_registry_remains_visible']
raise SystemExit(pytest.main(args))
