# CANDOR transcript-only processing protocol

## Current status

The CANDOR lane is ready for an **authorized package containing the verified original BetterUp Cliffhanger route described below**, but the real corpus is not present and has not been processed. Other transcript-only layouts remain blocked pending inspection and implementation. The tracked records in `Storage/synthetic-results/dataset-demos/candor_demo_output/` come only from fictional test conversations. They are not corpus statistics or experimental results.

The implementation is isolated in `scripts/prepare_candor.py` and `scripts/validate_candor.py`; it does not change the AGYW, Dreaddit, or KODIS inputs or outputs. It follows the shared record shape in `schemas/experiment_record.schema.json` while adding CANDOR-specific source authorization, input allowlisting, lineage, connected-component splitting, and privacy checks.

## Authorized input and route precedence

Use the original BetterUp per-conversation files at paths ending in:

```text
*/transcription/transcript_cliffhanger.csv
```

The builder discovers only that exact filename and parent directory, and the manifest must assert the **Cliffhanger** transcription algorithm. It does not download the corpus and will not silently substitute TalkBank ASR, audio/video, another CSV, or a ConvoKit-derived export. BetterUp's [CANDOR research page](https://www.betterup.com/research/candor-research) and [natural-turn-transcription repository](https://github.com/betterup/natural-turn-transcription) provide public background only; neither substitutes for inspection of the received package or review of its controlling access terms.

`manifests/candor_convokit_adapter.template.json` documents a nonpreferred derived route only. If an authorized ConvoKit serialization is deliberately used, its reply field is `reply-to`, not `reply_to`, and the derivation, version, counts, permissions, and mappings must be recorded separately. Do not describe a derived dump as the original BetterUp release. The legacy `fixtures/candor.synthetic.jsonl` is likewise only a mapping fixture; the CANDOR builder and validated demo do not consume it.

The paper, ConvoKit, and TalkBank may report slightly different release counts. The pipeline therefore records the files, rows, conversations, speakers, and linkage components actually observed in the authorized package; it never hard-codes a published count as a validation target.

## Fail-closed workflow after access is granted

Keep the authorized package below `dataset/raw/candor/`, with local-user-only permissions on the input root, transcript files, local manifests, adapter, split manifest, and secret. The scripts fail if real-data controls permit group/other access. Do not commit the package or a raw-ID crosswalk.

1. Create a text-free receipt from exact Cliffhanger files:

   ```bash
   python3 dataset/scripts/prepare_candor.py inspect \
     --input-root dataset/raw/candor/authorized-package \
     --output dataset/raw/candor/candor_source_manifest.local.json
   ```

   Inspection records common basenames, sizes, SHA-256 values, headers, and observed row counts. It does not emit transcript text, source paths, participant values, or experiment records. The draft remains pending; inspection alone is not authorization.

2. Keep the generated `dataset/raw/candor/candor_source_manifest.local.json` as the receipt and fill its pending authorization fields; use `manifests/candor_source_manifest.template.json` only as a field-value guide. Copy `manifests/candor_adapter.template.json` to the exact restricted local name `dataset/raw/candor/candor_adapter.local.json`. Document the access reference, received version, acquisition date, terms/PII-handling review, transcript-only approval, and manual-review plan. Remove every unresolved input assumption before setting the adapter/package statuses to verified/authorized. Set the adapter to verified only after confirming:

   - the exact text and speaker columns;
   - that each CSV row is one Cliffhanger turn and file order is conversational order;
   - whether optional record/reply columns exist and their semantics; and
   - that the selected speaker key identifies the same person across conversations.

   The supplied templates intentionally fail validation until those facts are established. Never infer them from this synthetic fixture.

3. Stage records with a stable project secret of at least 32 bytes stored outside the repository:

   ```bash
   python3 dataset/scripts/prepare_candor.py build \
     --input-root dataset/raw/candor/authorized-package \
     --adapter dataset/raw/candor/candor_adapter.local.json \
     --source-manifest dataset/raw/candor/candor_source_manifest.local.json \
     --secret-file /approved/secure/location/candor_hmac_key \
     --output dataset/deidentified/candor/staged
   ```

   Without a split manifest, every record receives `unassigned_pending_preregistration`. The build emits `linkage_groups.jsonl` containing only pseudonymous conversation/speaker connected components.

4. After split rules are preregistered, copy `manifests/candor_split_manifest.template.json` to `dataset/raw/candor/candor_splits.local.json` and assign each entire `candor_linkage_*` component to one split. Never optimize a ratio by breaking a component. Rerun with `--split-manifest`; the builder accepts exact component coverage only.

5. Validate the staged bundle:

   ```bash
   python3 dataset/scripts/validate_candor.py \
     --output dataset/deidentified/candor/staged \
     --adapter dataset/raw/candor/candor_adapter.local.json \
     --source-manifest dataset/raw/candor/candor_source_manifest.local.json \
     --split-manifest dataset/raw/candor/candor_splits.local.json
   ```

