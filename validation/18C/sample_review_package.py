#!/usr/bin/env python3
"""Build the frozen 18C candidate sample and blinded review packages.

This script never reads production assignments, model inputs, features, or SZZ data.
It deliberately refuses to describe the output as independent validation while the
historical 18-case exclusion set is unavailable.
"""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "validation" / "18C"
SEED = "SPRINT-10.8.2.18C.4-PROSPECTIVE-2026-08-14"
TARGET_SIZE = 48
SOURCE_HEAD = "3388cd919ab72af3ab1ed78af11edc8637fddc62"

LINKS = ROOT / "artifacts/derived/qtbase-commit-issue-links.json"
COMMITS = ROOT / "artifacts/raw/qtbase-commits.json"
ISSUES = ROOT / "artifacts/qtbase/issues/qtbug-cloud-60b32ea8c64ec02c/qt-issues.jsonl"
DIFFS = ROOT / "artifacts/qtbase/diffs/a1af25290bbd078628e362d4b704a047853d620c/qt-commit-diffs.jsonl"
STATS = ROOT / "artifacts/qtbase/diff-statistics/a1af25290bbd078628e362d4b704a047853d620c/qt-diff-statistics.jsonl"


def load(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def relation_id(link: dict[str, Any]) -> str:
    raw = "|".join(
        [link["commit_revision"], link["issue_identifier"], link["reference_type"], link["reference_location"]]
    )
    return "rel-sha256:" + hashlib.sha256(raw.encode()).hexdigest()


def temporal(commit: dict[str, Any], issue: dict[str, Any]) -> str:
    ct, it = parse_time(commit.get("committed_at")), parse_time(issue.get("created_timestamp"))
    if ct is None or it is None:
        return "UNKNOWN"
    return "ADMISSIBLE" if ct >= it else "INADMISSIBLE"


def deletion_band(stat: dict[str, Any] | None) -> str:
    if stat is None:
        return "missing"
    ins, dels = stat.get("insertions", 0), stat.get("deletions", 0)
    if dels == 0:
        return "none"
    if ins == 0:
        return "deletion-only"
    if dels > ins:
        return "deletion-dominant"
    return "mixed"


def change_family(diff: dict[str, Any] | None) -> str:
    if diff is None:
        return "missing"
    paths = [str(f.get("path") or f.get("new_path") or f.get("old_path") or "").lower() for f in diff.get("file_changes", [])]
    if paths and all("test" in p or "auto/" in p for p in paths):
        return "test-only"
    if paths and all(p.endswith((".md", ".txt", ".qdoc", ".qdocconf")) or "/doc" in p for p in paths):
        return "documentation-only"
    return "source-or-mixed"


def excerpt(diff: dict[str, Any] | None) -> str:
    if diff is None:
        return ""
    pieces: list[str] = []
    for file_change in diff.get("file_changes", [])[:6]:
        path = file_change.get("path") or file_change.get("new_path") or file_change.get("old_path") or "<unknown>"
        pieces.append(
            f"{file_change.get('change_type', 'unknown')} {path} "
            f"(+{file_change.get('additions', 0)}/-{file_change.get('deletions', 0)})"
        )
        for hunk in file_change.get("hunks", [])[:2]:
            text = hunk.get("patch") or hunk.get("text") or hunk.get("content") or ""
            if text:
                pieces.append(str(text)[:1200])
    return "\n".join(pieces)[:5000]


def seeded_rank(rel_id: str) -> str:
    return hashlib.sha256(f"{SEED}|{rel_id}".encode()).hexdigest()


def stress_flags(record: dict[str, Any]) -> list[str]:
    # Observable keyword/path triggers only: these are coverage flags, not judgments.
    text = (record["commit_message"] + "\n" + record["issue_summary"] + "\n" + record["issue_description"]).lower()
    flags = []
    patterns = {
        "assertive_non_corrective_candidate": ("support", "implement", "add "),
        "mitigation_candidate": ("mitigat", "workaround", "avoid "),
        "suppression_candidate": ("suppress", "disable", "ignore "),
        "reversal_of_suppression_candidate": ("re-enable", "reenable", "remove suppression", "undo disable"),
        "future_fix_claim_candidate": ("will be fixed", "fix will", "follow-up", "subsequent commit"),
        "housekeeping_or_provenance_candidate": ("cherry-pick", "merge", "sync", "cleanup", "typo"),
    }
    for name, needles in patterns.items():
        if any(needle in text for needle in needles):
            flags.append(name)
    if record["change_family"] == "test-only":
        flags.append("test_only")
    if record["temporal_relation"] != "ADMISSIBLE":
        flags.append("temporal_anomaly")
    if record["issue_description_availability"] == "absent-or-weak":
        flags.append("weak_or_absent_issue_description")
    if record["deletion_band"] in {"deletion-only", "deletion-dominant"}:
        flags.append(record["deletion_band"])
    return sorted(flags)


def main() -> None:
    links_doc, commits_doc, issues_doc = load(LINKS), load(COMMITS), load(ISSUES)
    diffs_doc, stats_doc = load(DIFFS), load(STATS)
    commits = {r["commit_id"]: r for r in commits_doc["records"]}
    issues = {r["issue_identifier"]: r for r in issues_doc["issues"]}
    diffs = {r["commit_identifier"]: r for r in diffs_doc.get("commit_diffs", [])}
    stat_records = stats_doc.get("commit_statistics") or stats_doc.get("records") or []
    stats = {r["commit_identifier"]: r for r in stat_records}

    candidates = []
    seen = set()
    for link in links_doc["links"]:
        rid = relation_id(link)
        if rid in seen or link["commit_revision"] not in commits or link["issue_identifier"] not in issues:
            continue
        seen.add(rid)
        commit, issue = commits[link["commit_revision"]], issues[link["issue_identifier"]]
        diff, stat = diffs.get(link["commit_revision"]), stats.get(link["commit_revision"])
        description = str(issue.get("description") or "")
        record = {
            "review_record_id": "18C4-" + rid[-12:],
            "relationship_identifier": rid,
            "commit_revision": link["commit_revision"],
            "issue_identifier": link["issue_identifier"],
            "source_relationship_artifact_digest": link.get("artifact_digest"),
            "reference_location": link["reference_location"],
            "reference_type": link["reference_type"],
            "commit_message": commit.get("message", ""),
            "issue_summary": issue.get("summary", ""),
            "issue_description": description,
            "issue_type": issue.get("issue_type"),
            "issue_status": issue.get("status"),
            "issue_resolution": issue.get("resolution"),
            "issue_created_timestamp": issue.get("created_timestamp"),
            "issue_resolved_timestamp": issue.get("resolved_timestamp"),
            "commit_timestamp": commit.get("committed_at"),
            "temporal_relation": temporal(commit, issue),
            "diff_availability": "available" if diff else "missing",
            "diff_summary_excerpt": excerpt(diff),
            "insertions": None if stat is None else stat.get("insertions"),
            "deletions": None if stat is None else stat.get("deletions"),
            "files_changed": None if stat is None else stat.get("files_changed"),
            "deletion_band": deletion_band(stat),
            "change_family": change_family(diff),
            "issue_description_availability": "present" if len(description.strip()) >= 40 else "absent-or-weak",
        }
        record["artifact_digest"] = digest(record)
        record["stress_condition_candidates"] = stress_flags(record)
        candidates.append(record)

    # Greedily maximize observable stratum/stress coverage; ties use frozen seeded rank.
    dimensions = ["reference_type", "temporal_relation", "diff_availability", "deletion_band", "change_family", "issue_description_availability"]
    uncovered = {(d, r[d]) for r in candidates for d in dimensions}
    uncovered |= {("stress", flag) for r in candidates for flag in r["stress_condition_candidates"]}
    selected, remaining = [], list(candidates)
    while remaining and len(selected) < TARGET_SIZE:
        def score(r: dict[str, Any]) -> tuple[int, str]:
            tokens = {(d, r[d]) for d in dimensions} | {("stress", f) for f in r["stress_condition_candidates"]}
            return (-len(tokens & uncovered), seeded_rank(r["relationship_identifier"]))
        choice = min(remaining, key=score)
        selected.append(choice)
        remaining.remove(choice)
        uncovered -= {(d, choice[d]) for d in dimensions}
        uncovered -= {("stress", f) for f in choice["stress_condition_candidates"]}

    selected.sort(key=lambda r: r["review_record_id"])
    package_path = HERE / "blinded_review_package.jsonl"
    with package_path.open("w", encoding="utf-8") as handle:
        for record in selected:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    form_fields = [
        "review_record_id", "relationship_identifier", "artifact_digest", "P", "S", "C", "I", "D", "M", "T",
        "fixing_decision", "unresolved_reason", "evidence_rationale", "reviewer_id", "review_round", "completed_at_utc",
    ]
    for reviewer in ("A", "B"):
        with (HERE / f"reviewer_{reviewer}_form.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=form_fields)
            writer.writeheader()
            for record in selected:
                writer.writerow({k: record.get(k, "") for k in form_fields})

    strata = {d: {} for d in dimensions}
    for record in selected:
        for d in dimensions:
            strata[d][record[d]] = strata[d].get(record[d], 0) + 1
    stress = sorted({flag for r in selected for flag in r["stress_condition_candidates"]})
    inputs = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in (LINKS, COMMITS, ISSUES, DIFFS, STATS)}
    outputs = {}
    for name in ("protocol.json", "decision_matrix.csv", "field_definitions.md", "recovery_and_gate.md", "reviewer_instructions.md", "review_form_template.csv", "sample_review_package.py", "blinded_review_package.jsonl", "reviewer_A_form.csv", "reviewer_B_form.csv"):
        path = HERE / name
        outputs[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest = {
        "protocol_id": "PROSPECTIVE_ALTERNATIVE_B_V1",
        "source_head": SOURCE_HEAD,
        "seed": SEED,
        "algorithm": "deterministic greedy observable-coverage then SHA-256 seeded order",
        "eligible_relationship_count": len(candidates),
        "sample_size": len(selected),
        "independence_status": "NOT_DEMONSTRATED",
        "human_review_status": "HUMAN_REVIEW_REQUIRED_AFTER_INDEPENDENCE_GATE",
        "strata_counts": strata,
        "represented_observable_stress_candidates": stress,
        "input_sha256": inputs,
        "artifact_sha256": outputs,
        "z_szz_fields_present": False,
        "agreement_statistics_present": False,
    }
    (HERE / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
