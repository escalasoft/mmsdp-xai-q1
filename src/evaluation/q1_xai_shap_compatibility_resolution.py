#!/usr/bin/env python3
"""Metadata-only SHAP compatibility-resolution amendment.

No package, model, dataset, explainer, attribution, or metric API is imported
or called. Authoritative release metadata was inspected out of process and is
persisted here as a deterministic evidence matrix.
"""

# ruff: noqa: E501

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

VERSION = "q1-xai-shap-compatibility-resolution-1.0.0"
BRANCH = "sprint-10/q1-xai-governance-protocol"
ORIGINAL = Path("audits/q1-xai-runtime-freeze/1.0.0")
OUTPUT_REL = ORIGINAL / "amendments/shap_compatibility_resolution/1.0.0"
OUTCOME = "SHAP_RUNTIME_REQUIRES_ISOLATED_XAI_ENVIRONMENT_OR_RUNTIME_AMENDMENT"
ORIGINAL_HASHES = {
    "MANIFEST.sha256": "27b12b1f9105c1c9fdbdf9cac9e7a9942ed20f6303586dd54ce84b29c11e5c29",
    "xai_runtime_contract.json": "876836ddef18d5400a870b21997ea68ecc1793dcc48466233cde015e7f03045d",
    "shap_version_freeze.json": "0a04879848b644d85d3f9fba575f876a13a5fe525dae55cab5cf20886904d301",
    "dependency_inventory.json": "8cadaa259cb0528fb5217cc3bd4796c33cfa7ee97cf20460c8b360bc24cdb9d2",
}
EXCLUDED = {
    ("apache/zeppelin", "Logistic Regression", "C+T"),
    ("apache/zeppelin", "Logistic Regression", "P+T"),
    ("apache/zeppelin", "Logistic Regression", "C+P+T"),
}
READY = "FUTURE_PRIMARY_XAI_STATE_READY_PENDING_SEPARATE_RUNTIME_AND_EXECUTION_AUTHORIZATION"


class AuditError(RuntimeError):
    """Fail-closed compatibility-audit integrity error."""


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(canonical(value) + b"\n")
    os.replace(temporary, path)


def inventory() -> dict[str, Any]:
    packages = sorted(
        ({"name": dist.metadata["Name"], "version": dist.version} for dist in importlib.metadata.distributions()),
        key=lambda row: row["name"].lower(),
    )
    return {"packages": packages, "count": len(packages), "sha256": hashlib.sha256(canonical(packages)).hexdigest()}


def verify_original(root: Path) -> dict[str, Any]:
    checked = {}
    for name, expected in ORIGINAL_HASHES.items():
        actual = sha256(root / ORIGINAL / name)
        if actual != expected:
            raise AuditError(f"original runtime freeze changed: {name}")
        checked[f"original_runtime_freeze/{name}"] = {"path": str(ORIGINAL / name), "sha256": actual}
    original_inventory = json.loads((root / ORIGINAL / "dependency_inventory.json").read_text())
    for name, record in original_inventory["parents_after"].items():
        path = root / record["path"]
        actual = sha256(path)
        if actual != record["sha256"]:
            raise AuditError(f"protected parent changed: {name}")
        checked[name] = {"path": record["path"], "sha256": actual}
    return checked


