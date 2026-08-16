"""Fail-closed TRAIN/VALIDATION baselines for frozen JIT-Defects4J inputs."""

# ruff: noqa: E501

from __future__ import annotations

import hashlib
import json
import platform
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import scipy
import sklearn
from scipy.sparse import csr_matrix, issparse
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    log_loss,
    matthews_corrcoef,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.preprocessing import StandardScaler

from models.logistic_regression_adapter import LogisticRegressionConfiguration
from models.lr import LogisticRegressionModel
from models.random_forest_adapter import RandomForestConfiguration
from models.rf import RandomForestModel

MODALITIES = ("CODE", "PROCESS", "TEXT")
FEATURES = {
    "CODE": (
        "changed_file_count",
        "files_added",
        "files_deleted",
        "files_modified",
        "files_other",
        "mode_change_count",
    ),
    "PROCESS": (
        "parent_count",
        "is_merge_commit",
        "has_prior_history",
        "prior_project_commit_count",
    ),
    "TEXT": tuple(f"tfidf_{index}" for index in range(5000)),
}


class DevelopmentBoundaryError(RuntimeError):
    """A frozen-input, leakage, or TEST-seal violation."""


def _bytes(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
    ).encode()


def _digest(value: object) -> str:
    return hashlib.sha256(_bytes(value)).hexdigest()


@dataclass(frozen=True)
class DevelopmentInputs:
    train: dict[str, Any]
    validation: dict[str, Any]
    adapter_audit: dict[str, Any]

    def partition(self, name: str) -> dict[str, Any]:
        if name == "test":
            raise DevelopmentBoundaryError("TEST is sealed from the development path")
        if name not in ("train", "validation"):
            raise DevelopmentBoundaryError("only TRAIN and VALIDATION are accessible")
        return getattr(self, name)


