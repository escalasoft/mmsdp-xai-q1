"""Deterministic classifiers required by the frozen Qt candidate policy."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping

__all__ = [
    "QtCommentLineClassifier",
    "QtFormattingOnlyClassifier",
]


_WHITESPACE_CODE_POINTS = frozenset(
    {
        0x0009,
        0x000A,
        0x000B,
        0x000C,
        0x000D,
        0x0020,
        0x0085,
        0x00A0,
        0x1680,
        0x2000,
        0x2001,
        0x2002,
        0x2003,
        0x2004,
        0x2005,
        0x2006,
        0x2007,
        0x2008,
        0x2009,
        0x200A,
        0x2028,
        0x2029,
        0x202F,
        0x205F,
        0x3000,
    }
)


def _whitespace_identity() -> tuple[str, ...]:
    return tuple(f"U+{value:04X}" for value in sorted(_WHITESPACE_CODE_POINTS))


def _is_whitespace(value: str) -> bool:
    return ord(value) in _WHITESPACE_CODE_POINTS


def _remove_whitespace(value: str) -> str:
    return "".join(character for character in value if not _is_whitespace(character))


class _ClassifierIdentity:
    version: str

    @classmethod
    def scientific_semantics(cls) -> Mapping[str, object]:
        raise NotImplementedError

    @classmethod
    def canonical_scientific_content(cls) -> bytes:
        """Return implementation-independent scientific semantics as UTF-8 JSON."""
        content = {
            "classifier_version": cls.version,
            "scientific_semantics": cls.scientific_semantics(),
        }
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

    @classmethod
    def identity_digest(cls) -> str:
        return hashlib.sha256(cls.canonical_scientific_content()).hexdigest()

    @classmethod
    def verify_identity(cls, version: str, digest: str) -> None:
        actual = cls.identity_digest()
        if version != cls.version or digest != actual:
            raise ValueError(
                f"classifier identity mismatch for {cls.version}: expected "
                f"{version}/{digest}, computed {cls.version}/{actual}"
            )


class QtCommentLineClassifier(_ClassifierIdentity):
    """Classify C/C++/Objective-C++/QML comment-only source lines."""

    version = "qt-comment-line-classification-contract-1.0.0"

    @classmethod
    def scientific_semantics(cls) -> Mapping[str, object]:
        return {
            "classification_unit": "ordered-source-lines-without-line-terminators",
            "comment_delimiters": {
                "block_close": "*/",
                "block_open": "/*",
                "line": "//",
            },
            "comment_only_rule": (
                "line-contains-comment-token-or-block-comment-content-and-contains-"
                "no-non-whitespace-content-outside-comments"
            ),
            "empty_line_rule": "not-comment-only-classified-separately-as-blank",
            "lexical_precedence": (
                "block-comment-state-then-quoted-content-then-comment-delimiters-"
                "then-other-content"
            ),
            "quote_delimiters": ["single-quote", "double-quote"],
            "quote_escape_rule": "backslash-escapes-next-code-point-within-quote",
            "quote_state_scope": "one-source-line",
            "quoted_comment_delimiter_rule": "treated-as-code-not-comment",
            "state_rule": "block-comment-state-carries-across-source-lines",
            "trailing_comment_rule": (
                "line-with-code-before-comment-is-not-comment-only"
            ),
            "whitespace_code_points": _whitespace_identity(),
        }

    @staticmethod
    def comment_only_line_numbers(lines: tuple[str, ...]) -> frozenset[int]:
        result: set[int] = set()
        in_block = False
        for number, line in enumerate(lines, 1):
            index = 0
            has_code = False
            has_comment = in_block
            quote: str | None = None
            escaped = False
            while index < len(line):
                char = line[index]
                following = line[index + 1] if index + 1 < len(line) else ""
                if in_block:
                    has_comment = True
                    if char == "*" and following == "/":
                        in_block = False
                        index += 2
                    else:
                        index += 1
                    continue
                if quote is not None:
                    has_code = True
                    if escaped:
                        escaped = False
                    elif char == "\\":
                        escaped = True
                    elif char == quote:
                        quote = None
                    index += 1
                    continue
                if char in {'"', "'"}:
                    quote = char
                    has_code = True
                    index += 1
                elif char == "/" and following == "/":
                    has_comment = True
                    break
                elif char == "/" and following == "*":
                    has_comment = True
                    in_block = True
                    index += 2
                else:
                    if not _is_whitespace(char):
                        has_code = True
                    index += 1
            if has_comment and not has_code:
                result.add(number)
        return frozenset(result)


class QtFormattingOnlyClassifier(_ClassifierIdentity):
    """Detect replacements that differ only in Unicode whitespace."""

    version = "qt-formatting-only-classification-contract-1.0.0"

    @classmethod
    def scientific_semantics(cls) -> Mapping[str, object]:
        return {
            "comparison_scope": (
                "deleted-line-against-each-added-line-in-same-diff-hunk"
            ),
            "empty_normalized_deleted_line_rule": "not-formatting-only",
            "equivalence_rule": (
                "formatting-only-if-nonempty-normalized-deleted-line-equals-at-least-"
                "one-normalized-added-line"
            ),
            "normalization_rule": "remove-all-listed-whitespace-code-points",
            "order_rule": "preserve-order-of-all-non-whitespace-code-points",
            "whitespace_code_points": _whitespace_identity(),
        }

    @staticmethod
    def is_formatting_only(deleted_line: str, added_lines: tuple[str, ...]) -> bool:
        normalized = _remove_whitespace(deleted_line)
        return bool(normalized) and any(
            normalized == _remove_whitespace(line) for line in added_lines
        )
