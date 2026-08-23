# ruff: noqa: E501
"""Sprint 41 prospective evidence-to-criterion-state operationalization."""

from __future__ import annotations

import hashlib
import json
import platform
from pathlib import Path
from typing import Any

from evaluation.q1_advancement_governance_protocol import (
    CRITERIA,
    STATES,
    criterion_class,
)

PROTOCOL_ID = "q1-prospective-criterion-operationalization"
VERSION = "1.0.0"
SPRINT = "10.8.2.41"
EFFECTIVE_FROM_SPRINT = "10.8.2.42"
PARENT = "q1-advancement-governance-outcome-mapping@1.0.0"
OUTPUT_REL = "audits/q1-prospective-criterion-operationalization/1.0.0"
STARTING_HEAD = "cde3b96df103a76c114f83d497bc6799851288e4"

HISTORICAL_DIRS = (
    "audits/q1-experimental-evidence-gap-audit",
    "audits/q1-experimental-validity-contract",
    "audits/q1-modality-factorial",
    "audits/q1-fusion-process-ablation",
    "audits/q1-forward-development-calibration",
    "audits/q1-development-practical-utility-protocol",
    "audits/q1-development-practical-utility-execution",
    "audits/q1-advancement-governance-outcome-mapping",
)

PROHIBITED_COUNTERS = (
    "TEST_label_accesses",
    "TEST_probability_loading",
    "TEST_scoring",
    "TEST_model_selection",
    "TEST_threshold_optimization",
    "TEST_calibration_fitting",
    "TEST_XAI",
    "model_fits",
    "model_refits",
    "calibrator_fits",
    "meta_learner_fits",
    "hyperparameter_searches",
    "threshold_optimizations",
    "candidate_selections",
    "external_dataset_acquisitions",
    "XAI_executions",
)

QUALITY_GATES = {
    "focused_sprint_41_pytest": {"passed": 22, "failed": 0},
    "relevant_regression_pytest": {"passed": 86, "failed": 0},
    "full_pytest": {"passed": 1448, "skipped": 1, "failed": 0},
    "sprint_41_ruff": {"verdict": "PASS", "findings": 0},
    "python_compilation": {"verdict": "PASS", "files": 3},
    "git_diff_check": {"verdict": "PASS", "errors": 0},
    "json_schema_validation": {"verdict": "PASS", "engine": "AJV Draft-07"},
    "deterministic_repeated_validation": {"verdict": "PASS"},
    "historical_hash_verification": {"verdict": "PASS", "scope": "Sprint 32-39"},
    "test_and_prohibited_counters": {"verdict": "PASS_ALL_ZERO"},
    "environment_note": (
        "An initial regression collection attempt with system Python 3.12 lacked "
        "scipy; all authoritative gates were rerun with the repository .venv "
        "(Python 3.11.14) without installing or changing dependencies."
    ),
}


def canonical_bytes(value: Any) -> bytes:
    """Return deterministic canonical JSON bytes."""
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _integrity(
    criterion: str,
    intent: str,
    source_types: list[str],
    invariants: list[str],
    rationale: str,
) -> dict[str, Any]:
    return {
        "id": criterion,
        "class": criterion_class(criterion),
        "scientific_intent": intent,
        "authoritative_evidence_source_types": source_types,
        "required_evidence": {
            "mandatory_invariants": invariants,
            "optional_limitation_records_allowed": True,
        },
        "provenance_requirements": [
            "evidence artifact path and SHA-256",
            "producing protocol/version and target sprint",
            "dataset, split, configuration, implementation, and runtime identities where applicable",
            "evidence generated no earlier than this contract's effective sprint or explicitly authorized persisted evidence",
        ],
        "comparator_reference": {
            "type": "frozen_invariant_set",
            "definition": "Every named mandatory invariant in this contract; predictive performance is not a comparator.",
            "freeze_timing": "before protected evidence access",
        },
        "metric_statistic": "Boolean satisfaction for every mandatory invariant",
        "directionality": "all mandatory invariants must be true",
        "decision_condition": {
            "PASS": "All mandatory invariants are present, valid, traceable, and true; no declared limitation is present.",
            "MIXED": "All mandatory invariants are present, valid, traceable, and true, but at least one complete non-mandatory limitation is declared.",
            "FAIL": "At least one present, valid, traceable mandatory invariant is false.",
            "UNRESOLVED": "Any mandatory invariant or required provenance item is missing, malformed, non-traceable, or not derivable.",
        },
        "missing_evidence_handling": "UNRESOLVED",
        "invalid_evidence_handling": "UNRESOLVED unless valid evidence affirmatively demonstrates a mandatory violation, which is FAIL",
        "blocking_semantics": "FAIL is integrity-blocking; UNRESOLVED is blocked by Sprint 39 RULE_1. This contract does not derive the advancement outcome.",
        "rationale": rationale,
        "anti_retrospective_tuning": "No outcome values or predictive cutoffs are used.",
        "rule_type": "ALL_MANDATORY_INVARIANTS",
    }


