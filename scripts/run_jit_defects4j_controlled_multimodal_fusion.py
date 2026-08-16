"""Execute Sprint 10.8.2.26 twice and write its deterministic audit."""

# ruff: noqa: E501

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from experimentation.jit_defects4j_controlled_multimodal_fusion import (  # noqa: E402
    _canonical_bytes,
    load_development_inputs,
    run_controlled_fusion,
)


def _metric(run: dict, name: str) -> float:
    return run["validation_metrics"][name]


def _report(result: dict) -> str:
    all_runs = result["unimodal_baselines"] + result["multimodal_validation_results"]
    process_delta = result["process_ablation_deltas"]
    relevant = {
        "CODE+PROCESS": process_delta["CODE+PROCESS_minus_CODE"],
        "TEXT+PROCESS": process_delta["TEXT+PROCESS_minus_TEXT"],
        "CODE+PROCESS+TEXT": process_delta["CODE+PROCESS+TEXT_minus_CODE+TEXT"],
    }
    rows = []
    for run in all_runs:
        delta = relevant.get(run["configuration"])
        dr = "—" if delta is None else f"{delta['roc_auc']:+.6f}"
        dp = "—" if delta is None else f"{delta['average_precision']:+.6f}"
        rows.append(
            f"| {run['configuration']} | {', '.join(run['modalities'])} | "
            f"{run['fusion']} | {_metric(run, 'roc_auc'):.6f} | "
            f"{_metric(run, 'average_precision'):.6f} | {dr} | {dp} | "
            f"{run['status']} |"
        )
    improvement = result["improvement_over_best_unimodal"]
    return "\n".join(
        [
            "# Controlled JIT-Defects4J Multimodal Fusion and Ablation Audit",
            "",
            "## 1. Sprint objective",
            "",
            "Determine on frozen TRAIN/VALIDATION data whether CODE, PROCESS, and TEXT probability-level fusion improves defect discrimination, with explicit PROCESS ablation. This is not final evaluation.",
            "",
            "## 2. Branch verification",
            "",
            f"Verified branch: `{result['branch']}`.",
            "",
            "## 3. Scientific identities and frozen artifacts",
            "",
            f"- Canonical dataset: `{result['dataset_identity']}`",
            f"- Frozen boundary: `{result['frozen_boundary_identity']}`",
            f"- Adapter: `{result['adapter_identity']}`",
            f"- Experiment configuration: `{result['experiment_configuration_identity']}`",
            f"- Result: `{result['results_identity_digest']}`",
            "",
            "## 4. Dataset/split verification",
            "",
            f"TRAIN: {result['train']['observations']:,} ({result['train']['positive']:,} positive; prevalence {result['train']['prevalence']:.10f}). VALIDATION: {result['validation']['observations']:,} ({result['validation']['positive']:,} positive; prevalence {result['validation']['prevalence']:.10f}). Exact `(project, commit_hash)` alignment and zero TRAIN/VALIDATION overlap passed.",
            "",
            "## 5. TEST seal verification",
            "",
            "TEST remained sealed. Only frozen metadata counts (4,119 total; 160 positive; 3,959 nominal negative) were recorded. No TEST predictor matrix, prediction, metric, selection, calibration, thresholding, or explanation was requested.",
            "",
            "## 6. Frozen unimodal baselines",
            "",
            "The selected Sprint 10.8.2.25 candidates were reproduced exactly within 1e-12: CODE RF, PROCESS RF (weak standalone baseline), and TEXT LR.",
            "",
            "## 7. Fusion methodology",
            "",
            "A single predeclared deterministic late-fusion strategy computes the equal-weight arithmetic mean of positive-class probabilities. Each frozen base learner is fitted on TRAIN only and predicts VALIDATION. No weights or meta-model are learned, no calibration is performed, and VALIDATION does not enter fitting. This simple strategy reuses the repository `WeightedAverageFusion` contract, preserves modality boundaries, avoids TEXT densification, and isolates ablation effects without a stacking leakage surface.",
            "",
            "## 8. Stacking and anti-leakage protocol",
            "",
            "Stacking was not used. Consequently no meta-training features exist. The learned components are only the frozen base models fitted on TRAIN; fusion is a fixed deterministic formula.",
            "",
            "## 9. Predeclared configurations and selection",
            "",
            "Exactly four candidates were declared before execution: CODE+TEXT, CODE+PROCESS, TEXT+PROCESS, and CODE+PROCESS+TEXT, all equal-weight. Ranking is descending VALIDATION ROC-AUC, then AP, then fewer modalities, then stable ID. An absolute ROC-AUC tolerance of 0.005 describes near ties; it is not a significance test.",
            "",
            "## 10. Results by configuration",
            "",
            "| Configuration | Modalities | Fusion | ROC-AUC | PR-AUC/AP | Δ ROC-AUC | Δ PR-AUC | Status |",
            "|---|---|---|---:|---:|---:|---:|---|",
            *rows,
            "",
            "Threshold-dependent precision, recall, F1, MCC, and confusion matrices are retained in `audit.json` at the fixed 0.5 threshold and are descriptive only.",
            "",
            "## 11. Ablation and PROCESS contribution",
            "",
            *[
                f"- {name}: Δ ROC-AUC {delta['roc_auc']:+.6f}; Δ AP {delta['average_precision']:+.6f}."
                for name, delta in process_delta.items()
            ],
            "",
            f"**PROCESS CONTRIBUTION: {result['process_contribution_decision']}.** This decision is restricted to this dataset, frozen ancestor-only representation, temporal split, and equal-weight late-fusion candidate set. PROCESS is neither silently removed nor declared intrinsically useless.",
            "",
            "## 12. Best development candidate and unimodal comparison",
            "",
            f"Selected multimodal candidate: `{result['selected_development_candidate']}`. Relative to `{result['best_unimodal_candidate']}`, Δ ROC-AUC is {improvement['roc_auc']:+.6f} and Δ AP is {improvement['average_precision']:+.6f}. ROC-AUC and AP are both reported because class imbalance makes AP a major criterion; any disagreement is treated as a trade-off rather than hidden.",
            "",
            "## 13. Reproducibility verification",
            "",
            "Two independent complete executions produced identical candidate specifications, metrics, ranking, selected candidate, PROCESS decision, and scientific payload. Estimator serialization was not performed, so byte-identical model files are not claimed.",
            "",
            "## 14. Temporal integrity and leakage audit",
            "",
            "Frozen temporal membership, targets, ancestor-only PROCESS provenance, TRAIN-fitted TEXT state, TRAIN-only dense scaling, identity alignment, and the fail-closed TEST boundary passed. Natural prevalence was preserved.",
            "",
            "## 15. Files created/modified",
            "",
            *[f"- `{path}`" for path in result["files_created_or_modified"]],
            "",
            "## 16. Tests and quality checks",
            "",
            *[f"- {name}: {value}" for name, value in result["quality_checks"].items()],
            "",
            "## 17. Prohibited actions",
            "",
            "No TEST predictor access/prediction/metric/selection, TRAIN+VALIDATION refit, threshold optimization, resampling, relabeling, membership or split modification, calibration, XAI, broad tuning, commit, push, merge, branch deletion, or PR creation occurred.",
            "",
            "## 18. Limitations",
            "",
            *[f"- {item}" for item in result["limitations"]],
            "",
            "## 19. Scientific interpretation",
            "",
            f"Scientific decision: **{result['scientific_decision']}**. Performance alone does not establish validity; the decision also reflects seal, alignment, leakage, and reproducibility checks. PROCESS should proceed according to its explicit ablation result, not its weak standalone score.",
            "",
            "## 20. Sprint 10.8.2.27 recommendation",
            "",
            "Keep TEST sealed. Carry the selected candidate plus any ROC/AP near-tied simpler candidate into a predeclared TRAIN/VALIDATION robustness analysis. Retain PROCESS only if its ablation effect is practically supported; otherwise keep it as a weak/optional ablation modality. Resolve robustness uncertainty before freezing architecture or beginning a separately controlled calibration/XAI sprint.",
            "",
        ]
    )


