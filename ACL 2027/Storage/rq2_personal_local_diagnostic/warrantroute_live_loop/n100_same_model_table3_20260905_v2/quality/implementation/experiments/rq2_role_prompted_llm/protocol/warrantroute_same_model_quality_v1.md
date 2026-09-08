# WarrantRoute Same-Model n100 and Review-Quality Protocol

Date: 2026-09-05. Authorized scope: a local, private working comparison requested
by the user. This protocol supplements the WarrantRoute Loop Experiment Guide.
It is not authorization to populate manuscript sources or a manuscript PDF.

## Model Comparison

The question is how the installed Qwen3 8B, Llama 3.1 8B and Gemma 3 4B models
perform when each supplies every agent of the same looping system. The three
conditions are `qwen_only`, `llama_only`, and `gemma_only`. Proposer, Evidence
Scout, Methods Challenger, Domain Challenger and Reviser are separate role
calls using one identical model digest within a condition. These are not the
earlier cyclic mixed-family `*_led` conditions. Gemma is smaller than the other
models, so this does not isolate family independently of model size.

The explicit `same_model_ablation` assignment policy permits this comparison.
The original controller's default still requires cross-family auditors and a
different-family reviser. Same-model role separation is not independence of
model errors. Reviser self-resolution is still prohibited: the original issue
owner must verify a proposed resolution in a separate call.

All three conditions use byte-identical role instructions and shared rater
guide, the same routing policy, the same seed schedule, context and output
caps, and the same packet IDs. Only agent model assignment changes. Existing
Qwen-specific `think=false` remains because that model has a thinking mode.
Two initial assessments are isolated. Routing, escalation, at most two revision
rounds, and the 12-call limit are unchanged. Playbook updates remain disabled.

The sample is 100 fixed packets per corpus: Dreaddit, GoEmotions, CaChe and
ParlaMint-GB. Every packet has one trajectory per model, with repetition seed
20260905. There are 400 distinct packets and 1,200 trajectories, not 1,200
independent source samples. No replacement samples or best-of reruns are used.
The first packet in each of the 12 dataset-model cells is an included technical
canary. Remaining work runs in frozen blocks, serially. Timing includes loading
and is descriptive, not a controlled hardware-performance benchmark.
Each included canary's review-quality request is also executed before moving
past the canary stage. Those exact saved judgments are reused at finalization,
not repeated votes. Five technically exhausted canary judgments pause the run.

## Secondary Review-Quality Measurement

Credibility and Conformability assess the original-claim review bundle, matching
the construct used for the historical baseline columns. They do not assess the
rewritten claim or prove that the loop repaired it. The whole loop runs, but
only `stage=initial` audit reports for the locked original claim enter this
measurement. Rechecks and revisions are excluded to avoid pairing an original
claim with a review of a different claim.

Use all required initial reports, never the best report or a majority vote.
Project each report to `serious_error_flags`, `rationale`, `disposition`, and
`cannot_judge`, exactly the historical baseline review fields. Rich issue
objects, numeric self-ratings and route scores are not separately judged. This
is explicitly a rating-projection quality measure, not an exhaustive assessment
of all structured loop outputs. Missing required initial reports are recorded
as unresolved, not evaluated as a complete bundle.

The judge receives the original claim, source context, and anonymous R1 through
R4 reviews, with source/provenance IDs consistently aliased. The source context
is sanitized with the existing baseline helper. No model, method, corpus,
target-flaw, route, revision outcome, numeric rating or builder annotation is
provided. Role order is deterministically shuffled with seed 20260904. Bundle
size and style can still reveal the condition.

Freeze the historical four-condition Credibility rubric and four-condition
Conformability rubric before generation. Credibility requires a specific,
faithful, adequate and defensible assessment without a material unwarranted
accusation or factual contradiction. Conformability requires each material
allegation to have a stated, traceable basis that actually supports its meaning
and scope. All requirements of a dimension must pass. At least one failed
requirement means false. A matching intended label is neither necessary nor
sufficient. Genuine essential-context inability yields null, not false.

