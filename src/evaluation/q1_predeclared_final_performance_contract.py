# ruff: noqa: E501
"""Sprint 44 prospective final-performance evaluation contract."""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
from pathlib import Path
from typing import Any

PROTOCOL_ID = "q1-predeclared-final-performance-contract"
VERSION = "1.0.0"
SPRINT = "10.8.2.44"
STARTING_MAIN = "1cd7b980c36a212f24d9cc239de2fcdb8473b821"
OUTPUT_REL = "audits/q1-predeclared-final-performance-contract/1.0.0"
SPRINT43_PATH = "audits/q1-controlled-advancement-decision/1.0.0/advancement_decision.json"
PRIMARY_METRICS = ("ROC-AUC", "PR-AUC", "Precision", "Recall", "F1-score", "MCC")
CALIBRATION_METRICS = ("Brier score", "ECE")
UTILITY_EVIDENCE = ("decision-curve evidence", "normalized/cost-based evidence")
PROHIBITED_COUNTERS = (
    "TEST_label_accesses", "TEST_prediction_accesses", "TEST_probability_loading",
    "TEST_scoring", "TEST_derived_artifact_inspections", "TEST_model_selection",
    "TEST_threshold_optimization", "TEST_calibration_fitting", "TEST_XAI",
    "model_fits", "model_refits", "calibrator_fits", "calibrator_refits",
    "meta_learner_fits", "hyperparameter_searches", "threshold_optimizations",
    "feature_selections", "imbalance_interventions", "modality_selections",
    "candidate_selections", "architecture_modifications", "external_dataset_acquisitions",
    "XAI_executions", "SHAP_executions", "LIME_executions", "counterfactual_generations",
)


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode()


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(root: Path, relative: str) -> Any:
    return json.loads((root / relative).read_text(encoding="utf-8"))


def validate_sprint43(value: dict[str, Any]) -> None:
    expected = {
        "advancement_outcome": "GO_WITH_LIMITATIONS",
        "matched_precedence_rule": "RULE_4",
        "test_access_authorized": False,
        "test_sealed": True,
        "final_candidate_authorized": False,
        "threshold_selection_authorized": False,
        "calibration_selection_authorized": False,
        "xai_authorized": False,
    }
    if value.get("sprint") != "10.8.2.43" or any(value.get(k) != v for k, v in expected.items()):
        raise ValueError("accepted Sprint 43 governance facts do not match the required immutable state")