SHAP_DATA = [
    ("0.47.0", "2025-03-05", ">=3.9", "numpy", "numba>=0.54", "shap-0.47.0-cp311-cp311-macosx_10_9_x86_64.whl", "aa357e5e517335cb6dc559f869fa726b6ad0a2936250f74db93869c1a267bc88", "e1f78d885bf4ac388b0030c8ecc35529411650b78d6caa814e2a6e281f7ab395"),
    ("0.47.1", "2025-03-22", ">=3.9", "numpy", "numba>=0.54", "shap-0.47.1-cp311-cp311-macosx_10_9_x86_64.whl", "6afca56a634190133710f65c6618c942083d3533e6d2463bcd65317e12587c4d", "292dc548c53fb0438fddacea793eb3482936621ad50a65529630684155625dce"),
    ("0.47.2", "2025-04-17", ">=3.9", "numpy", "numba>=0.54", "shap-0.47.2-cp311-cp311-macosx_10_9_x86_64.whl", "434a7eb17b11f35893538520cf5da39bcfe95d66873bc316ce241dda29350457", "8a53901fc44396d92a12b985d83ca4a47a7dcc4a04a7f7e556232a35f17d30c8"),
    ("0.48.0", "2025-06-12", ">=3.9", "numpy", "numba>=0.54", "shap-0.48.0-cp311-cp311-macosx_10_9_x86_64.whl", "4a90e6092b127bf2070ac055889c8a10f9cdf47831e4e850e6e70c9ae9fb6572", "f169dc73fe144e70a0331b5507f9fd290d7695a3c7935fa8e4862e376321baf9"),
    ("0.49.1", "2025-10-14", ">=3.9", "numpy", "numba>=0.54", "shap-0.49.1-cp311-cp311-macosx_10_9_x86_64.whl", "1e208a0129c721bd0eba6268a9ffac4610dbc8a833d07d2ad9f39541bb737f06", "1114ecd804fff29f50d522ce6031082fcf42fe4a32fb1b5da233b2415d784c8c"),
    ("0.50.0", "2025-11-11", ">=3.11", "numpy>=2", "numba>=0.54; python_version < '3.14'", "shap-0.50.0-cp311-cp311-macosx_10_9_x86_64.whl", "70a0e9c3b13a2b900ab4777a56d1e6cacddfd95f67cf382cdde24d376fbe13f4", "bdc559acf7f647bc3bb22c6a1fea9f50716ed357ad595bc357b43082ae4dc6b9"),
    ("0.51.0", "2026-03-04", ">=3.11", "numpy>=2", "numba<0.63; sys_platform == 'darwin' and platform_machine == 'x86_64'", "shap-0.51.0-cp311-cp311-macosx_10_9_x86_64.whl", "4b4b81d7401bc821490148a694a9f149f8ef488fa973b49fdc8a7916a572750f", "cfa17ff213657c9d50285aa923d79b0037a62e2ee1a31bc3eec7e196b00bdb59"),
    ("0.52.0", "2026-05-28", ">=3.12", "numpy>=2", "numba<0.63; sys_platform == 'darwin' and platform_machine == 'x86_64'", None, None, "81d4ae478f67f8122de1bb411dc4e3ddff0604cbc27dc9cb8ea66d5c73462fd2"),
]

NUMBA_DATA = [
    ("0.62.1", "2025-09-26", ">=3.10,<3.14", ">=1.22,<1.27 OR >=2.0,<2.4", ">=0.45.0dev0,<0.46", "0.45.1", "numba-0.62.1-cp311-cp311-macosx_10_15_x86_64.whl", "f43e24b057714e480fe44bc6031de499e7cf8150c63eb461192caa6cc8530bc8", "INCOMPATIBLE_NUMPY"),
    ("0.63.0", "2025-12-08", ">=3.10,<3.15", ">=1.22,<1.27 OR >=2.0,<2.4", ">=0.46.0dev0,<0.47", "0.46.0", None, None, "INCOMPATIBLE_NUMPY"),
    ("0.63.1", "2025-12-09", ">=3.10,<3.15", ">=1.22,<1.27 OR >=2.0,<2.4", ">=0.46.0dev0,<0.47", "0.46.0", None, None, "INCOMPATIBLE_NUMPY"),
    ("0.64.0", "2026-02-18", ">=3.10,<3.15", ">=1.22,<1.27 OR >=2.0,<2.5", ">=0.46.0dev0,<0.47", "0.46.0", None, None, "NUMPY_COMPATIBLE_PLATFORM_UNSUPPORTED"),
    ("0.65.0", "2026-03-31", ">=3.10,<3.15", ">=1.22,<1.27 OR >=2.0,<2.5", ">=0.47.0dev0,<0.48", "0.47.0", None, None, "NUMPY_COMPATIBLE_PLATFORM_UNSUPPORTED"),
    ("0.65.1", "2026-04-23", ">=3.10,<3.15", ">=1.22,<1.27 OR >=2.0,<2.5", ">=0.47.0dev0,<0.48", "0.47.0", None, None, "NUMPY_COMPATIBLE_PLATFORM_UNSUPPORTED"),
    ("0.66.0", "2026-06-30", ">=3.10,<3.15", ">=1.22,<1.27 OR >=2.0,<2.5", ">=0.48.0dev0,<0.49", "0.48.0", None, None, "NUMPY_COMPATIBLE_PLATFORM_UNSUPPORTED"),
    ("0.67.0", "2026-08-11", ">=3.10,<3.15", ">=1.22,<1.27 OR >=2.0,<2.6", ">=0.49.0dev0,<0.50", "0.49.0", None, None, "NUMPY_COMPATIBLE_PLATFORM_UNSUPPORTED"),
]

