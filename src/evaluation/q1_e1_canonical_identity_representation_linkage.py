# ruff: noqa: E501
"""56.3B-R2 canonical linkage audit; no model or explanation execution.

Only inherited whitelisted metadata, immutable R1 output and explicitly admitted
80-row TRAIN derivatives are read. A row digest is not a commit identity proof.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import struct
from pathlib import Path

from src.evaluation import q1_e1_input_provenance_eligibility as b
from src.evaluation import q1_e1_population_representation_provenance_resolution as r1

ROOT = b.ROOT
OUT = "audits/q1-e1-canonical-identity-representation-linkage/1.0.0"
SOURCE = "src/evaluation/q1_e1_canonical_identity_representation_linkage.py"
TEST = "tests/evaluation/test_q1_e1_canonical_identity_representation_linkage.py"
RAW = "audits/q1-primary-xai-runtime-smoke/1.0.0/selected_train_rows.json"
RAW_HASH = "5356e409cf20c0672476eeed339b040147a397e30629b18f7a110b0d715afed7"
R1_MANIFEST = "cee837e4dd4a6d06061710f5e88a37e93f243265c21bce8349efeb62d78ffbec"
VERDICT = "56_3B_R2_BLOCKED_CANONICAL_IDENTITY_LINKAGE_INCOMPLETE"
CRITICAL = (
    "partition",
    "project",
    "commit",
    "source_row",
    "modality",
    "raw_source",
    "transformation",
    "row_order",
    "column_order",
    "representation_value",
    "model_identity",
)
SERIALIZATION = dict(
    version="E1R2_ROW_V1",
    dtype="IEEE754_FLOAT64_LITTLE_ENDIAN",
    dense="ASCII E1R2_ROW_V1 + NUL + D; uint64_le column_count; contiguous float64_le values",
    sparse="ASCII E1R2_ROW_V1 + NUL + S; uint64_le column_count,nnz; sorted uint64_le indices; paired float64_le values",
    shape="One scientific row (1,column_count); no matrix row ordinal in value digest",
    sparse_order="Sort index-value pairs ascending by index; reject duplicates; preserve explicit zeros",
    nonfinite="REJECT_NAN_POSITIVE_INFINITY_NEGATIVE_INFINITY",
    signed_zero="Preserve IEEE754 sign bit",
    strings="Exact Unicode strings, no trimming, case folding, Unicode normalization or SHA expansion",
    utf8="Strict UTF8 for text digests; invalid strings rejected",
    numeric_decimal_precision="NOT_APPLICABLE_BINARY",
    json="UTF8; sorted keys; ensure_ascii=true; compact comma/colon separators; allow_nan=false; one LF",
    filesystem_metadata="EXCLUDED",
    digest="SHA256",
    frozen_before_row_digest_computation=True,
)
sha, encode, canonical = b.sha, b.encode, r1.canonical


def normalize_identity(project, identity, kind):
    if not isinstance(project, str) or not project or not isinstance(identity, str):
        return dict(status="IDENTITY_UNRESOLVED", key=None)
    if kind == "full_commit_sha" and re.fullmatch("[0-9a-f]{40}", identity):
        return dict(
            status="IDENTITY_CANONICAL_EXACT",
            key=[project, identity],
            proof_requirement="Authoritative project/commit binding required independently",
        )
    if kind == "frozen_row_sha256" and re.fullmatch("[0-9a-f]{64}", identity):
        return dict(
            status="IDENTITY_CANONICAL_WITH_LIMITATION",
            key=[project, identity],
            limitation="Internal row identity only; commit/source mapping unavailable",
        )
    return dict(status="IDENTITY_AMBIGUOUS", key=None)


def validate_identity_link(left, right):
    if left.get("partition") not in {"TRAIN", "T1"} or right.get("partition") not in {
        "TRAIN",
        "T1",
    }:
        raise PermissionError("T2/unknown partition denied")
    for field in ("partition", "project", "commit_identity", "scientific_identity"):
        if not left.get(field) or left[field] != right.get(field):
            raise ValueError("Identity linkage mismatch or missing: " + field)
    if (
        normalize_identity(left["project"], left["commit_identity"], "full_commit_sha")[
            "status"
        ]
        != "IDENTITY_CANONICAL_EXACT"
    ):
        raise ValueError("Exact full commit identity required")
    return True


def row_bytes(values, columns, indices=None):
    if type(columns) is not int or columns <= 0:
        raise ValueError("Positive column count required")
    if any(type(v) not in (int, float) or not math.isfinite(v) for v in values):
        raise ValueError("Nonfinite/nonnumeric representation")
    prefix = b"E1R2_ROW_V1\0"
    if indices is None:
        if len(values) != columns:
            raise ValueError("Dense width mismatch")
        return (
            prefix
            + b"D"
            + struct.pack("<Q", columns)
            + struct.pack("<" + "d" * columns, *values)
        )
    if (
        len(indices) != len(values)
        or len(set(indices)) != len(indices)
        or any(type(i) is not int or not 0 <= i < columns for i in indices)
    ):
        raise ValueError("Malformed sparse indices")
    pairs = sorted(zip(indices, values, strict=True))
    return (
        prefix
        + b"S"
        + struct.pack("<QQ", columns, len(pairs))
        + b"".join(struct.pack("<Q", i) for i, _ in pairs)
        + b"".join(struct.pack("<d", v) for _, v in pairs)
    )


def scope_status(strength, complete_population, partial_rows):
    if any(v not in {"P0", "P1", "P2", "P3", "P4"} for v in strength.values()):
        raise ValueError("Unknown provenance strength")
    if complete_population and all(strength.get(k) in {"P3", "P4"} for k in CRITICAL):
        return "CANONICAL_LINKAGE_COMPLETE"
    return (
        "CANONICAL_LINKAGE_PARTIAL" if partial_rows else "CANONICAL_LINKAGE_UNRESOLVED"
    )


class Evidence:
    def __init__(self, root=ROOT):
        self.root = Path(root).resolve()
        self.reader = r1.Reader(root)
        self.matrices = b.Reader(root)
        self.docs = {}
        self.reads = {}
        self.raw = []

    def load(self):
        manifest = self.root / r1.OUT / "MANIFEST.sha256"
        if manifest.resolve() != manifest:
            raise ValueError("R1 manifest symlink")
        raw = manifest.read_bytes()
        if sha(raw) != R1_MANIFEST:
            raise ValueError("Parent R1 manifest differs")
        self.reads[str(manifest.relative_to(self.root))] = sha(raw)
        names = []
        for line in raw.decode().splitlines():
            h, n = line.split("  ", 1)
            if Path(n).name != n or n in names:
                raise ValueError("R1 manifest traversal/duplicate")
            names.append(n)
            p = self.root / r1.OUT / n
            if p.resolve() != p:
                raise ValueError("R1 symlink")
            payload = p.read_bytes()
            if sha(payload) != h:
                raise ValueError("R1 digest mismatch")
            self.reads[str(p.relative_to(self.root))] = h
            if n.endswith(".jsonl"):
                self.docs[n] = [json.loads(x) for x in payload.decode().splitlines()]
            elif n.endswith(".json"):
                self.docs[n] = json.loads(payload)
        if set(names) != {
            p.name for p in manifest.parent.iterdir() if p.name != "MANIFEST.sha256"
        }:
            raise ValueError("R1 file set differs")
        verify_parent(self.docs)
        self.reader.load()
        self.matrices.load()
        # Prior verified inventory admits precisely these raw TRAIN-only bytes.
        p = self.root / RAW
        if p.resolve() != p:
            raise ValueError("Raw TRAIN symlink")
        raw = p.read_bytes()
        if sha(raw) != RAW_HASH:
            raise ValueError("Raw TRAIN digest mismatch")
        self.reads[RAW] = sha(raw)
        self.raw = json.loads(raw)
        if len(self.raw) != 80 or any(
            x["partition"] != "TRAIN"
            or x["project"] != "apache/activemq"
            or set(x) != {"C", "P", "T", "partition", "project", "row_identifier"}
            for x in self.raw
        ):
            raise ValueError("Raw partial source contract differs")
        producer = "src/dataset/apachejit_final_dataset_freeze.py"
        code_path = self.root / producer
        if code_path.resolve() != code_path:
            raise ValueError("Identity producer symlink")
        code = code_path.read_bytes()
        if not all(
            token in code
            for token in [
                b"apachejit-v2|",
                b"source_apachejit_row_identity",
                b"LABEL_NAME: bool(row.buggy)",
            ]
        ):
            raise ValueError("Frozen identity producer contract differs")
        self.reads[producer] = sha(code)
        self.reads.update(self.reader.reads)
        self.reads.update(self.matrices.reads)
        return self


def verify_parent(d):
    s = d["protocol_summary.json"]
    if (
        s["verdict"] != r1.VERDICT
        or s["candidate_scopes"] != 168
        or s["complete_train_route"]
    ):
        raise ValueError("Parent R1 material difference: STOP")
    if d["t1_feature_value_access_authorization_contract.json"]["authorized"]:
        raise ValueError("Parent T1 authorization changed")
    if any(d["governance_counters.json"][k] for k in b.ZERO):
        raise ValueError("Parent scientific counters differ")
    deps = d["reconstructed_state_e1_dependency_ledger.jsonl"]
    if len(deps) != 168 or any(x["origin"] != "RECONSTRUCTED" for x in deps):
        raise ValueError("Parent reconstructed state boundary differs")
    return True


def coverage(rows):
    result = {}
    mapping = {
        "CANONICAL_LINKAGE_COMPLETE": "exact",
        "CANONICAL_LINKAGE_COMPLETE_WITH_LIMITATION": "exact_with_limitation",
        "CANONICAL_LINKAGE_PARTIAL": "partial",
        "CANONICAL_LINKAGE_UNRESOLVED": "unresolved",
        "CANONICAL_LINKAGE_FAIL": "fail",
    }
    for dims in [
        ("project",),
        ("modality",),
        ("algorithm",),
        ("project", "modality"),
        ("modality", "algorithm"),
        ("project", "modality", "algorithm"),
    ]:
        groups = {}
        for row in rows:
            k = "|".join(row[x] for x in dims)
            counts = groups.setdefault(k, dict.fromkeys(mapping.values(), 0))
            counts[mapping[row["linkage_status"]]] += 1
        result[" × ".join(dims)] = groups
    return result


def build(e, paths):
    d = e.docs
    prior = e.reader.docs
    scopes = b.universe(prior[f"{b.OUT}/e1_scope_universe.json"])
    material = b.index(e.matrices.load()[f"{b.MAT}/e1_materialization_ledger.jsonl"])
    features = prior[f"{b.POP}/feature_order_registry.json"]["base_predictors"]
    raw_by_id = {r["row_identifier"]: r for r in e.raw}
    if len(raw_by_id) != 80:
        raise ValueError("Duplicate partial source identities")
    ledgers = []
    row_registry = []
    column_registry = []
    values = []
    models = []
    strengths = []
    texts = []
    for s in scopes:
        sid = s["scope_id"]
        k = b.key(s)
        m = material[k]
        common = dict(
            scope_id=sid,
            project=s["project"],
            algorithm=s["algorithm_family"],
            modality=s["modality"],
        )
        logical = f"{s['project']}|{s['algorithm_family']}|FINAL_BASE|{s['historical_configuration']}"
        feature = features[logical]
        names = feature["order"]
        if (
            len(names) != len(set(names))
            or sha(canonical(names)) != feature["order_sha256"]
        ):
            raise ValueError("Feature order identity mismatch")
        if s["modality"] in b.SEMANTICS and names != b.SEMANTICS[s["modality"]]:
            raise ValueError("CODE/PROCESS semantic mismatch")
        schema = sha(
            canonical(dict(modality=s["modality"], dtype="<f8", columns=names))
        )
        column_registry.append(
            dict(
                common,
                feature_names=names,
                n_columns=len(names),
                schema_digest=schema,
                column_order_digest=feature["order_sha256"],
                status="COLUMN_IDENTITY_EXACT_METADATA",
                observed_in_matrix=bool(m["matrix"]),
                evidence=f"{b.POP}/feature_order_registry.json",
            )
        )
        matrix = None
        if m["matrix"]:
            matrix = e.matrices.train_matrix(m)
            check = b.matrix_integrity(matrix, names)
            if check["status"] != "PASS_PARTIAL_TRAIN_ONLY":
                raise ValueError("Partial matrix integrity fails")
            if set(matrix["row_ids"]) != set(raw_by_id):
                raise ValueError("Raw/matrix identity mismatch")
            x = matrix["X"]
            for i, rid in enumerate(matrix["row_ids"]):
                if x["format"] == "DENSE":
                    serialized = row_bytes(x["values"][i], len(names))
                else:
                    start, end = x["indptr"][i : i + 2]
                    serialized = row_bytes(
                        x["data"][start:end], len(names), x["indices"][start:end]
                    )
                digest = sha(serialized)
                row_registry.append(
                    dict(
                        common,
                        partition="TRAIN",
                        matrix_path=m["matrix"]["path"],
                        matrix_row_index=i,
                        scientific_identity=rid,
                        commit_identity=None,
                        status="ROW_IDENTITY_EXACT_WITH_LIMITATION",
                        limitation="Exact persisted internal row binding; canonical commit/source location unproven",
                        source_digest=m["matrix"]["hash"],
                    )
                )
                values.append(
                    dict(
                        common,
                        partition="TRAIN",
                        identity=rid,
                        representation_digest=digest,
                        serialization_contract="E1R2_ROW_V1",
                        source_digest=m["matrix"]["hash"],
                        schema_digest=schema,
                        order_digest=feature["order_sha256"],
                        representation_origin="RECONSTRUCTED_REPRESENTATION",
                        original_matrix_claim=False,
                    )
                )
                if s["modality"] == "TEXT":
                    msg = raw_by_id[rid]["T"]
                    if not isinstance(msg, str):
                        raise ValueError("Raw message type mismatch")
                    texts.append(
                        dict(
                            common,
                            partition="TRAIN",
                            identity=rid,
                            commit_identity=None,
                            raw_message_sha256=sha(
                                msg.encode("utf-8", errors="strict")
                            ),
                            raw_source_digest=RAW_HASH,
                            representation_digest=digest,
                            status="TEXT_LINKAGE_PARTIAL",
                            numerical_transform_reexecuted=False,
                            raw_message_commit_proof=False,
                            matching_basis="EXACT_INTERNAL_ROW_ID_IN_TWO_VERIFIED_DERIVATIVES",
                            limitation="No canonical commit provenance; no claim of original vector recovery",
                        )
                    )
        strength = dict(
            partition="P2",
            project="P4",
            commit="P0",
            source_row="P0",
            modality="P4",
            raw_source="P2",
            transformation="P4",
            row_order="P4" if matrix else "P0",
            column_order="P4",
            representation_value="P4" if matrix else "P0",
            model_identity="P4",
        )
        status = scope_status(strength, False, bool(matrix))
        record = dict(
            common,
            partition="TRAIN_AND_T1_CANDIDATE_SCOPE",
            commit_identity=None,
            source_identity=None,
            source_location=None,
            source_schema_digest=None,
            transform_identity=sha(canonical(feature["preprocessing_state"])),
            representation_row_identity=None,
            representation_schema_digest=schema,
            representation_order_digest=feature["order_sha256"],
            representation_value_digest=None,
            model_identity=s["model_identity_sha256"],
            provenance_strength=strength,
            linkage_status=status,
            partial_train_rows=80 if matrix else 0,
            complete_canonical_rows=0,
            t1_feature_access_authorized=False,
            limitation="Internal TRAIN derivative linkage only; canonical identity/source route missing",
        )
        ledgers.append(record)
        strengths.append(
            dict(common, elements=strength, all_critical_at_least_P3=False)
        )
        dep = next(
            r
            for r in d["reconstructed_state_e1_dependency_ledger.jsonl"]
            if r["scope_id"] == sid
        )
        if feature["executable"]["sha256"] not in [
            r["expected_sha256"] for r in dep["objects"]
        ]:
            raise ValueError("Representation/model digest mismatch")
        models.append(
            dict(
                common,
                model_identity_sha256=s["model_identity_sha256"],
                reconstructed_state_digest=[
                    x["canonical_state_sha256"] for x in s["required_state_references"]
                ],
                runtime_contract=dep["runtime_match"],
                feature_count=len(names),
                feature_order_digest=feature["order_sha256"],
                preprocessing_identity=feature["preprocessing_state"],
                model_origin="RECONSTRUCTED",
                status="MODEL_LINKAGE_EXACT_WITH_LIMITATION",
                scope="PERSISTED_METADATA_AND_PARTIAL_DERIVATIVE_ONLY",
                complete_population_representation_linkage=False,
                model_loaded=False,
            )
        )
    expected = d["train_identity_access_path.json"]["expected"]
    train = []
    summaries = []
    completeness = []
    for project, exp in sorted(expected.items()):
        n = 80 if project == "apache/activemq" else 0
        summaries.append(
            dict(
                project=project,
                total_train=exp["count"],
                identity_exact_n=n,
                commit_link_exact_n=0,
                source_row_exact_n=0,
                representation_link_exact_n=0,
                coverage_fraction=0,
                partial_derivative_identity_fraction=n / exp["count"],
                expected_membership_digest=exp["membership_digest"],
                status="TRAIN_LINKAGE_PARTIAL" if n else "TRAIN_LINKAGE_UNRESOLVED",
            )
        )
        for mod in b.MODALITIES.values():
            completeness.append(
                dict(
                    project=project,
                    modality=mod,
                    total_expected_train_rows=exp["count"],
                    rows_identity_linked=n,
                    rows_source_linked=0,
                    rows_representation_linked=0,
                    rows_digest_verified=n,
                    coverage=0,
                    partial_derivative_rows=n,
                    status="TRAIN_REPRESENTATION_PARTIAL"
                    if n
                    else "TRAIN_REPRESENTATION_UNRESOLVED",
                    count_unit="Unique scientific identities, not multiplied by model family",
                )
            )
    for rid, row in sorted(raw_by_id.items()):
        train.append(
            dict(
                partition="TRAIN",
                project=row["project"],
                scientific_identity=rid,
                canonical_identity_key=normalize_identity(
                    row["project"], rid, "frozen_row_sha256"
                )["key"],
                commit_identity=None,
                source_identity=None,
                source_location=None,
                derivative_location=RAW,
                derivative_digest=RAW_HASH,
                linkage_status="TRAIN_LINKAGE_PARTIAL",
            )
        )
    files = {
        "protocol_summary.json": dict(
            verdict=VERDICT,
            candidate_scopes=168,
            canonical_complete_scopes=0,
            partial_scopes=12,
            unresolved_scopes=156,
            partial_train_unique_identities=80,
            representation_row_digests=len(values),
        ),
        "parent_r1_verification.json": dict(
            verified=True,
            manifest_sha256=R1_MANIFEST,
            parent_summary=d["protocol_summary.json"],
            parent_state_unchanged=True,
        ),
        "canonical_identity_representation_linkage_schema.json": dict(
            type="object",
            required=[
                "partition",
                "project",
                "commit_identity",
                "source_identity",
                "source_location",
                "modality",
                "source_schema_digest",
                "transform_identity",
                "representation_row_identity",
                "representation_schema_digest",
                "representation_order_digest",
                "representation_value_digest",
                "model_identity",
                "provenance_strength",
                "linkage_status",
            ],
            null_policy="Missing links stored as null and prohibit complete status",
            granularity="Canonical row × scope; scope ledger is a summary, not fabricated full row records",
        ),
        "canonical_identity_normalization.json": dict(
            status="IDENTITY_CANONICAL_WITH_LIMITATION",
            available_key=["project", "exact_frozen_row_identifier"],
            preferred_key=["project", "full_commit_sha"],
            full_sha_available_in_admitted_sources=False,
            short_sha_expansion="FORBIDDEN",
            row_index_matching="FORBIDDEN",
            message_similarity_matching="FORBIDDEN",
            normalization="No trimming, case/Unicode normalization, numeric coercion or heuristic merging",
            source_recipe="SHA256 UTF8 apachejit-v2|project|canonical_repository|commit_sha",
            inverse_mapping="NOT_DERIVABLE_FROM_SHA256_ALONE",
        ),
        "train_canonical_identity_linkage.jsonl": train,
        "train_linkage_coverage_summary.json": dict(
            projects=summaries,
            total_expected_train=sum(x["count"] for x in expected.values()),
            unique_internal_identities=80,
            canonical_commit_links=0,
            canonical_coverage=0,
        ),
        "t1_canonical_identity_linkage.jsonl": [],
        "representation_row_identity_registry.jsonl": row_registry,
        "representation_column_identity_registry.jsonl": column_registry,
        "representation_value_digest_registry.jsonl": values,
        "canonical_representation_serialization_contract.json": SERIALIZATION,
        "train_representation_completeness.json": completeness,
        "t1_feature_access_linkage_readiness.json": dict(
            status="T1_FEATURE_ACCESS_LINKAGE_NOT_READY",
            identity_linkage_status="T1_IDENTITY_LINKAGE_UNRESOLVED",
            allowed_identity_rows=0,
            feature_access_authorized=False,
            authorization="BLOCKED_PENDING_LINKAGE_AND_SEPARATE_HUMAN_AUTHORIZATION",
        ),
        "canonical_partition_boundary_evidence.json": dict(
            status="UNPROVEN",
            TRAIN_T1="COMPLETE_IDENTITY_SETS_UNAVAILABLE",
            TRAIN_T2="NOT_PROVEN_T2_SEALED",
            T1_T2="NOT_PROVEN_T2_SEALED",
            inherited_boundary_ref=f"{r1.OUT}/partition_identity_resolution.json",
            no_disjointness_claim=True,
        ),
        "representation_to_model_identity_linkage.jsonl": models,
        "canonical_linkage_provenance_strength.jsonl": strengths,
        "canonical_linkage_scope_ledger.jsonl": ledgers,
        "coverage_summary.json": coverage(ledgers),
        "text_commit_message_linkage.jsonl": [
            dict(
                identity=r["scientific_identity"],
                project=r["project"],
                partition="TRAIN",
                commit_identity=None,
                raw_message_sha256=sha(
                    raw_by_id[r["scientific_identity"]]["T"].encode()
                ),
                status="TEXT_LINKAGE_PARTIAL",
                canonical_message_commit_linkage=False,
                source_digest=RAW_HASH,
            )
            for r in train
        ],
        "text_message_to_vector_linkage.jsonl": texts,
        "q1_canonical_linkage_sufficiency.json": {
            m: dict(
                status="Q1_CANONICAL_LINKAGE_PARTIAL",
                complete_projects=0,
                publication_ready=False,
                critical_missing=["commit", "source_row", "complete_population"],
                dimensions={
                    x: "PRESERVED_BOUNDARY"
                    if x
                    in [
                        "reconstruction_transparency",
                        "no_T2_access",
                        "limitation_disclosure",
                    ]
                    else "INCOMPLETE_CANONICAL_CHAIN"
                    for x in [
                        "row_traceability",
                        "source_traceability",
                        "transformation_traceability",
                        "representation_traceability",
                        "feature_order",
                        "model_identity",
                        "partition_integrity",
                        "reconstruction_transparency",
                        "no_target_leakage",
                        "no_T2_access",
                        "reproducibility",
                        "cryptographic_evidence",
                        "manuscript_traceability",
                        "limitation_disclosure",
                    ]
                },
            )
            for m in b.MODALITIES.values()
        },
        "remaining_blockers.json": dict(
            items=[
                "Canonical row digest → full project/commit mapping unavailable",
                "Canonical source rows/offsets occur in mixed labelled provenance streams; opening is prohibited",
                "Complete TRAIN and permitted T1 identity source not established",
                "PROCESS ancestor-only source semantics remain insufficiently proven",
                "TEXT raw message origin at exact commit remains unproven despite exact transform metadata",
                "Partial derivative row digests do not establish canonical completeness",
            ]
        ),
        "future_revalidation_policy.json": dict(
            SPRINT56_3B_REVALIDATION_ELIGIBILITY="BLOCKED",
            eligible_scope_ids=[],
            authorized=False,
            started=False,
            T1_feature_reader_activated=False,
        ),
        "recommended_next_action.json": dict(
            action="Resolve canonical identity bridge under a separate evidence/access decision",
            required_artifact=[
                "project",
                "partition",
                "frozen_row_identifier",
                "full_commit_sha",
                "canonical_repository",
                "source_digest",
                "independently_proven_safe_source_offset",
            ],
            forbid="No mixed-stream scan, SHA guessing, message matching or new fitting",
            if_unavailable="Record unresolved; any broader access or changed scientific design requires separate amendment",
        ),
    }
    for mod in b.MODALITIES.values():
        files[mod.lower() + "_canonical_linkage.jsonl"] = [
            dict(
                r,
                modality_linkage_status=(
                    "TEXT_LINKAGE_PARTIAL"
                    if r["partial_train_rows"]
                    else "TEXT_E1_INELIGIBLE"
                )
                if mod == "TEXT"
                else mod
                + (
                    "_LINKAGE_PARTIAL"
                    if r["partial_train_rows"]
                    else "_LINKAGE_UNRESOLVED"
                ),
            )
            for r in ledgers
            if r["modality"] == mod
        ]
    e.reads.update(e.matrices.reads)
    inv = r1.inventory(paths, prior, e.reads)
    files["canonical_linkage_source_inventory.jsonl"] = [
        dict(
            path=x["path"],
            origin_sprint=x["origin_sprint"],
            artifact_family=x["artifact_type"],
            project=x["project"],
            partition=x["partition"],
            modality=x["modality"],
            row_count=x["rows"],
            identity_fields=x["identity_status"],
            commit_fields="NOT_ESTABLISHED_FOR_CANONICAL_POPULATION",
            schema_fields=x["feature_status"],
            ordering_fields="EXPLICIT_WHERE_REGISTERED_ONLY",
            digest_fields=x["source_digest"],
            provenance_strength=x["provenance_strength"],
            linkage_usefulness=x["scientific_reusability"],
            reason=x["blocking_reason"],
        )
        for x in inv
    ]
    files["identity_producer_analysis.json"] = dict(
        source="src/dataset/apachejit_final_dataset_freeze.py",
        source_sha256=e.reads["src/dataset/apachejit_final_dataset_freeze.py"],
        evidence_lines="778-807",
        row_id_recipe="SHA256 apachejit-v2|project|repository|commit_id",
        canonical_fields=[
            "commit_sha",
            "canonical_repository_identifier",
            "source_apachejit_row_identity",
        ],
        label_in_same_record=True,
        mixed_provenance_payload_opened=False,
        conclusion="Producer proves field semantics; it does not provide an admissible inverse index",
    )
    files["read_access_ledger.json"] = dict(
        reads=e.reads,
        scientific_payloads=[RAW, *sorted(e.matrices.partial)],
        payload_scope="80 admitted TRAIN identities only; no T1/T2 scientific rows",
    )
    counters = dict.fromkeys(b.ZERO, 0)
    counters.update(
        TRAIN_METADATA_ACCESS_COUNT=len(e.reads) - len(e.matrices.partial) - 1,
        TRAIN_IDENTITY_ACCESS_COUNT=80,
        TRAIN_SOURCE_VALUE_READ_COUNT=80,
        TRAIN_ACCESS_UNIT="Unique admitted TRAIN identities, not repeated across families/tests",
        TRAIN_REPRESENTATION_FILE_READ_COUNT=len(e.matrices.partial),
        TRAIN_RAW_SOURCE_FILE_READ_COUNT=1,
        T1_METADATA_ACCESS_COUNT=len(e.reads) - len(e.matrices.partial) - 1,
        METADATA_COUNT_UNIT="Conservative unique verified metadata files; overlapping TRAIN/T1 categories, not additive",
        T2_STATE="DENY_SEALED_REVIEWER_RESERVE",
        historical_T1_predictive_access_count=1,
        historical_T1_predictive_scoring_count=1,
    )
    files["governance_counters.json"] = counters
    return files


def report(f, flight):
    topics = [
        (
            "Objective",
            "Determine canonical row-to-source-to-representation linkage without executing E1.",
        ),
        (
            "Branch / HEAD",
            flight["branch"]
            + " / "
            + flight["head"]
            + ". Prior untracked B/R1 files classified as immutable parent work.",
        ),
        (
            "Parent R1 state",
            "R1 blocked population access; 168 reconstructed dependencies; 56 exact TEXT transform metadata bindings retained.",
        ),
        (
            "Scientific linkage problem",
            "Internal row identities and exact transform metadata do not prove canonical commit/source identity.",
        ),
        (
            "Source inventory",
            "Repository-wide path discovery repeated. Frozen producer code places commit and CSV row pointers with labels in mixed provenance records; no such stream opened.",
        ),
        (
            "Identity normalization",
            "Exact (project,frozen row SHA256) preserved with limitation. No authoritative full commit SHA in admitted derivatives; no heuristic matching or hash inversion.",
        ),
        (
            "TRAIN identity linkage",
            "80 unique internal activemq identities out of 56,821 expected TRAIN rows. Zero canonical commit/source links. Other 13 projects unresolved.",
        ),
        (
            "T1 identity linkage",
            "No permitted individual identity rows available. Empty registry, no invented placeholders; T1_IDENTITY_LINKAGE_UNRESOLVED.",
        ),
        (
            "CODE linkage",
            "4 partial scopes / 52 unresolved; frozen la,ld,nf,nd,ns,ent. Derivative row provenance is not canonical completeness.",
        ),
        (
            "PROCESS linkage",
            "4 partial scopes / 52 unresolved; ndev,age,nuc,aexp,arexp,asexp. Exact prediction-time aggregation remains unresolved.",
        ),
        (
            "TEXT raw-message linkage",
            "80 message byte digests tied to exact internal TRAIN identities, not to authoritative commit SHA. No message-similarity matching.",
        ),
        (
            "TEXT vector linkage",
            "320 internal message/vector pairings across 4 families. No transformation rerun; 56 frozen transform metadata bindings inherited. Full TEXT E1 remains ineligible.",
        ),
        (
            "Representation row identity",
            "960 row/scope entries prove matrix index → exact persisted internal identity for 12 partial scopes; canonical commit linkage remains missing.",
        ),
        (
            "Representation column identity",
            "168 metadata registries bind exact feature order and schema; only 12 have inspected partial matrices. No duplicate feature identities.",
        ),
        (
            "Serialization contract",
            "E1R2_ROW_V1 frozen in source before computation; binary float64 little endian, canonical sparse sorted pairs, strict finite values, signed zero preserved.",
        ),
        (
            "Representation digests",
            "960 deterministic SHA256 row/scope digests from five immutable partial TRAIN matrix files; no filesystem timestamps or output values involved.",
        ),
        (
            "Representation completeness",
            "Zero canonical complete scopes. One project × 3 modalities partial; 13 × 3 unresolved. Partial 80-row sample never treated as complete.",
        ),
        (
            "Partition boundary",
            "Complete TRAIN/T1 intersections unavailable; T2 sealed. No disjointness claim from aggregate counts/digests.",
        ),
        (
            "Representation-to-model linkage",
            "168 persisted metadata bindings retained with limitations; no claim that inaccessible population vectors align; no models loaded.",
        ),
        (
            "Reconstructed-state boundary",
            "Predictors remain RECONSTRUCTED; existing derived matrices labeled RECONSTRUCTED_REPRESENTATION. No original-matrix recovery claim.",
        ),
        (
            "Provenance strength",
            "Commit/source-row P0 prevents canonical completion even where column/value/model metadata are P4.",
        ),
        (
            "Q1 sufficiency",
            "Q1_CANONICAL_LINKAGE_PARTIAL for each modality; zero primary E1 publication-ready populations.",
        ),
        (
            "Coverage",
            "Universe fixed at 168: 12 partial, 156 unresolved, zero exact/limited-complete/fail; every family has 3 partial and 39 unresolved scopes.",
        ),
        (
            "Governance",
            "TRAIN-only raw/partial matrices read; T1 identity/features/labels/model queries and all T2/model/XAI/training/metric/figure counters zero. Historical T1 1/1. Safe regression results and exceptions recorded.",
        ),
        (
            "Revalidation readiness",
            "BLOCKED; T1 feature access not ready or activated; no eligibility revalidation launched.",
        ),
        (
            "Final recommendation",
            "Obtain independently verifiable frozen row/project/commit and safe source-location evidence. Without it, keep blocked; do not broaden access or substitute data implicitly.",
        ),
    ]
    return (
        "# Sprint 56.3B-R2 canonical linkage\n\n"
        + VERDICT
        + "\n\n"
        + "\n\n".join(
            f"## {chr(65 + i)}. {name}\n\n{text}"
            for i, (name, text) in enumerate(topics)
        )
        + "\n"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--validation", type=Path, required=True)
    args = parser.parse_args()
    r1.branch_gate(b.git("rev-parse", "--abbrev-ref", "HEAD"))
    flight = json.loads(args.preflight.read_text())
    if flight["head"] != b.git("rev-parse", "HEAD"):
        raise ValueError("HEAD changed")
    for p, h in flight["parent_hashes"].items():
        if sha((ROOT / p).read_bytes()) != h:
            raise ValueError("Parent changed")
    e = Evidence().load()
    paths = sorted(
        set(r1.discover())
        | {str(p.relative_to(ROOT)) for p in (ROOT / r1.OUT).iterdir()}
    )
    paths = [
        p for p in paths if not p.startswith(OUT + "/") and p not in {SOURCE, TEST}
    ]
    f = build(e, paths)
    f["preflight.json"] = flight
    f["validation_results.json"] = json.loads(args.validation.read_text())
    regression_metadata = sorted(e.reader.transform_refs)
    f["governance_counters.json"].update(
        REGRESSION_TRANSFORM_METADATA_FILE_READ_COUNT=len(regression_metadata),
        regression_access_scope="R1 tests reread these 14 exact JSON transforms; B tests reread same 5 admitted TRAIN matrices",
        scientific_counter_scope="Resolver plus safe regressions; synthetic fixture values excluded",
    )
    f["read_access_ledger.json"]["regression_transform_metadata_paths"] = (
        regression_metadata
    )
    f["SPRINT56_3B_R2_CANONICAL_LINKAGE_REPORT.md"] = report(f, flight)
    f["implementation_provenance.json"] = {
        p: sha((ROOT / p).read_bytes()) for p in [SOURCE, TEST]
    }
    if any(sha((ROOT / p).read_bytes()) != h for p, h in e.reads.items()):
        raise ValueError("Consumed bytes changed")
    if b.git("diff", "--name-only") or b.git("diff", "--cached", "--name-only"):
        raise ValueError("Tracked mutation or staging")
    f["historical_immutability_verification.json"] = dict(
        status="PASS",
        parent_hashes=flight["parent_hashes"],
        tracked_changes=[],
        staged_changes=[],
    )
    out = ROOT / OUT
    out.mkdir(parents=True, exist_ok=False)
    for n, raw in b.serialize(f).items():
        (out / n).write_bytes(raw)
    print(json.dumps(f["protocol_summary.json"], sort_keys=True))


if __name__ == "__main__":
    main()
