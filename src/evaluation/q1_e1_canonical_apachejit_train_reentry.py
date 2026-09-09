# ruff: noqa: E501
"""One official inventory and one bounded canonical TRAIN reconciliation.

Only the preattested ActiveMQ CODE prefix and accepted R4 TRAIN messages are
materialized as prospective source snapshots. No final representation is built.
The wider canonical recovery route terminates here; no further forensic search.
"""

from __future__ import annotations

import argparse
import json
import math
import platform
import re
from pathlib import Path

from src.evaluation import q1_e1_remaining_train_source_transformation_resolution as r4a

r4 = r4a.r4
ROOT = r4.ROOT
OUT = "audits/q1-e1-canonical-apachejit-train-reentry/1.0.0"
SOURCE = "src/evaluation/q1_e1_canonical_apachejit_train_reentry.py"
TEST = "tests/evaluation/test_q1_e1_canonical_apachejit_train_reentry.py"
R4A_PIN = "8d4440980cac6101961b985668b791c86e262e5d9545a4343ad713396aeaa892"
DOI = "10.5281/zenodo.5907847"
ARCHIVE = "533e7c6fc4f7cb6f34b35539a972d00baa63a125e88ddb5743283dd277edcd5c"
CODE_SHA = "a51f5fcbcaff57446ec2263d2624cbdbc404af95cae9e2909a4bf81c67ece1b6"
VERDICT = "56_3B_R4B_CLOSE_CANONICAL_REENTRY_ROUTE_INSUFFICIENT_FOR_PRIMARY_E1"
CLOSED = "CLOSED_UNDER_AVAILABLE_CANONICAL_EVIDENCE"
ARTICLE = "ARTICLE_ROUTE_C_E2_PRIMARY_PLUS_BOUNDED_COMPLEMENTARY_E1"
sha, encode = r4.sha, r4.encode


class SearchBudget:
    def __init__(self):
        self.used = set()

    def enter(self, phase, tier):
        if (
            tier not in {1, 2, 3, 4}
            or phase not in {"primary_inventory", "targeted_fallback_reconciliation"}
            or phase in self.used
        ):
            raise PermissionError("Finite R4B search limit")
        if (
            phase == "targeted_fallback_reconciliation"
            and "primary_inventory" not in self.used
        ):
            raise PermissionError("Primary inventory first")
        self.used.add(phase)

    def close(self):
        if self.used != {"primary_inventory", "targeted_fallback_reconciliation"}:
            raise ValueError("Finite attempt incomplete")
        return "CANONICAL_SOURCE_RECOVERY_SEARCH_TERMINATES_AT_R4B"


def validate_official(source):
    if (
        source.get("doi") != DOI
        or source.get("version") != "v2"
        or source.get("archive_sha256_from_frozen_lineage") != ARCHIVE
    ):
        raise ValueError("Official source identity mismatch")
    if source.get("published_balanced_train_replaces_campaign") is not False:
        raise ValueError("Published TRAIN cannot redefine campaign TRAIN")
    if source.get("official_record") != "https://zenodo.org/records/5907847":
        raise ValueError("Wrong canonical source")


def validate_parent(parent):
    s = parent["protocol_summary.json"]
    if (
        s["verdict"] != r4a.VERDICT
        or s["project_modalities"] != 42
        or s["projects"] != 14
        or s["combined_eligible_with_limitation"] != 1
        or s["new_representations"] != 0
    ):
        raise ValueError("R4A material difference")
    c = parent["governance_counters.json"]
    if any(c[k] for k in r4.r3.b.ZERO):
        raise ValueError("Parent scientific execution difference")
    if (
        c["T2_STATE"] != "DENY_SEALED_REVIEWER_RESERVE"
        or c["historical_T1_predictive_access_count"] != 1
        or c["historical_T1_predictive_scoring_count"] != 1
    ):
        raise ValueError("Historical boundaries differ")


def load_parent():
    inherited, r3, r4parent, reads = r4a.load_parent()
    base = ROOT / r4a.OUT
    raw = (base / "MANIFEST.sha256").read_bytes()
    if sha(raw) != R4A_PIN:
        raise ValueError("R4A manifest differs")
    docs = {}
    names = set()
    for line in raw.decode().splitlines():
        h, n = line.split("  ", 1)
        if n in names or Path(n).name != n:
            raise ValueError("Invalid parent manifest")
        names.add(n)
        p = base / n
        if p.resolve() != p:
            raise PermissionError("Parent symlink")
        b = p.read_bytes()
        if sha(b) != h:
            raise ValueError("Parent byte integrity")
        if n.endswith(".json"):
            docs[n] = json.loads(b)
        elif n.endswith(".jsonl"):
            docs[n] = r4a.lines(b)
    if names != {p.name for p in base.iterdir() if p.name != "MANIFEST.sha256"}:
        raise ValueError("Parent file set differs")
    validate_parent(docs)
    return inherited, r3, r4parent, docs, reads


def resolve_commit(project, commit, candidates):
    if (
        not project
        or not isinstance(commit, str)
        or not re.fullmatch("[0-9a-f]{7,40}", commit)
    ):
        raise ValueError("Invalid project-qualified identity")
    matches = [sha for p, sha in candidates if p == project and sha.startswith(commit)]
    if len(set(matches)) != 1:
        raise ValueError("Ambiguous/not-found project-qualified commit")
    return matches[0]


