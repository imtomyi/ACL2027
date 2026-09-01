# Qwen3 Generalist scoring export contract v1

## Purpose

This exporter creates the aggregate value for the Qwen3 8B Generalist row only
after an authorized held-out study has completed. It does not open evaluator
packets, corpus files, prompts, or manuscript files. The exporter consumes a
frozen scoring record, the integrity seal produced by
`seal_qwen3_generalist_packet_bank.py`, a sealed observation bundle, and the
sealer's separate rich private truth and cluster map. It also consumes the
formal execution freeze and the restricted raw execution bundle and seal. Its output contains
aggregate counts and hashes, not item-level truth, model rationales, or source
text.

## Frozen denominator and hit rule

The denominator is every item in the privacy-cleared packet-bank seal and the
hash-bound truth map. The seal identifier must be the deterministic identifier
derived from its bound packet-bank hash. Its exact file hash, study, actors,
item count, item-set commitment, family counts, post-cluster count, readiness,
schemas, analysis code, contract, and held-out preaccess bindings must match the
scoring freeze and the supplied files. The frozen item-set commitment must
match the rich truth-map item set. The observation bundle must contain exactly one terminal
repetition-1 record for every truth-map item and no additional item. Missing,
duplicate, replacement, or nonprimary records stop the export.

Every repetition-1 observation must carry the canonical SHA-256 digest of its
private raw execution record. The exporter verifies that digest against the
restricted raw bundle, the complete three-repetition item grid, and the raw
bundle's deterministic seal. The execution freeze must bind the exact formal
runner and runner contract. The reviewer model, model digest, repetition seed,
terminal status, and fixed source-free rationale projection must agree across
the frozen records.

A true positive requires a schema-valid rating, an empty `cannot_judge` list,
and the independently assigned required flag in `serious_error_flags`. Invalid
JSON, schema failure, truncation, context overflow, timeout, service failure,
model-identity failure, abstention, another terminal failure, a nonempty
`cannot_judge` list, or a missing or different flag counts as a miss. These
outcomes remain in the fixed denominator and are never retried or replaced for
scoring.

## Confidence interval

The primary metric is micro error-detection recall, reported as `TP/N` and a
proportion. Each truth row identifies one unique base packet and all complete,
disjoint released-post clusters that support it. Since one item-level outcome
may depend on several posts, the 95 percent interval resamples base-packet
connected components, preserving every post that contributes to an item. The
exporter uses 10,000 percentile bootstrap resamples with seed `20270826`. It
stops without an export when fewer than five independent components are
present.

## Eligibility boundary

The study freeze must predate held-out access and bind the approved corpus,
test split, post cluster, fixed denominator, privacy-cleared packet-bank seal,
private truth-map hash, distinct candidate generator, exact Qwen3 reviewer and
model digest, rating schema, exporter, and this contract. It must also name a
separate approval record that authorizes corpus use, privacy handling, provider
scope, and manuscript reporting.

The exporter also requires the exact hash-bound readiness report produced from
that approval record, together with the governance record, reviewer registry,
privacy-review log, source receipt, study manifest, held-out preaccess record,
and packet-study freeze. It reruns the formal readiness checker from the exact
records and requires the reproduced report to match. The packet-study freeze
must propagate the candidate-generator actor, model, immutable snapshot
digest, and prompt digest. The report must be a local-evidence record in formal
`real_text_candidate` mode. Its source-record hash must equal the approval
record hash in the study freeze. Dreaddit must have all ten required unique
gates complete, no blocking reasons, and `real_text_ready=true`. A
personal-local report, a report with fewer than ten completed gates, a changed
or unbound report, or a report with a blocked gate cannot authorize an export.
The observation seal must bind the resulting bundle to that exact study freeze
and attest a complete terminal record set without source text.

Every gate is checked before the output file is created. Private inputs must be
absolute, nonsymlinked mode-0600 files in the restricted governance or
`Storage/` roots. The output must be a new absolute path under a nonsymlinked
mode-0700 `Storage/` directory and is created mode 0600 without overwrite.

The local evidence format has no independently verifiable external-authority
signature. The exporter therefore records the exact local evidence chain as
verified but keeps the external-authority gate explicitly unsatisfied and sets
`manuscript_eligible=false`. A score cannot enter the manuscript until that
external-authority gate is satisfied. No local boolean or hash-shaped string
can satisfy the gate. Even after an external verification mechanism is added,
an export applies only to the single bound dataset, split, method, model,
denominator, and metric. It does not authorize any other row or claim.
