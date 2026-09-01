#!/usr/bin/env python3
"""Run one private real-data WarrantRoute packet with hardened local prompts."""

from __future__ import annotations

import argparse
import collections
import hashlib
import importlib.metadata
import importlib.util
import json
import os
import platform
import re
import stat
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

try:
    import jsonschema
except Exception:
    print(
        json.dumps(
            {
                "v24_status": "stopped",
                "failure_code": "v24_jsonschema_import_failed",
                "contains_source_text": False,
                "result_label": "private_personal_exploratory_not_for_publication",
                "evidence_status": "diagnostic_not_manuscript_evidence",
                "manuscript_eligible": False,
                "publication_or_release_eligible": False,
            },
            sort_keys=True,
        ),
        file=sys.stderr,
    )
    raise SystemExit(2) from None


SCRIPT = Path(__file__).resolve()
RQ2_ROOT = SCRIPT.parents[1]
WORKSPACE = RQ2_ROOT.parents[1]
V23_RUNNER = SCRIPT.with_name("run_personal_local_main_v23.py")
V23_RUNNER_SHA256 = "7506274237e225f94fbd2f8f8ec07a73fef8626f52ff0775550a6b76a9ce7b07"
V23_CONFIG = RQ2_ROOT / "config" / "personal_local_main_v23_freeze.json"
V23_CONFIG_SHA256 = "89c9a4bacaac829b7def06a0d588af86a0cb68ea8b81d3cec113e3ded5ad5339"
DEFAULT_CONFIG = RQ2_ROOT / "config" / "personal_local_real_smoke_v24_freeze.json"
OUTPUT_ROOT = (
    WORKSPACE
    / "Storage"
    / "rq2_personal_local_diagnostic"
    / "v24_one_packet_smoke_runs"
)
RUN_ID_RE = re.compile(r"rq2plv24_[0-9]{8}T[0-9]{6}Z_[0-9a-f]{8}")

STATUS = "private_personal_exploratory_not_for_publication"
EVIDENCE_STATUS = "diagnostic_not_manuscript_evidence"
VERIFICATION_LABEL = "frozen_local_model_screened_not_human_ground_truth"
GENERATION_REASON_CODES = {
    "insufficient_independent_support",
    "no_genuine_counterevidence",
    "no_context_only_candidate",
    "cannot_form_packet_bounded_claim",
    "ambiguous_evidence_roles",
    "outside_inference_would_be_required",
}


def raw_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_bound_module(path: Path, digest: str, name: str) -> Any:
    if raw_sha256(path) != digest:
        raise SystemExit(f"v24_{name}_hash_drift")
    spec = importlib.util.spec_from_file_location(f"rq2_v24_{name}", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"v24_{name}_import_spec_invalid")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


try:
    v23 = load_bound_module(V23_RUNNER, V23_RUNNER_SHA256, "v23")
    v22 = v23.v22
    v1 = v23.v1
    core = v22.core
    guard = v23.guard
except BaseException:
    print(
        json.dumps(
            {
                "v24_status": "stopped",
                "failure_code": "v24_predecessor_startup_validation_failed",
                "contains_source_text": False,
                "result_label": "private_personal_exploratory_not_for_publication",
                "evidence_status": "diagnostic_not_manuscript_evidence",
                "manuscript_eligible": False,
                "publication_or_release_eligible": False,
            },
            sort_keys=True,
        ),
        file=sys.stderr,
    )
    raise SystemExit(2) from None


