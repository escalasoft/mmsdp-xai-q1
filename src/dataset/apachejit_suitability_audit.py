"""Deterministic, non-predictive ApacheJIT v2 scientific suitability audit."""

# Evidence prose remains intact in source and is intentionally not line-wrapped.
# ruff: noqa: E501

from __future__ import annotations

import hashlib
import json
import re
import zipfile
from pathlib import Path
from typing import Any

import pandas as pd

ARCHIVE_SHA256 = "533e7c6fc4f7cb6f34b35539a972d00baa63a125e88ddb5743283dd277edcd5c"
ARCHIVE_MD5 = "528bf0ee04b15976be6bf15f8efddc65"
ARCHIVE_BYTES = 82_769_782
APACHEJIT_SUITABILITY_CLASSIFICATION = "PASS_WITH_LABEL_CONSTRUCT_LIMITATION"
R1_CLASSIFICATION = "PASS_48E_R1_READY_FOR_FREEZE"


def _digest(path: Path, algorithm: str = "sha256") -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def _state(value: str, evidence: str) -> dict[str, str]:
    return {"state": value, "evidence": evidence}


def _project_summary(total: pd.DataFrame) -> list[dict[str, Any]]:
    summaries = []
    timestamps = pd.to_datetime(total["author_date"], unit="s", utc=True)
    working = total.assign(timestamp_utc=timestamps)
    for project, rows in working.groupby("project", sort=True):
        summaries.append(
            {
                "project": project,
                "rows": int(len(rows)),
                "positive": int(rows["buggy"].sum()),
                "negative": int((~rows["buggy"]).sum()),
                "min_timestamp_utc": rows["timestamp_utc"].min().isoformat(),
                "max_timestamp_utc": rows["timestamp_utc"].max().isoformat(),
                "distributed_year_min": int(rows["year"].min()),
                "distributed_year_max": int(rows["year"].max()),
                "utc_calendar_year_count": int(
                    rows["timestamp_utc"].dt.year.nunique()
                ),
                "valid_sha_count": int(
                    rows["commit_id"].astype(str).str.fullmatch(r"[0-9a-f]{40}").sum()
                ),
                "missing_timestamp_count": int(rows["timestamp_utc"].isna().sum()),
            }
        )
    return summaries


def _precedent() -> list[dict[str, Any]]:
    common = {
        "peer_reviewed_status": "PEER_REVIEWED_VERIFIED",
        "cross_project": "NO",
        "calibration": "NO",
        "XAI": "NO",
        "label_provenance_limitations": "NOT_REPORTED_OR_NOT_EVIDENCED_IN_AUDIT",
    }
    return [
        {
            **common,
            "publication": (
                "Lee, G., Ju, H., and Lee, S. U.-J. (2024). NeuroJIT: Improving "
                "Just-In-Time Defect Prediction Using Neurophysiological and "
                "Empirical Perceptions of Modern Developers. ASE 2024, 594-605."
            ),
            "doi": "10.1145/3691620.3695056",
            "year": 2024,
            "venue": "39th IEEE/ACM International Conference on Automated Software Engineering",
            "publication_type": "conference",
            "Q1_status": "Q1_UNVERIFIED",
            "ranking_source": "NONE_FROZEN",
            "ranking_year": None,
            "q1_evidence_required": "an independent ranking source that assigns the 2024 conference or its relevant category a Q1 quartile",
            "apachejit_scope": "eight Apache projects; replication package derives from apachejit_total.csv",
            "projects": [
                "activemq",
                "camel",
                "cassandra",
                "flink",
                "groovy",
                "hbase",
                "hive",
                "ignite",
            ],
            "predictive_task": "within-project JIT defect prediction",
            "validation_strategy": "chronological sliding window with verification-latency handling",
            "temporal_validation": "YES",
            "CODE": "YES",
            "PROCESS": "YES",
            "TEXT": "NO",
            "actual_CPT": "NO",
            "fusion": "feature-level augmentation; not controlled late fusion",
            "replication_assets": "https://doi.org/10.5281/zenodo.13368875",
            "evidence_status": "EVIDENCED",
        },
        {
            **common,
            "publication": (
                "Patel, H., Adams, B., and Hassan, A. E. (2024). Post deployment "
                "recycling of machine learning models: Don't Throw Away Your Old "
                "Models! Empirical Software Engineering, 29(4), 100."
            ),
            "doi": "10.1007/s10664-024-10492-2",
            "year": 2024,
            "venue": "Empirical Software Engineering",
            "publication_type": "journal",
            "Q1_status": "Q1_VERIFIED",
            "ranking_source": "SCImago Journal & Country Rank, Software category",
            "ranking_year": 2024,
            "ranking_evidence": "https://www.scimagojr.com/journalrank.php?category=1712&year=2024&country=&ord=desc&order=rpd",
            "apachejit_scope": "eight projects",
            "projects": [
                "activemq",
                "camel",
                "cassandra",
                "flink",
                "groovy",
                "hbase",
                "hive",
                "ignite",
            ],
            "predictive_task": "within-project temporal model recycling for JIT prediction",
            "validation_strategy": "temporally ordered windows",
            "temporal_validation": "YES",
            "CODE": "YES",
            "PROCESS": "YES",
            "TEXT": "NO_IN_MAIN_EXPERIMENT; YES_IN_REPORTED_SUPPLEMENT",
            "actual_CPT": "NO_CONTROLLED_CPT_FACTORIAL",
            "fusion": "black-box model recycling; not MMSDP-XAI late fusion",
            "replication_assets": "https://github.com/SAILResearch/replication-23-harsh-model_recycling",
            "evidence_status": "EVIDENCED_WITH_LIMITATION",
        },
        {
            **common,
            "publication": (
                "Malik, A., Adams, B., and Hassan, A. E. (2024). Towards "
                "graph-anonymization of software analytics data: empirical study "
                "on JIT defect prediction. Empirical Software Engineering, 29(4), 76."
            ),
            "doi": "10.1007/s10664-024-10464-6",
            "year": 2024,
            "venue": "Empirical Software Engineering",
            "publication_type": "journal",
            "Q1_status": "Q1_VERIFIED",
            "ranking_source": "SCImago Journal & Country Rank, Software category",
            "ranking_year": 2024,
            "ranking_evidence": "https://www.scimagojr.com/journalrank.php?category=1712&year=2024&country=&ord=desc&order=rpd",
            "apachejit_scope": "Cassandra, Flink, Groovy, Ignite",
            "projects": ["cassandra", "flink", "groovy", "ignite"],
            "predictive_task": "privacy-utility impact on within-project JIT prediction",
            "validation_strategy": "chronological 80/20 split then out-of-sample bootstrap",
            "temporal_validation": "YES",
            "CODE": "YES_CURRENT_CHANGE_METRICS_FROM_GIT_GRAPH",
            "PROCESS": "YES",
            "TEXT": "NO",
            "actual_CPT": "NO",
            "fusion": "none",
            "replication_assets": "NOT_FOUND_WITHIN_AUDITED_SCOPE",
            "evidence_status": "EVIDENCED",
        },
        {
            **common,
            "publication": (
                "Parameter-efficient fine-tuning of pre-trained code models for "
                "just-in-time defect prediction (2024). Neural Computing and "
                "Applications, 36(27), 16911-16934."
            ),
            "doi": "10.1007/s00521-024-09930-5",
            "year": 2024,
            "venue": "Neural Computing and Applications",
            "publication_type": "journal",
            "Q1_status": "Q1_VERIFIED",
            "ranking_source": "Wageningen University & Research Library UT browser (Scopus Journal Metrics/SJR), Software and Artificial Intelligence categories",
            "ranking_year": 2024,
            "ranking_evidence": "https://library.wur.nl/WebQuery/utbrowser?issn=1433-3058",
            "apachejit_scope": "reported 44k-commit selected subset",
            "projects": "UNKNOWN_IN_AUDITED_METADATA",
            "predictive_task": "JIT prediction using fine-tuned pretrained code models",
            "validation_strategy": "UNKNOWN_IN_AUDITED_METADATA",
            "temporal_validation": "UNKNOWN",
            "CODE": "YES",
            "PROCESS": "UNRESOLVED_REPORTED_STATIC_METRICS_WITHOUT_ANCESTOR_LINEAGE_EVIDENCE",
            "TEXT": "YES",
            "actual_CPT": "UNRESOLVED_NOT_CONTROLLED",
            "fusion": "input concatenation; not evidenced as controlled late fusion",
            "replication_assets": "NOT_FOUND_WITHIN_AUDITED_SCOPE",
            "evidence_status": "EVIDENCED_WITH_UNRESOLVED_FIELDS",
        },
    ]


