"""Implementation-independent contracts for dataset artifacts and records."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path


class DatasetStage(Enum):
    """Lifecycle stage of a dataset artifact."""

    RAW = "raw"
    INTERIM = "interim"
    PROCESSED = "processed"


class DatasetSplit(Enum):
    """Chronological dataset split assigned outside this layer."""

    TRAIN = "train"
    VALIDATION = "validation"
    TEST = "test"


@dataclass
class DatasetArtifact:
    """Traceability metadata for a dataset artifact."""

    path: Path
    stage: DatasetStage
    dataset_version: str
    source_snapshot: str
    checksum: str
    created_at: datetime
    row_count: int
    column_names: tuple[str, ...]


@dataclass
class DatasetContract:
    """Caller-defined schema rules without unresolved scientific assumptions."""

    required_columns: tuple[str, ...]
    optional_columns: tuple[str, ...]
    primary_key: str
    target_column: str | None = None
    timestamp_column: str | None = None


class DatasetError(Exception):
    """Base exception for dataset-layer failures."""


class DatasetNotFoundError(DatasetError):
    """Raised when a dataset path does not identify a regular file."""


class UnsupportedDatasetFormatError(DatasetError):
    """Raised when a dataset format is unsupported."""


class MalformedDatasetError(DatasetError):
    """Raised when a supported dataset cannot be parsed safely."""


class DatasetValidationError(DatasetError):
    """Raised when dataset records violate a supplied contract."""
