"""Deterministic tabular export of scientific batch experiment results."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import os
import re
import tempfile
from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass, field, fields
from pathlib import Path
from types import MappingProxyType

from experimentation.batch_runner import BatchExperimentRecord, BatchExperimentResult

__all__ = [
    "ScientificResultsExportConfiguration",
    "ScientificResultsArtifact",
    "ScientificResultsExporter",
]

_SCHEMA_VERSION = "1.0"
_RUNTIME_COLUMN = "execution_duration_seconds"
_RECORD_COLUMNS = tuple(item.name for item in fields(BatchExperimentRecord))
_SUMMARY_COLUMNS = (
    "execution_index",
    "experiment_fingerprint",
    "dataset_name",
    "dataset_version",
    "model_name",
    "model_family",
    "calibration_method",
    "training_observation_count",
    "validation_observation_count",
    "test_observation_count",
    "uncalibrated_validation_roc_auc",
    "uncalibrated_validation_pr_auc",
    "uncalibrated_validation_f1",
    "uncalibrated_validation_mcc",
    "uncalibrated_validation_brier_score",
    "calibrated_validation_brier_score",
    "uncalibrated_test_roc_auc",
    "uncalibrated_test_pr_auc",
    "uncalibrated_test_precision",
    "uncalibrated_test_recall",
    "uncalibrated_test_f1",
    "uncalibrated_test_mcc",
    "uncalibrated_test_brier_score",
    "calibrated_test_brier_score",
    "successful_local_explanation_count",
    "unsupported_local_explanation_count",
    "successful_counterfactual_count",
    "unsupported_counterfactual_count",
)
_COMPARISON_COLUMNS = (
    "Model",
    "Calibration",
    "ROC-AUC",
    "PR-AUC",
    "Precision",
    "Recall",
    "F1",
    "MCC",
    "Brier (uncalibrated)",
    "Brier (calibrated)",
)
_COMPARISON_FIELDS = (
    "model_name",
    "calibration_method",
    "uncalibrated_test_roc_auc",
    "uncalibrated_test_pr_auc",
    "uncalibrated_test_precision",
    "uncalibrated_test_recall",
    "uncalibrated_test_f1",
    "uncalibrated_test_mcc",
    "uncalibrated_test_brier_score",
    "calibrated_test_brier_score",
)
_SAFE_PREFIX = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _freeze(value: object, *, location: str = "metadata") -> object:
    """Return an immutable, JSON-compatible, detached value."""
    if isinstance(value, Mapping):
        frozen: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(f"{location} keys must be strings")
            frozen[key] = _freeze(item, location=f"{location}.{key}")
        return MappingProxyType(frozen)
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item, location=location) for item in value)
    if value is None or isinstance(value, (str, bool, int)):
        return deepcopy(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{location} must not contain NaN or infinity")
        return value
    raise TypeError(f"{location} contains a non-JSON-compatible value")


def _thaw(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in sorted(value.items())}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return deepcopy(value)


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _csv_value(value: object) -> object:
    if value is None:
        return "null"
    if isinstance(value, (Mapping, list, tuple)):
        return _canonical_bytes(_thaw(value)).decode("utf-8")
    if isinstance(value, bool):
        return str(value).lower()
    return value


@dataclass(frozen=True, slots=True)
class ScientificResultsExportConfiguration:
    """Immutable configuration for a reproducible scientific export."""

    output_directory: str | os.PathLike[str]
    artifact_prefix: str = "scientific_results"
    include_runtime: bool = False
    decimal_places: int = 4
    sort_columns: tuple[str, ...] = ()
    metadata: Mapping[str, object] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        try:
            output_directory = os.fspath(self.output_directory)
        except TypeError as error:
            raise TypeError("output_directory must be a path-like string") from error
        if not isinstance(output_directory, str) or not output_directory.strip():
            raise ValueError("output_directory must be a non-empty path-like string")
        prefix = self.artifact_prefix
        if not isinstance(prefix, str) or not prefix.strip():
            raise ValueError("artifact_prefix must be a non-empty string")
        if Path(prefix).is_absolute() or "/" in prefix or "\\" in prefix:
            raise ValueError("artifact_prefix must not be absolute or contain paths")
        if prefix in {".", ".."} or not _SAFE_PREFIX.fullmatch(prefix):
            raise ValueError("artifact_prefix must be a safe file-name component")
        if not isinstance(self.include_runtime, bool):
            raise TypeError("include_runtime must be a boolean")
        if isinstance(self.decimal_places, bool) or not isinstance(
            self.decimal_places, int
        ):
            raise TypeError("decimal_places must be an integer and must not be bool")
        if self.decimal_places < 0:
            raise ValueError("decimal_places must be non-negative")
        if isinstance(self.sort_columns, (str, bytes)) or not isinstance(
            self.sort_columns, Sequence
        ):
            raise TypeError("sort_columns must be an ordered sequence")
        normalized_sort_columns = tuple(self.sort_columns)
        if any(not isinstance(item, str) for item in normalized_sort_columns):
            raise TypeError("sort_columns must contain strings")
        invalid = tuple(
            item for item in normalized_sort_columns if item not in _RECORD_COLUMNS
        )
        if invalid:
            raise ValueError(f"invalid sort columns: {', '.join(invalid)}")
        if len(set(normalized_sort_columns)) != len(normalized_sort_columns):
            raise ValueError("sort_columns must not contain duplicates")
        if _RUNTIME_COLUMN in normalized_sort_columns and not self.include_runtime:
            raise ValueError(
                "execution_duration_seconds may be sorted only when runtime is included"
            )
        if not isinstance(self.metadata, Mapping):
            raise TypeError("metadata must be a mapping")
        object.__setattr__(self, "output_directory", output_directory)
        object.__setattr__(self, "sort_columns", normalized_sort_columns)
        object.__setattr__(self, "metadata", _freeze(self.metadata))

    def to_dict(self) -> dict[str, object]:
        """Return a deterministic detached representation."""
        return {
            "output_directory": self.output_directory,
            "artifact_prefix": self.artifact_prefix,
            "include_runtime": self.include_runtime,
            "decimal_places": self.decimal_places,
            "sort_columns": list(self.sort_columns),
            "metadata": _thaw(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class ScientificResultsArtifact:
    """Immutable description of an exported scientific artifact bundle."""

    experiment_name: str
    execution_count: int
    complete_csv_path: str
    summary_csv_path: str
    markdown_table_path: str
    latex_table_path: str
    manifest_json_path: str
    complete_row_count: int
    summary_row_count: int
    exported_columns: tuple[str, ...]
    scientific_digest: str
    metadata: Mapping[str, object] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if (
            not isinstance(self.experiment_name, str)
            or not self.experiment_name.strip()
        ):
            raise ValueError("experiment_name must be a non-empty string")
        for name in (
            "complete_csv_path",
            "summary_csv_path",
            "markdown_table_path",
            "latex_table_path",
            "manifest_json_path",
        ):
            value = getattr(self, name)
            if not isinstance(value, str):
                raise TypeError(f"{name} must be a string")
            if not value:
                raise ValueError(f"{name} must not be empty")
        for name in ("execution_count", "complete_row_count", "summary_row_count"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{name} must be an integer and must not be bool")
            if value < 0:
                raise ValueError(f"{name} must be non-negative")
        if self.complete_row_count != self.execution_count:
            raise ValueError("complete_row_count must equal execution_count")
        if self.summary_row_count != self.execution_count:
            raise ValueError("summary_row_count must equal execution_count")
        columns = tuple(self.exported_columns)
        if not columns:
            raise ValueError("exported_columns must not be empty")
        if any(not isinstance(item, str) or not item for item in columns):
            raise ValueError("exported_columns must contain non-empty strings")
        if len(set(columns)) != len(columns):
            raise ValueError("exported_columns must not contain duplicates")
        digest = self.scientific_digest
        if (
            not isinstance(digest, str)
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
        ):
            raise ValueError("scientific_digest must be a SHA-256 hexadecimal digest")
        if not isinstance(self.metadata, Mapping):
            raise TypeError("metadata must be a mapping")
        object.__setattr__(self, "exported_columns", columns)
        object.__setattr__(self, "metadata", _freeze(self.metadata))

    def to_dict(self) -> dict[str, object]:
        """Return a deterministic detached representation."""
        return {
            item.name: (
                list(self.exported_columns)
                if item.name == "exported_columns"
                else _thaw(self.metadata)
                if item.name == "metadata"
                else getattr(self, item.name)
            )
            for item in fields(self)
        }


class ScientificResultsExporter:
    """Export batch records without executing or recalculating experiments."""

    def export(
        self,
        result: BatchExperimentResult,
        configuration: ScientificResultsExportConfiguration,
    ) -> ScientificResultsArtifact:
        """Atomically export complete, summary, comparison, and manifest files."""
        if not isinstance(result, BatchExperimentResult):
            raise TypeError("result must be a BatchExperimentResult")
        if not isinstance(configuration, ScientificResultsExportConfiguration):
            raise TypeError(
                "configuration must be a ScientificResultsExportConfiguration"
            )
        rows = result.to_rows(include_runtime=configuration.include_runtime)
        self._validate_finite(rows)
        if configuration.sort_columns:
            rows = sorted(
                rows,
                key=lambda row: tuple(
                    self._sort_key(row[column]) for column in configuration.sort_columns
                ),
            )
        exported_columns = tuple(
            column
            for column in _RECORD_COLUMNS
            if configuration.include_runtime or column != _RUNTIME_COLUMN
        )
        scientific_content = {
            "export_schema_version": _SCHEMA_VERSION,
            "experiment_name": result.experiment_name,
            "execution_count": result.execution_count,
            "experiment_fingerprints": [row["experiment_fingerprint"] for row in rows],
            "decimal_places": configuration.decimal_places,
            "include_runtime": configuration.include_runtime,
            "exported_columns": list(exported_columns),
            "sort_columns": list(configuration.sort_columns),
            "rows": rows,
        }
        digest = hashlib.sha256(_canonical_bytes(scientific_content)).hexdigest()
        prefix = configuration.artifact_prefix
        filenames = {
            "complete_csv": f"{prefix}_complete.csv",
            "summary_csv": f"{prefix}_summary.csv",
            "markdown_table": f"{prefix}_comparison.md",
            "latex_table": f"{prefix}_comparison.tex",
            "manifest_json": f"{prefix}_manifest.json",
        }
        manifest = {
            "export_schema_version": _SCHEMA_VERSION,
            "experiment_name": result.experiment_name,
            "execution_count": result.execution_count,
            "exported_files": filenames,
            "exported_columns": {
                "complete": list(exported_columns),
                "summary": list(_SUMMARY_COLUMNS),
                "comparison": list(_COMPARISON_COLUMNS),
            },
            "experiment_fingerprints": scientific_content["experiment_fingerprints"],
            "include_runtime": configuration.include_runtime,
            "decimal_places": configuration.decimal_places,
            "sort_columns": list(configuration.sort_columns),
            "scientific_digest": digest,
            "exporter_metadata": _thaw(configuration.metadata),
            "source_batch_metadata": _thaw(result.metadata),
            "scientific_content": scientific_content,
        }
        payloads = {
            filenames["complete_csv"]: self._csv(rows, exported_columns),
            filenames["summary_csv"]: self._csv(rows, _SUMMARY_COLUMNS),
            filenames["markdown_table"]: self._markdown(
                rows, configuration.decimal_places
            ),
            filenames["latex_table"]: self._latex(
                rows, configuration.decimal_places, prefix
            ),
            filenames["manifest_json"]: (
                json.dumps(
                    manifest,
                    ensure_ascii=False,
                    sort_keys=True,
                    indent=2,
                    allow_nan=False,
                )
                + "\n"
            ).encode("utf-8"),
        }
        destination = Path(configuration.output_directory)
        destination.mkdir(parents=True, exist_ok=True)
        paths = {name: destination / name for name in payloads}
        self._persist(payloads, paths)
        return ScientificResultsArtifact(
            experiment_name=result.experiment_name,
            execution_count=result.execution_count,
            complete_csv_path=str(paths[filenames["complete_csv"]]),
            summary_csv_path=str(paths[filenames["summary_csv"]]),
            markdown_table_path=str(paths[filenames["markdown_table"]]),
            latex_table_path=str(paths[filenames["latex_table"]]),
            manifest_json_path=str(paths[filenames["manifest_json"]]),
            complete_row_count=len(rows),
            summary_row_count=len(rows),
            exported_columns=exported_columns,
            scientific_digest=digest,
            metadata=configuration.metadata,
        )

    @staticmethod
    def _validate_finite(rows: list[dict[str, object]]) -> None:
        def visit(value: object) -> None:
            if isinstance(value, float) and not math.isfinite(value):
                raise ValueError("scientific content must not contain NaN or infinity")
            if isinstance(value, Mapping):
                for item in value.values():
                    visit(item)
            elif isinstance(value, (list, tuple)):
                for item in value:
                    visit(item)

        visit(rows)

    @staticmethod
    def _sort_key(value: object) -> tuple[int, object]:
        if value is None:
            return (0, "")
        if isinstance(value, bool):
            return (1, value)
        if isinstance(value, (int, float)):
            return (2, value)
        if isinstance(value, str):
            return (3, value)
        return (4, _canonical_bytes(_thaw(value)).decode("utf-8"))

    @staticmethod
    def _csv(rows: list[dict[str, object]], columns: tuple[str, ...]) -> bytes:
        stream = io.StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: _csv_value(row[column]) for column in columns})
        return stream.getvalue().encode("utf-8")

    @classmethod
    def _markdown(cls, rows: list[dict[str, object]], places: int) -> bytes:
        lines = [
            "| " + " | ".join(_COMPARISON_COLUMNS) + " |",
            "| " + " | ".join("---" for _ in _COMPARISON_COLUMNS) + " |",
        ]
        for row in rows:
            values = [
                cls._escape_markdown(str(row[_COMPARISON_FIELDS[0]])),
                cls._escape_markdown(str(row[_COMPARISON_FIELDS[1]])),
                *(
                    cls._format_number(row[name], places)
                    for name in _COMPARISON_FIELDS[2:]
                ),
            ]
            lines.append("| " + " | ".join(values) + " |")
        return ("\n".join(lines) + "\n").encode("utf-8")

    @classmethod
    def _latex(cls, rows: list[dict[str, object]], places: int, prefix: str) -> bytes:
        header = " & ".join(cls._escape_latex(item) for item in _COMPARISON_COLUMNS)
        lines = [
            "\\begin{table}[htbp]",
            "\\centering",
            "\\caption{Test-partition model and calibration comparison.}",
            f"\\label{{tab:{cls._latex_label(prefix)}}}",
            "\\begin{tabular}{llrrrrrrrr}",
            "\\hline",
            f"{header} \\\\",
            "\\hline",
        ]
        for row in rows:
            values = [
                cls._escape_latex(str(row[_COMPARISON_FIELDS[0]])),
                cls._escape_latex(str(row[_COMPARISON_FIELDS[1]])),
                *(
                    cls._format_number(row[name], places)
                    for name in _COMPARISON_FIELDS[2:]
                ),
            ]
            lines.append(" & ".join(values) + " \\\\")
        lines.extend(("\\hline", "\\end{tabular}", "\\end{table}"))
        return ("\n".join(lines) + "\n").encode("utf-8")

    @staticmethod
    def _format_number(value: object, places: int) -> str:
        if value is None:
            return "N/A"
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError("comparison metrics must be numeric or missing")
        if not math.isfinite(float(value)):
            raise ValueError("comparison metrics must be finite")
        return f"{float(value):.{places}f}"

    @staticmethod
    def _escape_markdown(value: str) -> str:
        return value.replace("\\", "\\\\").replace("|", "\\|").replace("\n", "<br>")

    @staticmethod
    def _escape_latex(value: str) -> str:
        replacements = {
            "\\": r"\textbackslash{}",
            "&": r"\&",
            "%": r"\%",
            "$": r"\$",
            "#": r"\#",
            "_": r"\_",
            "{": r"\{",
            "}": r"\}",
            "~": r"\textasciitilde{}",
            "^": r"\textasciicircum{}",
        }
        return "".join(replacements.get(character, character) for character in value)

    @staticmethod
    def _latex_label(prefix: str) -> str:
        return re.sub(r"[^a-z0-9:-]+", "-", prefix.lower()).strip("-:")

    @staticmethod
    def _persist(payloads: dict[str, bytes], paths: dict[str, Path]) -> None:
        temporary: dict[str, Path] = {}
        backups: dict[str, Path] = {}
        installed: list[str] = []
        try:
            for name, payload in payloads.items():
                descriptor, temporary_name = tempfile.mkstemp(
                    dir=paths[name].parent,
                    prefix=f".{name}.",
                    suffix=".tmp",
                )
                temporary[name] = Path(temporary_name)
                with os.fdopen(descriptor, "wb") as stream:
                    stream.write(payload)
                    stream.flush()
                    os.fsync(stream.fileno())
            for name, path in paths.items():
                if path.exists():
                    descriptor, backup_name = tempfile.mkstemp(
                        dir=path.parent,
                        prefix=f".{name}.",
                        suffix=".backup",
                    )
                    os.close(descriptor)
                    backup = Path(backup_name)
                    backup.unlink()
                    os.replace(path, backup)
                    backups[name] = backup
            for name, path in paths.items():
                os.replace(temporary[name], path)
                temporary.pop(name)
                installed.append(name)
        except Exception:
            for name in reversed(installed):
                paths[name].unlink(missing_ok=True)
            for name, backup in backups.items():
                os.replace(backup, paths[name])
            raise
        finally:
            for path in temporary.values():
                path.unlink(missing_ok=True)
            for path in backups.values():
                path.unlink(missing_ok=True)
