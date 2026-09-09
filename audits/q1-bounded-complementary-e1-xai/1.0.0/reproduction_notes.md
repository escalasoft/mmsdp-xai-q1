# Reproduction and closed execution boundary

This is a completed bounded execution. Do not rerun against the occupied namespace, start a recovery sprint, mutate parent artifacts, commit, push, or open a PR.

The preserved environment is `.venv-xai-s56` (Python 3.11.14, SHAP 0.51.0); package versions are in `e1_xai_runtime.json`. Attribution execution used one CPU thread and seeds 20260901–20260920. Figure generation uses a separate temporary Python environment whose versions are recorded in `figures/runtime.json`; it did not change the XAI environment.

In an independently authorized fresh reproduction workspace, the stages are `python -m src.evaluation.q1_bounded_complementary_e1_xai --prepare`; if and only if the documented terminal-LF gate fails, the one permitted `--prepare --bounded-repair` restores the exact expected hashes in child copies; then `--execute` executes the frozen families. The final runner records family-local exact TreeSHAP failure and proceeds with the remaining frozen families. The observed RF failure and first/remaining execution logs are retained. No model, vectorizer or tolerance change was used to repair RF.

`src/evaluation/q1_bounded_complementary_e1_publication.py` creates tables from saved valid results; `src/evaluation/q1_bounded_complementary_e1_figures.py` creates SVG and 300-dpi PNG files from those tables. Exact table and manuscript generation scripts used in this run are retained under `runtime/`. Final source hashes and the post-execution formatting/failure-handling changes are disclosed in `implementation_provenance.json`. These scripts are execution provenance, not instructions to launch new work.

Verification reads only this output package, metadata, and TRAIN parent artifacts. The root MANIFEST covers every persisted file other than itself, including the nested TRAIN-copy manifest. Parent checks are read-only. Legacy tests are not all green: the original R4 terminal-LF differences remain in place by design, and are reported rather than silently repaired in parent evidence.
