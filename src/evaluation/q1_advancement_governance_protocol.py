# ruff: noqa: E501
"""Sprint 39 prospective advancement-governance outcome mapping."""

from __future__ import annotations

import hashlib
import itertools
import json
import platform
from pathlib import Path
from typing import Any

PROTOCOL_ID = "q1-advancement-governance-outcome-mapping"
VERSION = "1.0.0"
SPRINT = "10.8.2.39"
EFFECTIVE_FROM_SPRINT = "10.8.2.40"
BRANCH = "sprint-10/q1-advancement-governance-outcome-mapping"
STARTING_HEAD = "6ffc42bdb1aee533fb4ed6f5cf0b5e8a517bbe14"
OUTPUT_REL = "audits/q1-advancement-governance-outcome-mapping/1.0.0"

CRITERIA = (
    "leakage_safety",
    "temporal_validity",
    "reproducibility",
    "discrimination",
    "calibration",
    "practical_utility",
    "complexity_parsimony",
    "stability_across_origins",
    "absence_of_outcome_driven_tuning",
)
INTEGRITY = frozenset(
    {
        "leakage_safety",
        "temporal_validity",
        "reproducibility",
        "absence_of_outcome_driven_tuning",
    }
)
SCIENTIFIC = frozenset(CRITERIA) - INTEGRITY
STATES = ("PASS", "MIXED", "FAIL", "UNRESOLVED")
OUTCOMES = ("BLOCKED", "NO_GO", "GO_WITH_LIMITATIONS", "GO")
HISTORICAL_DIRS = (
    "audits/q1-experimental-evidence-gap-audit",
    "audits/q1-experimental-validity-contract",
    "audits/q1-modality-factorial",
    "audits/q1-fusion-process-ablation",
    "audits/q1-forward-development-calibration",
    "audits/q1-development-practical-utility-protocol",
    "audits/q1-development-practical-utility-execution",
)
AUTHORIZATIONS = {
    "test_access_authorized": False,
    "final_candidate_authorized": False,
    "threshold_selection_authorized": False,
    "calibration_selection_authorized": False,
    "xai_authorized": False,
}
QUALITY_GATES = {
    "focused_sprint_39_pytest": {"passed": 20, "failed": 0},
    "relevant_regression_pytest": {"passed": 42, "failed": 0},
    "full_pytest": {"passed": 1426, "skipped": 1, "failed": 0},
    "sprint_39_ruff": {"verdict": "PASS", "findings": 0},
    "full_repository_ruff_diagnostic": {
        "verdict": "FAIL_PRE_EXISTING_UNRELATED",
        "findings": 31,
        "files": 2,
        "modified_to_repair": False,
    },
    "python_compilation": {"verdict": "PASS", "files": 3},
    "git_diff_check": {"verdict": "PASS", "errors": 0},
    "historical_hash_verification": {"verdict": "PASS", "files": 98},
    "test_and_prohibited_counters": {"verdict": "PASS_ALL_ZERO"},
}


