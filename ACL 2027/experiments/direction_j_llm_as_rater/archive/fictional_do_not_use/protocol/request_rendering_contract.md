# Direction J provider-neutral request rendering contract

Version: `direction-j-provider-neutral-request-v1`

Status: frozen synthetic-qualification request compiler; provider wire adapters
remain unvalidated and no packet produced under this contract authorizes a
network call.

## Purpose and boundary

`scripts/render_request_packets.py` deterministically compiles the same frozen
guide, evaluator item, and rating interface for the first-stage LLM actors. It
does not call a model, import a provider SDK, read credentials or environment
variables, read ratings or raw responses, or produce a study result. The
compiler is stdlib-only.

The only runnable scope is the independently authored fictional qualification
run `20260825_synthetic_paired_qualification_prepared`. The compiler fails if
any freeze, manifest, build receipt, item, or assignment marker permits real
source text. Real-text rendering remains blocked by the institutional,
platform, and model-processing gates.

## Fixed public inputs

The compiler has no CLI option for substituting a source artifact. Its complete
read allowlist is:

- `config/freeze_v1.json`
- `protocol/llm_judge_prompt_v1.md`
- `protocol/shared_rater_guide_v1.md`
- `schemas/shared_rating.schema.json`
- `runs/20260825_synthetic_paired_qualification_prepared/run_manifest.json`
- `runs/20260825_synthetic_paired_qualification_prepared/build_report.json`
- `runs/20260825_synthetic_paired_qualification_prepared/evaluator_items.jsonl`
- `runs/20260825_synthetic_paired_qualification_prepared/assignments/J_PRIMARY_rep1.csv`
- `runs/20260825_synthetic_paired_qualification_prepared/assignments/J_PRIMARY_rep2.csv`
- `runs/20260825_synthetic_paired_qualification_prepared/assignments/J_PRIMARY_rep3.csv`
- `runs/20260825_synthetic_paired_qualification_prepared/assignments/J_SENS_GEMINI_rep1.csv`

Every file and existing path component must be a non-symlink at its exact
checked-in location. The run manifest, build report, freeze, item bank, guide,
prompt, full rating schema, and four assignment receipts must agree on their
hashes and versions. The compiler does not open the private item key, a blind
map, `dataset/`, ratings, or raw model responses. An assignment row is rejected
unless `actor_kind` is exactly `llm`; consequently Charlie and the two expert
qualification assignments cannot be rendered through this tool.

## Exact message bytes

The prompt file must be BOM-free UTF-8 with LF newlines. Each marker must occur
exactly once as a complete line:

```text
<!-- BEGIN DIRECTION-J SYSTEM MESSAGE -->
<!-- END DIRECTION-J SYSTEM MESSAGE -->
<!-- BEGIN DIRECTION-J DEVELOPER MESSAGE -->
<!-- END DIRECTION-J DEVELOPER MESSAGE -->
```

The system and developer strings are the exact bytes after the LF terminating
the relevant `BEGIN` line and before the LF preceding the relevant `END` line.
The extraction does not trim, normalize, or add a newline.

The complete guide file bytes are used, including its final LF. Each evaluator
item is parsed from one canonical JSONL line and must serialize exactly as
UTF-8, sorted-key, compact JSON plus LF. For item bytes `I` and complete guide
bytes `G`, the user bytes are exactly:

```text
UTF8("SHARED RATER GUIDE\n")
+ G
+ UTF8("\nBEGIN EVALUATOR ITEM\n")
+ I
+ UTF8("END EVALUATOR ITEM\n\nReturn the shared rating JSON object only.\n")
```

The apparently doubled newline after the guide is intentional: `G` already
ends in LF and the next literal begins with LF. System, developer, and user are
stored as three separate strings. Their individual SHA-256 digests and the
canonical three-string object digest are recorded in every packet.

The renderer also asserts this fixed byte-level golden vector before producing
any packet:

- system SHA-256:
  `cab0c33a18371c39e30c4516020ba71a6ca2efef05af998cc10f0d357520efbf`
- developer SHA-256:
  `348cd32ef88dd175e2a810407adf1bac4028d9ddea114030e5f33c82be41b5bc`
- complete guide SHA-256:
  `ab0e8dfb1992927e8b2202353da55eba47f45a691222275c3feab42d53a46b4f`
