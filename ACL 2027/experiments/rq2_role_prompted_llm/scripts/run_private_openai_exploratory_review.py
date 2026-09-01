#!/usr/bin/env python3
"""Run the frozen private exploratory GPT-5.6 RQ2 review-only lane.

The program sends only the five sealed Dreaddit-train controlled items named in
the active freeze to the OpenAI Responses endpoint. It uses fresh stateless
calls, no tools, no retries, and store=false. All source-bearing request and
response artifacts remain permission-restricted under Storage. Aggregate
outputs are engineering diagnostics and are never manuscript-eligible.
"""

from __future__ import annotations

import argparse
import base64
import csv
import fcntl
import http.client
import importlib.metadata
import json
import math
import os
import platform
import random
import re
import ssl
import statistics
import sys
import threading
import time
import urllib.parse
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jsonschema

from run_private_local_development import (
    RQ2_ROOT,
    WORKSPACE,
    canonical_json,
    load_json,
    reviewer_user_prompt,
    secure_directory,
    sha256_bytes,
    sha256_file,
    validate_sealed_source_run,
    write_restricted,
)


SCRIPT = Path(__file__).resolve()
DEFAULT_CONFIG = RQ2_ROOT / "config" / "private_openai_exploratory_review_freeze.json"
STORAGE_ROOT = WORKSPACE / "Storage" / "rq2_private_openai_exploratory"
STATUS = "engineering_diagnostic_unverified_not_manuscript_eligible"
RUN_ID_RE = re.compile(r"^rq2gpt_[0-9]{8}T[0-9]{6}Z_[a-f0-9]{8}$")
MODEL_IDS = ("gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna")
ROLE_IDS = ("generalist", "methods", "domain")
EXPECTED_SOURCE_ITEM_PATHS = tuple(f"items/variant_{index:02d}.json" for index in range(1, 6))
DISPATCH_LEDGER = STORAGE_ROOT / "dispatch_budget_ledger.jsonl"
EXPECTED_MODELS = [
    {
        "model_id": "gpt-5.6-sol",
        "analysis_class": "exploratory_primary",
        "input_usd_per_million_tokens": 4.0,
        "output_usd_per_million_tokens": 20.0,
    },
    {
        "model_id": "gpt-5.6-terra",
        "analysis_class": "sensitivity",
        "input_usd_per_million_tokens": 2.0,
        "output_usd_per_million_tokens": 12.0,
    },
    {
        "model_id": "gpt-5.6-luna",
        "analysis_class": "sensitivity",
        "input_usd_per_million_tokens": 0.2,
        "output_usd_per_million_tokens": 1.2,
    },
]
EXPECTED_MODEL_ROLE_ACTORS = {
    "gpt-5.6-sol": {
        "generalist": "J_RQ2_GPT56_SOL_G",
        "methods": "J_RQ2_GPT56_SOL_M",
        "domain": "J_RQ2_GPT56_SOL_D",
    },
    "gpt-5.6-terra": {
        "generalist": "J_RQ2_GPT56_TERRA_G",
        "methods": "J_RQ2_GPT56_TERRA_M",
        "domain": "J_RQ2_GPT56_TERRA_D",
    },
    "gpt-5.6-luna": {
        "generalist": "J_RQ2_GPT56_LUNA_G",
        "methods": "J_RQ2_GPT56_LUNA_M",
        "domain": "J_RQ2_GPT56_LUNA_D",
    },
}


class APICallError(RuntimeError):
    def __init__(
        self,
        *,
        stage: str,
        cause_type: str,
        request_payload: dict[str, Any],
        raw_response: dict[str, Any],
        execution: dict[str, Any],
    ) -> None:
        super().__init__(f"OpenAI call failed during {stage}: {cause_type}")
        self.stage = stage
        self.cause_type = cause_type
        self.request_payload = request_payload
        self.raw_response = raw_response
        self.execution = execution


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def resolve_workspace_path(value: str) -> Path:
    path = (WORKSPACE / value).resolve()
    if path != WORKSPACE and WORKSPACE not in path.parents:
        raise ValueError(f"Path escapes workspace: {value}")
    return path


def model_slug(model_id: str) -> str:
    return model_id.replace(".", "p").replace("-", "_")


def make_run_id(requested: str | None) -> str:
    if requested is None:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        requested = f"rq2gpt_{timestamp}_{sha256_bytes(os.urandom(32))[:8]}"
    if not RUN_ID_RE.fullmatch(requested):
        raise ValueError("Run ID must match rq2gpt_YYYYMMDDTHHMMSSZ_abcdefgh")
    return requested


