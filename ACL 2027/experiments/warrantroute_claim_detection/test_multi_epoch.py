"""Offline schedule invariants; fixtures are software tests, not research data."""

import copy
import importlib.util
import json
import unittest
from pathlib import Path

from plan_multi_epoch import build_plan


class ScheduleTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads(Path(__file__).with_name("multi_epoch_v4.json").read_text())
        self.inputs = {
            ds: {phase: [f"{ds}_{phase}_{i}" for i in range(n)]
                 for phase, n in (("development", 20), ("evaluation", 100))}
            for ds in self.config["datasets"]
        }
        self.plan = build_plan(self.config, self.inputs)

    def test_counts(self):
        self.assertEqual(self.plan["counts"]["unique_packets"], 480)
        self.assertEqual(self.plan["counts"]["development_episodes"], 720)
        self.assertEqual(self.plan["counts"]["evaluation_outputs"], 7440)
        self.assertEqual(self.plan["counts"]["snapshots"], 48)

    def test_deterministic_and_independent_of_input_row_order(self):
        other = copy.deepcopy(self.inputs)
        for data in other.values():
            for rows in data.values():
                rows.reverse()
        self.assertEqual(self.plan, build_plan(self.config, other))

    def test_each_packet_once_per_epoch_and_same_model_orders(self):
        for ds in self.config["datasets"]:
            orders = []
            for model in self.config["models"]:
                jobs = [j for j in self.plan["jobs"] if j["phase"] == "development"
                        and j["dataset"] == ds and j["model"] == model]
                for epoch in (1, 2, 3):
                    ids = [j["packet_id"] for j in jobs if j["epoch"] == epoch]
                    self.assertEqual(set(ids), set(self.inputs[ds]["development"]))
                    self.assertEqual(len(ids), 20)
                orders.append([j["packet_id"] for j in jobs])
            self.assertEqual(orders[0], orders[1])
            self.assertEqual(orders[0], orders[2])

    def test_memory_continues_across_epochs_and_ids_do_not_collide(self):
        chains = {}
        ids = [j["job_id"] for j in self.plan["jobs"]]
        self.assertEqual(len(ids), len(set(ids)))
        for j in self.plan["jobs"]:
            if j["phase"] != "development":
                continue
            key = (j["dataset"], j["model"])
            if key in chains:
                self.assertEqual(j["previous_memory_event"], chains[key])
            else:
                self.assertTrue(j["previous_memory_event"].startswith("seed:"))
            chains[key] = j["job_id"]
        for s in self.plan["snapshots"]:
            if s["after_epoch"] == 3:
                self.assertEqual(s["after_memory_event"], chains[(s["dataset"], s["model"])])

    def test_evaluation_is_read_only_and_matched(self):
        for ds in self.config["datasets"]:
            for model in self.config["models"]:
                panels = {}
                for j in self.plan["jobs"]:
                    if j["phase"] != "evaluation":
                        continue
                    self.assertFalse(j["memory_updates_allowed"])
                    if (j["dataset"], j["model"], j["method"]) == (ds, model, "warrantroute"):
                        panels.setdefault(j["checkpoint"], set()).add(j["packet_id"])
                self.assertEqual(panels["E0"], panels["E1"])
                self.assertEqual(panels["E1"], panels["E3"])
                self.assertEqual(len(panels["E2"]), 20)
                self.assertTrue(panels["E2"].issubset(panels["E0"]))
        phases = [j["phase"] for j in self.plan["jobs"]]
        self.assertEqual(phases, sorted(phases))

    def test_reject_duplicate_or_overlapping_packet_ids(self):
        for duplicate in (True, False):
            data = copy.deepcopy(self.inputs)
            data["dreaddit"]["development"][0] = (
                data["dreaddit"]["development"][1] if duplicate
                else data["dreaddit"]["evaluation"][0])
            with self.assertRaises(ValueError):
                build_plan(self.config, data)

    def test_reject_feedback_leak_and_unadopted_learner(self):
        for key, value in (("evaluation_feedback_to_memory", True),
                           ("playbook_reset_between_epochs", True),
                           ("score_based_early_stopping", True),
                           ("learning_policy", "one_call_editor"), ("epochs", False)):
            config = copy.deepcopy(self.config)
            config[key] = value
            with self.assertRaises(ValueError):
                build_plan(config, self.inputs)

    def test_reject_probe_only_primary_endpoint(self):
        config = copy.deepcopy(self.config)
        config["checkpoints"][1]["scope"] = "probe"
        with self.assertRaises(ValueError):
            build_plan(config, self.inputs)

    def test_config_change_changes_job_namespace(self):
        config = copy.deepcopy(self.config)
        config["order_seed"] += 1
        self.assertNotEqual(self.plan["job_namespace"], build_plan(config, self.inputs)["job_namespace"])


class EstimateTests(unittest.TestCase):
    def test_epoch_counts_do_not_multiply_unique_data_or_reference_cost(self):
        path = Path(__file__).resolve().parents[2] / "Storage/experiment_guidelines/estimate_claim_detection_runtime.py"
        spec = importlib.util.spec_from_file_location("runtime_estimator", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        rates = {m: {"warrant_seconds": 60, "baseline_group_seconds": 60,
                     "mean_seconds": 10,
                     "role_mean_seconds": {"proposer": 10, "evidence_scout": 10, "reviser": 10}}
                 for m in module.MODELS}
        for design, calls in (("merged_review", 40560), ("merged_review_and_learning", 39120)):
            result = module.estimate(rates, 20, 100, 20, 1, design, epochs=3, full_checkpoints=3)
            self.assertEqual(result["max_total_semantic_calls"], calls)
            self.assertEqual(result["unique_packets"], 480)
            self.assertEqual(result["reference_calls"], 960)
            self.assertEqual(result["development_episodes"], 720)
            self.assertEqual(result["evaluation_outputs"], 7440)
        legacy = module.estimate(rates, 20, 100, 20, 3)
        self.assertEqual(legacy["max_total_semantic_calls"], 35760)
        self.assertEqual(legacy["evaluation_outputs"], 6720)
        with self.assertRaises(ValueError):
            module.estimate(rates, 20, 100, 20, 1, epochs=0)


if __name__ == "__main__":
    unittest.main()
