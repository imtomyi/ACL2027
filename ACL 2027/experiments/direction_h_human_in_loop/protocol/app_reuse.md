# Safe reuse of Warrant Study patterns

## Decision

Direction H will **not edit or run the shared Warrant Study app for the
synthetic pilot**. The existing app is wired to a protected real-item bank. Its
useful workflow patterns may be reimplemented in a Direction H-local,
synthetic-only adapter, but no real item, shared database, deployed endpoint, or
organizer response is an input to this direction.

The first Charlie session should remain file based. A small local interface is
optional only after the rating and feedback contracts are stable.

The ready reviewer-safe source is the frozen four-item queue in
`pilot/manifest.json`, `pilot/task_index.csv`, and `pilot/items/DHQ-001.json`
through `DHQ-004.json`. A collection interface may consume only this projection,
and only after `scripts/validate_artifacts.py --reviewer-safe` passes. It must
not reconstruct the queue from historical blinded bundles at review time.

## Patterns that can be reused

| Existing app location | Reusable pattern | Direction H use |
|---|---|---|
| `../../../app/feedback-collector-demo/lib/study-server.ts` | Server-side item lookup and a public projection; same-origin writes; no-store responses; bounded request size | Keep synthetic packets outside the client bundle and return only reviewer-safe fields. Reimplement locally without importing `study-data.ts`. |
| `../../../app/feedback-collector-demo/lib/study-server.ts` | Balanced assignment by base packet, one variant per base packet, least-used allocation, shuffled order | Use for later multi-rater synthetic sessions after a seed and allocation manifest are frozen. Preserve base-packet separation. |
| `../../../app/feedback-collector-demo/db/schema.ts` | Session, assignment, and review separation; uniqueness constraints; bounded review time | Create an isolated Direction H database or JSONL store keyed by rating and feedback IDs. Do not reuse the deployed D1 database. |
| `../../../app/feedback-collector-demo/app/api/study/review/route.ts` | Validate before insert, save after each item, prevent duplicate assignment submissions | Validate against the shared paper rating schema and Direction H feedback schema before an immutable first-pass insert. |
| `../../../app/feedback-collector-demo/app/api/study/start/route.ts` | Reviewer role, corpus familiarity, construction-involvement disclosure, consent/study versions | Retain these fields in a separate rater registry. Charlie must be marked construction-involved and analyzed as a developer-researcher case. |
| `../../../app/feedback-collector-demo/app/api/responses/route.ts` and organizer page | Analysis export with no source text or access secrets; spreadsheet-injection-safe CSV cells | Export IDs, ratings, flags, timing, and feedback links only. Keep source text and unblinding data out of reviewer/analysis exports. |
| Withdrawal route | Hashed withdrawal code and deletion of linked assignments/reviews | Reuse only if external human participants are recruited and the approved consent/withdrawal plan requires it. It is unnecessary for Charlie's internal synthetic qualification. |
| Participant UI | One packet at a time, source evidence before interpretation, explicit disposition and rationale | Preserve the sequence, but add all three paper metrics, metric-specific abstention, error flags/locations, and a separate feedback step. |

Security patterns are helpful but not evidence that protected-text processing is
authorized. An access code, server-only module, masked identifier, or restricted
database does not replace institutional/platform/model-processing approval.

## Schema gaps that must not be inherited

The current app predates `qc-paper-metrics-v1`. Its stored review row is not a
compatible Direction H or companion-rater record.

| Current app behavior | Required Direction H behavior |
|---|---|
| `support` | Export as the exact shared construct `evidential_credibility`. |
| `voice` | Export as `voice_boundary_preservation`, including dissent, counterevidence, minority/boundary cases, and contextual qualifications. |
| No scope item | Add independent 1--5 `scope_calibration`. Do not substitute analytic-contract fit. |
| One global `cannot_judge` switch | Use the shared per-metric `cannot_judge` array; only listed metrics are null. |
| Global abstention also nulls confidence | Always collect 1--5 reviewer confidence, including when one or more quality metrics cannot be judged. |
| No serious-error field | Collect the shared error-flag enum and source/output locations in the linked feedback record. |
| Optional rationale | Require a nonempty concise rationale, as the shared schema does. |
| `review_time_ms` only | May be captured internally in milliseconds, but export `review_seconds` as a nonnegative number with the conversion documented. |
| App-specific role strings | Export the exact `evaluator_group` enum. Charlie is `researcher`; construction involvement remains separate. |
| No corpus/evaluation/output/version keys | Add `annotation_version`, `rater_id`, `packet_id`, `corpus_id`, `evaluation_role`, `output_id`, and `rated_at_utc`. |
| Escalation-specific app coupling | Do not add constraints beyond the shared schema and frozen protocol. Keep `disposition` and `requested_expertise` semantically comparable with the companion direction. |
| Rationale doubles as feedback | Keep the rating rationale and revision-model feedback as separately versioned, linked records. |
| No repair experiment entities | Use Direction H `revision_case`, `revision_output`, and `repair_assessment` records with a frozen revision manifest. |