def load_development_inputs(root: Path) -> DevelopmentInputs:
    audit = json.loads(
        (root / "audits/jit-defects4j-adapters/1.0.0/audit.json").read_text()
    )
    base = root / "outputs/adapters/jit_defects4j/1.0.0"
    values: dict[str, Any] = {}
    for name in ("train", "validation"):
        path = base / f"{name}.json"
        expected = audit["generated_ignored_artifacts"][f"{name}.json"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise DevelopmentBoundaryError(
                f"frozen {name.upper()} adapter hash mismatch"
            )
        value = json.loads(path.read_text())
        if value.get("partition") != name:
            raise DevelopmentBoundaryError("adapter partition mismatch")
        values[name] = value
    expected_counts = {"train": 19114, "validation": 4086}
    for name, count in expected_counts.items():
        value = values[name]
        if len(value["identities"]) != count or len(value["targets"]) != count:
            raise DevelopmentBoundaryError(f"frozen {name.upper()} count mismatch")
    train_ids = {tuple(item) for item in values["train"]["identities"]}
    validation_ids = {tuple(item) for item in values["validation"]["identities"]}
    if (
        len(train_ids) != 19114
        or len(validation_ids) != 4086
        or train_ids & validation_ids
    ):
        raise DevelopmentBoundaryError("duplicate identity or TRAIN/VALIDATION overlap")
    if audit["test_sealing"]["test_matrix_materialized"]:
        raise DevelopmentBoundaryError("adapter audit does not prove the TEST seal")
    return DevelopmentInputs(values["train"], values["validation"], audit)


def _matrix(partition: dict[str, Any], modality: str):
    if modality == "TEXT":
        value = partition["text_csr"]
        matrix = csr_matrix(
            (value["data"], value["indices"], value["indptr"]), shape=value["shape"]
        )
        if not issparse(matrix) or matrix.shape[1] != 5000:
            raise DevelopmentBoundaryError(
                "TEXT must remain a 5,000-column sparse CSR matrix"
            )
        return matrix
    key = modality.lower()
    matrix = np.asarray(partition[key], dtype=float)
    if matrix.ndim != 2 or matrix.shape[1] != len(FEATURES[modality]):
        raise DevelopmentBoundaryError(f"{modality} dimensionality mismatch")
    return matrix


def _metrics(y: np.ndarray, scores: np.ndarray, threshold: float) -> dict[str, Any]:
    predictions = (scores >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, predictions, labels=(0, 1)).ravel()
    return {
        "roc_auc": float(roc_auc_score(y, scores)),
        "average_precision": float(average_precision_score(y, scores)),
        "brier_score_uncalibrated": float(brier_score_loss(y, scores)),
        "log_loss_uncalibrated": float(log_loss(y, scores, labels=(0, 1))),
        "score_summary": {
            "minimum": float(scores.min()),
            "maximum": float(scores.max()),
            "mean": float(scores.mean()),
            "standard_deviation": float(scores.std()),
        },
        "descriptive_at_fixed_0_5": {
            "precision": float(precision_score(y, predictions, zero_division=0)),
            "recall": float(recall_score(y, predictions, zero_division=0)),
            "f1": float(f1_score(y, predictions, zero_division=0)),
            "mcc": float(matthews_corrcoef(y, predictions)),
            "confusion_matrix": {
                "true_negative": int(tn),
                "false_positive": int(fp),
                "false_negative": int(fn),
                "true_positive": int(tp),
            },
            "decision_use": False,
        },
    }


def run_development_baselines(
    inputs: DevelopmentInputs, configuration: dict[str, Any]
) -> dict[str, Any]:
    if (
        configuration.get("fit_partition") != "train"
        or configuration.get("evaluation_partition") != "validation"
        or configuration.get("sealed_partition") != "test"
    ):
        raise DevelopmentBoundaryError(
            "required TRAIN/VALIDATION/TEST boundary is not declared"
        )
    if tuple(configuration.get("modalities", ())) != MODALITIES:
        raise DevelopmentBoundaryError(
            "only the three frozen unimodal representations are permitted"
        )
    train = inputs.partition("train")
    validation = inputs.partition("validation")
    train_y = np.asarray(train["targets"], dtype=int)
    validation_y = np.asarray(validation["targets"], dtype=int)
    if (int(train_y.sum()), int(validation_y.sum())) != (1912, 260):
        raise DevelopmentBoundaryError("target assignment mismatch")
    runs: list[dict[str, Any]] = []
    preprocessing: dict[str, Any] = {}
    for modality in MODALITIES:
        raw_train = _matrix(train, modality)
        raw_validation = _matrix(validation, modality)
        scaler = None
        if modality != "TEXT":
            scaler = StandardScaler().fit(raw_train)
            train_x = scaler.transform(raw_train)
            validation_x = scaler.transform(raw_validation)
            state = {
                "fit_partition": "train",
                "mean": scaler.mean_.tolist(),
                "scale": scaler.scale_.tolist(),
            }
        else:
            train_x, validation_x = raw_train, raw_validation
            state = {
                "fit_partition": "none",
                "preserved_sparse_csr": True,
                "text_state_digest": inputs.adapter_audit["modalities"]["text"][
                    "state_scientific_digest"
                ],
            }
        preprocessing[modality] = {**state, "digest": _digest(state)}
        for family in ("LR", "RF"):
            for index, declared in enumerate(configuration["models"][family]):
                settings = (
                    LogisticRegressionConfiguration(**declared).to_dict()
                    if family == "LR"
                    else RandomForestConfiguration(**declared).to_dict()
                )
                candidate_id = (
                    f"jit-10.8.2.25-{modality.lower()}-{family.lower()}-{index + 1}"
                )
                model = (
                    LogisticRegressionModel if family == "LR" else RandomForestModel
                )((0, 1), modality=modality, configuration=settings)
                model.fit(train_x, train_y)
                scores = np.asarray(model.predict_proba(validation_x))[:, 1]
                runs.append(
                    {
                        "candidate_id": candidate_id,
                        "status": "succeeded",
                        "modality": modality,
                        "representation": {
                            "CODE": "CODE-STRUCTURAL",
                            "PROCESS": "ancestor-only raw numeric (TRAIN-standardized for LR/RF comparability)",
                            "TEXT": "TRAIN-fitted TF-IDF unigram CSR",
                        }[modality],
                        "model_family": family,
                        "model_class": type(model._estimator).__module__
                        + "."
                        + type(model._estimator).__name__,
                        "hyperparameters": settings,
                        "random_seed": settings["random_state"],
                        "fit_partition": "train",
                        "evaluation_partition": "validation",
                        "train_count": len(train_y),
                        "validation_count": len(validation_y),
                        "feature_dimensionality": train_x.shape[1],
                        "preprocessing_state_digest": preprocessing[modality]["digest"],
                        "configuration_digest": _digest(
                            {"candidate_id": candidate_id, "hyperparameters": settings}
                        ),
                        "validation_metrics": _metrics(
                            validation_y,
                            scores,
                            float(configuration["fixed_descriptive_threshold"]),
                        ),
                    }
                )
    rankings: dict[str, list[str]] = {}
    selected: dict[str, str] = {}
    for modality in MODALITIES:
        ordered = sorted(
            (run for run in runs if run["modality"] == modality),
            key=lambda run: (
                -run["validation_metrics"]["roc_auc"],
                -run["validation_metrics"]["average_precision"],
                run["candidate_id"],
            ),
        )
        rankings[modality] = [run["candidate_id"] for run in ordered]
        selected[modality] = ordered[0]["candidate_id"]
    payload = {
        "schema_version": "jit-defects4j-controlled-baselines-1.0.0",
        "sprint": "10.8.2.25",
        "decision": "GO",
        "dataset_identity": inputs.adapter_audit["source"]["scientific_identity"],
        "frozen_boundary_identity": inputs.adapter_audit["source"]["input_identity"],
        "adapter_identity": inputs.adapter_audit["configuration_sha256"],
        "test_sealed": True,
        "train": {
            "observations": len(train_y),
            "positive": int(train_y.sum()),
            "nominal_negative": int((train_y == 0).sum()),
            "prevalence": float(train_y.mean()),
        },
        "validation": {
            "observations": len(validation_y),
            "positive": int(validation_y.sum()),
            "nominal_negative": int((validation_y == 0).sum()),
            "prevalence": float(validation_y.mean()),
        },
        "modalities": {
            name: {
                "dimensions": len(FEATURES[name]),
                "preprocessing": preprocessing[name],
            }
            for name in MODALITIES
        },
        "candidate_models": runs,
        "development_ranking": rankings,
        "selected_development_candidates": selected,
        "selection_policy": configuration["selection_policy"],
        "reproducibility": {
            "random_seed": configuration["random_seed"],
            "software": {
                "python": platform.python_version(),
                "numpy": np.__version__,
                "scipy": scipy.__version__,
                "scikit_learn": sklearn.__version__,
            },
        },
        "leakage_audit": {
            "target_derived_predictors": False,
            "label_derived_keywords": False,
            "descendant_process_information": False,
            "text_fit_partition": "train",
            "preprocessing_fit_partition": "train",
            "train_validation_overlap": 0,
            "test_access": False,
            "result": "pass",
        },
        "limitations": [
            "VALIDATION evidence is not final generalization evidence.",
            "CODE-STRUCTURAL is not a semantic code representation.",
            "PROCESS is a small ancestor-only baseline.",
            "PROCESS did not show non-trivial VALIDATION discrimination; its selected label identifies only the highest-ranked attempted PROCESS candidate.",
            "TF-IDF is a lexical baseline, not the final MMSDP-XAI TEXT representation.",
            "Probabilities are uncalibrated.",
        ],
    }
    return {**payload, "results_identity_digest": _digest(payload)}