def contract(root: Path) -> dict[str, Any]:
    sprint43 = load_json(root, SPRINT43_PATH)
    validate_sprint43(sprint43)
    return {
        "protocol_id": PROTOCOL_ID,
        "version": VERSION,
        "sprint": SPRINT,
        "contract_mode": "PROSPECTIVE_DECLARATION_ONLY",
        "effective_boundary": "BEFORE_ANY_TEST_ACCESS_OR_FINAL_CANDIDATE_DECISION",
        "authoritative_sprint43_input": {"path": SPRINT43_PATH, "sha256": digest(root / SPRINT43_PATH), **{k: sprint43[k] for k in ("advancement_outcome", "matched_precedence_rule", "test_access_authorized", "test_sealed", "final_candidate_authorized", "threshold_selection_authorized", "calibration_selection_authorized", "xai_authorized")}},
        "scientific_dimensions": {
            "comparative_contribution": "multimodal versus every admissible predeclared unimodal reference",
            "absolute_predictive_quality": "continuous discrimination and classification evidence",
            "probability_quality": "calibration evidence",
            "practical_utility": "decision-curve and cost evidence where applicable",
            "robustness_stability": "origin/evaluation-unit evidence without averaging away contradictions",
        },
        "reporting": {
            "primary_metrics_required_exactly": list(PRIMARY_METRICS),
            "mandatory_descriptive_context": ["positive-class prevalence"],
            "calibration_metrics_required_exactly": list(CALIBRATION_METRICS),
            "utility_evidence_required_where_applicable": list(UTILITY_EVIDENCE),
            "all_metrics_mandatory_even_when_unfavorable": True,
            "accuracy_not_sole_or_principal": True,
            "origin_level_evidence_preserved_when_available": True,
            "uncertainty": {"continuous_values_required": True, "comparative_deltas_required": True, "uncertainty_required": True, "method_must_be_predeclared_or_inherited": True, "no_post_hoc_metric_or_interval_selection": True},
        },
        "comparison_governance": {
            "comparators": "all predeclared admissible unimodal references; no easiest-to-beat selection",
            "metrics_fixed_before_outcomes": True,
            "favorable_origin_dropping_prohibited": True,
            "favorable_threshold_selection_prohibited": True,
            "contradictory_origin_averaging_prohibited": True,
        },
        "imbalance_governance": {
            "positive_class_prevalence_mandatory": True,
            "primary_experiment_post_outcome_prohibited": ["SMOTE", "SMOTE-Tomek", "ADASYN", "arbitrary over-sampling", "arbitrary under-sampling", "new cost-sensitive losses", "class-weight changes"],
            "future_experiment_conditions": ["independently prospective declaration", "TRAIN-only or formally authorized fitting", "explicit frozen-baseline comparison"],
            "implemented_in_sprint44": False,
        },
        "feature_selection_governance": {
            "primary_feature_space": "ALREADY_ACCEPTED_FROZEN_FEATURE_SPACE",
            "post_hoc_prohibited": ["Boruta", "genetic-algorithm feature selection", "recursive selection", "outcome-driven dimensionality reduction", "post-result correlation filtering"],
            "future_experiment_boundary": "independently predeclared TRAIN-only or formally nested development protocol",
        },
        "representation_scope": {
            "primary_representations": ["CODE", "PROCESS", "TEXT"],
            "status": "FROZEN_AS_ACCEPTED",
            "post_hoc_rescue_prohibited": True,
            "prospective_extensions_not_primary": ["CodeBERT", "new pretrained code embeddings", "AST CNNs", "GNN representations", "new semantic encoders", "redesigned modality"],
        },
        "interpretation": {
            "categories": ["STRONG", "MODERATE", "LIMITED", "INCONCLUSIVE"],
            "arbitrary_absolute_cutoffs_prohibited": True,
            "rule": "Use continuous metrics, comparative deltas, uncertainty, calibration, utility, robustness, diagnostics, and limitations; absent a historically frozen scientifically justified cutoff, do not fabricate one.",
        },
        "anomalously_high_performance": {
            "automatic_acceptance_prohibited": True,
            "diagnostic_audit_required": True,
            "audit_result_must_be_persisted": True,
            "checks": ["leakage", "temporal contamination", "duplicated or overlapping observations", "label-derived proxies", "bug/fix semantic leakage", "improper feature provenance", "train/evaluation overlap", "suspicious class separability", "repeated entities crossing prohibited temporal boundaries"],
        },
        "limited_performance": {
            "report_exactly_and_preserve_as_evidence": True,
            "unfavorable_metric_omission_prohibited": True,
            "retrospective_hypothesis_change_prohibited": True,
            "test_tuning_prohibited": True,
            "rescue_models_features_resampling_prohibited": True,
            "absolute_and_comparative_claims_must_be_distinguished": True,
            "narrower_claim_allowed_only_if_supported": True,
        },
        "later_test_authorization_request_conditions": [
            "Sprint 44 contract has immutable human acceptance", "historical integrity and manifest verification pass",
            "all required metrics/comparators/uncertainty procedures remain frozen", "candidate, threshold, and calibrator are independently authorized under accepted governance",
            "TEST remains sealed until a later explicit human-accepted authorization", "one-shot execution and zero-pre-access prohibited-operation ledger are verified",
            "high-performance diagnostic audit and limited-performance preservation procedures are operationally ready",
        ],
        "sprint44_authorizations": {"test_access_authorized": False, "final_candidate_authorized": False, "threshold_selection_authorized": False, "calibration_selection_authorized": False, "xai_authorized": False, "later_sprint_started": False},
        "test_sealed": True,
    }


def validate_contract(value: dict[str, Any]) -> None:
    if value.get("protocol_id") != PROTOCOL_ID or value.get("test_sealed") is not True:
        raise ValueError("invalid contract identity or TEST boundary")
    reporting = value.get("reporting", {})
    if reporting.get("primary_metrics_required_exactly") != list(PRIMARY_METRICS):
        raise ValueError("primary metric set was reduced or changed")
    if reporting.get("calibration_metrics_required_exactly") != list(CALIBRATION_METRICS):
        raise ValueError("calibration metric set was reduced or changed")
    if reporting.get("mandatory_descriptive_context") != [
        "positive-class prevalence"
    ]:
        raise ValueError("positive-class prevalence context is mandatory")
    if value.get("imbalance_governance", {}).get("positive_class_prevalence_mandatory") is not True:
        raise ValueError("positive-class prevalence is mandatory")
    if any(value.get("sprint44_authorizations", {}).values()):
        raise ValueError("Sprint 44 cannot grant execution authorization")