class V24Error(RuntimeError):
    """A finite error that never includes source text."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise V24Error(code)


EXPECTED_CONFIG = {
    "document_type": "rq2_personal_local_real_smoke_v24_freeze",
    "freeze_version": "rq2-personal-local-real-smoke-v2.4",
    "status": STATUS,
    "evidence_status": EVIDENCE_STATUS,
    "execution_scope": "one_packet_dreaddit_development_smoke_only",
    "source_bearing_run_allowed": True,
    "manuscript_use_allowed": False,
    "publication_or_release_allowed": False,
    "human_review_allowed": False,
    "source_or_excerpt_export_allowed": False,
    "output_root": (
        "Storage/rq2_personal_local_diagnostic/v24_one_packet_smoke_runs"
    ),
    "run_id_prefix": "rq2plv24_",
    "predecessor_v23_runner_file": (
        "experiments/rq2_role_prompted_llm/scripts/run_personal_local_main_v23.py"
    ),
    "predecessor_v23_runner_sha256": V23_RUNNER_SHA256,
    "predecessor_v23_config_file": (
        "experiments/rq2_role_prompted_llm/config/personal_local_main_v23_freeze.json"
    ),
    "predecessor_v23_config_sha256": V23_CONFIG_SHA256,
    "protocol_file": (
        "experiments/rq2_role_prompted_llm/protocol/"
        "personal_local_real_smoke_contract_v1.md"
    ),
    "protocol_sha256": (
        "39c3ee0bd816c5de0eae541a60140a9db759febc0ec50a7f2dca9e1879b15ee1"
    ),
    "runner_file": (
        "experiments/rq2_role_prompted_llm/scripts/"
        "run_personal_local_real_smoke_v24.py"
    ),
    "runner_sha256": None,
    "input": {
        "lane": "dreaddit_development",
        "corpus": "dreaddit",
        "split": "development_train",
        "records_file": "dataset/deidentified/dreaddit/records.jsonl",
        "records_file_sha256": (
            "86ba43a89d9ef52f5377d35c12d26690b820f24ce11bc6540eeae57605654d3a"
        ),
        "packet_count": 1,
        "excerpts_per_packet": 6,
        "excluded_predecessor_cluster_commitments": 90,
        "reserved_v22_qualification_packet_count": 10,
        "smoke_selection_rank": 11,
    },
    "process": {
        "source_free_canary_required_before_source_access": True,
        "real_model_calls_maximum": 2,
        "generator_model_role": "generator",
        "verifier_model_role": "verifier",
        "semantic_retries_allowed": False,
        "transport_retries_allowed": False,
        "replacement_packet_allowed": False,
        "real_packet_chunking_allowed": False,
    },
    "prompt_limit_policy": {
        "request_num_ctx": 16384,
        "minimum_native_context": 16384,
        "safety_margin_tokens": 512,
        "truncate": False,
        "shift": False,
        "input_overflow_action": "terminal_before_generation",
        "insufficient_output_headroom_action": "terminal_reject_without_retry",
        "atomic_semantic_unit": "complete_six_excerpt_packet",
    },
}


def resolve_workspace_file(relative: str) -> Path:
    require(isinstance(relative, str) and bool(relative), "v24_bound_path_invalid")
    path = (WORKSPACE / relative).absolute()
    try:
        path.relative_to(WORKSPACE)
    except ValueError:
        raise V24Error("v24_bound_path_escape") from None
    require(path.is_file() and not path.is_symlink(), "v24_bound_file_missing")
    v1.reject_symlink_components(path, anchor=WORKSPACE)
    return path


def validate_v24_freeze(
    config: dict[str, Any], *, config_path: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Validate only source-free files; do not open records or prior selections."""

    require(config_path == DEFAULT_CONFIG, "only_exact_v24_freeze_allowed")
    require(
        v22.strict_equal_v22(config, v1.load_json(config_path)),
        "v24_config_object_file_drift",
    )
    require(set(config) == set(EXPECTED_CONFIG), "v24_freeze_fields_mismatch")
    for key, expected in EXPECTED_CONFIG.items():
        if key == "runner_sha256":
            continue
        require(
            v22.strict_equal_v22(config.get(key), expected),
            f"v24_freeze_value_mismatch:{key}",
        )
    require(
        isinstance(config.get("runner_sha256"), str)
        and re.fullmatch(r"[0-9a-f]{64}", config["runner_sha256"]) is not None,
        "v24_runner_hash_invalid",
    )

    require(raw_sha256(V23_RUNNER) == V23_RUNNER_SHA256, "v24_v23_runner_hash_drift")
    require(raw_sha256(V23_CONFIG) == V23_CONFIG_SHA256, "v24_v23_config_hash_drift")
    protocol_path = resolve_workspace_file(config["protocol_file"])
    runner_path = resolve_workspace_file(config["runner_file"])
    require(raw_sha256(protocol_path) == config["protocol_sha256"], "v24_protocol_hash_drift")
    require(raw_sha256(runner_path) == config["runner_sha256"], "v24_runner_hash_drift")

    predecessor = v1.load_json(V23_CONFIG)
    v1_config, assets = v23.validate_v23_freeze(
        predecessor, config_path=V23_CONFIG
    )
    lane = v1_config["lanes"][config["input"]["lane"]]
    require(
        lane["corpus"] == config["input"]["corpus"]
        and lane["split"] == config["input"]["split"]
        and lane["records_file"] == config["input"]["records_file"]
        and lane["records_file_sha256"] == config["input"]["records_file_sha256"],
        "v24_input_binding_drift",
    )
    require(v1_config["excerpts_per_packet"] == 6, "v24_excerpt_count_drift")
    return v1_config, assets


def ensure_v24_path(path: Path) -> None:
    lexical = path.absolute()
    require(
        lexical == OUTPUT_ROOT or OUTPUT_ROOT in lexical.parents,
        "v24_output_path_escape",
    )
    v1.guard_output_path(lexical)


def ensure_private_directory(path: Path) -> None:
    ensure_v24_path(path)
    v1.ensure_private_directory(path)


def write_private_json(path: Path, value: Any) -> None:
    ensure_v24_path(path)
    v1.write_json_once(path, value)


def write_private_bytes(path: Path, value: bytes) -> None:
    ensure_v24_path(path)
    v1.write_bytes_once(path, value)


def build_run_id(requested: str | None) -> str:
    if requested is None:
        requested = (
            "rq2plv24_"
            + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            + "_"
            + v1.sha256_bytes(os.urandom(32))[:8]
        )
    require(RUN_ID_RE.fullmatch(requested) is not None, "v24_run_id_invalid")
    return requested


def model_native_context(
    v1_config: dict[str, Any], *, model_role: str, minimum: int
) -> dict[str, Any]:
    model_id = v1_config["models"][model_role]["model_id"]
    show = v1.api_json(
        v1_config["service_url"], "/api/show", {"model": model_id}, timeout=20
    )
    info = show.get("model_info")
    require(isinstance(info, dict), f"v24_{model_role}_model_info_missing")
    candidates = {
        key: value
        for key, value in info.items()
        if isinstance(key, str)
        and key.endswith(".context_length")
        and type(value) is int
    }
    require(
        len(candidates) == 1,
        f"v24_{model_role}_native_context_metadata_ambiguous",
    )
    key, value = next(iter(candidates.items()))
    require(value >= minimum, f"v24_{model_role}_native_context_insufficient")
    return {
        "model_role": model_role,
        "model_id": model_id,
        "metadata_key": key,
        "native_context_length": value,
    }


