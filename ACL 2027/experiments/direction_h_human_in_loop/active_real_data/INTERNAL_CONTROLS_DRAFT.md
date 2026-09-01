# Direction H internal controls — proposed defaults

Status: **draft for internal confirmation; not authorization to access, display,
rate, or process real text**.

This document prefills the operational controls the WarrantRoute team can
decide without reading either corpus and without representing that an
institution, source/platform, provider, or rater service has approved the
study. It contains no source text, raw source identifiers, participant
identifiers, reviewer identities, credentials, ratings, or results.

The controlling readiness record remains
`governance/local/project_governance.local.json`. Nothing in this draft changes
its gate statuses. The machine-readable companion is
[`configs/internal_controls.draft.json`](configs/internal_controls.draft.json).

## Scope and fixed posture

- Active corpora: real Dreaddit and real `agyw_focus_groups` only.
- Fictional or synthetic data: not authorized for this active lane.
- Real-text access: remains disabled until the corpus-specific readiness check
  passes every required gate at the intended execution time.
- Dreaddit roles: official train is proposed for development/pilot; official
  test is reserved for an in-domain audit after development choices freeze.
- AGYW role: held-out cross-domain confirmation. No AGYW text or source-derived
  output may influence prompts, packet construction, controlled defects,
  thresholds, model selection, stopping, outcomes, or analysis code.
- Charlie's role: developer-researcher case rater. His ratings are a
  researcher-in-the-loop baseline, not universal human ground truth and not the
  independent confirmatory panel.

## Responsibility separation

The following role labels are prefilled; the authorized system must assign
pseudonymous `OWNER_...` or `REV_...` IDs and preserve the identity crosswalk
outside the repository.

| Role | Minimum responsibility | Separation rule |
|---|---|---|
| Accountable PI/institutional authority | Confirms institutional scope and delegates operational ownership | Cannot be inferred from a checklist or this draft |
| Data steward | Controls corpus receipt, storage permissions, approved field extraction, and deletion verification | Does not decide publication permission alone |
| Study coordinator | Freezes task, sampling, prompts, model, outcomes, blinding, and assignments | Must not expose condition labels or repair outcomes to raters |
| Privacy reviewer A | Reviews every proposed excerpt and displayed context for each permitted use | Must be distinct from reviewer B and current for the corpus |
| Privacy reviewer B | Independently performs the same contextual review | Must be distinct from reviewer A and current for the corpus |
| Charlie case rater | Independently rates blinded evidence-linked outputs and records structured feedback | Cannot be treated as an independent confirmatory reviewer because of development involvement |
| Independent confirmatory rater | Rates the frozen confirmatory extension under the same item schema | Must not have participated in system development or see Charlie/model ratings |
| Model operator | Runs only the frozen, approved endpoint and passes the frozen feedback payload to the revision model | Cannot change the model, prompt, or payload after outcome access |
| Incident owner | Coordinates stop, containment, notification, and verified recovery | Must be assigned before any real-text access |

No person receives corpus access merely by occupying one of these roles. Corpus
scope, training/confidentiality status, effective dates, and expiry dates must
also be current in the restricted governance records.

## Data-minimization defaults

### Restricted preparation

1. Keep authoritative corpus files and any source-derived working records out
   of this Direction H folder.
2. Preserve the source manifests and exact file hashes without opening corpus
   records during governance or configuration checks.
3. Create only project-pseudonymous packet and excerpt identifiers; never
   encode a post ID, filename, focus-group number, speaker label, username, or
   participant attribute in those IDs.
4. Preserve complete source clusters: Dreaddit post; AGYW focus group and
   transcript-local speaker. A repeated speaker label in different focus
   groups must never be treated as one identity.
5. Exclude direct source identifiers, timestamps, engagement data, names,
   contact details, URLs, account handles, credentials, and identity-crosswalk
   material from model and rater payloads.

### Model payload

Only after authorization and two-person contextual privacy review, a payload
may contain the minimum cleared excerpt/context, blinded evidence links,
frozen task instructions, and a project-pseudonymous item ID. Do not include
sampling strata, corpus filenames, experimental condition, gold/benchmark
labels, Charlie's identity, other raters' decisions, or downstream outcomes.
Provider logging, tracing, feedback, caching, fine-tuning, and training paths
remain off unless the exact path is separately documented and approved.

### Human-review webpage

