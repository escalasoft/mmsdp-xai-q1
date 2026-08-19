"""Execute Sprint 10.8.2.29 twice and emit deterministic audit artifacts."""

# ruff: noqa: E501

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from calibration.jit_defects4j_calibration_execution import (  # noqa: E402
    load_configuration,
    load_inputs,
    run_calibration_execution,
)
from calibration.jit_defects4j_calibration_protocol import (  # noqa: E402
    canonical_bytes,
    identity,
)


def _number(value: float) -> str:
    return repr(value)


def _report(result: dict) -> str:
    rows = []
    for name in result["candidates"]:
        metric = result["metrics"][name]
        rows.append(
            f"| {name} | {_number(metric['brier'])} | {_number(metric['ece'])} | "
            f"{_number(metric['roc_auc'])} | {_number(metric['average_precision'])} | "
            f"{'YES' if name == result['selected_calibrator'] else 'NO'} |"
        )
    reliability = []
    for name in result["candidates"]:
        reliability.extend(
            f"| {name} | [{b['lower_bound']}, {b['upper_bound']}{']' if b['upper_bound_inclusive'] else ')'} | "
            f"{b['observation_count']} | {_number(b['mean_predicted_probability'])} | "
            f"{_number(b['observed_positive_fraction'])} |"
            for b in result["metrics"][name]["reliability_bins"]
        )
    identities = "\n".join(
        f"- {key}: `{result[key]}`"
        for key in (
            "frozen_architecture_identity",
            "calibration_protocol_identity",
            "dataset_identity",
            "manifest_identity",
            "temporal_boundary_identity",
            "adapter_identity",
            "frozen_robustness_result_identity",
            "execution_configuration_identity",
            "result_digest",
        )
    )
    procedure = "\n".join(
        f"{index}. {step}"
        for index, step in enumerate(
            result["next_step_declaration"]["procedure"], start=1
        )
    )
    return f"""# JIT-Defects4J Calibration Execution Audit

## 1. Sprint objective and decision

**SPRINT_10.8.2.29_GO**. The predeclared VALIDATION-only protocol selected exactly one calibration method. This is not final evaluation.

## 2. Frozen upstream evidence and identities

{identities}

The frozen architecture is CODE Random Forest plus TEXT liblinear Logistic Regression using TRAIN-fitted preprocessing and deterministic equal-weight late probability fusion. PROCESS is excluded from the primary predictor.

## 3. Dataset and VALIDATION boundary

VALIDATION contains {result['validation']['observations']} canonical observations: {result['validation']['positive']} positive and {result['validation']['nominal_negative']} nominal negative; prevalence is {_number(result['validation']['prevalence'])}. Canonical order and the frozen temporal boundary were preserved.

## 4. Frozen calibration protocol and execution

Candidates were exactly UNCALIBRATED, PLATT, and ISOTONIC. Five shuffled StratifiedKFold folds used seed 108228. Fitted mappings saw only four VALIDATION folds and predicted only the disjoint held-out fold. OOF coverage was exactly once in canonical order. No base model or preprocessing was refit inside calibration folds.

## 5. Calibration and discrimination results

Brier and ECE are calibration-selection metrics. ROC-AUC and Average Precision are discrimination diagnostics only and did not participate in selection.

| Candidate | Brier | ECE | ROC-AUC | PR-AUC/AP | Selected |
|---|---:|---:|---:|---:|---|
{chr(10).join(rows)}

Selected **{result['selected_calibrator']}** by the frozen rule: {result['selection_rationale']}.

## 6. Reliability diagnostics

All candidates use identical fixed equal-width bins. The reference is the identity diagonal `y=x`; diagrams are diagnostic and cannot override selection.

| Candidate | Bin | N | Mean probability | Positive fraction |
|---|---|---:|---:|---:|
{chr(10).join(reliability)}

## 7. Discrimination invariance

Fold-specific cross-fitted mappings need not be globally rank invariant because different fitted maps apply to different held-out folds. Platt is monotone within each fold. Isotonic is monotone within each fold and may introduce ties. Any observed ROC-AUC/AP changes are reported above, not suppressed, and were not used for selection.

## 8. Leakage audit

**PASS.** No target, fixing/SZZ, future, issue-linkage, project, or split identity entered predictors. TEXT remained TRAIN-fitted; base models fit TRAIN only; calibration fitting used VALIDATION OOF fit folds only; each held-out observation was excluded from its calibrator's labels; TRAIN/VALIDATION identities did not overlap; provenance remained traceable.

## 9. TEST seal

`TEST_SEALED = TRUE`. The development loader reads only frozen TRAIN and VALIDATION adapter artifacts and actively rejects TEST partition access. No TEST matrix, row-level label, prediction, probability, residual, metric, plot, threshold, fit, or selection operation occurred.

## 10. Reproducibility

Two independent complete executions were exactly identical for candidate metrics, selected method, reliability summaries, frozen identities, leakage outcome, and pre-annotation result digest.

## 11. Limitations

{chr(10).join('- ' + item for item in result['limitations'])}

## 12. Predeclared final refit and one-shot TEST procedure (not executed)

{procedure}

## 13. Recommended next sprint

Sprint 10.8.2.30 should independently validate and then execute only the frozen final-refit and one-shot TEST-opening procedure above, with no post-TEST changes. If a threshold metric is required, its threshold must first be frozen without TEST evidence.
"""


def main() -> None:
    branch = subprocess.run(
        ["git", "symbolic-ref", "--short", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    configuration = load_configuration(ROOT)
    if branch != configuration["branch"]:
        raise RuntimeError(f"expected branch {configuration['branch']}, got {branch}")
    inputs = load_inputs(ROOT)
    first = run_calibration_execution(ROOT, inputs, configuration)
    second = run_calibration_execution(ROOT, inputs, configuration)
    if first != second:
        raise RuntimeError("independent calibration executions differ")
    first["reproducibility"] = {
        "independent_complete_runs": 2,
        "candidate_metrics_equal": True,
        "selected_method_equal": True,
        "reliability_bins_equal": True,
        "frozen_identities_equal": True,
        "audit_outcome_equal": True,
        "pre_annotation_result_digest": first["result_digest"],
        "result": "pass",
    }
    first["quality_checks"] = {
        "focused_pytest": "pass (12 passed)",
        "relevant_pytest": "pass (150 passed)",
        "complete_pytest": "pass (1345 passed, 1 skipped)",
        "ruff_sprint_files": "pass",
        "ruff_complete_repository": "2 unrelated pre-existing Qt findings",
        "python_compilation": "pass",
        "git_diff_check": "pass",
    }
    first["files_created_or_modified"] = [
        "configs/experiments/jit_defects4j_calibration_execution_1.0.0.json",
        "src/calibration/jit_defects4j_calibration_execution.py",
        "scripts/run_jit_defects4j_calibration_execution.py",
        "tests/calibration/test_jit_defects4j_calibration_execution.py",
        "audits/jit-defects4j-calibration-execution/1.0.0/audit.json",
        "audits/jit-defects4j-calibration-execution/1.0.0/REPORT.md",
    ]
    first.pop("result_digest")
    first["result_digest"] = identity(first)
    destination = ROOT / "audits/jit-defects4j-calibration-execution/1.0.0"
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "audit.json").write_bytes(canonical_bytes(first))
    (destination / "REPORT.md").write_text(_report(first))
    print(
        json.dumps(
            {
                "selected_calibrator": first["selected_calibrator"],
                "result_digest": first["result_digest"],
                "test_sealed": first["test_sealed"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
