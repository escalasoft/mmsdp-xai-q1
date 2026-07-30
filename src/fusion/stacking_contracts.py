"""Framework-neutral contract for stacking meta-model adapters."""

from __future__ import annotations

from typing import Protocol, Self

__all__ = ["StackingMetaModel"]


class StackingMetaModel(Protocol):
    """Minimum learning and inference behavior for a stacking meta-model."""

    def fit(self, meta_features: object, targets: object, /) -> Self:
        """Fit the meta-model from stacking features and corresponding targets."""
        ...

    def predict(self, meta_features: object, /) -> object:
        """Predict one output for each supplied stacking observation."""
        ...

    def predict_proba(self, meta_features: object, /) -> object:
        """Return class probabilities for the supplied stacking observations."""
        ...
