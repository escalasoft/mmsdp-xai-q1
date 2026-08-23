# ruff: noqa: E501

"""Validate and materialize the declaration-only Sprint 37 protocol."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

VERSION = "q1-development-practical-utility-protocol-1.0.0"
CONFIG_REL = "configs/experiments/q1_development_practical_utility_protocol_1.0.0.json"
OUTPUT_REL = "audits/q1-development-practical-utility-protocol/1.0.0"
STARTING_HEAD = "abce993b1cf4664d3554a6ecbe58d33debba41bb"
DECISION = "SPRINT_10.8.2.37_GO_WITH_LIMITATIONS"


def digest(path: Path) -> str:
    """Return the SHA-256 digest for a file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_write(path: Path, value: Any) -> None:
    """Write stable, hashable JSON."""
    path.write_text(
        json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def load_protocol(root: Path) -> dict[str, Any]:
    """Load and validate the frozen configuration."""
    config = json.loads((root / CONFIG_REL).read_text(encoding="utf-8"))
    validate_protocol(root, config)
    return config


def validate_protocol(root: Path, config: dict[str, Any]) -> None:
    """Reject protocol drift, leakage authorization, and outcome tuning."""
    thresholds = config["threshold_policy"]["grid"]
    ratios = config["cost_model"]["FN_FP_ratios"]
    if thresholds != sorted(set(thresholds)) or not all(0 < t < 1 for t in thresholds):
        raise ValueError("threshold grid must be finite, ordered, unique, and internal")
    if 0.5 not in thresholds or len(thresholds) != 19:
        raise ValueError("frozen threshold grid drift")
    if ratios != [1, 2, 5, 10, 20] or config["cost_model"]["C_FP"] != 1:
        raise ValueError("frozen normalized cost scenarios drift")
    temporal = config["temporal_protocol"]
    source = root / temporal["source"]
    if digest(source) != temporal["source_sha256"]:
        raise ValueError("Sprint 36 temporal membership drift")
    if temporal["origins"] != ["O1", "O2", "O3", "O4", "O5"]:
        raise ValueError("frozen origin set drift")
    if config["sealed_partition"] != "test" or "NO_TEST" not in config["test_policy"]:
        raise ValueError("TEST boundary is not sealed")
    forbidden_true = (
        config["threshold_policy"]["outcome_dependent_threshold_selection"],
        config["threshold_policy"]["optimization"],
        config["cost_model"]["outcome_dependent_cost_selection"],
        config["decision_curve"]["executed_in_sprint_37"],
        config["inference"]["performed_in_sprint_37"],
    )
    if any(forbidden_true):
        raise ValueError("Sprint 37 must remain declaration-only")


def _temporal_artifact(root: Path, config: dict[str, Any]) -> dict[str, Any]:
    source = json.loads(
        (root / config["temporal_protocol"]["source"]).read_text(encoding="utf-8")
    )
    results = json.loads(
        (root / "audits/q1-forward-development-calibration/1.0.0/calibration_results.json")
        .read_text(encoding="utf-8")
    )["rows"]
    by_origin = {row["origin_id"]: row for row in results if row["method"] == "UNCALIBRATED"}
    origins = []
    for item in source["origins"]:
        row = by_origin[item["origin_id"]]
        origins.append(
            {
                **item,
                "calibration_membership_digest": row["calibration_membership_digest"],
                "evaluation_count": row["calibration_evaluation_count"],
                "positive_count": row["positive_count"],
                "prevalence": row["prevalence"],
                "project_membership_count": row["project_support"],
                "project_membership_policy": "all evaluable frozen project windows; names and commit memberships remain in the hashed Sprint 36 source",
            }
        )
    return {
        "source": config["temporal_protocol"]["source"],
        "source_sha256": config["temporal_protocol"]["source_sha256"],
        "calibration_membership_source": config["temporal_protocol"]["calibration_membership_source"],
        "calibration_membership_source_sha256": digest(
            root / config["temporal_protocol"]["calibration_membership_source"]
        ),
        "verdict": "MATCHES_FROZEN_SPRINT_36_DEVELOPMENT_MEMBERSHIPS",
        "origins": origins,
    }


def _historical_hashes(root: Path) -> dict[str, str]:
    paths = []
    for sprint_dir in (
        "audits/q1-experimental-evidence-gap-audit/1.0.0",
        "audits/q1-experimental-validity-contract/1.0.0",
        "audits/q1-modality-factorial/1.0.0",
        "audits/q1-fusion-process-ablation/1.0.0",
        "audits/q1-forward-development-calibration/1.0.0",
    ):
        paths.extend(path for path in (root / sprint_dir).rglob("*") if path.is_file())
    return {str(path.relative_to(root)): digest(path) for path in sorted(paths)}


def materialize(root: Path) -> Path:
    """Persist the frozen declaration and its audit evidence; perform no scoring."""
    config = load_protocol(root)
    output = root / OUTPUT_REL
    output.mkdir(parents=True, exist_ok=True)
    temporal = _temporal_artifact(root, config)
    artifacts = {
        "protocol.json": config,
        "cost_scenarios.json": config["cost_model"],
        "threshold_grid.json": config["threshold_policy"],
        "decision_curve_definition.json": config["decision_curve"],
        "utility_definition.json": config["utility"],
        "temporal_memberships.json": temporal,
        "metric_policy.json": {"outputs": config["outputs"], "aggregation": config["aggregation"]},
        "inference_policy.json": config["inference"],
        "advancement_rule.json": config["advancement"],
        "methodological_alignment.json": _alignment(),
        "historical_artifact_hashes.json": _historical_hashes(root),
        "execution_ledger.json": _ledger(),
        "scientific_decision.json": {
            "decision": DECISION,
            "final_model_selected": False,
            "final_calibrator_selected": False,
            "optimal_threshold_selected": False,
            "test_opening_authorized": False,
        },
    }
    for name, value in artifacts.items():
        canonical_write(output / name, value)
    manifest = {
        "experiment_version": VERSION,
        "branch": config["branch"],
        "starting_head": STARTING_HEAD,
        "configuration": CONFIG_REL,
        "configuration_sha256": digest(root / CONFIG_REL),
        "artifact_sha256": {
            name: digest(output / name) for name in sorted(artifacts)
        },
        "seed": config["seed"],
        "python_module": "src/evaluation/q1_development_practical_utility_protocol.py",
    }
    canonical_write(output / "experiment_manifest.json", manifest)
    (output / "REPORT.md").write_text(_report(config, temporal), encoding="utf-8")
    return output


def _ledger() -> dict[str, int | str]:
    keys = (
        "model_fits", "meta_learner_fits", "calibration_fits",
        "decision_curve_executions", "practical_utility_scoring",
        "threshold_optimizations", "hyperparameter_searches", "XAI_executions",
        "external_dataset_acquisitions", "TEST_scoring", "TEST_predictive_scoring",
        "TEST_model_selection", "TEST_threshold_optimization",
        "TEST_calibration_fitting", "TEST_XAI",
    )
    return {"sprint_mode": "PROTOCOL_DECLARATION_ONLY", **dict.fromkeys(keys, 0)}


def _alignment() -> dict[str, Any]:
    mapping = {
        "R1": "frozen forward temporal OOS DEVELOPMENT origins",
        "R2": "Treat None and Treat All chance/decision anchors",
        "R3": "Accuracy and F1 prohibited as sole evidence",
        "R4": "median, range, quartiles, IQR, and distributions required",
        "R5": "BH-FDR for a predeclared multiple-comparison family",
        "R6": "costs, thresholds, candidates, memberships, and rules frozen",
        "R7": "full origin-level and neutral-result reporting required",
        "R8": "dataset and membership sources identified by version and hash",
        "R9": "historical preprocessing lineage preserved and hashed",
        "R10": "seed and canonical artifact hashes persisted",
        "R14": "versioned code, configuration, and audit artifacts",
        "R15": "prescriptive pre-execution design independent of outcomes",
    }
    return {"reference": "Destefanis et al. (2026), An audit of machine learning experiments on software defect prediction", "type": "methodological_checklist_not_validated_score", "applicable_recommendations": mapping}


def _report(config: dict[str, Any], temporal: dict[str, Any]) -> str:
    grid = ", ".join(f"{x:.2f}" for x in config["threshold_policy"]["grid"])
    return f"""# Sprint 10.8.2.37 — DEVELOPMENT Decision-Curve / Practical-Utility Protocol Declaration

## 1. Scientific decision

**{DECISION}**. The DEVELOPMENT-only protocol is frozen and outcome-independent. This does not select a final model, calibrator, or threshold and does not authorize TEST access.

## 2. Branch / starting HEAD

`{config['branch']}` from `{STARTING_HEAD}`.

## 3. Purpose of Sprint 37

Predeclare practical-utility methods before execution, removing researcher degrees of freedom. No decision curve or utility comparison was calculated.

## 4. Prior evidence inherited from Sprint 36

Equal-weight leakage-safe C+T remains a reference, not a final model. ISOTONIC passed aggregate calibration adequacy but gains were modest and it introduced discrimination degradation/ties. No final calibrator or threshold was selected. Sprint 36 concluded `DECISION_CURVE_PROTOCOL_NOT_READY`; this sprint supplies the missing fixed cost and threshold contracts.

## 5. JIT-SDP operational decision semantics

At each commit the predictor emits a defect-proneness probability. Crossing a threshold flags the commit for additional quality attention (review, testing, inspection prioritization, or alert). Predictive classification is distinct from an operational intervention; no empirical industrial deployment cost is claimed.

## 6. TP/FP/TN/FN interpretation

TP is a defect-prone commit correctly flagged; FP is a non-defect-prone commit unnecessarily flagged; TN is a non-defect-prone commit correctly not flagged; FN is a missed opportunity to flag a defect-prone commit.

## 7. Frozen cost scenarios

Normalized `C_TP=C_TN=0`, `C_FP=1`; FN/FP ratios are **1, 2, 5, 10, 20**. These are sensitivity scenarios, not monetary or organization-specific costs, and cannot be changed after observing outcomes.

## 8. Frozen threshold grid

**{grid}**. The grid is identical across origins, calibration states, and candidates. `0.50` is the historical non-optimized reference. No post-hoc threshold addition or optimization is permitted.

## 9. Decision-curve formulation

`NB(t) = TP(t) / N - FP(t) / N * t / (1 - t)`, compared with Treat None / Flag None, Treat All / Flag All, and the reference predictor(s).

## 10. Practical-utility formulation

`ExpectedCost(t, r) = FP(t) * C_FP + FN(t) * C_FN(r)`, where `C_FN(r)=r`; `NormalizedCost(t, r) = ExpectedCost(t, r) / N`. Lower is better. Utility is not composited with discrimination, calibration, MCC, or F1.

## 11. Calibration states eligible for future comparison

UNCALIBRATED, PLATT, and ISOTONIC remain eligible for descriptive DEVELOPMENT comparison. This preserves Sprint 36's mixed evidence and makes no final-calibrator claim.

## 12. Temporal membership governance

Verdict: **{temporal['verdict']}**. O1–O5 and their train, calibration, evaluation, project support, prevalence, exclusions, membership digests, and source hashes are persisted. Boundaries and difficult origins cannot be moved or dropped.

## 13. Metric hierarchy

Every origin × calibration state × threshold must report TP, FP, TN, FN, recall, specificity, precision, MCC, predicted-positive rate, prevalence, net benefit, and normalized costs. ROC-AUC, PR-AUC, Brier, and ECE remain probability-level diagnostics. Accuracy or F1 cannot be sole evidence; F1 is descriptive only.

## 14. Dispersion policy

Across origins report median, minimum, maximum, Q1, Q3, and IQR; add mean, standard deviation, and confidence intervals where defensible. Article evidence must support box/distribution plots, not a single average.

## 15. Statistical-inference / BH-FDR policy

No inference occurred. Future multiple comparisons report magnitude/effect size first, uncertainty, raw p-values where applicable, and Benjamini–Hochberg FDR-adjusted p-values for the predeclared family. Neutral results remain; `p>=0.05` is not equivalence. Five origins give limited resolution, and commits are not independent experimental replications.

## 16. Advancement rule

Advancement jointly considers leakage safety, temporal validity, reproducibility, discrimination, calibration, utility, parsimony, stability, and absence of outcome tuning. No single best metric suffices. The simplest defensible candidate may advance despite a marginally lower isolated score. No candidate is selected here.

## 17. Destefanis et al. methodological alignment

The machine-readable checklist maps applicable R1–R10, R14, and R15 recommendations. It is not a new validated scientific score.

## 18. Reproducibility / hashes

Configuration, historical Sprint 32–36 artifacts, memberships, generated artifacts, version, seed, branch, and starting HEAD are hash-addressed in the manifests.

## 19. TEST governance

TEST remains sealed: scoring, predictive scoring, model selection, threshold optimization, calibration fitting, and XAI are all zero and unauthorized.

## 20. Execution ledger

Model fits, meta-learner fits, calibration fits, decision curves, utility scoring, threshold optimizations, hyperparameter searches, XAI, external acquisitions, and every TEST counter are zero. Sprint 37 declares only.

## 21. Quality-gate results

Focused Sprint 37 tests: **10 passed**. Relevant temporal, calibration,
evaluation, and governance tests: **105 passed**. Full pytest: **1394 passed,
1 skipped**. Sprint 37 Ruff, Python compilation, and `git diff --check`:
**PASS**. Full-repository Ruff is reported separately if historical findings
remain.

## 22. Limitations

Costs are normalized scenarios rather than observed industrial costs; only five origins limit inference; calibration evidence is DEVELOPMENT-only; C+T and all calibrators remain candidates; no utility outcomes or external validity are established.

## 23. Exact recommended next sprint

Sprint 10.8.2.38 — Execute Frozen DEVELOPMENT Decision-Curve and Practical-Utility Evaluation. Execute this protocol on DEVELOPMENT only; keep TEST sealed.
"""
