"""Framework-agnostic contracts for unimodal predictive models."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Protocol, Self, TypeVar

__all__ = ["ModelMetadata", "UnimodalModel"]


FeaturesT = TypeVar("FeaturesT", contravariant=True)
TargetsT = TypeVar("TargetsT", contravariant=True)
PredictionsT = TypeVar("PredictionsT", covariant=True)
ProbabilitiesT = TypeVar("ProbabilitiesT", covariant=True)


class ModelMetadata(Protocol):
    """Descriptive information exposed by every unimodal model."""

    @property
    def model_name(self) -> str:
        """Return the stable, human-readable name of the model."""
        ...

    @property
    def algorithm(self) -> str:
        """Return the implementation-independent algorithm family."""
        ...

    @property
    def modality(self) -> str:
        """Return the single input modality modeled by this instance."""
        ...

    @property
    def class_labels(self) -> Sequence[object]:
        """Return labels in the column order used by probability outputs."""
        ...

    @property
    def configuration(self) -> Mapping[str, object]:
        """Return a read-only view of the model's declared configuration."""
        ...


class UnimodalModel(
    Protocol[FeaturesT, TargetsT, PredictionsT, ProbabilitiesT],
):
    """Minimum lifecycle and inference behavior for a unimodal model.

    Implementations may use any learning framework or data container. They must
    document their behavior when inference is requested before fitting.
    """

    @property
    def is_fitted(self) -> bool:
        """Return whether the model has completed a successful fit."""
        ...

    @property
    def metadata(self) -> ModelMetadata:
        """Return metadata describing the model and its probability ordering."""
        ...

    def fit(self, features: FeaturesT, targets: TargetsT, /) -> Self:
        """Fit the model from unimodal features and corresponding targets."""
        ...

    def predict(self, features: FeaturesT, /) -> PredictionsT:
        """Predict one output for each supplied observation."""
        ...

    def predict_proba(self, features: FeaturesT, /) -> ProbabilitiesT:
        """Return class probabilities ordered according to metadata labels."""
        ...