The page may expose only the assigned cleared packet and frozen rating form.
Downloads, copy-oriented exports, source navigation, condition labels,
cross-rater ratings, and repair outcomes remain disabled. The page records the
structured rating, error flags, disposition, rationale, confidence, and active
review time using pseudonymous IDs. Rationale instructions must ask reviewers
to point to evidence identifiers and paraphrase where possible; rationales are
still restricted because they can reproduce source wording.

### Logs and exports

Operational logs contain only pseudonymous event, packet, excerpt, reviewer,
endpoint-profile, and run IDs; event timestamps; success/failure codes; and
durations. They must not contain prompt bodies, excerpts, rationales, model
outputs, raw source IDs, names, emails, IP addresses, credentials, or browser
session material. Any necessary security log with additional fields belongs in
the separately approved restricted system, not this repository.

## Retention and deletion proposal

This is a fail-closed procedure proposal, not a completed retention gate.
Exact project and provider deletion dates remain blank until the strictest
institutional, source/platform, and provider requirements are known.

1. Before first access, the data steward records the approved locations,
   artifact classes, backup behavior, responsible `OWNER_...` ID, deletion
   method, verification method, and future project/provider deadlines.
2. Retain only artifacts required for an approved analysis or audit. Disable
   browser downloads and ad hoc local copies by default.
3. Apply the earliest applicable deletion/expiry trigger across institution,
   source/platform, provider, protocol, rater role, and project closeout.
4. On expiry, withdrawal, or scope change, block new sessions and model calls,
   quarantine affected derivatives, and follow the approved deletion or
   reassignment procedure.
5. Verify deletion through a metadata-only inventory plus the approved storage
   or provider confirmation. Record the verification reference, not deleted
   text or credentials.
6. Never delete an authoritative source receipt or institutional record solely
   on the authority of this draft; the designated owner follows the approved
   schedule and backup/legal-hold requirements.

## Incident response proposal

An incident includes unauthorized text access or export, use of the wrong
endpoint/model/snapshot, text appearing in logs, a permissions failure,
credential or device compromise, cross-condition unblinding, or attempted
release outside an approved manifest.

1. Stop the affected rater sessions, model calls, exports, and releases.
2. Revoke or suspend affected access without copying protected material into a
   ticket, chat, or repository issue.
3. Preserve metadata-only event records and quarantine affected derivatives in
   the approved restricted location.
4. Notify the assigned incident owner, who follows institutional and provider
   notification timelines and decides whether broader reporting is required.
5. Determine scope using approved logs; do not inspect additional corpus text
   merely to investigate.
6. Delete, remediate, or re-review affected artifacts as directed; rotate
   credentials outside the repository where applicable.
7. Resume only after the incident owner records containment, any required
   notifications, corrective action, and a current readiness recheck.

## Release default

**No artifact is approved for public release by this draft.** In particular,
source text, excerpts/context, packet files, source-derived prompts, item-level
model outputs, item-level ratings, rationales, feedback, repair outputs,
review-time events, linkage tables, and identity/access records are restricted
by default.

Possible future release candidates are limited to code that contains no source
material, empty schemas/templates, documentation, and privacy-reviewed
aggregate statistics. Even these require an exact versioned release manifest,
license/attribution review, institutional scope, and the corpus-specific
release gate. Aggregate cells must be suppressed or combined when they risk
revealing a person, post, speaker, group, excerpt, rater, or source wording.

## Changes that force a new freeze and readiness check

- Corpus receipt, file hash, split, field contract, cluster rule, or intended
  role changes.
- Packet content/context, task, rubric, rating construct, error taxonomy,
  outcome definition, blinding, assignment, or sampling changes.
- Provider, tenant, endpoint, region, model snapshot, API, terms, retention,
  monitoring, subprocessor, logging, or caching changes.
- Rater role, rater service, access mechanism, training, consent,
  confidentiality, or withdrawal changes.
- Retention, deletion, incident, quotation, attribution, or release-scope
  changes.
- Any held-out AGYW access before the documented pre-access freeze.

## Fields intentionally not prefilled

The following cannot be truthfully supplied from internal design decisions:
institutional determination reference; Reddit/platform authorization;
corpus-specific provider permission; accountable owner and reviewer IDs;
endpoint profile; exact effective/expiry dates; approved retention deadlines;
privacy-review decisions; frozen-manifest hashes; sampling counts; and
permitted release classes. They remain pending and must not be inferred from
corpus possession, publication precedent, a public license, or a completed
checklist.
