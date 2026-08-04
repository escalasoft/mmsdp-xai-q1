"""Contract tests for the project-independent scientific dataset specification."""

from __future__ import annotations

import inspect
import json
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest

from dataset import scientific_dataset_contract as contract
from dataset.scientific_dataset_contract import (
    ScientificDatasetContractValidator,
    ScientificDatasetSpecification,
    ScientificFeatureDisposition,
    ScientificFeatureModality,
    ScientificFeatureProvenance,
    ScientificFeatureTemporalScope,
    ScientificLeakageRisk,
    load_scientific_dataset_specification,
)

CONFIG = Path(__file__).parents[2] / "configs" / "scientific_dataset.json"
EXPECTED_API = [
    "ScientificDatasetRole",
    "ScientificFeatureModality",
    "ScientificFeatureTemporalScope",
    "ScientificLeakageRisk",
    "ScientificFeatureDisposition",
    "ScientificDatasetIdentity",
    "ScientificObservationContract",
    "ScientificTargetContract",
    "ScientificTimestampContract",
    "ScientificFeatureProvenance",
    "ScientificDatasetSpecification",
    "ScientificDatasetValidationResult",
    "ScientificDatasetContractValidator",
    "load_scientific_dataset_specification",
]


@pytest.fixture
def specification() -> ScientificDatasetSpecification:
    return load_scientific_dataset_specification(CONFIG)


def _feature(**changes: object) -> ScientificFeatureProvenance:
    values: dict[str, object] = {
        "feature_name": "safe_metric",
        "modality": "process",
        "source_artifact": "repository-history",
        "source_fields": ("value",),
        "temporal_scope": "commit-current",
        "availability_time": "at commit",
        "derivation_summary": "Count an available value.",
        "uses_target": False,
        "uses_issue_linking_evidence": False,
        "uses_future_information": False,
        "uses_post_event_information": False,
        "computed_using_full_dataset": False,
        "leakage_risk": "low",
        "disposition": "permitted",
        "rationale": "Available at commit time.",
        "allowed_in_complete_scenario": True,
        "allowed_in_leakage_controlled_scenario": True,
        "metadata": {},
    }
    values.update(changes)
    return ScientificFeatureProvenance(**values)


def _validate(specification: ScientificDatasetSpecification):
    return ScientificDatasetContractValidator().validate(specification)


def _issue_feature(**changes: object) -> ScientificFeatureProvenance:
    values: dict[str, object] = {
        "feature_name": "prior_issue_metric",
        "temporal_scope": "history-before-commit",
        "availability_time": "before observation",
        "uses_issue_linking_evidence": True,
        "leakage_risk": "review-required",
        "disposition": "review-required",
        "rationale": "Human-readable documentation only.",
        "allowed_in_leakage_controlled_scenario": False,
        "metadata": {
            "temporal_cutoff_policy": "strictly-before-observation",
            "target_independence": True,
            "current_target_excluded": True,
            "future_links_excluded": True,
            "linkage_policy_version": "1.0.0",
        },
    }
    values.update(changes)
    return _feature(**values)


def test_loads_canonical_json_configuration(specification) -> None:
    assert specification.identity.dataset_name == "generic-commit-dataset-template"


def test_exact_public_api() -> None:
    assert contract.__all__ == EXPECTED_API


def test_structural_equality(specification) -> None:
    assert specification == load_scientific_dataset_specification(CONFIG)


def test_specification_and_nested_metadata_are_immutable(specification) -> None:
    with pytest.raises(FrozenInstanceError):
        specification.minimum_feature_count = 1
    with pytest.raises(TypeError):
        specification.metadata["new"] = True
    with pytest.raises(TypeError):
        specification.metadata["scenario_policy"]["complete"] = "changed"


def test_to_dict_is_deterministic_and_detached(specification) -> None:
    first = specification.to_dict()
    assert first == specification.to_dict()
    first["metadata"]["scenario_policy"]["complete"] = "changed"
    assert first != specification.to_dict()


def test_canonical_json_and_digest_are_stable(specification) -> None:
    assert specification.canonical_json() == specification.canonical_json()
    assert specification.scientific_digest() == specification.scientific_digest()
    assert len(specification.scientific_digest()) == 64


