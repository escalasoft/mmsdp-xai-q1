"""Framework-agnostic architectural abstraction for late fusion."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType

__all__ = ["LateFusionEngine"]


@dataclass(frozen=True, slots=True)
class LateFusionMetadata:
    """Immutable metadata describing a late-fusion engine."""

    fusion_name: str
    fusion_strategy: str
    input_modalities: tuple[str, ...]
    configuration: Mapping[str, object] = field(default_factory=dict)


class LateFusionEngine:
    """Architectural abstraction for late multimodal prediction fusion.

    Args:
        input_modalities: Modalities whose predictions are intended for fusion.
        fusion_strategy: Framework-independent identifier for the intended
            fusion strategy.
        configuration: Optional declarative fusion configuration.
    """

    def __init__(
        self,
        input_modalities: Sequence[str],
        *,
        fusion_strategy: str = "late-fusion",
        configuration: Mapping[str, object] | None = None,
    ) -> None:
        """Initialize a late-fusion engine with immutable metadata."""
        self._metadata = LateFusionMetadata(
            fusion_name=type(self).__name__,
            fusion_strategy=fusion_strategy,
            input_modalities=tuple(input_modalities),
            configuration=MappingProxyType(
                dict({} if configuration is None else configuration)
            ),
        )

    @property
    def metadata(self) -> LateFusionMetadata:
        """Return immutable metadata describing this fusion engine."""
        return self._metadata

    def combine(self, predictions: object, /) -> object:
        """Indicate that prediction fusion is not implemented."""
        raise NotImplementedError

    def validate_inputs(self, predictions: object, /) -> None:
        """Indicate that input validation is not implemented."""
        raise NotImplementedError
