from pathlib import Path

from evaluation.q1_human_prospective_authorization import validate


ROOT = Path(__file__).resolve().parents[2]


def test_human_authorization_is_valid_and_test_remains_sealed():
    result = validate(ROOT)
    assert result == {"status": "PASS", "test_sealed": True, "test_access_count": 0}
