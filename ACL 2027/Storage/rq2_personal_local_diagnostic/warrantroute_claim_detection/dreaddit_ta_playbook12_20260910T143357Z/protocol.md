# Twelve-Point TA Flaw Review and Playbook Continuation

Protocol: `ta-artifact-playbook-smoke-v1`. Local, unscored development only.
User authorization: continue the existing twelve-point codes/themes test through
flaw review and Playbook learning. This does not authorize manuscript scoring,
paid API calls, new data selection or resuming the old paragraph experiment.

## Fixed Inputs and Workload

Use all three locked TA artifacts from
`dreaddit_ta_generation12_20260910T141310Z`: twelve original, previously exposed
Dreaddit development paragraphs in their original three four-record packets.
Preserve both good and flawed generated content byte-for-byte. Verify the source
run, raw outputs and artifact hashes; do not regenerate or repair any artifact.
Three fixed-order epochs review those same artifacts, giving nine exposures,
not nine new independent samples. No baseline or held-out evaluation is included.

Use the same pinned local Gemma 3 4B installation for all three remaining roles:

1. Flaw Detector: one combined diagnosis/integration/check call per exposure.
2. Reflector/Curator: one update attempt after each valid locked review.
3. Rule Auditor: at most one call for the eligible candidate batch.

The TA Analyst's three construction calls have already completed in the source
run and are not repeated. This continuation uses at most 27 additional local
calls, a 30-minute wall-clock budget and 180-second per-call timeouts. Freeze
temperature 0, inherited seed, 49,152 context and 4,096 output tokens. The larger
context accommodates artifact, original sources, locked review and memory without
silently truncating them. No paid calls or model downloads are allowed.

## Actual Target and Evidence

The reviewer receives the TA artifact as structured codes, themes, source notes
and links, alongside the original source paragraphs. It does not receive a
flattened replacement claim. The existing reducer uses a serialized artifact
only as an internal case-support fingerprint, never as the detector's target.
Each allegation names its canonical flaw type, a located artifact target,
original evidence or a whole-packet missing warrant, mechanism and consequence.
Maximum four allegations per bounded smoke response; unresolved coverage limits
must be disclosed. Allegation counts are not accuracy or recall.

Artifact anchors name collection, unit ID, field and exact quote; original-source
anchors name excerpt ID and quote. A quotation fabricated inside the TA artifact
can be located as an artifact assertion without being valid source evidence.
Different defensible interpretations, codes-only outputs, limited single-source
claims or whitespace-only quote changes are not automatically material flaws.
Mechanical findings remain visible; they are not a gold inventory.

## Query-Level Learning

Begin a separately frozen empty-learning state with the two generic original
warrant/context seed rules, now scoped to TA by the new role prompts. Do not
import the old paragraph-learned rules, manual eight-rule draft or assistant's
post-run inspection notes. This reuses generic seed text, not learned findings.

After each valid prediction is locked, consider four explicitly named learning
opportunities: evidence-to-code checks, false-allegation prevention, flaw-type
distinction, and theme scope/counterevidence. Return at most two incremental
add/refine/reinforce proposals. Both reflections and candidates need located TA
and source evidence. General rule fields exclude participant facts, quotations,
code/theme IDs and case conclusions. No successful addition quota is imposed.

Use the existing deterministic memory admission, duplicate handling, seed
immutability, memory budget and six-criterion semantic audit. Additional checks
validate TA target anchors in proposals and audit decisions. Each admitted rule
has a stable `shr-xxxxx` TXT ID; candidate content has a separate `cand-` ID.
Seeds and learned rules stay distinguishable. Every query publishes a snapshot,
including rejected/no-change outcomes. The next detector receives the actual TXT
projection of all active rules, with hashes and rule checks stored in its locked
record. Repetition, reinforcement and prompt delivery are not new rules or proof
of improved detection. The same model's audit remains fallible.

Across epochs, give the learner only the latest earlier same-artifact candidate
procedures and recorded outcomes from this run. No future items, independent
scores, answer keys, baseline outputs or assistant-written inspection findings
enter the learning payload. No evaluation Judge is called.

## Reliability and Outputs

Acquire shared and per-run inference locks; never duplicate workers. Start and
clean up only an owned local Ollama server. Freeze source, code, prompts and
schedule before inference. Persist requests, responses, locked predictions,
candidate proposals, audits, per-edit receipts and hash-linked state transitions.
Missing responses stop for inspection, never automatic resending. Preserve
invalid/unfavorable outputs. No technical repair may silently modify a frozen run.

Keep `playbook_initial.txt`, `playbook_after.txt`, `changes.diff`, current TXT/JSON
and per-query history. Export query progress and candidate registers separately.
Source-free tests must cover separate anchor namespaces, invalid target/source
withholding, audit rejection, stable IDs, actual prompt delivery, no-change,
schema compatibility, memory leakage and no retry of uncertain calls. The first
live review/update cycle remains part of the fixed schedule, even if it fails.

There is no adjudicated complete flaw inventory, so detection accuracy, recall,
precision and detection-gated Credibility/Conformability stay unassessed. This
test cannot establish manuscript-qualified results or performance improvement.
The original TA generation reports and paused paragraph Playbooks are unchanged.
