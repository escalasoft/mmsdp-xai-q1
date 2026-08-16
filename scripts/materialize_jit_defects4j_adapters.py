"""Materialize development-only JIT-Defects4J adapter artifacts and audit."""

from __future__ import annotations

import json
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from preprocessing.jit_defects4j_adapters import (  # noqa: E402
    EXPECTED_COUNTS,
    EXPECTED_TARGETS,
    FrozenInput,
    JITDefects4JAdapters,
    canonical_bytes,
    file_digest,
    load_configuration,
)


def write_canonical(path: Path, value: object) -> str:
    payload = canonical_bytes(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return file_digest(path)


def materialize(root: Path = ROOT) -> dict[str, object]:
    config_path = root / "configs/jit_defects4j_adapters.json"
    config = load_configuration(config_path)
    source = FrozenInput.load(
        root / "data/processed/jit_defects4j/1.0.0",
        config["source_manifest_sha256"],
        config["source_scientific_identity"],
    )
    adapters = JITDefects4JAdapters(source, config)
    state = adapters.fit("train")
    train = adapters.transform("train")
    validation = adapters.transform("validation")
    generated = root / "outputs/adapters/jit_defects4j/1.0.0"
    state_sha = write_canonical(generated / "text-train-state.json", state.to_dict())
    train_sha = write_canonical(generated / "train.json", train.to_dict())
    validation_sha = write_canonical(
        generated / "validation.json", validation.to_dict()
    )
    audit: dict[str, object] = {
        "decision": "GO",
        "adapter_version": config["adapter_version"],
        "source": {
            "scientific_identity": config["source_scientific_identity"],
            "manifest_sha256": config["source_manifest_sha256"],
            "input_identity": source.input_identity,
            "artifact_sha256": {
                name: value["sha256"]
                for name, value in source.manifest["artifacts"].items()
            },
        },
        "configuration_sha256": adapters.configuration_digest,
        "configuration_file_sha256": file_digest(config_path),
        "counts": {"total": sum(EXPECTED_COUNTS.values()), **EXPECTED_COUNTS},
        "targets": EXPECTED_TARGETS,
        "modalities": {
            "code": {
                "representation": "CODE-STRUCTURAL",
                "features": list(adapters.CODE_FEATURES),
                "dimensions": 6,
                "fitted_state": "none",
            },
            "process": {
                "representation": "ancestor-only raw numeric",
                "features": list(adapters.PROCESS_FEATURES),
                "dimensions": 4,
                "fitted_state": "none",
                "scaling": "none",
            },
            "text": {
                "representation": "TRAIN-fitted TF-IDF unigram CSR",
                "dimensions": len(state.vocabulary),
                "fit_partition": "train",
                "state_sha256": state_sha,
                "state_scientific_digest": state.state_digest,
                "missing_policy": config["text"]["missing_sentinel"],
            },
        },
        "alignment": {
            "identity": ["project", "commit_hash"],
            "all_modality_universes_exact": True,
            "duplicates": 0,
            "cross_split_overlap": 0,
        },
        "test_sealing": {
            "membership_mechanically_verified": True,
            "adapter_fit_consumed_test": False,
            "development_transform_consumed_test": False,
            "test_matrix_materialized": False,
            "test_labels_used_for_decisions": False,
        },
        "leakage": {
            "target_in_predictors": False,
            "metadata_in_predictors": False,
            "partition_in_predictors": False,
            "target_derived_lexical_features": False,
            "process_ancestor_only_source_contract_verified": True,
            "result": "pass",
        },
        "generated_ignored_artifacts": {
            "text-train-state.json": state_sha,
            "train.json": train_sha,
            "validation.json": validation_sha,
        },
        "scientific_digests": {
            "train": train.scientific_digest,
            "validation": validation.scientific_digest,
        },
        "provenance": {
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "dependencies": "Python standard library only",
            "model_training_performed": False,
            "performance_evaluation_performed": False,
        },
    }
    audit_path = root / "audits/jit-defects4j-adapters/1.0.0/audit.json"
    write_canonical(audit_path, audit)
    return audit


if __name__ == "__main__":
    result = materialize()
    print(json.dumps(result, indent=2, sort_keys=True))
