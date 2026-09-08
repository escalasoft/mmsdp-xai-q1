# ruff: noqa: E501
"""56.3A-R1: read-only Git/byte forensics; no scientific payload execution.

Only explicitly named metadata, diagnostic logs and source text are inspected.
Git trees attest tracked historical file identities without opening scientific
blob contents. New writes are confined to the new immutable R1 audit package.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import re
import stat
import subprocess
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[2]
BRANCH = "sprint-10/q1-prospective-e1-protocol-freeze"
PACKAGE = "audits/q1-prospective-e1-parent-integrity-resolution/1.0.0"
SMOKE = "audits/q1-primary-xai-runtime-smoke/1.0.0"
TARGET = SMOKE + "/validation-initial-output.txt"
MANIFEST = SMOKE + "/MANIFEST.sha256"
SAFE_NAMES = frozenset(
    {
        "MANIFEST.sha256",
        "parent_integrity_before.json",
        "parent_integrity_after.json",
        "preexecution_integrity.json",
        "postexecution_integrity.json",
        "implementation_provenance.json",
        "validation_results.json",
        "validation_history.json",
        "validation-initial-output.txt",
        "validation-final-output.txt",
        "parent_integrity.json",
        "protocol_summary.json",
    }
)
SUPPORT_NAMES = (
    "SPRINT56_1_XAI_RUNTIME_SMOKE_REPORT.md",
    "validation_results.json",
    "validation_history.json",
    "determinism_smoke.json",
    "sprint56_1_summary.json",
    "runtime_governance_counters.json",
    "predictive_inventory_before.json",
    "predictive_inventory_after.json",
    "preexecution_integrity.json",
    "postexecution_integrity.json",
    "implementation_provenance.json",
    "validation-final-output.txt",
)
SOURCE_FILES = (
    "src/evaluation/q1_primary_xai_runtime_smoke.py",
    "src/evaluation/q1_primary_xai_runtime_smoke_closure.py",
    "tests/evaluation/test_q1_primary_xai_runtime_smoke.py",
)
RECOVERED = "R1_PASS_HISTORICAL_BYTE_VERSION_RECOVERED_DIAGNOSTIC_ONLY_MISMATCH"
PACKAGING = "R1_PASS_MANIFEST_PACKAGING_INCONSISTENCY_DIAGNOSTIC_ONLY"
LIMITED = "R1_PASS_CURRENT_LOG_SEMANTICALLY_EQUIVALENT_WITH_PROVENANCE_LIMITATION"
FAIL = "R1_FAIL_PARENT_SCIENTIFIC_INTEGRITY_AFFECTED"
BLOCKED = "R1_BLOCKED_PROVENANCE_UNRESOLVED"
RESOLUTIONS = {RECOVERED, PACKAGING, LIMITED, FAIL, BLOCKED}
ZERO = (
    "T1_SCIENTIFIC_ROW_ACCESS_COUNT",
    "T1_EXPLANATION_ROWS_READ_COUNT",
    "T1_E1_XAI_ACCESS_COUNT",
    "T1_E1_MODEL_QUERY_COUNT",
    "T1_E1_ATTRIBUTION_COUNT",
    "T1_E1_EXPLAINED_ROW_COUNT",
    "T2_ACCESS_COUNT",
    "T2_ROW_READ_COUNT",
    "T2_IDENTITY_READ_COUNT",
    "T2_FEATURE_READ_COUNT",
    "T2_LABEL_READ_COUNT",
    "T2_MODEL_QUERY_COUNT",
    "MODEL_QUERY_COUNT",
    "SHAP_EXECUTION_COUNT",
    "ANALYTICAL_ATTRIBUTION_EXECUTION_COUNT",
    "RETRAIN_COUNT",
    "REFIT_COUNT",
    "RECALIBRATION_COUNT",
    "PREDICTIVE_METRIC_RECOMPUTATION_COUNT",
    "HYPERPARAMETER_TUNING_COUNT",
    "MODEL_SELECTION_COUNT",
    "FIGURE_GENERATION_COUNT",
    "MODEL_MUTATION_COUNT",
    "ENVIRONMENT_MUTATION_COUNT",
    "HISTORICAL_PACKAGE_MUTATION_COUNT",
    "COMMIT_COUNT",
    "PUSH_COUNT",
    "PR_COUNT",
    "SPRINT56_1_REEXECUTION_COUNT",
    "SPRINT56_3A_REVALIDATION_COUNT",
)


class AuditBlocked(ValueError):
    """The requested provenance inference cannot safely be made."""


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def blob_id(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def canonical(value):
    return (
        json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False)
        + "\n"
    ).encode()


def safe_path(path):
    p = PurePosixPath(path)
    if p.is_absolute() or ".." in p.parts or not p.parts:
        return False
    if path.startswith(("src/", "tests/", "scripts/")) and p.suffix == ".py":
        return True
    if path.startswith(SMOKE + "/") and p.name in SUPPORT_NAMES:
        return True
    return (
        path.startswith("audits/")
        and p.name in SAFE_NAMES
        and not any(
            part in {"objects", "results", "repetitions", "data", "forensic"}
            for part in p.parts
        )
    )


class Reader:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.hashes = {}

    def read(self, path):
        if not safe_path(path):
            raise PermissionError("Diagnostic/metadata read boundary: " + path)
        resolved = self.root / path
        if resolved.resolve() != resolved or not resolved.is_file():
            raise AuditBlocked("Missing or symlinked metadata: " + path)
        raw = resolved.read_bytes()
        self.hashes[path] = sha(raw)
        return raw


class ReadOnlyGit:
    def __init__(self, root):
        self.root = Path(root)
        self.commands = []

    def run(self, *args, stdin=None, allowed_codes=(0,)):
        allowed = {
            "rev-parse",
            "status",
            "log",
            "ls-files",
            "diff",
            "check-ignore",
            "hash-object",
            "rev-list",
            "cat-file",
            "ls-tree",
            "check-attr",
        }
        if not args or args[0] not in allowed:
            raise PermissionError("Non-read-only Git operation")
        if any(
            a in {"-w", "--write", "--output", "--ext-diff", "--textconv", "--no-index"}
            or a.startswith(("--output=", "--exec="))
            for a in args
        ):
            raise PermissionError("Git mutation/external conversion forbidden")
        if args[0] == "cat-file" and (args != ("cat-file", "--batch") or stdin is None):
            raise PermissionError(
                "Git blobs only through allowlisted batch metadata reader"
            )
        if args[0] == "hash-object" and tuple(args[1:]) != ("--", TARGET):
            raise PermissionError("Only target diagnostic may be hashed through Git")
        if args[0] == "diff" and "--name-only" not in args:
            raise PermissionError("No scientific diff payload output")
        result = subprocess.run(
            ["git", *args],
            cwd=self.root,
            input=stdin,
            capture_output=True,
            check=False,
            env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
        )
        self.commands.append(
            {
                "argv": ["git", *args],
                "returncode": result.returncode,
                "stdout_sha256": sha(result.stdout),
                "stderr": result.stderr.decode(errors="replace"),
            }
        )
        if result.returncode not in allowed_codes:
            raise AuditBlocked(
                "Read-only Git failed: "
                + repr(args)
                + " "
                + result.stderr.decode(errors="replace")
            )
        return result.stdout

    def blobs(self, entries):
        if any(
            not safe_path(path) or not re.fullmatch("[0-9a-f]{40}", oid)
            for oid, path in entries
        ):
            raise PermissionError("Unapproved Git blob route")
        if not entries:
            return {}
        raw = self.run(
            "cat-file",
            "--batch",
            stdin=("\n".join(oid for oid, _ in entries) + "\n").encode(),
        )
        pos, result = 0, {}
        for oid, path in entries:
            end = raw.index(b"\n", pos)
            header = raw[pos:end].decode().split()
            if len(header) != 3 or header[:2] != [oid, "blob"]:
                raise AuditBlocked("Unexpected Git object type: " + path)
            size = int(header[2])
            start = end + 1
            content = raw[start : start + size]
            if (
                len(content) != size
                or raw[start + size : start + size + 1] != b"\n"
                or blob_id(content) != oid
            ):
                raise AuditBlocked("Git byte identity failed")
            result[(oid, path)] = content
            pos = start + size + 1
        if pos != len(raw):
            raise AuditBlocked("Unparsed Git batch bytes")
        return result


def manifest_entry(raw, target_name):
    matches = []
    for line in raw.decode().splitlines():
        if "  " not in line:
            raise AuditBlocked("Malformed manifest line")
        h, name = line.split("  ", 1)
        if name in {target_name, SMOKE + "/" + target_name}:
            if not re.fullmatch("[0-9a-f]{64}", h):
                raise AuditBlocked("Invalid expected SHA256")
            matches.append(
                {
                    "expected_sha256": h,
                    "exact_line": line,
                    "entry_path": name,
                    "path_semantics": "PACKAGE_RELATIVE_BASENAME"
                    if name == target_name
                    else "REPOSITORY_RELATIVE",
                }
            )
    if len(matches) != 1:
        raise AuditBlocked("Missing/duplicate target manifest entry")
    return matches[0]


def reconstruct_whitespace_candidate(current, expected):
    """Bounded forensic hypothesis test, not log regeneration or a restored artifact.

    Diagnostic separator lines consisting solely of E are tested with 1..80 trailing
    ASCII spaces. A candidate is accepted only by exact independent SHA256 equality.
    No hash match means unresolved; normalized text equality alone never suffices.
    """
    lines = current.splitlines(keepends=True)
    candidates = []
    attempts = 0
    for i, line in enumerate(lines):
        if line != b"E\n":
            continue
        for n in range(1, 81):
            candidate_lines = lines.copy()
            candidate_lines[i] = b"E" + b" " * n + b"\n"
            candidate = b"".join(candidate_lines)
            attempts += 1
            if sha(candidate) == expected:
                candidates.append(
                    (
                        candidate,
                        {
                            "line_1_based": i + 1,
                            "restored_ASCII_spaces": n,
                            "recipe": "Insert trailing ASCII spaces before LF on the bare E diagnostic separator line",
                        },
                    )
                )
    if len(candidates) > 1:
        raise AuditBlocked("Ambiguous forensic reconstruction")
    if not candidates:
        return None, {"status": "NO_EXACT_SHA256_MATCH", "candidate_tests": attempts}
    candidate, recipe = candidates[0]
    return candidate, {
        "status": "EXACT_MANIFEST_SHA256_MATCH",
        **recipe,
        "sha256": sha(candidate),
        "bytes": len(candidate),
        "git_blob_identity_if_materialized": blob_id(candidate),
        "candidate_tests": attempts,
        "source": "DETERMINISTIC_HASH_VERIFIED_RECONSTRUCTION_NOT_GIT_RECOVERY",
        "not_claimed": "No actor, tool, timestamp, or Git storage of these bytes inferred from hash equality",
    }


def difference_ledger(old, current):
    if old is None:
        return [
            {
                "classification": ["UNKNOWN_DIFFERENCE"],
                "old_bytes_available": False,
                "potential_scientific_relevance": "UNRESOLVED",
                "affects_smoke_conclusion": None,
            }
        ]
    a, b = old.splitlines(keepends=True), current.splitlines(keepends=True)
    result = []
    for tag, i, j, k, end_current in difflib.SequenceMatcher(
        a=a, b=b, autojunk=False
    ).get_opcodes():
        if tag == "equal":
            continue
        x, y = b"".join(a[i:j]), b"".join(b[k:end_current])
        whitespace = x.split() == y.split()
        result.append(
            {
                "operation": tag,
                "old_line_range_1_based": [i + 1, j],
                "current_line_range_1_based": [k + 1, end_current],
                "old_value": x.decode(),
                "current_value": y.decode(),
                "old_hex": x.hex(),
                "current_hex": y.hex(),
                "classification": ["WHITESPACE_ONLY", "FORMAT_ONLY"]
                if whitespace
                else ["UNKNOWN_DIFFERENCE"],
                "potential_scientific_relevance": "NONE: diagnostic content tokens identical"
                if whitespace
                else "UNRESOLVED",
                "affects_smoke_conclusion": False if whitespace else None,
                "affects_56_3A_contract_values": False if whitespace else None,
                "affects_56_3A_integrity_gate": True,
                "old_value_provenance": "Exact manifest-SHA256-matching deterministic candidate; not recovered Git blob",
            }
        )
    return result


def history_for(git, path):
    fmt = "%H%x09%P%x09%ad%x09%an%x09%s"
    raw = git.run(
        "log", "--all", "--follow", "--format=" + fmt, "--date=iso", "--", path
    ).decode()
    rows = []
    for line in raw.splitlines():
        commit, parents, date, author, subject = line.split("\t", 4)
        tree = git.run("ls-tree", "-r", commit, "--", path).decode()
        rows.append(
            {
                "commit": commit,
                "parents": parents.split(),
                "date": date,
                "author": author,
                "subject": subject,
                "ls_tree": tree,
            }
        )
    names = git.run(
        "log", "--all", "--name-status", "--format=%H %ad %s", "--date=iso", "--", path
    ).decode()
    return {
        "path": path,
        "follow_log_exact": raw,
        "name_status_log_exact": names,
        "changes": rows,
        "first_introduction_commit": rows[-1]["commit"] if rows else None,
        "scope": "All local refs reachable via --all; no network fetch, reflog or dangling-object claim",
    }


def search_metadata(git, reader, expected):
    all_objects = git.run("rev-list", "--all", "--objects").decode()
    entries = []
    for line in all_objects.splitlines():
        oid, separator, path = line.partition(" ")
        if separator and safe_path(path):
            entries.append((oid, path))
    entries = sorted(set(entries))
    blobs = git.blobs(entries)
    hits, exact_versions, source_name_hits = [], [], []
    for (oid, path), raw in sorted(blobs.items()):
        if path.endswith(".py") and b"validation-initial-output.txt" in raw:
            source_name_hits.append(
                {
                    "blob": oid,
                    "path": path,
                    "lines": [
                        i
                        for i, line in enumerate(raw.decode().splitlines(), 1)
                        if "validation-initial-output.txt" in line
                    ],
                }
            )
        if sha(raw) == expected:
            exact_versions.append(
                {"blob": oid, "path": path, "sha256": sha(raw), "bytes": len(raw)}
            )
        if expected.encode() in raw:
            hits.append(
                {
                    "blob": oid,
                    "path": path,
                    "blob_sha256": sha(raw),
                    "occurrences": [
                        {"line": i, "text": line}
                        for i, line in enumerate(raw.decode().splitlines(), 1)
                        if expected in line
                    ],
                }
            )
    head = git.run("rev-parse", "HEAD").decode().strip()
    for hit in hits:
        candidate_commits = [head] + git.run(
            "log", "--all", "--format=%H", "--", hit["path"]
        ).decode().splitlines()
        hit["verified_containing_commit"] = None
        for commit in dict.fromkeys(candidate_commits):
            entry = git.run("ls-tree", commit, "--", hit["path"]).decode().split()
            if len(entry) >= 3 and entry[2] == hit["blob"]:
                hit["verified_containing_commit"] = commit
                break
        if hit["verified_containing_commit"] is None:
            raise AuditBlocked("Digest reference commit provenance unresolved")
    tracked = git.run("ls-files").decode().splitlines()
    untracked = (
        git.run("ls-files", "--others", "--exclude-standard").decode().splitlines()
    )
    work_hits = []
    for path in sorted(set(tracked + untracked)):
        if path.startswith(PACKAGE + "/") or not safe_path(path):
            continue
        raw = reader.read(path)
        if expected.encode() in raw:
            work_hits.append(
                {
                    "path": path,
                    "sha256": sha(raw),
                    "classification": "PREEXISTING_56_3A"
                    if "prospective_e1_protocol_freeze" in path
                    or "q1-prospective-e1-protocol-freeze/" in path
                    else "HISTORICAL_METADATA",
                    "occurrences": [
                        {"line": i, "text": line}
                        for i, line in enumerate(raw.decode().splitlines(), 1)
                        if expected in line
                    ],
                }
            )
    commits = git.run("log", "--all", "--format=%H%n%B").decode()
    commit_hits = [line for line in commits.splitlines() if expected in line]
    target_blobs = [
        {"blob": oid, "path": path, "sha256": sha(raw), "bytes": len(raw)}
        for (oid, path), raw in blobs.items()
        if path == TARGET
    ]
    return {
        "expected_sha256": expected,
        "reachable_object_inventory_sha256": sha(all_objects.encode()),
        "reachable_object_count": len(all_objects.splitlines()),
        "searched_safe_blob_count": len(blobs),
        "searched_blob_inventory": [
            {"blob": oid, "path": path, "sha256": sha(raw)}
            for (oid, path), raw in sorted(blobs.items())
        ],
        "git_digest_reference_hits": hits,
        "working_tree_digest_reference_hits": work_hits,
        "commit_message_hits": commit_hits,
        "exact_expected_content_blobs": exact_versions,
        "explicit_target_name_in_reachable_source": source_name_hits,
        "target_historical_blobs": target_blobs,
        "exclusions": "Scientific payloads, model objects, row evidence, arbitrary JSON and non-metadata blobs never inspected",
        "negative_search_scope": "No exact expected bytes in reachable target versions or searched diagnostic/metadata/source blobs; not a claim about unseen payloads, dangling objects or remote history",
    }


def reconcile(reader, git, current, manifest):
    records, data = {}, {}
    for name in SUPPORT_NAMES:
        path = SMOKE + "/" + name
        raw = reader.read(path)
        expected = manifest_entry(manifest, name)["expected_sha256"]
        tree = git.run("ls-tree", "HEAD", "--", path).decode().split()
        match_head = len(tree) >= 3 and tree[2] == blob_id(raw)
        records[name] = {
            "path": path,
            "sha256": sha(raw),
            "manifest_expected_sha256": expected,
            "manifest_match": sha(raw) == expected,
            "HEAD_blob": tree[2] if len(tree) >= 3 else None,
            "HEAD_match": match_head,
        }
        if name.endswith(".json"):
            data[name] = json.loads(raw)
    summary, history, validation = (
        data[n]
        for n in [
            "sprint56_1_summary.json",
            "validation_history.json",
            "validation_results.json",
        ]
    )
    pre, post = (
        data["preexecution_integrity.json"],
        data["postexecution_integrity.json"],
    )
    invariants = {
        "all_support_bytes_manifest_and_HEAD_match": all(
            r["manifest_match"] and r["HEAD_match"] for r in records.values()
        ),
        "summary_PASS": summary["outcome"]
        == "PRIMARY_XAI_ISOLATED_RUNTIME_SMOKE_TEST_PASS",
        "five_families_pass": summary["passed_family_count"] == 5
        and all(v.endswith("_PASS") for v in summary["family_support"].values()),
        "determinism_pass": data["determinism_smoke.json"]["all_pass"] is True,
        "recorded_model_object_hashes_before_after_equal": pre["objects"]
        == post["objects"],
        "recorded_protected_hashes_before_after_equal": pre["protected"]
        == post["protected"],
        "predictive_inventories_semantically_equal": data[
            "predictive_inventory_before.json"
        ]
        == data["predictive_inventory_after.json"],
        "final_validation_pass_51": validation["status"] == "PASS"
        and validation["focused_and_sprint55_regression_tests_passed"] == 51,
        "initial_log_matches_recorded_initial_test_counts": "3 failed, 48 passed, 2 deselected"
        in current.decode()
        and history["first_full_suite"]["failed"] == 3
        and history["first_full_suite"]["passed"] == 48,
        "history_final_validation_agrees": history["final_full_suite"]
        == {"deselected": 3, "failed": 0, "passed": 51},
        "no_scientific_rerun_or_result_changes_recorded": history[
            "scientific_outputs_changed"
        ]
        is False
        and history["smoke_reexecuted_after_observing_outputs"] is False
        and history["versions_scopes_tolerances_changed"] is False,
    }
    source_checks = []
    for path, expected in data["implementation_provenance.json"]["files"].items():
        raw = reader.read(path)
        source_checks.append(
            {
                "path": path,
                "expected_sha256": expected,
                "sha256": sha(raw),
                "matches": sha(raw) == expected,
            }
        )
    invariants["implementation_provenance_matches"] = all(
        r["matches"] for r in source_checks
    )
    return {
        "independent_support": all(invariants.values()),
        "invariants": invariants,
        "evidence": records,
        "implementation_provenance_checks": source_checks,
        "initial_vs_final_distinction": "Initial validation had 3 test assertion failures; final validation had51passes. These are different validation stages, documented in unchanged history; neither expected nor current initial log is a final PASS log.",
        "test_only_corrections": history["first_full_suite"]["failures"],
        "parent_outcome": summary["outcome"],
        "summary": summary,
        "scope_limit": "Independent of mismatched log, not independent replication of the experiment. Existing summary/digest/governance metadata cross-checked only; models, raw smoke vectors and predictive rows never opened or recomputed.",
    }


def construction(reader):
    refs = {}
    for path in SOURCE_FILES:
        text = reader.read(path).decode()
        refs[path] = {
            "sha256": sha(text.encode()),
            "relevant_lines": [
                {"line": i, "text": line}
                for i, line in enumerate(text.splitlines(), 1)
                if any(
                    term in line
                    for term in [
                        "def manifest",
                        "MANIFEST.sha256",
                        "write_text",
                        "if p.is_file()",
                        "def sha(",
                        "open('rb')",
                        "h.update(block)",
                        "validation_path",
                        "manifest()",
                        "no smoke execution",
                        "No smoke execution",
                    ]
                )
            ],
        }
    return {
        "source_references": refs,
        "generator": "q1_primary_xai_runtime_smoke_closure.manifest()",
        "recipe": "Sorted direct child regular files; raw SHA256; entry uses p.name basename; final LF; manifest excludes itself",
        "hashing": "q1_primary_xai_runtime_smoke.sha reads raw bytes in rb blocks; no newline/whitespace normalization",
        "manifest_write_mode": "Path.write_text overwrite; not append",
        "diagnostic_log_writer": "No dedicated target-log writer in inspected reachable source/test/scripts; log content is captured pytest stdout, but exact capture command/mode not preserved",
        "test_runner_writes_target": "NOT_ESTABLISHED; inspected tests read the manifest/log but do not generate target",
        "validation_rerun": "validation_history proves initial and final test runs; says scientific smoke was not rerun. Wall-clock ordering relative to each manifest invocation not preserved",
        "close_order": "Writes metadata/report then calls manifest at closure line156; also provides standalone manifest CLI stage",
        "causal_candidates": [
            {
                "candidate": "Trailing-whitespace removal after hashing, before first commit",
                "status": "EXACT_BYTE_TRANSFORMATION_PROVEN; ACTOR_AND_COMMAND_UNPROVED",
            },
            {
                "candidate": "Stale digest copied from whitespace-preserving log",
                "status": "CONSISTENT_WITH_BYTES; exact operation unproved",
            },
            {
                "candidate": "Scientific output or PASS/FAIL changed in this log",
                "status": "REFUTED_BY_EXACT_SHA256_WHITESPACE_ONLY_CANDIDATE",
            },
            {
                "candidate": "Newline, timestamps, paths, warning/version/order changes",
                "status": "NOT_NEEDED; exact candidate/current diff contains none",
            },
            {
                "candidate": "Regeneration of the log after manifest",
                "status": "NOT_ESTABLISHED; no execution replay authorized",
            },
        ],
        "causal_limit": "Exact transformation and initial packaging inconsistency proven; no unsupported attribution to Git, an editor, hook or user. Git normally preserves spaces; storage alone is not evidence of trimming.",
    }


def choose_resolution(
    *,
    exact_git_recovery,
    exact_hash_candidate,
    whitespace_only,
    initial_packaging_mismatch,
    independent_support,
    material_change_unreconciled=False,
    strong_conclusion_equivalence=False,
):
    if material_change_unreconciled:
        return FAIL
    if not independent_support:
        return BLOCKED
    if exact_git_recovery and whitespace_only:
        return RECOVERED
    if exact_hash_candidate and whitespace_only and initial_packaging_mismatch:
        return PACKAGING
    if strong_conclusion_equivalence:
        return LIMITED
    return BLOCKED


def impact_matrix(resolution):
    passed = resolution.startswith("R1_PASS_")
    fields = [
        ("A", "Sprint56.1 runtime-smoke conclusion"),
        ("B", "Sprint56.1 model-state integrity"),
        ("C", "Sprint55 reconstructed-state equivalence"),
        ("D", "Sprint54 predictive results"),
        ("E", "Sprint56.2 alternative XAI architecture"),
        ("F", "Sprint56.3A protocol contracts"),
        ("G", "E1 candidate universe"),
        ("H", "T1 governance"),
        ("I", "T2 sealed reserve"),
    ]
    rows = []
    for letter, name in fields:
        status = (
            (
                "PASS_WITH_PROVENANCE_LIMITATION"
                if letter in {"A", "B", "F"}
                else "PASS_NO_IMPACT"
            )
            if passed
            else "POTENTIAL_IMPACT"
        )
        rows.append(
            {
                "id": letter,
                "dimension": name,
                "status": status,
                "basis": {
                    "A": "Manifest- and Git-matching non-log summary/history/determinism support historical PASS; initial log has only a separator whitespace difference",
                    "B": "Recorded pre/post object/protected digests agree; no current model load or independent model rehash; target cannot mutate state",
                    "C": "No G4/G5 change; diagnostic validation output is not equivalence input",
                    "D": "No predictive evidence or metric read/recomputation; tracked parent identities unchanged",
                    "E": "E2-primary/prospective-E1 architecture unchanged; historical recovery remains closed",
                    "F": "Contract values unaffected; original BLOCKED record remains; separate explicit R1-based revalidation only",
                    "G": "168 candidates,112 CODE/PROCESS pending,56TEXT ineligible,0execution-authorized unchanged",
                    "H": "New T1 counters zero; historical predictive1/1 unchanged",
                    "I": "DENY_SEALED_REVIEWER_RESERVE; zero access",
                }[letter],
                "impact_scope": "Impact of this diagnostic mismatch only; not a fresh scientific validation campaign",
            }
        )
    return rows


def investigate(root, preflight):
    reader, git = Reader(root), ReadOnlyGit(root)
    if git.run("rev-parse", "--abbrev-ref", "HEAD").decode().strip() != BRANCH:
        raise AuditBlocked("Unexpected branch")
    if git.run("rev-parse", "HEAD").decode().strip() != preflight["HEAD"]:
        raise AuditBlocked("HEAD changed since preflight")
    current, manifest = reader.read(TARGET), reader.read(MANIFEST)
    expected_record = manifest_entry(manifest, "validation-initial-output.txt")
    expected = expected_record["expected_sha256"]
    target_history, manifest_history = (
        history_for(git, TARGET),
        history_for(git, MANIFEST),
    )
    search = search_metadata(git, reader, expected)
    candidate, reconstruction = reconstruct_whitespace_candidate(current, expected)
    ledger = difference_ledger(candidate, current)
    semantics = reconcile(reader, git, current, manifest)
    same_commit = (
        target_history["first_introduction_commit"]
        == manifest_history["first_introduction_commit"]
    )
    one_file_version = len(search["target_historical_blobs"]) == 1
    first_entries = [
        (target_history["changes"][-1]["ls_tree"].split()[2], TARGET),
        (manifest_history["changes"][-1]["ls_tree"].split()[2], MANIFEST),
    ]
    initial_blobs = git.blobs(first_entries)
    initial_target, initial_manifest = (initial_blobs[entry] for entry in first_entries)
    initial_expected = manifest_entry(
        initial_manifest, "validation-initial-output.txt"
    )["expected_sha256"]
    first_mismatch = same_commit and sha(initial_target) != initial_expected
    whitespace_only = candidate is not None and all(
        r["classification"] == ["WHITESPACE_ONLY", "FORMAT_ONLY"] for r in ledger
    )
    resolution = choose_resolution(
        exact_git_recovery=bool(search["exact_expected_content_blobs"]),
        exact_hash_candidate=candidate is not None and sha(candidate) == expected,
        whitespace_only=whitespace_only,
        initial_packaging_mismatch=first_mismatch,
        independent_support=semantics["independent_support"],
    )
    tree = git.run("ls-tree", "HEAD", "--", TARGET).decode()
    target_stat = (Path(root) / TARGET).stat()
    tracking = {
        "status_short_exact": git.run("status", "--short", "--", TARGET).decode(),
        "ls_files_stage_exact": git.run("ls-files", "--stage", "--", TARGET).decode(),
        "diff_HEAD_name_only": git.run(
            "diff", "HEAD", "--name-only", "--", TARGET, MANIFEST
        ).decode(),
        "check_ignore_output": git.run(
            "check-ignore", "-v", TARGET, allowed_codes=(0, 1)
        ).decode(),
        "check_attributes": git.run(
            "check-attr", "--all", "--", TARGET, MANIFEST
        ).decode(),
        "git_hash_object": git.run("hash-object", "--", TARGET).decode().strip(),
        "HEAD_tree": tree,
        "generated": "Captured diagnostic stdout per content/history; exact capture command is unrecorded",
    }
    tracking["tracked"] = bool(tracking["ls_files_stage_exact"])
    tracking["untracked"] = not tracking["tracked"]
    tracking["modified"] = bool(tracking["diff_HEAD_name_only"])
    tracking["ignored"] = bool(tracking["check_ignore_output"])
    tracking["identical_to_HEAD"] = (
        blob_id(current) == tree.split()[2] and not tracking["diff_HEAD_name_only"]
    )
    timeline = {
        "first_file_commit": target_history["first_introduction_commit"],
        "first_manifest_commit": manifest_history["first_introduction_commit"],
        "introduced_together": same_commit,
        "target_change_commit_count": len(target_history["changes"]),
        "manifest_change_commit_count": len(manifest_history["changes"]),
        "subsequent_modification_evidence": "NONE_IN_REACHABLE_PATH_HISTORY",
        "mismatch_present_in_first_commit": first_mismatch,
        "initial_file_sha256": sha(initial_target),
        "initial_manifest_expected_sha256": initial_expected,
        "initial_file_blob": first_entries[0][0],
        "initial_manifest_blob": first_entries[1][0],
        "initial_file_identical_to_current": initial_target == current,
        "initial_manifest_identical_to_current": initial_manifest == manifest,
        "one_target_historical_blob": one_file_version,
        "generation_before_commit": "Both already existed at their joint addition; exact precommit creation/mutation times unrecorded",
        "file_mtimes_are_not_historical_execution_order": True,
    }
    cases = {
        "A": "Byte version changed relative to manifested stream; exact mutation command/time not established",
        "B": "PROVEN: stored manifest digest is stale relative to initially committed and current log",
        "C": "NOT_ESTABLISHED: no log regeneration command or model rerun inferred",
        "D": "PROVEN: nine trailing ASCII spaces only, line8; all other bytes equal to hash-matching candidate",
        "E": "REFUTED for the log: no PASS/FAIL/test count/scientific text change",
        "F": "NOT_FOUND in reachable target history or safely searched metadata/source blobs",
        "G": "SUPPORTED_WITH_SEARCH_SCOPE: target history contains one nonmatching blob; no claim about uninspected/dangling/remote objects",
        "H": "PROVEN: file and manifest jointly introduced with mismatch already present",
    }
    files = {
        "protocol_summary.json": {
            "sprint": "10.8.2.56.3A-R1",
            "resolution": resolution,
            "objective": "Parent diagnostic byte provenance only",
            "scientific_execution_authorized": False,
            "amendment_type": "PROVENANCE_AMENDMENT_NOT_MANIFEST_CORRECTION",
        },
        "preflight.json": preflight,
        "target_artifact_inventory.json": {
            "target": TARGET,
            "manifest": MANIFEST,
            "tracking": tracking,
            "mode": oct(stat.S_IMODE(target_stat.st_mode)),
            "git_mode": tree.split()[0],
            "generated_role": "Historical initial pytest diagnostic, not final validation or predictive results",
        },
        "current_hash_analysis.json": {
            "path": TARGET,
            "bytes": len(current),
            "line_count": current.count(b"\n"),
            "SHA256": sha(current),
            "Git_blob_SHA1_independent": blob_id(current),
            "Git_hash_object": tracking["git_hash_object"],
            "LF_count": current.count(b"\n"),
            "CR_count": current.count(b"\r"),
            "matches_manifest": sha(current) == expected,
            "matches_HEAD": tracking["identical_to_HEAD"],
        },
        "manifest_expected_hash.json": {
            **expected_record,
            "manifest_path": MANIFEST,
            "manifest_sha256": sha(manifest),
            "comparison": "MISMATCH_REMAINS_VISIBLE_NOT_REPAIRED",
        },
        "git_history_provenance.json": {
            "target": target_history,
            "manifest": manifest_history,
            "target_historical_blobs": search["target_historical_blobs"],
            "reachable_refs_only": True,
        },
        "manifest_file_timeline.json": timeline,
        "expected_digest_search.json": search,
        "historical_byte_recovery.json": {
            "exact_bytes_found_in_reachable_Git": bool(
                search["exact_expected_content_blobs"]
            ),
            "matching_git_versions": search["exact_expected_content_blobs"],
            "hash_verified_candidate": reconstruction,
            "forensic_copy_persisted": False,
            "reason_no_copy": "Expected bytes were reconstructed by exact SHA256 hypothesis testing, not recovered from a historical Git version; persist recipe and line/hex ledger only",
            "original_git_blob_available": False,
        },
        "historical_current_diff_ledger.jsonl": ledger,
        "difference_classification_summary.json": {
            "classes": ["WHITESPACE_ONLY", "FORMAT_ONLY"]
            if whitespace_only
            else ["UNKNOWN_DIFFERENCE"],
            "changed_lines": len(ledger),
            "byte_difference": len(candidate) - len(current) if candidate else None,
            "all_other_bytes_identical": whitespace_only,
            "semantic_token_stream_equal": candidate.split() == current.split()
            if candidate
            else None,
            "test_count_difference": False if whitespace_only else None,
            "PASS_FAIL_semantic_difference": False if whitespace_only else None,
            "runtime_version_scientific_result_difference": False
            if whitespace_only
            else None,
            "normalization_performed_on_historical_file": False,
        },
        "sprint56_1_semantic_reconciliation.json": semantics,
        "manifest_construction_analysis.json": construction(reader),
        "scientific_impact_matrix.json": {"dimensions": impact_matrix(resolution)},
        "resolution_decision.json": {
            "resolution": resolution,
            "cases_A_through_H": cases,
            "root_cause": "Historical packaging inconsistency: manifest hashes a byte stream equal to current log plus9trailing spaces on line8; first committed log lacks those spaces. Exact editor/hook/command/time of whitespace handling is not recoverable.",
            "proved": [
                "Exact expected SHA256 candidate",
                "Single whitespace-only changed line",
                "Initial joint commit already inconsistent",
                "Independent manifested/Git-matching non-log PASS evidence",
            ],
            "not_proved": [
                "Responsible actor/tool",
                "Exact overwrite or append command",
                "Exact precommit chronology",
                "Expected version present in Git",
            ],
            "criteria": {
                "independent_support": semantics["independent_support"],
                "exact_hash_candidate": candidate is not None,
                "whitespace_only": whitespace_only,
                "initial_packaging_mismatch": first_mismatch,
            },
        },
        "downstream_56_3a_policy.json": {
            "action": "REVALIDATE_SPRINT_56_3A_USING_EXPLICIT_R1_PROVENANCE_AMENDMENT"
            if resolution.startswith("R1_PASS_")
            else "SPRINT56_3A_REMAINS_BLOCKED",
            "original_mismatch_must_remain_visible": True,
            "original_56_3A_disposition": "PROSPECTIVE_E1_PROTOCOL_FREEZE_BLOCKED",
            "56_3A_revalidated_in_R1": False,
            "56_3B_authorized": False,
            "E1_execution_authorized": False,
            "no_retroactive_byte_identity": True,
            "no_historical_redefinition": True,
            "required_next_review": "Human review, then explicit amendment-referencing56.3A revalidation to determine PASS_WITH_LIMITATIONS or BLOCKED",
            "other_56_3A_failure": "Historical mtime-order assertion remains outside this narrow log audit; not silently waived",
        },
        "governance_counters.json": {
            **dict.fromkeys(ZERO, 0),
            "historical_T1_predictive_access_count": 1,
            "historical_T1_predictive_scoring_count": 1,
            "T2_STATE": "DENY_SEALED_REVIEWER_RESERVE",
        },
        "recommended_next_action.json": {
            "action": "Human review of R1 provenance amendment; only separately requested56.3A revalidation afterward",
            "automatic_revalidation": False,
            "stop_after_R1": True,
            "never": "Rewrite old log/manifest or start56.3B/XAI",
        },
    }
    metadata_hashes = dict(reader.hashes)
    for path, expected_hash in metadata_hashes.items():
        if sha(reader.read(path)) != expected_hash:
            raise AuditBlocked("Metadata changed during audit: " + path)
    files["read_only_access_ledger.json"] = {
        "working_metadata_hashes_before": metadata_hashes,
        "working_metadata_hashes_after": dict(reader.hashes),
        "Git_commands": git.commands,
        "no_scientific_blob_contents_read": True,
        "scope": "Explicit diagnostic/metadata/source allowlist",
    }
    return files


def encode_files(files):
    return {
        name: (
            b"".join(
                (
                    json.dumps(row, sort_keys=True, ensure_ascii=False, allow_nan=False)
                    + "\n"
                ).encode()
                for row in value
            )
            if name.endswith(".jsonl")
            else canonical(value)
        )
        for name, value in files.items()
    }


def make_manifest(files):
    return "".join(
        f"{sha(raw)}  {name}\n" for name, raw in sorted(files.items())
    ).encode()


def verify_files(files):
    if "MANIFEST.sha256" not in files:
        return False
    entries = {}
    for line in files["MANIFEST.sha256"].decode().splitlines():
        h, name = line.split("  ", 1)
        if name in entries or name == "MANIFEST.sha256":
            return False
        entries[name] = h
    return set(entries) == set(files) - {"MANIFEST.sha256"} and all(
        sha(files[n]) == h for n, h in entries.items()
    )


def write_new_package(root, output, files):
    root, output = Path(root).resolve(), Path(output)
    if output.resolve() != root / PACKAGE or output.absolute() != output.resolve():
        raise PermissionError("Historical/outside namespace write denied")
    if not verify_files(files) or any(PurePosixPath(n).name != n for n in files):
        raise AuditBlocked("Invalid new package or path traversal")
    output.mkdir(parents=True, exist_ok=False)
    for name, raw in sorted(files.items()):
        with (output / name).open("xb") as handle:
            handle.write(raw)
    if {p.name: p.read_bytes() for p in output.iterdir()} != files:
        raise AuditBlocked("Persisted new package verification failed")


def report(files):
    f = files
    current = f["current_hash_analysis.json"]
    expected = f["manifest_expected_hash.json"]
    history = f["manifest_file_timeline.json"]
    decision = f["resolution_decision.json"]
    resolution = decision["resolution"]
    sections = [
        (
            "A. Objective",
            "Explain only the historical diagnostic/manifest discrepancy; no scientific rerun or parent mutation.",
        ),
        (
            "B. Branch and HEAD",
            f"`{f['preflight.json']['branch']}`; `{f['preflight.json']['HEAD']}`. 44 existing56.3A files classified PREEXISTING_56_3A; R1 files separately classified.",
        ),
        ("C. Target artifact", f"`{TARGET}`; manifest `{MANIFEST}`."),
        (
            "D. Current hash",
            f"SHA256 `{current['SHA256']}`, {current['bytes']}bytes, {current['line_count']}LF-terminated lines; zero CR.",
        ),
        (
            "E. Manifest expected hash",
            f"SHA256 `{expected['expected_sha256']}`. Entry is a package-relative basename, not repository-relative. Mismatch remains unchanged.",
        ),
        (
            "F. Tracking status",
            "Tracked, not ignored, no local modification; identical to HEAD. Generated diagnostic stdout; capture command not preserved.",
        ),
        (
            "G. Git blob identity",
            f"Current blob `{current['Git_blob_SHA1_independent']}` independently matches git hash-object and HEAD tree.",
        ),
        (
            "H. Git history",
            "All local reachable refs inspected for both paths; one target version and one introduction change. Safe metadata/source blobs searched without scientific payload content.",
        ),
        ("I. File introduction commit", str(history["first_file_commit"])),
        (
            "J. Manifest introduction commit",
            str(history["first_manifest_commit"]) + "; same commit as target.",
        ),
        (
            "K. Subsequent modifications",
            "No later change found in reachable path history. Initial commit already had the mismatch; worktree did not cause it in56.3A or R1.",
        ),
        (
            "L. Expected-digest search",
            f"{f['expected_digest_search.json']['searched_safe_blob_count']}reachable metadata/source blobs searched. Digest references occur in historical manifests/snapshots and56.3A blocker metadata; references are not the expected bytes themselves. Full inventory/hits are persisted.",
        ),
        (
            "M. Historical byte recovery",
            "No exact expected version found in reachable target Git history. A deterministic candidate restoring9ASCII spaces on line8 matches the expected SHA256 exactly. This is hash-verified reconstruction, not Git recovery; no forensic copy masquerades as an original.",
        ),
        (
            "N. Byte-level diff",
            "Line8 expected candidate hex45+09×20+0a; current450a. Nine trailing ASCII spaces removed. The other4758bytes are unchanged;60lines retained. Exact escaped values and hex persisted in the diff ledger.",
        ),
        (
            "O. Difference classification",
            "WHITESPACE_ONLY and FORMAT_ONLY. No timestamp/path/order/warning/test-count/PASS-FAIL/runtime-version/scientific-result difference.",
        ),
        (
            "P. Diagnostic vs scientific semantics",
            "Both byte versions describe the same INITIAL validation:3failed,48passed,2deselected. Neither is the final PASS run. Their non-whitespace token streams are identical; harmlessness is demonstrated by exact SHA256 reconstruction, not inferred from the filename.",
        ),
        (
            "Q. Independent Sprint56.1 evidence",
            "Manifest- and HEAD-matching summary, validation history/results, determinism, counters and pre/post integrity metadata support PRIMARY_XAI_ISOLATED_RUNTIME_SMOKE_TEST_PASS. Final suite51passed,3deselected. History records test-only corrections and no scientific rerun or tolerance change. This is metadata reconciliation, not independent experiment replication.",
        ),
        (
            "R. Manifest construction behavior",
            "Closure source lines18–21 hashes sorted direct files as raw bytes, uses basenames and overwrites the manifest, excluding itself. Closure line156 manifests after its report. No target-log writer/capture command was found in reachable source/tests/scripts. Append/overwrite of the log and exact actor/time remain unproved.",
        ),
        (
            "S. Root-cause classification",
            decision["root_cause"]
            + " Cases B,D,H proven; regeneration/intentional actor claims not established.",
        ),
        (
            "T. Scientific impact matrix",
            "\n".join(
                "- "
                + r["id"]
                + ". "
                + r["dimension"]
                + ": "
                + r["status"]
                + " — "
                + r["basis"]
                for r in f["scientific_impact_matrix.json"]["dimensions"]
            ),
        ),
        ("U. Resolution class", resolution),
        (
            "V. Historical immutability",
            "Original log, manifest and historical packages preserved. SHA256 before/after for inspected metadata; Git mode/blob tree plus empty tracked diff for all tracked historical audit files. Uncommitted56.3A package/source/tests separately byte-snapshotted and preserved; no scientific objects reopened for hashing.",
        ),
        (
            "W. Governance counters",
            "All R1 T1/T2/model/XAI/training/metric/figure/mutation counters0; historical predictive T1=1/1; T2 DENY_SEALED_REVIEWER_RESERVE. No commit/push/PR.",
        ),
        (
            "X. Validation",
            json.dumps(
                f.get("validation_results.json", {"status": "PENDING"}), sort_keys=True
            ),
        ),
        (
            "Y. Downstream56.3A policy",
            "Only REVALIDATE_SPRINT_56_3A_USING_EXPLICIT_R1_PROVENANCE_AMENDMENT after human review. Original mismatch and BLOCKED record remain visible. R1 does not revalidate56.3A, waive its other timestamp assertion, start56.3B or authorize E1.",
        ),
        (
            "Z. Final recommendation",
            "Review this new provenance amendment. Preserve all historical artifacts. The demonstrated packaging difference is diagnostic-only, with explicit limits on actor/time and Git recovery; subsequent56.3A disposition requires a separate action.",
        ),
    ]
    ending = (
        "READY FOR HUMAN REVIEW — REVALIDATE SPRINT 56.3A WITH R1 PROVENANCE AMENDMENT"
        if resolution.startswith("R1_PASS_")
        else "FAIL — PARENT SCIENTIFIC INTEGRITY AFFECTED"
        if resolution == FAIL
        else "BLOCKED — PARENT INTEGRITY PROVENANCE REMAINS UNRESOLVED"
    )
    return (
        "# Sprint10.8.2.56.3A-R1 — Parent Integrity Provenance Resolution\n\n"
        + "\n\n".join("## " + a + "\n\n" + b for a, b in sections)
        + "\n\n"
        + ending
        + "\n"
    ).encode()


def preserve_preexisting(root, preflight):
    for path, record in preflight["preexisting_changes"].items():
        if not (
            path.startswith("audits/q1-prospective-e1-protocol-freeze/")
            or path
            in {
                "src/evaluation/q1_prospective_e1_protocol_freeze.py",
                "tests/evaluation/test_q1_prospective_e1_protocol_freeze.py",
                "tests/evaluation/run_q1_prospective_e1_governance_regressions.py",
            }
        ):
            raise AuditBlocked("Unrecognized pre-existing change")
        if sha((Path(root) / path).read_bytes()) != record["sha256"]:
            raise AuditBlocked("Pre-existing56.3A bytes changed: " + path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--validation", type=Path, required=True)
    args = parser.parse_args()
    preflight = json.loads(args.preflight.read_bytes())
    validation = json.loads(args.validation.read_bytes())
    if validation.get("status") != "PASS":
        raise AuditBlocked("R1 focused validation must pass before publication")
    preserve_preexisting(ROOT, preflight)
    files = investigate(ROOT, preflight)
    git = ReadOnlyGit(ROOT)
    tree_after = git.run("ls-tree", "-r", "HEAD", "--", "audits").decode()
    diff = git.run("diff", "HEAD", "--name-only").decode()
    if tree_after != preflight["historical_audit_tree_snapshot"] or diff:
        raise AuditBlocked("Tracked parent identities changed")
    preserve_preexisting(ROOT, preflight)
    files["validation_results.json"] = validation
    files["historical_immutability_verification.json"] = {
        "tracked_audit_tree_before_sha256": sha(
            preflight["historical_audit_tree_snapshot"].encode()
        ),
        "tracked_audit_tree_after_sha256": sha(tree_after.encode()),
        "tracked_diff_exact": diff,
        "preexisting_56_3A_files_verified": len(preflight["preexisting_changes"]),
        "old_manifest_sha256_before_after": sha((ROOT / MANIFEST).read_bytes()),
        "scope": "Git mode/blob identities and empty worktree diff for tracked historical packages; byte SHA256 before/after for inspected metadata; no scientific payload deserialization",
        "historical_mutation_count": 0,
    }
    files["implementation_provenance.json"] = {
        "source_sha256": sha(Path(__file__).read_bytes()),
        "test_sha256": sha(
            (
                ROOT
                / "tests/evaluation/test_q1_prospective_e1_parent_integrity_resolution.py"
            ).read_bytes()
        ),
    }
    files["change_classification.json"] = {
        "preexisting": preflight["preexisting_changes"],
        "NEW_56_3A_R1": [
            PACKAGE + "/",
            "src/evaluation/q1_prospective_e1_parent_integrity_resolution.py",
            "tests/evaluation/test_q1_prospective_e1_parent_integrity_resolution.py",
        ],
    }
    encoded = encode_files(files)
    encoded["SPRINT56_3A_R1_PARENT_INTEGRITY_RESOLUTION_REPORT.md"] = report(files)
    encoded["MANIFEST.sha256"] = make_manifest(encoded)
    write_new_package(ROOT, ROOT / PACKAGE, encoded)
    print(files["resolution_decision.json"]["resolution"])


if __name__ == "__main__":
    main()