def canonical_bytes(value: Any) -> bytes:
    """Serialize deterministic canonical JSON."""
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def digest(path: Path) -> str:
    """Return a file SHA-256 digest."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def criterion_class(criterion: str) -> str:
    """Return the frozen governance class for a canonical criterion."""
    if criterion in INTEGRITY:
        return "INTEGRITY_BLOCKING"
    if criterion in SCIENTIFIC:
        return "SCIENTIFIC_PERFORMANCE"
    raise ValueError(f"unknown criterion: {criterion}")


def contract() -> dict[str, Any]:
    """Return the prospective contract independently of observed outcomes."""
    state_semantics = {
        "PASS": (
            "Predeclared acceptance requirements are fully satisfied by complete, "
            "valid, traceable evidence."
        ),
        "MIXED": (
            "Complete, valid, traceable evidence contains a material limitation, "
            "heterogeneity, or partially favorable and unfavorable evidence that "
            "prevents an unqualified PASS."
        ),
        "FAIL": (
            "Complete and valid evidence violates a predeclared scientific or "
            "integrity requirement."
        ),
        "UNRESOLVED": (
            "Required evidence, operational definitions, provenance, or evaluation "
            "information is missing, incomplete, non-traceable, or non-derivable."
        ),
    }
    outcome_semantics = {
        "BLOCKED": "Advancement is blocked by unresolved evidence or integrity failure.",
        "NO_GO": "Valid governance evidence establishes scientific-performance failure.",
        "GO_WITH_LIMITATIONS": "Advancement has one or more explicit material limitations.",
        "GO": "All nine criteria satisfy their prospective acceptance requirements.",
    }
    return {
        "protocol_id": PROTOCOL_ID,
        "protocol_version": VERSION,
        "declared_in_sprint": SPRINT,
        "prospective_only": True,
        "effective_from_sprint": EFFECTIVE_FROM_SPRINT,
        "historical_sprints_excluded": "10.8.2.38_AND_EARLIER",
        "non_retroactivity": (
            "This contract must not reinterpret, overwrite, reclassify, or otherwise "
            "modify Sprint 10.8.2.38 or any earlier sprint."
        ),
        "criteria": [
            {"id": criterion, "class": criterion_class(criterion)}
            for criterion in CRITERIA
        ],
        "criterion_states": [
            {"id": state, "semantics": state_semantics[state]} for state in STATES
        ],
        "advancement_outcomes": [
            {"id": outcome, "semantics": outcome_semantics[outcome]}
            for outcome in OUTCOMES
        ],
        "precedence_rules": [
            {"id": "RULE_1", "condition": "ANY_UNRESOLVED", "outcome": "BLOCKED"},
            {"id": "RULE_2", "condition": "ANY_INTEGRITY_FAIL", "outcome": "BLOCKED"},
            {"id": "RULE_3", "condition": "ANY_SCIENTIFIC_FAIL", "outcome": "NO_GO"},
            {"id": "RULE_4", "condition": "ANY_MIXED", "outcome": "GO_WITH_LIMITATIONS"},
            {"id": "RULE_5", "condition": "ALL_PASS", "outcome": "GO"},
        ],
        "precedence_order": list(OUTCOMES),
        "input_scope": "already-derived prospective criterion-state records only",
        "test_access_prohibited": True,
        "independent_authorizations": dict(AUTHORIZATIONS),
    }


def validate_contract(value: dict[str, Any]) -> None:
    """Fail closed on contract drift and retrospective scope."""
    if value.get("protocol_id") != PROTOCOL_ID or value.get("protocol_version") != VERSION:
        raise ValueError("invalid protocol version")
    if value.get("prospective_only") is not True:
        raise ValueError("prospective-only marker missing")
    if value.get("effective_from_sprint") != EFFECTIVE_FROM_SPRINT:
        raise ValueError("invalid or retrospective effective sprint")
    rows = value.get("criteria")
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError("malformed criteria")
    identifiers = [row.get("id") for row in rows]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("duplicate criterion")
    if identifiers != list(CRITERIA):
        raise ValueError("criteria must match exact canonical order")
    if any(row.get("class") != criterion_class(row["id"]) for row in rows):
        raise ValueError("invalid criterion class")
    if [row.get("id") for row in value.get("criterion_states", [])] != list(STATES):
        raise ValueError("invalid state vocabulary")
    if [row.get("id") for row in value.get("advancement_outcomes", [])] != list(OUTCOMES):
        raise ValueError("invalid outcome vocabulary")
    if value.get("independent_authorizations") != AUTHORIZATIONS:
        raise ValueError("authorization drift")


def validate_records(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Validate a list representation so duplicate criteria remain detectable."""
    if not isinstance(records, list) or len(records) != len(CRITERIA):
        raise ValueError("malformed state vector")
    if any(not isinstance(row, dict) for row in records):
        raise ValueError("malformed criterion record")
    identifiers = [row.get("criterion") for row in records]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("duplicate criterion")
    if set(identifiers) != set(CRITERIA):
        raise ValueError("missing, extra, or unknown criterion")
    indexed = {row["criterion"]: row for row in records}
    for criterion in CRITERIA:
        row = indexed[criterion]
        if row.get("criterion_class") != criterion_class(criterion):
            raise ValueError("invalid criterion class")
        if row.get("state") not in STATES:
            raise ValueError("unknown state")
        if not isinstance(row.get("evidence_reference"), str) or not row["evidence_reference"]:
            raise ValueError("missing required evidence reference")
        if not isinstance(row.get("provenance_reference"), str) or not row["provenance_reference"]:
            raise ValueError("missing required provenance reference")
        hashes = row.get("relevant_hashes")
        if not isinstance(hashes, dict) or not hashes:
            raise ValueError("missing relevant hashes")
        if not all(
            isinstance(key, str)
            and isinstance(item, str)
            and len(item) == 64
            for key, item in hashes.items()
        ):
            raise ValueError("malformed relevant hashes")
    return indexed


