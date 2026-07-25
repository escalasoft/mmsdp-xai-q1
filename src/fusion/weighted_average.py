"""Weighted-average implementation of framework-agnostic late fusion."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from math import fsum, isclose
from numbers import Real
from types import MappingProxyType

from fusion.contracts import PredictionOutput
from fusion.late_fusion import LateFusionEngine

__all__ = ["WeightedAverageFusionMetadata", "WeightedAverageFusion"]


@dataclass(frozen=True, slots=True)
class WeightedAverageFusionMetadata:
    """Immutable metadata describing a weighted-average fusion engine.

    Attributes:
        fusion_name: Concrete fusion engine class name.
        fusion_strategy: Framework-independent fusion strategy identifier.
        input_modalities: Modalities whose predictions are combined.
        weights: Contribution assigned to each input modality.
        configuration: Declarative configuration for the fusion engine.
    """

    fusion_name: str
    fusion_strategy: str
    input_modalities: tuple[str, ...]
    weights: tuple[Real, ...]
    configuration: Mapping[str, object] = field(default_factory=dict)


class WeightedAverageFusion(LateFusionEngine):
    """Combine modality probability vectors using fixed scalar weights.

    Args:
        input_modalities: Modalities whose predictions are intended for fusion.
        weights: Weight corresponding to each prediction, in input order.
        configuration: Optional declarative fusion configuration.

    Notes:
        Weights are validated when predictions are combined. They are never
        normalized, calibrated, or otherwise transformed.
    """

    def __init__(
        self,
        input_modalities: Sequence[str],
        weights: Sequence[Real],
        *,
        configuration: Mapping[str, object] | None = None,
    ) -> None:
        """Initialize the engine with an immutable metadata snapshot."""
        immutable_configuration = MappingProxyType(
            dict({} if configuration is None else configuration)
        )
        self._metadata = WeightedAverageFusionMetadata(
            fusion_name=type(self).__name__,
            fusion_strategy="weighted-average",
            input_modalities=tuple(input_modalities),
            weights=tuple(weights),
            configuration=immutable_configuration,
        )

    @property
    def metadata(self) -> WeightedAverageFusionMetadata:
        """Return immutable metadata describing this fusion engine."""
        return self._metadata

    def validate_inputs(self, predictions: Sequence[PredictionOutput], /) -> None:
        """Validate predictions and the configured fusion weights.

        Args:
            predictions: Modality prediction outputs in weight order.

        Raises:
            ValueError: If there are no predictions, counts differ, a weight is
                non-numeric, weights do not sum to one, class labels differ, or
                probability vectors are incompatible with the class labels.
        """
        if not predictions:
            raise ValueError("at least one prediction is required")

        if len(self.metadata.weights) != len(predictions):
            raise ValueError(
                "weights length must equal the number of predictions "
                f"({len(self.metadata.weights)} != {len(predictions)})"
            )

        if any(
            isinstance(weight, bool) or not isinstance(weight, Real)
            for weight in self.metadata.weights
        ):
            raise ValueError("weights must be numeric")

        if not isclose(fsum(self.metadata.weights), 1.0):
            raise ValueError("weights must sum to one")

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
        """Return the weighted average of the supplied probability vectors.

        Args:
            predictions: Modality prediction outputs in weight order.

        Returns:
            A new multimodal prediction preserving the common class-label order.

        Raises:
            ValueError: If the predictions or configured weights are invalid.
        """
        self.validate_inputs(predictions)

        class_labels = tuple(predictions[0].class_labels)
        probabilities = tuple(
            fsum(
                weight * prediction.probabilities[class_index]
                for weight, prediction in zip(
                    self.metadata.weights, predictions, strict=True
                )
            )
            for class_index in range(len(class_labels))
        )

        return PredictionOutput(
            probabilities=probabilities,
            class_labels=class_labels,
            modality="MULTIMODAL",
            metadata=MappingProxyType(
                {
                    "fusion_name": self.metadata.fusion_name,
                    "fusion_strategy": self.metadata.fusion_strategy,
                    "input_modalities": self.metadata.input_modalities,
                    "weights": self.metadata.weights,
                    "configuration": self.metadata.configuration,
                }
            ),
        )
