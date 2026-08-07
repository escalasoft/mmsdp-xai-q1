"""Tests for the contract-only Qt candidate policy."""

from __future__ import annotations

import dataclasses
import inspect

from dataset import qt_candidate_construction_contracts as module
from dataset.qt_candidate_construction_contracts import (
    QtCandidateConstructionPolicy,
    QtCandidateConstructionSpecification,
)
from dataset.scientific_candidate_contracts import (
    ScientificCandidateConstructionSpecification,
)

SHA = "a" * 64


def test_exact_api_and_contract_only_surface() -> None:
    assert module.__all__ == [
        "QtCandidateConstructionPolicy",
        "QtCandidateConstructionSpecification",
    ]
    for kind in (QtCandidateConstructionPolicy, QtCandidateConstructionSpecification):
        assert dataclasses.is_dataclass(kind)
        assert kind.__dataclass_params__.frozen
        assert "__slots__" in vars(kind)
    public = {
        name
        for kind in (
            QtCandidateConstructionPolicy,
            QtCandidateConstructionSpecification,
        )
        for name, _ in inspect.getmembers(kind)
        if not name.startswith("_")
    }
    assert public.isdisjoint({"construct", "execute", "blame", "run", "assign"})


def test_qt_policy_freezes_all_required_scientific_decisions() -> None:
    policy = QtCandidateConstructionPolicy.create().scientific_policy
    assert policy.admissible_issue_types == ("Bug",)
    assert policy.admissible_issue_statuses == ("Closed", "Resolved")
    assert policy.admissible_issue_resolutions == ("Fixed",)
    assert policy.baseline_policy == "recorded-first-parent"
    assert policy.merge_fix_policy == "recorded-first-parent-baseline"
    assert policy.root_commit_policy == "excluded-no-parent-baseline"
    assert policy.follow_renames is True
    assert policy.follow_copies is False
    assert policy.whitespace_policy == "ignore-all-whitespace"
    assert policy.blank_line_policy == "exclude"
    assert policy.comment_line_policy == "exclude-language-aware"
    assert policy.comment_classifier_version == (
        "qt-comment-line-classification-contract-1.0.0"
    )
    assert len(policy.comment_classifier_digest) == 64
    assert policy.formatting_only_policy == "exclude-or-unresolved"
    assert policy.formatting_classifier_version == (
        "qt-formatting-only-classification-contract-1.0.0"
    )
    assert len(policy.formatting_classifier_digest) == 64
    assert policy.deletion_hunk_policy == "attribute-deleted-preimage-lines"
    assert policy.replacement_hunk_policy == "attribute-deleted-preimage-lines-only"
    assert policy.attribution_failure_policy == "record-unresolved-no-guess"


def test_qt_specification_binds_generic_contract_and_policy() -> None:
    policy = QtCandidateConstructionPolicy.create()
    values = {
        "schema_version": "1.0.0",
        "specification_version": "qt-candidate-specification-1.0.0",
        "repository_snapshot_digest": SHA,
        "commit_artifact_digest": SHA,
        "issue_artifact_digest": SHA,
        "commit_issue_link_artifact_digest": SHA,
        "target_evidence_artifact_digest": SHA,
        "diff_artifact_digest": SHA,
        "policy_digest": policy.scientific_policy.policy_digest,
    }
    scientific = ScientificCandidateConstructionSpecification(
        **values,
        specification_digest=(
            ScientificCandidateConstructionSpecification.calculate_digest(**values)
        ),
    )
    specification = QtCandidateConstructionSpecification(scientific, policy)
    assert specification.project_name == "qtbase"
    assert (
        specification.to_dict()["policy"]["scientific_policy"]["fixing_commit_policy"]
        == "matching-link-and-target-evidence-required"
    )


def test_module_has_no_git_network_model_feature_or_experiment_execution() -> None:
    source = inspect.getsource(module)
    forbidden = (
        "subprocess",
        "GitClient",
        "requests",
        "httpx",
        "sklearn",
        "feature_engineering",
        "experimentation",
    )
    assert all(value not in source for value in forbidden)
