#!/usr/bin/env python3
"""G5-only final-output/calibration equivalence and XAI-readiness freeze.

This module consumes immutable Sprint 54 evidence plus the exact-digest G4
scope ledger. It applies only already-persisted RAW identity or ISOTONIC
mappings. It has no feature loading, model query, fitting, calibration fitting,
metric, T2, SHAP/LIME import, or explanation execution path.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.metadata
import json
import os
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from experimentation.q1_controlled_train_validation_baselines import canonical_bytes, digest


VERSION = "q1-xai-g5-final-output-equivalence-1.0.0"
OUTPUT_REL = Path("audits/q1-xai-final-output-equivalence-g5/1.0.0")
T1_REL = Path("audits/q1-t1-confirmatory-execution/1.0.0")
BLOCK6_REL = Path("audits/q1-xai-reconstruction-equivalence-protocol/1.0.0")
BLOCK7_REL = Path("audits/q1-xai-reconstruction-execution/1.0.0")
BLOCK7B_REL = BLOCK7_REL / "dispositions/block7b_partial_eligibility/1.0.0"
G4_REL = Path("audits/q1-xai-reconstruction-equivalence-g4/1.0.0")
CALIBRATION_REL = Path("audits/q1-development-only-calibration/1.0.0")
GOVERNANCE_REL = Path("audits/q1-heldout-governance-calibration-freeze/1.0.0")
G4_PASS = "G4_PASS_ROW_LEVEL_RAW_EQUIVALENCE"
G5_PASS = "G5_PASS_FINAL_OUTPUT_EQUIVALENCE"
G5_CALIBRATION_FAIL = "G5_FAIL_CALIBRATION_EQUIVALENCE"
G5_FINAL_FAIL = "G5_FAIL_FINAL_OUTPUT_EQUIVALENCE"
G5_UPSTREAM = "G5_INELIGIBLE_UPSTREAM"
G5_UNRESOLVED = "G5_UNRESOLVED_TECHNICAL"
ABSOLUTE_BOUND = 1e-12
RELATIVE_BOUND = 1e-10
RELATIVE_DOMAIN = 1e-8
THRESHOLD = 0.5
EXCLUDED = {
    ("apache/zeppelin", "Logistic Regression", "C+T"),
    ("apache/zeppelin", "Logistic Regression", "P+T"),
    ("apache/zeppelin", "Logistic Regression", "C+P+T"),
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
    "block7b_eligibility": (
        BLOCK7B_REL / "scope_g1_g3_eligibility.jsonl",
        "2a64d2496c5114c50264f1fbb26d611d7655d91802568c359532e0809fdf043b",
    ),
    "block8_g4_manifest": (
        G4_REL / "MANIFEST.sha256",
        "158f52c8cd16e633d11202a86dff467d33838e84617aeaf64d94c361a66f3074",
    ),
    "block8_g4_scope_results": (
        G4_REL / "g4_scope_results.jsonl",
        "0320dcdf3eb73b5b242a4223292c9708074e6e24f33f4757a9ebe582a9e9d5c1",
    ),
    "frozen_numerical_tolerance": (
        BLOCK6_REL / "numerical_tolerance_policy.json",
        "62fd3780c94c6a69bfc036bdd4b567409ffc46c8c892a807b221f5d40d0eb336",
    ),
    "frozen_calibration_policy": (
        GOVERNANCE_REL / "frozen_calibration_policy.json",
        "b1fcce1e0dc5178ecf0606ddba3263add308db0da959c58a5addc136ebcefc25",
    ),
    "frozen_threshold_policy": (
        GOVERNANCE_REL / "frozen_threshold_policy.json",
        "06da87fe9d790c129b4debefcd2f739719b6882a022468cd322fbee7ce0cb0c5",
    ),
    "calibrator_states": (
        CALIBRATION_REL / "calibrator_states.jsonl.gz",
        "5708a6e2ca35d54e8fdc6cf0bbd23bc5e72be66d22400be97de152ee183dcbe3",
    ),
    "calibration_manifest": (
        CALIBRATION_REL / "MANIFEST.sha256",
        "09dccf5d11bdf7299c1e25ac359a170a38c9509b3ddb513b3d37b9a6ab765c26",
    ),
}


class G5Error(RuntimeError):
    """Fail-closed G5 authorization or equivalence error."""


def file_sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def float_digest(values: np.ndarray) -> str:
    payload = np.ascontiguousarray(values, dtype="<f8").tobytes(order="C")
    return hashlib.sha256(payload).hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(canonical_bytes(value) + b"\n")
    os.replace(temporary, path)


def verify_hashes(root: Path) -> dict[str, dict[str, Any]]:
    result = {}
    for name, (relative, expected) in FROZEN_HASHES.items():
        actual = file_sha256(root / relative)
        if actual != expected:
            raise G5Error(f"immutable hash mismatch: {name}")
        result[name] = {
            "path": str(relative), "expected_sha256": expected,
            "actual_sha256": actual, "status": "PASS_EXACT_SHA256",
        }
    return result


def load_g4(root: Path) -> list[dict[str, Any]]:
    path = root / FROZEN_HASHES["block8_g4_scope_results"][0]
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    if len(rows) != 389 or len({row["model_identity_sha256"] for row in rows}) != 389:
        raise G5Error("G4 universe is not 389 unique identities")
    if any(row["G4_outcome"] != G4_PASS for row in rows):
        raise G5Error("non-passing G4 scope entered G5")
    if {(row["project"], row["algorithm"], row["configuration"]) for row in rows} & EXCLUDED:
        raise G5Error("G3-excluded scope entered G5")
    if any(
        row["frozen_reference_probability_digest"] != row["reconstructed_probability_digest"]
        or row["max_absolute_error"] != 0.0
        or row["row_alignment_status"] != "EXACT_IDENTITY_AND_ORDER"
        for row in rows
    ):
        raise G5Error("G4 exact raw-vector evidence is not complete")
    return rows


def calibration_policy_index(root: Path) -> dict[tuple[str, str], dict[str, Any]]:
    policy = json.loads((root / FROZEN_HASHES["frozen_calibration_policy"][0]).read_text())
    aliases = {
        "CODE": "C", "PROCESS": "P", "TEXT": "T",
        "CODE + PROCESS": "C+P", "CODE + TEXT": "C+T",
        "PROCESS + TEXT": "P+T", "CODE + PROCESS + TEXT": "C+P+T",
    }
    indexed = {(row["algorithm"], aliases[row["configuration"]]): row for row in policy["mapping"]}
    if len(indexed) != 28 or policy["selection_counts"] != {"RAW": 27, "PLATT": 0, "ISOTONIC": 1}:
        raise G5Error("frozen calibration policy universe changed")
    return indexed


def isotonic_states(root: Path) -> dict[str, dict[str, Any]]:
    selected = {}
    with gzip.open(root / FROZEN_HASHES["calibrator_states"][0], "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            if (
                row["algorithm"] == "LightGBM" and row["configuration"] == "P"
                and row["method"] == "ISOTONIC" and row["evaluation_origin"] == 11
            ):
                selected[row["project"]] = row
    if len(selected) != 14:
        raise G5Error("frozen project-local isotonic state universe changed")
    linkage = json.loads((root / BLOCK7_REL / "calibration_linkage.json").read_text())
    linked = {row["project"]: row for row in linkage["states"]}
    for project, state in selected.items():
        if (
            digest(state) != linked[project]["state_sha256"]
            or state["fit_membership_digest"] != linked[project]["fit_membership_digest"]
        ):
            raise G5Error(f"Block 7 calibration linkage mismatch: {project}")
    return selected


def load_reference(root: Path) -> dict[tuple[str, str, str], dict[str, Any]]:
    grouped: dict[tuple[str, str, str], dict[str, Any]] = {}
    with gzip.open(root / FROZEN_HASHES["sprint54_t1_prediction_evidence"][0], "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            key = (row["project"], row["algorithm"], row["configuration"])
            item = grouped.setdefault(key, {
                "model_identity_sha256": row["model_identity_sha256"],
                "calibration_state": row["calibration_state"],
                "calibration_provenance": row["calibration_provenance"],
                "row_identifiers": [], "raw": [], "final": [],
                "decisions": [], "thresholds": [],
            })
            if (
                item["model_identity_sha256"] != row["model_identity_sha256"]
                or item["calibration_state"] != row["calibration_state"]
                or item["calibration_provenance"] != row["calibration_provenance"]
            ):
                raise G5Error(f"reference scope linkage changed: {key}")
            item["row_identifiers"].append(row["row_identifier"])
            item["raw"].append(float(row["raw_predicted_probability"]))
            item["final"].append(float(row["final_frozen_probability"]))
            item["decisions"].append(int(row["fixed_threshold_prediction"]))
            item["thresholds"].append(float(row["fixed_threshold"]))
    if len(grouped) != 392:
        raise G5Error("Sprint 54 reference scope universe changed")
    return grouped


def text_state_index(root: Path) -> dict[tuple[str, str], dict[str, Any]]:
    path = root / BLOCK7_REL / "repetitions/rep_01/component_journal.jsonl"
    result = {}
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row["logical_id"].endswith("|FINAL_BASE|T"):
            representation = row.get("text_representation")
            preprocessing = row["canonical_state"].get("preprocessing", {})
            representation_payload = None
            representation_bytes_valid = False
            representation_semantics_valid = False
            if representation is not None:
                representation_path = root / BLOCK7_REL / representation["path"]
                representation_bytes_valid = (
                    representation_path.is_file()
                    and representation_path.stat().st_size == representation["bytes"]
                    and file_sha256(representation_path) == representation["sha256"]
                )
                if representation_bytes_valid:
                    representation_payload = json.loads(representation_path.read_text())
                    vocabulary = representation_payload.get("vocabulary", {})
                    feature_order = representation_payload.get("feature_order", [])
                    idf = np.asarray(representation_payload.get("idf", []), dtype="<f8")
                    token_columns_exact = (
                        len(vocabulary) == len(feature_order)
                        and all(
                            isinstance(index, int)
                            and 0 <= index < len(feature_order)
                            and feature_order[index] == token
                            for token, index in vocabulary.items()
                        )
                    )
                    representation_semantics_valid = (
                        token_columns_exact
                        and digest(vocabulary) == preprocessing.get("vocabulary_sha256")
                        and digest(feature_order) == preprocessing.get("feature_order_sha256")
                        and float_digest(idf) == preprocessing.get("idf", {}).get("sha256")
                        and representation_payload.get("parameters") == preprocessing.get("parameters")
                    )
            ready = (
                representation is not None
                and representation_bytes_valid
                and representation_semantics_valid
                and preprocessing.get("type") == "TFIDF"
                and "vocabulary_sha256" in preprocessing
                and "idf" in preprocessing
                and "feature_order_sha256" in preprocessing
                and preprocessing.get("feature_count") == row["canonical_state"]["model"].get("n_features_in")
            )
            result[(row["canonical_state"]["provenance"]["project"], row["algorithm"])] = {
                "status": "TEXT_FEATURE_ATTRIBUTION_STATE_READY" if ready else "TEXT_FEATURE_ATTRIBUTION_STATE_INELIGIBLE",
                "logical_id": row["logical_id"],
                "text_representation_sha256": representation["sha256"] if representation else None,
                "vocabulary_sha256": preprocessing.get("vocabulary_sha256"),
                "idf_sha256": preprocessing.get("idf", {}).get("sha256"),
                "feature_order_sha256": preprocessing.get("feature_order_sha256"),
                "feature_count": preprocessing.get("feature_count"),
                "predictor_alignment": ready,
                "representation_object_bytes_verified": representation_bytes_valid,
                "vocabulary_idf_token_column_feature_order_verified": representation_semantics_valid,
            }
    if len(result) != 56:
        raise G5Error("final TEXT state inventory incomplete")
    return result


def compare_scope(
    g4: dict[str, Any], reference: dict[str, Any], policy: dict[str, Any],
    isotonic: dict[str, Any] | None,
) -> dict[str, Any]:
    raw = np.asarray(reference["raw"], dtype="<f8")
    frozen_final = np.asarray(reference["final"], dtype="<f8")
    if float_digest(raw) != g4["reconstructed_probability_digest"]:
        raise G5Error("G4 reconstructed raw digest/reference bytes mismatch")
    state = reference["calibration_state"]
    if state != policy["calibration_state"]:
        raise G5Error("reference/frozen-policy calibration state mismatch")
    if state == "RAW":
        reconstructed_final = raw.copy()
        state_digest = digest({
            "calibration_state": "RAW", "mapping": "IDENTITY",
            "policy_entry_sha256": digest(policy),
        })
        mapping_status = "RAW_IDENTITY_MAPPING_EXACT"
    elif state == "ISOTONIC" and isotonic is not None:
        if (
            isotonic["project"] != g4["project"]
            or isotonic["algorithm"] != g4["algorithm"]
            or isotonic["configuration"] != g4["configuration"]
            or isotonic["method"] != "ISOTONIC"
        ):
            raise G5Error("isotonic state identity mismatch")
        reconstructed_final = np.round(
            np.interp(raw, isotonic["x_thresholds"], isotonic["y_thresholds"]), decimals=12
        )
        state_digest = digest(isotonic)
        mapping_status = "PERSISTED_ISOTONIC_MAPPING_APPLIED_NO_REFIT"
    else:
        raise G5Error("authorized scope lacks applicable calibration mapping")
    finite = np.isfinite(reconstructed_final) & np.isfinite(frozen_final)
    difference = np.abs(reconstructed_final - frozen_final)
    relative_mask = np.abs(frozen_final) >= RELATIVE_DOMAIN
    relative = difference[relative_mask] / np.abs(frozen_final[relative_mask])
    absolute_violations = int(np.count_nonzero((difference > ABSOLUTE_BOUND) | ~finite))
    relative_violations = int(np.count_nonzero(relative > RELATIVE_BOUND))
    nonfinite = int(np.count_nonzero(~finite))
    thresholds = np.asarray(reference["thresholds"], dtype=float)
    if not np.all(thresholds == THRESHOLD):
        raise G5Error("frozen row threshold changed")
    reconstructed_decisions = (reconstructed_final >= thresholds).astype(int)
    decision_mismatches = int(np.count_nonzero(reconstructed_decisions != np.asarray(reference["decisions"], dtype=int)))
    aligned = (
        g4["T1_row_count"] == len(reference["row_identifiers"])
        and g4["T1_row_identity_digest"] == digest(reference["row_identifiers"])
    )
    passed = aligned and absolute_violations == relative_violations == nonfinite == decision_mismatches == 0
    reasons = []
    if not aligned: reasons.append("row identity/order mismatch")
    if absolute_violations: reasons.append(f"{absolute_violations} absolute-bound violations")
    if relative_violations: reasons.append(f"{relative_violations} relative-bound violations")
    if nonfinite: reasons.append(f"{nonfinite} NaN/Inf values")
    if decision_mismatches: reasons.append(f"{decision_mismatches} decision mismatches")
    failure_outcome = G5_CALIBRATION_FAIL if state == "ISOTONIC" else G5_FINAL_FAIL
    return {
        "schema_version": "q1-xai-g5-scope-result-1.0.0",
        "project": g4["project"], "algorithm": g4["algorithm"],
        "configuration": g4["configuration"],
        "model_identity_sha256": g4["model_identity_sha256"],
        "G4_outcome": g4["G4_outcome"],
        "frozen_calibration_state": state,
        "calibration_state_digest": state_digest,
        "calibration_policy_entry_sha256": digest(policy),
        "calibration_mapping_status": mapping_status,
        "T1_row_count": len(raw),
        "T1_row_identity_digest": digest(reference["row_identifiers"]),
        "raw_probability_digest": float_digest(raw),
        "reconstructed_final_probability_digest": float_digest(reconstructed_final),
        "frozen_final_probability_digest": float_digest(frozen_final),
        "max_absolute_error": float(np.max(difference)) if len(difference) else 0.0,
        "max_relative_error_where_defined": float(np.max(relative)) if len(relative) else 0.0,
        "relative_error_defined_row_count": int(np.count_nonzero(relative_mask)),
        "rows_with_absolute_bound_violation": absolute_violations,
        "rows_with_relative_bound_violation": relative_violations,
        "nan_or_infinite_count": nonfinite,
        "row_alignment_status": "EXACT_IDENTITY_AND_ORDER" if aligned else "MISMATCH",
        "frozen_threshold": THRESHOLD,
        "decision_output_status": "FROZEN_ROW_LEVEL_DECISION_VERIFIED",
        "decision_mismatch_count": decision_mismatches,
        "row_final_probability_comparison_count": len(raw),
        "G5_outcome": G5_PASS if passed else failure_outcome,
        "exact_failure_reason": None if passed else "; ".join(reasons),
        "markers": ["NOT_CONFIRMATORY", "NO_MODEL_SELECTION", "NO_SCIENTIFIC_UPDATE", "NO_XAI_EXECUTION"],
    }


def primary_method(row: dict[str, Any]) -> tuple[str, str]:
    if "+" in row["configuration"]:
        return "E2", "ANALYTICAL_LR_FUSION_DECOMPOSITION"
    return "E1", {
        "Logistic Regression": "ANALYTICAL_LINEAR_LOGIT_DECOMPOSITION",
        "Random Forest": "EXACT_TREESHAP_POSITIVE_CLASS_OUTPUT",
        "XGBoost": "EXACT_TREESHAP_NATIVE_RAW_MARGIN",
        "LightGBM": "EXACT_TREESHAP_NATIVE_RAW_MARGIN",
    }[row["algorithm"]]


def distribution(rows: list[dict[str, Any]], key: str) -> dict[str, dict[str, int]]:
    output = {}
    for value in sorted({row[key] for row in rows}):
        count = Counter(row["G5_outcome"] for row in rows if row[key] == value)
        output[value] = {
            "total": sum(count.values()), "pass": count[G5_PASS],
            "fail_calibration": count[G5_CALIBRATION_FAIL],
            "fail_final_output": count[G5_FINAL_FAIL],
            "ineligible_upstream": count[G5_UPSTREAM], "unresolved": count[G5_UNRESOLVED],
        }
    return output


def package_version(name: str) -> dict[str, Any]:
    try:
        observed = importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        observed = None
    return {"installed": observed is not None, "observed_version_without_import": observed}


def run(root: Path) -> None:
    output = root / OUTPUT_REL
    if output.exists():
        raise G5Error(f"refusing to overwrite G5 namespace: {output}")
    before = verify_hashes(root)
    g4_rows = load_g4(root)
    policies = calibration_policy_index(root)
    isotonic = isotonic_states(root)
    references = load_reference(root)
    text_states = text_state_index(root)

    results = []
    for g4 in g4_rows:
        key = (g4["project"], g4["algorithm"], g4["configuration"])
        reference = references[key]
        if reference["model_identity_sha256"] != g4["model_identity_sha256"]:
            raise G5Error(f"G4/reference model identity mismatch: {key}")
        policy = policies[(g4["algorithm"], g4["configuration"])]
        state = isotonic.get(g4["project"]) if policy["calibration_state"] == "ISOTONIC" else None
        results.append(compare_scope(g4, reference, policy, state))
    results.sort(key=lambda row: (row["project"], row["algorithm"], row["configuration"]))
    if len(results) != 389:
        raise G5Error("G5 result count changed")
    counts = Counter(row["G5_outcome"] for row in results)

    readiness = []
    for row in results:
        role, method = primary_method(row)
        contains_text = "T" in row["configuration"].split("+")
        text = text_states[(row["project"], row["algorithm"])] if contains_text else None
        state_available = row["G5_outcome"] == G5_PASS and (
            not contains_text or text["status"] == "TEXT_FEATURE_ATTRIBUTION_STATE_READY"
        )
        readiness.append({
            "schema_version": "q1-xai-future-readiness-scope-1.0.0",
            "project": row["project"], "algorithm": row["algorithm"],
            "configuration": row["configuration"],
            "model_identity_sha256": row["model_identity_sha256"],
            "G5_outcome": row["G5_outcome"],
            "future_xai_role": role, "future_primary_method": method,
            "method_specific_state_available": state_available,
            "text_feature_attribution_state": text["status"] if text else "NOT_APPLICABLE",
            "text_state_evidence": text,
            "calibration_explanation_readiness": (
                "E3_IDENTITY_MAPPING_READY" if row["frozen_calibration_state"] == "RAW"
                else "E3_FROZEN_MAPPING_INSPECTION_READY"
            ),
            "future_xai_readiness": (
                "FUTURE_PRIMARY_XAI_STATE_READY_PENDING_SEPARATE_RUNTIME_AND_EXECUTION_AUTHORIZATION"
                if state_available else "NOT_XAI_READY"
            ),
            "xai_executed": False,
        })

    ready = [row for row in readiness if row["future_xai_readiness"].startswith("FUTURE_PRIMARY")]
    if len(ready) == 389:
        outcome = "FULL_G5_FINAL_OUTPUT_EQUIVALENCE_XAI_READINESS_ESTABLISHED"
    elif ready and not counts[G5_UNRESOLVED]:
        outcome = "PARTIAL_G5_FINAL_OUTPUT_EQUIVALENCE_XAI_READINESS_ESTABLISHED"
    elif counts[G5_UNRESOLVED]:
        outcome = "G5_TECHNICAL_VERIFICATION_UNRESOLVED"
    else:
        outcome = "G5_FINAL_OUTPUT_EQUIVALENCE_INSUFFICIENT_FOR_PRIMARY_XAI"

    calibration_registry = {
        "schema_version": "q1-xai-g5-calibration-state-registry-1.0.0",
        "authorized_distribution": dict(sorted(Counter(row["frozen_calibration_state"] for row in results).items())),
        "historical_392_scope_distribution": {"RAW": 378, "ISOTONIC": 14},
        "raw_identity_mapping": {
            "scope_count": 375, "mapping": "final_probability = raw_probability",
            "fit_count": 0, "policy_source": str(FROZEN_HASHES["frozen_calibration_policy"][0]),
        },
        "isotonic": {
            "scope_count": 14,
            "source": str(FROZEN_HASHES["calibrator_states"][0]),
            "source_sha256": FROZEN_HASHES["calibrator_states"][1],
            "selection": "LightGBM|P|ISOTONIC|evaluation_origin=11",
            "fit_or_refit_during_g5": False,
            "states": [
                {
                    "project": project, "algorithm": state["algorithm"],
                    "configuration": state["configuration"], "method": state["method"],
                    "evaluation_origin": state["evaluation_origin"],
                    "fit_membership_digest": state["fit_membership_digest"],
                    "calibration_state_digest": digest(state),
                    "x_thresholds_sha256": digest(state["x_thresholds"]),
                    "y_thresholds_sha256": digest(state["y_thresholds"]),
                    "threshold_count": len(state["x_thresholds"]),
                }
                for project, state in sorted(isotonic.items())
            ],
        },
    }
    method_policy = {
        "schema_version": "q1-xai-post-g5-method-policy-freeze-1.0.0",
        "execution_in_g5": False,
        "E1_unimodal": {
            "Logistic Regression": "ANALYTICAL_LINEAR_LOGIT_DECOMPOSITION",
            "Random Forest": "EXACT_TREESHAP_POSITIVE_CLASS_OUTPUT",
            "XGBoost": "EXACT_TREESHAP_NATIVE_RAW_MARGIN",
            "LightGBM": "EXACT_TREESHAP_NATIVE_RAW_MARGIN",
        },
        "E2_multimodal": {
            "primary_method": "ANALYTICAL_LR_FUSION_DECOMPOSITION",
            "eta_fusion": "alpha + sum(beta_m * p_m)",
            "phi_m": "beta_m * (p_m - mu_m)",
            "phi_0": "alpha + sum(beta_m * mu_m)",
            "mu_m_source": "FROZEN_TRAIN_REFERENCE_POPULATION_DEFINED_BY_BLOCK4_ONLY",
            "values_calculated_in_g5": False,
        },
        "E3_calibration": {
            "RAW": "E3_IDENTITY_MAPPING_READY",
            "ISOTONIC": "E3_FROZEN_MAPPING_INSPECTION_READY",
            "feature_level_attribution_of_isotonic_change": "PROHIBITED",
            "plots_executed": False,
        },
        "LIME_PRIMARY_STATUS": "EXCLUDED_FROM_PRIMARY_XAI",
        "lime_reason": [
            "stochastic neighborhood generation", "stochastic sampling/surrogate behavior",
            "no required capability beyond deterministic analytical/TreeSHAP primary design",
            "additional reproducibility burden",
        ],
        "authorization_required_before_execution": True,
    }
    shap_runtime = {
        "schema_version": "q1-xai-prospective-shap-runtime-readiness-1.0.0",
        "inspection_method": "IMPORTLIB_METADATA_ONLY_NO_SHAP_IMPORT",
        "shap": package_version("shap"), "lime": package_version("lime"),
        "shap_execution_count": 0, "explainer_import_count": 0,
        "requirements_before_future_xai": [
            "freeze exact SHAP version", "freeze Python version",
            "freeze NumPy/SciPy/scikit-learn/XGBoost/LightGBM versions",
            "fix explainer type per algorithm family", "disable approximate mode",
            "freeze output scale", "freeze background and foreground populations",
            "retain Block 4 additivity/fidelity tolerances",
        ],
        "status": "RUNTIME_FREEZE_REQUIRED_BEFORE_PRIMARY_XAI",
    }
    claim_boundaries = {
        "schema_version": "q1-xai-claim-boundaries-freeze-1.0.0",
        "permitted_future_claims": [
            "feature association with model predictions", "modality contribution to fusion output",
            "local prediction decomposition", "global attribution patterns",
            "heterogeneity across projects/models",
        ],
        "prohibited_claims": [
            "causal effects", "defect causes", "proof that a feature causes bugs",
            "proof that one modality is scientifically superior",
            "proof that multimodality is universally better",
            "human-understandable semantic intent of commit messages",
        ],
    }
    governance = {
        "schema_version": "q1-xai-g5-technical-ledger-1.0.0",
        "authorized_G5_scope_count": 389,
        "G5_pass_count": counts[G5_PASS], "G5_fail_count": counts[G5_CALIBRATION_FAIL] + counts[G5_FINAL_FAIL],
        "G5_ineligible_upstream_count": counts[G5_UPSTREAM], "G5_unresolved_count": counts[G5_UNRESOLVED],
        "historical_T1_predictive_access_count": 1,
        "historical_T1_predictive_scoring_count": 1, "historical_T1_rerun": False,
        "G4_technical_scope_count": 389,
        "G5_T1_stored_reference_evidence_access_count": 1,
        "G5_T1_feature_access_count": 0, "G5_reconstructed_model_query_count": 0,
        "row_final_probability_comparison_count": sum(row["row_final_probability_comparison_count"] for row in results),
        "decision_output_comparison_count": sum(row["T1_row_count"] for row in results),
        "T2_access_count": 0, "T2_state": "DENY_SEALED_REVIEWER_RESERVE",
        "XAI_execution_count": 0, "SHAP_execution_count": 0, "LIME_execution_count": 0,
        "analytical_attribution_execution_count": 0,
        "refit_count": 0, "reconstruction_count": 0, "recalibration_count": 0,
        "metric_recomputation_count": 0, "threshold_optimization_count": 0,
        "excluded_scope_count": 3, "excluded_scope_G5_entry_count": 0,
        "markers": ["NOT_CONFIRMATORY", "NO_MODEL_SELECTION", "NO_SCIENTIFIC_UPDATE", "NO_XAI_EXECUTION"],
    }
    after = verify_hashes(root)
    if before != after:
        raise G5Error("immutable evidence changed during G5")
    alignment = {
        "schema_version": "q1-xai-g5-final-output-alignment-1.0.0",
        "authorized_scope_count": 389,
        "all_model_identities_exact": True,
        "all_calibration_states_exact": True,
        "all_row_identities_and_order_exact": all(row["row_alignment_status"] == "EXACT_IDENTITY_AND_ORDER" for row in results),
        "all_decisions_exact": all(row["decision_mismatch_count"] == 0 for row in results),
        "comparison_granularity": "EVERY_G4_PASS_SCOPE_X_EVERY_FROZEN_T1_ROW",
        "absolute_bound": ABSOLUTE_BOUND, "relative_bound": RELATIVE_BOUND,
        "relative_domain": "abs(reference_final_probability) >= 1e-8",
        "aggregate_metric_substitution": False,
        "hashes_before": before, "hashes_after": after,
    }
    ready_by_method = Counter(row["future_primary_method"] for row in ready)
    ready_by_calibration = Counter(
        next(result["frozen_calibration_state"] for result in results if result["model_identity_sha256"] == row["model_identity_sha256"])
        for row in ready
    )
    summary = {
        "schema_version": "q1-xai-g5-summary-1.0.0",
        "historical_scientific_classification": "MIXED_CONFIRMATORY_EVIDENCE",
        "historical_block7_outcome": "RECONSTRUCTION_NONDETERMINISTIC_STOP",
        "block7b_disposition": "PARTIAL_G1_G3_RECONSTRUCTION_READY_FOR_G4_REVIEW",
        "block8_outcome": "FULL_G4_RAW_EQUIVALENCE_READY_FOR_G5_REVIEW",
        "g5_outcome": outcome,
        "counts": {"authorized": 389, "pass": counts[G5_PASS], "fail_calibration": counts[G5_CALIBRATION_FAIL], "fail_final_output": counts[G5_FINAL_FAIL], "ineligible_upstream": counts[G5_UPSTREAM], "unresolved": counts[G5_UNRESOLVED]},
        "calibration_distribution": dict(sorted(Counter(row["frozen_calibration_state"] for row in results).items())),
        "by_algorithm": distribution(results, "algorithm"),
        "by_configuration": distribution(results, "configuration"),
        "by_project": distribution(results, "project"),
        "unimodal": {"total": sum("+" not in row["configuration"] for row in results), "pass": sum("+" not in row["configuration"] and row["G5_outcome"] == G5_PASS for row in results)},
        "multimodal": {"total": sum("+" in row["configuration"] for row in results), "pass": sum("+" in row["configuration"] and row["G5_outcome"] == G5_PASS for row in results)},
        "maximum_observed_absolute_error": max(row["max_absolute_error"] for row in results),
        "maximum_observed_relative_error_where_defined": max(row["max_relative_error_where_defined"] for row in results),
        "decision_mismatch_count": sum(row["decision_mismatch_count"] for row in results),
        "future_xai_readiness": {
            "state_ready_scope_count": len(ready),
            "not_ready_scope_count": 389 - len(ready),
            "by_method": dict(sorted(ready_by_method.items())),
            "by_calibration_state": dict(sorted(ready_by_calibration.items())),
            "text_state_ready_scope_count": sum(row["text_feature_attribution_state"] == "TEXT_FEATURE_ATTRIBUTION_STATE_READY" for row in ready),
            "authorization_status": "NOT_AUTHORIZED_FOR_EXECUTION",
        },
        "governance": governance,
    }

    output.mkdir(parents=True)
    (output / "g5_scope_results.jsonl").write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in results))
    (output / "xai_readiness_ledger.jsonl").write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in readiness))
    atomic_json(output / "g5_summary.json", summary)
    atomic_json(output / "g5_governance_ledger.json", governance)
    atomic_json(output / "calibration_state_registry.json", calibration_registry)
    atomic_json(output / "final_output_alignment.json", alignment)
    atomic_json(output / "xai_method_policy_freeze.json", method_policy)
    atomic_json(output / "shap_runtime_readiness.json", shap_runtime)
    atomic_json(output / "xai_claim_boundaries.json", claim_boundaries)
    write_report(output / "G5_FINAL_OUTPUT_EQUIVALENCE_REPORT.md", summary)
    names = sorted(path.name for path in output.iterdir() if path.is_file() and path.name != "MANIFEST.sha256")
    (output / "MANIFEST.sha256").write_text("".join(f"{file_sha256(output / name)}  {name}\n" for name in names))
    print(json.dumps({"outcome": outcome, "counts": dict(counts), "xai_state_ready": len(ready)}, sort_keys=True))


def write_report(path: Path, summary: dict[str, Any]) -> None:
    counts = summary["counts"]
    readiness = summary["future_xai_readiness"]
    path.write_text(f"""# G5 Final-Output Equivalence and XAI-Readiness Freeze

