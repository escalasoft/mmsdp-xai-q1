"""Authorized Sprint 55 Block 7 TRAIN/source-only reconstruction.

This module has no T1/T2 inference, equivalence, metric, or XAI path. Mixed
frozen payloads are byte-filtered against a TRAIN whitelist; non-TRAIN rows are
never deserialized, enumerated, counted, or retained.
"""

from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import io
import json
import os
import platform
import shutil
import subprocess
import tempfile
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
import lightgbm
import numpy as np
import scipy
import sklearn
import xgboost
from sklearn.linear_model import LogisticRegression

from experimentation.q1_controlled_late_fusion import FUSION_CONFIGURATIONS
from experimentation.q1_controlled_result_campaign import _meta
from experimentation.q1_controlled_train_validation_baselines import (
    CODE_FEATURES,
    CODE_KEYS,
    LABEL,
    PROCESS_FEATURES,
    PROCESS_KEYS,
    ROW_ID_PATTERN,
    TEXT_KEYS,
    canonical_bytes,
    digest,
)
from experimentation.q1_controlled_unimodal_modeling import (
    ALGORITHMS,
    MODALITIES,
    fit_unimodal,
    predict_positive_probability,
)

VERSION = "q1-xai-train-source-reconstruction-1.0.0"
OUTPUT_REL = Path("audits/q1-xai-reconstruction-execution/1.0.0")
FREEZE_REL = Path("audits/q1-apachejit-final-dataset-freeze/1.0.0")
PLAN_REL = Path(
    "audits/q1-t1-confirmatory-execution/1.0.0/engine/engine_readiness.json"
)
CAMPAIGN_REL = Path("audits/q1-controlled-train-validation-baselines/1.0.0/campaign")
UNIMODAL_REL = Path(
    "audits/q1-controlled-train-validation-baselines/1.0.0/"
    "unimodal_contract/unimodal_contract.json"
)
FUSION_REL = Path(
    "audits/q1-controlled-train-validation-baselines/1.0.0/"
    "late_fusion_contract/late_fusion_contract.json"
)
CALIBRATION_REL = Path(
    "audits/q1-development-only-calibration/1.0.0/calibrator_states.jsonl.gz"
)
BLOCK6_REL = Path("audits/q1-xai-reconstruction-equivalence-protocol/1.0.0")
BLOCK6A_REL = BLOCK6_REL / "amendments/historical_design_rationale/1.0.0"
EXPECTED_RUNTIME = {
    "python": "3.11.14",
    "numpy": "2.4.6",
    "scipy": "1.17.1",
    "scikit-learn": "1.9.0",
    "xgboost": "3.2.0",
    "lightgbm": "4.6.0",
}
EXPECTED_PARENT_MANIFEST = (
    "17341b4a585baab73118f21cc1056914326b61cba6751b16ff91bdf4b3dfc386"
)
EXPECTED_AMENDMENT_MANIFEST = (
    "c9502cb1ec85d3053b8a972d61657038e66d04fb5e619b0fe08ed94d581c91bb"
)
SEED = 20260901
REPETITIONS = 3


class ReconstructionError(RuntimeError):
    """Raised when an authorized reconstruction prerequisite fails closed."""


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _file_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_bytes(value) + b"\n"
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(payload)
    os.replace(temporary, path)


def _array_descriptor(value: Any) -> dict[str, Any]:
    array = np.ascontiguousarray(np.asarray(value))
    return {
        "dtype": array.dtype.str,
        "shape": list(array.shape),
        "sha256": _sha256_bytes(array.tobytes(order="C")),
    }


def _float64_output_bytes(value: Any) -> bytes:
    return np.ascontiguousarray(np.asarray(value, dtype="<f8")).tobytes(order="C")


class ObjectStore:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def put_bytes(self, payload: bytes, suffix: str) -> dict[str, Any]:
        sha256 = _sha256_bytes(payload)
        relative = Path("objects") / f"{sha256}{suffix}"
        destination = self.root.parent / relative
        if not destination.exists():
            temporary = destination.with_suffix(destination.suffix + ".tmp")
            temporary.write_bytes(payload)
            os.replace(temporary, destination)
        elif _file_sha256(destination) != sha256:
            raise ReconstructionError("content-addressed object collision")
        return {"path": str(relative), "sha256": sha256, "bytes": len(payload)}

    def put_file(self, source: Path, suffix: str) -> dict[str, Any]:
        sha256 = _file_sha256(source)
        relative = Path("objects") / f"{sha256}{suffix}"
        destination = self.root.parent / relative
        if not destination.exists():
            os.replace(source, destination)
        else:
            source.unlink()
            if _file_sha256(destination) != sha256:
                raise ReconstructionError("content-addressed file collision")
        return {
            "path": str(relative),
            "sha256": sha256,
            "bytes": destination.stat().st_size,
        }

    def put_array(self, value: Any) -> dict[str, Any]:
        stream = io.BytesIO()
        np.save(stream, np.asarray(value), allow_pickle=False)
        return self.put_bytes(stream.getvalue(), ".npy")


def _load_train_project(root: Path, project: str) -> list[dict[str, Any]]:
    """Load only whitelisted TRAIN rows; never deserialize non-TRAIN content."""
    base = root / FREEZE_REL
    memberships: list[dict[str, Any]] = []
    with gzip.open(base / "temporal_partition_manifest.jsonl.gz", "rb") as stream:
        for line in stream:
            if b'"partition":"TRAIN"' not in line:
                continue
            row = json.loads(line)
            if row["project"] == project:
                memberships.append(row)
    allowed = {row["row_identifier"] for row in memberships}
    if not allowed:
        raise ReconstructionError(f"no TRAIN rows for {project}")

    def selected_payload(name: str, keys: set[str] | frozenset[str]) -> dict[str, Any]:
        selected: dict[str, Any] = {}
        with gzip.open(base / name, "rb") as stream:
            for line in stream:
                match = ROW_ID_PATTERN.search(line)
                if match is None:
                    raise ReconstructionError(f"row id missing in {name}")
                row_id = match.group(1).decode("ascii")
                if row_id not in allowed:
                    continue
                row = json.loads(line)
                if set(row) != set(keys):
                    raise ReconstructionError(f"TRAIN schema mismatch in {name}")
                selected[row_id] = row
        if set(selected) != allowed:
            raise ReconstructionError(f"TRAIN payload incomplete in {name}")
        return selected

    identity: dict[str, Any] = {}
    with gzip.open(base / "row_identity_provenance.jsonl.gz", "rb") as stream:
        for line in stream:
            match = ROW_ID_PATTERN.search(line)
            if match is None:
                raise ReconstructionError("identity row id missing")
            row_id = match.group(1).decode("ascii")
            if row_id in allowed:
                identity[row_id] = json.loads(line)
    if set(identity) != allowed:
        raise ReconstructionError("TRAIN identities incomplete")
    code = selected_payload("code_dataset.jsonl.gz", CODE_KEYS)
    process = selected_payload("process_dataset.jsonl.gz", PROCESS_KEYS)
    text = selected_payload("text_dataset.jsonl.gz", TEXT_KEYS)
    result = []
    for membership in memberships:
        row_id = membership["row_identifier"]
        row_identity = identity[row_id]
        result.append(
            {
                "row_identifier": row_id,
                "project": project,
                "timestamp": row_identity["normalized_utc_timestamp"],
                "commit_sha": row_identity["commit_sha"],
                "partition": "TRAIN",
                "forward_block": membership["forward_block"],
                "target": int(row_identity[LABEL]),
                "C": [float(code[row_id][name]) for name in CODE_FEATURES],
                "P": [float(process[row_id][name]) for name in PROCESS_FEATURES],
                "T": text[row_id]["raw_commit_message"],
            }
        )
    return sorted(result, key=lambda row: (row["timestamp"], row["commit_sha"]))