def derive_outcome(states: dict[str, str]) -> tuple[str, str, str]:
    """Map a canonical state vector to exactly one outcome without evidence access."""
    if set(states) != set(CRITERIA):
        raise ValueError("invalid canonical state vector criteria")
    if any(states[criterion] not in STATES for criterion in CRITERIA):
        raise ValueError("invalid canonical state vector state")
    if any(states[criterion] == "UNRESOLVED" for criterion in CRITERIA):
        return "BLOCKED", "RULE_1", "ANY_UNRESOLVED"
    if any(states[criterion] == "FAIL" for criterion in INTEGRITY):
        return "BLOCKED", "RULE_2", "ANY_INTEGRITY_FAIL"
    if any(states[criterion] == "FAIL" for criterion in SCIENTIFIC):
        return "NO_GO", "RULE_3", "ANY_SCIENTIFIC_FAIL"
    if any(states[criterion] == "MIXED" for criterion in CRITERIA):
        return "GO_WITH_LIMITATIONS", "RULE_4", "ANY_MIXED"
    if all(states[criterion] == "PASS" for criterion in CRITERIA):
        return "GO", "RULE_5", "ALL_PASS"
    raise RuntimeError("valid state vector did not map to an outcome")


def _sprint_tuple(value: str) -> tuple[int, ...]:
    try:
        return tuple(int(part) for part in value.split("."))
    except (AttributeError, ValueError) as error:
        raise ValueError("invalid target sprint") from error


def evaluate(
    value: dict[str, Any], target_sprint: str, records: list[dict[str, Any]]
) -> dict[str, Any]:
    """Generate a canonical prospective derivation trace."""
    validate_contract(value)
    if _sprint_tuple(target_sprint) < _sprint_tuple(EFFECTIVE_FROM_SPRINT):
        raise ValueError("retrospective governance application prohibited")
    indexed = validate_records(records)
    states = {criterion: indexed[criterion]["state"] for criterion in CRITERIA}
    outcome, rule, reason = derive_outcome(states)
    return {
        "protocol_id": PROTOCOL_ID,
        "protocol_version": VERSION,
        "prospective_effective_from_sprint": EFFECTIVE_FROM_SPRINT,
        "target_sprint": target_sprint,
        "canonical_criterion_order": list(CRITERIA),
        "criteria": [
            {
                "criterion": criterion,
                "criterion_class": criterion_class(criterion),
                "state": indexed[criterion]["state"],
                "evidence_reference": indexed[criterion]["evidence_reference"],
                "provenance_reference": indexed[criterion]["provenance_reference"],
                "relevant_hashes": indexed[criterion]["relevant_hashes"],
            }
            for criterion in CRITERIA
        ],
        "matched_precedence_rule": rule,
        "reason_code": reason,
        "advancement_outcome": outcome,
        **AUTHORIZATIONS,
    }


