"""Reusable, fail-closed prospective ground-truth contracts.

The module validates evidence supplied by an acquisition process.  It never
discovers labels from commit text and never treats a fixing commit as the
corresponding bug-inducing commit.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum


class EvidenceState(StrEnum):
    """Mutually exclusive prospective evidence states."""

    SUPPORTED_POSITIVE = "SUPPORTED_POSITIVE"
    SUPPORTED_NEGATIVE = "SUPPORTED_NEGATIVE"
    RIGHT_CENSORED = "RIGHT_CENSORED"
    PROVENANCE_UNRESOLVED = "PROVENANCE_UNRESOLVED"
    AMBIGUOUS = "AMBIGUOUS"


class GroundTruthContractError(ValueError):
    """Raised when prospective evidence violates a scientific invariant."""


@dataclass(frozen=True)
class AttributionEvidence:
    """One repair-line attribution from a fixing commit into prior history."""

    defect_evidence_id: str
    defect_evidence_location: str
    fixing_sha: str
    parent_sha: str
    file_path: str
    repair_or_deleted_line: str
    line_history_evidence: str
    blamed_sha: str
    filters_applied: tuple[str, ...]
    attribution_result: str
    decision_reason: str
    evidence_timestamp: str
    evidence_hash: str

    def validate(self) -> list[str]:
        """Return all provenance defects without guessing missing values."""
        errors: list[str] = []
        required = {
            "defect_evidence_id": self.defect_evidence_id,
            "defect_evidence_location": self.defect_evidence_location,
            "fixing_sha": self.fixing_sha,
            "parent_sha": self.parent_sha,
            "file_path": self.file_path,
            "repair_or_deleted_line": self.repair_or_deleted_line,
            "line_history_evidence": self.line_history_evidence,
            "blamed_sha": self.blamed_sha,
            "attribution_result": self.attribution_result,
            "decision_reason": self.decision_reason,
            "evidence_timestamp": self.evidence_timestamp,
            "evidence_hash": self.evidence_hash,
        }
        errors.extend(
            f"missing {name}" for name, value in required.items() if not value
        )
        if not self.filters_applied:
            errors.append("missing filters_applied")
        if self.fixing_sha and self.fixing_sha == self.blamed_sha:
            errors.append("fixing commit must not be treated as inducing commit")
        if self.attribution_result not in {"ACCEPTED", "REJECTED", "AMBIGUOUS"}:
            errors.append("invalid attribution_result")
        return errors


@dataclass(frozen=True)
class VerificationMaturityRule:
    """Predeclared rule for affirmative prospective negative evidence."""

    rule_id: str
    window_seconds: int
    evidence_basis: str
    evidence_location: str
    project_aware: bool
    tracker_coverage_required: bool = True
    prediction_independent: bool = True
    predeclared: bool = True

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.rule_id or not self.evidence_basis or not self.evidence_location:
            errors.append("maturity rule provenance is incomplete")
        if self.window_seconds <= 0:
            errors.append("maturity window must be positive")
        if not self.tracker_coverage_required:
            errors.append("maturity rule must require complete evidence coverage")
        if not self.prediction_independent:
            errors.append("maturity rule must be prediction-independent")
        if not self.predeclared:
            errors.append("maturity rule must be predeclared")
        return errors


@dataclass(frozen=True)
class GroundTruthDecision:
    """A deterministic prospective label decision."""

    state: EvidenceState
    label: int | None
    reason: str
    accepted_attribution_hashes: tuple[str, ...] = ()


def canonical_bytes(value: object) -> bytes:
    """Serialize evidence deterministically."""
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode()


def evidence_digest(value: object) -> str:
    """Return a SHA-256 digest for canonical evidence."""
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def decide_ground_truth(
    *,
    commit_sha: str,
    commit_epoch: int,
    boundary_sha: str,
    boundary_epoch: int,
    identity_resolved: bool,
    provenance_resolved: bool,
    attributions: Sequence[AttributionEvidence] = (),
    negative_verification_complete: bool = False,
    tracker_coverage_complete: bool = False,
    maturity_rule: VerificationMaturityRule | None = None,
    evidence_cutoff_epoch: int | None = None,
) -> GroundTruthDecision:
    """Apply temporal, attribution, maturity, and censoring rules."""
    if (commit_epoch, commit_sha) <= (boundary_epoch, boundary_sha):
        raise GroundTruthContractError(
            "prospective identity is not strictly post-boundary"
        )
    if not identity_resolved or not provenance_resolved:
        return GroundTruthDecision(
            EvidenceState.PROVENANCE_UNRESOLVED,
            None,
            "identity or provenance incomplete",
        )

    accepted: list[AttributionEvidence] = []
    ambiguous = False
    for attribution in attributions:
        if attribution.validate():
            ambiguous = True
            continue
        if attribution.attribution_result == "AMBIGUOUS":
            ambiguous = True
        elif attribution.attribution_result == "ACCEPTED":
            accepted.append(attribution)
    accepted_candidates = {item.blamed_sha for item in accepted}
    if ambiguous or len(accepted_candidates) > 1:
        return GroundTruthDecision(
            EvidenceState.AMBIGUOUS, None, "attribution evidence is ambiguous"
        )
    if accepted_candidates:
        candidate = next(iter(accepted_candidates))
        if candidate != commit_sha:
            return GroundTruthDecision(
                EvidenceState.PROVENANCE_UNRESOLVED,
                None,
                "accepted attribution does not match prospective identity",
            )
        return GroundTruthDecision(
            EvidenceState.SUPPORTED_POSITIVE,
            1,
            "validated defect-to-fix-to-repair-line-to-blame chain",
            tuple(sorted(item.evidence_hash for item in accepted)),
        )

    if not negative_verification_complete:
        return GroundTruthDecision(
            EvidenceState.PROVENANCE_UNRESOLVED,
            None,
            "no affirmative positive or negative evidence",
        )
    if maturity_rule is None or maturity_rule.validate():
        return GroundTruthDecision(
            EvidenceState.PROVENANCE_UNRESOLVED,
            None,
            "defensible maturity rule unavailable",
        )
    if not tracker_coverage_complete:
        return GroundTruthDecision(
            EvidenceState.PROVENANCE_UNRESOLVED,
            None,
            "authoritative evidence coverage incomplete",
        )
    if evidence_cutoff_epoch is None:
        raise GroundTruthContractError("evidence cutoff required by maturity rule")
    if evidence_cutoff_epoch - commit_epoch < maturity_rule.window_seconds:
        return GroundTruthDecision(EvidenceState.RIGHT_CENSORED, None, "immature")
    return GroundTruthDecision(
        EvidenceState.SUPPORTED_NEGATIVE, 0, "affirmatively verified and mature"
    )


def validate_project_gates(gates: Mapping[str, object]) -> tuple[bool, list[str]]:
    """Recompute the frozen G1-G15 project eligibility contract."""
    reasons: list[str] = []
    for number in range(1, 16):
        name = f"G{number}"
        if gates.get(name) is not True:
            reasons.append(f"FAIL_{name}")
    return not reasons, reasons
