"""Execute and report the 392-condition Sprint 49 development campaign."""

from __future__ import annotations

import argparse
import copy
import csv
import gzip
import json
import math
import platform
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    matthews_corrcoef,
    precision_score,
    recall_score,
    roc_auc_score,
)

from experimentation.q1_controlled_development_governance import (
    PRIMARY_FOLD_IDENTIFIERS,
    select_hyperparameters,
)
from experimentation.q1_controlled_development_governance import (
    load_config as load_governance_config,
)
from experimentation.q1_controlled_late_fusion import (
    CONFIGURATIONS,
    FUSION_CONFIGURATIONS,
)
from experimentation.q1_controlled_late_fusion import (
    load_config as load_fusion_config,
)
from experimentation.q1_controlled_train_validation_baselines import (
    CODE_FEATURES,
    EXPECTED_PROJECTS,
    PROCESS_FEATURES,
    canonical_bytes,
    digest,
    file_digest,
    load_development_project,
)
from experimentation.q1_controlled_unimodal_modeling import (
    ALGORITHMS,
    MODALITIES,
    fit_unimodal,
    package_versions,
    predict_positive_probability,
)
from experimentation.q1_controlled_unimodal_modeling import (
    load_config as load_unimodal_config,
)

VERSION = "q1-controlled-result-contract-1.0.0"
CONFIG_REL = Path("configs/experiments/q1_controlled_result_contract_1.0.0.json")
OUTPUT_REL = Path("audits/q1-controlled-train-validation-baselines/1.0.0/campaign")
METRICS = ("PR_AUC", "ROC_AUC", "MCC", "Recall", "Precision", "F1")
THRESHOLD = 0.5


class CampaignError(RuntimeError):
    """Raised when the scientific result contract is violated."""


def assert_scoring_partition_allowed(partition: str) -> None:
    """Fail closed for TEST scoring until future authorization is implemented."""
    if partition in {"TRAIN", "VALIDATION"}:
        return
    if partition in {"T1", "T2"}:
        raise CampaignError(
            f"{partition} predictive scoring denied: explicit future authorization "
            "is required"
        )
    raise CampaignError(f"unknown scoring partition: {partition}")


def load_config(root: Path) -> dict[str, Any]:
    config = json.loads((root / CONFIG_REL).read_text(encoding="utf-8"))
    if config["experiment_version"] != VERSION:
        raise CampaignError("result-contract version mismatch")
    if tuple(config["metrics"]) != METRICS:
        raise CampaignError("predictive metric contract mismatch")
    if config["threshold_policy"] != {
        "source": "PREDECLARED_FIXED",
        "threshold": THRESHOLD,
        "validation_threshold_selection": "PROHIBITED",
    }:
        raise CampaignError("classification threshold contract mismatch")
    if config["condition_count"] != 392:
        raise CampaignError("primary condition-count contract mismatch")
    if tuple(config["development_fold_identifiers"]) != PRIMARY_FOLD_IDENTIFIERS:
        raise CampaignError("development-fold contract mismatch")
    return config


def predictive_metrics(y: np.ndarray, probabilities: np.ndarray) -> dict[str, Any]:
    if len(y) != len(probabilities) or len(np.unique(y)) != 2:
        raise CampaignError("metric inputs are invalid")
    predicted = (probabilities >= THRESHOLD).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, predicted, labels=[0, 1]).ravel()
    values = {
        "PR_AUC": float(average_precision_score(y, probabilities)),
        "ROC_AUC": float(roc_auc_score(y, probabilities)),
        "MCC": float(matthews_corrcoef(y, predicted)),
        "Recall": float(recall_score(y, predicted, zero_division=0)),
        "Precision": float(precision_score(y, predicted, zero_division=0)),
        "F1": float(f1_score(y, predicted, zero_division=0)),
        "TN": int(tn),
        "FP": int(fp),
        "FN": int(fn),
        "TP": int(tp),
        "positive_prevalence": float(np.mean(y)),
        "n_observations": len(y),
    }
    if any(not math.isfinite(values[metric]) for metric in METRICS):
        raise CampaignError("a required metric is not finite")
    return values


def _selected_config(
    base: dict[str, Any], algorithm: str, selected: dict[str, Any]
) -> dict[str, Any]:
    result = copy.deepcopy(base)
    result["algorithms"][algorithm] = dict(selected["selected_parameters"])
    return result


def _ordered(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: (row["timestamp"], row["commit_sha"]))


