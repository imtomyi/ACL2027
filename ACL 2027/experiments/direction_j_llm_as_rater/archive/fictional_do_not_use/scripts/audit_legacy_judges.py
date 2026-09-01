#!/usr/bin/env python3
"""Inventory the one allowlisted synthetic legacy judge run for Direction J.

This is deliberately a narrow audit, not a general run reader. It has no input
path option, refuses dataset paths, fails closed if the historical manifest no
longer describes synthetic-only data, and never maps legacy judge fields onto
the paper-aligned rating constructs.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


SCRIPT_PATH = Path(__file__).resolve()
DIRECTION_ROOT = SCRIPT_PATH.parents[1]
PROJECT_ROOT = SCRIPT_PATH.parents[3]
LEGACY_ROOT = PROJECT_ROOT / "experiments" / "qualitative_coding_baselines"
RUN_ID = "20260825_synthetic_qualification"
RUN_DIR = LEGACY_ROOT / "runs" / RUN_ID

EXPECTED_MANIFEST_SHA256 = "161b64ac97c5ab3b31af75f31d6a69152545f467a90755a944be79486886cc9d"
EXPECTED_RAW_FILESET_SHA256 = "9b79a46db86381aa89f8c677c5cb8f6a0b6bc6adb6cddfac79199931e744efa9"
EXPECTED_JUDGE_FILESET_SHA256 = "340ba30eae74dd1ab4dfb088917b692e05bdd1cdd266de9cf7be48bd6052de9e"
EXPECTED_BENCHMARK_ID = "qc-synthetic-v1"
EXPECTED_PACKET_IDS = [
    "syn_dreaddit_01",
    "syn_agyw_01",
    "syn_kodis_01",
    "syn_candor_01",
]
EXPECTED_CANDIDATE_MODELS = [
    "gpt-5.6-sol",
    "gpt-5.6-terra",
    "gpt-5.6-luna",
    "gpt-5.5",
    "gpt-5.4",
]
EXPECTED_JUDGE_MODELS = ["gpt-5.6-sol", "gpt-5.5", "gpt-5.4"]
EXPECTED_REPETITIONS = 3
EXPECTED_GENERATION_RECORDS = 60
EXPECTED_JUDGE_RECORDS = 36
EXPECTED_CANDIDATE_SCORE_ROWS = 180

MANIFEST_PATH = RUN_DIR / "run_manifest.json"
BENCHMARK_PATH = LEGACY_ROOT / "benchmark" / "synthetic_packets_v1.json"
EVALUATION_GUIDE_PATH = LEGACY_ROOT / "benchmark" / "evaluation_guide_v1.json"
ANALYTIC_CONTRACT_PATH = LEGACY_ROOT / "protocol" / "analytic_contract.md"
GENERATION_PROMPT_PATH = LEGACY_ROOT / "protocol" / "generation_prompt.md"
JUDGE_PROMPT_PATH = LEGACY_ROOT / "protocol" / "judge_prompt.md"
QUALITATIVE_SCHEMA_PATH = LEGACY_ROOT / "schemas" / "qualitative_output.schema.json"
RUN_SCHEMA_PATH = LEGACY_ROOT / "schemas" / "run_record.schema.json"
JUDGE_SCHEMA_PATH = LEGACY_ROOT / "schemas" / "judge_output.schema.json"
PAPER_RATING_SCHEMA_PATH = LEGACY_ROOT / "schemas" / "paper_metric_rating.schema.json"

BLIND_MAP_PATH = RUN_DIR / "blind_map_private.csv"
HUMAN_TEMPLATE_PATH = RUN_DIR / "human_pairwise_review_template.csv"
JUDGE_SCORE_PATH = RUN_DIR / "judge_scores_long.csv"
JUDGE_SUMMARY_PATH = RUN_DIR / "judge_model_summary.csv"
JUDGE_VALIDATION_PATH = RUN_DIR / "judge_validation_summary.json"
OBJECTIVE_METRICS_PATH = RUN_DIR / "objective_metrics_long.csv"
VALIDATION_ISSUES_PATH = RUN_DIR / "validation_issues.csv"
VALIDATION_SUMMARY_PATH = RUN_DIR / "validation_summary.json"

STATIC_ALLOWED_INPUTS = {
    MANIFEST_PATH,
    BENCHMARK_PATH,
    EVALUATION_GUIDE_PATH,
    ANALYTIC_CONTRACT_PATH,
    GENERATION_PROMPT_PATH,
    JUDGE_PROMPT_PATH,
    QUALITATIVE_SCHEMA_PATH,
    RUN_SCHEMA_PATH,
    JUDGE_SCHEMA_PATH,
    PAPER_RATING_SCHEMA_PATH,
    BLIND_MAP_PATH,
    HUMAN_TEMPLATE_PATH,
    JUDGE_SCORE_PATH,
    JUDGE_SUMMARY_PATH,
    JUDGE_VALIDATION_PATH,
    OBJECTIVE_METRICS_PATH,
    VALIDATION_ISSUES_PATH,
    VALIDATION_SUMMARY_PATH,
}
ALLOWED_RUN_SUBDIRECTORIES = {RUN_DIR / "raw", RUN_DIR / "judges"}
READ_PATHS: set[Path] = set()


def relative_to_project(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT).as_posix()


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def assert_no_dataset_path(path: Path) -> None:
    forbidden = {"dataset", "datasets"}
    if any(part.casefold() in forbidden for part in path.resolve().parts):
        raise RuntimeError(f"Dataset paths are forbidden: {path}")


def assert_allowed_input(path: Path) -> Path:
    resolved = path.resolve()
    assert_no_dataset_path(resolved)
    static = {item.resolve() for item in STATIC_ALLOWED_INPUTS}
    in_allowed_subdirectory = any(
        is_relative_to(resolved, directory.resolve())
        for directory in ALLOWED_RUN_SUBDIRECTORIES
    )
    if resolved not in static and not in_allowed_subdirectory:
        raise RuntimeError(f"Input is outside the legacy audit allowlist: {resolved}")
    if not resolved.is_file():
        raise FileNotFoundError(resolved)
    READ_PATHS.add(resolved)
    return resolved


def read_bytes(path: Path) -> bytes:
    return assert_allowed_input(path).read_bytes()


def read_text(path: Path) -> str:
    return read_bytes(path).decode("utf-8")


def read_json(path: Path) -> Any:
    return json.loads(read_text(path))


def read_csv(path: Path) -> list[dict[str, str]]:
    return list(csv.DictReader(read_text(path).splitlines()))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(read_text(path).splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"Invalid JSON in {path}:{line_number}: {error}") from error
        if not isinstance(value, dict):
            raise ValueError(f"Expected an object in {path}:{line_number}")
        records.append(value)
    return records


def sha256_path(path: Path) -> str:
    return hashlib.sha256(read_bytes(path)).hexdigest()


def fileset_sha256(paths: Iterable[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(read_bytes(path))
        digest.update(b"\0")
    return digest.hexdigest()


def sorted_counts(values: Iterable[Any]) -> dict[str, int]:
    counts = Counter(str(value) for value in values)
    return {key: counts[key] for key in sorted(counts)}


def required_keys(record: dict[str, Any], keys: Iterable[str], label: str) -> None:
    missing = sorted(set(keys) - set(record))
    if missing:
        raise ValueError(f"{label} is missing required keys: {missing}")


def assert_synthetic_manifest(manifest: dict[str, Any]) -> None:
    if sha256_path(MANIFEST_PATH) != EXPECTED_MANIFEST_SHA256:
        raise RuntimeError("Legacy run manifest differs from the hard-allowlisted file")
    required_keys(
        manifest,
        [
            "run_id",
            "qualification_scope",
            "benchmark",
            "models",
            "repetitions_per_model_packet",
            "expected_run_records",
            "supplementary_evaluation",
            "governance",
        ],
        "legacy manifest",
    )
    if manifest["run_id"] != RUN_ID:
        raise RuntimeError(f"Unexpected run_id: {manifest['run_id']!r}")
    if manifest["qualification_scope"] != "synthetic_only":
        raise RuntimeError("Legacy audit permits qualification_scope=synthetic_only only")
    benchmark = manifest["benchmark"]
    if benchmark.get("contains_real_source_text") is not False:
        raise RuntimeError("Legacy benchmark is not explicitly marked as excluding real text")
    if benchmark.get("path") != "benchmark/synthetic_packets_v1.json":
        raise RuntimeError(f"Unexpected benchmark path: {benchmark.get('path')!r}")
    if manifest["models"] != EXPECTED_CANDIDATE_MODELS:
        raise RuntimeError("Candidate model list differs from the hard allowlist")
    if manifest["repetitions_per_model_packet"] != EXPECTED_REPETITIONS:
        raise RuntimeError("Generation repetition count differs from the hard allowlist")
    if manifest["expected_run_records"] != EXPECTED_GENERATION_RECORDS:
        raise RuntimeError("Generation record count differs from the hard allowlist")
    supplementary = manifest["supplementary_evaluation"]
    if supplementary.get("judge_models") != EXPECTED_JUDGE_MODELS:
        raise RuntimeError("Judge model list differs from the hard allowlist")
    if supplementary.get("judge_records") != EXPECTED_JUDGE_RECORDS:
        raise RuntimeError("Judge record count differs from the hard allowlist")
    if supplementary.get("candidate_score_rows") != EXPECTED_CANDIDATE_SCORE_ROWS:
        raise RuntimeError("Candidate-score count differs from the hard allowlist")
    governance = manifest["governance"]
    prohibited_true = [
        "real_dreaddit_processed",
        "real_agyw_processed",
        "real_kodis_available",
        "real_candor_available",
        "heldout_data_used_for_selection",
    ]
    if any(governance.get(field) is not False for field in prohibited_true):
        raise RuntimeError("Manifest does not preserve the required no-real-text/no-heldout gate")


def expected_raw_files(models: list[str], repetitions: int) -> list[Path]:
    return [
        RUN_DIR / "raw" / f"{model}_run{run_index}.jsonl"
        for model in sorted(models)
        for run_index in range(1, repetitions + 1)
    ]


def expected_judge_files(judges: list[str], packet_ids: list[str]) -> list[Path]:
    return [
        RUN_DIR / "judges" / f"judge_{judge}_{packet_id}.jsonl"
        for judge in sorted(judges)
        for packet_id in sorted(packet_ids)
    ]


def assert_exact_file_set(directory: Path, expected: list[Path]) -> None:
    actual = sorted(directory.glob("*.jsonl"))
    expected_sorted = sorted(expected)
    if actual != expected_sorted:
        missing = [relative_to_project(path) for path in expected_sorted if path not in actual]
        extra = [relative_to_project(path) for path in actual if path not in expected_sorted]
        raise RuntimeError(
            f"Unexpected file set under {relative_to_project(directory)}; "
            f"missing={missing}; extra={extra}"
        )


def manifest_hash_checks(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    checks = {
        "run_manifest": (MANIFEST_PATH, EXPECTED_MANIFEST_SHA256),
        "benchmark": (BENCHMARK_PATH, manifest["benchmark"]["sha256"]),
        "analytic_contract": (
            ANALYTIC_CONTRACT_PATH,
            manifest["analytic_contract"]["sha256"],
        ),
        "generation_prompt": (GENERATION_PROMPT_PATH, manifest["prompt"]["sha256"]),
        "qualitative_output_schema": (
            QUALITATIVE_SCHEMA_PATH,
            manifest["output_schema"]["sha256"],
        ),
        "judge_prompt": (
            JUDGE_PROMPT_PATH,
            manifest["supplementary_evaluation"]["judge_prompt_sha256"],
        ),
        "judge_schema": (
            JUDGE_SCHEMA_PATH,
            manifest["supplementary_evaluation"]["judge_schema_sha256"],
        ),
        "evaluation_guide": (
            EVALUATION_GUIDE_PATH,
            manifest["supplementary_evaluation"]["evaluation_guide_sha256"],
        ),
        "blind_map": (
            BLIND_MAP_PATH,
            manifest["supplementary_evaluation"]["blind_map_sha256"],
        ),
    }
    result: dict[str, dict[str, Any]] = {}
    for name, (path, expected) in checks.items():
        observed = sha256_path(path)
        result[name] = {
            "path": relative_to_project(path),
            "expected_sha256": expected,
            "observed_sha256": observed,
            "matches": observed == expected,
        }
    if not all(item["matches"] for item in result.values()):
        raise RuntimeError("One or more frozen legacy inputs do not match the manifest")
    return result


def audit() -> dict[str, Any]:
    manifest = read_json(MANIFEST_PATH)
    assert_synthetic_manifest(manifest)
    hash_checks = manifest_hash_checks(manifest)

    benchmark = read_json(BENCHMARK_PATH)
    packets = benchmark.get("packets", [])
    packet_ids = [str(packet["packet_id"]) for packet in packets]
    if benchmark.get("benchmark_id") != EXPECTED_BENCHMARK_ID:
        raise ValueError("Synthetic benchmark ID differs from the hard allowlist")
    if packet_ids != EXPECTED_PACKET_IDS:
        raise ValueError("Synthetic packet IDs or order differ from the hard allowlist")
    if len(packet_ids) != len(set(packet_ids)):
        raise ValueError("Synthetic benchmark packet IDs are not unique")
    if len(packets) != int(manifest["benchmark"]["packets"]):
        raise ValueError("Benchmark packet count differs from the manifest")

    candidate_models = [str(value) for value in manifest["models"]]
    repetitions = int(manifest["repetitions_per_model_packet"])
    raw_files = expected_raw_files(candidate_models, repetitions)
    assert_exact_file_set(RUN_DIR / "raw", raw_files)
    observed_raw_fileset_sha256 = fileset_sha256(raw_files)
    if observed_raw_fileset_sha256 != EXPECTED_RAW_FILESET_SHA256:
        raise RuntimeError("Raw generation files differ from the hard-allowlisted fileset")
    generation_records = [record for path in raw_files for record in read_jsonl(path)]
    expected_generation_keys = {
        (model, run_index, packet_id)
        for model in candidate_models
        for run_index in range(1, repetitions + 1)
        for packet_id in packet_ids
    }
    generation_keys: list[tuple[str, int, str]] = []
    generation_scope_counts: Counter[str] = Counter()
    runtime_surfaces: Counter[str] = Counter()
    usage_available: Counter[str] = Counter()
    latency_available: Counter[str] = Counter()
    for index, record in enumerate(generation_records, start=1):
        required_keys(
            record,
            [
                "run_record_version",
                "qualification_scope",
                "model_id",
                "run_index",
                "packet_id",
                "prompt_version",
                "schema_version",
                "generated_at_utc",
                "output",
            ],
            f"generation record {index}",
        )
        generation_scope_counts[str(record["qualification_scope"])] += 1
        generation_keys.append(
            (str(record["model_id"]), int(record["run_index"]), str(record["packet_id"]))
        )
        runtime = record.get("runtime", {})
        runtime_surfaces[str(runtime.get("surface", "<missing>"))] += 1
        usage_available[str(bool(runtime.get("usage_available", False))).lower()] += 1
        latency_available[str(bool(runtime.get("latency_available", False))).lower()] += 1
    if set(generation_keys) != expected_generation_keys or len(generation_keys) != len(
        expected_generation_keys
    ):
        raise ValueError("Generation records do not form the expected model/repeat/packet grid")
    if set(generation_scope_counts) != {"synthetic_only"}:
        raise RuntimeError("A generation record is not synthetic_only")
    if len(generation_records) != int(manifest["expected_run_records"]):
        raise ValueError("Generation record count differs from the manifest")

    blind_rows = read_csv(BLIND_MAP_PATH)
    blind_map: dict[tuple[str, int, str], str] = {}
    for row in blind_rows:
        key = (row["packet_id"], int(row["run_index"]), row["blind_id"])
        if key in blind_map:
            raise ValueError(f"Duplicate blind-map key: {key}")
        blind_map[key] = row["model_id"]

    supplementary = manifest["supplementary_evaluation"]
    judge_models = [str(value) for value in supplementary["judge_models"]]
    judge_files = expected_judge_files(judge_models, packet_ids)
    assert_exact_file_set(RUN_DIR / "judges", judge_files)
    observed_judge_fileset_sha256 = fileset_sha256(judge_files)
    if observed_judge_fileset_sha256 != EXPECTED_JUDGE_FILESET_SHA256:
        raise RuntimeError("Judge records differ from the hard-allowlisted fileset")
    judge_records = [record for path in judge_files for record in read_jsonl(path)]
    judge_record_keys: list[tuple[str, str, int]] = []
    candidate_score_rows: list[dict[str, Any]] = []
    self_model_records = 0
    self_model_ratings = 0
    preference_candidate_coverage_failures = 0
    for index, record in enumerate(judge_records, start=1):
        required_keys(
            record,
            [
                "judge_prompt_version",
                "judge_model_id",
                "packet_id",
                "run_index",
                "evaluated_at_utc",
                "candidate_scores",
                "preference_groups",
                "panel_limitations",
            ],
            f"judge record {index}",
        )
        judge_id = str(record["judge_model_id"])
        packet_id = str(record["packet_id"])
        run_index = int(record["run_index"])
        judge_record_keys.append((judge_id, packet_id, run_index))
        mapped_models: list[str] = []
        seen_blinds: list[str] = []
        for score in record["candidate_scores"]:
            blind_id = str(score["blind_id"])
            seen_blinds.append(blind_id)
            key = (packet_id, run_index, blind_id)
            if key not in blind_map:
                raise ValueError(f"Judge score lacks a blind-map entry: {key}")
            model_id = blind_map[key]
            mapped_models.append(model_id)
            candidate_score_rows.append(
                {
                    "judge_model_id": judge_id,
                    "candidate_model_id": model_id,
                    "packet_id": packet_id,
                    "run_index": run_index,
                    "score": score,
                }
            )
            if model_id == judge_id:
                self_model_ratings += 1
        if judge_id in mapped_models:
            self_model_records += 1
        flattened_preferences = [
            str(blind_id)
            for group in record["preference_groups"]
            for blind_id in group
        ]
        if sorted(flattened_preferences) != sorted(seen_blinds):
            preference_candidate_coverage_failures += 1

    expected_judge_keys = {
        (judge, packet_id, run_index)
        for judge in judge_models
        for packet_id in packet_ids
        for run_index in range(1, repetitions + 1)
    }
    if set(judge_record_keys) != expected_judge_keys or len(judge_record_keys) != len(
        expected_judge_keys
    ):
        raise ValueError("Judge records do not form the expected judge/packet/run grid")
    if len(judge_records) != int(supplementary["judge_records"]):
        raise ValueError("Judge record count differs from the manifest")
    if len(candidate_score_rows) != int(supplementary["candidate_score_rows"]):
        raise ValueError("Candidate-score count differs from the manifest")

    judge_schema = read_json(JUDGE_SCHEMA_PATH)
    paper_schema = read_json(PAPER_RATING_SCHEMA_PATH)
    run_schema = read_json(RUN_SCHEMA_PATH)
    qualitative_schema = read_json(QUALITATIVE_SCHEMA_PATH)
    legacy_candidate_schema = judge_schema["properties"]["candidate_scores"]["items"]
    legacy_candidate_required = set(legacy_candidate_schema["required"])
    paper_required = set(paper_schema["required"])
    shared_named_fields = sorted(legacy_candidate_required & paper_required)
    legacy_error_enum = legacy_candidate_schema["properties"]["serious_error_flags"][
        "items"
    ]["enum"]
    paper_error_enum = paper_schema["properties"]["serious_error_flags"]["items"][
        "enum"
    ]

    human_rows = read_csv(HUMAN_TEMPLATE_PATH)
    human_status_counts = sorted_counts(row.get("review_status", "") for row in human_rows)
    populated_human_ratings = sum(
        bool(row.get("reviewer_id", "").strip())
        or bool(row.get("pairwise_choice", "").strip())
        for row in human_rows
    )

    score_dispositions = sorted_counts(
        row["score"].get("disposition", "<missing>") for row in candidate_score_rows
    )
    score_confidences = sorted_counts(
        row["score"].get("confidence", "<missing>") for row in candidate_score_rows
    )
    error_flags = sorted_counts(
        flag
        for row in candidate_score_rows
        for flag in row["score"].get("serious_error_flags", [])
    )
    rationale_nonempty = sum(
        bool(str(row["score"].get("rationale", "")).strip())
        for row in candidate_score_rows
    )

    objective_rows = read_csv(OBJECTIVE_METRICS_PATH)
    validation_issues = read_csv(VALIDATION_ISSUES_PATH)
    validation_summary = read_json(VALIDATION_SUMMARY_PATH)
    judge_validation_summary = read_json(JUDGE_VALIDATION_PATH)
    judge_score_rows = read_csv(JUDGE_SCORE_PATH)
    judge_summary_rows = read_csv(JUDGE_SUMMARY_PATH)

    overlap = sorted(set(candidate_models) & set(judge_models))
    output: dict[str, Any] = {
        "inventory_version": "direction-j-legacy-judge-inventory-v1",
        "scope": {
            "source_run_id": RUN_ID,
            "qualification_scope": manifest["qualification_scope"],
            "synthetic_only": True,
            "contains_real_source_text": False,
            "legacy_results_are_confirmatory": False,
            "human_comparability_established": False,
            "legacy_fields_may_be_reinterpreted_as_paper_metrics": False,
        },
        "guardrails": {
            "input_run_is_hard_allowlisted": True,
            "input_path_argument_supported": False,
            "dataset_paths_forbidden": True,
            "manifest_hashes_verified": True,
            "manifest_hash_checks": hash_checks,
            "raw_fileset_sha256": {
                "expected": EXPECTED_RAW_FILESET_SHA256,
                "observed": observed_raw_fileset_sha256,
                "matches": True,
            },
            "judge_fileset_sha256": {
                "expected": EXPECTED_JUDGE_FILESET_SHA256,
                "observed": observed_judge_fileset_sha256,
                "matches": True,
            },
        },
        "synthetic_benchmark": {
            "benchmark_id": benchmark.get("benchmark_id"),
            "packet_count": len(packets),
            "excerpt_count": sum(len(packet.get("excerpts", [])) for packet in packets),
            "packet_ids": sorted(packet_ids),
            "packets": [
                {
                    "packet_id": packet["packet_id"],
                    "corpus_proxy": packet["corpus_proxy"],
                    "status": packet["status"],
                    "excerpt_count": len(packet.get("excerpts", [])),
                    "distinct_source_count": len(
                        {excerpt["source_id"] for excerpt in packet.get("excerpts", [])}
                    ),
                }
                for packet in sorted(packets, key=lambda item: item["packet_id"])
            ],
        },
        "generation_records": {
            "candidate_models": candidate_models,
            "model_count": len(candidate_models),
            "generation_repetitions_per_model_packet": repetitions,
            "raw_file_count": len(raw_files),
            "record_count": len(generation_records),
            "records_by_model": sorted_counts(record["model_id"] for record in generation_records),
            "records_by_packet": sorted_counts(record["packet_id"] for record in generation_records),
            "qualification_scope_counts": dict(sorted(generation_scope_counts.items())),
            "runtime_surface_counts": dict(sorted(runtime_surfaces.items())),
            "usage_available_counts": dict(sorted(usage_available.items())),
            "latency_available_counts": dict(sorted(latency_available.items())),
            "reported_validation": validation_summary,
            "objective_metric_row_count": len(objective_rows),
            "deterministic_validation_issue_count": len(validation_issues),
            "deterministic_validation_issues_by_severity": sorted_counts(
                row.get("severity", "") for row in validation_issues
            ),
            "deterministic_validation_issues_by_kind": sorted_counts(
                row.get("kind", "") for row in validation_issues
            ),
        },
        "legacy_model_judges": {
            "judge_models": judge_models,
            "judge_model_count": len(judge_models),
            "judge_file_count": len(judge_files),
            "judge_record_count": len(judge_records),
            "candidate_score_count": len(candidate_score_rows),
            "unique_candidate_output_count": len(expected_generation_keys),
            "ratings_per_candidate_model": sorted_counts(
                row["candidate_model_id"] for row in candidate_score_rows
            ),
            "records_per_judge_model": sorted_counts(
                record["judge_model_id"] for record in judge_records
            ),
            "candidate_scores_per_record": sorted_counts(
                len(record["candidate_scores"]) for record in judge_records
            ),
            "preference_candidate_coverage_failures": preference_candidate_coverage_failures,
            "disposition_counts": score_dispositions,
            "confidence_counts": score_confidences,
            "serious_error_flag_counts": error_flags,
            "nonempty_rationale_count": rationale_nonempty,
            "escalation_count": score_dispositions.get("escalate", 0),
            "reported_validation": judge_validation_summary,
            "derived_long_score_row_count": len(judge_score_rows),
            "derived_model_summary_row_count": len(judge_summary_rows),
        },
        "model_overlap": {
            "candidate_model_ids": sorted(candidate_models),
            "judge_model_ids": sorted(judge_models),
            "exact_model_id_overlap": overlap,
            "exact_model_id_overlap_count": len(overlap),
            "candidate_models_not_used_as_judges": sorted(
                set(candidate_models) - set(judge_models)
            ),
            "judge_models_not_in_candidate_pool": sorted(
                set(judge_models) - set(candidate_models)
            ),
            "judge_records_containing_an_exact_self_model_candidate": self_model_records,
            "exact_self_model_candidate_ratings": self_model_ratings,
            "every_judge_record_contains_an_exact_self_model_candidate": (
                self_model_records == len(judge_records)
            ),
            "same_vendor_panel_declared_in_manifest": (
                "same-vendor judge panel" in supplementary.get("limitations", [])
            ),
            "candidate_judge_family_overlap_declared_in_manifest": (
                "candidate and judge model families overlap"
                in supplementary.get("limitations", [])
            ),
            "cross_vendor_or_independent_judge_present": False,
        },
        "schema_inventory": {
            "run_record_schema_id": run_schema.get("$id"),
            "qualitative_output_schema_id": qualitative_schema.get("$id"),
            "legacy_judge_schema_id": judge_schema.get("$id"),
            "paper_rating_schema_id": paper_schema.get("$id"),
            "legacy_judge_top_level_required": sorted(judge_schema["required"]),
            "legacy_candidate_score_required": sorted(legacy_candidate_required),
            "paper_rating_required": sorted(paper_required),
            "identically_named_required_fields": shared_named_fields,
            "paper_required_not_in_legacy_candidate_score": sorted(
                paper_required - legacy_candidate_required
            ),
            "legacy_candidate_required_not_in_paper_rating": sorted(
                legacy_candidate_required - paper_required
            ),
            "serious_error_enum_identical": legacy_error_enum == paper_error_enum,
            "serious_error_enum": legacy_error_enum,
            "paper_evaluator_group_enum": paper_schema["properties"]["evaluator_group"][
                "enum"
            ],
        },
        "interface_gaps": {
            "rating_unit": {
                "legacy": "one judge record scores and ranks exactly five candidates",
                "paper_aligned": "one rater rates one output_id per record",
            },
            "paper_constructs_absent_from_legacy_schema": [
                "evidential_credibility",
                "voice_boundary_preservation",
                "scope_calibration",
            ],
            "non_equivalence_constraints": [
                "legacy evidential_support is not evidential_credibility",
                "legacy voice_context_preservation plus negative_case_preservation is not the single voice_boundary_preservation item",
                "legacy analytic_contract_fit is not scope_calibration",
            ],
            "cannot_judge": "absent; legacy quality scores are mandatory integers",
            "abstention": "no metric-level abstention; escalate is available only as a disposition",
            "timing_and_cost": "no judge review_seconds, request latency, token usage, or cost fields",
            "judge_repetition": "legacy run_index identifies the candidate-generation repeat; no independent judge_repeat_index exists",
            "rater_identity": "judge_model_id exists, but no explicit rater_kind/provider/snapshot fields exist",
            "human_role_mislabeling_risk": "paper evaluator_group contains human expertise roles only and must not be assigned to an LLM",
            "serious_error_localization": "flags have types only; there is no target path, cited location, or error-level rationale",
            "rationale_usefulness": "free-text rationales exist, but no usefulness rating or downstream use measurement exists",
            "expert_reference": "no independent expert adjudication record or task-outcome reference is linked",
            "repair": "no repair attempt, resolved-error, collateral-error, or repaired-output linkage exists",
            "prompt_schema_mismatch": "overall_quality and panel_limitations are schema-required but are not explicitly defined as judge tasks in qc-judge-v1",
            "comparative_context": "legacy judges saw all five candidates together; scores are not isolated first-stage ratings",
        },
        "human_evidence_status": {
            "pairwise_template_row_count": len(human_rows),
            "review_status_counts": human_status_counts,
            "rows_with_reviewer_or_pairwise_choice": populated_human_ratings,
            "independent_human_ratings_available": False,
            "human_llm_agreement_estimable_from_legacy_run": False,
        },
        "outcome_availability": {
            "legacy_model_judge_score_agreement": "derivable among the three overlapping model judges only",
            "human_agreement": "not available",
            "serious_error_flags": "available as unadjudicated model-judge flags",
            "calibration_against_expert_adjudication": "not available",
            "metric_level_abstention": "not available",
            "escalation": "schema field available; no observed escalations",
            "rationale_text": "available",
            "rationale_usefulness": "not rated",
            "judge_cost": "not available",
            "judge_latency": "not available",
            "downstream_repair": "not available",
            "collateral_error": "not available",
        },
        "interpretation_limits": [
            "The source artifacts are a synthetic engineering qualification, not real-corpus evidence.",
            "All legacy judges are same-vendor models and exact candidate/judge model IDs overlap.",
            "The blank pairwise human template is not human rating evidence.",
            "Legacy field names must not be substituted for the paper-aligned constructs.",
            "Agreement among overlapping model judges is not validity and cannot replace independent expert adjudication or task outcomes.",
        ],
    }

    # Force reads of the explicitly referenced frozen contracts so their hashes
    # appear in the source inventory even when the manifest already supplied a
    # matching digest.
    for path in [RUN_SCHEMA_PATH, PAPER_RATING_SCHEMA_PATH]:
        sha256_path(path)
    output["source_files"] = [
        {
            "path": relative_to_project(path),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        for path in sorted(READ_PATHS)
    ]
    return output


def resolve_output(raw: str) -> Path:
    candidate = Path(raw)
    resolved = candidate.resolve() if candidate.is_absolute() else (PROJECT_ROOT / candidate).resolve()
    assert_no_dataset_path(resolved)
    if not is_relative_to(resolved, DIRECTION_ROOT.resolve()):
        raise RuntimeError(
            "Output must remain under experiments/direction_j_llm_as_rater"
        )
    if is_relative_to(resolved, LEGACY_ROOT.resolve()):
        raise RuntimeError("The legacy baseline tree is read-only for this audit")
    return resolved


def main() -> int:
    raise SystemExit(
        "Direction J data execution is blocked: no fictional-data permission is active, and real-text governance gates are incomplete."
    )
    parser = argparse.ArgumentParser(
        description="Audit the hard-allowlisted synthetic legacy model-judge run."
    )
    parser.add_argument(
        "--output",
        required=True,
        help="JSON destination under experiments/direction_j_llm_as_rater/",
    )
    args = parser.parse_args()
    output_path = resolve_output(args.output)
    inventory = audit()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(inventory, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "output": relative_to_project(output_path),
                "source_run_id": RUN_ID,
                "synthetic_only": True,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
