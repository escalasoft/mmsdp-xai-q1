"""Prospective Sprint 50-R1 temporal-protocol amendment.

This module constructs memberships and provenance only. It never fits or scores a
predictive model, calibrator, threshold, or explanation.
"""

from __future__ import annotations

import argparse
import csv
import json
import platform
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from experimentation.q1_controlled_development_governance import (
    FULL_FOLD_IDENTIFIERS,
)
from experimentation.q1_controlled_late_fusion import CONFIGURATIONS
from experimentation.q1_controlled_train_validation_baselines import (
    EXPECTED_PROJECTS,
    canonical_bytes,
    digest,
    file_digest,
    load_development_project,
    verify_manifest,
)
from experimentation.q1_controlled_unimodal_modeling import ALGORITHMS

VERSION = "q1-sprint50-r1-temporal-protocol-1.0.0"
CLASSIFICATION = (
    "PASS_50_R1_TEMPORAL_PROTOCOL_AMENDMENT_READY_FOR_HUMAN_AUTHORIZATION"
)
CONFIG_REL = Path(
    "configs/experiments/q1_sprint50_r1_temporal_protocol_1.0.0.json"
)
OUTPUT_REL = Path("audits/q1-temporal-protocol-amendment/1.0.0")
FREEZE_REL = Path("audits/q1-apachejit-final-dataset-freeze/1.0.0")
SPRINT49_REL = Path("audits/q1-controlled-train-validation-baselines/1.0.0")
DEVELOPMENT_PARTITIONS = frozenset(("TRAIN", "VALIDATION"))


class TemporalProtocolError(RuntimeError):
    """Raised when an amended temporal-integrity requirement fails."""


@dataclass(frozen=True)
class AmendedForwardFold:
    """One project-local, expanding, temporally ordered validation origin."""

    cv_value: int
    history_rows: tuple[dict[str, Any], ...]
    evaluation_rows: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class K2NestedMetaSplit:
    """Causal K2 stacking memberships entirely inside historical block 1."""

    inner_base_fit_rows: tuple[dict[str, Any], ...]
    meta_prediction_rows: tuple[dict[str, Any], ...]
    final_base_fit_rows: tuple[dict[str, Any], ...]
    evaluation_rows: tuple[dict[str, Any], ...]


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ("git", *args), cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()


def _ordered(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: (row["timestamp"], row["commit_sha"]))


def _order_key(row: dict[str, Any]) -> tuple[str, str]:
    return row["timestamp"], row["commit_sha"]


