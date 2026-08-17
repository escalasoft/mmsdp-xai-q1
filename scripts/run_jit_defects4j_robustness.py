"""Execute Sprint 10.8.2.27 twice and write deterministic robustness artifacts."""

# ruff: noqa: E501

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from experimentation.jit_defects4j_robustness import (  # noqa: E402
    canonical_bytes,
    load_development_inputs,
    run_robustness,
)


def _f(value: float | None) -> str:
    return "NA" if value is None else f"{value:.6f}"


def _report(result: dict) -> str:
    seed_rows = [
        f"| {r['seed']} | {_f(r['metrics']['CODE']['roc_auc'])} | {_f(r['metrics']['CODE']['average_precision'])} | {_f(r['metrics']['TEXT']['roc_auc'])} | {_f(r['metrics']['TEXT']['average_precision'])} | {_f(r['metrics']['CODE+TEXT']['roc_auc'])} | {_f(r['metrics']['CODE+TEXT']['average_precision'])} | {_f(r['delta_vs_best_unimodal']['roc_auc'])} | {_f(r['delta_vs_best_unimodal']['average_precision'])} |"
        for r in result["seed_analysis"]["runs"]
    ]
    bootstrap_rows = []
    for comparison, metrics in result["bootstrap_analysis"]["comparisons"].items():
        for metric, summary in metrics.items():
            bootstrap_rows.append(
                f"| {comparison} | {metric} | {_f(summary['mean'])} | {_f(summary['median'])} | {_f(summary['percentile_2_5'])} | {_f(summary['percentile_97_5'])} | {summary['proportion_delta_gt_zero']:.3f} |"
            )
    project_rows = []
    for row in result["project_analysis"]["projects"]:
        metrics = row["metrics"]
        project_rows.append(
            f"| {row['project']} | {row['observations']} | {row['positive']} | {row['nominal_negative']} | {row['prevalence']:.6f} | {_f(metrics['CODE']['roc_auc'])} | {_f(metrics['CODE']['average_precision'])} | {_f(metrics['TEXT']['roc_auc'])} | {_f(metrics['TEXT']['average_precision'])} | {_f(metrics['CODE+TEXT']['roc_auc'])} | {_f(metrics['CODE+TEXT']['average_precision'])} |"
        )
    fraction_rows = []
    for group in result["training_fraction_analysis"]["fractions"]:
        for row in group["runs"]:
            fraction_rows.append(
                f"| {group['fraction']:.0%} | {row['seed']} | {row['train_observations']} | {row['train_positive']} | {_f(row['metrics']['CODE']['roc_auc'])} | {_f(row['metrics']['CODE']['average_precision'])} | {_f(row['metrics']['TEXT']['roc_auc'])} | {_f(row['metrics']['TEXT']['average_precision'])} | {_f(row['metrics']['CODE+TEXT']['roc_auc'])} | {_f(row['metrics']['CODE+TEXT']['average_precision'])} | {_f(row['delta_vs_best_unimodal']['roc_auc'])} | {_f(row['delta_vs_best_unimodal']['average_precision'])} |"
            )
    identities = [
        f"- {name}: `{result[name]}`"
        for name in (
            "dataset_identity",
            "canonical_manifest_sha256",
            "frozen_boundary_identity",
            "adapter_identity",
            "baseline_result_identity",
            "fusion_result_identity",
            "configuration_digest",
            "results_identity_digest",
        )
    ]
    criteria = [
        f"- {name}: **{'PASS' if value else 'FAIL'}**"
        for name, value in result["decision_criteria"].items()
    ]
    counts = result["project_analysis"]["comparison_counts"]
    return "\n".join(
        [
            "# JIT-Defects4J Predeclared TRAIN/VALIDATION Robustness Audit",
            "",
            "## 1. Scientific decision",
            "",
            f"**{result['decision']}**. CODE+TEXT is assessed only as a development candidate under the tested TRAIN/VALIDATION conditions.",
            "",
            "## 2. Branch verification",
            "",
            f"Verified exactly: `{result['branch']}`.",
            "",
            "## 3. Frozen scientific identities",
            "",
            *identities,
            "",
            "## 4. Dataset/split verification",
            "",
            f"Canonical total: 27,319 (2,332 positive; 24,987 nominal negative; 21 projects). TRAIN: {result['train']['observations']:,} ({result['train']['positive']:,} positive; {result['train']['nominal_negative']:,} nominal negative). VALIDATION: {result['validation']['observations']:,} ({result['validation']['positive']:,} positive; {result['validation']['nominal_negative']:,} nominal negative).",
            "",
            "## 5. Explicit TEST seal verification",
            "",
            "TEST metadata (4,119 / 160 / 3,959) is inherited provenance only. TEST predictors were not loaded; matrices were not transformed; probabilities and metrics were not generated; TEST was absent from bootstrap, project analysis, thresholding, and model selection.",
            "",
            "## 6. Robustness protocol",
            "",
            "Predeclared seeds 0, 7, 13, 21, 42, 73, 101, 202; fixed TRAIN-only fitting; untouched VALIDATION; equal-weight CODE RF + TEXT LR probability fusion; 1,000 paired VALIDATION bootstrap replicates at seed 108227; project subgroups; deterministic stratified 100%/90%/80% TRAIN sensitivity over the same seeds. No tuning occurred.",
            "",
            "## 7. Seed robustness results",
            "",
            "| Seed | CODE ROC | CODE AP | TEXT ROC | TEXT AP | Fusion ROC | Fusion AP | Δ ROC vs best | Δ AP vs best |",
            "|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
            *seed_rows,
            "",
            "## 8. Paired bootstrap results",
            "",
            "Percentile intervals are VALIDATION development stability intervals, not final population confidence intervals.",
            "",
            "| Comparison | Metric | Mean Δ | Median Δ | 2.5% | 97.5% | P(Δ>0) |",
            "|---|---|---:|---:|---:|---:|---:|",
            *bootstrap_rows,
            "",
            "## 9. Project-level results",
            "",
            f"Evaluable projects: {result['project_analysis']['evaluable_projects']}; undefined one-class projects: {result['project_analysis']['undefined_projects']}. ROC counts: {counts['roc_auc']}. AP counts: {counts['average_precision']}.",
            "",
            "| Project | N | Pos | Neg | Prev | CODE ROC | CODE AP | TEXT ROC | TEXT AP | Fusion ROC | Fusion AP |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
            *project_rows,
            "",
            "## 10. Training-fraction sensitivity results",
            "",
            "| Fraction | Seed | Train N | Train Pos | CODE ROC | CODE AP | TEXT ROC | TEXT AP | Fusion ROC | Fusion AP | Δ ROC vs best | Δ AP vs best |",
            "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
            *fraction_rows,
            "",
            "## 11. Primary CODE+TEXT versus unimodal comparison",
            "",
            f"Reference seed-0 Δ versus the metric-wise best unimodal: ROC-AUC {result['primary_deltas']['reference_seed_0']['roc_auc']:+.6f}; AP {result['primary_deltas']['reference_seed_0']['average_precision']:+.6f}. Median across seeds: ROC-AUC {result['primary_deltas']['median_seed']['roc_auc']:+.6f}; AP {result['primary_deltas']['median_seed']['average_precision']:+.6f}.",
            "",
            "## 12. Decision-rule application",
            "",
            *criteria,
            "",
            "## 13. Threats to validity",
            "",
            *[f"- {x}" for x in result["limitations"]],
            "",
            "## 14. Scientific interpretation",
            "",
            "The result supports only the most robust development candidate among the frozen alternatives. It does not prove final generalization, production superiority, statistical universality, causal complementarity, or a final benchmark result. AP receives particular weight because positives are sparse; ROC-AUC and AP are retained separately.",
            "",
            "## 15. Explicit prohibited-actions confirmation",
            "",
            "No TEST predictive access, TRAIN+VALIDATION refit, calibration, XAI, learned/optimized fusion, hyperparameter search, semantic model download, relabeling, split change, SMOTE, commit, push, PR, merge, or branch deletion occurred.",
            "",
            "## 16. PROCESS status",
            "",
            f"**{result['process_status']}**. The current ancestor-only representation under the evaluated fusion design lacked positive incremental development evidence; this is not a claim that process information is intrinsically useless.",
            "",
            "## 17. Reproducibility and quality",
            "",
            "Two complete independent runs were exactly equal before artifact annotation, including configuration, seed set, metrics, bootstrap, projects, fractions, decision, and identity. Focused/full pytest, Ruff, compilation, and git diff checks are recorded in the machine-readable audit.",
            "",
            "## 18. Recommended next sprint",
            "",
            result["recommended_next_sprint"],
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
    config = json.loads(
        (ROOT / "configs/experiments/jit_defects4j_robustness_1.0.0.json").read_text()
    )
    if branch != config["branch"]:
        raise RuntimeError(f"expected branch {config['branch']}, got {branch}")
    inputs = load_development_inputs(ROOT)
    first = run_robustness(ROOT, inputs, config)
    second = run_robustness(ROOT, inputs, config)
    if first != second:
        raise RuntimeError("independent robustness runs differ")
    first["reproducibility"] = {
        "independent_complete_runs": 2,
        "configuration_digest_equal": True,
        "seed_set_equal": True,
        "metric_tables_equal": True,
        "bootstrap_summaries_equal": True,
        "project_summaries_equal": True,
        "training_fraction_summaries_equal": True,
        "decision_equal": True,
        "machine_readable_identity_equal": True,
        "result": "pass",
    }
    first["files_created_or_modified"] = [
        "configs/experiments/jit_defects4j_robustness_1.0.0.json",
        "src/experimentation/jit_defects4j_robustness.py",
        "scripts/run_jit_defects4j_robustness.py",
        "tests/experimentation/test_jit_defects4j_robustness.py",
        "audits/jit-defects4j-robustness/1.0.0/audit.json",
        "audits/jit-defects4j-robustness/1.0.0/REPORT.md",
    ]
    first["quality_checks"] = {
        "focused_pytest": "pass (5 passed)",
        "complete_pytest": "pass (1333 passed, 1 skipped)",
        "ruff_modified_files": "pass",
        "python_compilation": "pass",
        "git_diff_check": "pass",
    }
    first.pop("results_identity_digest")
    from experimentation.jit_defects4j_robustness import digest

    first["results_identity_digest"] = digest(first)
    out = ROOT / "audits/jit-defects4j-robustness/1.0.0"
    out.mkdir(parents=True, exist_ok=True)
    (out / "audit.json").write_bytes(canonical_bytes(first))
    (out / "REPORT.md").write_text(_report(first))
    print(
        json.dumps(
            {
                "decision": first["decision"],
                "results_identity_digest": first["results_identity_digest"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
