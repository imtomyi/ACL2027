#!/usr/bin/env python3
"""Create deterministic blinded candidate bundles for supplementary judging."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parents[1]
DEFAULT_RUN_DIR = PROJECT_ROOT / "Storage" / "synthetic-results" / "model-qualification" / "20260825_synthetic_qualification"
BENCHMARK_PATH = ROOT / "benchmark" / "synthetic_packets_v1.json"
MODELS = ["gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna", "gpt-5.5", "gpt-5.4"]
SEED = "qc-synthetic-v1-blind-20260825"


def load_records(raw_dir: Path) -> dict[tuple[str, int, str], dict[str, Any]]:
    records: dict[tuple[str, int, str], dict[str, Any]] = {}
    for path in sorted(raw_dir.glob("*.jsonl")):
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                record = json.loads(line)
                key = (record["model_id"], int(record["run_index"]), record["packet_id"])
                if key in records:
                    raise ValueError(f"duplicate run key {key} in {path}:{line_number}")
                records[key] = record
    return records


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    args = parser.parse_args()
    run_dir = args.run_dir.resolve()
    raw_dir = run_dir / "raw"
    blind_dir = run_dir / "blinded"
    blind_dir.mkdir(parents=True, exist_ok=True)

    benchmark = json.loads(BENCHMARK_PATH.read_text(encoding="utf-8"))
    packets = {packet["packet_id"]: packet for packet in benchmark["packets"]}
    records = load_records(raw_dir)
    expected = {
        (model, run_index, packet_id)
        for model in MODELS
        for run_index in (1, 2, 3)
        for packet_id in packets
    }
    if set(records) != expected:
        missing = sorted(expected - set(records))
        extra = sorted(set(records) - expected)
        raise ValueError(f"run set is incomplete; missing={missing}; extra={extra}")

    map_rows: list[dict[str, Any]] = []
    bundle_index: list[dict[str, Any]] = []
    for packet_id, packet in packets.items():
        for run_index in (1, 2, 3):
            ordered_models = sorted(
                MODELS,
                key=lambda model: hashlib.sha256(
                    f"{SEED}|{packet_id}|{run_index}|{model}".encode("utf-8")
                ).hexdigest(),
            )
            candidates = []
            for position, model_id in enumerate(ordered_models, start=1):
                blind_id = f"B{position}"
                candidates.append(
                    {
                        "blind_id": blind_id,
                        "output": records[(model_id, run_index, packet_id)]["output"],
                    }
                )
                map_rows.append(
                    {
                        "packet_id": packet_id,
                        "run_index": run_index,
                        "blind_id": blind_id,
                        "model_id": model_id,
                    }
                )
            bundle = {
                "bundle_version": "1.0",
                "benchmark_id": benchmark["benchmark_id"],
                "packet_id": packet_id,
                "run_index": run_index,
                "packet": packet,
                "candidates": candidates,
            }
            filename = f"{packet_id}_run{run_index}.json"
            (blind_dir / filename).write_text(
                json.dumps(bundle, indent=2, ensure_ascii=False, sort_keys=False) + "\n",
                encoding="utf-8",
            )
            bundle_index.append(
                {
                    "packet_id": packet_id,
                    "run_index": run_index,
                    "bundle_file": filename,
                    "candidate_count": len(candidates),
                }
            )

    private_map = run_dir / "blind_map_private.csv"
    with private_map.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["packet_id", "run_index", "blind_id", "model_id"]
        )
        writer.writeheader()
        writer.writerows(map_rows)
    with (blind_dir / "bundle_index.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["packet_id", "run_index", "bundle_file", "candidate_count"]
        )
        writer.writeheader()
        writer.writerows(bundle_index)
    print(
        json.dumps(
            {
                "bundles": len(bundle_index),
                "map_rows": len(map_rows),
                "private_map": str(private_map),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
