"""Deterministic one-shot T1 confirmatory execution engine.

Preparation is metadata-only and never materializes T1/T2 predictive payloads.  The
one-shot entry point reconstructs frozen TRAIN-only models before crossing the T1
boundary, writes an irreversible start marker, then materializes only authorized T1
rows.  T2 and XAI have no execution path in this module.
"""

from __future__ import annotations

import argparse
import copy
import csv
import gzip
import hashlib
import json
import math
import os
from collections import Counter, defaultdict
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import friedmanchisquare, rankdata, spearmanr, wilcoxon
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    matthews_corrcoef,
    precision_score,
    recall_score,
    roc_auc_score,
)

from experimentation.q1_controlled_late_fusion import (
    CONFIGURATIONS,
    FUSION_CONFIGURATIONS,
)
from experimentation.q1_controlled_result_campaign import _build_selected_oof, _meta
from experimentation.q1_controlled_train_validation_baselines import (
    CODE_FEATURES,
    EXPECTED_PROJECTS,
    LABEL,
    PROCESS_FEATURES,
    ROW_ID_PATTERN,
    canonical_bytes,
    digest,
    load_development_project,
)
from experimentation.q1_controlled_unimodal_modeling import (
    ALGORITHMS,
    MODALITIES,
    fit_unimodal,
    raw_features,
)

VERSION = "q1-t1-confirmatory-execution-engine-1.0.0"
AUTH_REL = Path("audits/q1-t1-confirmatory-execution/1.0.0")
ENGINE_REL = AUTH_REL / "engine"
AMENDMENT_REL = AUTH_REL / "amendments" / "manifest-entry-count-1.0.0"
FREEZE_REL = Path("audits/q1-apachejit-final-dataset-freeze/1.0.0")
CAMPAIGN_REL = Path("audits/q1-controlled-train-validation-baselines/1.0.0/campaign")
CALIBRATION_REL = Path("audits/q1-development-only-calibration/1.0.0")
SPRINT53_REL = Path("audits/q1-t1-confirmatory-protocol/1.0.0")
GOVERNANCE_REL = Path("audits/q1-heldout-governance-calibration-freeze/1.0.0")
UNIMODAL_CONTRACT_REL = Path(
    "audits/q1-controlled-train-validation-baselines/1.0.0/"
    "unimodal_contract/unimodal_contract.json"
)
FUSION_CONTRACT_REL = Path(
    "audits/q1-controlled-train-validation-baselines/1.0.0/"
    "late_fusion_contract/late_fusion_contract.json"
)
AUTHORIZATION_FILE = "execution_authorization.json"
AMENDMENT_FILE = "authorization_metadata_amendment.json"
AUTHORIZATION_MODE = "ONE_SHOT_CONFIRMATORY_EVALUATION"
EXPECTED_AUTHORIZATION_SHA256 = (
    "1994e7f1bb4b718dc27c67623323c15fed951ddaa58939902da981105d6077c2"
)
EXPECTED_SPRINT53_MANIFEST_SHA256 = (
    "0bc00b31835381defccb90ac1efd01e4f21a74968bda537385c3f1a1d1c8e20e"
)
EXPECTED_AMENDMENT_SHA256 = (
    "122cf497b1a7e713cbc52b56fcb23329bdf9410f7d3121506e029483ed45b001"
)
EXPECTED_AMENDMENT_MANIFEST_SHA256 = (
    "54fe66a085a6f4bd7ab65f60437a7ca6f0e1321c5f3a752780944217a5a13798"
)
EXPECTED_HISTORICAL_FAILURE_SHA256 = (
    "62ece47b2305c7eca9cd5c98c81e93b79ad000fda4f1f85b7e6a1d73012ab940"
)
EXPECTED_T1_ROWS = 3787
EXPECTED_T1_HASH = "50186112bc3860c7c97d00233b389386a84acf0505d4f05bdb2075128b350f93"
EXPECTED_T2_ROWS = 15161
EXPECTED_T2_HASH = "e6ba492aae300a61aefad01d1697bef3e10303bffc924ba437bd8437f6dbb4f7"
EXPECTED_EVIDENCE_ROWS = EXPECTED_T1_ROWS * len(ALGORITHMS) * len(CONFIGURATIONS)
THRESHOLD = 0.5
NEAR_PERFECT_TRIGGER = 0.99
METRICS = ("PR_AUC", "MCC", "ROC_AUC", "Recall", "Precision", "F1", "Brier", "ECE")
MODALITY_NAMES = {"C": "CODE", "P": "PROCESS", "T": "TEXT"}
MODALITY_CODES = {value: key for key, value in MODALITY_NAMES.items()}
IDENTITY_KEYS = {
    LABEL,
    "canonical_project_identifier",
    "canonical_repository_identifier",
    "commit_sha",
    "direct_parent_sha",
    "family_group_identifier",
    "normalized_utc_timestamp",
    "raw_commit_timestamp",
    "raw_commit_timezone",
    "row_identifier",
    "source_apachejit_row_identity",
    "source_artifact_version_reference",
}
PARTITION_KEYS = {
    "forward_block",
    "order_key",
    "partition",
    "predictive_access",
    "project",
    "row_identifier",
    "t0_structural_membership",
}
CODE_KEYS = {*CODE_FEATURES, "row_identifier"}
PROCESS_KEYS = {*PROCESS_FEATURES, "row_identifier"}
TEXT_KEYS = {
    "raw_commit_message",
    "raw_commit_message_bytes_base64",
    "raw_commit_message_sha256",
    "row_identifier",
}
EVIDENCE_FIELDS = (
    "row_identifier",
    "project",
    "benchmark_defined_observed_label",
    "algorithm",
    "configuration",
    "modalities",
    "raw_predicted_probability",
    "final_frozen_probability",
    "fixed_threshold_prediction",
    "fixed_threshold",
    "calibration_state",
    "model_identity_sha256",
    "model_provenance",
    "calibration_provenance",
    "execution_identifier",
)
INTEGRITY_CHECKS = (
    "exact T1 membership",
    "duplicate identities",
    "missing predictions",
    "missing probabilities",
    "probability range",
    "class prevalence",
    "configuration completeness",
    "execution-scope completeness",
    "T1/T2 contamination",
    "TRAIN/VALIDATION/T1 identity overlap",
    "leakage-contract violations",
    "model/configuration provenance",
    "calibration provenance",
)


class ConfirmatoryExecutionError(RuntimeError):
    """A fail-closed authorization, contract, integrity, or execution error."""


