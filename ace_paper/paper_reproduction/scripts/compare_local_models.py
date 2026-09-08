#!/usr/bin/env python3
"""Compare local Ollama models on identical official ACE Finance prompts."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openai import OpenAI


ROOT = Path(__file__).resolve().parents[1]
ACE_ROOT = ROOT.parent / "upstream"
sys.path.insert(0, str(ACE_ROOT))

from ace.prompts.generator import GENERATOR_PROMPT  # noqa: E402
from eval.finance.data_processor import DataProcessor  # noqa: E402
from utils import extract_answer  # noqa: E402


DEFAULT_MODELS = ["llama3.1:8b", "qwen3:8b", "gemma3:4b", "deepseek-r1:8b"]
DATA_FILES = {
    "formula": "formula_test.jsonl",
    "finer": "finer_test_subset_006_seed42.jsonl",
}


def load_samples(task: str, offset: int, count: int) -> list[dict[str, Any]]:
    path = ACE_ROOT / "eval" / "finance" / "data" / DATA_FILES[task]
    raw = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    processor = DataProcessor(task_name=task)
    return processor.process_task_data(raw)[offset : offset + count]


def installed_models() -> list[str]:
    result = subprocess.run(
        ["ollama", "list"], check=True, capture_output=True, text=True
    )
    lines = result.stdout.splitlines()[1:]
    return [line.split()[0] for line in lines if line.strip()]


def parse_final_answer(response: str) -> str:
    try:
        parsed = json.loads(response)
        if isinstance(parsed, dict) and "final_answer" in parsed:
            return str(parsed["final_answer"])
    except json.JSONDecodeError:
        pass
    return extract_answer(response)


def markdown_report(run: dict[str, Any]) -> str:
    lines = [
        "# Local Model Comparison",
        "",
        "> Exploratory local-model output. This is not an ACE paper reproduction result.",
        "",
        f"- Task: `{run['task']}`",
        f"- Samples: `{run['samples']}` from offset `{run['offset']}`",
        f"- Temperature: `{run['settings']['temperature']}`",
        f"- Seed: `{run['settings']['seed']}`",
        f"- Playbook: `{run['playbook']}`",
        "",
        "| Model | Correct | Total | Accuracy | Mean latency (s) |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for model in run["models"]:
        summary = run["results"][model]["summary"]
        lines.append(
            f"| `{model}` | {summary['correct']} | {summary['total']} | "
            f"{summary['accuracy']:.3f} | {summary['mean_latency_seconds']:.2f} |"
        )

    for sample_index in range(run["samples"]):
        lines.extend(["", f"## Sample {run['offset'] + sample_index}", ""])
        target = run["results"][run["models"][0]]["samples"][sample_index]["target"]
        question = run["results"][run["models"][0]]["samples"][sample_index]["question"]
        lines.extend([f"**Question:** {question}", "", f"**Target:** `{target}`", ""])
        for model in run["models"]:
            item = run["results"][model]["samples"][sample_index]
            lines.extend(
                [
                    f"### {model}",
                    "",
                    f"Extracted answer: `{item['final_answer']}`  ",
                    f"Correct: `{item['is_correct']}`  ",
                    f"Latency: `{item['latency_seconds']:.2f}s`",
                    "",
                    "```json",
                    item["response"],
                    "```",
                ]
            )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", nargs="+", default=DEFAULT_MODELS)
    parser.add_argument("--task", choices=sorted(DATA_FILES), default="formula")
    parser.add_argument("--samples", type=int, default=1)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--playbook", type=Path)
    parser.add_argument("--max-tokens", type=int, default=1024)
    parser.add_argument("--num-ctx", type=int, default=32768)
    parser.add_argument("--base-url", default="http://127.0.0.1:11434/v1")
    args = parser.parse_args()

    if args.samples < 1 or args.offset < 0:
        parser.error("--samples must be positive and --offset must be non-negative")

    available = installed_models()
    missing = [model for model in args.models if model not in available]
    if missing:
        parser.error(f"models are not installed in Ollama: {', '.join(missing)}")

    playbook = "(empty)"
    playbook_label = "(empty)"
    if args.playbook:
        playbook = args.playbook.resolve().read_text(encoding="utf-8")
        playbook_label = str(args.playbook.resolve())

    samples = load_samples(args.task, args.offset, args.samples)
    if len(samples) != args.samples:
        parser.error("requested sample range exceeds the dataset")

    processor = DataProcessor(task_name=args.task)
    client = OpenAI(api_key="ollama", base_url=args.base_url, timeout=900.0)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = ROOT / "model_comparison" / "runs" / timestamp
    run_dir.mkdir(parents=True, exist_ok=False)

    run: dict[str, Any] = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "classification": "exploratory_local_model_comparison_not_paper_reproduction",
        "ace_commit": subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ACE_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip(),
        "task": args.task,
        "samples": args.samples,
        "offset": args.offset,
        "models": args.models,
        "playbook": playbook_label,
        "settings": {
            "temperature": 0,
            "seed": 100,
            "max_tokens": args.max_tokens,
            "num_ctx": args.num_ctx,
            "execution": "sequential_models",
        },
        "results": {},
    }

    for model in args.models:
        print(f"\n=== {model} ===", flush=True)
        model_samples = []
        for relative_index, sample in enumerate(samples):
            prompt = GENERATOR_PROMPT.format(
                playbook, "(empty)", sample["question"], sample["context"]
            )
            started = time.perf_counter()
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0,
                    seed=100,
                    max_tokens=args.max_tokens,
                    response_format={"type": "json_object"},
                    extra_body={
                        "think": False,
                        "keep_alive": 0,
                        "options": {"num_ctx": args.num_ctx, "seed": 100},
                    },
                )
                latency = time.perf_counter() - started
                text = response.choices[0].message.content or ""
                final_answer = parse_final_answer(text)
                is_correct = processor.answer_is_correct(final_answer, sample["target"])
                usage = {
                    "prompt_tokens": getattr(response.usage, "prompt_tokens", None),
                    "completion_tokens": getattr(response.usage, "completion_tokens", None),
                }
                error = None
            except Exception as exc:  # Preserve failures as comparable outcomes.
                latency = time.perf_counter() - started
                text = ""
                final_answer = ""
                is_correct = False
                usage = {"prompt_tokens": None, "completion_tokens": None}
                error = f"{type(exc).__name__}: {exc}"

            print(
                f"sample={args.offset + relative_index} answer={final_answer!r} "
                f"correct={is_correct} latency={latency:.2f}s",
                flush=True,
            )
            model_samples.append(
                {
                    "dataset_index": args.offset + relative_index,
                    "question": sample["question"],
                    "context": sample["context"],
                    "target": sample["target"],
                    "prompt": prompt,
                    "response": text,
                    "final_answer": final_answer,
                    "is_correct": is_correct,
                    "latency_seconds": latency,
                    "usage": usage,
                    "error": error,
                }
            )

        correct = sum(item["is_correct"] for item in model_samples)
        total = len(model_samples)
        run["results"][model] = {
            "summary": {
                "correct": correct,
                "total": total,
                "accuracy": correct / total if total else 0,
                "mean_latency_seconds": sum(
                    item["latency_seconds"] for item in model_samples
                )
                / total,
            },
            "samples": model_samples,
        }

    json_path = run_dir / "comparison.json"
    report_path = run_dir / "comparison.md"
    json_path.write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")
    report_path.write_text(markdown_report(run), encoding="utf-8")
    latest = ROOT / "model_comparison" / "latest.json"
    latest.write_text(
        json.dumps({"run_dir": str(run_dir), "report": str(report_path)}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"\nJSON: {json_path}")
    print(f"Report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
