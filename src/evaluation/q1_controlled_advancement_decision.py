# ruff: noqa: E501
"""Sprint 43 controlled application of the frozen Sprint 39 decision mapper."""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
from pathlib import Path
from typing import Any

from evaluation.q1_advancement_governance_protocol import (
    AUTHORIZATIONS,
    CRITERIA,
    OUTCOMES,
    STATES,
    canonical_bytes,
    criterion_class,
    validate_contract,
)
from evaluation.q1_advancement_governance_protocol import (
    evaluate as frozen_evaluate,
)

PROTOCOL_ID = "q1-controlled-advancement-decision"
VERSION = "1.0.0"
SPRINT = "10.8.2.43"
STARTING_HEAD = "4fc4f888fa90ae9b3576640605a9c1081aec05fd"
OUTPUT_REL = "audits/q1-controlled-advancement-decision/1.0.0"
GOVERNANCE_PATH = (
    "audits/q1-advancement-governance-outcome-mapping/1.0.0/governance_contract.json"
)
OPERATIONALIZATION_PATH = "audits/q1-prospective-criterion-operationalization/1.0.0/criterion_operationalization.json"
EVIDENCE_PATH = "audits/q1-controlled-criterion-state-evaluation/1.0.0/criterion_state_evaluation.json"
PROHIBITED_COUNTERS = (
    "TEST_label_accesses",
    "TEST_prediction_accesses",
    "TEST_probability_loading",
    "TEST_scoring",
    "TEST_derived_artifact_inspections",
    "TEST_model_selection",
    "TEST_threshold_optimization",
    "TEST_calibration_fitting",
    "TEST_XAI",
    "model_fits",
    "model_refits",
    "calibrator_fits",
    "calibrator_refits",
    "meta_learner_fits",
    "hyperparameter_searches",
    "threshold_optimizations",
    "feature_selections",
    "modality_selections",
    "candidate_selections",
    "architecture_modifications",
    "external_dataset_acquisitions",
    "XAI_executions",
    "SHAP_executions",
    "LIME_executions",
    "counterfactual_generations",
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(root: Path, relative: str) -> Any:
    return json.loads((root / relative).read_text(encoding="utf-8"))


def source_hashes(root: Path) -> dict[str, str]:
    return {
        GOVERNANCE_PATH: digest(root / GOVERNANCE_PATH),
        OPERATIONALIZATION_PATH: digest(root / OPERATIONALIZATION_PATH),
        EVIDENCE_PATH: digest(root / EVIDENCE_PATH),
    }


def accepted_historical_hashes(root: Path) -> dict[str, str]:
    """Create an immutable baseline from all tracked pre-Sprint-43 audit artifacts."""
    result = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", STARTING_HEAD, "--", "audits"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    paths = sorted(result.stdout.splitlines())
    return {
        path: hashlib.sha256(
            subprocess.run(
                ["git", "show", f"{STARTING_HEAD}:{path}"],
                cwd=root,
                check=True,
                capture_output=True,
            ).stdout
        ).hexdigest()
        for path in paths
    }


def verify_historical_integrity(root: Path, expected: dict[str, str]) -> dict[str, Any]:
    current_paths = sorted(
        str(path.relative_to(root))
        for path in (root / "audits").rglob("*")
        if path.is_file() and OUTPUT_REL not in str(path.relative_to(root))
    )
    observed = {path: digest(root / path) for path in current_paths}
    missing = sorted(set(expected) - set(observed))
    unexpected = sorted(set(observed) - set(expected))
    mismatches = sorted(
        path
        for path in set(expected) & set(observed)
        if expected[path] != observed[path]
    )
    tracked = subprocess.run(
        ["git", "diff", "--name-only", STARTING_HEAD, "--", "audits"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    historical_tracked = sorted(
        path for path in tracked if not path.startswith(OUTPUT_REL + "/")
    )
    return {
        "baseline_revision": STARTING_HEAD,
        "baseline_source": "immutable Git blobs at accepted pre-Sprint-43 HEAD",
        "protected_files_checked": len(expected),
        "missing_files": missing,
        "unexpected_files": unexpected,
        "hash_mismatches": mismatches,
        "historical_tracked_modifications": historical_tracked,
        "historical_modification_count": len(
            set(missing + unexpected + mismatches + historical_tracked)
        ),
        "passed": not (missing or unexpected or mismatches or historical_tracked),
    }


def _validate_inputs(
    governance: dict[str, Any], evidence: dict[str, Any]
) -> list[dict[str, Any]]:
    validate_contract(governance)
    if governance.get("test_access_prohibited") is not True:
        raise ValueError("TEST sealing missing from governance")
    if evidence.get("sprint") != "10.8.2.42" or evidence.get("test_sealed") is not True:
        raise ValueError("invalid or unsealed Sprint 42 evidence")
    if evidence.get("advancement_outcome_derived") is not False:
        raise ValueError("Sprint 42 evidence contains an unauthorized outcome")
    if evidence.get("canonical_state_vocabulary") != list(STATES):
        raise ValueError("Sprint 42 state vocabulary drift")
    rows = evidence.get("criteria")
    if not isinstance(rows, list) or [row.get("criterion") for row in rows] != list(
        CRITERIA
    ):
        raise ValueError("malformed Sprint 42 criterion vector")
    if len({row.get("criterion") for row in rows}) != len(CRITERIA):
        raise ValueError("duplicate Sprint 42 criterion")
    for row in rows:
        criterion = row["criterion"]
        if row.get("state") not in STATES or row.get(
            "criterion_class"
        ) != criterion_class(criterion):
            raise ValueError("Sprint 42 criterion state/class drift")
        if (
            not row.get("evidence_references")
            or not row.get("rule_reference")
            or not row.get("evidence_provenance")
        ):
            raise ValueError("incomplete Sprint 42 evidence provenance")
    return rows


def derive(
    root: Path, evidence_override: dict[str, Any] | None = None
) -> dict[str, Any]:
    governance = load_json(root, GOVERNANCE_PATH)
    evidence = (
        evidence_override
        if evidence_override is not None
        else load_json(root, EVIDENCE_PATH)
    )
    rows = _validate_inputs(governance, evidence)
    governance_sha = digest(root / GOVERNANCE_PATH)
    evidence_sha = digest(root / EVIDENCE_PATH)
    records = [
        {
            "criterion": row["criterion"],
            "criterion_class": row["criterion_class"],
            "state": row["state"],
            "evidence_reference": EVIDENCE_PATH,
            "provenance_reference": GOVERNANCE_PATH,
            "relevant_hashes": {
                "accepted_criterion_state_evidence_sha256": evidence_sha,
                "frozen_governance_contract_sha256": governance_sha,
                "originating_rule_sha256": row["rule_reference"]["sha256"],
            },
        }
        for row in rows
    ]
    frozen_trace = frozen_evaluate(governance, SPRINT, records)
    rules = governance["precedence_rules"]
    states = {row["criterion"]: row["state"] for row in rows}
    conditions = {
        "ANY_UNRESOLVED": any(value == "UNRESOLVED" for value in states.values()),
        "ANY_INTEGRITY_FAIL": any(
            states[c] == "FAIL"
            for c in CRITERIA
            if criterion_class(c) == "INTEGRITY_BLOCKING"
        ),
        "ANY_SCIENTIFIC_FAIL": any(
            states[c] == "FAIL"
            for c in CRITERIA
            if criterion_class(c) == "SCIENTIFIC_PERFORMANCE"
        ),
        "ANY_MIXED": any(value == "MIXED" for value in states.values()),
        "ALL_PASS": all(value == "PASS" for value in states.values()),
    }
    precedence = [
        {
            "precedence": index,
            **rule,
            "condition_satisfied": conditions[rule["condition"]],
            "selected": rule["id"] == frozen_trace["matched_precedence_rule"],
        }
        for index, rule in enumerate(rules, 1)
    ]
    criterion_provenance = [
        {
            "criterion": row["criterion"],
            "state": row["state"],
            "originating_evidence": row["evidence_references"],
            "criterion_rule": row["rule_reference"],
            "applicable_decision_rule": frozen_trace["matched_precedence_rule"],
            "precedence": next(
                item["precedence"] for item in precedence if item["selected"]
            ),
            "resulting_outcome": frozen_trace["advancement_outcome"],
        }
        for row in rows
    ]
    return {
        "protocol_id": PROTOCOL_ID,
        "version": VERSION,
        "sprint": SPRINT,
        "input_criterion_state_vector": [
            {"criterion": c, "state": states[c]} for c in CRITERIA
        ],
        "source_artifacts": source_hashes(root),
        "governance_protocol": governance["protocol_id"],
        "governance_protocol_version": governance["protocol_version"],
        "precedence_evaluation": precedence,
        "criterion_provenance": criterion_provenance,
        "matched_precedence_rule": frozen_trace["matched_precedence_rule"],
        "reason_code": frozen_trace["reason_code"],
        "advancement_outcome": frozen_trace["advancement_outcome"],
        "authorized_outcome_count": int(
            frozen_trace["advancement_outcome"] in OUTCOMES
        ),
        "test_sealed": True,
        **AUTHORIZATIONS,
    }


def execution_ledger() -> dict[str, Any]:
    return {
        "sprint_mode": "CONTROLLED_DECISION_ONLY",
        **dict.fromkeys(PROHIBITED_COUNTERS, 0),
    }


PERFORMANCE_SAFEGUARD = {
    "documentary_only": True,
    "modifies_frozen_decision_mapper": False,
    "introduces_sprint_43_advancement_criterion": False,
    "later_evaluation_dimensions": [
        "ROC-AUC",
        "PR-AUC",
        "Precision",
        "Recall",
        "F1",
        "MCC",
        "Brier Score",
        "ECE / reliability",
        "unimodal baselines",
        "bimodal combinations",
        "full multimodal model",
        "ablation evidence",
        "temporal robustness",
        "cross-origin stability where available",
        "uncertainty/statistical comparison",
    ],
    "principles": [
        "Multimodality does not excuse poor predictive performance.",
        "Explainability does not excuse poor predictive performance.",
        "Calibration does not replace discrimination.",
        "High discrimination does not excuse leakage or invalid evaluation.",
        "A multimodal model must be compared against strong simpler baselines.",
        "A scientifically valid experiment may still provide insufficient evidence for a publication claim.",
        "No publication claim may exceed the empirical evidence.",
    ],
    "required_statement": "Advancement-governance validity does not by itself establish predictive superiority or publication-level performance sufficiency.",
}


def decision_schema() -> dict[str, Any]:
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "required": [
            "protocol_id",
            "version",
            "sprint",
            "input_criterion_state_vector",
            "precedence_evaluation",
            "criterion_provenance",
            "advancement_outcome",
            "authorized_outcome_count",
            "test_sealed",
        ],
        "properties": {
            "advancement_outcome": {"enum": list(OUTCOMES)},
            "authorized_outcome_count": {"const": 1},
            "test_sealed": {"const": True},
        },
    }


def report(
    decision: dict[str, Any],
    history: dict[str, Any],
    quality: dict[str, Any] | None = None,
) -> str:
    rows = "\n".join(
        f"| `{row['criterion']}` | **{row['state']}** |"
        for row in decision["input_criterion_state_vector"]
    )
    gates = (
        "\n".join(
            f"- `{row['id']}`: exit `{row['exit_code']}`; `{row['observed_output'].splitlines()[-1]}`"
            for row in (quality or {}).get("observed_results", [])
        )
        or "- Runtime validation not yet recorded."
    )
    principles = "\n".join(
        f"{i}. {text}" for i, text in enumerate(PERFORMANCE_SAFEGUARD["principles"], 1)
    )
    dimensions = ", ".join(PERFORMANCE_SAFEGUARD["later_evaluation_dimensions"])
    return f"""# Sprint 10.8.2.43 — Controlled Prospective Advancement Decision

## Evidence-derived decision

**{decision["advancement_outcome"]}**, mechanically selected by `{decision["matched_precedence_rule"]}` (`{decision["reason_code"]}`) from the accepted Sprint 42 vector under the frozen Sprint 39 mapper. This is not a desired-outcome selection.

| Criterion | Accepted state |
|---|---|
{rows}

The full evidence paths, SHA-256 identities, per-criterion provenance, rule traversal, precedence, and resulting outcome are in `advancement_decision.json`.

## Experimental validity versus performance sufficiency

Experimental/governance validity and predictive/scientific performance sufficiency are distinct. Discrimination, calibration, practical utility, temporal and cross-origin stability, comparative unimodal/bimodal/multimodal performance, uncertainty, and later statistical evaluation remain scientifically material.

Advancement-governance validity does not by itself establish predictive superiority or publication-level performance sufficiency.

## Documentary publication-performance safeguard

This safeguard is documentary only. It neither modifies the frozen mapper nor introduces a Sprint 43 advancement criterion. Later work must evaluate, where applicable: {dimensions}.

{principles}

## TEST and prohibited operations

TEST remained sealed. No fitting/refitting, calibration fitting/refitting, tuning, feature/modality/candidate selection, architecture modification, external acquisition, XAI, SHAP, LIME, counterfactual generation, or new experimental evaluation occurred. All counters in `execution_ledger.json` are zero.

## Historical integrity

`{history["protected_files_checked"]}` pre-Sprint-43 audit artifacts checked; missing `{len(history["missing_files"])}`; unexpected `{len(history["unexpected_files"])}`; hash mismatches `{len(history["hash_mismatches"])}`; historical tracked modifications `{len(history["historical_tracked_modifications"])}`. Verdict: **{"PASS" if history["passed"] else "FAIL"}**.

## Quality gates

Status: `{(quality or {}).get("status", "NOT_RUN_BY_MATERIALIZER")}`.

{gates}
"""


def materialize(root: Path) -> Path:
    output = root / OUTPUT_REL
    output.mkdir(parents=True, exist_ok=True)
    decision = derive(root)
    history_hashes = accepted_historical_hashes(root)
    history = verify_historical_integrity(root, history_hashes)
    if not history["passed"]:
        raise RuntimeError("protected historical artifact drift")
    artifacts = {
        "advancement_decision.json": decision,
        "advancement_decision.schema.json": decision_schema(),
        "execution_ledger.json": execution_ledger(),
        "scientific_decision.json": {
            "decision": decision["advancement_outcome"],
            "matched_rule": decision["matched_precedence_rule"],
            "scope": "ADVANCEMENT_GOVERNANCE_ONLY",
            "human_acceptance_required": True,
            **AUTHORIZATIONS,
        },
        "publication_performance_safeguard.json": PERFORMANCE_SAFEGUARD,
        "historical_artifact_hashes.json": history_hashes,
        "historical_integrity.json": history,
        "quality_gates.json": {
            "status": "NOT_RUN_BY_MATERIALIZER",
            "observed_results": [],
        },
    }
    for name, value in artifacts.items():
        (output / name).write_bytes(canonical_bytes(value))
    module = root / "src/evaluation/q1_controlled_advancement_decision.py"
    tests = root / "tests/evaluation/test_q1_controlled_advancement_decision.py"
    manifest = {
        "protocol_id": PROTOCOL_ID,
        "version": VERSION,
        "sprint": SPRINT,
        "starting_head": STARTING_HEAD,
        "runtime": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "implementation_sha256": digest(module),
        "tests_sha256": digest(tests),
        "source_artifact_sha256": source_hashes(root),
        "artifact_sha256": {name: digest(output / name) for name in sorted(artifacts)},
    }
    (output / "experiment_manifest.json").write_bytes(canonical_bytes(manifest))
    (output / "REPORT.md").write_text(report(decision, history), encoding="utf-8")
    return output


def record_quality_gates(root: Path, observed: list[dict[str, Any]]) -> None:
    required = {
        "focused_pytest",
        "sprint_39_42_regression",
        "full_pytest",
        "ruff",
        "python_compilation",
        "json_schema",
        "determinism",
        "historical_integrity",
        "artifact_manifest",
        "project_quality_gates",
        "repository_format_diagnostic",
        "git_diff_check",
    }
    if {row.get("id") for row in observed} != required or len(observed) != len(
        required
    ):
        raise ValueError("incomplete quality gate observations")
    if any(not row.get("observed_output") for row in observed):
        raise ValueError("quality gate observation missing output")
    failures = [row for row in observed if row.get("exit_code") != 0]
    if any(row.get("id") != "repository_format_diagnostic" for row in failures):
        raise ValueError("unexpected quality gate failure")
    output = root / OUTPUT_REL
    quality = {
        "status": (
            "COMPLETED_WITH_REPOSITORY_FORMAT_FINDINGS"
            if failures
            else "PASS_FROM_EXECUTED_COMMANDS"
        ),
        "observed_results": observed,
    }
    (output / "quality_gates.json").write_bytes(canonical_bytes(quality))
    decision = load_json(root, f"{OUTPUT_REL}/advancement_decision.json")
    history = load_json(root, f"{OUTPUT_REL}/historical_integrity.json")
    (output / "REPORT.md").write_text(
        report(decision, history, quality), encoding="utf-8"
    )
    manifest = load_json(root, f"{OUTPUT_REL}/experiment_manifest.json")
    manifest["report_sha256"] = digest(output / "REPORT.md")
    manifest["artifact_sha256"]["quality_gates.json"] = digest(
        output / "quality_gates.json"
    )
    (output / "experiment_manifest.json").write_bytes(canonical_bytes(manifest))
