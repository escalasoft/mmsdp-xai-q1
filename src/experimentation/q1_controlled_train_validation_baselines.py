"""Controlled ApacheJIT 48F-R1 TRAIN/VALIDATION predictive baselines."""

from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    f1_score,
    matthews_corrcoef,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

VERSION = "q1-controlled-train-validation-baselines-1.0.0"
FREEZE_REL = Path("audits/q1-apachejit-final-dataset-freeze/1.0.0")
CONFIG_REL = Path(
    "configs/experiments/q1_controlled_train_validation_baselines_1.0.0.json"
)
PILOT_REL = Path("audits/q1-controlled-train-validation-baselines/1.0.0/pilot")
LABEL = "BENCHMARK_DEFINED_OBSERVED_LABEL"
CODE_FEATURES = ("la", "ld", "nf", "nd", "ns", "ent")
PROCESS_FEATURES = ("ndev", "age", "nuc", "aexp", "arexp", "asexp")
PARTITIONS = ("TRAIN", "VALIDATION", "T1", "T2")
DEVELOPMENT_PARTITIONS = frozenset(("TRAIN", "VALIDATION"))
TEST_PARTITIONS = frozenset(("T1", "T2"))
EXPECTED_PROJECTS = (
    "apache/activemq",
    "apache/camel",
    "apache/cassandra",
    "apache/flink",
    "apache/groovy",
    "apache/hadoop-hdfs",
    "apache/hadoop-mapreduce",
    "apache/hbase",
    "apache/hive",
    "apache/ignite",
    "apache/kafka",
    "apache/spark",
    "apache/zeppelin",
    "apache/zookeeper",
)
EXPECTED_COUNTS = {"rows": 94710, "positive": 28239, "negative": 66471}
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
CODE_KEYS = frozenset((*CODE_FEATURES, "row_identifier"))
PROCESS_KEYS = frozenset((*PROCESS_FEATURES, "row_identifier"))
TEXT_KEYS = {
    "raw_commit_message",
    "raw_commit_message_bytes_base64",
    "raw_commit_message_sha256",
    "row_identifier",
}
ROW_ID_PATTERN = re.compile(rb'"row_identifier":"([0-9a-f]{64})"')


class IntegrityError(RuntimeError):
    """Raised when a frozen input or experimental boundary is violated."""


def canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=True,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def digest(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _gzip_rows(path: Path) -> Iterable[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            yield json.loads(line)


def verify_manifest(base: Path) -> dict[str, str]:
    manifest = base / "MANIFEST.sha256"
    if not manifest.is_file():
        raise IntegrityError("48F-R1 MANIFEST.sha256 is missing")
    expected: dict[str, str] = {}
    pattern = re.compile(r"([0-9a-f]{64})  ([^/]+)")
    for line in manifest.read_text(encoding="utf-8").splitlines():
        match = pattern.fullmatch(line)
        if match is None or match.group(2) in expected:
            raise IntegrityError("malformed or duplicate 48F-R1 manifest entry")
        expected[match.group(2)] = match.group(1)
    present = {path.name for path in base.iterdir() if path.is_file()}
    if present - {manifest.name} != set(expected):
        raise IntegrityError("48F-R1 manifest coverage mismatch")
    for name, expected_hash in expected.items():
        if file_digest(base / name) != expected_hash:
            raise IntegrityError(f"48F-R1 payload hash mismatch: {name}")
    return expected


def _partition_membership_hash(
    rows: list[dict[str, Any]], partition: str
) -> str:
    return digest(
        [row["row_identifier"] for row in rows if row["partition"] == partition]
    )


def verify_frozen_inputs(root: Path) -> dict[str, Any]:
    """Independently verify frozen integrity without predictive scoring."""
    base = root / FREEZE_REL
    manifest = verify_manifest(base)
    eligibility = _json(base / "final_project_eligibility.json")
    projects = tuple(eligibility["candidate_projects"])
    eligible = tuple(
        item["project"]
        for item in eligibility["projects"]
        if item["final_state"] == "ELIGIBLE"
    )
    if projects != EXPECTED_PROJECTS or eligible != EXPECTED_PROJECTS:
        raise IntegrityError("eligible project set or order differs from 48F-R1")

    identities = list(_gzip_rows(base / "row_identity_provenance.jsonl.gz"))
    if len(identities) != EXPECTED_COUNTS["rows"]:
        raise IntegrityError("frozen identity row count mismatch")
    if any(set(row) != IDENTITY_KEYS for row in identities):
        raise IntegrityError("row identity schema mismatch")
    row_ids = [row["row_identifier"] for row in identities]
    if len(set(row_ids)) != len(row_ids):
        raise IntegrityError("frozen row identifiers are not unique")
    labels = Counter(bool(row[LABEL]) for row in identities)
    if labels != Counter({False: 66471, True: 28239}):
        raise IntegrityError("frozen benchmark-defined label counts mismatch")
    if {row["canonical_project_identifier"] for row in identities} != set(
        EXPECTED_PROJECTS
    ):
        raise IntegrityError("identity projects differ from eligible projects")

    memberships = list(_gzip_rows(base / "temporal_partition_manifest.jsonl.gz"))
    if len(memberships) != len(identities):
        raise IntegrityError("temporal membership row count mismatch")
    if any(set(row) != PARTITION_KEYS for row in memberships):
        raise IntegrityError("temporal membership schema mismatch")
    membership_ids = [row["row_identifier"] for row in memberships]
    if membership_ids != row_ids:
        raise IntegrityError("frozen identities and memberships differ or reorder")
    partition_counts = Counter(row["partition"] for row in memberships)
    if set(partition_counts) != set(PARTITIONS):
        raise IntegrityError("unknown or missing temporal partition")

    identity_by_id = {row["row_identifier"]: row for row in identities}
    previous: dict[str, tuple[str, str]] = {}
    previous_rank: dict[str, int] = {}
    ranks = {name: index for index, name in enumerate(PARTITIONS)}
    for row in memberships:
        identity = identity_by_id[row["row_identifier"]]
        order_key = tuple(row["order_key"])
        project = row["project"]
        if order_key != (
            identity["normalized_utc_timestamp"],
            identity["commit_sha"],
        ):
            raise IntegrityError("temporal order key differs from frozen identity")
        if project != identity["canonical_project_identifier"]:
            raise IntegrityError("membership project differs from frozen identity")
        if project in previous and order_key < previous[project]:
            raise IntegrityError("project chronology is not UTC timestamp/SHA ordered")
        if (
            project in previous_rank
            and ranks[row["partition"]] < previous_rank[project]
        ):
            raise IntegrityError("project partition chronology moves backward")
        previous[project] = order_key
        previous_rank[project] = ranks[row["partition"]]

    schemas = {
        "CODE": _json(base / "code_schema.json"),
        "PROCESS": _json(base / "process_schema.json"),
        "TEXT": _json(base / "text_schema.json"),
    }
    if tuple(schemas["CODE"]["variables"]) != CODE_FEATURES:
        raise IntegrityError("CODE schema differs from frozen contract")
    if set(schemas["PROCESS"]["variables"]) != set(PROCESS_FEATURES):
        raise IntegrityError("PROCESS schema differs from frozen contract")
    if schemas["TEXT"]["variable"] != "raw_commit_message":
        raise IntegrityError("TEXT schema differs from frozen contract")

    modality_specs = (
        ("CODE", "code_dataset.jsonl.gz", CODE_KEYS),
        ("PROCESS", "process_dataset.jsonl.gz", PROCESS_KEYS),
        ("TEXT", "text_dataset.jsonl.gz", TEXT_KEYS),
    )
    modality_hashes: dict[str, str] = {}
    for modality, filename, keys in modality_specs:
        modality_ids: list[str] = []
        for row in _gzip_rows(base / filename):
            if set(row) != set(keys):
                raise IntegrityError(f"{modality} payload schema mismatch")
            modality_ids.append(row["row_identifier"])
            if modality in {"CODE", "PROCESS"}:
                names = CODE_FEATURES if modality == "CODE" else PROCESS_FEATURES
                if any(
                    not isinstance(row[name], (int, float))
                    or isinstance(row[name], bool)
                    or not math.isfinite(float(row[name]))
                    for name in names
                ):
                    raise IntegrityError(f"{modality} contains invalid numeric value")
            else:
                raw = base64.b64decode(row["raw_commit_message_bytes_base64"])
                if hashlib.sha256(raw).hexdigest() != row["raw_commit_message_sha256"]:
                    raise IntegrityError("TEXT exact-byte digest mismatch")
        if modality_ids != row_ids:
            raise IntegrityError(f"{modality} identities differ or reorder")
        modality_hashes[modality] = manifest[filename]

    family_contract = _json(base / "project_family_grouping.json")
    family_by_project = {
        project: family
        for family, members in family_contract["families"].items()
        for project in members
        if project in EXPECTED_PROJECTS
    }
    if set(family_by_project) != set(EXPECTED_PROJECTS):
        raise IntegrityError("eligible project-family grouping is incomplete")
    for row in identities:
        project = row["canonical_project_identifier"]
        if row["family_group_identifier"] != family_by_project[project]:
            raise IntegrityError("row family identifier differs from frozen grouping")

    return {
        "status": "PASS",
        "schema_version": VERSION,
        "frozen_manifest_sha256": file_digest(base / "MANIFEST.sha256"),
        "frozen_payload_count": len(manifest),
        "frozen_payload_hashes_verified": True,
        "eligible_projects": list(projects),
        "eligible_project_count": len(projects),
        "row_count": len(identities),
        "unique_row_identifier_count": len(set(row_ids)),
        "row_identity_ordered_sha256": digest(row_ids),
        "labels": {
            "name": LABEL,
            "positive": labels[True],
            "negative": labels[False],
            "verified_ground_truth_claimed": False,
        },
        "partition_counts": dict(sorted(partition_counts.items())),
        "partition_membership_ordered_sha256": {
            partition: _partition_membership_hash(memberships, partition)
            for partition in PARTITIONS
        },
        "partition_assignment_ordered_sha256": digest(
            [[row["row_identifier"], row["partition"]] for row in memberships]
        ),
        "schemas": {
            "CODE": list(CODE_FEATURES),
            "PROCESS": list(PROCESS_FEATURES),
            "TEXT": ["raw_commit_message"],
        },
        "modality_payload_sha256": modality_hashes,
        "cross_payload_row_identity_and_order_match": True,
        "utc_timestamp_then_sha_ordering": True,
        "partition_ordering": list(PARTITIONS),
        "family_count": len(set(family_by_project.values())),
        "project_family_grouping": dict(sorted(family_by_project.items())),
        "predictive_scoring_count": 0,
        "t1_predictive_access_count": 0,
        "t2_predictive_access_count": 0,
    }


def _load_allowed_payload(
    path: Path, allowed_ids: set[str], expected_keys: set[str] | frozenset[str]
) -> dict[str, dict[str, Any]]:
    """Deserialize only pre-whitelisted development rows from a mixed payload."""
    selected: dict[str, dict[str, Any]] = {}
    with gzip.open(path, "rb") as stream:
        for line in stream:
            match = ROW_ID_PATTERN.search(line)
            if match is None:
                raise IntegrityError(f"row identifier missing in {path.name}")
            row_id = match.group(1).decode("ascii")
            if row_id not in allowed_ids:
                continue
            row = json.loads(line)
            if set(row) != set(expected_keys):
                raise IntegrityError(f"development schema mismatch in {path.name}")
            selected[row_id] = row
    if set(selected) != allowed_ids:
        raise IntegrityError(f"development rows missing in {path.name}")
    return selected


def load_development_project(root: Path, project: str) -> list[dict[str, Any]]:
    """Load one project's TRAIN/VALIDATION rows without materializing TEST rows."""
    base = root / FREEZE_REL
    memberships: list[dict[str, Any]] = []
    with gzip.open(base / "temporal_partition_manifest.jsonl.gz", "rb") as stream:
        for line in stream:
            if b'"partition":"T1"' in line or b'"partition":"T2"' in line:
                continue
            row = json.loads(line)
            if row["partition"] not in DEVELOPMENT_PARTITIONS:
                raise IntegrityError("non-development partition reached pilot loader")
            if row["project"] == project:
                memberships.append(row)
    allowed_ids = {row["row_identifier"] for row in memberships}
    if not allowed_ids:
        raise IntegrityError(f"no development rows for pilot project {project}")

    identity_rows: dict[str, dict[str, Any]] = {}
    with gzip.open(base / "row_identity_provenance.jsonl.gz", "rb") as stream:
        for line in stream:
            match = ROW_ID_PATTERN.search(line)
            if match and match.group(1).decode("ascii") in allowed_ids:
                row = json.loads(line)
                identity_rows[row["row_identifier"]] = row
    modalities = {
        "C": _load_allowed_payload(
            base / "code_dataset.jsonl.gz", allowed_ids, CODE_KEYS
        ),
        "P": _load_allowed_payload(
            base / "process_dataset.jsonl.gz", allowed_ids, PROCESS_KEYS
        ),
        "T": _load_allowed_payload(
            base / "text_dataset.jsonl.gz", allowed_ids, TEXT_KEYS
        ),
    }
    if set(identity_rows) != allowed_ids:
        raise IntegrityError("development identities are incomplete")
    membership_by_id = {row["row_identifier"]: row for row in memberships}
    rows = []
    for row_id in (row["row_identifier"] for row in memberships):
        identity = identity_rows[row_id]
        membership = membership_by_id[row_id]
        rows.append(
            {
                "row_identifier": row_id,
                "project": project,
                "timestamp": identity["normalized_utc_timestamp"],
                "commit_sha": identity["commit_sha"],
                "partition": membership["partition"],
                "forward_block": membership["forward_block"],
                "target": int(identity[LABEL]),
                "C": [float(modalities["C"][row_id][name]) for name in CODE_FEATURES],
                "P": [
                    float(modalities["P"][row_id][name]) for name in PROCESS_FEATURES
                ],
                "T": modalities["T"][row_id]["raw_commit_message"],
            }
        )
    if any(row["partition"] in TEST_PARTITIONS for row in rows):
        raise IntegrityError("TEST row materialized in pilot")
    return rows


def _numeric_pipeline() -> Pipeline:
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )


def _text_pipeline(config: dict[str, Any]) -> TfidfVectorizer:
    params = dict(config["feature_policy"]["text_vectorizer"])
    params["ngram_range"] = tuple(params["ngram_range"])
    return TfidfVectorizer(**params)


def _estimator(config: dict[str, Any], algorithm: str):
    parameters = dict(config["algorithms"][algorithm])
    if algorithm == "Logistic Regression":
        return LogisticRegression(**parameters)
    if algorithm == "Random Forest":
        return RandomForestClassifier(**parameters)
    if algorithm == "XGBoost":
        from xgboost import XGBClassifier

        return XGBClassifier(**parameters)
    if algorithm == "LightGBM":
        from lightgbm import LGBMClassifier

        return LGBMClassifier(**parameters)
    raise IntegrityError(f"unknown frozen algorithm: {algorithm}")


def _fit_modality(
    rows: list[dict[str, Any]], modality: str, config: dict[str, Any], algorithm: str
) -> tuple[Any, Any]:
    y = np.asarray([row["target"] for row in rows], dtype=int)
    if modality in {"C", "P"}:
        transformer = _numeric_pipeline()
        features = transformer.fit_transform(
            np.asarray([row[modality] for row in rows], dtype=float)
        )
    elif modality == "T":
        transformer = _text_pipeline(config)
        features = transformer.fit_transform([row["T"] for row in rows])
    else:
        raise IntegrityError(f"unknown modality: {modality}")
    model = _estimator(config, algorithm).fit(features, y)
    return transformer, model


def _score_modality(
    state: tuple[Any, Any], rows: list[dict[str, Any]], modality: str
) -> np.ndarray:
    transformer, model = state
    raw = (
        np.asarray([row[modality] for row in rows], dtype=float)
        if modality in {"C", "P"}
        else [row["T"] for row in rows]
    )
    probabilities = np.asarray(model.predict_proba(transformer.transform(raw))[:, 1])
    if probabilities.shape != (len(rows),) or not np.all(np.isfinite(probabilities)):
        raise IntegrityError("invalid probability shape or non-finite value")
    if np.any(probabilities < 0) or np.any(probabilities > 1):
        raise IntegrityError("probability outside [0, 1]")
    return probabilities


def metric_values(y: np.ndarray, probabilities: np.ndarray) -> dict[str, float]:
    if len(np.unique(y)) != 2:
        raise IntegrityError("pilot metric input does not contain both classes")
    predicted = (probabilities >= 0.5).astype(int)
    values = {
        "ROC_AUC": float(roc_auc_score(y, probabilities)),
        "PR_AUC": float(average_precision_score(y, probabilities)),
        "Precision": float(precision_score(y, predicted, zero_division=0)),
        "Recall": float(recall_score(y, predicted, zero_division=0)),
        "F1": float(f1_score(y, predicted, zero_division=0)),
        "MCC": float(matthews_corrcoef(y, predicted)),
        "Brier": float(brier_score_loss(y, probabilities)),
    }
    if any(not math.isfinite(value) for value in values.values()):
        raise IntegrityError("pilot metric is not finite")
    return values


def execute_pilot_once(
    root: Path, project: str, config: dict[str, Any]
) -> dict[str, Any]:
    rows = load_development_project(root, project)
    train = [row for row in rows if row["partition"] == "TRAIN"]
    validation = [row for row in rows if row["partition"] == "VALIDATION"]
    if not train or not validation:
        raise IntegrityError("pilot TRAIN or VALIDATION membership is empty")
    if (train[-1]["timestamp"], train[-1]["commit_sha"]) >= (
        validation[0]["timestamp"],
        validation[0]["commit_sha"],
    ):
        raise IntegrityError("pilot TRAIN does not strictly precede VALIDATION")

    algorithm = "Logistic Regression"
    y_validation = np.asarray([row["target"] for row in validation], dtype=int)
    validation_probabilities: dict[str, np.ndarray] = {}
    base_results = {}
    train_states = {}
    for modality in ("C", "P", "T"):
        state = _fit_modality(train, modality, config, algorithm)
        probabilities = _score_modality(state, validation, modality)
        train_states[modality] = state
        validation_probabilities[modality] = probabilities
        base_results[modality] = {
            "metrics": metric_values(y_validation, probabilities),
            "probability_sha256": digest(probabilities.tolist()),
            "probability_min": float(probabilities.min()),
            "probability_max": float(probabilities.max()),
        }

    by_block: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in train:
        by_block[int(row["forward_block"])].append(row)
    oof_records: list[tuple[tuple[str, str], list[float], int, int]] = []
    fold_lineage = []
    blocks = sorted(by_block)
    for block in blocks[1:]:
        fit_rows = [row for prior in blocks if prior < block for row in by_block[prior]]
        prediction_rows = by_block[block]
        if len(set(row["target"] for row in fit_rows)) != 2:
            raise IntegrityError("forward OOF fit lacks both classes")
        fold_probabilities = {}
        for modality in ("C", "P", "T"):
            fold_state = _fit_modality(fit_rows, modality, config, algorithm)
            fold_probabilities[modality] = _score_modality(
                fold_state, prediction_rows, modality
            )
        fit_ids = {row["row_identifier"] for row in fit_rows}
        prediction_ids = {row["row_identifier"] for row in prediction_rows}
        if fit_ids & prediction_ids:
            raise IntegrityError("OOF fit/prediction memberships overlap")
        if max((row["timestamp"], row["commit_sha"]) for row in fit_rows) > min(
            (row["timestamp"], row["commit_sha"]) for row in prediction_rows
        ):
            raise IntegrityError("OOF fitting is not forward temporal")
        for index, row in enumerate(prediction_rows):
            oof_records.append(
                (
                    (row["timestamp"], row["commit_sha"]),
                    [fold_probabilities[m][index] for m in ("C", "P", "T")],
                    row["target"],
                    block,
                )
            )
        fold_lineage.append(
            {
                "prediction_block": block,
                "fit_blocks": [prior for prior in blocks if prior < block],
                "fit_count": len(fit_rows),
                "prediction_count": len(prediction_rows),
                "fit_membership_sha256": digest(
                    [row["row_identifier"] for row in fit_rows]
                ),
                "prediction_membership_sha256": digest(
                    [row["row_identifier"] for row in prediction_rows]
                ),
                "fit_prediction_disjoint": True,
                "strict_forward_time": True,
            }
        )
    oof_records.sort(key=lambda item: item[0])
    oof_x = np.asarray([item[1] for item in oof_records], dtype=float)
    oof_y = np.asarray([item[2] for item in oof_records], dtype=int)
    meta_model = LogisticRegression(
        **config["fusion"]["meta_learner_parameters"]
    ).fit(oof_x, oof_y)
    validation_meta_x = np.column_stack(
        [validation_probabilities[m] for m in ("C", "P", "T")]
    )
    fusion_probabilities = np.asarray(
        meta_model.predict_proba(validation_meta_x)[:, 1]
    )
    if np.any(fusion_probabilities < 0) or np.any(fusion_probabilities > 1):
        raise IntegrityError("fusion probability outside [0, 1]")
    fusion = {
        "metrics": metric_values(y_validation, fusion_probabilities),
        "probability_sha256": digest(fusion_probabilities.tolist()),
        "probability_min": float(fusion_probabilities.min()),
        "probability_max": float(fusion_probabilities.max()),
        "strategy": "STACKING_LATE_FUSION",
        "meta_training_source": "STRICT_FORWARD_OUT_OF_FOLD_TRAIN",
        "meta_training_count": len(oof_records),
        "meta_training_membership_sha256": digest(
            [
                [item[0][0], item[0][1], item[3]]
                for item in oof_records
            ]
        ),
        "folds": fold_lineage,
    }
    return {
        "pilot_project": project,
        "project_selection_rule": config["pilot_project_rule"],
        "algorithm": algorithm,
        "train_count": len(train),
        "validation_count": len(validation),
        "train_membership_sha256": digest(
            [row["row_identifier"] for row in train]
        ),
        "validation_membership_sha256": digest(
            [row["row_identifier"] for row in validation]
        ),
        "base_results": base_results,
        "fusion_C+P+T": fusion,
        "predictive_partitions_materialized": ["TRAIN", "VALIDATION"],
        "t1_predictive_access_count": 0,
        "t2_predictive_access_count": 0,
        "final_test_metric_count": 0,
    }


def _scientific_digest(payload: dict[str, Any]) -> str:
    return digest(payload)


def execute_pilot(root: Path) -> dict[str, Any]:
    config = _json(root / CONFIG_REL)
    if config["experiment_version"] != VERSION:
        raise IntegrityError("controlled baseline configuration version mismatch")
    if config["predictive_partitions"] != ["TRAIN", "VALIDATION"]:
        raise IntegrityError("predictive partition boundary mismatch")
    if config["test_partitions"] != {"T1": "DENY", "T2": "DENY"}:
        raise IntegrityError("TEST access boundary mismatch")
    project = min(EXPECTED_PROJECTS)
    first = execute_pilot_once(root, project, config)
    second = execute_pilot_once(root, project, config)
    first_digest = _scientific_digest(first)
    second_digest = _scientific_digest(second)
    if first_digest != second_digest:
        raise IntegrityError("deterministic pilot reproducibility failure")
    return {
        "status": "PASS",
        "schema_version": VERSION,
        "pilot": first,
        "repeat_run_scientific_sha256": [first_digest, second_digest],
        "reproducibility": first_digest == second_digest,
        "performance_used_for_project_selection": False,
        "scientific_hypothesis_modified": False,
        "projects_dropped": [],
        "algorithms_dropped": [],
        "pilot_metrics_are_engineering_evidence_only": True,
    }


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))


