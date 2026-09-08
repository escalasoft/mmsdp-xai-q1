# Sprint 56.1 — Isolated XAI Runtime + TRAIN-only Smoke Test

`PRIMARY_XAI_ISOLATED_RUNTIME_SMOKE_TEST_PASS`

## A–H. Provenance and frozen state

- **A. Branch / HEAD:** `sprint-10/q1-primary-xai-execution` / `89fe7e1c2da425ea63427d1d699d6f8a531e8c6f`. No commit or push.
- **B. Isolated environment:** `/Users/alex/ESTUDIO/DOCTORADO/Articulos/CONTRIBUCION/MMSDP-XAI-Q1/.venv-xai-s56`; system site packages disabled, narrowly ignored by `/.venv-xai-s56/`.
- **C. Predictive preservation:** inventory unchanged = `True`. Python 3.11.14, NumPy 2.4.6, SciPy 1.17.1, scikit-learn 1.9.0, XGBoost 3.2.0, LightGBM 4.6.0 remain in `.venv`. No predictive requirement edits. Protected Sprint 55 evidence hashes unchanged = `True`.
- **D–E. Exact XAI runtime:** Python `3.11.14`, NumPy `2.3.5`, SciPy `1.17.1`, scikit-learn `1.9.0`, XGBoost `3.2.0`, LightGBM `4.6.0`, SHAP `0.51.0`, Numba `0.62.1`, llvmlite `0.45.1`, joblib `1.5.3`, cloudpickle `3.1.2`. Platform `macOS-15.7.7-x86_64-i386-64bit`, architecture `x86_64`. All five prescribed thread variables equal 1; supported model controls and threadpool limits set to 1 in memory only.
- **F. Installation:** PyPI binary wheels exclusively; zero source builds. The initial sandbox DNS failure was followed by an authorized network retry of the same pins. Full commands, URLs, wheel hashes and dependency metadata are in `isolated_runtime_installation_provenance.json`, `pip-install-report.json`, `isolated_runtime_lock.json` and `requirements-xai-hashed.txt`. Bootstrap pip/setuptools versions are included in the complete lock inventory; Python executable and SHA256 are recorded. `pip check` passed. The NumPy-only change to the predictive-library tuple was chosen before any explanation based on [Numba compatibility](https://numba.readthedocs.io/en/stable/user/installing.html#version-support-information) and [SHAP 0.51.0 metadata](https://pypi.org/pypi/shap/0.51.0/json).
- **G. Object integrity:** 5,649 objects; 2,139,594,110 bytes; zero missing references and orphans. Every SHA256 verified before and after. Store snapshot `5e8ebc15b2377045683978763ecebdb621e5af24cbffddeb0b62d9cf1653dea9` matches Sprint 55. No resaving, conversion or serialization mutation.
- **H. Representatives:** `apache/activemq`, first lexicographic eligible project, repetition `rep_01`. Fixed LR TEXT, RF/XGB/LGB CODE and LR fusion C+P+T cover five families and TF-IDF without performance/attribution selection. G1–G5 universe remains 389 with the exact three apache/zeppelin LR exclusions.

## I–P. Load, fidelity and determinism

| Scope | Load compatibility | Smoke outcome | Max absolute additive residual | Max repeated attribution difference |
|---|---|---|---:|---:|
| Logistic Regression / T | LOAD_COMPATIBLE | LR_ANALYTICAL_SMOKE_PASS | 2.220446049250313e-16 | 0.0 |
| Random Forest / C | LOAD_COMPATIBLE | RF_TREESHAP_SMOKE_PASS | 5.9396931817445875e-15 | 0.0 |
| XGBoost / C | LOAD_COMPATIBLE | XGB_TREESHAP_SMOKE_PASS | 9.5367431640625e-07 | 0.0 |
| LightGBM / C | LOAD_COMPATIBLE | LGB_TREESHAP_SMOKE_PASS | 7.29104276953052e-15 | 0.0 |
| Logistic Regression / C+P+T | LOAD_COMPATIBLE | FUSION_ANALYTICAL_SMOKE_PASS | 0.0 | 0.0 |

**N. TEXT:** `TEXT_ALIGNMENT_SMOKE_PASS`. Exact persisted vocabulary, IDF, token-column map and feature order were compared with the loaded LR vectorizer; transformed TRAIN dimensionality and predictor alignment verified. Fusion uses that same frozen LR TEXT pipeline. Tree TEXT was not selected; no broader text-family compatibility claim is made.

**O. Analytical checks:** LR maximum sigmoid residual `2.7755575615628914e-17`; fusion maximum sigmoid residual `0.0`; fusion centered-logit maximum residual `4.440892098500626e-16`. All per-row values and complete contribution vectors are retained in the family JSON records for both runs. Local checks are the four SHA256-selected rows within the 16-row foreground. No feature/modality/token interpretation or scientific plot was generated.

**P. Repeatability:** tolerance fixed prospectively at 1e-12. Each completed method was instantiated/executed twice; persisted vectors are independently compared by tests. TreeSHAP uses `tree_path_dependent`, `model_output=raw`, `approximate=False`, `check_additivity=True`; RF selects positive-class probability, boosters use native raw margin. Stored TRAIN path counts supply the TreeSHAP background semantics; no explicit background matrix is required. Analytical fusion reference means use 64 TRAIN rows. Fidelity tolerances remain 1e-10 × (1 + |logit|), sigmoid 1e-10, and trees 1e-6 × (1 + |output|).

Exact warnings, including categories, source paths and line numbers, are retained in `model_state_load_compatibility.json`, family JSON records and `smoke-execution-output.txt`; captured warnings were also re-emitted. No warnings were filtered away. Load success is limited to the selected persisted states and is not proof of predictive equivalence across runtimes.

## Q–V. Governance and scientific disposition

- **Q. T1:** access = 0, model queries = 0, row reads = 0. Historical Sprint 54 predictive access/scoring remains 1/1.
- **R. T2:** access = 0; `DENY_SEALED_REVIEWER_RESERVE`.
- **S. Metrics:** predictive metric computations = 0.
- **T. Mutation:** artifact mutations, reconstruction, refit, retraining and recalibration = 0.
- **U. Family support:** 5/5 representative families passed; final classification `PRIMARY_XAI_ISOLATED_RUNTIME_SMOKE_TEST_PASS`.
- **V. Scientific disposition:** `TRAIN_ONLY_RUNTIME_VALIDATION_NO_SCIENTIFIC_XAI_CLAIM`. Sprint 54 `MIXED_CONFIRMATORY_EVIDENCE`, Sprint 55 closed/readiness state, G4 389/389 and G5 389/389 remain accepted without rerunning predictive evaluation.

TRAIN extraction read exactly 3675 first-project TRAIN records in each aligned frozen stream, stopping at its documented chronological prefix boundary. It did not traverse the remaining mixed-population stream, read labels, hash full dataset files, or open T1 prediction evidence. The TRAIN membership digest `3acfd7b19e5e059277ffaeed4751dee21ccf2e8ce8752ac67757b746d18db858` matches persisted final-base provenance. SHA256 selection produced 64 reference, 16 foreground, 4 local and 80 unique TRAIN inputs. Each prefix's compressed-byte boundary and decompressed-prefix digest are logged. These streams contain other partitions later in the files; only the TRAIN prefix was decoded. The Python audit hook governs smoke execution, while prefix extraction is separately bounded and tested; no OS-wide syscall trace is claimed.

## W. Exact Sprint 56.2 prerequisites

1. Human review and explicit separate Sprint 56.2 primary XAI execution authorization naming exact permitted scopes, role, methods, runtime lock and data partition.
2. Accept Sprint 56.1 family support, exact warning ledger, fidelity/additivity and deterministic-repeat evidence; any failure requires a prospectively authorized resolution, never output-driven scope/version changes.
3. Verify this manifest, exact isolated runtime lock, unchanged predictive runtime, and all 5649 immutable objects with 0 missing references and 0 orphans.
4. Preserve 389 G1-G5 eligible scopes and the three apache/zeppelin LR exclusions; separately govern load compatibility for all additional persisted states because five representative scopes do not prove universal compatibility.
5. Explicitly authorize T1 XAI access and query budgets before any T1 read; freeze TRAIN reference, T1 foreground and local SHA256 selections under Sprint 55 contracts before attribution.
6. Retain exact primary method scales, approximate=False, feature order, thread controls, frozen tolerances, query ledger and reproducibility checks.
7. Keep T2 DENY_SEALED_REVIEWER_RESERVE with zero access; no predictive metrics, retraining/refit, reconstruction, recalibration, LIME, PDP/ICE, counterfactuals or permutation importance.
8. Any state conversion, serialization change or scientific visualization outside separately authorized scope requires separate authorization.

`Sprint56_2_authorized=false`. Stop after this TRAIN-only validation. No primary XAI, T1/T2 access, plots, commit or push.

## Validation

`{"deselected": 3, "excluded_tests": {"test_gitignore_is_exact_narrow_and_registry_remains_visible": "Historical Sprint55 uncommitted byte count 42143545 does not apply to this Sprint56.1 worktree; narrow-ignore/visibility checks replaced", "test_isotonic_state_digests_match_persisted_source_and_block7_linkage": "Development probability ledger outside smoke scope", "test_parent_hashes_tolerances_and_calibrators_remain_unchanged": "Would read historical T1 prediction payload"}, "focused_and_sprint55_regression_tests_passed": 51, "git_diff_check": "PASS", "pip_check": "PASS", "protected_data_open_guard_enabled": true, "scientific_explanation_executions_repeated_per_family": 2, "status": "PASS"}`

The focused suite independently verifies persisted equations, additive residuals, repeat differences, deterministic selection, package/path separation, object hashes, prohibited-operation guards and the complete manifest. Relevant Sprint 55 runtime, SHAP compatibility, external-store and G5 regressions run under a protected-data read guard. Three exclusions are explicit: the G5 parent-hash test opens historical T1 predictions; the G5 isotonic linkage test opens an out-of-scope development probability ledger; and the historical external-store ignore test asserts the exact Sprint 55 uncommitted worktree size. Current narrow ignores and evidence visibility are verified by a replacement focused test. No Sprint 55 test or evidence was edited.

Validation development history is retained in `validation_history.json` and the captured test logs. Test-only corrections normalize JSON tuples/lists and restore XGBoost float32 arithmetic after JSON loading. The XGBoost additive sum also passes the original 1e-6 relative tolerance when independently recomputed in float64. No smoke execution, model, scope, version, attribution vector or tolerance was changed or rerun to obtain these test results.

READY FOR HUMAN REVIEW BEFORE PRIMARY XAI EXECUTION AUTHORIZATION