def file_sha256(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _manifest_entries(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        checksum, name = line.split("  ", 1)
        if len(checksum) != 64 or name in entries:
            raise ConfirmatoryExecutionError(f"malformed manifest: {path}")
        entries[name] = checksum
    return entries


def verify_manifest(directory: Path) -> dict[str, Any]:
    manifest = directory / "MANIFEST.sha256"
    if not manifest.is_file():
        raise ConfirmatoryExecutionError(f"missing manifest: {manifest}")
    entries = _manifest_entries(manifest)
    for name, expected in entries.items():
        candidate = directory / name
        if not candidate.is_file() or file_sha256(candidate) != expected:
            raise ConfirmatoryExecutionError(f"manifest mismatch: {candidate}")
    return {
        "manifest_sha256": file_sha256(manifest),
        "entry_count": len(entries),
        "status": "PASS",
    }


def verify_authorization(root: Path) -> dict[str, Any]:
    directory = root / AUTH_REL
    verify_manifest(directory)
    if set(_manifest_entries(directory / "MANIFEST.sha256")) != {AUTHORIZATION_FILE}:
        raise ConfirmatoryExecutionError(
            "Block 2 authorization manifest coverage changed"
        )
    if file_sha256(directory / AUTHORIZATION_FILE) != EXPECTED_AUTHORIZATION_SHA256:
        raise ConfirmatoryExecutionError("Block 2 authorization bytes changed")
    record = load_json(directory / AUTHORIZATION_FILE)
    required = (
        record["scientific_authorization"]["authorization_mode"] == AUTHORIZATION_MODE,
        record["heldout_identity_contract"]["t1"]["access_state"]
        == "AUTHORIZED_NOT_YET_ACCESSED",
        record["heldout_identity_contract"]["t1"]["predictive_access_count"] == 0,
        record["heldout_identity_contract"]["t2"]["access_state"] == "DENY",
        record["heldout_identity_contract"]["t2"]["predictive_access_count"] == 0,
        record["xai_contract"]["access_state"] == "DENY",
        record["xai_contract"]["execution_count"] == 0,
        record["discrepancies"] == [],
        len(record["execution_matrix"]) == 28,
    )
    if not all(required):
        raise ConfirmatoryExecutionError("Block 2 authorization invariant failed")
    computed_id = hashlib.sha256(
        record["execution_identifier_definition"]["canonical_basis"].encode()
    ).hexdigest()
    if computed_id != record["execution_identifier"]:
        raise ConfirmatoryExecutionError("deterministic execution identity changed")
    return record


def _validate_amendment_payload(
    amendment: dict[str, Any],
    authorization: dict[str, Any],
    sprint53: dict[str, Any],
    manifest_entries: dict[str, str],
) -> None:
    expected_enumeration = [
        {
            "index": index,
            "name": name,
            "declared_sha256": checksum,
            "exists": True,
            "hash_verified": True,
        }
        for index, (name, checksum) in enumerate(manifest_entries.items(), start=1)
    ]
    immutable = amendment["immutable_inputs"]
    correction = amendment["metadata_correction"]
    counters = amendment["counters_at_amendment"]
    effective = amendment["effective_authorization_view"]
    checks = (
        amendment["classification"]
        == "PROSPECTIVE_METADATA_CORRECTION_BEFORE_T1_ACCESS",
        amendment["execution_identifier"] == authorization["execution_identifier"],
        immutable["original_authorization"]["sha256_before"]
        == EXPECTED_AUTHORIZATION_SHA256,
        immutable["original_authorization"]["sha256_at_amendment"]
        == EXPECTED_AUTHORIZATION_SHA256,
        immutable["original_authorization"]["modified"] is False,
        immutable["sprint53_manifest"]["sha256_declared"]
        == EXPECTED_SPRINT53_MANIFEST_SHA256,
        immutable["sprint53_manifest"]["sha256_actual"]
        == EXPECTED_SPRINT53_MANIFEST_SHA256,
        immutable["sprint53_manifest"]["hashes_identical"] is True,
        immutable["sprint53_manifest"]["modified"] is False,
        correction["field"] == "sprint53_protocol.manifest_entry_count",
        correction["original_declared_entry_count"] == 21,
        correction["independently_verified_actual_entry_count"] == 22,
        correction["effective_entry_count"] == 22,
        correction["authorized_correction_fields"]
        == ["sprint53_protocol.manifest_entry_count"],
        correction["generic_tolerance_or_bypass"] is False,
        sprint53["manifest_sha256"] == EXPECTED_SPRINT53_MANIFEST_SHA256,
        sprint53["entry_count"] == 22,
        amendment["manifest_entries"] == expected_enumeration,
        amendment["entry_verification"]
        == {
            "enumerated_entry_count": 22,
            "all_entries_exist": True,
            "all_entry_hashes_match": True,
            "verification_status": "PASS_ALL_22_ENTRIES",
        },
        all(
            value is False
            for value in amendment["scientific_contract_changes"].values()
        ),
        counters
        == {
            "t1_predictive_access_count": 0,
            "t2_predictive_access_count": 0,
            "predictive_scoring_count": 0,
            "xai_execution_count": 0,
        },
        effective["composition"]
        == ["original immutable authorization", "this prospective amendment"],
        effective["effective_sprint53_manifest_entry_count"] == 22,
        effective["authorization_mode"] == AUTHORIZATION_MODE,
        effective["t1_access_state"] == "AUTHORIZED_NOT_YET_ACCESSED",
        effective["t2_access_state"] == "DENY",
        effective["xai_access_state"] == "DENY",
        amendment["remaining_discrepancies_after_effective_view"] == [],
    )
    if not all(checks):
        raise ConfirmatoryExecutionError("approved prospective amendment changed")


def verify_amendment(
    root: Path, authorization: dict[str, Any], sprint53: dict[str, Any]
) -> dict[str, Any]:
    directory = root / AMENDMENT_REL
    verified = verify_manifest(directory)
    manifest_path = directory / "MANIFEST.sha256"
    entries = _manifest_entries(manifest_path)
    if set(entries) != {AMENDMENT_FILE}:
        raise ConfirmatoryExecutionError("amendment manifest coverage changed")
    if (
        verified["manifest_sha256"] != EXPECTED_AMENDMENT_MANIFEST_SHA256
        or entries[AMENDMENT_FILE] != EXPECTED_AMENDMENT_SHA256
        or file_sha256(directory / AMENDMENT_FILE) != EXPECTED_AMENDMENT_SHA256
    ):
        raise ConfirmatoryExecutionError("approved prospective amendment bytes changed")
    sprint53_entries = _manifest_entries(root / SPRINT53_REL / "MANIFEST.sha256")
    amendment = load_json(directory / AMENDMENT_FILE)
    _validate_amendment_payload(amendment, authorization, sprint53, sprint53_entries)
    historical = root / amendment["historical_failure_preservation"]["path"]
    if (
        amendment["historical_failure_preservation"]
        != {
            "path": str(ENGINE_REL / "pre_execution_failure.json"),
            "sha256": EXPECTED_HISTORICAL_FAILURE_SHA256,
            "preserved": True,
        }
        or not historical.is_file()
        or file_sha256(historical) != EXPECTED_HISTORICAL_FAILURE_SHA256
    ):
        raise ConfirmatoryExecutionError("historical fail-closed evidence changed")
    return {
        "status": "PASS_EXACT_PROSPECTIVE_METADATA_CORRECTION",
        "amendment_sha256": EXPECTED_AMENDMENT_SHA256,
        "original_declared_entry_count": 21,
        "effective_entry_count": 22,
        "verified_entry_count": len(sprint53_entries),
    }


def verify_contracts(root: Path, authorization: dict[str, Any]) -> dict[str, Any]:
    sprint53 = verify_manifest(root / SPRINT53_REL)
    declared = authorization["sprint53_protocol"]
    if (
        declared["manifest_sha256"] != EXPECTED_SPRINT53_MANIFEST_SHA256
        or sprint53["manifest_sha256"] != EXPECTED_SPRINT53_MANIFEST_SHA256
        or declared["manifest_entry_count"] != 21
        or sprint53["entry_count"] != 22
    ):
        raise ConfirmatoryExecutionError("Sprint 53 protocol manifest changed")
    amendment = verify_amendment(root, authorization, sprint53)
    checked: dict[str, str] = {}
    for role, item in authorization["contract_registry"].items():
        candidate = root / item["path"]
        if not candidate.is_file() or file_sha256(candidate) != item["sha256"]:
            raise ConfirmatoryExecutionError(f"frozen {role} contract changed")
        checked[role] = item["sha256"]
    return {
        "sprint53_manifest": sprint53,
        "prospective_amendment": amendment,
        "contracts": checked,
    }


def _identity_hash(rows: list[dict[str, Any]]) -> str:
    selected = [
        {
            "project": row["project"],
            "row_identifier": row["row_identifier"],
            "order_key": row["order_key"],
        }
        for row in rows
    ]
    return hashlib.sha256(canonical_bytes(selected)).hexdigest()


def structural_memberships(root: Path) -> dict[str, Any]:
    path = root / FREEZE_REL / "temporal_partition_manifest.jsonl.gz"
    selected: dict[str, list[dict[str, Any]]] = {
        "TRAIN": [],
        "VALIDATION": [],
        "T1": [],
        "T2": [],
    }
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            if set(row) != PARTITION_KEYS or row["partition"] not in selected:
                raise ConfirmatoryExecutionError("frozen membership schema changed")
            if row["partition"] in {"T1", "T2"} and row["predictive_access"] != "DENY":
                raise ConfirmatoryExecutionError(
                    "held-out predictive access is not DENY"
                )
            selected[row["partition"]].append(row)
    identifiers = {
        partition: [row["row_identifier"] for row in rows]
        for partition, rows in selected.items()
    }
    if any(len(values) != len(set(values)) for values in identifiers.values()):
        raise ConfirmatoryExecutionError("duplicate partition identity")
    if any(
        set(identifiers[left]) & set(identifiers[right])
        for index, left in enumerate(selected)
        for right in list(selected)[index + 1 :]
    ):
        raise ConfirmatoryExecutionError("cross-partition identity contamination")
    if (
        len(selected["T1"]) != EXPECTED_T1_ROWS
        or _identity_hash(selected["T1"]) != EXPECTED_T1_HASH
    ):
        raise ConfirmatoryExecutionError("T1 identity contract changed")
    if (
        len(selected["T2"]) != EXPECTED_T2_ROWS
        or _identity_hash(selected["T2"]) != EXPECTED_T2_HASH
    ):
        raise ConfirmatoryExecutionError("T2 identity contract changed")
    return {
        "status": "PASS_STRUCTURAL_ONLY",
        "membership_manifest_sha256": file_sha256(path),
        "counts": {key: len(value) for key, value in selected.items()},
        "identity_hashes": {"T1": EXPECTED_T1_HASH, "T2": EXPECTED_T2_HASH},
        "predictive_access": {"T1": "DENY", "T2": "DENY"},
        "identifiers": identifiers,
    }


def _selected_rows(root: Path) -> dict[tuple[str, str, str], dict[str, Any]]:
    frozen = load_json(root / GOVERNANCE_REL / "frozen_hyperparameter_provenance.json")
    source = root / frozen["source"]
    if (
        file_sha256(source) != frozen["source_sha256"]
        or len(frozen["selected_rows"]) != 168
    ):
        raise ConfirmatoryExecutionError("frozen hyperparameter provenance changed")
    indexed = {
        (row["project"], row["algorithm"], MODALITY_CODES[row["modality"]]): row
        for row in frozen["selected_rows"]
    }
    expected = {
        (project, algorithm, modality)
        for project in EXPECTED_PROJECTS
        for algorithm in ALGORITHMS
        for modality in MODALITIES
    }
    if set(indexed) != expected:
        raise ConfirmatoryExecutionError("selected hyperparameter matrix incomplete")
    return indexed


def _development_provenance(root: Path) -> dict[tuple[str, str], dict[str, Any]]:
    payload = load_json(root / CAMPAIGN_REL / "execution_provenance.json")
    indexed = {
        (row["project"], row["algorithm_family"]): row for row in payload["rows"]
    }
    expected = {
        (project, algorithm)
        for project in EXPECTED_PROJECTS
        for algorithm in ALGORITHMS
    }
    if set(indexed) != expected:
        raise ConfirmatoryExecutionError("development model provenance incomplete")
    return indexed


def _latest_isotonic_states(root: Path) -> dict[str, dict[str, Any]]:
    path = root / CALIBRATION_REL / "calibrator_states.jsonl.gz"
    states: dict[str, dict[str, Any]] = {}
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            if (
                row["algorithm"] == "LightGBM"
                and row["configuration"] == "P"
                and row["method"] == "ISOTONIC"
                and row["evaluation_origin"] == 11
            ):
                states[row["project"]] = row
    if set(states) != set(EXPECTED_PROJECTS):
        raise ConfirmatoryExecutionError(
            "frozen project-local isotonic states incomplete"
        )
    return states


def _modalities(configuration: str) -> tuple[str, ...]:
    result = tuple(configuration.split("+"))
    if not result or any(value not in MODALITIES for value in result):
        raise ConfirmatoryExecutionError("unknown frozen configuration")
    return result


def build_execution_plan(
    root: Path, authorization: dict[str, Any]
) -> list[dict[str, Any]]:
    selected = _selected_rows(root)
    provenance = _development_provenance(root)
    calibrators = _latest_isotonic_states(root)
    unimodal = load_json(root / UNIMODAL_CONTRACT_REL)
    plan = []
    for project in EXPECTED_PROJECTS:
        for scope in authorization["execution_matrix"]:
            algorithm = scope["algorithm"]
            configuration = scope["configuration"]
            modalities = _modalities(configuration)
            base = [selected[(project, algorithm, modality)] for modality in modalities]
            frozen_provenance = provenance[(project, algorithm)]
            candidate_ids = {
                modality: row["selected_candidate_id"]
                for modality, row in zip(modalities, base, strict=True)
            }
            if any(
                frozen_provenance["selected_candidate_ids"][key] != value
                for key, value in candidate_ids.items()
            ):
                raise ConfirmatoryExecutionError(
                    "selection/provenance identity mismatch"
                )
            preprocessing = {
                modality: (
                    unimodal["numeric_preprocessing"][algorithm]
                    if modality in {"C", "P"}
                    else unimodal["modalities"]["T"]["representation"]
                )
                for modality in modalities
            }
            calibration = {
                "state": scope["calibration"],
                "fitting_during_t1": False,
                "selection_using_t1": False,
            }
            if scope["calibration"] == "ISOTONIC":
                state = calibrators[project]
                calibration.update(
                    {
                        "source": str(CALIBRATION_REL / "calibrator_states.jsonl.gz"),
                        "source_sha256": file_sha256(
                            root / CALIBRATION_REL / "calibrator_states.jsonl.gz"
                        ),
                        "state_key": {
                            "project": project,
                            "algorithm": "LightGBM",
                            "configuration": "P",
                            "method": "ISOTONIC",
                            "evaluation_origin": 11,
                        },
                        "fit_membership_digest": state["fit_membership_digest"],
                        "fit_rows": state["fit_rows"],
                        "state_sha256": digest(state),
                    }
                )
            late_fusion = None
            if len(modalities) > 1:
                late_fusion = {
                    "architecture": "DECISION_LEVEL_STACKING_LATE_FUSION",
                    "base_modalities": list(FUSION_CONFIGURATIONS[configuration]),
                    "independently_learned_base_modalities": True,
                    "meta_learner_family": "Logistic Regression",
                    "meta_training_membership_sha256": frozen_provenance[
                        "meta_training_membership_sha256"
                    ],
                    "warmup_backfilled": False,
                    "raw_feature_concatenation": False,
                    "averaging": False,
                    "voting": False,
                }
            identity_basis = {
                "project": project,
                "algorithm": algorithm,
                "configuration": configuration,
                "selected_candidate_ids": candidate_ids,
                "selected_parameters": {
                    modality: row["selected_parameters"]
                    for modality, row in zip(modalities, base, strict=True)
                },
                "train_identity_sha256": frozen_provenance["train_membership_sha256"],
                "preprocessing": preprocessing,
                "late_fusion": late_fusion,
                "calibration": calibration,
                "threshold": THRESHOLD,
            }
            plan.append(
                {
                    **identity_basis,
                    "model_identity_sha256": digest(identity_basis),
                    "training_partition": "TRAIN",
                    "development_validation_used_for_model_selection": False,
                    "t1_used_for_fit_or_selection": False,
                    "t2_used": False,
                }
            )
    if (
        len(plan) != 392
        or len(
            {(row["project"], row["algorithm"], row["configuration"]) for row in plan}
        )
        != 392
    ):
        raise ConfirmatoryExecutionError("project-scope execution plan incomplete")
    return plan


def pre_execution_integrity(root: Path) -> dict[str, Any]:
    authorization = verify_authorization(root)
    contracts = verify_contracts(root, authorization)
    memberships = structural_memberships(root)
    plan = build_execution_plan(root, authorization)
    matrix = {(row["algorithm"], row["configuration"]) for row in plan}
    if len(matrix) != 28 or any(row["threshold"] != THRESHOLD for row in plan):
        raise ConfirmatoryExecutionError("execution matrix or threshold changed")
    calibration = Counter(row["calibration"]["state"] for row in plan)
    if calibration != Counter({"RAW": 378, "ISOTONIC": 14}):
        raise ConfirmatoryExecutionError("project-scope calibration mapping changed")
    return {
        "status": "PASS_READY_T1_NOT_ACCESSED",
        "authorization_sha256": file_sha256(root / AUTH_REL / AUTHORIZATION_FILE),
        "execution_identifier": authorization["execution_identifier"],
        "contract_verification": contracts,
        "membership_verification": {
            key: value for key, value in memberships.items() if key != "identifiers"
        },
        "scope_count": 28,
        "project_scope_count": len(plan),
        "expected_evidence_rows": EXPECTED_EVIDENCE_ROWS,
        "calibration_project_scope_counts": dict(calibration),
        "threshold": THRESHOLD,
        "near_perfect_trigger": "ANY_T1_METRIC_GREATER_THAN_OR_EQUAL_TO_0.99",
        "evidence_fields": list(EVIDENCE_FIELDS),
        "integrity_checks": list(INTEGRITY_CHECKS),
        "t1_predictive_access_count": 0,
        "t2_predictive_access_count": 0,
        "xai_execution_count": 0,
        "discrepancies": [],
        "plan": plan,
    }


def _selected_config(
    base: dict[str, Any], algorithm: str, parameters: dict[str, Any]
) -> dict[str, Any]:
    result = copy.deepcopy(base)
    result["algorithms"][algorithm] = dict(parameters)
    return result


def reconstruct_project_models(
    root: Path, project: str, project_plan: list[dict[str, Any]]
) -> dict[str, Any]:
    """Reconstruct frozen TRAIN-only base and strict-forward stacking states."""
    if project not in EXPECTED_PROJECTS:
        raise ConfirmatoryExecutionError("unknown project")
    rows = load_development_project(root, project)
    train = [row for row in rows if row["partition"] == "TRAIN"]
    if any(row["partition"] in {"T1", "T2"} for row in rows):
        raise ConfirmatoryExecutionError("held-out row reached reconstruction")
    base_config = load_json(root / UNIMODAL_CONTRACT_REL)
    fusion_config = load_json(root / FUSION_CONTRACT_REL)
    result = {}
    for algorithm in ALGORITHMS:
        rows_for_algorithm = [
            row for row in project_plan if row["algorithm"] == algorithm
        ]
        exemplar = rows_for_algorithm[0]
        parameter_by_modality = {}
        config_by_modality = {}
        for modality in MODALITIES:
            source = next(
                row
                for row in project_plan
                if row["algorithm"] == algorithm
                and modality in row["selected_parameters"]
            )
            parameter_by_modality[modality] = source["selected_parameters"][modality]
            config_by_modality[modality] = _selected_config(
                base_config, algorithm, parameter_by_modality[modality]
            )
        oof = _build_selected_oof(train, algorithm, config_by_modality)
        oof_x = np.asarray(
            [row["probabilities"] for row in oof["records"]], dtype=float
        )
        oof_y = np.asarray([row["target"] for row in oof["records"]], dtype=int)
        bases = {
            modality: fit_unimodal(
                train, algorithm, modality, config_by_modality[modality]
            )
            for modality in MODALITIES
        }
        meta = {}
        for configuration, modalities in FUSION_CONFIGURATIONS.items():
            columns = [MODALITIES.index(modality) for modality in modalities]
            meta[configuration] = _meta(fusion_config).fit(oof_x[:, columns], oof_y)
        if (
            digest([row["row_identifier"] for row in train])
            != exemplar["train_identity_sha256"]
        ):
            raise ConfirmatoryExecutionError("reconstructed TRAIN membership changed")
        result[algorithm] = {"base": bases, "meta": meta}
    return result


def _load_allowed_payload(
    path: Path, allowed: set[str], expected: set[str]
) -> dict[str, dict[str, Any]]:
    selected: dict[str, dict[str, Any]] = {}
    with gzip.open(path, "rb") as stream:
        for line in stream:
            match = ROW_ID_PATTERN.search(line)
            if match is None:
                raise ConfirmatoryExecutionError(f"row identifier missing: {path.name}")
            row_id = match.group(1).decode("ascii")
            if row_id not in allowed:
                continue
            row = json.loads(line)
            if set(row) != expected:
                raise ConfirmatoryExecutionError(f"payload schema changed: {path.name}")
            selected[row_id] = row
    if set(selected) != allowed:
        raise ConfirmatoryExecutionError(
            f"authorized T1 payload incomplete: {path.name}"
        )
    return selected


def _load_authorized_t1(
    root: Path, project: str, membership_rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Materialize T1 only; caller must first persist the one-shot start marker."""
    if any(
        row["partition"] != "T1" or row["project"] != project for row in membership_rows
    ):
        raise ConfirmatoryExecutionError("non-T1 row requested")
    allowed = {row["row_identifier"] for row in membership_rows}
    base = root / FREEZE_REL
    identities = _load_allowed_payload(
        base / "row_identity_provenance.jsonl.gz", allowed, IDENTITY_KEYS
    )
    code = _load_allowed_payload(base / "code_dataset.jsonl.gz", allowed, CODE_KEYS)
    process = _load_allowed_payload(
        base / "process_dataset.jsonl.gz", allowed, PROCESS_KEYS
    )
    text = _load_allowed_payload(base / "text_dataset.jsonl.gz", allowed, TEXT_KEYS)
    result = []
    for member in membership_rows:
        row_id = member["row_identifier"]
        identity = identities[row_id]
        result.append(
            {
                "row_identifier": row_id,
                "project": project,
                "timestamp": identity["normalized_utc_timestamp"],
                "commit_sha": identity["commit_sha"],
                "partition": "T1",
                "forward_block": member["forward_block"],
                "target": int(identity[LABEL]),
                "C": [float(code[row_id][name]) for name in CODE_FEATURES],
                "P": [float(process[row_id][name]) for name in PROCESS_FEATURES],
                "T": text[row_id]["raw_commit_message"],
            }
        )
    return result


def _predict_t1(model: Any, rows: list[dict[str, Any]], modality: str) -> np.ndarray:
    if not rows or {row["partition"] for row in rows} != {"T1"}:
        raise ConfirmatoryExecutionError("authorized predictor accepts T1 only")
    classes = np.asarray(model.named_steps["model"].classes_)
    indexes = np.flatnonzero(classes == 1)
    if len(indexes) != 1:
        raise ConfirmatoryExecutionError("positive class unavailable")
    probabilities = np.asarray(
        model.predict_proba(raw_features(rows, modality))[:, indexes[0]], dtype=float
    )
    if (
        probabilities.shape != (len(rows),)
        or not np.isfinite(probabilities).all()
        or ((probabilities < 0) | (probabilities > 1)).any()
    ):
        raise ConfirmatoryExecutionError("invalid raw T1 probability")
    return probabilities


def _apply_frozen_calibration(
    raw: np.ndarray, plan: dict[str, Any], states: dict[str, dict[str, Any]]
) -> np.ndarray:
    if plan["calibration"]["state"] == "RAW":
        return raw.copy()
    if plan["calibration"]["state"] != "ISOTONIC":
        raise ConfirmatoryExecutionError("unapproved calibration state")
    state = states[plan["project"]]
    if digest(state) != plan["calibration"]["state_sha256"]:
        raise ConfirmatoryExecutionError("isotonic state provenance changed")
    return np.round(
        np.interp(raw, state["x_thresholds"], state["y_thresholds"]), decimals=12
    )


def _evidence_rows(
    t1_rows: list[dict[str, Any]],
    project_plan: list[dict[str, Any]],
    models: dict[str, Any],
    calibrators: dict[str, dict[str, Any]],
    execution_identifier: str,
) -> list[dict[str, Any]]:
    result = []
    for algorithm in ALGORITHMS:
        state = models[algorithm]
        base_probabilities = {
            modality: _predict_t1(state["base"][modality], t1_rows, modality)
            for modality in MODALITIES
        }
        streams = dict(base_probabilities)
        for configuration, modalities in FUSION_CONFIGURATIONS.items():
            matrix = np.column_stack(
                [base_probabilities[value] for value in modalities]
            )
            streams[configuration] = np.asarray(
                state["meta"][configuration].predict_proba(matrix)[:, 1], dtype=float
            )
        for plan in [row for row in project_plan if row["algorithm"] == algorithm]:
            raw = streams[plan["configuration"]]
            final = _apply_frozen_calibration(raw, plan, calibrators)
            for index, row in enumerate(t1_rows):
                evidence = {
                    "row_identifier": row["row_identifier"],
                    "project": row["project"],
                    "benchmark_defined_observed_label": row["target"],
                    "algorithm": algorithm,
                    "configuration": plan["configuration"],
                    "modalities": list(_modalities(plan["configuration"])),
                    "raw_predicted_probability": float(raw[index]),
                    "final_frozen_probability": float(final[index]),
                    "fixed_threshold_prediction": int(final[index] >= THRESHOLD),
                    "fixed_threshold": THRESHOLD,
                    "calibration_state": plan["calibration"]["state"],
                    "model_identity_sha256": plan["model_identity_sha256"],
                    "model_provenance": {
                        "training_partition": "TRAIN",
                        "train_identity_sha256": plan["train_identity_sha256"],
                        "selected_candidate_ids": plan["selected_candidate_ids"],
                        "late_fusion": plan["late_fusion"],
                    },
                    "calibration_provenance": plan["calibration"],
                    "execution_identifier": execution_identifier,
                }
                if tuple(evidence) != EVIDENCE_FIELDS:
                    raise ConfirmatoryExecutionError("evidence schema drift")
                result.append(evidence)
    return result


def post_execution_integrity(
    evidence: list[dict[str, Any]], memberships: dict[str, Any]
) -> dict[str, Any]:
    if len(evidence) != EXPECTED_EVIDENCE_ROWS:
        raise ConfirmatoryExecutionError("missing or excess T1 evidence rows")
    t1 = set(memberships["identifiers"]["T1"])
    t2 = set(memberships["identifiers"]["T2"])
    development = set(memberships["identifiers"]["TRAIN"]) | set(
        memberships["identifiers"]["VALIDATION"]
    )
    keys = [
        (row["row_identifier"], row["algorithm"], row["configuration"])
        for row in evidence
    ]
    if len(keys) != len(set(keys)):
        raise ConfirmatoryExecutionError("duplicate T1 identity/scope evidence")
    evidence_ids = {row["row_identifier"] for row in evidence}
    if evidence_ids != t1 or evidence_ids & t2 or evidence_ids & development:
        raise ConfirmatoryExecutionError("T1 evidence membership contamination")
    if any(tuple(row) != EVIDENCE_FIELDS for row in evidence):
        raise ConfirmatoryExecutionError("evidence schema incomplete")
    if any(
        not np.isfinite(row[field]) or not 0 <= row[field] <= 1
        for row in evidence
        for field in ("raw_predicted_probability", "final_frozen_probability")
    ):
        raise ConfirmatoryExecutionError("missing or out-of-range probability")
    expected_scopes = {
        (algorithm, configuration)
        for algorithm in ALGORITHMS
        for configuration in CONFIGURATIONS
    }
    by_identity: dict[str, set[tuple[str, str]]] = defaultdict(set)
    for row in evidence:
        by_identity[row["row_identifier"]].add((row["algorithm"], row["configuration"]))
    if any(scopes != expected_scopes for scopes in by_identity.values()):
        raise ConfirmatoryExecutionError("per-identity execution scope incomplete")
    labels = {
        row["row_identifier"]: row["benchmark_defined_observed_label"]
        for row in evidence
    }
    if set(labels.values()) != {0, 1}:
        raise ConfirmatoryExecutionError("T1 class support incomplete")
    return {
        "status": "PASS_COMPLETE_EVIDENCE",
        "evidence_rows": len(evidence),
        "unique_t1_identities": len(evidence_ids),
        "scope_count_per_identity": 28,
        "positive": sum(labels.values()),
        "negative": len(labels) - sum(labels.values()),
        "prevalence": sum(labels.values()) / len(labels),
        "duplicate_identity_scope_rows": 0,
        "missing_predictions": 0,
        "missing_probabilities": 0,
        "out_of_range_probabilities": 0,
        "t2_contamination": 0,
        "development_t1_overlap": 0,
        "leakage_contract_violations": 0,
        "failed_scopes": [],
    }


def near_perfect_flags(metric_rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Preserve and flag; never reject, alter, or suppress high results."""
    return [
        {**row, "integrity_audit_required": True}
        for row in metric_rows
        if float(row["metric_value"]) >= NEAR_PERFECT_TRIGGER
    ]


def _ece(targets: np.ndarray, probabilities: np.ndarray) -> float:
    indexes = np.minimum((probabilities * 10).astype(int), 9)
    return float(
        sum(
            float((indexes == index).mean())
            * abs(
                float(targets[indexes == index].mean())
                - float(probabilities[indexes == index].mean())
            )
            for index in range(10)
            if (indexes == index).any()
        )
    )


def _metric_values(targets: np.ndarray, probabilities: np.ndarray) -> dict[str, Any]:
    predictions = (probabilities >= THRESHOLD).astype(int)
    tn, fp, fn, tp = confusion_matrix(targets, predictions, labels=[0, 1]).ravel()
    values = {
        "PR_AUC": float(average_precision_score(targets, probabilities)),
        "MCC": float(matthews_corrcoef(targets, predictions)),
        "ROC_AUC": float(roc_auc_score(targets, probabilities)),
        "Recall": float(recall_score(targets, predictions, zero_division=0)),
        "Precision": float(precision_score(targets, predictions, zero_division=0)),
        "F1": float(f1_score(targets, predictions, zero_division=0)),
        "Brier": float(brier_score_loss(targets, probabilities)),
        "ECE": _ece(targets, probabilities),
        "TN": int(tn),
        "FP": int(fp),
        "FN": int(fn),
        "TP": int(tp),
    }
    if any(not math.isfinite(values[metric]) for metric in METRICS):
        raise ConfirmatoryExecutionError("non-finite confirmatory metric")
    return values


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ConfirmatoryExecutionError(f"empty required table: {path.name}")
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def _project_metrics(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in evidence:
        grouped[row["project"], row["algorithm"], row["configuration"]].append(row)
    result = []
    for key in sorted(grouped):
        rows = grouped[key]
        targets = np.asarray(
            [row["benchmark_defined_observed_label"] for row in rows], dtype=int
        )
        probabilities = np.asarray(
            [row["final_frozen_probability"] for row in rows], dtype=float
        )
        if set(targets.tolist()) != {0, 1}:
            raise ConfirmatoryExecutionError("project T1 metric lacks class support")
        result.append(
            {
                "project": key[0],
                "algorithm": key[1],
                "configuration": key[2],
                "n": len(rows),
                "positive": int(targets.sum()),
                "negative": int(len(targets) - targets.sum()),
                "prevalence": float(targets.mean()),
                "calibration_state": rows[0]["calibration_state"],
                "threshold": THRESHOLD,
                **_metric_values(targets, probabilities),
            }
        )
    if len(result) != 392:
        raise ConfirmatoryExecutionError("T1-A project metric matrix incomplete")
    return result


def _aggregate_metrics(project_metrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for algorithm in ALGORITHMS:
        for configuration in CONFIGURATIONS:
            selected = [
                row
                for row in project_metrics
                if row["algorithm"] == algorithm
                and row["configuration"] == configuration
            ]
            for metric in METRICS:
                values = np.asarray([row[metric] for row in selected], dtype=float)
                result.append(
                    {
                        "algorithm": algorithm,
                        "configuration": configuration,
                        "metric": metric,
                        "n_projects": len(values),
                        "mean": float(values.mean()),
                        "sample_standard_deviation": float(values.std(ddof=1)),
                        "median": float(np.median(values)),
                        "q1": float(np.quantile(values, 0.25)),
                        "q3": float(np.quantile(values, 0.75)),
                        "interquartile_range": float(
                            np.quantile(values, 0.75) - np.quantile(values, 0.25)
                        ),
                        "minimum": float(values.min()),
                        "maximum": float(values.max()),
                    }
                )
    return result


def _comparison_rows(
    root: Path, project_metrics: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    indexed = {
        (row["project"], row["algorithm"], row["configuration"]): row
        for row in project_metrics
    }
    contract = load_json(root / SPRINT53_REL / "frozen_comparator_contract.json")
    result: dict[str, list[dict[str, Any]]] = {
        "BEST_UNIMODAL": [],
        "BEST_PAIRWISE": [],
    }
    for identity in contract["comparator_identities"]:
        key = (identity["project"], identity["algorithm"])
        full = indexed[*key, "C+P+T"]
        baseline = indexed[*key, identity["selected_configuration"]]
        for metric in METRICS:
            raw_difference = float(full[metric] - baseline[metric])
            favorable_difference = (
                -raw_difference if metric in {"Brier", "ECE"} else raw_difference
            )
            result[identity["family"]].append(
                {
                    "project": key[0],
                    "algorithm": key[1],
                    "family": identity["family"],
                    "metric": metric,
                    "full_configuration": "C+P+T",
                    "comparator_configuration": identity["selected_configuration"],
                    "full_value": full[metric],
                    "comparator_value": baseline[metric],
                    "raw_full_minus_comparator": raw_difference,
                    "difference_favoring_full": favorable_difference,
                    "selection_partition": "DEVELOPMENT_VALIDATION",
                }
            )
    return result["BEST_UNIMODAL"], result["BEST_PAIRWISE"]


def _rank_biserial(differences: np.ndarray) -> float:
    nonzero = differences[differences != 0]
    if len(nonzero) == 0:
        return 0.0
    ranks = rankdata(np.abs(nonzero), method="average")
    return float((ranks[nonzero > 0].sum() - ranks[nonzero < 0].sum()) / ranks.sum())


def _holm(rows: list[dict[str, Any]], alpha: float = 0.05) -> None:
    ordered = sorted(enumerate(rows), key=lambda value: value[1]["raw_p_value"])
    running = 0.0
    for rank, (index, row) in enumerate(ordered):
        running = max(running, min(1.0, (len(rows) - rank) * row["raw_p_value"]))
        rows[index]["holm_adjusted_p_value"] = running
        if running >= alpha:
            state = "NON_SIGNIFICANT"
        elif row["mean_paired_difference"] > 0:
            state = "SIGNIFICANT_FAVORS_PROPOSAL"
        elif row["mean_paired_difference"] < 0:
            state = "SIGNIFICANT_FAVORS_COMPARATOR"
        else:
            state = "NON_SIGNIFICANT"
        rows[index]["result_state"] = state


def _statistical_rows(
    project_metrics: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    indexed = {
        (row["project"], row["algorithm"], row["configuration"]): row
        for row in project_metrics
    }
    families = {
        "FULL_VS_SIX": [
            ("C+P+T", value) for value in ("C", "P", "T", "C+P", "C+T", "P+T")
        ],
        "PAIRWISE_VS_PARENTS": [
            ("C+P", "C"),
            ("C+P", "P"),
            ("C+T", "C"),
            ("C+T", "T"),
            ("P+T", "P"),
            ("P+T", "T"),
        ],
    }
    omnibus = []
    pairwise = []
    for algorithm in ALGORITHMS:
        for metric in METRICS:
            arrays = [
                np.asarray(
                    [indexed[p, algorithm, c][metric] for p in EXPECTED_PROJECTS]
                )
                for c in CONFIGURATIONS
            ]
            if np.all(np.ptp(np.stack(arrays), axis=0) == 0):
                statistic, p_value = 0.0, 1.0
            else:
                test = friedmanchisquare(*arrays)
                statistic, p_value = float(test.statistic), float(test.pvalue)
                if not math.isfinite(statistic) or not math.isfinite(p_value):
                    raise ConfirmatoryExecutionError("invalid Friedman result")
            omnibus.append(
                {
                    "algorithm": algorithm,
                    "metric": metric,
                    "test": "FRIEDMAN",
                    "n_complete_projects": 14,
                    "configuration_count": 7,
                    "statistic": statistic,
                    "raw_p_value": p_value,
                    "result_state": (
                        "SIGNIFICANT" if p_value < 0.05 else "NON_SIGNIFICANT"
                    ),
                }
            )
            for family_id, contrasts in families.items():
                family = []
                for proposal, comparator in contrasts:
                    differences = np.asarray(
                        [
                            indexed[p, algorithm, proposal][metric]
                            - indexed[p, algorithm, comparator][metric]
                            for p in EXPECTED_PROJECTS
                        ],
                        dtype=float,
                    )
                    if metric in {"Brier", "ECE"}:
                        differences = -differences
                    nonzero = int(np.sum(differences != 0))
                    if nonzero < 2:
                        statistic, p_value = 0.0, 1.0
                    else:
                        test = wilcoxon(
                            differences,
                            zero_method="wilcox",
                            correction=False,
                            alternative="two-sided",
                            method="auto",
                        )
                        statistic, p_value = float(test.statistic), float(test.pvalue)
                    family.append(
                        {
                            "family": family_id,
                            "algorithm": algorithm,
                            "metric": metric,
                            "contrast": f"{proposal}_MINUS_{comparator}",
                            "proposal_configuration": proposal,
                            "comparator_configuration": comparator,
                            "n_complete_projects": 14,
                            "n_nonzero_pairs": nonzero,
                            "statistic": statistic,
                            "raw_p_value": p_value,
                            "holm_adjusted_p_value": None,
                            "mean_paired_difference": float(differences.mean()),
                            "median_paired_difference": float(np.median(differences)),
                            "positive_projects": int(np.sum(differences > 0)),
                            "tied_projects": int(np.sum(differences == 0)),
                            "negative_projects": int(np.sum(differences < 0)),
                            "paired_rank_biserial_correlation": _rank_biserial(
                                differences
                            ),
                            "result_state": None,
                        }
                    )
                _holm(family)
                pairwise.extend(family)
    return omnibus, pairwise


def _ablation_rows(project_metrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    indexed = {
        (row["project"], row["algorithm"], row["configuration"]): row
        for row in project_metrics
    }
    contrasts = [("C+P+T", value) for value in ("C", "P", "T", "C+P", "C+T", "P+T")] + [
        ("C+P", "C"),
        ("C+P", "P"),
        ("C+T", "C"),
        ("C+T", "T"),
        ("P+T", "P"),
        ("P+T", "T"),
    ]
    result = []
    for project in EXPECTED_PROJECTS:
        for algorithm in ALGORITHMS:
            for proposal, comparator in contrasts:
                for metric in METRICS:
                    raw = (
                        indexed[project, algorithm, proposal][metric]
                        - indexed[project, algorithm, comparator][metric]
                    )
                    result.append(
                        {
                            "project": project,
                            "algorithm": algorithm,
                            "metric": metric,
                            "contrast": f"{proposal}_MINUS_{comparator}",
                            "proposal_configuration": proposal,
                            "comparator_configuration": comparator,
                            "raw_difference": raw,
                            "difference_favoring_proposal": (
                                -raw if metric in {"Brier", "ECE"} else raw
                            ),
                        }
                    )
    return result


def _calibration_rows(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in evidence:
        grouped[row["project"], row["algorithm"], row["configuration"]].append(row)
    result = []
    for key in sorted(grouped):
        rows = grouped[key]
        targets = np.asarray(
            [row["benchmark_defined_observed_label"] for row in rows], dtype=int
        )
        raw = np.asarray([row["raw_predicted_probability"] for row in rows])
        final = np.asarray([row["final_frozen_probability"] for row in rows])
        raw_values = _metric_values(targets, raw)
        final_values = _metric_values(targets, final)
        result.append(
            {
                "project": key[0],
                "algorithm": key[1],
                "configuration": key[2],
                "selected_calibration_state": rows[0]["calibration_state"],
                "raw_Brier": raw_values["Brier"],
                "selected_Brier": final_values["Brier"],
                "Brier_change_selected_minus_raw": final_values["Brier"]
                - raw_values["Brier"],
                "raw_ECE": raw_values["ECE"],
                "selected_ECE": final_values["ECE"],
                "ECE_change_selected_minus_raw": final_values["ECE"]
                - raw_values["ECE"],
            }
        )
    return result


def _consistency_rows(
    root: Path,
    project_metrics: list[dict[str, Any]],
    best_unimodal: list[dict[str, Any]],
    best_pairwise: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    development = {}
    with (
        root / "audits/q1-temporal-robustness-cv/1.0.0/paired_statistical_input.csv"
    ).open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            development[
                row["project"], row["algorithm"], row["configuration"], row["metric"]
            ] = float(row["project_cv_mean"])
    t1 = {
        (row["project"], row["algorithm"], row["configuration"], metric): row[metric]
        for row in project_metrics
        for metric in ("PR_AUC", "MCC")
    }
    selected = [
        row
        for row in best_unimodal + best_pairwise
        if row["metric"] in {"PR_AUC", "MCC"}
    ]
    result = []
    rank_cache = {}
    for project in EXPECTED_PROJECTS:
        for algorithm in ALGORITHMS:
            for metric in ("PR_AUC", "MCC"):
                dev = np.asarray(
                    [development[project, algorithm, c, metric] for c in CONFIGURATIONS]
                )
                heldout = np.asarray(
                    [t1[project, algorithm, c, metric] for c in CONFIGURATIONS]
                )
                rank_cache[project, algorithm, metric] = float(
                    spearmanr(dev, heldout).statistic
                )
    for row in selected:
        key = row["project"], row["algorithm"]
        metric = row["metric"]
        comparator = row["comparator_configuration"]
        development_difference = (
            development[*key, "C+P+T", metric] - development[*key, comparator, metric]
        )
        t1_difference = row["raw_full_minus_comparator"]
        result.append(
            {
                "project": key[0],
                "algorithm": key[1],
                "family": row["family"],
                "metric": metric,
                "comparator_configuration": comparator,
                "development_direction": int(np.sign(development_difference)),
                "t1_direction": int(np.sign(t1_difference)),
                "sign_agreement": bool(
                    np.sign(development_difference) == np.sign(t1_difference)
                ),
                "development_rank": "SEVEN_CONFIGURATION_VECTOR",
                "t1_rank": "SEVEN_CONFIGURATION_VECTOR",
                "rank_consistency": rank_cache[*key, metric],
                "material_contradiction_flag": bool(
                    development_difference > 0 and t1_difference < 0
                ),
            }
        )
    return result


def _reliability_rows(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in evidence:
        grouped[row["algorithm"], row["configuration"]].append(row)
    result = []
    for key in sorted(grouped):
        rows = grouped[key]
        probabilities = np.asarray([row["final_frozen_probability"] for row in rows])
        targets = np.asarray([row["benchmark_defined_observed_label"] for row in rows])
        indexes = np.minimum((probabilities * 10).astype(int), 9)
        for index in range(10):
            mask = indexes == index
            result.append(
                {
                    "algorithm": key[0],
                    "configuration": key[1],
                    "bin": index,
                    "lower": index / 10,
                    "upper": (index + 1) / 10,
                    "count": int(mask.sum()),
                    "mean_probability": (
                        float(probabilities[mask].mean()) if mask.any() else None
                    ),
                    "observed_prevalence": (
                        float(targets[mask].mean()) if mask.any() else None
                    ),
                    "supported": bool(mask.any()),
                }
            )
    return result


def _near_perfect_audit(
    evidence: list[dict[str, Any]], project_metrics: list[dict[str, Any]]
) -> dict[str, Any]:
    grouped = defaultdict(list)
    for row in evidence:
        grouped[row["project"], row["algorithm"], row["configuration"]].append(row)
    triggers = []
    for metric_row in project_metrics:
        key = (
            metric_row["project"],
            metric_row["algorithm"],
            metric_row["configuration"],
        )
        rows = grouped[key]
        probabilities = np.asarray([row["final_frozen_probability"] for row in rows])
        for metric in METRICS:
            value = float(metric_row[metric])
            if value < NEAR_PERFECT_TRIGGER:
                continue
            triggers.append(
                {
                    "project": key[0],
                    "algorithm": key[1],
                    "configuration": key[2],
                    "metric": metric,
                    "metric_value": value,
                    "class_support": {
                        "positive": metric_row["positive"],
                        "negative": metric_row["negative"],
                    },
                    "prevalence": metric_row["prevalence"],
                    "confusion_matrix_where_relevant": {
                        name: metric_row[name] for name in ("TN", "FP", "FN", "TP")
                    },
                    "probability_distribution": {
                        "count": len(probabilities),
                        "minimum": float(probabilities.min()),
                        "q1": float(np.quantile(probabilities, 0.25)),
                        "median": float(np.median(probabilities)),
                        "q3": float(np.quantile(probabilities, 0.75)),
                        "maximum": float(probabilities.max()),
                        "mean": float(probabilities.mean()),
                        "standard_deviation": float(probabilities.std(ddof=1)),
                        "unique_probability_count": len(np.unique(probabilities)),
                        "boundary_probability_counts": {
                            "zero": int(np.sum(probabilities == 0)),
                            "one": int(np.sum(probabilities == 1)),
                        },
                    },
                    "duplicate_identity_diagnostics": {
                        "duplicate_row_identifiers": 0,
                        "cross_partition_identity_overlap": 0,
                        "exact_allowed_feature_duplicate_groups": (
                            "PRESERVED_FOR_BLOCK_6_AUDIT"
                        ),
                        "label_consistency_within_duplicate_groups": (
                            "PRESERVED_FOR_BLOCK_6_AUDIT"
                        ),
                    },
                    "leakage_contract_verification": "PASS",
                    "temporal_cv_trajectory_comparison": "PRESERVED_SPRINT50_REFERENCE",
                    "integrity_audit_required": True,
                }
            )
    return {
        "trigger": "ANY_T1_METRIC_GREATER_THAN_OR_EQUAL_TO_0.99",
        "trigger_count": len(triggers),
        "audit_required": bool(triggers),
        "values_preserved_unchanged": True,
        "triggers": triggers,
    }


def _scientific_classification(
    best_unimodal: list[dict[str, Any]], best_pairwise: list[dict[str, Any]]
) -> dict[str, Any]:
    primary = [
        row
        for row in best_unimodal + best_pairwise
        if row["metric"] in {"PR_AUC", "MCC"}
    ]
    grouped = defaultdict(list)
    for row in primary:
        grouped[row["family"], row["algorithm"], row["metric"]].append(
            row["difference_favoring_full"]
        )
    directions = {key: float(np.mean(values)) for key, values in grouped.items()}
    signs = [np.sign(value) for value in directions.values()]
    if all(value >= 0 for value in signs) and any(value > 0 for value in signs):
        state = "PASS_CONFIRMATORY_SUPPORT"
    elif all(value <= 0 for value in signs) and any(value < 0 for value in signs):
        state = "FAIL_CONFIRMATORY_CONTRADICTION"
    else:
        state = "MIXED_CONFIRMATORY_EVIDENCE"
    return {
        "classification": state,
        "integrity_status": "PASS",
        "decision_basis": (
            "FROZEN_PRIMARY_PR_AUC_AND_MCC_SELECTED_COMPARATOR_ALGORITHM_DIRECTIONS"
        ),
        "primary_direction_means": {
            f"{key[0]}::{key[1]}::{key[2]}": value
            for key, value in sorted(directions.items())
        },
        "negative_or_mixed_results_preserved": True,
        "post_t1_model_change": "PROHIBITED",
    }


def materialize_confirmatory_results(
    root: Path, output: Path, evidence: list[dict[str, Any]]
) -> dict[str, Any]:
    project_metrics = _project_metrics(evidence)
    aggregate = _aggregate_metrics(project_metrics)
    best_unimodal, best_pairwise = _comparison_rows(root, project_metrics)
    omnibus, statistical = _statistical_rows(project_metrics)
    calibration = _calibration_rows(evidence)
    ablation = _ablation_rows(project_metrics)
    consistency = _consistency_rows(root, project_metrics, best_unimodal, best_pairwise)
    reliability = _reliability_rows(evidence)
    near_perfect = _near_perfect_audit(evidence, project_metrics)
    classification = _scientific_classification(best_unimodal, best_pairwise)
    tables = {
        "T1-A_per_project_algorithm_configuration_metrics.csv": project_metrics,
        "T1-B_aggregate_algorithm_configuration_metrics.csv": aggregate,
        "T1-C_full_vs_frozen_best_unimodal.csv": best_unimodal,
        "T1-D_full_vs_frozen_best_pairwise.csv": best_pairwise,
        "T1-E_statistical_tests.csv": statistical,
        "T1-F_calibration_results.csv": calibration,
        "T1-G_ablation_modality_contributions.csv": ablation,
        "T1-H_development_t1_consistency.csv": consistency,
        "statistical_omnibus_results.csv": omnibus,
        "T1-FIG-1_pr_auc_data.csv": [
            row for row in aggregate if row["metric"] == "PR_AUC"
        ],
        "T1-FIG-2_mcc_data.csv": [row for row in aggregate if row["metric"] == "MCC"],
        "T1-FIG-3_stability_data.csv": consistency,
        "T1-FIG-4_ablation_data.csv": ablation,
        "T1-FIG-5_reliability_data.csv": reliability,
        "T1-FIG-6_temporal_generalization_data.csv": consistency,
    }
    for name, rows in tables.items():
        _write_csv(output / name, rows)
    _atomic_json(output / "near_perfect_result_audit.json", near_perfect)
    _atomic_json(output / "scientific_classification.json", classification)
    return {
        "table_count": 8,
        "figure_data_artifact_count": 6,
        "near_perfect_trigger_count": near_perfect["trigger_count"],
        "near_perfect_audit_required": near_perfect["audit_required"],
        "scientific_classification": classification["classification"],
    }


def prepare_engine(root: Path) -> dict[str, Any]:
    readiness = pre_execution_integrity(root)
    readiness["schema_version"] = VERSION
    readiness["engine_implementation"] = (
        "src/evaluation/q1_t1_confirmatory_execution.py"
    )
    readiness["engine_implementation_sha256"] = file_sha256(Path(__file__))
    readiness["execution_entry_point"] = "execute_one_shot"
    readiness["t1_execution_performed"] = False
    readiness["result_preservation_policy"] = (
        "PRESERVE_FAVORABLE_MIXED_NULL_UNFAVORABLE_AND_FAILED_SCOPES"
    )
    return readiness


def _atomic_json(path: Path, value: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(canonical_bytes(value))
    os.replace(temporary, path)


def _write_jsonl_gz(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as stream:
            for row in rows:
                stream.write(canonical_bytes(row))


def execute_one_shot(root: Path) -> Path:
    """Cross the T1 boundary exactly once.  Do not call during engine preparation."""
    readiness = pre_execution_integrity(root)
    authorization = verify_authorization(root)
    plan = readiness["plan"]
    models = {}
    for project in EXPECTED_PROJECTS:
        project_plan = [row for row in plan if row["project"] == project]
        models[project] = reconstruct_project_models(root, project, project_plan)
    output = root / AUTH_REL / "results"
    start = output / "execution_started.json"
    if output.exists() or start.exists():
        raise ConfirmatoryExecutionError("one-shot T1 execution was already started")
    output.mkdir(parents=True, exist_ok=False)
    amendment_sha256 = file_sha256(root / AMENDMENT_REL / AMENDMENT_FILE)
    sprint53_manifest_sha256 = file_sha256(root / SPRINT53_REL / "MANIFEST.sha256")
    _atomic_json(
        start,
        {
            "schema_version": VERSION,
            "state": "T1_EXECUTION_STARTED_IRREVERSIBLE",
            "execution_identifier": authorization["execution_identifier"],
            "authorization_sha256": readiness["authorization_sha256"],
            "amendment_sha256": amendment_sha256,
            "sprint53_manifest_sha256": sprint53_manifest_sha256,
            "t1_identity_sha256": EXPECTED_T1_HASH,
            "t2_identity_sha256": EXPECTED_T2_HASH,
            "started_at_utc": datetime.now(UTC).isoformat(),
            "one_shot_semantics": ("IRREVERSIBLE_SINGLE_T1_PREDICTIVE_ACCESS_NO_RERUN"),
            "execution_attempt": 1,
            "t1_predictive_access_count": 1,
            "t2_predictive_access_count": 0,
            "predictive_scoring_count": 0,
            "xai_execution_count": 0,
        },
    )
    memberships = structural_memberships(root)
    membership_path = root / FREEZE_REL / "temporal_partition_manifest.jsonl.gz"
    t1_by_project: dict[str, list[dict[str, Any]]] = defaultdict(list)
    with gzip.open(membership_path, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            if row["partition"] == "T1":
                t1_by_project[row["project"]].append(row)
    calibrators = _latest_isotonic_states(root)
    evidence: list[dict[str, Any]] = []
    partial = output / "t1_prediction_evidence.partial.jsonl.gz"
    try:
        for project in EXPECTED_PROJECTS:
            t1_rows = _load_authorized_t1(root, project, t1_by_project[project])
            project_plan = [row for row in plan if row["project"] == project]
            evidence.extend(
                _evidence_rows(
                    t1_rows,
                    project_plan,
                    models[project],
                    calibrators,
                    authorization["execution_identifier"],
                )
            )
            _write_jsonl_gz(partial, evidence)
        integrity = post_execution_integrity(evidence, memberships)
        final = output / "t1_prediction_evidence.jsonl.gz"
        os.replace(partial, final)
        _atomic_json(output / "post_execution_integrity.json", integrity)
        result_summary = materialize_confirmatory_results(root, output, evidence)
        _atomic_json(
            output / "execution_completed.json",
            {
                "schema_version": VERSION,
                "state": "T1_CONFIRMATORY_EXECUTION_COMPLETE_DO_NOT_RERUN",
                "execution_identifier": authorization["execution_identifier"],
                "authorization_sha256": readiness["authorization_sha256"],
                "amendment_sha256": amendment_sha256,
                "sprint53_manifest_sha256": sprint53_manifest_sha256,
                "t1_identity_sha256": EXPECTED_T1_HASH,
                "t2_identity_sha256": EXPECTED_T2_HASH,
                "evidence_sha256": file_sha256(final),
                "evidence_rows": len(evidence),
                "scope_count": 28,
                "project_scope_count": 392,
                "result_summary": result_summary,
                "completed_at_utc": datetime.now(UTC).isoformat(),
                "t1_predictive_access_count": 1,
                "t2_predictive_access_count": 0,
                "predictive_scoring_count": 1,
                "xai_execution_count": 0,
                "t1_rerun_permitted": False,
                "t2_access_state": "DENY_SEALED_REVIEWER_RESERVE",
            },
        )
        manifest_entries = [
            path
            for path in sorted(output.iterdir(), key=lambda value: value.name)
            if path.is_file() and path.name not in {"MANIFEST.sha256", partial.name}
        ]
        manifest = "".join(
            f"{file_sha256(path)}  {path.name}\n" for path in manifest_entries
        )
        (output / "MANIFEST.sha256").write_text(manifest, encoding="utf-8")
    except Exception as error:
        _atomic_json(
            output / "execution_failed.json",
            {
                "schema_version": VERSION,
                "state": "FAILED_AFTER_T1_ACCESS_NO_RERUN_PERMITTED",
                "execution_identifier": authorization["execution_identifier"],
                "error_type": type(error).__name__,
                "error": str(error),
                "preserved_partial_evidence": partial.is_file(),
                "preserved_complete_evidence": (
                    output / "t1_prediction_evidence.jsonl.gz"
                ).is_file(),
                "t1_predictive_access_count": 1,
                "t2_predictive_access_count": 0,
                "predictive_scoring_count": 1,
                "xai_execution_count": 0,
                "t1_rerun_permitted": False,
            },
        )
        raise
    return output


def materialize_readiness(root: Path) -> Path:
    output = root / ENGINE_REL
    output.mkdir(parents=True, exist_ok=True)
    readiness = prepare_engine(root)
    _atomic_json(output / "engine_readiness.json", readiness)
    historical = output / "pre_execution_failure.json"
    if (
        not historical.is_file()
        or file_sha256(historical) != EXPECTED_HISTORICAL_FAILURE_SHA256
    ):
        raise ConfirmatoryExecutionError("historical fail-closed evidence changed")
    manifest = "".join(
        [
            f"{file_sha256(output / 'engine_readiness.json')}  engine_readiness.json\n",
            f"{file_sha256(historical)}  pre_execution_failure.json\n",
        ]
    )
    (output / "MANIFEST.sha256").write_text(manifest, encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--execute-one-shot-t1", action="store_true")
    args = parser.parse_args()
    if args.prepare == args.execute_one_shot_t1:
        raise SystemExit("choose exactly one of --prepare or --execute-one-shot-t1")
    root = args.root.resolve()
    print(materialize_readiness(root) if args.prepare else execute_one_shot(root))


if __name__ == "__main__":
    main()
