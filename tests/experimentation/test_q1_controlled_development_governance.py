from __future__ import annotations

from pathlib import Path

import pytest

from experimentation.q1_controlled_development_governance import (
    DIAGNOSTIC_METRICS,
    FULL_FOLD_IDENTIFIERS,
    PRIMARY_DEVELOPMENT_FOLD_COUNT,
    PRIMARY_FOLD_IDENTIFIERS,
    SELECTION_METRIC,
    DevelopmentGovernanceError,
    build_forward_fold,
    build_primary_folds,
    load_config,
    select_hyperparameters,
)
from experimentation.q1_controlled_unimodal_modeling import (
    load_config as load_unimodal_config,
)

ROOT = Path(__file__).resolve().parents[2]


def _rows(blocks: tuple[int, ...], partition: str = "TRAIN"):
    rows = []
    index = 0
    for block in blocks:
        for within in range(8):
            rows.append(
                {
                    "row_identifier": f"{partition}-{block}-{within}",
                    "project": "apache/activemq",
                    "partition": partition,
                    "forward_block": float(block),
                    "timestamp": f"2020-01-{block:02d}T00:{within:02d}:00Z",
                    "commit_sha": f"{index:040x}",
                    "target": within % 2,
                    "C": [within, block, 1, 2, 3, within / 10],
                    "P": [1, within, block, 3, 4, 5],
                    "T": f"refactor module component block{block} value{within % 2}",
                }
            )
            index += 1
    return rows


def test_governance_is_compact_pr_auc_primary_and_accuracy_prohibited() -> None:
    config = load_config(ROOT)
    assert SELECTION_METRIC == "PR_AUC"
    assert DIAGNOSTIC_METRICS == ("MCC", "ROC_AUC", "Recall")
    assert all(len(space) == 2 for space in config["algorithm_search_spaces"].values())
    assert "Accuracy" in config["prohibited_selection_metrics"]
    assert config["random_seed"] == 20260901


def test_fold_infrastructure_supports_every_k_from_2_through_11() -> None:
    rows = _rows(tuple(range(1, 12)))
    assert FULL_FOLD_IDENTIFIERS == tuple(range(2, 12))
    for identifier in FULL_FOLD_IDENTIFIERS:
        fold = build_forward_fold(rows, identifier)
        assert fold.fold_identifier == identifier
        assert all(int(row["forward_block"]) < identifier for row in fold.fit_rows)
        assert all(int(row["forward_block"]) == identifier for row in fold.score_rows)


def test_primary_fold_count_and_identifiers_are_frozen_before_results() -> None:
    folds = build_primary_folds(_rows(tuple(range(1, 10))))
    assert PRIMARY_DEVELOPMENT_FOLD_COUNT == 3
    assert PRIMARY_FOLD_IDENTIFIERS == (3, 6, 9)
    assert tuple(fold.fold_identifier for fold in folds) == PRIMARY_FOLD_IDENTIFIERS


def test_train_only_search_records_space_metrics_parameters_seed_and_fits() -> None:
    result = select_hyperparameters(
        _rows(tuple(range(1, 10))),
        "Logistic Regression",
        "C",
        load_unimodal_config(ROOT),
        load_config(ROOT),
    )
    assert result["primary_selection_metric"] == "PR_AUC"
    assert result["diagnostic_metrics"] == ["MCC", "ROC_AUC", "Recall"]
    assert result["accuracy_used"] is False
    assert result["candidate_count"] == 2
    assert result["number_of_fits"] == 6
    assert result["selected_candidate_id"] in {"LR_C_0_1", "LR_C_1_0"}
    assert result["random_seed"] == 20260901
    assert result["validation_access_count"] == 0


def test_validation_rows_and_shuffled_or_unavailable_folds_fail_closed() -> None:
    with pytest.raises(DevelopmentGovernanceError, match="TRAIN rows only"):
        build_forward_fold(_rows((1, 2), "VALIDATION"), 2)
    with pytest.raises(DevelopmentGovernanceError, match="not available"):
        build_forward_fold(_rows((1, 2)), 3)
    with pytest.raises(DevelopmentGovernanceError, match="2..11"):
        build_forward_fold(_rows((1, 2)), 12)