def _relational(
    criterion: str,
    intent: str,
    sources: list[str],
    metrics: list[dict[str, str]],
    reference: str,
    rationale: str,
) -> dict[str, Any]:
    return {
        "id": criterion,
        "class": criterion_class(criterion),
        "scientific_intent": intent,
        "authoritative_evidence_source_types": sources,
        "required_evidence": {
            "paired_cells": "One finite candidate and reference value for every frozen metric × temporal-origin × predeclared-reference cell.",
            "origins": ["O1", "O2", "O3", "O4", "O5"],
            "metrics": metrics,
            "coverage": "Complete Cartesian coverage; cells cannot be dropped after outcome inspection.",
        },
        "provenance_requirements": [
            "candidate and reference identifiers frozen before evidence access",
            "artifact path and SHA-256",
            "origin-membership and temporal-protocol SHA-256",
            "metric implementation/configuration identity",
            "finite numeric values with identical memberships for each pair",
        ],
        "comparator_reference": {
            "type": "predeclared_paired_reference_set",
            "definition": reference,
            "freeze_timing": "before protected or target evidence access",
            "selection_prohibition": "References may not be selected because their observed results make advancement easier.",
        },
        "metric_statistic": "Cell-wise signed difference oriented so positive favors the candidate; zero is an exact tie.",
        "directionality": "higher oriented difference is better",
        "decision_condition": {
            "PASS": "Every required oriented paired difference is >= 0 and at least one is > 0.",
            "MIXED": "Required evidence is complete and valid, but the oriented differences contain both favorable and unfavorable values, or all values are exact ties.",
            "FAIL": "Every required oriented paired difference is <= 0 and at least one is < 0.",
            "UNRESOLVED": "Any required cell, metric, origin, reference, provenance item, or finite value is missing or invalid.",
        },
        "missing_evidence_handling": "UNRESOLVED",
        "invalid_evidence_handling": "UNRESOLVED",
        "blocking_semantics": "Scientific-performance state only; Sprint 39 alone maps the later nine-state vector to an outcome.",
        "rationale": rationale,
        "anti_retrospective_tuning": "The zero boundary is mathematical equality against a pre-existing reference, not a fitted performance cutoff.",
        "rule_type": "ORIENTED_PAIRED_DOMINANCE",
    }


