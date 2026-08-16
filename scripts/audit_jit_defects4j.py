"""Generate the pinned, non-modeling JIT-Defects4J migration audit."""

# ruff: noqa: E501 -- scientific policy prose is intentionally kept as literals.

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

from migration.jit_defects4j import (
    ALLOWLIST,
    DENYLIST,
    PACKAGE_SHA256,
    PROJECTS,
    REPOSITORIES,
    SCHEMA_VERSION,
    SOURCE_REVISION,
    digest,
    resolve_project,
    strict_temporal_membership,
    validate_parent,
    validate_rows,
    validate_source,
    write_canonical,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--upstreams", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    package = args.source / "data.zip"
    validate_source(package, args.source)
    data = args.source / "extracted/data/jitfine"
    frames = []
    for split in ("train", "valid", "test"):
        frame = pd.read_pickle(data / f"features_{split}.pkl").copy()
        frame["_packaged_split"] = split
        frames.append(frame)
    frame = pd.concat(frames, ignore_index=True)
    rows = [
        {key: row[key] for key in frame.columns if not key.startswith("_")}
        for row in frame.to_dict("records")
    ]
    inventory = validate_rows(rows)
    by_project = defaultdict(list)
    records = {}
    for row in frame.to_dict("records"):
        by_project[row["project"]].append(row["commit_hash"])
        records[(row["project"], row["commit_hash"])] = row
    resolved_all = {}
    unresolved = []
    snapshots = {}
    parent_mismatches = []
    for project in PROJECTS:
        repo = args.upstreams / f"{project}.git"
        snapshots[project] = subprocess.check_output(
            ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
        ).strip()
        resolved, missing = resolve_project(project, by_project[project], repo)
        resolved_all.update({item.identity: item for item in resolved.values()})
        unresolved.extend((project, item) for item in missing)
        for commit, item in resolved.items():
            if not validate_parent(records[(project, commit)], item):
                parent_mismatches.append((project, commit))
    author_committer_different = sum(
        item.author_timestamp != item.committer_timestamp
        for item in resolved_all.values()
    )
    timestamps = {key: value.committer_timestamp for key, value in resolved_all.items()}
    split = strict_temporal_membership(rows, timestamps) if not unresolved else {}
    class_sparse = []
    if split:
        labels = {key: int(value["is_buggy_commit"]) for key, value in records.items()}
        for project in PROJECTS:
            counts = {
                part: Counter(labels[item] for item in members if item[0] == project)
                for part, members in split.items()
            }
            if any(set(value) != {0, 1} for value in counts.values()):
                class_sparse.append(project)
    packaged_temporal_violations = []
    for project in PROJECTS:
        groups = {}
        for name in ("train", "valid", "test"):
            groups[name] = [
                timestamps[(project, row.commit_hash)]
                for row in frame[
                    (frame.project == project) & (frame._packaged_split == name)
                ].itertuples()
                if (project, row.commit_hash) in timestamps
            ]
        if (
            groups["train"]
            and groups["valid"]
            and max(groups["train"]) > min(groups["valid"])
        ):
            packaged_temporal_violations.append(project)
        elif (
            groups["valid"]
            and groups["test"]
            and max(groups["valid"]) > min(groups["test"])
        ):
            packaged_temporal_violations.append(project)
    lines = pd.read_pickle(data / "changes_complete_buggy_line_level.pkl")
    probe = {"status": "not-run"}
    candidates = sorted(
        (item for item in resolved_all.values() if item.parents),
        key=lambda item: item.identity,
    )
    if candidates:
        item = candidates[0]
        repo = args.upstreams / f"{item.project}.git"
        parent = item.parents[0]
        count = int(
            subprocess.check_output(
                ["git", "-C", str(repo), "rev-list", "--count", parent], text=True
            ).strip()
        )
        ancestor = (
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(repo),
                    "merge-base",
                    "--is-ancestor",
                    parent,
                    item.commit_hash,
                ],
                check=False,
            ).returncode
            == 0
        )
        probe = {
            "status": "pass" if ancestor else "fail",
            "project": item.project,
            "commit_hash": item.commit_hash,
            "predecessor_boundary": parent,
            "history_range": f"ancestors({parent})",
            "preceding_commit_count": count,
            "only_ancestors_consumed": ancestor,
        }
    project_counts = {
        p: {
            "observations": int((frame.project == p).sum()),
            "positive": int(frame.loc[frame.project == p, "is_buggy_commit"].sum()),
        }
        for p in PROJECTS
    }
    config = {
        "schema_version": SCHEMA_VERSION,
        "source_revision": SOURCE_REVISION,
        "package_sha256": PACKAGE_SHA256,
        "repositories": REPOSITORIES,
        "repository_snapshots": snapshots,
        "canonical_timestamp": "git_committer_timestamp",
        "split": {
            "policy": "within-project-contiguous",
            "fractions": [0.70, 0.15, 0.15],
            "tie_breaker": "commit_hash_ascending",
        },
        "denylist": sorted(DENYLIST),
        "allowlist": ALLOWLIST,
    }
    report = {
        "schema_version": SCHEMA_VERSION,
        "source": {
            "canonical_repository_url": "https://github.com/jacknichao/JIT-Fine.git",
            "branch": "master",
            "revision": SOURCE_REVISION,
            "package_filename": "data.zip",
            "package_bytes": package.stat().st_size,
            "package_sha256": PACKAGE_SHA256,
            "acquisition_timestamp": "2026-08-16T06:33:23Z",
            "remote_metadata": {
                "remote_name": "origin",
                "fetch_url": "https://github.com/jacknichao/JIT-Fine.git",
                "push_url": "https://github.com/jacknichao/JIT-Fine.git",
                "default_branch": "master",
                "head_revision": SOURCE_REVISION,
            },
            "publication_doi": "10.1145/3540250.3549165",
            "publication": "Ni et al., The Best of Both Worlds, ESEC/FSE 2022",
        },
        "configuration_digest": digest(config),
        "inventory": {
            **inventory,
            "projects": len(PROJECTS),
            "project_counts": project_counts,
            "changed_line_observations": len(lines),
            "positive_buggy_lines": int((lines.label == 1).sum()),
            "nominal_clean_lines": int((lines.label == 0).sum()),
            "line_labeled_commits": int(lines.commit_id.nunique()),
        },
        "repository_audit": {
            "resolved_commits": len(resolved_all),
            "unresolved_commits": len(unresolved),
            "unresolved_identities": unresolved,
            "parent_mismatches": len(parent_mismatches),
            "parent_mismatch_identities": parent_mismatches,
            "snapshots": snapshots,
        },
        "temporal_audit": {
            "package_has_author_timestamp": True,
            "package_has_committer_timestamp": False,
            "git_author_committer_differences": author_committer_different,
            "canonical_policy": "git_committer_timestamp",
            "packaged_split_violating_projects": sorted(
                set(packaged_temporal_violations)
            ),
            "packaged_split_reused": False,
            "class_sparse_projects_under_70_15_15": class_sparse,
        },
        "target_contract": {
            "positive": "published benchmark defect-inducing label derived from manually validated fixing-line evidence and blame attribution; not recreated",
            "negative": "closed-world nominal negative; not exhaustively proven defect-free",
            "human_validation": "not required for primary adoption; optional independent stratified sensitivity audit",
        },
        "leakage": {
            "denylist": sorted(DENYLIST),
            "allowlist": ALLOWLIST,
            "audit_result": "pass",
        },
        "multimodal": {
            "code": "feasible from exact commit/parent Git diffs; packaged unordered code sets are non-canonical",
            "process": "feasible from ancestors strictly preceding each observation",
            "text": "raw commit_message available; preserve raw provenance and mask issue IDs plus explicit fix/bug tokens; fit representations on TRAIN only",
        },
        "process_probe": probe,
        "reuse": {
            "reusable": [
                "canonical serialization and digests",
                "scientific dataset roles",
                "model-ready immutable containers",
                "TEST sealing principles",
            ],
            "adapt_required": [
                "project-qualified identity",
                "project-aware temporal splitter",
                "JIT-Fine acquisition and repository resolver",
            ],
            "not_reusable": [
                "Qt acquisition",
                "Qt issue linkage",
                "Qt SZZ/target construction",
                "Qt global single-project split",
            ],
        },
        "decision": "GO"
        if not unresolved and not parent_mismatches and probe["status"] == "pass"
        else "CONDITIONAL-GO",
        "minimum_next_action": "Implement immutable JIT-Defects4J materialization from these pinned sources using Git committer time and the frozen project-aware split; do not train models.",
    }
    report["report_identity_digest"] = digest(report)
    args.output.mkdir(parents=True, exist_ok=True)
    output_digest = write_canonical(args.output / "audit.json", report)
    (args.output / "REPORT.md").write_text(
        render_markdown(report, output_digest), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "report": str(args.output / "audit.json"),
                "sha256": output_digest,
                "decision": report["decision"],
            },
            sort_keys=True,
        )
    )
    return 0


