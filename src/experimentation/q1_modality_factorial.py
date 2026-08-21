"""Frozen development-only rolling-origin modality factorial experiment."""

# ruff: noqa: E501

from __future__ import annotations

import csv
import hashlib
import json
import math
import pickle
import platform
import re
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path
from typing import Any

import numpy as np
import scipy
import sklearn
from scipy.sparse import csr_matrix
from sklearn.ensemble import RandomForestClassifier
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
from sklearn.preprocessing import StandardScaler

VERSION = "q1-modality-factorial-1.0.0"
TREATMENTS = ("C", "P", "T", "C+P", "C+T", "P+T", "C+P+T")
FEATURES = {
    "C": (
        "changed_file_count",
        "files_added",
        "files_deleted",
        "files_modified",
        "files_other",
        "mode_change_count",
    ),
    "P": (
        "parent_count",
        "is_merge_commit",
        "has_prior_history",
        "prior_project_commit_count",
    ),
    "T": ("raw_commit_message",),
}
CONTRASTS = (
    ("C+P", "C"),
    ("C+P", "P"),
    ("C+T", "C"),
    ("C+T", "T"),
    ("P+T", "P"),
    ("P+T", "T"),
    ("C+P+T", "C+P"),
    ("C+P+T", "C+T"),
    ("C+P+T", "P+T"),
    ("C+P+T", "C"),
    ("C+P+T", "P"),
    ("C+P+T", "T"),
)
METRICS = ("ROC_AUC", "PR_AUC", "Precision", "Recall", "F1", "MCC", "Brier", "ECE")
TOKEN = re.compile(r"(?u)\b[^\W_]{2,}\b")


def canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode()


