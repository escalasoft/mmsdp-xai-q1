from __future__ import annotations

import gzip
import inspect
import json
from pathlib import Path

import pandas as pd

from dataset import apachejit_final_dataset_freeze as freeze

ROOT = Path(__file__).resolve().parents[2]
AUDIT_DIR = ROOT / "audits/q1-apachejit-final-dataset-freeze/1.0.0"


def _read_json(name: str) -> dict:
    return json.loads((AUDIT_DIR / name).read_text(encoding="utf-8"))


def _jsonl_count(name: str) -> int:
    with gzip.open(AUDIT_DIR / name, "rt", encoding="utf-8") as stream:
        return sum(1 for _ in stream)


def test_deterministic_gzip_jsonl(tmp_path: Path) -> None:
    rows = [{"z": 1, "a": "text"}, {"z": 2, "a": "more"}]
    first = tmp_path / "first.jsonl.gz"
    second = tmp_path / "second.jsonl.gz"
    freeze._write_jsonl_gz(first, rows)
    freeze._write_jsonl_gz(second, rows)
    assert first.read_bytes() == second.read_bytes()


def test_temporal_partition_is_forward_and_non_degenerate() -> None:
    rows = []
    for project in ("apache/a", "apache/b"):
        for position in range(220):
            rows.append(
                {
                    "project": project,
                    "commit_id": f"{position:040x}",
                    "timestamp_utc": pd.Timestamp(position, unit="s", tz="UTC"),
                    "buggy": position % 2 == 0,
                }
            )
    partitioned, summary = freeze._partition_rows(pd.DataFrame(rows))
    assert summary["support_rule"]["historical_800_300_400_screen_active"] is False
    assert all(
        row["all_required_blocks_have_both_classes"] for row in summary["projects"]
    )
    for _, project_rows in partitioned.groupby("project"):
        phase_order = project_rows["partition"].map(
            {"TRAIN": 0, "VALIDATION": 1, "T1": 2, "T2": 3}
        )
        assert phase_order.is_monotonic_increasing


def test_final_package_manifest_and_accounting() -> None:
    assert freeze.verify_manifest(AUDIT_DIR)
    eligibility = _read_json("final_project_eligibility.json")
    assert eligibility["candidate_count"] == 14
    assert eligibility["eligible_count"] == 14
    assert eligibility["ineligible_count"] == 0
    assert eligibility["unresolved_count"] == 0
    assert eligibility["pre_candidate_exclusions"] == ["apache/hadoop"]
    assert eligibility["predictive_performance_used"] is False
    assert all(
        all(row["eligibility_gates"].values())
        for row in eligibility["projects"]
        if row["final_state"] == "ELIGIBLE"
    )
    hadoop = next(
        row for row in eligibility["projects"] if row["project"] == "apache/hadoop"
    )
    assert hadoop["final_state"] == "INELIGIBLE"
    assert hadoop["positive_rows"] == 0


def test_final_eligibility_count_emerges_from_gates() -> None:
    assert "len(eligible) != 14" not in inspect.getsource(freeze.build_freeze)
    rows = []
    for index in range(14):
        gates = {f"E{number}": True for number in range(1, 16)}
        if index == 13:
            gates["E7"] = False
        state, failed, unresolved = freeze._candidate_outcome(gates)
        rows.append(
            {
                "project": f"apache/project-{index}",
                "candidate_48e_r1": True,
                "final_state": state,
                "failed_gates": failed,
                "unresolved_gates": unresolved,
                "family_group_identifier": f"apache/project-{index}",
                "temporal_feasibility": "PASS_FORWARD_ONLY",
            }
        )
    assert sum(row["final_state"] == "ELIGIBLE" for row in rows) == 13
    assert rows[-1]["final_state"] == "INELIGIBLE"
    assert rows[-1]["failed_gates"] == ["E7"]
    assert freeze._experimental_set_sufficiency(rows)["sufficient"] is True


def test_unresolved_candidates_are_not_promoted_or_forced() -> None:
    rows = []
    for index in range(14):
        gates = {f"E{number}": True for number in range(1, 16)}
        if index >= 10:
            gates["E2"] = None
        state, failed, unresolved = freeze._candidate_outcome(gates)
        rows.append(
            {
                "project": f"apache/project-{index}",
                "candidate_48e_r1": True,
                "final_state": state,
                "failed_gates": failed,
                "unresolved_gates": unresolved,
                "family_group_identifier": f"apache/project-{index}",
                "temporal_feasibility": "PASS_FORWARD_ONLY",
            }
        )
    assert sum(row["final_state"] == "ELIGIBLE" for row in rows) == 10
    assert sum(row["final_state"] == "UNRESOLVED" for row in rows) == 4
    assessment = freeze._experimental_set_sufficiency(rows)
    assert assessment["sufficient"] is True
    assert assessment["unresolved_candidate_count"] == 4


