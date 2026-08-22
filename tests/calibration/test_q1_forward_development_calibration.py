import hashlib
import json
from pathlib import Path

import numpy as np

from calibration.q1_forward_development_calibration import (
    CANDIDATES,
    CONFIG_REL,
    calibration_membership,
    reliability_bins,
)

ROOT = Path(__file__).resolve().parents[2]
CONFIG = json.loads((ROOT / CONFIG_REL).read_text())


def test_configuration_freezes_development_only_family_and_rule():
    assert CONFIG["status"] == "DEVELOPMENT_ONLY"
    assert CONFIG["sealed_partition"] == "test"
    assert tuple(CONFIG["calibration_candidates"]) == CANDIDATES
    assert CONFIG["metrics"]["ece_bin_edges"] == [index / 10 for index in range(11)]
    assert (
        CONFIG["decision_curve"]["policy"] == "READINESS_AUDIT_ONLY_NO_CURVE_EXECUTION"
    )
    assert CONFIG["selection_rule"][-1] == "candidate_order_UNCALIBRATED_PLATT_ISOTONIC"


def test_historical_origin_membership_is_immutable():
    path = ROOT / CONFIG["temporal_protocol"]["outer_membership_source"]
    assert (
        hashlib.sha256(path.read_bytes()).hexdigest()
        == CONFIG["temporal_protocol"]["outer_membership_sha256"]
    )


def test_fixed_reliability_bins_retain_empty_bins_and_rightmost_one():
    ece, bins = reliability_bins(np.asarray([0, 1, 1]), np.asarray([0.0, 0.15, 1.0]))
    assert np.isfinite(ece)
    assert len(bins) == 10
    assert bins[0]["support"] == 1
    assert bins[1]["support"] == 1
    assert bins[9]["support"] == 1 and bins[9]["right_inclusive"] is True
    assert bins[2]["support"] == 0 and bins[2]["mean_predicted_probability"] is None


def _rows(n, project="p"):
    return [
        {
            "project": project,
            "commit_hash": f"{index:040x}",
            "git_committer_timestamp": f"{index:020d} +0000",
            "target": index % 2,
        }
        for index in range(n)
    ]


def test_calibration_membership_is_forward_disjoint_and_deterministic():
    origin = {
        "origin_id": "O",
        "train": _rows(36),
        "evaluation": _rows(8, "q"),
        "frozen": {},
    }
    # Keep the same project in its next block and ensure unique identities.
    origin["evaluation"] = [
        {
            **row,
            "project": "p",
            "commit_hash": f"{100 + index:040x}",
            "git_committer_timestamp": f"{100 + index:020d} +0000",
        }
        for index, row in enumerate(origin["evaluation"])
    ]
    member = calibration_membership(origin, CONFIG)
    ids = [
        set((row["project"], row["commit_hash"]) for row in member[key])
        for key in ("base", "calibration", "evaluation")
    ]
    assert not ids[0] & ids[1] and not ids[0] & ids[2] and not ids[1] & ids[2]
    assert max(row["git_committer_timestamp"] for row in member["base"]) < min(
        row["git_committer_timestamp"] for row in member["calibration"]
    )
    assert max(row["git_committer_timestamp"] for row in member["calibration"]) < min(
        row["git_committer_timestamp"] for row in member["evaluation"]
    )


def test_no_prohibited_predictor_enters_frozen_ct_schema():
    used = {
        "changed_file_count",
        "files_added",
        "files_deleted",
        "files_modified",
        "files_other",
        "mode_change_count",
        "raw_commit_message",
    }
    assert not used.intersection(CONFIG["prohibited_predictors"])
    assert CONFIG["predictor"]["modalities"] == ["CODE", "TEXT"]


def test_generated_governance_and_reproducibility_if_present():
    output = ROOT / "audits/q1-forward-development-calibration/1.0.0"
    if not output.exists():
        return
    ledger = json.loads((output / "execution_ledger.json").read_text())
    for key in (
        "TEST_scoring",
        "TEST_predictive_scoring",
        "TEST_probability_loading",
        "TEST_calibration_fits",
        "TEST_threshold_optimization",
        "TEST_model_selection",
        "hyperparameter_searches",
        "continuous_fusion_weight_optimizations",
        "threshold_optimizations",
        "XAI_on_TEST",
    ):
        assert ledger[key] == 0
    results = json.loads((output / "calibration_results.json").read_text())
    assert len(results["rows"]) == 15
    assert {row["method"] for row in results["rows"]} == set(CANDIDATES)
    states = json.loads(
        (output / "calibration_reproducibility_manifest.json").read_text()
    )["fitted_states"]
    assert len(states) == 5 and all(
        item["reload_prediction_equivalence"] for item in states
    )
    readiness = json.loads((output / "decision_curve_readiness.json").read_text())
    assert readiness["actual_decision_curve_computed"] is False
    assert readiness["threshold_grid_selected"] is False
