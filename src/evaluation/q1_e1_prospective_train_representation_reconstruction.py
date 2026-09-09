# ruff: noqa: E501
"""R4: exact bounded TRAIN prefix and standalone frozen TEXT state only.

No fitted predictor deserialization. Numeric states embedded in predictive
pipelines cannot be restored here. Other projects have no admitted byte route.
"""

from __future__ import annotations

import argparse
import base64
import json
import math
import os
import platform
import re
import struct
import tempfile
import zlib
from pathlib import Path

from src.evaluation import q1_e1_prospective_reconstructed_representation_protocol as r3
from src.evaluation.q1_e1_canonical_identity_representation_linkage import row_bytes
from src.evaluation.q1_e1_population_representation_provenance_resolution import (
    canonical,
)

ROOT = r3.ROOT
OUT = "audits/q1-e1-prospective-train-representations/1.0.0"
R3_PIN = "4d5b9370e3c811260cebbca303b86ccc5a3f040be1e8e2ddb522dac488b53596"
FREEZE = "audits/q1-apachejit-final-dataset-freeze/1.0.0"
SMOKE = "audits/q1-primary-xai-runtime-smoke/1.0.0"
STATE = "audits/q1-xai-reconstruction-execution/1.0.0/objects/3ec8674534cc2001e030e56cb9a37bbf8d66d7564b4052084adaae0edc063559.tfidf.json"
STATE_PIN = Path(STATE).name.split(".")[0]
PROJECT = "apache/activemq"
SOURCE = "src/evaluation/q1_e1_prospective_train_representation_reconstruction.py"
TEST = "tests/evaluation/test_q1_e1_prospective_train_representation_reconstruction.py"
PARTIAL = "56_3B_R4_PASS_PARTIAL_TRAIN_RECONSTRUCTION_WITH_PREDECLARED_LIMITATIONS"
BLOCKED = "56_3B_R4_BLOCKED_TRAIN_SOURCE_ADMISSION_INSUFFICIENT"
FAIL = "56_3B_R4_FAIL_TRAIN_RECONSTRUCTION_INTEGRITY"
sha, encode = r3.sha, r3.encode
THREADS = [
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
]


def digest(value):
    return sha(canonical(value))


def verify_r3(d):
    if d["protocol_summary.json"]["verdict"] not in {
        r3.VERDICT,
        "56_3B_R3_PASS_PROSPECTIVE_RECONSTRUCTED_REPRESENTATION_PROTOCOL_AMENDMENT",
    }:
        raise ValueError("R3 PASS required")
    r3.validate_policy(d)
    if any(d["governance_counters.json"][k] for k in r3.b.ZERO):
        raise ValueError("R3 scientific state differs")
    if d["future_execution_policy.json"]["T1_included"]:
        raise ValueError("T1 must remain separate")


def metadata():
    reader = r3.Reader()
    inherited = reader.load()
    path = ROOT / r3.OUT
    raw = (path / "MANIFEST.sha256").read_bytes()
    if sha(raw) != R3_PIN:
        raise ValueError("R3 manifest changed")
    docs = {}
    for line in raw.decode().splitlines():
        h, n = line.split("  ", 1)
        if Path(n).name != n:
            raise ValueError("Invalid R3 manifest")
        data = (path / n).read_bytes()
        if sha(data) != h:
            raise ValueError("R3 artifact changed")
        if n.endswith(".json"):
            docs[n] = json.loads(data)
    verify_r3(docs)
    return inherited, docs, reader.reads