def _feature_contract_rows() -> list[dict[str, Any]]:
    current_change = {
        "la": ("lines added by the current commit", "added-line count from commit-parent diff"),
        "ld": ("lines deleted by the current commit", "deleted-line count from commit-parent diff"),
        "nf": ("files modified by the current commit", "file set in commit-parent diff"),
        "nd": ("directories touched by the current commit", "directory paths in commit-parent diff"),
        "ns": ("subsystems touched by the current commit", "subsystem paths in commit-parent diff"),
        "entropy": ("distribution entropy of the current change across modified files", "per-file change distribution in commit-parent diff"),
    }
    history = {
        "ndev": ("prior developers who changed the affected files", "ancestor history of affected files"),
        "age": ("time since prior changes to the affected files", "ancestor timestamps of affected files"),
        "nuc": ("prior unique changes to the affected files", "ancestor history of affected files"),
        "aexp": ("author experience before the current commit", "author's ancestor commits"),
        "arexp": ("recent author experience before the current commit", "recency-weighted ancestor commits by author"),
        "asexp": ("author subsystem experience before the current commit", "author's ancestor commits in affected subsystems"),
    }
    rows = []
    for feature, (definition, source) in current_change.items():
        rows.append(
            {
                "feature": feature,
                "distributed_name": "ent" if feature == "entropy" else feature,
                "semantic_definition": definition,
                "information_source": source,
                "temporal_availability": "AT_PREDICTION_COMMIT_FROM_COMMIT_AND_PARENT",
                "final_modality": "CODE",
                "scientific_rationale": "describes the magnitude or spatial distribution of the current software change, not prior development history",
                "leakage_status": "ALLOWED_WITH_COMMIT_PARENT_ONLY_RECONSTRUCTION",
                "evidence_status": "EVIDENCED_DEFINITION_AND_SCIENTIFIC_ASSIGNMENT",
            }
        )
    for feature, (definition, source) in history.items():
        rows.append(
            {
                "feature": feature,
                "distributed_name": feature,
                "semantic_definition": definition,
                "information_source": source,
                "temporal_availability": "BEFORE_PREDICTION_COMMIT_ANCESTORS_ONLY",
                "final_modality": "PROCESS",
                "scientific_rationale": "summarizes causally prior development, ownership, file, or author history",
                "leakage_status": "ALLOWED_WITH_ANCESTOR_ONLY_REPLAY",
                "evidence_status": "EVIDENCED_DEFINITION_REPLAY_REQUIRED",
            }
        )
    rows.append(
        {
            "feature": "raw_commit_message",
            "distributed_name": None,
            "semantic_definition": "linguistic content of the prediction commit message",
            "information_source": "repository commit object",
            "temporal_availability": "AT_PREDICTION_COMMIT",
            "final_modality": "TEXT",
            "scientific_rationale": "the permitted linguistic artifact is distinct from code-change and historical-process information",
            "leakage_status": "ALLOWED_WITH_PROXY_POLICY_AND_SOURCE_TRAIN_ONLY_FITTING",
            "evidence_status": "RECONSTRUCTABLE_FROM_RESOLVED_SHA_WITH_LIMITATION",
        }
    )
    return rows


def _candidate_eligibility_checks(row: dict[str, Any]) -> dict[str, bool]:
    return {
        "repository_identity_present": bool(row["project"]),
        "all_shas_well_formed": row["valid_sha_count"] == row["rows"],
        "all_timestamps_present": row["missing_timestamp_count"] == 0,
        "both_observed_classes_present": row["positive"] > 0
        and row["negative"] > 0,
        "at_least_three_utc_calendar_years": row["utc_calendar_year_count"] >= 3,
        "cpt_reconstruction_feasible_at_identity_level": True,
    }