def validate_freeze(
    config: dict[str, Any], config_path: Path, *, include_source_files: bool
) -> dict[str, Path]:
    if config_path.resolve() != DEFAULT_CONFIG.resolve():
        raise ValueError("Only the active OpenAI exploratory freeze may execute")
    if config.get("freeze_version") != "rq2-private-openai-exploratory-review-v1":
        raise ValueError("Unexpected OpenAI exploratory freeze version")
    if config.get("status") != STATUS or config.get("execution_authorized_within_declared_scope") is not True:
        raise ValueError("The OpenAI exploratory lane is not active")
    if config.get("review_only") is not True or config.get("corpus") != "dreaddit":
        raise ValueError("Only review-only Dreaddit development execution is allowed")
    if config.get("split") != "development_train" or config.get("rating_repetitions") != 1:
        raise ValueError("Unexpected split or repetition count")
    if config.get("models") != EXPECTED_MODELS:
        raise ValueError("Frozen GPT-5.6 model set, roles, or prices changed")
    if config.get("model_role_actor_ids") != EXPECTED_MODEL_ROLE_ACTORS:
        raise ValueError("Frozen model-role actor registry changed")
    if config.get("store") is not False or config.get("stream") is not False:
        raise ValueError("OpenAI calls must be stateless and nonstreaming")
    if config.get("tools_field") != "absent" or config.get("automatic_retries") != 0:
        raise ValueError("Tools and retries must remain disabled")
    if config.get("reasoning") != {"effort": "medium", "scope": "current_turn_only_stateless"}:
        raise ValueError("Frozen reasoning settings changed")
    if config.get("response_transport") != "responses_api_json_object_then_exact_local_schema_validation":
        raise ValueError("Unexpected response transport")
    if config.get("input_transport_prefix") != "Return the required response as json.\n\n":
        raise ValueError("Frozen JSON transport prefix changed")

    if config.get("api_url") != "https://api.openai.com/v1/responses":
        raise ValueError("OpenAI API URL changed from the frozen endpoint")
    parsed = urllib.parse.urlparse(config["api_url"])
    network = config.get("network_policy", {})
    if (
        parsed.scheme != "https"
        or parsed.hostname != "api.openai.com"
        or parsed.path != "/v1/responses"
        or parsed.query
        or parsed.fragment
        or network.get("allowed_host") != "api.openai.com"
        or network.get("environment_proxies_disabled") is not True
        or network.get("redirects_disabled") is not True
        or network.get("cloud_call_authorized_for_private_exploratory_rq2") is not True
    ):
        raise ValueError("OpenAI endpoint is outside the frozen Responses route")
    if config.get("max_output_tokens") != 2048 or config.get("max_concurrent_requests") != 3:
        raise ValueError("Frozen output or concurrency limit changed")
    if not isinstance(config.get("execution_order_seed"), int):
        raise ValueError("Execution-order seed is not frozen")
    cost_policy = config.get("cost_policy", {})
    if (
        cost_policy.get("experiment_ceiling_usd") != 3.0
        or cost_policy.get("input_token_overhead_per_call") != 12000
        or cost_policy.get("preflight_input_byte_overhead_per_call") != 2048
        or cost_policy.get("preflight_ceiling_usd") != 0.07
        or cost_policy.get("preflight_max_output_tokens") != 1024
        or cost_policy.get("fail_before_dispatch_if_selected_calls_max_cost_exceeds_ceiling") is not True
    ):
        raise ValueError("Frozen cost ceiling changed")
    if config.get("api_key_environment_variable") != "OPENAI_API_KEY":
        raise ValueError("Unexpected API-key environment variable")
    if config.get("preflight_required_before_source_dispatch") is not True:
        raise ValueError("Source-free preflight gate is not enabled")
    if config.get("preflight_receipt_valid_for_seconds") != 86400:
        raise ValueError("Unexpected preflight receipt validity window")
    privacy = config.get("privacy_and_retention", {})
    if (
        privacy.get("request_store_is_false") is not True
        or privacy.get("source_text_is_transmitted_to_openai_during_an_actual_review_run") is not True
        or privacy.get("claim_zero_retention_prohibited") is not True
    ):
        raise ValueError("Privacy/retention declarations changed")
    boundary = config.get("authorization_boundary", {})
    forbidden = (
        "dreaddit_test",
        "held_out_data",
        "cache2_or_cac_he",
        "cross_domain_confirmatory",
        "human_llm_comparison",
        "fixed_role_selection",
        "manuscript_evidence",
        "publication_or_release",
    )
    if any(boundary.get(name) is not False for name in forbidden):
        raise ValueError("OpenAI exploratory freeze broadens beyond its authorized boundary")

    versions = {
        "python_version": platform.python_version(),
        "jsonschema_version": importlib.metadata.version("jsonschema"),
    }
    for key, actual in versions.items():
        if config.get(key) != actual:
            raise ValueError(f"Runtime version drift for {key}: {actual}")

    paths = {
        "source_run": resolve_workspace_path(config["source_run_dir"]),
        "runner": resolve_workspace_path(config["runner_file"]),
        "source_validator": resolve_workspace_path(config["source_validator_file"]),
        "guide": resolve_workspace_path(config["shared_rater_guide_file"]),
        "item_schema": resolve_workspace_path(config["evaluator_item_schema_file"]),
        "rating_schema": resolve_workspace_path(config["shared_rating_schema_file"]),
    }
    expected_path_values = {
        "source_run_dir": "Storage/rq2_private_local_development/rq2dev_20260826T215429Z_53e4a7e1",
        "runner_file": "experiments/rq2_role_prompted_llm/scripts/run_private_openai_exploratory_review.py",
        "source_validator_file": "experiments/rq2_role_prompted_llm/scripts/run_private_local_development.py",
        "shared_rater_guide_file": "experiments/direction_j_llm_as_rater/protocol/shared_rater_guide_v1.md",
        "evaluator_item_schema_file": "experiments/direction_j_llm_as_rater/schemas/evaluator_item.schema.json",
        "shared_rating_schema_file": "experiments/direction_j_llm_as_rater/schemas/shared_rating.schema.json",
    }
    if any(config.get(key) != expected for key, expected in expected_path_values.items()):
        raise ValueError("Frozen input or executable path changed")
    if config.get("prompts") != {
        "generalist": "prompts/generalist_v1.md",
        "methods": "prompts/methods_v1.md",
        "domain": "prompts/domain_v1.md",
    }:
        raise ValueError("Frozen role-prompt paths changed")
    if set(config.get("prompt_sha256", {})) != set(ROLE_IDS):
        raise ValueError("Frozen role-prompt hash inventory is incomplete or has extra keys")
    for role, relative in config["prompts"].items():
        paths[f"prompt_{role}"] = (RQ2_ROOT / relative).resolve()

    expected_hashes = {
        "runner": config["runner_file_sha256"],
        "source_validator": config["source_validator_file_sha256"],
        "guide": config["shared_rater_guide_sha256"],
        "item_schema": config["evaluator_item_schema_sha256"],
        "rating_schema": config["shared_rating_schema_sha256"],
    }
    for role, expected in config["prompt_sha256"].items():
        expected_hashes[f"prompt_{role}"] = expected
    for name, expected in expected_hashes.items():
        if not isinstance(expected, str) or len(expected) != 64:
            raise ValueError(f"Unpinned hash for {name}")
        if sha256_file(paths[name]) != expected:
            raise ValueError(f"Frozen hash mismatch for {name}")

    source_items = config.get("source_items")
    if (
        not isinstance(source_items, list)
        or len(source_items) != 5
        or any(not isinstance(row, dict) for row in source_items)
        or tuple(row.get("path") for row in source_items) != EXPECTED_SOURCE_ITEM_PATHS
        or any(
            not isinstance(row.get("sha256"), str)
            or re.fullmatch(r"[a-f0-9]{64}", row["sha256"]) is None
            or not isinstance(row.get("size_bytes"), int)
            or row["size_bytes"] <= 0
            for row in source_items
        )
        or config.get("controlled_item_count") != 5
    ):
        raise ValueError("Frozen source-item inventory is not the exact five-item path set")

    if include_source_files:
        source = paths["source_run"]
        if source.name != config["source_run_id"]:
            raise ValueError("Frozen source-run identity changed")
        if sha256_file(source / "output_seal.json") != config["source_output_seal_sha256"]:
            raise ValueError("Frozen source output-seal hash changed")
        seal = load_json(source / "output_seal.json")
        if seal.get("seal_payload_sha256") != config["source_seal_payload_sha256"]:
            raise ValueError("Frozen source seal payload changed")
        if sha256_file(source / "truth_map.private.json") != config["source_truth_map_sha256"]:
            raise ValueError("Frozen source truth map changed")
        frozen_items = {row["path"]: row for row in source_items}
        for relative, row in frozen_items.items():
            path = source / relative
            if sha256_file(path) != row["sha256"] or path.stat().st_size != row["size_bytes"]:
                raise ValueError(f"Frozen source item changed: {relative}")
    return paths


