import subprocess
from copy import deepcopy
from pathlib import Path

from evaluation.q1_final_test_identity_boundary_amendment import (
    CANONICAL_BOUNDARY,
    CANONICAL_DATASET,
    CANONICAL_MANIFEST,
    CLASSIFICATION,
    canonical_bytes,
    collect_evidence,
    decide,
    evaluate,
)

ROOT = Path(__file__).resolve().parents[2]


def test_repository_evidence_fails_closed_without_test_access():
    evidence = collect_evidence(ROOT)
    assert evidence["canonical"]["scientific_identity"] == CANONICAL_DATASET
    assert evidence["canonical"]["manifest_identity"] == CANONICAL_MANIFEST
    assert evidence["canonical"]["temporal_boundary_identity"] == CANONICAL_BOUNDARY
    assert evidence["historical_test"]["consumed"] is True
    assert evidence["post_sprint31_materialization_changes"] == []
    result = decide(evidence)
    assert result["classification"] == CLASSIFICATION
    assert result["authorization_amended"] is False
    assert result["access_count"] == {"before": 0, "during": 0, "after": 0}


def test_any_possible_later_materialization_is_ambiguous_not_selected():
    evidence = collect_evidence(ROOT)
    evidence = deepcopy(evidence)
    evidence["post_sprint31_materialization_changes"] = ["data/candidate"]
    result = decide(evidence)
    assert result["classification"] == "AMBIGUOUS_FINAL_TEST_IDENTITY"
    assert result["candidate_final_test_identity"] is None
    assert result["one_shot_test_access_authorized"] is False


def test_replay_is_deterministic():
    assert canonical_bytes(evaluate(ROOT)) == canonical_bytes(evaluate(ROOT))


def test_no_accepted_historical_file_modified():
    rows = subprocess.run(
        ["git", "diff", "--name-status", "9647eec872971b2b366fb4f21dca9ba6b27f7f23"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    assert all(row.startswith("A\t") for row in rows)
