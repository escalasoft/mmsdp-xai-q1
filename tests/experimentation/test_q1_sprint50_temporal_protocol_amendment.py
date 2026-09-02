from __future__ import annotations

from pathlib import Path

import pytest

from experimentation.q1_controlled_development_governance import (
    FULL_FOLD_IDENTIFIERS,
)
from experimentation.q1_controlled_train_validation_baselines import (
    EXPECTED_PROJECTS,
    load_development_project,
)
from experimentation.q1_sprint50_temporal_protocol_amendment import (
    CLASSIFICATION,
    TemporalProtocolError,
    access_audit,
    assert_history_only_fit_scope,
    build_amended_forward_fold,
    build_k2_nested_meta_split,
    decision_gates,
    fold_manifest,
)

ROOT = Path(__file__).resolve().parents[2]


def _rows(project: str) -> list[dict]:
    return load_development_project(ROOT, project)


def test_exact_cv_2_11_forward_domain_and_deterministic_memberships() -> None:
    first, first_k2 = fold_manifest(ROOT)
    second, second_k2 = fold_manifest(ROOT)
    assert first == second and first_k2 == second_k2
    assert len(first) == 14 * 10
    assert len(first_k2) == 14
    assert {row["cv_value"] for row in first} == set(range(2, 12))


@pytest.mark.parametrize("project", EXPECTED_PROJECTS)
def test_all_forward_folds_are_strictly_ordered_disjoint_and_project_local(
    project: str,
) -> None:
    rows = _rows(project)
    for cv_value in FULL_FOLD_IDENTIFIERS:
        fold = build_amended_forward_fold(rows, cv_value)
        history_ids = {row["row_identifier"] for row in fold.history_rows}
        evaluation_ids = {row["row_identifier"] for row in fold.evaluation_rows}
        assert not history_ids & evaluation_ids
        assert max(
            (row["timestamp"], row["commit_sha"]) for row in fold.history_rows
        ) < min(
            (row["timestamp"], row["commit_sha"])
            for row in fold.evaluation_rows
        )
        assert {
            row["project"]
            for row in (*fold.history_rows, *fold.evaluation_rows)
        } == {project}


@pytest.mark.parametrize("project", EXPECTED_PROJECTS)
def test_k2_nested_late_fusion_is_causal_supported_and_not_backfilled(
    project: str,
) -> None:
    split = build_k2_nested_meta_split(_rows(project))
    inner_ids = {row["row_identifier"] for row in split.inner_base_fit_rows}
    meta_ids = {row["row_identifier"] for row in split.meta_prediction_rows}
    evaluation_ids = {row["row_identifier"] for row in split.evaluation_rows}
    assert inner_ids.isdisjoint(meta_ids | evaluation_ids)
    assert meta_ids.isdisjoint(evaluation_ids)
    assert {row["target"] for row in split.inner_base_fit_rows} == {0, 1}
    assert {row["target"] for row in split.meta_prediction_rows} == {0, 1}
    assert max(
        (row["timestamp"], row["commit_sha"])
        for row in split.inner_base_fit_rows
    ) < min(
        (row["timestamp"], row["commit_sha"])
        for row in split.meta_prediction_rows
    )
    assert max(
        (row["timestamp"], row["commit_sha"])
        for row in split.meta_prediction_rows
    ) < min(
        (row["timestamp"], row["commit_sha"])
        for row in split.evaluation_rows
    )


@pytest.mark.parametrize("cv_value", (10, 11))
def test_k10_k11_keep_validation_provenance_while_using_causal_history(
    cv_value: int,
) -> None:
    for project in EXPECTED_PROJECTS:
        fold = build_amended_forward_fold(_rows(project), cv_value)
        assert "VALIDATION" in {row["partition"] for row in fold.history_rows}
        assert {row["partition"] for row in fold.evaluation_rows} == {"VALIDATION"}
        assert all(
            row["partition"] in {"TRAIN", "VALIDATION"}
            for row in fold.history_rows
        )


def test_history_only_fit_guard_rejects_evaluation_or_future_rows() -> None:
    fold = build_amended_forward_fold(_rows(EXPECTED_PROJECTS[0]), 10)
    history = {row["row_identifier"] for row in fold.history_rows}
    evaluation = {row["row_identifier"] for row in fold.evaluation_rows}
    assert_history_only_fit_scope(set(list(history)[:5]), history, evaluation)
    with pytest.raises(TemporalProtocolError, match="non-historical"):
        assert_history_only_fit_scope(
            {next(iter(evaluation))}, history, evaluation
        )


def test_t1_t2_access_and_all_predictive_execution_counters_are_zero() -> None:
    audit = access_audit()
    counters = {key: value for key, value in audit.items() if key.endswith("_count")}
    assert counters and set(counters.values()) == {0}


def test_all_prospective_gates_pass_but_human_authorization_is_required() -> None:
    gates = decision_gates(ROOT)
    assert gates["classification"] == CLASSIFICATION
    assert all(row["passed"] for row in gates["gates"])
    assert gates["predictive_execution_authorized_by_automation"] is False
    assert gates["human_authorization_required"] is True
