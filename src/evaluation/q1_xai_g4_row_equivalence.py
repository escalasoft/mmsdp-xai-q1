#!/usr/bin/env python3
"""Block 8 G4-only row-level raw T1 equivalence verification.

The module has two explicit phases. ``prepare`` freezes authorization,
representative repetition, exclusions, tolerances, and input hashes without
materializing T1 features or probabilities. ``execute`` verifies those frozen
records, loads only T1-whitelisted feature rows, queries persisted rep_01
objects, and performs row-level raw-probability comparisons. There is no fit,
calibration, metric, T2, G5, threshold, selection, or XAI execution path.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import platform
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

from experimentation.q1_controlled_late_fusion import FUSION_CONFIGURATIONS
from experimentation.q1_controlled_train_validation_baselines import (
    CODE_FEATURES,
    EXPECTED_PROJECTS,
    LABEL,
    PROCESS_FEATURES,
    ROW_ID_PATTERN,
    canonical_bytes,
    digest,
)
from experimentation.q1_controlled_unimodal_modeling import ALGORITHMS, MODALITIES, raw_features


VERSION = "q1-xai-g4-row-equivalence-1.0.0"
OUTPUT_REL = Path("audits/q1-xai-reconstruction-equivalence-g4/1.0.0")
BLOCK7_REL = Path("audits/q1-xai-reconstruction-execution/1.0.0")
BLOCK7B_REL = BLOCK7_REL / "dispositions/block7b_partial_eligibility/1.0.0"
FREEZE_REL = Path("audits/q1-apachejit-final-dataset-freeze/1.0.0")
T1_REL = Path("audits/q1-t1-confirmatory-execution/1.0.0")
BLOCK6_REL = Path("audits/q1-xai-reconstruction-equivalence-protocol/1.0.0")
ELIGIBLE = "G1_G3_ELIGIBLE_FOR_FUTURE_G4_REVIEW"
PASS = "G4_PASS_ROW_LEVEL_RAW_EQUIVALENCE"
FAIL = "G4_FAIL_ROW_LEVEL_RAW_EQUIVALENCE"
UPSTREAM = "G4_INELIGIBLE_UPSTREAM"
UNRESOLVED = "G4_UNRESOLVED_TECHNICAL"
ABSOLUTE_BOUND = 1e-12
RELATIVE_BOUND = 1e-10
RELATIVE_DOMAIN = 1e-8
REPRESENTATIVE = "rep_01"
EXCLUDED = {
    ("apache/zeppelin", "Logistic Regression", "C+T"),
    ("apache/zeppelin", "Logistic Regression", "P+T"),
    ("apache/zeppelin", "Logistic Regression", "C+P+T"),
}
EXPECTED_RUNTIME = {
    "python": "3.11.14",
    "numpy": "2.4.6",
    "scipy": "1.17.1",
    "scikit-learn": "1.9.0",
    "xgboost": "3.2.0",
    "lightgbm": "4.6.0",
}
FROZEN_HASHES = {
    "sprint54_t1_prediction_evidence": (
        T1_REL / "results/t1_prediction_evidence.jsonl.gz",
        "eb4b6956b185e63cd322d92b8cdf96f53fcb09ef83b6a16f2334d660c6f5adc8",
    ),
    "sprint54_manifest": (
        T1_REL / "MANIFEST.sha256",
        "f4f910a5144241b53f7f741ab2e49a5cb541abd8cff88f72c7a05ee30ecaeedf",
    ),
    "block6_manifest": (
        BLOCK6_REL / "MANIFEST.sha256",
        "17341b4a585baab73118f21cc1056914326b61cba6751b16ff91bdf4b3dfc386",
    ),
    "block6a_manifest": (
        BLOCK6_REL / "amendments/historical_design_rationale/1.0.0/MANIFEST.sha256",
        "c9502cb1ec85d3053b8a972d61657038e66d04fb5e619b0fe08ed94d581c91bb",
    ),
    "block7_manifest": (
        BLOCK7_REL / "MANIFEST.sha256",
        "994a6f7aa8d1393904c605e0b5d65db6fcd39b9be55a1eb5219f899346b83d2e",
    ),
    "block7_g1_g2_g3_results": (
        BLOCK7_REL / "g1_g2_g3_results.json",
        "c07a0bd18d1c73e2cddae0ca829de3dd9e698b233d5d27f3f3f8928fb153f8a5",
    ),
    "block7a_manifest": (
        BLOCK7_REL / "forensics/g3_failure_root_cause/1.0.0/MANIFEST.sha256",
        "a6f4bd5e5ec43f844860283aef6b3f21933728a5d0817773e7cb1fb742b866e7",
    ),
    "block7b_manifest": (
        BLOCK7B_REL / "MANIFEST.sha256",
        "6e74700b5deeafb4e70d4e46a07a920df37372aa1f52fd1d17b26d3a7a2fdbeb",
    ),
    "block7b_scope_eligibility_ledger": (
        BLOCK7B_REL / "scope_g1_g3_eligibility.jsonl",
        "2a64d2496c5114c50264f1fbb26d611d7655d91802568c359532e0809fdf043b",
    ),
    "frozen_tolerance_policy": (
        BLOCK6_REL / "numerical_tolerance_policy.json",
        "62fd3780c94c6a69bfc036bdd4b567409ffc46c8c892a807b221f5d40d0eb336",
    ),
}


class G4Error(RuntimeError):
    """Fail-closed G4 prerequisite, alignment, or persistence error."""


def file_sha256(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def bytes_sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_json(path: Path, value: Any) -> None:
    payload = canonical_bytes(value) + b"\n"
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(payload)
    os.replace(temporary, path)


def verify_frozen_hashes(root: Path) -> dict[str, dict[str, Any]]:
    result = {}
    for name, (relative, expected) in FROZEN_HASHES.items():
        path = root / relative
        actual = file_sha256(path)
        if actual != expected:
            raise G4Error(f"immutable input hash mismatch: {name}")
        result[name] = {
            "path": str(relative),
            "expected_sha256": expected,
            "actual_sha256": actual,
            "status": "PASS_EXACT_SHA256",
        }
    return result


def runtime_contract() -> dict[str, Any]:
    observed = {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "scikit-learn": sklearn.__version__,
        "xgboost": xgboost.__version__,
        "lightgbm": lightgbm.__version__,
    }
    threads = {
        name: os.environ.get(name)
        for name in (
            "MKL_NUM_THREADS",
            "NUMEXPR_NUM_THREADS",
            "OMP_NUM_THREADS",
            "OPENBLAS_NUM_THREADS",
            "VECLIB_MAXIMUM_THREADS",
        )
    }
    if observed != EXPECTED_RUNTIME or any(value != "1" for value in threads.values()):
        raise G4Error(f"frozen runtime/thread contract mismatch: {observed}, {threads}")
    if platform.machine() != "x86_64":
        raise G4Error("frozen x86_64 runtime required")
    return {"versions": observed, "thread_controls": threads, "platform": platform.platform()}


def load_scope_ledger(root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    path = root / FROZEN_HASHES["block7b_scope_eligibility_ledger"][0]
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    if len(rows) != 392 or len({row["model_identity_sha256"] for row in rows}) != 392:
        raise G4Error("Block 7B scope universe is not 392 unique identities")
    eligible = [row for row in rows if row["eligibility_outcome"] == ELIGIBLE]
    excluded = [row for row in rows if row["eligibility_outcome"] != ELIGIBLE]
    excluded_keys = {(row["project"], row["algorithm"], row["configuration"]) for row in excluded}
    if len(eligible) != 389 or len(excluded) != 3 or excluded_keys != EXCLUDED:
        raise G4Error("Block 7B authorization/exclusion set changed")
    if any(
        row["G1_state"] != "G1_PASS_ALL_REQUIRED_COMPONENTS"
        or row["G2_state"] != "G2_PASS_ALL_REQUIRED_COMPONENTS"
        or row["G3_dependency_state"] != "G3_PASS_ALL_REQUIRED_COMPONENTS"
        for row in eligible
    ):
        raise G4Error("eligible scope lacks complete G1-G3 pass state")
    return eligible, excluded


def prepare(root: Path) -> None:
    output = root / OUTPUT_REL
    if output.exists():
        raise G4Error(f"refusing to overwrite G4 namespace: {output}")
    hashes = verify_frozen_hashes(root)
    runtime = runtime_contract()
    eligible, excluded = load_scope_ledger(root)
    tolerance = load_json(root / FROZEN_HASHES["frozen_tolerance_policy"][0])
    row_policy = tolerance["row_level_probability_equivalence"]
    if (
        row_policy["maximum_absolute_error"] != ABSOLUTE_BOUND
        or row_policy["maximum_relative_error"] != RELATIVE_BOUND
        or row_policy["relative_error_domain"] != "reference absolute probability >= 1e-8"
    ):
        raise G4Error("frozen row-level tolerance changed")

    output.mkdir(parents=True)
    policy = {
        "schema_version": "q1-xai-g4-representative-reconstruction-policy-1.0.0",
        "created_utc": datetime.now(UTC).isoformat(),
        "status": "FROZEN_BEFORE_ANY_T1_FEATURE_ACCESS_OR_MODEL_QUERY",
        "representative_reconstruction": REPRESENTATIVE,
        "selection_rule": "ALWAYS_REP_01_IF_AND_ONLY_IF_ALL_SCOPE_G3_DEPENDENCIES_PASSED_EXACT_G3",
        "authorized_scope_count": len(eligible),
        "eligible_model_identity_sha256_digest": digest(
            sorted(row["model_identity_sha256"] for row in eligible)
        ),
        "forbidden_selection_inputs": [
            "T1 probability difference",
            "T1 performance",
            "majority repetition",
            "probability averaging",
            "scientific attractiveness",
        ],
        "rep_02_use_for_g3_ineligible_scope": False,
        "refit_or_reconstruction": False,
        "markers": ["NOT_CONFIRMATORY", "NO_MODEL_SELECTION", "NO_SCIENTIFIC_UPDATE"],
    }
    atomic_json(output / "representative_reconstruction_policy.json", policy)
    registry = {
        "schema_version": "q1-xai-g4-sealed-reference-registry-1.0.0",
        "created_utc": datetime.now(UTC).isoformat(),
        "verification_phase": "PRE_QUERY",
        "references": hashes,
        "runtime": runtime,
        "t2_reference_or_content_access": False,
    }
    atomic_json(output / "sealed_reference_registry.json", registry)
    authorization = {
        "schema_version": "q1-xai-g4-authorization-preflight-1.0.0",
        "created_utc": datetime.now(UTC).isoformat(),
        "human_authorization": "GRANTED_G4_ONLY_FOR_BLOCK7B_ELIGIBLE_SCOPES",
        "authorized_scope_count": 389,
        "excluded_scope_count": 3,
        "authorized_model_identity_sha256": sorted(row["model_identity_sha256"] for row in eligible),
        "excluded_scopes": [
            {
                "project": row["project"],
                "algorithm": row["algorithm"],
                "configuration": row["configuration"],
                "model_identity_sha256": row["model_identity_sha256"],
            }
            for row in excluded
        ],
        "representative_policy_sha256": file_sha256(output / "representative_reconstruction_policy.json"),
        "sealed_reference_registry_sha256": file_sha256(output / "sealed_reference_registry.json"),
        "tolerance": {
            "maximum_absolute_error": ABSOLUTE_BOUND,
            "maximum_relative_error": RELATIVE_BOUND,
            "relative_error_reference_minimum_absolute_value": RELATIVE_DOMAIN,
            "every_row_required": True,
            "nan_or_infinite": "FAIL",
            "row_identity_or_order_mismatch": "FAIL",
        },
        "prohibited": ["G5", "XAI", "T2", "refit", "reconstruction", "metrics", "calibration"],
        "markers": ["NOT_CONFIRMATORY", "NO_MODEL_SELECTION", "NO_SCIENTIFIC_UPDATE"],
        "status": "PRE_QUERY_AUTHORIZATION_FROZEN",
    }
    atomic_json(output / "g4_authorization_and_preflight.json", authorization)
    print(json.dumps({"status": authorization["status"], "authorized": 389, "excluded": 3}))


def journal_index(root: Path) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    path = root / BLOCK7_REL / "repetitions/rep_01/component_journal.jsonl"
    records = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    indexed = {row["logical_id"]: row for row in records}
    if len(records) != len(indexed) or len(records) != 1736:
        raise G4Error("rep_01 component journal is incomplete or duplicated")
    g3 = load_json(root / BLOCK7_REL / "g1_g2_g3_results.json")
    states = {row["logical_id"]: row["result"] for row in g3["g3_results"]}
    return indexed, states


def load_executable(root: Path, record: dict[str, Any], g3_states: dict[str, str]) -> Any:
    logical_id = record["logical_id"]
    if record["repetition"] != 1 or record["g1"] != "G1_PASS" or record["g2"] != "G2_PASS":
        raise G4Error(f"component is not valid rep_01 G1/G2 state: {logical_id}")
    if g3_states.get(logical_id) != "G3_PASS_DETERMINISTIC":
        raise G4Error(f"component is not exact-G3 eligible: {logical_id}")
    reference = record["executable"]
    path = root / BLOCK7_REL / reference["path"]
    if (
        not path.is_file()
        or path.stat().st_size != reference["bytes"]
        or file_sha256(path) != reference["sha256"]
        or path.name.split(".", 1)[0] != reference["sha256"]
    ):
        raise G4Error(f"executable object integrity failed: {logical_id}")
    return joblib.load(path)


def load_t1_memberships(root: Path) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = defaultdict(list)
    path = root / FREEZE_REL / "temporal_partition_manifest.jsonl.gz"
    with gzip.open(path, "rb") as stream:
        for line in stream:
            if b'"partition":"T1"' not in line:
                continue
            row = json.loads(line)
            if row["partition"] != "T1" or row["project"] not in EXPECTED_PROJECTS:
                raise G4Error("T1 whitelist membership invalid")
            result[row["project"]].append(row)
    if set(result) != set(EXPECTED_PROJECTS):
        raise G4Error("T1 project whitelist incomplete")
    all_ids = [row["row_identifier"] for project in EXPECTED_PROJECTS for row in result[project]]
    if len(all_ids) != 3787 or len(all_ids) != len(set(all_ids)):
        raise G4Error("T1 whitelist identity count changed")
    return dict(result)


def load_allowed_payload(path: Path, allowed: set[str], expected_keys: set[str]) -> dict[str, dict[str, Any]]:
    selected = {}
    with gzip.open(path, "rb") as stream:
        for line in stream:
            match = ROW_ID_PATTERN.search(line)
            if match is None:
                raise G4Error(f"row identity absent from payload: {path.name}")
            row_id = match.group(1).decode("ascii")
            if row_id not in allowed:
                continue
            row = json.loads(line)
            if set(row) != expected_keys:
                raise G4Error(f"T1 payload schema changed: {path.name}")
            selected[row_id] = row
    if set(selected) != allowed:
        raise G4Error(f"T1 payload incomplete: {path.name}")
    return selected


def load_t1_project(root: Path, memberships: list[dict[str, Any]]) -> list[dict[str, Any]]:
    project = memberships[0]["project"]
    if any(row["partition"] != "T1" or row["project"] != project for row in memberships):
        raise G4Error("non-T1 membership reached feature loader")
    allowed = {row["row_identifier"] for row in memberships}
    base = root / FREEZE_REL
    identity_keys = {
        LABEL, "canonical_project_identifier",
        "canonical_repository_identifier", "commit_sha", "direct_parent_sha",
        "family_group_identifier", "normalized_utc_timestamp", "raw_commit_timestamp",
        "raw_commit_timezone", "row_identifier", "source_apachejit_row_identity",
        "source_artifact_version_reference",
    }
    code = load_allowed_payload(base / "code_dataset.jsonl.gz", allowed, {*CODE_FEATURES, "row_identifier"})
    process = load_allowed_payload(base / "process_dataset.jsonl.gz", allowed, {*PROCESS_FEATURES, "row_identifier"})
    text = load_allowed_payload(
        base / "text_dataset.jsonl.gz", allowed,
        {"raw_commit_message", "raw_commit_message_bytes_base64", "raw_commit_message_sha256", "row_identifier"},
    )
    identities = load_allowed_payload(base / "row_identity_provenance.jsonl.gz", allowed, identity_keys)
    rows = []
    for member in memberships:
        row_id = member["row_identifier"]
        identity = identities[row_id]
        rows.append({
            "row_identifier": row_id,
            "project": project,
            "timestamp": identity["normalized_utc_timestamp"],
            "commit_sha": identity["commit_sha"],
            "partition": "T1",
            "forward_block": member["forward_block"],
            "C": [float(code[row_id][name]) for name in CODE_FEATURES],
            "P": [float(process[row_id][name]) for name in PROCESS_FEATURES],
            "T": text[row_id]["raw_commit_message"],
        })
    return rows


def load_reference_evidence(root: Path) -> dict[tuple[str, str, str], dict[str, Any]]:
    grouped: dict[tuple[str, str, str], dict[str, Any]] = {}
    path = root / FROZEN_HASHES["sprint54_t1_prediction_evidence"][0]
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            key = (row["project"], row["algorithm"], row["configuration"])
            entry = grouped.setdefault(key, {
                "model_identity_sha256": row["model_identity_sha256"],
                "calibration_state": row["calibration_state"],
                "row_identifiers": [],
                "raw_probabilities": [],
            })
            if entry["model_identity_sha256"] != row["model_identity_sha256"]:
                raise G4Error(f"reference model identity drift: {key}")
            entry["row_identifiers"].append(row["row_identifier"])
            entry["raw_probabilities"].append(float(row["raw_predicted_probability"]))
    if len(grouped) != 392:
        raise G4Error("Sprint 54 reference scope universe changed")
    return grouped


def predict_base(model: Any, rows: list[dict[str, Any]], modality: str) -> np.ndarray:
    classes = np.asarray(model.named_steps["model"].classes_)
    positive = np.flatnonzero(classes == 1)
    if len(positive) != 1:
        raise G4Error("base positive-class semantics unavailable")
    value = np.asarray(model.predict_proba(raw_features(rows, modality))[:, positive[0]], dtype="<f8")
    if value.shape != (len(rows),):
        raise G4Error("base predictor output shape mismatch")
    return value


def predict_fusion(model: Any, matrix: np.ndarray) -> np.ndarray:
    classes = np.asarray(model.classes_)
    positive = np.flatnonzero(classes == 1)
    if len(positive) != 1 or int(model.n_features_in_) != matrix.shape[1]:
        raise G4Error("fusion positive-class or modality-width semantics unavailable")
    value = np.asarray(model.predict_proba(matrix)[:, positive[0]], dtype="<f8")
    if value.shape != (len(matrix),):
        raise G4Error("fusion predictor output shape mismatch")
    return value


def float_digest(values: np.ndarray) -> str:
    return bytes_sha256(np.ascontiguousarray(values, dtype="<f8").tobytes(order="C"))


def compare_scope(
    scope: dict[str, Any], reference: dict[str, Any], row_ids: list[str],
    reconstructed: np.ndarray | None, required_base_states: dict[str, str] | None,
    forced_outcome: str | None = None, forced_reason: str | None = None,
) -> dict[str, Any]:
    reference_ids = reference["row_identifiers"]
    reference_values = np.asarray(reference["raw_probabilities"], dtype="<f8")
    aligned = row_ids == reference_ids
    base_record = {
        "schema_version": "q1-xai-g4-scope-result-1.0.0",
        "project": scope["project"], "algorithm": scope["algorithm"],
        "configuration": scope["configuration"],
        "model_identity_sha256": scope["model_identity_sha256"],
        "representative_repetition": REPRESENTATIVE,
        "T1_row_count": len(reference_ids),
        "T1_row_identity_digest": digest(reference_ids),
        "frozen_reference_probability_digest": float_digest(reference_values),
        "calibration_state_recorded_for_future_G5_mapping": reference["calibration_state"],
        "required_base_G4_states": required_base_states,
        "row_alignment_status": "EXACT_IDENTITY_AND_ORDER" if aligned else "MISMATCH",
        "markers": ["NOT_CONFIRMATORY", "NO_MODEL_SELECTION", "NO_SCIENTIFIC_UPDATE"],
    }
    if forced_outcome:
        return {
            **base_record, "reconstructed_probability_digest": None,
            "max_absolute_error": None, "max_relative_error_where_defined": None,
            "relative_error_defined_row_count": 0,
            "rows_with_absolute_bound_violation": 0,
            "rows_with_relative_bound_violation": 0,
            "nan_or_infinite_count": 0,
            "row_probability_comparison_count": 0,
            "G4_outcome": forced_outcome, "exact_failure_reason": forced_reason,
        }
    if reconstructed is None or len(reconstructed) != len(reference_values):
        raise G4Error("comparison vector missing or length mismatch")
    finite = np.isfinite(reconstructed) & np.isfinite(reference_values)
    difference = np.abs(reconstructed - reference_values)
    relative_mask = np.abs(reference_values) >= RELATIVE_DOMAIN
    relative = difference[relative_mask] / np.abs(reference_values[relative_mask])
    absolute_violations = int(np.count_nonzero((difference > ABSOLUTE_BOUND) | ~finite))
    relative_violations = int(np.count_nonzero(relative > RELATIVE_BOUND))
    nonfinite = int(np.count_nonzero(~finite))
    passed = aligned and absolute_violations == 0 and relative_violations == 0 and nonfinite == 0
    reasons = []
    if not aligned: reasons.append("T1 row identity/order mismatch")
    if absolute_violations: reasons.append(f"{absolute_violations} absolute-bound row violations")
    if relative_violations: reasons.append(f"{relative_violations} relative-bound row violations")
    if nonfinite: reasons.append(f"{nonfinite} NaN/Inf values")
    return {
        **base_record,
        "reconstructed_probability_digest": float_digest(reconstructed),
        "max_absolute_error": float(np.max(difference)) if len(difference) else 0.0,
        "max_relative_error_where_defined": float(np.max(relative)) if len(relative) else 0.0,
        "relative_error_defined_row_count": int(np.count_nonzero(relative_mask)),
        "rows_with_absolute_bound_violation": absolute_violations,
        "rows_with_relative_bound_violation": relative_violations,
        "nan_or_infinite_count": nonfinite,
        "row_probability_comparison_count": len(reference_values),
        "G4_outcome": PASS if passed else FAIL,
        "exact_failure_reason": None if passed else "; ".join(reasons),
    }


def distribution(results: list[dict[str, Any]], key: str) -> dict[str, dict[str, int]]:
    output = {}
    for value in sorted({row[key] for row in results}):
        counter = Counter(row["G4_outcome"] for row in results if row[key] == value)
        output[value] = {
            "total": sum(counter.values()), "pass": counter[PASS], "fail": counter[FAIL],
            "ineligible_upstream": counter[UPSTREAM], "unresolved": counter[UNRESOLVED],
        }
    return output


def execute(root: Path) -> None:
    output = root / OUTPUT_REL
    required_preflight = {
        "representative_reconstruction_policy.json", "sealed_reference_registry.json",
        "g4_authorization_and_preflight.json",
    }
    if not output.is_dir() or any(not (output / name).is_file() for name in required_preflight):
        raise G4Error("prepared pre-query authorization package is absent")
    if any((output / name).exists() for name in ("g4_scope_results.jsonl", "g4_summary.json", "MANIFEST.sha256")):
        raise G4Error("refusing to overwrite an existing G4 execution")
    policy = load_json(output / "representative_reconstruction_policy.json")
    authorization = load_json(output / "g4_authorization_and_preflight.json")
    if (
        policy["status"] != "FROZEN_BEFORE_ANY_T1_FEATURE_ACCESS_OR_MODEL_QUERY"
        or policy["representative_reconstruction"] != REPRESENTATIVE
        or authorization["representative_policy_sha256"] != file_sha256(output / "representative_reconstruction_policy.json")
        or authorization["sealed_reference_registry_sha256"] != file_sha256(output / "sealed_reference_registry.json")
    ):
        raise G4Error("pre-query policy/authorization integrity failed")
    hashes_before = verify_frozen_hashes(root)
    runtime = runtime_contract()
    eligible, excluded = load_scope_ledger(root)
    eligible_by_key = {(row["project"], row["algorithm"], row["configuration"]): row for row in eligible}
    references = load_reference_evidence(root)
    for key, scope in eligible_by_key.items():
        if references[key]["model_identity_sha256"] != scope["model_identity_sha256"]:
            raise G4Error(f"reference/ledger model identity mismatch: {key}")
    journal, g3_states = journal_index(root)
    memberships = load_t1_memberships(root)

    results = []
    query_count = 0
    feature_row_access_count = 0
    project_access_count = 0
    dependency_edges = []
    for project in EXPECTED_PROJECTS:
        rows = load_t1_project(root, memberships[project])
        project_access_count += 1
        feature_row_access_count += len(rows)
        row_ids = [row["row_identifier"] for row in rows]
        for algorithm in ALGORITHMS:
            base_probabilities = {}
            base_states = {}
            for modality in MODALITIES:
                key = (project, algorithm, modality)
                scope = eligible_by_key[key]
                logical_id = f"{project}|{algorithm}|FINAL_BASE|{modality}"
                if logical_id not in scope["required_base_components"]:
                    raise G4Error(f"unimodal dependency linkage changed: {key}")
                model = load_executable(root, journal[logical_id], g3_states)
                probabilities = predict_base(model, rows, modality)
                query_count += 1
                result = compare_scope(scope, references[key], row_ids, probabilities, None)
                results.append(result)
                base_probabilities[modality] = probabilities
                base_states[modality] = result["G4_outcome"]
            for configuration, modalities in FUSION_CONFIGURATIONS.items():
                key = (project, algorithm, configuration)
                if key in EXCLUDED:
                    continue
                scope = eligible_by_key[key]
                required_states = {modality: base_states[modality] for modality in modalities}
                failed_bases = [modality for modality, state in required_states.items() if state != PASS]
                if failed_bases:
                    result = compare_scope(
                        scope, references[key], row_ids, None, required_states,
                        UPSTREAM, "Required unimodal raw G4 failure: " + ",".join(failed_bases),
                    )
                    results.append(result)
                    for modality in failed_bases:
                        dependency_edges.append({
                            "from": f"scope:{project}|{algorithm}|{modality}",
                            "to": f"scope:{project}|{algorithm}|{configuration}",
                            "relation": "G4_FAIL_CLOSED_REQUIRED_BASE",
                        })
                    continue
                logical_id = f"{project}|{algorithm}|FUSION_META|{configuration}"
                if scope["required_fusion_component"] != logical_id:
                    raise G4Error(f"fusion dependency linkage changed: {key}")
                record = journal[logical_id]
                if record["canonical_state"]["provenance"]["modality_order"] != list(modalities):
                    raise G4Error(f"frozen fusion modality order changed: {key}")
                if record["canonical_state"]["provenance"]["model_identity_sha256"] != scope["model_identity_sha256"]:
                    raise G4Error(f"fusion model identity linkage changed: {key}")
                model = load_executable(root, record, g3_states)
                matrix = np.column_stack([base_probabilities[modality] for modality in modalities])
                probabilities = predict_fusion(model, matrix)
                query_count += 1
                results.append(compare_scope(scope, references[key], row_ids, probabilities, required_states))

    results.sort(key=lambda row: (row["project"], row["algorithm"], row["configuration"]))
    if len(results) != 389 or len({row["model_identity_sha256"] for row in results}) != 389:
        raise G4Error("G4 result universe is not exactly 389 authorized identities")
    if any((row["project"], row["algorithm"], row["configuration"]) in EXCLUDED for row in results):
        raise G4Error("excluded G3 scope reached G4 results")

    counts = Counter(row["G4_outcome"] for row in results)
    compared_rows = sum(row["row_probability_comparison_count"] for row in results)
    if counts[PASS] == 389:
        outcome = "FULL_G4_RAW_EQUIVALENCE_READY_FOR_G5_REVIEW"
    elif counts[PASS] > 0 and not counts[UNRESOLVED]:
        outcome = "PARTIAL_G4_RAW_EQUIVALENCE_READY_FOR_G5_REVIEW"
    elif counts[UNRESOLVED]:
        outcome = "G4_TECHNICAL_VERIFICATION_UNRESOLVED"
    else:
        outcome = "G4_EQUIVALENCE_INSUFFICIENT_FOR_MEANINGFUL_XAI"
    finite_absolute = [row["max_absolute_error"] for row in results if row["max_absolute_error"] is not None]
    finite_relative = [row["max_relative_error_where_defined"] for row in results if row["max_relative_error_where_defined"] is not None]
    hashes_after = verify_frozen_hashes(root)
    if hashes_before != hashes_after:
        raise G4Error("immutable evidence changed during G4")

    result_path = output / "g4_scope_results.jsonl"
    result_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in results))
    governance = {
        "schema_version": "q1-xai-g4-technical-verification-ledger-1.0.0",
        "ledger_name": "RECONSTRUCTION_EQUIVALENCE_TECHNICAL_VERIFICATION_LEDGER",
        "authorized_scope_count": 389, "excluded_scope_count": 3,
        "technical_t1_access_event_count": 3,
        "technical_t1_feature_access_event_count": 2,
        "technical_t1_identity_schema_diagnostic_access_count": 1,
        "technical_t1_project_batch_count": project_access_count,
        "technical_t1_feature_access_count": feature_row_access_count,
        "technical_t1_feature_row_access_operation_count": feature_row_access_count + 245,
        "pre_query_model_execution_failed_attempt_count": 1,
        "failed_attempt_t1_feature_rows_accessed": 245,
        "failed_attempt_reconstructed_model_query_count": 0,
        "failed_attempt_row_probability_comparison_count": 0,
        "technical_reconstructed_model_query_count": query_count,
        "row_probability_comparison_count": compared_rows,
        "G4_pass_scope_count": counts[PASS], "G4_fail_scope_count": counts[FAIL],
        "G4_ineligible_upstream_count": counts[UPSTREAM], "G4_unresolved_count": counts[UNRESOLVED],
        "historical_t1_predictive_access_count": 1,
        "historical_t1_predictive_scoring_count": 1,
        "historical_t1_rerun": False,
        "T2_access_count": 0, "T2_state": "DENY_SEALED_REVIEWER_RESERVE",
        "G5_execution_count": 0, "XAI_execution_count": 0,
        "refit_count": 0, "reconstruction_count": 0, "metric_recomputation_count": 0,
        "excluded_scope_model_query_count": 0,
        "markers": ["NOT_CONFIRMATORY", "NO_MODEL_SELECTION", "NO_SCIENTIFIC_UPDATE"],
    }
    alignment = {
        "schema_version": "q1-xai-g4-reference-alignment-1.0.0",
        "scope_count": 389,
        "all_scope_model_identities_exact": True,
        "all_compared_row_identities_and_order_exact": all(
            row["row_alignment_status"] == "EXACT_IDENTITY_AND_ORDER" for row in results
        ),
        "comparison_granularity": "EVERY_AUTHORIZED_SCOPE_X_EVERY_PROJECT_T1_ROW",
        "absolute_bound": ABSOLUTE_BOUND, "relative_bound": RELATIVE_BOUND,
        "relative_domain": "abs(reference_probability) >= 1e-8",
        "aggregate_metric_substitution": False,
        "hashes_verified_before": hashes_before, "hashes_verified_after": hashes_after,
        "non_t1_payload_handling": "BYTE_FILTER_NO_NON_T1_DESERIALIZATION_ENUMERATION_OR_RETENTION",
        "labels_used_for_computation": False,
    }
    dependency_graph = {
        "schema_version": "q1-xai-g4-failure-dependency-graph-1.0.0",
        "G4_dependency_edges": dependency_edges,
        "G4_failed_scopes": [
            {key: row[key] for key in ("project", "algorithm", "configuration", "model_identity_sha256", "G4_outcome", "exact_failure_reason")}
            for row in results if row["G4_outcome"] != PASS
        ],
        "G3_excluded_scopes_not_queried": authorization["excluded_scopes"],
        "excluded_scope_model_query_count": 0,
    }
    summary = {
        "schema_version": "q1-xai-g4-summary-1.0.0",
        "historical_scientific_classification": [
            "MIXED_CONFIRMATORY_EVIDENCE",
            "PASS_CONFIRMATORY_EVIDENCE_INTERNALLY_CONSISTENT_REPORTABLE_MIXED",
        ],
        "historical_block7_outcome": "RECONSTRUCTION_NONDETERMINISTIC_STOP",
        "block7b_disposition": "PARTIAL_G1_G3_RECONSTRUCTION_READY_FOR_G4_REVIEW",
        "block8_outcome": outcome,
        "scope_counts": {"authorized": 389, "excluded_g3": 3, "pass": counts[PASS], "fail": counts[FAIL], "ineligible_upstream": counts[UPSTREAM], "unresolved": counts[UNRESOLVED]},
        "by_algorithm": distribution(results, "algorithm"),
        "by_configuration": distribution(results, "configuration"),
        "by_project": distribution(results, "project"),
        "unimodal": {
            "total": sum("+" not in row["configuration"] for row in results),
            "pass": sum("+" not in row["configuration"] and row["G4_outcome"] == PASS for row in results),
            "fail": sum("+" not in row["configuration"] and row["G4_outcome"] == FAIL for row in results),
        },
        "multimodal": {
            "total": sum("+" in row["configuration"] for row in results),
            "pass": sum("+" in row["configuration"] and row["G4_outcome"] == PASS for row in results),
            "fail": sum("+" in row["configuration"] and row["G4_outcome"] == FAIL for row in results),
            "ineligible_upstream": sum("+" in row["configuration"] and row["G4_outcome"] == UPSTREAM for row in results),
        },
        "maximum_observed_absolute_error": max(finite_absolute, default=None),
        "maximum_observed_relative_error_where_defined": max(finite_relative, default=None),
        "failed_scopes": dependency_graph["G4_failed_scopes"],
        "calibration_mapping_only": Counter(row["calibration_state_recorded_for_future_G5_mapping"] for row in results),
        "governance": governance,
        "xai_readiness_interpretation": "G4_PASS_ONLY_ESTABLISHES_RAW_T1_OUTPUT_EQUIVALENCE_NOT_ORIGINAL_STATE_OR_XAI_VALIDITY",
    }
    atomic_json(output / "g4_governance_ledger.json", governance)
    atomic_json(output / "g4_reference_alignment.json", alignment)
    atomic_json(output / "g4_failure_dependency_graph.json", dependency_graph)
    atomic_json(output / "g4_summary.json", summary)
    write_report(output / "BLOCK8_G4_REPORT.md", summary)
    artifact_names = sorted(path.name for path in output.iterdir() if path.is_file() and path.name != "MANIFEST.sha256")
    (output / "MANIFEST.sha256").write_text(
        "".join(f"{file_sha256(output / name)}  {name}\n" for name in artifact_names)
    )
    print(json.dumps({"outcome": outcome, "counts": dict(counts), "queries": query_count, "comparisons": compared_rows}, sort_keys=True))


def write_report(path: Path, summary: dict[str, Any]) -> None:
    counts = summary["scope_counts"]
    failures = summary["failed_scopes"]
    failure_text = "None." if not failures else "\n".join(
        f"- `{row['project']} | {row['algorithm']} | {row['configuration']}`: {row['G4_outcome']} — {row['exact_failure_reason']}"
        for row in failures
    )
    report = f"""# Block 8 G4 Row-Level Raw T1 Equivalence Report

