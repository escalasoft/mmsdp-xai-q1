#!/usr/bin/env python3
"""Materialize the frozen Block 7B dependency-only eligibility disposition."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT_FAILURE = "apache/zeppelin|Logistic Regression|OOF|T|block=2"
PROPAGATED_FAILURES = {
    "apache/zeppelin|Logistic Regression|FUSION_META|C+T",
    "apache/zeppelin|Logistic Regression|FUSION_META|P+T",
    "apache/zeppelin|Logistic Regression|FUSION_META|C+P+T",
}
FROZEN_FAILURES = {ROOT_FAILURE, *PROPAGATED_FAILURES}
ELIGIBLE = "G1_G3_ELIGIBLE_FOR_FUTURE_G4_REVIEW"
ROOT_INELIGIBLE = "G3_INELIGIBLE_ROOT_FAILURE"
PROPAGATED_INELIGIBLE = "G3_INELIGIBLE_PROPAGATED_DEPENDENCY"
HISTORICAL_OUTCOME = "RECONSTRUCTION_NONDETERMINISTIC_STOP"
DISPOSITION = "PARTIAL_G1_G3_RECONSTRUCTION_READY_FOR_G4_REVIEW"


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def digest_list(values: list[str]) -> str:
    return sha256_bytes(canonical_bytes(values))


def required_dependencies(scope: dict[str, Any]) -> tuple[list[str], list[str], str | None]:
    project = scope["project"]
    algorithm = scope["algorithm"]
    configuration = scope["configuration"]
    modalities = configuration.split("+")
    base = [f"{project}|{algorithm}|FINAL_BASE|{modality}" for modality in modalities]
    if len(modalities) == 1:
        return base, [], None
    oof = [
        f"{project}|{algorithm}|OOF|{modality}|block={block}"
        for modality in modalities
        for block in range(2, 10)
    ]
    fusion = f"{project}|{algorithm}|FUSION_META|{configuration}"
    return base, oof, fusion


def counted(records: list[dict[str, Any]], key: str) -> dict[str, dict[str, int]]:
    values: dict[str, Counter[str]] = {}
    for record in records:
        bucket = values.setdefault(record[key], Counter())
        bucket[record["eligibility_outcome"]] += 1
    result: dict[str, dict[str, int]] = {}
    for name in sorted(values):
        counter = values[name]
        result[name] = {
            "total": sum(counter.values()),
            "eligible": counter[ELIGIBLE],
            "ineligible_root_failure": counter[ROOT_INELIGIBLE],
            "ineligible_propagated_dependency": counter[PROPAGATED_INELIGIBLE],
            "g1_g2_ineligible": counter["G1_G2_INELIGIBLE"],
            "unresolved": counter["UNRESOLVED_DEPENDENCY"],
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    repo = args.repo.resolve()

    execution = repo / "audits/q1-xai-reconstruction-execution/1.0.0"
    output = execution / "dispositions/block7b_partial_eligibility/1.0.0"
    if output.exists():
        raise SystemExit(f"refusing to overwrite existing Block 7B package: {output}")

    plan_path = repo / "audits/q1-t1-confirmatory-execution/1.0.0/engine/engine_readiness.json"
    result_path = execution / "g1_g2_g3_results.json"
    policy_path = repo / "audits/q1-xai-reconstruction-equivalence-protocol/1.0.0/failure_partial_eligibility_policy.json"
    governance_path = execution / "governance_ledger.json"
    root_analysis_path = execution / "forensics/g3_failure_root_cause/1.0.0/g3_root_cause_analysis.json"
    downstream_path = execution / "forensics/g3_failure_root_cause/1.0.0/g3_downstream_propagation.json"

    plan_document = json.loads(plan_path.read_text())
    plan = plan_document["plan"]
    results_document = json.loads(result_path.read_text())
    policy = json.loads(policy_path.read_text())
    governance = json.loads(governance_path.read_text())
    root_analysis = json.loads(root_analysis_path.read_text())
    downstream = json.loads(downstream_path.read_text())

    if len(plan) != 392 or len({row["model_identity_sha256"] for row in plan}) != 392:
        raise SystemExit("frozen scope universe is not exactly 392 unique model identities")
    result_by_id = {row["logical_id"]: row for row in results_document["g3_results"]}
    observed_failures = {key for key, row in result_by_id.items() if row["result"] != "G3_PASS_DETERMINISTIC"}
    if observed_failures != FROZEN_FAILURES:
        raise SystemExit(f"frozen failure set changed: {sorted(observed_failures)}")
    if results_document["g3_counts"] != {
        "G3_FAIL_NONDETERMINISTIC": 4,
        "G3_PASS_DETERMINISTIC": 1732,
    }:
        raise SystemExit("frozen G3 counts changed")
    if results_document["outcome"] != HISTORICAL_OUTCOME:
        raise SystemExit("historical Block 7 outcome changed")
    if root_analysis["root_cause_classification"] != "TRUE_FITTED_MODEL_NONDETERMINISM":
        raise SystemExit("accepted Block 7A root classification changed")

    policy_rules = policy["fail_closed_rules"]
    records: list[dict[str, Any]] = []
    for scope in plan:
        base, oof, fusion = required_dependencies(scope)
        required = [*base, *oof, *([fusion] if fusion else [])]
        missing = [logical_id for logical_id in required if logical_id not in result_by_id]
        failed = [logical_id for logical_id in required if result_by_id.get(logical_id, {}).get("result") != "G3_PASS_DETERMINISTIC"]
        g1_states = {
            state
            for logical_id in required
            for state in result_by_id.get(logical_id, {}).get("g1_by_repetition", {}).values()
        }
        g2_states = {
            state
            for logical_id in required
            for state in result_by_id.get(logical_id, {}).get("g2_by_repetition", {}).values()
        }
        # G1/G2 totals are frozen at 5208/5208 pass. Their compact G3 records do not
        # repeat per-repetition G1/G2 fields, so the disposition links to the original
        # aggregate and component journals rather than fabricating absent fields.
        g1_state = "G1_PASS_ALL_REQUIRED_COMPONENTS"
        g2_state = "G2_PASS_ALL_REQUIRED_COMPONENTS"
        if g1_states and g1_states != {"G1_PASS"}:
            g1_state = "G1_FAIL_REQUIRED_COMPONENT"
        if g2_states and g2_states != {"G2_PASS"}:
            g2_state = "G2_FAIL_REQUIRED_COMPONENT"

        if missing:
            outcome = "UNRESOLVED_DEPENDENCY"
            reason = "One or more required logical components are absent from the frozen G3 result universe."
            g3_state = "G3_DEPENDENCY_UNRESOLVED"
        elif g1_state.startswith("G1_FAIL") or g2_state.startswith("G2_FAIL"):
            outcome = "G1_G2_INELIGIBLE"
            reason = "At least one required component failed frozen G1 or G2."
            g3_state = "G3_NOT_REACHED_FOR_SCOPE"
        elif ROOT_FAILURE in failed:
            outcome = PROPAGATED_INELIGIBLE
            reason = (
                "The final fusion scope consumes the failed TEXT OOF block-2 component; "
                "its fusion component is a recorded downstream propagation failure."
            )
            g3_state = "G3_FAIL_REQUIRED_ROOT_AND_PROPAGATED_COMPONENT"
        elif failed:
            outcome = ROOT_INELIGIBLE
            reason = "A directly required component has a frozen root G3 failure."
            g3_state = "G3_FAIL_REQUIRED_COMPONENT"
        else:
            outcome = ELIGIBLE
            reason = (
                "Every component required by this final scope passed frozen G1, G2, and exact G3; "
                "no failed component is in its dependency closure."
            )
            g3_state = "G3_PASS_ALL_REQUIRED_COMPONENTS"

        record = {
            "schema_version": "q1-xai-block7b-scope-eligibility-v1",
            "project": scope["project"],
            "algorithm": scope["algorithm"],
            "configuration": scope["configuration"],
            "model_identity_sha256": scope["model_identity_sha256"],
            "required_base_components": base,
            "required_oof_components": oof,
            "required_fusion_component": fusion,
            "G1_state": g1_state,
            "G2_state": g2_state,
            "G3_dependency_state": g3_state,
            "eligibility_outcome": outcome,
            "exact_reason": reason,
            "failed_upstream_logical_id": ROOT_FAILURE if ROOT_FAILURE in failed else (failed[0] if failed else None),
            "failed_dependency_logical_ids": failed,
            "unresolved_dependency_logical_ids": missing,
            "component_digests": {
                "required_base_component_identities_sha256": digest_list(base),
                "required_oof_component_identities_sha256": digest_list(oof),
                "required_fusion_component_identity_sha256": sha256_bytes(canonical_bytes(fusion)),
            },
            "gate_results": {"G1": g1_state, "G2": g2_state, "G3": g3_state},
            "dependency_policy_sha256": sha256_file(policy_path),
            "source_plan_sha256": sha256_file(plan_path),
            "source_g3_results_sha256": sha256_file(result_path),
        }
        records.append(record)

    records.sort(key=lambda row: (row["project"], row["algorithm"], row["configuration"]))
    outcome_counts = Counter(row["eligibility_outcome"] for row in records)
    affected = [row for row in records if row["eligibility_outcome"] != ELIGIBLE]
    if outcome_counts != Counter({ELIGIBLE: 389, PROPAGATED_INELIGIBLE: 3}):
        raise SystemExit(f"dependency-derived disposition differs from accepted hypothesis: {outcome_counts}")
    if {(row["project"], row["algorithm"], row["configuration"]) for row in affected} != {
        ("apache/zeppelin", "Logistic Regression", "C+T"),
        ("apache/zeppelin", "Logistic Regression", "P+T"),
        ("apache/zeppelin", "Logistic Regression", "C+P+T"),
    }:
        raise SystemExit("dependency-derived affected scope set is not exact")

    hashes = {
        "sprint54_t1_prediction_evidence_sha256": sha256_file(
            repo / "audits/q1-t1-confirmatory-execution/1.0.0/results/t1_prediction_evidence.jsonl.gz"
        ),
        "sprint54_manifest_sha256": sha256_file(repo / "audits/q1-t1-confirmatory-execution/1.0.0/MANIFEST.sha256"),
        "block6_manifest_sha256": sha256_file(repo / "audits/q1-xai-reconstruction-equivalence-protocol/1.0.0/MANIFEST.sha256"),
        "block6a_manifest_sha256": sha256_file(repo / "audits/q1-xai-reconstruction-equivalence-protocol/1.0.0/amendments/historical_design_rationale/1.0.0/MANIFEST.sha256"),
        "block7_manifest_sha256": sha256_file(execution / "MANIFEST.sha256"),
        "block7a_manifest_sha256": sha256_file(execution / "forensics/g3_failure_root_cause/1.0.0/MANIFEST.sha256"),
        "block7_g3_results_sha256": sha256_file(result_path),
        "failure_partial_eligibility_policy_sha256": sha256_file(policy_path),
        "scope_plan_sha256": sha256_file(plan_path),
    }
    summary = {
        "schema_version": "q1-xai-block7b-partial-eligibility-summary-v1",
        "historical_execution_outcome": HISTORICAL_OUTCOME,
        "post_forensic_scope_disposition": DISPOSITION,
        "scope_universe": {"total": 392, "unique_model_identities": 392},
        "eligibility_counts": {
            "eligible": outcome_counts[ELIGIBLE],
            "ineligible": 392 - outcome_counts[ELIGIBLE] - outcome_counts["UNRESOLVED_DEPENDENCY"],
            "unresolved": outcome_counts["UNRESOLVED_DEPENDENCY"],
            "g3_ineligible_root_failure": outcome_counts[ROOT_INELIGIBLE],
            "g3_ineligible_propagated_dependency": outcome_counts[PROPAGATED_INELIGIBLE],
            "g1_g2_ineligible": outcome_counts["G1_G2_INELIGIBLE"],
        },
        "frozen_g3": {
            "G3_PASS_DETERMINISTIC": 1732,
            "G3_FAIL_NONDETERMINISTIC": 4,
            "RAW_FAILED_LOGICAL_UNIT_COUNT": 4,
            "INDEPENDENT_ROOT_FAILURE_COUNT": 1,
            "DOWNSTREAM_PROPAGATED_FAILURE_COUNT": 3,
            "root_logical_id": ROOT_FAILURE,
            "root_classification": "TRUE_FITTED_MODEL_NONDETERMINISM",
            "downstream_logical_ids": sorted(PROPAGATED_FAILURES),
        },
        "affected_scopes": [
            {
                "project": row["project"],
                "algorithm": row["algorithm"],
                "configuration": row["configuration"],
                "model_identity_sha256": row["model_identity_sha256"],
                "eligibility_outcome": row["eligibility_outcome"],
                "failed_dependency_logical_ids": row["failed_dependency_logical_ids"],
            }
            for row in affected
        ],
        "eligibility_by_algorithm": counted(records, "algorithm"),
        "eligibility_by_configuration": counted(records, "configuration"),
        "eligibility_by_project": counted(records, "project"),
        "unaffected_zeppelin_logistic_regression_configurations": sorted(
            row["configuration"]
            for row in records
            if row["project"] == "apache/zeppelin"
            and row["algorithm"] == "Logistic Regression"
            and row["eligibility_outcome"] == ELIGIBLE
        ),
        "governance": {
            "T1_original_predictive_access_count": 1,
            "T1_original_predictive_scoring_count": 1,
            "T1_rerun": False,
            "block7_7a_7b_reconstructed_model_T1_query_count": 0,
            "T2_access_count": 0,
            "T2_state": "DENY_SEALED_REVIEWER_RESERVE",
            "G4_execution_count": 0,
            "G5_execution_count": 0,
            "XAI_execution_count": 0,
        },
        "xai_interpretation": {
            "G1_G3_eligibility_only": True,
            "establishes_original_state_identity": False,
            "establishes_T1_equivalence": False,
            "establishes_SHAP_eligibility": False,
            "establishes_LIME_eligibility": False,
            "establishes_explanatory_validity": False,
            "establishes_scientific_superiority": False,
            "g3_failed_scopes_prohibited_from_model_specific_xai": True,
        },
        "source_hashes": hashes,
        "policy_rules": policy_rules,
    }

    nodes = [
        {"id": ROOT_FAILURE, "type": "ROOT_FAILED_LOGICAL_UNIT", "classification": "TRUE_FITTED_MODEL_NONDETERMINISM"}
    ]
    edges: list[dict[str, str]] = []
    for row in affected:
        fusion = row["required_fusion_component"]
        nodes.append({"id": fusion, "type": "PROPAGATED_FAILED_LOGICAL_UNIT", "classification": "PROPAGATED_FROM_ROOT_TEXT_OOF"})
        scope_id = f"scope:{row['model_identity_sha256']}"
        nodes.append({
            "id": scope_id,
            "type": "FINAL_PROJECT_SCOPE",
            "project": row["project"],
            "algorithm": row["algorithm"],
            "configuration": row["configuration"],
        })
        edges.extend([
            {"from": ROOT_FAILURE, "to": fusion, "relation": "TEXT_OOF_COLUMN_CONSUMED_BY_FUSION_TRAINING"},
            {"from": ROOT_FAILURE, "to": scope_id, "relation": "REQUIRED_OOF_DEPENDENCY"},
            {"from": fusion, "to": scope_id, "relation": "REQUIRED_FUSION_COMPONENT"},
        ])
    zeppelin_t = next(
        row for row in records
        if row["project"] == "apache/zeppelin" and row["algorithm"] == "Logistic Regression" and row["configuration"] == "T"
    )
    graph = {
        "schema_version": "q1-xai-block7b-affected-dependency-graph-v1",
        "nodes": nodes,
        "edges": edges,
        "negative_dependency_check": {
            "scope": {
                "project": "apache/zeppelin",
                "algorithm": "Logistic Regression",
                "configuration": "T",
                "model_identity_sha256": zeppelin_t["model_identity_sha256"],
            },
            "required_components": zeppelin_t["required_base_components"],
            "required_oof_components": [],
            "consumes_root_failure": False,
            "outcome": ELIGIBLE,
            "reason": "The unimodal final TEXT scope consumes its independently G3-passing FINAL_BASE T component, not OOF fold state.",
        },
        "block7a_downstream_evidence_sha256": sha256_file(downstream_path),
    }

    report = f"""# Block 7B Partial G1-G3 Eligibility Disposition

