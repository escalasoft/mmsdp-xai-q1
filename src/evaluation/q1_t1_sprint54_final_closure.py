"""Materialize the deterministic Sprint 54 human-review closure package."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

from evaluation.q1_t1_confirmatory_execution import (
    AMENDMENT_REL,
    AUTH_REL,
    EXPECTED_AMENDMENT_MANIFEST_SHA256,
    EXPECTED_AMENDMENT_SHA256,
    EXPECTED_AUTHORIZATION_SHA256,
    EXPECTED_SPRINT53_MANIFEST_SHA256,
    EXPECTED_T1_HASH,
    EXPECTED_T1_ROWS,
    EXPECTED_T2_HASH,
    SPRINT53_REL,
    canonical_bytes,
    file_sha256,
    load_json,
    verify_manifest,
)
from evaluation.q1_t1_reporting_traceability_freeze import (
    BLOCK6_CLASSIFICATION,
    BLOCK6_REL,
    BLOCK7_REL,
    EXPECTED_BLOCK6_MANIFEST_SHA256,
    EXPECTED_EVIDENCE_SHA256,
    EXPECTED_RESULTS_MANIFEST_SHA256,
    MIXED,
    RESULTS_REL,
)

VERSION = "q1-t1-sprint54-final-closure-1.0.0"
BLOCK7_CLASSIFICATION = "PASS_REPORTING_TRACEABILITY_FROZEN_MIXED_CONFIRMATORY_EVIDENCE"
FINAL_CLASSIFICATION = (
    "PASS_54_FINAL_CLOSURE_READY_FOR_HUMAN_ACCEPTANCE_AND_GIT_CLOSURE"
)
BLOCK8_REL = AUTH_REL / "block8_final_closure" / "1.0.0"
EXPECTED_AUTH_MANIFEST_SHA256 = (
    "f4f910a5144241b53f7f741ab2e49a5cb541abd8cff88f72c7a05ee30ecaeedf"
)
EXPECTED_BLOCK7_MANIFEST_SHA256 = (
    "538a1df7abbc7c9840faa753d0a401b1d996bef7c0c402eb4d163fd64debca05"
)
EXPECTED_EXECUTION_IDENTIFIER = (
    "9fb5e4f7b43c7f5be7092632c4d471594aa28eeefa22cac4aa4a7e15355d7260"
)
EXPECTED_HEAD = "2c37c261f15678b425facb31959001fb8989dcd7"


class FinalClosureError(RuntimeError):
    """A fail-closed mismatch in the frozen Sprint 54 evidence chain."""


def _atomic_json(path: Path, value: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(canonical_bytes(value))
    os.replace(temporary, path)


def _verify_inputs(root: Path) -> dict[str, Any]:
    protocol = verify_manifest(root / SPRINT53_REL)
    authorization = verify_manifest(root / AUTH_REL)
    amendment = verify_manifest(root / AMENDMENT_REL)
    results = verify_manifest(root / RESULTS_REL)
    block6 = verify_manifest(root / BLOCK6_REL)
    block7 = verify_manifest(root / BLOCK7_REL)
    expected_manifests = (
        (protocol, EXPECTED_SPRINT53_MANIFEST_SHA256, 22),
        (authorization, EXPECTED_AUTH_MANIFEST_SHA256, 1),
        (amendment, EXPECTED_AMENDMENT_MANIFEST_SHA256, 1),
        (results, EXPECTED_RESULTS_MANIFEST_SHA256, 22),
        (block6, EXPECTED_BLOCK6_MANIFEST_SHA256, 7),
        (block7, EXPECTED_BLOCK7_MANIFEST_SHA256, 7),
    )
    if any(
        manifest["manifest_sha256"] != expected_sha
        or manifest["entry_count"] != expected_count
        for manifest, expected_sha, expected_count in expected_manifests
    ):
        raise FinalClosureError("manifest chain mismatch")

    auth = load_json(root / AUTH_REL / "execution_authorization.json")
    amend = load_json(root / AMENDMENT_REL / "authorization_metadata_amendment.json")
    started = load_json(root / RESULTS_REL / "execution_started.json")
    completed = load_json(root / RESULTS_REL / "execution_completed.json")
    integrity = load_json(root / RESULTS_REL / "post_execution_integrity.json")
    correction = load_json(
        root / RESULTS_REL / "post_execution_classification_correction.json"
    )
    scientific = load_json(root / RESULTS_REL / "scientific_classification.json")
    block6_audit = load_json(root / BLOCK6_REL / "confirmatory_evidence_audit.json")
    fusion = load_json(root / BLOCK6_REL / "multimodal_fusion_audit.json")
    block7_registry = load_json(root / BLOCK7_REL / "sealed_reference_registry.json")
    reporting = load_json(root / BLOCK7_REL / "scientific_reporting_contract.json")
    reviewer = load_json(root / BLOCK7_REL / "reviewer_traceability_matrix.json")
    claims = load_json(root / BLOCK7_REL / "manuscript_claim_ledger.json")
    limitations = load_json(root / BLOCK7_REL / "limitations_ledger.json")

    required = (
        file_sha256(root / AUTH_REL / "execution_authorization.json")
        == EXPECTED_AUTHORIZATION_SHA256,
        file_sha256(root / AMENDMENT_REL / "authorization_metadata_amendment.json")
        == EXPECTED_AMENDMENT_SHA256,
        auth["starting_head"] == EXPECTED_HEAD,
        auth["record_status"] == "AUTHORIZED_SCOPE_FROZEN_T1_NOT_YET_ACCESSED",
        auth["scientific_authorization"]["authorization_mode"]
        == "ONE_SHOT_CONFIRMATORY_EVALUATION",
        auth["pre_execution_counters"]["t1_predictive_access_count"] == 0,
        auth["pre_execution_counters"]["t2_predictive_access_count"] == 0,
        auth["pre_execution_counters"]["predictive_scoring_count"] == 0,
        auth["pre_execution_counters"]["xai_execution_count"] == 0,
        auth["heldout_identity_contract"]["t1"]["identity_row_count"]
        == EXPECTED_T1_ROWS,
        auth["heldout_identity_contract"]["t1"]["identity_sha256"] == EXPECTED_T1_HASH,
        auth["heldout_identity_contract"]["t2"]["identity_sha256"] == EXPECTED_T2_HASH,
        auth["threshold_policy"]["decision_threshold"] == 0.5,
        amend["classification"] == "PROSPECTIVE_METADATA_CORRECTION_BEFORE_T1_ACCESS",
        amend["metadata_correction"]["original_declared_entry_count"] == 21,
        amend["metadata_correction"]["effective_entry_count"] == 22,
        amend["remaining_discrepancies_after_effective_view"] == [],
        not any(amend["scientific_contract_changes"].values()),
        started["execution_attempt"] == 1,
        started["execution_identifier"] == EXPECTED_EXECUTION_IDENTIFIER,
        started["state"] == "T1_EXECUTION_STARTED_IRREVERSIBLE",
        completed["state"] == "T1_CONFIRMATORY_EXECUTION_COMPLETE_DO_NOT_RERUN",
        completed["execution_identifier"] == EXPECTED_EXECUTION_IDENTIFIER,
        completed["evidence_sha256"] == EXPECTED_EVIDENCE_SHA256,
        completed["t1_predictive_access_count"] == 1,
        completed["predictive_scoring_count"] == 1,
        completed["t2_predictive_access_count"] == 0,
        completed["xai_execution_count"] == 0,
        completed["t1_rerun_permitted"] is False,
        completed["t2_access_state"] == "DENY_SEALED_REVIEWER_RESERVE",
        completed["evidence_rows"] == 106036,
        completed["scope_count"] == 28,
        completed["project_scope_count"] == 392,
        integrity["status"] == "PASS_COMPLETE_EVIDENCE",
        integrity["unique_t1_identities"] == 3787,
        integrity["positive"] == 1046,
        integrity["negative"] == 2741,
        integrity["duplicate_identity_scope_rows"] == 0,
        integrity["missing_predictions"] == 0,
        integrity["missing_probabilities"] == 0,
        integrity["out_of_range_probabilities"] == 0,
        integrity["t2_contamination"] == 0,
        integrity["development_t1_overlap"] == 0,
        integrity["leakage_contract_violations"] == 0,
        correction["corrected_value"] == MIXED,
        correction["evidence_changed"] is False,
        correction["t1_predictive_access_count_added"] == 0,
        correction["predictive_scoring_count_added"] == 0,
        scientific["classification"] == MIXED,
        block6_audit["audit_classification"] == BLOCK6_CLASSIFICATION,
        block6_audit["evidence_or_metrics_changed"] is False,
        block6_audit["new_integrity_concerns"] == [],
        block7_registry["scientific_classification"] == MIXED,
        block7_registry["block6_classification"] == BLOCK6_CLASSIFICATION,
        block7_registry["sealed_inputs_modified"] is False,
        reporting["classification"] == MIXED,
        reporting["block6_classification"] == BLOCK6_CLASSIFICATION,
        reviewer["concern_count"] == 14,
        claims["status_counts"]
        == {
            "DEFERRED": 2,
            "MIXED": 1,
            "NOT_SUPPORTED": 5,
            "SUPPORTED": 2,
            "SUPPORTED_WITH_LIMITATION": 2,
        },
        limitations["limitation_count"] == 9,
    )
    if not all(required):
        raise FinalClosureError("frozen Sprint 54 closure invariant failed")
    return {
        "auth": auth,
        "amendment": amend,
        "started": started,
        "completed": completed,
        "integrity": integrity,
        "correction": correction,
        "scientific": scientific,
        "block6": block6_audit,
        "fusion": fusion,
        "registry": block7_registry,
        "reporting": reporting,
        "reviewer": reviewer,
        "claims": claims,
        "limitations": limitations,
    }


def _state() -> dict[str, Any]:
    return {
        "schema_version": VERSION,
        "closure_classification": FINAL_CLASSIFICATION,
        "scientific_classification": MIXED,
        "block6_classification": BLOCK6_CLASSIFICATION,
        "block7_classification": BLOCK7_CLASSIFICATION,
        "supported": [
            "Frozen models produced measurable predictive evidence on prospective T1.",
            "T1 execution is complete, internally consistent, and traceable.",
            "Most aggregate primary directions favor full multimodality.",
            "Frozen statistics retain favorable, null, and adverse evidence.",
            "Frozen LightGBM+PROCESS isotonic calibration modestly improved means.",
        ],
        "mixed": [
            "Multimodal benefit is algorithm-dependent.",
            "Full multimodality is not uniformly superior.",
            "Adverse Random Forest primary directions remain part of the evidence.",
        ],
        "not_supported": [
            "Universal multimodal superiority.",
            "Superiority for every project or algorithm.",
            "Causal modality effects.",
            "Verified-clean ground truth.",
            "Universal external generalization.",
            "Causal explanation of near-perfect metrics.",
        ],
        "deferred": [
            "T2 evaluation.",
            "XAI execution and conclusions.",
            "Any reviewer-reserve experiment requiring T2.",
        ],
    }


def _snapshot(data: dict[str, Any]) -> dict[str, Any]:
    integrity = data["integrity"]
    contract = data["reporting"]
    return {
        "schema_version": VERSION,
        "execution": {
            "execution_identifier": EXPECTED_EXECUTION_IDENTIFIER,
            "t1_identities": 3787,
            "positive": 1046,
            "negative": 2741,
            "prevalence": round(integrity["prevalence"], 6),
            "evidence_rows": 106036,
            "scopes": 28,
            "project_scopes": 392,
            "duplicate_rows": 0,
            "missing_predictions": 0,
            "missing_probabilities": 0,
            "out_of_range_probabilities": 0,
            "t2_contamination": 0,
            "train_validation_overlap": 0,
            "leakage_contract_violations": 0,
        },
        "descriptive_pr_auc_no_post_t1_selection": contract[
            "descriptive_results_only_no_post_t1_selection"
        ],
        "statistics": contract["statistical_reporting"],
        "calibration": contract["calibration_reporting"],
        "near_perfect_audit": contract["near_perfect_reporting"],
    }


def _framework(data: dict[str, Any]) -> dict[str, Any]:
    fusion = data["fusion"]
    return {
        "schema_version": VERSION,
        "pipeline": [
            "DATA_SOURCES",
            "CONSTRUCTION_PROVENANCE_LABELING",
            "MODALITY_SPECIFIC_PREPROCESSING",
            "CODE_PROCESS_TEXT",
            "INDEPENDENT_UNIMODAL_LEARNING",
            "BASE_PREDICTIONS",
            "DECISION_LEVEL_LATE_FUSION_STACKING",
            "DEFECT_PROBABILITY",
            "PROBABILISTIC_CALIBRATION",
            "EVALUATION_ROBUSTNESS_STATISTICS",
            "ABLATIONS",
            "XAI_GLOBAL_LOCAL_DEFERRED",
            "ROLE_ADAPTED_QA_EXPLANATIONS_DEFERRED",
        ],
        "distinct_modalities": fusion["semantically_distinct_modalities"],
        "independently_learned_base_modalities": True,
        "fusion_architecture": "DECISION_LEVEL_STACKING_LATE_FUSION",
        "raw_feature_concatenation": False,
        "simple_probability_averaging": False,
        "voting": False,
        "post_t1_meta_learner_fitting": False,
        "calibration_policy": {
            "RAW_project_scopes": 378,
            "ISOTONIC_project_scopes": 14,
            "ISOTONIC_scope": "LightGBM + PROCESS",
            "t1_fitting_or_selection": False,
        },
        "xai_state": "DEFERRED_NOT_EXECUTED",
        "qa_role_explanation_claimed": False,
        "status": "PASS_CONSISTENT_WITH_FROZEN_MMSDP_XAI_PIPELINE",
    }


def _reviewer_final(data: dict[str, Any]) -> dict[str, Any]:
    adverse = data["reporting"]["adverse_random_forest_primary_directions"]
    return {
        "schema_version": VERSION,
        "status": "PASS_14_OF_14_CONCERNS_TRACEABLE",
        "concern_count": data["reviewer"]["concern_count"],
        "concerns": data["reviewer"]["concerns"],
        "partially_addressed_labeled_fully_resolved": False,
        "limitations_hidden": False,
        "adverse_random_forest_directions": adverse,
        "adverse_random_forest_visible": True,
        "near_perfect_categories_presented_as_causal": False,
        "significance_equated_with_practical_significance": False,
        "non_significance_interpreted_as_equivalence": False,
    }


def _claim_limit_freeze(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": VERSION,
        "claim_status_counts": data["claims"]["status_counts"],
        "claims": data["claims"]["claims"],
        "prohibited_overclaims": data["claims"]["prohibited_overclaims"],
        "limitation_count": data["limitations"]["limitation_count"],
        "limitations": data["limitations"]["limitations"],
        "stronger_claims_added_in_block8": False,
    }


def _future_boundary() -> dict[str, Any]:
    return {
        "schema_version": VERSION,
        "permitted_after_human_acceptance": [
            "Commit, push, PR, or merge the already generated Sprint 54 package.",
            "Draft the manuscript from frozen evidence.",
            "Plan a separately governed XAI sprint.",
            "Plan a prospective T2 reviewer-reserve protocol if required.",
        ],
        "not_permitted_without_new_prospective_sprint": [
            "T1 rerun.",
            "T1 reselection, refitting, or rescoring.",
            "Post-T1 threshold optimization.",
            "Post-T1 calibration selection.",
            "Model or hyperparameter changes driven by T1.",
            "Hidden removal of adverse configurations.",
            "T2 access.",
            "XAI execution.",
        ],
        "next_scientifically_authorized_action": (
            "Human scientific review and acceptance of the frozen Sprint 54 package; "
            "after acceptance, Git closure of the already generated package."
        ),
    }


def _chain(root: Path, content_manifest_sha: str) -> dict[str, Any]:
    result_manifest = str(RESULTS_REL / "MANIFEST.sha256")
    stages = [
        (
            "Sprint 53 prospective protocol",
            str(SPRINT53_REL),
            str(SPRINT53_REL / "MANIFEST.sha256"),
            EXPECTED_SPRINT53_MANIFEST_SHA256,
            "PASS_FROZEN_PROSPECTIVE_PROTOCOL",
            "BEFORE_T1",
            False,
            False,
            "Sprint 54 authorization record",
        ),
        (
            "Sprint 54 authorization record",
            str(AUTH_REL / "execution_authorization.json"),
            str(AUTH_REL / "MANIFEST.sha256"),
            EXPECTED_AUTH_MANIFEST_SHA256,
            "AUTHORIZED_SCOPE_FROZEN_T1_NOT_YET_ACCESSED",
            "BEFORE_T1",
            False,
            False,
            "authorization metadata amendment",
        ),
        (
            "authorization metadata amendment",
            str(AMENDMENT_REL / "authorization_metadata_amendment.json"),
            str(AMENDMENT_REL / "MANIFEST.sha256"),
            EXPECTED_AMENDMENT_MANIFEST_SHA256,
            "PROSPECTIVE_METADATA_CORRECTION_BEFORE_T1_ACCESS",
            "BEFORE_T1",
            False,
            False,
            "one-shot T1 execution",
        ),
        (
            "one-shot T1 execution",
            str(RESULTS_REL / "execution_completed.json"),
            result_manifest,
            EXPECTED_RESULTS_MANIFEST_SHA256,
            "T1_CONFIRMATORY_EXECUTION_COMPLETE_DO_NOT_RERUN",
            "DURING_T1",
            True,
            False,
            "sealed T1 evidence",
        ),
        (
            "sealed T1 evidence",
            str(RESULTS_REL / "t1_prediction_evidence.jsonl.gz"),
            result_manifest,
            EXPECTED_RESULTS_MANIFEST_SHA256,
            "SEALED_COMPLETE_106036_ROWS",
            "AFTER_T1_ACCESS",
            False,
            False,
            "post-execution integrity",
        ),
        (
            "post-execution integrity",
            str(RESULTS_REL / "post_execution_integrity.json"),
            result_manifest,
            EXPECTED_RESULTS_MANIFEST_SHA256,
            "PASS_COMPLETE_EVIDENCE",
            "AFTER_T1_ACCESS",
            False,
            False,
            "scientific classification correction",
        ),
        (
            "scientific classification correction",
            str(RESULTS_REL / "post_execution_classification_correction.json"),
            result_manifest,
            EXPECTED_RESULTS_MANIFEST_SHA256,
            "POST_EXECUTION_DERIVED_CLASSIFICATION_CORRECTION_NO_RESCORING",
            "AFTER_T1_ACCESS",
            False,
            False,
            "Block 6 evidence audit",
        ),
        (
            "Block 6 evidence audit",
            str(BLOCK6_REL),
            str(BLOCK6_REL / "MANIFEST.sha256"),
            EXPECTED_BLOCK6_MANIFEST_SHA256,
            BLOCK6_CLASSIFICATION,
            "AFTER_T1_ACCESS",
            False,
            False,
            "Block 7 reporting/reviewer traceability freeze",
        ),
        (
            "Block 7 reporting/reviewer traceability freeze",
            str(BLOCK7_REL),
            str(BLOCK7_REL / "MANIFEST.sha256"),
            EXPECTED_BLOCK7_MANIFEST_SHA256,
            BLOCK7_CLASSIFICATION,
            "AFTER_T1_ACCESS",
            False,
            False,
            "Block 8 final closure",
        ),
        (
            "Block 8 final closure",
            str(BLOCK8_REL),
            str(BLOCK8_REL / "CLOSURE_CONTENT_MANIFEST.sha256"),
            content_manifest_sha,
            FINAL_CLASSIFICATION,
            "AFTER_T1_ACCESS",
            False,
            False,
            None,
        ),
    ]
    records = []
    for (
        stage,
        artifact,
        manifest,
        manifest_sha,
        status,
        timing,
        access,
        evidence_change,
        successor,
    ) in stages:
        artifact_path = root / artifact
        records.append(
            {
                "stage": stage,
                "artifact_or_package_path": artifact,
                "artifact_exists": artifact_path.exists(),
                "artifact_sha256": (
                    file_sha256(artifact_path) if artifact_path.is_file() else None
                ),
                "manifest_path": manifest,
                "manifest_sha256": manifest_sha,
                "governing_status": status,
                "temporal_relation_to_t1": timing,
                "predictive_access_occurred_at_stage": access,
                "predictive_evidence_created_as_authorized": (
                    stage == "one-shot T1 execution"
                ),
                "changed_predictive_evidence": evidence_change,
                "successor_artifact": successor,
            }
        )
    return {
        "schema_version": VERSION,
        "status": "PASS_COMPLETE_CHAIN_OF_CUSTODY",
        "stage_count": len(records),
        "stages": records,
        "all_links_present": True,
        "all_hashes_verified": True,
        "block8_outer_manifest_binding": (
            "MANIFEST.sha256 covers the chain record and every closure artifact; its "
            "hash is reported after deterministic package materialization."
        ),
    }


def _integrity_closure() -> dict[str, Any]:
    return {
        "schema_version": VERSION,
        "status": "PASS_SPRINT54_INTEGRITY_CLOSED",
        "execution_identifier": EXPECTED_EXECUTION_IDENTIFIER,
        "t1_predictive_access_count": 1,
        "predictive_scoring_count": 1,
        "t1_rerun_permitted": False,
        "t2_predictive_access_count": 0,
        "t2_state": "DENY_SEALED_REVIEWER_RESERVE",
        "xai_execution_count": 0,
        "sealed_predictive_or_scientific_artifact_changed": False,
        "post_t1_optimization_occurred": False,
        "new_statistical_test_occurred": False,
        "new_calibration_or_threshold_selection_occurred": False,
        "human_review_required": True,
    }


def _report() -> str:
    sections = [
        ("Scope", "Final consistency review of the sealed Sprint 54 T1 evidence."),
        (
            "Prospective protocol",
            "Sprint 53 and pre-access authorization hashes verify.",
        ),
        (
            "One-shot T1 execution",
            "T1 was accessed and scored exactly once; rerun is prohibited.",
        ),
        (
            "Execution integrity",
            (
                "3,787 identities and 106,036 complete evidence rows passed "
                "integrity checks."
            ),
        ),
        (
            "Predictive findings",
            (
                "Frozen models retain measurable T1 evidence; descriptive results "
                "do not select a new winner."
            ),
        ),
        (
            "Multimodal findings",
            (
                "Most aggregate primary directions favor full multimodality, with "
                "adverse Random Forest directions retained."
            ),
        ),
        (
            "Statistical evidence",
            (
                "The frozen analyses contain 137 favorable, 246 null, and one "
                "adverse contrast."
            ),
        ),
        (
            "Calibration evidence",
            (
                "Frozen LightGBM+PROCESS isotonic calibration produced modest mean "
                "Brier/ECE improvements."
            ),
        ),
        (
            "Near-perfect-result audit",
            (
                "All 62 triggers were preserved; 32 support/threshold and 30 "
                "extreme integrity-supported categories produced no escalation."
            ),
        ),
        (
            "Scientific classification",
            "MIXED_CONFIRMATORY_EVIDENCE; universal superiority is not supported.",
        ),
        (
            "Reviewer traceability",
            (
                "All 14 concerns retain evidence, interpretation, limitation, "
                "safe-claim, and overclaim boundaries."
            ),
        ),
        ("Limitations", "All nine frozen limitations remain explicit and unchanged."),
        (
            "T2 reserve state",
            "T2 predictive access is zero and the reviewer reserve remains sealed.",
        ),
        (
            "XAI state",
            "XAI execution is zero; explanations remain prospectively deferred.",
        ),
        (
            "Permitted future work",
            (
                "After human acceptance: Git closure, manuscript drafting, and "
                "separately governed future planning."
            ),
        ),
        (
            "Prohibited post-T1 actions",
            (
                "No T1 rerun, reselection, rescoring, threshold/calibration "
                "optimization, adverse-result removal, T2 access, or XAI execution."
            ),
        ),
        (
            "Human acceptance checklist",
            (
                "Review hashes, mixed classification, adverse evidence, access "
                "counters, limitations, and future-action boundary before Git closure."
            ),
        ),
    ]
    lines = ["# Final Sprint 54 Human Review Report", ""]
    for index, (title, text) in enumerate(sections, start=1):
        lines.extend([f"## {index}. {title}", "", text, ""])
    return "\n".join(lines)


def materialize_final_closure(root: Path) -> Path:
    data = _verify_inputs(root)
    output = root / BLOCK8_REL
    if output.exists():
        raise FinalClosureError("Block 8 final closure package already exists")
    output.mkdir(parents=True)
    artifacts = {
        "sprint54_final_scientific_state.json": _state(),
        "sprint54_final_result_snapshot.json": _snapshot(data),
        "sprint54_framework_consistency.json": _framework(data),
        "sprint54_reviewer_traceability_final_check.json": _reviewer_final(data),
        "sprint54_claim_and_limitation_freeze.json": _claim_limit_freeze(data),
        "sprint54_future_action_boundary.json": _future_boundary(),
        "sprint54_integrity_closure.json": _integrity_closure(),
    }
    for name, artifact in artifacts.items():
        _atomic_json(output / name, artifact)
    (output / "FINAL_SPRINT54_HUMAN_REVIEW_REPORT.md").write_text(
        _report(), encoding="utf-8"
    )
    content_paths = [output / name for name in artifacts]
    content_paths.append(output / "FINAL_SPRINT54_HUMAN_REVIEW_REPORT.md")
    content_manifest = "".join(
        f"{file_sha256(path)}  {path.name}\n"
        for path in sorted(content_paths, key=lambda item: item.name)
    )
    content_manifest_path = output / "CLOSURE_CONTENT_MANIFEST.sha256"
    content_manifest_path.write_text(content_manifest, encoding="utf-8")
    chain = _chain(root, file_sha256(content_manifest_path))
    _atomic_json(output / "sprint54_chain_of_custody.json", chain)
    manifest = "".join(
        f"{file_sha256(path)}  {path.name}\n"
        for path in sorted(output.iterdir(), key=lambda item: item.name)
        if path.name != "MANIFEST.sha256"
    )
    (output / "MANIFEST.sha256").write_text(manifest, encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    print(materialize_final_closure(args.root.resolve()))


if __name__ == "__main__":
    main()
