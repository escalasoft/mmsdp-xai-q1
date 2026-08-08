"""Focused unit tests for deterministic candidate construction helpers."""

import subprocess

import pytest

from dataset.qt_candidate_construction import (
    QtCandidateConstructionError,
    QtCandidateConstructor,
    _GitReader,
    _parse_blame,
)
from dataset.qt_candidate_construction_contracts import QtCandidateConstructionPolicy
from dataset.scientific_candidate_contracts import ScientificCandidateAttributionRecord


def _attribution(identifier_seed: str, hunk: str, line: int):
    policy = QtCandidateConstructionPolicy.create().scientific_policy
    values = {
        "repository_snapshot_digest": "a" * 64,
        "fixing_commit": "e" * 40,
        "baseline_commit": "d" * 40,
        "issue_identifier": "QTBUG-1",
        "target_evidence_identifier": "evidence",
        "commit_issue_link_identifier": "link",
        "commit_issue_link_artifact_digest": "b" * 64,
        "diff_artifact_digest": "c" * 64,
        "hunk_identifier": hunk,
        "old_path": "src/a.cpp",
        "old_blob_identifier": "c" * 40,
        "deleted_preimage_line_number": line,
        "blamed_historical_commit": identifier_seed * 40,
        "attribution_method": policy.attribution_method,
        "policy_version": policy.policy_version,
        "policy_digest": policy.policy_digest,
    }
    return ScientificCandidateAttributionRecord(
        **values,
        attribution_identifier=ScientificCandidateAttributionRecord.calculate_identifier(
            **values
        ),
    )


def test_line_porcelain_parser_validates_exact_single_line_provenance() -> None:
    oid = "a" * 40
    parsed = _parse_blame(
        f"{oid} 7 7 1\nauthor A\nfilename src/a.cpp\n\treturn 1;\n", 7
    )
    assert (parsed.commit, parsed.original_line, parsed.content, parsed.boundary) == (
        oid,
        7,
        "return 1;",
        False,
    )
    boundary = _parse_blame(
        f"^{oid} 7 7 1\nboundary\nfilename src/a.cpp\n\treturn 1;\n", 7
    )
    assert boundary.boundary
    with pytest.raises(QtCandidateConstructionError, match="header"):
        _parse_blame(f"{oid} 8 8 1\nfilename src/a.cpp\n\tx\n", 7)
    with pytest.raises(QtCandidateConstructionError, match="incomplete"):
        _parse_blame(f"{oid} 7 7 1\nfilename src/a.cpp\n", 7)


def test_candidate_aggregation_is_canonical_deduplicated_and_three_level() -> None:
    policy = QtCandidateConstructionPolicy.create().scientific_policy
    first = _attribution("a", "hunk-1", 1)
    second = _attribution("a", "hunk-1", 2)
    values = QtCandidateConstructor._candidates((second, first, first), policy)
    assert len(values) == 4
    assert [item.candidate_identifier for item in values] == sorted(
        item.candidate_identifier for item in values
    )
    assert {item.aggregation_level.value for item in values} == {
        "line",
        "hunk",
        "commit",
    }
    commit = next(item for item in values if item.aggregation_level.value == "commit")
    assert commit.attribution_identifiers == tuple(
        sorted({first.attribution_identifier, second.attribution_identifier})
    )


def test_git_blame_invocation_is_argument_safe_and_deterministic(
    monkeypatch, tmp_path
) -> None:
    captured = {}

    def run(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(command, 0, "porcelain", "")

    monkeypatch.setattr(subprocess, "run", run)
    reader = _GitReader(tmp_path)
    code, output = reader.run(
        "blame",
        [
            "--line-porcelain",
            "-M",
            "-w",
            "-L",
            "7,7",
            "a" * 40,
            "--",
            "src/a.cpp",
        ],
    )
    assert (code, output) == (0, "porcelain")
    assert captured["command"] == [
        "git",
        "-c",
        "color.ui=false",
        "-c",
        "core.quotePath=false",
        "blame",
        "--line-porcelain",
        "-M",
        "-w",
        "-L",
        "7,7",
        "a" * 40,
        "--",
        "src/a.cpp",
    ]
    assert captured["kwargs"]["shell"] is False
    assert captured["kwargs"]["env"]["GIT_NO_REPLACE_OBJECTS"] == "1"


def test_existing_exclusion_contract_represents_unresolved_attribution() -> None:
    policy = QtCandidateConstructionPolicy.create().scientific_policy
    common = {
        "fixing_commit": "e" * 40,
        "baseline_commit": "d" * 40,
        "issue_identifier": "QTBUG-1",
        "target_evidence_identifier": "evidence",
        "hunk_identifier": "hunk",
        "old_path": "src/a.cpp",
        "old_blob_identifier": "c" * 40,
        "deleted_preimage_line_number": 7,
        "policy_version": policy.policy_version,
        "policy_digest": policy.policy_digest,
    }
    exclusion = QtCandidateConstructor._exclusion(
        "unresolved",
        "temporal-inconsistency",
        "historical-commit-not-reachable-from-baseline",
        common,
    )
    assert exclusion.disposition.value == "unresolved"
    assert exclusion.reason.value == "temporal-inconsistency"
    assert len(exclusion.exclusion_identifier) == 64
