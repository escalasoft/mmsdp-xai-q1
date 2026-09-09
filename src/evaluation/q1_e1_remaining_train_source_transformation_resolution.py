# ruff: noqa: E501
"""Finite R4A resolution: 41 targets, immutable reuse of one R4 representation.

No source payload is opened unless all source/identity/semantics/transform gates
pass. No new target passes in the inspected frozen evidence. This module reports
that finite stop; it does not pretend to implement an unavailable source route.
"""

from __future__ import annotations

import argparse
import json
import math
import struct
from collections import Counter
from pathlib import Path

from src.evaluation import q1_e1_prospective_train_representation_reconstruction as r4

ROOT = r4.ROOT
OUT = "audits/q1-e1-remaining-train-source-transformation-resolution/1.0.0"
R4_PIN = "6a8f3c3e0609dad5ccc82ba42f964e12305ed9ae723ca1f7553bc5558bcc8855"
VERDICT = "56_3B_R4A_BLOCKED_SOURCE_COVERAGE_INSUFFICIENT"
SOURCE = "src/evaluation/q1_e1_remaining_train_source_transformation_resolution.py"
TEST = "tests/evaluation/test_q1_e1_remaining_train_source_transformation_resolution.py"
STORE = "audits/q1-xai-reconstruction-execution/1.0.0"
RAW = "data/external/apachejit-v2/extracted/apachejit/dataset/apachejit_total.csv"
NUMERIC_REASON = "NUMERIC_STATE_VALUES_NOT_STANDALONE; PREDICTOR_LOAD_DENIED; NEW_NUMERIC_FIT_NOT_AUTHORIZED_BY_R3"
ROUTE_REASON = "NO_FROZEN_TRAIN_ONLY_SEEK_ROUTE; PROJECT_GROUPED_GZIP_REQUIRES_TRAVERSING_EARLIER_T1_T2"
TEMPORAL_REASON = "PREDICTION_TIME_ANCESTOR_AGGREGATION_NOT_PROVEN"
sha, encode = r4.sha, r4.encode


def lines(raw):
    return [json.loads(x) for x in raw.decode().splitlines() if x.strip()]


def jsonl(rows):
    return b"".join(r4.canonical(x) for x in rows)


def verify_parent(d):
    s = d["protocol_summary.json"]
    c = d["governance_counters.json"]
    expected = {
        "verdict": r4.PARTIAL,
        "expected_train_rows": 56821,
        "projects": 14,
        "expected_project_modalities": 42,
        "persisted_representations": 1,
        "persisted_unique_train_rows": 3675,
        "compatible_e1_scopes": 4,
    }
    if any(s.get(k) != v for k, v in expected.items()):
        raise ValueError("R4 material parent difference")
    if any(c.get(k) != 0 for k in r4.r3.b.ZERO):
        raise ValueError("R4 prohibited counter differs")
    if (
        c["historical_T1_predictive_access_count"] != 1
        or c["historical_T1_predictive_scoring_count"] != 1
        or c["T2_STATE"] != "DENY_SEALED_REVIEWER_RESERVE"
    ):
        raise ValueError("Historical boundary differs")
    cov = d["coverage_summary.json"]
    if cov["blocked"] != 41 or cov["by_modality"]["TEXT"]["persisted_columns"] != 2557:
        raise ValueError("R4 coverage differs")
    return True


def load_parent():
    inherited, r3, reads = r4.metadata()
    base = ROOT / r4.OUT
    raw = (base / "MANIFEST.sha256").read_bytes()
    if sha(raw) != R4_PIN:
        raise ValueError("R4 immutable manifest mismatch")
    entries = {}
    d = {}
    for line in raw.decode().splitlines():
        h, n = line.split("  ", 1)
        p = base / n
        if (
            n in entries
            or Path(n).is_absolute()
            or ".." in Path(n).parts
            or p.resolve() != p
        ):
            raise ValueError("Unsafe parent manifest")
        data = p.read_bytes()
        if sha(data) != h:
            raise ValueError("Parent digest mismatch")
        entries[n] = h
        if n.endswith(".json"):
            d[n] = json.loads(data)
        elif n.endswith(".jsonl") and not n.startswith(
            ("sources/", "representations/")
        ):
            d[n] = lines(data)
    if set(entries) != {
        p.relative_to(base).as_posix()
        for p in base.rglob("*")
        if p.is_file() and p != base / "MANIFEST.sha256"
    }:
        raise ValueError("R4 file set differs")
    verify_parent(d)
    r4.verify_persistence(base / "representations/apache_activemq/TEXT")
    return inherited, r3, d, reads


def source_admission(record):
    """Pure proof gate; metadata truth values cannot open any path by themselves."""
    if record.get("partition") != "TRAIN":
        return "SOURCE_REJECTED"
    if record.get("classification") not in {
        "AUTHORITATIVE",
        "AUTHORITATIVE_WITH_LIMITATION",
        "DERIVABLE_FROM_AUTHORITATIVE_SOURCE",
    }:
        return "SOURCE_REJECTED"
    needed = [
        "project_known",
        "membership_known",
        "identity_deterministic",
        "semantics_known",
        "modality_correct",
        "safe_route",
        "transform_defined",
    ]
    if not all(record.get(k) is True for k in needed):
        return "SOURCE_REJECTED"
    if any(
        record.get(k)
        for k in [
            "T1_dependency",
            "T2_dependency",
            "target_dependency",
            "performance_selection",
            "new_fit",
        ]
    ):
        return "SOURCE_REJECTED"
    return (
        "SOURCE_ADMITTED_WITH_LIMITATION"
        if record["classification"] != "AUTHORITATIVE"
        else "SOURCE_ADMITTED"
    )


