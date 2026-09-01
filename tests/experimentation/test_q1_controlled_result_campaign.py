from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from experimentation.q1_controlled_result_campaign import (
    METRICS,
    THRESHOLD,
    CampaignError,
    _ablation_table,
    _long_rows,
    _prediction_rows,
    _relative_table,
    _write_csv,
    assert_scoring_partition_allowed,
    load_config,
    predictive_metrics,
)

ROOT = Path(__file__).resolve().parents[2]


def _validation_records():
    rows = []
    from experimentation.q1_controlled_late_fusion import CONFIGURATIONS
    from experimentation.q1_controlled_train_validation_baselines import (
        EXPECTED_PROJECTS,
    )
    from experimentation.q1_controlled_unimodal_modeling import ALGORITHMS

    for project in EXPECTED_PROJECTS:
        for algorithm in ALGORITHMS:
            for index, configuration in enumerate(CONFIGURATIONS):
                metrics = {metric: 0.2 + index * 0.05 for metric in METRICS}
                rows.append(
                    {
                        "project": project,
                        "algorithm_family": algorithm,
                        "configuration": configuration,
                        **metrics,
                    }
                )
    return rows


def test_metric_contract_includes_counts_prevalence_and_no_accuracy() -> None:
    values = predictive_metrics(
        np.asarray([0, 0, 1, 1]), np.asarray([0.1, 0.2, 0.8, 0.9])
    )
    assert tuple(metric for metric in values if metric in METRICS) == METRICS
    assert values["TN"] == 2 and values["TP"] == 2
    assert values["FP"] == 0 and values["FN"] == 0
    assert values["positive_prevalence"] == 0.5
    assert values["n_observations"] == 4
    assert "Accuracy" not in values


def test_threshold_and_guard_are_predeclared() -> None:
    config = load_config(ROOT)
    assert THRESHOLD == 0.5
    assert config["threshold_policy"]["source"] == "PREDECLARED_FIXED"
    assert config["threshold_policy"]["validation_threshold_selection"] == "PROHIBITED"
    assert (
        config["near_perfect_guard"]["flag"]
        == "PERFECT_OR_NEAR_PERFECT_PERFORMANCE_REQUIRES_AUDIT"
    )


def test_article_comparison_tables_have_complete_cardinality() -> None:
    validation = _validation_records()
    table_e = _relative_table(validation, ("C", "P", "T"), "full vs unimodal")
    table_f = _relative_table(validation, ("C+P", "C+T", "P+T"), "full vs pairwise")
    ablation = _ablation_table(validation)
    assert len(table_e) == 14 * 4 * 6
    assert len(table_f) == 14 * 4 * 6
    assert len(ablation) == 14 * 4 * 3 * 6
    assert not any(
        row["statistical_significance_claimed"] for row in table_e + table_f + ablation
    )


def test_long_contract_nests_project_algorithm_configuration_fold_metric() -> None:
    record = {
        "project": "apache/activemq",
        "algorithm_family": "Logistic Regression",
        "configuration": "C",
        "result_level": "VALIDATION",
        "development_fold": "FROZEN_VALIDATION",
        "threshold": 0.5,
        "TN": 2,
        "FP": 0,
        "FN": 0,
        "TP": 2,
        "positive_prevalence": 0.5,
        "n_observations": 4,
        "membership_sha256": "a" * 64,
        "probability_sha256": "b" * 64,
        **{metric: 1.0 for metric in METRICS},
    }
    rows = _long_rows([record])
    assert len(rows) == 6
    assert [row["metric"] for row in rows] == list(METRICS)
    assert all(row["development_fold"] == "FROZEN_VALIDATION" for row in rows)


def test_raw_probabilities_are_preserved_with_identity_and_observed_label() -> None:
    rows = _prediction_rows(
        "apache/activemq",
        "Logistic Regression",
        "C",
        "VALIDATION",
        "FROZEN_VALIDATION",
        "VALIDATION",
        ["a", "b"],
        np.asarray([0, 1]),
        np.asarray([0.25, 0.75]),
    )
    assert [row["raw_probability"] for row in rows] == [0.25, 0.75]
    assert [row["benchmark_defined_observed_label"] for row in rows] == [0, 1]
    assert [row["row_identifier"] for row in rows] == ["a", "b"]


@pytest.mark.parametrize("partition", ("T1", "T2"))
def test_test_access_guard_fails_closed_without_future_authorization(
    partition: str,
) -> None:
    with pytest.raises(CampaignError, match="explicit future authorization"):
        assert_scoring_partition_allowed(partition)


def test_train_and_validation_scoring_are_separately_allowed() -> None:
    assert_scoring_partition_allowed("TRAIN")
    assert_scoring_partition_allowed("VALIDATION")


def test_campaign_csv_writer_uses_deterministic_lf_line_endings(
    tmp_path: Path,
) -> None:
    output = tmp_path / "result.csv"
    _write_csv(output, [{"project": "apache/activemq", "metric": 0.5}])
    payload = output.read_bytes()
    assert payload == b"project,metric\napache/activemq,0.5\n"
    assert b"\r" not in payload