## A-E. Authorization, frozen scope, representative state, reference, and accounting

Human G4-only authorization was applied to exactly 389 Block 7B-eligible model identities. The three frozen Zeppelin Logistic Regression fusion exclusions were not queried. `rep_01` was frozen before any T1 feature access as the sole representative for scopes whose complete dependency closure passed exact G3. Sprint 54 evidence and every parent manifest/hash were verified before and after execution.

The separate technical ledger records {summary['governance']['technical_t1_feature_access_count']} unique T1 feature rows, two feature-access events (one fail-closed before querying and one successful execution), one authorized identity-schema diagnostic access, and {summary['governance']['technical_t1_feature_row_access_operation_count']} feature-row access operations across those attempts. The successful execution used 14 project batches, {summary['governance']['technical_reconstructed_model_query_count']} persisted reconstructed-component queries, and {summary['governance']['row_probability_comparison_count']} row-probability comparisons.

## F-H. Execution distributions

Exact results by algorithm, configuration, and project are persisted in `g4_summary.json`. Every one of the 389 authorized scopes is represented exactly once in `g4_scope_results.jsonl`.

## I-J. Unimodal and multimodal raw equivalence

Unimodal: {summary['unimodal']['pass']} pass, {summary['unimodal']['fail']} fail, {summary['unimodal']['total']} total. Multimodal: {summary['multimodal']['pass']} pass, {summary['multimodal']['fail']} direct fail, {summary['multimodal']['ineligible_upstream']} upstream-ineligible, {summary['multimodal']['total']} total. Fusion inputs used the frozen modality order and only base probabilities whose own raw G4 state passed.