def _build_selected_oof(
    train: list[dict[str, Any]],
    algorithm: str,
    modality_configs: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    by_block: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in _ordered(train):
        by_block[int(row["forward_block"])].append(row)
    blocks = sorted(by_block)
    records = []
    lineage = []
    for block in blocks[1:]:
        fit_rows = _ordered(
            [row for prior in blocks if prior < block for row in by_block[prior]]
        )
        score_rows = _ordered(by_block[block])
        scores = {}
        for modality in MODALITIES:
            model = fit_unimodal(
                fit_rows, algorithm, modality, modality_configs[modality]
            )
            scores[modality] = predict_positive_probability(model, score_rows, modality)
        for index, row in enumerate(score_rows):
            records.append(
                {
                    "row_identifier": row["row_identifier"],
                    "block": block,
                    "target": int(row["target"]),
                    "probabilities": [float(scores[m][index]) for m in MODALITIES],
                }
            )
        lineage.append(
            {
                "prediction_block": block,
                "fit_blocks": [prior for prior in blocks if prior < block],
                "fit_count": len(fit_rows),
                "prediction_count": len(score_rows),
                "fit_membership_sha256": digest(
                    [row["row_identifier"] for row in fit_rows]
                ),
                "prediction_membership_sha256": digest(
                    [row["row_identifier"] for row in score_rows]
                ),
                "strict_forward_and_disjoint": True,
            }
        )
    return {
        "records": records,
        "lineage": lineage,
        "warmup_ids": [row["row_identifier"] for row in by_block[blocks[0]]],
    }


def _meta(config: dict[str, Any]) -> LogisticRegression:
    parameters = dict(config["meta_learner"])
    parameters.pop("regularization")
    return LogisticRegression(**parameters)


def _top_variables(pipeline: Any, modality: str) -> list[dict[str, Any]]:
    model = pipeline.named_steps["model"]
    if modality == "C":
        names = list(CODE_FEATURES)
    elif modality == "P":
        names = list(PROCESS_FEATURES)
    else:
        names = list(pipeline.named_steps["tfidf"].get_feature_names_out())
    if hasattr(model, "coef_"):
        values = np.abs(np.asarray(model.coef_)[0])
    elif hasattr(model, "feature_importances_"):
        values = np.asarray(model.feature_importances_, dtype=float)
    else:
        return []
    indexes = np.argsort(-values, kind="stable")[:10]
    return [
        {"variable": names[index], "importance": float(values[index])}
        for index in indexes
    ]


def _meta_top_variables(model: LogisticRegression, modalities: tuple[str, ...]):
    values = np.abs(np.asarray(model.coef_)[0])
    indexes = np.argsort(-values, kind="stable")
    return [
        {
            "variable": f"{modalities[index]}_positive_probability",
            "importance": float(values[index]),
        }
        for index in indexes
    ]


def _condition_record(
    project: str,
    algorithm: str,
    configuration: str,
    level: str,
    fold: str,
    membership: list[str],
    y: np.ndarray,
    probabilities: np.ndarray,
    selection_ids: dict[str, str],
    meta_training_count: int,
    reproducibility: dict[str, Any],
) -> dict[str, Any]:
    metrics = predictive_metrics(y, probabilities)
    return {
        "project": project,
        "algorithm_family": algorithm,
        "configuration": configuration,
        "result_level": level,
        "development_fold": fold,
        "threshold": THRESHOLD,
        "threshold_source": "PREDECLARED_FIXED",
        "membership_sha256": digest(membership),
        "probability_sha256": digest(probabilities.tolist()),
        "selected_candidate_ids": selection_ids,
        "meta_training_row_count": meta_training_count,
        "metrics": {metric: metrics[metric] for metric in METRICS},
        **reproducibility,
        **metrics,
    }


def _reproducibility_metadata(
    algorithm: str,
    configuration: str,
    selections: dict[str, dict[str, Any]],
    unimodal: dict[str, Any],
    fusion: dict[str, Any],
    train_hash: str,
    validation_hash: str,
    runtime: dict[str, Any],
) -> dict[str, Any]:
    modalities = tuple(configuration.split("+"))
    schemas = {
        "C": list(CODE_FEATURES),
        "P": list(PROCESS_FEATURES),
        "T": {
            "input": "raw_commit_message",
            "representation": unimodal["modalities"]["T"]["representation"],
        },
    }
    hyperparameters: dict[str, Any] = {
        modality: selections[modality]["selected_parameters"]
        for modality in modalities
    }
    if len(modalities) > 1:
        hyperparameters["meta_learner"] = fusion["meta_learner"]
    representation = {
        "numeric_preprocessing": {
            modality: unimodal["numeric_preprocessing"][algorithm]
            for modality in modalities
            if modality in {"C", "P"}
        },
        "text": (
            unimodal["modalities"]["T"]["representation"]
            if "T" in modalities
            else None
        ),
    }
    return {
        "seed": unimodal["seed"],
        "package_versions": runtime["package_versions"],
        "runtime": runtime,
        "feature_schema_sha256": digest(
            {modality: schemas[modality] for modality in modalities}
        ),
        "train_identity_sha256": train_hash,
        "validation_identity_sha256": validation_hash,
        "hyperparameters": hyperparameters,
        "representation_parameters": representation,
        "threshold_policy": {
            "source": "PREDECLARED_FIXED",
            "threshold": THRESHOLD,
            "validation_threshold_selection": "PROHIBITED",
        },
        "status": "SUCCESS",
    }


def _prediction_rows(
    project: str,
    algorithm: str,
    configuration: str,
    result_level: str,
    fold: str,
    partition: str,
    row_ids: list[str],
    targets: np.ndarray,
    probabilities: np.ndarray,
) -> list[dict[str, Any]]:
    assert_scoring_partition_allowed(partition)
    return [
        {
            "project": project,
            "algorithm_family": algorithm,
            "configuration": configuration,
            "result_level": result_level,
            "development_fold": fold,
            "partition": partition,
            "row_identifier": row_id,
            "benchmark_defined_observed_label": int(target),
            "raw_probability": float(probability),
        }
        for row_id, target, probability in zip(
            row_ids, targets, probabilities, strict=True
        )
    ]


def _guard_triggered(record: dict[str, Any], config: dict[str, Any]) -> bool:
    guard = config["near_perfect_guard"]
    all_five = all(
        record[metric] >= guard["all_five_metric_threshold"]
        for metric in guard["metrics_all_five"]
    )
    pair = all(
        record[metric] >= guard["discrimination_pair_threshold"]
        for metric in guard["metrics_discrimination_pair"]
    )
    return all_five or pair


def _duplicate_score_checks(
    probabilities: np.ndarray, targets: np.ndarray
) -> dict[str, int]:
    grouped: dict[float, set[int]] = defaultdict(set)
    counts: Counter[float] = Counter()
    for probability, target in zip(probabilities, targets, strict=True):
        value = float(probability)
        counts[value] += 1
        grouped[value].add(int(target))
    return {
        "duplicate_predictive_score_count": sum(
            count - 1 for count in counts.values() if count > 1
        ),
        "duplicate_score_conflicting_label_group_count": sum(
            len(labels) > 1 for labels in grouped.values()
        ),
    }


def run_project(root_text: str, project: str) -> dict[str, Any]:
    root = Path(root_text)
    campaign_config = load_config(root)
    governance = load_governance_config(root)
    unimodal = load_unimodal_config(root)
    fusion = load_fusion_config(root)
    rows = load_development_project(root, project)
    train = [row for row in rows if row["partition"] == "TRAIN"]
    validation = [row for row in rows if row["partition"] == "VALIDATION"]
    assert_scoring_partition_allowed("TRAIN")
    assert_scoring_partition_allowed("VALIDATION")
    train_ids = [row["row_identifier"] for row in train]
    validation_ids = [row["row_identifier"] for row in validation]
    train_hash = digest(train_ids)
    validation_hash = digest(validation_ids)
    runtime = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "package_versions": package_versions(),
    }
    if set(train_ids) & set(validation_ids):
        raise CampaignError("TRAIN/VALIDATION identity overlap")
    if max((row["timestamp"], row["commit_sha"]) for row in train) >= min(
        (row["timestamp"], row["commit_sha"]) for row in validation
    ):
        raise CampaignError("TRAIN does not strictly precede VALIDATION")
    all_records = []
    selection_records = []
    provenance = []
    diagnostics = []
    prediction_rows = []
    for algorithm in ALGORITHMS:
        selections = {
            modality: select_hyperparameters(
                train, algorithm, modality, unimodal, governance
            )
            for modality in MODALITIES
        }
        selection_records.extend(selections.values())
        modality_configs = {
            modality: _selected_config(unimodal, algorithm, selection)
            for modality, selection in selections.items()
        }
        selection_ids = {
            modality: selection["selected_candidate_id"]
            for modality, selection in selections.items()
        }
        oof = _build_selected_oof(train, algorithm, modality_configs)
        oof_records = oof["records"]
        oof_x = np.asarray([record["probabilities"] for record in oof_records])
        oof_y = np.asarray([record["target"] for record in oof_records], dtype=int)
        oof_blocks = np.asarray([record["block"] for record in oof_records], dtype=int)
        oof_ids = [record["row_identifier"] for record in oof_records]

        final_base_models = {}
        validation_base = {}
        top_variables = {}
        for modality in MODALITIES:
            pipeline = fit_unimodal(
                train, algorithm, modality, modality_configs[modality]
            )
            final_base_models[modality] = pipeline
            validation_base[modality] = predict_positive_probability(
                pipeline, validation, modality
            )
            top_variables[modality] = _top_variables(pipeline, modality)

        final_meta = {}
        validation_streams = dict(validation_base)
        for configuration, modalities in FUSION_CONFIGURATIONS.items():
            columns = [MODALITIES.index(modality) for modality in modalities]
            model = _meta(fusion).fit(oof_x[:, columns], oof_y)
            final_meta[configuration] = model
            matrix = np.column_stack([validation_base[m] for m in modalities])
            validation_streams[configuration] = model.predict_proba(matrix)[:, 1]
            top_variables[configuration] = _meta_top_variables(model, modalities)

        validation_y = np.asarray([row["target"] for row in validation], dtype=int)
        for configuration in CONFIGURATIONS:
            reproducibility = _reproducibility_metadata(
                algorithm,
                configuration,
                selections,
                unimodal,
                fusion,
                train_hash,
                validation_hash,
                runtime,
            )
            record = _condition_record(
                project,
                algorithm,
                configuration,
                "VALIDATION",
                "FROZEN_VALIDATION",
                validation_ids,
                validation_y,
                validation_streams[configuration],
                selection_ids,
                len(oof_records),
                reproducibility,
            )
            all_records.append(record)
            prediction_rows.extend(
                _prediction_rows(
                    project,
                    algorithm,
                    configuration,
                    "VALIDATION",
                    "FROZEN_VALIDATION",
                    "VALIDATION",
                    validation_ids,
                    validation_y,
                    validation_streams[configuration],
                )
            )
            if _guard_triggered(record, campaign_config):
                diagnostics.append(
                    {
                        "flag": campaign_config["near_perfect_guard"]["flag"],
                        "project": project,
                        "algorithm_family": algorithm,
                        "configuration": configuration,
                        "modality": configuration,
                        "result_level": "VALIDATION",
                        "development_fold": "FROZEN_VALIDATION",
                        "trigger_metrics": {
                            metric: record[metric]
                            for metric in campaign_config["near_perfect_guard"][
                                "metrics_all_five"
                            ]
                        },
                        "class_counts": {
                            "negative": int((validation_y == 0).sum()),
                            "positive": int((validation_y == 1).sum()),
                        },
                        "top_predictive_variables": top_variables[configuration],
                        "duplicate_checks": {
                            "duplicate_row_identifier_count": len(validation_ids)
                            - len(set(validation_ids)),
                            "train_validation_identity_overlap_count": len(
                                set(train_ids) & set(validation_ids)
                            ),
                            **_duplicate_score_checks(
                                validation_streams[configuration], validation_y
                            ),
                        },
                        "label_proxy_checks": {
                            "label_used_as_predictor": False,
                            "identity_or_provenance_used_as_predictor": False,
                            "explicit_bug_fix_issue_indicators_used": False,
                            "denylist_intersection": [],
                            "raw_text_keyword_engineering": False,
                        },
                        "temporal_overlap_checks": {
                            "train_strictly_precedes_validation": True,
                            "oof_strict_forward": True,
                        },
                        "t1_t2_access_count": 0,
                        "top_predictive_variables_source": (
                            "FROZEN_FULL_TRAIN_MODEL_OR_META_MODEL"
                        ),
                    }
                )

        for fold_identifier in PRIMARY_FOLD_IDENTIFIERS:
            score_mask = oof_blocks == fold_identifier
            meta_mask = oof_blocks < fold_identifier
            fold_y = oof_y[score_mask]
            fold_ids = [
                row_id for row_id, keep in zip(oof_ids, score_mask, strict=True) if keep
            ]
            fold_streams = {
                modality: oof_x[score_mask, MODALITIES.index(modality)]
                for modality in MODALITIES
            }
            for configuration, modalities in FUSION_CONFIGURATIONS.items():
                columns = [MODALITIES.index(modality) for modality in modalities]
                model = _meta(fusion).fit(
                    oof_x[meta_mask][:, columns], oof_y[meta_mask]
                )
                fold_streams[configuration] = model.predict_proba(
                    oof_x[score_mask][:, columns]
                )[:, 1]
            for configuration in CONFIGURATIONS:
                reproducibility = _reproducibility_metadata(
                    algorithm,
                    configuration,
                    selections,
                    unimodal,
                    fusion,
                    train_hash,
                    validation_hash,
                    runtime,
                )
                record = _condition_record(
                    project,
                    algorithm,
                    configuration,
                    "TRAIN_DEVELOPMENT",
                    f"K{fold_identifier}",
                    fold_ids,
                    fold_y,
                    fold_streams[configuration],
                    selection_ids,
                    int(meta_mask.sum()),
                    reproducibility,
                )
                all_records.append(record)
                prediction_rows.extend(
                    _prediction_rows(
                        project,
                        algorithm,
                        configuration,
                        "TRAIN_DEVELOPMENT",
                        f"K{fold_identifier}",
                        "TRAIN",
                        fold_ids,
                        fold_y,
                        fold_streams[configuration],
                    )
                )
                if _guard_triggered(record, campaign_config):
                    diagnostics.append(
                        {
                            "flag": campaign_config["near_perfect_guard"]["flag"],
                            "project": project,
                            "algorithm_family": algorithm,
                            "configuration": configuration,
                            "modality": configuration,
                            "result_level": "TRAIN_DEVELOPMENT",
                            "development_fold": f"K{fold_identifier}",
                            "trigger_metrics": {
                                metric: record[metric]
                                for metric in campaign_config[
                                    "near_perfect_guard"
                                ]["metrics_all_five"]
                            },
                            "class_counts": {
                                "negative": int((fold_y == 0).sum()),
                                "positive": int((fold_y == 1).sum()),
                            },
                            "top_predictive_variables": top_variables[configuration],
                            "duplicate_checks": {
                                "duplicate_row_identifier_count": len(fold_ids)
                                - len(set(fold_ids)),
                                "fit_score_identity_overlap_count": 0,
                                **_duplicate_score_checks(
                                    fold_streams[configuration], fold_y
                                ),
                            },
                            "label_proxy_checks": {
                                "label_used_as_predictor": False,
                                "identity_or_provenance_used_as_predictor": False,
                                "explicit_bug_fix_issue_indicators_used": False,
                                "denylist_intersection": [],
                                "raw_text_keyword_engineering": False,
                            },
                            "temporal_overlap_checks": {
                                "development_fit_strictly_precedes_score": True,
                                "oof_strict_forward": True,
                            },
                            "t1_t2_access_count": 0,
                            "top_predictive_variables_source": (
                                "FROZEN_FULL_TRAIN_MODEL_OR_META_MODEL"
                            ),
                        }
                    )
        provenance.append(
            {
                "project": project,
                "algorithm_family": algorithm,
                "train_membership_sha256": digest(train_ids),
                "validation_membership_sha256": digest(validation_ids),
                "identical_memberships_all_configurations": True,
                "meta_training_row_count": len(oof_records),
                "meta_training_membership_sha256": digest(oof_ids),
                "warmup_row_count": len(oof["warmup_ids"]),
                "warmup_membership_sha256": digest(oof["warmup_ids"]),
                "warmup_backfilled": False,
                "oof_lineage": oof["lineage"],
                "selected_candidate_ids": selection_ids,
            }
        )
    return {
        "project": project,
        "records": all_records,
        "selections": selection_records,
        "provenance": provenance,
        "diagnostics": diagnostics,
        "predictions": prediction_rows,
    }


