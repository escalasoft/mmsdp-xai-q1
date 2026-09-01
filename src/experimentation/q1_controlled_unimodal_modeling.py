"""Campaign-grade unimodal modeling contract for ApacheJIT 48F-R1."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import platform
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from experimentation.q1_controlled_train_validation_baselines import (
    CODE_FEATURES,
    EXPECTED_PROJECTS,
    PROCESS_FEATURES,
    canonical_bytes,
    digest,
    file_digest,
    load_development_project,
)

VERSION = "q1-controlled-unimodal-modeling-1.0.0"
CONFIG_REL = Path("configs/experiments/q1_controlled_unimodal_modeling_1.0.0.json")
OUTPUT_REL = Path(
    "audits/q1-controlled-train-validation-baselines/1.0.0/unimodal_contract"
)
ALGORITHMS = (
    "Logistic Regression",
    "Random Forest",
    "XGBoost",
    "LightGBM",
)
MODALITIES = ("C", "P", "T")


class UnimodalContractError(RuntimeError):
    """Raised when a frozen unimodal modeling rule is violated."""


def load_config(root: Path) -> dict[str, Any]:
    config = json.loads((root / CONFIG_REL).read_text(encoding="utf-8"))
    if config["experiment_version"] != VERSION:
        raise UnimodalContractError("unimodal configuration version mismatch")
    if tuple(config["algorithm_order"]) != ALGORITHMS:
        raise UnimodalContractError("algorithm family order mismatch")
    if tuple(config["modalities"]["C"]["predictors"]) != CODE_FEATURES:
        raise UnimodalContractError("CODE predictor contract mismatch")
    if tuple(config["modalities"]["P"]["predictors"]) != PROCESS_FEATURES:
        raise UnimodalContractError("PROCESS predictor contract mismatch")
    if config["modalities"]["T"]["input"] != "raw_commit_message":
        raise UnimodalContractError("TEXT input contract mismatch")
    if config["transformer_or_embedding_model"] != "NONE":
        raise UnimodalContractError("unexpected transformer/embedding contract")
    if config["predictive_partitions"] != ["TRAIN", "VALIDATION"]:
        raise UnimodalContractError("development partition contract mismatch")
    if config["test_access"] != {"T1": "DENY", "T2": "DENY"}:
        raise UnimodalContractError("TEST access contract mismatch")
    imbalance = config["class_imbalance"]
    if imbalance != {
        "class_weighting": "NONE",
        "oversampling": "NONE",
        "smote": "PROHIBITED",
        "training_prevalence": "NATURAL",
    }:
        raise UnimodalContractError("class-imbalance contract mismatch")
    return config


def make_estimator(algorithm: str, config: dict[str, Any]):
    if algorithm not in ALGORITHMS:
        raise UnimodalContractError(f"unapproved algorithm family: {algorithm}")
    parameters = dict(config["algorithms"][algorithm])
    if algorithm == "Logistic Regression":
        return LogisticRegression(**parameters)
    if algorithm == "Random Forest":
        return RandomForestClassifier(**parameters)
    if algorithm == "XGBoost":
        from xgboost import XGBClassifier

        return XGBClassifier(**parameters)
    from lightgbm import LGBMClassifier

    return LGBMClassifier(**parameters)


def make_pipeline(
    algorithm: str, modality: str, config: dict[str, Any]
) -> Pipeline:
    """Build an unfitted project-local TRAIN-only unimodal pipeline."""
    if modality not in MODALITIES:
        raise UnimodalContractError(f"unapproved modality: {modality}")
    steps: list[tuple[str, Any]] = []
    if modality in {"C", "P"}:
        steps.append(("imputer", SimpleImputer(strategy="median")))
        if algorithm == "Logistic Regression":
            steps.append(("scaler", StandardScaler()))
    else:
        text_parameters = dict(config["modalities"]["T"]["representation"])
        text_parameters["ngram_range"] = tuple(text_parameters["ngram_range"])
        steps.append(("tfidf", TfidfVectorizer(**text_parameters)))
    steps.append(("model", make_estimator(algorithm, config)))
    return Pipeline(steps)


def raw_features(rows: list[dict[str, Any]], modality: str) -> Any:
    if modality in {"C", "P"}:
        return np.asarray([row[modality] for row in rows], dtype=float)
    if modality == "T":
        return [row["T"] for row in rows]
    raise UnimodalContractError(f"unapproved modality: {modality}")


def fit_unimodal(
    train_rows: list[dict[str, Any]],
    algorithm: str,
    modality: str,
    config: dict[str, Any],
) -> Pipeline:
    if not train_rows or {row["partition"] for row in train_rows} != {"TRAIN"}:
        raise UnimodalContractError("fit input must contain TRAIN rows only")
    if len({row["project"] for row in train_rows}) != 1:
        raise UnimodalContractError("unimodal fit must be project-local")
    y = np.asarray([row["target"] for row in train_rows], dtype=int)
    if len(np.unique(y)) != 2:
        raise UnimodalContractError("TRAIN fit requires both observed classes")
    return make_pipeline(algorithm, modality, config).fit(
        raw_features(train_rows, modality), y
    )


def predict_positive_probability(
    fitted: Pipeline, rows: list[dict[str, Any]], modality: str
) -> np.ndarray:
    if any(row["partition"] in {"T1", "T2"} for row in rows):
        raise UnimodalContractError("T1/T2 scoring is denied")
    model = fitted.named_steps["model"]
    class_indexes = np.flatnonzero(np.asarray(model.classes_) == 1)
    if len(class_indexes) != 1:
        raise UnimodalContractError("positive class is absent or ambiguous")
    probabilities = np.asarray(
        fitted.predict_proba(raw_features(rows, modality))[:, class_indexes[0]],
        dtype=float,
    )
    if (
        probabilities.shape != (len(rows),)
        or not np.all(np.isfinite(probabilities))
        or np.any(probabilities < 0)
        or np.any(probabilities > 1)
    ):
        raise UnimodalContractError("invalid positive-class probabilities")
    return probabilities


def package_versions() -> dict[str, str]:
    return {
        package: importlib.metadata.version(package)
        for package in (
            "numpy",
            "scipy",
            "scikit-learn",
            "xgboost",
            "lightgbm",
        )
    }


def smoke_test_contract(root: Path) -> dict[str, Any]:
    """Fit all 12 actual-data unimodal combinations without computing metrics."""
    config = load_config(root)
    project = min(EXPECTED_PROJECTS)
    rows = load_development_project(root, project)
    train = [row for row in rows if row["partition"] == "TRAIN"]
    validation = [row for row in rows if row["partition"] == "VALIDATION"]
    scored_rows = validation[:64]
    results = []
    for algorithm in ALGORITHMS:
        for modality in MODALITIES:
            fitted = fit_unimodal(train, algorithm, modality, config)
            probabilities = predict_positive_probability(fitted, scored_rows, modality)
            steps = list(fitted.named_steps)
            results.append(
                {
                    "algorithm": algorithm,
                    "modality": modality,
                    "pipeline_steps": steps,
                    "fit_project": project,
                    "fit_partition": "TRAIN",
                    "fit_count": len(train),
                    "fit_membership_sha256": digest(
                        [row["row_identifier"] for row in train]
                    ),
                    "engineering_score_partition": "VALIDATION",
                    "engineering_score_count": len(scored_rows),
                    "probability_sha256": digest(probabilities.tolist()),
                    "probability_min": float(probabilities.min()),
                    "probability_max": float(probabilities.max()),
                    "metrics_computed": False,
                    "t1_t2_access_count": 0,
                }
            )
    return {
        "schema_version": VERSION,
        "status": "PASS",
        "purpose": "ENGINEERING_CONTRACT_SMOKE_TEST_NOT_SCIENTIFIC_EVIDENCE",
        "project_selection_rule": "LEXICOGRAPHICALLY_FIRST_ELIGIBLE_PROJECT",
        "condition_count": len(results),
        "conditions": results,
        "validation_labels_used_for_selection_or_metrics": False,
        "t1_predictive_access_count": 0,
        "t2_predictive_access_count": 0,
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


def materialize(root: Path) -> Path:
    config = load_config(root)
    output = root / OUTPUT_REL
    smoke = smoke_test_contract(root)
    _write_json(output / "unimodal_contract.json", config)
    _write_json(output / "engineering_smoke_test.json", smoke)
    _write_json(
        output / "runtime.json",
        {
            "schema_version": VERSION,
            "python": platform.python_version(),
            "packages": package_versions(),
            "random_seed": config["seed"],
            "algorithm_random_seeds": {
                algorithm: config["algorithms"][algorithm]["random_state"]
                for algorithm in ALGORITHMS
            },
        },
    )
    _write_json(
        output / "implementation.json",
        {
            "schema_version": VERSION,
            "implementation_path": (
                "src/experimentation/q1_controlled_unimodal_modeling.py"
            ),
            "implementation_sha256": file_digest(Path(__file__)),
            "configuration_path": str(CONFIG_REL),
            "configuration_sha256": file_digest(root / CONFIG_REL),
            "block_2_pilot_implementation_modified": False,
        },
    )
    _write_json(
        output / "execution_ledger.json",
        {
            "schema_version": VERSION,
            "engineering_model_fit_count": len(ALGORITHMS) * len(MODALITIES),
            "scientific_condition_count": 0,
            "validation_metric_count": 0,
            "hyperparameter_search_count": 0,
            "oversampling_count": 0,
            "smote_count": 0,
            "t1_predictive_access_count": 0,
            "t2_predictive_access_count": 0,
            "final_test_metric_count": 0,
        },
    )
    report = "\n".join(
        (
            "# Sprint 49 Unimodal Modeling Contract",
            "",
            "The exact four families are Logistic Regression, Random Forest, "
            "XGBoost, and LightGBM. CODE uses only la, ld, nf, nd, ns, and ent. "
            "PROCESS uses only ndev, age, nuc, aexp, arexp, and asexp. Numeric "
            "median imputation is TRAIN-fitted. Standardization is applied only "
            "to Logistic Regression; tree families are not scaled.",
            "",
            "TEXT uses only the raw prediction-commit message and a TRAIN-fitted "
            "sparse word-unigram TF-IDF representation. Character n-grams, "
            "supervised vocabulary construction, dimensionality reduction, "
            "transformers/embeddings, and explicit bug/fix/issue indicators are "
            "not used. No earlier frozen contract requires a transformer.",
            "",
            "Natural TRAIN prevalence is preserved. Class weighting, oversampling, "
            "and SMOTE are not used. Every fitted model exposes positive-class "
            "probabilities. All 12 algorithm/modality pipelines passed an "
            "actual-data engineering smoke test without metrics or selection. T1 "
            "and T2 predictive accesses remain zero.",
            "",
        )
    )
    (output / "REPORT.md").write_text(report, encoding="utf-8")
    _write_manifest(output)
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    print(materialize(args.root.resolve()))


if __name__ == "__main__":
    main()
