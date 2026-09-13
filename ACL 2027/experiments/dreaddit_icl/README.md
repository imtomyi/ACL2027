# Dreaddit ICL local pilot and comparison design

This is a personal local stress-classification diagnostic using Qwen3-8B
Q4_K_M on Ollama. It does not reproduce the ACE paper's finance results.
The executed pilot uses only official-train development records, with one
passage per post and disjoint posts for demonstrations and pilot queries.
Existing duplicate eligibility and exact-date cluster exclusions are honored.
No text is sent to a remote inference service or included in result logs.

## Four proposed conditions

| Condition | Initial demonstrations | Update after predicting an evaluation item |
| --- | --- | --- |
| Offline, GT yes | Fixed texts with released training labels | None |
| Offline, GT no | Same texts with frozen zero-shot Qwen pseudo-labels | None |
| Online, GT yes | Same initial texts with released training labels | Append the item with its released label after scoring |
| Online, GT no | Same initial texts with the same frozen pseudo-labels | Append the item with its own predicted label after scoring |

GT-no variants are **pseudo-label ICL**, not standard supervised ICL. They do
not receive released labels in model inputs or select examples by label or
label-based validation. Ground truth remains available to a separate scorer.
This distinction concerns experimental access to labels, not model pretraining.
Dataset stress annotations are the benchmark reference, not clinical diagnoses.

Freeze example text IDs, ordering, prompt, token budget, model digest,
temperature, output format, test order, and eviction rule before test execution.
Use chronological append and oldest-first eviction in both online conditions.
Always predict before revealing the current label. Never retrospectively
rescore earlier predictions after an update. Do not evaluate the same item twice
within an online stream. Keep all conditions in separate fresh contexts.

Online variants require a time trajectory: report prequential accuracy and
macro-F1, cumulative curves, invalid outputs, input/output tokens, and wall time.
Report pseudo-label preparation separately from evaluation; the same preparation
can be reused by both GT-no conditions. Also report a zero-shot reference so that
any benefit or harm from demonstrations is measurable. Random-order robustness
runs should use predefined seeds, not a seed selected for high test accuracy.

## Timing pilot

`run_local.py` currently implements **Offline, GT yes only**. It samples 20
development queries with seed 42 and fills the 32,768-token budget with a fixed
prefix of training demonstrations, reserving the largest development query and
output/template headroom. Native thinking is disabled and the output is one
digit, with an eight-token cap. No parameter training is performed.

The first request includes cold loading and full demonstration prefill. Later
requests can reuse the prefix cache. Extrapolations assume this same cache
behavior and do not estimate online updates, where the prefix changes.
An estimate for 715 items is a scale reference for the source test size, not
confirmation that all 715 meet this workspace's eligibility rules.

Run from `/Users/tom/Documents/GitHub/ACL2027` using the existing Python
environment (only its installed tokenizer library is reused):

```sh
'ACL 2027/Storage/dreaddit_icl/runtime313/bin/python' \
  'ACL 2027/experiments/dreaddit_icl/run_local.py' \
  --samples 20 --output 'ACL 2027/Storage/dreaddit_icl/CHOOSE_NEW_RUN_NAME'
```

The local Ollama service must be running with `qwen3:8b` installed. The official
Qwen tokenizer must already be in the Hugging Face cache. Output directories are
created exclusively to prevent overwriting experiments. `config.json` records
source/model identities and sample IDs. `predictions.jsonl` checkpoints each
completed inference. `summary.json` is written only on successful completion.
The official test remains unused by this pilot.
