#!/usr/bin/env python3
"""Run the source-free v2.3 WarrantRoute prompt-limit diagnostic."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


SCRIPT = Path(__file__).resolve()
RQ2_ROOT = SCRIPT.parents[1]
WORKSPACE = RQ2_ROOT.parents[1]
V22_RUNNER = SCRIPT.with_name("run_personal_local_main_v22.py")
V22_RUNNER_SHA256 = "9ba6f1ae7fbd9e16b703df8209f09675398356d5d4c48d29ad68eded07533be1"
V22_CONFIG = RQ2_ROOT / "config" / "personal_local_main_v22_freeze.json"
V22_CONFIG_SHA256 = "1a36abb923976e6f0bf5099fcdf8c4df5668674aad88a37144ac540af5cf36d9"
PROMPT_GUARD = SCRIPT.with_name("prompt_limit_guard.py")
PROMPT_GUARD_SHA256 = "db70e4080e3f081792c7992db6d7576c334e72357ff295d8c964653512194ddd"
DEFAULT_CONFIG = RQ2_ROOT / "config" / "personal_local_main_v23_freeze.json"


def _raw_sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_bound_module(path: Path, digest: str, name: str) -> Any:
    if _raw_sha256(path) != digest:
        raise SystemExit(f"v23_{name}_hash_drift")
    spec = importlib.util.spec_from_file_location(f"rq2_v23_{name}", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"v23_{name}_import_spec_invalid")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


v22 = _load_bound_module(V22_RUNNER, V22_RUNNER_SHA256, "v22")
guard = _load_bound_module(PROMPT_GUARD, PROMPT_GUARD_SHA256, "prompt_guard")
v1 = v22.v1


class V23Error(RuntimeError):
    """A sanitized source-free v2.3 failure."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise V23Error(code)


EXPECTED_CONFIG = {
    "document_type": "rq2_personal_local_main_v23_freeze",
    "freeze_version": "rq2-personal-local-main-v2.3",
    "status": "private_personal_exploratory_not_for_publication",
    "evidence_status": "diagnostic_not_manuscript_evidence",
    "execution_scope": "source_free_transport_diagnostic_only",
    "source_bearing_run_allowed": False,
    "writes_allowed": False,
    "predecessor_v22_runner_file": (
        "experiments/rq2_role_prompted_llm/scripts/run_personal_local_main_v22.py"
    ),
    "predecessor_v22_runner_sha256": V22_RUNNER_SHA256,
    "predecessor_v22_config_file": (
        "experiments/rq2_role_prompted_llm/config/personal_local_main_v22_freeze.json"
    ),
    "predecessor_v22_config_sha256": V22_CONFIG_SHA256,
    "prompt_limit_helper_file": (
        "experiments/rq2_role_prompted_llm/scripts/prompt_limit_guard.py"
    ),
    "prompt_limit_helper_sha256": PROMPT_GUARD_SHA256,
    "protocol_file": (
        "experiments/rq2_role_prompted_llm/protocol/personal_local_main_contract_v5.md"
    ),
    "protocol_sha256": "cfbf110e3641cf9b79916a430bd84080206dc97f22d5c7dfb014ef48d790aa40",
    "runner_file": (
        "experiments/rq2_role_prompted_llm/scripts/run_personal_local_main_v23.py"
    ),
    "runner_sha256": None,
    "prompt_limit_policy": {
        "request_num_ctx": 16384,
        "minimum_native_context": 16384,
        "max_user_prompt_bytes": 8192,
        "reserved_output_tokens": 768,
        "safety_margin_tokens": 512,
        "max_chunks_per_case": 8,
        "max_overflow_rejections_per_case": 8,
        "truncate": False,
        "shift": False,
        "overflow_action": "deterministic_payload_bisection",
        "unsupported_semantic_unit_action": "fail_before_generation",
    },
    "live_interface_canary": {
        "logical_fixture_count": 3,
        "original_user_prompt_bytes_each": 16384,
        "chunkable_component": "source_free_inert_padding_only",
        "instruction_repeated_per_chunk": True,
        "reducer": "exact_consensus",
        "model_role": "verifier",
        "response_content_emission_allowed": False,
        "data_or_storage_access_allowed": False,
    },
}


def _resolve_workspace_file(relative: str) -> Path:
    require(isinstance(relative, str) and bool(relative), "v23_bound_path_invalid")
    path = (WORKSPACE / relative).absolute()
    try:
        path.relative_to(WORKSPACE)
    except ValueError:
        raise V23Error("v23_bound_path_escape") from None
    require(path.is_file() and not path.is_symlink(), "v23_bound_file_missing")
    v1.reject_symlink_components(path, anchor=WORKSPACE)
    return path


