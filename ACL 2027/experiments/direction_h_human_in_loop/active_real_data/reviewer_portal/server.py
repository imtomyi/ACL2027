#!/usr/bin/env python3
"""Serve the text-free Direction H reviewer onboarding portal.

Only the reduced output of the adjacent governance checker is read. This
module has no dataset path, packet loader, rating endpoint, or persistence.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable


PORTAL_ROOT = Path(__file__).resolve().parent
STATIC_ROOT = PORTAL_ROOT / "static"
READINESS_CHECKER = PORTAL_ROOT.parent / "check_readiness.py"
TARGETS = ("dreaddit", "agyw_focus_groups")
REQUIRED_GATE_COUNT = 10
MAX_REQUEST_BYTES = 2_048

GATE_LABELS = {
    "institutional_determination": "Institutional determination",
    "source_platform_authorization": "Source and platform permission",
    "provider_model_processing": "Approved model processing",
    "exact_corpus_input_contract": "Exact corpus and input contract",
    "two_person_excerpt_privacy_review": "Two-person excerpt privacy review",
    "cluster_aware_sampling": "Cluster-aware sampling plan",
    "frozen_study_manifest": "Frozen study plan",
    "rater_and_service_access_controls": "Reviewer and service access controls",
    "retention_deletion_controls": "Retention and deletion controls",
    "release_controls": "Release controls",
}

CORPUS_PRESENTATION = {
    "dreaddit": {
        "label": "Dreaddit",
        "role": "Development pilot and later in-domain audit",
    },
    "agyw_focus_groups": {
        "label": "AGYW focus groups",
        "role": "Held-out cross-domain confirmation",
    },
}

ACKNOWLEDGMENT_KEYS = {
    "independent_review_acknowledged",
    "researcher_role_acknowledged",
    "confidentiality_acknowledged",
}


class ReadinessUnavailable(RuntimeError):
    """Raised when readiness cannot be proven from safe metadata."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _is_plain_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def validate_readiness_report(report: Any) -> dict[str, Any]:
    """Validate and reduce checker output to fields safe for the page."""

    if not isinstance(report, dict):
        raise ReadinessUnavailable("Readiness output was not an object")
    if report.get("contains_real_source_text") is not False:
        raise ReadinessUnavailable("Readiness output was not certified text-free")
    if report.get("fictional_or_synthetic_data_authorized") is not False:
        raise ReadinessUnavailable("Data-scope marker was absent or inconsistent")

    assessed_at = report.get("assessment_as_of_utc")
    if not isinstance(assessed_at, str) or not assessed_at.endswith("Z"):
        raise ReadinessUnavailable("Readiness timestamp was missing")
    corpora = report.get("corpora")
    if not isinstance(corpora, dict) or set(corpora) != set(TARGETS):
        raise ReadinessUnavailable("Readiness did not cover exactly the study corpora")

    public_corpora: list[dict[str, Any]] = []
    all_ready = report.get("status") == "ready_for_restricted_next_step"
    for corpus_id in TARGETS:
        value = corpora.get(corpus_id)
        if not isinstance(value, dict):
            raise ReadinessUnavailable("A corpus readiness entry was malformed")
        completed = value.get("completed_gate_count")
        required = value.get("required_gate_count")
        ready = value.get("real_text_ready")
        blocker_ids = value.get("blocking_gate_ids")
        if not _is_plain_int(completed) or not _is_plain_int(required):
            raise ReadinessUnavailable("Gate counts were malformed")
        if required != REQUIRED_GATE_COUNT or not 0 <= completed <= required:
            raise ReadinessUnavailable("Gate counts were outside the approved contract")
        if not isinstance(ready, bool) or not isinstance(blocker_ids, list):
            raise ReadinessUnavailable("Readiness state was malformed")
        if len(blocker_ids) != len(set(blocker_ids)):
            raise ReadinessUnavailable("Blocking gates were duplicated")
        if any(gate_id not in GATE_LABELS for gate_id in blocker_ids):
            raise ReadinessUnavailable("An unknown blocking gate was reported")

        corpus_is_ready = ready and completed == required and not blocker_ids
        if ready != corpus_is_ready:
            raise ReadinessUnavailable("A corpus readiness claim was inconsistent")
        all_ready = all_ready and corpus_is_ready
        public_corpora.append(
            {
                "id": corpus_id,
                **CORPUS_PRESENTATION[corpus_id],
                "completed": completed,
                "required": required,
                "ready": corpus_is_ready,
                "blocking_items": [GATE_LABELS[gate_id] for gate_id in blocker_ids],
            }
        )

    expected = "ready_for_restricted_next_step" if all_ready else "blocked_before_text_access"
    if report.get("status") != expected:
        raise ReadinessUnavailable("Overall readiness was inconsistent")
    return {
        "status": "ready" if all_ready else "locked",
        "assessed_at": assessed_at,
        "contains_source_text": False,
        "corpora": public_corpora,
    }


