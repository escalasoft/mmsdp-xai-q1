"""Reusable foundation for framework-agnostic unimodal models."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sized
from dataclasses import dataclass
from types import MappingProxyType
from typing import Generic, Self, TypeVar

from models.contracts import ModelMetadata, UnimodalModel

__all__ = ["BaseModel"]


FeaturesT = TypeVar("FeaturesT")
TargetsT = TypeVar("TargetsT")
PredictionsT = TypeVar("PredictionsT")
ProbabilitiesT = TypeVar("ProbabilitiesT")


@dataclass(frozen=True, slots=True)
class _ImmutableModelMetadata:
    """Immutable snapshot of metadata supplied to a model."""

    model_name: str
    algorithm: str
    modality: str
    class_labels: tuple[object, ...]
    configuration: Mapping[str, object]

    @classmethod
    def from_metadata(cls, metadata: ModelMetadata) -> Self:
        """Create a defensive, immutable snapshot of model metadata.

        Args:
            metadata: Metadata object conforming to ``ModelMetadata``.

        Returns:
            An immutable snapshot detached from mutable input containers.

        Raises:
            TypeError: If ``metadata`` is ``None``.
            ValueError: If a required descriptive field is empty.
        """
        if metadata is None:
            raise TypeError("metadata must not be None")

        model_name = cls._validate_text(metadata.model_name, "model_name")
        algorithm = cls._validate_text(metadata.algorithm, "algorithm")
        modality = cls._validate_text(metadata.modality, "modality")
        configuration = MappingProxyType(dict(metadata.configuration))

        return cls(
            model_name=model_name,
            algorithm=algorithm,
            modality=modality,
            class_labels=tuple(metadata.class_labels),
            configuration=configuration,
        )

    @staticmethod
    def _validate_text(value: str, field_name: str) -> str:
        """Validate a required metadata text field."""
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"metadata.{field_name} must be a non-empty string")
        return value


class BaseModel(
    ABC,
    Generic[FeaturesT, TargetsT, PredictionsT, ProbabilitiesT],
    UnimodalModel[FeaturesT, TargetsT, PredictionsT, ProbabilitiesT],
):
    """Abstract base for reusable unimodal predictive models.

    The class owns framework-independent lifecycle behavior while subclasses
    implement all training and inference operations. Subclasses should call
    ``_mark_fitted()`` only after training completes successfully.

    Args:
        metadata: Descriptive metadata for the model. Its sequence and mapping
            values are defensively copied into immutable containers.
    """

    def __init__(self, metadata: ModelMetadata) -> None:
        """Initialize an unfitted model with immutable metadata."""
        self._metadata: ModelMetadata = _ImmutableModelMetadata.from_metadata(metadata)
        self._is_fitted = False

    @property
    def metadata(self) -> ModelMetadata:
        """Return immutable metadata describing this model."""
        return self._metadata

    @property
    def is_fitted(self) -> bool:
        """Return whether training has completed successfully."""
        return self._is_fitted

    def _mark_fitted(self) -> None:
        """Record that model fitting completed successfully."""
        self._is_fitted = True

    def _mark_unfitted(self) -> None:
        """Reset fitted state before retraining or clearing learned state."""
        self._is_fitted = False

    def _require_fitted(self) -> None:
        """Raise an error when an operation requires a fitted model.

        Raises:
            RuntimeError: If the model has not completed a successful fit.
        """
        if not self._is_fitted:
            raise RuntimeError(
                f"{self.metadata.model_name} must be fitted before inference"
            )

    @staticmethod
    def _require_not_none(value: object, name: str) -> None:
        """Validate that a required input is present.

        Args:
            value: Value to validate.
            name: Human-readable argument name used in the error message.

        Raises:
            TypeError: If ``value`` is ``None``.
        """
        if value is None:
            raise TypeError(f"{name} must not be None")

    @staticmethod
    def _require_same_length(
        first: Sized,
        second: Sized,
        *,
        first_name: str = "features",
        second_name: str = "targets",
    ) -> None:
        """Validate that two sized inputs contain the same item count.

        Args:
            first: First sized input.
            second: Second sized input.
            first_name: Name of the first input for error reporting.
            second_name: Name of the second input for error reporting.

        Raises:
            ValueError: If the input lengths differ.
        """

        def observation_count(value: Sized) -> int:
            try:
                return len(value)
            except TypeError:
                shape = getattr(value, "shape", None)
                if not shape:
                    raise
                return int(shape[0])

        first_count = observation_count(first)
        second_count = observation_count(second)
        if first_count != second_count:
            raise ValueError(
                f"{first_name} and {second_name} must have the same length "
                f"({first_count} != {second_count})"
            )

    @abstractmethod
    def fit(self, features: FeaturesT, targets: TargetsT, /) -> Self:
        """Fit the model and return this instance."""
        raise NotImplementedError

    @abstractmethod
    def predict(self, features: FeaturesT, /) -> PredictionsT:
        """Predict one output for each supplied observation."""
        raise NotImplementedError

    @abstractmethod
    def predict_proba(self, features: FeaturesT, /) -> ProbabilitiesT:
        """Return probabilities ordered by metadata class labels."""
        raise NotImplementedError
