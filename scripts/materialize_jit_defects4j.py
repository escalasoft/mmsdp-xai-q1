"""Materialize the canonical JIT-Defects4J CODE/PROCESS/TEXT dataset."""

# ruff: noqa: E501 -- scientific policy prose is intentionally literal.

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

from dataset.jit_defects4j_materialization import (
    CODE_FIELDS,
    DATASET_VERSION,
    MISSING_TEXT_SENTINEL,
    PARTITIONS,
    PROCESS_FIELDS,
    SCHEMA_VERSION,
    TEXT_FIELDS,
    ancestor_process_features,
    assign_split,
    canonical_jsonl,
    git_raw_diff,
    normalize_text,
    summarize,
    validate_predictor_schema,
    write_immutable,
)
from migration.jit_defects4j import (
    DENYLIST,
    PACKAGE_SHA256,
    PROJECTS,
    REPOSITORIES,
    SOURCE_REVISION,
    canonical_bytes,
    digest,
    resolve_project,
    validate_parent,
    validate_rows,
    validate_source,
)

ROOT = Path(__file__).resolve().parents[1]


def _load_rows(source: Path) -> list[dict[str, object]]:
    frames = []
    data = source / "extracted/data/jitfine"
    for supplied in ("train", "valid", "test"):
        frame = pd.read_pickle(data / f"features_{supplied}.pkl")
        frames.append(frame)
    combined = pd.concat(frames, ignore_index=True)
    return combined.to_dict("records")


def _configuration() -> dict[str, object]:
    return json.loads(
        (ROOT / "configs/jit_defects4j_materialization.json").read_text(
            encoding="utf-8"
        )
    )


