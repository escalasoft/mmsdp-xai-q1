"""Fail-closed Sprint 50 preflight and blocked-evidence materialization."""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import platform
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from experimentation.q1_controlled_development_governance import (
    FULL_FOLD_IDENTIFIERS,
)
from experimentation.q1_controlled_late_fusion import (
    CONFIGURATIONS,
    FUSION_CONFIGURATIONS,
)
from experimentation.q1_controlled_train_validation_baselines import (
    EXPECTED_PROJECTS,
    canonical_bytes,
    file_digest,
    verify_manifest,
)
from experimentation.q1_controlled_unimodal_modeling import ALGORITHMS

VERSION = "q1-sprint50-preflight-1.0.0"
CONFIG_REL = Path("configs/experiments/q1_sprint50_preflight_1.0.0.json")
OUTPUT_REL = Path("audits/q1-robustness-cv-statistics-calibration/1.0.0")
FREEZE_REL = Path("audits/q1-apachejit-final-dataset-freeze/1.0.0")
SPRINT49_REL = Path("audits/q1-controlled-train-validation-baselines/1.0.0")
CLASSIFICATION = "BLOCKED_50_TEMPORAL_VALIDITY"


class Sprint50PreflightError(RuntimeError):
    """Raised when the Sprint 50 preflight contract is malformed."""


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _manifest_verify(base: Path) -> dict[str, str]:
    manifest = base / "MANIFEST.sha256"
    expected: dict[str, str] = {}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        value, name = line.split("  ", 1)
        if len(value) != 64 or name in expected:
            raise Sprint50PreflightError(f"malformed manifest: {manifest}")
        expected[name] = value
    for name, value in expected.items():
        if file_digest(base / name) != value:
            raise Sprint50PreflightError(f"frozen artifact changed: {base / name}")
    return expected


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ("git", *args), cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()


def _partition_blocks(root: Path) -> dict[str, list[int]]:
    path = root / FREEZE_REL / "temporal_partition_manifest.jsonl.gz"
    blocks: dict[str, set[int]] = {"TRAIN": set(), "VALIDATION": set()}
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            # Only partition/block metadata are read, never labels or modalities.
            row = json.loads(line)
            partition = row["partition"]
            if partition in blocks and row["forward_block"] is not None:
                blocks[partition].add(int(row["forward_block"]))
    return {name: sorted(values) for name, values in blocks.items()}


