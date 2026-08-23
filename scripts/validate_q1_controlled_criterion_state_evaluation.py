# ruff: noqa: E501
"""Materialize Sprint 42 and capture actual command-level gate evidence."""

import subprocess
from pathlib import Path

from evaluation.q1_controlled_criterion_state_evaluation import (
    materialize,
    record_quality_gate_evidence,
)


def run(root: Path, gate_id: str, command: list[str]) -> dict[str, object]:
    result = subprocess.run(command, cwd=root, text=True, capture_output=True)
    output = (result.stdout + result.stderr).strip()
    if result.returncode:
        raise RuntimeError(f"{gate_id} failed ({result.returncode}):\n{output}")
    return {
        "id": gate_id,
        "command": command,
        "exit_code": result.returncode,
        "observed_output": output[-4000:] or "command completed with exit code 0",
    }


def validate(root: Path) -> None:
    materialize(root)
    python = str(root / ".venv/bin/python")
    pytest = str(root / ".venv/bin/pytest")
    ruff = str(root / ".venv/bin/ruff")
    changed = [
        "src/evaluation/q1_controlled_criterion_state_evaluation.py",
        "scripts/validate_q1_controlled_criterion_state_evaluation.py",
        "tests/evaluation/test_q1_controlled_criterion_state_evaluation.py",
    ]
    regression = [
        "tests/evaluation/test_q1_advancement_governance_protocol.py",
        "tests/evaluation/test_q1_prospective_criterion_operationalization.py",
        "tests/evaluation/test_q1_development_practical_utility_execution.py",
        "tests/evaluation/test_q1_development_practical_utility_protocol.py",
        "tests/calibration/test_q1_forward_development_calibration.py",
        "tests/experimentation/test_q1_fusion_process_ablation.py",
        "tests/experimentation/test_q1_modality_factorial.py",
        "tests/gates/test_q1_experimental_validity_contract.py",
    ]
    python_check = (
        "import hashlib,json; from pathlib import Path; "
        "from evaluation.q1_controlled_criterion_state_evaluation import "
        "accepted_historical_hashes,canonical_bytes,evaluate,verify_hashes; "
        "r=Path('.'); o=r/'audits/q1-controlled-criterion-state-evaluation/1.0.0'; "
        "assert canonical_bytes(evaluate(r))==(o/'criterion_state_evaluation.json').read_bytes()"
    )
    history_check = (
        "from pathlib import Path; from evaluation.q1_controlled_criterion_state_evaluation "
        "import accepted_historical_hashes,verify_hashes; r=Path('.'); "
        "x=verify_hashes(r,accepted_historical_hashes(r)); assert x['passed'],x; print(x)"
    )
    artifact_check = (
        "import hashlib,json; from pathlib import Path; r=Path('.'); "
        "o=r/'audits/q1-controlled-criterion-state-evaluation/1.0.0'; "
        "m=json.loads((o/'experiment_manifest.json').read_text()); "
        "assert all(hashlib.sha256((o/n).read_bytes()).hexdigest()==h "
        "for n,h in m['artifact_sha256'].items()); print(len(m['artifact_sha256']))"
    )
    ajv = "const fs=require('fs'),Ajv=require('ajv');const b='audits/q1-controlled-criterion-state-evaluation/1.0.0/';const s=JSON.parse(fs.readFileSync(b+'criterion_state_evaluation.schema.json'));const d=JSON.parse(fs.readFileSync(b+'criterion_state_evaluation.json'));if(!(new Ajv({allErrors:true})).validate(s,d))process.exit(1);console.log('valid');"
    observed = [
        run(
            root,
            "focused_pytest",
            [
                pytest,
                "-q",
                "tests/evaluation/test_q1_controlled_criterion_state_evaluation.py",
            ],
        ),
        run(root, "relevant_regression_pytest", [pytest, "-q", *regression]),
        run(root, "full_pytest", [pytest, "-q"]),
        run(root, "ruff", [ruff, "check", *changed]),
        run(root, "python_compilation", [python, "-m", "py_compile", *changed]),
        run(root, "json_schema", ["node", "-e", ajv]),
        run(root, "determinism", [python, "-c", python_check]),
        run(root, "historical_integrity", [python, "-c", history_check]),
        run(root, "artifact_manifest", [python, "-c", artifact_check]),
        run(root, "git_diff_check", ["git", "diff", "--check"]),
    ]
    record_quality_gate_evidence(root, observed)
    for item in observed:
        print(f"{item['id']}: {item['observed_output'].splitlines()[-1]}")


if __name__ == "__main__":
    validate(Path(__file__).resolve().parents[1])
