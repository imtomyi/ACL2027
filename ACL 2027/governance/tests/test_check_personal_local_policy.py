from __future__ import annotations

import copy
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path


GOVERNANCE_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = GOVERNANCE_ROOT / "scripts" / "check_personal_local_policy.py"
POLICY_PATH = GOVERNANCE_ROOT / "policies" / "personal_local_diagnostic_v1.json"

SPEC = importlib.util.spec_from_file_location("check_personal_local_policy", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
policy_check = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(policy_check)


def load_policy() -> dict:
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


class PersonalLocalPolicyTests(unittest.TestCase):
    def test_exact_policy_and_live_input_hashes_pass(self) -> None:
        policy = load_policy()
        policy_check.validate_policy(policy)
        report = policy_check.run(POLICY_PATH)

        self.assertTrue(report["policy_valid"])
        self.assertFalse(report["contains_source_text"])
        self.assertEqual(
            [item["corpus_id"] for item in report["bound_inputs"]],
            list(policy_check.CORPORA),
        )
        self.assertTrue(all(item["hash_matches"] for item in report["bound_inputs"]))
        self.assertEqual(
            report["model_transport"]["endpoint"], "http://127.0.0.1:11434"
        )

    def test_network_transport_is_exact_and_fail_closed(self) -> None:
        mutations = {
            "hostname_instead_of_numeric_loopback": ("endpoint", "http://localhost:11434"),
            "dns_enabled": ("dns_allowed", True),
            "cloud_enabled": ("cloud_processing_allowed", True),
            "remote_hosts_enabled": ("remote_hosts_allowed", True),
            "loopback_disabled": ("loopback_only", False),
            "port_changed": ("allowed_port", 11435),
        }
        for label, (key, value) in mutations.items():
            with self.subTest(label=label):
                policy = load_policy()
                policy["model_transport"][key] = value
                with self.assertRaises(policy_check.PersonalLocalPolicyError):
                    policy_check.validate_policy(policy)

    def test_human_and_release_capabilities_cannot_be_enabled(self) -> None:
        forbidden = (
            "human_rater_or_reviewer_access_allowed",
            "publication_or_submission_allowed",
            "redistribution_or_release_allowed",
            "source_or_excerpt_export_allowed",
        )
        for capability in forbidden:
            with self.subTest(capability=capability):
                policy = load_policy()
                policy["access_and_release"][capability] = True
                with self.assertRaises(policy_check.PersonalLocalPolicyError):
                    policy_check.validate_policy(policy)

    def test_only_exact_corpora_hashes_splits_and_clusters_are_accepted(self) -> None:
        mutations = []

        third_corpus = load_policy()
        third_corpus["input_bindings"]["candor"] = copy.deepcopy(
            third_corpus["input_bindings"]["dreaddit"]
        )
        mutations.append(("third_corpus", third_corpus))

        changed_hash = load_policy()
        changed_hash["input_bindings"]["dreaddit"]["records_sha256"] = "0" * 64
        mutations.append(("changed_hash", changed_hash))

        changed_split = load_policy()
        changed_split["input_bindings"]["dreaddit"]["allowed_splits"] = [
            "development_train"
        ]
        mutations.append(("changed_split", changed_split))

        changed_cluster = load_policy()
        changed_cluster["input_bindings"]["agyw_focus_groups"]["cluster_units"][1][
            "record_fields"
        ] = ["speaker_id"]
        mutations.append(("changed_cluster", changed_cluster))

        for label, policy in mutations:
            with self.subTest(label=label):
                with self.assertRaises(policy_check.PersonalLocalPolicyError):
                    policy_check.validate_policy(policy)

    def test_output_root_and_diagnostic_labels_are_exact(self) -> None:
        policy = load_policy()
        policy["output"]["root"] = "overleaf/results"
        with self.assertRaises(policy_check.PersonalLocalPolicyError):
            policy_check.validate_policy(policy)

        policy = load_policy()
        policy["labels"]["manuscript_use_allowed"] = True
        with self.assertRaises(policy_check.PersonalLocalPolicyError):
            policy_check.validate_policy(policy)

        policy = load_policy()
        policy["labels"]["evidence_status"] = "confirmatory"
        with self.assertRaises(policy_check.PersonalLocalPolicyError):
            policy_check.validate_policy(policy)

    def test_live_input_verifier_rejects_tampered_bytes(self) -> None:
        policy = load_policy()
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            records_path = (
                project_root / policy["input_bindings"]["dreaddit"]["records_path"]
            )
            records_path.parent.mkdir(parents=True)
            os.chmod(records_path.parent, 0o700)
            records_path.write_bytes(b"tampered\n")
            os.chmod(records_path, 0o600)
            with self.assertRaisesRegex(
                policy_check.PersonalLocalPolicyError, "SHA-256 mismatch"
            ):
                policy_check.verify_bound_inputs(policy, project_root)

    def test_private_file_and_directory_modes_are_enforced(self) -> None:
        policy = load_policy()
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            records_path = (
                project_root / policy["input_bindings"]["dreaddit"]["records_path"]
            )
            records_path.parent.mkdir(parents=True)
            os.chmod(records_path.parent, 0o700)
            records_path.write_bytes(b"private\n")
            os.chmod(records_path, 0o640)
            with self.assertRaisesRegex(
                policy_check.PersonalLocalPolicyError, "mode 0600"
            ):
                policy_check.verify_bound_inputs(policy, project_root)

        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            output_root = project_root / policy["output"]["root"]
            output_root.mkdir(parents=True)
            os.chmod(output_root, 0o755)
            with self.assertRaisesRegex(
                policy_check.PersonalLocalPolicyError, "mode 0700"
            ):
                policy_check.verify_output_root(policy, project_root)


if __name__ == "__main__":
    unittest.main()