- canonical item `DJI_182867ba6d054a6e` SHA-256:
  `e5cba4ac9484e8773113e16151d040af704d6d6b906eb1e51c7674c2090d029e`
- the rendered user bytes for that guide/item pair SHA-256:
  `019d8cb64539ec5d2e8c59dc169aee5b8987fbca5be1aa70ffe8167c1fc58f9d`

## Item and assignment binding

The item payload digest is `SHA256(I)`. The semantic-input digest is the
existing `canonical_manifest_v1` rule:

```json
{"interface_version":"direction-j-shared-interface-v1","item_payload_sha256":"<SHA256(I)>","shared_rater_guide_sha256":"<SHA256(G)>","shared_rater_guide_version":"direction-j-rater-guide-v1"}
```

The displayed object above is serialized as sorted-key compact UTF-8 JSON plus
LF before hashing. Every assignment row must match that digest and the frozen
`item_id`, `packet_id`, `output_id`, `corpus_id`, guide hash, interface version,
evaluation role, actor, repetition, and sequence. Each selected assignment must
contain all 24 items exactly once with sequences 1 through 24.

The render contains 96 packets:

- `J_PRIMARY`, repetitions 1, 2, and 3: 72 packets.
- `J_SENS_GEMINI`, repetition 1: 24 packets.

Each packet embeds the complete frozen judge record for its actor and the
complete frozen prompting policy, plus their canonical hashes. This preserves
null versus unset settings and does not translate settings to a provider wire
format.

## Canonical request packet JSONL

One packet is one JSON object serialized with UTF-8, sorted keys, compact
separators, no ASCII escaping, and a final LF. The file is the concatenation of
those lines, sorted by `actor_id`, `rating_repetition`, and `sequence`.

Every packet binds:

- request, study, run, actor, assignment, repetition, sequence, item, packet,
  output, corpus, and interface identifiers;
- the item, semantic input, guide, prompt source, freeze, build report, source
  receipt, evaluator bank, and assignment-manifest hashes;
- separate exact system, developer, and user strings and their hashes;
- the structural transport response schema and its canonical hash;
- the complete authoritative checked-in rating schema and its source-file hash;
- the complete frozen model settings and prompting policy;
- `contains_real_source_text=false`; and
- `wire_adapter_status=pending_provider_profile_and_wire_validation`.

`request_packet_id` is `DJREQ_` followed by the first 16 hex characters of the
SHA-256 of the canonical identity object constructed from run, actor,
assignment, repetition, sequence, item, semantic-input hash, and prompt hash.

The `provider_wire_adapter` object is deliberately non-executable:
`provider_wire_request` is null and rendered/dispatch/credential authorization
flags are false. A later provider-specific profile must validate role mapping,
structured-output support, model-returned version capture, token accounting,
raw-response capture, and the exact settings before dispatch. It may not
silently discard or merge the developer string.

## Structural transport schema versus authoritative validation

Provider structured-decoding dialects do not necessarily accept all
conditionals in the shared rating schema. The compiler therefore derives a
provider-neutral transport projection deterministically from the checked-in
full schema. The projection has the same ten required properties, primitive or
nullable types, enum values, array item enums, and
`additionalProperties=false`. It intentionally drops numeric and length
bounds, uniqueness, patterns, `if`/`then`/`else`, `allOf`, and other semantic or
cross-field constraints.

The transport projection is embedded as `response_schema`. Its digest is
`SHA256(canonical_json_utf8_lf(response_schema))`. The complete checked-in
schema is embedded separately as `post_validation_schema`, whose digest is the
SHA-256 of the exact checked-in file bytes.

The full `shared_rating.schema.json` remains authoritative. Every decoded
response must pass that full schema before it can become a successful rating.
Passing provider structured decoding or the structural projection never
replaces post-validation. A provider profile may further restrict its wire
schema but may not relax or replace the full post-validation requirement.

## Versioned format-only repair packet

Repair message version: `direction-j-format-repair-message-v1`.

Repair packet version: `direction-j-format-repair-packet-v1`.

Exactly one format-only retry is permitted, and only after the first attempt is
classified as `invalid_json` or `invalid_schema`. The retry is attempt 2; an
attempt 3 is forbidden. A timeout, provider error, content filter, substantive
disagreement, low confidence, or unfavorable rating cannot trigger this path.

