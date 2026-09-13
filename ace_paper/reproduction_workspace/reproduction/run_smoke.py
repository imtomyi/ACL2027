#!/usr/bin/env python3
"""Run a small, real-data ACE reproduction with a local Ollama model.

The harness imports the official ACE orchestration, agents, prompts, playbook
operations, and finance data processor from ../upstream. The only behavioral
adapter replaces the hosted API client factory with Ollama's OpenAI-compatible
endpoint.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import platform
import re
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openai import OpenAI


ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT / "upstream"
DATA_DIR = ROOT / "reproduction" / "data"
RESULTS_DIR = ROOT / "results"
DEFAULT_MODEL = "qwen3:8b"
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
UPSTREAM_COMMIT = "82709de050e1db6e6ef2f07bcb0393560b94992a"

SOURCES = {
    "train": UPSTREAM / "eval/finance/data/formula_train_subset_500.jsonl",
    "val": UPSTREAM / "eval/finance/data/formula_val_subset_300.jsonl",
    "test": UPSTREAM / "eval/finance/data/formula_test.jsonl",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL)
    parser.add_argument("--train-samples", type=int, default=2)
    parser.add_argument("--val-samples", type=int, default=2)
    parser.add_argument("--test-samples", type=int, default=2)
    parser.add_argument("--max-tokens", type=int, default=2048)
    parser.add_argument("--max-reflection-rounds", type=int, default=1)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def materialize_subsets(counts: dict[str, int]) -> dict[str, Any]:
    """Create deterministic prefix subsets while retaining full source provenance."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {
        "selection": "first_n_records_in_upstream_order",
        "upstream_commit": UPSTREAM_COMMIT,
        "datasets": {},
    }

    for split, source in SOURCES.items():
        records = read_jsonl(source)
        count = counts[split]
        if count < 1 or count > len(records):
            raise ValueError(f"{split} sample count must be between 1 and {len(records)}")

        subset = records[:count]
        destination = DATA_DIR / f"formula_{split}_n{count}.jsonl"
        with destination.open("w", encoding="utf-8") as stream:
            for record in subset:
                stream.write(json.dumps(record, ensure_ascii=False) + "\n")

        manifest["datasets"][split] = {
            "source": str(source.relative_to(ROOT)),
            "source_sha256": sha256(source),
            "source_records": len(records),
            "selected_indices_zero_based": list(range(count)),
            "subset": str(destination.relative_to(ROOT)),
            "subset_sha256": sha256(destination),
            "subset_records": count,
        }

    write_json(DATA_DIR / "manifest.json", manifest)
    return manifest


def assert_upstream_revision() -> str:
    if not (UPSTREAM / ".git").exists():
        raise RuntimeError("Missing official checkout at ace_paper/upstream")
    revision = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=UPSTREAM, text=True
    ).strip()
    if revision != UPSTREAM_COMMIT:
        raise RuntimeError(f"Expected upstream {UPSTREAM_COMMIT}, found {revision}")
    return revision


def get_ollama_model(ollama_url: str, model: str) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(f"{ollama_url}/api/tags", timeout=5) as response:
            payload = json.load(response)
    except Exception as exc:
        raise RuntimeError(f"Ollama is not reachable at {ollama_url}: {exc}") from exc

    for item in payload.get("models", []):
        if item.get("name") == model or item.get("model") == model:
            return item
    available = ", ".join(sorted(item.get("name", "") for item in payload.get("models", [])))
    raise RuntimeError(f"Ollama model {model!r} is not installed. Available: {available}")


def load_official_components(ollama_url: str):
    sys.path.insert(0, str(UPSTREAM))
    ace_module = importlib.import_module("ace.ace")
    finance_module = importlib.import_module("eval.finance.data_processor")

    def initialize_local_clients(api_provider: str):
        if api_provider != "ollama":
            raise ValueError(f"This harness only supports ollama, got {api_provider!r}")
        client = OpenAI(api_key="ollama", base_url=f"{ollama_url}/v1", timeout=300.0)
        return client, client, client

    # ACE.__init__ resolves this module global at runtime. Upstream files remain clean.
    ace_module.initialize_clients = initialize_local_clients
    return ace_module.ACE, finance_module.DataProcessor


