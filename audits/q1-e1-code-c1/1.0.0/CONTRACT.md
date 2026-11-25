# C.1 candidate — v1.0.0

Permission C is NOT authorized. `extract_real` always rejects. All capture,
decompression and publication tests use invented data. Real identity-only metadata
may be loaded through the pinned adapter. The B implementation, B tests and A/B
audit records remain unchanged.

## Identity adapter

`load_frozen_identities` verifies the exact three SHA-256 values hardcoded in
`HASHES` before parsing metadata. It requires ActiveMQ/T1, exact 245/245/8 unique
cardinalities, lowercase hexadecimal row identifiers, commit SHA format, the
documented project/repository/commit identity formula, matching commit/order keys
across all ledgers and the predeclared ordered temporal membership digest.
Temporal order, foreground order and local selection order remain separate
immutable tuples. No sampling, result-based selection or permutation is derived
from features. The real metadata verification is recorded separately from tests.

## Fixed boundaries and lexical output

Source: exactly 4,985,060 compressed bytes. Transport: at most 5,145 lines; target
indices [4900,5145), exactly 245. Line: at most 4,096 bytes including LF. Emitted
decompressed prefix: at most 4 MiB. Request: 12 MiB. Response: 2 MiB. Worker
timeout: 10 seconds. These constants may not be expanded after real observation.

Each admitted line has exactly row_identifier, la, ld, nf, nd, ns, ent. Duplicate
keys, unexpected keys, incorrect identifiers/order, missing rows and wrong types
are rejected. JSON integer tokens are parsed as integers; decimal/exponent tokens
are validated as Decimal. No binary float conversion occurs. Boolean/null/string/
container values and NaN/Infinity are rejected. A finite decimal such as 1e999 is
not silently converted to binary infinity; binary pipeline compatibility remains
a later, separate check. Original line bytes (including whitespace, numeric
spelling, key order and LF) are retained exactly. No reserialization, imputation,
scaling or predictive conversion is performed.

## Integrity and process boundaries

The broker checks a regular non-symlink synthetic fixture, exact size and metadata,
opens read-only with O_NOFOLLOW, holds a shared advisory lock, reads the bounded
source into immutable memory and checks the approved fixture hash. The worker
checks the same capture hash independently. The broker revalidates the returned
output bytes, ordered identities and hashes before accepting the response.
Detected changes during capture reject it. Changes to the source path after
capture do not change the immutable verified bytes used by the worker.

Both broker and worker possess the complete compressed stream, including bytes
encoding the invented T2 tail. No guarantee of a clean compressed-bit boundary or
native zlib buffer boundary is made. The decoder requests only one output byte at
a time and stops at the target LF. Pre-T1 lines are discarded without JSON parsing.
No T2 rows are emitted or interpreted by the intended control flow. Whole-file
integrity substitutes for verification of the gzip trailer, which cannot be
validated by decoding only the prefix. An expected hash cannot be changed to
accept a corrupted source.

The worker has no source pathname or inherited source descriptor. After imports,
Python audit hooks deny file opens, process creation, sockets and common filesystem
mutations. Tests use a separate consumer with file-open denial. These are trusted-
code controls, not an OS sandbox against arbitrary native code or other same-user
processes. Real E1 integration has not been implemented or tested.

## Atomic publication on macOS

Only complete validated output is passed to the publication function. A mode-0700
staging directory on the same filesystem contains a mode-0600 code_t1.jsonl and
provenance.json. Data and provenance are fsynced, then the directory is published
using Darwin renamex_np with RENAME_EXCL (0x00000004, verified in the local SDK).
An existing or racing destination is never overwritten. This directory rename is
the visibility commit point. No fallible publication work follows that point.
There is one data output, one provenance record, no additional gzip copy and no
feature values in provenance. Provenance includes source/output/code hashes,
identity-order digests, versions, limits and explicit pending memory status.

Failures before rename do not create an accepted destination. Handled failures
remove staging. A crash/kill can leave private incomplete staging; it is NOT an
accepted output and must never be consumed. Power-loss durability of the directory
entry is not proved. POSIX 0700 protects against other UIDs, not another process
with the same UID; Python consumer denial is not a substitute for OS permissions.
A genuinely inaccessible same-user staging area remains an isolation limitation.
The synthetic publication gate is not a hostile-user boundary against code changes
or malicious parent-directory replacement. Future production roots require review.

## Memory: PENDING, not PASS

Logical source, line, decoded, request and response bounds are implemented.
Intermediate Python/base64 copies and interpreter/native memory are additional;
the limits do not constitute an RSS ceiling. capture_output also relies on the
trusted worker enforcing its response bound before emission.

Two disposable macOS processes attempted RLIMIT_AS=64 MiB, with a planned 96 MiB
bytearray or mmap allocation. setrlimit itself raised ValueError in both cases;
the allocations did not proceed. See memory_probe.json. SDK resource.h exposes
RLIMIT_RSS as an alias for RLIMIT_AS, so merely changing the constant name supplies
no demonstrated independent enforcement. No reliable hard total-memory mechanism
has been validated or enabled. `memory_status` explicitly reports PENDING and
hard_total_memory_enforced=false. The test for this status is not a memory PASS.

## Results and authorization boundary

Synthetic tests exercise byte preservation, full target cardinality, both identity
orders, all requested rejection paths, source races, output tampering, atomic
no-overwrite behavior and a genuine ten-second subprocess timeout. Legacy B tests
are rerun unchanged. Real identity metadata are checked without CODE values.

Functional synthetic PASS does not grant Permission C. Overall readiness remains
C CONDITIONAL due to hard total-memory enforcement and same-user/OS isolation,
plus production capture/publication policy and crash-residue handling. New explicit
authorization is required before enabling any real source entry point. No model,
prediction, label, inference, SHAP or E1 operation is authorized here.
