from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pandas as pd

from dataset import apachejit_suitability_audit as audit

ROOT = Path(__file__).resolve().parents[2]
AUDIT_DIR = ROOT / "audits/q1-apachejit-v2-scientific-suitability/1.0.0"


def test_manifest_round_trip(tmp_path: Path) -> None:
    (tmp_path / "a.json").write_text('{"a":1}\n', encoding="utf-8")
    (tmp_path / "REPORT.md").write_text("report\n", encoding="utf-8")
    audit.write_manifest(tmp_path)
    assert audit.verify_manifest(tmp_path)
    (tmp_path / "a.json").write_text('{"a":2}\n', encoding="utf-8")
    assert not audit.verify_manifest(tmp_path)
    (tmp_path / "a.json").write_text('{"a":1}\n', encoding="utf-8")
    (tmp_path / "unlisted.json").write_text('{}\n', encoding="utf-8")
    assert not audit.verify_manifest(tmp_path)


def test_fail_closed_on_archive_identity(tmp_path: Path) -> None:
    archive = tmp_path / "wrong.zip"
    with zipfile.ZipFile(archive, "w") as package:
        package.writestr("readme.md", "not ApacheJIT")
    try:
        audit.build_audit(
            archive,
            tmp_path,
            tmp_path / "out",
            acquired_at="2026-08-31T00:00:00Z",
            starting_head="a" * 40,
            branch="test",
        )
    except ValueError as error:
        assert "SHA-256 mismatch" in str(error)
    else:
        raise AssertionError("wrong archive did not fail closed")


def test_project_summary_is_sorted_and_non_predictive() -> None:
    frame = pd.DataFrame(
        {
            "project": ["b", "a"],
            "commit_id": ["b" * 40, "a" * 40],
            "buggy": [True, False],
            "author_date": [2, 1],
            "year": [1970, 1970],
        }
    )
    rows = audit._project_summary(frame)
    assert [row["project"] for row in rows] == ["a", "b"]
    assert (
        audit.APACHEJIT_SUITABILITY_CLASSIFICATION
        == "PASS_WITH_LABEL_CONSTRUCT_LIMITATION"
    )
    assert audit.R1_CLASSIFICATION == "PASS_48E_R1_READY_FOR_FREEZE"

    eligible_row = {
        "project": "apache/example",
        "rows": 3,
        "positive": 1,
        "negative": 2,
        "valid_sha_count": 3,
        "missing_timestamp_count": 0,
        "utc_calendar_year_count": 3,
    }
    assert all(audit._candidate_eligibility_checks(eligible_row).values())
    eligible_row["positive"] = 0
    assert not audit._candidate_eligibility_checks(eligible_row)[
        "both_observed_classes_present"
    ]