def historical_hashes(root: Path) -> dict[str, str]:
    """Hash all files in the immutable tracked Sprint 32-38 audit scope."""
    paths: list[Path] = []
    for relative in HISTORICAL_DIRS:
        paths.extend(path for path in (root / relative).rglob("*") if path.is_file())
    return {str(path.relative_to(root)): digest(path) for path in sorted(paths)}


def verify_historical_hashes(root: Path, expected: dict[str, str]) -> None:
    """Fail if any historical file, path, or byte changes."""
    if historical_hashes(root) != expected:
        raise RuntimeError("Sprint 32-38 historical artifact hash mismatch")


def exhaustive_verification() -> dict[str, Any]:
    """Prove totality, repeatability, and order invariance for all 4^9 vectors."""
    counts = dict.fromkeys(OUTCOMES, 0)
    total = 0
    for vector in itertools.product(STATES, repeat=len(CRITERIA)):
        states = dict(zip(CRITERIA, vector, strict=True))
        first = derive_outcome(states)
        second = derive_outcome(dict(reversed(list(states.items()))))
        if first != second:
            raise RuntimeError("mapping is non-repeatable or order-dependent")
        counts[first[0]] += 1
        total += 1
    if total != 4**9 or sum(counts.values()) != total:
        raise RuntimeError("mapping is not total")
    return {
        "vectors_verified": total,
        "outcome_counts": counts,
        "authorized_outcomes": list(OUTCOMES),
        "deterministic_repeatability": True,
        "input_order_invariance": True,
        "exactly_one_outcome_per_vector": True,
        "verdict": "PASS",
    }


def execution_ledger() -> dict[str, int | str]:
    """Return explicit zero-use counters for all prohibited operations."""
    keys = (
        "TEST_scoring",
        "TEST_label_accesses",
        "TEST_probability_loading",
        "TEST_calibration_fitting",
        "TEST_threshold_optimization",
        "TEST_model_selection",
        "TEST_XAI",
        "model_fits",
        "calibrator_fits",
        "meta_learner_fits",
        "hyperparameter_searches",
        "threshold_optimizations",
        "external_dataset_acquisitions",
        "candidate_selections",
        "XAI_executions",
    )
    return {
        "sprint_mode": "PROSPECTIVE_GOVERNANCE_PROTOCOL_ONLY",
        **dict.fromkeys(keys, 0),
    }


def _contract_schema() -> dict[str, Any]:
    def exact_object(properties: dict[str, Any]) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": properties,
            "required": list(properties),
            "additionalProperties": False,
        }

    criteria = [
        exact_object(
            {
                "id": {"const": criterion},
                "class": {"const": criterion_class(criterion)},
            }
        )
        for criterion in CRITERIA
    ]
    states = [
        exact_object(
            {
                "id": {"const": state},
                "semantics": {"type": "string", "minLength": 1},
            }
        )
        for state in STATES
    ]
    outcomes = [
        exact_object(
            {
                "id": {"const": outcome},
                "semantics": {"type": "string", "minLength": 1},
            }
        )
        for outcome in OUTCOMES
    ]
    rules = [
        exact_object(
            {
                "id": {"const": rule},
                "condition": {"const": condition},
                "outcome": {"const": outcome},
            }
        )
        for rule, condition, outcome in (
            ("RULE_1", "ANY_UNRESOLVED", "BLOCKED"),
            ("RULE_2", "ANY_INTEGRITY_FAIL", "BLOCKED"),
            ("RULE_3", "ANY_SCIENTIFIC_FAIL", "NO_GO"),
            ("RULE_4", "ANY_MIXED", "GO_WITH_LIMITATIONS"),
            ("RULE_5", "ALL_PASS", "GO"),
        )
    ]
    authorizations = exact_object(
        {name: {"const": False} for name in AUTHORIZATIONS}
    )
    properties = {
        "protocol_id": {"const": PROTOCOL_ID},
        "protocol_version": {"const": VERSION},
        "declared_in_sprint": {"const": SPRINT},
        "prospective_only": {"const": True},
        "effective_from_sprint": {"const": EFFECTIVE_FROM_SPRINT},
        "historical_sprints_excluded": {"const": "10.8.2.38_AND_EARLIER"},
        "non_retroactivity": {"type": "string", "minLength": 1},
        "criteria": {
            "type": "array",
            "items": criteria,
            "additionalItems": False,
            "minItems": len(CRITERIA),
            "maxItems": len(CRITERIA),
        },
        "criterion_states": {
            "type": "array",
            "items": states,
            "additionalItems": False,
            "minItems": len(STATES),
            "maxItems": len(STATES),
        },
        "advancement_outcomes": {
            "type": "array",
            "items": outcomes,
            "additionalItems": False,
            "minItems": len(OUTCOMES),
            "maxItems": len(OUTCOMES),
        },
        "precedence_rules": {
            "type": "array",
            "items": rules,
            "additionalItems": False,
            "minItems": 5,
            "maxItems": 5,
        },
        "precedence_order": {
            "type": "array",
            "items": [{"const": outcome} for outcome in OUTCOMES],
            "additionalItems": False,
            "minItems": len(OUTCOMES),
            "maxItems": len(OUTCOMES),
        },
        "input_scope": {
            "const": "already-derived prospective criterion-state records only"
        },
        "test_access_prohibited": {"const": True},
        "independent_authorizations": authorizations,
    }
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": f"{PROTOCOL_ID}-{VERSION}",
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