def source_gate(project, partition, kind):
    if (
        partition != "TRAIN"
        or project != r4.PROJECT
        or kind not in {"CODE_CANONICAL_PREFIX", "R4_ACCEPTED_TEXT_SOURCE"}
    ):
        raise PermissionError("No admitted TRAIN source route")


def guard_fields(row, expected):
    if set(row) != set(expected) or {"buggy", "fix", "label", "target"} & set(row):
        raise ValueError("Labels/proxies or unexpected scientific fields")


def direct_reconstruction_gate(proof):
    required = [
        "canonical_identity_exact",
        "source_snapshot_admitted",
        "frozen_transform_executable",
        "fitting_authorized_or_not_required",
        "persistence_verified",
    ]
    if (
        not all(proof.get(k) is True for k in required)
        or proof.get("T1")
        or proof.get("T2")
        or proof.get("model_query")
        or proof.get("new_vectorizer_fit")
    ):
        raise PermissionError("Direct representation route closed")
    return "OPTIONAL_RECONSTRUCTION_GUARDS_PRESENT_NOT_XAI_AUTHORIZATION"


def freeze_decision(matrix):
    if len(matrix) != 42 or len({(x["project"], x["modality"]) for x in matrix}) != 42:
        raise ValueError("All42 scopes required")
    if len({x["project"] for x in matrix}) != 14:
        raise ValueError("All14 projects required")
    if any(x.get("performance_selection") for x in matrix):
        raise ValueError("Outcome-based fallback prohibited")
    if any(
        not x["representation_ready"] and x.get("closure") != CLOSED for x in matrix
    ):
        raise ValueError("Unresolved scope must close")
    return dict(
        verdict=VERDICT,
        fallback="E1_ILLUSTRATIVE_ONLY_NOT_PRIMARY",
        article_route=ARTICLE,
        q1="Q1_E1_CANONICAL_REENTRY_TOO_NARROW_FOR_PRIMARY_CLAIMS",
        search_terminated=True,
    )


def snapshot_payload(project, modality, rows, source_digest, origin, base):
    """Create source snapshot, never an executable model-input representation."""
    if project != r4.PROJECT or modality not in {"CODE", "TEXT"} or not rows:
        raise PermissionError("Snapshot scope not admitted")
    expected_fields = (
        r4.r3.b.SEMANTICS["CODE"] if modality == "CODE" else ["raw_commit_message"]
    )
    for row in rows:
        guard_fields(row.get("scientific_fields", {}), expected_fields)
        if not re.fullmatch("[0-9a-f]{40}", row.get("commit_identity", "")):
            raise ValueError("Full commit identity required for snapshot")
    ids = [x["commit_identity"] for x in rows]
    if len(ids) != len(set(ids)) or any(
        x["project"] != project or x["partition"] != "TRAIN" for x in rows
    ):
        raise ValueError("Snapshot identity/partition failure")
    if not re.fullmatch("[0-9a-f]{64}", source_digest):
        raise ValueError("Source digest required")
    runtime = dict(
        python=platform.python_version(),
        platform=platform.platform(),
        operations="JSON raw source serialization only; no transform/model execution",
    )
    schema = dict(
        state="PROSPECTIVE_CANONICAL_SOURCE_SNAPSHOT",
        modality=modality,
        scientific_fields=r4.r3.b.SEMANTICS["CODE"]
        if modality == "CODE"
        else ["raw_commit_message"],
        identity_fields=["project", "commit_identity", "row_identifier", "partition"],
        label_fields=[],
        serialization="Sorted compact ASCII JSON per line with final LF (inherited canonical encoder)",
    )
    contract = dict(
        partition="TRAIN",
        project=project,
        modality=modality,
        source_archive_digest=ARCHIVE,
        source_origin=origin,
        source_digest=source_digest,
        state="PROSPECTIVE_CANONICAL_SOURCE_SNAPSHOT",
        original_Sprint54_claim=False,
        no_fit=True,
    )
    row_order = [
        dict(
            row_index=i,
            project=project,
            commit_identity=x["commit_identity"],
            row_identifier=x["row_identifier"],
        )
        for i, x in enumerate(rows)
    ]
    payload = r4a.jsonl(rows)
    identity = dict(
        source_archive_digest=ARCHIVE,
        project=project,
        partition="TRAIN",
        row_count=len(rows),
        schema_digest=sha(encode(schema)),
        row_order_digest=sha(r4a.jsonl(row_order)),
        payload_digest=sha(payload),
        creation_contract_digest=sha(encode(contract)),
    )
    identity["snapshot_id"] = r4.digest(identity)
    folder = Path(base) / "source_snapshots" / "apache_activemq" / modality
    folder.mkdir(parents=True, exist_ok=False)
    objects = {
        "source.jsonl": payload,
        "schema.json": encode(schema),
        "row_order.jsonl": r4a.jsonl(row_order),
        "creation_contract.json": encode(contract),
        "runtime.json": encode(runtime),
        "snapshot_identity.json": encode(identity),
    }
    for n, b in objects.items():
        r4.atomic_file(folder, n, b)
    manifest = "".join(f"{sha(b)}  {n}\n" for n, b in sorted(objects.items()))
    r4.atomic_file(folder, "MANIFEST.sha256", manifest.encode())
    verify_snapshot(folder)
    return dict(
        **identity,
        modality=modality,
        state="PROSPECTIVE_CANONICAL_SOURCE_SNAPSHOT",
        path=str(folder.relative_to(base)),
        source_origin=origin,
        source_digest=source_digest,
        verified=True,
    )