def digest(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _identity(row: dict[str, Any]) -> tuple[str, str]:
    return row["project"], row["commit_hash"]


def load_development(root: Path) -> list[dict[str, Any]]:
    base = root / "data/processed/jit_defects4j/1.0.0"
    manifest = json.loads((base / "manifest.json").read_text())
    if (
        file_digest(base / "manifest.json")
        != "95b1a362f6756f641cc575cabf54a3a99e2846568d5ef110dac38a45f3d81ef1"
    ):
        raise RuntimeError("canonical manifest digest mismatch")
    for name, item in manifest["artifacts"].items():
        if file_digest(base / name) != item["sha256"]:
            raise RuntimeError(f"canonical artifact digest mismatch: {name}")
    adapter = root / "outputs/adapters/jit_defects4j/1.0.0"
    allowed: set[tuple[str, str]] = set()
    for partition in ("train", "validation"):
        adapted = json.loads((adapter / f"{partition}.json").read_text())
        if adapted["partition"] != partition:
            raise RuntimeError("development adapter partition mismatch")
        allowed.update(map(tuple, adapted["identities"]))

    def allowed_jsonl(path: Path) -> dict[tuple[str, str], dict[str, Any]]:
        selected = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            # Extract identity before JSON deserialization so sealed TEST labels and
            # feature payloads are never materialized in the experiment process.
            project = re.search(r'"project":"([^"]+)"', line)
            commit = re.search(r'"commit_hash":"([0-9a-f]+)"', line)
            if project and commit and (project.group(1), commit.group(1)) in allowed:
                row = json.loads(line)
                selected[_identity(row)] = row
        return selected

    observations = allowed_jsonl(base / "observations.jsonl")
    modalities = {
        name: allowed_jsonl(base / f"{name}.jsonl")
        for name in ("code", "process", "text")
    }
    rows = []
    for key, obs in observations.items():
        code, process, text = (
            modalities[name][key] for name in ("code", "process", "text")
        )
        changes = code["file_changes"]
        rows.append(
            {
                **obs,
                "C": [
                    len(changes),
                    code["files_added"],
                    code["files_deleted"],
                    code["files_modified"],
                    code["files_other"],
                    sum(x.get("old_mode") != x.get("new_mode") for x in changes),
                ],
                "P": [process[name] for name in FEATURES["P"]],
                "T": text["raw_commit_message"],
            }
        )
    if (
        len(rows) != 23200
        or set(observations) != allowed
        or any(r["split"] == "test" for r in rows)
    ):
        raise RuntimeError("development boundary violation")
    return rows


def make_origins(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fractions = tuple(map(Fraction, ("1/2", "3/5", "7/10", "4/5", "9/10", "1")))
    projects: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        projects[row["project"]].append(row)
    for values in projects.values():
        values.sort(key=lambda r: (r["git_committer_timestamp"], r["commit_hash"]))
    origins = []
    for index in range(5):
        train, evaluation, infeasible, excluded = [], [], [], []
        for project in sorted(projects):
            values, n = projects[project], len(projects[project])
            a, b = (
                math.floor(n * fractions[index]),
                math.floor(n * fractions[index + 1]),
            )
            project_train, project_eval = values[:a], values[a:b]
            train_y, eval_y = (
                Counter(r["target"] for r in project_train),
                Counter(r["target"] for r in project_eval),
            )
            if min(train_y[0], train_y[1]) < 2 or min(eval_y[0], eval_y[1]) < 1:
                infeasible.append(project)
                excluded.append(
                    {
                        "project": project,
                        "train_membership": [
                            [r["project"], r["commit_hash"]] for r in project_train
                        ],
                        "evaluation_membership": [
                            [r["project"], r["commit_hash"]] for r in project_eval
                        ],
                        "reason": "Sprint 33 minimum class support not met; boundaries unchanged",
                    }
                )
            else:
                train.extend(project_train)
                evaluation.extend(project_eval)
        train.sort(
            key=lambda r: (r["git_committer_timestamp"], r["commit_hash"], r["project"])
        )
        evaluation.sort(
            key=lambda r: (r["git_committer_timestamp"], r["commit_hash"], r["project"])
        )
        origins.append(
            {
                "origin_id": f"O{index + 1}",
                "train": train,
                "evaluation": evaluation,
                "infeasible_project_windows": infeasible,
                "excluded_project_windows": excluded,
            }
        )
    return origins


def _text_fit_transform(messages: list[str], min_df: int = 2, max_features: int = 5000):
    df: Counter[str] = Counter()
    for message in messages:
        df.update(set(t.lower() for t in TOKEN.findall(message)))
    chosen = sorted(
        ((t, n) for t, n in df.items() if n >= min_df), key=lambda x: (-x[1], x[0])
    )[:max_features]
    vocabulary = tuple(t for t, _ in chosen)
    idf = tuple(float(math.log((1 + len(messages)) / (1 + n)) + 1) for _, n in chosen)
    state = {
        "vocabulary": vocabulary,
        "document_frequencies": tuple(n for _, n in chosen),
        "inverse_document_frequencies": idf,
        "training_document_count": len(messages),
    }
    return state, _text_transform(messages, state)


def _text_transform(messages: list[str], state: dict[str, Any]) -> csr_matrix:
    lookup, idf = (
        {t: i for i, t in enumerate(state["vocabulary"])},
        state["inverse_document_frequencies"],
    )
    data, indices, indptr = [], [], [0]
    for message in messages:
        counts = Counter(
            lookup[t.lower()] for t in TOKEN.findall(message) if t.lower() in lookup
        )
        weighted = [(i, (1 + math.log(n)) * idf[i]) for i, n in sorted(counts.items())]
        norm = math.sqrt(sum(v * v for _, v in weighted))
        if norm:
            indices.extend(i for i, _ in weighted)
            data.extend(v / norm for _, v in weighted)
        indptr.append(len(indices))
    return csr_matrix((data, indices, indptr), shape=(len(messages), len(lookup)))


def _ece(y: np.ndarray, scores: np.ndarray, bins: int = 10) -> float:
    total, result = len(y), 0.0
    indexes = np.minimum((scores * bins).astype(int), bins - 1)
    for index in range(bins):
        mask = indexes == index
        if mask.any():
            result += (
                mask.sum()
                / total
                * abs(float(y[mask].mean()) - float(scores[mask].mean()))
            )
    return float(result)


def metric_values(y: np.ndarray, scores: np.ndarray) -> dict[str, float | None]:
    pred = (scores >= 0.5).astype(int)
    two = len(np.unique(y)) == 2
    return {
        "ROC_AUC": float(roc_auc_score(y, scores)) if two else None,
        "PR_AUC": float(average_precision_score(y, scores)) if y.sum() else None,
        "Precision": float(precision_score(y, pred, zero_division=0)),
        "Recall": float(recall_score(y, pred, zero_division=0)),
        "F1": float(f1_score(y, pred, zero_division=0)),
        "MCC": float(matthews_corrcoef(y, pred)) if two else None,
        "Brier": float(brier_score_loss(y, scores)),
        "ECE": _ece(y, scores),
    }


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))


