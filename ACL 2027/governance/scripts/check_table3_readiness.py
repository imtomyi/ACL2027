#!/usr/bin/env python3
"""Validate the four-corpus governance record for formal Table 3 execution.

This checker reads metadata and referenced evidence files only. It never opens a
packet bank, source corpus, truth map, reviewer output, or model prompt.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT = Path(__file__).resolve()
WORKSPACE = SCRIPT.parents[2]
GOVERNANCE_ROOT = WORKSPACE / "governance"
LOCAL_ROOT = GOVERNANCE_ROOT / "local"
DEFAULT_RECORD = GOVERNANCE_ROOT / "templates/table3_project_governance_v1.template.json"

CORPORA = ("dreaddit", "goemotions", "cache", "parlamint_gb")
DISPLAY_NAMES = {
    "dreaddit": "Dreaddit",
    "goemotions": "GoEmotions",
    "cache": "CaChe",
    "parlamint_gb": "ParlaMint-GB",
}
CLUSTER_UNITS = {
    "dreaddit": ["post"],
    "goemotions": ["comment"],
    "cache": ["focus_group", "transcript_local_speaker"],
    "parlamint_gb": ["debate"],
}
GATES = (
    "institutional_determination",
    "source_platform_authorization",
    "provider_model_processing",
    "exact_corpus_input_contract",
    "two_person_excerpt_privacy_review",
    "cluster_aware_sampling",
    "frozen_study_manifest",
    "rater_and_service_access_controls",
    "retention_deletion_controls",
    "release_controls",
)
TOP_LEVEL_KEYS = {
    "document_type",
    "governance_version",
    "record_status",
    "record_id",
    "study_id",
    "assessment_as_of_utc",
    "responsible_owner_id",
    "execution_authorized",
    "contains_real_source_text",
    "corpus_lanes",
    "template_notice",
}
LANE_KEYS = {
    "corpus_id",
    "display_name",
    "required_cluster_units",
    "planned_use",
    "gates",
}
GATE_KEYS = {
    "status",
    "evidence_reference",
    "evidence_sha256",
    "authority_id",
    "evidence_version",
    "approved_at_utc",
    "expires_at_utc",
    "last_verified_at_utc",
    "scope",
}
ALLOWED_STATUSES = {"pending", "approved", "rejected", "expired"}


class Table3ReadinessError(RuntimeError):
    """Raised for malformed governance metadata."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise Table3ReadinessError(code)


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def parse_utc(value: Any, label: str) -> datetime:
    require(isinstance(value, str) and value.endswith("Z"), f"{label}_invalid")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise Table3ReadinessError(f"{label}_invalid") from exc
    require(parsed.tzinfo is not None, f"{label}_invalid")
    return parsed.astimezone(timezone.utc)


def is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def load_record(path: Path) -> tuple[dict[str, Any], bytes]:
    try:
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Table3ReadinessError("governance_record_unreadable") from exc
    require(isinstance(value, dict), "governance_record_not_object")
    return value, raw


def validate_shape(record: dict[str, Any]) -> None:
    require(set(record) == TOP_LEVEL_KEYS, "governance_top_level_keys_invalid")
    require(
        record.get("document_type") == "table3_project_governance_record",
        "governance_document_type_invalid",
    )
    require(
        record.get("governance_version") == "table3-project-governance-v1",
        "governance_version_invalid",
    )
    require(
        record.get("record_status") in {"template_not_approved", "local_evidence_record"},
        "governance_record_status_invalid",
    )
    require(record.get("study_id") == "table3-formal-full-matrix-v1", "study_id_invalid")
    require(record.get("contains_real_source_text") is False, "governance_record_contains_source_text")
    lanes = record.get("corpus_lanes")
    require(isinstance(lanes, dict) and tuple(lanes) == CORPORA, "governance_corpus_order_invalid")
    for corpus_id in CORPORA:
        lane = lanes[corpus_id]
        require(isinstance(lane, dict) and set(lane) == LANE_KEYS, f"{corpus_id}_lane_shape_invalid")
        require(lane.get("corpus_id") == corpus_id, f"{corpus_id}_lane_id_invalid")
        require(lane.get("display_name") == DISPLAY_NAMES[corpus_id], f"{corpus_id}_display_name_invalid")
        require(lane.get("required_cluster_units") == CLUSTER_UNITS[corpus_id], f"{corpus_id}_cluster_units_invalid")
        require(
            lane.get("planned_use") == "table3_baseline_and_later_frozen_router_evaluation",
            f"{corpus_id}_planned_use_invalid",
        )
        gates = lane.get("gates")
        require(isinstance(gates, dict) and tuple(gates) == GATES, f"{corpus_id}_gate_order_invalid")
        for gate_id in GATES:
            gate = gates[gate_id]
            require(isinstance(gate, dict) and set(gate) == GATE_KEYS, f"{corpus_id}_{gate_id}_shape_invalid")
            require(gate.get("status") in ALLOWED_STATUSES, f"{corpus_id}_{gate_id}_status_invalid")
            require(gate.get("scope") == "table3_formal_full_matrix_v1", f"{corpus_id}_{gate_id}_scope_invalid")


