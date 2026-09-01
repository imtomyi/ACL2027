# Qwen3 Generalist packet-bank seal contract v1

## Purpose and boundary

This component seals an already constructed, independently verified, and
privacy-cleared Dreaddit test packet bank for the Qwen3 Generalist reviewer. It
does not construct or edit a packet, open a raw or deidentified corpus file,
call a model, score an observation, or grant authorization. The only output is
a content-free integrity seal under a private `Storage/` directory.

The tracked code and schemas are source-free. Tests use ephemeral inert
software-interface fixtures and delete them at completion. Test outputs are
not datasets, observations, or manuscript evidence.

## Read order and fail-closed rule

The production `seal` command first reads only text-free evidence: the packet
study freeze, formal readiness report, exact governance record, reviewer
registry, privacy-review log, approved packet manifest, source receipt,
preaccess record, and independent verification bundle and seal. It then
validates the tracked schemas and Qwen3 Generalist component freeze. It must
stop before checking the existence, permissions, or hash of the packet bank or
private truth map unless all of these conditions hold:

1. the readiness report is a formal `real_text_candidate` report;
2. the Dreaddit lane reports all ten required gates complete with no blocking
   reason codes and `real_text_ready=true`;
3. the report contains no personal-local ineligibility warning;
4. the study freeze binds every evidence file byte for byte, including the
   governance record, registry, privacy log, manifest, receipt, preaccess
   record, verification bundle, and verification seal;
5. the readiness counts match the registry and privacy log, and every privacy
   reviewer was active, in scope for Dreaddit, trained, acknowledged, verified,
   and unexpired at the recorded review time;
6. the packet manifest and governance gates bind the same receipt, packet-bank,
   truth-map, privacy-log, item-count, and reviewer records;
7. the preaccess chronology shows that the design was frozen before held-out
   access and that no reviewer output or test outcome was observed; and
8. the candidate generator differs from the Qwen reviewer by actor ID, model
   ID, and model-snapshot digest.

Passing these checks does not itself establish authorization. The readiness
report and study freeze remain upstream evidence records. The output seal uses
`integrity_validated_not_authorization` and explicitly records that it makes no
authorization or manuscript-result claim.

## Fixed study bindings

The study freeze is validated against
`qwen3_generalist_packet_study_freeze_v1.schema.json`. It fixes:

- corpus `dreaddit`, official split `test`, role `in_domain_audit`, and cluster
  unit `post`;
- reviewer actor `qwen3_8b_generalist_reviewer_v1`, model `qwen3:8b`, and role
  `generalist`;
- a distinct candidate-generation actor and immutable model-snapshot and
  prompt hashes, plus the exact Qwen reviewer snapshot;
- the exact item denominator `fixed_n`;
- one controlled version per base packet;
- complete, globally disjoint post clusters, including member-hash
  disjointness when a cluster is renamed;
- complete privacy-log coverage for every displayed excerpt and context;
- optional frozen counts for all five controlled-error families; and
- governance, registry, privacy, packet-manifest, source-receipt, independent
  verification, packet-bank, truth-map, scoring-contract, analysis-code,
  study-design-freeze, and held-out-preaccess hashes.

When family counts are frozen, their sum must equal `fixed_n` and the observed
truth-map counts must match exactly. Every bundle must include all five
families regardless of whether exact counts are frozen.

## Packet bank

The private packet-bank file is one JSON object with the following wrapper:

- `document_type`: `warrantroute_qwen3_generalist_evaluator_item_bank`
- `schema_version`: `qwen3-generalist-evaluator-item-bank-v1`
- the frozen `study_id`
- `corpus_id`: `dreaddit`
- `official_source_split`: `test`
- `evaluation_role`: `in_domain_audit`
- `privacy_clearance_status`:
  `cleared_for_bound_model_and_rater_display`
- `items`: exactly `fixed_n` objects satisfying
  `direction-j-evaluator-item-v1`

Item and packet identifiers must be unique. The item payload cannot contain a
truth label, target flaw, error family, route, generator identity, cluster ID,
verification output, or another hidden evaluation field. Display order,
excerpt uniqueness, displayed-source counts, and source-distribution counts
are checked against the payload.

## Private truth and cluster map

The separate coordinator-only map is validated against
`qwen3_generalist_truth_cluster_map_v1.schema.json`. It contains no source text.
For every evaluator item it binds:

- the same item, packet, and output identifiers;
- a unique base-packet identifier;
- the distinct candidate-generator actor;
- the canonical evaluator-item SHA-256;
- exactly one independently verified controlled-error family and its frozen
  response flag;
- a verification-record SHA-256; and
- opaque post-cluster and source-member hashes.

The evaluator bank and truth map must form an exact item-level bijection. The
five family-to-flag mappings are fixed as follows:

