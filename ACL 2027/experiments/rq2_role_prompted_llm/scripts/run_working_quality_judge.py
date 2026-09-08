#!/usr/bin/env python3
"""Run binary Credibility/Conformability LLM-as-Judge on working packets."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


SCRIPT = Path(__file__).resolve()
WORKSPACE = SCRIPT.parents[3]
DEFAULT_PACKET_FILE = (
    WORKSPACE
    / "Storage"
    / "draft_review_packets"
    / "draftpkt_20260901T052834Z"
    / "by_dataset"
    / "dreaddit.review_packets.jsonl"
)
DEFAULT_OUTPUT_ROOT = (
    WORKSPACE
    / "Storage"
    / "draft_review_packets"
    / "draftpkt_20260901T052834Z"
    / "quality_judge"
    / "credibility_conformability"
)
DEFAULT_JUDGE_MODEL = "qwen3:8b"
OLLAMA_GENERATE_URL = "http://127.0.0.1:11434/api/generate"
HIDDEN_FIELDS = {
    "known_intended_flaw_type",
    "known_intended_flaw_note",
    "review_instruction",
    "flaw_taxonomy",
}
EXPECTED_FIELDS = {
    "credibility",
    "conformability",
    "credibility_rationale",
    "conformability_rationale",
}


def safe_model_dir(model: str) -> str:
    return model.replace(":", "_").replace(".", "_")


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            stripped = line.strip()
            if not stripped:
                continue
            value = json.loads(stripped)
            if not isinstance(value, dict):
                raise ValueError(f"line {line_number}: JSON root is not an object")
            rows.append(value)
    return rows


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: JSON root is not an object")
    return value


def judge_payload(packet: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in packet.items() if key not in HIDDEN_FIELDS}


def build_prompt(packet: dict[str, Any]) -> str:
    payload = judge_payload(packet)
    instructions = """
You are an LLM-as-Judge for qualitative coding output quality.

Evaluate one generated qualitative output against its original input context.
Use only the supplied task payload. Do not use answer keys, target flaw labels,
outside facts, web search, or any other files.

Definitions:
- Credibility evaluates whether the generated codes, sub-themes, or themes can
  represent the data.
- Conformability assesses whether the generated codes, sub-themes, or themes
  are data-driven and consistent with the original input context.

Make a binary decision for each dimension. Return true only when the output
meets the definition for that dimension. Return false when the output is
unsupported, overgeneralized, inconsistent with context, not clearly
data-driven, or cannot be responsibly verified from the supplied context.

