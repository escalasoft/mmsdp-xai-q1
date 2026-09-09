# ruff: noqa: E501
"""56.3B-R1 provenance resolution: metadata only, no scientific execution.

Verified transform JSON is inspected as data, never deserialized as a fitted
estimator. Discovery lists paths; it never opens an unknown scientific source.
The T1 contract is a proposal and cannot authorize a read in this implementation.
"""

from __future__ import annotations

import argparse
import json
import math
import struct
import subprocess
from collections import Counter
from pathlib import Path

from src.evaluation import q1_e1_input_provenance_eligibility as parent

ROOT = parent.ROOT
OUT = "audits/q1-e1-population-representation-provenance-resolution/1.0.0"
PARENT = parent.OUT
SAFE = "audits/q1-primary-xai-safe-population-source/1.0.0"
STORE = "audits/q1-xai-reconstruction-execution/1.0.0"
FREEZE = "audits/q1-heldout-governance-calibration-freeze/1.0.0"
BOUNDARY = "audits/q1-primary-xai-t2-semantic-boundary-amendment/1.0.0"
VERDICT = "56_3B_R1_BLOCKED_POPULATION_ACCESS_PATH_NOT_ESTABLISHED"
SOURCE = "src/evaluation/q1_e1_population_representation_provenance_resolution.py"
TEST = "tests/evaluation/test_q1_e1_population_representation_provenance_resolution.py"
META = {
    SAFE: [
        "reconciliation_spec.json",
        "source_candidate_ledger.jsonl",
        "train_membership_registry.json",
        "t1_membership_registry.json",
        "source_discovery.json",
        "feature_schema.json",
    ],
    parent.POP: ["text_representation_registry.json", "feature_order_registry.json"],
    parent.MAT: ["e1_row_identity_registry.jsonl"],
    FREEZE: ["t1_identity_integrity.json", "frozen_feature_contract.json"],
    BOUNDARY: ["frozen_partition_function_spec.json"],
    "audits/q1-temporal-robustness-cv/1.0.0": ["temporal_membership_provenance.json"],
    "audits/q1-controlled-train-validation-baselines/1.0.0/campaign": [
        "xai_readiness.json",
        "reproducibility_manifest.json",
    ],
    "audits/q1-development-only-calibration/1.0.0": [
        "calibration_execution_contract.json",
        "input_probability_provenance.json",
    ],
    f"{STORE}/external_artifact_registry": ["external_artifact_summary.json"],
}
CODE_REFS = [
    "src/evaluation/q1_primary_xai_safe_population_source.py",
    "src/evaluation/q1_primary_xai_population_freeze.py",
    "src/evaluation/q1_primary_xai_e1_scientific_input_materialization.py",
    "src/experimentation/q1_controlled_result_campaign.py",
    "src/experimentation/q1_sprint50_large_artifact_packaging.py",
]
sha, encode = parent.sha, parent.encode


