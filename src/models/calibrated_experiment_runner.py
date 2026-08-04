"""Deterministic orchestration of calibrated model experiments."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from types import MappingProxyType

from dataset.model_input import PreparedModelInput
from models.calibration import (
    CalibratedPredictionResult,
    ModelProbabilityCalibrator,
    PreparedProbabilityCalibrator,
    ProbabilityCalibrationConfiguration,
)
from models.calibration_evaluation import (
    ProbabilityCalibrationComparison,
    ProbabilityCalibrationEvaluation,
    ProbabilityCalibrationEvaluator,
)
from models.experiment_runner import ModelExperimentResult
from models.logistic_regression_adapter import LogisticRegressionAdapter
from models.random_forest_adapter import RandomForestAdapter

__all__ = [
    "CalibratedModelExperimentResult",
    "CalibratedModelExperimentRunner",
]

_METHODS = frozenset({"platt", "isotonic"})
_UNSET = object()


def _freeze(value: object) -> object:
    """Return a detached, recursively immutable snapshot."""
    if isinstance(value, Mapping):
        return MappingProxyType(
            {deepcopy(key): _freeze(item) for key, item in value.items()}
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze(item) for item in value)
    return deepcopy(value)


def _freeze_mapping(value: Mapping[str, object]) -> Mapping[str, object]:
    return MappingProxyType(
        {deepcopy(key): _freeze(item) for key, item in value.items()}
    )


def _thaw(value: object) -> object:
    """Return a detached snapshot containing ordinary mutable containers."""
    if isinstance(value, Mapping):
        return {deepcopy(key): _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    if isinstance(value, frozenset):
        return {_thaw(item) for item in value}
    return deepcopy(value)


def _validate_name(name: str, value: object) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


@dataclass(frozen=True, slots=True, init=False)
class CalibratedModelExperimentResult:
    """Immutable result of one complete calibrated model experiment."""

    dataset_name: str
    dataset_version: str
    model_name: str
    calibration_method: str
    uncalibrated_experiment: ModelExperimentResult
    prepared_calibrator: PreparedProbabilityCalibrator
    calibrated_validation_prediction: CalibratedPredictionResult
    calibrated_test_prediction: CalibratedPredictionResult
    uncalibrated_validation_calibration: ProbabilityCalibrationEvaluation
    calibrated_validation_calibration: ProbabilityCalibrationEvaluation
    validation_calibration_comparison: ProbabilityCalibrationComparison
    uncalibrated_test_calibration: ProbabilityCalibrationEvaluation
    calibrated_test_calibration: ProbabilityCalibrationEvaluation
    test_calibration_comparison: ProbabilityCalibrationComparison
    metadata: Mapping[str, object]

    def __init__(
        self,
        dataset_name: str,
        dataset_version: str,
        model_name: str,
        calibration_method: str,
        uncalibrated_experiment: ModelExperimentResult,
        prepared_calibrator: PreparedProbabilityCalibrator,
        calibrated_validation_prediction: CalibratedPredictionResult,
        calibrated_test_prediction: CalibratedPredictionResult,
        uncalibrated_validation_calibration: ProbabilityCalibrationEvaluation,
        calibrated_validation_calibration: ProbabilityCalibrationEvaluation,
        validation_calibration_comparison: ProbabilityCalibrationComparison,
        uncalibrated_test_calibration: ProbabilityCalibrationEvaluation,
        calibrated_test_calibration: ProbabilityCalibrationEvaluation,
        test_calibration_comparison: ProbabilityCalibrationComparison,
        metadata: Mapping[str, object] = MappingProxyType({}),
    ) -> None:
        for name, value in (
            ("dataset_name", dataset_name),
            ("dataset_version", dataset_version),
            ("model_name", model_name),
            ("calibration_method", calibration_method),
        ):
            _validate_name(name, value)
        if calibration_method not in _METHODS:
            raise ValueError("calibration_method must be platt or isotonic")

        typed_values = (
            ("uncalibrated_experiment", uncalibrated_experiment, ModelExperimentResult),
            ("prepared_calibrator", prepared_calibrator, PreparedProbabilityCalibrator),
            (
                "calibrated_validation_prediction",
                calibrated_validation_prediction,
                CalibratedPredictionResult,
            ),
            (
                "calibrated_test_prediction",
                calibrated_test_prediction,
                CalibratedPredictionResult,
            ),
            (
                "uncalibrated_validation_calibration",
                uncalibrated_validation_calibration,
                ProbabilityCalibrationEvaluation,
            ),
            (
                "calibrated_validation_calibration",
                calibrated_validation_calibration,
                ProbabilityCalibrationEvaluation,
            ),
            (
                "validation_calibration_comparison",
                validation_calibration_comparison,
                ProbabilityCalibrationComparison,
            ),
            (
                "uncalibrated_test_calibration",
                uncalibrated_test_calibration,
                ProbabilityCalibrationEvaluation,
            ),
            (
                "calibrated_test_calibration",
                calibrated_test_calibration,
                ProbabilityCalibrationEvaluation,
            ),
            (
                "test_calibration_comparison",
                test_calibration_comparison,
                ProbabilityCalibrationComparison,
            ),
        )
        for name, value, expected_type in typed_values:
            if not isinstance(value, expected_type):
                raise TypeError(f"{name} must be a {expected_type.__name__}")
        if not isinstance(metadata, Mapping):
            raise TypeError("metadata must be a mapping")

        direct_results = (
            uncalibrated_experiment,
            prepared_calibrator,
            calibrated_validation_prediction,
            calibrated_test_prediction,
            uncalibrated_validation_calibration,
            calibrated_validation_calibration,
            uncalibrated_test_calibration,
            calibrated_test_calibration,
        )
        if any(item.dataset_name != dataset_name for item in direct_results):
            raise ValueError("dataset_name must match all nested results")
        if any(item.dataset_version != dataset_version for item in direct_results):
            raise ValueError("dataset_version must match all nested results")
        if any(item.model_name != model_name for item in direct_results):
            raise ValueError("model_name must match all nested results")
        if prepared_calibrator.method != calibration_method:
            raise ValueError("calibration_method must match the prepared calibrator")

        validation_items = (
            uncalibrated_experiment.validation_prediction,
            uncalibrated_experiment.validation_evaluation,
            calibrated_validation_prediction,
            uncalibrated_validation_calibration,
            calibrated_validation_calibration,
            validation_calibration_comparison.before,
            validation_calibration_comparison.after,
        )
        test_items = (
            uncalibrated_experiment.test_prediction,
            uncalibrated_experiment.test_evaluation,
            calibrated_test_prediction,
            uncalibrated_test_calibration,
            calibrated_test_calibration,
            test_calibration_comparison.before,
            test_calibration_comparison.after,
        )
        if any(item.partition_name != "validation" for item in validation_items):
            raise ValueError("validation results must use the validation partition")
        if any(item.partition_name != "test" for item in test_items):
            raise ValueError("test results must use the test partition")

        if calibrated_validation_prediction.calibration_method != calibration_method:
            raise ValueError("validation calibration_method must match")
        if calibrated_test_prediction.calibration_method != calibration_method:
            raise ValueError("test calibration_method must match")
        if calibrated_validation_calibration.calibration_method != calibration_method:
            raise ValueError("validation calibration evaluation method must match")
        if calibrated_test_calibration.calibration_method != calibration_method:
            raise ValueError("test calibration evaluation method must match")
        if uncalibrated_validation_calibration.calibration_method != "uncalibrated":
            raise ValueError("validation before evaluation must be uncalibrated")
        if uncalibrated_test_calibration.calibration_method != "uncalibrated":
            raise ValueError("test before evaluation must be uncalibrated")

        if (
            validation_calibration_comparison.before
            is not uncalibrated_validation_calibration
        ):
            raise ValueError(
                "validation comparison.before must be the uncalibrated evaluation"
            )
        if (
            validation_calibration_comparison.after
            is not calibrated_validation_calibration
        ):
            raise ValueError(
                "validation comparison.after must be the calibrated evaluation"
            )
        if test_calibration_comparison.before is not uncalibrated_test_calibration:
            raise ValueError(
                "test comparison.before must be the uncalibrated evaluation"
            )
        if test_calibration_comparison.after is not calibrated_test_calibration:
            raise ValueError("test comparison.after must be the calibrated evaluation")

        for partition_name, items in (
            ("validation", validation_items),
            ("test", test_items),
        ):
            labels = items[0].class_labels
            count = items[0].observation_count
            if any(item.class_labels != labels for item in items[1:]):
                raise ValueError(f"{partition_name} class_labels must match")
            if any(item.observation_count != count for item in items[1:]):
                raise ValueError(f"{partition_name} observation counts must match")

        if (
            prepared_calibrator.class_labels
            != uncalibrated_experiment.validation_prediction.class_labels
        ):
            raise ValueError("prepared calibrator class_labels must match predictions")
        if (
            calibrated_validation_prediction.identifiers
            != uncalibrated_experiment.validation_prediction.identifiers
        ):
            raise ValueError("validation identifiers must be preserved")
        if (
            calibrated_test_prediction.identifiers
            != uncalibrated_experiment.test_prediction.identifiers
        ):
            raise ValueError("test identifiers must be preserved")

        positive_labels = (
            prepared_calibrator.positive_label,
            calibrated_validation_prediction.positive_label,
            calibrated_test_prediction.positive_label,
            uncalibrated_validation_calibration.positive_label,
            calibrated_validation_calibration.positive_label,
            validation_calibration_comparison.before.positive_label,
            validation_calibration_comparison.after.positive_label,
            uncalibrated_test_calibration.positive_label,
            calibrated_test_calibration.positive_label,
            test_calibration_comparison.before.positive_label,
            test_calibration_comparison.after.positive_label,
        )
        if any(label != positive_labels[0] for label in positive_labels[1:]):
            raise ValueError("positive_label must match all calibration results")

        values = {
            "dataset_name": deepcopy(dataset_name),
            "dataset_version": deepcopy(dataset_version),
            "model_name": deepcopy(model_name),
            "calibration_method": deepcopy(calibration_method),
            **{name: value for name, value, _ in typed_values},
        }
        for name, value in values.items():
            object.__setattr__(self, name, value)
        object.__setattr__(self, "metadata", _freeze_mapping(metadata))

    def to_dict(self) -> dict[str, object]:
        """Return a deterministic, detached representation with mutable containers."""
        return {
            "dataset_name": deepcopy(self.dataset_name),
            "dataset_version": deepcopy(self.dataset_version),
            "model_name": deepcopy(self.model_name),
            "calibration_method": deepcopy(self.calibration_method),
            "uncalibrated_experiment": self.uncalibrated_experiment.to_dict(),
            "prepared_calibrator": self.prepared_calibrator.to_dict(),
            "calibrated_validation_prediction": (
                self.calibrated_validation_prediction.to_dict()
            ),
            "calibrated_test_prediction": self.calibrated_test_prediction.to_dict(),
            "uncalibrated_validation_calibration": (
                self.uncalibrated_validation_calibration.to_dict()
            ),
            "calibrated_validation_calibration": (
                self.calibrated_validation_calibration.to_dict()
            ),
            "validation_calibration_comparison": (
                self.validation_calibration_comparison.to_dict()
            ),
            "uncalibrated_test_calibration": (
                self.uncalibrated_test_calibration.to_dict()
            ),
            "calibrated_test_calibration": self.calibrated_test_calibration.to_dict(),
            "test_calibration_comparison": self.test_calibration_comparison.to_dict(),
            "metadata": _thaw(self.metadata),
        }


class CalibratedModelExperimentRunner:
    """Run one supported model experiment and calibrate its probabilities."""

    runner_name = "calibrated-model-experiment-runner"

    def __init__(
        self,
        *,
        model_adapter: object = _UNSET,
        calibration_configuration: ProbabilityCalibrationConfiguration,
        positive_label: object,
        bin_count: int = 10,
    ) -> None:
        if model_adapter is not _UNSET and not isinstance(
            model_adapter, (LogisticRegressionAdapter, RandomForestAdapter)
        ):
            raise TypeError("unsupported model adapter")
        if not isinstance(
            calibration_configuration, ProbabilityCalibrationConfiguration
        ):
            raise TypeError(
                "calibration_configuration must be a "
                "ProbabilityCalibrationConfiguration"
            )
        if isinstance(bin_count, bool) or not isinstance(bin_count, int):
            raise TypeError("bin_count must be an integer and must not be bool")
        if bin_count < 2:
            raise ValueError("bin_count must be at least 2")
        self._model_adapter = None if model_adapter is _UNSET else model_adapter
        self._calibration_configuration = calibration_configuration
        self._positive_label = _freeze(positive_label)
        self._bin_count = bin_count

    @property
    def model_adapter(self) -> LogisticRegressionAdapter | RandomForestAdapter | None:
        return self._model_adapter

    @property
    def calibration_configuration(self) -> ProbabilityCalibrationConfiguration:
        return self._calibration_configuration

    @property
    def positive_label(self) -> object:
        return _thaw(self._positive_label)

    @property
    def bin_count(self) -> int:
        return self._bin_count

    def run(
        self,
        uncalibrated: ModelExperimentResult | PreparedModelInput,
        prepared_input: PreparedModelInput | None = None,
    ) -> CalibratedModelExperimentResult:
        """Calibrate an existing experiment without any model training.

        The one-argument form remains for compatibility with earlier callers.
        New orchestration supplies the uncalibrated result explicitly.
        """
        if isinstance(uncalibrated, PreparedModelInput):
            if prepared_input is not None or self.model_adapter is None:
                raise TypeError(
                    "an uncalibrated experiment and PreparedModelInput are required"
                )
            from models.experiment_runner import ModelExperimentRunner

            prepared_input = uncalibrated
            uncalibrated = ModelExperimentRunner(
                model_adapter=self.model_adapter,
                positive_label=self._positive_label,
            ).run(prepared_input)
        if not isinstance(uncalibrated, ModelExperimentResult):
            if self.model_adapter is not None:
                raise TypeError("prepared_input must be a PreparedModelInput")
            raise TypeError("uncalibrated must be a ModelExperimentResult")
        if not isinstance(prepared_input, PreparedModelInput):
            raise TypeError("prepared_input must be a PreparedModelInput")
        evaluator = ProbabilityCalibrationEvaluator(
            positive_label=self._positive_label,
            bin_count=self.bin_count,
        )
        validation_before = evaluator.evaluate_uncalibrated(
            uncalibrated.validation_prediction, prepared_input.validation.y
        )
        test_before = evaluator.evaluate_uncalibrated(
            uncalibrated.test_prediction, prepared_input.test.y
        )

        calibrator = ModelProbabilityCalibrator(self.calibration_configuration)
        prepared_calibrator = calibrator.fit(
            uncalibrated.validation_prediction, prepared_input.validation.y
        )
        calibrated_validation = calibrator.calibrate(
            prepared_calibrator, uncalibrated.validation_prediction
        )
        calibrated_test = calibrator.calibrate(
            prepared_calibrator, uncalibrated.test_prediction
        )
        validation_after = evaluator.evaluate_calibrated(
            calibrated_validation, prepared_input.validation.y
        )
        test_after = evaluator.evaluate_calibrated(
            calibrated_test, prepared_input.test.y
        )
        validation_comparison = evaluator.compare(validation_before, validation_after)
        test_comparison = evaluator.compare(test_before, test_after)

        return CalibratedModelExperimentResult(
            dataset_name=prepared_input.dataset_name,
            dataset_version=prepared_input.dataset_version,
            model_name=uncalibrated.model_name,
            calibration_method=self.calibration_configuration.method,
            uncalibrated_experiment=uncalibrated,
            prepared_calibrator=prepared_calibrator,
            calibrated_validation_prediction=calibrated_validation,
            calibrated_test_prediction=calibrated_test,
            uncalibrated_validation_calibration=validation_before,
            calibrated_validation_calibration=validation_after,
            validation_calibration_comparison=validation_comparison,
            uncalibrated_test_calibration=test_before,
            calibrated_test_calibration=test_after,
            test_calibration_comparison=test_comparison,
            metadata=prepared_input.metadata,
        )