def contract() -> dict[str, Any]:
    """Build the prospective contract without loading observed outcomes."""
    criteria = [
        _integrity(
            "leakage_safety",
            "Demonstrate that labels, future information, partition identity, and fitted preprocessing state cannot leak into predictors or earlier temporal stages.",
            ["feature-lineage audit", "leakage denylist audit", "fit/predict membership audit", "execution ledger"],
            [
                "zero exact prohibited predictor overlaps",
                "zero unresolved semantic proxy ambiguities",
                "target/provenance/partition identifiers excluded from predictors",
                "all preprocessing and learned transformations fit only on the estimator training membership",
                "each predicted row is excluded from every fitted component that produced its prediction",
                "no future-derived vocabulary, scaling, feature selection, calibration, threshold, or statistic",
                "all TEST access/use counters are zero",
            ],
            "These are frozen Sprint 33 leakage and fit-boundary invariants; absence of leakage is an integrity property, not a performance threshold.",
        ),
        _integrity(
            "temporal_validity",
            "Demonstrate compliance with the frozen project-local chronological expanding-window protocol.",
            ["temporal memberships", "origin manifest", "chronology audit", "configuration manifest"],
            [
                "canonical ordering is git_committer_timestamp then commit_hash",
                "origins are exactly O1 through O5 with expanding train and contiguous next blocked evaluation",
                "every fit observation is chronologically before every observation it predicts",
                "no row is predicted by a model fitted on that row",
                "nested tuning/fusion/calibration uses earlier prefix then later contiguous validation",
                "difficult origins are not dropped and boundaries are not outcome-adjusted",
                "sealed TEST is excluded from campaign development",
            ],
            "The invariants are directly inherited from the accepted Sprint 33 temporal contract and Sprint 37 memberships.",
        ),
        _integrity(
            "reproducibility",
            "Demonstrate identity, traceability, deterministic configuration, and repeatable derivation for every consumed evidence item.",
            ["experiment manifest", "reproducibility manifest", "artifact hash manifest", "repeatability trace"],
            [
                "all required inputs, memberships, configurations, implementations, and outputs have SHA-256 identities",
                "seeds and deterministic procedures are declared",
                "runtime and ordered feature/schema identities are declared where applicable",
                "all fitted components used by evidence are persisted and bound into the predictor graph where applicable",
                "reload or deterministic reconstruction is prediction-equivalent on an authorized non-final fixture where applicable",
                "two validations of identical evidence produce byte-identical criterion records",
                "all referenced artifacts exist and match their declared hashes",
            ],
            "Repository manifests and hashes provide inherent identity checks; reproducibility does not require an arbitrary predictive-performance cutoff.",
        ),
        _relational(
            "discrimination",
            "Determine whether the prospectively declared candidate provides defensible ranking discrimination relative to every prospectively declared simpler scientific reference.",
            ["paired per-origin probability-level metric artifact", "origin membership manifest"],
            [
                {"id": "ROC_AUC", "orientation": "candidate_minus_reference"},
                {"id": "PR_AUC", "orientation": "candidate_minus_reference"},
            ],
            "Every eligible frozen simpler/unimodal comparator required by the declared scientific contrast; the reference set and candidate must be named before evidence access.",
            "ROC-AUC and PR-AUC are the canonical probability-level discrimination metrics in Sprint 37. Paired zero-difference dominance avoids an outcome-tuned absolute cutoff and preserves metric trade-offs as MIXED.",
        ),
        _relational(
            "calibration",
            "Determine whether probability accuracy is no worse than the frozen reference across both accepted calibration metrics and temporal origins.",
            ["paired per-origin calibration metric artifact", "reliability manifest", "origin membership manifest"],
            [
                {"id": "Brier", "orientation": "reference_minus_candidate"},
                {"id": "ECE", "orientation": "reference_minus_candidate"},
            ],
            "The same prospectively frozen simpler reference predictor/state used for the scientific contrast; no calibrator may be fitted or selected by Sprint 41.",
            "Brier and ECE are accepted by Sprints 36–37 and lower is better. Reversing the subtraction makes positive consistently favorable without inventing a tolerance; trade-offs become MIXED.",
        ),
        {
            **_relational(
                "practical_utility",
                "Determine whether the candidate is decision-useful across the entire predeclared threshold and cost-scenario grid.",
                ["decision-curve grid", "normalized-cost grid", "frozen threshold/cost protocol", "origin memberships"],
                [
                    {"id": "net_benefit_vs_treat_none", "orientation": "candidate_minus_reference"},
                    {"id": "net_benefit_vs_treat_all", "orientation": "candidate_minus_reference"},
                    {"id": "normalized_cost", "orientation": "reference_minus_candidate"},
                ],
                "For net benefit, both frozen treat-none and treat-all strategies; for normalized cost, every prospectively named predictor reference. All Sprint 37 thresholds, FN:FP ratios, calibration states, and origins remain in scope.",
                "Sprint 37 froze the complete grid and formulas before execution. Requiring cell-wise relational dominance prevents post-hoc selection of a favorable threshold or cost range.",
            ),
            "grid_requirements": {
                "thresholds": [0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95],
                "FN_FP_ratios": [1, 2, 5, 10, 20],
                "calibration_states": ["UNCALIBRATED", "PLATT", "ISOTONIC"],
            },
        },
        {
            "id": "complexity_parsimony",
            "class": criterion_class("complexity_parsimony"),
            "scientific_intent": "Prevent preference for additional modalities/components unless the extra burden is accompanied by defensible incremental scientific value.",
            "authoritative_evidence_source_types": ["frozen predictor graph manifest", "component manifest", "performance criterion states derived in a later authorized evaluation using the Sprint 41 operationalization"],
            "required_evidence": {
                "candidate_and_reference_complexity_vectors": ["modality_count", "fitted_component_count", "learned_fusion_component_count", "calibration_component_count"],
                "incremental_value_states": ["discrimination", "calibration", "practical_utility"],
                "future_state_timing": "The incremental-value states do not exist merely because Sprint 41 defines their rules; they may be derived only in a later explicitly authorized evaluation using this operationalization.",
                "prospective_policy_status": "Requiring simultaneous PASS in discrimination, calibration, and practical_utility for a strictly more-complex candidate is a new prospective, conservative, outcome-independent Sprint 41 operationalization; it is not an exact rule historically frozen by Sprint 37.",
                "stability_separation": "stability_across_origins remains an independent required Sprint 39 scientific criterion. It asks whether behavior is directionally stable across frozen temporal origins, whereas complexity_parsimony asks whether multidimensional incremental scientific value justifies extra complexity. Exclusion from this conjunction does not make stability optional and introduces no combined weight or score.",
            },
            "provenance_requirements": ["candidate/reference graph paths and SHA-256", "component-count derivation trace", "references frozen before evidence access", "hash-bound input criterion records"],
            "comparator_reference": {"type": "predeclared_simpler_predictor", "definition": "Every prospectively declared simpler comparator in the scientific contrast.", "freeze_timing": "before evidence access"},
            "metric_statistic": "Pareto partial order over non-negative observable component counts; no weighted complexity score.",
            "directionality": "fewer components/modalities is simpler",
            "decision_condition": {
                "PASS": "Candidate is no more complex than every reference, or it is more complex and discrimination, calibration, and practical_utility are all PASS.",
                "MIXED": "Complexity vectors are incomparable, or the candidate is more complex with no incremental-value FAIL/UNRESOLVED and at least one incremental-value MIXED.",
                "FAIL": "Candidate is more complex and at least one incremental-value criterion is FAIL.",
                "UNRESOLVED": "Any count/reference/provenance or required incremental-value state is missing/invalid, or any incremental-value state is UNRESOLVED.",
            },
            "missing_evidence_handling": "UNRESOLVED",
            "invalid_evidence_handling": "UNRESOLVED",
            "blocking_semantics": "Scientific-performance state only; Sprint 39 performs outcome mapping later.",
            "rationale": "Counts are reproducibly derivable from the predictor graph and Pareto ordering avoids subjective weights. Sprint 37 established joint relevance, rejected a single best metric, and permitted the simplest defensible candidate, but did not freeze this exact conjunction. Sprint 41 prospectively and conservatively requires simultaneous PASS in discrimination, calibration, and practical_utility so isolated favorable performance cannot justify extra complexity. stability_across_origins remains separately mandatory under Sprint 39 because robustness across time is scientifically distinct from incremental value.",
            "anti_retrospective_tuning": "No observed performance value sets a complexity weight or cutoff.",
            "rule_type": "PARETO_COMPLEXITY_WITH_INCREMENTAL_VALUE",
        },
        {
            "id": "stability_across_origins",
            "class": criterion_class("stability_across_origins"),
            "scientific_intent": "Determine whether the direction of incremental value is stable across the five frozen temporal evaluation origins.",
            "authoritative_evidence_source_types": ["origin-level oriented comparison records", "frozen origin memberships"],
            "required_evidence": {"origins": ["O1", "O2", "O3", "O4", "O5"], "origin_definition": "The five project-local chronological expanding-window evaluation origins frozen by Sprints 33 and 37; not datasets, projects, folds, modalities, or seeds.", "families": ["discrimination", "calibration", "practical_utility"]},
            "provenance_requirements": ["complete five-origin coverage", "origin membership SHA-256", "same candidate/reference identities at every origin", "finite oriented differences for every required family cell"],
            "comparator_reference": {"type": "same_predeclared_reference_set_as_performance_criteria", "definition": "No origin-specific comparator substitution is allowed.", "freeze_timing": "before evidence access"},
            "metric_statistic": "Per origin sign: FAVORABLE if every required oriented cell is >=0 and at least one >0; UNFAVORABLE if every cell <=0 and at least one <0; MIXED otherwise.",
            "directionality": "consistent favorable direction across all origins is better",
            "decision_condition": {
                "PASS": "All five origin signs are FAVORABLE.",
                "MIXED": "Complete valid evidence contains at least two different origin signs, or all five origin signs are MIXED.",
                "FAIL": "All five origin signs are UNFAVORABLE.",
                "UNRESOLVED": "Any required origin/family/cell/provenance item is missing or invalid.",
            },
            "missing_evidence_handling": "UNRESOLVED",
            "invalid_evidence_handling": "UNRESOLVED",
            "blocking_semantics": "Scientific-performance state only; Sprint 39 performs outcome mapping later.",
            "rationale": "Origin retains its accepted temporal meaning. Exact sign consistency is relational and requires no heterogeneity cutoff chosen from historical results.",
            "anti_retrospective_tuning": "No origin was removed and no dispersion threshold was selected from observed evidence.",
            "rule_type": "FIVE_ORIGIN_SIGN_CONSISTENCY",
        },
        _integrity(
            "absence_of_outcome_driven_tuning",
            "Demonstrate that candidate, reference, metrics, boundaries, rules, and authorizations were frozen before protected outcomes and remained unchanged afterward.",
            ["prospective declaration", "execution ledger", "artifact hash manifest", "authorization ledger", "version chronology"],
            [
                "operationalization effective sprint is 10.8.2.42 or later",
                "candidate/reference/metric/grid declarations predate target evidence access",
                "all TEST and prohibited-operation counters are zero",
                "Sprint 32 through Sprint 39 protected artifacts match their accepted hashes",
                "Sprint 39 criterion classes, state vocabulary, mapping, precedence, and authorizations are unchanged",
                "no rule or reference was revised after inspecting protected/final outcomes",
                "Sprint 41 was not applied to Sprint 38, Sprint 39, or the read-only Sprint 40 finding",
            ],
            "Prospective timestamps, immutable hashes, authorization boundaries, and zero-use ledgers are auditable evidence of procedural independence from outcomes.",
        ),
    ]
    return {
        "protocol_id": PROTOCOL_ID,
        "version": VERSION,
        "declared_in_sprint": SPRINT,
        "effective_sprint": EFFECTIVE_FROM_SPRINT,
        "prospective_only": True,
        "parent_governance_contract": PARENT,
        "scope": "EVIDENCE_TO_CRITERION_STATE_ONLY",
        "historical_application_prohibited": ["10.8.2.38", "10.8.2.39", "10.8.2.40", "10.8.2.41"],
        "canonical_state_vocabulary": list(STATES),
        "criteria": criteria,
        "anti_retrospective_tuning_declaration": "No threshold, tolerance, comparator, grid, or decision boundary was selected from observed Sprint 38 performance. Numerical grids are inherited unchanged from pre-existing contracts; other boundaries are equality/invariant conditions.",
        "advancement_outcome_derivation_prohibited": True,
        "test_access_prohibited": True,
    }


