"""Stacking foundation for framework-agnostic late fusion."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType

from fusion.contracts import PredictionOutput
from fusion.late_fusion import LateFusionEngine

__all__ = ["StackingFusionMetadata", "StackingFusion"]


@dataclass(frozen=True, slots=True)
class StackingFusionMetadata:
    """Immutable metadata describing a stacking fusion engine.

    Attributes:
        fusion_name: Concrete fusion engine class name.
        fusion_strategy: Framework-independent fusion strategy identifier.
        input_modalities: Modalities whose predictions are intended for fusion.
        configuration: Declarative configuration for the fusion engine.
    """

    fusion_name: str
    fusion_strategy: str
    input_modalities: tuple[str, ...]
    configuration: Mapping[str, object] = field(default_factory=dict)


class StackingFusion(LateFusionEngine):
    """Provide the architectural foundation for stacking-based late fusion.

    Args:
        input_modalities: Modalities whose predictions are intended for fusion.
        configuration: Optional declarative fusion configuration.

    Notes:
        Meta-model learning and prediction combination are intentionally
        deferred to a later implementation.
    """

    def __init__(
        self,
        input_modalities: Sequence[str],
        *,
        configuration: Mapping[str, object] | None = None,
    ) -> None:
        """Initialize the engine with an immutable metadata snapshot."""
        immutable_configuration = MappingProxyType(
            dict({} if configuration is None else configuration)
        )
        self._metadata = StackingFusionMetadata(
            fusion_name=type(self).__name__,
            fusion_strategy="stacking",
            input_modalities=tuple(input_modalities),
            configuration=immutable_configuration,
        )

    @property
    def metadata(self) -> StackingFusionMetadata:
        """Return immutable metadata describing this fusion engine."""
        return self._metadata

    def validate_inputs(self, predictions: Sequence[PredictionOutput], /) -> None:
        """Validate prediction compatibility for future stacking.

        Args:
            predictions: Modality prediction outputs in input order.

        Raises:
            ValueError: If there are no predictions, class labels differ, or
                probability vectors are incompatible with the class labels.
        """
        if not predictions:
            raise ValueError("at least one prediction is required")

        class_labels = tuple(predictions[0].class_labels)
        if any(
            tuple(prediction.class_labels) != class_labels
            for prediction in predictions[1:]
        ):
            raise ValueError("all predictions must share identical class_labels")

        for prediction in predictions:
            if not isinstance(prediction.probabilities, Sequence):
                raise ValueError("probabilities must be probability vectors")
            if len(prediction.probabilities) != len(class_labels):
                raise ValueError(
                    "each probability vector must match the number of class labels"
                )

    def combine(self, predictions: Sequence[PredictionOutput], /) -> PredictionOutput:
        """Indicate that stacking meta-model fusion is not implemented."""
        raise NotImplementedError
