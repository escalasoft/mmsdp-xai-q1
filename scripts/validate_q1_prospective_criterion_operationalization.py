"""Materialize and validate the Sprint 41 prospective contract."""

from pathlib import Path

from evaluation.q1_prospective_criterion_operationalization import materialize

if __name__ == "__main__":
    materialize(Path(__file__).resolve().parents[1])