def _git_revision() -> str | None:
    result = subprocess.run(
        ("git", "-C", str(ROOT), "rev-parse", "HEAD"),
        text=True,
        capture_output=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def materialize(source: Path, upstreams: Path, output: Path) -> dict[str, object]:
    validate_source(source / "data.zip", source)
    config = _configuration()
    schemas = {"code": CODE_FIELDS, "process": PROCESS_FIELDS, "text": TEXT_FIELDS}
    validate_predictor_schema(schemas)
    rows = _load_rows(source)
    inventory = validate_rows(rows)
    by_project: dict[str, list[str]] = {project: [] for project in PROJECTS}
    source_rows: dict[tuple[str, str], dict[str, object]] = {}
    for row in rows:
        identity = (str(row["project"]), str(row["commit_hash"]))
        by_project[identity[0]].append(identity[1])
        source_rows[identity] = row

    resolved = {}
    snapshots = {}
    for project in PROJECTS:
        repository = upstreams / f"{project}.git"
        values, missing = resolve_project(project, by_project[project], repository)
        if missing:
            raise RuntimeError(f"unresolved {project} commits: {len(missing)}")
        for commit, item in values.items():
            row = source_rows[(project, commit)]
            if row["parent_hashes"] and not validate_parent(row, item):
                raise RuntimeError(f"parent mismatch: {project}/{commit}")
        resolved.update({item.identity: item for item in values.values()})
        snapshots[project] = subprocess.check_output(
            ("git", "-C", str(repository), "rev-parse", "HEAD"), text=True
        ).strip()

    memberships = assign_split(rows, resolved)
    process_by_identity = {}
    code_by_identity = {}
    for project in PROJECTS:
        repository = upstreams / f"{project}.git"
        commits = by_project[project]
        history = ancestor_process_features(project, commits, repository)
        process_by_identity.update(
            {(project, commit): values for commit, values in history.items()}
        )
        with ThreadPoolExecutor(max_workers=8) as executor:
            values = executor.map(
                lambda commit: git_raw_diff(commit, repository), commits
            )
            code_by_identity.update(
                {(project, commit): value for commit, value in zip(commits, values)}
            )

    ordered_identities = sorted(
        resolved,
        key=lambda identity: (
            identity[0],
            resolved[identity].committer_timestamp,
            identity[1],
        ),
    )
    observations = []
    code_rows = []
    process_rows = []
    text_rows = []
    missing_text = 0
    for identity in ordered_identities:
        project, commit = identity
        source_row, git = source_rows[identity], resolved[identity]
        text, was_missing = normalize_text(source_row["commit_message"])
        missing_text += int(was_missing)
        base = {"project": project, "commit_hash": commit}
        observations.append(
            {
                **base,
                "git_committer_timestamp": git.committer_timestamp,
                "parent_hashes": list(git.parents),
                "parent_status": "root" if not git.parents else "resolved",
                "target": int(source_row["is_buggy_commit"]),
                "split": memberships[identity],
                "modalities": {
                    "code": "available",
                    "process": "available",
                    "text": "missing-sentinel" if was_missing else "available",
                },
            }
        )
        code_rows.append({**base, **code_by_identity[identity]})
        process_rows.append({**base, **process_by_identity[identity]})
        text_rows.append(
            {**base, "raw_commit_message": text, "was_missing": was_missing}
        )

    counts, sparse = summarize(observations)
    if counts["observations"] != inventory["observations"]:
        raise RuntimeError("target universe changed during materialization")
    artifact_payloads = {
        "observations.jsonl": canonical_jsonl(observations),
        "code.jsonl": canonical_jsonl(code_rows),
        "process.jsonl": canonical_jsonl(process_rows),
        "text.jsonl": canonical_jsonl(text_rows),
    }
    schema = {
        "schema_version": SCHEMA_VERSION,
        "observation_identity": ["project", "commit_hash"],
        "target": {
            "field": "target",
            "positive": "published JIT-Fine benchmark defect-inducing commit label derived from manually validated fixing-line evidence and blame attribution; preserved, not recreated",
            "negative": "closed-world nominal negative under the published benchmark; not an exhaustively proven defect-free commit",
        },
        "timestamp": "Git committer timestamp from the pinned project repository",
        "split": config["split"],
        "predictors": {
            "code": {
                "fields": list(CODE_FIELDS),
                "source": "exact Git current-vs-parent/root raw tree diff without rename inference",
                "raw": ["file_changes"],
                "derived": [
                    "files_added",
                    "files_deleted",
                    "files_modified",
                    "files_other",
                ],
                "missing_policy": "empty change list and zero counts for an empty diff",
                "availability": "commit-current",
            },
            "process": {
                "fields": list(PROCESS_FIELDS),
                "source": "pinned Git repository commit graph",
                "raw": [],
                "derived": list(PROCESS_FIELDS),
                "missing_policy": "root commits have zero parents/history and false indicators",
                "availability": "strict ancestors(C), excluding C and descendants",
            },
            "text": {
                "fields": list(TEXT_FIELDS),
                "source": "published canonical commit_message",
                "raw": list(TEXT_FIELDS),
                "derived": [],
                "missing_policy": MISSING_TEXT_SENTINEL,
                "availability": "commit-current",
            },
        },
    }
    denylist = {
        "policy": "fail-closed predictor exclusion",
        "prohibited_predictors": sorted(DENYLIST),
        "schemas_checked": {key: list(value) for key, value in schemas.items()},
        "result": "pass",
    }
    artifact_payloads["schema.json"] = canonical_bytes(schema)
    artifact_payloads["predictor_denylist.json"] = canonical_bytes(denylist)
    digests = {
        name: write_immutable(output / name, payload)
        for name, payload in artifact_payloads.items()
    }
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "dataset_version": DATASET_VERSION,
        "source": {
            "repository": "https://github.com/jacknichao/JIT-Fine.git",
            "revision": SOURCE_REVISION,
            "package": "data.zip",
            "package_sha256": PACKAGE_SHA256,
            "project_repositories": REPOSITORIES,
            "project_repository_snapshots": snapshots,
        },
        "materialization_configuration_digest": digest(config),
        "code_revision": _git_revision(),
        "temporal_policy": config["split"],
        "observation_identity": ["project", "commit_hash"],
        "predictor_schemas": {key: list(value) for key, value in schemas.items()},
        "counts": counts,
        "class_sparse_partitions": sparse,
        "missingness": {"commit_message": missing_text},
        "audits": {
            "identity_unique": True,
            "cross_split_overlap": 0,
            "leakage_denylist": "pass",
            "process_ancestor_only": "pass",
            "target_preserved": True,
        },
        "artifacts": {
            name: {"sha256": value} for name, value in sorted(digests.items())
        },
    }
    manifest["scientific_identity_digest"] = digest(manifest)
    manifest_digest = write_immutable(
        output / "manifest.json", canonical_bytes(manifest)
    )
    return {**manifest, "manifest_sha256": manifest_digest}


