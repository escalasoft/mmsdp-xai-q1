"""Framework-neutral execution of reproducible stacking experiments."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from numbers import Real

from experimentation.specification import ExperimentSpecification
from fusion.contracts import PredictionOutput
from fusion.stacking_contracts import StackingMetaModel
from fusion.stacking_features import StackingFeatureBuilder
from fusion.stacking_orchestrator import StackingFusionOrchestrator

__all__ = ["ExperimentRunResult", "ExperimentRunner"]


@dataclass(frozen=True, slots=True, init=False)
class ExperimentRunResult:
    """Detached direct outputs from one experiment execution."""

    experiment_id: str
    class_labels: tuple[object, ...]
    predictions: tuple[object, ...]
    probabilities: tuple[tuple[float, ...], ...]
    training_observation_count: int
    evaluation_observation_count: int

    def __init__(
        self,
        experiment_id: str,
        class_labels: Sequence[object],
        predictions: Sequence[object],
        probabilities: Sequence[Sequence[float]],
        training_observation_count: int,
        evaluation_observation_count: int,
    ) -> None:
        """Initialize an immutable, validated snapshot of execution outputs."""
        labels = tuple(class_labels)
        detached_predictions = tuple(predictions)
        detached_probabilities = tuple(tuple(row) for row in probabilities)

        if not experiment_id:
            raise ValueError("experiment_id must not be empty")
        if not labels:
            raise ValueError("class_labels must not be empty")
        if any(
            label == previous
            for index, label in enumerate(labels)
            for previous in labels[:index]
        ):
            raise ValueError("class_labels must not contain duplicates")
        self._validate_observation_count(
            training_observation_count, "training_observation_count"
        )
        self._validate_observation_count(
            evaluation_observation_count, "evaluation_observation_count"
        )
        if len(detached_predictions) != evaluation_observation_count:
            raise ValueError(
                "predictions count must equal evaluation_observation_count"
            )
        if len(detached_probabilities) != evaluation_observation_count:
            raise ValueError(
                "probabilities count must equal evaluation_observation_count"
            )
        for row in detached_probabilities:
            if len(row) != len(labels):
                raise ValueError(
                    "each probability row must have one value per class label"
                )
            if any(
                isinstance(value, bool) or not isinstance(value, Real)
                for value in row
            ):
                raise TypeError(
                    "probability values must be numeric and must not be bool"
                )

        object.__setattr__(self, "experiment_id", experiment_id)
        object.__setattr__(self, "class_labels", labels)
        object.__setattr__(self, "predictions", detached_predictions)
        object.__setattr__(self, "probabilities", detached_probabilities)
        object.__setattr__(
            self, "training_observation_count", training_observation_count
        )
        object.__setattr__(
            self, "evaluation_observation_count", evaluation_observation_count
        )

    @staticmethod
    def _validate_observation_count(value: int, name: str) -> None:
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"{name} must be an integer and must not be bool")
        if value < 0:
            raise ValueError(f"{name} must be non-negative")

    def to_dict(self) -> dict[str, object]:
        """Return a detached representation using standard mutable structures."""
        return {
            "experiment_id": self.experiment_id,
            "class_labels": list(self.class_labels),
            "predictions": list(self.predictions),
            "probabilities": [list(row) for row in self.probabilities],
            "training_observation_count": self.training_observation_count,
            "evaluation_observation_count": self.evaluation_observation_count,
        }


class ExperimentRunner:
    """Execute an explicitly specified stacking experiment."""

    def __init__(
        self,
        specification: ExperimentSpecification,
        feature_builder: StackingFeatureBuilder,
        meta_model: StackingMetaModel,
    ) -> None:
        """Initialize the runner from explicit configuration and dependencies."""
        if specification is None:
            raise ValueError("specification must not be None")
        if feature_builder is None:
            raise ValueError("feature_builder must not be None")
        if meta_model is None:
            raise ValueError("meta_model must not be None")

        metadata = feature_builder.metadata
        if specification.modalities != metadata.input_modalities:
            raise ValueError(
                "specification modalities must equal feature builder modalities"
            )

        declared_labels = getattr(metadata, "class_labels", None)
        if declared_labels is not None and tuple(declared_labels) != (
            specification.class_labels
        ):
            raise ValueError(
                "specification class labels must equal feature builder class labels"
            )
        if metadata.feature_names:
            expected_names = tuple(
                f"{modality}__{label}"
                for modality in specification.modalities
                for label in specification.class_labels
            )
            if metadata.feature_names != expected_names:
                raise ValueError(
                    "specification class labels are incompatible with feature names"
                )

        self._specification = specification
        self._orchestrator = StackingFusionOrchestrator(
            specification.modalities, feature_builder, meta_model
        )

    @property
    def specification(self) -> ExperimentSpecification:
        """Return the immutable experiment specification."""
        return self._specification

    def run(
        self,
        training_predictions: Sequence[PredictionOutput],
        training_targets: object,
        evaluation_predictions: Sequence[PredictionOutput],
    ) -> ExperimentRunResult:
        """Train and evaluate the injected stacking pipeline once."""
        training_count = self._validate_predictions(
            training_predictions, "training_predictions"
        )
        evaluation_count = self._validate_predictions(
            evaluation_predictions, "evaluation_predictions"
        )

        self._orchestrator.fit(training_predictions, training_targets)
        predictions = self._orchestrator.predict(evaluation_predictions)
        probabilities = self._orchestrator.predict_proba(evaluation_predictions)

        return ExperimentRunResult(
            experiment_id=self.specification.experiment_id,
            class_labels=self.specification.class_labels,
            predictions=tuple(predictions),
            probabilities=tuple(tuple(row) for row in probabilities),
            training_observation_count=training_count,
            evaluation_observation_count=evaluation_count,
        )

    def _validate_predictions(
        self, predictions: Sequence[PredictionOutput], name: str
    ) -> int:
        if not predictions:
            raise ValueError(f"{name} must not be empty")

        modality_count = len(self.specification.modalities)
        if len(predictions) % modality_count:
            raise ValueError(f"{name} contains an incomplete modality bundle")

        allowed_modalities = set(self.specification.modalities)
        for prediction in predictions:
            if tuple(prediction.class_labels) != self.specification.class_labels:
                raise ValueError(
                    "prediction class-label order must equal specification class labels"
                )
            if prediction.modality not in allowed_modalities:
                raise ValueError(
                    "prediction modality must be declared by the specification"
                )
        return len(predictions) // modality_count