def verify_snapshot(base):
    base = Path(base)
    manifest = base / "MANIFEST.sha256"
    if not manifest.is_file():
        raise ValueError("Snapshot must be persisted before use")
    entries = {
        n: h
        for h, n in (line.split("  ", 1) for line in manifest.read_text().splitlines())
    }
    required = {
        "source.jsonl",
        "schema.json",
        "row_order.jsonl",
        "creation_contract.json",
        "runtime.json",
        "snapshot_identity.json",
    }
    if set(entries) != required:
        raise ValueError("Snapshot persistence incomplete")
    for n, h in entries.items():
        if (base / n).is_symlink() or sha((base / n).read_bytes()) != h:
            raise ValueError("Snapshot digest mismatch")
    d = json.loads((base / "snapshot_identity.json").read_text())
    schema = json.loads((base / "schema.json").read_text())
    if schema["state"] != "PROSPECTIVE_CANONICAL_SOURCE_SNAPSHOT":
        raise ValueError("Original label forbidden")
    for field, name in {
        "payload_digest": "source.jsonl",
        "schema_digest": "schema.json",
        "row_order_digest": "row_order.jsonl",
        "creation_contract_digest": "creation_contract.json",
    }.items():
        if d.get(field) != entries[name]:
            raise ValueError("Required digest differs")
    copy = {k: v for k, v in d.items() if k != "snapshot_id"}
    if r4.digest(copy) != d["snapshot_id"]:
        raise ValueError("Snapshot identity differs")
    rows = r4a.lines((base / "source.jsonl").read_bytes())
    if (
        len(rows) != d["row_count"]
        or len({r["commit_identity"] for r in rows}) != len(rows)
        or any(r["partition"] != "TRAIN" or r["project"] != d["project"] for r in rows)
    ):
        raise ValueError("Snapshot rows invalid")
    return True


def materialize_sources(r4parent, out):
    identities = r4parent["train_row_identity_registry.jsonl"]
    if len(identities) != 3675 or any(
        x["partition"] != "TRAIN" or x["project"] != r4.PROJECT for x in identities
    ):
        raise ValueError("Frozen TRAIN registry differs")
    candidates = [(x["project"], x["commit_identity"]) for x in identities]
    for x in identities:
        resolve_commit(x["project"], x["commit_identity"], candidates)
    source_gate(r4.PROJECT, "TRAIN", "CODE_CANONICAL_PREFIX")
    source = f"{r4.FREEZE}/code_dataset.jsonl.gz"
    path = ROOT / source
    if path.resolve() != path:
        raise PermissionError("Source symlink")
    raw, consumed = r4.bounded_prefix(path, 3675, 183512)
    if consumed != 183512 or sha(raw) != CODE_SHA:
        raise ValueError("Canonical CODE TRAIN prefix differs")
    code = r4a.lines(raw)
    names = r4.r3.b.SEMANTICS["CODE"]
    code_rows = []
    for identity, features in zip(identities, code, strict=True):
        guard_fields(features, ["row_identifier", *names])
        if features["row_identifier"] != identity["train_row_id"]:
            raise ValueError("CODE identity join differs")
        if any(
            type(features[n]) not in {int, float} or not math.isfinite(features[n])
            for n in names
        ):
            raise ValueError("Canonical CODE nonfinite value")
        code_rows.append(
            dict(
                project=r4.PROJECT,
                partition="TRAIN",
                commit_identity=identity["commit_identity"],
                row_identifier=identity["train_row_id"],
                scientific_fields={n: features[n] for n in names},
            )
        )
    first = snapshot_payload(
        r4.PROJECT,
        "CODE",
        code_rows,
        CODE_SHA,
        dict(
            path=source,
            tier=3,
            compressed_prefix_bytes=183512,
            whole_container_read=False,
            lineage="Frozen canonical copy producer copies benchmark fields by exact identity; prior archive SHA verified at dataset freeze",
        ),
        out,
    )
    source_gate(r4.PROJECT, "TRAIN", "R4_ACCEPTED_TEXT_SOURCE")
    source_path = ROOT / r4.OUT / "sources/text_train_prefix.jsonl"
    text_raw = source_path.read_bytes()
    expected = next(
        p["prefix_sha256"]
        for p in r4parent["source_admission_before_payload.json"]["proofs"]
        if "text_dataset" in p["path"]
    )
    if sha(text_raw) != expected:
        raise ValueError("Parent TEXT source changed")
    texts = r4a.lines(text_raw)
    text_rows = []
    for identity, message in zip(identities, texts, strict=True):
        if message["row_identifier"] != identity["train_row_id"]:
            raise ValueError("TEXT commit link differs")
        text_rows.append(
            dict(
                project=r4.PROJECT,
                partition="TRAIN",
                commit_identity=identity["commit_identity"],
                row_identifier=identity["train_row_id"],
                scientific_fields={"raw_commit_message": message["raw_commit_message"]},
                raw_message_sha256=message["raw_commit_message_sha256"],
            )
        )
    second = snapshot_payload(
        r4.PROJECT,
        "TEXT",
        text_rows,
        expected,
        dict(
            path=str(source_path.relative_to(ROOT)),
            tier=3,
            upstream="Frozen exact commit-message Git extraction, already verified in R4",
            new_Git_acquisition=False,
        ),
        out,
    )
    return [first, second], identities


