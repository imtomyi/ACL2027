#!/usr/bin/env python3
"""Validate the exact personal, loopback-only RQ2 diagnostic policy.

The policy is intentionally narrower than project-wide real-text readiness. It
binds two deidentified record files by path and SHA-256 and does not authorize
cloud processing, DNS, human access, publication, or redistribution. This
checker reads the bound files only to calculate their hashes; it never parses
or emits source-derived records.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import stat
import sys
from pathlib import Path
from typing import Any


SCRIPT_PATH = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_PATH.parents[2]
POLICY_PATH = PROJECT_ROOT / "governance" / "policies" / "personal_local_diagnostic_v1.json"
STORAGE_ROOT = PROJECT_ROOT / "Storage"

DOCUMENT_TYPE = "warrantroute_personal_local_diagnostic_policy"
POLICY_VERSION = "warrantroute-personal-local-diagnostic-v1"
POLICY_SCOPE = "personal_local_only"
CORPORA = ("dreaddit", "agyw_focus_groups")

EXPECTED_INPUT_BINDINGS = {
    "dreaddit": {
        "records_path": "dataset/deidentified/dreaddit/records.jsonl",
        "records_sha256": "86ba43a89d9ef52f5377d35c12d26690b820f24ce11bc6540eeae57605654d3a",
        "allowed_splits": ["development_train", "in_domain_audit"],
        "split_roles": {
            "development_train": "development_diagnostic",
            "in_domain_audit": "post_development_audit_diagnostic",
        },
        "cluster_units": [
            {"unit": "post", "record_fields": ["source_id"]},
        ],
        "selection_use_by_split": {
            "development_train": True,
            "in_domain_audit": False,
        },
    },
    "agyw_focus_groups": {
        "records_path": "dataset/deidentified/agyw_focus_groups/records.jsonl",
        "records_sha256": "6dbaef1a21323c776c655693e0464bfa19e088e2ef6fc3b421a13c2bc785176e",
        "allowed_splits": ["heldout_cross_domain_evaluation"],
        "split_roles": {
            "heldout_cross_domain_evaluation": "heldout_cross_domain_diagnostic",
        },
        "cluster_units": [
            {"unit": "focus_group", "record_fields": ["source_id"]},
            {
                "unit": "transcript_local_speaker",
                "record_fields": ["source_id", "speaker_id"],
            },
        ],
        "selection_use_by_split": {
            "heldout_cross_domain_evaluation": False,
        },
    },
}

EXPECTED_MODEL_TRANSPORT = {
    "endpoint": "http://127.0.0.1:11434",
    "allowed_scheme": "http",
    "allowed_host": "127.0.0.1",
    "allowed_port": 11434,
    "loopback_only": True,
    "dns_allowed": False,
    "cloud_processing_allowed": False,
    "remote_hosts_allowed": False,
}

EXPECTED_ACCESS_AND_RELEASE = {
    "single_local_user_only": True,
    "human_rater_or_reviewer_access_allowed": False,
    "publication_or_submission_allowed": False,
    "redistribution_or_release_allowed": False,
    "source_or_excerpt_export_allowed": False,
}

EXPECTED_OUTPUT = {
    "root": "Storage/rq2_personal_local_diagnostic",
    "must_remain_under_root": True,
}

EXPECTED_LABELS = {
    "execution_class": "personal_local_diagnostic",
    "result_label": "private_personal_exploratory_not_for_publication",
    "evidence_status": "diagnostic_not_manuscript_evidence",
    "confirmatory_claims_allowed": False,
    "manuscript_use_allowed": False,
}

TOP_LEVEL_KEYS = {
    "document_type",
    "policy_version",
    "scope",
    "input_bindings",
    "model_transport",
    "access_and_release",
    "output",
    "labels",
}


class PersonalLocalPolicyError(RuntimeError):
    """Raised when the exact personal-local diagnostic contract is not met."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PersonalLocalPolicyError(message)


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), "Policy must be a JSON object")
    return value


