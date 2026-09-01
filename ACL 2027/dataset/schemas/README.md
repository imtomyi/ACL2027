# Shared experiment record

`experiment_record.schema.json` is the minimum common shape for all four study corpora. It mirrors the current Dreaddit and AGYW records while allowing dialogue-specific context for KODIS and CANDOR.

The schema standardizes structure, not privacy status. A record containing exact or lightly masked text remains restricted even when it validates.

## Stable meanings

- `record_id`: project-specific turn or segment identifier.
- `source_id`: project-specific post, focus-group, session, or conversation identifier.
- `speaker_id`: project-specific speaker identifier when the source supports one.
- `context.preceding_record_ids`: ordered local context within the same source.
- `sampling_strata`: variables allowed for sampling and audit, not automatically allowed as router features.
- `provenance`: integrity information without raw participant or platform identifiers.
- `quality`: sampling eligibility, masking events, and privacy-review status.

The governed KODIS and CANDOR pipeline uses keyed HMAC fingerprints and pseudonyms. The older Dreaddit and AGYW pipeline currently uses unkeyed source-text hashes. The schema accepts either while the cross-corpus format is being reconciled; the standalone private KODIS exploratory bundle is documented separately.
