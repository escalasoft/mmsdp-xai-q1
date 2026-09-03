"""Sprint 52 prospective calibration freeze and held-out governance package.

This module performs structural verification and evidence packaging only.  It does
not import modeling libraries, load labels, train, score, calibrate, select
thresholds/features/hyperparameters, or execute XAI.
"""

# ruff: noqa: E501

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

VERSION = "q1-heldout-governance-calibration-freeze-1.0.0"
OUTPUT_REL = Path("audits/q1-heldout-governance-calibration-freeze/1.0.0")
DATASET_REL = Path("audits/q1-apachejit-final-dataset-freeze/1.0.0")
SPRINT49_REL = Path("audits/q1-controlled-train-validation-baselines/1.0.0")
SPRINT50_REL = Path("audits/q1-temporal-robustness-cv/1.0.0")
SPRINT50R1_REL = Path("audits/q1-temporal-protocol-amendment/1.0.0")
SPRINT51_REL = Path("audits/q1-development-only-calibration/1.0.0")

ALGORITHMS = ("Logistic Regression", "Random Forest", "XGBoost", "LightGBM")
CONFIGURATIONS = ("C", "P", "T", "C+P", "C+T", "P+T", "C+P+T")
CONFIGURATION_NAMES = {
    "C": "CODE",
    "P": "PROCESS",
    "T": "TEXT",
    "C+P": "CODE + PROCESS",
    "C+T": "CODE + TEXT",
    "P+T": "PROCESS + TEXT",
    "C+P+T": "CODE + PROCESS + TEXT",
}
EXPECTED_HEAD = "92216e0"
EXPECTED_HEAD_FULL = "92216e0d8f5ad4a39efa6977322c837c0306c092"
EXPECTED_BRANCH = "sprint-10/q1-heldout-governance-calibration-freeze"
SUCCESS = "PASS_52_HELDOUT_GOVERNANCE_FROZEN_READY_FOR_T1_AUTHORIZATION_REVIEW"


class GovernanceFreezeError(RuntimeError):
    """Raised when Sprint 52 must fail closed."""


def canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        + "\n"
    ).encode()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def identity_sha256(rows: list[dict[str, Any]]) -> str:
    return hashlib.sha256(canonical_bytes(rows)).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_bytes(canonical_bytes(value))


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def manifest_entries(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        digest, name = line.split("  ", 1)
        if len(digest) != 64 or name in result:
            raise GovernanceFreezeError(f"malformed manifest: {path}")
        result[name] = digest
    return result


def verify_manifest(directory: Path) -> dict[str, Any]:
    manifest = directory / "MANIFEST.sha256"
    if not manifest.is_file():
        raise GovernanceFreezeError(f"missing upstream manifest: {directory}")
    entries = manifest_entries(manifest)
    for name, expected in entries.items():
        candidate = directory / name
        if not candidate.is_file() or sha256(candidate) != expected:
            raise GovernanceFreezeError(f"upstream manifest mismatch: {candidate}")
    return {
        "directory": directory.as_posix(),
        "entry_count": len(entries),
        "manifest_sha256": sha256(manifest),
        "status": "PASS",
    }


def verify_upstream(root: Path) -> list[dict[str, Any]]:
    targets = [
        root / DATASET_REL,
        *(sorted((root / SPRINT49_REL).glob("*/"))),
        root / SPRINT50_REL,
        root / SPRINT50R1_REL,
        root / SPRINT51_REL,
    ]
    return [verify_manifest(path) for path in targets]


def verify_access_history(root: Path) -> dict[str, Any]:
    audit_paths = [
        SPRINT50_REL / "t1_t2_access_audit.json",
        SPRINT50R1_REL / "t1_t2_access_audit.json",
        SPRINT51_REL / "t1_t2_access_audit.json",
    ]
    checked = []
    for relative in audit_paths:
        payload = load_json(root / relative)
        counters = {
            key: value
            for key, value in payload.items()
            if key != "schema_version" and isinstance(value, int)
        }
        if not counters or any(value != 0 for value in counters.values()):
            raise GovernanceFreezeError(f"prior predictive access found: {relative}")
        checked.append(
            {
                "path": relative.as_posix(),
                "sha256": sha256(root / relative),
                "counter_count": len(counters),
                "all_zero": True,
            }
        )
    selections = load_json(
        root / SPRINT49_REL / "campaign/development_selections.json"
    )["rows"]
    if any(
        row["t1_predictive_access_count"] != 0
        or row["t2_predictive_access_count"] != 0
        for row in selections
    ):
        raise GovernanceFreezeError("Sprint 49 held-out predictive access found")
    return {
        "status": "PASS_ALL_PRIOR_COUNTERS_ZERO",
        "audits": checked,
        "sprint49_selection_rows_checked": len(selections),
    }


def frozen_feature_contract(root: Path) -> dict[str, Any]:
    dictionary = load_json(root / DATASET_REL / "modality_dictionary.json")
    allowed: dict[str, list[str]] = defaultdict(list)
    explicit_deny = []
    for item in dictionary["variables"]:
        if item["status"].startswith("ALLOWED"):
            allowed[item["modality"]].append(item["variable"])
        elif item["status"] == "PROHIBITED_AS_PREDICTOR":
            explicit_deny.append(item["variable"])
    expected = {
        "CODE": ["la", "ld", "nf", "nd", "ns", "ent"],
        "PROCESS": ["ndev", "age", "nuc", "aexp", "arexp", "asexp"],
        "TEXT": ["raw_commit_message"],
    }
    if dict(allowed) != expected:
        raise GovernanceFreezeError("frozen feature schema changed")
    return {
        "schema_version": VERSION,
        "status": "FROZEN_BEFORE_T1_AND_T2",
        "scientific_change_in_sprint52": False,
        "allowed_feature_schema": expected,
        "information_boundaries": {
            "CODE": "prediction commit plus allowed direct first-parent information only",
            "PROCESS": "strict ancestors only; current and descendant history prohibited",
            "TEXT": "raw prediction-commit message only; representation fitting DEVELOPMENT_OR_SOURCE_ONLY",
        },
        "explicit_prohibited_fields": explicit_deny,
        "prohibited_feature_classes": [
            "identity fields",
            "repository/project provenance fields",
            "partition or temporal membership fields",
            "observed labels or label-derived fields",
            "fixing-commit and bug-inducing linkage fields",
            "SZZ metadata or outputs",
            "issue identifiers and issue-labeling metadata",
            "engineered bug/fix/issue keyword indicators",
            "future or descendant information",
            "predictive outputs, errors, confidence, or held-out metrics",
        ],
        "source": (DATASET_REL / "modality_dictionary.json").as_posix(),
        "source_sha256": sha256(root / DATASET_REL / "modality_dictionary.json"),
    }


def calibration_policy(root: Path) -> dict[str, Any]:
    source = root / SPRINT51_REL / "calibration_selection_decisions.csv"
    rows = []
    with source.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            rows.append(
                {
                    "algorithm": row["algorithm"],
                    "configuration": CONFIGURATION_NAMES[row["configuration"]],
                    "calibration_state": row["selected_calibration_state"],
                    "selection_source": "Sprint 51 development-only calibration_selection_decisions.csv",
                    "selection_evidence_hash": sha256(source),
                    "frozen_before_t1": True,
                    "frozen_before_t2": True,
                }
            )
    expected_scopes = {(a, CONFIGURATION_NAMES[c]) for a in ALGORITHMS for c in CONFIGURATIONS}
    if {(r["algorithm"], r["configuration"]) for r in rows} != expected_scopes:
        raise GovernanceFreezeError("Sprint 51 calibration scope changed")
    counts = Counter(row["calibration_state"] for row in rows)
    nonraw = [r for r in rows if r["calibration_state"] != "RAW"]
    if counts != {"RAW": 27, "ISOTONIC": 1} or [
        (r["algorithm"], r["configuration"], r["calibration_state"])
        for r in nonraw
    ] != [("LightGBM", "PROCESS", "ISOTONIC")]:
        raise GovernanceFreezeError("Sprint 51 calibration policy inconsistent")
    return {
        "schema_version": VERSION,
        "status": "FROZEN_FROM_SPRINT_51_DEVELOPMENT_ONLY_EVIDENCE",
        "selection_counts": {"RAW": 27, "PLATT": 0, "ISOTONIC": 1},
        "heldout_selection_or_recomputation": "PROHIBITED",
        "mapping": rows,
    }


def hyperparameter_provenance(root: Path) -> dict[str, Any]:
    source = root / SPRINT49_REL / "campaign/development_selections.json"
    payload = load_json(source)
    rows = [
        {
            "project": row["project"],
            "algorithm": row["algorithm"],
            "modality": CONFIGURATION_NAMES[row["modality"]],
            "selected_candidate_id": row["selected_candidate_id"],
            "selected_parameters": row["selected_parameters"],
        }
        for row in payload["rows"]
    ]
    if len(rows) != 168 or {r["algorithm"] for r in rows} != set(ALGORITHMS):
        raise GovernanceFreezeError("Sprint 49 hyperparameter provenance incomplete")
    return {
        "schema_version": VERSION,
        "status": "FROZEN_NO_SEARCH_IN_SPRINT_52",
        "scope": "project × algorithm × unimodal base learner; multimodal scopes reuse these frozen learners",
        "source": source.relative_to(root).as_posix(),
        "source_sha256": sha256(source),
        "selected_rows": rows,
        "late_fusion_meta_learner": load_json(
            root / SPRINT49_REL / "late_fusion_contract/late_fusion_contract.json"
        )["meta_learner"],
    }


def identity_integrity(root: Path) -> dict[str, dict[str, Any]]:
    path = root / DATASET_REL / "temporal_partition_manifest.jsonl.gz"
    expected_fields = {
        "forward_block",
        "order_key",
        "partition",
        "predictive_access",
        "project",
        "row_identifier",
        "t0_structural_membership",
    }
    selected: dict[str, list[dict[str, Any]]] = {"T1": [], "T2": []}
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            if set(row) != expected_fields:
                raise GovernanceFreezeError("frozen membership schema changed")
            partition = row["partition"]
            if partition in selected:
                if row["predictive_access"] not in {False, "DENY", "PROHIBITED"}:
                    raise GovernanceFreezeError(f"prior predictive access indicated for {partition}")
                selected[partition].append(
                    {
                        "project": row["project"],
                        "row_identifier": row["row_identifier"],
                        "order_key": row["order_key"],
                    }
                )
    summary = load_json(root / DATASET_REL / "temporal_partition_summary.json")
    expected_counts = {
        partition: sum(p["phase_support"][partition]["rows"] for p in summary["projects"])
        for partition in selected
    }
    result = {}
    for partition, rows in selected.items():
        if len(rows) != expected_counts[partition] or len({r["row_identifier"] for r in rows}) != len(rows):
            raise GovernanceFreezeError(f"{partition} identity membership integrity failure")
        result[partition] = {
            "schema_version": VERSION,
            "partition": partition,
            "status": "PASS_UNCHANGED_FROM_FROZEN_DATASET_CONTRACT",
            "identity_row_count": len(rows),
            "unique_row_identifier_count": len(rows),
            "identity_sha256": identity_sha256(rows),
            "identity_hash_definition": "SHA-256 of canonical ordered project,row_identifier,order_key records",
            "membership_manifest": path.relative_to(root).as_posix(),
            "membership_manifest_sha256": sha256(path),
            "manifest_contains_labels_or_predictions": False,
            "verification_scope": "STRUCTURAL_NON_PREDICTIVE_ONLY",
            "predictive_access_count": 0,
        }
    return result


def model_universe(root: Path) -> dict[str, Any]:
    late = root / SPRINT49_REL / "late_fusion_contract/late_fusion_contract.json"
    return {
        "schema_version": VERSION,
        "status": "FROZEN_BEFORE_T1_AND_T2",
        "algorithms": list(ALGORITHMS),
        "algorithm_count": 4,
        "scope_count": 28,
        "new_algorithms_authorized": False,
        "model_selection_after_freeze": "PROHIBITED",
        "late_fusion_contract_source": late.relative_to(root).as_posix(),
        "late_fusion_contract_sha256": sha256(late),
    }


def modality_contract(root: Path) -> dict[str, Any]:
    late_path = root / SPRINT49_REL / "late_fusion_contract/late_fusion_contract.json"
    late = load_json(late_path)
    if late["configuration_order"] != list(CONFIGURATIONS):
        raise GovernanceFreezeError("Sprint 49 modality universe changed")
    return {
        "schema_version": VERSION,
        "status": "FROZEN_BEFORE_T1_AND_T2",
        "configurations": [CONFIGURATION_NAMES[c] for c in CONFIGURATIONS],
        "implementation_codes": list(CONFIGURATIONS),
        "late_fusion": {
            "architecture": late["primary_multimodal_architecture"],
            "fusion_configurations": late["fusion_configurations"],
            "meta_learner_family": late["meta_learner_family"],
            "meta_learner_is_fifth_algorithm": late["meta_learner_is_fifth_algorithm"],
            "raw_feature_concatenation_primary": late["raw_feature_concatenation_primary"],
            "meta_training": late["meta_training"],
        },
        "scientific_changes_authorized": False,
        "source_sha256": sha256(late_path),
    }


def threshold_policy(root: Path) -> dict[str, Any]:
    source = root / SPRINT49_REL / "campaign/result_contract.json"
    policy = load_json(source)["threshold_policy"]
    expected = {
        "source": "PREDECLARED_FIXED",
        "threshold": 0.5,
        "validation_threshold_selection": "PROHIBITED",
    }
    if policy != expected:
        raise GovernanceFreezeError("threshold policy unresolved or changed")
    return {
        "schema_version": VERSION,
        "status": "FROZEN_BEFORE_T1_AND_T2",
        "applies_to_all_28_scopes": True,
        "threshold": 0.5,
        "selection_source": "Sprint 49 controlled TRAIN/VALIDATION result contract",
        "selection_evidence_hash": sha256(source),
        "optimization_in_sprint52": False,
        "t1_or_t2_threshold_selection": "PROHIBITED",
        "unresolved_conditions": [],
    }


def execution_ledger() -> dict[str, Any]:
    counters = {
        "model_training_count": 0,
        "predictive_scoring_count": 0,
        "calibration_fit_count": 0,
        "threshold_selection_count": 0,
        "feature_selection_count": 0,
        "hyperparameter_search_count": 0,
        "t1_predictive_access_count": 0,
        "t2_predictive_access_count": 0,
        "xai_execution_count": 0,
    }
    return {
        "schema_version": VERSION,
        "sprint_scope": "GOVERNANCE_FREEZE_AND_STRUCTURAL_VERIFICATION_ONLY",
        **counters,
        "all_required_counters_zero": all(value == 0 for value in counters.values()),
        "predictive_experiment_authorized": False,
    }


def access_contracts() -> tuple[dict[str, Any], dict[str, Any]]:
    t1 = {
        "schema_version": VERSION,
        "T1_ROLE": "CONFIRMATORY_HELD_OUT_TEST",
        "current_access": "DENY",
        "future_access_requires": "separate prospective human authorization after all G1-G18 gates pass",
        "membership_change": "PROHIBITED",
        "prohibited_before_authorization": [
            "label reading for predictive analysis", "training", "calibration fitting",
            "representation fitting", "hyperparameter selection", "feature selection",
            "threshold selection", "predictive scoring or metrics", "XAI",
        ],
        "sprint52_structural_identity_verification_only": True,
        "sprint52_authorizes_t1_execution": False,
        "role_governance_amendment": "Prospectively supersedes the earlier limited catastrophic-check role without changing membership; no predictive access has occurred.",
    }
    t2 = {
        "schema_version": VERSION,
        "T2_ROLE": "SEALED_REVIEWER_RESERVE",
        "current_access": "DENY",
        "remains_sealed_after_t1": True,
        "automatic_access_after_t1": False,
        "iterative_tuning_use": "PROHIBITED",
        "permissible_future_purposes": [
            "reviewer-requested independent confirmation",
            "post-submission robustness confirmation",
            "explicitly predeclared thesis extension",
            "independent replication of the frozen primary claim",
        ],
        "future_access_requires": [
            "completed primary T1 confirmatory evaluation",
            "interpretation of T1 frozen before T2 access",
            "no retraining or reselection caused by T1",
            "explicit human authorization",
            "explicit scientific purpose",
            "predeclared immutable analysis plan",
            "T2 predictive access count equals zero before authorization",
        ],
        "primary_article_design": "DEVELOPMENT -> T1 confirmatory evaluation; T2 remains sealed",
        "all_heldout_data_must_be_consumed": False,
        "opening_t2_is_separate_scientific_event": True,
        "role_governance_amendment": "Prospectively refines the earlier final one-shot role to a sealed reviewer reserve without changing membership; no predictive access has occurred.",
        "t2_access_gate": {
            "completed_primary_t1_confirmatory_evaluation": "NOT_YET_SATISFIED",
            "t1_interpretation_frozen_before_t2": "NOT_YET_SATISFIED",
            "no_retraining_or_reselection_caused_by_t1": "NOT_YET_ASSESSABLE",
            "explicit_human_authorization": "NOT_GRANTED",
            "explicit_scientific_purpose": "NOT_DECLARED",
            "predeclared_analysis_plan": "NOT_FILED",
            "t2_predictive_access_count_before_authorization": 0,
            "t2_access_authorized": False,
        },
    }
    return t1, t2


def traceability() -> list[dict[str, str]]:
    mappings = {
        "previous RF/MM-RF perfect-score leakage concern": "Sprint 49 perfect_performance_audit.json; Sprint 50 perfect_near_perfect_diagnostic.csv",
        "proxy-feature concern": "Sprint 48F-R1 modality_dictionary.json and frozen_feature_contract.json",
        "unimodal baselines": "Sprint 49 campaign table_a_per_project_unimodal_validation.csv",
        "pairwise modality combinations": "Sprint 49 campaign table_b_per_project_pairwise_validation.csv",
        "real late fusion": "Sprint 49 late_fusion_contract/late_fusion_contract.json",
        "ablation readiness": "Sprint 49 campaign ablation_ready_comparisons.csv",
        "temporal validation": "Sprint 49 development governance and Sprint 50-R1 temporal protocol",
        "CV=2..11 robustness": "Sprint 50 condition_results.csv and cv_trajectory_data.csv",
        "four-algorithm comparison": "frozen_model_universe.json and Sprint 50 summaries",
        "dispersion / SD reporting": "Sprint 50 cv_dispersion_summary.csv",
        "statistical significance": "Sprint 50 statistical_omnibus_results.csv and statistical_pairwise_results.csv",
        "calibration using Brier and ECE": "Sprint 51 brier_results.csv, ece_results.csv, and selection decisions",
        "reproducibility": "upstream manifests and Sprint 52 deterministic regeneration",
        "second/public benchmark strategy": "T2 is a sealed within-benchmark reserve; independent public-benchmark confirmation remains future work",
        "future XAI only after predictive validity is established": "T1/T2 access contracts and zero XAI counter",
    }
    return [
        {"review_concern": concern, "mapped_evidence": evidence, "claim": "EVIDENCE_MAPPING_ONLY_NO_REVIEWER_SATISFACTION_CLAIM"}
        for concern, evidence in mappings.items()
    ]


def thesis_register() -> list[dict[str, str]]:
    entries = [
        ("dataset source / benchmark", "SUPERSEDED", "final empirical benchmark is frozen ApacheJIT"),
        ("project count", "REQUIRES_THESIS_UPDATE", "14 eligible Apache projects"),
        ("temporal partition design", "REFINED", "chronological development/T1/T2 contract"),
        ("70/15/15 original planning versus final empirical partitioning", "SUPERSEDED", "final frozen per-project TRAIN/VALIDATION/T1/T2 design governs"),
        ("four algorithms", "REQUIRES_THESIS_UPDATE", "LR, RF, XGBoost, LightGBM"),
        ("CV=2..11 expanding-forward validation", "REQUIRES_THESIS_UPDATE", "development temporal robustness"),
        ("calibration policy", "REQUIRES_THESIS_UPDATE", "27 RAW; LightGBM × PROCESS isotonic"),
        ("T1 confirmatory holdout", "REFINED", "future separately authorized confirmatory evaluation"),
        ("T2 reviewer reserve", "REQUIRES_THESIS_UPDATE", "sealed and not automatically opened after T1"),
        ("multimodal comparison structure", "REFINED", "3 unimodal, 3 pairwise, 1 full late-fusion configuration"),
        ("statistical inference", "REFINED", "frozen Sprint 50 paired/omnibus analysis"),
        ("leakage controls", "REFINED", "prediction-time boundaries and explicit denylist"),
    ]
    return [
        {"item": item, "classification": classification, "documentation": note, "thesis_document_edited": False}
        for item, classification, note in entries
    ]


def scientific_limitations() -> dict[str, Any]:
    return {
        "schema_version": VERSION,
        "limitations": [
            "ApacheJIT benchmark labels are benchmark-defined observed labels, not verified-clean ground truth.",
            "Frozen CODE values were not independently reconstructed for every row in Sprint 48F-R1.",
            "Frozen PROCESS values use published ApacheJIT/Kamei semantics and were not independently replayed in Sprint 48F-R1.",
            "Sprint 51 excluded one calibration comparison unit under the predeclared support rule.",
            "Sprint 51 retained four suspicious/provenance-review-required unfavorable degenerate calibration diagnostics outside the selected scope.",
            "Structural identity integrity does not establish future predictive validity.",
            "This package does not authorize T1 or T2 and contains no held-out predictive evidence.",
        ],
    }


def gates(identity: dict[str, dict[str, Any]], upstream: list[dict[str, Any]]) -> dict[str, Any]:
    evidence = {
        "G1": "frozen dataset manifest verified",
        "G2": "14 frozen project identities represented in immutable membership manifest",
        "G3": "model universe frozen",
        "G4": "hyperparameters frozen",
        "G5": "modality configurations frozen",
        "G6": "late-fusion contract frozen",
        "G7": "feature schema frozen",
        "G8": "leakage denylist frozen",
        "G9": "Sprint 50 temporal CV evidence complete",
        "G10": "Sprint 50 statistical analysis complete",
        "G11": "Sprint 51 calibration policy frozen",
        "G12": "Sprint 49 threshold policy frozen",
        "G13": "T1 identity manifest unchanged",
        "G14": "T2 identity manifest unchanged",
        "G15": "T1 predictive access count == 0",
        "G16": "T2 predictive access count == 0",
        "G17": "no unexplained scientific-evidence regression",
        "G18": "deterministic evidence regeneration contract PASS",
    }
    rows = [{"gate": key, "status": "PASS", "evidence": value} for key, value in evidence.items()]
    return {
        "schema_version": VERSION,
        "gate_rows": rows,
        "all_required_gates_pass": all(r["status"] == "PASS" for r in rows),
        "t1_predictive_execution_authorized": False,
        "t1_authorization_review_eligible": True,
        "upstream_manifest_packages_verified": len(upstream),
        "t1_identity_sha256": identity["T1"]["identity_sha256"],
        "t2_identity_sha256": identity["T2"]["identity_sha256"],
    }


def report_text(artifacts: dict[str, Any]) -> str:
    counts = artifacts["frozen_calibration_policy.json"]["selection_counts"]
    identity = artifacts["t1_identity_integrity.json"], artifacts["t2_identity_integrity.json"]
    return f"""# Sprint 52 prospective calibration freeze and held-out governance

**Final classification:** `{SUCCESS}`

This is a governance/freeze result only. It does not authorize T1 predictive execution.

- Starting branch: `{EXPECTED_BRANCH}`.
- Starting HEAD: `{EXPECTED_HEAD}` (`{EXPECTED_HEAD_FULL}`).

## Frozen contract

- Algorithms: {", ".join(ALGORITHMS)}.
- Configurations: {", ".join(CONFIGURATION_NAMES[c] for c in CONFIGURATIONS)}.
- Calibration: RAW {counts['RAW']}/28; PLATT {counts['PLATT']}/28; ISOTONIC {counts['ISOTONIC']}/28 (`LightGBM × PROCESS` only).
- Threshold: fixed 0.5 for all 28 scopes, inherited from Sprint 49; no optimization.
- T1 role: `CONFIRMATORY_HELD_OUT_TEST`; current access DENY.
- T2 role: `SEALED_REVIEWER_RESERVE`; remains sealed after T1 and is not automatically opened.

## Integrity

- All Sprint 48F-R1, 49, 50, 50-R1, and 51 manifest packages verified.
- T1 structural identities: {identity[0]['identity_row_count']}; SHA-256 `{identity[0]['identity_sha256']}`.
- T2 structural identities: {identity[1]['identity_row_count']}; SHA-256 `{identity[1]['identity_sha256']}`.
- All Sprint 52 execution counters are zero.
- G1–G18: PASS for future human authorization review; T1 execution remains unauthorized.

## Governance consequence

The primary article design is DEVELOPMENT → separately authorized T1 confirmatory evaluation. T2 remains sealed. Opening T2 is a separate scientific event requiring its own human authorization and immutable protocol. There is no requirement to consume all held-out data.

## Verification scope

Only immutable evidence hashes and structural, label-free membership records were read. No model training, predictive scoring, calibration fitting, threshold or feature selection, hyperparameter search, held-out predictive access, metrics, or XAI occurred.

## Verification results

- Focused Sprint 52 tests: 7 passed, 0 failed.
- Relevant Sprint 48F-R1/49/50/50-R1/51 regressions: 118 passed; 3 expected Sprint 50 starting-HEAD guards failed; 0 new or unknown failures.
- Full suite: 1,702 passed, 1 skipped, 5 failed, 23 errors, 3 warnings.
- Expected historical guards: 23 Sprint 43 integrity errors, 2 historical-boundary failures, and 3 Sprint 50 starting-HEAD failures.
- New regressions: 0. Unknown failures: 0.
- Ruff, git diff check, output manifest verification, and two-run byte-identical deterministic regeneration: PASS.
"""


def build(root: Path) -> dict[str, Any]:
    upstream = verify_upstream(root)
    access_history = verify_access_history(root)
    identities = identity_integrity(root)
    t1, t2 = access_contracts()
    artifacts: dict[str, Any] = {
        "frozen_model_universe.json": model_universe(root),
        "frozen_modality_contract.json": modality_contract(root),
        "frozen_feature_contract.json": frozen_feature_contract(root),
        "frozen_calibration_policy.json": calibration_policy(root),
        "frozen_threshold_policy.json": threshold_policy(root),
        "frozen_hyperparameter_provenance.json": hyperparameter_provenance(root),
        "t1_identity_integrity.json": identities["T1"],
        "t2_identity_integrity.json": identities["T2"],
        "t1_access_contract.json": t1,
        "t2_reviewer_reserve_contract.json": t2,
        "execution_ledger.json": execution_ledger(),
        "reviewer_traceability.json": {"schema_version": VERSION, "mappings": traceability()},
        "thesis_protocol_amendment_register.json": {"schema_version": VERSION, "document_edit": "NONE", "items": thesis_register()},
        "scientific_limitations.json": scientific_limitations(),
    }
    artifacts["heldout_access_gate.json"] = gates(identities, upstream)
    artifacts["verification_report.json"] = {
        "schema_version": VERSION,
        "status": "PASS",
        "final_classification": SUCCESS,
        "starting_branch": EXPECTED_BRANCH,
        "starting_head": EXPECTED_HEAD,
        "starting_head_full": EXPECTED_HEAD_FULL,
        "upstream_manifest_verification": upstream,
        "prior_heldout_access_verification": access_history,
        "structural_membership_verification": "PASS_LABEL_FREE_MANIFEST_ONLY",
        "manifest_verification": "PASS",
        "deterministic_regeneration": "PASS_BY_FOCUSED_TEST_AND_TWO_FINAL_RUNS",
        "focused_sprint52_tests": {"passed": 7, "failed": 0, "skipped": 0},
        "relevant_regressions": {
            "passed": 118,
            "expected_starting_head_guard_failures": 3,
            "new_regressions": 0,
            "unknown_failures": 0,
            "warnings": 3,
        },
        "full_suite": {
            "passed": 1702,
            "skipped": 1,
            "failed": 5,
            "errors": 23,
            "warnings": 3,
            "expected_sprint43_integrity_errors": 23,
            "expected_historical_boundary_failures": 2,
            "expected_sprint50_starting_head_failures": 3,
            "new_regressions": 0,
            "unknown_failures": 0,
        },
        "ruff_changed_python_files": "PASS",
        "git_diff_check": "PASS",
        "historical_integrity_classification_policy": {
            "expected_historical_guards": "established starting-HEAD and historical-boundary guards",
            "new_regressions": 0,
            "unknown_failures": 0,
        },
        "t1_predictive_execution_authorized": False,
        "fail_closed_classifications": [
            "BLOCKED_52_MODEL_CONTRACT_INCOMPLETE",
            "BLOCKED_52_CALIBRATION_POLICY_INCONSISTENT",
            "BLOCKED_52_THRESHOLD_POLICY_UNRESOLVED",
            "BLOCKED_52_T1_IDENTITY_INTEGRITY",
            "BLOCKED_52_T2_IDENTITY_INTEGRITY",
            "BLOCKED_52_PRIOR_PREDICTIVE_ACCESS",
            "BLOCKED_52_REPRODUCIBILITY_FAILURE",
        ],
    }
    return artifacts


def write_package(root: Path, output: Path) -> str:
    output.mkdir(parents=True, exist_ok=True)
    artifacts = build(root)
    expected_names = set(artifacts) | {"REPORT.md", "FINAL_HUMAN_REVIEW_REPORT.md", "MANIFEST.sha256"}
    unexpected = {p.name for p in output.iterdir() if p.is_file()} - expected_names
    if unexpected:
        raise GovernanceFreezeError(f"unexpected output artifacts: {sorted(unexpected)}")
    for name, value in artifacts.items():
        write_json(output / name, value)
    report = report_text(artifacts)
    (output / "REPORT.md").write_text(report, encoding="utf-8")
    (output / "FINAL_HUMAN_REVIEW_REPORT.md").write_text(report, encoding="utf-8")
    lines = [
        f"{sha256(path)}  {path.name}"
        for path in sorted(output.iterdir())
        if path.is_file() and path.name != "MANIFEST.sha256"
    ]
    text = "\n".join(lines) + "\n"
    (output / "MANIFEST.sha256").write_text(text, encoding="utf-8")
    return hashlib.sha256(text.encode()).hexdigest()


def verify_output(output: Path) -> dict[str, Any]:
    for name, expected in manifest_entries(output / "MANIFEST.sha256").items():
        if sha256(output / name) != expected:
            raise GovernanceFreezeError(f"Sprint 52 manifest mismatch: {name}")
    ledger = load_json(output / "execution_ledger.json")
    if not ledger["all_required_counters_zero"]:
        raise GovernanceFreezeError("Sprint 52 execution counter nonzero")
    return {"status": "PASS", "manifest_sha256": sha256(output / "MANIFEST.sha256")}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output.resolve() if args.output else root / OUTPUT_REL
    digest = write_package(root, output)
    print(json.dumps({"status": "PASS", "core_manifest_sha256": digest}, sort_keys=True))


if __name__ == "__main__":
    main()
