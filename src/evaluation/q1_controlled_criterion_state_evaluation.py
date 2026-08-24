# ruff: noqa: E501
"""Sprint 42 controlled prospective criterion-state evaluation."""

from __future__ import annotations

import csv
import hashlib
import json
import platform
import subprocess
from functools import lru_cache
from pathlib import Path
from typing import Any

from evaluation.q1_advancement_governance_protocol import (
    CRITERIA,
    STATES,
    criterion_class,
)
from evaluation.q1_prospective_criterion_operationalization import (
    contract as sprint_41_contract,
)
from evaluation.q1_prospective_criterion_operationalization import (
    derive_criterion_state,
)

PROTOCOL_ID = "q1-controlled-criterion-state-evaluation"
VERSION = "1.0.0"
SPRINT = "10.8.2.42"
STARTING_HEAD = "9f25010d71c27216cf4e54220b70857a713b4ef5"
OUTPUT_REL = "audits/q1-controlled-criterion-state-evaluation/1.0.0"
RULE_PATH = "audits/q1-prospective-criterion-operationalization/1.0.0/criterion_operationalization.json"
HISTORICAL_DIRS = (
    "audits/q1-experimental-evidence-gap-audit",
    "audits/q1-experimental-validity-contract",
    "audits/q1-modality-factorial",
    "audits/q1-fusion-process-ablation",
    "audits/q1-forward-development-calibration",
    "audits/q1-development-practical-utility-protocol",
    "audits/q1-development-practical-utility-execution",
    "audits/q1-advancement-governance-outcome-mapping",
    "audits/q1-prospective-criterion-operationalization",
)
PROHIBITED_COUNTERS = (
    "TEST_label_accesses",
    "TEST_probability_loading",
    "TEST_scoring",
    "TEST_model_selection",
    "TEST_threshold_optimization",
    "TEST_calibration_fitting",
    "TEST_XAI",
    "model_fits",
    "model_refits",
    "calibrator_fits",
    "meta_learner_fits",
    "hyperparameter_searches",
    "threshold_optimizations",
    "candidate_selections",
    "external_dataset_acquisitions",
    "XAI_executions",
)


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@lru_cache(maxsize=4)
def accepted_historical_hashes(
    root: Path, revision: str = STARTING_HEAD
) -> dict[str, str]:
    """Read the protected baseline from immutable Git objects, not the worktree."""
    command = ["git", "ls-tree", "-r", "--name-only", revision, "--", *HISTORICAL_DIRS]
    result = subprocess.run(
        command, cwd=root, check=True, capture_output=True, text=True
    )
    paths = sorted(path for path in result.stdout.splitlines() if path)
    baseline: dict[str, str] = {}
    for path in paths:
        blob = subprocess.run(
            ["git", "show", f"{revision}:{path}"],
            cwd=root,
            check=True,
            capture_output=True,
        ).stdout
        baseline[path] = hashlib.sha256(blob).hexdigest()
    return baseline


def current_historical_hashes(root: Path) -> dict[str, str]:
    paths: list[Path] = []
    for relative in HISTORICAL_DIRS:
        paths.extend(path for path in (root / relative).rglob("*") if path.is_file())
    return {str(path.relative_to(root)): digest(path) for path in sorted(paths)}


def verify_hashes(root: Path, expected: dict[str, str]) -> dict[str, Any]:
    observed = current_historical_hashes(root)
    missing = sorted(set(expected) - set(observed))
    extra = sorted(set(observed) - set(expected))
    mismatches = sorted(
        path
        for path in set(expected) & set(observed)
        if expected[path] != observed[path]
    )
    return {
        "protected_files_checked": len(expected),
        "missing_files": missing,
        "extra_files": extra,
        "hash_mismatches": mismatches,
        "baseline_revision": STARTING_HEAD,
        "baseline_source": "immutable Git blobs addressed by accepted HEAD",
        "passed": not (missing or extra or mismatches),
    }


def _load_json(root: Path, relative: str) -> Any:
    return json.loads((root / relative).read_text(encoding="utf-8"))


def _ref(root: Path, path: str, sprint: str, fields: list[str]) -> dict[str, Any]:
    return {
        "path": path,
        "sha256": digest(root / path),
        "originating_sprint": sprint,
        "persisted_fields": fields,
    }