def evidence_blockers(gate: dict[str, Any], as_of: datetime) -> list[str]:
    if gate["status"] != "approved":
        return [f"status_{gate['status']}"]
    blockers: list[str] = []
    for field in ("authority_id", "evidence_version"):
        if not nonempty(gate.get(field)):
            blockers.append(f"missing_{field}")
    reference = gate.get("evidence_reference")
    evidence_path: Path | None = None
    if not nonempty(reference):
        blockers.append("missing_evidence_reference")
    else:
        candidate = Path(reference)
        evidence_path = candidate if candidate.is_absolute() else WORKSPACE / candidate
        evidence_path = evidence_path.resolve(strict=False)
        if not is_within(evidence_path, LOCAL_ROOT):
            blockers.append("evidence_outside_governance_local")
        elif evidence_path.is_symlink() or not evidence_path.is_file():
            blockers.append("evidence_file_missing_or_not_regular")
        elif stat.S_IMODE(evidence_path.stat().st_mode) != 0o600:
            blockers.append("evidence_file_mode_not_0600")
    expected_hash = gate.get("evidence_sha256")
    if not is_sha256(expected_hash):
        blockers.append("missing_or_invalid_evidence_sha256")
    elif evidence_path is not None and evidence_path.is_file() and not evidence_path.is_symlink():
        if sha256_file(evidence_path) != expected_hash:
            blockers.append("evidence_sha256_mismatch")
    timestamps: dict[str, datetime] = {}
    for field in ("approved_at_utc", "expires_at_utc", "last_verified_at_utc"):
        try:
            timestamps[field] = parse_utc(gate.get(field), field)
        except Table3ReadinessError:
            blockers.append(f"invalid_{field}")
    if len(timestamps) == 3:
        if timestamps["approved_at_utc"] > as_of:
            blockers.append("approval_not_yet_effective")
        if timestamps["expires_at_utc"] <= as_of:
            blockers.append("approval_expired")
        if timestamps["last_verified_at_utc"] > as_of:
            blockers.append("last_verified_in_future")
        if timestamps["last_verified_at_utc"] < timestamps["approved_at_utc"]:
            blockers.append("not_verified_after_approval")
    return sorted(set(blockers))


def build_report(
    record: dict[str, Any],
    *,
    record_sha256: str,
    as_of: datetime,
) -> dict[str, Any]:
    validate_shape(record)
    local_record = record.get("record_status") == "local_evidence_record"
    corpus_reports: dict[str, Any] = {}
    total_complete = 0
    for corpus_id in CORPORA:
        gate_reports: list[dict[str, Any]] = []
        for gate_id in GATES:
            blockers = evidence_blockers(record["corpus_lanes"][corpus_id]["gates"][gate_id], as_of)
            complete = not blockers
            total_complete += int(complete)
            gate_reports.append(
                {
                    "id": gate_id,
                    "complete": complete,
                    "blocking_reason_codes": blockers,
                }
            )
        completed = sum(item["complete"] for item in gate_reports)
        corpus_reports[corpus_id] = {
            "display_name": DISPLAY_NAMES[corpus_id],
            "required_cluster_units": CLUSTER_UNITS[corpus_id],
            "required_gate_count": len(GATES),
            "completed_gate_count": completed,
            "real_text_ready": local_record and completed == len(GATES),
            "gates": gate_reports,
        }
    all_gate_evidence_ready = total_complete == len(CORPORA) * len(GATES)
    all_ready = (
        local_record
        and all_gate_evidence_ready
        and record.get("execution_authorized") is True
        and nonempty(record.get("record_id"))
        and nonempty(record.get("responsible_owner_id"))
    )
    return {
        "document_type": "table3_project_readiness_report",
        "readiness_version": "table3-project-readiness-v1",
        "assessment_as_of_utc": as_of.isoformat().replace("+00:00", "Z"),
        "governance_record_sha256": record_sha256,
        "contains_real_source_text": False,
        "required_corpus_count": len(CORPORA),
        "required_gate_count": len(CORPORA) * len(GATES),
        "completed_gate_count": total_complete,
        "all_gate_evidence_ready": all_gate_evidence_ready,
        "execution_authorized": record.get("execution_authorized") is True,
        "all_real_corpora_ready": all_ready,
        "corpora": corpus_reports,
    }


def atomic_private_write(path: Path, content: bytes) -> None:
    require(is_within(path, LOCAL_ROOT), "output_must_be_under_governance_local")
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    with temporary.open("wb") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check all 40 Table 3 governance gates")
    parser.add_argument("--record", type=Path, default=DEFAULT_RECORD)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--output", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        as_of = parse_utc(args.as_of, "as_of")
        record_path = args.record.resolve()
        record, raw = load_record(record_path)
        if record.get("record_status") == "local_evidence_record":
            require(is_within(record_path, LOCAL_ROOT), "local_record_outside_governance_local")
            require(not record_path.is_symlink(), "local_record_is_symlink")
            require(stat.S_IMODE(record_path.stat().st_mode) == 0o600, "local_record_mode_not_0600")
        report = build_report(record, record_sha256=sha256_bytes(raw), as_of=as_of)
        content = canonical_bytes(report)
        if args.output is not None:
            atomic_private_write(args.output.resolve(), content)
        print(content.decode("utf-8"), end="")
        return 0 if report["all_real_corpora_ready"] else 2
    except Table3ReadinessError as exc:
        print(json.dumps({"status": "malformed", "error_code": str(exc)}, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