def build(primary, inherited, r3, r4parent, parent, snapshots, identities):
    projects = parent["apachejit_project_registry.json"]["projects"]
    sem = r3["code_process_semantic_contract.json"]["registry"]["registry"]
    matrix = []
    identity_ledger = []
    commit_ledger = []
    repos = []
    code_registry = []
    process_registry = []
    text_audit = []
    text_plan = []
    alignment = []
    transform = []
    state_by_project = {
        x["project"]: x for x in parent["text_vectorizer_scope_audit.jsonl"]
    }
    parent_rep = r4parent["representations/apache_activemq/TEXT/digests.json"][
        "representation_id"
    ]
    for row in projects:
        p = row["project_id"]
        known = p == r4.PROJECT
        candidates = next(
            (rs for rs in primary["project_repository_mapping"].values() if p in rs), []
        )
        repos.append(
            dict(
                project_id=p,
                canonical_project_name=p,
                repository_identity_candidates=candidates,
                source_url_if_persisted=None,
                repository_evidence="Official replication gitminer.py proj_repo literal",
                TRAIN_expected_count=row["TRAIN_expected_count"],
                canonical_dataset_row_count=None,
                canonical_dataset_row_count_status="Not scanned across prohibited partitions",
                identity_reconciliation_count=3675 if known else 0,
            )
        )
        if not known:
            identity_ledger.append(
                dict(
                    project=p,
                    expected_train_rows=row["TRAIN_expected_count"],
                    status="CANONICAL_TRAIN_MATCH_NOT_FOUND",
                    granularity="PROJECT_SUMMARY_NOT_FABRICATED_ROW_IDENTITIES",
                    reason="No admitted complete campaign TRAIN commit registry and safe canonical row route",
                    closure=CLOSED,
                )
            )
            commit_ledger.append(
                dict(
                    project=p,
                    status="UNRESOLVED_NO_SAFE_TRAIN_IDENTITY_ACCESS",
                    full_SHA_count=0,
                    short_SHA_guessing=False,
                    closure=CLOSED,
                )
            )
        for m in ["CODE", "PROCESS", "TEXT"]:
            source_ready = known and m in {"CODE", "TEXT"}
            rep_ready = known and m == "TEXT"
            state_ready = m == "TEXT"
            blockers = (
                []
                if rep_ready
                else (
                    []
                    if source_ready
                    else ["No admitted exact campaign TRAIN identity/source route"]
                )
                + (
                    []
                    if state_ready
                    else [
                        "Frozen numeric values not independently executable without prohibited predictor load or unauthorized refit"
                    ]
                )
                + (
                    ["PROCESS ancestral aggregation proof incomplete"]
                    if m == "PROCESS"
                    else []
                )
            )
            matrix.append(
                dict(
                    project=p,
                    modality=m,
                    canonical_identity=known,
                    source_ready=source_ready,
                    transform_ready=state_ready,
                    representation_ready=rep_ready,
                    representation_id=parent_rep if rep_ready else None,
                    representation_origin="R4_PARENT_NOT_REGENERATED"
                    if rep_ready
                    else None,
                    blocker=blockers,
                    next_action="Bounded complementary/illustrative E1 protocol only"
                    if rep_ready
                    else "No further canonical forensic search; retain limitation",
                    closure="ACCEPTED_PARENT_BOUNDED_ROUTE" if rep_ready else CLOSED,
                    performance_selection=False,
                )
            )
            transform.append(
                dict(
                    project=p,
                    modality=m,
                    status="TRANSFORM_ROUTE_READY_WITH_LIMITATION"
                    if state_ready
                    else "TRANSFORM_ROUTE_NOT_READY",
                    new_fit=False,
                    representation_compatible_inputs_available=rep_ready,
                    reason="Existing project-specific frozen vectorizer; full source joins unavailable outside ActiveMQ"
                    if state_ready
                    else "Numeric state values absent outside prohibited predictive containers",
                )
            )
        code_registry.append(
            dict(
                project=p,
                status="CODE_CANONICAL_SOURCE_READY_WITH_LIMITATION"
                if known
                else "CODE_CANONICAL_SOURCE_INSUFFICIENT",
                snapshot_id=snapshots[0]["snapshot_id"] if known else None,
                final_representation_ready=False,
                limitation="Raw frozen benchmark CODE values admitted; model preprocessing unresolved"
                if known
                else CLOSED,
            )
        )
        process_registry.append(
            dict(
                project=p,
                status="PROCESS_CANONICAL_SOURCE_INSUFFICIENT",
                snapshot_id=None,
                reason="No independently validated ancestor-only aggregation and executable transform; other-project source routes also unavailable",
                closure=CLOSED,
            )
        )
        text_audit.append(
            dict(
                project=p,
                status="TEXT_MESSAGE_SOURCE_READY_WITH_LIMITATION"
                if known
                else "TEXT_MESSAGE_SOURCE_REQUIRES_PROJECT_GIT_RESOLUTION",
                dataset_message_column=False,
                parent_source_available=known,
                replication_intermediate_message_presence="NOT_PROVEN_WITHOUT_UNADMITTED_PAYLOAD_READ",
                snapshot_id=snapshots[1]["snapshot_id"] if known else None,
                closure="BOUNDED_PARENT_SOURCE_REUSED" if known else CLOSED,
            )
        )
        text_plan.append(
            dict(
                project=p,
                repository_candidates=candidates,
                commit_SHA_source=f"{r4.OUT}/train_row_identity_registry.jsonl"
                if known
                else "UNAVAILABLE_SAFE_COMPLETE_TRAIN_REGISTRY",
                message_extraction_method="Exact admitted commit object: git cat-file commit <full SHA>; split first empty line, preserve raw message bytes",
                encoding="UTF-8 decode with replacement as frozen producer; preserve original bytes and SHA256",
                normalization="Frozen project vectorizer only; no new text cleaning",
                digest_strategy="SHA256 raw commit-message bytes plus project/full-SHA binding",
                executed=False,
                reason="Existing parent source sufficient"
                if known
                else "Exact safe TRAIN identities missing; no Git history traversal or further acquisition",
                closure="NOT_NEEDED_PARENT_REUSED" if known else CLOSED,
            )
        )
        state = state_by_project[p]
        alignment.append(
            dict(
                project=p,
                status="VECTORIZER_READY_WITH_LIMITATION"
                if known
                else "VECTORIZER_ALIGNMENT_UNPROVEN",
                vectorizer_state_sha256=state["state_digest"],
                state_reference=state["state_path"],
                project_specific=True,
                new_fit=False,
                complete_message_link=known,
                limitation="Existing exact transform metadata does not establish missing canonical message population",
            )
        )
    for i, x in enumerate(identities):
        identity_ledger.append(
            dict(
                project=x["project"],
                partition="TRAIN",
                train_row_id=x["train_row_id"],
                commit_identity=x["commit_identity"],
                canonical_source_row_reference=f"Frozen canonical TRAIN CODE prefix line {i + 1}; accepted R4 TEXT source same row_identifier",
                status="CANONICAL_TRAIN_MATCH_WITH_LIMITATION",
                limitation="Exact frozen canonical-copy binding; upstream mixed CSV not rescanned",
                source_archive_digest=ARCHIVE,
            )
        )
        commit_ledger.append(
            dict(
                project=x["project"],
                full_commit_sha=x["commit_identity"],
                frozen_row_identifier=x["train_row_id"],
                status="EXACT_PROJECT_QUALIFIED_FULL_SHA",
                short_SHA_resolution_used=False,
            )
        )
    decision = freeze_decision(matrix)
    code_features = []
    process_features = []
    temporal = []
    for x in sem:
        iscode = x["modality"] == "CODE"
        entry = dict(
            apachejit_field=x["feature_name"],
            semantic_definition=x["definition"],
            definition_evidence=x["source_provenance"],
            MMSDP_XAI_modality=x["modality"],
            raw_change_process_semantics="Prediction commit/direct-parent change metric"
            if iscode
            else "Strictly prior developer/file-history metric",
            transform_requirement=x["transformation"],
            prediction_time_validity="Frozen direct change semantics, authoritative benchmark values"
            if iscode
            else "Not independently proven from admitted replication logic",
            eligible_source_subset=[r4.PROJECT] if iscode else [],
            reason="Exact frozen change columns; no modality reassignment"
            if iscode
            else "Benchmark presence and bug-inducing collection logic do not prove per-field ancestor-only aggregation",
        )
        (code_features if iscode else process_features).append(entry)
        if not iscode:
            temporal.append(
                dict(
                    field=x["feature_name"],
                    status="PROCESS_ANCESTRAL_UNPROVEN",
                    history_derived_semantics=x["definition"],
                    source_implementation_inspected="Official gitminer.py traces bug-inducing candidates and clean commits; collector.py searches issue-linked commits; neither supplies complete numeric aggregation proof",
                    notebook_limitation="Construction notebooks inventoried; uncertified embedded outputs not opened under T1/T2 exclusion",
                    future_information_risk="NOT_DISCHARGED; no observed violation claimed",
                    materialization_permitted=False,
                )
            )
    primary_contract = {k: v for k, v in primary.items() if k != "inventory"}
    coverage = dict(
        source_ready_CODE=1,
        source_ready_PROCESS=0,
        source_ready_TEXT=1,
        representation_eligible_CODE=0,
        representation_eligible_PROCESS=0,
        representation_eligible_TEXT=1,
        projects_with_3_representations=0,
        projects_with_2_representations=0,
        projects_with_1_representation=1,
        projects_with_no_representation=13,
        source_snapshot_projects=1,
        source_snapshot_modalities=2,
        combined_unique_train_identities=3675,
        expected_train_identities=56821,
        new_representations=0,
        parent_representations=1,
    )
    counters = dict.fromkeys(
        (
            *r4.r3.b.ZERO,
            "TRAIN_CANONICAL_SOURCE_READ_COUNT",
            "TRAIN_SOURCE_SNAPSHOT_PERSIST_COUNT",
            "TRAIN_REPRESENTATION_RECONSTRUCTION_COUNT",
            "T2_IDENTITY_READ_COUNT",
            "HYPERPARAMETER_TUNING_COUNT",
        ),
        0,
    )
    counters.update(
        TRAIN_CANONICAL_SOURCE_READ_COUNT=7350,
        TRAIN_SOURCE_SNAPSHOT_PERSIST_COUNT=2,
        T1_IDENTITY_ACCESS_COUNT=0,
        historical_T1_predictive_access_count=1,
        historical_T1_predictive_scoring_count=1,
        T2_STATE="DENY_SEALED_REVIEWER_RESERVE",
        count_units={
            "TRAIN_CANONICAL_SOURCE_READ_COUNT": "One CODE and one existing TEXT row visit per3675 TRAIN identities; integrity rehashes tracked separately",
            "TRAIN_SOURCE_SNAPSHOT_PERSIST_COUNT": "Two raw-source snapshots; not final representations",
        },
        CSV_HEADER_ONLY_READ_OPERATIONS=primary[
            "header_operations_including_initial_inspection"
        ],
        NEW_GIT_EXTRACTIONS=0,
        ARCHIVE_FULL_PAYLOAD_READS=0,
    )
    return {
        "protocol_summary.json": dict(
            verdict=VERDICT,
            **coverage,
            source_recovery_closed=True,
            article_route=ARTICLE,
            scientific_interpretation="Canonical raw-source progress for one project does not establish primary multi-project E1; accepted R4 TEXT remains bounded complementary/illustrative input evidence",
        ),
        "parent_r4a_verification.json": dict(
            verified=True,
            manifest_sha256=R4A_PIN,
            R4A_verdict=parent["protocol_summary.json"]["verdict"],
            R3_R4_verified=True,
            parent_ActiveMQ_TEXT_overwritten=False,
        ),
        "r4b_termination_contract.json": dict(
            CANONICAL_SOURCE_RECOVERY_SEARCH_TERMINATES_AT_R4B=True,
            primary_inventory_rounds=1,
            targeted_fallback_reconciliation_rounds=1,
            allowed_tiers=[1, 2, 3, 4],
            new_lower_tiers=False,
            remaining_unresolved_state=CLOSED,
            R4C_forensic_search_recommended=False,
        ),
        "apachejit_canonical_source_contract.json": primary_contract,
        "apachejit_v2_inventory.jsonl": primary["inventory"],
        "label_exclusion_contract.json": dict(
            structurally_acknowledged=["buggy", "fix"],
            used_for_identity_selection=False,
            used_for_source_construction=False,
            used_for_feature_selection=False,
            used_for_imputation=False,
            published_train_substitution=False,
            scientific_label_values_read=0,
        ),
        "canonical_train_reentry_identity_ledger.jsonl": identity_ledger,
        "apachejit_commit_identity_resolution.jsonl": commit_ledger,
        "apachejit_project_repository_registry.json": dict(
            projects=repos,
            multi_repository_projects="HDFS/MAPREDUCE candidates retained; no arbitrary repository assignment",
        ),
        "apachejit_code_feature_mapping.jsonl": code_features,
        "canonical_code_train_source_snapshot_registry.jsonl": code_registry,
        "apachejit_process_feature_mapping.jsonl": process_features,
        "apachejit_process_temporal_provenance.jsonl": temporal,
        "canonical_process_train_source_snapshot_registry.jsonl": process_registry,
        "apachejit_text_message_source_audit.jsonl": text_audit,
        "text_message_reentry_plan.jsonl": text_plan,
        "text_vectorizer_canonical_alignment.jsonl": alignment,
        "canonical_source_snapshot_registry.jsonl": snapshots,
        "canonical_transform_reentry_readiness.jsonl": transform,
        "r4b_final_scientific_reentry_matrix.jsonl": matrix,
        "fallback_e1_route_decision.json": dict(
            status=decision["fallback"],
            basis="One project, one executable TEXT representation; CODE source only, no numeric representation; no PROCESS temporal proof",
            performance_based=False,
            E2="Primary multimodal explanation",
            E1="Bounded complementary/illustrative only; no attribution executed here",
            full_E2_scope_explained_by_E1=False,
            direct_E1_input_support=[
                dict(project=r4.PROJECT, modality="TEXT", representation_id=parent_rep)
            ],
        ),
        "q1_e1_canonical_reentry_assessment.json": dict(
            verdict=decision["q1"],
            **coverage,
            reason="One-project TEXT input provenance and two raw-source snapshots do not provide multi-project or numeric feature-explanation evidence. Deterministic source persistence is verified; transform, temporal and broader population limitations remain.",
        ),
        "article_timeline_route_decision.json": dict(
            route=ARTICLE,
            bounded_plan="Preserve E2 as primary; restrict complementary/illustrative E1 to scientifically supported inputs and separately authorized execution. No more canonical source-recovery sprint.",
            T1_authorized=False,
            XAI_authorized=False,
            R4C_recommended=False,
        ),
        "apachejit_source_citation.json": dict(
            authors=["Keshavarz, Hossein", "Nagappan, Meiyappan"],
            title=primary["title"],
            version="v2",
            doi=DOI,
            official_record=primary["official_record"],
            venue_as_described_by_source="MSR 2022 Data Showcase Track; official dataset description says submitted",
            publication_date=primary["published"],
            unverified_proceedings_pages_or_article_DOI=None,
        ),
        "r4b_replication_readiness.json": dict(
            status="READY_WITH_LIMITATION_FOR_ACTIVEMQ_RAW_SOURCE_SNAPSHOTS_ONLY",
            source_version="ApacheJIT v2",
            source_archive_digest=ARCHIVE,
            builder=SOURCE,
            project_mapping="apachejit_project_repository_registry.json",
            identity_mapping="canonical_train_reentry_identity_ledger.jsonl",
            feature_mapping=[
                "apachejit_code_feature_mapping.jsonl",
                "apachejit_process_feature_mapping.jsonl",
            ],
            temporal_evidence="apachejit_process_temporal_provenance.jsonl",
            snapshot_manifests=[x["path"] + "/MANIFEST.sha256" for x in snapshots],
            runtime="Snapshot runtime.json files; standard library source serialization only",
            frozen_parent_dependencies=True,
            no_new_model_or_XAI_package=True,
        ),
        "remaining_blockers.json": dict(
            items=[
                "13 projects: no safely accessible complete frozen TRAIN identity/source route",
                "Numeric imputer/scaler state values unavailable outside predictive containers; no new fit authorized",
                "PROCESS ancestor-only aggregation not established from admitted official evidence",
                "TEXT messages not present in four canonical table schemas; broader exact TRAIN-to-Git identity path unavailable",
            ],
            status=CLOSED,
            no_more_canonical_recovery=True,
        ),
        "governance_counters.json": counters,
        "recommended_next_action.json": dict(
            action="Close canonical-source recovery. Adopt ARTICLE_ROUTE_C_E2_PRIMARY_PLUS_BOUNDED_COMPLEMENTARY_E1 and prepare only a bounded complementary/illustrative E1 execution protocol for supported input evidence; keep T1/XAI separately gated.",
            source_search_continuation=False,
            automatic_T1_or_XAI=False,
        ),
    }


