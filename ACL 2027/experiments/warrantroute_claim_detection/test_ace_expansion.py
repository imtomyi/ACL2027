"""Offline expansion fixtures, never model or experiment evidence."""

import copy
import csv
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

import ace_flaw_contract as c
import plan_gemma_8h as design
import run_ace_flaw_8h as run
import test_ace_8h_runtime as fixtures


class ExpansionTests(unittest.TestCase):
    def setUp(self):
        self.plan = design.read(design.PLAN)
        self.plan["selection"].update(policy="remaining_prior_dev20_eval100_excluding_v2",
            evaluation_n=80, exclude_run="previous", exclude_inputs_sha256="placeholder")
        self.plan["expected"] = design.expected_counts(self.plan)
        self.fixture = fixtures.RuntimeTests()
        self.fixture.setUp()

    def data(self):
        return {ds: {phase: [{**self.fixture.packet(), "packet_id": f"{ds}-{phase}-{i}"}
                            for i in range(n)]
                     for phase, n in (("development", 10), ("evaluation", 80))}
                for ds in design.DATASETS}

    def test_expansion_counts_and_matched_schedule(self):
        counts = design.workload(self.plan)
        self.assertEqual(counts["unique_packets"], 360)
        self.assertEqual(counts["core_evaluation_reviews"], 640)
        self.assertEqual(counts["all_calls_max"], 2880)
        data = self.data()
        jobs = design.evaluation_schedule({ds: [p["packet_id"] for p in x["evaluation"]]
                                          for ds, x in data.items()}, 3, self.plan)
        self.assertEqual(len(jobs), 640)
        self.assertEqual(len({j["id"] for j in jobs}), 640)
        for a, b in zip(jobs[::2], jobs[1::2]):
            self.assertEqual(a["packet_id"], b["packet_id"])
            self.assertEqual((a["epoch"], b["epoch"]), (0, 3))

    def test_allocation_or_exclusion_drift_rejected(self):
        for key, value in (("evaluation_n", 100), ("exclude_inputs_sha256", "")):
            plan = copy.deepcopy(self.plan)
            plan["selection"][key] = value
            with self.assertRaises(ValueError):
                design.workload(plan)

    def test_development_schedule_uses_declared_size(self):
        data = self.data()
        plan = copy.deepcopy(self.plan)
        plan["selection"]["development_n"] = 3
        for ds in data:
            data[ds]["development"] = data[ds]["development"][:3]
        self.assertEqual(len(run.development_schedule(data, plan)), 36)

    def test_expanded_full_mock_schedule_and_final_denominators(self):
        with tempfile.TemporaryDirectory() as temp:
            root, data = Path(temp), self.data()
            run.write_json(root / "plan.json", self.plan)
            run.write_json(root / "inputs.private.json", data)
            run.write_json(root / "development_schedule.json", run.development_schedule(data, self.plan))
            start = time.time()
            run.write_json(root / "clock.json", {"started_unix": start, "deadline": start + 28800})
            for ds in data:
                run.snapshot(root, ds, 0, c.SEED)
            fake = self.fixture.client(root, learning={"reflection": [], "patches": [], "self_check": "No patch."})
            fake.deadline = start + 27900
            original_export = run.export
            def export_terminal(folder, terminal=None):
                return original_export(folder, terminal) if terminal else None
            with patch.object(run, "verify", return_value={}), patch.object(run, "Client", return_value=fake), \
                    patch.object(run, "export", side_effect=export_terminal):
                status = run.worker(root)
            self.assertEqual(status["development_valid"], 120)
            self.assertEqual(status["core_reviews_processed"], 640)
            self.assertEqual(status["core_reviews_planned"], 640)
            self.assertEqual(status["core_judgments_valid"], 640)
            self.assertEqual(status["optional_reviews_processed"], 40)
            self.assertEqual(status["state"], "completed_with_unresolved_quality")
            self.assertEqual(status["remaining_estimates_hours"]["core_total"], 0)
            self.assertEqual(run.read(root / "final_manifest.json")["core_expected"], 640)
            with (root / "results_table_ACE.csv").open() as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 4)
            for row in rows:
                self.assertEqual(row["Planned_N"], "80")
                self.assertEqual(row["credibility_binary_n"], "80")
                self.assertEqual(row["conformability_null"], "80")
                self.assertEqual(row["conformability_full_panel_pct"], "")
            self.assertIn("Reviews / 80", (root / "results_table_ACE.md").read_text())

    def candidate_fixture(self, root):
        source, previous = root / "candidate", root / "previous"
        inputs, old, splits = {}, {}, {}
        for ds in design.DATASETS:
            inputs[ds], old[ds], splits[ds] = {}, {}, {}
            for phase, n, old_n in (("development", 20, 10), ("evaluation", 100, 20)):
                rows = []
                for i in range(n):
                    pid = f"{ds}-{phase}-{i}"
                    evidence = {"text": f"Unique evidence {pid}", "source_id": pid, "source_record_id": pid}
                    rows.append({"packet_id": pid, "source_text_context": [evidence],
                                 "llm_generated_qualitative_claim": {"claim": "An experimental assertion"}})
                path = source / f"{ds}-{phase}.jsonl"
                run.write_text(path, "\n".join(json.dumps(v) for v in rows))
                inputs[ds][phase] = [{"packet_id": v["packet_id"]} for v in rows]
                old[ds][phase] = [{"packet_id": v["packet_id"], "task": {"evidence": v["source_text_context"]}}
                                  for v in rows[:old_n]]
                splits[ds][phase + "_file"] = str(path)
                splits[ds][phase + "_file_sha256"] = run.file_hash(path)
        run.write_json(source / "inputs.private.json", inputs)
        run.write_json(source / "manifest.json", {"splits": splits,
            "files": {"inputs.private.json": run.file_hash(source / "inputs.private.json")}})
        run.write_json(previous / "inputs.private.json", old)
        plan = copy.deepcopy(self.plan)
        plan["candidate_run"] = "candidate"
        plan["selection"].update(exclude_run=str(previous),
            exclude_inputs_sha256=run.file_hash(previous / "inputs.private.json"))
        return plan, old

    def test_selection_excludes_previous_packets_and_records(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plan, old = self.candidate_fixture(root)
            with patch.object(design, "PROJECT", root):
                audit = design.candidate_audit(plan)
            for ds, info in audit["datasets"].items():
                ids = info["candidate_ids_not_frozen"]
                self.assertEqual(len(ids["development"]), 10)
                self.assertEqual(len(ids["evaluation"]), 80)
                previous = {v["packet_id"] for rows in old[ds].values() for v in rows}
                self.assertFalse(previous & set(ids["development"] + ids["evaluation"]))
                self.assertEqual(info["overlap_with_previous_run"]["text"], 0)

    def test_selection_rejects_previous_text_even_with_new_id(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plan, old = self.candidate_fixture(root)
            old["dreaddit"]["evaluation"][0]["task"]["evidence"][0]["text"] = "Unique evidence dreaddit-evaluation-20"
            previous = root / "previous" / "inputs.private.json"
            run.write_json(previous, old, replace=True)
            plan["selection"]["exclude_inputs_sha256"] = run.file_hash(previous)
            with patch.object(design, "PROJECT", root), self.assertRaisesRegex(ValueError, "repeats previous"):
                design.candidate_audit(plan)

    def test_launch_requires_passed_preflight_before_clock_or_worker(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run.write_json(root / "runtime_config.json", {"required_smoke_report": str(root / "absent.json")})
            run.write_json(root / "inputs.private.json", self.data())
            with patch.object(run, "model_identity", return_value="same"), \
                    patch.object(run.subprocess, "Popen") as popen, self.assertRaises(FileNotFoundError):
                run.supervise_locked(root, {"model_digest": "same"})
            popen.assert_not_called()
            self.assertFalse((root / "clock.json").exists())


if __name__ == "__main__":
    unittest.main()