def selected_models(config: dict[str, Any], requested: list[str] | None) -> list[dict[str, Any]]:
    available = {row["model_id"]: row for row in config["models"]}
    ids = list(MODEL_IDS) if not requested else requested
    if len(set(ids)) != len(ids) or any(model_id not in available for model_id in ids):
        raise ValueError("Requested model subset is invalid or contains duplicates")
    return [available[model_id] for model_id in ids]


def estimated_max_cost(
    config: dict[str, Any], models: list[dict[str, Any]], *, source_byte_bound: bool
) -> float:
    if source_byte_bound:
        item_units = sum(int(row["size_bytes"]) for row in config["source_items"])
    else:
        item_units = int(config["cost_policy"]["input_token_overhead_per_call"])
    overhead = int(config["cost_policy"]["input_token_overhead_per_call"])
    max_output = int(config["max_output_tokens"])
    total = 0.0
    for model in models:
        # One UTF-8 byte per input token is an intentionally conservative upper bound.
        input_upper = len(ROLE_IDS) * (item_units + len(config["source_items"]) * overhead)
        output_upper = len(ROLE_IDS) * len(config["source_items"]) * max_output
        total += input_upper * model["input_usd_per_million_tokens"] / 1_000_000
        total += output_upper * model["output_usd_per_million_tokens"] / 1_000_000
    return total


def reserve_dispatch_budget(
    config_path: Path,
    config: dict[str, Any],
    models: list[dict[str, Any]],
    run_id: str,
    max_cost: float,
    preflight_receipt_sha256: str,
) -> dict[str, Any]:
    """Atomically reserve the worst-case spend and prevent duplicate executions."""
    ceiling = float(config["cost_policy"]["experiment_ceiling_usd"])
    if not 0 < max_cost <= ceiling:
        raise ValueError("Dispatch reservation is outside the frozen cost ceiling")
    STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
    STORAGE_ROOT.chmod(0o700)
    freeze_sha256 = sha256_file(config_path)
    requested_model_ids = [row["model_id"] for row in models]
    selected_model_ids = [model_id for model_id in MODEL_IDS if model_id in requested_model_ids]
    execution_signature = sha256_bytes(
        canonical_json(
            {
                "freeze_sha256": freeze_sha256,
                "selected_models": selected_model_ids,
                "rating_repetitions": config["rating_repetitions"],
            }
        )
    )
    record = {
        "document_type": "rq2_private_openai_dispatch_budget_reservation",
        "reserved_at_utc": utc_now(),
        "run_id": run_id,
        "freeze_sha256": freeze_sha256,
        "execution_signature": execution_signature,
        "selected_models": requested_model_ids,
        "canonical_selected_model_set": selected_model_ids,
        "reserved_max_cost_usd": max_cost,
        "experiment_ceiling_usd": ceiling,
        "preflight_receipt_sha256": preflight_receipt_sha256,
        "source_text_present": False,
        "reservation_is_fail_closed_and_append_only": True,
    }
    with DISPATCH_LEDGER.open("a+", encoding="utf-8") as handle:
        DISPATCH_LEDGER.chmod(0o600)
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            handle.seek(0)
            prior: list[dict[str, Any]] = []
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"Dispatch budget ledger is malformed at line {line_number}"
                    ) from exc
                if (
                    not isinstance(row, dict)
                    or row.get("document_type")
                    != "rq2_private_openai_dispatch_budget_reservation"
                    or not isinstance(row.get("reserved_max_cost_usd"), (int, float))
                    or isinstance(row.get("reserved_max_cost_usd"), bool)
                    or not math.isfinite(float(row["reserved_max_cost_usd"]))
                    or row["reserved_max_cost_usd"] < 0
                ):
                    raise ValueError("Dispatch budget ledger contains an invalid reservation")
                prior.append(row)
            if any(row.get("run_id") == run_id for row in prior):
                raise ValueError("Run ID already has a dispatch-budget reservation")
            if any(row.get("execution_signature") == execution_signature for row in prior):
                raise ValueError("This frozen model-set execution has already been reserved")
            reserved_total = sum(
                float(row["reserved_max_cost_usd"])
                for row in prior
                if row.get("freeze_sha256") == freeze_sha256
            )
            if reserved_total + max_cost > ceiling + 1e-12:
                raise ValueError("Cumulative frozen dispatch reservations exceed the cost ceiling")
            record["reserved_total_after_usd"] = reserved_total + max_cost
            handle.seek(0, os.SEEK_END)
            handle.write(canonical_json(record).decode("utf-8"))
            handle.flush()
            os.fsync(handle.fileno())
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    return record


def extract_output_text(response: dict[str, Any]) -> str:
    texts: list[str] = []
    refusals: list[str] = []
    for output in response.get("output", []):
        if not isinstance(output, dict) or output.get("type") != "message":
            continue
        for content in output.get("content", []):
            if not isinstance(content, dict):
                continue
            if content.get("type") == "output_text" and isinstance(content.get("text"), str):
                texts.append(content["text"])
            elif content.get("type") == "refusal":
                refusals.append(str(content.get("refusal", "")))
    if refusals:
        raise ValueError("Provider returned a refusal")
    if len(texts) != 1:
        raise ValueError("Provider did not return exactly one output_text block")
    return texts[0]


def response_execution(
    response: dict[str, Any], headers: dict[str, str], http_status: int, started_at: str, elapsed: float
) -> dict[str, Any]:
    usage = response.get("usage") if isinstance(response.get("usage"), dict) else {}
    output_details = usage.get("output_tokens_details") if isinstance(usage.get("output_tokens_details"), dict) else {}
    input_details = usage.get("input_tokens_details") if isinstance(usage.get("input_tokens_details"), dict) else {}
    return {
        "started_at_utc": started_at,
        "completed_at_utc": utc_now(),
        "elapsed_seconds": elapsed,
        "http_status": http_status,
        "request_id": headers.get("x-request-id"),
        "response_id": response.get("id"),
        "response_status": response.get("status"),
        "returned_model": response.get("model"),
        "service_tier": response.get("service_tier"),
        "incomplete_details": response.get("incomplete_details"),
        "input_tokens": usage.get("input_tokens"),
        "cached_input_tokens": input_details.get("cached_tokens"),
        "output_tokens": usage.get("output_tokens"),
        "reasoning_tokens": output_details.get("reasoning_tokens"),
        "total_tokens": usage.get("total_tokens"),
    }


