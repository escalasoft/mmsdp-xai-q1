"""Sealed-TEST deterministic Qt unimodal baseline execution boundary."""

from __future__ import annotations

import hashlib
import json
import pickle
import platform
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import scipy
import sklearn
from scipy.sparse import csr_matrix

from dataset.model_input import ModelPartitionInput, PreparedModelInput
from dataset.qt_model_input_adaptation import (
    QtModelInputAdaptationPolicy,
    QtModelInputAdaptationResult,
    QtModelInputAdaptationSpecification,
    QtModelInputAdaptationValidation,
)
from models.logistic_regression_adapter import LogisticRegressionConfiguration
from models.lr import LogisticRegressionModel
from models.random_forest_adapter import RandomForestConfiguration
from models.rf import RandomForestModel
from preprocessing.qt_model_ready_preparation import (
    QtModelReadyPreparation,
    prepare_qt_model_ready_inputs,
)

__all__ = ["QtBaselineBoundaryError", "load_qt_model_ready", "run_qt_baselines"]

PARTITIONS = ("train", "validation", "test")
MODALITIES = ("CODE", "PROCESS", "TEXT")
FORBIDDEN = (
    "bug_confidence",
    "fix_keyword_indicator",
    "has_bug_keyword",
    "msg_has_bug_kw",
    "commit_identifier",
    "committed_at",
    "partition",
    "target",
    "issue",
    "candidate",
    "szz",
    "fixing_evidence",
    "reviewer",
    "adjudication",
)


class QtBaselineBoundaryError(RuntimeError):
    """A fail-closed violation of the Sprint 10.8.2.20 boundary."""


def _canonical(value: object, *, pretty: bool = False) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            indent=2 if pretty else None,
            separators=None if pretty else (",", ":"),
        )
        + "\n"
    ).encode()


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _partition(value: dict[str, Any]) -> ModelPartitionInput:
    return ModelPartitionInput(
        value["partition_name"],
        value["identifiers"],
        value["X"],
        value["y"],
        value["feature_names"],
        value["metadata"],
    )


def _prepared(value: dict[str, Any]) -> PreparedModelInput:
    return PreparedModelInput(
        value["dataset_name"],
        value["dataset_version"],
        *(_partition(value[name]) for name in PARTITIONS),
        value["feature_names"],
        value["target_name"],
        value["metadata"],
    )


