#!/usr/bin/env python3
"""Materialize the Sprint 55 XAI runtime freeze without executing XAI.

The module reads governance metadata and installed-package metadata only.  It
has no data loading, model query, explainer import, attribution, fitting,
calibration, metric, T1-row, or T2 path.
"""

# ruff: noqa: E501

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

VERSION = "q1-xai-runtime-freeze-1.0.0"
BRANCH = "sprint-10/q1-xai-governance-protocol"
OUTPUT_REL = Path("audits/q1-xai-runtime-freeze/1.0.0")
G5_REL = Path("audits/q1-xai-final-output-equivalence-g5/1.0.0")
READY = "FUTURE_PRIMARY_XAI_STATE_READY_PENDING_SEPARATE_RUNTIME_AND_EXECUTION_AUTHORIZATION"
OUTCOME = "SHAP_RUNTIME_VERSION_UNRESOLVED"
EXCLUDED = {
    ("apache/zeppelin", "Logistic Regression", "C+T"),
    ("apache/zeppelin", "Logistic Regression", "P+T"),
    ("apache/zeppelin", "Logistic Regression", "C+P+T"),
}
THREAD_ENV = {
    "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1",
    "VECLIB_MAXIMUM_THREADS": "1",
}
FROZEN_HASHES = {
    "sprint54_t1_prediction_evidence": ("audits/q1-t1-confirmatory-execution/1.0.0/results/t1_prediction_evidence.jsonl.gz", "eb4b6956b185e63cd322d92b8cdf96f53fcb09ef83b6a16f2334d660c6f5adc8"),
    "sprint54_manifest": ("audits/q1-t1-confirmatory-execution/1.0.0/MANIFEST.sha256", "f4f910a5144241b53f7f741ab2e49a5cb541abd8cff88f72c7a05ee30ecaeedf"),
    "block6_manifest": ("audits/q1-xai-reconstruction-equivalence-protocol/1.0.0/MANIFEST.sha256", "17341b4a585baab73118f21cc1056914326b61cba6751b16ff91bdf4b3dfc386"),
    "block6a_manifest": ("audits/q1-xai-reconstruction-equivalence-protocol/1.0.0/amendments/historical_design_rationale/1.0.0/MANIFEST.sha256", "c9502cb1ec85d3053b8a972d61657038e66d04fb5e619b0fe08ed94d581c91bb"),
    "block7_manifest": ("audits/q1-xai-reconstruction-execution/1.0.0/MANIFEST.sha256", "994a6f7aa8d1393904c605e0b5d65db6fcd39b9be55a1eb5219f899346b83d2e"),
    "block7_results": ("audits/q1-xai-reconstruction-execution/1.0.0/g1_g2_g3_results.json", "c07a0bd18d1c73e2cddae0ca829de3dd9e698b233d5d27f3f3f8928fb153f8a5"),
    "block7a_manifest": ("audits/q1-xai-reconstruction-execution/1.0.0/forensics/g3_failure_root_cause/1.0.0/MANIFEST.sha256", "a6f4bd5e5ec43f844860283aef6b3f21933728a5d0817773e7cb1fb742b866e7"),
    "block7b_manifest": ("audits/q1-xai-reconstruction-execution/1.0.0/dispositions/block7b_partial_eligibility/1.0.0/MANIFEST.sha256", "6e74700b5deeafb4e70d4e46a07a920df37372aa1f52fd1d17b26d3a7a2fdbeb"),
    "block8_manifest": ("audits/q1-xai-reconstruction-equivalence-g4/1.0.0/MANIFEST.sha256", "158f52c8cd16e633d11202a86dff467d33838e84617aeaf64d94c361a66f3074"),
    "block8_results": ("audits/q1-xai-reconstruction-equivalence-g4/1.0.0/g4_scope_results.jsonl", "0320dcdf3eb73b5b242a4223292c9708074e6e24f33f4757a9ebe582a9e9d5c1"),
    "g5_manifest": ("audits/q1-xai-final-output-equivalence-g5/1.0.0/MANIFEST.sha256", "a0eaa7d0e0e6e3a119160bab2709f5f16319f6429fdd5cc16e72db311f851f10"),
    "g5_scope_results": ("audits/q1-xai-final-output-equivalence-g5/1.0.0/g5_scope_results.jsonl", "1f3ea876869fa969943843a53d9a5068ed71688c9b3f0a59e20f88773aab6eed"),
    "g5_readiness": ("audits/q1-xai-final-output-equivalence-g5/1.0.0/xai_readiness_ledger.jsonl", "7b213e30bbdd4347d27338400d89d602163e2e50973b6ad2bbd4197003b75dc2"),
    "g5_method_policy": ("audits/q1-xai-final-output-equivalence-g5/1.0.0/xai_method_policy_freeze.json", "8038611cf49ca14546942da660016a6ea0f6e154df33696ec1b5c1f0eacc4073"),
    "g5_shap_readiness": ("audits/q1-xai-final-output-equivalence-g5/1.0.0/shap_runtime_readiness.json", "e9fc98f439aa0a7493c997f7473ef94c1c02e3d3dcbe979b511beb8c75980e6e"),
    "tolerance_policy": ("audits/q1-xai-reconstruction-equivalence-protocol/1.0.0/numerical_tolerance_policy.json", "62fd3780c94c6a69bfc036bdd4b567409ffc46c8c892a807b221f5d40d0eb336"),
    "calibration_policy": ("audits/q1-heldout-governance-calibration-freeze/1.0.0/frozen_calibration_policy.json", "b1fcce1e0dc5178ecf0606ddba3263add308db0da959c58a5addc136ebcefc25"),
}