LLVMLITE_DATA = [
    ("0.45.1", ">=3.10", "20.x", "llvmlite-0.45.1-cp311-cp311-macosx_10_15_x86_64.whl", "60f92868d5d3af30b4239b50e1717cb4e4e54f6ac1c361a27903b318d0f07f42", "COMPATIBLE_BINARY_WHEEL_AVAILABLE"),
    ("0.46.0", ">=3.10", "20.x", None, None, "SOURCE_BUILD_ONLY_UNSUPPORTED_PLATFORM"),
    ("0.47.0", ">=3.10", "20.x", None, None, "SOURCE_BUILD_ONLY_UNSUPPORTED_PLATFORM"),
    ("0.48.0", ">=3.10", "22.x", None, None, "SOURCE_BUILD_ONLY_UNSUPPORTED_PLATFORM"),
    ("0.49.0", ">=3.10", "22.x", None, None, "SOURCE_BUILD_ONLY_UNSUPPORTED_PLATFORM"),
]


def shap_matrix() -> list[dict[str, Any]]:
    common = {"scipy_constraint": "unbounded direct requirement", "scikit_learn_constraint": "unbounded direct requirement", "pandas_constraint": "unbounded direct requirement", "packaging_constraint": ">20.9", "slicer_constraint": "==0.0.8", "cloudpickle_constraint": "unbounded direct requirement", "sdist_available": True}
    rows = []
    for version, date, python_req, numpy_req, numba_req, wheel, wheel_hash, sdist_hash in SHAP_DATA:
        if version == "0.52.0":
            outcome, distribution = "INCOMPATIBLE_PYTHON", "NO_COMPATIBLE_DISTRIBUTION"
        elif version == "0.51.0":
            outcome, distribution = "INCOMPATIBLE_NUMPY", "COMPATIBLE_BINARY_WHEEL_AVAILABLE"
        else:
            outcome, distribution = "INCOMPATIBLE_PLATFORM_WHEEL", "COMPATIBLE_BINARY_WHEEL_AVAILABLE"
        rows.append({"version": version, "release_date": date, "requires_python": python_req, "numpy_constraint": numpy_req, "numba_constraint": numba_req, **common, "cp311_darwin_x86_64_wheel": wheel is not None, "wheel_filename": wheel, "wheel_sha256": wheel_hash, "sdist_filename": f"shap-{version}.tar.gz", "sdist_sha256": sdist_hash, "authoritative_metadata": f"https://pypi.org/pypi/shap/{version}/json", "distribution_classification": distribution, "preliminary_compatibility_outcome": outcome})
    rows.append({"version": "0.49.0", "release_date": "2025-10-14", "release_status": "MAINTAINER_DOCUMENTED_BROKEN_RELEASE_NOT_PRESENT_IN_PYPI_RELEASE_INDEX", "distribution_classification": "NO_COMPATIBLE_DISTRIBUTION", "preliminary_compatibility_outcome": "INCOMPATIBLE_OTHER_DEPENDENCY", "authoritative_metadata": "https://shap.readthedocs.io/en/stable/release_notes.html#release-v0-49-0"})
    return sorted(rows, key=lambda row: tuple(int(x) for x in row["version"].split(".")))


