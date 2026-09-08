#!/usr/bin/env python3
"""Concurrency-safe local USD budget guard for Portkey experiment requests."""

from __future__ import annotations

import dataclasses
import datetime as dt
import fcntl
import json
import os
import tempfile
import urllib.parse
import uuid
from decimal import ROUND_CEILING, Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Mapping


HARD_MAX_BUDGET_USD = Decimal("100.00")
REMOTE_BUDGET_ACK = "I_SET_A_DEDICATED_PORTKEY_KEY_HARD_CAP_TO_100_USD_NO_RESET"
PRICING_ACK = "I_VERIFIED_CURRENT_MODEL_TOKEN_PRICING"
MILLION = Decimal("1000000")
MONEY_PLACES = Decimal("0.000000000001")


class PortkeyBudgetError(RuntimeError):
    pass


class PortkeyBudgetExceeded(PortkeyBudgetError):
    pass


def _decimal(environment: Mapping[str, str], name: str) -> Decimal:
    value = environment.get(name, "").strip()
    try:
        parsed = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise PortkeyBudgetError(f"invalid:{name}") from exc
    if not parsed.is_finite() or parsed < 0:
        raise PortkeyBudgetError(f"invalid:{name}")
    return parsed


def _money(value: Decimal) -> str:
    return format(value.quantize(MONEY_PLACES, rounding=ROUND_CEILING), "f")


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