def report(f, flight):
    sections = [
        (
            "Finite objective",
            "One official source inventory and one targeted canonical reconciliation; no lower tiers or further forensic search.",
        ),
        (
            "Branch and parents",
            flight["branch"]
            + " / "
            + flight["head"]
            + ". R3, R4 and R4A preserved; ActiveMQ TEXT not regenerated or overwritten.",
        ),
        (
            "Official source",
            "ApacheJIT v2, DOI "
            + DOI
            + ". Publisher metadata, local static replication code and exact table headers inspected. The frozen archive SHA-256 is inherited; no whole mixed archive/table read or download was performed. Notebook/intermediate payloads remain uninspected where T1/T2 exclusion cannot be certified.",
        ),
        (
            "Campaign membership",
            "56,821 expected TRAIN identities remain authoritative. Published balanced apachejit_train.csv is not substituted. Exact project/full-SHA identity is reconciled only for the3675 accepted ActiveMQ TRAIN identities.",
        ),
        (
            "Canonical snapshots",
            "Two PROSPECTIVE_CANONICAL_SOURCE_SNAPSHOT packages persisted: ActiveMQ CODE and TEXT,3675 rows each,3675 unique commits. CODE uses the exact preattested frozen canonical prefix. TEXT preserves already accepted raw messages from R4. No source label/proxy fields are used.",
        ),
        (
            "CODE and PROCESS",
            "CODE source is ready with limitation for ActiveMQ; final numeric preprocessing is unavailable. PROCESS remains insufficient for all14: official bug-inducing collection code does not establish complete per-feature ancestor-only metrics. No invented Git metrics or scaling.",
        ),
        (
            "TEXT and vectorizers",
            "ActiveMQ TEXT remains the only executable parent representation. Other13 message-to-TRAIN joins remain unresolved; existing project-specific vectorizers are retained without fitting. Git extraction recipes are recorded but not executed.",
        ),
        (
            "Storage and verification",
            "Each source snapshot persists payload, row order, schema, creation contract, runtime, identity and manifest before acceptance. No optional final representation reconstructed. Every new artifact is separated from historical evidence.",
        ),
        (
            "Scientific coverage",
            "Raw-source readiness CODE1, PROCESS0, TEXT1; final representation readiness CODE0, PROCESS0, TEXT1. One project has one eligible representation,13 have none. All42 decisions are explicit.",
        ),
        (
            "Publication decision",
            "Q1_E1_CANONICAL_REENTRY_TOO_NARROW_FOR_PRIMARY_CLAIMS. E1_ILLUSTRATIVE_ONLY_NOT_PRIMARY. Adopt "
            + ARTICLE
            + ". E1 cannot be presented as explaining all E2 scopes; no E1 attribution was run.",
        ),
        (
            "Termination",
            "CANONICAL_SOURCE_RECOVERY_SEARCH_TERMINATES_AT_R4B=true. All unresolved targets closed under available canonical evidence and current access constraints. Do not propose R4C solely to find more files.",
        ),
        (
            "Next action",
            "Close source recovery and move to a bounded complementary/illustrative E1 execution protocol using supported inputs, with E2 primary. T1 and XAI require separate authorization. No commit, push or PR.",
        ),
    ]
    return (
        "# Sprint 56.3B-R4B canonical ApacheJIT re-entry\n\n"
        + VERDICT
        + "\n\n"
        + "\n\n".join("## " + title + "\n\n" + text for title, text in sections)
        + "\n"
    )


