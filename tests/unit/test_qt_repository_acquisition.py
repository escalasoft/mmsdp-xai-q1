"""Unit contracts for deterministic Qt repository acquisition."""

import dataclasses
import json
import subprocess
from pathlib import Path

import pytest

import extraction.qt_repository_acquisition as acquisition
from dataset.scientific_builder_contracts import (
    ScientificArtifactReference,
    ScientificArtifactRole,
    ScientificRepositorySnapshot,
)
from extraction.qt_repository_acquisition import (
    QtRepositoryAcquirer,
    QtRepositoryAcquisitionResult,
    QtRepositoryAcquisitionSpecification,
)

CANONICAL = "https://code.qt.io/qt/qtbase.git"
REVISION = "a" * 40
DIGEST = "b" * 64


def specification(**changes: object) -> QtRepositoryAcquisitionSpecification:
    values = {
        "repository_name": "qtbase",
        "canonical_repository_url": CANONICAL,
        "transport_repository_url": CANONICAL,
        "requested_reference": "dev",
        "default_branch": "dev",
        "acquisition_policy_version": "1.0.0",
        "allowed_hash_algorithms": ("sha256", "sha1"),
        "metadata": {"nested": {"values": [1, 2]}},
    }
    values.update(changes)
    return QtRepositoryAcquisitionSpecification(**values)


def local_specification() -> QtRepositoryAcquisitionSpecification:
    return QtRepositoryAcquisitionSpecification._for_local_test(
        repository_name="qtbase",
        canonical_repository_url=CANONICAL,
        transport_repository_url="/tmp/operational-qtbase.git",
        requested_reference="dev",
        default_branch="dev",
        acquisition_policy_version="1.0.0",
        allowed_hash_algorithms=("sha1", "sha256"),
        metadata={},
    )


def snapshot(**changes: object) -> ScientificRepositorySnapshot:
    values = {
        "repository_name": "qtbase",
        "repository_url": CANONICAL,
        "repository_revision": REVISION,
        "default_branch": "dev",
        "acquisition_policy_version": "1.0.0",
        "snapshot_digest": DIGEST,
        "metadata": {},
    }
    values.update(changes)
    return ScientificRepositorySnapshot(**values)


def artifact(**changes: object) -> ScientificArtifactReference:
    values = {
        "artifact_name": "qtbase-repository-snapshot",
        "artifact_role": ScientificArtifactRole.REPOSITORY_SNAPSHOT,
        "repository_relative_path": "artifacts/repository/qtbase-snapshot.json",
        "content_digest": DIGEST,
        "schema_version": "1.0.0",
        "record_count": 1,
        "metadata": {},
    }
    values.update(changes)
    return ScientificArtifactReference(**values)


def result(**changes: object) -> QtRepositoryAcquisitionResult:
    spec = changes.pop("specification", specification(metadata={}))
    repository_snapshot = changes.pop("repository_snapshot", snapshot())
    acquisition_artifact = changes.pop("acquisition_artifact", artifact())
    assert isinstance(spec, QtRepositoryAcquisitionSpecification)
    assert isinstance(repository_snapshot, ScientificRepositorySnapshot)
    algorithm = changes.get("object_hash_algorithm", "sha1")
    revision = changes.get("resolved_revision", REVISION)
    assert isinstance(algorithm, str)
    assert isinstance(revision, str)
    identity_digest = DIGEST
    if isinstance(acquisition_artifact, ScientificArtifactReference):
        identity_digest = acquisition._identity_digest(
            spec,
            repository_snapshot,
            revision,
            algorithm,
            acquisition_artifact,
        )
    values = {
        "specification": spec,
        "repository_snapshot": repository_snapshot,
        "resolved_reference": spec.requested_reference,
        "resolved_revision": revision,
        "object_hash_algorithm": algorithm,
        "canonical_repository_url": CANONICAL,
        "transport_repository_url": spec.transport_repository_url,
        "repository_identity_digest": identity_digest,
        "acquisition_artifact": acquisition_artifact,
        "command_evidence": ("git:cat-file:completed", "git:rev-parse:completed"),
        "metadata": {},
    }
    values.update(changes)
    return QtRepositoryAcquisitionResult(**values)


def test_exact_public_api() -> None:
    assert acquisition.__all__ == [
        "QtRepositoryAcquisitionSpecification",
        "QtRepositoryAcquisitionResult",
        "QtRepositoryAcquirer",
    ]


