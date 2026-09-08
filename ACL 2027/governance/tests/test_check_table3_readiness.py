from __future__ import annotations

import copy
import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path


TEST_FILE = Path(__file__).resolve()
GOVERNANCE_ROOT = TEST_FILE.parents[1]
SCRIPT_DIR = GOVERNANCE_ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import check_table3_readiness as checker  # noqa: E402


class Table3ReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        path = GOVERNANCE_ROOT / "templates/table3_project_governance_v1.template.json"
        cls.template = json.loads(path.read_text(encoding="utf-8"))
        cls.as_of = datetime(2026, 9, 2, tzinfo=timezone.utc)

    def test_template_has_four_corpora_and_forty_pending_gates(self) -> None:
        report = checker.build_report(
            copy.deepcopy(self.template),
            record_sha256="0" * 64,
            as_of=self.as_of,
        )
        self.assertEqual(report["required_corpus_count"], 4)
        self.assertEqual(report["required_gate_count"], 40)
        self.assertEqual(report["completed_gate_count"], 0)
        self.assertFalse(report["all_real_corpora_ready"])
        self.assertEqual(tuple(report["corpora"]), checker.CORPORA)

    def test_authorization_flag_does_not_replace_gate_evidence(self) -> None:
        record = copy.deepcopy(self.template)
        record["record_status"] = "local_evidence_record"
        record["record_id"] = "T3-GOV-TEST"
        record["responsible_owner_id"] = "OWNER_TEST"
        record["execution_authorized"] = True
        report = checker.build_report(
            record,
            record_sha256="0" * 64,
            as_of=self.as_of,
        )
        self.assertFalse(report["all_gate_evidence_ready"])
        self.assertFalse(report["all_real_corpora_ready"])

    def test_corpus_order_drift_is_rejected(self) -> None:
        record = copy.deepcopy(self.template)
        record["corpus_lanes"] = {
            key: record["corpus_lanes"][key]
            for key in reversed(checker.CORPORA)
        }
        with self.assertRaisesRegex(
            checker.Table3ReadinessError, "governance_corpus_order_invalid"
        ):
            checker.build_report(
                record,
                record_sha256="0" * 64,
                as_of=self.as_of,
            )


if __name__ == "__main__":
    unittest.main()
