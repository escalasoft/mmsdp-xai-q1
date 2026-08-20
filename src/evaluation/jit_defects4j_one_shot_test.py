"""Fail-closed, probability-only, one-shot temporal TEST evaluation."""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from scipy.sparse import csr_matrix
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.preprocessing import StandardScaler

from calibration.jit_defects4j_calibration_protocol import (
    expected_calibration_error,
    identity,
    load_and_validate,
)
from experimentation.jit_defects4j_controlled_multimodal_fusion import _frozen_baselines
from models.logistic_regression_adapter import LogisticRegressionConfiguration
from models.lr import LogisticRegressionModel
from models.random_forest_adapter import RandomForestConfiguration
from models.rf import RandomForestModel
from preprocessing.jit_defects4j_adapters import (
    FORBIDDEN_PREDICTORS,
    FinalEvaluationSeal,
    FrozenInput,
    JITDefects4JAdapters,
    canonical_bytes,
    file_digest,
)
from preprocessing.jit_defects4j_adapters import (
    load_configuration as load_adapter_configuration,
)

EXPECTED_BRANCH = "sprint-10/jit-defects4j-one-shot-test-evaluation"
SPRINT_PATH_PREFIXES = (
    "configs/experiments/jit_defects4j_one_shot_test_1.0.0.json",
    "src/evaluation/",
    "scripts/run_jit_defects4j_one_shot_test.py",
    "tests/evaluation/",
    "audits/jit-defects4j-one-shot-test/",
)


class OneShotTestError(RuntimeError):
    """A pre-flight, leakage, frozen-contract, or one-shot violation."""


@dataclass(frozen=True)
class PreflightAuthorization:
    head: str
    identities: dict[str, str]
    final_contract: dict[str, Any]
    initial_worktree_clean: bool


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True
    )
    return result.stdout.rstrip("\n")


def _validate_configuration(configuration: dict[str, Any]) -> None:
    expected = {
        "branch": EXPECTED_BRANCH,
        "selected_calibrator": "ISOTONIC",
        "primary_modalities": ["CODE", "TEXT"],
        "excluded_modalities": ["PROCESS"],
        "fusion_weights": {"CODE": 0.5, "TEXT": 0.5},
        "classification_threshold": None,
        "ece_edges": [i / 10 for i in range(11)],
    }
    if any(configuration.get(key) != value for key, value in expected.items()):
        raise OneShotTestError("unauthorized one-shot configuration")
    if configuration.get("test") != {
        "observations": 4119,
        "positive": 160,
        "nominal_negative": 3959,
    }:
        raise OneShotTestError("TEST population contract changed")


def _worktree_is_authorized(status: str, require_clean: bool) -> bool:
    if not status:
        return True
    if require_clean:
        return False
    paths = []
    for line in status.splitlines():
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        paths.append(path)
    return bool(paths) and all(path.startswith(SPRINT_PATH_PREFIXES) for path in paths)


