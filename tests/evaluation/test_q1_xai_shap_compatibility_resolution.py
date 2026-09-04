# ruff: noqa: E501

import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = ROOT / "audits/q1-xai-runtime-freeze/1.0.0"
PACKAGE = ORIGINAL / "amendments/shap_compatibility_resolution/1.0.0"


def load(name):
    return json.loads((PACKAGE / name).read_text())


def test_all_required_shap_candidates_and_broken_intermediate_release_are_recorded():
    rows = load("shap_release_matrix.json")["rows"]
    versions = {row["version"] for row in rows}
    assert {"0.47.0", "0.47.1", "0.47.2", "0.48.0", "0.49.1", "0.50.0", "0.51.0", "0.52.0"} <= versions
    assert next(row for row in rows if row["version"] == "0.49.0")["release_status"] == "MAINTAINER_DOCUMENTED_BROKEN_RELEASE_NOT_PRESENT_IN_PYPI_RELEASE_INDEX"
    assert all("authoritative_metadata" in row for row in rows)


def test_numba_064_and_later_are_explicitly_accepted_for_numpy_246_not_generalized_from_0621():
    matrix = load("numba_compatibility_matrix.json")
    rows = {row["version"]: row for row in matrix["rows"]}
    assert matrix["numba_0_62_1_generalized_to_newer_versions"] is False
    assert matrix["numba_0_64_plus_explicitly_audited"] is True
    assert rows["0.62.1"]["numpy_2_4_6_supported"] is False
    for version in ("0.64.0", "0.65.0", "0.65.1", "0.66.0", "0.67.0"):
        assert rows[version]["numpy_2_4_6_supported"] is True
        assert rows[version]["compatibility_with_frozen_runtime"] == "NUMPY_COMPATIBLE_PLATFORM_UNSUPPORTED"


def test_platform_wheel_gap_is_precisely_separated_from_numpy_compatibility():
    wheels = load("platform_wheel_inventory.json")
    numba = {row["version"]: row for row in wheels["Numba"]}
    llvm = {row["version"]: row for row in wheels["llvmlite"]}
    assert numba["0.62.1"]["classification"] == "COMPATIBLE_BINARY_WHEEL_AVAILABLE"
    assert all(numba[v]["classification"] == "SOURCE_BUILD_ONLY" for v in ("0.64.0", "0.65.0", "0.65.1", "0.66.0", "0.67.0"))
    assert llvm["0.45.1"]["classification"] == "COMPATIBLE_BINARY_WHEEL_AVAILABLE"
    assert all(llvm[v]["classification"] == "SOURCE_BUILD_ONLY" for v in ("0.46.0", "0.47.0", "0.48.0", "0.49.0"))


def test_complete_transitive_matrix_derives_exact_allowed_reason_classes():
    matrix = load("transitive_runtime_compatibility_matrix.json")
    assert matrix["tuple_count"] == 64
    assert sum(matrix["classification_counts"].values()) == 64
    assert set(matrix["classification_counts"]) <= {"INCOMPATIBLE_PYTHON", "INCOMPATIBLE_NUMPY", "INCOMPATIBLE_NUMBA", "INCOMPATIBLE_PLATFORM_WHEEL", "INCOMPATIBLE_LLVMLITE", "INCOMPATIBLE_OTHER_DEPENDENCY", "METADATA_INSUFFICIENT"}
    assert "INCOMPATIBLE_PLATFORM_WHEEL" in matrix["classification_counts"]
    assert not any(row["classification"] == "COMPATIBLE_BY_AUTHORITATIVE_METADATA" for row in matrix["rows"])


def test_resolution_preserves_original_and_selects_no_package():
    result = load("shap_runtime_resolution.json")
    assert result["original_runtime_freeze_outcome"] == "SHAP_RUNTIME_VERSION_UNRESOLVED"
    assert result["amendment_outcome"] == "SHAP_RUNTIME_REQUIRES_ISOLATED_XAI_ENVIRONMENT_OR_RUNTIME_AMENDMENT"
    assert result["selected_SHAP_version"] is None
    assert result["selected_NumBa_version"] is None
    assert result["selected_llvmlite_version"] is None
    assert result["wheel_filename"] is result["wheel_sha256"] is None
    assert result["installation_performed"] is result["XAI_executed"] is result["predictive_runtime_changed"] is False
    assert result["T1_access"] == result["T2_access"] == 0