def _selected_config(
    base: dict[str, Any], algorithm: str, parameters: dict[str, Any]
) -> dict[str, Any]:
    result = copy.deepcopy(base)
    result["algorithms"][algorithm] = dict(parameters)
    return result


def _preprocessor_state(
    pipeline: Any, modality: str
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    if modality == "T":
        vectorizer = pipeline.named_steps["tfidf"]
        names = vectorizer.get_feature_names_out().tolist()
        vocabulary = {
            token: int(index) for token, index in vectorizer.vocabulary_.items()
        }
        representation = {
            "vocabulary": dict(sorted(vocabulary.items())),
            "idf": np.asarray(vectorizer.idf_, dtype=float).tolist(),
            "feature_order": names,
            "parameters": {
                "token_pattern": vectorizer.token_pattern,
                "lowercase": vectorizer.lowercase,
                "ngram_range": list(vectorizer.ngram_range),
                "min_df": vectorizer.min_df,
                "max_features": vectorizer.max_features,
                "sublinear_tf": vectorizer.sublinear_tf,
                "norm": vectorizer.norm,
            },
        }
        state = {
            "type": "TFIDF",
            "vocabulary_sha256": digest(representation["vocabulary"]),
            "idf": _array_descriptor(vectorizer.idf_),
            "feature_order_sha256": digest(names),
            "feature_count": len(names),
            "parameters": representation["parameters"],
        }
        return state, representation
    imputer = pipeline.named_steps["imputer"]
    state = {
        "type": "NUMERIC",
        "imputer_statistics": _array_descriptor(imputer.statistics_),
    }
    if "scaler" in pipeline.named_steps:
        scaler = pipeline.named_steps["scaler"]
        state["scaler"] = {
            "mean": _array_descriptor(scaler.mean_),
            "scale": _array_descriptor(scaler.scale_),
            "var": _array_descriptor(scaler.var_),
            "n_samples_seen": _array_descriptor(scaler.n_samples_seen_),
        }
    return state, None


def _model_state(model: Any, algorithm: str) -> dict[str, Any]:
    common = {
        "algorithm": algorithm,
        "classes": np.asarray(model.classes_).tolist(),
        "n_features_in": int(model.n_features_in_),
    }
    if algorithm == "Logistic Regression":
        return {
            **common,
            "coef": _array_descriptor(model.coef_),
            "intercept": _array_descriptor(model.intercept_),
            "n_iter": _array_descriptor(model.n_iter_),
        }
    if algorithm == "Random Forest":
        tree_digests = []
        for estimator in model.estimators_:
            tree = estimator.tree_
            tree_digests.append(
                digest(
                    {
                        "node_count": int(tree.node_count),
                        "max_depth": int(tree.max_depth),
                        "children_left": _array_descriptor(tree.children_left),
                        "children_right": _array_descriptor(tree.children_right),
                        "feature": _array_descriptor(tree.feature),
                        "threshold": _array_descriptor(tree.threshold),
                        "impurity": _array_descriptor(tree.impurity),
                        "n_node_samples": _array_descriptor(tree.n_node_samples),
                        "weighted_n_node_samples": _array_descriptor(
                            tree.weighted_n_node_samples
                        ),
                        "value": _array_descriptor(tree.value),
                    }
                )
            )
        return {
            **common,
            "estimator_count": len(tree_digests),
            "tree_digests": tree_digests,
        }
    if algorithm == "XGBoost":
        booster = model.get_booster()
        raw = bytes(booster.save_raw(raw_format="ubj"))
        return {
            **common,
            "booster_ubj_sha256": _sha256_bytes(raw),
            "config_sha256": digest(json.loads(booster.save_config())),
        }
    booster = model.booster_
    model_text = booster.model_to_string()
    return {
        **common,
        "booster_text_sha256": _sha256_bytes(model_text.encode()),
        "tree_count": int(booster.num_trees()),
    }


def _native_model_object(
    store: ObjectStore, model: Any, algorithm: str, temporary_dir: Path
) -> dict[str, Any] | None:
    if algorithm == "XGBoost":
        path = temporary_dir / "model.json"
        model.save_model(path)
        reference = store.put_file(path, ".xgb.json")
        loaded = xgboost.XGBClassifier()
        loaded.load_model(store.root.parent / reference["path"])
        if (
            loaded.get_booster().num_boosted_rounds()
            != model.get_booster().num_boosted_rounds()
        ):
            raise ReconstructionError("XGBoost native reload mismatch")
        return reference
    if algorithm == "LightGBM":
        path = temporary_dir / "model.txt"
        model.booster_.save_model(path)
        reference = store.put_file(path, ".lgb.txt")
        loaded = lightgbm.Booster(model_file=str(store.root.parent / reference["path"]))
        if loaded.num_trees() != model.booster_.num_trees():
            raise ReconstructionError("LightGBM native reload mismatch")
        return reference
    return None


def _structural_validate(pipeline: Any, algorithm: str, modality: str) -> None:
    model = pipeline.named_steps["model"]
    if np.asarray(model.classes_).tolist() != [0, 1]:
        raise ReconstructionError("class order is not [0,1]")
    if modality == "T":
        vectorizer = pipeline.named_steps["tfidf"]
        if len(vectorizer.vocabulary_) != len(vectorizer.idf_):
            raise ReconstructionError("TEXT vocabulary/IDF mismatch")
        transformed_features = len(vectorizer.get_feature_names_out())
    else:
        transformed_features = len(
            CODE_FEATURES if modality == "C" else PROCESS_FEATURES
        )
    if int(model.n_features_in_) != transformed_features:
        raise ReconstructionError("predictor/preprocessor feature mismatch")
    if algorithm == "Logistic Regression" and model.coef_.shape != (
        1,
        transformed_features,
    ):
        raise ReconstructionError("LR coefficient dimensions invalid")
    if algorithm == "Random Forest" and len(model.estimators_) != int(
        model.n_estimators
    ):
        raise ReconstructionError("RF estimator count invalid")
    if (
        algorithm == "XGBoost"
        and model.get_booster().num_features() != transformed_features
    ):
        raise ReconstructionError("XGBoost feature dimension invalid")
    if algorithm == "LightGBM" and model.booster_.num_feature() != transformed_features:
        raise ReconstructionError("LightGBM feature dimension invalid")


def _persist_pipeline(
    output: Path,
    store: ObjectStore,
    journal: Any,
    pipeline: Any,
    algorithm: str,
    modality: str,
    logical_id: str,
    repetition: int,
    provenance: dict[str, Any],
    check_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    preprocessing, text_representation = _preprocessor_state(pipeline, modality)
    state = {
        "logical_id": logical_id,
        "provenance": provenance,
        "preprocessing": preprocessing,
        "model": _model_state(pipeline.named_steps["model"], algorithm),
    }
    state_sha256 = digest(state)
    with tempfile.TemporaryDirectory(dir=output / ".tmp") as directory:
        temporary_dir = Path(directory)
        joblib_path = temporary_dir / "pipeline.joblib"
        joblib.dump(pipeline, joblib_path, compress=3, protocol=5)
        executable = store.put_file(joblib_path, ".pipeline.joblib")
        native = _native_model_object(
            store, pipeline.named_steps["model"], algorithm, temporary_dir
        )
    representation = None
    if text_representation is not None:
        representation = store.put_bytes(
            canonical_bytes(text_representation) + b"\n", ".tfidf.json"
        )
    reloaded = joblib.load(output / executable["path"])
    _structural_validate(reloaded, algorithm, modality)
    check = predict_positive_probability(reloaded, check_rows, modality)
    output_bytes = _float64_output_bytes(check)
    output_sha256 = _sha256_bytes(output_bytes)
    output_object = store.put_array(np.asarray(check, dtype="<f8"))
    record = {
        "unit_type": "UNIMODAL_PIPELINE",
        "logical_id": logical_id,
        "repetition": repetition,
        "algorithm": algorithm,
        "modality": modality,
        "g1": "G1_PASS",
        "g2": "G2_PASS",
        "canonical_state_sha256": state_sha256,
        "canonical_state": state,
        "train_source_check_output_sha256": output_sha256,
        "check_row_identity_sha256": digest(
            [row["row_identifier"] for row in check_rows]
        ),
        "check_row_count": len(check_rows),
        "executable": executable,
        "family_native_model": native,
        "text_representation": representation,
        "check_output": output_object,
    }
    journal.write(canonical_bytes(record) + b"\n")
    journal.flush()
    return record


def _persist_meta(
    output: Path,
    store: ObjectStore,
    journal: Any,
    model: LogisticRegression,
    logical_id: str,
    repetition: int,
    provenance: dict[str, Any],
    x: np.ndarray,
    row_ids: list[str],
) -> dict[str, Any]:
    state = {
        "logical_id": logical_id,
        "provenance": provenance,
        "classes": np.asarray(model.classes_).tolist(),
        "coef": _array_descriptor(model.coef_),
        "intercept": _array_descriptor(model.intercept_),
        "n_iter": _array_descriptor(model.n_iter_),
        "n_features_in": int(model.n_features_in_),
    }
    state_sha256 = digest(state)
    with tempfile.TemporaryDirectory(dir=output / ".tmp") as directory:
        path = Path(directory) / "meta.joblib"
        joblib.dump(model, path, compress=3, protocol=5)
        executable = store.put_file(path, ".meta.joblib")
    reloaded = joblib.load(output / executable["path"])
    if np.asarray(reloaded.classes_).tolist() != [0, 1] or reloaded.coef_.shape != (
        1,
        x.shape[1],
    ):
        raise ReconstructionError("fusion meta-state structurally invalid")
    check = reloaded.predict_proba(x)[:, int(np.flatnonzero(reloaded.classes_ == 1)[0])]
    output_sha256 = _sha256_bytes(_float64_output_bytes(check))
    record = {
        "unit_type": "FUSION_META_LEARNER",
        "logical_id": logical_id,
        "repetition": repetition,
        "algorithm": provenance["base_algorithm"],
        "configuration": provenance["configuration"],
        "g1": "G1_PASS",
        "g2": "G2_PASS",
        "canonical_state_sha256": state_sha256,
        "canonical_state": state,
        "train_source_check_output_sha256": output_sha256,
        "check_row_identity_sha256": digest(row_ids),
        "check_row_count": len(row_ids),
        "executable": executable,
        "check_output": store.put_array(np.asarray(check, dtype="<f8")),
    }
    journal.write(canonical_bytes(record) + b"\n")
    journal.flush()
    return record


def _verify_inputs(root: Path) -> dict[str, Any]:
    parent = root / BLOCK6_REL
    amendment = root / BLOCK6A_REL
    checks = {
        "block6_manifest": (
            _file_sha256(parent / "MANIFEST.sha256"),
            EXPECTED_PARENT_MANIFEST,
        ),
        "block6a_manifest": (
            _file_sha256(amendment / "MANIFEST.sha256"),
            EXPECTED_AMENDMENT_MANIFEST,
        ),
        "tolerance": (
            _file_sha256(parent / "numerical_tolerance_policy.json"),
            "62fd3780c94c6a69bfc036bdd4b567409ffc46c8c892a807b221f5d40d0eb336",
        ),
        "gates": (
            _file_sha256(parent / "equivalence_gate_hierarchy.json"),
            "e451edc38b5f2a91f4b00d475ca902a2ae13f319933519b177f607cdd54b3545",
        ),
        "t1_evidence": (
            _file_sha256(
                root / "audits/q1-t1-confirmatory-execution/1.0.0/results/"
                "t1_prediction_evidence.jsonl.gz"
            ),
            "eb4b6956b185e63cd322d92b8cdf96f53fcb09ef83b6a16f2334d660c6f5adc8",
        ),
    }
    failures = [
        name for name, (actual, expected) in checks.items() if actual != expected
    ]
    if failures:
        raise ReconstructionError(f"frozen input mismatch: {failures}")
    runtime = {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "scikit-learn": sklearn.__version__,
        "xgboost": xgboost.__version__,
        "lightgbm": lightgbm.__version__,
    }
    if runtime != EXPECTED_RUNTIME:
        raise ReconstructionError(f"runtime mismatch: {runtime}")
    if platform.machine() != "x86_64":
        raise ReconstructionError("frozen x86_64 runtime required")
    return {
        "status": "PASS_FROZEN_INPUTS_AND_RUNTIME",
        "hash_checks": {
            name: {"actual": actual, "expected": expected, "pass": actual == expected}
            for name, (actual, expected) in checks.items()
        },
        "runtime": runtime,
        "platform": platform.platform(),
        "non_train_payload_policy": (
            "BYTE_FILTER_NO_NONTRAIN_DESERIALIZATION_ENUMERATION_COUNT_OR_RETENTION"
        ),
    }


def _load_isotonic_links(root: Path) -> list[dict[str, Any]]:
    links = []
    with gzip.open(root / CALIBRATION_REL, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            if (
                row["algorithm"] == "LightGBM"
                and row["configuration"] == "P"
                and row["method"] == "ISOTONIC"
                and row["evaluation_origin"] == 11
            ):
                links.append(
                    {
                        "project": row["project"],
                        "state_sha256": digest(row),
                        "fit_membership_digest": row["fit_membership_digest"],
                    }
                )
    if len(links) != 14:
        raise ReconstructionError("isotonic link count mismatch")
    return sorted(links, key=lambda row: row["project"])


def _plan_indexes(
    root: Path,
) -> tuple[
    list[dict[str, Any]],
    dict[tuple[str, str, str], dict[str, Any]],
    dict[tuple[str, str, str], dict[str, Any]],
]:
    plan = _json(root / PLAN_REL)["plan"]
    if len(plan) != 392:
        raise ReconstructionError("plan count mismatch")
    scope = {
        (row["project"], row["algorithm"], row["configuration"]): row for row in plan
    }
    bases: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in plan:
        basis = {
            key: row[key]
            for key in (
                "project",
                "algorithm",
                "configuration",
                "selected_candidate_ids",
                "selected_parameters",
                "train_identity_sha256",
                "preprocessing",
                "late_fusion",
                "calibration",
                "threshold",
            )
        }
        if digest(basis) != row["model_identity_sha256"]:
            raise ReconstructionError("model identity digest mismatch")
        for modality, parameters in row["selected_parameters"].items():
            key = (row["project"], row["algorithm"], modality)
            candidate = {
                "selected_candidate_id": row["selected_candidate_ids"][modality],
                "selected_parameters": parameters,
            }
            if key in bases and bases[key] != candidate:
                raise ReconstructionError(
                    "base selection inconsistent across configurations"
                )
            bases[key] = candidate
    if len(bases) != 168:
        raise ReconstructionError("base selection universe mismatch")
    return plan, bases, scope


def _journal_records(path: Path) -> list[dict[str, Any]]:
    records = []
    with path.open("rb") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise ReconstructionError(
                    f"invalid journal JSON at {path}:{line_number}"
                ) from error
            if not isinstance(record, dict) or "logical_id" not in record:
                raise ReconstructionError(
                    f"invalid component record at {path}:{line_number}"
                )
            records.append(record)
    return records


def _record_object_references(record: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        reference
        for name in (
            "executable",
            "family_native_model",
            "text_representation",
            "check_output",
        )
        if (reference := record.get(name)) is not None
    ]


def _validate_object_reference(output: Path, reference: dict[str, Any]) -> Path:
    relative = Path(reference["path"])
    if relative.is_absolute() or relative.parts[:1] != ("objects",):
        raise ReconstructionError(f"object path escapes object store: {relative}")
    path = output / relative
    if not path.is_file():
        raise ReconstructionError(f"referenced object missing: {relative}")
    if path.stat().st_size != int(reference["bytes"]):
        raise ReconstructionError(f"referenced object size mismatch: {relative}")
    if _file_sha256(path) != reference["sha256"]:
        raise ReconstructionError(f"referenced object digest mismatch: {relative}")
    if path.name.split(".", 1)[0] != reference["sha256"]:
        raise ReconstructionError(f"object name is not digest-bound: {relative}")
    return path


def _validate_recovered_record(
    output: Path,
    record: dict[str, Any],
    repetition: int,
    expected_logical_id: str,
) -> None:
    if record.get("logical_id") != expected_logical_id:
        raise ReconstructionError(
            f"journal order/identity mismatch: {record.get('logical_id')} != "
            f"{expected_logical_id}"
        )
    if record.get("repetition") != repetition:
        raise ReconstructionError(f"repetition mismatch for {expected_logical_id}")
    state = record.get("canonical_state")
    if not isinstance(state, dict) or state.get("logical_id") != expected_logical_id:
        raise ReconstructionError(
            f"canonical identity mismatch for {expected_logical_id}"
        )
    if digest(state) != record.get("canonical_state_sha256"):
        raise ReconstructionError(
            f"canonical state digest mismatch for {expected_logical_id}"
        )
    if record.get("g1") != "G1_PASS" or record.get("g2") != "G2_PASS":
        raise ReconstructionError(
            f"non-terminal component record for {expected_logical_id}"
        )
    references = _record_object_references(record)
    if not references:
        raise ReconstructionError(
            f"component has no persisted objects: {expected_logical_id}"
        )
    paths = {
        reference["path"]: _validate_object_reference(output, reference)
        for reference in references
    }
    check = np.load(paths[record["check_output"]["path"]], allow_pickle=False)
    if len(check) != int(record["check_row_count"]):
        raise ReconstructionError(
            f"check output length mismatch for {expected_logical_id}"
        )
    if _sha256_bytes(_float64_output_bytes(check)) != record.get(
        "train_source_check_output_sha256"
    ):
        raise ReconstructionError(
            f"check output digest mismatch for {expected_logical_id}"
        )
    executable = joblib.load(paths[record["executable"]["path"]])
    if record.get("unit_type") == "UNIMODAL_PIPELINE":
        _structural_validate(executable, record["algorithm"], record["modality"])
    elif record.get("unit_type") == "FUSION_META_LEARNER":
        if np.asarray(executable.classes_).tolist() != [
            0,
            1,
        ] or executable.coef_.shape != (
            1,
            len(record["canonical_state"]["provenance"]["modality_order"]),
        ):
            raise ReconstructionError(
                f"fusion meta-state reload invalid for {expected_logical_id}"
            )
    else:
        raise ReconstructionError(f"unknown unit type for {expected_logical_id}")


def _expected_logical_ids(root: Path, projects: list[str]) -> list[str]:
    expected = []
    for project in projects:
        blocks = sorted(
            {int(row["forward_block"]) for row in _load_train_project(root, project)}
        )
        for algorithm in ALGORITHMS:
            for block in blocks[1:]:
                for modality in MODALITIES:
                    expected.append(
                        f"{project}|{algorithm}|OOF|{modality}|block={block}"
                    )
            for modality in MODALITIES:
                expected.append(f"{project}|{algorithm}|FINAL_BASE|{modality}")
            for configuration in FUSION_CONFIGURATIONS:
                expected.append(f"{project}|{algorithm}|FUSION_META|{configuration}")
    return expected


def _audit_interrupted_execution(
    root: Path, output: Path, projects: list[str]
) -> tuple[dict[int, list[dict[str, Any]]], dict[str, Any]]:
    expected = _expected_logical_ids(root, projects)
    records_by_repetition: dict[int, list[dict[str, Any]]] = {}
    referenced_objects: set[str] = set()
    repetition_states = {}
    for repetition in range(1, REPETITIONS + 1):
        rep_dir = output / "repetitions" / f"rep_{repetition:02d}"
        journal_path = rep_dir / "component_journal.jsonl"
        if not rep_dir.exists():
            records_by_repetition[repetition] = []
            repetition_states[f"rep_{repetition:02d}"] = {
                "classification": "NOT_STARTED",
                "completed_units": 0,
                "incomplete_units": len(expected),
                "failed_units": 0,
                "unresolved_units": 0,
                "last_fully_persisted_unit": None,
                "first_missing_unit": expected[0],
            }
            continue
        if not journal_path.is_file():
            raise ReconstructionError(f"repetition directory lacks journal: {rep_dir}")
        records = _journal_records(journal_path)
        identities = [record["logical_id"] for record in records]
        if len(identities) != len(set(identities)):
            raise ReconstructionError(
                f"duplicate component identity in rep_{repetition:02d}"
            )
        if identities != expected[: len(identities)]:
            raise ReconstructionError(
                f"journal is not a deterministic prefix in rep_{repetition:02d}"
            )
        for logical_id, record in zip(expected, records, strict=False):
            _validate_recovered_record(output, record, repetition, logical_id)
            referenced_objects.update(
                reference["path"] for reference in _record_object_references(record)
            )
        for descriptor_path in sorted(rep_dir.glob("oof_*.json")):
            descriptor = _json(descriptor_path)
            reference = descriptor.get("object")
            if not isinstance(reference, dict):
                raise ReconstructionError(f"invalid OOF descriptor: {descriptor_path}")
            _validate_object_reference(output, reference)
            referenced_objects.add(reference["path"])
        complete = len(records) == len(expected)
        summary_path = rep_dir / "repetition_summary.json"
        if complete:
            expected_summary = {
                "repetition": repetition,
                "component_count": len(records),
                "g1_pass": len(records),
                "g2_pass": len(records),
                "failure_count": 0,
            }
            if not summary_path.is_file() or _json(summary_path) != expected_summary:
                raise ReconstructionError(
                    f"complete repetition summary invalid: rep_{repetition:02d}"
                )
        elif summary_path.exists():
            raise ReconstructionError(
                f"partial repetition has terminal summary: rep_{repetition:02d}"
            )
        records_by_repetition[repetition] = records
        repetition_states[f"rep_{repetition:02d}"] = {
            "classification": "COMPLETE" if complete else "PARTIAL_RECOVERABLE",
            "completed_units": len(records),
            "incomplete_units": len(expected) - len(records),
            "failed_units": 0,
            "unresolved_units": 0,
            "last_fully_persisted_unit": identities[-1] if identities else None,
            "first_missing_unit": None if complete else expected[len(records)],
            "journal_sha256": _file_sha256(journal_path),
        }
    objects = sorted(path for path in (output / "objects").iterdir() if path.is_file())
    bad_objects = [
        str(path.relative_to(output))
        for path in objects
        if _file_sha256(path) != path.name.split(".", 1)[0]
    ]
    if bad_objects:
        raise ReconstructionError(f"object-store digest failures: {bad_objects[:3]}")
    actual_objects = {str(path.relative_to(output)) for path in objects}
    if actual_objects != referenced_objects:
        raise ReconstructionError(
            "object-store/reference mismatch: "
            f"missing={len(referenced_objects - actual_objects)}, "
            f"unresolved_orphan={len(actual_objects - referenced_objects)}"
        )
    populated_sets = [
        set(record["logical_id"] for record in rows)
        for rows in records_by_repetition.values()
        if rows
    ]
    common = set.intersection(*populated_sets) if populated_sets else set()
    by_repetition = {
        repetition: {record["logical_id"]: record for record in rows}
        for repetition, rows in records_by_repetition.items()
    }
    nondeterministic = []
    for logical_id in common:
        state_values = {
            by_repetition[repetition][logical_id]["canonical_state_sha256"]
            for repetition in by_repetition
            if logical_id in by_repetition[repetition]
        }
        output_values = {
            by_repetition[repetition][logical_id]["train_source_check_output_sha256"]
            for repetition in by_repetition
            if logical_id in by_repetition[repetition]
        }
        if len(state_values) != 1 or len(output_values) != 1:
            nondeterministic.append(logical_id)
    if nondeterministic:
        raise ReconstructionError(
            f"recovered components show nondeterminism: {nondeterministic[:3]}"
        )
    state = {
        "expected_units_per_repetition": len(expected),
        "repetitions": repetition_states,
        "object_store": {
            "content_addressed": True,
            "object_count": len(objects),
            "object_bytes": sum(path.stat().st_size for path in objects),
            "digest_failures": 0,
            "missing_references": 0,
            "unresolved_orphans": 0,
        },
        "journal_integrity": {
            "valid_deterministic_prefixes": True,
            "duplicate_component_identities": 0,
            "invalid_persisted_records": 0,
            "shared_units_checked_for_g3": len(common),
            "shared_unit_g3_mismatches": 0,
        },
        "tmp_empty": not (output / ".tmp").exists()
        or not any((output / ".tmp").iterdir()),
    }
    if not state["tmp_empty"]:
        raise ReconstructionError("incomplete transaction remains in .tmp")
    return records_by_repetition, state


def _append_recovery_event(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("ab") as stream:
        stream.write(canonical_bytes(event) + b"\n")
        stream.flush()
        os.fsync(stream.fileno())


def execute(root: Path, *, resume_interrupted: bool = False) -> Path:
    output = root / OUTPUT_REL
    existed = output.exists()
    if existed and not resume_interrupted:
        raise ReconstructionError(f"output already exists: {output}")
    if not existed and resume_interrupted:
        raise ReconstructionError(f"interrupted output does not exist: {output}")
    if not existed:
        output.mkdir(parents=True)
        (output / ".tmp").mkdir()
    objects = ObjectStore(output / "objects")
    recovery_journal = output / "recovery/1.0.0/recovery_journal.jsonl"
    try:
        input_verification = _verify_inputs(root)
        plan, bases, scopes = _plan_indexes(root)
        unimodal_config = _json(root / UNIMODAL_REL)
        fusion_config = _json(root / FUSION_REL)
        provenance_rows = _json(root / CAMPAIGN_REL / "execution_provenance.json")[
            "rows"
        ]
        development_provenance = {
            (row["project"], row["algorithm_family"]): row for row in provenance_rows
        }
        projects = sorted({row["project"] for row in plan})
        authorization = {
            "schema_version": VERSION,
            "human_authorization": "GRANTED_G1_G3_TRAIN_SOURCE_ONLY",
            "authorized": [
                "reconstruction",
                "immediate persistence",
                "G1",
                "G2",
                "G3",
            ],
            "denied": [
                "G4",
                "G5",
                "T1 model query",
                "T2 access",
                "XAI",
                "performance analysis",
            ],
            "repetitions": REPETITIONS,
            "seed": SEED,
        }
        runtime = {
            **input_verification["runtime"],
            "platform": input_verification["platform"],
            "pythonhashseed": os.environ.get("PYTHONHASHSEED"),
            "thread_controls": {
                name: os.environ.get(name)
                for name in (
                    "OMP_NUM_THREADS",
                    "OPENBLAS_NUM_THREADS",
                    "MKL_NUM_THREADS",
                    "VECLIB_MAXIMUM_THREADS",
                    "NUMEXPR_NUM_THREADS",
                )
            },
            "seed": SEED,
        }
        calibration_linkage = {
            "RAW_identity_mappings": 378,
            "ISOTONIC_reused_not_refitted": 14,
            "source": str(CALIBRATION_REL),
            "source_sha256": _file_sha256(root / CALIBRATION_REL),
            "states": _load_isotonic_links(root),
            "calibration_fit_count": 0,
        }

        if existed:
            controls = {
                "authorization.json": authorization,
                "frozen_input_verification.json": input_verification,
                "runtime.json": runtime,
                "calibration_linkage.json": calibration_linkage,
            }
            mismatches = [
                name
                for name, expected in controls.items()
                if _json(output / name) != expected
            ]
            if mismatches:
                raise ReconstructionError(
                    f"interrupted execution control mismatch: {mismatches}"
                )
            recovered_by_repetition, recovery_state = _audit_interrupted_execution(
                root, output, projects
            )
            recovery_dir = output / "recovery/1.0.0"
            recovery_dir.mkdir(parents=True, exist_ok=True)
            provenance_path = recovery_dir / "interruption_recovery.json"
            if provenance_path.exists():
                raise ReconstructionError("recovery provenance already exists")
            branch = subprocess.check_output(
                ["git", "symbolic-ref", "--short", "HEAD"], cwd=root, text=True
            ).strip()
            source_head = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=root, text=True
            ).strip()
            first_partial = next(
                (
                    value["first_missing_unit"]
                    for value in recovery_state["repetitions"].values()
                    if value["classification"] == "PARTIAL_RECOVERABLE"
                ),
                next(
                    (
                        value["first_missing_unit"]
                        for value in recovery_state["repetitions"].values()
                        if value["classification"] == "NOT_STARTED"
                    ),
                    None,
                ),
            )
            recovery_provenance = {
                "schema_version": "q1-xai-block7-interruption-recovery-1.0.0",
                "cause": "EXTERNAL_SESSION_USAGE_LIMIT_INTERRUPTION",
                "interruption_classification": "OPERATIONAL_NOT_SCIENTIFIC",
                "recovery_timestamp_utc": datetime.now(UTC).isoformat(),
                "branch": branch,
                "source_head": source_head,
                "runner_sha256_at_recovery": _file_sha256(Path(__file__)),
                "recovery_starting_state": recovery_state,
                "recovery_decision": "RESUME_EXISTING_NAMESPACE_APPEND_ONLY",
                "resumed_from_component_identity": first_partial,
                "provenance_chain": [
                    "ORIGINAL_INTERRUPTED_EXECUTION",
                    "FORENSIC_RECOVERY_AUDIT",
                    "RESUMED_EXECUTION",
                ],
                "protected_boundaries": {
                    "t1_new_model_query_count": 0,
                    "t2_access_count": 0,
                    "g4_execution_count": 0,
                    "g5_execution_count": 0,
                    "xai_execution_count": 0,
                },
            }
            _atomic_json(provenance_path, recovery_provenance)
            _append_recovery_event(
                recovery_journal,
                {
                    "event": "FORENSIC_RECOVERY_VALIDATED",
                    "timestamp_utc": datetime.now(UTC).isoformat(),
                    "resume_point": first_partial,
                    "recovered_component_count": sum(
                        len(rows) for rows in recovered_by_repetition.values()
                    ),
                },
            )
        else:
            _atomic_json(output / "authorization.json", authorization)
            _atomic_json(output / "frozen_input_verification.json", input_verification)
            _atomic_json(output / "runtime.json", runtime)
            _atomic_json(output / "calibration_linkage.json", calibration_linkage)
            recovered_by_repetition = {
                repetition: [] for repetition in range(1, REPETITIONS + 1)
            }
            recovery_state = None

        all_records: list[list[dict[str, Any]]] = []
        newly_reconstructed: list[dict[str, Any]] = []
        recovered_count = sum(len(rows) for rows in recovered_by_repetition.values())
        failures: list[dict[str, Any]] = []
        for repetition in range(1, REPETITIONS + 1):
            rep_dir = output / "repetitions" / f"rep_{repetition:02d}"
            rep_dir.mkdir(parents=True, exist_ok=True)
            existing_records = recovered_by_repetition[repetition]
            existing_by_id = {
                record["logical_id"]: record for record in existing_records
            }
            records = list(existing_records)
            journal_path = rep_dir / "component_journal.jsonl"
            mode = "ab" if journal_path.exists() else "wb"
            _append_recovery_event(
                recovery_journal,
                {
                    "event": "REPETITION_CONTINUATION_STARTED",
                    "timestamp_utc": datetime.now(UTC).isoformat(),
                    "repetition": repetition,
                    "recovered_valid_completed_components": len(existing_records),
                    "first_missing_component": (
                        _expected_logical_ids(root, projects)[len(existing_records)]
                        if len(existing_records)
                        < len(_expected_logical_ids(root, projects))
                        else None
                    ),
                },
            )
            with journal_path.open(mode) as journal:
                for project in projects:
                    train = _load_train_project(root, project)
                    for algorithm in ALGORITHMS:
                        try:
                            family_provenance = development_provenance[
                                (project, algorithm)
                            ]
                            train_digest = digest(
                                [row["row_identifier"] for row in train]
                            )
                            if (
                                train_digest
                                != family_provenance["train_membership_sha256"]
                            ):
                                raise ReconstructionError("TRAIN_MEMBERSHIP_MISMATCH")
                            modality_configs = {
                                modality: _selected_config(
                                    unimodal_config,
                                    algorithm,
                                    bases[(project, algorithm, modality)][
                                        "selected_parameters"
                                    ],
                                )
                                for modality in MODALITIES
                            }
                            by_block: dict[int, list[dict[str, Any]]] = defaultdict(
                                list
                            )
                            for row in train:
                                by_block[int(row["forward_block"])].append(row)
                            blocks = sorted(by_block)
                            oof_rows: list[dict[str, Any]] = []
                            lineage = []
                            for block in blocks[1:]:
                                fit_rows = [
                                    row
                                    for prior in blocks
                                    if prior < block
                                    for row in by_block[prior]
                                ]
                                score_rows = list(by_block[block])
                                fold_scores = {}
                                for modality in MODALITIES:
                                    logical_id = (
                                        f"{project}|{algorithm}|OOF|{modality}|"
                                        f"block={block}"
                                    )
                                    provenance = {
                                        "project": project,
                                        "algorithm": algorithm,
                                        "modality": modality,
                                        "role": "OOF_FOLD_BASE",
                                        "prediction_block": block,
                                        "fit_membership_sha256": digest(
                                            [row["row_identifier"] for row in fit_rows]
                                        ),
                                        "prediction_membership_sha256": digest(
                                            [
                                                row["row_identifier"]
                                                for row in score_rows
                                            ]
                                        ),
                                        "selected_candidate_id": bases[
                                            (project, algorithm, modality)
                                        ]["selected_candidate_id"],
                                        "selected_parameters": bases[
                                            (project, algorithm, modality)
                                        ]["selected_parameters"],
                                        "seed": SEED,
                                    }
                                    if logical_id in existing_by_id:
                                        record = existing_by_id[logical_id]
                                        if (
                                            record["canonical_state"]["provenance"]
                                            != provenance
                                        ):
                                            raise ReconstructionError(
                                                "recovered provenance mismatch: "
                                                f"{logical_id}"
                                            )
                                        fold_scores[modality] = np.load(
                                            output / record["check_output"]["path"],
                                            allow_pickle=False,
                                        )
                                    else:
                                        pipeline = fit_unimodal(
                                            fit_rows,
                                            algorithm,
                                            modality,
                                            modality_configs[modality],
                                        )
                                        record = _persist_pipeline(
                                            output,
                                            objects,
                                            journal,
                                            pipeline,
                                            algorithm,
                                            modality,
                                            logical_id,
                                            repetition,
                                            provenance,
                                            score_rows,
                                        )
                                        records.append(record)
                                        newly_reconstructed.append(
                                            {
                                                "repetition": repetition,
                                                "logical_id": logical_id,
                                            }
                                        )
                                        fold_scores[modality] = (
                                            predict_positive_probability(
                                                pipeline, score_rows, modality
                                            )
                                        )
                                for index, row in enumerate(score_rows):
                                    oof_rows.append(
                                        {
                                            "row_identifier": row["row_identifier"],
                                            "target": int(row["target"]),
                                            "probabilities": [
                                                float(fold_scores[modality][index])
                                                for modality in MODALITIES
                                            ],
                                        }
                                    )
                                lineage.append(
                                    {
                                        "prediction_block": block,
                                        "fit_blocks": [
                                            prior for prior in blocks if prior < block
                                        ],
                                        "fit_count": len(fit_rows),
                                        "prediction_count": len(score_rows),
                                        "fit_membership_sha256": digest(
                                            [row["row_identifier"] for row in fit_rows]
                                        ),
                                        "prediction_membership_sha256": digest(
                                            [
                                                row["row_identifier"]
                                                for row in score_rows
                                            ]
                                        ),
                                        "strict_forward_and_disjoint": True,
                                    }
                                )
                            if lineage != family_provenance["oof_lineage"]:
                                raise ReconstructionError("OOF lineage mismatch")
                            oof_ids = [row["row_identifier"] for row in oof_rows]
                            if (
                                digest(oof_ids)
                                != family_provenance["meta_training_membership_sha256"]
                            ):
                                raise ReconstructionError(
                                    "meta-training membership mismatch"
                                )

                            for modality in MODALITIES:
                                logical_id = (
                                    f"{project}|{algorithm}|FINAL_BASE|{modality}"
                                )
                                consuming = sorted(
                                    row["model_identity_sha256"]
                                    for row in plan
                                    if row["project"] == project
                                    and row["algorithm"] == algorithm
                                    and modality in row["configuration"].split("+")
                                )
                                provenance = {
                                    "project": project,
                                    "algorithm": algorithm,
                                    "modality": modality,
                                    "role": "FINAL_BASE",
                                    "train_membership_sha256": train_digest,
                                    "selected_candidate_id": bases[
                                        (project, algorithm, modality)
                                    ]["selected_candidate_id"],
                                    "selected_parameters": bases[
                                        (project, algorithm, modality)
                                    ]["selected_parameters"],
                                    "consuming_model_identity_sha256": consuming,
                                    "seed": SEED,
                                }
                                if logical_id in existing_by_id:
                                    if (
                                        existing_by_id[logical_id]["canonical_state"][
                                            "provenance"
                                        ]
                                        != provenance
                                    ):
                                        raise ReconstructionError(
                                            "recovered provenance mismatch: "
                                            f"{logical_id}"
                                        )
                                else:
                                    pipeline = fit_unimodal(
                                        train,
                                        algorithm,
                                        modality,
                                        modality_configs[modality],
                                    )
                                    record = _persist_pipeline(
                                        output,
                                        objects,
                                        journal,
                                        pipeline,
                                        algorithm,
                                        modality,
                                        logical_id,
                                        repetition,
                                        provenance,
                                        train,
                                    )
                                    records.append(record)
                                    newly_reconstructed.append(
                                        {
                                            "repetition": repetition,
                                            "logical_id": logical_id,
                                        }
                                    )

                            oof_x = np.asarray(
                                [row["probabilities"] for row in oof_rows],
                                dtype=float,
                            )
                            oof_y = np.asarray(
                                [row["target"] for row in oof_rows], dtype=int
                            )
                            oof_payload = (
                                canonical_bytes(
                                    {
                                        "row_identifiers": oof_ids,
                                        "targets": oof_y.tolist(),
                                        "probabilities": oof_x.tolist(),
                                    }
                                )
                                + b"\n"
                            )
                            descriptor_path = (
                                rep_dir / f"oof_{digest([project, algorithm])}.json"
                            )
                            if descriptor_path.exists():
                                descriptor = _json(descriptor_path)
                                expected_descriptor = {
                                    "project": project,
                                    "algorithm": algorithm,
                                    "lineage": lineage,
                                    "meta_training_membership_sha256": digest(oof_ids),
                                    "object": descriptor["object"],
                                }
                                if descriptor != expected_descriptor or descriptor[
                                    "object"
                                ]["sha256"] != _sha256_bytes(oof_payload):
                                    raise ReconstructionError(
                                        "recovered OOF descriptor mismatch: "
                                        f"{project} {algorithm}"
                                    )
                            else:
                                oof_object = objects.put_bytes(oof_payload, ".oof.json")
                                _atomic_json(
                                    descriptor_path,
                                    {
                                        "project": project,
                                        "algorithm": algorithm,
                                        "lineage": lineage,
                                        "meta_training_membership_sha256": digest(
                                            oof_ids
                                        ),
                                        "object": oof_object,
                                    },
                                )
                            for (
                                configuration,
                                modalities,
                            ) in FUSION_CONFIGURATIONS.items():
                                columns = [
                                    MODALITIES.index(modality)
                                    for modality in modalities
                                ]
                                scope = scopes[(project, algorithm, configuration)]
                                logical_id = (
                                    f"{project}|{algorithm}|FUSION_META|{configuration}"
                                )
                                provenance = {
                                    "project": project,
                                    "base_algorithm": algorithm,
                                    "configuration": configuration,
                                    "modality_order": list(modalities),
                                    "model_identity_sha256": scope[
                                        "model_identity_sha256"
                                    ],
                                    "meta_training_membership_sha256": digest(oof_ids),
                                    "seed": SEED,
                                }
                                if logical_id in existing_by_id:
                                    if (
                                        existing_by_id[logical_id]["canonical_state"][
                                            "provenance"
                                        ]
                                        != provenance
                                    ):
                                        raise ReconstructionError(
                                            "recovered provenance mismatch: "
                                            f"{logical_id}"
                                        )
                                else:
                                    meta = _meta(fusion_config).fit(
                                        oof_x[:, columns], oof_y
                                    )
                                    record = _persist_meta(
                                        output,
                                        objects,
                                        journal,
                                        meta,
                                        logical_id,
                                        repetition,
                                        provenance,
                                        oof_x[:, columns],
                                        oof_ids,
                                    )
                                    records.append(record)
                                    newly_reconstructed.append(
                                        {
                                            "repetition": repetition,
                                            "logical_id": logical_id,
                                        }
                                    )
                        except Exception as error:
                            failure = {
                                "repetition": repetition,
                                "project": project,
                                "algorithm": algorithm,
                                "stage": "G1_OR_G2_RECOVERY_RECONSTRUCTION",
                                "reason": f"{type(error).__name__}: {error}",
                            }
                            failures.append(failure)
                            _append_recovery_event(
                                recovery_journal,
                                {
                                    "event": "FAIL_CLOSED_COMPONENT_FAMILY",
                                    "timestamp_utc": datetime.now(UTC).isoformat(),
                                    **failure,
                                },
                            )
                            raise
            summary = {
                "repetition": repetition,
                "component_count": len(records),
                "g1_pass": sum(row["g1"] == "G1_PASS" for row in records),
                "g2_pass": sum(row["g2"] == "G2_PASS" for row in records),
                "failure_count": sum(
                    row["repetition"] == repetition for row in failures
                ),
            }
            summary_path = rep_dir / "repetition_summary.json"
            if summary_path.exists():
                if _json(summary_path) != summary:
                    raise ReconstructionError(
                        f"existing summary changed for rep_{repetition:02d}"
                    )
            else:
                _atomic_json(summary_path, summary)
            all_records.append(records)
            _append_recovery_event(
                recovery_journal,
                {
                    "event": "REPETITION_TERMINAL_VALID",
                    "timestamp_utc": datetime.now(UTC).isoformat(),
                    "repetition": repetition,
                    "component_count": len(records),
                    "journal_sha256": _file_sha256(journal_path),
                },
            )

        logical_sets = [
            {row["logical_id"] for row in records} for records in all_records
        ]
        common = set.intersection(*logical_sets) if logical_sets else set()
        union = set.union(*logical_sets) if logical_sets else set()
        g3_results = []
        for logical_id in sorted(union):
            matches = [
                [row for row in records if row["logical_id"] == logical_id]
                for records in all_records
            ]
            if any(len(rows) != 1 for rows in matches):
                result = "G3_INELIGIBLE_UPSTREAM"
                state_values = []
                output_values = []
            else:
                state_values = [rows[0]["canonical_state_sha256"] for rows in matches]
                output_values = [
                    rows[0]["train_source_check_output_sha256"] for rows in matches
                ]
                result = (
                    "G3_PASS_DETERMINISTIC"
                    if len(set(state_values)) == 1 and len(set(output_values)) == 1
                    else "G3_FAIL_NONDETERMINISTIC"
                )
            g3_results.append(
                {
                    "logical_id": logical_id,
                    "result": result,
                    "canonical_state_sha256_by_repetition": state_values,
                    "check_output_sha256_by_repetition": output_values,
                }
            )
        g3_counts = Counter(row["result"] for row in g3_results)
        if failures or common != union:
            outcome = "PARTIAL_G1_G3_RECONSTRUCTION_STOP"
        elif g3_counts["G3_FAIL_NONDETERMINISTIC"]:
            outcome = "RECONSTRUCTION_NONDETERMINISTIC_STOP"
        else:
            outcome = "FULL_G1_G3_RECONSTRUCTION_READY_FOR_HUMAN_BLOCK8_REVIEW"

        unit_types = Counter(row["unit_type"] for row in all_records[0])
        algorithm_counts = Counter(row["algorithm"] for row in all_records[0])
        final_base_count = sum(
            "|FINAL_BASE|" in row["logical_id"] for row in all_records[0]
        )
        oof_base_count = sum("|OOF|" in row["logical_id"] for row in all_records[0])
        meta_count = sum(
            row["unit_type"] == "FUSION_META_LEARNER" for row in all_records[0]
        )
        object_paths = list((output / "objects").iterdir())
        inventory = {
            "schema_version": VERSION,
            "outcome": outcome,
            "logical_reconstruction_units_attempted": len(union),
            "reconstruction_attempts_across_repetitions": sum(
                len(records) for records in all_records
            )
            + len(failures),
            "successful_component_attempts": sum(
                len(records) for records in all_records
            ),
            "recovered_existing_component_attempts": recovered_count,
            "newly_reconstructed_after_recovery_attempts": len(newly_reconstructed),
            "failed_component_or_family_attempts": len(failures),
            "unresolved_logical_units": len(union - common),
            "final_base_predictors_per_repetition": final_base_count,
            "oof_fold_base_predictors_per_repetition": oof_base_count,
            "fusion_meta_learners_per_repetition": meta_count,
            "numeric_final_preprocessing_chains_per_repetition": sum(
                "|FINAL_BASE|" in row["logical_id"]
                and row.get("modality") in {"C", "P"}
                for row in all_records[0]
            ),
            "text_final_vectorizers_per_repetition": sum(
                "|FINAL_BASE|" in row["logical_id"] and row.get("modality") == "T"
                for row in all_records[0]
            ),
            "unit_type_counts_per_repetition": dict(unit_types),
            "algorithm_counts_per_repetition": dict(algorithm_counts),
            "project_count": len(projects),
            "configuration_count": 7,
            "object_count": len(object_paths),
            "object_bytes": sum(path.stat().st_size for path in object_paths),
        }
        _atomic_json(output / "reconstruction_inventory.json", inventory)
        _atomic_json(
            output / "g1_g2_g3_results.json",
            {
                "outcome": outcome,
                "g1_pass_attempts": sum(len(records) for records in all_records),
                "g2_pass_attempts": sum(len(records) for records in all_records),
                "g3_counts": dict(g3_counts),
                "g3_results": g3_results,
                "failures": failures,
            },
        )
        _atomic_json(
            output / "governance_ledger.json",
            {
                "reconstruction_authorization_count": 1,
                "reconstruction_repetition_count": REPETITIONS,
                "reconstructed_component_attempt_count": sum(
                    len(records) for records in all_records
                ),
                "g1_check_count": sum(len(records) for records in all_records)
                + len(failures),
                "g2_check_count": sum(len(records) for records in all_records),
                "g3_check_count": len(g3_results),
                "failure_count": len(failures),
                "t1_model_query_count_block7": 0,
                "t2_access_count_block7": 0,
                "g4_execution_count": 0,
                "g5_execution_count": 0,
                "xai_execution_count": 0,
                "original_t1_predictive_access_count": 1,
                "original_t1_predictive_scoring_count": 1,
                "t1_rerun_permitted": False,
                "t2_state": "DENY_SEALED_REVIEWER_RESERVE",
            },
        )
        if recovery_state is not None:
            _atomic_json(
                output / "recovery/1.0.0/recovery_completion.json",
                {
                    "status": "RECOVERY_COMPLETE",
                    "timestamp_utc": datetime.now(UTC).isoformat(),
                    "initial_state": recovery_state,
                    "exact_resume_point": recovery_state["repetitions"]["rep_02"][
                        "first_missing_unit"
                    ],
                    "recovered_existing_components": recovered_count,
                    "newly_reconstructed_after_recovery": len(newly_reconstructed),
                    "newly_reconstructed_by_repetition": dict(
                        Counter(
                            f"rep_{row['repetition']:02d}"
                            for row in newly_reconstructed
                        )
                    ),
                    "duplicate_component_identities": 0,
                    "failed_components": len(failures),
                    "unresolved_components": len(union - common),
                    "final_repetition_status": {
                        f"rep_{repetition:02d}": "COMPLETE"
                        for repetition in range(1, REPETITIONS + 1)
                    },
                    "journal_chain": {
                        f"rep_{repetition:02d}": {
                            "before_sha256": recovery_state["repetitions"][
                                f"rep_{repetition:02d}"
                            ].get("journal_sha256"),
                            "after_sha256": _file_sha256(
                                output
                                / "repetitions"
                                / f"rep_{repetition:02d}"
                                / "component_journal.jsonl"
                            ),
                            "history_rewritten": False,
                        }
                        for repetition in range(1, REPETITIONS + 1)
                    },
                    "protected_boundaries": {
                        "t1_new_model_query_count": 0,
                        "t2_access_count": 0,
                        "g4_execution_count": 0,
                        "g5_execution_count": 0,
                        "xai_execution_count": 0,
                    },
                },
            )
        report = (
            "# Sprint 55 Block 7 Reconstruction Report\n\n"
            f"Outcome: `{outcome}`.\n\n"
            "The interrupted TRAIN/source-only execution was resumed in its "
            f"original namespace. {recovered_count} valid persisted component "
            "attempts were classified `RECOVERED_EXISTING_COMPONENT`; "
            f"{len(newly_reconstructed)} were classified "
            "`NEWLY_RECONSTRUCTED_AFTER_RECOVERY`; "
            f"failures: {len(failures)}; unresolved components: "
            f"{len(union - common)}.\n\n"
            f"Three repetitions contain {len(union)} logical fitted-state units "
            f"each. Per repetition: {final_base_count} final base predictors, "
            f"{meta_count} fusion LR meta-learners, and {oof_base_count} OOF fold "
            "base states. The 14 frozen isotonic mappings were linked and not "
            "refitted; 378 scopes retain RAW identity calibration.\n\n"
            f"G1 and G2 passed for {sum(len(records) for records in all_records)} "
            f"persisted attempts. G3 results: {dict(g3_counts)}. G3 compares exact "
            "canonical-state SHA-256 and exact canonical float64 TRAIN/source "
            "check-output SHA-256 across all three repetitions.\n\n"
            "No T1 model query, G4, G5, T2 access, performance analysis, SHAP, "
            "LIME, or other XAI occurred. The original Sprint 54 evidence and "
            "`MIXED_CONFIRMATORY_EVIDENCE` classification remain immutable. "
            "Reconstructed artifacts remain `RECONSTRUCTED_CANDIDATE_G1_G3`, "
            "never original Sprint 54 fitted state. Stop for human review before "
            "Block 8.\n"
        )
        (output / "BLOCK7_REPORT.md").write_text(report, encoding="utf-8")
        _append_recovery_event(
            recovery_journal,
            {
                "event": "BLOCK7_G1_G3_RECOVERY_COMPLETE",
                "timestamp_utc": datetime.now(UTC).isoformat(),
                "outcome": outcome,
                "t1_new_model_query_count": 0,
                "t2_access_count": 0,
                "g4_execution_count": 0,
                "g5_execution_count": 0,
                "xai_execution_count": 0,
            },
        )
        shutil.rmtree(output / ".tmp")
        manifest_lines = []
        for path in sorted(
            item
            for item in output.rglob("*")
            if item.is_file() and item.name != "MANIFEST.sha256"
        ):
            manifest_lines.append(f"{_file_sha256(path)}  {path.relative_to(output)}")
        (output / "MANIFEST.sha256").write_text(
            "\n".join(manifest_lines) + "\n", encoding="utf-8"
        )
        return output
    except Exception:
        failure_path = output / "execution_failure.json"
        if not failure_path.exists():
            _atomic_json(
                failure_path,
                {
                    "status": "FAIL_CLOSED",
                    "timestamp_utc": datetime.now(UTC).isoformat(),
                    "t1_model_query_count": 0,
                    "t2_access_count": 0,
                    "xai_execution_count": 0,
                },
            )
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--execute-authorized-g1-g3", action="store_true")
    parser.add_argument("--resume-interrupted-g1-g3", action="store_true")
    arguments = parser.parse_args()
    if arguments.execute_authorized_g1_g3 == arguments.resume_interrupted_g1_g3:
        raise SystemExit(
            "select exactly one of --execute-authorized-g1-g3 or "
            "--resume-interrupted-g1-g3"
        )
    print(
        execute(
            arguments.root.resolve(),
            resume_interrupted=arguments.resume_interrupted_g1_g3,
        )
    )


if __name__ == "__main__":
    main()