def numba_matrix() -> list[dict[str, Any]]:
    rows = []
    for version, date, python_req, numpy_req, llvm_req, llvm_selected, wheel, wheel_hash, outcome in NUMBA_DATA:
        rows.append({"version": version, "release_date": date, "release_status": "STABLE_RELEASE", "python_support": python_req, "numpy_support": numpy_req, "numpy_2_4_6_supported": version >= "0.64.0", "llvmlite_requirement": llvm_req, "representative_llvmlite": llvm_selected, "macos_x86_64_official_support": version == "0.62.1", "cp311_darwin_x86_64_wheel": wheel is not None, "wheel_filename": wheel, "wheel_sha256": wheel_hash, "sdist_available": True, "platform_note": "Official current Numba platform list supports macOS 11+ M1/Arm64, not macOS x86_64" if version >= "0.63.0" else "Published CPython 3.11 macOS x86_64 wheel", "compatibility_with_frozen_runtime": outcome, "metadata_source": f"https://pypi.org/pypi/numba/{version}/json", "support_matrix_source": "https://numba.readthedocs.io/en/stable/user/installing.html#version-support-information"})
    return rows


def llvmlite_matrix() -> list[dict[str, Any]]:
    numba_links = {
        "0.45.1": ["0.62.1"],
        "0.46.0": ["0.63.0", "0.63.1", "0.64.0"],
        "0.47.0": ["0.65.0", "0.65.1"],
        "0.48.0": ["0.66.0"],
        "0.49.0": ["0.67.0"],
    }
    return [{"version": version, "requires_python": python_req, "LLVM": llvm, "compatible_numba_versions": numba_links[version], "cp311_darwin_x86_64_wheel": wheel is not None, "wheel_filename": wheel, "wheel_sha256": wheel_hash, "sdist_available": True, "distribution_classification": "COMPATIBLE_BINARY_WHEEL_AVAILABLE" if wheel else "SOURCE_BUILD_ONLY", "official_macos_x86_64_support": wheel is not None, "support_note": status, "metadata_source": f"https://pypi.org/pypi/llvmlite/{version}/json"} for version, python_req, llvm, wheel, wheel_hash, status in LLVMLITE_DATA]


def transitive_matrix() -> list[dict[str, Any]]:
    rows = []
    for shap_version, *_ in SHAP_DATA:
        for numba_version, _, _, numpy_req, llvm_req, llvm_version, numba_wheel, _, _ in NUMBA_DATA:
            if shap_version == "0.52.0":
                classification, reason = "INCOMPATIBLE_PYTHON", "SHAP requires Python >=3.12"
            elif shap_version == "0.51.0" and numba_version >= "0.63.0":
                classification, reason = "INCOMPATIBLE_NUMBA", "SHAP Darwin x86_64 marker requires numba<0.63"
            elif numba_version < "0.64.0":
                classification, reason = "INCOMPATIBLE_NUMPY", f"Numba {numba_version} requires NumPy <2.4"
            elif numba_wheel is None:
                classification, reason = "INCOMPATIBLE_PLATFORM_WHEEL", "Numba and matching llvmlite lack CPython 3.11 Darwin x86_64 wheels and current official Numba platform support excludes macOS x86_64"
            else:
                classification, reason = "METADATA_INSUFFICIENT", "No authoritative complete tuple"
            rows.append({"SHAP": shap_version, "Numba": numba_version, "llvmlite": llvm_version, "llvmlite_requirement": llvm_req, "Python": "3.11.14", "NumPy": "2.4.6", "SciPy": "1.17.1", "scikit_learn": "1.9.0", "XGBoost": "3.2.0", "LightGBM": "4.6.0", "platform": "Darwin_x86_64", "numba_numpy_constraint": numpy_req, "classification": classification, "exact_reason": reason})
    return rows