def load_processed_subsets(data_processor, manifest: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    processed = {}
    for split, metadata in manifest["datasets"].items():
        raw = read_jsonl(ROOT / metadata["subset"])
        processed[split] = data_processor.process_task_data(raw)
    return processed


def summarize_run(run_dir: Path, results: dict[str, Any], provenance: dict[str, Any]) -> dict[str, Any]:
    playbook = (run_dir / "final_playbook.txt").read_text(encoding="utf-8")
    bullets = re.findall(
        r"^\[([^\]]+)\]\s+helpful=(\d+)\s+harmful=(\d+)\s+::\s+(.+)$",
        playbook,
        flags=re.MULTILINE,
    )
    operations_path = run_dir / "curator_operations_diff.jsonl"
    operations = []
    if operations_path.exists():
        operations = [json.loads(line) for line in operations_path.read_text(encoding="utf-8").splitlines() if line]

    initial = results["initial_test_results"]
    final = results["final_test_results"]
    best_playbook = (run_dir / "best_playbook.txt").read_text(encoding="utf-8")
    summary = {
        "status": "completed",
        "scope": "mechanism-level reproduction on a deterministic real Formula subset",
        "not_a_claim_of": "full paper table or AppWorld metric reproduction",
        "run_directory": str(run_dir),
        "initial_test_accuracy": initial["accuracy"],
        "final_test_accuracy": final["accuracy"],
        "initial_test_correct": initial["correct"],
        "final_test_correct": final["correct"],
        "test_total": final["total"],
        "final_playbook_bullet_count": len(bullets),
        "final_playbook_bullet_ids": [item[0] for item in bullets],
        "curator_operation_count": len(operations),
        "curator_operation_types": [item.get("operation_type") for item in operations],
        "best_playbook_matches_final_playbook": best_playbook == playbook,
        "provenance": provenance,
    }
    write_json(run_dir / "reproduction_summary.json", summary)
    write_json(RESULTS_DIR / "latest_run.json", summary)
    return summary


def main() -> int:
    args = parse_args()
    revision = assert_upstream_revision()
    model_metadata = get_ollama_model(args.ollama_url, args.model)
    counts = {
        "train": args.train_samples,
        "val": args.val_samples,
        "test": args.test_samples,
    }
    manifest = materialize_subsets(counts)

    provenance = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "official_repository": "https://github.com/ace-agent/ace",
        "official_project_page": "https://ace-agent.github.io/",
        "upstream_commit": revision,
        "model": args.model,
        "ollama_url": args.ollama_url,
        "ollama_model_digest": model_metadata.get("digest"),
        "ollama_model_size_bytes": model_metadata.get("size"),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "dataset_manifest": manifest,
    }
    write_json(ROOT / "PROVENANCE.json", provenance)

    ACE, DataProcessor = load_official_components(args.ollama_url)
    processor = DataProcessor("formula")
    samples = load_processed_subsets(processor, manifest)
    ace_system = ACE(
        api_provider="ollama",
        generator_model=args.model,
        reflector_model=args.model,
        curator_model=args.model,
        max_tokens=args.max_tokens,
        use_bulletpoint_analyzer=False,
    )

    config = {
        "task_name": "formula_local_smoke",
        "num_epochs": 1,
        "max_num_rounds": args.max_reflection_rounds,
        "curator_frequency": 1,
        "eval_steps": args.train_samples,
        "save_steps": 1,
        "playbook_token_budget": 12000,
        "json_mode": True,
        "no_ground_truth": False,
        "save_dir": str(RESULTS_DIR),
        "test_workers": 1,
        "use_bulletpoint_analyzer": False,
    }

    before = set(RESULTS_DIR.glob("ace_run_*")) if RESULTS_DIR.exists() else set()
    results = ace_system.run(
        mode="offline",
        train_samples=samples["train"],
        val_samples=samples["val"],
        test_samples=samples["test"],
        data_processor=processor,
        config=config,
    )
    created = set(RESULTS_DIR.glob("ace_run_*")) - before
    if len(created) != 1:
        raise RuntimeError(f"Expected one new run directory, found {len(created)}")
    run_dir = created.pop()
    summary = summarize_run(run_dir, results, provenance)
    print("\nACE reproduction summary")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

