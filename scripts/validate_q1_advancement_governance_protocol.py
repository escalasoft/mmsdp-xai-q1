"""Materialize and validate the prospective Sprint 39 governance protocol."""

from pathlib import Path

from evaluation.q1_advancement_governance_protocol import materialize

if __name__ == "__main__":
    materialize(Path(__file__).resolve().parents[1])
