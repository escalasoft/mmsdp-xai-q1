"""Repository scaffold and approved governance-baseline contract tests."""

import hashlib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

SRC_PACKAGES = [
    "extraction",
    "preprocessing",
    "feature_engineering",
    "dataset",
    "models",
    "multimodal",
    "calibration",
    "explainability",
    "evaluation",
    "utils",
    "visualization",
]

CONFIG_DIRS = [
    "dataset",
    "features",
    "preprocessing",
    "models",
    "fusion",
    "calibration",
    "evaluation",
    "explainability",
    "experiments",
]

GOVERNANCE_BASELINE = {
    "docs/PROJECT_CONTEXT.md": (
        "0b64b07f535846784c313d6791331355c6a9a85db5eb49041a7755f4b34426be"
    ),
    "docs/IMPLEMENTATION_ARCHITECTURE.md": (
        "6b55990405b37a64bde045f335b7d873736c127de47a6ed519b13090dd6cdd46"
    ),
    "docs/SYSTEM_ARCHITECTURE.md": (
        "425a22a8d3629589fe338cf333037d81cc730a44c57148d5d7847e1d6d5fca4e"
    ),
    "docs/DATASET_SPECIFICATION.md": (
        "1dc7f7054764a00a662b3a0917c3c6010ef3196d927009b5949950a249ce1ab7"
    ),
    "docs/FEATURE_SPECIFICATION.md": (
        "c84cb8211205b4d71d544574c6fe4dafe048603079bfe0bd741142beeec22763"
    ),
    "docs/REVIEWER_TRACEABILITY_MATRIX.md": (
        "3c0ca596c702dca56177c6d4d6c2556bbbbb3756380c4ca12ae168f8d6c5d100"
    ),
    "docs/DESIGN_DECISIONS.md": (
        "4c2196cb7b1552145f81394994ea3da0eadb6c851eaccaf4f2746f9ac84403ca"
    ),
    "docs/QUALITY_REQUIREMENTS.md": (
        "4723550c9e170c162cf3b823d5f157642e28d676b22373ddb160de076ef2f89b"
    ),
    "docs/RISK_REGISTER.md": (
        "4618181505f036a6a5b1fd010d3553058183e085651255c4caedffe53d1b45c6"
    ),
    "docs/EXPERIMENT_QUALITY_GATES.md": (
        "f8bd3b57ae8d9f5acbd24782dc8436130f7dccb2b89ca7ab9fac5ad38ca94e68"
    ),
}


def test_required_governance_documents_exist() -> None:
    for doc in GOVERNANCE_BASELINE:
        assert (REPO_ROOT / doc).is_file(), f"Missing governance document: {doc}"


def test_required_src_packages_exist_with_init_files() -> None:
    for package in SRC_PACKAGES:
        package_path = REPO_ROOT / "src" / package
        assert package_path.is_dir(), f"Missing source package: {package_path}"
        assert (package_path / "__init__.py").is_file(), (
            f"Missing package initializer: {package_path / '__init__.py'}"
        )


def test_required_configuration_directories_exist() -> None:
    for directory in CONFIG_DIRS:
        config_path = REPO_ROOT / "configs" / directory
        assert config_path.is_dir(), f"Missing config directory: {config_path}"


def test_governance_documents_are_not_modified() -> None:
    for doc, expected_digest in GOVERNANCE_BASELINE.items():
        actual_digest = hashlib.sha256((REPO_ROOT / doc).read_bytes()).hexdigest()
        assert actual_digest == expected_digest, (
            f"Governance document differs from the approved baseline: {doc}. "
            "Update GOVERNANCE_BASELINE only through an authorized governance sprint."
        )