def _write_manifest(output: Path) -> None:
    entries = [
        f"{file_digest(path)}  {path.name}"
        for path in sorted(output.iterdir())
        if path.is_file() and path.name != "MANIFEST.sha256"
    ]
    (output / "MANIFEST.sha256").write_text(
        "\n".join(entries) + "\n", encoding="utf-8"
    )


def write_pilot_artifacts(
    root: Path, integrity: dict[str, Any], pilot: dict[str, Any]
) -> Path:
    output = root / PILOT_REL
    output.mkdir(parents=True, exist_ok=True)
    _write_json(output / "input_integrity.json", integrity)
    _write_json(output / "pilot_report.json", pilot)
    _write_json(
        output / "pilot_corrections.json",
        {
            "schema_version": VERSION,
            "correction_count": 1,
            "corrections": [
                {
                    "stage": "PRE_PILOT_FAIL_CLOSED_INPUT_VERIFICATION",
                    "severity": "CATASTROPHIC_RUN_BLOCKER",
                    "symptom": (
                        "The verifier treated the PROCESS schema mapping's JSON key "
                        "order as a scientific feature-order contract."
                    ),
                    "correction": (
                        "Verify exact PROCESS variable-set equality while retaining "
                        "the predeclared modeling order from the frozen 48F-R1 "
                        "PROCESS_VARIABLES contract."
                    ),
                    "scientific_contract_changed": False,
                    "predictive_performance_consulted": False,
                    "t1_t2_accessed": False,
                }
            ],
            "statement": (
                "One fail-closed catastrophic run blocker was corrected before the "
                "successful pilot; no predictive outcome informed the correction."
            ),
        },
    )
    implementation = root / (
        "src/experimentation/q1_controlled_train_validation_baselines.py"
    )
    config = root / CONFIG_REL
    _write_json(
        output / "implementation_freeze.json",
        {
            "schema_version": VERSION,
            "status": "FROZEN_AFTER_PILOT_PASS",
            "implementation_path": str(implementation.relative_to(root)),
            "implementation_sha256": file_digest(implementation),
            "configuration_path": str(config.relative_to(root)),
            "configuration_sha256": file_digest(config),
            "pilot_scientific_sha256": pilot["repeat_run_scientific_sha256"][0],
            "allowed_future_change_policy": (
                "Any implementation change must fail closed and be recorded as a "
                "separately justified catastrophic correction before campaign "
                "execution."
            ),
        },
    )
    _write_json(
        output / "execution_ledger.json",
        {
            "schema_version": VERSION,
            "input_integrity_verifications": 1,
            "pilot_repetitions": 2,
            "pilot_project_count": 1,
            "pilot_base_model_fits_per_repetition": 27,
            "pilot_meta_model_fits_per_repetition": 1,
            "validation_scoring_conditions_per_repetition": 4,
            "t1_predictive_access_count": 0,
            "t2_predictive_access_count": 0,
            "final_test_metric_count": 0,
            "full_factorial_conditions_executed": 0,
        },
    )
    report = "\n".join(
        (
            "# Controlled TRAIN/VALIDATION Baselines — Input Integrity and Pilot",
            "",
            "The ApacheJIT 48F-R1 manifest and every listed payload hash passed. "
            "Exactly 14 frozen eligible projects, 94,710 unique ordered row "
            "identities, 28,239 benchmark-defined positive observations, 66,471 "
            "benchmark-defined negative observations, four temporal memberships, "
            "the CODE/PROCESS/TEXT schemas, strict UTC timestamp/SHA chronology, "
            "and 13 eligible family groups reconciled.",
            "",
            "The deterministic engineering pilot selected `apache/activemq`, the "
            "lexicographically first eligible project. CODE, PROCESS, and TEXT "
            "Logistic Regression pipelines and C+P+T stacking late fusion completed "
            "on TRAIN/VALIDATION only. Numeric imputation/scaling and TEXT TF-IDF "
            "were fitted on the applicable TRAIN prefix. The meta-learner used only "
            "strict-forward out-of-fold TRAIN probabilities. All probabilities were "
            "finite and in [0,1], all declared metrics computed, and two complete "
            "executions produced the same scientific digest.",
            "",
            "T1 predictive accesses: **0**. T2 predictive accesses: **0**. Final "
            "TEST metrics: **0**. The pilot did not select projects, alter "
            "hypotheses, or drop algorithms. One fail-closed PROCESS schema "
            "representation blocker was corrected without consulting performance; "
            "it is recorded separately in `pilot_corrections.json`. The final "
            "implementation and configuration hashes are frozen in "
            "`implementation_freeze.json`.",
            "",
        )
    )
    (output / "REPORT.md").write_text(report, encoding="utf-8")
    _write_manifest(output)
    return output


def run(root: Path) -> Path:
    integrity = verify_frozen_inputs(root)
    pilot = execute_pilot(root)
    return write_pilot_artifacts(root, integrity, pilot)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    print(run(args.root.resolve()))


if __name__ == "__main__":
    main()
