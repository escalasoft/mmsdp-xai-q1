"""Run and audit Sprint 10.8.2.25 without exposing TEST."""

# ruff: noqa: E501

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from experimentation.jit_defects4j_controlled_baselines import (  # noqa: E402
    load_development_inputs,
    run_development_baselines,
)
from preprocessing.jit_defects4j_adapters import canonical_bytes  # noqa: E402


def _report(result: dict[str, object]) -> str:
    runs = result["candidate_models"]
    selected = result["selected_development_candidates"]
    rows = []
    for run in runs:
        metrics = run["validation_metrics"]
        marker = (
            "selected"
            if selected[run["modality"]] == run["candidate_id"]
            else "candidate"
        )
        rows.append(
            f"| {run['modality']} | {run['model_family']} | {run['candidate_id']} | "
            f"{metrics['roc_auc']:.6f} | {metrics['average_precision']:.6f} | {marker} |"
        )
    return "\n".join(
        [
            "# Controlled JIT-Defects4J TRAIN/VALIDATION Baseline Audit",
            "",
            "## 1. Scientific decision",
            "",
            "**GO.** The frozen identities and temporal partitions were preserved; all development decisions use TRAIN/VALIDATION only. These are development results, not final generalization claims.",
            "",
            "## 2. Branch and repository state",
            "",
            "Executed on `sprint-10/jit-defects4j-controlled-baselines`. No commit, push, merge, or PR was performed.",
            "",
            "## 3. Scientific identities",
            "",
            f"- Canonical dataset: `{result['dataset_identity']}`",
            f"- Frozen boundary: `{result['frozen_boundary_identity']}`",
            f"- Adapter configuration: `{result['adapter_identity']}`",
            f"- Results identity: `{result['results_identity_digest']}`",
            "",
            "## 4. Partitions and TEST seal",
            "",
            f"TRAIN: {result['train']['observations']:,} observations, {result['train']['positive']:,} positive, {result['train']['nominal_negative']:,} nominal negative, prevalence {result['train']['prevalence']:.10f}.",
            f"VALIDATION: {result['validation']['observations']:,} observations, {result['validation']['positive']:,} positive, {result['validation']['nominal_negative']:,} nominal negative, prevalence {result['validation']['prevalence']:.10f}.",
            "TEST remained sealed. Only previously frozen metadata counts were verified; no TEST matrix, predictor, score, prediction, or predictive metric was requested.",
            "",
            "## 5. Frozen modalities and candidate policy",
            "",
            "CODE-STRUCTURAL has six exact Git raw-tree change-count features. PROCESS has four ancestor-only fields. TEXT is the frozen 5,000-dimensional TRAIN-fitted unigram TF-IDF CSR representation. Dense numeric scaling was fitted on TRAIN and applied transform-only to VALIDATION; TEXT remained sparse.",
            "",
            "Two deterministic LR configurations (C=0.1, 1.0) and two deterministic RF configurations (unbounded depth/leaf=1; depth=12/leaf=5), all seed 0 and without class weighting, were compared. Selection sorts VALIDATION ROC-AUC, then VALIDATION average precision, then stable candidate ID. Fixed-threshold 0.5 diagnostics are descriptive only and never drive selection.",
            "",
            "## 6. VALIDATION results and development ranking",
            "",
            "| Modality | Model | Candidate | VALIDATION ROC-AUC | VALIDATION PR-AUC/AP | Status |",
            "|---|---|---|---:|---:|---|",
            *rows,
            "",
            *(
                f"- {modality}: " + " > ".join(result["development_ranking"][modality])
                for modality in ("CODE", "PROCESS", "TEXT")
            ),
            "",
            "Selected for later controlled comparison: "
            + "; ".join(f"{key}={value}" for key, value in selected.items())
            + ".",
            "",
            "## 7. Leakage, temporal integrity, and reproducibility",
            "",
            "Exact `(project, commit_hash)` alignment, zero TRAIN/VALIDATION overlap, preserved targets, ancestor-only PROCESS provenance, TRAIN-only TEXT fitting, and TRAIN-only preprocessing were verified. The development loader exposes only TRAIN and VALIDATION and rejects TEST fail-closed.",
            "",
            "The complete workflow was run twice independently and the machine-readable result objects were identical. This establishes scientific/report reproducibility for the recorded runtime; byte-identical estimator serialization is not claimed because models are not persisted.",
            "",
            "## 8. Actions not performed",
            "",
            "No TEST predictive evaluation/selection/thresholding, TRAIN+VALIDATION refit, resampling, SMOTE, relabeling, membership change, calibration, fusion, stacking, XAI, SHAP, LIME, DiCE, pretrained download, semantic-code feature fabrication, commit, push, or PR creation was performed.",
            "",
            "## 9. Limitations and recommendation",
            "",
            *[f"- {item}" for item in result["limitations"]],
            "",
            "Sprint 10.8.2.26 should run a controlled CODE+TEXT TRAIN/VALIDATION comparison using only the selected frozen candidates. PROCESS should appear only as a prespecified weak-baseline ablation, not as an assumed contributor. Preserve identities and natural prevalence, predeclare fusion candidates, and keep TEST sealed. Calibration and XAI should remain outside that comparison unless separately frozen.",
            "",
        ]
    )


def main() -> None:
    configuration = json.loads(
        (
            ROOT / "configs/experiments/jit_defects4j_controlled_baselines_1.0.0.json"
        ).read_text()
    )
    inputs = load_development_inputs(ROOT)
    first = run_development_baselines(inputs, configuration)
    second = run_development_baselines(inputs, configuration)
    if first != second:
        raise RuntimeError("independent development runs were not identical")
    first["reproducibility"].update(
        {
            "independent_runs": 2,
            "machine_readable_results_identical": True,
            "selected_configuration_identical": True,
            "byte_identical_model_serialization_claimed": False,
        }
    )
    first.pop("results_identity_digest")
    first["results_identity_digest"] = (
        __import__("hashlib").sha256(canonical_bytes(first)).hexdigest()
    )
    output = ROOT / "audits/jit-defects4j-controlled-baselines/1.0.0"
    output.mkdir(parents=True, exist_ok=True)
    (output / "audit.json").write_bytes(canonical_bytes(first))
    (output / "REPORT.md").write_text(_report(first), encoding="utf-8")
    print(
        json.dumps(
            {
                "decision": first["decision"],
                "results_identity_digest": first["results_identity_digest"],
                "selected": first["selected_development_candidates"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
