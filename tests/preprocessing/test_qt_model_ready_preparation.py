"""Fail-closed tests for Qt train-only numeric input preparation."""

from __future__ import annotations

from dataclasses import replace

import pytest

from dataset.model_input import ModelPartitionInput, PreparedModelInput
from dataset.qt_model_input_adaptation import (
    QtModelInputAdaptationError,
    QtModelInputAdaptationResult,
    adapt_qt_model_inputs,
)
from preprocessing.qt_model_ready_preparation import (
    QtModelReadyPreparation,
    QtModelReadyPreparationError,
    QtTextRepresentationPolicy,
    prepare_qt_model_ready_inputs,
)
from tests.dataset.test_qt_model_input_adaptation import _split


def _replace_partition(
    model_input: PreparedModelInput,
    name: str,
    *,
    messages: tuple[str, ...] | None = None,
    targets: tuple[int, ...] | None = None,
    identifiers: tuple[str, ...] | None = None,
) -> PreparedModelInput:
    original = getattr(model_input, name)
    changed = ModelPartitionInput(
        original.partition_name,
        identifiers or original.identifiers,
        (
            tuple((message,) for message in messages)
            if messages is not None
            else original.X
        ),
        targets or original.y,
        original.feature_names,
        original.metadata,
    )
    return replace(model_input, **{name: changed})


def _rebind(
    source: QtModelInputAdaptationResult, **modalities
) -> QtModelInputAdaptationResult:
    values = {
        "specification": source.specification,
        "policy": source.policy,
        "code": modalities.get("code", source.code),
        "process": modalities.get("process", source.process),
        "text": modalities.get("text", source.text),
        "validation": source.validation,
        "source_split_identity_digest": source.source_split_identity_digest,
    }
    return QtModelInputAdaptationResult(
        **values,
        adaptation_identity_digest=QtModelInputAdaptationResult.calculate_identity(
            values["specification"],
            values["policy"],
            values["code"],
            values["process"],
            values["text"],
        ),
    )


def _source() -> QtModelInputAdaptationResult:
    source = adapt_qt_model_inputs(_split())
    text = source.text
    text = _replace_partition(
        text,
        "train",
        messages=("alpha beta beta", "alpha gamma", "beta gamma alpha"),
    )
    text = _replace_partition(
        text, "validation", messages=("alpha unseenvalidation", "gamma alpha")
    )
    text = _replace_partition(text, "test", messages=("beta unseentest", "alpha"))
    return _rebind(source, text=text)


def test_fits_train_only_and_validation_test_are_transform_only() -> None:
    result = prepare_qt_model_ready_inputs(_source())

    assert result.text_state.fit_partition == "train"
    assert result.text_state.training_document_count == 3
    assert result.fit_audit["fit_partitions"] == ("train",)
    assert result.fit_audit["transform_only_partitions"] == ("validation", "test")
    assert result.validation_audit["identifiers_aligned"] is True
    assert result.validation_audit["targets_aligned"] is True
    assert "unseenvalidation" not in result.text_state.vocabulary
    assert "unseentest" not in result.text_state.vocabulary


@pytest.mark.parametrize("partition", ["validation", "test"])
def test_changing_non_train_text_cannot_change_fitted_state(partition: str) -> None:
    source = _source()
    original = prepare_qt_model_ready_inputs(source)
    changed_text = _replace_partition(
        source.text,
        partition,
        messages=("completely novel vocabulary", "more future words"),
    )
    changed = prepare_qt_model_ready_inputs(_rebind(source, text=changed_text))

    assert changed.text_state == original.text_state
    assert changed.text_state.state_digest == original.text_state.state_digest


def test_changing_train_text_changes_fitted_state() -> None:
    source = _source()
    changed_text = _replace_partition(
        source.text,
        "train",
        messages=("delta delta epsilon", "delta epsilon", "epsilon delta"),
    )

    assert (
        prepare_qt_model_ready_inputs(
            _rebind(source, text=changed_text)
        ).text_state.state_digest
        != prepare_qt_model_ready_inputs(source).text_state.state_digest
    )


