# Sprint 50-R2 large-artifact packaging correction

**Classification:** `PASS_50_R2_LARGE_ARTIFACT_PACKAGING_CORRECTION`

This packaging-only correction excludes the large raw-probability ledger from ordinary Git tracking while leaving it at its original local path. No model, prediction, metric, statistical result, threshold, calibration state, temporal fold, label, feature, T1/T2 evidence, or XAI state changed.

## External artifact identity

- Original path: `audits/q1-temporal-robustness-cv/1.0.0/raw_probability_provenance.jsonl.gz`
- Compressed size: 96315731 bytes
- SHA-256: `94be037a1ed99e71b11bc1ae9733c1cffeef7ad5b881a5e48039fbd2b8145203`
- Records: 1928304
- External storage status: `NOT_YET_MATERIALIZED`
- External URL: none assigned.

## Packaging and manifest policy

`.gitignore` contains one exact repository-relative rule for this ledger. `MANIFEST.sha256` is now the Git-tracked lightweight-package manifest and excludes only the declared ledger. `external_artifact_inventory.json` separately freezes its size, hash, record count, schema, provenance, generation contract, expected materialization path, and verification rule.

## Scientific equality and calibration dependency

`scientific_equality_verification.json` proves the protected Sprint 50 results remain byte-identical. Future calibration must first materialize the ledger at the declared path (or an explicitly resolved durable copy) and run the inventory verifier. Missing data, hash/size/count drift, gzip damage, or schema drift fails closed before calibration.

## Reproduction

Verification command: `PYTHONPATH=src .venv/bin/python -m experimentation.q1_sprint50_large_artifact_packaging --root . --verify`

Recorded branch: `sprint-10/q1-robustness-cv-statistics-calibration`; HEAD: `2a140be481d29949d2fe0fd74dc5c99aeeecd143`.