def is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def validate_policy(policy: dict[str, Any]) -> None:
    """Require the complete, exact v1 policy contract."""

    require(set(policy) == TOP_LEVEL_KEYS, "Unexpected personal-local policy fields")
    require(policy.get("document_type") == DOCUMENT_TYPE, "Policy document type mismatch")
    require(policy.get("policy_version") == POLICY_VERSION, "Policy version mismatch")
    require(policy.get("scope") == POLICY_SCOPE, "Policy scope is not personal-local-only")
    require(
        policy.get("input_bindings") == EXPECTED_INPUT_BINDINGS,
        "Input paths, hashes, splits, roles, or cluster bindings changed",
    )
    require(
        policy.get("model_transport") == EXPECTED_MODEL_TRANSPORT,
        "Model transport is not exact loopback-only HTTP with DNS and cloud disabled",
    )
    require(
        policy.get("access_and_release") == EXPECTED_ACCESS_AND_RELEASE,
        "Human-access or release restrictions changed",
    )
    require(policy.get("output") == EXPECTED_OUTPUT, "Diagnostic output root changed")
    require(policy.get("labels") == EXPECTED_LABELS, "Diagnostic labels changed")


def verify_bound_inputs(
    policy: dict[str, Any], project_root: Path = PROJECT_ROOT
) -> list[dict[str, Any]]:
    """Verify regular, in-workspace input files against the fixed hashes."""

    project_root = project_root.resolve()
    results: list[dict[str, Any]] = []
    bindings = policy["input_bindings"]
    for corpus_id in CORPORA:
        binding = bindings[corpus_id]
        records_path = project_root / binding["records_path"]
        require(not records_path.is_symlink(), f"{corpus_id} records path must not be a symlink")
        require(
            records_path.is_file(),
            f"{corpus_id} bound deidentified records file is missing",
        )
        require(
            stat.S_IMODE(records_path.stat().st_mode) == 0o600,
            f"{corpus_id} records file must use mode 0600",
        )
        require(
            not records_path.parent.is_symlink()
            and records_path.parent.is_dir()
            and stat.S_IMODE(records_path.parent.stat().st_mode) == 0o700,
            f"{corpus_id} records directory must be a regular mode-0700 directory",
        )
        require(
            is_within(records_path, project_root),
            f"{corpus_id} records path escapes the project root",
        )
        observed = sha256_path(records_path)
        require(
            observed == binding["records_sha256"],
            f"{corpus_id} deidentified records SHA-256 mismatch",
        )
        results.append(
            {
                "corpus_id": corpus_id,
                "records_path": binding["records_path"],
                "records_sha256": observed,
                "hash_matches": True,
            }
        )
    return results


def verify_output_root(policy: dict[str, Any], project_root: Path = PROJECT_ROOT) -> None:
    """Ensure the declared output root is the fixed private diagnostic subtree."""

    project_root = project_root.resolve()
    storage_root = (project_root / "Storage").resolve()
    output_root = project_root / policy["output"]["root"]
    require(
        output_root.resolve() == storage_root / "rq2_personal_local_diagnostic",
        "Resolved diagnostic output root changed",
    )
    require(is_within(output_root, storage_root), "Diagnostic output root escapes Storage")
    if output_root.exists():
        require(not output_root.is_symlink(), "Diagnostic output root must not be a symlink")
        require(output_root.is_dir(), "Diagnostic output root exists but is not a directory")
        require(
            stat.S_IMODE(output_root.stat().st_mode) == 0o700,
            "Diagnostic output root must use mode 0700",
        )


def build_report(
    policy: dict[str, Any],
    policy_sha256: str,
    input_results: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "document_type": "warrantroute_personal_local_policy_check",
        "policy_version": POLICY_VERSION,
        "policy_sha256": policy_sha256,
        "policy_valid": True,
        "contains_source_text": False,
        "scope": POLICY_SCOPE,
        "bound_inputs": input_results,
        "model_transport": policy["model_transport"],
        "access_and_release": policy["access_and_release"],
        "output": policy["output"],
        "labels": policy["labels"],
        "warning_codes": [
            "diagnostic_only_not_manuscript_evidence",
            "declarative_policy_requires_execution_edge_enforcement",
        ],
    }


def run(policy_path: Path = POLICY_PATH, project_root: Path = PROJECT_ROOT) -> dict[str, Any]:
    require(not policy_path.is_symlink(), "Policy path must not be a symlink")
    require(policy_path.is_file(), "Personal-local policy file is missing")
    policy = load_json(policy_path)
    validate_policy(policy)
    input_results = verify_bound_inputs(policy, project_root)
    verify_output_root(policy, project_root)
    return build_report(policy, sha256_path(policy_path), input_results)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate the exact personal loopback-only RQ2 diagnostic policy"
    )
    parser.add_argument("--policy", type=Path, default=POLICY_PATH)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        report = run(args.policy)
    except (OSError, json.JSONDecodeError, PersonalLocalPolicyError) as exc:
        print(f"Personal-local policy check failed: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
