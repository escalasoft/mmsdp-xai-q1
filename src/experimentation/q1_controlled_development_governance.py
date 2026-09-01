"""TRAIN-only temporal hyperparameter governance for Sprint 49."""

from __future__ import annotations

import argparse
import copy
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.metrics import (
    average_precision_score,
    matthews_corrcoef,
    recall_score,
    roc_auc_score,
)

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

VERSION = "q1-controlled-development-governance-1.0.0"
CONFIG_REL = Path(
    "configs/experiments/q1_controlled_development_governance_1.0.0.json"
)
OUTPUT_REL = Path(
    "audits/q1-controlled-train-validation-baselines/1.0.0/"
    "development_governance"
)
FULL_FOLD_IDENTIFIERS = tuple(range(2, 12))
PRIMARY_FOLD_IDENTIFIERS = (3, 6, 9)
PRIMARY_DEVELOPMENT_FOLD_COUNT = len(PRIMARY_FOLD_IDENTIFIERS)
SELECTION_METRIC = "PR_AUC"
DIAGNOSTIC_METRICS = ("MCC", "ROC_AUC", "Recall")


class DevelopmentGovernanceError(RuntimeError):
    """Raised when temporal search or frozen selection governance is violated."""


@dataclass(frozen=True)
class ForwardFold:
    """One expanding, project-local, TRAIN-side temporal fold."""

    fold_identifier: int
    fit_rows: tuple[dict[str, Any], ...]
    score_rows: tuple[dict[str, Any], ...]


def load_config(root: Path) -> dict[str, Any]:
    config = json.loads((root / CONFIG_REL).read_text(encoding="utf-8"))
    if config["experiment_version"] != VERSION:
        raise DevelopmentGovernanceError("development configuration version mismatch")
    if tuple(config["full_robustness_fold_identifiers"]) != FULL_FOLD_IDENTIFIERS:
        raise DevelopmentGovernanceError("fold 2..11 infrastructure contract mismatch")
    if tuple(config["primary_development_fold_identifiers"]) != (
        PRIMARY_FOLD_IDENTIFIERS
    ):
        raise DevelopmentGovernanceError("primary fold identifiers mismatch")
    if config["primary_development_fold_count"] != PRIMARY_DEVELOPMENT_FOLD_COUNT:
        raise DevelopmentGovernanceError("primary fold count mismatch")
    if config["primary_selection_metric"] != SELECTION_METRIC:
        raise DevelopmentGovernanceError("PR-AUC selection contract mismatch")
    if tuple(config["diagnostic_metrics"]) != DIAGNOSTIC_METRICS:
        raise DevelopmentGovernanceError("secondary diagnostic contract mismatch")
    if "Accuracy" not in config["prohibited_selection_metrics"]:
        raise DevelopmentGovernanceError("accuracy prohibition is missing")
    if set(config["algorithm_search_spaces"]) != set(ALGORITHMS):
        raise DevelopmentGovernanceError("algorithm search-space family mismatch")
    for algorithm, candidates in config["algorithm_search_spaces"].items():
        if len(candidates) != 2:
            raise DevelopmentGovernanceError(
                f"{algorithm} search space is not the frozen two-candidate grid"
            )
        if len({candidate["candidate_id"] for candidate in candidates}) != 2:
            raise DevelopmentGovernanceError("candidate identifiers are not unique")
    if config["validation_access"] != (
        "EVALUATE_FROZEN_DEVELOPMENT_CHOICE_ONLY"
    ):
        raise DevelopmentGovernanceError("VALIDATION access contract mismatch")
    return config


def _order(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: (row["timestamp"], row["commit_sha"]))


def build_forward_fold(
    train_rows: list[dict[str, Any]], fold_identifier: int
) -> ForwardFold:
    """Build any expanding fold k in the supported 2..11 infrastructure."""
    if fold_identifier not in FULL_FOLD_IDENTIFIERS:
        raise DevelopmentGovernanceError("fold identifier must be in 2..11")
    if not train_rows or {row["partition"] for row in train_rows} != {"TRAIN"}:
        raise DevelopmentGovernanceError("development folds require TRAIN rows only")
    if len({row["project"] for row in train_rows}) != 1:
        raise DevelopmentGovernanceError("development folds must be project-local")
    fit_rows = _order(
        [
            row
            for row in train_rows
            if row["forward_block"] is not None
            and int(row["forward_block"]) < fold_identifier
        ]
    )
    score_rows = _order(
        [
            row
            for row in train_rows
            if row["forward_block"] is not None
            and int(row["forward_block"]) == fold_identifier
        ]
    )
    if not fit_rows or not score_rows:
        raise DevelopmentGovernanceError(
            f"fold {fold_identifier} is not available in supplied TRAIN rows"
        )
    if len({row["target"] for row in fit_rows}) != 2:
        raise DevelopmentGovernanceError("fold fit membership lacks both classes")
    if len({row["target"] for row in score_rows}) != 2:
        raise DevelopmentGovernanceError("fold score membership lacks both classes")
    fit_ids = {row["row_identifier"] for row in fit_rows}
    score_ids = {row["row_identifier"] for row in score_rows}
    if fit_ids & score_ids:
        raise DevelopmentGovernanceError("fold fit and score memberships overlap")
    if max((row["timestamp"], row["commit_sha"]) for row in fit_rows) >= min(
        (row["timestamp"], row["commit_sha"]) for row in score_rows
    ):
        raise DevelopmentGovernanceError("fold is not strictly forward temporal")
    return ForwardFold(fold_identifier, tuple(fit_rows), tuple(score_rows))


