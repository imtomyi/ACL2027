# Synthetic qualitative-coding model qualification

## Decision

Use **GPT-5.6 Sol as the provisional remediation candidate**, not as the frozen paper model. It had the strongest automatic evidence-gate result (10 of 12 strict run-level passes), but no candidate passed every strict gate. GPT-5.4 and GPT-5.5 received slightly higher supplementary same-vendor judge scores, so the final model must be chosen through blinded expert review on authorized Dreaddit development packets.

## Scope

This run is an engineering qualification on 48 entirely fictional excerpts shaped like four corpus types. It is **not a result for the real Dreaddit, AGYW, KODIS, or CANDOR datasets**.

- 5 recent model variants: GPT-5.6 Sol, GPT-5.6 Terra, GPT-5.6 Luna, GPT-5.5, and GPT-5.4
- 4 synthetic corpus proxies
- 3 independent repetitions per model and packet
- 60 generation records; all 60 passed the JSON schema
- 36 blinded judge records covering 180 candidate scores
- No real text was sent to a model

## Objective results

| Model | Strict passes | Exact quotes | Attribution | Multi-source themes | Cited-source coverage | Supplementary judge overall |
|---|---:|---:|---:|---:|---:|---:|
| GPT-5.6 Sol | **10/12 (83.3%)** | 100.0% | 100.0% | 91.7% | 100.0% | 4.56/5 |
| GPT-5.4 | 9/12 (75.0%) | 99.8% | 100.0% | **92.4%** | 99.3% | **4.67/5** |
| GPT-5.5 | 9/12 (75.0%) | 100.0% | 100.0% | 91.7% | 98.6% | 4.64/5 |
| GPT-5.6 Luna | 8/12 (66.7%) | 100.0% | 97.6% | 87.5% | 89.9% | 3.39/5 |
| GPT-5.6 Terra | 5/12 (41.7%) | 100.0% | 100.0% | 79.2% | 94.1% | 3.86/5 |

The recurring weakness was the KODIS-shaped proxy: some runs promoted single-source patterns to themes. The qualification therefore does not justify unattended use on that corpus type.

## Interpretation

The selection rule is lexicographic: governance and evidence validity first, then qualified-human non-inferiority, then total cost including human verification, with stability only as a tie-break. Judge scores are supporting evidence rather than a substitute for human review because all three judges were OpenAI-family models.

Run-time tokens, latency, and API cost are unavailable for this qualification because the candidates were executed as isolated Codex model tasks after direct OpenAI API inference returned `credit_balance_exhausted`. This limitation must be resolved in the authorized development tournament.

## Real-dataset status

- **Dreaddit:** not run. Institutional and platform authorization must be documented first. Selection may use only the approved development/train portion.
- **AGYW:** not run. It remains held out and cannot influence model, prompt, threshold, or packet selection; project-specific secondary-use/model-processing clearance is still required.
- **KODIS:** real distribution is absent; the repository contains only a three-record synthetic demo with zero eligible records.
- **CANDOR:** real distribution is absent; the repository contains only a nine-record synthetic demo with zero eligible records.

## Required next stage

1. Resolve and record the corpus-specific governance gates.
2. Run a blinded expert tournament on eligible Dreaddit development packets using the frozen prompt, schema, packet rules, repeat policy, and repair policy in this experiment.
3. Calibrate cost and verification time from that pilot.
4. Freeze the primary model and backup before any Dreaddit test or AGYW inference.
5. Report each corpus separately; do not label the synthetic proxies as corpus baselines.

## Artifact map

- `qualitative_coding_model_comparison.xlsx`: reviewer-facing workbook with summary, corpus-proxy detail, validation evidence, stability, blinded judge scores, and a blank human-review instrument
- `selection.json`: machine-readable qualification decision
- `model_objective_summary.csv`: model-level automatic metrics
- `model_dataset_summary.csv`: model-by-synthetic-proxy metrics
- `objective_metrics_long.csv`: run-level audit metrics
- `validation_issues.csv`: exact gate failures and warnings
- `judge_model_summary.csv` and `judge_scores_long.csv`: supplementary blinded-judge results
- `dataset_status.csv`: authoritative real-data status and blockers
- `raw/`, `blinded/`, and `judges/`: immutable generation, blinded-review, and judge records
- `run_inventory.csv`: hashes and parse status for every generation file
- `PAPER_METRIC_RESULTS.md`: paper-aligned synthetic measurement results and
  interpretation
- `paper_metric_model_summary.csv`: all four measures by model with packet-by-run
  bootstrap intervals
- `paper_metric_model_dataset_summary.csv`: all four measures by model and
  synthetic corpus proxy
- `paper_metric_ratings_long.csv`, `paper_metric_matches_long.csv`, and
  `paper_metric_panel_matches.csv`: rating, conceptual-match, and panel audit data
- `paper_metric_validation_summary.json`: record counts and validation status
