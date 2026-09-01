#!/usr/bin/env python3
"""Prepare fail-closed Dreaddit/AGYW candidate and privacy-review artifacts.

This script never changes the canonical real-corpus records.  It selects whole
source clusters into a text-free candidate manifest, quarantines any cluster
whose proposed excerpt or displayed context contains a numeric exact-date
pattern, and builds restricted review packets plus a text-free two-reviewer
ledger.  Generated records remain pending and ineligible for experiment use.

The tracked control template is intentionally invalid.  Real candidate
selection requires a restricted local control record backed by documentary
authorization; held-out lanes additionally require a completed pre-access
freeze.  Validation of that control happens before this script opens a real
records file.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


PIPELINE_VERSION = "dreaddit-agyw-review-v1"
SCHEMA_VERSION = "1.0"

DATASET_ROOT = Path(__file__).resolve().parents[1]
REVIEW_RUNTIME_ROOT = DATASET_ROOT / "deidentified" / "review_workflows"
REVIEW_CONTROL_ROOT = DATASET_ROOT / "deidentified" / "review_controls"

SELECTION_CONTROL_WARNING = (
    "Restricted local control only. It must be completed from documentary evidence; "
    "the tracked template is not authorization."
)
CANDIDATE_WARNING = (
    "Text-free candidate inventory only. Selection eligibility is not privacy, ethics, "
    "provider, rater-display, quotation, or experiment clearance."
)
LEDGER_WARNING = (
    "Ledger contains hashes and project-local IDs only, never excerpt text or raw source IDs. "
    "Even two completed privacy reviews do not satisfy external governance gates."
)

SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
REVIEWER_ID_RE = re.compile(r"^REV_[A-Z0-9]{8,32}$")
NOTES_REFERENCE_RE = re.compile(r"^review_note_[a-f0-9]{16}$")
MONTH_NAME_PATTERN = (
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|"
    r"Dec(?:ember)?)\.?"
)
EXACT_DATE_RE = re.compile(
    r"(?<!\d)(?:19|20)\d{2}[-/.](?:0?[1-9]|1[0-2])[-/.](?:0?[1-9]|[12]\d|3[01])(?!\d)"
    r"|(?<!\d)(?:0?[1-9]|1[0-2])[-/.](?:0?[1-9]|[12]\d|3[01])[-/.](?:19|20)?\d{2}(?!\d)"
    rf"|(?<![A-Za-z]){MONTH_NAME_PATTERN}\s+(?:0?[1-9]|[12]\d|3[01])"
    rf"(?:st|nd|rd|th)?(?:,\s*|\s+)(?:19|20)\d{{2}}(?!\d)"
    rf"|(?<!\d)(?:0?[1-9]|[12]\d|3[01])(?:st|nd|rd|th)?\s+"
    rf"(?:of\s+)?{MONTH_NAME_PATTERN}(?:,\s*|\s+)(?:19|20)\d{{2}}(?!\d)",
    re.IGNORECASE,
)
EXACT_DATE_PATTERN_VERSION = "numeric-and-month-name-exact-date-v2"

CONTROL_KEYS = {
    "document_type",
    "schema_version",
    "status",
    "corpus",
    "split",
    "local_candidate_selection_authorized",
    "authorization_reference",
    "authorized_by",
    "authorized_at_utc",
    "records_sha256",
    "source_manifest_sha256",
    "requested_cluster_count",
    "sampling_seed_sha256",
    "sampling_plan_sha256",
    "heldout",
    "warning",
}
HELDOUT_CONTROL_KEYS = {
    "is_heldout",
    "freeze_status",
    "frozen_at_utc",
    "heldout_access_log_clean",
    "packet_rules_sha256",
    "prompt_sha256",
    "model_snapshot",
    "outcomes_sha256",
    "analysis_code_sha256",
}
CANDIDATE_KEYS = {
    "document_type",
    "schema_version",
    "pipeline_version",
    "corpus",
    "split",
    "experimental_role",
    "status",
    "records_file",
    "records_sha256",
    "source_manifest_file",
    "source_manifest_sha256",
    "selection_control_file",
    "selection_control_sha256",
    "cluster_unit",
    "sampling_algorithm",
    "sampling_seed_sha256",
    "requested_cluster_count",
    "eligible_before_exact_date_quarantine",
    "exact_date_quarantine",
    "available_after_exact_date_quarantine",
    "selected",
    "clusters",
    "manual_privacy_review_required",
    "experiment_use_ready",
    "warning",
}
COUNT_KEYS = {"clusters", "records"}
CLUSTER_KEYS = {
    "cluster_id",
    "source_ids",
    "speaker_ids",
    "record_ids",
    "review_status",
    "experiment_use_ready",
}
QUARANTINE_CLUSTER_KEYS = {"cluster_id", "record_ids", "reason"}

PACKET_KEYS = {
    "review_item_id",
    "cluster_id",
    "record_id",
    "content_sha256",
    "review_content",
    "review_status",
    "experiment_use_ready",
}
REVIEW_CONTENT_KEYS = {
    "corpus",
    "split",
    "source_id",
    "speaker_id",
    "text",
    "context",
}
REVIEW_CONTEXT_KEYS = {"preceding", "moderator_question"}
PRECEDING_KEYS = {"record_id", "text"}
LEDGER_KEYS = {
    "document_type",
    "schema_version",
    "pipeline_version",
    "corpus",
    "split",
    "candidate_manifest_file",
    "candidate_manifest_sha256",
    "packet_file",
    "packet_sha256",
    "status",
    "entries",
    "experiment_use_ready",
    "warning",
}
LEDGER_ENTRY_KEYS = {
    "review_item_id",
    "record_id",
    "cluster_id",
    "content_sha256",
    "required_distinct_reviewers",
    "reviews",
    "privacy_review_complete",
    "permitted_uses",
    "experiment_use_ready",
}
PERMITTED_USE_KEYS = {"model_processing", "rater_display", "quotation"}
REVIEW_KEYS = {
    "reviewer_id",
    "reviewed_at_utc",
    "decision",
    "direct_identifiers_resolved",
    "contextual_risk_resolved",
    "model_processing_cleared",
    "rater_display_cleared",
    "quotation_cleared",
    "notes_reference",
}

CORPORA: dict[str, dict[str, Any]] = {
    "dreaddit": {
        "records": DATASET_ROOT / "deidentified" / "dreaddit" / "records.jsonl",
        "source_manifest": DATASET_ROOT / "manifests" / "dreaddit_source_manifest.json",
        "cluster_unit": "post",
        "splits": {
            "development_train": {"role": "development", "heldout": False},
            "in_domain_audit": {"role": "in_domain_audit", "heldout": True},
        },
    },
    "agyw_focus_groups": {
        "records": DATASET_ROOT / "deidentified" / "agyw_focus_groups" / "records.jsonl",
        "build_report": DATASET_ROOT
        / "deidentified"
        / "agyw_focus_groups"
        / "build_report.json",
        "source_manifest": DATASET_ROOT / "manifests" / "agyw_source_manifest.json",
        "cluster_unit": "focus_group_and_transcript_local_speaker",
        "splits": {
            "heldout_cross_domain_evaluation": {
                "role": "cross_domain_confirmatory",
                "heldout": True,
            }
        },
    },
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )


def canonical_compact_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")


def canonical_jsonl_bytes(values: Iterable[dict[str, Any]]) -> bytes:
    return b"".join(
        json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8") + b"\n"
        for value in values
    )


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def file_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def read_json_snapshot(path: Path) -> tuple[dict[str, Any], str]:
    content = path.read_bytes()
    value = json.loads(content.decode("utf-8"))
    require(isinstance(value, dict), f"Expected a JSON object in {path.name}")
    return value, sha256_bytes(content)


def read_records_snapshot(path: Path) -> tuple[list[dict[str, Any]], str]:
    content = path.read_bytes()
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(content.decode("utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        value = json.loads(line)
        require(isinstance(value, dict), f"Record line {line_number} is not an object")
        records.append(value)
    require(records, "No records found")
    return records, sha256_bytes(content)


def read_jsonl_snapshot(path: Path) -> tuple[list[dict[str, Any]], str]:
    return read_records_snapshot(path)


def is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def mode(path: Path) -> int:
    return path.stat().st_mode & 0o777


def require_private_file(path: Path, label: str) -> None:
    require(path.is_file() and not path.is_symlink(), f"Missing or unsafe {label}")
    require(mode(path) == 0o600, f"{label} must be mode 0600")


def ensure_private_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    require(not path.is_symlink(), "Review output directory cannot be a symlink")
    os.chmod(path, 0o700)


def atomic_write_private(path: Path, content: bytes, replace: bool) -> None:
    if path.exists() and not replace:
        raise FileExistsError(f"Refusing to replace {path}; add --replace after review")
    ensure_private_directory(path.parent)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    with temporary.open("xb") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)


def parse_utc(value: Any, label: str) -> None:
    require(isinstance(value, str) and value.endswith("Z"), f"Invalid {label}")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"Invalid {label}") from exc
    require(parsed.utcoffset() is not None, f"Invalid {label}")


def require_sha(value: Any, label: str) -> str:
    require(isinstance(value, str) and bool(SHA256_RE.fullmatch(value)), f"Invalid {label}")
    return value


def corpus_config(corpus: str, split: str) -> tuple[dict[str, Any], dict[str, Any]]:
    require(corpus in CORPORA, "Unsupported corpus")
    config = CORPORA[corpus]
    require(split in config["splits"], f"Split {split!r} is not allowed for {corpus}")
    return config, config["splits"][split]


def validate_selection_control_before_record_access(
    control: dict[str, Any],
    *,
    corpus: str,
    split: str,
    requested_clusters: int,
    sampling_seed_sha256: str,
    expected_source_manifest_sha256: str,
) -> None:
    """Validate authorization and held-out freeze before any records are opened."""
    _, split_config = corpus_config(corpus, split)
    require(set(control) == CONTROL_KEYS, "Unexpected selection-control fields")
    require(
        control.get("document_type") == "dreaddit_agyw_selection_control",
        "Invalid selection-control document type",
    )
    require(control.get("schema_version") == SCHEMA_VERSION, "Unsupported control version")
    require(
        control.get("status") == "authorized_for_local_candidate_selection",
        "Candidate selection is not authorized",
    )
    require(control.get("corpus") == corpus, "Selection-control corpus mismatch")
    require(control.get("split") == split, "Selection-control split mismatch")
    require(
        control.get("local_candidate_selection_authorized") is True,
        "Local candidate selection is not authorized",
    )
    for key in ("authorization_reference", "authorized_by", "sampling_plan_sha256"):
        value = control.get(key)
        if key.endswith("sha256"):
            require_sha(value, key)
        else:
            require(isinstance(value, str) and bool(value.strip()), f"Missing {key}")
    parse_utc(control.get("authorized_at_utc"), "authorized_at_utc")
    require_sha(control.get("records_sha256"), "records_sha256")
    require(
        control.get("source_manifest_sha256") == expected_source_manifest_sha256,
        "Selection-control source-manifest hash mismatch",
    )
    require(
        isinstance(control.get("requested_cluster_count"), int)
        and not isinstance(control.get("requested_cluster_count"), bool)
        and control["requested_cluster_count"] == requested_clusters
        and requested_clusters > 0,
        "Selection-control cluster count mismatch",
    )
    require(
        control.get("sampling_seed_sha256") == sampling_seed_sha256,
        "Selection-control sampling-seed hash mismatch",
    )
    require(control.get("warning") == SELECTION_CONTROL_WARNING, "Control warning changed")

    heldout = control.get("heldout")
    require(
        isinstance(heldout, dict) and set(heldout) == HELDOUT_CONTROL_KEYS,
        "Invalid held-out control shape",
    )
    if split_config["heldout"]:
        require(heldout.get("is_heldout") is True, "Held-out lane is not marked held out")
        require(
            heldout.get("freeze_status") == "frozen_before_heldout_access",
            "Held-out lane is not frozen and authorized before access",
        )
        parse_utc(heldout.get("frozen_at_utc"), "heldout.frozen_at_utc")
        require(
            heldout.get("heldout_access_log_clean") is True,
            "Held-out access log is not confirmed clean before freeze",
        )
        for key in (
            "packet_rules_sha256",
            "prompt_sha256",
            "outcomes_sha256",
            "analysis_code_sha256",
        ):
            require_sha(heldout.get(key), f"heldout.{key}")
        require(
            isinstance(heldout.get("model_snapshot"), str)
            and bool(heldout["model_snapshot"].strip()),
            "Held-out model snapshot is missing",
        )
    else:
        require(heldout.get("is_heldout") is False, "Development lane marked held out")
        require(
            heldout.get("freeze_status") == "not_applicable_development",
            "Development control has an invalid freeze status",
        )
        require(heldout.get("frozen_at_utc") is None, "Development control has a freeze time")
        require(
            heldout.get("heldout_access_log_clean") is False,
            "Development control has an invalid held-out access assertion",
        )
        for key in (
            "packet_rules_sha256",
            "prompt_sha256",
            "model_snapshot",
            "outcomes_sha256",
            "analysis_code_sha256",
        ):
            require(heldout.get(key) is None, f"Development control must leave {key} null")


def validate_record(record: dict[str, Any], corpus: str) -> None:
    for key in (
        "record_id",
        "corpus",
        "split",
        "source_id",
        "speaker_id",
        "text",
        "context",
        "quality",
    ):
        require(key in record, f"Record is missing {key}")
    require(record["corpus"] == corpus, "Record corpus mismatch")
    require(isinstance(record["record_id"], str) and record["record_id"], "Invalid record ID")
    require(isinstance(record["source_id"], str) and record["source_id"], "Invalid source ID")
    require(isinstance(record["text"], str) and record["text"].strip(), "Empty record text")
    require(isinstance(record["context"], dict), "Invalid record context")
    quality = record["quality"]
    require(isinstance(quality, dict), "Invalid record quality")
    require(
        quality.get("manual_excerpt_review_required") is True,
        "Candidate record is missing its manual-review gate",
    )
    require(
        quality.get("privacy_review_status") in (None, "pending"),
        "Canonical record has an unexpected privacy-review status",
    )
    if corpus == "dreaddit":
        require(record["speaker_id"] is None, "Unexpected Dreaddit speaker ID")
    else:
        speaker_id = record["speaker_id"]
        if speaker_id is not None:
            require(
                isinstance(speaker_id, str) and speaker_id.startswith(record["source_id"] + "_"),
                "AGYW speaker is not scoped to its focus group",
            )


def display_content(record: dict[str, Any], records_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    context = record["context"]
    preceding_ids = context.get("preceding_record_ids", [])
    require(isinstance(preceding_ids, list), "Invalid preceding context")
    require(len(preceding_ids) == len(set(preceding_ids)), "Duplicate preceding context ID")
    preceding: list[dict[str, str]] = []
    for previous_id in preceding_ids:
        require(isinstance(previous_id, str) and previous_id in records_by_id, "Missing context record")
        previous = records_by_id[previous_id]
        require(previous["source_id"] == record["source_id"], "Context crosses source clusters")
        preceding.append({"record_id": previous_id, "text": previous["text"]})
    moderator = context.get("moderator_question")
    require(moderator is None or isinstance(moderator, str), "Invalid moderator context")
    return {
        "corpus": record["corpus"],
        "split": record["split"],
        "source_id": record["source_id"],
        "speaker_id": record["speaker_id"],
        "text": record["text"],
        "context": {"preceding": preceding, "moderator_question": moderator},
    }


def content_has_exact_date(content: dict[str, Any]) -> bool:
    strings = [content["text"]]
    strings.extend(item["text"] for item in content["context"]["preceding"])
    moderator = content["context"]["moderator_question"]
    if moderator is not None:
        strings.append(moderator)
    return any(EXACT_DATE_RE.search(value) for value in strings)


def cluster_material(record: dict[str, Any], corpus: str) -> dict[str, Any]:
    if corpus == "dreaddit":
        return {"source_id": record["source_id"]}
    require(
        isinstance(record["speaker_id"], str) and record["speaker_id"],
        "Eligible AGYW record lacks a transcript-local speaker",
    )
    return {"source_id": record["source_id"], "speaker_id": record["speaker_id"]}


def cluster_id(material: dict[str, Any]) -> str:
    return "review_cluster_" + sha256_bytes(canonical_compact_bytes(material))[:16]


def build_candidate_manifest(
    records: list[dict[str, Any]],
    *,
    corpus: str,
    split: str,
    requested_clusters: int,
    sampling_seed: str,
    records_sha256: str,
    source_manifest_sha256: str,
    selection_control_file: str,
    selection_control_sha256: str,
) -> dict[str, Any]:
    config, split_config = corpus_config(corpus, split)
    require(requested_clusters > 0, "requested_clusters must be positive")
    require(isinstance(sampling_seed, str) and bool(sampling_seed), "Sampling seed is empty")
    require_sha(records_sha256, "records_sha256")
    require_sha(source_manifest_sha256, "source_manifest_sha256")
    require_sha(selection_control_sha256, "selection_control_sha256")

    records_by_id: dict[str, dict[str, Any]] = {}
    order: dict[str, int] = {}
    for index, record in enumerate(records):
        validate_record(record, corpus)
        record_id = record["record_id"]
        require(record_id not in records_by_id, "Duplicate record ID")
        records_by_id[record_id] = record
        order[record_id] = index

    grouped: dict[str, dict[str, Any]] = {}
    for record in records:
        if record["split"] != split:
            continue
        if record["quality"].get("eligible_for_packet_sampling") is not True:
            continue
        material = cluster_material(record, corpus)
        identifier = cluster_id(material)
        group = grouped.setdefault(
            identifier,
            {
                "material": material,
                "record_ids": [],
                "date_hit_record_ids": [],
            },
        )
        require(group["material"] == material, "Cluster-ID collision")
        group["record_ids"].append(record["record_id"])

    # Scan every record belonging to a selectable cluster, including records that are
    # retained only as context.  An ineligible segment must not let another segment
    # from the same post/speaker cluster evade exact-date quarantine.
    for record in records:
        if record["split"] != split:
            continue
        if corpus == "agyw_focus_groups" and record["speaker_id"] is None:
            # Collective turns have no speaker cluster. If displayed, they are still
            # scanned through the eligible target record's preceding context below.
            continue
        identifier = cluster_id(cluster_material(record, corpus))
        if identifier in grouped and content_has_exact_date(
            display_content(record, records_by_id)
        ):
            grouped[identifier]["date_hit_record_ids"].append(record["record_id"])

    require(grouped, "No content-eligible records in requested split")
    for group in grouped.values():
        group["record_ids"].sort(key=order.__getitem__)

    quarantined = {identifier: group for identifier, group in grouped.items() if group["date_hit_record_ids"]}
    available = {identifier: group for identifier, group in grouped.items() if not group["date_hit_record_ids"]}
    require(
        requested_clusters <= len(available),
        "Requested cluster count exceeds the post-quarantine candidate pool",
    )

    seed_hash = sha256_bytes(sampling_seed.encode("utf-8"))
    ranked = sorted(
        available,
        key=lambda identifier: hashlib.sha256(
            sampling_seed.encode("utf-8") + b"\x00" + identifier.encode("ascii")
        ).hexdigest(),
    )
    chosen = ranked[:requested_clusters]

    cluster_entries: list[dict[str, Any]] = []
    for identifier in chosen:
        group = available[identifier]
        material = group["material"]
        cluster_entries.append(
            {
                "cluster_id": identifier,
                "source_ids": [material["source_id"]],
                "speaker_ids": [material["speaker_id"]] if "speaker_id" in material else [],
                "record_ids": group["record_ids"],
                "review_status": "pending_two_person_privacy_review",
                "experiment_use_ready": False,
            }
        )

    quarantine_entries = [
        {
            "cluster_id": identifier,
            "record_ids": group["record_ids"],
            "reason": "exact_date_in_excerpt_or_displayed_context",
        }
        for identifier, group in sorted(quarantined.items())
    ]
    eligible_record_count = sum(len(group["record_ids"]) for group in grouped.values())
    available_record_count = sum(len(group["record_ids"]) for group in available.values())
    selected_record_count = sum(len(entry["record_ids"]) for entry in cluster_entries)

    manifest = {
        "document_type": "dreaddit_agyw_candidate_manifest",
        "schema_version": SCHEMA_VERSION,
        "pipeline_version": PIPELINE_VERSION,
        "corpus": corpus,
        "split": split,
        "experimental_role": split_config["role"],
        "status": "pending_two_person_privacy_review_and_external_governance",
        "records_file": config["records"].name,
        "records_sha256": records_sha256,
        "source_manifest_file": config["source_manifest"].name,
        "source_manifest_sha256": source_manifest_sha256,
        "selection_control_file": selection_control_file,
        "selection_control_sha256": selection_control_sha256,
        "cluster_unit": config["cluster_unit"],
        "sampling_algorithm": "sha256_rank_by_private_or_preregistered_seed_v1",
        "sampling_seed_sha256": seed_hash,
        "requested_cluster_count": requested_clusters,
        "eligible_before_exact_date_quarantine": {
            "clusters": len(grouped),
            "records": eligible_record_count,
        },
        "exact_date_quarantine": {
            "policy": "quarantine_entire_source_cluster_without_rewriting_canonical_records",
            "pattern_version": EXACT_DATE_PATTERN_VERSION,
            "clusters": len(quarantined),
            "records": sum(len(group["record_ids"]) for group in quarantined.values()),
            "quarantined_clusters": quarantine_entries,
        },
        "available_after_exact_date_quarantine": {
            "clusters": len(available),
            "records": available_record_count,
        },
        "selected": {"clusters": len(cluster_entries), "records": selected_record_count},
        "clusters": cluster_entries,
        "manual_privacy_review_required": True,
        "experiment_use_ready": False,
        "warning": CANDIDATE_WARNING,
    }
    validate_candidate_shape(manifest)
    return manifest


def validate_candidate_shape(manifest: dict[str, Any]) -> None:
    require(set(manifest) == CANDIDATE_KEYS, "Unexpected candidate-manifest fields")
    require(
        manifest.get("document_type") == "dreaddit_agyw_candidate_manifest",
        "Invalid candidate-manifest type",
    )
    require(manifest.get("schema_version") == SCHEMA_VERSION, "Candidate schema mismatch")
    require(manifest.get("pipeline_version") == PIPELINE_VERSION, "Candidate pipeline mismatch")
    config, split_config = corpus_config(str(manifest.get("corpus")), str(manifest.get("split")))
    require(manifest.get("experimental_role") == split_config["role"], "Experimental role mismatch")
    require(
        manifest.get("status") == "pending_two_person_privacy_review_and_external_governance",
        "Candidate status is not fail closed",
    )
    require(manifest.get("records_file") == config["records"].name, "Records filename mismatch")
    require(
        manifest.get("source_manifest_file") == config["source_manifest"].name,
        "Source-manifest filename mismatch",
    )
    for key in ("records_sha256", "source_manifest_sha256", "selection_control_sha256"):
        require_sha(manifest.get(key), key)
    require(
        isinstance(manifest.get("selection_control_file"), str)
        and manifest["selection_control_file"].endswith(".local.json"),
        "Invalid selection-control filename",
    )
    require(manifest.get("cluster_unit") == config["cluster_unit"], "Cluster-unit mismatch")
    require(
        manifest.get("sampling_algorithm") == "sha256_rank_by_private_or_preregistered_seed_v1",
        "Sampling algorithm changed",
    )
    require_sha(manifest.get("sampling_seed_sha256"), "sampling_seed_sha256")
    require(
        isinstance(manifest.get("requested_cluster_count"), int)
        and not isinstance(manifest.get("requested_cluster_count"), bool)
        and manifest["requested_cluster_count"] > 0,
        "Invalid requested cluster count",
    )
    for key in (
        "eligible_before_exact_date_quarantine",
        "available_after_exact_date_quarantine",
        "selected",
    ):
        value = manifest.get(key)
        require(isinstance(value, dict) and set(value) == COUNT_KEYS, f"Invalid {key}")
        require(
            all(isinstance(count, int) and not isinstance(count, bool) and count >= 0 for count in value.values()),
            f"Invalid counts in {key}",
        )
    quarantine = manifest.get("exact_date_quarantine")
    require(
        isinstance(quarantine, dict)
        and set(quarantine)
        == {"policy", "pattern_version", "clusters", "records", "quarantined_clusters"},
        "Invalid exact-date quarantine section",
    )
    require(
        quarantine.get("policy")
        == "quarantine_entire_source_cluster_without_rewriting_canonical_records",
        "Exact-date quarantine policy changed",
    )
    require(quarantine.get("pattern_version") == EXACT_DATE_PATTERN_VERSION, "Date pattern changed")
    quarantined_entries = quarantine.get("quarantined_clusters")
    require(isinstance(quarantined_entries, list), "Invalid quarantined cluster list")
    for entry in quarantined_entries:
        require(isinstance(entry, dict) and set(entry) == QUARANTINE_CLUSTER_KEYS, "Invalid quarantine entry")
        require(entry.get("reason") == "exact_date_in_excerpt_or_displayed_context", "Invalid quarantine reason")
        require(isinstance(entry.get("record_ids"), list) and entry["record_ids"], "Empty quarantine entry")
    require(quarantine.get("clusters") == len(quarantined_entries), "Quarantine cluster count mismatch")
    require(
        quarantine.get("records") == sum(len(entry["record_ids"]) for entry in quarantined_entries),
        "Quarantine record count mismatch",
    )
    clusters = manifest.get("clusters")
    require(isinstance(clusters, list) and clusters, "No selected clusters")
    require(len(clusters) == manifest["requested_cluster_count"], "Selected cluster count mismatch")
    seen_clusters: set[str] = set()
    seen_records: set[str] = set()
    for entry in clusters:
        require(isinstance(entry, dict) and set(entry) == CLUSTER_KEYS, "Invalid cluster entry")
        identifier = entry.get("cluster_id")
        require(isinstance(identifier, str) and identifier.startswith("review_cluster_"), "Invalid cluster ID")
        require(identifier not in seen_clusters, "Duplicate selected cluster")
        seen_clusters.add(identifier)
        require(
            isinstance(entry.get("source_ids"), list) and len(entry["source_ids"]) == 1,
            "Cluster must have one source ID",
        )
        require(isinstance(entry.get("speaker_ids"), list), "Invalid cluster speaker IDs")
        if manifest["corpus"] == "dreaddit":
            require(entry["speaker_ids"] == [], "Dreaddit cluster contains speaker IDs")
        else:
            require(len(entry["speaker_ids"]) == 1, "AGYW cluster must have one speaker ID")
        record_ids = entry.get("record_ids")
        require(isinstance(record_ids, list) and record_ids, "Selected cluster has no records")
        require(not seen_records.intersection(record_ids), "Record appears in multiple selected clusters")
        seen_records.update(record_ids)
        require(
            entry.get("review_status") == "pending_two_person_privacy_review"
            and entry.get("experiment_use_ready") is False,
            "Selected cluster bypasses review gate",
        )
    require(
        manifest["selected"] == {"clusters": len(clusters), "records": len(seen_records)},
        "Selected counts mismatch",
    )
    require(manifest.get("manual_privacy_review_required") is True, "Manual review gate missing")
    require(manifest.get("experiment_use_ready") is False, "Candidate manifest became experiment-ready")
    require(manifest.get("warning") == CANDIDATE_WARNING, "Candidate warning changed")


def prepare_candidate_from_paths(
    *,
    corpus: str,
    split: str,
    requested_clusters: int,
    sampling_seed: str,
    selection_control_path: Path,
) -> dict[str, Any]:
    """Build expected candidate manifest; control validation precedes records access."""
    config, _ = corpus_config(corpus, split)
    source_manifest_sha = file_sha256(config["source_manifest"])
    control, control_sha = read_json_snapshot(selection_control_path)
    seed_sha = sha256_bytes(sampling_seed.encode("utf-8"))
    validate_selection_control_before_record_access(
        control,
        corpus=corpus,
        split=split,
        requested_clusters=requested_clusters,
        sampling_seed_sha256=seed_sha,
        expected_source_manifest_sha256=source_manifest_sha,
    )
    # This is deliberately the first access to the protected records file.
    records, records_sha = read_records_snapshot(config["records"])
    require(
        control.get("records_sha256") == records_sha,
        "Selection-control records hash mismatch",
    )
    return build_candidate_manifest(
        records,
        corpus=corpus,
        split=split,
        requested_clusters=requested_clusters,
        sampling_seed=sampling_seed,
        records_sha256=records_sha,
        source_manifest_sha256=source_manifest_sha,
        selection_control_file=selection_control_path.name,
        selection_control_sha256=control_sha,
    )


def build_review_bundle(
    records: list[dict[str, Any]],
    candidate: dict[str, Any],
    *,
    candidate_file: str,
    candidate_sha256: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    validate_candidate_shape(candidate)
    corpus = candidate["corpus"]
    records_by_id: dict[str, dict[str, Any]] = {}
    for record in records:
        validate_record(record, corpus)
        require(record["record_id"] not in records_by_id, "Duplicate record ID")
        records_by_id[record["record_id"]] = record

    packets: list[dict[str, Any]] = []
    for cluster in candidate["clusters"]:
        for record_id in cluster["record_ids"]:
            require(record_id in records_by_id, "Candidate record is missing")
            record = records_by_id[record_id]
            require(record["split"] == candidate["split"], "Candidate record split changed")
            require(
                record["quality"].get("eligible_for_packet_sampling") is True,
                "Candidate record is no longer content-eligible",
            )
            content = display_content(record, records_by_id)
            require(
                not content_has_exact_date(content),
                "Exact date reached a review packet instead of quarantine",
            )
            content_sha = sha256_bytes(canonical_compact_bytes(content))
            item_id = "review_item_" + sha256_bytes(
                canonical_compact_bytes(
                    {"cluster_id": cluster["cluster_id"], "record_id": record_id, "content_sha256": content_sha}
                )
            )[:16]
            packets.append(
                {
                    "review_item_id": item_id,
                    "cluster_id": cluster["cluster_id"],
                    "record_id": record_id,
                    "content_sha256": content_sha,
                    "review_content": content,
                    "review_status": "pending_two_person_privacy_review",
                    "experiment_use_ready": False,
                }
            )

    require(packets, "No review packets were produced")
    packet_sha = sha256_bytes(canonical_jsonl_bytes(packets))
    ledger_entries = [
        {
            "review_item_id": packet["review_item_id"],
            "record_id": packet["record_id"],
            "cluster_id": packet["cluster_id"],
            "content_sha256": packet["content_sha256"],
            "required_distinct_reviewers": 2,
            "reviews": [],
            "privacy_review_complete": False,
            "permitted_uses": {
                "model_processing": False,
                "rater_display": False,
                "quotation": False,
            },
            "experiment_use_ready": False,
        }
        for packet in packets
    ]
    ledger = {
        "document_type": "dreaddit_agyw_privacy_review_ledger",
        "schema_version": SCHEMA_VERSION,
        "pipeline_version": PIPELINE_VERSION,
        "corpus": corpus,
        "split": candidate["split"],
        "candidate_manifest_file": candidate_file,
        "candidate_manifest_sha256": candidate_sha256,
        "packet_file": "privacy_review_packets.jsonl",
        "packet_sha256": packet_sha,
        "status": "pending_two_person_privacy_review",
        "entries": ledger_entries,
        "experiment_use_ready": False,
        "warning": LEDGER_WARNING,
    }
    validate_packet_shapes(packets)
    validate_ledger_shape_and_reviews(ledger, packets)
    return packets, ledger


def validate_packet_shapes(packets: list[dict[str, Any]]) -> None:
    require(packets, "Review packet file is empty")
    seen_items: set[str] = set()
    for packet in packets:
        require(set(packet) == PACKET_KEYS, "Unexpected review-packet fields")
        item_id = packet.get("review_item_id")
        require(isinstance(item_id, str) and item_id.startswith("review_item_"), "Invalid review item ID")
        require(item_id not in seen_items, "Duplicate review item ID")
        seen_items.add(item_id)
        content = packet.get("review_content")
        require(isinstance(content, dict) and set(content) == REVIEW_CONTENT_KEYS, "Invalid review content")
        context = content.get("context")
        require(isinstance(context, dict) and set(context) == REVIEW_CONTEXT_KEYS, "Invalid review context")
        require(isinstance(content.get("text"), str) and content["text"].strip(), "Empty excerpt")
        require(context.get("moderator_question") is None or isinstance(context["moderator_question"], str), "Invalid moderator context")
        preceding = context.get("preceding")
        require(isinstance(preceding, list), "Invalid preceding review context")
        for prior in preceding:
            require(isinstance(prior, dict) and set(prior) == PRECEDING_KEYS, "Invalid prior context item")
            require(isinstance(prior["record_id"], str) and isinstance(prior["text"], str), "Invalid prior context")
        require(
            packet.get("content_sha256") == sha256_bytes(canonical_compact_bytes(content)),
            "Review content hash mismatch",
        )
        require(not content_has_exact_date(content), "Review packet contains an exact date")
        require(
            packet.get("review_status") == "pending_two_person_privacy_review"
            and packet.get("experiment_use_ready") is False,
            "Review packet bypasses its pending gate",
        )


def derived_entry_state(entry: dict[str, Any]) -> tuple[bool, dict[str, bool], str]:
    reviews = entry["reviews"]
    reviewer_ids = [review["reviewer_id"] for review in reviews]
    require(len(reviewer_ids) == len(set(reviewer_ids)), "Privacy reviewers must be distinct")
    decisions = [review["decision"] for review in reviews]
    if any(decision == "rejected" for decision in decisions):
        return False, {key: False for key in PERMITTED_USE_KEYS}, "rejected"
    approvals = [review for review in reviews if review["decision"] == "approved_restricted"]
    complete = len(approvals) >= 2 and len(approvals) == len(reviews)
    if not complete:
        return False, {key: False for key in PERMITTED_USE_KEYS}, "pending"
    permitted = {
        "model_processing": all(review["model_processing_cleared"] for review in approvals),
        "rater_display": all(review["rater_display_cleared"] for review in approvals),
        "quotation": all(review["quotation_cleared"] for review in approvals),
    }
    return True, permitted, "complete"


def validate_review_record(review: dict[str, Any]) -> None:
    require(set(review) == REVIEW_KEYS, "Unexpected privacy-review fields")
    require(bool(REVIEWER_ID_RE.fullmatch(str(review.get("reviewer_id", "")))), "Invalid reviewer ID")
    parse_utc(review.get("reviewed_at_utc"), "reviewed_at_utc")
    require(
        review.get("decision") in {"approved_restricted", "needs_revision", "rejected"},
        "Invalid privacy-review decision",
    )
    for key in (
        "direct_identifiers_resolved",
        "contextual_risk_resolved",
        "model_processing_cleared",
        "rater_display_cleared",
        "quotation_cleared",
    ):
        require(isinstance(review.get(key), bool), f"Invalid review boolean {key}")
    if review["decision"] == "approved_restricted":
        require(
            review["direct_identifiers_resolved"] is True
            and review["contextual_risk_resolved"] is True,
            "Approved review has unresolved privacy risk",
        )
    else:
        require(
            review["model_processing_cleared"] is False
            and review["rater_display_cleared"] is False
            and review["quotation_cleared"] is False,
            "Nonapproved review cannot clear a use",
        )
    notes_reference = review.get("notes_reference")
    require(
        notes_reference is None
        or (
            isinstance(notes_reference, str)
            and bool(NOTES_REFERENCE_RE.fullmatch(notes_reference))
        ),
        "Invalid notes reference; use only an opaque review_note_* token",
    )


def validate_ledger_shape_and_reviews(
    ledger: dict[str, Any], packets: list[dict[str, Any]]
) -> dict[str, Any]:
    require(set(ledger) == LEDGER_KEYS, "Unexpected privacy-ledger fields")
    require(
        ledger.get("document_type") == "dreaddit_agyw_privacy_review_ledger",
        "Invalid privacy-ledger type",
    )
    require(ledger.get("schema_version") == SCHEMA_VERSION, "Ledger schema mismatch")
    require(ledger.get("pipeline_version") == PIPELINE_VERSION, "Ledger pipeline mismatch")
    config, _ = corpus_config(str(ledger.get("corpus")), str(ledger.get("split")))
    require(
        ledger.get("candidate_manifest_file") == "candidate_manifest.json",
        "Candidate-manifest filename changed",
    )
    require_sha(ledger.get("candidate_manifest_sha256"), "candidate_manifest_sha256")
    require_sha(ledger.get("packet_sha256"), "packet_sha256")
    require(ledger.get("packet_file") == "privacy_review_packets.jsonl", "Packet filename changed")
    require(ledger.get("warning") == LEDGER_WARNING, "Ledger warning changed")
    require(ledger.get("experiment_use_ready") is False, "Ledger became experiment-ready")
    require(
        ledger.get("packet_sha256") == sha256_bytes(canonical_jsonl_bytes(packets)),
        "Ledger packet hash mismatch",
    )
    packet_by_item = {packet["review_item_id"]: packet for packet in packets}
    require(len(packet_by_item) == len(packets), "Duplicate packet review item")
    require(
        all(
            packet["review_content"]["corpus"] == ledger["corpus"]
            and packet["review_content"]["split"] == ledger["split"]
            for packet in packets
        ),
        "Ledger corpus/split differs from review packets",
    )
    require(config["records"].name == "records.jsonl", "Unexpected canonical records name")
    entries = ledger.get("entries")
    require(isinstance(entries, list) and len(entries) == len(packets), "Ledger coverage mismatch")
    seen: set[str] = set()
    states: Counter[str] = Counter()
    for entry in entries:
        require(isinstance(entry, dict) and set(entry) == LEDGER_ENTRY_KEYS, "Invalid ledger entry")
        item_id = entry.get("review_item_id")
        require(item_id in packet_by_item and item_id not in seen, "Ledger item mismatch")
        seen.add(item_id)
        packet = packet_by_item[item_id]
        for key in ("record_id", "cluster_id", "content_sha256"):
            require(entry.get(key) == packet.get(key), f"Ledger {key} mismatch")
        require(entry.get("required_distinct_reviewers") == 2, "Two reviewers are required")
        reviews = entry.get("reviews")
        require(isinstance(reviews, list), "Ledger reviews must be a list")
        for review in reviews:
            require(isinstance(review, dict), "Invalid privacy-review record")
            validate_review_record(review)
        complete, permitted, state = derived_entry_state(entry)
        states[state] += 1
        require(entry.get("privacy_review_complete") is complete, "Stored review completion is wrong")
        require(
            isinstance(entry.get("permitted_uses"), dict)
            and set(entry["permitted_uses"]) == PERMITTED_USE_KEYS
            and entry["permitted_uses"] == permitted,
            "Stored permitted-use intersection is wrong",
        )
        require(entry.get("experiment_use_ready") is False, "Ledger entry became experiment-ready")
    require(seen == set(packet_by_item), "Ledger omits review packets")
    if states["rejected"]:
        expected_status = "contains_rejected_items"
    elif states["complete"] == len(entries):
        expected_status = "privacy_review_complete_local_governance_still_required"
    else:
        expected_status = "pending_two_person_privacy_review"
    require(ledger.get("status") == expected_status, "Ledger status does not match reviews")
    return {
        "review_items": len(entries),
        "privacy_review_complete": states["complete"],
        "pending": states["pending"],
        "rejected": states["rejected"],
        "experiment_use_ready": 0,
    }


def build_dreaddit_exact_date_audit(
    records: list[dict[str, Any]], records_sha256: str
) -> dict[str, Any]:
    hits: list[dict[str, Any]] = []
    all_eligible = Counter()
    for record in records:
        validate_record(record, "dreaddit")
        if record["quality"].get("eligible_for_packet_sampling") is True:
            all_eligible[record["split"]] += 1
        if EXACT_DATE_RE.search(record["text"]):
            hits.append(
                {
                    "record_id": record["record_id"],
                    "source_id": record["source_id"],
                    "split": record["split"],
                    "content_rule_eligible": record["quality"].get("eligible_for_packet_sampling")
                    is True,
                }
            )
    hits.sort(key=lambda item: item["record_id"])
    affected_sources = {item["source_id"] for item in hits}
    quarantined_eligible = Counter(
        record["split"]
        for record in records
        if record["source_id"] in affected_sources
        and record["quality"].get("eligible_for_packet_sampling") is True
    )
    after = {
        split: all_eligible[split] - quarantined_eligible[split]
        for split in sorted(all_eligible)
    }
    return {
        "document_type": "dreaddit_exact_date_quarantine_audit",
        "schema_version": SCHEMA_VERSION,
        "pipeline_version": PIPELINE_VERSION,
        "corpus": "dreaddit",
        "records_sha256": records_sha256,
        "pattern_version": EXACT_DATE_PATTERN_VERSION,
        "status": "quarantine_required_pending_manual_privacy_review",
        "records_rewritten": False,
        "quarantine_unit": "entire_post_cluster",
        "matched_records": len(hits),
        "matched_post_clusters": len(affected_sources),
        "matches": hits,
        "content_rule_eligible_before_quarantine": dict(sorted(all_eligible.items())),
        "content_rule_eligible_quarantined_by_cluster": dict(
            sorted(quarantined_eligible.items())
        ),
        "content_rule_eligible_after_cluster_quarantine": after,
        "manual_privacy_review_required": True,
        "experiment_use_ready": False,
        "warning": (
            "Pattern matches are quarantined rather than silently rewritten. They are not a "
            "complete privacy screen, and nonmatching records still require human review."
        ),
    }


def build_agyw_reconciliation_audit(
    build_report: dict[str, Any],
    build_report_sha256: str,
    source_manifest: dict[str, Any],
    source_manifest_sha256: str,
) -> dict[str, Any]:
    require_sha(build_report_sha256, "build_report_sha256")
    require_sha(source_manifest_sha256, "source_manifest_sha256")
    reported = source_manifest.get("reported_collection", {}).get("participants")
    require(isinstance(reported, int) and not isinstance(reported, bool), "Missing reported participants")
    require(build_report.get("corpus") == "agyw_focus_groups", "AGYW build-report corpus mismatch")
    observed = build_report.get("observed_participant_keys")
    require(
        isinstance(observed, int) and not isinstance(observed, bool) and observed >= 0,
        "Missing observed participant-key count",
    )
    require(
        build_report.get("reported_participants") == reported,
        "Build report and source manifest disagree on reported participants",
    )
    files = build_report.get("files")
    require(isinstance(files, dict) and files, "Missing AGYW per-focus-group report")
    by_source = {
        source_id: {
            "participant_turns": values["participant"],
            "collective_turns": values["collective"],
            "records": values["participant"] + values["collective"],
        }
        for source_id, values in sorted(files.items())
    }
    for source_id, values in by_source.items():
        require(source_id.startswith("agyw_fgd_"), "Unexpected AGYW focus-group ID")
        require(
            all(isinstance(value, int) and not isinstance(value, bool) and value >= 0 for value in values.values()),
            "Invalid AGYW focus-group counts",
        )
    record_counts = build_report.get("record_counts")
    require(isinstance(record_counts, dict), "Missing AGYW aggregate record counts")
    require(
        sum(item["participant_turns"] for item in by_source.values())
        == record_counts.get("participant")
        and sum(item["collective_turns"] for item in by_source.values())
        == record_counts.get("collective"),
        "AGYW per-focus-group and aggregate counts disagree",
    )
    return {
        "document_type": "agyw_participant_reconciliation_audit",
        "schema_version": SCHEMA_VERSION,
        "pipeline_version": PIPELINE_VERSION,
        "corpus": "agyw_focus_groups",
        "build_report_sha256": build_report_sha256,
        "source_manifest_sha256": source_manifest_sha256,
        "status": "unresolved_requires_source_confirmation",
        "reported_source_participants": reported,
        "observed_transcript_local_speaker_keys": observed,
        "observed_minus_reported": observed - reported,
        "focus_groups": len(by_source),
        "by_focus_group": by_source,
        "identity_scope": "transcript_local_only",
        "per_focus_group_speaker_key_distribution_available": False,
        "cross_focus_group_identity_inference_permitted": False,
        "participant_coverage_claim_permitted": False,
        "experiment_use_ready": False,
        "unverified_explanations": [
            "A participant may be absent from parsed speaking turns.",
            "Two source labels may have been normalized to one transcript-local key.",
            "The paper count and deposited transcript participation may differ.",
        ],
        "required_resolution": (
            "Obtain source confirmation or a documented transcript-level participant roster; "
            "do not infer or invent the missing identity."
        ),
        "warning": (
            "This audit is regenerated from the text-free aggregate build report and contains "
            "no transcript text or raw participant identity. It does not reconcile 106 observed "
            "keys with 107 reported people."
        ),
    }


def enforce_control_path(path: Path) -> Path:
    resolved = path.resolve()
    require(is_within(resolved, REVIEW_CONTROL_ROOT), "Selection control must remain in restricted review_controls")
    require(resolved.name.endswith(".local.json"), "Selection control must use an untracked .local.json name")
    require_private_file(resolved, "selection control")
    require(mode(resolved.parent) == 0o700, "Selection-control directory must be mode 0700")
    return resolved


def enforce_candidate_output(path: Path, corpus: str) -> Path:
    resolved = path.resolve()
    require(is_within(resolved, REVIEW_RUNTIME_ROOT / corpus), "Candidate output is outside its restricted corpus root")
    require(resolved.name == "candidate_manifest.json", "Candidate output must be candidate_manifest.json")
    return resolved


def enforce_runtime_candidate(path: Path, corpus: str) -> Path:
    resolved = path.resolve()
    require(is_within(resolved, REVIEW_RUNTIME_ROOT / corpus), "Candidate manifest is outside its restricted corpus root")
    require(resolved.name == "candidate_manifest.json", "Unexpected candidate-manifest filename")
    require_private_file(resolved, "candidate manifest")
    require(mode(resolved.parent) == 0o700, "Candidate runtime directory must be mode 0700")
    return resolved


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    sample = subparsers.add_parser("sample", help="Build a text-free cluster candidate manifest")
    sample.add_argument("--corpus", choices=tuple(CORPORA), required=True)
    sample.add_argument("--split", required=True)
    sample.add_argument("--clusters", type=int, required=True)
    sample.add_argument("--seed", required=True)
    sample.add_argument("--selection-control", type=Path, required=True)
    sample.add_argument("--output", type=Path, required=True)
    sample.add_argument("--replace", action="store_true")

    bundle = subparsers.add_parser(
        "build-review-bundle", help="Build restricted packets and an empty text-free ledger"
    )
    bundle.add_argument("--corpus", choices=tuple(CORPORA), required=True)
    bundle.add_argument("--split", required=True)
    bundle.add_argument("--clusters", type=int, required=True)
    bundle.add_argument("--seed", required=True)
    bundle.add_argument("--selection-control", type=Path, required=True)
    bundle.add_argument("--candidate-manifest", type=Path, required=True)
    bundle.add_argument("--replace", action="store_true")

    return parser.parse_args()


def run_sample(args: argparse.Namespace) -> dict[str, Any]:
    control_path = enforce_control_path(args.selection_control)
    output = enforce_candidate_output(args.output, args.corpus)
    manifest = prepare_candidate_from_paths(
        corpus=args.corpus,
        split=args.split,
        requested_clusters=args.clusters,
        sampling_seed=args.seed,
        selection_control_path=control_path,
    )
    atomic_write_private(output, canonical_json_bytes(manifest), args.replace)
    return {
        "status": manifest["status"],
        "corpus": manifest["corpus"],
        "split": manifest["split"],
        "selected": manifest["selected"],
        "exact_date_quarantine": {
            "clusters": manifest["exact_date_quarantine"]["clusters"],
            "records": manifest["exact_date_quarantine"]["records"],
        },
        "experiment_use_ready": False,
        "output": output.name,
    }


def run_build_review_bundle(args: argparse.Namespace) -> dict[str, Any]:
    control_path = enforce_control_path(args.selection_control)
    candidate_path = enforce_runtime_candidate(args.candidate_manifest, args.corpus)
    candidate, candidate_sha = read_json_snapshot(candidate_path)
    expected = prepare_candidate_from_paths(
        corpus=args.corpus,
        split=args.split,
        requested_clusters=args.clusters,
        sampling_seed=args.seed,
        selection_control_path=control_path,
    )
    require(candidate == expected, "Candidate manifest does not match current inputs/control/seed")
    config, _ = corpus_config(args.corpus, args.split)
    records, records_sha = read_records_snapshot(config["records"])
    require(records_sha == candidate["records_sha256"], "Records changed during bundle preparation")
    packets, ledger = build_review_bundle(
        records,
        candidate,
        candidate_file=candidate_path.name,
        candidate_sha256=candidate_sha,
    )
    packet_path = candidate_path.parent / "privacy_review_packets.jsonl"
    ledger_path = candidate_path.parent / "privacy_review_ledger.json"
    if not args.replace:
        require(not packet_path.exists() and not ledger_path.exists(), "Review bundle already exists")
    atomic_write_private(packet_path, canonical_jsonl_bytes(packets), args.replace)
    atomic_write_private(ledger_path, canonical_json_bytes(ledger), args.replace)
    return {
        "status": ledger["status"],
        "corpus": ledger["corpus"],
        "split": ledger["split"],
        "review_items": len(ledger["entries"]),
        "required_distinct_reviewers_per_item": 2,
        "experiment_use_ready": False,
        "packet_file": packet_path.name,
        "ledger_file": ledger_path.name,
    }


def main() -> None:
    args = parse_args()
    try:
        if args.command == "sample":
            result = run_sample(args)
        elif args.command == "build-review-bundle":
            result = run_build_review_bundle(args)
        else:  # pragma: no cover
            raise ValueError("Unknown command")
        print(json.dumps(result, indent=2, sort_keys=True))
    except (FileExistsError, json.JSONDecodeError, OSError, TypeError, ValueError) as exc:
        if isinstance(exc, OSError):
            print("Dreaddit/AGYW review preparation blocked: restricted file operation failed", file=sys.stderr)
        else:
            print(f"Dreaddit/AGYW review preparation blocked: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
