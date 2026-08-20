#!/usr/bin/env python3
"""Execute the TEST-sealed Sprint 10.8.2.30 audit."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from calibration.jit_defects4j_final_refit_audit import (  # noqa: E402
    load_inputs,
    run_audit,
)


def main() -> None:
    config = json.loads(
        (
            ROOT / "configs/experiments/jit_defects4j_final_refit_audit_1.0.0.json"
        ).read_text()
    )
    result = run_audit(ROOT, load_inputs(ROOT), config)
    destination = ROOT / "audits/jit-defects4j-final-refit-audit/1.0.0/audit.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(result["decision"], result["result_digest"])


if __name__ == "__main__":
    main()
