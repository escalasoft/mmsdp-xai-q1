"""Fail-closed validation for the frozen JIT-Defects4J calibration protocol."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np


class CalibrationProtocolError(RuntimeError):
    """A frozen architecture, calibration, leakage, or TEST-seal violation."""


def canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
    ).encode()


def identity(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def load_and_validate(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    architecture = json.loads(
        (
            root / "configs/experiments/jit_defects4j_frozen_architecture_1.0.0.json"
        ).read_text()
    )
    protocol = json.loads(
        (
            root / "configs/experiments/jit_defects4j_calibration_protocol_1.0.0.json"
        ).read_text()
    )
    validate_architecture(architecture)
    validate_protocol(protocol)
    verify_repository_evidence(root, architecture)
    return architecture, protocol


def validate_architecture(value: dict[str, Any]) -> None:
    if value.get("primary_modalities") != ["CODE", "TEXT"]:
        raise CalibrationProtocolError("primary modality set must be exactly CODE+TEXT")
    fusion = value.get("fusion", {})
    if (
        fusion.get("weights") != {"CODE": 0.5, "TEXT": 0.5}
        or fusion.get("learned") is not False
    ):
        raise CalibrationProtocolError("fusion must be fixed equal-weight CODE+TEXT")
    semantics = value.get("probability_semantics", {})
    if semantics.get("positive_label") != 1 or semantics.get("source_column") != 1:
        raise CalibrationProtocolError("positive-class probability semantics changed")
    process = value.get("process_status", {})
    if (
        process.get("in_primary_predictor") is not False
        or process.get("retained") is not True
    ):
        raise CalibrationProtocolError("PROCESS status changed")


def validate_protocol(value: dict[str, Any]) -> None:
    if value.get("candidate_methods") != ["UNCALIBRATED", "PLATT", "ISOTONIC"]:
        raise CalibrationProtocolError("calibrator set or order changed")
    cross = value.get("cross_fitting", {})
    expected = {
        "partition": "VALIDATION",
        "splitter": "StratifiedKFold",
        "folds": 5,
        "shuffle": True,
        "random_seed": 108228,
    }
    if any(
        cross.get(key) != expected_value for key, expected_value in expected.items()
    ):
        raise CalibrationProtocolError("cross-fitting contract changed")
    ece = value.get("metrics", {}).get("ece", {})
    if (
        ece.get("bins") != 10
        or ece.get("edges") != [i / 10 for i in range(11)]
        or not all(
            ece.get(key) for key in ("intervals", "empty_bins", "formula", "weighting")
        )
    ):
        raise CalibrationProtocolError("ECE is incomplete or changed")
    selection = value.get("selection_rule", {})
    if (
        selection.get("final_tie_order") != value["candidate_methods"]
        or selection.get("primary_absolute_tolerance") != 1e-12
        or selection.get("secondary_absolute_tolerance") != 1e-12
    ):
        raise CalibrationProtocolError("selection/tie contract changed")
    if (
        value.get("threshold_separation", {}).get(
            "calibrator_selection_uses_threshold_metrics"
        )
        is not False
    ):
        raise CalibrationProtocolError("thresholding must remain separate")
    if value.get("test_seal", {}).get("TEST_SEALED") is not True:
        raise CalibrationProtocolError("TEST must remain sealed")
    safeguards = value.get("leakage_safeguards", {})
    if any(
        safeguards.get(key) is not False
        for key in (
            "test_derived_transformations",
            "test_calibrator_fit",
            "test_method_selection",
            "test_threshold_selection",
            "project_identifier_as_predictor",
        )
    ):
        raise CalibrationProtocolError("leakage safeguard weakened")


def verify_repository_evidence(root: Path, architecture: dict[str, Any]) -> None:
    robustness = json.loads(
        (root / "audits/jit-defects4j-robustness/1.0.0/audit.json").read_text()
    )
    adapter = json.loads(
        (root / "audits/jit-defects4j-adapters/1.0.0/audit.json").read_text()
    )
    expected = {
        key: architecture["dataset"][key]
        for key in (
            "identity",
            "manifest_sha256",
            "frozen_boundary_identity",
            "adapter_identity",
        )
    }
    actual = {
        "identity": robustness["dataset_identity"],
        "manifest_sha256": robustness["canonical_manifest_sha256"],
        "frozen_boundary_identity": robustness["frozen_boundary_identity"],
        "adapter_identity": robustness["adapter_identity"],
    }
    if actual != expected:
        raise CalibrationProtocolError(
            "dataset/manifest/boundary/adapter identity mismatch"
        )
    if (
        robustness.get("results_identity_digest")
        != architecture["prior_evidence"]["result_identity"]
        or robustness.get("decision") != "GO"
    ):
        raise CalibrationProtocolError("Sprint 10.8.2.27 evidence mismatch")
    if (
        not robustness.get("test_sealed")
        or adapter["test_sealing"]["test_matrix_materialized"]
    ):
        raise CalibrationProtocolError("prior evidence does not preserve TEST seal")


def expected_calibration_error(y_true: np.ndarray, probabilities: np.ndarray) -> float:
    y = np.asarray(y_true, dtype=int)
    p = np.asarray(probabilities, dtype=float)
    if (
        y.ndim != 1
        or p.shape != y.shape
        or len(y) == 0
        or not np.isin(y, (0, 1)).all()
        or not np.isfinite(p).all()
        or ((p < 0) | (p > 1)).any()
    ):
        raise CalibrationProtocolError("invalid inputs for predeclared ECE")
    bins = np.minimum((p * 10).astype(int), 9)
    return float(
        sum(
            np.mean(bins == b) * abs(y[bins == b].mean() - p[bins == b].mean())
            for b in range(10)
            if np.any(bins == b)
        )
    )


def select_method(metrics: dict[str, dict[str, float]]) -> str:
    if set(metrics) != {"UNCALIBRATED", "PLATT", "ISOTONIC"}:
        raise CalibrationProtocolError(
            "selection requires exactly the predeclared candidates"
        )
    order = ["UNCALIBRATED", "PLATT", "ISOTONIC"]
    best_brier = min(metrics[name]["brier"] for name in order)
    tied = [name for name in order if abs(metrics[name]["brier"] - best_brier) <= 1e-12]
    best_ece = min(metrics[name]["ece"] for name in tied)
    return next(name for name in tied if abs(metrics[name]["ece"] - best_ece) <= 1e-12)
