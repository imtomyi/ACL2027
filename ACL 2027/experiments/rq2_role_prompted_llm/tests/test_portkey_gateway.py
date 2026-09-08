#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import portkey_gateway as p
import portkey_budget as b


def environment(**overrides: str) -> dict[str, str]:
    ledger = str(Path(tempfile.gettempdir()) / "portkey-gateway-unit-test-ledger.json")
    result = {
        "PORTKEY_API_KEY": "secret-test-value",
        "PORTKEY_PROVIDER": "@provider-prod",
        "PORTKEY_MODEL": "model-id",
        "PORTKEY_ALLOW_EXTERNAL_DATA": p.EXTERNAL_DATA_ACK,
        "PORTKEY_BUDGET_USD": "100.00",
        "PORTKEY_REMOTE_BUDGET_ACK": b.REMOTE_BUDGET_ACK,
        "PORTKEY_RUN_ID": "unit-test",
        "PORTKEY_BUDGET_LEDGER": ledger,
        "PORTKEY_INPUT_USD_PER_1M_TOKENS": "1.00",
        "PORTKEY_OUTPUT_USD_PER_1M_TOKENS": "2.00",
        "PORTKEY_PRICING_VERIFIED_DATE": datetime.now(timezone.utc).date().isoformat(),
        "PORTKEY_PRICING_SOURCE_URL": "https://example.test/pricing",
        "PORTKEY_PRICING_ACK": b.PRICING_ACK,
    }
    result.update(overrides)
    return result


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = json.dumps(payload).encode()
        self.headers = {"x-portkey-request-id": "request-1"}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.payload


class PortkeyGatewayTests(unittest.TestCase):
    def setUp(self):
        ledger = Path(environment()["PORTKEY_BUDGET_LEDGER"])
        ledger.unlink(missing_ok=True)
        ledger.with_suffix(ledger.suffix + ".lock").unlink(missing_ok=True)

    def tearDown(self):
        self.setUp()

    def test_requires_key_model_selector_and_external_ack(self):
        for value in ({}, environment(PORTKEY_API_KEY=""), environment(PORTKEY_MODEL=""),
                      environment(PORTKEY_PROVIDER=""), environment(PORTKEY_ALLOW_EXTERNAL_DATA="NO")):
            with self.subTest(value=value), self.assertRaises(p.PortkeyConfigurationError):
                p.PortkeySettings.from_environment(value)

    def test_provider_and_config_are_mutually_exclusive(self):
        with self.assertRaises(p.PortkeyConfigurationError):
            p.PortkeySettings.from_environment(environment(PORTKEY_CONFIG="cf-one"))

    def test_custom_or_insecure_url_requires_explicit_opt_in(self):
        for value in (environment(PORTKEY_BASE_URL="https://gateway.example/v1"),
                      environment(PORTKEY_BASE_URL="http://localhost:8787/v1")):
            with self.subTest(value=value), self.assertRaises(p.PortkeyConfigurationError):
                p.PortkeySettings.from_environment(value)

    def test_snapshot_never_contains_secret(self):
        settings = p.PortkeySettings.from_environment(environment())
        snapshot = json.dumps(settings.redacted_snapshot())
        self.assertNotIn("secret-test-value", snapshot)
        self.assertEqual(settings.headers()["x-portkey-provider"], "@provider-prod")
        self.assertEqual(
            json.loads(settings.headers()["x-portkey-metadata"])["experiment_run_id"],
            "unit-test",
        )

    def test_request_body_modes(self):
        settings = p.PortkeySettings.from_environment(environment())
        body = p.build_chat_body(settings, prompt="prompt", temperature=0, top_p=1, max_tokens=64)
        self.assertEqual(body["response_format"], {"type": "json_object"})
        self.assertEqual(body["messages"], [{"role": "user", "content": "prompt"}])
        schema_settings = p.PortkeySettings.from_environment(
            environment(PORTKEY_RESPONSE_FORMAT="json_schema")
        )
        schema = {"type": "object"}
        body = p.build_chat_body(schema_settings, prompt="prompt", temperature=0, top_p=1,
                                 max_tokens=64, response_schema=schema)
        self.assertEqual(body["response_format"]["json_schema"]["schema"], schema)

    @mock.patch("portkey_gateway.urllib.request.urlopen")
    def test_completion_normalizes_response_without_secret(self, urlopen):
        urlopen.return_value = FakeResponse({
            "id": "response-1", "model": "model-id", "created": 1,
            "choices": [{"message": {"content": "{\"ok\":true}"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 4},
        })
        settings = p.PortkeySettings.from_environment(environment())
        result = p.chat_completion(settings, prompt="prompt", temperature=0, top_p=1, max_tokens=64)
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.portkey.ai/v1/chat/completions")
        self.assertEqual(result["content"], '{"ok":true}')
        self.assertEqual(result["request_id"], "request-1")
        self.assertEqual(result["budget"]["settlement"], "usage_tokens_settled")
        self.assertNotIn("secret-test-value", json.dumps(result))


if __name__ == "__main__":
    unittest.main()
