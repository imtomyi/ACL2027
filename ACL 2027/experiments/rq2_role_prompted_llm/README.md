# RQ2 role-prompted LLM review

Status: **v2.3 is the current source-free transport health check, and v2.4 is
the current one-packet private real-data smoke diagnostic**. The v2.2
qualification remains an immutable predecessor. All outputs are private
engineering records, not manuscript evidence, and are not eligible for
publication, submission, redistribution, or release.

## Qwen3 WarrantRoute component

The source-free WarrantRoute successor binds the exact Qwen3 8B reviewer and
implements the four packet-level route contracts, strict source-free schemas,
and deterministic reduction rules. `none` selects the researcher output,
single-specialist routes select only that specialist, and `both` takes the
union of qualitative methods and domain flags. Failed selected roles contribute
no flags and never trigger fallback.

This version does not authenticate a learned policy, create an execution seal,
or accept inline Qwen ratings as evidence. Its public policy, sealing, and route-
application entrypoints fail closed. The in-memory applications in the tests
are software contract fixtures only. A future authorized successor must verify
a passed qualification seal, an immutable policy and implementation, a pre-
access seal, and a sealed text-free observation-projection bank.

The source-free checks are:

```sh
python3 experiments/rq2_role_prompted_llm/scripts/run_qwen3_warrantroute.py dry-run
python3 experiments/rq2_role_prompted_llm/scripts/run_qwen3_warrantroute.py source-free-test
```

Router training and real-data execution remain blocked. The active manuscript
has not yet frozen the feature encoding, training target, model formulation,
regularization, expert-time costs and budget, thresholds, route ties, failure
action, development minima, or baseline procedures. See
`protocol/qwen3_warrantroute_contract_v1.md`.

## Model-neutral WarrantRoute adapter

The routing layer also has a source-free model-neutral interface. Qwen3 8B is
the primary profile. Llama 3.1 8B and Gemma 3 4B are unbound adapter templates
that use the same reviewer-matrix schema, route names, role mapping, failure
handling, and deterministic reducer. The selected profile supplies model and
actor identities, which the source-free fixture validator checks exactly.
Reusing the reducer and schemas for another model does not establish reviewer
compatibility. Activation still requires a new model-specific freeze, transport
binding, and live source-free canary.

Statically validate each profile's frozen identity and adapter shape. These
commands do not contact a model or run its reviewer canary:

```sh
python3 experiments/rq2_role_prompted_llm/scripts/run_warrantroute_multimodel.py dry-run --reviewer-profile qwen3_8b
python3 experiments/rq2_role_prompted_llm/scripts/run_warrantroute_multimodel.py dry-run --reviewer-profile llama3_1_8b
python3 experiments/rq2_role_prompted_llm/scripts/run_warrantroute_multimodel.py dry-run --reviewer-profile gemma3_4b
```

The Llama and Gemma profiles do not authorize model calls. Each needs a new
model-specific reviewer freeze and three-role canary before activation. Gemma
also requires the guarded 16,384-token context path. Training and real-data
execution remain blocked for every profile. See
`protocol/warrantroute_multimodel_adapter_contract_v1.md`.

This adapter freeze is separate from inactive or historical model-profile
registries used by other components. Its Gemma context requirement controls any
future WarrantRoute reviewer activation.

## Qwen3 All roles component

The source-free All roles successor derives a descriptive full-review result
from the same sealed Qwen3 review matrix. It creates no fourth prompt, actor, or
model call. For the primary result, it unions the usable repetition 1 flags from
the researcher, qualitative methods, and domain roles and checks the exact
required flag once per eligible item. The stability sensitivity first retains
flags selected in at least two of three repetitions within each role and then
unions the three role-level sets.

The source-free configuration and nine-request plan check is:

```sh
python3 experiments/rq2_role_prompted_llm/scripts/run_qwen3_all_roles.py dry-run
```

The local identity check and optional inert role canaries are:

```sh
python3 experiments/rq2_role_prompted_llm/scripts/run_qwen3_all_roles.py preflight-service
python3 experiments/rq2_role_prompted_llm/scripts/run_qwen3_all_roles.py source-free-test
```

