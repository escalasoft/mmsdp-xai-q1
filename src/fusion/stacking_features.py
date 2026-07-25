"""Framework-agnostic construction of stacking meta-features."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType

from fusion.contracts import PredictionOutput

__all__ = ["StackingFeaturesMetadata", "StackingFeatureBuilder"]


@dataclass(frozen=True, slots=True)
class StackingFeaturesMetadata:
    """Immutable metadata describing a stacking feature builder.

    Attributes:
        input_modalities: Modalities whose probabilities form the features.
        feature_names: Deterministic names for the flattened probabilities.
        configuration: Declarative configuration for feature construction.
    """

    input_modalities: tuple[str, ...]
    feature_names: tuple[str, ...]
    configuration: Mapping[str, object] = field(default_factory=dict)


class StackingFeatureBuilder:
    """Transform modality probability vectors into stacking meta-features.

    Args:
        input_modalities: Modalities whose predictions will form the features.
        class_labels: Class-label order used by every modality prediction.
        configuration: Optional declarative feature-building configuration.

    Notes:
        Features are ordered first by modality and then by class label. Each
        call builds the single feature-matrix row represented by the supplied
        modality predictions.
    """

    def __init__(
        self,
        input_modalities: Sequence[str],
        class_labels: Sequence[object] | None = None,
        *,
        configuration: Mapping[str, object] | None = None,
    ) -> None:
        """Initialize the builder with an immutable metadata snapshot."""
        modalities = tuple(input_modalities)
        labels = None if class_labels is None else tuple(class_labels)
        self._class_labels = labels
        self._metadata = StackingFeaturesMetadata(
            input_modalities=modalities,
            feature_names=(
                ()
                if labels is None
                else tuple(
                    f"{modality}__{label}"
                    for modality in modalities
                    for label in labels
                )
            ),
            configuration=MappingProxyType(
                dict({} if configuration is None else configuration)
            ),
        )

    @property
    def metadata(self) -> StackingFeaturesMetadata:
        """Return immutable metadata describing the generated features."""
        return self._metadata

    def validate_inputs(self, predictions: Sequence[PredictionOutput], /) -> None:
        """Validate prediction compatibility for feature construction.

        Args:
            predictions: Modality prediction outputs in feature order.

        Raises:
            ValueError: If there are no predictions, class labels differ, or
                probability vectors are incompatible with the class labels.
        """
        if not predictions:
            raise ValueError("at least one prediction is required")

        class_labels = tuple(predictions[0].class_labels)
        if (
            self._class_labels is not None and class_labels != self._class_labels
        ) or any(
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

    def build_features(
        self, predictions: Sequence[PredictionOutput], /
    ) -> tuple[tuple[object, ...], ...]:
        """Return a one-row feature matrix in deterministic prediction order.

        Args:
            predictions: Modality prediction outputs in feature order.

        Returns:
            A standard-library tuple matrix containing flattened probabilities.

        Raises:
            ValueError: If the supplied predictions are incompatible.
        """
        self.validate_inputs(predictions)
        if self._class_labels is None:
            class_labels = tuple(predictions[0].class_labels)
            self._class_labels = class_labels
            self._metadata = StackingFeaturesMetadata(
                input_modalities=self.metadata.input_modalities,
                feature_names=tuple(
                    f"{modality}__{label}"
                    for modality in self.metadata.input_modalities
                    for label in class_labels
                ),
                configuration=self.metadata.configuration,
            )
        return (
            tuple(
                probability
                for prediction in predictions
                for probability in prediction.probabilities
            ),
        )
