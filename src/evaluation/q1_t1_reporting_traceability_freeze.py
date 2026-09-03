"""Freeze reviewer-ready reporting from sealed Sprint 54 audit evidence only."""

from __future__ import annotations

import argparse
import os
from collections import Counter
from pathlib import Path
from typing import Any

from evaluation.q1_t1_confirmatory_execution import (
    AUTH_REL,
    canonical_bytes,
    file_sha256,
    load_json,
    verify_manifest,
)

VERSION = "q1-t1-reporting-reviewer-traceability-freeze-1.0.0"
RESULTS_REL = AUTH_REL / "results"
BLOCK6_REL = AUTH_REL / "block6_evidence_audit" / "1.0.0"
BLOCK7_REL = AUTH_REL / "block7_reporting_traceability" / "1.0.0"
EXPECTED_RESULTS_MANIFEST_SHA256 = (
    "f396cfa0db8d01c8c1392fe7bb8affe8413638e3c0e20a3c113d7fe94a6d3a7e"
)
EXPECTED_BLOCK6_MANIFEST_SHA256 = (
    "bc279a8b7f74992db2010d3273476e7e337f9a916d2f49e12cab194fda5c18f7"
)
EXPECTED_EVIDENCE_SHA256 = (
    "eb4b6956b185e63cd322d92b8cdf96f53fcb09ef83b6a16f2334d660c6f5adc8"
)
MIXED = "MIXED_CONFIRMATORY_EVIDENCE"
BLOCK6_CLASSIFICATION = (
    "PASS_CONFIRMATORY_EVIDENCE_INTERNALLY_CONSISTENT_REPORTABLE_MIXED"
)


class ReportingFreezeError(RuntimeError):
    """A fail-closed mismatch in sealed reporting inputs or invariants."""