def test_digest_changes_after_scientific_change(specification) -> None:
    changed = replace(specification, leakage_policy_version="1.0.1")
    assert changed.scientific_digest() != specification.scientific_digest()


@pytest.mark.parametrize(
    "label",
    [True, False, 1.0, float("nan"), float("inf"), [], (), set(), {}, None, object()],
)
def test_binary_target_rejects_invalid_labels(specification, label) -> None:
    with pytest.raises((TypeError, ValueError), match="positive_label"):
        replace(specification.target, positive_label=label)


def test_binary_target_accepts_detached_string_or_integer_labels(specification) -> None:
    integer_target = replace(specification.target, negative_label=-1, positive_label=2)
    string_target = replace(
        specification.target, negative_label="clean", positive_label="defect"
    )
    assert integer_target.to_dict()["positive_label"] == 2
    assert string_target.to_dict()["negative_label"] == "clean"
    with pytest.raises(ValueError, match="distinct"):
        replace(specification.target, negative_label=1, positive_label=1)
    with pytest.raises(ValueError, match="non-empty"):
        replace(specification.target, positive_label="  ")


def test_core_observation_roles(specification) -> None:
    assert specification.identity.observation_unit == "commit"
    assert specification.observation.identifier_role.value == "identifier"
    assert (
        specification.observation.timestamp_field == specification.timestamp.field_name
    )
    assert specification.observation.target_field == specification.target.field_name


def test_required_modalities_and_future_extensions(specification) -> None:
    assert {item.value for item in specification.required_modalities} == {
        "code",
        "process",
        "text",
    }
    assert {item.value for item in specification.optional_modalities} >= {
        "ast",
        "cfg",
        "call-graph",
        "image",
    }
    with pytest.raises(ValueError, match="modality"):
        _feature(modality="undocumented-new-modality")


def test_duplicate_feature_rejected(specification) -> None:
    with pytest.raises(ValueError, match="unique"):
        replace(
            specification,
            features=specification.features + (specification.features[0],),
        )


def test_duplicate_and_overlapping_modalities_rejected(specification) -> None:
    with pytest.raises(ValueError, match="duplicates"):
        replace(
            specification,
            required_modalities=specification.required_modalities
            + (ScientificFeatureModality.CODE,),
        )
    with pytest.raises(ValueError, match="overlap"):
        replace(specification, optional_modalities=(ScientificFeatureModality.CODE,))


def test_missing_required_modality_rejected(specification) -> None:
    with pytest.raises(ValueError, match="code, process, and text"):
        replace(
            specification,
            required_modalities=(
                ScientificFeatureModality.CODE,
                ScientificFeatureModality.PROCESS,
            ),
        )


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"uses_target": True}, "must be prohibited"),
        ({"uses_future_information": True}, "must be prohibited"),
        ({"uses_post_event_information": True}, "must be prohibited"),
        ({"temporal_scope": "future-derived"}, "must be prohibited"),
        ({"temporal_scope": "post-event"}, "must be prohibited"),
        ({"computed_using_full_dataset": True}, "full-dataset"),
    ],
)
def test_dangerous_feature_states_are_rejected(changes, message) -> None:
    with pytest.raises(ValueError, match=message):
        _feature(**changes)


@pytest.mark.parametrize(
    "changes",
    [
        {
            "disposition": "prohibited",
            "leakage_risk": "low",
            "allowed_in_complete_scenario": False,
            "allowed_in_leakage_controlled_scenario": False,
        },
        {"disposition": "permitted", "leakage_risk": "prohibited"},
        {
            "disposition": "review-required",
            "leakage_risk": "none",
            "allowed_in_leakage_controlled_scenario": False,
        },
        {
            "disposition": "review-required",
            "leakage_risk": "low",
            "allowed_in_leakage_controlled_scenario": False,
        },
        {"disposition": "permitted", "leakage_risk": "high"},
        {"disposition": "permitted", "leakage_risk": "review-required"},
    ],
)
def test_inconsistent_leakage_risk_and_disposition_rejected(changes) -> None:
    with pytest.raises(ValueError):
        _feature(**changes)


