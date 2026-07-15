"""Safe, standard-library-only loading for dataset artifacts."""

import csv
from pathlib import Path

from .schema import (
    DatasetNotFoundError,
    MalformedDatasetError,
    UnsupportedDatasetFormatError,
)


def load_csv(path: str | Path) -> list[dict[str, str]]:
    """Load UTF-8 CSV records without transforming source values."""
    dataset_path = Path(path)
    if not dataset_path.is_file():
        raise DatasetNotFoundError(f"Dataset file not found: {dataset_path}")
    if dataset_path.suffix.lower() != ".csv":
        raise UnsupportedDatasetFormatError(
            f"Unsupported dataset format: {dataset_path.suffix or '<none>'}"
        )

    try:
        with dataset_path.open("r", encoding="utf-8", newline="") as source:
            reader = csv.DictReader(source, strict=True)
            fieldnames = _validate_header(reader.fieldnames)
            records = []
            for line_number, row in enumerate(reader, start=2):
                if None in row or any(value is None for value in row.values()):
                    raise MalformedDatasetError(
                        f"Malformed CSV row at line {line_number}"
                    )
                records.append({name: row[name] for name in fieldnames})
            return records
    except MalformedDatasetError:
        raise
    except (csv.Error, UnicodeError, OSError) as error:
        raise MalformedDatasetError(
            f"Unable to read CSV dataset: {dataset_path}"
        ) from error


def _validate_header(fieldnames: list[str] | None) -> tuple[str, ...]:
    if not fieldnames or any(not name for name in fieldnames):
        raise MalformedDatasetError("CSV dataset must have a non-empty header")
    if len(fieldnames) != len(set(fieldnames)):
        raise MalformedDatasetError("CSV dataset contains duplicate column names")
    return tuple(fieldnames)
