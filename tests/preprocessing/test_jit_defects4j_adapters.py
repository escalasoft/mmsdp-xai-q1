"""Focused fail-closed tests for frozen JIT-Defects4J adapters."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from preprocessing.jit_defects4j_adapters import (
    AdapterContractError,
    FinalEvaluationSeal,
    FrozenInput,
    JITDefects4JAdapters,
    canonical_bytes,
    digest,
)


def _rows() -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    observations, code, process, text = [], [], [], []
    counts = {"train": 3, "validation": 2, "test": 2}
    index = 0
    for split, count in counts.items():
        for _ in range(count):
            identity = {"project": "p", "commit_hash": f"{index:040x}"}
            observations.append({**identity, "split": split, "target": index % 2})
            code.append(
                {
                    **identity,
                    "file_changes": [{"old_mode": "100644", "new_mode": "100755"}],
                    "files_added": 0,
                    "files_deleted": 0,
                    "files_modified": 1,
                    "files_other": 0,
                }
            )
            process.append(
                {
                    **identity,
                    "parent_count": int(index > 0),
                    "is_merge_commit": 0,
                    "has_prior_history": int(index > 0),
                    "prior_project_commit_count": index,
                }
            )
            message = "alpha beta" if split == "train" else f"future{split}"
            text.append(
                {**identity, "raw_commit_message": message, "was_missing": False}
            )
            index += 1
    return observations, code, process, text


def _source(rows=None) -> FrozenInput:
    observations, code, process, text = rows or _rows()
    identities = {
        split: tuple(
            (row["project"], row["commit_hash"])
            for row in observations
            if row["split"] == split
        )
        for split in ("train", "validation", "test")
    }
    return FrozenInput(
        Path("."),
        {},
        tuple(observations),
        {(r["project"], r["commit_hash"]): r for r in code},
        {(r["project"], r["commit_hash"]): r for r in process},
        {(r["project"], r["commit_hash"]): r for r in text},
        identities,
        digest(identities),
    )


def _config() -> dict:
    return {
        "adapter_version": "test",
        "fit_partition": "train",
        "code": {"features": list(JITDefects4JAdapters.CODE_FEATURES)},
        "process": {"features": list(JITDefects4JAdapters.PROCESS_FEATURES)},
        "text": {
            "source_field": "raw_commit_message",
            "minimum_document_frequency": 1,
            "maximum_features": 10,
        },
    }


def test_identity_alignment_schema_and_distribution_are_preserved() -> None:
    adapter = JITDefects4JAdapters(_source(), _config())
    adapter.fit()
    result = adapter.transform("train")
    assert result.identities == adapter.source.identities["train"]
    assert result.targets == (0, 1, 0)
    assert len(result.code[0]) == 6 and result.code[0][-1] == 1
    assert len(result.process[0]) == 4
    assert result.text_csr["shape"][0] == 3


def test_fit_is_train_only_and_non_train_cannot_change_state() -> None:
    source = _source()
    first = JITDefects4JAdapters(source, _config())
    state = first.fit()
    changed = _rows()
    for row in changed[3]:
        if row["commit_hash"] not in {item[1] for item in source.identities["train"]}:
            row["raw_commit_message"] = "novel validation test vocabulary"
    second = JITDefects4JAdapters(_source(changed), _config())
    assert second.fit() == state
    with pytest.raises(AdapterContractError, match="TRAIN only"):
        first.fit("validation")


def test_test_is_sealed_from_development_but_mechanical_support_is_explicit() -> None:
    adapter = JITDefects4JAdapters(_source(), _config())
    adapter.fit()
    with pytest.raises(AdapterContractError, match="TEST is sealed"):
        adapter.transform("test")
    with pytest.raises(AdapterContractError, match="seal required"):
        adapter.transform_test(None)  # type: ignore[arg-type]
    result = adapter.transform_test(FinalEvaluationSeal("a" * 64))
    assert result.name == "test" and len(result.identities) == 2


def test_text_vocabulary_is_deterministic_train_only_and_has_no_target_rules() -> None:
    one = JITDefects4JAdapters(_source(), _config())
    two = JITDefects4JAdapters(_source(), deepcopy(_config()))
    assert one.fit() == two.fit()
    assert one.text_state.vocabulary == ("alpha", "beta")  # type: ignore[union-attr]
    names = set(one.CODE_FEATURES + one.PROCESS_FEATURES)
    assert names.isdisjoint({"target", "split", "project", "has_bug_keyword"})


def test_missing_text_sentinel_is_tokenized_deterministically() -> None:
    rows = _rows()
    rows[3][0]["raw_commit_message"] = "<MISSING_COMMIT_MESSAGE>"
    one = JITDefects4JAdapters(_source(rows), _config())
    state = one.fit()
    transformed = one.transform("train")
    assert state.vocabulary == ("alpha", "beta")
    assert transformed.text_csr["indptr"][:2] == [0, 0]


def test_shuffled_or_misaligned_identity_fails_closed_in_real_loader(
    tmp_path: Path,
) -> None:
    observations, code, process, text = _rows()
    text[0]["commit_hash"] = "f" * 40
    artifacts = {
        "observations.jsonl": observations,
        "code.jsonl": code,
        "process.jsonl": process,
        "text.jsonl": text,
    }
    hashes = {}
    for name, values in artifacts.items():
        payload = b"".join(canonical_bytes(value) for value in values)
        (tmp_path / name).write_bytes(payload)
        import hashlib

        hashes[name] = {"sha256": hashlib.sha256(payload).hexdigest()}
    manifest = {"scientific_identity_digest": "a" * 64, "artifacts": hashes}
    (tmp_path / "manifest.json").write_bytes(canonical_bytes(manifest))
    import hashlib

    manifest_hash = hashlib.sha256(
        (tmp_path / "manifest.json").read_bytes()
    ).hexdigest()
    with pytest.raises(AdapterContractError, match="identity universe mismatch"):
        FrozenInput.load(tmp_path, manifest_hash, "a" * 64)


def test_repeated_transform_is_scientifically_identical_without_resampling() -> None:
    adapter = JITDefects4JAdapters(_source(), _config())
    adapter.fit()
    first = adapter.transform("validation")
    second = adapter.transform("validation")
    assert first == second
    assert len(first.identities) == len(set(first.identities)) == 2
    assert first.scientific_digest == second.scientific_digest


def test_configuration_rejects_metadata_as_predictor() -> None:
    config = _config()
    config["code"]["features"][0] = "target"
    with pytest.raises(AdapterContractError, match="schema mismatch"):
        JITDefects4JAdapters(_source(), config)
