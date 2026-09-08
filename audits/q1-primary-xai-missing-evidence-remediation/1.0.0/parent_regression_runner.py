import sys
import pytest
from src.evaluation import q1_primary_xai_missing_evidence_remediation as s
s.prepare()
sys.addaudithook(s.guard)
base=['test_parent_hashes_unchanged','test_scope_integrity_exclusions','test_e1_e2_independent','test_t1_exact_g4_reference_reconciliation','test_oof_membership_provenance_and_reference_limit','test_e2_coverage_order_and_no_overclaim','test_project_and_modality_coverage_reconcile','test_graphics_map_matches_inputs','test_counters_and_unique_file_inventory','test_manifest']
q1=['test_base_manifest_and_all_files_unchanged','test_scientific_verdict_separate_and_defensible','test_claim_traceability_fields_and_no_supported_partial_claim','test_graphs_not_publication_ready','test_scientific_counters_unchanged_and_zero_for_amendment','test_amendment_manifest']
raise SystemExit(pytest.main(['-q','-p','no:cacheprovider',*[f'tests/evaluation/test_q1_primary_xai_frozen_evidence_reuse.py::{n}' for n in base],*[f'tests/evaluation/test_q1_scientific_sufficiency.py::{n}' for n in q1]]))
