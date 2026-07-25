"""Framework-agnostic architectural specialization for process models."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Self

from models.base import BaseModel

__all__ = ["ProcessModel"]


@dataclass(frozen=True, slots=True)
class _ProcessModelMetadata:
    """Metadata used to initialize a process-modality model."""

    model_name: str
    algorithm: str
    modality: str
    class_labels: Sequence[object]
    configuration: Mapping[str, object] = field(default_factory=dict)


class ProcessModel(BaseModel[object, object, object, object]):
    """Architectural base specialization for the PROCESS modality.

    Args:
        class_labels: Labels in the order expected for probability outputs.
        algorithm: Framework-independent identifier for the intended algorithm.
        configuration: Optional declarative model configuration.
    """

    def __init__(
        self,
        class_labels: Sequence[object] = (0, 1),
        *,
        algorithm: str = "process-model",
        configuration: Mapping[str, object] | None = None,
    ) -> None:
        """Initialize an unfitted process model with immutable metadata."""
        metadata = _ProcessModelMetadata(
            model_name=type(self).__name__,
            algorithm=algorithm,
            modality="PROCESS",
            class_labels=class_labels,
            configuration={} if configuration is None else configuration,
        )
        super().__init__(metadata)

    def fit(self, features: object, targets: object, /) -> Self:
        """Indicate that training is not implemented by this architecture."""
        raise NotImplementedError

    def predict(self, features: object, /) -> object:
        """Indicate that prediction is not implemented by this architecture."""
        raise NotImplementedError

    def predict_proba(self, features: object, /) -> object:
        """Indicate that probability prediction is not implemented."""
        raise NotImplementedError