The real builder refuses input outside `dataset/raw/candor/` and refuses output outside `dataset/deidentified/candor/`. It never writes a raw-ID crosswalk.

The output directory is a closed bundle: only `records.jsonl`, `linkage_groups.jsonl`, `build_report.json`, and an optional `validation_report.json` are allowed. Unknown files, directories, and symlinks cause failure. A replacement build first invalidates an existing validation report; rerun the validator before relying on rebuilt output. Validation reports include SHA-256 values for the exact validated bundle.

## Retained and excluded information

The allowlist retains only:

- normalized, first-pass pattern-masked transcript text;
- keyed pseudonymous conversation, speaker, turn, and linkage-component IDs;
- a derived positive turn ordinal based on verified CSV row order;
- bounded preceding-turn IDs and an optional verified backward reply link;
- keyed text integrity fingerprints and nonidentifying row provenance; and
- pending privacy-review status.

All other CSV columns must be explicitly listed as discarded in the verified adapter. In particular, outputs exclude structured audio, video, survey, demographic, location, precise-timestamp, timing-offset, raw-source-identifier, and metadata-derived sampling-strata fields. A person can still state an age, exact time, location, employer, or other identifying fact inside transcript text; these free-text disclosures remain unresolved until human review. The source receipt records file hashes and aggregate observed counts but no raw conversation path or participant value.

Global speaker pseudonyms are allowed only after the authorized key is confirmed to be person-stable across conversations. Conversations and speakers form a bipartite graph; each connected component is the indivisible experimental split unit. The validator independently recomputes this graph and rejects a conversation, linked speaker, or component that spans splits.

## Privacy status and human review

Automatic masking covers URL, email, IP address, handle, phone-like number, and numeric exact-date patterns. It does **not** reliably remove names, places, employers, schools, street addresses, demographic self-disclosures, precise times written in free text, unusual life histories, searchable phrases, or other quasi-identifying context.

Every staged natural-language record therefore starts with:

- `eligible_for_packet_sampling: false`;
- `manual_privacy_review_pending` as an ineligibility reason;
- `manual_excerpt_review_required: true`; and
- `privacy_review_status: pending`.

The outputs are restricted and pseudonymized, not anonymous. Pattern masking is not completed de-identification. A documented human privacy and permissions review is required before model, rater, packet-sampling, quotation, or release use. BetterUp/TalkBank access, redistribution, and PII-handling terms remain controlling; no public redistribution is cleared by this pipeline.

## Synthetic demo

The demo input includes three fictional conversations, nine turns, and five fictional speakers. One speaker key links two conversations, producing a six-turn component; the third conversation is a separate three-turn component. The fixture deliberately contains timing, demographic, survey, audio/video, and raw-ID columns so their exclusion can be tested. It also exercises one URL, email, IP address, handle, phone-like number, and exact date.

Build and validate it with:

```bash
python3 dataset/scripts/prepare_candor.py build \
  --input-root dataset/fixtures/candor_synthetic/package \
  --adapter dataset/manifests/candor_demo_adapter.json \
  --source-manifest dataset/manifests/candor_demo_source_manifest.json \
  --split-manifest dataset/manifests/candor_demo_split_manifest.json \
  --output Storage/synthetic-results/dataset-demos/candor_demo_output \
  --demo --replace

python3 dataset/scripts/validate_candor.py \
  --output Storage/synthetic-results/dataset-demos/candor_demo_output \
  --adapter dataset/manifests/candor_demo_adapter.json \
  --source-manifest dataset/manifests/candor_demo_source_manifest.json \
  --split-manifest dataset/manifests/candor_demo_split_manifest.json \
  --demo \
  --validation-report Storage/synthetic-results/dataset-demos/candor_demo_output/validation_report.json \
  --replace-report

python3 -m unittest dataset/tests/test_candor_pipeline.py
```

`--demo` is bound to the exact shipped `dataset/fixtures/candor_synthetic/package`, demo control-file paths/checksums, and dedicated fixture output area. It cannot be used on arbitrary or real input, cannot write into the real CANDOR output root, and cannot accept a real secret file. The validation report distinguishes linkage-component integrity from split isolation and labels the applied split as synthetic rather than preregistered.

## Exactly what remains blocked

Until authorized access is granted and the received package is inspected, the following are not complete:

- authoritative file inventory, version, sizes, SHA-256 values, and observed release counts;
- verification of actual CSV headers, row granularity, order, and optional reply semantics;
- verification of a global person-stable speaker key or another approved linkage mechanism;
- the real conversation-speaker graph, components, preregistered assignments, and split sizes;
- real transcript preprocessing, masking statistics, validation, and sampling eligibility;
- manual contextual privacy review and any approved review-state changes;
- confirmation of access scope, secondary-use/ethics determination, model or rater processing, retention/deletion controls, quotation, and redistribution permissions; and
- any corpus-dependent WarrantRoute result.

Do not state that the real CANDOR corpus is prepared, de-identified, validated, anonymous, or cleared for experiments while these items remain unresolved.
