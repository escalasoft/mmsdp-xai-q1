from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from experimentation.q1_controlled_unimodal_modeling import (
    ALGORITHMS,
    MODALITIES,
    UnimodalContractError,
    fit_unimodal,
    load_config,
    make_pipeline,
    package_versions,
    predict_positive_probability,
)

ROOT = Path(__file__).resolve().parents[2]


def _rows(partition: str = "TRAIN") -> list[dict[str, object]]:
    return [
        {
            "row_identifier": str(index),
            "project": "apache/activemq",
            "partition": partition,
            "target": index % 2,
            "C": [index, index + 1, 1, 2, 3, 0.1 * index],
            "P": [1, index, 2, 3, 4, 5],
            "T": f"refactor module component value {index % 4}",
        }
        for index in range(20)
    ]


def test_exact_families_modalities_versions_and_seed_contract() -> None:
    config = load_config(ROOT)
    assert ALGORITHMS == (
        "Logistic Regression",
        "Random Forest",
        "XGBoost",
        "LightGBM",
    )
    assert MODALITIES == ("C", "P", "T")
    assert config["seed"] == 20260901
    assert set(package_versions()) == {
        "numpy",
        "scipy",
        "scikit-learn",
        "xgboost",
        "lightgbm",
    }


def test_numeric_scaling_is_lr_only_and_text_is_sparse_tfidf() -> None:
    config = load_config(ROOT)
    for algorithm in ALGORITHMS:
        numeric_steps = list(make_pipeline(algorithm, "C", config).named_steps)
        assert ("scaler" in numeric_steps) is (algorithm == "Logistic Regression")
        assert numeric_steps[0] == "imputer"
        text_steps = list(make_pipeline(algorithm, "T", config).named_steps)
        assert text_steps == ["tfidf", "model"]


@pytest.mark.parametrize("algorithm", ALGORITHMS)
@pytest.mark.parametrize("modality", MODALITIES)
def test_all_twelve_pipelines_produce_valid_probabilities(
    algorithm: str, modality: str
) -> None:
    config = load_config(ROOT)
    fitted = fit_unimodal(_rows(), algorithm, modality, config)
    probabilities = predict_positive_probability(fitted, _rows("VALIDATION"), modality)
    assert probabilities.shape == (20,)
    assert np.all(np.isfinite(probabilities))
    assert np.all((probabilities >= 0) & (probabilities <= 1))


def test_fit_is_project_local_train_only_and_test_scoring_denied() -> None:
    config = load_config(ROOT)
    with pytest.raises(UnimodalContractError, match="TRAIN rows only"):
        fit_unimodal(_rows("VALIDATION"), "Logistic Regression", "C", config)
    fitted = fit_unimodal(_rows(), "Logistic Regression", "C", config)
    with pytest.raises(UnimodalContractError, match="T1/T2 scoring is denied"):
        predict_positive_probability(fitted, _rows("T1"), "C")