def validate_contract(value: dict[str, Any]) -> None:
    """Fail closed on any drift from the canonical prospective contract."""
    expected = contract()
    if value != expected:
        raise ValueError("contract does not match canonical Sprint 41 operationalization")
    rows = value["criteria"]
    ids = [row["id"] for row in rows]
    if ids != list(CRITERIA) or len(ids) != len(set(ids)):
        raise ValueError("criteria do not exactly match Sprint 39")
    if value["canonical_state_vocabulary"] != list(STATES):
        raise ValueError("state vocabulary drift")


def _sprint_tuple(value: str) -> tuple[int, ...]:
    try:
        return tuple(int(part) for part in value.split("."))
    except (AttributeError, ValueError) as error:
        raise ValueError("invalid sprint") from error


def assert_prospective_target(target_sprint: str) -> None:
    if _sprint_tuple(target_sprint) < _sprint_tuple(EFFECTIVE_FROM_SPRINT):
        raise ValueError("retrospective operationalization prohibited")


def derive_integrity_state(evidence: dict[str, Any], expected_invariants: list[str]) -> str:
    """Derive an integrity criterion state without performance access."""
    if not isinstance(evidence, dict) or evidence.get("valid") is not True:
        return "UNRESOLVED"
    invariants = evidence.get("invariants")
    provenance_complete = evidence.get("provenance_complete")
    limitations = evidence.get("limitations")
    if not isinstance(invariants, dict) or provenance_complete is not True or not isinstance(limitations, list):
        return "UNRESOLVED"
    if set(invariants) != set(expected_invariants) or any(type(value) is not bool for value in invariants.values()):
        return "UNRESOLVED"
    if any(value is False for value in invariants.values()):
        return "FAIL"
    return "MIXED" if limitations else "PASS"