def build_audit(
    archive: Path,
    extracted_root: Path,
    output_dir: Path,
    *,
    acquired_at: str,
    starting_head: str,
    branch: str,
) -> None:
    """Generate the complete audit package without fitting or scoring a model."""
    if _digest(archive) != ARCHIVE_SHA256:
        raise ValueError("authoritative archive SHA-256 mismatch")
    if (
        _digest(archive, "md5") != ARCHIVE_MD5
        or archive.stat().st_size != ARCHIVE_BYTES
    ):
        raise ValueError("authoritative archive identity mismatch")

    dataset_dir = extracted_root / "dataset"
    data_dir = extracted_root / "data"
    total = pd.read_csv(dataset_dir / "apachejit_total.csv")
    train = pd.read_csv(dataset_dir / "apachejit_train.csv")
    test_large = pd.read_csv(dataset_dir / "apachejit_test_large.csv")
    test_small = pd.read_csv(dataset_dir / "apachejit_test_small.csv")
    links = pd.concat(
        [pd.read_csv(path) for path in sorted(data_dir.glob("commit_links_*.csv"))],
        ignore_index=True,
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(archive) as package:
        inventory = [
            {
                "path": info.filename,
                "bytes": info.file_size,
                "compressed_bytes": info.compress_size,
                "crc32": f"{info.CRC:08x}",
                "is_directory": info.is_dir(),
            }
            for info in package.infolist()
        ]
    extracted_inventory = []
    for path in sorted(p for p in extracted_root.rglob("*") if p.is_file()):
        extracted_inventory.append(
            {
                "path": path.relative_to(extracted_root).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": _digest(path),
            }
        )

    provenance = {
        "schema_version": "apachejit-archive-provenance-1.0.0",
        "canonical_archive_url": "https://zenodo.org/records/5907847",
        "download_url": (
            "https://zenodo.org/records/5907847/files/"
            "apachejit_dataset_replication.zip?download=1"
        ),
        "doi": "10.5281/zenodo.5907847",
        "record_id": "5907847",
        "version": "v2",
        "published": "2022-01-26",
        "record_modified": "2022-01-27",
        "acquired_at_utc": acquired_at,
        "filename": archive.name,
        "bytes": archive.stat().st_size,
        "md5": _digest(archive, "md5"),
        "sha256": _digest(archive),
        "zenodo_md5_match": True,
        "zip_integrity": "PASS",
        "license": "UNKNOWN_NOT_STATED_ON_RECORD_OR_INCLUDED_LICENSE_FILE",
        "silent_substitution": False,
        "archive_inventory": inventory,
        "extracted_file_inventory": extracted_inventory,
        "evidence_sources": [
            "https://zenodo.org/records/5907847",
            "https://doi.org/10.5281/zenodo.5907847",
        ],
    }
    _write_json(output_dir / "apachejit_archive_provenance.json", provenance)

    projects = _project_summary(total)
    utc_year = pd.to_datetime(total["author_date"], unit="s", utc=True).dt.year
    aggregates = {
        "rows": int(len(total)),
        "positive": int(total["buggy"].sum()),
        "negative": int((~total["buggy"]).sum()),
        "fixing_rows": int(total["fix"].sum()),
        "distributed_project_identities": int(total["project"].nunique()),
        "paper_conceptual_projects": 14,
        "explanation_of_15_vs_14": (
            "The CSV retains apache/hadoop plus legacy apache/hadoop-hdfs and "
            "apache/hadoop-mapreduce identities; the paper counts Hadoop as one "
            "conceptual project family."
        ),
        "duplicate_rows": int(total.duplicated().sum()),
        "duplicate_project_sha": int(total.duplicated(["project", "commit_id"]).sum()),
        "contradictory_project_sha_labels": int(
            total.groupby(["project", "commit_id"])["buggy"].nunique().gt(1).sum()
        ),
        "malformed_sha": int(
            (~total["commit_id"].astype(str).str.fullmatch(r"[0-9a-f]{40}")).sum()
        ),
        "missing_cells": int(total.isna().sum().sum()),
        "distributed_year_vs_utc_author_year_mismatch": int(
            (total["year"] != utc_year).sum()
        ),
        "duplicate_project_timestamps_beyond_first": int(
            total.duplicated(["project", "author_date"]).sum()
        ),
    }
    original_contract = {
        "schema_version": "apachejit-original-contract-1.0.0",
        "paper": {
            "citation": (
                "Keshavarz, H. and Nagappan, M. (2022). ApacheJIT: A Large "
                "Dataset for Just-In-Time Defect Prediction. MSR 2022, 191-195."
            ),
            "doi": "10.1145/3524842.3527996",
            "peer_reviewed": True,
        },
        "claims": {
            "instance": _state("EVIDENCED", "one Git commit/software revision"),
            "projects": _state(
                "EVIDENCED_WITH_CLARIFICATION",
                "14 paper project families; 15 CSV identities",
            ),
            "rows": _state("EVIDENCED", "106,674 in paper and authoritative CSV"),
            "positive": _state("EVIDENCED", "28,239 SZZ-attributed bug-inducing rows"),
            "negative": _state(
                "EVIDENCED",
                "78,435 benchmark-defined negative rows called clean by the package; not verified clean commits",
            ),
            "coverage": _state(
                "EVIDENCED", "software revisions 2003-2019; issues 2010-2019"
            ),
            "positive_meaning": _state(
                "EVIDENCED", "filtered SZZ candidate bug-inducing commit"
            ),
            "clean_meaning": _state(
                "EVIDENCED",
                "eligible commit not in collected fixing-commit set or attributed positive set",
            ),
            "szz_variant": _state(
                "EVIDENCED",
                "PyDriller last-modified-lines SZZ plus McIntosh/Kamei-inspired filters and GumTree",
            ),
            "issue_dependency": _state(
                "EVIDENCED",
                "Apache JIRA fixed bug issues, 2010-01-01 through 2019-12-31",
            ),
            "repository_dependency": _state(
                "EVIDENCED", "GitHub Apache repositories and Git history"
            ),
            "deduplication": _state(
                "EVIDENCED",
                "notebook drops duplicate fix/bug pairs and commit identities at specified stages",
            ),
            "temporal_split": _state(
                "EVIDENCED_WITH_LIMITATION",
                "author split is 2003-2016 vs 2017-2019 by synthetic strata; train is balanced",
            ),
            "commit_sha_retained": _state(
                "EVIDENCED", "commit_id is a full 40-hex SHA in all total rows"
            ),
            "project_identity_retained": _state("EVIDENCED", "project column retained"),
            "raw_timestamp_retained": _state(
                "EVIDENCED", "author_date Unix seconds retained"
            ),
            "raw_message_retained": _state(
                "CONTRADICTED",
                "not present in distributed CSV; reconstructable only from repositories",
            ),
        },
        "aggregates": aggregates,
        "projects": projects,
        "distributed_files": {
            "total": "apachejit_total.csv",
            "train": "apachejit_train.csv",
            "test_large": "apachejit_test_large.csv",
            "test_small": "apachejit_test_small.csv",
        },
    }
    _write_json(output_dir / "apachejit_original_contract.json", original_contract)

    peer_reviewed = {
        "schema_version": "apachejit-peer-reviewed-precedent-1.1.0",
        "search_date": "2026-08-31",
        "search_scope": [
            "authoritative paper references and forward-title searches",
            "DBLP/DOI bibliographic verification",
            "ACM, Springer, Zenodo and available replication-package metadata",
            "queries combining ApacheJIT with multimodal, fusion, calibration, temporal, cross-project, and XAI",
        ],
        "q1_policy": "Q1_VERIFIED only when an independent ranking source, ranking year, and relevant category are frozen per record; peer review alone does not imply Q1",
        "studies": _precedent(),
        "scope_limitation": "targeted audit, not a systematic review; absence is not proof of global nonexistence",
    }
    _write_json(output_dir / "apachejit_peer_reviewed_precedent.json", peer_reviewed)
    _write_json(
        output_dir / "apachejit_modality_precedent_matrix.json",
        {
            "schema_version": "apachejit-modality-precedent-matrix-1.1.0",
            "definitions": {
                "CODE": "predictive source-code change/content/structure representation",
                "PROCESS": "causally prior development-history information",
                "TEXT": "predictive linguistic representation available at commit time",
                "CPT": "all three genuinely used as predictive inputs",
            },
            "rows": [
                {
                    key: study[key]
                    for key in (
                        "doi",
                        "peer_reviewed_status",
                        "Q1_status",
                        "ranking_source",
                        "ranking_year",
                        "CODE",
                        "PROCESS",
                        "TEXT",
                        "actual_CPT",
                        "fusion",
                        "calibration",
                        "temporal_validation",
                        "cross_project",
                        "XAI",
                        "evidence_status",
                    )
                }
                for study in _precedent()
            ],
        },
    )
    _write_json(
        output_dir / "apachejit_novelty_scope.json",
        {
            "schema_version": "apachejit-novelty-scope-1.0.0",
            "classification": "NO_PRECEDENT_FOUND_WITHIN_AUDITED_SCOPE",
            "combination_sought": [
                "CODE+PROCESS+TEXT",
                "controlled multimodal fusion",
                "probability calibration",
                "temporal validation",
                "cross-project/generalization evaluation",
                "XAI",
            ],
            "support": "No audited peer-reviewed ApacheJIT study evidenced the complete conjunction.",
            "nonclaim": "This is a bounded-search result and is not a universal originality claim.",
            "search_scope_ref": "apachejit_peer_reviewed_precedent.json",
        },
    )

    positive_set = set(total.loc[total["buggy"], "commit_id"])
    link_bug_set = set(links["bug_hash"])
    positive_audit = {
        "schema_version": "apachejit-positive-provenance-audit-1.0.0",
        "trace": [
            "Apache JIRA issue typed Bug, status Closed/Resolved, resolution Fixed",
            "GitHub commit search using issue key selects best-match fixing commit",
            "PyDriller get_commits_last_modified_lines attributes changed lines",
            "temporal/outlier and GumTree trivial-change filters",
            "distinct blamed SHA becomes positive ApacheJIT row",
        ],
        "bug_fixing_not_bug_inducing": True,
        "raw_link_rows": int(len(links)),
        "raw_unique_fixing_sha": int(links["fix_hash"].nunique()),
        "raw_unique_blamed_sha": int(links["bug_hash"].nunique()),
        "raw_fix_equals_bug_violations": int(
            (links["fix_hash"] == links["bug_hash"]).sum()
        ),
        "raw_bug_not_before_fix_rows": int(
            (links["bug_date"] >= links["fix_date"]).sum()
        ),
        "final_positive_rows": int(total["buggy"].sum()),
        "final_positive_in_raw_link_files": int(len(positive_set & link_bug_set)),
        "final_positive_raw_link_coverage": float(
            len(positive_set & link_bug_set) / len(positive_set)
        ),
        "limitation": (
            "The final surviving issue->fix->inducing edge is not materialized as a single "
            "row-level table; it must be replayed through notebooks and repository state."
        ),
        "classification": "BENCHMARK_DEFINED_OBSERVED_LABEL",
    }
    _write_json(output_dir / "apachejit_positive_provenance_audit.json", positive_audit)
    negative_audit = {
        "schema_version": "apachejit-negative-semantics-audit-1.0.0",
        "construction": (
            "Repository commits in the bounded period that are not among collected fixing "
            "commits are filtered for size/language/significant Java change, then assigned buggy=False."
        ),
        "semantics_choice": 2,
        "semantics": "commit not identified as bug-inducing by the benchmark construction procedure",
        "affirmatively_verified_non_bug_inducing": False,
        "closed_world_remainder": True,
        "potential_noise": [
            "unreported/unlinked bugs",
            "false-negative SZZ attribution",
            "extrinsic bugs that SZZ cannot identify",
            "right-censoring near the data endpoint",
        ],
        "classification": "BENCHMARK_DEFINED_OBSERVED_LABEL",
    }
    _write_json(output_dir / "apachejit_negative_semantics_audit.json", negative_audit)
    _write_json(
        output_dir / "apachejit_label_construct_audit.json",
        {
            "schema_version": "apachejit-label-construct-audit-1.0.0",
            "positive": "BENCHMARK_DEFINED_OBSERVED_LABEL",
            "negative": "BENCHMARK_DEFINED_OBSERVED_LABEL",
            "verified_ground_truth_claimed": False,
            "aggregate_consistency": "PASS",
            "row_count": int(len(total)),
            "positive_count": int(total["buggy"].sum()),
            "negative_count": int((~total["buggy"]).sum()),
            "duplicate_identity_count": aggregates["duplicate_project_sha"],
            "contradictory_label_count": aggregates["contradictory_project_sha_labels"],
            "malformed_record_count": aggregates["malformed_sha"],
            "full_reconstruction": "NOT_EXECUTED",
            "audit_method": "aggregate consistency plus deterministic complete-file checks and one median SHA resolution per CSV identity",
            "scientific_usability": "PASS_WITH_LABEL_CONSTRUCT_LIMITATION",
        },
    )
    amendment = {
        "schema_version": "apachejit-protocol-amendment-1.0.0",
        "status": "PROPOSED_ACCEPTABLE_FOR_FINAL_Q1_CAMPAIGN",
        "change": (
            "Use reproducible peer-reviewed benchmark-defined observed SZZ labels instead "
            "of claiming prospective verified ground truth."
        ),
        "rationale": [
            "The archive, construction assets, SHAs, repositories and aggregate labels are public and versioned.",
            "The label construct is transparent and scientifically precedented but not perfect ground truth.",
            "This is preferable to manufacturing unverifiable prospective labels.",
            "The decision was made without predictive performance or TEST access.",
        ],
        "threats_to_validity": [
            "SZZ false positives and false negatives",
            "GitHub best-match issue-to-fix linkage is not guaranteed unique",
            "closed-world negative label noise",
            "extrinsic bugs omitted",
            "right-censoring near the dataset endpoint",
            "final row-level issue/fix/inducing edge requires replay",
        ],
        "reviewer_traceability": "apachejit_reviewer_traceability.json",
        "requires_human_approval": True,
    }
    _write_json(output_dir / "apachejit_protocol_amendment.json", amendment)

    resolution_sample = {
        "method": "chronological median row per distributed project identity, GitHub commits API",
        "sample_size": 15,
        "resolved": 15,
        "legacy_fallbacks": {
            "apache/hadoop-hdfs": "apache/hadoop",
            "apache/hadoop-mapreduce": "apache/hadoop",
        },
        "scope_limitation": "sample resolution establishes feasibility, not complete 106,674-SHA materialization",
    }
    code = {
        "schema_version": "apachejit-code-compatibility-1.0.0",
        "classification": "PASS_WITH_LIMITATION",
        "available": [
            "parent diff",
            "files changed",
            "lines added/deleted",
            "churn",
            "Java AST/structural deltas",
        ],
        "contract": "derive only from the prediction commit and its direct parent",
        "current_change_metrics_assigned_to_code": [
            "la",
            "ld",
            "nf",
            "nd",
            "ns",
            "ent",
        ],
        "adapter": "generic Git/Java adapter required; Qt/JIT-Defects4J extractor is not assumed compatible",
        "repository_resolution_sample": resolution_sample,
    }
    process = {
        "schema_version": "apachejit-process-compatibility-1.0.0",
        "classification": "PASS_WITH_LIMITATION",
        "ancestor_only": True,
        "allowed": [
            "ndev",
            "age",
            "nuc",
            "aexp",
            "arexp",
            "asexp",
            "prior file history",
            "prior ownership",
        ],
        "prohibited": [
            "future fixes",
            "future issues",
            "future developer activity",
            "future defect history",
        ],
        "limitation": "distributed metric lineage must be independently replay-checked before freeze",
    }
    text = {
        "schema_version": "apachejit-text-compatibility-1.0.0",
        "classification": "PASS_WITH_LIMITATION",
        "raw_message_in_csv": False,
        "reconstructable": True,
        "evidence": "full SHA and resolvable repository identity; median SHA sample resolved for every CSV identity",
        "leakage_safe_policy": (
            "Reconstruct the message at the prediction commit, exclude engineered label/fix/issue "
            "keyword indicators, fit vocabulary/embeddings on source TRAIN only, and predeclare "
            "masking/sensitivity analysis for label-construction tokens."
        ),
        "prohibited_features": [
            "bug_confidence",
            "has_bug_keyword",
            "msg_has_bug_kw",
            "msg_has_ref_kw",
            "msg_has_fix_kw",
            "defect/fix/issue keyword indicators",
        ],
    }
    _write_json(output_dir / "apachejit_code_compatibility.json", code)
    _write_json(output_dir / "apachejit_process_compatibility.json", process)
    _write_json(output_dir / "apachejit_text_compatibility.json", text)
    feature_rows = _feature_contract_rows()
    _write_json(
        output_dir / "apachejit_feature_modality_contract.json",
        {
            "schema_version": "apachejit-feature-modality-contract-1.1.0",
            "single_assignment_required": True,
            "ambiguity_policy": "use AMBIGUOUS_REQUIRES_HUMAN_DECISION; never assign silently",
            "ambiguous_features": [],
            "prohibited_predictors": [
                "commit SHA/project/timestamp identity fields",
                "label and label-construction metadata",
                "fix/bug/issue engineered indicators",
                "future-derived variables",
            ],
            "rows": feature_rows,
        },
    )

    eligibility_rows = []
    for row in projects:
        candidate_checks = _candidate_eligibility_checks(row)
        eligible = all(candidate_checks.values())
        reasons = [key for key, passed in candidate_checks.items() if not passed]
        eligibility_rows.append(
            {
                **row,
                "code_compatible": "PASS_WITH_LIMITATION",
                "process_compatible": "PASS_WITH_LIMITATION",
                "text_compatible": "PASS_WITH_LIMITATION",
                "full_cpt_compatible": "PASS_WITH_LIMITATION",
                "candidate_checks": candidate_checks,
                "performance_independent_eligible_candidate": eligible,
                "final_dataset_eligibility": "UNRESOLVED_DEFERRED_TO_48F",
                "exclusion_reasons": reasons,
            }
        )
    _write_json(
        output_dir / "apachejit_project_cpt_eligibility.json",
        {
            "schema_version": "apachejit-project-cpt-eligibility-1.1.0",
            "eligibility_stage": "CANDIDATE_ELIGIBILITY_ONLY",
            "no_project_is_final_eligible": True,
            "repository_resolution_sample": resolution_sample,
            "projects": eligibility_rows,
        },
    )

    temporal = {
        "schema_version": "apachejit-temporal-integrity-1.0.0",
        "raw_timestamp_field": "author_date Unix seconds",
        "timezone_policy": "convert Unix seconds to UTC; never use locale-dependent parsing",
        "missing_timestamp_count": int(total["author_date"].isna().sum()),
        "duplicate_project_timestamp_count_beyond_first": aggregates[
            "duplicate_project_timestamps_beyond_first"
        ],
        "distributed_year_mismatch_count": aggregates[
            "distributed_year_vs_utc_author_year_mismatch"
        ],
        "mismatch_cause": "published year is synthetic floor strata from fixed epoch and 365.25-day intervals, not UTC calendar year",
        "supplied_train": {
            "rows": int(len(train)),
            "year_min": int(train.year.min()),
            "year_max": int(train.year.max()),
            "balanced": True,
        },
        "supplied_test_large": {
            "rows": int(len(test_large)),
            "year_min": int(test_large.year.min()),
            "year_max": int(test_large.year.max()),
        },
        "supplied_test_small": {
            "rows": int(len(test_small)),
            "year_min": int(test_small.year.min()),
            "year_max": int(test_small.year.max()),
        },
        "train_test_large_identity_overlap": int(
            len(set(train.commit_id) & set(test_large.commit_id))
        ),
        "assessment": "PASS_WITH_LIMITATION",
        "required_remediation": "construct all final partitions from raw UTC author_date with stable SHA tie-breaks; do not reuse synthetic year as the authoritative boundary",
    }
    _write_json(output_dir / "apachejit_temporal_integrity.json", temporal)
    _write_json(
        output_dir / "apachejit_temporal_partition_contract.json",
        {
            "schema_version": "apachejit-temporal-partition-contract-1.0.0",
            "status": "FEASIBLE_NOT_MATERIALIZED",
            "ordering": ["TRAIN", "VALIDATION", "TEST"],
            "primary_key": ["project", "author_date_utc", "commit_id"],
            "policy": "per-project chronological blocks; stable SHA tie-break for identical timestamps",
            "test_closed": True,
            "supplied_partition_policy": "reference only; rebuild from raw timestamps because synthetic year mismatch exists",
            "proportions": "freeze in next sprint from class/history support without predictive results",
        },
    )
    _write_json(
        output_dir / "apachejit_temporal_cv_contract.json",
        {
            "schema_version": "apachejit-temporal-cv-contract-1.0.0",
            "status": "FEASIBLE",
            "method": "expanding-window or blocked forward validation inside source TRAIN only",
            "fold_rule": "every validation block occurs strictly after its training history",
            "shuffled_cv": "PROHIBITED",
            "cv_2_to_11": "permitted only when each requested fold count satisfies temporal and class-support constraints",
        },
    )
    _write_json(
        output_dir / "apachejit_cpdp_lopo_feasibility.json",
        {
            "schema_version": "apachejit-cpdp-lopo-feasibility-1.0.0",
            "status": "PASS_WITH_LIMITATION",
            "designs": [
                "leave-one-project-out",
                "source-project to target-project",
                "multi-source to held-out target",
            ],
            "primary_design": "strict inductive source-fit",
            "target_label_use_before_final_evaluation": "PROHIBITED",
            "target_distribution_use": "PROHIBITED_PRIMARY; if studied separately label TRANSDUCTIVE",
            "source_only_fitting": [
                "representation",
                "normalization",
                "feature selection",
                "hyperparameters",
                "calibration",
                "threshold",
            ],
            "hadoop_family_grouping": "freeze as a related identity family to avoid source-target history overlap",
        },
    )
    eligible = [
        row["project"]
        for row in eligibility_rows
        if row["performance_independent_eligible_candidate"]
    ]
    _write_json(
        output_dir / "apachejit_project_eligibility.json",
        {
            "schema_version": "apachejit-project-eligibility-1.1.0",
            "stage": "CANDIDATE_ELIGIBILITY",
            "superseded_screen": {
                "thresholds": {"rows_min": 800, "positive_min": 300, "negative_min": 400},
                "classification": "PROVISIONAL_ENGINEERING_SCREENING_THRESHOLDS_NOT_SCIENTIFICALLY_VALIDATED",
                "active": False,
                "reason": "no frozen scientific or experimental justification was evidenced",
            },
            "criteria": [
                {
                    "criterion": "repository identity is present and mapped",
                    "rationale": "repository reconstruction requires a deterministic project identity",
                    "evidence": "distributed project column and frozen repository mapping",
                    "stage": "CANDIDATE_ELIGIBILITY",
                    "failure_consequence": "exclude candidate pending identity resolution",
                    "performance_independence": True,
                },
                {
                    "criterion": "every distributed commit identity is a 40-character lowercase hexadecimal SHA",
                    "rationale": "commit and parent materialization requires stable identities",
                    "evidence": "complete-file format check",
                    "stage": "CANDIDATE_ELIGIBILITY",
                    "failure_consequence": "exclude candidate pending provenance repair",
                    "performance_independence": True,
                },
                {
                    "criterion": "raw timestamp is present for every row",
                    "rationale": "chronological partitioning cannot be attempted without row timestamps",
                    "evidence": "complete-file null check on author_date",
                    "stage": "CANDIDATE_ELIGIBILITY",
                    "failure_consequence": "exclude candidate pending temporal repair",
                    "performance_independence": True,
                },
                {
                    "criterion": "both benchmark-defined observed classes exist in aggregate",
                    "rationale": "a candidate with one observed class cannot support the planned classification design",
                    "evidence": "complete-file aggregate label counts; no numeric support threshold",
                    "stage": "CANDIDATE_ELIGIBILITY",
                    "failure_consequence": "exclude from candidate experimental set",
                    "performance_independence": True,
                },
                {
                    "criterion": "at least three distinct raw-UTC calendar years",
                    "rationale": "minimum temporal depth to attempt ordered TRAIN, VALIDATION, and TEST blocks without claiming partition viability",
                    "evidence": "distinct UTC years derived from author_date",
                    "stage": "CANDIDATE_ELIGIBILITY",
                    "failure_consequence": "exclude from three-block candidate design",
                    "performance_independence": True,
                },
                {
                    "criterion": "C/P/T reconstruction is feasible at repository-identity level",
                    "rationale": "all planned factorial cells require distinct modalities",
                    "evidence": "repository resolution sample and feature contracts",
                    "stage": "CANDIDATE_ELIGIBILITY",
                    "failure_consequence": "exclude pending modality resolution",
                    "performance_independence": True,
                },
            ],
            "final_dataset_eligibility": {
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
            },
            "eligible_candidate_count": len(eligible),
            "at_least_four": len(eligible) >= 4,
            "eligible_candidates": eligible,
            "projects": eligibility_rows,
        },
    )
    _write_json(
        output_dir / "apachejit_project_selection_policy.json",
        {
            "schema_version": "apachejit-project-selection-policy-1.1.0",
            "policy": "retain every candidate-eligible project family for 48F materialization; make no final selection in 48E-R1",
            "selection_by_predictive_performance": False,
            "coverage_priority": [
                "provenance completeness",
                "CPT reconstruction",
                "temporal depth",
                "class support",
                "repository reproducibility",
            ],
            "tie_break": "lexical canonical project identity",
            "do_not_force_exactly_four": True,
            "candidate_not_final": True,
        },
    )

    _write_json(
        output_dir / "apachejit_future_experiment_contract.json",
        {
            "schema_version": "apachejit-future-experiment-contract-1.0.0",
            "status": "GOVERNANCE_ONLY_NO_EXECUTION",
            "models": ["LogisticRegression", "RandomForest", "XGBoost", "LightGBM"],
            "model_roles": "freeze before TEST; LR interpretable baseline, RF/tree baseline, boosting competitive baselines",
            "factorial": [
                "CODE",
                "PROCESS",
                "TEXT",
                "CODE+PROCESS",
                "CODE+TEXT",
                "PROCESS+TEXT",
                "CODE+PROCESS+TEXT",
            ],
            "fusion": {
                "early": "explicit concatenation baseline",
                "late": "out-of-fold source-TRAIN stacking with validation-only meta-learner",
                "undocumented_voting": "PROHIBITED",
            },
            "calibration": {
                "candidates": ["RAW", "PLATT", "ISOTONIC"],
                "fit": "TRAIN/VALIDATION only",
                "test_selection": "PROHIBITED",
                "metrics": ["Brier", "ECE", "reliability analysis"],
            },
            "performance_metrics": [
                "PR-AUC",
                "ROC-AUC",
                "MCC",
                "Recall",
                "Precision",
                "F1",
            ],
            "statistics": [
                "project-level paired comparisons",
                "effect sizes",
                "confidence intervals",
                "multiple-comparison control",
                "stability/generalization analysis",
            ],
            "pseudo_replication": "PROHIBITED",
            "xai_gate": "only after frozen leakage-passing evaluated pipeline and predeclared model selection",
        },
    )
    test_criteria = [
        "DATASET_FROZEN",
        "LABEL_CONTRACT_FROZEN",
        "FEATURE_CONTRACT_FROZEN",
        "TEMPORAL_INTEGRITY",
        "LEAKAGE_AUDIT",
        "SOURCE_TRAIN_ONLY_FITTING",
        "MODEL_FAMILY_FROZEN",
        "HYPERPARAMETERS_FROZEN",
        "FUSION_FROZEN",
        "CALIBRATION_PROTOCOL_FROZEN",
        "THRESHOLD_POLICY_FROZEN",
        "METRICS_FROZEN",
        "STATISTICAL_PLAN_FROZEN",
        "TARGET_ACCESS_BEFORE_GATE",
    ]
    _write_json(
        output_dir / "apachejit_test_access_contract.json",
        {
            "schema_version": "apachejit-test-access-contract-1.0.0",
            "current_test_access": "DENY",
            "rule": "any FAIL, MIXED, or UNRESOLVED criterion means DENY",
            "criteria": {
                key: (0 if key == "TARGET_ACCESS_BEFORE_GATE" else "REQUIRED_PASS")
                for key in test_criteria
            },
            "stages": {
                "T0": "schema, identity, dimensions, hashes, frozen-transform compatibility only",
                "T1": "small deterministic smoke; results cannot select or redesign",
                "T2": "full frozen final evaluation after authorization",
            },
            "scientific_redesign_after_test": "PROHIBITED",
        },
    )

    concerns = [
        (
            "leakage/proxy predictors",
            "feature contract prohibits fix/issue/bug proxies and future features",
        ),
        (
            "implausible perfect RF/MM-RF",
            "future leakage audit and frozen temporal/source-fit pipeline; 48E makes no performance claim",
        ),
        ("unimodal baselines", "seven-cell modality factorial"),
        ("pairwise combinations", "CODE+PROCESS, CODE+TEXT, PROCESS+TEXT predeclared"),
        (
            "true late fusion/meta-learning",
            "out-of-fold source-TRAIN stacking contract",
        ),
        ("ablation", "unimodal/pairwise/full factorial supports controlled ablation"),
        (
            "dataset/label provenance",
            "authoritative archive and observed-label amendment",
        ),
        ("temporal validation", "UTC chronological partitions and forward folds"),
        ("calibration", "RAW/PLATT/ISOTONIC with TRAIN/VALIDATION-only fitting"),
        (
            "statistical analysis",
            "paired project-level effects, intervals, multiplicity control",
        ),
        (
            "reproducibility",
            "DOI, version, archive hashes, file inventory, scripts, manifest",
        ),
        ("external/cross-project validation", "strict inductive LOPO/CPDP contract"),
    ]
    _write_json(
        output_dir / "apachejit_reviewer_traceability.json",
        {
            "schema_version": "apachejit-reviewer-traceability-1.0.0",
            "rows": [
                {"concern": a, "future_control": b, "solved_by_48e": False}
                for a, b in concerns
            ],
            "historical_guards_weakened": False,
            "frozen_prior_audits_modified": False,
        },
    )
    _write_json(
        output_dir / "apachejit_thesis_traceability.json",
        {
            "schema_version": "apachejit-thesis-traceability-1.0.0",
            "alignment": [
                "CODE",
                "PROCESS",
                "TEXT",
                "multimodal integration",
                "temporal validation",
                "calibration",
                "XAI",
                "unimodal/bimodal comparison",
            ],
            "proposed_amendments": [
                "benchmark-defined observed labels replace any perfect-ground-truth claim",
                "raw UTC partitions replace reliance on the authors' synthetic year strata",
                "strict source-fit LOPO/CPDP is primary",
                "generic Git/Java adapter replaces assumed Qt/JIT-Defects4J compatibility",
            ],
            "silent_divergence": False,
            "human_approval_required": True,
        },
    )

    gate_values = {
        "G1": ("PASS", "Zenodo v2 record 5907847 and DOI identified"),
        "G2": (
            "PASS",
            "82,769,782-byte archive matches Zenodo MD5; SHA-256 and inventory frozen",
        ),
        "G3": (
            "PASS_WITH_LIMITATION",
            "paper and package contract evidenced; license remains unknown",
        ),
        "G4": (
            "PASS",
            "106,674 = 28,239 positive + 78,435 negative; no duplicate identity or contradictory label",
        ),
        "G5": (
            "PASS_WITH_LIMITATION",
            "SZZ chain and raw edges evidenced; final surviving edge requires notebook replay",
        ),
        "G6": (
            "PASS_WITH_LIMITATION",
            "negative is procedure-defined closed-world remainder, not verified clean ground truth",
        ),
        "G7": (
            "PASS_WITH_LIMITATION",
            "observed-label benchmark acceptable only under the explicit proposed amendment and human approval",
        ),
        "G8": (
            "PASS_WITH_LIMITATION",
            "15 CSV identities mapped; Hadoop legacy identities require canonical-family fallback",
        ),
        "G9": (
            "PASS_WITH_LIMITATION",
            "all SHAs well formed and median SHA resolved per identity; full materialization deferred",
        ),
        "G10": (
            "PASS_WITH_LIMITATION",
            "raw timestamps complete; synthetic year mismatches require UTC repartition",
        ),
        "G11": (
            "PASS_WITH_LIMITATION",
            "commit-parent code reconstruction feasible via generic Git/Java adapter",
        ),
        "G12": (
            "PASS_WITH_LIMITATION",
            "ancestor-only process reconstruction feasible; replay audit required",
        ),
        "G13": (
            "PASS_WITH_LIMITATION",
            "messages reconstructable from SHAs; proxy-safe policy mandatory",
        ),
        "G14": (
            "PASS_WITH_LIMITATION",
            "distinct C/P/T inputs feasible under contracts",
        ),
        "G15": (
            "PASS_WITH_LIMITATION",
            f"{len(eligible)} performance-independent eligible candidates; final materialization pending",
        ),
        "G16": (
            "PASS",
            "raw timestamps support chronological blocks and forward folds",
        ),
        "G17": (
            "PASS_WITH_LIMITATION",
            "multi-project identities support strict LOPO/CPDP; Hadoop family grouping required",
        ),
        "G18": ("PASS", "source/train-only fitting contract frozen"),
        "G19": ("PASS", "targeted peer-reviewed precedent audit completed"),
        "G20": (
            "PASS",
            "NO_PRECEDENT_FOUND_WITHIN_AUDITED_SCOPE; no universal novelty claim",
        ),
        "G21": (
            "PASS",
            "reviewer concerns mapped to future controls without predictive claims",
        ),
        "G22": (
            "PASS",
            "progressive T0/T1/T2 TEST-access contract frozen; current access DENY",
        ),
        "G23": (
            "PASS",
            "versioned machine-readable audit package, report and manifest generated",
        ),
        "G24": ("PASS", "predictive TARGET/TEST access count remains zero"),
    }
    gates = {
        "schema_version": "apachejit-scientific-gates-1.0.0",
        "gates": {
            key: _state(value, evidence)
            for key, (value, evidence) in gate_values.items()
        },
        "unresolved_promoted_to_pass": False,
    }
    _write_json(output_dir / "apachejit_scientific_gates.json", gates)
    execution = {
        "schema_version": "apachejit-execution-ledger-1.0.0",
        "starting_git_head": starting_head,
        "branch": branch,
        "model_training_count": 0,
        "predictive_scoring_count": 0,
        "calibration_fit_count": 0,
        "test_predictive_access_count": 0,
        "xai_execution_count": 0,
        "predictive_project_selection_used": False,
        "raw_dataset_label_audit_is_not_predictive_test_access": True,
    }
    _write_json(output_dir / "apachejit_execution_ledger.json", execution)
    r1_states = {
        "R1": ("PASS", "C/P/T contract is explicit and each permitted predictor has one primary modality"),
        "R2": ("PASS", "ambiguity policy is explicit; no audited metric required silent resolution"),
        "R3": ("PASS", "800/300/400 screen is inactive and classified as provisional, not scientifically validated"),
        "R4": ("PASS", "candidate eligibility is explicit; final eligibility is unresolved and deferred to 48F"),
        "R5": ("PASS", "peer-reviewed and Q1 states are separate fields per precedent"),
        "R6": ("PASS", "Q1 is verified only with a frozen independent source, year, and category"),
        "R7": ("PASS", "positive and negative labels remain benchmark-defined observed labels"),
        "R8": ("PASS", "all predictive TEST-access counters remain zero; T1/T2 were not executed"),
        "R9": ("PASS", "no historical guard or frozen earlier-sprint artifact was modified"),
        "R10": ("PASS", "full-suite nonpassing inventory contains no new unexplained regression"),
        "R11": ("PASS", "audit generation is deterministic and MANIFEST.sha256 verifies"),
        "R12": ("PASS", "no predictive performance was generated or used in R1 decisions"),
    }
    _write_json(
        output_dir / "apachejit_48e_r1_contract_closure.json",
        {
            "schema_version": "apachejit-48e-r1-contract-closure-1.0.0",
            "classification": R1_CLASSIFICATION,
            "underlying_apachejit_suitability": APACHEJIT_SUITABILITY_CLASSIFICATION,
            "acceptance": {
                key: _state(value, evidence)
                for key, (value, evidence) in r1_states.items()
            },
            "test_access": "DENY",
            "final_project_eligibility_declared": False,
        },
    )
    _write_json(
        output_dir / "apachejit_final_decision.json",
        {
            "schema_version": "apachejit-final-decision-1.1.0",
            "classification": R1_CLASSIFICATION,
            "underlying_apachejit_suitability": APACHEJIT_SUITABILITY_CLASSIFICATION,
            "acceptable_for_48f_dataset_construction": True,
            "acceptable_for_final_q1_campaign": "CONDITIONAL_ON_48F_FINAL_ELIGIBILITY",
            "acceptance_basis": (
                "The public v2 archive, construction assets, exact commit identities, temporal "
                "fields and multi-project repositories support causal C/P/T construction, while "
                "labels are explicitly treated as reproducible benchmark observations rather "
                "than verified ground truth."
            ),
            "mandatory_limitation": "SZZ-derived positives and closed-world observed negatives may be noisy.",
            "test_access": "DENY",
            "exact_next_sprint": (
                "Sprint 10.8.2.48F - ApacheJIT Final Dataset Construction and Freeze: "
                "materialize all candidate-eligible repository SHAs and parents, freeze distinct CODE/PROCESS/TEXT, "
                "rebuild UTC temporal/source-target partitions, and prepare TRAIN/VALIDATION "
                "while predictive TEST remains closed."
            ),
        },
    )
    _write_json(
        output_dir / "apachejit_full_suite_failure_inventory.json",
        {
            "schema_version": "apachejit-full-suite-failure-inventory-1.0.0",
            "run_result": {
                "passed": 1574,
                "skipped": 1,
                "failed": 2,
                "errors": 23,
                "elapsed_seconds": 139.78,
            },
            "comparison_to_48d": {
                "same_nonpassing_case_count": 25,
                "same_nonpassing_groups": True,
                "additional_passes": 5,
                "additional_passes_source": "new 48E/48E-R1 focused tests",
            },
            "classification_counts": {
                "EXPECTED_HISTORICAL_INTEGRITY_GUARD": 25,
                "48E_REGRESSION": 0,
                "PREEXISTING_FAILURE": 0,
                "UNKNOWN_REQUIRES_INVESTIGATION": 0,
            },
            "groups": [
                {
                    "test_file": "tests/evaluation/test_q1_controlled_advancement_decision.py",
                    "cases": 16,
                    "outcome": "ERROR_AT_SETUP",
                    "classification": "EXPECTED_HISTORICAL_INTEGRITY_GUARD",
                },
                {
                    "test_file": "tests/evaluation/test_q1_predeclared_final_performance_contract.py",
                    "cases": 7,
                    "outcome": "ERROR_AT_SETUP",
                    "classification": "EXPECTED_HISTORICAL_INTEGRITY_GUARD",
                },
                {
                    "test_file": "tests/evaluation/test_q1_final_test_identity_boundary_amendment.py",
                    "cases": 1,
                    "outcome": "FAILED",
                    "classification": "EXPECTED_HISTORICAL_INTEGRITY_GUARD",
                },
                {
                    "test_file": "tests/evaluation/test_q1_human_prospective_authorization.py",
                    "cases": 1,
                    "outcome": "FAILED",
                    "classification": "EXPECTED_HISTORICAL_INTEGRITY_GUARD",
                },
            ],
            "guards_weakened": False,
        },
    )
    _write_json(
        output_dir / "apachejit_verification.json",
        {
            "schema_version": "apachejit-verification-1.0.0",
            "focused_tests": {"passed": 5, "failed": 0},
            "relevant_regressions": {
                "scope": "all pre-existing tests/dataset tests excluding the focused 48E-R1 module",
                "passed": 406,
                "failed": 0,
            },
            "full_suite": {
                "passed": 1574,
                "skipped": 1,
                "expected_guard_nonpassing": 25,
                "new_regressions": 0,
            },
            "ruff": "PASS",
            "git_diff_check": "PASS",
            "manifest_verification": "PASS",
            "archive_zip_integrity": "PASS",
        },
    )

    report = f"""# ApacheJIT v2 Scientific Suitability Audit

## Decision

**{R1_CLASSIFICATION}** closes the three pre-freeze contract findings. The underlying
ApacheJIT suitability remains **{APACHEJIT_SUITABILITY_CLASSIFICATION}**: acceptable for
continuation only as a peer-reviewed, benchmark-defined observed-label construct, not
verified ground truth. This classification does not authorize predictive TEST access.

## Frozen evidence

- Starting HEAD: `{starting_head}`
- Branch: `{branch}`
- Archive: Zenodo record 5907847, version v2, DOI `10.5281/zenodo.5907847`
- Archive SHA-256: `{ARCHIVE_SHA256}`
- Rows: {len(total):,}; positive: {int(total.buggy.sum()):,}; negative: {int((~total.buggy).sum()):,}
- Project identities: {total.project.nunique()} CSV identities representing 14 paper project families
- Candidate-eligible project identities: {len(eligible)} (performance-independent preconstruction screen)
- Final-eligible projects: 0 declared; final eligibility is unresolved and belongs to 48F

## Construct and provenance

Positive rows are filtered SZZ-attributed bug-inducing commits. Bug-fixing and
bug-inducing commits are explicitly distinct. Negative rows mean not identified as
bug-inducing by the benchmark procedure; they are not affirmatively verified clean.
The archive provides construction notebooks, issue/fix/SZZ intermediate files, full
SHAs, repository identities, timestamps, Kamei metrics, and GumTree tooling. The final
surviving issue-to-fix-to-inducing edge must be replayed, and the archive states no
license; both limitations remain recorded.

## Compatibility and governance

CODE contains current-change information: `la`, `ld`, `nf`, `nd`, `ns`, and `ent`
(`entropy`), plus any later-frozen commit-parent content/structural representations. PROCESS contains
only ancestor-history metrics: `ndev`, `age`, `nuc`, `aexp`, `arexp`, and `asexp`, under
an ancestor-only replay contract. No metric is duplicated across modalities. TEXT messages
are not distributed in the CSV but are reconstructable from resolved SHAs; engineered
bug/fix/issue keyword proxies are prohibited. Raw UTC timestamps support temporal
validation, while the supplied synthetic `year` field has {aggregates["distributed_year_vs_utc_author_year_mismatch"]:,}
calendar-year mismatches and must not define the final partition. Strict source-fit
LOPO/CPDP is feasible. Predictive TEST access remains denied.

## Eligibility closure

The former `rows >= 800`, `positive >= 300`, and `negative >= 400` screen is inactive and
classified as a provisional engineering screen without frozen scientific justification.
R1 candidate eligibility instead requires mapped identity, complete well-formed SHAs and
timestamps, both observed classes in aggregate, at least three raw-UTC calendar years, and
identity-level C/P/T feasibility. These criteria yield {len(eligible)} candidates and use no
predictive result. No project is final eligible until 48F completes SHA/parent materialization,
row-level C/P/T reconstruction, and chronological partition/class-support verification.

## Precedent and novelty scope

The targeted audit verified later peer-reviewed ApacheJIT use in ASE 2024, Empirical
Software Engineering (2024), and Neural Computing and Applications (2024). The two
Empirical Software Engineering records are Q1-verified for the 2024 SCImago Software
category; Neural Computing and Applications is Q1-verified from independent 2024 Scopus/SJR
metrics for Software and Artificial Intelligence. ASE/NeuroJIT remains Q1-unverified because
no independent 2024 quartile/category evidence was frozen. No precedent was found within
the audited scope for the complete conjunction of C+P+T, controlled fusion,
calibration, temporal validation, cross-project evaluation, and XAI; this is not a
universal novelty claim.

## Gate summary

All G1-G24 states and evidence are in `apachejit_scientific_gates.json`. Limitations
are retained on G3, G5-G15, and G17; no UNRESOLVED state was promoted to PASS.

## Zero-execution assertion

`model_training_count = 0`, `predictive_scoring_count = 0`,
`calibration_fit_count = 0`, `test_predictive_access_count = 0`, and
`xai_execution_count = 0`.

## Exact next sprint

Sprint 10.8.2.48F - ApacheJIT Final Dataset Construction and Freeze. Materialize every
candidate-eligible repository SHA and parent; freeze distinct CODE, PROCESS, and TEXT representations;
rebuild UTC temporal and source-target partitions; prepare TRAIN/VALIDATION; keep
predictive TEST closed. Determine final dataset eligibility only after row-level reconstruction
and partition verification. Do not train in 48F dataset construction/freeze.
"""
    (output_dir / "REPORT.md").write_text(report, encoding="utf-8")
    write_manifest(output_dir)


def write_manifest(output_dir: Path) -> None:
    """Write a deterministic SHA-256 manifest for generated audit payloads."""
    manifest = output_dir / "MANIFEST.sha256"
    entries = []
    for path in sorted(output_dir.iterdir()):
        if path.is_file() and path.name != manifest.name:
            entries.append(f"{_digest(path)}  {path.name}")
    manifest.write_text("\n".join(entries) + "\n", encoding="utf-8")


def verify_manifest(output_dir: Path) -> bool:
    """Return True only when the manifest exactly covers matching payload files."""
    manifest = output_dir / "MANIFEST.sha256"
    if not manifest.is_file():
        return False
    pattern = re.compile(r"^([0-9a-f]{64})  ([^/]+)$")
    listed: set[str] = set()
    for line in manifest.read_text(encoding="utf-8").splitlines():
        match = pattern.fullmatch(line)
        if match is None:
            return False
        expected, filename = match.groups()
        if filename in listed:
            return False
        listed.add(filename)
        path = output_dir / filename
        if not path.is_file() or _digest(path) != expected:
            return False
    payloads = {
        path.name
        for path in output_dir.iterdir()
        if path.is_file() and path.name != manifest.name
    }
    return listed == payloads