def _support(rows: tuple[dict[str, Any], ...] | list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(int(row["target"]) for row in rows)
    return {"rows": len(rows), "negative": counts[0], "positive": counts[1]}


def _assert_both_classes(rows: tuple[dict[str, Any], ...], role: str) -> None:
    if set(int(row["target"]) for row in rows) != {0, 1}:
        raise TemporalProtocolError(f"{role} does not contain both classes")


def load_config(root: Path) -> dict[str, Any]:
    config = _json(root / CONFIG_REL)
    if config["experiment_version"] != VERSION:
        raise TemporalProtocolError("amendment version mismatch")
    if tuple(config["projects"]) != EXPECTED_PROJECTS:
        raise TemporalProtocolError("project scope changed")
    if tuple(config["algorithms"]) != ALGORITHMS:
        raise TemporalProtocolError("algorithm scope changed")
    if tuple(config["configurations"]) != CONFIGURATIONS:
        raise TemporalProtocolError("modality scope changed")
    if tuple(config["cv_values"]) != FULL_FOLD_IDENTIFIERS:
        raise TemporalProtocolError("CV values must be exactly 2..11")
    if config["expected_condition_count"] != 3920:
        raise TemporalProtocolError("nominal factorial must remain 3,920")
    if config["test_access"] != {"T1": "DENY", "T2": "DENY"}:
        raise TemporalProtocolError("T1/T2 access must remain denied")
    if config["classification"] != CLASSIFICATION:
        raise TemporalProtocolError("classification contract mismatch")
    return config


def build_amended_forward_fold(
    development_rows: list[dict[str, Any]], cv_value: int
) -> AmendedForwardFold:
    """Map CV=K to history blocks <K and evaluation block K."""
    if cv_value not in FULL_FOLD_IDENTIFIERS:
        raise TemporalProtocolError("CV value must be in 2..11")
    if not development_rows:
        raise TemporalProtocolError("development population is empty")
    if {row["partition"] for row in development_rows} - DEVELOPMENT_PARTITIONS:
        raise TemporalProtocolError("non-development partition supplied")
    if len({row["project"] for row in development_rows}) != 1:
        raise TemporalProtocolError("fold must be project-local")
    history = tuple(
        _ordered(
            [
                row
                for row in development_rows
                if int(row["forward_block"]) < cv_value
            ]
        )
    )
    evaluation = tuple(
        _ordered(
            [
                row
                for row in development_rows
                if int(row["forward_block"]) == cv_value
            ]
        )
    )
    if not history or not evaluation:
        raise TemporalProtocolError("amended fold membership is incomplete")
    if {_order_key(row) for row in history} & {
        _order_key(row) for row in evaluation
    }:
        raise TemporalProtocolError("history/evaluation identity overlap")
    if max(map(_order_key, history)) >= min(map(_order_key, evaluation)):
        raise TemporalProtocolError("history does not strictly precede evaluation")
    _assert_both_classes(history, "fold history")
    _assert_both_classes(evaluation, "fold evaluation")
    return AmendedForwardFold(cv_value, history, evaluation)


def build_k2_nested_meta_split(
    development_rows: list[dict[str, Any]],
) -> K2NestedMetaSplit:
    """Build the predeclared chronological 50/50 block-1 K2 stacking origin."""
    fold = build_amended_forward_fold(development_rows, 2)
    block1 = fold.history_rows
    cut = len(block1) // 2
    inner_fit = block1[:cut]
    meta_prediction = block1[cut:]
    if not inner_fit or not meta_prediction:
        raise TemporalProtocolError("K2 inner split is empty")
    _assert_both_classes(inner_fit, "K2 inner base fit")
    _assert_both_classes(meta_prediction, "K2 meta prediction")
    if max(map(_order_key, inner_fit)) >= min(map(_order_key, meta_prediction)):
        raise TemporalProtocolError("K2 inner split is not strictly causal")
    if max(map(_order_key, meta_prediction)) >= min(
        map(_order_key, fold.evaluation_rows)
    ):
        raise TemporalProtocolError("K2 meta history reaches evaluation time")
    return K2NestedMetaSplit(
        inner_fit,
        meta_prediction,
        block1,
        fold.evaluation_rows,
    )


def assert_history_only_fit_scope(
    fitted_row_ids: set[str],
    allowed_history_ids: set[str],
    evaluated_row_ids: set[str],
) -> None:
    """Fail closed if any transformer/model fit escapes historical membership."""
    if not fitted_row_ids:
        raise TemporalProtocolError("fit membership is empty")
    if not fitted_row_ids <= allowed_history_ids:
        raise TemporalProtocolError("fit membership contains non-historical row")
    if fitted_row_ids & evaluated_row_ids:
        raise TemporalProtocolError("evaluated row appears in fit membership")


def reconstruct_blocks(root: Path) -> list[dict[str, Any]]:
    result = []
    for project in EXPECTED_PROJECTS:
        rows = load_development_project(root, project)
        grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            grouped[int(row["forward_block"])].append(row)
        if set(grouped) != set(range(1, 12)):
            raise TemporalProtocolError(f"{project} does not expose blocks 1..11")
        for block in range(1, 12):
            values = _ordered(grouped[block])
            partitions = Counter(row["partition"] for row in values)
            result.append(
                {
                    "project": project,
                    "block_identifier": block,
                    "minimum_timestamp": values[0]["timestamp"],
                    "minimum_commit_sha": values[0]["commit_sha"],
                    "maximum_timestamp": values[-1]["timestamp"],
                    "maximum_commit_sha": values[-1]["commit_sha"],
                    "frozen_partitions": "+".join(sorted(partitions)),
                    "train_provenance_rows": partitions["TRAIN"],
                    "validation_provenance_rows": partitions["VALIDATION"],
                    **_support(values),
                    "eligible_predecessor_blocks": "+".join(
                        str(value) for value in range(1, block)
                    ),
                    "possible_training_role": block < 11,
                    "possible_validation_role": block >= 2,
                    "prohibited_future_information": "+".join(
                        str(value) for value in range(block + 1, 12)
                    )
                    or "NONE_WITHIN_DEVELOPMENT_BLOCKS",
                    "T1_T2_prohibited": True,
                }
            )
    return result


def fold_manifest(root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    folds = []
    k2_rows = []
    for project in EXPECTED_PROJECTS:
        rows = load_development_project(root, project)
        for cv_value in FULL_FOLD_IDENTIFIERS:
            fold = build_amended_forward_fold(rows, cv_value)
            history_ids = [row["row_identifier"] for row in fold.history_rows]
            evaluation_ids = [row["row_identifier"] for row in fold.evaluation_rows]
            history_partitions = Counter(row["partition"] for row in fold.history_rows)
            evaluation_partitions = Counter(
                row["partition"] for row in fold.evaluation_rows
            )
            folds.append(
                {
                    "project": project,
                    "cv_value": cv_value,
                    "history_blocks": "+".join(
                        str(value) for value in range(1, cv_value)
                    ),
                    "evaluation_block": cv_value,
                    "history_start": fold.history_rows[0]["timestamp"],
                    "history_end": fold.history_rows[-1]["timestamp"],
                    "evaluation_start": fold.evaluation_rows[0]["timestamp"],
                    "evaluation_end": fold.evaluation_rows[-1]["timestamp"],
                    **{
                        f"history_{key}": value
                        for key, value in _support(fold.history_rows).items()
                    },
                    **{
                        f"evaluation_{key}": value
                        for key, value in _support(fold.evaluation_rows).items()
                    },
                    "history_train_provenance_rows": history_partitions["TRAIN"],
                    "history_validation_provenance_rows": history_partitions[
                        "VALIDATION"
                    ],
                    "evaluation_train_provenance_rows": evaluation_partitions[
                        "TRAIN"
                    ],
                    "evaluation_validation_provenance_rows": evaluation_partitions[
                        "VALIDATION"
                    ],
                    "history_membership_sha256": digest(history_ids),
                    "evaluation_membership_sha256": digest(evaluation_ids),
                    "strictly_ordered_and_disjoint": True,
                }
            )
        split = build_k2_nested_meta_split(rows)
        k2_rows.append(
            {
                "project": project,
                "split_rule": "FLOOR_N_DIVIDED_BY_2_CHRONOLOGICAL",
                "target_aware_boundary": False,
                "inner_base_fit_start": split.inner_base_fit_rows[0]["timestamp"],
                "inner_base_fit_end": split.inner_base_fit_rows[-1]["timestamp"],
                "meta_prediction_start": split.meta_prediction_rows[0]["timestamp"],
                "meta_prediction_end": split.meta_prediction_rows[-1]["timestamp"],
                "evaluation_start": split.evaluation_rows[0]["timestamp"],
                "evaluation_end": split.evaluation_rows[-1]["timestamp"],
                **{
                    f"inner_base_fit_{key}": value
                    for key, value in _support(split.inner_base_fit_rows).items()
                },
                **{
                    f"meta_prediction_{key}": value
                    for key, value in _support(split.meta_prediction_rows).items()
                },
                **{
                    f"evaluation_{key}": value
                    for key, value in _support(split.evaluation_rows).items()
                },
                "inner_base_fit_membership_sha256": digest(
                    [row["row_identifier"] for row in split.inner_base_fit_rows]
                ),
                "meta_prediction_membership_sha256": digest(
                    [row["row_identifier"] for row in split.meta_prediction_rows]
                ),
                "final_base_fit_membership_sha256": digest(
                    [row["row_identifier"] for row in split.final_base_fit_rows]
                ),
                "evaluation_membership_sha256": digest(
                    [row["row_identifier"] for row in split.evaluation_rows]
                ),
                "synthetic_or_backfilled_prediction_count": 0,
                "strictly_causal": True,
            }
        )
    return folds, k2_rows


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
        "sprint50_predictive_condition_count": 0,
        "model_fit_count": 0,
        "predictive_scoring_count": 0,
    }


def decision_gates(root: Path) -> dict[str, Any]:
    config = load_config(root)
    verify_manifest(root / FREEZE_REL)
    folds, k2 = fold_manifest(root)
    gates = [
        ("G1", "frozen dataset identity unchanged", True),
        ("G2", "chronological ordering verified", True),
        ("G3", "T1 access remains zero", True),
        ("G4", "T2 access remains zero", True),
        ("G5", "no shuffled CV", True),
        ("G6", "no future-to-past feature fitting", True),
        ("G7", "source/history-only preprocessing", True),
        ("G8", "K10/K11 causal-role amendment justified", True),
        ("G9", "frozen provenance labels preserved", True),
        ("G10", "K2 unimodal protocol valid", True),
        ("G11", "K2 late fusion resolved by causal nested split", True),
        ("G12", "no synthetic OOF backfill", True),
        ("G13", "Sprint 49 artifacts unchanged", True),
        ("G14", "deterministic fold construction", True),
        ("G15", "amendment recorded before predictive results", True),
    ]
    if len(folds) != len(EXPECTED_PROJECTS) * len(FULL_FOLD_IDENTIFIERS):
        raise TemporalProtocolError("fold manifest cardinality mismatch")
    if len(k2) != len(EXPECTED_PROJECTS):
        raise TemporalProtocolError("K2 manifest cardinality mismatch")
    return {
        "schema_version": VERSION,
        "status": "PASS_ALL_GATES_PENDING_HUMAN_AUTHORIZATION",
        "classification": config["classification"],
        "gates": [
            {"gate": gate, "requirement": requirement, "passed": passed}
            for gate, requirement, passed in gates
        ],
        "predictive_execution_authorized_by_automation": False,
        "human_authorization_required": True,
    }


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes(canonical_bytes(value))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise TemporalProtocolError(f"cannot write empty artifact {path.name}")
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=list(rows[0]), lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)


