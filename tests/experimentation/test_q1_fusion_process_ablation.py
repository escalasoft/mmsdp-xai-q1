import hashlib
import json
from pathlib import Path

import numpy as np

from experimentation.q1_fusion_process_ablation import (
    CONFIG_REL,
    PROCESS_INDEX,
    _nested_memberships,
    exact_two_sided_sign_test,
)

ROOT = Path(__file__).resolve().parents[2]
CONFIG = json.loads((ROOT / CONFIG_REL).read_text())


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rows(n: int = 36):
    return [
        {
            "project": "p",
            "commit_hash": f"{index:040x}",
            "git_committer_timestamp": f"{index:020d} +0000",
            "target": index % 2,
            "split": "train",
            "C": [index] * 6,
            "P": [index] * 4,
            "T": str(index),
        }
        for index in range(n)
    ]


def test_configuration_predeclares_candidates_and_keeps_test_sealed():
    assert CONFIG["sealed_partition"] == "test"
    assert CONFIG["development_partitions"] == ["train", "validation"]
    assert set(CONFIG["fixed_fusion_candidates"]) == {"C+T", "C+P+T"}
    assert len(CONFIG["fixed_fusion_candidates"]["C+T"]) == 3
    assert len(CONFIG["fixed_fusion_candidates"]["C+P+T"]) == 3
    assert CONFIG["paired_inference"]["family"] == "exact-two-sided-paired-sign-test"


def test_process_ablation_family_is_exact_and_has_no_target_proxies():
    family = CONFIG["process_ablation_family"]
    assert len(family) == 7
    assert set(family["P_full"]) == set(PROCESS_INDEX)
    assert all(values for values in family.values())
    assert not set(CONFIG["prohibited_predictors"]).intersection(
        feature for features in family.values() for feature in features
    )


def test_nested_predictions_are_strictly_out_of_time_and_disjoint():
    blocks = _nested_memberships(_rows(), CONFIG)
    assert len(blocks) == 3
    for block in blocks:
        fit_ids = {tuple(value) for value in block["fit_membership"]}
        prediction_ids = {tuple(value) for value in block["prediction_membership"]}
        assert fit_ids.isdisjoint(prediction_ids)
        fit = block["train"]
        prediction = block["prediction"]
        latest_fit = max(
            (row["git_committer_timestamp"], row["commit_hash"]) for row in fit
        )
        assert latest_fit < min(
            (row["git_committer_timestamp"], row["commit_hash"]) for row in prediction
        )


def test_ablation_does_not_change_labels_or_boundaries():
    rows = _rows()
    before = [(row["project"], row["commit_hash"], row["target"]) for row in rows]
    _nested_memberships(rows, CONFIG)
    after = [(row["project"], row["commit_hash"], row["target"]) for row in rows]
    assert before == after


def test_exact_sign_test_reports_small_origin_limit():
    result = exact_two_sided_sign_test([1, 2, 3, 4, 5])
    assert result["wins"] == 5
    assert result["valid_paired_origins"] == 5
    assert result["exact_two_sided_p_value"] == 0.0625
    assert result["supports_superiority_at_alpha_0_05"] is False


def test_historical_sprint34_memberships_are_frozen():
    path = ROOT / "audits/q1-modality-factorial/1.0.0/origin_memberships.json"
    assert _sha256(path) == CONFIG["origin_membership_sha256"]


def test_generated_artifacts_and_ledger_if_present():
    output = ROOT / "audits/q1-fusion-process-ablation/1.0.0"
    if not output.exists():
        return
    ledger = json.loads((output / "execution_ledger.json").read_text())
    assert ledger["TEST_predictive_scoring"] == 0
    assert ledger["TEST_based_model_selection"] == 0
    assert ledger["TEST_based_threshold_optimization"] == 0
    assert ledger["TEST_calibration_fitting"] == 0
    assert ledger["XAI_on_TEST"] == 0
    assert ledger["calibration_fits"] == 0
    assert ledger["threshold_optimizations"] == 0
    memberships = json.loads(
        (output / "nested_stacking_memberships.json").read_text()
    )["blocks"]
    assert len(memberships) == 15
    for block in memberships:
        assert set(map(tuple, block["fit_membership"])).isdisjoint(
            map(tuple, block["prediction_membership"])
        )
    states = json.loads(
        (output / "reproducibility_manifest.json").read_text()
    )["fitted_states"]
    assert len(states) == 5
    assert all(state["reload_prediction_equivalence"] for state in states)
    assert all(len(state["sha256"]) == 64 for state in states)
    comparisons = json.loads((output / "paired_inference.json").read_text())[
        "comparisons"
    ]
    assert comparisons
    assert all(item["valid_paired_origins"] == 5 for item in comparisons)
    assert all(np.isfinite(item["mean_signed_difference"]) for item in comparisons)