def execute(flight, primary):
    r4.r3.branch_gate(r4.r3.b.git("rev-parse", "--abbrev-ref", "HEAD"))
    if flight["head"] != r4.r3.b.git("rev-parse", "HEAD"):
        raise ValueError("HEAD changed")
    before = r4.snapshot(flight)
    validate_official(primary)
    budget = SearchBudget()
    budget.enter("primary_inventory", 1)
    inherited, r3, r4parent, parent, reads = load_parent()
    out = ROOT / OUT
    if out.resolve() != out:
        raise PermissionError("Output symlink")
    out.mkdir(parents=True, exist_ok=False)
    r4.atomic_file(out, "preflight.json", encode(flight))
    r4.atomic_file(out, "parent_integrity_before.json", encode(before))
    budget.enter("targeted_fallback_reconciliation", 3)
    snapshots, identities = materialize_sources(r4parent, out)
    f = build(primary, inherited, r3, r4parent, parent, snapshots, identities)
    budget.close()
    f["parent_integrity_after.json"] = r4.snapshot(flight)
    f["parent_integrity_diff.json"] = dict(
        status="PASS", changed=[], R4_ActiveMQ_TEXT_unchanged=True
    )
    f["governance_counters.json"].update(
        T1_METADATA_ACCESS_COUNT=len(reads),
        T1_METADATA_COUNT_UNIT="Unique inherited safe governance metadata paths; no T1 feature or label values",
    )
    f["reviewer_canonical_reentry_explanation.md"] = (
        "# Reviewer canonical-source re-entry explanation\n\nHistorical complete feature matrices were unavailable as preserved executable artifacts, so canonical re-entry was bounded to official ApacheJIT v2 lineage and the already frozen campaign TRAIN population. Official metadata, table headers and safe replication source code were inspected; published balanced TRAIN was not substituted. No whole mixed archive/table read, T1 feature/label access or T2 access was permitted.\n\nThe one targeted reconciliation persisted ActiveMQ CODE raw change metrics from a preverified3675-row TRAIN prefix and ActiveMQ TEXT messages from the immutable R4 source. Full project/commit identities, row order, source/archive digests, schemas, runtime, creation contracts and manifests accompany both snapshots. They are PROSPECTIVE_CANONICAL_SOURCE_SNAPSHOT artifacts, not original Sprint54 inputs or final model matrices.\n\nNo new representation, predictor query, fitting, metrics or XAI was executed. Only the accepted ActiveMQ TEXT representation remains available for bounded complementary/illustrative E1. The other13 projects lack safe complete joins; numerical state and PROCESS temporal proof remain insufficient. Static-source inventory does not assert that uninspected notebook/data outputs lack useful information; they were not admitted under the preserved partition boundary. This limited canonical route is closed for primary E1 expansion. E2 remains primary, with no claim that E1 covers every fusion scope.\n"
    )
    f["SPRINT56_3B_R4B_CANONICAL_APACHEJIT_REENTRY_REPORT.md"] = report(f, flight)
    for n, value in f.items():
        r4.atomic_file(
            out,
            n,
            r4a.jsonl(value)
            if n.endswith(".jsonl")
            else value.encode()
            if isinstance(value, str)
            else encode(value),
        )
    print(json.dumps(f["protocol_summary.json"], sort_keys=True))


