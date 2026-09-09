# ruff: noqa: E501
"""R3 prospective protocol amendment. Contracts only; no scientific execution.

Historical matrix-byte recovery is closed. Safe source access, exact scientific
semantics and frozen predictor-input compatibility are NOT waived. PASS describes
protocol coherence; it is neither population eligibility nor execution approval.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path, PurePosixPath

from src.evaluation import q1_e1_input_provenance_eligibility as b

ROOT = b.ROOT
OUT = "audits/q1-e1-prospective-reconstructed-representation-protocol/1.0.0"
R1 = "audits/q1-e1-population-representation-provenance-resolution/1.0.0"
R2 = "audits/q1-e1-canonical-identity-representation-linkage/1.0.0"
SOURCE = "src/evaluation/q1_e1_prospective_reconstructed_representation_protocol.py"
TEST = (
    "tests/evaluation/test_q1_e1_prospective_reconstructed_representation_protocol.py"
)
PINS = {
    b.OUT: "55433729f28c86d442c97af0cecffa46deaef055cb5543ccf089bc613a613e86",
    R1: "cee837e4dd4a6d06061710f5e88a37e93f243265c21bce8349efeb62d78ffbec",
    R2: "7c2e8e93e8a34f4ad5438e53f6a6ac5eba9c75b067670202c191579568991dc7",
}
VERDICT = "56_3B_R3_PASS_PROTOCOL_AMENDMENT_WITH_PREDECLARED_LIMITATIONS"
Q1 = "Q1_PROTOCOL_AMENDMENT_DEFENSIBLE_WITH_LIMITATION"
READY = "READY_FOR_SEPARATE_HUMAN_AUTHORIZATION"
CLOSED = "CLOSED_AS_INFEASIBLE_UNDER_AVAILABLE_EVIDENCE"
NAMESPACE = "audits/q1-prospective-reconstructed-e1-representations"
REPRESENTATION = [
    "representation_matrix",
    "row_identity_registry",
    "column_identity_registry",
    "feature_schema",
    "transform_contract",
    "transform_state",
    "matrix_digest",
    "schema_digest",
    "row_order_digest",
    "column_order_digest",
    "source_digest",
    "creation_runtime",
    "provenance_manifest",
]
TEXT_EXTRA = [
    "raw_message_registry",
    "vectorizer_state",
    "vocabulary",
    "idf",
    "token_column_registry",
]
ALL_ARTIFACTS = [
    "dataset_identity",
    "partition_membership",
    "row_identity_order",
    "raw_feature_source_identity",
    "transformed_feature_matrices",
    "column_identity_order",
    "fitted_preprocessing_state",
    "fitted_text_vectorizer_state",
    "vocabulary",
    "idf",
    "model_state",
    "class_order",
    "model_feature_order",
    "fusion_meta_learner_state",
    "calibration_state",
    "runtime_metadata",
    "package_versions",
    "random_seeds",
    "deterministic_thread_configuration",
    "row_level_predictions",
    "explanation_inputs",
    "explanation_outputs",
    "background_population",
    "foreground_population",
    "local_case_population",
    "sha256_provenance_manifests",
]
VALIDATION = [
    "source_provenance",
    "partition_correctness",
    "identity_completeness",
    "feature_schema_correctness",
    "row_order_correctness",
    "column_order_correctness",
    "nan_inf_integrity",
    "deterministic_repeatability",
    "transformation_correctness",
    "model_feature_count_compatibility",
    "model_feature_order_compatibility",
    "provenance_manifest_verification",
]
Q1_DIMENSIONS = [
    "transparent_historical_limitation",
    "no_retroactive_rewriting",
    "immutable_predictive_evidence",
    "reconstruction_labeled",
    "prospective_protocol_freeze",
    "no_test_label_dependence",
    "no_T2_access",
    "deterministic_reconstruction",
    "complete_persistence",
    "row_feature_model_traceability",
    "fidelity_plan",
    "stability_plan",
    "heterogeneity_plan",
    "threats_to_validity",
    "replication_package_readiness",
]
LITERATURE = [
    dict(
        id="ORMENISAN2020",
        title="Time Travel and Provenance for Machine Learning Pipelines",
        authors="Ormenisan et al.",
        year=2020,
        venue="USENIX OpML",
        url="https://www.usenix.org/conference/opml20/presentation/ormenisan",
        supports=[
            "Pipeline processing steps and artifacts",
            "Data versioning/provenance for reproducibility and debugging",
        ],
    ),
    dict(
        id="PINEAU2021",
        title="Improving Reproducibility in Machine Learning Research",
        authors="Pineau et al.",
        year=2021,
        venue="JMLR 22(164):1–20",
        url="https://jmlr.org/papers/v22/20-303.html",
        supports=[
            "Documented code/data and experimental reporting",
            "Reproducibility checklists and robust workflows",
        ],
    ),
    dict(
        id="LUNDBERG2017",
        title="A Unified Approach to Interpreting Model Predictions",
        authors="Lundberg and Lee",
        year=2017,
        venue="NeurIPS 30",
        url="https://proceedings.neurips.cc/paper/2017/hash/8a20a8621978632d76c43dfd28b67767-Abstract.html",
        supports=[
            "Feature attribution for model predictions",
            "Additive explanation methods; not causal proof",
        ],
    ),
    dict(
        id="MLMD",
        title="ML Metadata",
        authors="TensorFlow authors",
        year=None,
        venue="Official technical documentation",
        url="https://www.tensorflow.org/tfx/guide/mlmd",
        supports=["Artifacts, executions, provenance and runtime metadata"],
        evidence_type="Primary documentation, not a journal article",
    ),
]
sha, encode = b.sha, b.encode


class Reader:
    def __init__(self, root=ROOT):
        self.root = Path(root).resolve()
        self.reads = {}
        self.docs = {}
        self.allowed = {f"{p}/MANIFEST.sha256" for p in PINS}
        self.allowed |= {
            "src/evaluation/q1_t1_confirmatory_execution.py",
            "src/experimentation/q1_controlled_result_campaign.py",
        }

    def read(self, path):
        if path not in self.allowed:
            raise PermissionError("Protocol-only read boundary")
        p = self.root / path
        if p.resolve() != p or not p.is_file():
            raise ValueError("Missing/symlink-routed evidence")
        raw = p.read_bytes()
        self.reads[path] = sha(raw)
        return raw

    def load(self):
        for package, pin in PINS.items():
            raw = self.read(package + "/MANIFEST.sha256")
            if sha(raw) != pin:
                raise ValueError("Parent immutable manifest mismatch")
            entries = {}
            for line in raw.decode().splitlines():
                h, n = line.split("  ", 1)
                if (
                    n in entries
                    or PurePosixPath(n).name != n
                    or not re.fullmatch("[0-9a-f]{64}", h)
                ):
                    raise ValueError("Ambiguous/traversing manifest")
                entries[n] = h
            if set(entries) != {
                p.name
                for p in (self.root / package).iterdir()
                if p.name != "MANIFEST.sha256"
            }:
                raise ValueError("Parent file set differs")
            for n, h in entries.items():
                path = f"{package}/{n}"
                self.allowed.add(path)
                raw = self.read(path)
                if sha(raw) != h:
                    raise ValueError("Parent digest mismatch")
                if n.endswith(".jsonl"):
                    self.docs[path] = [json.loads(x) for x in raw.decode().splitlines()]
                elif n.endswith(".json"):
                    self.docs[path] = json.loads(raw)
        self.read("src/evaluation/q1_t1_confirmatory_execution.py")
        self.read("src/experimentation/q1_controlled_result_campaign.py")
        verify_parents(self.docs)
        return self.docs


def branch_gate(branch):
    if branch != b.BRANCH:
        raise ValueError("Wrong branch: STOP")


def verify_parents(d):
    expected = {
        b.OUT: b.BLOCKED,
        R1: "56_3B_R1_BLOCKED_POPULATION_ACCESS_PATH_NOT_ESTABLISHED",
        R2: "56_3B_R2_BLOCKED_CANONICAL_IDENTITY_LINKAGE_INCOMPLETE",
    }
    for package, verdict in expected.items():
        s = d[f"{package}/protocol_summary.json"]
        if s["verdict"] != verdict or s["candidate_scopes"] != 168:
            raise ValueError("Parent material state difference")
        c = d[f"{package}/governance_counters.json"]
        if any(c[k] for k in b.ZERO):
            raise ValueError("Parent scientific counter difference")
        if (
            c["historical_T1_predictive_access_count"] != 1
            or c["historical_T1_predictive_scoring_count"] != 1
        ):
            raise ValueError("Historical predictive counters differ")
        if c["T2_STATE"] != "DENY_SEALED_REVIEWER_RESERVE":
            raise ValueError("T2 boundary differs")
    b.universe(d[f"{b.OUT}/e1_scope_universe.json"])
    if d[f"{R2}/protocol_summary.json"]["canonical_complete_scopes"] != 0:
        raise ValueError("Recovery state differs")
    return True


def validate_destination(path):
    p = PurePosixPath(path)
    if p.is_absolute() or ".." in p.parts or str(p) != path:
        raise PermissionError("Noncanonical destination")
    parts = p.parts
    prefix = PurePosixPath(NAMESPACE).parts
    if parts[: len(prefix)] != prefix or len(parts) < len(prefix) + 2:
        raise PermissionError("Historical or unversioned destination")
    if not re.fullmatch(r"[1-9][0-9]*\.[0-9]+\.[0-9]+", parts[len(prefix)]):
        raise PermissionError("Versioned immutable namespace required")
    return True


def validate_reconstruction_request(request):
    """Validate future preflight, never authorize or reconstruct anything."""
    if request.get("partition") != "TRAIN":
        raise PermissionError("R4 default is TRAIN only")
    if (
        request.get("labels")
        or request.get("t2")
        or request.get("performance_selection")
    ):
        raise PermissionError("Forbidden scientific dependency")
    if request.get("new_fit") or request.get("new_vectorizer"):
        raise PermissionError("New fit needs separate methodological authorization")
    required = [
        "source_digest_verified",
        "safe_identity_route",
        "partition_contract_verified",
        "semantics_verified",
        "frozen_transform_verified",
        "reconstructed_model_equivalence_verified",
    ]
    if not all(request.get(k) is True for k in required):
        raise ValueError("Source/transform admission incomplete")
    validate_destination(request["destination"])
    return "PREFLIGHT_VALID_NOT_EXECUTION_AUTHORIZATION"


def persistence_gate(artifacts, digests, modality):
    """Pure validator of already-persisted byte snapshots; no artifact writer.

    R4 must wire verified on-disk snapshots and immutable publication receipts to
    this validator. Passing this function alone never authorizes XAI execution.
    """
    if modality not in {"CODE", "PROCESS", "TEXT"}:
        raise ValueError("Unknown modality")
    required = set(REPRESENTATION + (TEXT_EXTRA if modality == "TEXT" else []))
    if not required <= artifacts.keys() or set(artifacts) != set(digests):
        raise ValueError("Persistence incomplete: STOP")
    if any(
        not isinstance(raw, bytes) or sha(raw) != digests[name]
        for name, raw in artifacts.items()
    ):
        raise ValueError("Persisted artifact digest mismatch: STOP")
    return "PERSISTENCE_VERIFIED_NOT_XAI_AUTHORIZATION"


def validate_policy(f):
    if (
        f["predictive_xai_evidence_boundary.json"]["SPRINT54_PREDICTIVE_BLOCK"]
        != "CLOSED_IMMUTABLE"
    ):
        raise ValueError("Predictive boundary changed")
    if f["future_execution_policy.json"]["authorized"]:
        raise ValueError("Protocol cannot authorize execution")
    if (
        f["terminology_contract.json"]["predictor_state"] != "RECONSTRUCTED"
        or f["terminology_contract.json"]["representation_state"]
        != "RECONSTRUCTED_REPRESENTATION"
    ):
        raise ValueError("Original/reconstructed conflation")
    if (
        f["historical_recovery_closure.json"][
            "HISTORICAL_EXACT_E1_REPRESENTATION_RECOVERY"
        ]
        != CLOSED
    ):
        raise ValueError("Historical recovery reopened")
    if (
        f["future_ml_xai_artifact_persistence_contract.json"]["required"]
        != ALL_ARTIFACTS
    ):
        raise ValueError("Persistence requirements weakened")
    if (
        f["representation_artifact_package_contract.json"]["required"] != REPRESENTATION
        or f["representation_artifact_package_contract.json"]["TEXT_additional"]
        != TEXT_EXTRA
    ):
        raise ValueError("Representation persistence weakened")
    if f["reconstruction_validation_contract.json"]["checks"] != VALIDATION:
        raise ValueError("Scientific validation weakened")
    if (
        f["persistence_at_creation_contract.json"]["failure"]
        != "STOP_NO_EPHEMERAL_DOWNSTREAM"
    ):
        raise ValueError("Ephemeral downstream bypass")
    return True


def literature_markdown():
    return """# Literature-supported methodological rationale

