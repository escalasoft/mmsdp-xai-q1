# SHAP Compatibility Resolution Amendment

## Final disposition

`SHAP_RUNTIME_REQUIRES_ISOLATED_XAI_ENVIRONMENT_OR_RUNTIME_AMENDMENT`

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
- **Y:** Final outcome: `SHAP_RUNTIME_REQUIRES_ISOLATED_XAI_ENVIRONMENT_OR_RUNTIME_AMENDMENT`.
- **Z:** Close Sprint 55 with this compatibility fact. Before Sprint 56, human review must choose an isolated supported XAI environment or a prospective runtime amendment, followed by `XAI_RUNTIME_SMOKE_TEST_REQUIRED`; do not start attribution directly.

Branch `sprint-10/q1-xai-governance-protocol`, HEAD `e13e9949a0bc0ea828882c4d22a5de310f909386`, timestamp `2026-09-04T09:44:13.118505+00:00`. No package install/uninstall/import, model query, XAI, fitting, reconstruction, recalibration, metric recomputation, T1-row access, or T2 access occurred.