The reducer validates the complete three-role by three-repetition observation
grid, recomputes domain-separated fixture observation commitments, binds the
local matrix and exact model and prompt identities, checks denominator
arithmetic, re-derives results before sealing, and applies the fixed
source-cluster bootstrap rule. Any external study seal hashes in a fixture stay
explicitly unverified. Real execution remains blocked pending a passed
qualification gate and a new approved study freeze. See
`protocol/qwen3_all_roles_contract_v1.md`.

## Portable All roles model profiles

The additive v2 wrapper keeps the Qwen3 v1 freeze unchanged and makes the same
All roles method reusable with a closed set of local reviewer profiles. Qwen3
8B remains the primary and default profile. Llama 3.1 8B and Gemma 3 4B reuse
the same three prompts, three repetition seeds, rating schemas, failure rules,
reducer, and bootstrap. Profiles may change only exact model identity, actor
IDs, manifest bindings, and the message packaging required by the tracked
Ollama template. A failed selected profile never falls back to another model.

Build the nine-request source-free plans with:

```sh
python3 experiments/rq2_role_prompted_llm/scripts/run_all_roles_profiles_v2.py dry-run
python3 experiments/rq2_role_prompted_llm/scripts/run_all_roles_profiles_v2.py --model-profile llama3_1_8b dry-run
python3 experiments/rq2_role_prompted_llm/scripts/run_all_roles_profiles_v2.py --model-profile gemma3_4b dry-run
```

For the exact selected local model, use `preflight-service` to verify the
Ollama identity and `source-free-test` to run the inert three-role interface
canary. The tracked Qwen, Llama, and Gemma profiles passed that source-free
interface canary on August 28, 2026. Qwen remains the sole primary profile, and
Llama and Gemma remain compatibility profiles. A later study freeze must
separately authorize real execution. The tracked v2 `run` command is blocked
for every profile. Results and seals bind the selected profile ID and profile
hash, so unchanged artifacts cannot be replayed across models. These local
hashes do not authenticate a coherently relabeled artifact. Real execution
will require a verified upstream acquisition or review-matrix seal. See
`protocol/all_roles_profiles_v2_contract.md`.

## Qwen3 fixed-role component

The source-free fixed-role successor uses Qwen3 8B as the primary reviewer
under the `researcher`, `qualitative_methods`, and `domain` prompts. It builds
the same hardened, stateless request for every role and repetition. Its selector
requires a passed qualification seal, an error-family-balanced Dreaddit
development projection, repetition 1 observations from the exact Qwen snapshot,
and a clean pre-held-out access state. It fails closed on an empty denominator,
imbalance, duplicate records, actor or hash drift, and missing observations.

The source-free configuration and nine-request plan check is:

```sh
python3 experiments/rq2_role_prompted_llm/scripts/run_qwen3_fixed_role.py dry-run
```

The local Ollama identity check is:

```sh
python3 experiments/rq2_role_prompted_llm/scripts/run_qwen3_fixed_role.py preflight-service
```

The optional inert three-role interface canary is:

```sh
python3 experiments/rq2_role_prompted_llm/scripts/run_qwen3_fixed_role.py source-free-test
```

Real packet execution and fixed-role selection remain blocked under the tracked
component freeze. A new approved study freeze must bind a passed qualification
seal, privacy-cleared packet bank, candidate-generation actor, sample and
cluster minima, output location, and pre-held-out access record. See
`protocol/qwen3_fixed_role_contract_v1.md`.

## Qwen3 Generalist reviewer component

The Generalist reviewer is now implemented as a separate Qwen3 8B reviewer
actor. It reuses the shared evaluator-item and rating schemas, the shared rater
guide, and the frozen Generalist prompt. It does not reuse Qwen's historical
candidate-generation role. The component has no corpus path and cannot open a
real packet bank. A reduced transport schema constrains JSON generation, and
the complete shared schema separately enforces numeric and cross-field rules.

The source-free configuration check is:

```sh
python3 experiments/rq2_role_prompted_llm/scripts/run_qwen3_generalist_reviewer.py dry-run
```

The local Ollama identity check is:

```sh
python3 experiments/rq2_role_prompted_llm/scripts/run_qwen3_generalist_reviewer.py preflight-service
```

The live source-free interface canary is:

```sh
python3 experiments/rq2_role_prompted_llm/scripts/run_qwen3_generalist_reviewer.py source-free-test
```

The canary uses one inert in-memory software fixture, writes nothing, and is
not research evidence. The `run` command remains blocked. A separate formal
study freeze must bind an authorized, privacy-cleared packet bank, a distinct
candidate-generation actor, governance records, and the frozen analysis before
real packets may be opened or sent to Qwen. The current component hash is a
local reproducibility record, not an external approval seal. See
`protocol/qwen3_generalist_reviewer_contract_v1.md`.

## Qwen3 Generalist scoring export

The separate scoring exporter is ready for an authorized Dreaddit test run. It
reads no evaluator packet or corpus file. It joins a complete sealed set of
Qwen3 repetition-1 terminal observations to a separately hash-bound private
truth and post-cluster map, retains every failure as a miss, and reports
`TP/N`, recall, and a 10,000-resample post-cluster percentile 95 percent
confidence interval. It writes an aggregate private file only after the study
freeze, approval, privacy, provider-scope, preaccess, candidate-separation,
model, schema, input-hash, denominator, and cluster-minimum checks all pass.

The source-free static check is:

```sh
python3 experiments/rq2_role_prompted_llm/scripts/export_qwen3_generalist_score.py dry-run
```

The `export` command additionally requires the authorized study freeze, its
exact formal readiness report, the sealed observation bundle and seal, the
private truth/cluster map, and a new output path. The readiness report must bind
the same authorization record and show all ten Dreaddit gates complete. The
exporter refuses personal-local or incomplete readiness reports and never
overwrites an existing export. No approved study freeze or real result is
created by this component. See
`protocol/qwen3_generalist_scoring_export_contract_v1.md`.

## V2.4 one-packet real-data smoke diagnostic

V2.4 tests the smallest complete WarrantRoute semantic unit: one deterministic
Dreaddit development packet with six excerpts from six disjoint post clusters.
The packet is selected outside the ten packets reserved for the v2.2
qualification. Qwen constructs one positional base, code validates and maps
it, and Gemma returns one flat base-admissibility decision. No variants,
reviewers, replacement packets, retries, or qualification claims are allowed.

Before source access, v2.4 reruns the complete v2.3 source-free canary. It then
validates the exact personal-local policy and live hashes. The integrity check
hashes both bound corpus files without parsing or emitting records. The
inherited selector decodes the full indexed Dreaddit development split to rank
eligible clusters, but only the selected six excerpts are sent to the models.
No AGYW record is decoded or sent to a model.

Both real-data calls request a 16,384-token context and set
`truncate=false` and `shift=false`. A real six-excerpt packet is atomic and is
never chunked. Input overflow stops before generation. A success without the
frozen output reserve and safety margin is rejected and never retried.

The source-free static check is:

```sh
python3 experiments/rq2_role_prompted_llm/scripts/run_personal_local_real_smoke_v24.py dry-run
```

The explicit private one-packet command is:

```sh
python3 experiments/rq2_role_prompted_llm/scripts/run_personal_local_real_smoke_v24.py run
```

Runner-written source-bearing requests, responses, and derived prose remain
under `Storage/rq2_personal_local_diagnostic/v24_one_packet_smoke_runs/` with
private permissions. Prompts are sent only to the numeric-loopback Ollama
service. Ollama logging is operator-managed, so source-bearing execution
requires a single-user process with debug and request-body logging disabled.
Console output and the sanitized report contain counts, hashes, token
accounting, finite stage statuses, and structured decisions only. The freeze
is `config/personal_local_real_smoke_v24_freeze.json`, the contract is
`protocol/personal_local_real_smoke_contract_v1.md`, and the runner is
`scripts/run_personal_local_real_smoke_v24.py`.

## V2.3 prompt-limit diagnostic

V2.3 prevents Ollama from silently truncating or shifting input context. It
sets `truncate=false` and `shift=false`, partitions only the source-free
canary's inert padding, repeats the complete instruction for every chunk, and
requires exact consensus across all chunk responses. It preserves every v2.2
file byte-for-byte.