class FreezeError(RuntimeError):
    """Fail-closed runtime-freeze integrity error."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(canonical_bytes(value) + b"\n")
    os.replace(temporary, path)


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def verify_parents(root: Path) -> dict[str, Any]:
    result = {}
    for name, (relative, expected) in FROZEN_HASHES.items():
        actual = sha256(root / relative)
        if actual != expected:
            raise FreezeError(f"immutable parent mismatch: {name}: {actual}")
        result[name] = {"path": relative, "sha256": actual, "status": "PASS_EXACT_SHA256"}
    return result


def load_universe(root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = [json.loads(line) for line in (root / G5_REL / "xai_readiness_ledger.jsonl").read_text().splitlines() if line]
    identities = {row["model_identity_sha256"] for row in rows}
    scopes = {(row["project"], row["algorithm"], row["configuration"]) for row in rows}
    if len(rows) != 389 or len(identities) != 389 or any(row["future_xai_readiness"] != READY for row in rows):
        raise FreezeError("G5 future-XAI universe is not exactly 389 unique ready identities")
    if scopes & EXCLUDED:
        raise FreezeError("a G3-excluded scope entered the runtime freeze")
    summary = json.loads((root / G5_REL / "g5_summary.json").read_text())
    if summary["g5_outcome"] != "FULL_G5_FINAL_OUTPUT_EQUIVALENCE_XAI_READINESS_ESTABLISHED":
        raise FreezeError("G5 starting outcome changed")
    return rows, summary


def package_inventory() -> dict[str, Any]:
    packages = sorted(
        ({"name": dist.metadata["Name"], "version": dist.version} for dist in importlib.metadata.distributions()),
        key=lambda row: row["name"].lower(),
    )
    return {
        "packages": packages,
        "package_count": len(packages),
        "canonical_inventory_sha256": hashlib.sha256(canonical_bytes(packages)).hexdigest(),
    }


def verify_predictive_runtime(inventory: dict[str, Any]) -> None:
    installed = {row["name"].lower(): row["version"] for row in inventory["packages"]}
    expected = {
        "numpy": "2.4.6", "scipy": "1.17.1", "scikit-learn": "1.9.0",
        "xgboost": "3.2.0", "lightgbm": "4.6.0",
    }
    if platform.python_version() != "3.11.14":
        raise FreezeError(f"frozen Python changed: {platform.python_version()}")
    if {name: installed.get(name) for name in expected} != expected:
        raise FreezeError("frozen predictive dependency version changed")


def contracts() -> dict[str, Any]:
    deterministic_selection = {
        "seed": 20260901,
        "stable_key": "SHA256(canonical_JSON(seed,purpose,project,model_identity_sha256,row_identifier))",
        "within_stratum_selection": "ascending stable_key; take allocated count",
        "final_order": "ascending stable_key",
        "allocation": "equal integer allocation across available binary strata; deterministically reallocate unused quota",
        "performance_independent": True,
        "explanation_independent": True,
    }
    explainer = {
        "schema_version": VERSION,
        "execution_authorized": False,
        "E1_unimodal": {
            "Logistic Regression": {"primary_method": "ANALYTICAL_LINEAR_LOGIT_DECOMPOSITION", "scale": "LOGIT", "global": "MEAN_ABSOLUTE_CENTERED_LOGIT_CONTRIBUTION", "local": "EXACT_ANALYTICAL_LOGIT_DECOMPOSITION", "coefficient_magnitude": "DIAGNOSTIC_ONLY", "optional_cross_check": "LINEARSHAP_ONLY_AFTER_SEPARATE_AUTHORIZATION_AND_NUMERICAL_EQUIVALENCE"},
            "Random Forest": {"primary_method": "EXACT_TREESHAP_POSITIVE_CLASS_OUTPUT", "explainer": "TreeSHAP", "scale": "POSITIVE_CLASS_MODEL_OUTPUT_PER_FROZEN_RF_CONTRACT", "approximate": False, "impurity_importance": "DIAGNOSTIC_ONLY_NOT_SHAP"},
            "XGBoost": {"primary_method": "EXACT_TREESHAP_NATIVE_RAW_MARGIN", "explainer": "TreeSHAP", "scale": "NATIVE_RAW_MARGIN", "approximate": False},
            "LightGBM": {"primary_method": "EXACT_TREESHAP_NATIVE_RAW_MARGIN", "explainer": "TreeSHAP", "scale": "NATIVE_RAW_MARGIN", "approximate": False},
        },
        "E2_multimodal": {"primary_method": "ANALYTICAL_LR_FUSION_DECOMPOSITION", "scale": "META_LOGIT", "eta": "alpha + sum(beta_m * p_m)", "local_contribution": "c_m = beta_m * p_m", "centered_contribution": "phi_m = beta_m * (p_m - mu_m)", "baseline": "phi_0 = alpha + sum(beta_m * mu_m)", "mu_source": "same-project frozen TRAIN-reference mean unimodal probability", "sigmoid_probability": "REPORT_SEPARATELY_NOT_ADDITIVE_SCALE", "naive_concatenated_feature_shap": "FORBIDDEN", "causal_interpretation": "FORBIDDEN"},
        "E3_calibration": {"separate_from_E1_E2": True, "RAW": "E3_IDENTITY_MAPPING_READY", "ISOTONIC": "E3_FROZEN_MAPPING_INSPECTION_READY", "feature_assignment_through_calibration": "FORBIDDEN", "shap_through_isotonic": "FORBIDDEN"},
        "LIME_PRIMARY_STATUS": "EXCLUDED_FROM_PRIMARY_XAI",
        "LIME_future_status": "EXPLORATORY_NON_CONFIRMATORY_XAI_REQUIRES_SEPARATE_AUTHORIZATION",
        "counterfactual_status": "EXCLUDED_FROM_SPRINT56_PRIMARY_XAI_REQUIRES_SEPARATE_PROTOCOL",
    }
    population = {
        "schema_version": VERSION, "selection_execution_in_freeze": False,
        "TRAIN_background": {"source": "SAME_PROJECT_TRAIN_ONLY", "maximum_rows_per_scope": 256, "stratification": "TRAIN_LABEL_WHERE_APPLICABLE", "T1_label_use": False, "T2_use": False, **deterministic_selection, "analytical_centering_reference": True, "TreeSHAP_background": "USE_ONLY_WHEN_FROZEN_EXPLAINER_SEMANTICS_REQUIRE; OTHERWISE RECORD_NOT_REQUIRED"},
        "T1_global_foreground": {"source": "T1_ONLY", "maximum_rows_per_scope": 256, "stratification": "FROZEN_PREDICTED_DECISION_WHERE_AVAILABLE; OTHERWISE_UNSTRATIFIED", "label_use": False, "correctness_or_performance_use": False, "T2_use": False, **deterministic_selection},
    }
    local = {
        "schema_version": VERSION, "selection_execution_in_freeze": False, "source": "SUBSET_OF_FROZEN_T1_GLOBAL_FOREGROUND", "maximum_rows_per_scope": 8,
        "strata": "FROZEN_PREDICTED_POSITIVE_AND_NEGATIVE_WHERE_AVAILABLE; OTHERWISE_UNSTRATIFIED", "target_allocation": "4/4 WITH DETERMINISTIC UNUSED-QUOTA_REALLOCATION", "label_use": False,
        "post_attribution_selection": "FORBIDDEN", **deterministic_selection,
    }
    query = {
        "schema_version": VERSION, "execution_in_freeze": False,
        "per_scope": {"TRAIN_background_unique_rows_max": 256, "T1_global_foreground_unique_rows_max": 256, "T1_local_cases_max": 8, "local_cases_are_foreground_subset": True, "unique_model_input_rows_max": 512, "fidelity_checks": "EVERY_EXPLAINED_ROW", "stability_repetitions": 20, "primary_attribution_row_evaluations_max_including_stability": 5120},
        "T2_queries": 0, "budget_extension": "REQUIRES_NEW_PROSPECTIVE_HUMAN_AUTHORIZATION",
    }
    fidelity = {
        "schema_version": VERSION,
        "analytical_LR": {"identity": "eta = intercept + sum(feature_contributions)", "residual_bound": "abs(residual) <= 1e-10 * (1 + abs(eta))", "sigmoid_bound": "abs(sigmoid(eta) - model_probability) <= 1e-10", "failure": "XAI_FAIL_FIDELITY"},
        "TreeSHAP": {"identity": "base_value + sum(SHAP_values) = model_output_on_frozen_scale", "residual_bound": "abs(residual) <= 1e-6 * (1 + abs(model_output))", "approximate": "FORBIDDEN", "failure": "XAI_FAIL_ADDITIVITY"},
        "global": {"aggregation": "MEAN_ABSOLUTE_ATTRIBUTION_ON_FROZEN_FOREGROUND", "also_store": ["SIGNED_MEAN_ATTRIBUTION", "RANK", "SUPPORT_COUNT"], "reconstruction_tolerance": 1e-12},
    }
    stability = {
        "schema_version": VERSION, "seeds": list(range(20260901, 20260921)), "population_reselection_by_stability_seed": False,
        "deterministic_method_max_absolute_attribution_difference": 1e-12, "top_k": [3, 10], "metrics": ["JACCARD_OVERLAP", "SPEARMAN_RANK_CORRELATION", "SIGN_AGREEMENT", "TOTAL_VARIATION_DISTANCE"], "post_result_threshold_change": "FORBIDDEN",
    }
    text = {
        "schema_version": VERSION, "required_G5_state": "TEXT_FEATURE_ATTRIBUTION_STATE_READY", "required_evidence": ["TFIDF_VOCABULARY", "IDF", "TOKEN_TO_COLUMN_MAPPING", "FEATURE_ORDER", "PREDICTOR_ALIGNMENT", "REPRESENTATION_DIGEST"],
        "Logistic Regression": "ANALYTICAL_TFIDF_FEATURE_CONTRIBUTION", "tree_families": "TREESHAP_ON_EXACT_FROZEN_TFIDF_SPACE", "token_labels": "PRESERVE_EXACT_VOCABULARY_LABELS", "semantic_intent_inference": "FORBIDDEN", "cross_project_rank_averaging": "FORBIDDEN_UNLESS_EXACT_REPRESENTATION_COMPATIBILITY_EVIDENCED",
    }
    correlated = {
        "schema_version": VERSION, "modalities": ["CODE", "PROCESS"], "evidence_source": "TRAIN_ONLY", "measure": "SPEARMAN_RHO", "absolute_threshold": 0.70,
        "group_construction": "CONNECTED_COMPONENTS_OF_UNDIRECTED_PAIRWISE_THRESHOLD_GRAPH; SINGLETONS_NOT_REPORTED_AS_CORRELATED_GROUPS", "freeze_timing": "BEFORE_ATTRIBUTION_INTERPRETATION", "outputs": ["INDIVIDUAL_ATTRIBUTIONS", "GROUPED_ATTRIBUTION_SUMMARIES"], "causal_responsibility_claim": "FORBIDDEN",
    }
    heterogeneity = {
        "schema_version": VERSION,
        "cross_model": {"minimum_eligible_comparable_algorithm_families": 3, "thresholds": {"Jaccard": 0.60, "Spearman": 0.70, "sign_agreement": 0.80, "total_variation_max": 0.25}, "failure_labels": ["MODEL_DEPENDENT", "HETEROGENEOUS"], "family_reselection": "FORBIDDEN"},
        "cross_project": {"fewer_than_projects": 3, "insufficient_label": "INSUFFICIENT_PROJECT_SUPPORT", "stable_minimum_pass_projects": 11, "eligible_project_universe": 14, "maximum_material_reversal_projects": 1, "otherwise": ["PROJECT_SPECIFIC", "HETEROGENEOUS", "MODEL_DEPENDENT"], "universal_claim": "ALL_ELIGIBLE_PROJECTS_AND_ALL_APPLICABLE_ALGORITHM_FAMILIES_REQUIRED"},
        "performance_independent": True,
    }
    return {"explainer_contract.json": explainer, "explanation_population_policy.json": population, "local_case_selection_policy.json": local, "query_budget_policy.json": query, "xai_fidelity_contract.json": fidelity, "xai_stability_contract.json": stability, "text_attribution_contract.json": text, "correlated_feature_policy.json": correlated, "heterogeneity_interpretation_policy.json": heterogeneity}


def report(head: str, timestamp: str) -> str:
    return f"""# Sprint 55 XAI Runtime Freeze Report

