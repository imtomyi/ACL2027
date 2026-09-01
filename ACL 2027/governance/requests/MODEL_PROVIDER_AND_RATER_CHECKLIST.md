# Model-provider and human-rater checklist — draft, not approval

Use this checklist to collect evidence; it does not authorize protected text to leave restricted storage. Every corpus remains blocked unless the exact provider endpoint and every human/service role are separately in scope, current, and recorded in `governance/local/`.

## Model endpoint evidence

Create one `MEP_…` profile for each distinct provider/tenant/product/endpoint/model/region combination. Do not store keys, credentials, account emails, contract text, or source text in the profile.

- [ ] Provider legal/service name.
- [ ] Pseudonymous or non-secret account/tenant reference.
- [ ] Product or endpoint name and endpoint region.
- [ ] Exact model ID and immutable snapshot/revision.
- [ ] API version.
- [ ] Provider terms version and privacy/data-processing terms version.
- [ ] Explicitly approved corpus IDs and protected-data classification.
- [ ] Training use is explicitly disabled; “default,” “may opt out,” or silence is not sufficient evidence.
- [ ] Retention mode and exact retention days.
- [ ] Deletion behavior, including logs/backups and deletion verification.
- [ ] Human-access/abuse-monitoring conditions.
- [ ] Subprocessors reference and processing region.
- [ ] Approval effective date, expiry/re-review date, and last version-verification date.
- [ ] Institutional/source/platform permission covers this exact endpoint and use.

Recheck the profile when the model snapshot, API, terms, region, tenant, retention, abuse-monitoring, subprocessors, or purpose changes. A model provider’s technical availability or account setting is not project approval.

## Model-use controls

- [ ] Only excerpts and context cleared by two current privacy reviewers may be sent.
- [ ] Prompts contain no raw source identifiers, unnecessary context, credentials, or reviewer identities.
- [ ] Logging, tracing, caching, feedback, fine-tuning, and training paths are disabled or separately approved and recorded.
- [ ] Output storage and deletion follow the strictest institution/source/platform/provider rule.
- [ ] Model outputs are treated as potentially identifying and remain restricted until reviewed.
- [ ] No provider endpoint is used for a corpus absent from its `approved_corpora` list.

## Pseudonymous reviewer registry

The tracked and local registries contain pseudonyms only. Use IDs matching `REV_[A-Z0-9]{8,32}`. Keep the name/email/signature-to-ID crosswalk outside the repository in the approved restricted identity system and store only its non-sensitive reference locally.

For every reviewer, record:

- [ ] Status (`pending`, `active`, `expired`, or `withdrawn`).
- [ ] Approved roles, such as `privacy_reviewer` or an exact rater role named in the gate.
- [ ] Approved corpus IDs.
- [ ] Privacy-training version.
- [ ] Confidentiality-acknowledgment version.
- [ ] Approval effective date, expiry/re-review date, and last version-verification date.

Do not record names, emails, signatures, account handles, free-text notes, or source-derived details in the JSON registry.

## Two-person contextual privacy review

- [ ] Every candidate excerpt and sufficient surrounding context has one text-free record.
- [ ] Packet IDs match `PKT_[A-Z0-9]{8,32}` and excerpt IDs match `EXC_[A-Z0-9]{8,32}`; neither encodes a raw source ID.
- [ ] Context is represented only by an approved manifest/hash, never copied text.
- [ ] At least two distinct, active `privacy_reviewer` IDs are current for the corpus.
- [ ] Review timestamp and separate model-processing, rater-display, and quotation decisions are recorded.
- [ ] Rejected excerpts are excluded; one use permission never implies another.
- [ ] Self-disclosed PII and contextual reidentification risks are evaluated, not merely pattern-matched.

## Rater/service authorization

- [ ] Institution/source/platform permits the exact human exposure and displayed context.
- [ ] If a rater vendor or platform is used, the contract names data location, subprocessors, retention/deletion, access, incident reporting, reuse/training prohibition, and audit rights.
- [ ] Approved roles in the governance gate exactly match at least one current reviewer’s role and corpus scope.
- [ ] Least privilege, encryption in transit/at rest, access logging, session controls, and export/download restrictions are verified.
- [ ] Rater information sheet/consent, compensation, withdrawal process, support contact, and confidentiality obligations are versioned.
- [ ] Withdrawal or role expiry immediately removes access and triggers any required deletion/reassignment.
- [ ] Rater exports contain pseudonymous packet/excerpt IDs only and no source receipt IDs.

## Retention, deletion, and release handoff

- [ ] Project and provider deletion deadlines are future-dated and compatible with all agreements.
- [ ] Responsible pseudonymous `OWNER_…` ID, deletion procedure, verification method, backup handling, and incident-response reference are recorded.
- [ ] Release manifest enumerates exact permitted artifact classes; source text, prompts, ratings, and model outputs are not implicitly releasable.
- [ ] Quotation/release receives its own privacy, license/attribution, institution, and provider review.
- [ ] Expired or version-stale evidence blocks new model calls, rater sessions, quotation, and release.

No checkbox or template entry substitutes for the underlying institutional, source/platform, provider, rater, retention, or release evidence.
