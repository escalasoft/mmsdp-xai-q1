#!/usr/bin/env python3
"""Generate or verify the ApacheJIT v2 scientific suitability audit package."""

from __future__ import annotations

import argparse
from pathlib import Path

from dataset.apachejit_suitability_audit import build_audit, verify_manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--extracted-root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--acquired-at")
    parser.add_argument("--starting-head")
    parser.add_argument("--branch")
    parser.add_argument("--verify-manifest", action="store_true")
    args = parser.parse_args()
    if args.verify_manifest:
        if not verify_manifest(args.output):
            raise SystemExit("manifest verification failed")
        print("MANIFEST_VERIFICATION=PASS")
        return 0
    required = {
        "archive": args.archive,
        "extracted_root": args.extracted_root,
        "acquired_at": args.acquired_at,
        "starting_head": args.starting_head,
        "branch": args.branch,
    }
    missing = [name for name, value in required.items() if value is None]
    if missing:
        parser.error(f"missing generation arguments: {', '.join(missing)}")
    build_audit(
        args.archive,
        args.extracted_root,
        args.output,
        acquired_at=args.acquired_at,
        starting_head=args.starting_head,
        branch=args.branch,
    )
    print("APACHEJIT_SUITABILITY_AUDIT=GENERATED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