def canonical(value):
    return (
        json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode()


def branch_gate(branch):
    if branch != parent.BRANCH:
        raise ValueError("Wrong branch: STOP before reads")


class Reader:
    def __init__(self, root=ROOT):
        self.root = Path(root).resolve()
        self.reads = {}
        self.transform_refs = {}
        self.docs = {}
        self.allowed = {f"{ns}/{n}" for ns, names in META.items() for n in names}
        self.allowed |= {f"{ns}/MANIFEST.sha256" for ns in META}
        self.allowed |= {f"{PARENT}/MANIFEST.sha256", *CODE_REFS}

    def exact_read(self, relative):
        if relative not in self.allowed:
            raise PermissionError("Unknown payload path denied before open")
        path = self.root / relative
        if path.resolve() != path or not path.is_file():
            raise ValueError("Missing or symlink-routed evidence")
        raw = path.read_bytes()
        self.reads[relative] = sha(raw)
        return raw

    def package(self, namespace, names=None):
        if namespace not in {*META, PARENT}:
            raise PermissionError("Unapproved package")
        raw = self.exact_read(f"{namespace}/MANIFEST.sha256")
        if (
            namespace == PARENT
            and sha(raw)
            != "55433729f28c86d442c97af0cecffa46deaef055cb5543ccf089bc613a613e86"
        ):
            raise ValueError("Parent 56.3B immutable manifest differs")
        entries = {}
        for line in raw.decode().splitlines():
            digest, name = line.split("  ", 1)
            if name in entries or len(digest) != 64:
                raise ValueError("Ambiguous manifest")
            entries[name] = digest
        if names is None:
            if namespace != PARENT:
                raise PermissionError("Whole package not admitted")
            names = sorted(entries)
            if any(Path(n).name != n for n in names):
                raise ValueError("Parent manifest traversal")
            if set(names) != {
                p.name
                for p in (self.root / namespace).iterdir()
                if p.name != "MANIFEST.sha256"
            }:
                raise ValueError("Parent file-set mismatch")
        elif set(names) - set(META[namespace]):
            raise PermissionError("Unknown metadata")
        self.allowed |= {f"{namespace}/{n}" for n in names}
        for name in names:
            path = f"{namespace}/{name}"
            raw = self.exact_read(path)
            if sha(raw) != entries.get(name, entries.get(path)):
                raise ValueError("Metadata digest mismatch: " + path)
            if name.endswith(".jsonl"):
                self.docs[path] = [json.loads(s) for s in raw.decode().splitlines()]
            elif name.endswith(".json"):
                self.docs[path] = json.loads(raw)
        return self.docs

    def load(self):
        self.package(PARENT)
        verify_parent(self.docs)
        for namespace, names in META.items():
            self.package(namespace, names)
        for rel in CODE_REFS:
            self.exact_read(rel)
        registry = self.docs[f"{parent.POP}/text_representation_registry.json"][
            "states"
        ]
        for record in registry.values():
            ref = record["representation_object"]
            rel = f"{STORE}/{ref['path']}"
            if rel != f"{STORE}/objects/{ref['sha256']}.tfidf.json":
                raise ValueError("Invalid transform object routing")
            self.transform_refs[rel] = ref
            self.allowed.add(rel)
        return self.docs

    def transform(self, relative):
        if relative not in self.transform_refs:
            raise PermissionError("Only manifest-bound TFIDF metadata admitted")
        ref = self.transform_refs[relative]
        raw = self.exact_read(relative)
        if sha(raw) != ref["sha256"] or len(raw) != ref["bytes"]:
            raise ValueError("TFIDF metadata bytes mismatch")
        return json.loads(raw)


def verify_parent(docs):
    summary = docs[f"{PARENT}/protocol_summary.json"]
    rows = docs[f"{PARENT}/e1_scope_eligibility_ledger.jsonl"]
    if summary["verdict"] != parent.BLOCKED or summary["candidate_scopes"] != 168:
        raise ValueError("Parent 56.3B state differs: STOP")
    parent.universe(docs[f"{PARENT}/e1_scope_universe.json"])
    if len(rows) != 168 or len({r["scope_id"] for r in rows}) != 168:
        raise ValueError("Parent ledger mismatch")
    actual = Counter((r["modality"], r["final_scope_eligibility"]) for r in rows)
    expected = {
        ("CODE", "Q1_E1_BLOCKED"): 56,
        ("PROCESS", "Q1_E1_BLOCKED"): 56,
        ("TEXT", "Q1_E1_INELIGIBLE"): 56,
    }
    if (
        actual != expected
        or summary["eligible_projects"]
        or summary["eligible_algorithm_families"]
    ):
        raise ValueError("Material parent eligibility difference")
    for n in [
        "train_background_population_registry",
        "t1_global_foreground_population_registry",
        "local_case_population_registry",
    ]:
        if docs[f"{PARENT}/{n}.jsonl"]:
            raise ValueError("Unexpected admitted parent population")
    counters = docs[f"{PARENT}/governance_counters.json"]
    if any(counters[k] for k in parent.ZERO):
        raise ValueError("Unexpected parent scientific execution")
    if any(
        r["reconstructed_state_status"] != "RECONSTRUCTED_NOT_ORIGINAL_SPRINT54"
        for r in rows
    ):
        raise ValueError("Reconstructed state mislabeled")
    return True


def verify_text(record, transform):
    names, vocab, idf = (
        transform["feature_order"],
        transform["vocabulary"],
        transform["idf"],
    )
    required = {
        "lowercase",
        "token_pattern",
        "ngram_range",
        "min_df",
        "max_features",
        "sublinear_tf",
        "norm",
    }
    checks = dict(
        order=names == record["final_column_order"],
        vocabulary=vocab == {name: i for i, name in enumerate(names)},
        count=len(names)
        == len(set(names))
        == len(vocab)
        == len(idf)
        == record["feature_count"],
        finite=all(type(x) in (float, int) and math.isfinite(x) for x in idf),
        configuration=transform["parameters"] == record["tokenizer_rules"]
        and required <= transform["parameters"].keys(),
        order_hash=sha(canonical(names)) == record["feature_order_sha256"],
        vocabulary_hash=sha(canonical(vocab)) == record["vocabulary_sha256"],
        idf_hash=sha(struct.pack("<" + "d" * len(idf), *idf)) == record["idf_sha256"],
        idf_dtype=record["idf_dtype"] == "<f8",
        historical_alignment=record["predictor_alignment"]
        == "EXACT_CANONICAL_MODEL_DIMENSION_AND_G5_STATE_EVIDENCE",
    )
    if not all(checks.values()):
        raise ValueError("TEXT metadata integrity mismatch")
    return checks


def validate_route(request, bound):
    """Pure pre-read authorization validator on synthetic/approved metadata.

    This verifies binding only; it grants no access and invokes no file reader.
    An adapter would still require a separately authorized immutable byte route.
    """
    if request.get("partition") not in {"TRAIN", "T1"}:
        raise PermissionError("T2/unknown partition denied")
    for field in (
        "partition",
        "project",
        "modality",
        "scope_id",
        "schema",
        "source_digest",
    ):
        if request.get(field) != bound.get(field) or not bound.get(field):
            raise PermissionError("Route binding mismatch: " + field)
    if request.get("identity") not in bound.get("identities", []):
        raise PermissionError("Identity not authorized")
    if bound["modality"] not in {"CODE", "PROCESS", "TEXT"}:
        raise PermissionError("Unknown modality")
    denied = {
        "label",
        "labels",
        "class",
        "target",
        "prediction",
        "probability",
        "score",
        "confidence",
    }
    if set(request.get("fields", [])) & denied:
        raise PermissionError("Label/prediction field denied independently of schema")
    if (
        bound["modality"] in parent.SEMANTICS
        and bound["schema"] != parent.SEMANTICS[bound["modality"]]
    ):
        raise PermissionError("Frozen numeric feature semantics differ")
    allowed = {"row_identifier", "project", "partition", *bound["schema"]}
    if not set(request.get("fields", [])) <= allowed:
        raise PermissionError("Labels/predictions/unknown fields denied")
    if request.get("operation") != "READ_FEATURES":
        raise PermissionError("Model queries and other operations denied")
    if (
        bound.get("identity_partition_proof") is not True
        or bound.get("safe_byte_route") is not True
    ):
        raise PermissionError("No identity-first byte-level route proof")
    return "BINDING_VALID_NOT_AUTHORIZATION"


def t1_payload_read(*args, **kwargs):
    raise PermissionError("T1 feature values not authorized in 56.3B-R1")


def strength_ready(elements):
    required = {
        "row_identity",
        "partition",
        "project",
        "modality",
        "raw_source",
        "transformation",
        "feature_order",
        "final_representation",
        "model_identity",
        "population_membership",
    }
    return required <= elements.keys() and all(
        elements[k] in {"P3", "P4"} for k in required
    )


def discover(root=ROOT):
    roots = [
        n
        for n in [
            "audits",
            "data",
            "artifacts",
            "outputs",
            "experiments",
            "configs",
            "src",
            "tests",
        ]
        if (root / n).exists()
    ]
    command = [
        "rg",
        "--files",
        "--hidden",
        "--no-ignore",
        *roots,
        "-g",
        "!**/.git/**",
        "-g",
        "!**/__pycache__/**",
        "-g",
        "!**/objects/**",
    ]
    paths = subprocess.check_output(command, cwd=root, text=True).splitlines()
    return sorted(
        p for p in paths if not p.startswith(OUT + "/") and p not in {SOURCE, TEST}
    )


def inventory(paths, docs, reads):
    known = {
        r["path"]: r for r in docs[f"{PARENT}/scientific_input_source_inventory.jsonl"]
    }
    result = []
    for path in sorted(set(paths) | set(reads)):
        k = known.get(path, {})
        # A path is a discovery lead only; classification does not assert its contents.
        result.append(
            dict(
                path=path,
                origin_sprint=k.get("originating_sprint", "UNKNOWN_FROM_PATH_ONLY"),
                artifact_type=k.get(
                    "artifact_family",
                    "METADATA" if path in reads else "UNINSPECTED_DISCOVERY_LEAD",
                ),
                project=k.get("project"),
                partition=k.get("partition", "UNKNOWN_NOT_OPENED"),
                modality=k.get("modality"),
                rows=k.get("rows"),
                columns=k.get("columns"),
                identity_status=k.get("identities", "UNPROVEN"),
                feature_status="NO_COMPLETE_SAFE_SOURCE",
                representation_status=k.get("classification", "UNKNOWN_SOURCE"),
                model_alignment_status="NOT_A_POPULATION_ALIGNMENT_PROOF",
                source_digest=reads.get(path, k.get("sha256")),
                digest_basis="CURRENT" if path in reads else "INHERITED_OR_UNKNOWN",
                provenance_strength="P4" if path in reads else "P0",
                strength_scope="File digest only, not row-level provenance",
                scientific_reusability="EVIDENCE_ONLY"
                if path in reads
                else "NOT_ADMITTED",
                blocking_reason=k.get(
                    "reason",
                    "No independently verified source/partition binding; discovery listing is not authorization",
                ),
            )
        )
    return result


def build(reader, paths):
    d = reader.docs
    scopes = d[f"{PARENT}/e1_scope_universe.json"]
    projects = sorted({r["project"] for r in scopes})
    text_records = d[f"{parent.POP}/text_representation_registry.json"]["states"]
    if len(text_records) != 56:
        raise ValueError("TEXT registry coverage differs")
    tokens = []
    for logical, rec in sorted(text_records.items()):
        ref = rec["representation_object"]
        checks = verify_text(rec, reader.transform(f"{STORE}/{ref['path']}"))
        sid = logical.replace("|FINAL_BASE|", "|")
        scope = next(s for s in scopes if s["scope_id"] == sid)
        dep = next(
            r
            for r in d[f"{PARENT}/reconstructed_state_acceptability.jsonl"]
            if r["scope_id"] == sid
        )
        if (
            rec["project"] != scope["project"]
            or rec["algorithm"] != scope["algorithm_family"]
            or rec["pipeline_object"]
            not in [st["objects"].get("executable") for st in dep["evidence"]["states"]]
        ):
            raise ValueError("TEXT predictor identity linkage mismatch")
        if dep["status"] != "HISTORICALLY_EQUIVALENT":
            raise ValueError("TEXT reconstructed equivalence missing")
        tokens.append(
            dict(
                scope_id=sid,
                project=rec["project"],
                algorithm=rec["algorithm"],
                status="TEXT_ALIGNMENT_EXACT_RECONSTRUCTED",
                scope="TRANSFORM_METADATA_ONLY",
                checks=checks,
                representation_object=ref,
                model_identity=scope["model_identity_sha256"],
                feature_count=rec["feature_count"],
                feature_order_sha256=rec["feature_order_sha256"],
                vocabulary_sha256=rec["vocabulary_sha256"],
                idf_sha256=rec["idf_sha256"],
                tokenizer_rules=rec["tokenizer_rules"],
                raw_message_identity_chain="UNPROVEN",
                population_sparse_vectors="NOT_AVAILABLE",
                e1_eligibility="TEXT_E1_INELIGIBLE",
            )
        )
    identities = {}
    for r in d[f"{parent.MAT}/e1_row_identity_registry.jsonl"]:
        if r["partition"] != "TRAIN" or not r["no_T1_rows"]:
            raise ValueError("Partial identity metadata is not TRAIN only")
        ids = r["row_ids"]
        if ids and sha(canonical(ids)) != r["row_identity_hash"]:
            raise ValueError("TRAIN identity sequence digest mismatch")
        for ordinal, rid in enumerate(ids):
            identities[(r["project"], rid)] = dict(
                project=r["project"],
                row_identifier=rid,
                partition="TRAIN",
                inherited_partial_ordinal=ordinal,
                commit_identity=None,
                source_byte_offset=None,
                complete_identity_route=False,
                scope="HISTORICAL_PARTIAL_ONLY",
                evidence_ref=f"{parent.MAT}/e1_row_identity_registry.jsonl",
            )
    if len(identities) != 80:
        raise ValueError("Unexpected partial TRAIN evidence")
    resolution = {}
    for mod in ["CODE", "PROCESS", "TEXT"]:
        resolution[mod] = [
            dict(
                project=p,
                modality=mod,
                status=(
                    mod + "_PARTIAL" if p == "apache/activemq" else mod + "_UNRESOLVED"
                ),
                complete_representation_status="REPRESENTATION_UNPROVEN",
                features=parent.SEMANTICS.get(mod, "Per-project learned vocabulary"),
                train_partial_rows=80 if p == "apache/activemq" else 0,
                source_route="COMPLETE_IDENTITY_COMMIT_BRIDGE_UNAVAILABLE",
                ancestor_proof="INHERITED_NOT_INDEPENDENTLY_ESTABLISHED"
                if mod == "PROCESS"
                else "NOT_APPLICABLE",
                transformation="FROZEN_PREPROCESSING_METADATA",
                token_metadata="EXACT_RECONSTRUCTED"
                if mod == "TEXT"
                else "NOT_APPLICABLE",
                no_population_promotion=True,
                evidence_refs=[
                    f"{PARENT}/scientific_input_source_inventory.jsonl",
                    f"{parent.POP}/feature_order_registry.json",
                    f"{SAFE}/reconciliation_spec.json",
                ],
            )
            for p in projects
        ]
    alignment, dependencies, strength = [], [], []
    features = d[f"{parent.POP}/feature_order_registry.json"]["base_predictors"]
    if len(features) != 168:
        raise ValueError("Feature metadata universe incomplete")
    prior_align = {
        r["scope_id"]: r for r in d[f"{PARENT}/input_model_alignment_ledger.jsonl"]
    }
    for s in scopes:
        sid = s["scope_id"]
        a = prior_align[sid]
        prior = next(
            r
            for r in d[f"{PARENT}/reconstructed_state_acceptability.jsonl"]
            if r["scope_id"] == sid
        )
        state = prior["evidence"]
        logical = f"{s['project']}|{s['algorithm_family']}|FINAL_BASE|{s['historical_configuration']}"
        feature = features[logical]
        if (
            sha(canonical(feature["order"])) != feature["order_sha256"]
            or feature["project"] != s["project"]
            or feature["algorithm"] != s["algorithm_family"]
            or not feature["preprocessing_state"]
        ):
            raise ValueError("Feature metadata binding mismatch")
        if (
            s["modality"] in parent.SEMANTICS
            and feature["order"] != parent.SEMANTICS[s["modality"]]
        ):
            raise ValueError("CODE/PROCESS semantic mismatch")
        if feature["executable"] not in [
            st["objects"].get("executable") for st in state["states"]
        ]:
            raise ValueError("Predictor feature metadata digest mismatch")
        refs = [obj for st in state["states"] for obj in st["objects"].values()]
        existence = [
            dict(
                path=f"{STORE}/{obj['path']}",
                exists=(ROOT / STORE / obj["path"]).is_file(),
                expected_sha256=obj["sha256"],
                digest_basis="INHERITED_NOT_MODEL_REHASHED",
            )
            for obj in refs
        ]
        dependencies.append(
            dict(
                scope_id=sid,
                origin="RECONSTRUCTED",
                objects=existence,
                reconstructed_object_exists=all(r["exists"] for r in existence),
                model_identity=s["model_identity_sha256"],
                g4=state["G4"],
                g5=state["G5"],
                runtime_match="HISTORICAL_METADATA_ONLY_NO_NEW_LOAD",
                representation_prerequisites="Complete row/raw/transform/order/matrix alignment required",
                eligible_if_input_chain_passes=prior["status"]
                == "HISTORICALLY_EQUIVALENT"
                and all(r["exists"] for r in existence),
                current_execution_authorized=False,
                equivalence_rerun=False,
            )
        )
        alignment.append(
            dict(
                scope_id=sid,
                status="MODEL_ALIGNMENT_METADATA_UNPROVEN",
                metadata_subchain_status="FROZEN_METADATA_AVAILABLE",
                model_identity=s["model_identity_sha256"],
                historical_metadata=a["historical_metadata"],
                feature_order_sha256=feature["order_sha256"],
                preprocessing=feature["preprocessing_state"],
                metadata_binding="ORDER_PROJECT_FAMILY_EXECUTABLE_DIGEST_VERIFIED",
                token_metadata_exact=s["modality"] == "TEXT",
                full_representation_alignment=False,
                reason="No full population scientific vectors; dimensions alone insufficient",
            )
        )
        elements = dict(
            row_identity="P2",
            partition="P2",
            project="P4",
            modality="P4",
            raw_source="P2",
            transformation="P4" if s["modality"] == "TEXT" else "P3",
            feature_order="P4",
            final_representation="P2" if s["project"] == "apache/activemq" else "P0",
            model_identity="P4",
            population_membership="P2",
        )
        strength.append(
            dict(
                scope_id=sid,
                elements=elements,
                advance=strength_ready(elements),
                evidence_refs=[
                    f"{SAFE}/reconciliation_spec.json",
                    f"{parent.POP}/feature_order_registry.json",
                    f"{PARENT}/input_model_alignment_ledger.jsonl",
                ],
                scoring_scope="Complete scientific population; metadata hash strength is not row evidence",
            )
        )
    authorization = dict(
        status="READY_FOR_SEPARATE_HUMAN_AUTHORIZATION",
        authorized=False,
        applicability="Proposed contract only; operational access remains blocked by unresolved routing",
        current=dict(
            T1_METADATA="ALLOW_AGGREGATE_ONLY",
            T1_IDENTITIES="NOT_READ_IN_R1",
            T1_FEATURE_VALUES="DENY_IN_R1",
            T1_LABELS="DENY",
            T1_PREDICTIONS="DENY_IN_R1",
            T1_MODEL_QUERY="DENY_IN_56_3B_R1",
            T2="DENY",
        ),
        desired_future=dict(
            T1_METADATA="ALLOW",
            T1_IDENTITIES="ALLOW_AFTER_IDENTITY_BOUND_APPROVAL",
            T1_FEATURE_VALUES="CONDITIONALLY_ALLOW_FOR_FROZEN_ELIGIBILITY_AND_XAI",
            T1_LABELS="DENY",
            T1_PREDICTIONS="REUSE_ONLY_IF_FROZEN_AND_ALREADY_AUTHORIZED",
            T1_MODEL_QUERY="DENY_IN_56_3B_R1",
            T2="DENY",
        ),
        projects=projects,
        modalities=["CODE", "PROCESS", "TEXT"],
        candidate_scope_ids=[r["scope_id"] for r in scopes],
        allowed_identity_set=[],
        identity_set_status="UNRESOLVED_NO_WILDCARD",
        required_boundaries=[
            "Identity digest",
            "Project",
            "Modality",
            "Scope/model identity",
            "Exact ordered schema",
            "Immutable source digest and prevalidated byte route",
            "No physical reading of labels or predictions",
            "No mixed-container scan/filter",
            "No T2",
            "Read-only deterministic logged access",
        ],
        not_authorized=[
            "Inference",
            "Metrics",
            "Tuning",
            "Training",
            "Refit",
            "Attribution",
            "Population sampling",
        ],
        log_fields=[
            "access_class",
            "scope_id",
            "project",
            "modality",
            "identity_set_digest",
            "source_digest",
            "schema_digest",
            "rows_read",
            "denial_reason",
        ],
    )
    blockers = [
        "Complete frozen row-id → repository/commit → safe source offset bridge absent",
        "TRAIN/T1 count+digest references do not expose the complete row/commit mapping",
        "Mixed source CSV/gzip cannot be scanned or hashed to repair routing under T2 seal",
        "Exact PROCESS aggregation and per-row prediction-time availability remain incomplete",
        "TEXT transform metadata is exact; raw message identity and full sparse population are not",
        "T1 feature-value authorization contract is proposed, not activated",
    ]
    files = dict()
    files["protocol_summary.json"] = dict(
        verdict=VERDICT,
        candidate_scopes=168,
        parent_verified=True,
        complete_train_route=False,
        exact_text_transform_metadata_scopes=len(tokens),
        scientific_population_paths_established=0,
        no_revalidation_started=True,
    )
    files["parent_56_3b_verification.json"] = dict(
        verified=True,
        summary=d[f"{PARENT}/protocol_summary.json"],
        parent_manifest_sha256=reader.reads[f"{PARENT}/MANIFEST.sha256"],
        prior_partial_text_scope_count=4,
        expanded_transform_metadata_scope_count=56,
        reconciliation="Additional existing 56.2 transform metadata verified; does not contradict complete-population blockers or rewrite parent",
    )
    files["train_identity_access_path.json"] = dict(
        status="TRAIN_ACCESS_PATH_PARTIAL",
        complete_route=False,
        historical_partial_identities=80,
        complete_commit_lookup_count=0,
        expected=d[f"{SAFE}/reconciliation_spec.json"]["TRAIN"],
        recipe=d[f"{SAFE}/reconciliation_spec.json"]["row_identity_recipe"],
        reason="One-way row digest cannot be inverted; independent exact commit bridge required",
        historical_subset_not_background=True,
    )
    files["train_identity_registry.jsonl"] = list(identities.values())
    for mod in resolution:
        files[mod.lower() + "_representation_resolution.jsonl"] = resolution[mod]
    files["text_token_column_alignment.jsonl"] = tokens
    files["t1_feature_value_access_authorization_contract.json"] = authorization
    files["t1_safe_access_model.json"] = dict(
        status="DESIGN_VALIDATED_NO_PAYLOAD_ADAPTER",
        binding_validator="validate_route(request,bound)",
        payload_reader="ALWAYS_DENY_IN_R1",
        filtering_after_read="FORBIDDEN",
        unknown_fields="DENY",
        authorization_is_separate=True,
    )
    files["t1_access_failure_policy.json"] = dict(
        action="DENY_BEFORE_OPEN",
        failures=[
            "identity unauthorized",
            "project mismatch",
            "modality mismatch",
            "scope mismatch",
            "schema/order mismatch",
            "label or prediction requested",
            "model query requested",
            "T2 or unknown partition",
            "source digest mismatch",
            "identity partition proof absent",
            "safe byte route absent",
        ],
    )
    files["partition_identity_resolution.json"] = dict(
        status="NOT_ESTABLISHED",
        TRAIN_T1="UNPROVEN_COMPLETE_IDENTITIES_UNAVAILABLE",
        TRAIN_T2="UNPROVEN_T2_NOT_READ",
        T1_T2="UNPROVEN_T2_NOT_READ",
        aggregate_ordinal_contract=d[f"{BOUNDARY}/frozen_partition_function_spec.json"],
        t1_aggregate=d[f"{FREEZE}/t1_identity_integrity.json"],
        no_row_disjointness_inferred_from_counts=True,
        t2_identity_payload_read=False,
    )
    files["model_alignment_metadata_resolution.jsonl"] = alignment
    files["reconstructed_state_e1_dependency_ledger.jsonl"] = dependencies
    files["scientific_representation_rematerialization_policy.json"] = dict(
        authorized=False,
        status="CONDITIONAL_POLICY_ONLY_NO_ROUTE",
        label="RECONSTRUCTED_REPRESENTATION",
        original_claim="PROHIBITED_WITHOUT_EXACT_ORIGINAL_PROOF",
        requirements=[
            "Frozen source and transformation digests",
            "Exact historical versions",
            "Exact row and column order",
            "Frozen fitted preprocessing only",
            "No source substitution",
            "No T1 labels",
            "No T2",
            "No fitting on T1",
            "No tuning or outcome selection",
            "Immediate SHA256 persistence",
            "Row-order and column-order registries",
            "Provenance manifest",
        ],
        background_summary_policy_change="NOT_AUTHORIZED",
        seed=20260901,
        background_cap=256,
        background_sampling_executed=False,
    )
    files["representation_integrity_readiness.jsonl"] = [
        dict(
            r,
            status="HISTORICAL_PARTIAL_RESULT_NOT_REEXECUTED"
            if r["status"] == "PASS_PARTIAL_TRAIN_ONLY"
            else "UNOBSERVED",
            current_matrix_payload_read=False,
            evidence_scope="R1 resolver; parent regression rechecks documented in validation_results.json",
        )
        for r in d[f"{PARENT}/feature_value_integrity.jsonl"]
    ]
    files["provenance_strength_ledger.jsonl"] = strength
    files["q1_provenance_path_summary.json"] = {
        m: dict(
            status="Q1_PROVENANCE_PATH_PARTIAL",
            complete_path_projects=0,
            primary_e1_ready=False,
            publication_ready=False,
        )
        for m in resolution
    }
    files["remaining_blockers.json"] = dict(
        items=blockers, all_critical_elements_at_least_P3=False
    )
    counters = dict.fromkeys(parent.ZERO, 0)
    counters.update(
        T1_METADATA_ACCESS_COUNT=len(reader.reads) - len(reader.transform_refs),
        T1_METADATA_ACCESS_UNIT="Conservative unique governance metadata files; includes non-T1 metadata",
        TRAIN_IDENTITY_ROW_READ_COUNT=80,
        TRANSFORM_METADATA_FILE_READ_COUNT=len(reader.transform_refs),
        T1_PREDICTION_ACCESS_COUNT=0,
        TRAIN_FEATURE_VALUE_ACCESS_COUNT=0,
        historical_T1_predictive_access_count=1,
        historical_T1_predictive_scoring_count=1,
        T2_STATE="DENY_SEALED_REVIEWER_RESERVE",
    )
    files["governance_counters.json"] = counters
    files["future_revalidation_policy.json"] = dict(
        SPRINT56_3B_REVALIDATION_ELIGIBILITY="BLOCKED",
        authorized=False,
        started=False,
        next_sprint="56.3B-R2 only after resolved routing and separate human authorization",
    )
    files["recommended_next_action.json"] = dict(
        action="Obtain or independently establish a permitted immutable population routing artifact",
        exact_required_fields=[
            "project",
            "partition",
            "row_identifier",
            "canonical_repository",
            "commit_sha",
            "frozen_source_digest",
            "safe_record_offset_or_separate_partition_file",
            "ordered_feature_schema_digest",
        ],
        verification="Reconcile full ordered TRAIN/T1 membership digests without touching T2 or T1 labels",
        no_feasible_current_generation_route=True,
        alternatives="If no such artifact exists, require a separate governance/design amendment; no scan-and-filter workaround",
    )
    files["population_and_representation_source_inventory.jsonl"] = inventory(
        paths, d, reader.reads
    )
    files["source_discovery.json"] = dict(
        roots_count=dict(Counter(p.split("/")[0] for p in paths)),
        listed_file_count=len(paths),
        path_list_digest=sha(canonical(paths)),
        random_access_extension_candidates=[
            p
            for p in paths
            if p.endswith(
                (
                    ".parquet",
                    ".npz",
                    ".npy",
                    ".arrow",
                    ".feather",
                    ".sqlite",
                    ".gzi",
                    ".idx",
                )
            )
        ],
        excluded="Git internal objects, __pycache__, opaque model object directories; exact named transform objects inspected separately",
        historical_discovery_ref=f"{SAFE}/source_discovery.json",
        limits="Repository plus ignored artifacts; no external copies asserted absent; uninspected paths remain unknown",
        development_findings=[
            "Sprint49 xai_readiness specifies deterministic reconstruction, not persisted original matrices",
            "Sprint50 membership provenance contains fold counts/digests, not a commit bridge",
            "Sprint51 calibration consumes probability provenance, not scientific feature vectors",
            "Sprint52 T1 identity integrity supplies aggregate count/digest and a mixed manifest pointer",
            "Sprint55/56.2 contains exact transform metadata but no complete safely routed raw population",
        ],
    )
    files["read_access_ledger.json"] = dict(
        reads=reader.reads.copy(), no_unknown_payload_open=True
    )
    return files


def report(files, flight):
    labels = [
        "Objective",
        "Branch / HEAD",
        "Parent 56.3B blocker",
        "Remediation scope",
        "Source inventory",
        "TRAIN identity routing",
        "TRAIN representation provenance",
        "CODE resolution",
        "PROCESS resolution",
        "TEXT resolution",
        "Token-column alignment",
        "T1 authorization design",
        "T1 safe access model",
        "Partition identity proof",
        "Model alignment metadata",
        "Reconstructed-state dependencies",
        "Rematerialization policy",
        "Representation integrity readiness",
        "Provenance strength",
        "Q1 sufficiency",
        "Remaining blockers",
        "Governance counters",
        "Tests",
        "Manifest",
        "Revalidation eligibility",
        "Final recommendation",
    ]
    contents = [
        "Resolve existing provenance without changing scientific data or executing explanations.",
        flight["branch"]
        + " / "
        + flight["head"]
        + ". Existing untracked 56.3B package/code/tests inventoried and preserved.",
        "Parent verified: 168 scopes, CODE 56 blocked, PROCESS 56 blocked, TEXT 56 ineligible; no admitted primary population.",
        "Read-only metadata, partial TRAIN identity metadata, exact JSON transform inspection and access contract design. No broad rematerialization.",
        "Repository-wide path discovery including ignored data. Each path classified; unknown payloads unopened. Development 49–52 supplies contracts/counts/digests or predictions, not a verified full row-to-source bridge.",
        "TRAIN_ACCESS_PATH_PARTIAL: 80 historical activemq identities retained. No complete identity-to-commit/offset route. Hash identities cannot be inverted.",
        "Full TRAIN representations UNPROVEN in all 14 projects. Partial matrices from 56.3B are preserved, not promoted.",
        "CODE la, ld, nf, nd, ns, ent retained. One project partial, 13 unresolved; exact supplied benchmark values cannot be replaced by approximate Git metrics.",
        "PROCESS ndev, age, nuc, aexp, arexp, asexp retained. One project partial, 13 unresolved. Exact ancestor-only aggregation/cutoff proof remains incomplete.",
        "TEXT scientific population remains ineligible: raw message identity and full sparse vectors unavailable. Transform metadata is a distinct proven component.",
        "56/56 TEXT transform metadata bindings verified: exact vocabulary, IDF float64 bytes, tokenizer parameters, final feature order and inherited predictor linkage. RECONSTRUCTED, not original. This expands inspected component evidence beyond the 4 partial matrices in 56.3B.",
        "Formal contract READY_FOR_SEPARATE_HUMAN_AUTHORIZATION, not authorized. Empty allowed identity set; operational access blocked until safe route and exact bounds exist.",
        "Pure pre-read binding validator tested; payload reader always denies in R1. Unknown identities, partitions, fields, schema/project/modality mismatches and output requests fail closed.",
        "Disjointness UNPROVEN. Ordinal frozen boundaries and aggregate digests do not establish row-level intersections. No T2 identity payload used.",
        "168 complete representation alignments remain unproven; persisted metadata retained. No model loads or inference.",
        "168 dependency entries retain RECONSTRUCTED origin and G4/G5. Object existence checked using filesystem metadata only; predictor bytes not loaded/rehashed.",
        "Conditional exact frozen transformation policy only. Future derived vectors must be RECONSTRUCTED_REPRESENTATION. No new fitting or source substitution; no background policy change.",
        "No matrix payload inspected by the R1 resolver. Safe 56.3B regressions rechecked 12 partial scope matrices in 5 unique TRAIN files; remaining 156 unobserved. IDF finiteness checked separately.",
        "10 critical elements scored P0–P4 per scope. None advances: missing complete source/population evidence cannot be compensated by a P4 transform hash.",
        "All modalities Q1_PROVENANCE_PATH_PARTIAL with zero complete population paths. Neither publication readiness nor E1 eligibility is claimed.",
        "; ".join(files["remaining_blockers.json"]["items"]),
        "T1 identities/features/labels/predictions/model queries zero; T2 and model/XAI/training/metrics/figures zero. Historical T1 1/1. TRAIN 80 unique partial identities; transform metadata reads separately logged. Parent regressions read 5 admitted partial TRAIN matrix files, counted separately from the resolver.",
        "Focused and safe regression results and exact historical branch/HEAD/diagnostic exceptions are in validation_results.json. No legacy execution tests run.",
        "MANIFEST.sha256 covers every package file except itself; independently verified after publication. Parent byte hashes rechecked before publication.",
        "BLOCKED; 56.3B-R2 not started or authorized.",
        "Obtain a pre-existing independently verifiable TRAIN/T1 identity-to-commit and safe-offset artifact, or separately amend governance if none exists. Do not scan mixed T2 containers. Revalidation awaits resolved evidence and separate authorization.",
    ]
    return (
        "# Sprint 56.3B-R1 provenance resolution\n\n"
        + VERDICT
        + "\n\n"
        + "\n\n".join(
            f"## {chr(65 + i)}. {title}\n\n{text}"
            for i, (title, text) in enumerate(zip(labels, contents, strict=True))
        )
        + "\n"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--validation", type=Path, required=True)
    args = parser.parse_args()
    branch_gate(parent.git("rev-parse", "--abbrev-ref", "HEAD"))
    flight = json.loads(args.preflight.read_text())
    if flight["head"] != parent.git("rev-parse", "HEAD"):
        raise ValueError("HEAD changed")
    for path, h in flight["parent_hashes"].items():
        if sha((ROOT / path).read_bytes()) != h:
            raise ValueError("Parent 56.3B changed")
    reader = Reader()
    reader.load()
    files = build(reader, discover())
    files["preflight.json"] = flight
    files["validation_results.json"] = json.loads(args.validation.read_text())
    regression_paths = files["validation_results.json"]["regression_train_matrix_paths"]
    expected_paths = reader.docs[f"{PARENT}/read_access_ledger.json"][
        "partial_train_paths"
    ]
    if sorted(regression_paths) != sorted(expected_paths):
        raise ValueError("Regression TRAIN read accounting incomplete")
    files["governance_counters.json"].update(
        TRAIN_FEATURE_VALUE_ACCESS_COUNT=len(set(regression_paths)),
        TRAIN_FEATURE_VALUE_ACCESS_UNIT="Unique previously admitted partial TRAIN files read by parent regressions",
        RESOLVER_TRAIN_FEATURE_VALUE_ACCESS_COUNT=0,
        counter_scope="Resolver plus documented safe regressions; synthetic test fixtures excluded",
    )
    files["SPRINT56_3B_R1_POPULATION_REPRESENTATION_PROVENANCE_REPORT.md"] = report(
        files, flight
    )
    if any(sha((ROOT / p).read_bytes()) != h for p, h in reader.reads.items()):
        raise ValueError("Consumed evidence changed")
    if parent.git("diff", "--name-only") or parent.git(
        "diff", "--cached", "--name-only"
    ):
        raise ValueError("Historical tracked changes or staging detected")
    files["historical_immutability_verification.json"] = dict(
        parent_hashes=flight["parent_hashes"],
        consumed_metadata_hashes=reader.reads,
        tracked_changes=[],
        staged_changes=[],
        status="PASS",
    )
    files["implementation_provenance.json"] = {
        p: sha((ROOT / p).read_bytes()) for p in [SOURCE, TEST]
    }
    out = ROOT / OUT
    out.mkdir(parents=True, exist_ok=False)
    for name, raw in parent.serialize(files).items():
        (out / name).write_bytes(raw)
    print(json.dumps(files["protocol_summary.json"], sort_keys=True))


if __name__ == "__main__":
    main()