def render_report(manifest: dict[str, object]) -> str:
    counts = manifest["counts"]
    lines = [
        "# Canonical JIT-Defects4J Multimodal Dataset Audit",
        "",
        "Decision: **GO**",
        "",
        "## Inventory and frozen temporal split",
        "",
        f"- Observations: {counts['observations']} ({counts['positive']} positive; {counts['nominal_negative']} nominal negative).",
    ]
    for partition in PARTITIONS:
        item = counts["splits"][partition]
        lines.append(
            f"- {partition.upper()}: {item['observations']} ({item['positive']} positive; {item['nominal_negative']} nominal negative; prevalence {item['positive_prevalence']:.8f})."
        )
    lines.extend(
        [
            "- Projects: 21.",
            f"- Class-sparse project partitions: {len(manifest['class_sparse_partitions'])}; see manifest for exact entries.",
            "- Identity uniqueness: PASS; cross-partition overlap: 0.",
            "",
            "## Predictor contracts",
            "",
            "- CODE: exact Git parent/root raw tree changes: path, status, modes, old/new blob identities, and status counts.",
            "- PROCESS: parent count, merge indicator, prior-history indicator, and exact count of commits in ancestors(C). Descendants and C itself are excluded.",
            f"- TEXT: canonical raw commit message; missing values use `{MISSING_TEXT_SENTINEL}`.",
            "- Leakage denylist: PASS. Targets, line labels, fix/SZZ/blame/future/post-observation metadata, label-derived fields, and supplied partitions are excluded.",
            "",
            "## Reproducibility",
            "",
            f"- Source revision: `{SOURCE_REVISION}`.",
            f"- Package SHA-256: `{PACKAGE_SHA256}`.",
            f"- Scientific identity: `{manifest['scientific_identity_digest']}`.",
            f"- Manifest SHA-256: `{manifest['manifest_sha256']}`.",
            "- Every scientific artifact is canonically serialized and SHA-256 identified in `manifest.json`.",
            "",
            "## Per-project counts and class sparsity",
            "",
            "| Project | Split | N | Positive | Nominal negative | Prevalence | Sparse |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    sparse_keys = {
        (x["project"], x["split"]) for x in manifest["class_sparse_partitions"]
    }
    for project in PROJECTS:
        for partition in PARTITIONS:
            item = counts["per_project"][project][partition]
            lines.append(
                f"| {project} | {partition} | {item['observations']} | {item['positive']} | {item['nominal_negative']} | {item['positive_prevalence']:.8f} | {'yes' if (project, partition) in sparse_keys else 'no'} |"
            )
    lines.extend(
        [
            "",
            "## Limitations",
            "",
            "Nominal negatives retain the benchmark's closed-world semantics. CODE is a deterministic tree-change representation, not raw patch text or a learned encoding; rename similarity is deliberately not inferred. PROCESS intentionally favors a small auditable ancestor-only schema. No model, vectorizer, embedding, calibration, fusion, or explanation was fit.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--upstreams", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--audit-output", type=Path)
    args = parser.parse_args()
    manifest = materialize(args.source, args.upstreams, args.output)
    if args.audit_output:
        args.audit_output.mkdir(parents=True, exist_ok=True)
        (args.audit_output / "REPORT.md").write_text(
            render_report(manifest), encoding="utf-8"
        )
        (args.audit_output / "audit.json").write_bytes(canonical_bytes(manifest))
    print(
        json.dumps(
            {"decision": "GO", "manifest_sha256": manifest["manifest_sha256"]},
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
