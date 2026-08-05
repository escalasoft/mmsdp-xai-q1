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
        "b34c9c33e05ef53e1c278f7962af9eac822c7d5b83c8a9be20ccd124cc9beb19"
    ),
    "docs/SYSTEM_ARCHITECTURE.md": (
        "425a22a8d3629589fe338cf333037d81cc730a44c57148d5d7847e1d6d5fca4e"
    ),
    "docs/DATASET_SPECIFICATION.md": (
        "1dc7f7054764a00a662b3a0917c3c6010ef3196d927009b5949950a249ce1ab7"
    ),
    "docs/FEATURE_SPECIFICATION.md": (
        "aa61d28e81a5f665c5684b3229a2a49be2ee2bdcb5273c8572fba5730e13b83a"
    ),
    "docs/REVIEWER_TRACEABILITY_MATRIX.md": (
        "3f200187cb819571b7babcec05623efad7915da035d9d28a5356b1ca8cf10ea8"
    ),
    "docs/DESIGN_DECISIONS.md": (
        "ea46fd612146ceb7e545e4760e4c084b6fba4528e0e9e2453488c6187350a7bc"
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