def build_primary_folds(train_rows: list[dict[str, Any]]) -> tuple[ForwardFold, ...]:
    return tuple(
        build_forward_fold(train_rows, identifier)
        for identifier in PRIMARY_FOLD_IDENTIFIERS
    )


def development_metrics(
    targets: np.ndarray, probabilities: np.ndarray
) -> dict[str, float]:
    if len(np.unique(targets)) != 2:
        raise DevelopmentGovernanceError("development diagnostic lacks both classes")
    predicted = (probabilities >= 0.5).astype(int)
    metrics = {
        "PR_AUC": float(average_precision_score(targets, probabilities)),
        "MCC": float(matthews_corrcoef(targets, predicted)),
        "ROC_AUC": float(roc_auc_score(targets, probabilities)),
        "Recall": float(recall_score(targets, predicted, zero_division=0)),
    }
    if any(not np.isfinite(value) for value in metrics.values()):
        raise DevelopmentGovernanceError("non-finite development metric")
    return metrics


def _candidate_unimodal_config(
    unimodal_config: dict[str, Any],
    algorithm: str,
    parameter_overrides: dict[str, Any],
) -> dict[str, Any]:
    candidate_config = copy.deepcopy(unimodal_config)
    unknown = set(parameter_overrides) - set(candidate_config["algorithms"][algorithm])
    if unknown:
        raise DevelopmentGovernanceError(
            f"candidate overrides unknown parameters: {sorted(unknown)}"
        )
    candidate_config["algorithms"][algorithm].update(parameter_overrides)
    return candidate_config


def select_hyperparameters(
    train_rows: list[dict[str, Any]],
    algorithm: str,
    modality: str,
    unimodal_config: dict[str, Any],
    governance_config: dict[str, Any],
) -> dict[str, Any]:
    """Select by mean TRAIN-fold PR-AUC; never inspect VALIDATION."""
    if algorithm not in ALGORITHMS or modality not in MODALITIES:
        raise DevelopmentGovernanceError("unknown algorithm or modality")
    folds = build_primary_folds(train_rows)
    candidate_results = []
    for candidate_index, candidate in enumerate(
        governance_config["algorithm_search_spaces"][algorithm]
    ):
        candidate_config = _candidate_unimodal_config(
            unimodal_config, algorithm, candidate["parameters"]
        )
        fold_results = []
        for fold in folds:
            fit_rows = list(fold.fit_rows)
            score_rows = list(fold.score_rows)
            fitted = fit_unimodal(
                fit_rows, algorithm, modality, candidate_config
            )
            probabilities = predict_positive_probability(
                fitted, score_rows, modality
            )
            targets = np.asarray([row["target"] for row in score_rows], dtype=int)
            fold_results.append(
                {
                    "fold_identifier": fold.fold_identifier,
                    "fit_row_count": len(fit_rows),
                    "score_row_count": len(score_rows),
                    "fit_membership_sha256": digest(
                        [row["row_identifier"] for row in fit_rows]
                    ),
                    "score_membership_sha256": digest(
                        [row["row_identifier"] for row in score_rows]
                    ),
                    "metrics": development_metrics(targets, probabilities),
                }
            )
        mean_metrics = {
            metric: float(
                np.mean([result["metrics"][metric] for result in fold_results])
            )
            for metric in (SELECTION_METRIC, *DIAGNOSTIC_METRICS)
        }
        candidate_results.append(
            {
                "candidate_index": candidate_index,
                "candidate_id": candidate["candidate_id"],
                "parameter_overrides": candidate["parameters"],
                "effective_parameters": candidate_config["algorithms"][algorithm],
                "fold_results": fold_results,
                "mean_metrics": mean_metrics,
            }
        )
    selected = min(
        candidate_results,
        key=lambda result: (
            -result["mean_metrics"][SELECTION_METRIC],
            result["candidate_index"],
        ),
    )
    return {
        "project": train_rows[0]["project"],
        "algorithm": algorithm,
        "modality": modality,
        "search_method": governance_config["search_method"],
        "full_search_space": governance_config["algorithm_search_spaces"][algorithm],
        "primary_selection_metric": SELECTION_METRIC,
        "diagnostic_metrics": list(DIAGNOSTIC_METRICS),
        "accuracy_used": False,
        "primary_development_fold_count": PRIMARY_DEVELOPMENT_FOLD_COUNT,
        "primary_development_fold_identifiers": list(PRIMARY_FOLD_IDENTIFIERS),
        "temporal_fold_rule": governance_config["temporal_fold_rule"],
        "random_seed": governance_config["random_seed"],
        "candidate_count": len(candidate_results),
        "number_of_fits": len(candidate_results) * len(folds),
        "candidate_results": candidate_results,
        "selected_candidate_id": selected["candidate_id"],
        "selected_parameters": selected["effective_parameters"],
        "selected_mean_pr_auc": selected["mean_metrics"][SELECTION_METRIC],
        "tie_break": governance_config["candidate_tie_break"],
        "validation_access_count": 0,
        "t1_predictive_access_count": 0,
        "t2_predictive_access_count": 0,
    }