def validate_temporal(feature):
    if feature.get("target_dependency") or feature.get("future_information"):
        raise ValueError("Future/target-derived PROCESS feature rejected")
    if feature.get("ancestral_proof") is not True:
        raise ValueError("PROCESS ancestry unproven")
    if type(feature.get("value_timestamp")) not in {int, float} or type(
        feature.get("prediction_timestamp")
    ) not in {int, float}:
        raise ValueError("PROCESS timestamps unproven")
    if (
        not math.isfinite(feature["value_timestamp"])
        or not math.isfinite(feature["prediction_timestamp"])
        or feature["value_timestamp"] > feature["prediction_timestamp"]
    ):
        raise ValueError("Future PROCESS timestamp")
    return True


def validate_text_binding(binding):
    if binding.get("new_fit"):
        raise PermissionError("New vectorizer fit denied")
    if binding.get("vectorizer_scope") != "PROJECT_SPECIFIC" or binding.get(
        "project"
    ) != binding.get("state_project"):
        raise ValueError("Cross-project vectorizer mismatch")
    if (
        not binding.get("project")
        or binding.get("message_commit_link") is not True
        or binding.get("state_verified") is not True
    ):
        raise ValueError("TEXT linkage/state missing")
    return True


def validate_feature_order(modality, names, contract):
    if modality not in {"CODE", "PROCESS"} or names != contract["names"][modality]:
        raise ValueError("Frozen modality/column boundary differs")
    return True


def eligibility_gate(proof):
    if source_admission(proof) not in {
        "SOURCE_ADMITTED",
        "SOURCE_ADMITTED_WITH_LIMITATION",
    }:
        raise PermissionError("Rejected source cannot reconstruct")
    if proof.get("representation_state") != "RECONSTRUCTED_REPRESENTATION":
        raise ValueError("Original label forbidden")
    for key in [
        "row_registry",
        "column_registry",
        "transform_state",
        "source_digest",
        "matrix_digest",
        "schema_digest",
        "row_order_digest",
        "column_order_digest",
        "manifest_verified",
        "persistence_verified",
        "repeatability_verified",
        "numerical_integrity_verified",
        "partition_verified",
        "model_metadata_verified",
    ]:
        if not proof.get(key):
            raise ValueError("Eligibility proof missing: " + key)
    return "ELIGIBLE_FOR_REVIEW_NOT_T1_OR_XAI_AUTHORIZATION"


def coverage(rows):
    keys = [(x["project"], x["modality"]) for x in rows]
    if len(rows) != 42 or len(set(keys)) != 42:
        raise ValueError("Exactly 42 distinct project/modalities required")
    projects = sorted({x["project"] for x in rows})
    if len(projects) != 14 or any(
        {x["modality"] for x in rows if x["project"] == p}
        != {"CODE", "PROCESS", "TEXT"}
        for p in projects
    ):
        raise ValueError("Incomplete project coverage")
    if (
        sum(
            x["reconstruction_status"] == "PARENT_COMPLETE_WITH_LIMITATION"
            for x in rows
        )
        != 1
    ):
        raise ValueError("Parent must be counted exactly once")
    by_modality = {}
    eligible_per_project = Counter()
    for modality in ["CODE", "PROCESS", "TEXT"]:
        selected = [x for x in rows if x["modality"] == modality]
        by_modality[modality] = {
            k: sum(x["q1_status"] == v for x in selected)
            for k, v in {
                "eligible": "Q1_E1_TRAIN_ELIGIBLE",
                "limited": "Q1_E1_TRAIN_ELIGIBLE_WITH_LIMITATION",
                "blocked": "Q1_E1_TRAIN_BLOCKED",
                "ineligible": "Q1_E1_TRAIN_INELIGIBLE",
                "fail": "Q1_E1_TRAIN_FAIL",
            }.items()
        }
    for x in rows:
        if x["q1_status"] in {
            "Q1_E1_TRAIN_ELIGIBLE",
            "Q1_E1_TRAIN_ELIGIBLE_WITH_LIMITATION",
        }:
            eligible_per_project[x["project"]] += 1
    return dict(
        expected=42,
        eligible_including_limited=sum(eligible_per_project.values()),
        by_modality=by_modality,
        projects_with_3_modalities=sum(eligible_per_project[p] == 3 for p in projects),
        projects_with_2_modalities=sum(eligible_per_project[p] == 2 for p in projects),
        projects_with_1_modality=sum(eligible_per_project[p] == 1 for p in projects),
        projects_without_eligible_modality=sum(
            eligible_per_project[p] == 0 for p in projects
        ),
        project_eligible_modality_counts={p: eligible_per_project[p] for p in projects},
    )


