"""Logistic-regression meta-model adapter for stacking fusion."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Self

from models.lr import LogisticRegressionModel

__all__ = ["StackingLogisticRegressionMetadata", "StackingLogisticRegression"]


@dataclass(frozen=True, slots=True)
class StackingLogisticRegressionMetadata:
    """Immutable metadata describing a stacking logistic-regression model.

    Attributes:
        model_name: Concrete stacking meta-model class name.
        algorithm: Framework-independent learning algorithm identifier.
        class_labels: Labels in the required probability-column order.
        configuration: Declarative logistic-regression configuration.
    """

    model_name: str
    algorithm: str
    class_labels: tuple[object, ...]
    configuration: Mapping[str, object] = field(default_factory=dict)


class StackingLogisticRegression:
    """Adapt logistic regression for stacking meta-features.

    Args:
        class_labels: Labels in the required probability-column order.
        configuration: Optional configuration delegated to the reusable
            logistic-regression model.

    Notes:
        Feature matrices are expected to be produced by
        :class:`fusion.stacking_features.StackingFeatureBuilder`. This adapter
        performs no feature construction or transformation of its own.
    """

    def __init__(
        self,
        class_labels: Sequence[object] = (0, 1),
        *,
        configuration: Mapping[str, object] | None = None,
    ) -> None:
        """Initialize an unfitted stacking meta-model."""
        labels = tuple(class_labels)
        settings = dict({} if configuration is None else configuration)
        self._metadata = StackingLogisticRegressionMetadata(
            model_name=type(self).__name__,
            algorithm="logistic-regression",
            class_labels=labels,
            configuration=MappingProxyType(settings),
        )
        self._model = LogisticRegressionModel(
            class_labels=labels,
            modality="MULTIMODAL",
            configuration=settings,
        )

    @property
    def metadata(self) -> StackingLogisticRegressionMetadata:
        """Return immutable metadata describing this stacking meta-model."""
        return self._metadata

    def fit(self, meta_features: object, targets: object, /) -> Self:
        """Fit the delegated model on stacking meta-features."""
        self._model.fit(meta_features, targets)
        return self

    def predict(self, meta_features: object, /) -> object:
        """Delegate class-label prediction for stacking meta-features."""
        return self._model.predict(meta_features)

    def predict_proba(self, meta_features: object, /) -> object:
        """Delegate probability prediction for stacking meta-features."""
        return self._model.predict_proba(meta_features)
