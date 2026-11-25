"""Permission B only. No production entry point and no real-source access."""

from __future__ import annotations

import base64
import dataclasses
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import zlib

FEATURES = ("la", "ld", "nf", "nd", "ns", "ent")
FIELDS = {"row_identifier", *FEATURES}
MAX_SOURCE = 8 * 1024 * 1024
MAX_REQUEST = 12 * 1024 * 1024
MAX_OUTPUT = 2 * 1024 * 1024


class Rejected(Exception):
    """Only fixed, non-data-bearing error codes may cross the boundary."""


def require(condition, code):
    if not condition:
        raise Rejected(code)


@dataclasses.dataclass(frozen=True)
class Contract:
    expected_sha256: str
    expected_ids: tuple[str, ...]
    local_ids: tuple[str, ...]
    start: int
    stop: int
    max_compressed: int
    max_line: int = 4096
    max_decoded: int = 4 * 1024 * 1024
    # Explicit scalar types, not conversions; no historical typing claim.
    types: tuple[str, ...] = ("int", "int", "int", "int", "int", "float")

    def validate(self):
        require(re.fullmatch(r"[0-9a-f]{64}", self.expected_sha256) is not None, "CONTRACT")
        require(all(type(v) is int for v in (self.start, self.stop, self.max_compressed,
                                             self.max_line, self.max_decoded)), "CONTRACT")
        require(0 <= self.start < self.stop <= 5145, "CONTRACT")
        require(1 <= len(self.expected_ids) <= 245, "CONTRACT")
        require(self.stop - self.start == len(self.expected_ids), "CONTRACT")
        require(len(set(self.expected_ids)) == len(self.expected_ids), "CONTRACT")
        require(all(type(v) is str and re.fullmatch(r"synthetic-row-[0-9]{4}", v)
                    for v in self.expected_ids), "SYNTHETIC_ONLY")
        require(len(set(self.local_ids)) == len(self.local_ids)
                and set(self.local_ids) <= set(self.expected_ids), "CONTRACT")
        require(0 < self.max_compressed <= MAX_SOURCE, "CONTRACT")
        require(0 < self.max_line <= 16384 and 0 < self.max_decoded <= 8 * 1024 * 1024,
                "CONTRACT")
        require(len(self.types) == 6 and all(v in ("int", "float") for v in self.types),
                "CONTRACT")


def _stamp(value):
    return (value.st_dev, value.st_ino, value.st_mode, value.st_size,
            value.st_mtime_ns, value.st_ctime_ns)


def _read_verified_fixture(path, contract):
    """Read only temporary synthetic fixtures, then hand off immutable bytes."""
    path = Path(path).absolute()
    require(path.name == "fixture.code.jsonl.gz"
            and path.parent.name.startswith("e1-code-b-synthetic-"), "SYNTHETIC_ONLY")
    require(path.parent.resolve() == path.parent, "SYNTHETIC_ONLY")
    initial = path.lstat()
    require(stat.S_ISREG(initial.st_mode) and not stat.S_ISLNK(initial.st_mode), "SOURCE")
    require(0 < initial.st_size <= contract.max_compressed, "BYTE_LIMIT")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
        original = _stamp(initial)
        require(_stamp(os.fstat(fd)) == original == _stamp(path.lstat()), "SOURCE_CHANGED")
        chunks, count, h = [], 0, hashlib.sha256()
        while True:
            block = os.read(fd, min(65536, initial.st_size - count + 1))
            if not block:
                break
            count += len(block)
            require(count <= initial.st_size, "SOURCE_CHANGED")
            chunks.append(block)
            h.update(block)
        require(count == initial.st_size, "SOURCE_CHANGED")
        require(_stamp(os.fstat(fd)) == original == _stamp(path.lstat()), "SOURCE_CHANGED")
        require(h.hexdigest() == contract.expected_sha256, "HASH_MISMATCH")
        return b"".join(chunks)
    finally:
        os.close(fd)


def _pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, "DUPLICATE_KEY")
        result[key] = value
    return result


def _constant(_):
    raise Rejected("NONFINITE")