def evidence_registry() -> dict[str, Any]:
    response_hashes = {
        "shap/0.47.0": "01a14e2d89fd1c8afb606fd07963abd7257109842834b5603d90dfc21b7e293a", "shap/0.47.1": "ee822a985c1c8e3914898c79fd07d4ebffe2f51a99d41adcdc440b26a7b25d25", "shap/0.47.2": "23d4bda25b21da0a76a6f41f1922d39111b11d86dc2275a3445a1caf3199d4da", "shap/0.48.0": "a0dee2f584cbaf936a128df6d68b13edc23fb4a6ed33f72008b6df4046c10e71", "shap/0.49.1": "abba8291a9f46ba7c97fa23ad3277c489f2880ccd1a3a163e673d0fa85657736", "shap/0.50.0": "5aee8d28c8c403f9bc0ec94bdb696fc4357c1a06eef45771b758f372b3dc75aa", "shap/0.51.0": "034c832dce059a976498a6b74b46cc59da178e0b7f41abeaa2ca3fcee14f3079", "shap/0.52.0": "f7ac2ae61ab81d8b47bfcb2659496b967789ac509d2eb79446ae66ff471e4125",
        "numba/0.62.1": "fbf0fc2c2de4df8faa628f2180431204b95b2e57f244ce014988c5f9a599d0e1", "numba/0.63.0": "aded44e5dd7535c7f5cd43f1ad7ed6a047f0a424072d03ab242e251043c40d89", "numba/0.63.1": "a2c9888bd2d4f583ba4b5887c757ab63f0e8e5893fb71994af77effef1adeaa7", "numba/0.64.0": "1a1626325dccf491768e99e86f2d3f4ac0cd38aa5fa206f695482135c6cb98f5", "numba/0.65.0": "85e58a2d2d2cf8684cc2e4b44ac5f505bc00eda31d67eee00b4a6f402e48e20d", "numba/0.65.1": "458e3435dc4d352d71a29fa98936954d8681dc61c0c2bbcc6428e6a5a53436b2", "numba/0.66.0": "08a278bd1255e36796d6aa66ab0f01ce9710a5fd9352a0438ea33edafd017cc2", "numba/0.67.0": "e2345f16a1f7ae32fcbb75f1b1a4ef1de0894bc55559a5ec3caf6ce854b8abec",
        "llvmlite/0.45.1": "b4ed14f9c05383b195aa37ea452f5463000beb699f33e8e23085afa0df23157f", "llvmlite/0.46.0": "2a43695e63fe53a1978c6d80315f0d8c6dfe3471d16193ea3afe330e88076929", "llvmlite/0.47.0": "c699d12af6d9472f5bbf8435aaf5bb379267de9c6dc0107e74035114ffa43380", "llvmlite/0.48.0": "9f6df03fc305136f598d6711f0c75a1df3e62f5b595f6996baa3f6760d74fc5f", "llvmlite/0.49.0": "a9f23f98e62a42ae239b10db2cbd2f3617eeb529263ba3525d856acd3d38fe5a",
    }
    records = [{"authority": "PyPI", "url": f"https://pypi.org/pypi/{key}/json", "downloaded_response_sha256": value} for key, value in sorted(response_hashes.items())]
    records += [
        {"authority": "Official Numba documentation", "url": "https://numba.readthedocs.io/en/stable/user/installing.html#version-support-information", "downloaded_response_sha256": "13dd6d34cdd0f1ea9d488bfc33754ed505cca3b6c2c23dbb53491a5b8c60db64"},
        {"authority": "Official SHAP release notes", "url": "https://shap.readthedocs.io/en/stable/release_notes.html", "downloaded_response_sha256": "97c6d3c443d4b13129c924f1e030d49260c9d89c4d9338910051b9312cefe099"},
        {"authority": "Official SHAP TreeExplainer documentation", "url": "https://shap.readthedocs.io/en/latest/generated/shap.TreeExplainer.html", "downloaded_response_sha256": "6c3817ad7447de23d22f786804f0a6c55c70719c88830999722558cd9970ff00"},
    ]
    return {"schema_version": VERSION, "source_precedence": ["PYPI_RELEASE_AND_WHEEL_METADATA", "OFFICIAL_NUMBA_SUPPORT_MATRIX", "OFFICIAL_SHAP_DOCUMENTATION_AND_RELEASE_NOTES", "OFFICIAL_LLVMLITE_METADATA", "PROJECT_MAINTAINER_RELEASE_ARTIFACTS"], "records": records, "unofficial_sources_used": False}


