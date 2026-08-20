#!/usr/bin/env python3
"""Run the Sprint 10.8.2.31A post-TEST reconstruction audit."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from evaluation.jit_defects4j_frozen_predictor_reconstruction_audit import (  # noqa: E402
    load_configuration,
    run_audit,
)


def main() -> None:
    result = run_audit(ROOT, load_configuration(ROOT))
    destination = ROOT / (
        "audits/jit-defects4j-frozen-predictor-reconstruction-audit/"
        "1.0.0/audit.json"
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(result["scientific_decision"], result["result_digest"])


if __name__ == "__main__":
    main()