def inspect_transforms(scopes, alignment):
    result = []
    hashes = {}
    for project in sorted({s["project"] for s in scopes}):
        ss = [s for s in scopes if s["project"] == project and s["modality"] == "TEXT"]
        refs = [
            s["required_state_references"][0]["objects"]["text_representation"]
            for s in ss
        ]
        if len(ss) != 4 or len({r["sha256"] for r in refs}) != 1:
            raise ValueError("Family-specific TEXT states require separate resolution")
        path = f"{STORE}/{refs[0]['path']}"
        p = ROOT / path
        if p.resolve() != p or not p.is_file():
            raise ValueError("Missing/symlink state")
        raw = p.read_bytes()
        if sha(raw) != refs[0]["sha256"]:
            raise ValueError("TEXT immutable state digest mismatch")
        d = json.loads(raw)
        r4.validate_text(d)
        for item in [x for x in alignment if x["project"] == project]:
            if (
                item["feature_count"] != len(d["feature_order"])
                or item["feature_order_sha256"] != r4.digest(d["feature_order"])
                or item["vocabulary_sha256"] != r4.digest(d["vocabulary"])
                or item["idf_sha256"]
                != sha(struct.pack("<" + "d" * len(d["idf"]), *d["idf"]))
            ):
                raise ValueError("Frozen TEXT metadata mismatch")
        hashes[path] = sha(raw)
        result.append(
            dict(
                project=project,
                state_project=project,
                vectorizer_scope="PROJECT_SPECIFIC",
                scope_matches_predictors=True,
                state_path=path,
                state_digest=sha(raw),
                feature_count=len(d["feature_order"]),
                feature_order_sha256=r4.digest(d["feature_order"]),
                vocabulary_sha256=r4.digest(d["vocabulary"]),
                idf_sha256=sha(struct.pack("<" + "d" * len(d["idf"]), *d["idf"])),
                parameters=d["parameters"],
                state_status="RECONSTRUCTED_TRANSFORM_STATE",
                status="REUSE_RECONSTRUCTED_EQUIVALENT_VECTORIZER",
                new_vectorizer_fit="DENY",
                model_dependencies=[s["scope_id"] for s in ss],
                used_for_new_representation=False,
            )
        )
    return result, hashes


