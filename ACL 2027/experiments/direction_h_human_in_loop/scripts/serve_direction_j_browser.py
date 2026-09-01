#!/usr/bin/env python3
"""Serve the exact Direction J Charlie queue through a fail-closed browser UI.

This synthetic-only instrument never opens Direction J's private item key.  It
requires a completed, non-Charlie activation record and prospectively recorded
qualification artifacts before it displays an analysis item.  Ratings lock
before feedback, use Direction J's exact actor-neutral schema, and are never
overwritten.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
import warnings
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

warnings.filterwarnings("ignore", category=DeprecationWarning)

try:
    from jsonschema import Draft202012Validator, FormatChecker, RefResolver
except ModuleNotFoundError:
    candidates = [
        Path.home() / "miniconda3" / "bin" / "python3",
        Path("/usr/bin/python3"),
        Path("/usr/local/bin/python3"),
    ]
    for candidate in candidates:
        if not candidate.is_file() or candidate.resolve() == Path(sys.executable).resolve():
            continue
        if subprocess.run(
            [str(candidate), "-c", "import jsonschema"], capture_output=True, check=False
        ).returncode == 0:
            os.execv(str(candidate), [str(candidate), __file__, *sys.argv[1:]])
    raise SystemExit("No local Python runtime with jsonschema is available; nothing was served.")


DIRECTION_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[3]
BRIDGE_ROOT = DIRECTION_ROOT / "companion_j_bridge"
BROWSER_ROOT = BRIDGE_ROOT / "browser"
RESPONSE_ROOT = BROWSER_ROOT / "responses"
LOCKED_ROOT = RESPONSE_ROOT / "locked"
MANIFEST_PATH = BROWSER_ROOT / "manifest.json"
ACTIVATION_PATH = BROWSER_ROOT / "activation_record.json"
ACTOR_REGISTRY_PATH = DIRECTION_ROOT / "coordinator_only" / "direction_j_browser_actor_registry.json"
COMPREHENSION_PATH = DIRECTION_ROOT / "coordinator_only" / "direction_j_browser_comprehension_record.json"

J_ROOT = PROJECT_ROOT / "experiments" / "direction_j_llm_as_rater"
J_RUN_ROOT = J_ROOT / "runs" / "20260825_synthetic_paired_qualification_prepared"
J_RUN_MANIFEST = J_RUN_ROOT / "run_manifest.json"
J_ITEMS_PATH = J_RUN_ROOT / "evaluator_items.jsonl"
J_ASSIGNMENT_PATH = J_RUN_ROOT / "assignments" / "charlie_rep1.csv"
J_GUIDE_PATH = J_ROOT / "protocol" / "shared_rater_guide_v1.md"
J_ITEM_SCHEMA_PATH = J_ROOT / "schemas" / "evaluator_item.schema.json"
J_RATING_SCHEMA_PATH = J_ROOT / "schemas" / "shared_rating.schema.json"
J_ACTOR_SCHEMA_PATH = J_ROOT / "schemas" / "actor_registry.schema.json"

BASE_FEEDBACK_SCHEMA_PATH = DIRECTION_ROOT / "schemas" / "feedback_record.schema.json"
BROWSER_FEEDBACK_SCHEMA_PATH = DIRECTION_ROOT / "schemas" / "direction_j_browser_feedback.schema.json"
TIMING_SCHEMA_PATH = DIRECTION_ROOT / "schemas" / "direction_j_browser_timing_receipt.schema.json"
BROWSER_MANIFEST_SCHEMA_PATH = DIRECTION_ROOT / "schemas" / "direction_j_browser_manifest.schema.json"
ACTIVATION_SCHEMA_PATH = DIRECTION_ROOT / "schemas" / "direction_j_browser_activation.schema.json"
COMPREHENSION_SCHEMA_PATH = DIRECTION_ROOT / "schemas" / "direction_j_browser_comprehension_record.schema.json"

INSTRUMENT_VERSION = "direction-h-direction-j-browser-v1"
BRIDGE_ID = "direction-h-direction-j-synthetic-qualification-v1"
MAX_REQUEST_BYTES = 131_072
ALLOWED_LOCATION_PREFIXES = (
    "/proposed_interpretation/theme_name",
    "/proposed_interpretation/claim",
    "/proposed_interpretation/explanation",
    "/proposed_interpretation/boundary_conditions/",
)
EDITABLE_EVIDENCE_FIELDS = {
    "candidate_role",
    "candidate_attributed_excerpt_id",
    "candidate_attributed_source_id",
    "candidate_attributed_speaker_id",
    "candidate_quote",
    "candidate_warrant",
}


class InstrumentError(RuntimeError):
    """A preflight, validation, or collection stop condition."""


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def rendered_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_utc(value: str, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise InstrumentError(f"{label} is not an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise InstrumentError(f"{label} lacks a UTC offset")
    return parsed.astimezone(timezone.utc)


def load_json(path: Path, label: str) -> Any:
    if path.is_symlink() or not path.is_file():
        raise InstrumentError(f"{label} is missing or unsafe: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise InstrumentError(f"cannot parse {label}: {exc}") from exc


def require_project_file(relative_path: str, label: str) -> Path:
    candidate = PROJECT_ROOT / relative_path
    if candidate.is_symlink():
        raise InstrumentError(f"{label} may not be a symlink: {relative_path}")
    resolved = candidate.resolve()
    try:
        resolved.relative_to(PROJECT_ROOT.resolve())
    except ValueError as exc:
        raise InstrumentError(f"{label} leaves the project root: {relative_path}") from exc
    if not resolved.is_file():
        raise InstrumentError(f"{label} is missing: {relative_path}")
    return resolved


def schema_store() -> dict[str, Any]:
    paths = [
        J_ITEM_SCHEMA_PATH,
        J_RATING_SCHEMA_PATH,
        J_ACTOR_SCHEMA_PATH,
        BASE_FEEDBACK_SCHEMA_PATH,
        BROWSER_FEEDBACK_SCHEMA_PATH,
        TIMING_SCHEMA_PATH,
        BROWSER_MANIFEST_SCHEMA_PATH,
        ACTIVATION_SCHEMA_PATH,
        COMPREHENSION_SCHEMA_PATH,
    ]
    store: dict[str, Any] = {}
    for path in paths:
        schema = load_json(path, f"schema {path.name}")
        Draft202012Validator.check_schema(schema)
        if "$id" in schema:
            store[schema["$id"]] = schema
    return store


def validate(value: Any, schema_path: Path, label: str, store: dict[str, Any]) -> None:
    schema = load_json(schema_path, f"{label} schema")
    resolver = RefResolver.from_schema(schema, store=store)
    validator = Draft202012Validator(
        schema, resolver=resolver, format_checker=FormatChecker()
    )
    errors = sorted(validator.iter_errors(value), key=lambda error: list(error.path))
    if errors:
        detail = "; ".join(
            f"/{'/'.join(str(part) for part in error.path)}: {error.message}"
            for error in errors[:8]
        )
        raise InstrumentError(f"{label} fails schema: {detail}")


def load_assignments() -> list[dict[str, str]]:
    with J_ASSIGNMENT_PATH.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 24:
        raise InstrumentError("Charlie assignment must contain exactly 24 rows")
    required = {
        "assignment_id", "actor_id", "actor_kind", "rating_repetition", "sequence",
        "item_id", "item_payload_sha256", "interface_version",
        "shared_rater_guide_version", "shared_rater_guide_sha256",
        "semantic_input_sha256", "packet_id", "output_id", "corpus_id",
        "evaluation_role",
    }
    if set(rows[0]) != required:
        raise InstrumentError("Charlie assignment columns drifted")
    for index, row in enumerate(rows, start=1):
        if row["actor_id"] != "charlie" or row["actor_kind"] != "human":
            raise InstrumentError("Charlie assignment actor drifted")
        if row["rating_repetition"] != "1" or row["sequence"] != str(index):
            raise InstrumentError("Charlie assignment order/repetition drifted")
    return rows


def load_items(store: dict[str, Any]) -> dict[str, dict[str, Any]]:
    items: dict[str, dict[str, Any]] = {}
    for line_number, line in enumerate(J_ITEMS_PATH.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise InstrumentError(f"evaluator item line {line_number} is invalid JSON") from exc
        validate(item, J_ITEM_SCHEMA_PATH, f"evaluator item line {line_number}", store)
        item_id = item["item_id"]
        if item_id in items:
            raise InstrumentError(f"duplicate evaluator item: {item_id}")
        items[item_id] = item
    if len(items) != 24:
        raise InstrumentError("Direction J evaluator bank must contain exactly 24 items")
    return items


def verify_assignment_items(
    assignments: list[dict[str, str]], items: dict[str, dict[str, Any]]
) -> None:
    guide_hash = sha256_file(J_GUIDE_PATH)
    if len({row["item_id"] for row in assignments}) != 24:
        raise InstrumentError("Charlie assignment contains duplicate item IDs")
    for row in assignments:
        item = items.get(row["item_id"])
        if item is None:
            raise InstrumentError(f"assigned item is absent: {row['item_id']}")
        item_hash = sha256_bytes(canonical_bytes(item))
        if item_hash != row["item_payload_sha256"]:
            raise InstrumentError(f"item payload hash mismatch: {row['item_id']}")
        for field in ("packet_id", "output_id", "corpus_id"):
            if item[field] != row[field]:
                raise InstrumentError(f"assignment/item {field} mismatch: {row['item_id']}")
        if row["shared_rater_guide_sha256"] != guide_hash:
            raise InstrumentError("shared guide hash drifted in Charlie assignment")
        semantic = {
            "interface_version": row["interface_version"],
            "item_payload_sha256": item_hash,
            "shared_rater_guide_sha256": guide_hash,
            "shared_rater_guide_version": row["shared_rater_guide_version"],
        }
        if sha256_bytes(canonical_bytes(semantic)) != row["semantic_input_sha256"]:
            raise InstrumentError(f"semantic input hash mismatch: {row['item_id']}")


def response_stem(row: dict[str, str]) -> str:
    return f"{int(row['sequence']):03d}_{row['item_id']}"


def response_dir(row: dict[str, str]) -> Path:
    return LOCKED_ROOT / response_stem(row)


def response_state(assignments: list[dict[str, str]]) -> tuple[int, dict[str, str] | None, str]:
    completed = 0
    pending: dict[str, str] | None = None
    gap_seen = False
    if RESPONSE_ROOT.exists():
        allowed_root = {"README.md", "locked"}
        extra = {path.name for path in RESPONSE_ROOT.iterdir()} - allowed_root
        if extra:
            raise InstrumentError("browser response root contains an unexpected entry")
    if LOCKED_ROOT.exists() and (LOCKED_ROOT.is_symlink() or not LOCKED_ROOT.is_dir()):
        raise InstrumentError("browser locked-response path is unsafe")
    expected_dirs = {response_stem(row) for row in assignments}
    if LOCKED_ROOT.exists():
        actual_entries = {path.name for path in LOCKED_ROOT.iterdir()}
        unexpected = actual_entries - expected_dirs
        if unexpected:
            raise InstrumentError("browser response area contains an unexpected entry")
    for row in assignments:
        directory = response_dir(row)
        if not directory.exists():
            gap_seen = True
            if pending is None:
                pending = row
            continue
        if directory.is_symlink() or not directory.is_dir():
            raise InstrumentError(f"unsafe response directory: {directory.name}")
        rating = directory / "rating.json"
        timing = directory / "timing_receipt.json"
        feedback = directory / "feedback_commit" / "feedback.json"
        if not rating.is_file() or not timing.is_file():
            raise InstrumentError(f"partial rating lock: {directory.name}")
        if feedback.is_file():
            if gap_seen:
                raise InstrumentError("completed response appears after a sequence gap")
            completed += 1
        else:
            if pending is not None and pending is not row:
                raise InstrumentError("multiple incomplete response positions exist")
            pending = row
            gap_seen = True
            return completed, pending, "feedback_pending"
    return completed, pending, "next_rating" if pending else "complete"


def validate_prepared() -> dict[str, Any]:
    store = schema_store()
    manifest = load_json(MANIFEST_PATH, "browser manifest")
    validate(manifest, BROWSER_MANIFEST_SCHEMA_PATH, "browser manifest", store)
    if manifest["status"] != "prepared_not_activated_or_run":
        raise InstrumentError("browser manifest is not in its prepared state")
    if manifest["data_scope"] != "synthetic_qualification_only" or manifest[
        "contains_real_source_text"
    ] is not False:
        raise InstrumentError("browser manifest is not synthetic-only")
    for label, lock in manifest["file_locks"].items():
        path = require_project_file(lock["path"], f"browser lock {label}")
        if sha256_file(path) != lock["sha256"]:
            raise InstrumentError(f"browser locked artifact drifted: {label}")
    files = manifest["instrument_bundle"]["files"]
    mapping = {}
    locks_by_path = {lock["path"]: lock["sha256"] for lock in manifest["file_locks"].values()}
    for path in files:
        if path not in locks_by_path:
            raise InstrumentError(f"instrument bundle path is not file-locked: {path}")
        mapping[path] = locks_by_path[path]
    if sha256_bytes(canonical_bytes(mapping)) != manifest["instrument_bundle"]["sha256"]:
        raise InstrumentError("browser instrument-bundle hash drifted")

    run_manifest = load_json(J_RUN_MANIFEST, "Direction J run manifest")
    if run_manifest.get("contains_real_source_text") is not False:
        raise InstrumentError("Direction J run manifest does not prove synthetic-only input")
    if int(run_manifest.get("ratings_collected", 0)) != 0:
        raise InstrumentError("Direction J prepared run unexpectedly reports collected ratings")
    assignments = load_assignments()
    items = load_items(store)
    verify_assignment_items(assignments, items)
    completed, pending, state = response_state(assignments)
    return {
        "store": store,
        "manifest": manifest,
        "assignments": assignments,
        "items": items,
        "completed_count": completed,
        "pending": pending,
        "response_state": state,
    }


def verify_comprehension(record: dict[str, Any]) -> None:
    if record["record_status"] != "scored" or record["final_status"] not in {
        "passed", "passed_after_retraining"
    }:
        raise InstrumentError("Charlie comprehension check is not prospectively passed")
    expected = {"TQ1": "C", "TQ2": "B"}
    attempts = record["attempts"]
    if not attempts or len(attempts) > 2:
        raise InstrumentError("comprehension record has an invalid attempt count")
    for index, attempt in enumerate(attempts, start=1):
        if attempt["attempt"] != index:
            raise InstrumentError("comprehension attempts are not contiguous")
        correct = sum(attempt["responses"].get(key) == value for key, value in expected.items())
        if attempt["correct_count"] != correct or attempt["passed"] != (correct == 2):
            raise InstrumentError("comprehension scoring does not match the frozen key")
        if index == 1 and attempt["remediation_completed"] is not False:
            raise InstrumentError("first comprehension attempt cannot claim remediation")
        if index == 2 and attempt["remediation_completed"] is not True:
            raise InstrumentError("second comprehension attempt lacks recorded remediation")
    if record["final_status"] == "passed" and not (len(attempts) == 1 and attempts[0]["passed"]):
        raise InstrumentError("comprehension final status does not match attempts")
    if record["final_status"] == "passed_after_retraining" and not (
        len(attempts) == 2 and not attempts[0]["passed"] and attempts[1]["passed"]
    ):
        raise InstrumentError("retraining status does not match attempts")


def validate_activation(prepared: dict[str, Any]) -> dict[str, Any]:
    store = prepared["store"]
    if not ACTIVATION_PATH.is_file():
        raise InstrumentError(
            "browser queue is prepared but not activated: a non-Charlie coordinator must "
            "create companion_j_bridge/browser/activation_record.json"
        )
    activation = load_json(ACTIVATION_PATH, "browser activation record")
    validate(activation, ACTIVATION_SCHEMA_PATH, "browser activation record", store)
    if activation["record_status"] != "activated":
        raise InstrumentError("browser activation record is incomplete")
    actual_locks = {
        "browser_manifest_sha256": sha256_file(MANIFEST_PATH),
        "direction_j_run_manifest_sha256": sha256_file(J_RUN_MANIFEST),
        "evaluator_items_sha256": sha256_file(J_ITEMS_PATH),
        "charlie_assignment_sha256": sha256_file(J_ASSIGNMENT_PATH),
        "shared_rater_guide_sha256": sha256_file(J_GUIDE_PATH),
        "shared_rating_schema_sha256": sha256_file(J_RATING_SCHEMA_PATH),
        "actor_registry_sha256": sha256_file(ACTOR_REGISTRY_PATH)
        if ACTOR_REGISTRY_PATH.is_file() else None,
        "comprehension_record_sha256": sha256_file(COMPREHENSION_PATH)
        if COMPREHENSION_PATH.is_file() else None,
    }
    if activation["locks"] != actual_locks:
        raise InstrumentError("browser activation locks do not match current artifacts")
    activated_at = parse_utc(activation["activated_at_utc"], "activation time")
    if activated_at > datetime.now(timezone.utc):
        raise InstrumentError("browser activation time is in the future")

    actor_registry = load_json(ACTOR_REGISTRY_PATH, "Direction J Charlie actor registry")
    validate(actor_registry, J_ACTOR_SCHEMA_PATH, "Direction J Charlie actor registry", store)
    actors = [actor for actor in actor_registry["actors"] if actor["actor_id"] == "charlie"]
    if len(actors) != 1:
        raise InstrumentError("actor registry must contain exactly one charlie actor")
    actor = actors[0]
    profile = actor.get("human_profile", {})
    if actor["actor_kind"] != "human" or profile.get("evaluator_group") != "researcher":
        raise InstrumentError("Charlie actor registry role is incompatible")
    if profile.get("helped_construct") is not True or profile.get(
        "independence_eligibility"
    ) != "ineligible":
        raise InstrumentError("Charlie must remain a construction-involved ineligible case")
    if profile.get("qualifications_recorded") is not True:
        raise InstrumentError("Charlie's actual qualifications are not recorded")
    if profile.get("tutorial_version") != "direction-h-direction-j-browser-tutorial-v1":
        raise InstrumentError("Charlie actor registry tutorial version drifted")

    comprehension = load_json(COMPREHENSION_PATH, "Charlie comprehension record")
    validate(comprehension, COMPREHENSION_SCHEMA_PATH, "Charlie comprehension record", store)
    verify_comprehension(comprehension)
    if profile.get("comprehension_check_status") != comprehension["final_status"]:
        raise InstrumentError("actor registry/comprehension status mismatch")
    if sha256_file(BROWSER_ROOT / "tutorial" / "comprehension_check_v1.json") != comprehension[
        "tutorial_packet_sha256"
    ]:
        raise InstrumentError("comprehension packet hash drifted")
    for path in (ACTOR_REGISTRY_PATH, COMPREHENSION_PATH):
        if datetime.fromtimestamp(path.stat().st_mtime, timezone.utc) > activated_at:
            raise InstrumentError("qualification artifact was modified after queue activation")
    return {**prepared, "activation": activation, "actor_registry": actor_registry}


def decode_pointer_token(token: str) -> str:
    output = []
    index = 0
    while index < len(token):
        if token[index] != "~":
            output.append(token[index])
            index += 1
        elif index + 1 < len(token) and token[index + 1] in {"0", "1"}:
            output.append("~" if token[index + 1] == "0" else "/")
            index += 2
        else:
            raise InstrumentError("malformed JSON Pointer escape")
    return "".join(output)


def resolve_pointer(document: Any, pointer: str) -> Any:
    if not pointer.startswith("/"):
        raise InstrumentError("feedback pointer must start with /")
    current = document
    for raw in pointer[1:].split("/"):
        token = decode_pointer_token(raw)
        if isinstance(current, dict) and token in current:
            current = current[token]
        elif isinstance(current, list) and token.isdigit() and str(int(token)) == token:
            index = int(token)
            if index >= len(current):
                raise InstrumentError("feedback pointer index is out of range")
            current = current[index]
        else:
            raise InstrumentError("feedback pointer does not resolve")
    return current


def editable_pointer(pointer: str) -> bool:
    if pointer in ALLOWED_LOCATION_PREFIXES[:3]:
        return True
    if pointer.startswith(ALLOWED_LOCATION_PREFIXES[3]):
        suffix = pointer[len(ALLOWED_LOCATION_PREFIXES[3]):]
        return suffix.isdigit()
    parts = pointer.split("/")
    return (
        len(parts) == 4
        and parts[1] == "evidence"
        and parts[2].isdigit()
        and parts[3] in EDITABLE_EVIDENCE_FIELDS
    )


def validate_findings(item: dict[str, Any], feedback: dict[str, Any], rating: dict[str, Any]) -> None:
    def strings(value: Any):
        if isinstance(value, str):
            yield value
        elif isinstance(value, dict):
            for nested_value in value.values():
                yield from strings(nested_value)
        elif isinstance(value, list):
            for nested_value in value:
                yield from strings(nested_value)

    model_text = "\n".join(strings(feedback["model_feedback"]))
    forbidden = {
        "feedback_author_identity": r"\bcharlie\b|\bdeveloper[- ]researcher\b",
        "condition_or_target_disclosure": (
            r"\bplanted\b|\bmanipulation\b|\bcontrolled condition\b|"
            r"\bnatural condition\b|\bfeedback arm\b|\bno[- ]feedback arm\b"
        ),
        "candidate_model_identity": (
            r"\b(?:gpt|claude|gemini|llama|qwen)(?:[- .]?\w+)*\b|"
            r"\b(?:openai|anthropic|google deepmind|meta ai)\b"
        ),
    }
    for label, pattern in forbidden.items():
        if re.search(pattern, model_text, flags=re.IGNORECASE):
            raise InstrumentError(
                f"identity-free feedback contains forbidden {label}; revise before lock"
            )
    findings = feedback["model_feedback"]["findings"]
    excerpt_ids = {row["excerpt_id"] for row in item["evidence"]}
    for finding in findings:
        unknown = set(finding["evidence_excerpt_ids"]) - excerpt_ids
        if unknown:
            raise InstrumentError("feedback finding cites an unknown excerpt ID")
        for pointer in finding["output_locations"]:
            if not editable_pointer(pointer):
                raise InstrumentError("feedback finding targets an immutable/noncandidate field")
            resolve_pointer(item, pointer)
    serious = {
        finding["error_flag"] for finding in findings if finding["severity"] == "serious"
    }
    if serious != set(rating["serious_error_flags"]):
        raise InstrumentError("serious feedback findings do not match the locked rating flags")


def verify_timing(payload: dict[str, Any]) -> None:
    started = parse_utc(payload["started_at_utc"], "timing start")
    submitted = parse_utc(payload["rating_submitted_at_utc"], "timing submit")
    if submitted < started:
        raise InstrumentError("rating submit predates timing start")
    log = payload["timing_log"]
    totals = log["active_ms"] + log["hidden_ms"] + log["idle_paused_ms"]
    if log["duration_sum_error_ms"] != log["wall_ms"] - totals:
        raise InstrumentError("timing duration_sum_error_ms is inconsistent")
    if abs(log["duration_sum_error_ms"]) > 3:
        raise InstrumentError("timing components do not reconcile")
    elapsed_ms = (submitted - started).total_seconds() * 1000
    if abs(elapsed_ms - log["wall_ms"]) > 5000:
        raise InstrumentError("browser wall timing and UTC timestamps differ materially")
    segments = log["segments"]
    prior_end = 0
    for index, segment in enumerate(segments, start=1):
        if segment["index"] != index:
            raise InstrumentError("timing segment indices are not contiguous")
        if abs(segment["start_offset_ms"] - prior_end) > 2:
            raise InstrumentError("timing segments contain a gap or overlap")
        if abs(
            segment["duration_ms"]
            - (segment["end_offset_ms"] - segment["start_offset_ms"])
        ) > 2:
            raise InstrumentError("timing segment duration is inconsistent")
        prior_end = segment["end_offset_ms"]
    if abs(prior_end - log["wall_ms"]) > 2:
        raise InstrumentError("timing segments do not end at wall duration")


def write_file(path: Path, payload: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def commit_rating_pair(directory: Path, rating: dict[str, Any], receipt: dict[str, Any]) -> None:
    LOCKED_ROOT.mkdir(parents=True, exist_ok=True)
    if directory.exists():
        raise InstrumentError("rating lock already exists")
    temporary = Path(tempfile.mkdtemp(prefix=f".{directory.name}.", dir=LOCKED_ROOT))
    try:
        write_file(temporary / "rating.json", rendered_bytes(rating))
        write_file(temporary / "timing_receipt.json", rendered_bytes(receipt))
        os.rename(temporary, directory)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


def commit_feedback(directory: Path, feedback: dict[str, Any]) -> None:
    destination = directory / "feedback_commit"
    if destination.exists():
        raise InstrumentError("feedback sidecar already exists")
    temporary = Path(tempfile.mkdtemp(prefix=".feedback.", dir=directory))
    try:
        write_file(temporary / "feedback.json", rendered_bytes(feedback))
        os.rename(temporary, destination)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


class ReviewState:
    def __init__(self, prepared: dict[str, Any]):
        self.prepared = prepared
        self.lock = threading.RLock()
        self.launch_nonce = secrets.token_urlsafe(32)
        self.sessions: dict[str, str] = {}

    def next_assignment(self) -> tuple[dict[str, str], str, int]:
        completed, pending, state = response_state(self.prepared["assignments"])
        if pending is None:
            raise InstrumentError("all 24 assignments are complete")
        return pending, state, completed


def public_assignment(row: dict[str, str]) -> dict[str, Any]:
    return {
        "assignment_id": row["assignment_id"],
        "sequence": int(row["sequence"]),
        "item_id": row["item_id"],
        "packet_id": row["packet_id"],
        "output_id": row["output_id"],
        "corpus_id": row["corpus_id"],
        "evaluation_role": row["evaluation_role"],
        "item_payload_sha256": row["item_payload_sha256"],
        "interface_version": row["interface_version"],
        "shared_rater_guide_version": row["shared_rater_guide_version"],
        "shared_rater_guide_sha256": row["shared_rater_guide_sha256"],
        "semantic_input_sha256": row["semantic_input_sha256"],
    }


def make_handler(state: ReviewState):
    class Handler(BaseHTTPRequestHandler):
        server_version = "WarrantRouteDirectionJ/1"

        def log_message(self, format_string: str, *args: Any) -> None:
            sys.stderr.write("browser-instrument: " + (format_string % args) + "\n")

        def end_headers(self) -> None:
            self.send_header("Cache-Control", "no-store, max-age=0")
            self.send_header("Pragma", "no-cache")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; script-src 'self'; style-src 'self'; "
                "connect-src 'self'; img-src 'none'; frame-ancestors 'none'; base-uri 'none'",
            )
            super().end_headers()

        def send_json(self, status: int, value: Any) -> None:
            payload = json.dumps(value, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def send_asset(self, path: Path, content_type: str) -> None:
            payload = path.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def read_body(self) -> dict[str, Any]:
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError as exc:
                raise InstrumentError("invalid Content-Length") from exc
            if length <= 0 or length > MAX_REQUEST_BYTES:
                raise InstrumentError("request body size is outside the allowed range")
            try:
                value = json.loads(self.rfile.read(length))
            except Exception as exc:  # noqa: BLE001
                raise InstrumentError("request body is not valid JSON") from exc
            if not isinstance(value, dict):
                raise InstrumentError("request body must be a JSON object")
            return value

        def require_launch(self) -> None:
            if not secrets.compare_digest(
                self.headers.get("X-WarrantRoute-Launch", ""), state.launch_nonce
            ):
                raise InstrumentError("local launch token is missing or invalid")

        def require_session(self, body: dict[str, Any], item_id: str) -> str:
            token = body.get("session_token")
            if not isinstance(token, str) or not secrets.compare_digest(
                state.sessions.get(token, ""), item_id
            ):
                raise InstrumentError("review session token is missing or invalid")
            return token

        def do_GET(self) -> None:  # noqa: N802
            route = urlparse(self.path).path
            try:
                if route == "/":
                    self.send_asset(BROWSER_ROOT / "index.html", "text/html; charset=utf-8")
                elif route == "/app.js":
                    self.send_asset(BROWSER_ROOT / "app.js", "text/javascript; charset=utf-8")
                elif route == "/styles.css":
                    self.send_asset(BROWSER_ROOT / "styles.css", "text/css; charset=utf-8")
                elif route == "/api/bootstrap":
                    with state.lock:
                        completed, pending, phase = response_state(state.prepared["assignments"])
                    self.send_json(
                        HTTPStatus.OK,
                        {
                            "launch_nonce": state.launch_nonce,
                            "completed_count": completed,
                            "feedback_pending": phase == "feedback_pending",
                            "queue_complete": pending is None,
                        },
                    )
                else:
                    self.send_json(HTTPStatus.NOT_FOUND, {"error": "Not found."})
            except InstrumentError as exc:
                self.send_json(HTTPStatus.CONFLICT, {"error": str(exc)})

        def do_POST(self) -> None:  # noqa: N802
            route = urlparse(self.path).path
            try:
                self.require_launch()
                body = self.read_body()
                with state.lock:
                    if route == "/api/session/start":
                        self.start_session(body)
                    elif route == "/api/rating":
                        self.lock_rating(body)
                    elif route == "/api/feedback":
                        self.lock_feedback(body)
                    else:
                        self.send_json(HTTPStatus.NOT_FOUND, {"error": "Not found."})
            except InstrumentError as exc:
                self.send_json(HTTPStatus.CONFLICT, {"error": str(exc)})
            except Exception as exc:  # noqa: BLE001
                self.send_json(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    {"error": f"Local instrument stopped safely: {type(exc).__name__}."},
                )

        def start_session(self, body: dict[str, Any]) -> None:
            if body.get("launch_nonce") != state.launch_nonce:
                raise InstrumentError("launch nonce mismatch")
            row, phase, completed = state.next_assignment()
            item = state.prepared["items"][row["item_id"]]
            token = secrets.token_urlsafe(32)
            state.sessions[token] = row["item_id"]
            response: dict[str, Any] = {
                "session_token": token,
                "state": phase,
                "completed_count": completed,
                "assignment": public_assignment(row),
                "guide": J_GUIDE_PATH.read_text(encoding="utf-8"),
                "item": item,
            }
            if phase == "feedback_pending":
                directory = response_dir(row)
                rating = load_json(directory / "rating.json", "locked rating")
                receipt = load_json(directory / "timing_receipt.json", "timing receipt")
                validate(rating, J_RATING_SCHEMA_PATH, "locked rating", state.prepared["store"])
                validate(receipt, TIMING_SCHEMA_PATH, "timing receipt", state.prepared["store"])
                response.update(
                    {
                        "rating": rating,
                        "review_seconds": receipt["review_seconds"],
                        "timing_receipt_sha256": sha256_file(directory / "timing_receipt.json"),
                    }
                )
            self.send_json(HTTPStatus.OK, response)

        def lock_rating(self, body: dict[str, Any]) -> None:
            row, phase, _ = state.next_assignment()
            self.require_session(body, row["item_id"])
            if phase == "feedback_pending":
                directory = response_dir(row)
                existing = load_json(directory / "rating.json", "locked rating")
                if body.get("rating") != existing:
                    raise InstrumentError("an immutable rating is already locked for this item")
                receipt_path = directory / "timing_receipt.json"
                self.send_json(
                    HTTPStatus.OK,
                    {
                        "session_token": body["session_token"],
                        "rating": existing,
                        "timing_receipt_sha256": sha256_file(receipt_path),
                    },
                )
                return
            rating = body.get("rating")
            timing_payload = {
                "started_at_utc": body.get("started_at_utc"),
                "rating_submitted_at_utc": body.get("rating_submitted_at_utc"),
                "timing_log": body.get("timing_log"),
            }
            validate(rating, J_RATING_SCHEMA_PATH, "submitted shared rating", state.prepared["store"])
            verify_timing(timing_payload)
            server_received = utc_now()
            if parse_utc(timing_payload["rating_submitted_at_utc"], "rating submit") > (
                parse_utc(server_received, "server receipt")
            ):
                raise InstrumentError("rating submit timestamp is after server receipt")
            manifest = state.prepared["manifest"]
            receipt = {
                "receipt_version": "direction-h-direction-j-browser-timing-receipt-v1",
                "instrument_version": INSTRUMENT_VERSION,
                "bridge_id": BRIDGE_ID,
                "study_id": "direction-j-v1",
                "run_id": "20260825_synthetic_paired_qualification_prepared",
                "assignment_id": row["assignment_id"],
                "sequence": int(row["sequence"]),
                "item_id": row["item_id"],
                "packet_id": row["packet_id"],
                "output_id": row["output_id"],
                "corpus_id": row["corpus_id"],
                "evaluation_role": row["evaluation_role"],
                "actor_id": "charlie",
                "actor_kind": "human",
                "rating_repetition": 1,
                "direction_h_case": {
                    "case_id": "charlie_dev_researcher_01",
                    "evaluator_group": "researcher",
                    "case_role": "developer_researcher_case_baseline",
                    "construction_involved": True,
                    "independent_human_pool_eligible": False,
                    "universal_ground_truth": False,
                },
                "item_payload_sha256": row["item_payload_sha256"],
                "interface_version": row["interface_version"],
                "shared_rater_guide_version": row["shared_rater_guide_version"],
                "shared_rater_guide_sha256": row["shared_rater_guide_sha256"],
                "semantic_input_sha256": row["semantic_input_sha256"],
                "prompt_or_instrument_version": INSTRUMENT_VERSION,
                "prompt_or_instrument_sha256": manifest["instrument_bundle"]["sha256"],
                "browser_manifest_sha256": sha256_file(MANIFEST_PATH),
                "activation_record_sha256": sha256_file(ACTIVATION_PATH),
                "started_at_utc": timing_payload["started_at_utc"],
                "rating_submitted_at_utc": timing_payload["rating_submitted_at_utc"],
                "server_received_at_utc": server_received,
                "review_seconds": round(timing_payload["timing_log"]["active_ms"] / 1000, 3),
                "timing_log": timing_payload["timing_log"],
                "rating_record_sha256": sha256_bytes(canonical_bytes(rating)),
                "blinding": {
                    "candidate_identity_hidden": True,
                    "condition_hidden": True,
                    "other_ratings_hidden": True,
                    "workspace_classification": "condition_masked_developer",
                    "private_map_access_separated": False,
                    "unblinded_at_utc": None,
                },
                "paired_observation_projection": {
                    "status": "public_fields_ready_pending_locked_private_join",
                    "started_at_utc_source": "started_at_utc",
                    "completed_at_utc_source": "rating_submitted_at_utc",
                    "review_seconds_source": "review_seconds",
                    "missing_coordinator_private_fields": [
                        "candidate_generation_run_id",
                        "candidate_generation_repetition",
                        "blind_id",
                    ],
                },
            }
            validate(receipt, TIMING_SCHEMA_PATH, "timing receipt", state.prepared["store"])
            commit_rating_pair(response_dir(row), rating, receipt)
            self.send_json(
                HTTPStatus.OK,
                {
                    "session_token": body["session_token"],
                    "rating": rating,
                    "timing_receipt_sha256": sha256_file(
                        response_dir(row) / "timing_receipt.json"
                    ),
                },
            )

        def lock_feedback(self, body: dict[str, Any]) -> None:
            row, phase, completed = state.next_assignment()
            self.require_session(body, row["item_id"])
            if phase != "feedback_pending":
                raise InstrumentError("rating must lock before feedback")
            directory = response_dir(row)
            rating = load_json(directory / "rating.json", "locked rating")
            receipt_path = directory / "timing_receipt.json"
            feedback_id = "DHJBF_" + hashlib.sha256(
                (INSTRUMENT_VERSION + "|" + row["assignment_id"]).encode("utf-8")
            ).hexdigest()[:16]
            feedback = {
                "feedback_version": "direction-h-direction-j-browser-feedback-v1",
                "feedback_id": feedback_id,
                "bridge_id": BRIDGE_ID,
                "instrument_version": INSTRUMENT_VERSION,
                "assignment_id": row["assignment_id"],
                "item_id": row["item_id"],
                "pointer_base": "direction-j-evaluator-item-root",
                "rating_key": {
                    "rating_schema_version": "direction-j-shared-rating-v1",
                    "rating_record_sha256": sha256_bytes(canonical_bytes(rating)),
                    "actor_id": "charlie",
                    "rating_repetition": 1,
                    "item_id": row["item_id"],
                    "packet_id": row["packet_id"],
                    "output_id": row["output_id"],
                },
                "timing_receipt_sha256": sha256_file(receipt_path),
                "feedback_status": body.get("feedback_status"),
                "model_feedback": body.get("model_feedback"),
                "created_at_utc": utc_now(),
            }
            validate(feedback, BROWSER_FEEDBACK_SCHEMA_PATH, "browser feedback", state.prepared["store"])
            validate_findings(state.prepared["items"][row["item_id"]], feedback, rating)
            commit_feedback(directory, feedback)
            state.sessions.pop(body["session_token"], None)
            self.send_json(
                HTTPStatus.OK,
                {"completed_count": completed + 1, "item_id": row["item_id"]},
            )

    return Handler


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Serve the synthetic-only exact Direction J Charlie browser queue."
    )
    parser.add_argument("--host", default="127.0.0.1", help="Loopback host only.")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--prepared-only",
        action="store_true",
        help="Validate frozen public artifacts and response absence without requiring activation.",
    )
    parser.add_argument(
        "--check-activation",
        action="store_true",
        help="Validate activation and qualification gates without starting a server.",
    )
    args = parser.parse_args()
    try:
        prepared = validate_prepared()
        if args.prepared_only:
            print(
                json.dumps(
                    {
                        "status": "valid_prepared_not_activated",
                        "synthetic_items": 24,
                        "contains_real_source_text": False,
                        "completed_responses": prepared["completed_count"],
                    },
                    sort_keys=True,
                )
            )
            return 0
        activated = validate_activation(prepared)
        if args.check_activation:
            print(
                json.dumps(
                    {
                        "status": "valid_activated",
                        "synthetic_items": 24,
                        "completed_responses": activated["completed_count"],
                    },
                    sort_keys=True,
                )
            )
            return 0
        if args.host not in {"127.0.0.1", "localhost", "::1"}:
            raise InstrumentError("the reviewer server may bind only to loopback")
        if not (1024 <= args.port <= 65535):
            raise InstrumentError("port must be between 1024 and 65535")
        state = ReviewState(activated)
        server = ThreadingHTTPServer((args.host, args.port), make_handler(state))
        print(f"Synthetic Charlie reviewer ready at http://{args.host}:{args.port}/")
        print("Stop with Ctrl-C. No item is displayed until Begin is selected in the browser.")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
        return 0
    except InstrumentError as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
