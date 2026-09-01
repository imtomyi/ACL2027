# Qwen3 Generalist private-local pilot contract v1

This lane implements the user's explicit scope: a private, single-user, local
experiment with no API and no publication. It does not claim external
authorization. Its outputs are not manuscript evidence and must not be copied
to the manuscript, a submission, or a public release.

## Frozen candidate pool

The input is the locally deidentified Dreaddit official test split, represented
locally as `in_domain_audit`. Selection is deterministic and uses only records
marked eligible for packet sampling. Before ranking, the runner excludes every
post commitment in the frozen snapshot of earlier Dreaddit audit selections.
It also checks that the snapshot still covers every earlier audit-selection
file present at execution time.

The complete candidate pool contains 15 disjoint base-packet components. Each
base packet contains six distinct posts, and no post occurs in two packets.
Three packets are assigned prospectively to each of the five flaw families in
three rounds of the frozen family order. The runner processes all 15 slots.
It does not stop when a family first passes, replace a rejected slot, or move a
packet between families.

Local `llama3.1:8b` creates each bounded base and its controlled variant. Local
`gemma3:4b` receives only the base and variant, without the intended family or
truth label, and independently applies the frozen construction-verification
schema. Only candidates satisfying the deterministic structural checks and
the complete frozen Gemma acceptance rule enter the sealed bank. Generated
text is never treated as a source passage. Every evidence passage and quoted
passage is copied exactly from its selected local Dreaddit record.

## Review gate and execution

Qwen review begins only after all 15 slots have been processed and the accepted
bank has been sealed. The bank must contain at least five accepted items and
must represent all five flaw families. Otherwise the run stops without a Qwen
review or score.

The run is checkpointed and may be continued only with its explicit frozen
run ID. On resume, the runner verifies the freeze, runner, service identity,
selection, request, response, and completed-call hashes before reusing them.
It never reissues a completed or terminal call. If execution stopped after a
request was saved but before a response was saved, that call is closed as a
terminal interruption rather than silently reissued. If a response was saved,
the runner validates it and completes the missing local checkpoint without a
new model call. Thus resume continues the same execution and does not change a
candidate, prompt, model, seed, or denominator.

Local `qwen3:8b` receives the same Generalist prompt and shared rating guide for
every accepted item. Each item is reviewed in three independent, stateless
calls with seeds `2027082601`, `2027082602`, and `2027082603`. Repetition 1 is
primary. No call is retried, and no item is replaced after the bank seal. A
valid primary rating is a hit only when `cannot_judge` is empty and the exact
frozen serious-error flag for that item's flaw family is present. Every failed,
invalid, incomplete, truncated, or context-invalid call is a miss.

The output reports TP, N, recall, and a percentile 95% component-bootstrap
interval from 10,000 resamples with seed `20270826`. The bootstrap unit is the
accepted base-packet/post component. The result label is `automated-target
detection among Gemma-screened Llama variants`.

## Privacy and transport

Only numeric-loopback Ollama at `127.0.0.1:11434` is permitted. Proxies,
redirects, DNS names, tools, streaming, silent truncation, context shifting,
and automatic retries are disabled. The three model identities and local
manifest hashes are distinct and frozen.

All requests, responses, selected packets, candidate artifacts, truth records,
and observations remain below
`Storage/rq2_qwen3_generalist_private_pilot/`. Directories use mode `0700` and
files use mode `0600`. Standard output and standard error contain only finite,
source-free status fields. The aggregate score contains no source passage.

This private pilot is exploratory and locally model-screened. Gemma screening
is not human ground truth. The result has `manuscript_eligible: false`,
`publication_or_release_eligible: false`, and
`external_authorization_claimed: false`.
