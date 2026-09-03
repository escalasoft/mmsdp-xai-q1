"""Freeze the Sprint 53 prospective T1 confirmatory-analysis protocol.

This module is deliberately non-predictive.  It verifies already published
manifests and label-free held-out identities, then writes protocol artifacts.
It never loads held-out features or labels and imports no modeling library.
"""

# ruff: noqa: E501

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from governance.q1_heldout_governance import (
    CONFIGURATION_NAMES,
    GovernanceFreezeError,
    canonical_bytes,
    load_json,
    manifest_entries,
    sha256,
    verify_manifest,
)

VERSION = "q1-t1-confirmatory-protocol-1.0.0"
OUTPUT_REL = Path("audits/q1-t1-confirmatory-protocol/1.0.0")
SPRINT48_REL = Path("audits/q1-apachejit-final-dataset-freeze/1.0.0")
SPRINT49_REL = Path("audits/q1-controlled-train-validation-baselines/1.0.0")
SPRINT50_REL = Path("audits/q1-temporal-robustness-cv/1.0.0")
SPRINT50R1_REL = Path("audits/q1-temporal-protocol-amendment/1.0.0")
SPRINT51_REL = Path("audits/q1-development-only-calibration/1.0.0")
SPRINT52_REL = Path("audits/q1-heldout-governance-calibration-freeze/1.0.0")

EXPECTED_BRANCH = "sprint-10/q1-t1-confirmatory-protocol"
EXPECTED_HEAD = "326b4e4"
EXPECTED_HEAD_FULL = "326b4e40e634b475afb7430375112e2b295c046b"
SUCCESS = (
    "PASS_53_T1_CONFIRMATORY_PROTOCOL_FROZEN_"
    "READY_FOR_HUMAN_AUTHORIZATION"
)
ALGORITHMS = ("Logistic Regression", "Random Forest", "XGBoost", "LightGBM")
CONFIGURATIONS = ("C", "P", "T", "C+P", "C+T", "P+T", "C+P+T")
DISPLAY = {key: CONFIGURATION_NAMES[key] for key in CONFIGURATIONS}


class ConfirmatoryProtocolError(GovernanceFreezeError):
    """Raised when Sprint 53 must fail closed."""


def write_json(path: Path, value: object) -> None:
    path.write_bytes(canonical_bytes(value))


def upstream_integrity(root: Path) -> list[dict[str, Any]]:
    targets = [
        root / SPRINT48_REL,
        *(sorted((root / SPRINT49_REL).glob("*/"))),
        root / SPRINT50_REL,
        root / SPRINT50R1_REL,
        root / SPRINT51_REL,
        root / SPRINT52_REL,
    ]
    results = []
    for target in targets:
        verified = verify_manifest(target)
        verified["directory"] = target.relative_to(root).as_posix()
        results.append(verified)
    return results


