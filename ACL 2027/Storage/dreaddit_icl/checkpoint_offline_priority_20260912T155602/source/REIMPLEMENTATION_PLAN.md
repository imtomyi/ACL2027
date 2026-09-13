# Dreaddit method comparison: implementation preparation

Prepared on 2026-09-12. No comparison run was launched. This document is an
implementation specification, not a claim that the ten runners are complete.
The earlier ICL pilot remains interrupted without completed predictions.

## Scope and source baseline

Implement the ten conditions in ACE Table 2 on Dreaddit with local Qwen3-8B
Q4_K_M. This is a method-transfer experiment, not numerical reproduction of
DeepSeek-V3.1 on FiNER/Formula. Preserve official optimizer mechanisms instead
of replacing them with hand-written simplified loops.

- Base: the same task definition and output contract, without demonstrations.
- ICL: fixed training demonstrations packed to the available context budget.
- MIPROv2: official DSPy instruction/example search with `auto="heavy"`.
- GEPA: official DSPy reflective Pareto search with `auto="heavy"`.
- DC-CU: official cumulative generator/curator workflow, separate GT policies.
- ACE: official generation/reflection/curation and grow/refine components,
  separate offline/online and GT policies.

Source manifests and selected source snapshots are in
`../../Storage/dreaddit_icl/comparison_preparation_20260912/`.
DSPy 3.0.3 is a pinned engineering baseline, not a proven original paper version.
The DC repository snapshot is pinned to a resolved current commit; the paper's
historical DC commit is not known. Existing ACE source is pinned separately.
Before implementation, resolve transitive dependency versions in a dedicated
environment, clone full source at these commits, and record dependency hashes.
Do not install into or modify other experiments' environments.

## Prepared data and protocol

Use all 2,804 eligible official-train passages. With seed 42, assign 20% of
post groups to validation, yielding 2,249 training and 555 validation passages.
The official test has 712 eligible passages after existing exclusions. Keep
every passage in its assigned post group; do not deduplicate to one per post.
Prepared manifests contain IDs only, no text or label contents. No inference
or test-label-driven optimization was performed during preparation.

Freeze identical splits, test order, Qwen digest, task definition and output
parser for all conditions. Score accuracy as primary, macro-F1 as secondary,
and report invalid outputs separately. Run one condition at a time locally.
Set native thinking off, context to 32,768, and per-call output cap to 4,096.
Start memory methods from an empty playbook. Use a declared 16K-token soft
playbook cap, token-aware pruning, and fail before any silent context truncation.
These memory limits are local adaptations, not paper-equivalent settings.

## Required adapters and checks before execution

1. **Local transport:** native Ollama request adapter with explicit thinking-off,
   prompt/output accounting, timeout, abort, model identity checks, and resume.
   Disable executable Python tool calls for this text-classification task.
2. **Dataset adapter:** lazy local text access from frozen IDs. Separate released
   label access from query inputs. Never place the current test label in a prompt.
3. **Base/ICL:** shared output contract and scorer; verify context packing using
   the actual tokenizer/template; preserve a stable demonstration prefix.
4. **MIPROv2:** a single DSPy predictor, training demonstrations, and explicit
   held-out validation metric. Preserve bootstrap/proposal/search stages.
5. **GEPA:** five-argument feedback callback for pinned DSPy, explicit reflection
   model equal to Qwen, trace capture, and full candidate-selection metadata.
6. **DC-CU:** preserve cumulative whole-cheatsheet rewriting, adaptation logs,
   and pre-update scoring. Add a documented supervised feedback adapter for GT O.
7. **ACE:** reuse official components through an adapter, including bullet usage,
   curator operations and deduplication. Preserve post-curator diagnostics and
   account for their cost. Use the scored first prediction for online accuracy.
8. **Checkpoints:** isolate each condition. Record source/config hashes, RNG state,
   cursor, memory before/after, raw local outputs and role-level token counts.
   Commit a stream step atomically to prevent double updates on resume.
9. **Verification:** test label noninterference, train/validation post separation,
   predict-before-update, deterministic resume, context overflow, invalid output
   accounting, frozen offline memory, and preservation of optimizer budgets.
   These tests remain to be implemented with the runners.

## Critical release differences

The pinned ACE financial `_train_single_sample` uses target correctness even
with `no_ground_truth=True`. It sends correctness feedback and uses it to
choose reflection branches and terminate retries. In binary classification,
correct/incorrect feedback plus a prediction reveals the label.

The primary GT-X condition must therefore remove correctness feedback AND
label-dependent control flow. Use a fixed single reflection, curator update,
and diagnostic generation, never validation-selected checkpoints. Keep labels
in a separate reporting scorer. If a literal released-code variant is needed,
name it `answer_hidden_correctness_feedback`, not `strict_no_gt`, and report it
separately from the ten-condition matrix.

The released finance online code evaluates a window (default 100) before
training on that window. The paper describes sample-wise prediction followed
by update. Use window 1 for the primary protocol and record the deviation from
the release default. Keep the independent first prediction and include any
duplicate training/diagnostic generations in timing rather than hiding them.

For GT O, the released ACE step uses 4 main LLM calls when initially correct,
or `3 + 2*r` calls when reflection runs for `r` rounds (up to 13 for r=5).
Deduplication can add work beyond these counts. Maximum five epochs are a
budget scenario, not a claim that every original paper row always used five.

## Reproducible timing model

`prepare_comparison.py` downloads source snapshots and produces `protocol.json`,
`splits.json`, `sources.json`, and `time_estimates.json` without model inference.
It extracts only GEPA's budget calculation from the pinned source: heavy with
one predictor and validation size 555 gives 4,920 metric calls, excluding
reflection calls and final test. MIPRO uses a planning allowance of seven full
validation sweeps, 27 minibatches of 35, and 90 bootstrap evaluations; cache
hits and search behavior change actual calls. GEPA's assumed 180 reflection
calls is a scenario allowance, not an official bound.

All timing inputs below are assumptions, not measured Mac throughput:

| Unit | Fast | Middle | Slow |
| --- | ---: | ---: | ---: |
| Ordinary prediction | 2 s | 8 s | 20 s |
| Cached long-prefix ICL prediction | 3 s | 12 s | 40 s |
| ACE complete adaptation step | 45 s | 120 s | 300 s |
| DC complete adaptation step | 30 s | 90 s | 240 s |
| Search reflection/proposal | 30 s | 90 s | 240 s |

The complete-step assumptions include generation, reflection, curation and
routine memory processing; if actual input growth or deduplication exceeds
them, estimates must increase. Model sampling a long response up to the cap,
swap, thermal throttling and cache eviction can exceed the slow scenario.

ACE Offline GT O includes validation every 100 training steps. That is
12,210 validation predictions per epoch, or 61,050 over five epochs, plus the
712 final predictions. Strict GT X uses the final checkpoint without labeled
validation and therefore excludes these validation calls. Both process all
2,249 training items each epoch. Online methods process all 712 test items.

| Full ten-condition suite | Fast | Middle | Slow |
| --- | ---: | ---: | ---: |
| ACE offline 1 epoch | 4.3 days | 12.5 days | 31.7 days |
| ACE offline 5 epochs | 14.8 days | 42.0 days | 105.4 days |

These are continuous wall-clock compute scenarios for one seed. They exclude
implementation time and do not constitute confidence intervals. Three seeds
approximately triple compute, unless a predefined reusable preparation stage
is explicitly shared. The model should be calibrated with separately authorized
short runs before allocating a fixed completion deadline.