def execution_ledger() -> dict[str, Any]:
    return {"sprint_mode": "CONTRACT_ONLY", **dict.fromkeys(PROHIBITED_COUNTERS, 0)}


def accepted_historical_hashes(root: Path) -> dict[str, str]:
    paths = subprocess.run(["git", "ls-tree", "-r", "--name-only", STARTING_MAIN, "--", "audits"], cwd=root, check=True, capture_output=True, text=True).stdout.splitlines()
    return {path: hashlib.sha256(subprocess.run(["git", "show", f"{STARTING_MAIN}:{path}"], cwd=root, check=True, capture_output=True).stdout).hexdigest() for path in sorted(paths)}


def verify_historical_integrity(root: Path, expected: dict[str, str]) -> dict[str, Any]:
    observed = {str(p.relative_to(root)): digest(p) for p in (root / "audits").rglob("*") if p.is_file() and not str(p.relative_to(root)).startswith(OUTPUT_REL + "/")}
    missing = sorted(set(expected) - set(observed))
    unexpected = sorted(set(observed) - set(expected))
    mismatches = sorted(p for p in set(expected) & set(observed) if expected[p] != observed[p])
    modified = [p for p in subprocess.run(["git", "diff", "--name-only", STARTING_MAIN, "--", "audits"], cwd=root, check=True, capture_output=True, text=True).stdout.splitlines() if not p.startswith(OUTPUT_REL + "/")]
    return {"baseline_revision": STARTING_MAIN, "baseline_source": "accepted immutable Git objects at starting main", "protected_files_checked": len(expected), "missing_files": missing, "unexpected_files": unexpected, "hash_mismatches": mismatches, "historical_tracked_modifications": sorted(modified), "passed": not (missing or unexpected or mismatches or modified)}


def schema() -> dict[str, Any]:
    return {"$schema": "http://json-schema.org/draft-07/schema#", "type": "object", "additionalProperties": False, "required": ["protocol_id", "version", "sprint", "contract_mode", "authoritative_sprint43_input", "scientific_dimensions", "reporting", "comparison_governance", "imbalance_governance", "feature_selection_governance", "representation_scope", "interpretation", "anomalously_high_performance", "limited_performance", "later_test_authorization_request_conditions", "sprint44_authorizations", "test_sealed", "effective_boundary"], "properties": {"protocol_id": {"const": PROTOCOL_ID}, "version": {"const": VERSION}, "sprint": {"const": SPRINT}, "contract_mode": {"const": "PROSPECTIVE_DECLARATION_ONLY"}, "test_sealed": {"const": True}, **{k: {"type": "object"} for k in ("authoritative_sprint43_input", "scientific_dimensions", "reporting", "comparison_governance", "imbalance_governance", "feature_selection_governance", "representation_scope", "interpretation", "anomalously_high_performance", "limited_performance", "sprint44_authorizations")}, "later_test_authorization_request_conditions": {"type": "array", "minItems": 1, "items": {"type": "string"}}, "effective_boundary": {"type": "string"}}}


def report(value: dict[str, Any], history: dict[str, Any]) -> str:
    return f"""# Sprint 10.8.2.44 — Predeclared Final Performance Evaluation Contract

## Scope and authority

This is a prospective contract only. Sprint 43 is consumed at SHA-256 `{value['authoritative_sprint43_input']['sha256']}` with outcome `GO_WITH_LIMITATIONS` under `RULE_4`. That outcome does not authorize TEST. TEST remains sealed and candidate, threshold, calibrator, and XAI authorization remain false.

## Frozen evidence

Primary predictive-performance reporting is mandatory and non-reducible: {', '.join(PRIMARY_METRICS)}. Positive-class prevalence is not a predictive-performance metric; it is mandatory descriptive class-distribution context and must accompany performance reporting independently. Calibration requires {', '.join(CALIBRATION_METRICS)}. Decision-curve and normalized/cost evidence are required where applicable. Accuracy cannot be the sole or principal argument; unfavorable and origin-level results cannot be hidden.

## Prospective safeguards

The accepted feature space and CODE/PROCESS/TEXT representations are frozen. Post-outcome imbalance intervention, feature selection, representation redesign, TEST tuning, and rescue experiments are prohibited. Anomalously high performance requires a persisted diagnostic audit and is never automatically accepted. Moderate or limited performance is reported exactly, preserved, and may support only a narrower evidence-backed claim.

## Interpretation

Comparative contribution, absolute predictive quality, calibration, practical utility, and robustness/stability are distinct, scientifically material dimensions. Interpretation uses STRONG, MODERATE, LIMITED, or INCONCLUSIVE without fabricated numerical cutoffs.

## Integrity and execution

Historical integrity: **{'PASS' if history['passed'] else 'FAIL'}** across `{history['protected_files_checked']}` accepted audit files. Every prohibited-operation counter is zero. Later TEST access requires a separate, explicit, human-accepted authorization; this contract does not grant it.
"""


