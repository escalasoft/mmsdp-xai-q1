"""Unit contracts for the commit-only scientific extraction stage."""

import dataclasses
import json
from pathlib import Path

import pytest

import extraction.qt_commit_extraction as extraction
from extraction.qt_commit_extraction import (
    QtCommitExtractionSpecification,
    QtCommitExtractor,
    ScientificCommitRecord,
)


def test_exact_public_api_and_stage_boundary() -> None:
    assert extraction.__all__ == [
        "QtCommitExtractionSpecification",
        "ScientificCommitRecord",
        "QtCommitExtractionResult",
        "QtCommitExtractor",
    ]
    prohibited = {
        "extract_issues",
        "extract_diffs",
        "construct_features",
        "construct_targets",
        "assemble_dataset",
        "train_model",
        "run_experiments",
    }
    assert prohibited.isdisjoint(dir(QtCommitExtractor))
    assert QtCommitExtractor.extractor_name == "qt-commit-extractor"


def test_specification_is_immutable_and_detaches_metadata() -> None:
    source = {"nested": ["value"]}
    specification = QtCommitExtractionSpecification("1.0.0", metadata=source)
    source["nested"].append("changed")
    assert specification.to_dict()["metadata"] == {"nested": ["value"]}
    with pytest.raises(dataclasses.FrozenInstanceError):
        specification.schema_version = "2.0.0"  # type: ignore[misc]


def test_only_one_explicit_ordering_policy_is_admissible() -> None:
    with pytest.raises(ValueError, match="ordering_policy"):
        QtCommitExtractionSpecification("1.0.0", ordering_policy="date-order")


def test_governed_configuration_matches_the_fixed_stage_policy() -> None:
    path = Path(__file__).parents[2] / "configs" / "qt_commit_extraction.json"
    specification = QtCommitExtractionSpecification(
        **json.loads(path.read_text(encoding="utf-8"))
    )
    assert specification.ordering_policy == "topological-oldest-first-v1"


def test_commit_record_is_frozen_and_contains_no_downstream_fields() -> None:
    assert ScientificCommitRecord.__dataclass_params__.frozen
    assert "__dict__" not in ScientificCommitRecord.__slots__
    names = set(ScientificCommitRecord.__dataclass_fields__)
    prohibited = {"issue", "diff", "feature", "target", "label", "dataset"}
    assert not any(term in name for name in names for term in prohibited)


def test_commit_record_defensively_freezes_parent_identifiers() -> None:
    parents = ["b" * 40]
    record = ScientificCommitRecord(
        commit_id="a" * 40,
        parent_ids=parents,  # type: ignore[arg-type]
        author_name="Author",
        author_email="author@example.invalid",
        authored_at="2001-01-01T00:00:00+00:00",
        committer_name="Committer",
        committer_email="committer@example.invalid",
        committed_at="2001-01-01T00:00:00+00:00",
        message="message\n",
    )
    parents.append("c" * 40)
    assert record.parent_ids == ("b" * 40,)
