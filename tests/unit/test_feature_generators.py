from dataclasses import FrozenInstanceError

import pytest

from feature_engineering import (
    FeatureEngineeringError,
    generate_code_features,
    generate_process_features,
    generate_text_features,
)


def test_code_features_are_deterministic_arithmetic() -> None:
    source = {
        "commit_hash": "abc",
        "lines_added": "7",
        "lines_deleted": "3",
        "changed_file_count": "2",
        "label": "must-not-be-read",
    }
    first = generate_code_features([source])
    second = generate_code_features([source])
    assert first == second
    assert first[0].lines_changed == 10
    assert first[0].changed_file_count == 2


@pytest.mark.parametrize("field", ["lines_added", "lines_deleted", "changed_file_count"])
def test_code_features_reject_invalid_counts(field) -> None:
    source = {
        "commit_hash": "abc",
        "lines_added": "1",
        "lines_deleted": "2",
        "changed_file_count": "1",
    }
    source[field] = "-1"
    with pytest.raises(FeatureEngineeringError):
        generate_code_features([source])


def test_process_features_use_only_current_record() -> None:
    source = {
        "commit_hash": "abc",
        "parent_commit_hashes": "p1 p2",
        "author_identifier": "person",
        "committer_identifier": "person",
    }
    feature = generate_process_features([source])[0]
    assert (feature.parent_count, feature.is_merge_commit) == (2, 1)
    assert feature.author_is_committer == 1


def test_process_features_allow_root_commit() -> None:
    source = {
        "commit_hash": "abc",
        "parent_commit_hashes": "",
        "author_identifier": "author",
        "committer_identifier": "committer",
    }
    feature = generate_process_features([source])[0]
    assert (feature.parent_count, feature.is_merge_commit) == (0, 0)
    assert feature.author_is_committer == 0


def test_text_features_are_rule_based_and_preserve_input() -> None:
    source = {"commit_hash": "abc", "commit_message": "Fix café\nwith care"}
    original = source.copy()
    feature = generate_text_features([source])[0]
    assert source == original
    assert feature.character_count == len(source["commit_message"])
    assert feature.word_count == 4
    assert feature.line_count == 2
    assert feature.non_whitespace_character_count == 15


def test_feature_contracts_are_immutable() -> None:
    feature = generate_text_features(
        [{"commit_hash": "abc", "commit_message": "message"}]
    )[0]
    with pytest.raises(FrozenInstanceError):
        feature.word_count = 99