def finalize(validation):
    out = ROOT / OUT
    r4.r3.branch_gate(r4.r3.b.git("rev-parse", "--abbrev-ref", "HEAD"))
    r4.snapshot(json.loads((out / "preflight.json").read_text()))
    for p in (out / "source_snapshots/apache_activemq").iterdir():
        verify_snapshot(p)
    r4.atomic_file(out, "validation_results.json", validation.read_bytes())
    r4.atomic_file(
        out,
        "implementation_provenance.json",
        encode({p: sha((ROOT / p).read_bytes()) for p in [SOURCE, TEST]}),
    )
    manifest = "".join(
        f"{sha(p.read_bytes())}  {p.relative_to(out).as_posix()}\n"
        for p in sorted(out.rglob("*"))
        if p.is_file()
    )
    r4.atomic_file(out, "MANIFEST.sha256", manifest.encode())
    print("MANIFEST", sha((out / "MANIFEST.sha256").read_bytes()))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", type=Path)
    parser.add_argument("--primary", type=Path)
    parser.add_argument("--finalize", type=Path)
    args = parser.parse_args()
    if args.finalize:
        finalize(args.finalize)
    elif args.preflight and args.primary:
        execute(
            json.loads(args.preflight.read_text()), json.loads(args.primary.read_text())
        )
    else:
        parser.error("preflight/primary or finalize required")


if __name__ == "__main__":
    main()
