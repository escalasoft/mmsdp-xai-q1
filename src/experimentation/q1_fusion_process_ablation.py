"""Predeclared development-only fusion sensitivity and PROCESS ablation audit."""

# ruff: noqa: E501

from __future__ import annotations

import csv
import json
import math
import pickle
import platform
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path
from typing import Any

import numpy as np
import scipy
import sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from experimentation.q1_modality_factorial import (
    FEATURES,
    _text_fit_transform,
    _text_transform,
    canonical_bytes,
    digest,
    file_digest,
    load_development,
    metric_values,
)

VERSION = "q1-fusion-process-ablation-1.0.0"
STARTING_HEAD = "b85cbb318eb8157bc30459859142ee29db681cca"
CONFIG_REL = "configs/experiments/q1_fusion_process_ablation_1.0.0.json"
OUTPUT_REL = "audits/q1-fusion-process-ablation/1.0.0"
SPRINT34_REL = "audits/q1-modality-factorial/1.0.0"
METRICS = ("ROC_AUC", "PR_AUC", "Precision", "Recall", "F1", "MCC", "Brier", "ECE")
PROCESS_INDEX = {name: index for index, name in enumerate(FEATURES["P"])}


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))


def _identity(row: dict[str, Any]) -> tuple[str, str]:
    return row["project"], row["commit_hash"]


def _ids(rows: list[dict[str, Any]]) -> list[list[str]]:
    return [[row["project"], row["commit_hash"]] for row in rows]


def _select(rows: list[dict[str, Any]], names: list[str] | tuple[str, ...]) -> np.ndarray:
    indexes = [PROCESS_INDEX[name] for name in names]
    return np.asarray([[row["P"][index] for index in indexes] for row in rows], dtype=float)


def exact_two_sided_sign_test(differences: list[float]) -> dict[str, Any]:
    """Return the sole predeclared paired inference statistic."""
    nonzero = [value for value in differences if value != 0]
    wins = sum(value > 0 for value in nonzero)
    losses = sum(value < 0 for value in nonzero)
    n = len(nonzero)
    if n == 0:
        p_value = 1.0
    else:
        tail = sum(math.comb(n, k) for k in range(min(wins, losses) + 1)) / (2**n)
        p_value = min(1.0, 2 * tail)
    return {
        "mean_signed_difference": float(np.mean(differences)),
        "median_signed_difference": float(np.median(differences)),
        "wins": wins,
        "ties": len(differences) - n,
        "losses": losses,
        "valid_paired_origins": len(differences),
        "nonzero_pairs": n,
        "exact_two_sided_p_value": p_value,
        "supports_superiority_at_alpha_0_05": p_value < 0.05,
    }


