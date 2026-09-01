#!/usr/bin/env python3
"""Validate the pending Dreaddit pre-access package without opening corpus data."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[4]
LANE_ROOT = Path(__file__).resolve().parent

CONTRACT_PATH = LANE_ROOT / "dreaddit_input_contract.pending.json"
FREEZE_PATH = LANE_ROOT / "dreaddit_study_freeze.pending.json"

ALLOWLIST = {
    "dataset/manifests/dreaddit_source_manifest.json",
    "experiments/direction_h_human_in_loop/active_real_data/dreaddit/dreaddit_input_contract.pending.json",
    "experiments/direction_j_llm_as_rater/schemas/evaluator_item.schema.json",
    "experiments/direction_j_llm_as_rater/schemas/shared_rating.schema.json",
    "experiments/direction_j_llm_as_rater/schemas/paired_observation.schema.json",
    "experiments/direction_j_llm_as_rater/protocol/shared_rater_guide_v1.md",
    "experiments/direction_h_human_in_loop/schemas/feedback_record.schema.json",
    "experiments/direction_j_llm_as_rater/schemas/repair_assessment.schema.json",
    "experiments/direction_h_human_in_loop/schemas/post_revision_rating_link.schema.json",
}

FORBIDDEN_PARTS = {
    "raw",
    "deidentified",
    "pilot",
    "companion_j_bridge",
    "inactive_fictional_artifacts",
}


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def safe_reference(reference: str) -> Path:
    if reference not in ALLOWLIST:
        raise ValueError(f"reference is not metadata allowlisted: {reference}")
    relative = Path(reference)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"unsafe reference: {reference}")
    if FORBIDDEN_PARTS.intersection(relative.parts):
        raise ValueError(f"forbidden data or fictional-artifact path: {reference}")
    resolved = (PROJECT_ROOT / relative).resolve()
    resolved.relative_to(PROJECT_ROOT.resolve())
    return resolved


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require_false(mapping: dict[str, Any], fields: list[str], label: str) -> None:
    for field in fields:
        if mapping.get(field) is not False:
            raise ValueError(f"{label}.{field} must remain false in pending scaffold")


def require_null(mapping: dict[str, Any], label: str) -> None:
    for field, value in mapping.items():
        if value is not None:
            raise ValueError(f"{label}.{field} must remain null before freeze")


def main() -> int:
    contract = load_json(CONTRACT_PATH)
    freeze = load_json(FREEZE_PATH)

    if contract.get("document_type") != "direction_h_dreaddit_input_contract":
        raise ValueError("unexpected contract document_type")
    if contract.get("status") != "pending_not_authorized":
        raise ValueError("input contract must remain pending_not_authorized")
    require_false(
        contract,
        [
            "contract_frozen",
            "real_text_access_authorized",
            "model_processing_authorized",
            "human_display_authorized",
        ],
        "contract",
    )
    if contract.get("corpus", {}).get("corpus_id") != "dreaddit":
        raise ValueError("contract corpus_id must be dreaddit")

    source_receipt = contract["corpus"]["source_receipt_reference"]
    source_receipt_path = safe_reference(source_receipt)
    if sha256_file(source_receipt_path) != contract["corpus"]["source_receipt_sha256"]:
        raise ValueError("source receipt hash mismatch")
    source_manifest = load_json(source_receipt_path)
    if source_manifest.get("corpus_id") != "dreaddit":
        raise ValueError("source manifest corpus_id mismatch")
    manifest_hashes = {
        entry["name"]: entry["sha256"]
        for entry in source_manifest.get("files", [])
        if isinstance(entry, dict) and "name" in entry and "sha256" in entry
    }
    for entry in contract["corpus"]["source_files"]:
        source_name = Path(entry["path"]).name
        if entry["sha256_from_source_receipt"] != manifest_hashes.get(source_name):
            raise ValueError(f"source-receipt hash binding mismatch: {source_name}")

    require_false(
        contract["governance_binding"],
        [
            "current_gate_authorization_asserted_by_this_contract",
            "exact_corpus_input_contract_gate_complete",
        ],
        "contract.governance_binding",
    )
    require_false(
        contract["release_contract"],
        [
            "source_or_analysis_text_redistribution_permitted",
            "quotation_permitted",
            "release_controls_approved",
        ],
        "contract.release_contract",
    )

    if freeze.get("document_type") != "direction_h_dreaddit_study_freeze":
        raise ValueError("unexpected freeze document_type")
    if freeze.get("status") != "pending_not_frozen":
        raise ValueError("study freeze must remain pending_not_frozen")
    if freeze.get("frozen_at_utc") is not None or freeze.get("frozen_by_authority_id") is not None:
        raise ValueError("pending freeze cannot claim a freeze time or authority")
    if freeze.get("real_text_preaccess_freeze_complete") is not False:
        raise ValueError("real_text_preaccess_freeze_complete must remain false")
    if freeze.get("fictional_or_synthetic_data_authorized") is not False:
        raise ValueError("fictional_or_synthetic_data_authorized must remain false")

    contract_reference = freeze["input_contract"]["reference"]
    contract_reference_path = safe_reference(contract_reference)
    if contract_reference_path != CONTRACT_PATH.resolve():
        raise ValueError("freeze points to unexpected input contract")
    if sha256_file(contract_reference_path) != freeze["input_contract"]["sha256"]:
        raise ValueError("input contract hash mismatch")

    seen_roles: set[str] = set()
    for binding in freeze["companion_item_level_contracts"]:
        role = binding["role"]
        if role in seen_roles:
            raise ValueError(f"duplicate companion contract role: {role}")
        seen_roles.add(role)
        reference_path = safe_reference(binding["reference"])
        if sha256_file(reference_path) != binding["sha256"]:
            raise ValueError(f"companion contract hash mismatch: {binding['reference']}")

    require_null(freeze["required_freeze_bindings"], "freeze.required_freeze_bindings")
    require_false(
        freeze["authorization_claims"],
        list(freeze["authorization_claims"].keys()),
        "freeze.authorization_claims",
    )
    for lane in freeze["corpus_lanes"]:
        if lane.get("local_candidate_selection_authorized") is not False:
            raise ValueError("candidate selection must remain unauthorized")
    require_false(
        freeze["planned_outcome_scope"],
        [
            "defect_detection_outcome_definition_frozen",
            "downstream_repair_outcome_definition_frozen",
            "empirical_results_present",
            "ratings_present",
        ],
        "freeze.planned_outcome_scope",
    )

    print("PASS: Dreaddit pre-access metadata is internally bound and fail closed.")
    print("PASS: Validator opened only allowlisted metadata/code-contract files; no corpus record path was accessed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
