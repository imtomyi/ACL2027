#!/usr/bin/env python3
"""Build the deterministic, synthetic-only Direction J first-run package.

The builder has no arbitrary input option. It reads only the frozen fictional
qualification bundles and their synthetic blind map. It never reads dataset/
or the Warrant Study app's protected item bank.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import random
import stat
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


SCRIPT_PATH = Path(__file__).resolve()
DIRECTION_ROOT = SCRIPT_PATH.parents[1]
PROJECT_ROOT = SCRIPT_PATH.parents[3]
BASELINE_ROOT = PROJECT_ROOT / "experiments" / "qualitative_coding_baselines"
BASELINE_RUN = PROJECT_ROOT / "Storage" / "synthetic-results" / "model-qualification" / "20260825_synthetic_qualification"
BLINDED_DIR = BASELINE_RUN / "blinded"
BLIND_MAP = BASELINE_RUN / "blind_map_private.csv"
BASELINE_MANIFEST = BASELINE_RUN / "run_manifest.json"
BENCHMARK_PATH = BASELINE_ROOT / "benchmark" / "synthetic_packets_v1.json"
ITEM_SCHEMA_PATH = DIRECTION_ROOT / "schemas" / "evaluator_item.schema.json"
RATER_GUIDE_PATH = DIRECTION_ROOT / "protocol" / "shared_rater_guide_v1.md"
FREEZE_PATH = DIRECTION_ROOT / "config" / "freeze_v1.json"
OUTPUT_DIR = PROJECT_ROOT / "Storage" / "synthetic-results" / "archived-experiments" / "direction-j" / "20260825_synthetic_paired_qualification_prepared"

SELECTION_SEED = "direction-j-synthetic-first-run-v1|2026-08-25"
EXPECTED_BENCHMARK_SHA256 = "d38fbb7860edd47d21e22e51da8f44a71ec6ddcb3fc5ac217598747d54865b39"
EXPECTED_BENCHMARK_PROVENANCE = (
    "Entirely fictional text written for pipeline qualification; no "
    "source-corpus text or published theme was used."
)
EXPECTED_BUNDLE_SHA256 = {
    "syn_agyw_01_run1.json": "52559d02efd32fc43300f9394cfcd84630ee12b800912b58e0c1516ae67e9850",
    "syn_agyw_01_run2.json": "4450d29d5dc29be148eb908b54fada018377246a82923bd1f3c010f62289ca3e",
    "syn_agyw_01_run3.json": "de39fccadf56e25ad529b0c0d5e733c67e161f105b1e65ad1faeaad367e570a4",
    "syn_candor_01_run1.json": "43e491536fd8f8f06c22755bd3156ba97ca19a2244d6301d3af30d5bda71dbe6",
    "syn_candor_01_run2.json": "6a8dce86c95d1637b1bcb9746d3b435af678912dd5cdbf05e32d3ff51871614c",
    "syn_candor_01_run3.json": "7edf64c5e2d1e36a210e650a58bcf34555a50232df6ea51501bb456c562d78a2",
    "syn_dreaddit_01_run1.json": "a3596502513042486f62f462342d1efd2edca8de8ce3bc3611769d4245b1c48a",
    "syn_dreaddit_01_run2.json": "2f66ff9de15170b8c309f967190f0bb505d160f08f84a05e074019fff526897a",
    "syn_dreaddit_01_run3.json": "f3a637b2e9d23156abc4e6d627ff87df93dbc4a95397c5d37dee0e575e8d448f",
    "syn_kodis_01_run1.json": "09cb476888701a277f7bfaeb7e76cc68fd2e7637bd70c47c7cd94be0ff5c2801",
    "syn_kodis_01_run2.json": "65440f4ad41357e507d3d080362d55a8665940f5c76e26decd3519e7ee97ed86",
    "syn_kodis_01_run3.json": "5e19efeaff7439baf727ee7352a57cfcfdabea2add6e044afed62985c32dd6b1",
}
PACKET_ORDER = [
    "syn_dreaddit_01",
    "syn_agyw_01",
    "syn_kodis_01",
    "syn_candor_01",
]
MODEL_ORDER = [
    "gpt-5.4",
    "gpt-5.5",
    "gpt-5.6-luna",
    "gpt-5.6-sol",
    "gpt-5.6-terra",
]
SENTINEL_FAMILIES = [
    "fabricated_or_altered_quote",
    "wrong_attribution",
    "unsupported_inference",
    "hidden_source_concentration",
    "lost_negative_case",
    "contextual_flattening",
    "unsupported_abstraction",
    "sensitive_or_diagnostic_inference",
]
ACTOR_REPETITIONS = {
    "charlie": [1],
    "J_PRIMARY": [1, 2, 3],
    "J_SENS_GEMINI": [1],
    "QME_QUAL": [1],
    "DOMAIN_QUAL": [1],
}
ACTOR_KINDS = {
    "charlie": "human",
    "J_PRIMARY": "llm",
    "J_SENS_GEMINI": "llm",
    "QME_QUAL": "human",
    "DOMAIN_QUAL": "human",
}
INTERFACE_VERSION = "direction-j-shared-interface-v1"
RATER_GUIDE_VERSION = "direction-j-rater-guide-v1"

ANALYTIC_CONTRACT = {
    "contract_id": "bounded-codebook-source-warrant",
    "contract_version": "qc-analytic-contract-v1",
    "task_description": (
        "Judge whether one proposed theme is warranted by the supplied fictional "
        "packet under a bounded, codebook-oriented qualitative task."
    ),
    "validity_rules": [
        "Use only the displayed packet; do not infer outside facts or population prevalence.",
        "Exact candidate quotations must be contiguous substrings of the displayed excerpt.",
        "Source and speaker attribution must match the displayed evidence.",
        "Cross-source wording requires evidence from at least two distinct sources.",
        "Consequential disagreement, counterevidence, boundary cases, and temporal change must remain visible.",
        "Claim breadth, strength, polarity, and causal language must match the evidence.",
    ],
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_path(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode(
        "utf-8"
    )


def semantic_input_sha256(item_payload_sha256: str, guide_sha256: str) -> str:
    manifest = {
        "interface_version": INTERFACE_VERSION,
        "item_payload_sha256": item_payload_sha256,
        "shared_rater_guide_sha256": guide_sha256,
        "shared_rater_guide_version": RATER_GUIDE_VERSION,
    }
    return sha256_bytes(canonical_bytes(manifest))


def opaque(prefix: str, *parts: object) -> str:
    material = "|".join([SELECTION_SEED, *(str(part) for part in parts)])
    return f"{prefix}_{hashlib.sha256(material.encode('utf-8')).hexdigest()[:16]}"


def lexical_absolute(path: Path) -> Path:
    """Return an absolute normalized path without resolving symlinks."""

    return Path(os.path.abspath(os.fspath(path)))


def reject_symlink_components(path: Path) -> None:
    """Reject a symlink at the input or at any directory leading to it."""

    absolute = lexical_absolute(path)
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current /= part
        if current.is_symlink():
            raise RuntimeError(f"Synthetic builder refused symlinked input: {current}")


def assert_safe_input(path: Path) -> Path:
    absolute = lexical_absolute(path)
    allowed_files = {
        lexical_absolute(BLIND_MAP),
        lexical_absolute(BASELINE_MANIFEST),
        lexical_absolute(BENCHMARK_PATH),
        lexical_absolute(ITEM_SCHEMA_PATH),
        lexical_absolute(RATER_GUIDE_PATH),
        lexical_absolute(FREEZE_PATH),
        *(
            lexical_absolute(BLINDED_DIR / filename)
            for filename in EXPECTED_BUNDLE_SHA256
        ),
    }
    if absolute not in allowed_files:
        raise RuntimeError(f"Synthetic builder refused non-allowlisted input: {absolute}")
    reject_symlink_components(absolute)
    return absolute


def read_pinned_bytes(path: Path, expected_sha256: str | None = None) -> bytes:
    """Read an allowlisted regular file once and verify those exact bytes."""

    absolute = assert_safe_input(path)
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(absolute, flags)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise RuntimeError(f"Synthetic builder refused non-regular input: {absolute}")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    stable_identity = (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
    ) == (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    )
    if not stable_identity:
        raise RuntimeError(f"Synthetic builder input changed while being read: {absolute}")
    data = b"".join(chunks)
    if len(data) != before.st_size:
        raise RuntimeError(f"Synthetic builder input size changed while being read: {absolute}")
    observed_sha256 = sha256_bytes(data)
    if expected_sha256 is not None and observed_sha256 != expected_sha256:
        raise RuntimeError(
            f"Pinned input digest mismatch: {absolute}; "
            f"expected={expected_sha256}; observed={observed_sha256}"
        )
    return data


def parse_json_bytes(data: bytes, label: str) -> Any:
    try:
        return json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Pinned input is not valid UTF-8 JSON ({label}): {error}") from error


def load_pinned_inputs() -> dict[str, Any]:
    """Capture every source/config input in one immutable, digest-checked snapshot."""

    freeze_bytes = read_pinned_bytes(FREEZE_PATH)
    freeze = parse_json_bytes(freeze_bytes, "Direction J freeze")
    scope = freeze.get("scope", {})
    if (
        scope.get("runnable_lane") != "synthetic_qualification_only"
        or scope.get("contains_real_source_text") is not False
        or scope.get("real_text_execution") != "blocked"
    ):
        raise RuntimeError("Direction J freeze is not a blocked-real-text synthetic lane")

    frozen_sources = freeze.get("source_evidence", {})
    manifest_sha256 = frozen_sources.get("legacy_run_manifest", {}).get("sha256")
    blind_map_sha256 = frozen_sources.get("legacy_private_blind_map", {}).get("sha256")
    if not isinstance(manifest_sha256, str) or not isinstance(blind_map_sha256, str):
        raise RuntimeError("Direction J freeze lacks pinned legacy source digests")

    manifest_bytes = read_pinned_bytes(BASELINE_MANIFEST, manifest_sha256)
    blind_map_bytes = read_pinned_bytes(BLIND_MAP, blind_map_sha256)
    benchmark_bytes = read_pinned_bytes(BENCHMARK_PATH, EXPECTED_BENCHMARK_SHA256)

    reject_symlink_components(BLINDED_DIR)
    if not BLINDED_DIR.is_dir():
        raise RuntimeError(f"Pinned blinded-bundle directory is missing: {BLINDED_DIR}")
    actual_names = {path.name for path in BLINDED_DIR.glob("*.json")}
    if actual_names != set(EXPECTED_BUNDLE_SHA256):
        raise RuntimeError("Blinded bundle file set changed")
    bundle_bytes = {
        filename: read_pinned_bytes(BLINDED_DIR / filename, expected_sha256)
        for filename, expected_sha256 in EXPECTED_BUNDLE_SHA256.items()
    }
    bundle_sha256 = {
        filename: sha256_bytes(data) for filename, data in bundle_bytes.items()
    }

    shared_files = freeze.get("shared_interface", {}).get("files", {})
    schema_sha256 = shared_files.get("schemas/evaluator_item.schema.json")
    guide_sha256 = shared_files.get("protocol/shared_rater_guide_v1.md")
    if not isinstance(schema_sha256, str) or not isinstance(guide_sha256, str):
        raise RuntimeError("Direction J freeze lacks pinned schema/guide digests")
    schema_bytes = read_pinned_bytes(ITEM_SCHEMA_PATH, schema_sha256)
    guide_bytes = read_pinned_bytes(RATER_GUIDE_PATH, guide_sha256)

    return {
        "freeze_bytes": freeze_bytes,
        "freeze": freeze,
        "manifest_bytes": manifest_bytes,
        "manifest": parse_json_bytes(manifest_bytes, "legacy run manifest"),
        "blind_map_bytes": blind_map_bytes,
        "benchmark_bytes": benchmark_bytes,
        "benchmark": parse_json_bytes(benchmark_bytes, "fictional benchmark"),
        "bundle_bytes": bundle_bytes,
        "bundle_sha256": bundle_sha256,
        "bundles": {
            filename: parse_json_bytes(data, f"blinded bundle {filename}")
            for filename, data in bundle_bytes.items()
        },
        "schema_bytes": schema_bytes,
        "schema": parse_json_bytes(schema_bytes, "evaluator-item schema"),
        "guide_bytes": guide_bytes,
    }


def load_blind_map(blind_map_bytes: bytes) -> dict[tuple[str, int, str], str]:
    try:
        text = blind_map_bytes.decode("utf-8")
    except UnicodeDecodeError as error:
        raise RuntimeError(f"Pinned blind map is not UTF-8: {error}") from error
    rows = csv.DictReader(text.splitlines())
    result: dict[tuple[str, int, str], str] = {}
    for row in rows:
        key = (row["packet_id"], int(row["run_index"]), row["model_id"])
        if key in result:
            raise ValueError(f"Duplicate blind-map key: {key}")
        result[key] = row["blind_id"]
    return result


def verify_synthetic_manifest(
    inputs: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    freeze = inputs["freeze"]
    frozen_sources = freeze.get("source_evidence", {})
    frozen_manifest_hash = frozen_sources.get("legacy_run_manifest", {}).get("sha256")
    if sha256_bytes(inputs["manifest_bytes"]) != frozen_manifest_hash:
        raise RuntimeError("Baseline manifest differs from the Direction J freeze")
    frozen_blind_map_hash = frozen_sources.get("legacy_private_blind_map", {}).get(
        "sha256"
    )
    if sha256_bytes(inputs["blind_map_bytes"]) != frozen_blind_map_hash:
        raise RuntimeError("Baseline blind map differs from the Direction J freeze")
    manifest = inputs["manifest"]
    if manifest.get("qualification_scope") != "synthetic_only":
        raise RuntimeError("Baseline manifest is not synthetic_only")
    if manifest.get("benchmark", {}).get("contains_real_source_text") is not False:
        raise RuntimeError("Baseline manifest does not exclude real source text")
    governance = manifest.get("governance", {})
    if governance.get("real_dreaddit_processed") is not False:
        raise RuntimeError("Baseline manifest says real Dreaddit was processed")
    if governance.get("real_agyw_processed") is not False:
        raise RuntimeError("Baseline manifest says real AGYW was processed")
    if governance.get("heldout_data_used_for_selection") is not False:
        raise RuntimeError("Baseline manifest says held-out data were used")
    if sorted(manifest.get("models", [])) != MODEL_ORDER:
        raise RuntimeError("Candidate model grid changed from the frozen first-run expectation")
    benchmark_record = manifest.get("benchmark", {})
    if benchmark_record.get("path") != "benchmark/synthetic_packets_v1.json":
        raise RuntimeError("Baseline manifest benchmark path changed")
    if benchmark_record.get("sha256") != EXPECTED_BENCHMARK_SHA256:
        raise RuntimeError("Baseline manifest benchmark hash changed")
    if sha256_bytes(inputs["benchmark_bytes"]) != EXPECTED_BENCHMARK_SHA256:
        raise RuntimeError("Pinned fictional benchmark bytes changed")
    frozen_benchmark = frozen_sources.get("synthetic_benchmark", {})
    if frozen_benchmark.get("sha256") != EXPECTED_BENCHMARK_SHA256:
        raise RuntimeError("Direction J freeze does not pin the fictional benchmark")
    benchmark = inputs["benchmark"]
    if benchmark.get("provenance") != EXPECTED_BENCHMARK_PROVENANCE:
        raise RuntimeError("Fictional benchmark provenance assertion changed")
    if benchmark.get("license") != "CC0-1.0":
        raise RuntimeError("Fictional benchmark license changed")
    packets = benchmark.get("packets", [])
    packet_map = {packet.get("packet_id"): packet for packet in packets}
    if list(packet_map) != PACKET_ORDER or len(packet_map) != len(PACKET_ORDER):
        raise RuntimeError("Fictional benchmark packet grid changed")
    frozen_bundles = frozen_sources.get("blinded_bundle_sha256", {})
    if (
        frozen_bundles != EXPECTED_BUNDLE_SHA256
        or inputs["bundle_sha256"] != EXPECTED_BUNDLE_SHA256
    ):
        raise RuntimeError("Direction J freeze does not pin the exact blinded bundles")
    expected_fileset_sha256 = sha256_bytes(canonical_bytes(inputs["bundle_sha256"]))
    if (
        frozen_sources.get("blinded_bundle_fileset_sha256")
        != expected_fileset_sha256
    ):
        raise RuntimeError("Direction J freeze has the wrong blinded-bundle receipt")
    return manifest, packet_map


def load_bundle(
    packet_id: str,
    run_index: int,
    expected_packet: dict[str, Any],
    bundles: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    filename = f"{packet_id}_run{run_index}.json"
    data = bundles[filename]
    if data.get("packet_id") != packet_id or data.get("run_index") != run_index:
        raise ValueError(f"Bundle identity mismatch in {filename}")
    if len(data.get("candidates", [])) != 5:
        raise ValueError(f"Expected five candidates in {filename}")
    if data.get("packet", {}).get("status") != "synthetic_proxy_not_corpus_result":
        raise RuntimeError(f"Bundle is not explicitly synthetic: {filename}")
    if data.get("packet") != expected_packet:
        raise RuntimeError(f"Bundle packet differs from pinned fictional benchmark: {filename}")
    return data


def candidate_for_model(
    bundle: dict[str, Any],
    blind_map: dict[tuple[str, int, str], str],
    model_id: str,
) -> dict[str, Any]:
    key = (bundle["packet_id"], int(bundle["run_index"]), model_id)
    blind_id = blind_map[key]
    matches = [item for item in bundle["candidates"] if item["blind_id"] == blind_id]
    if len(matches) != 1:
        raise ValueError(f"Could not resolve exactly one candidate for {key}")
    return matches[0]


def choose_theme(output: dict[str, Any], packet_id: str, run_index: int, model_id: str) -> dict[str, Any]:
    themes = output.get("themes", [])
    if not themes:
        raise ValueError(f"Candidate {packet_id}/{run_index}/{model_id} has no themes")
    digest = hashlib.sha256(
        f"{SELECTION_SEED}|theme|{packet_id}|{run_index}|{model_id}".encode("utf-8")
    ).digest()
    return deepcopy(themes[int.from_bytes(digest[:8], "big") % len(themes)])


def build_natural_item(
    packet: dict[str, Any],
    output: dict[str, Any],
    theme: dict[str, Any],
    packet_id: str,
    run_index: int,
    model_id: str,
) -> dict[str, Any]:
    support = {entry["excerpt_id"]: entry for entry in theme.get("evidence", [])}
    counter = {entry["excerpt_id"]: entry for entry in theme.get("counterevidence", [])}
    evidence: list[dict[str, Any]] = []
    for display_order, excerpt in enumerate(packet["excerpts"], start=1):
        candidate = support.get(excerpt["excerpt_id"])
        role = "support"
        if candidate is None:
            candidate = counter.get(excerpt["excerpt_id"])
            role = "counterevidence"
        if candidate is None:
            role = "context_only"
        evidence.append(
            {
                "display_order": display_order,
                "excerpt_id": excerpt["excerpt_id"],
                "source_id": excerpt["source_id"],
                "speaker_id": excerpt.get("speaker_id"),
                "local_context": excerpt.get("context"),
                "text": excerpt["text"],
                "candidate_role": role,
                "candidate_attributed_excerpt_id": (
                    None if candidate is None else candidate["excerpt_id"]
                ),
                "candidate_attributed_source_id": (
                    None if candidate is None else candidate["source_id"]
                ),
                "candidate_attributed_speaker_id": None,
                "candidate_quote": None if candidate is None else candidate["quote"],
                "candidate_warrant": None if candidate is None else candidate["warrant"],
            }
        )
    item = {
        "item_schema_version": "direction-j-evaluator-item-v1",
        "item_id": opaque("DJI", packet_id, run_index, model_id, theme["theme_id"]),
        "packet_id": opaque("DJP", packet_id, run_index, model_id, theme["theme_id"]),
        "output_id": opaque("DJO", packet_id, run_index, model_id),
        "corpus_id": "synthetic_proxy",
        "research_question": packet["research_question"],
        "analytic_contract": deepcopy(ANALYTIC_CONTRACT),
        "context_note": packet["context_note"],
        "proposed_interpretation": {
            "theme_id": opaque("DJT", packet_id, run_index, model_id, theme["theme_id"]),
            "theme_name": theme["name"],
            "claim": theme["claim"],
            "explanation": theme["explanation"],
            "boundary_conditions": deepcopy(theme.get("boundary_conditions", [])),
        },
        "evidence": evidence,
        "source_coverage": {},
    }
    refresh_coverage(item)
    return item


def refresh_coverage(item: dict[str, Any]) -> None:
    evidence = item["evidence"]
    presented = Counter(entry["source_id"] for entry in evidence)
    cited = Counter(
        entry["candidate_attributed_source_id"]
        for entry in evidence
        if entry["candidate_role"] != "context_only"
    )
    item["source_coverage"] = {
        "presented_excerpt_count": len(evidence),
        "presented_source_count": len(presented),
        "candidate_cited_excerpt_count": sum(cited.values()),
        "candidate_cited_source_count": len(cited),
        "sampling_frame_excerpt_count": len(evidence),
        "sampling_frame_source_count": len(presented),
        "source_distribution": [
            {
                "source_id": source_id,
                "presented_excerpt_count": presented[source_id],
                "candidate_cited_excerpt_count": cited[source_id],
            }
            for source_id in sorted(presented)
        ],
        "coverage_note": (
            "Counts describe only this complete fictional packet. They do not "
            "represent people or population prevalence."
        ),
    }


def first_cited(item: dict[str, Any]) -> dict[str, Any]:
    for entry in item["evidence"]:
        if entry["candidate_role"] != "context_only":
            return entry
    raise ValueError("Sentinel transform requires at least one cited excerpt")


def plant_sentinel(item: dict[str, Any], family: str) -> None:
    """Apply an intentionally simple qualification-only defect.

    These controls qualify plumbing and obvious-defect handling. Their private
    label is not a complete adjudication and their difficulty is not treated as
    representative of naturally occurring errors.
    """

    cited = first_cited(item)
    if family == "fabricated_or_altered_quote":
        cited["candidate_quote"] = f"{cited['candidate_quote']} always"
    elif family == "wrong_attribution":
        alternatives = [
            entry["source_id"]
            for entry in item["evidence"]
            if entry["source_id"] != cited["source_id"]
        ]
        if not alternatives:
            raise ValueError("Wrong-attribution sentinel requires a second source")
        cited["candidate_attributed_source_id"] = alternatives[0]
    elif family == "unsupported_inference":
        item["proposed_interpretation"]["claim"] += (
            " This pattern is caused by a stable personal disposition."
        )
    elif family == "hidden_source_concentration":
        kept = False
        for entry in item["evidence"]:
            if entry["candidate_role"] != "context_only" and not kept:
                kept = True
                continue
            if entry["candidate_role"] != "context_only":
                entry["candidate_role"] = "context_only"
                entry["candidate_attributed_excerpt_id"] = None
                entry["candidate_attributed_source_id"] = None
                entry["candidate_attributed_speaker_id"] = None
                entry["candidate_quote"] = None
                entry["candidate_warrant"] = None
        item["proposed_interpretation"]["claim"] = (
            "Across the complete packet, "
            + item["proposed_interpretation"]["claim"].removeprefix("In these excerpts, ").removeprefix("In these fictional posts, ")
        )
    elif family == "lost_negative_case":
        changed = False
        for entry in item["evidence"]:
            if entry["candidate_role"] == "counterevidence":
                entry["candidate_role"] = "context_only"
                entry["candidate_attributed_excerpt_id"] = None
                entry["candidate_attributed_source_id"] = None
                entry["candidate_attributed_speaker_id"] = None
                entry["candidate_quote"] = None
                entry["candidate_warrant"] = None
                changed = True
        item["proposed_interpretation"]["boundary_conditions"] = []
        if not changed:
            item["proposed_interpretation"]["claim"] += (
                " No displayed source offers a meaningful exception or boundary."
            )
    elif family == "contextual_flattening":
        item["proposed_interpretation"]["claim"] = (
            "The packet shows that people resolve difficulty through better individual communication."
        )
        item["proposed_interpretation"]["explanation"] = (
            "The local sequence, source position, structural conditions, and competing meanings do not affect the interpretation."
        )
        item["proposed_interpretation"]["boundary_conditions"] = []
    elif family == "unsupported_abstraction":
        item["proposed_interpretation"]["claim"] = (
            "People in this population generally follow this pattern: "
            + item["proposed_interpretation"]["claim"]
        )
    elif family == "sensitive_or_diagnostic_inference":
        item["proposed_interpretation"]["claim"] += (
            " This establishes a clinical condition in the people described."
        )
    else:
        raise ValueError(f"Unknown sentinel family: {family}")
    refresh_coverage(item)


def selected_records(
    benchmark_packets: dict[str, dict[str, Any]],
    blind_map: dict[tuple[str, int, str], str],
    bundles: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    evaluator_items: list[dict[str, Any]] = []
    private_rows: list[dict[str, Any]] = []
    sentinel_index = 0
    seen_base: set[tuple[str, int, str, str]] = set()
    for packet_index, packet_id in enumerate(PACKET_ORDER):
        for run_index in range(1, 4):
            cell = packet_index * 3 + (run_index - 1)
            bundle = load_bundle(
                packet_id,
                run_index,
                benchmark_packets[packet_id],
                bundles,
            )
            for slot, model_index in enumerate((2 * cell, 2 * cell + 1)):
                model_id = MODEL_ORDER[model_index % len(MODEL_ORDER)]
                candidate = candidate_for_model(bundle, blind_map, model_id)
                output = candidate["output"]
                theme = choose_theme(output, packet_id, run_index, model_id)
                base_key = (packet_id, run_index, model_id, theme["theme_id"])
                if base_key in seen_base:
                    raise ValueError(f"Duplicate selected base theme: {base_key}")
                seen_base.add(base_key)
                natural = build_natural_item(
                    bundle["packet"], output, theme, packet_id, run_index, model_id
                )
                original_hash = sha256_bytes(canonical_bytes(natural))
                is_control = (cell + slot) % 2 == 0
                family = None
                item = deepcopy(natural)
                if is_control:
                    family = SENTINEL_FAMILIES[sentinel_index % len(SENTINEL_FAMILIES)]
                    sentinel_index += 1
                    plant_sentinel(item, family)
                item_hash = sha256_bytes(canonical_bytes(item))
                evaluator_items.append(item)
                private_rows.append(
                    {
                        "item_id": item["item_id"],
                        "item_payload_sha256": item_hash,
                        "parent_natural_item_sha256": original_hash,
                        "baseline_packet_id": packet_id,
                        "candidate_generation_run_id": (
                            f"20260825_synthetic_qualification:{model_id}:run{run_index}"
                        ),
                        "candidate_generation_repetition": run_index,
                        "candidate_model_id": model_id,
                        "baseline_blind_id": candidate["blind_id"],
                        "baseline_theme_id": theme["theme_id"],
                        "condition": "sentinel_control" if is_control else "natural",
                        "planted_serious_error_flags": [] if family is None else [family],
                        "truth_scope": (
                            "planted_manipulation_only_not_complete_gold_adjudication"
                        ),
                    }
                )
    if len(evaluator_items) != 24 or len({row["item_id"] for row in private_rows}) != 24:
        raise AssertionError("First-run selector must produce exactly 24 unique items")
    return evaluator_items, private_rows


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))


def write_jsonl(path: Path, values: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"".join(canonical_bytes(value) for value in values))


def assert_prepared_output_is_rebuildable() -> None:
    """Refuse to rewrite a run after collection has begun."""

    if not OUTPUT_DIR.exists():
        return
    manifest_path = OUTPUT_DIR / "run_manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("status") != "prepared_not_run" or manifest.get(
            "ratings_collected"
        ) != 0:
            raise RuntimeError("Refused to rebuild a run that is no longer prepared-only")
    for directory_name in ("ratings", "raw_model_responses"):
        directory = OUTPUT_DIR / directory_name
        if directory.exists():
            payloads = [path for path in directory.iterdir() if path.name != "README.md"]
            if payloads:
                raise RuntimeError(
                    f"Refused to rebuild because {directory_name} contains collected payloads"
                )


def write_assignments(
    items: list[dict[str, Any]],
    item_hashes: dict[str, str],
    semantic_input_hashes: dict[str, str],
    guide_sha256: str,
) -> dict[str, dict[str, str]]:
    reports: dict[str, dict[str, str]] = {}
    assignment_dir = OUTPUT_DIR / "assignments"
    assignment_dir.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "assignment_id",
        "actor_id",
        "actor_kind",
        "rating_repetition",
        "sequence",
        "item_id",
        "item_payload_sha256",
        "interface_version",
        "shared_rater_guide_version",
        "shared_rater_guide_sha256",
        "semantic_input_sha256",
        "packet_id",
        "output_id",
        "corpus_id",
        "evaluation_role",
    ]
    for actor_id, repetitions in ACTOR_REPETITIONS.items():
        for repetition in repetitions:
            ordered = list(items)
            seed = int.from_bytes(
                hashlib.sha256(
                    f"{SELECTION_SEED}|order|{actor_id}|{repetition}".encode("utf-8")
                ).digest()[:8],
                "big",
            )
            random.Random(seed).shuffle(ordered)
            path = assignment_dir / f"{actor_id}_rep{repetition}.csv"
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                for sequence, item in enumerate(ordered, start=1):
                    writer.writerow(
                        {
                            "assignment_id": opaque(
                                "DJA", actor_id, repetition, item["item_id"]
                            ),
                            "actor_id": actor_id,
                            "actor_kind": ACTOR_KINDS[actor_id],
                            "rating_repetition": repetition,
                            "sequence": sequence,
                            "item_id": item["item_id"],
                            "item_payload_sha256": item_hashes[item["item_id"]],
                            "interface_version": INTERFACE_VERSION,
                            "shared_rater_guide_version": RATER_GUIDE_VERSION,
                            "shared_rater_guide_sha256": guide_sha256,
                            "semantic_input_sha256": semantic_input_hashes[item["item_id"]],
                            "packet_id": item["packet_id"],
                            "output_id": item["output_id"],
                            "corpus_id": item["corpus_id"],
                            "evaluation_role": "synthetic_qualification",
                        }
                    )
            reports[path.name] = {
                "sha256": sha256_path(path),
                "rows": str(len(ordered)),
            }
    return reports


def main() -> None:
    raise SystemExit(
        "Direction J data execution is blocked: no fictional-data permission is active, and real-text governance gates are incomplete."
    )
    assert_prepared_output_is_rebuildable()
    inputs = load_pinned_inputs()
    manifest, benchmark_packets = verify_synthetic_manifest(inputs)
    blind_map = load_blind_map(inputs["blind_map_bytes"])
    schema = inputs["schema"]
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    evaluator_items, private_rows = selected_records(
        benchmark_packets,
        blind_map,
        inputs["bundles"],
    )
    for item in evaluator_items:
        errors = sorted(validator.iter_errors(item), key=lambda error: list(error.path))
        if errors:
            detail = "; ".join(error.message for error in errors[:5])
            raise ValueError(f"Generated item {item['item_id']} fails schema: {detail}")
    evaluator_items.sort(key=lambda item: item["item_id"])
    private_rows.sort(key=lambda row: row["item_id"])
    item_hashes = {
        item["item_id"]: sha256_bytes(canonical_bytes(item)) for item in evaluator_items
    }
    guide_sha256 = sha256_bytes(inputs["guide_bytes"])
    semantic_input_hashes = {
        item_id: semantic_input_sha256(item_hash, guide_sha256)
        for item_id, item_hash in item_hashes.items()
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    evaluator_path = OUTPUT_DIR / "evaluator_items.jsonl"
    private_path = OUTPUT_DIR / "private" / "item_key.jsonl"
    write_jsonl(evaluator_path, evaluator_items)
    write_jsonl(private_path, private_rows)
    private_path.chmod(0o600)
    assignment_report = write_assignments(
        evaluator_items, item_hashes, semantic_input_hashes, guide_sha256
    )

    natural_count = sum(row["condition"] == "natural" for row in private_rows)
    control_count = sum(row["condition"] == "sentinel_control" for row in private_rows)
    model_counts = Counter(row["candidate_model_id"] for row in private_rows)
    model_condition_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for row in private_rows:
        model_condition_counts[row["candidate_model_id"]][row["condition"]] += 1
    control_family_counts = Counter(
        flag
        for row in private_rows
        for flag in row["planted_serious_error_flags"]
    )
    bundle_fileset_sha256 = sha256_bytes(canonical_bytes(inputs["bundle_sha256"]))
    source_receipt = {
        "receipt_version": "direction-j-synthetic-source-receipt-v1",
        "baseline_run_manifest_sha256": sha256_bytes(inputs["manifest_bytes"]),
        "synthetic_benchmark_sha256": sha256_bytes(inputs["benchmark_bytes"]),
        "synthetic_benchmark_provenance": EXPECTED_BENCHMARK_PROVENANCE,
        "independently_authored_fictional_text": True,
        "contains_real_source_text": False,
        "blinded_bundle_fileset_sha256": bundle_fileset_sha256,
        "blinded_bundle_sha256": dict(sorted(inputs["bundle_sha256"].items())),
    }
    source_receipt_sha256 = sha256_bytes(canonical_bytes(source_receipt))
    build_report = {
        "build_version": "direction-j-synthetic-builder-v1",
        "status": "prepared_not_run",
        "qualification_scope": "synthetic_only",
        "contains_real_source_text": False,
        "selection_uses_legacy_judge_scores": False,
        "selection_seed_sha256": sha256_bytes(SELECTION_SEED.encode("utf-8")),
        "evaluator_items": len(evaluator_items),
        "natural_items": natural_count,
        "sentinel_control_items": control_count,
        "unique_fictional_base_packets": len(
            {row["baseline_packet_id"] for row in private_rows}
        ),
        "items_are_source_independent": False,
        "unique_parent_theme_outputs": len(
            {row["parent_natural_item_sha256"] for row in private_rows}
        ),
        "candidate_model_counts_private_audit": dict(sorted(model_counts.items())),
        "candidate_model_condition_counts_private_audit": {
            model: dict(sorted(counts.items()))
            for model, counts in sorted(model_condition_counts.items())
        },
        "planted_family_counts_private_audit": dict(sorted(control_family_counts.items())),
        "source_receipt": source_receipt,
        "source_receipt_sha256": source_receipt_sha256,
        "input_hashes": {
            "baseline_run_manifest": sha256_bytes(inputs["manifest_bytes"]),
            "baseline_blind_map": sha256_bytes(inputs["blind_map_bytes"]),
            "synthetic_benchmark": sha256_bytes(inputs["benchmark_bytes"]),
            "blinded_bundle_fileset": bundle_fileset_sha256,
            "evaluator_item_schema": sha256_bytes(inputs["schema_bytes"]),
            "shared_rater_guide": guide_sha256,
            "direction_j_freeze": sha256_bytes(inputs["freeze_bytes"]),
        },
        "output_hashes": {
            "evaluator_items.jsonl": sha256_path(evaluator_path),
            "private/item_key.jsonl": sha256_path(private_path),
        },
        "assignment_files": assignment_report,
        "legacy_manifest_expected_candidate_records": manifest["expected_run_records"],
        "interpretation": (
            "Fictional engineering qualification only. Sentinel truth covers only "
            "the planted manipulation and is not complete expert adjudication."
        ),
        "qualification_blinding_limit": (
            "Published deterministic IDs provide operational mount isolation only; "
            "they are not secure against a reader of the full workspace."
        ),
    }
    write_json(OUTPUT_DIR / "build_report.json", build_report)
    run_manifest = {
        "run_manifest_version": "direction-j-run-manifest-v1",
        "run_id": "20260825_synthetic_paired_qualification_prepared",
        "status": "prepared_not_run",
        "study_id": "direction-j-v1",
        "evaluation_role": "synthetic_qualification",
        "qualification_scope": "synthetic_only",
        "contains_real_source_text": False,
        "independently_authored_fictional_text": True,
        "ratings_collected": 0,
        "outcomes_available": False,
        "freeze_path": "../../config/freeze_v1.json",
        "evaluator_items_path": "evaluator_items.jsonl",
        "evaluator_items_sha256": sha256_path(evaluator_path),
        "interface_version": INTERFACE_VERSION,
        "shared_rater_guide_version": RATER_GUIDE_VERSION,
        "shared_rater_guide_sha256": guide_sha256,
        "semantic_input_hash_rule": "canonical_manifest_v1",
        "source_receipt_sha256": source_receipt_sha256,
        "synthetic_benchmark_sha256": sha256_bytes(inputs["benchmark_bytes"]),
        "blinded_bundle_fileset_sha256": bundle_fileset_sha256,
        "freeze_sha256": sha256_bytes(inputs["freeze_bytes"]),
        "build_report_sha256": sha256_path(OUTPUT_DIR / "build_report.json"),
        "assignment_manifest_count": len(assignment_report),
        "unique_fictional_base_packets": 4,
        "items_are_source_independent": False,
        "qualification_blinding_strength": (
            "operational_mount_isolation_not_secure_against_workspace_reader"
        ),
        "private_key_path": "private/item_key.jsonl",
        "private_key_sha256": sha256_path(private_path),
        "private_key_must_not_be_mounted_to_evaluators": True,
        "actor_registry_status": "pending_charlie_expert_qualification_and_provider_profile_confirmation",
        "expected_observations": {
            "charlie": 24,
            "J_PRIMARY": 72,
            "J_SENS_GEMINI": 24,
            "QME_QUAL": 24,
            "DOMAIN_QUAL": 24,
        },
        "result_label": "synthetic_qualification_only",
    }
    write_json(OUTPUT_DIR / "run_manifest.json", run_manifest)
    (OUTPUT_DIR / "ratings").mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "raw_model_responses").mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "private" / "README.md").write_text(
        "# Private synthetic key\n\n"
        "Do not mount `item_key.jsonl`, build reports, blind maps, or adjudication "
        "records into an evaluator session. The key contains only synthetic "
        "provenance, but it would reveal conditions and candidate identities.\n",
        encoding="utf-8",
    )
    (OUTPUT_DIR / "ratings" / "README.md").write_text(
        "# Ratings\n\nNo ratings have been collected. Do not create placeholder "
        "records. Store only schema-valid, locked observations with raw-source "
        "hashes.\n",
        encoding="utf-8",
    )
    (OUTPUT_DIR / "raw_model_responses" / "README.md").write_text(
        "# Raw model responses\n\nNo calls have been made. On execution, retain "
        "immutable request/response bytes and telemetry; keep this directory "
        "restricted and never expose it to other evaluator calls.\n",
        encoding="utf-8",
    )
    (OUTPUT_DIR / "README.md").write_text(
        "# Prepared Direction J synthetic qualification\n\n"
        "Status: prepared, not executed. This run contains 24 fictional "
        "evaluator items, seven separately randomized assignment manifests, "
        "and zero ratings, raw model responses, adjudications, repairs, or "
        "empirical results.\n\n"
        "The items reuse four fictional packet contexts across distinct candidate "
        "themes and generation repetitions. They are pipeline checks, not "
        "source-independent observations. The published deterministic IDs provide "
        "only operational blinding: evaluator sessions must not have workspace, "
        "builder, legacy-bundle, or private-map access. Keep `private/item_key.jsonl` "
        "outside every evaluator runtime and unblind only after all declared locks.\n",
        encoding="utf-8",
    )
    print(
        f"Prepared {len(evaluator_items)} synthetic-only items in "
        f"{OUTPUT_DIR.relative_to(PROJECT_ROOT)}"
    )


if __name__ == "__main__":
    main()