def report(timestamp: str, head: str) -> str:
    return f"""# SHAP Compatibility Resolution Amendment

## Final disposition

`{OUTCOME}`

This amendment preserves the original historical result `SHAP_RUNTIME_VERSION_UNRESOLVED`. The exhaustive metadata audit establishes that Numba 0.64.0–0.67.0 **do** support frozen NumPy 2.4.6 and Python 3.11.14; the earlier Numba 0.62.1 constraint was not generalized. The remaining blocker is platform reproducibility: those compatible Numba releases and their llvmlite partners have no CPython 3.11 Darwin x86_64 wheels, and current official Numba support lists macOS only for M1/Arm64. Numba 0.62.1/llvmlite 0.45.1 have x86_64 wheels but require NumPy <2.4. SHAP 0.51.0 additionally pins Numba <0.63 on Darwin x86_64, and SHAP 0.52.0 requires Python >=3.12.

## A–Z findings

- **A:** Original result preserved: `SHAP_RUNTIME_VERSION_UNRESOLVED`.
- **B:** The amendment tested later Numba support and prohibited overgeneralization from 0.62.1.
- **C:** Frozen runtime remains Python 3.11.14, NumPy 2.4.6, SciPy 1.17.1, scikit-learn 1.9.0, XGBoost 3.2.0, LightGBM 4.6.0 on Darwin x86_64.
- **D–E:** SHAP 0.47.0, 0.47.1, 0.47.2, 0.48.0, 0.49.1, 0.50.0, 0.51.0, and 0.52.0 were inspected; maintainer-documented broken 0.49.0 was recorded separately. Only 0.52.0 fails Python 3.11.
- **F–H:** Numba 0.62.1, 0.63.0, and 0.63.1 exclude NumPy 2.4; 0.64.0–0.67.0 support 2.4.6.
- **I–J:** llvmlite 0.45.1 has a CPython 3.11 macOS x86_64 wheel, but its Numba chain excludes NumPy 2.4. llvmlite 0.46–0.49 and Numba 0.63–0.67 are source-only and unsupported for this platform family.
- **K–M:** Official TreeExplainer metadata supports RF/tree models, XGBoost, LightGBM, raw output, and `approximate=False`; exact XGBoost 3.2.0 and LightGBM 4.6.0 integration still requires a future smoke test.
- **N–O:** 64 transitive tuples were evaluated. None is fully compatible with a supported binary chain. Rejections preserve exact Python, NumPy, SHAP–Numba marker, or platform-wheel reason.
- **P–Q:** No candidate selected; package versions and hashes remain null in the resolution record. Candidate wheel/source hashes are retained in the matrices.
- **R–S:** Any future resolution requires installation, but no installation occurred here.
- **T:** Predictive package inventory is identical before and after.
- **U:** The 389-scope universe and three exclusions are unchanged.
- **V:** Analytical LR E1 and analytical fusion E2 readiness remain valid and unexecuted.
- **W–X:** T1 explanation access and T2 access are both zero; T2 remains `DENY_SEALED_REVIEWER_RESERVE`.
- **Y:** Final outcome: `{OUTCOME}`.
- **Z:** Close Sprint 55 with this compatibility fact. Before Sprint 56, human review must choose an isolated supported XAI environment or a prospective runtime amendment, followed by `XAI_RUNTIME_SMOKE_TEST_REQUIRED`; do not start attribution directly.

Branch `{BRANCH}`, HEAD `{head}`, timestamp `{timestamp}`. No package install/uninstall/import, model query, XAI, fitting, reconstruction, recalibration, metric recomputation, T1-row access, or T2 access occurred.
"""