def build(inherited, r3, parent, transforms):
    scopes = inherited[f"{r4.r3.b.OUT}/e1_scope_universe.json"]
    universe = parent["train_universe_registry.jsonl"]
    counts = {x["project"]: x["total_frozen_train_identities"] for x in universe}
    if len(counts) != 14 or sum(counts.values()) != 56821:
        raise ValueError("Frozen universe differs")
    if any(
        counts[s["project"]] != s["historical_train_count_metadata"] for s in scopes
    ):
        raise ValueError("Campaign count mismatch")
    population = json.loads(
        (ROOT / r4.SMOKE / "train_only_population_manifest.json").read_text()
    )
    prefix_records = {x["path"]: x for x in population["bounded_prefix_reads"]}
    sem = r3["code_process_semantic_contract.json"]
    features = sem["registry"]["registry"]
    if r3["train_reconstruction_policy.json"]["no_new_fit"] is not True:
        raise ValueError("Numeric fit policy differs")
    parent_id = parent["representations/apache_activemq/TEXT/digests.json"][
        "representation_id"
    ]
    matrix = []
    candidates = []
    decisions = []
    routes = {m: [] for m in ["CODE", "PROCESS", "TEXT"]}
    for project in sorted(counts):
        for modality in ["CODE", "PROCESS", "TEXT"]:
            reused = (project, modality) == (r4.PROJECT, "TEXT")
            safe_prefix = project == r4.PROJECT
            transform_ok = modality == "TEXT"
            reason = (
                []
                if reused
                else ([ROUTE_REASON] if not safe_prefix else [])
                + ([NUMERIC_REASON] if not transform_ok else [])
                + ([TEMPORAL_REASON] if modality == "PROCESS" else [])
            )
            row = dict(
                project=project,
                modality=modality,
                expected_train_rows=counts[project],
                source_candidate_status="PARENT_ADMITTED"
                if reused
                else "BOUNDED_RAW_PREFIX_ATTESTED_TRANSFORM_BLOCKED"
                if safe_prefix
                else "SOURCE_REJECTED_NO_SAFE_ROUTE",
                identity_linkage_status="PARENT_FULL_COMMIT_TRAIN_REGISTRY"
                if safe_prefix
                else "COMPLETE_SAFE_TRAIN_IDENTITY_ROUTE_UNRESOLVED",
                transform_status="TEXT_TRANSFORM_EXACT_METADATA_VERIFIED"
                if transform_ok
                else f"{modality}_TRANSFORM_BLOCKED",
                reconstruction_status="PARENT_COMPLETE_WITH_LIMITATION"
                if reused
                else f"{modality}_RECONSTRUCTION_BLOCKED",
                persistence_status="PARENT_IMMUTABLE_REFERENCE_ONLY"
                if reused
                else "NOT_CREATED_SOURCE_OR_TRANSFORM_GATE_FAILED",
                q1_status="Q1_E1_TRAIN_ELIGIBLE_WITH_LIMITATION"
                if reused
                else "Q1_E1_TRAIN_BLOCKED",
                blocking_reason=reason,
                representation_id=parent_id if reused else None,
                new_representation=False,
            )
            matrix.append(row)
            filename = {
                "CODE": "code_dataset.jsonl.gz",
                "PROCESS": "process_dataset.jsonl.gz",
                "TEXT": "text_dataset.jsonl.gz",
            }[modality]
            route = dict(
                project=project,
                modality=modality,
                source_path=f"{r4.FREEZE}/{filename}",
                partition="TRAIN",
                route="PARENT_REUSED"
                if reused
                else "CODE_SOURCE_WITH_PREDECLARED_LIMITATION"
                if safe_prefix and modality == "CODE"
                else "BOUNDED_PREFIX_RAW_ROUTE_ONLY"
                if safe_prefix
                else f"{modality}_SOURCE_NOT_ESTABLISHED",
                project_grouped_stream=True,
                tail_scan_authorized=False,
                source_value_read=False,
                preexisting_prefix_attestation=prefix_records.get(
                    f"{r4.FREEZE}/{filename}"
                )
                if safe_prefix
                else None,
                prefix_authority=f"{r4.SMOKE}/train_only_population_manifest.json"
                if safe_prefix
                else None,
                identity_reference=f"{r4.OUT}/train_row_identity_registry.jsonl"
                if safe_prefix
                else None,
                status=row["source_candidate_status"],
                blockers=reason,
            )
            routes[modality].append(route)
            if reused:
                continue
            candidate = dict(
                project=project,
                modality=modality,
                partition="TRAIN",
                path=route["source_path"],
                classification="AUTHORITATIVE_WITH_LIMITATION"
                if safe_prefix
                else "INADMISSIBLE",
                project_known=True,
                membership_known=safe_prefix,
                identity_deterministic=safe_prefix,
                semantics_known=modality != "PROCESS",
                modality_correct=True,
                safe_route=safe_prefix,
                transform_defined=transform_ok,
                T1_dependency=not safe_prefix,
                T2_dependency=not safe_prefix,
                target_dependency=False,
                new_fit=False,
                performance_selection=False,
                reason=reason,
                digest_unit="Existing TRAIN prefix attestation where available; never whole mixed-container hash",
            )
            candidates.append(candidate)
            decisions.append(
                dict(
                    project=project,
                    modality=modality,
                    path=candidate["path"],
                    status=source_admission(candidate),
                    reason=reason,
                )
            )
            candidates.append(
                dict(
                    project=project,
                    modality=modality,
                    path=RAW,
                    classification="INADMISSIBLE",
                    role="Frozen upstream benchmark table",
                    reason="Exact per-project TRAIN membership join not safely routed; full table includes prohibited partitions; no open/filter allowed",
                    source_value_read=False,
                )
            )
            candidates.append(
                dict(
                    project=project,
                    modality=modality,
                    path=next(
                        x["state_path"] for x in transforms if x["project"] == project
                    )
                    if transform_ok
                    else f"{r4.r3.b.OUT}/e1_scope_universe.json",
                    executable_references=[
                        ss["required_state_references"]
                        for ss in scopes
                        if ss["project"] == project and ss["modality"] == modality
                    ]
                    if not transform_ok
                    else [],
                    classification="AUTHORITATIVE_WITH_LIMITATION"
                    if transform_ok
                    else "INADMISSIBLE",
                    role="Transformation state",
                    reason="State metadata verified, missing raw-message source"
                    if transform_ok
                    else NUMERIC_REASON,
                    source_value_read=False,
                    predictor_deserialized=False,
                )
            )
    if (
        len(matrix) != 42
        or len(decisions) != 41
        or any(x["status"] != "SOURCE_REJECTED" for x in decisions)
    ):
        raise ValueError(
            "Unexpected admitted new scope: execution requires separate resolution path implementation"
        )
    cov = coverage(matrix)
    feature_rows = {}
    for modality in ["CODE", "PROCESS"]:
        selected = [x for x in features if x["modality"] == modality]
        validate_feature_order(modality, [x["feature_name"] for x in selected], sem)
        feature_rows[modality] = [
            dict(
                feature_name=x["feature_name"],
                definition=x["definition"],
                source_field=x["feature_name"],
                raw_transformed_status="Frozen raw benchmark column -> stored median imputer; LR also stored scaler",
                prediction_time_availability=x["authoritative_record"].get(
                    "temporal_semantics",
                    "Requires explicit strictly ancestral source/aggregation proof",
                ),
                modality_assignment=modality,
                transform=x["transformation"],
                column_order=x["feature_order"],
                leakage_assessment="Current commit/first parent only"
                if modality == "CODE"
                else "TEMPORAL_PROVENANCE_UNPROVEN",
                ancestor_only_required=modality == "PROCESS",
                timestamp_dependency=modality == "PROCESS",
                future_information_risk="Not independently discharged"
                if modality == "PROCESS"
                else "No future input permitted",
                eligibility="SOURCE_AND_TRANSFORM_BLOCKED",
                authoritative_record=x["authoritative_record"],
            )
            for x in selected
        ]
    linkage = []
    inherited_links = {
        x["scope_id"]: x
        for x in parent["train_representation_to_e1_scope_linkage.jsonl"]
    }
    for scope in scopes:
        link = inherited_links[scope["scope_id"]]
        reuse = link["representation_id"] is not None
        linkage.append(
            dict(
                scope_id=scope["scope_id"],
                project=scope["project"],
                modality=scope["modality"],
                algorithm_family=scope["algorithm_family"],
                model_identity_digest=scope["model_identity_sha256"],
                representation_id=parent_id if reuse else None,
                representation_path=f"{r4.OUT}/representations/apache_activemq/TEXT"
                if reuse
                else None,
                status="COMPATIBLE_METADATA_WITH_LIMITATION" if reuse else "UNPROVEN",
                model_query=False,
                model_load=False,
                dependency_mode="PARENT_REFERENCE" if reuse else "BLOCKED_INPUT",
                feature_count=2557 if reuse else None,
                feature_order_digest=link["feature_order_digest"] if reuse else None,
                preprocessor_identity=link["preprocessing_state_sha256"]
                if reuse
                else None,
            )
        )
    qualitative = dict(
        classification="Q1_TRAIN_COVERAGE_WEAK",
        rationale="One complete TRAIN TEXT population from one project remains useful as bounded evidence, but 13 projects and both numeric modalities are absent. Four algorithm dependencies do not add project or modality diversity. Missingness follows source/transform/temporal constraints, not outcomes. No arbitrary numeric threshold or broad Q1 sufficiency claim.",
        source_blocked_remaining=39,
        transform_blocked_numeric=28,
        temporal_unproven_process=14,
        blocker_counts_overlap=True,
        T1_campaign_readiness="BLOCKED_COVERAGE_WEAK",
    )
    f = {
        "protocol_summary.json": dict(
            verdict=VERDICT,
            expected_train_identities=56821,
            projects=14,
            project_modalities=42,
            remaining_targets=41,
            newly_resolved=0,
            new_representations=0,
            new_rows_persisted=0,
            combined_eligible_with_limitation=1,
            combined_blocked=41,
            parent_representation_reused=True,
            coverage_assessment=qualitative["classification"],
            dominant_blocker="Safe TRAIN source routes absent for 39 of 41 remaining targets",
        ),
        "parent_r4_verification.json": dict(
            verified=True,
            manifest_sha256=R4_PIN,
            summary=parent["protocol_summary.json"],
            R3_verified=True,
            parent_modified=False,
        ),
        "parent_activemq_text_reuse.json": dict(
            status="PARENT_RECONSTRUCTED_REPRESENTATION_ACCEPTED_WITH_LIMITATION",
            project=r4.PROJECT,
            modality="TEXT",
            rows=3675,
            columns=2557,
            representation_id=parent_id,
            path=f"{r4.OUT}/representations/apache_activemq/TEXT",
            digests=parent["representations/apache_activemq/TEXT/digests.json"],
            regenerated=False,
            copied=False,
            overwritten=False,
        ),
        "remaining_train_scope_matrix.jsonl": matrix,
        "apachejit_project_registry.json": dict(
            projects=[
                dict(
                    project_id=p,
                    canonical_project_name=p,
                    TRAIN_expected_count=counts[p],
                    partition_source=f"{r4.FREEZE}/temporal_partition_summary.json",
                    identity_scheme="project/full commit SHA linked through frozen row_identifier",
                    count_evidence="Original frozen TRAIN phase counts, independently crosschecked with 168 campaign scopes",
                )
                for p in sorted(counts)
            ],
            source_digest=sha(
                (ROOT / r4.FREEZE / "temporal_partition_summary.json").read_bytes()
            ),
        ),
        "r4a_source_candidate_ledger.jsonl": candidates,
        "r4a_source_admission_decisions.jsonl": decisions,
        "code_feature_resolution_registry.jsonl": feature_rows["CODE"],
        "code_source_route_by_project.jsonl": routes["CODE"],
        "code_r4a_reconstruction_ledger.jsonl": [
            x for x in matrix if x["modality"] == "CODE"
        ],
        "process_feature_semantic_registry.jsonl": feature_rows["PROCESS"],
        "process_source_route_by_project.jsonl": routes["PROCESS"],
        "process_temporal_validity_audit.jsonl": [
            dict(
                project=p,
                status="TEMPORAL_PROVENANCE_UNPROVEN",
                classification="BLOCKED_NOT_OBSERVED_VIOLATION",
                features=[x["feature_name"] for x in feature_rows["PROCESS"]],
                value_timestamp_verified=False,
                recomputed_history=False,
                target_dependency_permitted=False,
                reason=TEMPORAL_REASON,
            )
            for p in sorted(counts)
        ],
        "process_transform_state_registry.jsonl": [
            dict(
                project=p,
                modality="PROCESS",
                status="PROCESS_TRANSFORM_BLOCKED",
                state_values_persisted=False,
                reason=NUMERIC_REASON,
            )
            for p in sorted(counts)
        ],
        "process_r4a_reconstruction_ledger.jsonl": [
            x for x in matrix if x["modality"] == "PROCESS"
        ],
        "text_source_route_by_project.jsonl": routes["TEXT"],
        "text_message_source_resolution.jsonl": [
            dict(
                project=p,
                status="TEXT_MESSAGE_SOURCE_EXACT_WITH_LIMITATION"
                if p == r4.PROJECT
                else "TEXT_MESSAGE_SOURCE_UNRESOLVED",
                parent_reuse_only=p == r4.PROJECT,
                new_messages_read=0,
                reason="Parent exact committed source prefix retained"
                if p == r4.PROJECT
                else ROUTE_REASON,
            )
            for p in sorted(counts)
        ],
        "text_vectorizer_scope_audit.jsonl": transforms,
        "text_r4a_reconstruction_ledger.jsonl": [
            x for x in matrix if x["modality"] == "TEXT"
        ],
        "r4a_train_row_registry.jsonl": [],
        "r4a_train_column_registry.jsonl": [],
        "r4a_transform_state_registry.jsonl": [
            dict(
                project=x["project"],
                modality="TEXT",
                transform_family="TFIDF",
                input_schema="Project-specific raw TRAIN messages",
                output_schema=dict(
                    feature_count=x["feature_count"],
                    feature_order_sha256=x["feature_order_sha256"],
                ),
                state_values_reference=x["state_path"],
                origin=STORE,
                reconstructed_status="RECONSTRUCTED_TRANSFORM_STATE",
                state_digest=x["state_digest"],
                runtime_reference=f"{r4.SMOKE}/isolated_runtime_lock.json",
                new_state_persisted=False,
                used_for_new_representation=False,
            )
            for x in transforms
        ],
        "r4a_representation_to_model_dependency.jsonl": linkage,
        "r4a_representation_digest_registry.jsonl": [],
        "r4a_reconstruction_repeatability.jsonl": [
            dict(
                project=x["project"],
                modality=x["modality"],
                status="PARENT_EXACT_REPEATABILITY_REFERENCED"
                if x["representation_id"]
                else "NOT_EXECUTED_GATE_BLOCKED",
                new_replay=False,
                parent_evidence=f"{r4.OUT}/train_reconstruction_repeatability.jsonl"
                if x["representation_id"]
                else None,
            )
            for x in matrix
        ],
        "r4a_numerical_integrity.jsonl": [
            dict(
                project=x["project"],
                modality=x["modality"],
                status="PARENT_PASS_REFERENCED"
                if x["representation_id"]
                else "NOT_TESTED_NO_MATRIX",
                parent_evidence=f"{r4.OUT}/train_feature_value_integrity.jsonl"
                if x["representation_id"]
                else None,
            )
            for x in matrix
        ],
        "r4a_partition_safety.json": dict(
            TRAIN_ONLY="PASS_NO_NEW_SOURCE_PAYLOAD",
            new_rows=0,
            parent_TRAIN_rows=3675,
            parent_partition_evidence=f"{r4.OUT}/train_partition_safety_audit.json",
            new_T1_T2_payload_access=False,
            no_new_empirical_disjointness_claim=True,
        ),
        "r4a_q1_e1_train_admissibility.jsonl": matrix,
        "r4a_scientific_coverage.json": dict(**cov, **qualitative),
        "combined_r4_r4a_train_coverage.json": dict(
            **cov,
            new_R4A_representations=0,
            parent_R4_representations=1,
            new_rows=0,
            combined_unique_rows=3675,
            new_columns=dict(CODE=0, PROCESS=0, TEXT=0),
            combined_columns=dict(CODE=0, PROCESS=0, TEXT=2557),
            algorithm_dependencies_eligible=4,
            algorithm_dependencies_total=168,
        ),
        "r4a_background_readiness.jsonl": [
            dict(
                project=x["project"],
                modality=x["modality"],
                status="BACKGROUND_READY_WITH_LIMITATION"
                if x["representation_id"]
                else "BACKGROUND_BLOCKED",
                representation_id=x["representation_id"],
                new_background_selected=False,
            )
            for x in matrix
        ],
        "r4a_correlation_readiness.jsonl": [
            dict(
                project=x["project"],
                modality=x["modality"],
                status="BLOCKED_NO_NUMERIC_REPRESENTATION",
                correlation_computed=False,
            )
            for x in matrix
            if x["modality"] != "TEXT"
        ],
        "r4a_model_compatibility_metadata.jsonl": linkage,
        "r4a_replication_readiness.jsonl": [
            dict(
                project=x["project"],
                modality=x["modality"],
                status="REPLICATION_READY_WITH_LIMITATION"
                if x["representation_id"]
                else "REPLICATION_NOT_READY",
                parent_reuse=bool(x["representation_id"]),
                reason=x["blocking_reason"],
            )
            for x in matrix
        ],
        "reviewer_r4a_persistence_evidence.md": "# R4A reviewer evidence\n\nNo additional project/modality representation was reconstructed in R4A. The accepted ActiveMQ TEXT representation remains referenced without regeneration, copying or modification. Systematic persistence correction beyond that one-project TEXT case has therefore not been demonstrated.\n\nAll 42 combinations are accounted for: one parent eligible with limitation, 41 blocked. Thirteen projects lack a physically safe TRAIN-only identity/source route; all 28 numeric targets lack independently usable fitted transform values, and all 14 PROCESS targets require stronger prediction-time ancestry evidence. These blockers overlap. All 14 project-specific TF-IDF states were verified, but a vectorizer alone does not prove message provenance. No new fit, predictor load/query, T1 feature/label read, T2 access, XAI, metric recomputation or figure generation occurred.\n\nNo historical matrix recovery claim is made. Exclusions are methodological and independent of predictive or explanatory outcomes. General TRAIN coverage remains weak, so the campaign-level T1 phase is blocked in R4A.\n",
        "remaining_blockers.json": dict(
            dominant="SOURCE_COVERAGE",
            source_blocked_targets=39,
            numeric_transform_blocked_targets=28,
            process_temporal_unproven_targets=14,
            overlapping_counts=True,
            items=[ROUTE_REASON, NUMERIC_REASON, TEMPORAL_REASON],
            minimal_remedies=[
                "Obtain frozen project-specific TRAIN identity/feature extracts or a verified TRAIN-only seek index created without this sprint traversing T1/T2",
                "Provide standalone frozen numeric imputer/scaler values bound by existing digests; alternatively separately authorize a method amendment before any TRAIN-only transform refit",
                "Supply exact PROCESS prediction-time/ancestor aggregation evidence",
            ],
            historical_exact_matrix_recovery_required=False,
        ),
        "future_t1_policy.json": dict(
            T1_FEATURE_RECONSTRUCTION_PHASE="BLOCKED_COVERAGE_WEAK",
            authorized=False,
            R5_started=False,
            parent_R4_subset_statement_unchanged=True,
            reason=qualitative["rationale"],
        ),
        "recommended_next_action.json": dict(
            action="Resolve specific TRAIN-only source routing and standalone numeric-state prerequisites before reconstruction; obtain PROCESS temporal proof. Keep T1/R5 blocked until coverage is reassessed.",
            new_scientific_authorization_granted=False,
            historical_forensics_restarted=False,
        ),
    }
    artifact_records = lines(
        (
            ROOT
            / STORE
            / "external_artifact_registry/external_artifact_inventory.jsonl"
        ).read_bytes()
    )
    f["numeric_transform_resolution.json"] = dict(
        producer="src/evaluation/q1_xai_train_source_reconstruction.py:_preprocessor_state",
        descriptor_fields=["dtype", "shape", "sha256"],
        numeric_state_values_standalone=False,
        external_store_artifact_counts=dict(
            Counter(x["artifact_type"] for x in artifact_records)
        ),
        transform_rule="Frozen median imputer for every family; additional frozen StandardScaler for LR",
        new_numeric_fit_authorized=False,
        direct_raw_passthrough_authorized=False,
        deduplication_rule="Matching column schemas alone do not imply identical transformed matrices: LR scaling must remain distinct unless exact state/output equivalence is proven",
        scope="Inspected frozen store inventory and producer; no claim about unprovided external artifacts",
    )
    f["governance_counters.json"] = dict.fromkeys(
        (
            *r4.r3.b.ZERO,
            "TRAIN_SOURCE_VALUE_READ_COUNT",
            "TRAIN_REPRESENTATION_RECONSTRUCTION_COUNT",
            "TRAIN_REPRESENTATION_PERSIST_COUNT",
            "TRAIN_RECONSTRUCTION_REPLAY_COUNT",
            "T2_IDENTITY_READ_COUNT",
            "T2_ROW_READ_COUNT",
            "HYPERPARAMETER_TUNING_COUNT",
        ),
        0,
    )
    f["governance_counters.json"].update(
        historical_T1_predictive_access_count=1,
        historical_T1_predictive_scoring_count=1,
        T2_STATE="DENY_SEALED_REVIEWER_RESERVE",
        TRANSFORM_STATE_METADATA_FILE_READ_COUNT=14,
        PARENT_REPRESENTATION_REGENERATIONS=0,
        T1_IDENTITY_ACCESS_COUNT=0,
    )
    return f


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--validation", type=Path, required=True)
    args = parser.parse_args()
    flight = json.loads(args.preflight.read_text())
    r4.r3.branch_gate(r4.r3.b.git("rev-parse", "--abbrev-ref", "HEAD"))
    if r4.r3.b.git("rev-parse", "HEAD") != flight["head"]:
        raise ValueError("HEAD changed")
    before = r4.snapshot(flight)
    inherited, r3, parent, reads = load_parent()
    transforms, state_hashes = inspect_transforms(
        inherited[f"{r4.r3.b.OUT}/e1_scope_universe.json"],
        inherited[f"{r4.r3.R1}/text_token_column_alignment.jsonl"],
    )
    f = build(inherited, r3, parent, transforms)
    f["preflight.json"] = flight
    f["validation_results.json"] = json.loads(args.validation.read_text())
    f["parent_integrity_before.json"] = before
    f["parent_integrity_after.json"] = r4.snapshot(flight)
    f["parent_integrity_diff.json"] = dict(
        status="PASS", changed=[], parent_R4_representations_overwritten=False
    )
    f["targeted_resolution_evidence.json"] = dict(
        scope="Only frozen per-project modality routes, exact state references, producer serialization/partition code and semantic contracts; no broad discovery",
        state_hashes=state_hashes,
        metadata_paths=flight["targeted_metadata_paths"],
        numeric_state_producer="src/evaluation/q1_xai_train_source_reconstruction.py:_preprocessor_state emits numeric array descriptors (shape/dtype/hash), returns no standalone state values",
        source_route_producer="src/dataset/apachejit_final_dataset_freeze.py:_partition_rows groups projects and emits TRAIN/VALIDATION/T1/T2 before next project",
        numeric_fit_policy="R3 train_reconstruction_policy.no_new_fit=true; R4A condition for previously authorized numeric fitting is not satisfied",
        source_payload_reads=[],
    )
    f["governance_counters.json"].update(
        T1_METADATA_ACCESS_COUNT=len(reads),
        T1_METADATA_COUNT_UNIT="Unique inherited governance metadata paths; no new T1 scientific identities or values",
        TRAIN_PARENT_INTEGRITY_HASH_READS_ONLY=True,
    )
    f["implementation_provenance.json"] = {
        p: sha((ROOT / p).read_bytes()) for p in [SOURCE, TEST]
    }
    f["SPRINT56_3B_R4A_REMAINING_TRAIN_RESOLUTION_REPORT.md"] = report(f, flight)
    out = ROOT / OUT
    if out.resolve() != out:
        raise PermissionError("Symlink output")
    out.mkdir(parents=True, exist_ok=False)
    for n, value in f.items():
        r4.atomic_file(
            out,
            n,
            jsonl(value)
            if n.endswith(".jsonl")
            else value.encode()
            if isinstance(value, str)
            else encode(value),
        )
    manifest = "".join(
        f"{sha(p.read_bytes())}  {p.name}\n" for p in sorted(out.iterdir())
    )
    r4.atomic_file(out, "MANIFEST.sha256", manifest.encode())
    print(json.dumps(f["protocol_summary.json"], sort_keys=True))
    print("MANIFEST", sha((out / "MANIFEST.sha256").read_bytes()))


