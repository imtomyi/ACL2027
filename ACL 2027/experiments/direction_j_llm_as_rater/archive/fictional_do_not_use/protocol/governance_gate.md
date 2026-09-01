# Direction J governance gate

Version: `direction-j-governance-gate-v1`  
Status: synthetic-only; no protected real text is authorized for Direction J

## Purpose

This gate governs every Direction J run in which an LLM acts as a first-stage
judge and every paired human-comparator run that receives the same packet. It
inherits the WarrantRoute dataset controls and fails closed. A public download,
an upstream ethics approval, prior masking, or successful schema validation is
not permission for this project to send text to a model or show it to a rater.

The only currently runnable lane is synthetic qualification. Synthetic packets
must be fictional, must carry a manifest assertion that they contain no real
source text, and must not be derived by paraphrasing a protected source excerpt.
Synthetic results are engineering evidence only and must never be pooled with or
described as results for Dreaddit, CaCHe/AGYW, KODIS, or CANDOR.

Synthetic labels alone are insufficient. The qualification builder must verify
the exact benchmark hash and its independent-fictional-authorship provenance,
the exact 12-file blinded-bundle set and each bundle hash, and byte equality
between every bundled packet and the frozen benchmark packet before it exposes
text. It writes a hashed synthetic source receipt into the build and run
manifests; analysis must remain bound to that receipt, the evaluator-bank hash,
the build-report hash, and the current freeze.

## Fail-closed rule

Before a runner reads, samples, serializes, logs, uploads, or displays any
protected real text, copy `config/governance_gate.template.json` to a restricted,
untracked local approval record and complete it from documentary evidence. The
template itself is intentionally blocked and is never an approval record.

A real-text run is permitted only when all of the following are true:

1. `gate_mode` is `real_text_authorized`, `real_text_gate.decision` is
   `approved`, and both `runnable` and `all_requirements_satisfied` are `true`.
2. Every object in `real_text_gate.requirements` has `status: "approved"`, a
   nonempty evidence reference, a named approval authority, and a dated approval
   that is still in force.
3. The selected corpus lane is explicitly `authorized`, its exact version,
   split, role, file hashes, and allowed fields match the run input, and no
   optional or held-out lane is used outside its frozen role.
4. The provider, product or endpoint, exact model snapshot, retention mode,
   deletion behavior, abuse-monitoring or human-access conditions, training-use
   setting, subprocessors, and region are the approved values. Direction J
   requires provider training on protected text to be disabled. Any change in
   provider, endpoint, model snapshot, or terms closes the gate until reapproval.
5. Every excerpt and its minimum necessary local context appear in the approved
   packet manifest and have two distinct documented privacy reviewers. Automatic
   masking or a directory named `deidentified` is not sufficient.
6. Sampling preserves the declared source clusters, and the frozen packet,
   prompt, schema, judge, repetition, blinding, leakage, aggregation, analysis,
   and access-log hashes all match the run manifest.
7. Storage, access, retention, deletion, withdrawal where applicable, and release
   controls are documented and active. Release clearance is separate from
   processing clearance.

Any absent required field, unresolved `null`, expired approval, mismatched hash,
unknown status, or unverified assertion means **stop before reading the input**.
A runner must not offer an override flag, silently fall back to a broader field
set, or treat an operator confirmation as documentary approval.

## Required documentary evidence