def preflight_required_service(v1_config: dict[str, Any]) -> dict[str, Any]:
    """Validate Ollama and only the two model roles used by this smoke run."""

    endpoint = v1_config["service_url"]
    version = v1.api_json(endpoint, "/api/version", timeout=20)
    require(
        version.get("version") == v1_config["ollama_version"],
        "v24_ollama_version_drift",
    )
    tags = v1.api_json(endpoint, "/api/tags", timeout=20)
    available = tags.get("models")
    require(isinstance(available, list), "v24_ollama_tags_invalid")
    result: dict[str, Any] = {
        "ollama_version": version["version"],
        "endpoint": endpoint,
        "endpoint_is_numeric_loopback": True,
        "models": {},
    }
    for role in ("generator", "verifier"):
        frozen = v1_config["models"][role]
        exact = [
            row
            for row in available
            if isinstance(row, dict) and row.get("name") == frozen["model_id"]
        ]
        require(len(exact) == 1, f"v24_model_not_uniquely_available:{role}")
        returned = exact[0]
        digest = str(returned.get("digest", "")).removeprefix("sha256:")
        require(
            digest == frozen["local_manifest_file_sha256"],
            f"v24_model_tag_digest_drift:{role}",
        )
        result["models"][role] = {
            "model_id": frozen["model_id"],
            "digest": returned.get("digest"),
            "size": returned.get("size"),
        }
    return result


def recheck_required_service(
    v1_config: dict[str, Any], baseline: dict[str, Any]
) -> None:
    require(
        preflight_required_service(v1_config) == baseline,
        "v24_model_service_identity_changed",
    )