The source-free static check is:

```sh
python3 experiments/rq2_role_prompted_llm/scripts/run_personal_local_main_v23.py dry-run
```

With numeric-loopback Ollama running, the source-free live check is:

```sh
python3 experiments/rq2_role_prompted_llm/scripts/run_personal_local_main_v23.py preflight-service
```

V2.3 does not generically split real six-excerpt WarrantRoute packets. Such a
split would change joint support, counterevidence, boundary, and independence
judgments. A future source-bearing freeze must define task-specific chunk
schemas and a deterministic reducer. Until then, an oversized real semantic
unit must stop before generation.

The v2.3 freeze is `config/personal_local_main_v23_freeze.json`, its contract is
`protocol/personal_local_main_contract_v5.md`, its prompt guard is
`scripts/prompt_limit_guard.py`, and its runner is
`scripts/run_personal_local_main_v23.py`.

## Frozen v2 qualification boundary

The qualification freeze is `config/personal_local_main_v2_freeze.json`; its
contract is `protocol/personal_local_main_contract_v3.md`; and its runner is
`scripts/run_personal_local_main_v2.py`. The v1 runner, freeze, and failed run
remain immutable historical diagnostic records.

## V2 qualification-only boundary

V2 imports hash-verified v1 safety, local-service, checkpoint, sampling, item,
and aggregation helpers without changing v1 bytes. It writes only below the
separate `Storage/rq2_personal_local_diagnostic/v2_runs/` namespace and rejects
v1 run identifiers. It reads the source-free v1 development selection
commitments only to exclude those clusters. It does not resume, copy, pool, or
analyze a v1 outcome.

The runner selects ten fresh Dreaddit development packets. Qwen returns a
six-position base plan rather than arbitrary excerpt identifiers. Code maps
positions to opaque identifiers and quarantines any schema-valid base that
fails the frozen support, countercase, context, independence, or boundary-link
rules. Gemma then performs a separate compact base-admissibility gate. Every
non-admitted base has five recorded `skipped_invalid_base` slots and no
dependent call.

Unsupported evidence, source concentration, and counterevidence loss are
assembled by deterministic finite edits. Qwen proposes only a single targeted
field replacement for contextual flattening and only a single claim
replacement for unsupported abstraction. A second target-blind Gemma phase
sees an admitted compact base and a machine-derived diff. Terminal or invalid
slots are quarantined once and are never retried, regenerated, replaced,
manually overridden, or cherry-picked.
Comparison outcomes carry the frozen label
`frozen_local_model_screened_not_human_ground_truth`; they are not human ground
truth.

The frozen qualification requires at least eight admitted bases, no more than
two unclear base decisions, exact structural signatures, no terminal or
deterministic-invariant failure, at most two unclear comparisons per family,
at least five accepted independent clusters per family, and at least thirty
accepted variants overall. Pass and fail outcomes both produce a complete
qualification-only seal and stop. This freeze never calls Llama, selects a
fixed role, or opens Dreaddit audit or AGYW. Any continuation requires a later,
separate v2-main freeze bound to a passed qualification seal.

The source-free dry run neither opens corpus records nor contacts Ollama:

```sh
python3 experiments/rq2_role_prompted_llm/scripts/run_personal_local_main_v2.py dry-run
```

The service preflight contacts only numeric-loopback Ollama metadata endpoints
and does not open corpus records:

```sh
python3 experiments/rq2_role_prompted_llm/scripts/run_personal_local_main_v2.py preflight-service
```

The explicit source-bearing qualification command is:

```sh
python3 experiments/rq2_role_prompted_llm/scripts/run_personal_local_main_v2.py run
```

Every lifecycle summary reconciles
`planned = skipped_invalid_base + attempted`,
`attempted = constructed + preverification_quarantined`,
`constructed = verification_attempted`,
`verification_attempted = verified + verifier_terminal`, and
`verified = accepted + verifier_valid_rejected`. `Verified` means a valid
comparison-verifier output, not merely a started call.

## Frozen v1 historical boundary