These sources support general principles; none validates this repository's reconstructed matrices or grants journal acceptance.

ML pipelines transform raw data into features and generate intermediate artifacts. Ormenisan et al. describe capturing processing/artifact provenance and using versioned data for reproducibility and debugging. This motivates retaining source, transformation and representation lineage. [Ormenisan et al., OpML 2020](https://www.usenix.org/conference/opml20/presentation/ormenisan).

Pineau et al. identify reliable reporting and reproducibility as methodological requirements and discuss code submission, reproducibility challenges and checklists. This supports documenting code, data and experimental choices; it does not establish that a missing historical state can be recovered. [Pineau et al., JMLR 2021](https://jmlr.org/papers/v22/20-303.html).

ML Metadata explicitly models artifacts and executions and supports tracing how artifacts were produced. It illustrates why preprocessing, data lineage and environment metadata must accompany model/output artifacts. This is primary engineering documentation, not peer-reviewed evidence for the particular amendment. [TensorFlow ML Metadata](https://www.tensorflow.org/tfx/guide/mlmd).

SHAP assigns feature importance to particular model predictions. Its additive explanation formulation supports post-hoc analysis of documented model inputs, not causal claims or provenance inference. It cannot establish that a reconstructed input equals an unavailable historical matrix. [Lundberg and Lee, NeurIPS 2017](https://proceedings.neurips.cc/paper/2017/hash/8a20a8621978632d76c43dfd28b67767-Abstract.html).

Our methodological inference is conditional: explicit source/transform lineage, deterministic reconstruction, previously supported predictor equivalence and complete persistence can define a transparent new explanatory experiment. Historical preprocessing capture gaps remain limitations. Exact safe input routing and scientific semantics must still pass independent checks. The literature does not demonstrate those checks for MMSDP-XAI, does not declare this exact workflow standard, and does not say that Q1 journals explicitly allow reconstructed feature matrices.

The mandatory A–Z persistence policy is a prospective project decision informed by these principles, not a quotation or universal rule attributed to any single source.
"""


def compile_protocol(d):
    verify_parents(d)
    inherited = d[f"{b.OUT}/frozen_parent_contracts.json"]
    scopes = d[f"{b.OUT}/e1_scope_universe.json"]
    limitations = [
        "SAFE_SOURCE_ACCESS_STILL_UNRESOLVED",
        "COMPLETE_POPULATION_NOT_YET_MATERIALIZED",
        "PROCESS_SOURCE_SEMANTICS_MUST_BE_VERIFIED",
        "POST_HOC_RECONSTRUCTION_PROVENANCE",
        "NO_ORIGINAL_BYTE_EQUIVALENCE_CLAIM",
        "PERSISTENCE_RUNTIME_INTEGRATION_REQUIRED_IN_R4",
    ]
    f = {
        "protocol_summary.json": dict(
            verdict=VERDICT,
            scope_count=168,
            amendment_level="PROTOCOL_ONLY",
            q1_defensibility=Q1,
            currently_admitted_execution_scopes=[],
            limitations=limitations,
        ),
        "parent_r2_verification.json": dict(
            verified=True,
            summary=d[f"{R2}/protocol_summary.json"],
            manifest_sha256=PINS[R2],
            B_R1_R2_historical_dispositions_unchanged=True,
        ),
        "historical_recovery_closure.json": dict(
            HISTORICAL_EXACT_E1_REPRESENTATION_RECOVERY=CLOSED,
            limitation="Artifact persistence/provenance",
            data_corruption_inferred=False,
            predictive_invalidity_inferred=False,
            model_invalidity_inferred=False,
            original_fitted_predictor_objects_persisted=False,
            complete_original_transformed_matrices_persisted=False,
            evidence_scope="Inspected repository producer and preserved audit inventories; no claim about every possible external copy",
            no_further_historical_forensic_dependency=True,
            evidence_refs=[
                f"{R2}/remaining_blockers.json",
                f"{R1}/source_discovery.json",
                "src/evaluation/q1_t1_confirmatory_execution.py",
                "src/experimentation/q1_controlled_result_campaign.py",
            ],
        ),
        "predictive_xai_evidence_boundary.json": dict(
            SPRINT54_PREDICTIVE_BLOCK="CLOSED_IMMUTABLE",
            classification="MIXED_CONFIRMATORY_EVIDENCE",
            historical_T1_predictive_access=1,
            historical_T1_predictive_scoring=1,
            predictive_evidence="Frozen Sprint54 results",
            xai_evidence="Future prospective reconstructed representation layer",
            retroactive_attachment_to_Sprint54=False,
            predictive_metric_recomputation="DENY",
        ),
        "prospective_e1_design.json": dict(
            HISTORICAL_E1="NONPRIMARY_ILLUSTRATIVE_ONLY_WHERE_VALID",
            PROSPECTIVE_RECONSTRUCTED_E1="PRIMARY_COMPLEMENTARY_FEATURE_LEVEL_XAI",
            chain=[
                "frozen benchmark source",
                "frozen partition contract",
                "project/commit identity",
                "frozen modality semantics",
                "frozen transformation contract",
                "prospective reconstructed representation",
                "reconstructed predictor",
                "prior equivalence evidence",
                "future E1",
            ],
            original_matrix_byte_recovery_required=False,
            scientific_identity_and_transform_compatibility_required=True,
            candidate_scope_ids=[s["scope_id"] for s in scopes],
            performance_based_reselection=False,
        ),
        "terminology_contract.json": dict(
            predictor_state="RECONSTRUCTED",
            representation_state="RECONSTRUCTED_REPRESENTATION",
            mandatory=[
                "RECONSTRUCTED predictor",
                "RECONSTRUCTED_REPRESENTATION",
                "PROSPECTIVE_XAI_REPRESENTATION",
                "FROZEN_TRANSFORMATION_CONTRACT",
                "POST_HOC_EXPLANATION",
                "PROSPECTIVE_EXPLANATION_PROTOCOL",
            ],
            prohibited_unless_literally_proven=[
                "ORIGINAL_REPRESENTATION",
                "RECOVERED_ORIGINAL_MATRIX",
                "ORIGINAL_FEATURE_MATRIX",
                "BYTE_IDENTICAL_TO_SPRINT54",
                "ORIGINAL_SPRINT54_XAI_INPUT",
            ],
        ),
        "scientific_rationale.json": dict(
            preserved=[
                "row-level predictions",
                "model identities",
                "hyperparameters",
                "seeds",
                "contracts",
                "runtime metadata",
                "predictive evidence",
            ],
            not_persisted=[
                "complete fitted predictor executable states in original campaign",
                "complete original transformed input matrices",
            ],
            reason_evidence="Producer persists predictive evidence and metadata; no full executable representation export established",
            exact_historical_human_reason="UNKNOWN_NOT_DOCUMENTED",
            scientific_acceptability="Conditional new experiment, not proof of historical matrix equivalence",
            corrected_workflow="Persist source/row/column/transform/model/runtime/output provenance at creation before downstream use",
        ),
        "future_ml_xai_artifact_persistence_contract.json": dict(
            applies_to="ALL_FUTURE_MMSDP_XAI_PREDICTIVE_AND_EXPLANATORY_EXECUTIONS",
            required=ALL_ARTIFACTS,
            completion_gate="No completed campaign with missing required artifacts",
            applicability="For scientifically unused components persist explicit NOT_APPLICABLE plus reason; never fabricate an object",
            phases=dict(
                before_prediction="Input/model/environment artifacts",
                before_XAI="Input/model/population/configuration manifests verified",
                after_XAI="All explanation/figure artifacts",
            ),
            future_predictions_only_campaign="FORBIDDEN",
        ),
        "representation_artifact_package_contract.json": dict(
            unit="project × modality × partition",
            required=REPRESENTATION,
            TEXT_additional=TEXT_EXTRA,
            model_family="Shared representation only if exact frozen transform compatibility; otherwise family-specific child namespace",
            no_ephemeral_only=True,
            persist_immediately=True,
        ),
        "immutable_namespace_contract.json": dict(
            namespace=NAMESPACE + "/<version>/",
            NO_OVERWRITE_HISTORICAL_EVIDENCE=True,
            historical_targets="DENY",
            new_version_for_amendment=True,
            symlink_escape="DENY",
            accepted_version_replacement="DENY",
        ),
        "reconstruction_source_policy.json": dict(
            preference_order=[
                "frozen ApacheJIT benchmark",
                "frozen authoritative partition metadata",
                "frozen feature definitions",
                "frozen transformations",
                "proven reconstructed preprocessing/vectorizer states",
                "source-derived values only under exact frozen semantics",
            ],
            evidence_refs=[
                f"{R1}/population_and_representation_source_inventory.jsonl",
                f"{R2}/identity_producer_analysis.json",
            ],
            source_admission="Require explicit project/commit/partition binding, source digest, and physically safe read route before opening",
            mixed_csv_gzip_scan_filter="NOT_AUTHORIZED",
            T2_byte_access="DENY",
            current_operational_route="UNRESOLVED; amendment does not waive access governance",
            forbidden=[
                "T1 labels",
                "T2",
                "test outcomes",
                "explanations",
                "model errors",
                "post-hoc features",
                "new engineering",
                "performance-guided changes",
            ],
        ),
        "partition_policy.json": dict(
            contract="Historical frozen temporal definitions retained",
            random_resplit="DENY",
            TRAIN="BACKGROUND_REFERENCE",
            T1="FOREGROUND_AFTER_SEPARATE_AUTHORIZATION",
            T2="DENY_SEALED_REVIEWER_RESERVE",
            no_inferred_disjointness=True,
            required="Persist exact full per-project membership and row order; source routing preflight first",
        ),
        "train_reconstruction_policy.json": dict(
            allowed_partition="TRAIN",
            complete_population_required=True,
            source_only=True,
            allowed_operations=[
                "Retrieve legitimate frozen TRAIN inputs",
                "Apply already-fitted frozen transform",
                "Persist representation",
            ],
            no_model_query=True,
            no_new_fit=True,
            prior_admission="Identity/project/partition/source/transform checks must pass before opening",
            forbidden_partitions=["T1", "T2"],
            performance_selection=False,
            partial_80_row_promotion=False,
        ),
        "t1_reconstruction_policy.json": dict(
            authorized=False,
            authorization=READY,
            T1_LABELS_FOR_E1_SELECTION="DENY",
            default_R4_scope="EXCLUDED",
            future_allowed=[
                "identity",
                "raw feature input",
                "deterministic frozen transform",
                "representation persistence",
            ],
            forbidden=[
                "labels",
                "outcome sampling",
                "metrics",
                "model reselection",
                "tuning",
                "T2",
            ],
            activation_requires="Separate scope/identity-bounded human authorization and source admission",
        ),
        "text_reconstruction_policy.json": dict(
            chain=[
                "commit",
                "raw message",
                "normalization",
                "proven fitted/reconstructed vectorizer",
                "vocabulary",
                "IDF",
                "token order",
                "sparse vector",
            ],
            preferred="Exact persisted RECONSTRUCTED vectorizer metadata; 56 inherited bindings",
            new_vectorizer_fit_authorized=False,
            new_vectorizer_fit="Separate methodological change; frozen TRAIN only if explicitly authorized",
            new_T1_fit="DENY",
            new_vectorizer_not_equivalent_by_default=True,
            expected_predictor_alignment="Verify vocabulary, IDF, normalization and column order against exact intended predictor; matching dimensions insufficient",
        ),
        "code_process_semantic_contract.json": dict(
            names=b.SEMANTICS,
            registry=inherited["code_process_feature_contract"],
            CODE="Structural/change commit features",
            PROCESS="Developer/history/strict-ancestor features",
            required_feature_fields=[
                "name",
                "semantic definition",
                "source",
                "prediction-time availability",
                "transformation",
                "ordering",
                "leakage assessment",
            ],
            feature_migration="DENY",
            approximate_Git_substitution="DENY",
            PROCESS_unknown_rule="BLOCK affected scope rather than invent aggregation",
        ),
        "reconstruction_validation_contract.json": dict(
            checks=VALIDATION,
            original_byte_comparison_required=False,
            validation_target="Frozen prospective reconstruction contract and exact intended predictor-input semantics",
            missing_or_failed_check="BLOCK_SCOPE",
            NaN_Inf="Frozen contract only; no new imputation",
            repeatability="Two independent future replays on identical frozen inputs; compare schema/order/values using predeclared serialization",
            serialization=d[
                f"{R2}/canonical_representation_serialization_contract.json"
            ],
        ),
        "model_relationship_contract.json": dict(
            MODEL_STATE="RECONSTRUCTED",
            XAI_REPRESENTATION_STATE="RECONSTRUCTED_REPRESENTATION",
            no_model_retraining_for_XAI=True,
            prior_equivalence_required=["G4", "G5 where applicable"],
            equivalence_not_rerun=True,
            model_identity_fixed=True,
            original_matrix_equivalence_not_claimed=True,
        ),
        "e1_e2_continuity_contract.json": dict(
            E1="Within-modality feature explanation",
            E2="Primary multimodal fusion explanation",
            continuity="ARCHITECTURAL_AND_INTERPRETIVE",
            algebraic_SHAP_propagation="DENY_UNLESS_SEPARATELY_PROVEN",
            inherited=inherited["e1_e2_continuity_contract"],
        ),
        "future_xai_method_contract.json": dict(
            inherited=inherited["e1_method_contract"],
            executed=False,
            approximate=False,
            LIME="EXCLUDED",
            counterfactuals="EXCLUDED",
            fidelity=inherited["fidelity_contract"],
            stability=inherited["stability_contract"],
            heterogeneity=inherited["heterogeneity_contract"],
            correlated_features=inherited["correlated_feature_policy"],
        ),
        "background_foreground_contract.json": dict(
            seed=20260901,
            TRAIN_max=256,
            T1_max=256,
            local_max=8,
            local_subset_of_global=True,
            before_attribution=True,
            label_independent=True,
            kmeans_change="NOT_AUTHORIZED",
            selection_executed=False,
            exact_parent_policies={
                k: inherited[k]
                for k in [
                    "train_background_policy",
                    "t1_global_foreground_policy",
                    "local_case_selection_policy",
                ]
            },
        ),
        "persistence_at_creation_contract.json": dict(
            sequence=[
                "construct",
                "persist matrix",
                "persist row registry",
                "persist column registry",
                "persist transform state",
                "compute SHA256",
                "write manifest",
                "verify manifest",
                "downstream eligibility gate",
            ],
            failure="STOP_NO_EPHEMERAL_DOWNSTREAM",
            downstream_XAI_before_verification=False,
            verification_helper="persistence_gate",
            integration_status="Protocol validator supplied; R4 builder must integrate and test persisted-file/receipt wiring",
        ),
        "atomic_write_immutability_contract.json": dict(
            sequence=[
                "exclusive temporary write in destination filesystem",
                "flush/fsync",
                "validate contents",
                "atomic no-clobber publish",
                "SHA256",
                "manifest registration",
                "manifest verification",
                "accept immutable version",
            ],
            replace_existing=False,
            ordinary_overwriting_rename="FORBIDDEN",
            failure="STOP; retain failure journal; no downstream use",
            amendment="New version only; no mutation of accepted version",
        ),
        "runtime_persistence_contract.json": dict(
            required=[
                "Python",
                "NumPy",
                "SciPy",
                "scikit-learn",
                "XGBoost",
                "LightGBM",
                "SHAP",
                "Numba",
                "joblib",
                "cloudpickle/pickle version/protocol",
                "OS/platform",
                "CPU architecture",
                "thread count",
                "deterministic flags",
                "seeds",
                "requirements lock/freeze",
            ],
            inherited_XAI_lock=inherited["e1_method_contract"]["runtime_lock"],
            silent_runtime_change=False,
        ),
        "future_model_persistence_contract.json": dict(
            required=[
                "LR coefficients/intercept/class order",
                "RF trees",
                "XGB booster",
                "LGB booster",
                "fitted preprocessing",
                "vectorizer",
                "fusion meta-learner",
                "calibrator",
                "executable object SHA256",
            ],
            predictions_only_completion=False,
            original_current_models_recreated=False,
        ),
        "future_xai_persistence_contract.json": dict(
            required=[
                "explainer type/version",
                "configuration",
                "background IDs",
                "foreground IDs",
                "local IDs",
                "base/expected values",
                "SHAP or analytical values",
                "output scale",
                "feature order",
                "model identity",
                "representation identity",
                "fidelity residuals",
                "stability evidence",
                "global aggregation",
                "heterogeneity evidence",
                "figure source tables",
                "rendered figures",
                "figure metadata",
                "manifest",
            ],
            figure_without_source_tables="DENY",
            executed=False,
        ),
        "threats_to_validity.json": dict(
            threat="Post-hoc reconstructed representation provenance",
            limitations=[
                "Original matrices not persisted",
                "Reconstruction follows predictive campaign",
                "Bytes may differ from historical ephemeral state",
                "No predictive reevaluation",
                "Future claims concern the reconstructed explanation pipeline",
                "Source access remains unresolved",
            ],
            mitigations=[
                "frozen source",
                "frozen transformations",
                "deterministic execution",
                "prior predictor equivalence",
                "complete persistence",
                "SHA256 manifests",
                "no T1 labels",
                "no T2",
                "no tuning",
            ],
            future_mitigations_executed=False,
        ),
        "q1_defensibility_assessment.json": dict(
            verdict=Q1,
            dimensions={
                k: dict(
                    status="SPECIFIED_NOT_EMPIRICALLY_EXECUTED",
                    evidence="R3 frozen contracts",
                    limitation="Source admission and prospective validation still required",
                )
                for k in Q1_DIMENSIONS
            },
            scope="Protocol defensibility only; not journal acceptance, reconstruction success or E1 readiness",
            limitations=limitations,
        ),
        "replication_package_contract.json": dict(
            required=[
                "source snapshot identifier",
                "partition registry",
                "representation builder",
                "transformation contracts",
                "reconstructed predictor states",
                "environment lock",
                "population registries",
                "XAI configuration",
                "tests",
                "figures",
                "source tables",
                "manifests",
            ],
            status="BLUEPRINT_FROZEN_NOT_EXECUTION_PACKAGE_READY",
            licensing="Where redistribution restricted, retain lawful retrieval instructions and digests; never infer permission",
        ),
        "prohibited_claims.json": dict(
            claims=[
                "We recovered the original Sprint54 representations",
                "Reconstructed matrices are identical to historical matrices",
                "Original XAI inputs were preserved",
                "SHAP explains the exact historical Sprint54 matrix",
                "SHAP proves causality",
                "All projects share identical drivers",
                "All algorithms use features identically",
            ],
            exceptions="Original-identity claims require literal independent evidence, not this amendment",
        ),
        "future_claims.json": dict(
            status="CONDITIONAL_NOT_CURRENT_FINDINGS",
            claims=[
                "Representations reconstructed prospectively from frozen sources",
                "Predictive results kept immutable",
                "XAI artifacts persisted separately",
                "Populations independent of T1 labels",
                "Row/column/transform/model/runtime/digest provenance retained",
            ],
            required_evidence="Actual successful reconstruction, persistence and relevant execution audit",
        ),
        "future_execution_policy.json": dict(
            PROSPECTIVE_RECONSTRUCTED_REPRESENTATION_EXECUTION=READY,
            authorized=False,
            started=False,
            authorization_meaning="Future controlled TRAIN campaign may be requested; no current source route or population is approved",
            R4_must_stop_before_payload_if_source_admission_fails=True,
            current_admitted_scope_ids=[],
            T1_included=False,
            XAI_authorized=False,
        ),
        "recommended_next_action.json": dict(
            sprint="56.3B-R4 — Prospective TRAIN Representation Reconstruction & Persistence",
            mode="Separate human authorization; source-admission preflight first",
            prerequisites=[
                "Immutable safe TRAIN source route",
                "Project/commit/partition proof",
                "Frozen transformations",
                "Mandatory persistence integration",
            ],
            historical_original_matrix_recovery_required=False,
            T1_default_excluded=True,
            started=False,
        ),
    }
    reviewer_current = (
        "The confirmatory predictive experiment was completed and frozen before the feature-level explainability campaign. "
        "Predictive outputs and experimental metadata were retained, but complete fitted/transformed feature matrices were not persisted as standalone scientific artifacts in the inspected workflow. "
        "The exact historical human reason is not documented. The implementation focused on predictive outputs and experimental evidence; the representation persistence limitation was identified during later XAI audits. "
        "We have now frozen a prospective deterministic reconstruction protocol. No representations have been reconstructed under R3. "
        "Future representations must use admitted frozen inputs and transformations, retain explicit reconstructed labels, and be versioned, hashed and persisted separately. "
        "This amendment changes the provenance protocol for post-hoc explanation inputs; it does not recompute or replace the frozen predictive results."
    )
    slots = dict(
        preserved_outputs="[Sprint54 manifest and row-prediction evidence reference; do not reopen payload here]",
        implementation="src/evaluation/q1_t1_confirmatory_execution.py:1578",
        historical_gaps=f"{R2}/remaining_blockers.json",
        predictor_equivalence="[Per-scope G4/G5 ledger and state digest]",
        future_reconstruction="[Future accepted representation manifest]",
        future_validation="[Future contract-validation results]",
        future_persistence="[Future atomic publication receipts and verified manifests]",
    )
    f["reviewer_artifact_persistence_response.json"] = dict(
        status="CURRENT_PROTOCOL_STATEMENT_WITH_CONDITIONAL_EXECUTION_SLOTS",
        current_response=reviewer_current,
        evidence_slots=slots,
        exact_historical_human_reason="UNKNOWN_NOT_DOCUMENTED",
        historical_design_characterization="Inference from inspected implementation and retained artifacts, not an assertion of human motive",
        future_completed_response="Only after all future evidence slots are verified may “were reconstructed, validated, versioned, hashed and persisted” replace prospective language",
    )
    f["reviewer_artifact_persistence_response.md"] = (
        "# Reviewer response: artifact persistence\n\n"
        + reviewer_current
        + "\n\n"
        + "\n".join(f"- **{k}:** {v}" for k, v in slots.items())
        + "\n\nThe completed reconstruction wording is not currently authorized by the evidence.\n"
    )
    f["manuscript_transparency_contract.json"] = dict(
        current_statement=reviewer_current,
        final_wording=False,
        mandatory_limitation="Original confirmatory feature-representation artifacts were not persisted; future XAI uses separately validated reconstructed representations.",
        tense_gate="Do not claim future artifacts have already been reconstructed or persisted",
        predictive_evidence_unmodified=True,
    )
    f["literature_supported_methodological_rationale.md"] = literature_markdown()
    f["literature_evidence_registry.json"] = dict(
        sources=LITERATURE,
        verification_date="2026-09-08",
        inspected_via="Primary publisher/research pages and official documentation using web tool",
        claims_not_supported=[
            "Our specific reconstruction is validated",
            "Q1 journals explicitly permit this workflow",
            "All missing historical data can be reconstructed",
        ],
    )
    f["governance_counters.json"] = dict.fromkeys(
        (*b.ZERO, "REPRESENTATION_RECONSTRUCTION_COUNT"), 0
    )
    f["governance_counters.json"].update(
        historical_T1_predictive_access_count=1,
        historical_T1_predictive_scoring_count=1,
        T2_STATE="DENY_SEALED_REVIEWER_RESERVE",
    )
    validate_policy(f)
    return f


def report(f, flight):
    titles = [
        "Objective",
        "Branch/HEAD",
        "Parent R2 state",
        "Why historical recovery is closed",
        "Predictive/XAI evidence boundary",
        "New prospective E1 design",
        "Terminology",
        "Scientific rationale",
        "Reviewer persistence question",
        "Literature-supported principles",
        "Future persistence architecture",
        "Representation package",
        "Immutable namespace",
        "Reconstruction sources",
        "TRAIN policy",
        "T1 policy",
        "TEXT policy",
        "CODE/PROCESS policy",
        "Representation validation",
        "Model relationship",
        "E1/E2 continuity",
        "Future XAI",
        "Threats to validity",
        "Q1 defensibility",
        "Replication package",
        "Recommendation",
    ]
    texts = [
        "Freeze a prospective reconstruction protocol and creation-time persistence governance. No representation or explanation execution.",
        flight["branch"]
        + " / "
        + flight["head"]
        + ". Nine preexisting B/R1/R2 entries classified as immutable prior work.",
        "Required B/R1/R2 blocked dispositions verified; 168 candidate scopes, zero complete canonical populations, 12 partial scopes retained.",
        "Original fitted executable state and complete transformed matrices were not persisted in the inspected confirmatory workflow. Historical exact matrix recovery is CLOSED_AS_INFEASIBLE_UNDER_AVAILABLE_EVIDENCE; no inference of data corruption or predictive invalidity.",
        "Sprint54 CLOSED_IMMUTABLE, MIXED_CONFIRMATORY_EVIDENCE, T1 1/1. Prospective XAI representations are separate explanatory evidence; no retroactive changes.",
        "Historical E1 nonprimary/illustrative where valid; prospective reconstructed E1 primary complementary feature-level analysis. Replace original-byte recovery with frozen-contract validation, preserving source and identity rigor.",
        "RECONSTRUCTED predictors and RECONSTRUCTED_REPRESENTATION inputs always distinct from original historical artifacts.",
        "Conditional reproducibility remedy using frozen legitimate inputs, exact semantics, transforms and supported predictor equivalence. No proof of reconstruction success yet.",
        "Current response and evidence slots provided. Exact historical human reason is UNKNOWN_NOT_DOCUMENTED; design characterization is an inference from code, not invented intention. Future completed-tense wording is gated.",
        "Primary provenance, reproducibility and SHAP sources support general traceability principles only. They do not validate this workflow or guarantee journal acceptance; see literature rationale and registry.",
        "A–Z artifacts required for future predictive/explanatory campaigns, with phase-specific gates and justified NOT_APPLICABLE for unused components. Predictions-only completion forbidden.",
        "Per project/modality/partition: matrix, row/column registries, schema, frozen transform/state, digests, runtime and manifest; TEXT additionally messages/vectorizer/vocabulary/IDF/token registry.",
        "New versioned prospective namespace, no historical overwrite, no symlink escape, no accepted-version replacement.",
        "Frozen sources and exact transforms are specified. Safe TRAIN source routing remains unresolved. R4 must obtain admissible identity-first access before reading; mixed T2 containers remain forbidden.",
        "Complete TRAIN-only population for admitted scopes; deterministic source-only construction, fixed membership/order, no model query or new fit.",
        "Separate human authorization required; T1 excluded from default R4. Labels, outcomes, metrics, tuning and T2 forbidden.",
        "Use existing exact reconstructed vectorizer where proven; a new TRAIN-only vectorizer fit would be a separately authorized methodological change and cannot be assumed compatible with the fixed predictor.",
        "CODE la/ld/nf/nd/ns/ent; PROCESS ndev/age/nuc/aexp/arexp/asexp; exact semantics and prediction-time provenance required. Unknown PROCESS rules block scopes; no feature migration.",
        "Twelve required source/partition/identity/schema/order/finite/repeatability/transform/model/manifest checks against the prospective contract. No original matrix byte equivalence requirement.",
        "Only fixed RECONSTRUCTED predictors with prior G4/G5 support; no training for XAI, no automatic equivalence of newly changed transforms.",
        "E1 within-modality features, E2 primary multimodal fusion. Architectural/interpretive continuity; no algebraic feature-SHAP propagation claim.",
        "Inherited LR analytical logit and exact tree methods/scales, fidelity, stability and heterogeneity unchanged. TRAIN/T1 caps 256, seed 20260901, local cap 8; no k-means amendment.",
        "Post-hoc reconstructed representation provenance disclosed: later construction, possible byte differences, unexecuted mitigations, unresolved sources and no predictive reevaluation.",
        Q1
        + ". Protocol coherence only. Source admission, population eligibility, execution validation and runtime enforcement remain future requirements.",
        "Blueprint frozen, not yet a runnable replication package. Requires source retrieval/digests, builder, states, lock, populations, tests, XAI outputs, figures/tables and manifests; licensing respected.",
        "Request separate authorization for R4 TRAIN source-admission and reconstruction/persistence. Stop if admissible inputs unavailable. Do not resume forensic original-matrix recovery, activate T1, or start R4 in R3.",
    ]
    return (
        "# Sprint 56.3B-R3 prospective reconstructed representation protocol\n\n"
        + VERDICT
        + "\n\n"
        + "\n\n".join(
            f"## {chr(65 + i)}. {title}\n\n{text}"
            for i, (title, text) in enumerate(zip(titles, texts, strict=True))
        )
        + "\n"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--validation", type=Path, required=True)
    args = parser.parse_args()
    branch_gate(b.git("rev-parse", "--abbrev-ref", "HEAD"))
    flight = json.loads(args.preflight.read_text())
    if flight["head"] != b.git("rev-parse", "HEAD"):
        raise ValueError("HEAD changed")
    for p, h in flight["parent_hashes"].items():
        if sha((ROOT / p).read_bytes()) != h:
            raise ValueError("Inherited artifact changed")
    reader = Reader()
    f = compile_protocol(reader.load())
    f["preflight.json"] = flight
    f["validation_results.json"] = json.loads(args.validation.read_text())
    f["SPRINT56_3B_R3_PROSPECTIVE_RECONSTRUCTED_REPRESENTATION_PROTOCOL_REPORT.md"] = (
        report(f, flight)
    )
    f["read_access_ledger.json"] = dict(
        reads=reader.reads,
        access_scope="Approved governance packages and static producer source only; no scientific payload",
    )
    f["implementation_provenance.json"] = {
        p: sha((ROOT / p).read_bytes()) for p in [SOURCE, TEST]
    }
    if any(sha((ROOT / p).read_bytes()) != h for p, h in reader.reads.items()):
        raise ValueError("Parent changed during compilation")
    if b.git("diff", "--name-only") or b.git("diff", "--cached", "--name-only"):
        raise ValueError("Historical tracked changes or staging")
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