def load_qt_model_ready(path: str | Path) -> QtModelReadyPreparation:
    """Load, reconstruct, and cryptographically revalidate the frozen input artifact."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    specification = QtModelInputAdaptationSpecification(**raw["specification"])
    policy_values = dict(raw["policy"])
    for key in (
        "modality_order",
        "code_feature_names",
        "process_feature_names",
        "text_feature_names",
    ):
        policy_values[key] = tuple(policy_values[key])
    policy = QtModelInputAdaptationPolicy(**policy_values)
    validation_values = dict(raw["validation"])
    validation_values["modalities"] = tuple(validation_values["modalities"])
    validation_values["error_codes"] = tuple(validation_values["error_codes"])
    source = QtModelInputAdaptationResult(
        specification,
        policy,
        _prepared(raw["code"]),
        _prepared(raw["process"]),
        _prepared(raw["text"]),
        QtModelInputAdaptationValidation(**validation_values),
        raw["source_split_identity_digest"],
        raw["adaptation_identity_digest"],
    )
    return prepare_qt_model_ready_inputs(source)


def _matrix(prepared: QtModelReadyPreparation, modality: str, partition: str):
    source = getattr(getattr(prepared, partition), modality.lower())
    if modality == "TEXT":
        return csr_matrix(
            (source.data, source.indices, source.indptr),
            shape=(source.row_count, source.column_count),
        )
    return np.asarray(source.rows, dtype=float)


def _distribution(targets: tuple[object, ...]) -> dict[str, object]:
    counts = Counter(int(value) for value in targets)
    return {
        "count": len(targets),
        "negative_count": counts[0],
        "positive_count": counts[1],
        "positive_rate": counts[1] / len(targets),
    }


def _metrics(targets, probabilities, threshold: float) -> dict[str, object]:
    from sklearn.metrics import (
        average_precision_score,
        confusion_matrix,
        f1_score,
        matthews_corrcoef,
        precision_score,
        recall_score,
        roc_auc_score,
    )

    y = np.asarray(targets, dtype=int)
    predictions = (probabilities >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, predictions, labels=(0, 1)).ravel()
    return {
        "roc_auc": float(roc_auc_score(y, probabilities)),
        "average_precision": float(average_precision_score(y, probabilities)),
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
    }


def _feature_names(prepared: QtModelReadyPreparation, modality: str) -> tuple[str, ...]:
    return tuple(getattr(prepared, f"{modality.lower()}_feature_names"))


def _model(kind: str, modality: str, configuration: dict[str, object]):
    cls = LogisticRegressionModel if kind == "LR" else RandomForestModel
    return cls((0, 1), modality=modality, configuration=configuration)


def run_qt_baselines(
    prepared: QtModelReadyPreparation, configuration: dict[str, Any]
) -> dict[str, object]:
    """Fit TRAIN and evaluate only TRAIN/VALIDATION for six isolated baselines."""
    if not isinstance(prepared, QtModelReadyPreparation):
        raise TypeError("prepared must be QtModelReadyPreparation")
    if configuration.get("fit_partition") != "train" or configuration.get(
        "evaluation_partitions"
    ) != ["train", "validation"]:
        raise QtBaselineBoundaryError(
            "only TRAIN fit and TRAIN/VALIDATION evaluation are permitted"
        )
    if configuration.get("sealed_partition") != "test":
        raise QtBaselineBoundaryError("TEST must remain sealed")
    if tuple(configuration.get("modalities", ())) != MODALITIES:
        raise QtBaselineBoundaryError("exactly three isolated modalities are required")
    train_distribution = _distribution(prepared.train.y)
    validation_distribution = _distribution(prepared.validation.y)
    if (
        train_distribution["positive_count"] == 0
        or train_distribution["negative_count"] == 0
    ):
        raise QtBaselineBoundaryError(
            "TRAIN must contain both binary target classes before classifier fitting"
        )
    if (
        validation_distribution["positive_count"] == 0
        or validation_distribution["negative_count"] == 0
    ):
        raise QtBaselineBoundaryError(
            "VALIDATION must contain both binary target classes for "
            "ROC-AUC/PR-AUC evaluation"
        )
    threshold = float(configuration["decision_threshold"])
    results = []
    for modality in MODALITIES:
        names = _feature_names(prepared, modality)
        if any(token in name.lower() for name in names for token in FORBIDDEN):
            raise QtBaselineBoundaryError("forbidden leakage predictor")
        train_x = _matrix(prepared, modality, "train")
        for kind in ("LR", "RF"):
            declared = dict(configuration["models"][kind]["hyperparameters"])
            validated = (
                LogisticRegressionConfiguration(**declared)
                if kind == "LR"
                else RandomForestConfiguration(**declared)
            )
            settings = validated.to_dict()
            model = _model(kind, modality, settings)
            model.fit(train_x, prepared.train.y)
            evaluations = {}
            probability_outputs = {}
            for partition in ("train", "validation"):
                probabilities = np.asarray(
                    model.predict_proba(_matrix(prepared, modality, partition))
                )[:, 1]
                probability_outputs[partition] = probabilities.tolist()
                evaluations[partition] = _metrics(
                    getattr(prepared, partition).y, probabilities, threshold
                )
            fitted_bytes = pickle.dumps(model._estimator, protocol=5)
            results.append(
                {
                    "run_id": f"qt-10.8.2.20-{modality.lower()}-{kind.lower()}",
                    "status": "succeeded",
                    "modality": modality,
                    "model": kind,
                    "model_class": configuration["models"][kind]["class"],
                    "hyperparameters": settings,
                    "random_seed": settings["random_state"],
                    "fit_partition": "train",
                    "evaluation_partitions": ["train", "validation"],
                    "feature_names": list(names),
                    "feature_identity_digest": _digest(list(names)),
                    "fitted_model_sha256": hashlib.sha256(fitted_bytes).hexdigest(),
                    "metrics": evaluations,
                    "probabilities": probability_outputs,
                }
            )
    identity = {
        "schema_version": "qt-unimodal-baseline-results-1.0.0",
        "configuration": configuration,
        "preparation_identity_digest": prepared.preparation_identity_digest,
        "source_model_input_identity_digest": (
            prepared.source_model_input_identity_digest
        ),
        "text_policy_digest": prepared.representation_policy.policy_digest,
        "text_state_digest": prepared.text_state.state_digest,
        "partition_identity_digests": {
            name: _digest(list(getattr(prepared, name).identifiers))
            for name in ("train", "validation", "test")
        },
        "class_distributions": {
            "train": train_distribution,
            "validation": validation_distribution,
        },
        "software_versions": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "scikit_learn": sklearn.__version__,
        },
        "metric_definitions": {
            "roc_auc": "sklearn.metrics.roc_auc_score",
            "average_precision": "sklearn.metrics.average_precision_score",
            "precision_recall_f1": "binary fixed-threshold scores with zero_division=0",
            "mcc": "sklearn.metrics.matthews_corrcoef",
            "confusion_matrix": "labels ordered [0,1]",
        },
        "test_sealing": {
            "structural_checks_only": True,
            "predict_called": False,
            "targets_used_for_metrics": False,
            "outcomes_persisted": False,
        },
        "scientific_exclusions": {
            "fusion": False,
            "calibration": False,
            "xai": False,
            "human_18c_consumed": False,
            "test_predictive_evaluation": False,
        },
        "runs": results,
    }
    return {**identity, "results_identity_digest": _digest(identity)}
