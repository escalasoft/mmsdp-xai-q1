# ruff: noqa: E501
"""Materialize Sprint 43 and persist actual command observations."""

import subprocess
from pathlib import Path

from evaluation.q1_controlled_advancement_decision import (
    materialize,
    record_quality_gates,
)


def run(
    root: Path, gate_id: str, command: list[str], *, diagnostic: bool = False
) -> dict[str, object]:
    result = subprocess.run(command, cwd=root, text=True, capture_output=True)
    output = (result.stdout + result.stderr).strip()
    if result.returncode and not diagnostic:
        raise RuntimeError(f"{gate_id} failed ({result.returncode}):\n{output}")
    return {
        "id": gate_id,
        "command": command,
        "exit_code": result.returncode,
        "observed_output": output[-5000:] or "command completed with exit code 0",
    }


def validate(root: Path) -> None:
    materialize(root)
    python = str(root / ".venv/bin/python")
    pytest = str(root / ".venv/bin/pytest")
    ruff = str(root / ".venv/bin/ruff")
    changed = [
        "src/evaluation/q1_controlled_advancement_decision.py",
        "scripts/validate_q1_controlled_advancement_decision.py",
        "tests/evaluation/test_q1_controlled_advancement_decision.py",
    ]
    regression = [
        "tests/evaluation/test_q1_advancement_governance_protocol.py",
        "tests/evaluation/test_q1_prospective_criterion_operationalization.py",
        "tests/evaluation/test_q1_controlled_criterion_state_evaluation.py",
    ]
    determinism = "from pathlib import Path; from evaluation.q1_controlled_advancement_decision import canonical_bytes,derive; r=Path('.'); assert canonical_bytes(derive(r))==canonical_bytes(derive(r)); print('deterministic')"
    history = "from pathlib import Path; from evaluation.q1_controlled_advancement_decision import accepted_historical_hashes,verify_historical_integrity; r=Path('.'); x=verify_historical_integrity(r,accepted_historical_hashes(r)); assert x['passed'],x; print(x)"
    manifest = "import hashlib,json; from pathlib import Path; r=Path('.'); o=r/'audits/q1-controlled-advancement-decision/1.0.0'; m=json.loads((o/'experiment_manifest.json').read_text()); assert all(hashlib.sha256((o/n).read_bytes()).hexdigest()==h for n,h in m['artifact_sha256'].items()); print(len(m['artifact_sha256']))"
    schema = "const fs=require('fs'),Ajv=require('ajv');const b='audits/q1-controlled-advancement-decision/1.0.0/';const s=JSON.parse(fs.readFileSync(b+'advancement_decision.schema.json'));const d=JSON.parse(fs.readFileSync(b+'advancement_decision.json'));if(!(new Ajv({allErrors:true})).validate(s,d))process.exit(1);console.log('valid');"
    observed = [
        run(
            root,
            "focused_pytest",
            [
                pytest,
                "-q",
                "tests/evaluation/test_q1_controlled_advancement_decision.py",
            ],
        ),
        run(root, "sprint_39_42_regression", [pytest, "-q", *regression]),
        run(root, "full_pytest", [pytest, "-q"]),
        run(root, "ruff", [ruff, "check", *changed]),
        run(root, "python_compilation", [python, "-m", "py_compile", *changed]),
        run(root, "json_schema", ["node", "-e", schema]),
        run(root, "determinism", [python, "-c", determinism]),
        run(root, "historical_integrity", [python, "-c", history]),
        run(root, "artifact_manifest", [python, "-c", manifest]),
        run(root, "project_quality_gates", ["make", "lint", f"PYTHON={python}"]),
        run(
            root,
            "repository_format_diagnostic",
            ["make", "format-check", f"PYTHON={python}"],
            diagnostic=True,
        ),
        run(root, "git_diff_check", ["git", "diff", "--check"]),
    ]
    record_quality_gates(root, observed)
    for item in observed:
        print(f"{item['id']}: {item['observed_output'].splitlines()[-1]}")


if __name__ == "__main__":
    validate(Path(__file__).resolve().parents[1])