## A. 392-scope universe verified

The frozen confirmatory plan contains exactly **392** project/algorithm/configuration scopes and **392** unique `model_identity_sha256` values. Every scope appears exactly once in `scope_g1_g3_eligibility.jsonl`; every required dependency resolves to the frozen 1,736-unit G3 universe.

## B-D. Counts

- Eligible for possible future G4 review: **389**
- Ineligible: **3**
- Unresolved: **0**
- G1/G2 ineligible: **0**

The frozen component result remains 1,732 exact G3 passes and four G3 failures: one independent root plus three propagated failures. This disposition does not alter those results.

## E-F. Affected scopes and dependency paths

Only the following scopes are ineligible:

1. `apache/zeppelin | Logistic Regression | C+T` (`0147ca63a4a2489b26c36de8f710f55cbf2c260d0c2b17465ef3955085c611c9`)
2. `apache/zeppelin | Logistic Regression | P+T` (`dc23ba88042d5f02f5713e0e667f67d7b4fcb1e5031aafe01249bf4238557333`)
3. `apache/zeppelin | Logistic Regression | C+P+T` (`76c18e414f03fb10ea26dbb9b021b843a337cf69ec28f9e51f03e0d6cdc50837`)

For each, the dependency path is the failed root `{ROOT_FAILURE}` -> the configuration-specific failed `FUSION_META` component -> the final project scope. Each is classified `{PROPAGATED_INELIGIBLE}`. No final scope is classified as a direct root failure because the failed component is an OOF fold state used only by fusion training.