def run(root: Path) -> Path:
    branch = subprocess.check_output(["git", "symbolic-ref", "--short", "HEAD"], cwd=root, text=True).strip()
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    if branch != BRANCH:
        raise AuditError(f"wrong branch: {branch}")
    protected_before = verify_original(root)
    before = inventory()
    installed = {row["name"].lower(): row["version"] for row in before["packages"]}
    frozen = {"numpy": "2.4.6", "scipy": "1.17.1", "scikit-learn": "1.9.0", "xgboost": "3.2.0", "lightgbm": "4.6.0"}
    if platform.python_version() != "3.11.14" or {name: installed.get(name) for name in frozen} != frozen:
        raise AuditError("predictive runtime changed before audit")
    readiness_path = root / "audits/q1-xai-final-output-equivalence-g5/1.0.0/xai_readiness_ledger.jsonl"
    readiness = [json.loads(line) for line in readiness_path.read_text().splitlines()]
    if len(readiness) != 389 or len({row["model_identity_sha256"] for row in readiness}) != 389 or any(row["future_xai_readiness"] != READY for row in readiness):
        raise AuditError("389-scope G5 readiness universe changed")
    if {(row["project"], row["algorithm"], row["configuration"]) for row in readiness} & EXCLUDED:
        raise AuditError("excluded scope entered amendment")

    output = root / OUTPUT_REL
    output.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).isoformat()
    shap = shap_matrix()
    numba = numba_matrix()
    llvm = llvmlite_matrix()
    transitive = transitive_matrix()
    wheels = {"schema_version": VERSION, "target": "CPython_3.11_Darwin_x86_64", "SHAP": [{"version": row["version"], "classification": row["distribution_classification"], "filename": row.get("wheel_filename"), "sha256": row.get("wheel_sha256")} for row in shap], "Numba": [{"version": row["version"], "classification": "COMPATIBLE_BINARY_WHEEL_AVAILABLE" if row["cp311_darwin_x86_64_wheel"] else "SOURCE_BUILD_ONLY", "filename": row["wheel_filename"], "sha256": row["wheel_sha256"]} for row in numba], "llvmlite": [{"version": row["version"], "classification": row["distribution_classification"], "filename": row["wheel_filename"], "sha256": row["wheel_sha256"]} for row in llvm]}
    capabilities = {"schema_version": VERSION, "official_documentation": "https://shap.readthedocs.io/en/latest/generated/shap.TreeExplainer.html", "candidates": [{"SHAP": row["version"], "Random_Forest": "CAPABILITY_METADATA_SUPPORTED", "XGBoost": "CAPABILITY_METADATA_SUPPORTED", "LightGBM": "CAPABILITY_METADATA_SUPPORTED", "raw_margin_output": "CAPABILITY_METADATA_SUPPORTED", "approximate_false": "CAPABILITY_METADATA_SUPPORTED", "exact_XGBoost_3_2_0": "MODEL_LIBRARY_COMPATIBILITY_REQUIRES_SANDBOX_SMOKE_TEST", "exact_LightGBM_4_6_0": "MODEL_LIBRARY_COMPATIBILITY_REQUIRES_SANDBOX_SMOKE_TEST"} for row in shap if row["version"] != "0.49.0"], "execution_performed": False}
    counters = {"XAI_execution_count": 0, "SHAP_import_count": 0, "SHAP_execution_count": 0, "LIME_execution_count": 0, "analytical_feature_attribution_execution_count": 0, "analytical_fusion_attribution_execution_count": 0, "model_query_count": 0, "T1_explanation_access_count": 0, "T2_access_count": 0, "fit_count": 0, "reconstruction_count": 0, "recalibration_count": 0, "metric_recomputation_count": 0, "package_installation_count": 0, "package_uninstallation_count": 0, "predictive_runtime_mutation_count": 0}
    resolution = {"schema_version": VERSION, "original_runtime_freeze_outcome": "SHAP_RUNTIME_VERSION_UNRESOLVED", "amendment_outcome": OUTCOME, "selected_SHAP_version": None, "selected_NumBa_version": None, "selected_llvmlite_version": None, "Python_version": "3.11.14", "NumPy_version": "2.4.6", "platform": "macOS_Darwin_x86_64", "wheel_filename": None, "wheel_sha256": None, "selection_rationale": "No candidate has a complete officially supported CPython 3.11 Darwin x86_64 binary dependency chain while preserving NumPy 2.4.6. Numba >=0.64 resolves NumPy compatibility but not the unsupported platform/wheel gap.", "dependency_chain": {"Numba_0_62_1": "binary available but NumPy<2.4", "Numba_0_64_through_0_67": "NumPy 2.4.6 compatible but no macOS x86_64 Numba/llvmlite wheels and platform not officially supported", "SHAP_0_51_0": "Darwin x86_64 requires numba<0.63", "SHAP_0_52_0": "requires Python>=3.12"}, "capability_status": "GENERAL_CAPABILITY_METADATA_SUPPORTED_EXACT_MODEL_LIBRARY_SMOKE_TEST_REQUIRED", "installation_performed": False, "XAI_executed": False, "predictive_runtime_changed": False, "T1_access": 0, "T2_access": 0}
    disposition = {"schema_version": VERSION, "outcome": OUTCOME, "Sprint56_authorized": False, "XAI_RUNTIME_SMOKE_TEST_REQUIRED": True, "smoke_test_authorized_now": False, "future_smoke_test_requirements": ["IMPORT_SUCCEEDS", "NO_PREDICTIVE_DEPENDENCY_CHANGES", "RF_TREEEXPLAINER_INSTANTIATION", "XGBOOST_TREEEXPLAINER_INSTANTIATION", "LIGHTGBM_TREEEXPLAINER_INSTANTIATION", "EXPECTED_OUTPUT_SCALE", "APPROXIMATE_FALSE", "ONE_NON_T1_TRAIN_ONLY_SYNTHETIC_OR_MINIMAL_ADDITIVITY_CASE"], "analytical_readiness_preserved": ["ANALYTICAL_LINEAR_LOGIT_DECOMPOSITION", "ANALYTICAL_LR_FUSION_DECOMPOSITION"], "analytical_execution_authorized": False, "maximum_future_XAI_scope_count": 389, "excluded_scopes": [list(row) for row in sorted(EXCLUDED)], "recommendation": "Separate human review must choose an isolated supported XAI environment or prospectively authorize a predictive-runtime amendment; then freeze exact artifacts and authorize a sandbox smoke test before XAI."}

    write_json(output / "shap_release_matrix.json", {"schema_version": VERSION, "candidate_count": len(shap), "required_released_candidates_complete": True, "rows": shap})
    write_json(output / "numba_compatibility_matrix.json", {"schema_version": VERSION, "rows": numba, "numba_0_62_1_generalized_to_newer_versions": False, "numba_0_64_plus_explicitly_audited": True})
    write_json(output / "llvmlite_compatibility_matrix.json", {"schema_version": VERSION, "rows": llvm})
    write_json(output / "transitive_runtime_compatibility_matrix.json", {"schema_version": VERSION, "tuple_count": len(transitive), "classification_counts": {name: sum(row["classification"] == name for row in transitive) for name in sorted({row["classification"] for row in transitive})}, "rows": transitive})
    write_json(output / "platform_wheel_inventory.json", wheels)
    write_json(output / "required_xai_capability_matrix.json", capabilities)
    write_json(output / "compatibility_evidence_registry.json", evidence_registry())
    write_json(output / "shap_runtime_resolution.json", resolution)
    write_json(output / "sprint56_runtime_disposition.json", disposition)

    after = inventory()
    protected_after = verify_original(root)
    if before != after or protected_before != protected_after:
        raise AuditError("runtime or protected evidence changed during audit")
    immutability = {"schema_version": VERSION, "branch": branch, "git_HEAD": head, "timestamp_utc": timestamp, "frozen_predictive_runtime": {"Python": "3.11.14", "NumPy": "2.4.6", "SciPy": "1.17.1", "scikit-learn": "1.9.0", "XGBoost": "3.2.0", "LightGBM": "4.6.0"}, "before": before, "after": after, "inventories_identical": True, "protected_before": protected_before, "protected_after": protected_after, "protected_hashes_identical": True, "counters": counters}
    write_json(output / "predictive_runtime_immutability.json", immutability)
    (output / "SHAP_COMPATIBILITY_RESOLUTION_REPORT.md").write_text(report(timestamp, head))
    names = sorted(path.name for path in output.iterdir() if path.is_file() and path.name != "MANIFEST.sha256" and not path.name.endswith(".tmp"))
    (output / "MANIFEST.sha256").write_text("".join(f"{sha256(output / name)}  {name}\n" for name in names))
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    print(run(args.root.resolve()))


if __name__ == "__main__":
    main()
