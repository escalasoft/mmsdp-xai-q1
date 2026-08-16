# JIT-Defects4J Migration Preparation Gate

Decision: **GO**

## Frozen provenance

- JIT-Fine revision: `584799fdec6095ab75a45fd2a5f8db5b12163aa5`
- `data.zip`: 75326372 bytes; SHA-256 `9e5ca1a393b70ee7e87c410b162005958775f3f3732f9f83da9dd24a7dfe2b47`
- DOI: `10.1145/3540250.3549165`

## Dataset inventory

- Commits: 27319 (2332 positive; 24987 nominal negative)
- Projects: 21: ant-ivy, commons-bcel, commons-beanutils, commons-codec, commons-collections, commons-compress, commons-configuration, commons-dbcp, commons-digester, commons-io, commons-jcs, commons-lang, commons-math, commons-net, commons-scxml, commons-validator, commons-vfs, giraph, gora, opennlp, parquet-mr
- Line observations in the published buggy-line table: 26104 (2060 buggy; 24044 nominal clean; 475 commits)
- Missing parent fields in package: 2; duplicate project-qualified IDs: 0

## Repository, parent, and temporal gate

- Resolved commits: 27319; unresolved: 0; parent mismatches: 0
- Canonical timestamp: Git committer timestamp; author/committer values differ for 1095 observations.
- Supplied partitions fail strict per-project chronology for 21 projects and are not reused.
- Projects with a class-sparse partition under the design-only 70/15/15 policy: commons-beanutils, commons-dbcp, gora

## Scientific contracts

- Positive target: published benchmark defect-inducing label derived from manually validated fixing-line evidence and blame attribution; not recreated.
- Negative policy: closed-world nominal negative; not exhaustively proven defect-free.
- Human validation: not required for primary adoption; optional independent stratified sensitivity audit.
- Leakage: fail-closed denylist and separate CODE/PROCESS/TEXT allowlists; target, line label, classification, fix, SZZ/blame, future metadata, and supplied split are prohibited predictors.
- CODE: exact Git parent diffs only. PROCESS: ancestor-only history. TEXT: raw provenance plus deterministic leakage masking; representations fit on TRAIN only.
- TEST is excluded from fitting, preprocessing fitting, selection, thresholds, calibration, and feature selection.

## Process-history probe

- `{'status': 'pass', 'project': 'ant-ivy', 'commit_hash': '000c0f0f0354bd6facb653ebc9b21317cb183788', 'predecessor_boundary': '14c16b3535c5b2d7ee976c7637144b06cea1e1cb', 'history_range': 'ancestors(14c16b3535c5b2d7ee976c7637144b06cea1e1cb)', 'preceding_commit_count': 388, 'only_ancestors_consumed': True}`

## Reuse and threats

The framework-neutral digest/identity and immutable model-input contracts are reusable. Qt-specific acquisition, issue linkage, SZZ/target construction, and global split code are not. Threats include upstream history rewrites after the frozen snapshots, pickle portability/security, benchmark closed-world negatives, two package parent omissions, author-date rewriting, class sparsity, and text masking construct loss.

## Reproducibility identities

- Schema: `jit-defects4j-migration-audit-1.0.0`
- Configuration digest: `93b7dd791ed200103d3773e2b04384005ae9815a9207de4d1c02ef2185267311`
- Report identity digest: `ad2e761920fca085ecd81ffd98a3ebaf6f54005dc5eb226be9898494d54713e2`
- `audit.json` SHA-256: `d8878732bed5e532dde57d4ca2d4ed976740890c4ed527d82161e5f7e4e714e9`

## Exact next action

Implement immutable JIT-Defects4J materialization from these pinned sources using Git committer time and the frozen project-aware split; do not train models.
