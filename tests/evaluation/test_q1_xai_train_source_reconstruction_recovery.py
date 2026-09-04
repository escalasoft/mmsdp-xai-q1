import hashlib
import json
from pathlib import Path

import pytest

from evaluation.q1_xai_train_source_reconstruction import (
    ALGORITHMS,
    FUSION_CONFIGURATIONS,
    MODALITIES,
    OUTPUT_REL,
    ReconstructionError,
    _append_recovery_event,
    _expected_logical_ids,
    _journal_records,
    _plan_indexes,
    _validate_object_reference,
)

ROOT = Path(__file__).resolve().parents[2]


def test_frozen_reconstruction_universe_has_exact_deterministic_order():
    plan, _, _ = _plan_indexes(ROOT)
    projects = sorted({row["project"] for row in plan})
    logical_ids = _expected_logical_ids(ROOT, projects)

    assert len(logical_ids) == 1736
    assert len(logical_ids) == len(set(logical_ids))
    assert logical_ids[0] == ("apache/activemq|Logistic Regression|OOF|C|block=2")
    assert logical_ids[-1] == "apache/zookeeper|LightGBM|FUSION_META|C+P+T"
    assert tuple(ALGORITHMS) == (
        "Logistic Regression",
        "Random Forest",
        "XGBoost",
        "LightGBM",
    )
    assert tuple(MODALITIES) == ("C", "P", "T")
    assert tuple(FUSION_CONFIGURATIONS) == ("C+P", "C+T", "P+T", "C+P+T")


def test_historical_blank_lines_parse_and_recovery_events_append(tmp_path):
    journal = tmp_path / "journal.jsonl"
    first = {"logical_id": "unit-1", "repetition": 1}
    journal.write_bytes(json.dumps(first).encode() + b"\n\n")
    before = journal.read_bytes()

    assert _journal_records(journal) == [first]
    _append_recovery_event(journal, {"event": "RECOVERY", "sequence": 2})

    after = journal.read_bytes()
    assert after.startswith(before)
    appended = [json.loads(line) for line in after[len(before) :].splitlines() if line]
    assert appended == [
        {
            "event": "RECOVERY",
            "sequence": 2,
        }
    ]


def test_object_reference_must_be_content_addressed_and_hash_valid(tmp_path):
    output = tmp_path / OUTPUT_REL
    objects = output / "objects"
    objects.mkdir(parents=True)
    payload = b"immutable fitted state"
    sha256 = hashlib.sha256(payload).hexdigest()
    path = objects / f"{sha256}.joblib"
    path.write_bytes(payload)
    reference = {
        "path": f"objects/{path.name}",
        "sha256": sha256,
        "bytes": len(payload),
    }

    assert _validate_object_reference(output, reference) == path
    path.write_bytes(payload + b" changed")
    with pytest.raises(ReconstructionError, match="size mismatch"):
        _validate_object_reference(output, reference)


def test_resume_code_has_no_t1_t2_g4_g5_or_xai_execution_path():
    source = (ROOT / "src/evaluation/q1_xai_train_source_reconstruction.py").read_text()
    assert "--resume-interrupted-g1-g3" in source
    assert 'mode = "ab" if journal_path.exists() else "wb"' in source
    assert 'shutil.rmtree(output / "objects")' not in source
    assert '"t1_model_query_count_block7": 0' in source
    assert '"t2_access_count_block7": 0' in source
    assert '"g4_execution_count": 0' in source
    assert '"g5_execution_count": 0' in source
    assert '"xai_execution_count": 0' in source
