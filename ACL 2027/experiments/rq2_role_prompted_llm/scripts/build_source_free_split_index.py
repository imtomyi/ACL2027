#!/usr/bin/env python3
"""Build the frozen source-free byte index for the bound Dreaddit JSONL file.

The helper reads each record locally only to obtain its split label. It never
prints, copies, or stores record text or any other source-bearing field.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RECORDS = ROOT / "dataset/deidentified/dreaddit/records.jsonl"
OUTPUT = ROOT / "dataset/deidentified/dreaddit/records.split_index.json"
EXPECTED_RECORDS_SHA256 = "86ba43a89d9ef52f5377d35c12d26690b820f24ce11bc6540eeae57605654d3a"
ALLOWED_SPLITS = {"development_train", "in_domain_audit"}


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def main() -> None:
    digest = hashlib.sha256()
    entries: dict[str, list[dict[str, object]]] = {key: [] for key in sorted(ALLOWED_SPLITS)}
    offset = 0
    line_count = 0
    with RECORDS.open("rb") as handle:
        for line_number, raw_line in enumerate(handle, 1):
            line_count = line_number
            digest.update(raw_line)
            if not raw_line.strip():
                offset += len(raw_line)
                continue
            record = json.loads(raw_line)
            if not isinstance(record, dict) or record.get("split") not in ALLOWED_SPLITS:
                raise RuntimeError("unexpected_record_or_split")
            split = record["split"]
            entries[split].append(
                {
                    "line_number": line_number,
                    "byte_offset": offset,
                    "byte_length": len(raw_line),
                    "line_sha256": hashlib.sha256(raw_line).hexdigest(),
                }
            )
            del record
            offset += len(raw_line)
    observed = digest.hexdigest()
    if observed != EXPECTED_RECORDS_SHA256:
        raise RuntimeError("bound_records_hash_mismatch")
    payload = {
        "document_type": "rq2_source_free_jsonl_split_index",
        "index_version": "rq2-source-free-split-index-v1",
        "records_path": "dataset/deidentified/dreaddit/records.jsonl",
        "records_sha256": observed,
        "file_size_bytes": offset,
        "line_count": line_count,
        "splits": entries,
        "contains_source_text": False,
        "stored_fields": ["split", "line_number", "byte_offset", "byte_length", "line_sha256"],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=".records.split_index.", dir=OUTPUT.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(canonical_bytes(payload))
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary_name, 0o600)
        os.replace(temporary_name, OUTPUT)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)
    counts = Counter({split: len(rows) for split, rows in entries.items()})
    print(json.dumps({"status": "source_free_split_index_written", "line_counts": counts,
                      "contains_source_text": False}, sort_keys=True))


if __name__ == "__main__":
    main()
