#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import portkey_budget as b


class BudgetLedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.ledger_path = Path(self.temp.name) / "ledger.json"
        self.settings = b.BudgetSettings.from_environment(
            {
                "PORTKEY_BUDGET_USD": "0.01",
                "PORTKEY_REMOTE_BUDGET_ACK": b.REMOTE_BUDGET_ACK,
                "PORTKEY_RUN_ID": "budget-test",
                "PORTKEY_BUDGET_LEDGER": str(self.ledger_path),
                "PORTKEY_INPUT_USD_PER_1M_TOKENS": "1000",
                "PORTKEY_OUTPUT_USD_PER_1M_TOKENS": "1000",
                "PORTKEY_PRICING_VERIFIED_DATE": datetime.now(timezone.utc).date().isoformat(),
                "PORTKEY_PRICING_SOURCE_URL": "https://example.test/pricing",
                "PORTKEY_PRICING_ACK": b.PRICING_ACK,
                "PORTKEY_COST_SAFETY_MULTIPLIER": "1",
                "PORTKEY_INPUT_OVERHEAD_TOKENS": "0",
                "PORTKEY_OUTPUT_OVERHEAD_TOKENS": "0",
            },
            default_ledger_path=self.ledger_path,
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_cap_cannot_exceed_100(self):
        values = self._environment()
        values["PORTKEY_BUDGET_USD"] = "100.01"
        with self.assertRaises(b.PortkeyBudgetError):
            b.BudgetSettings.from_environment(values, default_ledger_path=self.ledger_path)

    def test_reservation_blocks_request_that_would_cross_cap(self):
        ledger = b.BudgetLedger(self.settings)
        first = ledger.reserve(prompt="1234", max_tokens=4, model="model", trace_id="one")
        with self.assertRaises(b.PortkeyBudgetExceeded):
            ledger.reserve(prompt="1", max_tokens=2, model="model", trace_id="two")
        ledger.settle(
            first["reservation_id"],
            usage={"prompt_tokens": 2, "completion_tokens": 2},
            outcome="success",
        )
        self.assertEqual(Decimal(ledger.status()["committed_usd"]), Decimal("0.004"))

    def test_missing_usage_commits_full_reservation(self):
        ledger = b.BudgetLedger(self.settings)
        item = ledger.reserve(prompt="1", max_tokens=2, model="model", trace_id=None)
        settled = ledger.settle(item["reservation_id"], usage=None, outcome="timeout")
        self.assertEqual(settled["committed_usd"], item["reserved_usd"])
        stored = json.loads(self.ledger_path.read_text())
        self.assertEqual(stored["entries"][0]["settlement"], "full_reservation_committed")

    def _environment(self) -> dict[str, str]:
        return {
            "PORTKEY_BUDGET_USD": "0.01",
            "PORTKEY_REMOTE_BUDGET_ACK": b.REMOTE_BUDGET_ACK,
            "PORTKEY_RUN_ID": "budget-test",
            "PORTKEY_BUDGET_LEDGER": str(self.ledger_path),
            "PORTKEY_INPUT_USD_PER_1M_TOKENS": "1000",
            "PORTKEY_OUTPUT_USD_PER_1M_TOKENS": "1000",
            "PORTKEY_PRICING_VERIFIED_DATE": datetime.now(timezone.utc).date().isoformat(),
            "PORTKEY_PRICING_SOURCE_URL": "https://example.test/pricing",
            "PORTKEY_PRICING_ACK": b.PRICING_ACK,
        }


if __name__ == "__main__":
    unittest.main()
