"""Leakage-controlled decision-level late fusion for the Sprint 49 campaign."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.linear_model import LogisticRegression

from experimentation.q1_controlled_train_validation_baselines import (
    EXPECTED_PROJECTS,
    canonical_bytes,
    digest,
    file_digest,
    load_development_project,
)
from experimentation.q1_controlled_unimodal_modeling import (
    ALGORITHMS,
    MODALITIES,
    fit_unimodal,
    predict_positive_probability,
)
from experimentation.q1_controlled_unimodal_modeling import (
    load_config as load_unimodal_config,
)

VERSION = "q1-controlled-late-fusion-1.0.0"
CONFIG_REL = Path("configs/experiments/q1_controlled_late_fusion_1.0.0.json")
OUTPUT_REL = Path(
    "audits/q1-controlled-train-validation-baselines/1.0.0/late_fusion_contract"
)
CONFIGURATIONS = ("C", "P", "T", "C+P", "C+T", "P+T", "C+P+T")
FUSION_CONFIGURATIONS = {
    "C+P": ("C", "P"),
    "C+T": ("C", "T"),
    "P+T": ("P", "T"),
    "C+P+T": ("C", "P", "T"),
}


class LateFusionContractError(RuntimeError):
    """Raised when causal stacking or configuration identity is violated."""


@dataclass(frozen=True)
class OOFMetaTable:
    """Causally valid modality-probability table built from TRAIN only."""

    row_identifiers: tuple[str, ...]
    targets: np.ndarray
    probabilities: np.ndarray
    warmup_row_identifiers: tuple[str, ...]
    fold_lineage: tuple[dict[str, Any], ...]


def load_config(root: Path) -> dict[str, Any]:
    config = json.loads((root / CONFIG_REL).read_text(encoding="utf-8"))
    if config["experiment_version"] != VERSION:
        raise LateFusionContractError("late-fusion configuration version mismatch")
    if tuple(config["configuration_order"]) != CONFIGURATIONS:
        raise LateFusionContractError("seven-condition matrix mismatch")
    actual_fusion = {
        name: tuple(modalities)
        for name, modalities in config["fusion_configurations"].items()
    }
    if actual_fusion != FUSION_CONFIGURATIONS:
        raise LateFusionContractError("late-fusion modality mapping mismatch")
    if config["primary_multimodal_architecture"] != (
        "DECISION_LEVEL_STACKING_LATE_FUSION"
    ):
        raise LateFusionContractError("primary architecture is not late fusion")
    if config["raw_feature_concatenation_primary"] is not False:
        raise LateFusionContractError("raw concatenation cannot be primary")
    meta = config["meta_learner"]
    if (
        config["meta_learner_family"] != "Logistic Regression"
        or config["meta_learner_is_fifth_algorithm"] is not False
        or meta["regularization"] != "L2"
        or meta["l1_ratio"] != 0.0
    ):
        raise LateFusionContractError(
            "fixed L2 Logistic Regression meta-contract mismatch"
        )
    if config["validation_label_use_for_meta_fit"] != "PROHIBITED":
        raise LateFusionContractError("VALIDATION label meta-fit prohibition missing")
    if config["meta_training"]["backfill_warmup_rows"] is not False:
        raise LateFusionContractError("warm-up backfill must remain prohibited")
    return config


def _ordered(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: (row["timestamp"], row["commit_sha"]))


def _membership_digest(rows: list[dict[str, Any]]) -> str:
    return digest([row["row_identifier"] for row in rows])


def build_oof_meta_table(
    train_rows: list[dict[str, Any]],
    algorithm: str,
    unimodal_config: dict[str, Any],
) -> OOFMetaTable:
    """Generate strict-forward OOF TRAIN probabilities for C, P, and T."""
    if algorithm not in ALGORITHMS:
        raise LateFusionContractError(f"unapproved base family: {algorithm}")
    if not train_rows or {row["partition"] for row in train_rows} != {"TRAIN"}:
        raise LateFusionContractError("OOF input must contain TRAIN rows only")
    if len({row["project"] for row in train_rows}) != 1:
        raise LateFusionContractError("OOF generation must be project-local")
    by_block: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in _ordered(train_rows):
        block = row["forward_block"]
        if block is None:
            raise LateFusionContractError("TRAIN row lacks a forward block")
        by_block[int(block)].append(row)
    blocks = sorted(by_block)
    if len(blocks) < 2:
        raise LateFusionContractError("at least two TRAIN forward blocks are required")
    warmup = tuple(row["row_identifier"] for row in by_block[blocks[0]])
    records: list[tuple[tuple[str, str], str, int, list[float]]] = []
    lineage: list[dict[str, Any]] = []
    for prediction_block in blocks[1:]:
        fit_blocks = [block for block in blocks if block < prediction_block]
        fit_rows = _ordered([row for block in fit_blocks for row in by_block[block]])
        prediction_rows = _ordered(by_block[prediction_block])
        if len(set(row["target"] for row in fit_rows)) != 2:
            raise LateFusionContractError("OOF base fit lacks both classes")
        if len(set(row["target"] for row in prediction_rows)) != 2:
            raise LateFusionContractError("OOF prediction block lacks both classes")
        fit_ids = {row["row_identifier"] for row in fit_rows}
        prediction_ids = {row["row_identifier"] for row in prediction_rows}
        if fit_ids & prediction_ids:
            raise LateFusionContractError("OOF fit and prediction rows overlap")
        fit_max = max((row["timestamp"], row["commit_sha"]) for row in fit_rows)
        prediction_min = min(
            (row["timestamp"], row["commit_sha"]) for row in prediction_rows
        )
        if fit_max >= prediction_min:
            raise LateFusionContractError("OOF base fit is not strictly earlier")
        fold_probabilities: dict[str, np.ndarray] = {}
        for modality in MODALITIES:
            fitted = fit_unimodal(
                fit_rows, algorithm, modality, unimodal_config
            )
            fold_probabilities[modality] = predict_positive_probability(
                fitted, prediction_rows, modality
            )
        for index, row in enumerate(prediction_rows):
            records.append(
                (
                    (row["timestamp"], row["commit_sha"]),
                    row["row_identifier"],
                    int(row["target"]),
                    [float(fold_probabilities[m][index]) for m in MODALITIES],
                )
            )
        lineage.append(
            {
                "prediction_block": prediction_block,
                "fit_blocks": fit_blocks,
                "fit_row_count": len(fit_rows),
                "prediction_row_count": len(prediction_rows),
                "fit_membership_sha256": _membership_digest(fit_rows),
                "prediction_membership_sha256": _membership_digest(
                    prediction_rows
                ),
                "fit_prediction_disjoint": True,
                "strict_forward_time": True,
                "base_family": algorithm,
                "modalities": list(MODALITIES),
            }
        )
    records.sort(key=lambda record: record[0])
    row_ids = tuple(record[1] for record in records)
    if set(row_ids) & set(warmup):
        raise LateFusionContractError("warm-up rows were backfilled into OOF table")
    probabilities = np.asarray([record[3] for record in records], dtype=float)
    if (
        probabilities.shape != (len(records), len(MODALITIES))
        or not np.all(np.isfinite(probabilities))
        or np.any(probabilities < 0)
        or np.any(probabilities > 1)
    ):
        raise LateFusionContractError("invalid OOF probability table")
    targets = np.asarray([record[2] for record in records], dtype=int)
    if len(np.unique(targets)) != 2:
        raise LateFusionContractError("meta-training table lacks both classes")
    return OOFMetaTable(
        row_identifiers=row_ids,
        targets=targets,
        probabilities=probabilities,
        warmup_row_identifiers=warmup,
        fold_lineage=tuple(lineage),
    )


def _meta_learner(config: dict[str, Any]) -> LogisticRegression:
    parameters = dict(config["meta_learner"])
    parameters.pop("regularization")
    return LogisticRegression(**parameters)


def fit_and_score_family(
    train_rows: list[dict[str, Any]],
    validation_rows: list[dict[str, Any]],
    algorithm: str,
    unimodal_config: dict[str, Any],
    fusion_config: dict[str, Any],
) -> dict[str, Any]:
    """Produce the seven probability streams without using VALIDATION labels."""
    if not validation_rows or {row["partition"] for row in validation_rows} != {
        "VALIDATION"
    }:
        raise LateFusionContractError("score input must contain VALIDATION rows only")
    if {row["project"] for row in train_rows} != {
        row["project"] for row in validation_rows
    }:
        raise LateFusionContractError("TRAIN/VALIDATION project mismatch")
    oof = build_oof_meta_table(train_rows, algorithm, unimodal_config)
    meta_models: dict[str, LogisticRegression] = {}
    for configuration, modalities in FUSION_CONFIGURATIONS.items():
        columns = [MODALITIES.index(modality) for modality in modalities]
        meta_models[configuration] = _meta_learner(fusion_config).fit(
            oof.probabilities[:, columns], oof.targets
        )

    base_probabilities: dict[str, np.ndarray] = {}
    for modality in MODALITIES:
        fitted = fit_unimodal(train_rows, algorithm, modality, unimodal_config)
        base_probabilities[modality] = predict_positive_probability(
            fitted, validation_rows, modality
        )
    probability_streams = dict(base_probabilities)
    for configuration, modalities in FUSION_CONFIGURATIONS.items():
        matrix = np.column_stack(
            [base_probabilities[modality] for modality in modalities]
        )
        probability_streams[configuration] = np.asarray(
            meta_models[configuration].predict_proba(matrix)[:, 1], dtype=float
        )
    expected_shape = (len(validation_rows),)
    if tuple(probability_streams) != CONFIGURATIONS:
        raise LateFusionContractError("seven probability streams are incomplete")
    if any(
        probabilities.shape != expected_shape
        or not np.all(np.isfinite(probabilities))
        or np.any(probabilities < 0)
        or np.any(probabilities > 1)
        for probabilities in probability_streams.values()
    ):
        raise LateFusionContractError("invalid VALIDATION probability stream")
    validation_ids = tuple(row["row_identifier"] for row in validation_rows)
    return {
        "algorithm": algorithm,
        "base_learner_family": algorithm,
        "meta_learner_family": "Logistic Regression",
        "meta_learner_counted_as_fifth_algorithm": False,
        "architecture": "DECISION_LEVEL_STACKING_LATE_FUSION",
        "raw_feature_concatenation": False,
        "train_membership_sha256": _membership_digest(train_rows),
        "validation_membership_sha256": digest(list(validation_ids)),
        "identical_validation_identities_all_seven_conditions": True,
        "meta_training_row_count": len(oof.row_identifiers),
        "meta_training_membership_sha256": digest(list(oof.row_identifiers)),
        "warmup_row_count": len(oof.warmup_row_identifiers),
        "warmup_membership_sha256": digest(list(oof.warmup_row_identifiers)),
        "warmup_backfilled": False,
        "oof_fold_count": len(oof.fold_lineage),
        "oof_fold_lineage": list(oof.fold_lineage),
        "validation_labels_used_for_meta_fit": False,
        "probability_streams": {
            configuration: {
                "row_count": len(probabilities),
                "validation_membership_sha256": digest(list(validation_ids)),
                "probability_sha256": digest(probabilities.tolist()),
                "probability_min": float(probabilities.min()),
                "probability_max": float(probabilities.max()),
                "meta_features": (
                    list(FUSION_CONFIGURATIONS[configuration])
                    if configuration in FUSION_CONFIGURATIONS
                    else [configuration]
                ),
            }
            for configuration, probabilities in probability_streams.items()
        },
    }


def engineering_smoke_test(root: Path) -> dict[str, Any]:
    unimodal_config = load_unimodal_config(root)
    fusion_config = load_config(root)
    project = min(EXPECTED_PROJECTS)
    rows = load_development_project(root, project)
    train = [row for row in rows if row["partition"] == "TRAIN"]
    validation = [row for row in rows if row["partition"] == "VALIDATION"]
    families = [
        fit_and_score_family(
            train,
            validation,
            algorithm,
            unimodal_config,
            fusion_config,
        )
        for algorithm in ALGORITHMS
    ]
    meta_counts = {item["meta_training_row_count"] for item in families}
    warmup_counts = {item["warmup_row_count"] for item in families}
    if len(meta_counts) != 1 or len(warmup_counts) != 1:
        raise LateFusionContractError("family OOF memberships are inconsistent")
    return {
        "schema_version": VERSION,
        "status": "PASS",
        "purpose": "ENGINEERING_ARCHITECTURE_SMOKE_TEST_NOT_SCIENTIFIC_EVIDENCE",
        "project": project,
        "project_selection_rule": "LEXICOGRAPHICALLY_FIRST_ELIGIBLE_PROJECT",
        "base_family_count": len(families),
        "configuration_count": len(families) * len(CONFIGURATIONS),
        "families": families,
        "meta_training_row_count": next(iter(meta_counts)),
        "warmup_row_count": next(iter(warmup_counts)),
        "performance_used_for_any_decision": False,
        "validation_metric_count": 0,
        "validation_labels_used_for_meta_fit": False,
        "t1_predictive_access_count": 0,
        "t2_predictive_access_count": 0,
    }


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))


def _write_manifest(output: Path) -> None:
    entries = [
        f"{file_digest(path)}  {path.name}"
        for path in sorted(output.iterdir())
        if path.is_file() and path.name != "MANIFEST.sha256"
    ]
    (output / "MANIFEST.sha256").write_text(
        "\n".join(entries) + "\n", encoding="utf-8"
    )


def materialize(root: Path) -> Path:
    config = load_config(root)
    smoke = engineering_smoke_test(root)
    output = root / OUTPUT_REL
    _write_json(output / "late_fusion_contract.json", config)
    _write_json(output / "engineering_smoke_test.json", smoke)
    _write_json(
        output / "architecture.json",
        {
            "schema_version": VERSION,
            "base_learner_rule": {
                algorithm: {
                    modality: f"{modality}_{algorithm}"
                    for modality in MODALITIES
                }
                for algorithm in ALGORITHMS
            },
            "primary_multimodal_architecture": (
                "DECISION_LEVEL_STACKING_LATE_FUSION"
            ),
            "multimodal_meta_features": {
                name: [f"{modality}_positive_probability" for modality in modalities]
                for name, modalities in FUSION_CONFIGURATIONS.items()
            },
            "raw_feature_concatenation": "NOT_PRIMARY_AND_NOT_EXECUTED",
            "meta_learner": "FIXED_LOGISTIC_REGRESSION_L2",
            "meta_learner_is_fifth_algorithm": False,
            "algorithm_comparison_unit": "BASE_LEARNER_FAMILY",
        },
    )
    _write_json(
        output / "execution_ledger.json",
        {
            "schema_version": VERSION,
            "engineering_project_count": 1,
            "engineering_base_family_count": len(ALGORITHMS),
            "engineering_condition_count": len(ALGORITHMS) * len(CONFIGURATIONS),
            "engineering_oof_base_fit_count": sum(
                item["oof_fold_count"] * len(MODALITIES)
                for item in smoke["families"]
            ),
            "engineering_full_train_base_refit_count": (
                len(ALGORITHMS) * len(MODALITIES)
            ),
            "engineering_meta_fit_count": (
                len(ALGORITHMS) * len(FUSION_CONFIGURATIONS)
            ),
            "scientific_condition_count": 0,
            "validation_metric_count": 0,
            "warmup_backfill_count": 0,
            "t1_predictive_access_count": 0,
            "t2_predictive_access_count": 0,
            "final_test_metric_count": 0,
        },
    )
    _write_json(
        output / "implementation.json",
        {
            "schema_version": VERSION,
            "implementation_path": (
                "src/experimentation/q1_controlled_late_fusion.py"
            ),
            "implementation_sha256": file_digest(Path(__file__)),
            "configuration_path": str(CONFIG_REL),
            "configuration_sha256": file_digest(root / CONFIG_REL),
            "block_2_and_3_implementations_modified": False,
        },
    )
    report = "\n".join(
        (
            "# Sprint 49 Controlled Late-Fusion Contract",
            "",
            "For each base family A, C_A, P_A, and T_A are independently fitted "
            "modality models. C+P, C+T, P+T, and C+P+T consume only their "
            "positive-class probabilities as meta-features. Raw feature "
            "concatenation is neither primary nor executed.",
            "",
            "Each fixed L2 Logistic Regression meta-learner is trained only from "
            "strict-forward out-of-fold TRAIN probabilities. The earliest TRAIN "
            "block is retained as warm-up and never backfilled. Base learners are "
            "then refitted on full project TRAIN and score identical VALIDATION "
            "identities. VALIDATION labels do not fit a base learner or meta-learner.",
            "",
            "The meta-learner is not a fifth family; comparisons refer to the four "
            "base families. The engineering smoke test executed all 28 conditions "
            "for the deterministic pilot project without metrics or performance "
            "selection. T1/T2 predictive access remains zero.",
            "",
        )
    )
    (output / "REPORT.md").write_text(report, encoding="utf-8")
    _write_manifest(output)
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    print(materialize(args.root.resolve()))


if __name__ == "__main__":
    main()
