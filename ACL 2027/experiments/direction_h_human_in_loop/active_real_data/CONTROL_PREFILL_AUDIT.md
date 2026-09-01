# Direction H control-prefill audit

Audit date: 2026-08-25

Scope: governance/configuration metadata only. No Dreaddit row, Reddit post,
AGYW transcript line, prepared record, excerpt, packet, fictional item, rating,
or result was opened or used for this audit.

## Files inspected

- Project governance template and restricted local governance status record.
- Text-free reviewer-registry and privacy-log templates/current status records.
- Dreaddit and AGYW source manifests: corpus/version, file names, hashes,
  declared split/role, license/handling statements, and aggregate receipt
  metadata only.
- Held-out-freeze and privacy-ledger templates.
- Direction H active-real-data index and reserved config/run indexes.

## Current machine state

| Control | Dreaddit | AGYW focus groups |
|---|---|---|
| `real_text_runnable` | `false` | `false` |
| Governance gate statuses | 10 pending | 10 pending |
| Source receipt manifest | present | present |
| Selection authorization template | pending/not authorized | pending/not authorized |
| Two-person privacy records | none | none |

The local record has no responsible owner ID. The reviewer registry contains no
reviewer entry, and the privacy log contains no review record. Restricted local
file permissions are correctly fail-closed (`0700` directory and `0600` JSON
files), but permissions alone do not authorize text access.

The controlling record's `gate_mode` is still `synthetic_only`. That is a
fail-closed readiness mode, not permission to use fictional data in Direction
H. The active Direction H scope separately records that fictional/synthetic
data are not authorized. The governance status must not be changed merely to
make a runtime proceed.

## Safely prefilled internal controls

The following are now proposed in
[`INTERNAL_CONTROLS_DRAFT.md`](INTERNAL_CONTROLS_DRAFT.md) and its
machine-readable companion:

- Real-only Direction H scope and held-out AGYW posture.
- Charlie's developer-researcher case-baseline designation.
- Separation among coordinator, privacy reviewers, case rater, independent
  confirmatory raters, model operator, data steward, and incident owner.
- Minimum model/rater payload and an allowlisted text-free operational log.
- No source material in this folder and pseudonymous IDs that cannot encode
  raw source identifiers.
- Blinding, no cross-rater visibility, frozen revision model, and no
  post-outcome prompt/model changes.
- A fail-closed retention/deletion procedure with exact deadlines deliberately
  unfilled.
- A stop/contain/notify/remediate incident procedure with the owner deliberately
  unfilled.
- Public release denied by default, with no currently permitted artifact
  class.

## Items that were not and cannot be prefilled

- Institutional determination, authority, version, or dates.
- Reddit/platform authorization for the held Dreaddit receipt and exact uses.
- Provider/endpoint/model-processing approval or settings.
- Owner/reviewer identities, consent, training, confidentiality, role dates,
  or expiry dates.
- Privacy decisions for any excerpt or context.
- Sampling counts, power basis, random seed, candidate selection, or packet
  hash.
- Frozen task/prompt/model/outcome/analysis hashes.
- Exact project/provider retention deadlines and backup/legal-hold rules.
- Any quotation, attribution, artifact class, or public-release permission.

These values require a real decision or evidence and must not be generated from
checklist completion, corpus possession, a publication example, or the source
manifest.

## Minimal internal confirmation later

Once external scope exists, the coordinator can minimize administrative work
by confirming the proposed defaults as one versioned internal package, assigning
the required pseudonymous owners/reviewers, inserting the exact dates and
evidence references, and rerunning the readiness checker. Confirmation should
occur in the approved system or a restricted local record; this tracked audit
must remain text-free and unsigned.
