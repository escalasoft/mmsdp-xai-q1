import sys
import pytest
from src.evaluation import q1_primary_xai_e1_e2_resolution as s
s.prepare()
sys.addaudithook(s.guard)
base=['test_parent_hashes_unchanged','test_scope_integrity_exclusions','test_e1_e2_independent','test_t1_exact_g4_reference_reconciliation','test_oof_membership_provenance_and_reference_limit','test_e2_coverage_order_and_no_overclaim','test_project_and_modality_coverage_reconcile','test_graphics_map_matches_inputs','test_counters_and_unique_file_inventory','test_manifest']
q1=['test_base_manifest_and_all_files_unchanged','test_scientific_verdict_separate_and_defensible','test_claim_traceability_fields_and_no_supported_partial_claim','test_graphs_not_publication_ready','test_scientific_counters_unchanged_and_zero_for_amendment','test_amendment_manifest']
d=['test_parent_evidence_unchanged','test_scopes_and_exclusions','test_e1_e2_independent_not_ready','test_reference_regimes_and_exact_provenance','test_fusion_model_and_modality_order','test_fidelity_complete','test_stability_and_heterogeneity_complete','test_manifest']
s54=['test_pre_and_post_execution_integrity_check_inventory','test_second_t1_access_is_blocked_before_payload_materialization']
args=['-q','-p','no:cacheprovider']
for file,names in [('test_q1_primary_xai_frozen_evidence_reuse.py',base),('test_q1_scientific_sufficiency.py',q1),('test_q1_primary_xai_missing_evidence_remediation.py',d),('test_q1_t1_confirmatory_execution.py',s54)]:args.extend(f'tests/evaluation/{file}::{n}' for n in names)
raise SystemExit(pytest.main(args))