@pytest.mark.parametrize(
    "disposition",
    ["metadata-only", "identifier-only", "target-only", "timestamp-only"],
)
def test_non_feature_dispositions_are_never_enabled(disposition) -> None:
    with pytest.raises(ValueError, match="non-feature fields"):
        _feature(disposition=disposition)


@pytest.mark.parametrize(
    "name", ["commit_hash", "commit_timestamp", "is_defect_prone", "dataset_partition"]
)
def test_role_like_predictors_are_detected(specification, name) -> None:
    result = _validate(
        replace(
            specification,
            features=specification.features + (_feature(feature_name=name),),
        )
    )
    assert not result.is_valid
    assert any("enabled as a predictor" in error for error in result.errors)


def test_review_required_excluded_from_leakage_controlled(specification) -> None:
    with pytest.raises(ValueError, match="review-required"):
        replace(
            specification.feature_by_name("message_embedding"),
            allowed_in_leakage_controlled_scenario=True,
        )


def test_scenario_selection_is_explicit(specification) -> None:
    assert [item.feature_name for item in specification.permitted_features()] == [
        "lines_added",
        "prior_commit_count",
        "message_embedding",
        "prior_issue_resolution_rate",
    ]
    assert [
        item.feature_name for item in specification.leakage_controlled_features()
    ] == ["lines_added", "prior_commit_count"]
    assert all(
        item.disposition is not ScientificFeatureDisposition.PROHIBITED
        for item in specification.permitted_features()
    )
    assert all(
        item.disposition is ScientificFeatureDisposition.PERMITTED
        for item in specification.leakage_controlled_features()
    )


@pytest.mark.parametrize(
    "name",
    [
        "bug_confidence",
        "msg_has_bug_kw",
        "has_bug_keyword",
        "contains_bug_keyword",
        "contains_fix_keyword",
        "issue_link_indicator",
        "bug_link_count",
        "future_bug_count",
        "future_fix_count",
        "post_release_defect_count",
        "label_confidence",
        "target_probability",
        "is_bug",
        "is_buggy",
    ],
)
def test_suspicious_name_variants_are_detected(specification, name) -> None:
    candidate = _feature(feature_name=name)
    retained = tuple(
        item for item in specification.features if item.feature_name != name
    )
    result = _validate(replace(specification, features=retained + (candidate,)))
    assert any("prohibited feature-name policy" in error for error in result.errors)


def test_independent_strictly_prior_issue_history_is_not_automatically_prohibited(
    specification,
) -> None:
    feature = specification.feature_by_name("prior_issue_resolution_rate")
    assert (
        feature.temporal_scope is ScientificFeatureTemporalScope.HISTORY_BEFORE_COMMIT
    )
    assert feature.disposition is ScientificFeatureDisposition.REVIEW_REQUIRED
    assert not any(
        feature.feature_name in error for error in _validate(specification).errors
    )


def test_issue_feature_admissibility_does_not_parse_rationale(specification) -> None:
    first = _issue_feature(rationale="No policy keywords appear here.")
    second = replace(first, rationale="Completely different readable explanation.")
    for feature in (first, second):
        result = _validate(
            replace(specification, features=specification.features + (feature,))
        )
        assert not any(feature.feature_name in error for error in result.errors)


@pytest.mark.parametrize(
    "missing",
    [
        "temporal_cutoff_policy",
        "target_independence",
        "current_target_excluded",
        "future_links_excluded",
        "linkage_policy_version",
    ],
)
def test_issue_feature_missing_structured_control_fails(specification, missing) -> None:
    metadata = dict(_issue_feature().metadata)
    del metadata[missing]
    feature = _issue_feature(metadata=metadata)
    result = _validate(
        replace(specification, features=specification.features + (feature,))
    )
    assert any("issue-linking evidence" in error for error in result.errors)


@pytest.mark.parametrize(
    ("control", "value"),
    [
        ("temporal_cutoff_policy", "at-or-before-observation"),
        ("target_independence", False),
        ("current_target_excluded", False),
        ("future_links_excluded", False),
        ("linkage_policy_version", ""),
    ],
)
def test_issue_feature_false_or_invalid_control_fails(
    specification, control, value
) -> None:
    metadata = dict(_issue_feature().metadata)
    metadata[control] = value
    feature = _issue_feature(metadata=metadata)
    result = _validate(
        replace(specification, features=specification.features + (feature,))
    )
    assert any("issue-linking evidence" in error for error in result.errors)


