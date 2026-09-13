#!/usr/bin/env python3
"""Run independent local ACE loops and save one learned playbook per model."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openai import OpenAI


ROOT = Path(__file__).resolve().parents[1]
ACE_ROOT = ROOT.parent / "upstream"
OUTPUT_ROOT = ROOT / "model_comparison" / "model_specific_ace"
UPSTREAM_COMMIT = "82709de050e1db6e6ef2f07bcb0393560b94992a"
DEFAULT_MODELS = ["llama3.1:8b", "qwen3:8b", "gemma3:4b", "deepseek-r1:8b"]
DATA_FILES = {
    "train": ACE_ROOT / "eval/finance/data/formula_train_subset_500.jsonl",
    "validation": ACE_ROOT / "eval/finance/data/formula_val_subset_300.jsonl",
    "test": ACE_ROOT / "eval/finance/data/formula_test.jsonl",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", nargs="+", default=DEFAULT_MODELS)
    parser.add_argument("--train-samples", type=int, default=3)
    parser.add_argument("--validation-samples", type=int, default=3)
    parser.add_argument("--test-samples", type=int, default=3)
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--reflection-rounds", type=int, default=1)
    parser.add_argument("--max-tokens", type=int, default=1536)
    parser.add_argument("--eval-steps", type=int)
    parser.add_argument("--playbook-token-budget", type=int, default=12000)
    parser.add_argument("--deduplicate", action="store_true")
    parser.add_argument("--native-nonthinking", action="store_true")
    parser.add_argument("--context-window", type=int, default=32768)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--minimum-free-disk-gib", type=float, default=5.0)
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    return parser.parse_args()


def slug(model: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", model.lower()).strip("_")


def read_jsonl(path: Path, count: int) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    if count < 1 or count > len(rows):
        raise ValueError(f"sample count for {path.name} must be in [1, {len(rows)}]")
    return rows[:count]


def ollama_inventory(url: str) -> dict[str, dict[str, Any]]:
    with urllib.request.urlopen(f"{url}/api/tags", timeout=10) as response:
        payload = json.load(response)
    inventory = {}
    for item in payload.get("models", []):
        name = item.get("name") or item.get("model")
        if name:
            inventory[name] = item
    return inventory


def load_official_ace(url: str, native_nonthinking=False, context_window=32768, seed=42):
    sys.path.insert(0, str(ACE_ROOT))
    ace_module = importlib.import_module("ace.ace")
    finance_module = importlib.import_module("eval.finance.data_processor")

    def initialize_local_clients(api_provider: str):
        if api_provider != "ollama":
            raise ValueError(f"Expected ollama provider, received {api_provider!r}")
        if native_nonthinking:
            from ollama_client import OllamaClient
            return tuple(OllamaClient(url, context_window, seed) for _ in range(3))
        kwargs = {
            "api_key": "ollama",
            "base_url": f"{url}/v1",
            "timeout": 900.0,
            "max_retries": 1,
        }
        return OpenAI(**kwargs), OpenAI(**kwargs), OpenAI(**kwargs)

    ace_module.initialize_clients = initialize_local_clients
    return ace_module.ACE, finance_module.DataProcessor


def parse_bullets(playbook: str) -> list[dict[str, Any]]:
    pattern = re.compile(
        r"^\[([^\]]+)\]\s+helpful=(\d+)\s+harmful=(\d+)\s+::\s+(.+)$",
        flags=re.MULTILINE,
    )
    return [
        {
            "id": match.group(1),
            "helpful": int(match.group(2)),
            "harmful": int(match.group(3)),
            "content": match.group(4),
        }
        for match in pattern.finditer(playbook)
    ]


def write_report(experiment: dict[str, Any], path: Path) -> None:
    lines = [
        "# Model-Specific ACE Playbooks",
        "",
        "> Local model substitution experiment. This does not reproduce the paper's model or Table 2 numbers.",
        "",
        f"- Train samples: `{experiment['settings']['train_samples']}`",
        f"- Validation samples: `{experiment['settings']['validation_samples']}`",
        f"- Test samples: `{experiment['settings']['test_samples']}`",
        f"- Epochs: `{experiment['settings']['epochs']}`",
        f"- Reflection rounds: `{experiment['settings']['reflection_rounds']}`",
        "",
        "| Model | Initial acc. | Final acc. | Bullets | ADD operations |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for model in experiment["models"]:
        item = experiment["results"][model]
        lines.append(
            f"| `{model}` | {item['initial_test_accuracy']:.3f} | "
            f"{item['final_test_accuracy']:.3f} | {item['bullet_count']} | "
            f"{item['add_operation_count']} |"
        )

    for model in experiment["models"]:
        item = experiment["results"][model]
        lines.extend([
            "", f"## {model}", "",
            f"Final learned playbook: `{item['playbook_path']}`", "",
            f"Validation-selected playbook used for test scoring: `{item['test_evaluated_playbook_path']}`", "",
        ])
        if item["bullets"]:
            for bullet in item["bullets"]:
                lines.append(f"- `{bullet['id']}` {bullet['content']}")
        else:
            lines.append("No bullet was successfully added by the Curator.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    free_gib = shutil.disk_usage(ROOT).free / 1024**3
    if free_gib < args.minimum_free_disk_gib:
        raise SystemExit(
            f"Insufficient disk space: {free_gib:.2f} GiB free; "
            f"{args.minimum_free_disk_gib:.2f} GiB required before starting. "
            "No inference was started."
        )
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ACE_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if revision != UPSTREAM_COMMIT:
        raise RuntimeError(f"Expected ACE {UPSTREAM_COMMIT}, found {revision}")

    inventory = ollama_inventory(args.ollama_url)
    missing = [model for model in args.models if model not in inventory]
    if missing:
        raise RuntimeError(f"Models not installed in Ollama: {', '.join(missing)}")

    os.environ["HF_HOME"] = str(ROOT / ".hf")
    ACE, DataProcessor = load_official_ace(
        args.ollama_url, args.native_nonthinking, args.context_window, args.seed
    )
    processor = DataProcessor("formula")
    samples = {
        "train": processor.process_task_data(read_jsonl(DATA_FILES["train"], args.train_samples)),
        "validation": processor.process_task_data(
            read_jsonl(DATA_FILES["validation"], args.validation_samples)
        ),
        "test": processor.process_task_data(read_jsonl(DATA_FILES["test"], args.test_samples)),
    }

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    experiment_dir = OUTPUT_ROOT / "runs" / timestamp
    playbook_dir = experiment_dir / "playbooks"
    playbook_dir.mkdir(parents=True, exist_ok=False)
    experiment: dict[str, Any] = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "classification": "local_model_substitution_not_original_paper_model",
        "ace_commit": revision,
        "python": platform.python_version(),
        "models": args.models,
        "settings": {
            "task": "formula",
            "selection": "first_n_records_in_released_order",
            "train_samples": args.train_samples,
            "validation_samples": args.validation_samples,
            "test_samples": args.test_samples,
            "epochs": args.epochs,
            "reflection_rounds": args.reflection_rounds,
            "max_tokens": args.max_tokens,
            "eval_steps": args.eval_steps or args.train_samples,
            "playbook_token_budget": args.playbook_token_budget,
            "deduplicate": args.deduplicate,
            "deduplication_threshold": 0.90,
            "native_nonthinking": args.native_nonthinking,
            "context_window": args.context_window if args.native_nonthinking else None,
            "seed": args.seed if args.native_nonthinking else None,
            "batch_size": 1,
            "ground_truth_feedback": True,
            "initial_playbook": "official_empty_section_template",
            "same_model_for_generator_reflector_curator": True,
            "model_execution": "sequential",
        },
        "results": {},
        "source_sha256": {
            split: hashlib.sha256(path.read_bytes()).hexdigest()
            for split, path in DATA_FILES.items()
        },
        "model_inventory": {model: inventory[model] for model in args.models},
    }
    (experiment_dir / "manifest.json").write_text(
        json.dumps(experiment, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Experiment directory: {experiment_dir}", flush=True)

    for model in args.models:
        print(f"\n{'=' * 72}\nMODEL-SPECIFIC ACE: {model}\n{'=' * 72}", flush=True)
        model_root = experiment_dir / "raw_runs" / slug(model)
        model_root.mkdir(parents=True)
        ace = ACE(
            api_provider="ollama",
            generator_model=model,
            reflector_model=model,
            curator_model=model,
            max_tokens=args.max_tokens,
            use_bulletpoint_analyzer=args.deduplicate,
        )
        config = {
            "task_name": f"formula_model_specific_{slug(model)}",
            "num_epochs": args.epochs,
            "max_num_rounds": args.reflection_rounds,
            "curator_frequency": 1,
            "eval_steps": args.eval_steps or args.train_samples,
            "save_steps": 1,
            "playbook_token_budget": args.playbook_token_budget,
            "json_mode": True,
            "no_ground_truth": False,
            "save_dir": str(model_root),
            "test_workers": 1,
            "use_bulletpoint_analyzer": args.deduplicate,
            "api_provider": "ollama",
            "batch_size": 1,
        }
        before = set(model_root.glob("ace_run_*"))
        results = ace.run(
            mode="offline",
            train_samples=samples["train"],
            val_samples=samples["validation"],
            test_samples=samples["test"],
            data_processor=processor,
            config=config,
        )
        created = set(model_root.glob("ace_run_*")) - before
        if len(created) != 1:
            raise RuntimeError(f"Expected one run directory for {model}, found {len(created)}")
        raw_run = created.pop()
        source_playbook = raw_run / "final_playbook.txt"
        destination_playbook = playbook_dir / f"{slug(model)}_playbook.txt"
        shutil.copy2(source_playbook, destination_playbook)
        selected_playbook = playbook_dir / f"{slug(model)}_selected_playbook.txt"
        shutil.copy2(raw_run / "best_playbook.txt", selected_playbook)
        playbook = destination_playbook.read_text(encoding="utf-8")
        bullets = parse_bullets(playbook)

        operations_path = raw_run / "curator_operations_diff.jsonl"
        operations = []
        if operations_path.exists():
            operations = [
                json.loads(line)
                for line in operations_path.read_text(encoding="utf-8").splitlines()
                if line
            ]
        initial = results["initial_test_results"]
        final = results["final_test_results"]
        experiment["results"][model] = {
            "ollama_digest": inventory[model].get("digest"),
            "ollama_size_bytes": inventory[model].get("size"),
            "raw_run_directory": str(raw_run),
            "playbook_path": str(destination_playbook),
            "test_evaluated_playbook_path": str(selected_playbook),
            "bullet_count": len(bullets),
            "bullets": bullets,
            "operation_count": len(operations),
            "add_operation_count": sum(
                item.get("operation_type") == "ADD" for item in operations
            ),
            "initial_test_accuracy": initial["accuracy"],
            "initial_test_correct": initial["correct"],
            "final_test_accuracy": final["accuracy"],
            "final_test_correct": final["correct"],
            "test_total": final["total"],
        }

    comparison_path = experiment_dir / "comparison.json"
    report_path = experiment_dir / "comparison.md"
    comparison_path.write_text(json.dumps(experiment, indent=2) + "\n", encoding="utf-8")
    write_report(experiment, report_path)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    (OUTPUT_ROOT / "latest.json").write_text(
        json.dumps(
            {
                "experiment_dir": str(experiment_dir),
                "comparison": str(comparison_path),
                "report": str(report_path),
                "playbooks": {
                    model: experiment["results"][model]["playbook_path"]
                    for model in args.models
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"\nComparison: {comparison_path}")
    print(f"Report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