| Gate | Minimum evidence |
|---|---|
| Institutional determination | Project-specific determination covering secondary use, protected-text model processing, the LLM-judge study, and human rater exposure; reference, scope, authority, date, and expiry or continuing-status check. |
| Source and platform authorization | Corpus terms and version plus any required source-owner or platform confirmation. Dreaddit requires a documented institutional and Reddit/platform basis; CaCHe's CC BY license and source-study approvals do not replace this project's determination. |
| Provider and model processing | Approved provider, product/endpoint, model snapshot, contractual terms version, retention and deletion mode, training disabled, provider human-access/abuse-monitoring terms, subprocessors, region, and approved data classification. |
| Exact input contract | Corpus, received version, split, experimental role, source hashes, allowed fields, prohibited fields, context limits, and purpose. |
| Excerpt privacy review | Frozen excerpt/packet manifest; two distinct reviewers for every excerpt and displayed context; direct-identifier masking; contextual-risk decision; quotation and rater-display permission. |
| Cluster-aware sampling | Preregistered sampling plan and hash; Dreaddit clustered by post; CaCHe clustered by focus group and transcript-local speaker; no source cluster split or turn-level independence claim. |
| Frozen study manifest | Packet manifest, judge prompt/schema, primary judge and snapshot, repetitions, decoding, retry/repair policy, blinding, leakage controls, aggregation, analysis code, and freeze timestamp. |
| Rater and service access | Named approved roles/users, least-privilege storage and service access, production consent and withdrawal procedure for humans, encryption, and access logging. |
| Retention and deletion | Project and provider retention deadlines, deletion procedure, deletion verification, incident response, and responsible owner. |
| Release | Exact releasable fields and artifacts, source/platform/license basis, privacy review, treatment of rationales and ratings, and prohibition on source-derived text or short hashes unless separately cleared. |

Approvals do not transfer between corpora, providers, model products, study roles,
or deployments. A model-processing approval does not authorize rater display or
release, and a rater-display approval does not authorize model processing.

## Reconciled Direction J corpus scope

Direction J uses the current two-corpus confirmatory design:

- **Dreaddit official train** is the development lane. Only an authorized,
  eligible, privacy-reviewed subset may inform judge selection, prompting,
  thresholds, or qualification.
- **Dreaddit official test** is a secondary in-domain audit. It remains blocked
  until the primary judge, prompt, schema, repetitions, aggregation, outcomes,
  and analysis are frozen on development data.
- **All 11 CaCHe AGYW/community-men focus groups** are the held-out cross-domain
  confirmatory lane. No CaCHe text, model output, published theme, human rating,
  or outcome may influence judge selection, prompting, thresholds, packet rules,
  stopping rules, or outcome definitions. Here `held out` describes this study's
  procedure; it does not mean model-unseen or absent from training data.
- **KODIS and CANDOR** are optional sensitivity lanes only. Both remain blocked
  pending authorized real distributions, version-specific adapters and
  validation, privacy review, preregistered roles and splits, and all gates above.
  They are not part of the primary two-corpus design and cannot substitute for a
  failed or unavailable confirmatory lane.

## Explicit prohibition on the current app item bank

Do not read, copy, prompt with, export, or otherwise use the exact Dreaddit text
embedded in `app/feedback-collector-demo/lib/study-data.ts` for Direction J. The
app's statements that excerpts were screened or are for approved raters do not
document the institutional, Reddit/platform, provider/model, hosting, retention,
or rater-access gates required here. The item bank is therefore protected and
out of scope until a complete local approval record passes this gate. Direction
J synthetic runs must use only the fictional qualification packets or new
independently authored synthetic fixtures.

Local filesystem readability is not authorization. Direction J scripts must
hard-allowlist synthetic paths in synthetic mode and must reject paths under
`dataset/raw/`, `dataset/deidentified/`, `dataset/agyw_focus_groups/`, and
`app/feedback-collector-demo/lib/study-data.ts` before opening them.

## Machine-check behavior

The machine check must run before input discovery. It must:

1. parse the local approval record and reject the tracked template filename;
2. require the exact gate version, the exact ten requirement IDs in the template,
   and statuses drawn only from `pending`, `approved`, `rejected`, or `expired`;
   reject unknown properties or status values;
3. evaluate every required gate rather than trusting the summary booleans;
4. compare the requested corpus, version, split, fields, provider, model snapshot,
   and artifact hashes with the approved values;
5. verify two distinct privacy-reviewer records for every packet excerpt;
6. verify the corpus-specific cluster unit and frozen-role constraints;
7. write only a text-free gate receipt containing the decision, approval-record
   hash, manifest hashes, and timestamps; and
8. stop before input access on any failure.

The approval record may contain internal references but must not contain source
text, raw identifiers, access secrets, participant identities, or provider keys.

## Current first run

Run Direction J only on the existing fictional synthetic qualification material.
Record the synthetic packet hash, judge prompt and schema hashes, model snapshot,
independent judge-repetition index, usage, latency, cost, and output hash. Label
every result `synthetic_qualification_only`. No current synthetic score is an
empirical real-corpus result or evidence that the real-text gate has been met.