@pytest.mark.parametrize(
    "changes",
    [
        {"uses_target": True},
        {"uses_future_information": True},
        {"uses_post_event_information": True},
        {"computed_using_full_dataset": True},
    ],
)
def test_current_target_or_non_prior_issue_linkage_remains_prohibited(changes) -> None:
    with pytest.raises(ValueError, match="must be prohibited|full-dataset"):
        _issue_feature(**changes)


def test_text_embedding_is_not_automatically_leakage_free(specification) -> None:
    feature = specification.feature_by_name("message_embedding")
    assert feature.leakage_risk is ScientificLeakageRisk.MEDIUM
    assert feature.disposition is ScientificFeatureDisposition.REVIEW_REQUIRED
    assert not feature.allowed_in_leakage_controlled_scenario


def test_missing_rationale_rejected() -> None:
    with pytest.raises(ValueError, match="rationale"):
        _feature(rationale="")


def test_missing_provenance_and_unknown_scope_warn(specification) -> None:
    incomplete = _feature(
        feature_name="incomplete",
        source_fields=(),
        source_artifact="unclassified",
        temporal_scope="unknown",
    )
    result = _validate(
        replace(specification, features=specification.features + (incomplete,))
    )
    assert any("provenance detail is incomplete" in item for item in result.warnings)
    assert any("source artifact is unclassified" in item for item in result.warnings)
    assert any("temporal scope is unknown" in item for item in result.warnings)


def test_minimum_feature_count_validation(specification) -> None:
    result = _validate(
        replace(specification, minimum_feature_count=len(specification.features) + 1)
    )
    assert "minimum feature count is not satisfied" in result.errors
    with pytest.raises(ValueError, match="positive integer"):
        replace(specification, minimum_feature_count=True)


@pytest.mark.parametrize("metadata", [[], "metadata", None])
def test_non_mapping_metadata_rejected(metadata) -> None:
    with pytest.raises(TypeError, match="mapping"):
        replace(_feature(), metadata=metadata)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_metadata_rejected(value) -> None:
    with pytest.raises(ValueError, match="finite"):
        replace(_feature(), metadata={"value": value})


def test_validation_result_count_invariants_and_order(specification) -> None:
    result = _validate(specification)
    assert result.error_count == len(result.errors)
    assert result.warning_count == len(result.warnings)
    assert result.is_valid == (not result.errors)
    assert list(result.errors) == sorted(result.errors)
    assert list(result.warnings) == sorted(result.warnings)


def test_loader_rejects_unknown_top_level_field(tmp_path) -> None:
    parsed = json.loads(CONFIG.read_text(encoding="utf-8"))
    parsed["unknown"] = True
    path = tmp_path / "unknown.json"
    path.write_text(json.dumps(parsed), encoding="utf-8")
    with pytest.raises(ValueError, match="unknown top-level"):
        load_scientific_dataset_specification(path)


def test_loader_rejects_missing_required_field(tmp_path) -> None:
    parsed = json.loads(CONFIG.read_text(encoding="utf-8"))
    del parsed["identity"]
    path = tmp_path / "missing.json"
    path.write_text(json.dumps(parsed), encoding="utf-8")
    with pytest.raises(ValueError, match="missing required top-level"):
        load_scientific_dataset_specification(path)


def test_loader_does_not_mutate_equivalent_parsed_input(specification) -> None:
    before = json.loads(CONFIG.read_text(encoding="utf-8"))
    specification.to_dict()["metadata"]["new"] = True
    assert json.loads(CONFIG.read_text(encoding="utf-8")) == before


def test_public_validator_has_no_operational_behavior() -> None:
    names = {
        name
        for name, _ in inspect.getmembers(
            ScientificDatasetContractValidator, inspect.isfunction
        )
        if not name.startswith("_")
    }
    assert names == {"validate"}
    forbidden = {
        "train",
        "predict",
        "save",
        "plot",
        "extract",
        "download",
        "request",
        "persist",
    }
    assert not names & forbidden