@dataclasses.dataclass(frozen=True)
class BudgetSettings:
    cap_usd: Decimal
    input_usd_per_million_tokens: Decimal
    output_usd_per_million_tokens: Decimal
    safety_multiplier: Decimal
    input_overhead_tokens: int
    output_overhead_tokens: int
    ledger_path: Path
    run_id: str
    pricing_verified_date: str
    pricing_source_url: str

    @classmethod
    def from_environment(
        cls,
        environment: Mapping[str, str],
        *,
        default_ledger_path: Path,
    ) -> "BudgetSettings":
        required = (
            "PORTKEY_BUDGET_USD",
            "PORTKEY_INPUT_USD_PER_1M_TOKENS",
            "PORTKEY_OUTPUT_USD_PER_1M_TOKENS",
            "PORTKEY_RUN_ID",
            "PORTKEY_PRICING_VERIFIED_DATE",
            "PORTKEY_PRICING_SOURCE_URL",
        )
        missing = [name for name in required if not environment.get(name, "").strip()]
        if missing:
            raise PortkeyBudgetError("missing:" + ",".join(missing))
        if environment.get("PORTKEY_REMOTE_BUDGET_ACK", "").strip() != REMOTE_BUDGET_ACK:
            raise PortkeyBudgetError(
                "remote_budget_ack_required:PORTKEY_REMOTE_BUDGET_ACK=" + REMOTE_BUDGET_ACK
            )
        if environment.get("PORTKEY_PRICING_ACK", "").strip() != PRICING_ACK:
            raise PortkeyBudgetError("pricing_ack_required:PORTKEY_PRICING_ACK=" + PRICING_ACK)

        cap = _decimal(environment, "PORTKEY_BUDGET_USD")
        if cap <= 0 or cap > HARD_MAX_BUDGET_USD:
            raise PortkeyBudgetError("PORTKEY_BUDGET_USD_must_be_in_range:(0,100]")
        input_rate = _decimal(environment, "PORTKEY_INPUT_USD_PER_1M_TOKENS")
        output_rate = _decimal(environment, "PORTKEY_OUTPUT_USD_PER_1M_TOKENS")
        if input_rate <= 0 or output_rate <= 0:
            raise PortkeyBudgetError("token_prices_must_be_positive")

        try:
            verified_date = dt.date.fromisoformat(environment["PORTKEY_PRICING_VERIFIED_DATE"].strip())
        except ValueError as exc:
            raise PortkeyBudgetError("invalid:PORTKEY_PRICING_VERIFIED_DATE") from exc
        today = dt.datetime.now(dt.timezone.utc).date()
        if verified_date > today or (today - verified_date).days > 7:
            raise PortkeyBudgetError("pricing_verification_must_be_within_7_days")
        pricing_source = environment["PORTKEY_PRICING_SOURCE_URL"].strip()
        parsed_source = urllib.parse.urlparse(pricing_source)
        if (
            parsed_source.scheme != "https"
            or not parsed_source.netloc
            or parsed_source.username
            or parsed_source.password
            or parsed_source.query
            or parsed_source.fragment
        ):
            raise PortkeyBudgetError("PORTKEY_PRICING_SOURCE_URL_must_be_public_https_without_query")

        safety_multiplier = _decimal_with_default(
            environment, "PORTKEY_COST_SAFETY_MULTIPLIER", "1.10"
        )
        if safety_multiplier < 1:
            raise PortkeyBudgetError("PORTKEY_COST_SAFETY_MULTIPLIER_must_be_at_least_1")
        input_overhead = _integer_with_default(
            environment, "PORTKEY_INPUT_OVERHEAD_TOKENS", 2048
        )
        output_overhead = _integer_with_default(
            environment, "PORTKEY_OUTPUT_OVERHEAD_TOKENS", 256
        )
        if input_overhead < 0 or output_overhead < 0:
            raise PortkeyBudgetError("budget_token_overheads_must_be_nonnegative")

        run_id = environment["PORTKEY_RUN_ID"].strip()
        if not run_id.replace("-", "").replace("_", "").isalnum():
            raise PortkeyBudgetError("invalid:PORTKEY_RUN_ID")
        ledger_text = environment.get("PORTKEY_BUDGET_LEDGER", "").strip()
        ledger_path = Path(ledger_text).expanduser() if ledger_text else default_ledger_path
        if not ledger_path.is_absolute():
            raise PortkeyBudgetError("PORTKEY_BUDGET_LEDGER_must_be_absolute")
        return cls(
            cap_usd=cap,
            input_usd_per_million_tokens=input_rate,
            output_usd_per_million_tokens=output_rate,
            safety_multiplier=safety_multiplier,
            input_overhead_tokens=input_overhead,
            output_overhead_tokens=output_overhead,
            ledger_path=ledger_path,
            run_id=run_id,
            pricing_verified_date=verified_date.isoformat(),
            pricing_source_url=pricing_source,
        )

    def redacted_snapshot(self) -> dict[str, Any]:
        return {
            "hard_max_budget_usd": _money(HARD_MAX_BUDGET_USD),
            "configured_cap_usd": _money(self.cap_usd),
            "input_usd_per_1m_tokens": _money(self.input_usd_per_million_tokens),
            "output_usd_per_1m_tokens": _money(self.output_usd_per_million_tokens),
            "safety_multiplier": str(self.safety_multiplier),
            "input_overhead_tokens": self.input_overhead_tokens,
            "output_overhead_tokens": self.output_overhead_tokens,
            "ledger_path": str(self.ledger_path),
            "run_id": self.run_id,
            "pricing_verified_date": self.pricing_verified_date,
            "pricing_source_url": self.pricing_source_url,
            "remote_hard_cap_acknowledged": True,
        }


def _decimal_with_default(
    environment: Mapping[str, str], name: str, default: str
) -> Decimal:
    merged = dict(environment)
    merged[name] = environment.get(name, default)
    return _decimal(merged, name)


def _integer_with_default(
    environment: Mapping[str, str], name: str, default: int
) -> int:
    try:
        return int(environment.get(name, str(default)))
    except ValueError as exc:
        raise PortkeyBudgetError(f"invalid:{name}") from exc


