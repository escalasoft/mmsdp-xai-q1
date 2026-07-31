"""Deterministic standard-library adapter for CSV dataset sources."""

from __future__ import annotations

import csv
from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

from .contracts import AdaptedDataset, DatasetRecord

__all__ = ["CsvDatasetAdapterConfiguration", "CsvDatasetAdapter"]


def _invalid_name(value: object) -> bool:
    """Return whether *value* is not a non-blank string."""

    return not isinstance(value, str) or not value.strip()


def _freeze(value: object) -> object:
    """Return a detached, recursively immutable snapshot of *value*."""

    if isinstance(value, Mapping):
        return MappingProxyType(
            {deepcopy(key): _freeze(item) for key, item in value.items()}
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze(item) for item in value)
    return deepcopy(value)


def _thaw(value: object) -> object:
    """Return a detached representation made from ordinary Python containers."""

    if isinstance(value, Mapping):
        return {deepcopy(key): _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    if isinstance(value, frozenset):
        return {_thaw(item) for item in value}
    return deepcopy(value)


@dataclass(frozen=True, slots=True)
class CsvDatasetAdapterConfiguration:
    """Immutable configuration describing column roles in a CSV dataset.

    Args:
        dataset_name: Stable, non-empty dataset name.
        dataset_version: Stable, non-empty dataset version.
        feature_names: Ordered names of columns used as features.
        target_name: Name of the prediction-target column.
        identifier_name: Optional observation-identifier column name.
        timestamp_name: Optional timestamp column name.
        delimiter: Single-character CSV delimiter.
        encoding: Text encoding used to open the CSV source.
        metadata: Optional descriptive metadata copied into the result.
    """

    dataset_name: str
    dataset_version: str
    feature_names: Sequence[str]
    target_name: str
    identifier_name: str | None = None
    timestamp_name: str | None = None
    delimiter: str = ","
    encoding: str = "utf-8"
    metadata: Mapping[str, object] | None = None

    def __post_init__(self) -> None:
        """Validate column roles and detach all caller-owned containers."""

        for field_name in ("dataset_name", "dataset_version", "target_name"):
            if _invalid_name(getattr(self, field_name)):
                raise ValueError(f"{field_name} must be a non-empty string")
        for field_name in ("identifier_name", "timestamp_name"):
            value = getattr(self, field_name)
            if value is not None and _invalid_name(value):
                raise ValueError(f"{field_name} must be None or a non-empty string")
        if isinstance(self.feature_names, (str, bytes)) or not isinstance(
            self.feature_names, Sequence
        ):
            raise TypeError("feature_names must be a sequence of strings")
        features = tuple(self.feature_names)
        if not features:
            raise ValueError("feature_names must not be empty")
        if any(_invalid_name(name) for name in features):
            raise ValueError("feature_names must contain non-empty strings")
        if len(features) != len(set(features)):
            raise ValueError("feature_names must not contain duplicates")

        roles = (self.target_name, self.identifier_name, self.timestamp_name)
        if any(role in features for role in roles if role is not None):
            raise ValueError("configured column roles must not overlap feature_names")
        non_null_roles = tuple(role for role in roles if role is not None)
        if len(non_null_roles) != len(set(non_null_roles)):
            raise ValueError("configured column roles must not overlap")
        if not isinstance(self.delimiter, str) or len(self.delimiter) != 1:
            raise ValueError("delimiter must be a single character")
        if _invalid_name(self.encoding):
            raise ValueError("encoding must be a non-empty string")
        if self.metadata is not None and not isinstance(self.metadata, Mapping):
            raise TypeError("metadata must be a mapping or None")

        object.__setattr__(self, "feature_names", features)
        object.__setattr__(self, "metadata", _freeze(self.metadata or {}))

    def to_dict(self) -> dict[str, object]:
        """Return a deterministic, detached ordinary-structure representation."""

        return {
            "dataset_name": self.dataset_name,
            "dataset_version": self.dataset_version,
            "feature_names": list(self.feature_names),
            "target_name": self.target_name,
            "identifier_name": self.identifier_name,
            "timestamp_name": self.timestamp_name,
            "delimiter": self.delimiter,
            "encoding": self.encoding,
            "metadata": _thaw(self.metadata),
        }


class CsvDatasetAdapter:
    """Adapt a CSV file into immutable, framework-neutral dataset records."""

    adapter_name = "csv"

    def __init__(self, configuration: CsvDatasetAdapterConfiguration) -> None:
        """Create an adapter using one validated CSV configuration."""

        if not isinstance(configuration, CsvDatasetAdapterConfiguration):
            raise TypeError("configuration must be CsvDatasetAdapterConfiguration")
        self._configuration = configuration

    def adapt(self, source: object, /) -> AdaptedDataset:
        """Read *source* and return its deterministic normalized representation.

        Args:
            source: CSV file path supplied as ``str`` or ``pathlib.Path``.

        Raises:
            TypeError: If the source has an unsupported type.
            FileNotFoundError: If the source does not exist.
            IsADirectoryError: If the source identifies a directory.
            ValueError: If CSV structure or configured values are invalid.
        """

        if not isinstance(source, (str, Path)):
            raise TypeError("source must be a str or pathlib.Path")
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"CSV source does not exist: {path}")
        if path.is_dir():
            raise IsADirectoryError(f"CSV source is a directory: {path}")
        if not path.is_file():
            raise ValueError(f"CSV source is not a regular file: {path}")

        try:
            with path.open(
                "r", encoding=self._configuration.encoding, newline=""
            ) as stream:
                reader = csv.reader(
                    stream, delimiter=self._configuration.delimiter, strict=True
                )
                records = self._read_records(reader, path)
        except (csv.Error, UnicodeError) as error:
            raise ValueError(f"unable to parse CSV source: {path}") from error

        metadata = dict(self._configuration.metadata)
        metadata.update(
            {
                "adapter": {"name": self.adapter_name},
                "source": {"path": str(path)},
            }
        )
        return AdaptedDataset(
            dataset_name=self._configuration.dataset_name,
            dataset_version=self._configuration.dataset_version,
            records=records,
            feature_names=self._configuration.feature_names,
            target_name=self._configuration.target_name,
            metadata=metadata,
        )

    def _read_records(
        self, reader: csv.reader, path: Path
    ) -> tuple[DatasetRecord, ...]:
        """Validate and convert rows emitted by *reader*."""

        try:
            header = next(reader)
        except StopIteration as error:
            raise ValueError("CSV source must not be empty") from error
        if not header or all(name == "" for name in header):
            raise ValueError("CSV source must contain a header")
        if len(header) != len(set(header)):
            raise ValueError("CSV header must not contain duplicate columns")

        required = set(self._configuration.feature_names)
        required.add(self._configuration.target_name)
        if self._configuration.identifier_name is not None:
            required.add(self._configuration.identifier_name)
        if self._configuration.timestamp_name is not None:
            required.add(self._configuration.timestamp_name)
        missing = [name for name in required if name not in header]
        if missing:
            raise ValueError(
                f"CSV header is missing configured columns: {sorted(missing)}"
            )

        indexes = {name: header.index(name) for name in required}
        identifiers: set[str] = set()
        records: list[DatasetRecord] = []
        for observation_number, row in enumerate(reader, start=1):
            if len(row) != len(header):
                raise ValueError(
                    f"CSV row {observation_number} has {len(row)} columns; "
                    f"expected {len(header)}"
                )
            features = {
                name: row[indexes[name]] for name in self._configuration.feature_names
            }
            empty_features = [name for name, value in features.items() if value == ""]
            if empty_features:
                raise ValueError(
                    f"CSV row {observation_number} has empty configured features: "
                    f"{empty_features}"
                )
            target = row[indexes[self._configuration.target_name]]
            if target == "":
                raise ValueError(f"CSV row {observation_number} has an empty target")

            identifier_name = self._configuration.identifier_name
            identifier = (
                str(observation_number)
                if identifier_name is None
                else row[indexes[identifier_name]]
            )
            if identifier == "":
                raise ValueError(
                    f"CSV row {observation_number} has an empty identifier"
                )
            if identifier in identifiers:
                raise ValueError(f"CSV contains duplicate identifier: {identifier}")
            identifiers.add(identifier)

            timestamp_name = self._configuration.timestamp_name
            timestamp = None if timestamp_name is None else row[indexes[timestamp_name]]
            if timestamp == "":
                raise ValueError(f"CSV row {observation_number} has an empty timestamp")
            records.append(
                DatasetRecord(
                    identifier=identifier,
                    features=features,
                    target=target,
                    timestamp=timestamp,
                    metadata={
                        "source": {
                            "path": str(path),
                            "row_number": observation_number,
                            "line_number": reader.line_num,
                        }
                    },
                )
            )
        if not records:
            raise ValueError("CSV source must contain at least one observation")
        return tuple(records)
