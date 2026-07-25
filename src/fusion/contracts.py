"""Framework-agnostic contracts for modality prediction outputs."""

from __future__ import annotations

from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass

__all__ = ["PredictionOutput", "FusionInput"]


@dataclass(frozen=True, slots=True)
class PredictionOutput:
    """Prediction probabilities and descriptive modality information."""

    probabilities: object
    class_labels: Sequence[object]
    modality: str
    metadata: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class FusionInput:
    """Collection of modality predictions supplied for fusion."""

    predictions: Collection[PredictionOutput]
