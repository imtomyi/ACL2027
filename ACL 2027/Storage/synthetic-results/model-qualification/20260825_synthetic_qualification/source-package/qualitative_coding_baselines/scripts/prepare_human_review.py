#!/usr/bin/env python3
"""Create blinded pairwise review assignments and a flat blind-output index."""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parents[1]
DEFAULT_RUN_DIR = PROJECT_ROOT / "Storage" / "synthetic-results" / "model-qualification" / "20260825_synthetic_qualification"
SIDE_SEED = "qc-human-pair-side-20260825"


def join_lines(values: list[str]) -> str:
    return "\n".join(value for value in values if value)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    args = parser.parse_args()
    run_dir = args.run_dir.resolve()
    blind_dir = run_dir / "blinded"
    review_rows: list[dict[str, Any]] = []
    output_rows: list[dict[str, Any]] = []
    source_rows: list[dict[str, Any]] = []
    seen_sources: set[tuple[str, str]] = set()

    for bundle_path in sorted(blind_dir.glob("syn_*_run*.json")):
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        packet = bundle["packet"]
        packet_id = bundle["packet_id"]
        run_index = int(bundle["run_index"])
        for excerpt in packet["excerpts"]:
            source_key = (packet_id, excerpt["excerpt_id"])
            if source_key not in seen_sources:
                seen_sources.add(source_key)
                source_rows.append(
                    {
                        "packet_id": packet_id,
                        "corpus_proxy": packet["corpus_proxy"],
                        "research_question": packet["research_question"],
                        "excerpt_id": excerpt["excerpt_id"],
                        "source_id": excerpt["source_id"],
                        "speaker_id": excerpt.get("speaker_id") or "",
                        "context": excerpt.get("context", ""),
                        "text": excerpt["text"],
                    }
                )
        candidates = {item["blind_id"]: item["output"] for item in bundle["candidates"]}
        for blind_id, output in sorted(candidates.items()):
            codes = [
                f"{code['code_id']} {code['label']}: {code['definition']}"
                for code in output.get("codes", [])
            ]
            themes = [
                f"{theme['theme_id']} {theme['name']}: {theme['claim']}"
                for theme in output.get("themes", [])
            ]
            negative_cases = [
                f"{item['excerpt_id']}: {item['implication']}"
                for item in output.get("negative_cases", [])
            ]
            memo = output.get("reflexive_memo", {})
            output_rows.append(
                {
                    "packet_id": packet_id,
                    "run_index": run_index,
                    "blind_id": blind_id,
                    "analysis_summary": output.get("analysis_summary", ""),
                    "codes": join_lines(codes),
                    "themes": join_lines(themes),
                    "negative_cases": join_lines(negative_cases),
                    "uncertainties": join_lines(memo.get("uncertainties", [])),
                    "alternative_interpretations": join_lines(
                        memo.get("alternative_interpretations", [])
                    ),
                    "limitations": join_lines(memo.get("limitations", [])),
                    "bundle_file": bundle_path.name,
                }
            )
        for pair_index, (left, right) in enumerate(
            itertools.combinations(sorted(candidates), 2), start=1
        ):
            digest = hashlib.sha256(
                f"{SIDE_SEED}|{packet_id}|{run_index}|{left}|{right}".encode("utf-8")
            ).hexdigest()
            candidate_a, candidate_b = (right, left) if int(digest[-1], 16) % 2 else (left, right)
            review_rows.append(
                {
                    "reviewer_id": "",
                    "packet_id": packet_id,
                    "run_index": run_index,
                    "pair_id": f"{packet_id}_r{run_index}_p{pair_index:02d}",
                    "candidate_a": candidate_a,
                    "candidate_b": candidate_b,
                    "pairwise_choice": "",
                    "a_evidential_support": "",
                    "b_evidential_support": "",
                    "a_voice_context": "",
                    "b_voice_context": "",
                    "a_negative_case": "",
                    "b_negative_case": "",
                    "a_contract_fit": "",
                    "b_contract_fit": "",
                    "a_codebook_usability": "",
                    "b_codebook_usability": "",
                    "a_disposition": "",
                    "b_disposition": "",
                    "serious_error_flags": "",
                    "confidence": "",
                    "requested_expertise": "",
                    "rationale": "",
                    "review_status": "not_started"
                }
            )

    outputs = [
        (run_dir / "source_packets_flat.csv", source_rows),
        (run_dir / "blind_outputs_flat.csv", output_rows),
        (run_dir / "human_pairwise_review_template.csv", review_rows),
    ]
    for path, rows in outputs:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    print(
        json.dumps(
            {
                "source_rows": len(source_rows),
                "blind_output_rows": len(output_rows),
                "pairwise_review_rows": len(review_rows),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
