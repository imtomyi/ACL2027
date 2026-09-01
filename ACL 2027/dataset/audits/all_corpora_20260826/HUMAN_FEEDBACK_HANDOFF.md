# Human-feedback handoff

As of 2026-08-26, deterministic corpus preparation has reached the point where
corpus statistics can be reported without inventing experimental outcomes. The
five real corpora on disk are Dreaddit, Cache2/CaCHe, KODIS, CaSiNo, and the AMI
scenario meetings. Their units are heterogeneous and must not be summed into a
single sample size.

## Completed machine-checkable work

| Corpus | Completed status | Current boundary |
|---|---|---|
| Dreaddit | Processed derivative validated; duplicate and exact-date cluster rules leave 3,516 candidate segments and 301,279 words | Governance decision, two-person excerpt/privacy clearance, and ratings |
| Cache2/CaCHe | Processed derivative validated; 3,076 primary-eligible participant turns and 98,735 words | Reconcile 106 observed speaker keys with 107 reported participants, then governance/privacy clearance and ratings |
| KODIS | Private exploratory conversion validated; 2,076 dialogues, 27,121 turns, and 568,333 words | Keep one unsplit exploratory role; confirm allowed model/rater use and perform contextual privacy review |
| CaSiNo | Source and schema inventory verified; 1,030 dialogues and 11,919 ordinary messages | Approve transcript allowlist and either obtain participant linkage or keep one unsplit role; adapter still needed |
| AMI scenario | Source and connected-component inventory verified; 138 meetings and 69,258 speech segments | Approve and validate transcript adapter; preserve all 35 meeting-speaker components |

KODIS is technically fit for local exploratory dialogue experiments using the
private `exploratory_unsplit` output. That conclusion does not make it a
confirmatory dataset, authorize external model processing or rater disclosure,
or support participant-disjoint evaluation.

## Decisions that require the study lead

1. Confirm the manuscript roles of KODIS, CaSiNo, and AMI, including whether
   KODIS remains outside the confirmatory comparison.
2. Record the allowed model-processing and rater-access pathway for every real
   corpus used in a study.
3. Approve reviewer-role qualifications, dual-expertise handling, tutorial and
   comprehension rules, recruitment, consent, compensation, and withdrawal.
4. Freeze packet counts, ratings per role, the expert-minute budget, power
   target, noninferiority margin, and model snapshots.
5. Approve privacy-cleared packets and controlled variants before assignment.

## Human evidence required for manuscript results

| Manuscript result | Human input that must exist first |
|---|---|
| Study accounting | Unique rater identities, role eligibility, packet assignments, exclusions, and active review time |
| Artifact-quality profile | Three construct-specific ordinal ratings, construct-specific abstentions, serious-error flags, and independent analyst concept matches |
| Role sensitivity | Repeated blinded ratings by researcher, qualitative-methods, and domain-expert groups for each failure family |
| Routing | Expert escalation decisions and observed expert minutes, with a frozen development-only policy |
| Repair | Feedback text, fixed-model revisions, and separate blinded repair/collateral-error judgments |
| Reliability and calibration | Repeated ratings, confidence, abstentions, active time, and frozen scoring/export code |
| Selective-risk curve | Human serious-error labels and review-time budgets across routing thresholds |

These cells must remain blank until those records exist. Corpus sizes, parser
diagnostics, synthetic model-judge scores, and outcome fields in source data are
not substitutes for human evaluation.

## Working artifacts

- `corpus_inventory.csv`: manuscript-facing five-corpus preparation statistics.
- `aggregate_inventory.json`: machine-readable preparation summary.
- `results_cell_status.csv`: exact result-table-to-human-input map.
- `../../KODIS_EXPLORATORY.md`: KODIS private exploratory processing contract.
- `../../../app/feedback-collector-demo/`: local feedback-instrument workspace;
  its core contract tests pass locally, but do not deploy or collect ratings
  until the study lead resolves and approves the decisions listed in
  `../../../app/feedback-collector-demo/CONTRACT_HANDOFF.md`, including the
  item bank and participant materials.