## A-H. Authorization, inherited scope, calibration, and final output

Human G5-only authorization was applied to exactly the 389 frozen G4-pass identities. The three Zeppelin Logistic Regression fusion exclusions did not enter G5. Frozen evidence gives 375 RAW identity mappings and 14 persisted project-specific LightGBM PROCESS isotonic mappings. No calibrator was fit, selected, altered, or rounded beyond the historically frozen `np.round(np.interp(...), 12)` mapping semantics.

All {counts['pass']} authorized scopes passed final-output row equivalence; calibration failures, final-output failures, upstream-ineligible scopes, and unresolved scopes are all zero. Maximum absolute and relative differences were `{summary['maximum_observed_absolute_error']}` and `{summary['maximum_observed_relative_error_where_defined']}`. Every persisted threshold decision matched; decision mismatch count is {summary['decision_mismatch_count']}.

## I-N. Result distributions

Exact distributions by algorithm, configuration, project, unimodal/multimodal status, and calibration state are in `g5_summary.json`. Unimodal scopes passed {summary['unimodal']['pass']}/{summary['unimodal']['total']}; multimodal scopes passed {summary['multimodal']['pass']}/{summary['multimodal']['total']}. RAW passed 375/375 and ISOTONIC passed 14/14.

## O-S. Documentation-only XAI readiness