## Disposition

`{OUTCOME}`

The complete explainer, population, ordering, query-budget, fidelity, stability, interpretation, T1, and T2 contracts are frozen. No SHAP release can currently be selected without changing the frozen predictive runtime: SHAP 0.52.0 requires Python >=3.12, while SHAP 0.51.0 on Darwin x86_64 requires Numba <0.63 and Numba 0.62.1 requires NumPy <2.4, conflicting with frozen NumPy 2.4.6. Installation and execution therefore remain prohibited pending a separate prospective human decision.

## A–Z record

- **A — Branch and HEAD:** `{BRANCH}` at `{head}`.
- **B — Starting G5 state:** `FULL_G5_FINAL_OUTPUT_EQUIVALENCE_XAI_READINESS_ESTABLISHED`.
- **C — XAI universe:** 389 unique G5-ready scopes, verified from the frozen ledger.
- **D — Exclusions:** Zeppelin Logistic Regression `C+T`, `P+T`, and `C+P+T` remain excluded.
- **E — Runtime:** Python 3.11.14; NumPy 2.4.6; SciPy 1.17.1; scikit-learn 1.9.0; XGBoost 3.2.0; LightGBM 4.6.0; Darwin x86_64.
- **F — SHAP:** no version selected; authoritative package metadata proves the current incompatibility chain. Status `{OUTCOME}`.
- **G — Installation:** none; before/after package inventories are identical.
- **H — Explainers:** analytical LR logit decomposition; exact RF TreeSHAP positive-class output; exact XGBoost/LightGBM TreeSHAP native raw margin; analytical LR fusion decomposition.
- **I — Scales:** LOGIT, frozen RF positive-class model output, NATIVE_RAW_MARGIN, and META_LOGIT respectively.
- **J — TRAIN background:** same-project TRAIN only, maximum 256, deterministic stratification and SHA-256 ordering, seed 20260901.
- **K — T1 foreground:** T1 only, maximum 256, performance/explanation independent, no labels, deterministic frozen-decision strata and SHA-256 ordering.
- **L — Local cases:** foreground subset, maximum 8, frozen-decision 4/4 allocation with deterministic reallocation; never selected after attribution.
- **M — Budget:** maximum 256 TRAIN background and 256 unique T1 foreground rows per scope; local 8 are a subset; fidelity on every explained row; no T2.
- **N — LR fidelity:** decomposition residual <= `1e-10*(1+abs(eta))`; sigmoid residual <= `1e-10`.
- **O — TreeSHAP additivity:** residual <= `1e-6*(1+abs(model_output))`; approximate mode forbidden.
- **P — TEXT:** only G5-aligned frozen TF-IDF state; exact vocabulary/token-column/IDF/order/predictor linkage; no semantic-intent inference.
- **Q — Correlation:** TRAIN-only CODE/PROCESS Spearman groups at absolute rho >=0.70, connected-component grouping, individual and grouped summaries.
- **R — Stability:** seeds 20260901–20260920; deterministic maximum difference 1e-12; top-k 3/10 with Jaccard, Spearman, sign agreement, and total variation.
- **S — Cross-model:** at least three comparable eligible families; frozen 0.60/0.70/0.80/0.25 thresholds.
- **T — Projects:** fewer than three is insufficient; stability requires at least 11/14 projects and at most one material reversal.
- **U — E3:** RAW identity and frozen isotonic inspection remain separate from E1/E2; no feature attribution through calibration.
- **V — LIME:** excluded from primary XAI; exploratory use requires separate authorization.
- **W — Counterfactuals:** excluded from Sprint 56 primary XAI and require a separate protocol.
- **X — T1:** no T1 rows accessed in this freeze; future use is separately counted `TECHNICAL_EXPLANATION_ACCESS`; historical counters remain 1/1/false.
- **Y — T2:** access count 0; state `DENY_SEALED_REVIEWER_RESERVE`.
- **Z — Sprint 56 prerequisites:** resolve and prospectively amend the SHAP version/runtime conflict without silent predictive-stack mutation; freeze package provenance and hashes; obtain separate execution authorization; verify all parent hashes and thread controls; materialize populations before attribution; retain zero T2 access.

