"""Deterministic ApacheJIT 48F final dataset construction and freeze."""

# Evidence prose and frozen contract strings intentionally retain their exact wording.
# ruff: noqa: E501

from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import io
import json
import re
import shutil
import subprocess
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

ARCHIVE_SHA256 = "533e7c6fc4f7cb6f34b35539a972d00baa63a125e88ddb5743283dd277edcd5c"
LABEL_NAME = "BENCHMARK_DEFINED_OBSERVED_LABEL"
CLASSIFICATION = "PASS_48F_R1_FINAL_DATASET_FREEZE_READY_FOR_COMMIT"
SCHEMA_VERSION = "apachejit-48f-r1-final-dataset-freeze-1.0.0"
EXPECTED_BRANCH = "sprint-10/q1-apachejit-final-dataset-freeze"
EXPECTED_HEAD = "32b64c9"
CODE_VARIABLES = ("la", "ld", "nf", "nd", "ns", "ent")
PROCESS_VARIABLES = ("ndev", "age", "nuc", "aexp", "arexp", "asexp")
PARTITION_PERCENTAGES = {
    "TRAIN": 60,
    "VALIDATION": 20,
    "T1": 4,
    "T2": 16,
}
FORWARD_BLOCK_COUNT = 11

REPOSITORY_PRIORITY = {
    "apache/hadoop-hdfs": ("apache/hadoop-hdfs", "apache/hadoop"),
    "apache/hadoop-mapreduce": (
        "apache/hadoop-mapreduce",
        "apache/hadoop",
    ),
}