def build_request_payload(
    config: dict[str, Any],
    model_id: str,
    instructions: str,
    input_text: str,
    *,
    max_output_tokens: int | None = None,
) -> dict[str, Any]:
    return {
        "model": model_id,
        "instructions": instructions,
        "input": config["input_transport_prefix"] + input_text,
        "reasoning": {"effort": config["reasoning"]["effort"], "context": "current_turn"},
        "text": {"format": {"type": "json_object"}},
        "max_output_tokens": max_output_tokens or config["max_output_tokens"],
        "service_tier": "default",
        "store": False,
        "stream": False,
    }


def api_call(
    config: dict[str, Any],
    model_id: str,
    instructions: str,
    input_text: str,
    rating_schema: dict[str, Any],
    *,
    max_output_tokens: int | None = None,
    request_artifact_path: Path | None = None,
    response_artifact_path: Path | None = None,
    response_headers_artifact_path: Path | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    key_name = config["api_key_environment_variable"]
    api_key = os.environ.get(key_name)
    if not api_key:
        raise RuntimeError(f"{key_name} is not set")
    payload = build_request_payload(
        config,
        model_id,
        instructions,
        input_text,
        max_output_tokens=max_output_tokens,
    )
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if request_artifact_path is not None:
        write_restricted(request_artifact_path, body, raw=True)
    parsed_url = urllib.parse.urlparse(config["api_url"])
    started_at = utc_now()
    started = time.monotonic()
    raw_body = b""
    headers: dict[str, str] = {}
    status = 0
    try:
        connection = http.client.HTTPSConnection(
            parsed_url.hostname,
            port=443,
            timeout=int(config["request_timeout_seconds"]),
            context=ssl.create_default_context(),
        )
        connection.request(
            "POST",
            parsed_url.path,
            body=body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "warrant-route-rq2-private-exploratory/1",
            },
        )
        http_response = connection.getresponse()
        status = http_response.status
        headers = {key.lower(): value for key, value in http_response.getheaders()}
        raw_body = http_response.read(5_000_001)
        connection.close()
        if response_artifact_path is not None:
            write_restricted(response_artifact_path, raw_body, raw=True)
        if response_headers_artifact_path is not None:
            write_restricted(response_headers_artifact_path, headers)
        if len(raw_body) > 5_000_000:
            raise ValueError("Provider response exceeded the frozen size limit")
        response = json.loads(raw_body)
        if not isinstance(response, dict):
            raise ValueError("Provider response was not a JSON object")
    except Exception as exc:
        elapsed = time.monotonic() - started
        if response_artifact_path is not None and not response_artifact_path.exists():
            write_restricted(
                response_artifact_path,
                {
                    "no_wire_response_body": True,
                    "failure_type": type(exc).__name__,
                },
            )
        if (
            response_headers_artifact_path is not None
            and not response_headers_artifact_path.exists()
        ):
            write_restricted(response_headers_artifact_path, headers)
        raw = {
            "transport_or_parse_error": {
                "type": type(exc).__name__,
                "http_status": status or None,
                "response_body_base64": base64.b64encode(raw_body).decode("ascii") if raw_body else None,
                "response_body_sha256": sha256_bytes(raw_body) if raw_body else None,
                "response_headers": headers,
            }
        }
        raise APICallError(
            stage="transport_or_http_parse",
            cause_type=type(exc).__name__,
            request_payload=payload,
            raw_response=raw,
            execution={
                "started_at_utc": started_at,
                "completed_at_utc": utc_now(),
                "elapsed_seconds": elapsed,
                "http_status": status or None,
                "request_id": headers.get("x-request-id"),
            },
        ) from exc

    elapsed = time.monotonic() - started
    execution = response_execution(response, headers, status, started_at, elapsed)
    try:
        if status < 200 or status >= 300:
            raise ValueError("Provider returned a non-success HTTP status")
        if response.get("status") != "completed":
            raise ValueError("Provider response did not complete")
        returned = response.get("model")
        if returned != model_id:
            raise ValueError("Provider returned a model other than the exact frozen model ID")
        output_text = extract_output_text(response)
        rating = json.loads(output_text)
        jsonschema.validate(rating, rating_schema)
    except Exception as exc:
        raise APICallError(
            stage="response_validation",
            cause_type=type(exc).__name__,
            request_payload=payload,
            raw_response=response,
            execution=execution,
        ) from exc
    return rating, payload, {"raw": response, "headers": headers, "execution": execution}


def sanitized_failure(config: dict[str, Any], exc: Exception) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    if isinstance(exc, APICallError):
        provider_error = (
            exc.raw_response.get("error")
            if isinstance(exc.raw_response.get("error"), dict)
            else {}
        )
        return (
            exc.request_payload,
            exc.raw_response,
            exc.execution,
            {
                "type": type(exc).__name__,
                "stage": exc.stage,
                "cause_type": exc.cause_type,
                "http_status": exc.execution.get("http_status"),
                "provider_error_type": provider_error.get("type"),
                "provider_error_code": provider_error.get("code"),
                "provider_error_param": provider_error.get("param"),
            },
        )
    return (
        {"model": None, "request_not_constructed_due_to_internal_error": True},
        {"terminal_error_type": type(exc).__name__},
        {"elapsed_seconds": None},
        {"type": type(exc).__name__, "stage": "pre_dispatch_or_internal"},
    )


def actual_cost(model: dict[str, Any], execution: dict[str, Any]) -> float | None:
    input_tokens = execution.get("input_tokens")
    output_tokens = execution.get("output_tokens")
    if not isinstance(input_tokens, int) or not isinstance(output_tokens, int):
        return None
    return (
        input_tokens * model["input_usd_per_million_tokens"]
        + output_tokens * model["output_usd_per_million_tokens"]
    ) / 1_000_000


