from __future__ import annotations

from pathlib import Path

import pytest

from experimentation.q1_controlled_late_fusion import (
    CONFIGURATIONS,
    FUSION_CONFIGURATIONS,
    LateFusionContractError,
    build_oof_meta_table,
    fit_and_score_family,
    load_config,
)
from experimentation.q1_controlled_unimodal_modeling import (
    load_config as load_unimodal_config,
)

ROOT = Path(__file__).resolve().parents[2]


def _rows(partition: str, blocks: tuple[int, ...]) -> list[dict[str, object]]:
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


def test_architecture_and_configuration_matrix_are_exact() -> None:
    config = load_config(ROOT)
    assert CONFIGURATIONS == ("C", "P", "T", "C+P", "C+T", "P+T", "C+P+T")
    assert FUSION_CONFIGURATIONS == {
        "C+P": ("C", "P"),
        "C+T": ("C", "T"),
        "P+T": ("P", "T"),
        "C+P+T": ("C", "P", "T"),
    }
    assert config["meta_learner"]["regularization"] == "L2"
    assert config["meta_learner"]["l1_ratio"] == 0.0
    assert config["meta_learner_is_fifth_algorithm"] is False
    assert config["raw_feature_concatenation_primary"] is False


def test_oof_table_is_forward_train_only_and_warmup_is_not_backfilled() -> None:
    table = build_oof_meta_table(
        _rows("TRAIN", (1, 2, 3, 4)),
        "Logistic Regression",
        load_unimodal_config(ROOT),
    )
    assert table.probabilities.shape == (24, 3)
    assert len(table.warmup_row_identifiers) == 8
    assert not set(table.row_identifiers) & set(table.warmup_row_identifiers)
    assert all(
        fold["fit_prediction_disjoint"] and fold["strict_forward_time"]
        for fold in table.fold_lineage
    )


def test_seven_conditions_share_validation_identities_and_use_probabilities() -> None:
    result = fit_and_score_family(
        _rows("TRAIN", (1, 2, 3, 4)),
        _rows("VALIDATION", (5,)),
        "Logistic Regression",
        load_unimodal_config(ROOT),
        load_config(ROOT),
    )
    assert tuple(result["probability_streams"]) == CONFIGURATIONS
    assert len(
        {
            row["validation_membership_sha256"]
            for row in result["probability_streams"].values()
        }
    ) == 1
    assert result["validation_labels_used_for_meta_fit"] is False
    assert result["raw_feature_concatenation"] is False
    assert result["meta_learner_counted_as_fifth_algorithm"] is False
    for row in result["probability_streams"].values():
        assert 0 <= row["probability_min"] <= row["probability_max"] <= 1


def test_in_sample_or_test_memberships_are_rejected() -> None:
    config = load_unimodal_config(ROOT)
    with pytest.raises(LateFusionContractError, match="TRAIN rows only"):
        build_oof_meta_table(
            _rows("VALIDATION", (1, 2)), "Logistic Regression", config
        )
    rows = _rows("TRAIN", (1, 2))
    rows[8]["timestamp"] = rows[0]["timestamp"]
    rows[8]["commit_sha"] = rows[0]["commit_sha"]
    with pytest.raises(LateFusionContractError, match="not strictly earlier"):
        build_oof_meta_table(rows, "Logistic Regression", config)