def materialize(root: Path) -> Path:
    output = root / OUTPUT_REL
    output.mkdir(parents=True, exist_ok=True)
    value = contract(root)
    validate_contract(value)
    hashes = accepted_historical_hashes(root)
    history = verify_historical_integrity(root, hashes)
    if not history["passed"]:
        raise RuntimeError("protected historical artifact drift")
    artifacts = {"final_performance_contract.json": value, "final_performance_contract.schema.json": schema(), "execution_ledger.json": execution_ledger(), "historical_artifact_hashes.json": hashes, "historical_integrity.json": history, "quality_gates.json": {"status": "NOT_RUN_BY_MATERIALIZER", "observed_results": []}, "scientific_decision.json": {"decision": "SPRINT_10.8.2.44_READY_FOR_HUMAN_REVIEW", "scope": "PROSPECTIVE_CONTRACT_ONLY", "human_acceptance_required": True, "test_access_authorized": False, "final_candidate_authorized": False, "threshold_selection_authorized": False, "calibration_selection_authorized": False, "xai_authorized": False}}
    for name, item in artifacts.items():
        (output / name).write_bytes(canonical_bytes(item))
    manifest = {"protocol_id": PROTOCOL_ID, "version": VERSION, "sprint": SPRINT, "starting_main": STARTING_MAIN, "runtime": {"python": platform.python_version(), "platform": platform.platform()}, "implementation_sha256": digest(root / "src/evaluation/q1_predeclared_final_performance_contract.py"), "tests_sha256": digest(root / "tests/evaluation/test_q1_predeclared_final_performance_contract.py"), "source_artifact_sha256": {SPRINT43_PATH: digest(root / SPRINT43_PATH)}, "artifact_sha256": {name: digest(output / name) for name in sorted(artifacts)}}
    (output / "experiment_manifest.json").write_bytes(canonical_bytes(manifest))
    (output / "REPORT.md").write_text(report(value, history), encoding="utf-8")
    return output


def record_quality_gates(root: Path, observed: list[dict[str, Any]]) -> None:
    """Persist already-observed validation results without executing experiments."""
    required = {
        "focused_pytest", "preceding_regressions", "legacy_full_pytest", "ruff",
        "python_compilation", "ajv_schema", "deterministic_replay",
        "artifact_manifest", "historical_integrity", "git_diff_check",
    }
    if {row.get("id") for row in observed} != required:
        raise ValueError("incomplete quality-gate evidence")
    if any(row.get("exit_code") != 0 or not row.get("observed_output") for row in observed):
        raise ValueError("a quality gate did not pass")
    output = root / OUTPUT_REL
    quality = {"status": "PASS_FROM_EXECUTED_COMMANDS", "observed_results": observed}
    (output / "quality_gates.json").write_bytes(canonical_bytes(quality))
    report_path = output / "REPORT.md"
    base_report = report(
        load_json(root, f"{OUTPUT_REL}/final_performance_contract.json"),
        load_json(root, f"{OUTPUT_REL}/historical_integrity.json"),
    )
    lines = "\n".join(
        f"- `{row['id']}`: PASS — {row['observed_output']}" for row in observed
    )
    report_path.write_text(f"{base_report}\n## Quality gates\n\n{lines}\n", encoding="utf-8")
    manifest_path = output / "experiment_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["artifact_sha256"]["quality_gates.json"] = digest(
        output / "quality_gates.json"
    )
    manifest["report_sha256"] = digest(report_path)
    manifest_path.write_bytes(canonical_bytes(manifest))


if __name__ == "__main__":
    materialize(Path(__file__).resolve().parents[2])