def score(
    observations: list[dict[str, Any]],
    truth: list[dict[str, Any]],
    config: dict[str, Any],
    selected_model_ids: list[str],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    truth_by_item = {row["item_id"]: row for row in truth}
    model_rows = {row["model_id"]: row for row in config["models"]}
    observed_models = {row.get("model_id") for row in observations}
    if (
        not selected_model_ids
        or len(selected_model_ids) != len(set(selected_model_ids))
        or observed_models != set(selected_model_ids)
    ):
        raise ValueError("Observation model set does not exactly match the selected model set")
    expected_cells = {
        (model_id, role, item_id, 1)
        for model_id in selected_model_ids
        for role in ROLE_IDS
        for item_id in truth_by_item
    }
    actual_cells = [
        (
            row.get("model_id"),
            row.get("prompted_role"),
            row.get("item_id"),
            row.get("rating_repetition"),
        )
        for row in observations
    ]
    if len(actual_cells) != len(set(actual_cells)) or set(actual_cells) != expected_cells:
        raise ValueError("Observation cells do not form the complete unique model-role-item product")
    summary: dict[str, dict[str, dict[str, Any]]] = {}
    by_flaw: dict[str, dict[str, dict[str, dict[str, Any]]]] = {}
    scoring_rows: list[dict[str, Any]] = []
    for model_id in {row["model_id"] for row in observations}:
        summary[model_id] = {
            role: {"tp": 0, "n": 0, "terminal_failures": 0} for role in ROLE_IDS
        }
        by_flaw[model_id] = {
            role: {
                family: {"tp": 0, "n": 0, "terminal_failures": 0}
                for family in config["flaw_families"]
            }
            for role in ROLE_IDS
        }
    for observation in observations:
        model_id = observation["model_id"]
        role = observation["prompted_role"]
        target = truth_by_item[observation["item_id"]]
        family = target["target_flaw"]
        required = target["required_flag"]
        flags = [] if observation["rating"] is None else observation["rating"]["serious_error_flags"]
        cannot_judge = [] if observation["rating"] is None else observation["rating"]["cannot_judge"]
        detected = (
            observation["status"] == "valid"
            and not cannot_judge
            and required in flags
        )
        cell = summary[model_id][role]
        flaw_cell = by_flaw[model_id][role][family]
        cell["n"] += 1
        flaw_cell["n"] += 1
        if detected:
            cell["tp"] += 1
            flaw_cell["tp"] += 1
        if observation["status"] != "valid":
            cell["terminal_failures"] += 1
            flaw_cell["terminal_failures"] += 1
        scoring_rows.append(
            {
                "observation_id": observation["observation_id"],
                "model_id": model_id,
                "role": role,
                "item_id": observation["item_id"],
                "target_flaw": family,
                "required_flag": required,
                "detected": detected,
                "observation_status": observation["status"],
            }
        )
    for model_id, roles in summary.items():
        for role, cell in roles.items():
            cell["recall"] = cell["tp"] / cell["n"] if cell["n"] else None
            for flaw_cell in by_flaw[model_id][role].values():
                flaw_cell["recall"] = flaw_cell["tp"] / flaw_cell["n"] if flaw_cell["n"] else None

    operations: dict[str, Any] = {}
    for model_id in summary:
        model_observations = [row for row in observations if row["model_id"] == model_id]
        valid = [row for row in model_observations if row["status"] == "valid"]
        latencies = [row["execution"]["elapsed_seconds"] for row in valid]
        costs = [
            row["estimated_cost_usd"]
            for row in model_observations
            if row["estimated_cost_usd"] is not None
        ]
        operations[model_id] = {
            "valid_calls": len(valid),
            "total_calls": len(model_observations),
            "input_tokens": sum((row["execution"].get("input_tokens") or 0) for row in valid),
            "output_tokens": sum((row["execution"].get("output_tokens") or 0) for row in valid),
            "reasoning_tokens": sum((row["execution"].get("reasoning_tokens") or 0) for row in valid),
            "estimated_known_cost_usd": sum(costs),
            "unknown_cost_call_count": sum(
                row["estimated_cost_usd"] is None for row in model_observations
            ),
            "latency_seconds": {
                "median": statistics.median(latencies) if latencies else None,
                "min": min(latencies) if latencies else None,
                "max": max(latencies) if latencies else None,
            },
            "analysis_class": model_rows[model_id]["analysis_class"],
        }
    return (
        {
            "document_type": "rq2_private_openai_exploratory_results",
            "status": STATUS,
            "manuscript_eligible": False,
            "independent_variant_verification_complete": False,
            "warning": "Unverified one-packet, one-repeat engineering diagnostic; do not compare as a main-study result.",
            "model_role_summary": summary,
            "model_role_by_flaw": by_flaw,
            "operations": operations,
            "scoring_rule": "exact target-to-serious_error_flags mapping; every eligible failure remains a miss",
        },
        scoring_rows,
    )


def preflight_cost_bound(
    config: dict[str, Any], models: list[dict[str, Any]], instructions: str, task: str
) -> float:
    output_upper = int(config["cost_policy"]["preflight_max_output_tokens"])
    byte_overhead = int(
        config["cost_policy"]["preflight_input_byte_overhead_per_call"]
    )
    total = 0.0
    for model in models:
        payload = build_request_payload(
            config,
            model["model_id"],
            instructions,
            task,
            max_output_tokens=output_upper,
        )
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode(
            "utf-8"
        )
        # A token cannot encode fewer than one UTF-8 byte. The additional frozen
        # byte allowance covers provider-side message framing not present in the
        # serialized HTTP body, without loading or downloading tokenizer data.
        input_upper = len(body) + byte_overhead
        total += (
            input_upper * model["input_usd_per_million_tokens"]
            + output_upper * model["output_usd_per_million_tokens"]
        ) / 1_000_000
    return total


def write_preflight_receipt(
    config_path: Path,
    config: dict[str, Any],
    models: list[dict[str, Any]],
    outcomes: list[dict[str, Any]],
    cost_bound: float,
) -> Path:
    os.umask(0o077)
    STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
    STORAGE_ROOT.chmod(0o700)
    receipt_dir = STORAGE_ROOT / "preflight_receipts"
    receipt_dir.mkdir(parents=True, exist_ok=True)
    receipt_dir.chmod(0o700)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    nonce = sha256_bytes(os.urandom(32))[:8]
    passed = all(row["status"] == "passed" for row in outcomes)
    receipt = {
        "document_type": "rq2_private_openai_source_free_preflight_receipt",
        "status": "passed" if passed else "failed",
        "created_at_utc": utc_now(),
        "freeze_sha256": sha256_file(config_path),
        "runner_file_sha256": config["runner_file_sha256"],
        "api_endpoint": config["api_url"],
        "selected_models": [row["model_id"] for row in models],
        "model_outcomes": outcomes,
        "conservative_preflight_cost_bound_usd": cost_bound,
        "source_text_present": False,
        "source_text_transmitted": False,
        "manuscript_eligible": False,
    }
    path = receipt_dir / f"preflight_{stamp}_{nonce}.json"
    write_restricted(path, receipt)
    return path


def valid_preflight_receipt(
    config_path: Path, config: dict[str, Any], models: list[dict[str, Any]]
) -> tuple[Path, bytes, dict[str, Any]]:
    receipt_dir = STORAGE_ROOT / "preflight_receipts"
    expected_models = [row["model_id"] for row in models]
    expected_freeze = sha256_file(config_path)
    now = datetime.now(timezone.utc)
    candidates: list[tuple[datetime, Path, bytes, dict[str, Any]]] = []
    if receipt_dir.is_dir():
        for path in receipt_dir.glob("preflight_*.json"):
            try:
                receipt_bytes = path.read_bytes()
                receipt = json.loads(receipt_bytes)
                if not isinstance(receipt, dict):
                    continue
                created = datetime.fromisoformat(
                    str(receipt["created_at_utc"]).replace("Z", "+00:00")
                )
                if created.utcoffset() is None:
                    continue
                age = (now - created).total_seconds()
                outcomes = receipt.get("model_outcomes")
                if (
                    not isinstance(outcomes, list)
                    or len(outcomes) != len(expected_models)
                    or any(not isinstance(row, dict) for row in outcomes)
                    or [row.get("model_id") for row in outcomes] != expected_models
                    or any(
                        row.get("status") != "passed"
                        or row.get("returned_model") != row.get("model_id")
                        or row.get("schema_version") != "direction-j-shared-rating-v1"
                        for row in outcomes
                    )
                ):
                    continue
                cost_bound = receipt.get("conservative_preflight_cost_bound_usd")
                if (
                    receipt.get("document_type")
                    != "rq2_private_openai_source_free_preflight_receipt"
                    or receipt.get("status") != "passed"
                    or receipt.get("freeze_sha256") != expected_freeze
                    or receipt.get("runner_file_sha256")
                    != config["runner_file_sha256"]
                    or receipt.get("api_endpoint") != config["api_url"]
                    or receipt.get("selected_models") != expected_models
                    or not 0 <= age <= config["preflight_receipt_valid_for_seconds"]
                    or not isinstance(cost_bound, (int, float))
                    or isinstance(cost_bound, bool)
                    or not 0 <= cost_bound <= config["cost_policy"]["preflight_ceiling_usd"]
                    or receipt.get("source_text_present") is not False
                    or receipt.get("source_text_transmitted") is not False
                    or receipt.get("manuscript_eligible") is not False
                ):
                    continue
                candidates.append((created, path, receipt_bytes, receipt))
            except Exception:
                continue
    if not candidates:
        raise ValueError(
            "No current successful source-free preflight receipt is bound to this freeze and model set"
        )
    _, path, receipt_bytes, receipt = max(candidates, key=lambda row: row[0])
    return path, receipt_bytes, receipt


def run_preflight(
    config_path: Path,
    config: dict[str, Any],
    models: list[dict[str, Any]],
    paths: dict[str, Path],
) -> None:
    rating_schema = load_json(paths["rating_schema"])
    prompt = paths["prompt_generalist"].read_text(encoding="utf-8")
    task = (
        "No corpus or source material is present. This is a JSON transport test. Return an accept "
        "rating with all three construct scores 5, cannot_judge empty, confidence 5, requested_expertise "
        "none, serious_error_flags empty, and rationale 'No-source transport test.'"
    )
    cost_bound = preflight_cost_bound(config, models, prompt, task)
    if cost_bound > config["cost_policy"]["preflight_ceiling_usd"]:
        raise ValueError("Source-free preflight cost bound exceeds the frozen ceiling")
    outcomes = []
    for model in models:
        started = time.monotonic()
        try:
            rating, _, response = api_call(
                config,
                model["model_id"],
                prompt,
                task,
                rating_schema,
                max_output_tokens=config["cost_policy"]["preflight_max_output_tokens"],
            )
            outcomes.append(
                {
                    "model_id": model["model_id"],
                    "status": "passed",
                    "returned_model": response["execution"].get("returned_model"),
                    "elapsed_seconds": time.monotonic() - started,
                    "schema_version": rating["rating_schema_version"],
                }
            )
        except Exception as exc:
            _, _, execution, error = sanitized_failure(config, exc)
            outcomes.append(
                {
                    "model_id": model["model_id"],
                    "status": "failed",
                    "elapsed_seconds": execution.get("elapsed_seconds"),
                    "error": error,
                }
            )
    receipt = write_preflight_receipt(config_path, config, models, outcomes, cost_bound)
    print(
        json.dumps(
            {
                "status": "source_free_api_preflight",
                "models": outcomes,
                "receipt": str(receipt),
                "source_text_transmitted": False,
            },
            sort_keys=True,
        )
    )
    if any(row["status"] != "passed" for row in outcomes):
        raise SystemExit(3)


def execute_run(
    config_path: Path,
    config: dict[str, Any],
    models: list[dict[str, Any]],
    paths: dict[str, Path],
    preflight_receipt_path: Path,
    preflight_receipt_bytes: bytes,
    preflight_receipt_record: dict[str, Any],
    run_id: str | None,
) -> Path:
    os.umask(0o077)
    run_id = make_run_id(run_id)
    max_cost = estimated_max_cost(config, models, source_byte_bound=True)
    if max_cost > config["cost_policy"]["experiment_ceiling_usd"]:
        raise ValueError(f"Conservative maximum cost {max_cost:.6f} exceeds the frozen ceiling")
    preflight_receipt_sha256 = sha256_bytes(preflight_receipt_bytes)
    reservation = reserve_dispatch_budget(
        config_path,
        config,
        models,
        run_id,
        max_cost,
        preflight_receipt_sha256,
    )
    items, truth = validate_sealed_source_run(paths["source_run"], config)
    item_schema = load_json(paths["item_schema"])
    for item in items:
        jsonschema.validate(item, item_schema)
    if len(items) != config["controlled_item_count"]:
        raise ValueError("Controlled-item count differs from the freeze")

    STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
    STORAGE_ROOT.chmod(0o700)
    run_dir = STORAGE_ROOT / run_id
    secure_directory(run_dir)
    for name in ("raw", "raw/requests", "raw/responses", "observations"):
        path = run_dir / name
        path.mkdir(parents=True, exist_ok=False)
        path.chmod(0o700)
    freeze_bytes = config_path.read_bytes()
    write_restricted(run_dir / "freeze_snapshot.json", freeze_bytes, raw=True)
    write_restricted(
        run_dir / "preflight_receipt_snapshot.json",
        preflight_receipt_bytes,
        raw=True,
    )
    write_restricted(run_dir / "dispatch_budget_reservation.json", reservation)
    write_restricted(
        run_dir / "preflight_link.json",
        {
            "preflight_receipt": preflight_receipt_path.name,
            "preflight_receipt_snapshot": "preflight_receipt_snapshot.json",
            "preflight_receipt_sha256": preflight_receipt_sha256,
            "preflight_receipt_created_at_utc": preflight_receipt_record[
                "created_at_utc"
            ],
            "source_text_present": False,
        },
    )
    write_restricted(
        run_dir / "sealed_input_link.json",
        {
            "source_run_id": paths["source_run"].name,
            "source_output_seal_sha256": config["source_output_seal_sha256"],
            "source_truth_map_sha256": config["source_truth_map_sha256"],
            "item_payloads": [
                {"item_id": item["item_id"], "item_payload_sha256": sha256_bytes(canonical_json(item))}
                for item in items
            ],
            "source_text_present_in_this_link_record": False,
            "source_text_present_in_linked_items_and_api_requests": True,
            "status": STATUS,
        },
    )

    guide = paths["guide"].read_text(encoding="utf-8")
    rating_schema = load_json(paths["rating_schema"])
    model_map = {row["model_id"]: row for row in models}
    calls = [
        (model["model_id"], role, item)
        for model in models
        for role in ROLE_IDS
        for item in items
    ]
    random.Random(config["execution_order_seed"]).shuffle(calls)
    stop_event = threading.Event()

    def worker(model_id: str, role: str, item: dict[str, Any]) -> dict[str, Any]:
        prompt = paths[f"prompt_{role}"].read_text(encoding="utf-8")
        artifact_stem = f"review_{model_slug(model_id)}_{item['item_id']}_{role}"
        request_path = run_dir / "raw" / "requests" / f"{artifact_stem}.json"
        response_path = run_dir / "raw" / "responses" / f"{artifact_stem}.json"
        response_headers_path = (
            run_dir / "raw" / "responses" / f"{artifact_stem}.headers.json"
        )
        try:
            if stop_event.is_set():
                raise RuntimeError("Dispatch canceled before request construction")
            rating, request, response = api_call(
                config,
                model_id,
                prompt,
                reviewer_user_prompt(guide, item),
                rating_schema,
                request_artifact_path=request_path,
                response_artifact_path=response_path,
                response_headers_artifact_path=response_headers_path,
            )
            return {
                "model_id": model_id,
                "role": role,
                "item": item,
                "status": "valid",
                "rating": rating,
                "request_path": request_path,
                "response_path": response_path,
                "response_headers_path": response_headers_path,
                "execution": response["execution"],
                "error": None,
            }
        except Exception as exc:
            request, raw, execution, error = sanitized_failure(config, exc)
            if request.get("model") is None:
                request["model"] = model_id
            if not request_path.exists():
                write_restricted(request_path, request)
            if not response_path.exists():
                write_restricted(response_path, raw)
            if not response_headers_path.exists():
                write_restricted(response_headers_path, {})
            return {
                "model_id": model_id,
                "role": role,
                "item": item,
                "status": "terminal_error",
                "rating": None,
                "request_path": request_path,
                "response_path": response_path,
                "response_headers_path": response_headers_path,
                "execution": execution,
                "error": error,
            }

    observations: list[dict[str, Any]] = []
    completed = 0
    total = len(calls)
    pool: ThreadPoolExecutor | None = None
    futures: dict[Future[dict[str, Any]], tuple[str, str, str]] = {}
    try:
        pool = ThreadPoolExecutor(max_workers=int(config["max_concurrent_requests"]))
        futures = {
            pool.submit(worker, model_id, role, item): (model_id, role, item["item_id"])
            for model_id, role, item in calls
        }
        for future in as_completed(futures):
            record = future.result()
            completed += 1
            http_status = record["execution"].get("http_status")
            error_stage = (record.get("error") or {}).get("stage")
            returned_model = record["execution"].get("returned_model")
            if (
                error_stage == "pre_dispatch_or_internal"
                or isinstance(http_status, int)
                and 400 <= http_status < 500
                or returned_model is not None
                and returned_model != record["model_id"]
            ):
                raise RuntimeError(
                    "Experiment-wide abort after setup, access, or model-identity failure"
                )
            print(
                f"RQ2 GPT exploratory review {completed}/{total}: {record['model_id']} {record['role']} {record['status']}",
                flush=True,
            )
            model_id = record["model_id"]
            role = record["role"]
            item = record["item"]
            request_path = record["request_path"]
            response_path = record["response_path"]
            response_headers_path = record["response_headers_path"]
            prompt_hash = config["prompt_sha256"][role]
            item_hash = sha256_bytes(canonical_json(item))
            execution = record["execution"]
            observation = {
                    "observation_id": "OBS_" + sha256_bytes(
                        canonical_json([run_id, model_id, role, item["item_id"], 1])
                    )[:20],
                    "run_id": run_id,
                    "source_run_id": config["source_run_id"],
                    "item_id": item["item_id"],
                    "model_id": model_id,
                    "returned_model": execution.get("returned_model"),
                    "analysis_class": model_map[model_id]["analysis_class"],
                    "actor_id": config["model_role_actor_ids"][model_id][role],
                    "actor_kind": "openai_responses_role_prompted_proxy",
                    "prompted_role": role,
                    "rating_repetition": 1,
                    "status": record["status"],
                    "item_payload_sha256": item_hash,
                    "prompt_sha256": prompt_hash,
                    "semantic_input_sha256": sha256_bytes(
                        canonical_json(
                            {
                                "item_payload_sha256": item_hash,
                                "shared_rater_guide_sha256": config["shared_rater_guide_sha256"],
                                "prompt_sha256": prompt_hash,
                                "requested_model": model_id,
                                "input_transport_prefix_sha256": sha256_bytes(
                                    config["input_transport_prefix"].encode("utf-8")
                                ),
                            }
                        )
                    ),
                    "request_artifact_sha256": sha256_file(request_path),
                    "response_artifact_sha256": sha256_file(response_path),
                    "response_headers_artifact_sha256": sha256_file(response_headers_path),
                    "execution": execution,
                    "estimated_cost_usd": actual_cost(model_map[model_id], execution),
                    "rating": record["rating"],
                    "error": record["error"],
                    "status_label": STATUS,
            }
            observations.append(observation)
            write_restricted(
                run_dir / "observations" / f"{observation['observation_id']}.json", observation
            )
    except BaseException as exc:
        stop_event.set()
        for pending in futures:
            pending.cancel()
        if pool is not None:
            pool.shutdown(wait=True, cancel_futures=True)
        marker = run_dir / "FAILED_UNSEALED.json"
        if not marker.exists():
            write_restricted(
                marker,
                {
                    "document_type": "rq2_private_openai_failed_unsealed_marker",
                    "run_id": run_id,
                    "status": STATUS,
                    "failed_at_utc": utc_now(),
                    "failure_type": type(exc).__name__,
                    "completed_observation_count": len(observations),
                    "manuscript_eligible": False,
                },
            )
        raise
    else:
        if pool is not None:
            pool.shutdown(wait=True)

    observations.sort(key=lambda row: (row["model_id"], row["prompted_role"], row["item_id"]))
    selected_model_ids = [row["model_id"] for row in models]
    results, scoring_rows = score(
        observations, truth, config, selected_model_ids
    )
    results["run_id"] = run_id
    results["selected_models"] = [row["model_id"] for row in models]
    known_costs = [
        row["estimated_cost_usd"]
        for row in observations
        if row["estimated_cost_usd"] is not None
    ]
    results["estimated_known_cost_usd"] = sum(known_costs)
    results["unknown_cost_call_count"] = sum(
        row["estimated_cost_usd"] is None for row in observations
    )
    results["default_abuse_monitoring_retention_may_be_up_to_days"] = 30
    results["zero_data_retention_verified"] = False
    write_restricted(run_dir / "results.exploratory.json", results)

    scoring_rows.sort(key=lambda row: (row["model_id"], row["role"], row["item_id"]))
    csv_path = run_dir / "scoring.exploratory.csv"
    with csv_path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(scoring_rows[0]))
        writer.writeheader()
        writer.writerows(scoring_rows)
    csv_path.chmod(0o600)

    manifest = {
        "document_type": "rq2_private_openai_exploratory_run_manifest",
        "run_id": run_id,
        "status": STATUS,
        "completed_at_utc": utc_now(),
        "freeze_sha256": sha256_bytes(freeze_bytes),
        "runner_file_sha256": config["runner_file_sha256"],
        "python_version": config["python_version"],
        "jsonschema_version": config["jsonschema_version"],
        "requested_models": [row["model_id"] for row in models],
        "preflight_receipt_sha256": preflight_receipt_sha256,
        "dispatch_execution_signature": reservation["execution_signature"],
        "dispatch_reserved_max_cost_usd": reservation["reserved_max_cost_usd"],
        "dispatch_reserved_total_after_usd": reservation[
            "reserved_total_after_usd"
        ],
        "observation_count": len(observations),
        "valid_observation_count": sum(row["status"] == "valid" for row in observations),
        "conservative_pre_dispatch_max_cost_usd": max_cost,
        "estimated_known_cost_usd": results["estimated_known_cost_usd"],
        "unknown_cost_call_count": results["unknown_cost_call_count"],
        "source_text_present_only_in_linked_restricted_items_and_raw_request_artifacts": True,
        "source_text_transmitted_to_openai": True,
        "api_endpoint": config["api_url"],
        "store": False,
        "tools_present": False,
        "automatic_retries": 0,
        "zero_data_retention_verified": False,
        "manuscript_eligible": False,
    }
    write_restricted(run_dir / "run_manifest.json", manifest)

    seal_entries = []
    for path in sorted(run_dir.rglob("*")):
        if path.is_file() and path.name != "output_seal.json":
            seal_entries.append(
                {
                    "path": path.relative_to(run_dir).as_posix(),
                    "sha256": sha256_file(path),
                    "size_bytes": path.stat().st_size,
                }
            )
    write_restricted(
        run_dir / "output_seal.json",
        {
            "document_type": "rq2_private_openai_exploratory_output_seal",
            "run_id": run_id,
            "status": STATUS,
            "sealed_at_utc": utc_now(),
            "files": seal_entries,
            "seal_payload_sha256": sha256_bytes(canonical_json(seal_entries)),
            "manuscript_eligible": False,
        },
    )
    return run_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run private exploratory GPT-5.6 RQ2 reviews.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--run-id")
    parser.add_argument("--model", action="append", choices=MODEL_IDS, dest="models")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate frozen non-source files and cost bounds; make no API call and open no item text.",
    )
    parser.add_argument(
        "--preflight-api",
        action="store_true",
        help="Make one source-free JSON transport call per selected model.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute source-bearing reviews only after a current successful preflight receipt exists.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    selected_modes = sum(bool(value) for value in (args.dry_run, args.preflight_api, args.execute))
    if selected_modes != 1:
        raise ValueError("Choose exactly one of --dry-run, --preflight-api, or --execute")
    if args.preflight_api or args.execute:
        raise ValueError(
            "OpenAI preflight and execution are inactive and forbidden by the active "
            "personal-local-only policy"
        )
    config_path = args.config.resolve()
    config = load_json(config_path)
    paths = validate_freeze(config, config_path, include_source_files=False)
    models = selected_models(config, args.models)
    if args.dry_run:
        bound = estimated_max_cost(config, models, source_byte_bound=True)
        if bound > config["cost_policy"]["experiment_ceiling_usd"]:
            raise ValueError("Frozen conservative cost bound exceeds the ceiling")
        print(
            json.dumps(
                {
                    "status": "dry_run_passed_without_source_or_api_access",
                    "selected_models": [row["model_id"] for row in models],
                    "conservative_max_cost_usd": round(bound, 6),
                    "source_text_printed": False,
                },
                sort_keys=True,
            )
        )
        return 0
    if args.preflight_api:
        run_preflight(config_path, config, models, paths)
        return 0
    if not os.environ.get("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY must be set before any source file is opened")
    (
        preflight_receipt_path,
        preflight_receipt_bytes,
        preflight_receipt_record,
    ) = valid_preflight_receipt(config_path, config, models)
    paths = validate_freeze(config, config_path, include_source_files=True)
    run_dir = execute_run(
        config_path,
        config,
        models,
        paths,
        preflight_receipt_path,
        preflight_receipt_bytes,
        preflight_receipt_record,
        args.run_id,
    )
    print(
        json.dumps(
            {
                "status": STATUS,
                "run_directory": str(run_dir),
                "source_text_printed": False,
                "source_text_transmitted_to_openai": True,
                "manuscript_eligible": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("Interrupted; any partial run remains unsealed and diagnostic-only.", file=sys.stderr)
        raise SystemExit(130)
