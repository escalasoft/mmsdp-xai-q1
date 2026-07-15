"""Deterministic process feature generation from dataset records."""

from collections.abc import Iterable, Mapping

from .code_features import _required
from .schema import FeatureEngineeringError, ProcessFeatureRecord


def generate_process_features(
    records: Iterable[Mapping[str, str]],
) -> tuple[ProcessFeatureRecord, ...]:
    """Derive commit topology and identity-equality flags without history fitting."""
    features = []
    for record in records:
        commit_hash = _required(record, "commit_hash")
        try:
            parent_value = record["parent_commit_hashes"]
        except KeyError as error:
            raise FeatureEngineeringError(
                "Missing required field: parent_commit_hashes"
            ) from error
        if not isinstance(parent_value, str):
            raise FeatureEngineeringError(
                "Field must be a string: parent_commit_hashes"
            )
        parents = tuple(parent_value.split())
        author = _required(record, "author_identifier")
        committer = _required(record, "committer_identifier")
        features.append(
            ProcessFeatureRecord(
                commit_hash=commit_hash,
                parent_count=len(parents),
                is_merge_commit=int(len(parents) > 1),
                author_is_committer=int(author == committer),
            )
        )
    return tuple(features)
