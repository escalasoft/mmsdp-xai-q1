"""Train-only Qt text representation and numeric model-input preparation.

This boundary consumes the frozen post-split Qt modality inputs.  It does not
split observations, inspect targets while fitting, or train a predictive model.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
from types import MappingProxyType

from dataset.model_input import ModelPartitionInput, PreparedModelInput
from dataset.qt_model_input_adaptation import (
    QT_PROCESS_FEATURE_NAMES,
    QT_TEXT_FEATURE_NAMES,
    QtModelInputAdaptationResult,
)
from feature_engineering.qt_feature_construction import QT_CODE_FEATURE_NAMES

__all__ = [
    "QtModelReadyPreparationError",
    "QtTextRepresentationPolicy",
    "QtTextRepresentationState",
    "DenseNumericMatrix",
    "SparseNumericMatrix",
    "QtNumericPartition",
    "QtModelReadyPreparation",
    "prepare_qt_model_ready_inputs",
]

_PARTITIONS = ("train", "validation", "test")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_TOKEN = re.compile(r"(?u)\b[^\W_]{2,}\b")
_EMBEDDED_PROVENANCE = re.compile(
    r"https?://\S+|\b\S+@\S+\b|\b[0-9a-fA-F]{40,64}\b|\b[A-Z][A-Z0-9]+-[0-9]+\b"
)
_FORBIDDEN = re.compile(
    r"(^|_)(bug_confidence|fix_keyword_indicator|has_bug_keyword|msg_has_bug_kw)($|_)"
    r"|(^|_)(commit_identifier|committed_at|partition|target|issue|candidate|szz)($|_)"
)


class QtModelReadyPreparationError(RuntimeError):
    """A fail-closed violation of the Qt model-ready preparation boundary."""


def _thaw(value: object) -> object:
    if is_dataclass(value) and not isinstance(value, type):
        return {item.name: _thaw(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    if isinstance(value, Enum):
        return value.value
    return value


def _digest(value: object) -> str:
    payload = json.dumps(
        _thaw(value),
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _require_digest(value: object, name: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")
    return value


def _freeze_mapping(value: Mapping[str, object]) -> Mapping[str, object]:
    return MappingProxyType({key: _freeze(item) for key, item in value.items()})


def _freeze(value: object) -> object:
    if isinstance(value, Mapping):
        return _freeze_mapping(value)
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    return value


def _numeric(value: object) -> bool:
    return type(value) is int or (type(value) is float and math.isfinite(value))


@dataclass(frozen=True, slots=True)
class QtTextRepresentationPolicy:
    """Frozen target-independent unigram TF-IDF baseline policy."""

    policy_version: str = "qt-text-tfidf-policy-1.0.0"
    source_field: str = "raw_commit_message"
    text_scope: str = "first-non-empty-subject-line"
    analyzer: str = "unicode-word-unigrams"
    lowercase: bool = True
    token_pattern: str = r"(?u)\b[^\W_]{2,}\b"
    embedded_provenance_policy: str = (
        "remove-url-email-git-object-and-issue-identifiers"
    )
    minimum_document_frequency: int = 2
    maximum_features: int = 5000
    vocabulary_order: str = "descending-train-document-frequency-then-token"
    weighting: str = "sublinear-tf-smooth-idf-l2"
    fit_partition: str = "train"
    transform_partitions: tuple[str, ...] = ("validation", "test")
    policy_digest: str = ""

    def __post_init__(self) -> None:
        content = self.to_dict()
        content.pop("policy_digest")
        if content != self.scientific_values():
            raise ValueError("text representation policy does not match frozen values")
        if self.policy_digest != self.calculate_digest():
            raise ValueError("policy_digest must identify the frozen policy")

    @staticmethod
    def scientific_values() -> dict[str, object]:
        return {
            "policy_version": "qt-text-tfidf-policy-1.0.0",
            "source_field": "raw_commit_message",
            "text_scope": "first-non-empty-subject-line",
            "analyzer": "unicode-word-unigrams",
            "lowercase": True,
            "token_pattern": r"(?u)\b[^\W_]{2,}\b",
            "embedded_provenance_policy": (
                "remove-url-email-git-object-and-issue-identifiers"
            ),
            "minimum_document_frequency": 2,
            "maximum_features": 5000,
            "vocabulary_order": "descending-train-document-frequency-then-token",
            "weighting": "sublinear-tf-smooth-idf-l2",
            "fit_partition": "train",
            "transform_partitions": ["validation", "test"],
        }

    @classmethod
    def create(cls) -> QtTextRepresentationPolicy:
        return cls(policy_digest=cls.calculate_digest())

    @classmethod
    def calculate_digest(cls) -> str:
        return _digest(cls.scientific_values())

    def to_dict(self) -> dict[str, object]:
        return _thaw(self)  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class QtTextRepresentationState:
    """The complete learned state fitted from TRAIN messages only."""

    state_version: str
    policy_digest: str
    fit_partition: str
    training_document_count: int
    training_corpus_digest: str
    vocabulary: tuple[str, ...]
    document_frequencies: tuple[int, ...]
    inverse_document_frequencies: tuple[float, ...]
    state_digest: str

    def __post_init__(self) -> None:
        if self.state_version != "qt-train-fitted-tfidf-state-1.0.0":
            raise ValueError("unsupported text state version")
        _require_digest(self.policy_digest, "policy_digest")
        _require_digest(self.training_corpus_digest, "training_corpus_digest")
        if self.fit_partition != "train":
            raise ValueError("text state may only be fitted on train")
        if (
            type(self.training_document_count) is not int
            or self.training_document_count <= 0
        ):
            raise ValueError("training_document_count must be positive")
        size = len(self.vocabulary)
        if not size or len(set(self.vocabulary)) != size:
            raise ValueError("vocabulary must be non-empty and unique")
        if (
            len(self.document_frequencies) != size
            or len(self.inverse_document_frequencies) != size
        ):
            raise ValueError("learned text state arrays must align")
        if any(
            type(item) is not int or item <= 0
            for item in self.document_frequencies
        ):
            raise ValueError("document frequencies must be positive integers")
        if any(
            type(item) is not float or not math.isfinite(item)
            for item in self.inverse_document_frequencies
        ):
            raise ValueError("inverse document frequencies must be finite floats")
        expected = _digest(self._content())
        if self.state_digest != expected:
            raise ValueError("state_digest must identify the fitted TRAIN state")

    def _content(self) -> dict[str, object]:
        return {
            item.name: getattr(self, item.name)
            for item in fields(self)
            if item.name != "state_digest"
        }

    @property
    def feature_names(self) -> tuple[str, ...]:
        return tuple(f"tfidf:{token}" for token in self.vocabulary)

    def to_dict(self) -> dict[str, object]:
        return _thaw(self)  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class DenseNumericMatrix:
    rows: tuple[tuple[int | float, ...], ...]
    column_count: int
    matrix_digest: str

    def __post_init__(self) -> None:
        if (
            type(self.column_count) is not int
            or self.column_count <= 0
            or not self.rows
        ):
            raise ValueError("dense matrix dimensions must be positive")
        if any(len(row) != self.column_count for row in self.rows):
            raise ValueError("dense matrix rows must have the declared width")
        if any(not _numeric(value) for row in self.rows for value in row):
            raise ValueError("dense predictor matrices must be numeric and finite")
        content = {"rows": self.rows, "column_count": self.column_count}
        if self.matrix_digest != _digest(content):
            raise ValueError("matrix_digest must identify dense matrix content")

    @classmethod
    def create(
        cls, rows: Sequence[Sequence[int | float]], column_count: int
    ) -> DenseNumericMatrix:
        frozen = tuple(tuple(row) for row in rows)
        content = {"rows": frozen, "column_count": column_count}
        return cls(frozen, column_count, _digest(content))

    @property
    def row_count(self) -> int:
        return len(self.rows)

    def to_dict(self) -> dict[str, object]:
        return _thaw(self)  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class SparseNumericMatrix:
    """Canonical compressed-sparse-row numeric matrix."""

    row_count: int
    column_count: int
    indptr: tuple[int, ...]
    indices: tuple[int, ...]
    data: tuple[float, ...]
    matrix_digest: str

    def __post_init__(self) -> None:
        if type(self.row_count) is not int or self.row_count <= 0:
            raise ValueError("row_count must be positive")
        if type(self.column_count) is not int or self.column_count <= 0:
            raise ValueError("column_count must be positive")
        if len(self.indptr) != self.row_count + 1 or self.indptr[0] != 0:
            raise ValueError("CSR indptr is malformed")
        if self.indptr[-1] != len(self.indices) or len(self.indices) != len(self.data):
            raise ValueError("CSR arrays must align")
        if any(a > b for a, b in zip(self.indptr, self.indptr[1:])):
            raise ValueError("CSR indptr must be monotonic")
        if any(
            type(item) is not int or not 0 <= item < self.column_count
            for item in self.indices
        ):
            raise ValueError("CSR indices are invalid")
        for start, end in zip(self.indptr, self.indptr[1:]):
            if tuple(sorted(self.indices[start:end])) != self.indices[start:end]:
                raise ValueError("CSR row indices must be sorted")
        if any(
            type(item) is not float or not math.isfinite(item) for item in self.data
        ):
            raise ValueError("CSR values must be finite floats")
        if self.matrix_digest != _digest(self._content()):
            raise ValueError("matrix_digest must identify sparse matrix content")

    def _content(self) -> dict[str, object]:
        return {
            "row_count": self.row_count,
            "column_count": self.column_count,
            "indptr": self.indptr,
            "indices": self.indices,
            "data": self.data,
        }

    def to_dict(self) -> dict[str, object]:
        return _thaw(self)  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class QtNumericPartition:
    partition_name: str
    identifiers: tuple[object, ...]
    y: tuple[object, ...]
    code: DenseNumericMatrix
    process: DenseNumericMatrix
    text: SparseNumericMatrix

    def __post_init__(self) -> None:
        if self.partition_name not in _PARTITIONS:
            raise ValueError("unexpected partition name")
        count = len(self.identifiers)
        if not count or len(set(self.identifiers)) != count or len(self.y) != count:
            raise ValueError(
                "identifiers and targets must be non-empty, unique, and aligned"
            )
        if any(
            matrix.row_count != count
            for matrix in (self.code, self.process, self.text)
        ):
            raise ValueError("all modality matrices must align by row")

    @property
    def observation_count(self) -> int:
        return len(self.identifiers)

    def to_dict(self) -> dict[str, object]:
        return _thaw(self)  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class QtModelReadyPreparation:
    preparation_version: str
    source_model_input_identity_digest: str
    source_model_input_specification_digest: str
    representation_policy: QtTextRepresentationPolicy
    text_state: QtTextRepresentationState
    code_feature_names: tuple[str, ...]
    process_feature_names: tuple[str, ...]
    text_feature_names: tuple[str, ...]
    train: QtNumericPartition
    validation: QtNumericPartition
    test: QtNumericPartition
    fit_audit: Mapping[str, object]
    validation_audit: Mapping[str, object]
    preparation_identity_digest: str

    def __post_init__(self) -> None:
        if self.preparation_version != "qt-model-ready-preparation-1.0.0":
            raise ValueError("unsupported preparation version")
        _require_digest(
            self.source_model_input_identity_digest,
            "source_model_input_identity_digest",
        )
        _require_digest(
            self.source_model_input_specification_digest,
            "source_model_input_specification_digest",
        )
        if self.text_state.policy_digest != self.representation_policy.policy_digest:
            raise ValueError("text state and policy disagree")
        if (
            self.code_feature_names != QT_CODE_FEATURE_NAMES
            or self.process_feature_names != QT_PROCESS_FEATURE_NAMES
        ):
            raise ValueError("CODE and PROCESS schemas must remain frozen")
        if self.text_feature_names != self.text_state.feature_names:
            raise ValueError("TEXT feature names must derive from fitted state")
        numeric_names = self.code_feature_names + self.process_feature_names
        if any(_FORBIDDEN.search(name.lower()) for name in numeric_names):
            raise ValueError("forbidden predictor leakage field")
        if tuple(self.fit_audit.get("fit_partitions", ())) != ("train",):
            raise ValueError("fit audit must prove TRAIN-only fitting")
        if tuple(self.fit_audit.get("transform_only_partitions", ())) != (
            "validation",
            "test",
        ):
            raise ValueError("fit audit must prove transform-only validation/test")
        if self.validation_audit.get("identifiers_aligned") is not True:
            raise ValueError("validation audit must prove identifier alignment")
        if self.validation_audit.get("targets_aligned") is not True:
            raise ValueError("validation audit must prove target alignment")
        if self.validation_audit.get("schemas_validated") is not True:
            raise ValueError("validation audit must prove exact schemas")
        for partition in (self.train, self.validation, self.test):
            if partition.code.column_count != len(self.code_feature_names):
                raise ValueError("CODE matrix schema mismatch")
            if partition.process.column_count != len(self.process_feature_names):
                raise ValueError("PROCESS matrix schema mismatch")
            if partition.text.column_count != len(self.text_feature_names):
                raise ValueError("TEXT matrix schema mismatch")
        if self.preparation_identity_digest != _digest(self._identity_content()):
            raise ValueError("preparation_identity_digest is inconsistent")
        object.__setattr__(self, "fit_audit", _freeze_mapping(self.fit_audit))
        object.__setattr__(
            self, "validation_audit", _freeze_mapping(self.validation_audit)
        )

    def _identity_content(self) -> dict[str, object]:
        return {
            item.name: getattr(self, item.name)
            for item in fields(self)
            if item.name != "preparation_identity_digest"
        }

    @property
    def partition_counts(self) -> Mapping[str, int]:
        return MappingProxyType(
            {name: getattr(self, name).observation_count for name in _PARTITIONS}
        )

    def to_dict(self) -> dict[str, object]:
        result = _thaw(self)
        result["partition_counts"] = dict(self.partition_counts)
        return result  # type: ignore[return-value]


def _messages(partition: ModelPartitionInput) -> tuple[str, ...]:
    if partition.feature_names != QT_TEXT_FEATURE_NAMES:
        raise QtModelReadyPreparationError(
            "TEXT source schema is not frozen raw_commit_message"
        )
    result: list[str] = []
    for row in partition.X:
        if len(row) != 1 or not isinstance(row[0], str):
            raise QtModelReadyPreparationError(
                "TEXT source rows must contain one Python string"
            )
        result.append(row[0])
    return tuple(result)


def _tokens(message: str) -> tuple[str, ...]:
    subject = next((line.strip() for line in message.splitlines() if line.strip()), "")
    without_provenance = _EMBEDDED_PROVENANCE.sub(" ", subject)
    return tuple(_TOKEN.findall(without_provenance.lower()))


def _fit_text(
    messages: tuple[str, ...], policy: QtTextRepresentationPolicy
) -> QtTextRepresentationState:
    document_frequency: Counter[str] = Counter()
    for message in messages:
        document_frequency.update(set(_tokens(message)))
    eligible = [
        (token, count)
        for token, count in document_frequency.items()
        if count >= policy.minimum_document_frequency
    ]
    eligible.sort(key=lambda item: (-item[1], item[0]))
    selected = eligible[: policy.maximum_features]
    if not selected:
        raise QtModelReadyPreparationError("TRAIN text yields an empty vocabulary")
    vocabulary = tuple(token for token, _ in selected)
    frequencies = tuple(count for _, count in selected)
    count = len(messages)
    idf = tuple(
        float(math.log((1 + count) / (1 + value)) + 1.0)
        for value in frequencies
    )
    content = {
        "state_version": "qt-train-fitted-tfidf-state-1.0.0",
        "policy_digest": policy.policy_digest,
        "fit_partition": "train",
        "training_document_count": count,
        "training_corpus_digest": _digest({"ordered_messages": messages}),
        "vocabulary": vocabulary,
        "document_frequencies": frequencies,
        "inverse_document_frequencies": idf,
    }
    return QtTextRepresentationState(**content, state_digest=_digest(content))


def _transform_text(
    messages: tuple[str, ...], state: QtTextRepresentationState
) -> SparseNumericMatrix:
    lookup = {token: index for index, token in enumerate(state.vocabulary)}
    indptr = [0]
    indices: list[int] = []
    data: list[float] = []
    for message in messages:
        counts = Counter(
            index
            for token in _tokens(message)
            if (index := lookup.get(token)) is not None
        )
        weighted = [
            (
                index,
                (1.0 + math.log(count))
                * state.inverse_document_frequencies[index],
            )
            for index, count in sorted(counts.items())
        ]
        norm = math.sqrt(sum(value * value for _, value in weighted))
        if norm:
            indices.extend(index for index, _ in weighted)
            data.extend(float(value / norm) for _, value in weighted)
        indptr.append(len(indices))
    content = {
        "row_count": len(messages),
        "column_count": len(state.vocabulary),
        "indptr": tuple(indptr),
        "indices": tuple(indices),
        "data": tuple(data),
    }
    return SparseNumericMatrix(**content, matrix_digest=_digest(content))


def _validate_source(source: QtModelInputAdaptationResult) -> None:
    if not isinstance(source, QtModelInputAdaptationResult):
        raise TypeError("source must be a QtModelInputAdaptationResult")
    expected_identity = QtModelInputAdaptationResult.calculate_identity(
        source.specification, source.policy, source.code, source.process, source.text
    )
    if source.adaptation_identity_digest != expected_identity:
        raise QtModelReadyPreparationError(
            "source model-input identity binding is invalid"
        )
    numeric_modalities = (
        (source.code, QT_CODE_FEATURE_NAMES),
        (source.process, QT_PROCESS_FEATURE_NAMES),
    )
    for modality, expected in numeric_modalities:
        if modality.feature_names != expected:
            raise QtModelReadyPreparationError(
                "numeric source schema differs from frozen schema"
            )
    for name in _PARTITIONS:
        modalities = (source.code, source.process, source.text)
        partitions = tuple(getattr(item, name) for item in modalities)
        if any(
            item.identifiers != partitions[0].identifiers for item in partitions[1:]
        ):
            raise QtModelReadyPreparationError(
                "cross-modality identifiers are not aligned"
            )
        if any(item.y != partitions[0].y for item in partitions[1:]):
            raise QtModelReadyPreparationError("cross-modality targets are not aligned")
        for partition in partitions[:2]:
            if any(not _numeric(value) for row in partition.X for value in row):
                raise QtModelReadyPreparationError(
                    "CODE and PROCESS must remain numeric and finite"
                )


def prepare_qt_model_ready_inputs(
    source: QtModelInputAdaptationResult,
    policy: QtTextRepresentationPolicy | None = None,
) -> QtModelReadyPreparation:
    """Fit TEXT on TRAIN and transform the frozen partitions without resplitting."""
    _validate_source(source)
    representation_policy = policy or QtTextRepresentationPolicy.create()
    if not isinstance(representation_policy, QtTextRepresentationPolicy):
        raise TypeError("policy must be a QtTextRepresentationPolicy")
    text_messages = {
        name: _messages(getattr(source.text, name)) for name in _PARTITIONS
    }
    state = _fit_text(text_messages["train"], representation_policy)
    text_matrices = {
        name: _transform_text(text_messages[name], state) for name in _PARTITIONS
    }

    partitions: dict[str, QtNumericPartition] = {}
    for name in _PARTITIONS:
        code = getattr(source.code, name)
        process = getattr(source.process, name)
        partitions[name] = QtNumericPartition(
            partition_name=name,
            identifiers=code.identifiers,
            y=code.y,
            code=DenseNumericMatrix.create(code.X, len(QT_CODE_FEATURE_NAMES)),
            process=DenseNumericMatrix.create(process.X, len(QT_PROCESS_FEATURE_NAMES)),
            text=text_matrices[name],
        )
    values = {
        "preparation_version": "qt-model-ready-preparation-1.0.0",
        "source_model_input_identity_digest": source.adaptation_identity_digest,
        "source_model_input_specification_digest": (
            source.specification.specification_digest
        ),
        "representation_policy": representation_policy,
        "text_state": state,
        "code_feature_names": QT_CODE_FEATURE_NAMES,
        "process_feature_names": QT_PROCESS_FEATURE_NAMES,
        "text_feature_names": state.feature_names,
        "train": partitions["train"],
        "validation": partitions["validation"],
        "test": partitions["test"],
        "fit_audit": {
            "fit_partitions": ("train",),
            "transform_only_partitions": ("validation", "test"),
            "target_values_consumed_by_text_fit": False,
            "resplitting_performed": False,
            "model_training_performed": False,
        },
        "validation_audit": {
            "identifiers_aligned": True,
            "targets_aligned": True,
            "schemas_validated": True,
            "partition_counts": {
                name: partitions[name].observation_count for name in _PARTITIONS
            },
        },
    }
    return QtModelReadyPreparation(
        **values, preparation_identity_digest=_digest(values)
    )
