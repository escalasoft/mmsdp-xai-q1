# ruff: noqa: E501
"""Prospective E1 protocol compiler. Standard library, metadata only, no execution.

The pure compiler is branch independent. Publication of a new immutable package
requires the separately captured clean-tree preflight and matching parent HEAD.
No manifest entry is ever followed to a scientific payload or model object.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "audits/q1-prospective-e1-protocol-freeze/1.0.0"
BRANCH = "sprint-10/q1-prospective-e1-protocol-freeze"
PACKAGES = (
    "q1-xai-runtime-freeze",
    "q1-xai-reconstruction-execution",
    "q1-xai-reconstruction-equivalence-g4",
    "q1-xai-final-output-equivalence-g5",
    "q1-primary-xai-runtime-smoke",
    "q1-primary-xai-population-freeze",
    "q1-primary-xai-frozen-evidence-reuse",
    "q1-primary-xai-e1-input-e2-reference-resolution",
    "q1-primary-xai-e1-scientific-input-materialization",
    "q1-primary-xai-canonical-source-rematerialization-feasibility",
    "q1-primary-xai-alternative-design",
)
RUNTIME, G5, SMOKE, POP, MATERIAL, CANON, ALT = (
    PACKAGES[i] for i in (0, 3, 4, 5, 8, 9, 10)
)
SOURCES = {
    "methods": (RUNTIME, "explainer_contract.json"),
    "fidelity": (RUNTIME, "xai_fidelity_contract.json"),
    "stability": (RUNTIME, "xai_stability_contract.json"),
    "heterogeneity": (RUNTIME, "heterogeneity_interpretation_policy.json"),
    "correlation": (RUNTIME, "correlated_feature_policy.json"),
    "budget": (RUNTIME, "query_budget_policy.json"),
    "t1": (RUNTIME, "t1_xai_access_policy.json"),
    "g5": (G5, "g5_scope_results.jsonl"),
    "states": (POP, "model_state_readiness_ledger.jsonl"),
    "scales": (POP, "xai_output_scale_contract.json"),
    "runtime": (SMOKE, "isolated_runtime_lock.json"),
    "parent_log_audit": (SMOKE, "validation-initial-output.txt"),
    "material": (MATERIAL, "e1_materialization_ledger.jsonl"),
    "code": (CANON, "code_feature_definition_registry.jsonl"),
    "process": (CANON, "process_feature_definition_registry.jsonl"),
    "recovery": (CANON, "q1_e1_rematerialization_feasibility.json"),
    "architecture": (ALT, "recommended_xai_architecture.json"),
    "continuity": (ALT, "explanation_continuity_contract.json"),
    "counters": (ALT, "governance_counters.json"),
    "persistence": (ALT, "prospective_e1_persistence_contract.json"),
}
FAMILIES = ("Logistic Regression", "Random Forest", "XGBoost", "LightGBM")
MODALITIES = {"C": "CODE", "P": "PROCESS", "T": "TEXT"}
PASS_LIMITED = "PROSPECTIVE_E1_PROTOCOL_FREEZE_PASS_WITH_LIMITATIONS"
BLOCKED = "PROSPECTIVE_E1_PROTOCOL_FREEZE_BLOCKED"
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
    "ENVIRONMENT_MUTATION_COUNT",
    "MODEL_MUTATION_COUNT",
    "E2_REOPEN_COUNT",
    "POPULATION_SELECTION_COUNT",
    "HISTORICAL_E1_RECOVERY_COUNT",
    "COMMIT_COUNT",
    "PUSH_COUNT",
    "PR_COUNT",
)


class ProtocolBlocked(ValueError):
    """Missing or contradictory parent evidence; no package is published."""


def encode(value):
    return (
        json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False)
        + "\n"
    ).encode()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def source_path(package, name):
    return f"audits/{package}/1.0.0/{name}"


def allowed_paths():
    return {source_path(*v) for v in SOURCES.values()} | {
        source_path(p, "MANIFEST.sha256") for p in PACKAGES
    }


class MetadataReader:
    """Exact allowlist; links, arbitrary JSON and manifest targets are denied."""

    def __init__(self, root):
        self.root = Path(root).resolve()
        self.reads = {}

    def read(self, relative):
        if relative not in allowed_paths():
            raise PermissionError("Protocol metadata read boundary: " + relative)
        path = self.root / relative
        if path.resolve() != path or not path.is_file():
            raise ProtocolBlocked(
                "Missing metadata or symbolic-link routing: " + relative
            )
        raw = path.read_bytes()
        self.reads[relative] = digest(raw)
        return raw


def load_evidence(root=ROOT):
    reader = MetadataReader(root)
    manifests = {}
    for package in PACKAGES:
        lines = (
            reader.read(source_path(package, "MANIFEST.sha256")).decode().splitlines()
        )
        entries = {}
        for line in lines:
            h, name = line.split("  ", 1)
            if (
                name in entries
                or len(h) != 64
                or any(c not in "0123456789abcdef" for c in h)
            ):
                raise ProtocolBlocked("Ambiguous parent manifest: " + package)
            entries[name] = h
        if not entries:
            raise ProtocolBlocked("Empty parent manifest: " + package)
        manifests[package] = entries
    evidence = {}
    for key, (package, name) in SOURCES.items():
        raw = reader.read(source_path(package, name))
        # Some old manifests use repository-relative rather than basename entries.
        expected = manifests[package].get(
            name, manifests[package].get(source_path(package, name))
        )
        if key == "parent_log_audit":
            # Audit this diagnostic artifact, never use its contents as scientific
            # evidence. A mismatch becomes an explicit BLOCKED disposition.
            evidence[key] = {
                "path": source_path(package, name),
                "manifest_sha256": expected,
                "actual_sha256": digest(raw),
                "status": "PASS"
                if digest(raw) == expected
                else "FAIL_MANIFEST_MISMATCH",
                "scope": "Historical validation log; original bytes not recoverable from current manifest alone",
            }
            continue
        if digest(raw) != expected:
            raise ProtocolBlocked("Parent metadata digest mismatch: " + key)
        evidence[key] = (
            [json.loads(line) for line in raw.decode().splitlines() if line]
            if name.endswith(".jsonl")
            else json.loads(raw)
        )
    return evidence, reader.reads


def keyed(rows, field="configuration"):
    result = {}
    for row in rows:
        key = (row["project"], row["algorithm"], row[field])
        if key in result:
            raise ProtocolBlocked("Duplicate scope metadata: " + repr(key))
        result[key] = row
    return result


def scope_universe(evidence):
    g5 = keyed(evidence["g5"])
    states = keyed(evidence["states"])
    material = keyed(evidence["material"], "modality")
    projects = sorted({r["project"] for r in evidence["g5"]})
    if len(projects) != 14 or len(g5) != 389:
        raise ProtocolBlocked("Parent scope universe changed")
    result = []
    for project in projects:
        for family in FAMILIES:
            for code, modality in MODALITIES.items():
                key = (project, family, code)
                g, s, m = (d.get(key) for d in (g5, states, material))
                if not all((g, s, m)):
                    raise ProtocolBlocked("Missing candidate evidence: " + repr(key))
                identity = g["model_identity_sha256"]
                if any(r["model_identity_sha256"] != identity for r in (s, m)):
                    raise ProtocolBlocked("Contradictory model identity: " + repr(key))
                equivalent = (
                    g["G4_outcome"] == "G4_PASS_ROW_LEVEL_RAW_EQUIVALENCE"
                    and g["G5_outcome"] == "G5_PASS_FINAL_OUTPUT_EQUIVALENCE"
                    and s["state_readiness"] == "READY_VERIFIED"
                    and s["G4"] == g["G4_outcome"]
                    and s["G5"] == g["G5_outcome"]
                    and all(
                        s["G1_G3"].get(f"G{i}") == f"G{i}_PASS_ALL_REQUIRED_COMPONENTS"
                        for i in range(1, 4)
                    )
                )
                # Historical incomplete input evidence must never silently promote a scope.
                if m["full_scope_materialized"] or m["materialized_t1_rows"] != 0:
                    raise ProtocolBlocked(
                        "Unexpected input evidence requires prospective review"
                    )
                status = (
                    "E1_INELIGIBLE_EQUIVALENCE"
                    if not equivalent
                    else "TEXT_E1_INELIGIBLE"
                    if modality == "TEXT"
                    else "E1_PENDING_SCIENTIFIC_INPUT_PROVENANCE"
                )
                result.append(
                    {
                        "scope_id": "|".join(key),
                        "project": project,
                        "algorithm_family": family,
                        "modality": modality,
                        "historical_configuration": code,
                        "model_identity_sha256": identity,
                        "state_origin": "RECONSTRUCTED_NOT_ORIGINAL_SPRINT54",
                        "equivalence_eligible": equivalent,
                        "eligibility": status,
                        "scientific_execution_eligible": False,
                        "fidelity": "FIDELITY_NOT_TESTED",
                        "stability": "INSUFFICIENT_EVIDENCE",
                        "required_state_references": s["states"],
                        "historical_train_count_metadata": m["expected_train_rows"],
                        "historical_t1_count_metadata": m["expected_t1_rows"],
                        "historical_partial_train_count_metadata": m[
                            "materialized_train_rows"
                        ],
                        "input_blocker": m["exact_blocker"],
                        "text_gate": "Complete token/vectorizer/row alignment NOT_ESTABLISHED"
                        if modality == "TEXT"
                        else "NOT_APPLICABLE",
                        "future_gate": "Separate authorized source/identity/representation proof; no historical recovery rerun",
                        "source_keys": ["g5", "states", "material"],
                    }
                )
    return result


def fidelity_status(passed, attempted, expected):
    if not (0 <= passed <= attempted <= expected):
        raise ValueError("Invalid fidelity counts")
    if attempted == 0:
        return "FIDELITY_NOT_TESTED"
    if passed < attempted:
        return "FIDELITY_FAIL"
    return "FIDELITY_PASS" if attempted == expected else "FIDELITY_MIXED"


def compile_protocol(e):
    """Pure deterministic policy compilation: no files, git, scientific rows or models."""
    if (
        e["recovery"]["scientific_path"]
        != "CANONICAL_E1_REMATERIALIZATION_PATH_NOT_ESTABLISHED"
    ):
        raise ProtocolBlocked("Historical recovery disposition changed")
    if e["architecture"]["selected_alternative"] != "C":
        raise ProtocolBlocked("Parent architecture changed")
    if e["counters"]["T2_STATE"] != "DENY_SEALED_REVIEWER_RESERVE":
        raise ProtocolBlocked("T2 policy changed")
    if any(v != 0 for k, v in e["counters"].items() if k.endswith("_COUNT")):
        raise ProtocolBlocked("Parent design counters are nonzero")
    if (
        e["t1"]["historical_T1_predictive_access_count"],
        e["t1"]["historical_T1_predictive_scoring_count"],
    ) != (1, 1):
        raise ProtocolBlocked("Historical predictive counters changed")
    scopes = scope_universe(e)
    p = {}

    def put(name, value):
        p[name + ".json"] = value

    p["e1_scope_universe.jsonl"] = scopes
    counts = dict(sorted(Counter(r["eligibility"] for r in scopes).items()))
    put(
        "protocol_summary",
        {
            "schema_version": "q1-prospective-e1-protocol-freeze-1.0.0",
            "disposition": PASS_LIMITED
            if e["parent_log_audit"]["status"] == "PASS"
            else BLOCKED,
            "protocol_acceptance": "BLOCKED_PENDING_PARENT_INTEGRITY_RESOLUTION"
            if e["parent_log_audit"]["status"] != "PASS"
            else "FROZEN_WITH_LIMITATIONS",
            "parent_integrity_finding": e["parent_log_audit"],
            "candidate_scopes": len(scopes),
            "equivalence_eligible_count": sum(
                r["equivalence_eligible"] for r in scopes
            ),
            "eligibility_counts": counts,
            "scientific_execution_eligible_count": 0,
            "execution_authorized": False,
            "protocol_frozen_is_not_E1_Q1_ready": True,
            "limitations": [
                "Complete legitimate TRAIN/T1 scientific inputs not established",
                "All TEXT scopes fail complete input/alignment proof at freeze time",
                "No empirical E1 fidelity, stability, heterogeneity or continuity established",
                "No new source, predictor, training or historical recovery authorized",
            ],
        },
    )
    put(
        "scientific_state_preservation",
        {
            "predictive_conclusion": "MIXED_CONFIRMATORY_EVIDENCE",
            "predictive_evidence": "CLOSED_IMMUTABLE",
            "historical_T1_predictive_access_count": 1,
            "historical_T1_predictive_scoring_count": 1,
            "G5_verified_scopes": 389,
            "primary_XAI_core": "E2_ANALYTICAL_FUSION",
            "complementary_XAI_layer": "PROSPECTIVE_E1",
            "E3": "SEPARATE_CALIBRATION",
            "historical_E1": "LIMITED_ILLUSTRATIVE_ONLY",
            "historical_recovery": "CLOSED",
            "original_Sprint54_state_claim": "FORBIDDEN",
            "parent_architecture": e["architecture"],
            "parent_counters": e["counters"],
        },
    )
    put(
        "e1_unit_of_analysis",
        {
            "unit": ["project", "algorithm_family", "unimodal_modality"],
            "families": list(FAMILIES),
            "modalities": list(MODALITIES.values()),
            "theoretical_maximum": 168,
            "multimodal_E1": "FORBIDDEN",
            "primary_selection": "PERFORMANCE_INDEPENDENT_SCOPE_COMPLETE_ELIGIBLE_UNIVERSE",
            "eligibility_rules": {
                "E1_INELIGIBLE_EQUIVALENCE": "Any G1–G5/state gate not verified",
                "TEXT_E1_INELIGIBLE": "Any exact text alignment or future row representation proof absent",
                "E1_PENDING_SCIENTIFIC_INPUT_PROVENANCE": "State equivalent; complete legitimate inputs unproved",
                "E1_ELIGIBLE_AFTER_SEPARATE_AUTHORIZATION": "All AUTH-E1 gates plus full per-scope evidence; not assigned in 56.3A",
            },
            "unknown": "Fail closed; retain in coverage denominator; never silently drop",
            "terminology": {
                "E1": "Feature-level explanation of one specific unimodal predictive model",
                "E2": "Analytical multimodal fusion explanation at modality level",
                "E3": "Calibration mapping explanation or calibration-state inspection",
                "historical_E1": "Historical frozen predictor explanation with incompletely recovered scientific input chain",
                "prospective_complementary_E1": "New predeclared explanation analysis of eligible reconstructed states and controlled TRAIN/T1 populations",
            },
        },
    )
    put(
        "e1_method_contract",
        {
            "inherited": e["methods"],
            "resolved_scales": e["scales"],
            "LIME": "EXCLUDED_FROM_PRIMARY_XAI",
            "counterfactuals": "EXCLUDED_FROM_PRIMARY_XAI",
            "runtime_lock": e["runtime"],
            "runtime_validation_scope": "TRAIN_ONLY_REPRESENTATIVE_SMOKE_NOT_ALL_SCOPE_PROOF",
        },
    )
    put(
        "lr_analytical_contract",
        {
            "primary_method": e["methods"]["E1_unimodal"]["Logistic Regression"],
            "eta": "intercept + sum(beta_j*x_j)",
            "phi_j": "beta_j*(x_j-mu_j)",
            "phi_0": "intercept + sum(beta_j*mu_j)",
            "mu_j": "Arithmetic mean over exact transformed selected TRAIN reference; no refit",
            "identity": "phi_0 + sum(phi_j) = eta(x)",
            "scale": "LOGIT",
            "primary_global": "mean_i(abs(phi_j(x_i)))",
            "secondary": [
                "sign consistency",
                "rank stability",
                "coefficient sign",
                "contribution distribution",
            ],
            "coefficient_magnitude": "DIAGNOSTIC_ONLY",
            "fidelity": e["fidelity"]["analytical_LR"],
            "class_semantics": "Positive observed benchmark class 1; exact stored class order required",
        },
    )
    for prefix, family in [
        ("rf", "Random Forest"),
        ("xgb", "XGBoost"),
        ("lgb", "LightGBM"),
    ]:
        put(
            prefix + "_treeshap_contract",
            {
                "family": family,
                "primary_method": e["methods"]["E1_unimodal"][family],
                "scale": e["scales"]["E1"][family],
                "explainer": "shap.TreeExplainer",
                **e["scales"]["TreeSHAP"],
                "approximate": False,
                "check_additivity": True,
                "positive_class": 1,
                "class_order": "Verify exact model ordering before selecting class-1 slice",
                "required": [
                    "exact booster/predictor state digest",
                    "exact feature order",
                    "objective and positive-class semantics",
                    "missing/categorical semantics",
                    "runtime compatibility",
                    "every-row manual frozen-scale residual check",
                ],
                "TRAIN_reference_role": "Freeze capped TRAIN reference for diagnostics; TreeSHAP uses persisted TRAIN path counts, data=None",
                "no_switch_to_interventional": True,
                "fidelity": e["fidelity"]["TreeSHAP"],
                "impurity_importance": "DIAGNOSTIC_ONLY_NOT_SHAP",
            },
        )
    selection = {
        "seed": 20260901,
        "maximum_rows_per_scope": 256,
        "selection_executed": False,
        "synthetic_centroids": "FORBIDDEN",
        "tie_break": "SHA-256 lexical ordering over stable row identity; identity lexical order resolves a hash collision",
        "stable_key": "SHA256(UTF8(canonical compact sorted-key JSON of seed,purpose,project,representation_identity,row_identifier)))",
        "canonical_JSON": "ensure_ascii=false; separators=(comma,colon); no whitespace; identity strings exact, no normalization",
        "representation_identity": "Frozen project/modality preprocessing+feature-order digest; shared across families when exact representation compatible; include family only if technically required",
        "identity_gate": "Unique canonical project+commit identity, exact partition proof, valid representation; missing or conflicting identity blocks scope",
        "allocation": "If N<=256 take all. Otherwise cyclic lexicographic nonempty-stratum allocation, one row per stratum per cycle until cap; exhausted strata skipped",
        "within_stratum": "Ascending stable_key; final selected order ascending stable_key",
        "representation_validity": "Validate before sampling; retain excluded counts/reasons; systematic or ambiguous provenance blocks scope",
        "record": [
            "source population count",
            "valid count",
            "excluded count and reasons",
            "selected count",
            "class distribution where allowed",
            "temporal range",
            "identity digest",
            "selection digest",
            "row order",
            "stratum quotas",
        ],
        "temporal_coverage": "Report selected/source ranges after authorized selection; no temporal data invented and no reselection from diagnostics",
        "primary_estimand": "Mean over balanced selected reference/foreground, not prevalence-weighted full partition mean",
        "result_dependent_selection": "FORBIDDEN",
    }
    put(
        "train_background_policy",
        {
            **selection,
            "partition": "TRAIN",
            "strata": "Legitimate frozen TRAIN binary label if complete and authorized, otherwise one unlabelled stratum",
            "label_permission_decision": "Record source-level authorization and completeness before selection, never infer from outcomes",
            "purpose": "TRAIN_REFERENCE",
            "T1_labels": "FORBIDDEN",
            "tree_background": e["scales"]["TreeSHAP"]["background"],
            "shap_kmeans_primary": "FORBIDDEN",
            "kmeans_sensitivity": "Separate prospective amendment only after documented necessity, primary infeasibility and reduced/unreduced comparison protocol",
        },
    )
    put(
        "t1_global_foreground_policy",
        {
            **selection,
            "partition": "T1",
            "mode": "T1_SELECTION_LABEL_BLIND",
            "label_aware_mode": "T1_SELECTION_LABEL_AWARE_NOT_AUTHORIZED",
            "future_56_3B_56_3C_mode": "T1_SELECTION_LABEL_BLIND_ONLY_UNDER_SEPARATE_AUTHORIZATION",
            "purpose": "T1_GLOBAL",
            "strata": "Frozen predicted decision 0/1 if complete; otherwise one identity-only stratum",
            "decision_source": "Previously frozen outputs linked by exact state/row identity; never query entire T1 to select cases",
            "prohibited_inputs": [
                "T1 labels",
                "error ranking",
                "PR-AUC",
                "MCC",
                "F1",
                "SHAP magnitude",
                "T2",
            ],
            "confidence_bins": "Not used for global sampling; avoids extra output access requirements",
            "source_population": "Exact project T1 membership already governed in parent G4/G5; eligibility requires legitimate complete representation evidence",
            "new_population": "Not a substitute for historical T1; requires separate prospective design amendment and own partition namespace",
        },
    )
    put(
        "local_case_selection_policy",
        {
            "maximum_rows_per_scope": 8,
            "subset_of_global": True,
            "mode": "T1_SELECTION_LABEL_BLIND",
            "seed": 20260901,
            "selection_executed": False,
            "tie_break": selection["tie_break"],
            "class_quota": "Four predicted-positive and four predicted-negative if available",
            "ordered_roles_per_predicted_class": [
                "maximum absolute p_minus_frozen_threshold: high confidence",
                "minimum absolute p_minus_frozen_threshold: near threshold",
                "minimum distance from within-class median absolute p_minus_frozen_threshold",
                "maximum absolute p_minus_frozen_threshold among remaining: integrity-supported extreme",
            ],
            "algorithm": "Within each class select ordered roles without replacement, ties by global selection key. Reallocate unused class slots by ascending global key. If probability or threshold linkage incomplete, use ascending global key with available decision quotas; annotate confidence roles unavailable.",
            "probability_scale": "Exactly frozen decision input scale, calibration identity recorded; no newly computed confidence for selection",
            "labels": "TP/TN/FP/FN strata not authorized; correctness may be annotated after selection only under separate label access authorization",
            "label_aware_alternative": "Future amendment may specify high-confidence TP,TN,FP,FN,near-threshold positive,near-threshold negative,median-confidence,integrity-supported extreme; prohibited in current primary selection",
            "attractive_plot_selection": "FORBIDDEN",
            "freeze_before_attribution": True,
        },
    )
    text_requirements = [
        "exact frozen vocabulary",
        "exact IDF",
        "tokenizer and lowercasing",
        "n-gram range",
        "min_df/max_df/max_features/sublinear_tf/norm/token_pattern/analyzer/stop_words/encoding",
        "final column order",
        "predictor-vectorizer alignment",
        "future row transformed representation availability",
        "token identity",
    ]
    put(
        "text_e1_contract",
        {
            "required_proofs": text_requirements,
            "any_unknown": "TEXT_E1_INELIGIBLE",
            "global": "Mean absolute token attribution within project/model over ALL selected rows, including zero-valued tokens",
            "local": "Exact transformed message token contributions; retain nonzero attribution to absent tokens for centered/path-dependent methods",
            "empty_message": "Preserve frozen vectorizer behavior; no synthetic token or silent row deletion",
            "cross_project": "No literal token-rank averaging without demonstrated vocabulary and semantic alignment",
            "semantic_categories": "Optional only with explicit versioned manual coding rubric, token-to-category map and reproducible coding audit before synthesis",
            "allowed_wording": [
                "associated with model prediction",
                "contributed to the model output",
                "received positive/negative attribution",
            ],
            "forbidden": [
                "developer intent",
                "tokens cause defects",
                "correlation grouping of tokens",
            ],
        },
    )
    registry = []
    display = {
        "la": "Lines added",
        "ld": "Lines deleted",
        "nf": "Files changed",
        "nd": "Directories changed",
        "ns": "Subsystems changed",
        "ent": "Change entropy",
        "ndev": "Prior developers",
        "age": "Time since prior changes",
        "nuc": "Prior unique changes",
        "aexp": "Author experience",
        "arexp": "Recent author experience",
        "asexp": "Author subsystem experience",
    }
    units = {
        "la": "lines",
        "ld": "lines",
        "nf": "files",
        "nd": "directories",
        "ns": "subsystems",
        "ndev": "developers",
        "nuc": "changes",
        "aexp": "commits",
        "asexp": "commits within subsystems",
        "age": "SOURCE_UNIT_UNRESOLVED",
        "ent": "dimensionless; logarithm base/normalization unresolved",
        "arexp": "weighted commits; weighting/time unit unresolved",
    }
    for key, modality in [("code", "CODE"), ("process", "PROCESS")]:
        for r in e[key]:
            name = r["feature_name"]
            registry.append(
                {
                    "feature_name": name,
                    "display_name": display[name],
                    "modality": modality,
                    "feature_order": r["feature_order"],
                    "definition": r.get(
                        "scientific_definition", r.get("semantic_definition")
                    ),
                    "unit": units[name],
                    "transformation": r.get(
                        "transformation/preprocessing", r.get("preprocessing")
                    ),
                    "missing_value_policy": r.get(
                        "missing_value_semantics", r.get("missing_value_handling")
                    ),
                    "sign_interpretation_limits": "Model-scale association relative to reference; no causal monotonicity; correlated predictors redistribute attribution",
                    "source_provenance": source_path(*SOURCES[key]),
                    "authoritative_record": r,
                    "independent_recomputation": "NOT_AUTHORIZED; definitions do not establish equivalent input replay",
                    "unresolved_unit_gate": "Retain source units without invented conversion; block unit-specific claims until authoritative proof",
                }
            )
    put(
        "code_process_feature_contract",
        {
            "registry": registry,
            "silent_modality_reclassification": "FORBIDDEN",
            "figure_names": "display_name mapped to exact feature_name and order; no opaque Column_N names",
            "alignment": "Require ordered column digest, dtype, transformation state and predictor dimension agreement per scope",
            "semantic_limits": "Parent missing routing/PROCESS computation semantics remain unresolved; no Git-derived proxy replacement",
        },
    )
    put(
        "correlated_feature_policy",
        {
            **e["correlation"],
            "population": "Frozen valid TRAIN reference, at most 256 rows; no T1 correlation computation",
            "ranks": "Average ranks for ties; pairwise finite values only with support count >=3; undefined/constant pairs create no edge",
            "missing": "Use exact model preprocessing; report missing pair support; never fit a SHAP-specific imputer",
            "group_importance": "mean_i(abs(sum_j_in_group(phi_ij)))",
            "redistribution": "Also report sum_j mean_i(abs(phi_ij)), each member share and cancellation gap",
            "group_alignment": "Same frozen TRAIN group identities required for across-family grouped comparisons",
            "warning": "Small within-group rank swaps need not imply substantive instability; no causal interpretation",
        },
    )
    put(
        "fidelity_contract",
        {
            "inherited_exact": e["fidelity"],
            "unexplained_fraction_threshold": 0.0,
            "threshold_origin": "56.3A strict completion rule; no numerical tolerance changes",
            "denominator": "All frozen expected foreground rows in every required repetition; failed/omitted rows never removed",
            "statuses": {
                "FIDELITY_NOT_TESTED": "Zero attempted rows",
                "FIDELITY_PASS": "Every expected row attempted and passes finite residual bounds",
                "FIDELITY_MIXED": "Attempted rows pass but expected rows missing; diagnostic only, scope inadmissible",
                "FIDELITY_FAIL": "Any attempted row fails bound, raises error or yields nonfinite attribution/output",
            },
            "scope_admission": "Only FIDELITY_PASS; any unexplained fraction >0 fails scientific eligibility",
            "tolerance_relaxation": "FORBIDDEN",
            "sampled_fidelity_only": "FORBIDDEN",
        },
    )
    thresholds = e["heterogeneity"]["cross_model"]["thresholds"]
    put(
        "stability_contract",
        {
            "inherited_exact": e["stability"],
            "comparison_thresholds": thresholds,
            "threshold_source": "Sprint55 heterogeneity diagnostic thresholds; prospectively applied to comparable ranking diagnostics",
            "populations": "Identical state, reference and foreground across seeds; no population reselection",
            "repetitions": 20,
            "comparison_pairs": "All 190 unordered repetition pairs",
            "scope": "Numerical repeatability and fixed-population ranking agreement, not sampling/reference robustness",
            "k": "min(k, aligned feature count); k covering entire support is non-discriminating and cannot alone support STABLE",
            "ranking": "Descending mean absolute attribution; exact feature identity lexical tie-break; Spearman uses average tied ranks",
            "sign_agreement": "Fraction of aligned row-feature attribution entries with equal sign using zero band +/-1e-12; also report signed-mean global agreement; do not silently drop zeros",
            "TV": "0.5*sum(abs(p_j-q_j)), p normalized mean absolute attribution over identical support; all-zero distribution undefined",
            "statuses": {
                "STABLE": "Fidelity complete; all numerical repeats <=1e-12 and all defined informative metrics meet all frozen thresholds",
                "MIXED_STABILITY": "Fidelity complete and numerical repeatability passes, with both passing and failing informative ranking diagnostics",
                "UNSTABLE": "Any numerical-repeat bound violation or all informative ranking diagnostics fail",
                "INSUFFICIENT_EVIDENCE": "Missing repetition, fidelity failure, unaligned support, undefined required metric or no informative metric",
            },
            "undefined": "Report reason; never replace undefined with a pass",
            "post_result_change": "FORBIDDEN",
        },
    )
    put(
        "heterogeneity_contract",
        {
            "inherited_exact": e["heterogeneity"],
            "axes": [
                "within-project cross-model",
                "within-model cross-project",
                "modality synthesis",
            ],
            "comparison": "Every unordered eligible family pair on common exact feature semantics and aligned population; unequal populations descriptive only, not isolated model effects",
            "scales": "Compare ranks and normalized nonnegative mean-absolute attribution distributions only; never pool raw probability/logit/margin magnitudes",
            "sign_comparison": "Aligned signed-mean feature contribution direction only; differing references disclosed; cancellation/undefined signs reported",
            "statuses": {
                "INSUFFICIENT_CROSS_MODEL_EVIDENCE": "Fewer than 3 comparable eligible families or required comparison metrics undefined",
                "STABLE_CROSS_MODEL_PATTERN": "All comparable family pairs meet all thresholds within project",
                "PROJECT_SPECIFIC_PATTERN": "Within-project stable pattern but cross-project support rule fails",
                "MODEL_DEPENDENT_PATTERN": "Within-project cross-family disagreement with a consistent passing within-family cross-project pattern",
                "HETEROGENEOUS_PATTERN": "Both axes disagree or no single project/family localization supported",
            },
            "precedence": "Insufficient first; report axis-specific labels, never force one pooled label",
            "cross_project_rule": e["heterogeneity"]["cross_project"],
            "material_reversal": "Opposite nonzero signed-mean attribution for an aligned top-3 feature, exceeding the fixed zero band in both projects; disclose every reversal",
            "universal": "All 14 candidate projects and all four families eligible/comparable and passing, with zero material reversals; otherwise no universal claim",
            "TEXT": "Project-specific unless exact cross-project semantic mapping is proved",
            "inferential_policy": "Descriptive only; no predictive significance tests for explanation superiority; future inferential test requires separate freeze",
        },
    )
    put(
        "e1_e2_continuity_contract",
        {
            "chain": [
                "original feature",
                "unimodal representation",
                "unimodal model",
                "unimodal probability",
                "fusion meta-model",
                "multimodal prediction",
            ],
            "E1": "feature -> unimodal-model contribution",
            "E2": "unimodal probability -> fused meta-logit contribution",
            "E2_role": "PRIMARY_EXPLANATORY_CORE",
            "E1_role": "COMPLEMENTARY_FEATURE_LAYER",
            "parent_exact_link_contract": e["continuity"],
            "labels": {
                "CONTINUITY_ARCHITECTURAL": "Same CODE/PROCESS/TEXT definitions and late-fusion hierarchy documented; distinct reconstructed/historical states and populations disclosed",
                "CONTINUITY_DIRECTIONAL": "Architectural continuity plus exact same-row/state/probability linkage, passing E1/E2 fidelity and stable within-scale directional co-occurrence; descriptive only",
                "CONTINUITY_PROJECT_SPECIFIC": "Directional conditions hold only in named projects; disclose all other projects and failures",
                "CONTINUITY_MODEL_DEPENDENT": "Directional conditions vary by family within an aligned project/population; all families shown",
                "CONTINUITY_NOT_ESTABLISHED": "Architecture/semantics incompatible or required empirical linkage absent for the proposed claim",
            },
            "label_assignment": "Architectural label is design-level; directional/project/model labels require future evidence and may accompany it; no empirical label assigned now",
            "prohibited": [
                "propagate E1 SHAP through E2",
                "sum heterogeneous base-model scales",
                "largest E1 feature necessarily responsible for largest E2 modality contribution",
                "splice prospective E1 and historical E2 into an exact shared-row chain",
            ],
        },
    )
    put(
        "e1_e2_bridge_policy",
        {
            "unit": "project x family x multimodal configuration; only included modalities",
            "E1_supply": "Within-modality top features and stability",
            "E2_supply": "Analytical modality contributions on frozen fusion meta-logit and OOF reference",
            "strong_modality": "Modality with maximum mean absolute E2 contribution in configuration; exact ties all retained",
            "common_chain_required": "Exact linked row/population, base state, representation and unimodal probability to E2 inputs for empirical co-occurrence; architecture-only otherwise",
            "status_precedence": [
                "BRIDGE_INSUFFICIENT_E2",
                "BRIDGE_INSUFFICIENT_E1",
                "BRIDGE_CONSISTENT",
                "BRIDGE_PARTIALLY_CONSISTENT",
                "BRIDGE_DIVERGENT",
            ],
            "statuses": {
                "BRIDGE_INSUFFICIENT_E2": "Missing eligible/fidelity-complete E2 for configuration",
                "BRIDGE_INSUFFICIENT_E1": "Missing eligible E1, undefined stability, inadequate population or unproved exact common chain",
                "BRIDGE_CONSISTENT": "All strong E2 modalities contain STABLE E1 patterns",
                "BRIDGE_PARTIALLY_CONSISTENT": "At least one strong modality has STABLE or MIXED_STABILITY E1 but not all are STABLE",
                "BRIDGE_DIVERGENT": "Every strong modality has UNSTABLE E1 despite complete eligible comparable evidence",
            },
            "allowed_wording": "modality-level contribution co-occurred with stable feature-level attribution patterns",
            "forbidden_wording": [
                "feature X caused modality Y to dominate",
                "SHAP proves why multimodality improved",
                "feature X explains the performance gain",
            ],
            "no_mathematical_composition": True,
        },
    )
    names = [
        ("E1-G1", "Global mean absolute feature attribution"),
        ("E1-G2", "Cross-model rank stability and heterogeneity matrix"),
        ("E1-G3", "Project-level top-feature/group heatmap"),
        ("E1-L1", "Preselected local waterfall"),
        ("E1-L2", "Preselected local comparison"),
        ("E1-C1", "CODE/PROCESS correlated-group comparison"),
        ("E1-T1", "Project/model token attribution summary"),
        ("E1-E2", "Architectural feature-to-unimodal-to-fusion bridge"),
    ]
    put(
        "figure_contract",
        {
            "generated_count": 0,
            "families": [
                {
                    "id": ident,
                    "title": title,
                    "status": "FROZEN_DESIGN_NOT_EMPIRICAL_RESULT",
                    "required_metadata": [
                        "eligible scope count",
                        "population count",
                        "family",
                        "modality",
                        "attribution scale",
                        "normalization rule",
                        "missing/ineligible scopes",
                        "descriptive/inferential label",
                        "source manifest",
                        "feature/row/state digests",
                    ],
                    "normalization": "Within-scope raw scale; rank/TV panels may use sum-to-one absolute importance with zero-sum flagged; never cross-scale raw pooling",
                    "reporting": "DESCRIPTIVE",
                    "condition": (
                        "Correct-versus-error annotation requires separate label authorization after label-blind selection; otherwise prediction-only panels, no correct/error claim"
                        if ident == "E1-L2"
                        else "Exact bridge linkage or architecture-only diagram with separate scales"
                        if ident == "E1-E2"
                        else "Eligible evidence, fidelity/stability and complete coverage disclosure"
                    ),
                }
                for ident, title in names
            ],
        },
    )
    criteria = [
        "exact reconstructed-state provenance",
        "equivalence eligibility",
        "feature-order integrity",
        "preprocessing integrity",
        "TRAIN background integrity",
        "T1 foreground integrity",
        "model-output scale integrity",
        "fidelity",
        "deterministic repeatability",
        "stability",
        "attribution completeness",
        "project coverage",
        "algorithm-family coverage",
        "modality coverage",
        "local explanation coverage",
        "global explanation coverage",
        "heterogeneity analysis eligibility",
        "manuscript traceability",
    ]
    put(
        "q1_scientific_sufficiency_gate",
        {
            "criteria": criteria,
            "matrix_statuses": [
                "PASS",
                "PASS_WITH_LIMITATION",
                "FAIL",
                "NOT_APPLICABLE",
            ],
            "current_assessment": "NOT_EXECUTED; no E1_Q1_READY disposition in 56.3A",
            "hard_gates": criteria[:9] + [criteria[10], criteria[17]],
            "scope_minimum": ">=3 global rows; >=1 local row per nonempty predicted class (max8); exact small-population counts disclosed",
            "coverage_minimum_for_limited_synthesis": ">=3 projects each with >=3 comparable families per claimed modality; cross-project stability still requires inherited >=11 pass and <=1 reversal",
            "matrix_rule": "PASS requires criterion fully met; PASS_WITH_LIMITATION only predeclared coverage/stability limits; FAIL for unmet required gate; NOT_APPLICABLE only logically absent diagnostic, never missing data",
            "aggregation": {
                "E1_Q1_READY": "All 168 candidate scopes satisfy every applicable criterion; all modalities/families/projects covered; complete local/global and heterogeneity outputs",
                "E1_Q1_READY_WITH_PREDECLARED_LIMITATIONS": "All admitted scopes pass hard gates; minimum limited synthesis coverage met for every claimed modality; deficits/instability disclosed without universal claims",
                "E1_Q1_PARTIAL_ONLY": "Some hard-gate-passing evidence but minimum coverage/synthesis or required outputs incomplete",
                "E1_Q1_NOT_READY": "No admissible scope or common governance/provenance violation",
            },
            "no_promotion_by_explainer_success": True,
        },
    )
    auth = [
        "eligible reconstructed model state verified",
        "TRAIN background identities frozen",
        "T1 foreground identities frozen",
        "local case identities frozen",
        "runtime/explainer version frozen",
        "output scale frozen",
        "feature order and preprocessing frozen",
        "query budget frozen",
        "fidelity tolerance frozen",
        "stability protocol frozen",
        "claim boundaries accepted",
        "T2 access remains zero",
    ]
    put(
        "execution_authorization_gate",
        {
            "scientific_execution_authorized": False,
            "requirements": {
                f"AUTH-E1-{i}": {
                    "requirement": x,
                    "execution_gate_status": "PENDING_FUTURE_EVIDENCE_AND_HUMAN_APPROVAL",
                }
                for i, x in enumerate(auth, 1)
            },
            "additional_hard_gates": [
                "Legitimate source authorization independent of historical closed recovery",
                "Exact row/partition/representation/predictor linkage",
                "Separate human approval of scope roster and digest-bound execution plan",
            ],
            "rule": "All required gates PASS with evidence references and explicit human execution approval; freeze is never authorization",
            "56_3B": "Metadata-only source/provenance and eligibility assessment first; any row materialization needs separate explicit authorization before payload access",
            "56_3C": "Only after 56.3B verified populations and separate scientific attribution authorization",
            "no_source": "Stop and request design review; do not reopen repeated historical recovery or train new states",
        },
    )
    put(
        "t1_xai_access_policy",
        {
            "mode": "DENY_IN_56_3A",
            "historical_T1_predictive_access_count": 1,
            "historical_T1_predictive_scoring_count": 1,
            "new_counter_namespace": [k for k in ZERO if k.startswith("T1_")],
            "future_label_policy": "T1_SELECTION_LABEL_BLIND",
            "no_predictive_reaccess_or_rescoring": True,
            "metadata_reads": "Scope aggregate counts and digests only; no individual T1 identities, labels, features or prediction rows",
        },
    )
    put(
        "t2_sealed_reserve_policy",
        {
            "status": "DENY_SEALED_REVIEWER_RESERVE",
            "current_access_count": 0,
            "future_budget": 0,
            "forbidden_uses": [
                "background",
                "foreground",
                "local",
                "stability",
                "figures",
                "method selection",
                "protocol validation",
            ],
            "partial_consumption": "FORBIDDEN",
        },
    )
    put(
        "query_budget",
        {
            "inherited_exact": e["budget"],
            "current_all_scientific_budgets": 0,
            "future_per_scope": e["budget"]["per_scope"],
            "future_direct_model_row_evaluations_max": 5120,
            "additional_background_model_queries": 0,
            "tree_internal_evaluations": "Record measured count or null with measurement limitation; unknown is never zero; distinguish row inputs and traversal operations",
            "record": [
                "explainer calls",
                "rows supplied including repeats",
                "unique TRAIN rows",
                "unique T1 rows",
                "direct model calls",
                "direct model row evaluations",
                "measurable internal evaluations",
                "analytical row count",
                "cached/reused outputs",
            ],
            "LR": "Analytical row count, not inflated prediction queries; validation queries counted only when actually made",
            "no_extra_queries_for_local_subset": True,
            "extension": "Separate prospective human authorization; never auto-expand",
        },
    )
    put(
        "missing_value_policy",
        {
            "validate": [
                "NaN",
                "+Inf",
                "-Inf",
                "dtype",
                "feature count",
                "feature order",
            ],
            "NaN": "Preserve supported fitted model missing semantics; otherwise exact frozen imputer only",
            "Inf": "Reject unless explicit frozen predictor semantics prove validity; never silently replace",
            "dtype_count_order_mismatch": "Block scope before any attribution",
            "new_imputer_fit": "FORBIDDEN",
            "SHAP_specific_imputation": "FORBIDDEN",
            "invalid_selected_row": "Keep in failure denominator; no post-attribution replacement",
            "empty_or_unknown_population": "INELIGIBLE; no synthetic padding",
        },
    )
    put(
        "reproducibility_persistence_contract",
        {
            "parent_required": e["persistence"],
            "namespace": "New versioned prospective E1 namespace, content-addressed lossless artifacts; never overwrite Sprint54/55/56.2",
            "persist": [
                "runtime and SHAP/NumPy/SciPy/sklearn/XGB/LGB versions",
                "model digest",
                "preprocessor/vectorizer digest",
                "feature-order digest",
                "background/foreground/local identities and partition/order",
                "raw and exact transformed inputs and their provenance",
                "seed",
                "attribution scale",
                "explainer configuration/background digest",
                "raw attribution arrays",
                "base values",
                "fidelity residuals",
                "stability results",
                "eligibility",
                "figure-data tables",
                "figure hashes",
                "execution counters",
                "SHA-256 manifest",
                "same-row E1/E2 chain records",
            ],
            "large_objects": "Storage location, retention, immutable hashes and access governance fixed before execution; no pointer-only unverified claims",
            "output_schemas_reference": "output_schemas.json",
            "no_overwrite": True,
        },
    )
    put(
        "primary_secondary_analysis_policy",
        {
            "primary": "PERFORMANCE_INDEPENDENT_SCOPE_COMPLETE_ELIGIBLE_UNIVERSE",
            "secondary_label": "POST_HOC_BEST_OBSERVED_MODEL_ANALYSIS",
            "secondary": "Only after primary E1 complete, use stored frozen PR-AUC ranking; ties keep all; no metric recomputation",
            "cannot": [
                "redefine primary universe",
                "replace poor/heterogeneous E1 findings",
                "select on XAI outcomes",
            ],
            "inferential_policy": "Descriptive effects, rank/sign/distribution agreement and coverage; any inference needs separate justified freeze",
        },
    )
    put(
        "manuscript_integration_contract",
        {
            "predictive_layer": "CLOSED",
            "E2": "PRIMARY_ANALYTICAL_FUSION_CORE",
            "E1": "PROSPECTIVE_COMPLEMENTARY",
            "E3": "SEPARATE",
            "sections": [
                "Explainability Protocol",
                "Feature-Level Explanations (E1)",
                "Multimodal Fusion Explanations (E2)",
                "Calibration Interpretation (E3)",
                "Cross-Model Explanation Stability",
                "Cross-Project Explanation Heterogeneity",
                "Local Explanation Case Study",
                "E1–E2 Architectural Continuity",
                "Limitations of Reconstructed-State Explanation",
                "Threats to XAI Validity",
            ],
            "current_scope": "Protocol/design text only; no empirical XAI results",
        },
    )
    put(
        "threats_to_validity",
        {
            "threats": [
                "Reconstructed predictors are not original Sprint54 serialized states",
                "Model explanation is not a causal software-engineering mechanism",
                "Correlated features redistribute attribution",
                "TEXT association does not establish semantic developer intent",
                "Cross-project vocabularies and token semantics differ",
                "Eligibility failures reduce project/modality coverage",
                "RF probability and LR/boosted logit-margin scales differ",
                "Attribution magnitudes require justified normalization before cross-model comparison",
                "Local explanations are case-specific",
                "E2 modality contribution is not E1 feature importance",
                "ApacheJIT benchmark-defined observed labels are not independently verified-clean ground truth",
                "One benchmark family limits external generalization",
                "Balanced capped reference/foreground defines a sample-specific estimand",
                "Identical deterministic repetitions do not establish sampling or background robustness",
                "Historical input provenance remains unresolved and cannot be repaired by policy wording",
            ]
        },
    )
    put(
        "prohibited_claims",
        {
            "allowed": [
                "feature association with model output",
                "relative within-scope attribution importance",
                "model/project-specific explanatory patterns",
                "cross-model disagreement",
                "cross-project heterogeneity",
                "analytical fusion modality contribution",
                "architectural continuity",
                "measured explanation stability",
                "descriptive cross-level co-occurrence when linked",
            ],
            "prohibited": [
                "causal defect causes",
                "causal developer behavior",
                "semantic intent from TEXT",
                "universal software-defect mechanisms",
                "universal feature superiority",
                "universal multimodal superiority",
                "reconstructed states are original Sprint54 models",
                "unvalidated end-to-end E1 decomposition of E2",
                "SHAP proves performance improvement",
                "largest E1 feature caused largest E2 modality contribution",
            ],
        },
    )
    put(
        "execution_counters",
        {
            **dict.fromkeys(ZERO, 0),
            "historical_T1_predictive_access_count": 1,
            "historical_T1_predictive_scoring_count": 1,
            "T2_STATE": "DENY_SEALED_REVIEWER_RESERVE",
            "stage": "PROTOCOL_FREEZE_ONLY",
        },
    )
    put(
        "recommended_next_action",
        {
            "next_sprint": "Sprint 10.8.2.56.3B — Prospective E1 Scientific Input Provenance and Population Eligibility Gate",
            "start_authorized": False,
            "next_scientific_execution_authorized": False,
            "prerequisites": [
                "Human review of this immutable protocol and disclosed 0 execution-eligible scopes",
                "Resolve legitimate non-T2 source provenance without repeated historical recovery",
                "Exact reconstructed-state and representation linkage, including strict TEXT proof",
                "Separate authorization before TRAIN/T1 population materialization",
                "Persist deterministic TRAIN/global/local identities and complete AUTH-E1-1 through AUTH-E1-12",
                "Human authorization of Sprint56.3C scientific attribution only after 56.3B gates pass",
            ],
            "if_source_unavailable": "BLOCK prospective execution; human design review required; no automatic new model training or source substitution",
            "stop_after_56_3A": True,
        },
    )
    put("output_schemas", output_schemas(criteria))
    if p["protocol_summary.json"]["disposition"] == BLOCKED:
        p["recommended_next_action.json"]["immediate_action"] = (
            "Parent integrity provenance review, then re-review Sprint56.3A; do not start56.3B"
        )
        p["recommended_next_action.json"]["blocking_evidence"] = e["parent_log_audit"]
    return p


def output_schemas(criteria):
    """Typed future record contracts, with no scientific result placeholders."""
    common = {
        k: {"type": "string", "minLength": 1}
        for k in [
            "scope_id",
            "project",
            "algorithm_family",
            "modality",
            "protocol_digest",
            "model_digest",
            "preprocessing_digest",
            "feature_order_digest",
            "population_digest",
        ]
    }
    fields = {
        "population": {
            "partition": {"enum": ["TRAIN", "T1"]},
            "row_identity": {"type": "string"},
            "selection_key": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
            "role": {"enum": ["TRAIN_REFERENCE", "GLOBAL", "LOCAL"]},
            "position": {"type": "integer", "minimum": 0},
        },
        "attribution": {
            "row_identity": {"type": "string"},
            "seed": {"type": "integer", "minimum": 20260901, "maximum": 20260920},
            "scale": {
                "enum": ["LOGIT", "POSITIVE_CLASS_PROBABILITY", "NATIVE_RAW_MARGIN"]
            },
            "feature_names": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
            },
            "values": {"type": "array", "items": {"type": "number"}, "minItems": 1},
            **{
                k: {"type": "number"}
                for k in ["base_value", "model_output", "residual"]
            },
            "fidelity_status": {"enum": ["FIDELITY_PASS", "FIDELITY_FAIL"]},
        },
        "global_feature": {
            "feature_name": {"type": "string"},
            "display_name": {"type": "string"},
            "mean_absolute": {"type": "number", "minimum": 0},
            "signed_mean": {"type": "number"},
            "rank": {"type": "integer", "minimum": 1},
            "support_count": {"type": "integer", "minimum": 1},
            "scale": {"type": "string"},
        },
        "sufficiency": {
            "criterion": {"enum": criteria},
            "status": {
                "enum": ["PASS", "PASS_WITH_LIMITATION", "FAIL", "NOT_APPLICABLE"]
            },
            "evidence_reference": {"type": "string", "minLength": 1},
            "reason": {"type": "string", "minLength": 1},
        },
        "stability": {
            "comparison_id": {"type": "string"},
            "metrics": {
                "type": "object",
                "required": [
                    "jaccard_k3",
                    "jaccard_k10",
                    "spearman",
                    "sign_agreement",
                    "TV",
                    "max_absolute_difference",
                ],
                "properties": {
                    k: {"type": ["number", "null"]}
                    for k in [
                        "jaccard_k3",
                        "jaccard_k10",
                        "spearman",
                        "sign_agreement",
                        "TV",
                        "max_absolute_difference",
                    ]
                },
            },
            "undefined_reasons": {"type": "array", "items": {"type": "string"}},
            "status": {
                "enum": [
                    "STABLE",
                    "MIXED_STABILITY",
                    "UNSTABLE",
                    "INSUFFICIENT_EVIDENCE",
                ]
            },
        },
        "bridge": {
            "configuration": {"enum": ["C+P", "C+T", "P+T", "C+P+T"]},
            "row_link_digest": {"type": ["string", "null"]},
            "E2_evidence_digest": {"type": ["string", "null"]},
            "status": {
                "enum": [
                    "BRIDGE_CONSISTENT",
                    "BRIDGE_PARTIALLY_CONSISTENT",
                    "BRIDGE_DIVERGENT",
                    "BRIDGE_INSUFFICIENT_E1",
                    "BRIDGE_INSUFFICIENT_E2",
                ]
            },
            "continuity_label": {"type": "string"},
            "reason": {"type": "string"},
        },
    }
    return {
        "schema_version": "1.0.0",
        "schemas": {
            name: {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
                "required": list(common) + list(extra),
                "properties": {**common, **extra},
                "additionalProperties": False,
            }
            for name, extra in fields.items()
        },
        "semantic_validation": [
            "Finite numbers only",
            "Attribution length equals ordered feature count",
            "All row identities belong to authorized population; local subset global",
            "Digest references resolve to immutable validated files",
            "No row record from T2",
            "No schema-valid record alone proves scientific eligibility",
        ],
    }


def report(p, parent):
    sections = [
        (
            "A. Branch and parent",
            f"Branch `{parent['branch']}`; HEAD `{parent['HEAD']}`. Clean preflight; merge parents {parent['merge_parents']}. Eleven packages present; metadata hashes verified. Scientific payload files were not opened to hash them.",
        ),
        (
            "B. Scientific state preserved",
            "Sprint54 predictive evidence closed; MIXED_CONFIRMATORY_EVIDENCE; historical T1 access/scoring 1/1. G5 equivalence is reconstructed-state evidence, never original Sprint54 serialization. E2 remains primary; E3 separate; historical E1 illustrative and recovery closed.",
        ),
        (
            "C. E1 unit of analysis",
            "Project × algorithm family × unimodal modality. Performance-independent scope-complete eligible universe.",
        ),
        ("D. Eligible algorithm families", ", ".join(FAMILIES)),
        (
            "E. Eligible modalities",
            "CODE, PROCESS, TEXT; no pairwise/full multimodal feature attribution.",
        ),
        (
            "F. Candidate scope universe",
            f"168 candidates across 14 projects. Classification: {p['protocol_summary.json']['eligibility_counts']}. 168 have parent reconstructed-state equivalence; zero are scientifically execution-eligible now. TEXT requires complete representation/alignment proof, not just an available vectorizer.",
        ),
        (
            "G. E1 method mapping",
            "LR analytical logit decomposition; RF exact positive-class probability TreeSHAP; XGBoost/LightGBM exact native raw-margin TreeSHAP. LIME/counterfactuals excluded. Runtime is the existing isolated Sprint56.1 lock.",
        ),
        (
            "H. LR analytical contract",
            "phi_j=beta_j*(x_j-mu_j); phi_0=intercept+sum(beta_j*mu_j). mu is the selected transformed TRAIN reference mean. Global importance mean|phi|; raw coefficient magnitude diagnostic only.",
        ),
        (
            "I. TreeSHAP contract",
            "Inherit tree_path_dependent, model_output=raw, data=None, approximate=False. Persisted TRAIN path counts define tree references; capped explicit TRAIN rows do not silently change the TreeSHAP estimand. RF class 1 probability; boosters raw margin. Every explained row checked.",
        ),
        (
            "J. TRAIN background policy",
            "At most 256 observed rows per project/modality, shared across families where representations permit. All if small, otherwise equal round-robin binary TRAIN-label strata if authorized; identity-only fallback. Seed 20260901, SHA-256 lexical ordering; no kmeans. Class balancing defines the reference estimand, not full-TRAIN prevalence.",
        ),
        (
            "K. T1 global foreground policy",
            "At most 256. T1_SELECTION_LABEL_BLIND; frozen predicted-decision strata if complete, otherwise identity-only. No labels, errors, metrics or attribution selection. Only exact authorized T1 representations; new populations cannot silently replace historical T1.",
        ),
        (
            "L. Local case policy",
            "At most eight, subset of global: four per available predicted class, high confidence, near threshold, median confidence, remaining integrity-supported extreme; deterministic ties and quota fallback. Correct/error annotation deferred to separate label permission after selection.",
        ),
        (
            "M. TEXT contract",
            "Exact vocabulary, IDF, tokenizer settings, column order, predictor alignment and row representations required. Missing proof means TEXT_E1_INELIGIBLE. Keep absent-token contributions where method produces them. No token-rank pooling or intent claims.",
        ),
        (
            "N. CODE/PROCESS feature contract",
            "Twelve authoritative features frozen with definitions, units/unknown units, transforms, sign limits, missing policies and provenance. Parent PROCESS replay semantics and age/entropy/recency unit details remain explicitly unresolved; no silent reclassification or invented Git proxy.",
        ),
        (
            "O. Correlated-feature policy",
            "TRAIN-only absolute Spearman rho>=0.70 connected components; no TEXT grouping. Sum member contributions per row before mean absolute group aggregation, plus within-group shares and cancellation diagnostics. Do not overinterpret small correlated rank swaps.",
        ),
        (
            "P. Fidelity",
            "Inherited LR residual <=1e-10*(1+|eta|), sigmoid bound 1e-10; trees <=1e-6*(1+|output|); global reconstruction 1e-12. Zero unexplained fraction permitted. PASS/MIXED/FAIL/NOT_TESTED exact rules; only complete PASS admitted.",
        ),
        (
            "Q. Stability",
            "Seeds 20260901–20260920; identical populations, all 190 repeat pairs, deterministic difference<=1e-12. Top3/top10; Jaccard>=.60, Spearman>=.70, sign>=.80, TV<=.25 on comparable support. Degenerate metrics are insufficient, not passes. No claim of sampling robustness from identical reruns.",
        ),
        (
            "R. Heterogeneity",
            "Within-project cross-model, within-model cross-project, modality synthesis. >=3 comparable families; inherited cross-project >=11 passing projects and <=1 material reversal. Raw cross-scale pooling forbidden; universal claim requires all14/all4 with no reversal. Descriptive primary analysis.",
        ),
        (
            "S. E1–E2 continuity",
            "Features -> representation -> base model -> probability -> fusion -> multimodal prediction. Architectural continuity is design-level; directional/project/model labels require exact linked future evidence. Never propagate/add E1 SHAP values through E2 or equate feature importance with modality contribution.",
        ),
        (
            "T. E1–E2 bridge",
            "Compare stable E1 patterns and strongest E2 modality descriptively, only with exact common chain. Five bridge statuses distinguish consistency, partial consistency, divergence, insufficient E1 and insufficient E2. Historical/prospective panels cannot imply a shared row without proof.",
        ),
        (
            "U. Figures",
            "Eight frozen families: E1-G1,G2,G3,L1,L2,C1,T1,E2. Every panel requires counts, family, modality, scale, normalization, omissions and descriptive label. No figures generated; correct/error L2 conditional on separate label authorization.",
        ),
        (
            "V. Q1 sufficiency gate",
            "Eighteen criteria, hard provenance/fidelity/repeatability/completeness/traceability gates, explicit small-sample and multi-project/family coverage rules. Four future E1_Q1 dispositions defined but none assigned now. Successful SHAP execution alone never suffices.",
        ),
        (
            "W. Governance and counters",
            "All current scientific execution/access/mutation counters zero; historical predictive counters 1/1. T2 DENY_SEALED_REVIEWER_RESERVE, future budget0. AUTH-E1-1 through12 plus source proof and explicit human approval required. Future budgets:256 TRAIN,256 unique T1,8 local subset,20 repeats,5120 attribution row evaluations and at most5120 direct model row evaluations.",
        ),
        (
            "X. Threats to validity",
            "\n".join("- " + x for x in p["threats_to_validity.json"]["threats"]),
        ),
        (
            "Y. Prohibited claims",
            "\n".join("- " + x for x in p["prohibited_claims.json"]["prohibited"]),
        ),
        (
            "Z. Final disposition / next action",
            p["protocol_summary.json"]["disposition"]
            + ". Contracts are prepared and persisted for review, with zero currently executable scopes. Parent integrity finding: "
            + json.dumps(
                p["protocol_summary.json"]["parent_integrity_finding"], sort_keys=True
            )
            + ". Resolve the inherited manifest discrepancy through a separately reviewed provenance amendment; do not rewrite parent artifacts. Then re-review 56.3A before any next sprint. Planned next sprint: "
            + p["recommended_next_action.json"]["next_sprint"]
            + ". Human review, legitimate source proof, representation/identity alignment and separate population-access authorization are prerequisites. If no legitimate source is available, stop for design review; do not reopen historical recovery, train, refit, recalibrate or start attribution. See validation_results.json for the sealed validation record.",
        ),
    ]
    return (
        "# Sprint 10.8.2.56.3A — Prospective Complementary E1 Protocol Freeze\n\n"
        + "Disposition: **"
        + p["protocol_summary.json"]["disposition"]
        + "**. "
        + "The immutable package records the proposed contracts and audit outcome. A BLOCKED disposition means protocol acceptance has not passed; references below to frozen designs do not authorize their execution. Parent evidence remains untouched.\n\n"
        + "\n\n".join("## " + title + "\n\n" + text for title, text in sections)
        + (
            "\n\nBLOCKED — DO NOT START PROSPECTIVE E1 EXECUTION\n"
            if p["protocol_summary.json"]["disposition"] == BLOCKED
            else "\n\nREADY FOR HUMAN REVIEW BEFORE PROSPECTIVE E1 EXECUTION AUTHORIZATION\n"
        )
    ).encode()


def serialize(p):
    return {
        name: (
            b"".join(
                (
                    json.dumps(r, sort_keys=True, ensure_ascii=False, allow_nan=False)
                    + "\n"
                ).encode()
                for r in value
            )
            if name.endswith(".jsonl")
            else encode(value)
        )
        for name, value in p.items()
    }


def manifest_bytes(files):
    return "".join(
        f"{digest(raw)}  {name}\n" for name, raw in sorted(files.items())
    ).encode()


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def publish(preflight, validation, output=OUT):
    """No overwrite. Validate everything before creating the package directory."""
    if preflight["branch"] != BRANCH or preflight["initial_status"] != "":
        raise ProtocolBlocked("Clean expected-branch preflight required")
    if (
        git("rev-parse", "--abbrev-ref", "HEAD") != BRANCH
        or git("rev-parse", "HEAD") != preflight["HEAD"]
    ):
        raise ProtocolBlocked("Branch/HEAD differs from clean preflight")
    if git("diff", "--name-only") or git("diff", "--cached", "--name-only"):
        raise ProtocolBlocked("Tracked parent changes exist")
    if len(git("rev-list", "--parents", "-n", "1", "HEAD").split()) != 3:
        raise ProtocolBlocked("Expected merge parent missing")
    e, hashes = load_evidence()
    for path, h in preflight["required_package_manifest_hashes"].items():
        if hashes.get(path) != h:
            raise ProtocolBlocked("Parent manifest changed since preflight")
    # Anchor every metadata input to the parent commit without reading model/T1 payloads.
    for path in hashes:
        tree = git("ls-tree", "HEAD", "--", path).split()
        if len(tree) < 3 or tree[1] != "blob":
            raise ProtocolBlocked("Parent input absent in HEAD: " + path)
        raw = MetadataReader(ROOT).read(path)
        blob_id = hashlib.sha1(
            b"blob " + str(len(raw)).encode() + b"\0" + raw
        ).hexdigest()
        if tree[2] != blob_id:
            raise ProtocolBlocked("Metadata differs from committed parent: " + path)
    p = compile_protocol(e)
    if validation.get("status") != "PASS":
        p["protocol_summary.json"]["disposition"] = BLOCKED
        p["protocol_summary.json"]["protocol_acceptance"] = (
            "BLOCKED_PENDING_VALIDATION_RESOLUTION"
        )
    parent = {
        **preflight,
        "metadata_hashes_before": hashes,
        "verification_scope": "Required package manifests and exact allowlisted metadata; scientific payloads deliberately not read",
        "all_metadata_matches_parent_git_blobs": True,
        "parent_manifest_content_finding": e["parent_log_audit"],
        "full_parent_package_manifest_pass_claimed": False,
    }
    _, after = load_evidence()
    if hashes != after:
        raise ProtocolBlocked("Parent metadata changed during compilation")
    parent["metadata_hashes_after"] = after
    p["parent_integrity.json"] = parent
    p["validation_results.json"] = validation
    p["access_log.json"] = {
        "metadata_paths_and_hashes": hashes,
        "scientific_payload_reads": 0,
        "model_deserialization": 0,
    }
    p["implementation_provenance.json"] = {
        "source_sha256": digest(Path(__file__).read_bytes()),
        "test_sha256": digest(
            (
                ROOT / "tests/evaluation/test_q1_prospective_e1_protocol_freeze.py"
            ).read_bytes()
        ),
        "regression_runner_sha256": digest(
            (
                ROOT
                / "tests/evaluation/run_q1_prospective_e1_governance_regressions.py"
            ).read_bytes()
        ),
        "runtime": "Existing .venv Python; standard-library compiler; no installation",
    }
    files = serialize(p)
    files["SPRINT56_3A_PROSPECTIVE_E1_PROTOCOL_FREEZE_REPORT.md"] = report(p, parent)
    files["MANIFEST.sha256"] = manifest_bytes(files)
    output = Path(output)
    if output.resolve() != OUT.resolve():
        raise ProtocolBlocked("Publication restricted to new sprint namespace")
    output.mkdir(parents=True, exist_ok=False)
    for name, raw in sorted(files.items()):
        with (output / name).open("xb") as handle:
            handle.write(raw)
    # Validate the newly persisted package, including exact file-set coverage.
    actual = {
        path.name: path.read_bytes() for path in output.iterdir() if path.is_file()
    }
    if actual != files:
        raise ProtocolBlocked("Published package differs from compiled bytes")
    return p["protocol_summary.json"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--validation", type=Path, required=True)
    args = parser.parse_args()
    try:
        summary = publish(
            json.loads(args.preflight.read_bytes()),
            json.loads(args.validation.read_bytes()),
        )
    except (ProtocolBlocked, OSError, KeyError, ValueError) as error:
        parser.exit(1, "PROSPECTIVE_E1_PROTOCOL_FREEZE_BLOCKED: " + str(error) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