def engineering_smoke_test(root: Path) -> dict[str, Any]:
    governance = load_config(root)
    unimodal = load_unimodal_config(root)
    project = min(EXPECTED_PROJECTS)
    development_rows = load_development_project(root, project)
    train = [row for row in development_rows if row["partition"] == "TRAIN"]
    selections = [
        select_hyperparameters(train, algorithm, modality, unimodal, governance)
        for algorithm in ALGORITHMS
        for modality in MODALITIES
    ]
    return {
        "schema_version": VERSION,
        "status": "PASS",
        "purpose": "ENGINEERING_SEARCH_SMOKE_TEST_NOT_SCIENTIFIC_EVIDENCE",
        "project": project,
        "project_selection_rule": "LEXICOGRAPHICALLY_FIRST_ELIGIBLE_PROJECT",
        "search_count": len(selections),
        "number_of_fits": sum(item["number_of_fits"] for item in selections),
        "primary_development_fold_count": PRIMARY_DEVELOPMENT_FOLD_COUNT,
        "primary_development_fold_identifiers": list(PRIMARY_FOLD_IDENTIFIERS),
        "selections": selections,
        "results_used_to_modify_search_space": False,
        "validation_access_count": 0,
        "validation_metric_count": 0,
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
    governance = load_config(root)
    smoke = engineering_smoke_test(root)
    output = root / OUTPUT_REL
    _write_json(output / "development_governance.json", governance)
    _write_json(output / "engineering_search_smoke_test.json", smoke)
    _write_json(
        output / "fold_infrastructure.json",
        {
            "schema_version": VERSION,
            "supported_fold_identifiers": list(FULL_FOLD_IDENTIFIERS),
            "fold_rule": governance["temporal_fold_rule"],
            "random_or_shuffled_k_fold": "PROHIBITED",
            "primary_development_fold_count": PRIMARY_DEVELOPMENT_FOLD_COUNT,
            "primary_fold_identifiers": list(PRIMARY_FOLD_IDENTIFIERS),
            "primary_fold_rationale": governance["primary_fold_rationale"],
            "full_2_11_robustness_execution": "DEFERRED_NOT_EXECUTED",
        },
    )
    _write_json(
        output / "execution_ledger.json",
        {
            "schema_version": VERSION,
            "engineering_search_count": smoke["search_count"],
            "engineering_fit_count": smoke["number_of_fits"],
            "scientific_search_count": 0,
            "scientific_fit_count": 0,
            "primary_development_fold_count": PRIMARY_DEVELOPMENT_FOLD_COUNT,
            "full_robustness_fold_count_executed": 0,
            "validation_access_count": 0,
            "validation_metric_count": 0,
            "accuracy_selection_count": 0,
            "search_space_post_validation_change_count": 0,
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
                "src/experimentation/q1_controlled_development_governance.py"
            ),
            "implementation_sha256": file_digest(Path(__file__)),
            "configuration_path": str(CONFIG_REL),
            "configuration_sha256": file_digest(root / CONFIG_REL),
            "blocks_2_3_4_implementations_modified": False,
        },
    )
    report = "\n".join(
        (
            "# Sprint 49 Development and Hyperparameter Governance",
            "",
            "Every project/algorithm/modality search uses exactly two predeclared "
            "candidates and three expanding TRAIN-only folds (k=3, 6, 9). This "
            "early/middle/late setting was frozen before results to provide drift "
            "coverage at six fits per search. Infrastructure supports k=2 through "
            "11, but the full robustness sweep is deferred.",
            "",
            "Mean PR-AUC is the sole selection statistic. MCC, ROC-AUC, and Recall "
            "are diagnostics; accuracy is never computed or used. Ties follow "
            "predeclared candidate order. Search preserves natural prevalence, "
            "uses seed 20260901, and never consumes VALIDATION, T1, or T2.",
            "",
            "The actual-data engineering smoke test completed 12 independent "
            "searches and 72 TRAIN-side fits without VALIDATION metrics. Its "
            "selections are engineering evidence only and did not alter grids. "
            "Campaign selections will be recorded independently per project, "
            "algorithm, and modality before each frozen VALIDATION evaluation.",
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
