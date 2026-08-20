from pathlib import Path

from scripts.audit_q1_experimental_evidence_gap import (
    COLUMNS,
    DECISION,
    MATRIX,
    ROADMAP,
    main,
    validate,
)


def test_contract_is_valid_and_complete():
    validate()
    assert len(MATRIX) >= 15
    assert {r["evidence_id"] for r in MATRIX} == {f"EV-{i:03d}" for i in range(1, 16)}
    assert all(list(r) == COLUMNS for r in MATRIX)
    assert DECISION == "SPRINT_10.8.2.32_GO_WITH_LIMITATIONS"


def test_roadmap_rejects_random_cv_and_preserves_test(tmp_path: Path):
    main(tmp_path)
    audit = tmp_path / "audits/q1-experimental-evidence-gap-audit/1.0.0"
    assert len(list(audit.iterdir())) == 7
    assert all(
        "random" not in " ".join(s["allowed_modifications"]).lower()
        for s in ROADMAP
    )
    governance = (audit / "test_governance.json").read_text()
    assert '"test_predictive_scoring": 0' in governance
    assert "SEALED_HISTORICAL_EVIDENCE" in governance