def _decode(payload, contract):
    contract.validate()
    require(len(payload) <= contract.max_compressed, "BYTE_LIMIT")
    require(hashlib.sha256(payload).hexdigest() == contract.expected_sha256, "HASH_MISMATCH")
    decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
    consumed = decoded = line_count = 0
    line, staged = bytearray(), []
    while line_count < contract.stop:
        if decoder.unconsumed_tail:
            compressed = decoder.unconsumed_tail
        else:
            require(consumed < len(payload), "TRUNCATED")
            compressed = payload[consumed:consumed + 1]
            consumed += 1
        byte = decoder.decompress(compressed, max_length=1)
        require(not decoder.eof or byte, "TRUNCATED")
        decoded += len(byte)
        require(decoded <= contract.max_decoded, "MEMORY_LIMIT")
        line.extend(byte)
        require(len(line) <= contract.max_line, "LINE_LIMIT")
        if byte != b"\n":
            continue
        if line_count >= contract.start:
            row = json.loads(line, object_pairs_hook=_pairs, parse_constant=_constant)
            require(type(row) is dict and set(row) == FIELDS, "SCHEMA")
            index = line_count - contract.start
            require(row["row_identifier"] == contract.expected_ids[index], "IDENTITY_ORDER")
            for field, kind in zip(FEATURES, contract.types):
                value = row[field]
                require(type(value) is (int if kind == "int" else float), "TYPE")
                require(type(value) is int or math.isfinite(value), "NONFINITE")
            staged.append(row)
        line.clear()
        line_count += 1
    require(len(staged) == len(contract.expected_ids), "COVERAGE")
    return {"rows": staged, "transport": {"compressed_bytes_consumed": consumed,
            "decoded_bytes": decoded, "lines": line_count}}


def _deny_io(event, args):
    if event == "open" or event.startswith(("socket.", "subprocess.")) or event in {
        "os.mkdir", "os.remove", "os.rename", "os.rmdir", "os.link", "os.symlink",
        "os.chmod", "os.truncate", "os.utime", "os.system", "os.listdir", "os.scandir"
    }:
        raise Rejected("IO_DENIED")


def _worker():
    # All imports are complete. This worker receives no path or file descriptor.
    sys.addaudithook(_deny_io)
    try:
        raw = sys.stdin.buffer.read(MAX_REQUEST + 1)
        require(len(raw) <= MAX_REQUEST, "REQUEST_LIMIT")
        request = json.loads(raw)
        c = Contract(**request["contract"])
        payload = base64.b64decode(request["payload"], validate=True)
        result = _decode(payload, c)
        wire = json.dumps(result, allow_nan=False, separators=(",", ":")).encode()
        require(len(wire) <= MAX_OUTPUT, "OUTPUT_LIMIT")
    except BaseException:
        # Do not serialize original exceptions or partial rows, even on last-row failure.
        sys.stdout.write('{"error":"REJECTED"}')
        return 2
    sys.stdout.buffer.write(wire)
    return 0


def _run_worker(payload, contract):
    request = json.dumps({"contract": dataclasses.asdict(contract),
                          "payload": base64.b64encode(payload).decode("ascii")}).encode()
    require(len(request) <= MAX_REQUEST, "REQUEST_LIMIT")
    run = subprocess.run([sys.executable, "-I", "-B", str(Path(__file__).resolve()), "--worker"],
                         input=request, capture_output=True, timeout=10, close_fds=True,
                         env={"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"})
    require(run.returncode == 0 and not run.stderr and len(run.stdout) <= MAX_OUTPUT,
            "WORKER_REJECTED")
    result = json.loads(run.stdout)
    require("rows" in result, "WORKER_REJECTED")
    return result


def extract_synthetic(path, contract):
    """Return all approved rows, or raise a fixed error; never yield partial rows."""
    try:
        contract.validate()
        payload = _read_verified_fixture(path, contract)
        return _run_worker(payload, contract)
    except BaseException:
        raise Rejected("EXTRACTION_REJECTED") from None


if __name__ == "__main__":
    if sys.argv[1:] == ["--worker"]:
        raise SystemExit(_worker())
    raise SystemExit("SYNTHETIC_WORKER_ONLY")