def validate_v23_freeze(
    config: dict[str, Any], *, config_path: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Validate v2.3 without opening records, selections, or Storage."""

    require(config_path == DEFAULT_CONFIG, "only_exact_v23_freeze_allowed")
    require(config == v1.load_json(config_path), "v23_config_object_file_drift")
    require(set(config) == set(EXPECTED_CONFIG), "v23_freeze_fields_mismatch")
    for key, expected in EXPECTED_CONFIG.items():
        if key == "runner_sha256":
            continue
        require(config.get(key) == expected, f"v23_freeze_value_mismatch:{key}")
    require(
        isinstance(config.get("runner_sha256"), str)
        and len(config["runner_sha256"]) == 64,
        "v23_runner_hash_invalid",
    )

    require(_raw_sha256(V22_RUNNER) == V22_RUNNER_SHA256, "v23_v22_runner_hash_drift")
    require(_raw_sha256(V22_CONFIG) == V22_CONFIG_SHA256, "v23_v22_config_hash_drift")
    require(_raw_sha256(PROMPT_GUARD) == PROMPT_GUARD_SHA256, "v23_prompt_guard_hash_drift")
    protocol_path = _resolve_workspace_file(config["protocol_file"])
    runner_path = _resolve_workspace_file(config["runner_file"])
    require(
        _raw_sha256(protocol_path) == config["protocol_sha256"],
        "v23_protocol_hash_drift",
    )
    require(_raw_sha256(runner_path) == config["runner_sha256"], "v23_runner_hash_drift")

    predecessor_config = v1.load_json(V22_CONFIG)
    v1_config, _, paths, excluded = v22.validate_v22_freeze(
        predecessor_config,
        include_record_hashes=False,
        config_path=V22_CONFIG,
    )
    require(excluded == set(), "v23_source_free_validation_loaded_exclusions")
    assets = v22.load_assets(paths)
    v22.validate_interface_assets(predecessor_config, assets)
    return v1_config, assets


def _fixed_and_chunkable_canary(
    assets: dict[str, Any], case: dict[str, Any]
) -> tuple[str, str]:
    fixture_doc = assets["transport_canary_fixtures"]
    profile = fixture_doc["source_free_prompt_profile"]
    fixed = profile["prefix"] + case["canary_instruction"] + "\n"
    whole = v22.build_source_free_canary_prompt(profile, case["canary_instruction"])
    require(whole.startswith(fixed), "v23_canary_fixed_prefix_mismatch")
    chunkable = whole[len(fixed) :]
    require(
        len(whole.encode("ascii")) == 16384 and chunkable.isascii(),
        "v23_canary_source_free_prompt_invalid",
    )
    return fixed, chunkable


def prepare_chunked_canary(
    config: dict[str, Any], v1_config: dict[str, Any], assets: dict[str, Any]
) -> list[dict[str, Any]]:
    policy = config["prompt_limit_policy"]
    rows: list[dict[str, Any]] = []
    for case in assets["transport_canary_fixtures"]["fixtures"]:
        guard.require_approved_chunking_scope(
            component=config["live_interface_canary"]["chunkable_component"],
            reducer=config["live_interface_canary"]["reducer"],
        )
        fixed, chunkable = _fixed_and_chunkable_canary(assets, case)
        plan = guard.build_chunk_plan(
            fixed_prefix=fixed,
            chunkable_payload=chunkable,
            max_user_prompt_bytes=policy["max_user_prompt_bytes"],
            max_chunks=policy["max_chunks_per_case"],
        )
        require(plan.chunk_count > 1, "v23_canary_did_not_exercise_chunking")
        requests: list[dict[str, Any]] = []
        for user_prompt in plan.user_prompts:
            request = v1.build_model_request(
                v1_config,
                model_role="verifier",
                system_prompt=assets["prompt_base_admissibility"],
                user_prompt=user_prompt,
                output_schema=assets["schema_base_admissibility"],
                rating_call=False,
                rating_repetition=None,
            )
            request = guard.harden_ollama_request(
                request, num_ctx=policy["request_num_ctx"]
            )
            require(
                request.get("truncate") is False
                and request.get("shift") is False
                and request["options"]["num_ctx"] == policy["request_num_ctx"],
                "v23_hardened_request_invalid",
            )
            requests.append(request)
        rows.append({"case": case, "plan": plan, "requests": requests})
    require(len(rows) == 3, "v23_canary_fixture_count_invalid")
    return rows


def _plan_digest(
    *, fixed: str, payload_chunks: list[str], max_user_prompt_bytes: int
) -> str:
    value = {
        "fixed_prefix_sha256": guard.sha256_bytes(fixed.encode("utf-8")),
        "original_payload_sha256": guard.sha256_bytes(
            "".join(payload_chunks).encode("utf-8")
        ),
        "chunk_payload_sha256": [
            guard.sha256_bytes(chunk.encode("utf-8")) for chunk in payload_chunks
        ],
        "user_prompt_bytes": [
            guard.utf8_size(fixed + chunk) for chunk in payload_chunks
        ],
        "max_user_prompt_bytes": max_user_prompt_bytes,
        "contains_prompt_content": False,
    }
    return guard.sha256_bytes(guard.canonical_bytes(value))


def _model_native_context(
    v1_config: dict[str, Any], *, minimum: int
) -> dict[str, Any]:
    model_id = v1_config["models"]["verifier"]["model_id"]
    show = v1.api_json(
        v1_config["service_url"], "/api/show", {"model": model_id}, timeout=20
    )
    info = show.get("model_info")
    require(isinstance(info, dict), "v23_model_info_missing")
    candidates = {
        key: value
        for key, value in info.items()
        if isinstance(key, str)
        and key.endswith(".context_length")
        and type(value) is int
    }
    require(len(candidates) == 1, "v23_native_context_metadata_ambiguous")
    key, value = next(iter(candidates.items()))
    require(value >= minimum, "v23_native_context_capacity_insufficient")
    return {"metadata_key": key, "native_context_length": value}


def _split_overflow_chunk(payload: str) -> tuple[str, ...]:
    size = guard.utf8_size(payload)
    require(size > 1, "v23_overflow_chunk_unsplittable")
    children = guard.split_utf8_exact(payload, max(1, (size + 1) // 2))
    require(len(children) >= 2 and "".join(children) == payload, "v23_overflow_split_invalid")
    return children


def run_chunked_canary(
    config: dict[str, Any], v1_config: dict[str, Any], assets: dict[str, Any]
) -> dict[str, Any]:
    policy = config["prompt_limit_policy"]
    prepared = prepare_chunked_canary(config, v1_config, assets)
    chunk_counts: dict[str, int] = {}
    initial_plan_hashes: dict[str, str] = {}
    final_plan_hashes: dict[str, str] = {}
    request_hashes: list[str] = []
    prompt_token_counts: list[int] = []
    overflow_rejections = 0
    generated_attempts = 0

    for row in prepared:
        case = row["case"]
        code = case["code"]
        plan = row["plan"]
        fixed = plan.fixed_prefix
        chunks = list(plan.payload_chunks)
        initial_plan_hashes[code] = plan.plan_sha256
        canonical_outputs: list[dict[str, Any]] = []
        index = 0
        case_overflows = 0
        while index < len(chunks):
            require(
                len(chunks) <= policy["max_chunks_per_case"],
                f"v23_canary_case_{code}_max_chunks_exceeded",
            )
            user_prompt = fixed + chunks[index]
            base_request = v1.build_model_request(
                v1_config,
                model_role="verifier",
                system_prompt=assets["prompt_base_admissibility"],
                user_prompt=user_prompt,
                output_schema=assets["schema_base_admissibility"],
                rating_call=False,
                rating_repetition=None,
            )
            request = guard.harden_ollama_request(
                base_request, num_ctx=policy["request_num_ctx"]
            )
            request_hashes.append(guard.sha256_bytes(guard.canonical_bytes(request)))
            try:
                response = v1.api_json(
                    v1_config["service_url"], "/api/chat", request, timeout=180
                )
            except Exception as exc:
                if guard.is_ollama_context_overflow(exc):
                    case_overflows += 1
                    overflow_rejections += 1
                    require(
                        case_overflows
                        <= policy["max_overflow_rejections_per_case"],
                        f"v23_canary_case_{code}_overflow_limit_exceeded",
                    )
                    children = _split_overflow_chunk(chunks[index])
                    chunks[index : index + 1] = list(children)
                    continue
                raise V23Error(
                    f"v23_canary_case_{code}_chunk_{index + 1:02d}_transport_failed"
                ) from None

            generated_attempts += 1
            try:
                accounting = guard.validate_successful_context_use(
                    response,
                    num_ctx=policy["request_num_ctx"],
                    reserved_output_tokens=policy["reserved_output_tokens"],
                    safety_margin_tokens=policy["safety_margin_tokens"],
                )
                transport, _ = v1.parse_model_response(
                    response,
                    expected_model=v1_config["models"]["verifier"]["model_id"],
                    output_schema=assets["schema_base_admissibility"],
                )
                canonical = v22.adapt_base_admissibility_transport_v22(
                    transport,
                    transport_schema=assets["schema_base_admissibility"],
                    canonical_schema=assets["canonical_base_admissibility_schema"],
                    adapter_contract=assets["transport_adapter_contract"],
                )
            except Exception:
                raise V23Error(
                    f"v23_canary_case_{code}_chunk_{index + 1:02d}_validation_failed"
                ) from None
            require(
                v22.strict_equal_v22(canonical, case["canonical_output"]),
                f"v23_canary_case_{code}_chunk_{index + 1:02d}_fixture_mismatch",
            )
            prompt_token_counts.append(accounting["prompt_eval_count"])
            canonical_outputs.append(canonical)
            index += 1

        try:
            guard.exact_consensus(canonical_outputs)
        except guard.PromptLimitError:
            raise V23Error(f"v23_canary_case_{code}_exact_consensus_failed") from None
        chunk_counts[code] = len(chunks)
        final_plan_hashes[code] = _plan_digest(
            fixed=fixed,
            payload_chunks=chunks,
            max_user_prompt_bytes=policy["max_user_prompt_bytes"],
        )

    return {
        "status": "passed",
        "logical_fixture_count": 3,
        "generated_physical_attempts": generated_attempts,
        "pre_generation_overflow_rejections": overflow_rejections,
        "chunk_counts": chunk_counts,
        "initial_plan_set_sha256": guard.sha256_bytes(
            guard.canonical_bytes(initial_plan_hashes)
        ),
        "final_plan_set_sha256": guard.sha256_bytes(
            guard.canonical_bytes(final_plan_hashes)
        ),
        "request_set_sha256": guard.sha256_bytes(
            guard.canonical_bytes(request_hashes)
        ),
        "prompt_eval_count_min": min(prompt_token_counts),
        "prompt_eval_count_max": max(prompt_token_counts),
        "request_num_ctx": policy["request_num_ctx"],
        "automatic_chunking_used": any(value > 1 for value in chunk_counts.values()),
        "truncate": False,
        "shift": False,
        "reducer": "exact_consensus",
        "model_content_retained": False,
        "contains_source_text": False,
        "data_or_storage_opened": False,
        "writes_artifacts": False,
    }


def static_summary(
    config: dict[str, Any], v1_config: dict[str, Any], assets: dict[str, Any]
) -> dict[str, Any]:
    prepared = prepare_chunked_canary(config, v1_config, assets)
    counts = {row["case"]["code"]: row["plan"].chunk_count for row in prepared}
    return {
        "v23_static_status": "passed",
        "automatic_chunking_configured": True,
        "logical_fixture_count": 3,
        "planned_chunk_counts": counts,
        "planned_generated_physical_attempts": sum(counts.values()),
        "request_num_ctx": config["prompt_limit_policy"]["request_num_ctx"],
        "max_user_prompt_bytes": config["prompt_limit_policy"][
            "max_user_prompt_bytes"
        ],
        "truncate": False,
        "shift": False,
        "source_bearing_run_allowed": False,
        "data_opened": False,
        "storage_opened": False,
        "service_contacted": False,
        "writes_artifacts": False,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("dry-run", help="Validate the source-free chunking contract.")
    subparsers.add_parser(
        "preflight-service",
        help="Run chunked source-free canaries against numeric-loopback Ollama.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = args.config.absolute()
    try:
        config = v1.load_json(config_path)
        v1_config, assets = validate_v23_freeze(config, config_path=config_path)
        if args.command == "dry-run":
            print(json.dumps(static_summary(config, v1_config, assets), sort_keys=True))
            return 0
        service = v1.preflight_service(v1_config)
        native_context = _model_native_context(
            v1_config,
            minimum=config["prompt_limit_policy"]["minimum_native_context"],
        )
        canary = run_chunked_canary(config, v1_config, assets)
        print(
            json.dumps(
                {
                    "v23_status": "passed",
                    "endpoint": service["endpoint"],
                    "endpoint_is_numeric_loopback": service[
                        "endpoint_is_numeric_loopback"
                    ],
                    "ollama_version": service["ollama_version"],
                    "verifier_model": service["models"]["verifier"]["model_id"],
                    "native_context": native_context,
                    "chunked_canary": canary,
                    "contains_source_text": False,
                    "writes_artifacts": False,
                    "manuscript_eligible": False,
                },
                sort_keys=True,
            )
        )
        return 0
    except (v1.PersonalLocalError, v22.V22Error, guard.PromptLimitError, V23Error) as exc:
        print(
            json.dumps(
                {
                    "v23_status": "stopped",
                    "failure_code": str(exc),
                    "contains_source_text": False,
                    "writes_artifacts": False,
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
                    "v23_status": "stopped",
                    "failure_code": "v23_runtime_failure",
                    "contains_source_text": False,
                    "writes_artifacts": False,
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