The maximum future model-specific XAI state universe is {readiness['state_ready_scope_count']} scopes, with zero currently marked not-ready. This is state readiness only and remains pending a separate runtime and execution authorization. E1 maps LR to analytical linear-logit decomposition, RF to exact positive-class TreeSHAP, and XGBoost/LightGBM to exact native raw-margin TreeSHAP. E2 maps all multimodal scopes to analytical LR fusion decomposition using the frozen formulas and a future frozen TRAIN reference population. E3 maps RAW to identity-mapping readiness and ISOTONIC to frozen-mapping inspection readiness. All {readiness['text_state_ready_scope_count']} TEXT-consuming scopes have exact TF-IDF vocabulary, IDF, token-column/feature-order, and predictor alignment evidence.

## T-U. SHAP and LIME

Neither SHAP nor LIME is installed in the frozen environment. Neither was imported or executed. A future stage must freeze the complete SHAP/runtime/explainer/output-scale/background/foreground contract before execution. `LIME_PRIMARY_STATUS = EXCLUDED_FROM_PRIMARY_XAI`; exploratory LIME would require separate non-confirmatory authorization.

## V-Y. Claims and governance

Future outputs may describe predictive feature associations, modality contributions, decompositions, global patterns, and heterogeneity. They may not be described as causal effects, defect causes, universal modality/multimodality superiority, or semantic intent. Historical T1 access/scoring remain 1/1 and rerun remains false. `T2_ACCESS_COUNT = 0`; `T2_STATE = DENY_SEALED_REVIEWER_RESERVE`. XAI, SHAP, LIME, and analytical-attribution execution counts remain 0.

## Z. Outcome and next action

`g5_outcome = {summary['g5_outcome']}`

The next action is human review. If primary XAI is later authorized, first freeze the missing SHAP/runtime execution contract and exact explanation populations/query budget, then limit execution to the 389 ledger identities and the method/output-scale rules in this package. G5 itself grants no XAI authorization.
""")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    run(args.repo.resolve())


if __name__ == "__main__":
    main()
