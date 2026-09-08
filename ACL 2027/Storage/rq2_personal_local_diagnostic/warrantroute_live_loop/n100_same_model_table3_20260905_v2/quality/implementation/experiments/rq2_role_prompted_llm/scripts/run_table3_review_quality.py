#!/usr/bin/env python3
"""Frozen, resumable local review-quality audit of the working n100 baselines."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import fcntl
import hashlib
import importlib.metadata
import io
import json
import os
import re
import statistics
import sys
import tempfile
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

import run_table3_n100_prompt_identity_repair as repair
import run_working_generalist_reviews as reviewer
import score_working_detection_table as detection


SCRIPT = Path(__file__).resolve()
WORKSPACE = SCRIPT.parents[3]
BUNDLE = WORKSPACE / "Storage/draft_review_packets/table3_review_quality_v1"
API = "http://127.0.0.1:11434/api/"
SERVER_LOG = Path.home() / ".ollama/logs/server.log"
METRICS = ("credibility", "conformability")
HEADERS = ("Credibility (%)", "Conformability (%)")
ROLES = ("generalist", "qualitative_methods", "domain")
SAFE_METADATA = {"subreddit", "participant_group", "chamber", "year"}
REMOVED_METADATA = {"split", "stress_label", "label_ids", "word_count"}
REVIEW_FIELDS = ("serious_error_flags", "rationale", "disposition", "cannot_judge")
ID_PATTERN = re.compile(r"\b(?:[ESPRDU][1-9][0-9]*|EXC_[A-Za-z0-9_]+)\b")


class ContractError(RuntimeError):
    pass


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def file_hash(path: Path) -> str:
    return digest(path.read_bytes())


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_write(path: Path, data: str, *, immutable: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".pending-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if immutable:
            os.link(temporary, path)
        else:
            os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def write_json(path: Path, value: Any, *, immutable: bool = False) -> None:
    atomic_write(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n", immutable=immutable)


def api(path: str, payload: dict | None = None, timeout: int = 30) -> dict:
    data = None if payload is None else canonical(payload).encode("utf-8")
    request = urllib.request.Request(API + path, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def runtime(model: str) -> dict:
    models = {row["name"]: row for row in api("tags")["models"]}
    if model not in models:
        raise ContractError(f"judge_not_installed:{model}")
    shown = api("show", {"model": model})
    return {
        "ollama_version": api("version")["version"],
        "model": models[model],
        "template": shown.get("template"),
        "parameters": shown.get("parameters"),
        "capabilities": shown.get("capabilities"),
        "model_info": shown.get("model_info"),
        "python": sys.version,
        "jsonschema": importlib.metadata.version("jsonschema"),
    }


def inside_storage(path: Path) -> Path:
    path = path.resolve()
    path.relative_to((WORKSPACE / "Storage").resolve())
    return path


def check_hashes(bindings: list[dict]) -> None:
    for binding in bindings:
        path = Path(binding["path"])
        if not path.is_file() or file_hash(path) != binding["sha256"]:
            raise ContractError(f"bound_file_changed:{path}")


def bind(path: Path) -> dict:
    return {"path": str(path.resolve()), "sha256": file_hash(path)}


def sanitize_packet(packet: dict) -> tuple[dict, dict]:
    sources = packet["source_text_context"]
    if not sources or len({s["excerpt_id"] for s in sources}) != len(sources):
        raise ContractError("missing_or_duplicate_source_context")
    maps: dict[str, str] = {}
    groups: dict[str, dict[str, str]] = defaultdict(dict)

    def alias(value: str | None, prefix: str) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str) or not value:
            raise ContractError("invalid_provenance_identifier")
        if value in maps:
            return maps[value]
        if value not in groups[prefix]:
            groups[prefix][value] = f"{prefix}{len(groups[prefix]) + 1}"
        mapped = groups[prefix][value]
        maps[value] = mapped
        return mapped

    # Establish aliases for every displayed source before processing references.
    for source in sources:
        for field, prefix in (("excerpt_id", "E"), ("source_id", "S"),
                              ("speaker_id", "P"), ("source_record_id", "D")):
            alias(source.get(field), prefix)
    context = []
    for source in sources:
        if not isinstance(source.get("text"), str) or not source["text"].strip():
            raise ContractError("empty_source_text")
        metadata = source.get("metadata") or {}
        if set(metadata) - SAFE_METADATA - REMOVED_METADATA:
            raise ContractError(f"unreviewed_metadata_keys:{sorted(set(metadata) - SAFE_METADATA - REMOVED_METADATA)}")
        local = source.get("local_context")
        if local is not None:
            if not isinstance(local, dict) or set(local) - {"moderator_question", "preceding_record_ids"}:
                raise ContractError("unreviewed_local_context_shape")
            question = local.get("moderator_question")
            if question is not None and not isinstance(question, str):
                raise ContractError("invalid_moderator_question")
            local = {"moderator_question": question, "preceding_record_ids": [
                alias(value, "D") for value in local.get("preceding_record_ids", [])
            ]}
        context.append({
            "excerpt_id": maps[source["excerpt_id"]],
            "source_id": maps[source["source_id"]],
            "source_record_id": maps.get(source.get("source_record_id")),
            "speaker_id": maps.get(source.get("speaker_id")),
            "text": source["text"], "local_context": local,
            "metadata": {key: value for key, value in metadata.items() if key in SAFE_METADATA},
        })
    claim = packet["llm_generated_qualitative_claim"]
    if not isinstance(claim.get("claim"), str) or not claim["claim"].strip():
        raise ContractError("empty_claim")
    cited = claim["cited_excerpt_ids"]
    if not set(cited).issubset({s["excerpt_id"] for s in sources}):
        raise ContractError("unknown_candidate_citation")
    payload = {
        "research_question": packet["research_question"],
        "source_context": context,
        "reviewed_claim": {"claim": claim["claim"], "cited_excerpt_ids": [maps[v] for v in cited]},
    }
    return payload, maps


def review_bundle(packet: dict, context: dict, maps: dict, ratings: dict, roles: list[str]) -> dict:
    chosen = sorted(roles, key=lambda role: digest(canonical([
        20260904, packet["corpus_id"], packet["packet_id"], role
    ]).encode()))
    aliases = dict(maps)
    for role in chosen:
        for unknown in re.findall(r"\b(?:EXC|PKT|OUT)_[A-Za-z0-9_]+\b", ratings[role]["rationale"]):
            if unknown not in aliases:
                aliases[unknown] = f"U{1 + sum(v.startswith('U') for v in aliases.values())}"
    pattern = re.compile(r"(?<!\w)(?:" + "|".join(re.escape(v) for v in sorted(aliases, key=len, reverse=True)) + r")(?!\w)")
    members = []
    for i, role in enumerate(chosen, 1):
        rating = ratings[role]
        member = {key: rating[key] for key in REVIEW_FIELDS}
        member["rationale"] = pattern.sub(lambda match: aliases[match[0]], member["rationale"])
        member["review_id"] = f"R{i}"
        members.append(member)
    return {**context, "review_bundle": members}


def make_request(config: dict, instruction: str, schema: dict, payload: dict) -> dict:
    generation = config["proposed_generation"]
    prompt = instruction.rstrip() + "\n\nOutput schema:\n" + canonical(schema)
    prompt += "\n\nEvaluation payload JSON:\n" + canonical(payload)
    request = {
        "model": config["primary_judge_candidate"]["model_id"],
        "prompt": prompt, "stream": False, "format": "json",
        "options": {key: generation[key] for key in ("temperature", "top_p", "num_ctx", "num_predict")},
    }
    if "explicit_think" in generation:
        request["think"] = generation["explicit_think"]
    return request


def prepare(run_root: Path, design_path: Path) -> dict:
    if run_root.exists():
        raise ContractError("run_directory_already_exists")
    design = read_json(design_path)
    if design.get("inference_authorized") is not True or design.get("manuscript_eligible") is not False:
        raise ContractError("working_run_not_authorized")
    if design["validation_plan"]["optional_modules_enabled_by_default"]:
        raise ContractError("optional_modules_not_implemented")
    config_path = WORKSPACE / design["input_config"]
    original = read_json(config_path)
    if design["method_members"] != {"Generalist": ["generalist"], "Fixed role": ["qualitative_methods"], "All roles": list(ROLES)}:
        raise ContractError("unexpected_baseline_definition")
    if design["reviewer_models"] != original["models"]:
        raise ContractError("reviewer_model_mismatch")
    instruction_path = design_path.parent / design["prompt_file"]
    schema_path = design_path.parent / design["schema_file"]
    instruction, schema = instruction_path.read_text(), read_json(schema_path)
    Draft202012Validator.check_schema(schema)
    environment = runtime(design["primary_judge_candidate"]["model_id"])
    if environment["model"]["digest"] != design["primary_judge_candidate"]["observed_local_digest"]:
        raise ContractError("judge_digest_changed")
    role_prompts, guide = repair.prompt_assets(original)
    bindings = [bind(p) for p in (SCRIPT, Path(repair.__file__), Path(reviewer.__file__), Path(detection.__file__), design_path, instruction_path, schema_path, config_path)]
    bindings += [bind(WORKSPACE / row["path"]) for row in [*original["role_prompts"].values(), original["shared_rater_guide"]]]
    datasets = {row["corpus_id"]: row for row in original["datasets"]}
    prepared: dict[str, list] = {}
    private_maps = []
    for corpus in design["corpora"]:
        dataset = datasets[corpus]
        packet_path = WORKSPACE / dataset["packet_file"]
        if file_hash(packet_path) != dataset["packet_file_sha256"]:
            raise ContractError(f"packet_hash_mismatch:{corpus}")
        bindings.append(bind(packet_path))
        packets = repair.load_jsonl(packet_path)
        if len(packets) != 100 or len({p["packet_id"] for p in packets}) != 100:
            raise ContractError(f"packet_count_invalid:{corpus}")
        packets.sort(key=lambda p: digest(canonical([20260904, corpus, p["packet_id"]]).encode()))
        prepared[corpus] = []
        for packet in packets:
            if packet["corpus_id"] != corpus:
                raise ContractError("packet_corpus_mismatch")
            context, aliases = sanitize_packet(packet)
            private_maps.append({"corpus_id": corpus, "packet_id": packet["packet_id"], "aliases": aliases,
                                 "source_ids": [s["source_id"] for s in packet["source_text_context"]]})
            group = []
            for model in design["reviewer_models"]:
                ratings, sources = {}, {}
                for role in ROLES:
                    path = WORKSPACE / "Storage/draft_review_packets" / dataset["run_id"] / design["reviewer_output_directory"] / role / reviewer.safe_model_dir(model) / (packet["packet_id"] + ".json")
                    record = read_json(path)
                    if any(record.get(k) != v for k, v in {"status": "valid", "corpus_id": corpus, "packet_id": packet["packet_id"], "model_id": model, "role": role}.items()):
                        raise ContractError(f"review_identity_invalid:{path}")
                    expected = reviewer.sha256_text(repair.build_historical_prompt(role_prompts[role], guide, packet))
                    if record.get("prompt_sha256") != expected:
                        raise ContractError(f"review_prompt_hash_mismatch:{path}")
                    ratings[role] = record["parsed_rating"]
                    if any(key not in ratings[role] for key in REVIEW_FIELDS):
                        raise ContractError("review_fields_missing")
                    sources[role] = bind(path)
                    bindings.append(sources[role])
                for method, roles in design["method_members"].items():
                    payload = review_bundle(packet, context, aliases, ratings, roles)
                    request = make_request(design, instruction, schema, payload)
                    key = [corpus, packet["packet_id"], model, method, design["reviewer_output_directory"]]
                    group.append({"unit_id": digest(canonical(key).encode()), "corpus_id": corpus,
                                  "packet_id": packet["packet_id"], "reviewer_model_id": model,
                                  "method": method, "source_reviews": [sources[r] for r in roles],
                                  "payload": payload, "request_sha256": digest(canonical(request).encode()),
                                  "prompt_utf8_bytes": len(request["prompt"].encode())})
            prepared[corpus].append(group)
    units = [unit for index in range(100) for corpus in design["corpora"] for unit in prepared[corpus][index]]
    if len(units) != 3600 or len({u["unit_id"] for u in units}) != 3600:
        raise ContractError("unit_inventory_invalid")
    longest = max(units, key=lambda u: u["prompt_utf8_bytes"])
    canary_ids = [u["unit_id"] for u in units[:36]]
    if longest["unit_id"] not in canary_ids:
        units.remove(longest)
        units.insert(36, longest)
    gate_ids = list(dict.fromkeys([*canary_ids, longest["unit_id"]]))
    table_csv, table_md = inside_storage(WORKSPACE / design["table_csv"]), inside_storage(WORKSPACE / design["table_markdown"])
    table_rows = list(csv.reader(io.StringIO(table_csv.read_text())))
    if len(table_rows) != 49 or table_rows[0][-2:] != list(HEADERS):
        raise ContractError("unexpected_table_shape")
    expected_keys = {(detection.DATASET_LABELS[u["corpus_id"]], u["method"], detection.MODEL_LABELS[u["reviewer_model_id"]]) for u in units}
    if len({tuple(r[:3]) for r in table_rows[1:]}) != 48 or not expected_keys.issubset({tuple(r[:3]) for r in table_rows[1:]}):
        raise ContractError("table_key_mismatch")
    if any(r[-2:] != ["N/A", "N/A"] for r in table_rows[1:] if tuple(r[:3]) in expected_keys):
        raise ContractError("existing_quality_scores_must_not_be_overwritten")
    run_root.mkdir(parents=True)
    atomic_write(run_root / "units.jsonl", "".join(canonical(u) + "\n" for u in units), immutable=True)
    write_json(run_root / "private/provenance.json", private_maps, immutable=True)
    write_json(run_root / "design_snapshot.json", design, immutable=True)
    write_json(run_root / "schema_snapshot.json", schema, immutable=True)
    atomic_write(run_root / "prompt_snapshot.txt", instruction, immutable=True)
    atomic_write(run_root / "table_before.csv", table_csv.read_text(), immutable=True)
    atomic_write(run_root / "table_before.md", table_md.read_text(), immutable=True)
    manifest = {
        "schema_version": "table3-review-quality-run-v1", "protocol_id": design["protocol_id"],
        "run_id": run_root.name, "created_at_utc": now(), "status": "prepared",
        "authorization": design.get("execution_authorization"), "planned_units": 3600,
        "planned_binary_decisions": 7200, "primary_rows": 36, "deferred_rows": 12,
        "canary_unit_ids": canary_ids, "gate_unit_ids": gate_ids,
        "longest_prompt_utf8_bytes": longest["prompt_utf8_bytes"],
        "longest_input_probe_unit": longest["unit_id"],
        "runtime": environment, "bound_inputs": bindings,
        "frozen_assets": [bind(run_root / name) for name in ("units.jsonl", "design_snapshot.json", "schema_snapshot.json", "prompt_snapshot.txt", "table_before.csv", "table_before.md", "private/provenance.json")],
        "table_paths": {"csv": str(table_csv), "md": str(table_md)},
        "manuscript_eligible": False, "human_audit_status": "not_run",
        "optional_modules_enabled": False, "server_log": str(SERVER_LOG),
    }
    manifest["contract_sha256"] = digest(canonical(manifest).encode())
    write_json(run_root / "manifest.json", manifest, immutable=True)
    return manifest


def allowed_ids(payload: dict) -> set[str]:
    result = {"CLAIM"}
    def visit(value: Any) -> None:
        if isinstance(value, dict):
            for v in value.values():
                visit(v)
        elif isinstance(value, list):
            for v in value:
                visit(v)
        elif isinstance(value, str):
            result.update(ID_PATTERN.findall(value))
    visit(payload)
    return result


def strict_json(raw: str) -> Any:
    def unique(pairs: list) -> dict:
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate_json_key")
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=unique, parse_constant=lambda value: (_ for _ in ()).throw(ValueError("nonfinite_json_number")))


def validate_response(response: dict, unit: dict, schema: dict, generation: dict, model: str) -> tuple[dict | None, list[str]]:
    errors = []
    if response.get("model") != model:
        errors.append("response_model_mismatch")
    if response.get("done") is not True or response.get("done_reason") != "stop":
        errors.append("incomplete_or_truncated_response")
    tokens = response.get("prompt_eval_count")
    if type(tokens) is not int or tokens <= 0:
        errors.append("missing_prompt_token_count")
    elif tokens + generation["num_predict"] >= generation["num_ctx"]:
        errors.append("context_capacity_risk")
    try:
        decision = strict_json(response.get("response", ""))
        validator = Draft202012Validator(schema)
        errors.extend("schema:" + error.message for error in validator.iter_errors(decision))
        if not errors:
            ids = allowed_ids(unit["payload"])
            for metric in METRICS:
                rationale = decision[metric + "_rationale"]
                if len(rationale.split()) > generation["rationale_max_words_per_dimension"]:
                    errors.append(metric + "_rationale_word_limit")
                if set(ID_PATTERN.findall(rationale)) - ids:
                    errors.append(metric + "_unknown_evidence_id")
        return decision, errors
    except (ValueError, TypeError) as exc:
        return None, [*errors, "json_parse:" + str(exc)]


def log_position() -> tuple[int, int]:
    stat = SERVER_LOG.stat()
    return stat.st_ino, stat.st_size


def truncation_since(position: tuple[int, int]) -> bool:
    stat = SERVER_LOG.stat()
    if stat.st_ino != position[0] or stat.st_size < position[1]:
        raise ContractError("server_log_rotated_during_request")
    with SERVER_LOG.open("rb") as handle:
        handle.seek(position[1])
        lines = handle.read().decode("utf-8", errors="replace").lower()
    return log_reports_truncation(lines)


def log_reports_truncation(lines: str) -> bool:
    # llama.cpp reports "truncated = 0" for ordinary, complete requests.
    for line in lines.lower().splitlines():
        if "truncat" not in line:
            continue
        cleared = re.sub(r"\btruncated\s*=\s*(?:0|false)\b", "", line)
        if "truncat" in cleared:
            return True
    return False


def valid_record(record: dict, unit: dict, manifest: dict, schema: dict, design: dict) -> bool:
    if record.get("status") != "valid":
        return False
    if record.get("contract_sha256") != manifest["contract_sha256"] or record.get("request_sha256") != unit["request_sha256"] or record.get("unit_id") != unit["unit_id"]:
        raise ContractError("saved_output_identity_mismatch")
    parsed, errors = validate_response(record["ollama_response"], unit, schema, design["proposed_generation"], design["primary_judge_candidate"]["model_id"])
    if errors or parsed != record.get("decision"):
        raise ContractError("saved_valid_output_failed_validation")
    return True


def recover_interrupted_attempt(run_root: Path, manifest: dict, units: list[dict]) -> None:
    path = run_root / "in_flight.json"
    if not path.exists():
        return
    attempt = read_json(path)
    if attempt.get("status") != "in_flight":
        return
    unit = next((u for u in units if u["unit_id"] == attempt.get("unit_id")), None)
    if (unit is None or attempt.get("contract_sha256") != manifest["contract_sha256"]
            or attempt.get("request_sha256") != unit["request_sha256"]
            or type(attempt.get("attempt")) is not int or not 1 <= attempt["attempt"] <= 3):
        raise ContractError("interrupted_attempt_identity_mismatch")
    target = run_root / "attempts" / unit["unit_id"] / f"{attempt['attempt']:02d}.json"
    if not target.exists():
        attempt.update(status="transport_error", errors=["interrupted_request_outcome_unknown"],
                       recovered_at_utc=now(), wall_seconds=None)
        write_json(target, attempt, immutable=True)
    write_json(path, {"status": "idle", "recovered_at_utc": now()})


def summarize(units: list[dict], records: dict[str, dict]) -> dict:
    grouped: dict[tuple, list] = defaultdict(list)
    complete_pairs = 0
    for unit in units:
        record = records.get(unit["unit_id"], {})
        decision = record.get("decision", {}) if record.get("status") == "valid" else {}
        complete_pairs += all(type(decision.get(m)) is bool for m in METRICS)
        grouped[(unit["corpus_id"], unit["method"], unit["reviewer_model_id"])].append(decision)
    rows = []
    for (corpus, method, model), decisions in grouped.items():
        row = {"corpus_id": corpus, "method": method, "reviewer_model_id": model, "planned": len(decisions)}
        for metric in METRICS:
            passed = sum(d.get(metric) is True for d in decisions)
            failed = sum(d.get(metric) is False for d in decisions)
            missing = len(decisions) - passed - failed
            row[metric] = {"true": passed, "false": failed, "unresolved": missing,
                           "percent": 100 * passed / len(decisions) if not missing else None}
        rows.append(row)
    return {"planned_units": len(units), "valid_records": sum(r.get("status") == "valid" for r in records.values()),
            "completed_binary_pairs": complete_pairs, "progress_percent": round(100 * complete_pairs / len(units), 2), "rows": rows}


def render_table(rows: list[list[str]]) -> tuple[str, str]:
    buffer = io.StringIO(newline="")
    csv.writer(buffer, lineterminator="\n").writerows(rows)
    markdown = "\n".join("| " + " | ".join(row) + " |" for row in [rows[0], ["---"] * len(rows[0]), *rows[1:]]) + "\n"
    return buffer.getvalue(), markdown


def export_tables(run_root: Path, manifest: dict, summary: dict) -> dict:
    rows = list(csv.reader(io.StringIO((run_root / "table_before.csv").read_text())))
    by_key = {(detection.DATASET_LABELS[r["corpus_id"]], r["method"], detection.MODEL_LABELS[r["reviewer_model_id"]]): r for r in summary["rows"]}
    for row in rows[1:]:
        item = by_key.get(tuple(row[:3]))
        if item:
            for index, metric in enumerate(METRICS, 5):
                value = item[metric]["percent"]
                row[index] = "N/A" if value is None else f"{value:.1f}"
    csv_text, md_text = render_table(rows)
    original_md = (run_root / "table_before.md").read_text()
    original_md = original_md.split("\n## Review-Quality Audit\n", 1)[0]
    original_md = original_md.replace("## Quality Metric Status", "## Historical Quality Status (Before This Audit)")
    table_pattern = r"(?m)^\| Dataset \|[^\n]*\n(?:\|[^\n]*\n)+"
    matches = list(re.finditer(table_pattern, original_md))
    if len(matches) != 1:
        raise ContractError("markdown_table_not_uniquely_identified")
    md_text = original_md[:matches[0].start()] + md_text + original_md[matches[0].end():]
    md_text += ("\n## Review-Quality Audit\n\n"
                f"Run: `{manifest['run_id']}`. Judge: `qwen3:8b`. "
                f"Complete binary pairs: {summary['completed_binary_pairs']}/{summary['planned_units']}.\n\n"
                "Credibility and Conformability are review-level rubric pass rates, not claim-level quality, "
                "label-match accuracy, or independently verified correctness. Each completed metric has denominator 100. "
                "N/A means incomplete or unassessable, not zero. WarrantRoute is deferred.\n\n"
                "TP/N and Recall are preserved historical values. Historical reviewer inputs exposed intended-flaw hints. "
                "This retrospective audit does not repair that exposure. Working diagnostic only; not manuscript-eligible. "
                "Human audit and optional repeat/secondary-judge checks have not run.\n\n"
                f"Progress and provenance: `{run_root / 'progress.json'}` and `{run_root / 'manifest.json'}`.\n")
    atomic_write(run_root / "table_current.csv", csv_text)
    atomic_write(run_root / "table_current.md", md_text)
    receipt_path = run_root / "export_receipt.json"
    receipt = read_json(receipt_path) if receipt_path.exists() else {"expected_hashes": {
        "csv": file_hash(run_root / "table_before.csv"), "md": file_hash(run_root / "table_before.md")}}
    desired = {"csv": csv_text, "md": md_text}
    desired_hashes = {key: digest(text.encode()) for key, text in desired.items()}
    for key, target in manifest["table_paths"].items():
        allowed = {receipt["expected_hashes"][key], desired_hashes[key]}
        allowed.add(receipt.get("pending_hashes", {}).get(key))
        if file_hash(Path(target)) not in allowed:
            return {"status": "external_edit_conflict", "path": target, "run_exports_available": True}
    receipt["pending_hashes"] = desired_hashes
    write_json(receipt_path, receipt)
    for key, target in manifest["table_paths"].items():
        atomic_write(Path(target), desired[key])
    write_json(receipt_path, {"expected_hashes": desired_hashes, "updated_at_utc": now()})
    return {"status": "updated", "quality_complete_rows": sum(all(r[m]["percent"] is not None for m in METRICS) for r in summary["rows"])}


def execute(run_root: Path, *, canary_only: bool = False, max_units: int | None = None) -> int:
    manifest = read_json(run_root / "manifest.json")
    expected_contract = manifest.pop("contract_sha256")
    if digest(canonical(manifest).encode()) != expected_contract:
        raise ContractError("manifest_hash_changed")
    manifest["contract_sha256"] = expected_contract
    check_hashes(manifest["bound_inputs"] + manifest["frozen_assets"])
    design = read_json(run_root / "design_snapshot.json")
    schema = read_json(run_root / "schema_snapshot.json")
    instruction = (run_root / "prompt_snapshot.txt").read_text()
    units = repair.load_jsonl(run_root / "units.jsonl")
    environment = runtime(design["primary_judge_candidate"]["model_id"])
    if environment != manifest["runtime"]:
        raise ContractError("runtime_drift")
    recover_interrupted_attempt(run_root, manifest, units)
    records = {}
    attempts: list[dict] = []
    for unit in units:
        for path in sorted((run_root / "attempts" / unit["unit_id"]).glob("*.json")):
            attempt = read_json(path)
            if attempt.get("contract_sha256") != expected_contract or attempt.get("request_sha256") != unit["request_sha256"]:
                raise ContractError("attempt_contract_changed")
            attempts.append(attempt)
            if valid_record(attempt, unit, manifest, schema, design) and unit["unit_id"] not in records:
                records[unit["unit_id"]] = attempt
    gate = set(manifest["gate_unit_ids"])
    model = design["primary_judge_candidate"]["model_id"]
    generation = design["proposed_generation"]
    started = time.monotonic()
    this_run = 0
    consecutive_failures = 0

    def progress(status: str, current: dict | None = None, error: str | None = None) -> dict:
        summary = summarize(units, records)
        durations = [r["wall_seconds"] for r in attempts if r.get("status") == "valid"][-100:]
        median = statistics.median(durations) if len(durations) >= 5 else None
        summary.update({"status": status, "run_id": run_root.name, "updated_at_utc": now(),
                        "pid": os.getpid(), "contract_sha256": expected_contract,
                        "actual_request_attempts": len(attempts),
                        "retry_attempts": sum(max(0, n-1) for n in Counter(a["unit_id"] for a in attempts).values()),
                        "error_attempts": sum(a.get("status") != "valid" for a in attempts),
                        "current": current, "error": error, "median_valid_wall_seconds": median,
                        "eta_seconds": median * (len(units) - len(records)) if median is not None else None,
                        "elapsed_process_seconds": time.monotonic() - started,
                        "human_audit_status": "not_run", "deferred_methods": ["WarrantRoute"],
                        "manuscript_eligible": False})
        summary["export"] = export_tables(run_root, manifest, summary)
        write_json(run_root / "progress.json", summary)
        return summary

    progress("canary_running" if not gate.issubset(records) else "running")
    for unit in units:
        uid = unit["unit_id"]
        if uid in records:
            continue
        if uid not in gate and not gate.issubset(records):
            progress("canary_blocked", error="One or more gate cases exhausted their technical retries.")
            return 2
        if canary_only and uid not in gate:
            progress("canary_complete")
            return 0
        if max_units is not None and this_run >= max_units:
            progress("paused_at_requested_limit")
            return 0
        request = make_request(design, instruction, schema, unit["payload"])
        if digest(canonical(request).encode()) != unit["request_sha256"]:
            raise ContractError("rebuilt_request_hash_mismatch")
        prior = [a for a in attempts if a["unit_id"] == uid]
        current = {k: unit[k] for k in ("unit_id", "corpus_id", "packet_id", "reviewer_model_id", "method")}
        for number in range(len(prior) + 1, 4):
            position = log_position()
            attempt = {**current, "attempt": number, "created_at_utc": now(),
                       "contract_sha256": expected_contract, "request_sha256": unit["request_sha256"],
                       "status": "in_flight", "judged_object": "review_bundle", "judge_model_id": model}
            write_json(run_root / "in_flight.json", attempt)
            progress("canary_running" if uid in gate else "running", current)
            call_started = time.monotonic()
            try:
                response = api("generate", request, generation["timeout_seconds"])
                # Keep the final answer and performance metadata, not private thinking text.
                kept = {k: v for k, v in response.items() if k not in {"thinking", "context", "logprobs"}}
                kept["thinking_character_count"] = len(response.get("thinking", ""))
                decision, errors = validate_response(response, unit, schema, generation, model)
                try:
                    if truncation_since(position):
                        errors.append("server_reported_truncation")
                except (ContractError, OSError) as exc:
                    errors.append("context_log_unverifiable:" + str(exc))
                attempt.update(status="valid" if not errors else "schema_error", decision=decision,
                               errors=errors, ollama_response=kept)
            except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
                attempt.update(status="transport_error", errors=[type(exc).__name__ + ":" + str(exc)])
            attempt["wall_seconds"] = round(time.monotonic() - call_started, 4)
            write_json(run_root / "attempts" / uid / f"{number:02d}.json", attempt, immutable=True)
            attempts.append(attempt)
            write_json(run_root / "in_flight.json", {"status": "idle", "last_unit_id": uid, "updated_at_utc": now()})
            print(f"{now()} {attempt['status']} {unit['corpus_id']} {unit['method']} {unit['reviewer_model_id']} attempt={number} valid={len(records) + (attempt['status'] == 'valid')}/3600", flush=True)
            if attempt["status"] == "valid":
                records[uid] = attempt
                break
            if any(e in {"context_capacity_risk", "server_reported_truncation"} or e.startswith("context_log_unverifiable:") for e in attempt.get("errors", [])):
                progress("context_blocked", current, "Frozen input exceeds the safe context capacity. New contract required.")
                return 2
            if number < 3:
                time.sleep(15 if attempt["status"] == "transport_error" else 1)
        this_run += 1
        consecutive_failures = 0 if uid in records else consecutive_failures + 1
        progress("canary_running" if not gate.issubset(records) else "running", current)
        if uid in gate and uid not in records:
            progress("canary_blocked", current, "Canary case exhausted technical retries.")
            return 2
        if consecutive_failures >= 5:
            progress("repeated_errors_blocked", current, "Five consecutive units failed. No scores were fabricated.")
            return 2
    summary = progress("completed_diagnostic" if len(records) == len(units) and summarize(units, records)["completed_binary_pairs"] == len(units) else "completed_with_unresolved_quality")
    if summary["export"]["status"] != "updated":
        summary["status"] = "completed_export_conflict"
    check_hashes(manifest["bound_inputs"] + manifest["frozen_assets"])
    write_json(run_root / "final.json", summary)
    write_json(run_root / "progress.json", summary)
    return 0 if summary["status"] == "completed_diagnostic" else 2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("prepare", "run"))
    parser.add_argument("--run-id")
    parser.add_argument("--run-root", type=Path)
    parser.add_argument("--design", type=Path, default=BUNDLE / "design.json")
    parser.add_argument("--canary-only", action="store_true")
    parser.add_argument("--max-units", type=int)
    args = parser.parse_args()
    run_root = args.run_root or BUNDLE / "runs" / str(args.run_id)
    if not args.run_root and (not args.run_id or not re.fullmatch(r"[A-Za-z0-9_-]+", args.run_id)):
        parser.error("A safe --run-id or an existing --run-root is required.")
    run_root = inside_storage(run_root)
    BUNDLE.mkdir(parents=True, exist_ok=True)
    with (BUNDLE / ".runner.lock").open("a+") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit("Another review-quality worker holds the lock.")
        try:
            if args.command == "prepare":
                result = prepare(run_root, args.design.resolve())
                print(json.dumps({k: result[k] for k in ("run_id", "status", "planned_units", "longest_prompt_utf8_bytes")}), flush=True)
            else:
                return execute(run_root, canary_only=args.canary_only, max_units=args.max_units)
        except Exception as exc:
            if run_root.exists():
                write_json(run_root / "fatal_error.json", {"status": "blocked", "at_utc": now(), "error": type(exc).__name__ + ":" + str(exc)})
            raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
