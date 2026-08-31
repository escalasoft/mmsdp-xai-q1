"""Focused leakage and campaign-orchestration tests for Sprint 48B."""

import json

import pytest

from experimentation.q1_campaign_readiness import (
    CampaignContractError,
    SourceOnlyStandardizer,
    consume_target_authorization,
    generate_campaign_cells,
    lopo_membership,
    validate_feature_schema,
)


def test_standardizer_never_fits_target_distribution() -> None:
    state = SourceOnlyStandardizer.fit(
        [[1.0, 7.0], [3.0, 7.0], [5.0, 7.0]], ["varying", "constant"]
    )
    first = state.transform([[100.0, 999.0]], ["varying", "constant"])
    state_before = state.to_dict()
    state.transform([[-100.0, -999.0]], ["varying", "constant"])

    assert state.fit_scope == "SOURCE_TRAIN_ONLY"
    assert state.retained_features == ("varying",)
    source_deviation = (8.0 / 3.0) ** 0.5
    assert first[0][0] == pytest.approx((100.0 - 3.0) / source_deviation)
    assert state.to_dict() == state_before
    assert state.to_dict()["target_fitted_state"] is False


def test_schema_and_lopo_are_exact_and_disjoint() -> None:
    schema = {"C": ["added"], "P": ["history"], "T": ["message"]}
    validate_feature_schema(schema, schema, {"target", "fix_issue"})
    membership = lopo_membership({"a": ["1", "2"], "b": ["3"]}, "b")
    assert membership["source_projects"] == ["a"]
    assert membership["source_target_overlap"] == 0

    with pytest.raises(CampaignContractError, match="prohibited"):
        validate_feature_schema(
            {"C": ["target"], "P": ["history"], "T": ["message"]},
            {"C": ["target"], "P": ["history"], "T": ["message"]},
            {"target"},
        )


def test_campaign_factorial_is_unique_and_blocked() -> None:
    cells = generate_campaign_cells([f"project-{index}" for index in range(10)])
    assert len(cells) == 720
    assert len({cell["configuration_id"] for cell in cells}) == 720
    assert all(cell["execution_status"] == "BLOCKED_PRE_EXECUTION" for cell in cells)


def test_target_gate_is_default_deny_identity_bound_and_one_use(tmp_path) -> None:
    bindings = {
        "dataset_identity": "dataset",
        "target_identity": "target",
        "temporal_boundary_digest": "boundary",
        "sample_manifest_sha256": "samples",
        "provenance_digest": "provenance",
        "feature_schema_digest": "features",
    }
    request = {**bindings, "authorization_token": "human-token"}
    with pytest.raises(CampaignContractError, match="not authorized"):
        consume_target_authorization(
            {
                **bindings,
                "execution_authorized": False,
                "access_counter": 0,
                "authorization_token": None,
            },
            request,
            tmp_path / "ledger.json",
        )

    policy = {
        **bindings,
        "execution_authorized": True,
        "access_counter": 0,
        "authorization_token": "human-token",
    }
    ledger_path = tmp_path / "ledger.json"
    ledger = consume_target_authorization(policy, request, ledger_path)
    assert ledger["access_counter"] == 1
    assert json.loads(ledger_path.read_text()) == ledger
    with pytest.raises(CampaignContractError, match="already exists"):
        consume_target_authorization(policy, request, ledger_path)