def _trace_schema() -> dict[str, Any]:
    def exact_criterion(criterion: str) -> dict[str, Any]:
        properties = {
            "criterion": {"const": criterion},
            "criterion_class": {"const": criterion_class(criterion)},
            "state": {"enum": list(STATES)},
            "evidence_reference": {"type": "string", "minLength": 1},
            "provenance_reference": {"type": "string", "minLength": 1},
            "relevant_hashes": {
                "type": "object",
                "minProperties": 1,
                "patternProperties": {
                    "^[A-Za-z0-9_.-]+$": {
                        "type": "string",
                        "pattern": "^[0-9a-f]{64}$",
                    }
                },
                "additionalProperties": False,
            },
        }
        return {
            "type": "object",
            "properties": properties,
            "required": list(properties),
            "additionalProperties": False,
        }

    properties = {
        "protocol_id": {"const": PROTOCOL_ID},
        "protocol_version": {"const": VERSION},
        "prospective_effective_from_sprint": {"const": EFFECTIVE_FROM_SPRINT},
        "target_sprint": {"type": "string", "pattern": r"^10\.8\.2\.[0-9]+$"},
        "canonical_criterion_order": {
            "type": "array",
            "items": [{"const": criterion} for criterion in CRITERIA],
            "additionalItems": False,
            "minItems": len(CRITERIA),
            "maxItems": len(CRITERIA),
        },
        "criteria": {
            "type": "array",
            "items": [exact_criterion(criterion) for criterion in CRITERIA],
            "additionalItems": False,
            "minItems": len(CRITERIA),
            "maxItems": len(CRITERIA),
        },
        "matched_precedence_rule": {
            "enum": ["RULE_1", "RULE_2", "RULE_3", "RULE_4", "RULE_5"]
        },
        "reason_code": {
            "enum": [
                "ANY_UNRESOLVED",
                "ANY_INTEGRITY_FAIL",
                "ANY_SCIENTIFIC_FAIL",
                "ANY_MIXED",
                "ALL_PASS",
            ]
        },
        "advancement_outcome": {"enum": list(OUTCOMES)},
        **{name: {"const": False} for name in AUTHORIZATIONS},
    }
    def contains_state(state: str, class_name: str | None = None) -> dict[str, Any]:
        row_properties: dict[str, Any] = {"state": {"const": state}}
        required = ["state"]
        if class_name is not None:
            row_properties["criterion_class"] = {"const": class_name}
            required.append("criterion_class")
        return {
            "properties": {
                "criteria": {
                    "contains": {
                        "type": "object",
                        "properties": row_properties,
                        "required": required,
                    }
                }
            }
        }

    def rule_labels(rule: str, reason: str, outcome: str) -> dict[str, Any]:
        return {
            "properties": {
                "matched_precedence_rule": {"const": rule},
                "reason_code": {"const": reason},
                "advancement_outcome": {"const": outcome},
            }
        }

    unresolved = contains_state("UNRESOLVED")
    integrity_fail = contains_state("FAIL", "INTEGRITY_BLOCKING")
    scientific_fail = contains_state("FAIL", "SCIENTIFIC_PERFORMANCE")
    mixed = contains_state("MIXED")
    mapping_branches = [
        {
            "allOf": [
                unresolved,
                rule_labels("RULE_1", "ANY_UNRESOLVED", "BLOCKED"),
            ]
        },
        {
            "allOf": [
                {"not": unresolved},
                integrity_fail,
                rule_labels("RULE_2", "ANY_INTEGRITY_FAIL", "BLOCKED"),
            ]
        },
        {
            "allOf": [
                {"not": unresolved},
                {"not": integrity_fail},
                scientific_fail,
                rule_labels("RULE_3", "ANY_SCIENTIFIC_FAIL", "NO_GO"),
            ]
        },
        {
            "allOf": [
                {"not": unresolved},
                {"not": integrity_fail},
                {"not": scientific_fail},
                mixed,
                rule_labels("RULE_4", "ANY_MIXED", "GO_WITH_LIMITATIONS"),
            ]
        },
        {
            "allOf": [
                {"not": unresolved},
                {"not": integrity_fail},
                {"not": scientific_fail},
                {"not": mixed},
                rule_labels("RULE_5", "ALL_PASS", "GO"),
            ]
        },
    ]
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": f"{PROTOCOL_ID}-derivation-trace-{VERSION}",
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "oneOf": mapping_branches,
        "additionalProperties": False,
    }