The secondary judge is the fixed local `qwen3:8b` digest also used for the
baseline audit. It is separate from the loop and receives no loop scores.
Qwen also participates in one evaluated condition, so self-family preference
remains a limitation. These are LLM-assessed rubric pass rates, not expert truth.

The prompt is the saved baseline prompt with R4 support and one frozen formatting
suffix requiring at most 45 words per rationale and only CLAIM/R identifiers.
The substantive 60-word validation ceiling and rubric do not change. Requests
use the same JSON schema for every condition, temperature 0, top_p 1, context
8192, output cap 384, timeout 240 seconds, and explicit Qwen thinking disabled.
Schema-constrained generation, R4 support and explicit thinking control differ
from the historical primary baseline audit and are disclosed, not claimed to
be a byte-identical measurement replication. The requested three-model loop
comparison itself uses an identical measurement procedure across conditions.

Each assessable trajectory gets one logical judgment yielding both dimensions,
not repeated votes. At most three identical technical attempts are allowed for
transport, truncated or schema-invalid judge responses. Keep the first valid
response, including false or null. Never retry a valid unfavorable response.
An interrupted attempt consumes an attempt and remains in the journal. At most
1,200 logical judge evaluations, 2,400 binary decisions, and 3,600 HTTP attempts
are planned. Missing reviews do not consume a judge request.

## Denominators and Failure Handling

Each of the 12 table rows has 100 planned packets. For each dimension separately,
true + false + unresolved must equal 100. Report `100 * true / 100` only when all
100 decisions are binary. Otherwise retain N/A and report all three counts in
the companion summary. Do not turn missing model outputs into false, silently
drop difficult packets, or divide only by valid cases.

Completed loop trajectories are immutable and skipped on resume. Original
detection flags are retained if a later revision fails. Failed or in-flight
loop calls are not repeated under another identity. Human escalation is a
terminal state, not necessarily a technical failure or a successful repair.
Individual failures remain in the denominator. The supervisor pauses for
contract/hash changes, service unavailability, at least three technical loop
failures in the 12 included canaries, or five consecutive unsuccessful judge
units. It does not change prompts or thresholds to improve observed scores.

Source-connected bootstrap recall intervals are produced by the new scorer
(10,000 draws, seed 20270826), not the historical Wilson intervals. A single
source component has no estimable cluster interval. Recall is based on the
original intended-flaw flags, never accepted status or revised text.

## Records and Export

Freeze config, implementation, packet snapshots, judge runtime, prompt, schema,
this protocol, and original table files before the first main call. Bind every
quality unit to the actual trajectory result hash. Preserve raw responses,
attempts, usage, errors and snapshots. Execution is local Ollama only, with no
Portkey or paid API requests. The existing USD 100 external-spend ceiling is
not permission to use an external service for these packets.

After all trajectories and planned judgments terminate, export standalone
comparison and quality summaries. Replace only the 12 WarrantRoute rows of the
Storage Table 3, including detection and quality columns together. Preserve
the 36 baseline rows and archive the original CSV/MD. Refuse an unrecognized
concurrent table edit. Use a resumable export journal and verify all 48 rows.
Unresolved quality cells stay N/A. Never attach new-loop quality numbers to old
WarrantGate detection values. The new manifest is distinct from historical
finalization manifests and must not claim those old records describe this run.

Select ten packet IDs per corpus deterministically, independent of outcomes,
and export their 120 anonymous three-model bundles for later human audit.
Human judgments are pending, not fabricated or inferred from the LLM judge.
An independent qualified panel, including a human-audited subset, is required
before treating these measurements as validated semantic evidence.

The packets were previously exposed and their controlled flaw-template claim
fields can disclose intended flaws to the agents. Judge sanitization does not
undo that exposure. Therefore all outputs remain private working diagnostics.
`semantic_repair_quality` stays null. No claims of unbiased held-out accuracy,
clinical expertise, repair improvement, or manuscript eligibility follow.
