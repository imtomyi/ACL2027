# Proposal: corpus swap to GoEmotions + ParlaMint-GB

Status: **PROPOSAL / DRAFT. Not authorized. Nothing here is manuscript-eligible.**
Author contact: oodivgpt@gmail.com
Date: 2026-08-29 (America/Chicago)

## Why this folder exists

The five obtained corpora (Dreaddit, CaChe/AGYW, KODIS, CaSiNo, AMI) are each
gated for the same underlying reason: consent, platform terms, or residual
re-identification risk for LLM and rater processing are not cleared. This folder
proposes replacing the two corpora that currently have provisional manuscript
roles (Dreaddit for development, CaChe for held-out evaluation) with two
permissively licensed, redistributable public corpora, so the WarrantRoute study
can run and be published without the licensing and consent gate.

Verified license basis for the swap:

| Corpus | Role | License | Source of truth |
|---|---|---|---|
| GoEmotions | development + in-domain audit | Apache-2.0 (repo) / CC BY 4.0 (data) | Demszky et al. 2020; Google Research release |
| ParlaMint-GB | held-out cross-domain confirmatory | CC BY 4.0 | ParlaMint 3.0, CLARIN.SI DOI 11356/1486 |

Rejected during verification, recorded so the reasoning is not repeated:

- **SemEval-2014 ABSA**: no published license, "All Rights Reserved." This is the
  same missing-license condition that gates Dreaddit, so it would reintroduce the
  wall rather than remove it.
- **Yelp Open Dataset**: non-commercial, non-sublicensable, revocable, no data
  redistribution. Academic publication of results is carved out, but the data and
  derivatives cannot be redistributed, so it is not clean for release.

## Contents

- `PREREGISTRATION_DRAFT.md` — revised two-lane preregistration and protocol.
- `table1_data_statistics_skeleton.tex` — Table 1 (`Data Statistics`) skeleton
  and draft Section 2 prose for the two corpora. All measured statistics remain
  `\fillin` placeholders until a frozen authorized analysis produces them.
- `provenance_goemotions.md` — record-before-analysis stub.
- `provenance_parlamint_gb.md` — record-before-analysis stub.

## Hard constraints carried from workspace policy

1. No number in any file here may enter the manuscript until a frozen, authorized
   real-corpus analysis of these corpora produces it. Measured cells stay as
   explicit placeholders.
2. Adopting this swap is a design change, not a file substitution. It supersedes
   the Dreaddit + CaChe preregistration and requires a fresh, timestamped
   preregistration freeze before any packet or reviewer run.
3. The required-citation checker
   (`governance/scripts/check_required_manuscript_citations.py`) and `custom.bib`
   must be updated to match the swapped corpora as part of adoption. That change
   is intentionally not made here.
4. Each corpus must still complete the six-point record-before-analysis contract
   in `dataset/README.md` before processing. The stubs here start that record.
