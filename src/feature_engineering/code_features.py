"""Deterministic code-change feature generation from dataset records."""

from collections.abc import Iterable, Mapping

from .schema import CodeFeatureRecord, FeatureEngineeringError


def generate_code_features(
    records: Iterable[Mapping[str, str]],
) -> tuple[CodeFeatureRecord, ...]:
    """Create transparent line and file counts without scaling or fitting."""
    features = []
    for record in records:
        commit_hash = _required(record, "commit_hash")
        added = _non_negative_integer(record, "lines_added")
        deleted = _non_negative_integer(record, "lines_deleted")
        file_count = _non_negative_integer(record, "changed_file_count")
        features.append(
            CodeFeatureRecord(
                commit_hash=commit_hash,
                lines_added=added,
                lines_deleted=deleted,
                lines_changed=added + deleted,
                changed_file_count=file_count,
            )
        )
    return tuple(features)


def _required(record: Mapping[str, str], field: str) -> str:
    try:
        value = record[field]
    except KeyError as error:
        raise FeatureEngineeringError(f"Missing required field: {field}") from error
    if not isinstance(value, str) or not value:
        raise FeatureEngineeringError(f"Field must be a non-empty string: {field}")
    return value


def _non_negative_integer(record: Mapping[str, str], field: str) -> int:
    value = _required(record, field)
    try:
        number = int(value)
    except ValueError as error:
        raise FeatureEngineeringError(f"Field must be an integer: {field}") from error
    if number < 0:
        raise FeatureEngineeringError(f"Field must be non-negative: {field}")
    return number