Return exactly one JSON object with exactly these fields:
- credibility: boolean
- conformability: boolean
- credibility_rationale: concise string, no source quotations
- conformability_rationale: concise string, no source quotations
"""
    return "\n\n".join(
        [
            instructions.strip(),
            "Task payload JSON:",
            json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2),
        ]
    )


def call_ollama(model: str, prompt: str, timeout: int) -> tuple[str, dict[str, Any]]:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0,
            "top_p": 1,
            "num_ctx": 8192,
            "num_predict": 384,
        },
    }
    request = urllib.request.Request(
        OLLAMA_GENERATE_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        response_payload = json.loads(response.read().decode("utf-8"))
    raw = response_payload.get("response")
    if not isinstance(raw, str):
        raise RuntimeError("ollama_response_missing_text")
    return raw, response_payload


def extract_json_object(raw: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        if not match:
            raise
        value = json.loads(match.group(0))
    if not isinstance(value, dict):
        raise ValueError("parsed_response_not_object")
    return value


def normalize_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "yes", "y", "1", "pass", "correct"}:
            return True
        if lowered in {"false", "no", "n", "0", "fail", "incorrect"}:
            return False
    return None


def normalize_decision(value: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    notes: list[str] = []
    value = dict(value)
    for key in ("credibility", "conformability"):
        original = value.get(key)
        normalized = normalize_bool(original)
        if normalized is None:
            normalized = False
            notes.append(f"normalized_{key}_missing_or_unclear_to_false")
        elif normalized is not original:
            notes.append(f"normalized_{key}_to_boolean")
        value[key] = normalized
    for key in ("credibility_rationale", "conformability_rationale"):
        if value.get(key) is None:
            value[key] = ""
            notes.append(f"normalized_{key}_missing_to_empty_string")
        if not isinstance(value.get(key), str) or not value[key].strip():
            value[key] = "No valid rationale was provided; counted as a binary metric failure."
            notes.append(f"normalized_{key}_empty_to_failure_rationale")
    return value, notes


def validate_decision(value: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if set(value) != EXPECTED_FIELDS:
        errors.append("field_set_mismatch")
    if not isinstance(value.get("credibility"), bool):
        errors.append("credibility_not_boolean")
    if not isinstance(value.get("conformability"), bool):
        errors.append("conformability_not_boolean")
    for key in ("credibility_rationale", "conformability_rationale"):
        rationale = value.get(key)
        if not isinstance(rationale, str) or not rationale.strip() or len(rationale) > 1000:
            errors.append(f"{key}_invalid")
    return errors


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet-file", type=Path, default=DEFAULT_PACKET_FILE)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--judge-model", default=DEFAULT_JUDGE_MODEL)
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    packets = load_jsonl(args.packet_file)
    model_dir = args.output_root / safe_model_dir(args.judge_model)
    started = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    records: list[dict[str, Any]] = []

    for packet in packets:
        packet_id = packet["packet_id"]
        output_file = model_dir / f"{packet_id}.json"
        if output_file.exists() and not args.overwrite:
            records.append(
                {
                    "packet_id": packet_id,
                    "status": "existing",
                    "path": str(output_file),
                }
            )
            print(f"skip existing {args.judge_model} {packet_id}")
            continue
        prompt = build_prompt(packet)
        record: dict[str, Any] = {
            "record_schema_version": "working-quality-judge-output-v1",
            "run_started_at_utc": started,
            "created_at_utc": dt.datetime.now(dt.timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "corpus_id": packet.get("corpus_id"),
            "packet_id": packet_id,
            "output_id": packet.get("output_id"),
            "judged_output_field": "llm_generated_qualitative_claim",
            "judge_model_id": args.judge_model,
            "metric_source_note": "Qiao et al. 2025 definitions; Zheng et al. 2023 LLM-as-Judge binary decision style",
            "prompt_sha256": sha256_text(prompt),
            "source_packet_file": str(args.packet_file),
            "hidden_fields_removed": sorted(HIDDEN_FIELDS),
        }
        try:
            raw, ollama_payload = call_ollama(args.judge_model, prompt, args.timeout)
            parsed_raw = extract_json_object(raw)
            parsed, normalization_notes = normalize_decision(parsed_raw)
            validation_errors = validate_decision(parsed)
            record.update(
                {
                    "status": "valid" if not validation_errors else "schema_warning",
                    "validation_errors": validation_errors,
                    "normalization_notes": normalization_notes,
                    "parsed_decision_raw": parsed_raw,
                    "parsed_decision": parsed,
                    "raw_response": raw,
                    "ollama_done": ollama_payload.get("done"),
                    "ollama_total_duration": ollama_payload.get("total_duration"),
                    "ollama_eval_count": ollama_payload.get("eval_count"),
                }
            )
        except (
            TimeoutError,
            urllib.error.URLError,
            json.JSONDecodeError,
            ValueError,
            RuntimeError,
        ) as exc:
            record.update(
                {
                    "status": "error",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )
        write_json(output_file, record)
        records.append(
            {
                "packet_id": packet_id,
                "status": record["status"],
                "path": str(output_file),
            }
        )
        print(f"{record['status']} {args.judge_model} {packet_id}")

    completed_records = [load_json(Path(row["path"])) for row in records]
    valid_records = [row for row in completed_records if row.get("status") == "valid"]
    credibility_yes = sum(
        1 for row in valid_records if row["parsed_decision"]["credibility"] is True
    )
    conformability_yes = sum(
        1 for row in valid_records if row["parsed_decision"]["conformability"] is True
    )
    denominator = len(valid_records)
    summary = {
        "summary_schema_version": "working-quality-judge-summary-v1",
        "created_at_utc": dt.datetime.now(dt.timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        "packet_file": str(args.packet_file),
        "output_root": str(args.output_root),
        "judge_model_id": args.judge_model,
        "record_count": len(records),
        "valid_count": denominator,
        "credibility_success_rate": credibility_yes / denominator if denominator else None,
        "conformability_success_rate": conformability_yes / denominator if denominator else None,
        "records": records,
    }
    write_json(args.output_root / "run_summary.json", summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
