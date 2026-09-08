"""Run metadata/static parent tests; omit the obsolete parent branch/HEAD assertion.

The existing 56.2H guard denies source/T1/T2 payload routing and parent writes.
Its own runner supplies 56 earlier governance regressions in a separate command.
No training/smoke-execution entry point is called here.
"""

import sys

import pytest
from src.evaluation import q1_primary_xai_alternative_design as prior

prior.prepare()
sys.addaudithook(prior.guard)
raise SystemExit(
    pytest.main(
        [
            "-q",
            "-p",
            "no:cacheprovider",
            "tests/evaluation/test_q1_xai_runtime_freeze.py",
            "tests/evaluation/test_q1_primary_xai_alternative_design.py",
            "-k",
            "not test_branch_head",
        ]
    )
)
