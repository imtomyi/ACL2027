#!/usr/bin/env python3
"""Minimal, secret-safe Portkey AI Gateway adapter for future experiments."""

from __future__ import annotations

import dataclasses
import json
import os
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Mapping

from portkey_budget import BudgetLedger, BudgetSettings, PortkeyBudgetError


DEFAULT_BASE_URL = "https://api.portkey.ai/v1"
EXTERNAL_DATA_ACK = "I_ACKNOWLEDGE_EXTERNAL_TRANSMISSION"
ALLOWED_RESPONSE_FORMATS = {"json_object", "json_schema", "text"}
DEFAULT_LEDGER_PATH = (
    Path(__file__).resolve().parents[3]
    / "Storage"
    / "portkey_budget"
    / "portkey_experiment_budget_v1.json"
)


class PortkeyConfigurationError(ValueError):
    pass


class PortkeyRequestError(RuntimeError):
    pass


def _text(environment: Mapping[str, str], name: str) -> str | None:
    value = environment.get(name, "").strip()
    return value or None


@dataclasses.dataclass(frozen=True)
class PortkeySettings:
    api_key: str
    model: str
    provider: str | None
    config: str | None
    base_url: str
    timeout_seconds: int
    response_format: str
    external_data_acknowledged: bool
    budget: BudgetSettings

    @classmethod
    def from_environment(
        cls,
        environment: Mapping[str, str] | None = None,
        *,
        require_external_data_ack: bool = True,
    ) -> "PortkeySettings":
        environment = os.environ if environment is None else environment
        missing = [name for name in ("PORTKEY_API_KEY", "PORTKEY_MODEL") if not _text(environment, name)]
        provider = _text(environment, "PORTKEY_PROVIDER")
        config = _text(environment, "PORTKEY_CONFIG")
        if not provider and not config:
            missing.append("PORTKEY_PROVIDER_or_PORTKEY_CONFIG")
        if missing:
            raise PortkeyConfigurationError("missing:" + ",".join(missing))
        if provider and config:
            raise PortkeyConfigurationError("set_exactly_one_of:PORTKEY_PROVIDER,PORTKEY_CONFIG")

        base_url = (_text(environment, "PORTKEY_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        parsed = urllib.parse.urlparse(base_url)
        if not parsed.scheme or not parsed.netloc or parsed.query or parsed.fragment:
            raise PortkeyConfigurationError("invalid:PORTKEY_BASE_URL")
        custom_url = base_url != DEFAULT_BASE_URL
        if parsed.scheme != "https" and environment.get("PORTKEY_ALLOW_INSECURE_HTTP") != "YES":
            raise PortkeyConfigurationError("insecure_http_requires:PORTKEY_ALLOW_INSECURE_HTTP=YES")
        if custom_url and environment.get("PORTKEY_ALLOW_CUSTOM_BASE_URL") != "YES":
            raise PortkeyConfigurationError("custom_url_requires:PORTKEY_ALLOW_CUSTOM_BASE_URL=YES")

        try:
            timeout = int(environment.get("PORTKEY_TIMEOUT_SECONDS", "240"))
        except ValueError as exc:
            raise PortkeyConfigurationError("invalid:PORTKEY_TIMEOUT_SECONDS") from exc
        if not 1 <= timeout <= 3600:
            raise PortkeyConfigurationError("out_of_range:PORTKEY_TIMEOUT_SECONDS")

        response_format = environment.get("PORTKEY_RESPONSE_FORMAT", "json_object").strip()
        if response_format not in ALLOWED_RESPONSE_FORMATS:
            raise PortkeyConfigurationError("invalid:PORTKEY_RESPONSE_FORMAT")
        acknowledged = environment.get("PORTKEY_ALLOW_EXTERNAL_DATA") == EXTERNAL_DATA_ACK
        if require_external_data_ack and not acknowledged:
            raise PortkeyConfigurationError(
                "external_data_ack_required:PORTKEY_ALLOW_EXTERNAL_DATA=" + EXTERNAL_DATA_ACK
            )
        provider = provider.removeprefix("@") if provider else None
        if provider and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", provider):
            raise PortkeyConfigurationError("invalid:PORTKEY_PROVIDER")
        if config and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", config):
            raise PortkeyConfigurationError("invalid:PORTKEY_CONFIG")
        try:
            budget = BudgetSettings.from_environment(
                environment, default_ledger_path=DEFAULT_LEDGER_PATH
            )
        except PortkeyBudgetError as exc:
            raise PortkeyConfigurationError(str(exc)) from exc
        return cls(
            api_key=_text(environment, "PORTKEY_API_KEY") or "",
            model=_text(environment, "PORTKEY_MODEL") or "",
            provider=provider,
            config=config,
            base_url=base_url,
            timeout_seconds=timeout,
            response_format=response_format,
            external_data_acknowledged=acknowledged,
            budget=budget,
        )

    def headers(self, *, trace_id: str | None = None) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "x-portkey-api-key": self.api_key,
            "x-portkey-metadata": json.dumps(
                {"_environment": "acl2027-experiment", "experiment_run_id": self.budget.run_id},
                separators=(",", ":"),
            ),
        }
        if self.provider:
            headers["x-portkey-provider"] = "@" + self.provider
        if self.config:
            headers["x-portkey-config"] = self.config
        if trace_id:
            headers["x-portkey-trace-id"] = trace_id
        return headers

    def redacted_snapshot(self) -> dict[str, Any]:
        return {
            "backend": "portkey_ai_gateway",
            "base_url": self.base_url,
            "model": self.model,
            "provider": "@" + self.provider if self.provider else None,
            "config": self.config,
            "timeout_seconds": self.timeout_seconds,
            "response_format": self.response_format,
            "external_data_acknowledged": self.external_data_acknowledged,
            "api_key_present": bool(self.api_key),
            "api_key_value_recorded": False,
            "budget": self.budget.redacted_snapshot(),
        }


def build_chat_body(
    settings: PortkeySettings,
    *,
    prompt: str,
    temperature: float,
    top_p: float,
    max_tokens: int,
    response_schema: dict[str, Any] | None = None,
    schema_name: str = "experiment_response",
) -> dict[str, Any]:
    if not prompt:
        raise PortkeyConfigurationError("empty_prompt")
    if response_schema is not None and settings.response_format == "text":
        raise PortkeyConfigurationError("response_schema_incompatible_with_text_mode")
    body: dict[str, Any] = {
        "model": settings.model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": max_tokens,
        "stream": False,
    }
    if settings.response_format == "json_object":
        body["response_format"] = {"type": "json_object"}
    elif settings.response_format == "json_schema":
        if response_schema is None:
            raise PortkeyConfigurationError("json_schema_mode_requires_response_schema")
        body["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": schema_name, "strict": True, "schema": response_schema},
        }
    return body