- `unsupported_evidence` to `unsupported_inference`
- `source_concentration` to `hidden_source_concentration`
- `counterevidence_loss` to `lost_negative_case`
- `contextual_flattening` to `contextual_flattening`
- `unsupported_abstraction` to `unsupported_abstraction`

For every opaque post cluster, the set of packet member hashes must equal the
set of sampling-frame member hashes. Neither a cluster ID nor any member hash
may occur in two evaluator items, so renaming a reused cluster cannot evade the
disjointness check.

## Independent controlled-error verification

The text-free verification bundle is validated against
`qwen3_generalist_verification_bundle_v1.schema.json`, and its separate seal is
validated against `qwen3_generalist_verification_seal_v1.schema.json`. The
bundle must have exactly one row per evaluator item. Each row binds the
canonical evaluator-item hash, error family, required response flag, and at
least the frozen number of distinct verifiers. A verifier may be neither the
candidate generator nor the Qwen reviewer. The truth map binds the canonical
hash of the complete verification row. The verification seal binds the exact
bundle bytes, item count, and canonical sorted item-ID-set hash.

## Privacy coverage commitment

Every displayed evidence row must have one matching Dreaddit privacy-log
record. Its `packet_id` and `excerpt_id` must match, at least two distinct
pseudonymous reviewers must be listed, the decision must be approved, and both
model processing and rater display must be cleared. Every listed reviewer must
also have an active Dreaddit `privacy_reviewer` record whose approval,
verification, expiration, training, and confidentiality fields cover the
recorded review time.

The privacy record's `context_sha256` is the SHA-256 of canonical UTF-8 JSON,
with a trailing newline, for this exact object:

```json
{
  "excerpt_id": "...",
  "local_context": "...",
  "packet_id": "...",
  "source_id": "...",
  "speaker_id": null,
  "text": "..."
}
```

Canonical JSON sorts keys, uses no insignificant whitespace, and preserves the
Unicode text rather than ASCII-escaping it. This binds the reviewed context to
the exact content displayed to the model without placing that content in the
privacy log or final seal.

## Storage and output

The study freeze, readiness report, governance record, reviewer registry,
privacy log, packet manifest, and preaccess record must be regular mode-0600
files directly under a mode-0700 `governance/local/` directory. The source
receipt must be a regular file below `dataset/manifests/`. The verification
bundle, verification seal, packet bank, and truth map must be regular mode-0600
files in a mode-0700 directory below `Storage/`. Symlinks, path escapes, hash
drift, an existing output, and a nonprivate output directory are terminal
failures.

The seal contains only corpus and split labels, actor IDs, counts, and hashes.
It includes a deterministic opaque seal ID, the exact item count, and the
SHA-256 of the canonical sorted item-ID set so a later scoring freeze can bind
the same denominator without reopening the packet bank.
It never contains evaluator items, excerpts, local context, interpretations,
truth rows, or reviewer decisions. It is written once with mode 0600 and never
overwrites an existing file.

## Commands

The static source-free check reads no packet or truth map:

```sh
python3 experiments/rq2_role_prompted_llm/scripts/seal_qwen3_generalist_packet_bank.py dry-run
```

The production interface is:

```sh
python3 experiments/rq2_role_prompted_llm/scripts/seal_qwen3_generalist_packet_bank.py seal \
  --study-freeze /ABSOLUTE/PATH/governance/local/STUDY_FREEZE.local.json \
  --readiness-report /ABSOLUTE/PATH/governance/local/readiness_report.local.json \
  --governance-record /ABSOLUTE/PATH/governance/local/project_governance.local.json \
  --reviewer-registry /ABSOLUTE/PATH/governance/local/reviewer_registry.local.json \
  --privacy-log /ABSOLUTE/PATH/governance/local/privacy_review_log.local.json \
  --packet-manifest /ABSOLUTE/PATH/governance/local/packet_manifest.local.json \
  --source-receipt /ABSOLUTE/PATH/dataset/manifests/dreaddit_source_manifest.json \
  --preaccess-record /ABSOLUTE/PATH/governance/local/preaccess_record.local.json \
  --verification-bundle /ABSOLUTE/PATH/Storage/PRIVATE_RUN/verification_bundle.private.json \
  --verification-seal /ABSOLUTE/PATH/Storage/PRIVATE_RUN/verification_seal.private.json \
  --packet-bank /ABSOLUTE/PATH/Storage/PRIVATE_RUN/evaluator_items.private.json \
  --truth-map /ABSOLUTE/PATH/Storage/PRIVATE_RUN/truth_cluster_map.private.json \
  --output /ABSOLUTE/PATH/Storage/PRIVATE_RUN/packet_bank_seal.json
```

All paths must be absolute. There is no override, repair, or overwrite option.