def test_capabilities_are_documented_but_exact_model_libraries_require_smoke_test():
    rows = load("required_xai_capability_matrix.json")["candidates"]
    assert len(rows) == 8
    assert all(row["Random_Forest"] == "CAPABILITY_METADATA_SUPPORTED" for row in rows)
    assert all(row["XGBoost"] == row["LightGBM"] == "CAPABILITY_METADATA_SUPPORTED" for row in rows)
    assert all(row["approximate_false"] == "CAPABILITY_METADATA_SUPPORTED" for row in rows)
    assert all(row["exact_XGBoost_3_2_0"] == row["exact_LightGBM_4_6_0"] == "MODEL_LIBRARY_COMPATIBILITY_REQUIRES_SANDBOX_SMOKE_TEST" for row in rows)


def test_predictive_runtime_scope_and_all_counters_are_immutable():
    record = load("predictive_runtime_immutability.json")
    assert record["frozen_predictive_runtime"] == {"Python": "3.11.14", "NumPy": "2.4.6", "SciPy": "1.17.1", "scikit-learn": "1.9.0", "XGBoost": "3.2.0", "LightGBM": "4.6.0"}
    assert record["before"] == record["after"]
    assert record["inventories_identical"] is record["protected_hashes_identical"] is True
    assert all(value == 0 for value in record["counters"].values())
    disposition = load("sprint56_runtime_disposition.json")
    assert disposition["maximum_future_XAI_scope_count"] == 389
    assert len(disposition["excluded_scopes"]) == 3
    assert disposition["analytical_readiness_preserved"] == ["ANALYTICAL_LINEAR_LOGIT_DECOMPOSITION", "ANALYTICAL_LR_FUSION_DECOMPOSITION"]
    assert disposition["Sprint56_authorized"] is False
    assert disposition["XAI_RUNTIME_SMOKE_TEST_REQUIRED"] is True


def test_original_runtime_freeze_files_are_byte_identical():
    expected = {
        "MANIFEST.sha256": "27b12b1f9105c1c9fdbdf9cac9e7a9942ed20f6303586dd54ce84b29c11e5c29",
        "xai_runtime_contract.json": "876836ddef18d5400a870b21997ea68ecc1793dcc48466233cde015e7f03045d",
        "shap_version_freeze.json": "0a04879848b644d85d3f9fba575f876a13a5fe525dae55cab5cf20886904d301",
        "dependency_inventory.json": "8cadaa259cb0528fb5217cc3bd4796c33cfa7ee97cf20460c8b360bc24cdb9d2",
    }
    assert all(hashlib.sha256((ORIGINAL / name).read_bytes()).hexdigest() == digest for name, digest in expected.items())


def test_source_has_no_install_import_execution_or_data_path():
    source = (ROOT / "src/evaluation/q1_xai_shap_compatibility_resolution.py").read_text().lower()
    assert "import " + "shap" not in source
    assert "import " + "lime" not in source
    assert "pip install" not in source
    assert "subprocess" + ".run" not in source
    assert ".fit(" not in source
    assert "predict_proba(" not in source
    assert "t2_rel" not in source


def test_evidence_registry_and_manifest_are_complete():
    registry = load("compatibility_evidence_registry.json")
    assert registry["unofficial_sources_used"] is False
    authorities = Counter(row["authority"] for row in registry["records"])
    assert authorities["PyPI"] == 21
    assert authorities["Official Numba documentation"] == 1
    assert authorities["Official SHAP release notes"] == 1
    assert authorities["Official SHAP TreeExplainer documentation"] == 1
    required = {"SHAP_COMPATIBILITY_RESOLUTION_REPORT.md", "shap_release_matrix.json", "numba_compatibility_matrix.json", "llvmlite_compatibility_matrix.json", "transitive_runtime_compatibility_matrix.json", "platform_wheel_inventory.json", "required_xai_capability_matrix.json", "compatibility_evidence_registry.json", "shap_runtime_resolution.json", "predictive_runtime_immutability.json", "sprint56_runtime_disposition.json"}
    entries = {}
    for line in (PACKAGE / "MANIFEST.sha256").read_text().splitlines():
        digest, name = line.split("  ", 1)
        entries[name] = digest
    assert set(entries) == required
    assert all(hashlib.sha256((PACKAGE / name).read_bytes()).hexdigest() == digest for name, digest in entries.items())