def _atomic_json(path: Path, value: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(canonical_bytes(value))
    os.replace(temporary, path)


def _verify_inputs(root: Path) -> dict[str, Any]:
    results = verify_manifest(root / RESULTS_REL)
    block6 = verify_manifest(root / BLOCK6_REL)
    if results["manifest_sha256"] != EXPECTED_RESULTS_MANIFEST_SHA256:
        raise ReportingFreezeError("sealed Sprint 54 results manifest changed")
    if block6["manifest_sha256"] != EXPECTED_BLOCK6_MANIFEST_SHA256:
        raise ReportingFreezeError("sealed Block 6 audit manifest changed")
    completed = load_json(root / RESULTS_REL / "execution_completed.json")
    scientific = load_json(root / RESULTS_REL / "scientific_classification.json")
    audit = load_json(root / BLOCK6_REL / "confirmatory_evidence_audit.json")
    near = load_json(root / BLOCK6_REL / "near_perfect_result_audit.json")
    statistical = load_json(root / BLOCK6_REL / "statistical_evidence_audit.json")
    calibration = load_json(root / BLOCK6_REL / "calibration_evidence_audit.json")
    fusion = load_json(root / BLOCK6_REL / "multimodal_fusion_audit.json")
    required = (
        scientific["classification"] == MIXED,
        audit["audit_classification"] == BLOCK6_CLASSIFICATION,
        audit["execution_integrity_status"] == "PASS",
        audit["result_reconciliation_status"] == "PASS_EXACT_RECONCILIATION",
        audit["t1_predictive_access_count"] == 1,
        audit["predictive_scoring_count"] == 1,
        audit["t2_predictive_access_count"] == 0,
        audit["xai_execution_count"] == 0,
        audit["t1_rerun_permitted"] is False,
        audit["t1_rows"] == 3787,
        audit["t1_evidence_rows"] == 106036,
        audit["new_integrity_concerns"] == [],
        audit["evidence_or_metrics_changed"] is False,
        completed["evidence_sha256"] == EXPECTED_EVIDENCE_SHA256,
        completed["scope_count"] == 28,
        completed["project_scope_count"] == 392,
        near["trigger_count"] == 62,
        near["integrity_concern_count"] == 0,
        near["taxonomy_counts"]
        == {
            "EXPLAINABLE_BY_CLASS_SUPPORT_OR_THRESHOLD_BEHAVIOR": 32,
            "EXTREME_BUT_INTEGRITY_SUPPORTED": 30,
        },
        statistical["status"] == "PASS",
        calibration["status"] == "PASS",
        fusion["status"] == "PASS",
    )
    adverse = audit["classification_audit"]["adverse_random_forest_primary_directions"]
    if not all(required) or set(adverse) != {
        "BEST_PAIRWISE::Random Forest::MCC",
        "BEST_PAIRWISE::Random Forest::PR_AUC",
        "BEST_UNIMODAL::Random Forest::MCC",
    }:
        raise ReportingFreezeError("frozen Block 7 reporting invariant failed")
    return {
        "completed": completed,
        "scientific": scientific,
        "audit": audit,
        "near": near,
        "statistical": statistical,
        "calibration": calibration,
        "fusion": fusion,
        "adverse": adverse,
    }


def _reporting_contract(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": VERSION,
        "classification": MIXED,
        "block6_classification": BLOCK6_CLASSIFICATION,
        "confirmed_by_t1": [
            "Frozen models retain measurable predictive evidence on prospective T1.",
            (
                "The complete execution is internally consistent, traceable, and free "
                "of detected development/T2 contamination under frozen contracts."
            ),
            (
                "Full multimodality has favorable aggregate PR-AUC/MCC directions for "
                "most algorithms and frozen comparator families."
            ),
            (
                "Frozen statistical and calibration analyses are reproducible from "
                "sealed evidence."
            ),
        ],
        "mixed_algorithm_dependent": [
            "Full multimodality is not uniformly superior across algorithms/projects.",
            "Random Forest adverse primary directions remain visible and reportable.",
            "The scientific classification remains MIXED_CONFIRMATORY_EVIDENCE.",
        ],
        "not_confirmed_by_t1": [
            "Universal superiority of CODE+PROCESS+TEXT.",
            "Superiority for every algorithm or project.",
            "Causal contribution of any modality.",
            "Independently verified-clean ground truth.",
            "Generalization beyond the evaluated Apache benchmark family.",
            "T2 performance.",
            "XAI conclusions.",
        ],
        "deferred_not_evaluated": [
            "T2 remains a sealed reviewer reserve.",
            "XAI remains prospectively deferred and separately governed.",
            "Post-T1 optimization and model/configuration reselection are prohibited.",
        ],
        "limitations": [
            (
                "Benchmark-defined labels are not independently verified-clean "
                "ground truth."
            ),
            "Evaluation is within one 14-project Apache benchmark family.",
            "Project-level paired inference has limited power.",
            "PR-AUC-selected comparators need not optimize MCC.",
            "ECE can be sensitive to frozen binning and sample support.",
            "Ablation contrasts are predictive associations, not causal effects.",
            "T2 has not been accessed.",
            "XAI has not been executed.",
            (
                "Near-perfect integrity support does not causally explain why values "
                "became extreme."
            ),
        ],
        "descriptive_results_only_no_post_t1_selection": [
            {
                "algorithm": "XGBoost",
                "configuration": "CODE",
                "metric": "PR_AUC",
                "value": 0.6584414158428827,
            },
            {
                "algorithm": "XGBoost",
                "configuration": "CODE+PROCESS",
                "metric": "PR_AUC",
                "value": 0.6785419992551178,
            },
            {
                "algorithm": "XGBoost",
                "configuration": "CODE+PROCESS+TEXT",
                "metric": "PR_AUC",
                "value": 0.6888303122451366,
            },
        ],
        "statistical_reporting": {
            "friedman_omnibus_rows": 32,
            "paired_two_sided_wilcoxon_rows": 384,
            "holm_families": 64,
            "alpha": 0.05,
            "result_state_counts": {
                "SIGNIFICANT_FAVORS_PROPOSAL": 137,
                "NON_SIGNIFICANT": 246,
                "SIGNIFICANT_FAVORS_COMPARATOR": 1,
                "INSUFFICIENT_SUPPORT": 0,
            },
            "new_tests_or_selection": False,
            "non_significance_is_equivalence": False,
            "statistical_significance_is_practical_significance": False,
        },
        "calibration_reporting": {
            "RAW_project_scopes": 378,
            "ISOTONIC_project_scopes": 14,
            "ISOTONIC_scope": "LightGBM + PROCESS",
            "mean_Brier_RAW": 0.18861868409707291,
            "mean_Brier_ISOTONIC": 0.18224662976077852,
            "mean_ECE_RAW": 0.15258750959102632,
            "mean_ECE_ISOTONIC": 0.15118676971769288,
            "interpretation": "MODEST_FROZEN_CALIBRATION_IMPROVEMENTS",
            "broad_calibration_superiority_claim": False,
            "t1_calibration_fit_or_selection": False,
        },
        "near_perfect_reporting": {
            "trigger_count": 62,
            "taxonomy_counts": {
                "EXPLAINABLE_BY_CLASS_SUPPORT_OR_THRESHOLD_BEHAVIOR": 32,
                "EXTREME_BUT_INTEGRITY_SUPPORTED": 30,
                "INSUFFICIENT_SUPPORT_FOR_INTERPRETATION": 0,
                "INTEGRITY_CONCERN_REQUIRES_ESCALATION": 0,
            },
            "values_changed": False,
            "taxonomy_semantics": (
                "INTEGRITY_AUDIT_CATEGORIES_NOT_CAUSAL_EXPLANATIONS_OF_EXTREMENESS"
            ),
        },
        "adverse_random_forest_primary_directions": data["adverse"],
    }


def _concern(
    concern: str,
    artifact: str,
    status: str,
    interpretation: str,
    limitation: str,
    safe_claim: str,
    overclaim: str,
) -> dict[str, str]:
    return {
        "reviewer_concern": concern,
        "governing_contract_or_artifact": artifact,
        "evidence_status": status,
        "scientific_interpretation": interpretation,
        "remaining_limitation": limitation,
        "manuscript_safe_claim": safe_claim,
        "prohibited_overclaim": overclaim,
    }


def _reviewer_matrix() -> list[dict[str, str]]:
    result_root = str(RESULTS_REL)
    audit_root = str(BLOCK6_REL)
    return [
        _concern(
            "leakage / target proxy risk",
            f"{audit_root}/confirmatory_evidence_audit.json",
            "VERIFIED_UNDER_FROZEN_CONTRACTS",
            "No detected development/T2 contamination or leakage-contract violation.",
            "Audit cannot establish absence of every conceivable construct proxy.",
            "No leakage was detected under the frozen identity and feature contracts.",
            "The benchmark is proven free of all possible target proxies.",
        ),
        _concern(
            "implausibly high or perfect metrics",
            f"{audit_root}/near_perfect_result_audit.json",
            "PARTIALLY_ADDRESSED_INTEGRITY_SUPPORTED",
            (
                "All 62 triggers retain intact identity, probability, and provenance "
                "traces."
            ),
            "Integrity categories do not causally explain extreme values.",
            "Near-perfect values were preserved and passed the specified audit checks.",
            "Near-perfect values prove exceptional universal predictive performance.",
        ),
        _concern(
            "temporal evaluation",
            f"{result_root}/post_execution_integrity.json",
            "VERIFIED_UNDER_FROZEN_PARTITIONS",
            "One prospective T1 execution used the frozen temporal membership.",
            "Only one held-out horizon and one benchmark family were evaluated.",
            "Results describe the frozen prospective T1 partition.",
            "Temporal generalization is universal or permanent.",
        ),
        _concern(
            "unimodal baselines",
            f"{result_root}/T1-A_per_project_algorithm_configuration_metrics.csv",
            "VERIFIED_COMPLETE",
            "CODE, PROCESS, and TEXT unimodal results are all retained.",
            "Relative performance varies by project and algorithm.",
            "All frozen unimodal baselines were evaluated on T1.",
            "Every multimodal configuration outperforms every unimodal baseline.",
        ),
        _concern(
            "pairwise modality combinations",
            f"{result_root}/T1-D_full_vs_frozen_best_pairwise.csv",
            "VERIFIED_COMPLETE_MIXED",
            "All three pairwise combinations and frozen comparisons are retained.",
            "Random Forest primary directions include adverse evidence.",
            "Pairwise comparisons are complete and algorithm-dependent.",
            "Full multimodality uniformly beats pairwise models.",
        ),
        _concern(
            "full multimodal fusion",
            f"{result_root}/T1-C_full_vs_frozen_best_unimodal.csv",
            "MIXED",
            "Most aggregate primary directions are favorable, but not all.",
            "No uniform algorithm/project superiority is supported.",
            "Full multimodality shows mostly favorable aggregate directions.",
            "CODE+PROCESS+TEXT is universally superior.",
        ),
        _concern(
            "fusion architecture",
            f"{audit_root}/multimodal_fusion_audit.json",
            "VERIFIED_UNDER_FROZEN_CONTRACT",
            "Decision-level stacking used independently learned base modalities.",
            "This does not prove stacking is optimal among untested architectures.",
            "The evaluated multimodal models use frozen decision-level stacking.",
            "Stacking is the universally optimal fusion method.",
        ),
        _concern(
            "calibration",
            f"{audit_root}/calibration_evidence_audit.json",
            "SUPPORTED_WITH_LIMITATION",
            "Frozen LightGBM+PROCESS isotonic calibration modestly improved means.",
            "ECE depends on frozen binning/support; broad superiority is unsupported.",
            "The frozen isotonic scope modestly improved mean Brier and ECE.",
            "Isotonic calibration is superior for all models and configurations.",
        ),
        _concern(
            "statistical comparison",
            f"{audit_root}/statistical_evidence_audit.json",
            "VERIFIED_MIXED",
            "Frozen Friedman/Wilcoxon/Holm/rank-biserial outputs reconcile exactly.",
            "Significance does not establish practical importance or equivalence.",
            (
                "Predeclared statistical analyses produced favorable, null, and "
                "adverse evidence."
            ),
            "Significance proves practically important universal superiority.",
        ),
        _concern(
            "reproducibility / provenance",
            f"{audit_root}/MANIFEST.sha256",
            "VERIFIED",
            "Sealed hashes, prediction provenance, and audit manifests verify.",
            "Reproducibility remains bounded by the frozen environment/contracts.",
            "The Sprint 54 evidence package is cryptographically traceable.",
            "Cryptographic traceability alone proves external scientific validity.",
        ),
        _concern(
            "benchmark label semantics",
            "audits/q1-t1-confirmatory-protocol/1.0.0/scientific_limitations.json",
            "LIMITATION_PRESERVED",
            "Labels are benchmark-defined observed labels.",
            "They are not independently verified-clean ground truth.",
            "Evaluation uses ApacheJIT benchmark-defined labels.",
            "Apache benchmark labels are verified-clean ground truth.",
        ),
        _concern(
            "external generalization",
            f"{audit_root}/reviewer_reportability_audit.json",
            "NOT_EVALUATED",
            "Evidence covers 14 projects in one Apache benchmark family.",
            "Generalization beyond that family remains untested.",
            "Findings apply to the evaluated Apache benchmark family.",
            "The results generalize to all software projects.",
        ),
        _concern(
            "T2 reserve",
            f"{result_root}/execution_completed.json",
            "DEFERRED_SEALED",
            "T2 access remains zero and the reserve remains sealed.",
            "T2 provides no evidence in Sprint 54.",
            "T2 remains an untouched reviewer reserve.",
            "T2 confirms the findings.",
        ),
        _concern(
            "XAI status",
            f"{result_root}/execution_completed.json",
            "DEFERRED_NOT_EXECUTED",
            "XAI execution remains zero and requires separate governance.",
            "No explanatory conclusion is supported in Sprint 54.",
            "Frozen prediction evidence is preserved for later governed XAI.",
            "XAI explains the T1 predictions.",
        ),
    ]


def _claim(
    claim_id: str, claim: str, status: str, evidence: list[str], guard: str
) -> dict[str, Any]:
    return {
        "claim_id": claim_id,
        "candidate_claim": claim,
        "evidence_status": status,
        "evidence_references": evidence,
        "reporting_guard": guard,
    }


def _claims() -> list[dict[str, Any]]:
    results = str(RESULTS_REL)
    audit = str(BLOCK6_REL)
    return [
        _claim(
            "C01",
            "Frozen models retain measurable predictive evidence on T1.",
            "SUPPORTED",
            [f"{results}/T1-A_per_project_algorithm_configuration_metrics.csv"],
            "Report all configurations and algorithms.",
        ),
        _claim(
            "C02",
            "The completed evidence is internally consistent and traceable.",
            "SUPPORTED",
            [f"{audit}/confirmatory_evidence_audit.json"],
            "Limit the claim to frozen checks and artifacts.",
        ),
        _claim(
            "C03",
            "Full multimodality has mostly favorable aggregate primary directions.",
            "SUPPORTED_WITH_LIMITATION",
            [
                f"{results}/T1-C_full_vs_frozen_best_unimodal.csv",
                f"{results}/T1-D_full_vs_frozen_best_pairwise.csv",
            ],
            "Preserve adverse Random Forest directions.",
        ),
        _claim(
            "C04",
            "Primary directions are algorithm-dependent.",
            "MIXED",
            [f"{audit}/confirmatory_evidence_audit.json"],
            "Retain MIXED_CONFIRMATORY_EVIDENCE classification.",
        ),
        _claim(
            "C05",
            "Frozen LightGBM+PROCESS isotonic calibration modestly improves means.",
            "SUPPORTED_WITH_LIMITATION",
            [f"{audit}/calibration_evidence_audit.json"],
            "Do not claim broad calibration superiority.",
        ),
        _claim(
            "C06",
            "MMSDP-XAI universally outperforms unimodal models.",
            "NOT_SUPPORTED",
            [f"{audit}/confirmatory_evidence_audit.json"],
            "Prohibited universal-overperformance claim.",
        ),
        _claim(
            "C07",
            "Multimodality is superior for all algorithms.",
            "NOT_SUPPORTED",
            [f"{audit}/confirmatory_evidence_audit.json"],
            "Contradicted by adverse Random Forest directions.",
        ),
        _claim(
            "C08",
            "Near-perfect results prove exceptional predictive performance.",
            "NOT_SUPPORTED",
            [f"{audit}/near_perfect_result_audit.json"],
            "Audit categories are not causal or universal-performance explanations.",
        ),
        _claim(
            "C09",
            "Apache benchmark labels are verified-clean ground truth.",
            "NOT_SUPPORTED",
            [f"{audit}/reviewer_reportability_audit.json"],
            "Use benchmark-defined observed-label wording.",
        ),
        _claim(
            "C10",
            "The results generalize to all software projects.",
            "NOT_SUPPORTED",
            [f"{audit}/reviewer_reportability_audit.json"],
            "Limit inference to the evaluated benchmark family.",
        ),
        _claim(
            "C11",
            "T2 confirms the findings.",
            "DEFERRED",
            [f"{results}/execution_completed.json"],
            "T2 remains sealed and contributes no evidence.",
        ),
        _claim(
            "C12",
            "XAI explains the T1 predictions.",
            "DEFERRED",
            [f"{results}/execution_completed.json"],
            "XAI execution is zero and separately governed.",
        ),
    ]


def _limitations() -> list[dict[str, str]]:
    values = [
        ("L01", "Benchmark-defined labels are not independently verified-clean."),
        ("L02", "Evaluation covers one 14-project Apache benchmark family."),
        ("L03", "Project-level inference has limited power where applicable."),
        ("L04", "PR-AUC-selected comparators need not optimize MCC."),
        ("L05", "ECE may be sensitive to frozen binning and sample support."),
        ("L06", "Ablation contrasts are predictive/associational, not causal."),
        ("L07", "T2 has not been accessed and provides no Sprint 54 evidence."),
        ("L08", "XAI has not been executed."),
        ("L09", "Near-perfect integrity support is not a causal explanation."),
    ]
    return [
        {
            "limitation_id": identifier,
            "limitation": limitation,
            "status": "PRESERVED",
            "mitigation_or_boundary": "REPORT_EXPLICITLY_NO_POST_T1_OPTIMIZATION",
        }
        for identifier, limitation in values
    ]


def _summary() -> list[dict[str, str]]:
    return [
        {
            "topic": "predictive evidence",
            "RESULT": "All 28 frozen scopes produced complete T1 evidence.",
            "INTERPRETATION": "Frozen models retain measurable prospective evidence.",
            "LIMITATION": "This does not imply universal superiority.",
        },
        {
            "topic": "full multimodality",
            "RESULT": "Most aggregate primary directions are favorable.",
            "INTERPRETATION": "Evidence supports useful but algorithm-dependent gains.",
            "LIMITATION": "Random Forest includes adverse primary directions.",
        },
        {
            "topic": "statistics",
            "RESULT": "137 favorable, 246 null, and one adverse governed contrast.",
            "INTERPRETATION": "Evidence contains favorable, null, and adverse effects.",
            "LIMITATION": (
                "Non-significance is not equivalence; significance is not practical "
                "importance."
            ),
        },
        {
            "topic": "calibration",
            "RESULT": (
                "Frozen isotonic LightGBM+PROCESS modestly improved mean Brier/ECE."
            ),
            "INTERPRETATION": "The preselected calibration state transferred modestly.",
            "LIMITATION": "No broad calibration superiority is established.",
        },
        {
            "topic": "near-perfect metrics",
            "RESULT": (
                "All 62 triggers passed specified integrity checks without escalation."
            ),
            "INTERPRETATION": "Values are integrity-supported under the frozen audit.",
            "LIMITATION": "Taxonomies do not causally explain extreme values.",
        },
        {
            "topic": "external scope",
            "RESULT": "T1 covers 14 Apache projects; T2 and XAI remain untouched.",
            "INTERPRETATION": "Sprint 54 supports a bounded benchmark conclusion.",
            "LIMITATION": (
                "External generalization, T2 performance, and XAI are untested."
            ),
        },
    ]


def materialize_reporting_freeze(root: Path) -> Path:
    data = _verify_inputs(root)
    contract = _reporting_contract(data)
    concerns = _reviewer_matrix()
    claims = _claims()
    limitations = _limitations()
    summary = _summary()
    statuses = Counter(row["evidence_status"] for row in claims)
    prohibited = [
        "MMSDP-XAI universally outperforms unimodal models",
        "multimodality is superior for all algorithms",
        "near-perfect results prove exceptional predictive performance",
        "Apache benchmark labels are verified-clean ground truth",
        "the results generalize to all software projects",
        "T2 confirms the findings",
        "XAI explains the T1 predictions",
    ]
    output = root / BLOCK7_REL
    if output.exists():
        raise ReportingFreezeError("Block 7 reporting package already exists")
    output.mkdir(parents=True)
    artifacts = {
        "scientific_reporting_contract.json": contract,
        "reviewer_traceability_matrix.json": {
            "schema_version": VERSION,
            "concern_count": len(concerns),
            "concerns": concerns,
            "resolved_status_prohibited_for_partial_evidence": True,
        },
        "manuscript_claim_ledger.json": {
            "schema_version": VERSION,
            "allowed_statuses": [
                "SUPPORTED",
                "SUPPORTED_WITH_LIMITATION",
                "MIXED",
                "NOT_SUPPORTED",
                "DEFERRED",
            ],
            "status_counts": dict(statuses),
            "claims": claims,
            "prohibited_overclaims": prohibited,
            "future_evidence_required_to_change_prohibitions": True,
        },
        "limitations_ledger.json": {
            "schema_version": VERSION,
            "limitation_count": len(limitations),
            "limitations": limitations,
        },
        "reviewer_facing_summary.json": {
            "schema_version": VERSION,
            "classification": MIXED,
            "entries": summary,
            "promotional_language": False,
            "adverse_random_forest_hidden": False,
            "non_significance_interpreted_as_equivalence": False,
            "statistical_significance_interpreted_as_practical": False,
        },
        "sealed_reference_registry.json": {
            "schema_version": VERSION,
            "results_manifest_sha256": EXPECTED_RESULTS_MANIFEST_SHA256,
            "block6_manifest_sha256": EXPECTED_BLOCK6_MANIFEST_SHA256,
            "t1_evidence_sha256": EXPECTED_EVIDENCE_SHA256,
            "scientific_classification": MIXED,
            "block6_classification": BLOCK6_CLASSIFICATION,
            "t1_predictive_access_count": 1,
            "predictive_scoring_count": 1,
            "t2_predictive_access_count": 0,
            "xai_execution_count": 0,
            "t1_rerun_permitted": False,
            "sealed_inputs_modified": False,
        },
    }
    for name, artifact in artifacts.items():
        _atomic_json(output / name, artifact)
    report = "\n".join(
        [
            "# Sprint 54 Block 7 Reporting and Reviewer Traceability Freeze",
            "",
            f"- Block 7 classification: `PASS_REPORTING_TRACEABILITY_FROZEN_{MIXED}`",
            f"- Scientific classification: `{MIXED}`",
            f"- Block 6 classification: `{BLOCK6_CLASSIFICATION}`",
            f"- Reviewer concerns mapped: `{len(concerns)}`",
            f"- Manuscript claims: `{len(claims)}` ({dict(statuses)})",
            f"- Preserved limitations: `{len(limitations)}`",
            "- T1 access/scoring: `1 / 1`; T2 access: `0`; XAI execution: `0`",
            "- T1 rerun: prohibited; T2: sealed reviewer reserve",
            "",
            (
                "The package is a reporting and traceability freeze over immutable "
                "Sprint 54 evidence. It preserves favorable, null, adverse, and "
                "near-perfect results without new prediction, selection, calibration, "
                "statistical testing, T2 access, or XAI execution."
            ),
            "",
        ]
    )
    (output / "BLOCK7_REPORT.md").write_text(report, encoding="utf-8")
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
    print(materialize_reporting_freeze(args.root.resolve()))


if __name__ == "__main__":
    main()