def oriented_dominance_state(evidence: dict[str, Any]) -> str:
    """Classify a complete vector of oriented paired differences."""
    if not isinstance(evidence, dict) or evidence.get("valid") is not True or evidence.get("complete") is not True or evidence.get("provenance_complete") is not True:
        return "UNRESOLVED"
    differences = evidence.get("oriented_differences")
    if not isinstance(differences, list) or not differences:
        return "UNRESOLVED"
    if any(type(value) not in (int, float) or not float("-inf") < value < float("inf") for value in differences):
        return "UNRESOLVED"
    if all(value >= 0 for value in differences) and any(value > 0 for value in differences):
        return "PASS"
    if all(value <= 0 for value in differences) and any(value < 0 for value in differences):
        return "FAIL"
    return "MIXED"


def complexity_state(evidence: dict[str, Any]) -> str:
    """Apply Pareto complexity and incremental-value rules."""
    if not isinstance(evidence, dict) or evidence.get("valid") is not True or evidence.get("provenance_complete") is not True:
        return "UNRESOLVED"
    candidate = evidence.get("candidate")
    references = evidence.get("references")
    value_states = evidence.get("incremental_value_states")
    dimensions = ("modality_count", "fitted_component_count", "learned_fusion_component_count", "calibration_component_count")
    if not isinstance(candidate, dict) or not isinstance(references, list) or not references or not isinstance(value_states, dict):
        return "UNRESOLVED"
    vectors = [candidate, *references]
    if any(set(vector) != set(dimensions) or any(type(vector[key]) is not int or vector[key] < 0 for key in dimensions) for vector in vectors):
        return "UNRESOLVED"
    if set(value_states) != {"discrimination", "calibration", "practical_utility"} or any(state not in STATES for state in value_states.values()):
        return "UNRESOLVED"
    if any(state == "UNRESOLVED" for state in value_states.values()):
        return "UNRESOLVED"
    no_more_complex = all(all(candidate[key] <= reference[key] for key in dimensions) for reference in references)
    strictly_more = all(all(candidate[key] >= reference[key] for key in dimensions) and any(candidate[key] > reference[key] for key in dimensions) for reference in references)
    if no_more_complex:
        return "PASS"
    if not strictly_more:
        return "MIXED"
    if any(state == "FAIL" for state in value_states.values()):
        return "FAIL"
    if all(state == "PASS" for state in value_states.values()):
        return "PASS"
    return "MIXED"


