# All roles model-profile compatibility contract v2

## Scope

This additive component makes the WarrantRoute All roles implementation
portable across frozen local reviewer models while preserving the existing
Qwen3 v1 freeze. Qwen3 8B remains the primary and default profile. Llama 3.1 8B
and Gemma 3 4B are compatibility profiles. The Llama and Gemma profiles do not
become study models, manuscript evidence, or approved substitutes merely by
being registered. Their exact tracked profiles passed the inert three-role
source-free canary on August 28, 2026. This establishes interface compatibility
only.

The component is source-free. It can validate tracked assets, build inert
requests, check one selected local model identity, run inert role canaries, and
exercise software fixtures. Every source-bearing command is blocked for every
profile. A failed selected profile never falls back to Qwen or another model.

## Shared core and model profiles

The core owns the researcher, qualitative-methods, and domain prompts, the
shared guide and schemas, three repetitions and their seeds, decoding safety
settings, the All roles reducer, failure scoring, denominator, bootstrap,
source-free boundary, and result-seal rules. A profile cannot override these
elements.

A model profile owns only the exact model and manifest identity, all manifest
layer digests, inherited manifest parameters, three model-specific actor IDs,
and the message-packaging capability required by the model template. The
registry is closed. Profiles are selected by a known identifier, never by an
arbitrary configuration or model path.

The loader verifies the exact config, template, license, and parameter blob
bytes against their content-addressed digests. A service preflight additionally
streams and verifies the selected model blob before any chat call. A
process-local cache is valid only while the blob's device, inode, size,
modification time, and change time remain unchanged.

The common reviewer runtime explicitly sends temperature 0.2, top-p 1, top-k
20, repeat penalty 1, an 8,192-token context, and a 512-token output limit. It
uses the three frozen repetition seeds. Explicit top-k and repeat-penalty values
prevent Qwen, Llama, and Gemma from silently inheriting different sampling
values from their manifests. Requests disable thinking, tools, streaming,
automatic retries, truncation, and context shifting.

The generation interface uses the frozen flat, fully required rating transport
schema and then validates the response against the authoritative shared rating
schema locally. Every profile receives the same concise serialization reminder
for the authoritative cross-field rules, including the relation among null
scores, `cannot_judge`, disposition, requested expertise, and acceptance. This
reminder does not repair, coerce, or retry an invalid response. Qwen and Llama
use distinct system and user messages. Gemma uses one delimited user message
because its tracked Ollama template does not preserve a distinct system role.
This packaging difference is explicit in its profile and cannot alter the role
prompt, guide, item serialization, schemas, seeds, or reducer.

## All roles semantics

All profiles use the same method. Repetition 1 is primary. Each role contributes
its serious-error flags only for a valid response with an empty
`cannot_judge` array. All other statuses contribute an empty set and remain in
the denominator. The primary item flag set is the union across the three roles,
and the item is a hit only when that union contains the prespecified target
flag.

For stability, each role first retains flags appearing in at least two of its
three repetitions. The three role-level sets are then unioned. Votes are never
pooled across roles to satisfy the two-of-three threshold. All roles creates no
fourth prompt, actor, or model call.

## Profile-bound integrity

The canonical profile bytes and SHA-256 are carried in the immutable context.
The profile identifier and hash enter every fixture-observation commitment and
the fixture-matrix commitment. Results and result seals bind both the component
freeze and the selected profile hash. An unchanged fixture, result,
observation, response, or seal produced under one profile is invalid under
every other profile.

External qualification, eligibility, truth, or review-matrix hashes in a
software fixture remain explicitly unverified. Local commitments provide
fixture integrity and reproducibility. They do not authenticate an external
study record, prove which model originally produced coherently relabeled and
resealed fields, or authorize real execution. A future study runner must verify
an authenticated upstream acquisition or review-matrix seal before accepting
real observations.

The dynamically specialized input, result, and seal schemas have distinct v2
identifiers containing both the profile ID and component-freeze SHA-256. An
external schema cache therefore cannot alias schemas from different freezes.
These schemas never reuse the v1 Qwen identifiers or reinterpret v1 artifacts.

## Commands

The generic entrypoint defaults to Qwen3:

```sh
python3 experiments/rq2_role_prompted_llm/scripts/run_all_roles_profiles_v2.py dry-run
```

Source-free Llama and Gemma plans use a closed profile identifier:

```sh
python3 experiments/rq2_role_prompted_llm/scripts/run_all_roles_profiles_v2.py --model-profile llama3_1_8b dry-run
python3 experiments/rq2_role_prompted_llm/scripts/run_all_roles_profiles_v2.py --model-profile gemma3_4b dry-run
```

`preflight-service` checks only the selected profile. `source-free-test` sends
the inert interface canary through the three role prompts for only the selected
profile. Both commands require the exact tracked Ollama version, model tag,
manifest digest, and layer bindings. Dry-run, preflight, and canary reports
identify the exact component-freeze SHA-256 and selected profile SHA-256. `run`
always fails before model-service, dataset, `Storage/`, or output access.

Llama and Gemma remain compatibility profiles despite passing their exact
source-free canaries. A later approved study freeze must separately authorize
any real use, preserve distinct candidate-generation and reviewer records, and
precede any held-out access.
