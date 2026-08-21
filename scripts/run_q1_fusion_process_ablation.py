#!/usr/bin/env python3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

if __name__ == "__main__":
    from experimentation.q1_fusion_process_ablation import run  # noqa: E402

    print(run(ROOT))