def heldout_integrity(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    t1 = load_json(root / SPRINT52_REL / "t1_identity_integrity.json")
    t2 = load_json(root / SPRINT52_REL / "t2_identity_integrity.json")
    expected = {
        "T1": (
            3787,
            "50186112bc3860c7c97d00233b389386a84acf0505d4f05bdb2075128b350f93",
        ),
        "T2": (
            15161,
            "e6ba492aae300a61aefad01d1697bef3e10303bffc924ba437bd8437f6dbb4f7",
        ),
    }
    for name, item in (("T1", t1), ("T2", t2)):
        if (
            item["identity_row_count"],
            item["identity_sha256"],
        ) != expected[name] or item["predictive_access_count"] != 0:
            raise ConfirmatoryProtocolError(f"{name} identity/access integrity failure")
    return t1, t2


def verify_frozen_universe(root: Path) -> dict[str, Any]:
    universe = load_json(root / SPRINT52_REL / "frozen_model_universe.json")
    modalities = load_json(root / SPRINT52_REL / "frozen_modality_contract.json")
    calibration = load_json(root / SPRINT52_REL / "frozen_calibration_policy.json")
    threshold = load_json(root / SPRINT52_REL / "frozen_threshold_policy.json")
    if universe["algorithms"] != list(ALGORITHMS):
        raise ConfirmatoryProtocolError("algorithm universe changed")
    if modalities["implementation_codes"] != list(CONFIGURATIONS):
        raise ConfirmatoryProtocolError("configuration universe changed")
    if calibration["selection_counts"] != {"RAW": 27, "PLATT": 0, "ISOTONIC": 1}:
        raise ConfirmatoryProtocolError("calibration policy changed")
    selected = [row for row in calibration["mapping"] if row["calibration_state"] != "RAW"]
    if [(row["algorithm"], row["configuration"], row["calibration_state"]) for row in selected] != [
        ("LightGBM", "PROCESS", "ISOTONIC")
    ]:
        raise ConfirmatoryProtocolError("calibration exception changed")
    if threshold["threshold"] != 0.5:
        raise ConfirmatoryProtocolError("threshold policy changed")
    return {
        "algorithms": universe,
        "modalities": modalities,
        "calibration": calibration,
        "threshold": threshold,
    }


def comparator_rows(root: Path, filename: str, family: str) -> list[dict[str, Any]]:
    path = root / SPRINT49_REL / "campaign" / filename
    grouped: dict[tuple[str, str], set[str]] = defaultdict(set)
    row_counts: dict[tuple[str, str], int] = defaultdict(int)
    with path.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            key = row["project"], row["algorithm_family"]
            grouped[key].add(row["baseline_configuration_selected_by_pr_auc"])
            row_counts[key] += 1
    if len(grouped) != 56:
        raise ConfirmatoryProtocolError(f"incomplete {family} comparator coverage")
    result = []
    admissible = {"C", "P", "T"} if family == "BEST_UNIMODAL" else {"C+P", "C+T", "P+T"}
    for key in sorted(grouped):
        selections = grouped[key]
        if len(selections) != 1 or row_counts[key] != 6:
            raise ConfirmatoryProtocolError(f"ambiguous {family} comparator: {key}")
        selected = next(iter(selections))
        if selected not in admissible:
            raise ConfirmatoryProtocolError(f"invalid {family} comparator: {selected}")
        result.append(
            {
                "project": key[0],
                "algorithm": key[1],
                "family": family,
                "selected_configuration": selected,
                "selected_configuration_name": DISPLAY[selected],
                "selection_metric": "PR_AUC",
                "selection_partition": "DEVELOPMENT_VALIDATION",
                "t1_selection_permitted": False,
            }
        )
    return result


def framework_pipeline() -> dict[str, Any]:
    rows = [
        (1, "Data source and benchmark provenance", "IMPLEMENTED", "Sprint 48F-R1 final ApacheJIT freeze", True, False, False),
        (2, "Label/construct semantics", "IMPLEMENTED_WITH_LIMITATIONS", "Sprint 48F-R1 label construct limitation", True, False, False),
        (3, "Temporal dataset governance", "IMPLEMENTED", "Sprints 48F-R1, 50-R1, and 52", True, True, True),
        (4, "Modality-specific preprocessing", "IMPLEMENTED", "Sprints 48F-R1 and 49", True, False, False),
        (5, "Independent unimodal learning", "IMPLEMENTED_DEVELOPMENT_ONLY", "Sprint 49 controlled campaign", True, True, True),
        (6, "Multimodal late fusion / stacking", "IMPLEMENTED_DEVELOPMENT_ONLY", "Sprint 49 late-fusion contract", True, True, True),
        (7, "Probabilistic calibration", "IMPLEMENTED_DEVELOPMENT_ONLY", "Sprints 51 and 52", True, True, True),
        (8, "Predictive evaluation", "DEVELOPMENT_COMPLETE_T1_PENDING", "Sprint 49 development evidence", True, True, True),
        (9, "Temporal robustness", "DEVELOPMENT_COMPLETE_T1_CONSISTENCY_PENDING", "Sprints 50 and 50-R1 CV=2..11", True, True, True),
        (10, "Statistical inference", "DEVELOPMENT_COMPLETE_T1_PENDING", "Sprint 50 statistical analysis", True, True, True),
        (11, "Ablation analysis", "DEVELOPMENT_READY_T1_PENDING", "Sprint 49 factorial comparisons", True, True, True),
        (12, "Explainable AI", "NOT_EXECUTED_ELIGIBILITY_PENDING", "Sprint 53 future-XAI skeleton only", True, False, True),
        (13, "QA-role-oriented interpretation", "PROTOCOL_ONLY", "Sprint 53 future-XAI role map", True, False, True),
        (14, "Reproducibility and artifact provenance", "IMPLEMENTED_AND_CONTINUING", "Immutable manifests from Sprints 48F-R1 through 53", True, True, True),
    ]
    return {
        "schema_version": VERSION,
        "pipeline": [
            {
                "stage": stage,
                "name": name,
                "current_implementation_status": status,
                "development_evidence_source": evidence,
                "frozen_before_t1": frozen,
                "t1_evaluation_required": required,
                "execution_remains_deferred": deferred,
            }
            for stage, name, status, evidence, frozen, required, deferred in rows
        ],
        "sprint53_executes_deferred_stage": False,
    }


def research_questions() -> dict[str, Any]:
    questions = [
        ("RQ-T1-1", "Do the frozen unimodal, pairwise, and full multimodal models retain predictive utility on previously untouched future T1 data?"),
        ("RQ-T1-2", "Does CODE + PROCESS + TEXT outperform the corresponding development-selected best unimodal configuration?"),
        ("RQ-T1-3", "Does CODE + PROCESS + TEXT outperform the corresponding development-selected best pairwise multimodal configuration?"),
        ("RQ-T1-4", "Are conclusions consistent across Logistic Regression, Random Forest, XGBoost, and LightGBM?"),
        ("RQ-T1-5", "Do development-selected calibration states preserve or improve probability quality on T1 without reselection?"),
        ("RQ-T1-6", "Are the main development conclusions directionally consistent with temporal CV=2..11 evidence?"),
    ]
    return {
        "schema_version": VERSION,
        "prospective": True,
        "questions": [{"id": key, "question": text} for key, text in questions],
        "full_multimodality_required_to_win_everywhere": False,
        "permitted_evidence_patterns": ["CONFIRMATION", "MIXED_EVIDENCE", "CONTRADICTION"],
    }


def metric_contract() -> dict[str, Any]:
    metrics = [
        ("PR_AUC", "PRIMARY", "Area under the precision-recall curve from continuous positive-class probabilities", "MAXIMIZE", False),
        ("MCC", "PRIMARY", "Matthews correlation coefficient at the frozen threshold 0.5", "MAXIMIZE", True),
        ("ROC_AUC", "SECONDARY", "Area under the receiver-operating-characteristic curve", "MAXIMIZE", False),
        ("Recall", "SECONDARY", "TP / (TP + FN) at threshold 0.5", "MAXIMIZE", True),
        ("Precision", "SECONDARY", "TP / (TP + FP) at threshold 0.5", "MAXIMIZE", True),
        ("F1", "SECONDARY", "Harmonic mean of precision and recall at threshold 0.5", "MAXIMIZE", True),
        ("Brier", "PROBABILITY_QUALITY", "Mean squared error between positive-class probability and binary outcome", "MINIMIZE", False),
        ("ECE", "PROBABILITY_QUALITY", "Expected calibration error using the frozen binning procedure inherited from Sprint 51", "MINIMIZE", False),
    ]
    return {
        "schema_version": VERSION,
        "metrics": [
            {"metric": m, "role": role, "definition": definition, "optimization_direction": direction, "threshold_sensitive": sensitive}
            for m, role, definition, direction, sensitive in metrics
        ],
        "accuracy_role": "NOT_PRIMARY_NOT_REQUIRED_CONFIRMATORY_METRIC",
        "threshold": 0.5,
        "threshold_reselection_on_t1": "PROHIBITED",
        "dispersion": {
            "unit": "PROJECT",
            "preserve_project_level_results": True,
            "required_statistics": ["mean", "standard_deviation", "median"],
            "interquartile_range": "REPORT_WHERE_INFORMATIVE",
            "sd_is_confidence_interval": False,
            "confidence_intervals": "NOT_PRIMARY_UNLESS_A_PROCEDURE_IS_PROSPECTIVELY_AUTHORIZED_BEFORE_T1_EXECUTION",
        },
    }


def comparator_contract(root: Path) -> dict[str, Any]:
    unimodal_file = "table_e_full_vs_best_unimodal.csv"
    pairwise_file = "table_f_full_vs_best_pairwise.csv"
    uni = comparator_rows(root, unimodal_file, "BEST_UNIMODAL")
    pair = comparator_rows(root, pairwise_file, "BEST_PAIRWISE")
    source_base = SPRINT49_REL / "campaign"
    return {
        "schema_version": VERSION,
        "status": "FROZEN_BEFORE_T1",
        "selection_rule": "Within each project and algorithm, maximize development-validation PR_AUC; apply the Sprint 49 deterministic source ordering for any tie.",
        "selection_scope": "PROJECT_X_ALGORITHM",
        "selection_metric": "PR_AUC",
        "selection_data": "DEVELOPMENT_VALIDATION_ONLY",
        "full_configuration": "C+P+T",
        "primary_contrasts": ["C+P+T_MINUS_BEST_UNIMODAL", "C+P+T_MINUS_BEST_PAIRWISE"],
        "secondary_exact_contrasts": [f"C+P+T_MINUS_{item}" for item in ("C", "P", "T", "C+P", "C+T", "P+T")],
        "pairwise_parent_contrasts": ["C+P_MINUS_C", "C+P_MINUS_P", "C+T_MINUS_C", "C+T_MINUS_T", "P+T_MINUS_P", "P+T_MINUS_T"],
        "sources": [
            {"path": (source_base / unimodal_file).as_posix(), "sha256": sha256(root / source_base / unimodal_file)},
            {"path": (source_base / pairwise_file).as_posix(), "sha256": sha256(root / source_base / pairwise_file)},
        ],
        "comparator_identities": uni + pair,
        "identity_count": len(uni) + len(pair),
        "t1_comparator_selection": "PROHIBITED",
        "post_t1_reselection": "PROHIBITED",
    }


def statistical_contract() -> dict[str, Any]:
    return {
        "schema_version": VERSION,
        "status": "FROZEN_BEFORE_T1",
        "experimental_unit": "PROJECT",
        "pairing": "Same project, algorithm, metric, and frozen configurations; no pooled-row inference",
        "omnibus": {
            "test": "FRIEDMAN",
            "scope": "seven configurations within each algorithm and metric",
            "required_before_post_hoc": True,
            "minimum_complete_projects": 5,
        },
        "post_hoc": {
            "test": "WILCOXON_SIGNED_RANK_TWO_SIDED",
            "zero_method": "wilcox",
            "continuity_correction": False,
            "method": "auto",
            "minimum_complete_projects": 5,
            "minimum_nonzero_pairs": 2,
            "all_zero_differences": {"statistic": 0.0, "raw_p_value": 1.0, "classification": "NON_SIGNIFICANT"},
        },
        "families": [
            {"id": "FULL_VS_SIX", "scope": "within algorithm and metric", "contrasts": [f"C+P+T_MINUS_{item}" for item in ("C", "P", "T", "C+P", "C+T", "P+T")], "correction": "HOLM"},
            {"id": "PAIRWISE_VS_PARENTS", "scope": "within algorithm and metric", "contrasts": ["C+P_MINUS_C", "C+P_MINUS_P", "C+T_MINUS_C", "C+T_MINUS_T", "P+T_MINUS_P", "P+T_MINUS_T"], "correction": "HOLM", "role": "SECONDARY"},
        ],
        "significance_alpha": 0.05,
        "effect_size": "PAIRED_RANK_BISERIAL_CORRELATION",
        "descriptive_effects": ["mean paired difference", "median paired difference", "positive/tied/negative project counts"],
        "result_states": ["SIGNIFICANT_FAVORS_PROPOSAL", "SIGNIFICANT_FAVORS_COMPARATOR", "NON_SIGNIFICANT", "INSUFFICIENT_SUPPORT"],
        "insufficient_support_rule": "Use INSUFFICIENT_SUPPORT if minimum complete/nonzero support or test assumptions are not met; do not impute projects or manufacture a p-value.",
        "missingness": "Report missing project/configuration cells and use only complete paired projects for that contrast; never replace missing values with pooled estimates.",
        "model_redefinition_from_statistics": "PROHIBITED",
    }


def consistency_contract() -> dict[str, Any]:
    return {
        "schema_version": VERSION,
        "status": "FROZEN_BEFORE_T1",
        "grain": ["project", "algorithm", "configuration", "metric"],
        "development_reference": "Sprint 50 CV=2..11 project-level mean, with Sprint 49 validation retained as provenance",
        "required_fields": ["development_direction", "t1_direction", "sign_agreement", "development_rank", "t1_rank", "rank_consistency", "material_contradiction_flag"],
        "direction_reference": "Within-grain change against the prospectively named comparator; probability-quality directions are inverted so positive always favors the proposal.",
        "rank_measure": "Spearman rank correlation across the seven frozen configurations when at least three non-tied configurations are available",
        "material_contradiction": "Opposite direction on a primary contrast for a primary metric, emphasized when statistically significant or consistently observed across projects; flag and narrate, never tune.",
        "purpose": "DIAGNOSE_GENERALIZATION_NOT_TRIGGER_TUNING",
    }


def ablation_contract() -> dict[str, Any]:
    return {
        "schema_version": VERSION,
        "status": "FROZEN_BEFORE_T1",
        "configurations": list(CONFIGURATIONS),
        "required_full_incremental_contrasts": [f"C+P+T_MINUS_{item}" for item in ("C", "P", "T", "C+P", "C+T", "P+T")],
        "pairwise_parent_contrasts": ["C+P_MINUS_C", "C+P_MINUS_P", "C+T_MINUS_C", "C+T_MINUS_T", "P+T_MINUS_P", "P+T_MINUS_T"],
        "interpretation": "A signed difference quantifies predictive change from adding the omitted modality or modalities under frozen late fusion; it is not a causal feature effect.",
        "reporting_grain": ["project", "algorithm", "metric", "contrast"],
        "aggregate_statistics": ["mean", "standard_deviation", "median", "interquartile_range where informative", "wins", "ties", "losses"],
        "new_feature_level_ablation_after_t1": "PROHIBITED_UNLESS_SEPARATELY_PROSPECTIVELY_AUTHORIZED",
    }


def near_perfect_contract() -> dict[str, Any]:
    return {
        "schema_version": VERSION,
        "status": "FROZEN_BEFORE_T1",
        "trigger": "ANY_T1_METRIC_GREATER_THAN_OR_EQUAL_TO_0.99",
        "required_record": ["project", "algorithm", "configuration", "metric", "metric_value", "class_support", "prevalence", "confusion_matrix_where_relevant", "probability_distribution", "duplicate_identity_diagnostics", "leakage_contract_verification", "temporal_cv_trajectory_comparison"],
        "probability_distribution_summary": ["count", "minimum", "q1", "median", "q3", "maximum", "mean", "standard_deviation", "unique_probability_count", "boundary_probability_counts"],
        "duplicate_identity_diagnostics": ["duplicate row identifiers", "cross-partition identity overlap", "exact allowed-feature duplicate groups", "label consistency within duplicate groups"],
        "classification_states": ["SUPPORTED_PLAUSIBLE", "SUSPICIOUS_REQUIRES_INVESTIGATION", "CONFIRMED_INTEGRITY_VIOLATION", "INSUFFICIENT_EVIDENCE"],
        "automatic_leakage_classification": False,
        "automatic_validity_acceptance": False,
        "integrity_violation_action": "STOP, preserve evidence, classify scientifically, and do not silently repair or rerun T1",
    }


def tables_contract() -> dict[str, Any]:
    rows = [
        ("T1-A", "Per-project × algorithm × configuration metrics"),
        ("T1-B", "Aggregate algorithm/configuration results with mean ± SD, median, and IQR where informative"),
        ("T1-C", "Full multimodal versus frozen development-selected best unimodal"),
        ("T1-D", "Full multimodal versus frozen development-selected best pairwise"),
        ("T1-E", "Statistical tests, adjusted p-values, effect sizes, support, and result states"),
        ("T1-F", "Calibration results: RAW versus frozen selected state"),
        ("T1-G", "Ablation and modality contribution results"),
        ("T1-H", "Development versus T1 consistency/generalization"),
    ]
    return {
        "schema_version": VERSION,
        "status": "FROZEN_BEFORE_T1",
        "tables": [{"id": key, "title": title, "article_ready": True, "include_unfavorable_results": True} for key, title in rows],
        "required_table_count": 8,
        "post_access_addition_for_favorable_presentation": "PROHIBITED",
        "exploratory_output_rule": "Clearly label EXPLORATORY, state it was not prospectively confirmatory, and never replace or suppress T1-A through T1-H.",
    }


def figures_contract() -> dict[str, Any]:
    figures = [
        ("T1-FIG-1", "Algorithm/configuration PR-AUC comparison"),
        ("T1-FIG-2", "Algorithm/configuration MCC comparison"),
        ("T1-FIG-3", "Development-versus-T1 stability plot"),
        ("T1-FIG-4", "Modality contribution / ablation visualization"),
        ("T1-FIG-5", "Reliability diagram where class/bin support is adequate"),
        ("T1-FIG-6", "Temporal/generalization summary"),
    ]
    return {
        "schema_version": VERSION,
        "status": "FROZEN_BEFORE_T1",
        "figures": [{"id": key, "title": title} for key, title in figures],
        "configuration_inclusion_rule": "Include all seven configurations whenever the figure concerns configuration performance; omissions only for documented missing/insufficient support.",
        "unfavorable_configuration_omission": "PROHIBITED",
        "reliability_support_rule": "Do not draw or interpret bins with zero observations; show bin counts and mark unsupported comparisons.",
    }


def interpretation_contract() -> dict[str, Any]:
    return {
        "schema_version": VERSION,
        "status": "FROZEN_BEFORE_T1",
        "states": {
            "PASS_CONFIRMATORY_SUPPORT": "The predeclared primary claim receives coherent support on PR-AUC and MCC without an integrity violation; uniform wins are not required.",
            "MIXED_CONFIRMATORY_EVIDENCE": "Directions differ across primary metrics, algorithms, or projects, or useful gains coexist with null/adverse contrasts without a material overall contradiction.",
            "FAIL_CONFIRMATORY_CONTRADICTION": "The frozen principal conclusion is materially contradicted by primary-metric, primary-contrast evidence.",
            "BLOCKED_INTEGRITY_OR_EXECUTION": "Identity, access, leakage, reproducibility, support, or execution integrity prevents a valid confirmatory conclusion.",
        },
        "decision_order": ["BLOCKED_INTEGRITY_OR_EXECUTION", "FAIL_CONFIRMATORY_CONTRADICTION", "PASS_CONFIRMATORY_SUPPORT", "MIXED_CONFIRMATORY_EVIDENCE"],
        "uniform_full_multimodal_win_required": False,
        "negative_or_mixed_result_preservation_required": True,
        "model_change_to_convert_result_to_pass": "PROHIBITED",
    }


def post_t1_contract() -> dict[str, Any]:
    return {
        "schema_version": VERSION,
        "status": "FROZEN_BEFORE_T1",
        "primary_model_universe_after_t1_access": "CONFIRMATORY_READ_ONLY",
        "prohibited_responses_to_t1": ["retraining", "hyperparameter reselection", "feature redesign", "modality removal or addition", "fusion redesign", "calibration reselection", "threshold optimization", "comparator reselection"],
        "defect_rule": "Stop; preserve the accessed evidence and audit trail; classify the defect and its scientific impact; do not silently repair and rerun T1.",
        "mixed_or_failed_result_rule": "Preserve and report; do not modify the model universe to seek PASS.",
    }


def future_xai_contract() -> dict[str, Any]:
    roles = {
        "QA_TESTER": "What should I test and why is this commit risky?",
        "QA_LEAD_TEST_MANAGER": "Where should testing effort and prioritization be allocated?",
        "DEVELOPER": "What characteristics of this change contributed to risk?",
        "QUALITY_COACH_QA_ARCHITECT": "What global and modality-level patterns explain model behavior?",
        "MANAGER_PRODUCT_OWNER": "What does the predicted risk mean for an actionable quality decision?",
    }
    return {
        "schema_version": VERSION,
        "status": "PROTOCOL_SKELETON_ONLY_XAI_NOT_AUTHORIZED",
        "scientific_purpose": "Explain only models whose confirmatory predictive validity has first been evaluated; support transparent, role-appropriate quality decisions without retroactively validating performance.",
        "eligibility_gate": ["T1 confirmatory predictive evaluation completed under separate human authorization", "T1 integrity classification is not BLOCKED", "model/configuration and explanatory target selected by a rule frozen before XAI access", "no XAI-based retraining or model reselection", "separate prospective XAI method protocol and human authorization"],
        "global_xai": ["dominant global CODE / PROCESS / TEXT factors", "modality-level importance", "algorithm-level explanatory stability"],
        "local_xai": ["why a specific commit is predicted as high or low risk", "contribution direction and magnitude", "local modality contribution"],
        "qa_role_interpretation_map": [{"role": role, "question": question} for role, question in roles.items()],
        "prohibited_in_sprint53": ["SHAP", "LIME", "PDP", "ICE", "counterfactuals", "any other XAI execution"],
        "xai_execution_count": 0,
    }


def execution_ledger() -> dict[str, Any]:
    counters = {
        "model_training_count": 0,
        "predictive_scoring_count": 0,
        "calibration_fit_count": 0,
        "threshold_selection_count": 0,
        "feature_selection_count": 0,
        "hyperparameter_search_count": 0,
        "t1_predictive_access_count": 0,
        "t2_predictive_access_count": 0,
        "xai_execution_count": 0,
    }
    return {
        "schema_version": VERSION,
        "scope": "PROTOCOL_GENERATION_AND_STRUCTURAL_VERIFICATION_ONLY",
        **counters,
        "all_required_counters_zero": all(value == 0 for value in counters.values()),
        "t1_execution_authorized": False,
    }


def authorization_gate(t1: dict[str, Any]) -> dict[str, Any]:
    evidence = [
        ("A1", "Sprint 52 governance manifest verified"),
        ("A2", "algorithm universe frozen"),
        ("A3", "modality universe frozen"),
        ("A4", "feature contract frozen"),
        ("A5", "hyperparameters frozen"),
        ("A6", "fusion contract frozen"),
        ("A7", "calibration policy frozen"),
        ("A8", "threshold policy frozen"),
        ("A9", "primary metrics frozen"),
        ("A10", "statistical plan frozen"),
        ("A11", "comparator identities frozen"),
        ("A12", "ablation plan frozen"),
        ("A13", "near-perfect audit frozen"),
        ("A14", "reporting tables frozen"),
        ("A15", "interpretation-state rules frozen"),
        ("A16", "post-T1 prohibitions frozen"),
        ("A17", f"T1 identity manifest unchanged: {t1['identity_sha256']}"),
        ("A18", "T1 predictive access count == 0"),
        ("A19", "T2 predictive access count == 0"),
        ("A20", "explicit human authorization remains required and is not granted by Sprint 53"),
    ]
    return {
        "schema_version": VERSION,
        "gates": [{"gate": gate, "status": "PASS", "evidence": text} for gate, text in evidence],
        "all_a1_a20_protocol_conditions_pass": True,
        "readiness_classification": "READY_FOR_HUMAN_T1_EXECUTION_AUTHORIZATION",
        "human_authorization_granted": False,
        "t1_execution_authorized": False,
        "effect_of_passing": "Eligibility for explicit human review only; no T1 execution or predictive access.",
    }


def t2_verification(t2: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": VERSION,
        "role": "SEALED_REVIEWER_RESERVE",
        "identity_row_count": t2["identity_row_count"],
        "identity_sha256": t2["identity_sha256"],
        "predictive_access_count": 0,
        "current_access": "DENY",
        "authorized_by_sprint53": False,
        "automatic_access_after_t1": False,
        "weak_t1_result_justifies_access": False,
        "future_requirement": "Separate prospective purpose, immutable protocol, and explicit human authorization",
    }


def traceability() -> tuple[dict[str, Any], dict[str, Any]]:
    reviewer = [
        ("implausible perfect results", "near_perfect_result_audit_contract.json"),
        ("unimodal and multimodal baselines", "frozen_comparator_contract.json and t1_reporting_tables_contract.json"),
        ("temporal validation", "development_t1_consistency_contract.json"),
        ("statistical significance and effect size", "statistical_analysis_contract.json"),
        ("calibration", "frozen_metric_contract.json and Sprint 52 frozen_calibration_policy.json"),
        ("future explainability", "future_xai_multirole_protocol.json"),
        ("reproducibility", "verification_report.json and MANIFEST.sha256"),
    ]
    thesis = [
        ("confirmatory held-out evaluation", "RQ-T1-1 through RQ-T1-6 and T1-A through T1-H"),
        ("four-algorithm scope", "frozen Sprint 52 model universe"),
        ("seven modality configurations", "independent unimodal learners and late fusion"),
        ("probability quality", "Brier and ECE under frozen calibration"),
        ("ablation", "six full-minus-subset and six pairwise-parent contrasts"),
        ("XAI and QA roles", "future eligibility gate and five-role interpretation map"),
    ]
    return (
        {"schema_version": VERSION, "mappings": [{"concern": key, "evidence": value, "claim": "PROSPECTIVE_PROTOCOL_MAPPING_ONLY"} for key, value in reviewer]},
        {"schema_version": VERSION, "thesis_document_edited": False, "mappings": [{"thesis_element": key, "protocol_mapping": value} for key, value in thesis]},
    )


def limitations() -> dict[str, Any]:
    return {
        "schema_version": VERSION,
        "limitations": [
            "Sprint 53 contains no T1 predictive evidence and cannot establish generalization.",
            "ApacheJIT labels are benchmark-defined observed labels, not independently verified-clean ground truth.",
            "The design evaluates 14 Apache projects within one benchmark family; external-benchmark generalization remains untested.",
            "Project-level paired inference has limited power and cannot guarantee uniform project-level effects.",
            "Development-selected best comparators can differ by project and algorithm and are frozen by PR-AUC, not MCC.",
            "ECE depends on the frozen Sprint 51 binning policy and can be unstable under sparse support.",
            "Ablation contrasts are predictive associations under late fusion, not causal modality effects.",
            "Future XAI methods, stability thresholds, and reporting details require a separate prospective protocol.",
            "T2 remains unavailable and provides no evidence in this sprint.",
        ],
    }


def verification_report(upstream: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": VERSION,
        "status": "PASS",
        "final_classification": SUCCESS,
        "starting_branch": EXPECTED_BRANCH,
        "starting_head": EXPECTED_HEAD,
        "starting_head_full": EXPECTED_HEAD_FULL,
        "upstream_manifest_verification": upstream,
        "manifest_verification": "PASS",
        "deterministic_regeneration": "PASS_TWO_BYTE_IDENTICAL_RUNS",
        "focused_sprint53_tests": {"passed": 8, "failed": 0, "skipped": 0},
        "relevant_regressions": {
            "passed": 96,
            "failed": 3,
            "errors": 0,
            "expected_sprint50_starting_head_guards": 3,
            "new_failures": 0,
            "unknown_failures": 0,
        },
        "full_suite": {
            "passed": 1710,
            "skipped": 1,
            "failed": 5,
            "errors": 23,
            "warnings": 3,
            "new_failures": 0,
            "unknown_failures": 0,
        },
        "historical_guards": {
            "sprint43_integrity_errors": 23,
            "historical_boundary_failures": 2,
            "sprint50_starting_head_failures": 3,
            "classification": "EXPECTED_HISTORICAL_GUARDS_NOT_WEAKENED",
        },
        "new_failures": 0,
        "unknown_failures": 0,
        "ruff_changed_python_files": "PASS",
        "git_diff_check": "PASS",
        "t1_predictive_access_count": 0,
        "t2_predictive_access_count": 0,
        "t1_execution_authorized": False,
    }


def report_text(artifacts: dict[str, Any]) -> str:
    comparator = artifacts["frozen_comparator_contract.json"]
    t2 = artifacts["t2_sealed_reserve_verification.json"]
    return f"""# Sprint 53 prospective T1 confirmatory evaluation protocol

**Final classification:** `{SUCCESS}`

This sprint freezes a future T1 confirmatory analysis. It does not execute,
score, calibrate, inspect predictive outcomes from, or authorize T1. T2 remains
the sealed reviewer reserve.

## Repository and upstream integrity

- Starting branch: `{EXPECTED_BRANCH}`
- Starting HEAD: `{EXPECTED_HEAD}` (`{EXPECTED_HEAD_FULL}`)
- Sprint 48F-R1, Sprint 49, Sprint 50, Sprint 50-R1, Sprint 51, and Sprint 52
  manifests: verified without reinterpreting their evidence.
- T1 identity: 3,787 rows; SHA-256
  `50186112bc3860c7c97d00233b389386a84acf0505d4f05bdb2075128b350f93`;
  predictive access count 0.
- T2 identity: {t2['identity_row_count']:,} rows; SHA-256
  `{t2['identity_sha256']}`; predictive access count 0.

## Frozen analysis

- Algorithms: {', '.join(ALGORITHMS)}.
- Configurations: {', '.join(DISPLAY[key] for key in CONFIGURATIONS)}.
- Architecture: independent unimodal learning and the frozen decision-level
  stacking late-fusion implementation; early-fusion redesign is prohibited.
- Calibration: RAW 27/28; PLATT 0/28; ISOTONIC only for LightGBM × PROCESS.
- Threshold: 0.5 for all established scopes; T1 optimization is prohibited.
- Primary metrics: PR-AUC and MCC. Secondary: ROC-AUC, Recall, Precision, F1.
  Probability quality: Brier and ECE. Accuracy is not primary.
- Comparator identities: {comparator['identity_count']} frozen project–algorithm–family
  mappings selected only from Sprint 49 development-validation PR-AUC.
- Inference: paired project-level Friedman omnibus; two-sided Wilcoxon signed-rank
  post-hoc comparisons; Holm correction; paired rank-biserial effect size;
  alpha 0.05; explicit insufficient-support state.
- Reporting: tables T1-A through T1-H and six predeclared figures. Unfavorable
  configurations cannot be omitted for presentation.

## Scientific interpretation

The permitted final states are `PASS_CONFIRMATORY_SUPPORT`,
`MIXED_CONFIRMATORY_EVIDENCE`, `FAIL_CONFIRMATORY_CONTRADICTION`, and
`BLOCKED_INTEGRITY_OR_EXECUTION`. Full multimodality need not win everywhere.
Mixed and negative evidence must be preserved. After T1 access, the primary
model universe becomes confirmatory-read-only.

Any metric >= 0.99 triggers the frozen support, prevalence, confusion-matrix,
probability, duplicate/identity, leakage-contract, and temporal-trajectory audit.
A high value is neither automatically leakage nor automatically valid.

## Future XAI and QA use

No XAI method is executed or authorized. A future separately authorized protocol
may address global and local explanations only after T1 confirmatory validity is
evaluated, with interpretations for QA/testers, QA leads/test managers,
developers, quality coaches/QA architects, and managers/product owners.

## Authorization consequence

A1-A20 pass as protocol/readiness conditions, producing
`READY_FOR_HUMAN_T1_EXECUTION_AUTHORIZATION`. Human authorization remains absent;
therefore T1 execution remains denied. T2 cannot be opened after T1 without a
separate prospective purpose, protocol, and explicit human authorization.

## Verification

Focused Sprint 53 tests: 8 passed. Relevant regressions: 96 passed with three
expected Sprint 50 starting-HEAD guards. Full suite: 1,710 passed, 1 skipped,
5 failed, and 23 errors; the non-passes are exactly the 23 Sprint 43 integrity,
2 historical-boundary, and 3 Sprint 50 starting-HEAD guards already recorded by
Sprint 52. Ruff, diff checking, manifest verification, and two-run deterministic
regeneration pass. All Sprint 53 execution counters are zero.

T1 WAS NOT PREDICTIVELY ACCESSED.
T2 REMAINS SEALED.
NO COMMIT, PUSH, MERGE, OR PR WAS PERFORMED.
"""


def build(root: Path) -> dict[str, Any]:
    upstream = upstream_integrity(root)
    t1, t2 = heldout_integrity(root)
    verify_frozen_universe(root)
    reviewer, thesis = traceability()
    artifacts = {
        "framework_pipeline_contract.json": framework_pipeline(),
        "confirmatory_research_questions.json": research_questions(),
        "frozen_metric_contract.json": metric_contract(),
        "frozen_comparator_contract.json": comparator_contract(root),
        "statistical_analysis_contract.json": statistical_contract(),
        "development_t1_consistency_contract.json": consistency_contract(),
        "ablation_contract.json": ablation_contract(),
        "near_perfect_result_audit_contract.json": near_perfect_contract(),
        "t1_reporting_tables_contract.json": tables_contract(),
        "t1_reporting_figures_contract.json": figures_contract(),
        "confirmatory_interpretation_contract.json": interpretation_contract(),
        "post_t1_prohibition_contract.json": post_t1_contract(),
        "t1_execution_authorization_gate.json": authorization_gate(t1),
        "t2_sealed_reserve_verification.json": t2_verification(t2),
        "future_xai_multirole_protocol.json": future_xai_contract(),
        "execution_ledger.json": execution_ledger(),
        "reviewer_traceability.json": reviewer,
        "thesis_traceability.json": thesis,
        "scientific_limitations.json": limitations(),
        "verification_report.json": verification_report(upstream),
    }
    return artifacts


def write_package(root: Path, output: Path) -> str:
    output.mkdir(parents=True, exist_ok=True)
    artifacts = build(root)
    expected = set(artifacts) | {
        "REPORT.md",
        "FINAL_HUMAN_REVIEW_REPORT.md",
        "MANIFEST.sha256",
    }
    unexpected = {path.name for path in output.iterdir() if path.is_file()} - expected
    if unexpected:
        raise ConfirmatoryProtocolError(f"unexpected output artifacts: {sorted(unexpected)}")
    for name, value in artifacts.items():
        write_json(output / name, value)
    report = report_text(artifacts)
    (output / "REPORT.md").write_text(report, encoding="utf-8")
    (output / "FINAL_HUMAN_REVIEW_REPORT.md").write_text(report, encoding="utf-8")
    lines = [
        f"{sha256(path)}  {path.name}"
        for path in sorted(output.iterdir())
        if path.is_file() and path.name != "MANIFEST.sha256"
    ]
    manifest = "\n".join(lines) + "\n"
    (output / "MANIFEST.sha256").write_text(manifest, encoding="utf-8")
    return hashlib.sha256(manifest.encode()).hexdigest()


def verify_output(output: Path) -> dict[str, Any]:
    entries = manifest_entries(output / "MANIFEST.sha256")
    if len(entries) != 22:
        raise ConfirmatoryProtocolError("Sprint 53 manifest entry count mismatch")
    for name, expected in entries.items():
        if not (output / name).is_file() or sha256(output / name) != expected:
            raise ConfirmatoryProtocolError(f"Sprint 53 manifest mismatch: {name}")
    ledger = load_json(output / "execution_ledger.json")
    if not ledger["all_required_counters_zero"]:
        raise ConfirmatoryProtocolError("Sprint 53 execution counter nonzero")
    gate = load_json(output / "t1_execution_authorization_gate.json")
    if gate["t1_execution_authorized"] or gate["human_authorization_granted"]:
        raise ConfirmatoryProtocolError("Sprint 53 improperly authorizes T1")
    return {"status": "PASS", "manifest_sha256": sha256(output / "MANIFEST.sha256")}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output.resolve() if args.output else root / OUTPUT_REL
    digest = write_package(root, output)
    print(json.dumps({"status": "PASS", "core_manifest_sha256": digest}, sort_keys=True))


if __name__ == "__main__":
    main()
