#!/usr/bin/env python3
"""Source-free prompt-limit planning for local WarrantRoute calls.

The helper never decides how research evidence should be aggregated.  Callers
must supply a fixed instruction prefix, an explicitly chunkable payload, and a
task-specific reducer.  It prevents Ollama's default silent input truncation by
requiring ``truncate=false`` and ``shift=false`` on every planned request.
"""

from __future__ import annotations

import base64
import copy
import hashlib
import json
from dataclasses import dataclass
from typing import Any, Sequence


class PromptLimitError(RuntimeError):
    """A finite, source-free prompt-limit failure."""


def require_approved_chunking_scope(*, component: str, reducer: str) -> None:
    """Permit only the currently frozen, semantics-preserving reducer."""

    if (
        component != "source_free_inert_padding_only"
        or reducer != "exact_consensus"
    ):
        raise PromptLimitError("prompt_limit_semantic_chunk_contract_required")


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def utf8_size(text: str) -> int:
    if not isinstance(text, str):
        raise PromptLimitError("prompt_limit_text_not_string")
    return len(text.encode("utf-8"))


def _largest_prefix_within_bytes(text: str, byte_limit: int) -> int:
    low = 0
    high = len(text)
    while low < high:
        middle = (low + high + 1) // 2
        if utf8_size(text[:middle]) <= byte_limit:
            low = middle
        else:
            high = middle - 1
    return low