def preflight(
    root: Path, configuration: dict[str, Any], *, require_clean: bool = True
) -> PreflightAuthorization:
    """Validate every frozen gate without loading row-level TEST data."""
    _validate_configuration(configuration)
    branch = _git(root, "symbolic-ref", "--short", "HEAD")
    if branch != EXPECTED_BRANCH:
        raise OneShotTestError("wrong branch")
    status = _git(root, "status", "--porcelain=v1")
    if not _worktree_is_authorized(status, require_clean):
        raise OneShotTestError("working tree is dirty or contains non-sprint changes")
    head = _git(root, "rev-parse", "HEAD")
    if head != configuration["expected_head_at_preflight"]:
        raise OneShotTestError("pre-flight HEAD changed")
    if configuration.get("initial_preflight_worktree_clean") is not True:
        raise OneShotTestError("clean initial pre-flight was not recorded")
    ancestor = subprocess.run(
        [
            "git",
            "merge-base",
            "--is-ancestor",
            configuration["required_head_ancestor"],
            head,
        ],
        cwd=root,
    )
    if ancestor.returncode != 0:
        raise OneShotTestError("HEAD does not descend from Sprint 10.8.2.30")

    architecture, protocol = load_and_validate(root)
    final_audit = _read(
        root / "audits/jit-defects4j-final-refit-audit/1.0.0/audit.json"
    )
    calibration = _read(
        root / "audits/jit-defects4j-calibration-execution/1.0.0/audit.json"
    )
    observed = {
        **final_audit["final_contract"]["identities"],
        "final_refit_contract": final_audit["final_contract_digest"],
        "final_refit_audit": final_audit["result_digest"],
    }
    if observed != configuration["expected_identities"]:
        raise OneShotTestError("frozen identity or contract mismatch")
    if (
        identity(architecture) != observed["architecture"]
        or identity(protocol) != observed["calibration_protocol"]
    ):
        raise OneShotTestError("frozen contract digest mismatch")
    if final_audit.get("decision") != "SPRINT_10.8.2.30_GO":
        raise OneShotTestError("final-refit audit did not authorize evaluation")
    if not final_audit.get("test_sealed") or not calibration.get("test_sealed"):
        raise OneShotTestError("TEST was not sealed before this sprint")
    if final_audit["selected_procedure"] != "A_NO_BASE_REFIT":
        raise OneShotTestError("base-refit procedure changed")
    if final_audit["final_contract"]["classification_threshold"] != "UNDEFINED":
        raise OneShotTestError("classification threshold exists")
    prediction = root / configuration["prediction_artifact"]
    state = root / configuration["state_artifact"]
    if prediction.exists() or state.exists():
        raise OneShotTestError("prior or in-progress TEST scoring artifact exists")
    return PreflightAuthorization(
        head,
        observed,
        final_audit["final_contract"],
        configuration["initial_preflight_worktree_clean"],
    )


def reliability_bins(y: np.ndarray, p: np.ndarray) -> list[dict[str, Any]]:
    assignments = np.minimum((p * 10).astype(int), 9)
    return [
        {
            "bin_index": index,
            "lower_bound": index / 10,
            "upper_bound": (index + 1) / 10,
            "upper_bound_inclusive": index == 9,
            "support": int(selected.sum()),
            "mean_predicted_probability": float(p[selected].mean()),
            "observed_positive_fraction": float(y[selected].mean()),
        }
        for index in range(10)
        if (selected := assignments == index).any()
    ]


def probability_metrics(y: np.ndarray, p: np.ndarray) -> dict[str, float]:
    if p.shape != y.shape or not np.isfinite(p).all() or ((p < 0) | (p > 1)).any():
        raise OneShotTestError("invalid probability vector")
    return {
        "roc_auc": float(roc_auc_score(y, p)),
        "average_precision": float(average_precision_score(y, p)),
        "brier": float(brier_score_loss(y, p)),
        "ece": expected_calibration_error(y, p),
    }


def metrics_from_prediction_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    y = np.asarray([row["target"] for row in rows], dtype=int)
    raw = np.asarray([row["p_raw_fusion"] for row in rows], dtype=float)
    calibrated = np.asarray([row["p_calibrated"] for row in rows], dtype=float)
    return {
        "raw": probability_metrics(y, raw),
        "calibrated": probability_metrics(y, calibrated),
        "reliability_bins": reliability_bins(y, calibrated),
    }