## K-N. Exact outcomes, errors, and dependency propagation

- Pass: {counts['pass']}
- Fail: {counts['fail']}
- Ineligible upstream: {counts['ineligible_upstream']}
- Unresolved: {counts['unresolved']}
- Maximum observed absolute error: `{summary['maximum_observed_absolute_error']}`
- Maximum observed relative error where defined: `{summary['maximum_observed_relative_error_where_defined']}`

Failed or propagated scopes:

{failure_text}

## O-S. Exclusions and governance

The excluded Zeppelin Logistic Regression `C+T`, `P+T`, and `C+P+T` scopes received zero T1 model queries. Historical Sprint 54 predictive access/scoring remain 1/1 and rerun remains false. `T2_ACCESS_COUNT = 0`; `T2_STATE = DENY_SEALED_REVIEWER_RESERVE`. T2 remains untouched and reserved for future reviewer-facing validation under a separately frozen protocol. G5 execution is 0 and XAI execution is 0.

## T. Validation

Focused tests verify the 392/389/3 universe, pre-query representative policy, exclusion enforcement, absence of fitting/reconstruction and aggregate metrics, exact row/model alignment, immutable tolerances/hashes, technical counters, T2/G5/XAI zeros, and artifact manifest integrity. Relevant Sprint 54 through Block 7B governance regressions are reported separately in the completion handoff.

## U-V. Scientific outcome and next action

`block8_outcome = {summary['block8_outcome']}`

This outcome establishes only raw row-level T1 predictive equivalence for passing reconstructed scopes. It does not make reconstructed state original, validate explanations, authorize G5/XAI, establish multimodal superiority, or support causal interpretation. The next action is human review of this G4 package. Any G5 or method-specific XAI work requires a separate prospective authorization and must be limited to scopes allowed by this result.
"""
    path.write_text(report)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("prepare", "execute"))
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    if args.phase == "prepare":
        prepare(args.repo.resolve())
    else:
        execute(args.repo.resolve())


if __name__ == "__main__":
    main()