def _long_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for record in records:
        for metric in METRICS:
            rows.append(
                {
                    "project": record["project"],
                    "algorithm_family": record["algorithm_family"],
                    "configuration": record["configuration"],
                    "result_level": record["result_level"],
                    "development_fold": record["development_fold"],
                    "metric": metric,
                    "value": record[metric],
                    "threshold": record["threshold"],
                    "TN": record["TN"],
                    "FP": record["FP"],
                    "FN": record["FN"],
                    "TP": record["TP"],
                    "positive_prevalence": record["positive_prevalence"],
                    "n_observations": record["n_observations"],
                    "membership_sha256": record["membership_sha256"],
                    "probability_sha256": record["probability_sha256"],
                }
            )
    return rows


def _validation(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [record for record in records if record["result_level"] == "VALIDATION"]


def _table_d(validation: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in validation:
        grouped[row["algorithm_family"], row["configuration"]].append(row)
    result = []
    for (algorithm, configuration), rows in grouped.items():
        item: dict[str, Any] = {
            "algorithm_family": algorithm,
            "configuration": configuration,
            "project_count": len(rows),
        }
        for metric in METRICS:
            values = np.asarray([row[metric] for row in rows])
            item[f"{metric}_mean"] = float(values.mean())
            item[f"{metric}_median"] = float(np.median(values))
            item[f"{metric}_std"] = float(values.std(ddof=1))
        result.append(item)
    return result


def _relative_table(
    validation: list[dict[str, Any]], baseline_configs: tuple[str, ...], label: str
):
    indexed = {
        (row["project"], row["algorithm_family"], row["configuration"]): row
        for row in validation
    }
    result = []
    for project in EXPECTED_PROJECTS:
        for algorithm in ALGORITHMS:
            candidates = [
                indexed[project, algorithm, configuration]
                for configuration in baseline_configs
            ]
            best = max(
                candidates,
                key=lambda row: (
                    row["PR_AUC"],
                    -baseline_configs.index(row["configuration"]),
                ),
            )
            full = indexed[project, algorithm, "C+P+T"]
            for metric in METRICS:
                denominator = abs(best[metric])
                result.append(
                    {
                        "project": project,
                        "algorithm_family": algorithm,
                        "comparison": label,
                        "baseline_configuration_selected_by_pr_auc": best[
                            "configuration"
                        ],
                        "metric": metric,
                        "full_value": full[metric],
                        "baseline_value": best[metric],
                        "absolute_difference": full[metric] - best[metric],
                        "relative_difference": None
                        if denominator == 0
                        else (full[metric] - best[metric]) / denominator,
                        "statistical_significance_claimed": False,
                    }
                )
    return result


def _ablation_table(validation: list[dict[str, Any]]) -> list[dict[str, Any]]:
    indexed = {
        (row["project"], row["algorithm_family"], row["configuration"]): row
        for row in validation
    }
    result = []
    for project in EXPECTED_PROJECTS:
        for algorithm in ALGORITHMS:
            full = indexed[project, algorithm, "C+P+T"]
            for pairwise in ("C+P", "C+T", "P+T"):
                baseline = indexed[project, algorithm, pairwise]
                for metric in METRICS:
                    result.append(
                        {
                            "project": project,
                            "algorithm_family": algorithm,
                            "comparison": f"C+P+T vs {pairwise}",
                            "metric": metric,
                            "full_value": full[metric],
                            "pairwise_value": baseline[metric],
                            "signed_difference": full[metric] - baseline[metric],
                            "statistical_significance_claimed": False,
                        }
                    )
    return result


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise CampaignError(f"cannot write empty table: {path.name}")
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=list(rows[0]), lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)


def _write_jsonl_gz(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("wb") as raw_stream:
        with gzip.GzipFile(
            filename="", mode="wb", fileobj=raw_stream, mtime=0
        ) as stream:
            for row in rows:
                stream.write(
                    json.dumps(
                        row,
                        ensure_ascii=True,
                        allow_nan=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ).encode("utf-8")
                    + b"\n"
                )


def _write_manifest(output: Path) -> None:
    entries = [
        f"{file_digest(path)}  {path.name}"
        for path in sorted(output.iterdir())
        if path.is_file() and path.name != "MANIFEST.sha256"
    ]
    (output / "MANIFEST.sha256").write_text("\n".join(entries) + "\n", encoding="utf-8")


def execute(root: Path, workers: int = 1) -> Path:
    config = load_config(root)
    if workers < 1:
        raise CampaignError("workers must be positive")
    project_payloads = []
    if workers == 1:
        for project in EXPECTED_PROJECTS:
            project_payloads.append(run_project(str(root), project))
            print(f"completed {project}", flush=True)
    else:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(run_project, str(root), project): project
                for project in EXPECTED_PROJECTS
            }
            for future in as_completed(futures):
                project = futures[future]
                project_payloads.append(future.result())
                print(f"completed {project}", flush=True)
        project_payloads.sort(
            key=lambda payload: EXPECTED_PROJECTS.index(payload["project"])
        )
    records = [row for payload in project_payloads for row in payload["records"]]
    selections = [row for payload in project_payloads for row in payload["selections"]]
    provenance = [row for payload in project_payloads for row in payload["provenance"]]
    diagnostics = [
        row for payload in project_payloads for row in payload["diagnostics"]
    ]
    predictions = [
        row for payload in project_payloads for row in payload["predictions"]
    ]
    validation = _validation(records)
    expected_validation = len(EXPECTED_PROJECTS) * len(ALGORITHMS) * len(CONFIGURATIONS)
    expected_development = expected_validation * len(PRIMARY_FOLD_IDENTIFIERS)
    if (
        len(validation) != expected_validation
        or len(records) - len(validation) != expected_development
    ):
        raise CampaignError("campaign result cardinality mismatch")
    key_counts = Counter(
        (row["project"], row["algorithm_family"], row["configuration"])
        for row in validation
    )
    if set(key_counts.values()) != {1}:
        raise CampaignError("validation condition is missing or duplicated")
    validation_prediction_count = sum(
        row["result_level"] == "VALIDATION" for row in predictions
    )
    expected_validation_predictions = sum(
        row["n_observations"] for row in validation
    )
    if validation_prediction_count != expected_validation_predictions:
        raise CampaignError("raw VALIDATION prediction cardinality mismatch")
    if any(row["partition"] in {"T1", "T2"} for row in predictions):
        raise CampaignError("TEST prediction reached raw prediction ledger")
    output = root / OUTPUT_REL
    output.mkdir(parents=True, exist_ok=True)
    long_rows = _long_rows(records)
    _write_json(output / "result_contract.json", config)
    _write_json(
        output / "condition_results.json", {"schema_version": VERSION, "rows": records}
    )
    _write_csv(output / "condition_results.csv", records)
    _write_csv(output / "metric_results_long.csv", long_rows)
    _write_jsonl_gz(output / "raw_prediction_ledger.jsonl.gz", predictions)
    _write_json(
        output / "development_selections.json",
        {"schema_version": VERSION, "rows": selections},
    )
    _write_json(
        output / "execution_provenance.json",
        {"schema_version": VERSION, "rows": provenance},
    )
    reproducibility_rows = [
        {
            key: row[key]
            for key in (
                "project",
                "algorithm_family",
                "configuration",
                "seed",
                "package_versions",
                "feature_schema_sha256",
                "train_identity_sha256",
                "validation_identity_sha256",
                "hyperparameters",
                "representation_parameters",
                "threshold_policy",
                "runtime",
                "metrics",
                "status",
                "probability_sha256",
            )
        }
        for row in validation
    ]
    _write_json(
        output / "reproducibility_manifest.json",
        {"schema_version": VERSION, "rows": reproducibility_rows},
    )
    table_a = [row for row in validation if row["configuration"] in MODALITIES]
    table_b = [
        row for row in validation if row["configuration"] in ("C+P", "C+T", "P+T")
    ]
    table_c = [row for row in validation if row["configuration"] == "C+P+T"]
    table_d = _table_d(validation)
    table_e = _relative_table(
        validation, MODALITIES, "C+P+T versus best unimodal by PR_AUC"
    )
    table_f = _relative_table(
        validation, ("C+P", "C+T", "P+T"), "C+P+T versus best pairwise by PR_AUC"
    )
    for filename, rows in (
        ("table_a_per_project_unimodal_validation.csv", table_a),
        ("table_b_per_project_pairwise_validation.csv", table_b),
        ("table_c_per_project_full_validation.csv", table_c),
        ("table_d_aggregate_algorithm_configuration.csv", table_d),
        ("table_e_full_vs_best_unimodal.csv", table_e),
        ("table_f_full_vs_best_pairwise.csv", table_f),
        ("ablation_ready_comparisons.csv", _ablation_table(validation)),
    ):
        _write_csv(output / filename, rows)
    _write_json(
        output / "perfect_performance_audit.json",
        {
            "schema_version": VERSION,
            "automatic_flag": config["near_perfect_guard"]["flag"],
            "trigger_count": len(diagnostics),
            "diagnostics": diagnostics,
            "dataset_changed_due_to_performance": False,
            "t1_t2_investigative_access_count": 0,
        },
    )
    raw_prediction_path = output / "raw_prediction_ledger.jsonl.gz"
    _write_json(
        output / "calibration_readiness.json",
        {
            "schema_version": VERSION,
            "status": "READY_FOR_NEXT_EXPERIMENTAL_STAGE",
            "preserved_probability_state": "RAW_UNCALIBRATED",
            "raw_prediction_ledger_path": str(
                raw_prediction_path.relative_to(root)
            ),
            "raw_prediction_ledger_sha256": file_digest(raw_prediction_path),
            "validation_prediction_count": validation_prediction_count,
            "train_development_prediction_count": (
                len(predictions) - validation_prediction_count
            ),
            "future_compatible_states": ["raw", "Platt", "isotonic"],
            "future_metrics_ready": [
                "Brier",
                "ECE",
                "MCE",
                "reliability_diagram",
            ],
            "labels_preserved_for_calibration_evaluation": True,
            "train_side_predictions_available_for_calibrator_fit": True,
            "calibrator_fit_count": 0,
            "calibration_claims_made": False,
            "t1_calibration_access_count": 0,
            "t2_calibration_access_count": 0,
        },
    )
    _write_json(
        output / "xai_readiness.json",
        {
            "schema_version": VERSION,
            "status": "DEFERRED_UNTIL_AFTER_PREDICTIVE_VALIDITY",
            "xai_execution_count": 0,
            "shap_execution_count": 0,
            "lime_execution_count": 0,
            "counterfactual_execution_count": 0,
            "feature_removal_from_xai_count": 0,
            "reconstruction_basis": [
                "reproducibility_manifest.json",
                "development_selections.json",
                "execution_provenance.json",
                "raw_prediction_ledger.jsonl.gz",
            ],
            "trained_state_policy": (
                "Deterministic reconstruction from frozen identities, schemas, "
                "representations, hyperparameters, seeds, and probability hashes; "
                "large runtime-specific pickles are not asserted portable."
            ),
            "t1_t2_xai_access_count": 0,
        },
    )
    oof_base_fit_count = sum(
        len(row["oof_lineage"]) * len(MODALITIES) for row in provenance
    )
    full_base_fit_count = len(EXPECTED_PROJECTS) * len(ALGORITHMS) * len(MODALITIES)
    full_meta_fit_count = (
        len(EXPECTED_PROJECTS) * len(ALGORITHMS) * len(FUSION_CONFIGURATIONS)
    )
    development_meta_fit_count = full_meta_fit_count * len(
        PRIMARY_FOLD_IDENTIFIERS
    )
    search_fit_count = sum(row["number_of_fits"] for row in selections)
    model_training_count = (
        search_fit_count
        + oof_base_fit_count
        + full_base_fit_count
        + full_meta_fit_count
        + development_meta_fit_count
    )
    _write_json(
        output / "execution_ledger.json",
        {
            "schema_version": VERSION,
            "primary_validation_condition_count": len(validation),
            "train_development_condition_fold_count": expected_development,
            "long_metric_row_count": len(long_rows),
            "hyperparameter_search_count": len(selections),
            "hyperparameter_search_fit_count": search_fit_count,
            "oof_base_model_training_count": oof_base_fit_count,
            "full_train_base_model_training_count": full_base_fit_count,
            "meta_model_training_count": (
                full_meta_fit_count + development_meta_fit_count
            ),
            "model_training_count": model_training_count,
            "predictive_scoring_count": model_training_count,
            "train_development_prediction_row_count": (
                len(predictions) - validation_prediction_count
            ),
            "validation_prediction_row_count": validation_prediction_count,
            "train_development_condition_scoring_count": expected_development,
            "validation_condition_scoring_count": len(validation),
            "validation_threshold_selection_count": 0,
            "accuracy_primary_result_count": 0,
            "statistical_significance_claim_count": 0,
            "feature_level_shap_ablation_count": 0,
            "calibrator_fit_count": 0,
            "xai_execution_count": 0,
            "t1_predictive_access_count": 0,
            "t2_predictive_access_count": 0,
            "final_test_metric_count": 0,
        },
    )
    _write_json(
        output / "implementation_corrections.json",
        {
            "schema_version": VERSION,
            "correction_count": 1,
            "corrections": [
                {
                    "stage": "POST_EXECUTION_RESULT_CONTRACT_AUDIT",
                    "type": "REPORTING_SCHEMA_ONLY",
                    "defect": (
                        "Ceiling diagnostics lacked an explicit modality alias and "
                        "did not echo trigger metrics or predictive-score duplicate "
                        "checks."
                    ),
                    "correction": (
                        "Add modality, trigger_metrics, score-duplicate checks, "
                        "denylist intersection, and top-variable source provenance."
                    ),
                    "scientific_protocol_changed": False,
                    "dataset_changed": False,
                    "search_space_changed": False,
                    "selected_parameters_changed": False,
                    "threshold_changed": False,
                    "validation_result_used_for_model_change": False,
                    "t1_t2_accessed": False,
                }
            ],
        },
    )
    _write_json(
        output / "implementation.json",
        {
            "schema_version": VERSION,
            "implementation_path": (
                "src/experimentation/q1_controlled_result_campaign.py"
            ),
            "implementation_sha256": file_digest(Path(__file__)),
            "configuration_path": str(CONFIG_REL),
            "configuration_sha256": file_digest(root / CONFIG_REL),
            "prior_block_implementations_modified": False,
        },
    )
    report = "\n".join(
        (
            "# Sprint 49 Controlled TRAIN/VALIDATION Campaign Results",
            "",
            f"The campaign produced {len(validation)} primary VALIDATION conditions "
            f"and {expected_development} TRAIN-development condition-fold results. "
            "Every result reports PR-AUC, ROC-AUC, MCC, Recall, Precision, F1, "
            "confusion counts, prevalence, observation count, threshold, and "
            "membership/probability hashes.",
            "",
            "Threshold 0.5 was predeclared and never selected on VALIDATION. All "
            "hyperparameter choices were frozen by TRAIN-side PR-AUC before "
            "VALIDATION scoring. Accuracy is not a primary result. T1 and T2 were "
            "not predictively accessed.",
            "",
            "Tables A–F and explicit full-versus-pairwise ablation comparisons are "
            "provided. Differences are descriptive; no statistical-significance "
            "claim is made. Feature-level SHAP ablation was not executed.",
            "",
            "The automatic ceiling-performance guard produced "
            f"{len(diagnostics)} diagnostic flag(s). Every flag is retained for "
            "audit without changing the dataset or accessing T1/T2.",
            "",
        )
    )
    (output / "REPORT.md").write_text(report, encoding="utf-8")
    _write_manifest(output)
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()
    print(execute(args.root.resolve(), workers=args.workers))


if __name__ == "__main__":
    main()