def atomic_file(base, name, raw):
    """No-clobber publication; never overwrite an accepted artifact."""
    base = Path(base)
    if len(raw) >= 25_000_000:
        raise ValueError("Storage cap: STOP before write")
    p = base / name
    if Path(name).is_absolute() or ".." in Path(name).parts or str(Path(name)) != name:
        raise PermissionError("Noncanonical publication path")
    if p.resolve() != p.absolute():
        raise PermissionError("Symlink publication denied")
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".r4-", dir=p.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        if sha(Path(temporary).read_bytes()) != sha(raw):
            raise ValueError("Write integrity failure: STOP")
        os.link(temporary, p)
        os.chmod(p, 0o444)
        directory = os.open(p.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return sha(p.read_bytes())


def source_gate(proof):
    if proof.get("partition") != "TRAIN" or proof.get("project") != PROJECT:
        raise PermissionError("Only proven first-project TRAIN prefix allowed")
    if proof.get("source_class") != "AUTHORITATIVE_FROZEN_SOURCE_WITH_LIMITATION":
        raise PermissionError("Unknown/partial source denied")
    if proof.get("path") not in {
        FREEZE + "/" + n
        for n in ["temporal_partition_manifest.jsonl.gz", "text_dataset.jsonl.gz"]
    }:
        raise PermissionError("No source route admitted")
    for key in ["membership_verified", "producer_order_verified", "boundary_verified"]:
        if proof.get(key) is not True:
            raise PermissionError("Missing source proof")
    if (
        proof.get("decompressed_lines_read") != 3675
        or type(proof.get("compressed_bytes_read")) is not int
        or proof["compressed_bytes_read"] <= 0
    ):
        raise ValueError("Invalid frozen prefix bounds")
    bounds = {
        FREEZE + "/temporal_partition_manifest.jsonl.gz": (
            269397,
            "b86eae216207f4db218c8d99eb791efbd6d17205153dbd7e1d23bfea1825c922",
        ),
        FREEZE + "/text_dataset.jsonl.gz": (
            706809,
            "708d0909cc4d1cb665eab7bd91fcf17f2c3d5ca5ef5e32eb73e235c193b78ee5",
        ),
    }
    if (proof["compressed_bytes_read"], proof["prefix_sha256"]) != bounds[
        proof["path"]
    ]:
        raise PermissionError("Frozen boundary/digest must not expand")
    if not re.fullmatch("[0-9a-f]{64}", proof.get("prefix_sha256", "")):
        raise ValueError("Source digest required")


def bounded_prefix(path, line_count, byte_cap):
    """Never read beyond the precommitted compressed-byte cap; no tail scan."""
    if (
        type(line_count) is not int
        or line_count <= 0
        or type(byte_cap) is not int
        or byte_cap <= 0
    ):
        raise ValueError("Positive integer bounds required")
    decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
    lines, line, consumed = [], bytearray(), 0
    with Path(path).open("rb", buffering=0) as stream:
        while len(lines) < line_count:
            if decoder.unconsumed_tail:
                compressed = decoder.unconsumed_tail
            else:
                if consumed >= byte_cap:
                    raise ValueError("Frozen byte boundary reached: STOP")
                compressed = stream.read(1)
                consumed += len(compressed)
                if not compressed:
                    raise ValueError("Premature prefix EOF")
            byte = decoder.decompress(compressed, max_length=1)
            line.extend(byte)
            if byte == b"\n":
                lines.append(bytes(line))
                line.clear()
    return b"".join(lines), consumed


def read_source(proof):
    source_gate(proof)
    path = ROOT / proof["path"]
    if path.resolve() != path:
        raise PermissionError("Symlink source denied")
    raw, consumed = bounded_prefix(
        path, proof["decompressed_lines_read"], proof["compressed_bytes_read"]
    )
    if consumed != proof["compressed_bytes_read"] or sha(raw) != proof["prefix_sha256"]:
        raise ValueError("Frozen prefix mismatch: STOP")
    return raw


def identities(rows, expected):
    result = []
    seen = set()
    for i, row in enumerate(rows):
        if row.get("partition") != "TRAIN" or row.get("project") != PROJECT:
            raise ValueError("TRAIN partition contamination: FAIL")
        rid = row.get("row_identifier")
        order = row.get("order_key", [])
        if (
            not isinstance(rid, str)
            or not re.fullmatch("[0-9a-f]{64}", rid)
            or rid in seen
        ):
            raise ValueError("Missing/duplicate row identity")
        if len(order) != 2 or not re.fullmatch("[0-9a-f]{40}", order[1]):
            raise ValueError("Commit identity absent")
        seen.add(rid)
        result.append(
            dict(
                train_row_id=rid,
                project=PROJECT,
                commit_identity=order[1],
                canonical_identity_key=[PROJECT, order[1]],
                source_row_reference=f"{FREEZE}/temporal_partition_manifest.jsonl.gz#TRAIN-prefix-line={i + 1}",
                partition="TRAIN",
                modality_availability=dict(CODE=False, PROCESS=False, TEXT=True),
                provenance_strength="FROZEN_PARTITION_FULL_COMMIT_SHA",
                source_digest=expected["prefix_sha256"],
            )
        )
    if [r["train_row_id"] for r in result] != expected["ids"]:
        raise ValueError("Frozen complete membership/order mismatch")
    return result


def validate_text(state):
    if set(state) != {"parameters", "vocabulary", "idf", "feature_order"}:
        raise ValueError("Standalone TEXT state incomplete")
    names = state["feature_order"]
    vocab = state["vocabulary"]
    if (
        not names
        or len(names) != len(set(names))
        or vocab != {n: i for i, n in enumerate(names)}
    ):
        raise ValueError("TEXT token order mismatch")
    if len(state["idf"]) != len(names) or any(
        not math.isfinite(x) or x <= 0 for x in state["idf"]
    ):
        raise ValueError("TEXT IDF invalid")
    required = {
        "lowercase",
        "max_features",
        "min_df",
        "ngram_range",
        "norm",
        "sublinear_tf",
        "token_pattern",
    }
    if set(state["parameters"]) != required:
        raise ValueError("Frozen tokenizer parameters incomplete")


def transform_text(messages, state):
    """Restore explicit state, never fit or deserialize an estimator."""
    validate_text(state)
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer

    parameters = dict(state["parameters"])
    parameters["ngram_range"] = tuple(parameters["ngram_range"])
    vectorizer = TfidfVectorizer(vocabulary=state["vocabulary"], **parameters)
    vectorizer.idf_ = np.asarray(state["idf"], dtype=np.float64)
    if vectorizer.get_feature_names_out().tolist() != state["feature_order"]:
        raise ValueError("Restored feature order differs")
    matrix = vectorizer.transform(messages).tocsr()
    matrix.sort_indices()
    return matrix


def integrity(matrix, row_ids, names):
    import numpy as np

    if len(row_ids) != len(set(row_ids)) or len(names) != len(set(names)):
        raise ValueError("Duplicate identities/columns")
    if matrix.shape != (len(row_ids), len(names)) or matrix.dtype.str != "<f8":
        raise ValueError("Matrix schema/dtype mismatch")
    if not np.isfinite(matrix.data).all():
        raise ValueError("NaN/Inf forbidden")
    matrix.check_format(full_check=True)
    if not matrix.has_canonical_format:
        raise ValueError("Noncanonical CSR")
    nonzero = np.asarray(matrix.getnnz(axis=0)).ravel()
    if not matrix.nnz or (nonzero == 0).any():
        raise ValueError("Unexpected all-zero TRAIN vocabulary columns")
    constant_count = int(
        (matrix.min(axis=0).toarray() == matrix.max(axis=0).toarray()).sum()
    )
    if constant_count:
        raise ValueError("Unexpected constant TRAIN feature")
    return dict(
        status="PASS",
        constant_columns=constant_count,
        shape=list(matrix.shape),
        dtype=matrix.dtype.str,
        nnz=int(matrix.nnz),
        NaN=0,
        positive_Inf=0,
        negative_Inf=0,
        duplicate_identities=0,
        duplicate_columns=0,
        zero_only_columns=int((nonzero == 0).sum()),
        unexpected_constants="NONE_NONZERO; every feature varies or has sparse zeros",
        sparse_index_validity="PASS",
    )


def matrix_objects(matrix):
    # R2 canonical sparse row serialization plus explicit CSR components.
    rows = [
        row_bytes(
            matrix.data[matrix.indptr[i] : matrix.indptr[i + 1]].tolist(),
            matrix.shape[1],
            matrix.indices[matrix.indptr[i] : matrix.indptr[i + 1]].tolist(),
        )
        for i in range(matrix.shape[0])
    ]
    canonical_matrix = (
        b"E1R4_MATRIX_V1\0"
        + struct.pack("<QQ", *matrix.shape)
        + b"".join(struct.pack("<Q", len(x)) + x for x in rows)
    )
    return {
        "matrix.bin": canonical_matrix,
        "csr_data.f64": matrix.data.astype("<f8").tobytes(),
        "csr_indices.u64": matrix.indices.astype("<u8").tobytes(),
        "csr_indptr.u64": matrix.indptr.astype("<u8").tobytes(),
        "csr_shape.json": encode(
            dict(shape=list(matrix.shape), dtype="<f8", index_dtype="<u8")
        ),
    }


def verify_persistence(base):
    base = Path(base)
    manifest = base / "MANIFEST.sha256"
    if not manifest.is_file():
        raise ValueError("No manifest: STOP")
    required = {
        "matrix.bin",
        "row_registry.jsonl",
        "column_registry.jsonl",
        "transform_state.json",
        "schema.json",
        "digests.json",
        "provenance.json",
        "raw_message_registry.jsonl",
        "vocabulary.json",
        "idf.json",
        "token_column_registry.jsonl",
        "creation_runtime.json",
        "csr_data.f64",
        "csr_indices.u64",
        "csr_indptr.u64",
        "csr_shape.json",
    }
    entries = {}
    for line in manifest.read_text().splitlines():
        h, n = line.split("  ", 1)
        if Path(n).name != n or n in entries:
            raise ValueError("Invalid manifest")
        entries[n] = h
    if not required <= entries.keys() or set(entries) != {
        p.name for p in base.iterdir() if p.name != "MANIFEST.sha256"
    }:
        raise ValueError("Persistence incomplete: STOP")
    for n, h in entries.items():
        p = base / n
        if p.is_symlink() or not p.is_file() or sha(p.read_bytes()) != h:
            raise ValueError("Persistence integrity: STOP")
    rows = [
        json.loads(x)
        for x in (base / "row_registry.jsonl").read_text().splitlines()
        if x.strip()
    ]
    columns = [
        json.loads(x)
        for x in (base / "column_registry.jsonl").read_text().splitlines()
        if x.strip()
    ]
    schema = json.loads((base / "schema.json").read_text())
    if schema["state"] != "RECONSTRUCTED_REPRESENTATION" or schema["shape"] != [
        len(rows),
        len(columns),
    ]:
        raise ValueError("Persisted representation schema mismatch")
    if len({x["train_row_id"] for x in rows}) != len(rows) or any(
        x["partition"] != "TRAIN" or x["row_index"] != i for i, x in enumerate(rows)
    ):
        raise ValueError("Persisted TRAIN row registry mismatch")
    if [x["column_index"] for x in columns] != list(range(len(columns))) or [
        x["feature_identity"] for x in columns
    ] != schema["feature_order"]:
        raise ValueError("Persisted feature order mismatch")
    d = json.loads((base / "digests.json").read_text())
    for key, name in {
        "matrix_digest": "matrix.bin",
        "transform_digest": "transform_state.json",
        "row_order_digest": "row_registry.jsonl",
        "column_order_digest": "column_registry.jsonl",
        "schema_digest": "schema.json",
    }.items():
        if d[key] != entries[name]:
            raise ValueError("Persisted cross-artifact digest mismatch")
    identity_fields = {
        k: d[k]
        for k in [
            "source_digest",
            "partition",
            "project",
            "modality",
            "transform_digest",
            "row_order_digest",
            "column_order_digest",
            "matrix_digest",
        ]
    }
    if digest(identity_fields) != d["representation_id"]:
        raise ValueError("Representation identity mismatch")
    provenance = json.loads((base / "provenance.json").read_text())
    if (
        provenance["state"] != "RECONSTRUCTED_REPRESENTATION"
        or provenance["predictor_state"] != "RECONSTRUCTED"
        or provenance["representation_id"] != d["representation_id"]
    ):
        raise ValueError("Original/reconstructed provenance conflation")
    return "ELIGIBLE_FOR_DOWNSTREAM_REVIEW_NOT_XAI_AUTHORIZATION"


def jsonl(rows):
    return b"".join(canonical(row) + b"\n" for row in rows)


def snapshot(flight):
    hashes = {p: sha((ROOT / p).read_bytes()) for p in flight["parent_hashes"]}
    for name, expected in flight.get("inherited_payload_stats", {}).items():
        st = (ROOT / name).stat()
        if [st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns] != expected:
            raise ValueError("Inherited payload filesystem identity changed")
    if hashes != flight["parent_hashes"]:
        raise ValueError("Inherited bytes changed")
    index = r3.b.git("ls-files", "-s", "audits", "data", "src", "tests")
    if (
        index.strip() != flight["tracked_index"].strip()
        or r3.b.git("diff", "--name-only")
        or r3.b.git("diff", "--cached", "--name-only")
    ):
        raise ValueError("Tracked historical integrity changed")
    return dict(
        metadata_sha256=hashes,
        tracked_index_sha256=sha(index.strip().encode()),
        scope="Metadata bytes plus tracked Git identities and clean diff; sealed scientific payloads not rehashed",
        scientific_payload_rehash=False,
        inherited_payload_stat_entries=len(flight.get("inherited_payload_stats", {})),
    )


def runtime():
    from importlib.metadata import version

    lock = json.loads((ROOT / SMOKE / "isolated_runtime_lock.json").read_text())
    needed = {"numpy", "scipy", "scikit-learn"}
    expected = {
        x["name"]: x["version"]
        for x in lock["inventory"]["packages"]
        if x["name"] in needed
    }
    actual = {name: version(name) for name in needed}
    if actual != expected or platform.python_version() != lock["inventory"]["python"]:
        raise ValueError("Frozen runtime differs")
    if any(os.environ.get(k) != "1" for k in THREADS):
        raise ValueError("Threads must be frozen to one")
    return dict(
        python=platform.python_version(),
        packages=actual,
        platform=platform.platform(),
        architecture=platform.machine(),
        threads={k: os.environ[k] for k in THREADS},
        seed=20260901,
        lock_sha256=sha((ROOT / SMOKE / "isolated_runtime_lock.json").read_bytes()),
        model_deserialization=False,
        new_vectorizer_fit=False,
    )


def execute(flight):
    r3.branch_gate(r3.b.git("rev-parse", "--abbrev-ref", "HEAD"))
    if flight["head"] != r3.b.git("rev-parse", "HEAD"):
        raise ValueError("HEAD changed")
    before = snapshot(flight)
    inherited, parent, reads = metadata()
    scopes = inherited[f"{r3.b.OUT}/e1_scope_universe.json"]
    summary = json.loads(
        (ROOT / FREEZE / "temporal_partition_summary.json").read_text()
    )
    counts = {
        x["project"]: x["phase_support"]["TRAIN"]["rows"] for x in summary["projects"]
    }
    assert len(counts) == 14 and sum(counts.values()) == 56821
    assert all(
        counts[s["project"]] == s["historical_train_count_metadata"] for s in scopes
    )
    population = json.loads(
        (ROOT / SMOKE / "train_only_population_manifest.json").read_text()
    )
    assert (
        population["available_train_rows"] == counts[PROJECT]
        and digest(population["train_ids_chronological"])
        == population["train_membership_sha256"]
    )
    state_raw = (ROOT / STATE).read_bytes()
    if sha(state_raw) != STATE_PIN:
        raise ValueError("TEXT state digest mismatch")
    state = json.loads(state_raw)
    validate_text(state)
    text_scopes = [
        s for s in scopes if s["project"] == PROJECT and s["modality"] == "TEXT"
    ]
    assert len(text_scopes) == 4
    for scope in text_scopes:
        reference = scope["required_state_references"][0]["objects"][
            "text_representation"
        ]
        if reference["sha256"] != STATE_PIN:
            raise ValueError("Family-specific TEXT state differs")
    frozen_columns = inherited[f"{r3.R1}/text_token_column_alignment.jsonl"]
    for item in frozen_columns:
        if item["project"] == PROJECT:
            if item["feature_order_sha256"] != digest(state["feature_order"]) or item[
                "vocabulary_sha256"
            ] != digest(state["vocabulary"]):
                raise ValueError("TEXT schema compatibility fails")
    environment = runtime()
    out = ROOT / OUT
    if out.resolve() != out:
        raise PermissionError("Symlink output")
    out.mkdir(parents=True, exist_ok=False)

    def save(name, value):
        return atomic_file(
            out, name, value if isinstance(value, bytes) else encode(value)
        )

    save("preflight.json", flight)
    save("parent_integrity_before.json", before)
    save("runtime.json", environment)
    proofs = []
    for rec in population["bounded_prefix_reads"]:
        if rec["path"].endswith(
            ("temporal_partition_manifest.jsonl.gz", "text_dataset.jsonl.gz")
        ):
            proof = {
                **rec,
                "project": PROJECT,
                "partition": "TRAIN",
                "source_class": "AUTHORITATIVE_FROZEN_SOURCE_WITH_LIMITATION",
                "membership_verified": True,
                "producer_order_verified": True,
                "boundary_verified": True,
                "limitation": "Digest and route cover only frozen TRAIN prefix; no full mixed-container read/hash. Valid for ActiveMQ only.",
            }
            source_gate(proof)
            proofs.append(proof)
    save(
        "source_admission_before_payload.json",
        dict(
            proofs=proofs,
            authorization="User R4 TRAIN reconstruction authorization",
            not_scan_filter=True,
            parent_change="R3 no operational route admitted; R4 independently binds preexisting S56.1 prefix evidence to full TRAIN contract. Historical failure evidence unchanged.",
        ),
    )
    prefix = {}
    for proof in proofs:
        raw = read_source(proof)
        name = "partition" if "partition_manifest" in proof["path"] else "text"
        save(f"sources/{name}_train_prefix.jsonl", raw)
        prefix[name] = [json.loads(line) for line in raw.splitlines()]
    expected = {**proofs[0], "ids": population["train_ids_chronological"]}
    rows = identities(prefix["partition"], expected)
    ids = [x["train_row_id"] for x in rows]
    messages = []
    raw_registry = []
    for i, (identity, text) in enumerate(zip(rows, prefix["text"], strict=True)):
        if (
            set(text)
            != {
                "row_identifier",
                "raw_commit_message",
                "raw_commit_message_bytes_base64",
                "raw_commit_message_sha256",
            }
            or text["row_identifier"] != identity["train_row_id"]
        ):
            raise ValueError("TEXT schema/identity mismatch")
        raw = base64.b64decode(text["raw_commit_message_bytes_base64"], validate=True)
        if (
            sha(raw) != text["raw_commit_message_sha256"]
            or raw.decode("utf-8", errors="replace") != text["raw_commit_message"]
        ):
            raise ValueError("Raw-message byte provenance mismatch")
        messages.append(text["raw_commit_message"])
        raw_registry.append(
            dict(
                train_row_id=identity["train_row_id"],
                commit_identity=identity["commit_identity"],
                source_row=i,
                raw_message_sha256=sha(raw),
                source="sources/text_train_prefix.jsonl",
            )
        )
    if len(messages) != counts[PROJECT]:
        raise ValueError("Full TRAIN required")
    save("train_row_identity_registry.jsonl", jsonl(rows))
    columns = [
        dict(
            column_index=i,
            feature_identity=n,
            semantic="Frozen TF-IDF unigram",
            modality="TEXT",
        )
        for i, n in enumerate(state["feature_order"])
    ]
    ordered_rows = [
        dict(
            row_index=i,
            canonical_identity_key=x["canonical_identity_key"],
            train_row_id=x["train_row_id"],
            partition="TRAIN",
        )
        for i, x in enumerate(rows)
    ]
    base = out / "representations/apache_activemq/TEXT"
    base.mkdir(parents=True)
    payloads = {
        "row_registry.jsonl": jsonl(ordered_rows),
        "column_registry.jsonl": jsonl(columns),
        "transform_state.json": state_raw,
        "schema.json": encode(
            dict(
                state="RECONSTRUCTED_REPRESENTATION",
                format="CSR",
                shape=[len(rows), len(columns)],
                dtype="<f8",
                feature_order=state["feature_order"],
                missing="No new imputation",
            )
        ),
        "raw_message_registry.jsonl": jsonl(raw_registry),
        "vocabulary.json": encode(state["vocabulary"]),
        "idf.json": encode(state["idf"]),
        "token_column_registry.jsonl": jsonl(columns),
        "creation_runtime.json": encode(environment),
    }
    for name, raw in payloads.items():
        atomic_file(base, name, raw)
    save(
        "train_storage_plan.json",
        dict(
            rows=len(rows),
            columns=len(columns),
            dense_upper_bound_bytes=len(rows) * len(columns) * 8,
            storage="CSR and R2 canonical row stream; single representation shared by four families",
            file_cap_bytes=25_000_000,
            source_prefixes_persisted=True,
            frozen_before_matrix_construction=True,
        ),
    )
    matrix = transform_text(messages, state)
    # Persist immediately, before any readiness claim or downstream analysis.
    blobs = matrix_objects(matrix)
    for name, raw in blobs.items():
        atomic_file(base, name, raw)
    check = integrity(matrix, ids, state["feature_order"])
    source_digest = next(
        p["prefix_sha256"] for p in proofs if "text_dataset" in p["path"]
    )
    digests = dict(
        source_digest=source_digest,
        partition="TRAIN",
        project=PROJECT,
        modality="TEXT",
        transform_digest=STATE_PIN,
        row_order_digest=sha(payloads["row_registry.jsonl"]),
        column_order_digest=sha(payloads["column_registry.jsonl"]),
        matrix_digest=sha(blobs["matrix.bin"]),
    )
    representation_id = digest(digests)
    atomic_file(
        base,
        "digests.json",
        encode(
            {
                **digests,
                "schema_digest": sha(payloads["schema.json"]),
                "representation_id": representation_id,
                "canonical_id_construction": "SHA256 sorted compact ASCII JSON object of source_digest,partition,project,modality,transform_digest,row_order_digest,column_order_digest,matrix_digest",
            }
        ),
    )
    atomic_file(
        base,
        "provenance.json",
        encode(
            dict(
                state="RECONSTRUCTED_REPRESENTATION",
                predictor_state="RECONSTRUCTED",
                representation_id=representation_id,
                source=proofs,
                canonical_identity="Frozen partition order_key full commit SHA joined by exact row_identifier",
                historical_byte_identity_claim=False,
                model_queries=0,
                limitation="Prospective restoration of standalone frozen vectorizer state; no original historical matrix byte claim",
                e1_scope_ids=[s["scope_id"] for s in text_scopes],
            )
        ),
    )
    manifest = b"".join(
        f"{sha(p.read_bytes())}  {p.name}\n".encode() for p in sorted(base.iterdir())
    )
    atomic_file(base, "MANIFEST.sha256", manifest)
    verify_persistence(base)
    # Independent replay from persisted source/state, without any model object.
    replay_messages = [
        json.loads(line)["raw_commit_message"]
        for line in (out / "sources/text_train_prefix.jsonl").read_bytes().splitlines()
    ]
    replay_state = json.loads((base / "transform_state.json").read_bytes())
    replay = transform_text(replay_messages, replay_state)
    integrity(replay, ids, replay_state["feature_order"])
    again = matrix_objects(replay)
    repeat = all(again[k] == v for k, v in blobs.items())
    if not repeat:
        raise ValueError("Deterministic replay failed")
    # Second construction is verification-only; persisted identity is deduplicated.
    return finish(
        flight,
        before,
        inherited,
        parent,
        counts,
        scopes,
        proofs,
        rows,
        columns,
        ordered_rows,
        check,
        representation_id,
        digests,
        reads,
    )


def finish(
    flight,
    before,
    inherited,
    parent,
    counts,
    scopes,
    proofs,
    rows,
    columns,
    ordered_rows,
    check,
    representation_id,
    digests,
    reads,
):
    out = ROOT / OUT
    files = {}
    n = len(rows)
    width = len(columns)

    def good(project, modality):
        return project == PROJECT and modality == "TEXT"

    records = []
    for project in sorted(counts):
        for modality in ["CODE", "PROCESS", "TEXT"]:
            success = good(project, modality)
            reason = (
                None
                if success
                else (
                    "STANDALONE_NUMERIC_TRANSFORM_STATE_UNAVAILABLE_WITHOUT_PREDICTOR_DESERIALIZATION"
                    if project == PROJECT
                    else "NO_PREVERIFIED_TRAIN_ONLY_RANDOM_ACCESS_ROUTE"
                )
            )
            if modality == "PROCESS":
                reason = (
                    reason + "; ANCESTOR_ONLY_FEATURE_PROVENANCE_REQUIRES_VERIFICATION"
                )
            records.append(
                dict(
                    project=project,
                    modality=modality,
                    expected_train_rows=counts[project],
                    persisted_rows=n if success else 0,
                    persisted_columns=width if success else 0,
                    representation_id=representation_id if success else None,
                    state="RECONSTRUCTED_REPRESENTATION" if success else None,
                    status=(
                        f"{modality}_TRAIN_RECONSTRUCTED_WITH_LIMITATION"
                        if success
                        else f"{modality}_TRAIN_RECONSTRUCTION_BLOCKED"
                    ),
                    reason=reason,
                    q1_status="Q1_TRAIN_REPRESENTATION_ELIGIBLE_WITH_LIMITATION"
                    if success
                    else "Q1_TRAIN_REPRESENTATION_BLOCKED",
                )
            )
    coverage = dict(
        expected_project_modalities=42,
        reconstructed_exact=0,
        reconstructed_limited=1,
        blocked=41,
        failed=0,
        expected_e1_dependencies=168,
        compatible_e1_dependencies=4,
        blocked_e1_dependencies=164,
        unique_TRAIN_rows=56821,
        persisted_unique_TRAIN_rows=n,
        by_project={
            p: dict(
                expected=3,
                reconstructed_limited=int(p == PROJECT),
                blocked=2 if p == PROJECT else 3,
            )
            for p in counts
        },
        by_modality={
            m: dict(
                expected=14,
                reconstructed_limited=int(m == "TEXT"),
                blocked=13 if m == "TEXT" else 14,
                persisted_columns=width if m == "TEXT" else 0,
            )
            for m in ["CODE", "PROCESS", "TEXT"]
        },
        by_algorithm={
            a: dict(expected=42, compatible=1, blocked=41)
            for a in sorted({s["algorithm_family"] for s in scopes})
        },
    )
    files["protocol_summary.json"] = dict(
        verdict=PARTIAL,
        phase="TRAIN_ONLY_RECONSTRUCTION_AND_VERIFICATION",
        historical_exact_recovery="CLOSED_AS_INFEASIBLE_UNDER_AVAILABLE_EVIDENCE",
        predictive_evidence="CLOSED_IMMUTABLE",
        expected_train_rows=56821,
        projects=14,
        expected_project_modalities=42,
        persisted_representations=1,
        persisted_unique_train_rows=n,
        compatible_e1_scopes=4,
        limitations=[
            "Only first-project source prefix safely routable",
            "Numeric standalone transform values unavailable; no predictor deserialization",
            "PROCESS semantics require further evidence",
            "No original matrix byte-equivalence claim",
            "No T1 population or XAI authorization",
        ],
    )
    files["parent_r3_verification.json"] = dict(
        verified=True,
        manifest_sha256=R3_PIN,
        verdict=parent["protocol_summary.json"]["verdict"],
        authorization="R4 user instruction authorizes TRAIN only",
        namespace_override="R4 explicitly prescribes q1-e1-prospective-train-representations/1.0.0; replaces conceptual R3 destination for this execution only",
        historical_failure_packages_unchanged=True,
    )
    files["train_universe_registry.jsonl"] = [
        dict(
            project=p,
            total_frozen_train_identities=count,
            authority=f"{FREEZE}/temporal_partition_summary.json",
            count_basis="Original frozen phase_support.TRAIN.rows; not 80-row derivative",
            admitted_source_rows=n if p == PROJECT else 0,
            availability={m: good(p, m) for m in ["CODE", "PROCESS", "TEXT"]},
            algorithm_dependencies=4,
        )
        for p, count in sorted(counts.items())
    ]
    files["train_source_admission_ledger.jsonl"] = [
        dict(
            path=next(x["path"] for x in proofs if "text_dataset" in x["path"])
            if good(rec["project"], rec["modality"])
            else None,
            project=rec["project"],
            partition="TRAIN",
            modality=rec["modality"],
            origin_sprint="48 freeze;56.1 prefix attestation;R4 fresh prefix verification"
            if good(rec["project"], rec["modality"])
            else "R1/R2 inventory",
            source_class="AUTHORITATIVE_FROZEN_SOURCE_WITH_LIMITATION"
            if good(rec["project"], rec["modality"])
            else "UNKNOWN_SOURCE",
            admitted=good(rec["project"], rec["modality"]),
            source_digest=digests["source_digest"]
            if good(rec["project"], rec["modality"])
            else None,
            digest_unit="Decompressed exact frozen TRAIN prefix only",
            row_count=n if good(rec["project"], rec["modality"]) else 0,
            identity_fields=["project", "order_key.commit_sha", "row_identifier"],
            scientific_semantics="Frozen modality contract",
            reason="Exact bounded prefix hash, ordered identity membership and standalone TEXT state verified"
            if good(rec["project"], rec["modality"])
            else rec["reason"],
            limitation="No access beyond ActiveMQ prefix; partial historical 80-row derivative not used",
        )
        for rec in records
    ]
    for m in ["CODE", "PROCESS", "TEXT"]:
        files[f"{m.lower()}_train_reconstruction_ledger.jsonl"] = [
            rec for rec in records if rec["modality"] == m
        ]
    files["train_transform_state_registry.jsonl"] = [
        dict(
            project=PROJECT,
            modality="TEXT",
            transform_type="FROZEN_TFIDF_STATE_RESTORATION_NO_FIT",
            state_digest=STATE_PIN,
            origin=STATE,
            status="RECONSTRUCTED",
            runtime="runtime.json",
            feature_order_digest=digests["column_order_digest"],
            path="representations/apache_activemq/TEXT/transform_state.json",
        )
    ]
    files["train_representation_row_registry.jsonl"] = [
        dict(representation_id=representation_id, **r) for r in ordered_rows
    ]
    files["train_representation_column_registry.jsonl"] = [
        dict(representation_id=representation_id, **c) for c in columns
    ]
    files["train_serialization_contract.json"] = dict(
        inherited=inherited[
            f"{r3.R2}/canonical_representation_serialization_contract.json"
        ],
        matrix_envelope="E1R4_MATRIX_V1 NUL, little-endian uint64 rows/columns, each length-prefixed E1R2_ROW_V1 canonical sparse row",
        sparse_components="Explicit data<float64LE>, indices<uint64LE>, indptr<uint64LE>, shape/dtype JSON",
        deterministic=True,
        timestamps_in_serialization=False,
        representation_id="SHA256 compact sorted ASCII JSON of source_digest,partition,project,modality,transform_digest,row_order_digest,column_order_digest,matrix_digest",
        original_matrix_byte_claim=False,
    )
    files["train_representation_digest_registry.jsonl"] = [
        dict(representation_id=representation_id, **digests)
    ]
    files["train_reconstruction_repeatability.jsonl"] = [
        dict(
            project=PROJECT,
            modality="TEXT",
            representation_id=representation_id,
            status="REPEATABILITY_EXACT",
            constructions=2,
            independent_vectorizer_restorations=2,
            source="Persisted verified full TRAIN raw-message prefix; reread on replay",
            compared=[
                "row identities",
                "column identities",
                "shape",
                "dtype",
                "matrix bytes",
                "transform digest",
                "source digest",
            ],
            canonical_and_CSR_components_identical=True,
            deduplicated=True,
            new_fit=False,
        )
    ]
    files["train_feature_value_integrity.jsonl"] = [
        dict(
            project=PROJECT,
            modality="TEXT",
            representation_id=representation_id,
            **check,
        )
    ]
    files["train_partition_safety_audit.json"] = dict(
        TRAIN_ONLY="PASS",
        rows_verified=n,
        source="Frozen partition TRAIN prefix with matching preexisting membership digest",
        full_commit_identity=True,
        T1_rows=0,
        T2_rows=0,
        other_partitions_not_opened=True,
        overlap_proof="Exact equality to frozen TRAIN membership; no T1/T2 payload traversal or empirical reopening",
        prefix_limits=proofs,
    )
    linkage = []
    for scope in scopes:
        success = good(scope["project"], scope["modality"])
        linkage.append(
            dict(
                scope_id=scope["scope_id"],
                project=scope["project"],
                modality=scope["modality"],
                algorithm_family=scope["algorithm_family"],
                model_identity_sha256=scope["model_identity_sha256"],
                model_state="RECONSTRUCTED",
                representation_id=representation_id if success else None,
                status="COMPATIBLE_BY_METADATA_WITH_LIMITATION"
                if success
                else "UNPROVEN",
                expected_feature_count=width if success else None,
                feature_order_digest=digests["column_order_digest"]
                if success
                else None,
                preprocessing_state_sha256=STATE_PIN if success else None,
                model_queries=0,
                limitation="Frozen metadata compatibility and prior equivalence; not a new prediction-equivalence run",
            )
        )
    files["train_representation_model_compatibility.jsonl"] = linkage
    files["train_representation_to_e1_scope_linkage.jsonl"] = linkage
    files["train_background_readiness.jsonl"] = [
        dict(
            scope_id=x["scope_id"],
            representation_id=x["representation_id"],
            status="BACKGROUND_SOURCE_READY_WITH_LIMITATION"
            if x["representation_id"]
            else "BACKGROUND_SOURCE_BLOCKED",
            final_subset_selected=False,
            XAI_authorized=False,
        )
        for x in linkage
    ]
    files["train_correlation_readiness.jsonl"] = [
        dict(
            project=x["project"],
            modality=x["modality"],
            status="BLOCKED_NO_PERSISTED_NUMERIC_MATRIX",
            correlation_computed=False,
            prospective_abs_spearman_threshold=0.70,
        )
        for x in records
        if x["modality"] != "TEXT"
    ]
    files["train_storage_plan.json"] = dict(
        unit="project × modality; identical TEXT state shared by four families",
        row_estimate=n,
        column_estimate=width,
        dense_float64_upper_bound_bytes=n * width * 8,
        format="CSR plus R2 canonical row stream",
        file_cap_bytes=25000000,
        large_artifact_strategy="Deterministic sparse components; no extra matrix per algorithm",
        plan_basis="Frozen row count and frozen vocabulary known before reconstruction",
        source_prefixes_persisted=True,
    )
    sizes = {
        str(p.relative_to(out)): p.stat().st_size for p in out.rglob("*") if p.is_file()
    }
    if max(sizes.values()) >= 25000000:
        raise ValueError("Storage cap exceeded")
    files["train_storage_audit.json"] = dict(
        files=sizes,
        bytes_at_representation_verification=sum(sizes.values()),
        largest_file_bytes=max(sizes.values()),
        representation_directories=1,
        algorithm_duplicate_matrices=0,
        canonical_plus_CSR="Two documented equivalent serialization views, not algorithm replicas",
    )
    files["train_persistence_verification.jsonl"] = [
        dict(
            project=PROJECT,
            modality="TEXT",
            representation_id=representation_id,
            status=verify_persistence(out / "representations/apache_activemq/TEXT"),
            required_objects_verified=True,
            manifest="representations/apache_activemq/TEXT/MANIFEST.sha256",
            downstream_scientific_use=False,
        )
    ]
    files["train_replication_readiness.json"] = dict(
        status="REPLICATION_READY_WITH_LIMITATION",
        eligible_subset="ActiveMQ TEXT full TRAIN only",
        source_snapshot=proofs,
        persisted_source_prefixes=[
            "sources/partition_train_prefix.jsonl",
            "sources/text_train_prefix.jsonl",
        ],
        builder=SOURCE,
        environment="runtime.json and parent frozen runtime lock",
        transform_state=STATE,
        requires_frozen_parent_metadata=True,
        remaining_41_project_modalities="REPLICATION_NOT_READY",
        source_redistribution="No license grant inferred; retain benchmark access conditions",
    )
    files["reviewer_train_persistence_evidence.md"] = (
        "# R4 reviewer persistence evidence\n\nActiveMQ TEXT: 3,675 complete frozen TRAIN rows were reconstructed using the standalone frozen TF-IDF vocabulary, IDF and normalization state, without fitting a new vectorizer or loading a predictor. The 2,557-column sparse representation was immediately persisted in the separate R4 namespace with source prefixes, full commit identities from frozen partition metadata, row/column order, transform state, runtime and SHA-256 manifests. Two independent state restorations produced identical canonical and CSR bytes. Persistence verification preceded readiness.\n\nThis is one shared representation linked by metadata to four algorithm families. CODE/PROCESS and the other 13 projects remain blocked. No T1 feature or label access, T2 payload access, model queries, SHAP, metrics or figures occurred. No claim of original historical matrix-byte recovery is made. The correction is demonstrated for this subset only.\n"
    )
    files["q1_train_representation_sufficiency.json"] = dict(
        dimensions=[
            "source admitted",
            "complete TRAIN identity",
            "project known",
            "semantics valid",
            "frozen transformation",
            "transform persisted",
            "row order persisted",
            "column order persisted",
            "matrix persisted",
            "digests verified",
            "repeatability",
            "partition safety",
            "no leakage",
            "model metadata compatibility",
            "bounded limitation",
        ],
        project_modalities=records,
        eligible_exact=0,
        eligible_with_limitation=1,
        blocked=41,
    )
    files["coverage_summary.json"] = coverage
    files["remaining_blockers.json"] = dict(
        items=[
            "13 projects: no preverified TRAIN-only random-access route; mixed stream scan remains denied",
            "ActiveMQ CODE/PROCESS: standalone fitted numeric parameter values absent; cannot load predictive pipelines or refit",
            "PROCESS prediction-time ancestor semantics need source evidence",
            "T1 separate authorization and source admission required; no XAI authorization",
        ],
        historical_exact_recovery_reopened=False,
    )
    counters = dict.fromkeys(
        (
            *r3.b.ZERO,
            "TRAIN_SOURCE_VALUE_READ_COUNT",
            "TRAIN_REPRESENTATION_RECONSTRUCTION_COUNT",
            "TRAIN_REPRESENTATION_PERSIST_COUNT",
            "T2_ROW_READ_COUNT",
            "HYPERPARAMETER_TUNING_COUNT",
        ),
        0,
    )
    counters.update(
        TRAIN_SOURCE_VALUE_READ_COUNT=2 * n,
        TRAIN_REPRESENTATION_RECONSTRUCTION_COUNT=2,
        TRAIN_REPRESENTATION_PERSIST_COUNT=1,
        TRAIN_IDENTITY_ROWS_VERIFIED=n,
        T1_METADATA_ACCESS_COUNT=len(reads),
        T1_IDENTITY_ACCESS_COUNT=0,
        historical_T1_predictive_access_count=1,
        historical_T1_predictive_scoring_count=1,
        T2_STATE="DENY_SEALED_REVIEWER_RESERVE",
        count_units={
            "TRAIN_SOURCE_VALUE_READ_COUNT": "row visits: one full TEXT prefix plus one persisted-prefix replay",
            "TRAIN_REPRESENTATION_RECONSTRUCTION_COUNT": "two independent transforms",
            "TRAIN_REPRESENTATION_PERSIST_COUNT": "one unique persisted representation; replay bytes identical and deduplicated",
            "T1_METADATA_ACCESS_COUNT": "conservative count of inherited governance metadata files, not new T1 identities or payload",
        },
    )
    files["governance_counters.json"] = counters
    files["future_t1_policy.json"] = dict(
        T1_REPRESENTATION_PHASE="READY_FOR_SEPARATE_HUMAN_AUTHORIZATION",
        authorized=False,
        scope_limit="Only successful TRAIN dependency may be considered; others blocked",
        T1_labels="DENY",
        T2="DENY_SEALED_REVIEWER_RESERVE",
        R5_started=False,
    )
    files["recommended_next_action.json"] = dict(
        sprint="56.3B-R5 — TRAIN Verification Closure & T1 Scientific Feature Access Authorization",
        action="Human review of ActiveMQ TEXT subset and separate identity-bounded T1 authorization; obtain safe sources and standalone numeric states before expanding TRAIN",
        automatic_start=False,
    )
    after = snapshot(flight)
    files["parent_integrity_after.json"] = after
    files["parent_integrity_diff.json"] = dict(
        status="PASS",
        changed=[],
        before_equals_after=before == after,
        scope=before["scope"],
    )
    titles = [
        "Objective",
        "Branch/HEAD",
        "Parent R3 state",
        "TRAIN scientific universe",
        "Source admission",
        "Identity registry",
        "CODE reconstruction",
        "PROCESS reconstruction",
        "TEXT reconstruction",
        "Transformation state",
        "Row-order persistence",
        "Column-order persistence",
        "Serialization",
        "Representation digests",
        "Repeatability",
        "Feature integrity",
        "Partition safety",
        "Model compatibility metadata",
        "Background readiness",
        "Correlation readiness",
        "Coverage",
        "Storage",
        "Persistence verification",
        "Q1 sufficiency",
        "T1 next-phase readiness",
        "Recommendation",
    ]
    paragraphs = [
        "Controlled TRAIN reconstruction and persistence only.",
        flight["branch"] + " / " + flight["head"],
        "R3 PASS_WITH_LIMITATIONS verified; historical failures remain intact.",
        "56,821 frozen TRAIN identities, 14 projects, 42 project/modalities, 168 dependencies. Counts from original partition summary.",
        "Exact preattested ActiveMQ gzip prefixes only; no tail scan. All other project routes blocked.",
        "3,675 unique frozen TRAIN identities and full commit SHA from partition order_key. No diagnostic-row promotion.",
        "14 projects blocked; no standalone numeric fitted values loaded.",
        "14 projects blocked; numeric-state and ancestor-semantic prerequisites remain.",
        "ActiveMQ TEXT complete: 3,675 × 2,557, shared by four families. Other 13 projects blocked.",
        "Standalone TF-IDF state restored twice without fit; vocabulary/IDF/order persisted.",
        "One-to-one row index/full-commit registry persisted.",
        "All 2,557 token columns ordered and persisted.",
        "R2 canonical row encoding and deterministic CSR components; no timestamps.",
        "Matrix, source, schema, state, row/column digests and immutable representation identity persisted.",
        "Two independent transforms from frozen state and source; byte-exact canonical/CSR equality.",
        "Finite values, valid canonical sparse structure, unique identities/columns, no zero-only vocabulary columns.",
        "TRAIN_ONLY PASS from exact frozen membership; no T1/T2 decoding.",
        "Four TEXT scopes compatible by frozen state/order metadata with limitation; no model queries.",
        "Four dependencies ready with limitation; no final background subset selected.",
        "No numeric matrices; no correlation computation.",
        "1/42 project-modalities reconstructed with limitation; 41 blocked. 4/168 dependencies ready.",
        "Sparse storage shared across families; file cap enforced. Source prefixes persisted.",
        "Creation-time persistence and manifest verification completed before readiness.",
        "Eligible with limitation for ActiveMQ TEXT only; no original matrix-byte claim.",
        "READY_FOR_SEPARATE_HUMAN_AUTHORIZATION, not authorized; R5 not started.",
        "Review subset; separately authorize next phase and resolve remaining source/transform blockers.",
    ]
    files["SPRINT56_3B_R4_TRAIN_RECONSTRUCTION_PERSISTENCE_REPORT.md"] = (
        "# Sprint 56.3B-R4\n\n"
        + PARTIAL
        + "\n\n"
        + "\n\n".join(
            f"## {chr(65 + i)}. {title}\n\n{paragraph}"
            for i, (title, paragraph) in enumerate(zip(titles, paragraphs, strict=True))
        )
        + "\n"
    )
    files.pop("train_storage_plan.json", None)
    for name, value in files.items():
        atomic_file(
            out,
            name,
            jsonl(value)
            if name.endswith(".jsonl")
            else value.encode()
            if isinstance(value, str)
            else encode(value),
        )
    print(json.dumps(files["protocol_summary.json"], sort_keys=True))


def finalize(validation):
    r3.branch_gate(r3.b.git("rev-parse", "--abbrev-ref", "HEAD"))
    out = ROOT / OUT
    snapshot(json.loads((out / "preflight.json").read_text()))
    verify_persistence(out / "representations/apache_activemq/TEXT")
    atomic_file(out, "validation_results.json", validation.read_bytes())
    atomic_file(
        out,
        "implementation_provenance.json",
        encode({p: sha((ROOT / p).read_bytes()) for p in [SOURCE, TEST]}),
    )
    entries = [p for p in out.rglob("*") if p.is_file()]
    manifest = "".join(
        f"{sha(p.read_bytes())}  {p.relative_to(out).as_posix()}\n"
        for p in sorted(entries)
    )
    atomic_file(out, "MANIFEST.sha256", manifest.encode())
    print(
        "MANIFEST",
        sha((out / "MANIFEST.sha256").read_bytes()),
        "FILES",
        len(entries) + 1,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", type=Path)
    parser.add_argument("--finalize", type=Path)
    args = parser.parse_args()
    if args.finalize:
        finalize(args.finalize)
    elif args.preflight:
        execute(json.loads(args.preflight.read_text()))
    else:
        parser.error("preflight or finalize required")


if __name__ == "__main__":
    main()
