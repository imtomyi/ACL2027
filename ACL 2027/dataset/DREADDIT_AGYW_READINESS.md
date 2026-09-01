# Dreaddit and CaCHe/AGYW experiment-readiness workflow

## Current verdict

The pinned Dreaddit and AGYW working bundles are available for the active
single-user `personal_local_only` diagnostic lane. That lane uses only a
loopback local model and restricted `Storage/` output. It does not permit human
review, external services, publication, submission, quotation, redistribution,
or release.

The candidate/privacy-review workflow below is retained for a future formal or
publication study. Its ten external gates are not applicable to the personal
lane, and its formal `real_text_ready` signal remains false.

The readiness tooling in this workflow does not rewrite the canonical bundles and can
never mark an item experiment-ready. It produces only restricted candidate/review
artifacts that remain fail closed while human and external gates are pending. Treat
all source-derived text as restricted and pseudonymized, not anonymous.

Validate the checked-in, text-free readiness audits from the workspace root:

```bash
python3 dataset/scripts/validate_dreaddit_agyw_review.py audits
```

This command recomputes the Dreaddit date audit from the canonical Dreaddit working
copy. It validates the AGYW 106/107 reconciliation against the existing text-free
aggregate build report, so it does not open the held-out AGYW transcript records.

## What the workflow enforces

- Dreaddit candidates are sampled as complete eligible post clusters.
- AGYW candidates are sampled as complete eligible
  `(focus group, transcript-local speaker)` clusters. The same label in two focus
  groups is never treated as the same person.
- Candidate order is deterministic for the same private or preregistered seed. The
  manifest stores only the seed's SHA-256 digest.
- A numeric or month-name exact date in an excerpt, preceding displayed turn, or
  moderator question quarantines the entire candidate cluster. Canonical text is not
  silently changed.
- Held-out candidate selection is rejected before the records file is opened unless
  the local control binds the exact inputs, seed, plan, packet rules, prompt, model
  snapshot, outcome definitions, and analysis code to a completed pre-access freeze.
- Review packets contain the restricted excerpt and displayed context. The separate
  ledger contains hashes and project-local IDs only: no excerpt text, raw source IDs,
  or free-form reviewer notes.
- Every ledger item requires two distinct pseudonymous reviewers. A local two-person
  approval still leaves `experiment_use_ready` false because external governance is a
  separate gate.
- Runtime directories are mode `0700`; controls, manifests, packets, and ledgers are
  mode `0600`. Runtime artifacts belong under `dataset/deidentified/` and must not be
  committed or redistributed.

## Pre-access control

`dataset/manifests/dreaddit_agyw_heldout_freeze.template.json` is intentionally
pending and invalid for real selection. Copy it only to an untracked restricted name
under:

```text
dataset/deidentified/review_controls/<control-name>.local.json
```

Set its directory to mode `0700` and the file to mode `0600`. Complete it only from
documentary evidence; copying the template, knowing a checksum, or possessing a local
corpus is not authorization. The control must bind the canonical records and source
manifest hashes, requested cluster count, sampling-seed digest, and sampling-plan
digest.

Allowed lanes are:

| Corpus | Split | Held-out rule |
|---|---|---|
| `dreaddit` | `development_train` | Mark the held-out section not applicable; institutional and source authorization are still required. |
| `dreaddit` | `in_domain_audit` | Freeze before access. |
| `agyw_focus_groups` | `heldout_cross_domain_evaluation` | Freeze before any candidate-selection access to transcript text. |

For either held-out lane, `freeze_status` must be
`frozen_before_heldout_access`, the pre-freeze access log must be clean, and every
required artifact reference must be complete. Do not set
`authorized_for_local_candidate_selection` or any approval field while the evidence
is pending.

## Authorized future run

Choose the cluster count from the preregistered power analysis and expert-time budget,
not from an arbitrary fraction of a split. For comparable evaluation, use the same
preregistered base-packet target for Dreaddit audit and AGYW, while reporting each
corpus separately.

After all pre-access evidence exists, create a candidate manifest in a new restricted
run directory. This example is a command shape, not authorization to run it now:

```bash
python3 dataset/scripts/prepare_dreaddit_agyw_review.py sample \
  --corpus agyw_focus_groups \
  --split heldout_cross_domain_evaluation \
  --clusters <preregistered-cluster-count> \
  --seed <private-or-preregistered-seed> \
  --selection-control dataset/deidentified/review_controls/<control-name>.local.json \
  --output dataset/deidentified/review_workflows/agyw_focus_groups/<run-name>/candidate_manifest.json
```

Validate the deterministic selection before creating any review packet:

```bash
python3 dataset/scripts/validate_dreaddit_agyw_review.py candidate \
  --corpus agyw_focus_groups \
  --split heldout_cross_domain_evaluation \
  --clusters <preregistered-cluster-count> \
  --seed <private-or-preregistered-seed> \
  --selection-control dataset/deidentified/review_controls/<control-name>.local.json \
  --candidate-manifest dataset/deidentified/review_workflows/agyw_focus_groups/<run-name>/candidate_manifest.json
```

Then create the restricted packet and empty ledger beside the candidate manifest:

```bash
python3 dataset/scripts/prepare_dreaddit_agyw_review.py build-review-bundle \
  --corpus agyw_focus_groups \
  --split heldout_cross_domain_evaluation \
  --clusters <preregistered-cluster-count> \
  --seed <private-or-preregistered-seed> \
  --selection-control dataset/deidentified/review_controls/<control-name>.local.json \
  --candidate-manifest dataset/deidentified/review_workflows/agyw_focus_groups/<run-name>/candidate_manifest.json
```

The directory will contain:

- `candidate_manifest.json`: text-free selected and quarantined cluster inventory;
- `privacy_review_packets.jsonl`: restricted excerpts plus displayed context; and
- `privacy_review_ledger.json`: text-free decisions and content bindings.

Do not use `--replace` unless the exact target was reviewed and replacement is
intentional. A fresh run directory is preferable for a new plan, seed, or control.

## Two-person review contract

Each reviewer inspects the packet text and all displayed context, then records only a
pseudonymous `REV_*` identifier from the restricted project reviewer registry, UTC review time, decision, direct-identifier and
contextual-risk findings, and separate permissions for model processing, rater
display, and quotation. `notes_reference` must be null or an opaque
`review_note_` plus 16 lowercase hexadecimal characters pointing to a separately controlled evidence store; prose and
source identifiers are rejected from the ledger.

Reviewer IDs must be distinct for an item. One review, duplicate reviewer IDs,
unresolved risk under an approval decision, or any inconsistent stored aggregate
causes validation to fail. Permissions are the intersection of both approvals. A
rejection clears all permitted uses. Even when all items reach
`privacy_review_complete_local_governance_still_required`, the ledger and every entry
remain `experiment_use_ready: false`.

Validate a populated ledger with the same bound arguments:

```bash
python3 dataset/scripts/validate_dreaddit_agyw_review.py ledger \
  --corpus agyw_focus_groups \
  --split heldout_cross_domain_evaluation \
  --clusters <preregistered-cluster-count> \
  --seed <private-or-preregistered-seed> \
  --selection-control dataset/deidentified/review_controls/<control-name>.local.json \
  --candidate-manifest dataset/deidentified/review_workflows/agyw_focus_groups/<run-name>/candidate_manifest.json
```

The validator re-derives the candidate, packet bytes, content hashes, coverage, review
state, and permission intersection. A successful result confirms local integrity and
privacy-ledger consistency only; it is not external clearance.

## Dreaddit exact-date quarantine

`dataset/audits/dreaddit_exact_date_quarantine.json` is bound to the unchanged
Dreaddit records SHA-256. Detector version
`numeric-and-month-name-exact-date-v2` finds 13 directly matching records in 13 post
clusters. Complete-cluster quarantine removes 13 content-rule-eligible development
records and 3 audit records because three dated posts also contain another eligible
segment. The remaining content-rule pools are 2,804 development records and 712 audit
records.

These matches are not a complete identifier screen. Nonmatching records still require
two-person contextual review, and quotation/release remains separately blocked.

## AGYW 106/107 reconciliation

`dataset/audits/agyw_participant_reconciliation.json` binds the aggregate AGYW build
report and source manifest. The source reports 107 participants; the canonical build
report records 106 normalized transcript-local speaker keys. The difference remains
unresolved. The audit records three possible explanations only as unverified
hypotheses and forbids cross-focus-group identity inference and complete-participant-
coverage claims.

Resolution requires source confirmation or a documented transcript-level participant
roster. Do not infer, merge, split, or invent an identity to force the counts to match.

## Exact remaining blockers for a formal/publication study

Under the retained formal/publication framework, Dreaddit and AGYW both keep
`real_text_ready: false` and all ten external gates remain pending:

1. project-specific institutional secondary-use determination;
2. exact source/platform authorization and terms scope;
3. approved model/provider processing profile;
4. exact corpus/version/input-field contract;
5. completed two-person review for every selected excerpt and displayed context;
6. approved cluster-aware sampling plan and power/time-derived count;
7. frozen study manifest (and clean pre-access freeze for held-out lanes);
8. rater consent, withdrawal, least-privilege, encryption, and access logging;
9. retention, deletion, incident-response, and responsible-owner controls; and
10. release-class, license/attribution, and release privacy review.

Dreaddit additionally lacks a corpus license and documented source ethics/privacy
statement in the archive, so the current institutional and platform determinations
must explicitly cover model processing, rater display, quotation, and release. AGYW's
CC BY 4.0 deposit and upstream consent/ethics statements do not replace this project's
secondary-use, model, rater, contextual-privacy, or release determination. The AGYW
106/107 discrepancy must be resolved before any complete-participant-coverage claim.

Those requirements do not apply to the active personal-local diagnostic lane.
They must still be completed before any human-facing, cloud, publication,
submission, quotation, redistribution, or release workflow is enabled. This
formal workflow records no real approval and does not change KODIS, CANDOR, or
their processing files.

## Regression checks

```bash
python3 -m unittest -v dataset/tests/test_dreaddit_agyw_review.py
python3 dataset/scripts/validate_corpora.py
```

The targeted tests cover whole-cluster sampling, deterministic manifests, numeric and
month-name exact-date quarantine (including displayed context), two distinct reviewers,
ledger text exclusion, private file modes, checksum-bound audits, and rejection before
held-out AGYW records access.