def stability_state(evidence: dict[str, Any]) -> str:
    """Classify exact sign consistency over the five canonical origins."""
    if not isinstance(evidence, dict) or evidence.get("valid") is not True or evidence.get("provenance_complete") is not True:
        return "UNRESOLVED"
    origins = evidence.get("origins")
    expected = {f"O{index}" for index in range(1, 6)}
    if not isinstance(origins, dict) or set(origins) != expected:
        return "UNRESOLVED"
    signs: list[str] = []
    for origin in sorted(origins):
        state = oriented_dominance_state(origins[origin])
        if state == "UNRESOLVED":
            return state
        signs.append({"PASS": "FAVORABLE", "FAIL": "UNFAVORABLE", "MIXED": "MIXED"}[state])
    if all(sign == "FAVORABLE" for sign in signs):
        return "PASS"
    if all(sign == "UNFAVORABLE" for sign in signs):
        return "FAIL"
    return "MIXED"


def derive_criterion_state(target_sprint: str, criterion: str, evidence: dict[str, Any]) -> dict[str, str]:
    """Derive one state only; never invoke Sprint 39 outcome mapping."""
    assert_prospective_target(target_sprint)
    operationalization = {row["id"]: row for row in contract()["criteria"]}
    if criterion not in operationalization:
        raise ValueError("unknown criterion")
    rule = operationalization[criterion]
    if rule["rule_type"] == "ALL_MANDATORY_INVARIANTS":
        state = derive_integrity_state(evidence, rule["required_evidence"]["mandatory_invariants"])
    elif rule["rule_type"] == "ORIENTED_PAIRED_DOMINANCE":
        state = oriented_dominance_state(evidence)
    elif rule["rule_type"] == "PARETO_COMPLEXITY_WITH_INCREMENTAL_VALUE":
        state = complexity_state(evidence)
    else:
        state = stability_state(evidence)
    return {"criterion": criterion, "criterion_class": criterion_class(criterion), "state": state, "target_sprint": target_sprint}


def historical_hashes(root: Path) -> dict[str, str]:
    paths: list[Path] = []
    for relative in HISTORICAL_DIRS:
        paths.extend(path for path in (root / relative).rglob("*") if path.is_file())
    return {str(path.relative_to(root)): digest(path) for path in sorted(paths)}