def chat_completion(
    settings: PortkeySettings,
    *,
    prompt: str,
    temperature: float,
    top_p: float,
    max_tokens: int,
    response_schema: dict[str, Any] | None = None,
    schema_name: str = "experiment_response",
    trace_id: str | None = None,
) -> dict[str, Any]:
    body = build_chat_body(
        settings,
        prompt=prompt,
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
        response_schema=response_schema,
        schema_name=schema_name,
    )
    ledger = BudgetLedger(settings.budget)
    reservation = ledger.reserve(
        prompt=prompt,
        max_tokens=max_tokens,
        model=settings.model,
        trace_id=trace_id,
    )
    request = urllib.request.Request(
        settings.base_url + "/chat/completions",
        data=json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
        headers=settings.headers(trace_id=trace_id),
        method="POST",
    )
    try:
        with urllib.request.urlopen(
            request,
            timeout=settings.timeout_seconds,
            context=ssl.create_default_context(),
        ) as response:
            raw = response.read()
            request_id = response.headers.get("x-request-id") or response.headers.get("x-portkey-request-id")
    except urllib.error.HTTPError as exc:
        ledger.settle(reservation["reservation_id"], usage=None, outcome=f"http_{exc.code}")
        detail = exc.read(2048).decode("utf-8", errors="replace")
        raise PortkeyRequestError(f"http_{exc.code}:{detail}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        ledger.settle(reservation["reservation_id"], usage=None, outcome=type(exc).__name__)
        raise PortkeyRequestError(type(exc).__name__ + ":" + str(exc)) from exc
    try:
        payload = json.loads(raw)
        choice = payload["choices"][0]
        content = choice["message"]["content"]
        if not isinstance(content, str) or not content:
            raise ValueError("empty_completion_content")
    except (json.JSONDecodeError, KeyError, IndexError, TypeError, ValueError) as exc:
        ledger.settle(reservation["reservation_id"], usage=None, outcome="invalid_gateway_response")
        raise PortkeyRequestError("invalid_gateway_response:" + str(exc)) from exc
    settlement = ledger.settle(
        reservation["reservation_id"], usage=payload.get("usage"), outcome="success"
    )
    return {
        "backend": "portkey_ai_gateway",
        "model": payload.get("model", settings.model),
        "content": content,
        "finish_reason": choice.get("finish_reason"),
        "usage": payload.get("usage"),
        "response_id": payload.get("id"),
        "request_id": request_id,
        "created": payload.get("created"),
        "budget": {
            "reservation_id": reservation["reservation_id"],
            "settlement": settlement["settlement"],
            "committed_usd": settlement["committed_usd"],
        },
    }


def probe(settings: PortkeySettings) -> dict[str, Any]:
    return chat_completion(
        settings,
        prompt='Return exactly this JSON object: {"portkey_probe":true}',
        temperature=0,
        top_p=1,
        max_tokens=32,
        response_schema={
            "type": "object",
            "additionalProperties": False,
            "required": ["portkey_probe"],
            "properties": {"portkey_probe": {"const": True}},
        } if settings.response_format == "json_schema" else None,
        schema_name="portkey_probe",
        trace_id="acl2027-portkey-preflight",
    )
