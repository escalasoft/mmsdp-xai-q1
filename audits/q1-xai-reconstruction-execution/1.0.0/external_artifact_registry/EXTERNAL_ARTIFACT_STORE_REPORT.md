# External Reconstructed Artifact Store Freeze

## Classification

`EXTERNAL_RECONSTRUCTED_EXECUTABLE_ARTIFACT_STORE`

The object files are generated fitted-state artifacts required for future Sprint 56 XAI. They are not source code and are intentionally excluded from ordinary Git blob storage, but remain scientifically required, locally preserved, and provenance-bound by SHA-256. Git exclusion does not make them disposable.

## Verified disposition

- Object count: 5649
- Total bytes: 2139594110
- Largest object: `objects/fce2084679fed5d607f5e35f0fac702675a7e31a802db5220f7a5b84cc012066.pipeline.joblib` (27691155 bytes)
- Block 7 manifest-referenced objects: 5649
- Missing references: 0
- Orphans: 0
- Integrity: `PASS_EXACT_CONTENT_ADDRESSED_MANIFEST_EQUIVALENCE`
- Store snapshot SHA-256: `5e8ebc15b2377045683978763ecebdb621e5af24cbffddeb0b62d9cf1653dea9`
- Git policy: `/audits/q1-xai-reconstruction-execution/1.0.0/objects/`
- Git-visible Sprint 55 working-tree evidence after object exclusion: 42143545 bytes

## Preservation and restoration

`LOCAL_ARTIFACT_PRESERVATION_REQUIRED_UNTIL_SPRINT56`

Do not delete, clean, relocate, compress, overwrite, or modify this store before the Sprint 56 runtime/environment strategy is finalized. Sprint 56 must fail closed if any required object is absent, has a size mismatch, or fails SHA-256 verification against `external_artifact_inventory.jsonl`.

A future separately authorized publication may deposit a versioned bundle in Zenodo or an equivalent scientific repository with this inventory, checksums, provenance, and DOI/content identifier. No bundle, upload, relocation, or publication occurred in this block.

T1 access, T2 access, model queries, XAI, fitting, reconstruction, and recalibration were all zero. Existing Block 7/7A/7B, G4, G5, and runtime-freeze evidence remained unchanged.