def test_r1_modality_and_precedent_contracts_are_explicit() -> None:
    rows = audit._feature_contract_rows()
    assignment = {row["feature"]: row["final_modality"] for row in rows}
    assert len(assignment) == len(rows)
    assert {
        key: assignment[key] for key in ("la", "ld", "nf", "nd", "ns", "entropy")
    } == {key: "CODE" for key in ("la", "ld", "nf", "nd", "ns", "entropy")}
    assert {
        key: assignment[key]
        for key in ("ndev", "age", "nuc", "aexp", "arexp", "asexp")
    } == {
        key: "PROCESS" for key in ("ndev", "age", "nuc", "aexp", "arexp", "asexp")
    }
    assert assignment["raw_commit_message"] == "TEXT"
    assert all(
        set(
            (
                "feature",
                "semantic_definition",
                "information_source",
                "temporal_availability",
                "final_modality",
                "scientific_rationale",
                "leakage_status",
                "evidence_status",
            )
        ).issubset(row)
        for row in rows
    )

    studies = audit._precedent()
    assert studies
    assert all(
        study["peer_reviewed_status"] == "PEER_REVIEWED_VERIFIED"
        for study in studies
    )
    assert all(
        study["Q1_status"] == "Q1_UNVERIFIED"
        or (
            study["ranking_source"] != "NONE_FROZEN"
            and study["ranking_year"] == 2024
            and study["ranking_evidence"].startswith("https://")
        )
        for study in studies
    )
    serialized = json.dumps(audit._precedent())
    assert "VERIFIED_PRECEDENT_EXISTS" not in serialized
    assert all("predictive_task" in study for study in studies)
    graph_anonymization = next(
        study for study in studies if study["doi"] == "10.1007/s10664-024-10464-6"
    )
    assert graph_anonymization["CODE"] == "YES_CURRENT_CHANGE_METRICS_FROM_GIT_GRAPH"
    assert graph_anonymization["PROCESS"] == "YES"
    assert graph_anonymization["TEXT"] == "NO"
    assert graph_anonymization["actual_CPT"] == "NO"
    assert all(
        set(
            (
                "publication",
                "year",
                "venue",
                "peer_reviewed_status",
                "Q1_status",
                "ranking_source",
                "ranking_year",
                "CODE",
                "PROCESS",
                "TEXT",
                "actual_CPT",
                "fusion",
                "temporal_validation",
                "cross_project",
                "calibration",
                "XAI",
                "evidence_status",
            )
        ).issubset(study)
        for study in studies
    )


def test_generated_r1_package_preserves_scientific_closure() -> None:
    assert audit.verify_manifest(AUDIT_DIR)

    code = json.loads(
        (AUDIT_DIR / "apachejit_code_compatibility.json").read_text()
    )
    assert code["contract"] == (
        "derive only from the prediction commit and its direct parent"
    )

    eligibility = json.loads(
        (AUDIT_DIR / "apachejit_project_eligibility.json").read_text()
    )
    assert eligibility["stage"] == "CANDIDATE_ELIGIBILITY"
    assert eligibility["superseded_screen"]["active"] is False
    assert eligibility["superseded_screen"]["classification"] == (
        "PROVISIONAL_ENGINEERING_SCREENING_THRESHOLDS_NOT_SCIENTIFICALLY_VALIDATED"
    )
    assert eligibility["eligible_candidate_count"] == 14
    assert eligibility["final_dataset_eligibility"] == {
        "status": "UNRESOLVED_DEFERRED_TO_48F",
        "requirements": [
            "complete SHA and parent materialization",
            "row-level CODE/PROCESS/TEXT reconstruction",
            "frozen chronological TRAIN/VALIDATION/TEST partitions",
            "class support verified within every required partition and temporal fold",
            "LOPO/CPDP source-target independence verification",
        ],
        "final_eligible_project_count": 0,
        "zero_means_not_yet_determined": True,
    }
    assert all(
        row["final_dataset_eligibility"] == "UNRESOLVED_DEFERRED_TO_48F"
        for row in eligibility["projects"]
    )
    excluded = {
        row["project"]: row["exclusion_reasons"]
        for row in eligibility["projects"]
        if not row["performance_independent_eligible_candidate"]
    }
    assert excluded == {"apache/hadoop": ["both_observed_classes_present"]}

    labels = json.loads(
        (AUDIT_DIR / "apachejit_label_construct_audit.json").read_text()
    )
    assert labels["positive"] == "BENCHMARK_DEFINED_OBSERVED_LABEL"
    assert labels["negative"] == "BENCHMARK_DEFINED_OBSERVED_LABEL"
    assert labels["verified_ground_truth_claimed"] is False
    assert labels["full_reconstruction"] == "NOT_EXECUTED"

    ledger = json.loads(
        (AUDIT_DIR / "apachejit_execution_ledger.json").read_text()
    )
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
    decision = json.loads(
        (AUDIT_DIR / "apachejit_final_decision.json").read_text()
    )
    assert decision["classification"] == "PASS_48E_R1_READY_FOR_FREEZE"
    assert decision["test_access"] == "DENY"
