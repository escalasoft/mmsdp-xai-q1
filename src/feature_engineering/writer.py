"""Deterministic, atomic CSV writing for immutable feature records."""

import csv
import hashlib
import os
import tempfile
from collections.abc import Iterable
from dataclasses import astuple
from pathlib import Path

from .schema import (
    CodeFeatureRecord,
    FeatureArtifact,
    FeatureEngineeringError,
    FeatureModality,
    ProcessFeatureRecord,
    TextFeatureRecord,
)

CODE_COLUMNS = tuple(CodeFeatureRecord.__dataclass_fields__)
PROCESS_COLUMNS = tuple(ProcessFeatureRecord.__dataclass_fields__)
TEXT_COLUMNS = tuple(TextFeatureRecord.__dataclass_fields__)
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_PROTECTED_OUTPUT_DIRECTORIES = (_PROJECT_ROOT / "docs", _PROJECT_ROOT / "reference")


def write_code_features(
    records: Iterable[CodeFeatureRecord], output_path: str | Path, **options: bool
) -> FeatureArtifact:
    """Write code features in their stable contract order."""
    return _write(records, output_path, FeatureModality.CODE, CODE_COLUMNS, **options)


def write_process_features(
    records: Iterable[ProcessFeatureRecord], output_path: str | Path, **options: bool
) -> FeatureArtifact:
    """Write process features in their stable contract order."""
    return _write(
        records, output_path, FeatureModality.PROCESS, PROCESS_COLUMNS, **options
    )


def write_text_features(
    records: Iterable[TextFeatureRecord], output_path: str | Path, **options: bool
) -> FeatureArtifact:
    """Write text features in their stable contract order."""
    return _write(records, output_path, FeatureModality.TEXT, TEXT_COLUMNS, **options)


def _write(
    records: Iterable[object],
    output_path: str | Path,
    modality: FeatureModality,
    columns: tuple[str, ...],
    *,
    overwrite: bool = False,
    create_parents: bool = False,
) -> FeatureArtifact:
    destination = Path(output_path).resolve()
    if destination.suffix.lower() != ".csv":
        raise FeatureEngineeringError("Feature output must use the .csv extension")
    if any(destination.is_relative_to(path) for path in _PROTECTED_OUTPUT_DIRECTORIES):
        raise FeatureEngineeringError(
            f"Feature output is prohibited in governance paths: {destination}"
        )
    if destination.exists() and not overwrite:
        raise FeatureEngineeringError(f"Feature output exists: {destination}")
    if not destination.parent.exists():
        if not create_parents:
            raise FeatureEngineeringError(
                f"Output parent directory does not exist: {destination.parent}"
            )
        destination.parent.mkdir(parents=True)

    count = 0
    temporary_name = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_name = temporary.name
            writer = csv.writer(temporary, lineterminator="\n")
            writer.writerow(columns)
            for record in records:
                writer.writerow(astuple(record))
                count += 1
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_name, destination)
        temporary_name = None
    except (csv.Error, OSError, TypeError) as error:
        raise FeatureEngineeringError(
            f"Unable to write feature output: {destination}"
        ) from error
    finally:
        if temporary_name is not None:
            Path(temporary_name).unlink(missing_ok=True)

    return FeatureArtifact(
        path=destination,
        modality=modality,
        row_count=count,
        column_names=columns,
        checksum=hashlib.sha256(destination.read_bytes()).hexdigest(),
    )