The canonical rating schema remains
`../../qualitative_coding_baselines/schemas/paper_metric_rating.schema.json`.
Direction H must not fork it. Companion-specific linkage and revision fields
belong in the local schemas described by `companion_alignment.md`.

## Fail-closed synthetic adapter plan

Implement any future adapter entirely below
`experiments/direction_h_human_in_loop/`. It should have two physically and
logically separate lanes.

### Reviewer lane

Inputs are allowlisted to:

1. `../../qualitative_coding_baselines/benchmark/synthetic_packets_v1.json`; and
2. the matching `../../../Storage/synthetic-results/model-qualification/20260825_synthetic_qualification/blinded/syn_*_run*.json` bundles.

The adapter must reject an input unless all of the following hold:

- benchmark ID is `qc-synthetic-v1`;
- provenance states that the text is entirely fictional;
- packet status is `synthetic_proxy_not_corpus_result`;
- packet ID begins with `syn_`;
- the bundle contains only blind candidate IDs plus qualitative outputs;
- the packet/bundle hashes match the frozen adapter manifest; and
- no unknown path, symlink, URL, arbitrary import root, or `dataset/` path is
  accepted.

Reviewer output contains only the analytic question/contract, bounded fictional
source excerpts and IDs, one blinded candidate, stable packet/output IDs, and
display-order metadata. Strip and reject `model_id`, judge fields, failure or
condition labels, `truth_record`, expected ratings/dispositions, and unblinding
keys. Never join the shared private blind map.

The current projection is already materialized as `pilot/items/DHQ-001.json`
through `DHQ-004.json`, with opaque `DHO-*` output IDs and no source-run or blind
candidate identifiers. Charlie and any Direction H-local interface use those
files, not the adapter inputs above. If the projection and frozen manifest do
not validate together, stop rather than falling back to a shared source bundle.

Construct opaque output IDs without model, run, or source blind identity, such
as the frozen queue's `DHO-K7R4`. Record the adapter version, input hashes, seed,
schema versions, output count, and creation time in a synthetic build manifest.
The reviewer queue and response files should live under a reviewer-specific
folder with no coordinator-only siblings.

### Coordinator lane

Controlled qualification truth belongs only in the separate coordinator-held
map conforming to `truth_map.schema.json`. The reviewer-safe `pilot_item` schema
forbids `truth_record` and other condition fields; do not create a richer pilot
item that adds them back. The truth map must never be served, copied, or embedded
in the reviewer queue. Revision cases given to the frozen model must conform to
`revision_case.schema.json`, which also omits coordinator truth.

Keep the following separate:

- reviewer-safe item and display order;
- Charlie's locked paper-metric rating;
- Charlie's linked formatter-ready feedback;
- the no-feedback versus Charlie-feedback assignment;
- frozen revision manifest and model outputs;
- coordinator truth/unblinding;
- blinded R/P/C/Y repair assessments; and
- exact post-revision `qc-paper-metrics-v1` rows plus their local hash links.

Join them only after annotation lock, using opaque IDs in the analysis step.
Charlie does not need access to the coordinator lane.

## Local collection flow

If a Direction H-local interface is later useful, its minimum flow is:

1. Create a session from the synthetic reviewer queue and rater registry.
2. Show one evidence packet/candidate at a time with no model or condition data.
3. Start item timing when the complete item becomes visible; pause or flag
   inactive intervals under a frozen rule.
4. Collect the exact paper rating record.
5. Collect a separate feedback record tied to the same packet, output, rater,
   and rating identifiers.
6. Validate both records, then append them immutably before advancing.
7. Prevent silent edits; represent a correction as a timestamped amendment.
8. Export source-free analysis tables and a validation report.

For a confirmatory extension, add seeded incomplete-block assignment,
twin-pair separation, repeat-item reliability checks, accessibility testing,
approved consent/withdrawal, and at least the preregistered independent ratings
per role. Do not infer confirmatory readiness from the synthetic Charlie pilot.

## Verification checklist

Before using an adapter or interface, verify that:

- a repository search of reviewer assets finds no `model_id`, `truth_record`,
  private-map rows, expected outcome, judge score, or real corpus record ID;
- public/client assets contain no source packet text unless the packet is one of
  the allowlisted fictional benchmark packets;
- every reviewer item traces to one hashed synthetic bundle and one blind ID;
- every rating passes the unchanged paper-metric schema;
- every feedback/revision/repair record passes its Direction H schema;
- no output ID appears twice for the same rater and annotation version;
- no-feedback and Charlie-feedback cases use the same frozen revision model,
  prompt, decoding configuration, and formatter except for the feedback input;
- repair assessors cannot see feedback condition, Charlie's identity, or
  coordinator truth; and
- no shared app, dataset, or baseline artifact was modified.

## Real-data boundary

There is no generic switch that turns this adapter into a real-data collector.
Real corpora require a separate approved runner and signed fail-closed manifest
naming the corpus, split, fields, provider, retention/deletion mode, approval
scope/date, rater-exposure permission, and completed excerpt review. Until those
gates are satisfied, Direction H remains synthetic only and the shared real-item
app stays untouched.
