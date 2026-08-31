#!/usr/bin/env python3
# ruff: noqa: E501
"""Generate and verify the non-predictive Sprint 48C evidence package."""

from __future__ import annotations

import argparse
from pathlib import Path

from experimentation.q1_prospective_target_label_materialization import (
    generate,
    validate_frozen_48c_snapshot,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("audits/q1-prospective-target-label-materialization/1.0.0"),
    )
    arguments = parser.parse_args()
    root = arguments.root.resolve()
    output = arguments.output if arguments.output.is_absolute() else root / arguments.output
    generate(root, output)
    errors = validate_frozen_48c_snapshot(output)
    if errors:
        for error in errors:
            print(error)
        return 1
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
