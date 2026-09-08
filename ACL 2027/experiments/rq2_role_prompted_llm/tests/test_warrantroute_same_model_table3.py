"""Same-model assignment, blinded measurement, retry and export tests."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import run_warrantroute_same_model_table3 as audit
from test_warrantroute_loop_n100 import FakeClient, packet, report


class SameModelTests(unittest.TestCase):
    def setUp(self):
        self.config = audit.quality.read_json(audit.CONFIG)
        self.policy = audit.quality.read_json(audit.WORKSPACE / self.config["gate_policy"])

    def client(self, responder):
        config = copy.deepcopy(self.config)
        config["configurations"]["qwen_led"] = config["configurations"]["qwen_only"]
        return FakeClient(config, responder)

    def test_assignments_and_other_settings_match(self):
        base = audit.loop.read_json(audit.loop.DEFAULT_CONFIG)
        for field in ("runtime", "prompt_file", "guide_file", "gate_policy", "datasets", "model_digests"):
            self.assertEqual(self.config[field], base[field])
        for name, model in (("qwen_only", "qwen3:8b"), ("llama_only", "llama3.1:8b"), ("gemma_only", "gemma3:4b")):
            self.assertEqual(set(self.config["configurations"][name]), set(audit.loop.runtime.ROLES))
            self.assertEqual(set(self.config["configurations"][name].values()), {model})

    def test_same_model_requires_opt_in(self):
        client = self.client(lambda *_: report())
        self.assertEqual(audit.loop.runtime.run_packet(packet(), client, self.policy)["status"], "accepted")
        client = self.client(lambda *_: report())
        client.config.pop("model_assignment_policy")
        result = audit.loop.runtime.run_packet(packet(), client, self.policy)
        self.assertIn("no_cross_family_auditor", result["error"])
        self.assertEqual(client.records, [])

    def test_mixed_model_rejected_under_same_model_policy(self):
        client = self.client(lambda *_: report())
        client.assignment["reviser"] = "gemma3:4b"
        self.assertEqual(audit.loop.runtime.run_packet(packet(), client, self.policy)["status"], "quarantined")
        self.assertEqual(client.records, [])

    def test_revision_requires_owner_recheck(self):
        def respond(role, stage, payload):
            if role == "reviser":
                return {"claim": "Revised fixture", "central_concept": "Fixture", "scope": "Limited",
                        "evidence_ids": ["E1"], "counterevidence_ids": [], "uncertainty": "Limited",
                        "issue_responses": {i["issue_id"]: "Changed scope" for i in payload["issues"]}}
            return report("unsupported_inference") if stage == "initial" else report(resolved=[i["issue_id"] for i in payload["assigned_issues"]])
        client = self.client(respond)
        result = audit.loop.runtime.run_packet(packet(), client, self.policy)
        self.assertEqual(result["status"], "accepted")
        self.assertEqual(result["revision_rounds"], 1)
        self.assertIn(("evidence_scout", "recheck-1"), [(r, s) for r, s, _ in client.requests])
        self.assertEqual(result["original_detected_flags"], ["unsupported_inference"])

    def test_canary_covers_12_cells_without_duplicates(self):
        manifest = {"seeds": [1], "configurations": list(audit.MODELS), "methods": ["warrantroute"], "cell_canary_first": True}
        packets = {d: [{"packet_id": str(i)} for i in range(100)] for d in audit.LABELS}
        jobs = list(audit.loop.jobs(manifest, packets))
        keys = [(d, s, n, m, p["packet_id"]) for d, s, n, m, p in jobs]
        self.assertEqual(len(set(keys)), 1200)
        self.assertEqual(len({(d, n) for d, _, n, _, _ in jobs[:12]}), 12)

    def fixture_unit(self, missing=False):
        p = packet()
        p["source_text_context"][0].update(local_context=None, metadata={})
        context, aliases = audit.quality.sanitize_packet(p)
        inputs = {"dreaddit": {p["packet_id"]: {"context": context, "aliases": aliases}}}
        result = audit.loop.runtime.run_packet(p, self.client(lambda *_: report()), self.policy)
        result["result_sha256"] = "fixture"
        if missing:
            result["audit_history"].pop()
        result["audit_history"].append({"role": "evidence_scout", "stage": "recheck-1", "report": report("lost_negative_case")})
        return audit.make_unit(("dreaddit", 1, "qwen_only", "warrantroute", p), result, inputs, self.config)

    def test_projection_excludes_rechecks_labels_and_numeric_scores(self):
        unit = self.fixture_unit()
        payload = json.dumps(unit["payload"])
        for word in ("SECRET", "qwen", "proposer", "evidential_credibility", "theme_name", "lost_negative_case"):
            self.assertNotIn(word, payload)
        self.assertTrue(unit["initial_bundle_complete"])
        self.assertEqual(len(unit["payload"]["review_bundle"]), 2)
        self.assertFalse(self.fixture_unit(missing=True)["initial_bundle_complete"])

    def test_first_valid_false_or_null_is_never_retried(self):
        for outcome in (False, None):
            with self.subTest(outcome=outcome), tempfile.TemporaryDirectory() as temp:
                directory = Path(temp)
                audit.quality.atomic_write(directory / "prompt.txt", "Fixture only")
                response = {"model": "qwen3:8b", "done": True, "done_reason": "stop", "prompt_eval_count": 100,
                            "response": json.dumps({"credibility": outcome, "conformability": outcome,
                                                    "credibility_rationale": "Fixture CLAIM assessment.",
                                                    "conformability_rationale": "Fixture CLAIM assessment."})}
                with patch.object(audit.quality, "api", return_value=response) as api, \
                     patch.object(audit.quality, "log_position", return_value=(1, 0)), \
                     patch.object(audit.quality, "truncation_since", return_value=False):
                    for _ in range(2):
                        result = audit.judge_one(directory, {"sha256": "fixture", "judge_attempt_limit": 3}, self.fixture_unit(),
                                                 audit.quality.read_json(audit.BASE / "design_snapshot.json"),
                                                 audit.quality.read_json(audit.BASE / "schema_snapshot.json"))
                        self.assertIs(result["decision"]["credibility"], outcome)
                    self.assertEqual(api.call_count, 1)

    def test_failed_attempts_are_bounded_and_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            audit.quality.atomic_write(directory / "prompt.txt", "Fixture only")
            with patch.object(audit.quality, "api", side_effect=TimeoutError("fixture")) as api, \
                 patch.object(audit.quality, "log_position", return_value=(1, 0)):
                for _ in range(2):
                    result = audit.judge_one(directory, {"sha256": "fixture", "judge_attempt_limit": 3}, self.fixture_unit(),
                                             audit.quality.read_json(audit.BASE / "design_snapshot.json"),
                                             audit.quality.read_json(audit.BASE / "schema_snapshot.json"))
                    self.assertIsNone(result["decision"])
                self.assertEqual(api.call_count, 3)
                self.assertEqual(len(list(directory.glob("units/*/attempts/*.json"))), 3)

    def test_export_preserves_36_baselines_and_unresolved_cells(self):
        rows = [["Dataset", "Method", "Model", "TP/N", "Recall", "Credibility", "Conformability"]]
        metrics, summary = [], {"rows": []}
        for dataset, label in audit.LABELS.items():
            corpus = self.config["datasets"][dataset]["corpus_id"]
            for method in ("Generalist", "Fixed role", "All roles", "WarrantRoute"):
                for name, model in audit.MODELS.items():
                    rows.append([label, method, model, "old", "old", "old", "old"])
                    if method == "WarrantRoute":
                        metrics.append({"dataset": dataset, "configuration": name, "n": 100, "tp": 50,
                                        "recall": .5, "recall_cluster_interval": [.4, .6]})
                        summary["rows"].append({"corpus_id": corpus, "reviewer_model_id": self.config["configurations"][name]["proposer"],
                                                "planned": 100, "credibility": {"true": 50, "false": 50, "unresolved": 0, "percent": 50},
                                                "conformability": {"true": 50, "false": 49, "unresolved": 1, "percent": None}})
        output = audit.export_rows(rows, metrics, summary)
        for old, new in zip(rows[1:], output[1:]):
            if old[1] == "WarrantRoute":
                self.assertEqual(new[3:], ["50/100", "50.0 [40.0, 60.0]", "50.0", "N/A"])
            else:
                self.assertEqual(old, new)

    def test_runtime_parameter_normalization_preserves_values(self):
        first = {"parameters": "stop a\nstop b\ntop_p 1"}
        second = {"parameters": "top_p 1\nstop b\nstop a"}
        self.assertEqual(audit.normalized_runtime(first), audit.normalized_runtime(second))
        second["parameters"] = "top_p .9\nstop b\nstop a"
        self.assertNotEqual(audit.normalized_runtime(first), audit.normalized_runtime(second))


if __name__ == "__main__":
    unittest.main()