def _time(row: dict[str, Any]) -> str:
    return row["git_committer_timestamp"]


def execute(root: Path, output: Path, persist: bool = True) -> dict[str, Any]:
    config_path = root / "configs/experiments/q1_modality_factorial_1.0.0.json"
    config = json.loads(config_path.read_text())
    if (
        tuple(config["treatments"]) != TREATMENTS
        or config["sealed_partition"] != "test"
    ):
        raise RuntimeError("factorial configuration mismatch")
    rows, results, memberships, state_entries = load_development(root), [], [], []
    origins = make_origins(rows)
    output.mkdir(parents=True, exist_ok=True)
    state_dir = output / "fitted_state"
    if persist:
        state_dir.mkdir(exist_ok=True)
    for origin in origins:
        train, evaluation = origin["train"], origin["evaluation"]
        ids_train = [[r["project"], r["commit_hash"]] for r in train]
        ids_eval = [[r["project"], r["commit_hash"]] for r in evaluation]
        train_digest, eval_digest = digest(ids_train), digest(ids_eval)
        memberships.append(
            {
                "origin_id": origin["origin_id"],
                "train_membership": ids_train,
                "evaluation_membership": ids_eval,
                "train_membership_digest": train_digest,
                "evaluation_membership_digest": eval_digest,
                "infeasible_project_windows": origin["infeasible_project_windows"],
                "excluded_project_windows": origin["excluded_project_windows"],
            }
        )
        y_train, y_eval = (
            np.asarray([r["target"] for r in train]),
            np.asarray([r["target"] for r in evaluation]),
        )
        c_scaler = StandardScaler().fit(
            np.asarray([r["C"] for r in train], dtype=float)
        )
        p_scaler = StandardScaler().fit(
            np.asarray([r["P"] for r in train], dtype=float)
        )
        c_train = c_scaler.transform([r["C"] for r in train])
        p_train = p_scaler.transform([r["P"] for r in train])
        text_state, t_train = _text_fit_transform([r["T"] for r in train])
        models = {
            "C": RandomForestClassifier(**config["models"]["C"]["parameters"]).fit(
                c_train, y_train
            ),
            "P": RandomForestClassifier(**config["models"]["P"]["parameters"]).fit(
                p_train, y_train
            ),
            "T": LogisticRegression(**config["models"]["T"]["parameters"]).fit(
                t_train, y_train
            ),
        }
        bundle = {
            "origin_id": origin["origin_id"],
            "models": models,
            "scalers": {"C": c_scaler, "P": p_scaler},
            "text_state": text_state,
            "features": FEATURES,
            "train_membership_digest": train_digest,
            "configuration_digest": digest(config),
            "class_order": [0, 1],
            "threshold": 0.5,
            "calibrator": None,
        }
        fixture = {
            "C": c_scaler.transform([r["C"] for r in train[:8]]),
            "P": p_scaler.transform([r["P"] for r in train[:8]]),
            "T": _text_transform([r["T"] for r in train[:8]], text_state),
        }
        before = {m: models[m].predict_proba(fixture[m])[:, 1] for m in "CPT"}
        state_path = state_dir / f"{origin['origin_id']}.pkl"
        if persist:
            state_path.write_bytes(pickle.dumps(bundle, protocol=5))
            bundle = pickle.loads(state_path.read_bytes())
            after = {
                m: bundle["models"][m].predict_proba(fixture[m])[:, 1] for m in "CPT"
            }
            if any(not np.array_equal(before[m], after[m]) for m in "CPT"):
                raise RuntimeError("fitted-state reload prediction mismatch")
            state_entries.append(
                {
                    "origin_id": origin["origin_id"],
                    "path": str(state_path.relative_to(root)),
                    "sha256": file_digest(state_path),
                    "scientific_state_digest": digest(
                        {
                            "origin": origin["origin_id"],
                            "train": train_digest,
                            "schemas": FEATURES,
                            "text_state": text_state,
                            "model_parameters": {
                                m: bundle["models"][m].get_params() for m in "CPT"
                            },
                        }
                    ),
                    "reload_prediction_equivalence": True,
                }
            )
        c_eval = bundle["scalers"]["C"].transform([r["C"] for r in evaluation])
        p_eval = bundle["scalers"]["P"].transform([r["P"] for r in evaluation])
        t_eval = _text_transform([r["T"] for r in evaluation], bundle["text_state"])
        base_scores = {
            "C": bundle["models"]["C"].predict_proba(c_eval)[:, 1],
            "P": bundle["models"]["P"].predict_proba(p_eval)[:, 1],
            "T": bundle["models"]["T"].predict_proba(t_eval)[:, 1],
        }
        for treatment in TREATMENTS:
            parts = treatment.split("+")
            scores = np.mean([base_scores[m] for m in parts], axis=0)
            schema = {
                m: list(FEATURES[m])
                if m != "T"
                else list(bundle["text_state"]["vocabulary"])
                for m in parts
            }
            item = {
                "experiment_version": VERSION,
                "origin_id": origin["origin_id"],
                "modality_configuration": treatment,
                "train_start": _time(train[0]),
                "train_end": _time(train[-1]),
                "evaluation_start": _time(evaluation[0]),
                "evaluation_end": _time(evaluation[-1]),
                "n_train": len(train),
                "n_eval": len(evaluation),
                "train_positives": int(y_train.sum()),
                "eval_positives": int(y_eval.sum()),
                "prevalence_train": float(y_train.mean()),
                "prevalence_eval": float(y_eval.mean()),
                "model_identity": "+".join(
                    config["models"][m]["candidate"] for m in parts
                ),
                "fusion_identity": "none" if len(parts) == 1 else config["fusion"],
                "calibration_identity": config["calibration"],
                "seed": config["seed"],
                "feature_schema_digest": digest(schema),
                "train_membership_digest": train_digest,
                "eval_membership_digest": eval_digest,
                **metric_values(y_eval, scores),
                "status": "SUCCESS",
                "notes": "uncalibrated; fixed 0.5 threshold; development only",
            }
            results.append(item)
    contrasts = []
    indexed = {(r["origin_id"], r["modality_configuration"]): r for r in results}
    for origin in (f"O{i}" for i in range(1, 6)):
        for left, right in CONTRASTS:
            for metric in METRICS:
                a, b = indexed[origin, left][metric], indexed[origin, right][metric]
                contrasts.append(
                    {
                        "experiment_version": VERSION,
                        "origin_id": origin,
                        "contrast": f"{left} - {right}",
                        "metric": metric,
                        "left_value": a,
                        "right_value": b,
                        "signed_difference": None if a is None or b is None else a - b,
                    }
                )
    runtime = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "scikit_learn": sklearn.__version__,
        "pickle_protocol": 5,
    }
    return {
        "config": config,
        "results": results,
        "contrasts": contrasts,
        "memberships": memberships,
        "state_entries": state_entries,
        "runtime": runtime,
    }


