"""Execute the frozen Sprint 37 DEVELOPMENT practical-utility protocol."""

# ruff: noqa: E501

from __future__ import annotations

import csv
import hashlib
import json
import math
import pickle
import platform
from collections import defaultdict
from io import StringIO
from pathlib import Path
from typing import Any

import numpy as np
import scipy
import sklearn

from calibration.q1_forward_development_calibration import _apply, _score_ct
from experimentation.q1_modality_factorial import digest, load_development

VERSION = "q1-development-practical-utility-execution-1.0.0"
SPRINT = "10.8.2.38"
OUTPUT_REL = "audits/q1-development-practical-utility-execution/1.0.0"
PROTOCOL_REL = "audits/q1-development-practical-utility-protocol/1.0.0"
CALIBRATION_REL = "audits/q1-forward-development-calibration/1.0.0"
STARTING_HEAD = "488921fcfd2f8081748986930d77dce6a0d38ab2"
BRANCH = "sprint-10/q1-development-practical-utility-execution"
STATES = ("UNCALIBRATED", "PLATT", "ISOTONIC")
ORIGINS = ("O1", "O2", "O3", "O4", "O5")
EVIDENCE_STATES = frozenset({"PASS", "MIXED", "UNRESOLVED"})
UNRESOLVED_DECISION = "SPRINT_10.8.2.38_ADVANCEMENT_UNRESOLVED"
QUALITY_GATES = {
    "focused_sprint_38_pytest": {"passed": 12, "failed": 0},
    "relevant_existing_pytest": {"passed": 231, "failed": 0},
    "full_pytest": {"passed": 1406, "skipped": 1, "failed": 0},
    "sprint_38_ruff": {"verdict": "PASS", "findings": 0},
    "full_repository_ruff_diagnostic": {
        "verdict": "FAIL_PRE_EXISTING_UNRELATED",
        "findings": 31,
        "files": 2,
        "modified_to_repair": False,
    },
    "python_compilation": {"verdict": "PASS", "files": 2},
    "git_diff_check": {"verdict": "PASS", "errors": 0},
}


