"""Rule-based text feature generation from dataset records."""

from collections.abc import Iterable, Mapping

from .code_features import _required
from .schema import TextFeatureRecord


def generate_text_features(
    records: Iterable[Mapping[str, str]],
) -> tuple[TextFeatureRecord, ...]:
    """Count message structure exactly, without vocabulary or semantic inference."""
    features = []
    for record in records:
        commit_hash = _required(record, "commit_hash")
        message = _required(record, "commit_message")
        features.append(
            TextFeatureRecord(
                commit_hash=commit_hash,
                character_count=len(message),
                word_count=len(message.split()),
                line_count=len(message.splitlines()) or 1,
                non_whitespace_character_count=sum(
                    not character.isspace() for character in message
                ),
            )
        )
    return tuple(features)