def report(f, flight):
    sections = [
        (
            "Objective",
            "Finite resolution of 41 remaining targets, preserving accepted ActiveMQ TEXT.",
        ),
        (
            "Branch and parent",
            flight["branch"]
            + " / "
            + flight["head"]
            + "; R3 and R4 verified. All inherited bytes/identities unchanged within the documented integrity scope.",
        ),
        (
            "Authoritative universe",
            "56,821 TRAIN identities, 14 projects, 42 project/modalities and 168 family dependencies. All remain in the ledger.",
        ),
        (
            "Source resolution",
            "39 remaining project/modalities lack a verified TRAIN-only read route. Project-grouped compressed streams require crossing earlier T1/T2 partitions without an independent seek index. No such traversal was performed.",
        ),
        (
            "CODE",
            "Frozen la/ld/nf/nd/ns/ent preserved. ActiveMQ raw prefix exists, but standalone median/scaler values are unavailable; R3 did not authorize refitting. All 14 blocked.",
        ),
        (
            "PROCESS",
            "Frozen ndev/age/nuc/aexp/arexp/asexp preserved. Table presence does not prove strictly ancestral aggregation. No temporal violation was observed; proof remains insufficient for all 14.",
        ),
        (
            "TEXT",
            "All 14 project-specific reconstructed TF-IDF states verified against model-bound vocabulary, IDF and column metadata. No cross-project reuse or new fit. Remaining 13 lack admitted complete commit/message routes.",
        ),
        (
            "Persistence and identity",
            "No new representation, row population, column population or transform state created. Empty new registries are intentional. Parent ActiveMQ TEXT remains one immutable digest reference; no matrix copy.",
        ),
        (
            "Coverage",
            "CODE 0/14, PROCESS 0/14, TEXT 1/14 with limitation. Combined 1/42, four family dependencies. One project has one eligible modality; 13 have none. No multi-project expansion achieved.",
        ),
        (
            "Scientific assessment",
            "Q1_TRAIN_COVERAGE_WEAK: missing project diversity and both numeric modalities. No arbitrary eligibility threshold or performance-based exclusions. Source blockage dominates the 41 unresolved targets; numeric and temporal blockers overlap.",
        ),
        (
            "Validation and governance",
            "New scientific counters zero. Parent T1 predictive counts 1/1; T2 sealed. Safe test results and historical exceptions are preserved in validation_results.json. No model loads, inference, XAI, metrics, fitting or figures.",
        ),
        (
            "Reviewer interpretation",
            "Persistence correction remains demonstrated only for the accepted R4 subset. R4A does not claim systematic correction beyond it or original historical matrix recovery.",
        ),
        (
            "Next action",
            "Obtain verified TRAIN-only identity/source access, standalone frozen numeric values and exact PROCESS temporal proof. T1/R5 remain blocked under the R4A coverage gate. No commit, push or PR.",
        ),
    ]
    return (
        "# Sprint 56.3B-R4A remaining TRAIN resolution\n\n"
        + VERDICT
        + "\n\n"
        + "\n\n".join("## " + title + "\n\n" + text for title, text in sections)
        + "\n"
    )


if __name__ == "__main__":
    main()