Timestamp: `{timestamp}`. XAI, SHAP, LIME, analytical attribution, T1 explanation, T2 access, fitting, reconstruction, recalibration, and metric-recomputation counts are all zero.
"""


def run(root: Path) -> Path:
    branch = git(root, "symbolic-ref", "--short", "HEAD")
    head = git(root, "rev-parse", "HEAD")
    if branch != BRANCH:
        raise FreezeError(f"wrong branch: {branch}")
    parents_before = verify_parents(root)
    universe, g5_summary = load_universe(root)
    before = package_inventory()
    verify_predictive_runtime(before)
    if any(row["name"].lower() in {"shap", "lime"} for row in before["packages"]):
        raise FreezeError("G5 package absence premise changed")
    timestamp = datetime.now(UTC).isoformat()
    output = root / OUTPUT_REL
    output.mkdir(parents=True, exist_ok=True)

    runtime = {
        "schema_version": VERSION, "outcome": OUTCOME, "timestamp_utc": timestamp, "branch": branch, "git_HEAD": head,
        "platform": platform.platform(), "system": platform.system(), "architecture": platform.machine(), "python": platform.python_version(), "python_executable": sys.executable,
        "frozen_predictive_runtime": {"Python": "3.11.14", "NumPy": "2.4.6", "SciPy": "1.17.1", "scikit-learn": "1.9.0", "XGBoost": "3.2.0", "LightGBM": "4.6.0"},
        "thread_environment_required": THREAD_ENV, "thread_environment_observed_during_freeze": {name: os.environ.get(name) for name in THREAD_ENV}, "thread_environment_enforcement_time": "MANDATORY_BEFORE_ANY_FUTURE_POPULATION_OR_ATTRIBUTION_EXECUTION", "deterministic_ordering": ["projects", "algorithms", "configurations", "features", "rows", "background_rows", "foreground_rows", "local_cases"],
        "g5_ready_scope_count": len(universe), "excluded_scope_count": 3, "identity_universe_sha256": hashlib.sha256(canonical_bytes(sorted(row["model_identity_sha256"] for row in universe))).hexdigest(),
        "historical_states": {"Sprint54": "MIXED_CONFIRMATORY_EVIDENCE", "Block7": "RECONSTRUCTION_NONDETERMINISTIC_STOP", "Block7B": "PARTIAL_G1_G3_RECONSTRUCTION_READY_FOR_G4_REVIEW", "Block8": "FULL_G4_RAW_EQUIVALENCE_READY_FOR_G5_REVIEW", "G5": g5_summary["g5_outcome"]},
        "execution_counters": {"XAI_execution_count": 0, "SHAP_execution_count": 0, "LIME_execution_count": 0, "analytical_feature_attribution_execution_count": 0, "analytical_fusion_attribution_execution_count": 0, "PDP_ICE_execution_count": 0, "counterfactual_execution_count": 0, "T1_explanation_access_count": 0, "T2_access_count": 0, "refit_count": 0, "reconstruction_count": 0, "recalibration_count": 0, "metric_recomputation_count": 0},
        "parents_before": parents_before,
    }
    shap_freeze = {
        "schema_version": VERSION, "status": OUTCOME, "selected_version": None, "installation_performed": False, "installation_command": None, "package_trials": 0, "explainer_imports": 0, "explainer_executions": 0,
        "compatibility_rationale": "No released candidate examined is compatible with both frozen Python 3.11.14 and NumPy 2.4.6 on Darwin x86_64 without changing the predictive runtime.",
        "candidates": [
            {"version": "0.52.0", "result": "INCOMPATIBLE", "reason": "Requires-Python >=3.12; frozen Python is 3.11.14", "source": "https://pypi.org/pypi/shap/0.52.0/json"},
            {"version": "0.51.0", "result": "INCOMPATIBLE_DEPENDENCY_CHAIN", "reason": "Supports Python >=3.11 and NumPy >=2, but Darwin x86_64 requires numba<0.63; Numba 0.62.1 requires numpy<2.4", "source": "https://pypi.org/pypi/shap/0.51.0/json", "wheel": {"filename": "shap-0.51.0-cp311-cp311-macosx_10_9_x86_64.whl", "sha256": "4b4b81d7401bc821490148a694a9f149f8ef488fa973b49fdc8a7916a572750f"}},
            {"version": "numba-0.62.1", "result": "INCOMPATIBLE_WITH_FROZEN_NUMPY", "reason": "Requires numpy<2.4,>=1.22", "source": "https://pypi.org/pypi/numba/0.62.1/json", "wheel_sha256": "f43e24b057714e480fe44bc6031de499e7cf8150c63eb461192caa6cc8530bc8"},
        ],
        "resolution_requirement": "A compatible future SHAP release or a separately human-authorized predictive-runtime change followed by a prospective amendment is required.",
    }
    t1 = {"schema_version": VERSION, "freeze_access_count": 0, "future_access_class": "TECHNICAL_EXPLANATION_ACCESS", "historical_T1_predictive_access_count": 1, "historical_T1_predictive_scoring_count": 1, "historical_T1_rerun": False, "future_rows": "ONLY_FROZEN_FOREGROUND_AND_LOCAL_POLICY_ROWS", "label_use_for_selection": False, "historical_counter_increment": False}
    t2 = {"schema_version": VERSION, "T2_ACCESS_COUNT": 0, "T2_STATE": "DENY_SEALED_REVIEWER_RESERVE", "all_primary_XAI_use": "PROHIBITED", "reserved_for": "FUTURE_REVIEWER_FACING_VALIDATION_UNDER_NEW_PROSPECTIVE_PROTOCOL"}
    prereq = {"schema_version": VERSION, "Sprint56_authorized": False, "runtime_freeze_outcome": OUTCOME, "blocking_prerequisite": "SHAP_VERSION_AND_COMPATIBLE_RUNTIME_NOT_FROZEN", "required_before_execution": ["SEPARATE_HUMAN_PRIMARY_XAI_EXECUTION_AUTHORIZATION", "PROSPECTIVE_SHAP_RUNTIME_AMENDMENT", "EXACT_SHAP_VERSION_AND_PACKAGE_HASH", "COMPATIBILITY_WITH_OR_SEPARATELY_AUTHORIZED_CHANGE_TO_FROZEN_PREDICTIVE_RUNTIME", "BEFORE_AFTER_ENVIRONMENT_INVENTORY", "SINGLE_THREAD_ENVIRONMENT_APPLIED", "PARENT_HASHES_REVERIFIED", "389_SCOPE_UNIVERSE_REVERIFIED", "TRAIN_BACKGROUND_T1_FOREGROUND_LOCAL_CASES_MATERIALIZED_BEFORE_ATTRIBUTION", "ZERO_T2_ACCESS"], "execution_forbidden_until_all_satisfied": True}

    for name, value in contracts().items():
        write_json(output / name, value)
    write_json(output / "xai_runtime_contract.json", runtime)
    write_json(output / "shap_version_freeze.json", shap_freeze)
    write_json(output / "t1_xai_access_policy.json", t1)
    write_json(output / "t2_reviewer_reserve_policy.json", t2)
    write_json(output / "sprint56_primary_xai_authorization_prerequisites.json", prereq)

    after = package_inventory()
    if before != after:
        raise FreezeError("package environment changed during metadata-only freeze")
    parents_after = verify_parents(root)
    if parents_before != parents_after:
        raise FreezeError("parent evidence changed during freeze")
    inventory = {"schema_version": VERSION, "inspection": "IMPORTLIB_METADATA_ONLY_NO_EXPLAINER_IMPORT", "installation_performed": False, "requirements_constraints_delta": [], "before": before, "after": after, "inventories_identical": True, "parents_after": parents_after}
    write_json(output / "dependency_inventory.json", inventory)
    (output / "XAI_RUNTIME_FREEZE_REPORT.md").write_text(report(head, timestamp))

    manifest_names = sorted(path.name for path in output.iterdir() if path.is_file() and path.name != "MANIFEST.sha256" and not path.name.endswith(".tmp"))
    manifest = "".join(f"{sha256(output / name)}  {name}\n" for name in manifest_names)
    (output / "MANIFEST.sha256").write_text(manifest)
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    print(run(args.root.resolve()))


if __name__ == "__main__":
    main()
