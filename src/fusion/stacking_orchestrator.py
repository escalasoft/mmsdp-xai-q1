"""Framework-neutral orchestration for stacking fusion."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Self

from fusion.contracts import PredictionOutput
from fusion.stacking_features import StackingFeatureBuilder

__all__ = ["StackingFusionOrchestratorMetadata", "StackingFusionOrchestrator"]


@dataclass(frozen=True, slots=True)
class StackingFusionOrchestratorMetadata:
    """Immutable metadata describing a stacking fusion orchestrator.

    Attributes:
        orchestrator_name: Concrete orchestrator class name.
        fusion_strategy: Framework-independent fusion strategy identifier.
        input_modalities: Modalities whose predictions are orchestrated.
        meta_model_name: Concrete stacking meta-model class name.
        configuration: Declarative orchestrator configuration.
    """

    orchestrator_name: str
    fusion_strategy: str
    input_modalities: tuple[str, ...]
    meta_model_name: str
    configuration: Mapping[str, object] = field(default_factory=dict)


class StackingFusionOrchestrator:
    """Coordinate stacking feature construction, training, and inference.

    Args:
        input_modalities: Modalities whose predictions will form meta-features.
        feature_builder: Builder responsible for constructing meta-features.
        meta_model: Stacking meta-model adapter used for learning and inference.
        configuration: Optional declarative orchestrator configuration.
    """

    def __init__(
        self,
        input_modalities: Sequence[str],
        feature_builder: StackingFeatureBuilder,
        meta_model: object,
        *,
        configuration: Mapping[str, object] | None = None,
    ) -> None:
        """Initialize the orchestrator with injected stacking components."""
        modalities = tuple(input_modalities)
        if not modalities:
            raise ValueError("at least one input modality is required")
        if len(set(modalities)) != len(modalities):
            raise ValueError("input modality names must be unique")
        if feature_builder is None:
            raise ValueError("feature_builder must not be None")
        if meta_model is None:
            raise ValueError("meta_model must not be None")

        self._feature_builder = feature_builder
        self._meta_model = meta_model
        self._metadata = StackingFusionOrchestratorMetadata(
            orchestrator_name=type(self).__name__,
            fusion_strategy="stacking",
            input_modalities=modalities,
            meta_model_name=type(meta_model).__name__,
            configuration=MappingProxyType(
                dict({} if configuration is None else configuration)
            ),
        )

    @property
    def metadata(self) -> StackingFusionOrchestratorMetadata:
        """Return immutable metadata describing this orchestrator."""
        return self._metadata

    def fit(
        self,
        predictions: Sequence[PredictionOutput],
        targets: object,
        /,
    ) -> Self:
        """Build stacking meta-features and fit the injected meta-model."""
        meta_features = self._feature_builder.build_features(predictions)
        self._meta_model.fit(meta_features, targets)
        return self

    def predict(self, predictions: Sequence[PredictionOutput], /) -> object:
        """Build meta-features and delegate class-label prediction."""
        meta_features = self._feature_builder.build_features(predictions)
        return self._meta_model.predict(meta_features)

    def predict_proba(self, predictions: Sequence[PredictionOutput], /) -> object:
        """Build meta-features and delegate probability prediction."""
        meta_features = self._feature_builder.build_features(predictions)
        return self._meta_model.predict_proba(meta_features)