def test_specification_is_immutable_detached_and_deterministic() -> None:
    source = {"nested": {"values": [1, 2]}}
    spec = specification(metadata=source)
    source["nested"]["values"].append(3)  # type: ignore[index,union-attr]
    assert spec.to_dict()["metadata"] == {"nested": {"values": [1, 2]}}
    assert spec.allowed_hash_algorithms == ("sha1", "sha256")
    with pytest.raises(dataclasses.FrozenInstanceError):
        spec.requested_reference = "other"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"repository_name": "other"}, "qtbase"),
        ({"canonical_repository_url": "https://example.test/qtbase.git"}, "canonical"),
        ({"transport_repository_url": "https://u:p@example.test/repo"}, "credentials"),
        ({"requested_reference": ""}, "non-empty"),
        ({"allowed_hash_algorithms": ()}, "exactly sha1 and sha256"),
        ({"allowed_hash_algorithms": ("sha1",)}, "exactly sha1 and sha256"),
        (
            {"allowed_hash_algorithms": ("sha1", "sha1", "sha256")},
            "exactly sha1 and sha256",
        ),
        (
            {"allowed_hash_algorithms": ("sha1", "sha256", "sha512")},
            "exactly sha1 and sha256",
        ),
    ],
)
def test_invalid_specification_is_rejected(
    change: dict[str, object], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        specification(**change)


def test_constructor_performs_no_subprocess(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("constructor invoked subprocess")

    monkeypatch.setattr(subprocess, "run", forbidden)
    specification()
    QtRepositoryAcquirer()


def test_placeholder_prevents_execution(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    spec = specification(requested_reference="revision-required-before-execution")

    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("placeholder invoked subprocess")

    monkeypatch.setattr(subprocess, "run", forbidden)
    with pytest.raises(ValueError, match="deliberately resolved"):
        QtRepositoryAcquirer().acquire(spec, tmp_path / "clone")


def test_metadata_rejects_runtime_and_local_identity() -> None:
    with pytest.raises(ValueError, match="forbidden"):
        specification(metadata={"hostname": "worker"})
    with pytest.raises(ValueError, match="machine-local"):
        specification(metadata={"note": "/tmp/local"})


def test_configuration_keeps_deliberate_placeholder() -> None:
    config_path = (
        Path(__file__).resolve().parents[2] / "configs/qt_repository_acquisition.json"
    )
    config = json.loads(config_path.read_text(encoding="utf-8"))
    assert config["canonical_repository_url"] == CANONICAL
    assert config["requested_reference"] == "revision-required-before-execution"


def test_adapter_has_no_downstream_scientific_apis() -> None:
    prohibited = {
        "extract_commits",
        "extract_diffs",
        "extract_issues",
        "construct_targets",
        "construct_features",
        "construct_dataset",
        "train_model",
        "run_experiment",
    }
    assert prohibited.isdisjoint(dir(QtRepositoryAcquirer))
    assert QtRepositoryAcquirer.acquirer_name == "qt-repository-acquirer"


def test_result_type_is_frozen_and_slotted() -> None:
    assert QtRepositoryAcquisitionResult.__dataclass_params__.frozen
    assert "__dict__" not in QtRepositoryAcquisitionResult.__slots__


def test_valid_result_and_command_evidence_are_accepted() -> None:
    created = result()
    assert created.command_evidence == (
        "git:cat-file:completed",
        "git:rev-parse:completed",
    )


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"resolved_reference": "other"}, "resolved_reference"),
        (
            {"transport_repository_url": "https://example.test/repo.git"},
            "production transport",
        ),
        (
            {"canonical_repository_url": "https://example.test/qtbase.git"},
            "canonical_repository_url",
        ),
        ({"repository_snapshot": snapshot(repository_name="other")}, "repository_name"),
        (
            {
                "repository_snapshot": snapshot(
                    repository_url="https://example.test/qtbase.git"
                )
            },
            "repository_url",
        ),
        ({"repository_snapshot": snapshot(default_branch="main")}, "default_branch"),
        (
            {"repository_snapshot": snapshot(acquisition_policy_version="2.0.0")},
            "acquisition_policy_version",
        ),
    ],
)
def test_result_consistency_mismatches_are_rejected(
    change: dict[str, object], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        result(**change)


def test_local_result_transport_mismatch_is_rejected() -> None:
    spec = local_specification()._detached_for_result()
    with pytest.raises(ValueError, match="local-test transport"):
        result(specification=spec, transport_repository_url="other")


def test_non_artifact_reference_is_rejected() -> None:
    with pytest.raises(TypeError, match="ScientificArtifactReference"):
        result(acquisition_artifact="not-an-artifact")


@pytest.mark.parametrize(
    "evidence",
    [
        ("",),
        ("git:status:completed",),
        ("git:clone:/tmp/private",),
        ("git:clone:completed:2026-08-04T12:00:00Z",),
        ("git:clone:completed in 2s",),
        ("git:clone:completed user=alex",),
        ("git:clone:completed host=worker",),
        ("git:clone:completed https://u:p@example.test",),
        ("git:clone:completed stdout=data",),
        ("git:clone:completed <object at 0x123456>",),
    ],
)
def test_malformed_or_path_bearing_command_evidence_is_rejected(
    evidence: tuple[str, ...],
) -> None:
    with pytest.raises(ValueError, match="command_evidence"):
        result(command_evidence=evidence)
