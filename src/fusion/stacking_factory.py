"""Framework-neutral factory for stacking meta-model adapters."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType

from fusion.stacking_contracts import StackingMetaModel
from fusion.stacking_lr import StackingLogisticRegression
from fusion.stacking_rf import StackingRandomForest

__all__ = ["StackingMetaModelFactoryMetadata", "StackingMetaModelFactory"]


@dataclass(frozen=True, slots=True)
class StackingMetaModelFactoryMetadata:
    """Immutable metadata describing a stacking meta-model factory.

    Attributes:
        factory_name: Concrete stacking meta-model factory class name.
        supported_algorithms: Framework-independent algorithm identifiers.
        configuration: Declarative factory configuration.
    """

    factory_name: str
    supported_algorithms: tuple[str, ...]
    configuration: Mapping[str, object] = field(default_factory=dict)


class StackingMetaModelFactory:
    """Construct stacking meta-model adapters from exact identifiers.

    Args:
        configuration: Optional declarative factory configuration.
    """

    _SUPPORTED_ALGORITHMS = ("logistic-regression", "random-forest")

    def __init__(self, *, configuration: Mapping[str, object] | None = None) -> None:
        """Initialize the factory with an immutable metadata snapshot."""
        self._metadata = StackingMetaModelFactoryMetadata(
            factory_name=type(self).__name__,
            supported_algorithms=self._SUPPORTED_ALGORITHMS,
            configuration=MappingProxyType(
                dict({} if configuration is None else configuration)
            ),
        )

    @property
    def metadata(self) -> StackingMetaModelFactoryMetadata:
        """Return immutable metadata describing this factory."""
        return self._metadata

    def create(
        self,
        algorithm: str,
        class_labels: Sequence[object],
        *,
        configuration: Mapping[str, object] | None = None,
    ) -> StackingMetaModel:
        """Create the stacking adapter selected by an exact identifier.

        Args:
            algorithm: Framework-independent algorithm identifier.
            class_labels: Labels in the required probability-column order.
            configuration: Optional configuration delegated to the adapter.

        Returns:
            An unfitted stacking meta-model adapter.

        Raises:
            ValueError: If the algorithm is empty or unsupported, or if class
                labels are empty or contain duplicates.
        """
        if not algorithm:
            raise ValueError("algorithm must not be empty")

        labels = tuple(class_labels)
        if not labels:
            raise ValueError("class_labels must not be empty")
        if len(set(labels)) != len(labels):
            raise ValueError("class_labels must not contain duplicates")

        if algorithm == "logistic-regression":
            return StackingLogisticRegression(labels, configuration=configuration)
        if algorithm == "random-forest":
            return StackingRandomForest(labels, configuration=configuration)

        supported = ", ".join(self._SUPPORTED_ALGORITHMS)
        raise ValueError(
            f"unsupported stacking meta-model algorithm {algorithm!r}; "
            f"supported identifiers: {supported}"
        )