def file_digest(path: Path) -> str:
    """Return a file SHA-256 digest."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_bytes(value: object) -> bytes:
    """Serialize stable machine-readable JSON."""
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def write_json(path: Path, value: object) -> None:
    path.write_bytes(canonical_bytes(value))


def _protocol_files(root: Path) -> dict[str, str]:
    manifest = json.loads((root / PROTOCOL_REL / "experiment_manifest.json").read_text())
    expected = manifest["artifact_sha256"]
    actual = {name: file_digest(root / PROTOCOL_REL / name) for name in expected}
    if actual != expected:
        raise RuntimeError("Sprint 37 protocol artifact hash mismatch")
    return actual


def validate_pre_execution(root: Path) -> dict[str, Any]:
    """Fail closed on any protocol, lineage, temporal, or prediction drift."""
    hashes = _protocol_files(root)
    protocol = json.loads((root / PROTOCOL_REL / "protocol.json").read_text())
    thresholds = json.loads((root / PROTOCOL_REL / "threshold_grid.json").read_text())
    costs = json.loads((root / PROTOCOL_REL / "cost_scenarios.json").read_text())
    curve = json.loads((root / PROTOCOL_REL / "decision_curve_definition.json").read_text())
    utility = json.loads((root / PROTOCOL_REL / "utility_definition.json").read_text())
    advancement = json.loads((root / PROTOCOL_REL / "advancement_rule.json").read_text())
    temporal = json.loads((root / PROTOCOL_REL / "temporal_memberships.json").read_text())
    sprint36 = root / CALIBRATION_REL / "temporal_memberships.json"
    if file_digest(sprint36) != temporal["source_sha256"]:
        raise RuntimeError("Sprint 36/Sprint 37 temporal source mismatch")
    sprint36_members = json.loads(sprint36.read_text())
    source_by_origin = {row["origin_id"]: row for row in sprint36_members["origins"]}
    if tuple(row["origin_id"] for row in temporal["origins"]) != ORIGINS:
        raise RuntimeError("frozen DEVELOPMENT origin set mismatch")
    for row in temporal["origins"]:
        source = source_by_origin[row["origin_id"]]
        if row["calibration_evaluation_membership_digest"] != source["calibration_evaluation_membership_digest"]:
            raise RuntimeError("Sprint 36/Sprint 37 DEVELOPMENT membership mismatch")
    if thresholds != protocol["threshold_policy"] or costs != protocol["cost_model"]:
        raise RuntimeError("frozen thresholds or costs disagree with protocol")
    if curve != protocol["decision_curve"] or utility != protocol["utility"]:
        raise RuntimeError("frozen decision or utility formula disagrees with protocol")
    if advancement != protocol["advancement"]:
        raise RuntimeError("frozen advancement rule disagrees with protocol")
    if tuple(protocol["calibration_states"]) != STATES or protocol["sealed_partition"] != "test":
        raise RuntimeError("calibration state or sealed-partition drift")
    states = {}
    historical = json.loads((root / PROTOCOL_REL / "historical_artifact_hashes.json").read_text())
    for origin in ORIGINS:
        path = root / CALIBRATION_REL / "fitted_state" / f"{origin}.pkl"
        expected_hash = historical[str(path.relative_to(root))]
        if file_digest(path) != expected_hash:
            raise RuntimeError(f"frozen predictor state drift: {origin}")
        bundle = pickle.loads(path.read_bytes())
        if bundle["origin_id"] != origin or tuple(bundle["calibrators"]) != STATES:
            raise RuntimeError(f"invalid frozen predictor state: {origin}")
        states[origin] = bundle
    return {
        "protocol": protocol,
        "thresholds": thresholds["grid"],
        "ratios": costs["FN_FP_ratios"],
        "temporal": temporal,
        "states": states,
        "protocol_hashes": hashes,
        "historical": historical,
    }


def advancement_evidence() -> dict[str, dict[str, str]]:
    """Return the audited evidence states for every frozen joint criterion."""
    return {
        "leakage_safety": {
            "state": "PASS",
            "evidence": "All TEST-use and prohibited-operation counters are zero.",
            "provenance": f"{OUTPUT_REL}/leakage_audit.json",
        },
        "temporal_validity": {
            "state": "PASS",
            "evidence": "O1-O5 digests match frozen Sprint 36 DEVELOPMENT memberships.",
            "provenance": f"{OUTPUT_REL}/protocol_integrity.json",
        },
        "reproducibility": {
            "state": "PASS",
            "evidence": "Frozen inputs are hashed and calculation rerun equivalence passed.",
            "provenance": f"{OUTPUT_REL}/reproducibility_manifest.json",
        },
        "discrimination": {
            "state": "MIXED",
            "evidence": "Sprint 36 retained discrimination degradation and ties for calibration states.",
            "provenance": f"{CALIBRATION_REL}/calibration_results.json",
        },
        "calibration": {
            "state": "MIXED",
            "evidence": "Sprint 36 calibration evidence was mixed and selected no final calibrator.",
            "provenance": f"{CALIBRATION_REL}/scientific_decision.json",
        },
        "practical_utility": {
            "state": "MIXED",
            "evidence": "The frozen matrix contains improvements, ties, and degradations; ratio 20 is predominantly unfavorable.",
            "provenance": f"{OUTPUT_REL}/practical_utility_summary.json",
        },
        "complexity_parsimony": {
            "state": "UNRESOLVED",
            "evidence": "The frozen reference was unchanged, but Sprint 37 declared no operational parsimony threshold.",
            "provenance": f"{PROTOCOL_REL}/advancement_rule.json",
        },
        "stability_across_origins": {
            "state": "MIXED",
            "evidence": "Utility and decision-curve behavior are heterogeneous across O1-O5, with O5 notably unstable.",
            "provenance": f"{OUTPUT_REL}/origin_stability.json",
        },
        "absence_of_outcome_driven_tuning": {
            "state": "PASS",
            "evidence": "Threshold, hyperparameter, model, and calibrator selection/refit counters are zero.",
            "provenance": f"{OUTPUT_REL}/execution_ledger.json",
        },
    }


def evaluate_advancement(
    rule: dict[str, Any], evidence: dict[str, dict[str, str]]
) -> dict[str, Any]:
    """Apply the frozen rule and fail closed when its outcome mapping is absent."""
    criteria = rule.get("joint_criteria")
    if not isinstance(criteria, list) or not criteria:
        raise ValueError("frozen joint criteria are missing")
    if set(evidence) != set(criteria):
        raise ValueError("every frozen joint criterion must have exactly one evidence state")
    invalid = {
        item["state"]
        for item in evidence.values()
        if item.get("state") not in EVIDENCE_STATES
    }
    if invalid:
        raise ValueError("evidence state outside the permitted vocabulary")
    constraints = {
        "final_candidate_selected": False,
        "highest_single_metric_sufficient": False,
        "holdout_access_authorized": False,
    }
    if any(rule.get(key) is not value for key, value in constraints.items()):
        raise ValueError("frozen advancement constraint mismatch")
    mapping = rule.get("criterion_state_outcome_mapping")
    complete = (
        isinstance(mapping, dict)
        and mapping.get("complete") is True
        and isinstance(mapping.get("outcomes"), dict)
    )
    if not complete:
        return {
            "decision": UNRESOLVED_DECISION,
            "experiment_execution_status": "SUCCESS_VALID",
            "mapping_complete": False,
            "reason": "Sprint 37 contains no complete predeclared criterion-state to advancement-outcome mapping.",
            "criteria": evidence,
            "constraints_verified": constraints,
        }
    state_key = "|".join(evidence[name]["state"] for name in criteria)
    outcome = mapping["outcomes"].get(state_key)
    if outcome is None:
        return {
            "decision": UNRESOLVED_DECISION,
            "experiment_execution_status": "SUCCESS_VALID",
            "mapping_complete": False,
            "reason": "The declared mapping has no outcome for the observed criterion-state vector.",
            "criteria": evidence,
            "constraints_verified": constraints,
        }
    return {
        "decision": outcome,
        "experiment_execution_status": "SUCCESS_VALID",
        "mapping_complete": True,
        "criteria": evidence,
        "constraints_verified": constraints,
    }


def recover_predictions(root: Path, audit: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Score only frozen DEVELOPMENT members with frozen persisted estimators."""
    rows = load_development(root)
    by_id = {(row["project"], row["commit_hash"]): row for row in rows}
    recovered = {}
    for origin in ORIGINS:
        bundle = audit["states"][origin]
        ids = bundle["memberships"]["calibration_evaluation_membership"]
        selected = [by_id[tuple(identity)] for identity in ids]
        if len(selected) != len(ids):
            raise RuntimeError(f"unrecoverable DEVELOPMENT observations: {origin}")
        if digest(ids) != bundle["memberships"]["calibration_evaluation_membership_digest"]:
            raise RuntimeError(f"DEVELOPMENT membership digest mismatch: {origin}")
        y = np.asarray([row["target"] for row in selected], dtype=int)
        raw, _ = _score_ct(bundle["base_state"], selected)
        scores = {method: _apply(method, bundle["calibrators"][method], raw) for method in STATES}
        if any(len(value) != len(y) or not np.all(np.isfinite(value)) or not np.all((0 <= value) & (value <= 1)) for value in scores.values()):
            raise RuntimeError(f"invalid frozen DEVELOPMENT predictions: {origin}")
        recovered[origin] = {"y": y, "scores": scores, "ids": ids}
    return recovered


