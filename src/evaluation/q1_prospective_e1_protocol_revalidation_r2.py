# ruff: noqa: E501
"""R2 validates immutable 56.3A compiler output with one explicit R1 amendment.

The validation mode consumes only the two new metadata packages. It does not
reopen the historical compiler's source-data loader, change its inputs, mark a
failed manifest as matching, or regenerate any historical package. All original
contract bytes remain authoritative; only the downstream disposition is new.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[2]
BRANCH = "sprint-10/q1-prospective-e1-protocol-freeze"
BASE = "audits/q1-prospective-e1-protocol-freeze/1.0.0"
R1 = "audits/q1-prospective-e1-parent-integrity-resolution/1.0.0"
OUT = "audits/q1-prospective-e1-protocol-revalidation-r2/1.0.0"
TARGET = "audits/q1-primary-xai-runtime-smoke/1.0.0/validation-initial-output.txt"
ORDER_ROOT = "audits/q1-primary-xai-e1-input-e2-reference-resolution/1.0.0"
ORDER_PATHS = (
    ORDER_ROOT + "/prospective_resolution_policy.json",
    ORDER_ROOT + "/e2_reference_means.jsonl",
)
ORDER_TEST = "test_q1_primary_xai_e1_e2_resolution.py::test_decision_frozen_before_mean"
LOG_TEST = "test_q1_primary_xai_alternative_design.py::test_parent_preservation"
R1_CLASS = "R1_PASS_MANIFEST_PACKAGING_INCONSISTENCY_DIAGNOSTIC_ONLY"
PASS = "R2_PASS_PROTOCOL_FREEZE_WITH_R1_PROVENANCE_LIMITATION"
INVALID = "R2_BLOCKED_R1_AMENDMENT_INVALID"
BLOCKED = "R2_BLOCKED_OTHER_PROTOCOL_INTEGRITY_REQUIREMENT"
FAIL = "R2_FAIL_PROTOCOL_SCIENTIFIC_INTEGRITY"
READY = "READY_FOR_SEPARATE_HUMAN_AUTHORIZATION"
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
    "MODEL_LOAD_COUNT",
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
    "HISTORICAL_PACKAGE_MUTATION_COUNT",
    "ENVIRONMENT_MUTATION_COUNT",
    "COMMIT_COUNT",
    "PUSH_COUNT",
    "PR_COUNT",
)
R1_REQUIRED = {
    "SPRINT56_3A_R1_PARENT_INTEGRITY_RESOLUTION_REPORT.md",
    "protocol_summary.json",
    "current_hash_analysis.json",
    "manifest_expected_hash.json",
    "git_history_provenance.json",
    "manifest_file_timeline.json",
    "historical_byte_recovery.json",
    "difference_classification_summary.json",
    "sprint56_1_semantic_reconciliation.json",
    "manifest_construction_analysis.json",
    "scientific_impact_matrix.json",
    "resolution_decision.json",
    "downstream_56_3a_policy.json",
    "governance_counters.json",
    "recommended_next_action.json",
    "validation_results.json",
}


class ValidationBlocked(ValueError):
    def __init__(self, reason, result=BLOCKED):
        super().__init__(reason)
        self.result = result


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(value):
    return (
        json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False)
        + "\n"
    ).encode()


def manifest_bytes(files):
    return "".join(
        f"{sha(raw)}  {name}\n" for name, raw in sorted(files.items())
    ).encode()


class VerifiedPackage:
    """Byte snapshots are verified at construction and again before consumption."""

    def __init__(self, namespace, files):
        self.namespace = namespace
        self.files = dict(files)
        self.verify()

    def verify(self):
        result = INVALID if self.namespace == R1 else BLOCKED
        if self.namespace not in {R1, BASE, OUT} or "MANIFEST.sha256" not in self.files:
            raise ValidationBlocked("Missing approved package manifest", result)
        entries = {}
        for line in self.files["MANIFEST.sha256"].decode().splitlines():
            if "  " not in line:
                raise ValidationBlocked("Malformed manifest", result)
            digest, name = line.split("  ", 1)
            if (
                name in entries
                or PurePosixPath(name).name != name
                or name == "MANIFEST.sha256"
                or not re.fullmatch("[0-9a-f]{64}", digest)
            ):
                raise ValidationBlocked("Ambiguous manifest entry", result)
            entries[name] = digest
        if set(entries) != set(self.files) - {"MANIFEST.sha256"}:
            raise ValidationBlocked("Manifest file-set mismatch", result)
        if not all(sha(self.files[n]) == h for n, h in entries.items()):
            raise ValidationBlocked("Manifest digest mismatch", result)
        if self.namespace == R1 and not R1_REQUIRED <= set(entries):
            raise ValidationBlocked("Required R1 amendment input missing", INVALID)
        self.entries = entries
        return {
            "status": "PASS",
            "namespace": self.namespace,
            "manifest_sha256": sha(self.files["MANIFEST.sha256"]),
            "verified_file_count": len(entries),
            "exact_file_set": True,
        }

    def documents(self):
        self.verify()
        return {
            name: (
                [json.loads(line) for line in raw.decode().splitlines() if line]
                if name.endswith(".jsonl")
                else json.loads(raw)
            )
            for name, raw in self.files.items()
            if name.endswith((".json", ".jsonl"))
        }


def read_package(root, namespace):
    if namespace not in {R1, BASE}:
        raise PermissionError("R2 may read only R1 and original56.3A packages")
    directory = Path(root).resolve() / namespace
    if directory.resolve() != directory or not directory.is_dir():
        raise ValidationBlocked(
            "Missing/symlinked package", INVALID if namespace == R1 else BLOCKED
        )
    files = {}
    for path in sorted(directory.iterdir()):
        if (
            path.resolve() != path
            or not path.is_file()
            or path.suffix not in {".json", ".jsonl", ".md", ".sha256"}
        ):
            raise ValidationBlocked(
                "Unexpected package member; do not follow it",
                INVALID if namespace == R1 else BLOCKED,
            )
        files[path.name] = path.read_bytes()
    return VerifiedPackage(namespace, files)


def git(*args):
    if not args or args[0] not in {
        "rev-parse",
        "status",
        "log",
        "ls-tree",
        "diff",
        "ls-files",
    }:
        raise PermissionError("Git metadata inspection only")
    if any(
        a.startswith(("--output", "--exec", "--ext-diff", "--textconv"))
        or a in {"-p", "--patch"}
        for a in args
    ):
        raise PermissionError("No Git payload output or external operations")
    if args[0] == "diff" and "--name-only" not in args and "--check" not in args:
        raise PermissionError("No content diff")
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True)


def verify_r1(amendment, original):
    amendment_manifest = amendment.verify()
    docs = amendment.documents()
    base = original.documents()
    try:
        summary = docs["protocol_summary.json"]
        resolution = docs["resolution_decision.json"]
        current = docs["current_hash_analysis.json"]
        expected = docs["manifest_expected_hash.json"]
        diff = docs["difference_classification_summary.json"]
        semantic = docs["sprint56_1_semantic_reconciliation.json"]
        downstream = docs["downstream_56_3a_policy.json"]
        counters = docs["governance_counters.json"]
        old = base["protocol_summary.json"]["parent_integrity_finding"]
        required_zero = set(ZERO) - {"MODEL_LOAD_COUNT"}
        checks = {
            "R1_resolution_exact": summary["resolution"]
            == resolution["resolution"]
            == R1_CLASS,
            "amendment_type_exact": summary["amendment_type"]
            == "PROVENANCE_AMENDMENT_NOT_MANIFEST_CORRECTION",
            "one_target_exact": current["path"] == old["path"] == TARGET,
            "recorded_mismatch_retained": current["SHA256"]
            != expected["expected_sha256"]
            and current["matches_manifest"] is False
            and old["status"] == "FAIL_MANIFEST_MISMATCH",
            "amendment_digest_pair_binds_original_failure": current["SHA256"]
            == old["actual_sha256"]
            and expected["expected_sha256"] == old["manifest_sha256"],
            "difference_classes_exact": set(diff["classes"])
            == {"WHITESPACE_ONLY", "FORMAT_ONLY"},
            "PASS_FAIL_semantics_unchanged": diff["PASS_FAIL_semantic_difference"]
            is False,
            "test_count_unchanged": diff["test_count_difference"] is False,
            "scientific_result_unchanged": diff[
                "runtime_version_scientific_result_difference"
            ]
            is False,
            "independent_support": semantic["independent_support"] is True
            and set(semantic["invariants"])
            == {
                "all_support_bytes_manifest_and_HEAD_match",
                "summary_PASS",
                "five_families_pass",
                "determinism_pass",
                "recorded_model_object_hashes_before_after_equal",
                "recorded_protected_hashes_before_after_equal",
                "predictive_inventories_semantically_equal",
                "final_validation_pass_51",
                "initial_log_matches_recorded_initial_test_counts",
                "history_final_validation_agrees",
                "no_scientific_rerun_or_result_changes_recorded",
                "implementation_provenance_matches",
            }
            and all(v is True for v in semantic["invariants"].values()),
            "support_records_bound": all(
                x["manifest_match"] is True
                and x["HEAD_match"] is True
                and x["sha256"] == x["manifest_expected_sha256"]
                for x in semantic["evidence"].values()
            )
            and len(semantic["evidence"]) == 12,
            "historical_mutation_zero": counters["HISTORICAL_PACKAGE_MUTATION_COUNT"]
            == 0,
            "all_scientific_counters_zero": all(
                counters.get(k) == 0 for k in required_zero
            ),
            "T1_historical_and_T2_preserved": counters[
                "historical_T1_predictive_access_count"
            ]
            == counters["historical_T1_predictive_scoring_count"]
            == 1
            and counters["T2_STATE"] == "DENY_SEALED_REVIEWER_RESERVE",
            "downstream_action_exact": downstream["action"]
            == "REVALIDATE_SPRINT_56_3A_USING_EXPLICIT_R1_PROVENANCE_AMENDMENT",
            "no_prior_execution_authorization": summary[
                "scientific_execution_authorized"
            ]
            is False
            and downstream["56_3A_revalidated_in_R1"] is False
            and downstream["56_3B_authorized"] is False
            and downstream["E1_execution_authorized"] is False,
            "no_false_Git_recovery": docs["historical_byte_recovery.json"][
                "exact_bytes_found_in_reachable_Git"
            ]
            is False,
            "R1_validation_pass": docs["validation_results.json"]["status"] == "PASS",
            "original_disposition_retained": base["protocol_summary.json"][
                "disposition"
            ]
            == "PROSPECTIVE_E1_PROTOCOL_FREEZE_BLOCKED",
        }
    except (KeyError, TypeError) as error:
        raise ValidationBlocked(
            "Incomplete R1 amendment: " + str(error), INVALID
        ) from error
    if not all(checks.values()):
        raise ValidationBlocked(
            "Invalid R1 conditions: "
            + ", ".join(k for k, v in checks.items() if not v),
            INVALID,
        )
    return {
        "manifest": amendment_manifest,
        "resolution": R1_CLASS,
        "conditions": checks,
        "status": "VALID",
        "scope": {
            "only_artifact": TARGET,
            "current_sha256": current["SHA256"],
            "manifest_expected_sha256": expected["expected_sha256"],
        },
        "excluded_from_amendment": [
            "any other manifest mismatch",
            "mtime/order",
            "source provenance",
            "model state",
            "TEXT alignment",
            "population source",
            "T1/T2 boundary",
            "scientific input provenance",
        ],
    }


def chronology_metadata():
    records = []
    for path in ORDER_PATHS:
        log = git("log", "--all", "--format=%H %P %ad %s", "--date=iso", "--", path)
        commits = [line.split()[0] for line in log.splitlines()]
        records.append(
            {
                "path": path,
                "history_exact": log,
                "change_commits": commits,
                "HEAD_tree_entry": git("ls-tree", "HEAD", "--", path),
                "first_commit_tree_entry": git("ls-tree", commits[-1], "--", path)
                if commits
                else "",
            }
        )
    return {
        "records": records,
        "method": "Git metadata only; neither historical file payload nor current mtime read",
        "filesystem_mtime_proves_generation_order": False,
    }


def review_mtime(original_docs, chronology, historical_unchanged):
    failures = original_docs["validation_results.json"].get("failures", [])
    old = [x for x in failures if x.get("test") == ORDER_TEST]
    counters = original_docs["execution_counters.json"]
    records = chronology.get("records", [])
    same_initial = (
        len(records) == 2
        and [r["path"] for r in records] == list(ORDER_PATHS)
        and all(len(r["change_commits"]) == 1 for r in records)
        and records[0]["change_commits"] == records[1]["change_commits"]
        and all(
            r["HEAD_tree_entry"] == r["first_commit_tree_entry"]
            and r["HEAD_tree_entry"]
            for r in records
        )
    )
    future_protocol_unexecuted = all(
        counters.get(k) == 0
        for k in [
            "T1_E1_ATTRIBUTION_COUNT",
            "SHAP_EXECUTION_COUNT",
            "ANALYTICAL_ATTRIBUTION_EXECUTION_COUNT",
            "POPULATION_SELECTION_COUNT",
        ]
    )
    policy_is_prospective = (
        original_docs["protocol_summary.json"]["execution_authorized"] is False
        and original_docs["local_case_selection_policy.json"][
            "freeze_before_attribution"
        ]
        is True
        and original_docs["t1_global_foreground_policy.json"]["selection_executed"]
        is False
    )
    bounded = (
        len(old) == 1
        and same_initial
        and historical_unchanged is True
        and future_protocol_unexecuted
        and policy_is_prospective
        and chronology.get("filesystem_mtime_proves_generation_order") is False
    )
    return {
        "assertion": ORDER_TEST,
        "original_failure_preserved": old,
        "disposition": "PASS_WITH_NONSCIENTIFIC_LIMITATION"
        if bounded
        else "BLOCKED_UNRESOLVED",
        "historical_generation_order": "NOT_PROVEN; neither filesystem mtime nor same-commit trees establish within-commit event order",
        "original_assertion_redefined_as_PASS": False,
        "R1_amendment_used_for_this_review": False,
        "Git_provenance": chronology,
        "checks": {
            "both_files_unchanged_since_joint_introduction": same_initial,
            "historical_tracked_evidence_unchanged": historical_unchanged,
            "future_protocol_unexecuted": future_protocol_unexecuted,
            "prospective_pre_attribution_gates_retained": policy_is_prospective,
        },
        "scientific_relevance_boundary": "The failed filesystem test concerns historical E2 reference-file write order. R2 does not validate that historical order or recompute/use row-level E2 values. Future E1 population, fidelity, scale and authorization definitions are immutable and still precede any authorized E1 execution.",
        "bounded_limitation": "The recorded timestamp failure remains a historical provenance limitation, not proof of invalid E2 values. It is not a protocol-definition blocker for this unexecuted prospective E1 freeze. No historical chronology claim is permitted.",
        "future_scientific_requirement": "Persist explicit event/protocol digests before future population selection/attribution; never substitute mtime for prospective governance",
        "unknown_or_additional_order_failures": "BLOCKED; this adjudication applies only to the recorded test and exact two paths",
    }


def validate_contract(docs):
    """Validator mode for the original compiler output, with no input rematerialization.

    Checks cover original governance, every scope and all18 policy families. Each
    unchanged file is also bound to the verified original manifest. Missing policy
    structure blocks; contradictory scientific/governance content fails closed.
    """
    checks = {}

    def add(name, condition, scientific=False):
        checks[name] = {
            "status": "PASS"
            if condition
            else ("FAIL_SCIENTIFIC" if scientific else "BLOCKED"),
            "scientific": scientific,
        }

    try:
        summary = docs["protocol_summary.json"]
        scopes = docs["e1_scope_universe.jsonl"]
        state = docs["scientific_state_preservation.json"]
        counters = docs["execution_counters.json"]
        add(
            "predictive_state",
            state["predictive_conclusion"] == "MIXED_CONFIRMATORY_EVIDENCE"
            and state["predictive_evidence"] == "CLOSED_IMMUTABLE",
            True,
        )
        add(
            "historical_counters",
            counters["historical_T1_predictive_access_count"]
            == counters["historical_T1_predictive_scoring_count"]
            == 1,
            True,
        )
        add(
            "all_new_original_counters_zero",
            all(v == 0 for k, v in counters.items() if k.endswith("_COUNT")),
            True,
        )
        add(
            "original_scope_counts",
            summary["candidate_scopes"] == 168
            and summary["scientific_execution_eligible_count"] == 0
            and summary["eligibility_counts"]
            == {
                "E1_PENDING_SCIENTIFIC_INPUT_PROVENANCE": 112,
                "TEXT_E1_INELIGIBLE": 56,
            },
            True,
        )
        add(
            "scope_identity_unique",
            len(scopes) == len({r["scope_id"] for r in scopes}) == 168,
            True,
        )
        add(
            "scope_projects_families",
            len({r["project"] for r in scopes}) == 14
            and {r["algorithm_family"] for r in scopes}
            == {"Logistic Regression", "Random Forest", "XGBoost", "LightGBM"},
            True,
        )
        add(
            "unimodal_scope_only",
            {r["modality"] for r in scopes} == {"CODE", "PROCESS", "TEXT"}
            and all(r["historical_configuration"] in {"C", "P", "T"} for r in scopes),
            True,
        )
        add(
            "scope_equivalence_no_execution",
            all(
                r["equivalence_eligible"] is True
                and r["scientific_execution_eligible"] is False
                and r["state_origin"] == "RECONSTRUCTED_NOT_ORIGINAL_SPRINT54"
                for r in scopes
            ),
            True,
        )
        add(
            "scope_status_no_promotion",
            all(
                r["eligibility"]
                == (
                    "TEXT_E1_INELIGIBLE"
                    if r["modality"] == "TEXT"
                    else "E1_PENDING_SCIENTIFIC_INPUT_PROVENANCE"
                )
                and r["fidelity"] == "FIDELITY_NOT_TESTED"
                and r["stability"] == "INSUFFICIENT_EVIDENCE"
                for r in scopes
            ),
            True,
        )
        add(
            "historical_recovery_closed",
            state["historical_recovery"] == "CLOSED"
            and state["historical_E1"] == "LIMITED_ILLUSTRATIVE_ONLY",
            True,
        )
        add(
            "E2_E3_architecture",
            state["primary_XAI_core"] == "E2_ANALYTICAL_FUSION"
            and state["E3"] == "SEPARATE_CALIBRATION"
            and state["complementary_XAI_layer"] == "PROSPECTIVE_E1",
            True,
        )
        lr = docs["lr_analytical_contract.json"]
        add(
            "LR_method",
            lr["scale"] == "LOGIT"
            and lr["phi_j"] == "beta_j*(x_j-mu_j)"
            and lr["phi_0"] == "intercept + sum(beta_j*mu_j)"
            and lr["primary_global"] == "mean_i(abs(phi_j(x_i)))",
        )
        for prefix, scale in [
            ("rf", "POSITIVE_CLASS_PROBABILITY"),
            ("xgb", "NATIVE_RAW_MARGIN"),
            ("lgb", "NATIVE_RAW_MARGIN"),
        ]:
            tree = docs[prefix + "_treeshap_contract.json"]
            add(
                prefix + "_exact_tree",
                tree["approximate"] is False
                and tree["check_additivity"] is True
                and tree["feature_perturbation"] == "tree_path_dependent"
                and tree["model_output"] == "raw"
                and tree["scale"] == scale
                and tree["positive_class"] == 1,
            )
        method = docs["e1_method_contract.json"]
        add(
            "LIME_counterfactual_excluded",
            method["LIME"] == method["counterfactuals"] == "EXCLUDED_FROM_PRIMARY_XAI",
        )
        add(
            "runtime_frozen",
            len(method["runtime_lock"]["inventory"]["packages"]) > 0
            and any(
                x["name"] == "shap" and x["version"] == "0.51.0"
                for x in method["runtime_lock"]["inventory"]["packages"]
            ),
        )
        for key in ["train_background_policy", "t1_global_foreground_policy"]:
            p = docs[key + ".json"]
            add(
                key,
                p["maximum_rows_per_scope"] == 256
                and p["seed"] == 20260901
                and p["selection_executed"] is False
                and "SHA-256" in p["tie_break"]
                and p["result_dependent_selection"] == "FORBIDDEN",
            )
        fg = docs["t1_global_foreground_policy.json"]
        local = docs["local_case_selection_policy.json"]
        add(
            "foreground_label_blind",
            fg["mode"] == "T1_SELECTION_LABEL_BLIND"
            and "T1 labels" in fg["prohibited_inputs"],
        )
        add(
            "local_subset_cap",
            local["maximum_rows_per_scope"] == 8
            and local["subset_of_global"] is True
            and local["freeze_before_attribution"] is True
            and local["mode"] == "T1_SELECTION_LABEL_BLIND",
        )
        budget = docs["query_budget.json"]["future_per_scope"]
        add(
            "query_budgets",
            budget["TRAIN_background_unique_rows_max"] == 256
            and budget["T1_global_foreground_unique_rows_max"] == 256
            and budget["T1_local_cases_max"] == 8
            and budget["primary_attribution_row_evaluations_max_including_stability"]
            == 5120
            and docs["query_budget.json"]["current_all_scientific_budgets"] == 0,
        )
        fidelity = docs["fidelity_contract.json"]
        exact = fidelity["inherited_exact"]
        add(
            "fidelity_tolerances",
            exact["analytical_LR"]["residual_bound"]
            == "abs(residual) <= 1e-10 * (1 + abs(eta))"
            and exact["TreeSHAP"]["residual_bound"]
            == "abs(residual) <= 1e-6 * (1 + abs(model_output))"
            and exact["global"]["reconstruction_tolerance"] == 1e-12
            and fidelity["unexplained_fraction_threshold"] == 0
            and fidelity["tolerance_relaxation"] == "FORBIDDEN",
        )
        stability = docs["stability_contract.json"]
        inherited = stability["inherited_exact"]
        add(
            "stability",
            inherited["seeds"] == list(range(20260901, 20260921))
            and inherited["top_k"] == [3, 10]
            and inherited["deterministic_method_max_absolute_attribution_difference"]
            == 1e-12
            and inherited["population_reselection_by_stability_seed"] is False
            and len(stability["statuses"]) == 4,
        )
        thresholds = {
            "Jaccard": 0.6,
            "Spearman": 0.7,
            "sign_agreement": 0.8,
            "total_variation_max": 0.25,
        }
        add(
            "heterogeneity",
            stability["comparison_thresholds"] == thresholds
            and docs["heterogeneity_contract.json"]["inherited_exact"]["cross_model"][
                "minimum_eligible_comparable_algorithm_families"
            ]
            == 3,
        )
        correlation = docs["correlated_feature_policy.json"]
        add(
            "correlated_features",
            correlation["absolute_threshold"] == 0.70
            and correlation["evidence_source"] == "TRAIN_ONLY"
            and correlation["modalities"] == ["CODE", "PROCESS"]
            and correlation["group_importance"]
            == "mean_i(abs(sum_j_in_group(phi_ij)))",
        )
        features = docs["code_process_feature_contract.json"]["registry"]
        add(
            "feature_registry",
            len(features) == 12
            and all(
                {
                    "feature_name",
                    "modality",
                    "definition",
                    "unit",
                    "transformation",
                    "sign_interpretation_limits",
                    "missing_value_policy",
                    "source_provenance",
                }
                <= set(r)
                for r in features
            ),
        )
        text = docs["text_e1_contract.json"]
        add(
            "TEXT_alignment",
            text["any_unknown"] == "TEXT_E1_INELIGIBLE"
            and len(text["required_proofs"]) >= 9,
        )
        continuity = docs["e1_e2_continuity_contract.json"]
        add(
            "E2_continuity",
            continuity["E2_role"] == "PRIMARY_EXPLANATORY_CORE"
            and continuity["E1_role"] == "COMPLEMENTARY_FEATURE_LAYER"
            and "propagate E1 SHAP through E2" in continuity["prohibited"]
            and len(continuity["labels"]) == 5,
        )
        add(
            "bridge_separate",
            docs["e1_e2_bridge_policy.json"]["no_mathematical_composition"] is True
            and len(docs["e1_e2_bridge_policy.json"]["statuses"]) == 5,
        )
        add(
            "figure_families",
            docs["figure_contract.json"]["generated_count"] == 0
            and len(docs["figure_contract.json"]["families"]) == 8,
        )
        add(
            "claims",
            len(docs["prohibited_claims.json"]["prohibited"]) >= 9
            and "reconstructed states are original Sprint54 models"
            in docs["prohibited_claims.json"]["prohibited"],
        )
        add(
            "T2_sealed",
            docs["t2_sealed_reserve_policy.json"]["status"]
            == "DENY_SEALED_REVIEWER_RESERVE"
            and docs["t2_sealed_reserve_policy.json"]["future_budget"] == 0
            and counters["T2_STATE"] == "DENY_SEALED_REVIEWER_RESERVE",
            True,
        )
        auth = docs["execution_authorization_gate.json"]
        add(
            "authorization_closed",
            auth["scientific_execution_authorized"] is False
            and len(auth["requirements"]) == 12
            and docs["recommended_next_action.json"]["start_authorized"] is False,
            True,
        )
        add(
            "input_provenance_still_required",
            all(r["input_blocker"] and r["future_gate"] for r in scopes)
            and len(auth["additional_hard_gates"]) >= 3,
        )
        add(
            "missing_value_policy",
            docs["missing_value_policy.json"]["new_imputer_fit"] == "FORBIDDEN"
            and docs["missing_value_policy.json"]["SHAP_specific_imputation"]
            == "FORBIDDEN",
        )
        add(
            "persistence",
            docs["reproducibility_persistence_contract.json"]["no_overwrite"] is True
            and len(docs["output_schemas.json"]["schemas"]) == 6,
        )
        add(
            "scientific_sufficiency",
            len(docs["q1_scientific_sufficiency_gate.json"]["criteria"]) == 18
            and docs["q1_scientific_sufficiency_gate.json"][
                "no_promotion_by_explainer_success"
            ]
            is True,
        )
        add(
            "primary_secondary",
            docs["primary_secondary_analysis_policy.json"]["secondary_label"]
            == "POST_HOC_BEST_OBSERVED_MODEL_ANALYSIS",
        )
    except (KeyError, TypeError, ValueError) as error:
        add("definition_structure_missing:" + str(error), False)
    return checks


def q1_matrix(original, checks):
    items = [
        (
            "A",
            "explanation methods",
            ["e1_method_contract.json"],
            [
                "LR_method",
                "rf_exact_tree",
                "xgb_exact_tree",
                "lgb_exact_tree",
                "LIME_counterfactual_excluded",
                "runtime_frozen",
            ],
        ),
        (
            "B",
            "output scales",
            [
                "lr_analytical_contract.json",
                "rf_treeshap_contract.json",
                "xgb_treeshap_contract.json",
                "lgb_treeshap_contract.json",
            ],
            ["LR_method", "rf_exact_tree", "xgb_exact_tree", "lgb_exact_tree"],
        ),
        (
            "C",
            "background policy",
            ["train_background_policy.json"],
            ["train_background_policy"],
        ),
        (
            "D",
            "foreground policy",
            ["t1_global_foreground_policy.json"],
            ["t1_global_foreground_policy", "foreground_label_blind"],
        ),
        (
            "E",
            "local case policy",
            ["local_case_selection_policy.json"],
            ["local_subset_cap"],
        ),
        ("F", "query budgets", ["query_budget.json"], ["query_budgets"]),
        (
            "G",
            "fidelity tolerances",
            ["fidelity_contract.json"],
            ["fidelity_tolerances"],
        ),
        ("H", "stability protocol", ["stability_contract.json"], ["stability"]),
        (
            "I",
            "correlated-feature handling",
            ["correlated_feature_policy.json", "code_process_feature_contract.json"],
            ["correlated_features", "feature_registry"],
        ),
        (
            "J",
            "heterogeneity policy",
            ["heterogeneity_contract.json"],
            ["heterogeneity"],
        ),
        (
            "K",
            "TEXT attribution constraints",
            ["text_e1_contract.json"],
            ["TEXT_alignment"],
        ),
        (
            "L",
            "E2 analytical fusion continuity",
            ["e1_e2_continuity_contract.json", "e1_e2_bridge_policy.json"],
            ["E2_continuity", "bridge_separate"],
        ),
        (
            "M",
            "calibration explanation boundary",
            ["scientific_state_preservation.json"],
            ["E2_E3_architecture"],
        ),
        (
            "N",
            "prohibited overclaims",
            ["prohibited_claims.json", "primary_secondary_analysis_policy.json"],
            ["claims", "primary_secondary"],
        ),
        ("O", "T2 reserve boundary", ["t2_sealed_reserve_policy.json"], ["T2_sealed"]),
        ("P", "figure families", ["figure_contract.json"], ["figure_families"]),
        (
            "Q",
            "scope eligibility rules",
            ["e1_unit_of_analysis.json", "e1_scope_universe.jsonl"],
            [
                "scope_identity_unique",
                "scope_status_no_promotion",
                "authorization_closed",
            ],
        ),
        (
            "R",
            "scientific input provenance requirement",
            [
                "reproducibility_persistence_contract.json",
                "execution_authorization_gate.json",
            ],
            ["input_provenance_still_required", "persistence", "missing_value_policy"],
        ),
    ]
    limits = {
        "K": "All56TEXT scopes remain ineligible; defining the alignment gate is not fulfilling it",
        "Q": "All168scopes remain non-executable;112numeric pending and56TEXT ineligible",
        "R": "Legitimate source/representation proof is still absent; no input requirement waived",
    }
    rows = []
    for letter, item, refs, required in items:
        ok = all(checks.get(k, {}).get("status") == "PASS" for k in required)
        rows.append(
            {
                "id": letter,
                "item": item,
                "status": (
                    "FROZEN_WITH_LIMITATION" if letter in limits else "FROZEN_PASS"
                )
                if ok
                else "BLOCKED",
                "checks": required,
                "source_files": {BASE + "/" + n: original.entries.get(n) for n in refs},
                "limitation": limits.get(letter),
                "meaning": "Protocol definition readiness only, not executed scientific sufficiency",
            }
        )
    return rows


def select_result(r1_valid, checks, remaining, matrix):
    if not r1_valid:
        return INVALID
    if any(r["status"] == "FAIL_SCIENTIFIC" for r in checks.values()) or any(
        r["status"] == "FAIL_SCIENTIFIC_RELEVANCE" for r in remaining
    ):
        return FAIL
    if (
        not checks
        or {r.get("id") for r in matrix} != set("ABCDEFGHIJKLMNOPQR")
        or len(matrix) != 18
        or any(r["status"] != "PASS" for r in checks.values())
        or any(r["status"] == "BLOCKED_UNRESOLVED" for r in remaining)
        or any(r["status"] == "BLOCKED" for r in matrix)
    ):
        return BLOCKED
    return PASS


def implementation_binding(original, amendment, preexisting):
    checks = []
    for package, source, test, runner in [
        (
            original,
            "src/evaluation/q1_prospective_e1_protocol_freeze.py",
            "tests/evaluation/test_q1_prospective_e1_protocol_freeze.py",
            "tests/evaluation/run_q1_prospective_e1_governance_regressions.py",
        ),
        (
            amendment,
            "src/evaluation/q1_prospective_e1_parent_integrity_resolution.py",
            "tests/evaluation/test_q1_prospective_e1_parent_integrity_resolution.py",
            None,
        ),
    ]:
        sealed = package.documents()["implementation_provenance.json"]
        for key, path in [
            ("source_sha256", source),
            ("test_sha256", test),
            ("regression_runner_sha256", runner),
        ]:
            if path is None:
                continue
            matched = sealed.get(key) == preexisting.get(path, {}).get("sha256")
            checks.append(
                {
                    "test": "implementation_provenance:" + path,
                    "status": "PASS_PROVEN" if matched else "BLOCKED_UNRESOLVED",
                    "basis": "Current source/test bytes match the sealed original implementation digest",
                    "expected_sha256": sealed.get(key),
                    "current_sha256": preexisting.get(path, {}).get("sha256"),
                }
            )
    return checks


def revalidate(original, amendment, chronology, historical_unchanged, preexisting):
    verification = verify_r1(amendment, original)
    d = original.documents()
    a = amendment.documents()
    checks = validate_contract(d)
    mtime = review_mtime(d, chronology, historical_unchanged)
    remaining = implementation_binding(original, amendment, preexisting)
    failures = d["validation_results.json"].get("failures", [])
    for failure in failures:
        if (
            failure.get("test") == LOG_TEST
            and failure.get("finding")
            == d["protocol_summary.json"]["parent_integrity_finding"]
        ):
            status = "PASS_PROVEN"
            basis = "Specific byte mismatch retained; semantic acceptance through exact R1 amendment"
        elif failure.get("test") == ORDER_TEST:
            status = mtime["disposition"]
            basis = "Separate R2 relevance review; not covered by R1 amendment"
        else:
            status = "BLOCKED_UNRESOLVED"
            basis = "No amendment or bounded review for this independent failure"
        remaining.append(
            {
                "test": failure.get("test"),
                "status": status,
                "basis": basis,
                "original_failure": failure,
            }
        )
    if not historical_unchanged:
        remaining.append(
            {
                "test": "historical_snapshot",
                "status": "BLOCKED_UNRESOLVED",
                "basis": "Historical identity changes cannot be waived",
            }
        )
    if Counter(x.get("test") for x in failures) != Counter([LOG_TEST, ORDER_TEST]):
        remaining.append(
            {
                "test": "original_failure_inventory",
                "status": "BLOCKED_UNRESOLVED",
                "basis": "Original failure set missing, duplicated or changed",
            }
        )
    matrix = q1_matrix(original, checks)
    result = select_result(True, checks, remaining, matrix)
    ready = READY if result == PASS else "NOT_READY"
    scopes = []
    for row in d["e1_scope_universe.jsonl"]:
        scopes.append(
            {
                "scope_id": row["scope_id"],
                "project": row["project"],
                "algorithm_family": row["algorithm_family"],
                "modality": row["modality"],
                "model_identity_sha256": row["model_identity_sha256"],
                "original_56_3A_status": row["eligibility"],
                "status_after_R2": "TEXT_E1_INELIGIBLE_PENDING_ALIGNMENT_PROOF"
                if row["modality"] == "TEXT"
                else "E1_PENDING_SCIENTIFIC_INPUT_PROVENANCE",
                "scientific_execution_eligible": False,
                "input_blocker_retained": row["input_blocker"],
                "status_label_change_only": row["modality"] == "TEXT",
            }
        )
    scope_counts = dict(Counter(x["status_after_R2"] for x in scopes))
    wording = "The prospective E1 protocol was revalidated after an explicit provenance amendment resolved a historical diagnostic packaging inconsistency. The original byte-level mismatch remains visible and was not retroactively corrected. Independent immutable metadata supported unchanged scientific semantics."
    files = {
        "protocol_summary.json": {
            "resolution": result,
            "original_56_3A_disposition": d["protocol_summary.json"]["disposition"],
            "R1_resolution": R1_CLASS,
            "candidate_scopes": len(scopes),
            "scope_status_counts": scope_counts,
            "scientific_execution_authorized": False,
            "SPRINT56_3B_ELIGIBILITY": ready,
        },
        "r1_amendment_verification.json": verification,
        "historical_mismatch_retention.json": {
            **verification["scope"],
            "HISTORICAL_BYTE_INTEGRITY": "KNOWN_MISMATCH_RETAINED",
            "historical_manifest_match": False,
            "historical_manifest_modified": False,
            "original_56_3A_finding": d["protocol_summary.json"][
                "parent_integrity_finding"
            ],
            "R1_manifest_sha256": sha(amendment.files["MANIFEST.sha256"]),
            "no_retroactive_byte_identity": True,
        },
        "scientific_semantic_integrity.json": {
            "status": "PASS_WITH_PROVENANCE_AMENDMENT",
            "independent_support": True,
            "R1_evidence_references": a["sprint56_1_semantic_reconciliation.json"][
                "evidence"
            ],
            "provenance_limits": [
                "Original expected bytes not recovered from reachable Git",
                "Actor/tool/time of whitespace handling unproved",
                "Historical within-commit generation order unproved",
            ],
            "scope": TARGET,
            "not_a_universal_manifest_waiver": True,
        },
        "remaining_integrity_checks.json": {
            "checks": remaining,
            "contract_checks": checks,
            "no_scientific_requirement_waived": True,
        },
        "mtime_order_resolution.json": mtime,
        "revalidated_56_3a_contract.json": {
            "mode": "VALIDATE_FROZEN_COMPILER_OUTPUT_WITH_EXPLICIT_R1_AMENDMENT",
            "original_compiler_provenance": d["implementation_provenance.json"],
            "original_contract_file_hashes": original.entries,
            "original_manifest_sha256": sha(original.files["MANIFEST.sha256"]),
            "all_original_contract_bytes_retained": True,
            "policy_values_changed": False,
            "old_package_regenerated": False,
            "validated_check_count": len(checks),
            "contract_checks": checks,
            "new_downstream_56_3A_disposition": "PROSPECTIVE_E1_PROTOCOL_FREEZE_PASS_WITH_LIMITATIONS"
            if result == PASS
            else d["protocol_summary.json"]["disposition"],
            "original_disposition_retained": d["protocol_summary.json"]["disposition"],
            "exceptions": [
                "R1-scoped diagnostic semantic amendment",
                "Independent R2 bounded non-scientific mtime provenance limitation",
            ],
            "not_reexecuted": "Historical source loader/compiler publisher and scientific parent payloads; validation is against the identical persisted compiler output",
        },
        "e1_scope_status_after_r2.jsonl": scopes,
        "q1_protocol_sufficiency_matrix.json": {
            "items": matrix,
            "status_counts": dict(Counter(r["status"] for r in matrix)),
            "no_definition_blocker": all(r["status"] != "BLOCKED" for r in matrix),
            "empirical_E1_Q1_readiness_claimed": False,
        },
        "scientific_claim_boundary.json": {
            "allowed_if_R2_PASS": wording,
            "currently_applicable": result == PASS,
            "prohibited": [
                "The historical manifest was corrected.",
                "The original bytes were recovered from Git.",
                "The original file always matched the manifest.",
                "The discrepancy had no provenance limitation.",
                "E1 scientific execution was completed.",
                "TEXT E1 was fully validated.",
                "T1 was re-explained.",
                "T2 was accessed.",
            ],
        },
        "downstream_56_3b_policy.json": {
            "SPRINT56_3B_ELIGIBILITY": ready,
            "authorized": False,
            "automatically_started": False,
            "E1_execution_authorized": False,
            "SHAP_authorized": False,
            "T1_scientific_row_access_authorized": False,
            "prerequisites": "Separate human authorization of56.3B source/provenance/eligibility scope; later scientific execution requires all original AUTH-E1 gates",
        },
        "governance_counters.json": {
            **dict.fromkeys(ZERO, 0),
            "historical_T1_predictive_access_count": 1,
            "historical_T1_predictive_scoring_count": 1,
            "T2_STATE": "DENY_SEALED_REVIEWER_RESERVE",
        },
        "recommended_next_action.json": {
            "action": "Human review; consider separate56.3B authorization"
            if result == PASS
            else "Resolve independent blocker; no56.3B authorization",
            "stop_after_R2": True,
            "next_sprint_started": False,
        },
    }
    return files


def serialize(files):
    return {
        name: b"".join(
            (
                json.dumps(x, sort_keys=True, ensure_ascii=False, allow_nan=False)
                + "\n"
            ).encode()
            for x in value
        )
        if name.endswith(".jsonl")
        else encode(value)
        for name, value in files.items()
    }


def report(f):
    result = f["protocol_summary.json"]["resolution"]
    sections = [
        (
            "A. Objective",
            "Controlled validation of original56.3A compiler output using explicit R1 amendment; no scientific execution.",
        ),
        (
            "B. Branch and HEAD",
            f"`{f['preflight.json']['branch']}`; `{f['preflight.json']['HEAD']}`.",
        ),
        (
            "C. Original56.3A disposition",
            "PROSPECTIVE_E1_PROTOCOL_FREEZE_BLOCKED remains immutable in the original package.",
        ),
        (
            "D. R1 provenance amendment",
            R1_CLASS + "; PROVENANCE_AMENDMENT_NOT_MANIFEST_CORRECTION.",
        ),
        (
            "E. R1 manifest verification",
            "Exact file set and every digest verified before use; original56.3A manifest also verified.",
        ),
        (
            "F. Historical mismatch retention",
            "HISTORICAL_BYTE_INTEGRITY=KNOWN_MISMATCH_RETAINED. Current and expected digests remain different; no original log or manifest changed.",
        ),
        (
            "G. Scientific semantic integrity",
            "PASS_WITH_PROVENANCE_AMENDMENT for the one diagnostic file; no broader waiver.",
        ),
        (
            "H. Independent parent support",
            "Twelve R1-verified, manifested/Git-anchored support records retain the historical Sprint56.1 PASS. R2 reads their amendment metadata only; it does not load their historical scientific payloads.",
        ),
        (
            "I. Revalidation scope",
            "Same immutable protocol definitions and scope ledger validated in VALIDATE_FROZEN_COMPILER_OUTPUT_WITH_EXPLICIT_R1_AMENDMENT mode. Historical source-data loader and publisher are not rerun.",
        ),
        (
            "J. Non-waiver policy",
            "Only the exact log/digest pair receives the R1 semantic amendment. Unknown failures, altered contracts, source/state errors, population/TEXT failures and T1/T2 boundary failures remain blocking.",
        ),
        (
            "K. mtime/order review",
            f["mtime_order_resolution.json"]["disposition"]
            + ". Git places both files in the same introduction commit with unchanged tree identities; it cannot prove their original generation order. The old failed assertion is preserved. Its historical E2 write-order question does not determine definitions in an unexecuted prospective E1 protocol; no historical chronology claim is made.",
        ),
        (
            "L. Remaining integrity checks",
            "\n".join(
                "- " + r["test"] + ": " + r["status"]
                for r in f["remaining_integrity_checks.json"]["checks"]
            ),
        ),
        (
            "M. E1 universe",
            "168 immutable candidates,14projects,4families,3unimodal modalities; no model selection or execution readiness promotion.",
        ),
        ("N. CODE/PROCESS status", "112 E1_PENDING_SCIENTIFIC_INPUT_PROVENANCE."),
        (
            "O. TEXT status",
            "56 TEXT_E1_INELIGIBLE_PENDING_ALIGNMENT_PROOF; explicit label refinement only, no new alignment evidence.",
        ),
        (
            "P. Q1 protocol sufficiency",
            json.dumps(
                f["q1_protocol_sufficiency_matrix.json"]["status_counts"],
                sort_keys=True,
            )
            + ". Eighteen protocol items assessed, distinct from empirical E1 sufficiency.",
        ),
        (
            "Q. Explanation methods",
            "LR exact analytical logit; RF exact positive-class-probability TreeSHAP; XGBoost/LightGBM exact raw-margin TreeSHAP; approximate=False and tree_path_dependent. LIME/counterfactual exclusions unchanged.",
        ),
        (
            "R. Population policies",
            "TRAIN<=256; T1global<=256 label-blind; local<=8 global subset. Seed20260901, deterministic SHA256 selection; no population selected in R2.",
        ),
        (
            "S. Fidelity/stability/heterogeneity",
            "Original numerical bounds, zero unexplained fraction, seeds20260901–20260920, correlation.70, rank/sign/TV thresholds and>=3family rule preserved without relaxation.",
        ),
        (
            "T. E2 continuity",
            "E2 remains primary analytical fusion; E1 complementary; E3 calibration separate. No SHAP propagation through E2, heterogeneous-scale summation, causal or universal claims.",
        ),
        (
            "U. T1 governance",
            "All new T1 scientific counters0; historical predictive1/1. R2 does not authorize future row access.",
        ),
        ("V. T2 reserve", "DENY_SEALED_REVIEWER_RESERVE; access/query budget0."),
        (
            "W. Governance counters",
            "Model loads/queries, XAI, training/refit/recalibration, metrics, figures, historical mutations and commit/push/PR all0.",
        ),
        (
            "X. Validation",
            json.dumps(
                f.get("validation_results.json", {"status": "PENDING"}), sort_keys=True
            ),
        ),
        (
            "Y.56.3B eligibility",
            f["downstream_56_3b_policy.json"]["SPRINT56_3B_ELIGIBILITY"]
            + "; not AUTHORIZED and not started.",
        ),
        (
            "Z. Final recommendation",
            result
            + ". "
            + f["recommended_next_action.json"]["action"]
            + ". Original byte mismatch, original BLOCKED package and historical mtime uncertainty remain visible.",
        ),
    ]
    ending = (
        "READY FOR HUMAN REVIEW — SPRINT 56.3B MAY BE SEPARATELY AUTHORIZED"
        if result == PASS
        else "FAIL — SPRINT 56.3A SCIENTIFIC INTEGRITY NOT PRESERVED"
        if result == FAIL
        else "BLOCKED — SPRINT 56.3A PROTOCOL REVALIDATION INCOMPLETE"
    )
    return (
        "# Sprint10.8.2.56.3A-R2 — Protocol Freeze Revalidation\n\n"
        + "\n\n".join("## " + a + "\n\n" + b for a, b in sections)
        + "\n\n"
        + ending
        + "\n"
    ).encode()


def write_package(root, output, files):
    root = Path(root).resolve()
    output = Path(output)
    if output.absolute() != root / OUT or output.resolve() != root / OUT:
        raise PermissionError("R2 writes restricted to new namespace")
    VerifiedPackage(OUT, files)
    output.mkdir(parents=True, exist_ok=False)
    for name, raw in sorted(files.items()):
        with (output / name).open("xb") as handle:
            handle.write(raw)
    persisted = {p.name: p.read_bytes() for p in output.iterdir()}
    if persisted != files:
        raise ValidationBlocked("Persisted R2 bytes differ")


def preserve_preexisting(preflight):
    allowed_sources = {
        "src/evaluation/q1_prospective_e1_protocol_freeze.py",
        "tests/evaluation/test_q1_prospective_e1_protocol_freeze.py",
        "tests/evaluation/run_q1_prospective_e1_governance_regressions.py",
        "src/evaluation/q1_prospective_e1_parent_integrity_resolution.py",
        "tests/evaluation/test_q1_prospective_e1_parent_integrity_resolution.py",
    }
    for path, record in preflight["preexisting"].items():
        if not (path.startswith((BASE + "/", R1 + "/")) or path in allowed_sources):
            raise ValidationBlocked("Unrecognized pre-existing path")
        if sha((ROOT / path).read_bytes()) != record["sha256"]:
            raise ValidationBlocked("Pre-existing bytes changed: " + path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--validation", type=Path, required=True)
    args = parser.parse_args()
    try:
        pre = json.loads(args.preflight.read_bytes())
        validation = json.loads(args.validation.read_bytes())
        if (
            git("rev-parse", "--abbrev-ref", "HEAD").strip() != BRANCH
            or git("rev-parse", "HEAD").strip() != pre["HEAD"]
        ):
            raise ValidationBlocked("Branch/HEAD changed")
        preserve_preexisting(pre)
        amendment = read_package(ROOT, R1)
        original = read_package(ROOT, BASE)
        verify_r1(amendment, original)
        tree = git("ls-tree", "-r", "HEAD", "--", "audits")
        diff = git("diff", "HEAD", "--name-only")
        historical_unchanged = (
            tree == pre["historical_git_tree"]
            and diff == ""
            and tree
            == amendment.documents()["preflight.json"]["historical_audit_tree_snapshot"]
        )
        files = revalidate(
            original,
            amendment,
            chronology_metadata(),
            historical_unchanged,
            pre["preexisting"],
        )
        if validation.get("status") != "PASS":
            raise ValidationBlocked("Focused validation incomplete")
        preserve_preexisting(pre)
        if (
            read_package(ROOT, R1).files != amendment.files
            or read_package(ROOT, BASE).files != original.files
        ):
            raise ValidationBlocked("Parent package changed during revalidation")
        files["preflight.json"] = pre
        files["validation_results.json"] = validation
        files["historical_immutability_verification.json"] = {
            "historical_tracked_tree_unchanged": historical_unchanged,
            "tracked_diff_exact": diff,
            "tree_sha256": sha(tree.encode()),
            "preexisting_files_byte_identical": len(pre["preexisting"]),
            "original56_3A_manifest_sha256_before_after": sha(
                original.files["MANIFEST.sha256"]
            ),
            "R1_manifest_sha256_before_after": sha(amendment.files["MANIFEST.sha256"]),
            "historical_Sprint56_1_manifest_unchanged": historical_unchanged,
            "verification_boundary": "Current Git tree and empty tracked diff retain all historical tracked audit bytes, including the old manifest. No historical scientific file opened; R1 and56.3A files individually SHA256-checked before/after.",
        }
        files["implementation_provenance.json"] = {
            "source_sha256": sha(Path(__file__).read_bytes()),
            "test_sha256": sha(
                (
                    ROOT
                    / "tests/evaluation/test_q1_prospective_e1_protocol_revalidation_r2.py"
                ).read_bytes()
            ),
        }
        files["change_classification.json"] = {
            "preexisting": pre["preexisting"],
            "NEW_56_3A_R2": [
                OUT + "/",
                "src/evaluation/q1_prospective_e1_protocol_revalidation_r2.py",
                "tests/evaluation/test_q1_prospective_e1_protocol_revalidation_r2.py",
            ],
        }
        encoded = serialize(files)
        encoded["SPRINT56_3A_R2_PROTOCOL_REVALIDATION_REPORT.md"] = report(files)
        encoded["MANIFEST.sha256"] = manifest_bytes(encoded)
        write_package(ROOT, ROOT / OUT, encoded)
        print(files["protocol_summary.json"]["resolution"])
    except ValidationBlocked as error:
        parser.exit(1, error.result + ": " + str(error) + "\n")


if __name__ == "__main__":
    main()
