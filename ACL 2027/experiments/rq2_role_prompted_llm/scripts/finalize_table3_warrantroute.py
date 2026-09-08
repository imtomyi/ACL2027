#!/usr/bin/env python3
"""Finalize and validate the balanced-n100 Table 3 with WarrantGate v0.

This is a post-processing entry point. It is designed to run only after the
reviewer queue is idle. It can repair missing or invalid reviewer records,
rebuild role summaries, create WarrantGate v0 routes, score Table 3, and publish
the combined table only after all integrity checks pass.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import fcntl
import hashlib
import json
import math
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


SCRIPT = Path(__file__).resolve()
RQ2_ROOT = SCRIPT.parents[1]
WORKSPACE = SCRIPT.parents[3]
STORAGE = WORKSPACE / "Storage" / "draft_review_packets"

ROLES = ("generalist", "qualitative_methods", "domain")
MODELS = ("qwen3:8b", "llama3.1:8b", "gemma3:4b")
METHODS = ("Generalist", "Fixed role", "All roles", "WarrantRoute")
MODEL_LABELS = {
    "qwen3:8b": "Qwen3 8B",
    "llama3.1:8b": "Llama 3.1 8B",
    "gemma3:4b": "Gemma 3 4B",
}
MODEL_IDS_BY_LABEL = {label: model for model, label in MODEL_LABELS.items()}
ROUTE_TO_ROLES = {
    "generalist": ("generalist",),
    "qualitative_methods": ("qualitative_methods",),
    "domain": ("domain",),
    "both": ("qualitative_methods", "domain"),
}
TARGET_FLAWS = {
    "unsupported_evidence",
    "source_concentration",
    "counterevidence_loss",
    "contextual_flattening",
    "unsupported_abstraction",
}
TABLE_HEADERS = ("Dataset", "Method", "Model", "TP/N", "Recall (%) ↑")
RECALL_PATTERN = re.compile(r"^([0-9]+(?:\.[0-9]+)?)\s+\[[^\]]+\]$")
TP_N_PATTERN = re.compile(r"^(\d+)/(\d+)$")

BANKS = (
    {
        "dataset": "Dreaddit",
        "run_id": "dreaddit_dev580_working_v1",
        "corpus_id": "dreaddit",
    },
    {
        "dataset": "GoEmotion",
        "run_id": "goemotions_train_all_working_v1",
        "corpus_id": "goemotions",
    },
    {
        "dataset": "CaChe",
        "run_id": "agyw_focus_groups_eval765_working_v1",
        "corpus_id": "agyw_focus_groups",
    },
    {
        "dataset": "ParlaMint-GB",
        "run_id": "parlamint_gb_fullsample_eval100_working_v1",
        "corpus_id": "parlamint_gb",
    },
)


class IntegrityError(RuntimeError):
    """Raised when an artifact cannot be used for the final Table 3 export."""


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def safe_model_dir(model: str) -> str:
    return model.replace(":", "_").replace(".", "_")


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise IntegrityError(f"cannot read JSON {path}: {error}") from error
    if not isinstance(value, dict):
        raise IntegrityError(f"{path}: JSON root is not an object")
    return value


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        handle = path.open("r", encoding="utf-8")
    except OSError as error:
        raise IntegrityError(f"cannot open JSONL {path}: {error}") from error
    with handle:
        for line_number, line in enumerate(handle, 1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                value = json.loads(stripped)
            except json.JSONDecodeError as error:
                raise IntegrityError(f"{path}:{line_number}: invalid JSON: {error}") from error
            if not isinstance(value, dict):
                raise IntegrityError(f"{path}:{line_number}: row is not an object")
            rows.append(value)
    return rows


def load_csv(path: Path) -> list[dict[str, str]]:
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))
    except OSError as error:
        raise IntegrityError(f"cannot read CSV {path}: {error}") from error


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    atomic_write_text(
        path,
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )


def atomic_write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    text = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows
    )
    atomic_write_text(path, text)


def atomic_write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(TABLE_HEADERS))
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def atomic_write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    lines = [
        "| " + " | ".join(TABLE_HEADERS) + " |",
        "| " + " | ".join("---" for _ in TABLE_HEADERS) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(row[header] for header in TABLE_HEADERS) + " |")
    atomic_write_text(path, "\n".join(lines) + "\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_command(command: list[str], log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as log:
        log.write(f"\n[{now_utc()}] $ {subprocess.list2cmdline(command)}\n")
        log.flush()
        completed = subprocess.run(
            command,
            cwd=WORKSPACE,
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        log.write(f"[{now_utc()}] exit_code={completed.returncode}\n")
    if completed.returncode:
        raise subprocess.CalledProcessError(completed.returncode, command)


def packet_paths(bank: dict[str, str], sample_n: int) -> tuple[Path, Path]:
    root = STORAGE / bank["run_id"] / "sample_packets" / f"balanced_n{sample_n}"
    return (
        root / "by_dataset" / f"{bank['corpus_id']}.review_packets.jsonl",
        root / "private" / "truth_map.private.jsonl",
    )


def validate_packet_bank(
    bank: dict[str, str], sample_n: int
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    packet_file, truth_file = packet_paths(bank, sample_n)
    packets = load_jsonl(packet_file)
    truth = load_jsonl(truth_file)
    if len(packets) != sample_n:
        raise IntegrityError(
            f"{bank['dataset']}: expected {sample_n} packets, found {len(packets)}"
        )
    if len(truth) != sample_n:
        raise IntegrityError(
            f"{bank['dataset']}: expected {sample_n} truth rows, found {len(truth)}"
        )
    packet_ids = [str(row.get("packet_id")) for row in packets]
    truth_ids = [str(row.get("packet_id")) for row in truth]
    if len(set(packet_ids)) != sample_n:
        raise IntegrityError(f"{bank['dataset']}: duplicate packet IDs")
    if len(set(truth_ids)) != sample_n:
        raise IntegrityError(f"{bank['dataset']}: duplicate truth-map packet IDs")
    if set(packet_ids) != set(truth_ids):
        raise IntegrityError(f"{bank['dataset']}: packet and truth-map IDs differ")
    for row in packets:
        if str(row.get("corpus_id")) != bank["corpus_id"]:
            raise IntegrityError(f"{bank['dataset']}: packet corpus_id mismatch")
    for row in truth:
        if str(row.get("corpus_id")) != bank["corpus_id"]:
            raise IntegrityError(f"{bank['dataset']}: truth corpus_id mismatch")
        if str(row.get("known_intended_flaw_type")) not in TARGET_FLAWS:
            raise IntegrityError(
                f"{bank['dataset']}: unsupported flaw type "
                f"{row.get('known_intended_flaw_type')!r}"
            )
    return packets, truth


def reviewer_record_issue(
    path: Path,
    *,
    packet_id: str,
    corpus_id: str,
    role: str,
    model: str,
) -> str | None:
    if not path.exists():
        return "missing"
    try:
        row = load_json(path)
    except IntegrityError as error:
        return str(error)
    expected = {
        "packet_id": packet_id,
        "corpus_id": corpus_id,
        "role": role,
        "model_id": model,
    }
    for field, value in expected.items():
        if str(row.get(field)) != value:
            return f"{field}_mismatch:{row.get(field)!r}"
    if row.get("status") != "valid":
        return f"status={row.get('status')!r}"
    if not isinstance(row.get("parsed_rating"), dict):
        return "parsed_rating_missing"
    return None


def collect_reviewer_issues(
    bank: dict[str, str], packets: list[dict[str, Any]]
) -> dict[tuple[str, str], list[tuple[dict[str, Any], str]]]:
    root = STORAGE / bank["run_id"]
    issues: dict[tuple[str, str], list[tuple[dict[str, Any], str]]] = defaultdict(list)
    for role in ROLES:
        for model in MODELS:
            model_dir = root / "reviewer_outputs" / role / safe_model_dir(model)
            for packet in packets:
                packet_id = str(packet["packet_id"])
                issue = reviewer_record_issue(
                    model_dir / f"{packet_id}.json",
                    packet_id=packet_id,
                    corpus_id=bank["corpus_id"],
                    role=role,
                    model=model,
                )
                if issue:
                    issues[(role, model)].append((packet, issue))
    return issues


def repair_reviewer_outputs(
    bank: dict[str, str],
    packets: list[dict[str, Any]],
    *,
    timeout: int,
    num_predict: int,
    max_rounds: int,
    log_path: Path,
) -> None:
    root = STORAGE / bank["run_id"]
    repair_root = root / "postprocess" / "table3_warrantroute_n100" / "repair_inputs"
    for round_number in range(1, max_rounds + 1):
        issues = collect_reviewer_issues(bank, packets)
        if not issues:
            return
        issue_count = sum(len(rows) for rows in issues.values())
        with log_path.open("a", encoding="utf-8") as log:
            log.write(
                f"[{now_utc()}] repair_round={round_number} "
                f"dataset={bank['dataset']} invalid_records={issue_count}\n"
            )
        for (role, model), problem_rows in sorted(issues.items()):
            subset_path = repair_root / role / f"{safe_model_dir(model)}.jsonl"
            atomic_write_jsonl(subset_path, [packet for packet, _issue in problem_rows])
            run_command(
                [
                    sys.executable,
                    str(RQ2_ROOT / "scripts" / "run_working_generalist_reviews.py"),
                    "--packet-file",
                    str(subset_path),
                    "--output-root",
                    str(root / "reviewer_outputs" / role),
                    "--role",
                    role,
                    "--models",
                    model,
                    "--timeout",
                    str(timeout),
                    "--num-predict",
                    str(num_predict),
                    "--overwrite",
                ],
                log_path,
            )
    remaining = collect_reviewer_issues(bank, packets)
    if remaining:
        summary = ", ".join(
            f"{role}/{model}={len(rows)}" for (role, model), rows in sorted(remaining.items())
        )
        raise IntegrityError(
            f"{bank['dataset']}: invalid reviewer records remain after "
            f"{max_rounds} repair rounds: {summary}"
        )


def summarize_roles(bank: dict[str, str], log_path: Path) -> None:
    root = STORAGE / bank["run_id"]
    for role in ROLES:
        role_root = root / "reviewer_outputs" / role
        run_command(
            [
                sys.executable,
                str(RQ2_ROOT / "scripts" / "summarize_working_generalist_reviews.py"),
                "--input-root",
                str(role_root),
                "--output-root",
                str(role_root / "derived"),
            ],
            log_path,
        )


def choose_route(scores: dict[str, Any], tie_order: list[str]) -> str:
    order = {name: index for index, name in enumerate(tie_order)}
    numeric: dict[str, float] = {}
    for action in tie_order:
        value = scores.get(action)
        if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            raise IntegrityError(f"invalid route score for {action}: {value!r}")
        numeric[action] = float(value)
    return max(numeric, key=lambda action: (numeric[action], -order[action]))


def validate_routes(
    path: Path,
    *,
    bank: dict[str, str],
    packet_ids: set[str],
    policy: dict[str, Any],
) -> dict[str, Counter[str]]:
    rows = load_jsonl(path)
    expected_keys = {(model, packet_id) for model in MODELS for packet_id in packet_ids}
    actual_keys: set[tuple[str, str]] = set()
    distribution: dict[str, Counter[str]] = {model: Counter() for model in MODELS}
    for row in rows:
        key = (str(row.get("model_id")), str(row.get("packet_id")))
        if key in actual_keys:
            raise IntegrityError(f"{bank['dataset']}: duplicate WarrantGate route {key}")
        actual_keys.add(key)
        if str(row.get("corpus_id")) != bank["corpus_id"]:
            raise IntegrityError(f"{bank['dataset']}: route corpus_id mismatch for {key}")
        if str(row.get("policy_id")) != str(policy["policy_id"]):
            raise IntegrityError(f"{bank['dataset']}: route policy mismatch for {key}")
        route = str(row.get("route"))
        if route not in ROUTE_TO_ROLES:
            raise IntegrityError(f"{bank['dataset']}: invalid route {route!r} for {key}")
        if tuple(row.get("selected_roles", [])) != ROUTE_TO_ROLES[route]:
            raise IntegrityError(f"{bank['dataset']}: selected_roles mismatch for {key}")
        if row.get("uses_known_intended_flaw_type") is not False:
            raise IntegrityError(f"{bank['dataset']}: truth leakage marker for {key}")
        if row.get("uses_specialist_outputs") is not False:
            raise IntegrityError(f"{bank['dataset']}: specialist-output leakage marker for {key}")
        if row.get("contains_source_text") is not False:
            raise IntegrityError(f"{bank['dataset']}: source-text leakage marker for {key}")
        expected_route = choose_route(dict(row.get("scores", {})), list(policy["tie_order"]))
        features = row.get("features", {})
        if not isinstance(features, dict):
            raise IntegrityError(f"{bank['dataset']}: route features missing for {key}")
        if features.get("valid_generalist") == 0.0:
            expected_route = str(policy["inference_failure_action"])
        if route != expected_route:
            raise IntegrityError(
                f"{bank['dataset']}: selected route {route!r} != argmax "
                f"{expected_route!r} for {key}"
            )
        distribution[key[0]][route] += 1
    if actual_keys != expected_keys:
        missing = len(expected_keys - actual_keys)
        extra = len(actual_keys - expected_keys)
        raise IntegrityError(
            f"{bank['dataset']}: WarrantGate route key mismatch "
            f"(missing={missing}, extra={extra})"
        )
    return distribution


def validate_table_rows(
    rows: list[dict[str, str]], *, dataset: str, sample_n: int
) -> list[dict[str, str]]:
    if len(rows) != len(METHODS) * len(MODELS):
        raise IntegrityError(
            f"{dataset}: expected 12 Table 3 rows, found {len(rows)}"
        )
    expected_keys = {
        (method, MODEL_LABELS[model]) for method in METHODS for model in MODELS
    }
    actual_keys: set[tuple[str, str]] = set()
    for row in rows:
        if tuple(row) != TABLE_HEADERS:
            raise IntegrityError(f"{dataset}: unexpected Table 3 columns {tuple(row)}")
        if row["Dataset"] != dataset:
            raise IntegrityError(
                f"{dataset}: dataset label mismatch {row['Dataset']!r}"
            )
        key = (row["Method"], row["Model"])
        if key in actual_keys:
            raise IntegrityError(f"{dataset}: duplicate Table 3 row {key}")
        actual_keys.add(key)
        match = TP_N_PATTERN.fullmatch(row["TP/N"])
        if not match:
            raise IntegrityError(f"{dataset}: invalid TP/N {row['TP/N']!r} for {key}")
        tp, denominator = (int(value) for value in match.groups())
        if denominator != sample_n or not 0 <= tp <= denominator:
            raise IntegrityError(f"{dataset}: impossible TP/N {row['TP/N']!r} for {key}")
        recall_match = RECALL_PATTERN.fullmatch(row["Recall (%) ↑"])
        if not recall_match:
            raise IntegrityError(
                f"{dataset}: invalid Recall {row['Recall (%) ↑']!r} for {key}"
            )
        reported_recall = float(recall_match.group(1))
        expected_recall = round(100 * tp / denominator, 1)
        if abs(reported_recall - expected_recall) > 0.05:
            raise IntegrityError(
                f"{dataset}: Recall {reported_recall} does not match {tp}/{denominator}"
            )
    if actual_keys != expected_keys:
        raise IntegrityError(f"{dataset}: Table 3 method/model combinations are incomplete")
    return rows


def validate_method_detail(
    path: Path,
    *,
    bank: dict[str, str],
    packet_ids: set[str],
    route_path: Path,
) -> None:
    rows = load_csv(path)
    expected_keys = {
        (method, model, packet_id)
        for method in METHODS
        for model in MODELS
        for packet_id in packet_ids
    }
    actual_keys: set[tuple[str, str, str]] = set()
    route_rows = load_jsonl(route_path)
    routes = {
        (str(row["model_id"]), str(row["packet_id"])): str(row["route"])
        for row in route_rows
    }
    for row in rows:
        key = (str(row["method"]), str(row["model_id"]), str(row["packet_id"]))
        if key in actual_keys:
            raise IntegrityError(f"{bank['dataset']}: duplicate method detail row {key}")
        actual_keys.add(key)
        if str(row.get("corpus_id")) != bank["corpus_id"]:
            raise IntegrityError(f"{bank['dataset']}: method detail corpus mismatch for {key}")
        if key[0] == "WarrantRoute":
            expected_route = routes.get((key[1], key[2]))
            if row.get("route") != expected_route:
                raise IntegrityError(
                    f"{bank['dataset']}: WarrantRoute detail did not apply route for {key}"
                )
            if not str(row.get("status", "")).startswith("working_warrantgate_v0;"):
                raise IntegrityError(
                    f"{bank['dataset']}: WarrantRoute proxy used instead of WarrantGate for {key}"
                )
    if actual_keys != expected_keys:
        missing = len(expected_keys - actual_keys)
        extra = len(actual_keys - expected_keys)
        raise IntegrityError(
            f"{bank['dataset']}: method detail key mismatch "
            f"(missing={missing}, extra={extra})"
        )


def artifact_dirs(
    bank: dict[str, str], sample_n: int, artifact_root: Path | None
) -> tuple[Path, Path]:
    if artifact_root is not None:
        base = artifact_root / bank["run_id"]
        return base / "warrantgate", base / "table"
    root = STORAGE / bank["run_id"]
    return (
        root / "warrantgate" / f"table3_warrantgate_v0_n{sample_n}",
        root / "table_exports" / f"table3_warrantroute_final_n{sample_n}",
    )


def finalize_bank(
    bank: dict[str, str],
    *,
    sample_n: int,
    repair_invalid: bool,
    max_repair_rounds: int,
    timeout: int,
    num_predict: int,
    artifact_root: Path | None,
    log_path: Path,
    policy: dict[str, Any],
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    packets, _truth = validate_packet_bank(bank, sample_n)
    issues = collect_reviewer_issues(bank, packets)
    if issues and repair_invalid:
        repair_reviewer_outputs(
            bank,
            packets,
            timeout=timeout,
            num_predict=num_predict,
            max_rounds=max_repair_rounds,
            log_path=log_path,
        )
        issues = collect_reviewer_issues(bank, packets)
    if issues:
        summary = ", ".join(
            f"{role}/{model}={len(rows)}" for (role, model), rows in sorted(issues.items())
        )
        raise IntegrityError(f"{bank['dataset']}: reviewer output validation failed: {summary}")

    root = STORAGE / bank["run_id"]
    packet_file, truth_file = packet_paths(bank, sample_n)
    summarize_roles(bank, log_path)
    route_dir, table_dir = artifact_dirs(bank, sample_n, artifact_root)
    run_command(
        [
            sys.executable,
            str(RQ2_ROOT / "scripts" / "build_working_warrantgate_routes.py"),
            "--run-root",
            str(root),
            "--packet-file",
            str(packet_file),
            "--policy",
            str(RQ2_ROOT / "config" / "working_warrantgate_v0_policy.json"),
            "--output-dir",
            str(route_dir),
        ],
        log_path,
    )
    packet_ids = {str(row["packet_id"]) for row in packets}
    distribution = validate_routes(
        route_dir / "routes.jsonl",
        bank=bank,
        packet_ids=packet_ids,
        policy=policy,
    )
    run_command(
        [
            sys.executable,
            str(RQ2_ROOT / "scripts" / "score_working_detection_table.py"),
            "--run-root",
            str(root),
            "--truth-map",
            str(truth_file),
            "--roles",
            *ROLES,
            "--models",
            *MODELS,
            "--warrantgate-routes",
            str(route_dir / "routes.jsonl"),
            "--output-dir",
            str(table_dir),
        ],
        log_path,
    )
    table_rows = validate_table_rows(
        load_csv(table_dir / "table3_fill.csv"),
        dataset=bank["dataset"],
        sample_n=sample_n,
    )
    validate_method_detail(
        table_dir / "method_detection_detail.csv",
        bank=bank,
        packet_ids=packet_ids,
        route_path=route_dir / "routes.jsonl",
    )
    return table_rows, {
        "dataset": bank["dataset"],
        "packet_count": sample_n,
        "reviewer_output_count": sample_n * len(ROLES) * len(MODELS),
        "route_count": sample_n * len(MODELS),
        "route_distribution": {
            model: dict(sorted(distribution[model].items())) for model in MODELS
        },
        "route_file": str(route_dir / "routes.jsonl"),
        "table_file": str(table_dir / "table3_fill.csv"),
    }


def ordered_rows(rows: list[dict[str, str]], banks: list[dict[str, str]]) -> list[dict[str, str]]:
    dataset_order = {bank["dataset"]: index for index, bank in enumerate(banks)}
    method_order = {method: index for index, method in enumerate(METHODS)}
    model_order = {MODEL_LABELS[model]: index for index, model in enumerate(MODELS)}
    return sorted(
        rows,
        key=lambda row: (
            dataset_order[row["Dataset"]],
            method_order[row["Method"]],
            model_order[row["Model"]],
        ),
    )


def manuscript_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    last_dataset = ""
    last_method_by_dataset: dict[str, str] = {}
    for row in rows:
        dataset = row["Dataset"]
        method = row["Method"]
        result.append(
            {
                "Dataset": dataset if dataset != last_dataset else "",
                "Method": method if last_method_by_dataset.get(dataset) != method else "",
                "Model": row["Model"],
                "TP/N": row["TP/N"],
                "Recall (%) ↑": row["Recall (%) ↑"],
            }
        )
        last_dataset = dataset
        last_method_by_dataset[dataset] = method
    return result


def select_banks(names: list[str] | None) -> list[dict[str, str]]:
    if not names:
        return list(BANKS)
    wanted = {name.casefold() for name in names}
    selected = [
        bank
        for bank in BANKS
        if bank["dataset"].casefold() in wanted or bank["corpus_id"].casefold() in wanted
    ]
    if len(selected) != len(wanted):
        found = {
            value.casefold()
            for bank in selected
            for value in (bank["dataset"], bank["corpus_id"])
        }
        missing = sorted(name for name in wanted if name not in found)
        raise IntegrityError(f"unknown dataset selection: {', '.join(missing)}")
    return selected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-n", type=int, default=100)
    parser.add_argument("--datasets", nargs="+", default=None)
    parser.add_argument("--repair-invalid", action="store_true")
    parser.add_argument("--max-repair-rounds", type=int, default=5)
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument("--num-predict", type=int, default=256)
    parser.add_argument("--artifact-root", type=Path, default=None)
    parser.add_argument(
        "--output-prefix",
        type=Path,
        default=STORAGE / "table3_warrantroute_n100_final",
    )
    parser.add_argument(
        "--log-path",
        type=Path,
        default=STORAGE / "table3_warrantroute_n100_finalize.log",
    )
    parser.add_argument(
        "--lock-path",
        type=Path,
        default=STORAGE / "table3_warrantroute_n100_finalize.lock",
    )
    args = parser.parse_args()

    if args.sample_n <= 0:
        raise IntegrityError("sample-n must be positive")
    if args.max_repair_rounds <= 0:
        raise IntegrityError("max-repair-rounds must be positive")

    selected_banks = select_banks(args.datasets)
    policy_path = RQ2_ROOT / "config" / "working_warrantgate_v0_policy.json"
    policy = load_json(policy_path)
    args.lock_path.parent.mkdir(parents=True, exist_ok=True)
    with args.lock_path.open("a+", encoding="utf-8") as lock_handle:
        try:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise IntegrityError("another Table 3 finalizer is already running") from error

        args.log_path.parent.mkdir(parents=True, exist_ok=True)
        with args.log_path.open("a", encoding="utf-8") as log:
            log.write(
                f"[{now_utc()}] finalize_start sample_n={args.sample_n} "
                f"datasets={','.join(bank['dataset'] for bank in selected_banks)}\n"
            )

        all_rows: list[dict[str, str]] = []
        dataset_summaries: list[dict[str, Any]] = []
        for bank in selected_banks:
            rows, summary = finalize_bank(
                bank,
                sample_n=args.sample_n,
                repair_invalid=args.repair_invalid,
                max_repair_rounds=args.max_repair_rounds,
                timeout=args.timeout,
                num_predict=args.num_predict,
                artifact_root=args.artifact_root,
                log_path=args.log_path,
                policy=policy,
            )
            all_rows.extend(rows)
            dataset_summaries.append(summary)

        all_rows = ordered_rows(all_rows, selected_banks)
        expected_total = len(selected_banks) * len(METHODS) * len(MODELS)
        if len(all_rows) != expected_total:
            raise IntegrityError(
                f"combined Table 3 expected {expected_total} rows, found {len(all_rows)}"
            )
        output_csv = args.output_prefix.with_suffix(".csv")
        output_md = args.output_prefix.with_suffix(".md")
        output_manuscript_csv = args.output_prefix.with_name(
            args.output_prefix.name + "_manuscript"
        ).with_suffix(".csv")
        output_manifest = args.output_prefix.with_name(
            args.output_prefix.name + "_manifest"
        ).with_suffix(".json")
        atomic_write_csv(output_csv, all_rows)
        atomic_write_markdown(output_md, all_rows)
        atomic_write_csv(output_manuscript_csv, manuscript_rows(all_rows))
        manifest = {
            "manifest_schema_version": "table3-warrantroute-final-v1",
            "status": "validated_complete",
            "created_at_utc": now_utc(),
            "sample_n_per_dataset": args.sample_n,
            "datasets": dataset_summaries,
            "roles": list(ROLES),
            "models": list(MODELS),
            "methods": list(METHODS),
            "table_row_count": len(all_rows),
            "expected_table_row_count": expected_total,
            "reviewer_status_requirement": "valid",
            "warrantroute_policy_id": policy["policy_id"],
            "warrantroute_policy_sha256": sha256_file(policy_path),
            "warrantroute_builder_sha256": sha256_file(
                RQ2_ROOT / "scripts" / "build_working_warrantgate_routes.py"
            ),
            "table_scorer_sha256": sha256_file(
                RQ2_ROOT / "scripts" / "score_working_detection_table.py"
            ),
            "combined_csv": str(output_csv),
            "combined_markdown": str(output_md),
            "manuscript_csv": str(output_manuscript_csv),
            "working_result_only": True,
            "manuscript_eligible": False,
        }
        atomic_write_json(output_manifest, manifest)
        with args.log_path.open("a", encoding="utf-8") as log:
            log.write(
                f"[{now_utc()}] finalize_validated_complete "
                f"rows={len(all_rows)} output={output_csv}\n"
            )
        print(output_csv)
        print(output_manifest)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (IntegrityError, subprocess.CalledProcessError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)

