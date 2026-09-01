# Qwen3 WarrantRoute component contract v1

## Purpose

This component provides the source-free engineering boundary for WarrantRoute
with the exact Qwen3 8B reviewer snapshot already bound by the Qwen3 fixed-role
component. It fixes the schemas, route vocabulary, role mapping, failure rules,
and deterministic route reducer that a future authorized execution component
must use.

It does not authenticate a routing policy, create an execution route seal,
accept inline ratings as evidence, train the manuscript router, open a packet
bank, call a model, read held-out data, or produce manuscript evidence under
the current freeze. The public policy, sealing, and application entrypoints
fail closed. In-memory route applications are software contract fixtures only.

## Review roles and route actions

The Qwen3 snapshot is used under three prompts in this order:

1. `researcher`
2. `qualitative_methods`
3. `domain`

The router chooses exactly one of four actions:

1. `none` selects the researcher observation.
2. `qualitative_methods` selects the qualitative methods observation.
3. `domain` selects the domain observation.
4. `both` takes the union of the qualitative methods and domain flags.

Specialist routes never include the researcher flags. A selected role that
fails contributes no flag. It is never replaced by another role, and no merged
rating is created. Repetition 1 is primary. The two-of-three sensitivity keeps
a flag only when at least two stateless repetitions from the same role select
it, then applies the same frozen route.

## Router boundary

Router inputs contain only a source-free projection of signals available before
specialist review. The projection may eventually include frozen numeric,
boolean, and categorical encodings of the initial researcher judgment and
nonsensitive provenance. The active component binds no feature names because
the feature set has not been prospectively frozen.

The router input cannot contain source text, rationales, protected attributes,
verified errors, controlled-condition labels, specialist observations,
specialist outcomes, test outcomes, or the post-route useful-role label. The
runtime recursively rejects these fields even when they are nested.

The canonical lane identities are explicit. Dreaddit development maps the
official training split to `development_train`. Dreaddit audit maps the official
test split to `in_domain_audit`. CaChe maps the complete focus-group collection
to the internal `agyw_focus_groups` held-out lane. Loose aliases are rejected.

## Future policy requirements

A future policy manifest must bind the exact implementation, policy artifact,
feature set and order, preprocessing, development projection, qualification
gate, regularization, expert-time budget and route costs, threshold rule, route
tie order, and inference-failure action. The underlying files and seals must be
opened and hash-verified. A caller-provided `passed` value or hash-shaped string
is not sufficient.

The policy and every packet route must be sealed before the first Dreaddit audit
or CaChe read. A route cannot change after specialist observations, Qwen role
outputs, target flags, human responses, or held-out outcomes become available.

The binding chain must be acyclic. The qualification gate is bound by its
qualification seal. The policy manifest then binds the policy, implementation,
gate, and qualification seal. A pre-access seal binds that manifest. A new
execution freeze finally binds every one of those artifacts. The current v1
freeze cannot be converted into that execution freeze by changing booleans.

An authorized route application must load ratings from a sealed, text-free
observation-projection bank. It must verify the projection seal, file hashes,
complete role and repetition inventory, evaluator-item hash, Qwen snapshot,
actor, prompt hash, and repetition seed. Inline rating objects and caller-
provided observation hashes are never authoritative. No such observation bank
exists yet, so real route application remains blocked.

## Scientific decisions still required

The active manuscript does not yet fix the exact feature encoding, missing-value
rules, training target, model formulation, regularizer and solver, class
weighting, expert-time costs, budget, threshold objective, route tie rule,
inference-failure action, random-routing procedure, uncertainty-only baseline,
minimum development items and clusters, or the order of two specialist feedback
records for repair. These choices affect the study and cannot be inferred from
the historical diagnostic proxy.

For that reason, policy validation, route sealing, route application, `train`,
and `run` fail closed. Enabling them requires a new authorized successor freeze
after a qualification gate passes and every decision above is recorded
prospectively.

## Current commands

`dry-run` validates the component freeze, Qwen dependency, exact model manifest,
schemas, route semantics, and blocked execution boundary. It does not contact
Ollama or read `dataset/` or `Storage/`.

`source-free-test` exercises the four route mappings using finite in-memory
software contract values. It is not a dataset, experiment, result, or manuscript
artifact.

`train` and `run` are intentionally blocked.