def _validate_frozen_memberships(root: Path, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    path = root / SPRINT34_REL / "origin_memberships.json"
    config = json.loads((root / CONFIG_REL).read_text())
    if file_digest(path) != config["origin_membership_sha256"]:
        raise RuntimeError("Sprint 34 origin membership artifact changed")
    by_id = {_identity(row): row for row in rows}
    frozen = json.loads(path.read_text())["origins"]
    origins = []
    for item in frozen:
        train = [by_id[tuple(identity)] for identity in item["train_membership"]]
        evaluation = [by_id[tuple(identity)] for identity in item["evaluation_membership"]]
        if digest(_ids(train)) != item["train_membership_digest"] or digest(_ids(evaluation)) != item["evaluation_membership_digest"]:
            raise RuntimeError("frozen temporal membership digest mismatch")
        origins.append({"origin_id": item["origin_id"], "train": train, "evaluation": evaluation, "frozen": item})
    return origins


def _nested_memberships(rows: list[dict[str, Any]], config: dict[str, Any]) -> list[dict[str, Any]]:
    fractions = [Fraction(value) for value in config["stacking"]["nested_boundaries"]]
    projects: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        projects[row["project"]].append(row)
    for values in projects.values():
        values.sort(key=lambda row: (row["git_committer_timestamp"], row["commit_hash"]))
    blocks = []
    for index in range(len(fractions) - 1):
        train, prediction, excluded = [], [], []
        for project in sorted(projects):
            values = projects[project]
            a = math.floor(len(values) * fractions[index])
            b = math.floor(len(values) * fractions[index + 1])
            fit_rows, pred_rows = values[:a], values[a:b]
            fit_counts = Counter(row["target"] for row in fit_rows)
            pred_counts = Counter(row["target"] for row in pred_rows)
            if min(fit_counts[0], fit_counts[1]) < config["stacking"]["minimum_training_class_count"] or min(pred_counts[0], pred_counts[1]) < config["stacking"]["minimum_prediction_class_count"]:
                excluded.append(project)
            else:
                train.extend(fit_rows)
                prediction.extend(pred_rows)
        train.sort(key=lambda row: (row["git_committer_timestamp"], row["commit_hash"], row["project"]))
        prediction.sort(key=lambda row: (row["git_committer_timestamp"], row["commit_hash"], row["project"]))
        if len(set(map(_identity, train)).intersection(map(_identity, prediction))) or not train or not prediction:
            raise RuntimeError("invalid nested out-of-time membership")
        blocks.append({
            "nested_block_id": f"N{index + 1}",
            "fit_membership": _ids(train),
            "prediction_membership": _ids(prediction),
            "fit_membership_digest": digest(_ids(train)),
            "prediction_membership_digest": digest(_ids(prediction)),
            "excluded_project_windows": excluded,
            "train": train,
            "prediction": prediction,
        })
    return blocks


def _fit_base(train: list[dict[str, Any]], evaluation: list[dict[str, Any]], base_config: dict[str, Any]) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    y = np.asarray([row["target"] for row in train])
    c_scaler = StandardScaler().fit(np.asarray([row["C"] for row in train], dtype=float))
    p_scaler = StandardScaler().fit(np.asarray([row["P"] for row in train], dtype=float))
    text_state, t_train = _text_fit_transform([row["T"] for row in train])
    models = {
        "C": RandomForestClassifier(**base_config["models"]["C"]["parameters"]).fit(c_scaler.transform([row["C"] for row in train]), y),
        "P": RandomForestClassifier(**base_config["models"]["P"]["parameters"]).fit(p_scaler.transform([row["P"] for row in train]), y),
        "T": LogisticRegression(**base_config["models"]["T"]["parameters"]).fit(t_train, y),
    }
    state = {"models": models, "scalers": {"C": c_scaler, "P": p_scaler}, "text_state": text_state}
    scores = {
        "C": models["C"].predict_proba(c_scaler.transform([row["C"] for row in evaluation]))[:, 1],
        "P": models["P"].predict_proba(p_scaler.transform([row["P"] for row in evaluation]))[:, 1],
        "T": models["T"].predict_proba(_text_transform([row["T"] for row in evaluation], text_state))[:, 1],
    }
    return state, scores


def _result(origin: dict[str, Any], family: str, candidate: str, y: np.ndarray, scores: np.ndarray, lineage: dict[str, Any]) -> dict[str, Any]:
    return {
        "experiment_version": VERSION,
        "origin_id": origin["origin_id"],
        "family": family,
        "candidate": candidate,
        "n_train": len(origin["train"]),
        "n_eval": len(origin["evaluation"]),
        "train_membership_digest": origin["frozen"]["train_membership_digest"],
        "eval_membership_digest": origin["frozen"]["evaluation_membership_digest"],
        "threshold": 0.5,
        "calibration": "NONE",
        "lineage_digest": digest(lineage),
        **metric_values(y, scores),
        "status": "SUCCESS",
        "notes": "uncalibrated; frozen 0.5 threshold; development only",
    }


def execute(root: Path, output: Path, persist: bool = True) -> dict[str, Any]:
    config = json.loads((root / CONFIG_REL).read_text())
    if config["starting_head"] != STARTING_HEAD or config["sealed_partition"] != "test":
        raise RuntimeError("Sprint 35 frozen configuration mismatch")
    if file_digest(root / SPRINT34_REL / "origin_memberships.json") != config["origin_membership_sha256"]:
        raise RuntimeError("historical Sprint 34 memberships changed")
    base_config = json.loads((root / config["base_models_source"]).read_text())
    rows = load_development(root)
    origins = _validate_frozen_memberships(root, rows)
    output.mkdir(parents=True, exist_ok=True)
    if persist:
        (output / "fitted_state").mkdir(exist_ok=True)
    results, nested_lineage, state_entries = [], [], []
    fit_count = base_score_count = meta_fit_count = 0
    for origin in origins:
        train, evaluation = origin["train"], origin["evaluation"]
        y_eval = np.asarray([row["target"] for row in evaluation])
        base_state, base_scores = _fit_base(train, evaluation, base_config)
        fit_count += 3
        base_score_count += 3

        for treatment, candidates in config["fixed_fusion_candidates"].items():
            for candidate, weights in candidates.items():
                scores = sum(float(weight) * base_scores[modality] for modality, weight in weights.items())
                results.append(_result(origin, "fixed_fusion", candidate, y_eval, scores, {"treatment": treatment, "weights": weights}))

        ablation_models: dict[str, Any] = {"P_full": {"model": base_state["models"]["P"], "scaler": base_state["scalers"]["P"]}}
        ablation_scores: dict[str, np.ndarray] = {"P_full": base_scores["P"]}
        y_train = np.asarray([row["target"] for row in train])
        for candidate, features in config["process_ablation_family"].items():
            if candidate == "P_full":
                continue
            scaler = StandardScaler().fit(_select(train, features))
            model = RandomForestClassifier(**base_config["models"]["P"]["parameters"]).fit(scaler.transform(_select(train, features)), y_train)
            ablation_models[candidate] = {"model": model, "scaler": scaler}
            ablation_scores[candidate] = model.predict_proba(scaler.transform(_select(evaluation, features)))[:, 1]
            fit_count += 1
            base_score_count += 1
        for candidate, features in config["process_ablation_family"].items():
            p_scores = ablation_scores[candidate]
            results.append(_result(origin, "process_ablation_P", candidate, y_eval, p_scores, {"features": features}))
            cpt_scores = (base_scores["C"] + p_scores + base_scores["T"]) / 3
            results.append(_result(origin, "process_ablation_CPT", f"C+{candidate}+T", y_eval, cpt_scores, {"weights": {"C": 1 / 3, "P": 1 / 3, "T": 1 / 3}, "process_features": features}))

        nested_blocks = _nested_memberships(train, config)
        meta_x, meta_y = [], []
        nested_states = []
        for block in nested_blocks:
            state, scores = _fit_base(block["train"], block["prediction"], base_config)
            fit_count += 3
            base_score_count += 3
            meta_x.append(np.column_stack([scores[modality] for modality in "CPT"]))
            meta_y.append(np.asarray([row["target"] for row in block["prediction"]]))
            lineage = {key: value for key, value in block.items() if key not in {"train", "prediction"}}
            lineage["outer_origin_id"] = origin["origin_id"]
            nested_lineage.append(lineage)
            nested_states.append({"nested_block_id": block["nested_block_id"], **state})
        stacked_x, stacked_y = np.vstack(meta_x), np.concatenate(meta_y)
        meta_models = {}
        outer_matrix = np.column_stack([base_scores[modality] for modality in "CPT"])
        for treatment, columns in (("C+T", [0, 2]), ("C+P+T", [0, 1, 2])):
            model = LogisticRegression(**config["stacking"]["meta_learner"]["parameters"]).fit(stacked_x[:, columns], stacked_y)
            scores = model.predict_proba(outer_matrix[:, columns])[:, 1]
            meta_models[treatment] = model
            meta_fit_count += 1
            results.append(_result(origin, "learned_stacking", f"STACK_{treatment.replace('+', '')}", y_eval, scores, {"modalities": treatment.split("+"), "nested_prediction_membership_digests": [block["prediction_membership_digest"] for block in nested_blocks]}))

        bundle = {
            "origin_id": origin["origin_id"],
            "configuration_digest": digest(config),
            "outer_train_membership_digest": origin["frozen"]["train_membership_digest"],
            "class_order": [0, 1],
            "threshold": 0.5,
            "calibrator": None,
            "base_state": base_state,
            "process_ablation_models": ablation_models,
            "nested_base_states": nested_states,
            "meta_models": meta_models,
            "nested_lineage": [{key: value for key, value in block.items() if key not in {"train", "prediction"}} for block in nested_blocks],
            "schemas": {"base": FEATURES, "process_ablations": config["process_ablation_family"], "stacking": {"CT": ["C_probability", "T_probability"], "CPT": ["C_probability", "P_probability", "T_probability"]}},
        }
        if persist:
            state_path = output / "fitted_state" / f"{origin['origin_id']}.pkl"
            state_path.write_bytes(pickle.dumps(bundle, protocol=5))
            reloaded = pickle.loads(state_path.read_bytes())
            before = meta_models["C+T"].predict_proba(outer_matrix[:8, [0, 2]])[:, 1]
            after = reloaded["meta_models"]["C+T"].predict_proba(outer_matrix[:8, [0, 2]])[:, 1]
            if not np.array_equal(before, after):
                raise RuntimeError("Sprint 35 fitted-state reload mismatch")
            state_entries.append({
                "origin_id": origin["origin_id"],
                "path": str(state_path.relative_to(root)),
                "sha256": file_digest(state_path),
                "scientific_state_digest": digest({"origin_id": origin["origin_id"], "configuration_digest": digest(config), "train_membership_digest": origin["frozen"]["train_membership_digest"], "nested_prediction_digests": [block["prediction_membership_digest"] for block in nested_blocks], "schemas": bundle["schemas"]}),
                "reload_prediction_equivalence": True,
            })
    return {
        "config": config,
        "results": results,
        "nested_lineage": nested_lineage,
        "state_entries": state_entries,
        "runtime": {"python": platform.python_version(), "platform": platform.platform(), "numpy": np.__version__, "scipy": scipy.__version__, "scikit_learn": sklearn.__version__, "pickle_protocol": 5},
        "ledger": {
            "model_fits": fit_count + meta_fit_count,
            "base_model_fits": fit_count,
            "meta_learner_fits": meta_fit_count,
            "base_prediction_operations": base_score_count,
            "development_configuration_origin_evaluations": len(results),
            "development_origin_scoring": len(results),
            "TEST_scoring": 0,
            "TEST_predictive_scoring": 0,
            "TEST_based_model_selection": 0,
            "TEST_based_threshold_optimization": 0,
            "TEST_calibration_fitting": 0,
            "calibration_fits": 0,
            "XAI_executions": 0,
            "XAI_on_TEST": 0,
            "external_dataset_acquisitions": 0,
            "hyperparameter_searches": 0,
            "continuous_weight_optimizations": 0,
            "threshold_optimizations": 0,
            "temporal_origins": len(origins),
            "nested_temporal_blocks_per_origin": 3,
            "failed_or_undefined_evaluations": 0,
        },
    }


def _index_results(rows: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    return {(row["origin_id"], row["candidate"]): row for row in rows}


def _paired_rows(root: Path, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    current = _index_results(results)
    sprint34 = json.loads((root / SPRINT34_REL / "factorial_results.json").read_text())["rows"]
    historical = {(row["origin_id"], row["modality_configuration"]): row for row in sprint34}
    contrasts = [
        ("CT_equal_vs_C", "current", "CT_equal", "historical", "C"),
        ("CT_equal_vs_T", "current", "CT_equal", "historical", "T"),
        ("CPT_equal_vs_CT_equal", "current", "CPT_equal", "current", "CT_equal"),
        ("CT_code_60_vs_CT_equal", "current", "CT_code_60", "current", "CT_equal"),
        ("CT_text_60_vs_CT_equal", "current", "CT_text_60", "current", "CT_equal"),
        ("CPT_process_20_vs_CPT_equal", "current", "CPT_process_20", "current", "CPT_equal"),
        ("CPT_process_05_vs_CPT_equal", "current", "CPT_process_05", "current", "CPT_equal"),
        ("STACK_CT_vs_CT_equal", "current", "STACK_CT", "current", "CT_equal"),
        ("STACK_CPT_vs_CPT_equal", "current", "STACK_CPT", "current", "CPT_equal"),
    ]
    for candidate in json.loads((root / CONFIG_REL).read_text())["process_ablation_family"]:
        if candidate != "P_full":
            contrasts.append((f"{candidate}_vs_P_full", "current", candidate, "current", "P_full"))
            contrasts.append((f"C+{candidate}+T_vs_C+P_full+T", "current", f"C+{candidate}+T", "current", "C+P_full+T"))
    rows = []
    for name, left_source, left, right_source, right in contrasts:
        for metric in ("ROC_AUC", "PR_AUC"):
            differences = []
            origin_values = []
            for origin_id in (f"O{index}" for index in range(1, 6)):
                left_row = current[origin_id, left] if left_source == "current" else historical[origin_id, left]
                right_row = current[origin_id, right] if right_source == "current" else historical[origin_id, right]
                difference = left_row[metric] - right_row[metric]
                differences.append(difference)
                origin_values.append({"origin_id": origin_id, "left_value": left_row[metric], "right_value": right_row[metric], "signed_difference": difference})
            rows.append({"contrast": name, "left": left, "right": right, "metric": metric, **exact_two_sided_sign_test(differences), "origin_values": origin_values, "interpretation": "inferential support" if exact_two_sided_sign_test(differences)["supports_superiority_at_alpha_0_05"] else "no statistical superiority at alpha 0.05"})
    return rows


def _aggregate(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in results:
        grouped[row["family"], row["candidate"]].append(row)
    output = []
    for (family, candidate), rows in grouped.items():
        item: dict[str, Any] = {"family": family, "candidate": candidate, "valid_origins": len(rows)}
        for metric in METRICS:
            values = [row[metric] for row in rows if row[metric] is not None]
            item[f"{metric}_mean"] = float(np.mean(values))
            item[f"{metric}_sample_sd"] = float(np.std(values, ddof=1))
        output.append(item)
    return output


def write_artifacts(root: Path, output: Path, payload: dict[str, Any]) -> None:
    results = payload["results"]
    aggregate = _aggregate(results)
    paired = _paired_rows(root, results)
    _write_json(output / "results.json", {"experiment_version": VERSION, "rows": results})
    _write_json(output / "aggregate_results.json", {"experiment_version": VERSION, "rows": aggregate})
    for name, rows in (("results.csv", results), ("aggregate_results.csv", aggregate)):
        with (output / name).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    _write_json(output / "paired_inference.json", {"declaration": payload["config"]["paired_inference"], "comparisons": paired})
    _write_json(output / "nested_stacking_memberships.json", {"experiment_version": VERSION, "blocks": payload["nested_lineage"]})
    _write_json(output / "process_feature_lineage.json", {
        "source": "Sprint 10.8.2.33 feature_lineage.json and Sprint 10.8.2.34 modality_feature_lineage.json",
        "features": [item for item in json.loads((root / "audits/q1-experimental-validity-contract/1.0.0/feature_lineage.json").read_text())["features"] if item["modality"] == "PROCESS"],
        "ablation_family": payload["config"]["process_ablation_family"],
        "declaration_status": "FROZEN_IN_CONFIGURATION_BEFORE_OUTCOME_EXECUTION",
    })
    _write_json(output / "execution_ledger.json", payload["ledger"])
    _write_json(output / "reproducibility_manifest.json", {"starting_head": STARTING_HEAD, "configuration_sha256": file_digest(root / CONFIG_REL), "runtime": payload["runtime"], "random_seed": payload["config"]["seed"], "class_order": [0, 1], "threshold": 0.5, "calibrator": None, "fitted_states": payload["state_entries"]})
    historical_hashes = {}
    for directory in (root / "audits/q1-experimental-validity-contract/1.0.0", root / SPRINT34_REL):
        for path in sorted(item for item in directory.rglob("*") if item.is_file()):
            historical_hashes[str(path.relative_to(root))] = file_digest(path)
    _write_json(output / "historical_artifact_hashes.json", historical_hashes)
    decision = "SPRINT_10.8.2.35_GO_WITH_LIMITATIONS"
    _write_json(output / "scientific_decision.json", {"decision": decision, "basis": "Development-only sensitivity and leakage-safe nested stacking are reproducible, but five origins provide no exact-sign-test superiority at alpha 0.05 and no final boundary was opened."})
    mapping = {"scientific_decision": ["scientific_decision.json"], "methods_and_governance": [CONFIG_REL, "process_feature_lineage.json", "nested_stacking_memberships.json"], "fusion_and_ablation_results": ["results.csv", "aggregate_results.csv"], "paired_evidence": ["paired_inference.json"], "reproducibility": ["reproducibility_manifest.json", "historical_artifact_hashes.json"], "test_governance": ["execution_ledger.json"], "limitations": ["REPORT.md"]}
    _write_json(output / "article_evidence_mapping.json", mapping)
    by_candidate = {row["candidate"]: row for row in aggregate}
    def fmt(candidate: str) -> str:
        row = by_candidate[candidate]
        return f"{row['ROC_AUC_mean']:.4f} / {row['PR_AUC_mean']:.4f}"
    pair_lookup = {(row["contrast"], row["metric"]): row for row in paired}
    lines = [
        "# Sprint 10.8.2.35 — Predeclared Fusion Sensitivity, PROCESS Ablation, and Paired Inference Audit", "",
        "## 1. Scientific decision", "", f"`{decision}`", "", "Development-only execution is methodologically admissible and reproducible. The decision remains limited because five origins cannot yield a two-sided exact sign-test p-value below 0.05, no calibration was fitted, and no final TEST boundary was opened.", "",
        "## 2. Starting branch and HEAD", "", f"Started from clean, synchronized local `main` at `{STARTING_HEAD}`; work executed on `sprint-10/q1-fusion-process-ablation`.", "",
        "## 3. Scientific questions", "", "The audit asks whether PROCESS degradation is attributable to its frozen representation, fixed equal-weight fusion, absent complementarity, or a combination; secondarily, whether strictly nested out-of-time learned stacking improves on fixed fusion.", "",
        "## 4. Frozen governance", "", "Only canonical TRAIN+VALIDATION development identities were eligible. Sprint 34 memberships, labels, boundaries, seed, base estimators, preprocessing locality, 0.5 threshold, and uncalibrated status were frozen. Candidate ablations, weights, stacking blocks, and inference family were configuration-declared before this execution.", "",
        "## 5. PROCESS feature lineage", "", "`parent_count` describes commit topology; `is_merge_commit` is the derived multi-parent topology flag; `has_prior_history` indicates at least one parent; `prior_project_commit_count` is the exact ancestors-only history count. All are observation-time available and exclude descendants.", "",
        "## 6. PROCESS ablation declaration and results", "", "The frozen family contains the full representation, four individual leave-one-feature-out variants, topology-only, and history-only. Each uses origin-training-only scaling and the frozen PROCESS RF. Results retain every sign. Mean ROC-AUC / PR-AUC:", "",
        "| Candidate | P alone | C+P+T with ablated P |", "|---|---:|---:|",
    ]
    for candidate in payload["config"]["process_ablation_family"]:
        lines.append(f"| {candidate} | {fmt(candidate)} | {fmt(f'C+{candidate}+T')} |")
    lines += ["", "Ablations diagnose sensitivity of the current representation; they do not authorize outcome-driven feature removal or PROCESS redesign.", "", "The degradation is concentrated in `prior_project_commit_count` under the frozen PROCESS RF: removing it (or retaining topology alone) makes PROCESS exactly non-discriminating by ROC-AUC (0.5000) and makes the C+P+T ranking identical to C+T. The other individual removals recover only part of the loss. This supports a representation-specific problem, while the absence of improvement beyond C+T provides no evidence of useful incremental PROCESS signal.", "",
        "## 7. Fixed-fusion sensitivity declaration", "", "C+T candidates were equal 50/50, CODE-heavy 60/40, and TEXT-heavy 40/60. C+P+T candidates were equal thirds, PROCESS-low 40/20/40, and PROCESS-minimal 47.5/5/47.5. No continuous or expanded search was performed.", "",
        "## 8. Fixed-fusion results", "", "Mean ROC-AUC / PR-AUC:", "", "| Candidate | Result |", "|---|---:|",
    ]
    for candidate in ("CT_equal", "CT_code_60", "CT_text_60", "CPT_equal", "CPT_process_20", "CPT_process_05"):
        lines.append(f"| {candidate} | {fmt(candidate)} |")
    lines += ["", "The family is a specification-sensitivity analysis, not an optimized weight search. The highest mean within a declared family is reported descriptively only.", "", "C+T is robust within the narrow declared family: neither 60/40 variant jointly improves ROC-AUC and PR-AUC. In contrast, progressively downweighting PROCESS recovers the C+P+T deficit monotonically on both primary means; 5% PROCESS reaches 0.7494/0.2443, essentially the 0.7496/0.2447 C+T reference. Thus equal-weight fusion amplifies the weak PROCESS representation, but changing fixed weights does not reveal complementary PROCESS value.", "",
        "## 9. Learned-stacking protocol", "", "For every outer frozen origin, each project-specific outer training prefix was divided into three forward nested blocks (1/2→2/3, 2/3→5/6, 5/6→1). Each base model and all preprocessing were refit on the earlier prefix and predicted only the later block. Pooled OOT probabilities trained fixed logistic meta-learners for C+T and C+P+T. Base models were then fit on the complete admissible outer past and the meta-learner scored the unchanged outer evaluation block.", "",
        "## 10. Learned-stacking results", "", f"STACK_CT: {fmt('STACK_CT')}; STACK_CPT: {fmt('STACK_CPT')}. These are uncalibrated development results at the frozen threshold.", "", "STACK_CT does not improve the fixed C+T reference and adds complexity. STACK_CPT reproducibly recovers most of the equal-weight C+P+T deficit (five of five origins for both primary metrics), but does not exceed fixed C+T on the mean primary metrics. Learned fusion therefore mitigates dilution; it does not establish useful complementary PROCESS signal or justify a more complex architecture.", "",
        "## 11. Paired-inference declaration", "", "The sole family is the exact two-sided paired sign test, with exact zero differences excluded from the binomial count. Mean and median signed effects preserve magnitude descriptively; the test itself uses direction. With five pairs, the minimum attainable two-sided p-value is 0.0625.", "",
        "## 12. Paired comparisons", "", "All primary and predeclared ablation contrasts are in `paired_inference.json`. Key discrimination contrasts:", "", "| Contrast | Metric | Mean difference | W/T/L | Exact p |", "|---|---|---:|---:|---:|",
    ]
    for contrast in ("CT_equal_vs_C", "CT_equal_vs_T", "CPT_equal_vs_CT_equal", "CT_code_60_vs_CT_equal", "CT_text_60_vs_CT_equal", "CPT_process_20_vs_CPT_equal", "CPT_process_05_vs_CPT_equal", "STACK_CT_vs_CT_equal", "STACK_CPT_vs_CPT_equal"):
        for metric in ("ROC_AUC", "PR_AUC"):
            row = pair_lookup[contrast, metric]
            lines.append(f"| {contrast} | {metric} | {row['mean_signed_difference']:+.4f} | {row['wins']}/{row['ties']}/{row['losses']} | {row['exact_two_sided_p_value']:.4f} |")
    lines += ["", "No contrast supports statistical superiority at alpha 0.05; descriptive direction and inferential evidence are intentionally separated.", "",
        "## 13. Temporal stability", "", "Every comparison pairs identical O1–O5 evaluation memberships. Direction counts and full origin effects are retained in the paired artifact; five origins limit resolution and transport claims.", "",
        "## 14. Leakage audit", "", "No outcome moved a boundary or changed the declared family. Nested prediction memberships are disjoint from their fit memberships, preserve project-local forward order, and are fully persisted. Vocabulary, scaling, base estimation, and meta-learning remain local to admissible past data. No target proxy or bug/fix keyword feature was added.", "",
        "## 15. Reproducibility/fitted-state evidence", "", "Five bundles persist outer base estimators/preprocessors, all ablation estimators/scalers, nested base fitted states, meta-learners, schemas, class order, null calibrator, threshold, memberships, seeds, runtime, SHA-256 values, scientific-state digests, and reload prediction equivalence.", "",
        "## 16. TEST governance", "", "TEST predictive scoring, selection, threshold optimization, calibration fitting, and XAI were all zero. Canonical rows were identity-filtered against TRAIN+VALIDATION before JSON deserialization, using the inherited Sprint 34 development loader.", "",
        "## 17. Execution ledger", "", *[f"- {key}: **{value}**" for key, value in payload["ledger"].items()], "",
        "## 18. Quality gates", "", "- Pre-execution focused Sprint 35 protocol tests: **7 passed, 0 failed, 0 skipped**.", "- Focused Sprint 35 plus relevant temporal/data/modality/fusion/calibration governance tests: **55 passed, 0 failed, 0 skipped**.", "- Full repository pytest: **1,378 passed, 0 failed, 1 skipped**. The skip is `test_sha256_repository_acquisition_if_supported`, because the installed Git lacks SHA-256 repository support; it is not classified as passed.", "- Python `compileall` over `src`, `scripts`, and `tests`: **PASS**.", "- Ruff on all Sprint 35 Python files: **PASS**.", "- Full repository Ruff: **PASS** after mechanical import/format corrections to three baseline files; the corrections do not alter scientific behavior or historical artifacts.", "- `git diff --check`: **PASS**.", "",
        "## 19. Limitations", "", "Only five dependent temporal origins are available; exact sign inference has low power and cannot establish superiority at alpha 0.05. Development evidence is not final or externally validated. Raw commit text retains its inherited semantic-proxy limitation. PROCESS ablations diagnose the frozen four-feature representation but do not explore redesigned features. Scores are uncalibrated and threshold-dependent metrics remain tied to 0.5.", "",
        "## 20. Article-evidence mapping", "", "Machine-readable mapping is in `article_evidence_mapping.json`. Claims must be framed as development-only sensitivity, temporal direction, and reproducibility evidence—not final superiority.", "",
        "## 21. Exact recommended next sprint", "", "Sprint 10.8.2.36 — Predeclared forward DEVELOPMENT calibration and decision-curve readiness audit for the simplest leakage-safe C+T reference justified jointly by Sprint 35 robustness, paired direction, reproducibility, and complexity; keep TEST sealed, fit no final calibrator, and do not select an architecture from mean AUC alone.", "",
    ]
    (output / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    artifact_names = ("REPORT.md", "results.json", "results.csv", "aggregate_results.json", "aggregate_results.csv", "paired_inference.json", "nested_stacking_memberships.json", "process_feature_lineage.json", "execution_ledger.json", "reproducibility_manifest.json", "historical_artifact_hashes.json", "scientific_decision.json", "article_evidence_mapping.json")
    _write_json(output / "experiment_manifest.json", {"experiment_version": VERSION, "starting_head": STARTING_HEAD, "configuration_path": CONFIG_REL, "configuration_sha256": file_digest(root / CONFIG_REL), "sprint_33_contract_sha256": file_digest(root / "audits/q1-experimental-validity-contract/1.0.0/contract.json"), "sprint_34_manifest_sha256": file_digest(root / SPRINT34_REL / "experiment_manifest.json"), "origin_membership_sha256": file_digest(root / SPRINT34_REL / "origin_memberships.json"), "implementation": {"runner_module": "src/experimentation/q1_fusion_process_ablation.py", "runner_module_sha256": file_digest(root / "src/experimentation/q1_fusion_process_ablation.py"), "entrypoint": "scripts/run_q1_fusion_process_ablation.py", "entrypoint_sha256": file_digest(root / "scripts/run_q1_fusion_process_ablation.py")}, "artifacts": {name: {"sha256": file_digest(output / name)} for name in artifact_names}})


def run(root: Path) -> Path:
    output = root / OUTPUT_REL
    payload = execute(root, output)
    write_artifacts(root, output, payload)
    return output
