# Dreaddit pilot input contract — version 0.1, pending approval

Status: **prospective draft; not authorization to open, sample, display, or
process real text**.

## Bound source

- Corpus: Dreaddit.
- Source snapshot: author archive downloaded 2026-08-25.
- Source manifest: `dataset/manifests/dreaddit_source_manifest.json`.
- Source-manifest SHA-256:
  `ac67c5ff5a643fe11a76a51d075febaceecdd7d5de550f9d61c6f6dd0b12195f`.
- Pilot split: official training split only.
- Experimental role: development and variance/timing pilot only.
- Official training rows: 2,838.
- Content-rule-eligible training rows before exact-date quarantine: 2,817.
- Exact-date quarantine audit SHA-256:
  `dc8fc4ba422d443ea5e11cf309b22c242d32cc027ec6965157dc98decca4f9c6`.
- Content-rule pool after complete-post exact-date quarantine: 2,804 records.

## Permitted working fields

- Project-pseudonymous record and post/source identifiers.
- Official split.
- Minimally masked text selected under the approved sampling plan.
- Only the context required by the frozen packet-construction rule.
- Sampling strata needed to balance the pilot.
- Restricted provenance needed to verify source fidelity.
- Eligibility, masking, and privacy-review status.
- Stress label and subreddit only as sampling/audit variables; neither may be
  presented as thematic truth or exposed to the router.

## Prohibited fields and uses

- Original Reddit post identifiers, account identifiers, timestamps,
  engagement metadata, precise dates, the released confidence field, LIWC/DAL
  features, and other unused columns.
- Reidentification, participant contact, model training/fine-tuning,
  redistribution, commercial use, or use outside this pilot.
- Model processing, rater display, quotation, or release unless each use has
  separate affirmative institutional, platform/source, provider, and privacy
  approval.
- Dreaddit test access for development or pilot decisions.
- AGYW/CaCHe access for this pilot.

## Purpose and outputs

The restricted input may be used only to estimate pilot variance, paired
discordance, review time, cannot-judge rates, exclusions, and instrument
behavior. Pilot records and source clusters are excluded from later evaluation.
Permitted public outputs are limited to aggregate, non-text statistics and
project-authored schemas/code unless a later release review expressly approves
additional artifact classes.

## Approval fields

The institutional authority and PI must record the approved evidence reference,
version, scope, effective date, expiry/re-review date, and authority identifier
outside this tracked draft. Until then, the corresponding governance gate
remains `pending`.