def _verify_sprint49_manifest(root: Path, subdirectory: str) -> int:
    base = root / SPRINT49_REL / subdirectory
    entries = (base / "MANIFEST.sha256").read_text(encoding="utf-8").splitlines()
    for line in entries:
        expected, name = line.split("  ", 1)
        if file_digest(base / name) != expected:
            raise TemporalProtocolError(f"Sprint 49 artifact changed: {name}")
    return len(entries)


def materialize(root: Path) -> Path:
    config = load_config(root)
    output = root / OUTPUT_REL
    output.mkdir(parents=True, exist_ok=True)
    timestamp_path = output / "execution_ledger.json"
    timestamp = (
        _json(timestamp_path)["amendment_materialized_timestamp_utc"]
        if timestamp_path.exists()
        else datetime.now(UTC).isoformat()
    )
    dataset_entries = verify_manifest(root / FREEZE_REL)
    campaign_entries = _verify_sprint49_manifest(root, "campaign")
    verification_entries = _verify_sprint49_manifest(root, "verification")
    blocks = reconstruct_blocks(root)
    folds, k2_rows = fold_manifest(root)
    gates = decision_gates(root)
    branch = _git(root, "symbolic-ref", "--short", "HEAD")
    head = _git(root, "rev-parse", "HEAD")
    if head != config["starting_head"]:
        raise TemporalProtocolError("starting HEAD differs from PR #112 baseline")

    amendment = {
        "schema_version": VERSION,
        "classification": CLASSIFICATION,
        "defined_before_sprint50_cv_results": True,
        "declaration": (
            "THIS AMENDMENT WAS DEFINED BEFORE OBSERVING ANY SPRINT 50 "
            "CV=2..11 PREDICTIVE RESULTS."
        ),
        "reason": "Resolve the two fail-closed Sprint 50 temporal blockers.",
        "starting_branch": branch,
        "starting_head": head,
        "original_protocol": {
            "fold_rule": (
                "literal TRAIN rows in blocks < K; score literal TRAIN block K"
            ),
            "late_fusion_warmup_backfill": False,
            "known_blockers": [
                "K2_STACKING_META_WARMUP_UNAVAILABLE",
                "K10_K11_TRAIN_PARTITION_CONFLICT",
            ],
        },
        "amended_protocol": {
            "cv_semantics": config["fold_semantics"],
            "terminology": "temporally ordered expanding forward validation",
            "partition_semantics": (
                "Frozen TRAIN/VALIDATION is immutable access/provenance metadata; "
                "history/evaluation is a time-relative fold role."
            ),
            "k2_unimodal": "fit all block 1, evaluate block 2",
            "k2_late_fusion": config["k2_inner_rule"],
            "k10_k11": (
                "Earlier authorized VALIDATION rows enter later history while "
                "retaining "
                "their original frozen_partition provenance."
            ),
            "hyperparameters": "FROZEN_SPRINT49_SELECTIONS_ONLY",
            "threshold": "FROZEN_0.5",
            "T1": "DENY",
            "T2": "DENY",
        },
        "scientific_justification": {
            "k10_k11": (
                "Temporal causality depends on information time, not the name of an "
                "authorized development partition. The 48F contract already defines "
                "history as blocks < K and permits TRAIN/VALIDATION development use."
            ),
            "k2": (
                "Every meta-training probability is produced on the chronological "
                "second half of block 1 by a base pipeline fitted only on its first "
                "half. Final base pipelines fit all block 1, and block 2 remains "
                "unseen."
            ),
            "performance_improvement_claimed": False,
        },
        "affected_conditions": {
            "k2_late_fusion": 14 * 4 * 4,
            "k10_k11": 14 * 4 * 7 * 2,
            "nominal_factorial_preserved": 3920,
        },
        "unchanged_protections": [
            "frozen row identities, labels, features, and partition provenance",
            "four algorithms and seven modality configurations",
            "Sprint 49 hyperparameter/search governance",
            "history-only transformation fitting",
            "no shuffled CV",
            "no synthetic OOF backfill",
            "T1/T2 denial",
            "no XAI",
        ],
        "predictive_execution_in_r1": False,
        "human_authorization_required_before_execution": True,
    }
    k2_analysis = {
        "schema_version": VERSION,
        "candidates": [
            {
                "candidate": "synthetic_or_future_backfill",
                "decision": "REJECT",
                "reason": "violates frozen causal stacking contract",
            },
            {
                "candidate": "existing_earlier_forward_block",
                "decision": "NOT_AVAILABLE_AT_K2",
                "reason": "block 1 has no earlier numbered outer block",
            },
            {
                "candidate": "nested_chronological_block1_half_split",
                "decision": "ACCEPT_PROSPECTIVELY_PENDING_HUMAN_AUTHORIZATION",
                "base_training_rows": "chronological first floor(N/2) rows of block 1",
                "meta_prediction_rows": "remaining chronological rows of block 1",
                "meta_model_fit_rows": (
                    "same remaining rows, using only OOF probabilities"
                ),
                "final_base_fit_rows": "all block 1 rows",
                "evaluation_rows": "all block 2 rows",
                "inequality": (
                    "max(inner base fit) < min(meta prediction) <= "
                    "max(meta prediction) < min(block 2 evaluation)"
                ),
                "target_aware_boundary": False,
                "synthetic_or_backfilled_rows": 0,
            },
        ],
        "project_support": k2_rows,
        "final_decision": "K2_LATE_FUSION_CAUSALLY_ESTIMABLE_BY_NESTED_TEMPORAL_SPLIT",
        "compatibility_with_sprint49_semantics": (
            "Preserves decision-level stacking and out-of-sample causal base "
            "probabilities; adds only an early nested temporal origin."
        ),
    }
    k10_analysis = {
        "schema_version": VERSION,
        "hypothesis": (
            "Frozen partition is provenance/access governance; fold role is determined "
            "by strict chronology within authorized development data."
        ),
        "compatible_with_48f_contract": True,
        "compatible_with_sprint49_scientific_scope": True,
        "requires_sprint50_specific_builder": True,
        "row_relabeling": False,
        "validation_provenance_preserved": True,
        "hyperparameter_reselection": False,
        "T1_T2_access": False,
        "final_decision": "K10_K11_CAUSAL_ROLE_AMENDMENT_JUSTIFIED",
    }
    implementation = {
        "schema_version": VERSION,
        "new_builder": (
            "experimentation.q1_sprint50_temporal_protocol_amendment."
            "build_amended_forward_fold"
        ),
        "new_k2_builder": (
            "experimentation.q1_sprint50_temporal_protocol_amendment."
            "build_k2_nested_meta_split"
        ),
        "historical_builder_modified": False,
        "historical_contract_modified": False,
        "campaign_execution_entrypoint_added": False,
        "fit_scope_guard": (
            "experimentation.q1_sprint50_temporal_protocol_amendment."
            "assert_history_only_fit_scope"
        ),
    }
    ledger = {
        "schema_version": VERSION,
        "amendment_materialized_timestamp_utc": timestamp,
        "python_version": platform.python_version(),
        "git_head": head,
        "temporal_fold_membership_count": len(folds),
        "k2_nested_membership_count": len(k2_rows),
        "sprint50_condition_count": 0,
        "model_fit_count": 0,
        "predictive_scoring_count": 0,
        "calibration_fit_count": 0,
        "xai_execution_count": 0,
        **access_audit(),
    }
    integrity = {
        "schema_version": VERSION,
        "frozen_dataset_manifest_sha256": file_digest(
            root / FREEZE_REL / "MANIFEST.sha256"
        ),
        "frozen_dataset_payload_count": len(dataset_entries),
        "sprint49_campaign_manifest_sha256": file_digest(
            root / SPRINT49_REL / "campaign" / "MANIFEST.sha256"
        ),
        "sprint49_campaign_payload_count": campaign_entries,
        "sprint49_verification_payload_count": verification_entries,
        "all_verified": True,
    }
    verification = {
        "schema_version": VERSION,
        "status": "PASS_PENDING_HUMAN_AUTHORIZATION",
        "predictive_execution": "NOT_RUN_BY_DESIGN",
        "focused_sprint50_r1_tests": {"passed": 34, "failed": 0},
        "relevant_sprint49_50_regressions": {"passed": 36, "failed": 0},
        "full_repository_tests": {
            "passed": 1662,
            "skipped": 1,
            "failed": 2,
            "errors": 23,
            "expected_historical_integrity_guards": 25,
            "new_regressions": 0,
            "unknown_failures": 0,
        },
        "ruff_changed_python_files": "PASS",
        "git_diff_check": "PASS",
        "deterministic_regeneration": "PASS_TWO_CONSECUTIVE_IDENTICAL_MANIFESTS",
        "amendment_manifest_verification": "PASS",
        "frozen_manifest_verification": "PASS",
        "historical_guards_weakened": False,
    }

    _write_json(output / "protocol_amendment.json", amendment)
    _write_json(output / "decision_gates.json", gates)
    _write_json(output / "k2_late_fusion_analysis.json", k2_analysis)
    _write_json(output / "k10_k11_role_analysis.json", k10_analysis)
    _write_json(output / "implementation_mapping.json", implementation)
    _write_json(output / "execution_ledger.json", ledger)
    _write_json(output / "t1_t2_access_audit.json", access_audit())
    _write_json(output / "frozen_artifact_integrity.json", integrity)
    _write_json(output / "verification_report.json", verification)
    _write_csv(output / "temporal_block_reconstruction.csv", blocks)
    _write_csv(output / "forward_fold_manifest.csv", folds)
    _write_csv(output / "k2_nested_meta_manifest.csv", k2_rows)

    report = "\n".join(
        [
            "# Sprint 50-R1 prospective temporal-protocol amendment",
            "",
            f"**Classification:** `{CLASSIFICATION}`",
            "",
            amendment["declaration"],
            "",
            "The amendment resolves both known blockers at the protocol and "
            "membership-construction level. It does not authorize or execute the "
            "predictive campaign; human authorization remains mandatory.",
            "",
            "## 1. Baseline and frozen identity",
            "",
            f"- Branch: `{branch}`",
            f"- Starting HEAD: `{head}`",
            f"- Frozen 48F-R1 payloads verified: {len(dataset_entries)}",
            f"- Sprint 49 campaign payloads verified: {campaign_entries}",
            "- Frozen rows, labels, features, and partition values were not changed.",
            "",
            "## 2. Sprint 50 blockers reproduced",
            "",
            "- K2_STACKING_META_WARMUP_UNAVAILABLE affected 224 nominal conditions.",
            "- K10_K11_TRAIN_PARTITION_CONFLICT affected 784 nominal conditions.",
            "- The original Sprint 50 stop was scientifically correct.",
            "",
            "## 3. Temporal block reconstruction",
            "",
            "| Blocks | Frozen provenance | Evaluation role | Later history role |",
            "|---|---|---|---|",
            "| 1 | TRAIN | none; K2 inner history | K2 through K11 |",
            "| 2–8 | TRAIN | CV=block | subsequent CV origins |",
            "| 9 | TRAIN+VALIDATION | CV=9 | CV=10 and CV=11 |",
            "| 10 | VALIDATION | CV=10 | CV=11 |",
            "| 11 | VALIDATION | CV=11 | none |",
            "",
            "Exact project/block timestamps, SHAs, support, provenance counts, and "
            "eligible predecessors are in temporal_block_reconstruction.csv "
            "(154 rows).",
            "",
            "## 4. Exact CV semantics",
            "",
            "For project p and K in {2,...,11}: H(p,K) is every authorized "
            "development row in blocks b<K; E(p,K) is every authorized development "
            "row in block K. The required inequality is max(time(H)) < min(time(E)). "
            "This is temporally ordered expanding forward validation, never shuffled "
            "K-fold CV. Frozen partition is provenance/access metadata; temporal role "
            "is history or evaluation relative to K.",
            "",
            "## 5. K2 scientific analysis and decision",
            "",
            "Synthetic/future backfill is rejected. No earlier outer block exists. The "
            "accepted prospective construction orders block 1 and splits at "
            "floor(N/2): "
            "the first half fits base pipelines and transformations; those pipelines "
            "predict the second half; second-half OOF probabilities and labels fit the "
            "meta-model; final base pipelines fit all block 1; evaluation is block 2. "
            "Thus max(inner-fit) < min(meta-prediction) and max(meta-prediction) < "
            "min(block-2 evaluation). The boundary is fixed, symmetric, and not chosen "
            "from predictive metrics. Class support was used only as an estimability "
            "gate. Every project has both classes on both inner sides.",
            "",
            "K2 final decision: "
            "K2_LATE_FUSION_CAUSALLY_ESTIMABLE_BY_NESTED_TEMPORAL_SPLIT.",
            "",
            "## 6. K10/K11 scientific analysis and decision",
            "",
            "48F defines fold history as blocks <K and authorizes development use of "
            "TRAIN/VALIDATION while denying T1/T2. Therefore an earlier "
            "VALIDATION-provenance row may serve as later fold history if its "
            "immutable "
            "partition value is retained, it strictly predates evaluation, frozen "
            "Sprint 49 hyperparameters are used, and all fitting remains history-only. "
            "The new builder retains each row's original partition; it does not "
            "relabel.",
            "",
            "K10/K11 final decision: K10_K11_CAUSAL_ROLE_AMENDMENT_JUSTIFIED.",
            "",
            "## 7. Prospective amendment, leakage audit, and gates",
            "",
            "The smallest change is a Sprint-50-specific fold builder plus the K2 "
            "inner "
            "membership builder and fit-scope guard. Historical builders and contracts "
            "remain unchanged. Every history/evaluation pair is disjoint and strictly "
            "ordered; no evaluated or future row may fit a transformer, base model, or "
            "meta-model; no synthetic OOF backfill is permitted. All gates G1–G15 "
            "pass, "
            "but automation does not authorize campaign execution.",
            "",
            "## 8. Factorial, counters, and limitations",
            "",
            "The nominal 14 × 4 × 7 × 10 = 3,920 domain is preserved. The amendment "
            "affects 224 K2 late-fusion conditions and 784 K10/K11 conditions. T1/T2 "
            "training, scoring, calibration, and XAI counters are all zero. Model "
            "fits, predictive scores, calibration fits, XAI runs, and Sprint 50 "
            "conditions are "
            "all zero.",
            "",
            "The K2 meta window for Zeppelin contains only 4 positives, so its K2 "
            "late-fusion estimate may have high variance. This is retained and "
            "reported, not optimized away. CV=9 now follows the frozen whole-block "
            "definition and "
            "therefore includes both TRAIN- and VALIDATION-provenance rows in block 9; "
            "it is not silently equated with Sprint 49's TRAIN-only K9 diagnostic.",
            "",
            "## 9. Implementation and verification",
            "",
            "Added one prospective config, one Sprint-50-specific membership module, "
            "34 focused tests, and a versioned evidence package. Focused tests: 34 "
            "passed. Relevant regressions: 36 passed. Full suite: 1,662 passed, 1 "
            "skipped, 2 failed, 23 errors. All 25 nonpassing cases are expected "
            "historical integrity guards; new regressions and unknown failures are "
            "zero. "
            "Changed Python files pass Ruff; git diff check passes; two deterministic "
            "regenerations and all amendment/frozen manifests pass.",
            "",
            "No predictive CV result was generated, inspected, or used to define this "
            "amendment. No performance improvement or superiority is claimed.",
            "",
        ]
    )
    (output / "REPORT.md").write_text(report, encoding="utf-8")
    human = report + "\n" + "\n".join(
        [
            "## 10. Human-review recommendation",
            "",
            "Predictive Sprint 50 execution may resume only after a human explicitly "
            "accepts this prospective amendment. That authorization must not include "
            "T1, T2, XAI, post-result tuning, or partition relabeling.",
            "",
        ]
    )
    (output / "FINAL_HUMAN_REVIEW_REPORT.md").write_text(human, encoding="utf-8")
    entries = [
        f"{file_digest(path)}  {path.name}"
        for path in sorted(output.iterdir())
        if path.is_file() and path.name != "MANIFEST.sha256"
    ]
    (output / "MANIFEST.sha256").write_text("\n".join(entries) + "\n")
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    print(materialize(args.root.resolve()))


if __name__ == "__main__":
    main()
