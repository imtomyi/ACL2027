# Charlie: start here

> **STOP — this older fictional-data handoff is inactive.** Fictional or
> synthetic data is not authorized for the current study. The active target
> corpora are real Dreaddit and real `agyw_focus_groups`, and both remain
> blocked before text access. Start at
> [`REAL_DATA_START_HERE.md`](REAL_DATA_START_HERE.md); do not run any command
> below unless a future, versioned scope decision explicitly reactivates it.

The current companion-compatible pilot uses Direction J's exact 24 fictional
theme-and-evidence items. Do **not** start the older four-item full-output
collector in the same phase; both queues reuse the same source contexts and are
not exchangeable.

Your first safe action is a read-only preflight from this directory:

```bash
python3 scripts/validate_direction_j_browser.py --prepared-only
```

It should report `valid_prepared_not_activated`, 24 synthetic items, zero
ratings, zero feedback records, and no real text. This command displays no
analysis item and writes nothing.

Next, read the exact shared guide and the excluded tutorial:

- `../direction_j_llm_as_rater/protocol/shared_rater_guide_v1.md`
- `companion_j_bridge/browser/tutorial/tutorial_v1.md`
- `companion_j_bridge/browser/tutorial/comprehension_check_v1.json`

Record your actual two comprehension answers in a copy of
`companion_j_bridge/browser/tutorial/charlie_response.template.json` and return
them to the non-reviewing coordinator. Do not score yourself, fill in a pass,
open `coordinator_only/`, inspect Direction J's private key/condition map, view
another assignment, or start either collector.

The coordinator must score and freeze the qualification record, complete the
actor registry, and activate the browser lane before you can rate. When they
confirm activation, run:

```bash
python3 scripts/validate_direction_j_browser.py
python3 scripts/serve_direction_j_browser.py
```

Then use the loopback address shown in the terminal. Rate the displayed evidence
only. Record the three separate constructs, construct-specific cannot-judge,
confidence, disposition, requested expertise, all applicable serious-error
flags, and a concise source-linked rationale. Submit the rating before writing
the identity-free revision feedback. Do not infer a planted condition or aim for
any quota of defects.

Your records are a construction-involved developer-researcher case baseline.
They do not establish universal human ground truth or independent-human
performance.
