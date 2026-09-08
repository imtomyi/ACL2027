#!/usr/bin/env python3
"""Prepare, run, resume, and score the private n=100 WarrantRoute live loop."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import fcntl
import hashlib
import io
import json
import os
import platform
import random
import re
import tempfile
import urllib.request
from importlib.metadata import version
from collections import Counter, defaultdict
from pathlib import Path

import warrantroute_loop_runtime as runtime

WORKSPACE = runtime.WORKSPACE
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config/warrantroute_loop_n100_v1.json"
OUTPUT_ROOT = WORKSPACE / "Storage/rq2_personal_local_diagnostic/warrantroute_live_loop"
METHODS = ("warrantroute", "always_on", "no_revision")
TARGET_TO_FLAG = {
    "unsupported_evidence": "unsupported_inference",
    "source_concentration": "hidden_source_concentration",
    "counterevidence_loss": "lost_negative_case",
    "contextual_flattening": "contextual_flattening",
    "unsupported_abstraction": "unsupported_abstraction",
}


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def write_json(path: Path, value: dict) -> None:
    atomic_text(path, json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def get_models() -> dict[str, dict]:
    with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=10) as response:
        models = json.load(response)["models"]
    return {row["name"]: row for row in models}


def verify_models(config: dict, configurations: list[str]) -> dict:
    available = get_models()
    selected = {model for name in configurations for model in config["configurations"][name].values()}
    for model in selected:
        if model not in available:
            raise ValueError(f"model_not_installed:{model}")
        if available[model]["digest"] != config["model_digests"][model]:
            raise ValueError(f"model_digest_mismatch:{model}")
    return {model: {key: available[model][key] for key in ("digest", "size", "details")}
            for model in sorted(selected)}


def inputs_for(config: dict, datasets: list[str], sample_n: int) -> tuple[dict, dict]:
    packets, bindings = {}, {}
    for name in datasets:
        dataset = config["datasets"][name]
        bank = WORKSPACE / "Storage/draft_review_packets" / dataset["bank"] / "sample_packets/balanced_n100"
        source = bank / "by_dataset" / f"{dataset['corpus_id']}.review_packets.jsonl"
        truth = bank / "private/truth_map.private.jsonl"
        rows = read_jsonl(source)
        if len(rows) != config["sample_n"]:
            raise ValueError(f"packet_inventory_mismatch:{name}:{len(rows)}")
        ids = [row["packet_id"] for row in rows]
        if len(ids) != len(set(ids)) or any(not re.fullmatch(r"[A-Za-z0-9_-]+", pid) for pid in ids):
            raise ValueError(f"invalid_packet_ids:{name}")
        if any(row["corpus_id"] != dataset["corpus_id"] for row in rows):
            raise ValueError(f"corpus_binding_mismatch:{name}")
        chosen = sorted(rows, key=lambda row: row["packet_id"])[:sample_n]
        packets[name] = [
            {"packet_id": row["packet_id"], "corpus_id": row["corpus_id"], **runtime.packet_payload(row)}
            for row in chosen
        ]
        bindings[name] = {"source_file": str(source), "source_sha256": sha_file(source),
                          "truth_file": str(truth), "truth_sha256": sha_file(truth),
                          "packet_count": len(chosen), "available_packet_count": len(rows)}
    return packets, bindings


def implementation_files() -> list[Path]:
    return [Path(__file__).resolve(), Path(runtime.__file__),
            ROOT / "scripts/build_working_warrantgate_routes.py",
            runtime.H_ROOT / "scripts/ace_tight_loop_controller.py", runtime.STATE_SCHEMA_PATH]


def selected_names(requested: list[str] | None, available: dict, defaults: list[str]) -> list[str]:
    names = list(available) if requested == ["all"] else list(requested or defaults)
    if len(names) != len(set(names)) or not names or set(names) - set(available):
        raise ValueError("invalid_or_duplicate_selection")
    return names


def plan(args: argparse.Namespace) -> tuple[dict, dict, dict]:
    config = read_json(args.config)
    if config["manuscript_eligible"] is not False or config["data_use"] != "private_working_diagnostic":
        raise ValueError("this_runner_supports_private_working_diagnostics_only")
    if (WORKSPACE / config["output_root"]).resolve() != OUTPUT_ROOT.resolve():
        raise ValueError("working_output_root_mismatch")
    if not 0 <= config["runtime"]["max_revision_rounds"] <= 2:
        raise ValueError("invalid_revision_round_limit")
    if not 4 <= config["runtime"]["max_agent_calls"] <= 12:
        raise ValueError("invalid_agent_call_limit")
    datasets = selected_names(args.datasets, config["datasets"], list(config["datasets"]))
    names = selected_names(args.configurations, config["configurations"], config["default_configurations"])
    sample_n = args.sample_n or config["sample_n"]
    if not 1 <= sample_n <= config["sample_n"]:
        raise ValueError("sample_n_must_be_between_1_and_100")
    methods = args.methods or config["default_methods"]
    if len(methods) != len(set(methods)):
        raise ValueError("duplicate_method")
    models = verify_models(config, names)
    packets, bindings = inputs_for(config, datasets, sample_n)
    prompt = (WORKSPACE / config["prompt_file"]).read_text()
    guide = (WORKSPACE / config["guide_file"]).read_text()
    for rows in packets.values():
        for row in rows:
            if len(prompt) + len(guide) + 2 * len(json.dumps(row)) > config["runtime"]["max_input_characters"]:
                raise ValueError("packet_exceeds_conservative_input_character_screen")
    seeds = [config["repetition_seeds"][0] + index for index in range(args.repetitions)]
    total = sample_n * len(datasets) * len(names) * len(methods) * len(seeds)
    manifest = {
        "plan_version": "warrantroute-live-loop-plan-v1", "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "sample_n_per_dataset": sample_n, "datasets": bindings, "configurations": names,
        "methods": methods, "seeds": seeds, "models": models,
        "expected_trajectories": total, "maximum_agent_calls": total * config["runtime"]["max_agent_calls"],
        "minimum_initial_calls": 2 * total, "new_llm_calls_during_preparation": 0,
        "configuration_assignments": {name: config["configurations"][name] for name in names},
        "implementation": {str(path): sha_file(path) for path in implementation_files()},
        "manuscript_eligible": False, "playbook_updates": False,
        "execution_mode": "serial_independent_initial_passes",
        "runtime_environment": {"python": platform.python_version(), "platform": platform.platform(),
                                "jsonschema": version("jsonschema")},
    }
    return config, manifest, packets


def prepare(args: argparse.Namespace) -> dict:
    config, manifest, packets = plan(args)
    if args.command == "preflight":
        return {"status": "ready_for_private_n100_preparation", **manifest}
    root = WORKSPACE / config["output_root"]
    run_dir = args.run_dir or root / dt.datetime.now(dt.timezone.utc).strftime("n100_%Y%m%dT%H%M%SZ")
    run_dir = run_dir.resolve()
    if not run_dir.is_relative_to(root.resolve()) or run_dir == root.resolve():
        raise ValueError("run_directory_must_be_a_new_child_of_configured_output_root")
    run_dir.mkdir(parents=True, exist_ok=False, mode=0o700)
    write_json(run_dir / "config.json", config)
    assets = {
        "prompt.md": WORKSPACE / config["prompt_file"],
        "guide.md": WORKSPACE / config["guide_file"],
        "gate_policy.json": WORKSPACE / config["gate_policy"],
    }
    manifest["assets"] = {"config.json": sha_file(run_dir / "config.json")}
    for name, path in assets.items():
        atomic_text(run_dir / name, path.read_text())
        manifest["assets"][name] = sha_file(run_dir / name)
    for path in implementation_files():
        snapshot = Path("implementation") / path.relative_to(WORKSPACE)
        atomic_text(run_dir / snapshot, path.read_text())
        manifest["assets"][str(snapshot)] = sha_file(run_dir / snapshot)
    for name, rows in packets.items():
        path = run_dir / "inputs" / f"{name}.json"
        write_json(path, {"packets": rows})
        manifest["datasets"][name].update(input_file=str(path.relative_to(run_dir)), input_sha256=sha_file(path))
    manifest["run_id"] = run_dir.name
    manifest["plan_sha256"] = runtime.digest(manifest)
    write_json(run_dir / "manifest.json", manifest)
    return {"status": "prepared", "run_dir": str(run_dir),
            "expected_trajectories": manifest["expected_trajectories"],
            "maximum_agent_calls": manifest["maximum_agent_calls"],
            "models": list(manifest["models"]), "manuscript_eligible": False}


def load_run(run_dir: Path, *, check_service: bool = False) -> tuple[dict, dict, dict]:
    manifest = read_json(run_dir / "manifest.json")
    content = {key: value for key, value in manifest.items() if key != "plan_sha256"}
    if runtime.digest(content) != manifest["plan_sha256"]:
        raise ValueError("plan_hash_mismatch")
    for filename, expected in manifest["assets"].items():
        if sha_file(run_dir / filename) != expected:
            raise ValueError(f"frozen_asset_changed:{filename}")
    for filename, expected in manifest["implementation"].items():
        if sha_file(Path(filename)) != expected:
            raise ValueError(f"implementation_changed:{Path(filename).name}:prepare_a_new_run")
    config = read_json(run_dir / "config.json")
    if check_service:
        verify_models(config, manifest["configurations"])
    packets = {}
    for name, binding in manifest["datasets"].items():
        path = run_dir / binding["input_file"]
        if sha_file(path) != binding["input_sha256"]:
            raise ValueError(f"frozen_packet_snapshot_changed:{name}")
        packets[name] = read_json(path)["packets"]
    return config, manifest, packets


def jobs(manifest: dict, packets: dict):
    for dataset, rows in packets.items():
        for seed in manifest["seeds"]:
            for name in manifest["configurations"]:
                for method in manifest["methods"]:
                    for packet in rows:
                        yield dataset, seed, name, method, packet


def result_dir(run_dir: Path, dataset: str, seed: int, name: str, method: str, packet: dict) -> Path:
    return run_dir / "results" / dataset / str(seed) / name / method / packet["packet_id"]


def read_result(path: Path, manifest: dict, dataset: str, seed: int, name: str, method: str, packet: dict) -> dict:
    result = read_json(path)
    if result.get("result_sha256") != runtime.digest({key: value for key, value in result.items() if key != "result_sha256"}):
        raise ValueError("result_integrity_mismatch")
    expected = {"plan_sha256": manifest["plan_sha256"], "dataset": dataset,
                "seed": seed, "configuration": name, "method": method, "packet_id": packet["packet_id"]}
    if any(result.get(key) != value for key, value in expected.items()):
        raise ValueError("result_identity_mismatch")
    return result


def execute(args: argparse.Namespace) -> dict:
    run_dir = args.run_dir.resolve()
    config, manifest, packets = load_run(run_dir, check_service=True)
    with (run_dir / "run.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError("run_already_active") from exc
        prompt, guide = (run_dir / "prompt.md").read_text(), (run_dir / "guide.md").read_text()
        policy = read_json(run_dir / "gate_policy.json")
        completed = 0
        failures = 0
        for dataset, seed, name, method, packet in jobs(manifest, packets):
            directory = result_dir(run_dir, dataset, seed, name, method, packet)
            result_file = directory / "result.json"
            if result_file.exists():
                read_result(result_file, manifest, dataset, seed, name, method, packet)
                continue
            verify_models(config, [name])
            client = runtime.AgentClient(config, config["configurations"][name], seed, prompt, guide,
                                         directory / "calls", write_json)
            result = runtime.run_packet(packet, client, policy, method)
            result.update(configuration=name, seed=seed, dataset=dataset, plan_sha256=manifest["plan_sha256"])
            result["result_sha256"] = runtime.digest(result)
            write_json(result_file, result)
            completed += 1
            failures += int(result["error"] is not None)
            print(json.dumps({"dataset": dataset, "configuration": name, "method": method,
                              "packet_id": packet["packet_id"], "status": result["status"],
                              "calls": result["cost"]["agent_calls"]}), flush=True)
            if args.max_packets and completed >= args.max_packets:
                break
        result = progress(run_dir, manifest, packets)
        write_json(run_dir / "progress.json", result)
        return result


def progress(run_dir: Path, manifest: dict, packets: dict) -> dict:
    states: Counter = Counter()
    count = 0
    calls = 0
    failed = 0
    for dataset, seed, name, method, packet in jobs(manifest, packets):
        path = result_dir(run_dir, dataset, seed, name, method, packet) / "result.json"
        if path.exists():
            row = read_result(path, manifest, dataset, seed, name, method, packet)
            count += 1
            states[row["status"]] += 1
            calls += row["cost"]["agent_calls"]
            failed += int(row["error"] is not None)
    return {"status": "complete" if count == manifest["expected_trajectories"] else "incomplete",
            "completed_trajectories": count, "expected_trajectories": manifest["expected_trajectories"],
            "terminal_states": dict(states), "trajectories_with_errors": failed,
            "agent_calls": calls, "manuscript_eligible": False}


def cluster_components(packets: list[dict]) -> dict[str, str]:
    parent = {row["packet_id"]: row["packet_id"] for row in packets}

    def find(value: str) -> str:
        while parent[value] != value:
            parent[value] = parent[parent[value]]
            value = parent[value]
        return value

    owner = {}
    for packet in packets:
        pid = packet["packet_id"]
        for source in packet["source_text_context"]:
            sid = source["source_id"]
            if sid in owner:
                parent[find(pid)] = find(owner[sid])
            else:
                owner[sid] = pid
    return {pid: find(pid) for pid in parent}


def bootstrap_interval(values: dict[str, list[float]], draws: int = 10000) -> list[float] | None:
    if len(values) < 2:
        return None
    groups = list(values.values())
    rng = random.Random(20270826)
    samples = []
    for _ in range(draws):
        chosen = [groups[rng.randrange(len(groups))] for _ in groups]
        samples.append(sum(sum(group) for group in chosen) / sum(len(group) for group in chosen))
    samples.sort()
    return [samples[int(0.025 * draws)], samples[min(draws - 1, int(0.975 * draws))]]


def score(args: argparse.Namespace) -> dict:
    run_dir = args.run_dir.resolve()
    _config, manifest, packets = load_run(run_dir)
    current = progress(run_dir, manifest, packets)
    if current["status"] != "complete":
        raise ValueError("complete_the_frozen_inventory_before_scoring")
    truths = {}
    for dataset, binding in manifest["datasets"].items():
        path = Path(binding["truth_file"])
        if sha_file(path) != binding["truth_sha256"]:
            raise ValueError(f"truth_file_changed:{dataset}")
        truth_rows = read_jsonl(path)
        truths[dataset] = {row["packet_id"]: row["known_intended_flaw_type"] for row in truth_rows}
        if len(truths[dataset]) != len(truth_rows):
            raise ValueError("duplicate_truth_id")
    groups = defaultdict(list)
    packet_detail = []
    for dataset, seed, name, method, packet in jobs(manifest, packets):
        path = result_dir(run_dir, dataset, seed, name, method, packet) / "result.json"
        row = read_result(path, manifest, dataset, seed, name, method, packet)
        target = truths[dataset][packet["packet_id"]]
        if target not in TARGET_TO_FLAG:
            raise ValueError(f"unsupported_truth_family:{target}")
        detected = int(TARGET_TO_FLAG[target] in row["original_detected_flags"])
        detail = {"dataset": dataset, "configuration": name, "method": method, "seed": seed,
                  "packet_id": packet["packet_id"], "detected": detected,
                  "target_flaw": target, "status": row["status"], "cost": row["cost"],
                  "revision_rounds": row["revision_rounds"], "error": row["error"]}
        groups[(dataset, name, method, seed)].append(detail)
        packet_detail.append(detail)
    metrics = []
    for (dataset, name, method, seed), rows in groups.items():
        clusters = cluster_components(packets[dataset])
        clustered = defaultdict(list)
        for row in rows:
            clustered[clusters[row["packet_id"]]].append(row["detected"])
        metrics.append({
            "dataset": dataset, "configuration": name, "method": method, "seed": seed,
            "n": len(rows), "tp": sum(row["detected"] for row in rows),
            "recall": sum(row["detected"] for row in rows) / len(rows),
            "recall_cluster_interval": bootstrap_interval(clustered), "source_components": len(clustered),
            "mean_agent_calls": sum(row["cost"]["agent_calls"] for row in rows) / len(rows),
            "mean_input_tokens": sum(row["cost"]["input_tokens"] for row in rows) / len(rows),
            "mean_output_tokens": sum(row["cost"]["output_tokens"] for row in rows) / len(rows),
            "mean_wall_seconds": sum(row["cost"]["wall_seconds"] for row in rows) / len(rows),
            "mean_revision_rounds": sum(row["revision_rounds"] for row in rows) / len(rows),
            "accepted_fraction": sum(row["status"] == "accepted" for row in rows) / len(rows),
            "error_fraction": sum(row["error"] is not None for row in rows) / len(rows),
            "usage_complete": all(row["cost"]["usage_complete"] for row in rows),
            "repair_quality": None, "manuscript_eligible": False,
        })
    comparisons = []
    for dataset in packets:
        clusters = cluster_components(packets[dataset])
        for seed in manifest["seeds"]:
            keys = [key for key in groups if key[0] == dataset and key[3] == seed]
            for index, left in enumerate(keys):
                for right in keys[index + 1:]:
                    left_rows = {row["packet_id"]: row for row in groups[left]}
                    right_rows = {row["packet_id"]: row for row in groups[right]}
                    diffs = defaultdict(list)
                    for pid in left_rows:
                        diffs[clusters[pid]].append(left_rows[pid]["detected"] - right_rows[pid]["detected"])
                    comparisons.append({"dataset": dataset, "seed": seed,
                                        "left": list(left[1:3]), "right": list(right[1:3]),
                                        "recall_difference": sum(map(sum, diffs.values())) / len(left_rows),
                                        "paired_cluster_interval": bootstrap_interval(diffs),
                                        "interpretation": "exploratory_unadjusted_not_confirmatory"})
    report = {"status": "scored_working_results", "metrics": metrics, "comparisons": comparisons,
              "accepted_is_not_independent_quality": True, "manuscript_eligible": False}
    write_json(run_dir / "comparison.json", report)
    write_json(run_dir / "scoring_detail.private.json", {"rows": packet_detail})
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=list(metrics[0]))
    writer.writeheader()
    writer.writerows(metrics)
    atomic_text(run_dir / "comparison.csv", stream.getvalue())
    lines = ["# WarrantRoute n=100 working comparison", "",
             "Private diagnostic results. Acceptance is a loop decision, not a repair-quality score.", "",
             "| Dataset | Configuration | Method | Seed | TP/N | Recall | Calls | Seconds |",
             "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |"]
    for row in metrics:
        lines.append(f"| {row['dataset']} | {row['configuration']} | {row['method']} | {row['seed']} | "
                     f"{row['tp']}/{row['n']} | {row['recall']:.3f} | {row['mean_agent_calls']:.2f} | "
                     f"{row['mean_wall_seconds']:.2f} |")
    atomic_text(run_dir / "comparison.md", "\n".join(lines) + "\n")
    return {"status": report["status"], "comparison_file": str(run_dir / "comparison.md"),
            "metric_rows": len(metrics), "manuscript_eligible": False}


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    sub = result.add_subparsers(dest="command", required=True)
    for command in ("preflight", "prepare"):
        child = sub.add_parser(command)
        child.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
        child.add_argument("--datasets", nargs="+")
        child.add_argument("--configurations", nargs="+")
        child.add_argument("--methods", nargs="+", choices=METHODS)
        child.add_argument("--sample-n", type=int)
        child.add_argument("--repetitions", type=int, choices=(1, 3), default=1)
        if command == "prepare":
            child.add_argument("--run-dir", type=Path)
    for command in ("run", "status", "score"):
        child = sub.add_parser(command)
        child.add_argument("--run-dir", type=Path, required=True)
        if command == "run":
            child.add_argument("--max-packets", type=int)
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command in {"preflight", "prepare"}:
            report = prepare(args)
        elif args.command == "run":
            if args.max_packets is not None and args.max_packets < 1:
                raise ValueError("max_packets_must_be_positive")
            report = execute(args)
        elif args.command == "score":
            report = score(args)
        else:
            _config, manifest, packets = load_run(args.run_dir)
            report = progress(args.run_dir, manifest, packets)
        print(json.dumps(report, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "blocked", "error_type": type(exc).__name__, "error": str(exc)[:300]}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
