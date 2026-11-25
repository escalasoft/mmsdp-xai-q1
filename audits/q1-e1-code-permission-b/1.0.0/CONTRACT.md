# E1-CODE Permission B — synthetic extractor contract v1.0.0

Status: synthetic implementation only. Permission C is not granted. Historical
contracts, model state, tolerances and the real 245/8 identity universe are not
changed. The real CODE file must not be opened by this implementation or tests.

## Entry points and process boundaries

`src/governance/e1_code_synthetic_extractor.py:extract_synthetic` accepts only a
regular, non-symlink `fixture.code.jsonl.gz` in a directory named
`e1-code-b-synthetic-*`, with canonical parent path. Contracts accept invented
identifiers `synthetic-row-NNNN` only. There is no production CLI or real identity
adapter. This gate prevents accidental use; it is not a hostile-user security
boundary (a user able to change code or stage hard links is outside its threat
model).

The broker opens a fixture read-only with O_NOFOLLOW and a shared advisory lock.
It checks identity, size, mtime and ctime before/after reading, checks the complete
compressed SHA-256 against the predeclared fixture digest, and captures immutable
compressed bytes in bounded memory. The worker receives those bytes and the
contract over an explicit pipe, never a source path or inherited source file
descriptor. The source is closed before worker creation. The worker independently
checks the digest and uses no source filesystem access.

The worker is a fresh Python process with isolated imports, bytecode disabled,
closed inherited descriptors and a 10-second timeout. After imports, an audit hook
rejects file opens, common filesystem mutations, process creation and sockets.
It returns only a complete validated result or the constant `REJECTED`. The broker
raises only `EXTRACTION_REJECTED`, without original exception chaining. No logging,
model loading, fitting, transformation or scientific computation is implemented.

A synthetic consumer process is tested with rows only and an audit policy that
denies opening the source. No actual E1 process is invoked or modified. These
Python policies and process separation are defense in depth for trusted code,
not an OS-enforced sandbox against arbitrary native code or a malicious process.

## Input, identity, order and types

The immutable contract declares SHA-256, ordered target identifiers, local-case
identifiers, start/stop line boundaries, compressed-byte bound, line bound,
decompressed-byte bound and a type for each feature before execution.

Source format is a single gzip stream containing newline-delimited JSON. The
worker decodes one output byte at a time and stops exactly after the stop-th LF.
Positions are transport boundaries only. Each target row must match the exact
predeclared identity at that position; identities are never reconstructed from
row indices. The expected identity set is unique, local cases are a subset, and
the target count equals stop-start. Prefix rows before start are discarded
without JSON interpretation and without downstream scientific use.

Target rows must contain exactly `row_identifier, la, ld, nf, nd, ns, ent`.
Additional or missing fields, duplicate JSON keys, unexpected/duplicate/missing
identities and reordered rows cause total rejection. Tests use int for the first
five features and float for ent. These are explicit synthetic types, not a claim
about unobserved real T1 scalar types. The contract supports a predeclared int or
float per feature; bool, null, strings and containers are rejected. No conversion
between int and float is allowed, and all floats must be finite. Numeric values
and Python scalar types are preserved; original lexical JSON spelling is not
preserved. Future lexical/precision requirements must be settled before C.

## Output, atomicity and bounds

The scientific output is the `rows` list, whose rows have only the seven allowed
fields. A separate `transport` envelope reports counts for synthetic validation;
it is not a feature column and must not be delivered as E1 input. No output file
or snapshot is written by the extractor. Staged rows remain private until the
entire target segment validates. Last-row errors release no partial rows.

Hard ceilings: source 8 MiB, request 12 MiB, response 2 MiB, stop 5145 lines,
targets 245 rows, line 16 KiB, total emitted decompressed bytes 8 MiB. Each contract
may tighten these limits. Only one line and the bounded target set are staged.
The broker/IPC use several bounded copies of compressed/request bytes; this is
not an 8 MiB total RSS claim. No OS memory limit is enforced. Decompressor native
state and interpreter overhead are additional. Timeout and logical size bounds
are enforced. Filesystem caches, process RSS and kernel buffers are not measured.

## Integrity and concurrency

Source replacement or detectable modification during capture is rejected. The
whole-file digest also rejects changed bytes even if stat metadata are restored.
After successful capture, later changes to the path do not affect extraction:
the worker consumes the already verified immutable bytes. A test deliberately
changes the source after capture and verifies the original approved result.
This is snapshot-in-memory consistency, not a claim that the path stays unchanged.
The advisory lock is not a guarantee against uncooperative writers.

Truncation/corruption against an approved digest is rejected before decoding.
Premature decoded EOF is rejected even if a synthetic contract is given the
truncated stream's hash. A prefix reader cannot verify the final gzip trailer or
CRC without decoding the tail; integrity of that tail relies on the approved
complete digest. A deliberately corrupt tail with a newly approved digest is
outside the guarantee. Expected digests must never be recomputed to accept a
failed real source.

The decoder emits no bytes after the target LF; compressed bytes/bits and native
decompressor buffers are not asserted to have a clean physical T1/T2 boundary.
Synthetic tail noninterference concerns scientific rows, not the full-file digest
or compressed transport counts, which can legitimately change with compression.

## Permission C prerequisites and stop

Before any real route is enabled: explicit new human authorization; approval of
the real identity adapter and scalar-type rule; review of all tests; a decision
on OS-enforced consumer isolation; explicit approval of complete compressed-byte
capture/retention in RAM and whole-file verification within the real extraction
operation; approved resource limits and retention/persistence policy. Permission
A's earlier PASS does not replace checking the bytes actually extracted.

No real extraction, inference, SHAP or E1 follows this synthetic validation.
No acceptance rule, population, model or predictive tolerance may be adjusted
based on real results. Any error requires complete rejection and human review.
