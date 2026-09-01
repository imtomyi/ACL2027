# WarrantRoute multimodel adapter contract v1

## Purpose

This source-free adapter separates WarrantRoute routing semantics from reviewer
model identity. Qwen3 8B is the primary profile. Llama 3.1 8B and Gemma 3 4B
are unbound adapter templates that use the same reviewer-matrix schema and
deterministic route reducer.

The adapter never trains a router, opens a corpus, calls a model, accepts a
reviewer output as study evidence, writes an experimental result, or changes a
manuscript. Every profile remains ineligible for source-bearing execution under
this freeze.

## Stable interface

Every reviewer profile supplies only these model-specific values:

1. An opaque profile identifier.
2. The exact model identifier and local manifest hash.
3. One unique actor identifier for each of the researcher, qualitative methods,
   and domain roles.
4. A minimum context window and reviewer-canary status.

The reviewer-matrix schema, rating projection, route names, route-to-role map,
failure behavior, and reduction algorithm are shared by all profiles. The
schema validates identity shape. Runtime checks bind each observation to the
selected profile's exact model, manifest, actor, role, item, and repetition.
There is no implicit fallback to Qwen or to any other profile.

Every software fixture binds the exact adapter-freeze hash and the canonical
selected-profile hash. The reducer reloads those frozen bytes before accepting
the fixture. An unregistered profile, altered schema, or profile substitution
therefore fails before reduction.

## Route semantics

The four route actions are model-independent:

1. `none` uses the researcher-role flags.
2. `qualitative_methods` uses only the qualitative-methods-role flags.
3. `domain` uses only the domain-role flags.
4. `both` unions the qualitative-methods and domain flags.

A failed selected role contributes no flags. Another role never replaces it.
Repetition 1 is primary. The descriptive stability calculation retains a flag
when at least two of three repetitions within the same role select it and then
applies the unchanged route.

## Profiles in this freeze

`qwen3_8b` is the primary source-free interface and uses the existing Qwen3 8B
reviewer identities. `llama3_1_8b` and `gemma3_4b` are adapter templates only.
Their actor identifiers are new and model-specific. They do not reuse legacy
Llama actor aliases or Gemma's construction-verifier identity.

Llama requires a new reviewer freeze that binds all three role prompts, its
model-specific message packaging and transport schema, decoding settings, and
context guard, followed by a three-role, three-repetition source-free canary.
Gemma requires the same and must use a guarded context window of at least 16,384
tokens. Neither template authorizes a model call.

## Activating another model

Activation requires a new immutable reviewer profile and fixed-role component,
not a runtime string substitution. The successor must:

1. Bind the exact model manifest, role prompts, transport schema, local
   validation schema, decoding, seeds, and context guard.
2. Pass a source-free reviewer canary for all three roles and repetitions.
3. Seal model-specific observations before the WarrantRoute execution layer
   reads them.
4. Bind the chosen profile into the learned policy, route records, route seals,
   pre-access seal, and execution freeze.

The route algorithm and reviewer-matrix schema are intended to remain
unchanged. The profile registry, whitelist, asset hashes, and activation freeze
must change.

## Commands

`dry-run --reviewer-profile PROFILE` validates the complete source-free freeze,
schemas, prompt hashes, exact local model manifest, and selected profile.

`source-free-test --reviewer-profile PROFILE` checks the four route mappings on
opaque in-memory software values. It is not a dataset or experiment.

`train` and `run` always fail closed.
