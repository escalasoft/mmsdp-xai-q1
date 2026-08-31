"""Leakage-safe contracts for the prospective Q1 WPDP/LOPO campaign.

This module prepares and validates campaign state.  It deliberately contains no
final-target loader, scorer, metric evaluation, or automatic authorization path.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from typing import Any

ALGORITHMS = ("LR", "RF", "XGBOOST", "LIGHTGBM")
MODALITIES = ("C", "P", "T", "C+P", "C+T", "P+T", "C+P+T")
CALIBRATION_BY_MODALITY = {
    modality: (
        ("UNCALIBRATED", "PLATT", "ISOTONIC")
        if modality == "C+P+T"
        else ("UNCALIBRATED",)
    )
    for modality in MODALITIES
}
DESIGNS = ("WPDP", "LOPO_CPDP")


class CampaignContractError(ValueError):
    """Raised when a frozen campaign contract would be violated."""


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def digest(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


@dataclass(frozen=True, slots=True)
class SourceOnlyStandardizer:
    """Immutable numeric state learned exclusively from SOURCE TRAIN rows."""

    feature_names: tuple[str, ...]
    retained_features: tuple[str, ...]
    medians: tuple[float, ...]
    means: tuple[float, ...]
    standard_deviations: tuple[float, ...]
    fit_scope: str = "SOURCE_TRAIN_ONLY"

    @classmethod
    def fit(
        cls,
        source_train: list[list[float | int | None]],
        feature_names: list[str] | tuple[str, ...],
    ) -> SourceOnlyStandardizer:
        names = tuple(feature_names)
        if not source_train or not names:
            raise CampaignContractError("SOURCE TRAIN and feature names are required")
        if len(set(names)) != len(names) or any(
            len(row) != len(names) for row in source_train
        ):
            raise CampaignContractError("SOURCE TRAIN schema is invalid")
        columns = list(zip(*source_train, strict=True))
        medians: list[float] = []
        means: list[float] = []
        deviations: list[float] = []
        retained: list[str] = []
        for name, column in zip(names, columns, strict=True):
            observed = [float(value) for value in column if value is not None]
            if not observed or any(not math.isfinite(value) for value in observed):
                raise CampaignContractError(f"invalid SOURCE TRAIN feature: {name}")
            fill = float(median(observed))
            complete = [fill if value is None else float(value) for value in column]
            mean = math.fsum(complete) / len(complete)
            variance = math.fsum((value - mean) ** 2 for value in complete) / len(
                complete
            )
            deviation = math.sqrt(variance)
            if deviation == 0.0:
                continue
            retained.append(name)
            medians.append(fill)
            means.append(mean)
            deviations.append(deviation)
        if not retained:
            raise CampaignContractError(
                "SOURCE TRAIN has no non-constant numeric feature"
            )
        return cls(
            names, tuple(retained), tuple(medians), tuple(means), tuple(deviations)
        )

    def transform(
        self,
        rows: list[list[float | int | None]],
        feature_names: list[str] | tuple[str, ...],
    ) -> tuple[tuple[float, ...], ...]:
        if tuple(feature_names) != self.feature_names:
            raise CampaignContractError("inference schema differs from SOURCE TRAIN")
        indexes = [self.feature_names.index(name) for name in self.retained_features]
        output = []
        for row in rows:
            if len(row) != len(self.feature_names):
                raise CampaignContractError(
                    "inference row differs from SOURCE TRAIN schema"
                )
            transformed = []
            for position, fill, mean, deviation in zip(
                indexes, self.medians, self.means, self.standard_deviations, strict=True
            ):
                value = fill if row[position] is None else float(row[position])
                if not math.isfinite(value):
                    raise CampaignContractError("inference features must be finite")
                transformed.append((value - mean) / deviation)
            output.append(tuple(transformed))
        return tuple(output)

    def to_dict(self) -> dict[str, object]:
        return {
            "fit_scope": self.fit_scope,
            "feature_names": list(self.feature_names),
            "retained_features": list(self.retained_features),
            "medians": list(self.medians),
            "means": list(self.means),
            "standard_deviations": list(self.standard_deviations),
            "target_fitted_state": False,
        }


def validate_feature_schema(
    actual: dict[str, list[str] | tuple[str, ...]],
    expected: dict[str, list[str] | tuple[str, ...]],
    denylist: set[str] | frozenset[str],
) -> None:
    """Reject incompatible, cross-modality, or prohibited predictor schemas."""
    if set(actual) != {"C", "P", "T"} or set(expected) != {"C", "P", "T"}:
        raise CampaignContractError("exact C/P/T modality membership is required")
    seen: set[str] = set()
    for modality in ("C", "P", "T"):
        fields = tuple(actual[modality])
        if fields != tuple(expected[modality]) or len(fields) != len(set(fields)):
            raise CampaignContractError(f"incompatible {modality} schema")
        if seen.intersection(fields):
            raise CampaignContractError("features cross modality boundaries")
        prohibited = set(fields).intersection(denylist)
        if prohibited:
            raise CampaignContractError(f"prohibited predictors: {sorted(prohibited)}")
        seen.update(fields)


def lopo_membership(
    project_samples: dict[str, tuple[str, ...] | list[str]], target_project: str
) -> dict[str, object]:
    """Create deterministic pooled-SOURCE and held-out-TARGET membership."""
    if target_project not in project_samples or len(project_samples) < 2:
        raise CampaignContractError(
            "LOPO requires a known target and at least two projects"
        )
    source_projects = tuple(sorted(set(project_samples).difference({target_project})))
    source = tuple(
        (project, sample)
        for project in source_projects
        for sample in sorted(project_samples[project])
    )
    target = tuple(
        (target_project, sample) for sample in sorted(project_samples[target_project])
    )
    if set(source).intersection(target):
        raise CampaignContractError("SOURCE and TARGET overlap")
    payload = {
        "source_projects": list(source_projects),
        "target_project": target_project,
        "source_sample_count": len(source),
        "target_sample_count": len(target),
        "source_identity_digest": digest(source),
        "target_identity_digest": digest(target),
        "source_target_overlap": 0,
    }
    return {**payload, "membership_digest": digest(payload)}


def generate_campaign_cells(
    targets: list[str] | tuple[str, ...],
) -> list[dict[str, object]]:
    """Generate the frozen 36-cell-per-design target matrix without executing it."""
    cells = []
    for design in DESIGNS:
        for target in sorted(targets):
            for algorithm in ALGORITHMS:
                for modality in MODALITIES:
                    for calibration in CALIBRATION_BY_MODALITY[modality]:
                        core = {
                            "design": design,
                            "target": target,
                            "algorithm": algorithm,
                            "modality": modality,
                            "calibration": calibration,
                            "seed": 20260829,
                        }
                        cells.append(
                            {
                                **core,
                                "configuration_id": digest(core)[:24],
                                "execution_status": "BLOCKED_PRE_EXECUTION",
                            }
                        )
    if len({cell["configuration_id"] for cell in cells}) != len(cells):
        raise CampaignContractError("campaign configuration identifiers collide")
    return cells


REQUIRED_TARGET_BINDINGS = (
    "dataset_identity",
    "target_identity",
    "temporal_boundary_digest",
    "sample_manifest_sha256",
    "provenance_digest",
    "feature_schema_digest",
)


def consume_target_authorization(
    policy: dict[str, Any], request: dict[str, Any], ledger_path: Path
) -> dict[str, Any]:
    """Atomically consume a one-use, identity-bound authorization in later sprints."""
    if policy.get("execution_authorized") is not True:
        raise CampaignContractError("TARGET execution is not authorized")
    if policy.get("access_counter") != 0:
        raise CampaignContractError("TARGET authorization was already consumed")
    if policy.get("authorization_token") is None:
        raise CampaignContractError("explicit authorization token is absent")
    if request.get("authorization_token") != policy["authorization_token"]:
        raise CampaignContractError("authorization token mismatch")
    for field in REQUIRED_TARGET_BINDINGS:
        if not policy.get(field) or request.get(field) != policy[field]:
            raise CampaignContractError(f"TARGET binding mismatch: {field}")
    if ledger_path.exists():
        raise CampaignContractError("TARGET access ledger already exists")
    ledger = {
        "access_counter": 1,
        "authorization_consumed": True,
        "request_digest": digest({key: request[key] for key in sorted(request)}),
        "target_identity": request["target_identity"],
    }
    descriptor = os.open(ledger_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(descriptor, canonical_bytes(ledger))
    finally:
        os.close(descriptor)
    return ledger
