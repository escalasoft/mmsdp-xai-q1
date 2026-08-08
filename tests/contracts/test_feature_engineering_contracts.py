from dataclasses import is_dataclass

import feature_engineering

EXPECTED_EXPORTS = {
    "CodeFeatureRecord",
    "FeatureArtifact",
    "FeatureEngineeringError",
    "FeatureModality",
    "ProcessFeatureRecord",
    "TextFeatureRecord",
    "generate_code_features",
    "generate_process_features",
    "generate_text_features",
    "write_code_features",
    "write_process_features",
    "write_text_features",
    "QtFeatureAdmissibility",
    "QtFeatureDataType",
    "QtFeatureDefinition",
    "QtFeatureInventory",
    "QtFeatureLeakageClassification",
    "QtFeatureMissingPolicy",
    "build_qt_feature_inventory",
}


def test_package_has_stable_explicit_exports() -> None:
    assert set(feature_engineering.__all__) == EXPECTED_EXPORTS
    assert all(hasattr(feature_engineering, name) for name in EXPECTED_EXPORTS)


def test_contracts_are_frozen_and_exclude_forbidden_fields() -> None:
    record_types = (
        feature_engineering.CodeFeatureRecord,
        feature_engineering.ProcessFeatureRecord,
        feature_engineering.TextFeatureRecord,
        feature_engineering.FeatureArtifact,
    )
    prohibited = {"label", "target", "defect", "split", "probability", "prediction"}
    for record_type in record_types:
        assert is_dataclass(record_type)
        assert record_type.__dataclass_params__.frozen
        assert prohibited.isdisjoint(record_type.__dataclass_fields__)
