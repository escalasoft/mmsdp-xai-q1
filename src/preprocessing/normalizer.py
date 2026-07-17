"""Public contracts for train-fitted preprocessing normalization."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol, TypeVar

from preprocessing.schema import PreprocessingSplit, _freeze_mapping
from preprocessing.splitter import PreprocessingPartitions

__all__ = [
    "FittedNormalizer",
    "FittedNormalizerState",
    "NormalizationSpec",
    "NormalizedPartitions",
    "TrainFittedNormalizer",
]


DatasetT = TypeVar("DatasetT")


@dataclass(frozen=True)
class NormalizationSpec:
    """Feature selection for a normalization stage, independent of its algorithm."""

    feature_names: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "feature_names", tuple(self.feature_names))


@dataclass(frozen=True)
class FittedNormalizerState:
    """Immutable evidence and opaque parameters produced by training-only fitting."""

    feature_names: tuple[str, ...]
    fit_split: PreprocessingSplit
    parameters: Mapping[str, object]

    def __post_init__(self) -> None:
        if self.fit_split is not PreprocessingSplit.TRAIN:
            raise ValueError("fit_split must be PreprocessingSplit.TRAIN")
        object.__setattr__(self, "feature_names", tuple(self.feature_names))
        object.__setattr__(self, "parameters", _freeze_mapping(self.parameters))


@dataclass(frozen=True)
class NormalizedPartitions:
    """Transformed partitions accompanied by the state fitted on training data."""

    train_records: object
    validation_records: object
    test_records: object
    fitted_state: FittedNormalizerState


class FittedNormalizer(Protocol[DatasetT]):
    """A fitted stage that applies one unchanged transformation to a dataset."""

    @property
    def state(self) -> FittedNormalizerState: ...

    def transform(self, dataset: DatasetT, /) -> DatasetT: ...


class TrainFittedNormalizer(Protocol[DatasetT]):
    """A normalization stage whose learned state comes only from training data."""

    def fit(
        self,
        training_data: DatasetT,
        /,
        *,
        spec: NormalizationSpec,
    ) -> FittedNormalizer[DatasetT]: ...


def fit_normalizer_on_training_data(
    training_data: DatasetT,
    normalizer: TrainFittedNormalizer[DatasetT],
    /,
    *,
    spec: NormalizationSpec,
) -> FittedNormalizer[DatasetT]:
    """Fit a normalizer using only the supplied training dataset."""
    return normalizer.fit(training_data, spec=spec)


def transform_preprocessing_partitions(
    partitions: PreprocessingPartitions,
    fitted_normalizer: FittedNormalizer[DatasetT],
    /,
) -> NormalizedPartitions:
    """Apply one fitted normalizer unchanged to every dataset partition."""
    return NormalizedPartitions(
        train_records=fitted_normalizer.transform(partitions.train_records),
        validation_records=fitted_normalizer.transform(partitions.validation_records),
        test_records=fitted_normalizer.transform(partitions.test_records),
        fitted_state=fitted_normalizer.state,
    )