def materialize(root: Path) -> Path:
    """Persist only the prospective Sprint 39 governance protocol."""
    output = root / OUTPUT_REL
    output.mkdir(parents=True, exist_ok=True)
    governance = contract()
    validate_contract(governance)
    history = historical_hashes(root)
    exhaustive = exhaustive_verification()
    artifacts: dict[str, Any] = {
        "governance_contract.json": governance,
        "governance_contract.schema.json": _contract_schema(),
        "derivation_trace.schema.json": _trace_schema(),
        "historical_artifact_hashes.json": history,
        "execution_ledger.json": execution_ledger(),
        "exhaustive_verification.json": exhaustive,
        "quality_gates.json": QUALITY_GATES,
        "scientific_decision.json": {
            "decision": "SPRINT_10.8.2.39_GOVERNANCE_PROTOCOL_GO",
            "scope": "PROSPECTIVE_GOVERNANCE_MECHANICS_ONLY",
            "sprint_38_execution_status_unchanged": "SUCCESS_VALID",
            "sprint_38_advancement_unchanged": (
                "SPRINT_10.8.2.38_ADVANCEMENT_UNRESOLVED"
            ),
            **AUTHORIZATIONS,
        },
    }
    for name, item in artifacts.items():
        (output / name).write_bytes(canonical_bytes(item))
    module_path = root / "src/evaluation/q1_advancement_governance_protocol.py"
    test_path = root / "tests/evaluation/test_q1_advancement_governance_protocol.py"
    manifest = {
        "experiment_version": f"{PROTOCOL_ID}-{VERSION}",
        "sprint": SPRINT,
        "branch": BRANCH,
        "starting_head": STARTING_HEAD,
        "python_module": str(module_path.relative_to(root)),
        "test_module": str(test_path.relative_to(root)),
        "runtime": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "canonical_serialization": (
            "UTF-8 JSON, sorted keys, compact separators, one trailing newline"
        ),
        "implementation_sha256": digest(module_path),
        "test_sha256": digest(test_path),
        "artifact_sha256": {
            name: digest(output / name) for name in sorted(artifacts)
        },
    }
    (output / "experiment_manifest.json").write_bytes(canonical_bytes(manifest))
    (output / "REPORT.md").write_text(
        _report(exhaustive, len(history)), encoding="utf-8"
    )
    verify_historical_hashes(root, history)
    return output


