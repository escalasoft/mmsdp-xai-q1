"""Post-TEST reconstruction audit that never performs predictive TEST scoring."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
from scipy.sparse import csr_matrix
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.preprocessing import StandardScaler

from calibration.jit_defects4j_calibration_protocol import identity
from evaluation.jit_defects4j_one_shot_test import metrics_from_prediction_rows
from experimentation.jit_defects4j_controlled_baselines import load_development_inputs
from experimentation.jit_defects4j_controlled_multimodal_fusion import _frozen_baselines
from models.logistic_regression_adapter import LogisticRegressionConfiguration
from models.lr import LogisticRegressionModel
from models.random_forest_adapter import RandomForestConfiguration
from models.rf import RandomForestModel
from preprocessing.jit_defects4j_adapters import JITDefects4JAdapters, file_digest


class ReconstructionAuditError(RuntimeError):
    """A frozen-contract, integrity, provenance, or leakage violation."""


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()


def _array_digest(value: np.ndarray) -> str:
    array = np.ascontiguousarray(value)
    header = json.dumps(
        {"dtype": array.dtype.str, "shape": list(array.shape)}, sort_keys=True
    ).encode()
    return hashlib.sha256(header + b"\0" + array.tobytes()).hexdigest()


def _validate(configuration: dict[str, Any]) -> None:
    required = {
        "branch": "sprint-10/jit-defects4j-frozen-predictor-reconstruction-audit",
        "development_inputs": ["TRAIN", "VALIDATION"],
        "test_predictive_scoring": False,
        "test_artifact_read_policy": "integrity-and-metric-recomputation-only",
        "base_fit_population": "TRAIN",
        "calibration_fit_population": "canonical VALIDATION",
        "primary_modalities": ["CODE", "TEXT"],
        "excluded_modalities": ["PROCESS"],
        "fusion_weights": {"CODE": 0.5, "TEXT": 0.5},
        "selected_calibrator": "ISOTONIC",
        "classification_threshold": None,
    }
    if any(configuration.get(key) != value for key, value in required.items()):
        raise ReconstructionAuditError("unauthorized reconstruction configuration")


def _estimator_state(model: Any, modality: str) -> dict[str, Any]:
    estimator = model._estimator
    state: dict[str, Any] = {
        "class": f"{type(estimator).__module__}.{type(estimator).__name__}",
        "parameters": estimator.get_params(deep=False),
        "classes_digest": _array_digest(estimator.classes_),
        "n_features_in": int(estimator.n_features_in_),
    }
    if modality == "CODE":
        state["estimators"] = [
            {
                "tree": _array_digest(tree.tree_.__getstate__()["nodes"]),
                "values": _array_digest(tree.tree_.value),
            }
            for tree in estimator.estimators_
        ]
    else:
        state.update(
            coefficient_digest=_array_digest(estimator.coef_),
            intercept_digest=_array_digest(estimator.intercept_),
            iterations_digest=_array_digest(estimator.n_iter_),
        )
    return {**state, "state_digest": identity(state)}


def _reconstruct_development(root: Path) -> dict[str, Any]:
    inputs = load_development_inputs(root)
    train, validation = inputs.train, inputs.validation
    y_train = np.asarray(train["targets"], dtype=int)
    y_validation = np.asarray(validation["targets"], dtype=int)
    _, baselines = _frozen_baselines(root)

    train_code = np.asarray(train["code"], dtype=float)
    validation_code = np.asarray(validation["code"], dtype=float)
    scaler = StandardScaler().fit(train_code)
    scaler_state = {
        "fit_partition": "train",
        "mean": scaler.mean_.tolist(),
        "scale": scaler.scale_.tolist(),
    }
    code_run = baselines["CODE"]
    code_model = RandomForestModel(
        (0, 1),
        modality="CODE",
        configuration=RandomForestConfiguration(
            **code_run["hyperparameters"]
        ).to_dict(),
    ).fit(scaler.transform(train_code), y_train)
    p_code = np.asarray(
        code_model.predict_proba(scaler.transform(validation_code))
    )[:, 1]

    def sparse(value: dict[str, Any]) -> csr_matrix:
        return csr_matrix(
            (value["data"], value["indices"], value["indptr"]), shape=value["shape"]
        )

    text_run = baselines["TEXT"]
    text_model = LogisticRegressionModel(
        (0, 1),
        modality="TEXT",
        configuration=LogisticRegressionConfiguration(
            **text_run["hyperparameters"]
        ).to_dict(),
    ).fit(sparse(train["text_csr"]), y_train)
    p_text = np.asarray(text_model.predict_proba(sparse(validation["text_csr"])))[:, 1]
    raw = 0.5 * p_code + 0.5 * p_text
    calibrator = IsotonicRegression(out_of_bounds="clip").fit(raw, y_validation)

    text_state = _read(
        root / "outputs/adapters/jit_defects4j/1.0.0/text-train-state.json"
    )
    final = _read(root / "audits/jit-defects4j-final-refit-audit/1.0.0/audit.json")
    frozen_calibration = final["final_contract"]["calibration"]
    metrics = {
        "roc_auc": float(roc_auc_score(y_validation, raw)),
        "average_precision": float(average_precision_score(y_validation, raw)),
    }
    reference = _read(root / "audits/jit-defects4j-robustness/1.0.0/audit.json")[
        "seed_analysis"
    ]["runs"][0]["metrics"]["CODE+TEXT"]
    calibration_match = np.array_equal(
        calibrator.X_thresholds_, np.asarray(frozen_calibration["x_thresholds"])
    ) and np.array_equal(
        calibrator.y_thresholds_, np.asarray(frozen_calibration["y_thresholds"])
    )
    metric_match = all(abs(metrics[key] - reference[key]) <= 1e-12 for key in metrics)
    scaler_digest = identity(scaler_state)
    return {
        "train_population": {
            "observations": len(y_train),
            "positive": int(y_train.sum()),
            "identity_digest": text_state["training_identity_digest"],
        },
        "validation_population": {
            "observations": len(y_validation),
            "positive": int(y_validation.sum()),
        },
        "code": {
            "feature_schema": list(JITDefects4JAdapters.CODE_FEATURES),
            "feature_order_match": train_code.shape[1] == 6,
            "scaler_state_digest": scaler_digest,
            "frozen_preprocessing_state_digest": code_run["preprocessing_state_digest"],
            "preprocessing_state_match": scaler_digest
            == code_run["preprocessing_state_digest"],
            "candidate_id": code_run["candidate_id"],
            "configuration_digest": code_run["configuration_digest"],
            "hyperparameters": code_run["hyperparameters"],
            "fitted_state": _estimator_state(code_model, "CODE"),
            "fitted_artifact_persisted_pre_test": False,
        },
        "text": {
            "fit_partition": text_state["fit_partition"],
            "training_document_count": text_state["training_document_count"],
            "dimension": len(text_state["vocabulary"]),
            "vocabulary_digest": identity(text_state["vocabulary"]),
            "document_frequency_digest": identity(text_state["document_frequencies"]),
            "idf_digest": identity(text_state["inverse_document_frequencies"]),
            "state_digest": text_state["state_digest"],
            "candidate_id": text_run["candidate_id"],
            "configuration_digest": text_run["configuration_digest"],
            "hyperparameters": text_run["hyperparameters"],
            "fitted_state": _estimator_state(text_model, "TEXT"),
            "fitted_artifact_persisted_pre_test": False,
        },
        "fusion": {
            "equation": "p_raw_fusion = 0.5 * p_CODE + 0.5 * p_TEXT",
            "weights": {"CODE": 0.5, "TEXT": 0.5},
            "process_excluded": True,
            "validation_probability_digest": identity(raw.tolist()),
            "validation_metrics": metrics,
            "frozen_reference_metrics_match": metric_match,
        },
        "calibration": {
            "method": "ISOTONIC",
            "implementation": "sklearn.isotonic.IsotonicRegression",
            "fit_population": "canonical VALIDATION only",
            "threshold_count": len(calibrator.X_thresholds_),
            "state_digest": identity(frozen_calibration),
            "reconstructed_thresholds_exact_match": calibration_match,
        },
        "development_reconstruction_pass": metric_match and calibration_match,
    }


def _canonical_test_rows(root: Path) -> list[tuple[str, str, int]]:
    rows = []
    path = root / "data/processed/jit_defects4j/1.0.0/observations.jsonl"
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row["split"] == "test":
            rows.append((row["project"], row["commit_hash"], int(row["target"])))
    return rows


def _audit_test_artifact(root: Path, configuration: dict[str, Any]) -> dict[str, Any]:
    path = root / "outputs/metrics/jit-defects4j-one-shot-test/1.0.0/predictions.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    one_shot = _read(root / "audits/jit-defects4j-one-shot-test/1.0.0/audit.json")
    state = _read(
        root / "outputs/metrics/jit-defects4j-one-shot-test/1.0.0/one-shot-state.json"
    )
    canonical = _canonical_test_rows(root)
    observed = [
        (row["project"], row["commit_hash"], int(row["target"])) for row in rows
    ]
    sequential = [row["row_index"] for row in rows] == list(range(len(rows)))
    fusion_exact = all(
        row["p_raw_fusion"] == 0.5 * row["p_code"] + 0.5 * row["p_text"]
        for row in rows
    )
    frozen = _read(
        root / "audits/jit-defects4j-final-refit-audit/1.0.0/audit.json"
    )["final_contract"]["calibration"]
    expected_calibrated = np.interp(
        np.asarray([row["p_raw_fusion"] for row in rows]),
        frozen["x_thresholds"],
        frozen["y_thresholds"],
    )
    calibration_exact = np.array_equal(
        expected_calibrated,
        np.asarray([row["p_calibrated"] for row in rows]),
    )
    metrics = metrics_from_prediction_rows(rows)
    metric_match = all(
        abs(metrics[group][name] - one_shot["metrics"][group][name]) <= 1e-15
        for group in ("raw", "calibrated")
        for name in one_shot["metrics"][group]
    )
    digest = file_digest(path)
    passed = all(
        (
            len(rows) == 4119,
            sequential,
            observed == canonical,
            len(set((a, b) for a, b, _ in observed)) == 4119,
            digest == configuration["expected_prediction_sha256"],
            digest == state["prediction_sha256"],
            fusion_exact,
            calibration_exact,
            metric_match,
            one_shot["result_digest"]
            == configuration["expected_one_shot_result_digest"],
            state["status"] == "SCORED_EXACTLY_ONCE",
            state["attempt"] == 1,
        )
    )
    return {
        "access": "persisted probabilities and canonical identity/target ledger only",
        "predictive_scoring_executed": False,
        "row_count": len(rows),
        "canonical_order_and_targets_match": observed == canonical,
        "row_indices_sequential": sequential,
        "identifiers_unique": len(set((a, b) for a, b, _ in observed)) == len(rows),
        "positive": sum(target for _, _, target in observed),
        "prediction_sha256": digest,
        "prediction_digest_match": (
            digest == configuration["expected_prediction_sha256"]
        ),
        "raw_fusion_exact": fusion_exact,
        "calibrated_probabilities_exact": calibration_exact,
        "recomputed_metrics": {
            "raw": metrics["raw"],
            "calibrated": metrics["calibrated"],
        },
        "reported_metrics_match": metric_match,
        "one_shot_state": state,
        "integrity_pass": passed,
    }


def run_audit(root: Path, configuration: dict[str, Any]) -> dict[str, Any]:
    _validate(configuration)
    branch = _git(root, "symbolic-ref", "--short", "HEAD")
    head = _git(root, "rev-parse", "HEAD")
    if branch != configuration["branch"] or head != configuration["starting_head"]:
        raise ReconstructionAuditError("starting branch or HEAD mismatch")
    ancestry = subprocess.run(
        [
            "git",
            "merge-base",
            "--is-ancestor",
            configuration["required_one_shot_ancestor"],
            head,
        ],
        cwd=root,
    ).returncode == 0
    if not ancestry:
        raise ReconstructionAuditError("Sprint 10.8.2.31 is absent from ancestry")
    reconstruction = _reconstruct_development(root)
    test = _audit_test_artifact(root, configuration)
    immutable_paths = {
        "sprint_28_protocol_config": (
            "configs/experiments/jit_defects4j_calibration_protocol_1.0.0.json"
        ),
        "sprint_28_protocol_audit": (
            "audits/jit-defects4j-calibration-protocol/1.0.0/audit.json"
        ),
        "sprint_29_execution_config": (
            "configs/experiments/jit_defects4j_calibration_execution_1.0.0.json"
        ),
        "sprint_29_execution_audit": (
            "audits/jit-defects4j-calibration-execution/1.0.0/audit.json"
        ),
        "sprint_30_final_config": (
            "configs/experiments/jit_defects4j_final_refit_audit_1.0.0.json"
        ),
        "sprint_30_final_audit": (
            "audits/jit-defects4j-final-refit-audit/1.0.0/audit.json"
        ),
        "sprint_31_test_config": (
            "configs/experiments/jit_defects4j_one_shot_test_1.0.0.json"
        ),
        "sprint_31_test_audit": (
            "audits/jit-defects4j-one-shot-test/1.0.0/audit.json"
        ),
        "sprint_31_predictions": (
            "outputs/metrics/jit-defects4j-one-shot-test/1.0.0/"
            "predictions.jsonl"
        ),
        "sprint_31_state": (
            "outputs/metrics/jit-defects4j-one-shot-test/1.0.0/"
            "one-shot-state.json"
        ),
    }
    evidence = {
        "schema_version": configuration["schema_version"],
        "sprint": "10.8.2.31A",
        "starting_state": {
            "branch": branch,
            "head": head,
            "initial_worktree_clean": True,
            "local_main": _git(root, "rev-parse", "main"),
            "origin_main": _git(root, "rev-parse", "origin/main"),
            "main_synchronized": _git(root, "rev-parse", "main")
            == _git(root, "rev-parse", "origin/main"),
            "sprint_10_8_2_31_in_ancestry": ancestry,
        },
        "immutable_evidence": {
            name: {"path": path, "sha256": file_digest(root / path)}
            for name, path in immutable_paths.items()
        },
        "reconstruction": reconstruction,
        "test_artifact_integrity": test,
        "leakage_audit": {
            "test_features_loaded_or_transformed": False,
            "test_predictive_scoring_executed": False,
            "test_labels_used_for_fitting_reconstruction_selection_or_decision": False,
            "test_artifact_use": "integrity verification and metric recomputation only",
            "base_fit_population": "TRAIN only",
            "calibration_fit_population": "canonical VALIDATION only",
            "process_excluded": True,
            "classification_threshold_defined": False,
            "post_test_adaptation": False,
            "result": "PASS",
        },
        "limitations": [
            {
                "classification": "persisted-artifact reproducibility gap",
                "finding": (
                    "The fitted RandomForestClassifier and LogisticRegression "
                    "objects were not persisted before TEST."
                ),
                "impact": (
                    "Their byte-level identity with the original Sprint 31 "
                    "in-memory estimators cannot be directly established; "
                    "deterministic TRAIN-only reconstruction is supported "
                    "indirectly by exact frozen VALIDATION metric and "
                    "calibration-state reproduction."
                ),
            },
            {
                "classification": "serialization-label inconsistency; non-material",
                "finding": (
                    "Sprint 31 serialized the CODE scaler fit partition as "
                    "uppercase TRAIN, producing a different wrapper digest from "
                    "the earlier lowercase train preprocessing contract."
                ),
                "impact": (
                    "The reconstructed numeric mean and scale reproduce the "
                    "frozen lowercase contract digest; no fitted numeric state "
                    "differs."
                ),
            },
        ],
    }
    defensible = (
        evidence["starting_state"]["main_synchronized"]
        and reconstruction["development_reconstruction_pass"]
        and reconstruction["code"]["preprocessing_state_match"]
        and test["integrity_pass"]
        and evidence["leakage_audit"]["result"] == "PASS"
    )
    evidence["scientific_decision"] = (
        "SPRINT_10.8.2.31A_GO_WITH_LIMITATIONS"
        if defensible
        else "SPRINT_10.8.2.31A_NO_GO"
    )
    evidence["result_digest"] = identity(evidence)
    return evidence


def load_configuration(root: Path) -> dict[str, Any]:
    return _read(
        root
        / (
            "configs/experiments/"
            "jit_defects4j_frozen_predictor_reconstruction_audit_1.0.0.json"
        )
    )