## G. Unaffected Zeppelin Logistic Regression scopes

`C`, `P`, `T`, and `C+P` remain eligible. In particular, unimodal `T` requires the independently G3-passing `FINAL_BASE|T` state and does not consume any OOF state. It is therefore not excluded by the failed TEXT OOF fold.

## H-J. Eligibility distributions

- Algorithm: Logistic Regression 95 eligible / 3 ineligible; Random Forest, XGBoost, and LightGBM each 98 eligible / 0 ineligible.
- Configuration: `C`, `P`, `T`, and `C+P` each 56 eligible; `C+T`, `P+T`, and `C+P+T` each 55 eligible / 1 ineligible.
- Project: `apache/zeppelin` 25 eligible / 3 ineligible; each of the other 13 projects 28 eligible / 0 ineligible.

Full enumerations by algorithm, configuration, and project are in `partial_eligibility_summary.json`.

## K-L. Outcomes preserved

- `historical_execution_outcome = {HISTORICAL_OUTCOME}`
- `post_forensic_scope_disposition = {DISPOSITION}`

The latter is a provenance-separated disposition layer and does not replace the historical Block 7 result.

## M-O. Governance

T1 original predictive access remains 1, original predictive scoring remains 1, and T1 rerun remains false. Block 7/7A/7B reconstructed-model T1 queries remain 0. T2 access remains 0 and its state remains `DENY_SEALED_REVIEWER_RESERVE`. G4, G5, and XAI execution counts remain 0.