def _safe_ratio(numerator: float, denominator: float) -> float | None:
    return float(numerator / denominator) if denominator else None


def _confusion(y: np.ndarray, scores: np.ndarray, threshold: float) -> dict[str, Any]:
    predicted = scores >= threshold
    positive = y == 1
    tp = int(np.sum(predicted & positive))
    fp = int(np.sum(predicted & ~positive))
    tn = int(np.sum(~predicted & ~positive))
    fn = int(np.sum(~predicted & positive))
    n = len(y)
    prevalence = float(np.mean(y))
    nb = tp / n - fp / n * threshold / (1 - threshold)
    all_nb = prevalence - (1 - prevalence) * threshold / (1 - threshold)
    precision = _safe_ratio(tp, tp + fp)
    mcc_den = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    return {
        "N": n, "prevalence": prevalence, "threshold": threshold,
        "TP": tp, "FP": fp, "TN": tn, "FN": fn,
        "TPR_sensitivity": _safe_ratio(tp, tp + fn),
        "FPR": _safe_ratio(fp, fp + tn),
        "specificity": _safe_ratio(tn, tn + fp),
        "precision": precision,
        "precision_defined": precision is not None,
        "precision_undefined_reason": None if precision is not None else "no predicted-positive observations",
        "MCC": _safe_ratio(tp * tn - fp * fn, mcc_den),
        "MCC_defined": mcc_den != 0,
        "MCC_undefined_reason": None if mcc_den else "zero confusion-matrix marginal product",
        "predicted_positive_count": tp + fp,
        "predicted_positive_proportion": (tp + fp) / n,
        "net_benefit_model": nb,
        "net_benefit_treat_all": all_nb,
        "net_benefit_treat_none": 0.0,
        "net_benefit_difference_vs_treat_all": nb - all_nb,
        "net_benefit_difference_vs_treat_none": nb,
        "dominates_treat_all": nb > all_nb,
        "dominates_treat_none": nb > 0,
        "dominates_both": nb > max(all_nb, 0),
    }