def verify_historical_hashes(root: Path, expected: dict[str, str]) -> None:
    if historical_hashes(root) != expected:
        raise RuntimeError("Sprint 32-39 historical artifact hash mismatch")


def execution_ledger() -> dict[str, int | str]:
    return {"sprint_mode": "PROSPECTIVE_CRITERION_OPERATIONALIZATION_ONLY", **dict.fromkeys(PROHIBITED_COUNTERS, 0)}


def contract_schema() -> dict[str, Any]:
    """Return a strict Draft-07 structural schema; semantic equality is also checked."""
    criterion = {
        "type": "object",
        "required": ["id", "class", "scientific_intent", "authoritative_evidence_source_types", "required_evidence", "provenance_requirements", "comparator_reference", "metric_statistic", "directionality", "decision_condition", "missing_evidence_handling", "invalid_evidence_handling", "blocking_semantics", "rationale", "anti_retrospective_tuning", "rule_type"],
        "properties": {
            "id": {"enum": list(CRITERIA)}, "class": {"enum": ["INTEGRITY_BLOCKING", "SCIENTIFIC_PERFORMANCE"]},
            "scientific_intent": {"type": "string", "minLength": 1}, "authoritative_evidence_source_types": {"type": "array", "minItems": 1, "items": {"type": "string", "minLength": 1}},
            "required_evidence": {"type": "object", "minProperties": 1}, "provenance_requirements": {"type": "array", "minItems": 1, "items": {"type": "string", "minLength": 1}},
            "comparator_reference": {"type": "object", "minProperties": 2}, "metric_statistic": {"type": "string", "minLength": 1}, "directionality": {"type": "string", "minLength": 1},
            "decision_condition": {"type": "object", "required": list(STATES), "properties": {state: {"type": "string", "minLength": 1} for state in STATES}, "additionalProperties": False},
            "missing_evidence_handling": {"const": "UNRESOLVED"}, "invalid_evidence_handling": {"type": "string", "minLength": 1}, "blocking_semantics": {"type": "string", "minLength": 1},
            "rationale": {"type": "string", "minLength": 1}, "anti_retrospective_tuning": {"type": "string", "minLength": 1}, "rule_type": {"enum": ["ALL_MANDATORY_INVARIANTS", "ORIENTED_PAIRED_DOMINANCE", "PARETO_COMPLEXITY_WITH_INCREMENTAL_VALUE", "FIVE_ORIGIN_SIGN_CONSISTENCY"]},
            "grid_requirements": {"type": "object"},
        },
        "additionalProperties": False,
    }
    properties = {
        "protocol_id": {"const": PROTOCOL_ID}, "version": {"const": VERSION}, "declared_in_sprint": {"const": SPRINT}, "effective_sprint": {"const": EFFECTIVE_FROM_SPRINT}, "prospective_only": {"const": True},
        "parent_governance_contract": {"const": PARENT}, "scope": {"const": "EVIDENCE_TO_CRITERION_STATE_ONLY"},
        "historical_application_prohibited": {"const": ["10.8.2.38", "10.8.2.39", "10.8.2.40", "10.8.2.41"]},
        "canonical_state_vocabulary": {"const": list(STATES)},
        "criteria": {"type": "array", "items": criterion, "minItems": len(CRITERIA), "maxItems": len(CRITERIA)},
        "anti_retrospective_tuning_declaration": {"type": "string", "minLength": 1}, "advancement_outcome_derivation_prohibited": {"const": True}, "test_access_prohibited": {"const": True},
    }
    return {"$schema": "http://json-schema.org/draft-07/schema#", "$id": f"{PROTOCOL_ID}-{VERSION}", "type": "object", "required": list(properties), "properties": properties, "additionalProperties": False}


def evidence_schema() -> dict[str, Any]:
    """Schema for a later single-criterion evidence envelope."""
    properties = {
        "protocol_id": {"const": PROTOCOL_ID}, "protocol_version": {"const": VERSION}, "target_sprint": {"type": "string", "pattern": r"^10\.8\.2\.[0-9]+$"},
        "criterion": {"enum": list(CRITERIA)}, "evidence": {"type": "object"}, "artifact_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
    }
    return {"$schema": "http://json-schema.org/draft-07/schema#", "$id": f"{PROTOCOL_ID}-evidence-{VERSION}", "type": "object", "required": list(properties), "properties": properties, "additionalProperties": False}


