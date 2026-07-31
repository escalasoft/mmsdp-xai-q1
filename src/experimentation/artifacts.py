"""Deterministic persistence for reproducible experiment artifacts."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass, fields
from pathlib import Path

from experimentation.evaluation import ExperimentEvaluationResult
from experimentation.runner import ExperimentRunResult
from experimentation.specification import ExperimentSpecification

__all__ = ["ExperimentArtifactManifest", "ExperimentArtifactWriter"]

_ARTIFACT_FILENAMES = (
    "specification.json",
    "run_result.json",
    "evaluation.json",
    "manifest.json",
)


@dataclass(frozen=True, slots=True)
class ExperimentArtifactManifest:
    """Immutable description of one persisted experiment artifact bundle."""

    experiment_id: str
    output_directory: str
    specification_file: str
    run_result_file: str
    evaluation_file: str
    manifest_file: str
    specification_sha256: str
    run_result_sha256: str
    evaluation_sha256: str

    def __post_init__(self) -> None:
        for field in fields(self):
            value = getattr(self, field.name)
            if not isinstance(value, str):
                raise TypeError(f"{field.name} must be a string")
            if not value:
                raise ValueError(f"{field.name} must not be empty")
            object.__setattr__(self, field.name, str(value))

        for name in (
            "specification_sha256",
            "run_result_sha256",
            "evaluation_sha256",
        ):
            value = getattr(self, name)
            if len(value) != 64 or any(
                character not in "0123456789abcdef" for character in value
            ):
                raise ValueError(
                    f"{name} must be a lowercase 64-character hexadecimal string"
                )

    def to_dict(self) -> dict[str, object]:
        """Return a detached dictionary containing every manifest field."""
        return {field.name: getattr(self, field.name) for field in fields(self)}


class ExperimentArtifactWriter:
    """Persist one validated experiment bundle as deterministic JSON files."""

    def __init__(self, *, overwrite: bool = False) -> None:
        if not isinstance(overwrite, bool):
            raise TypeError("overwrite must be a boolean")
        self._overwrite = overwrite

    @property
    def overwrite(self) -> bool:
        """Whether existing experiment artifacts may be replaced."""
        return self._overwrite

    def write(
        self,
        specification: ExperimentSpecification,
        run_result: ExperimentRunResult,
        evaluation: ExperimentEvaluationResult,
        output_directory: str | Path,
    ) -> ExperimentArtifactManifest:
        """Write and return the manifest for one experiment artifact bundle."""
        self._validate_inputs(specification, run_result, evaluation, output_directory)
        destination = Path(output_directory)
        destination.mkdir(parents=True, exist_ok=True)
        final_paths = {
            filename: destination / filename for filename in _ARTIFACT_FILENAMES
        }
        if not self.overwrite:
            existing = next(
                (path for path in final_paths.values() if path.exists()), None
            )
            if existing is not None:
                raise FileExistsError(f"artifact already exists: {existing}")

        specification_bytes = self._serialize(specification.to_dict())
        run_result_bytes = self._serialize(run_result.to_dict())
        evaluation_bytes = self._serialize(evaluation.to_dict())
        manifest = ExperimentArtifactManifest(
            experiment_id=str(specification.experiment_id),
            output_directory=str(destination),
            specification_file="specification.json",
            run_result_file="run_result.json",
            evaluation_file="evaluation.json",
            manifest_file="manifest.json",
            specification_sha256=self._sha256(specification_bytes),
            run_result_sha256=self._sha256(run_result_bytes),
            evaluation_sha256=self._sha256(evaluation_bytes),
        )
        content = {
            "specification.json": specification_bytes,
            "run_result.json": run_result_bytes,
            "evaluation.json": evaluation_bytes,
            "manifest.json": self._serialize(manifest.to_dict()),
        }
        self._persist(content, final_paths, overwrite=self.overwrite)
        return manifest

    @staticmethod
    def _validate_inputs(
        specification: ExperimentSpecification,
        run_result: ExperimentRunResult,
        evaluation: ExperimentEvaluationResult,
        output_directory: str | Path,
    ) -> None:
        for value, name in (
            (specification, "specification"),
            (run_result, "run_result"),
            (evaluation, "evaluation"),
        ):
            if value is None:
                raise ValueError(f"{name} must not be None")
        if isinstance(output_directory, str) and not output_directory:
            raise ValueError("output_directory must not be empty")
        if not isinstance(output_directory, (str, Path)):
            raise TypeError("output_directory must be a string or Path")
        if specification.experiment_id != run_result.experiment_id:
            raise ValueError("specification and run result experiment IDs must match")
        if specification.experiment_id != evaluation.experiment_id:
            raise ValueError("specification and evaluation experiment IDs must match")
        if specification.class_labels != run_result.class_labels:
            raise ValueError("specification and run result class labels must match")
        if run_result.class_labels != evaluation.class_labels:
            raise ValueError("run result and evaluation class labels must match")
        if evaluation.observation_count != run_result.evaluation_observation_count:
            raise ValueError("evaluation observation counts must match")

    @staticmethod
    def _serialize(value: dict[str, object]) -> bytes:
        text = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        return f"{text}\n".encode()

    @staticmethod
    def _sha256(content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    @staticmethod
    def _persist(
        content: dict[str, bytes],
        final_paths: dict[str, Path],
        *,
        overwrite: bool,
    ) -> None:
        temporary_paths: dict[str, Path] = {}
        backup_paths: dict[str, Path] = {}
        installed_paths: list[Path] = []
        try:
            for filename, payload in content.items():
                descriptor, temporary_name = tempfile.mkstemp(
                    dir=final_paths[filename].parent,
                    prefix=f".{filename}.",
                    suffix=".tmp",
                )
                temporary_path = Path(temporary_name)
                temporary_paths[filename] = temporary_path
                with os.fdopen(descriptor, "wb") as stream:
                    stream.write(payload)
                    stream.flush()
                    os.fsync(stream.fileno())
            for filename in _ARTIFACT_FILENAMES:
                final_path = final_paths[filename]
                if final_path.exists():
                    if not overwrite:
                        raise FileExistsError(f"artifact already exists: {final_path}")
                    descriptor, backup_name = tempfile.mkstemp(
                        dir=final_path.parent,
                        prefix=f".{filename}.",
                        suffix=".backup",
                    )
                    os.close(descriptor)
                    backup_path = Path(backup_name)
                    backup_path.unlink()
                    os.replace(final_path, backup_path)
                    backup_paths[filename] = backup_path
            for filename in _ARTIFACT_FILENAMES:
                final_path = final_paths[filename]
                os.replace(temporary_paths.pop(filename), final_path)
                installed_paths.append(final_path)
        except Exception:
            for installed_path in installed_paths:
                installed_path.unlink(missing_ok=True)
            for filename, backup_path in backup_paths.items():
                os.replace(backup_path, final_paths[filename])
            raise
        finally:
            for temporary_path in temporary_paths.values():
                temporary_path.unlink(missing_ok=True)
            for backup_path in backup_paths.values():
                backup_path.unlink(missing_ok=True)