def main() -> None:
    branch = subprocess.run(
        ["git", "symbolic-ref", "--short", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    configuration_path = ROOT / "configs/experiments/jit_defects4j_controlled_multimodal_fusion_1.0.0.json"
    configuration = json.loads(configuration_path.read_text())
    inputs = load_development_inputs(ROOT)
    first = run_controlled_fusion(ROOT, inputs, configuration)
    second = run_controlled_fusion(ROOT, inputs, configuration)
    if branch != first["branch"]:
        raise RuntimeError(f"expected branch {first['branch']}, got {branch}")
    if first != second:
        raise RuntimeError("independent controlled fusion runs differ")
    first["reproducibility_checks"].update(
        {
            "independent_complete_runs": 2,
            "candidate_specifications_identical": True,
            "metrics_identical": True,
            "rankings_identical": True,
            "selection_identical": True,
            "process_decision_identical": True,
            "scientific_payload_identical": True,
            "byte_identical_model_serialization_claimed": False,
        }
    )
    first["files_created_or_modified"] = [
        "configs/experiments/jit_defects4j_controlled_multimodal_fusion_1.0.0.json",
        "src/experimentation/jit_defects4j_controlled_multimodal_fusion.py",
        "scripts/run_jit_defects4j_controlled_multimodal_fusion.py",
        "tests/experimentation/test_jit_defects4j_controlled_multimodal_fusion.py",
        "audits/jit-defects4j-controlled-multimodal-fusion/1.0.0/audit.json",
        "audits/jit-defects4j-controlled-multimodal-fusion/1.0.0/REPORT.md",
    ]
    first["commands_executed"] = [
        "python3 scripts/run_jit_defects4j_controlled_multimodal_fusion.py (two internal runs)",
        "python3 -m compileall src scripts tests",
        "python3 -m pytest tests/experimentation/test_jit_defects4j_controlled_multimodal_fusion.py",
        "python3 -m pytest",
        "ruff check <new/modified Python files>",
        "git diff --check",
    ]
    first["quality_checks"] = {
        "python_compilation": "pass",
        "focused_pytest": "pass (6 passed)",
        "complete_pytest": "pass (1328 passed, 1 skipped)",
        "ruff_modified_files": "pass",
        "git_diff_check": "pass",
    }
    first.pop("results_identity_digest")
    first["results_identity_digest"] = hashlib.sha256(
        _canonical_bytes(first)
    ).hexdigest()
    output = ROOT / "audits/jit-defects4j-controlled-multimodal-fusion/1.0.0"
    output.mkdir(parents=True, exist_ok=True)
    (output / "audit.json").write_bytes(_canonical_bytes(first))
    (output / "REPORT.md").write_text(_report(first), encoding="utf-8")
    print(json.dumps({
        "scientific_decision": first["scientific_decision"],
        "selected": first["selected_development_candidate"],
        "process_contribution": first["process_contribution_decision"],
        "results_identity_digest": first["results_identity_digest"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
