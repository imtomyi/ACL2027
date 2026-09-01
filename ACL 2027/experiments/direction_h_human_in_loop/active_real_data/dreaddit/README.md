# Dreaddit real-data lane

Roles: official train for development/pilot; official test for in-domain audit
only after packet, prompt, duplicate, model, outcome, and analysis rules freeze.

Current status: restricted source and working copy present; `0/10` governance
gates; no item authorized for processing or display.

Additional blockers include the absent dataset license and absent archived
source ethics/privacy statement. Institutional and Reddit/platform evidence
must explicitly cover restricted preparation, model processing, rater display,
quotation, and release review. Preserve complete post clusters. Stress labels
and subreddit may support sampling/audit only; they are not qualitative ground
truth or router features.

Do not open `dataset/raw/dreaddit/` or
`dataset/deidentified/dreaddit/records.jsonl` from this lane until the exact
governance record is ready. Exact-date quarantine and two-person contextual
privacy review remain mandatory after authorization.

## Metadata-only pre-access package

- [`dreaddit_input_contract.pending.json`](dreaddit_input_contract.pending.json)
  binds the known source receipt, official split roles, proposed minimum fields,
  cluster rule, Direction H researcher role, and release posture. Every access
  and approval field remains false.
- [`dreaddit_study_freeze.pending.json`](dreaddit_study_freeze.pending.json)
  binds the actor-neutral Direction J item/rating contracts and Direction H
  feedback/repair contracts needed for item-level comparison. Every unfinished
  study choice remains null and the freeze remains inactive.
- [`validate_preaccess_metadata.py`](validate_preaccess_metadata.py) validates
  only these metadata files and their explicitly allowlisted text-free source
  manifest, schemas, and guide. It refuses paths under raw, deidentified,
  pilot, and fictional artifact areas.

These files reduce setup work but do not complete any governance gate. A future
authorized copy must use a new versioned filename; do not overwrite the pending
audit scaffold or flip its false fields in place.
