#!/usr/bin/env python3
"""Run the frozen Sprint 36 DEVELOPMENT-only calibration audit."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from calibration.q1_forward_development_calibration import run  # noqa: E402

if __name__ == "__main__":
    print(run(ROOT))
