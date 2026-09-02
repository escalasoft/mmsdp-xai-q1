from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import pytest

from experimentation.q1_controlled_late_fusion import CONFIGURATIONS
from experimentation.q1_controlled_train_validation_baselines import (
    EXPECTED_PROJECTS,
)
from experimentation.q1_controlled_unimodal_modeling import ALGORITHMS
from experimentation.q1_sprint50_temporal_robustness import (
    METRICS,
    RobustnessCampaignError,
    _holm,
    _prediction_row,
    _rank_biserial,
    _summary,
    _write_csv,
    best_family_comparison_rows,
    classify,
    comparison_rows,
    comparison_summary_rows,
    load_config,
    paired_project_input,
    probability_metrics,
    statistical_results,
    verify_sources,
)

ROOT = Path(__file__).resolve().parents[2]


def _synthetic_conditions() -> list[dict]:
    rows = []
    for project_index, project in enumerate(EXPECTED_PROJECTS):
        for algorithm_index, algorithm in enumerate(ALGORITHMS):
            for configuration_index, configuration in enumerate(CONFIGURATIONS):
                for cv_value in range(2, 12):
                    base = (
                        0.1
                        + project_index / 100
                        + algorithm_index / 1000
                        + configuration_index / 10000
                        + cv_value / 100000
                    )
                    rows.append(
                        {
                            "project": project,
                            "algorithm": algorithm,
                            "configuration": configuration,
                            "cv_value": cv_value,
                            **{metric: base for metric in METRICS},
                        }
                    )
    return rows


def test_contract_freezes_exact_factorial_and_prospective_rules() -> None:
    config = load_config(ROOT)
    assert len(EXPECTED_PROJECTS) * len(ALGORITHMS) * len(CONFIGURATIONS) * 10 == 3920
    assert config["expected_condition_count"] == 3920
    assert config["cv_values"] == list(range(2, 12))
    assert config["ceiling_diagnostic_threshold"] == 0.99
    assert config["threshold"] == 0.5
    assert config["inference"]["experimental_unit"] == "PROJECT"
    assert config["inference"]["multiple_comparison_correction"] == "HOLM"


def test_all_frozen_source_manifests_verify_before_execution() -> None:
    result = verify_sources(ROOT)
    assert result["status"] == "PASS"
    assert result["T1_access_count"] == result["T2_access_count"] == 0


def test_metrics_include_primary_set_confusion_and_raw_calibration() -> None:
    targets = np.asarray([0, 0, 1, 1])
    probabilities = np.asarray([0.1, 0.2, 0.8, 0.9])
    result = probability_metrics(targets, probabilities)
    assert all(result[metric] == pytest.approx(1.0) for metric in METRICS)
    assert (result["TN"], result["FP"], result["FN"], result["TP"]) == (2, 0, 0, 2)
    assert result["Brier"] == pytest.approx(0.025)
    assert result["ECE"] == pytest.approx(0.15)


def test_metric_population_requires_both_classes() -> None:
    with pytest.raises(RobustnessCampaignError, match="metric population"):
        probability_metrics(np.asarray([0, 0]), np.asarray([0.1, 0.2]))


def test_sample_sd_and_dispersion_are_not_margin_of_error() -> None:
    result = _summary([1.0, 2.0, 3.0])
    assert result["metric_mean"] == pytest.approx(2.0)
    assert result["metric_sd"] == pytest.approx(1.0)
    assert result["metric_median"] == pytest.approx(2.0)
    assert result["metric_min"] == 1.0
    assert result["metric_max"] == 3.0
    assert result["n_cv"] == 3


def test_pairing_preserves_project_algorithm_configuration_cv_identity() -> None:
    conditions = _synthetic_conditions()
    comparisons = comparison_rows(conditions)
    assert len(comparisons) == 14 * 4 * 10 * 6 * 6
    assert len(
        {
            (
                row["project"],
                row["algorithm"],
                row["cv_value"],
                row["metric"],
                row["comparator"],
            )
            for row in comparisons
        }
    ) == len(comparisons)


def test_best_unimodal_and_best_pairwise_are_distinct_descriptive_comparisons() -> None:
    conditions = _synthetic_conditions()
    rows = best_family_comparison_rows(conditions)
    assert len(rows) == 14 * 4 * 10 * 2 * 6
    assert {row["comparison_family"] for row in rows} == {
        "BEST_UNIMODAL",
        "BEST_PAIRWISE",
    }
    summary = comparison_summary_rows(rows, load_config(ROOT))
    assert len(summary) == 4 * 6 * 2
    assert {row["n_conditions"] for row in summary} == {14 * 10}
    assert all(
        row["project_wins"] + row["project_ties"] + row["project_losses"] == 14
        for row in summary
    )
    assert all(
        row["cv_wins"] + row["cv_ties"] + row["cv_losses"] == 10 for row in summary
    )


def test_inference_uses_fourteen_project_units_and_expected_families() -> None:
    config = load_config(ROOT)
    paired = paired_project_input(_synthetic_conditions(), config)
    assert len(paired) == 14 * 4 * 7 * 2
    assert {row["cv_origin_count"] for row in paired} == {10}
    omnibus, pairwise = statistical_results(paired, config)
    assert len(omnibus) == 4 * 2
    assert len(pairwise) == 4 * 2 * 6
    assert {row["n_paired_projects"] for row in pairwise} == {14}
    assert all(0 <= row["adjusted_p_value"] <= 1 for row in pairwise)


def test_holm_adjustment_and_rank_biserial_direction() -> None:
    rows = [{"raw_p_value": value} for value in (0.01, 0.04, 0.03)]
    _holm(rows, 0.05)
    assert [row["adjusted_p_value"] for row in rows] == pytest.approx(
        [0.03, 0.06, 0.06]
    )
    assert _rank_biserial(np.asarray([1.0, 2.0, 3.0])) == pytest.approx(1.0)
    assert _rank_biserial(np.asarray([-1.0, -2.0, -3.0])) == pytest.approx(-1.0)
    assert _rank_biserial(np.asarray([0.0, 0.0])) == 0.0


def test_classification_is_prospectively_deterministic() -> None:
    config = load_config(ROOT)
    neutral = [
        {
            "holm_significant": False,
            "mean_paired_difference": 0.1,
            "bootstrap_95_ci_low": 0.01,
            "rank_biserial_correlation": 1.0,
        }
    ] * 48
    assert classify(neutral, 0, config) == "PASS_50_NO_STATISTICAL_SUPERIORITY"
    robust = [{**row, "holm_significant": True} for row in neutral]
    assert classify(robust, 0, config) == (
        "PASS_50_ROBUST_TEMPORAL_EVIDENCE_READY_FOR_NEXT_STAGE"
    )
    assert classify(robust, 1, config) == "BLOCKED_50_REPRODUCIBILITY"


def test_prediction_guard_denies_non_development_partition() -> None:
    condition = {
        "project": "p",
        "algorithm": "LR",
        "configuration": "C",
        "cv_value": 2,
    }
    row = {
        "row_identifier": "x",
        "partition": "T1",
        "forward_block": 2,
        "target": 1,
    }
    with pytest.raises(RobustnessCampaignError, match="prediction attempt denied"):
        _prediction_row(condition, row, 0.5)


def test_csv_serialization_uses_lf_line_endings(tmp_path: Path) -> None:
    path = tmp_path / "evidence.csv"
    _write_csv(path, [{"a": 1, "b": 2}])
    assert b"\r\n" not in path.read_bytes()
    with path.open(newline="", encoding="utf-8") as stream:
        assert list(csv.DictReader(stream)) == [{"a": "1", "b": "2"}]
