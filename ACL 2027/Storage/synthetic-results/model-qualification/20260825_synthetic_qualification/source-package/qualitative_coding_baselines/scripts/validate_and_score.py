#!/usr/bin/env python3
"""Validate qualitative-coding run records and compute integrity diagnostics.

The metrics in this script are deliberately limited to machine-checkable
properties. They do not score interpretive truth or replace blinded reviewers.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import math
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parents[1]
DEFAULT_RUN_DIR = PROJECT_ROOT / "Storage" / "synthetic-results" / "model-qualification" / "20260825_synthetic_qualification"
BENCHMARK_PATH = ROOT / "benchmark" / "synthetic_packets_v1.json"
OUTPUT_SCHEMA_PATH = ROOT / "schemas" / "qualitative_output.schema.json"

TOKEN_RE = re.compile(r"[a-z0-9]+")
BROAD_RE = re.compile(
    r"\b(most|typically|typical|generally|always|never|the population|proves?|causes?)\b",
    re.IGNORECASE,
)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ratio(numerator: int | float, denominator: int | float) -> float:
    return float(numerator) / float(denominator) if denominator else 0.0


def mean(values: Iterable[float]) -> float:
    vals = list(values)
    return statistics.fmean(vals) if vals else 0.0


def jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return ratio(len(left & right), len(union)) if union else 1.0


def token_set(values: Iterable[str]) -> set[str]:
    return {
        token
        for value in values
        for token in TOKEN_RE.findall(str(value).lower())
        if len(token) > 2
    }


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def iter_citations(output: dict[str, Any]) -> Iterable[tuple[str, dict[str, Any]]]:
    for code in output.get("codes", []):
        for citation in code.get("exemplars", []):
            yield "code_exemplar", citation
    for theme in output.get("themes", []):
        for citation in theme.get("evidence", []):
            yield "theme_evidence", citation
        for citation in theme.get("counterevidence", []):
            yield "theme_counterevidence", citation
    for citation in output.get("negative_cases", []):
        yield "negative_case", citation


def flatten_validation_error(error: Any) -> str:
    location = "/".join(str(part) for part in error.absolute_path)
    return f"{location or '<root>'}: {error.message}"


def validate_record(
    envelope: dict[str, Any],
    packets: dict[str, dict[str, Any]],
    validator: Draft202012Validator,
    source_file: str,
    line_number: int,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, set[str]]]:
    issues: list[dict[str, Any]] = []
    output = envelope.get("output") if isinstance(envelope, dict) else None
    model_id = str(envelope.get("model_id", "")) if isinstance(envelope, dict) else ""
    run_index = envelope.get("run_index") if isinstance(envelope, dict) else None
    packet_id = str(envelope.get("packet_id", "")) if isinstance(envelope, dict) else ""

    def issue(kind: str, detail: str, severity: str = "error") -> None:
        issues.append(
            {
                "source_file": source_file,
                "line_number": line_number,
                "model_id": model_id,
                "run_index": run_index,
                "packet_id": packet_id,
                "severity": severity,
                "kind": kind,
                "detail": detail,
            }
        )

    required_envelope = {
        "run_record_version",
        "qualification_scope",
        "model_id",
        "run_index",
        "packet_id",
        "prompt_version",
        "schema_version",
        "generated_at_utc",
        "output",
    }
    missing_envelope = sorted(required_envelope - set(envelope)) if isinstance(envelope, dict) else []
    for key in missing_envelope:
        issue("missing_envelope_field", key)
    if envelope.get("qualification_scope") != "synthetic_only":
        issue("scope_mismatch", "qualification_scope must be synthetic_only")
    if envelope.get("prompt_version") != "qc-direct-v1":
        issue("prompt_version_mismatch", str(envelope.get("prompt_version")))
    if envelope.get("schema_version") != "qualitative-output-v1":
        issue("schema_version_mismatch", str(envelope.get("schema_version")))
    if packet_id not in packets:
        issue("unknown_packet", packet_id)
        packet = {"excerpts": []}
    else:
        packet = packets[packet_id]
    if not isinstance(output, dict):
        issue("missing_output", "output must be an object")
        output = {}
    if output.get("packet_id") != packet_id:
        issue("packet_id_mismatch", f"output={output.get('packet_id')} envelope={packet_id}")
    expected_question = packet.get("research_question")
    if output.get("research_question") != expected_question:
        issue("research_question_mismatch", "output must reproduce the packet question exactly")

    schema_errors = sorted(validator.iter_errors(output), key=lambda err: list(err.absolute_path))
    for error in schema_errors:
        issue("output_schema", flatten_validation_error(error))

    excerpts = {item["excerpt_id"]: item for item in packet.get("excerpts", [])}
    sources = {item["source_id"] for item in packet.get("excerpts", [])}
    code_ids = [item.get("code_id") for item in output.get("codes", []) if isinstance(item, dict)]
    theme_ids = [item.get("theme_id") for item in output.get("themes", []) if isinstance(item, dict)]
    code_id_set = {item for item in code_ids if item}
    duplicate_code_ids = len(code_ids) - len(set(code_ids))
    duplicate_theme_ids = len(theme_ids) - len(set(theme_ids))
    if duplicate_code_ids:
        issue("duplicate_code_id", str(duplicate_code_ids))
    if duplicate_theme_ids:
        issue("duplicate_theme_id", str(duplicate_theme_ids))

    assignments = output.get("assignments", []) if isinstance(output.get("assignments", []), list) else []
    assignment_ids = [item.get("excerpt_id") for item in assignments if isinstance(item, dict)]
    assignment_counts = Counter(assignment_ids)
    missing_assignments = sorted(set(excerpts) - set(assignment_ids))
    extra_assignments = sorted(set(assignment_ids) - set(excerpts))
    duplicate_assignments = sorted(key for key, count in assignment_counts.items() if count > 1)
    for excerpt_id in missing_assignments:
        issue("missing_assignment", excerpt_id)
    for excerpt_id in extra_assignments:
        issue("unknown_assignment_excerpt", excerpt_id)
    for excerpt_id in duplicate_assignments:
        issue("duplicate_assignment", excerpt_id)

    assignment_ref_total = 0
    assignment_ref_valid = 0
    not_coded_inconsistent = 0
    for assignment in assignments:
        if not isinstance(assignment, dict):
            continue
        refs = assignment.get("code_ids", []) if isinstance(assignment.get("code_ids", []), list) else []
        for code_id in refs:
            assignment_ref_total += 1
            if code_id in code_id_set:
                assignment_ref_valid += 1
            else:
                issue("unknown_assignment_code", f"{assignment.get('excerpt_id')} -> {code_id}")
        if bool(assignment.get("not_coded")) == bool(refs):
            not_coded_inconsistent += 1
            issue(
                "not_coded_inconsistent",
                f"{assignment.get('excerpt_id')}: not_coded={assignment.get('not_coded')} code_ids={refs}",
            )

    theme_ref_total = 0
    theme_ref_valid = 0
    theme_source_diversity: list[int] = []
    theme_concentration: list[float] = []
    theme_source_list_exact = 0
    theme_count = 0
    citation_counter_by_type: Counter[str] = Counter()
    valid_excerpt_citations: set[str] = set()
    valid_source_citations: set[str] = set()
    citation_total = 0
    excerpt_valid = 0
    source_valid = 0
    attribution_valid = 0
    quote_exact = 0

    for citation_type, citation in iter_citations(output):
        citation_counter_by_type[citation_type] += 1
        citation_total += 1
        if not isinstance(citation, dict):
            issue("citation_not_object", citation_type)
            continue
        excerpt_id = citation.get("excerpt_id")
        source_id = citation.get("source_id")
        quote = citation.get("quote")
        excerpt = excerpts.get(excerpt_id)
        if excerpt is not None:
            excerpt_valid += 1
            valid_excerpt_citations.add(excerpt_id)
        else:
            issue("unknown_citation_excerpt", f"{citation_type}: {excerpt_id}")
        if source_id in sources:
            source_valid += 1
            valid_source_citations.add(source_id)
        else:
            issue("unknown_citation_source", f"{citation_type}: {source_id}")
        if excerpt is not None and source_id == excerpt.get("source_id"):
            attribution_valid += 1
        elif excerpt is not None:
            issue(
                "citation_attribution_mismatch",
                f"{citation_type}: {excerpt_id} belongs to {excerpt.get('source_id')}, not {source_id}",
            )
        if excerpt is not None and isinstance(quote, str) and quote in excerpt.get("text", ""):
            quote_exact += 1
        else:
            issue("non_exact_quote", f"{citation_type}: {excerpt_id}: {quote!r}")

    for theme in output.get("themes", []):
        if not isinstance(theme, dict):
            continue
        theme_count += 1
        for code_id in theme.get("code_ids", []):
            theme_ref_total += 1
            if code_id in code_id_set:
                theme_ref_valid += 1
            else:
                issue("unknown_theme_code", f"{theme.get('theme_id')} -> {code_id}")
        evidence = [item for item in theme.get("evidence", []) if isinstance(item, dict)]
        counterevidence = [
            item for item in theme.get("counterevidence", []) if isinstance(item, dict)
        ]
        evidence_sources = [item.get("source_id") for item in evidence if item.get("source_id")]
        unique_evidence_sources = set(evidence_sources)
        theme_source_diversity.append(len(unique_evidence_sources))
        counts = Counter(evidence_sources)
        theme_concentration.append(ratio(max(counts.values(), default=0), len(evidence_sources)))
        represented_sources = unique_evidence_sources | {
            item.get("source_id") for item in counterevidence if item.get("source_id")
        }
        declared_sources = set(theme.get("source_ids", []))
        if declared_sources == represented_sources:
            theme_source_list_exact += 1
        else:
            issue(
                "theme_source_list_mismatch",
                f"{theme.get('theme_id')}: declared={sorted(declared_sources)} represented={sorted(represented_sources)}",
                severity="warning",
            )
        if len(unique_evidence_sources) < 2:
            issue("single_source_theme", str(theme.get("theme_id")))

    claim_text = " ".join(
        [str(output.get("analysis_summary", ""))]
        + [str(theme.get("claim", "")) for theme in output.get("themes", []) if isinstance(theme, dict)]
        + [str(theme.get("explanation", "")) for theme in output.get("themes", []) if isinstance(theme, dict)]
    )
    broad_terms = BROAD_RE.findall(claim_text)

    schema_error_count = sum(1 for item in issues if item["kind"] == "output_schema")
    exact_quote_rate = ratio(quote_exact, citation_total)
    attribution_rate = ratio(attribution_valid, citation_total)
    assignment_completeness = ratio(len(set(assignment_ids) & set(excerpts)), len(excerpts))
    code_ref_rate = ratio(assignment_ref_valid + theme_ref_valid, assignment_ref_total + theme_ref_total)
    multi_source_theme_rate = ratio(sum(value >= 2 for value in theme_source_diversity), theme_count)
    hard_gate_pass = int(
        schema_error_count == 0
        and exact_quote_rate == 1.0
        and attribution_rate == 1.0
        and assignment_completeness == 1.0
        and not extra_assignments
        and not duplicate_assignments
        and code_ref_rate == 1.0
        and not_coded_inconsistent == 0
        and multi_source_theme_rate == 1.0
    )

    metrics = {
        "source_file": source_file,
        "line_number": line_number,
        "model_id": model_id,
        "run_index": run_index,
        "packet_id": packet_id,
        "schema_valid": int(schema_error_count == 0),
        "schema_error_count": schema_error_count,
        "issue_count": len(issues),
        "hard_gate_pass": hard_gate_pass,
        "code_count": len(output.get("codes", [])),
        "theme_count": len(output.get("themes", [])),
        "assignment_count": len(assignments),
        "assignment_completeness": assignment_completeness,
        "code_reference_validity": code_ref_rate,
        "citation_count": citation_total,
        "exact_quote_rate": exact_quote_rate,
        "source_id_validity": ratio(source_valid, citation_total),
        "attribution_validity": attribution_rate,
        "cited_excerpt_coverage": ratio(len(valid_excerpt_citations), len(excerpts)),
        "cited_source_coverage": ratio(len(valid_source_citations), len(sources)),
        "theme_multi_source_rate": multi_source_theme_rate,
        "mean_theme_source_count": mean(theme_source_diversity),
        "mean_theme_source_concentration": mean(theme_concentration),
        "theme_source_list_exact_rate": ratio(theme_source_list_exact, theme_count),
        "counterevidence_count": citation_counter_by_type["theme_counterevidence"],
        "negative_case_count": citation_counter_by_type["negative_case"],
        "broad_claim_term_count": len(broad_terms),
    }
    features = {
        "code_label_tokens": token_set(
            code.get("label", "") for code in output.get("codes", []) if isinstance(code, dict)
        ),
        "theme_name_tokens": token_set(
            theme.get("name", "") for theme in output.get("themes", []) if isinstance(theme, dict)
        ),
        "cited_excerpts": valid_excerpt_citations,
        "negative_case_excerpts": {
            item.get("excerpt_id")
            for item in output.get("negative_cases", [])
            if isinstance(item, dict) and item.get("excerpt_id") in excerpts
        },
    }
    return metrics, issues, features


def aggregate_model_rows(metric_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in metric_rows:
        groups[str(row["model_id"])].append(row)
    summaries: list[dict[str, Any]] = []
    metric_fields = [
        "schema_valid",
        "hard_gate_pass",
        "assignment_completeness",
        "code_reference_validity",
        "exact_quote_rate",
        "attribution_validity",
        "cited_excerpt_coverage",
        "cited_source_coverage",
        "theme_multi_source_rate",
        "mean_theme_source_count",
        "mean_theme_source_concentration",
        "theme_source_list_exact_rate",
        "counterevidence_count",
        "negative_case_count",
        "broad_claim_term_count",
    ]
    for model_id, rows in sorted(groups.items()):
        result: dict[str, Any] = {"model_id": model_id, "run_records": len(rows)}
        for field in metric_fields:
            result[f"mean_{field}"] = mean(float(row[field]) for row in rows)
        result["all_records_hard_gate_pass"] = int(all(row["hard_gate_pass"] == 1 for row in rows))
        result["total_issues"] = sum(int(row["issue_count"]) for row in rows)
        summaries.append(result)
    return summaries


def stability_rows(
    metric_rows: list[dict[str, Any]],
    feature_rows: dict[tuple[str, int, str], dict[str, set[str]]],
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in metric_rows:
        grouped[(str(row["model_id"]), str(row["packet_id"]))].append(row)
    rows: list[dict[str, Any]] = []
    for (model_id, packet_id), items in sorted(grouped.items()):
        items = sorted(items, key=lambda row: int(row["run_index"]))
        pairs = list(itertools.combinations(items, 2))
        pair_scores: dict[str, list[float]] = defaultdict(list)
        for left, right in pairs:
            left_features = feature_rows[(model_id, int(left["run_index"]), packet_id)]
            right_features = feature_rows[(model_id, int(right["run_index"]), packet_id)]
            for field in [
                "code_label_tokens",
                "theme_name_tokens",
                "cited_excerpts",
                "negative_case_excerpts",
            ]:
                pair_scores[field].append(jaccard(left_features[field], right_features[field]))
        code_counts = [float(item["code_count"]) for item in items]
        theme_counts = [float(item["theme_count"]) for item in items]
        rows.append(
            {
                "model_id": model_id,
                "packet_id": packet_id,
                "runs_present": len(items),
                "pair_count": len(pairs),
                "mean_code_label_token_jaccard": mean(pair_scores["code_label_tokens"]),
                "mean_theme_name_token_jaccard": mean(pair_scores["theme_name_tokens"]),
                "mean_cited_excerpt_jaccard": mean(pair_scores["cited_excerpts"]),
                "mean_negative_case_jaccard": mean(pair_scores["negative_case_excerpts"]),
                "code_count_sd": statistics.pstdev(code_counts) if len(code_counts) > 1 else 0.0,
                "theme_count_sd": statistics.pstdev(theme_counts) if len(theme_counts) > 1 else 0.0,
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    args = parser.parse_args()
    run_dir = args.run_dir.resolve()
    raw_dir = run_dir / "raw"
    benchmark = read_json(BENCHMARK_PATH)
    packets = {packet["packet_id"]: packet for packet in benchmark["packets"]}
    output_schema = read_json(OUTPUT_SCHEMA_PATH)
    validator = Draft202012Validator(output_schema)

    metric_rows: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    inventory: list[dict[str, Any]] = []
    features: dict[tuple[str, int, str], dict[str, set[str]]] = {}

    for path in sorted(raw_dir.glob("*.jsonl")):
        parsed = 0
        parse_errors = 0
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    envelope = json.loads(line)
                except json.JSONDecodeError as error:
                    parse_errors += 1
                    issues.append(
                        {
                            "source_file": path.name,
                            "line_number": line_number,
                            "model_id": "",
                            "run_index": "",
                            "packet_id": "",
                            "severity": "error",
                            "kind": "json_parse",
                            "detail": str(error),
                        }
                    )
                    continue
                parsed += 1
                metrics, record_issues, record_features = validate_record(
                    envelope, packets, validator, path.name, line_number
                )
                metric_rows.append(metrics)
                issues.extend(record_issues)
                feature_key = (
                    str(metrics["model_id"]),
                    int(metrics["run_index"]),
                    str(metrics["packet_id"]),
                )
                features[feature_key] = record_features
        inventory.append(
            {
                "source_file": path.name,
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "records_parsed": parsed,
                "parse_errors": parse_errors,
            }
        )

    duplicate_keys = [
        key
        for key, count in Counter(
            (row["model_id"], row["run_index"], row["packet_id"]) for row in metric_rows
        ).items()
        if count > 1
    ]
    for model_id, run_index, packet_id in duplicate_keys:
        issues.append(
            {
                "source_file": "",
                "line_number": "",
                "model_id": model_id,
                "run_index": run_index,
                "packet_id": packet_id,
                "severity": "error",
                "kind": "duplicate_run_key",
                "detail": "model_id/run_index/packet_id must be unique",
            }
        )

    metric_fields = [
        "source_file",
        "line_number",
        "model_id",
        "run_index",
        "packet_id",
        "schema_valid",
        "schema_error_count",
        "issue_count",
        "hard_gate_pass",
        "code_count",
        "theme_count",
        "assignment_count",
        "assignment_completeness",
        "code_reference_validity",
        "citation_count",
        "exact_quote_rate",
        "source_id_validity",
        "attribution_validity",
        "cited_excerpt_coverage",
        "cited_source_coverage",
        "theme_multi_source_rate",
        "mean_theme_source_count",
        "mean_theme_source_concentration",
        "theme_source_list_exact_rate",
        "counterevidence_count",
        "negative_case_count",
        "broad_claim_term_count",
    ]
    summary_rows = aggregate_model_rows(metric_rows)
    stability = stability_rows(metric_rows, features)
    write_csv(
        run_dir / "run_inventory.csv",
        inventory,
        ["source_file", "bytes", "sha256", "records_parsed", "parse_errors"],
    )
    write_csv(run_dir / "objective_metrics_long.csv", metric_rows, metric_fields)
    issue_fields = [
        "source_file",
        "line_number",
        "model_id",
        "run_index",
        "packet_id",
        "severity",
        "kind",
        "detail",
    ]
    write_csv(run_dir / "validation_issues.csv", issues, issue_fields)
    with (run_dir / "validation_issues.jsonl").open("w", encoding="utf-8") as handle:
        for item in issues:
            handle.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")
    if summary_rows:
        write_csv(run_dir / "model_objective_summary.csv", summary_rows, list(summary_rows[0]))
    if stability:
        write_csv(run_dir / "stability_by_model_packet.csv", stability, list(stability[0]))

    expected_keys = {
        (model, run_index, packet_id)
        for model in ["gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna", "gpt-5.5", "gpt-5.4"]
        for run_index in [1, 2, 3]
        for packet_id in packets
    }
    observed_keys = {
        (str(row["model_id"]), int(row["run_index"]), str(row["packet_id"])) for row in metric_rows
    }
    audit = {
        "run_records": len(metric_rows),
        "expected_run_records": len(expected_keys),
        "missing_run_keys": [list(key) for key in sorted(expected_keys - observed_keys)],
        "unexpected_run_keys": [list(key) for key in sorted(observed_keys - expected_keys)],
        "duplicate_run_keys": [list(key) for key in duplicate_keys],
        "validation_issue_count": len(issues),
        "hard_gate_pass_records": sum(int(row["hard_gate_pass"]) for row in metric_rows),
        "complete": observed_keys == expected_keys and not duplicate_keys,
    }
    (run_dir / "validation_summary.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(audit, sort_keys=True))
    return 0 if audit["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
