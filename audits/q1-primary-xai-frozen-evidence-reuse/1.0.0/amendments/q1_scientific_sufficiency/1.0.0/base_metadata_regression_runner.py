import sys
import pytest
from src.evaluation import q1_primary_xai_q1_scientific_sufficiency as s
sys.addaudithook(s.guard)
names=['test_parent_hashes_unchanged','test_scope_integrity_exclusions','test_e1_e2_independent',
 'test_t1_exact_g4_reference_reconciliation','test_oof_membership_provenance_and_reference_limit',
 'test_e2_coverage_order_and_no_overclaim','test_project_and_modality_coverage_reconcile',
 'test_graphics_map_matches_inputs','test_counters_and_unique_file_inventory','test_manifest']
raise SystemExit(pytest.main(['-q','-p','no:cacheprovider',*[f'tests/evaluation/test_q1_primary_xai_frozen_evidence_reuse.py::{name}' for name in names]]))
