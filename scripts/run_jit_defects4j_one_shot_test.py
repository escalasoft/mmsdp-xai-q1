#!/usr/bin/env python3
"""Run the sole authorized Sprint 10.8.2.31 predictive TEST evaluation."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from evaluation.jit_defects4j_one_shot_test import (  # noqa: E402
    execute_once,
    load_configuration,
    preflight,
)


def main() -> None:
    configuration = load_configuration(ROOT)
    # Sprint files are necessarily uncommitted because this sprint forbids commits;
    # pre-flight permits only these new paths after the clean initial gate.
    authorization = preflight(ROOT, configuration, require_clean=False)
    result, _ = execute_once(ROOT, configuration, authorization)
    destination = ROOT / "audits/jit-defects4j-one-shot-test/1.0.0/audit.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    reliability = destination.with_name("reliability_bins.json")
    reliability.write_text(
        json.dumps(result["reliability_bins"], indent=2, sort_keys=True) + "\n"
    )
    print(result["scientific_decision"], result["result_digest"])


if __name__ == "__main__":
    main()