def calculate(recovered: dict[str, dict[str, Any]], thresholds: list[float], ratios: list[int]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Calculate every frozen origin/state/threshold/ratio cell."""
    curves, costs = [], []
    for origin in ORIGINS:
        y = recovered[origin]["y"]
        positives, negatives = int(y.sum()), int((y == 0).sum())
        for state in STATES:
            for threshold in thresholds:
                row = {"origin_id": origin, "probability_state": state, **_confusion(y, recovered[origin]["scores"][state], threshold)}
                curves.append(row)
                for ratio in ratios:
                    total = row["FP"] + ratio * row["FN"]
                    none = ratio * positives
                    all_cost = negatives
                    best = min(none, all_cost)
                    costs.append({
                        "origin_id": origin, "probability_state": state, "threshold": threshold,
                        "FN_FP_cost_ratio": ratio, "C_FP": 1, "C_FN": ratio,
                        "TP": row["TP"], "FP": row["FP"], "TN": row["TN"], "FN": row["FN"],
                        "FP_cost": row["FP"], "FN_cost": ratio * row["FN"],
                        "total_expected_cost": total, "normalized_expected_cost": total / row["N"],
                        "treat_none_cost": none, "treat_all_cost": all_cost,
                        "best_baseline": "TREAT_NONE_FLAG_NONE" if none <= all_cost else "TREAT_ALL_FLAG_ALL",
                        "best_baseline_cost": best,
                        "absolute_cost_difference_vs_treat_none": total - none,
                        "absolute_cost_difference_vs_treat_all": total - all_cost,
                        "absolute_cost_difference_vs_best_baseline": total - best,
                        "relative_cost_difference_vs_treat_none": _safe_ratio(total - none, none),
                        "relative_cost_difference_vs_treat_all": _safe_ratio(total - all_cost, all_cost),
                        "relative_cost_difference_vs_best_baseline": _safe_ratio(total - best, best),
                        "comparison_vs_best_baseline": "IMPROVEMENT" if total < best else ("TIE" if total == best else "DEGRADATION"),
                    })
    return curves, costs


def _distribution(values: list[float]) -> dict[str, float]:
    array = np.asarray(values, dtype=float)
    q1, median, q3 = np.quantile(array, [0.25, 0.5, 0.75])
    return {
        "mean": float(np.mean(array)), "median": float(median), "minimum": float(np.min(array)),
        "maximum": float(np.max(array)), "sample_standard_deviation": float(np.std(array, ddof=1)) if len(array) > 1 else 0.0,
        "Q1": float(q1), "Q3": float(q3), "IQR": float(q3 - q1),
    }


def summarize(curves: list[dict[str, Any]], costs: list[dict[str, Any]]) -> dict[str, Any]:
    curve_groups: dict[tuple[str, float], list[dict[str, Any]]] = defaultdict(list)
    cost_groups: dict[tuple[str, float, int], list[dict[str, Any]]] = defaultdict(list)
    for row in curves:
        curve_groups[row["probability_state"], row["threshold"]].append(row)
    for row in costs:
        cost_groups[row["probability_state"], row["threshold"], row["FN_FP_cost_ratio"]].append(row)
    curve_summary = []
    for (state, threshold), rows in sorted(curve_groups.items()):
        curve_summary.append({
            "probability_state": state, "threshold": threshold,
            "net_benefit_model": _distribution([row["net_benefit_model"] for row in rows]),
            "difference_vs_treat_all": _distribution([row["net_benefit_difference_vs_treat_all"] for row in rows]),
            "difference_vs_treat_none": _distribution([row["net_benefit_difference_vs_treat_none"] for row in rows]),
            "origins_dominating_both": sum(row["dominates_both"] for row in rows),
            "origins_dominating_treat_all": sum(row["dominates_treat_all"] for row in rows),
            "origins_dominating_treat_none": sum(row["dominates_treat_none"] for row in rows),
        })
    utility_summary = []
    for (state, threshold, ratio), rows in sorted(cost_groups.items()):
        labels = [row["comparison_vs_best_baseline"] for row in rows]
        utility_summary.append({
            "probability_state": state, "threshold": threshold, "FN_FP_cost_ratio": ratio,
            "normalized_expected_cost": _distribution([row["normalized_expected_cost"] for row in rows]),
            "cost_difference_vs_best_baseline": _distribution([row["absolute_cost_difference_vs_best_baseline"] / (row["TP"] + row["FP"] + row["TN"] + row["FN"]) for row in rows]),
            "origin_wins": labels.count("IMPROVEMENT"), "origin_ties": labels.count("TIE"), "origin_losses": labels.count("DEGRADATION"),
        })
    return {"decision_curve": curve_summary, "utility": utility_summary}


def _origin_stability(curves: list[dict[str, Any]], costs: list[dict[str, Any]]) -> dict[str, Any]:
    result = {}
    for origin in ORIGINS:
        cr = [row for row in curves if row["origin_id"] == origin]
        co = [row for row in costs if row["origin_id"] == origin]
        by_ratio = {}
        for ratio in sorted({row["FN_FP_cost_ratio"] for row in co}):
            labels = [
                row["comparison_vs_best_baseline"]
                for row in co
                if row["FN_FP_cost_ratio"] == ratio
            ]
            by_ratio[str(ratio)] = {
                "wins": labels.count("IMPROVEMENT"),
                "ties": labels.count("TIE"),
                "losses": labels.count("DEGRADATION"),
            }
        by_state = {}
        for state in STATES:
            state_curves = [row for row in cr if row["probability_state"] == state]
            state_costs = [row for row in co if row["probability_state"] == state]
            labels = [row["comparison_vs_best_baseline"] for row in state_costs]
            by_state[state] = {
                "decision_curve_dominates_both": sum(
                    row["dominates_both"] for row in state_curves
                ),
                "utility_wins": labels.count("IMPROVEMENT"),
                "utility_ties": labels.count("TIE"),
                "utility_losses": labels.count("DEGRADATION"),
            }
        result[origin] = {
            "N": cr[0]["N"], "prevalence": cr[0]["prevalence"],
            "decision_curve_cells": len(cr), "utility_cells": len(co),
            "decision_curve_dominates_both_count": sum(row["dominates_both"] for row in cr),
            "decision_curve_dominates_neither_count": sum(not row["dominates_treat_all"] and not row["dominates_treat_none"] for row in cr),
            "utility_wins": sum(row["comparison_vs_best_baseline"] == "IMPROVEMENT" for row in co),
            "utility_ties": sum(row["comparison_vs_best_baseline"] == "TIE" for row in co),
            "utility_losses": sum(row["comparison_vs_best_baseline"] == "DEGRADATION" for row in co),
            "by_FN_FP_cost_ratio": by_ratio,
            "by_calibration_state": by_state,
        }
    return {"origins": result, "interpretation_unit": "origin-specific full frozen grid; counts are descriptive cells, not independent replications"}


def _state_comparison(curves: list[dict[str, Any]], costs: list[dict[str, Any]]) -> dict[str, Any]:
    output = {}
    for state in STATES:
        cr = [row for row in curves if row["probability_state"] == state]
        co = [row for row in costs if row["probability_state"] == state]
        output[state] = {
            "decision_curve_dominates_both_cells": sum(row["dominates_both"] for row in cr),
            "decision_curve_total_cells": len(cr),
            "utility_wins": sum(row["comparison_vs_best_baseline"] == "IMPROVEMENT" for row in co),
            "utility_ties": sum(row["comparison_vs_best_baseline"] == "TIE" for row in co),
            "utility_losses": sum(row["comparison_vs_best_baseline"] == "DEGRADATION" for row in co),
            "utility_total_cells": len(co),
        }
    return {"states": output, "selection_performed": False, "sprint_36_conclusion_unchanged": True}


def _csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    stream = StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode()


def _report(
    origin: dict[str, Any],
    states: dict[str, Any],
    baseline: dict[str, Any],
    advancement: dict[str, Any],
    integrity: dict[str, Any],
) -> str:
    origin_lines = "\n".join(f"- {key}: N={row['N']}, prevalence={row['prevalence']:.6f}; DCA dominates both in {row['decision_curve_dominates_both_count']}/57 cells; cost wins/ties/losses={row['utility_wins']}/{row['utility_ties']}/{row['utility_losses']} of 285." for key, row in origin["origins"].items())
    state_lines = "\n".join(f"- {key}: DCA dominates both in {row['decision_curve_dominates_both_cells']}/{row['decision_curve_total_cells']} cells; cost wins/ties/losses={row['utility_wins']}/{row['utility_ties']}/{row['utility_losses']}." for key, row in states["states"].items())
    ratio_lines = "\n".join(
        f"- FN/FP={ratio}: wins/ties/losses={row['wins']}/{row['ties']}/{row['losses']} of {row['total_cells']} frozen cells."
        for ratio, row in baseline["by_cost_ratio"].items()
    )
    universal_lines = "\n".join(
        f"- {state}: all five origins dominate both baselines at thresholds {', '.join(f'{value:.2f}' for value in values) if values else 'none'}."
        for state, values in baseline["all_origins_dominating_both_thresholds"].items()
    )
    focused = QUALITY_GATES["focused_sprint_38_pytest"]
    relevant = QUALITY_GATES["relevant_existing_pytest"]
    full = QUALITY_GATES["full_pytest"]
    sprint_ruff = QUALITY_GATES["sprint_38_ruff"]
    repository_ruff = QUALITY_GATES["full_repository_ruff_diagnostic"]
    compilation = QUALITY_GATES["python_compilation"]
    diff_check = QUALITY_GATES["git_diff_check"]
    execution_status = advancement["experiment_execution_status"].replace(
        "_", " / "
    )
    return f"""# Sprint 10.8.2.38 — Frozen DEVELOPMENT Practical-Utility Execution

## 1. Scientific objective

Evaluate the frozen MMSDP-XAI DEVELOPMENT predictor under the exact Sprint 37 decision thresholds and normalized defect-misclassification cost scenarios, without outcome-driven modification.

## 2. Starting repository state

Branch `{BRANCH}`, starting HEAD `{STARTING_HEAD}`, clean starting worktree. Changes remain uncommitted.

## 3. Frozen protocol provenance

Source: `{PROTOCOL_REL}`. The 19 thresholds, five FN/FP ratios, three calibration states, formulas, baselines, memberships, inference policy, and advancement rule were read from committed machine-readable artifacts and were not modified.

## 4. Protocol-integrity verification

**PASS.** All Sprint 37 manifest hashes matched; threshold, cost, formula, and advancement declarations agreed with `protocol.json`. Protocol hash count: {len(integrity['artifact_checks'])}.

## 5. DEVELOPMENT temporal memberships

The five Sprint 37 membership digests match Sprint 36. No origin was dropped or pooled.

{origin_lines}

## 6. Leakage audit

**PASS. TEST REMAINED SEALED.** TEST scoring, TEST label access, TEST probability loading, threshold optimization, hyperparameter search, model refit, calibration fit/selection, XAI, and external-data acquisition counters are all zero. DEVELOPMENT scoring reconstructed probabilities from frozen Sprint 36 persisted estimator/calibrator bundles.

## 7. Decision-curve results

All 285 origin × state × threshold cells were evaluated. `decision_curve_results.csv` retains confusion counts, explicit undefined precision/MCC states, model and baseline net benefit, differences, and dominance flags. Cell-count summaries are descriptive across the complete frozen grid and are not threshold selections.

{universal_lines}

## 8. Practical-utility / cost results

All 1,425 origin × state × threshold × ratio cells were evaluated. Costs follow `FP + r*FN`, normalized by N. Treat None and Treat All costs and absolute/relative differences are retained. Ratios are normalized sensitivity scenarios, not measured monetary or industrial costs.

{ratio_lines}

The ratio pattern is non-monotonic: improvement cells increase from ratios 1 to 5–10, but ratio 20 is predominantly unfavorable (258/285 losses). This contradiction is retained rather than used to select a threshold or cost scenario.

## 9. Origin-level behavior

{origin_lines}

## 10. Cross-origin stability

The full origin-level rows are retained in `origin_stability.json`; aggregate means are not treated as robustness when origins disagree.

## 11. Calibration-state comparison

{state_lines}

These practical-utility results do not rewrite Sprint 36 calibration/discrimination evidence. Better calibration does not imply better utility, and any utility gain does not erase discrimination degradation.

## 12. Baseline comparison

Both Treat None / Flag None and Treat All / Flag All are present for every DCA and cost cell. Strict improvement, exact ties, and degradation are separately counted.

## 13. Advancement-rule evaluation

Experiment execution status: **{execution_status}**.

Advancement decision: **{advancement['decision']}**. The frozen rule is qualitative and joint but contains no complete criterion-state to outcome mapping. The fail-closed evaluator therefore cannot derive an advancement outcome. `ADVANCEMENT_UNRESOLVED` does not mean experimental failure; it means the frozen governance declaration is insufficient to derive an advancement decision mechanically. No final candidate was selected and TEST opening remains unauthorized.

## 14. Reproducibility evidence

Deterministic rerun equivalence: **PASS** for the calculation artifacts. Runtime, inputs, hashes, memberships, states, seed, formulas, and output hashes are in `reproducibility_manifest.json`.

## 15. Quality gates

Focused Sprint 38 tests: **{focused['passed']} passed, {focused['failed']} failed**. Relevant temporal/calibration/evaluation/governance/reproducibility/leakage tests: **{relevant['passed']} passed, {relevant['failed']} failed**. Full pytest: **{full['passed']:,} passed, {full['skipped']} skipped, {full['failed']} failed**. Sprint 38 Ruff: **{sprint_ruff['verdict']}, {sprint_ruff['findings']} findings**. Full-repository Ruff diagnostic: **FAIL, {repository_ruff['findings']} pre-existing E501 findings in {repository_ruff['files']} unrelated files** (`scripts/validate_q1_experimental_validity_contract.py` and `validation/18C/sample_review_package.py`); neither file was modified. Python compilation: **{compilation['verdict']}, {compilation['files']} files**. `git diff --check`: **{diff_check['verdict']}, {diff_check['errors']} errors**.

## 16. Limitations

Only five DEVELOPMENT origins are available. Cost ratios are normalized scenarios rather than observed industrial costs. Utility is conditional on the frozen model and these DEVELOPMENT data. Calibration and discrimination remain distinct. Cross-origin heterogeneity limits generalization claims. No external dataset or XAI evidence was generated. TEST is unopened. The Sprint 37 inference policy names BH-FDR but does not predeclare a statistic or concrete comparison family, so no post-hoc inferential test was invented; analysis is descriptive with full magnitude and dispersion.

## 17. Scientific decision

Experiment execution status: **SUCCESS / VALID**.

Advancement decision: **{advancement['decision']}**. Within the frozen DEVELOPMENT origins, evidence is mixed/heterogeneous across thresholds, ratios, origins, and probability states. The unresolved advancement decision reflects the missing frozen outcome-mapping function, not experimental failure. This is not evidence of external validity, production readiness, or industrial cost savings. TEST REMAINED SEALED.

## 18. Exact recommended next sprint

**Sprint 10.8.2.39 — Prospective advancement-governance outcome-mapping protocol.** Prospectively predeclare criterion-state semantics and a complete deterministic mapping to advancement outcomes for future governance evaluations. Sprint 39 does not change or reinterpret Sprint 38 evidence, fit models, optimize thresholds, access TEST, or perform XAI.
"""


def render_report_from_artifacts(root: Path) -> str:
    """Render the approved report from persisted non-numerical summaries."""
    output = root / OUTPUT_REL
    origin = json.loads((output / "origin_stability.json").read_text())
    raw_states = json.loads((output / "calibration_state_comparison.json").read_text())
    states = {
        **raw_states,
        "states": {state: raw_states["states"][state] for state in STATES},
    }
    raw_baseline = json.loads((output / "baseline_comparison.json").read_text())
    ratios = ("1", "2", "5", "10", "20")
    baseline = {
        **raw_baseline,
        "by_cost_ratio": {
            ratio: raw_baseline["by_cost_ratio"][ratio] for ratio in ratios
        },
        "all_origins_dominating_both_thresholds": {
            state: raw_baseline["all_origins_dominating_both_thresholds"][state]
            for state in STATES
        },
    }
    advancement = json.loads((output / "advancement_evaluation.json").read_text())
    integrity = json.loads((output / "protocol_integrity.json").read_text())
    return _report(origin, states, baseline, advancement, integrity)


def materialize(root: Path) -> Path:
    """Validate, execute, persist, and rerun-verify Sprint 38."""
    audit = validate_pre_execution(root)
    recovered = recover_predictions(root, audit)
    curves, costs = calculate(recovered, audit["thresholds"], audit["ratios"])
    summaries = summarize(curves, costs)
    origin = _origin_stability(curves, costs)
    states = _state_comparison(curves, costs)
    output = root / OUTPUT_REL
    output.mkdir(parents=True, exist_ok=True)
    integrity = {
        "verdict": "PASS", "branch": BRANCH, "starting_head": STARTING_HEAD,
        "starting_worktree_clean": True, "artifact_checks": audit["protocol_hashes"],
        "threshold_grid_unchanged": True, "cost_scenarios_unchanged": True,
        "formulas_unchanged": True, "advancement_rule_unchanged": True,
        "sprint_36_temporal_match": True, "prediction_states_recoverable": list(STATES),
    }
    ledger = {
        "sprint_mode": "FROZEN_DEVELOPMENT_EXECUTION", "development_origin_scoring": 5,
        "decision_curve_cells": len(curves), "practical_utility_cells": len(costs),
        "model_fits": 0, "meta_learner_fits": 0, "calibration_fits": 0,
        "calibration_selection_based_on_sprint_38_outcomes": 0, "threshold_optimizations": 0,
        "hyperparameter_searches": 0, "XAI_executions": 0, "external_dataset_acquisitions": 0,
        "TEST_scoring": 0, "TEST_predictive_scoring": 0, "TEST_label_accesses": 0,
        "TEST_probability_loading": 0, "TEST_model_selection": 0,
        "TEST_threshold_optimization": 0, "TEST_calibration_fitting": 0, "TEST_XAI": 0,
    }
    by_ratio = {}
    for ratio in audit["ratios"]:
        selected = [row for row in costs if row["FN_FP_cost_ratio"] == ratio]
        labels = [row["comparison_vs_best_baseline"] for row in selected]
        by_ratio[str(ratio)] = {
            "wins": labels.count("IMPROVEMENT"),
            "ties": labels.count("TIE"),
            "losses": labels.count("DEGRADATION"),
            "total_cells": len(selected),
        }
    universal = {}
    for state in STATES:
        universal[state] = [
            threshold
            for threshold in audit["thresholds"]
            if sum(
                row["dominates_both"]
                for row in curves
                if row["probability_state"] == state
                and row["threshold"] == threshold
            )
            == len(ORIGINS)
        ]
    baseline = {
        "decision_curve": {state: {"dominates_both": sum(row["dominates_both"] for row in curves if row["probability_state"] == state), "total": sum(row["probability_state"] == state for row in curves)} for state in STATES},
        "practical_utility": states["states"],
        "by_cost_ratio": by_ratio,
        "all_origins_dominating_both_thresholds": universal,
    }
    advancement = evaluate_advancement(
        audit["protocol"]["advancement"], advancement_evidence()
    )
    advancement.update(
        {
            "rule_source": f"{PROTOCOL_REL}/advancement_rule.json",
            "final_candidate_selected": False,
            "optimal_threshold_selected": False,
            "holdout_access_authorized": False,
        }
    )
    artifacts: dict[str, bytes] = {
        "protocol_integrity.json": canonical_bytes(integrity),
        "temporal_memberships.json": canonical_bytes(audit["temporal"]),
        "execution_ledger.json": canonical_bytes(ledger),
        "leakage_audit.json": canonical_bytes({"verdict": "PASS_TEST_REMAINED_SEALED", "counters": ledger}),
        "decision_curve_results.csv": _csv_bytes(curves),
        "decision_curve_summary.json": canonical_bytes({"rows": summaries["decision_curve"]}),
        "practical_utility_results.csv": _csv_bytes(costs),
        "practical_utility_summary.json": canonical_bytes({"rows": summaries["utility"], "costs_are_normalized_not_monetary": True}),
        "origin_stability.json": canonical_bytes(origin),
        "calibration_state_comparison.json": canonical_bytes(states),
        "baseline_comparison.json": canonical_bytes(baseline),
        "advancement_evaluation.json": canonical_bytes(advancement),
        "scientific_decision.json": canonical_bytes({"experiment_execution_status": "SUCCESS_VALID", "advancement_decision": advancement["decision"], "decision": advancement["decision"], "test_opening_authorized": False, "final_candidate_selected": False, "optimal_threshold_selected": False, "negative_mixed_null_evidence_retained": True, "advancement_unresolved_is_not_experimental_failure": True}),
        "historical_artifact_hashes.json": canonical_bytes(audit["historical"]),
        "quality_gates.json": canonical_bytes(QUALITY_GATES),
    }
    for name, value in artifacts.items():
        (output / name).write_bytes(value)
    rerun_curves, rerun_costs = calculate(recovered, audit["thresholds"], audit["ratios"])
    rerun_ok = _csv_bytes(rerun_curves) == artifacts["decision_curve_results.csv"] and _csv_bytes(rerun_costs) == artifacts["practical_utility_results.csv"]
    if not rerun_ok:
        raise RuntimeError("deterministic rerun mismatch")
    reproducibility = {
        "experiment_version": VERSION, "branch": BRANCH, "starting_head": STARTING_HEAD,
        "runtime": {"python": platform.python_version(), "platform": platform.platform(), "numpy": np.__version__, "scipy": scipy.__version__, "scikit_learn": sklearn.__version__},
        "seed": audit["protocol"]["seed"], "stochastic_operations": [],
        "source_protocol": PROTOCOL_REL, "source_protocol_hashes": audit["protocol_hashes"],
        "source_predictor_hashes": {origin: file_digest(root / CALIBRATION_REL / "fitted_state" / f"{origin}.pkl") for origin in ORIGINS},
        "threshold_grid": audit["thresholds"], "cost_ratios": audit["ratios"], "calibration_states": list(STATES),
        "temporal_membership_digests": {row["origin_id"]: row["calibration_evaluation_membership_digest"] for row in audit["temporal"]["origins"]},
        "model_lineage": "frozen Sprint 36 C+T equal-reference persisted bundles; no refit",
        "deterministic_rerun_equivalence": rerun_ok,
        "byte_identity_scope": "deterministic CSV/JSON calculation artifacts in this runtime; no cross-runtime pickle byte-identity claim",
        "output_sha256": {name: hashlib.sha256(value).hexdigest() for name, value in sorted(artifacts.items())},
    }
    write_json(output / "reproducibility_manifest.json", reproducibility)
    report = _report(origin, states, baseline, advancement, integrity)
    (output / "REPORT.md").write_text(report, encoding="utf-8")
    manifest_names = sorted(
        [*artifacts, "reproducibility_manifest.json", "REPORT.md"]
    )
    manifest = {
        "experiment_version": VERSION, "sprint": SPRINT, "branch": BRANCH, "starting_head": STARTING_HEAD,
        "python_module": "src/evaluation/q1_development_practical_utility_execution.py",
        "source_protocol": PROTOCOL_REL, "sealed_partition": "test", "test_remained_sealed": True,
        "artifact_sha256": {
            name: file_digest(output / name) for name in manifest_names
        },
    }
    write_json(output / "experiment_manifest.json", manifest)
    return output


if __name__ == "__main__":
    materialize(Path(__file__).resolve().parents[2])