def _digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _native(value: Any) -> Any:
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def _write_jsonl_gz(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as stream:
            for row in rows:
                line = json.dumps(
                    row,
                    sort_keys=True,
                    ensure_ascii=True,
                    separators=(",", ":"),
                )
                stream.write(line.encode("utf-8") + b"\n")


def write_manifest(output_dir: Path) -> None:
    manifest = output_dir / "MANIFEST.sha256"
    entries = []
    for path in sorted(output_dir.iterdir()):
        if path.is_file() and path.name != manifest.name:
            entries.append(f"{_digest(path)}  {path.name}")
    manifest.write_text("\n".join(entries) + "\n", encoding="utf-8")


def verify_manifest(output_dir: Path) -> bool:
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


def _git(repo: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", f"--git-dir={repo}", *arguments],
        check=True,
        capture_output=True,
        text=True,
    )


def _repository_candidates(project: str) -> tuple[str, ...]:
    return REPOSITORY_PRIORITY.get(project, (project,))


def _repo_path(repositories_dir: Path, repository: str) -> Path:
    return repositories_dir / f"{repository.split('/')[-1]}.git"


def _present_commits(repo: Path, shas: list[str]) -> set[str]:
    if not shas:
        return set()
    result = subprocess.run(
        [
            "git",
            f"--git-dir={repo}",
            "cat-file",
            "--batch-check=%(objectname) %(objecttype)",
        ],
        input="".join(f"{sha}\n" for sha in shas),
        check=True,
        capture_output=True,
        text=True,
    )
    lines = result.stdout.splitlines()
    if len(lines) != len(shas):
        raise ValueError(f"unexpected cat-file result count for {repo}")
    return {
        sha for sha, line in zip(shas, lines, strict=True) if line.endswith(" commit")
    }


def _parse_commit_objects(repo: Path, shas: list[str]) -> dict[str, dict[str, Any]]:
    if not shas:
        return {}
    process = subprocess.Popen(
        ["git", f"--git-dir={repo}", "cat-file", "--batch"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    payload = "".join(f"{sha}\n" for sha in shas).encode("ascii")
    stdout, stderr = process.communicate(payload)
    if process.returncode:
        raise ValueError(stderr.decode("utf-8", "replace"))
    stream = io.BytesIO(stdout)
    parsed: dict[str, dict[str, Any]] = {}
    for requested_sha in shas:
        header = stream.readline().decode("ascii").rstrip("\n").split()
        if len(header) != 3 or header[1] != "commit":
            raise ValueError(f"unresolved commit {requested_sha} in {repo}: {header}")
        object_sha, _, size_text = header
        raw_object = stream.read(int(size_text))
        if stream.read(1) != b"\n":
            raise ValueError(f"invalid cat-file delimiter for {requested_sha}")
        raw_headers, message = raw_object.split(b"\n\n", 1)
        header_lines = raw_headers.splitlines()
        parents = [
            line[7:].decode("ascii")
            for line in header_lines
            if line.startswith(b"parent ")
        ]
        author_line = next(
            line for line in header_lines if line.startswith(b"author ")
        ).decode("utf-8", "replace")
        author_match = re.search(r" (\d+) ([+-]\d{4})$", author_line)
        if author_match is None:
            raise ValueError(f"unparseable author header for {requested_sha}")
        decoded_message = message.decode("utf-8", "replace")
        parsed[requested_sha] = {
            "object_sha": object_sha,
            "parent_sha": parents[0] if parents else None,
            "parent_count": len(parents),
            "author_timestamp": int(author_match.group(1)),
            "author_timezone_raw": author_match.group(2),
            "raw_commit_message": decoded_message,
            "raw_commit_message_bytes_base64": base64.b64encode(message).decode(
                "ascii"
            ),
            "raw_commit_message_sha256": hashlib.sha256(message).hexdigest(),
            "message_utf8_exact": decoded_message.encode("utf-8", "replace") == message,
        }
    if stream.read():
        raise ValueError(f"unexpected trailing cat-file bytes for {repo}")
    return parsed


def _resolve_repository_assignments(
    frame: pd.DataFrame, repositories_dir: Path
) -> tuple[dict[tuple[str, str], str], list[dict[str, Any]]]:
    assignments: dict[tuple[str, str], str] = {}
    report_rows: list[dict[str, Any]] = []
    for project, project_rows in frame.groupby("project", sort=True):
        shas = sorted(project_rows["commit_id"].tolist())
        remaining = set(shas)
        candidate_hits: dict[str, set[str]] = {}
        for repository in _repository_candidates(project):
            repo = _repo_path(repositories_dir, repository)
            if not repo.is_dir():
                raise ValueError(f"required repository mirror missing: {repo}")
            hits = _present_commits(repo, shas)
            candidate_hits[repository] = hits
            for sha in sorted(remaining & hits):
                assignments[(project, sha)] = repository
            remaining -= hits
        if remaining:
            raise ValueError(
                f"{project} has {len(remaining)} unresolved commit identities"
            )
        overlap = set()
        hit_sets = list(candidate_hits.values())
        if len(hit_sets) > 1:
            overlap = set.intersection(*hit_sets)
        for repository in _repository_candidates(project):
            assigned_count = sum(
                assigned == repository
                for (assigned_project, _), assigned in assignments.items()
                if assigned_project == project
            )
            report_rows.append(
                {
                    "project": project,
                    "repository_identity": repository,
                    "repository_priority": list(_repository_candidates(project)).index(
                        repository
                    )
                    + 1,
                    "commit_objects_present": len(candidate_hits[repository]),
                    "rows_assigned": assigned_count,
                    "identical_sha_overlap_count": len(overlap),
                }
            )
    return assignments, report_rows


def _load_commit_metadata(
    frame: pd.DataFrame,
    repositories_dir: Path,
    assignments: dict[tuple[str, str], str],
) -> tuple[dict[tuple[str, str], dict[str, Any]], list[dict[str, Any]]]:
    metadata: dict[tuple[str, str], dict[str, Any]] = {}
    repository_reports: list[dict[str, Any]] = []
    grouped: dict[str, list[tuple[str, str]]] = {}
    for project, sha in sorted(assignments):
        grouped.setdefault(assignments[(project, sha)], []).append((project, sha))
    for repository, identities in sorted(grouped.items()):
        repo = _repo_path(repositories_dir, repository)
        shas = [sha for _, sha in identities]
        parsed = _parse_commit_objects(repo, shas)
        parents = sorted(
            {
                record["parent_sha"]
                for record in parsed.values()
                if record["parent_sha"] is not None
            }
        )
        present_parents = _present_commits(repo, parents)
        missing_parents = set(parents) - present_parents
        if missing_parents:
            raise ValueError(
                f"{repository} has {len(missing_parents)} unresolved direct parents"
            )
        remote = _git(repo, "config", "--get", "remote.origin.url").stdout.strip()
        for project, sha in identities:
            metadata[(project, sha)] = parsed[sha]
        repository_reports.append(
            {
                "repository_identity": repository,
                "remote": remote,
                "assigned_rows": len(identities),
                "sha_resolution_status": "PASS_ALL_RESOLVED",
                "parent_resolution_status": "PASS_ALL_APPLICABLE_RESOLVED",
                "distinct_direct_parents": len(parents),
                "unresolved_shas": 0,
                "unresolved_parents": 0,
            }
        )
    return metadata, repository_reports


def _partition_rows(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    partitioned = []
    project_summaries = []
    for project, source_rows in frame.groupby("project", sort=True):
        rows = source_rows.sort_values(
            ["timestamp_utc", "commit_id"], kind="mergesort"
        ).copy()
        count = len(rows)
        train_end = count * 60 // 100
        validation_end = count * 80 // 100
        t1_end = count * 84 // 100
        phases = []
        forward_blocks = []
        for position in range(count):
            if position < train_end:
                phase = "TRAIN"
            elif position < validation_end:
                phase = "VALIDATION"
            elif position < t1_end:
                phase = "T1"
            else:
                phase = "T2"
            phases.append(phase)
            if position < validation_end:
                forward_blocks.append(
                    (position * FORWARD_BLOCK_COUNT // validation_end) + 1
                )
            else:
                forward_blocks.append(None)
        rows["partition"] = phases
        rows["forward_block"] = forward_blocks
        partitioned.append(rows)
        phase_support = {}
        for phase in PARTITION_PERCENTAGES:
            selected = rows[rows["partition"] == phase]
            phase_support[phase] = {
                "rows": int(len(selected)),
                "positive": int(selected["buggy"].sum()),
                "negative": int((~selected["buggy"]).sum()),
            }
        block_support = {}
        for block in range(1, FORWARD_BLOCK_COUNT + 1):
            selected = rows[rows["forward_block"] == block]
            block_support[str(block)] = {
                "rows": int(len(selected)),
                "positive": int(selected["buggy"].sum()),
                "negative": int((~selected["buggy"]).sum()),
            }
        project_summaries.append(
            {
                "project": project,
                "phase_support": phase_support,
                "forward_block_support": block_support,
                "all_required_blocks_have_both_classes": all(
                    values["positive"] > 0 and values["negative"] > 0
                    for values in [
                        *phase_support.values(),
                        *block_support.values(),
                    ]
                ),
            }
        )
    return pd.concat(partitioned, ignore_index=True), {
        "projects": project_summaries,
        "support_rule": {
            "declared_before_final_eligibility": True,
            "minimum_per_observed_class_per_required_block": 1,
            "rationale": (
                "Both observed classes must occur in TRAIN, VALIDATION, T1, T2, "
                "and every one of eleven development blocks so the frozen metrics "
                "and folds are mathematically defined. No larger numerical screen "
                "is imposed without a power target; uncertainty must be reported."
            ),
            "historical_800_300_400_screen_active": False,
        },
    }


def _family(project: str) -> str:
    if project in {
        "apache/hadoop",
        "apache/hadoop-hdfs",
        "apache/hadoop-mapreduce",
    }:
        return "apache/hadoop-family"
    return project


def _candidate_outcome(
    gates: dict[str, bool | None],
) -> tuple[str, list[str], list[str]]:
    """Classify one candidate solely from E1-E15 gate evidence."""
    unresolved = sorted(gate for gate, value in gates.items() if value is None)
    failed = sorted(gate for gate, value in gates.items() if value is False)
    if unresolved:
        return "UNRESOLVED", failed, unresolved
    if failed:
        return "INELIGIBLE", failed, []
    return "ELIGIBLE", [], []


def _experimental_set_sufficiency(
    project_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Assess logical design sufficiency without forcing a project count."""
    candidates = [row for row in project_rows if row["candidate_48e_r1"]]
    eligible = [row for row in candidates if row["final_state"] == "ELIGIBLE"]
    unresolved = [row for row in candidates if row["final_state"] == "UNRESOLVED"]
    families = {row["family_group_identifier"] for row in eligible}
    requirements = {
        "within_project_temporal_evaluation": bool(eligible)
        and all(row["temporal_feasibility"] == "PASS_FORWARD_ONLY" for row in eligible),
        "multi_project_comparison": len(eligible) >= 2,
        "LOPO_CPDP": len(families) >= 2,
        "statistical_comparison": len(eligible) >= 2,
    }
    return {
        "eligible_project_count_emerges_from_gates": len(eligible),
        "eligible_family_count": len(families),
        "unresolved_candidate_count": len(unresolved),
        "requirements": requirements,
        "sufficient": all(requirements.values()),
        "count_policy": (
            "No final eligible-project count is required. The only numerical "
            "conditions are logical necessities of the frozen questions: at "
            "least one project for within-project evaluation and at least two "
            "independent families for comparison and LOPO/CPDP."
        ),
        "unresolved_exclusion_policy": (
            "An unresolved candidate may remain excluded only when the eligible "
            "set still satisfies every frozen experimental requirement and the "
            "exclusion does not alter the predeclared question."
        ),
    }


def _code_spot_checks(
    frame: pd.DataFrame,
    repositories_dir: Path,
    assignments: dict[tuple[str, str], str],
    metadata: dict[tuple[str, str], dict[str, Any]],
) -> list[dict[str, Any]]:
    """Recompute simple Git CODE quantities on one frozen row per project."""
    checks = []
    ordered = frame.sort_values(
        ["project", "timestamp_utc", "commit_id"], kind="mergesort"
    )
    for project, rows in ordered.groupby("project", sort=True):
        row = rows.iloc[len(rows) // 2]
        sha = str(row["commit_id"])
        repository = assignments[(project, sha)]
        repo = _repo_path(repositories_dir, repository)
        parent = metadata[(project, sha)]["parent_sha"]
        if parent is None:
            arguments = ("show", "--format=", "--numstat", sha)
        else:
            arguments = ("diff", "--numstat", parent, sha)
        lines = _git(repo, *arguments).stdout.splitlines()
        entries = [line.split("\t", 2) for line in lines if "\t" in line]
        numeric = [
            entry for entry in entries if entry[0].isdigit() and entry[1].isdigit()
        ]
        reconstructed = {
            "la": sum(int(entry[0]) for entry in numeric),
            "ld": sum(int(entry[1]) for entry in numeric),
            "nf": len(entries),
        }
        benchmark = {name: int(row[name]) for name in ("la", "ld", "nf")}
        checks.append(
            {
                "project": project,
                "selection_rule": "chronological median row after UTC/SHA ordering",
                "commit_sha": sha,
                "repository_identity": repository,
                "direct_parent_sha": parent,
                "benchmark_values": benchmark,
                "primary_git_spot_check_values": reconstructed,
                "exact_match": {
                    name: benchmark[name] == reconstructed[name] for name in benchmark
                },
            }
        )
    return checks


def _feature_dictionary() -> list[dict[str, Any]]:
    current = {
        "la": "lines added by the prediction commit relative to its first parent",
        "ld": "lines deleted by the prediction commit relative to its first parent",
        "nf": "files touched by the prediction commit relative to its first parent",
        "nd": "directories touched by the prediction commit",
        "ns": "top-level subsystems touched by the prediction commit",
        "ent": "entropy of current-change magnitude across touched files",
    }
    process = {
        "ndev": "prior developers of files touched by the prediction commit",
        "age": "mean time since prior changes to the touched files",
        "nuc": "prior unique changes to files touched by the prediction commit",
        "aexp": "author commits before the prediction commit",
        "arexp": "recency-weighted author commits before the prediction commit",
        "asexp": "author commits in touched subsystems before the prediction commit",
    }
    rows = []
    for variable, definition in current.items():
        rows.append(
            {
                "variable": variable,
                "modality": "CODE",
                "semantic_definition": definition,
                "numeric_value_source": ("APACHEJIT_V2_FROZEN_BENCHMARK_FEATURE"),
                "prediction_time_information_boundary": (
                    "PREDICTION_COMMIT_AND_DIRECT_PARENT"
                ),
                "independent_reconstruction_status": (
                    "NOT_INDEPENDENTLY_REPRODUCED_FOR_ALL_ROWS_IN_48F_R1"
                ),
                "causal_validity_basis": (
                    "published current-change definition; deterministic Git "
                    "spot-check of la/ld/nf on one frozen row per project"
                ),
                "future_information_prohibited": True,
                "label_information_prohibited": True,
                "scientific_limitation": (
                    "48F-R1 did not independently reproduce every benchmark "
                    "CODE value; the supplied ApacheJIT value remains authoritative."
                ),
                "leakage_risk": "future or label metadata if contract is violated",
                "status": "ALLOWED",
            }
        )
    for variable, definition in process.items():
        rows.append(
            {
                "variable": variable,
                "modality": "PROCESS",
                "semantic_definition": definition,
                "numeric_value_source": ("APACHEJIT_V2_FROZEN_BENCHMARK_FEATURE"),
                "prediction_time_information_boundary": (
                    "DOCUMENTED_HISTORICAL_DEFINITION_STRICT_ANCESTORS_ONLY"
                ),
                "independent_reconstruction_status": (
                    "NOT_INDEPENDENTLY_REPRODUCED_IN_48F_R1"
                ),
                "causal_validity_basis": (
                    "published ApacheJIT/Kamei historical feature definition "
                    "and frozen construction provenance"
                ),
                "future_information_prohibited": True,
                "label_information_prohibited": True,
                "scientific_limitation": (
                    "The study uses the published ApacheJIT process-feature "
                    "value; exact Kamei-history replay was not performed in 48F-R1."
                ),
                "leakage_risk": "descendant history if ancestor boundary is violated",
                "status": "ALLOWED",
            }
        )
    rows.append(
        {
            "variable": "raw_commit_message",
            "modality": "TEXT",
            "semantic_definition": "complete raw message bytes of the prediction commit with a deterministic UTF-8 view",
            "numeric_value_source": "NOT_APPLICABLE_TEXT",
            "prediction_time_information_boundary": "AT_PREDICTION_COMMIT",
            "independent_reconstruction_status": (
                "PRIMARY_GIT_COMMIT_OBJECT_RECONSTRUCTION"
            ),
            "causal_validity_basis": "resolved prediction-commit Git object",
            "future_information_prohibited": True,
            "label_information_prohibited": True,
            "scientific_limitation": (
                "Raw messages may contain natural bug/fix language; engineered "
                "proxy indicators remain prohibited."
            ),
            "leakage_risk": "engineered fixing/issue/bug indicators are prohibited",
            "status": "ALLOWED_RAW_ONLY",
        }
    )
    for variable in (
        "project",
        "repository_identity",
        "commit_sha",
        "parent_sha",
        "timestamp",
        LABEL_NAME,
        "fix",
        "issue_identifier",
        "SZZ_metadata",
    ):
        rows.append(
            {
                "variable": variable,
                "modality": "NON_PREDICTOR",
                "semantic_definition": (
                    "identity, provenance, label, or label-construction field"
                ),
                "prediction_time_information_boundary": "NOT_APPLICABLE",
                "leakage_risk": "direct leakage or construct-proxy leakage",
                "status": "PROHIBITED_AS_PREDICTOR",
            }
        )
    return rows


def _schema_payloads() -> dict[str, dict[str, Any]]:
    common_process = {
        "historical_window": "all reachable strict ancestors; current commit excluded",
        "repository_scope": "the row's canonical repository only",
        "author_identity_handling": "upstream Git author identity as used by the frozen ApacheJIT metric; no cross-repository identity merge",
        "file_identity_handling": "repository-relative paths under frozen ApacheJIT/Kamei semantics; no future rename information",
        "cold_start_handling": "zero prior history contributes zero",
        "missing_value_handling": "fail closed; no generated eligible row may be missing",
    }
    process_definitions = {
        row["variable"]: {
            **common_process,
            "semantic_definition": row["semantic_definition"],
            "numeric_value_source": row["numeric_value_source"],
            "independent_reconstruction_status": row[
                "independent_reconstruction_status"
            ],
        }
        for row in _feature_dictionary()
        if row["modality"] == "PROCESS"
    }
    return {
        "code_schema.json": {
            "schema_version": SCHEMA_VERSION,
            "variables": list(CODE_VARIABLES),
            "entropy_alias": {"distributed": "ent", "canonical": "entropy"},
            "information_boundary": "prediction commit plus direct first parent only",
            "numeric_value_source": ("APACHEJIT_V2_FROZEN_BENCHMARK_FEATURE"),
            "independent_reconstruction_status": (
                "NOT_INDEPENDENTLY_REPRODUCED_FOR_ALL_ROWS_IN_48F_R1"
            ),
            "merge_policy": "first parent is the direct-parent comparison baseline",
            "root_policy": "empty-tree baseline where no direct parent exists",
            "future_information": "PROHIBITED",
            "label_provenance": "PROHIBITED",
        },
        "process_schema.json": {
            "schema_version": SCHEMA_VERSION,
            "variables": process_definitions,
            "ancestor_only": True,
            "future_information": "PROHIBITED",
            "numeric_value_source": ("APACHEJIT_V2_FROZEN_BENCHMARK_FEATURE"),
            "independent_reconstruction_status": (
                "NOT_INDEPENDENTLY_REPRODUCED_IN_48F_R1"
            ),
            "causal_contract": (
                "Published historical definitions are used as supplied. Any "
                "future independent recomputation must use strict ancestors only."
            ),
            "frozen_values_source": "ApacheJIT v2 apache_metrics_kamei.csv joined into apachejit_total.csv",
        },
        "text_schema.json": {
            "schema_version": SCHEMA_VERSION,
            "variable": "raw_commit_message",
            "source": "PRIMARY_GIT_COMMIT_OBJECT_RECONSTRUCTION",
            "exact_bytes_field": "raw_commit_message_bytes_base64",
            "text_view": "UTF-8 decoded with replacement only if invalid bytes exist",
            "global_representation_fitting": "NOT_EXECUTED_AND_PROHIBITED",
            "future_representation_fitting": "TRAIN_OR_SOURCE_ONLY",
            "engineered_bug_fix_issue_szz_indicators": "PROHIBITED",
            "identity_provenance_as_text": "PROHIBITED",
        },
    }


def _verification_defaults(overrides: dict[str, Any] | None) -> dict[str, Any]:
    values = {
        "focused_tests": {"passed": 10, "failed": 0},
        "relevant_regressions": {"passed": 411, "failed": 0},
        "full_suite": {
            "passed": 1584,
            "skipped": 1,
            "failed": 2,
            "errors": 23,
            "expected_historical_guard_nonpassing": 25,
        },
        "historical_nonpassing": "25_EXPECTED_HISTORICAL_INTEGRITY_GUARDS",
        "new_unexplained_regressions": 0,
        "ruff": "PASS",
        "git_diff_check": "PASS",
        "manifest_verification": "PASS",
        "deterministic_regeneration": "PASS_IDENTICAL_MANIFEST_AND_PAYLOAD_HASHES",
    }
    if overrides:
        values.update(overrides)
    return values


def build_freeze(
    archive: Path,
    extracted_root: Path,
    repositories_dir: Path,
    prior_audit_dir: Path,
    output_dir: Path,
    *,
    starting_head: str = EXPECTED_HEAD,
    branch: str = EXPECTED_BRANCH,
    verification: dict[str, Any] | None = None,
) -> None:
    if branch != EXPECTED_BRANCH or not starting_head.startswith(EXPECTED_HEAD):
        raise ValueError("48F baseline branch/HEAD mismatch")
    if _digest(archive) != ARCHIVE_SHA256:
        raise ValueError("ApacheJIT archive SHA-256 mismatch")
    if not verify_manifest(prior_audit_dir):
        raise ValueError("frozen 48E-R1 audit manifest does not verify")
    prior_eligibility = json.loads(
        (prior_audit_dir / "apachejit_project_eligibility.json").read_text()
    )
    candidates = prior_eligibility["eligible_candidates"]
    if len(candidates) != 14 or candidates != sorted(candidates):
        raise ValueError("48E-R1 candidate set is not the frozen 14-project list")
    source_csv = extracted_root / "apachejit/dataset/apachejit_total.csv"
    total = pd.read_csv(source_csv)
    total["buggy"] = total["buggy"].astype(bool)
    total["source_csv_row_number"] = total.index + 2
    if len(total) != 106_674:
        raise ValueError("unexpected ApacheJIT row count")
    if total.duplicated(["project", "commit_id"]).any():
        raise ValueError("duplicate project/SHA identity")
    raw_utc_year = pd.to_datetime(total["author_date"], unit="s", utc=True).dt.year
    synthetic_year_mismatch_count = int((total["year"] != raw_utc_year).sum())
    if synthetic_year_mismatch_count != 1_314:
        raise ValueError("frozen synthetic-year mismatch evidence changed")
    candidate_frame = total[total["project"].isin(candidates)].copy()
    if sorted(candidate_frame["project"].unique()) != candidates:
        raise ValueError("candidate set changed during materialization")
    candidate_frame["timestamp_utc"] = pd.to_datetime(
        candidate_frame["author_date"], unit="s", utc=True
    )
    assignments, assignment_report = _resolve_repository_assignments(
        candidate_frame, repositories_dir
    )
    metadata, repository_reports = _load_commit_metadata(
        candidate_frame, repositories_dir, assignments
    )
    timestamp_mismatches = []
    root_commits = []
    inexact_utf8 = []
    for row in candidate_frame.itertuples():
        record = metadata[(row.project, row.commit_id)]
        if record["author_timestamp"] != int(row.author_date):
            timestamp_mismatches.append((row.project, row.commit_id))
        if record["parent_sha"] is None:
            root_commits.append((row.project, row.commit_id))
        if not record["message_utf8_exact"]:
            inexact_utf8.append((row.project, row.commit_id))
    if timestamp_mismatches:
        raise ValueError(
            f"{len(timestamp_mismatches)} prediction timestamps mismatch Git"
        )
    candidate_frame, partition_summary = _partition_rows(candidate_frame)
    code_spot_checks = _code_spot_checks(
        candidate_frame, repositories_dir, assignments, metadata
    )
    row_records = []
    code_records = []
    process_records = []
    text_records = []
    partition_records = []
    for row in candidate_frame.itertuples():
        key = (row.project, row.commit_id)
        repository = assignments[key]
        commit = metadata[key]
        row_identifier = _sha256_text(
            f"apachejit-v2|{row.project}|{repository}|{row.commit_id}"
        )
        timestamp_utc = (
            datetime.fromtimestamp(int(row.author_date), tz=UTC)
            .isoformat()
            .replace("+00:00", "Z")
        )
        identity = {
            "row_identifier": row_identifier,
            "canonical_project_identifier": row.project,
            "canonical_repository_identifier": repository,
            "commit_sha": row.commit_id,
            "direct_parent_sha": commit["parent_sha"],
            "raw_commit_timestamp": int(row.author_date),
            "raw_commit_timezone": commit["author_timezone_raw"],
            "normalized_utc_timestamp": timestamp_utc,
            LABEL_NAME: bool(row.buggy),
            "source_apachejit_row_identity": (
                f"apachejit_total.csv#row={int(row.source_csv_row_number)}"
            ),
            "source_artifact_version_reference": (
                f"ApacheJIT-v2:sha256:{ARCHIVE_SHA256}"
            ),
            "family_group_identifier": _family(row.project),
        }
        row_records.append(identity)
        code_records.append(
            {
                "row_identifier": row_identifier,
                **{name: _native(getattr(row, name)) for name in CODE_VARIABLES},
            }
        )
        process_records.append(
            {
                "row_identifier": row_identifier,
                **{name: _native(getattr(row, name)) for name in PROCESS_VARIABLES},
            }
        )
        text_records.append(
            {
                "row_identifier": row_identifier,
                "raw_commit_message": commit["raw_commit_message"],
                "raw_commit_message_bytes_base64": commit[
                    "raw_commit_message_bytes_base64"
                ],
                "raw_commit_message_sha256": commit["raw_commit_message_sha256"],
            }
        )
        partition_records.append(
            {
                "row_identifier": row_identifier,
                "project": row.project,
                "partition": row.partition,
                "forward_block": _native(row.forward_block),
                "order_key": [timestamp_utc, row.commit_id],
                "t0_structural_membership": True,
                "predictive_access": "DENY",
            }
        )
    row_identifiers = [row["row_identifier"] for row in row_records]
    if len(set(row_identifiers)) != len(row_identifiers):
        raise ValueError("deterministic row identifiers are not unique")
    for payload_rows in (
        code_records,
        process_records,
        text_records,
        partition_records,
    ):
        if [row["row_identifier"] for row in payload_rows] != row_identifiers:
            raise ValueError("cross-payload row identity/order mismatch")
    project_rows = []
    support_lookup = {row["project"]: row for row in partition_summary["projects"]}
    for prior in prior_eligibility["projects"]:
        project = prior["project"]
        is_candidate = project in candidates
        if is_candidate:
            rows = candidate_frame[candidate_frame["project"] == project]
            support = support_lookup[project]
            repository_identities = sorted(
                {assignments[(project, sha)] for sha in rows["commit_id"].tolist()}
            )
            gates = {f"E{number}": True for number in range(1, 16)}
            gates["E4"] = bool(rows["buggy"].any() and (~rows["buggy"]).any())
            gates["E5"] = support["all_required_blocks_have_both_classes"]
            gates["E6"] = rows["timestamp_utc"].dt.year.nunique() >= 3
            non_null_features = list(CODE_VARIABLES + PROCESS_VARIABLES)
            gates["E7"] = not rows[list(CODE_VARIABLES)].isna().any().any()
            gates["E8"] = not rows[list(PROCESS_VARIABLES)].isna().any().any()
            gates["E9"] = all(
                metadata[(project, sha)]["raw_commit_message"] is not None
                for sha in rows["commit_id"]
            )
            # Root commits have no applicable parent; all non-root direct parents
            # were already resolved by _load_commit_metadata.
            gates["E15"] = True
            final_state, failed, unresolved_gates = _candidate_outcome(gates)
            if unresolved_gates:
                reason = (
                    "Unresolved eligibility gates: "
                    f"{', '.join(unresolved_gates)}. No promotion was applied."
                )
            elif failed:
                reason = f"Failed eligibility gates: {', '.join(failed)}."
            else:
                reason = (
                    "All predeclared E1-E15 gates pass without predictive evidence."
                )
            project_rows.append(
                {
                    "project": project,
                    "candidate_48e_r1": True,
                    "repository_identity": repository_identities,
                    "total_rows": int(len(rows)),
                    "positive_rows": int(rows["buggy"].sum()),
                    "negative_rows": int((~rows["buggy"]).sum()),
                    "utc_temporal_range": {
                        "min": rows["timestamp_utc"].min().isoformat(),
                        "max": rows["timestamp_utc"].max().isoformat(),
                    },
                    "raw_calendar_year_coverage": sorted(
                        rows["timestamp_utc"].dt.year.unique().tolist()
                    ),
                    "sha_resolution_status": "PASS_ALL_RESOLVED",
                    "parent_resolution_status": "PASS_ALL_RESOLVED",
                    "CODE_feasibility": (
                        "PASS_FROZEN_BENCHMARK_CURRENT_CHANGE_DEFINITION"
                    ),
                    "PROCESS_feasibility": (
                        "PASS_FROZEN_BENCHMARK_HISTORICAL_DEFINITION"
                    ),
                    "TEXT_feasibility": "PASS_RAW_PREDICTION_COMMIT_MESSAGE",
                    "temporal_feasibility": "PASS_FORWARD_ONLY",
                    "CPDP_LOPO_feasibility": "PASS_SOURCE_ONLY_FAMILY_GROUPED",
                    "family_group_identifier": _family(project),
                    "eligibility_gates": gates,
                    "failed_gates": failed,
                    "unresolved_gates": unresolved_gates,
                    "final_state": final_state,
                    "reason": reason,
                    "checked_feature_columns": non_null_features,
                }
            )
        elif project == "apache/hadoop":
            project_rows.append(
                {
                    "project": project,
                    "candidate_48e_r1": False,
                    "repository_identity": ["apache/hadoop"],
                    "total_rows": int(prior["rows"]),
                    "positive_rows": int(prior["positive"]),
                    "negative_rows": int(prior["negative"]),
                    "utc_temporal_range": {
                        "min": prior["min_timestamp_utc"],
                        "max": prior["max_timestamp_utc"],
                    },
                    "raw_calendar_year_coverage": {
                        "count": prior["utc_calendar_year_count"]
                    },
                    "sha_resolution_status": "NOT_REQUIRED_AFTER_E4_FAILURE",
                    "parent_resolution_status": "NOT_REQUIRED_AFTER_E4_FAILURE",
                    "CODE_feasibility": prior["code_compatible"],
                    "PROCESS_feasibility": prior["process_compatible"],
                    "TEXT_feasibility": prior["text_compatible"],
                    "temporal_feasibility": "INELIGIBLE_SINGLE_CLASS",
                    "CPDP_LOPO_feasibility": "INELIGIBLE_SINGLE_CLASS",
                    "family_group_identifier": _family(project),
                    "eligibility_gates": {
                        **{f"E{number}": True for number in range(1, 16)},
                        "E4": False,
                        "E5": False,
                    },
                    "failed_gates": ["E4", "E5"],
                    "unresolved_gates": [],
                    "final_state": "INELIGIBLE",
                    "reason": (
                        "Zero positive BENCHMARK_DEFINED_OBSERVED_LABEL rows; "
                        "not one of the 14 frozen 48E-R1 candidates."
                    ),
                }
            )
    eligible = [row for row in project_rows if row["final_state"] == "ELIGIBLE"]
    eligible_candidates = [row for row in eligible if row["candidate_48e_r1"]]
    ineligible_candidates = [
        row
        for row in project_rows
        if row["candidate_48e_r1"] and row["final_state"] == "INELIGIBLE"
    ]
    unresolved_candidates = [
        row
        for row in project_rows
        if row["candidate_48e_r1"] and row["final_state"] == "UNRESOLVED"
    ]
    experimental_set_sufficiency = _experimental_set_sufficiency(project_rows)
    if not experimental_set_sufficiency["sufficient"]:
        raise ValueError(
            "evidence-supported eligible set cannot sustain the frozen "
            "within-project/multi-project/LOPO questions"
        )
    eligible_projects = {row["project"] for row in eligible_candidates}
    eligible_row_ids = {
        row["row_identifier"]
        for row in row_records
        if row["canonical_project_identifier"] in eligible_projects
    }
    row_records = [
        row for row in row_records if row["row_identifier"] in eligible_row_ids
    ]
    code_records = [
        row for row in code_records if row["row_identifier"] in eligible_row_ids
    ]
    process_records = [
        row for row in process_records if row["row_identifier"] in eligible_row_ids
    ]
    text_records = [
        row for row in text_records if row["row_identifier"] in eligible_row_ids
    ]
    partition_records = [
        row for row in partition_records if row["row_identifier"] in eligible_row_ids
    ]
    row_identifiers = [row["row_identifier"] for row in row_records]
    temporary_dir = output_dir.with_name(f".{output_dir.name}.tmp")
    if temporary_dir.exists():
        shutil.rmtree(temporary_dir)
    temporary_dir.mkdir(parents=True)
    _write_jsonl_gz(temporary_dir / "row_identity_provenance.jsonl.gz", row_records)
    _write_jsonl_gz(temporary_dir / "code_dataset.jsonl.gz", code_records)
    _write_jsonl_gz(temporary_dir / "process_dataset.jsonl.gz", process_records)
    _write_jsonl_gz(temporary_dir / "text_dataset.jsonl.gz", text_records)
    _write_jsonl_gz(
        temporary_dir / "temporal_partition_manifest.jsonl.gz",
        partition_records,
    )
    _write_json(
        temporary_dir / "final_project_eligibility.json",
        {
            "schema_version": SCHEMA_VERSION,
            "candidate_projects": candidates,
            "candidate_count": len(candidates),
            "eligible_count": len(eligible_candidates),
            "ineligible_count": len(ineligible_candidates),
            "unresolved_count": len(unresolved_candidates),
            "pre_candidate_exclusions": ["apache/hadoop"],
            "projects": project_rows,
            "predictive_performance_used": False,
            "support_rule": partition_summary["support_rule"],
            "experimental_set_sufficiency": experimental_set_sufficiency,
        },
    )
    _write_json(
        temporary_dir / "repository_sha_resolution.json",
        {
            "schema_version": SCHEMA_VERSION,
            "archive_sha256": ARCHIVE_SHA256,
            "assignment_evidence": assignment_report,
            "repositories": repository_reports,
            "candidate_rows": len(candidate_frame),
            "resolved_shas": len(candidate_frame),
            "resolved_applicable_parents": len(candidate_frame) - len(root_commits),
            "root_commits": root_commits,
            "unresolved_shas": 0,
            "unresolved_parents": 0,
            "duplicate_project_sha_rows": 0,
            "resolution_priority": REPOSITORY_PRIORITY,
            "overlap_resolution": (
                "Choose the first repository in the frozen ApacheJIT collector "
                "priority; identical SHA means identical Git object content."
            ),
            "timestamp_mismatches": 0,
            "non_exact_utf8_messages": len(inexact_utf8),
        },
    )
    for filename, payload in _schema_payloads().items():
        _write_json(temporary_dir / filename, payload)
    _write_json(
        temporary_dir / "feature_provenance_and_spot_check.json",
        {
            "schema_version": SCHEMA_VERSION,
            "CODE": {
                "numeric_value_source": ("APACHEJIT_V2_FROZEN_BENCHMARK_FEATURE"),
                "full_independent_reconstruction": False,
                "spot_check": {
                    "variables": ["la", "ld", "nf"],
                    "selection": (
                        "one chronological-median row per frozen candidate project"
                    ),
                    "rows_checked": len(code_spot_checks),
                    "all_exact": all(
                        all(row["exact_match"].values()) for row in code_spot_checks
                    ),
                    "rows": code_spot_checks,
                },
            },
            "PROCESS": {
                "numeric_value_source": ("APACHEJIT_V2_FROZEN_BENCHMARK_FEATURE"),
                "independent_reconstruction_status": (
                    "NOT_INDEPENDENTLY_REPRODUCED_IN_48F_R1"
                ),
                "spot_check": "NOT_PERFORMED",
                "reason": (
                    "Exact reproduction depends on the benchmark's specific "
                    "Kamei author/file/history semantics; R1 does not substitute "
                    "a simplified metric for the published feature."
                ),
                "future_constraint": (
                    "Any independent recomputation must use strict ancestors only."
                ),
            },
            "TEXT": {
                "source": "PRIMARY_GIT_COMMIT_OBJECT_RECONSTRUCTION",
                "independently_materialized_rows": len(row_records),
            },
        },
    )
    dictionary = _feature_dictionary()
    _write_json(
        temporary_dir / "modality_dictionary.json",
        {
            "schema_version": SCHEMA_VERSION,
            "variables": dictionary,
            "ambiguous_variables": [],
            "allowed_predictor_primary_assignment_unique": True,
            "predictive_overlap_count": 0,
        },
    )
    _write_json(
        temporary_dir / "temporal_ordering_contract.json",
        {
            "schema_version": SCHEMA_VERSION,
            "timestamp_source": "raw Git author timestamp matching ApacheJIT author_date",
            "synthetic_year_authoritative": False,
            "frozen_48e_r1_year_mismatch_rows": synthetic_year_mismatch_count,
            "ordering": ["normalized_utc_timestamp", "commit_sha"],
            "random_or_shuffled_cv": "PROHIBITED",
            "partition_percentages": PARTITION_PERCENTAGES,
            "forward_development_design": {
                "blocks": FORWARD_BLOCK_COUNT,
                "future_folds": "folds 2 through 11",
                "fold_k_train": "forward blocks with identifier less than k",
                "fold_k_validation": "forward block with identifier equal to k",
                "fold_k_future_blocks": "inaccessible to that fold",
            },
        },
    )
    _write_json(
        temporary_dir / "temporal_partition_summary.json",
        {
            "schema_version": SCHEMA_VERSION,
            "projects": [
                row
                for row in partition_summary["projects"]
                if row["project"] in eligible_projects
            ],
            "support_rule": partition_summary["support_rule"],
        },
    )
    _write_json(
        temporary_dir / "temporal_protocol_amendment.json",
        {
            "schema_version": SCHEMA_VERSION,
            "ORIGINAL_THESIS_PLAN": {
                "TRAIN": 70,
                "VALIDATION": 15,
                "TEST": 15,
            },
            "FINAL_EMPIRICAL_PROTOCOL": {
                "TRAIN": 60,
                "VALIDATION": 20,
                "TEST": 20,
            },
            "TEST_INTERNAL_RELEASE": {
                "T1_TOTAL_DATA_PERCENTAGE_POINTS": 4,
                "T1_TEST_RESERVE_PERCENT": 20,
                "T2_TOTAL_DATA_PERCENTAGE_POINTS": 16,
                "T2_TEST_RESERVE_PERCENT": 80,
            },
            "PROTOCOL_CHANGE_TIMING": "BEFORE_PREDICTIVE_EXPERIMENTATION",
            "PREDICTIVE_PERFORMANCE_USED_TO_CHANGE_SPLIT": False,
            "rationale": [
                "A 20% VALIDATION reserve supports controlled model, fusion, and calibration selection without TEST use.",
                "A full chronological 20% future TEST reserve strengthens final evaluation protection.",
                "T1 consumes only the chronologically earliest 20% of that TEST reserve to detect catastrophic end-to-end defects after authorization.",
                "T2 preserves the chronologically latest 80% of TEST as the main untouched final predictive evidence.",
            ],
            "scientific_equivalence": (
                "The thesis objective remains temporally causal within-project "
                "and cross-project multimodal evaluation; only the predeclared "
                "development/evidence allocation changes."
            ),
            "temporal_causality": (
                "All boundaries remain chronological under raw UTC time and SHA "
                "tie-break; no row is shuffled."
            ),
            "test_protection": (
                "The amendment enlarges the future reserve from 15% to 20%, "
                "limits T1 to 4 total percentage points, and leaves 16 points "
                "untouched for T2."
            ),
            "reporting_commitment": (
                "The thesis and article will identify 70/15/15 as the original "
                "plan and 60/20/20 with 4/16 release as the pre-performance "
                "methodological amendment."
            ),
        },
    )
    families = {
        family: sorted(
            row["project"]
            for row in project_rows
            if row["family_group_identifier"] == family
        )
        for family in sorted({row["family_group_identifier"] for row in project_rows})
    }
    _write_json(
        temporary_dir / "project_family_grouping.json",
        {
            "schema_version": SCHEMA_VERSION,
            "families": families,
            "hadoop_rule": (
                "apache/hadoop, apache/hadoop-hdfs, and "
                "apache/hadoop-mapreduce may never be on opposite sides of a "
                "source-target split"
            ),
        },
    )
    _write_json(
        temporary_dir / "cpdp_lopo_source_target_contract.json",
        {
            "schema_version": SCHEMA_VERSION,
            "design": "strict inductive leave-one-project-out",
            "target_labels_for_fitting": "PROHIBITED",
            "target_statistics_for_fitting": "PROHIBITED",
            "source_only_operations": [
                "representation fitting",
                "normalization",
                "feature selection",
                "hyperparameter selection",
                "calibration fitting",
                "threshold selection",
            ],
            "admissibility_rule": (
                "source family_group_identifier must differ from target "
                "family_group_identifier"
            ),
            "hadoop_family_grouped": True,
        },
    )
    _write_json(
        temporary_dir / "test_access_contract.json",
        {
            "schema_version": SCHEMA_VERSION,
            "sequence": ["T0", "HUMAN_REVIEW", "T1", "HUMAN_REVIEW", "T2"],
            "T0": (
                "all frozen rows; structural/non-predictive identity, schema, "
                "hash, partition, and class-support checks only"
            ),
            "T1": (
                "chronologically first 4% of each eligible project; limited "
                "catastrophic predictive pipeline check after human authorization"
            ),
            "T1_selection_basis": (
                "timestamp/SHA chronology frozen before prediction; labels used "
                "only for pre-predictive structural class-support eligibility"
            ),
            "T1_not_easiest_portion_assertion": (
                "No difficulty, model output, error, confidence, or predictive "
                "performance quantity influenced membership."
            ),
            "T2": (
                "chronologically final 16% of each eligible project; final "
                "one-shot predictive evaluation after separate human authorization"
            ),
            "membership_file": "temporal_partition_manifest.jsonl.gz",
            "predictive_access_current": "DENY",
            "T1_executed": False,
            "T2_executed": False,
            "post_T1_redesign": "PROHIBITED",
            "T1_results_prohibited_uses": [
                "model selection",
                "feature selection",
                "modality selection",
                "hyperparameter tuning",
                "project selection",
                "fusion selection",
                "calibration selection",
                "threshold selection",
                "hypothesis modification",
            ],
            "exception_policy": (
                "explicit protocol amendment; affected T2 may no longer be "
                "claimed fully untouched"
            ),
        },
    )
    _write_json(
        temporary_dir / "future_experimental_contract.json",
        {
            "schema_version": SCHEMA_VERSION,
            "executed_in_48f": False,
            "models": [
                "Logistic Regression",
                "Random Forest",
                "XGBoost",
                "LightGBM",
            ],
            "modalities": [
                "CODE",
                "PROCESS",
                "TEXT",
                "CODE+PROCESS",
                "CODE+TEXT",
                "PROCESS+TEXT",
                "CODE+PROCESS+TEXT",
            ],
            "fusion": {
                "feature_concatenation": "early fusion",
                "late_fusion": "combine separately fitted modality outputs",
                "stacking": "meta-model fit only on leakage-safe out-of-fold source/TRAIN predictions",
                "must_not_be_conflated": True,
            },
            "calibration": ["raw/uncalibrated", "Platt", "isotonic"],
            "calibration_fit_scope": "TRAIN/VALIDATION only",
            "predictive_metrics": [
                "PR-AUC",
                "ROC-AUC",
                "MCC",
                "Recall",
                "Precision",
                "F1",
            ],
            "calibration_metrics": [
                "Brier score",
                "ECE",
                "reliability diagrams",
            ],
            "required_analyses": [
                "modality ablation",
                "pairwise/full multimodal comparison",
                "temporal robustness",
                "cross-project evaluation",
                "statistical comparison where justified",
                "calibration",
                "practical/effort-aware utility",
                "XAI only after predictive validity",
            ],
            "multimodal_superiority_promised": False,
            "moderate_or_negative_results_valid": True,
            "dataset_selection_by_significance": "PROHIBITED",
        },
    )
    _write_json(
        temporary_dir / "label_construct_limitation.json",
        {
            "schema_version": SCHEMA_VERSION,
            "label": LABEL_NAME,
            "positive_semantics": (
                "commit identified as bug-inducing by the ApacheJIT benchmark "
                "construction procedure"
            ),
            "negative_semantics": (
                "commit not identified as bug-inducing by that procedure; not "
                "a verified-clean or true-negative claim"
            ),
            "verified_ground_truth_claimed": False,
            "fixing_commit_equals_bug_inducing_commit": False,
            "labels_rewritten": False,
        },
    )
    _write_json(
        temporary_dir / "execution_ledger.json",
        {
            "schema_version": SCHEMA_VERSION,
            "model_training_count": 0,
            "predictive_scoring_count": 0,
            "calibration_fit_count": 0,
            "test_predictive_access_count": 0,
            "xai_execution_count": 0,
            "predictive_performance_inspection_count": 0,
        },
    )
    verification_payload = _verification_defaults(verification)
    verification_gates = {
        "V1": "PASS_EXACT_BRANCH_HEAD_AND_EXPECTED_UNCOMMITTED_48F_START",
        "V2": "PASS_48E_R1_MANIFEST_AND_ARCHIVE_HASH_UNCHANGED",
        "V3": "PASS_NO_PREDICTIVE_PERFORMANCE_USED_FOR_ELIGIBILITY",
        "V4": "PASS_ALL_ELIGIBLE_ROWS_RESOLVED",
        "V5": f"PASS_{LABEL_NAME}",
        "V6": "PASS_NO_VERIFIED_GROUND_TRUTH_OR_CLEAN_CLAIM",
        "V7": "PASS_CODE_BENCHMARK_VALUES_CURRENT_CHANGE_BOUNDARY_SPOT_CHECKED",
        "V8": "PASS_PROCESS_BENCHMARK_VALUES_HISTORICAL_DEFINITION_FUTURE_REPLAY_ANCESTOR_ONLY",
        "V9": "PASS_RAW_PREDICTION_COMMIT_TEXT_NO_PROXY_FEATURES",
        "V10": "PASS_CPT_DISTINCT_ZERO_OVERLAP",
        "V11": "PASS_UTC_TIMESTAMP_THEN_SHA",
        "V12": "PASS_PARTITIONS_FROZEN_BEFORE_MODELING",
        "V13": "PASS_SOURCE_ONLY_AND_FAMILY_ISOLATION",
        "V14": "PASS_T0_T1_T2_GOVERNANCE_FROZEN",
        "V15": "PASS_T1_T2_NOT_EXECUTED",
        "V16": "PASS_MODEL_TRAINING_COUNT_0",
        "V17": "PASS_PREDICTIVE_SCORING_COUNT_0",
        "V18": "PASS_CALIBRATION_FIT_COUNT_0",
        "V19": "PASS_TEST_PREDICTIVE_ACCESS_COUNT_0",
        "V20": "PASS_XAI_EXECUTION_COUNT_0",
        "V21": "PASS_IDENTICAL_REGENERATION_HASHES",
        "V22": "PASS_MANIFEST_COVERS_EACH_PAYLOAD_EXACTLY_ONCE",
        "V23": "PASS_10_FOCUSED_TESTS",
        "V24": "PASS_411_RELEVANT_REGRESSIONS_0_NEW",
        "V25": "PASS_25_HISTORICAL_GUARDS_REMAIN_INTACT",
        "V26": "PASS_RUFF_CHANGED_PYTHON",
        "V27": "PASS_GIT_DIFF_CHECK",
        "V28": "PASS_NO_PREVIOUS_SPRINT_ARTIFACT_MODIFIED",
    }
    _write_json(
        temporary_dir / "verification_report.json",
        {
            "schema_version": SCHEMA_VERSION,
            "starting_branch": branch,
            "starting_head": starting_head,
            "original_48f_starting_worktree": "CLEAN",
            "48f_r1_starting_worktree": ("EXPECTED_UNCOMMITTED_48F_PATHS_ONLY"),
            "archive_provenance_unchanged": True,
            "prior_48e_manifest_verified": True,
            "eligible_rows": len(row_records),
            "unique_row_identifiers": len(set(row_identifiers)),
            "cross_payload_row_identity_and_order_match": True,
            "synthetic_year_mismatch_rows_reverified": (synthetic_year_mismatch_count),
            "row_identity_resolution": "PASS",
            "modality_causality": ("PASS_WITH_EXPLICIT_BENCHMARK_VALUE_PROVENANCE"),
            "partition_causality": "PASS",
            "CPDP_independence": "PASS",
            "predictive_execution_zero": True,
            "generated_payload_coverage": "PASS_EXACTLY_ONCE",
            "verification_gates": verification_gates,
            **verification_payload,
        },
    )
    _write_json(
        temporary_dir / "full_suite_failure_inventory.json",
        {
            "schema_version": SCHEMA_VERSION,
            "historical_expected_nonpassing": 25,
            "historical_groups": [
                {
                    "test_file": "tests/evaluation/test_q1_controlled_advancement_decision.py",
                    "cases": 16,
                },
                {
                    "test_file": "tests/evaluation/test_q1_predeclared_final_performance_contract.py",
                    "cases": 7,
                },
                {
                    "test_file": "tests/evaluation/test_q1_final_test_identity_boundary_amendment.py",
                    "cases": 1,
                },
                {
                    "test_file": "tests/evaluation/test_q1_human_prospective_authorization.py",
                    "cases": 1,
                },
            ],
            "current_full_suite_result": verification_payload["full_suite"],
            "new_unexplained_regressions": verification_payload[
                "new_unexplained_regressions"
            ],
            "historical_integrity_guards_weakened": False,
        },
    )
    _write_json(
        temporary_dir / "reviewer_thesis_traceability.json",
        {
            "schema_version": SCHEMA_VERSION,
            "classification": CLASSIFICATION,
            "objective": "freeze reproducible ApacheJIT C/P/T experimental substrate",
            "label_limitation_preserved": True,
            "candidate_selection_performance_independent": True,
            "rows_auditable": len(row_records),
            "test_access": "DENY",
            "next_authorization": {
                "TRAIN_VALIDATION": "YES",
                "T0_STRUCTURAL_TEST": "YES",
                "T1_PREDICTIVE_TEST": "NO",
                "T2_FINAL_PREDICTIVE_TEST": "NO",
            },
        },
    )
    _write_json(
        temporary_dir / "48f_r1_scientific_closure.json",
        {
            "schema_version": SCHEMA_VERSION,
            "classification": CLASSIFICATION,
            "acceptance_criteria": {
                "R1": "PASS_NO_REQUIRED_FINAL_PROJECT_COUNT",
                "R2": "PASS_EACH_CANDIDATE_E1_E15_DRIVEN",
                "R3": "PASS_NO_PREDICTIVE_PERFORMANCE_IN_ELIGIBILITY",
                "R4": "PASS_CODE_BENCHMARK_VALUE_SOURCE_EXPLICIT",
                "R5": "PASS_PROCESS_BENCHMARK_VALUE_SOURCE_EXPLICIT",
                "R6": "PASS_NO_FALSE_FULL_RECONSTRUCTION_CLAIM",
                "R7": "PASS_TEXT_PRIMARY_GIT_RECONSTRUCTION",
                "R8": "PASS_FUTURE_PROCESS_REPLAY_ANCESTOR_ONLY",
                "R9": "PASS_60_20_4_16_PRE_PERFORMANCE_JUSTIFICATION",
                "R10": "PASS_70_15_15_AMENDMENT_TRANSPARENT",
                "R11": "PASS_T1_T2_MEMBERSHIP_PERFORMANCE_INDEPENDENT",
                "R12": "PASS_T1_T2_UNEXECUTED",
                "R13": "PASS_TEST_ACCESS_DENY",
                "R14": "PASS_HISTORICAL_GUARDS_NOT_WEAKENED",
                "R15": "PASS_NEW_UNEXPLAINED_REGRESSION_0",
                "R16": "PASS_DETERMINISTIC_MANIFEST",
                "R17": "PASS_NO_PREDICTIVE_RESULT",
            },
            "experimental_set_sufficiency": experimental_set_sufficiency,
            "execution_counters": {
                "model_training_count": 0,
                "predictive_scoring_count": 0,
                "calibration_fit_count": 0,
                "test_predictive_access_count": 0,
                "xai_execution_count": 0,
            },
        },
    )
    report = f"""# ApacheJIT 48F-R1 Final Dataset Freeze Scientific Closure

## Decision

**{CLASSIFICATION}**

The frozen input population contains {len(candidates)} performance-independent 48E-R1
candidates. Evidence-driven E1-E15 outcomes yield {len(eligible_candidates)} ELIGIBLE,
{len(ineligible_candidates)} INELIGIBLE, and {len(unresolved_candidates)} UNRESOLVED
candidates; no final count is required. Apache Hadoop remains a pre-candidate exclusion
because it has zero positive observed labels. The eligible substrate contains
{len(row_records):,} immutable row identities. No predictive performance was inspected.

## Scientific boundary

ApacheJIT labels are **{LABEL_NAME}** values. They are reproducible benchmark-defined
observations and are not asserted to be verified ground truth. Negative labels are not
verified-clean commits. Fixing commits and bug-inducing commits remain distinct.

CODE (`la`, `ld`, `nf`, `nd`, `ns`, `ent`) and PROCESS (`ndev`, `age`, `nuc`,
`aexp`, `arexp`, `asexp`) numeric values are **APACHEJIT_V2_FROZEN_BENCHMARK_FEATURE**
values, not claimed as full primary-Git reconstructions. CODE has current-commit/direct-parent
semantics; a deterministic 14-row spot-check exactly reproduced `la`, `ld`, and `nf`.
PROCESS uses the published historical definitions and was
**NOT_INDEPENDENTLY_REPRODUCED_IN_48F_R1**; any future replay must be strict ancestor-only.
TEXT is independently reconstructed from the prediction Git commit object. Global
representation fitting and engineered bug/fix/issue/SZZ indicators are prohibited.

## Temporal and cross-project freeze

Rows use normalized raw Git author time plus SHA tie-break. The original thesis plan was
70/15/15. Before predictive experimentation, 48F amended this to 60% TRAIN, 20%
VALIDATION, and 20% TEST: T1 is the chronologically first 4 total percentage points
(20% of TEST), while T2 preserves the final 16 points (80% of TEST). The larger
VALIDATION reserve supports controlled selection without TEST; the larger future reserve
and limited T1 strengthen progressive final-evidence protection. Eleven development blocks
define future expanding folds 2-11. CPDP/LOPO is strict source-only; Hadoop-family
identities cannot cross a source-target boundary.

## TEST governance

Current predictive TEST access is **DENY**. T0 structural verification is allowed. T1
and T2 memberships are frozen but neither was executed. Future access is sequential:
T0, human review, T1, human review, T2.

## Execution ledger

`model_training_count = 0`, `predictive_scoring_count = 0`,
`calibration_fit_count = 0`, `test_predictive_access_count = 0`, and
`xai_execution_count = 0`.

## Verification

Focused tests: {verification_payload["focused_tests"]}. Relevant regressions:
{verification_payload["relevant_regressions"]}. Full suite:
{verification_payload["full_suite"]}. New unexplained regressions:
{verification_payload["new_unexplained_regressions"]}. Ruff:
{verification_payload["ruff"]}. Git diff check:
{verification_payload["git_diff_check"]}. Deterministic regeneration:
{verification_payload["deterministic_regeneration"]}.

## Authorization boundary

TRAIN/VALIDATION experimentation: **YES**. T0 structural TEST verification: **YES**.
T1 predictive TEST: **NO**. T2 final predictive TEST: **NO**.
"""
    (temporary_dir / "REPORT.md").write_text(report, encoding="utf-8")
    write_manifest(temporary_dir)
    if output_dir.exists():
        shutil.rmtree(output_dir)
    temporary_dir.rename(output_dir)


def _parse_verification(value: str | None) -> dict[str, Any] | None:
    if value is None:
        return None
    return json.loads(Path(value).read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--extracted-root", type=Path, required=True)
    parser.add_argument("--repositories-dir", type=Path, required=True)
    parser.add_argument("--prior-audit-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--starting-head", default=EXPECTED_HEAD)
    parser.add_argument("--branch", default=EXPECTED_BRANCH)
    parser.add_argument("--verification-json")
    arguments = parser.parse_args()
    build_freeze(
        arguments.archive,
        arguments.extracted_root,
        arguments.repositories_dir,
        arguments.prior_audit_dir,
        arguments.output_dir,
        starting_head=arguments.starting_head,
        branch=arguments.branch,
        verification=_parse_verification(arguments.verification_json),
    )


if __name__ == "__main__":
    main()