def check_readiness() -> dict[str, Any]:
    """Run the governance-only checker and return a validated summary."""

    if READINESS_CHECKER.is_symlink() or not READINESS_CHECKER.is_file():
        raise ReadinessUnavailable("Readiness checker is unavailable")
    completed = subprocess.run(
        [sys.executable, str(READINESS_CHECKER), "--as-of", utc_now()],
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    if completed.returncode not in {0, 3}:
        raise ReadinessUnavailable("Readiness checker did not validate")
    try:
        report = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise ReadinessUnavailable("Readiness checker returned unreadable output") from exc
    summary = validate_readiness_report(report)
    if completed.returncode == 0 and summary["status"] != "ready":
        raise ReadinessUnavailable("Checker exit state was inconsistent")
    if completed.returncode == 3 and summary["status"] != "locked":
        raise ReadinessUnavailable("Checker exit state was inconsistent")
    return summary


def validate_acknowledgments(value: Any) -> bool:
    """Accept only three fixed, non-sensitive, ephemeral acknowledgments."""

    return (
        isinstance(value, dict)
        and set(value) == ACKNOWLEDGMENT_KEYS
        and all(value[key] is True for key in ACKNOWLEDGMENT_KEYS)
    )


def public_summary_is_ready(summary: Any) -> bool:
    """Require a complete public summary again at the access edge."""

    if not isinstance(summary, dict) or summary.get("status") != "ready":
        return False
    if summary.get("contains_source_text") is not False:
        return False
    corpora = summary.get("corpora")
    if not isinstance(corpora, list) or len(corpora) != len(TARGETS):
        return False
    if {value.get("id") for value in corpora if isinstance(value, dict)} != set(TARGETS):
        return False
    return all(
        isinstance(value, dict)
        and value.get("ready") is True
        and value.get("completed") == REQUIRED_GATE_COUNT
        and value.get("required") == REQUIRED_GATE_COUNT
        and value.get("blocking_items") == []
        for value in corpora
    )


def readiness_response(
    readiness_provider: Callable[[], dict[str, Any]],
) -> tuple[HTTPStatus, dict[str, Any]]:
    """Return readiness metadata; any verification failure remains locked."""

    try:
        summary = readiness_provider()
    except Exception:
        return HTTPStatus.SERVICE_UNAVAILABLE, {
            "status": "locked",
            "reason": "Readiness could not be verified. No review access is available.",
            "contains_source_text": False,
            "corpora": [],
        }
    if not isinstance(summary, dict) or summary.get("contains_source_text") is not False:
        return HTTPStatus.SERVICE_UNAVAILABLE, {
            "status": "locked",
            "reason": "Readiness could not be verified. No review access is available.",
            "contains_source_text": False,
            "corpora": [],
        }
    return HTTPStatus.OK, summary


def access_response(
    readiness_provider: Callable[[], dict[str, Any]], acknowledgments: Any
) -> tuple[HTTPStatus, dict[str, Any]]:
    """Return a text-free onboarding handoff or a locked response."""

    if not validate_acknowledgments(acknowledgments):
        return HTTPStatus.BAD_REQUEST, {
            "status": "incomplete_acknowledgments",
            "contains_source_text": False,
        }
    try:
        summary = readiness_provider()
    except Exception:
        return HTTPStatus.SERVICE_UNAVAILABLE, {
            "status": "locked",
            "reason": "Readiness could not be verified. No review access is available.",
            "contains_source_text": False,
        }
    if not public_summary_is_ready(summary):
        return HTTPStatus.LOCKED, {
            "status": "locked",
            "reason": "External study requirements are still incomplete.",
            "contains_source_text": False,
        }
    return HTTPStatus.OK, {
        "status": "onboarding_complete",
        "next": "approved_restricted_packet_service_required",
        "contains_source_text": False,
    }


def make_handler(
    readiness_provider: Callable[[], dict[str, Any]] = check_readiness,
) -> type[BaseHTTPRequestHandler]:
    """Create an HTTP handler with an injectable provider for tests."""

    class PortalHandler(BaseHTTPRequestHandler):
        server_version = "DirectionHPortal/1"

        def log_message(self, format: str, *args: object) -> None:
            return  # Intentionally no request or reviewer activity log.

        def _security_headers(self) -> None:
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")

        def _send_json(self, status: HTTPStatus, value: dict[str, Any]) -> None:
            body = (json.dumps(value, sort_keys=True) + "\n").encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self._security_headers()
            self.end_headers()
            self.wfile.write(body)

        def _send_static(self, filename: str, content_type: str) -> None:
            path = STATIC_ROOT / filename
            if path.is_symlink() or not path.is_file():
                self._send_json(HTTPStatus.NOT_FOUND, {"status": "not_found"})
                return
            body = path.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self._security_headers()
            self.end_headers()
            self.wfile.write(body)

        def _read_json(self) -> Any:
            raw_length = self.headers.get("Content-Length")
            if raw_length is None:
                raise ValueError("Missing request length")
            try:
                length = int(raw_length)
            except ValueError as exc:
                raise ValueError("Invalid request length") from exc
            if not 0 < length <= MAX_REQUEST_BYTES:
                raise ValueError("Request size is not allowed")
            if self.headers.get_content_type() != "application/json":
                raise ValueError("Only JSON is accepted")
            try:
                return json.loads(self.rfile.read(length))
            except json.JSONDecodeError as exc:
                raise ValueError("Unreadable JSON") from exc

        def do_GET(self) -> None:  # noqa: N802
            static_routes = {
                "/": ("index.html", "text/html; charset=utf-8"),
                "/styles.css": ("styles.css", "text/css; charset=utf-8"),
                "/app.js": ("app.js", "text/javascript; charset=utf-8"),
            }
            if self.path in static_routes:
                self._send_static(*static_routes[self.path])
                return
            if self.path == "/api/readiness":
                status, payload = readiness_response(readiness_provider)
                self._send_json(status, payload)
                return
            self._send_json(HTTPStatus.NOT_FOUND, {"status": "not_found"})

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/api/review-access":
                self._send_json(HTTPStatus.NOT_FOUND, {"status": "not_found"})
                return
            try:
                acknowledgments = self._read_json()
            except ValueError:
                self._send_json(HTTPStatus.BAD_REQUEST, {"status": "invalid_request", "contains_source_text": False})
                return
            status, payload = access_response(readiness_provider, acknowledgments)
            self._send_json(status, payload)

    return PortalHandler


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve the locked Direction H reviewer portal")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    if args.host not in {"127.0.0.1", "localhost"}:
        parser.error("The pre-authorization portal may bind only to localhost")
    server = ThreadingHTTPServer((args.host, args.port), make_handler())
    print(f"Direction H reviewer portal: http://{args.host}:{server.server_port}")
    print("Text-free onboarding only; review content remains server-locked.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
