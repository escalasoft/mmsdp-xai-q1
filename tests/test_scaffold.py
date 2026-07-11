"""Repository scaffold contract tests for Sprint 1."""

from pathlib import Path
import subprocess


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

GOVERNANCE_DOCS = [
    "docs/PROJECT_CONTEXT.md",
    "docs/IMPLEMENTATION_ARCHITECTURE.md",
    "docs/SYSTEM_ARCHITECTURE.md",
    "docs/DATASET_SPECIFICATION.md",
    "docs/FEATURE_SPECIFICATION.md",
    "docs/DESIGN_DECISIONS.md",
    "docs/QUALITY_REQUIREMENTS.md",
    "docs/RISK_REGISTER.md",
    "docs/EXPERIMENT_QUALITY_GATES.md",
]
def test_required_governance_documents_exist() -> None:
    for doc in GOVERNANCE_DOCS:
        assert (REPO_ROOT / doc).is_file(), (
            f"Missing governance document: {doc}"
        )

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
    result = subprocess.run(
        ["git", "diff", "--exit-code", "--", *GOVERNANCE_DOCS],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_no_python_implementation_modules_were_introduced() -> None:
    python_files = {
        path.relative_to(REPO_ROOT)
        for root in ("src", "tests")
        for path in (REPO_ROOT / root).rglob("*.py")
    }

    allowed_files = {Path("src/__init__.py"), Path("tests/test_scaffold.py")}
    allowed_files.update(Path("src") / package / "__init__.py" for package in SRC_PACKAGES)
    allowed_files.update(
        Path("tests") / package / "__init__.py"
        for package in ("unit", "integration", "contracts", "gates")
    )
    allowed_files.add(Path("tests/__init__.py"))

    assert python_files <= allowed_files
