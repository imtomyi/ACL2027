#!/usr/bin/env python3
"""Prospective, text-free sample-size and review-time scenario simulation.

This is a planning tool, not confirmatory analysis. It uses no corpus records.
Replace its assumptions with pilot estimates before freezing the real study.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np
from scipy.special import expit, logit
from scipy.stats import binomtest


FAMILIES = (
    "unsupported_evidence",
    "source_concentration",
    "counterevidence_loss",
    "contextual_flattening",
    "unsupported_abstraction",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--simulations", type=int, default=3000)
    parser.add_argument("--seed", type=int, default=20260825)
    parser.add_argument(
        "--items-per-family", default="12,24,40,60,80,100,120,150",
        help="Comma-separated controlled-item counts for each failure family.",
    )
    parser.add_argument("--ratings-per-role-item", type=int, default=3)
    parser.add_argument("--baseline-detection", type=float, default=0.55)
    parser.add_argument("--aligned-role-gain", type=float, default=0.15)
    parser.add_argument("--item-logit-sd", type=float, default=0.85)
    parser.add_argument("--rater-logit-sd", type=float, default=0.45)
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument("--median-researcher-minutes", type=float, default=3.0)
    parser.add_argument("--median-expert-minutes", type=float, default=5.0)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def validate(args: argparse.Namespace, counts: list[int]) -> None:
    if args.simulations < 100:
        raise ValueError("--simulations must be at least 100")
    if not counts or any(value < 2 for value in counts):
        raise ValueError("all --items-per-family values must be at least 2")
    if args.ratings_per_role_item < 1:
        raise ValueError("--ratings-per-role-item must be positive")
    for name in ("baseline_detection", "aligned_role_gain", "alpha"):
        value = getattr(args, name)
        if not 0 < value < 1:
            raise ValueError(f"--{name.replace('_', '-')} must be between 0 and 1")
    if args.baseline_detection + args.aligned_role_gain >= 1:
        raise ValueError("baseline detection plus aligned role gain must be below 1")


def majority_detection(
    rng: np.random.Generator,
    item_effect: np.ndarray,
    probability: float,
    ratings: int,
    rater_sd: float,
) -> np.ndarray:
    rater_effect = rng.normal(0.0, rater_sd, size=(len(item_effect), ratings))
    probabilities = expit(logit(probability) + item_effect[:, None] + rater_effect)
    votes = rng.binomial(1, probabilities)
    # With an even number of ratings, ties conservatively count as not detected.
    return votes.sum(axis=1) > ratings / 2


def paired_p_value(reference: np.ndarray, aligned: np.ndarray) -> float:
    aligned_only = int(np.sum((~reference) & aligned))
    reference_only = int(np.sum(reference & (~aligned)))
    discordant = aligned_only + reference_only
    if discordant == 0:
        return 1.0
    return float(binomtest(aligned_only, discordant, 0.5, alternative="two-sided").pvalue)


def estimate_power(args: argparse.Namespace, n_items: int, rng: np.random.Generator) -> float:
    significant = 0
    for _ in range(args.simulations):
        item_effect = rng.normal(0.0, args.item_logit_sd, size=n_items)
        researcher = majority_detection(
            rng, item_effect, args.baseline_detection,
            args.ratings_per_role_item, args.rater_logit_sd,
        )
        aligned = majority_detection(
            rng, item_effect, args.baseline_detection + args.aligned_role_gain,
            args.ratings_per_role_item, args.rater_logit_sd,
        )
        significant += paired_p_value(researcher, aligned) < args.alpha
    return significant / args.simulations


def design_row(args: argparse.Namespace, n_items: int, power: float) -> dict[str, object]:
    controlled_items = n_items * len(FAMILIES)
    natural_items = controlled_items
    total_items = controlled_items + natural_items
    ratings = total_items * 3 * args.ratings_per_role_item
    researcher_minutes = total_items * args.ratings_per_role_item * args.median_researcher_minutes
    expert_minutes = total_items * 2 * args.ratings_per_role_item * args.median_expert_minutes
    return {
        "controlled_items_per_failure_family": n_items,
        "controlled_items": controlled_items,
        "matched_natural_items": natural_items,
        "total_items": total_items,
        "ratings_per_role_per_item": args.ratings_per_role_item,
        "total_independent_ratings": ratings,
        "estimated_power_aligned_role_gain": round(power, 4),
        "researcher_hours": round(researcher_minutes / 60, 1),
        "expert_hours": round(expert_minutes / 60, 1),
        "all_human_review_hours": round((researcher_minutes + expert_minutes) / 60, 1),
    }


def main() -> None:
    args = parse_args()
    counts = [int(value) for value in args.items_per_family.split(",")]
    validate(args, counts)
    rng = np.random.default_rng(args.seed)
    rows = [design_row(args, n, estimate_power(args, n, rng)) for n in counts]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    recommended = next(
        (row for row in rows if float(row["estimated_power_aligned_role_gain"]) >= 0.80),
        None,
    )
    print(f"wrote {args.output}")
    if recommended:
        print(
            "first scenario at or above 80% power: "
            f"{recommended['controlled_items_per_failure_family']} controlled items/family, "
            f"{recommended['total_items']} total items"
        )
    else:
        print("no evaluated scenario reached 80% power")


if __name__ == "__main__":
    main()