def select_smoke_packet(
    v1_config: dict[str, Any],
    records: Sequence[dict[str, Any]],
    *,
    excluded_commitments: set[str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Select rank 11 so the smoke packet is outside v2.2's ten packets."""

    require(len(excluded_commitments) == 90, "v24_exclusion_denominator_invalid")
    lane_name = "dreaddit_development"
    lane = v1_config["lanes"][lane_name]
    filtered = [
        row
        for row in records
        if core.cluster_commitment(row, lane["corpus"])
        not in excluded_commitments
    ]
    ranked = v1.deterministic_packet_plan(
        filtered,
        lane_name=lane_name,
        lane=lane,
        seed=int(v1_config["sampling_seed"]),
        packet_count=11,
        excerpts_per_packet=6,
    )
    qualification_commitments = {
        value
        for packet in ranked[:10]
        for value in packet["selection_cluster_commitments"]
    }
    packet = ranked[10]
    smoke_commitments = set(packet["selection_cluster_commitments"])
    require(
        len(qualification_commitments) == 60
        and len(smoke_commitments) == 6
        and smoke_commitments.isdisjoint(qualification_commitments)
        and smoke_commitments.isdisjoint(excluded_commitments),
        "v24_smoke_selection_not_disjoint",
    )
    selection = v1.source_free_selection_record(packet)
    selection.update(
        {
            "document_type": "rq2_personal_local_v24_smoke_selection",
            "lane": lane_name,
            "corpus": lane["corpus"],
            "split": lane["split"],
            "smoke_packet_count": 1,
            "excerpts_per_packet": 6,
            "selection_rank_after_predecessor_exclusions": 11,
            "excluded_predecessor_cluster_commitment_count": 90,
            "reserved_v22_qualification_cluster_commitment_count": 60,
            "overlaps_reserved_v22_qualification_packets": False,
            "contains_source_text": False,
            "result_label": STATUS,
            "evidence_status": EVIDENCE_STATUS,
            "manuscript_eligible": False,
            "publication_or_release_eligible": False,
        }
    )
    return packet, selection


def initialize_run(
    config: dict[str, Any],
    config_path: Path,
    v1_config: dict[str, Any],
    v1_paths: dict[str, Path],
    *,
    run_id: str,
    service: dict[str, Any],
    native_contexts: list[dict[str, Any]],
    canary: dict[str, Any],
    policy_evidence: dict[str, Any],
) -> Path:
    os.umask(0o077)
    ensure_private_directory(OUTPUT_ROOT)
    run_dir = OUTPUT_ROOT / run_id
    require(not v1.safe_exists(run_dir), "v24_run_id_already_exists")
    ensure_private_directory(run_dir)
    for relative in ("raw/calls", "selection", "private", "analysis"):
        ensure_private_directory(run_dir / relative)
    write_private_bytes(run_dir / "freeze_snapshot.json", config_path.read_bytes())
    write_private_bytes(run_dir / "policy_snapshot.json", v1_paths["policy"].read_bytes())
    contract = {
        "document_type": "rq2_personal_local_v24_smoke_run_contract",
        "run_id": run_id,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "freeze_sha256": raw_sha256(config_path),
        "runner_sha256": raw_sha256(SCRIPT),
        "protocol_sha256": config["protocol_sha256"],
        "policy_sha256": v1_config["policy_file_sha256"],
        "python_version": platform.python_version(),
        "jsonschema_version": importlib.metadata.version("jsonschema"),
        "service": service,
        "native_contexts": native_contexts,
        "source_free_canary": canary,
        "policy_evidence": policy_evidence,
        "real_packet_count": 1,
        "real_excerpt_count": 6,
        "maximum_real_model_calls": 2,
        "real_packet_chunking_allowed": False,
        "transport_retries_allowed": False,
        "semantic_retries_allowed": False,
        "runner_retained_source_text_location": (
            "private_request_response_and_item_artifacts_only"
        ),
        "source_bearing_transport": "numeric_loopback_ollama_only",
        "service_logging_attested_by_runner": False,
        "this_manifest_contains_source_text": False,
        "sealed_run_contains_restricted_source_text": True,
        "result_label": STATUS,
        "evidence_status": EVIDENCE_STATUS,
        "manuscript_eligible": False,
        "publication_or_release_eligible": False,
    }
    write_private_json(run_dir / "run_contract.json", contract)
    return run_dir


def invoke_hardened_call(
    v1_config: dict[str, Any],
    run_dir: Path,
    *,
    call_id: str,
    model_role: str,
    system_prompt: str,
    user_prompt: str,
    output_schema: dict[str, Any],
    num_ctx: int,
    safety_margin_tokens: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Make exactly one private call; never split, retry, or print content."""

    require(
        re.fullmatch(r"[A-Za-z0-9_]+", call_id) is not None,
        "v24_call_id_invalid",
    )
    base_request = v1.build_model_request(
        v1_config,
        model_role=model_role,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        output_schema=output_schema,
        rating_call=False,
        rating_repetition=None,
    )
    request = guard.harden_ollama_request(base_request, num_ctx=num_ctx)
    require(
        request.get("truncate") is False
        and request.get("shift") is False
        and request["options"].get("num_ctx") == num_ctx,
        "v24_hardened_request_invalid",
    )
    reserved = int(request["options"]["num_predict"])
    call_dir = run_dir / "raw" / "calls" / call_id
    ensure_private_directory(call_dir)
    request_path = call_dir / "request.private.json"
    response_path = call_dir / "response.private.json"
    write_private_json(request_path, request)
    call_contract = {
        "document_type": "rq2_personal_local_v24_smoke_call_contract",
        "call_id": call_id,
        "model_role": model_role,
        "model_id": request["model"],
        "request_sha256": v1.sha256_file(request_path),
        "system_prompt_sha256": v1.sha256_bytes(system_prompt.encode("utf-8")),
        "system_prompt_bytes": len(system_prompt.encode("utf-8")),
        "user_prompt_sha256": v1.sha256_bytes(user_prompt.encode("utf-8")),
        "user_prompt_bytes": len(user_prompt.encode("utf-8")),
        "output_schema_sha256": v1.sha256_bytes(v1.canonical_bytes(output_schema)),
        "num_ctx": num_ctx,
        "reserved_output_tokens": reserved,
        "safety_margin_tokens": safety_margin_tokens,
        "truncate": False,
        "shift": False,
        "attempt_count": 1,
        "contains_source_text": False,
        "result_label": STATUS,
        "evidence_status": EVIDENCE_STATUS,
        "manuscript_eligible": False,
        "publication_or_release_eligible": False,
    }
    write_private_json(call_dir / "call_contract.json", call_contract)

    started = time.monotonic()
    try:
        response = v1.api_json(
            v1_config["service_url"], "/api/chat", request, timeout=600
        )
    except Exception as exc:
        pre_generation_overflow = guard.is_ollama_context_overflow(exc)
        code = (
            "v24_atomic_packet_context_overflow"
            if pre_generation_overflow
            else "v24_local_transport_failed"
        )
        write_private_json(
            call_dir / "terminal_error.json",
            {
                "document_type": "rq2_personal_local_v24_smoke_call_error",
                "call_id": call_id,
                "failure_code": code,
                "generated_response_status": (
                    "none_pre_generation"
                    if pre_generation_overflow
                    else "unknown_transport_failure"
                ),
                "pre_generation_rejection": pre_generation_overflow,
                "retry_allowed": False,
                "contains_source_text": False,
                "result_label": STATUS,
                "evidence_status": EVIDENCE_STATUS,
                "manuscript_eligible": False,
                "publication_or_release_eligible": False,
            },
        )
        raise V24Error(code) from None

    elapsed = time.monotonic() - started
    write_private_json(response_path, response)
    try:
        accounting = guard.validate_successful_context_use(
            response,
            num_ctx=num_ctx,
            reserved_output_tokens=reserved,
            safety_margin_tokens=safety_margin_tokens,
        )
        output, execution = v1.parse_model_response(
            response,
            expected_model=v1_config["models"][model_role]["model_id"],
            output_schema=output_schema,
        )
        require(
            execution.get("done_reason") == "stop",
            "v24_model_done_reason_invalid",
        )
    except Exception:
        write_private_json(
            call_dir / "terminal_error.json",
            {
                "document_type": "rq2_personal_local_v24_smoke_call_error",
                "call_id": call_id,
                "failure_code": "v24_model_response_validation_failed",
                "generated_response_exists": True,
                "retry_allowed": False,
                "contains_source_text": False,
                "result_label": STATUS,
                "evidence_status": EVIDENCE_STATUS,
                "manuscript_eligible": False,
                "publication_or_release_eligible": False,
            },
        )
        raise V24Error("v24_model_response_validation_failed") from None

    summary = {
        "call_id": call_id,
        "model_role": model_role,
        "model_id": request["model"],
        "request_sha256": v1.sha256_file(request_path),
        "response_sha256": v1.sha256_file(response_path),
        "user_prompt_sha256": call_contract["user_prompt_sha256"],
        "user_prompt_bytes": call_contract["user_prompt_bytes"],
        "prompt_eval_count": accounting["prompt_eval_count"],
        "eval_count": accounting["eval_count"],
        "num_ctx": num_ctx,
        "reserved_output_tokens": reserved,
        "safety_margin_tokens": safety_margin_tokens,
        "elapsed_seconds": round(elapsed, 6),
        "done_reason": execution["done_reason"],
        "truncate": False,
        "shift": False,
        "attempt_count": 1,
        "schema_valid": True,
        "contains_source_text": False,
        "result_label": STATUS,
        "evidence_status": EVIDENCE_STATUS,
        "manuscript_eligible": False,
        "publication_or_release_eligible": False,
    }
    write_private_json(call_dir / "success_summary.json", summary)
    return output, summary


def role_counts(metadata: dict[str, Any]) -> dict[str, int]:
    counts = collections.Counter(metadata["role_by_position"].values())
    return {
        "support": counts.get("support", 0),
        "counterevidence": counts.get("counterevidence", 0),
        "context_only": counts.get("context_only", 0),
    }


def validate_generation_cross_fields(generated: dict[str, Any]) -> None:
    """Enforce the v2.1 prompt's status conventions beyond JSON Schema."""

    require(
        generated.get("generation_schema_version")
        == "rq2-base-generation-v2.1",
        "v24_generation_version_invalid",
    )
    role_plan = generated.get("role_plan")
    require(
        isinstance(role_plan, list)
        and [row.get("position") for row in role_plan if isinstance(row, dict)]
        == [1, 2, 3, 4, 5, 6],
        "v24_generation_position_sequence_invalid",
    )
    reasons = generated.get("reason_codes")
    require(
        isinstance(reasons, list)
        and len(reasons) == len(set(reasons))
        and set(reasons) <= GENERATION_REASON_CODES,
        "v24_generation_reason_codes_invalid",
    )
    prose = [generated.get(key) for key in ("theme_name", "claim", "explanation")]
    status = generated.get("status")
    if status == "constructed":
        require(
            generated.get("claim_scope") == "displayed_packet_only",
            "v24_constructed_claim_scope_invalid",
        )
        require(
            all(
                isinstance(value, str)
                and bool(value.strip())
                and value != "NOT_CONSTRUCTED"
                for value in prose
            ),
            "v24_constructed_prose_invalid",
        )
        require(
            all(
                isinstance(row, dict)
                and row.get("role")
                in {"support", "counterevidence", "context_only"}
                for row in role_plan
            ),
            "v24_constructed_role_status_invalid",
        )
        require(reasons == [], "v24_constructed_reason_codes_nonempty")
        return
    require(status == "not_constructable", "v24_generation_status_invalid")
    require(
        prose == ["NOT_CONSTRUCTED", "NOT_CONSTRUCTED", "NOT_CONSTRUCTED"],
        "v24_not_constructable_sentinel_invalid",
    )
    require(
        generated.get("claim_scope") == "not_constructed",
        "v24_not_constructable_claim_scope_invalid",
    )
    require(
        all(
            isinstance(row, dict) and row.get("role") == "unassigned"
            for row in role_plan
        ),
        "v24_not_constructable_roles_invalid",
    )
    require(
        generated.get("boundary_conditions") == [],
        "v24_not_constructable_boundaries_invalid",
    )
    require(bool(reasons), "v24_not_constructable_reasons_missing")


def base_report(
    run_dir: Path,
    *,
    selection: dict[str, Any],
    canary: dict[str, Any],
    policy_evidence: dict[str, Any],
) -> dict[str, Any]:
    return {
        "document_type": "rq2_personal_local_v24_smoke_sanitized_report",
        "run_id": run_dir.name,
        "result_label": STATUS,
        "evidence_status": EVIDENCE_STATUS,
        "input": {
            "dataset": "dreaddit",
            "split": "development_train",
            "packet_count": 1,
            "excerpt_count": 6,
            "selection_rank_after_predecessor_exclusions": 11,
            "record_file_sha256": (
                "86ba43a89d9ef52f5377d35c12d26690b820f24ce11bc6540eeae57605654d3a"
            ),
            "record_id_commitment": selection["record_id_commitment"],
            "selection_cluster_commitments": selection[
                "selection_cluster_commitments"
            ],
            "overlaps_reserved_v22_qualification_packets": False,
            "source_text_emitted": False,
        },
        "process": {
            "policy_validation": policy_evidence,
            "source_free_canary": {
                "status": canary["status"],
                "logical_fixture_count": canary["logical_fixture_count"],
                "physical_attempt_count": canary["generated_physical_attempts"],
                "automatic_chunking_used": canary["automatic_chunking_used"],
                "prompt_eval_count_min": canary["prompt_eval_count_min"],
                "prompt_eval_count_max": canary["prompt_eval_count_max"],
            },
            "selection": "one_intact_six_excerpt_packet",
            "real_packet_chunking": "not_used_atomic_packet",
            "real_calls": [],
        },
        "output": {},
        "operational_status": "running",
        "contains_source_text": False,
        "raw_source_bearing_artifacts_private": True,
        "human_ground_truth": False,
        "manuscript_eligible": False,
        "publication_or_release_eligible": False,
    }


def write_report_and_seal(run_dir: Path, report: dict[str, Any]) -> None:
    report_path = run_dir / "analysis" / "sanitized_report.json"
    write_private_json(report_path, report)
    write_private_json(
        run_dir / "run_terminal_status.json",
        {
            "document_type": "rq2_personal_local_v24_smoke_terminal_status",
            "run_id": run_dir.name,
            "operational_status": report["operational_status"],
            "semantic_outcome": report["output"].get("semantic_outcome"),
            "sanitized_report_sha256": v1.sha256_file(report_path),
            "contains_source_text": False,
            "result_label": STATUS,
            "evidence_status": EVIDENCE_STATUS,
            "manuscript_eligible": False,
            "publication_or_release_eligible": False,
        },
    )
    inventory: list[dict[str, Any]] = []
    for path in sorted(run_dir.rglob("*")):
        mode = os.lstat(path).st_mode
        require(not stat.S_ISLNK(mode), "v24_seal_symlink_rejected")
        if stat.S_ISDIR(mode):
            require(stat.S_IMODE(mode) == 0o700, "v24_seal_directory_mode_invalid")
            continue
        require(stat.S_ISREG(mode), "v24_seal_non_regular_file")
        require(stat.S_IMODE(mode) == 0o600, "v24_seal_file_mode_invalid")
        inventory.append(
            {
                "path": path.relative_to(run_dir).as_posix(),
                "sha256": v1.sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
        )
    write_private_json(
        run_dir / "output_seal.json",
        {
            "document_type": "rq2_personal_local_v24_smoke_output_seal",
            "run_id": run_dir.name,
            "inventory": inventory,
            "inventory_sha256": v1.sha256_bytes(v1.canonical_bytes(inventory)),
            "contains_source_text": False,
            "sealed_run_contains_restricted_source_text": True,
            "result_label": STATUS,
            "evidence_status": EVIDENCE_STATUS,
            "manuscript_eligible": False,
            "publication_or_release_eligible": False,
        },
    )


def finalize_operational_failure(
    run_dir: Path,
    report: dict[str, Any],
    *,
    failure_code: str,
    attempted_real_calls: int,
) -> Path:
    """Seal a sanitized terminal failure after private run creation."""

    report["operational_status"] = "failed"
    report["output"].update(
        {
            "end_to_end_base_gate_exercised": False,
            "real_model_call_count": len(report["process"]["real_calls"]),
            "real_model_call_attempt_count": attempted_real_calls,
            "semantic_outcome": "operational_failure",
            "failure_code": failure_code,
        }
    )
    write_report_and_seal(run_dir, report)
    return run_dir


def execute(config: dict[str, Any], config_path: Path, run_id: str | None) -> Path:
    os.umask(0o077)
    v1_config, source_free_assets = validate_v24_freeze(
        config, config_path=config_path
    )

    service = preflight_required_service(v1_config)
    policy = config["prompt_limit_policy"]
    native_contexts = [
        model_native_context(
            v1_config,
            model_role=role,
            minimum=policy["minimum_native_context"],
        )
        for role in ("generator", "verifier")
    ]
    canary = v23.run_chunked_canary(
        config=v1.load_json(V23_CONFIG),
        v1_config=v1_config,
        assets=source_free_assets,
    )
    require(canary["status"] == "passed", "v24_source_free_canary_failed")

    # Only after the canary: validate the source-free policy boundary, then
    # let its exact validator perform the authorized live hash reads. No
    # corpus record is decoded and no predecessor selection is opened yet.
    source_free_v1_paths = v1.validate_freeze(
        v1_config,
        include_record_hashes=False,
        config_path=core.V1_CONFIG,
    )
    policy_doc = v1.load_json(source_free_v1_paths["policy"])
    v1.validate_policy_boundary(policy_doc, v1_config)
    policy_evidence = v1.run_exact_policy_validator(
        source_free_v1_paths, v1_config["policy_file_sha256"]
    )
    v1_paths = v1.validate_freeze(
        v1_config,
        include_record_hashes=True,
        config_path=core.V1_CONFIG,
    )
    predecessor_config = v1.load_json(v23.V22_CONFIG)
    bound_v1_config, bound_v1_paths, bound_paths, excluded = v22.validate_v22_freeze(
        predecessor_config,
        include_record_hashes=True,
        config_path=v23.V22_CONFIG,
    )
    require(bound_v1_config == v1_config, "v24_v1_config_changed_after_canary")
    require(len(excluded) == 90, "v24_predecessor_exclusions_invalid")
    assets = v22.load_assets(bound_paths)
    v22.validate_interface_assets(predecessor_config, assets)
    recheck_required_service(v1_config, service)

    lane_name = "dreaddit_development"
    lane = v1_config["lanes"][lane_name]
    split_index = v1.load_json(bound_v1_paths["split_index"])
    records = v1.load_bound_records(
        bound_v1_paths[f"records_{lane_name}"],
        lane["corpus"],
        lane["records_file_sha256"],
        lane["split"],
        split_index=split_index,
    )
    packet, selection = select_smoke_packet(
        v1_config, records, excluded_commitments=excluded
    )
    records_by_id = {row["record_id"]: row for row in records}
    excerpts = v1.excerpt_payload(packet, lane_name, records_by_id)
    del records_by_id, records, packet
    require(len(excerpts) == 6, "v24_excerpt_payload_count_invalid")

    resolved_run_id = build_run_id(run_id)
    run_dir = initialize_run(
        config,
        config_path,
        v1_config,
        v1_paths,
        run_id=resolved_run_id,
        service=service,
        native_contexts=native_contexts,
        canary=canary,
        policy_evidence=policy_evidence,
    )
    report = base_report(
        run_dir,
        selection=selection,
        canary=canary,
        policy_evidence=policy_evidence,
    )
    try:
        write_private_json(
            run_dir / "selection" / "dreaddit_development.json", selection
        )
    except Exception:
        return finalize_operational_failure(
            run_dir,
            report,
            failure_code="v24_selection_artifact_write_failed",
            attempted_real_calls=0,
        )

    try:
        recheck_required_service(v1_config, service)
        generation_prompt = core.base_generation_user_prompt(
            lane["corpus"], excerpts
        )
        generated, generation_call = invoke_hardened_call(
            v1_config,
            run_dir,
            call_id="generate_dreaddit_development_smoke_01_base",
            model_role="generator",
            system_prompt=assets["prompt_base_generation"],
            user_prompt=generation_prompt,
            output_schema=assets["schema_base_generation"],
            num_ctx=policy["request_num_ctx"],
            safety_margin_tokens=policy["safety_margin_tokens"],
        )
    except (
        core.V2Error,
        v1.PersonalLocalError,
        guard.PromptLimitError,
        V24Error,
    ) as exc:
        return finalize_operational_failure(
            run_dir,
            report,
            failure_code=str(exc),
            attempted_real_calls=1,
        )
    except Exception:
        return finalize_operational_failure(
            run_dir,
            report,
            failure_code="v24_generation_stage_runtime_failure",
            attempted_real_calls=1,
        )
    report["process"]["real_calls"].append(generation_call)
    report["output"]["generation_schema_status"] = "valid"
    report["output"]["generation_status"] = generated.get("status")
    try:
        validate_generation_cross_fields(generated)
    except V24Error as exc:
        return finalize_operational_failure(
            run_dir,
            report,
            failure_code=str(exc),
            attempted_real_calls=1,
        )
    report["output"]["generation_cross_field_status"] = "valid"

    if generated.get("status") != "constructed":
        report["operational_status"] = "completed_generator_terminal"
        report["output"].update(
            {
                "end_to_end_base_gate_exercised": False,
                "real_model_call_count": 1,
                "real_model_call_attempt_count": 1,
                "semantic_outcome": "generator_not_constructable",
                "reason_codes": sorted(set(generated.get("reason_codes", []))),
            }
        )
        write_report_and_seal(run_dir, report)
        return run_dir

    try:
        roles, interpretation, metadata = core.map_positional_base_v2(
            generated, excerpts
        )
        base_item = v1.build_item(
            lane_name=lane_name,
            corpus=lane["corpus"],
            packet_id=selection["packet_id"],
            output_key="v24-smoke-01:base",
            interpretation=interpretation,
            roles=roles,
            excerpts=excerpts,
        )
        jsonschema.validate(base_item, v1.load_json(bound_v1_paths["item_schema"]))
    except (core.V2Error, v1.PersonalLocalError, jsonschema.ValidationError) as exc:
        code = (
            str(exc)
            if isinstance(exc, (core.V2Error, v1.PersonalLocalError))
            and str(exc) in core.BASE_SEMANTIC_CODES
            else "v24_deterministic_base_item_invalid"
        )
        report["operational_status"] = "completed_deterministic_construction_terminal"
        report["output"].update(
            {
                "end_to_end_base_gate_exercised": False,
                "real_model_call_count": 1,
                "real_model_call_attempt_count": 1,
                "semantic_outcome": "deterministic_construction_invalid",
                "reason_codes": [code],
            }
        )
        write_report_and_seal(run_dir, report)
        return run_dir
    except Exception:
        return finalize_operational_failure(
            run_dir,
            report,
            failure_code="v24_deterministic_construction_runtime_failure",
            attempted_real_calls=1,
        )

    try:
        write_private_json(
            run_dir / "private" / "base_item.private.json", base_item
        )
        write_private_json(
            run_dir / "private" / "base_mapping.private.json", metadata
        )
        report["output"]["deterministic_mapping_status"] = "valid"
        report["output"]["role_counts"] = role_counts(metadata)

        view = core.compact_base_view(base_item, metadata)
        write_private_json(
            run_dir / "private" / "base_gate_input_seal.json",
            {
                "document_type": (
                    "rq2_personal_local_v24_smoke_base_gate_input_seal"
                ),
                "base_item_sha256": v1.sha256_bytes(
                    v1.canonical_bytes(base_item)
                ),
                "compact_view_sha256": v1.sha256_bytes(
                    v1.canonical_bytes(view)
                ),
                "target_free": True,
                "contains_source_text": False,
            },
        )
    except Exception:
        return finalize_operational_failure(
            run_dir,
            report,
            failure_code="v24_private_base_artifact_stage_failed",
            attempted_real_calls=1,
        )
    try:
        recheck_required_service(v1_config, service)
        gate_prompt = core.base_gate_user_prompt(view)
        transport_output, gate_call = invoke_hardened_call(
            v1_config,
            run_dir,
            call_id="verify_dreaddit_development_smoke_01_base",
            model_role="verifier",
            system_prompt=assets["prompt_base_admissibility"],
            user_prompt=gate_prompt,
            output_schema=assets["schema_base_admissibility"],
            num_ctx=policy["request_num_ctx"],
            safety_margin_tokens=policy["safety_margin_tokens"],
        )
    except (
        core.V2Error,
        v1.PersonalLocalError,
        guard.PromptLimitError,
        V24Error,
    ) as exc:
        return finalize_operational_failure(
            run_dir,
            report,
            failure_code=str(exc),
            attempted_real_calls=2,
        )
    except Exception:
        return finalize_operational_failure(
            run_dir,
            report,
            failure_code="v24_base_gate_stage_runtime_failure",
            attempted_real_calls=2,
        )
    report["process"]["real_calls"].append(gate_call)
    try:
        canonical = v22.adapt_base_admissibility_transport_v22(
            transport_output,
            transport_schema=assets["schema_base_admissibility"],
            canonical_schema=assets["canonical_base_admissibility_schema"],
            adapter_contract=assets["transport_adapter_contract"],
        )
        admitted, acceptance_reasons = core.base_gate_acceptance(
            canonical, base_item, metadata
        )
    except Exception:
        return finalize_operational_failure(
            run_dir,
            report,
            failure_code="v24_base_gate_adapter_or_acceptance_failed",
            attempted_real_calls=2,
        )
    try:
        write_private_json(
            run_dir / "private" / "base_gate_canonical.private.json", canonical
        )
    except Exception:
        return finalize_operational_failure(
            run_dir,
            report,
            failure_code="v24_canonical_gate_artifact_write_failed",
            attempted_real_calls=2,
        )
    report["operational_status"] = "passed"
    report["output"].update(
        {
            "end_to_end_base_gate_exercised": True,
            "real_model_call_count": 2,
            "real_model_call_attempt_count": 2,
            "transport_schema_status": "valid",
            "adapter_status": "valid",
            "canonical_schema_status": "valid",
            "semantic_outcome": (
                "admitted"
                if admitted
                else "unclear"
                if canonical.get("base_status") == "unclear"
                else "rejected"
            ),
            "base_status": canonical["base_status"],
            "reason_codes": canonical["reason_codes"],
            "checks": canonical["checks"],
            "readiness": canonical["readiness"],
            "deterministic_admitted": admitted,
            "deterministic_acceptance_reason_codes": acceptance_reasons,
            "verification_label": VERIFICATION_LABEL,
        }
    )
    write_report_and_seal(run_dir, report)
    return run_dir


def static_summary(config: dict[str, Any]) -> dict[str, Any]:
    v1_config, _ = validate_v24_freeze(config, config_path=DEFAULT_CONFIG)
    return {
        "v24_static_status": "passed",
        "dataset": "dreaddit",
        "split": "development_train",
        "planned_packet_count": 1,
        "planned_excerpt_count": 6,
        "planned_real_model_calls_maximum": 2,
        "request_num_ctx": config["prompt_limit_policy"]["request_num_ctx"],
        "truncate": False,
        "shift": False,
        "real_packet_chunking_allowed": False,
        "generator_model": v1_config["models"]["generator"]["model_id"],
        "verifier_model": v1_config["models"]["verifier"]["model_id"],
        "data_opened": False,
        "storage_opened": False,
        "service_contacted": False,
        "writes_artifacts": False,
        "result_label": STATUS,
        "evidence_status": EVIDENCE_STATUS,
        "manuscript_eligible": False,
        "publication_or_release_eligible": False,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("dry-run", help="Validate the one-packet smoke contract.")
    run_parser = subparsers.add_parser(
        "run", help="Run one private six-excerpt Dreaddit development packet."
    )
    run_parser.add_argument("--run-id")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = args.config.absolute()
    if config_path != DEFAULT_CONFIG:
        print(
            json.dumps(
                {
                    "v24_status": "stopped",
                    "failure_code": "only_exact_v24_freeze_allowed",
                    "contains_source_text": False,
                    "result_label": STATUS,
                    "evidence_status": EVIDENCE_STATUS,
                    "manuscript_eligible": False,
                    "publication_or_release_eligible": False,
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2
    try:
        config = v1.load_json(config_path)
        if args.command == "dry-run":
            print(json.dumps(static_summary(config), sort_keys=True))
            return 0
        run_dir = execute(config, config_path, args.run_id)
        report = v1.load_json(run_dir / "analysis" / "sanitized_report.json")
        print(
            json.dumps(
                {
                    "v24_status": report["operational_status"],
                    "run_id": run_dir.name,
                    "input_packet_count": report["input"]["packet_count"],
                    "input_excerpt_count": report["input"]["excerpt_count"],
                    "real_model_call_count": report["output"].get(
                        "real_model_call_count"
                    ),
                    "semantic_outcome": report["output"].get("semantic_outcome"),
                    "contains_source_text": False,
                    "result_label": STATUS,
                    "evidence_status": EVIDENCE_STATUS,
                    "manuscript_eligible": False,
                    "publication_or_release_eligible": False,
                },
                sort_keys=True,
            )
        )
        return (
            0
            if report["operational_status"]
            in {
                "passed",
                "completed_generator_terminal",
                "completed_deterministic_construction_terminal",
            }
            else 3
        )
    except (v1.PersonalLocalError, v22.V22Error, v23.V23Error, guard.PromptLimitError, V24Error) as exc:
        print(
            json.dumps(
                {
                    "v24_status": "stopped",
                    "failure_code": str(exc),
                    "contains_source_text": False,
                    "result_label": STATUS,
                    "evidence_status": EVIDENCE_STATUS,
                    "manuscript_eligible": False,
                    "publication_or_release_eligible": False,
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2
    except Exception:
        print(
            json.dumps(
                {
                    "v24_status": "stopped",
                    "failure_code": "v24_runtime_failure",
                    "contains_source_text": False,
                    "result_label": STATUS,
                    "evidence_status": EVIDENCE_STATUS,
                    "manuscript_eligible": False,
                    "publication_or_release_eligible": False,
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
