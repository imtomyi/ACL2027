#!/usr/bin/env python3
"""Run working-bank role-prompted reviews with local Ollama models.

This is a pragmatic runner for the local working packet bank under
Storage/draft_review_packets. It intentionally avoids the source-free formal
freezes and writes raw local outputs for pilot table construction.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


SCRIPT = Path(__file__).resolve()
WORKSPACE = SCRIPT.parents[3]
RQ2_ROOT = SCRIPT.parents[1]
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
    / "reviewer_outputs_prompt_suite_v2"
    / "generalist"
)
ROLE_PROMPTS = {
    "generalist": RQ2_ROOT / "prompts" / "generalist_v2.md",
    "qualitative_methods": RQ2_ROOT / "prompts" / "qualitative_methods_v2.md",
    "domain": RQ2_ROOT / "prompts" / "domain_v2.md",
}
SHARED_GUIDE = (
    WORKSPACE
    / "experiments"
    / "direction_j_llm_as_rater"
    / "protocol"
    / "shared_rater_guide_v1.md"
)
DEFAULT_MODELS = ("qwen3:8b", "llama3.1:8b", "gemma3:4b")
OLLAMA_GENERATE_URL = "http://127.0.0.1:11434/api/generate"
REVIEWER_PAYLOAD_FIELDS = (
    "packet_schema_version",
    "packet_id",
    "research_question",
    "source_text_context",
    "llm_generated_qualitative_claim",
)
FORBIDDEN_PAYLOAD_FIELDS = {
    "known_intended_flaw_type",
    "known_intended_flaw_note",
    "review_instruction",
    "answer_key",
    "target_flaw",
    "route",
    "route_assignment",
    "other_reviewer_output",
}
EXPECTED_FIELDS = {
    "rating_schema_version",
    "evidential_credibility",
    "voice_boundary_preservation",
    "scope_calibration",
    "cannot_judge",
    "confidence",
    "disposition",
    "requested_expertise",
    "serious_error_flags",
    "rationale",
}
ALLOWED_FLAGS = {
    "fabricated_or_altered_quote",
    "wrong_attribution",
    "unsupported_inference",
    "hidden_source_concentration",
    "lost_negative_case",
    "contextual_flattening",
    "unsupported_abstraction",
    "sensitive_or_diagnostic_inference",
    "inconsistent_codebook",
    "other",
}
FLAG_ALIASES = {
    "unsupported_evidence": "unsupported_inference",
    "source_concentration": "hidden_source_concentration",
    "counterevidence_loss": "lost_negative_case",
}


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


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def nested_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        result = set(value)
        for item in value.values():
            result.update(nested_keys(item))
        return result
    if isinstance(value, list):
        result: set[str] = set()
        for item in value:
            result.update(nested_keys(item))
        return result
    return set()


def reviewer_payload(packet: dict[str, Any]) -> dict[str, Any]:
    missing = [field for field in REVIEWER_PAYLOAD_FIELDS if field not in packet]
    if missing:
        raise ValueError(f"reviewer_payload_missing_fields:{','.join(missing)}")
    payload = {field: packet[field] for field in REVIEWER_PAYLOAD_FIELDS}
    leaked = sorted(FORBIDDEN_PAYLOAD_FIELDS.intersection(nested_keys(payload)))
    if leaked:
        raise ValueError(f"forbidden_reviewer_payload_fields:{','.join(leaked)}")
    return payload


def build_prompt(role_prompt: str, shared_guide: str, packet: dict[str, Any]) -> str:
    payload = reviewer_payload(packet)
    return "\n\n".join(
        [
            role_prompt.strip(),
            "Shared rater guide:",
            shared_guide.strip(),
            "Task payload JSON:",
            json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2),
            (
                "Return exactly one JSON object. Do not mention the hidden answer key, "
                "target flaw labels, or any field not present in the task payload. "
                "Keep rationale concise, no more than 60 words."
            ),
        ]
    )


def call_ollama(
    model: str, prompt: str, timeout: int, num_predict: int
) -> tuple[str, dict[str, Any]]:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.2,
            "top_p": 1,
            "num_ctx": 8192,
            "num_predict": num_predict,
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
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        if not match:
            raise
        parsed = json.loads(match.group(0))
    if not isinstance(parsed, dict):
        raise ValueError("parsed_response_not_object")
    return parsed


def normalize_rating(value: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    notes: list[str] = []
    if set(value) == {"direction-j-shared-rating-v1"} and isinstance(
        value["direction-j-shared-rating-v1"], dict
    ):
        value = dict(value["direction-j-shared-rating-v1"])
        notes.append("unwrapped_schema_named_object")
    else:
        value = dict(value)

    if "rating_schema_version" not in value:
        value["rating_schema_version"] = "direction-j-shared-rating-v1"
        notes.append("inserted_rating_schema_version")

    cannot_judge = value.get("cannot_judge")
    if cannot_judge is None:
        value["cannot_judge"] = []
        notes.append("normalized_cannot_judge_null_to_empty_list")
    elif isinstance(cannot_judge, dict):
        value["cannot_judge"] = [
            str(key) for key, item in cannot_judge.items() if item not in {None, False, ""}
        ]
        notes.append("normalized_cannot_judge_object_to_list")

    flags = value.get("serious_error_flags")
    if flags is None:
        value["serious_error_flags"] = []
        notes.append("normalized_serious_error_flags_null_to_empty_list")
    elif isinstance(flags, list):
        normalized_flags: list[str] = []
        for flag in flags:
            normalized = FLAG_ALIASES.get(flag, flag)
            if normalized != flag:
                notes.append(f"mapped_flag:{flag}->{normalized}")
            if normalized not in normalized_flags:
                normalized_flags.append(normalized)
        value["serious_error_flags"] = normalized_flags

    return value, notes


def validate_rating(value: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if set(value) != EXPECTED_FIELDS:
        errors.append("field_set_mismatch")
    if value.get("rating_schema_version") != "direction-j-shared-rating-v1":
        errors.append("schema_version_invalid")
    for field in (
        "evidential_credibility",
        "voice_boundary_preservation",
        "scope_calibration",
        "confidence",
    ):
        item = value.get(field)
        if field == "confidence":
            valid = isinstance(item, int) and 1 <= item <= 5
        else:
            valid = item is None or (isinstance(item, int) and 1 <= item <= 5)
        if not valid:
            errors.append(f"{field}_invalid")
    cannot_judge = value.get("cannot_judge")
    if not isinstance(cannot_judge, list) or len(cannot_judge) != len(set(cannot_judge)):
        errors.append("cannot_judge_invalid")
    flags = value.get("serious_error_flags")
    if (
        not isinstance(flags, list)
        or len(flags) != len(set(flags))
        or any(flag not in ALLOWED_FLAGS for flag in flags)
    ):
        errors.append("serious_error_flags_invalid")
    if value.get("disposition") not in {"accept", "revise", "reject", "escalate"}:
        errors.append("disposition_invalid")
    if value.get("requested_expertise") not in {
        "qualitative_methods",
        "domain",
        "both",
        "none",
    }:
        errors.append("requested_expertise_invalid")
    rationale = value.get("rationale")
    if not isinstance(rationale, str) or not rationale.strip() or len(rationale) > 1000:
        errors.append("rationale_invalid")
    return errors


def safe_model_dir(model: str) -> str:
    return model.replace(":", "_").replace(".", "_")


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet-file", type=Path, default=DEFAULT_PACKET_FILE)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument(
        "--role",
        choices=sorted(ROLE_PROMPTS),
        default="generalist",
        help="Role prompt to apply to every packet.",
    )
    parser.add_argument("--models", nargs="+", default=list(DEFAULT_MODELS))
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument("--num-predict", type=int, default=384)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    packets = load_jsonl(args.packet_file)
    role_prompt_path = ROLE_PROMPTS[args.role]
    role_prompt = read_text(role_prompt_path)
    role_prompt_sha256 = sha256_text(role_prompt)
    shared_guide = read_text(SHARED_GUIDE)
    run_started = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")

    manifest_records: list[dict[str, Any]] = []
    for model in args.models:
        model_dir = args.output_root / safe_model_dir(model)
        for packet in packets:
            packet_id = packet["packet_id"]
            output_file = model_dir / f"{packet_id}.json"
            if output_file.exists() and not args.overwrite:
                existing = json.loads(output_file.read_text(encoding="utf-8"))
                if existing.get("role_prompt_sha256") != role_prompt_sha256:
                    raise RuntimeError(
                        f"existing_output_prompt_contract_mismatch:{output_file}"
                    )
                print(f"skip existing {model} {packet_id}", flush=True)
                continue
            prompt = build_prompt(role_prompt, shared_guide, packet)
            record: dict[str, Any] = {
                "record_schema_version": "working-role-review-output-v2",
                "run_started_at_utc": run_started,
                "created_at_utc": dt.datetime.now(dt.timezone.utc)
                .isoformat()
                .replace("+00:00", "Z"),
                "corpus_id": packet.get("corpus_id"),
                "packet_id": packet_id,
                "output_id": packet.get("output_id"),
                "role": args.role,
                "model_id": model,
                "role_prompt_file": str(role_prompt_path),
                "role_prompt_sha256": role_prompt_sha256,
                "prompt_sha256": sha256_text(prompt),
                "source_packet_file": str(args.packet_file),
                "reviewer_payload_fields": list(REVIEWER_PAYLOAD_FIELDS),
            }
            try:
                raw, ollama_payload = call_ollama(
                    model, prompt, args.timeout, args.num_predict
                )
                parsed_raw = extract_json_object(raw)
                parsed, normalization_notes = normalize_rating(parsed_raw)
                validation_errors = validate_rating(parsed)
                record.update(
                    {
                        "status": "valid" if not validation_errors else "schema_warning",
                        "validation_errors": validation_errors,
                        "normalization_notes": normalization_notes,
                        "parsed_rating_raw": parsed_raw,
                        "parsed_rating": parsed,
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
            manifest_records.append(
                {
                    "model_id": model,
                    "packet_id": packet_id,
                    "status": record["status"],
                    "path": str(output_file),
                }
            )
            print(f"{record['status']} {model} {packet_id}", flush=True)

    manifest = {
        "manifest_schema_version": "working-role-review-run-manifest-v2",
        "created_at_utc": dt.datetime.now(dt.timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        "packet_file": str(args.packet_file),
        "output_root": str(args.output_root),
        "models": args.models,
        "role": args.role,
        "role_prompt_file": str(role_prompt_path),
        "role_prompt_sha256": role_prompt_sha256,
        "reviewer_payload_fields": list(REVIEWER_PAYLOAD_FIELDS),
        "packet_count": len(packets),
        "records": manifest_records,
    }
    write_json(args.output_root / "run_manifest.json", manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
