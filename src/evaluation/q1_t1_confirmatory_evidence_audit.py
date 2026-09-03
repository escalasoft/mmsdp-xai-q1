"""Deterministic post-execution audit of sealed Sprint 54 T1 evidence."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import os
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from evaluation.q1_t1_confirmatory_execution import (
    AUTH_REL,
    ENGINE_REL,
    EVIDENCE_FIELDS,
    EXPECTED_EVIDENCE_ROWS,
    EXPECTED_T1_HASH,
    EXPECTED_T1_ROWS,
    EXPECTED_T2_HASH,
    METRICS,
    SPRINT53_REL,
    THRESHOLD,
    _ablation_rows,
    _aggregate_metrics,
    _calibration_rows,
    _comparison_rows,
    _project_metrics,
    _reliability_rows,
    _statistical_rows,
    canonical_bytes,
    file_sha256,
    load_json,
    verify_manifest,
)

VERSION = "q1-t1-confirmatory-evidence-audit-1.0.0"
RESULTS_REL = AUTH_REL / "results"
AUDIT_REL = AUTH_REL / "block6_evidence_audit" / "1.0.0"
EXPECTED_RESULTS_MANIFEST_SHA256 = (
    "f396cfa0db8d01c8c1392fe7bb8affe8413638e3c0e20a3c113d7fe94a6d3a7e"
)
EXPECTED_EVIDENCE_SHA256 = (
    "eb4b6956b185e63cd322d92b8cdf96f53fcb09ef83b6a16f2334d660c6f5adc8"
)


class EvidenceAuditError(RuntimeError):
    """A fail-closed inconsistency in sealed confirmatory evidence."""


def _atomic_json(path: Path, value: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(canonical_bytes(value))
    os.replace(temporary, path)


def _csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def _expected_csv(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [
        {key: "" if value is None else str(value) for key, value in row.items()}
        for row in rows
    ]


def _reconcile_csv(path: Path, expected: list[dict[str, Any]]) -> None:
    if _csv_rows(path) != _expected_csv(expected):
        raise EvidenceAuditError(f"sealed table does not reconcile: {path.name}")


def _load_evidence(path: Path) -> list[dict[str, Any]]:
    rows = []
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            if set(row) != set(EVIDENCE_FIELDS) or len(row) != len(EVIDENCE_FIELDS):
                raise EvidenceAuditError("sealed evidence schema changed")
            rows.append(row)
    return rows


def _verify_execution_integrity(
    root: Path, evidence: list[dict[str, Any]]
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    results = root / RESULTS_REL
    started = load_json(results / "execution_started.json")
    completed = load_json(results / "execution_completed.json")
    integrity = load_json(results / "post_execution_integrity.json")
    keys = [
        (row["row_identifier"], row["algorithm"], row["configuration"])
        for row in evidence
    ]
    identities = {row["row_identifier"] for row in evidence}
    project_scopes = {
        (row["project"], row["algorithm"], row["configuration"]) for row in evidence
    }
    scopes = {(row["algorithm"], row["configuration"]) for row in evidence}
    probabilities = np.asarray(
        [
            value
            for row in evidence
            for value in (
                row["raw_predicted_probability"],
                row["final_frozen_probability"],
            )
        ],
        dtype=float,
    )
    checks = (
        len(evidence) == EXPECTED_EVIDENCE_ROWS,
        len(identities) == EXPECTED_T1_ROWS,
        len(keys) == len(set(keys)),
        len(scopes) == 28,
        len(project_scopes) == 392,
        np.isfinite(probabilities).all(),
        ((probabilities >= 0) & (probabilities <= 1)).all(),
        integrity["status"] == "PASS_COMPLETE_EVIDENCE",
        integrity["duplicate_identity_scope_rows"] == 0,
        integrity["missing_predictions"] == 0,
        integrity["missing_probabilities"] == 0,
        integrity["development_t1_overlap"] == 0,
        integrity["t2_contamination"] == 0,
        integrity["leakage_contract_violations"] == 0,
        completed["t1_predictive_access_count"] == 1,
        completed["predictive_scoring_count"] == 1,
        completed["t2_predictive_access_count"] == 0,
        completed["xai_execution_count"] == 0,
        completed["t1_rerun_permitted"] is False,
        started["execution_attempt"] == 1,
        started["t1_identity_sha256"] == EXPECTED_T1_HASH,
        started["t2_identity_sha256"] == EXPECTED_T2_HASH,
        completed["evidence_sha256"] == EXPECTED_EVIDENCE_SHA256,
        file_sha256(results / "t1_prediction_evidence.jsonl.gz")
        == EXPECTED_EVIDENCE_SHA256,
    )
    if not all(checks):
        raise EvidenceAuditError("sealed execution-integrity invariant failed")
    execution_ids = {row["execution_identifier"] for row in evidence}
    if execution_ids != {completed["execution_identifier"]}:
        raise EvidenceAuditError("execution identifier provenance changed")
    return started, completed, integrity


def _verify_provenance(
    root: Path, evidence: list[dict[str, Any]]
) -> tuple[dict[str, Any], dict[str, Any]]:
    readiness = load_json(root / ENGINE_REL / "engine_readiness.json")
    plan = {
        (row["project"], row["algorithm"], row["configuration"]): row
        for row in readiness["plan"]
    }
    calibration = Counter()
    multimodal = 0
    for row in evidence:
        key = row["project"], row["algorithm"], row["configuration"]
        frozen = plan.get(key)
        if (
            frozen is None
            or row["model_identity_sha256"] != frozen["model_identity_sha256"]
        ):
            raise EvidenceAuditError("model identity/provenance mismatch")
        model = row["model_provenance"]
        calibrator = row["calibration_provenance"]
        if (
            model["training_partition"] != "TRAIN"
            or model["train_identity_sha256"] != frozen["train_identity_sha256"]
            or model["selected_candidate_ids"] != frozen["selected_candidate_ids"]
            or calibrator != frozen["calibration"]
            or row["fixed_threshold"] != THRESHOLD
            or row["fixed_threshold_prediction"]
            != int(row["final_frozen_probability"] >= THRESHOLD)
        ):
            raise EvidenceAuditError(
                "frozen model/calibration/threshold provenance drift"
            )
        calibration[key] = row["calibration_state"]
        if "+" in row["configuration"]:
            fusion = model["late_fusion"]
            if (
                fusion["architecture"] != "DECISION_LEVEL_STACKING_LATE_FUSION"
                or not fusion["independently_learned_base_modalities"]
                or fusion["raw_feature_concatenation"]
                or fusion["averaging"]
                or fusion["voting"]
            ):
                raise EvidenceAuditError("frozen late-fusion contract drift")
            multimodal += 1
    states = Counter(calibration.values())
    if states != Counter({"RAW": 378, "ISOTONIC": 14}):
        raise EvidenceAuditError("calibration project-scope mapping changed")
    isotonic = [key for key, state in calibration.items() if state == "ISOTONIC"]
    if any(key[1:] != ("LightGBM", "P") for key in isotonic):
        raise EvidenceAuditError("isotonic scope identity changed")
    return readiness, {
        "status": "PASS",
        "project_scope_counts": dict(states),
        "isotonic_scope": "LightGBM + PROCESS",
        "isotonic_project_scopes": len(isotonic),
        "threshold": THRESHOLD,
        "multimodal_evidence_rows": multimodal,
        "t1_calibration_fit_or_selection": False,
        "t1_meta_learner_fit": False,
    }


def _reconcile_results(
    root: Path, evidence: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    results = root / RESULTS_REL
    project = _project_metrics(evidence)
    aggregate = _aggregate_metrics(project)
    unimodal, pairwise = _comparison_rows(root, project)
    omnibus, statistics = _statistical_rows(project)
    calibration = _calibration_rows(evidence)
    ablation = _ablation_rows(project)
    reliability = _reliability_rows(evidence)
    reconciliations = {
        "T1-A_per_project_algorithm_configuration_metrics.csv": project,
        "T1-B_aggregate_algorithm_configuration_metrics.csv": aggregate,
        "T1-C_full_vs_frozen_best_unimodal.csv": unimodal,
        "T1-D_full_vs_frozen_best_pairwise.csv": pairwise,
        "T1-E_statistical_tests.csv": statistics,
        "T1-F_calibration_results.csv": calibration,
        "T1-G_ablation_modality_contributions.csv": ablation,
        "statistical_omnibus_results.csv": omnibus,
        "T1-FIG-1_pr_auc_data.csv": [
            row for row in aggregate if row["metric"] == "PR_AUC"
        ],
        "T1-FIG-2_mcc_data.csv": [row for row in aggregate if row["metric"] == "MCC"],
        "T1-FIG-4_ablation_data.csv": ablation,
        "T1-FIG-5_reliability_data.csv": reliability,
    }
    for name, expected in reconciliations.items():
        _reconcile_csv(results / name, expected)
    index = {
        (row["algorithm"], row["configuration"], row["metric"]): row
        for row in aggregate
    }
    descriptive = {
        "best_unimodal_t1_pr_auc": {
            "algorithm": "XGBoost",
            "configuration": "C",
            "value": index["XGBoost", "C", "PR_AUC"]["mean"],
        },
        "best_pairwise_t1_pr_auc": {
            "algorithm": "XGBoost",
            "configuration": "C+P",
            "value": index["XGBoost", "C+P", "PR_AUC"]["mean"],
        },
        "full_multimodal_xgboost_t1_pr_auc": {
            "algorithm": "XGBoost",
            "configuration": "C+P+T",
            "value": index["XGBoost", "C+P+T", "PR_AUC"]["mean"],
        },
        "post_t1_selection_permitted": False,
    }
    expected_values = (0.6584414158428827, 0.6785419992551178, 0.6888303122451366)
    if not all(
        math.isclose(item["value"], expected, rel_tol=0, abs_tol=1e-15)
        for item, expected in zip(descriptive.values(), expected_values, strict=False)
        if isinstance(item, dict)
    ):
        raise EvidenceAuditError("descriptive aggregate reconciliation changed")
    return project, {
        "status": "PASS_EXACT_RECONCILIATION",
        "reconciled_artifacts": sorted(reconciliations),
        "metrics": list(METRICS),
        "project_metric_rows": len(project),
        "aggregate_metric_rows": len(aggregate),
        "descriptive_checks": descriptive,
        "metrics_or_probabilities_changed": False,
    }


def _statistical_audit(root: Path) -> dict[str, Any]:
    rows = _csv_rows(root / RESULTS_REL / "T1-E_statistical_tests.csv")
    omnibus = _csv_rows(root / RESULTS_REL / "statistical_omnibus_results.csv")
    states = Counter(row["result_state"] for row in rows)
    if len(rows) != 384 or len(omnibus) != 32:
        raise EvidenceAuditError("statistical result matrix incomplete")
    if states != Counter(
        {
            "SIGNIFICANT_FAVORS_PROPOSAL": 137,
            "NON_SIGNIFICANT": 246,
            "SIGNIFICANT_FAVORS_COMPARATOR": 1,
        }
    ):
        raise EvidenceAuditError("statistical result-state counts changed")
    grouped: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if int(row["n_complete_projects"]) < 5 or int(row["n_nonzero_pairs"]) < 2:
            if row["result_state"] != "INSUFFICIENT_SUPPORT":
                raise EvidenceAuditError(
                    "insufficient support not classified explicitly"
                )
        grouped[row["family"], row["algorithm"], row["metric"]].append(row)
    for family in grouped.values():
        ordered = sorted(family, key=lambda row: float(row["raw_p_value"]))
        running = 0.0
        for rank, row in enumerate(ordered):
            running = max(
                running,
                min(1.0, (len(ordered) - rank) * float(row["raw_p_value"])),
            )
            if not math.isclose(
                running, float(row["holm_adjusted_p_value"]), rel_tol=0, abs_tol=1e-15
            ):
                raise EvidenceAuditError("Holm adjustment mismatch")
    primary = {
        metric: Counter(row["result_state"] for row in rows if row["metric"] == metric)
        for metric in ("PR_AUC", "MCC")
    }
    return {
        "status": "PASS",
        "friedman_omnibus_rows": len(omnibus),
        "paired_two_sided_wilcoxon_rows": len(rows),
        "holm_families": len(grouped),
        "paired_rank_biserial_rows": len(rows),
        "alpha": 0.05,
        "minimum_complete_projects": 5,
        "minimum_nonzero_pairs": 2,
        "insufficient_support_rows": states["INSUFFICIENT_SUPPORT"],
        "result_state_counts": dict(states),
        "primary_metric_state_counts": {
            metric: dict(counts) for metric, counts in primary.items()
        },
        "new_tests_introduced": False,
    }


def _calibration_audit(root: Path, provenance: dict[str, Any]) -> dict[str, Any]:
    rows = _csv_rows(root / RESULTS_REL / "T1-F_calibration_results.csv")
    isotonic = [row for row in rows if row["selected_calibration_state"] == "ISOTONIC"]
    values = {
        "mean_Brier_RAW": float(np.mean([float(row["raw_Brier"]) for row in isotonic])),
        "mean_Brier_ISOTONIC": float(
            np.mean([float(row["selected_Brier"]) for row in isotonic])
        ),
        "mean_ECE_RAW": float(np.mean([float(row["raw_ECE"]) for row in isotonic])),
        "mean_ECE_ISOTONIC": float(
            np.mean([float(row["selected_ECE"]) for row in isotonic])
        ),
    }
    expected = (
        0.18861868409707291,
        0.18224662976077852,
        0.15258750959102632,
        0.15118676971769288,
    )
    if provenance["project_scope_counts"] != {"RAW": 378, "ISOTONIC": 14} or not all(
        math.isclose(value, target, rel_tol=0, abs_tol=1e-15)
        for value, target in zip(values.values(), expected, strict=True)
    ):
        raise EvidenceAuditError("calibration evidence reconciliation changed")
    return {
        "status": "PASS",
        **provenance,
        **values,
        "interpretation": "FROZEN_CONFIRMATORY_CALIBRATION_EVIDENCE_ONLY",
    }


def _near_perfect_audit(
    root: Path,
    evidence: list[dict[str, Any]],
    project_metrics: list[dict[str, Any]],
    integrity: dict[str, Any],
) -> dict[str, Any]:
    results = root / RESULTS_REL
    original = load_json(results / "near_perfect_result_audit.json")
    metric_index = {
        (row["project"], row["algorithm"], row["configuration"]): row
        for row in project_metrics
    }
    evidence_index: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in evidence:
        evidence_index[row["project"], row["algorithm"], row["configuration"]].append(
            row
        )
    audited = []
    taxonomy = Counter()
    for trigger in original["triggers"]:
        key = trigger["project"], trigger["algorithm"], trigger["configuration"]
        metric_row = metric_index[key]
        rows = evidence_index[key]
        metric = trigger["metric"]
        value = float(trigger["metric_value"])
        models = {row["model_identity_sha256"] for row in rows}
        calibration = {
            json.dumps(row["calibration_provenance"], sort_keys=True) for row in rows
        }
        if (
            not math.isclose(value, float(metric_row[metric]), rel_tol=0, abs_tol=0)
            or value < 0.99
            or len(models) != 1
            or len(calibration) != 1
        ):
            category = "INTEGRITY_CONCERN_REQUIRES_ESCALATION"
        elif metric in {"Recall", "Precision", "F1", "MCC"}:
            category = "EXPLAINABLE_BY_CLASS_SUPPORT_OR_THRESHOLD_BEHAVIOR"
        elif min(metric_row["positive"], metric_row["negative"]) < 5:
            category = "INSUFFICIENT_SUPPORT_FOR_INTERPRETATION"
        else:
            category = "EXTREME_BUT_INTEGRITY_SUPPORTED"
        taxonomy[category] += 1
        probabilities = [row["final_frozen_probability"] for row in rows]
        audited.append(
            {
                "project": key[0],
                "algorithm": key[1],
                "configuration": key[2],
                "metric": metric,
                "metric_value": value,
                "taxonomy": category,
                "value_preserved_unchanged": True,
                "class_support": trigger["class_support"],
                "prevalence": trigger["prevalence"],
                "confusion_matrix": trigger["confusion_matrix_where_relevant"],
                "probability_evidence_sha256": hashlib.sha256(
                    canonical_bytes(
                        [
                            [row["row_identifier"], probability]
                            for row, probability in zip(
                                rows, probabilities, strict=True
                            )
                        ]
                    )
                ).hexdigest(),
                "identity_integrity": "PASS_EXACT_T1_MEMBERSHIP",
                "duplicate_identity_scope_rows": integrity[
                    "duplicate_identity_scope_rows"
                ],
                "leakage_contract_violations": integrity["leakage_contract_violations"],
                "model_identity_sha256": next(iter(models)),
                "model_provenance": rows[0]["model_provenance"],
                "calibration_provenance": rows[0]["calibration_provenance"],
                "temporal_integrity": "PASS_NO_DEVELOPMENT_OR_T2_CONTAMINATION",
            }
        )
    if len(audited) != 62 or taxonomy["INTEGRITY_CONCERN_REQUIRES_ESCALATION"]:
        raise EvidenceAuditError("near-perfect trigger audit failed closed")
    return {
        "status": "PASS_ALL_TRIGGERS_AUDITED_VALUES_UNCHANGED",
        "trigger_count": len(audited),
        "taxonomy_counts": dict(taxonomy),
        "integrity_concern_count": 0,
        "t1_additional_access_count": 0,
        "predictive_scoring_added": 0,
        "records": audited,
    }


def _classification_audit(root: Path) -> dict[str, Any]:
    results = root / RESULTS_REL
    classification = load_json(results / "scientific_classification.json")
    correction = load_json(results / "post_execution_classification_correction.json")
    adverse = {
        key: value
        for key, value in classification["primary_direction_means"].items()
        if value < 0
    }
    if (
        classification["classification"] != "MIXED_CONFIRMATORY_EVIDENCE"
        or set(adverse)
        != {
            "BEST_PAIRWISE::Random Forest::MCC",
            "BEST_PAIRWISE::Random Forest::PR_AUC",
            "BEST_UNIMODAL::Random Forest::MCC",
        }
        or correction["evidence_changed"] is not False
        or any(
            correction[key] != 0
            for key in (
                "t1_predictive_access_count_added",
                "t2_predictive_access_count_added",
                "predictive_scoring_count_added",
                "xai_execution_count_added",
            )
        )
    ):
        raise EvidenceAuditError("scientific classification reconciliation failed")
    return {
        "status": "PASS",
        "classification": "MIXED_CONFIRMATORY_EVIDENCE",
        "adverse_random_forest_primary_directions": adverse,
        "initial_pass_corrected_at_interpretation_layer_only": True,
        "evidence_changed": False,
        "additional_t1_access": 0,
        "additional_predictive_scoring": 0,
        "unfavorable_results_removed": False,
    }


def _reviewer_reportability(root: Path, near: dict[str, Any]) -> dict[str, Any]:
    limitations = load_json(root / SPRINT53_REL / "scientific_limitations.json")[
        "limitations"
    ]
    return {
        "status": "SCIENTIFICALLY_REPORTABLE_WITH_MIXED_CLASSIFICATION_AND_LIMITATIONS",
        "what_t1_confirms": [
            "All frozen scopes retain measurable future-partition predictive evidence.",
            (
                "Full multimodality has favorable aggregate PR-AUC/MCC directions "
                "for most algorithms and frozen comparators."
            ),
            "The one-shot evidence is complete, traceable, and internally consistent.",
        ],
        "what_t1_does_not_confirm": [
            "Uniform superiority of full multimodality across algorithms or projects.",
            (
                "External-benchmark generalization, causal modality effects, or "
                "verified-clean ground truth."
            ),
            "T2 performance or any XAI claim.",
        ],
        "favorable_full_multimodality": (
            "Positive primary aggregate directions except the recorded Random Forest "
            "adverse directions."
        ),
        "mixed_or_adverse": (
            "Random Forest is adverse versus best pairwise for PR-AUC/MCC and "
            "marginally adverse versus best unimodal for MCC."
        ),
        "calibration": (
            "Frozen LightGBM+PROCESS isotonic calibration modestly improves mean "
            "Brier and ECE; no reselection occurred."
        ),
        "near_perfect": {
            "trigger_count": near["trigger_count"],
            "taxonomy_counts": near["taxonomy_counts"],
            "values_changed": False,
        },
        "limitations": limitations,
        "post_t1_optimization": "PROHIBITED_TO_PRESERVE_CONFIRMATORY_VALIDITY",
        "t2": "SEALED_REVIEWER_RESERVE_NO_EVIDENCE_IN_SPRINT54",
        "xai": "DEFERRED_TO_SEPARATELY_GOVERNED_ANALYSIS_OVER_FROZEN_EVIDENCE",
    }


def materialize_audit(root: Path) -> Path:
    results = root / RESULTS_REL
    verified = verify_manifest(results)
    if verified["manifest_sha256"] != EXPECTED_RESULTS_MANIFEST_SHA256:
        raise EvidenceAuditError("sealed Sprint 54 result manifest changed")
    verify_manifest(root / ENGINE_REL)
    evidence = _load_evidence(results / "t1_prediction_evidence.jsonl.gz")
    started, completed, integrity = _verify_execution_integrity(root, evidence)
    _, provenance = _verify_provenance(root, evidence)
    project_metrics, reconciliation = _reconcile_results(root, evidence)
    statistical = _statistical_audit(root)
    calibration = _calibration_audit(root, provenance)
    near = _near_perfect_audit(root, evidence, project_metrics, integrity)
    classification = _classification_audit(root)
    fusion = {
        "status": "PASS",
        "architecture": "DECISION_LEVEL_STACKING_LATE_FUSION",
        "independently_learned_base_modalities": True,
        "raw_feature_concatenation": False,
        "simple_averaging": False,
        "voting": False,
        "post_t1_meta_learner_fitting": False,
        "semantically_distinct_modalities": ["CODE", "PROCESS", "TEXT"],
    }
    reviewer = _reviewer_reportability(root, near)
    overall = {
        "schema_version": VERSION,
        "audit_classification": (
            "PASS_CONFIRMATORY_EVIDENCE_INTERNALLY_CONSISTENT_REPORTABLE_MIXED"
        ),
        "execution_integrity_status": "PASS",
        "result_reconciliation_status": reconciliation["status"],
        "scientific_classification": classification["classification"],
        "execution_identifier": completed["execution_identifier"],
        "t1_rows": EXPECTED_T1_ROWS,
        "t1_identity_sha256": EXPECTED_T1_HASH,
        "t1_evidence_rows": EXPECTED_EVIDENCE_ROWS,
        "t1_predictive_access_count": 1,
        "predictive_scoring_count": 1,
        "t2_predictive_access_count": 0,
        "xai_execution_count": 0,
        "t1_rerun_permitted": False,
        "t2_access_state": "DENY_SEALED_REVIEWER_RESERVE",
        "irreversible_marker_sha256": file_sha256(results / "execution_started.json"),
        "sealed_results_manifest_sha256": EXPECTED_RESULTS_MANIFEST_SHA256,
        "new_integrity_concerns": [],
        "evidence_or_metrics_changed": False,
        "audit_inputs": {
            "execution_started_state": started["state"],
            "execution_completed_state": completed["state"],
            "post_execution_integrity_state": integrity["status"],
        },
    }
    output = root / AUDIT_REL
    if output.exists():
        raise EvidenceAuditError("Block 6 audit package already exists")
    output.mkdir(parents=True)
    artifacts = {
        "confirmatory_evidence_audit.json": {
            **overall,
            "reconciliation": reconciliation,
            "classification_audit": classification,
        },
        "near_perfect_result_audit.json": near,
        "statistical_evidence_audit.json": statistical,
        "calibration_evidence_audit.json": calibration,
        "multimodal_fusion_audit.json": fusion,
        "reviewer_reportability_audit.json": reviewer,
    }
    for name, payload in artifacts.items():
        _atomic_json(output / name, payload)
    report = "\n".join(
        [
            "# Sprint 54 Block 6 Confirmatory Evidence Audit",
            "",
            f"- Audit classification: `{overall['audit_classification']}`",
            "- Execution integrity: `PASS`",
            f"- Reconciliation: `{reconciliation['status']}`",
            f"- Scientific classification: `{classification['classification']}`",
            "- T1 access/scoring: `1 / 1`; T2 access: `0`; XAI: `0`",
            (
                f"- Evidence: `{EXPECTED_EVIDENCE_ROWS:,}` rows over "
                f"`{EXPECTED_T1_ROWS:,}` T1 identities and 28 scopes"
            ),
            (
                f"- Statistical audit: `{statistical['status']}`; 32 Friedman "
                "rows and 384 Holm-governed paired Wilcoxon rows"
            ),
            (
                f"- Calibration audit: `{calibration['status']}`; 378 RAW and "
                "14 frozen ISOTONIC project-scopes"
            ),
            (
                f"- Near-perfect audit: `{near['trigger_count']}` triggers, all "
                "values unchanged, no integrity escalation"
            ),
            "- T1 rerun: prohibited; T2: sealed; XAI: deferred",
            "",
            (
                "The sealed T1 evidence is internally consistent and scientifically "
                "reportable as mixed confirmatory evidence. Full multimodality is "
                "favorable on most aggregate primary comparisons, while adverse "
                "Random Forest directions are explicitly preserved. No post-T1 "
                "optimization, reselection, rescoring, T2 access, or XAI execution "
                "occurred during this audit."
            ),
            "",
        ]
    )
    (output / "BLOCK6_REPORT.md").write_text(report, encoding="utf-8")
    manifest = "".join(
        f"{file_sha256(path)}  {path.name}\n"
        for path in sorted(output.iterdir(), key=lambda item: item.name)
        if path.name != "MANIFEST.sha256"
    )
    (output / "MANIFEST.sha256").write_text(manifest, encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    print(materialize_audit(args.root.resolve()))


if __name__ == "__main__":
    main()
