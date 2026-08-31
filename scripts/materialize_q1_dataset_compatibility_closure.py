#!/usr/bin/env python3
"""Generate and validate the non-executing Sprint 48B evidence package."""

from __future__ import annotations

import argparse
from pathlib import Path

from experimentation.q1_dataset_materialization_closure import generate, validate


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("audits/q1-dataset-materialization-compatibility-closure/1.0.0"),
    )
    arguments = parser.parse_args()
    root = arguments.root.resolve()
    output = arguments.output
    if not output.is_absolute():
        output = root / output
    generate(root, output)
    errors = validate(output)
    if errors:
        for error in errors:
            print(error)
        return 1
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