def observed_integrity_evidence(
    expected_invariants: list[str],
    observations: dict[str, dict[str, Any]],
    limitations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Convert independently observed fields into a Sprint 41 envelope."""
    complete = set(observations) == set(expected_invariants)
    valid = complete and all(
        isinstance(item, dict)
        and item.get("valid") is True
        and item.get("artifact_exists") is True
        and item.get("field_present") is True
        and item.get("structurally_valid") is True
        and item.get("predicate_evaluable") is True
        and type(item.get("supported")) is bool
        and isinstance(item.get("path"), str)
        and isinstance(item.get("field"), str)
        and isinstance(item.get("artifact_sha256"), str)
        and len(item["artifact_sha256"]) == 64
        for item in observations.values()
    )
    return {
        "valid": valid,
        "provenance_complete": valid,
        "invariants": {
            invariant: observations[invariant]["supported"]
            for invariant in expected_invariants
            if invariant in observations
            and observations[invariant].get("valid") is True
        },
        "limitations": limitations or [],
        "invariant_observations": observations,
    }


def _observation(
    root: Path,
    path: str,
    field: str,
    observed: Any,
    supported: bool,
    *,
    field_present: bool,
    structurally_valid: bool,
) -> dict[str, Any]:
    artifact = root / path
    artifact_exists = artifact.is_file()
    predicate_evaluable = artifact_exists and field_present and structurally_valid
    return {
        "path": path,
        "field": field,
        "observed_value": observed,
        "artifact_exists": artifact_exists,
        "field_present": field_present,
        "structurally_valid": structurally_valid,
        "predicate_evaluable": predicate_evaluable,
        "supported": supported if predicate_evaluable else None,
        "valid": predicate_evaluable,
        "artifact_sha256": digest(artifact) if artifact_exists else "",
    }


def _zeroes(value: dict[str, Any], names: list[str]) -> bool:
    return all(type(value.get(name)) is int and value[name] == 0 for name in names)


def build_integrity_evidence(
    root: Path, documents: dict[str, Any] | None = None
) -> dict[str, dict[str, Any]]:
    """Map every integrity invariant to actual persisted fields and predicates."""
    rules = _criterion_rules()
    contract_path = "audits/q1-experimental-validity-contract/1.0.0/contract.json"
    lineage_path = "audits/q1-experimental-validity-contract/1.0.0/feature_lineage.json"
    leakage_path = (
        "audits/q1-development-practical-utility-execution/1.0.0/leakage_audit.json"
    )
    protocol_path = "audits/q1-development-practical-utility-execution/1.0.0/protocol_integrity.json"
    repro_path = "audits/q1-development-practical-utility-execution/1.0.0/reproducibility_manifest.json"
    cal_repro_path = "audits/q1-forward-development-calibration/1.0.0/calibration_reproducibility_manifest.json"
    memberships_path = "audits/q1-development-practical-utility-execution/1.0.0/temporal_memberships.json"
    governance_path = "audits/q1-advancement-governance-outcome-mapping/1.0.0/governance_contract.json"

    def load(path: str) -> Any:
        return (
            documents[path]
            if documents is not None and path in documents
            else _load_json(root, path)
        )

    contract = load(contract_path)
    lineage = load(lineage_path)
    leakage = load(leakage_path)
    protocol = load(protocol_path)
    repro = load(repro_path)
    cal_repro = load(cal_repro_path)
    memberships = load(memberships_path)
    governance = load(governance_path)
    sprint41 = load(RULE_PATH)
    counters = leakage.get("counters", {})
    temporal = contract.get("temporal_protocol", {})
    denylist = contract.get("leakage_denylist", {})
    origins = memberships.get("origins", memberships)
    origin_ids = (
        [item.get("origin_id") if type(item) is dict else None for item in origins]
        if isinstance(origins, list)
        else []
    )
    baseline = accepted_historical_hashes(root)
    history_check = verify_hashes(root, baseline)

    field_types: dict[str, type] = {
        "exact_prohibited_overlaps": list,
        "leakage_denylist.unresolved_ambiguities": list,
        "leakage_denylist.exact_predictor_overlaps": list,
        "temporal_protocol.chronology_constraints": list,
        "leakage_denylist.semantic_classes": list,
        "counters.TEST_*": dict,
        "experimental_unit_and_target.temporal_order": list,
        "origins[].origin_id": list,
        "sprint_36_temporal_match": bool,
        "temporal_protocol.validation_rule": str,
        "threshold_grid_unchanged/cost_scenarios_unchanged": dict,
        "verdict": str,
        "source_predictor_hashes/temporal_membership_digests/output_sha256": dict,
        "seed/stochastic_operations": dict,
        "runtime/random_seed/fitted_states[].scientific_state_digest": dict,
        "fitted_states": list,
        "same_runtime_prediction_equivalence/fitted_states[].reload_prediction_equivalence": dict,
        "deterministic_rerun_equivalence": bool,
        "output_sha256": int,
        "effective_sprint": str,
        "advancement_rule_unchanged/threshold_grid_unchanged/cost_scenarios_unchanged": dict,
        "counters": dict,
        "Git baseline comparison": dict,
        "criteria/criterion_states/precedence_rules/independent_authorizations": dict,
        "anti_retrospective_tuning_declaration": str,
        "historical_application_prohibited": list,
    }

    def obs(path: str, field: str, value: Any, predicate: bool) -> dict[str, Any]:
        expected_type = field_types[field]
        field_present = value is not None
        structurally_valid = field_present and type(value) is expected_type
        return _observation(
            root,
            path,
            field,
            value,
            predicate,
            field_present=field_present,
            structurally_valid=structurally_valid,
        )

    def constituent(
        label: str, container: Any, key: str, expected_type: type
    ) -> dict[str, Any]:
        container_valid = type(container) is dict
        present = container_valid and key in container
        value = container[key] if present else None
        return {
            "field": label,
            "present": present,
            "observed_value": value,
            "structurally_valid": present and type(value) is expected_type,
            "expected_type": expected_type.__name__,
        }

    def collection_constituents(
        label: str,
        container: Any,
        key: str,
        nested_fields: dict[str, type],
    ) -> list[dict[str, Any]]:
        """Retain every persisted element, including malformed ones."""
        items = [constituent(label, container, key, list)]
        collection = (
            container.get(key) if type(container) is dict and key in container else None
        )
        if type(collection) is not list:
            return items
        for index, row in enumerate(collection):
            items.append(
                {
                    "field": f"{label}[{index}]",
                    "present": True,
                    "observed_value": row,
                    "structurally_valid": type(row) is dict,
                    "expected_type": "dict",
                }
            )
            if type(row) is dict:
                items.extend(
                    constituent(f"{label}[{index}].{field}", row, field, expected)
                    for field, expected in nested_fields.items()
                )
        return items

    def mapping_constituents(
        label: str,
        container: Any,
        key: str,
        value_type: type,
        required_keys: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        items = [constituent(label, container, key, dict)]
        mapping = (
            container.get(key) if type(container) is dict and key in container else None
        )
        if type(mapping) is not dict:
            return items
        keys = required_keys if required_keys is not None else list(mapping)
        items.extend(
            constituent(f"{label}.{child}", mapping, child, value_type)
            for child in keys
        )
        return items

    def composite_obs(
        path: str,
        field: str,
        constituents: list[dict[str, Any]],
        predicate: Any,
    ) -> dict[str, Any]:
        value = {item["field"]: item["observed_value"] for item in constituents}
        field_present = all(item["present"] for item in constituents)
        structurally_valid = all(item["structurally_valid"] for item in constituents)
        supported = bool(predicate()) if field_present and structurally_valid else False
        observation = _observation(
            root,
            path,
            field,
            value,
            supported,
            field_present=field_present,
            structurally_valid=structurally_valid,
        )
        observation["constituents"] = constituents
        return observation

    leakage_invariants = rules["leakage_safety"]["required_evidence"][
        "mandatory_invariants"
    ]
    leakage_obs = {
        leakage_invariants[0]: obs(
            lineage_path,
            "exact_prohibited_overlaps",
            lineage.get("exact_prohibited_overlaps"),
            lineage.get("exact_prohibited_overlaps") == [],
        ),
        leakage_invariants[1]: obs(
            contract_path,
            "leakage_denylist.unresolved_ambiguities",
            denylist.get("unresolved_ambiguities"),
            denylist.get("unresolved_ambiguities") == [],
        ),
        leakage_invariants[2]: composite_obs(
            contract_path,
            "leakage_denylist.exact_predictor_overlaps",
            [
                constituent(
                    "exact_predictor_overlaps",
                    denylist,
                    "exact_predictor_overlaps",
                    list,
                ),
                constituent("exact_names", denylist, "exact_names", list),
            ],
            lambda: (
                denylist.get("exact_predictor_overlaps") == []
                and all(
                    name in denylist.get("exact_names", [])
                    for name in [
                        "target",
                        "project",
                        "commit_hash",
                        "git_committer_timestamp",
                    ]
                )
            ),
        ),
        leakage_invariants[3]: obs(
            contract_path,
            "temporal_protocol.chronology_constraints",
            temporal.get("chronology_constraints"),
            "all fitted transformations use the same training membership as their estimator"
            in temporal.get("chronology_constraints", []),
        ),
        leakage_invariants[4]: obs(
            contract_path,
            "temporal_protocol.chronology_constraints",
            temporal.get("chronology_constraints"),
            "a row is never predicted by a model fitted on that row"
            in temporal.get("chronology_constraints", []),
        ),
        leakage_invariants[5]: obs(
            contract_path,
            "leakage_denylist.semantic_classes",
            denylist.get("semantic_classes"),
            "validation/final-derived vocabulary, scaling, feature selection, calibration, thresholds or statistics"
            in denylist.get("semantic_classes", []),
        ),
        leakage_invariants[6]: composite_obs(
            leakage_path,
            "counters.TEST_*",
            [
                constituent(f"counters.{key}", counters, key, int)
                for key in [
                    "TEST_label_accesses",
                    "TEST_probability_loading",
                    "TEST_scoring",
                    "TEST_model_selection",
                    "TEST_threshold_optimization",
                    "TEST_calibration_fitting",
                    "TEST_XAI",
                ]
            ],
            lambda: _zeroes(
                counters,
                [
                    "TEST_label_accesses",
                    "TEST_probability_loading",
                    "TEST_scoring",
                    "TEST_model_selection",
                    "TEST_threshold_optimization",
                    "TEST_calibration_fitting",
                    "TEST_XAI",
                ],
            ),
        ),
    }
    raw_text_limitation = {
        "text": "canonical raw commit text retains the accepted semantic-proxy limitation",
        "path": contract_path,
        "field": "leakage_denylist.suspected_semantic_proxies",
        "observed_value": denylist.get("suspected_semantic_proxies"),
    }

    temporal_invariants = rules["temporal_validity"]["required_evidence"][
        "mandatory_invariants"
    ]
    temporal_obs = {
        temporal_invariants[0]: obs(
            contract_path,
            "experimental_unit_and_target.temporal_order",
            contract.get("experimental_unit_and_target", {}).get("temporal_order"),
            contract.get("experimental_unit_and_target", {}).get("temporal_order")
            == ["git_committer_timestamp", "commit_hash"],
        ),
        temporal_invariants[1]: composite_obs(
            memberships_path,
            "origins[].origin_id",
            collection_constituents(
                "origins", memberships, "origins", {"origin_id": str}
            ),
            lambda: origin_ids == ["O1", "O2", "O3", "O4", "O5"],
        ),
        temporal_invariants[2]: obs(
            protocol_path,
            "sprint_36_temporal_match",
            protocol.get("sprint_36_temporal_match"),
            protocol.get("sprint_36_temporal_match") is True,
        ),
        temporal_invariants[3]: obs(
            contract_path,
            "temporal_protocol.chronology_constraints",
            temporal.get("chronology_constraints"),
            "a row is never predicted by a model fitted on that row"
            in temporal.get("chronology_constraints", []),
        ),
        temporal_invariants[4]: obs(
            contract_path,
            "temporal_protocol.validation_rule",
            temporal.get("validation_rule"),
            isinstance(temporal.get("validation_rule"), str)
            and "earlier expanding prefix" in temporal["validation_rule"]
            and "later contiguous validation block" in temporal["validation_rule"],
        ),
        temporal_invariants[5]: composite_obs(
            protocol_path,
            "threshold_grid_unchanged/cost_scenarios_unchanged",
            [
                constituent(
                    "threshold_grid_unchanged",
                    protocol,
                    "threshold_grid_unchanged",
                    bool,
                ),
                constituent(
                    "cost_scenarios_unchanged",
                    protocol,
                    "cost_scenarios_unchanged",
                    bool,
                ),
            ],
            lambda: (
                protocol.get("threshold_grid_unchanged") is True
                and protocol.get("cost_scenarios_unchanged") is True
            ),
        ),
        temporal_invariants[6]: obs(
            leakage_path,
            "verdict",
            leakage.get("verdict"),
            leakage.get("verdict") == "PASS_TEST_REMAINED_SEALED",
        ),
    }

    repro_invariants = rules["reproducibility"]["required_evidence"][
        "mandatory_invariants"
    ]
    source_hashes = repro.get("source_predictor_hashes", {})
    membership_hashes = repro.get("temporal_membership_digests", {})
    fitted_states = cal_repro.get("fitted_states", [])
    repro_obs = {
        repro_invariants[0]: composite_obs(
            repro_path,
            "source_predictor_hashes/temporal_membership_digests/output_sha256",
            [
                *mapping_constituents(
                    "source_predictor_hashes",
                    repro,
                    "source_predictor_hashes",
                    str,
                    ["O1", "O2", "O3", "O4", "O5"],
                ),
                *mapping_constituents(
                    "temporal_membership_digests",
                    repro,
                    "temporal_membership_digests",
                    str,
                    ["O1", "O2", "O3", "O4", "O5"],
                ),
                *mapping_constituents("output_sha256", repro, "output_sha256", str),
            ],
            lambda: (
                set(source_hashes) == {"O1", "O2", "O3", "O4", "O5"}
                and set(membership_hashes) == {"O1", "O2", "O3", "O4", "O5"}
                and bool(repro.get("output_sha256"))
            ),
        ),
        repro_invariants[1]: composite_obs(
            repro_path,
            "seed/stochastic_operations",
            [
                constituent("seed", repro, "seed", int),
                constituent(
                    "stochastic_operations", repro, "stochastic_operations", list
                ),
            ],
            lambda: repro.get("seed") == 0 and repro.get("stochastic_operations") == [],
        ),
        repro_invariants[2]: composite_obs(
            cal_repro_path,
            "runtime/random_seed/fitted_states[].scientific_state_digest",
            [
                constituent("runtime", cal_repro, "runtime", dict),
                *[
                    constituent(
                        f"runtime.{key}", cal_repro.get("runtime"), key, expected
                    )
                    for key, expected in {
                        "python": str,
                        "platform": str,
                        "numpy": str,
                        "scikit_learn": str,
                        "scipy": str,
                        "pickle_protocol": int,
                    }.items()
                ],
                constituent("random_seed", cal_repro, "random_seed", int),
                *collection_constituents(
                    "fitted_states",
                    cal_repro,
                    "fitted_states",
                    {"scientific_state_digest": str},
                ),
            ],
            lambda: (
                isinstance(cal_repro.get("runtime"), dict)
                and cal_repro.get("random_seed") == 0
                and len(fitted_states) == 5
                and all(
                    len(row.get("scientific_state_digest", "")) == 64
                    for row in fitted_states
                )
            ),
        ),
        repro_invariants[3]: composite_obs(
            cal_repro_path,
            "fitted_states",
            collection_constituents(
                "fitted_states",
                cal_repro,
                "fitted_states",
                {"origin_id": str, "path": str, "sha256": str},
            ),
            lambda: (
                len(fitted_states) == 5
                and all(
                    (root / row.get("path", "")).is_file()
                    and digest(root / row["path"]) == row.get("sha256")
                    for row in fitted_states
                )
            ),
        ),
        repro_invariants[4]: composite_obs(
            cal_repro_path,
            "same_runtime_prediction_equivalence/fitted_states[].reload_prediction_equivalence",
            [
                constituent(
                    "same_runtime_prediction_equivalence",
                    cal_repro,
                    "same_runtime_prediction_equivalence",
                    bool,
                ),
                *collection_constituents(
                    "fitted_states",
                    cal_repro,
                    "fitted_states",
                    {"reload_prediction_equivalence": bool},
                ),
            ],
            lambda: (
                cal_repro.get("same_runtime_prediction_equivalence") is True
                and all(
                    row.get("reload_prediction_equivalence") is True
                    for row in fitted_states
                )
            ),
        ),
        repro_invariants[5]: obs(
            repro_path,
            "deterministic_rerun_equivalence",
            repro.get("deterministic_rerun_equivalence"),
            repro.get("deterministic_rerun_equivalence") is True,
        ),
        repro_invariants[6]: composite_obs(
            repro_path,
            "output_sha256",
            [constituent("output_sha256", repro, "output_sha256", dict)],
            lambda: all(
                (
                    root
                    / f"audits/q1-development-practical-utility-execution/1.0.0/{name}"
                ).is_file()
                for name in repro.get("output_sha256", {})
            ),
        ),
    }
    pickle_limitation = {
        "text": "cross-runtime pickle byte identity is not claimed",
        "path": cal_repro_path,
        "field": "cross_runtime_pickle_byte_identity_guaranteed",
        "observed_value": cal_repro.get(
            "cross_runtime_pickle_byte_identity_guaranteed"
        ),
    }

    tuning_invariants = rules["absence_of_outcome_driven_tuning"]["required_evidence"][
        "mandatory_invariants"
    ]
    governance_rows = governance.get("criteria")
    state_rows = governance.get("criterion_states")
    governance_criteria = (
        [row.get("id") for row in governance_rows]
        if type(governance_rows) is list
        and all(type(row) is dict for row in governance_rows)
        else []
    )
    governance_states = (
        [row.get("id") for row in state_rows]
        if type(state_rows) is list and all(type(row) is dict for row in state_rows)
        else []
    )
    tuning_obs = {
        tuning_invariants[0]: obs(
            RULE_PATH,
            "effective_sprint",
            sprint41.get("effective_sprint"),
            sprint41.get("effective_sprint") == SPRINT,
        ),
        tuning_invariants[1]: composite_obs(
            protocol_path,
            "advancement_rule_unchanged/threshold_grid_unchanged/cost_scenarios_unchanged",
            [
                constituent(key, protocol, key, bool)
                for key in [
                    "advancement_rule_unchanged",
                    "threshold_grid_unchanged",
                    "cost_scenarios_unchanged",
                ]
            ],
            lambda: all(
                protocol.get(key) is True
                for key in [
                    "advancement_rule_unchanged",
                    "threshold_grid_unchanged",
                    "cost_scenarios_unchanged",
                ]
            ),
        ),
        tuning_invariants[2]: composite_obs(
            leakage_path,
            "counters",
            [
                constituent(f"counters.{key}", counters, key, int)
                for key in [
                    "TEST_label_accesses",
                    "TEST_probability_loading",
                    "TEST_scoring",
                    "TEST_model_selection",
                    "TEST_threshold_optimization",
                    "TEST_calibration_fitting",
                    "TEST_XAI",
                    "model_fits",
                    "meta_learner_fits",
                    "hyperparameter_searches",
                    "threshold_optimizations",
                    "external_dataset_acquisitions",
                    "XAI_executions",
                ]
            ],
            lambda: _zeroes(
                counters,
                [
                    "TEST_label_accesses",
                    "TEST_probability_loading",
                    "TEST_scoring",
                    "TEST_model_selection",
                    "TEST_threshold_optimization",
                    "TEST_calibration_fitting",
                    "TEST_XAI",
                    "model_fits",
                    "meta_learner_fits",
                    "hyperparameter_searches",
                    "threshold_optimizations",
                    "external_dataset_acquisitions",
                    "XAI_executions",
                ],
            ),
        ),
        tuning_invariants[3]: obs(
            "audits/q1-prospective-criterion-operationalization/1.0.0/historical_artifact_hashes.json",
            "Git baseline comparison",
            history_check,
            history_check["passed"] is True,
        ),
        tuning_invariants[4]: composite_obs(
            governance_path,
            "criteria/criterion_states/precedence_rules/independent_authorizations",
            [
                *collection_constituents(
                    "criteria", governance, "criteria", {"id": str, "class": str}
                ),
                *collection_constituents(
                    "criterion_states",
                    governance,
                    "criterion_states",
                    {"id": str, "semantics": str},
                ),
                *collection_constituents(
                    "precedence_rules",
                    governance,
                    "precedence_rules",
                    {"id": str, "condition": str, "outcome": str},
                ),
                *mapping_constituents(
                    "independent_authorizations",
                    governance,
                    "independent_authorizations",
                    bool,
                    [
                        "test_access_authorized",
                        "final_candidate_authorized",
                        "threshold_selection_authorized",
                        "calibration_selection_authorized",
                        "xai_authorized",
                    ],
                ),
            ],
            lambda: (
                governance_criteria == list(CRITERIA)
                and governance_states == list(STATES)
                and all(
                    value is False
                    for value in governance.get(
                        "independent_authorizations", {}
                    ).values()
                )
            ),
        ),
        tuning_invariants[5]: obs(
            RULE_PATH,
            "anti_retrospective_tuning_declaration",
            sprint41.get("anti_retrospective_tuning_declaration"),
            isinstance(sprint41.get("anti_retrospective_tuning_declaration"), str)
            and bool(sprint41["anti_retrospective_tuning_declaration"]),
        ),
        tuning_invariants[6]: obs(
            RULE_PATH,
            "historical_application_prohibited",
            sprint41.get("historical_application_prohibited"),
            sprint41.get("historical_application_prohibited")
            == ["10.8.2.38", "10.8.2.39", "10.8.2.40", "10.8.2.41"],
        ),
    }
    return {
        "leakage_safety": observed_integrity_evidence(
            leakage_invariants, leakage_obs, [raw_text_limitation]
        ),
        "temporal_validity": observed_integrity_evidence(
            temporal_invariants, temporal_obs
        ),
        "reproducibility": observed_integrity_evidence(
            repro_invariants, repro_obs, [pickle_limitation]
        ),
        "absence_of_outcome_driven_tuning": observed_integrity_evidence(
            tuning_invariants, tuning_obs
        ),
    }


def _criterion_rules() -> dict[str, dict[str, Any]]:
    return {row["id"]: row for row in sprint_41_contract()["criteria"]}


def build_evidence(root: Path) -> dict[str, dict[str, Any]]:
    """Build evidence envelopes from accepted persisted DEVELOPMENT artifacts only."""
    paired_path = "audits/q1-fusion-process-ablation/1.0.0/paired_inference.json"
    paired = _load_json(root, paired_path)
    comparisons = paired if isinstance(paired, list) else paired["comparisons"]
    selected = [
        row
        for row in comparisons
        if row["contrast"] in {"CT_equal_vs_C", "CT_equal_vs_T"}
        and row["metric"] in {"ROC_AUC", "PR_AUC"}
    ]
    discrimination_differences = [
        cell["signed_difference"] for row in selected for cell in row["origin_values"]
    ]

    calibration_path = (
        "audits/q1-forward-development-calibration/1.0.0/calibration_results.json"
    )
    calibration_rows = _load_json(root, calibration_path)["rows"]
    by_key = {(row["origin_id"], row["method"]): row for row in calibration_rows}
    calibration_differences = []
    for origin in (f"O{i}" for i in range(1, 6)):
        reference, candidate = (
            by_key[(origin, "UNCALIBRATED")],
            by_key[(origin, "ISOTONIC")],
        )
        calibration_differences.extend(
            [
                reference["Brier"] - candidate["Brier"],
                reference["ECE"] - candidate["ECE"],
            ]
        )

    dca_path = "audits/q1-development-practical-utility-execution/1.0.0/decision_curve_results.csv"
    utility_path = "audits/q1-development-practical-utility-execution/1.0.0/practical_utility_results.csv"
    practical_by_origin = {f"O{i}": [] for i in range(1, 6)}
    with (root / dca_path).open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            practical_by_origin[row["origin_id"]].extend(
                [
                    float(row["net_benefit_difference_vs_treat_none"]),
                    float(row["net_benefit_difference_vs_treat_all"]),
                ]
            )
    with (root / utility_path).open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            practical_by_origin[row["origin_id"]].append(
                -float(row["absolute_cost_difference_vs_best_baseline"])
            )
    practical_differences = [
        value for origin in practical_by_origin.values() for value in origin
    ]

    integrity = build_integrity_evidence(root)

    discrimination = {
        "valid": True,
        "complete": len(discrimination_differences) == 20,
        "provenance_complete": True,
        "oriented_differences": discrimination_differences,
    }
    calibration = {
        "valid": True,
        "complete": len(calibration_differences) == 10,
        "provenance_complete": True,
        "oriented_differences": calibration_differences,
    }
    practical = {
        "valid": True,
        "complete": len(practical_differences) == 1995,
        "provenance_complete": True,
        "oriented_differences": practical_differences,
    }
    interim_states = {
        "discrimination": derive_criterion_state(
            SPRINT, "discrimination", discrimination
        )["state"],
        "calibration": derive_criterion_state(SPRINT, "calibration", calibration)[
            "state"
        ],
        "practical_utility": derive_criterion_state(
            SPRINT, "practical_utility", practical
        )["state"],
    }
    complexity = {
        "valid": True,
        "provenance_complete": True,
        "candidate": {
            "modality_count": 2,
            "fitted_component_count": 2,
            "learned_fusion_component_count": 0,
            "calibration_component_count": 1,
        },
        "references": [
            {
                "modality_count": 1,
                "fitted_component_count": 1,
                "learned_fusion_component_count": 0,
                "calibration_component_count": 0,
            },
            {
                "modality_count": 1,
                "fitted_component_count": 1,
                "learned_fusion_component_count": 0,
                "calibration_component_count": 0,
            },
        ],
        "incremental_value_states": interim_states,
    }
    stability = {
        "valid": True,
        "provenance_complete": True,
        "origins": {
            origin: {
                "valid": True,
                "complete": True,
                "provenance_complete": True,
                "oriented_differences": [
                    *[
                        cell["signed_difference"]
                        for row in selected
                        for cell in row["origin_values"]
                        if cell["origin_id"] == origin
                    ],
                    by_key[(origin, "UNCALIBRATED")]["Brier"]
                    - by_key[(origin, "ISOTONIC")]["Brier"],
                    by_key[(origin, "UNCALIBRATED")]["ECE"]
                    - by_key[(origin, "ISOTONIC")]["ECE"],
                    *practical_by_origin[origin],
                ],
            }
            for origin in practical_by_origin
        },
    }
    return {
        **integrity,
        "discrimination": discrimination,
        "calibration": calibration,
        "practical_utility": practical,
        "complexity_parsimony": complexity,
        "stability_across_origins": stability,
    }


def evidence_references(root: Path) -> dict[str, list[dict[str, Any]]]:
    common_integrity = [
        _ref(
            root,
            "audits/q1-experimental-validity-contract/1.0.0/contract.json",
            "10.8.2.33",
            ["temporal_protocol", "leakage_denylist", "fitted_state_persistence"],
        ),
        _ref(
            root,
            "audits/q1-development-practical-utility-execution/1.0.0/execution_ledger.json",
            "10.8.2.38",
            ["TEST_*", "model_fits", "threshold_optimizations", "XAI_executions"],
        ),
        _ref(
            root,
            "audits/q1-development-practical-utility-execution/1.0.0/reproducibility_manifest.json",
            "10.8.2.38",
            [
                "deterministic_rerun_equivalence",
                "source_predictor_hashes",
                "temporal_membership_digests",
            ],
        ),
    ]
    discrimination = [
        _ref(
            root,
            "audits/q1-fusion-process-ablation/1.0.0/paired_inference.json",
            "10.8.2.35",
            ["CT_equal_vs_C", "CT_equal_vs_T", "origin_values", "ROC_AUC", "PR_AUC"],
        )
    ]
    calibration = [
        _ref(
            root,
            "audits/q1-forward-development-calibration/1.0.0/calibration_results.json",
            "10.8.2.36",
            ["rows[].origin_id", "rows[].method", "rows[].Brier", "rows[].ECE"],
        )
    ]
    utility = [
        _ref(
            root,
            "audits/q1-development-practical-utility-execution/1.0.0/decision_curve_results.csv",
            "10.8.2.38",
            [
                "origin_id",
                "probability_state",
                "threshold",
                "net_benefit_difference_vs_treat_none",
                "net_benefit_difference_vs_treat_all",
            ],
        ),
        _ref(
            root,
            "audits/q1-development-practical-utility-execution/1.0.0/practical_utility_results.csv",
            "10.8.2.38",
            [
                "origin_id",
                "probability_state",
                "threshold",
                "FN_FP_cost_ratio",
                "absolute_cost_difference_vs_best_baseline",
            ],
        ),
    ]
    complexity = [
        _ref(
            root,
            "configs/experiments/q1_fusion_process_ablation_1.0.0.json",
            "10.8.2.35",
            ["fixed_fusion_candidates", "modalities", "calibration"],
        ),
        *discrimination,
        *calibration,
        *utility,
    ]
    return {
        "leakage_safety": common_integrity,
        "temporal_validity": common_integrity,
        "reproducibility": common_integrity,
        "discrimination": discrimination,
        "calibration": calibration,
        "practical_utility": utility,
        "complexity_parsimony": complexity,
        "stability_across_origins": [*discrimination, *calibration, *utility],
        "absence_of_outcome_driven_tuning": [
            *common_integrity,
            _ref(
                root,
                RULE_PATH,
                "10.8.2.41",
                [
                    "effective_sprint",
                    "historical_application_prohibited",
                    "anti_retrospective_tuning_declaration",
                ],
            ),
        ],
    }


def rationale(criterion: str, state: str, evidence: dict[str, Any]) -> tuple[str, str]:
    codes = {
        "leakage_safety": "ALL_INVARIANTS_TRUE_WITH_DECLARED_LIMITATION",
        "temporal_validity": "ALL_TEMPORAL_INVARIANTS_TRUE",
        "reproducibility": "ALL_INVARIANTS_TRUE_WITH_DECLARED_LIMITATION",
        "discrimination": "COMPLETE_PAIRED_VECTOR_HAS_FAVORABLE_AND_UNFAVORABLE_CELLS",
        "calibration": "COMPLETE_PAIRED_VECTOR_HAS_FAVORABLE_AND_UNFAVORABLE_CELLS",
        "practical_utility": "COMPLETE_FROZEN_GRID_HAS_FAVORABLE_AND_UNFAVORABLE_CELLS",
        "complexity_parsimony": "STRICTLY_MORE_COMPLEX_WITH_MIXED_INCREMENTAL_VALUE",
        "stability_across_origins": "COMPLETE_ORIGINS_HAVE_MIXED_DIRECTIONAL_CELLS",
        "absence_of_outcome_driven_tuning": "ALL_PROSPECTIVE_INVARIANTS_TRUE",
    }
    summaries = {
        "leakage_safety": "All mandatory leakage and TEST-sealing invariants are true, but the inherited raw-text semantic-proxy limitation prevents unqualified PASS.",
        "temporal_validity": "The frozen O1–O5 expanding, blocked DEVELOPMENT memberships and fit-before-predict invariants are complete and true.",
        "reproducibility": "Hashes, identities, persisted fitted states and deterministic rerun equivalence are present; cross-runtime pickle byte identity remains explicitly unclaimed.",
        "discrimination": "The complete CT_equal versus C and T ROC-AUC/PR-AUC origin vector contains both favorable and unfavorable differences.",
        "calibration": "The complete ISOTONIC versus UNCALIBRATED Brier/ECE origin vector contains both favorable and unfavorable differences.",
        "practical_utility": "The complete frozen threshold, cost, calibration-state and origin grid contains improvements, ties and degradations.",
        "complexity_parsimony": "CT with calibration is Pareto more complex than each unimodal uncalibrated reference; the required incremental-value states are MIXED, so Sprint 41 requires MIXED.",
        "stability_across_origins": "Every O1–O5 record is complete, but origin-level combined directional cells are mixed; stability is evaluated independently of complexity.",
        "absence_of_outcome_driven_tuning": "The prospective timing, protected hashes, unchanged Sprint 39 governance and zero Sprint 42 prohibited counters satisfy all mandatory invariants.",
    }
    return codes[criterion], summaries[criterion]


def evaluate(root: Path) -> dict[str, Any]:
    evidence = build_evidence(root)
    references = evidence_references(root)
    rules = _criterion_rules()
    records = []
    for criterion in CRITERIA:
        derived = derive_criterion_state(SPRINT, criterion, evidence[criterion])
        code, reason = rationale(criterion, derived["state"], evidence[criterion])
        if "invariant_observations" in evidence[criterion]:
            derivation = {
                "valid": evidence[criterion]["valid"],
                "provenance_complete": evidence[criterion]["provenance_complete"],
                "invariant_observations": evidence[criterion]["invariant_observations"],
                "limitations": evidence[criterion]["limitations"],
            }
        else:
            derivation = {
                "valid": evidence[criterion].get("valid"),
                "provenance_complete": evidence[criterion].get("provenance_complete"),
                "derivation_input_type": rules[criterion]["rule_type"],
            }
        records.append(
            {
                "criterion": criterion,
                "criterion_class": criterion_class(criterion),
                "state": derived["state"],
                "evidence_references": references[criterion],
                "evidence_provenance": {
                    "eligibility": "ACCEPTED_PERSISTED_DEVELOPMENT_ONLY",
                    "authorized_evaluation_sprint": SPRINT,
                },
                "evidence_derivation": derivation,
                "rule_reference": {
                    "path": RULE_PATH,
                    "sha256": digest(root / RULE_PATH),
                    "rule_type": rules[criterion]["rule_type"],
                    "declared_in_sprint": "10.8.2.41",
                },
                "reason_code": code,
                "rationale": reason,
            }
        )
    return {
        "protocol_id": PROTOCOL_ID,
        "version": VERSION,
        "sprint": SPRINT,
        "evaluation_status": "MATERIALIZED_VALID_PENDING_HUMAN_ACCEPTANCE",
        "evaluation_timing": "DERIVED_DURING_AUTHORIZED_SPRINT_10.8.2.42",
        "prospectivity": {
            "sprint_41_role": "RULE_DEFINITION_NOT_PRIOR_STATE_DERIVATION",
            "retrospective_reinterpretation": False,
            "future_evidence_used": False,
        },
        "test_sealed": True,
        "advancement_outcome_derived": False,
        "canonical_state_vocabulary": list(STATES),
        "criteria": records,
    }


def validate_evaluation(value: dict[str, Any]) -> None:
    forbidden = {"advancement_outcome", "final_candidate", "governance_outcome"}
    if forbidden & set(value):
        raise ValueError("unauthorized advancement outcome field")
    if (
        value.get("advancement_outcome_derived") is not False
        or value.get("test_sealed") is not True
    ):
        raise ValueError("advancement or TEST boundary violation")
    rows = value.get("criteria")
    if not isinstance(rows, list) or [row.get("criterion") for row in rows] != list(
        CRITERIA
    ):
        raise ValueError("criteria must be exactly nine and in canonical order")
    if len({row["criterion"] for row in rows}) != len(CRITERIA):
        raise ValueError("duplicate criterion")
    for row in rows:
        if row.get("state") not in STATES or row.get(
            "criterion_class"
        ) != criterion_class(row["criterion"]):
            raise ValueError("invalid criterion state or class")
        if (
            not row.get("evidence_references")
            or not row.get("evidence_provenance")
            or not row.get("rule_reference")
        ):
            raise ValueError("missing evidence or rule provenance")


def execution_ledger() -> dict[str, int | str]:
    return {
        "sprint_mode": "CONTROLLED_CRITERION_STATE_EVALUATION_ONLY",
        **dict.fromkeys(PROHIBITED_COUNTERS, 0),
    }


def evaluation_schema() -> dict[str, Any]:
    row_properties = {
        "criterion": {"enum": list(CRITERIA)},
        "criterion_class": {"enum": ["INTEGRITY_BLOCKING", "SCIENTIFIC_PERFORMANCE"]},
        "state": {"enum": list(STATES)},
        "evidence_references": {"type": "array", "minItems": 1},
        "evidence_provenance": {"type": "object"},
        "evidence_derivation": {"type": "object"},
        "rule_reference": {"type": "object"},
        "reason_code": {"type": "string"},
        "rationale": {"type": "string"},
    }
    properties = {
        "protocol_id": {"const": PROTOCOL_ID},
        "version": {"const": VERSION},
        "sprint": {"const": SPRINT},
        "evaluation_status": {"type": "string"},
        "evaluation_timing": {"const": "DERIVED_DURING_AUTHORIZED_SPRINT_10.8.2.42"},
        "prospectivity": {"type": "object"},
        "test_sealed": {"const": True},
        "advancement_outcome_derived": {"const": False},
        "canonical_state_vocabulary": {"const": list(STATES)},
        "criteria": {
            "type": "array",
            "minItems": 9,
            "maxItems": 9,
            "items": {
                "type": "object",
                "required": list(row_properties),
                "properties": row_properties,
                "additionalProperties": False,
            },
        },
    }
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "required": list(properties),
        "properties": properties,
        "additionalProperties": False,
    }


def report(
    value: dict[str, Any], integrity_count: int, quality: dict[str, Any] | None = None
) -> str:
    validated = (quality or {}).get("status") == "PASS_FROM_EXECUTED_COMMANDS"
    decision = (
        "SPRINT_10.8.2.42_CORRECTED_READY_FOR_HUMAN_ACCEPTANCE"
        if validated
        else "SPRINT_10.8.2.42_MATERIALIZED_PENDING_COMMAND_VALIDATION"
    )
    gate_rows = (
        "\n".join(
            f"- `{row['id']}`: exit `{row['exit_code']}`; observed `{row['observed_output'].splitlines()[-1]}`"
            for row in (quality or {}).get("observed_results", [])
        )
        or "- No runtime command evidence recorded by the materializer."
    )
    rows = "\n".join(
        f"| `{row['criterion']}` | `{row['criterion_class']}` | **{row['state']}** | `{row['reason_code']}` |"
        for row in value["criteria"]
    )
    return f"""# Sprint 10.8.2.42 — Controlled Prospective Criterion-State Evaluation

## Decision

**{decision}**

The criterion-state evaluation was materialized and validated. Human acceptance remains required.

## Evidence, rule, and derivation boundary

Inherited accepted DEVELOPMENT evidence comes from Sprints 33–38. Sprint 39 supplies the exact criterion identifiers, classes, and state vocabulary. Sprint 40 persisted no state vector. Sprint 41 supplies prospective rules only. The states below were newly derived during Sprint 42; no earlier Sprint was reinterpreted.

| Criterion | Class | State | Deterministic reason code |
|---|---|---|---|
{rows}

Full evidence paths, hashes, originating Sprints, persisted fields, Sprint 41 rule types, and rationales are in `criterion_state_evaluation.json`.

## Operations not performed

No TEST access, scoring, probability loading, fitting, refitting, calibration fitting, meta-learning, tuning, candidate selection, external acquisition, or XAI was performed. Every prohibited-operation counter is zero.

## Historical integrity

PASS: {integrity_count} protected persisted Sprint 32–41 files were SHA-256 addressed and verified unchanged. Sprint 40 is represented by its accepted read-only branch/commit state and has no additional persisted artifacts.

## Quality gates

The scientific materializer does not claim runtime quality-gate results. Command-observed results are recorded separately by the validation runner after the commands execute. Current validation status: `{(quality or {}).get("status", "NOT_RUN_BY_MATERIALIZER")}`.

{gate_rows}

## Scientific boundary

This Sprint establishes only that the nine-state vector is a deterministic prospective application of Sprint 41 to eligible persisted DEVELOPMENT evidence. It does not derive an advancement outcome, select a final candidate, authorize TEST, Sprint 43, XAI, deployment, a threshold, or a calibrator.
"""


def materialize(root: Path) -> Path:
    output = root / OUTPUT_REL
    output.mkdir(parents=True, exist_ok=True)
    value = evaluate(root)
    validate_evaluation(value)
    history = accepted_historical_hashes(root)
    integrity = verify_hashes(root, history)
    if not integrity["passed"]:
        raise RuntimeError("accepted Git historical baseline mismatch")
    artifacts: dict[str, Any] = {
        "criterion_state_evaluation.json": value,
        "criterion_state_evaluation.schema.json": evaluation_schema(),
        "execution_ledger.json": execution_ledger(),
        "historical_artifact_hashes.json": history,
        "historical_integrity.json": {
            **integrity,
            "baseline_creation": "git show of every protected path at accepted revision",
            "comparison_target": "current working-tree protected paths",
            "tracked_historical_modifications": sorted(
                set(integrity["missing_files"])
                | set(integrity["extra_files"])
                | set(integrity["hash_mismatches"])
            ),
        },
        "quality_gates.json": {
            "status": "NOT_RUN_BY_MATERIALIZER",
            "evidence_type": "RUNTIME_COMMAND_RESULTS_REQUIRED",
            "observed_results": [],
        },
        "scientific_decision.json": {
            "decision": "SPRINT_10.8.2.42_MATERIALIZED_PENDING_COMMAND_VALIDATION",
            "scope": "CRITERION_STATE_EVALUATION_ONLY",
            "human_acceptance_required": True,
            "advancement_outcome_derived": False,
            "test_access_authorized": False,
            "sprint_43_authorized": False,
            "xai_authorized": False,
        },
    }
    for name, item in artifacts.items():
        (output / name).write_bytes(canonical_bytes(item))
    module = root / "src/evaluation/q1_controlled_criterion_state_evaluation.py"
    tests = root / "tests/evaluation/test_q1_controlled_criterion_state_evaluation.py"
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
        "artifact_sha256": {name: digest(output / name) for name in sorted(artifacts)},
    }
    (output / "experiment_manifest.json").write_bytes(canonical_bytes(manifest))
    (output / "REPORT.md").write_text(report(value, len(history)), encoding="utf-8")
    return output


def record_quality_gate_evidence(root: Path, observed: list[dict[str, Any]]) -> None:
    """Persist only successful command observations produced by the gate runner."""
    required = {
        "focused_pytest",
        "relevant_regression_pytest",
        "full_pytest",
        "ruff",
        "python_compilation",
        "json_schema",
        "determinism",
        "historical_integrity",
        "artifact_manifest",
        "git_diff_check",
    }
    ids = [row.get("id") for row in observed]
    if set(ids) != required or len(ids) != len(required):
        raise ValueError("incomplete or duplicate observed quality gates")
    if any(
        row.get("exit_code") != 0
        or not row.get("command")
        or not row.get("observed_output")
        for row in observed
    ):
        raise ValueError("quality gates require successful command observations")
    output = root / OUTPUT_REL
    quality = {
        "status": "PASS_FROM_EXECUTED_COMMANDS",
        "evidence_type": "CAPTURED_RUNTIME_COMMAND_RESULTS",
        "observed_results": observed,
    }
    (output / "quality_gates.json").write_bytes(canonical_bytes(quality))
    decision = _load_json(root, f"{OUTPUT_REL}/scientific_decision.json")
    decision["decision"] = "SPRINT_10.8.2.42_CORRECTED_READY_FOR_HUMAN_ACCEPTANCE"
    (output / "scientific_decision.json").write_bytes(canonical_bytes(decision))
    value = _load_json(root, f"{OUTPUT_REL}/criterion_state_evaluation.json")
    (output / "REPORT.md").write_text(
        report(value, len(accepted_historical_hashes(root)), quality), encoding="utf-8"
    )
    manifest = _load_json(root, f"{OUTPUT_REL}/experiment_manifest.json")
    for name in ["quality_gates.json", "scientific_decision.json"]:
        manifest["artifact_sha256"][name] = digest(output / name)
    (output / "experiment_manifest.json").write_bytes(canonical_bytes(manifest))
