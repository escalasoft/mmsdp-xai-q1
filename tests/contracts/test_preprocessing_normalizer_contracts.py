"""Public API contracts for train-fitted preprocessing normalization."""

import inspect
from dataclasses import FrozenInstanceError, fields, is_dataclass

import pytest

import preprocessing.normalizer as normalizer
from preprocessing.normalizer import (
    FittedNormalizerState,
    NormalizationSpec,
    NormalizedPartitions,
)
from preprocessing.schema import PreprocessingSplit


def test_normalizer_module_exports_exact_public_api() -> None:
    expected = {
        "FittedNormalizer",
        "FittedNormalizerState",
        "NormalizationSpec",
        "NormalizedPartitions",
        "TrainFittedNormalizer",
    }

    assert set(normalizer.__all__) == expected
    assert all(getattr(normalizer, name) is not None for name in expected)


@pytest.mark.parametrize(
    ("contract", "field_names"),
    [
        (NormalizationSpec, ["feature_names"]),
        (
            FittedNormalizerState,
            ["feature_names", "fit_split", "parameters"],
        ),
        (
            NormalizedPartitions,
            [
                "train_records",
                "validation_records",
                "test_records",
                "fitted_state",
            ],
        ),
    ],
)
def test_public_dataclasses_are_immutable_exact_contracts(
    contract: type[object], field_names: list[str]
) -> None:
    assert is_dataclass(contract)
    assert [field.name for field in fields(contract)] == field_names


def test_fitted_state_is_defensively_immutable() -> None:
    source = {"center": [1.0]}
    state = FittedNormalizerState(
        feature_names=["change_size"],  # type: ignore[arg-type]
        fit_split=PreprocessingSplit.TRAIN,
        parameters=source,
    )
    source["center"].append(2.0)

    assert state.feature_names == ("change_size",)
    assert state.parameters == {"center": (1.0,)}
    with pytest.raises(TypeError):
        state.parameters["center"] = [3.0]  # type: ignore[index]
    with pytest.raises(FrozenInstanceError):
        state.fit_split = PreprocessingSplit.TEST  # type: ignore[misc]


def test_public_protocols_expose_only_fit_and_transform_boundaries() -> None:
    assert normalizer.TrainFittedNormalizer._is_protocol  # type: ignore[attr-defined]
    assert normalizer.FittedNormalizer._is_protocol  # type: ignore[attr-defined]

    fit_parameters = inspect.signature(normalizer.TrainFittedNormalizer.fit).parameters
    transform_parameters = inspect.signature(
        normalizer.FittedNormalizer.transform
    ).parameters
    assert list(fit_parameters) == ["self", "training_data", "spec"]
    assert fit_parameters["spec"].kind is inspect.Parameter.KEYWORD_ONLY
    assert list(transform_parameters) == ["self", "dataset"]


def test_fitted_state_rejects_non_training_fit_provenance() -> None:
    with pytest.raises(ValueError, match="fit_split must be"):
        FittedNormalizerState((), PreprocessingSplit.VALIDATION, {})


def test_contract_module_does_not_load_scientific_libraries() -> None:
    source = inspect.getsource(normalizer)

    assert "import pandas" not in source
    assert "import numpy" not in source
    assert "import sklearn" not in source