def test_final_payloads_have_exact_row_coverage() -> None:
    expected = 94_710
    for name in (
        "row_identity_provenance.jsonl.gz",
        "code_dataset.jsonl.gz",
        "process_dataset.jsonl.gz",
        "text_dataset.jsonl.gz",
        "temporal_partition_manifest.jsonl.gz",
    ):
        assert _jsonl_count(name) == expected
    resolution = _read_json("repository_sha_resolution.json")
    assert resolution["resolved_shas"] == expected
    assert resolution["unresolved_shas"] == 0
    assert resolution["unresolved_parents"] == 0
    assert resolution["timestamp_mismatches"] == 0


def test_modality_and_access_boundaries_are_frozen() -> None:
    dictionary = _read_json("modality_dictionary.json")
    allowed = {
        row["variable"]: row["modality"]
        for row in dictionary["variables"]
        if row["status"].startswith("ALLOWED")
    }
    assert {name: allowed[name] for name in freeze.CODE_VARIABLES} == {
        name: "CODE" for name in freeze.CODE_VARIABLES
    }
    assert {name: allowed[name] for name in freeze.PROCESS_VARIABLES} == {
        name: "PROCESS" for name in freeze.PROCESS_VARIABLES
    }
    assert allowed["raw_commit_message"] == "TEXT"
    assert dictionary["predictive_overlap_count"] == 0
    required_provenance = {
        "variable",
        "modality",
        "semantic_definition",
        "numeric_value_source",
        "prediction_time_information_boundary",
        "independent_reconstruction_status",
        "causal_validity_basis",
        "future_information_prohibited",
        "label_information_prohibited",
        "scientific_limitation",
    }
    assert all(
        required_provenance.issubset(row)
        for row in dictionary["variables"]
        if row["modality"] in {"CODE", "PROCESS", "TEXT"}
    )
    access = _read_json("test_access_contract.json")
    assert access["predictive_access_current"] == "DENY"
    assert access["T1_executed"] is False
    assert access["T2_executed"] is False
    ledger = _read_json("execution_ledger.json")
    assert {
        key: ledger[key]
        for key in (
            "model_training_count",
            "predictive_scoring_count",
            "calibration_fit_count",
            "test_predictive_access_count",
            "xai_execution_count",
        )
    } == {
        "model_training_count": 0,
        "predictive_scoring_count": 0,
        "calibration_fit_count": 0,
        "test_predictive_access_count": 0,
        "xai_execution_count": 0,
    }


def test_label_and_hadoop_family_semantics_are_preserved() -> None:
    labels = _read_json("label_construct_limitation.json")
    assert labels["label"] == "BENCHMARK_DEFINED_OBSERVED_LABEL"
    assert labels["verified_ground_truth_claimed"] is False
    assert labels["fixing_commit_equals_bug_inducing_commit"] is False
    grouping = _read_json("project_family_grouping.json")
    assert grouping["families"]["apache/hadoop-family"] == [
        "apache/hadoop",
        "apache/hadoop-hdfs",
        "apache/hadoop-mapreduce",
    ]
    cpdp = _read_json("cpdp_lopo_source_target_contract.json")
    assert cpdp["target_labels_for_fitting"] == "PROHIBITED"
    assert cpdp["hadoop_family_grouped"] is True


def test_feature_provenance_and_spot_check_are_precise() -> None:
    provenance = _read_json("feature_provenance_and_spot_check.json")
    assert provenance["CODE"]["numeric_value_source"] == (
        "APACHEJIT_V2_FROZEN_BENCHMARK_FEATURE"
    )
    assert provenance["CODE"]["full_independent_reconstruction"] is False
    assert provenance["CODE"]["spot_check"]["rows_checked"] == 14
    assert provenance["CODE"]["spot_check"]["all_exact"] is True
    assert provenance["PROCESS"]["independent_reconstruction_status"] == (
        "NOT_INDEPENDENTLY_REPRODUCED_IN_48F_R1"
    )
    assert provenance["TEXT"]["source"] == ("PRIMARY_GIT_COMMIT_OBJECT_RECONSTRUCTION")


def test_temporal_amendment_is_pre_performance_and_test_remains_closed() -> None:
    amendment = _read_json("temporal_protocol_amendment.json")
    assert amendment["ORIGINAL_THESIS_PLAN"] == {
        "TRAIN": 70,
        "VALIDATION": 15,
        "TEST": 15,
    }
    assert amendment["FINAL_EMPIRICAL_PROTOCOL"] == {
        "TRAIN": 60,
        "VALIDATION": 20,
        "TEST": 20,
    }
    assert amendment["TEST_INTERNAL_RELEASE"] == {
        "T1_TOTAL_DATA_PERCENTAGE_POINTS": 4,
        "T1_TEST_RESERVE_PERCENT": 20,
        "T2_TOTAL_DATA_PERCENTAGE_POINTS": 16,
        "T2_TEST_RESERVE_PERCENT": 80,
    }
    assert amendment["PROTOCOL_CHANGE_TIMING"] == ("BEFORE_PREDICTIVE_EXPERIMENTATION")
    assert amendment["PREDICTIVE_PERFORMANCE_USED_TO_CHANGE_SPLIT"] is False
    access = _read_json("test_access_contract.json")
    assert access["predictive_access_current"] == "DENY"
    assert access["T1_executed"] is False
    assert access["T2_executed"] is False
