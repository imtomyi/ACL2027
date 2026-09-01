# KODIS preprocessing and readiness status

## Current status

The received KODIS distribution is present in the restricted landing area as
`raw/kodis/KODIS-EN.xlsx`, with its provider README and a checksum inventory.
The project has not yet recorded the governing request/EULA, approved users,
institutional determination, or model/rater scope in the local receipt. Real
preprocessing, experimental splits, privacy clearance, sampling eligibility,
and corpus-dependent results therefore remain blocked. Aggregate receipt
metrics are in `audits/kodis_20260826/`. `Storage/synthetic-results/dataset-demos/kodis_demo/`
still contains only a deterministic fictional fixture; its counts are not
KODIS corpus statistics or experimental results.

KODIS processing is isolated in `scripts/prepare_kodis.py` and `scripts/validate_kodis.py`. The older shared dialogue scripts remain available for other lanes but are not the authorized KODIS workflow. The KODIS-specific workflow follows `schemas/experiment_record.schema.json` and adds source authorization, exact input/control receipts, whole-dialogue filtering, message-order diagnostics, globally linked participant components, component-level splits, privacy gates, and checksum-bound validation.

The [KODIS paper](https://aclanthology.org/2025.naacl-long.637/) points researchers to a request form, describes a mixture of human-to-human and human-to-GPT-4 dialogues, limits corpus access to noncommercial uses, and reports USC IRB approval, informed consent, and removal of IP addresses, worker identifiers, and location information before release. The current access agreement received by the project—not the paper's publication license—must control local storage, processing, model/rater access, quotation, and redistribution.

## Received schema findings

The received release is a one-sheet XLSX with one row per dyad, a blank-header
dyad ID column, buyer/seller survey and demographic fields, a multiline
`formattedChat` transcript, outcome fields, and `buyer_is_AI` / `seller_is_AI`
flags. It does not contain message IDs, reply links, an explicit completion or
event-type field, or a cross-dialogue person-stable participant ID. The current
real adapter template therefore cannot be marked verified against this file.

The aggregate audit found 2,860 unique dyads: 2,085 flagged human-human and
775 flagged human-AI. Nine human-human rows have no transcript. Of the 2,076
nonempty human-human transcripts, 1,798 satisfy the synthetic workflow's
current minimum-length, buyer-first, two-role, and strict-alternation rules.
Strict alternation is not a valid release-wide assumption: 271 nonempty
human-human transcripts contain consecutive turns by the same role, and nine
begin with the seller. These rows must not be silently discarded merely to fit
the fictional adapter. The real adapter and dialogue rules require a documented
revision after the provider confirms completeness and transcript semantics.

Before changing the local adapter to verified, document or obtain confirmation for:

- the package/version label and the governing request/EULA (the workbook hash,
  size, row count, and observed schema are already recorded locally);
- how completion and event semantics should be interpreted for the one-row-per-dyad transcript strings;
- the exact marker distinguishing human-to-human from human-to-AI sessions;
- the exact marker proving that a dialogue is complete;
- which event values represent participant messages rather than system/finalization events;
- whether timestamp-prefixed transcript lines are the authoritative message
  boundaries and whether repeated-role messages and seller-first dialogues are valid;
- whether any unavailable participant key can establish person-stable linkage
  across conversations, or whether KODIS must remain one unsplit role; and
- every nonretained field, including surveys, demographics, preference justifications, compensation, timestamps, worker/platform IDs, and model-derived labels.

The real builder rejects `manifests/kodis_adapter.template.json`, any pending authorization receipt, unverified speaker linkage, a missing interaction/completion/event marker, an unclassified input field, or a selected file that differs from the restricted receipt.

## Fail-closed workflow after access is granted

Keep the authorized package below `dataset/raw/kodis/`. That landing directory is mode `0700`. Preserve the received archive unchanged, use mode `0700` for restricted subdirectories and `0600` for restricted files and local controls, and never commit the corpus, controls, secret, or a raw-ID crosswalk.

1. Place the authorized archive and any inspected extraction below `dataset/raw/kodis/`. Do not reconstruct the corpus from the paper or public examples. The inspector refuses symlinks and group/other-readable package entries.

2. Create the restricted inventory receipt:

   ```bash
   python3 dataset/scripts/prepare_kodis.py inspect \
     --input-root dataset/raw/kodis \
     --output dataset/raw/kodis/kodis_source_manifest.local.json
   ```

   With no authorized files, this command exits with a blocked status and writes nothing. With a package, it records relative paths, sizes, hashes, formats, and observed tabular row counts but deliberately leaves authorization and content roles pending.

3. Review the current access agreement and institutional determination. In the local receipt:

   - set `status` to `authorized_for_restricted_local_preprocessing` only with written local-processing authority;
   - record the authorization reference, agreement version and acceptance date, receipt date, package version, and approved users/team;
   - acknowledge the current noncommercial, redistribution, and identity-protection requirements;
   - record a documented institutional/ethics determination for local preprocessing;
   - record model/rater processing as either `pending_separate_written_confirmation` or `documented_approved_restricted`;
   - set the privacy plan to `documented_two_person_review_required`; and
   - mark only verified transcript exports as selected, with content role `verified-dialogue-export-with-interaction-completion-and-event-markers`.

   Inventory entries for surveys, demographics, outcomes, annotations, media, or unknown files must remain unselected.

4. Copy `manifests/kodis_adapter.template.json` to the exact restricted name `dataset/raw/kodis/kodis_adapter.local.json`. Replace every pending value from direct inspection. The verified adapter must use version `1.0`, status `verified_against_authorized_package`, exact selected filenames and input fields, distinct mappings, an explicit discard list covering every nonretained field, a buyer/seller value map, verified global person-stable speaker linkage, and this exact note:

   > Verified against the authorized KODIS package: selected transcript files, exact fields, human-human and completeness markers, message-event filter, consecutive message order, buyer/seller role mapping, and globally person-stable participant linkage were manually confirmed.

   If the release cannot support any assertion, stop rather than infer it from transcript text.

5. Store a stable random secret of at least 32 bytes outside `dataset/` with mode `0600`. The real workflow requires `--secret-file`; demo secrets and environment fallbacks are not accepted.

6. Build restricted records before assigning experimental splits:

   ```bash
   python3 dataset/scripts/prepare_kodis.py build \
     --input-root dataset/raw/kodis \
     --adapter dataset/raw/kodis/kodis_adapter.local.json \
     --source-manifest dataset/raw/kodis/kodis_source_manifest.local.json \
     --secret-file /restricted/outside-repository/kodis-pseudonym.key \
     --output dataset/deidentified/kodis
   ```

   Without a split manifest, every retained record is labeled `unassigned_pending_preregistration`. The builder emits only pseudonymous records, connected-component linkage groups, and aggregate diagnostics. It never marks a record eligible.

7. Freeze the received version, participant linkage, sample-size plan, and split rules. Copy `manifests/kodis_split_manifest.template.json` to the exact restricted name `dataset/raw/kodis/kodis_splits.local.json`; set status `preregistered_component_assignments` and assign every emitted `kodis_linkage_*` component exactly once. A component contains every conversation connected by a recurring participant. Never break a component to improve split ratios.

8. Rebuild with the split manifest and explicit replacement:

   ```bash
   python3 dataset/scripts/prepare_kodis.py build \
     --input-root dataset/raw/kodis \
     --adapter dataset/raw/kodis/kodis_adapter.local.json \
     --source-manifest dataset/raw/kodis/kodis_source_manifest.local.json \
     --split-manifest dataset/raw/kodis/kodis_splits.local.json \
     --secret-file /restricted/outside-repository/kodis-pseudonym.key \
     --output dataset/deidentified/kodis \
     --replace
   ```

9. Validate the raw receipt, controls, schema, regenerated records, dialogue lineage, component graph, split isolation, reports, hashes, and permissions:

   ```bash
   python3 dataset/scripts/validate_kodis.py \
     --input-root dataset/raw/kodis \
     --output dataset/deidentified/kodis \
     --adapter dataset/raw/kodis/kodis_adapter.local.json \
     --source-manifest dataset/raw/kodis/kodis_source_manifest.local.json \
     --split-manifest dataset/raw/kodis/kodis_splits.local.json \
     --secret-file /restricted/outside-repository/kodis-pseudonym.key \
     --validation-report dataset/deidentified/kodis/validation_report.json \
     --replace-report
   ```

The output directory must contain only `records.jsonl`, `linkage_groups.jsonl`, `build_report.json`, and optionally `validation_report.json`; it must be mode `0700`, with files mode `0600`. Rebuilding invalidates an existing validation report.

## Retained data and dialogue rules

The restricted records retain only:

- keyed pseudonymous file, conversation, participant, message, and linkage-component identifiers;
- normalized buyer or seller role;
- ordered message text after transparent pattern masking;
- up to three preceding pseudonymous message references and an optional backward reply reference;
- keyed text fingerprints and ordinal source-row/turn lineage;
- a component-level split label; and
- privacy-review and sampling status.

Every other verified input field must be explicitly discarded. Structured country, demographics, personality/culture measures, surveys, preference justifications, compensation, precise timestamps, platform/worker IDs, model emotion labels, human-to-AI text, incomplete-dialogue text, and nonmessage event text do not enter the staged records.

The builder selects complete human-to-human conversations at the conversation level, then retains only verified message events. It requires at least eight integer-indexed messages, consecutive indices from one, buyer first, alternating buyer/seller roles, unique message IDs, and no exact duplicate complete dialogue. Missing or inconsistent interaction/completion markers fail the build; they are never inferred from words in the conversation.

Automatic masks cover URLs, emails, IPv4 addresses, handles, phone-like numbers, and numeric exact dates. They do not reliably remove names, organizations, schools, street addresses, demographics stated in free text, precise times written in prose, unusual biographies, or searchable phrases.

The outputs are restricted and pseudonymized, not anonymous. Every message remains `privacy_review_status: pending`, `manual_excerpt_review_required: true`, and `eligible_for_packet_sampling: false`. A documented two-person contextual review and a separately approved promotion workflow are required before any rating, modeling, quotation, or release use. That promotion workflow is intentionally not implemented here.

## Synthetic fixture

The shipped fixture is fictional and checksum-bound to its exact input, adapter, source receipt, split manifest, and dedicated output area. It contains:

- three complete human-to-human conversations with eight retained messages each;
- one fictional participant linking two conversations into a 16-message component;
- a separate eight-message component;
- one human-to-AI conversation, one incomplete human-to-human conversation, and one system event that are quarantined; and
- synthetic structured survey, demographic, timestamp, worker-ID, preference, and model-label fields used only to test exclusion.

Build and validate it with:

```bash
python3 dataset/scripts/prepare_kodis.py build \
  --input-root dataset/fixtures/kodis_synthetic/package \
  --adapter dataset/manifests/kodis_demo_adapter.json \
  --source-manifest dataset/manifests/kodis_demo_source_manifest.json \
  --split-manifest dataset/manifests/kodis_demo_split_manifest.json \
  --output Storage/synthetic-results/dataset-demos/kodis_demo \
  --demo --replace

python3 dataset/scripts/validate_kodis.py \
  --input-root dataset/fixtures/kodis_synthetic/package \
  --output Storage/synthetic-results/dataset-demos/kodis_demo \
  --adapter dataset/manifests/kodis_demo_adapter.json \
  --source-manifest dataset/manifests/kodis_demo_source_manifest.json \
  --split-manifest dataset/manifests/kodis_demo_split_manifest.json \
  --demo \
  --validation-report Storage/synthetic-results/dataset-demos/kodis_demo/validation_report.json \
  --replace-report

python3 -m unittest dataset/tests/test_kodis_pipeline.py
```

The synthetic split labels are demonstration fixtures, not preregistered real-corpus assignments.

## Exactly what remains blocked

Until authorized access is granted and the received package is inspected, none of the following is complete:

- current written access approval, agreement version, authorized users, and verified local/model/rater processing scope;
- authoritative archive/file inventory, package version, receipt date, sizes, hashes, and observed counts;
- actual file format, field names, row granularity, conversation/message order, and system-event semantics;
- reliable human-to-human, completion, message-event, and buyer/seller mappings;
- verification of a globally person-stable participant key or another approved linkage mechanism;
- the real complete-dialogue set, duplicate diagnostics, conversation-participant graph, components, preregistered assignments, and split sizes;
- real preprocessing, masking totals, schema/bundle validation, and sampling eligibility;
- two-person contextual privacy review and any separately approved eligibility-state changes;
- institutional/ethics confirmation for the intended processing, retention/deletion controls, model or rater exposure, quotation, and redistribution; and
- every KODIS-dependent WarrantRoute result.

Do not state that the governed KODIS workflow is prepared, de-identified,
validated, anonymous, or cleared for experiments while these gates remain
unresolved. The separately documented private exploratory bundle is a minimal,
unsplit local conversion and does not satisfy or bypass these gates.