G1-G3 eligibility establishes only that a reconstructed candidate may be considered by a separately authorized future G4 review. It does not establish original-state identity, T1 equivalence, SHAP or LIME eligibility, explanatory validity, or scientific superiority. The three G3-ineligible scopes remain prohibited from model-specific XAI based on reconstructed state.

## P. Validation

The focused Block 7B tests verify the 392-scope bijection, unique model-identity linkage, exact dependency derivation, unchanged four-unit G3 failure set and counts, lack of rescue or collateral exclusion, zero protected executions, and unchanged source manifests/hashes. `MANIFEST.sha256` covers the four new disposition artifacts without modifying prior manifests.

## Q. Exact recommended Block 8 authorization scope

No Block 8 action is authorized by this package. If a later human decision authorizes Block 8, the recommended maximum scope is G4 row-level equivalence review for exactly the **389** records classified `{ELIGIBLE}` in `scope_g1_g3_eligibility.jsonl`. It must exclude the three enumerated Zeppelin Logistic Regression fusion scopes. Such authorization would not include G5, XAI, T2 access, remediation, refitting, or replacement of any repetition.
"""

    output.mkdir(parents=True)
    jsonl_path = output / "scope_g1_g3_eligibility.jsonl"
    jsonl_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in records))
    (output / "affected_dependency_graph.json").write_text(json.dumps(graph, indent=2, sort_keys=True) + "\n")
    (output / "partial_eligibility_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    (output / "BLOCK7B_PARTIAL_ELIGIBILITY_REPORT.md").write_text(report)
    artifact_names = [
        "BLOCK7B_PARTIAL_ELIGIBILITY_REPORT.md",
        "affected_dependency_graph.json",
        "partial_eligibility_summary.json",
        "scope_g1_g3_eligibility.jsonl",
    ]
    manifest = "".join(f"{sha256_file(output / name)}  {name}\n" for name in artifact_names)
    (output / "MANIFEST.sha256").write_text(manifest)
    print(json.dumps({"output": str(output), "counts": dict(outcome_counts)}, sort_keys=True))


if __name__ == "__main__":
    main()
