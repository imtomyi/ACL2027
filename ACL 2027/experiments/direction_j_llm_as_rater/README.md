# Research Direction J: an LLM as the first-stage WarrantRoute judge

Version: `direction-j-v1`  
Status: **real-data study planned; blocked before data access**  
Date: 2026-08-25

## Purpose

Direction J compares an LLM judge with Charlie and, in the confirmatory phase,
independent humans on identical source-grounded items and the same structured
rating contract. Outcomes include construct-level agreement, serious-error
detection, calibration, abstention and escalation, rationale usefulness,
cost/latency, and downstream repair without collateral error.

The LLM is always recorded as a model system, never as a human. Agreement is a
diagnostic, not validity: every first-stage actor is compared separately with
locked independent expert adjudication and downstream task outcomes.

## Data policy and target sources

The intended real sources are Dreaddit and `agyw_focus_groups`. No fictional or
synthetic data is authorized. Fresh, explicit user permission is required
before any future fictional-data use; prior permission does not carry forward.
See [`NO_FICTIONAL_DATA.md`](NO_FICTIONAL_DATA.md).

Protected real text also remains blocked. The workspace does not currently
contain a completed approval record establishing the required institutional,
source/platform, provider-processing, privacy-review, exact-version/field,
cluster-sampling, access, retention, deletion, and release gates. Do not open,
copy, render, or process dataset text until those records are complete.

Planned roles:

- Dreaddit train: approved development only.
- Dreaddit test: post-freeze in-domain audit.
- `agyw_focus_groups`: post-freeze cross-domain confirmatory evaluation.

Preserve post/document clusters for Dreaddit and focus-group/speaker clusters
for AGYW. “Held out” means held out from this study's development, not model
training-unseen.

## Active artifact map

- [`protocol/real_first_run_plan.md`](protocol/real_first_run_plan.md) — the
  gate-to-first-run sequence for the two real sources.
- [`config/governance_gate.template.json`](config/governance_gate.template.json)
  — fail-closed gate; both real lanes remain non-runnable.
- [`config/real_study_freeze.template.json`](config/real_study_freeze.template.json)
  — prospective real-study freeze; the tracked template is not approval.
- `protocol/study_protocol.md` and `protocol/analysis_plan.md` — paired design,
  outcomes, and analysis definitions.
- `protocol/shared_interface.md`, `protocol/shared_rater_guide_v1.md`, and
  `schemas/` — the item-level human/LLM response contract.
- `runs/real/dreaddit/` and `runs/real/agyw_focus_groups/` — empty, blocked lane
  directories containing policy readmes only.
- `scripts/` — policy-only placeholder. Synthetic-specific entry points were
  moved into the restricted quarantine. A new real-data runner may be created
  only after the exact gate and freeze pass.
- `archive/fictional_do_not_use/` — quarantined prior fictional artifacts. Do
  not open or use them.

## First run

The current first step is documentary, not computational: complete and approve
the missing governance records, then replace the tracked real-study template
with a signed prospective freeze. Until then, the correct number of dataset
records opened, model calls, human ratings, and empirical results is zero.

Once authorized, the first run must:

1. create privacy-cleared, cluster-aware packets from the approved real splits;
2. give Charlie, the LLM, and later independent humans the identical canonical
   item and complete guide;
3. use the same full structured rating response at item level;
4. lock first-stage and independent expert ratings before adjudication/unblinding;
5. keep Dreaddit development/audit and AGYW confirmatory estimates separate;
6. report each rating construct separately and never treat human agreement alone
   as validity; and
7. collect serious-error, calibration, escalation, rationale, cost/latency, and
   repair-without-collateral-error outcomes without filling missing results.

Charlie’s actual relationship to item construction must be documented, not
assumed. If involved, Charlie is excluded from the primary independence analysis
and reported separately.
