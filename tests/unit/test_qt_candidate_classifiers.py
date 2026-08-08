"""Unit tests for frozen Qt candidate classifiers."""

import pytest

from dataset.qt_candidate_classifiers import (
    QtCommentLineClassifier,
    QtFormattingOnlyClassifier,
)
from dataset.qt_candidate_construction_contracts import QtCandidateConstructionPolicy
from dataset.scientific_candidate_contracts import ScientificCandidateConstructionPolicy


def test_classifier_identities_match_the_approved_policy() -> None:
    assert QtCommentLineClassifier.identity_digest() == (
        "0aac48e6867d7fd5022028a9570a007ae87cfeef45f6a2aad957c2d6e83ca483"
    )
    assert QtFormattingOnlyClassifier.identity_digest() == (
        "9bd515bae7626e39e86874f0f6359f36bd8358a8948f747db63f6b90ec1deda2"
    )
    QtCommentLineClassifier.verify_identity(
        QtCommentLineClassifier.version, QtCommentLineClassifier.identity_digest()
    )
    with pytest.raises(ValueError, match="classifier identity mismatch"):
        QtCommentLineClassifier.verify_identity(
            QtCommentLineClassifier.version, "0" * 64
        )


def test_canonical_content_is_deterministic_and_binds_scientific_semantics() -> None:
    comment_first = QtCommentLineClassifier.canonical_scientific_content()
    comment_second = QtCommentLineClassifier.canonical_scientific_content()
    formatting_first = QtFormattingOnlyClassifier.canonical_scientific_content()
    formatting_second = QtFormattingOnlyClassifier.canonical_scientific_content()
    assert comment_first == comment_second
    assert formatting_first == formatting_second
    assert comment_first != QtCommentLineClassifier.version.encode("utf-8")
    assert formatting_first != QtFormattingOnlyClassifier.version.encode("utf-8")
    assert b'"block_open":"/*"' in comment_first
    assert b'"line":"//"' in comment_first
    assert b'"state_rule"' in comment_first
    assert b'"normalization_rule"' in formatting_first
    assert b'"equivalence_rule"' in formatting_first
    assert b'"U+3000"' in formatting_first
    assert QtCommentLineClassifier.identity_digest() == (
        QtCommentLineClassifier.identity_digest()
    )
    assert QtFormattingOnlyClassifier.identity_digest() == (
        QtFormattingOnlyClassifier.identity_digest()
    )


def test_incorrect_classifier_version_fails_fast() -> None:
    with pytest.raises(ValueError, match="classifier identity mismatch"):
        QtFormattingOnlyClassifier.verify_identity(
            "qt-formatting-only-classification-contract-incorrect",
            QtFormattingOnlyClassifier.identity_digest(),
        )


def test_corrected_policy_digest_is_reproducible_from_contract_content() -> None:
    first = QtCandidateConstructionPolicy.create().scientific_policy
    second = QtCandidateConstructionPolicy.create().scientific_policy
    content = first.to_dict()
    content.pop("metadata")
    content.pop("policy_digest")
    assert first.policy_digest == second.policy_digest
    assert (
        first.policy_digest
        == ScientificCandidateConstructionPolicy.calculate_digest(**content)
    )


def test_language_aware_comment_classification_preserves_code() -> None:
    lines = (
        "// comment",
        "int value = 1; // trailing",
        "/* block",
        " * continuation",
        " */",
        'const char *text = "// not a comment";',
        "   ",
    )
    assert QtCommentLineClassifier.comment_only_line_numbers(lines) == {
        1,
        3,
        4,
        5,
    }


def test_formatting_only_classifier_is_exact_after_whitespace_removal() -> None:
    assert QtFormattingOnlyClassifier.is_formatting_only(
        "if (ready) {", ("if(ready){",)
    )
    assert not QtFormattingOnlyClassifier.is_formatting_only(
        "return first;", ("return second;",)
    )
    assert not QtFormattingOnlyClassifier.is_formatting_only("  ", ("",))