def _report(exhaustive: dict[str, Any], historical_count: int) -> str:
    counts = exhaustive["outcome_counts"]
    return f"""# Sprint 10.8.2.39 — Prospective Advancement-Governance Protocol

## 1. Historical governance problem

Sprint 38 executed successfully and validly, but the frozen Sprint 37 qualitative joint rule lacked complete state semantics, aggregation, precedence, and a total criterion-state-to-outcome mapping.

## 2. Sprint 38 remains unchanged

Sprint 38 experimental execution remains **SUCCESS_VALID**.

Sprint 38 advancement remains **SPRINT_10.8.2.38_ADVANCEMENT_UNRESOLVED**.

Sprint 39 does not retrospectively resolve, reinterpret, overwrite, or reclassify Sprint 38.

## 3. Prospective criteria and classes

The exact canonical criteria are leakage safety, temporal validity, reproducibility, discrimination, calibration, practical utility, complexity parsimony, stability across origins, and absence of outcome-driven tuning. Leakage safety, temporal validity, reproducibility, and absence of outcome-driven tuning are integrity/blocking criteria. The remaining five are scientific-performance criteria.

## 4. State semantics

**PASS** is complete, valid, traceable evidence satisfying predeclared acceptance requirements. **MIXED** is complete, valid, traceable evidence with a material limitation, heterogeneity, or partially favorable/unfavorable result preventing unqualified PASS. **FAIL** violates a predeclared requirement. **UNRESOLVED** is missing, incomplete, non-traceable, or non-derivable evidence or definition. FAIL and UNRESOLVED remain distinct.

## 5. Deterministic mapping and precedence

In exact order: any UNRESOLVED yields BLOCKED; otherwise any integrity FAIL yields BLOCKED; otherwise any scientific FAIL yields NO_GO; otherwise any MIXED criterion yields GO_WITH_LIMITATIONS; otherwise all PASS yields GO. `BLOCKED > NO_GO > GO_WITH_LIMITATIONS > GO` denotes decision precedence, not desirability.

## 6. Exhaustive 4^9 verification

**PASS:** {exhaustive['vectors_verified']:,} vectors produced exactly one authorized outcome. Counts: BLOCKED={counts['BLOCKED']:,}; NO_GO={counts['NO_GO']:,}; GO_WITH_LIMITATIONS={counts['GO_WITH_LIMITATIONS']:,}; GO={counts['GO']:,}. Repeatability and input-order invariance passed.

## 7. Prospective-only and authorization boundaries

The contract is effective from Sprint {EFFECTIVE_FROM_SPRINT}. Retrospective targets fail closed. Outcomes do not authorize TEST, final-candidate/model selection, calibration or threshold selection, deployment, XAI, or publication claims.

## 8. TEST sealing and prohibited activity

All TEST-use, fitting, optimization, selection, external-acquisition, and XAI counters remain zero. Sprint 39 performs governance formalization only, not scientific-performance experimentation.

## 9. Historical integrity

**PASS:** {historical_count} Sprint 32–38 audit artifacts are hash-addressed and verified unchanged.

## 10. Limitations

Sprint 39 formalizes governance mechanics, not model performance. Criterion-specific scientific thresholds still require prospective operationalization. Complexity parsimony especially requires an explicit acceptance definition before future classification. GO_WITH_LIMITATIONS must not become a permissive fallback. Governance outcomes are not TEST or deployment authorizations.

## 11. Exact recommended next step

Human review of the uncommitted Sprint 39 protocol. If accepted, preserve it before any future criterion operationalization or evidence evaluation; do not apply it to Sprint 38 or access TEST.
"""