The runner permits exactly three descriptive lanes: five Dreaddit-development
packets for fixed-role selection, five disjoint Dreaddit audit packets, and five
AGYW held-out focus-group packets. Each packet produces five controlled-flaw
variants. The three frozen prompted roles are reviewed in three independent,
stateless repetitions only after pre-review construction screening.

Generation uses local `qwen3:8b` with temperature 0, a 1,536-token cap, and
thinking explicitly disabled. Review uses local `llama3.1:8b` with temperature
0.2, a 512-token cap, and the fixed distinct repetition seeds `2027082601`,
`2027082602`, and `2027082603`. Independent blinded construction verification
uses local `gemma3:4b`, temperature 0, seed `2027082699`, and a 768-token cap.
Gemma sees the base and variant only—not the frozen target, construction note,
family index, truth, or reviewer outputs. Truncated responses fail validation. All three models
must be served by the exact numeric-loopback Ollama endpoint; DNS, redirects,
proxies, cloud processing, tools, and human review are forbidden.

The source-free readiness scope assessment and the pinned exact personal policy
validator are conjunctive. Before parsing a corpus record, the runner verifies
the policy, validator, readiness record, consolidated two-incident manifest,
static artifacts, and both live record hashes. A frozen source-free byte-offset
and line-hash index ensures development loading decodes only Dreaddit development
rows. Restricted source-bearing files stay
under `Storage/rq2_personal_local_diagnostic/` with private permissions. Source
text is never printed or placed in the run manifest, seal, or aggregate JSON.

## Frozen v1 commands retained for audit

The static dry run neither opens corpus records nor contacts Ollama:

```sh
python3 experiments/rq2_role_prompted_llm/scripts/run_personal_local_main.py dry-run
```

The service preflight contacts only the numeric-loopback Ollama metadata
endpoints and does not open corpus records:

```sh
python3 experiments/rq2_role_prompted_llm/scripts/run_personal_local_main.py preflight-service
```

The historical v1 runner is not the prospective qualification path. Its former
source-bearing command is retained here only to identify the frozen interface:

```sh
python3 experiments/rq2_role_prompted_llm/scripts/run_personal_local_main.py run
```

An interrupted run resumes from immutable per-call and per-observation
checkpoints when the same `--run-id` is supplied. The maximum complete plan
makes 90 generator calls, 75 verifier calls, and 675 reviewer calls, for 840
local calls total. Fewer reviewer calls occur when Gemma excludes variants
before review. API cost is
recorded as `0.0`; electricity and hardware cost are explicitly not measured.

## Analysis boundary

The development lane selects one fixed role by repetition-1 micro recall, with
ties resolved `generalist > methods > domain`, and seals that choice before a
held-out split is retained or prepared. The generalist repetition-1
`requested_expertise` value drives a frozen personal-diagnostic router proxy.
That proxy is not the manuscript's unimplemented trained regularized router.

Detection requires a valid output, empty `cannot_judge`, and the exact frozen
target flag. Performance is explicitly labeled `automated-target recall among
Gemma-screened variants`; it is not human ground truth. A variant is accepted
only when frozen structural invariants pass and blinded Gemma identifies exactly
the intended single flaw with one valid opaque anchor. Wrong, multiple,
unchanged, unclear, or otherwise flawed variants are quarantined without
regeneration, replacement, or manual override and are excluded before review,
not scored as misses. Reports keep repetition 1 primary, two-of-three flag stability as
a sensitivity analysis, held-out corpora separate, discordants and failures,
token and latency accounting, and a 10,000-resample cluster bootstrap with seed
`20270826`. A confidence interval is not estimable below five independent
clusters.

## Inactive legacy paths

`protocol/execution_contract_v1.md`,
`config/private_local_development_freeze.json`, and
`scripts/run_private_local_development.py` are retained only as inactive
one-packet engineering records. They are not an executable current boundary.

All OpenAI/cloud execution, including
`config/private_openai_exploratory_review_freeze.json` and
`scripts/run_private_openai_exploratory_review.py`, is inactive and forbidden
under the current personal-local policy. No source-bearing command from those
legacy files is authorized.
