# ruff: noqa: E501
"""56.3B: read-only scientific provenance gate; never executes a predictor.

Only manifest-verified governance metadata and explicitly admitted historical
TRAIN partial matrices can be read. Missing proof is not a negative measurement.
This gate cannot repair inputs or authorize future scientific execution.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import subprocess
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = "audits/q1-prospective-e1-protocol-freeze/1.0.0"
R1 = "audits/q1-prospective-e1-parent-integrity-resolution/1.0.0"
R2 = "audits/q1-prospective-e1-protocol-revalidation-r2/1.0.0"
MAT = "audits/q1-primary-xai-e1-scientific-input-materialization/1.0.0"
CAN = "audits/q1-primary-xai-canonical-source-rematerialization-feasibility/1.0.0"
POP = "audits/q1-primary-xai-population-freeze/1.0.0"
OUT = "audits/q1-e1-input-provenance-eligibility/1.0.0"
BRANCH = "sprint-10/q1-e1-input-provenance-eligibility"
MERGE = "0620c76fbcdcd1e602d5d5422b1f8e2c591553d9"
R2_PASS = "R2_PASS_PROTOCOL_FREEZE_WITH_R1_PROVENANCE_LIMITATION"
BLOCKED = "56_3B_BLOCKED_SCIENTIFIC_INPUT_PROVENANCE_INSUFFICIENT"
SEED = 20260901
FAMILIES = ("Logistic Regression", "Random Forest", "XGBoost", "LightGBM")
MODALITIES = {"C": "CODE", "P": "PROCESS", "T": "TEXT"}
SEMANTICS = {
    "CODE": ["la", "ld", "nf", "nd", "ns", "ent"],
    "PROCESS": ["ndev", "age", "nuc", "aexp", "arexp", "asexp"],
}
CONTRACTS = (
    "train_background_policy",
    "t1_global_foreground_policy",
    "local_case_selection_policy",
    "t1_xai_access_policy",
    "code_process_feature_contract",
    "text_e1_contract",
    "fidelity_contract",
    "stability_contract",
    "correlated_feature_policy",
    "e1_e2_continuity_contract",
    "e1_e2_bridge_policy",
    "e1_method_contract",
    "prohibited_claims",
    "scientific_state_preservation",
    "heterogeneity_contract",
    "figure_contract",
)
META = {
    BASE: ["e1_scope_universe.jsonl", *[n + ".json" for n in CONTRACTS]],
    R1: ["protocol_summary.json", "resolution_decision.json"],
    R2: [
        "protocol_summary.json",
        "revalidated_56_3a_contract.json",
        "downstream_56_3b_policy.json",
        "scientific_semantic_integrity.json",
    ],
    MAT: [
        "e1_materialization_ledger.jsonl",
        "e1_feature_schema_registry.jsonl",
        "e1_model_alignment_registry.jsonl",
        "e1_representation_equivalence.jsonl",
        "e1_materialization_source_registry.jsonl",
        "e1_missingness_analysis.json",
    ],
    CAN: [
        "canonical_source_registry.jsonl",
        "canonical_source_routing_safety.jsonl",
        "exact_remaining_blockers.json",
        "text_representation_contract.json",
    ],
    POP: ["model_state_readiness_ledger.jsonl"],
}
ZERO = tuple(
    n + "_COUNT"
    for n in (
        "T1_IDENTITY_ACCESS",
        "T1_FEATURE_VALUE_ACCESS",
        "T1_LABEL_ACCESS",
        "T1_MODEL_QUERY",
        "T2_ACCESS",
        "T2_ROW_READ",
        "T2_IDENTITY_READ",
        "T2_FEATURE_READ",
        "T2_LABEL_READ",
        "T2_MODEL_QUERY",
        "MODEL_QUERY",
        "SHAP_EXECUTION",
        "ANALYTICAL_ATTRIBUTION_EXECUTION",
        "E1_ATTRIBUTION",
        "E1_EXPLAINED_ROW",
        "FIGURE_GENERATION",
        "RETRAIN",
        "REFIT",
        "RECALIBRATION",
        "HYPERPARAMETER_TUNING",
        "MODEL_SELECTION",
        "PREDICTIVE_METRIC_RECOMPUTATION",
        "MODEL_LOAD",
        "COMMIT",
        "PUSH",
        "PR",
    )
)


def encode(obj):
    return (
        json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        + "\n"
    ).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def preflight(branch, parent_pass, ancestry):
    if branch != BRANCH:
        raise ValueError("Wrong branch: STOP")
    if parent_pass != R2_PASS or not ancestry:
        raise ValueError("Parent R2 PASS and merged ancestry required")


class Reader:
    """No paths are admitted by suffix alone or by an arbitrary manifest entry."""

    def __init__(self, root=ROOT):
        self.root = Path(root).resolve()
        self.allowed = {f"{p}/{n}" for p, names in META.items() for n in names}
        self.allowed |= {f"{p}/MANIFEST.sha256" for p in META}
        self.reads = {}
        self.partial = set()
        self.admitted_records = set()

    def read(self, path):
        if path not in self.allowed:
            raise PermissionError("Unapproved scientific payload: " + path)
        target = self.root / path
        if target.resolve() != target or not target.is_file():
            raise ValueError("Missing or symlink-routed evidence: " + path)
        raw = target.read_bytes()
        self.reads[path] = sha(raw)
        return raw

    def load(self):
        docs = {}
        for package, names in META.items():
            entries = {}
            for line in self.read(package + "/MANIFEST.sha256").decode().splitlines():
                digest, name = line.split("  ", 1)
                if name in entries or len(digest) != 64:
                    raise ValueError("Ambiguous parent manifest")
                entries[name] = digest
            for name in names:
                path = f"{package}/{name}"
                raw = self.read(path)
                if sha(raw) != entries.get(name, entries.get(path)):
                    raise ValueError("Parent digest mismatch: " + path)
                docs[path] = (
                    list(map(json.loads, raw.decode().splitlines()))
                    if name.endswith(".jsonl")
                    else json.loads(raw)
                )
        self.admitted_records = {
            sha(encode(r))
            for r in docs[f"{MAT}/e1_materialization_ledger.jsonl"]
            if r["status"] == "PARTIAL_TRAIN_ONLY"
        }
        return docs

    def train_matrix(self, record):
        # The manifest-verified materialization ledger establishes TRAIN-only
        # routing BEFORE payload access. Nothing from T1 or T2 is admitted.
        if (
            record["status"] != "PARTIAL_TRAIN_ONLY"
            or record["project"] != "apache/activemq"
            or record["materialized_t1_rows"] != 0
            or record["materialized_train_rows"] != 80
        ):
            raise PermissionError("No proven historical partial TRAIN admission")
        if sha(encode(record)) not in self.admitted_records:
            raise PermissionError("Record not loaded from verified parent metadata")
        ref = record["matrix"]
        expected = f"{MAT}/{ref['hash']}.matrix.json"
        if ref["path"] != expected:
            raise PermissionError("Unexpected matrix routing")
        self.allowed.add(expected)
        raw = self.read(expected)
        if sha(raw) != ref["hash"]:
            raise ValueError("Partial matrix digest mismatch")
        self.partial.add(expected)
        matrix = json.loads(raw)
        if matrix["partition"] != "TRAIN" or matrix["project"] != record["project"]:
            raise ValueError("Partial TRAIN metadata contradiction")
        return matrix


def key(row):
    return (
        row["project"],
        row.get("algorithm", row.get("algorithm_family")),
        row.get(
            "historical_configuration", row.get("configuration", row.get("modality"))
        ),
    )


def index(rows):
    result = {key(r): r for r in rows}
    if len(result) != len(rows):
        raise ValueError("Duplicate scope")
    return result


def universe(rows):
    projects = sorted({r["project"] for r in rows})
    expected = set(itertools.product(projects, FAMILIES, MODALITIES))
    if len(projects) != 14 or len(rows) != 168 or set(index(rows)) != expected:
        raise ValueError("Frozen unimodal universe mismatch")
    if len({r["scope_id"] for r in rows}) != 168:
        raise ValueError("Duplicate scope identity")
    for r in rows:
        if r["modality"] != MODALITIES[r["historical_configuration"]]:
            raise ValueError("Modality semantics mismatch")
        if r["scope_id"] != "|".join(key(r)):
            raise ValueError("Scope identity mismatch")
    return sorted(rows, key=lambda r: r["scope_id"])


def matrix_integrity(matrix, names):
    x = matrix["X"]
    n, p = x["shape"]
    ids = matrix["row_ids"]
    bad = []
    if matrix["partition"] != "TRAIN":
        raise PermissionError("Only TRAIN integrity inspection permitted")
    if (
        len(ids) != n
        or matrix["feature_names"] != names
        or matrix["feature_order"] != names
        or len(names) != p
    ):
        bad.append("SCHEMA_OR_ORDER_MISMATCH")
    duplicates = len(ids) - len(set(ids))
    dupcols = len(names) - len(set(names))
    if duplicates or dupcols:
        bad.append("DUPLICATE_IDENTITIES_OR_COLUMNS")
    if x["dtype"] != "<f8":
        bad.append("UNEXPECTED_DTYPE")
    if x["format"] == "DENSE":
        if len(x["values"]) != n or any(len(v) != p for v in x["values"]):
            bad.append("DENSE_SHAPE_MISMATCH")
        values = [v for row in x["values"] for v in row]
    elif x["format"] == "CSR":
        values, ix, ptr = x["data"], x["indices"], x["indptr"]
        valid = (
            len(ptr) == n + 1
            and ptr[0] == 0
            and ptr[-1] == len(values) == len(ix)
            and all(type(i) is int and 0 <= i < p for i in ix)
            and all(type(i) is int and 0 <= i <= len(ix) for i in ptr)
            and all(a <= b for a, b in itertools.pairwise(ptr))
        )
        if valid:
            valid = all(len(set(ix[a:b])) == b - a for a, b in itertools.pairwise(ptr))
        if not valid:
            bad.append("MALFORMED_SPARSE_INDICES")
    else:
        values = []
        bad.append("UNKNOWN_MATRIX_FORMAT")
    numeric = all(type(v) in (float, int) for v in values)
    nan = sum(math.isnan(v) for v in values) if numeric else None
    inf = sum(math.isinf(v) for v in values) if numeric else None
    if not numeric or nan or inf:
        bad.append("NONFINITE_OR_NONNUMERIC")
    return {
        "status": "FAIL" if bad else "PASS_PARTIAL_TRAIN_ONLY",
        "n_rows": n,
        "n_columns": p,
        "nan_count": nan,
        "inf_count": inf,
        "duplicate_row_count": duplicates,
        "duplicate_column_count": dupcols,
        "schema_hash": sha(encode({"names": names, "dtype": x["dtype"]})),
        "order_hash": sha(encode(names)),
        "hash_encoding": "encode() canonical JSON",
        "dtype": x["dtype"],
        "format": x["format"],
        "reasons": bad,
    }


def text_alignment(schema):
    """Validate inherited token-column metadata; never infer raw-row provenance."""
    text = schema.get("text")
    if not text:
        return "UNPROVEN"
    names = schema["feature_names"]
    expected = {token: i for i, token in enumerate(names)}
    config = {
        "lowercase",
        "token_pattern",
        "ngram_range",
        "min_df",
        "max_features",
        "sublinear_tf",
        "norm",
        "representation_source",
    }
    exact = (
        text.get("vocabulary") == expected
        and text.get("token_column_mapping") == expected
        and len(text.get("idf", [])) == len(names)
        and all(math.isfinite(v) for v in text["idf"])
        and config <= text.keys()
        and bool(text["representation_source"].get("sha256"))
    )
    return "EXACT_PARTIAL_METADATA_ONLY" if exact else "UNPROVEN"


def eligibility(proof, modality):
    """All A-R scientific dimensions must be explicit; unknown never passes."""
    if proof.get("contamination") is True or proof.get("integrity") == "FAIL":
        return "Q1_E1_INELIGIBLE"
    if modality == "TEXT" and proof.get("token_column_alignment") is not True:
        return "Q1_E1_INELIGIBLE"
    required = (
        "row_identity",
        "feature_order",
        "preprocessing",
        "reconstructed",
        "g4",
        "g5",
        "semantics",
        "no_leakage",
        "partition",
        "population",
        "model_alignment",
        "finite",
        "t1_feature_authorized",
        "fidelity_ready",
        "stability_ready",
        "heterogeneity_ready",
        "local_global_ready",
        "manuscript_traceability",
        "scale",
        "limitations_bounded",
        "no_posthoc",
        "no_t2",
    )
    if not all(proof.get(k) is True for k in required):
        return "Q1_E1_BLOCKED"
    return "Q1_E1_ELIGIBLE"


def select_identities(ids, project, representation, purpose, partition):
    """Frozen identity-only fallback; no outcome arguments or model access."""
    if (purpose, partition) not in {("TRAIN_REFERENCE", "TRAIN"), ("T1_GLOBAL", "T1")}:
        raise PermissionError("Invalid selection partition")
    if len(ids) != len(set(ids)) or any(not isinstance(i, str) or not i for i in ids):
        raise ValueError("Unique exact identities required")

    def order(identity):
        raw = json.dumps(
            dict(
                seed=SEED,
                purpose=purpose,
                project=project,
                representation_identity=representation,
                row_identifier=identity,
            ),
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode()
        return sha(raw), identity

    return sorted(ids, key=order)[:256]


def local_cases(global_ids):
    if len(global_ids) > 256 or len(set(global_ids)) != len(global_ids):
        raise ValueError("Invalid frozen foreground")
    return global_ids[:8]


def disjoint(train, t1):
    if set(train) & set(t1):
        raise ValueError("TRAIN/T1 contamination")
    return True


def coverage(rows):
    result = {}
    for fields in [
        ("modality",),
        ("algorithm",),
        ("project",),
        ("modality", "algorithm"),
        ("algorithm", "project"),
    ]:
        groups = {}
        for r in rows:
            group = "|".join(r[f] for f in fields)
            counts = groups.setdefault(
                group,
                dict(
                    eligible_n=0,
                    eligible_with_limitation_n=0,
                    blocked_n=0,
                    ineligible_n=0,
                ),
            )
            name = {
                "Q1_E1_ELIGIBLE": "eligible_n",
                "Q1_E1_ELIGIBLE_WITH_PREDECLARED_LIMITATION": "eligible_with_limitation_n",
                "Q1_E1_BLOCKED": "blocked_n",
                "Q1_E1_INELIGIBLE": "ineligible_n",
            }
            counts[name[r["final_scope_eligibility"]]] += 1
        result[" × ".join(fields)] = groups
    return result


def compile_gate(docs, reader):
    parent = docs[f"{R2}/protocol_summary.json"]
    if parent["resolution"] != R2_PASS:
        raise ValueError("Parent R2 PASS required")
    checks = docs[f"{R2}/revalidated_56_3a_contract.json"]["contract_checks"]
    if not checks or any(v["status"] != "PASS" for v in checks.values()):
        raise ValueError("R2 contract verification incomplete")
    if docs[f"{R2}/downstream_56_3b_policy.json"][
        "T1_scientific_row_access_authorized"
    ]:
        raise ValueError("Changed T1 governance requires explicit gate amendment")
    scopes = universe(docs[f"{BASE}/e1_scope_universe.jsonl"])
    material = index(docs[f"{MAT}/e1_materialization_ledger.jsonl"])
    schemas = index(docs[f"{MAT}/e1_feature_schema_registry.jsonl"])
    alignments = index(docs[f"{MAT}/e1_model_alignment_registry.jsonl"])
    states = index(docs[f"{POP}/model_state_readiness_ledger.jsonl"])
    ledgers, integrity, reconstructed, aligns, inventory = [], [], [], [], []
    for source in docs[f"{CAN}/canonical_source_registry.jsonl"]:
        inventory.append(
            dict(
                path=source["source_path"],
                artifact_family=source["source_type"],
                originating_sprint=source["creation_stage"],
                project=source["project_coverage"],
                modality=source["modality_coverage"],
                partition="UNRESOLVED_OR_MIXED",
                rows=None,
                columns=None,
                identities=source["row_identity_semantics"],
                feature_names=source.get("scientific_schema"),
                feature_order=None,
                transform_identity=None,
                model_identity=None,
                sha256=source["source_sha256"],
                digest_basis="INHERITED_NOT_PAYLOAD_REHASHED",
                provenance_chain=source,
                persisted_before_t1=source["predates_T1_evaluation"],
                input_values_authoritative=source["canonical_origin_supported"],
                safe_for_e1=False,
                classification=(
                    "PARTIAL_SOURCE"
                    if source["canonical_classification"] == "NONCANONICAL"
                    else "INELIGIBLE_SOURCE"
                ),
                reason=source["reason"],
            )
        )
    for s in scopes:
        k = key(s)
        m, schema, alignment, state = material[k], schemas[k], alignments[k], states[k]
        if not (
            s["model_identity_sha256"]
            == m["model_identity_sha256"]
            == state["model_identity_sha256"]
        ):
            raise ValueError("Model identity contradiction")
        if (
            s["modality"] in SEMANTICS
            and schema["feature_names"] != SEMANTICS[s["modality"]]
        ):
            raise ValueError("CODE/PROCESS semantics changed")
        sid = s["scope_id"]
        row = dict(
            scope_id=sid,
            project=s["project"],
            algorithm=s["algorithm_family"],
            modality=s["modality"],
        )
        measure = dict(
            status="NOT_OBSERVED_NO_ADMITTED_MATRIX",
            n_rows=None,
            n_columns=None,
            nan_count=None,
            inf_count=None,
            duplicate_row_count=None,
            duplicate_column_count=None,
            schema_hash=None,
            order_hash=None,
            matrix_hash=None,
        )
        if m["matrix"]:
            matrix = reader.train_matrix(m)
            measure = matrix_integrity(matrix, schema["feature_names"])
            measure["matrix_hash"] = m["matrix"]["hash"]
            if measure["status"] == "FAIL":
                raise ValueError("Scientific matrix integrity failure: " + sid)
            inventory.append(
                dict(
                    row,
                    path=m["matrix"]["path"],
                    artifact_family="TRAIN_MATRIX",
                    originating_sprint="56.2F",
                    partition="TRAIN",
                    rows=measure["n_rows"],
                    columns=measure["n_columns"],
                    identities="80 inherited TRAIN identities",
                    feature_names=schema["feature_names"],
                    feature_order=schema["feature_names"],
                    transform_identity=alignment["preprocessing"],
                    model_identity=s["model_identity_sha256"],
                    sha256=m["matrix"]["hash"],
                    digest_basis="CURRENT_VERIFIED",
                    provenance_chain=[
                        f"{MAT}/e1_materialization_source_registry.jsonl",
                        f"{MAT}/e1_materialization_ledger.jsonl",
                    ],
                    persisted_before_t1=False,
                    input_values_authoritative="PARTIAL_DERIVATIVE",
                    safe_for_e1=False,
                    classification="PARTIAL_SOURCE",
                    reason="Historical 80-row convenience subset; not frozen prospective population",
                )
            )
        integrity.append(dict(row, **measure))
        token_status = (
            text_alignment(schema) if s["modality"] == "TEXT" else "NOT_APPLICABLE"
        )
        inventory.append(
            dict(
                row,
                path=f"{POP}/model_state_readiness_ledger.jsonl",
                artifact_family="RECONSTRUCTED_MODEL_METADATA",
                originating_sprint="55/56.2",
                partition="FROZEN_TRAIN_FITTED_STATE",
                rows=None,
                columns=(alignment.get("details") or {}).get("n_features_in"),
                identities=None,
                feature_names=schema["feature_names"],
                feature_order=schema["order_status"],
                transform_identity=alignment["preprocessing"],
                model_identity=s["model_identity_sha256"],
                sha256=reader.reads[f"{POP}/model_state_readiness_ledger.jsonl"],
                digest_basis="METADATA_REHASHED_OBJECT_DIGESTS_INHERITED",
                provenance_chain=state["states"],
                persisted_before_t1=False,
                input_values_authoritative=False,
                safe_for_e1=False,
                classification="RECONSTRUCTED_EQUIVALENT_SOURCE"
                if s["equivalence_eligible"]
                else "UNKNOWN_SOURCE",
                reason="Reconstructed equivalent predictor metadata is not a scientific input matrix",
            )
        )
        equivalent = (
            s["equivalence_eligible"] is True
            and state["G4"] == "G4_PASS_ROW_LEVEL_RAW_EQUIVALENCE"
            and state["G5"] == "G5_PASS_FINAL_OUTPUT_EQUIVALENCE"
            and s["state_origin"] == "RECONSTRUCTED_NOT_ORIGINAL_SPRINT54"
            and all(
                x["status"] == "READY_VERIFIED" for x in s["required_state_references"]
            )
        )
        reconstructed.append(
            dict(
                row,
                status="HISTORICALLY_EQUIVALENT" if equivalent else "BLOCKED",
                state_origin=s["state_origin"],
                evidence=state,
                reverified_model_objects=False,
                future_e1_eligible=False,
                reason="Equivalence does not establish input/population provenance",
            )
        )
        aligns.append(
            dict(
                row,
                status="ALIGNMENT_UNPROVEN",
                partial_alignment_status=alignment["status"],
                token_column_alignment_status=token_status,
                historical_metadata=alignment,
                schema_evidence=schema,
                current_integrity=measure["status"],
                reason="Exact whole prospective population-to-model chain unavailable",
            )
        )
        reasons = [
            "T1_FEATURE_ACCESS_NOT_YET_AUTHORIZED",
            "COMPLETE_TRAIN_PROVENANCE_UNRESOLVED",
            "ROW_COMMIT_SAFE_ROUTING_UNPROVEN",
            "POPULATION_NOT_FROZEN",
            "R1_DIAGNOSTIC_PROVENANCE_LIMITATION",
        ]
        if s["modality"] == "TEXT":
            reasons.append("COMPLETE_TOKEN_COLUMN_ROW_MODEL_CHAIN_UNPROVEN")
        if s["modality"] == "PROCESS":
            reasons.append("ANCESTOR_AGGREGATION_PROOF_INCOMPLETE")
        if not equivalent:
            reasons.append("RECONSTRUCTED_EQUIVALENCE_UNPROVEN")
        status = eligibility({"reconstructed": equivalent}, s["modality"])
        ledgers.append(
            dict(
                row,
                model_identity=s["model_identity_sha256"],
                reconstructed_state_status=s["state_origin"],
                source_artifact=m["matrix"],
                partition_provenance="PARTIAL_TRAIN_ONLY; T1 aggregate digest in parent",
                train_input_status=m["status"],
                t1_input_status=reasons[0],
                feature_semantics_status="INHERITED_DEFINITIONS_VALUE_PROOF_INCOMPLETE",
                feature_order_status=schema["order_status"],
                token_column_alignment_status=token_status,
                preprocessing_status="FROZEN_METADATA_AVAILABLE",
                model_alignment_status="ALIGNMENT_UNPROVEN",
                nan_inf_status=measure["status"],
                partition_contamination_status="UNPROVEN_NO_ADMITTED_POPULATION",
                background_population_status="BLOCKED",
                foreground_population_status="BLOCKED",
                local_population_status="BLOCKED",
                fidelity_readiness="BLOCKED_NOT_TESTED",
                stability_readiness="BLOCKED_NOT_TESTED",
                heterogeneity_readiness="BLOCKED",
                figure_readiness="BLOCKED",
                q1_scientific_sufficiency=status,
                final_scope_eligibility=status,
                limitation_codes=reasons,
                blocking_reason="; ".join(reasons),
                evidence_refs=[
                    f"{BASE}/e1_scope_universe.jsonl",
                    f"{MAT}/e1_materialization_ledger.jsonl",
                    f"{MAT}/e1_feature_schema_registry.jsonl",
                    f"{POP}/model_state_readiness_ledger.jsonl",
                    f"{CAN}/exact_remaining_blockers.json",
                    f"{R2}/downstream_56_3b_policy.json",
                ],
            )
        )
    for path, digest in sorted(reader.reads.items()):
        if path in reader.partial:
            continue
        inventory.append(
            dict(
                path=path,
                artifact_family="AUDIT_METADATA",
                originating_sprint="INHERITED_55_56",
                project=None,
                modality=None,
                partition="AGGREGATE_METADATA",
                rows=None,
                columns=None,
                identities=None,
                feature_names=None,
                feature_order=None,
                transform_identity=None,
                model_identity=None,
                sha256=digest,
                digest_basis="CURRENT_VERIFIED",
                provenance_chain=[path],
                persisted_before_t1=False,
                input_values_authoritative=False,
                safe_for_e1=False,
                classification="DERIVED_AUDIT_SOURCE",
                reason="Evidence only; not input values",
            )
        )
    counters = dict.fromkeys(ZERO, 0)
    counters.update(
        T1_METADATA_ACCESS_COUNT=sum(
            1 for p in reader.reads if p not in reader.partial
        ),
        T1_METADATA_ACCESS_UNIT="Unique verified metadata files; conservative, includes TRAIN governance",
        TRAIN_MATRIX_FILE_READ_COUNT=len(reader.partial),
        historical_T1_predictive_access_count=1,
        historical_T1_predictive_scoring_count=1,
        T2_STATE="DENY_SEALED_REVIEWER_RESERVE",
    )
    files = {
        "e1_scope_universe.json": scopes,
        "e1_scope_eligibility_ledger.jsonl": ledgers,
        "scientific_input_source_inventory.jsonl": inventory,
        "input_model_alignment_ledger.jsonl": aligns,
        "feature_value_integrity.jsonl": integrity,
        "reconstructed_state_acceptability.jsonl": reconstructed,
        "coverage_summary.json": coverage(ledgers),
        "governance_counters.json": counters,
        "protocol_summary.json": dict(
            verdict=BLOCKED,
            candidate_scopes=len(scopes),
            eligible_scope_ids=[],
            eligible_projects=[],
            eligible_algorithm_families=[],
            scope_counts=dict(Counter(r["final_scope_eligibility"] for r in ledgers)),
        ),
        "parent_state_verification.json": dict(
            r2=parent,
            immutable_scientific_state=docs[
                f"{BASE}/scientific_state_preservation.json"
            ],
            r1=docs[f"{R1}/resolution_decision.json"],
            parent_reads=reader.reads.copy(),
        ),
        "partition_contamination_audit.json": dict(
            status="UNPROVEN_NO_ADMITTED_POPULATION",
            admitted_population_count=0,
            TRAIN_T1="NOT_TESTED_NO_AUTHORIZED_T1_IDENTITIES",
            TRAIN_T2="NOT_TESTED_T2_SEALED",
            T1_T2="NOT_TESTED_T2_SEALED",
            contamination_detected=False,
            no_contamination_claim_authorized=False,
        ),
        "future_execution_policy.json": dict(
            FUTURE_PRIMARY_E1_EXECUTION_ELIGIBILITY="BLOCKED",
            authorized=False,
            eligible_scope_ids=[],
            later_scope_addition="Separate provenance gate",
            execution_scope="Only exact future frozen eligible ledger; separate human authorization",
        ),
        "recommended_next_action.json": dict(
            action="Separate provenance-routing amendment",
            prerequisites=[
                "Pre-existing immutable TRAIN/T1 identity-to-commit/source-offset bridge",
                "Explicit T1 feature/identity access authorization with T2 exclusion",
                "Complete authoritative numeric inputs and ancestor-only PROCESS proof",
                "Exact TEXT row-token-column-state proof",
                "Rerun eligibility before requesting E1 execution",
            ],
            no_recovery_or_rematerialization_authorized=True,
        ),
        "claim_to_evidence_boundary.json": dict(
            current_allowed=[
                "168 candidate scopes audited; zero admitted for primary E1",
                "E1 explains within-modality feature behavior; E2 explains cross-modality fusion behavior",
                "Historical partial TRAIN representation evidence retained without promotion",
            ],
            conditional_future_claims=[
                "Only provenance-eligible scopes explained, if later executed and verified",
                "Populations selected deterministically before attribution, if later frozen",
            ],
            prohibited=docs[f"{BASE}/prohibited_claims.json"],
            fusion="eta=alpha+sum(beta_m*p_m); phi_m=beta_m*(p_m-mu_m)",
            continuity="Architectural and interpretive; no automatic feature-SHAP propagation",
        ),
        "heterogeneity_readiness.json": dict(
            status="BLOCKED",
            eligible_projects=0,
            eligible_families=0,
            minimum_comparative_families=3,
            text_token_rank_pooling="FORBIDDEN_WITHOUT_COMPARABILITY_PROOF",
        ),
        "figure_readiness_matrix.json": {
            name: dict(status="BLOCKED", reason="No eligible E1 population")
            for name in [
                "CODE_global",
                "PROCESS_global",
                "TEXT_global",
                "local",
                "stability",
                "heterogeneity",
                "E1_E2_continuity",
            ]
        },
    }
    files["figure_readiness_matrix.json"]["E2_modality_contribution"] = dict(
        status="NOT_APPLICABLE",
        reason="Preserved parent E2; not re-audited or generated in this E1 gate",
    )
    for name in (
        "train_background_population_registry",
        "t1_global_foreground_population_registry",
        "local_case_population_registry",
        "t1_foreground_candidate_registry",
        "train_background_candidate_registry",
    ):
        files[name + ".jsonl"] = []
    for modality in MODALITIES.values():
        files[modality.lower() + "_provenance_ledger.jsonl"] = [
            dict(
                r,
                provenance_status=(
                    "TEXT_E1_INELIGIBLE"
                    if modality == "TEXT"
                    else modality + "_PROVENANCE_BLOCKED"
                ),
            )
            for r in ledgers
            if r["modality"] == modality
        ]
    dimensions = [
        "provenance_completeness",
        "row_identity",
        "feature_semantics",
        "preprocessing",
        "model_state",
        "alignment",
        "partitions",
        "population",
        "fidelity",
        "stability",
        "heterogeneity",
        "local_global",
        "manuscript",
        "no_leakage",
        "no_posthoc",
        "no_t2",
        "scale",
        "bounded_limitations",
    ]
    files["q1_scientific_sufficiency_ledger.jsonl"] = [
        dict(
            scope_id=r["scope_id"],
            status=r["final_scope_eligibility"],
            dimensions={
                d: (
                    "PRESERVED_PROTOCOL"
                    if d in ["no_posthoc", "no_t2", "scale"]
                    else "INSUFFICIENT_FOR_PRIMARY_E1"
                )
                for d in dimensions
            },
            evidence_refs=r["evidence_refs"],
        )
        for r in ledgers
    ]
    for name in ("fidelity", "stability", "correlated_feature"):
        files[name + "_readiness.jsonl"] = [
            dict(
                scope_id=r["scope_id"],
                status="BLOCKED",
                computation_executed=False,
                contract_ref=f"{BASE}/"
                + (
                    "correlated_feature_policy"
                    if name == "correlated_feature"
                    else name + "_contract"
                )
                + ".json",
            )
            for r in ledgers
        ]
    files["algorithm_specific_readiness.json"] = {
        a: dict(
            status="BLOCKED",
            model_metadata_available=True,
            exact_population_alignment=False,
            no_new_runtime_load_proof=True,
        )
        for a in FAMILIES
    }
    files["explanation_scale_registry.json"] = dict(
        Logistic_Regression="LOGIT",
        Random_Forest="POSITIVE_CLASS_MODEL_OUTPUT",
        XGBoost="NATIVE_RAW_MARGIN",
        LightGBM="NATIVE_RAW_MARGIN",
        E2="META_LOGIT",
        mixed_scale_quantitative_comparison="PROHIBITED",
    )
    files["frozen_parent_contracts.json"] = {
        n: docs[f"{BASE}/{n}.json"] for n in CONTRACTS
    }
    files["population_selection_policy.json"] = dict(
        seed=SEED,
        background_cap=256,
        foreground_cap=256,
        local_cap=8,
        selection_executed=False,
        identity_fallback="Parent compact sorted-key SHA256; single unlabelled stratum",
        local_fallback="First 8 frozen global keys; subset; no output reuse authorized here",
        policies_changed=False,
        missing_population="Empty registry means no admitted population",
    )
    return files


def serialize(files):
    result = {}
    for name, value in files.items():
        if name.endswith(".jsonl"):
            result[name] = b"".join(
                (
                    json.dumps(r, sort_keys=True, ensure_ascii=False, allow_nan=False)
                    + "\n"
                ).encode()
                for r in value
            )
        elif isinstance(value, str):
            result[name] = value.encode()
        else:
            result[name] = encode(value)
    result["MANIFEST.sha256"] = "".join(
        f"{sha(raw)}  {name}\n" for name, raw in sorted(result.items())
    ).encode()
    return result


def report(files, flight):
    topics = [
        (
            "Objective",
            "Determine provenance and eligibility without scientific execution.",
        ),
        (
            "Branch and HEAD",
            f"{flight['branch']} / {flight['head']}; clean initial tree; merge ancestry verified.",
        ),
        (
            "Parent scientific state",
            "54 closed, MIXED_CONFIRMATORY_EVIDENCE, T1 historical 1/1; 55 RECONSTRUCTED. 56.3A original blocked disposition retained; downstream R2 PASS with R1 diagnostic limitation.",
        ),
        (
            "E1/E2 architecture",
            "E1 explains within-modality features; E2 explains fusion. Architectural and interpretive continuity; no multiplication of E1 SHAP by fusion weights claimed exact.",
        ),
        (
            "Candidate scope universe",
            "168 = 14 projects × 4 families × CODE/PROCESS/TEXT. No pairwise or full multimodal E1.",
        ),
        (
            "Source inventory",
            "Canonical source metadata and per-scope TRAIN matrices inventoried with digest basis. Mixed containers never opened. This is completeness within existing frozen registries, not proof no external copy exists.",
        ),
        (
            "CODE provenance",
            "56 blocked. Exact schema la, ld, nf, nd, ns, ent (entropy alias). Authoritative supplied benchmark values required; Git substitutions unproved.",
        ),
        (
            "PROCESS provenance",
            "56 blocked. ndev, age, nuc, aexp, arexp, asexp retained. Strict-ancestor availability and exact aggregation remain incompletely established; no size features reclassified.",
        ),
        (
            "TEXT provenance",
            "56 ineligible. Exact partial vectorizer metadata is preserved for activemq; full row-message-token-column-model chain remains unproven. No literal token rank pooling.",
        ),
        (
            "Model-input alignment",
            "168 ALIGNMENT_UNPROVEN for prospective populations. Historical structural checks on partial TRAIN matrices do not establish full alignment.",
        ),
        (
            "Reconstructed state acceptability",
            "Per-scope G4/G5 and persisted object identities retained in ledger. No model object loaded or newly hashed. RECONSTRUCTED never ORIGINAL; equivalence alone does not admit inputs.",
        ),
        (
            "TRAIN background eligibility",
            "No population admitted. 80 historical activemq rows are a convenience prefix, not a new representative reference. Frozen cap 256 and seed 20260901 retained.",
        ),
        (
            "T1 foreground eligibility",
            "No population admitted; inherited R2 grants no scientific-row access. T1_FEATURE_ACCESS_NOT_YET_AUTHORIZED. Aggregate metadata only.",
        ),
        (
            "Local case eligibility",
            "No cases admitted. Future local cap 8, subset of global cap 256, ordered identity fallback before attribution.",
        ),
        (
            "Partition integrity",
            "No admitted population; disjointness UNPROVEN, not PASS. No T2 identities read, including boundary metadata. No contamination observed is not proof of absence.",
        ),
        (
            "Feature value integrity",
            "Permitted partial TRAIN matrices checked for finite values, shape, dtype, sparse indices, duplicate IDs/columns and feature order. Unavailable matrices have null measurements, never zero-by-assumption.",
        ),
        (
            "Fidelity readiness",
            "BLOCKED; zero execution. LR residual <=1e-10*(1+abs(eta)); tree <=1e-6*(1+abs(output)); all foreground rows required.",
        ),
        (
            "Stability readiness",
            "BLOCKED; original 20 seeds and fixed population preserved. No resampling or attribution. Requirements retained in frozen_parent_contracts.json.",
        ),
        (
            "Correlated-feature readiness",
            "BLOCKED; TRAIN-only frozen reference unavailable; no correlation computed.",
        ),
        (
            "Heterogeneity readiness",
            "0 eligible projects/families. At least 3 eligible families required for comparative claims. Cross-project explanation claims unsupported.",
        ),
        (
            "Figure readiness",
            "All E1-dependent figures BLOCKED. E2 preserved outside this gate; no figure generated.",
        ),
        (
            "Q1 sufficiency",
            "CODE/PROCESS/TEXT explanations currently unsupported for primary E1. Semantic definitions and preprocessing metadata traceable, complete values/populations not. Global/local/stability publication claims unavailable.",
        ),
        (
            "Coverage",
            "CODE 0/0/56/0; PROCESS 0/0/56/0; TEXT 0/0/0/56 (eligible/limited/blocked/ineligible). Universe unchanged; no favorable subset promotion.",
        ),
        (
            "Governance counters",
            "All scientific execution, model, T1 labels/features/identities, training, metric and T2 counters zero. Metadata and TRAIN matrix reads separately recorded. No commit, push, staging or PR.",
        ),
        (
            "Future execution eligibility",
            "BLOCKED. This gate never grants scientific execution authorization. No eligible IDs.",
        ),
        (
            "Final recommendation",
            "Separate provenance-routing amendment establishing immutable safe TRAIN/T1 identity bridge and explicit T1 access; preserve T2 seal. No raw regeneration or historical recovery rerun here. Re-run eligibility before requesting execution.",
        ),
    ]
    return (
        "# Sprint 56.3B scientific input provenance and eligibility\n\n"
        + BLOCKED
        + "\n\n"
        + "\n\n".join(
            f"## {chr(65 + i)}. {title}\n\n{text}"
            for i, (title, text) in enumerate(topics)
        )
        + "\n"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--validation", type=Path, required=True)
    args = parser.parse_args()
    flight = json.loads(args.preflight.read_text())
    if git("rev-parse", "--abbrev-ref", "HEAD") != BRANCH:
        raise ValueError("Wrong branch: STOP before evidence access")
    reader = Reader()
    docs = reader.load()
    ancestry = (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", MERGE, "HEAD"], cwd=ROOT, check=False
        ).returncode
        == 0
    )
    preflight(
        git("rev-parse", "--abbrev-ref", "HEAD"),
        docs[f"{R2}/protocol_summary.json"]["resolution"],
        ancestry,
    )
    if flight["head"] != git("rev-parse", "HEAD") or flight["initial_status"]:
        raise ValueError("Preflight HEAD or initial clean-tree mismatch")
    allowed_new = {
        "src/evaluation/q1_e1_input_provenance_eligibility.py",
        "tests/evaluation/test_q1_e1_input_provenance_eligibility.py",
    }
    untracked = set(git("ls-files", "--others", "--exclude-standard").splitlines())
    if (
        untracked - allowed_new
        or git("diff", "--name-only")
        or git("diff", "--cached", "--name-only")
    ):
        raise ValueError("Unexpected workspace changes: inventory before publication")
    files = compile_gate(docs, reader)
    files["preflight.json"] = flight
    files["validation_results.json"] = json.loads(args.validation.read_text())
    files["read_access_ledger.json"] = dict(
        reads=reader.reads, partial_train_paths=sorted(reader.partial)
    )
    files["implementation_provenance.json"] = {
        p: sha((ROOT / p).read_bytes())
        for p in [
            "src/evaluation/q1_e1_input_provenance_eligibility.py",
            "tests/evaluation/test_q1_e1_input_provenance_eligibility.py",
        ]
    }
    files["SPRINT56_3B_SCIENTIFIC_INPUT_PROVENANCE_ELIGIBILITY_REPORT.md"] = report(
        files, flight
    )
    # Recheck only the exact admitted reads; never follow scientific manifests.
    if any(sha((ROOT / p).read_bytes()) != h for p, h in reader.reads.items()):
        raise ValueError("Parent bytes changed during gate")
    files["historical_immutability_verification.json"] = dict(
        status="PASS_FOR_ALL_CONSUMED_BYTES",
        checks=reader.reads,
        tracked_changes=git("diff", "--name-only"),
        staged_changes=git("diff", "--cached", "--name-only"),
        payload_scope="No mixed payload or model object read; git evidence covers tracked parents",
    )
    out = ROOT / OUT
    out.mkdir(parents=True, exist_ok=False)
    for name, raw in serialize(files).items():
        (out / name).write_bytes(raw)
    print(json.dumps(files["protocol_summary.json"], sort_keys=True))


if __name__ == "__main__":
    main()