def _claim_once(state_path: Path, authorization: PreflightAuthorization) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_bytes(
        {"status": "SCORING_CLAIMED", "head": authorization.head, "attempt": 1}
    )
    try:
        descriptor = os.open(state_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    except FileExistsError as error:
        raise OneShotTestError(
            "second predictive TEST scoring run is forbidden"
        ) from error
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(payload)


def _model_scores(
    train: dict[str, Any], test: dict[str, Any], baselines: dict[str, Any]
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    y_train = np.asarray(train["targets"], dtype=int)
    train_code = np.asarray(train["code"], dtype=float)
    test_code = np.asarray(test["code"], dtype=float)
    scaler = StandardScaler().fit(train_code)
    code_run = baselines["CODE"]
    code_model = RandomForestModel(
        (0, 1),
        modality="CODE",
        configuration=RandomForestConfiguration(
            **code_run["hyperparameters"]
        ).to_dict(),
    )
    code_model.fit(scaler.transform(train_code), y_train)
    p_code = np.asarray(code_model.predict_proba(scaler.transform(test_code)))[:, 1]

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
    )
    text_model.fit(sparse(train["text_csr"]), y_train)
    p_text = np.asarray(text_model.predict_proba(sparse(test["text_csr"])))[:, 1]
    scaler_state = {
        "fit_partition": "TRAIN",
        "mean": scaler.mean_.tolist(),
        "scale": scaler.scale_.tolist(),
    }
    return p_code, p_text, scaler_state


def execute_once(
    root: Path, configuration: dict[str, Any], authorization: PreflightAuthorization
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Open TEST once, score the immutable system once, and persist probabilities."""
    state_path = root / configuration["state_artifact"]
    prediction_path = root / configuration["prediction_artifact"]
    _claim_once(state_path, authorization)

    adapter_config = load_adapter_configuration(
        root / "configs/jit_defects4j_adapters.json"
    )
    source = FrozenInput.load(
        root / "data/processed/jit_defects4j/1.0.0",
        configuration["expected_identities"]["manifest"],
        configuration["expected_identities"]["dataset"],
    )
    adapters = JITDefects4JAdapters(source, adapter_config)
    text_state = adapters.fit("train")
    train = adapters.transform("train").to_dict()
    test = adapters.transform_test(
        FinalEvaluationSeal(
            configuration["expected_identities"]["final_refit_contract"]
        )
    ).to_dict()
    identities = [tuple(item) for item in test["identities"]]
    if len(identities) != 4119 or len(set(identities)) != 4119:
        raise OneShotTestError("TEST identity count or uniqueness mismatch")
    development = set(map(tuple, source.identities["train"])) | set(
        map(tuple, source.identities["validation"])
    )
    if development.intersection(identities):
        raise OneShotTestError("TRAIN/VALIDATION/TEST overlap")
    y = np.asarray(test["targets"], dtype=int)
    if (len(y), int(y.sum()), int((y == 0).sum())) != (4119, 160, 3959):
        raise OneShotTestError("TEST target membership changed")

    _, baselines = _frozen_baselines(root)
    frozen = authorization.final_contract
    for modality in ("CODE", "TEXT"):
        run = baselines[modality]
        expected = frozen[modality.lower()]
        if any(
            run[key] != expected[key]
            for key in (
                "candidate_id",
                "configuration_digest",
                "preprocessing_state_digest",
            )
        ):
            raise OneShotTestError(f"frozen {modality} model identity mismatch")
    p_code, p_text, scaler_state = _model_scores(train, test, baselines)
    raw = 0.5 * p_code + 0.5 * p_text
    calibration = frozen["calibration"]
    calibrator = IsotonicRegression(out_of_bounds="clip")
    calibrator.X_thresholds_ = np.asarray(calibration["x_thresholds"], dtype=float)
    calibrator.y_thresholds_ = np.asarray(calibration["y_thresholds"], dtype=float)
    calibrator.X_min_ = float(calibrator.X_thresholds_[0])
    calibrator.X_max_ = float(calibrator.X_thresholds_[-1])
    calibrator.increasing_ = True
    from scipy.interpolate import interp1d

    calibrator.f_ = interp1d(
        calibrator.X_thresholds_,
        calibrator.y_thresholds_,
        kind="linear",
        bounds_error=False,
        fill_value=(calibrator.y_thresholds_[0], calibrator.y_thresholds_[-1]),
    )
    calibrated = np.asarray(calibrator.predict(raw), dtype=float)
    rows = [
        {
            "row_index": index,
            "project": project,
            "commit_hash": commit_hash,
            "target": int(y[index]),
            "p_code": float(p_code[index]),
            "p_text": float(p_text[index]),
            "p_raw_fusion": float(raw[index]),
            "p_calibrated": float(calibrated[index]),
        }
        for index, (project, commit_hash) in enumerate(identities)
    ]
    prediction_path.parent.mkdir(parents=True, exist_ok=True)
    payload = b"".join(canonical_bytes(row) for row in rows)
    prediction_path.write_bytes(payload)
    prediction_sha = file_digest(prediction_path)
    diagnostics = metrics_from_prediction_rows(rows)
    result = {
        "schema_version": configuration["schema_version"],
        "sprint": "10.8.2.31",
        "scientific_decision": "SPRINT_10.8.2.31_GO",
        "prominent_statement": (
            "THIS IS FINAL ONE-SHOT TEMPORAL TEST EVIDENCE FOR THE FROZEN "
            "CONFIGURATION."
        ),
        "branch": EXPECTED_BRANCH,
        "head_at_preflight": authorization.head,
        "initial_worktree_clean": authorization.initial_worktree_clean,
        "test_opening": "AUTHORIZED_AFTER_ALL_FROZEN_GATES_PASSED",
        "test_scoring_count": 1,
        "frozen_identities": authorization.identities,
        "architecture": (
            "TRAIN-fitted six-feature CODE RF + TRAIN-only 5000-dimensional "
            "unigram TF-IDF TEXT liblinear LR"
        ),
        "fusion": "p_raw_fusion = 0.5 * p_CODE + 0.5 * p_TEXT",
        "selected_calibrator": "ISOTONIC",
        "process": "EXCLUDED FROM PRIMARY PREDICTOR",
        "classification_threshold": "UNDEFINED",
        "test": {
            "observations": 4119,
            "positive": 160,
            "nominal_negative": 3959,
            "prevalence": float(y.mean()),
            "duplicates": 0,
            "development_overlap": 0,
            "canonical_order_preserved": True,
        },
        "metrics": {"raw": diagnostics["raw"], "calibrated": diagnostics["calibrated"]},
        "reliability_bins": diagnostics["reliability_bins"],
        "preprocessing": {
            "code_scaler": {**scaler_state, "digest": identity(scaler_state)},
            "text": {
                "fit_partition": "TRAIN",
                "dimension": 5000,
                "state_digest": text_state.state_digest,
            },
        },
        "leakage_audit": {
            "target_as_predictor": False,
            "future_information_as_predictor": False,
            "fixing_szz_issue_linkage_as_predictor": False,
            "test_labels_during_transformation": False,
            "test_statistics_during_fitting": False,
            "split_or_project_as_predictor": False,
            "test_vocabulary_scaling_calibration_or_weights": False,
            "predictor_schema_denylist_overlap": sorted(
                set(JITDefects4JAdapters.CODE_FEATURES)
                .union({adapter_config["text"]["source_field"]})
                .intersection(FORBIDDEN_PREDICTORS)
            ),
            "result": "PASS",
        },
        "prediction_artifact": {
            "path": configuration["prediction_artifact"],
            "sha256": prediction_sha,
            "row_count": len(rows),
            "schema": list(rows[0]),
            "scientific_identity": identity(rows),
        },
        "limitations": [
            (
                "Single temporal TEST partition from JIT-Defects4J; not external "
                "validation across independent datasets."
            ),
            "No universal generalization, causality, or statistical superiority claim.",
            (
                "Project diagnostics, if derived later from this immutable artifact, "
                "are descriptive only."
            ),
        ],
    }
    result_digest = identity(result)
    final_state = {
        "status": "SCORED_EXACTLY_ONCE",
        "attempt": 1,
        "prediction_sha256": prediction_sha,
        "result_digest": result_digest,
    }
    state_path.chmod(0o644)
    state_path.write_bytes(canonical_bytes(final_state))
    state_path.chmod(0o444)
    return {**result, "result_digest": result_digest}, rows


def load_configuration(root: Path) -> dict[str, Any]:
    return _read(root / "configs/experiments/jit_defects4j_one_shot_test_1.0.0.json")