The retry repeats the original system, developer, and user strings byte-for-byte
and verifies each original message hash. The sole appended message is produced
by `render_repair_instruction`. That function accepts only:

- exact invalid response bytes captured before decoding or normalization;
- failure class `invalid_json` or `invalid_schema`;
- attempt number 2; and
- validator-produced schema-error records with exactly the string fields
  `instance_path`, `schema_path`, `keyword`, and `message`.

It has no argument for a truth key, reference answer, other candidate output,
revised evaluator item, new guide, or alternate prompt. `invalid_schema`
requires at least one error record. Duplicate records are rejected; the
remaining records are sorted by their own canonical JSON bytes. Standard padded RFC
4648 base64 carries the invalid response bytes, accompanied by their byte
length and SHA-256.

The appended message bytes are exactly:

```text
UTF8("DIRECTION-J FORMAT-ONLY REPAIR\n")
+ canonical_json_utf8_lf({
  "attempt_number": 2,
  "failure_class": "invalid_json|invalid_schema",
  "instruction": "The preceding response failed format validation. Using only the exact invalid response and validator diagnostics below, return one corrected shared rating JSON object. Do not change the item, use outside information, or add commentary.",
  "invalid_response_base64": "<standard padded base64>",
  "invalid_response_length_bytes": <integer>,
  "invalid_response_sha256": "<lowercase SHA-256>",
  "repair_message_version": "direction-j-format-repair-message-v1",
  "schema_errors": [<canonical sorted records>]
})
```

The exact appended-message SHA-256 is stored as
`appended_repair_message_sha256`. The repair packet also binds the original
request packet ID, actor, assignment, repetition, sequence, both response-schema
hashes, failure class, attempt number, and the still-pending wire-adapter state.
The initial renderer does not invent repair packets before an observed invalid
response.

Frozen repair test vector:

- invalid bytes:
  `{"confidence":6,"rating_schema_version":"direction-j-shared-rating-v1"}\n`
- failure class: `invalid_schema`
- input errors (the function sorts them):
  `("/confidence", "/properties/confidence/maximum", "maximum", "6 exceeds maximum 5")`
  and `("", "/required", "required", "missing required fields")`
- appended-message SHA-256:
  `f6ed7b374a8b67b7bd22426ba27d670ac066145df10fb74ff05ca8f972cbfbac`

The self-test recomputes this vector and confirms that reversing the input error
order yields the same repair message.

## CLI and output containment

All relative packet paths are interpreted from the project root. The only
accepted packet output path is:

`Storage/synthetic-results/archived-experiments/direction-j/20260825_synthetic_paired_qualification_prepared/request-packets/request_packets_v1.jsonl`

Nested output, path traversal, symlinks, private/result/raw-response paths, and
any other directory are rejected.

Allowlisted inputs are opened with `O_NOFOLLOW` where the host supports it,
must be regular files, and are checked by file descriptor for stable device,
inode, size, and modification time across the read. Output creation is
descriptor-relative to a non-symlink run/output directory, uses
`O_CREAT|O_EXCL|O_NOFOLLOW`, never overwrites, verifies an exact readback, and
then removes owner write permission. An existing file is accepted only after
the same immutable read and a byte-for-byte deterministic verification.

```bash
# Default: validate all frozen inputs and render in memory; write nothing.
python3 experiments/direction_j_llm_as_rater/scripts/render_request_packets.py

# Positive and negative tests; write nothing.
python3 experiments/direction_j_llm_as_rater/scripts/render_request_packets.py --self-test

# Explicit, idempotent write. An existing differing file is never overwritten.
python3 experiments/direction_j_llm_as_rater/scripts/render_request_packets.py \
  --write Storage/synthetic-results/archived-experiments/direction-j/20260825_synthetic_paired_qualification_prepared/request-packets/request_packets_v1.jsonl

# Reconstruct from frozen sources and compare the existing file byte-for-byte.
python3 experiments/direction_j_llm_as_rater/scripts/render_request_packets.py \
  --verify Storage/synthetic-results/archived-experiments/direction-j/20260825_synthetic_paired_qualification_prepared/request-packets/request_packets_v1.jsonl
```

The summary reports only packet counts, actor/repetition counts, the JSONL hash,
scope, and action. These are construction facts, not ratings, agreement
estimates, validity evidence, or empirical study results.
