"""Integration tests for framework-neutral stacking orchestration."""

from collections.abc import Sequence

import pytest

from fusion.contracts import PredictionOutput
from fusion.stacking_contracts import StackingMetaModel
from fusion.stacking_features import StackingFeatureBuilder
from fusion.stacking_orchestrator import StackingFusionOrchestrator

MODALITIES = ("CODE", "PROCESS", "TEXT")
CLASS_LABELS = ("clean", "defective")
EXPECTED_META_FEATURES = ((0.8, 0.2, 0.6, 0.4, 0.3, 0.7),)


class RecordingFeatureBuilder(StackingFeatureBuilder):
    """Production feature builder that records its orchestration boundary."""

    def __init__(self) -> None:
        super().__init__(MODALITIES, CLASS_LABELS)
        self.received_predictions: list[Sequence[PredictionOutput]] = []

    def build_features(
        self, predictions: Sequence[PredictionOutput], /
    ) -> tuple[tuple[object, ...], ...]:
        self.received_predictions.append(predictions)
        return super().build_features(predictions)


class RecordingMetaModel:
    """Deterministic structural implementation of ``StackingMetaModel``."""

    def __init__(self) -> None:
        self.fit_calls: list[tuple[object, object]] = []
        self.predict_calls: list[object] = []
        self.predict_proba_calls: list[object] = []
        self.prediction = ("defective",)
        self.probabilities = ((0.25, 0.75),)

    def fit(self, meta_features: object, targets: object, /) -> "RecordingMetaModel":
        self.fit_calls.append((meta_features, targets))
        return self

    def predict(self, meta_features: object, /) -> object:
        self.predict_calls.append(meta_features)
        return self.prediction

    def predict_proba(self, meta_features: object, /) -> object:
        self.predict_proba_calls.append(meta_features)
        return self.probabilities


@pytest.fixture
def predictions() -> tuple[PredictionOutput, ...]:
    return (
        PredictionOutput((0.8, 0.2), CLASS_LABELS, "CODE", {"source": "code"}),
        PredictionOutput((0.6, 0.4), CLASS_LABELS, "PROCESS", {"source": "process"}),
        PredictionOutput((0.3, 0.7), CLASS_LABELS, "TEXT", {"source": "text"}),
    )


@pytest.fixture
def components() -> tuple[RecordingFeatureBuilder, RecordingMetaModel]:
    builder = RecordingFeatureBuilder()
    model = RecordingMetaModel()
    meta_model: StackingMetaModel = model
    assert meta_model is model
    return builder, model


def test_fit_builds_features_and_delegates_training_unchanged(
    predictions: tuple[PredictionOutput, ...],
    components: tuple[RecordingFeatureBuilder, RecordingMetaModel],
) -> None:
    builder, model = components
    targets = (0, 1, 1)
    orchestrator = StackingFusionOrchestrator(MODALITIES, builder, model)

    result = orchestrator.fit(predictions, targets)

    assert builder.received_predictions == [predictions]
    assert builder.received_predictions[0] is predictions
    assert model.fit_calls == [(EXPECTED_META_FEATURES, targets)]
    assert model.fit_calls[0][1] is targets
    assert result is orchestrator


def test_predict_builds_features_and_returns_delegated_prediction_unchanged(
    predictions: tuple[PredictionOutput, ...],
    components: tuple[RecordingFeatureBuilder, RecordingMetaModel],
) -> None:
    builder, model = components
    orchestrator = StackingFusionOrchestrator(MODALITIES, builder, model)

    result = orchestrator.predict(predictions)

    assert builder.received_predictions == [predictions]
    assert builder.received_predictions[0] is predictions
    assert model.predict_calls == [EXPECTED_META_FEATURES]
    assert result is model.prediction


def test_predict_proba_builds_features_and_returns_probabilities_unchanged(
    predictions: tuple[PredictionOutput, ...],
    components: tuple[RecordingFeatureBuilder, RecordingMetaModel],
) -> None:
    builder, model = components
    orchestrator = StackingFusionOrchestrator(MODALITIES, builder, model)

    result = orchestrator.predict_proba(predictions)

    assert builder.received_predictions == [predictions]
    assert builder.received_predictions[0] is predictions
    assert model.predict_proba_calls == [EXPECTED_META_FEATURES]
    assert result is model.probabilities


@pytest.mark.parametrize("modalities", [(), ("CODE", "CODE")])
def test_constructor_rejects_invalid_input_modalities(
    modalities: tuple[str, ...],
    components: tuple[RecordingFeatureBuilder, RecordingMetaModel],
) -> None:
    builder, model = components

    with pytest.raises(ValueError):
        StackingFusionOrchestrator(modalities, builder, model)


def test_constructor_rejects_none_feature_builder() -> None:
    with pytest.raises(ValueError, match="feature_builder"):
        StackingFusionOrchestrator(
            MODALITIES,
            None,
            RecordingMetaModel(),  # type: ignore[arg-type]
        )


def test_constructor_rejects_none_meta_model() -> None:
    with pytest.raises(ValueError, match="meta_model"):
        StackingFusionOrchestrator(
            MODALITIES,
            RecordingFeatureBuilder(),
            None,  # type: ignore[arg-type]
        )


def test_metadata_preserves_identity_strategy_and_immutable_configuration() -> None:
    configuration = {"folds": 5}
    orchestrator = StackingFusionOrchestrator(
        MODALITIES,
        RecordingFeatureBuilder(),
        RecordingMetaModel(),
        configuration=configuration,
    )
    configuration["folds"] = 10

    assert orchestrator.metadata.input_modalities == MODALITIES
    assert orchestrator.metadata.meta_model_name == "RecordingMetaModel"
    assert orchestrator.metadata.fusion_strategy == "stacking"
    assert orchestrator.metadata.configuration == {"folds": 5}
    with pytest.raises(TypeError):
        orchestrator.metadata.configuration["folds"] = 10  # type: ignore[index]
