"""End-to-end smoke test for the stacking fusion pipeline."""

from collections.abc import Sequence

from fusion.contracts import PredictionOutput
from fusion.stacking_factory import StackingMetaModelFactory
from fusion.stacking_features import StackingFeatureBuilder
from fusion.stacking_lr import StackingLogisticRegression
from fusion.stacking_orchestrator import StackingFusionOrchestrator

MODALITIES = ("CODE", "PROCESS", "TEXT")
CLASS_LABELS = ("defective", "clean")


class BatchStackingFeatureBuilder(StackingFeatureBuilder):
    """Apply the public single-observation builder API to a training batch."""

    def build_features(
        self, predictions: Sequence[PredictionOutput], /
    ) -> tuple[tuple[object, ...], ...]:
        modality_count = len(self.metadata.input_modalities)
        if len(predictions) % modality_count:
            raise ValueError("each observation must contain every modality")
        return tuple(
            super(BatchStackingFeatureBuilder, self).build_features(
                predictions[index : index + modality_count]
            )[0]
            for index in range(0, len(predictions), modality_count)
        )


def prediction_bundle(
    defective_probability: float,
) -> tuple[PredictionOutput, ...]:
    """Create one deterministic, consistently ordered multimodal observation."""
    return tuple(
        PredictionOutput(
            probabilities=(defective_probability, 1.0 - defective_probability),
            class_labels=CLASS_LABELS,
            modality=modality,
            metadata={},
        )
        for modality in MODALITIES
    )


def test_factory_logistic_regression_runs_complete_stacking_pipeline() -> None:
    builder = BatchStackingFeatureBuilder(MODALITIES, CLASS_LABELS)
    meta_model = StackingMetaModelFactory().create(
        "logistic-regression",
        CLASS_LABELS,
        configuration={"random_state": 17, "solver": "liblinear"},
    )
    orchestrator = StackingFusionOrchestrator(
        MODALITIES,
        builder,
        meta_model,
    )
    clean = prediction_bundle(0.05)
    defective = prediction_bundle(0.95)
    training_predictions = (
        clean + defective + prediction_bundle(0.10) + prediction_bundle(0.90)
    )
    targets = ("clean", "defective", "clean", "defective")

    fitted = orchestrator.fit(training_predictions, targets)
    predictions = tuple(orchestrator.predict(clean + defective))
    probabilities = tuple(
        tuple(row) for row in orchestrator.predict_proba(clean + defective)
    )

    assert isinstance(meta_model, StackingLogisticRegression)
    assert meta_model.metadata.class_labels == CLASS_LABELS
    assert orchestrator.metadata.meta_model_name == "StackingLogisticRegression"
    assert fitted is orchestrator
    assert predictions == ("clean", "defective")
    assert len(probabilities) == 2
    assert all(len(row) == len(CLASS_LABELS) for row in probabilities)
    assert all(abs(sum(row) - 1.0) < 1e-12 for row in probabilities)
    assert (
        probabilities[0][CLASS_LABELS.index("clean")]
        > probabilities[0][CLASS_LABELS.index("defective")]
    )
    assert (
        probabilities[1][CLASS_LABELS.index("defective")]
        > probabilities[1][CLASS_LABELS.index("clean")]
    )
