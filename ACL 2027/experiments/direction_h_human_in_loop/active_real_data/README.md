# Active real-data coordination area

This folder is the only active Direction H lane. It contains no corpus text.
Target corpora are `dreaddit` and `agyw_focus_groups`; both are presently
blocked before record access.

## Current gate result

The governance-only checker reports:

| Corpus | Intended role | Completed gates | Ready |
|---|---|---:|---|
| Dreaddit train | development/pilot | 0/10 | no |
| Dreaddit test | in-domain audit after freeze | 0/10 | no |
| AGYW focus groups | held-out cross-domain confirmation | 0/10 | no |

Restricted source and prepared working directories exist with owner-only
permissions. That confirms storage hygiene only; it is not experiment approval.

## Preparation order

1. Complete the project-specific institutional determination for secondary
   use, protected-text model processing, human-rater exposure, and release
   review.
2. Complete corpus-specific source/platform scope. Dreaddit needs affirmative
   Reddit/platform coverage; AGYW needs exact CC BY attribution and project-use
   scope documented.
3. Approve exact provider/model endpoints and retention/training/human-access
   settings separately for each corpus.
4. Freeze corpus/version/split/allowed fields and the Direction H task,
   constructs, packet context, model, prompts, outcomes, and analysis code.
   AGYW must remain untouched by development choices and frozen before held-out
   candidate-selection access.
5. Fix the power/expert-time-derived cluster counts and preserve Dreaddit posts
   and AGYW `(focus group, transcript-local speaker)` clusters.
6. Create restricted candidate packets, then obtain two distinct reviewers'
   privacy and permission decisions for every excerpt and displayed context.
7. Complete rater consent/withdrawal, least-privilege, encryption/access logs,
   retention/deletion, incident response, and responsible-owner records.
8. Re-run the governance-only checker. Only an evidence-backed `10/10` and
   `real_text_ready=true` permits the next restricted preparation step.

The AGYW 106/107 participant-key discrepancy must be resolved before any
complete-participant-coverage claim. It does not authorize merging identities
across focus groups.

## Dataset-specific indexes

- [`dreaddit/README.md`](dreaddit/README.md)
- [`agyw_focus_groups/README.md`](agyw_focus_groups/README.md)
- [`reviewer_portal/README.md`](reviewer_portal/README.md) — text-free reviewer
  onboarding and live readiness display; review content remains server-locked.
- [`INTERNAL_CONTROLS_DRAFT.md`](INTERNAL_CONTROLS_DRAFT.md) — prefilled
  internal data-minimization, responsibility, retention, incident, and release
  defaults; not authorization.
- [`CONTROL_PREFILL_AUDIT.md`](CONTROL_PREFILL_AUDIT.md) — text-free audit of
  what was safely prepared and what still requires evidence.
- [`configs/README.md`](configs/README.md) — contains only a nonactive,
  text-free internal-control draft; no real-data runtime configuration is
  active.
- [`runs/README.md`](runs/README.md) — reserved for approved run metadata;
  currently contains no run.

These files describe gates and roles only. They intentionally contain no
excerpt, participant narrative, raw source identifier, or candidate item.
