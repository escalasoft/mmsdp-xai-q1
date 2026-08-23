"""Materialize and validate the Sprint 37 declaration."""

from pathlib import Path

from evaluation.q1_development_practical_utility_protocol import materialize

if __name__ == "__main__":
    repository = Path(__file__).resolve().parents[1]
    print(materialize(repository))