class BudgetLedger:
    def __init__(self, settings: BudgetSettings):
        self.settings = settings
        self.lock_path = settings.ledger_path.with_suffix(settings.ledger_path.suffix + ".lock")

    def reserve(
        self,
        *,
        prompt: str,
        max_tokens: int,
        model: str,
        trace_id: str | None,
    ) -> dict[str, Any]:
        if max_tokens <= 0:
            raise PortkeyBudgetError("max_tokens_must_be_positive")
        input_tokens = len(prompt.encode("utf-8")) + self.settings.input_overhead_tokens
        output_tokens = max_tokens + self.settings.output_overhead_tokens
        raw = self._token_cost(input_tokens, output_tokens)
        reserved = raw * self.settings.safety_multiplier
        reservation_id = str(uuid.uuid4())
        with self._locked_ledger() as ledger:
            available = self.settings.cap_usd - _effective_total(ledger)
            if reserved > available:
                raise PortkeyBudgetExceeded(
                    "budget_exhausted:required_usd=" + _money(reserved)
                    + ",available_usd=" + _money(max(available, Decimal("0")))
                )
            entry = {
                "reservation_id": reservation_id,
                "run_id": self.settings.run_id,
                "created_at": _now(),
                "status": "reserved",
                "model": model,
                "trace_id": trace_id,
                "prompt_utf8_bytes": len(prompt.encode("utf-8")),
                "reserved_input_tokens": input_tokens,
                "reserved_output_tokens": output_tokens,
                "input_usd_per_1m_tokens": _money(
                    self.settings.input_usd_per_million_tokens
                ),
                "output_usd_per_1m_tokens": _money(
                    self.settings.output_usd_per_million_tokens
                ),
                "safety_multiplier": str(self.settings.safety_multiplier),
                "pricing_verified_date": self.settings.pricing_verified_date,
                "pricing_source_url": self.settings.pricing_source_url,
                "reserved_usd": _money(reserved),
                "committed_usd": _money(Decimal("0")),
            }
            ledger["entries"].append(entry)
            self._write_locked(ledger)
        return dict(entry)

    def settle(
        self,
        reservation_id: str,
        *,
        usage: Mapping[str, Any] | None,
        outcome: str,
    ) -> dict[str, Any]:
        with self._locked_ledger() as ledger:
            entry = next(
                (item for item in ledger["entries"] if item["reservation_id"] == reservation_id),
                None,
            )
            if entry is None:
                raise PortkeyBudgetError("unknown_reservation:" + reservation_id)
            if entry["status"] != "reserved":
                return dict(entry)
            reserved = Decimal(entry["reserved_usd"])
            token_counts = _usage_tokens(usage)
            if token_counts is None or outcome != "success":
                committed = reserved
                settlement = "full_reservation_committed"
            else:
                input_tokens, output_tokens = token_counts
                committed = self._token_cost(input_tokens, output_tokens) * self.settings.safety_multiplier
                settlement = "usage_tokens_settled"
                entry["actual_input_tokens"] = input_tokens
                entry["actual_output_tokens"] = output_tokens
                entry["token_cost_before_safety_usd"] = _money(
                    self._token_cost(input_tokens, output_tokens)
                )
            if committed > reserved:
                settlement = "reported_usage_exceeded_conservative_reservation"
                entry["budget_anomaly"] = "reported_usage_exceeded_conservative_reservation"
            entry.update(
                status="settled",
                settled_at=_now(),
                outcome=outcome,
                settlement=settlement,
                committed_usd=_money(committed),
            )
            self._write_locked(ledger)
            return dict(entry)

    def status(self) -> dict[str, Any]:
        with self._locked_ledger(write_initial=False) as ledger:
            committed = _committed_total(ledger)
            reserved = _reserved_total(ledger)
            return {
                "cap_usd": _money(self.settings.cap_usd),
                "committed_usd": _money(committed),
                "pending_reserved_usd": _money(reserved),
                "effective_total_usd": _money(committed + reserved),
                "available_usd": _money(max(self.settings.cap_usd - committed - reserved, Decimal("0"))),
                "request_count": len(ledger["entries"]),
                "pending_count": sum(1 for entry in ledger["entries"] if entry["status"] == "reserved"),
            }

    def _token_cost(self, input_tokens: int, output_tokens: int) -> Decimal:
        return (
            Decimal(input_tokens) * self.settings.input_usd_per_million_tokens
            + Decimal(output_tokens) * self.settings.output_usd_per_million_tokens
        ) / MILLION

    def _new_ledger(self) -> dict[str, Any]:
        return {
            "schema_version": "portkey-cost-ledger-v1",
            "currency": "USD",
            "cap_usd": _money(self.settings.cap_usd),
            "created_at": _now(),
            "entries": [],
        }

    def _read_locked(self) -> dict[str, Any]:
        if not self.settings.ledger_path.exists():
            return self._new_ledger()
        try:
            ledger = json.loads(self.settings.ledger_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise PortkeyBudgetError("invalid_budget_ledger:" + str(exc)) from exc
        if ledger.get("schema_version") != "portkey-cost-ledger-v1":
            raise PortkeyBudgetError("unsupported_budget_ledger_schema")
        if Decimal(str(ledger.get("cap_usd"))) != self.settings.cap_usd:
            raise PortkeyBudgetError("budget_cap_does_not_match_existing_ledger")
        if not isinstance(ledger.get("entries"), list):
            raise PortkeyBudgetError("invalid_budget_ledger_entries")
        return ledger

    def _write_locked(self, ledger: dict[str, Any]) -> None:
        path = self.settings.ledger_path
        path.parent.mkdir(parents=True, exist_ok=True)
        handle = tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, prefix=path.name + ".", delete=False
        )
        try:
            with handle:
                json.dump(ledger, handle, ensure_ascii=False, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(handle.name, path)
        finally:
            if os.path.exists(handle.name):
                os.unlink(handle.name)

    class _LockedLedger:
        def __init__(self, owner: "BudgetLedger", write_initial: bool):
            self.owner = owner
            self.write_initial = write_initial
            self.lock_file = None
            self.ledger = None

        def __enter__(self) -> dict[str, Any]:
            self.owner.lock_path.parent.mkdir(parents=True, exist_ok=True)
            self.lock_file = self.owner.lock_path.open("a+")
            fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_EX)
            self.ledger = self.owner._read_locked()
            if self.write_initial and not self.owner.settings.ledger_path.exists():
                self.owner._write_locked(self.ledger)
            return self.ledger

        def __exit__(self, *args: Any) -> None:
            if self.lock_file is not None:
                fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_UN)
                self.lock_file.close()

    def _locked_ledger(self, *, write_initial: bool = True) -> "BudgetLedger._LockedLedger":
        return self._LockedLedger(self, write_initial)


def _usage_tokens(usage: Mapping[str, Any] | None) -> tuple[int, int] | None:
    if not isinstance(usage, Mapping):
        return None
    input_value = usage.get("prompt_tokens", usage.get("input_tokens"))
    output_value = usage.get("completion_tokens", usage.get("output_tokens"))
    if isinstance(input_value, bool) or isinstance(output_value, bool):
        return None
    if not isinstance(input_value, int) or not isinstance(output_value, int):
        return None
    if input_value < 0 or output_value < 0:
        return None
    return input_value, output_value


def _committed_total(ledger: Mapping[str, Any]) -> Decimal:
    return sum(
        (Decimal(entry["committed_usd"]) for entry in ledger["entries"] if entry["status"] == "settled"),
        Decimal("0"),
    )


def _reserved_total(ledger: Mapping[str, Any]) -> Decimal:
    return sum(
        (Decimal(entry["reserved_usd"]) for entry in ledger["entries"] if entry["status"] == "reserved"),
        Decimal("0"),
    )


def _effective_total(ledger: Mapping[str, Any]) -> Decimal:
    return _committed_total(ledger) + _reserved_total(ledger)