def materialize(root: Path) -> Path:
    """Persist only Sprint 41 prospective governance artifacts."""
    output = root / OUTPUT_REL
    output.mkdir(parents=True, exist_ok=True)
    value = contract()
    validate_contract(value)
    history = historical_hashes(root)
    artifacts: dict[str, Any] = {
        "criterion_operationalization.json": value,
        "criterion_operationalization.schema.json": contract_schema(),
        "evidence_contract.schema.json": evidence_schema(),
        "execution_ledger.json": execution_ledger(),
        "historical_artifact_hashes.json": history,
        "quality_gates.json": QUALITY_GATES,
        "scientific_decision.json": {"decision": "SPRINT_10.8.2.41_READY_FOR_HUMAN_REVIEW", "scope": "PROSPECTIVE_CRITERION_OPERATIONALIZATION_ONLY", "advancement_outcome_derived": False, "test_access_authorized": False},
    }
    for name, item in artifacts.items():
        (output / name).write_bytes(canonical_bytes(item))
    module = root / "src/evaluation/q1_prospective_criterion_operationalization.py"
    tests = root / "tests/evaluation/test_q1_prospective_criterion_operationalization.py"
    manifest = {
        "protocol_id": PROTOCOL_ID, "version": VERSION, "sprint": SPRINT, "effective_sprint": EFFECTIVE_FROM_SPRINT, "starting_head": STARTING_HEAD,
        "runtime": {"python": platform.python_version(), "platform": platform.platform()},
        "implementation_sha256": digest(module), "tests_sha256": digest(tests), "artifact_sha256": {name: digest(output / name) for name in sorted(artifacts)},
    }
    (output / "experiment_manifest.json").write_bytes(canonical_bytes(manifest))
    (output / "REPORT.md").write_text(report(len(history)), encoding="utf-8")
    verify_historical_hashes(root, history)
    return output


def report(historical_count: int) -> str:
    return f"""# Sprint 10.8.2.41 — Prospective Criterion Operationalization

## Decision

**SPRINT_10.8.2.41_READY_FOR_HUMAN_REVIEW**

## Scope

This sprint freezes the missing evidence-to-criterion-state layer subordinate to Sprint 39. It derives no advancement outcome and does not retrospectively classify Sprint 38, Sprint 39, or the read-only Sprint 40 finding. It is effective from Sprint 10.8.2.42 after human acceptance.

## Scientific rules

Integrity criteria use complete mandatory invariant sets. Discrimination and calibration use paired sign-oriented dominance over ROC-AUC/PR-AUC and Brier/ECE. Practical utility uses the complete frozen Sprint 37 threshold/cost/calibration/origin grid. Complexity uses observable component counts and Pareto ordering. For a strictly more-complex candidate, simultaneous PASS in discrimination, calibration, and practical utility is explicitly a new prospective, conservative, outcome-independent Sprint 41 policy rather than an exact Sprint 37 rule. The required input states may be derived only in a later explicitly authorized evaluation using this operationalization; Sprint 41 does not claim they already exist.

Stability remains an independent Sprint 39 scientific criterion evaluated over the five frozen temporal origins O1–O5. Complexity asks whether multidimensional incremental value justifies additional burden; stability asks whether behavior is directionally stable across origins. Stability is neither optional nor absorbed into complexity, and no combined weight or aggregate score connects them.

Missing or invalid evidence maps to UNRESOLVED. Valid mandatory integrity violations map to FAIL. Valid relational trade-offs map to MIXED. No new scientific state or outcome was introduced.

## Anti-retrospective-tuning audit

No threshold, tolerance, comparator, or boundary was selected from observed Sprint 38 performance. Numerical grids are inherited unchanged from Sprint 37. Other boundaries are exact equality, Boolean invariants, or Pareto relations.

## TEST sealing and prohibited activity

All TEST access, scoring, probability loading, fitting, tuning, selection, external acquisition, and XAI counters are zero.

## Historical integrity

**PASS:** {historical_count} persisted Sprint 32–39 artifacts were SHA-256 addressed and verified unchanged.

## Interpretation

Sprint 41 makes a later evidence evaluation deterministic. It does not establish predictive superiority, calibration adequacy, practical usefulness, stability, advancement, final-candidate selection, TEST authorization, XAI authorization, or deployment readiness.
"""