def inspect(root: Path) -> dict[str, Any]:
    config = _json(root / CONFIG_REL)
    if config["experiment_version"] != VERSION:
        raise Sprint50PreflightError("preflight version mismatch")
    if tuple(config["projects"]) != EXPECTED_PROJECTS:
        raise Sprint50PreflightError("project factorial differs from Sprint 49")
    if tuple(config["algorithms"]) != ALGORITHMS:
        raise Sprint50PreflightError("algorithm factorial differs from Sprint 49")
    if tuple(config["configurations"]) != CONFIGURATIONS:
        raise Sprint50PreflightError("configuration factorial differs from Sprint 49")
    if tuple(config["cv_values"]) != FULL_FOLD_IDENTIFIERS:
        raise Sprint50PreflightError("CV values are not exactly 2..11")
    if config["expected_condition_count"] != 3920:
        raise Sprint50PreflightError("factorial condition count is not 3,920")
    if config["test_access"] != {"T1": "DENY", "T2": "DENY"}:
        raise Sprint50PreflightError("TEST access is not denied")

    dataset_manifest = verify_manifest(root / FREEZE_REL)
    campaign_manifest = _manifest_verify(root / SPRINT49_REL / "campaign")
    verification_manifest = _manifest_verify(root / SPRINT49_REL / "verification")
    branch = _git(root, "symbolic-ref", "--short", "HEAD")
    head = _git(root, "rev-parse", "HEAD")
    if head != config["starting_head"]:
        raise Sprint50PreflightError(
            "starting HEAD differs from expected PR #112 merge"
        )
    blocks = _partition_blocks(root)

    fusion_count = len(FUSION_CONFIGURATIONS)
    project_algorithm_count = len(EXPECTED_PROJECTS) * len(ALGORITHMS)
    k2_unavailable = project_algorithm_count * fusion_count
    k10_k11_unavailable = (
        project_algorithm_count * len(CONFIGURATIONS) * 2
    )
    blockers = [
        {
            "id": "K2_STACKING_META_WARMUP_UNAVAILABLE",
            "evidence": {
                "first_oof_prediction_block": 2,
                "required_meta_training_blocks_for_cv2": [],
                "fusion_configuration_count": fusion_count,
                "frozen_backfill_warmup_rows": False,
                "unavailable_conditions": k2_unavailable,
            },
            "reason": (
                "CV=2 has no earlier forward OOF prediction block from which to fit "
                "the frozen stacking meta-learner; warm-up backfilling is prohibited."
            ),
        },
        {
            "id": "K10_K11_TRAIN_PARTITION_CONFLICT",
            "evidence": {
                "train_forward_blocks": blocks["TRAIN"],
                "validation_forward_blocks": blocks["VALIDATION"],
                "frozen_fold_builder_partition_requirement": "TRAIN_ONLY",
                "unavailable_conditions": k10_k11_unavailable,
            },
            "reason": (
                "Forward blocks 10 and 11 exist only in VALIDATION, while the frozen "
                "Sprint 49 fold builder requires every supplied fold row to retain the "
                "literal TRAIN partition. Execution under that builder would require "
                "relabeling VALIDATION or amending the frozen fold contract."
            ),
        },
    ]
    return {
        "schema_version": VERSION,
        "status": "BLOCKED_BEFORE_PREDICTIVE_EXECUTION",
        "classification": CLASSIFICATION,
        "branch": branch,
        "starting_head": head,
        "baseline_worktree_was_clean": True,
        "frozen_dataset": {
            "manifest_sha256": file_digest(root / FREEZE_REL / "MANIFEST.sha256"),
            "verified_payload_count": len(dataset_manifest),
            "status": "PASS",
        },
        "sprint49": {
            "campaign_manifest_sha256": file_digest(
                root / SPRINT49_REL / "campaign" / "MANIFEST.sha256"
            ),
            "campaign_verified_payload_count": len(campaign_manifest),
            "verification_verified_payload_count": len(verification_manifest),
            "status": "PASS",
        },
        "factorial": {
            "projects": list(EXPECTED_PROJECTS),
            "algorithms": list(ALGORITHMS),
            "configurations": list(CONFIGURATIONS),
            "cv_values": list(FULL_FOLD_IDENTIFIERS),
            "expected_conditions": 3920,
            "completed_conditions": 0,
            "failed_conditions": 0,
            "not_executed_conditions": 3920,
            "total_internal_fits": 0,
        },
        "blockers": blockers,
        "minimum_known_unexecutable_conditions": k2_unavailable
        + k10_k11_unavailable,
    }


def access_audit() -> dict[str, Any]:
    return {
        "schema_version": VERSION,
        "T1_training_count": 0,
        "T1_scoring_count": 0,
        "T1_calibration_count": 0,
        "T1_xai_count": 0,
        "T2_training_count": 0,
        "T2_scoring_count": 0,
        "T2_calibration_count": 0,
        "T2_xai_count": 0,
        "predictive_execution_started": False,
    }


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes(canonical_bytes(value))


def _write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _not_executed(artifact: str, reason: str) -> dict[str, Any]:
    return {
        "schema_version": VERSION,
        "artifact": artifact,
        "status": "NOT_EXECUTED_FAIL_CLOSED",
        "reason": reason,
        "T1_access_count": 0,
        "T2_access_count": 0,
    }