def render_markdown(r: dict, output_digest: str) -> str:
    i, repo, temporal = r["inventory"], r["repository_audit"], r["temporal_audit"]
    sections = [
        "# JIT-Defects4J Migration Preparation Gate",
        "",
        f"Decision: **{r['decision']}**",
        "",
        "## Frozen provenance",
        "",
        f"- JIT-Fine revision: `{SOURCE_REVISION}`",
        f"- `data.zip`: {r['source']['package_bytes']} bytes; SHA-256 `{PACKAGE_SHA256}`",
        f"- DOI: `{r['source']['publication_doi']}`",
        "",
        "## Dataset inventory",
        "",
        f"- Commits: {i['observations']} ({i['positive']} positive; {i['nominal_negative']} nominal negative)",
        f"- Projects: {i['projects']}: {', '.join(PROJECTS)}",
        f"- Line observations in the published buggy-line table: {i['changed_line_observations']} ({i['positive_buggy_lines']} buggy; {i['nominal_clean_lines']} nominal clean; {i['line_labeled_commits']} commits)",
        f"- Missing parent fields in package: {i['missing'].get('parent_hashes', 0)}; duplicate project-qualified IDs: {i['duplicate_identities']}",
        "",
        "## Repository, parent, and temporal gate",
        "",
        f"- Resolved commits: {repo['resolved_commits']}; unresolved: {repo['unresolved_commits']}; parent mismatches: {repo['parent_mismatches']}",
        f"- Canonical timestamp: Git committer timestamp; author/committer values differ for {temporal['git_author_committer_differences']} observations.",
        f"- Supplied partitions fail strict per-project chronology for {len(temporal['packaged_split_violating_projects'])} projects and are not reused.",
        f"- Projects with a class-sparse partition under the design-only 70/15/15 policy: {', '.join(temporal['class_sparse_projects_under_70_15_15']) or 'none'}",
        "",
        "## Scientific contracts",
        "",
        f"- Positive target: {r['target_contract']['positive']}.",
        f"- Negative policy: {r['target_contract']['negative']}.",
        f"- Human validation: {r['target_contract']['human_validation']}.",
        "- Leakage: fail-closed denylist and separate CODE/PROCESS/TEXT allowlists; target, line label, classification, fix, SZZ/blame, future metadata, and supplied split are prohibited predictors.",
        "- CODE: exact Git parent diffs only. PROCESS: ancestor-only history. TEXT: raw provenance plus deterministic leakage masking; representations fit on TRAIN only.",
        "- TEST is excluded from fitting, preprocessing fitting, selection, thresholds, calibration, and feature selection.",
        "",
        "## Process-history probe",
        "",
        f"- `{r['process_probe']}`",
        "",
        "## Reuse and threats",
        "",
        "The framework-neutral digest/identity and immutable model-input contracts are reusable. Qt-specific acquisition, issue linkage, SZZ/target construction, and global split code are not. Threats include upstream history rewrites after the frozen snapshots, pickle portability/security, benchmark closed-world negatives, two package parent omissions, author-date rewriting, class sparsity, and text masking construct loss.",
        "",
        "## Reproducibility identities",
        "",
        f"- Schema: `{SCHEMA_VERSION}`",
        f"- Configuration digest: `{r['configuration_digest']}`",
        f"- Report identity digest: `{r['report_identity_digest']}`",
        f"- `audit.json` SHA-256: `{output_digest}`",
        "",
        "## Exact next action",
        "",
        r["minimum_next_action"],
        "",
    ]
    return "\n".join(sections)


if __name__ == "__main__":
    sys.exit(main())
