import json
from pathlib import Path

from experimentation.q1_modality_factorial import (
    CONTRASTS,
    FEATURES,
    TREATMENTS,
    digest,
    make_origins,
    metric_values,
)


def test_exact_factorial_and_clean_features():
    assert TREATMENTS == ("C", "P", "T", "C+P", "C+T", "P+T", "C+P+T")
    prohibited = {
        "target",
        "bug_confidence",
        "has_bug_keyword",
        "msg_has_bug_kw",
        "split",
        "commit_hash",
        "project",
    }
    assert not prohibited.intersection(
        name for values in FEATURES.values() for name in values
    )


def test_origin_boundaries_are_chronological_and_label_independent():
    rows = []
    for i in range(20):
        rows.append(
            {
                "project": "p",
                "commit_hash": f"{i:040x}",
                "git_committer_timestamp": f"{i:020d} +0000",
                "target": i % 2,
                "split": "train",
                "C": [i] * 6,
                "P": [i] * 4,
                "T": str(i),
            }
        )
    origins = make_origins(rows)
    assert len(origins) == 5
    for origin in origins:
        assert max(
            (r["git_committer_timestamp"], r["commit_hash"]) for r in origin["train"]
        ) < min(
            (r["git_committer_timestamp"], r["commit_hash"])
            for r in origin["evaluation"]
        )


def test_result_and_contrast_contracts():
    assert len(CONTRASTS) == 12
    assert digest({"b": 2, "a": 1}) == digest({"a": 1, "b": 2})
    metrics = metric_values(
        __import__("numpy").array([0, 1]), __import__("numpy").array([0.2, 0.8])
    )
    assert set(metrics) == {
        "ROC_AUC",
        "PR_AUC",
        "Precision",
        "Recall",
        "F1",
        "MCC",
        "Brier",
        "ECE",
    }


def test_generated_artifact_invariants_if_present():
    root = Path(__file__).resolve().parents[2]
    out = root / "audits/q1-modality-factorial/1.0.0"
    if not out.exists():
        return
    rows = json.loads((out / "factorial_results.json").read_text())["rows"]
    assert len(rows) == 35
    by_origin = {}
    for row in rows:
        by_origin.setdefault(row["origin_id"], []).append(row)
    assert all(
        {r["modality_configuration"] for r in group} == set(TREATMENTS)
        for group in by_origin.values()
    )
    assert all(
        len({r["train_membership_digest"] for r in group}) == 1
        for group in by_origin.values()
    )
    assert all(
        len({r["eval_membership_digest"] for r in group}) == 1
        for group in by_origin.values()
    )
    ledger = json.loads((out / "execution_ledger.json").read_text())
    assert (
        ledger["TEST_scoring"]
        == ledger["calibration_fits"]
        == ledger["XAI_executions"]
        == 0
    )
    contrasts = list(
        __import__("csv").DictReader((out / "pairwise_contrasts.csv").open())
    )
    assert any(float(row["signed_difference"]) < 0 for row in contrasts)
    assert all(
        abs(
            float(row["signed_difference"])
            - (float(row["left_value"]) - float(row["right_value"]))
        )
        < 1e-15
        for row in contrasts
    )
    reproducibility = json.loads((out / "reproducibility_manifest.json").read_text())
    assert all(
        len(item["sha256"]) == 64 and item["reload_prediction_equivalence"]
        for item in reproducibility["fitted_states"]
    )
