#!/usr/bin/env python3
"""Validate Portkey environment settings without exposing the API key."""

from __future__ import annotations

import argparse
import json

from portkey_budget import BudgetLedger, PortkeyBudgetError
from portkey_gateway import PortkeyConfigurationError, PortkeyRequestError, PortkeySettings, probe


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe", action="store_true", help="Make one minimal external model request.")
    args = parser.parse_args()
    try:
        settings = PortkeySettings.from_environment(require_external_data_ack=True)
    except PortkeyConfigurationError as exc:
        print(json.dumps({"status": "not_ready", "error": str(exc)}, indent=2))
        return 2
    try:
        budget_status = BudgetLedger(settings.budget).status()
    except PortkeyBudgetError as exc:
        print(json.dumps({"status": "not_ready", "error": str(exc)}, indent=2))
        return 2
    output = {
        "status": "configuration_ready",
        "settings": settings.redacted_snapshot(),
        "budget_status": budget_status,
        "network_probe": "not_run",
    }
    if args.probe:
        try:
            response = probe(settings)
            parsed = json.loads(response["content"])
            if parsed != {"portkey_probe": True}:
                raise PortkeyRequestError("unexpected_probe_content")
            output.update(status="probe_passed", network_probe="passed", response={
                key: response.get(key) for key in ("model", "finish_reason", "usage", "response_id", "request_id")
            })
            output["budget_status"] = BudgetLedger(settings.budget).status()
        except (PortkeyRequestError, PortkeyBudgetError, json.JSONDecodeError) as exc:
            output.update(status="probe_failed", network_probe="failed", error=str(exc))
            print(json.dumps(output, indent=2))
            return 2
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