def _preferred_boundary(text: str, maximum: int) -> int:
    """Choose a deterministic semantic boundary without dropping delimiters."""

    if maximum >= len(text):
        return len(text)
    minimum = max(1, maximum // 2)
    prefix = text[:maximum]
    for marker in ("\n\n", "\n", ". ", "? ", "! ", "; ", ", ", " "):
        index = prefix.rfind(marker, minimum)
        if index >= minimum:
            return index + len(marker)
    return maximum


def split_utf8_exact(text: str, max_chunk_bytes: int) -> tuple[str, ...]:
    """Split text losslessly at preferred boundaries and never inside UTF-8."""

    if type(max_chunk_bytes) is not int or max_chunk_bytes <= 0:
        raise PromptLimitError("prompt_limit_invalid_chunk_byte_limit")
    if not isinstance(text, str):
        raise PromptLimitError("prompt_limit_text_not_string")
    if text == "":
        return ("",)

    chunks: list[str] = []
    remaining = text
    while remaining:
        maximum = _largest_prefix_within_bytes(remaining, max_chunk_bytes)
        if maximum == 0:
            raise PromptLimitError("prompt_limit_single_codepoint_exceeds_chunk_limit")
        boundary = _preferred_boundary(remaining, maximum)
        chunk = remaining[:boundary]
        if not chunk or utf8_size(chunk) > max_chunk_bytes:
            raise PromptLimitError("prompt_limit_internal_chunk_boundary_invalid")
        chunks.append(chunk)
        remaining = remaining[boundary:]

    if "".join(chunks) != text:
        raise PromptLimitError("prompt_limit_chunk_reassembly_failed")
    return tuple(chunks)


@dataclass(frozen=True)
class ChunkPlan:
    strategy: str
    fixed_prefix: str
    payload_chunks: tuple[str, ...]
    max_user_prompt_bytes: int
    fixed_prefix_sha256: str
    original_payload_sha256: str
    chunk_payload_sha256: tuple[str, ...]
    user_prompt_bytes: tuple[int, ...]
    plan_sha256: str

    @property
    def user_prompts(self) -> tuple[str, ...]:
        return tuple(self.fixed_prefix + chunk for chunk in self.payload_chunks)

    @property
    def chunk_count(self) -> int:
        return len(self.payload_chunks)

    def public_summary(self) -> dict[str, Any]:
        return {
            "strategy": self.strategy,
            "chunk_count": self.chunk_count,
            "max_user_prompt_bytes": self.max_user_prompt_bytes,
            "fixed_prefix_sha256": self.fixed_prefix_sha256,
            "original_payload_sha256": self.original_payload_sha256,
            "chunk_payload_sha256": list(self.chunk_payload_sha256),
            "user_prompt_bytes": list(self.user_prompt_bytes),
            "plan_sha256": self.plan_sha256,
            "contains_prompt_content": False,
        }


def build_chunk_plan(
    *,
    fixed_prefix: str,
    chunkable_payload: str,
    max_user_prompt_bytes: int,
    max_chunks: int,
) -> ChunkPlan:
    """Plan deterministic chunks while repeating the complete instruction."""

    if not isinstance(fixed_prefix, str) or not fixed_prefix:
        raise PromptLimitError("prompt_limit_fixed_prefix_missing")
    if not isinstance(chunkable_payload, str):
        raise PromptLimitError("prompt_limit_payload_not_string")
    if type(max_user_prompt_bytes) is not int or max_user_prompt_bytes <= 0:
        raise PromptLimitError("prompt_limit_invalid_user_prompt_limit")
    if type(max_chunks) is not int or max_chunks <= 0:
        raise PromptLimitError("prompt_limit_invalid_max_chunks")

    fixed_bytes = utf8_size(fixed_prefix)
    if fixed_bytes >= max_user_prompt_bytes:
        raise PromptLimitError("prompt_limit_fixed_prefix_exceeds_budget")
    payload_limit = max_user_prompt_bytes - fixed_bytes
    payload_chunks = split_utf8_exact(chunkable_payload, payload_limit)
    if len(payload_chunks) > max_chunks:
        raise PromptLimitError("prompt_limit_max_chunks_exceeded")
    if "".join(payload_chunks) != chunkable_payload:
        raise PromptLimitError("prompt_limit_chunk_reassembly_failed")

    user_prompt_bytes = tuple(
        utf8_size(fixed_prefix + chunk) for chunk in payload_chunks
    )
    if any(size > max_user_prompt_bytes for size in user_prompt_bytes):
        raise PromptLimitError("prompt_limit_planned_chunk_exceeds_budget")

    fixed_hash = sha256_bytes(fixed_prefix.encode("utf-8"))
    payload_hash = sha256_bytes(chunkable_payload.encode("utf-8"))
    chunk_hashes = tuple(
        sha256_bytes(chunk.encode("utf-8")) for chunk in payload_chunks
    )
    strategy = "single_request" if len(payload_chunks) == 1 else "chunked_exact"
    public = {
        "strategy": strategy,
        "chunk_count": len(payload_chunks),
        "max_user_prompt_bytes": max_user_prompt_bytes,
        "fixed_prefix_sha256": fixed_hash,
        "original_payload_sha256": payload_hash,
        "chunk_payload_sha256": list(chunk_hashes),
        "user_prompt_bytes": list(user_prompt_bytes),
        "contains_prompt_content": False,
    }
    return ChunkPlan(
        strategy=strategy,
        fixed_prefix=fixed_prefix,
        payload_chunks=payload_chunks,
        max_user_prompt_bytes=max_user_prompt_bytes,
        fixed_prefix_sha256=fixed_hash,
        original_payload_sha256=payload_hash,
        chunk_payload_sha256=chunk_hashes,
        user_prompt_bytes=user_prompt_bytes,
        plan_sha256=sha256_bytes(canonical_bytes(public)),
    )


def split_planned_payload_chunk(
    plan: ChunkPlan, chunk_index: int, *, max_chunks: int
) -> ChunkPlan:
    """Deterministically bisect one rejected chunk and rebuild the plan."""

    if type(chunk_index) is not int or not 0 <= chunk_index < plan.chunk_count:
        raise PromptLimitError("prompt_limit_split_index_invalid")
    target = plan.payload_chunks[chunk_index]
    target_bytes = utf8_size(target)
    if target_bytes <= 1:
        raise PromptLimitError("prompt_limit_unsplittable_payload")
    children = split_utf8_exact(target, max(1, (target_bytes + 1) // 2))
    if len(children) < 2:
        midpoint = max(1, len(target) // 2)
        children = (target[:midpoint], target[midpoint:])
    payload_chunks = (
        plan.payload_chunks[:chunk_index]
        + tuple(children)
        + plan.payload_chunks[chunk_index + 1 :]
    )
    if len(payload_chunks) > max_chunks:
        raise PromptLimitError("prompt_limit_max_chunks_exceeded")
    payload = "".join(payload_chunks)
    rebuilt = build_chunk_plan(
        fixed_prefix=plan.fixed_prefix,
        chunkable_payload=payload,
        max_user_prompt_bytes=plan.max_user_prompt_bytes,
        max_chunks=max_chunks,
    )
    if rebuilt.payload_chunks == plan.payload_chunks:
        raise PromptLimitError("prompt_limit_split_made_no_progress")
    return ChunkPlan(
        strategy="chunked_exact",
        fixed_prefix=rebuilt.fixed_prefix,
        payload_chunks=payload_chunks,
        max_user_prompt_bytes=rebuilt.max_user_prompt_bytes,
        fixed_prefix_sha256=rebuilt.fixed_prefix_sha256,
        original_payload_sha256=rebuilt.original_payload_sha256,
        chunk_payload_sha256=tuple(
            sha256_bytes(chunk.encode("utf-8")) for chunk in payload_chunks
        ),
        user_prompt_bytes=tuple(
            utf8_size(rebuilt.fixed_prefix + chunk) for chunk in payload_chunks
        ),
        plan_sha256=sha256_bytes(
            canonical_bytes(
                {
                    "strategy": "chunked_exact",
                    "chunk_count": len(payload_chunks),
                    "max_user_prompt_bytes": rebuilt.max_user_prompt_bytes,
                    "fixed_prefix_sha256": rebuilt.fixed_prefix_sha256,
                    "original_payload_sha256": rebuilt.original_payload_sha256,
                    "chunk_payload_sha256": [
                        sha256_bytes(chunk.encode("utf-8"))
                        for chunk in payload_chunks
                    ],
                    "user_prompt_bytes": [
                        utf8_size(rebuilt.fixed_prefix + chunk)
                        for chunk in payload_chunks
                    ],
                    "contains_prompt_content": False,
                }
            )
        ),
    )


def harden_ollama_request(request: dict[str, Any], *, num_ctx: int) -> dict[str, Any]:
    """Return a request that forbids input truncation and context shifting."""

    if not isinstance(request, dict):
        raise PromptLimitError("prompt_limit_request_not_object")
    if type(num_ctx) is not int or num_ctx <= 0:
        raise PromptLimitError("prompt_limit_invalid_num_ctx")
    hardened = copy.deepcopy(request)
    options = hardened.get("options")
    if not isinstance(options, dict):
        raise PromptLimitError("prompt_limit_request_options_missing")
    options["num_ctx"] = num_ctx
    hardened["truncate"] = False
    hardened["shift"] = False
    return hardened


def is_ollama_context_overflow(error: BaseException) -> bool:
    """Recognize only Ollama's finite pre-generation context error."""

    raw = getattr(error, "raw", None)
    if not isinstance(raw, dict) or raw.get("http_status") != 400:
        return False
    encoded = raw.get("body_base64")
    if not isinstance(encoded, str):
        return False
    try:
        body = base64.b64decode(encoded, validate=True)
        value = json.loads(body)
    except Exception:
        return False
    return value == {"error": "the input length exceeds the context length"}


def validate_successful_context_use(
    response: dict[str, Any],
    *,
    num_ctx: int,
    reserved_output_tokens: int,
    safety_margin_tokens: int,
) -> dict[str, int]:
    """Reject missing accounting or a success without output headroom."""

    prompt_tokens = response.get("prompt_eval_count")
    output_tokens = response.get("eval_count")
    if type(prompt_tokens) is not int or prompt_tokens <= 0:
        raise PromptLimitError("prompt_limit_prompt_token_count_missing")
    if type(output_tokens) is not int or output_tokens < 0:
        raise PromptLimitError("prompt_limit_output_token_count_missing")
    if (
        type(reserved_output_tokens) is not int
        or reserved_output_tokens < 0
        or type(safety_margin_tokens) is not int
        or safety_margin_tokens < 0
    ):
        raise PromptLimitError("prompt_limit_invalid_token_reserve")
    if prompt_tokens >= num_ctx:
        raise PromptLimitError("prompt_limit_input_context_saturated")
    if prompt_tokens + reserved_output_tokens + safety_margin_tokens > num_ctx:
        raise PromptLimitError("prompt_limit_output_headroom_insufficient")
    return {
        "prompt_eval_count": prompt_tokens,
        "eval_count": output_tokens,
        "reserved_output_tokens": reserved_output_tokens,
        "safety_margin_tokens": safety_margin_tokens,
        "num_ctx": num_ctx,
    }


def exact_consensus(values: Sequence[Any]) -> Any:
    """Return the value only when every canonical JSON value is identical."""

    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)) or not values:
        raise PromptLimitError("prompt_limit_consensus_values_missing")
    encodings = [canonical_bytes(value) for value in values]
    if any(value != encodings[0] for value in encodings[1:]):
        raise PromptLimitError("prompt_limit_exact_consensus_failed")
    return values[0]