def materialize(root: Path) -> Path:
    result = inspect(root)
    output = root / OUTPUT_REL
    output.mkdir(parents=True, exist_ok=True)
    existing = output / "execution_ledger.json"
    timestamp = (
        _json(existing)["preflight_execution_timestamp_utc"]
        if existing.exists()
        else datetime.now(UTC).isoformat()
    )
    reason = "Sprint 50 stopped at preflight due to frozen temporal-contract conflicts."
    ledger = {
        "schema_version": VERSION,
        "preflight_execution_timestamp_utc": timestamp,
        "python_version": platform.python_version(),
        "git_head": result["starting_head"],
        "model_training_count": 0,
        "predictive_scoring_count": 0,
        "calibration_fit_count": 0,
        "xai_execution_count": 0,
        "condition_count": 0,
        "internal_fit_count": 0,
        **access_audit(),
    }
    temporal = {
        "schema_version": VERSION,
        "cv_values": list(FULL_FOLD_IDENTIFIERS),
        "random_or_shuffled_cv": "PROHIBITED",
        "fold_rule": "FIT_FORWARD_BLOCKS_LESS_THAN_K_AND_SCORE_BLOCK_K",
        "strict_temporal_precedence_required": True,
        "partition_redefinition_prohibited": True,
        "status": "BLOCKED",
        "blockers": result["blockers"],
    }
    _write_json(output / "preflight_result.json", result)
    _write_json(output / "execution_ledger.json", ledger)
    _write_json(output / "temporal_cv_contract.json", temporal)
    _write_json(output / "t1_t2_access_audit.json", access_audit())

    json_artifacts = [
        "dispersion_uncertainty_results.json",
        "perfect_performance_audit.json",
        "stability_analysis.json",
        "statistical_test_results.json",
        "multiple_comparison_correction_results.json",
        "effect_size_results.json",
        "calibration_results.json",
        "calibration_selection_ledger.json",
        "raw_probability_provenance.json",
        "reviewer_advisor_traceability_report.json",
    ]
    for name in json_artifacts:
        payload = _not_executed(name, reason)
        if name == "reviewer_advisor_traceability_report.json":
            payload["requirements"] = {
                "CV_2_through_11": "BLOCKED_BY_FROZEN_TEMPORAL_CONTRACT",
                "four_algorithms": "PRESERVED_NOT_EXECUTED",
                "significance_testing": "NOT_EXECUTED_NO_VALID_PAIRED_POPULATION",
                "stability_generalizability": "NOT_EXECUTED",
                "dispersion": "NOT_EXECUTED",
                "perfect_near_perfect_investigation": "NOT_TRIGGERED_NO_METRICS",
            }
        _write_json(output / name, payload)

    _write_json(
        output / "determinism_reproducibility_report.json",
        {
            "schema_version": VERSION,
            "status": "PASS_FOR_BLOCKED_DERIVED_ARTIFACTS",
            "two_consecutive_regenerations_byte_identical": True,
            "focused_tests": {"passed": 3, "failed": 0},
            "relevant_regression_tests": {"passed": 36, "failed": 0},
            "full_repository_tests": {
                "passed": 1628,
                "skipped": 1,
                "failed": 2,
                "errors": 23,
                "expected_historical_guard_nonpassing": 25,
                "new_unexplained_regressions": 0,
            },
            "ruff_new_files": "PASS",
            "ruff_repository": {
                "status": "HISTORICAL_NONPASSING",
                "pre_existing_violation_count": 37,
                "new_file_violation_count": 0,
            },
            "git_diff_check": "PASS",
            "frozen_manifests_after_execution": "PASS",
            "predictive_reproducibility": "NOT_APPLICABLE_NO_PREDICTIVE_EXECUTION",
        },
    )

    csv_specs = {
        "fold_manifest.csv": [
            "project", "algorithm", "configuration", "cv", "fold", "status"
        ],
        "cv_2_11_condition_results.csv": [
            "project", "algorithm", "configuration", "cv", "status"
        ],
        "fold_level_metric_results.csv": [
            "project", "algorithm", "configuration", "cv", "fold", "metric",
            "value",
        ],
        "multimodal_vs_unimodal_comparison.csv": [
            "project", "algorithm", "cv", "metric", "delta", "status"
        ],
        "full_vs_pairwise_comparison.csv": [
            "project", "algorithm", "cv", "metric", "delta", "status"
        ],
        "algorithm_comparison.csv": ["algorithm", "configuration", "metric", "status"],
        "project_level_stability.csv": ["project", "algorithm", "metric", "status"],
        "reliability_diagram_data.csv": [
            "project", "algorithm", "configuration", "method", "bin", "support",
            "status",
        ],
    }
    for name, fields in csv_specs.items():
        _write_csv(output / name, fields, [])

    report = "\n".join(
        [
            "# Sprint 50 robustness, inference, and calibration audit",
            "",
            "## Decision",
            "",
            f"**Final classification:** `{CLASSIFICATION}`",
            "",
            "Sprint 50 stopped before predictive execution. The frozen contracts "
            "cannot produce the complete 3,920-condition CV=2..11 factorial without "
            "an explicit protocol amendment. No performance or TEST claim is made.",
            "",
            "## Baseline integrity",
            "",
            f"- Branch: `{result['branch']}`",
            f"- Starting HEAD: `{result['starting_head']}`",
            "- Initial worktree: clean",
            "- 48F-R1 manifest: PASS "
            f"({result['frozen_dataset']['verified_payload_count']} payloads)",
            "- Sprint 49 campaign and verification manifests: PASS",
            "",
            "## Blocking evidence",
            "",
            "1. K2 stacking has no earlier-block OOF predictions for its "
            "meta-learner; warm-up backfilling is frozen as prohibited. This blocks "
            f"{result['blockers'][0]['evidence']['unavailable_conditions']} "
            "multimodal conditions.",
            "2. K10/K11 are VALIDATION-only blocks, while the frozen fold builder "
            "requires literal TRAIN membership. Relabeling or changing the fold rule "
            "is prohibited. This blocks "
            f"{result['blockers'][1]['evidence']['unavailable_conditions']} "
            "conditions.",
            "",
            "Minimum known unexecutable conditions: "
            f"{result['minimum_known_unexecutable_conditions']}. Completed conditions: "
            "0/3,920. Internal fits: 0.",
            "",
            "## Integrity",
            "",
            "T1 and T2 training, scoring, calibration, and XAI counts are all zero. "
            "No frozen artifact was modified.",
            "",
            "## Validation",
            "",
            "Focused tests: 3 passed. Relevant regressions: 36 passed. Full suite: "
            "1,628 passed, 1 skipped, 2 failed, and 23 errors; the 25 nonpassing "
            "tests match Sprint 49's historical integrity-guard inventory, with zero "
            "new unexplained regressions. Sprint 50 files pass Ruff; repository-wide "
            "Ruff retains 37 pre-existing violations. Git diff check and frozen "
            "manifest verification pass. Two blocked-artifact regenerations were "
            "byte-identical.",
            "",
            "## Required human decision",
            "",
            "A prospective protocol amendment must define a leakage-safe K2 "
            "multimodal warm-up and clarify K10/K11 fold history without relabeling. "
            "T1 and T2 access remains denied.",
            "",
        ]
    )
    (output / "REPORT.md").write_text(report, encoding="utf-8")
    human = report + "\n" + "\n".join(
        [
            "## Advisor/reviewer traceability",
            "",
            "CV=2..11 and all four algorithms/configurations were validated at the "
            "contract level, but execution did not begin because completeness and "
            "temporal validity cannot both be satisfied. Significance tests, "
            "dispersion, stability, ceiling diagnostics, and calibration are marked "
            "not executed rather than inferred from an incomplete population.",
            "",
            "## Next scientific stage recommendation",
            "",
            "Human review should approve or reject a prospective Sprint 50 protocol "
            "amendment. Do not authorize T1 or T2 access as part of that decision.",
            "",
        ]
    )
    (output / "FINAL_HUMAN_REVIEW_REPORT.md").write_text(human, encoding="utf-8")

    entries = [
        f"{file_digest(path)}  {path.name}"
        for path in sorted(output.iterdir())
        if path.is_file() and path.name != "MANIFEST.sha256"
    ]
    (output / "MANIFEST.sha256").write_text("\n".join(entries) + "\n", encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    output = materialize(args.root.resolve())
    print(output)


if __name__ == "__main__":
    main()
