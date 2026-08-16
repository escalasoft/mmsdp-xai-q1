"""Fail-closed adapters for the frozen canonical JIT-Defects4J dataset.

This module prepares representations; it never trains or evaluates a predictor.
Ordinary development transformations deliberately cannot expose TEST.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PARTITIONS = ("train", "validation", "test")
DEVELOPMENT_PARTITIONS = ("train", "validation")
IDENTITY_FIELDS = ("project", "commit_hash")
EXPECTED_COUNTS = {"train": 19114, "validation": 4086, "test": 4119}
EXPECTED_TARGETS = {
    "train": {"positive": 1912, "nominal_negative": 17202},
    "validation": {"positive": 260, "nominal_negative": 3826},
    "test": {"positive": 160, "nominal_negative": 3959},
}
FORBIDDEN_PREDICTORS = {
    "target",
    "split",
    "project",
    "commit_hash",
    "classification",
    "label",
    "fix",
    "szz",
    "blame_output",
    "is_buggy_commit",
    "packaged_split",
    "bug_confidence",
    "has_bug_keyword",
    "msg_has_bug_kw",
}
_TOKEN = re.compile(r"(?u)\b[^\W_]{2,}\b")


class AdapterContractError(RuntimeError):
    """A scientific input, alignment, leakage, or lifecycle violation."""


def canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode()


def digest(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _identity(row: dict[str, Any]) -> tuple[str, str]:
    try:
        identity = (row["project"], row["commit_hash"])
    except KeyError as error:
        raise AdapterContractError("row lacks project-qualified identity") from error
    if not all(isinstance(value, str) and value for value in identity):
        raise AdapterContractError("identity fields must be non-empty strings")
    return identity


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        try:
            value = json.loads(line)
        except json.JSONDecodeError as error:
            raise AdapterContractError(
                f"malformed {path.name} line {number}"
            ) from error
        if not isinstance(value, dict):
            raise AdapterContractError(f"non-object {path.name} line {number}")
        rows.append(value)
    return rows


def _index(
    rows: list[dict[str, Any]], name: str
) -> dict[tuple[str, str], dict[str, Any]]:
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        identity = _identity(row)
        if identity in result:
            raise AdapterContractError(f"duplicate identity in {name}")
        result[identity] = row
    return result


@dataclass(frozen=True)
class FrozenInput:
    root: Path
    manifest: dict[str, Any]
    observations: tuple[dict[str, Any], ...]
    code: dict[tuple[str, str], dict[str, Any]]
    process: dict[tuple[str, str], dict[str, Any]]
    text: dict[tuple[str, str], dict[str, Any]]
    identities: dict[str, tuple[tuple[str, str], ...]]
    input_identity: str

    @classmethod
    def load(
        cls,
        root: Path,
        expected_manifest_sha256: str,
        expected_scientific_identity: str,
    ) -> FrozenInput:
        manifest_path = root / "manifest.json"
        if file_digest(manifest_path) != expected_manifest_sha256:
            raise AdapterContractError("canonical manifest SHA-256 mismatch")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("scientific_identity_digest") != expected_scientific_identity:
            raise AdapterContractError("canonical scientific identity mismatch")
        for name, entry in manifest.get("artifacts", {}).items():
            path = root / name
            if not path.is_file() or file_digest(path) != entry.get("sha256"):
                raise AdapterContractError(f"frozen artifact hash mismatch: {name}")
        observations = _read_jsonl(root / "observations.jsonl")
        indexes = {
            name: _index(_read_jsonl(root / f"{name}.jsonl"), name)
            for name in ("code", "process", "text")
        }
        observed = _index(observations, "observations")
        universe = set(observed)
        if any(set(index) != universe for index in indexes.values()):
            raise AdapterContractError("modality identity universe mismatch")
        identities: dict[str, list[tuple[str, str]]] = {name: [] for name in PARTITIONS}
        targets = {name: Counter() for name in PARTITIONS}
        for row in observations:
            split = row.get("split")
            target = row.get("target")
            if split not in PARTITIONS or target not in (0, 1):
                raise AdapterContractError("invalid frozen split or target")
            identities[split].append(_identity(row))
            targets[split][target] += 1
        if set().union(*(set(values) for values in identities.values())) != universe:
            raise AdapterContractError("split membership is not total")
        if sum(len(set(values)) for values in identities.values()) != len(universe):
            raise AdapterContractError("cross-split overlap or duplicate membership")
        for split in PARTITIONS:
            if len(identities[split]) != EXPECTED_COUNTS[split]:
                raise AdapterContractError(f"frozen {split} count mismatch")
            expected = EXPECTED_TARGETS[split]
            if (
                targets[split][1] != expected["positive"]
                or targets[split][0] != expected["nominal_negative"]
            ):
                raise AdapterContractError(
                    f"frozen {split} target distribution mismatch"
                )
        frozen_identities = {key: tuple(value) for key, value in identities.items()}
        identity_payload = {
            "scientific_identity": expected_scientific_identity,
            "manifest_sha256": expected_manifest_sha256,
            "ordered_membership": frozen_identities,
        }
        return cls(
            root,
            manifest,
            tuple(observations),
            indexes["code"],
            indexes["process"],
            indexes["text"],
            frozen_identities,
            digest(identity_payload),
        )


@dataclass(frozen=True)
class TextState:
    vocabulary: tuple[str, ...]
    document_frequencies: tuple[int, ...]
    inverse_document_frequencies: tuple[float, ...]
    training_document_count: int
    training_identity_digest: str
    configuration_digest: str
    state_digest: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "fit_partition": "train",
            "vocabulary": list(self.vocabulary),
            "document_frequencies": list(self.document_frequencies),
            "inverse_document_frequencies": list(self.inverse_document_frequencies),
            "training_document_count": self.training_document_count,
            "training_identity_digest": self.training_identity_digest,
            "configuration_digest": self.configuration_digest,
            "state_digest": self.state_digest,
        }


@dataclass(frozen=True)
class AdaptedPartition:
    name: str
    identities: tuple[tuple[str, str], ...]
    targets: tuple[int, ...]
    code: tuple[tuple[int, ...], ...]
    process: tuple[tuple[int, ...], ...]
    text_csr: dict[str, Any]
    scientific_digest: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "partition": self.name,
            "identities": self.identities,
            "targets": self.targets,
            "code": self.code,
            "process": self.process,
            "text_csr": self.text_csr,
            "scientific_digest": self.scientific_digest,
        }


class FinalEvaluationSeal:
    """Opaque capability issued only after all development decisions are frozen."""

    def __init__(self, decisions_digest: str) -> None:
        if not re.fullmatch(r"[0-9a-f]{64}", decisions_digest):
            raise ValueError("decisions_digest must be a SHA-256")
        self.decisions_digest = decisions_digest


class JITDefects4JAdapters:
    CODE_FEATURES = (
        "changed_file_count",
        "files_added",
        "files_deleted",
        "files_modified",
        "files_other",
        "mode_change_count",
    )
    PROCESS_FEATURES = (
        "parent_count",
        "is_merge_commit",
        "has_prior_history",
        "prior_project_commit_count",
    )

    def __init__(self, source: FrozenInput, configuration: dict[str, Any]) -> None:
        self.source = source
        self.configuration = configuration
        self.configuration_digest = digest(configuration)
        if tuple(configuration["code"]["features"]) != self.CODE_FEATURES:
            raise AdapterContractError("CODE configuration/schema mismatch")
        if tuple(configuration["process"]["features"]) != self.PROCESS_FEATURES:
            raise AdapterContractError("PROCESS configuration/schema mismatch")
        self._audit_schema()
        self.text_state: TextState | None = None

    def _audit_schema(self) -> None:
        names = set(self.CODE_FEATURES + self.PROCESS_FEATURES)
        names.add(self.configuration["text"]["source_field"])
        overlap = names.intersection(FORBIDDEN_PREDICTORS)
        if overlap:
            raise AdapterContractError(f"leakage-prone predictors: {sorted(overlap)}")

    def fit(self, partition: str = "train") -> TextState:
        if partition != "train":
            raise AdapterContractError("learned adapter state may fit TRAIN only")
        identities = self.source.identities["train"]
        messages = [self.source.text[item]["raw_commit_message"] for item in identities]
        if any(not isinstance(value, str) for value in messages):
            raise AdapterContractError("TEXT contains a non-string message")
        config = self.configuration["text"]
        frequency: Counter[str] = Counter()
        for message in messages:
            tokens = {token.lower() for token in _TOKEN.findall(message)}
            frequency.update(tokens)
        selected = [
            (token, count)
            for token, count in frequency.items()
            if count >= config["minimum_document_frequency"]
        ]
        selected.sort(key=lambda item: (-item[1], item[0]))
        selected = selected[: config["maximum_features"]]
        if not selected:
            raise AdapterContractError("TRAIN TEXT produced an empty vocabulary")
        vocabulary = tuple(token for token, _ in selected)
        dfs = tuple(count for _, count in selected)
        idfs = tuple(
            float(math.log((1 + len(messages)) / (1 + count)) + 1.0) for count in dfs
        )
        content = {
            "fit_partition": "train",
            "vocabulary": vocabulary,
            "document_frequencies": dfs,
            "inverse_document_frequencies": idfs,
            "training_document_count": len(messages),
            "training_identity_digest": digest(identities),
            "configuration_digest": self.configuration_digest,
        }
        self.text_state = TextState(
            vocabulary,
            dfs,
            idfs,
            len(messages),
            digest(identities),
            self.configuration_digest,
            digest(content),
        )
        return self.text_state

    def transform(self, partition: str) -> AdaptedPartition:
        if partition not in DEVELOPMENT_PARTITIONS:
            raise AdapterContractError("TEST is sealed from development transformation")
        return self._transform(partition)

    def transform_test(self, seal: FinalEvaluationSeal) -> AdaptedPartition:
        if not isinstance(seal, FinalEvaluationSeal):
            raise AdapterContractError("explicit final-evaluation seal required")
        return self._transform("test")

    def _transform(self, partition: str) -> AdaptedPartition:
        if self.text_state is None:
            raise AdapterContractError("TEXT adapter must be fitted on TRAIN first")
        identities = self.source.identities[partition]
        observations = {_identity(row): row for row in self.source.observations}
        targets = tuple(observations[item]["target"] for item in identities)
        code_rows = []
        process_rows = []
        messages = []
        for item in identities:
            code = self.source.code[item]
            changes = code.get("file_changes")
            if not isinstance(changes, list):
                raise AdapterContractError("CODE file_changes must be a list")
            mode_changes = sum(
                change.get("old_mode") != change.get("new_mode") for change in changes
            )
            code_rows.append(
                (
                    len(changes),
                    *(code[name] for name in self.CODE_FEATURES[1:-1]),
                    mode_changes,
                )
            )
            process = self.source.process[item]
            process_rows.append(tuple(process[name] for name in self.PROCESS_FEATURES))
            messages.append(self.source.text[item]["raw_commit_message"])
        if any(
            type(value) is not int or value < 0
            for row in code_rows + process_rows
            for value in row
        ):
            raise AdapterContractError("numeric modality value violates domain")
        csr = self._text_csr(messages)
        content = {
            "partition": partition,
            "identities": identities,
            "targets": targets,
            "code": code_rows,
            "process": process_rows,
            "text_csr": csr,
            "source_input_identity": self.source.input_identity,
            "text_state_digest": self.text_state.state_digest,
        }
        return AdaptedPartition(
            partition,
            identities,
            targets,
            tuple(code_rows),
            tuple(process_rows),
            csr,
            digest(content),
        )

    def _text_csr(self, messages: list[str]) -> dict[str, Any]:
        assert self.text_state is not None
        lookup = {
            token: index for index, token in enumerate(self.text_state.vocabulary)
        }
        indptr = [0]
        indices: list[int] = []
        data: list[float] = []
        for message in messages:
            counts = Counter(
                lookup[token.lower()]
                for token in _TOKEN.findall(message)
                if token.lower() in lookup
            )
            weighted = [
                (
                    index,
                    (1.0 + math.log(count))
                    * self.text_state.inverse_document_frequencies[index],
                )
                for index, count in sorted(counts.items())
            ]
            norm = math.sqrt(sum(value * value for _, value in weighted))
            if norm:
                indices.extend(index for index, _ in weighted)
                data.extend(float(value / norm) for _, value in weighted)
            indptr.append(len(indices))
        content = {
            "shape": [len(messages), len(self.text_state.vocabulary)],
            "indptr": indptr,
            "indices": indices,
            "data": data,
        }
        content["scientific_digest"] = digest(content)
        return content


def load_configuration(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("fit_partition") != "train":
        raise AdapterContractError("adapter configuration is not TRAIN-only")
    return value