def test_membership_alignment_and_numeric_schemas_are_preserved() -> None:
    source = _source()
    result = prepare_qt_model_ready_inputs(source)

    assert result.code_feature_names == source.code.feature_names
    assert result.process_feature_names == source.process.feature_names
    assert result.partition_counts == {"train": 3, "validation": 2, "test": 2}
    for name in ("train", "validation", "test"):
        actual = getattr(result, name)
        expected = getattr(source.code, name)
        assert actual.identifiers == expected.identifiers
        assert actual.y == expected.y
        assert actual.code.rows == expected.X
        assert actual.process.rows == getattr(source.process, name).X
        assert actual.text.row_count == len(expected.identifiers)


def test_forbidden_predictors_and_provenance_are_outside_matrices() -> None:
    result = prepare_qt_model_ready_inputs(_source())
    names = (
        result.code_feature_names
        + result.process_feature_names
        + result.text_feature_names
    )
    forbidden = {
        "bug_confidence",
        "fix_keyword_indicator",
        "has_bug_keyword",
        "msg_has_bug_kw",
        "commit_identifier",
        "committed_at",
        "partition",
        "target",
        "issue",
        "candidate",
        "szz",
    }
    assert all(not any(item in name for item in forbidden) for name in names)
    assert result.train.identifiers
    assert result.train.y


def test_structured_message_provenance_is_not_exposed_as_text_features() -> None:
    source = _source()
    messages = (
        "Useful subject\n\nChange-Id: "
        "I0123456789012345678901234567890123456789\n"
        "Reviewed-by: Person <p@example.org>",
        "Useful subject QTBUG-123 https://example.org/path\nBody provenance",
        "Another useful subject\nTask-number: QTBUG-456",
    )
    text = _replace_partition(source.text, "train", messages=messages)
    state = prepare_qt_model_ready_inputs(_rebind(source, text=text)).text_state

    assert "useful" in state.vocabulary
    assert set(state.vocabulary).isdisjoint(
        {"change", "id", "reviewed", "person", "example", "org", "qtbug", "123"}
    )


def test_target_changes_cannot_influence_text_state() -> None:
    source = _source()
    changed_targets = tuple(1 - value for value in source.text.train.y)
    changed_text = _replace_partition(source.text, "train", targets=changed_targets)
    changed_code = _replace_partition(source.code, "train", targets=changed_targets)
    changed_process = _replace_partition(
        source.process, "train", targets=changed_targets
    )
    changed_source = _rebind(
        source, code=changed_code, process=changed_process, text=changed_text
    )

    assert (
        prepare_qt_model_ready_inputs(changed_source).text_state
        == prepare_qt_model_ready_inputs(source).text_state
    )


def test_repeated_execution_is_identical() -> None:
    first = prepare_qt_model_ready_inputs(_source())
    repeated = prepare_qt_model_ready_inputs(_source())

    assert first == repeated
    assert first.to_dict() == repeated.to_dict()
    assert first.preparation_identity_digest == repeated.preparation_identity_digest


def test_malformed_or_missing_source_bindings_fail_closed() -> None:
    with pytest.raises(TypeError, match="QtModelInputAdaptationResult"):
        prepare_qt_model_ready_inputs(None)  # type: ignore[arg-type]

    source = _source()
    mismatched = _replace_partition(
        source.text,
        "validation",
        identifiers=("f" * 40, "e" * 40),
    )
    with pytest.raises(QtModelInputAdaptationError, match="identifier"):
        _rebind(source, text=mismatched)


def test_representation_policy_identity_is_frozen_and_validated() -> None:
    policy = QtTextRepresentationPolicy.create()
    result = prepare_qt_model_ready_inputs(_source(), policy)
    assert result.text_state.policy_digest == policy.policy_digest

    with pytest.raises(ValueError, match="frozen values"):
        replace(policy, maximum_features=10)
    with pytest.raises(ValueError, match="policy_digest"):
        replace(policy, policy_digest="0" * 64)


def test_empty_train_vocabulary_fails_closed() -> None:
    source = _source()
    text = _replace_partition(source.text, "train", messages=("x", "y", "z"))
    with pytest.raises(QtModelReadyPreparationError, match="empty vocabulary"):
        prepare_qt_model_ready_inputs(_rebind(source, text=text))


def test_result_rejects_audit_claiming_validation_fit() -> None:
    result = prepare_qt_model_ready_inputs(_source())
    values = result._identity_content()
    values["fit_audit"] = {
        **dict(result.fit_audit),
        "fit_partitions": ("train", "validation"),
    }
    with pytest.raises(ValueError, match="TRAIN-only"):
        QtModelReadyPreparation(
            **values,
            preparation_identity_digest=result.preparation_identity_digest,
        )