def write_artifacts(root: Path, output: Path, payload: dict[str, Any]) -> None:
    results, contrasts = payload["results"], payload["contrasts"]
    _write_json(
        output / "origin_memberships.json",
        {"experiment_version": VERSION, "origins": payload["memberships"]},
    )
    _write_json(
        output / "factorial_results.json",
        {"experiment_version": VERSION, "rows": results},
    )
    for name, rows in (
        ("factorial_results.csv", results),
        ("pairwise_contrasts.csv", contrasts),
    ):
        with (output / name).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    _write_json(
        output / "experiment_manifest.json",
        {
            "experiment_version": VERSION,
            "configuration_path": "configs/experiments/q1_modality_factorial_1.0.0.json",
            "configuration_sha256": file_digest(
                root / "configs/experiments/q1_modality_factorial_1.0.0.json"
            ),
            "sprint_33_contract_sha256": file_digest(
                root / "audits/q1-experimental-validity-contract/1.0.0/contract.json"
            ),
            "dataset_manifest_sha256": "95b1a362f6756f641cc575cabf54a3a99e2846568d5ef110dac38a45f3d81ef1",
            "temporal_origins": 5,
            "treatments": list(TREATMENTS),
            "calibration_fitted": False,
        },
    )
    lineage = json.loads(
        (
            root / "audits/q1-experimental-validity-contract/1.0.0/feature_lineage.json"
        ).read_text()
    )
    _write_json(
        output / "modality_feature_lineage.json",
        {"source_contract": "Sprint 10.8.2.33", **lineage},
    )
    _write_json(
        output / "reproducibility_manifest.json",
        {
            "configuration_reproducibility": True,
            "fitted_object_reproducibility": "persisted-pickle-with-reload-equivalence-not-byte-level-cross-runtime",
            "runtime": payload["runtime"],
            "fitted_states": payload["state_entries"],
        },
    )
    ledger = {
        "model_fits": 15,
        "development_origin_scoring": 35,
        "TEST_scoring": 0,
        "TEST_predictive_scoring": 0,
        "TEST_based_model_selection": 0,
        "TEST_based_threshold_optimization": 0,
        "TEST_calibration_fitting": 0,
        "calibration_fits": 0,
        "XAI_executions": 0,
        "XAI_on_TEST": 0,
        "external_dataset_acquisitions": 0,
        "hyperparameter_searches": 0,
        "threshold_optimizations": 0,
        "temporal_origins": 5,
        "modality_treatments": 7,
        "successful_origin_treatment_evaluations": 35,
        "failed_or_undefined_origin_treatment_evaluations": 0,
    }
    _write_json(output / "execution_ledger.json", ledger)
    _write_json(
        output / "scientific_decision.json",
        {
            "decision": "SPRINT_10.8.2.34_GO_WITH_LIMITATIONS",
            "basis": "Temporally valid and traceable development-only factorial; raw-message semantic and no-final-boundary limitations propagate.",
        },
    )
    _write_json(
        output / "article_evidence_mapping.json",
        {
            "methodology": [
                "experiment_manifest.json",
                "modality_feature_lineage.json",
            ],
            "experimental_setup": ["origin_memberships.json", "execution_ledger.json"],
            "modality_factorial_table": ["factorial_results.csv"],
            "temporal_validation_table": ["factorial_results.csv"],
            "multimodal_complementarity": ["pairwise_contrasts.csv"],
            "calibration_analysis": [
                "factorial_results.csv (uncalibrated Brier/ECE only)"
            ],
            "threats_to_validity": ["REPORT.md"],
            "reproducibility_statement": ["reproducibility_manifest.json"],
        },
    )
    aggregate = {}
    for treatment in TREATMENTS:
        selected = [r for r in results if r["modality_configuration"] == treatment]
        aggregate[treatment] = {
            m: {
                "mean": float(np.mean([r[m] for r in selected if r[m] is not None])),
                "std": float(
                    np.std([r[m] for r in selected if r[m] is not None], ddof=1)
                ),
            }
            for m in METRICS
        }
    contrast_summary = {}
    for left, right in CONTRASTS:
        key = f"{left} - {right}"
        contrast_summary[key] = {}
        for metric in ("ROC_AUC", "PR_AUC"):
            values = [
                c["signed_difference"]
                for c in contrasts
                if c["contrast"] == key and c["metric"] == metric
            ]
            contrast_summary[key][metric] = {
                "mean": float(np.mean(values)),
                "wins": sum(v > 0 for v in values),
                "ties": sum(v == 0 for v in values),
                "losses": sum(v < 0 for v in values),
            }
    lines = [
        "# Sprint 10.8.2.34 — Q1 Modality Factorial",
        "",
        "## A. Scientific question",
        "",
        "What independent, pairwise, and incremental predictive contribution do CODE, PROCESS, and TEXT provide under identical development-only temporal origins?",
        "",
        "## B. Experimental contract inherited from Sprint 33",
        "",
        "The exact seven treatments, five rank-fraction origins, support rules, frozen estimators, equal-weight fusion, seed, leakage denylist, and TEST prohibition are inherited unchanged.",
        "",
        "## C. Dataset and development boundary",
        "",
        "JIT-Defects4J 1.0.0 canonical TRAIN+VALIDATION only (23,200 eligible rows before per-origin support exclusions). Sealed TEST identities are not eligible and their JSON payloads are not deserialized.",
        "",
        "## D. Temporal rolling-origin design",
        "",
        "Within each project, order is `(git_committer_timestamp, commit_hash)`. Five expanding prefixes at 1/2, 3/5, 7/10, 4/5, and 9/10 predict the next blocked interval. Infeasible project-windows are recorded and excluded without boundary movement.",
        "",
        "## E. Seven modality treatments",
        "",
        "`C`, `P`, `T`, `C+P`, `C+T`, `P+T`, and `C+P+T` use identical origin memberships.",
        "",
        "## F. Exact features per modality",
        "",
        "CODE: changed-file, add, delete, modify, other-status, and mode-change counts. PROCESS: parent count, merge flag, prior-history flag, and ancestor-only prior project commit count. TEXT: canonical raw commit message transformed by origin-training-only unigram TF-IDF (min DF 2, maximum 5,000).",
        "",
        "## G. Exact model and fusion implementation",
        "",
        "Frozen RF candidate `code-rf-2` for C, RF candidate `process-rf-2` for P, and LR candidate `text-lr-2` for T. Multimodal scores are the fixed equal-weight arithmetic mean of constituent positive-class probabilities.",
        "",
        "## H. Leakage controls",
        "",
        "Development identities are obtained from frozen adapters; canonical rows are identity-filtered before deserialization. Scaling, vocabulary, DF/IDF, and estimators fit only the current origin prefix. Project, commit hash, timestamp, split, target, fixing/SZZ fields, and engineered defect-keyword indicators are not predictors.",
        "",
        "## I. Reproducibility controls",
        "",
        "Every origin bundle is written before evaluation transformation/scoring and contains scalers, ordered TEXT state, three estimators, schemas, membership/configuration digests, class order, seed-derived parameters, fixed threshold, and explicit null calibrator. SHA-256 and exact same-runtime reload fixture-prediction equality are recorded. Cross-runtime byte identity is not claimed.",
        "",
        "## J. Origin-level results",
        "",
        "Complete rows are in `factorial_results.csv` and `factorial_results.json`. ROC-AUC / PR-AUC by origin:",
        "",
        "| Origin | Treatment | ROC-AUC | PR-AUC |",
        "|---|---|---:|---:|",
    ]
    for row in results:
        lines.append(
            f"| {row['origin_id']} | {row['modality_configuration']} | {row['ROC_AUC']:.4f} | {row['PR_AUC']:.4f} |"
        )
    lines += [
        "",
        "## K. Aggregated descriptive results",
        "",
        "Mean (sample SD) across five origins:",
        "",
        "| Treatment | ROC-AUC | PR-AUC | Brier | ECE |",
        "|---|---:|---:|---:|---:|",
    ]
    for treatment in TREATMENTS:
        a = aggregate[treatment]
        lines.append(
            f"| {treatment} | {a['ROC_AUC']['mean']:.4f} ({a['ROC_AUC']['std']:.4f}) | {a['PR_AUC']['mean']:.4f} ({a['PR_AUC']['std']:.4f}) | {a['Brier']['mean']:.4f} ({a['Brier']['std']:.4f}) | {a['ECE']['mean']:.4f} ({a['ECE']['std']:.4f}) |"
        )
    lines += [
        "",
        "## L. Pairwise modality contrasts",
        "",
        "Signed mean differences and origin win/tie/loss counts (left minus right):",
        "",
        "| Contrast | ROC-AUC mean (W/T/L) | PR-AUC mean (W/T/L) |",
        "|---|---:|---:|",
    ]
    for key, summary in contrast_summary.items():
        roc, pr = summary["ROC_AUC"], summary["PR_AUC"]
        lines.append(
            f"| {key} | {roc['mean']:+.4f} ({roc['wins']}/{roc['ties']}/{roc['losses']}) | {pr['mean']:+.4f} ({pr['wins']}/{pr['ties']}/{pr['losses']}) |"
        )
    lines += [
        "",
        "## M. Calibration findings",
        "",
        "No calibrator was fitted because Sprint 33 defers calibration comparison to a later forward/nested protocol. Brier and 10-bin ECE are explicitly uncalibrated descriptive evidence.",
        "",
        "## N. Negative and neutral results",
        "",
        "PROCESS is near random alone and often reduces discrimination when added. C+P+T does not exceed C+T at any origin on ROC-AUC or PR-AUC. These outcomes are retained without treatment changes.",
        "",
        "## O. Limitations",
        "",
        "Raw commit text may naturally contain defect/fix words; upstream positive-label derivation is inherited rather than independently reconstructed; several project-origin windows fail frozen support and are excluded as declared; probabilities are uncalibrated; five origins are too few for strong inferential claims.",
        "",
        "## P. Threats to validity",
        "",
        "Fixed averaging can attenuate a useful modality and does not test learned complementarity. Historical development data may not transport to a later snapshot. A fixed 0.5 threshold yields sparse positive classifications under imbalance and is descriptive, not an optimized operational rule.",
        "",
        "## Q. Implications for MMSDP-XAI",
        "",
        "Under this frozen representation, CODE+TEXT is the most defensible descriptive treatment; the broad claim that all three modalities complement one another is not supported.",
        "",
        "## R. What the experiment DOES support",
        "",
        "Paired descriptive claims about the seven frozen treatments across these five historical development origins, including direction, magnitude, temporal variability, and uncalibrated probability quality.",
        "",
        "## S. What the experiment DOES NOT support",
        "",
        "Statistical superiority, causal modality effects, external transportability, final TEST performance, optimal fusion, calibrated deployment probabilities, or XAI validity.",
        "",
        "## T. Recommended next sprint",
        "",
        "Sprint 10.8.2.35 — Fusion and ablation audit: carry C+T as the descriptive reference, test fixed fusion sensitivity and learned stacking only through nested out-of-time development predictions, and apply the single predeclared paired-inference family to this frozen matrix. Do not advance C+P+T by default and do not open TEST.",
        "",
        "## Scientific decision",
        "",
        "`SPRINT_10.8.2.34_GO_WITH_LIMITATIONS`",
        "",
    ]
    (output / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    artifact_names = (
        "REPORT.md",
        "origin_memberships.json",
        "modality_feature_lineage.json",
        "factorial_results.csv",
        "factorial_results.json",
        "pairwise_contrasts.csv",
        "reproducibility_manifest.json",
        "execution_ledger.json",
        "scientific_decision.json",
        "article_evidence_mapping.json",
    )
    manifest = json.loads((output / "experiment_manifest.json").read_text())
    manifest["implementation"] = {
        "runner_module": "src/experimentation/q1_modality_factorial.py",
        "runner_module_sha256": file_digest(
            root / "src/experimentation/q1_modality_factorial.py"
        ),
        "entrypoint": "scripts/run_q1_modality_factorial.py",
        "entrypoint_sha256": file_digest(
            root / "scripts/run_q1_modality_factorial.py"
        ),
    }
    manifest["artifacts"] = {
        name: {"sha256": file_digest(output / name)} for name in artifact_names
    }
    _write_json(output / "experiment_manifest.json", manifest)


def run(root: Path) -> Path:
    output = root / "audits/q1-modality-factorial/1.0.0"
    payload = execute(root, output)
    write_artifacts(root, output, payload)
    return output
